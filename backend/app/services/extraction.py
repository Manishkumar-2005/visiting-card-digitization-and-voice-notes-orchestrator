"""AI data extraction (Task 3).

Uses Anthropic Claude vision to read a visiting-card image and return
structured ContactDetails. Implemented with langchain-anthropic so the same
model config is reused by the agent.
"""
from __future__ import annotations

import base64
from typing import Optional

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from app.config import get_settings
from app.schemas import ContactDetails

_EXTRACTION_INSTRUCTION = (
    "You are an OCR + information-extraction engine for business cards. "
    "Look at the visiting card image and extract the contact details. "
    "Return only the fields you can actually see; leave a field null if it is "
    "not present. Normalise the phone number to digits with an optional leading "
    "'+'. Do not invent data."
)


def _client(model_name: str) -> ChatGroq:
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set — cannot run Groq model."
        )
    return ChatGroq(
        model=model_name,
        api_key=settings.groq_api_key,
        max_tokens=1024 if "vision" in model_name else 2048,
        timeout=60,
    )


def extract_contact_from_image(image_bytes: bytes, media_type: str) -> ContactDetails:
    """Run Llama vision over the card image and return structured fields."""
    settings = get_settings()
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    llm = _client(settings.groq_vision_model).with_structured_output(ContactDetails)
    message = HumanMessage(
        content=[
            {"type": "text", "text": _EXTRACTION_INSTRUCTION},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{b64}"
                }
            },
        ]
    )
    result = llm.invoke([message])
    if isinstance(result, ContactDetails):
        return result
    # with_structured_output may return a dict depending on version.
    return ContactDetails(**dict(result))


def enrich_company(contact: ContactDetails) -> ContactDetails:
    """Bonus (Task: Data Enrichment). Ask the LLM to best-guess the company
    website / LinkedIn from the company name when they are missing.

    This is clearly heuristic — the model proposes likely URLs, it does not
    verify them. Disabled unless ENABLE_ENRICHMENT=true.
    """
    if not contact.company:
        return contact
    if contact.website and contact.linkedin:
        return contact

    settings = get_settings()
    llm = _client(settings.groq_model)
    prompt = (
        "Given the company name below, suggest the single most likely official "
        "website URL and the most likely LinkedIn company page URL. If you are "
        "not reasonably confident, return 'unknown'. Respond as two lines:\n"
        "website: <url-or-unknown>\nlinkedin: <url-or-unknown>\n\n"
        f"Company: {contact.company}"
    )
    try:
        text = llm.invoke([HumanMessage(content=prompt)]).content
        if isinstance(text, list):  # content blocks
            text = " ".join(b.get("text", "") for b in text if isinstance(b, dict))
        website = _parse_line(text, "website")
        linkedin = _parse_line(text, "linkedin")
        if website and not contact.website:
            contact.website = website
        if linkedin and not contact.linkedin:
            contact.linkedin = linkedin
    except Exception:
        # Enrichment is best-effort; never block the main flow.
        pass
    return contact


def _parse_line(text: str, key: str) -> Optional[str]:
    for line in (text or "").splitlines():
        if line.lower().strip().startswith(f"{key}:"):
            value = line.split(":", 1)[1].strip()
            if value and value.lower() != "unknown":
                return value
    return None
