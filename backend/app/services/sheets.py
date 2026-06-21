"""Google Sheets integration + deduplication (Task 4).

Google Sheets is used as the primary contact database. Before inserting a new
row we check whether the contact already exists (matched on normalised phone or
email). Voice notes later update the same row (Task 5).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

from app.config import get_settings
from app.schemas import ContactDetails

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Column order in the worksheet. Index in this list + 1 == 1-based column number.
HEADERS = [
    "Timestamp",
    "Name",
    "Phone",
    "Email",
    "Company",
    "Title",
    "Website",
    "LinkedIn",
    "Address",
    "AudioURL",
    "Transcript",
    "SessionID",
]
COL = {name: i + 1 for i, name in enumerate(HEADERS)}


def _normalise_phone(phone: Optional[str]) -> str:
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    # Compare on the last 10 digits to be robust to country-code variations.
    return digits[-10:] if len(digits) >= 10 else digits


def _normalise_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()


class SheetsClient:
    def __init__(self) -> None:
        settings = get_settings()
        if settings.google_service_account_json:
            info = json.loads(settings.google_service_account_json)
            creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
        elif settings.google_service_account_file:
            creds = Credentials.from_service_account_file(
                settings.google_service_account_file, scopes=_SCOPES
            )
        else:
            raise RuntimeError(
                "No Google credentials configured. Set GOOGLE_SERVICE_ACCOUNT_JSON "
                "or GOOGLE_SERVICE_ACCOUNT_FILE."
            )
        if not settings.google_sheet_id:
            raise RuntimeError("GOOGLE_SHEET_ID is not set.")

        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(settings.google_sheet_id)
        try:
            self.ws = spreadsheet.worksheet(settings.google_worksheet_name)
        except gspread.WorksheetNotFound:
            self.ws = spreadsheet.add_worksheet(
                settings.google_worksheet_name, rows=1000, cols=len(HEADERS)
            )
        self._ensure_header()

    def _ensure_header(self) -> None:
        existing = self.ws.row_values(1)
        if existing != HEADERS:
            self.ws.update("A1", [HEADERS])

    # ---- Deduplication ----
    def find_duplicate(self, contact: ContactDetails) -> Optional[dict]:
        """Return the existing record (with its row number) if a contact with the
        same phone or email already exists, else None."""
        target_phone = _normalise_phone(contact.phone)
        target_email = _normalise_email(contact.email)
        if not target_phone and not target_email:
            return None

        records = self.ws.get_all_values()  # includes header at index 0
        for idx, row in enumerate(records[1:], start=2):  # row numbers are 1-based
            row_phone = _normalise_phone(row[COL["Phone"] - 1] if len(row) >= COL["Phone"] else "")
            row_email = _normalise_email(row[COL["Email"] - 1] if len(row) >= COL["Email"] else "")
            if target_phone and row_phone and target_phone == row_phone:
                return {"row": idx, "matched_on": "phone", "name": row[COL["Name"] - 1]}
            if target_email and row_email and target_email == row_email:
                return {"row": idx, "matched_on": "email", "name": row[COL["Name"] - 1]}
        return None

    # ---- Insert ----
    def append_contact(self, contact: ContactDetails, session_id: str) -> int:
        ts = datetime.now(timezone.utc).isoformat()
        row = [
            ts,
            contact.name or "",
            contact.phone or "",
            contact.email or "",
            contact.company or "",
            contact.title or "",
            contact.website or "",
            contact.linkedin or "",
            contact.address or "",
            "",  # AudioURL (filled later by a voice note)
            "",  # Transcript
            session_id,
        ]
        self.ws.append_row(row, value_input_option="USER_ENTERED")
        # The new row is the current last row.
        return len(self.ws.get_all_values())

    # ---- Update (voice note attachment, Task 5) ----
    def update_audio(self, row: int, audio_url: str, transcript: str = "") -> None:
        self.ws.update_cell(row, COL["AudioURL"], audio_url)
        if transcript:
            self.ws.update_cell(row, COL["Transcript"], transcript)


_client: Optional[SheetsClient] = None


def get_sheets() -> SheetsClient:
    global _client
    if _client is None:
        _client = SheetsClient()
    return _client
