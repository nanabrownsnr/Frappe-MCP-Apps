"""Register Twynity's well-known manifest and health HTTP routes.

FastMCP's JWT verifier protects its MCP transport, not custom routes by
default. These two routes are intentionally public; add explicit authorization
inside any new custom route that should be protected.
"""

from pydantic import BaseModel, HttpUrl
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.auth import get_current_user
from app.config import settings
from app.frappe_connection import get_connection, save_connection


def register_routes(mcp):
    class FrappeConnection(BaseModel):
        frappe_base_url: HttpUrl
        api_key: str
        api_secret: str

    @mcp.custom_route("/api/v1/schema", methods=["GET"])
    async def configuration_schema(request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "name": "frappe_configuration",
                "endpoint": "/api/v1/configuration",
                "method": "POST",
                "schema": {
                    "frappe_base_url": "string",
                    "api_key": "string",
                    "api_secret": "string",
                },
            }
        )

    @mcp.custom_route("/api/v1/configuration", methods=["POST"])
    async def configure_frappe(request: Request) -> JSONResponse:
        user = get_current_user()
        payload = FrappeConnection.model_validate(await request.json())
        await save_connection(user["id"], str(payload.frappe_base_url), payload.api_key, payload.api_secret)
        return JSONResponse({"configured": True})

    @mcp.custom_route("/api/v1/external-connection/me", methods=["GET"])
    async def external_connection_me(request: Request) -> JSONResponse:
        user = get_current_user()
        return JSONResponse({"connected": await get_connection(user["id"]) is not None})

    @mcp.custom_route("/api/v1/.well-known/mcp.json", methods=["GET"])
    async def manifest(request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "name": settings.APP_TITLE,
                "base_url": f"{settings.PUBLIC_URL}/mcp",
                "version": settings.APP_VERSION,
                "external_connections": {"project": {"name": "frappe_configuration"}},
            },
            status_code=200,
        )

    @mcp.custom_route("/api/v1/health", methods=["GET"])
    async def health_status(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"}, status_code=200)
