# Example Script

## Purpose

This document describes the runnable example script that exercises the SDK with the Telethon transport once Telegram credentials are available.

## File

- [`examples/telethon_keyword_search.py`](/home/kali/Desktop/CollectCTIFeeds/examples/telethon_keyword_search.py)

## What It Does

The script:

1. reads Telegram credentials from a config file
2. creates `TelegramSessionConfig`
3. creates `TelethonTelegramTransport`
4. wraps it with `TelegramSDK`
5. connects to Telegram
6. runs:
   - `search_public_chats`
   - `search_messages`
   - `search_public_posts`
   - fallback `search_chat_messages` inside discovered public chats
7. prints the results to stdout

## Required Runtime Inputs

- search query passed as a command-line parameter
- `config/telegram.session.json`

## Optional Command-Line Parameter

- `--config`

## Interactive Inputs

The script asks for:

- Telegram login code
- Telegram 2FA password if the account uses it

## Example Run

```bash
cp config/telegram.session.example.json config/telegram.session.json
.venv/bin/python examples/telethon_keyword_search.py "sinh trac hoc"
```

## Notes

- The default config file path is `config/telegram.session.json`.
- The default session file path inside the example template is `.sessions/collector`.
- The first run should create a reusable local session, and the parent session directory is created automatically.
- Public post search may fail or be limited depending on Telegram search restrictions, Premium requirements, and account state.
- If public post search fails, the example still runs a fallback per-chat search across discovered public chats.

## Alternate Config Path

```bash
.venv/bin/python examples/telethon_keyword_search.py "sinh trac hoc" --config /path/to/telegram.session.json
```
