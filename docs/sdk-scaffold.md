# SDK Scaffold

## Purpose

This document describes the SDK scaffold currently implemented in this repository, including the folder structure, public API, and current backend status.

## Current Status

The repository includes a clean Python package named `sdk` that defines a stable Telegram SDK surface without locking the project to a single backend implementation.

The current backend is an in-memory adapter used for local validation and interface testing.

No real Telegram transport has been wired yet.

## Folder Structure

```text
sdk/
  __init__.py
  client.py
  config.py
  errors.py
  models.py
  transports.py
  adapters/
    __init__.py
    memory.py
  services/
    __init__.py
    bot_search.py
    bots.py
    chats.py
    search.py
  workflows/
    __init__.py
    discovery.py
```

## Public Entry Point

The main entry point is:

- `TelegramSDK`

Defined in:

- [`sdk/client.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/client.py)

This class exposes clean function names and delegates work to service modules backed by a transport implementation.

## Public Methods

The current public methods are:

- `connect`
- `close`
- `search_public_chats`
- `search_messages`
- `search_chat_messages`
- `search_public_posts`
- `resolve_username`
- `get_chat`
- `get_chat_history`
- `get_message`
- `export_message_link`
- `send_text`
- `start_bot`
- `click_message_button`
- `search_via_bot`
- `search_via_en_searchbot`
- `discover_by_keyword`

## Architecture

The SDK is split into the following layers.

### Facade layer

The facade is `TelegramSDK`.

Responsibility:

- provide a stable public API
- avoid exposing backend-specific details to callers

### Service layer

Service modules:

- [`sdk/services/bot_search.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/services/bot_search.py)
- [`sdk/services/search.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/services/search.py)
- [`sdk/services/chats.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/services/chats.py)
- [`sdk/services/bots.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/services/bots.py)

Responsibility:

- organize related operations by concern
- keep method names clear and consistent

### Workflow layer

Workflow modules:

- [`sdk/workflows/discovery.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/workflows/discovery.py)

Responsibility:

- combine multiple search strategies into one higher-level discovery flow
- keep unofficial bot logic outside the transport layer

### Transport layer

Transport contract:

- [`sdk/transports.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/transports.py)

Responsibility:

- define the backend interface the SDK depends on
- make Telethon, TDLib, or raw MTProto adapters interchangeable

### Adapter layer

Current adapter:

- [`sdk/adapters/memory.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/adapters/memory.py)

Responsibility:

- provide a local development backend
- validate method naming and flow before integrating a real Telegram backend

## Domain Models

Defined in:

- [`sdk/models.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/models.py)

Current models:

- `User`
- `Chat`
- `Message`
- `InlineButton`
- `SearchResults`
- `BotStartResult`
- `BotSearchResults`
- `KeywordDiscoveryResults`

These models provide a normalized SDK-level representation of Telegram entities and actions.

## Configuration

Defined in:

- [`sdk/config.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/config.py)

Current config model:

- `TelegramSessionConfig`

Fields:

- `api_id`
- `api_hash`
- `session_name`
- `phone_number`

## Errors

Defined in:

- [`sdk/errors.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/errors.py)

Current exceptions:

- `TelegramSDKError`
- `TransportNotConnectedError`
- `EntityNotFoundError`

## Validation Performed

The current scaffold was validated with:

- Python compile check across the `sdk` package
- local smoke test using the in-memory adapter

Confirmed flows:

- public post search
- public message link export
- bot start flow

## Next Implementation Step

The next production step is to add a real Telegram adapter while keeping the current public API unchanged.

Recommended first adapter:

- `sdk/adapters/telethon.py`

That adapter should implement the contract defined in [`sdk/transports.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/transports.py).

## Documentation Convention

Going forward, each meaningful addition should be documented in a clearly named Markdown file.

Recommended naming style:

- `docs/sdk-scaffold.md`
- `docs/telethon-adapter.md`
- `docs/auth-flow.md`
- `docs/search-workflow.md`

This keeps implementation progress visible and easy to trace.
