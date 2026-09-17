"""Frappe schema tool."""

from typing import Any

from app.tools.frappe_common import get, path_part


def register_tool(mcp) -> None:
    @mcp.tool()
    async def frappe_schema(doctype: str) -> dict[str, Any]:
        """Return safe field metadata for a Frappe DocType."""
        result = await get(f"/api/resource/DocType/{path_part(doctype)}")
        return result if isinstance(result, dict) else {}
