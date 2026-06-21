"""MongoDB access layer: chat sessions and message history.

The LangGraph agent's *conversation state* is persisted separately by a
checkpointer (see agent/graph.py). This module stores the user-facing
session list and the rendered message transcript so the React UI can
reload past conversations.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pymongo import MongoClient, DESCENDING

from app.config import get_settings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Mongo:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = MongoClient(settings.mongodb_uri)
        self._db = self._client[settings.mongodb_db]
        self.sessions = self._db["sessions"]
        self.messages = self._db["messages"]
        # Helpful indexes (idempotent).
        self.messages.create_index([("session_id", 1), ("created_at", 1)])
        self.sessions.create_index([("updated_at", DESCENDING)])

    # ---- Sessions ----
    def create_session(self, title: str = "New chat") -> dict:
        session_id = str(uuid.uuid4())
        doc = {
            "session_id": session_id,
            "title": title,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        self.sessions.insert_one(doc)
        return doc

    def list_sessions(self) -> list[dict]:
        out = []
        for s in self.sessions.find().sort("updated_at", DESCENDING):
            out.append(
                {
                    "session_id": s["session_id"],
                    "title": s.get("title", "Chat"),
                    "created_at": s.get("created_at", ""),
                    "updated_at": s.get("updated_at", ""),
                    "message_count": self.messages.count_documents(
                        {"session_id": s["session_id"]}
                    ),
                }
            )
        return out

    def get_session(self, session_id: str) -> Optional[dict]:
        return self.sessions.find_one({"session_id": session_id}, {"_id": 0})

    def touch_session(self, session_id: str, title: Optional[str] = None) -> None:
        update = {"updated_at": _now_iso()}
        if title:
            update["title"] = title
        self.sessions.update_one({"session_id": session_id}, {"$set": update})

    # ---- Messages ----
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        kind: str = "text",
        media_url: Optional[str] = None,
    ) -> dict:
        doc = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "kind": kind,
            "media_url": media_url,
            "created_at": _now_iso(),
        }
        self.messages.insert_one(doc)
        self.touch_session(session_id)
        return doc

    def list_messages(self, session_id: str) -> list[dict]:
        out = []
        for m in self.messages.find({"session_id": session_id}).sort("created_at", 1):
            out.append(
                {
                    "role": m["role"],
                    "content": m["content"],
                    "kind": m.get("kind", "text"),
                    "media_url": m.get("media_url"),
                    "created_at": m.get("created_at"),
                }
            )
        return out


_mongo: Optional[Mongo] = None


def get_mongo() -> Mongo:
    global _mongo
    if _mongo is None:
        _mongo = Mongo()
    return _mongo
