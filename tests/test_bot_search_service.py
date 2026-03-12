from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from sdk.adapters.memory import MemoryTelegramTransport
from sdk.botkit.errors import BotTimeoutError
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
        self._en_total_pages = 2
        self._en_current_page = 1
        self._pagination_click_attempts = 0
        self._delay_pagination_update = False
        self._never_update_pagination = False
        self._pending_page_update_polls = 0
        self._history_failures_remaining = 0
        self._message_failures_remaining = 0

    def send_text(self, chat_id: int, text: str) -> Message:
        sent = super().send_text(chat_id=chat_id, text=text)
        if chat_id == 100:
            self._en_current_page = 1
            reply = self._append_message(
                chat_id=chat_id,
                text=self._page_text(1),
                buttons=self._page_buttons(1),
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
            if self._never_update_pagination:
                message.is_edited = True
                message.edit_timestamp = "edited-stalled"
                return message
            if self._delay_pagination_update and self._pagination_click_attempts < 2:
                self._pending_page_update_polls = 2
                message.is_edited = True
                message.edit_timestamp = "edited-pending"
                return message
            if not self._delay_pagination_update or self._pagination_click_attempts >= 2:
                self._advance_page_message(message)
                message.is_edited = True
                message.edit_timestamp = f"edited-page-{self._en_current_page}"
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
        message = super().get_message(chat_id=chat_id, message_id=message_id)
        if (
            chat_id == 100
            and message_id == self._en_reply_message_id
            and self._pending_page_update_polls > 0
        ):
            self._pending_page_update_polls -= 1
            message.is_edited = True
            message.edit_timestamp = "edited-pending"
            if self._pending_page_update_polls == 0:
                self._advance_page_message(message)
                message.edit_timestamp = f"edited-page-{self._en_current_page}"
        return message

    def _advance_page_message(self, message: Message) -> None:
        if self._en_current_page < self._en_total_pages:
            self._en_current_page += 1
        message.text = self._page_text(self._en_current_page)
        message.buttons = self._page_buttons(self._en_current_page)

    def _page_text(self, page_number: int) -> str:
        page_map = {
            1: "Results for query: @Alpha https://t.me/BetaChan\nPage 1 / {total}",
            2: "Results for query: @Gamma\nPage 2 / {total}",
            3: "Results for query: @Delta https://t.me/OmegaChan\nPage 3 / {total}",
        }
        template = page_map.get(
            page_number,
            f"Results for query: @Page{page_number}\nPage {page_number} / {{total}}",
        )
        return template.format(total=self._en_total_pages)

    def _page_buttons(self, page_number: int) -> list[list[InlineButton]]:
        if page_number >= self._en_total_pages:
            return []
        return [[InlineButton(text="➡️")]]

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
        self._tempdir = tempfile.TemporaryDirectory()
        self.transport = ScriptedBotTransport()
        self.transport.connect()
        self.service = BotSearchService(self.transport)

    def tearDown(self) -> None:
        self.transport.close()
        self._tempdir.cleanup()

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

    def test_search_via_en_searchbot_reports_first_page_metadata_without_full_crawl(self) -> None:
        result = self.service.search_via_en_searchbot(
            "needle",
            crawl_all_pages=False,
            poll_attempts=2,
            poll_interval_seconds=0.0,
        )

        self.assertEqual(result.pages_collected, 1)
        self.assertEqual(result.total_pages, 2)
        self.assertFalse(result.checkpoint_complete)
        self.assertEqual(len(result.page_snapshots), 0)
        self.assertIn("@Alpha", result.extracted_usernames)

    def test_search_via_en_searchbot_ignores_non_bot_noise_and_waits_for_pagination(self) -> None:
        self.transport._delay_pagination_update = True

        result = self.service.search_via_en_searchbot(
            "needle",
            crawl_all_pages=True,
            max_pages=2,
            poll_attempts=2,
            poll_interval_seconds=0.0,
        )

        self.assertEqual(self.transport._pagination_click_attempts, 1)
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

    def test_search_via_en_searchbot_waits_for_real_page_change_after_edit_marker(self) -> None:
        self.transport._delay_pagination_update = True

        result = self.service.search_via_en_searchbot(
            "needle",
            crawl_all_pages=True,
            max_pages=2,
            poll_attempts=2,
            poll_interval_seconds=0.0,
            history_limit=20,
        )

        self.assertEqual(len(result.page_snapshots), 2)
        self.assertEqual(result.page_snapshots[-1].text, "Results for query: @Gamma\nPage 2 / 2")

    def test_search_via_en_searchbot_fails_if_not_all_pages_can_be_collected(self) -> None:
        self.transport._never_update_pagination = True

        with self.assertRaisesRegex(
            BotTimeoutError,
            "Could not advance pagination beyond page 1/2",
        ):
            self.service.search_via_en_searchbot(
                "needle",
                crawl_all_pages=True,
                max_pages=2,
                poll_attempts=1,
                poll_interval_seconds=0.0,
                history_limit=20,
            )

    def test_search_via_en_searchbot_streams_pages_to_checkpoint_without_keeping_all_in_memory(self) -> None:
        self.transport._en_total_pages = 3
        checkpoint_path = Path(self._tempdir.name) / "en-searchbot.jsonl"

        result = self.service.search_via_en_searchbot(
            "needle",
            crawl_all_pages=True,
            max_pages=3,
            poll_attempts=2,
            poll_interval_seconds=0.0,
            checkpoint_path=str(checkpoint_path),
            keep_page_snapshots_in_memory=False,
        )

        self.assertEqual(result.total_pages, 3)
        self.assertEqual(result.pages_collected, 3)
        self.assertEqual(result.page_snapshots, [])
        self.assertEqual(result.checkpoint_path, str(checkpoint_path))
        self.assertTrue(result.checkpoint_complete)
        self.assertFalse(result.resumed_from_checkpoint)
        self.assertCountEqual(
            result.extracted_chat_usernames,
            ["@Alpha", "@Gamma", "@Delta", "@BetaChan", "@OmegaChan"],
        )

        records = [
            json.loads(line)
            for line in checkpoint_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        page_numbers = [record["page_number"] for record in records if record["type"] == "page"]
        self.assertEqual(page_numbers, [1, 2, 3])
        self.assertEqual(records[-1]["type"], "complete")

    def test_search_via_en_searchbot_resumes_from_checkpoint(self) -> None:
        self.transport._en_total_pages = 3
        checkpoint_path = Path(self._tempdir.name) / "resume-search.jsonl"
        checkpoint_path.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "type": "meta",
                            "version": 1,
                            "bot_id": "en_searchbot",
                            "bot_username": "en_SearchBot",
                            "query": "needle",
                            "created_at": "2026-03-12T00:00:00+00:00",
                        }
                    ),
                    json.dumps(
                        {
                            "type": "page",
                            "page_number": 1,
                            "total_pages": 3,
                            "signature": "Results for query: @Alpha https://t.me/BetaChan\nPage 1 / 3\n➡️:None:",
                            "message_id": 2,
                            "timestamp": "local-now",
                            "edit_timestamp": None,
                            "text": "Results for query: @Alpha https://t.me/BetaChan\nPage 1 / 3",
                            "extracted_usernames": ["@Alpha"],
                            "extracted_links": ["https://t.me/BetaChan"],
                            "extracted_chat_usernames": ["@Alpha", "@BetaChan"],
                            "recorded_at": "2026-03-12T00:00:01+00:00",
                        }
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.service.search_via_en_searchbot(
            "needle",
            crawl_all_pages=True,
            max_pages=3,
            poll_attempts=2,
            poll_interval_seconds=0.0,
            checkpoint_path=str(checkpoint_path),
            resume_checkpoint=True,
            keep_page_snapshots_in_memory=False,
        )

        self.assertEqual(result.total_pages, 3)
        self.assertEqual(result.pages_collected, 3)
        self.assertTrue(result.checkpoint_complete)
        self.assertTrue(result.resumed_from_checkpoint)
        self.assertEqual(result.page_snapshots, [])
        records = [
            json.loads(line)
            for line in checkpoint_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        page_numbers = [record["page_number"] for record in records if record["type"] == "page"]
        self.assertEqual(page_numbers, [1, 2, 3])

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
