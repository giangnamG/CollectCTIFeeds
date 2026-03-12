# Telegram SDK

This workspace now includes a clean Python SDK scaffold under [`sdk`](./sdk) for Telegram-style search, chat metadata, history, and bot interaction workflows.

The public entry point is `TelegramSDK`. It exposes stable method names while keeping the backend transport swappable. You can plug in a TDLib, Telethon, or raw MTProto transport later without changing the SDK's public surface.

## Docs

Project documentation is kept in clearly named Markdown files.

- [`telegram-sdk-research.md`](./telegram-sdk-research.md): research notes on Telegram SDK and API options
- [`telegram-search-techniques.md`](./telegram-search-techniques.md): search techniques and tradeoffs
- [`plan.md`](./plan.md): collection workflow plan
- [`docs/sdk-scaffold.md`](./docs/sdk-scaffold.md): current SDK structure and implemented public API
- [`docs/telethon-adapter.md`](./docs/telethon-adapter.md): real Telegram backend adapter design and usage
- [`docs/example-script.md`](./docs/example-script.md): runnable example for the Telethon adapter
- [`docs/config-file.md`](./docs/config-file.md): file format for Telegram credentials and session settings
- [`docs/en-searchbot-integration.md`](./docs/en-searchbot-integration.md): unofficial `@en_SearchBot` workflow and usage
- [`docs/botkit.md`](./docs/botkit.md): tài liệu tiếng Việt về cách dùng BotSDK, adapter, và bot orchestration
- [`docs/onboarding.md`](./docs/onboarding.md): hướng dẫn onboarding cho người mới vào dự án
- [`docs/tool-schema.md`](./docs/tool-schema.md): tài liệu về tool schema chính thức để dựng facade kiểu MCP hoặc automation

## Package layout

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

## Public methods

`TelegramSDK` exposes:

- `search_public_chats`
- `search_messages`
- `search_chat_messages`
- `search_public_posts`
- `resolve_username`
- `resolve_chat_reference`
- `get_chat`
- `get_chat_history`
- `get_message`
- `inspect_chat`
- `inspect_chat_page`
- `inspect_message`
- `inspect_chat_tool_payload`
- `inspect_chat_page_tool_payload`
- `inspect_message_tool_payload`
- `export_message_link`
- `send_text`
- `start_bot`
- `list_message_buttons`
- `click_message_button`
- `click_button_reference`
- `search_via_bot`
- `search_via_en_searchbot`
- `discover_by_keyword`

`search_via_en_searchbot(...)` hiện hỗ trợ thêm mode crawl lớn:

- `checkpoint_path`: ghi từng trang ra file JSONL
- `resume_checkpoint`: resume từ checkpoint cũ nếu job bị ngắt
- `keep_page_snapshots_in_memory=False`: không giữ toàn bộ trang trong RAM
- `page_snapshot_memory_limit`: chỉ giữ lại một số snapshot gần nhất trong bộ nhớ

Các method theo chat hiện đã hỗ trợ `chat_reference` linh hoạt:

- `chat_id` dạng số nguyên
- `@username`
- `https://t.me/...`

Các API inspection hiện cũng hỗ trợ:

- lọc theo `direction`: `latest`, `before`, `after`, `around`
- neo theo `anchor_message_id`
- lọc theo `query`
- xuất payload dạng dict sẵn dùng cho tooling/MCP facade

## Quick example

```python
from sdk import MemoryTelegramTransport, TelegramSDK
from sdk.models import BotStartResult, Chat, Message, SearchResults

transport = MemoryTelegramTransport(
    chats=[
        Chat(
            chat_id=1001,
            title="Biometric Market",
            username="biometric_market",
            kind="channel",
            is_public=True,
        )
    ],
    messages=[
        Message(
            message_id=5001,
            chat_id=1001,
            sender_id=3001,
            text="Ban sinh trac hoc, VCAM full set",
            timestamp="2026-03-11T04:00:00Z",
        )
    ],
)

sdk = TelegramSDK(transport)
hits = sdk.search_public_posts("sinh trac hoc")
print(hits.messages[0].text)
```

## Next backend adapters

The current package includes a memory adapter to validate structure and method naming. The next production step is to add a real adapter for one of:

- TDLib
- Telethon
- raw MTProto

## Telethon adapter

A real Telethon-backed transport now exists at [`sdk/adapters/telethon.py`](./sdk/adapters/telethon.py).

It keeps the `TelegramSDK` public API unchanged and swaps only the backend transport implementation.

## Example

A runnable example is available at [`examples/telethon_keyword_search.py`](./examples/telethon_keyword_search.py).

Run it with:

```bash
.venv/bin/python examples/telethon_keyword_search.py "sinh trac hoc"
```

An `@en_SearchBot` example is also available at [`examples/en_searchbot_search.py`](./examples/en_searchbot_search.py).

Run it with:

```bash
.venv/bin/python examples/en_searchbot_search.py "sinh trac hoc"
```

To attempt a paginated `@en_SearchBot` crawl:

```bash
.venv/bin/python examples/en_searchbot_search.py "sinh trac hoc" --crawl-all-pages
```
# CollectCTIFeeds
