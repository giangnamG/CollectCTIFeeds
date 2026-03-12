"""Truy vấn @en_SearchBot qua TelegramSDK và in kết quả đã chuẩn hóa."""

from __future__ import annotations

import argparse
from getpass import getpass

from sdk import TelegramSDK, TelegramSessionConfig
from sdk.adapters.telethon import TelethonTelegramTransport


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Truy vấn @en_SearchBot thông qua TelegramSDK."
    )
    parser.add_argument("query", help="Từ khóa hoặc cụm từ sẽ gửi cho @en_SearchBot")
    parser.add_argument(
        "--config",
        default="config/telegram.session.json",
        help="Đường dẫn tới file cấu hình phiên Telegram dạng JSON",
    )
    parser.add_argument(
        "--poll-attempts",
        type=int,
        default=6,
        help="Số lần kiểm tra chat bot để lấy phản hồi",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Số giây chờ giữa các lần kiểm tra phản hồi",
    )
    parser.add_argument(
        "--history-limit",
        type=int,
        default=20,
        help="Số tin nhắn gần nhất trong chat bot sẽ được đọc ở mỗi lần kiểm tra",
    )
    parser.add_argument(
        "--crawl-all-pages",
        action="store_true",
        help="Bấm nút phân trang và thu thập tất cả các trang kết quả",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Giới hạn số trang tối đa khi quét kết quả có phân trang",
    )
    parser.add_argument(
        "--checkpoint-path",
        default=None,
        help="Ghi từng trang kết quả ra file checkpoint JSONL để resume crawl lớn",
    )
    parser.add_argument(
        "--resume-checkpoint",
        action="store_true",
        help="Tiếp tục crawl từ checkpoint đã có thay vì ghi đè từ đầu",
    )
    parser.add_argument(
        "--no-keep-pages-in-memory",
        action="store_true",
        help="Không giữ toàn bộ page snapshot trong RAM; dùng chung với checkpoint cho crawl lớn",
    )
    parser.add_argument(
        "--page-snapshot-memory-limit",
        type=int,
        default=None,
        help="Giới hạn số page snapshot giữ lại trong RAM khi crawl lớn",
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
            poll_attempts=args.poll_attempts,
            poll_interval_seconds=args.poll_interval,
            history_limit=args.history_limit,
            crawl_all_pages=args.crawl_all_pages,
            max_pages=args.max_pages,
            checkpoint_path=args.checkpoint_path,
            resume_checkpoint=args.resume_checkpoint,
            keep_page_snapshots_in_memory=not args.no_keep_pages_in_memory,
            page_snapshot_memory_limit=args.page_snapshot_memory_limit,
        )
    finally:
        sdk.close()

    print(f"Bot: @{result.bot_username}")
    print(f"Từ khóa: {result.query}")
    print(f"ID tin nhắn yêu cầu: {result.request_message.message_id}")
    print(f"Tổng số trang: {result.total_pages}")
    print(f"Số trang đã thu được: {result.pages_collected}")
    print(f"Checkpoint: {result.checkpoint_path}")
    print(f"Hoàn tất checkpoint: {result.checkpoint_complete}")
    print(f"Resume từ checkpoint: {result.resumed_from_checkpoint}")

    print("\n== Các tin nhắn phản hồi ==")
    if not result.reply_messages:
        print("- không ghi nhận được phản hồi nào")
    for message in result.reply_messages:
        print(f"- message_id={message.message_id} text={message.text[:500]!r}")

    print("\n== Ảnh chụp trạng thái phân trang ==")
    if not result.page_snapshots:
        print("- không có")
    for index, message in enumerate(result.page_snapshots, start=1):
        print(
            f"- page_snapshot={index} message_id={message.message_id} "
            f"text={message.text[:500]!r}"
        )

    print("\n== Username trích xuất được ==")
    if not result.extracted_usernames:
        print("- không có")
    for username in result.extracted_usernames:
        print(f"- {username}")

    print("\n== Liên kết Telegram trích xuất được ==")
    if not result.extracted_links:
        print("- không có")
    for link in result.extracted_links:
        print(f"- {link}")

    print("\n== Username chat suy ra từ kết quả ==")
    if not result.extracted_chat_usernames:
        print("- không có")
    for username in result.extracted_chat_usernames:
        print(f"- {username}")


if __name__ == "__main__":
    main()
