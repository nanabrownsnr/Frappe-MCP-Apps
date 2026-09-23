"""Frappe count tool."""

import json
from typing import Any

from app.tools.frappe_common import get, validate_doctype, validate_filters


def register_tool(mcp) -> None:
    @mcp.tool()
    async def frappe_count(doctype: str, filters: list[Any] | None = None) -> int:
        """Count records for an exact DocType name.

        First call frappe_doctypes to map the user's wording to the exact
        DocType name, then pass that exact name here.
        """
        doctype = validate_doctype(doctype)
        validate_filters(filters)
        params: dict[str, Any] = {"doctype": doctype}
        if filters:
            params["filters"] = json.dumps(filters)
        result = await get("/api/method/frappe.client.get_count", params)
        try:
            return int(result)
        except (TypeError, ValueError):
            raise ValueError("Frappe returned an invalid record count.") from None
