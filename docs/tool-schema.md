## Tool Schema chính thức cho lớp facade

Tài liệu này mô tả lớp `sdk/tool_schema.py`, được thêm vào để chuẩn bị cho các delivery layer như:

- MCP facade
- internal tool runner
- automation gateway

### Mục tiêu

SDK hiện đã có domain logic và orchestration.

Để dựng một lớp tool phía trên mà không phải tự suy luận input/output của từng method, dự án cần một lớp schema chính thức mô tả:

- tên tool
- ý nghĩa tool
- input parameter
- output mong đợi
- tag chức năng

### Các class chính

- `ToolParameterSchema`
  Mô tả một input parameter

- `ToolSchema`
  Mô tả một tool hoàn chỉnh

- `TelegramToolCatalog`
  Catalog chứa danh sách tool schema mặc định

### Cách dùng nhanh

```python
from sdk import TelegramToolCatalog

catalog = TelegramToolCatalog()
for tool in catalog.list_tools():
    print(tool.name, tool.tags)
```

Nếu cần payload dạng `dict`:

```python
payload = TelegramToolCatalog().to_payload()
```

### Các tool schema mặc định hiện có

Hiện tại catalog mặc định đã mô tả các tool sau:

- `resolve_chat_reference`
- `inspect_chat`
- `inspect_chat_page`
- `inspect_message`
- `list_message_buttons`
- `click_button_reference`
- `execute_bot_command`

### Vì sao cần `inspect_chat_page`

Đối với chat history lớn, chỉ dùng `inspect_chat()` là chưa đủ rõ cho pagination.

`inspect_chat_page()` giải quyết vấn đề đó bằng cách trả về:

- danh sách message của page hiện tại
- `pagination.next_before_message_id`
- `pagination.next_cursor`
- metadata về số lượng đã scan và đã trả về

### Cursor hiện tại hoạt động thế nào

SDK dùng `HistoryCursor` để chuẩn hóa cursor.

Cursor chứa:

- `before_message_id`
- `page_size`
- `query`
- `direction`

Cursor có thể:

- truyền trực tiếp dưới dạng object
- encode thành token string bằng `to_token()`
- decode lại bằng `HistoryCursor.from_token(token)`

### Ví dụ dùng cursor

```python
first_page = sdk.inspect_chat_page("@public_chan", page_size=20)
next_cursor = first_page.pagination.next_cursor

second_page = sdk.inspect_chat_page(
    "@public_chan",
    cursor=next_cursor,
)
```

Nếu muốn dùng token:

```python
token = next_cursor.to_token()
page = sdk.inspect_chat_page("@public_chan", cursor=token)
```

### Tool-ready payload

Ngoài dataclass inspection, SDK còn có:

- `inspect_chat_tool_payload(...)`
- `inspect_chat_page_tool_payload(...)`
- `inspect_message_tool_payload(...)`

Các method này trả về payload dạng `dict`, phù hợp để đưa thẳng vào:

- MCP tool result
- JSON API
- log/debug pipeline

### Phạm vi của tool schema

Lưu ý:

- `sdk/tool_schema.py` chỉ mô tả contract ở mức tool
- nó không thực thi tool
- nó không thay thế `TelegramSDK` hay `BotSDK`

Nói ngắn gọn:

- `TelegramSDK` và `BotSDK` là execution layer
- `tool_schema.py` là contract layer cho delivery interface

### Khi nào nên mở rộng catalog

Bạn nên thêm tool schema mới khi:

- SDK có thêm public method có ý nghĩa ở delivery layer
- một bot command cần được expose như tool rõ ràng
- MCP facade hoặc automation layer cần contract ổn định

Bạn không nên thêm tool schema mới nếu:

- method còn đang thử nghiệm nội bộ
- public API chưa ổn định
- output chưa đủ chuẩn hóa
