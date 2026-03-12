"""Telethon-backed transport for real Telegram access."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from sdk.config import TelegramSessionConfig
from sdk.errors import EntityNotFoundError, TelegramSDKError, TransportNotConnectedError
from sdk.models import BotStartResult, Chat, InlineButton, Message, SearchResults, User
from sdk.transports import TelegramTransport


class TelethonTelegramTransport(TelegramTransport):
    """Telegram transport implemented with Telethon."""

    def __init__(self, config: TelegramSessionConfig) -> None:
        self.config = config
        self._client: Any | None = None
        self._entity_cache: dict[int, Any] = {}
        self._message_cache: dict[tuple[int, int], Any] = {}
        self._telegram_client_cls: Any | None = None
        self._functions: Any | None = None
        self._types: Any | None = None
        self._utils: Any | None = None

    def connect(self) -> None:
        self._load_telethon()
        self._ensure_session_directory()

        if self._client is None:
            self._client = self._telegram_client_cls(
                self.config.session_name,
                int(self.config.api_id),
                self.config.api_hash,
            )

        self._client.connect()

        if self._client.is_user_authorized():
            return

        if not self.config.phone_number:
            raise TelegramSDKError(
                "phone_number is required to authenticate a Telethon user session."
            )
        if self.config.code_callback is None:
            raise TelegramSDKError(
                "code_callback is required to complete first-time Telethon login."
            )

        start_kwargs: dict[str, Any] = {
            "phone": self.config.phone_number,
            "code_callback": self.config.code_callback,
        }
        if self.config.password_callback is not None:
            start_kwargs["password"] = self.config.password_callback

        self._client.start(**start_kwargs)

    def close(self) -> None:
        if self._client is not None:
            self._client.disconnect()

    def search_public_chats(self, query: str, limit: int = 20) -> list[Chat]:
        client = self._client_or_raise()
        request = self._functions.contacts.SearchRequest(q=query, limit=limit)
        result = client(request)

        chats = [self._to_chat(entity) for entity in result.chats]
        bots = [
            self._bot_user_to_chat(user)
            for user in result.users
            if getattr(user, "bot", False) and getattr(user, "username", None)
        ]
        public_chats = [chat for chat in chats + bots if chat.is_public]
        return public_chats[:limit]

    def search_messages(self, query: str, limit: int = 50) -> SearchResults:
        client = self._client_or_raise()
        request = self._functions.messages.SearchGlobalRequest(
            q=query,
            filter=self._types.InputMessagesFilterEmpty(),
            min_date=None,
            max_date=None,
            offset_rate=0,
            offset_peer=self._types.InputPeerEmpty(),
            offset_id=0,
            limit=limit,
        )
        result = client(request)
        return self._build_search_results(query=query, result=result)

    def search_chat_messages(
        self,
        chat_id: int,
        query: str,
        limit: int = 50,
    ) -> list[Message]:
        client = self._client_or_raise()
        entity = self._get_entity_by_chat_id(chat_id)
        request = self._functions.messages.SearchRequest(
            peer=self._utils.get_input_peer(entity),
            q=query,
            filter=self._types.InputMessagesFilterEmpty(),
            min_date=None,
            max_date=None,
            offset_id=0,
            add_offset=0,
            limit=limit,
            max_id=0,
            min_id=0,
            hash=0,
            from_id=None,
            saved_peer_id=None,
            saved_reaction=None,
            top_msg_id=None,
        )
        result = client(request)
        messages = self._collect_messages(result.messages)
        return messages[:limit]

    def search_public_posts(self, query: str, limit: int = 50) -> SearchResults:
        client = self._client_or_raise()
        kwargs: dict[str, Any] = {
            "hashtag": None,
            "offset_rate": 0,
            "offset_peer": self._types.InputPeerEmpty(),
            "offset_id": 0,
            "limit": limit,
        }
        if self.config.allow_paid_stars is not None:
            kwargs["allow_paid_stars"] = self.config.allow_paid_stars

        request = self._functions.channels.SearchPostsRequest(query=query, **kwargs)
        result = client(request)
        return self._build_search_results(query=query, result=result)

    def resolve_username(self, username: str) -> Chat | User:
        client = self._client_or_raise()
        normalized = self._normalize_username(username)
        entity = client.get_entity(normalized)
        self._cache_entity(entity)
        if isinstance(entity, self._types.User):
            return self._to_user(entity)
        return self._to_chat(entity)

    def get_chat(self, chat_id: int) -> Chat:
        client = self._client_or_raise()
        entity = self._get_entity_by_chat_id(chat_id)
        chat = self._to_chat(entity)

        if isinstance(entity, self._types.Channel):
            try:
                full = client(
                    self._functions.channels.GetFullChannelRequest(
                        channel=self._utils.get_input_channel(entity)
                    )
                )
            except Exception:
                return chat
            return Chat(
                chat_id=chat.chat_id,
                title=chat.title,
                username=chat.username,
                kind=chat.kind,
                description=getattr(full.full_chat, "about", None),
                is_public=chat.is_public,
            )

        return chat

    def get_chat_history(
        self,
        chat_id: int,
        limit: int = 100,
        before_message_id: int | None = None,
    ) -> list[Message]:
        client = self._client_or_raise()
        entity = self._get_entity_by_chat_id(chat_id)
        raw_messages = client.get_messages(
            entity,
            limit=limit,
            max_id=before_message_id or 0,
        )
        return self._collect_messages(raw_messages)[:limit]

    def get_message(self, chat_id: int, message_id: int) -> Message:
        client = self._client_or_raise()
        entity = self._get_entity_by_chat_id(chat_id)
        raw_message = client.get_messages(entity, ids=message_id)
        if raw_message is None or isinstance(raw_message, self._types.MessageEmpty):
            raise EntityNotFoundError(
                f"Message not found: chat_id={chat_id}, message_id={message_id}"
            )
        return self._to_message(raw_message)

    def export_message_link(self, chat_id: int, message_id: int) -> str:
        client = self._client_or_raise()
        entity = self._get_entity_by_chat_id(chat_id)
        if not isinstance(entity, self._types.Channel):
            raise EntityNotFoundError(
                f"Chat {chat_id} is not a channel or supergroup that supports export links."
            )
        result = client(
            self._functions.channels.ExportMessageLinkRequest(
                channel=self._utils.get_input_channel(entity),
                id=message_id,
                thread=False,
                grouped=False,
            )
        )
        return result.link

    def send_text(self, chat_id: int, text: str) -> Message:
        client = self._client_or_raise()
        entity = self._get_entity_by_chat_id(chat_id)
        sent = client.send_message(entity, text)
        return self._to_message(sent)

    def start_bot(
        self,
        bot_username: str,
        parameter: str | None = None,
    ) -> BotStartResult:
        client = self._client_or_raise()
        normalized = self._normalize_username(bot_username)
        self._cache_entity(client.get_entity(normalized))
        result = client(
            self._functions.messages.StartBotRequest(
                bot=normalized,
                peer=normalized,
                start_param=parameter or "start",
            )
        )
        welcome_message = None
        if getattr(result, "updates", None):
            for update in result.updates:
                message = getattr(update, "message", None)
                if message is not None and getattr(message, "message", None):
                    welcome_message = message.message
                    break
        return BotStartResult(
            bot_username=normalized,
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
        raw_message = self._fetch_raw_message(chat_id=chat_id, message_id=message_id)
        for row_index, button_row in enumerate(getattr(raw_message, "buttons", None) or []):
            for column_index, button in enumerate(button_row):
                row_match = row is None or row == row_index
                column_match = column is None or column == column_index
                text_match = button_text is None or getattr(button, "text", None) == button_text
                data_match = data is None or getattr(button, "data", None) == data
                if row_match and column_match and text_match and data_match:
                    button.click()
                    return self.get_message(chat_id=chat_id, message_id=message_id)
        raise EntityNotFoundError(
            f"Button not found in message {message_id} for chat {chat_id}"
        )

    def _load_telethon(self) -> None:
        if self._telegram_client_cls is not None:
            return
        try:
            from telethon.sync import TelegramClient  # type: ignore
            from telethon import functions, types, utils  # type: ignore
        except ImportError as exc:
            raise TelegramSDKError(
                "Telethon is not installed. Install project dependencies first."
            ) from exc

        self._telegram_client_cls = TelegramClient
        self._functions = functions
        self._types = types
        self._utils = utils

    def _ensure_session_directory(self) -> None:
        session_path = Path(self.config.session_name)
        parent = session_path.parent
        if str(parent) not in {"", "."}:
            parent.mkdir(parents=True, exist_ok=True)

    def _client_or_raise(self) -> Any:
        if self._client is None:
            raise TransportNotConnectedError(
                "Transport is not connected. Call connect() before using the SDK."
            )
        return self._client

    def _get_entity_by_chat_id(self, chat_id: int) -> Any:
        client = self._client_or_raise()
        entity = self._entity_cache.get(chat_id)
        if entity is not None:
            return entity
        try:
            entity = client.get_entity(chat_id)
        except Exception as exc:
            raise EntityNotFoundError(
                f"Chat not found or not cached for chat_id={chat_id}"
            ) from exc
        self._cache_entity(entity)
        return entity

    def _build_search_results(self, query: str, result: Any) -> SearchResults:
        chats_map: dict[int, Chat] = {}
        for entity in self._iter_entities(result):
            self._cache_entity(entity)
            if isinstance(entity, self._types.User):
                if getattr(entity, "bot", False) and getattr(entity, "username", None):
                    chat = self._bot_user_to_chat(entity)
                    chats_map[chat.chat_id] = chat
                continue
            chat = self._to_chat(entity)
            chats_map[chat.chat_id] = chat

        messages = self._collect_messages(result.messages)
        for message in messages:
            if message.chat_id not in chats_map and message.chat_id in self._entity_cache:
                chats_map[message.chat_id] = self._to_chat(self._entity_cache[message.chat_id])

        return SearchResults(query=query, chats=list(chats_map.values()), messages=messages)

    def _collect_messages(self, raw_messages: Iterable[Any]) -> list[Message]:
        messages: list[Message] = []
        for raw in raw_messages:
            if isinstance(raw, self._types.MessageEmpty):
                continue
            try:
                messages.append(self._to_message(raw))
            except EntityNotFoundError:
                continue
        return messages

    def _cache_entity(self, entity: Any) -> int:
        peer_id = self._utils.get_peer_id(entity)
        self._entity_cache[peer_id] = entity
        return peer_id

    def _iter_entities(self, result: Any) -> Iterable[Any]:
        for entity in getattr(result, "chats", []) or []:
            yield entity
        for entity in getattr(result, "users", []) or []:
            yield entity

    def _to_chat(self, entity: Any) -> Chat:
        self._cache_entity(entity)
        if isinstance(entity, self._types.Channel):
            return Chat(
                chat_id=self._utils.get_peer_id(entity),
                title=entity.title,
                username=getattr(entity, "username", None),
                kind="supergroup" if getattr(entity, "megagroup", False) else "channel",
                description=None,
                is_public=bool(getattr(entity, "username", None)),
            )

        if isinstance(entity, self._types.Chat):
            return Chat(
                chat_id=self._utils.get_peer_id(entity),
                title=entity.title,
                username=None,
                kind="group",
                description=None,
                is_public=False,
            )

        if isinstance(entity, self._types.User) and getattr(entity, "bot", False):
            return self._bot_user_to_chat(entity)

        raise EntityNotFoundError(f"Entity is not a chat-like object: {entity!r}")

    def _bot_user_to_chat(self, entity: Any) -> Chat:
        self._cache_entity(entity)
        title = self._display_name(entity)
        return Chat(
            chat_id=self._utils.get_peer_id(entity),
            title=title,
            username=getattr(entity, "username", None),
            kind="bot",
            description=None,
            is_public=bool(getattr(entity, "username", None)),
        )

    def _to_user(self, entity: Any) -> User:
        self._cache_entity(entity)
        return User(
            user_id=self._utils.get_peer_id(entity),
            username=getattr(entity, "username", None),
            display_name=self._display_name(entity),
            is_bot=bool(getattr(entity, "bot", False)),
        )

    def _to_message(self, entity: Any) -> Message:
        chat_id = self._message_chat_id(entity)
        self._message_cache[(chat_id, entity.id)] = entity
        if chat_id not in self._entity_cache:
            raise EntityNotFoundError(f"Missing cached chat entity for message {entity.id}")

        permalink = None
        raw_text = getattr(entity, "message", None) or ""
        if not isinstance(raw_text, str):
            raw_text = str(raw_text)

        chat_entity = self._entity_cache[chat_id]
        if isinstance(chat_entity, self._types.Channel) and getattr(chat_entity, "username", None):
            permalink = f"https://t.me/{chat_entity.username}/{entity.id}"

        return Message(
            message_id=entity.id,
            chat_id=chat_id,
            sender_id=self._message_sender_id(entity),
            text=raw_text,
            timestamp=entity.date.isoformat(),
            permalink=permalink,
            buttons=self._extract_buttons(entity),
            reply_to_message_id=self._reply_to_message_id(entity),
            edit_timestamp=(
                entity.edit_date.isoformat()
                if getattr(entity, "edit_date", None) is not None
                else None
            ),
            is_edited=getattr(entity, "edit_date", None) is not None,
            metadata=self._message_metadata(entity),
        )

    def _extract_buttons(self, entity: Any) -> list[list[InlineButton]]:
        rows: list[list[InlineButton]] = []
        for raw_row in getattr(entity, "buttons", None) or []:
            row: list[InlineButton] = []
            for raw_button in raw_row:
                row.append(
                    InlineButton(
                        text=getattr(raw_button, "text", "") or "",
                        data=getattr(raw_button, "data", None),
                        url=getattr(raw_button, "url", None),
                    )
                )
            rows.append(row)
        return rows

    def _message_chat_id(self, message: Any) -> int:
        peer = getattr(message, "peer_id", None)
        if peer is not None:
            return self._utils.get_peer_id(peer)
        raise EntityNotFoundError(f"Message does not include peer information: {message!r}")

    def _get_raw_message(self, chat_id: int, message_id: int) -> Any:
        cached = self._message_cache.get((chat_id, message_id))
        if cached is not None:
            return cached
        return self._fetch_raw_message(chat_id=chat_id, message_id=message_id)

    def _fetch_raw_message(self, chat_id: int, message_id: int) -> Any:
        client = self._client_or_raise()
        entity = self._get_entity_by_chat_id(chat_id)
        raw_message = client.get_messages(entity, ids=message_id)
        if raw_message is None or isinstance(raw_message, self._types.MessageEmpty):
            raise EntityNotFoundError(
                f"Message not found: chat_id={chat_id}, message_id={message_id}"
            )
        self._message_cache[(chat_id, message_id)] = raw_message
        return raw_message

    def _message_sender_id(self, message: Any) -> int | None:
        sender = getattr(message, "from_id", None)
        if sender is None:
            return None
        return self._utils.get_peer_id(sender)

    @staticmethod
    def _reply_to_message_id(message: Any) -> int | None:
        reply_to = getattr(message, "reply_to", None)
        if reply_to is None:
            return None
        return getattr(reply_to, "reply_to_msg_id", None)

    def _message_metadata(self, message: Any) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "out": bool(getattr(message, "out", False)),
            "post": bool(getattr(message, "post", False)),
            "grouped_id": getattr(message, "grouped_id", None),
            "via_bot_id": None,
        }
        via_bot = getattr(message, "via_bot_id", None)
        if via_bot is not None:
            try:
                metadata["via_bot_id"] = self._utils.get_peer_id(via_bot)
            except Exception:
                metadata["via_bot_id"] = via_bot
        return metadata

    @staticmethod
    def _display_name(entity: Any) -> str:
        first = getattr(entity, "first_name", None) or ""
        last = getattr(entity, "last_name", None) or ""
        display = " ".join(part for part in [first, last] if part).strip()
        if display:
            return display
        return getattr(entity, "title", None) or getattr(entity, "username", None) or str(
            getattr(entity, "id", "unknown")
        )

    @staticmethod
    def _normalize_username(username: str) -> str:
        return username.removeprefix("@")
