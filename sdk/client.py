"""Stable SDK facade for Telegram workflows."""

from __future__ import annotations

from sdk.botkit import BotRequest, BotResponse, BotSDK
from sdk.botkit.adapters import EnSearchBotAdapter
from sdk.botkit.contracts import IBotAdapter
from sdk.botkit.models import BotCommand
from sdk.models import (
    ChatInspection,
    HistoryCursor,
    InspectionDirection,
    MessageButtonRef,
    MessageInspection,
)
from sdk.session import InMemorySessionStore
from sdk.services.bot_search import BotSearchService
from sdk.services.bots import BotService
from sdk.services.chats import ChatService
from sdk.services.search import SearchService
from sdk.transports import TelegramTransport
from sdk.workflows.discovery import KeywordDiscoveryWorkflow


class TelegramSDK:
    """High-level facade with clean, transport-agnostic method names."""

    def __init__(self, transport: TelegramTransport) -> None:
        self.transport = transport
        self.botkit = BotSDK(transport)
        self.botkit.register_adapter(
            EnSearchBotAdapter(
                transport=transport,
                session_store=InMemorySessionStore(),
            )
        )
        self.search = SearchService(transport)
        self.chats = ChatService(transport)
        self.bots = BotService(transport)
        self.bot_search = BotSearchService(transport, bot_sdk=self.botkit)
        self.discovery = KeywordDiscoveryWorkflow(transport, bot_search=self.bot_search)

    def connect(self) -> None:
        self.transport.connect()

    def close(self) -> None:
        self.transport.close()

    def register_bot_adapter(self, adapter: IBotAdapter) -> None:
        self.botkit.register_adapter(adapter)

    def execute_bot_command(self, request: BotRequest) -> BotResponse:
        return self.botkit.execute_command(request)

    def get_supported_bot_commands(self, bot_id: str) -> list[BotCommand]:
        return self.botkit.get_supported_commands(bot_id)

    def list_registered_bots(self) -> list[str]:
        return self.botkit.list_bots()

    def search_public_chats(self, query: str, limit: int = 20):
        return self.search.search_public_chats(query=query, limit=limit)

    def search_messages(self, query: str, limit: int = 50):
        return self.search.search_messages(query=query, limit=limit)

    def search_chat_messages(
        self,
        chat_reference: int | str,
        query: str,
        limit: int = 50,
    ):
        return self.search.search_chat_messages(
            chat_reference=chat_reference,
            query=query,
            limit=limit,
        )

    def search_public_posts(self, query: str, limit: int = 50):
        return self.search.search_public_posts(query=query, limit=limit)

    def resolve_username(self, username: str):
        return self.search.resolve_username(username=username)

    def resolve_chat_reference(self, reference: int | str):
        return self.chats.resolve_chat_reference(reference=reference)

    def get_chat(self, chat_reference: int | str):
        return self.chats.get_chat(chat_reference=chat_reference)

    def get_chat_history(
        self,
        chat_reference: int | str,
        limit: int = 100,
        before_message_id: int | None = None,
    ):
        return self.chats.get_chat_history(
            chat_reference=chat_reference,
            limit=limit,
            before_message_id=before_message_id,
        )

    def get_message(self, chat_reference: int | str, message_id: int):
        return self.chats.get_message(
            chat_reference=chat_reference,
            message_id=message_id,
        )

    def export_message_link(self, chat_reference: int | str, message_id: int) -> str:
        return self.chats.export_message_link(
            chat_reference=chat_reference,
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
        return self.chats.inspect_chat(
            chat_reference=chat_reference,
            history_limit=history_limit,
            anchor_message_id=anchor_message_id,
            direction=direction,
            query=query,
            scan_limit=scan_limit,
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
        return self.chats.inspect_chat_page(
            chat_reference=chat_reference,
            page_size=page_size,
            cursor=cursor,
            before_message_id=before_message_id,
            query=query,
            scan_limit=scan_limit,
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
        return self.chats.inspect_message(
            chat_reference=chat_reference,
            message_id=message_id,
            context_limit=context_limit,
            before_limit=before_limit,
            after_limit=after_limit,
            query=query,
            scan_limit=scan_limit,
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
        return self.chats.inspect_chat_tool_payload(
            chat_reference=chat_reference,
            history_limit=history_limit,
            anchor_message_id=anchor_message_id,
            direction=direction,
            query=query,
            scan_limit=scan_limit,
        )

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
        return self.chats.inspect_chat_page_tool_payload(
            chat_reference=chat_reference,
            page_size=page_size,
            cursor=cursor,
            before_message_id=before_message_id,
            query=query,
            scan_limit=scan_limit,
        )

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
        return self.chats.inspect_message_tool_payload(
            chat_reference=chat_reference,
            message_id=message_id,
            context_limit=context_limit,
            before_limit=before_limit,
            after_limit=after_limit,
            query=query,
            scan_limit=scan_limit,
        )

    def send_text(self, chat_reference: int | str, text: str):
        return self.bots.send_text(chat_reference=chat_reference, text=text)

    def start_bot(self, bot_username: str, parameter: str | None = None):
        return self.bots.start_bot(
            bot_username=bot_username,
            parameter=parameter,
        )

    def click_message_button(
        self,
        chat_reference: int | str,
        message_id: int,
        *,
        button_text: str | None = None,
        row: int | None = None,
        column: int | None = None,
        data: bytes | None = None,
    ):
        return self.bots.click_message_button(
            chat_reference=chat_reference,
            message_id=message_id,
            button_text=button_text,
            row=row,
            column=column,
            data=data,
        )

    def list_message_buttons(
        self,
        chat_reference: int | str,
        message_id: int,
    ) -> list[MessageButtonRef]:
        return self.bots.list_message_buttons(
            chat_reference=chat_reference,
            message_id=message_id,
        )

    def click_button_reference(
        self,
        chat_reference: int | str,
        message_id: int,
        button: MessageButtonRef,
    ):
        return self.bots.click_button_reference(
            chat_reference=chat_reference,
            message_id=message_id,
            button=button,
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
    ):
        return self.bot_search.search_via_bot(
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
    ):
        return self.bot_search.search_via_en_searchbot(
            query=query,
            poll_attempts=poll_attempts,
            poll_interval_seconds=poll_interval_seconds,
            history_limit=history_limit,
            crawl_all_pages=crawl_all_pages,
            max_pages=max_pages,
        )

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
    ):
        return self.discovery.discover_by_keyword(
            query=query,
            public_chat_limit=public_chat_limit,
            global_message_limit=global_message_limit,
            public_post_limit=public_post_limit,
            fallback_limit_per_chat=fallback_limit_per_chat,
            use_en_searchbot=use_en_searchbot,
            bot_poll_attempts=bot_poll_attempts,
            bot_poll_interval_seconds=bot_poll_interval_seconds,
        )
