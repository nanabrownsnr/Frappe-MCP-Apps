"""Shared Frappe transport and response-safety helpers."""

import json
from typing import Any
from urllib.parse import quote

import httpx

from app.auth import get_current_user
from app.config import settings
from app.frappe_connection import get_connection


def path_part(value: str) -> str:
    return quote(value, safe="")


async def doctype_schema(doctype: str) -> dict[str, Any]:
    """Fetch a DocType's metadata for internal schema-driven tool behavior."""
    result = await get(f"/api/resource/DocType/{path_part(doctype)}")
    return result if isinstance(result, dict) else {}


def schema_fields(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Return valid fields for generic record listing and UI column metadata."""
    fields = schema.get("fields", [])
    if not isinstance(fields, list):
        return [{"fieldname": "name", "label": "Name", "fieldtype": "Data"}]

    selected = [
        field for field in fields
        if isinstance(field, dict)
        and field.get("fieldname")
        and field.get("fieldtype") not in {"Section Break", "Column Break", "Tab Break", "Table", "Table MultiSelect", "HTML", "Button", "Fold", "Heading", "Image"}
        and not field.get("hidden")
    ]
    by_name = {field["fieldname"]: field for field in selected}
    for name, label in (("name", "Name"), ("owner", "Owner"), ("creation", "Created"), ("modified", "Modified")):
        by_name.setdefault(name, {"fieldname": name, "label": label, "fieldtype": "Data"})
    return list(by_name.values())


class FrappeRequestError(RuntimeError):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        super().__init__(detail)


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


def chat_data(summary: str, data: Any, *, canvas: bool = False) -> str:
    """Include returned records in model-visible text as well as UI payloads."""
    rendered = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    suffix = "\nThese records are also displayed on the canvas." if canvas else ""
    return f"{summary}\nData:\n{rendered}{suffix}"


def chat_record_index(
    doctype: str,
    records: list[dict[str, Any]],
    schema: dict[str, Any],
    metadata: list[dict[str, Any]],
    *,
    canvas: bool = False,
) -> str:
    """Return a compact count and get-ready record ID/label index for chat."""
    ignored = {"name", "owner", "creation", "modified", "modified_by", "docstatus"}
    title_candidates = []
    configured_title = schema.get("title_field")
    if configured_title:
        title_candidates.append(configured_title)
    search_fields = schema.get("search_fields", "")
    if isinstance(search_fields, str):
        title_candidates.extend(
            value.strip()
            for value in search_fields.split(",")
            if value.strip() not in ignored
        )
    title_candidates.extend(
        field["fieldname"]
        for field in metadata
        if field["fieldname"] not in ignored
        and field.get("fieldtype") in {"Data", "Link", "Select", "Email", "Phone"}
    )
    title_candidates = list(dict.fromkeys(title_candidates))

    references = []
    for record in records:
        name = record.get("name")
        if not name:
            continue
        label = next((record.get(field) for field in title_candidates if record.get(field)), None)
        references.append(f"{name} ({label})" if label and str(label) != str(name) else str(name))

    message = f"Found {len(records)} {doctype} records."
    if references:
        message += "\nRecord names (use these exact IDs with frappe_get): " + "; ".join(references)
    if canvas:
        message += "\nFull record details are displayed on the canvas."
    return message


async def get(path: str, params: dict[str, Any] | None = None) -> Any:
    base, auth = await connection()
    async with httpx.AsyncClient(timeout=settings.FRAPPE_TIMEOUT_SECONDS) as client:
        response = await client.get(f"{base}{path}", params=params, headers={"Authorization": auth})
    if response.status_code in (401, 403):
        raise PermissionError("Frappe denied this read.")
    if response.status_code == 417:
        detail = response.text[:500].replace("\n", " ")
        raise FrappeRequestError(417, f"Frappe rejected the request (417). Check the DocType, fields, or filters. {detail}")
    response.raise_for_status()
    body = response.json()
    return redact(body.get("data", body.get("message", body)))
