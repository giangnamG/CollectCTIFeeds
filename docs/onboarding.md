## Hướng dẫn onboarding cho người mới

Tài liệu này dành cho lập trình viên mới tham gia dự án `CollectCTIFeeds`.

Mục tiêu là giúp bạn hiểu nhanh:

- Dự án này đang giải quyết bài toán gì
- Các lớp chính trong SDK nằm ở đâu
- Nên bắt đầu đọc code từ đâu
- Cách chạy thử nhanh
- Những nguyên tắc kỹ thuật không được phá vỡ

### 1. Dự án này làm gì

Codebase hiện tại xây dựng một SDK Python để làm việc với Telegram theo hướng sạch và có thể mở rộng.

Phạm vi chính hiện nay gồm:

- Tìm kiếm chat công khai
- Tìm kiếm tin nhắn
- Đọc lịch sử chat
- Gọi bot Telegram
- Điều phối workflow với bot như `@en_SearchBot`

### 2. Kiến trúc ở mức cao

Hãy nhìn hệ thống theo 3 tầng:

1. `Transport`
   Tầng này nói chuyện trực tiếp với Telegram hoặc backend mô phỏng.

2. `Service / Workflow`
   Tầng này ghép nhiều thao tác transport thành use case rõ ràng.

3. `Bot Orchestration`
   Tầng này chuẩn hóa cách ứng dụng gọi nhiều bot khác nhau thông qua adapter.

Sơ đồ ngắn:

```text
Ứng dụng
  -> TelegramSDK
    -> Search / Chats / Bots / BotSearch / Discovery
    -> BotSDK
      -> BotAdapter
        -> TelegramTransport
```

### 3. Những thư mục quan trọng

- `sdk/client.py`
  Facade public chính là `TelegramSDK`.

- `sdk/transports.py`
  Contract transport. Đây là boundary giữa SDK và backend Telegram.

- `sdk/adapters/`
  Các transport implementation, ví dụ memory hoặc Telethon.

- `sdk/services/`
  Các service nghiệp vụ như search, chat, bot search.

- `sdk/workflows/`
  Các workflow nhiều bước như keyword discovery.

- `sdk/botkit/`
  Lớp orchestration cho bot.

- `sdk/session/`
  Session store cho conversational bot.

- `examples/`
  Script ví dụ để chạy nhanh và hiểu cách wiring.

- `docs/`
  Tài liệu kỹ thuật và hướng dẫn sử dụng.

### 4. Nên đọc code theo thứ tự nào

Nếu bạn mới vào dự án, nên đọc theo thứ tự này:

1. [README.md](/home/kali/Desktop/CollectCTIFeeds/README.md)
2. [sdk/client.py](/home/kali/Desktop/CollectCTIFeeds/sdk/client.py)
3. [sdk/transports.py](/home/kali/Desktop/CollectCTIFeeds/sdk/transports.py)
4. [sdk/adapters/memory.py](/home/kali/Desktop/CollectCTIFeeds/sdk/adapters/memory.py)
5. [sdk/services/bot_search.py](/home/kali/Desktop/CollectCTIFeeds/sdk/services/bot_search.py)
6. [sdk/botkit/sdk.py](/home/kali/Desktop/CollectCTIFeeds/sdk/botkit/sdk.py)
7. [sdk/botkit/base.py](/home/kali/Desktop/CollectCTIFeeds/sdk/botkit/base.py)
8. [sdk/botkit/adapters/en_searchbot.py](/home/kali/Desktop/CollectCTIFeeds/sdk/botkit/adapters/en_searchbot.py)

Thứ tự này giúp bạn đi từ facade public xuống transport và cuối cùng là bot orchestration.

### 5. Cách chạy thử nhanh

#### Chạy kiểm tra compile

```bash
python -m compileall sdk tests examples
```

#### Chạy test

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

#### Chạy ví dụ tìm kiếm với `@en_SearchBot`

```bash
.venv/bin/python examples/en_searchbot_search.py "sinh trắc học" --crawl-all-pages
```

#### Chạy ví dụ trực tiếp với `BotSDK`

```bash
.venv/bin/python examples/botkit_en_searchbot.py "sinh trắc học" --crawl-all-pages
```

### 6. Khi nào dùng lớp nào

#### Dùng `TelegramSDK`

Dùng khi:

- Bạn muốn một entry point chung cho toàn bộ tính năng
- Bạn đang viết application/service layer
- Bạn cần search, chat, bot workflow trong cùng một facade

#### Dùng `BotSDK`

Dùng khi:

- Bạn đang viết logic chuyên cho bot orchestration
- Bạn cần đăng ký adapter riêng
- Bạn muốn kiểm soát session store hoặc command execution ở mức thấp hơn

### 7. Quy tắc kiến trúc bắt buộc

Đây là những nguyên tắc không nên vi phạm:

- Không nhét bot-specific parsing vào `sdk/transports.py`
- Không để `TelegramSDK` biến thành god object
- Không hardcode command string ở nhiều nơi
- Không cho application layer dùng trực tiếp object thô của Telethon
- Bot mới phải đi qua adapter thay vì viết thêm service tạm bợ

### 8. Khi thêm một bot mới, bạn phải làm gì

Luồng chuẩn là:

1. Tạo adapter mới trong `sdk/botkit/adapters/`
2. Kế thừa `BaseBotAdapter`
3. Khai báo `bot_id`, `bot_username`
4. Cài `supports()`
5. Cài `get_supported_commands()`
6. Cài `map_command()`
7. Cài `parse_response()`
8. Đăng ký adapter vào `TelegramSDK` hoặc `BotSDK`
9. Viết test contract cho adapter

### 9. Các lỗi thường gặp khi bắt đầu

- Quên gọi `connect()` trước khi dùng SDK
- Đăng ký adapter nhưng không có session store phù hợp
- Dùng alias command nhưng chưa đăng ký trong `CommandRegistry`
- Tin rằng transport phải hiểu logic từng bot
- Không truyền param bắt buộc vào `BotRequest`
- Truyền `t.me/joinchat/...` hoặc reference không hợp lệ vào API resolve chat

### 10. Một số API tiện ích mới nên biết

Ngoài các API cũ, hiện tại `TelegramSDK` còn có thêm:

- `resolve_chat_reference(reference)`
  Dùng khi input có thể là `chat_id`, `@username`, hoặc `https://t.me/...`

- `get_chat(...)`, `get_chat_history(...)`, `get_message(...)`, `search_chat_messages(...)`
  Hiện cũng đã nhận `chat_reference`, không còn bị khóa chỉ ở `chat_id`

- `list_message_buttons(chat_reference, message_id)`
  Dùng để inspect các inline button trước khi click

- `click_button_reference(chat_reference, message_id, button)`
  Dùng để click lại một button bằng reference đã lấy từ `list_message_buttons`

- `inspect_chat(chat_reference, history_limit)`
  Dùng để xem nhanh metadata chat và các tin nhắn gần nhất

- `inspect_chat_page(chat_reference, page_size, ...)`
  Dùng khi chat history lớn và cần cursor/pagination rõ ràng hơn

- `inspect_message(chat_reference, message_id, context_limit)`
  Dùng để xem message, button và ngữ cảnh trước đó

- `inspect_chat_tool_payload(...)`
  Dùng khi cần payload dạng `dict` sẵn dùng cho lớp tool hoặc MCP facade

- `inspect_chat_page_tool_payload(...)`
  Dùng khi cần payload pagination-ready thay vì dataclass

- `inspect_message_tool_payload(...)`
  Dùng khi cần payload inspection đã chuẩn hóa thay vì dataclass

Các API inspection hiện hỗ trợ thêm:

- `direction`: `latest`, `before`, `after`, `around`
- `anchor_message_id`
- `query`
- `before_limit` và `after_limit` cho ngữ cảnh message
- `HistoryCursor` để phân trang chat history lớn

Ngoài ra, dự án hiện đã có lớp tool schema chính thức tại:

- [docs/tool-schema.md](/home/kali/Desktop/CollectCTIFeeds/docs/tool-schema.md)

Đây là nền để sau này dựng MCP facade hoặc automation layer mà không phải thiết kế lại contract input/output.

### 11. Những tài liệu nên đọc tiếp theo

- [docs/botkit.md](/home/kali/Desktop/CollectCTIFeeds/docs/botkit.md)
- [docs/telethon-adapter.md](/home/kali/Desktop/CollectCTIFeeds/docs/telethon-adapter.md)
- [docs/en-searchbot-integration.md](/home/kali/Desktop/CollectCTIFeeds/docs/en-searchbot-integration.md)
- [docs/sdk-scaffold.md](/home/kali/Desktop/CollectCTIFeeds/docs/sdk-scaffold.md)

### 12. Mức độ trưởng thành hiện tại của hệ thống

Hiện tại hệ thống đã có:

- SDK facade dùng được
- Memory transport để mô phỏng
- Telethon transport để làm việc thật với Telegram
- Bot orchestration layer cơ bản
- `@en_SearchBot` đã đi qua execution path mới
- Regression tests cho các flow chính

Nhưng chưa hoàn thiện hoàn toàn ở các điểm:

- Retry/backoff thực thụ
- Correlation đủ chặt cho chat rất bận
- Session production-grade cho nhiều worker
- Adapter thật cho nhiều bot ngoài `@en_SearchBot`

### 13. Lời khuyên thực tế cho người mới

- Đừng bắt đầu bằng việc sửa transport nếu vấn đề nằm ở bot behavior.
- Đừng thêm abstraction mới nếu adapter hiện tại chưa dùng hết.
- Hãy viết test trước khi migrate một flow cũ sang botkit.
- Nếu thay đổi chạm vào public API, phải kiểm tra backward compatibility.

Nếu bạn cần một điểm bắt đầu cụ thể, hãy bắt đầu từ:

- chạy `examples/en_searchbot_search.py`
- đọc `docs/botkit.md`
- sau đó đi vào `sdk/services/bot_search.py` và `sdk/botkit/adapters/en_searchbot.py`
