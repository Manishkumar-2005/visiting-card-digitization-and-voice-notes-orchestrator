"""Optional audio transcription (Task 5 enhancement).

Core requirement: the audio must be processed so it is *accessible* and its URL
stored in the sheet. Storing + serving the file (storage.py) satisfies that.

If TRANSCRIPTION_PROVIDER=openai and OPENAI_API_KEY is set, we additionally
transcribe the audio with Whisper and store the transcript in the sheet. The
provider is pluggable — add others here.
"""
from __future__ import annotations

from app.config import get_settings


def transcribe(audio_path: str) -> str:
    """Return a transcript string, or "" if transcription is disabled/unavailable."""
    settings = get_settings()
    if settings.transcription_provider == "openai" and settings.openai_api_key:
        return _transcribe_openai(audio_path, settings.openai_api_key)
    return ""


def _transcribe_openai(audio_path: str, api_key: str) -> str:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        with open(audio_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1", file=f
            )
        return getattr(result, "text", "") or ""
    except Exception as exc:  # never break the flow on transcription errors
        return f"[transcription failed: {exc}]"
