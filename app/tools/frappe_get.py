"""Frappe single-record tool."""

from typing import Any

from fastmcp.apps import AppConfig

from app.tools.frappe_common import get, path_part, ui_result
from app.ui.frappe_ui.resource import VIEW_URI


def register_tool(mcp) -> None:
    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI, visibility=["model", "app"]))
    async def frappe_get(doctype: str, name: str) -> Any:
        """Fetch one current record as the calling user's Frappe seat."""
        result = await get(f"/api/resource/{path_part(doctype)}/{path_part(name)}")
        record = result if isinstance(result, dict) else {}
        return ui_result(
            VIEW_URI, f"Loaded {doctype} {name}.", {"doctype": doctype, "record": record}
        )
