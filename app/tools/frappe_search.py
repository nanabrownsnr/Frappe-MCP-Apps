"""Frappe search tool."""

import json

from fastmcp.apps import AppConfig
from fastmcp.tools import ToolResult

from app.config import settings
from app.tools.frappe_common import get, normalize_doctype, path_part
from app.ui.frappe_ui.resource import VIEW_URI


def register_tool(mcp) -> None:
    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI, visibility=["model", "app"]))
    async def frappe_search(doctype: str, query: str = "", limit: int = 20) -> ToolResult:
        """Search current Frappe records for the calling user's ERP seat."""
        doctype = normalize_doctype(doctype)
        params = {
            "limit_page_length": max(1, min(limit, settings.FRAPPE_MAX_LIMIT)),
            "order_by": "modified desc",
        }
        if query:
            params["filters"] = json.dumps([[doctype, "name", "like", f"%{query}%"]])
        result = await get(f"/api/resource/{path_part(doctype)}", params)
        records = result if isinstance(result, list) else []
        if not records:
            return ToolResult(content=f"Found 0 {doctype} records.")
        return ToolResult(
            content=f"Found {len(records)} {doctype} records.",
            structured_content={"doctype": doctype, "records": records},
            meta={"ui": {"resourceUri": VIEW_URI}},
        )
