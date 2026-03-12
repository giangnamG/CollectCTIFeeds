"""Helpers for resolving flexible Telegram references."""

from __future__ import annotations

import re

from sdk.errors import InvalidEntityReferenceError
from sdk.models import Chat, Message, MessageButtonRef, User
from sdk.transports import TelegramTransport

_TELEGRAM_LINK_PATTERN = re.compile(
    r"^(?:https?://)?t\.me/(?P<username>[A-Za-z0-9_]{5,32})(?:/\d+)?(?:[/?#].*)?$",
    re.IGNORECASE,
)
_UNSUPPORTED_LINK_PREFIXES = {
    "addstickers",
    "c",
    "joinchat",
    "proxy",
    "share",
    "socks",
}


def resolve_chat_reference(
    transport: TelegramTransport,
    reference: int | str,
) -> Chat:
    """Resolve chat references accepted as id, @username, or t.me link."""

    if isinstance(reference, int):
        return transport.get_chat(reference)

    raw_reference = reference.strip()
    if not raw_reference:
        raise InvalidEntityReferenceError("Chat reference cannot be blank.")

    if _looks_like_integer(raw_reference):
        return transport.get_chat(int(raw_reference))

    normalized_username = _normalize_username_reference(raw_reference)
    entity = transport.resolve_username(normalized_username)
    if isinstance(entity, Chat):
        return entity
    if isinstance(entity, User):
        return Chat(
            chat_id=entity.user_id,
            title=entity.display_name or entity.username or str(entity.user_id),
            username=entity.username,
            kind="bot" if entity.is_bot else "private",
            is_public=bool(entity.username),
        )
    raise InvalidEntityReferenceError(
        f"Unsupported entity resolved from reference: {raw_reference}"
    )


def list_message_button_refs(message: Message) -> list[MessageButtonRef]:
    """Return stable references for all inline buttons in a message."""

    button_refs: list[MessageButtonRef] = []
    for row_index, button_row in enumerate(message.buttons):
        for column_index, button in enumerate(button_row):
            button_refs.append(
                MessageButtonRef(
                    row=row_index,
                    column=column_index,
                    text=button.text,
                    data=button.data,
                    url=button.url,
                )
            )
    return button_refs


def _normalize_username_reference(reference: str) -> str:
    link_match = _TELEGRAM_LINK_PATTERN.match(reference)
    if link_match:
        username = link_match.group("username")
        if username.casefold() in _UNSUPPORTED_LINK_PREFIXES:
            raise InvalidEntityReferenceError(
                f"Unsupported Telegram reference format: {reference}"
            )
        return username

    normalized = reference.removeprefix("@").strip()
    if not normalized:
        raise InvalidEntityReferenceError("Chat reference cannot be blank.")
    if normalized.casefold() in _UNSUPPORTED_LINK_PREFIXES:
        raise InvalidEntityReferenceError(
            f"Unsupported Telegram reference format: {reference}"
        )
    if "/" in normalized or " " in normalized:
        raise InvalidEntityReferenceError(
            f"Unsupported Telegram reference format: {reference}"
        )
    return normalized


def _looks_like_integer(reference: str) -> bool:
    stripped = reference.strip()
    if not stripped:
        return False
    if stripped.startswith("-"):
        return stripped[1:].isdigit()
    return stripped.isdigit()
