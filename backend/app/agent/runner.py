"""Drives one agent turn and normalises the result for the API layer."""
from __future__ import annotations

from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from app.agent.graph import get_graph


def _config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


def _text_from(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(p for p in parts if p)
    return str(content)


def _final_assistant_text(result: dict) -> str:
    """Concatenate the trailing assistant message(s) produced this turn."""
    messages = result.get("messages", [])
    collected = []
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            txt = _text_from(msg.content)
            if txt.strip():
                collected.append(txt.strip())
        elif isinstance(msg, HumanMessage):
            break
    return "\n\n".join(reversed(collected)).strip()


def _shape(result: dict) -> dict:
    interrupts = result.get("__interrupt__")
    if interrupts:
        payload = interrupts[0].value if hasattr(interrupts[0], "value") else interrupts[0]
        return {
            "needs_confirmation": True,
            "confirmation_prompt": payload.get("message")
            if isinstance(payload, dict)
            else str(payload),
            "contact": payload.get("contact") if isinstance(payload, dict) else None,
            "assistant_text": "",
        }
    return {
        "needs_confirmation": False,
        "confirmation_prompt": None,
        "contact": result.get("last_contact") or result.get("extracted_contact"),
        "assistant_text": _final_assistant_text(result),
    }


def run_turn(
    session_id: str,
    text: str,
    image_b64: Optional[str] = None,
    image_media_type: Optional[str] = None,
    audio_url: Optional[str] = None,
    audio_path: Optional[str] = None,
) -> dict:
    graph = get_graph()
    state_in = {
        "messages": [HumanMessage(content=text)],
        "session_id": session_id,
        "pending_image_b64": image_b64,
        "pending_image_media_type": image_media_type,
        "pending_audio_url": audio_url,
        "pending_audio_path": audio_path,
    }
    result = graph.invoke(state_in, _config(session_id))
    return _shape(result)


def resume_turn(session_id: str, decision: dict) -> dict:
    """Resume a graph paused at a human-in-the-loop interrupt."""
    graph = get_graph()
    result = graph.invoke(Command(resume=decision), _config(session_id))
    return _shape(result)
