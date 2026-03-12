## Botkit và cách sử dụng

Tài liệu này mô tả lớp `sdk/botkit`, cách nó được nối vào `TelegramSDK`, và cách đội phát triển nên dùng nó khi tích hợp bot Telegram.

### Botkit giải quyết bài toán gì

`Botkit` là lớp orchestration nằm trên transport Telegram.

Nó được tạo ra để giải quyết 2 vấn đề tách biệt:

- `TelegramTransport` chỉ nên lo việc nói chuyện với Telegram.
- Mỗi bot có hành vi riêng, nhưng ứng dụng vẫn cần một cách gọi thống nhất.

Nói ngắn gọn:

- Transport nói chuyện với Telegram.
- Adapter nói chuyện với từng bot.
- `BotSDK` điều phối việc thực thi command.

### Các thành phần chính

- `BotSDK`: lớp điều phối chính cho bot command.
- `IBotAdapter`: contract chung cho tất cả bot.
- `BaseBotAdapter`: base class chứa workflow dùng lại được.
- `BotRegistry`: đăng ký adapter theo `bot_id`.
- `CommandRegistry`: quản lý command chuẩn hóa và alias.
- `SessionStore`: lưu session/state cho conversational bot.

### Tích hợp hiện tại trong codebase

Hiện tại `TelegramSDK` đã tích hợp `BotSDK` và expose ra ngoài qua thuộc tính:

```python
sdk.botkit
```

Ngoài ra `TelegramSDK` cũng đã có các method public để application layer dùng trực tiếp:

- `register_bot_adapter(adapter)`
- `execute_bot_command(request)`
- `get_supported_bot_commands(bot_id)`
- `list_registered_bots()`
- `resolve_chat_reference(reference)`
- `list_message_buttons(chat_reference, message_id)`
- `click_button_reference(chat_reference, message_id, button)`

`EnSearchBotAdapter` được đăng ký mặc định khi khởi tạo `TelegramSDK`.

Điều này có nghĩa là các flow sau đã đi qua kiến trúc mới:

- `search_via_en_searchbot()`
- `discover_by_keyword(..., use_en_searchbot=True)`

### Cách sử dụng nhanh với TelegramSDK

Đây là cách nên dùng khi application chỉ cần gọi bot mà không muốn tự quản lý `BotSDK` riêng.

```python
from sdk import BotContext, BotRequest, TelegramSDK
from sdk.adapters.memory import MemoryTelegramTransport

transport = MemoryTelegramTransport(...)
sdk = TelegramSDK(transport)
sdk.connect()

try:
    response = sdk.execute_bot_command(
        BotRequest(
            bot_id="en_searchbot",
            command_name="search.keyword",
            params={"query": "sinh trắc học"},
            context=BotContext(tenant_id="local", user_id="cli"),
        )
    )
finally:
    sdk.close()

print(response.status)
print(response.data["extracted_usernames"])
```

### Cách sử dụng `search_via_en_searchbot()`

Nếu chỉ cần dùng `@en_SearchBot` theo API cũ, bạn có thể tiếp tục gọi:

```python
result = sdk.search_via_en_searchbot(
    "sinh trắc học",
    poll_attempts=6,
    poll_interval_seconds=2.0,
    history_limit=20,
    crawl_all_pages=True,
    max_pages=3,
)
```

Kết quả trả về là `BotSearchResults`, bao gồm:

- `bot_username`
- `query`
- `bot_chat`
- `request_message`
- `reply_messages`
- `page_snapshots`
- `extracted_usernames`
- `extracted_links`
- `extracted_chat_usernames`

### Cách đăng ký bot mới

Khi có bot mới, không nên viết logic trực tiếp vào `sdk/services/` hoặc `sdk/transports.py`.

Thay vào đó, hãy tạo một adapter mới kế thừa `BaseBotAdapter` rồi đăng ký vào `TelegramSDK` hoặc `BotSDK`.

Ví dụ:

```python
from sdk import InMemorySessionStore, MonitoringBotAdapter, TelegramSDK

sdk = TelegramSDK(transport)
sdk.register_bot_adapter(
    MonitoringBotAdapter(
        transport=transport,
        session_store=InMemorySessionStore(),
    )
)
```

Sau đó có thể gọi command:

```python
response = sdk.execute_bot_command(
    BotRequest(
        bot_id="monitoring",
        command_name="status",
        context=BotContext(tenant_id="local", user_id="cli"),
    )
)
```

### Cách resolve chat reference linh hoạt

SDK hiện hỗ trợ resolve chat theo nhiều định dạng tham chiếu:

- `chat_id` kiểu số nguyên
- `@username`
- link `https://t.me/...`

Ví dụ:

```python
chat = sdk.resolve_chat_reference("@en_SearchBot")
chat = sdk.resolve_chat_reference("https://t.me/en_SearchBot")
chat = sdk.resolve_chat_reference(123456789)
```

Điểm này được thêm vào để học từ mô hình input linh hoạt của các Telegram tool server như `telegram-mcp`, nhưng vẫn giữ boundary của SDK hiện tại.

Các API facade sau hiện cũng đã nhận `chat_reference` thay vì bắt buộc chỉ nhận `chat_id`:

- `get_chat(...)`
- `get_chat_history(...)`
- `get_message(...)`
- `export_message_link(...)`
- `search_chat_messages(...)`
- `send_text(...)`
- `click_message_button(...)`

### Cách inspect inline button trước khi click

Thay vì phải tự nhớ `row` và `column`, bạn có thể liệt kê button trước:

```python
buttons = sdk.list_message_buttons("@some_bot", message_id=123)
for button in buttons:
    print(button.row, button.column, button.text, button.url)
```

Sau đó click lại bằng chính reference đã lấy ra:

```python
updated_message = sdk.click_button_reference(
    "@some_bot",
    message_id=123,
    button=buttons[0],
)
```

Điều này đặc biệt hữu ích với bot có callback hoặc phân trang.

### Cách inspect chat và message để phục vụ tooling

Ngoài việc đọc dữ liệu thô, SDK hiện có thêm 2 utility inspection:

```python
chat_info = sdk.inspect_chat(
    "@public_chan",
    history_limit=10,
    direction="around",
    anchor_message_id=123,
)
message_info = sdk.inspect_message(
    "@public_chan",
    message_id=123,
    before_limit=3,
    after_limit=2,
)
```

`inspect_chat(...)` trả về:

- metadata của chat
- danh sách tin nhắn gần nhất

`inspect_message(...)` trả về:

- chat chứa message
- chính message đó
- danh sách inline button dưới dạng `MessageButtonRef`
- các tin nhắn ngữ cảnh đứng trước message

Nhóm API này được thêm để chuẩn bị cho các lớp automation/tooling cao hơn mà không cần làm bẩn transport layer.

`inspect_chat(...)` hiện hỗ trợ thêm:

- `direction="latest"`: lấy các tin nhắn gần nhất
- `direction="before"`: lấy các tin nhắn trước `anchor_message_id`
- `direction="after"`: lấy các tin nhắn sau `anchor_message_id`
- `direction="around"`: lấy ngữ cảnh quanh `anchor_message_id`
- `query="..."`: chỉ giữ lại các tin nhắn chứa chuỗi cần lọc

Ví dụ:

```python
recent_after = sdk.inspect_chat(
    "@public_chan",
    history_limit=5,
    direction="after",
    anchor_message_id=100,
)
```

Nếu chat history lớn và cần pagination rõ ràng hơn, nên dùng:

```python
page = sdk.inspect_chat_page("@public_chan", page_size=20)
next_cursor = page.pagination.next_cursor

older_page = sdk.inspect_chat_page(
    "@public_chan",
    cursor=next_cursor,
)
```

`inspect_chat_page(...)` phù hợp hơn `inspect_chat(...)` khi:

- cần duyệt lịch sử chat theo nhiều trang
- cần cursor rõ ràng để truyền qua tool/API
- cần metadata về `returned_count`, `scanned_count`, `next_cursor`

### Cách lấy payload sẵn dùng cho tooling hoặc MCP facade

Nếu bạn cần dữ liệu dạng `dict` để đưa thẳng vào tool layer, không cần tự serialize model:

```python
chat_payload = sdk.inspect_chat_tool_payload(
    "@public_chan",
    history_limit=5,
    direction="after",
    anchor_message_id=100,
)

message_payload = sdk.inspect_message_tool_payload(
    "@public_chan",
    message_id=123,
    before_limit=2,
    after_limit=2,
)

page_payload = sdk.inspect_chat_page_tool_payload(
    "@public_chan",
    page_size=20,
)
```

Payload này được chuẩn hóa sẵn theo hướng:

- metadata chat
- message
- button references
- context trước/sau
- dữ liệu bytes của button ở dạng `hex`

Điểm này giúp sau này dựng MCP layer phía trên mà không phải serialize lại từ đầu.

### Tool schema chính thức

Ngoài payload inspection, SDK hiện đã có lớp schema chính thức tại `sdk/tool_schema.py`.

Bạn có thể dùng:

```python
from sdk import TelegramToolCatalog

catalog = TelegramToolCatalog()
tools = catalog.to_payload()
```

Mục tiêu của lớp này là mô tả public tool contract cho các lớp như:

- MCP facade
- automation gateway
- internal tool runner

Chi tiết xem thêm tại [docs/tool-schema.md](/home/kali/Desktop/CollectCTIFeeds/docs/tool-schema.md).

### Cấu trúc thực thi một bot command

Luồng thực thi tiêu chuẩn hiện tại là:

1. Ứng dụng tạo `BotRequest`.
2. `TelegramSDK` hoặc `BotSDK` resolve đúng adapter theo `bot_id`.
3. `CommandRegistry` chuẩn hóa command name và alias.
4. `BotSDK` validate request trước khi thực thi.
5. `BaseBotAdapter` xử lý workflow chung:
   resolve bot, start bot, gửi text, chờ reply, parse response.
6. Adapter cụ thể chuẩn hóa output thành `BotResponse`.

### Validation hiện có

`BotSDK` hiện đã validate sớm các command parameter bắt buộc.

Ví dụ, nếu command yêu cầu `query` nhưng request truyền chuỗi rỗng, SDK sẽ ném:

```python
BotValidationError
```

Mục tiêu của bước này là fail sớm, tránh để adapter hoặc transport xử lý dữ liệu sai.

### Khi nào nên dùng TelegramSDK, khi nào nên dùng BotSDK trực tiếp

Nên dùng `TelegramSDK` khi:

- Ứng dụng đã dùng facade này cho search/chat/bot workflows.
- Bạn muốn một entry point thống nhất cho toàn bộ SDK.
- Bạn muốn dùng các helper sẵn có như `search_via_en_searchbot()`.

Nên dùng `BotSDK` trực tiếp khi:

- Bạn đang viết service chuyên biệt chỉ phục vụ bot orchestration.
- Bạn muốn tự kiểm soát registry, session store, và adapter lifecycle.
- Bạn không cần toàn bộ facade `TelegramSDK`.

### Quy tắc mở rộng cho đội phát triển

- Không đưa parser riêng của bot vào `sdk/transports.py`.
- Không hardcode command string ở nhiều nơi khác nhau.
- Mỗi bot mới phải có adapter riêng.
- Nếu bot có nhiều bước, phải mô tả rõ session key và state cần lưu.
- Nếu bot dùng callback hoặc pagination, logic đó phải nằm trong adapter.

### Các lỗi cần biết

Một số lỗi chính trong bot orchestration:

- `BotCapabilityError`: bot không hỗ trợ command được gọi.
- `BotValidationError`: request sai hoặc thiếu param bắt buộc.
- `BotTimeoutError`: bot không trả lời trong thời gian cho phép.
- `BotResponseError`: reply nhận được nhưng parse thất bại.
- `BotUnavailableError`: không resolve được bot hoặc bot không truy cập được.
- `InvalidEntityReferenceError`: tham chiếu chat không hợp lệ hoặc không đúng định dạng hỗ trợ.

### Ví dụ chạy script có sẵn

Script ví dụ dùng `BotSDK`:

```bash
.venv/bin/python examples/botkit_en_searchbot.py "sinh trắc học" --crawl-all-pages
```

Script ví dụ dùng `TelegramSDK`:

```bash
.venv/bin/python examples/en_searchbot_search.py "sinh trắc học" --crawl-all-pages
```

### Tình trạng hiện tại

Đã hoàn thành:

- Tạo `sdk/botkit/` làm lớp orchestration mới.
- Tích hợp `BotSDK` vào `TelegramSDK`.
- Migrate `@en_SearchBot` sang execution path mới.
- Giữ backward compatibility cho `search_via_en_searchbot()`.
- Thêm validation cơ bản cho command request.
- Thêm regression tests cho cả path cũ và path mới.
- Thêm retry/backoff cho các thao tác đọc transport trong flow bot.
- Thêm correlation mạnh hơn cho `@en_SearchBot` bằng metadata như `reply_to_message_id`.

### Hướng phát triển tiếp theo

- Hoàn thiện `RedisSessionStore` cho môi trường nhiều worker.
- Chuyển adapter minh họa thứ hai thành adapter dùng thật.

### Hardening hiện có cho `@en_SearchBot`

Flow `@en_SearchBot` hiện đã được siết thêm ở 2 hướng:

- Retry/backoff cho các thao tác đọc transport như `get_chat_history` và `get_message`
- Correlation mạnh hơn bằng metadata message, đặc biệt là `reply_to_message_id`

Điều này giúp giảm rủi ro ở các tình huống:

- Telethon timeout ngắn hoặc lỗi transient khi poll lịch sử
- Bot trả về message nhiễu cùng chat nhưng không phải phản hồi cho request hiện tại
- Pagination update bị chậm sau khi click nút `➡️`

Lưu ý:

- Retry tự động hiện chỉ ưu tiên cho các thao tác đọc/an toàn để tránh duplicate query
- `send_text()` không được retry mù để không vô tình gửi trùng lệnh
