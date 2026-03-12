"""Domain models shared across the SDK."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
import json
from typing import Any, Literal

ChatKind = Literal["private", "group", "supergroup", "channel", "bot"]
InspectionDirection = Literal["latest", "before", "after", "around"]


@dataclass(slots=True)
class User:
    """Telegram user or bot profile."""

    user_id: int
    username: str | None = None
    display_name: str | None = None
    is_bot: bool = False


@dataclass(slots=True)
class Chat:
    """Telegram chat, group, channel, or bot dialog."""

    chat_id: int
    title: str
    username: str | None = None
    kind: ChatKind = "private"
    description: str | None = None
    is_public: bool = False


@dataclass(slots=True)
class Message:
    """Telegram message payload."""

    message_id: int
    chat_id: int
    sender_id: int | None
    text: str
    timestamp: str
    permalink: str | None = None
    media_urls: list[str] = field(default_factory=list)
    buttons: list[list["InlineButton"]] = field(default_factory=list)
    reply_to_message_id: int | None = None
    edit_timestamp: str | None = None
    is_edited: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InlineButton:
    """Normalized inline button metadata from a Telegram message."""

    text: str
    data: bytes | None = None
    url: str | None = None


@dataclass(slots=True)
class MessageButtonRef:
    """Stable reference to an inline button inside a normalized message."""

    row: int
    column: int
    text: str
    data: bytes | None = None
    url: str | None = None

    def to_tool_payload(self) -> dict[str, Any]:
        return {
            "row": self.row,
            "column": self.column,
            "text": self.text,
            "data_hex": self.data.hex() if self.data is not None else None,
            "url": self.url,
        }


@dataclass(slots=True)
class HistoryCursor:
    """Cursor for paginating large chat history inspections."""

    before_message_id: int | None = None
    page_size: int = 20
    query: str | None = None
    direction: InspectionDirection = "before"

    def to_tool_payload(self) -> dict[str, Any]:
        return {
            "before_message_id": self.before_message_id,
            "page_size": self.page_size,
            "query": self.query,
            "direction": self.direction,
            "token": self.to_token(),
        }

    def to_token(self) -> str:
        payload = {
            "before_message_id": self.before_message_id,
            "page_size": self.page_size,
            "query": self.query,
            "direction": self.direction,
        }
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(encoded).decode("ascii")

    @classmethod
    def from_token(cls, token: str) -> "HistoryCursor":
        decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        payload = json.loads(decoded)
        return cls(
            before_message_id=payload.get("before_message_id"),
            page_size=int(payload.get("page_size", 20)),
            query=payload.get("query"),
            direction=payload.get("direction", "before"),
        )


@dataclass(slots=True)
class InspectionPagination:
    """Pagination metadata for history inspection results."""

    page_size: int
    returned_count: int
    scanned_count: int
    has_more_before: bool
    next_before_message_id: int | None = None
    next_cursor: HistoryCursor | None = None
    scan_limit_reached: bool = False

    def to_tool_payload(self) -> dict[str, Any]:
        return {
            "page_size": self.page_size,
            "returned_count": self.returned_count,
            "scanned_count": self.scanned_count,
            "has_more_before": self.has_more_before,
            "next_before_message_id": self.next_before_message_id,
            "next_cursor": (
                self.next_cursor.to_tool_payload() if self.next_cursor is not None else None
            ),
            "scan_limit_reached": self.scan_limit_reached,
        }


@dataclass(slots=True)
class ChatInspection:
    """Normalized chat inspection payload for tooling and debugging."""

    chat: Chat
    recent_messages: list["Message"] = field(default_factory=list)
    direction: InspectionDirection = "latest"
    anchor_message_id: int | None = None
    query: str | None = None
    pagination: InspectionPagination | None = None

    def to_tool_payload(self) -> dict[str, Any]:
        return {
            "chat": _chat_to_payload(self.chat),
            "direction": self.direction,
            "anchor_message_id": self.anchor_message_id,
            "query": self.query,
            "recent_messages": [_message_to_payload(message) for message in self.recent_messages],
            "pagination": (
                self.pagination.to_tool_payload() if self.pagination is not None else None
            ),
        }


@dataclass(slots=True)
class MessageInspection:
    """Inspection payload for a specific message and its nearby context."""

    chat: Chat
    message: "Message"
    buttons: list[MessageButtonRef] = field(default_factory=list)
    context_messages: list["Message"] = field(default_factory=list)
    context_before: list["Message"] = field(default_factory=list)
    context_after: list["Message"] = field(default_factory=list)
    query: str | None = None

    def to_tool_payload(self) -> dict[str, Any]:
        return {
            "chat": _chat_to_payload(self.chat),
            "message": _message_to_payload(self.message),
            "buttons": [button.to_tool_payload() for button in self.buttons],
            "context_messages": [
                _message_to_payload(message) for message in self.context_messages
            ],
            "context_before": [
                _message_to_payload(message) for message in self.context_before
            ],
            "context_after": [
                _message_to_payload(message) for message in self.context_after
            ],
            "query": self.query,
        }


@dataclass(slots=True)
class SearchResults:
    """Combined search response with matched chats and messages."""

    query: str
    chats: list[Chat] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)


@dataclass(slots=True)
class BotStartResult:
    """Result of starting a bot conversation."""

    bot_username: str
    parameter: str | None = None
    welcome_message: str | None = None


@dataclass(slots=True)
class BotSearchResults:
    """Normalized result payload returned by an unofficial search bot."""

    bot_username: str
    query: str
    bot_chat: Chat
    request_message: Message
    reply_messages: list[Message] = field(default_factory=list)
    page_snapshots: list[Message] = field(default_factory=list)
    extracted_usernames: list[str] = field(default_factory=list)
    extracted_links: list[str] = field(default_factory=list)
    extracted_chat_usernames: list[str] = field(default_factory=list)


@dataclass(slots=True)
class KeywordDiscoveryResults:
    """Combined keyword discovery output across official and unofficial sources."""

    query: str
    public_chats: list[Chat] = field(default_factory=list)
    global_messages: list[Message] = field(default_factory=list)
    public_posts: list[Message] = field(default_factory=list)
    fallback_messages: list[Message] = field(default_factory=list)
    bot_results: list[BotSearchResults] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _chat_to_payload(chat: Chat) -> dict[str, Any]:
    return {
        "chat_id": chat.chat_id,
        "title": chat.title,
        "username": chat.username,
        "kind": chat.kind,
        "description": chat.description,
        "is_public": chat.is_public,
    }


def _message_to_payload(message: Message) -> dict[str, Any]:
    return {
        "message_id": message.message_id,
        "chat_id": message.chat_id,
        "sender_id": message.sender_id,
        "text": message.text,
        "timestamp": message.timestamp,
        "permalink": message.permalink,
        "media_urls": list(message.media_urls),
        "reply_to_message_id": message.reply_to_message_id,
        "edit_timestamp": message.edit_timestamp,
        "is_edited": message.is_edited,
        "metadata": dict(message.metadata),
        "buttons": [
            [
                MessageButtonRef(
                    row=row_index,
                    column=column_index,
                    text=button.text,
                    data=button.data,
                    url=button.url,
                ).to_tool_payload()
                for column_index, button in enumerate(button_row)
            ]
            for row_index, button_row in enumerate(message.buttons)
        ],
    }
