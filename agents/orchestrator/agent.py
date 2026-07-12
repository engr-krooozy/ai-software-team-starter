import json
import os
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LoopAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.events import Event, EventActions

from authenticated_httpx import create_authenticated_client


# --- Callbacks ---
def create_save_output_callback(key: str):
    """Creates a callback to save the agent's final response to session state."""

    def callback(callback_context: CallbackContext, **kwargs) -> None:
        ctx = callback_context
        # Find the last event from this agent that has content
        for event in reversed(ctx.session.events):
            if event.author == ctx.agent_name and event.content and event.content.parts:
                text = event.content.parts[0].text
                if text:
                    # Try to parse as JSON if it looks like it, for review_feedback
                    if key == "review_feedback" and text.strip().startswith("{"):
                        try:
                            ctx.state[key] = json.loads(text)
                        except json.JSONDecodeError:
                            ctx.state[key] = text
                    else:
                        ctx.state[key] = text
                    print(f"[{ctx.agent_name}] Saved output to state['{key}']")
                    return

    return callback


# --- Remote Agents ---
# Each teammate runs in its own container. We connect to them via A2A using
# their agent cards. Default URLs assume the local dev ports from run_local.sh.

# Connect to the Planner (localhost port 8001)
planner_url = os.environ.get(
    "PLANNER_AGENT_CARD_URL",
    "http://localhost:8001/a2a/agent/.well-known/agent-card.json",
)
planner = RemoteA2aAgent(
    name="planner",
    agent_card=planner_url,
    description="Decomposes the product idea into a build plan.",
    # IMPORTANT: Save the output to state for the Builder and Reviewer to see
    after_agent_callback=create_save_output_callback("build_plan"),
    # IMPORTANT: httpx client with Id Token Authentication
    httpx_client=create_authenticated_client(planner_url),
)

# Connect to the UX Designer (localhost port 8005)
ux_designer_url = os.environ.get(
    "UX_DESIGNER_AGENT_CARD_URL",
    "http://localhost:8005/a2a/agent/.well-known/agent-card.json",
)
ux_designer = RemoteA2aAgent(
    name="ux_designer",
    agent_card=ux_designer_url,
    description="Turns the build plan into a concrete design spec.",
    after_agent_callback=create_save_output_callback("design_spec"),
    # IMPORTANT: httpx client with Id Token Authentication
    httpx_client=create_authenticated_client(ux_designer_url),
)

# Connect to the Builder (localhost port 8002)
builder_url = os.environ.get(
    "BUILDER_AGENT_CARD_URL",
    "http://localhost:8002/a2a/agent/.well-known/agent-card.json",
)
builder = RemoteA2aAgent(
    name="builder",
    agent_card=builder_url,
    description="Implements the plan as a single-file web app.",
    after_agent_callback=create_save_output_callback("app_code"),
    # IMPORTANT: httpx client with Id Token Authentication
    httpx_client=create_authenticated_client(builder_url),
)

# Connect to the Reviewer (localhost port 8003)
reviewer_url = os.environ.get(
    "REVIEWER_AGENT_CARD_URL",
    "http://localhost:8003/a2a/agent/.well-known/agent-card.json",
)
reviewer = RemoteA2aAgent(
    name="reviewer",
    agent_card=reviewer_url,
    description="Reviews the built app against the plan.",
    after_agent_callback=create_save_output_callback("review_feedback"),
    # IMPORTANT: httpx client with Id Token Authentication
    httpx_client=create_authenticated_client(reviewer_url),
)


# --- Local Orchestration Agents ---
class EscalationChecker(BaseAgent):
    """Checks the reviewer's feedback and escalates (breaks the loop) if it passed."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        feedback = ctx.session.state.get("review_feedback")

        # Debug log to see what we got from the remote agent
        print(f"[EscalationChecker] Feedback received: {feedback}")

        if feedback and isinstance(feedback, dict) and feedback.get("status") == "pass":
            yield Event(author=self.name, actions=EventActions(escalate=True))
        elif isinstance(feedback, str) and '"status": "pass"' in feedback:
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            yield Event(author=self.name)


escalation_checker = EscalationChecker(name="escalation_checker")


# --- Orchestration ---
# Build loop: the Builder ships, the Reviewer gates, until the review passes
# or we hit max_iterations.
build_loop = LoopAgent(
    name="build_loop",
    description="Iteratively builds and reviews the app until it passes review.",
    sub_agents=[builder, reviewer, escalation_checker],
    max_iterations=3,
)

# The full team pipeline: plan, design, then build/review until it ships.
root_agent = SequentialAgent(
    name="software_team_pipeline",
    description="A software team that plans, designs, builds, and reviews a product from a single idea.",
    sub_agents=[planner, ux_designer, build_loop],
)
