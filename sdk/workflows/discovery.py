"""High-level discovery workflows for keyword-driven collection."""

from __future__ import annotations

from sdk.models import KeywordDiscoveryResults, Message
from sdk.services.bot_search import BotSearchService
from sdk.transports import TelegramTransport


class KeywordDiscoveryWorkflow:
    """Combine official Telegram search with bot-assisted enrichment."""

    def __init__(
        self,
        transport: TelegramTransport,
        bot_search: BotSearchService | None = None,
    ) -> None:
        self.transport = transport
        self.bot_search = bot_search or BotSearchService(transport)

    def discover_by_keyword(
        self,
        query: str,
        *,
        public_chat_limit: int = 10,
        global_message_limit: int = 10,
        public_post_limit: int = 10,
        fallback_limit_per_chat: int = 5,
        use_en_searchbot: bool = False,
        bot_poll_attempts: int = 6,
        bot_poll_interval_seconds: float = 2.0,
    ) -> KeywordDiscoveryResults:
        errors: list[str] = []

        public_chats = self.transport.search_public_chats(
            query=query,
            limit=public_chat_limit,
        )
        global_results = self.transport.search_messages(
            query=query,
            limit=global_message_limit,
        )

        public_posts: list[Message] = []
        try:
            post_results = self.transport.search_public_posts(
                query=query,
                limit=public_post_limit,
            )
        except Exception as exc:
            errors.append(f"public post search failed: {exc}")
        else:
            public_posts = post_results.messages

        fallback_messages = self._search_inside_discovered_chats(
            query=query,
            public_chat_limit=public_chat_limit,
            fallback_limit_per_chat=fallback_limit_per_chat,
            errors=errors,
            public_chats=public_chats,
        )

        bot_results = []
        if use_en_searchbot:
            try:
                bot_results.append(
                    self.bot_search.search_via_en_searchbot(
                        query=query,
                        poll_attempts=bot_poll_attempts,
                        poll_interval_seconds=bot_poll_interval_seconds,
                    )
                )
            except Exception as exc:
                errors.append(f"@en_SearchBot search failed: {exc}")

        return KeywordDiscoveryResults(
            query=query,
            public_chats=public_chats,
            global_messages=global_results.messages,
            public_posts=public_posts,
            fallback_messages=fallback_messages,
            bot_results=bot_results,
            errors=errors,
        )

    def _search_inside_discovered_chats(
        self,
        *,
        query: str,
        public_chat_limit: int,
        fallback_limit_per_chat: int,
        errors: list[str],
        public_chats,
    ) -> list[Message]:
        messages: list[Message] = []
        seen: set[tuple[int, int]] = set()

        for chat in public_chats[:public_chat_limit]:
            try:
                chat_messages = self.transport.search_chat_messages(
                    chat_id=chat.chat_id,
                    query=query,
                    limit=fallback_limit_per_chat,
                )
            except Exception as exc:
                errors.append(f"per-chat search failed for {chat.title}: {exc}")
                continue

            for message in chat_messages:
                key = (message.chat_id, message.message_id)
                if key in seen:
                    continue
                seen.add(key)
                messages.append(message)

        messages.sort(key=lambda item: (item.chat_id, item.message_id))
        return messages
