# AGENTS.md — context for AI coding assistants (Antigravity, etc.)

This repo is a multi-agent "AI software team" built with Google ADK and the A2A
protocol, deployed as six Cloud Run services. Participants extend it during a
workshop, usually with an agentic IDE driving the changes.

## What this system does

A user types a product idea into the Studio web app (or runs `cli.py`). The
Orchestrator runs a pipeline: **Planner** (idea → build plan), **UX Designer**
(plan → design spec), then a **build loop** where the **Builder** (plan +
design spec → static app files) and the **Reviewer** (structured pass/fail
verdict) iterate up to 3 times. The Studio previews the shipped app in an
iframe (`/preview/{session}/...`) and offers a single-file or zip download;
`cli.py` writes the files into a local directory instead.

## Layout and conventions

- `agents/<name>/agent.py` — each agent's definition. The module must expose
  `root_agent`. Worker agents (planner, ux_designer, builder, reviewer) are
  plain ADK `Agent`s; all orchestration logic lives ONLY in
  `agents/orchestrator/agent.py`.
- `agents/orchestrator/agent.py` — connects to workers via `RemoteA2aAgent`
  (agent-card URLs from `*_AGENT_CARD_URL` env vars), saves each worker's output
  to session state via `after_agent_callback`, and breaks the loop with
  `EscalationChecker` when `review_feedback.status == "pass"`.
- `shared/*.py` — infrastructure symlinked into every service dir
  (`adk_app.py` server entrypoint, `a2a_utils.py` card rewriting,
  `authenticated_httpx.py` Cloud Run identity tokens). **Edit the file in
  `shared/`, never the symlink targets' copies.** When adding a new agent,
  recreate the same symlinks (`ln -s ../../shared/adk_app.py ...`).
- `app/main.py` — Studio backend. Streams NDJSON events to the frontend:
  `session`, `status`, `plan`, `review`, `result`. The frontend
  (`app/frontend/app.js`) renders those; keep both sides in sync when adding
  event types.
- Model id lives in each `agent.py` as `MODEL`, read from the `GEMINI_MODEL`
  env var (default `gemini-3.1-pro`). `deploy.sh` accepts
  `BUILDER_GEMINI_MODEL` to give the builder a custom model; swap a deployed
  service's model with `gcloud run services update <svc> --update-env-vars
  GEMINI_MODEL=...` (never `--set-env-vars`, which wipes the other vars).

## How to run and verify

- Local: `./run_local.sh` (ports 8001-8005 for agents, 8004 orchestrator,
  8000 for Studio).
  Requires `uv` and Google credentials (`gcloud auth application-default login`).
- Agent card smoke test:
  `curl http://localhost:8001/a2a/agent/.well-known/agent-card.json`
- Deploy: `./deploy.sh` (Cloud Run; workers are private, `studio` is public).

## Common tasks

- **Add a teammate**: copy an existing worker dir (e.g. `agents/reviewer`),
  write its `agent.py` + `pyproject.toml`, recreate the two symlinks, add it to
  `run_local.sh` (new port + card URL env var), wire a `RemoteA2aAgent` into the
  orchestrator pipeline, add a deploy block in `deploy.sh`, and (optionally) a
  status line in `app/main.py`'s `AGENT_STATUS`.
- **Change what the team builds**: edit the worker instructions in lockstep —
  the Planner's constraints, the UX Designer's spec, the Builder's output
  contract (`=== FILE: path ===` marker + fenced block per file, `index.html`
  required), and the Reviewer's checklist must agree. If the Builder's output
  format changes, update `parse_files()` in `app/main.py`.

## Gotchas

- The Reviewer uses `output_schema`, so it must keep
  `disallow_transfer_to_parent/peers=True`.
- State keys are load-bearing strings: `build_plan`, `design_spec`,
  `app_code`, `review_feedback` (orchestrator callbacks + EscalationChecker +
  worker instructions all reference them).
- `run_local.sh` kills anything on ports 8000-8005 before starting.
