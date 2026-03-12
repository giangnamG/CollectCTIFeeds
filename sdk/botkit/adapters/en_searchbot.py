"""Adapter for the unofficial @en_SearchBot workflow."""

from __future__ import annotations

import re
import time

from sdk.botkit.base import BaseBotAdapter
from sdk.botkit.checkpoints import BotSearchCheckpointWriter
from sdk.botkit.errors import BotTimeoutError
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
        initial_aggregates = self._extract_aggregates(replies)
        session.state["last_collected_aggregates"] = initial_aggregates
        session.state["last_checkpoint_state"] = None
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
        aggregates = session.state.get("last_collected_aggregates") or self._extract_aggregates(
            reply_messages
        )
        checkpoint_state = session.state.get("last_checkpoint_state") or {}
        inferred_pages_collected, inferred_total_pages = self._infer_pagination_state(
            reply_messages=reply_messages,
            page_snapshots=page_snapshots,
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
                "total_pages": checkpoint_state.get("total_pages", inferred_total_pages),
                "pages_collected": checkpoint_state.get(
                    "pages_collected",
                    inferred_pages_collected,
                ),
                "checkpoint_path": checkpoint_state.get("path"),
                "checkpoint_complete": checkpoint_state.get("is_complete", False),
                "resumed_from_checkpoint": checkpoint_state.get("resumed", False),
                "extracted_usernames": aggregates["extracted_usernames"],
                "extracted_links": aggregates["extracted_links"],
                "extracted_chat_usernames": aggregates["extracted_chat_usernames"],
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

        checkpoint = self._build_checkpoint_writer(request)
        keep_page_snapshots_in_memory = bool(
            request.options.get(
                "keep_page_snapshots_in_memory",
                checkpoint is None,
            )
        )
        page_snapshot_memory_limit = request.options.get("page_snapshot_memory_limit")
        memory_limit = (
            None
            if page_snapshot_memory_limit is None
            else max(0, int(page_snapshot_memory_limit))
        )
        snapshots_by_page: dict[int, Message] = {}
        collected_page_numbers: set[int] = set()
        current = paginated
        seen_signatures = {self._message_signature(current)}
        aggregate_state = self._load_checkpoint_aggregates(checkpoint)
        self._record_page_snapshot(
            page=current,
            snapshots_by_page=snapshots_by_page,
            collected_page_numbers=collected_page_numbers,
            keep_in_memory=keep_page_snapshots_in_memory,
            memory_limit=memory_limit,
            checkpoint=checkpoint,
            aggregate_state=aggregate_state,
        )
        pagination_poll_attempts = int(
            request.options.get("pagination_poll_attempts", max(poll_attempts * 10, 60))
        )
        pagination_history_limit = int(
            request.options.get(
                "pagination_history_limit",
                max(200, len(reply_messages) * 10),
            )
        )
        pagination_stall_retries = int(
            request.options.get("pagination_stall_retries", 30)
        )
        stall_count = 0

        while True:
            target_pages = self._page_total(current)
            if max_pages is not None:
                target_pages = min(target_pages, max_pages)
            current_page_number = self._page_number(current)
            current_signature = self._message_signature(current)
            if current_page_number >= target_pages:
                break
            if not self._has_next_button(current):
                raise BotTimeoutError(
                    f"Pagination stopped unexpectedly at page {current_page_number}/{target_pages} "
                    f"for bot '{self.bot_id}'."
                )

            updated = self._advance_to_next_page(
                request=request,
                session=session,
                current=current,
                poll_attempts=pagination_poll_attempts,
                poll_interval_seconds=poll_interval_seconds,
            )
            if not self._shows_forward_progress(
                candidate=updated,
                previous_signature=current_signature,
                previous_page_number=current_page_number,
            ):
                recovered = self._recover_paginated_message(
                    request=request,
                    session=session,
                    current=current,
                    history_limit=pagination_history_limit,
                )
                if not self._shows_forward_progress(
                    candidate=recovered,
                    previous_signature=current_signature,
                    previous_page_number=current_page_number,
                ):
                    stall_count += 1
                    if stall_count > pagination_stall_retries:
                        raise BotTimeoutError(
                            f"Could not advance pagination beyond page {current_page_number}/{target_pages} "
                            f"for bot '{self.bot_id}' after {pagination_stall_retries} recovery attempts."
                        )
                    if poll_interval_seconds > 0:
                        time.sleep(poll_interval_seconds)
                    continue
                updated = recovered
            stall_count = 0
            current = updated
            current_signature = self._message_signature(current)
            current_page_number = self._page_number(current)
            if current_signature in seen_signatures:
                stall_count += 1
                if stall_count > pagination_stall_retries:
                    raise BotTimeoutError(
                        f"Pagination kept returning the same page signature at page "
                        f"{current_page_number}/{target_pages} for bot '{self.bot_id}'."
                    )
                if poll_interval_seconds > 0:
                    time.sleep(poll_interval_seconds)
                continue
            seen_signatures.add(current_signature)
            self._record_page_snapshot(
                page=current,
                snapshots_by_page=snapshots_by_page,
                collected_page_numbers=collected_page_numbers,
                keep_in_memory=keep_page_snapshots_in_memory,
                memory_limit=memory_limit,
                checkpoint=checkpoint,
                aggregate_state=aggregate_state,
            )

        expected_pages = target_pages if max_pages is None else min(target_pages, max_pages)
        collected_pages = self._collected_page_count(
            snapshots_by_page=snapshots_by_page,
            collected_page_numbers=collected_page_numbers,
            checkpoint=checkpoint,
        )
        if collected_pages != expected_pages:
            raise BotTimeoutError(
                f"Pagination finished with {collected_pages}/{expected_pages} pages "
                f"for bot '{self.bot_id}'."
            )
        if checkpoint is not None:
            checkpoint.mark_complete(total_pages=expected_pages)
            checkpoint_state = checkpoint.state()
            session.state["last_checkpoint_state"] = {
                "path": checkpoint_state.path,
                "total_pages": checkpoint_state.total_pages,
                "pages_collected": checkpoint_state.pages_collected,
                "last_page_number": checkpoint_state.last_page_number,
                "is_complete": checkpoint_state.is_complete,
                "resumed": checkpoint_state.resumed,
            }
            aggregate_state = checkpoint.combined_aggregates()
        else:
            session.state["last_checkpoint_state"] = {
                "path": None,
                "total_pages": expected_pages,
                "pages_collected": collected_pages,
                "last_page_number": expected_pages,
                "is_complete": True,
                "resumed": False,
            }
        session.state["last_collected_aggregates"] = aggregate_state
        return [snapshots_by_page[page] for page in sorted(snapshots_by_page)]

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
        previous_edit_timestamp = current.edit_timestamp
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
                previous_edit_timestamp=previous_edit_timestamp,
                poll_attempts=poll_attempts,
                poll_interval_seconds=poll_interval_seconds,
            )
            if self._shows_forward_progress(
                candidate=updated,
                previous_signature=previous_signature,
                previous_page_number=previous_page_number,
            ):
                return updated
            if click_attempt < click_attempts - 1 and poll_interval_seconds > 0:
                time.sleep(poll_interval_seconds)
        return None

    def _recover_paginated_message(
        self,
        *,
        request: BotRequest,
        session: BotSession,
        current: Message,
        history_limit: int,
    ) -> Message | None:
        history = self.call_with_transport_retry(
            lambda: self.transport.get_chat_history(
                chat_id=session.chat_id,
                limit=history_limit,
            ),
            request=request,
            operation="get_chat_history",
            allow_replay=True,
        )
        candidates: list[Message] = []
        current_page_number = self._page_number(current)
        current_signature = self._message_signature(current)
        for message in history:
            if message.sender_id is not None and message.sender_id != session.chat_id:
                continue
            if not PAGE_PATTERN.search(message.text):
                continue
            if message.message_id == current.message_id:
                candidates.append(message)
                continue
            if self._page_number(message) > current_page_number:
                candidates.append(message)
        candidates.sort(
            key=lambda message: (
                self._page_number(message),
                message.edit_timestamp or "",
                message.message_id,
            )
        )
        for candidate in reversed(candidates):
            if (
                self._page_number(candidate) > current_page_number
                or self._message_signature(candidate) != current_signature
            ):
                return candidate
        return None

    def _build_checkpoint_writer(
        self,
        request: BotRequest,
    ) -> BotSearchCheckpointWriter | None:
        checkpoint_path = request.options.get("checkpoint_path")
        if checkpoint_path is None:
            return None
        return BotSearchCheckpointWriter(
            str(checkpoint_path),
            bot_id=self.bot_id,
            bot_username=self.bot_username,
            query=str(request.params.get("query", "")),
            resume=bool(request.options.get("resume_checkpoint", False)),
        )

    def _load_checkpoint_aggregates(
        self,
        checkpoint: BotSearchCheckpointWriter | None,
    ) -> dict[str, list[str]]:
        if checkpoint is None:
            return {
                "extracted_usernames": [],
                "extracted_links": [],
                "extracted_chat_usernames": [],
            }
        return checkpoint.combined_aggregates()

    def _record_page_snapshot(
        self,
        *,
        page: Message,
        snapshots_by_page: dict[int, Message],
        collected_page_numbers: set[int],
        keep_in_memory: bool,
        memory_limit: int | None,
        checkpoint: BotSearchCheckpointWriter | None,
        aggregate_state: dict[str, list[str]],
    ) -> None:
        page_number = self._page_number(page)
        total_pages = self._page_total(page)
        signature = self._message_signature(page)
        collected_page_numbers.add(page_number)
        page_aggregates = self._extract_aggregates([page])
        if checkpoint is not None:
            checkpoint.append_page(
                page_number=page_number,
                total_pages=total_pages,
                signature=signature,
                text=page.text,
                message_id=page.message_id,
                timestamp=page.timestamp,
                edit_timestamp=page.edit_timestamp,
                extracted_usernames=page_aggregates["extracted_usernames"],
                extracted_links=page_aggregates["extracted_links"],
                extracted_chat_usernames=page_aggregates["extracted_chat_usernames"],
            )
            checkpoint_aggregates = checkpoint.combined_aggregates()
            aggregate_state["extracted_usernames"] = checkpoint_aggregates["extracted_usernames"]
            aggregate_state["extracted_links"] = checkpoint_aggregates["extracted_links"]
            aggregate_state["extracted_chat_usernames"] = checkpoint_aggregates[
                "extracted_chat_usernames"
            ]
        else:
            self._merge_aggregate_values(
                aggregate_state,
                page_aggregates,
            )

        if not keep_in_memory:
            return

        snapshots_by_page[page_number] = self.snapshot_message(page)
        if memory_limit is None or memory_limit <= 0:
            if memory_limit == 0:
                snapshots_by_page.clear()
            return
        while len(snapshots_by_page) > memory_limit:
            oldest_page = min(snapshots_by_page)
            snapshots_by_page.pop(oldest_page, None)

    @staticmethod
    def _collected_page_count(
        *,
        snapshots_by_page: dict[int, Message],
        collected_page_numbers: set[int],
        checkpoint: BotSearchCheckpointWriter | None,
    ) -> int:
        if checkpoint is not None:
            return checkpoint.state().pages_collected
        return len(collected_page_numbers)

    def _wait_for_message_update(
        self,
        *,
        request: BotRequest,
        chat_id: int,
        message_id: int,
        previous_signature: str,
        previous_page_number: int,
        previous_edit_timestamp: str | None,
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
                or self._is_new_edit_version(
                    current=current,
                    previous_edit_timestamp=previous_edit_timestamp,
                )
            ):
                return current
            if attempt < poll_attempts - 1:
                time.sleep(poll_interval_seconds)
        return current

    @staticmethod
    def _shows_forward_progress(
        *,
        candidate: Message | None,
        previous_signature: str,
        previous_page_number: int,
    ) -> bool:
        if candidate is None:
            return False
        candidate_page_number = EnSearchBotAdapter._page_number(candidate)
        if candidate_page_number > previous_page_number:
            return True
        candidate_signature = EnSearchBotAdapter._message_signature(candidate)
        if (
            candidate_page_number == previous_page_number
            and candidate_signature != previous_signature
        ):
            return True
        return False

    @staticmethod
    def _is_new_edit_version(
        *,
        current: Message,
        previous_edit_timestamp: str | None,
    ) -> bool:
        if current.edit_timestamp is None:
            return False
        if previous_edit_timestamp is None:
            return True
        return current.edit_timestamp != previous_edit_timestamp

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

    @classmethod
    def _extract_aggregates(cls, messages: list[Message]) -> dict[str, list[str]]:
        extracted_usernames = cls._extract_usernames(messages)
        extracted_links = cls._extract_links(messages)
        extracted_chat_usernames = cls._extract_chat_usernames(
            extracted_usernames=extracted_usernames,
            extracted_links=extracted_links,
        )
        return {
            "extracted_usernames": extracted_usernames,
            "extracted_links": extracted_links,
            "extracted_chat_usernames": extracted_chat_usernames,
        }

    @staticmethod
    def _merge_aggregate_values(
        aggregate_state: dict[str, list[str]],
        page_aggregates: dict[str, list[str]],
    ) -> None:
        for key, values in page_aggregates.items():
            seen = {value.casefold() for value in aggregate_state[key]}
            for value in values:
                normalized = value.casefold()
                if normalized in seen:
                    continue
                seen.add(normalized)
                aggregate_state[key].append(value)

    @classmethod
    def _infer_pagination_state(
        cls,
        *,
        reply_messages: list[Message],
        page_snapshots: list[Message],
    ) -> tuple[int, int | None]:
        if page_snapshots:
            highest_page = max(cls._page_number(message) for message in page_snapshots)
            total_pages = max(cls._page_total(message) for message in page_snapshots)
            return highest_page, total_pages

        paginated = cls._find_paginated_message(reply_messages)
        if paginated is None:
            return 0, None
        return cls._page_number(paginated), cls._page_total(paginated)

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
