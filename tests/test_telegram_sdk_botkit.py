from __future__ import annotations

import unittest

from sdk import (
    BotContext,
    BotRequest,
    BotValidationError,
    Chat,
    InMemorySessionStore,
    Message,
    MonitoringBotAdapter,
    TelegramSDK,
)
from sdk.adapters.memory import MemoryTelegramTransport


class ScriptedMonitoringTransport(MemoryTelegramTransport):
    def __init__(self) -> None:
        super().__init__(
            chats=[
                Chat(
                    chat_id=300,
                    title="Monitoring Bot",
                    username="monitoring_bot",
                    kind="bot",
                    is_public=True,
                )
            ]
        )

    def send_text(self, chat_id: int, text: str) -> Message:
        sent = super().send_text(chat_id=chat_id, text=text)
        reply_text = "Status: OK" if text == "/status" else f"Search: {text}"
        next_message_id = max((message.message_id for message in self._messages), default=0) + 1
        self._messages.append(
            Message(
                message_id=next_message_id,
                chat_id=chat_id,
                sender_id=999,
                text=reply_text,
                timestamp="local-now",
            )
        )
        return sent


class TelegramSDKBotkitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = ScriptedMonitoringTransport()
        self.sdk = TelegramSDK(self.transport)
        self.sdk.register_bot_adapter(
            MonitoringBotAdapter(
                transport=self.transport,
                session_store=InMemorySessionStore(),
            )
        )
        self.sdk.connect()

    def tearDown(self) -> None:
        self.sdk.close()

    def test_execute_bot_command_supports_alias_resolution_via_telegram_sdk(self) -> None:
        response = self.sdk.execute_bot_command(
            BotRequest(
                bot_id="monitoring",
                command_name="status",
                context=BotContext(tenant_id="local", user_id="tester"),
                options={"poll_attempts": 2, "poll_interval_seconds": 0.0},
            )
        )

        self.assertEqual(response.bot_id, "monitoring")
        self.assertEqual(response.command_name, "monitor.status")
        self.assertEqual(response.status, "ok")
        self.assertIn("Status: OK", response.data["text"])
        self.assertIn("monitoring", self.sdk.list_registered_bots())

    def test_execute_bot_command_validates_required_params_before_adapter_execution(self) -> None:
        with self.assertRaises(BotValidationError):
            self.sdk.execute_bot_command(
                BotRequest(
                    bot_id="monitoring",
                    command_name="monitor.search",
                    params={"query": "   "},
                    context=BotContext(tenant_id="local", user_id="tester"),
                    options={"poll_attempts": 2, "poll_interval_seconds": 0.0},
                )
            )


if __name__ == "__main__":
    unittest.main()
