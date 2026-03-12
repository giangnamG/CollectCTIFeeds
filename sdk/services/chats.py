"""Chat metadata and history services."""

from __future__ import annotations

from sdk.models import (
    ChatInspection,
    HistoryCursor,
    InspectionDirection,
    InspectionPagination,
    Message,
    MessageInspection,
)
from sdk.references import list_message_button_refs, resolve_chat_reference
from sdk.transports import TelegramTransport


class ChatService:
    """Chat-focused operations exposed by the SDK."""

    def __init__(self, transport: TelegramTransport) -> None:
        self.transport = transport

    def get_chat(self, chat_reference: int | str):
        chat = resolve_chat_reference(self.transport, chat_reference)
        return self.transport.get_chat(chat_id=chat.chat_id)

    def resolve_chat_reference(self, reference: int | str):
        return resolve_chat_reference(self.transport, reference)

    def get_chat_history(
        self,
        chat_reference: int | str,
        limit: int = 100,
        before_message_id: int | None = None,
    ):
        chat = resolve_chat_reference(self.transport, chat_reference)
        return self.transport.get_chat_history(
            chat_id=chat.chat_id,
            limit=limit,
            before_message_id=before_message_id,
        )

    def get_message(self, chat_reference: int | str, message_id: int):
        chat = resolve_chat_reference(self.transport, chat_reference)
        return self.transport.get_message(chat_id=chat.chat_id, message_id=message_id)

    def export_message_link(self, chat_reference: int | str, message_id: int) -> str:
        chat = resolve_chat_reference(self.transport, chat_reference)
        return self.transport.export_message_link(
            chat_id=chat.chat_id,
            message_id=message_id,
        )

    def inspect_chat(
        self,
        chat_reference: int | str,
        history_limit: int = 10,
        *,
        anchor_message_id: int | None = None,
        direction: InspectionDirection = "latest",
        query: str | None = None,
        scan_limit: int | None = None,
    ) -> ChatInspection:
        chat = resolve_chat_reference(self.transport, chat_reference)
        messages = self._collect_inspection_messages(
            chat_id=chat.chat_id,
            limit=history_limit,
            anchor_message_id=anchor_message_id,
            direction=direction,
            query=query,
            scan_limit=scan_limit,
        )
        return ChatInspection(
            chat=self.transport.get_chat(chat_id=chat.chat_id),
            recent_messages=messages,
            direction=direction,
            anchor_message_id=anchor_message_id,
            query=query,
        )

    def inspect_chat_page(
        self,
        chat_reference: int | str,
        page_size: int = 20,
        *,
        cursor: HistoryCursor | str | None = None,
        before_message_id: int | None = None,
        query: str | None = None,
        scan_limit: int | None = None,
    ) -> ChatInspection:
        chat = resolve_chat_reference(self.transport, chat_reference)
        resolved_cursor = self._coerce_history_cursor(
            cursor=cursor,
            page_size=page_size,
            before_message_id=before_message_id,
            query=query,
        )
        page_messages, pagination = self._collect_history_page(
            chat_id=chat.chat_id,
            cursor=resolved_cursor,
            scan_limit=scan_limit,
        )
        return ChatInspection(
            chat=self.transport.get_chat(chat_id=chat.chat_id),
            recent_messages=page_messages,
            direction=resolved_cursor.direction,
            anchor_message_id=resolved_cursor.before_message_id,
            query=resolved_cursor.query,
            pagination=pagination,
        )

    def inspect_message(
        self,
        chat_reference: int | str,
        message_id: int,
        context_limit: int = 5,
        *,
        before_limit: int | None = None,
        after_limit: int | None = None,
        query: str | None = None,
        scan_limit: int | None = None,
    ) -> MessageInspection:
        chat = resolve_chat_reference(self.transport, chat_reference)
        message = self.transport.get_message(chat_id=chat.chat_id, message_id=message_id)
        before_messages = self._collect_inspection_messages(
            chat_id=chat.chat_id,
            limit=before_limit if before_limit is not None else context_limit,
            anchor_message_id=message_id,
            direction="before",
            query=query,
            scan_limit=scan_limit,
        )
        after_messages = self._collect_inspection_messages(
            chat_id=chat.chat_id,
            limit=after_limit if after_limit is not None else 0,
            anchor_message_id=message_id,
            direction="after",
            query=query,
            scan_limit=scan_limit,
        )
        context_messages = [*before_messages, *after_messages]
        context_messages.sort(key=lambda item: item.message_id)
        return MessageInspection(
            chat=self.transport.get_chat(chat_id=chat.chat_id),
            message=message,
            buttons=list_message_button_refs(message),
            context_messages=context_messages,
            context_before=before_messages,
            context_after=after_messages,
            query=query,
        )

    def inspect_chat_tool_payload(
        self,
        chat_reference: int | str,
        history_limit: int = 10,
        *,
        anchor_message_id: int | None = None,
        direction: InspectionDirection = "latest",
        query: str | None = None,
        scan_limit: int | None = None,
    ) -> dict:
        return self.inspect_chat(
            chat_reference=chat_reference,
            history_limit=history_limit,
            anchor_message_id=anchor_message_id,
            direction=direction,
            query=query,
            scan_limit=scan_limit,
        ).to_tool_payload()

    def inspect_chat_page_tool_payload(
        self,
        chat_reference: int | str,
        page_size: int = 20,
        *,
        cursor: HistoryCursor | str | None = None,
        before_message_id: int | None = None,
        query: str | None = None,
        scan_limit: int | None = None,
    ) -> dict:
        return self.inspect_chat_page(
            chat_reference=chat_reference,
            page_size=page_size,
            cursor=cursor,
            before_message_id=before_message_id,
            query=query,
            scan_limit=scan_limit,
        ).to_tool_payload()

    def inspect_message_tool_payload(
        self,
        chat_reference: int | str,
        message_id: int,
        context_limit: int = 5,
        *,
        before_limit: int | None = None,
        after_limit: int | None = None,
        query: str | None = None,
        scan_limit: int | None = None,
    ) -> dict:
        return self.inspect_message(
            chat_reference=chat_reference,
            message_id=message_id,
            context_limit=context_limit,
            before_limit=before_limit,
            after_limit=after_limit,
            query=query,
            scan_limit=scan_limit,
        ).to_tool_payload()

    def _collect_inspection_messages(
        self,
        *,
        chat_id: int,
        limit: int,
        anchor_message_id: int | None,
        direction: InspectionDirection,
        query: str | None,
        scan_limit: int | None,
    ) -> list[Message]:
        if limit <= 0:
            return []

        normalized_direction = direction
        if normalized_direction == "before":
            messages = self.transport.get_chat_history(
                chat_id=chat_id,
                limit=limit,
                before_message_id=anchor_message_id,
            )
            messages.sort(key=lambda item: item.message_id)
            return self._filter_messages(messages, query)

        fetch_limit = max(scan_limit or (max(limit * 4, 20)), limit)
        messages = self.transport.get_chat_history(chat_id=chat_id, limit=fetch_limit)
        messages.sort(key=lambda item: item.message_id)

        if normalized_direction == "latest":
            filtered = messages[-limit:]
        elif normalized_direction == "after":
            filtered = [
                message
                for message in messages
                if anchor_message_id is not None and message.message_id > anchor_message_id
            ][:limit]
        elif normalized_direction == "around":
            if anchor_message_id is None:
                filtered = messages[-limit:]
            else:
                half_window = max(limit // 2, 1)
                before = [
                    message for message in messages if message.message_id < anchor_message_id
                ][-half_window:]
                after = [
                    message for message in messages if message.message_id > anchor_message_id
                ][: max(limit - len(before), 0)]
                filtered = [*before, *after]
        else:
            raise ValueError(f"Unsupported inspection direction: {direction}")

        return self._filter_messages(filtered, query)

    @staticmethod
    def _filter_messages(messages: list[Message], query: str | None) -> list[Message]:
        if not query:
            return messages
        needle = query.casefold()
        return [message for message in messages if needle in message.text.casefold()]

    def _collect_history_page(
        self,
        *,
        chat_id: int,
        cursor: HistoryCursor,
        scan_limit: int | None,
    ) -> tuple[list[Message], InspectionPagination]:
        fetch_limit = max(scan_limit or max(cursor.page_size * 4, 20), cursor.page_size)
        collected = self.transport.get_chat_history(
            chat_id=chat_id,
            limit=fetch_limit,
            before_message_id=cursor.before_message_id,
        )
        collected.sort(key=lambda item: item.message_id)
        filtered = self._filter_messages(collected, cursor.query)
        page_messages = filtered[-cursor.page_size :]

        oldest_scanned_id = collected[0].message_id if collected else None
        oldest_returned_id = page_messages[0].message_id if page_messages else None
        has_more_before = False
        if oldest_returned_id is not None and oldest_scanned_id is not None:
            has_more_before = oldest_scanned_id < oldest_returned_id or len(collected) == fetch_limit
        elif collected and len(collected) == fetch_limit:
            has_more_before = True

        next_before_message_id = oldest_returned_id if has_more_before else None
        next_cursor = None
        if next_before_message_id is not None:
            next_cursor = HistoryCursor(
                before_message_id=next_before_message_id,
                page_size=cursor.page_size,
                query=cursor.query,
                direction="before",
            )

        pagination = InspectionPagination(
            page_size=cursor.page_size,
            returned_count=len(page_messages),
            scanned_count=len(collected),
            has_more_before=has_more_before,
            next_before_message_id=next_before_message_id,
            next_cursor=next_cursor,
            scan_limit_reached=bool(collected) and len(collected) == fetch_limit,
        )
        return page_messages, pagination

    @staticmethod
    def _coerce_history_cursor(
        *,
        cursor: HistoryCursor | str | None,
        page_size: int,
        before_message_id: int | None,
        query: str | None,
    ) -> HistoryCursor:
        if isinstance(cursor, HistoryCursor):
            return cursor
        if isinstance(cursor, str):
            return HistoryCursor.from_token(cursor)
        return HistoryCursor(
            before_message_id=before_message_id,
            page_size=page_size,
            query=query,
            direction="before",
        )
