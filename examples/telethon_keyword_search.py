"""Chạy tìm kiếm từ khóa trên Telegram bằng transport Telethon của SDK."""

from __future__ import annotations

import argparse
from getpass import getpass

from sdk import TelegramSDK, TelegramSessionConfig
from sdk.adapters.telethon import TelethonTelegramTransport


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tìm kiếm Telegram bằng transport Telethon của SDK."
    )
    parser.add_argument("query", help="Từ khóa hoặc cụm từ cần tìm")
    parser.add_argument(
        "--config",
        default="config/telegram.session.json",
        help="Đường dẫn tới file cấu hình phiên Telegram dạng JSON",
    )
    return parser.parse_args()


def build_sdk(config_path: str, query: str) -> TelegramSDK:
    config = TelegramSessionConfig.from_file(
        config_path,
        code_callback=lambda: input("Nhập mã đăng nhập Telegram: ").strip(),
        password_callback=lambda: getpass("Nhập mật khẩu 2FA Telegram (nếu có): "),
    )

    transport = TelethonTelegramTransport(config)
    sdk = TelegramSDK(transport)
    sdk.connect()
    print(f"Đã kết nối. Bắt đầu tìm kiếm với từ khóa: {query}")
    return sdk


def print_public_chats(sdk: TelegramSDK, query: str) -> None:
    print("\n== Chat công khai ==")
    for chat in sdk.search_public_chats(query, limit=10):
        print(f"- [{chat.kind}] {chat.title} id={chat.chat_id} username={chat.username}")


def print_global_messages(sdk: TelegramSDK, query: str) -> None:
    print("\n== Tin nhắn toàn cục ==")
    results = sdk.search_messages(query, limit=10)
    for message in results.messages:
        print(
            f"- chat_id={message.chat_id} message_id={message.message_id} "
            f"timestamp={message.timestamp} text={message.text[:120]!r}"
        )


def print_public_posts(sdk: TelegramSDK, query: str) -> None:
    print("\n== Bài viết công khai ==")
    try:
        results = sdk.search_public_posts(query, limit=10)
    except Exception as exc:
        print(f"- tìm bài viết công khai thất bại: {exc}")
        return

    for message in results.messages:
        print(
            f"- chat_id={message.chat_id} message_id={message.message_id} "
            f"link={message.permalink} text={message.text[:120]!r}"
        )


def print_chat_fallback_search(sdk: TelegramSDK, query: str) -> None:
    print("\n== Tìm kiếm dự phòng theo từng chat ==")
    chats = sdk.search_public_chats(query, limit=10)
    if not chats:
        print("- không tìm thấy chat công khai nào để chạy tìm kiếm dự phòng")
        return

    found_any = False
    for chat in chats:
        try:
            messages = sdk.search_chat_messages(chat.chat_id, query, limit=5)
        except Exception as exc:
            print(f"- [{chat.title}] tìm kiếm thất bại: {exc}")
            continue

        if not messages:
            continue

        found_any = True
        print(f"- [{chat.title}]")
        for message in messages:
            print(
                f"  message_id={message.message_id} timestamp={message.timestamp} "
                f"link={message.permalink} text={message.text[:120]!r}"
            )

    if not found_any:
        print("- không tìm thấy tin nhắn phù hợp trong các chat công khai đã phát hiện")


def main() -> None:
    args = parse_args()
    sdk = build_sdk(config_path=args.config, query=args.query)
    try:
        print_public_chats(sdk, args.query)
        print_global_messages(sdk, args.query)
        print_public_posts(sdk, args.query)
        print_chat_fallback_search(sdk, args.query)
    finally:
        sdk.close()


if __name__ == "__main__":
    main()
