"""WhatsApp Business (Meta Cloud API) notification (Task 6).

Triggered after a unique card is successfully logged. Sends to a predefined
manager number. Supports both a plain text message (only delivered inside the
24h customer-service window) and an approved template message (works anytime).
"""
from __future__ import annotations

import requests

from app.config import get_settings


def _build_text(name: str, company: str) -> str:
    who = name or "a new contact"
    where = f" from {company}" if company else ""
    return (
        f"📇 New visiting card logged: *{who}*{where} has been added to the "
        f"contacts sheet."
    )


def send_new_card_alert(name: str, company: str) -> dict:
    """Return {ok, detail}. Never raises — a failed notification must not break
    the logging flow."""
    settings = get_settings()
    if not (settings.whatsapp_token and settings.whatsapp_phone_number_id
            and settings.whatsapp_manager_number):
        return {"ok": False, "detail": "WhatsApp not configured (skipped)."}

    url = (
        f"https://graph.facebook.com/{settings.whatsapp_api_version}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }

    if settings.whatsapp_template_name:
        payload = {
            "messaging_product": "whatsapp",
            "to": settings.whatsapp_manager_number,
            "type": "template",
            "template": {
                "name": settings.whatsapp_template_name,
                "language": {"code": settings.whatsapp_template_lang},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": name or "New contact"},
                            {"type": "text", "text": company or "—"},
                        ],
                    }
                ],
            },
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": settings.whatsapp_manager_number,
            "type": "text",
            "text": {"body": _build_text(name, company)},
        }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code in (200, 201):
            return {"ok": True, "detail": "WhatsApp alert sent."}
        return {
            "ok": False,
            "detail": f"WhatsApp API error {resp.status_code}: {resp.text[:300]}",
        }
    except requests.RequestException as exc:
        return {"ok": False, "detail": f"WhatsApp request failed: {exc}"}
