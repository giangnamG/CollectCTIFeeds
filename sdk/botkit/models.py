"""Domain models for bot orchestration on top of Telegram primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sdk.models import Message


class ExecutionMode(str, Enum):
    """How a command is expected to complete."""

    SYNC = "sync"
    ASYNC = "async"
    CONVERSATIONAL = "conversational"


class BotCapability(str, Enum):
    """High-level bot features used for routing and validation."""

    SEARCH = "search"
    MONITORING = "monitoring"
    TRADING = "trading"
    CALLBACKS = "callbacks"
    PAGINATION = "pagination"


@dataclass(slots=True)
class RetryPolicy:
    """Transport-agnostic retry hints for bot command execution."""

    max_attempts: int = 3
    backoff_seconds: float = 1.0


@dataclass(slots=True)
class BotCommand:
    """Canonical command metadata exposed to the application layer."""

    name: str
    aliases: list[str] = field(default_factory=list)
    parameters: dict[str, str] = field(default_factory=dict)
    capabilities: set[BotCapability] = field(default_factory=set)
    execution_mode: ExecutionMode = ExecutionMode.SYNC
    timeout_seconds: float = 15.0
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)


@dataclass(slots=True)
class BotContext:
    """Execution context passed from the application layer into the SDK."""

    tenant_id: str
    user_id: str
    chat_id: int | None = None
    correlation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BotRequest:
    """Normalized bot command request."""

    bot_id: str
    command_name: str
    params: dict[str, Any] = field(default_factory=dict)
    context: BotContext = field(
        default_factory=lambda: BotContext(tenant_id="default", user_id="default")
    )
    request_id: str | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BotResponse:
    """Normalized bot execution response returned to application code."""

    bot_id: str
    command_name: str
    status: str
    data: dict[str, Any] = field(default_factory=dict)
    raw_messages: list[Message] = field(default_factory=list)
    correlation_id: str | None = None


@dataclass(slots=True)
class BotSession:
    """Per bot/user session state for conversational workflows."""

    bot_id: str
    bot_username: str
    chat_id: int
    authenticated: bool = False
    state: dict[str, Any] = field(default_factory=dict)
