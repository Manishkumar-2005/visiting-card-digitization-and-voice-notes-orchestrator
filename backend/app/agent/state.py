"""Conversation state for the single LangGraph agent (Task 2).

`messages` carries the chat history (reduced with add_messages). The remaining
keys carry per-turn context: the pending uploaded media, the most recent
extraction, duplicate status, and a reference to the last contact's Google
Sheet row — this is what lets a *later* voice note attach to the *correct*
contact entry.
"""
from __future__ import annotations

from typing import Annotated, Optional, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    session_id: str

    # Pending media for the current turn (set by the API before invoking).
    pending_image_b64: Optional[str]
    pending_image_media_type: Optional[str]
    pending_audio_url: Optional[str]
    pending_audio_path: Optional[str]

    # Working memory produced by the tools.
    extracted_contact: Optional[dict]
    duplicate_info: Optional[dict]
    last_contact: Optional[dict]
    last_contact_row: Optional[int]
