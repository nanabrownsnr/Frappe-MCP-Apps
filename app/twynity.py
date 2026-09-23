"""Register Twynity's manifest, health, and external-connection routes.

FastMCP's JWT verifier protects its MCP transport, not custom routes by
default. Manifest, schema, health, and configuration preflight routes are
public; routes that read or save user connection data authenticate explicitly.
"""

from pydantic import BaseModel, Field, HttpUrl, ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.auth import get_current_user
from app.config import settings
from app.frappe_connection import get_connection, save_connection


def register_routes(mcp):
    class FrappeConnection(BaseModel):
        frappe_base_url: HttpUrl
        api_key: str = Field(min_length=1)
        api_secret: str = Field(min_length=1)

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

    @mcp.custom_route("/api/v1/configuration", methods=["POST", "OPTIONS"])
    async def configure_frappe(request: Request) -> JSONResponse:
        if request.method == "OPTIONS":
            return Response(status_code=204)
        try:
            user = get_current_user()
        except ValueError:
            return JSONResponse({"detail": "Authentication required."}, status_code=401)
        try:
            body = await request.json()
        except ValueError:
            return JSONResponse({"detail": "Request body must contain valid JSON."}, status_code=400)
        try:
            payload = FrappeConnection.model_validate(body)
        except ValidationError as error:
            details = [
                {"field": ".".join(str(part) for part in item["loc"]), "message": item["msg"]}
                for item in error.errors(include_input=False)
            ]
            return JSONResponse({"detail": details}, status_code=422)
        await save_connection(user["id"], str(payload.frappe_base_url), payload.api_key, payload.api_secret)
        return JSONResponse({"configured": True})

    @mcp.custom_route("/api/v1/external-connection/me", methods=["GET"])
    async def external_connection_me(request: Request) -> JSONResponse:
        try:
            user = get_current_user()
        except ValueError:
            return JSONResponse({"detail": "Authentication required."}, status_code=401)
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
