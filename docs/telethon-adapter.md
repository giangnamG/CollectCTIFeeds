# Telethon Adapter

## Purpose

This document describes the real Telegram backend adapter implemented with Telethon and how it fits into the existing SDK without changing the public SDK API.

## Goal

The SDK already exposed stable public methods through `TelegramSDK`.

The purpose of the Telethon adapter is to replace the in-memory development backend with a real Telegram client backend while preserving the same application-facing methods.

That means code using:

- `search_public_chats`
- `search_messages`
- `search_chat_messages`
- `search_public_posts`
- `resolve_username`
- `get_chat`
- `get_chat_history`
- `export_message_link`
- `send_text`
- `start_bot`

does not need to change.

## Files Added or Updated

Added:

- [`sdk/adapters/telethon.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/adapters/telethon.py)
- [`docs/telethon-adapter.md`](/home/kali/Desktop/CollectCTIFeeds/docs/telethon-adapter.md)

Updated:

- [`sdk/config.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/config.py)
- [`sdk/adapters/__init__.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/adapters/__init__.py)
- [`pyproject.toml`](/home/kali/Desktop/CollectCTIFeeds/pyproject.toml)
- [`README.md`](/home/kali/Desktop/CollectCTIFeeds/README.md)

## Dependency

The adapter depends on:

- `telethon>=1.42,<2`

This was added to [`pyproject.toml`](/home/kali/Desktop/CollectCTIFeeds/pyproject.toml).

The version is intentionally pinned below `2` because the current adapter is written for the stable Telethon 1.x API shape.

## Public SDK API

The `TelegramSDK` API remains unchanged.

Only the transport implementation changes.

Before:

```python
from sdk import MemoryTelegramTransport, TelegramSDK

transport = MemoryTelegramTransport(...)
sdk = TelegramSDK(transport)
sdk.search_messages("vcam")
```

After:

```python
from sdk import TelegramSDK, TelegramSessionConfig
from sdk.adapters.telethon import TelethonTelegramTransport

config = TelegramSessionConfig(
    api_id="123456",
    api_hash="your_api_hash",
    session_name="collector",
    phone_number="+15550000000",
    code_callback=lambda: input("Telegram login code: "),
)

transport = TelethonTelegramTransport(config)
sdk = TelegramSDK(transport)
sdk.connect()
sdk.search_messages("vcam")
```

## Adapter Responsibilities

The Telethon adapter implements the transport contract from:

- [`sdk/transports.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/transports.py)

Implemented operations:

- connect to Telegram
- authenticate a user session
- search public chats
- search globally across messages
- search messages inside a specific chat
- search public posts
- resolve usernames
- fetch chat metadata
- fetch chat history
- export message links
- send text messages
- start bot conversations

## Authentication Model

The adapter uses:

- `api_id`
- `api_hash`
- `session_name`
- `phone_number`
- `code_callback`
- `password_callback`

These are defined in:

- [`sdk/config.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/config.py)

The config model also supports file loading through:

- `TelegramSessionConfig.from_file(...)`

### Notes

- If a valid Telethon session file already exists, the adapter can reuse it.
- For first-time login, `phone_number` and `code_callback` are required.
- If the account uses two-factor authentication, `password_callback` is needed.
- If `session_name` includes a directory path such as `.sessions/collector`, the adapter now creates that parent directory automatically.

## Search and Chat Mapping

The adapter keeps the SDK models normalized even though Telethon returns Telegram-specific entity types.

Mapping output models:

- `Chat`
- `User`
- `Message`
- `SearchResults`
- `BotStartResult`

It also keeps an internal entity cache so SDK-level `chat_id` values returned from search results can be used later for history retrieval, link export, and message sending.

## Search Methods Backed by Telethon

Current implementation uses Telethon methods and raw requests for:

- public chat search
- global message search
- per-chat search
- public post search

This aligns with the SDK research and keeps the SDK transport-focused instead of exposing Telethon objects directly.

## Current Implementation Boundary

The adapter currently issues a single request per search call.

That means:

- `search_messages`
- `search_chat_messages`
- `search_public_posts`

currently return up to the first page of results requested from Telegram. If deeper pagination is needed later, it should be added inside the adapter without changing the public SDK API.

## Limitations

There are still important runtime limitations.

- The current environment did not have Telethon installed during implementation.
- The adapter was implemented and syntax-checked, but not live-tested against Telegram.
- Real Telegram verification requires:
  - installing dependencies
  - valid Telegram API credentials
  - interactive or callback-based login
- Public post search may be blocked by Telegram account capability limits such as Premium-only access for `SearchPostsRequest`.

## Validation Performed

The following validation was completed locally:

- source-level integration into the SDK package
- dependency wiring in project metadata
- compile-time syntax validation of the package structure

Live Telegram API validation was not possible in the current environment because `telethon` is not installed and no Telegram credentials were provided.

## Next Recommended Step

The next useful step is to install dependencies and run a real login flow against Telegram.

After that, the adapter should be tested in this order:

1. `resolve_username`
2. `search_public_chats`
3. `search_messages`
4. `search_chat_messages`
5. `get_chat_history`
6. `send_text`
7. `start_bot`
8. `search_public_posts`
9. `export_message_link`
