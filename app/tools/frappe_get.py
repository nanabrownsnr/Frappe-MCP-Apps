"""Frappe single-record tool."""

from fastmcp.apps import AppConfig
from fastmcp.tools import ToolResult

from app.tools.frappe_common import chat_data, get, path_part
from app.ui.frappe_ui.resource import VIEW_URI


def register_tool(mcp) -> None:
    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI, visibility=["model", "app"]))
    async def frappe_get(doctype: str, name: str) -> ToolResult:
        """Fetch one record by exact DocType and record name.

        First call frappe_doctypes to confirm the exact DocType, then use
        frappe_search to find the record name if it is not already known.
        """
        result = await get(f"/api/resource/{path_part(doctype)}/{path_part(name)}")
        record = result if isinstance(result, dict) else {}
        if not record:
            return ToolResult(content=f"No {doctype} record found for {name}.")
        return ToolResult(
            content=chat_data(f"Loaded {doctype} {name}.", record, canvas=True),
            structured_content={"doctype": doctype, "record": record},
            meta={"ui": {"resourceUri": VIEW_URI}},
        )
