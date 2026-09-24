"""Commit a user-confirmed Frappe create form as a new document."""

from typing import Any

from fastmcp.apps import AppConfig
from fastmcp.tools import ToolResult

from app.tools.frappe_common import (
    chat_data,
    doctype_schema,
    path_part,
    post,
    schema_fields,
    validate_doctype,
)
from app.ui.frappe_ui.resource import VIEW_URI

_SYSTEM_FIELDS = {
    "name",
    "doctype",
    "owner",
    "creation",
    "modified",
    "modified_by",
    "docstatus",
    "idx",
    "_user_tags",
    "_comments",
    "_assign",
    "_liked_by",
}
_UNSUPPORTED_TYPES = {
    "Button",
    "Column Break",
    "Fold",
    "Heading",
    "HTML",
    "Image",
    "Password",
    "Read Only",
    "Section Break",
    "Tab Break",
    "Table",
    "Table MultiSelect",
}


def _enabled(value: Any) -> bool:
    return value is True or value == 1 or value == "1"


def _createable_fields(schema: dict[str, Any]) -> tuple[set[str], dict[str, str]]:
    fields = schema_fields(schema)
    editable = {
        field["fieldname"]
        for field in fields
        if field["fieldname"] not in _SYSTEM_FIELDS
        and not field["fieldname"].startswith("_")
        and field.get("fieldtype") not in _UNSUPPORTED_TYPES
        and not _enabled(field.get("read_only"))
        and not _enabled(field.get("is_virtual"))
    }
    required = {
        field["fieldname"]: field.get("label") or field["fieldname"]
        for field in fields
        if field["fieldname"] in editable and _enabled(field.get("reqd"))
    }
    return editable, required


def register_tool(mcp) -> None:
    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI, visibility=["app"]))
    async def frappe_create_record(doctype: str, values: dict[str, Any]) -> ToolResult:
        """Create a Frappe record after explicit confirmation in the UI.

        This app-only tool is called by the Create button after the user has
        reviewed the editable form. It performs one insert and returns the
        created record for the UI's read-only detail view. It is not the
        Frappe docstatus Submit action. Never invoke it directly on the user's
        behalf; the user must click Create. Server-side Frappe permissions,
        validation, workflows, and document hooks remain authoritative.
        """
        doctype = validate_doctype(doctype)
        if not isinstance(values, dict) or not values:
            raise ValueError("Input 'values' must be a non-empty object of fields to create.")
        invalid_keys = [key for key in values if not isinstance(key, str) or not key.strip()]
        if invalid_keys:
            raise ValueError("Every key in input 'values' must be a non-empty field name.")

        schema = await doctype_schema(doctype)
        allowed, required = _createable_fields(schema)
        unknown = sorted(set(values) - allowed)
        if unknown:
            raise ValueError(
                f"Input 'values' contains unknown, hidden, read-only, or unsupported field(s) "
                f"for {doctype}: {', '.join(unknown)}. Reopen the create form to refresh its schema."
            )
        missing = sorted(name for name in required if values.get(name) is None or values.get(name) == "")
        if missing:
            missing_labels = [required[name] for name in missing]
            raise ValueError(
                "Input 'values' is missing required field(s): "
                f"{', '.join(missing_labels)} ({', '.join(missing)}). Fill them in the create form."
            )

        created = await post(f"/api/resource/{path_part(doctype)}", values)
        if not isinstance(created, dict) or not created.get("name"):
            raise ValueError(f"Frappe returned an invalid create response for {doctype}.")
        return ToolResult(
            content=chat_data(f"Created {doctype} {created['name']}.", created),
            structured_content={"mode": "created_record", "doctype": doctype, "record": created},
        )
