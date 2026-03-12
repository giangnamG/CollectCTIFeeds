"""Registries for bot adapters and canonical bot commands."""

from __future__ import annotations

from dataclasses import replace

from sdk.botkit.contracts import IBotAdapter
from sdk.botkit.errors import BotCapabilityError
from sdk.botkit.models import BotCommand


class BotRegistry:
    """Lookup table for bot adapters."""

    def __init__(self, adapters: list[IBotAdapter] | None = None) -> None:
        self._adapters: dict[str, IBotAdapter] = {}
        for adapter in adapters or []:
            self.register(adapter)

    def register(self, adapter: IBotAdapter) -> None:
        self._adapters[adapter.bot_id] = adapter

    def resolve(self, bot_id: str) -> IBotAdapter:
        try:
            return self._adapters[bot_id]
        except KeyError as exc:
            raise BotCapabilityError(f"No bot adapter registered for '{bot_id}'.") from exc

    def list_bot_ids(self) -> list[str]:
        return sorted(self._adapters)

    def all(self) -> list[IBotAdapter]:
        return [self._adapters[bot_id] for bot_id in self.list_bot_ids()]


class CommandRegistry:
    """Per-bot canonical command registry with alias resolution."""

    def __init__(self) -> None:
        self._commands: dict[str, dict[str, BotCommand]] = {}
        self._aliases: dict[str, dict[str, str]] = {}

    def register(self, bot_id: str, command: BotCommand) -> None:
        self._commands.setdefault(bot_id, {})[command.name] = command
        alias_map = self._aliases.setdefault(bot_id, {})
        alias_map[command.name] = command.name
        for alias in command.aliases:
            alias_map[alias] = command.name

    def register_adapter(self, adapter: IBotAdapter) -> None:
        for command in adapter.get_supported_commands():
            self.register(adapter.bot_id, command)

    def resolve_for_bot(self, bot_id: str, command_name: str) -> BotCommand:
        try:
            canonical_name = self._aliases[bot_id][command_name]
            return self._commands[bot_id][canonical_name]
        except KeyError as exc:
            raise BotCapabilityError(
                f"Command '{command_name}' is not registered for bot '{bot_id}'."
            ) from exc

    def list_for_bot(self, bot_id: str) -> list[BotCommand]:
        return [
            self._commands[bot_id][name]
            for name in sorted(self._commands.get(bot_id, {}))
        ]

    def normalize_request_name(self, bot_id: str, command_name: str) -> str:
        return self.resolve_for_bot(bot_id, command_name).name

    def clone_for_bot(self, bot_id: str, command_name: str) -> BotCommand:
        return replace(self.resolve_for_bot(bot_id, command_name))
