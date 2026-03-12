"""Configuration models for Telegram client sessions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from sdk.errors import TelegramSDKError


@dataclass(slots=True)
class TelegramSessionConfig:
    """Runtime configuration for a Telegram-backed transport."""

    api_id: str
    api_hash: str
    session_name: str = "default"
    phone_number: str | None = None
    code_callback: Callable[[], str] | None = None
    password_callback: Callable[[], str] | None = None
    allow_paid_stars: int | None = None

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        code_callback: Callable[[], str] | None = None,
        password_callback: Callable[[], str] | None = None,
    ) -> "TelegramSessionConfig":
        """Load session config from a JSON file."""

        config_path = Path(path)
        if not config_path.exists():
            raise TelegramSDKError(f"Config file not found: {config_path}")

        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TelegramSDKError(
                f"Config file is not valid JSON: {config_path}"
            ) from exc

        required_fields = ["api_id", "api_hash"]
        missing = [field for field in required_fields if not payload.get(field)]
        if missing:
            missing_fields = ", ".join(missing)
            raise TelegramSDKError(
                f"Config file is missing required fields: {missing_fields}"
            )

        return cls(
            api_id=str(payload["api_id"]),
            api_hash=str(payload["api_hash"]),
            session_name=str(payload.get("session_name", "default")),
            phone_number=payload.get("phone_number"),
            code_callback=code_callback,
            password_callback=password_callback,
            allow_paid_stars=payload.get("allow_paid_stars"),
        )
