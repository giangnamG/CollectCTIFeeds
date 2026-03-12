"""Checkpoint helpers for long-running bot crawls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class BotSearchCheckpointState:
    """Persisted crawl state loaded from a checkpoint file."""

    path: str
    total_pages: int | None
    pages_collected: int
    last_page_number: int | None
    is_complete: bool
    resumed: bool


class BotSearchCheckpointWriter:
    """Append-only JSONL checkpoint file for large paginated bot crawls."""

    _VERSION = 1

    def __init__(
        self,
        path: str,
        *,
        bot_id: str,
        bot_username: str,
        query: str,
        resume: bool = False,
    ) -> None:
        self.path = Path(path)
        self.bot_id = bot_id
        self.bot_username = bot_username
        self.query = query
        self.resumed = resume and self.path.exists()
        self._page_signatures: dict[int, str] = {}
        self._page_aggregates: dict[int, dict[str, list[str]]] = {}
        self._total_pages: int | None = None
        self._complete = False
        self._load_or_initialize()

    def state(self) -> BotSearchCheckpointState:
        return BotSearchCheckpointState(
            path=str(self.path),
            total_pages=self._total_pages,
            pages_collected=len(self._page_signatures),
            last_page_number=max(self._page_signatures, default=None),
            is_complete=self._complete,
            resumed=self.resumed,
        )

    def append_page(
        self,
        *,
        page_number: int,
        total_pages: int,
        signature: str,
        text: str,
        message_id: int,
        timestamp: str,
        edit_timestamp: str | None,
        extracted_usernames: list[str],
        extracted_links: list[str],
        extracted_chat_usernames: list[str],
    ) -> bool:
        if self._page_signatures.get(page_number) == signature:
            self._total_pages = total_pages
            return False

        self._page_signatures[page_number] = signature
        self._page_aggregates[page_number] = {
            "extracted_usernames": list(extracted_usernames),
            "extracted_links": list(extracted_links),
            "extracted_chat_usernames": list(extracted_chat_usernames),
        }
        self._total_pages = total_pages
        self._append_record(
            {
                "type": "page",
                "page_number": page_number,
                "total_pages": total_pages,
                "signature": signature,
                "message_id": message_id,
                "timestamp": timestamp,
                "edit_timestamp": edit_timestamp,
                "text": text,
                "extracted_usernames": list(extracted_usernames),
                "extracted_links": list(extracted_links),
                "extracted_chat_usernames": list(extracted_chat_usernames),
                "recorded_at": _utc_now(),
            }
        )
        return True

    def mark_complete(self, *, total_pages: int) -> None:
        self._total_pages = total_pages
        self._complete = True
        self._append_record(
            {
                "type": "complete",
                "total_pages": total_pages,
                "pages_collected": len(self._page_signatures),
                "completed_at": _utc_now(),
            }
        )

    def combined_aggregates(self) -> dict[str, list[str]]:
        usernames = _dedupe_in_order(
            value
            for page_number in sorted(self._page_aggregates)
            for value in self._page_aggregates[page_number]["extracted_usernames"]
        )
        links = _dedupe_in_order(
            value
            for page_number in sorted(self._page_aggregates)
            for value in self._page_aggregates[page_number]["extracted_links"]
        )
        chat_usernames = _dedupe_in_order(
            value
            for page_number in sorted(self._page_aggregates)
            for value in self._page_aggregates[page_number]["extracted_chat_usernames"]
        )
        return {
            "extracted_usernames": usernames,
            "extracted_links": links,
            "extracted_chat_usernames": chat_usernames,
        }

    def _load_or_initialize(self) -> None:
        if self.resumed:
            self._load_existing()
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            handle.write("")
        self._append_record(
            {
                "type": "meta",
                "version": self._VERSION,
                "bot_id": self.bot_id,
                "bot_username": self.bot_username,
                "query": self.query,
                "created_at": _utc_now(),
            }
        )

    def _load_existing(self) -> None:
        with self.path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                record = json.loads(line)
                record_type = record.get("type")
                if record_type == "meta":
                    self._validate_meta(record)
                    continue
                if record_type == "page":
                    page_number = int(record["page_number"])
                    self._page_signatures[page_number] = str(record["signature"])
                    self._page_aggregates[page_number] = {
                        "extracted_usernames": list(record.get("extracted_usernames", [])),
                        "extracted_links": list(record.get("extracted_links", [])),
                        "extracted_chat_usernames": list(
                            record.get("extracted_chat_usernames", [])
                        ),
                    }
                    total_pages = record.get("total_pages")
                    if total_pages is not None:
                        self._total_pages = int(total_pages)
                    continue
                if record_type == "complete":
                    total_pages = record.get("total_pages")
                    if total_pages is not None:
                        self._total_pages = int(total_pages)
                    self._complete = True

    def _validate_meta(self, record: dict[str, Any]) -> None:
        if record.get("version") != self._VERSION:
            raise ValueError(
                f"Unsupported checkpoint version in {self.path}: {record.get('version')}"
            )
        if record.get("bot_id") != self.bot_id:
            raise ValueError(
                f"Checkpoint {self.path} belongs to bot '{record.get('bot_id')}', "
                f"not '{self.bot_id}'."
            )
        if record.get("query") != self.query:
            raise ValueError(
                f"Checkpoint {self.path} belongs to query '{record.get('query')}', "
                f"not '{self.query}'."
            )

    def _append_record(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def _dedupe_in_order(values) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = value.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(value)
    return ordered


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
