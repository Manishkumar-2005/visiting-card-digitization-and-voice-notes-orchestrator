"""Central configuration. All secrets are read from environment variables
(or a local .env file in development). Nothing is hard-coded.

In production (Cloud Run / Render / etc.) these are injected via the platform's
secret manager — see README "Secrets Management".
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ---- App ----
    app_name: str = "Visiting Card Orchestrator"
    # Public URL of THIS backend (used to build absolute audio/image URLs that
    # get written into Google Sheets). e.g. https://my-backend.run.app
    public_base_url: str = "http://localhost:8000"
    # Comma-separated list of allowed CORS origins for the React frontend.
    cors_origins: str = "https://visiting-card-digitization-and-voic-orpin.vercel.app,http://localhost:5173,http://localhost:3000"
    media_dir: str = "media"

    # ---- Anthropic (Vision extraction + agent reasoning) ----
    anthropic_api_key: Optional[str] = None
    # Override if your key doesn't have access to the default model.
    anthropic_model: str = "claude-opus-4-8"

    # ---- MongoDB (chat sessions, message history, agent checkpoints) ----
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "visiting_cards"

    # ---- Google Sheets ----
    # Path to a service-account JSON file, OR provide the JSON inline via
    # GOOGLE_SERVICE_ACCOUNT_JSON (preferred for cloud secret managers).
    google_service_account_file: Optional[str] = None
    google_service_account_json: Optional[str] = None
    google_sheet_id: Optional[str] = None
    google_worksheet_name: str = "Contacts"

    # ---- WhatsApp Business (Meta Cloud API) ----
    whatsapp_token: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    # The manager who should be alerted (E.164, e.g. 919876543210).
    whatsapp_manager_number: Optional[str] = None
    whatsapp_api_version: str = "v21.0"
    # Optional approved template name. If set, a template message is sent
    # (works outside the 24h customer-service window). Otherwise a plain text
    # message is sent (only delivered if the manager messaged you in the last 24h).
    whatsapp_template_name: Optional[str] = None
    whatsapp_template_lang: str = "en_US"

    # ---- Audio transcription (optional) ----
    # "none" -> store audio + URL only (satisfies the core requirement).
    # "openai" -> additionally transcribe with Whisper (needs OPENAI_API_KEY).
    transcription_provider: str = "none"
    openai_api_key: Optional[str] = None

    # ---- Bonus features ----
    # Human-in-the-loop: interrupt the graph for manual confirmation before
    # writing to Sheets / sending WhatsApp.
    human_in_the_loop: bool = False
    # Data enrichment: ask the LLM to guess company website / LinkedIn.
    enable_enrichment: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
