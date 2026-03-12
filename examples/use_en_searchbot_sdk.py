"""Script mẫu tối giản để dùng TelegramSDK gọi @en_SearchBot."""

from __future__ import annotations

import argparse
from getpass import getpass

from sdk import TelegramSDK, TelegramSessionConfig
from sdk.adapters.telethon import TelethonTelegramTransport


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dùng TelegramSDK để gửi keyword tới @en_SearchBot."
    )
    parser.add_argument("query", help="Từ khóa hoặc cụm từ cần tìm")
    parser.add_argument(
        "--config",
        default="config/telegram.session.json",
        help="Đường dẫn tới file cấu hình phiên Telegram",
    )
    parser.add_argument(
        "--crawl-all-pages",
        action="store_true",
        help="Thu thập toàn bộ các trang kết quả",
    )
    parser.add_argument(
        "--checkpoint-path",
        default=None,
        help="File JSONL để ghi checkpoint khi crawl lớn",
    )
    parser.add_argument(
        "--resume-checkpoint",
        action="store_true",
        help="Tiếp tục từ checkpoint cũ nếu file đã tồn tại",
    )
    parser.add_argument(
        "--no-keep-pages-in-memory",
        action="store_true",
        help="Không giữ toàn bộ page snapshot trong RAM",
    )
    return parser.parse_args()


def build_sdk(config_path: str) -> TelegramSDK:
    config = TelegramSessionConfig.from_file(
        config_path,
        code_callback=lambda: input("Nhập mã đăng nhập Telegram: ").strip(),
        password_callback=lambda: getpass("Nhập mật khẩu 2FA Telegram (nếu có): "),
    )
    transport = TelethonTelegramTransport(config)
    sdk = TelegramSDK(transport)
    sdk.connect()
    return sdk


def main() -> None:
    args = parse_args()
    sdk = build_sdk(args.config)

    try:
        result = sdk.search_via_en_searchbot(
            args.query,
            crawl_all_pages=args.crawl_all_pages,
            checkpoint_path=args.checkpoint_path,
            resume_checkpoint=args.resume_checkpoint,
            keep_page_snapshots_in_memory=not args.no_keep_pages_in_memory,
        )
    finally:
        sdk.close()

    print(f"Bot: @{result.bot_username}")
    print(f"Keyword: {result.query}")
    print(f"So trang da thu: {result.pages_collected}/{result.total_pages}")
    print(f"Checkpoint: {result.checkpoint_path}")
    print(f"Resume: {result.resumed_from_checkpoint}")
    print(f"Hoan tat checkpoint: {result.checkpoint_complete}")
    print(f"So username trich xuat duoc: {len(result.extracted_usernames)}")
    print(f"So link Telegram trich xuat duoc: {len(result.extracted_links)}")

    if not args.crawl_all_pages:
        print("Luu y: ban dang doc trang dau tien. Them --crawl-all-pages de crawl du toan bo.")

    if result.reply_messages:
        print("\n== Trang phan hoi dau tien ==")
        print(result.reply_messages[0].text[:1000])

    if result.extracted_usernames:
        print("\n== Username ==")
        for username in result.extracted_usernames:
            print(username)

    if result.extracted_links:
        print("\n== Link Telegram ==")
        for link in result.extracted_links:
            print(link)


if __name__ == "__main__":
    main()
