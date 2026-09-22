"""Frappe schema tool."""

from typing import Any

from app.tools.frappe_common import doctype_schema


def register_tool(mcp) -> None:
    @mcp.tool()
    async def frappe_schema(doctype: str) -> dict[str, Any]:
        """Return field metadata for a Frappe DocType.

        First call frappe_doctypes to confirm the exact DocType name.
        """
        return await doctype_schema(doctype)
