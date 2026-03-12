"""Contracts for the bot orchestration layer."""

from __future__ import annotations

from typing import Protocol

from sdk.botkit.models import BotCommand, BotRequest, BotResponse, BotSession


class SessionStore(Protocol):
    """Persistence boundary for bot conversation state."""

    def get(self, key: str) -> BotSession | None:
        """Return a stored session for the given key."""

    def save(self, key: str, session: BotSession) -> None:
        """Persist session state."""

    def delete(self, key: str) -> None:
        """Remove session state."""


class IBotAdapter(Protocol):
    """Common bot adapter contract exposed to the orchestrator."""

    bot_id: str
    bot_username: str

    def supports(self, command_name: str) -> bool:
        """Return whether the adapter supports a canonical command."""

    def get_supported_commands(self) -> list[BotCommand]:
        """Return canonical commands supported by this adapter."""

    def execute(self, request: BotRequest) -> BotResponse:
        """Execute the request and return a normalized response."""
