"""Safely update one Frappe document through the standard REST API."""

from typing import Any

from fastmcp.tools import ToolResult

from app.tools.frappe_common import (
    chat_data,
    doctype_schema,
    get_for_update,
    path_part,
    put,
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
    "Table MultiSelect",
}


def _is_enabled(value: Any) -> bool:
    return value is True or value == 1 or value == "1"


def _editable_fields(schema: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], set[str]]:
    """Return visible fields and the subset marked read-only/virtual."""
    raw_fields = schema.get("fields", [])
    if not isinstance(raw_fields, list):
        raw_fields = []
    fields = {
        field["fieldname"]: field
        for field in raw_fields
        if isinstance(field, dict)
        and field.get("fieldname")
        and not field.get("hidden")
        and field["fieldname"] not in _SYSTEM_FIELDS
        and not field["fieldname"].startswith("_")
        and field.get("fieldtype") not in _NON_WRITABLE_TYPES
    }
    read_only = {
        name
        for name, field in fields.items()
        if _is_enabled(field.get("read_only")) or _is_enabled(field.get("is_virtual"))
    }
    return fields, read_only


def _validate_append_rows(
    fieldname: str,
    rows: Any,
    child_schema: dict[str, Any],
) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError(
            f"Input 'child_table_changes' for {fieldname!r} must include a non-empty list of row objects."
        )
    child_fields, read_only = _editable_fields(child_schema)
    child_fields = {
        name: field for name, field in child_fields.items() if field.get("fieldtype") != "Table"
    }
    validated = []
    for index, row in enumerate(rows):
        unknown = sorted(set(row) - set(child_fields))
        forbidden = sorted(set(row) & read_only)
        if forbidden:
            raise ValueError(
                f"Input 'child_table_changes' row {index} for {fieldname!r} contains "
                f"read-only or virtual child field(s): {', '.join(forbidden)}."
            )
        if unknown:
            raise ValueError(
                f"Input 'child_table_changes' row {index} for {fieldname!r} contains "
                f"unknown, hidden, or unsupported child field(s): {', '.join(unknown)}."
            )
        missing = [
            name
            for name, field in child_fields.items()
            if _is_enabled(field.get("reqd")) and (row.get(name) is None or row.get(name) == "")
        ]
        if missing:
            labels = [child_fields[name].get("label") or name for name in missing]
            raise ValueError(
                f"Input 'child_table_changes' row {index} for {fieldname!r} is missing "
                f"required child field(s): {', '.join(labels)} ({', '.join(missing)})."
            )
        validated.append(row)
    return validated


def register_tool(mcp) -> None:
    @mcp.tool()
    async def frappe_update(
        doctype: str,
        name: str,
        values: dict[str, Any] | None = None,
        child_table_changes: list[dict[str, Any]] | None = None,
    ) -> ToolResult:
        """Update explicitly specified fields on one existing Frappe record.

        First confirm the exact DocType with frappe_doctypes and use an exact
        record name from prior results (or find it with frappe_search). Only
        include fields the user asked to change; values are partial updates.
        To add a row to a child table, use child_table_changes with
        {fieldname, operation: "append", rows: [...]}. The table and child-row
        fields are validated from their DocType schemas. Existing rows are
        preserved. Do not pass a child table in values or replace its contents.
        Do not infer updates or clear a field with null unless the user clearly
        asked to clear it. Use frappe_schema when field names are uncertain.
        Hidden, read-only, virtual, and system fields are rejected. To add rows
        to a child table, use child_table_changes with an append operation;
        existing child rows are preserved. Do not replace the table contents.
        Appending uses a read/modify/write sequence, so avoid concurrent edits
        to the same document while it runs.
        Frappe enforces its own write permissions, field validations, workflows,
        and document hooks. This tool returns a confirmation and updated record
        data but does not open a canvas view.
        """
        doctype = validate_doctype(doctype)
        if not name.strip():
            raise ValueError("Input 'name' must be the exact, non-empty Frappe record name.")
        if values is None:
            values = {}
        if not isinstance(values, dict):
            raise ValueError("Input 'values' must be an object of fields to update.")
        if child_table_changes is not None and not isinstance(child_table_changes, list):
            raise ValueError("Input 'child_table_changes' must be a list of append operations.")
        if not values and not child_table_changes:
            raise ValueError(
                "Input 'values' must be a non-empty object unless 'child_table_changes' is provided."
            )
        invalid_keys = [key for key in values if not isinstance(key, str) or not key.strip()]
        if invalid_keys:
            raise ValueError("Every key in input 'values' must be a non-empty field name.")

        schema = await doctype_schema(doctype)
        fields, read_only = _editable_fields(schema)
        requested = set(values)
        forbidden = sorted(requested & read_only)
        scalar_fields = {name for name, field in fields.items() if field.get("fieldtype") != "Table"}
        unknown = sorted(requested - scalar_fields - read_only)
        direct_tables = sorted(
            name for name in requested if fields.get(name, {}).get("fieldtype") == "Table"
        )
        if direct_tables:
            raise ValueError(
                f"Input 'values' cannot replace child table field(s) {', '.join(direct_tables)}. "
                "Use 'child_table_changes' with operation 'append' to preserve existing rows."
            )
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

        update_values = dict(values)
        appended_by_field: dict[str, list[dict[str, Any]]] = {}
        for index, change in enumerate(child_table_changes or []):
            if not isinstance(change, dict):
                raise ValueError(f"Input 'child_table_changes[{index}]' must be an object.")
            unexpected = sorted(set(change) - {"fieldname", "operation", "rows"})
            if unexpected:
                raise ValueError(
                    f"Input 'child_table_changes[{index}]' has unsupported key(s): "
                    f"{', '.join(unexpected)}."
                )
            fieldname = change.get("fieldname")
            if not isinstance(fieldname, str) or not fieldname.strip():
                raise ValueError(f"Input 'child_table_changes[{index}].fieldname' must be a non-empty string.")
            if change.get("operation") != "append":
                raise ValueError(
                    f"Input 'child_table_changes[{index}].operation' must be 'append'."
                )
            table_field = fields.get(fieldname)
            if not table_field or table_field.get("fieldtype") != "Table":
                raise ValueError(
                    f"Input 'child_table_changes[{index}].fieldname' {fieldname!r} is not an "
                    f"editable child table on {doctype}."
                )
            child_doctype = table_field.get("options")
            if not isinstance(child_doctype, str) or not child_doctype.strip():
                raise ValueError(f"Frappe metadata for table field {fieldname!r} has no child DocType.")
            child_schema = await doctype_schema(child_doctype)
            appended_by_field.setdefault(fieldname, []).extend(
                _validate_append_rows(fieldname, change.get("rows"), child_schema)
            )

        endpoint = f"/api/resource/{path_part(doctype)}/{path_part(name)}"
        if appended_by_field:
            current = await get_for_update(endpoint)
            if not isinstance(current, dict) or current.get("name") != name:
                raise ValueError(f"Could not read {doctype} {name} to safely append child rows.")
            for fieldname, new_rows in appended_by_field.items():
                existing_rows = current.get(fieldname, [])
                if not isinstance(existing_rows, list) or any(not isinstance(row, dict) for row in existing_rows):
                    raise ValueError(
                        f"Frappe returned an invalid child table '{fieldname}' for {doctype} {name}."
                    )
                update_values[fieldname] = [*existing_rows, *new_rows]

        result = await put(endpoint, update_values)
        if not isinstance(result, dict):
            raise ValueError(f"Frappe returned an invalid update response for {doctype} {name}.")
        updated_fields = list(update_values)
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
