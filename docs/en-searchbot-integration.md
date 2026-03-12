# en_SearchBot Integration

## Purpose

This document describes the unofficial `@en_SearchBot` integration added to the SDK.

The integration is intentionally implemented above the transport layer so the core Telegram transport remains official and backend-agnostic.

## Design

`@en_SearchBot` is treated as:

- an unofficial discovery source
- optional enrichment or alternate keyword discovery
- separate from Telegram's official search methods

It is not baked into the Telethon transport itself.

## Files Added or Updated

Added:

- [`sdk/services/bot_search.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/services/bot_search.py)
- [`sdk/workflows/discovery.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/workflows/discovery.py)
- [`sdk/workflows/__init__.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/workflows/__init__.py)
- [`examples/en_searchbot_search.py`](/home/kali/Desktop/CollectCTIFeeds/examples/en_searchbot_search.py)
- [`docs/en-searchbot-integration.md`](/home/kali/Desktop/CollectCTIFeeds/docs/en-searchbot-integration.md)

Updated:

- [`sdk/models.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/models.py)
- [`sdk/client.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/client.py)
- [`sdk/services/__init__.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/services/__init__.py)
- [`sdk/__init__.py`](/home/kali/Desktop/CollectCTIFeeds/sdk/__init__.py)
- [`README.md`](/home/kali/Desktop/CollectCTIFeeds/README.md)
- [`docs/sdk-scaffold.md`](/home/kali/Desktop/CollectCTIFeeds/docs/sdk-scaffold.md)

## Public SDK Methods

New facade methods:

- `search_via_bot`
- `search_via_en_searchbot`
- `discover_by_keyword`
- `click_message_button`

These extend the SDK without changing any existing public method names.

## Result Models

New models:

- `BotSearchResults`
- `KeywordDiscoveryResults`
- `InlineButton`

### `BotSearchResults`

Contains:

- bot username
- query
- bot chat metadata
- request message
- reply messages
- page snapshots for paginated result messages
- extracted `@usernames`
- extracted Telegram links
- extracted chat usernames inferred from messages and links

### `KeywordDiscoveryResults`

Contains:

- public chats discovered through official search
- global messages discovered through official search
- public posts if available
- fallback per-chat search results
- bot-assisted results
- non-fatal errors

## How Bot Search Works

The bot-search service performs this flow:

1. resolve the bot username
2. start the bot conversation
3. send the query text
4. poll recent bot chat history for replies newer than the request message
5. normalize the reply messages
6. extract usernames and Telegram links from the bot output

If `crawl_all_pages=True`, it also attempts to:

7. detects paginated result messages such as `Page 1/52`
8. clicks the `➡️` inline button
9. polls the edited message until the page content changes
10. store a snapshot of each page

## Extraction Rules

The current parser extracts:

- `@usernames`
- `t.me/...` links
- likely chat usernames inferred from `t.me/<username>` links

This parser is intentionally conservative and text-based.

## Workflow Layer

The discovery workflow combines:

- official public chat search
- official global message search
- official public post search when available
- fallback per-chat keyword search
- optional `@en_SearchBot` lookup

This workflow is exposed through:

- `TelegramSDK.discover_by_keyword(...)`

## Example Script

Use:

- [`examples/en_searchbot_search.py`](/home/kali/Desktop/CollectCTIFeeds/examples/en_searchbot_search.py)

Example:

```bash
python examples/en_searchbot_search.py "sinh trac hoc"
```

Optional parameters:

- `--config`
- `--poll-attempts`
- `--poll-interval`
- `--history-limit`
- `--crawl-all-pages`
- `--max-pages`

Paginated crawl example:

```bash
python examples/en_searchbot_search.py "sinh trac hoc" --crawl-all-pages --max-pages 5
```

## Limitations

- `@en_SearchBot` is unofficial and may change behavior at any time.
- Reply formatting may change, which may break parsing.
- Rate limits or anti-abuse controls may apply.
- A live test on March 11, 2026 showed the bot can enforce a daily usage limit and redirect users to referral or premium upsell flows instead of returning search results.
- A live test on March 11, 2026 also showed normal result pages such as `Page 1/52`; the integration now attempts to click the `➡️` pagination button and capture page snapshots, but page-turn callbacks may still time out or be ignored by the bot depending on current bot behavior and account limits.
- Bot replies are polled from recent history, so if the bot responds very slowly the default polling settings may need to be increased.
- Extracted usernames and links are heuristic outputs, not guaranteed complete classifications.

## Recommendation

Use this integration as:

- optional enrichment
- alternate discovery
- one source among several

Do not treat it as the sole or authoritative Telegram collection backend.
