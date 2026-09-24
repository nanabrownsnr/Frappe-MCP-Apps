"""Prepare a schema-driven, editable Frappe creation form without writing."""

from typing import Any

from fastmcp.apps import AppConfig
from fastmcp.tools import ToolResult

from app.tools.frappe_common import doctype_schema, schema_fields, validate_doctype
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


def _form_fields(schema: dict[str, Any]) -> list[dict[str, Any]]:
    fields = []
    for field in schema_fields(schema):
        fieldname = field["fieldname"]
        if (
            fieldname in _SYSTEM_FIELDS
            or fieldname.startswith("_")
            or field.get("fieldtype") in _UNSUPPORTED_TYPES
            or _enabled(field.get("read_only"))
            or _enabled(field.get("is_virtual"))
        ):
            continue
        fields.append(
            {
                "fieldname": fieldname,
                "label": field.get("label") or fieldname,
                "fieldtype": field.get("fieldtype") or "Data",
                "options": field.get("options"),
                "reqd": _enabled(field.get("reqd")),
                "default": field.get("default"),
                "description": field.get("description"),
                "depends_on": field.get("depends_on"),
                "mandatory_depends_on": field.get("mandatory_depends_on"),
                "precision": field.get("precision"),
            }
        )
    return fields


def _missing_required(fields: list[dict[str, Any]], values: dict[str, Any]) -> list[dict[str, str]]:
    missing = []
    for field in fields:
        value = values.get(field["fieldname"])
        if field["reqd"] and (value is None or value == ""):
            missing.append(
                {
                    "fieldname": field["fieldname"],
                    "label": field["label"],
                }
            )
    return missing


def register_tool(mcp) -> None:
    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI, visibility=["model", "app"]))
    async def frappe_create_prepare(
        doctype: str,
        values: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Prepare a user-reviewed Frappe create form; this tool never writes.

        Use this whenever the user asks to create, add, or make a new Frappe
        record, for example “create a new lead” or “add a contact”. First call
        frappe_doctypes to find the exact DocType that matches the request. If
        multiple DocTypes could fit (for example CRM Lead and Lead), ask which
        one they mean; do not guess. Pass values the user supplied or that are
        unambiguous from context. This tool reads merged DocType metadata and
        opens an editable form in the app UI; it does not save anything. The
        user reviews/edits the form and confirms by pressing Create. Never call
        the app-only frappe_create_record tool yourself; only that explicit UI
        action may invoke it. Frappe remains authoritative for conditional and
        server-side validation.
        """
        doctype = validate_doctype(doctype)
        if values is not None and not isinstance(values, dict):
            raise ValueError("Input 'values' must be an object mapping field names to values.")
        values = values or {}
        invalid_keys = [key for key in values if not isinstance(key, str) or not key.strip()]
        if invalid_keys:
            raise ValueError("Every key in input 'values' must be a non-empty field name.")

        schema = await doctype_schema(doctype)
        fields = _form_fields(schema)
        fields_by_name = {field["fieldname"]: field for field in fields}
        unknown = sorted(set(values) - set(fields_by_name))
        if unknown:
            raise ValueError(
                f"Input 'values' contains unknown, hidden, read-only, or unsupported field(s) "
                f"for {doctype}: {', '.join(unknown)}. Use frappe_schema to check available fields."
            )

        proposed_values = {
            field["fieldname"]: field["default"]
            for field in fields
            if field["default"] is not None
        }
        proposed_values.update(values)
        missing_required = _missing_required(fields, proposed_values)
        message = (
            f"Prepared a {doctype} form with {len(proposed_values)} prefilled field(s). "
            f"{len(missing_required)} required field(s) still need values. "
            "Review the form; nothing has been created yet."
        )
        return ToolResult(
            content=message,
            structured_content={
                "mode": "create_form",
                "doctype": doctype,
                "fields": fields,
                "values": proposed_values,
                "missing_required": missing_required,
            },
            meta={"ui": {"resourceUri": VIEW_URI}},
        )
