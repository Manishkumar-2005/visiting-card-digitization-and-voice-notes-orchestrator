# Project Overview — Visiting Card Digitization & Voice Notes Orchestrator

## The problem

Sales teams at conferences collect stacks of physical visiting cards. Turning
those cards into usable CRM data is slow and error-prone:

- **Manual data entry** — someone re-types every card into a sheet. It's tedious
  and introduces typos.
- **Duplicates** — the same person is met twice (or by two reps), so the same
  contact gets entered multiple times, polluting the database.
- **No context** — a card tells you *who* someone is, but not *why they mattered*
  ("interested in our enterprise plan", "follow up after Q3"). Reps remember
  these as voice notes in the moment, but they're rarely captured against the
  right contact.
- **No real-time visibility** — managers don't know a promising lead was captured
  until much later.

## What this system solves

It removes the friction entirely. A rep just **chats**: upload a photo of the
card, and the system does the rest end-to-end:

1. **Reads the card** with AI vision and extracts structured details (name,
   phone, email, company, title, …).
2. **Prevents duplicates** by checking the existing database before inserting.
3. **Logs the contact** into Google Sheets (a shared, zero-setup "CRM").
4. **Notifies the manager instantly** on WhatsApp that a new lead was captured.
5. **Captures context** — the rep records a voice note that gets attached to that
   exact contact's row, so the "why" lives next to the "who".

The result: a card becomes a clean, deduplicated, annotated CRM record in
seconds, with the manager looped in in real time — no manual typing.

## How it works

The core design choice is a **single LangGraph agent** acting as the brain. Rather
than hard-coding a rigid pipeline, the workflow is expressed as an LLM agent that
**decides which tools to call** based on the conversation and the user's latest
action.

### The agent and its tools

The agent is a `StateGraph` with two nodes — an **LLM node** (Claude, bound to
tools) and a **tool-execution node** — looping until the task is done. Every
external integration is a tool:

| Tool | What it does | Integration |
|---|---|---|
| `extract_card_details` | OCR + structured extraction from the card image | Claude vision |
| `check_duplicate` | Looks for an existing contact by phone/email | Google Sheets |
| `log_contact` | Appends a new row | Google Sheets |
| `send_whatsapp_notification` | Alerts the manager | WhatsApp Business API |
| `attach_voice_note` | Stores audio, transcribes, updates the row | Storage + Sheets |

The **system prompt** encodes the business rules ("extract → check duplicate →
log if new → notify; for a voice note, attach to the last contact"), and the
agent follows them while narrating progress to the user.

### State that links voice notes to the right contact

Each chat session is a LangGraph `thread_id`, and the agent's state is persisted
by a **MongoDB checkpointer**. The state carries `last_contact_row` — the Google
Sheet row of the most recently handled contact. So when a voice note arrives in a
*later* request, the agent already knows which row to update. This is what makes
"add a voice note to the card I just scanned" work seamlessly, and it scales to
**multiple concurrent chat sessions**, each with its own isolated context.

### Deduplication

Before inserting, `check_duplicate` normalizes phone numbers (digits, last 10) and
emails (lowercased) and scans the sheet. A match short-circuits the insert; the
agent tells the user the contact already exists and creates **no** duplicate row —
but still keeps that existing row in context so a voice note can attach to it.

### Human-in-the-loop (bonus)

With `HUMAN_IN_THE_LOOP=true`, the graph **interrupts** right before writing to
Sheets. The UI shows a confirmation card with the extracted details; the user
approves (optionally edited) or cancels. On approval the graph **resumes** exactly
where it paused — a clean demonstration of LangGraph's interrupt/resume.

### Data enrichment (bonus)

With `ENABLE_ENRICHMENT=true`, the agent asks the model to best-guess the
company's website and LinkedIn from the company name and appends them to the row.

## Technology choices & why

- **LangGraph** — gives an explicit, inspectable agent graph with first-class
  state, checkpointing (durable per-session memory), and interrupts (HITL). It's
  the natural fit for "one agent orchestrating several tools with memory".
- **Claude (Anthropic)** — strong vision for reading cards and reliable tool-use
  for orchestration, via a single model config reused across the app.
- **FastAPI** — fast, typed Python API; one multipart endpoint handles text,
  image, and audio so the UI stays simple.
- **Google Sheets** — a shared, human-readable database the sales team can open
  directly; zero schema setup.
- **MongoDB (Atlas M0)** — stores the chat transcript/sessions and backs the
  agent checkpointer.
- **React (Vite)** — a clean chat UI with image upload, in-browser voice
  recording, and a session sidebar.
- **Docker + Cloud Run/Render** — containerized services with secrets injected by
  the platform's secret manager (never committed).

## End-to-end flow (what a demo shows)

1. Upload a card image → agent extracts details, logs to Sheets, WhatsApp alert
   arrives on the manager's phone.
2. Upload the same card again → agent reports a duplicate, no new row.
3. Record a voice note → the contact's Sheet row gets an `AudioURL` (and
   transcript if enabled).

## Suggested demo video script (3–5 min)

1. **Intro (20s):** the problem and the one-agent architecture (show the diagram).
2. **Scan a card (60s):** upload image in the chat; show the agent's reply and the
   **new row** in Google Sheets.
3. **WhatsApp (20s):** show the alert arriving on the phone.
4. **Duplicate (30s):** re-upload the same card; show the agent refusing and **no**
   new row.
5. **Voice note (45s):** record in the UI; refresh Sheets to show the populated
   `AudioURL` (and transcript).
6. **Bonus (30s):** toggle `HUMAN_IN_THE_LOOP`; show the confirmation card and
   approve.
7. **Wrap (20s):** mention deployment (Docker on Cloud Run/Render) and secret
   management.
