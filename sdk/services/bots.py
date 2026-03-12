"""Bot interaction services."""

from __future__ import annotations

from sdk.models import MessageButtonRef
from sdk.references import list_message_button_refs, resolve_chat_reference
from sdk.transports import TelegramTransport


class BotService:
    """Bot and message sending operations exposed by the SDK."""

    def __init__(self, transport: TelegramTransport) -> None:
        self.transport = transport

    def send_text(self, chat_reference: int | str, text: str):
        chat = resolve_chat_reference(self.transport, chat_reference)
        return self.transport.send_text(chat_id=chat.chat_id, text=text)

    def list_message_buttons(
        self,
        chat_reference: int | str,
        message_id: int,
    ) -> list[MessageButtonRef]:
        chat = resolve_chat_reference(self.transport, chat_reference)
        message = self.transport.get_message(chat_id=chat.chat_id, message_id=message_id)
        return list_message_button_refs(message)

    def start_bot(self, bot_username: str, parameter: str | None = None):
        return self.transport.start_bot(
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
        chat = resolve_chat_reference(self.transport, chat_reference)
        return self.transport.click_message_button(
            chat_id=chat.chat_id,
            message_id=message_id,
            button_text=button_text,
            row=row,
            column=column,
            data=data,
        )

    def click_button_reference(
        self,
        chat_reference: int | str,
        message_id: int,
        button: MessageButtonRef,
    ):
        chat = resolve_chat_reference(self.transport, chat_reference)
        return self.transport.click_message_button(
            chat_id=chat.chat_id,
            message_id=message_id,
            row=button.row,
            column=button.column,
            button_text=button.text or None,
            data=button.data,
        )
