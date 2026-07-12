# Module 2 — How it works (20 min)

Goal: understand the three layers — worker agents, A2A plumbing, and orchestration.

## Layer 1: Worker agents (the specialists)

Open `agents/planner/agent.py`, `agents/ux_designer/agent.py`,
`agents/builder/agent.py`, `agents/reviewer/agent.py`. Each is just an ADK
`Agent`: a model, a role description, and an instruction. Two details matter:

- **The contract is in the prompts.** The Planner promises acceptance criteria;
  the UX Designer promises a spec with concrete hex values and durations; the
  Builder promises `=== FILE: path ===` blocks with `index.html` required; the
  Reviewer checks all of it. Multi-agent systems live or die on these
  interfaces.
- **The Reviewer has `output_schema=ReviewFeedback`** (a Pydantic model with
  `status: pass|fail`). That's what turns an LLM opinion into something a
  program can branch on.

## Layer 2: A2A (the org chart wiring)

Each worker runs behind `shared/adk_app.py` with `--a2a`, which:

1. Builds an **agent card** at startup and serves it at
   `/a2a/agent/.well-known/agent-card.json`.
2. Exposes the agent at `/a2a/agent` speaking the A2A protocol.
3. Rewrites the card's URL behind proxies (`shared/a2a_utils.py`) so the same
   container works on localhost and Cloud Run.

`shared/authenticated_httpx.py` attaches Cloud Run **identity tokens** to
outbound calls — this is why the worker services can stay
`--no-allow-unauthenticated` in production.

## Layer 3: Orchestration (the team lead)

Open `agents/orchestrator/agent.py`. Bottom-up:

```
SequentialAgent(software_team_pipeline)
 ├── RemoteA2aAgent(planner)          # plan once
 ├── RemoteA2aAgent(ux_designer)      # design once
 └── LoopAgent(build_loop, max_iterations=3)
      ├── RemoteA2aAgent(builder)     # build
      ├── RemoteA2aAgent(reviewer)    # review
      └── EscalationChecker           # pass? break the loop
```

- **`RemoteA2aAgent`** makes a remote service feel like a local sub-agent —
  it's constructed from nothing but the agent-card URL.
- **`after_agent_callback`** saves each worker's output into session state
  (`build_plan`, `design_spec`, `app_code`, `review_feedback`).
- **`EscalationChecker`** is a tiny custom `BaseAgent`: it reads
  `review_feedback` from state and yields an `escalate` event when the review
  passed. Escalation is how ADK breaks a `LoopAgent`.

Note what the orchestrator does **not** contain: an LLM call of its own. The
control flow is deterministic code; only the workers think.

## The Studio (how you watched it happen)

`app/main.py` calls the Orchestrator's ADK API server (`/run_sse`) and relays
each event as NDJSON to the browser — that's the team activity timeline. At the
end, `parse_files()` extracts the `=== FILE: path ===` blocks from the
Builder's final message, keeps the product in memory, and serves it to the
preview iframe at `/preview/{session}/...` (with `/download/{session}.zip` for
multi-file products). `cli.py` consumes the same NDJSON stream and writes the
files to disk instead.

## Try this (5 min)

1. In `agents/orchestrator/agent.py`, set `max_iterations=1` and restart —
   quality drops become visible when the Reviewer can't send work back.
2. Make the Reviewer stricter (e.g. "fail any app without keyboard support")
   and watch the loop actually iterate. Restore `max_iterations=3` after.

Next: [Module 3 — Deploy](03-deploy.md)
