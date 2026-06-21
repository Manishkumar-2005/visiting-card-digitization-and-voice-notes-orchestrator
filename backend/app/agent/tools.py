"""Agent tools (Task 2: all external integrations are tools within the graph).

Each tool reads what it needs from the injected graph state and returns a
`Command` that (a) updates the state and (b) appends a ToolMessage the agent can
reason over. This keeps the agent the single source of orchestration while the
side-effects (vision, Sheets, WhatsApp, audio) live behind clean tool calls.
"""
from __future__ import annotations

import base64
from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command, interrupt

from app.config import get_settings
from app.schemas import ContactDetails
from app.services import extraction, sheets, transcription, whatsapp


def _tool_msg(content: str, tool_call_id: str) -> ToolMessage:
    return ToolMessage(content=content, tool_call_id=tool_call_id)


@tool
def extract_card_details(
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Extract structured contact details from the visiting-card image the user
    just uploaded. Returns name, phone, email, company and any extra fields."""
    b64 = state.get("pending_image_b64")
    media_type = state.get("pending_image_media_type") or "image/jpeg"
    if not b64:
        return Command(
            update={
                "messages": [
                    _tool_msg(
                        "No visiting-card image is attached to this turn. Ask the "
                        "user to upload one.",
                        tool_call_id,
                    )
                ]
            }
        )

    image_bytes = base64.b64decode(b64)
    contact = extraction.extract_contact_from_image(image_bytes, media_type)

    settings = get_settings()
    if settings.enable_enrichment:
        contact = extraction.enrich_company(contact)

    summary = (
        "Extracted contact details:\n"
        f"- Name: {contact.name or '—'}\n"
        f"- Phone: {contact.phone or '—'}\n"
        f"- Email: {contact.email or '—'}\n"
        f"- Company: {contact.company or '—'}\n"
        f"- Title: {contact.title or '—'}\n"
        f"- Website: {contact.website or '—'}\n"
        f"- LinkedIn: {contact.linkedin or '—'}"
    )
    return Command(
        update={
            "extracted_contact": contact.model_dump(),
            "duplicate_info": None,
            "pending_image_b64": None,  # consume the image
            "messages": [_tool_msg(summary, tool_call_id)],
        }
    )


@tool
def check_duplicate(
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Check whether the just-extracted contact already exists in the Google
    Sheet (matched on phone or email). Use before logging."""
    extracted = state.get("extracted_contact")
    if not extracted:
        return Command(
            update={
                "messages": [
                    _tool_msg("No extracted contact to check yet.", tool_call_id)
                ]
            }
        )
    contact = ContactDetails(**extracted)
    dup = sheets.get_sheets().find_duplicate(contact)
    if dup:
        msg = (
            f"DUPLICATE found: a contact matching this {dup['matched_on']} already "
            f"exists in row {dup['row']} (name: {dup.get('name') or '—'}). Do not log "
            f"a new row."
        )
    else:
        msg = "No duplicate found. Safe to log this contact as a new row."
    return Command(
        update={
            "duplicate_info": dup,
            "messages": [_tool_msg(msg, tool_call_id)],
        }
    )


@tool
def log_contact(
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Append the extracted contact to the Google Sheet as a new row. Refuses if
    the contact is a known duplicate."""
    extracted = state.get("extracted_contact")
    if not extracted:
        return Command(
            update={"messages": [_tool_msg("No contact to log.", tool_call_id)]}
        )

    dup = state.get("duplicate_info")
    if dup:
        # Keep the existing row in context so a later voice note can attach to it.
        return Command(
            update={
                "last_contact": extracted,
                "last_contact_row": dup["row"],
                "messages": [
                    _tool_msg(
                        f"Skipped logging — contact already exists in row {dup['row']}. "
                        f"No duplicate row created.",
                        tool_call_id,
                    )
                ],
            }
        )

    contact = ContactDetails(**extracted)

    # ---- Bonus: Human-in-the-loop confirmation before writing ----
    settings = get_settings()
    if settings.human_in_the_loop:
        decision = interrupt(
            {
                "type": "confirm_log",
                "message": "Please confirm these details before logging to Google "
                "Sheets and notifying the manager.",
                "contact": contact.model_dump(),
            }
        )
        # `decision` is supplied when the graph is resumed (see /confirm endpoint).
        if not decision or not decision.get("approved"):
            return Command(
                update={
                    "messages": [
                        _tool_msg(
                            "User cancelled. Contact was NOT logged and no "
                            "notification was sent.",
                            tool_call_id,
                        )
                    ]
                }
            )
        edited = decision.get("edited_contact")
        if edited:
            contact = ContactDetails(**edited)

    row = sheets.get_sheets().append_contact(contact, state.get("session_id", ""))
    return Command(
        update={
            "extracted_contact": contact.model_dump(),
            "last_contact": contact.model_dump(),
            "last_contact_row": row,
            "messages": [
                _tool_msg(
                    f"Logged contact '{contact.name or '—'}' to Google Sheets at "
                    f"row {row}.",
                    tool_call_id,
                )
            ],
        }
    )


@tool
def send_whatsapp_notification(
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Alert the manager on WhatsApp that a new unique card was just logged."""
    contact = state.get("last_contact")
    if not contact or not state.get("last_contact_row"):
        return Command(
            update={
                "messages": [
                    _tool_msg(
                        "No newly-logged contact to notify about.", tool_call_id
                    )
                ]
            }
        )
    if state.get("duplicate_info"):
        return Command(
            update={
                "messages": [
                    _tool_msg(
                        "Contact was a duplicate — skipping WhatsApp alert.",
                        tool_call_id,
                    )
                ]
            }
        )
    result = whatsapp.send_new_card_alert(
        name=contact.get("name") or "", company=contact.get("company") or ""
    )
    text = "WhatsApp alert sent to manager." if result["ok"] else result["detail"]
    return Command(update={"messages": [_tool_msg(text, tool_call_id)]})


@tool
def attach_voice_note(
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Attach the voice note the user just uploaded to the most recently handled
    contact's row in the Google Sheet (updates the AudioURL, plus transcript if
    transcription is enabled)."""
    audio_url = state.get("pending_audio_url")
    audio_path = state.get("pending_audio_path")
    row = state.get("last_contact_row")

    if not audio_url:
        return Command(
            update={
                "messages": [
                    _tool_msg("No voice note is attached to this turn.", tool_call_id)
                ]
            }
        )
    if not row:
        return Command(
            update={
                "messages": [
                    _tool_msg(
                        "There is no contact in context to attach this voice note "
                        "to. Ask the user to upload a visiting card first.",
                        tool_call_id,
                    )
                ]
            }
        )

    transcript = transcription.transcribe(audio_path) if audio_path else ""
    sheets.get_sheets().update_audio(row, audio_url, transcript)

    detail = f"Attached the voice note to the contact in row {row}."
    if transcript and not transcript.startswith("[transcription failed"):
        detail += f' Transcript: "{transcript[:200]}"'
    return Command(
        update={
            "pending_audio_url": None,
            "pending_audio_path": None,
            "messages": [_tool_msg(detail, tool_call_id)],
        }
    )


ALL_TOOLS = [
    extract_card_details,
    check_duplicate,
    log_contact,
    send_whatsapp_notification,
    attach_voice_note,
]
