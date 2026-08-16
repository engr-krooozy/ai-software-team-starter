# Module 0 — Setup (10 min)

Goal: a GCP project ready for Vertex AI + Cloud Run, and this repo running tools installed.

## 1. Tools

- **uv** (Python package manager): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Google Cloud SDK**: https://cloud.google.com/sdk/docs/install
- **Antigravity** (or any agentic IDE) with this repo opened — you'll use it in Module 4.

> 💡 Cloud Shell / Cloud Shell Editor works too and has `gcloud` preinstalled.

## 2. Project and APIs

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

## 3. Application Default Credentials

The agents call Gemini through Vertex AI using your local credentials:

```bash
gcloud auth application-default login
```

**No GCP billing?** Get an API key from [AI Studio](https://aistudio.google.com/apikey)
instead, copy `.env.example` to `.env`, and set `GEMINI_API_KEY`.

## 4. Install dependencies

```bash
git clone <this-repo> && cd ai-software-team-starter
uv sync
```

## Checkpoint ✅

```bash
gcloud config get-value project     # prints your project id
uv --version                        # prints a version
```

Next: [Module 1 — Meet the team](01-meet-the-team.md)
