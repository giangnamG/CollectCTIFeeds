"""Official tool schema definitions for higher-level delivery layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolParameterSchema:
    """Describes one input parameter for a tool-facing API."""

    name: str
    type: str
    description: str
    required: bool = False
    default: Any = None
    enum: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
            "default": self.default,
        }
        if self.enum:
            payload["enum"] = list(self.enum)
        return payload


@dataclass(slots=True)
class ToolSchema:
    """Tool schema for SDK methods that can be surfaced as external tools."""

    name: str
    description: str
    parameters: list[ToolParameterSchema] = field(default_factory=list)
    result_description: str = ""
    tags: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [parameter.to_payload() for parameter in self.parameters],
            "result_description": self.result_description,
            "tags": list(self.tags),
        }


class TelegramToolCatalog:
    """Catalog of tool schemas for facades such as MCP or internal automation."""

    def __init__(self, tools: list[ToolSchema] | None = None) -> None:
        self._tools = tools or build_default_tool_schemas()
        self._by_name = {tool.name: tool for tool in self._tools}

    def list_tools(self) -> list[ToolSchema]:
        return list(self._tools)

    def get_tool(self, name: str) -> ToolSchema:
        return self._by_name[name]

    def to_payload(self) -> list[dict[str, Any]]:
        return [tool.to_payload() for tool in self._tools]


def build_default_tool_schemas() -> list[ToolSchema]:
    return [
        ToolSchema(
            name="resolve_chat_reference",
            description="Chuẩn hóa chat reference từ chat_id, @username hoặc t.me link.",
            parameters=[
                ToolParameterSchema(
                    name="reference",
                    type="string|integer",
                    description="Chat reference cần resolve.",
                    required=True,
                )
            ],
            result_description="Thông tin chat đã chuẩn hóa.",
            tags=["chat", "reference"],
        ),
        ToolSchema(
            name="inspect_chat",
            description="Đọc nhanh metadata chat và một lát cắt history có lọc theo hướng.",
            parameters=[
                ToolParameterSchema(
                    name="chat_reference",
                    type="string|integer",
                    description="Chat reference cần inspect.",
                    required=True,
                ),
                ToolParameterSchema(
                    name="history_limit",
                    type="integer",
                    description="Số message tối đa cần lấy.",
                    default=10,
                ),
                ToolParameterSchema(
                    name="direction",
                    type="string",
                    description="Hướng đọc history.",
                    default="latest",
                    enum=["latest", "before", "after", "around"],
                ),
                ToolParameterSchema(
                    name="anchor_message_id",
                    type="integer|null",
                    description="Message neo cho before/after/around.",
                    default=None,
                ),
                ToolParameterSchema(
                    name="query",
                    type="string|null",
                    description="Chỉ giữ các message chứa query.",
                    default=None,
                ),
            ],
            result_description="ChatInspection dataclass hoặc payload tương đương.",
            tags=["chat", "inspection"],
        ),
        ToolSchema(
            name="inspect_chat_page",
            description="Lấy một page của chat history lớn với cursor rõ ràng cho pagination.",
            parameters=[
                ToolParameterSchema(
                    name="chat_reference",
                    type="string|integer",
                    description="Chat reference cần đọc lịch sử.",
                    required=True,
                ),
                ToolParameterSchema(
                    name="page_size",
                    type="integer",
                    description="Kích thước mỗi trang kết quả.",
                    default=20,
                ),
                ToolParameterSchema(
                    name="cursor",
                    type="string|null",
                    description="Cursor token từ page trước, nếu có.",
                    default=None,
                ),
                ToolParameterSchema(
                    name="before_message_id",
                    type="integer|null",
                    description="Neo thủ công để đọc các message cũ hơn.",
                    default=None,
                ),
                ToolParameterSchema(
                    name="query",
                    type="string|null",
                    description="Lọc message theo query.",
                    default=None,
                ),
            ],
            result_description="ChatInspection có kèm pagination và next cursor.",
            tags=["chat", "pagination", "inspection"],
        ),
        ToolSchema(
            name="inspect_message",
            description="Inspect một message cụ thể, button và context trước/sau.",
            parameters=[
                ToolParameterSchema(
                    name="chat_reference",
                    type="string|integer",
                    description="Chat chứa message cần inspect.",
                    required=True,
                ),
                ToolParameterSchema(
                    name="message_id",
                    type="integer",
                    description="ID của message cần inspect.",
                    required=True,
                ),
                ToolParameterSchema(
                    name="before_limit",
                    type="integer|null",
                    description="Số message ngữ cảnh phía trước.",
                    default=None,
                ),
                ToolParameterSchema(
                    name="after_limit",
                    type="integer|null",
                    description="Số message ngữ cảnh phía sau.",
                    default=None,
                ),
                ToolParameterSchema(
                    name="query",
                    type="string|null",
                    description="Lọc context theo query.",
                    default=None,
                ),
            ],
            result_description="MessageInspection dataclass hoặc payload tương đương.",
            tags=["message", "inspection"],
        ),
        ToolSchema(
            name="list_message_buttons",
            description="Liệt kê inline button của một message dưới dạng reference ổn định.",
            parameters=[
                ToolParameterSchema(
                    name="chat_reference",
                    type="string|integer",
                    description="Chat chứa message.",
                    required=True,
                ),
                ToolParameterSchema(
                    name="message_id",
                    type="integer",
                    description="ID message cần đọc button.",
                    required=True,
                ),
            ],
            result_description="Danh sách MessageButtonRef.",
            tags=["message", "buttons"],
        ),
        ToolSchema(
            name="click_button_reference",
            description="Click inline button bằng reference đã inspect trước đó.",
            parameters=[
                ToolParameterSchema(
                    name="chat_reference",
                    type="string|integer",
                    description="Chat chứa message.",
                    required=True,
                ),
                ToolParameterSchema(
                    name="message_id",
                    type="integer",
                    description="ID message cần click button.",
                    required=True,
                ),
                ToolParameterSchema(
                    name="button",
                    type="object",
                    description="MessageButtonRef hoặc payload button tương đương.",
                    required=True,
                ),
            ],
            result_description="Message đã được refresh sau khi click button.",
            tags=["message", "buttons", "action"],
        ),
        ToolSchema(
            name="execute_bot_command",
            description="Thực thi một bot command chuẩn hóa qua BotSDK.",
            parameters=[
                ToolParameterSchema(
                    name="bot_id",
                    type="string",
                    description="Mã định danh bot adapter.",
                    required=True,
                ),
                ToolParameterSchema(
                    name="command_name",
                    type="string",
                    description="Tên command canonical hoặc alias.",
                    required=True,
                ),
                ToolParameterSchema(
                    name="params",
                    type="object",
                    description="Tham số đầu vào cho command.",
                    default={},
                ),
            ],
            result_description="BotResponse chuẩn hóa.",
            tags=["bot", "command"],
        ),
    ]
