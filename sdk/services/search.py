"""Search-related SDK services."""

from __future__ import annotations

from sdk.references import resolve_chat_reference
from sdk.transports import TelegramTransport


class SearchService:
    """Search operations exposed by the SDK."""

    def __init__(self, transport: TelegramTransport) -> None:
        self.transport = transport

    def search_public_chats(self, query: str, limit: int = 20):
        return self.transport.search_public_chats(query=query, limit=limit)

    def search_messages(self, query: str, limit: int = 50):
        return self.transport.search_messages(query=query, limit=limit)

    def search_chat_messages(self, chat_reference: int | str, query: str, limit: int = 50):
        chat = resolve_chat_reference(self.transport, chat_reference)
        return self.transport.search_chat_messages(
            chat_id=chat.chat_id,
            query=query,
            limit=limit,
        )

    def search_public_posts(self, query: str, limit: int = 50):
        return self.transport.search_public_posts(query=query, limit=limit)

    def resolve_username(self, username: str):
        return self.transport.resolve_username(username=username)
