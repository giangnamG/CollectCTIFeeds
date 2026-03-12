"""Example adapter for a command-driven monitoring bot."""

from __future__ import annotations

from sdk.botkit.base import BaseBotAdapter
from sdk.botkit.models import (
    BotCapability,
    BotCommand,
    BotRequest,
    BotResponse,
    BotSession,
    ExecutionMode,
)
from sdk.models import Message


class MonitoringBotAdapter(BaseBotAdapter):
    """Reference adapter showing how a more traditional command bot plugs in."""

    bot_id = "monitoring"
    bot_username = "monitoring_bot"

    _command_templates = {
        "monitor.status": "/status",
        "monitor.search": "/search {query}",
    }

    def supports(self, command_name: str) -> bool:
        return command_name in self._command_templates

    def get_supported_commands(self) -> list[BotCommand]:
        return [
            BotCommand(
                name="monitor.status",
                aliases=["status"],
                capabilities={BotCapability.MONITORING},
                execution_mode=ExecutionMode.SYNC,
            ),
            BotCommand(
                name="monitor.search",
                aliases=["search"],
                parameters={"query": "str"},
                capabilities={BotCapability.MONITORING, BotCapability.SEARCH},
                execution_mode=ExecutionMode.SYNC,
            ),
        ]

    def map_command(self, request: BotRequest, session: BotSession) -> str:
        template = self._command_templates[request.command_name]
        if "{query}" in template:
            query = str(request.params.get("query", "")).strip()
            if not query:
                raise ValueError("monitor.search requires a non-empty 'query' parameter.")
            session.state["last_query"] = query
            return template.format(query=query)
        return template

    def parse_response(
        self,
        *,
        request: BotRequest,
        session: BotSession,
        sent_message: Message,
        reply_messages: list[Message],
    ) -> BotResponse:
        combined_text = "\n".join(message.text for message in reply_messages)
        return BotResponse(
            bot_id=self.bot_id,
            command_name=request.command_name,
            status="ok",
            data={
                "text": combined_text,
                "reply_count": len(reply_messages),
            },
            raw_messages=reply_messages,
            correlation_id=request.context.correlation_id or request.request_id,
        )
