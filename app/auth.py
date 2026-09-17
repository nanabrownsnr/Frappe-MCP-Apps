"""Configure JWT verification for MCP requests.

Change the account-service/JWKS settings in ``config.py``; custom HTTP routes
registered in ``twynity.py`` are not automatically protected by this verifier.
"""

from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token

from app.config import settings


def get_auth_provider() -> JWTVerifier:
    """Builds the auth checker FastMCP will run on every incoming request."""
    jwks_url = (
        f"{settings.ACCOUNT_SERVICE_URL.rstrip('/')}"
        f"/{settings.ACCOUNT_SERVICE_JWKS_ENDPOINT.lstrip('/')}"
    )
    return JWTVerifier(jwks_uri=jwks_url)


def get_current_user() -> dict[str, str]:
    token = get_access_token()
    if token is None:
        raise ValueError("User is not authenticated.")
    claims = token.claims
    user_id = str(claims.get("id") or claims.get("sub") or "")
    if not user_id:
        raise ValueError("Authenticated token has no user id.")
    return {"id": user_id, "email": str(claims.get("sub") or "")}
