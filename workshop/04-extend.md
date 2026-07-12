# Module 4 — Extend your team (25 min)

Goal: use Antigravity (or your agentic IDE of choice) to grow the team. This is
the point of the workshop: you are the one developer; the repo is your team;
your IDE agent is how you manage them.

Open this repo in Antigravity. `AGENTS.md` at the repo root briefs it on the
architecture, conventions, and gotchas — so you can prompt at the level of
*intent*, not file paths.

## The worked example: how the UX Designer got hired

This repo's `ux_designer` agent (port 8005, `design_spec` state key) was added
*by an AI coding agent* from a prompt like the one below. Study the diff of
what "hiring a teammate" touches — `agents/ux_designer/` (mostly boilerplate +
one instruction), one `RemoteA2aAgent` block in the orchestrator, one port in
`run_local.sh`, one deploy block in `deploy.sh`, one `AGENT_STATUS` line in the
Studio:

> Add a new A2A worker agent `ux_designer` modeled on `agents/planner`: it takes
> the user's idea and the build plan and outputs a concise design spec. Run it
> on port 8005 locally. Wire it into the orchestrator pipeline between the
> planner and the build loop, saving its output to state key `design_spec`.
> Update the builder's instruction to follow the design spec, and update
> run_local.sh, deploy.sh, and the Studio's AGENT_STATUS map.

## Challenge A — Hire your own teammate ⭐ (recommended)

Now hire the sixth worker yourself. Good candidates:

- An **Accessibility Auditor** that runs *inside the build loop* after the
  Reviewer, failing builds with missing labels, poor contrast against the
  design spec's palette, or no keyboard path.
- A **Copywriter** between the Planner and the UX Designer that names the
  product and writes its microcopy (state key `copy_deck`), which the Builder
  must use verbatim.
- A **Test Engineer** that turns the plan's acceptance criteria into a manual
  QA checklist shipped alongside the product as `TESTING.md`.

Adapt the prompt above; the pattern is identical. Verify: run locally, watch
the new teammate appear in the timeline, then `./deploy.sh` — you now have a
**seven-service** production system.

## Challenge B — Give the Reviewer real teeth

The Reviewer currently reasons about code; let it *check* code. Ideas:

- Add a deterministic pre-check before the LLM review: parse the
  `=== FILE: path ===` blocks (reuse `parse_files()` from `app/main.py`),
  confirm `index.html` exists, every relative reference resolves to an
  emitted file, and nothing contains external `http(s)://` references.
- Make the Reviewer's schema richer: `severity`, `criteria_results: list`.
  Update the EscalationChecker and the Studio's review rendering to match.

## Challenge C — Change what the team ships

Swap the product domain by editing the worker instructions in lockstep
(see `AGENTS.md` → "Change what the team builds"):

- A **data team**: Planner scopes an analysis, Builder writes a Python
  script (the multi-file contract already supports `analysis.py` +
  `README.md`), Reviewer checks it runs on the sample data.
- A **content team**: landing-page copy + brand kit instead of an app.

## Challenge D — Production niceties

- Persist every shipped product to a GCS bucket from `app/main.py` — today
  the preview store is in-memory per instance and vanishes on scale-down.
- Add `--session_service_uri` (SQLite locally, Cloud SQL in prod) so build
  sessions survive restarts.
- Set `--trace_to_cloud` on the agent services and explore the traces in
  Cloud Trace.

## Wrap-up

You built and deployed a multi-agent system where:

- each agent is an independently deployable, independently *replaceable*
  microservice with a discoverable card (A2A),
- orchestration is deterministic code, not vibes (ADK workflow agents),
- quality is enforced by a structured review gate, not hope — you watched it
  send real builds back with real defects,
- the product ships as real files (Studio preview, zip, or `cli.py` straight
  into a workspace),
- and one developer directed the whole thing through an agentic IDE.

That's the shape of agentic software engineering. Take the repo home and make
the team yours. 🚀
