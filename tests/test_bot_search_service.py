from __future__ import annotations

import unittest

from sdk.adapters.memory import MemoryTelegramTransport
from sdk.models import Chat, InlineButton, Message
from sdk.services.bot_search import BotSearchService


class ScriptedBotTransport(MemoryTelegramTransport):
    def __init__(self) -> None:
        super().__init__(
            chats=[
                Chat(
                    chat_id=100,
                    title="En SearchBot",
                    username="en_SearchBot",
                    kind="bot",
                    is_public=True,
                ),
                Chat(
                    chat_id=200,
                    title="Legacy Bot",
                    username="legacy_bot",
                    kind="bot",
                    is_public=True,
                ),
            ]
        )
        self._en_reply_message_id: int | None = None
        self._pagination_click_attempts = 0
        self._delay_pagination_update = False
        self._history_failures_remaining = 0
        self._message_failures_remaining = 0

    def send_text(self, chat_id: int, text: str) -> Message:
        sent = super().send_text(chat_id=chat_id, text=text)
        if chat_id == 100:
            reply = self._append_message(
                chat_id=chat_id,
                text="Results for query: @Alpha https://t.me/BetaChan\nPage 1 / 2",
                buttons=[[InlineButton(text="➡️")]],
                sender_id=100,
                reply_to_message_id=sent.message_id,
            )
            self._en_reply_message_id = reply.message_id
            self._append_message(
                chat_id=chat_id,
                text="Noise that should be ignored",
                sender_id=100,
                reply_to_message_id=999999,
            )
        elif chat_id == 200:
            self._append_message(
                chat_id=chat_id,
                text="Legacy hit: @Legacy https://t.me/LegacyChan",
                sender_id=999,
            )
        return sent

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
        message = super().click_message_button(
            chat_id=chat_id,
            message_id=message_id,
            button_text=button_text,
            row=row,
            column=column,
            data=data,
        )
        if chat_id == 100 and message_id == self._en_reply_message_id:
            self._pagination_click_attempts += 1
            if not self._delay_pagination_update or self._pagination_click_attempts >= 2:
                message.text = "Results for query: @Gamma\nPage 2 / 2"
                message.buttons = []
        return message

    def get_chat_history(
        self,
        chat_id: int,
        limit: int = 100,
        before_message_id: int | None = None,
    ) -> list[Message]:
        if self._history_failures_remaining > 0:
            self._history_failures_remaining -= 1
            raise TimeoutError("simulated transient history timeout")
        return super().get_chat_history(
            chat_id=chat_id,
            limit=limit,
            before_message_id=before_message_id,
        )

    def get_message(self, chat_id: int, message_id: int) -> Message:
        if self._message_failures_remaining > 0:
            self._message_failures_remaining -= 1
            raise TimeoutError("simulated transient message timeout")
        return super().get_message(chat_id=chat_id, message_id=message_id)

    def _append_message(
        self,
        *,
        chat_id: int,
        text: str,
        sender_id: int | None,
        buttons: list[list[InlineButton]] | None = None,
        reply_to_message_id: int | None = None,
    ) -> Message:
        next_message_id = max((message.message_id for message in self._messages), default=0) + 1
        message = Message(
            message_id=next_message_id,
            chat_id=chat_id,
            sender_id=sender_id,
            text=text,
            timestamp="local-now",
            buttons=buttons or [],
            reply_to_message_id=reply_to_message_id,
        )
        self._messages.append(message)
        return message


class BotSearchServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = ScriptedBotTransport()
        self.transport.connect()
        self.service = BotSearchService(self.transport)

    def tearDown(self) -> None:
        self.transport.close()

    def test_search_via_en_searchbot_preserves_bot_search_results_shape(self) -> None:
        result = self.service.search_via_en_searchbot(
            "needle",
            crawl_all_pages=True,
            max_pages=2,
            poll_attempts=2,
            poll_interval_seconds=0.0,
        )

        self.assertEqual(result.bot_username, "en_SearchBot")
        self.assertEqual(result.query, "needle")
        self.assertEqual(result.request_message.text, "needle")
        self.assertEqual(len(result.page_snapshots), 2)
        self.assertCountEqual(result.extracted_usernames, ["@Alpha", "@Gamma"])
        self.assertEqual(result.extracted_links, ["https://t.me/BetaChan"])
        self.assertCountEqual(
            result.extracted_chat_usernames,
            ["@Alpha", "@Gamma", "@BetaChan"],
        )

    def test_search_via_en_searchbot_ignores_non_bot_noise_and_retries_pagination(self) -> None:
        self.transport._delay_pagination_update = True

        result = self.service.search_via_en_searchbot(
            "needle",
            crawl_all_pages=True,
            max_pages=2,
            poll_attempts=2,
            poll_interval_seconds=0.0,
        )

        self.assertEqual(self.transport._pagination_click_attempts, 2)
        self.assertEqual(len(result.page_snapshots), 2)
        self.assertNotIn("Noise that should be ignored", [message.text for message in result.reply_messages])
        self.assertCountEqual(result.extracted_usernames, ["@Alpha", "@Gamma"])

    def test_search_via_en_searchbot_retries_transient_transport_timeouts(self) -> None:
        self.transport._history_failures_remaining = 1
        self.transport._message_failures_remaining = 1

        result = self.service.search_via_en_searchbot(
            "needle",
            crawl_all_pages=True,
            max_pages=2,
            poll_attempts=2,
            poll_interval_seconds=0.0,
        )

        self.assertEqual(result.bot_username, "en_SearchBot")
        self.assertEqual(len(result.page_snapshots), 2)

    def test_search_via_bot_keeps_legacy_flow_for_unregistered_bot(self) -> None:
        result = self.service.search_via_bot(
            "legacy_bot",
            "legacy-needle",
            poll_attempts=2,
            poll_interval_seconds=0.0,
        )

        self.assertEqual(result.bot_username, "legacy_bot")
        self.assertEqual(result.query, "legacy-needle")
        self.assertEqual(result.request_message.text, "legacy-needle")
        self.assertEqual(result.extracted_usernames, ["@Legacy"])
        self.assertEqual(result.extracted_links, ["https://t.me/LegacyChan"])
        self.assertEqual(
            result.extracted_chat_usernames,
            ["@Legacy", "@LegacyChan"],
        )


if __name__ == "__main__":
    unittest.main()
