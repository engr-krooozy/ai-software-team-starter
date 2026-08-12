#!/bin/bash

# Deploys the full team to Cloud Run:
#   planner, builder, reviewer, ux-designer  (private A2A microservices)
#   orchestrator                (private, wired to the four above)
#   studio                      (public web app, wired to the orchestrator)
#
# Optional: BUILDER_GEMINI_MODEL=gemini-2.5-pro ./deploy.sh
#           gives the builder a stronger model than the flash default.
#           (Check which pro models your project can access; e.g. Qwiklabs
#           lab projects had gemini-2.5-pro but not gemini-3-pro-preview.)

set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "${SCRIPT_DIR}"

if [ -f ".env" ]; then
  set -a; source .env; set +a
fi

if [[ "${GOOGLE_CLOUD_PROJECT}" == "" ]]; then
  GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project -q)
fi
if [[ "${GOOGLE_CLOUD_PROJECT}" == "" ]]; then
  echo "ERROR: Run 'gcloud config set project' to set an active project, or set GOOGLE_CLOUD_PROJECT."
  exit 1
fi

REGION="${GOOGLE_CLOUD_LOCATION}"
if [[ "${REGION}" == "global" || "${REGION}" == "" ]]; then
  REGION=$(gcloud config get-value compute/region -q)
  if [[ "${REGION}" == "" ]]; then
    REGION="us-central1"
    echo "WARNING: No compute region configured. Defaulting to ${REGION}."
  fi
fi
echo "Using project ${GOOGLE_CLOUD_PROJECT}."
echo "Using compute region ${REGION}."

gcloud run deploy planner \
  --source agents/planner \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --no-allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true"
PLANNER_URL=$(gcloud run services describe planner --region $REGION --format='value(status.url)')

gcloud run deploy builder \
  --source agents/builder \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --no-allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true" \
  --set-env-vars GEMINI_MODEL="${BUILDER_GEMINI_MODEL:-gemini-3.1-pro}"
BUILDER_URL=$(gcloud run services describe builder --region $REGION --format='value(status.url)')

gcloud run deploy reviewer \
  --source agents/reviewer \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --no-allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true"
REVIEWER_URL=$(gcloud run services describe reviewer --region $REGION --format='value(status.url)')

gcloud run deploy ux-designer \
  --source agents/ux_designer \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --no-allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true"
UX_DESIGNER_URL=$(gcloud run services describe ux-designer --region $REGION --format='value(status.url)')

# The orchestrator and studio hold one request open for a whole pipeline run;
# a multi-iteration build easily exceeds Cloud Run's 300s default timeout.
gcloud run deploy orchestrator \
  --source agents/orchestrator \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --timeout 900 \
  --no-allow-unauthenticated \
  --set-env-vars PLANNER_AGENT_CARD_URL=$PLANNER_URL/a2a/agent/.well-known/agent-card.json \
  --set-env-vars BUILDER_AGENT_CARD_URL=$BUILDER_URL/a2a/agent/.well-known/agent-card.json \
  --set-env-vars REVIEWER_AGENT_CARD_URL=$REVIEWER_URL/a2a/agent/.well-known/agent-card.json \
  --set-env-vars UX_DESIGNER_AGENT_CARD_URL=$UX_DESIGNER_URL/a2a/agent/.well-known/agent-card.json \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true"
ORCHESTRATOR_URL=$(gcloud run services describe orchestrator --region $REGION --format='value(status.url)')

gcloud run deploy studio \
  --source app \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --timeout 900 \
  --allow-unauthenticated \
  --set-env-vars AGENT_SERVER_URL=$ORCHESTRATOR_URL \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}"
STUDIO_URL=$(gcloud run services describe studio --region $REGION --format='value(status.url)')

echo ""
echo "=============================================="
echo "🚢 Your AI software team is live:"
echo "   ${STUDIO_URL}"
echo "=============================================="
