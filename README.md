# 🎯 PlaceMentor AI

AI-powered placement tracking for college students. PlaceMentor connects to a
student's college Gmail, auto-extracts placement / internship / hackathon /
competition opportunities, checks eligibility, and generates tailored resumes,
cover letters, and company research — all on **free / open-source tiers**.

> Built to run at **₹0/month**: Groq + Gemini (LLMs), HuggingFace + FAISS
> (local AI), Supabase + MongoDB Atlas (DBs), Upstash (Redis), Cloudinary
> (storage), Tavily (search), Render + Vercel (hosting).

---

## Architecture

```
        React + Redux (Vercel)
                 │  REST + JWT
        ┌────────┴─────────┐
        │   FastAPI API    │  students: auth, profile, opportunities,
        │   (Render)       │  applications, AI, analytics, Gmail sync
        └───┬─────────┬────┘
   SQLAlchemy│         │motor
        ┌────┴───┐ ┌───┴─────────┐
        │Supabase│ │MongoDB Atlas│  raw emails, AI content, company reports
        │Postgres│ └─────────────┘
        └────┬───┘
             │ (same DB, managed=False)
        ┌────┴───────────┐
        │ Django + DRF   │  placement staff: manual uploads, announcements,
        │ admin (Render) │  engagement analytics — SimpleJWT
        └────────────────┘

  Celery worker + beat (Render)  ── Upstash Redis broker
     every 30m: Gmail sync → AI pipeline   every 1h: deadline reminders (SMTP)
```

The **FastAPI** and **Django** services share one relational database
(`db/schema.sql` is the source of truth). FastAPI owns the schema via
SQLAlchemy; Django maps the same tables with `managed=False`.

### AI pipeline (per new email)
`extract` (LangChain + Groq + PydanticOutputParser) → `classify`
(bart-large-mnli zero-shot, Groq fallback <0.7) → upsert opportunity →
`eligibility` (hard rules + XGBoost) → fan-out: company research
(Tavily + FAISS + RetrievalQA), resume optimizer (deterministic ATS score),
cover letter (Groq → ReportLab → Cloudinary) → schedule reminders → notify.

Every external integration **degrades gracefully**: with no API keys the app
boots on SQLite, uses regex/keyword heuristics instead of LLMs, stores files
locally, and skips email — so you can develop the whole UI offline.

---

## Repository layout

```
backend/
  fastapi_app/   FastAPI student API (core, routers, models, services, tasks)
  ai_agents/     LLM client, extractor, classifier, researcher, optimizer, ...
  ml_models/     XGBoost eligibility model + synthetic data generator
  analytics/     pandas stats + matplotlib base64 charts
  admin_portal/  Django + DRF admin (SimpleJWT)
frontend/        React + Redux Toolkit + Tailwind + Recharts (Vite)
db/schema.sql    Shared Postgres schema
docker-compose.yml  render.yaml  .github/workflows/ci-cd.yml
```

---

## Quickstart (local, zero keys required)

### 1. Backend API
```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r fastapi_app/requirements-core.txt   # or requirements.txt for full AI
uvicorn fastapi_app.main:app --reload --port 8000
# → http://localhost:8000/docs
```
Boots on `./placementor.db` (SQLite). Register, build a profile, upload a
resume PDF, create opportunities, check eligibility, generate cover letters —
all work offline.

### 2. Frontend
```bash
cd frontend
npm install
cp .env.example .env      # VITE_API_URL defaults to http://localhost:8000
npm run dev               # → http://localhost:3000
```

### 3. Admin portal (optional)
```bash
cd backend/admin_portal
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 8001   # /admin and /api/...
```

### 4. Background jobs (optional, needs Redis)
```bash
# from backend/ with the venv active
celery -A fastapi_app.tasks.celery_app worker --loglevel=info
celery -A fastapi_app.tasks.celery_app beat   --loglevel=info
```

Or run everything with Docker: `docker compose up --build`.

---

## Enabling the free services

Copy `.env.example` → `.env` and fill in what you want. Each block is optional.

| Feature | Keys | Get them (free) |
|---|---|---|
| Postgres | `SUPABASE_DB_URL` | supabase.com → run `db/schema.sql` |
| Documents | `MONGO_URI` | cloud.mongodb.com (M0) |
| LLM | `GROQ_API_KEY` (+ `GEMINI_API_KEY` fallback) | console.groq.com/keys |
| Web search | `TAVILY_API_KEY` | tavily.com |
| Storage | `CLOUDINARY_*` | cloudinary.com |
| Redis | `UPSTASH_REDIS_URL` | console.upstash.com |
| Gmail sync | `GOOGLE_CLIENT_ID/SECRET` | console.cloud.google.com (enable Gmail API) |
| Reminders | `GMAIL_ADDRESS` + `GMAIL_APP_PASSWORD` | myaccount.google.com/apppasswords |
| Admins | `ADMIN_EMAILS` | comma-separated; these accounts get admin rights |

Notes:
- **Upstash needs SSL** — `rediss://` URLs auto-enable `ssl_cert_reqs=CERT_NONE`.
- **Groq rate limits** are retried with exponential backoff, then fall back to
  Gemini automatically.
- **Company research is cached** in MongoDB by company name to save Tavily quota;
  FAISS indexes persist under `faiss_indexes/`.

---

## Deployment

- **Frontend → Vercel**: import `frontend/`, set `VITE_API_URL` to your Render
  API URL. `vercel.json` handles SPA routing.
- **Backend → Render**: `render.yaml` defines 4 services (FastAPI, Django,
  Celery worker, Celery beat). Create a `placementor-env` env group with the
  `.env` keys.
- **CI/CD**: `.github/workflows/ci-cd.yml` runs backend/django/frontend checks
  on every push and triggers Render deploy hooks + a Vercel deploy on `main`.

---

## Verified end-to-end

The stack was exercised live: JWT register/login, profile + resume PDF parsing,
admin-guarded opportunity creation, eligibility (hard-rule fails + XGBoost
scoring), application tracker with deadline reminders, deterministic ATS
scoring, ReportLab cover-letter PDFs, base64 matplotlib charts, and the Django
admin writing announcements/opportunities that the FastAPI service serves to
students from the shared database.
