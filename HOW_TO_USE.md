# 🧭 How to Use — Visiting Card Orchestrator

A step-by-step guide to running and using the app. For architecture and the
deployment guide see [`README.md`](./README.md); for the problem/solution writeup
see [`PROJECT_OVERVIEW.md`](./PROJECT_OVERVIEW.md).

---

## 1. Start the app

The whole stack (MongoDB + backend + frontend) runs with one command from the
project root:

```bash
docker compose up -d
```

Then open:

| What | URL |
|---|---|
| 💬 **Chat UI** (use this) | **http://localhost:3000** |
| 🔧 Backend API docs | http://localhost:8000/docs |
| ❤️ Health check | http://localhost:8000/health |

To stop: `docker compose down`  ·  To watch logs: `docker compose logs -f backend`

> The UI loads and you can click around even before adding API keys. To actually
> process cards you must add the keys in **Step 2**.

---

## 2. Add your keys (one-time)

Open **`backend/.env`** and fill the 3 required secrets (Meta/WhatsApp is
optional). Each is marked `>>> PASTE ... <<<` in the file:

| Key | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com → API Keys |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Google Cloud → Service Account → download JSON → paste it on **one line** |
| `GOOGLE_SHEET_ID` | from your Sheet's URL: `docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit` |
| `WHATSAPP_*` (optional) | https://developers.facebook.com → your app → WhatsApp → API Setup |

**Google one-time setup (important):**
1. Create a Google Cloud project → enable the **Google Sheets API**.
2. Create a **Service Account**, download its JSON key.
3. Create a Google Sheet, copy its **ID** from the URL.
4. **Share the Sheet** (Editor) with the service-account's email — the
   `client_email` value inside the JSON. *Without this the app can't write.*

Apply the keys (reloads only the backend):

```bash
docker compose up -d --force-recreate backend
```

---

## 3. Use the Chat UI

### a) Start a session
Click **➕ New** in the left sidebar. Each session is independent — its own
conversation and its own agent memory. You can have several going at once.

### b) Digitize a visiting card 📷
Click the **📷** button (bottom-left of the composer) and pick a card image.
The agent will:
1. **Extract** the details with Claude vision (name, phone, email, company, …).
2. **Check for duplicates** in your Google Sheet.
3. **Log** a new row (only if it's not a duplicate).
4. **Send a WhatsApp alert** to the manager (if WhatsApp is configured).

It replies in chat with a summary of exactly what it did. **Open your Google
Sheet** — a new row will be there.

### c) Try a duplicate 🔁
Upload the **same card again**. The agent tells you the contact already exists
and does **not** create a second row.

### d) Add a voice note 🎙️
After a card is scanned, click **🎙️**, speak your note, then click **⏹️** to stop.
The recording is uploaded, stored, and its URL is written into that contact's
row (in the `AudioURL` column). Refresh the Sheet to see it. (If you set
`TRANSCRIPTION_PROVIDER=openai` + `OPENAI_API_KEY`, the transcript is added too.)

### e) Plain chat 💬
You can also just type a message and press **Enter** — the agent responds
conversationally and will ask you to upload a card if needed.

---

## 4. Optional: demo the bonus features

**Human-in-the-loop confirmation** — the agent pauses and asks you to confirm
before writing anything:
```bash
# in backend/.env
HUMAN_IN_THE_LOOP=true
```
```bash
docker compose up -d --force-recreate backend
```
Now uploading a card shows a **confirmation card** with the extracted details and
**✅ Confirm / ✋ Cancel** buttons. Nothing is written until you confirm.

**Data enrichment** (already on by default — `ENABLE_ENRICHMENT=true`) — the agent
guesses the company website / LinkedIn from the company name and adds them to the
row.

---

## 5. Quick reference

| Action | Command |
|---|---|
| Start everything | `docker compose up -d` |
| Apply new `.env` keys | `docker compose up -d --force-recreate backend` |
| View backend logs | `docker compose logs -f backend` |
| Stop everything | `docker compose down` |
| Rebuild after code changes | `docker compose up -d --build` |
| Reset the database | `docker compose down -v` (⚠️ deletes Mongo + media volumes) |

---

## 6. Troubleshooting

| Symptom | Fix |
|---|---|
| UI says "Could not reach the backend" | Backend not up — `docker compose logs backend`; confirm http://localhost:8000/health returns `ok`. |
| Card upload errors with auth/401 | `ANTHROPIC_API_KEY` missing or wrong in `backend/.env` → recreate backend. |
| Nothing appears in the Sheet | Sheet not shared with the service-account email, or wrong `GOOGLE_SHEET_ID`. |
| WhatsApp not received | Optional — only works if `WHATSAPP_*` are set; plain-text messages need the manager to have messaged you in the last 24h, otherwise use an approved template (`WHATSAPP_TEMPLATE_NAME`). |
| Mic button does nothing | Browser needs microphone permission; use `http://localhost` (allowed) and click **Allow**. |
| Port already in use | Something else is on 3000/8000/27017 — stop it, or change the port mappings in `docker-compose.yml`. |
