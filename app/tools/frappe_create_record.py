"""Commit a user-confirmed Frappe create form as a new document."""

from typing import Any

from fastmcp.apps import AppConfig
from fastmcp.tools import ToolResult

from app.tools.frappe_common import (
    chat_data,
    doctype_schema,
    path_part,
    post,
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
    "Table MultiSelect",
}


def _enabled(value: Any) -> bool:
    return value is True or value == 1 or value == "1"


def _createable_fields(
    schema: dict[str, Any], *, allow_tables: bool = True
) -> dict[str, dict[str, Any]]:
    raw_fields = schema.get("fields", [])
    if not isinstance(raw_fields, list):
        return {}
    return {
        field["fieldname"]: field
        for field in raw_fields
        if isinstance(field, dict)
        and field.get("fieldname")
        and not field.get("hidden")
        and field["fieldname"] not in _SYSTEM_FIELDS
        and not field["fieldname"].startswith("_")
        and field.get("fieldtype") not in _UNSUPPORTED_TYPES
        and (allow_tables or field.get("fieldtype") != "Table")
        and not _enabled(field.get("read_only"))
        and not _enabled(field.get("is_virtual"))
    }


async def _validate_values(
    values: dict[str, Any],
    fields: dict[str, dict[str, Any]],
    doctype: str,
    path: str = "Input 'values'",
) -> None:
    unknown = sorted(set(values) - set(fields))
    if unknown:
        raise ValueError(
            f"{path} contains unknown, hidden, read-only, or unsupported field(s) for "
            f"{doctype}: {', '.join(unknown)}. Reopen the create form to refresh its schema."
        )

    missing = [
        fieldname
        for fieldname, field in fields.items()
        if _enabled(field.get("reqd"))
        and (
            values.get(fieldname) is None
            or values.get(fieldname) == ""
            or (field.get("fieldtype") == "Table" and not values.get(fieldname))
        )
    ]
    if missing:
        labels = [fields[fieldname].get("label") or fieldname for fieldname in missing]
        raise ValueError(
            f"{path} is missing required field(s): {', '.join(labels)} "
            f"({', '.join(missing)}). Fill them in the create form."
        )

    for fieldname, field in fields.items():
        if field.get("fieldtype") != "Table" or fieldname not in values:
            continue
        rows = values[fieldname]
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError(f"{path}.{fieldname} must be a list of child-row objects.")
        if not rows:
            continue
        child_doctype = field.get("options")
        if not isinstance(child_doctype, str) or not child_doctype.strip():
            raise ValueError(f"Frappe metadata for table field {fieldname!r} has no child DocType.")
        child_schema = await doctype_schema(child_doctype)
        child_fields = _createable_fields(child_schema, allow_tables=False)
        for row_index, row in enumerate(rows):
            await _validate_values(
                row,
                child_fields,
                child_doctype,
                f"{path}.{fieldname}[{row_index}]",
            )


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
        allowed = _createable_fields(schema)
        await _validate_values(values, allowed, doctype)

        created = await post(f"/api/resource/{path_part(doctype)}", values)
        if not isinstance(created, dict) or not created.get("name"):
            raise ValueError(f"Frappe returned an invalid create response for {doctype}.")
        return ToolResult(
            content=chat_data(f"Created {doctype} {created['name']}.", created),
            structured_content={"mode": "created_record", "doctype": doctype, "record": created},
        )
