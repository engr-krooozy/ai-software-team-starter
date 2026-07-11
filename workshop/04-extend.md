# Module 4 — Extend your team (25 min)

Goal: use Antigravity (or your agentic IDE of choice) to grow the team. This is
the point of the workshop: you are the one developer; the repo is your team;
your IDE agent is how you manage them.

Open this repo in Antigravity. `AGENTS.md` at the repo root briefs it on the
architecture, conventions, and gotchas — so you can prompt at the level of
*intent*, not file paths.

## Challenge A — Hire a fourth teammate ⭐ (recommended)

Add a **UX Designer** agent that runs between the Planner and the build loop,
producing a short design spec (layout, color palette, interaction details) that
the Builder must follow.

Prompt your IDE with something like:

> Add a new A2A worker agent `ux_designer` modeled on `agents/planner`: it takes
> the user's idea and the build plan and outputs a concise design spec. Run it
> on port 8005 locally. Wire it into the orchestrator pipeline between the
> planner and the build loop, saving its output to state key `design_spec`.
> Update the builder's instruction to follow the design spec, and update
> run_local.sh, deploy.sh, and the Studio's AGENT_STATUS map.

Verify: run locally, watch the new teammate appear in the timeline, then
`./deploy.sh` — you now have a **six-service** production system.

## Challenge B — Give the Reviewer real teeth

The Reviewer currently reasons about code; let it *check* code. Ideas:

- Add a validation step that confirms the output parses as HTML and contains
  no external `http(s)://` references (a deterministic pre-check before the
  LLM review).
- Make the Reviewer's schema richer: `severity`, `criteria_results: list`.
  Update the EscalationChecker and the Studio's review rendering to match.

## Challenge C — Change what the team ships

Swap the product domain by editing the three worker instructions in lockstep
(see `AGENTS.md` → "Change what the team builds"):

- A **data team**: Planner scopes an analysis, Builder writes a single Python
  script, Reviewer checks it runs on the sample data.
- A **content team**: landing-page copy + brand kit instead of an app.

## Challenge D — Production niceties

- Persist every shipped product to a GCS bucket from `app/main.py`.
- Add `--session_service_uri` (SQLite locally, Cloud SQL in prod) so build
  sessions survive restarts.
- Set `--trace_to_cloud` on the agent services and explore the traces in
  Cloud Trace.

## Wrap-up

You built and deployed a multi-agent system where:

- each agent is an independently deployable, independently *replaceable*
  microservice with a discoverable card (A2A),
- orchestration is deterministic code, not vibes (ADK workflow agents),
- quality is enforced by a structured review gate, not hope,
- and one developer directed the whole thing through an agentic IDE.

That's the shape of agentic software engineering. Take the repo home and make
the team yours. 🚀
