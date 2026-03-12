"""Custom exceptions raised by the SDK."""


class TelegramSDKError(Exception):
    """Base exception for all SDK-specific errors."""


class TransportNotConnectedError(TelegramSDKError):
    """Raised when an operation requires an active transport session."""


class EntityNotFoundError(TelegramSDKError):
    """Raised when a requested chat, user, or message cannot be found."""


class InvalidEntityReferenceError(TelegramSDKError):
    """Raised when a chat reference cannot be parsed or normalized."""
