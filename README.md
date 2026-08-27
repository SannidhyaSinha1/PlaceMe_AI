# 🎯 PlaceMe AI

Reads the placement emails already sitting in your college Gmail and turns each
one into a clean company listing — role, type, stipend, location, deadline,
skills and the eligibility bar the email stated.

That is the whole app. Connect Gmail, hit sync, browse the companies.

> Built to run at **₹0/month**: Groq + Gemini (LLMs), Supabase (Postgres),
> Render + Vercel (hosting).

---

## Architecture

```
        React + Redux (Vercel)
                 │  REST + JWT
        ┌────────┴─────────┐
        │   FastAPI API    │  auth + Gmail OAuth, sync, opportunities
        │   (Render)       │
        └────────┬─────────┘
        SQLAlchemy│
        ┌─────────┴────────┐
        │ Supabase Postgres│  users (encrypted Gmail tokens) + opportunities
        └──────────────────┘
```

### The pipeline (per email)

```
Gmail (read-only, one sender)
  → extract  LangChain → Groq, Gemini fallback → PydanticOutputParser
  → upsert   dedup by Gmail message id, never re-parsed once stored
  → list     GET /opportunities
```

The extractor **degrades gracefully**: with no LLM keys it falls back to regex
and keyword heuristics, so the whole UI works offline. `/health` reports which
path is live (`llm` = a provider client that actually built, `llm_stats` =
per-provider call/failure counters since boot).

---

## Repository layout

```
backend/
  fastapi_app/   API — core (config/db/security), routers, models, services
  ai_agents/     llm_client (Groq → Gemini fallback) + email_extractor
frontend/        React + Redux Toolkit + Tailwind (Vite)
docker-compose.yml  render.yaml  .github/workflows/ci-cd.yml
```

### API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/auth/register`, `/auth/login` | account that holds the Gmail tokens |
| `GET`  | `/auth/me` | current user + `gmail_connected` |
| `GET`  | `/auth/gmail/connect` → `/auth/gmail/callback` | OAuth consent flow |
| `POST` | `/gmail/sync` | fetch new emails, parse each into an opportunity |
| `GET`  | `/opportunities` | list, with `type` / `search` / `upcoming` / `sort` |
| `GET`  | `/opportunities/{id}` | one company's parsed details |
| `GET`  | `/opportunities/{id}/email` | the original Gmail message |

---

## Quickstart (local, zero keys required)

### 1. Backend API
```bash
cd backend && python3.12 -m venv .venv && source .venv/bin/activate && pip install -r fastapi_app/requirements.txt && uvicorn fastapi_app.main:app --reload --port 8000
```
Boots on `./placementor.db` (SQLite) at http://localhost:8000/docs.

### 2. Frontend
```bash
cd frontend && npm install && npm run dev
```
→ http://localhost:3000 (`VITE_API_URL` defaults to `http://localhost:8000`).

Or run both with Docker: `docker compose up --build`.

---

## Enabling the free services

Copy `.env.example` → `.env` and fill in what you want. Each block is optional.

| Feature | Keys | Get them (free) |
|---|---|---|
| Postgres | `SUPABASE_DB_URL` | supabase.com (else local SQLite) |
| LLM parsing | `GROQ_API_KEY` (+ `GEMINI_API_KEY` fallback) | console.groq.com/keys |
| Gmail sync | `GOOGLE_CLIENT_ID/SECRET` | console.cloud.google.com (enable Gmail API) |

Notes:
- **Which mailbox, which emails**: `PLACEMENT_EMAIL_SENDER` restricts the sync
  to one sender; `PLACEMENT_EMAIL_SINCE` (default `180d`) caps how far back.
- **Groq rate limits** are retried with exponential backoff, then fall back to
  Gemini automatically. Pin models with `GROQ_MODEL` / `GEMINI_MODEL` — a
  retired model id is the usual cause of a silent drop to heuristics.
- **Gmail tokens are encrypted at rest** (Fernet, `TOKEN_ENCRYPTION_KEY`).
- **Already-synced emails are never re-parsed**, so a rate-limited LLM can't
  overwrite good rows with a heuristic guess.

---

## Deployment

- **Frontend → Vercel**: import `frontend/`, set `VITE_API_URL` to your Render
  API URL. `vercel.json` handles SPA routing.
- **Backend → Render**: `render.yaml` defines the FastAPI service. Create a
  `placementor-env` env group with the `.env` keys.
- **CI/CD**: `.github/workflows/ci-cd.yml` runs backend + frontend checks on
  every push and triggers the Render deploy hook + a Vercel deploy on `main`.
