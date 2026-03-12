from __future__ import annotations

import unittest

from sdk import TelegramToolCatalog, build_default_tool_schemas


class ToolSchemaTests(unittest.TestCase):
    def test_default_tool_catalog_contains_inspection_and_bot_tools(self) -> None:
        catalog = TelegramToolCatalog()
        tool_names = [tool.name for tool in catalog.list_tools()]

        self.assertIn("resolve_chat_reference", tool_names)
        self.assertIn("inspect_chat", tool_names)
        self.assertIn("inspect_chat_page", tool_names)
        self.assertIn("inspect_message", tool_names)
        self.assertIn("execute_bot_command", tool_names)

    def test_tool_payload_exposes_parameters_and_tags(self) -> None:
        tools = build_default_tool_schemas()
        page_tool = next(tool for tool in tools if tool.name == "inspect_chat_page")
        payload = page_tool.to_payload()

        parameter_names = [item["name"] for item in payload["parameters"]]
        self.assertEqual(payload["name"], "inspect_chat_page")
        self.assertIn("pagination", " ".join(payload["tags"]))
        self.assertIn("cursor", parameter_names)
        self.assertIn("page_size", parameter_names)


if __name__ == "__main__":
    unittest.main()
