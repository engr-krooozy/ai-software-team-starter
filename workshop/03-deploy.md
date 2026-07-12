# Module 3 — Deploy (20 min)

Goal: the same six services, live on Cloud Run, with proper service-to-service auth.

## 1. Ship it

```bash
./deploy.sh
# optional: give the Builder a stronger model than the flash default
BUILDER_GEMINI_MODEL=gemini-2.5-pro ./deploy.sh
```

While the builds run (~3-4 min per service the first time), read what the
script actually does:

1. Deploys `planner`, `builder`, `reviewer`, `ux-designer` from source with
   **`--no-allow-unauthenticated`** — they are private; only callers presenting
   a valid identity token for the project can reach them.
2. Captures each service's URL and deploys `orchestrator` with the four
   `*_AGENT_CARD_URL` env vars pointing at them. Same container as local —
   only the env changed.
3. Deploys `studio` with **`--allow-unauthenticated`**: the one public door.
4. Gives `orchestrator` and `studio` a **900s request timeout** — they hold one
   request open for a whole pipeline run, and a multi-iteration build outlives
   Cloud Run's 300s default (a silent, hard-to-debug failure otherwise).

```
Internet ──▶ studio (public)
                │ identity token
                ▼
            orchestrator (private)
             │        │        │        │   identity tokens
             ▼        ▼        ▼        ▼
        planner  ux-designer  builder  reviewer   (private)
```

## 2. Verify

Open the URL printed at the end (`https://studio-....run.app`) and ship a
product from your phone if you like — it's a real deployed app now. Or ship
into your workspace from the terminal:

```bash
uv run python cli.py "a habit tracker with streaks" -o ./habits \
  --server https://studio-....run.app
```

Then prove the workers are actually private:

```bash
PLANNER_URL=$(gcloud run services describe planner --region us-central1 --format='value(status.url)')
curl -s -o /dev/null -w "%{http_code}\n" $PLANNER_URL   # 403 — locked
curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  $PLANNER_URL/a2a/agent/.well-known/agent-card.json | head -c 300   # works
```

## 3. Observe

- **Logs**: `gcloud run services logs read orchestrator --region us-central1 --limit 50`
  — look for the `[EscalationChecker] Feedback received:` lines.
- **Console**: Cloud Run → orchestrator → Logs shows the whole team
  conversation across services.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Build fails with permissions error | `gcloud services enable cloudbuild.googleapis.com artifactregistry.googleapis.com` |
| Studio loads but building fails instantly | Check `AGENT_SERVER_URL` on the `studio` service points at the orchestrator URL |
| Orchestrator 500s about agent cards | Redeploy orchestrator — a worker URL changed |
| Builder errors with a model 404 | Your project can't access that Gemini model — swap it without a rebuild: `gcloud run services update builder --update-env-vars GEMINI_MODEL=gemini-3-flash-preview --region us-central1` |
| A long build just stops mid-loop, no error anywhere | A request timed out — check `timeoutSeconds` on `orchestrator` and `studio` is 900, not 300 |
| Two deployments fighting over one project | Don't deploy another lab with a service named `orchestrator` into the same project — it silently rewires the Studio |

Next: [Module 4 — Extend](04-extend.md)
