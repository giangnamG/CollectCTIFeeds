"""Bot-assisted search services built on top of the transport interface."""

from __future__ import annotations

from dataclasses import replace
import re
import time

from sdk.botkit import BotContext, BotRequest, BotSDK
from sdk.botkit.adapters import EnSearchBotAdapter
from sdk.errors import EntityNotFoundError, TelegramSDKError
from sdk.models import BotSearchResults, Chat, Message, User
from sdk.session import InMemorySessionStore
from sdk.transports import TelegramTransport

USERNAME_PATTERN = re.compile(r"(?<![\w/])@([A-Za-z0-9_]{5,32})")
LINK_PATTERN = re.compile(r"(?:(?:https?://)?t\.me/[^\s<>()\]]+)")
CHAT_LINK_PATTERN = re.compile(r"^(?:https?://)?t\.me/([A-Za-z0-9_]{5,32})(?:[/?#].*)?$")
IGNORED_LINK_PREFIXES = {"c", "joinchat", "share", "addstickers", "socks", "proxy"}
PAGE_PATTERN = re.compile(r"Page\s+(\d+)\s*/\s*(\d+)", re.IGNORECASE)


class BotSearchService:
    """Interact with Telegram bots that return search-like results."""

    def __init__(
        self,
        transport: TelegramTransport,
        bot_sdk: BotSDK | None = None,
    ) -> None:
        self.transport = transport
        self._bot_sdk = bot_sdk or BotSDK(transport)
        if EnSearchBotAdapter.bot_id not in self._bot_sdk.list_bots():
            self._bot_sdk.register_adapter(
                EnSearchBotAdapter(
                    transport=transport,
                    session_store=InMemorySessionStore(),
                )
            )

    def search_via_bot(
        self,
        bot_username: str,
        query: str,
        *,
        poll_attempts: int = 6,
        poll_interval_seconds: float = 2.0,
        history_limit: int = 20,
        crawl_all_pages: bool = False,
        max_pages: int | None = None,
        checkpoint_path: str | None = None,
        resume_checkpoint: bool = False,
        keep_page_snapshots_in_memory: bool = True,
        page_snapshot_memory_limit: int | None = None,
    ) -> BotSearchResults:
        if self._is_en_searchbot(bot_username):
            return self._search_via_en_searchbot_adapter(
                query=query,
                poll_attempts=poll_attempts,
                poll_interval_seconds=poll_interval_seconds,
                history_limit=history_limit,
                crawl_all_pages=crawl_all_pages,
                max_pages=max_pages,
                checkpoint_path=checkpoint_path,
                resume_checkpoint=resume_checkpoint,
                keep_page_snapshots_in_memory=keep_page_snapshots_in_memory,
                page_snapshot_memory_limit=page_snapshot_memory_limit,
            )
        return self._search_via_bot_legacy(
            bot_username=bot_username,
            query=query,
            poll_attempts=poll_attempts,
            poll_interval_seconds=poll_interval_seconds,
            history_limit=history_limit,
            crawl_all_pages=crawl_all_pages,
            max_pages=max_pages,
        )

    def search_via_en_searchbot(
        self,
        query: str,
        *,
        poll_attempts: int = 6,
        poll_interval_seconds: float = 2.0,
        history_limit: int = 20,
        crawl_all_pages: bool = False,
        max_pages: int | None = None,
        checkpoint_path: str | None = None,
        resume_checkpoint: bool = False,
        keep_page_snapshots_in_memory: bool = True,
        page_snapshot_memory_limit: int | None = None,
    ) -> BotSearchResults:
        return self._search_via_en_searchbot_adapter(
            query=query,
            poll_attempts=poll_attempts,
            poll_interval_seconds=poll_interval_seconds,
            history_limit=history_limit,
            crawl_all_pages=crawl_all_pages,
            max_pages=max_pages,
            checkpoint_path=checkpoint_path,
            resume_checkpoint=resume_checkpoint,
            keep_page_snapshots_in_memory=keep_page_snapshots_in_memory,
            page_snapshot_memory_limit=page_snapshot_memory_limit,
        )

    def _search_via_en_searchbot_adapter(
        self,
        *,
        query: str,
        poll_attempts: int,
        poll_interval_seconds: float,
        history_limit: int,
        crawl_all_pages: bool,
        max_pages: int | None,
        checkpoint_path: str | None,
        resume_checkpoint: bool,
        keep_page_snapshots_in_memory: bool,
        page_snapshot_memory_limit: int | None,
    ) -> BotSearchResults:
        response = self._bot_sdk.execute_command(
            BotRequest(
                bot_id=EnSearchBotAdapter.bot_id,
                command_name="search.keyword",
                params={"query": query},
                context=BotContext(
                    tenant_id="telegram-sdk",
                    user_id="bot-search-service",
                ),
                options={
                    "poll_attempts": poll_attempts,
                    "poll_interval_seconds": poll_interval_seconds,
                    "history_limit": history_limit,
                    "crawl_all_pages": crawl_all_pages,
                    "max_pages": max_pages,
                    "checkpoint_path": checkpoint_path,
                    "resume_checkpoint": resume_checkpoint,
                    "keep_page_snapshots_in_memory": keep_page_snapshots_in_memory,
                    "page_snapshot_memory_limit": page_snapshot_memory_limit,
                },
            )
        )
        data = response.data
        bot_chat = data.get("bot_chat")
        if not isinstance(bot_chat, Chat):
            bot_chat = self._resolve_bot_chat(EnSearchBotAdapter.bot_username)
        request_message = data.get("request_message")
        if not isinstance(request_message, Message):
            raise TelegramSDKError("Bot adapter response is missing request message data.")
        page_snapshots = data.get("page_snapshots", [])
        return BotSearchResults(
            bot_username=bot_chat.username or EnSearchBotAdapter.bot_username,
            query=str(data.get("query", query)),
            bot_chat=bot_chat,
            request_message=request_message,
            reply_messages=response.raw_messages,
            page_snapshots=page_snapshots if isinstance(page_snapshots, list) else [],
            total_pages=data.get("total_pages"),
            pages_collected=int(data.get("pages_collected", len(page_snapshots))),
            checkpoint_path=data.get("checkpoint_path"),
            checkpoint_complete=bool(data.get("checkpoint_complete", False)),
            resumed_from_checkpoint=bool(data.get("resumed_from_checkpoint", False)),
            extracted_usernames=list(data.get("extracted_usernames", [])),
            extracted_links=list(data.get("extracted_links", [])),
            extracted_chat_usernames=list(data.get("extracted_chat_usernames", [])),
        )

    def _search_via_bot_legacy(
        self,
        *,
        bot_username: str,
        query: str,
        poll_attempts: int,
        poll_interval_seconds: float,
        history_limit: int,
        crawl_all_pages: bool,
        max_pages: int | None,
    ) -> BotSearchResults:
        bot_chat = self._resolve_bot_chat(bot_username)
        self.transport.start_bot(bot_username=bot_username)
        request_message = self.transport.send_text(chat_id=bot_chat.chat_id, text=query)
        reply_messages = self._wait_for_replies(
            bot_chat=bot_chat,
            after_message_id=request_message.message_id,
            poll_attempts=poll_attempts,
            poll_interval_seconds=poll_interval_seconds,
            history_limit=history_limit,
        )
        page_snapshots: list[Message] = []
        if crawl_all_pages:
            page_snapshots = self._crawl_all_pages(
                bot_chat=bot_chat,
                reply_messages=reply_messages,
                poll_attempts=poll_attempts,
                poll_interval_seconds=poll_interval_seconds,
                max_pages=max_pages,
            )

        extraction_source = self._merge_messages(reply_messages, page_snapshots)
        extracted_usernames = self._extract_usernames(extraction_source)
        extracted_links = self._extract_links(extraction_source)
        extracted_chat_usernames = self._extract_chat_usernames(
            extracted_usernames=extracted_usernames,
            extracted_links=extracted_links,
        )
        return BotSearchResults(
            bot_username=bot_chat.username or bot_username.removeprefix("@"),
            query=query,
            bot_chat=bot_chat,
            request_message=request_message,
            reply_messages=reply_messages,
            page_snapshots=page_snapshots,
            extracted_usernames=extracted_usernames,
            extracted_links=extracted_links,
            extracted_chat_usernames=extracted_chat_usernames,
        )

    def _resolve_bot_chat(self, bot_username: str) -> Chat:
        entity = self.transport.resolve_username(bot_username)
        if isinstance(entity, Chat):
            if entity.kind != "bot":
                raise TelegramSDKError(f"Resolved entity is not a bot: {bot_username}")
            return entity
        if isinstance(entity, User) and entity.is_bot:
            return Chat(
                chat_id=entity.user_id,
                title=entity.display_name or entity.username or str(entity.user_id),
                username=entity.username,
                kind="bot",
                is_public=bool(entity.username),
            )
        raise EntityNotFoundError(f"Bot not found: {bot_username}")

    def _wait_for_replies(
        self,
        *,
        bot_chat: Chat,
        after_message_id: int,
        poll_attempts: int,
        poll_interval_seconds: float,
        history_limit: int,
    ) -> list[Message]:
        stable_cycles = 0
        previous_ids: tuple[int, ...] = ()
        collected: dict[int, Message] = {}

        for attempt in range(poll_attempts):
            history = self.transport.get_chat_history(
                chat_id=bot_chat.chat_id,
                limit=history_limit,
            )
            replies = [
                message
                for message in history
                if message.message_id > after_message_id and message.text.strip()
            ]
            replies.sort(key=lambda item: item.message_id)

            for message in replies:
                collected[message.message_id] = message

            reply_ids = tuple(message.message_id for message in replies)
            if reply_ids and reply_ids == previous_ids:
                stable_cycles += 1
            else:
                stable_cycles = 0
            previous_ids = reply_ids

            if reply_ids and stable_cycles >= 1:
                break
            if attempt < poll_attempts - 1:
                time.sleep(poll_interval_seconds)

        return [collected[key] for key in sorted(collected)]

    def _extract_usernames(self, messages: list[Message]) -> list[str]:
        usernames: list[str] = []
        seen: set[str] = set()
        for message in messages:
            for match in USERNAME_PATTERN.findall(message.text):
                username = f"@{match}"
                normalized = username.casefold()
                if normalized not in seen:
                    usernames.append(username)
                    seen.add(normalized)
        return usernames

    def _extract_links(self, messages: list[Message]) -> list[str]:
        links: list[str] = []
        seen: set[str] = set()
        for message in messages:
            for raw_link in LINK_PATTERN.findall(message.text):
                link = self._normalize_link(raw_link)
                if link.casefold() not in seen:
                    links.append(link)
                    seen.add(link.casefold())
        return links

    def _extract_chat_usernames(
        self,
        *,
        extracted_usernames: list[str],
        extracted_links: list[str],
    ) -> list[str]:
        chat_usernames = list(extracted_usernames)
        seen = {username.casefold() for username in extracted_usernames}
        for link in extracted_links:
            match = CHAT_LINK_PATTERN.match(link)
            if not match:
                continue
            username = match.group(1)
            if username.casefold() in IGNORED_LINK_PREFIXES:
                continue
            candidate = f"@{username}"
            if candidate.casefold() not in seen:
                chat_usernames.append(candidate)
                seen.add(candidate.casefold())
        return chat_usernames

    @staticmethod
    def _normalize_link(raw_link: str) -> str:
        trimmed = raw_link.rstrip(".,);]>")
        if trimmed.startswith("http://") or trimmed.startswith("https://"):
            return trimmed
        return f"https://{trimmed}"

    def _crawl_all_pages(
        self,
        *,
        bot_chat: Chat,
        reply_messages: list[Message],
        poll_attempts: int,
        poll_interval_seconds: float,
        max_pages: int | None,
    ) -> list[Message]:
        paginated = self._find_paginated_message(reply_messages)
        if paginated is None:
            return []

        snapshots = [self._snapshot_message(paginated)]
        current = paginated
        target_pages = self._page_total(current)
        if max_pages is not None:
            target_pages = min(target_pages, max_pages)

        while self._page_number(current) < target_pages:
            if not self._has_next_button(current):
                break

            previous_signature = self._message_signature(current)
            self.transport.click_message_button(
                chat_id=bot_chat.chat_id,
                message_id=current.message_id,
                button_text="➡️",
            )
            current = self._wait_for_message_update(
                bot_chat=bot_chat,
                message_id=current.message_id,
                previous_signature=previous_signature,
                poll_attempts=poll_attempts,
                poll_interval_seconds=poll_interval_seconds,
            )
            if self._message_signature(current) == previous_signature:
                break
            snapshots.append(self._snapshot_message(current))

        return snapshots

    def _wait_for_message_update(
        self,
        *,
        bot_chat: Chat,
        message_id: int,
        previous_signature: str,
        poll_attempts: int,
        poll_interval_seconds: float,
    ) -> Message:
        current = self.transport.get_message(chat_id=bot_chat.chat_id, message_id=message_id)
        for attempt in range(poll_attempts):
            current = self.transport.get_message(
                chat_id=bot_chat.chat_id,
                message_id=message_id,
            )
            if self._message_signature(current) != previous_signature:
                return current
            if attempt < poll_attempts - 1:
                time.sleep(poll_interval_seconds)
        return current

    def _find_paginated_message(self, messages: list[Message]) -> Message | None:
        for message in reversed(messages):
            if PAGE_PATTERN.search(message.text) and self._has_next_button(message):
                return message
        for message in reversed(messages):
            if PAGE_PATTERN.search(message.text):
                return message
        return None

    @staticmethod
    def _has_next_button(message: Message) -> bool:
        for row in message.buttons:
            for button in row:
                if button.text == "➡️":
                    return True
        return False

    @staticmethod
    def _page_total(message: Message) -> int:
        match = PAGE_PATTERN.search(message.text)
        if not match:
            return 1
        return int(match.group(2))

    @staticmethod
    def _page_number(message: Message) -> int:
        match = PAGE_PATTERN.search(message.text)
        if not match:
            return 1
        return int(match.group(1))

    @staticmethod
    def _message_signature(message: Message) -> str:
        button_signature = "|".join(
            f"{button.text}:{button.data!r}:{button.url or ''}"
            for row in message.buttons
            for button in row
        )
        return f"{message.text}\n{button_signature}"

    @staticmethod
    def _snapshot_message(message: Message) -> Message:
        return replace(
            message,
            buttons=[[replace(button) for button in row] for row in message.buttons],
        )

    @staticmethod
    def _merge_messages(primary: list[Message], secondary: list[Message]) -> list[Message]:
        seen: set[tuple[int, int, str]] = set()
        merged: list[Message] = []
        for message in [*primary, *secondary]:
            key = (message.chat_id, message.message_id, message.text)
            if key in seen:
                continue
            seen.add(key)
            merged.append(message)
        return merged

    @staticmethod
    def _is_en_searchbot(bot_username: str) -> bool:
        return bot_username.removeprefix("@").casefold() == "en_searchbot"
