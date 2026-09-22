"""Frappe DocType discovery tool."""

import json
from typing import Any

from app.tools.frappe_common import get


def register_tool(mcp) -> None:
    @mcp.tool()
    async def frappe_doctypes(query: str = "", limit: int = 200) -> list[dict[str, Any]]:
        """Discover exact Frappe DocType names before listing or searching.

        Use this to map the user's wording to available record types. If more
        than one returned DocType could reasonably match, ask the user which
        one they mean before querying records. Pass the exact selected name
        to the other Frappe tools.
        """
        filters: list[list[Any]] = [["DocType", "istable", "=", 0]]
        if query:
            filters.append(["DocType", "name", "like", f"%{query}%"])
        result = await get(
            "/api/resource/DocType",
            {
                "fields": json.dumps(["name", "module", "issingle"]),
                "filters": json.dumps(filters),
                "limit_page_length": max(1, min(limit, 500)),
            },
        )
        return result if isinstance(result, list) else []
