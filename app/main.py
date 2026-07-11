import json
import logging
import os
import re
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from google.genai import types as genai_types
from httpx_sse import aconnect_sse
from pydantic import BaseModel

from authenticated_httpx import create_authenticated_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent_name = os.getenv("AGENT_NAME", None)
agent_server_url = os.getenv("AGENT_SERVER_URL")
if not agent_server_url:
    raise ValueError("AGENT_SERVER_URL environment variable not set")
else:
    agent_server_url = agent_server_url.rstrip("/")

clients: Dict[str, httpx.AsyncClient] = {}


async def get_client(agent_server_origin: str) -> httpx.AsyncClient:
    global clients
    if agent_server_origin not in clients:
        clients[agent_server_origin] = create_authenticated_client(agent_server_origin)
    return clients[agent_server_origin]


async def create_session(
    agent_server_origin: str, agent_name: str, user_id: str
) -> Dict[str, Any]:
    httpx_client = await get_client(agent_server_origin)
    headers = [("Content-Type", "application/json")]
    session_request_url = f"{agent_server_origin}/apps/{agent_name}/users/{user_id}/sessions"
    session_response = await httpx_client.post(session_request_url, headers=headers)
    session_response.raise_for_status()
    return session_response.json()


async def get_session(
    agent_server_origin: str, agent_name: str, user_id: str, session_id: str
) -> Optional[Dict[str, Any]]:
    httpx_client = await get_client(agent_server_origin)
    headers = [("Content-Type", "application/json")]
    session_request_url = f"{agent_server_origin}/apps/{agent_name}/users/{user_id}/sessions/{session_id}"
    session_response = await httpx_client.get(session_request_url, headers=headers)
    if session_response.status_code == 404:
        return None
    session_response.raise_for_status()
    return session_response.json()


async def list_agents(agent_server_origin: str) -> List[str]:
    httpx_client = await get_client(agent_server_origin)
    headers = [("Content-Type", "application/json")]
    list_url = f"{agent_server_origin}/list-apps"
    list_response = await httpx_client.get(list_url, headers=headers)
    list_response.raise_for_status()
    agent_list = list_response.json()
    if not agent_list:
        agent_list = ["agent"]
    return agent_list


async def query_adk_server(
    agent_server_origin: str, agent_name: str, user_id: str, message: str, session_id
) -> AsyncGenerator[Dict[str, Any], None]:
    httpx_client = await get_client(agent_server_origin)
    request = {
        "appName": agent_name,
        "userId": user_id,
        "sessionId": session_id,
        "newMessage": {"role": "user", "parts": [{"text": message}]},
        "streaming": False,
    }
    async with aconnect_sse(
        httpx_client, "POST", f"{agent_server_origin}/run_sse", json=request
    ) as event_source:
        if event_source.response.is_error:
            await event_source.response.aread()
            event = {
                "author": agent_name,
                "content": {
                    "parts": [{"text": f"Error {event_source.response.text}"}]
                },
            }
            yield event
        else:
            async for server_event in event_source.aiter_sse():
                event = server_event.json()
                yield event


def extract_html(text: str) -> Optional[str]:
    """Pulls the final HTML document out of the builder's response."""
    if not text:
        return None
    # Preferred: the single ```html fenced block the builder is instructed to emit
    blocks = re.findall(r"```html\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if blocks:
        return blocks[-1].strip()
    # Fallback: a bare HTML document
    match = re.search(r"(<!DOCTYPE html.*?</html>)", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


# Progress messages shown in the Studio timeline as each teammate takes over.
AGENT_STATUS = {
    "planner": "📋 Planner is decomposing your idea into a build plan...",
    "builder": "🔨 Builder is implementing the app...",
    "reviewer": "🔍 Reviewer is testing the build against the plan...",
}


class SimpleChatRequest(BaseModel):
    message: str
    user_id: str = "test_user"
    session_id: Optional[str] = None


@app.post("/api/build_stream")
async def build_stream(request: SimpleChatRequest):
    """Streams the team's progress and the final product as NDJSON."""
    global agent_name, agent_server_url
    if not agent_name:
        agent_name = (await list_agents(agent_server_url))[0]  # type: ignore

    session = None
    if request.session_id:
        session = await get_session(
            agent_server_url,  # type: ignore
            agent_name,
            request.user_id,
            request.session_id,
        )
    if session is None:
        session = await create_session(
            agent_server_url,  # type: ignore
            agent_name,
            request.user_id,
        )

    events = query_adk_server(
        agent_server_url,  # type: ignore
        agent_name,
        request.user_id,
        request.message,
        session["id"],
    )

    async def event_generator():
        yield json.dumps({"type": "session", "session_id": session["id"]}) + "\n"

        last_author = None
        plan_text = ""
        builder_text = ""
        iterations = 0

        async for event in events:
            author = event.get("author")

            # Announce hand-offs between teammates
            if author in AGENT_STATUS and author != last_author:
                if author == "builder":
                    iterations += 1
                yield json.dumps(
                    {"type": "status", "agent": author, "text": AGENT_STATUS[author]}
                ) + "\n"
            if author:
                last_author = author

            # Collect this event's text
            text = ""
            if event.get("content"):
                content = genai_types.Content.model_validate(event["content"])
                for part in content.parts or []:
                    if part.text:
                        text += part.text
            if not text:
                continue

            if author == "planner":
                plan_text += text
                yield json.dumps({"type": "plan", "text": plan_text}) + "\n"
            elif author == "builder":
                builder_text = text  # keep only the latest build
            elif author == "reviewer":
                verdict = None
                try:
                    verdict = json.loads(text)
                except json.JSONDecodeError:
                    pass
                yield json.dumps(
                    {
                        "type": "review",
                        "iteration": iterations,
                        "status": (verdict or {}).get("status", "unknown"),
                        "feedback": (verdict or {}).get("feedback", text),
                    }
                ) + "\n"

        html = extract_html(builder_text)
        yield json.dumps(
            {
                "type": "result",
                "html": html,
                "raw": builder_text if html is None else None,
                "iterations": iterations,
            }
        ) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


# Mount frontend from the copied location
frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
