"""Frappe list tool."""

import json
from typing import Any

from fastmcp.apps import AppConfig
from fastmcp.tools import ToolResult

from app.config import settings
from app.tools.frappe_common import (
    FrappeRequestError,
    chat_record_index,
    default_list_fields,
    doctype_schema,
    get,
    path_part,
    schema_fields,
    validate_doctype,
    validate_filters,
)
from app.ui.frappe_ui.resource import VIEW_URI

_CRM_DEAL_PIPELINE_FIELDS = (
    "status",
    "organization",
    "lead_name",
    "deal_value",
    "currency",
    "custom_service_line",
    "probability",
)
_CRM_DEAL_CLOSED_STATUSES = {"Won", "Lost"}


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
        `fields` for the default behavior: the tool loads DocType metadata and
        returns at most ten fields total, always including `name`. The
        original five-field metadata selection order is preserved; the five
        extra slots prioritize Currency fields and their companion currency
        fields, then custom fields before other scalar fields. For the default
        `CRM Deal` pipeline result, the projection specifically includes
        status, organization, lead name, deal value, currency, service line,
        and probability; each record also includes `id` (the Frappe `name`)
        and derived `heat`. Other DocTypes use the generic metadata projection.
        If `fields` is
        supplied, the result contains `name` plus exactly those fields (up to
        Frappe's response limits), without adding automatic preview fields.
        If Frappe rejects explicitly requested fields, report that error rather
        than silently changing the requested projection. For the automatic
        generic automatic projection only, a 417 response causes
        lower-priority preview fields to be dropped one at a time, with
        `name` retained. The CRM Deal pipeline projection is kept intact and
        reports upstream errors rather than dropping required pipeline data.
        The tool returns the records in the chat result and matching UI
        column metadata for the canvas. Do not call it again just to fetch
        fields when this call already returned records.
        """
        doctype = validate_doctype(doctype)
        validate_filters(filters)
        schema = await doctype_schema(doctype)
        metadata = schema_fields(schema)
        valid_names = {field["fieldname"] for field in metadata}
        if fields is not None:
            unknown_fields = [name for name in fields if name not in valid_names]
            if unknown_fields:
                raise ValueError(f"Unknown fields for {doctype}: {', '.join(unknown_fields)}")
        explicit_fields = bool(fields)
        if explicit_fields:
            selected_names = list(dict.fromkeys(["name", *fields]))
        elif doctype == "CRM Deal":
            missing_pipeline_fields = [
                fieldname
                for fieldname in _CRM_DEAL_PIPELINE_FIELDS
                if fieldname not in valid_names
            ]
            if missing_pipeline_fields:
                raise ValueError(
                    "CRM Deal schema is missing pipeline field(s): "
                    f"{', '.join(missing_pipeline_fields)}. Check the DocType schema."
                )
            selected_names = ["name", *_CRM_DEAL_PIPELINE_FIELDS]
        else:
            selected_names = default_list_fields(schema, metadata, limit=10)
        params: dict[str, Any] = {
            "fields": json.dumps(selected_names),
            "limit_page_length": max(1, min(limit, settings.FRAPPE_MAX_LIMIT)),
            "limit_start": max(0, start),
        }
        if filters:
            params["filters"] = json.dumps(filters)
        if order_by:
            params["order_by"] = order_by
        while True:
            try:
                result = await get(f"/api/resource/{path_part(doctype)}", params)
                break
            except FrappeRequestError as error:
                if (
                    error.status_code != 417
                    or explicit_fields
                    or doctype == "CRM Deal"
                    or selected_names == ["name"]
                ):
                    raise
                selected_names = selected_names[:-1]
                params["fields"] = json.dumps(selected_names)
        if not isinstance(result, list) or any(not isinstance(record, dict) for record in result):
            raise ValueError(f"Frappe returned an invalid record list for {doctype}.")
        records = result
        if doctype == "CRM Deal" and not explicit_fields:
            records = [
                {
                    **record,
                    "id": record.get("name"),
                    "heat": int(
                        record.get("status") not in _CRM_DEAL_CLOSED_STATUSES
                        and isinstance(record.get("probability"), (int, float))
                        and record["probability"] >= 50
                    ),
                }
                for record in records
            ]
        if not records:
            return ToolResult(content=f"Found 0 {doctype} records.")
        response_fields = set(records[0])
        metadata_by_name = {field["fieldname"]: field for field in metadata}
        columns = [
            {
                "label": metadata_by_name[fieldname].get("label") or fieldname,
                "key": fieldname,
                "type": metadata_by_name[fieldname].get("fieldtype", "Data"),
                "options": metadata_by_name[fieldname].get("options"),
            }
            for fieldname in selected_names
            if fieldname in metadata_by_name and fieldname in response_fields
        ]
        return ToolResult(
            content=chat_record_index(doctype, records, schema, metadata, canvas=True),
            structured_content={"doctype": doctype, "records": records, "columns": columns},
            meta={"ui": {"resourceUri": VIEW_URI}},
        )
