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
from app.tools.frappe_doctypes import register_tool as register_frappe_doctypes
from app.tools.frappe_get import register_tool as register_frappe_get
from app.tools.frappe_job_overview import register_tool as register_frappe_job_overview
from app.tools.frappe_list import register_tool as register_frappe_list
from app.tools.frappe_schema import register_tool as register_frappe_schema
from app.tools.frappe_search import register_tool as register_frappe_search
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
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["mcp-protocol-version", "mcp-session-id", "Authorization", "Content-Type"],
        expose_headers=["mcp-session-id"],
    )
]


app = mcp.http_app(middleware=middleware)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
