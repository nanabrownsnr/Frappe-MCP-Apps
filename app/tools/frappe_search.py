"""Frappe search tool."""

import json

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


def register_tool(mcp) -> None:
    @mcp.tool()
    async def frappe_search(doctype: str, query: str = "", limit: int = 20) -> ToolResult:
        """Search records in a Frappe DocType by a text query.

        First call frappe_doctypes to map the user's wording to the exact
        DocType name. This tool loads the schema internally, searches the
        DocType's configured search fields (then global-search fields, then
        `name`), and selects display fields automatically. The agent does not
        need to call frappe_schema or provide a fields list first.
        """
        schema = await doctype_schema(doctype)
        metadata = schema_fields(schema)
        fields_by_name = {field["fieldname"]: field for field in metadata}
        configured = schema.get("search_fields", "")
        configured_names = [name.strip() for name in configured.split(",") if name.strip()] if isinstance(configured, str) else []
        searchable = [name for name in configured_names if name in fields_by_name]
        if not searchable:
            searchable = [name for name, field in fields_by_name.items() if field.get("in_global_search")]
        if not searchable:
            searchable = ["name"]
        if "name" in fields_by_name and "name" not in searchable:
            searchable.insert(0, "name")
        selected_names = list(fields_by_name)
        params = {
            "fields": json.dumps(selected_names),
            "limit_page_length": max(1, min(limit, settings.FRAPPE_MAX_LIMIT)),
            "order_by": "modified desc",
        }
        if query:
            params["or_filters"] = json.dumps([[name, "like", f"%{query}%"] for name in searchable])
        try:
            result = await get(f"/api/resource/{path_part(doctype)}", params)
        except FrappeRequestError as error:
            if error.status_code != 417 or not query or searchable == ["name"]:
                raise
            params["fields"] = json.dumps(["name"])
            params["or_filters"] = json.dumps([["name", "like", f"%{query}%"]])
            searchable = ["name"]
            result = await get(f"/api/resource/{path_part(doctype)}", params)
        records = result if isinstance(result, list) else []
        if not records:
            return ToolResult(content=f"Found 0 {doctype} records.")
        return ToolResult(
            content=chat_data(f"Found {len(records)} {doctype} records.", records),
            structured_content={
                "doctype": doctype,
                "records": records,
                "columns": [
                    {"label": field.get("label") or field["fieldname"], "key": field["fieldname"], "type": field.get("fieldtype", "Data"), "options": field.get("options")}
                    for field in metadata if field["fieldname"] in records[0]
                ],
            },
        )
