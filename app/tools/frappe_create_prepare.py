"""Prepare a schema-driven, editable Frappe creation form without writing."""

from typing import Any

from fastmcp.apps import AppConfig
from fastmcp.tools import ToolResult

from app.tools.frappe_common import doctype_schema, validate_doctype
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


async def _form_fields(
    schema: dict[str, Any], *, allow_tables: bool = True
) -> list[dict[str, Any]]:
    fields = []
    raw_fields = schema.get("fields", [])
    if not isinstance(raw_fields, list):
        return fields
    for field in raw_fields:
        if not isinstance(field, dict) or not field.get("fieldname") or field.get("hidden"):
            continue
        fieldname = field["fieldname"]
        fieldtype = field.get("fieldtype") or "Data"
        if fieldtype == "Table" and not allow_tables:
            continue
        if (
            fieldname in _SYSTEM_FIELDS
            or fieldname.startswith("_")
            or fieldtype in _UNSUPPORTED_TYPES
            or _enabled(field.get("read_only"))
            or _enabled(field.get("is_virtual"))
        ):
            continue
        metadata = {
                "fieldname": fieldname,
                "label": field.get("label") or fieldname,
                "fieldtype": fieldtype,
                "options": field.get("options"),
                "reqd": _enabled(field.get("reqd")),
                "default": field.get("default"),
                "description": field.get("description"),
                "depends_on": field.get("depends_on"),
                "mandatory_depends_on": field.get("mandatory_depends_on"),
                "precision": field.get("precision"),
            }
        if fieldtype == "Table":
            child_doctype = field.get("options")
            if not isinstance(child_doctype, str) or not child_doctype.strip():
                raise ValueError(
                    f"Frappe metadata for table field {fieldname!r} has no child DocType."
                )
            child_schema = await doctype_schema(child_doctype)
            metadata["child_doctype"] = child_doctype
            metadata["child_fields"] = await _form_fields(child_schema, allow_tables=False)
        fields.append(metadata)
    return fields


def _missing_required(fields: list[dict[str, Any]], values: dict[str, Any]) -> list[dict[str, str]]:
    missing = []
    for field in fields:
        value = values.get(field["fieldname"])
        if field["reqd"] and (
            value is None or value == "" or (field["fieldtype"] == "Table" and not value)
        ):
            missing.append(
                {
                    "fieldname": field["fieldname"],
                    "label": field["label"],
                }
            )
        if field["fieldtype"] == "Table" and isinstance(value, list):
            for row_index, row in enumerate(value):
                if not isinstance(row, dict):
                    continue
                for missing_child in _missing_required(field.get("child_fields", []), row):
                    missing.append(
                        {
                            "fieldname": f"{field['fieldname']}[{row_index}].{missing_child['fieldname']}",
                            "label": f"{field['label']} row {row_index + 1}: {missing_child['label']}",
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
        record, for example "create a new lead" or "add a contact". First call
        frappe_doctypes to find the exact DocType that matches the request. If
        multiple DocTypes could fit (for example CRM Lead and Lead), ask which
        one they mean; do not guess. Pass values the user supplied or that are
        unambiguous from context. This tool reads merged DocType metadata and
        opens an editable form in the app UI, including row editors for child
        tables. Child-table values, when supplied, are lists of row objects.
        It does not save anything. The
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
        fields = await _form_fields(schema)
        fields_by_name = {field["fieldname"]: field for field in fields}
        unknown = sorted(set(values) - set(fields_by_name))
        if unknown:
            raise ValueError(
                f"Input 'values' contains unknown, hidden, read-only, or unsupported field(s) "
                f"for {doctype}: {', '.join(unknown)}. Use frappe_schema to check available fields."
            )

        proposed_values = {
            field["fieldname"]: ([] if field["fieldtype"] == "Table" else field["default"])
            for field in fields
            if field["fieldtype"] == "Table" or field["default"] is not None
        }
        proposed_values.update(values)
        for field in fields:
            if field["fieldtype"] != "Table" or field["fieldname"] not in proposed_values:
                continue
            rows = proposed_values[field["fieldname"]]
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise ValueError(
                    f"Input 'values.{field['fieldname']}' must be a list of child-row objects."
                )
            rows = [
                {
                    **{
                        child["fieldname"]: child["default"]
                        for child in field["child_fields"]
                        if child["default"] is not None
                    },
                    **row,
                }
                for row in rows
            ]
            proposed_values[field["fieldname"]] = rows
            allowed_child_fields = {child["fieldname"] for child in field["child_fields"]}
            for row_index, row in enumerate(rows):
                unknown_child_fields = sorted(set(row) - allowed_child_fields)
                if unknown_child_fields:
                    raise ValueError(
                        f"Input 'values.{field['fieldname']}[{row_index}]' contains unknown, "
                        f"hidden, read-only, or unsupported child field(s): "
                        f"{', '.join(unknown_child_fields)}."
                    )
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
