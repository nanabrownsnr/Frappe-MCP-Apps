"""Frappe project overview tool."""

import asyncio
from typing import Any

from fastmcp.tools import ToolResult

from app.tools.frappe_common import chat_data, get, path_part


async def _slice(doctype: str, project: str) -> Any:
    return await get(
        f"/api/resource/{path_part(doctype)}",
        {"filters": f'[["{doctype}","project","=","{project}"]]', "limit_page_length": 50},
    )


def register_tool(mcp) -> None:
    @mcp.tool()
    async def frappe_job_overview(project: str) -> ToolResult:
        """Return a project and its related invoices and timesheets."""
        values = await asyncio.gather(
            get(f"/api/resource/Project/{path_part(project)}"),
            _slice("Sales Invoice", project),
            _slice("Purchase Invoice", project),
            _slice("Timesheet", project),
            return_exceptions=True,
        )
        names = ("project", "sales_invoices", "purchase_invoices", "timesheets")
        overview = {
            name: (str(value) if isinstance(value, BaseException) else value)
            for name, value in zip(names, values, strict=True)
        }
        if not isinstance(overview["project"], dict) or not overview["project"]:
            return ToolResult(content=f"No project record found for {project}.")
        return ToolResult(
            content=chat_data(f"Loaded project overview for {project}.", overview),
            structured_content={"doctype": "Project", "record": overview},
        )
