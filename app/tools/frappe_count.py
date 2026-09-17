"""Frappe count tool."""

import json
from typing import Any

from app.tools.frappe_common import get


def register_tool(mcp) -> None:
    @mcp.tool()
    async def frappe_count(doctype: str, filters: list[Any] | None = None) -> int:
        """Count permitted records without downloading them."""
        params: dict[str, Any] = {"doctype": doctype}
        if filters:
            params["filters"] = json.dumps(filters)
        result = await get("/api/method/frappe.client.get_count", params)
        try:
            return int(result)
        except (TypeError, ValueError):
            return 0
