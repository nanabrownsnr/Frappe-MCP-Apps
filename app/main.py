"""Compose and expose the FastMCP ASGI application.

Import and register new tools/resources here. Twynity-specific HTTP routes live
in ``twynity.py`` and are separate from FastMCP's JWT-protected MCP transport.
"""

import asyncio
from contextlib import asynccontextmanager, suppress
from logging import getLogger

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware as MCPMiddleware
from fastmcp.server.middleware import MiddlewareContext
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from app.auth import get_auth_provider
from app.config import settings
from app.frappe_connection import ensure_schema
from app.license import license_watcher
from app.tools.frappe_count import register_tool as register_frappe_count
from app.tools.frappe_create_prepare import register_tool as register_frappe_create_prepare
from app.tools.frappe_create_record import register_tool as register_frappe_create_record
from app.tools.frappe_doctypes import register_tool as register_frappe_doctypes
from app.tools.frappe_get import register_tool as register_frappe_get
from app.tools.frappe_job_overview import register_tool as register_frappe_job_overview
from app.tools.frappe_list import register_tool as register_frappe_list
from app.tools.frappe_schema import register_tool as register_frappe_schema
from app.tools.frappe_search import register_tool as register_frappe_search
from app.tools.frappe_update import register_tool as register_frappe_update
from app.twynity import register_routes
from app.ui.frappe_ui.resource import register_resource
from app.usage import save_usage_report

logger = getLogger(__name__)


@asynccontextmanager
async def app_lifespan(server):
    await ensure_schema()
    task = asyncio.create_task(license_watcher())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


mcp = FastMCP(
    settings.APP_TITLE,
    instructions=(
        "You are connected to the user's Frappe ERP site through their saved API credentials. "
        "You can query any DocType that is installed and readable by that Frappe account, "
        "across available modules such as ERPNext, CRM, HRMS, and custom apps. Installed apps "
        "vary by site. When the user asks about Frappe/ERP data, do not claim you lack access: "
        "use frappe_doctypes to identify the exact DocType when needed, then use that exact name. "
        "If multiple discovered DocTypes could reasonably match the request, ask the user which "
        "one they mean instead of guessing. "
        "For lists, omit fields unless the user asks for a subset; frappe_list discovers fields "
        "from the DocType schema internally. Its chat result contains the record count and exact "
        "record IDs with labels; full data is sent to the canvas. Do not repeat a list call just "
        "to obtain fields. If the user asks to open a listed record, call frappe_get with the "
        "exact DocType and ID from the result. For any request to create, add, or make a new "
        "record (for example, ‘create a new lead’), first use frappe_doctypes to identify the "
        "exact DocType. If multiple DocTypes fit, ask the user which one they mean. Then call "
        "frappe_create_prepare with the exact DocType and known values to open the editable form. "
        "Do not create directly: only the user's explicit Create button in the UI may invoke the "
        "app-only frappe_create_record tool. When asked to change a record, call "
        "frappe_update with only the explicitly requested fields and values; use null only when "
        "the user explicitly asks to clear a field. Do not claim a change succeeded unless the "
        "tool confirms it. For a pipeline or record view, tell the user the "
        "full data is displayed on the canvas. If a tool reports invalid input, use the named "
        "argument or filter index in the error to correct the call and retry when the correction "
        "is clear; ask the user only when the missing or ambiguous value cannot be inferred. "
        "For connection, permission, timeout, or server errors, follow the recovery hint in the "
        "tool error and do not claim the query returned no records."
    ),
    auth=get_auth_provider(),
    lifespan=app_lifespan,
)


register_frappe_list(mcp)
register_frappe_get(mcp)
register_frappe_search(mcp)
register_frappe_count(mcp)
register_frappe_doctypes(mcp)
register_frappe_schema(mcp)
register_frappe_job_overview(mcp)
register_frappe_update(mcp)
register_frappe_create_prepare(mcp)
register_frappe_create_record(mcp)


class UsageTrackingMiddleware(MCPMiddleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        try:
            headers = get_http_headers()
            await save_usage_report(
                method="TOOL_CALL",
                endpoint=context.message.name,
                auth_header=headers.get("authorization"),
            )
        except Exception:
            logger.exception("Usage tracking failed — continuing with tool call anyway")

        return await call_next(context)


mcp.add_middleware(UsageTrackingMiddleware())

register_resource(mcp)
register_routes(mcp)


origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
if not origins:
    raise RuntimeError("ALLOWED_ORIGINS must contain at least one origin")

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id"],
    )
]


app = mcp.http_app(
    middleware=middleware,
    transport="streamable-http",
    stateless_http=True,
    json_response=True,
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
