# Telegram CTI Collection Plan

## Scope

This document describes a planning-only workflow for collecting Telegram threat intelligence starting from keywords, preserving evidence, enriching relevant findings, and exporting the result to DOCX.

The core workflow should use Telegram's official user API (`api_id` + `api_hash`) for discovery and collection. Unofficial services such as `@en_SearchBot`, `TgScan`, and `tgdb.org` should be treated as optional enrichment only, not as the primary collection layer.

## Rationale

The workflow should not depend on unofficial bots or third-party sites for core collection because they are brittle and may change behavior, disappear, rate-limit aggressively, or produce incomplete results.

The defensible approach is:

1. Discover data through official Telegram access.
2. Preserve raw evidence.
3. Enrich selected hits with supporting context.
4. Generate analyst-ready reporting output.

## High-Level Workflow

1. Start from a maintained keyword list.
2. Search Telegram for public and accessible content related to those keywords.
3. Normalize each relevant result into a structured record.
4. Enrich selected results with additional context.
5. Capture screenshots and evidence links.
6. Use GPT to generate a short analytical description.
7. Export findings to DOCX.

## Keyword-Driven Discovery

The workflow starts with a controlled list of search terms and variants.

Initial examples:

- `vcam`
- `sinh trắc học`
- `trắc sinh học`
- `bán + [danh từ]`
- `mua + [danh từ]`

The keyword set should also include:

- lowercase/uppercase normalization
- accent and no-accent variants
- slang or alternative spellings
- noun combinations commonly used in sale/purchase requests

## Official Telegram Collection Layer

Use Telegram MTProto via a normal user account authenticated with `api_id` and `api_hash`.

Recommended official methods:

- `messages.searchGlobal` for global discovery of accessible messages and peers
- `contacts.resolveUsername` for resolving usernames into Telegram entities
- `channels.getFullChannel` for channel or supergroup metadata
- `messages.getHistory` for contextual history around relevant posts
- `channels.exportMessageLink` for public message links when available

This layer should be treated as the authoritative source for:

- message text
- timestamps
- channel/group metadata
- usernames
- Telegram numeric IDs when accessible
- message links for public posts

## Hit Normalization

Each relevant hit should be converted into a structured case record.

Recommended fields:

- matched keyword
- raw post text
- post date and time
- threat actor username, such as `@username`
- threat actor Telegram numeric ID if available
- group/channel title
- group/channel username or peer ID
- message ID
- media present or not
- collection timestamp
- assessment label:
  - `buying`
  - `selling`
  - `seeking`
  - `offering service`
  - `unknown`

## Optional Enrichment Layer

After a post is identified as relevant, additional enrichment can be performed.

Optional enrichment sources:

- `@en_SearchBot`
- `TgScan`
- `tgdb.org`
- manual analyst validation

This enrichment stage should only add supporting context such as:

- related groups or channels
- repeated actor presence across communities
- possible aliases
- other public references tied to the same actor

Important rule:

- Do not treat these sources as complete, reliable, or primary evidence.

## Evidence Preservation

Evidence should be frozen before analysis text is generated.

For each relevant hit:

1. Save the raw message content and metadata.
2. Generate a Telegram link if the message is publicly linkable.
3. Capture a screenshot that includes the message and the visible group/channel title.

If a public Telegram link is not available:

- create an internal evidence record with the key metadata
- still preserve a screenshot or rendered evidence card

The screenshot is important because the reporting requirement includes visual proof of the original post and the source title.

## GPT-Assisted Analysis

Once evidence is preserved, GPT can be used as a post-processing step.

Input to GPT:

- screenshot of the message
- raw post text
- actor metadata
- matched keyword
- source group/channel

Expected output:

- a short threat description
- a concise summary of what the actor is trying to buy, sell, or obtain
- glossary keywords extracted from the post
- likely target or victim focus
- confidence note if inference is weak

Analyst review remains necessary because target inference can be ambiguous.

## DOCX Reporting Format

The final report should be generated in DOCX format.

Suggested per-record structure:

- `Threat Actor name: @username - ID`
- `Source Group/Channel: [title]`
- `Post Date: [timestamp]`
- `Matched Keyword: [keyword]`
- `Assessment: buying / selling / seeking / unknown`
- `Link: [Telegram link if available]`
- `Screenshot: [embedded image]`
- `Short Description: [GPT-assisted summary]`
- `Glossary: [related keywords and terms]`
- `Target: [what the actor appears to be targeting]`
- `Notes / Related Groups: [optional enrichment]`

## Recommended Processing Order

1. Run keyword discovery through the official Telegram API.
2. Filter and triage relevant results.
3. Normalize results into structured records.
4. Enrich selected records using optional third-party sources or analyst review.
5. Capture screenshots and preserve message evidence.
6. Send evidence and text to GPT for short analytical output.
7. Export all accepted findings to DOCX.

## Constraints and Assumptions

- Official Telegram search only returns content the authenticated account can access.
- Private groups and private channels require access or membership.
- Public CTI-relevant collection is reasonable; indiscriminate personal profiling should be avoided.
- Unofficial bots and indexing sites may break, throttle, or change behavior without notice.
- Analyst review is still required before final reporting.

## Next Planning Step

If planning continues, the next useful document should define:

1. folder structure
2. data schema for collected hits
3. evidence storage layout
4. triage rules for relevance
5. DOCX template fields
6. separation between official collection and unofficial enrichment
