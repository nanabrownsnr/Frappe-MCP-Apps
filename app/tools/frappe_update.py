"""Safely update one Frappe document through the standard REST API."""

from typing import Any

from fastmcp.tools import ToolResult

from app.tools.frappe_common import (
    chat_data,
    doctype_schema,
    path_part,
    put,
    schema_fields,
    validate_doctype,
)

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
_NON_WRITABLE_TYPES = {
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


def _is_enabled(value: Any) -> bool:
    return value is True or value == 1 or value == "1"


def _editable_fields(schema: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], set[str]]:
    """Return visible scalar fields and the subset marked read-only/virtual."""
    fields = {
        field["fieldname"]: field
        for field in schema_fields(schema)
        if field["fieldname"] not in _SYSTEM_FIELDS
        and not field["fieldname"].startswith("_")
        and field.get("fieldtype") not in _NON_WRITABLE_TYPES
    }
    read_only = {
        name
        for name, field in fields.items()
        if _is_enabled(field.get("read_only")) or _is_enabled(field.get("is_virtual"))
    }
    return fields, read_only


def register_tool(mcp) -> None:
    @mcp.tool()
    async def frappe_update(doctype: str, name: str, values: dict[str, Any]) -> ToolResult:
        """Update explicitly specified fields on one existing Frappe record.

        First confirm the exact DocType with frappe_doctypes and use an exact
        record name from prior results (or find it with frappe_search). Only
        include fields the user asked to change; values are partial updates.
        Do not infer updates or clear a field with null unless the user clearly
        asked to clear it. Use frappe_schema when field names are uncertain.
        Hidden, read-only, virtual, system, and child-table fields are rejected.
        Frappe enforces its own write permissions, field validations, workflows,
        and document hooks. This tool returns a confirmation and updated record
        data but does not open a canvas view.
        """
        doctype = validate_doctype(doctype)
        if not name.strip():
            raise ValueError("Input 'name' must be the exact, non-empty Frappe record name.")
        if not isinstance(values, dict) or not values:
            raise ValueError("Input 'values' must be a non-empty object of fields to update.")
        invalid_keys = [key for key in values if not isinstance(key, str) or not key.strip()]
        if invalid_keys:
            raise ValueError("Every key in input 'values' must be a non-empty field name.")

        schema = await doctype_schema(doctype)
        fields, read_only = _editable_fields(schema)
        requested = set(values)
        forbidden = sorted(requested & read_only)
        unknown = sorted(requested - set(fields) - read_only)
        if forbidden:
            raise ValueError(
                f"Input 'values' contains read-only or virtual field(s) for {doctype}: "
                f"{', '.join(forbidden)}. Choose editable fields from the DocType schema."
            )
        if unknown:
            raise ValueError(
                f"Input 'values' contains unknown, hidden, or unsupported field(s) for "
                f"{doctype}: {', '.join(unknown)}. Use frappe_schema to check available fields."
            )

        result = await put(
            f"/api/resource/{path_part(doctype)}/{path_part(name)}",
            values,
        )
        if not isinstance(result, dict):
            raise ValueError(f"Frappe returned an invalid update response for {doctype} {name}.")
        updated_fields = list(values)
        return ToolResult(
            content=chat_data(
                f"Updated {doctype} {name}. Fields changed: {', '.join(updated_fields)}.",
                result,
            ),
            structured_content={
                "doctype": doctype,
                "name": result.get("name", name),
                "updated_fields": updated_fields,
                "record": result,
            },
        )
