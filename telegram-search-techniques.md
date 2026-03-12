# Telegram Search Techniques

## Purpose

This document explains practical techniques for building a script that searches Telegram starting from keywords, and identifies the approach that is most suitable for a CTI-style workflow.

## Summary

There are three realistic ways to automate Telegram search:

1. Use the official Telegram user API via MTProto.
2. Automate the Telegram UI in a browser or desktop client.
3. Automate third-party bots or indexing sites.

The recommended primary approach is the first one: official MTProto search using a normal Telegram account authenticated with `api_id` and `api_hash`.

## Technique 1: Official MTProto User API

This is the best technical approach for a script that needs to search Telegram in a stable and defensible way.

Use a normal Telegram user account, not the Bot API.

Why:

- Telegram search methods for broad message discovery are exposed through the user API.
- It is more reliable than UI scraping.
- It is a better foundation for evidence collection and structured reporting.
- It avoids depending on unofficial bots or websites for core collection.

### Key official methods

- `messages.searchGlobal`
  - global search across messages and peers the authenticated account can access
  - https://core.telegram.org/method/messages.searchGlobal

- `messages.search`
  - search inside one known chat, group, or channel
  - https://core.telegram.org/method/messages.search

- `channels.searchPosts`
  - search public channel posts by keyword
  - https://core.telegram.org/method/channels.searchPosts

- `channels.checkSearchPostsFlood`
  - check whether a public post search can be done for free or requires paid access
  - https://core.telegram.org/method/channels.checkSearchPostsFlood

- `contacts.search`
  - search public usernames and contacts by text
  - https://core.telegram.org/method/contacts.search

- `contacts.resolveUsername`
  - resolve an exact username to a Telegram entity
  - https://core.telegram.org/method/contacts.resolveUsername

- `channels.getFullChannel`
  - fetch full metadata for a channel or supergroup
  - https://core.telegram.org/method/channels.getFullChannel

- `messages.getHistory`
  - fetch surrounding history for context
  - https://core.telegram.org/method/messages.getHistory

- `channels.exportMessageLink`
  - create public message links when available
  - https://core.telegram.org/method/channels.exportMessageLink

### Official search strategy

Recommended order:

1. Search for public posts by keyword using `channels.searchPosts`.
2. Search broader accessible content using `messages.searchGlobal`.
3. Resolve discovered usernames with `contacts.resolveUsername`.
4. Pull entity metadata with `channels.getFullChannel`.
5. Fetch nearby message history with `messages.getHistory`.
6. Export public message links when possible using `channels.exportMessageLink`.

### Important limitation

Telegram documents that full-text search over public channel posts has limited free usage and may require payment in Telegram Stars after the free quota is exhausted.

Reference:

- Telegram search documentation: https://core.telegram.org/api/search

### Recommended libraries

For implementation, the most practical choices are:

- `Telethon`
  - good for Python scripting
  - simple for keyword-driven collection flows

- `TDLib`
  - stronger for large-scale client-like workflows
  - better if the system becomes more complex over time

## Technique 2: Browser or UI Automation

This technique uses browser automation tools such as Playwright or Selenium to operate Telegram Web, or desktop automation to operate Telegram Desktop.

This is useful for:

- capturing screenshots
- reproducing an analyst workflow visually
- interacting with Telegram bots that do not expose a stable API

This is not a good primary collection layer because it is:

- brittle
- slower
- more likely to break when the UI changes
- harder to maintain at scale

Recommended use:

- use UI automation only for screenshot capture and analyst-facing evidence collection
- do not rely on it for the core keyword search pipeline if official API methods can cover the need

## Technique 3: Third-Party Bots and Indexing Sites

Examples:

- `@en_SearchBot`
- `TgScan`
- `tgdb.org`

These can be useful for enrichment, but should not be treated as the foundation of the workflow.

Risks:

- behavior may change without notice
- coverage is unclear
- results may be incomplete
- interfaces may break
- rate limits and anti-abuse controls may make automation unstable

Recommended use:

- only as optional supporting enrichment
- only after a relevant hit has already been found through the official Telegram collection path

## Recommended Architecture

If the goal is CTI collection from keywords, the script should be built around:

- `channels.searchPosts`
- `messages.searchGlobal`
- `contacts.resolveUsername`
- `channels.getFullChannel`
- `messages.getHistory`

Then add:

- browser automation for screenshots
- optional third-party enrichment for related groups, channels, or actors

## Practical Recommendation

The most defensible and maintainable design is:

1. Use official MTProto methods for discovery and context collection.
2. Preserve raw evidence and message metadata.
3. Use UI automation for screenshots only.
4. Use third-party bots/sites only as enrichment.

That keeps the pipeline stable even if unofficial tools stop working.
