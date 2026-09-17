"""Frappe single-record tool."""

from fastmcp.apps import AppConfig
from fastmcp.tools import ToolResult

from app.tools.frappe_common import get, path_part
from app.ui.frappe_ui.resource import VIEW_URI


def register_tool(mcp) -> None:
    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI, visibility=["model", "app"]))
    async def frappe_get(doctype: str, name: str) -> ToolResult:
        """Fetch one current record as the calling user's Frappe seat."""
        result = await get(f"/api/resource/{path_part(doctype)}/{path_part(name)}")
        record = result if isinstance(result, dict) else {}
        return ToolResult(
            content=f"Loaded {doctype} {name}.",
            structured_content={"doctype": doctype, "record": record},
            meta={"ui": {"resourceUri": VIEW_URI}},
        )
