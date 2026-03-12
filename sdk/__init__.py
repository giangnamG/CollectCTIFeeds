"""Public package exports for the Telegram SDK."""

from sdk.botkit import (
    BaseBotAdapter,
    BotCapability,
    BotCommand,
    BotContext,
    BotRegistry,
    BotRequest,
    BotResponse,
    BotSDK,
    BotSession,
    BotValidationError,
    CommandRegistry,
    ExecutionMode,
)
from sdk.client import TelegramSDK
from sdk.config import TelegramSessionConfig
from sdk.errors import InvalidEntityReferenceError
from sdk.models import (
    BotSearchResults,
    BotStartResult,
    Chat,
    ChatInspection,
    HistoryCursor,
    InspectionPagination,
    InspectionDirection,
    InlineButton,
    KeywordDiscoveryResults,
    Message,
    MessageButtonRef,
    MessageInspection,
    SearchResults,
    User,
)
from sdk.adapters.memory import MemoryTelegramTransport
from sdk.botkit.adapters import EnSearchBotAdapter, MonitoringBotAdapter
from sdk.session import InMemorySessionStore, RedisSessionStore
from sdk.tool_schema import (
    TelegramToolCatalog,
    ToolParameterSchema,
    ToolSchema,
    build_default_tool_schemas,
)
from sdk.transports import TelegramTransport
from sdk.workflows.discovery import KeywordDiscoveryWorkflow

try:
    from sdk.adapters.telethon import TelethonTelegramTransport
except Exception:  # pragma: no cover - optional dependency import guard
    TelethonTelegramTransport = None

__all__ = [
    "BaseBotAdapter",
    "BotCapability",
    "BotCommand",
    "BotContext",
    "BotRegistry",
    "BotStartResult",
    "BotSearchResults",
    "BotRequest",
    "BotResponse",
    "BotSDK",
    "BotSession",
    "BotValidationError",
    "Chat",
    "ChatInspection",
    "CommandRegistry",
    "EnSearchBotAdapter",
    "ExecutionMode",
    "HistoryCursor",
    "InMemorySessionStore",
    "InspectionPagination",
    "InspectionDirection",
    "InlineButton",
    "KeywordDiscoveryResults",
    "InvalidEntityReferenceError",
    "MemoryTelegramTransport",
    "Message",
    "MessageButtonRef",
    "MessageInspection",
    "MonitoringBotAdapter",
    "KeywordDiscoveryWorkflow",
    "RedisSessionStore",
    "SearchResults",
    "TelegramSDK",
    "TelegramSessionConfig",
    "TelethonTelegramTransport",
    "TelegramToolCatalog",
    "TelegramTransport",
    "ToolParameterSchema",
    "ToolSchema",
    "User",
    "build_default_tool_schemas",
]
