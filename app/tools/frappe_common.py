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
    """Fetch Frappe's merged metadata, including custom fields, for a DocType."""
    result = await get(
        "/api/method/frappe.desk.form.load.getdoctype",
        {"doctype": doctype},
    )
    if not isinstance(result, dict):
        raise ValueError(f"Frappe returned invalid metadata for DocType {doctype!r}.")

    # getdoctype adds the metadata bundle to the top-level ``docs`` response.
    # Also accept a ``message`` wrapper for Frappe versions/proxies that wrap
    # the method response differently.
    bundle = result.get("docs")
    if not isinstance(bundle, list):
        message = result.get("message")
        bundle = message.get("docs") if isinstance(message, dict) else message
    if isinstance(bundle, dict):
        bundle = [bundle]
    if isinstance(bundle, list):
        for metadata in bundle:
            if isinstance(metadata, dict) and metadata.get("name") == doctype:
                return metadata

    raise ValueError(f"Frappe returned no metadata for DocType {doctype!r}.")


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
    def __init__(self, status_code: int | None, detail: str):
        self.status_code = status_code
        super().__init__(detail)


def validate_doctype(doctype: str) -> str:
    """Reject a missing DocType locally, with a useful argument name."""
    if not doctype.strip():
        raise ValueError("Input 'doctype' must be a non-empty exact Frappe DocType name.")
    return doctype.strip()


def validate_filters(filters: list[Any] | None) -> None:
    """Validate Frappe's 3- or 4-part filter format before making a request."""
    if filters is None:
        return
    if not isinstance(filters, list):
        raise ValueError("Input 'filters' must be a list of 3- or 4-item filter lists.")
    for index, item in enumerate(filters):
        if not isinstance(item, list) or len(item) not in (3, 4):
            raise ValueError(
                f"Input 'filters[{index}]' must be [field, operator, value] or "
                "[doctype, field, operator, value]."
            )
        if any(not isinstance(part, str) or not part.strip() for part in item[:-1]):
            raise ValueError(
                f"Input 'filters[{index}]' has an invalid field, DocType, or operator; "
                "these entries must be non-empty strings."
            )


def _response_detail(response: httpx.Response) -> str:
    """Extract a short, useful Frappe error without returning a traceback."""
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        messages = body.get("_server_messages")
        if isinstance(messages, str):
            try:
                messages = json.loads(messages)
            except ValueError:
                pass
        if isinstance(messages, list):
            for message in messages:
                if isinstance(message, str):
                    try:
                        parsed = json.loads(message)
                    except ValueError:
                        parsed = message
                    if isinstance(parsed, dict):
                        parsed = parsed.get("message") or parsed.get("title")
                    if isinstance(parsed, str) and parsed.strip():
                        return " ".join(parsed.split())[:400]
        # Frappe often sets ``exc_type`` to the generic name "ValidationError"
        # while the actionable field-level reason is in ``_server_messages``.
        # Prefer useful response details over that generic exception label.
        for key in ("_error_message", "message", "exception", "exc_type"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                # ``exception`` may contain a full traceback; only expose its first line.
                return " ".join(value.splitlines()[0].split())[:400]
    return " ".join(response.text.split())[:400]


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


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    redact_response: bool = True,
) -> Any:
    base, auth = await connection()
    try:
        async with httpx.AsyncClient(timeout=settings.FRAPPE_TIMEOUT_SECONDS) as client:
            headers = {"Authorization": auth, "Accept": "application/json"}
            if json_body is not None:
                headers["Content-Type"] = "application/json"
            response = await client.request(
                method,
                f"{base}{path}",
                params=params,
                json=json_body,
                headers=headers,
            )
    except httpx.TimeoutException as error:
        if method.upper() == "POST":
            raise FrappeRequestError(
                None,
                "The Frappe create request timed out; the outcome is unknown. Check whether the "
                "record was created before retrying, to avoid creating a duplicate.",
            ) from error
        raise FrappeRequestError(
            None,
            f"Frappe request timed out after {settings.FRAPPE_TIMEOUT_SECONDS:g}s. "
            "Retry, or verify the Frappe site URL if the timeout persists.",
        ) from error
    except httpx.ConnectError as error:
        raise FrappeRequestError(
            None,
            "Could not connect to the configured Frappe site. Verify the saved base URL "
            "and that the site is reachable, then retry.",
        ) from error
    except httpx.RequestError as error:
        raise FrappeRequestError(
            None,
            f"Frappe request failed ({type(error).__name__}). Verify the site connection and retry.",
        ) from error

    status = response.status_code
    detail = _response_detail(response)
    if status == 401:
        raise PermissionError(
            "Frappe authentication failed (401). Check the saved API key and API secret, "
            "then retry."
        )
    if status == 403:
        raise PermissionError(
            "Frappe denied this request (403). The API-key user may lack the required read or "
            "write permission for this DocType or one of its fields; check Frappe roles and permissions."
        )
    if status == 404:
        raise FrappeRequestError(
            status,
            f"Frappe could not find the requested DocType, record, or method (404). "
            f"Check the exact DocType and record name. {detail}",
        )
    if status == 417:
        if method.upper() == "POST":
            raise FrappeRequestError(
                status,
                f"Frappe rejected the create request (417); this record was not created. "
                f"Frappe validation detail: {detail} Correct the indicated field(s) or linked "
                "records in the form, then retry.",
            )
        raise FrappeRequestError(
            status,
            f"Frappe rejected the request (417). Check the DocType, field names, supplied field "
            f"values, and filters; if this is a permissions issue, check the API-key user's access. {detail}",
        )
    if status == 429:
        raise FrappeRequestError(
            status,
            "Frappe rate-limited this request (429). Wait briefly, then retry with a smaller "
            "limit or fewer requests.",
        )
    if status >= 500:
        retry_hint = (
            " Check whether the record was created before retrying, to avoid a duplicate."
            if method.upper() == "POST"
            else " Retry shortly."
        )
        raise FrappeRequestError(
            status,
            f"Frappe returned a server error ({status}).{retry_hint} If it persists, "
            f"check Frappe server health. {detail}",
        )
    if status >= 400:
        raise FrappeRequestError(
            status,
            f"Frappe rejected the request ({status}). Check the tool inputs, DocType, and "
            f"permissions. {detail}",
        )
    try:
        body = response.json()
    except ValueError as error:
        raise FrappeRequestError(
            status,
            "Frappe returned a successful status but the response was not valid JSON. "
            "Retry, and check the site/API response if it persists.",
        ) from error
    result = body.get("data", body.get("message", body))
    return redact(result) if redact_response else result


async def get(path: str, params: dict[str, Any] | None = None) -> Any:
    return await _request("GET", path, params=params)


async def get_for_update(path: str) -> Any:
    """Read an unredacted record for an internal read/modify/write operation.

    The value must only be used to preserve existing fields while constructing
    a write; callers should return the normal redacted response from the save.
    """
    return await _request("GET", path, redact_response=False)


async def put(path: str, json_body: dict[str, Any]) -> Any:
    """Update a Frappe document using its normal REST save/validation path."""
    return await _request("PUT", path, json_body=json_body)


async def post(path: str, json_body: dict[str, Any]) -> Any:
    """Create a Frappe document through its standard REST insert path."""
    return await _request("POST", path, json_body=json_body)
