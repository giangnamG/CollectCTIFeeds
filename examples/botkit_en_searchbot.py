"""Ví dụ chạy @en_SearchBot thông qua lớp BotSDK orchestration."""

from __future__ import annotations

import argparse
from getpass import getpass

from sdk import TelegramSessionConfig
from sdk.adapters.telethon import TelethonTelegramTransport
from sdk.botkit import BotContext, BotRequest, BotSDK
from sdk.botkit.adapters import EnSearchBotAdapter
from sdk.session import InMemorySessionStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chạy @en_SearchBot thông qua lớp điều phối BotSDK."
    )
    parser.add_argument("query", help="Từ khóa hoặc cụm từ cần tìm")
    parser.add_argument(
        "--config",
        default="config/telegram.session.json",
        help="Đường dẫn tới file cấu hình phiên Telegram dạng JSON",
    )
    parser.add_argument(
        "--crawl-all-pages",
        action="store_true",
        help="Tiếp tục bấm nút sang trang nếu bot có phân trang",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = TelegramSessionConfig.from_file(
        args.config,
        code_callback=lambda: input("Nhập mã đăng nhập Telegram: ").strip(),
        password_callback=lambda: getpass("Nhập mật khẩu 2FA Telegram (nếu có): "),
    )

    transport = TelethonTelegramTransport(config)
    bot_sdk = BotSDK(transport)
    bot_sdk.register_adapter(EnSearchBotAdapter(transport, InMemorySessionStore()))
    bot_sdk.connect()

    try:
        response = bot_sdk.execute_command(
            BotRequest(
                bot_id="en_searchbot",
                command_name="search.keyword",
                params={"query": args.query},
                context=BotContext(tenant_id="local", user_id="cli"),
                options={"crawl_all_pages": args.crawl_all_pages},
            )
        )
    finally:
        bot_sdk.close()

    print(f"Trạng thái: {response.status}")
    print(f"Tài khoản tìm được: {response.data['extracted_usernames']}")
    print(f"Liên kết Telegram: {response.data['extracted_links']}")
    print(f"Username chat suy ra: {response.data['extracted_chat_usernames']}")


if __name__ == "__main__":
    main()
