"""Tests for consistent per-call metadata on MCP tool responses."""

import asyncio
from types import SimpleNamespace

from fastmcp.tools import ToolResult

from app import main


def test_usage_middleware_adds_toolname_without_overwriting_existing_meta(monkeypatch):
    async def no_op(*args, **kwargs):
        return None

    monkeypatch.setattr(main, "get_http_headers", lambda: {})
    monkeypatch.setattr(main, "save_usage_report", no_op)

    result = ToolResult(
        content="Found records.",
        structured_content={"records": [{"name": "REC-001"}]},
        meta={"ui": {"resourceUri": "ui://twynity/frappe-dashboard.html"}},
    )
    context = SimpleNamespace(message=SimpleNamespace(name="frappe_list"))

    async def call_next(_context):
        return result

    returned = asyncio.run(main.UsageTrackingMiddleware().on_call_tool(context, call_next))

    assert returned is result
    assert returned.meta == {
        "ui": {"resourceUri": "ui://twynity/frappe-dashboard.html"},
        "toolname": "frappe_list",
    }
    assert returned.structured_content == {"records": [{"name": "REC-001"}]}


def test_usage_middleware_adds_toolname_to_results_without_existing_meta(monkeypatch):
    async def no_op(*args, **kwargs):
        return None

    monkeypatch.setattr(main, "get_http_headers", lambda: {})
    monkeypatch.setattr(main, "save_usage_report", no_op)

    result = ToolResult(content="7", structured_content={"count": 7})
    context = SimpleNamespace(message=SimpleNamespace(name="frappe_count"))

    async def call_next(_context):
        return result

    returned = asyncio.run(main.UsageTrackingMiddleware().on_call_tool(context, call_next))

    assert returned.meta == {"toolname": "frappe_count"}
