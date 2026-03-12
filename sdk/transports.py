"""Transport contracts for Telegram backend implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from sdk.models import BotStartResult, Chat, Message, SearchResults, User


class TelegramTransport(ABC):
    """Abstract backend contract for Telegram operations."""

    @abstractmethod
    def connect(self) -> None:
        """Initialize the backend session."""

    @abstractmethod
    def close(self) -> None:
        """Close the backend session."""

    @abstractmethod
    def search_public_chats(self, query: str, limit: int = 20) -> list[Chat]:
        """Search public groups, channels, or bots by text."""

    @abstractmethod
    def search_messages(self, query: str, limit: int = 50) -> SearchResults:
        """Search messages across accessible chats."""

    @abstractmethod
    def search_chat_messages(
        self,
        chat_id: int,
        query: str,
        limit: int = 50,
    ) -> list[Message]:
        """Search messages inside a specific chat."""

    @abstractmethod
    def search_public_posts(self, query: str, limit: int = 50) -> SearchResults:
        """Search public channel posts by keyword."""

    @abstractmethod
    def resolve_username(self, username: str) -> Chat | User:
        """Resolve a Telegram username to a concrete entity."""

    @abstractmethod
    def get_chat(self, chat_id: int) -> Chat:
        """Fetch chat metadata."""

    @abstractmethod
    def get_chat_history(
        self,
        chat_id: int,
        limit: int = 100,
        before_message_id: int | None = None,
    ) -> list[Message]:
        """Fetch chronological history for a chat."""

    @abstractmethod
    def get_message(self, chat_id: int, message_id: int) -> Message:
        """Fetch a single message by chat and message id."""

    @abstractmethod
    def export_message_link(self, chat_id: int, message_id: int) -> str:
        """Create a shareable message link when supported."""

    @abstractmethod
    def send_text(self, chat_id: int, text: str) -> Message:
        """Send a text message to a chat or bot."""

    @abstractmethod
    def start_bot(
        self,
        bot_username: str,
        parameter: str | None = None,
    ) -> BotStartResult:
        """Start a bot conversation."""

    @abstractmethod
    def click_message_button(
        self,
        chat_id: int,
        message_id: int,
        *,
        button_text: str | None = None,
        row: int | None = None,
        column: int | None = None,
        data: bytes | None = None,
    ) -> Message:
        """Click an inline button in a message and return the refreshed message."""
