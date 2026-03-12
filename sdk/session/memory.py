"""In-memory bot session store for local usage and unit tests."""

from __future__ import annotations

from sdk.botkit.models import BotSession


class InMemorySessionStore:
    """Simple session store backed by a Python dictionary."""

    def __init__(self) -> None:
        self._sessions: dict[str, BotSession] = {}

    def get(self, key: str) -> BotSession | None:
        return self._sessions.get(key)

    def save(self, key: str, session: BotSession) -> None:
        self._sessions[key] = session

    def delete(self, key: str) -> None:
        self._sessions.pop(key, None)
