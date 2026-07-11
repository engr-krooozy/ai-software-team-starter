# One Developer. Four AI Agents. One Deployed Product.

**Build a Multi-Agent Software Team in 90 Minutes with Antigravity, ADK and A2A.**

This is the starter repo for the workshop. By the end of the session you will have a
**working, deployed product**: a web app ("Studio") where anyone types a product idea
and your AI software team plans it, builds it, reviews it, and ships it — live on
Cloud Run.

```
   💡 idea
    │
    ▼
┌─────────────┐     A2A      ┌──────────┐
│ Orchestrator│ ───────────▶ │ Planner  │  decomposes the idea into a build plan
│  (team lead)│              └──────────┘
│             │     A2A      ┌──────────┐
│  Sequential │ ───────────▶ │ Builder  │  implements it as a single-file web app
│      +      │              └──────────┘
│    Loop     │     A2A      ┌──────────┐
│             │ ───────────▶ │ Reviewer │  tests it against the plan: pass / fail
└─────────────┘              └──────────┘
    │                (fail → back to Builder, max 3 iterations)
    ▼
   🚢 shipped product (previewed live in the Studio, downloadable)
```

Every agent is its own containerized microservice speaking the
[A2A protocol](https://a2a-protocol.org). The Orchestrator composes them with
[ADK](https://google.github.io/adk-docs/) workflow agents (`SequentialAgent` +
`LoopAgent`) using `RemoteA2aAgent`. The deployment step puts all five services
on Cloud Run with service-to-service authentication.

## The team

| Service | Role | ADK concept | Port (local) |
|---|---|---|---|
| `agents/planner` | Decomposes the idea into an MVP plan with acceptance criteria | `Agent` | 8001 |
| `agents/builder` | Implements the plan as one self-contained HTML file | `Agent` | 8002 |
| `agents/reviewer` | QA-gates the build; structured pass/fail verdict | `Agent` + `output_schema` | 8003 |
| `agents/orchestrator` | Team lead: plan → (build ⇄ review) loop | `SequentialAgent`, `LoopAgent`, `RemoteA2aAgent` | 8004 |
| `app` (Studio) | Web UI: idea in, live team activity, product preview out | FastAPI + ADK API server client | 8000 |

## Quick start

**Prerequisites:** [`uv`](https://docs.astral.sh/uv/), the
[Google Cloud SDK](https://cloud.google.com/sdk), and a GCP project with the
Vertex AI, Cloud Run, and Cloud Build APIs enabled.

```bash
# 1. Authenticate
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# 2. Install dependencies
uv sync

# 3. Run the whole team locally
./run_local.sh

# 4. Open the Studio
open http://localhost:8000
```

Type an idea — *"a pomodoro timer with a session log"* — and watch the team work.

## Deploy to Cloud Run

```bash
./deploy.sh
```

This deploys `planner`, `builder`, `reviewer`, and `orchestrator` as **private**
services (agent-to-agent calls use Cloud Run identity tokens), and `studio` as the
single **public** entry point. The script prints your live product URL at the end.

## Workshop modules (90 minutes)

| # | Module | Time |
|---|---|---|
| 0 | [Setup](workshop/00-setup.md) — project, APIs, auth, uv | 10 min |
| 1 | [Meet the team](workshop/01-meet-the-team.md) — run locally, ship your first product | 15 min |
| 2 | [How it works](workshop/02-how-it-works.md) — ADK workflow agents, A2A agent cards, the review loop | 20 min |
| 3 | [Deploy](workshop/03-deploy.md) — five Cloud Run services, service-to-service auth | 20 min |
| 4 | [Extend](workshop/04-extend.md) — use Antigravity to grow your team | 25 min |

## Project structure

```
ai-software-team/
├── agents/
│   ├── planner/        # A2A microservice: idea → build plan
│   ├── builder/        # A2A microservice: plan → single-file web app
│   ├── reviewer/       # A2A microservice: app → structured pass/fail
│   └── orchestrator/   # Team lead: SequentialAgent + LoopAgent over RemoteA2aAgents
├── app/                # "Studio" web app (FastAPI + vanilla JS frontend)
├── shared/             # Files symlinked into every service:
│   ├── adk_app.py              #   ADK API server entrypoint with A2A support
│   ├── a2a_utils.py            #   Agent-card URL rewriting behind Cloud Run proxies
│   └── authenticated_httpx.py  #   httpx client with Cloud Run identity tokens
├── run_local.sh        # Run all 5 services locally
├── deploy.sh           # Deploy all 5 services to Cloud Run
└── workshop/           # The 90-minute workshop guide
```

Shared infrastructure files live in `shared/` and are **symlinked** into each
service directory so every container stays self-contained at build time.

## Extending it into your own product

This repo is deliberately a *starter*: the team currently ships single-file web
apps, but the pattern generalizes. Swap the agents' instructions and you have a
data-pipeline team, a content team, or a research team. See
[workshop/04-extend.md](workshop/04-extend.md) for guided challenges, including
adding a fourth teammate over A2A.

## Credits

The A2A/ADK service scaffolding (`shared/`) is adapted from Google's
[production-ready-ai roadshow lab](https://github.com/GoogleCloudPlatform/devrel-demos/tree/main/agents/build-with-ai/production-ready-ai)
(Apache 2.0). This repo is likewise licensed under [Apache 2.0](LICENSE).
