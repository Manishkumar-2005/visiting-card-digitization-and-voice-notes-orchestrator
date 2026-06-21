"""Chat API: sessions, message/upload, and human-in-the-loop confirmation.

A single multipart endpoint (`/chat`) handles text, image and audio so the React
UI can send any combination. The endpoint persists the user-visible transcript
to MongoDB and delegates all orchestration to the LangGraph agent.
"""
from __future__ import annotations

import base64
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.agent import runner
from app.schemas import (
    ChatMessageOut,
    ChatResponse,
    ConfirmRequest,
    SessionCreateResponse,
    SessionSummary,
)
from app.services import storage
from app.services.mongo import get_mongo

router = APIRouter(prefix="/api", tags=["chat"])


# ---------- Sessions (multiple chat sessions, Task 1) ----------

@router.post("/sessions", response_model=SessionCreateResponse)
def create_session() -> SessionCreateResponse:
    doc = get_mongo().create_session()
    return SessionCreateResponse(session_id=doc["session_id"], title=doc["title"])


@router.get("/sessions", response_model=list[SessionSummary])
def list_sessions() -> list[SessionSummary]:
    return [SessionSummary(**s) for s in get_mongo().list_sessions()]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
def get_messages(session_id: str) -> list[ChatMessageOut]:
    if not get_mongo().get_session(session_id):
        raise HTTPException(404, "Session not found")
    return [ChatMessageOut(**m) for m in get_mongo().list_messages(session_id)]


# ---------- Chat (text + image + audio) ----------

@router.post("/sessions/{session_id}/chat", response_model=ChatResponse)
async def chat(
    session_id: str,
    text: str = Form(""),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
) -> ChatResponse:
    mongo = get_mongo()
    if not mongo.get_session(session_id):
        raise HTTPException(404, "Session not found")

    image_b64 = None
    image_media_type = None
    audio_url = None
    audio_path = None

    # ---- Handle uploaded image ----
    if image is not None:
        raw = await image.read()
        image_media_type = image.content_type or "image/jpeg"
        image_b64 = base64.standard_b64encode(raw).decode("utf-8")
        _, media_url = storage.save_bytes(raw, image.filename or "card.jpg", "images")
        mongo.add_message(
            session_id,
            role="user",
            content=text or "Uploaded a visiting card.",
            kind="image",
            media_url=media_url,
        )

    # ---- Handle uploaded audio ----
    if audio is not None:
        raw = await audio.read()
        audio_path, audio_url = storage.save_bytes(
            raw, audio.filename or "note.webm", "audio"
        )
        mongo.add_message(
            session_id,
            role="user",
            content=text or "Uploaded a voice note.",
            kind="audio",
            media_url=audio_url,
        )

    # ---- Plain text message ----
    if image is None and audio is None:
        if not text.strip():
            raise HTTPException(400, "Empty message")
        mongo.add_message(session_id, role="user", content=text, kind="text")

    # ---- Build the instruction for the agent ----
    if image is not None:
        agent_text = text or (
            "I've uploaded a visiting card image. Please digitize it: extract the "
            "details, check for duplicates, log it to the sheet, and notify the manager."
        )
    elif audio is not None:
        agent_text = text or (
            "I've uploaded a voice note. Please attach it to the contact we just added."
        )
    else:
        agent_text = text

    result = await run_in_threadpool(
        runner.run_turn,
        session_id,
        agent_text,
        image_b64,
        image_media_type,
        audio_url,
        audio_path,
    )

    return _finalize(session_id, result)


@router.post("/sessions/{session_id}/confirm", response_model=ChatResponse)
async def confirm(session_id: str, body: ConfirmRequest) -> ChatResponse:
    """Resume a human-in-the-loop interrupt (bonus). The user approves or rejects
    (optionally with edited fields) before the contact is written + notified."""
    mongo = get_mongo()
    if not mongo.get_session(session_id):
        raise HTTPException(404, "Session not found")

    decision = {"approved": body.approved}
    if body.edited_contact is not None:
        decision["edited_contact"] = body.edited_contact.model_dump()

    mongo.add_message(
        session_id,
        role="user",
        content="✅ Confirmed" if body.approved else "✋ Cancelled",
        kind="text",
    )
    result = await run_in_threadpool(runner.resume_turn, session_id, decision)
    return _finalize(session_id, result)


# ---------- Helpers ----------

def _finalize(session_id: str, result: dict) -> ChatResponse:
    mongo = get_mongo()
    out_messages: list[ChatMessageOut] = []

    if result.get("needs_confirmation"):
        prompt = result.get("confirmation_prompt") or "Please confirm before saving."
        mongo.add_message(session_id, role="assistant", content=prompt, kind="text")
        out_messages.append(ChatMessageOut(role="assistant", content=prompt))
    else:
        assistant_text = result.get("assistant_text") or "Done."
        mongo.add_message(
            session_id, role="assistant", content=assistant_text, kind="text"
        )
        out_messages.append(ChatMessageOut(role="assistant", content=assistant_text))

        # Auto-title the session from the contact's name on the first card.
        contact = result.get("contact") or {}
        session = mongo.get_session(session_id)
        if session and session.get("title") in (None, "New chat") and contact.get("name"):
            mongo.touch_session(session_id, title=contact["name"])

    return ChatResponse(
        session_id=session_id,
        messages=out_messages,
        contact=result.get("contact"),
        needs_confirmation=bool(result.get("needs_confirmation")),
        confirmation_prompt=result.get("confirmation_prompt"),
    )
