"""Shared workflow for bot adapters built on top of TelegramTransport."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import replace
import time

from sdk.botkit.contracts import SessionStore
from sdk.botkit.errors import (
    BotAuthenticationError,
    BotCapabilityError,
    BotResponseError,
    BotTimeoutError,
    BotUnavailableError,
)
from sdk.botkit.models import BotCommand, BotRequest, BotResponse, BotSession
from sdk.errors import EntityNotFoundError, TelegramSDKError
from sdk.models import Chat, Message, User
from sdk.transports import TelegramTransport


class BaseBotAdapter(ABC):
    """Template-method base for bot-specific adapters."""

    _TRANSIENT_RETRYABLE_ERROR_NAMES = {
        "FloodWaitError",
        "FloodTestPhoneWaitError",
        "InterdcCallErrorError",
        "InterdcCallRichErrorError",
        "ReadCancelledError",
        "RpcCallFailError",
        "ServerError",
        "SlowModeWaitError",
        "TimedOutError",
        "TimeoutError",
    }

    bot_id: str
    bot_username: str

    def __init__(self, transport: TelegramTransport, session_store: SessionStore) -> None:
        self.transport = transport
        self.session_store = session_store

    def execute(self, request: BotRequest) -> BotResponse:
        if not self.supports(request.command_name):
            raise BotCapabilityError(
                f"Bot '{self.bot_id}' does not support command '{request.command_name}'."
            )

        session = self._get_or_create_session(request)
        self.bootstrap_session(session, request)
        try:
            payload = self.map_command(request, session)
            sent_message = self.transport.send_text(chat_id=session.chat_id, text=payload)
            session.state["last_request_message_id"] = sent_message.message_id
            reply_messages = self.collect_reply_messages(
                session=session,
                sent_message=sent_message,
                request=request,
            )
        except BotTimeoutError:
            raise
        except EntityNotFoundError as exc:
            raise BotUnavailableError(str(exc)) from exc
        except TelegramSDKError:
            raise
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise BotResponseError(
                f"Failed to execute '{request.command_name}' for bot '{self.bot_id}'."
            ) from exc

        try:
            response = self.parse_response(
                request=request,
                session=session,
                sent_message=sent_message,
                reply_messages=reply_messages,
            )
        except TelegramSDKError:
            raise
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise BotResponseError(
                f"Failed to parse response for '{request.command_name}' from "
                f"bot '{self.bot_id}'."
            ) from exc
        session.state["last_response_message_ids"] = [
            message.message_id for message in reply_messages
        ]
        self._save_session(request, session)
        return response

    def bootstrap_session(self, session: BotSession, request: BotRequest) -> None:
        """Ensure the bot conversation is started and session metadata is current."""

        if session.state.get("started"):
            return
        try:
            self.call_with_transport_retry(
                lambda: self.transport.start_bot(bot_username=self.bot_username),
                request=request,
                operation="start_bot",
                allow_replay=True,
            )
        except Exception as exc:
            raise BotAuthenticationError(
                f"Failed to bootstrap bot session for '{self.bot_username}'."
            ) from exc
        session.state["started"] = True
        session.authenticated = True

    def collect_reply_messages(
        self,
        *,
        session: BotSession,
        sent_message: Message,
        request: BotRequest,
    ) -> list[Message]:
        """Poll chat history until a stable set of replies is observed."""

        poll_attempts = int(request.options.get("poll_attempts", 6))
        poll_interval_seconds = float(request.options.get("poll_interval_seconds", 2.0))
        history_limit = int(request.options.get("history_limit", 20))
        stable_cycles_required = int(request.options.get("stable_cycles_required", 1))

        stable_cycles = 0
        previous_ids: tuple[int, ...] = ()
        collected: dict[int, Message] = {}

        for attempt in range(poll_attempts):
            history = self.call_with_transport_retry(
                lambda: self.transport.get_chat_history(
                    chat_id=session.chat_id,
                    limit=history_limit,
                ),
                request=request,
                operation="get_chat_history",
                allow_replay=True,
            )
            replies = self.filter_reply_messages(
                session=session,
                history=history,
                sent_message=sent_message,
                request=request,
            )
            for reply in replies:
                collected[reply.message_id] = reply

            reply_ids = tuple(reply.message_id for reply in replies)
            if reply_ids and reply_ids == previous_ids:
                stable_cycles += 1
            else:
                stable_cycles = 0
            previous_ids = reply_ids

            if reply_ids and stable_cycles >= stable_cycles_required:
                return [collected[key] for key in sorted(collected)]
            if attempt < poll_attempts - 1:
                time.sleep(poll_interval_seconds)

        if collected:
            return [collected[key] for key in sorted(collected)]
        raise BotTimeoutError(
            f"Timed out waiting for replies from bot '{self.bot_id}' for command "
            f"'{request.command_name}'."
        )

    def filter_reply_messages(
        self,
        *,
        session: BotSession,
        history: list[Message],
        sent_message: Message,
        request: BotRequest,
    ) -> list[Message]:
        """Default reply filter using message id correlation."""

        replies = [
            message
            for message in history
            if message.message_id > sent_message.message_id and message.text.strip()
        ]
        replies.sort(key=lambda item: item.message_id)
        return replies

    def _get_or_create_session(self, request: BotRequest) -> BotSession:
        session_key = self.build_session_key(request)
        existing = self.session_store.get(session_key)
        if existing is not None:
            return existing

        bot_chat = self.resolve_bot_chat()
        session = BotSession(
            bot_id=self.bot_id,
            bot_username=self.bot_username,
            chat_id=bot_chat.chat_id,
        )
        self.session_store.save(session_key, session)
        return session

    def _save_session(self, request: BotRequest, session: BotSession) -> None:
        self.session_store.save(self.build_session_key(request), session)

    def build_session_key(self, request: BotRequest) -> str:
        """Build a stable session key that is safe for multi-tenant applications."""

        if request.context.chat_id is not None:
            return (
                f"{request.context.tenant_id}:{request.context.user_id}:{self.bot_id}:"
                f"{request.context.chat_id}"
            )
        return f"{request.context.tenant_id}:{request.context.user_id}:{self.bot_id}"

    def resolve_bot_chat(self) -> Chat:
        """Resolve a bot username to a normalized chat record."""

        try:
            entity = self.call_with_transport_retry(
                lambda: self.transport.resolve_username(self.bot_username),
                request=None,
                operation="resolve_username",
                allow_replay=True,
            )
        except EntityNotFoundError as exc:
            raise BotUnavailableError(f"Bot not found: {self.bot_username}") from exc

        if isinstance(entity, Chat):
            if entity.kind != "bot":
                raise BotUnavailableError(
                    f"Resolved entity is not a bot: {self.bot_username}"
                )
            return entity
        if isinstance(entity, User) and entity.is_bot:
            return Chat(
                chat_id=entity.user_id,
                title=entity.display_name or entity.username or str(entity.user_id),
                username=entity.username,
                kind="bot",
                is_public=bool(entity.username),
            )
        raise BotUnavailableError(f"Bot not found: {self.bot_username}")

    def call_with_transport_retry(
        self,
        func,
        *,
        request: BotRequest | None,
        operation: str,
        allow_replay: bool,
    ):
        max_attempts = 1 if not allow_replay else self._retry_attempts(request)
        backoff_seconds = self._retry_backoff_seconds(request)
        max_wait_seconds = self._retry_max_wait_seconds(request)

        attempt = 0
        while True:
            attempt += 1
            try:
                return func()
            except Exception as exc:
                if attempt >= max_attempts:
                    raise
                retry_delay = self._retry_delay_for_exception(
                    exc,
                    attempt=attempt,
                    backoff_seconds=backoff_seconds,
                    max_wait_seconds=max_wait_seconds,
                )
                if retry_delay is None:
                    raise
                if retry_delay > 0:
                    time.sleep(retry_delay)

    def _retry_attempts(self, request: BotRequest | None) -> int:
        if request is None:
            return 3
        return max(1, int(request.options.get("transport_retry_attempts", 3)))

    def _retry_backoff_seconds(self, request: BotRequest | None) -> float:
        if request is None:
            return 0.5
        return max(0.0, float(request.options.get("transport_retry_backoff_seconds", 0.5)))

    def _retry_max_wait_seconds(self, request: BotRequest | None) -> float:
        if request is None:
            return 8.0
        return max(0.0, float(request.options.get("transport_retry_max_wait_seconds", 8.0)))

    def _retry_delay_for_exception(
        self,
        exc: Exception,
        *,
        attempt: int,
        backoff_seconds: float,
        max_wait_seconds: float,
    ) -> float | None:
        if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
            return min(backoff_seconds * (2 ** (attempt - 1)), max_wait_seconds)

        error_name = exc.__class__.__name__
        if error_name not in self._TRANSIENT_RETRYABLE_ERROR_NAMES:
            return None

        wait_seconds = getattr(exc, "seconds", None)
        if isinstance(wait_seconds, int | float):
            return min(float(wait_seconds), max_wait_seconds)
        return min(backoff_seconds * (2 ** (attempt - 1)), max_wait_seconds)

    @staticmethod
    def snapshot_message(message: Message) -> Message:
        """Clone a message so later edits do not mutate stored snapshots."""

        return replace(
            message,
            buttons=[[replace(button) for button in row] for row in message.buttons],
        )

    @staticmethod
    def merge_messages(primary: list[Message], secondary: list[Message]) -> list[Message]:
        """Return a stable, deduplicated message list."""

        seen: set[tuple[int, int, str]] = set()
        merged: list[Message] = []
        for message in [*primary, *secondary]:
            key = (message.chat_id, message.message_id, message.text)
            if key in seen:
                continue
            seen.add(key)
            merged.append(message)
        return merged

    @abstractmethod
    def supports(self, command_name: str) -> bool:
        """Return whether the adapter supports a canonical command."""

    @abstractmethod
    def get_supported_commands(self) -> list[BotCommand]:
        """Return canonical commands supported by this adapter."""

    @abstractmethod
    def map_command(self, request: BotRequest, session: BotSession) -> str:
        """Map a canonical request into the raw bot input text."""

    @abstractmethod
    def parse_response(
        self,
        *,
        request: BotRequest,
        session: BotSession,
        sent_message: Message,
        reply_messages: list[Message],
    ) -> BotResponse:
        """Normalize raw bot replies into a BotResponse."""
