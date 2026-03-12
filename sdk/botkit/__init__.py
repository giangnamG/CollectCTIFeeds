"""Bot orchestration layer built on top of the Telegram transport boundary."""

from sdk.botkit.base import BaseBotAdapter
from sdk.botkit.contracts import IBotAdapter, SessionStore
from sdk.botkit.errors import (
    BotAuthenticationError,
    BotCapabilityError,
    BotExecutionError,
    BotResponseError,
    BotTimeoutError,
    BotUnavailableError,
    BotValidationError,
)
from sdk.botkit.models import (
    BotCapability,
    BotCommand,
    BotContext,
    BotRequest,
    BotResponse,
    BotSession,
    ExecutionMode,
    RetryPolicy,
)
from sdk.botkit.registry import BotRegistry, CommandRegistry
from sdk.botkit.sdk import BotSDK

__all__ = [
    "BaseBotAdapter",
    "BotAuthenticationError",
    "BotCapability",
    "BotCapabilityError",
    "BotCommand",
    "BotContext",
    "BotExecutionError",
    "BotRegistry",
    "BotRequest",
    "BotResponse",
    "BotResponseError",
    "BotSDK",
    "BotSession",
    "BotTimeoutError",
    "BotUnavailableError",
    "BotValidationError",
    "CommandRegistry",
    "ExecutionMode",
    "IBotAdapter",
    "RetryPolicy",
    "SessionStore",
]
