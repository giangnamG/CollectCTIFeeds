"""Adapter for the unofficial @en_SearchBot workflow."""

from __future__ import annotations

import re
import time

from sdk.botkit.base import BaseBotAdapter
from sdk.botkit.models import (
    BotCapability,
    BotCommand,
    BotRequest,
    BotResponse,
    BotSession,
    ExecutionMode,
)
from sdk.models import Message

USERNAME_PATTERN = re.compile(r"(?<![\w/])@([A-Za-z0-9_]{5,32})")
LINK_PATTERN = re.compile(r"(?:(?:https?://)?t\.me/[^\s<>()\]]+)")
CHAT_LINK_PATTERN = re.compile(r"^(?:https?://)?t\.me/([A-Za-z0-9_]{5,32})(?:[/?#].*)?$")
IGNORED_LINK_PREFIXES = {"c", "joinchat", "share", "addstickers", "socks", "proxy"}
PAGE_PATTERN = re.compile(r"Page\s+(\d+)\s*/\s*(\d+)", re.IGNORECASE)


class EnSearchBotAdapter(BaseBotAdapter):
    """Bot adapter that wraps the existing @en_SearchBot search workflow."""

    bot_id = "en_searchbot"
    bot_username = "en_SearchBot"

    def supports(self, command_name: str) -> bool:
        return command_name == "search.keyword"

    def get_supported_commands(self) -> list[BotCommand]:
        return [
            BotCommand(
                name="search.keyword",
                aliases=["search"],
                parameters={"query": "str"},
                capabilities={
                    BotCapability.SEARCH,
                    BotCapability.CALLBACKS,
                    BotCapability.PAGINATION,
                },
                execution_mode=ExecutionMode.CONVERSATIONAL,
                timeout_seconds=15.0,
            )
        ]

    def map_command(self, request: BotRequest, session: BotSession) -> str:
        query = str(request.params.get("query", "")).strip()
        if not query:
            raise ValueError("search.keyword requires a non-empty 'query' parameter.")
        session.state["last_query"] = query
        return query

    def collect_reply_messages(
        self,
        *,
        session: BotSession,
        sent_message: Message,
        request: BotRequest,
    ) -> list[Message]:
        replies = super().collect_reply_messages(
            session=session,
            sent_message=sent_message,
            request=request,
        )
        page_snapshots: list[Message] = []
        if request.options.get("crawl_all_pages"):
            max_pages = request.options.get("max_pages")
            page_snapshots = self._crawl_all_pages(
                request=request,
                session=session,
                reply_messages=replies,
                poll_attempts=int(request.options.get("poll_attempts", 6)),
                poll_interval_seconds=float(
                    request.options.get("poll_interval_seconds", 2.0)
                ),
                max_pages=int(max_pages) if max_pages is not None else None,
            )
        session.state["last_page_snapshots"] = page_snapshots
        return self.merge_messages(replies, page_snapshots)

    def filter_reply_messages(
        self,
        *,
        session: BotSession,
        history: list[Message],
        sent_message: Message,
        request: BotRequest,
    ) -> list[Message]:
        replies = super().filter_reply_messages(
            session=session,
            history=history,
            sent_message=sent_message,
            request=request,
        )
        filtered: list[Message] = []
        for message in replies:
            if not self._looks_like_relevant_reply(
                message=message,
                session=session,
                sent_message=sent_message,
            ):
                continue
            filtered.append(message)
        direct_replies = [
            message
            for message in filtered
            if message.reply_to_message_id == sent_message.message_id
        ]
        if direct_replies:
            tracked_ids = {
                *session.state.get("tracked_reply_message_ids", []),
                *(message.message_id for message in direct_replies),
            }
            session.state["tracked_reply_message_ids"] = sorted(tracked_ids)
            filtered = [
                message
                for message in filtered
                if message.message_id in tracked_ids
                or message.reply_to_message_id == sent_message.message_id
            ]
        return filtered

    def parse_response(
        self,
        *,
        request: BotRequest,
        session: BotSession,
        sent_message: Message,
        reply_messages: list[Message],
    ) -> BotResponse:
        page_snapshots = session.state.get("last_page_snapshots", [])
        extracted_usernames = self._extract_usernames(reply_messages)
        extracted_links = self._extract_links(reply_messages)
        extracted_chat_usernames = self._extract_chat_usernames(
            extracted_usernames=extracted_usernames,
            extracted_links=extracted_links,
        )
        return BotResponse(
            bot_id=self.bot_id,
            command_name=request.command_name,
            status="ok",
            data={
                "bot_chat": self.resolve_bot_chat(),
                "query": request.params.get("query"),
                "request_message": sent_message,
                "reply_count": len(reply_messages),
                "page_snapshots": page_snapshots,
                "page_snapshot_count": len(page_snapshots),
                "extracted_usernames": extracted_usernames,
                "extracted_links": extracted_links,
                "extracted_chat_usernames": extracted_chat_usernames,
            },
            raw_messages=reply_messages,
            correlation_id=request.context.correlation_id or request.request_id,
        )

    def _crawl_all_pages(
        self,
        *,
        request: BotRequest,
        session: BotSession,
        reply_messages: list[Message],
        poll_attempts: int,
        poll_interval_seconds: float,
        max_pages: int | None,
    ) -> list[Message]:
        paginated = self._find_paginated_message(reply_messages)
        if paginated is None:
            return []

        snapshots = [self.snapshot_message(paginated)]
        current = paginated
        seen_signatures = {self._message_signature(current)}
        seen_page_numbers = {self._page_number(current)}
        target_pages = self._page_total(current)
        if max_pages is not None:
            target_pages = min(target_pages, max_pages)

        while self._page_number(current) < target_pages:
            if not self._has_next_button(current):
                break

            updated = self._advance_to_next_page(
                request=request,
                session=session,
                current=current,
                poll_attempts=poll_attempts,
                poll_interval_seconds=poll_interval_seconds,
            )
            if updated is None:
                break
            current = updated
            current_signature = self._message_signature(current)
            current_page_number = self._page_number(current)
            if current_signature in seen_signatures:
                break
            if current_page_number in seen_page_numbers and current_page_number != 1:
                break
            seen_signatures.add(current_signature)
            seen_page_numbers.add(current_page_number)
            snapshots.append(self.snapshot_message(current))

        return snapshots

    def _advance_to_next_page(
        self,
        *,
        request: BotRequest,
        session: BotSession,
        current: Message,
        poll_attempts: int,
        poll_interval_seconds: float,
    ) -> Message | None:
        previous_signature = self._message_signature(current)
        previous_page_number = self._page_number(current)
        click_attempts = int(request.options.get("pagination_click_attempts", 2))

        for click_attempt in range(click_attempts):
            self.transport.click_message_button(
                chat_id=session.chat_id,
                message_id=current.message_id,
                button_text="➡️",
            )
            updated = self._wait_for_message_update(
                request=request,
                chat_id=session.chat_id,
                message_id=current.message_id,
                previous_signature=previous_signature,
                previous_page_number=previous_page_number,
                poll_attempts=poll_attempts,
                poll_interval_seconds=poll_interval_seconds,
            )
            if (
                self._message_signature(updated) != previous_signature
                or self._page_number(updated) > previous_page_number
            ):
                return updated
            if click_attempt < click_attempts - 1 and poll_interval_seconds > 0:
                time.sleep(poll_interval_seconds)
        return None

    def _wait_for_message_update(
        self,
        *,
        request: BotRequest,
        chat_id: int,
        message_id: int,
        previous_signature: str,
        previous_page_number: int,
        poll_attempts: int,
        poll_interval_seconds: float,
    ) -> Message:
        current = self.call_with_transport_retry(
            lambda: self.transport.get_message(chat_id=chat_id, message_id=message_id),
            request=request,
            operation="get_message",
            allow_replay=True,
        )
        for attempt in range(poll_attempts):
            current = self.call_with_transport_retry(
                lambda: self.transport.get_message(chat_id=chat_id, message_id=message_id),
                request=request,
                operation="get_message",
                allow_replay=True,
            )
            current_signature = self._message_signature(current)
            current_page_number = self._page_number(current)
            if (
                current_signature != previous_signature
                or current_page_number > previous_page_number
            ):
                return current
            if attempt < poll_attempts - 1:
                time.sleep(poll_interval_seconds)
        return current

    @staticmethod
    def _looks_like_relevant_reply(
        *,
        message: Message,
        session: BotSession,
        sent_message: Message,
    ) -> bool:
        if message.message_id <= sent_message.message_id:
            return False
        if not message.text.strip():
            return False
        if message.sender_id is not None and message.sender_id not in {session.chat_id}:
            return False
        tracked_reply_ids = set(session.state.get("tracked_reply_message_ids", []))
        if tracked_reply_ids and message.message_id in tracked_reply_ids:
            return True
        if (
            message.reply_to_message_id is not None
            and message.reply_to_message_id != sent_message.message_id
        ):
            return False
        return True

    @staticmethod
    def _extract_usernames(messages: list[Message]) -> list[str]:
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

    @staticmethod
    def _extract_links(messages: list[Message]) -> list[str]:
        links: list[str] = []
        seen: set[str] = set()
        for message in messages:
            for raw_link in LINK_PATTERN.findall(message.text):
                link = EnSearchBotAdapter._normalize_link(raw_link)
                if link.casefold() not in seen:
                    links.append(link)
                    seen.add(link.casefold())
        return links

    @staticmethod
    def _extract_chat_usernames(
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

    @staticmethod
    def _find_paginated_message(messages: list[Message]) -> Message | None:
        for message in reversed(messages):
            if PAGE_PATTERN.search(message.text) and EnSearchBotAdapter._has_next_button(
                message
            ):
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
