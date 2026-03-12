# Config File

## Purpose

This document defines the file-based configuration format for Telegram credentials and session settings used by the SDK example scripts.

## Primary Config File

Recommended runtime config path:

- `config/telegram.session.json`

Example template:

- [`config/telegram.session.example.json`](/home/kali/Desktop/CollectCTIFeeds/config/telegram.session.example.json)

## JSON Format

```json
{
  "api_id": "123456",
  "api_hash": "your_api_hash",
  "session_name": ".sessions/collector",
  "phone_number": "+15550000000",
  "allow_paid_stars": null
}
```

## Fields

- `api_id`
  - required
  - Telegram application API ID

- `api_hash`
  - required
  - Telegram application API hash

- `session_name`
  - optional
  - local Telethon session path or name
  - default: `default`
  - parent directories are created automatically if needed

- `phone_number`
  - optional for reused sessions
  - required for first-time login

- `allow_paid_stars`
  - optional
  - used if public post search needs Telegram Stars allowance

## Current Loader

The config loader is implemented in:

- [`sdk/config.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/config.py)

Method:

- `TelegramSessionConfig.from_file(...)`

## Example Script Usage

The Telethon example now reads its credentials from a config file.

Script:

- [`examples/telethon_keyword_search.py`](/home/kali/Desktop/CollectCTIFeeds/examples/telethon_keyword_search.py)

By default it expects:

- `config/telegram.session.json`

Override path with:

- `--config`

The search query is passed separately as a positional command-line parameter.

## Example Run

```bash
cp config/telegram.session.example.json config/telegram.session.json
.venv/bin/python examples/telethon_keyword_search.py "sinh trac hoc"
```

## Security Note

The real config file contains sensitive Telegram credentials.

Recommended practice:

- keep `config/telegram.session.json` out of version control
- commit only the example template

Current repository guard:

- [`.gitignore`](/home/kali/Desktop/CollectCTIFeeds/.gitignore) excludes:
  - `config/telegram.session.json`
  - `.sessions/`
  - `.venv/`
