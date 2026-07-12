#!/bin/bash

# Runs the whole team locally:
#   8001 planner | 8002 builder | 8003 reviewer | 8005 ux_designer | 8004 orchestrator | 8000 studio

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "${SCRIPT_DIR}"

if [ -f ".env" ]; then
  set -a; source .env; set +a
fi

# Kill any existing processes on these ports
echo "Stopping any existing processes on ports 8000-8005..."
lsof -ti:8000,8001,8002,8003,8004,8005 | xargs kill -9 2>/dev/null

# Set common environment variables for local development
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project -q 2>/dev/null)}"
export GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-global}"
export GOOGLE_GENAI_USE_VERTEXAI="${GOOGLE_GENAI_USE_VERTEXAI:-True}"

echo "Starting Planner Agent on port 8001..."
pushd agents/planner > /dev/null
uv run adk_app.py --host 0.0.0.0 --port 8001 --a2a . &
PLANNER_PID=$!
popd > /dev/null

echo "Starting Builder Agent on port 8002..."
pushd agents/builder > /dev/null
uv run adk_app.py --host 0.0.0.0 --port 8002 --a2a . &
BUILDER_PID=$!
popd > /dev/null

echo "Starting Reviewer Agent on port 8003..."
pushd agents/reviewer > /dev/null
uv run adk_app.py --host 0.0.0.0 --port 8003 --a2a . &
REVIEWER_PID=$!
popd > /dev/null

echo "Starting UX Designer Agent on port 8005..."
pushd agents/ux_designer > /dev/null
uv run adk_app.py --host 0.0.0.0 --port 8005 --a2a . &
UX_DESIGNER_PID=$!
popd > /dev/null

export PLANNER_AGENT_CARD_URL=http://localhost:8001/a2a/agent/.well-known/agent-card.json
export BUILDER_AGENT_CARD_URL=http://localhost:8002/a2a/agent/.well-known/agent-card.json
export REVIEWER_AGENT_CARD_URL=http://localhost:8003/a2a/agent/.well-known/agent-card.json
export UX_DESIGNER_AGENT_CARD_URL=http://localhost:8005/a2a/agent/.well-known/agent-card.json

# Wait a bit for the A2A agents to start up
sleep 5

echo "Starting Orchestrator Agent on port 8004..."
pushd agents/orchestrator > /dev/null
uv run adk_app.py --host 0.0.0.0 --port 8004 . &
ORCHESTRATOR_PID=$!
popd > /dev/null

sleep 3

echo "Starting Studio app on port 8000..."
pushd app > /dev/null
export AGENT_SERVER_URL=http://localhost:8004
uv run uvicorn main:app --host 0.0.0.0 --port 8000 &
STUDIO_PID=$!
popd > /dev/null

echo ""
echo "All services started!"
echo "  Planner:      http://localhost:8001"
echo "  Builder:      http://localhost:8002"
echo "  Reviewer:     http://localhost:8003"
echo "  UX Designer:  http://localhost:8005"
echo "  Orchestrator: http://localhost:8004"
echo "  Studio (UI):  http://localhost:8000   <-- open this"
echo ""
echo "Press Ctrl+C to stop the team."

trap "kill $PLANNER_PID $BUILDER_PID $REVIEWER_PID $UX_DESIGNER_PID $ORCHESTRATOR_PID $STUDIO_PID 2>/dev/null; exit" INT
wait
