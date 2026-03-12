from __future__ import annotations

import unittest

from sdk import HistoryCursor, InvalidEntityReferenceError, TelegramSDK
from sdk.adapters.memory import MemoryTelegramTransport
from sdk.models import Chat, InlineButton, Message, User


class ReferenceToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = MemoryTelegramTransport(
            chats=[
                Chat(
                    chat_id=1001,
                    title="Public Channel",
                    username="public_chan",
                    kind="channel",
                    is_public=True,
                ),
                Chat(
                    chat_id=2002,
                    title="Search Bot",
                    username="en_SearchBot",
                    kind="bot",
                    is_public=True,
                ),
            ],
            messages=[
                Message(
                    message_id=500,
                    chat_id=1001,
                    sender_id=41,
                    text="Previous context",
                    timestamp="2026-03-11T23:59:00Z",
                ),
                Message(
                    message_id=501,
                    chat_id=1001,
                    sender_id=42,
                    text="Choose an action",
                    timestamp="2026-03-12T00:00:00Z",
                    buttons=[
                        [InlineButton(text="Open"), InlineButton(text="Details")],
                        [InlineButton(text="Visit", url="https://t.me/public_chan")],
                    ],
                ),
                Message(
                    message_id=502,
                    chat_id=1001,
                    sender_id=43,
                    text="After context one",
                    timestamp="2026-03-12T00:01:00Z",
                ),
                Message(
                    message_id=503,
                    chat_id=1001,
                    sender_id=44,
                    text="After context two",
                    timestamp="2026-03-12T00:02:00Z",
                ),
            ],
            users=[
                User(
                    user_id=3003,
                    username="helper_user",
                    display_name="Helper User",
                    is_bot=False,
                )
            ],
        )
        self.sdk = TelegramSDK(self.transport)
        self.sdk.connect()

    def tearDown(self) -> None:
        self.sdk.close()

    def test_resolve_chat_reference_accepts_chat_id_username_and_tme_link(self) -> None:
        by_id = self.sdk.resolve_chat_reference(1001)
        by_username = self.sdk.resolve_chat_reference("@public_chan")
        by_link = self.sdk.resolve_chat_reference("https://t.me/public_chan/501")
        private_user = self.sdk.resolve_chat_reference("@helper_user")

        self.assertEqual(by_id.chat_id, 1001)
        self.assertEqual(by_username.chat_id, 1001)
        self.assertEqual(by_link.chat_id, 1001)
        self.assertEqual(private_user.chat_id, 3003)
        self.assertEqual(private_user.kind, "private")

    def test_list_message_buttons_and_click_by_button_reference(self) -> None:
        buttons = self.sdk.list_message_buttons("@public_chan", 501)

        self.assertEqual(len(buttons), 3)
        self.assertEqual(buttons[0].row, 0)
        self.assertEqual(buttons[0].column, 0)
        self.assertEqual(buttons[0].text, "Open")
        self.assertEqual(buttons[2].url, "https://t.me/public_chan")

        refreshed = self.sdk.click_button_reference(
            "https://t.me/public_chan",
            501,
            buttons[1],
        )
        self.assertEqual(refreshed.chat_id, 1001)
        self.assertEqual(refreshed.message_id, 501)

    def test_existing_sdk_methods_accept_chat_reference(self) -> None:
        chat = self.sdk.get_chat("@public_chan")
        history = self.sdk.get_chat_history("https://t.me/public_chan", limit=5)
        message = self.sdk.get_message("@public_chan", 501)
        exported = self.sdk.export_message_link("@public_chan", 501)
        found = self.sdk.search_chat_messages("@public_chan", "Choose", limit=5)
        sent = self.sdk.send_text("@public_chan", "Hello by reference")
        clicked = self.sdk.click_message_button("@public_chan", 501, button_text="Open")

        self.assertEqual(chat.chat_id, 1001)
        self.assertEqual(history[0].message_id, 503)
        self.assertEqual(message.message_id, 501)
        self.assertEqual(exported, "https://t.me/public_chan/501")
        self.assertEqual(found[0].message_id, 501)
        self.assertEqual(sent.chat_id, 1001)
        self.assertEqual(clicked.message_id, 501)

    def test_inspect_chat_and_message_expose_context_for_tooling(self) -> None:
        self.sdk.send_text("@public_chan", "Older context")
        inspection = self.sdk.inspect_chat("@public_chan", history_limit=5)
        message_inspection = self.sdk.inspect_message("@public_chan", 501, context_limit=5)

        self.assertEqual(inspection.chat.chat_id, 1001)
        self.assertGreaterEqual(len(inspection.recent_messages), 2)
        self.assertEqual(message_inspection.chat.chat_id, 1001)
        self.assertEqual(message_inspection.message.message_id, 501)
        self.assertEqual(len(message_inspection.buttons), 3)
        self.assertEqual(
            [message.message_id for message in message_inspection.context_messages],
            [500],
        )

    def test_inspection_supports_direction_filters_and_query(self) -> None:
        before = self.sdk.inspect_chat(
            "@public_chan",
            history_limit=2,
            anchor_message_id=502,
            direction="before",
        )
        after = self.sdk.inspect_chat(
            "@public_chan",
            history_limit=2,
            anchor_message_id=501,
            direction="after",
        )
        around = self.sdk.inspect_chat(
            "@public_chan",
            history_limit=3,
            anchor_message_id=501,
            direction="around",
        )
        filtered = self.sdk.inspect_chat(
            "@public_chan",
            history_limit=5,
            direction="latest",
            query="after context",
        )

        self.assertEqual([message.message_id for message in before.recent_messages], [500, 501])
        self.assertEqual([message.message_id for message in after.recent_messages], [502, 503])
        self.assertEqual([message.message_id for message in around.recent_messages], [500, 502, 503])
        self.assertEqual([message.message_id for message in filtered.recent_messages], [502, 503])

    def test_inspection_tool_payload_is_ready_for_tooling_layer(self) -> None:
        message_payload = self.sdk.inspect_message_tool_payload(
            "@public_chan",
            501,
            before_limit=1,
            after_limit=2,
        )
        chat_payload = self.sdk.inspect_chat_tool_payload(
            "@public_chan",
            history_limit=2,
            direction="after",
            anchor_message_id=501,
        )

        self.assertEqual(message_payload["message"]["message_id"], 501)
        self.assertEqual(
            [item["message_id"] for item in message_payload["context_before"]],
            [500],
        )
        self.assertEqual(
            [item["message_id"] for item in message_payload["context_after"]],
            [502, 503],
        )
        self.assertEqual(message_payload["buttons"][0]["text"], "Open")
        self.assertEqual(chat_payload["direction"], "after")
        self.assertEqual(
            [item["message_id"] for item in chat_payload["recent_messages"]],
            [502, 503],
        )

    def test_inspect_chat_page_returns_pagination_and_cursor(self) -> None:
        first_page = self.sdk.inspect_chat_page("@public_chan", page_size=2)
        self.assertEqual(
            [message.message_id for message in first_page.recent_messages],
            [502, 503],
        )
        self.assertIsNotNone(first_page.pagination)
        assert first_page.pagination is not None
        self.assertTrue(first_page.pagination.has_more_before)
        self.assertEqual(first_page.pagination.next_before_message_id, 502)
        self.assertIsNotNone(first_page.pagination.next_cursor)

        second_page = self.sdk.inspect_chat_page(
            "@public_chan",
            cursor=first_page.pagination.next_cursor,
        )
        self.assertEqual(
            [message.message_id for message in second_page.recent_messages],
            [500, 501],
        )

    def test_history_cursor_roundtrip_and_query_page_filter(self) -> None:
        cursor = HistoryCursor(before_message_id=503, page_size=2, query="context")
        token = cursor.to_token()
        decoded = HistoryCursor.from_token(token)
        page = self.sdk.inspect_chat_page("@public_chan", cursor=token)

        self.assertEqual(decoded.before_message_id, 503)
        self.assertEqual(decoded.page_size, 2)
        self.assertEqual(decoded.query, "context")
        self.assertEqual(
            [message.message_id for message in page.recent_messages],
            [500, 502],
        )

    def test_resolve_chat_reference_rejects_invalid_reference(self) -> None:
        with self.assertRaises(InvalidEntityReferenceError):
            self.sdk.resolve_chat_reference("   ")

        with self.assertRaises(InvalidEntityReferenceError):
            self.sdk.resolve_chat_reference("https://t.me/joinchat/abcdef")


if __name__ == "__main__":
    unittest.main()
