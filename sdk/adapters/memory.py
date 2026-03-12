"""In-memory transport used for local development and tests."""

from __future__ import annotations

from sdk.errors import EntityNotFoundError, TransportNotConnectedError
from sdk.models import BotStartResult, Chat, Message, SearchResults, User
from sdk.transports import TelegramTransport


class MemoryTelegramTransport(TelegramTransport):
    """Simple transport that stores Telegram-like data in memory."""

    def __init__(
        self,
        chats: list[Chat] | None = None,
        messages: list[Message] | None = None,
        users: list[User] | None = None,
    ) -> None:
        self._connected = False
        self._chats = {chat.chat_id: chat for chat in chats or []}
        self._messages = list(messages or [])
        self._users_by_username = {
            self._normalize_username(user.username): user
            for user in users or []
            if user.username
        }
        self._users_by_id = {user.user_id: user for user in users or []}

    def connect(self) -> None:
        self._connected = True

    def close(self) -> None:
        self._connected = False

    def search_public_chats(self, query: str, limit: int = 20) -> list[Chat]:
        self._ensure_connected()
        needle = query.casefold()
        results = [
            chat
            for chat in self._chats.values()
            if chat.is_public and needle in self._chat_search_blob(chat)
        ]
        return results[:limit]

    def search_messages(self, query: str, limit: int = 50) -> SearchResults:
        self._ensure_connected()
        needle = query.casefold()
        messages = [
            message for message in self._messages if needle in message.text.casefold()
        ][:limit]
        chat_ids = {message.chat_id for message in messages}
        chats = [self._chats[chat_id] for chat_id in chat_ids if chat_id in self._chats]
        return SearchResults(query=query, chats=chats, messages=messages)

    def search_chat_messages(
        self,
        chat_id: int,
        query: str,
        limit: int = 50,
    ) -> list[Message]:
        self._ensure_connected()
        self.get_chat(chat_id)
        needle = query.casefold()
        results = [
            message
            for message in self._messages
            if message.chat_id == chat_id and needle in message.text.casefold()
        ]
        return results[:limit]

    def search_public_posts(self, query: str, limit: int = 50) -> SearchResults:
        self._ensure_connected()
        needle = query.casefold()
        results = []
        chats = {}
        for message in self._messages:
            chat = self._chats.get(message.chat_id)
            if not chat or not chat.is_public or chat.kind != "channel":
                continue
            if needle in message.text.casefold():
                results.append(message)
                chats[chat.chat_id] = chat
            if len(results) >= limit:
                break
        return SearchResults(query=query, chats=list(chats.values()), messages=results)

    def resolve_username(self, username: str) -> Chat | User:
        self._ensure_connected()
        normalized = self._normalize_username(username)
        for chat in self._chats.values():
            if self._normalize_username(chat.username) == normalized:
                return chat
        user = self._users_by_username.get(normalized)
        if user:
            return user
        raise EntityNotFoundError(f"Username not found: {username}")

    def get_chat(self, chat_id: int) -> Chat:
        self._ensure_connected()
        chat = self._chats.get(chat_id)
        if not chat:
            raise EntityNotFoundError(f"Chat not found: {chat_id}")
        return chat

    def get_chat_history(
        self,
        chat_id: int,
        limit: int = 100,
        before_message_id: int | None = None,
    ) -> list[Message]:
        self._ensure_connected()
        self.get_chat(chat_id)
        messages = [message for message in self._messages if message.chat_id == chat_id]
        messages.sort(key=lambda item: item.message_id, reverse=True)
        if before_message_id is not None:
            messages = [
                message
                for message in messages
                if message.message_id < before_message_id
            ]
        return messages[:limit]

    def get_message(self, chat_id: int, message_id: int) -> Message:
        self._ensure_connected()
        self.get_chat(chat_id)
        return self._get_message(chat_id=chat_id, message_id=message_id)

    def export_message_link(self, chat_id: int, message_id: int) -> str:
        self._ensure_connected()
        chat = self.get_chat(chat_id)
        if not chat.is_public or not chat.username:
            raise EntityNotFoundError(
                f"Chat {chat_id} does not support a public message link"
            )
        self._get_message(chat_id=chat_id, message_id=message_id)
        return f"https://t.me/{chat.username}/{message_id}"

    def send_text(self, chat_id: int, text: str) -> Message:
        self._ensure_connected()
        self.get_chat(chat_id)
        next_message_id = max((message.message_id for message in self._messages), default=0)
        message = Message(
            message_id=next_message_id + 1,
            chat_id=chat_id,
            sender_id=0,
            text=text,
            timestamp="local-now",
        )
        self._messages.append(message)
        return message

    def start_bot(
        self,
        bot_username: str,
        parameter: str | None = None,
    ) -> BotStartResult:
        self._ensure_connected()
        entity = self.resolve_username(bot_username)
        if not isinstance(entity, Chat) or entity.kind != "bot":
            raise EntityNotFoundError(f"Bot not found: {bot_username}")
        welcome_message = (
            f"Started @{self._normalize_username(bot_username)}"
            if parameter is None
            else f"Started @{self._normalize_username(bot_username)} with {parameter}"
        )
        return BotStartResult(
            bot_username=self._normalize_username(bot_username),
            parameter=parameter,
            welcome_message=welcome_message,
        )

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
        self._ensure_connected()
        message = self._get_message(chat_id=chat_id, message_id=message_id)
        for row_index, button_row in enumerate(message.buttons):
            for column_index, button in enumerate(button_row):
                row_match = row is None or row == row_index
                column_match = column is None or column == column_index
                text_match = button_text is None or button.text == button_text
                data_match = data is None or button.data == data
                if row_match and column_match and text_match and data_match:
                    return message
        raise EntityNotFoundError(
            f"Button not found in message {message_id} for chat {chat_id}"
        )

    def _get_message(self, chat_id: int, message_id: int) -> Message:
        for message in self._messages:
            if message.chat_id == chat_id and message.message_id == message_id:
                return message
        raise EntityNotFoundError(
            f"Message not found: chat_id={chat_id}, message_id={message_id}"
        )

    def _chat_search_blob(self, chat: Chat) -> str:
        values = [chat.title, chat.username or "", chat.description or ""]
        return " ".join(values).casefold()

    def _ensure_connected(self) -> None:
        if not self._connected:
            raise TransportNotConnectedError(
                "Transport is not connected. Call connect() before using the SDK."
            )

    @staticmethod
    def _normalize_username(username: str | None) -> str:
        return (username or "").removeprefix("@").casefold()
