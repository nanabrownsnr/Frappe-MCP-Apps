"""Frappe list tool."""

import json
from typing import Any

from fastmcp.apps import AppConfig

from app.config import settings
from app.tools.frappe_common import get, path_part, ui_result
from app.ui.frappe_ui.resource import VIEW_URI


def register_tool(mcp) -> None:
    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI, visibility=["model", "app"]))
    async def frappe_list(
        doctype: str,
        fields: list[str] | None = None,
        filters: list[Any] | None = None,
        order_by: str | None = None,
        limit: int = 20,
        start: int = 0,
    ) -> Any:
        """List current records as the calling user's Frappe seat."""
        params: dict[str, Any] = {
            "fields": json.dumps(fields or ["name"]),
            "limit_page_length": max(1, min(limit, settings.FRAPPE_MAX_LIMIT)),
            "limit_start": max(0, start),
        }
        if filters:
            params["filters"] = json.dumps(filters)
        if order_by:
            params["order_by"] = order_by
        result = await get(f"/api/resource/{path_part(doctype)}", params)
        records = result if isinstance(result, list) else []
        return ui_result(
            VIEW_URI,
            f"Found {len(records)} {doctype} records.",
            {"doctype": doctype, "records": records},
        )
