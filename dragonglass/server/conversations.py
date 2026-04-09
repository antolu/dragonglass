from __future__ import annotations

import json
import logging
import pathlib
import time

from dragonglass import paths
from dragonglass.agent import history_to_events
from dragonglass.agent.types import (
    ConversationLoadedEvent,
    ConversationsListEvent,
    _Message,
)

logger = logging.getLogger(__name__)

MAX_TITLE_LENGTH = 40

ConversationSummary = dict[str, str | float]


class ConversationStore:
    def __init__(self) -> None:
        self._current_id: str | None = None

    @property
    def current_id(self) -> str | None:
        return self._current_id

    @current_id.setter
    def current_id(self, value: str | None) -> None:
        self._current_id = value

    @staticmethod
    def get_path(conversation_id: str) -> pathlib.Path:
        return paths.CONVERSATIONS_DIR / f"{conversation_id}.json"

    def save(self, conversation_id: str, history: list[_Message]) -> None:
        path = self.get_path(conversation_id)
        title = "New Chat"
        for msg in history:
            if msg.get("role") == "user" and msg.get("content"):
                content = str(msg["content"])
                title = content[:MAX_TITLE_LENGTH] + (
                    "..." if len(content) > MAX_TITLE_LENGTH else ""
                )
                break

        data = {
            "id": conversation_id,
            "title": title,
            "updated_at": time.time(),
            "history": history,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(
            "conversations: saved id=%s messages=%d title=%r",
            conversation_id,
            len(history),
            title,
        )

    def list_serialized(self) -> list[ConversationSummary]:  # noqa: PLR6301
        conversations: list[ConversationSummary] = []
        for path in paths.CONVERSATIONS_DIR.glob("*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                    conversations.append({
                        "id": str(data["id"]),
                        "title": str(data["title"]),
                        "updated_at": float(data.get("updated_at", 0)),
                    })
            except Exception:
                logger.warning(
                    "conversations: failed to load metadata from %s",
                    path,
                    exc_info=True,
                )
        conversations.sort(key=lambda x: x["updated_at"], reverse=True)
        return conversations

    def load(self, conversation_id: str) -> ConversationLoadedEvent | None:
        path = self.get_path(conversation_id)
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self._current_id = conversation_id
        events = history_to_events(data["history"])
        return ConversationLoadedEvent(id=conversation_id, history=events)

    def get_history(self, conversation_id: str) -> list[_Message] | None:
        path = self.get_path(conversation_id)
        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return data["history"]
        except Exception:
            logger.warning(
                "conversations: failed to read history from %s", path, exc_info=True
            )
            return None

    def delete(self, conversation_id: str) -> None:
        path = self.get_path(conversation_id)
        if path.exists():
            path.unlink()
        if self._current_id == conversation_id:
            self._current_id = None

    def build_list_event(self) -> ConversationsListEvent:
        return ConversationsListEvent(conversations=self.list_serialized())
