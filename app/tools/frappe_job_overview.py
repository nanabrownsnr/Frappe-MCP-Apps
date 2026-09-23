"""Frappe project overview tool."""

import asyncio
import json
from typing import Any

from fastmcp.tools import ToolResult

from app.tools.frappe_common import chat_data, get, path_part


async def _slice(doctype: str, project: str) -> Any:
    return await get(
        f"/api/resource/{path_part(doctype)}",
        {
            "filters": json.dumps([[doctype, "project", "=", project]]),
            "limit_page_length": 50,
        },
    )


def register_tool(mcp) -> None:
    @mcp.tool()
    async def frappe_job_overview(project: str) -> ToolResult:
        """Return a project and its related invoices and timesheets."""
        if not project.strip():
            raise ValueError("Input 'project' must be the exact, non-empty Project record name.")
        values = await asyncio.gather(
            get(f"/api/resource/Project/{path_part(project)}"),
            _slice("Sales Invoice", project),
            _slice("Purchase Invoice", project),
            _slice("Timesheet", project),
            return_exceptions=True,
        )
        project_result = values[0]
        if isinstance(project_result, BaseException):
            raise project_result
        if not isinstance(project_result, dict):
            raise ValueError(f"Frappe returned an invalid Project response for {project}.")
        names = ("project", "sales_invoices", "purchase_invoices", "timesheets")
        overview = {
            name: (str(value) if isinstance(value, BaseException) else value)
            for name, value in zip(names, values, strict=True)
        }
        if not overview["project"]:
            return ToolResult(content=f"No project record found for {project}.")
        return ToolResult(
            content=chat_data(f"Loaded project overview for {project}.", overview),
            structured_content={"doctype": "Project", "record": overview},
        )
