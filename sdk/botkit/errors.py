"""Bot orchestration errors."""

from sdk.errors import TelegramSDKError


class BotExecutionError(TelegramSDKError):
    """Base exception for bot orchestration failures."""


class BotUnavailableError(BotExecutionError):
    """Raised when a bot cannot be reached or resolved."""


class BotTimeoutError(BotExecutionError):
    """Raised when a bot reply does not arrive within the allowed window."""


class BotResponseError(BotExecutionError):
    """Raised when a bot response cannot be parsed or normalized."""


class BotAuthenticationError(BotExecutionError):
    """Raised when bot-specific authentication or session bootstrap fails."""


class BotCapabilityError(BotExecutionError):
    """Raised when a bot does not support the requested command."""


class BotValidationError(BotExecutionError):
    """Raised when a bot request fails canonical command validation."""
