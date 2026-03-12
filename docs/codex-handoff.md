## Handoff cho Codex phiên sau

Tài liệu này tóm tắt trạng thái kỹ thuật hiện tại để một phiên Codex mới có thể tiếp tục công việc mà không phải dò lại toàn bộ lịch sử.

### 1. Dự án đang làm gì

Repo này là một Python SDK cho Telegram theo hướng:

- facade public ổn định qua `TelegramSDK`
- transport boundary tách biệt
- bot orchestration qua `sdk/botkit`
- focus hiện tại là `@en_SearchBot`

### 2. Kiến trúc thực tế

```text
Application
  -> TelegramSDK
    -> services/*
    -> BotSDK
      -> BaseBotAdapter
      -> EnSearchBotAdapter
    -> TelegramTransport
      -> Memory / Telethon adapters
```

Các file quan trọng:

- `sdk/client.py`: API public
- `sdk/services/bot_search.py`: API tiện dụng cho bot search
- `sdk/botkit/base.py`: workflow chung + transport retry
- `sdk/botkit/adapters/en_searchbot.py`: logic thật của `@en_SearchBot`
- `sdk/botkit/checkpoints.py`: checkpoint JSONL cho crawl lớn
- `tests/test_bot_search_service.py`: regression suite chính cho `@en_SearchBot`

### 3. Trạng thái `@en_SearchBot`

Đã có:

- search keyword qua `TelegramSDK.search_via_en_searchbot(...)`
- full crawl qua pagination `➡️`
- retry/backoff cho các thao tác đọc
- correlation tốt hơn với `reply_to_message_id`, `edit_timestamp`, `is_edited`
- fail rõ ràng nếu không crawl đủ số trang bot báo
- checkpoint/resume cho crawl rất lớn

Chưa có:

- stream xử lý nội dung từng page ra worker riêng
- progress logging chi tiết theo từng page trong public API
- output schema riêng cho export kết quả rất lớn ngoài checkpoint JSONL

### 4. Những gì vừa được thêm gần đây

- mode `stream/checkpoint` cho `@en_SearchBot`
- `BotSearchResults` có thêm:
  - `total_pages`
  - `pages_collected`
  - `checkpoint_path`
  - `checkpoint_complete`
  - `resumed_from_checkpoint`
- script mẫu mới:
  - `examples/use_en_searchbot_sdk.py`
- fix UX:
  - nếu chưa bật `crawl_all_pages`, SDK vẫn tự báo được `1/N` từ trang đầu thay vì `0/None`

### 5. Cách verify nhanh

Test:

```bash
python -m unittest discover -s tests -p 'test_*.py'
python -m compileall sdk tests examples
```

Chạy script mẫu:

```bash
python examples/use_en_searchbot_sdk.py "bypass kyc"
python examples/use_en_searchbot_sdk.py "bypass kyc" --crawl-all-pages
python examples/use_en_searchbot_sdk.py "bypass kyc" \
  --crawl-all-pages \
  --checkpoint-path artifacts/en-searchbot-bypass-kyc.jsonl \
  --resume-checkpoint \
  --no-keep-pages-in-memory
```

### 6. Rủi ro và boundary không được phá

- Không chuyển bot-specific parsing vào transport.
- Không để `search_via_en_searchbot()` trả thiếu trang mà vẫn báo thành công.
- Không dùng `len(page_snapshots)` để suy ra số trang thu được khi đang chạy mode checkpoint/memory cap.
- Không commit runtime artifact trong `artifacts/`.

### 7. Hướng tiếp theo hợp lý

Nếu tiếp tục phát triển, ưu tiên theo thứ tự:

1. progress telemetry/logging cho crawl dài
2. export schema cho kết quả lớn ngoài checkpoint JSONL
3. background worker/queue cho crawl rất dài
4. thêm bot thứ hai thật sự production-ready ngoài `@en_SearchBot`
