"""Frappe search tool."""

import json
from typing import Any

from fastmcp.apps import AppConfig

from app.config import settings
from app.tools.frappe_common import get, path_part, ui_result
from app.ui.frappe_ui.resource import VIEW_URI


def register_tool(mcp) -> None:
    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI, visibility=["model", "app"]))
    async def frappe_search(doctype: str, query: str = "", limit: int = 20) -> Any:
        """Search current Frappe records for the calling user's ERP seat."""
        params = {
            "limit_page_length": max(1, min(limit, settings.FRAPPE_MAX_LIMIT)),
            "order_by": "modified desc",
        }
        if query:
            params["filters"] = json.dumps([[doctype, "name", "like", f"%{query}%"]])
        result = await get(f"/api/resource/{path_part(doctype)}", params)
        records = result if isinstance(result, list) else []
        return ui_result(
            VIEW_URI,
            f"Found {len(records)} {doctype} records.",
            {"doctype": doctype, "records": records},
        )
