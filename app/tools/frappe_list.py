"""Frappe list tool."""

import json
from typing import Any

from fastmcp.apps import AppConfig
from fastmcp.tools import ToolResult

from app.config import settings
from app.tools.frappe_common import (
    FrappeRequestError,
    chat_data,
    doctype_schema,
    get,
    path_part,
    schema_fields,
)
from app.ui.frappe_ui.resource import VIEW_URI


def register_tool(mcp) -> None:
    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI, visibility=["model", "app"]))
    async def frappe_list(
        doctype: str,
        fields: list[str] | None = None,
        filters: list[Any] | None = None,
        order_by: str | None = None,
        limit: int = 20,
        start: int = 0,
    ) -> ToolResult:
        """List records from a Frappe DocType.

        First call frappe_doctypes to identify the exact DocType name. Omit
        `fields` for the default behavior: this tool loads the DocType schema
        and selects its available scalar fields automatically. Only provide
        `fields` when the user specifically asks for a limited field subset.
        The tool returns the records in the chat result and matching UI
        column metadata for the canvas. Do not call it again just to fetch
        fields when this call already returned records.
        """
        schema = await doctype_schema(doctype)
        metadata = schema_fields(schema)
        valid_names = {field["fieldname"] for field in metadata}
        if fields is not None:
            unknown_fields = [name for name in fields if name not in valid_names]
            if unknown_fields:
                raise ValueError(f"Unknown fields for {doctype}: {', '.join(unknown_fields)}")
        selected_names = list(dict.fromkeys(fields if fields else valid_names))
        if "name" not in selected_names:
            selected_names.insert(0, "name")
        params: dict[str, Any] = {
            "fields": json.dumps(selected_names),
            "limit_page_length": max(1, min(limit, settings.FRAPPE_MAX_LIMIT)),
            "limit_start": max(0, start),
        }
        if filters:
            params["filters"] = json.dumps(filters)
        if order_by:
            params["order_by"] = order_by
        try:
            result = await get(f"/api/resource/{path_part(doctype)}", params)
        except FrappeRequestError as error:
            if error.status_code != 417 or selected_names == ["name"]:
                raise
            params["fields"] = json.dumps(["name"])
            selected_names = ["name"]
            result = await get(f"/api/resource/{path_part(doctype)}", params)
        records = result if isinstance(result, list) else []
        if not records:
            return ToolResult(content=f"Found 0 {doctype} records.")
        response_fields = set(records[0])
        columns = [
            {"label": field.get("label") or field["fieldname"], "key": field["fieldname"], "type": field.get("fieldtype", "Data"), "options": field.get("options")}
            for field in metadata if field["fieldname"] in selected_names and field["fieldname"] in response_fields
        ]
        return ToolResult(
            content=chat_data(f"Found {len(records)} {doctype} records.", records, canvas=True),
            structured_content={"doctype": doctype, "records": records, "columns": columns},
            meta={"ui": {"resourceUri": VIEW_URI}},
        )
