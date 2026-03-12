"""Transport adapters for different Telegram backends."""

from sdk.adapters.memory import MemoryTelegramTransport

try:
    from sdk.adapters.telethon import TelethonTelegramTransport
except Exception:  # pragma: no cover - optional dependency import guard
    TelethonTelegramTransport = None

__all__ = ["MemoryTelegramTransport", "TelethonTelegramTransport"]
