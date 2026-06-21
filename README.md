# 📇 Visiting Card Digitization & Voice Notes Orchestrator

An end-to-end system that digitizes physical visiting cards through a **Chat UI**.
A **single LangGraph agent** orchestrates the whole workflow: it extracts contact
details from a card image with Claude vision, deduplicates and logs them to
**Google Sheets**, alerts a manager over the **WhatsApp Business API**, and later
attaches **voice notes** to the correct contact.

> Built for the AI Engineer assignment. See [`PROJECT_OVERVIEW.md`](./PROJECT_OVERVIEW.md)
> for the problem statement, what it solves, and how.

---

## ✨ Features (maps 1:1 to the assignment tasks)

| Task | Feature | Where |
|---|---|---|
| 1. Chat UI | React chat with image upload, voice recording, multiple sessions | `frontend/` |
| 2. Single LangGraph agent | One `StateGraph` agent; all integrations are tools/nodes; per-session state via checkpointer | `backend/app/agent/` |
| 3. AI extraction | Claude vision → structured `ContactDetails` (name, phone, email, company, …) | `backend/app/services/extraction.py` |
| 4. Google Sheets + dedup | Sheets as the DB; duplicates matched on phone/email; handled gracefully in the chat | `backend/app/services/sheets.py` |
| 5. Voice handling | Audio stored & served (clickable URL), transcribed (optional), attached to the right row | `agent/tools.py`, `services/transcription.py` |
| 6. WhatsApp | Meta Cloud API alert on each unique card | `backend/app/services/whatsapp.py` |
| 7. Cloud deploy | Dockerized backend + frontend, docker-compose, secret management | `*/Dockerfile`, `docker-compose.yml` |
| Bonus | Human-in-the-loop interrupt + confirmation card; company website/LinkedIn enrichment | `agent/tools.py`, `services/extraction.py` |

**Stack:** LangGraph · FastAPI (Python) · React (Vite) · MongoDB · Anthropic Claude
(vision + reasoning) · Google Sheets API · WhatsApp Business API.

---

## 🏗️ Architecture

```
                        ┌──────────────────────────────────────────────┐
  React Chat UI         │                FastAPI backend               │
  (image / audio /  ──▶ │  /api/sessions/{id}/chat  (multipart upload) │
   text, sessions)      │            │                                 │
                        │            ▼                                 │
                        │   ┌──────────────────────────────────────┐   │
                        │   │     SINGLE LangGraph Agent           │   │
                        │   │  agent(LLM)  ⇄  tools (ToolNode)     │   │
                        │   │                                      │   │
                        │   │  Tools:                              │   │
                        │   │   • extract_card_details  ─▶ Claude  │   │
                        │   │   • check_duplicate       ─▶ Sheets  │   │
                        │   │   • log_contact           ─▶ Sheets  │   │
                        │   │   • send_whatsapp_...     ─▶ WhatsApp │   │
                        │   │   • attach_voice_note     ─▶ Sheets  │   │
                        │   │                                      │   │
                        │   │  State (checkpointer = MongoDB):     │   │
                        │   │   messages, last_contact_row, ...    │   │
                        │   └──────────────────────────────────────┘   │
                        │   MongoDB: sessions + chat transcript        │
                        │   /media : serves uploaded images & audio    │
                        └──────────────────────────────────────────────┘
```

**Why a checkpointer matters:** each chat session is a LangGraph `thread_id`. The
agent persists `last_contact_row` in its state, so when a voice note arrives in a
later request the agent already knows which Google Sheet row to update — this is
the "link the voice note to the right contact" requirement.

The agent loop: `agent → (tools_condition) → tools → agent → … → END`. The LLM
decides which tools to call and in what order based on the system prompt and the
user's latest action (card image vs. voice note vs. text).

---

## 🔑 Environment Variables

Copy the templates and fill them in:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env   # optional for local dev
```

### Backend (`backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | Claude key (vision extraction + agent). |
| `ANTHROPIC_MODEL` | — | Defaults to `claude-opus-4-8`; override if your key lacks access. |
| `MONGODB_URI` | ✅ | `mongodb://mongo:27017` (compose) or an **Atlas M0** URI. |
| `MONGODB_DB` | — | Defaults to `visiting_cards`. |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | ✅* | Full service-account JSON (one line). Preferred for cloud. |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | ✅* | …or a path to the JSON file (use one of the two). |
| `GOOGLE_SHEET_ID` | ✅ | The spreadsheet ID (from its URL). |
| `GOOGLE_WORKSHEET_NAME` | — | Defaults to `Contacts` (auto-created). |
| `WHATSAPP_TOKEN` | ➖ | Meta Cloud API access token. |
| `WHATSAPP_PHONE_NUMBER_ID` | ➖ | Sender phone-number ID. |
| `WHATSAPP_MANAGER_NUMBER` | ➖ | Manager number (E.164, no `+`, e.g. `919876543210`). |
| `WHATSAPP_TEMPLATE_NAME` | ➖ | Optional approved template (works outside the 24h window). |
| `PUBLIC_BASE_URL` | ✅ | Public URL of the backend; used to build audio/image links saved in Sheets. |
| `CORS_ORIGINS` | ✅ | Comma-separated allowed frontend origins. |
| `TRANSCRIPTION_PROVIDER` | — | `none` (default) or `openai` (needs `OPENAI_API_KEY`). |
| `HUMAN_IN_THE_LOOP` | — | `true` enables the confirmation interrupt (bonus). |
| `ENABLE_ENRICHMENT` | — | `true` enables website/LinkedIn enrichment (bonus). |

\* Provide **either** `GOOGLE_SERVICE_ACCOUNT_JSON` **or** `GOOGLE_SERVICE_ACCOUNT_FILE`.
➖ WhatsApp is optional to *run*; required for the Task 6 demo. If unset, the agent
skips the alert gracefully.

### Frontend (`frontend/.env`)

| Variable | Description |
|---|---|
| `VITE_API_BASE_URL` | Backend base URL (default `http://localhost:8000`). |

---

## 🚀 Run locally

### Option A — Docker Compose (recommended, one command)

```bash
cp backend/.env.example backend/.env   # then fill in the secrets
docker compose up --build
```

- Frontend → http://localhost:3000
- Backend  → http://localhost:8000  (Swagger docs at `/docs`)
- MongoDB  → localhost:27017 (containerized)

### Option B — Run each service by hand

**1. MongoDB** — run locally or use an Atlas M0 URI in `.env`.

**2. Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**3. Frontend**
```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

---

## 🧪 How to test

1. Open the UI, click **+ New** to start a session.
2. Click **📷** and upload a visiting-card image. The agent will reply with the
   extracted details and confirm it logged them to Google Sheets + sent the
   WhatsApp alert. **Check your sheet** — a new row appears.
3. Upload the **same card again** → the agent tells you it's a duplicate and does
   **not** create a second row.
4. Click **🎙️**, record a short voice note, stop. The agent attaches the audio
   URL (and transcript if enabled) to that contact's row — **refresh the sheet**
   to see the `AudioURL` column populated.
5. (Bonus) Set `HUMAN_IN_THE_LOOP=true`, restart, upload a card → a confirmation
   card appears before anything is written; **Confirm** or **Cancel**.

API can also be tested directly via Swagger at `http://localhost:8000/docs`.

---

## ☁️ Deployment guide

The backend and frontend are independent containers — deploy them anywhere that
runs Docker. Below: **Render** (simplest) and **GCP Cloud Run**.

### Secrets management (important)
- **Never commit** `.env` or the service-account JSON (`.gitignore` enforces this).
- In the cloud, set each variable as a **platform secret / environment variable**.
- For Google credentials in the cloud, paste the JSON into the single
  `GOOGLE_SERVICE_ACCOUNT_JSON` variable (no file needed) **or** mount it as a
  secret file and point `GOOGLE_SERVICE_ACCOUNT_FILE` at it.

### Render
**Backend (Web Service):** repo = `backend/`, runtime = Docker. Add all backend
env vars in the dashboard. Set `PUBLIC_BASE_URL` to the service's own URL. Add a
persistent disk mounted at `/app/media` if you want audio to survive restarts (or
switch storage to S3/GCS — see below).
**Frontend (Static Site or Docker):** build with
`VITE_API_BASE_URL=https://<your-backend>.onrender.com`.

### GCP Cloud Run
```bash
# Backend
gcloud run deploy vc-backend --source backend \
  --region us-central1 --allow-unauthenticated \
  --set-env-vars "PUBLIC_BASE_URL=https://vc-backend-xxxx.run.app,MONGODB_URI=<atlas-uri>,..." \
  --set-secrets "ANTHROPIC_API_KEY=anthropic:latest,GOOGLE_SERVICE_ACCOUNT_JSON=gsa:latest"

# Frontend
gcloud run deploy vc-frontend --source frontend \
  --region us-central1 --allow-unauthenticated \
  --set-build-env-vars "VITE_API_BASE_URL=https://vc-backend-xxxx.run.app"
```
Use **MongoDB Atlas M0** for the database and **Cloud Run secrets / Secret
Manager** for all keys.

> **Audio storage in the cloud:** local `/media` is fine for a prototype but is
> ephemeral on serverless. `services/storage.py` exposes a single
> `save_bytes() -> (path, public_url)` seam — swap its body for a GCS/S3 upload
> and everything else (including the Sheets audio URL) keeps working.

---

## 🔌 Third-party setup (one-time)

**Google Sheets**
1. Create a Google Cloud project → enable the **Google Sheets API**.
2. Create a **Service Account**, download its JSON key.
3. Create a spreadsheet, copy its ID from the URL, set `GOOGLE_SHEET_ID`.
4. **Share the sheet** with the service account's email (Editor).

**WhatsApp Business (Meta Cloud API)**
1. Create a Meta app → add the **WhatsApp** product.
2. Copy the temporary access token + **Phone number ID** → `WHATSAPP_TOKEN`,
   `WHATSAPP_PHONE_NUMBER_ID`.
3. Add the manager's number as a test recipient → `WHATSAPP_MANAGER_NUMBER`.
4. To message outside the 24h window, create an approved **template** and set
   `WHATSAPP_TEMPLATE_NAME`.

**Anthropic** — get an API key from the Claude console → `ANTHROPIC_API_KEY`.

---

## 📁 Project structure

```
backend/
  app/
    main.py                 FastAPI app, CORS, /media static mount
    config.py               Settings (all secrets via env)
    schemas.py              Pydantic models (ContactDetails, API I/O)
    agent/
      graph.py              The single LangGraph StateGraph + checkpointer
      state.py              Agent state schema
      tools.py              extract / dedupe / log / whatsapp / voice tools
      prompts.py            System prompt (orchestration rules)
      runner.py             Turn driver + interrupt handling
    services/
      extraction.py         Claude vision extraction + enrichment
      sheets.py             Google Sheets + deduplication
      whatsapp.py           WhatsApp Business API
      storage.py            Media storage (swap for S3/GCS)
      transcription.py      Optional Whisper transcription
      mongo.py              Sessions + chat transcript
    routers/chat.py         REST endpoints
  Dockerfile, requirements.txt, .env.example
frontend/
  src/ (App, components, api, styles)
  Dockerfile, nginx.conf, package.json, .env.example
docker-compose.yml
README.md, PROJECT_OVERVIEW.md
```

---

## 📦 Deliverables checklist

- [x] Source code (this repo)
- [x] README: env setup, run/test, deployment, architecture
- [x] `PROJECT_OVERVIEW.md`: problem / what & how it solves
- [ ] **You provide:** live deployed URLs (after deploying with your keys)
- [ ] **You provide:** 3–5 min demo video (script in `PROJECT_OVERVIEW.md`)
```
