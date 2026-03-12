# Telegram SDK Research

## Purpose

This document summarizes Telegram's official SDK and API options for integrating Telegram into another program as a library and calling functions to perform actions such as:

- interacting with Telegram bots
- searching messages
- searching groups and channels
- resolving usernames
- collecting accessible posts from chats, groups, and channels

## Main Finding

The official Telegram component that most closely matches an embeddable SDK or library is **TDLib**.

TDLib is Telegram's official client library for integrating Telegram capabilities into another application. It supports function-style interaction from an external program and is designed for building full Telegram client functionality into software.

Official references:

- TDLib overview: https://core.telegram.org/tdlib
- TDLib documentation: https://core.telegram.org/tdlib/docs/

## Official Telegram Options

Telegram provides three relevant layers:

1. TDLib
2. MTProto API
3. Bot API

### 1. TDLib

TDLib stands for Telegram Database Library.

It is Telegram's official cross-platform client library and is the best fit when another program needs to integrate Telegram as a functional library.

Key characteristics:

- official Telegram client library
- designed to be embedded into applications
- supports C++, Java, and .NET directly
- also exposes a JSON interface for use from other languages
- suitable for search, chat access, bot interaction, and message collection

Official sources:

- https://core.telegram.org/tdlib
- https://core.telegram.org/tdlib/docs/

### 2. MTProto API

MTProto is Telegram's underlying client API.

It is lower level than TDLib and exposes the raw methods for:

- searching messages
- resolving usernames
- sending messages
- interacting with bots
- accessing channels and groups

To use it, a developer needs:

- `api_id`
- `api_hash`

Official source:

- https://core.telegram.org/api/obtaining_api_id

### 3. Bot API

The Bot API is a separate official HTTP API for Telegram bots.

It is useful when building a bot service, but it is not the right API for broad Telegram-wide search or for acting like a user account across public groups, channels, and bots.

Official source:

- https://core.telegram.org/bots/api

## Best Choice for Search and Bot Interaction

If the goal is to build a program that:

- searches Telegram by keyword
- searches groups, channels, and posts
- talks to existing bots
- resolves usernames
- collects messages from accessible channels and groups

then the recommended foundation is:

- **TDLib** or direct **MTProto**
- authenticated as a **user account**

This is preferable to using the Bot API for this use case.

## TDLib Functions Relevant to the Use Case

TDLib exposes function-like operations that another program can call.

Important examples:

### Search public chats by username

- `searchPublicChat`
- documentation: https://core.telegram.org/tdlib/docs/classtd_1_1td__api_1_1search_public_chat.html

Use case:

- resolve a known public username into a chat/channel/group

### Search public chats by text

- `searchPublicChats`
- documentation: https://core.telegram.org/tdlib/docs/classtd_1_1td__api_1_1search_public_chats.html

Use case:

- search public chats by title or public username text

### Search messages across chats

- `searchMessages`
- documentation: https://core.telegram.org/tdlib/docs/classtd_1_1td__api_1_1search_messages.html

Use case:

- find messages across accessible chats matching a keyword

### Search messages inside one chat

- `searchChatMessages`
- documentation: https://core.telegram.org/tdlib/docs/classtd_1_1td__api_1_1search_chat_messages.html

Use case:

- search inside one specific group, channel, or chat

### Send a message

- `sendMessage`
- documentation: https://core.telegram.org/tdlib/docs/classtd_1_1td__api_1_1send_message.html

Use case:

- send a message to a bot, group, or user chat that the authenticated account can access

## Raw MTProto Methods Relevant to the Use Case

If using MTProto directly, these official methods are especially relevant.

### Search globally across accessible content

- `messages.searchGlobal`
- documentation: https://core.telegram.org/method/messages.searchGlobal

Use case:

- search messages and peers the authenticated account can access

### Search within one chat

- `messages.search`
- documentation: https://core.telegram.org/method/messages.search

Use case:

- search a specific group, channel, or chat for a keyword

### Search public channel posts

- `channels.searchPosts`
- documentation: https://core.telegram.org/method/channels.searchPosts

Use case:

- search public channel posts by keyword

### Telegram search overview

- documentation: https://core.telegram.org/api/search

Use case:

- understand Telegram's official search model and limitations

## Bot Interaction Methods

If the requirement is to make a program act like a Telegram user that communicates with bots, the official MTProto API provides methods for this.

### Start a bot

- `messages.startBot`
- documentation: https://core.telegram.org/method/messages.startBot

Use case:

- start a bot conversation, including deep-link parameters

### Send a message to a bot

- `messages.sendMessage`
- documentation: https://core.telegram.org/method/messages.sendMessage

Use case:

- send text to a bot as the authenticated user

### Get inline bot results

- `messages.getInlineBotResults`
- documentation: https://core.telegram.org/method/messages.getInlineBotResults

Use case:

- request inline query results from a bot

### Click an inline button / get callback response

- `messages.getBotCallbackAnswer`
- documentation: https://core.telegram.org/method/messages.getBotCallbackAnswer

Use case:

- interact with bot buttons in messages

## What the SDK/API Can Do

With TDLib or MTProto authenticated as a user account, a program can generally:

- resolve public usernames
- search public chats
- search accessible messages
- search inside groups and channels it can access
- search public channel posts
- send messages to bots
- start bot conversations
- collect chat metadata
- fetch message history from accessible entities

## What It Cannot Do Freely

There are important limits.

- It cannot freely access private groups or private channels without access.
- It cannot bypass Telegram permissions.
- Search results depend on what the authenticated account can access.
- Some public full-text search functionality may be quota-limited or tied to Telegram Stars payment according to Telegram's official search documentation.

Relevant official references:

- https://core.telegram.org/api/search
- https://core.telegram.org/method/channels.searchPosts

## Practical Recommendation

For a CTI or OSINT-oriented automation workflow, the most practical architecture is:

1. Use TDLib as the SDK layer.
2. Authenticate with a normal Telegram user account.
3. Use official search functions to discover chats, channels, and messages.
4. Use bot interaction functions only when there is a specific need to query a Telegram bot.
5. Keep Bot API usage separate unless the project also needs to operate its own bot.

## Final Conclusion

Telegram does provide an official embeddable toolkit for another program to integrate and call like a library.

The best official answer is:

- **TDLib** as the SDK
- **MTProto** as the underlying API

These support the kinds of function-driven operations relevant to the workflow:

- call or interact with bots
- search messages
- search groups and channels
- fetch accessible posts and metadata

The simple Bot API is not enough for broad Telegram client-style search and collection use cases.
