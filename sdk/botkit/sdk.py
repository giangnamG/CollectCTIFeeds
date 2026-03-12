"""Application-facing orchestrator for Telegram bot adapters."""

from __future__ import annotations

from dataclasses import replace

from sdk.botkit.contracts import IBotAdapter
from sdk.botkit.errors import BotValidationError
from sdk.botkit.models import BotCommand, BotRequest, BotResponse
from sdk.botkit.registry import BotRegistry, CommandRegistry
from sdk.transports import TelegramTransport


class BotSDK:
    """Resolve bot adapters and execute canonical bot commands."""

    def __init__(
        self,
        transport: TelegramTransport,
        bot_registry: BotRegistry | None = None,
        command_registry: CommandRegistry | None = None,
    ) -> None:
        self.transport = transport
        self.bot_registry = bot_registry or BotRegistry()
        self.command_registry = command_registry or CommandRegistry()

    def connect(self) -> None:
        self.transport.connect()

    def close(self) -> None:
        self.transport.close()

    def register_adapter(self, adapter: IBotAdapter) -> None:
        self.bot_registry.register(adapter)
        self.command_registry.register_adapter(adapter)

    def execute_command(self, request: BotRequest) -> BotResponse:
        adapter = self.bot_registry.resolve(request.bot_id)
        command = self.command_registry.resolve_for_bot(
            request.bot_id,
            request.command_name,
        )
        normalized_request = replace(request, command_name=command.name)
        self._validate_request(command, normalized_request)
        return adapter.execute(normalized_request)

    def get_supported_commands(self, bot_id: str) -> list[BotCommand]:
        return self.command_registry.list_for_bot(bot_id)

    def list_bots(self) -> list[str]:
        return self.bot_registry.list_bot_ids()

    @staticmethod
    def _validate_request(command: BotCommand, request: BotRequest) -> None:
        missing: list[str] = []
        blank: list[str] = []
        for parameter_name in command.parameters:
            if parameter_name not in request.params:
                missing.append(parameter_name)
                continue
            value = request.params[parameter_name]
            if value is None:
                blank.append(parameter_name)
                continue
            if isinstance(value, str) and not value.strip():
                blank.append(parameter_name)
        if missing or blank:
            problems: list[str] = []
            if missing:
                problems.append(f"missing params: {', '.join(sorted(missing))}")
            if blank:
                problems.append(f"blank params: {', '.join(sorted(blank))}")
            raise BotValidationError(
                f"Invalid request for command '{command.name}': {'; '.join(problems)}"
            )
