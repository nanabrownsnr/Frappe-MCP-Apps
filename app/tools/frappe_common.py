"""Shared Frappe transport and response-safety helpers."""

from typing import Any
from urllib.parse import quote

import httpx

from app.auth import get_current_user
from app.config import settings
from app.frappe_connection import get_connection


def path_part(value: str) -> str:
    return quote(value, safe="")


async def connection() -> tuple[str, str]:
    stored = await get_connection(get_current_user()["id"])
    if stored is None:
        raise ValueError("Configure your Frappe connection first.")
    return stored[0], f"token {stored[1]}:{stored[2]}"


def redact(value: Any) -> Any:
    if isinstance(value, list):
        return [redact(item) for item in value]
    if not isinstance(value, dict):
        return value
    blocked = ("password", "secret", "token", "salary", "bank", "sin", "passport")
    return {k: redact(v) for k, v in value.items() if not any(x in k.lower() for x in blocked)}


async def get(path: str, params: dict[str, Any] | None = None) -> Any:
    base, auth = await connection()
    async with httpx.AsyncClient(timeout=settings.FRAPPE_TIMEOUT_SECONDS) as client:
        response = await client.get(f"{base}{path}", params=params, headers={"Authorization": auth})
        # CRM installations differ in their Lead/Deal field names. Frappe
        # answers an invalid `fields` projection with 417. Retry once without
        # that optional projection; permissions still apply and redaction is
        # performed below before the result reaches the model or UI.
        if response.status_code == 417 and params and "fields" in params:
            fallback_params = dict(params)
            fallback_params.pop("fields")
            response = await client.get(f"{base}{path}", params=fallback_params, headers={"Authorization": auth})
    if response.status_code in (401, 403):
        raise PermissionError("Frappe denied this read.")
    response.raise_for_status()
    body = response.json()
    return redact(body.get("data", body.get("message", body)))
