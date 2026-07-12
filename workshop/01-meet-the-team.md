# Module 1 — Meet the team (15 min)

Goal: run all six services locally and ship your first product.

## 1. Start the team

```bash
./run_local.sh
```

This starts six processes:

| Port | Service | What it is |
|---|---|---|
| 8001 | Planner | A2A microservice |
| 8005 | UX Designer | A2A microservice |
| 8002 | Builder | A2A microservice |
| 8003 | Reviewer | A2A microservice |
| 8004 | Orchestrator | ADK API server, connects to the four above |
| 8000 | Studio | The web app you interact with |

First run takes a minute while `uv` resolves each service's environment.

## 2. Ship something

Open **http://localhost:8000**, click one of the example chips (or type your own
idea), and hit **🚀 Build it**. Watch the team activity panel:

1. 📋 Planner drafts the build plan (appears in the **Plan** tab).
2. 🎨 UX Designer writes a design spec — palette, layout, interaction details
   (appended below the plan in the **Plan** tab).
3. 🔨 Builder writes the app as one or more static files.
4. 🔍 Reviewer verdicts it against plan *and* spec — on **fail**, the Builder
   gets the feedback and tries again (up to 3 iterations).
5. 🚢 The finished product renders live in the **Preview** tab. Download it
   with the ⬇️ button — a single HTML file, or a zip when the Builder split
   the app into several files.

**The IDE workflow:** you can also ship from the terminal — the product's
files land in a directory you can iterate on with your IDE agent:

```bash
uv run python cli.py "a pomodoro timer with a session log" -o ./pomodoro
```

## 3. Poke at the seams

Each teammate is a real, separately-addressable service. Prove it:

```bash
# The Planner's A2A business card:
curl -s http://localhost:8001/a2a/agent/.well-known/agent-card.json | python3 -m json.tool
```

That agent card — name, description, skills, endpoint URL — is everything the
Orchestrator needs to hire this teammate. No shared code, no shared process.

## Checkpoint ✅

- The Studio previewed a working app in the iframe.
- You fetched at least one agent card with `curl`.

Next: [Module 2 — How it works](02-how-it-works.md)
