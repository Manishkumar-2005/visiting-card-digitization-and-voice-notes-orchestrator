"""Pydantic models shared across the API and the agent."""
from typing import Optional

from pydantic import BaseModel, Field


class ContactDetails(BaseModel):
    """Structured data extracted from a visiting card.

    The four required fields per the assignment are name, phone, email, company.
    The rest are best-effort extras that improve the Google Sheet record.
    """

    name: Optional[str] = Field(None, description="Full name of the person")
    phone: Optional[str] = Field(None, description="Primary phone number")
    email: Optional[str] = Field(None, description="Email address")
    company: Optional[str] = Field(None, description="Company / organisation name")
    title: Optional[str] = Field(None, description="Job title / designation")
    website: Optional[str] = Field(None, description="Company website")
    linkedin: Optional[str] = Field(None, description="LinkedIn profile URL")
    address: Optional[str] = Field(None, description="Postal address")


# ---- API request/response models ----

class SessionCreateResponse(BaseModel):
    session_id: str
    title: str


class SessionSummary(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class ChatMessageOut(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
    kind: str = "text"  # "text" | "image" | "audio"
    media_url: Optional[str] = None
    created_at: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageOut]
    contact: Optional[dict] = None
    needs_confirmation: bool = False
    confirmation_prompt: Optional[str] = None


class ConfirmRequest(BaseModel):
    approved: bool
    # Optional corrected fields supplied by the user during confirmation.
    edited_contact: Optional[ContactDetails] = None
