"""Local media storage that serves uploaded images/audio over HTTP.

The audio URL written into Google Sheets is built from PUBLIC_BASE_URL, so it
is a real, clickable link. For production you would swap this for GCS / S3 —
the interface (`save_upload` -> public URL) stays the same. See README.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Tuple

from app.config import get_settings

_settings = get_settings()
_MEDIA_ROOT = Path(_settings.media_dir)
_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def save_bytes(data: bytes, original_filename: str, subdir: str) -> Tuple[str, str]:
    """Persist raw bytes. Returns (absolute_path, public_url)."""
    ext = Path(original_filename or "").suffix or ".bin"
    name = f"{uuid.uuid4().hex}{ext}"
    folder = _MEDIA_ROOT / subdir
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    with open(path, "wb") as f:
        f.write(data)
    public_url = f"{_settings.public_base_url.rstrip('/')}/media/{subdir}/{name}"
    return str(path), public_url


def media_root() -> str:
    return str(_MEDIA_ROOT)
