"""Contract tests for the Frappe tools; all upstream calls are mocked."""

import asyncio
import json

import httpx
import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ValidationError

from app.tools import (
    frappe_common,
    frappe_count,
    frappe_create_prepare,
    frappe_create_record,
    frappe_doctypes,
    frappe_get,
    frappe_job_overview,
    frappe_list,
    frappe_schema,
    frappe_search,
    frappe_update,
)
from app.tools.frappe_common import default_list_fields, schema_fields

SCHEMA = {
    "name": "CRM Deal",
    "title_field": "organization",
    "search_fields": "organization,custom_service_line",
    "fields": [
        {"fieldname": "organization", "label": "Organization", "fieldtype": "Data"},
        {
            "fieldname": "custom_service_line",
            "label": "Service Line",
            "fieldtype": "Select",
            "options": "Product\\nConsulting",
        },
        {"fieldname": "status", "label": "Status", "fieldtype": "Link", "options": "CRM Deal Status"},
        {"fieldname": "products", "label": "Products", "fieldtype": "Table"},
        {"fieldname": "internal_note", "label": "Internal note", "fieldtype": "Data", "hidden": 1},
    ],
}
RECORD = {
    "name": "CRM-DEAL-0001",
    "organization": "Acme",
    "custom_service_line": "Consulting",
    "status": "Discovery",
}


@pytest.fixture
def server():
    mcp = FastMCP("frappe-tool-tests")
    for module in (
        frappe_schema,
        frappe_doctypes,
        frappe_list,
        frappe_search,
        frappe_get,
        frappe_count,
        frappe_job_overview,
        frappe_update,
        frappe_create_prepare,
        frappe_create_record,
    ):
        module.register_tool(mcp)
    return mcp


async def invoke(server, name, arguments):
    tool = await server.get_tool(name)
    assert tool is not None
    return await tool.run(arguments)


def plain_value(result):
    structured = result.structured_content
    return structured.get("result", structured)


def text_of(result):
    return " ".join(getattr(item, "text", str(item)) for item in result.content)


@pytest.mark.asyncio
async def test_schema_includes_custom_fields_and_rejects_malformed_metadata(monkeypatch):
    async def merged_metadata(path, params=None):
        assert path == "/api/method/frappe.desk.form.load.getdoctype"
        assert params == {"doctype": "CRM Deal"}
        return {"docs": [{"name": "CRM Deal", "fields": [SCHEMA["fields"][1]]}]}

    monkeypatch.setattr(frappe_common, "get", merged_metadata)
    assert await frappe_common.doctype_schema("CRM Deal") == {
        "name": "CRM Deal",
        "fields": [SCHEMA["fields"][1]],
    }

    async def malformed(*args, **kwargs):
        return {"docs": [{"name": "Other DocType", "fields": []}]}

    monkeypatch.setattr(frappe_common, "get", malformed)
    with pytest.raises(ValueError, match="no metadata"):
        await frappe_common.doctype_schema("CRM Deal")

    async def invalid_shape(*args, **kwargs):
        return []

    monkeypatch.setattr(frappe_common, "get", invalid_shape)
    with pytest.raises(ValueError, match="invalid metadata"):
        await frappe_common.doctype_schema("CRM Deal")


@pytest.mark.asyncio
async def test_schema_tool_returns_metadata(server, monkeypatch):
    async def schema(doctype):
        assert doctype == "CRM Deal"
        return SCHEMA

    monkeypatch.setattr(frappe_schema, "doctype_schema", schema)
    result = await invoke(server, "frappe_schema", {"doctype": "CRM Deal"})
    assert plain_value(result)["fields"][1]["fieldname"] == "custom_service_line"


def test_default_list_fields_prioritize_frappe_metadata_and_exclude_unsafe_types():
    schema = {
        "title_field": "display_name",
        "search_fields": "search_label,display_name",
        "fields": [
            {"fieldname": "other", "fieldtype": "Data"},
            {"fieldname": "display_name", "fieldtype": "Data"},
            {"fieldname": "list_field", "fieldtype": "Link", "in_list_view": 1},
            {"fieldname": "search_label", "fieldtype": "Select"},
            {"fieldname": "global_field", "fieldtype": "Data", "in_global_search": 1},
            {"fieldname": "long_note", "fieldtype": "Long Text", "in_list_view": 1},
            {"fieldname": "password", "fieldtype": "Password", "in_list_view": 1},
            {"fieldname": "rows", "fieldtype": "Table", "in_list_view": 1},
            {"fieldname": "private_bank_account", "fieldtype": "Data", "in_list_view": 1},
        ],
    }

    selected = default_list_fields(schema, schema_fields(schema), limit=5)

    assert selected == ["name", "display_name", "list_field", "search_label", "global_field"]


def test_ten_field_preview_preserves_original_order_then_adds_currency_and_custom_fields():
    schema = {
        "title_field": "title",
        "search_fields": "search_label",
        "fields": [
            {"fieldname": "title", "fieldtype": "Data"},
            {"fieldname": "list_field", "fieldtype": "Link", "in_list_view": 1},
            {"fieldname": "search_label", "fieldtype": "Data"},
            {"fieldname": "ordinary_one", "fieldtype": "Data"},
            {"fieldname": "ordinary_two", "fieldtype": "Data"},
            {"fieldname": "expected_deal_value", "fieldtype": "Currency", "options": "currency"},
            {"fieldname": "deal_value", "fieldtype": "Currency", "options": "currency"},
            {"fieldname": "currency", "fieldtype": "Link", "options": "Currency"},
            {
                "fieldname": "custom_service_line",
                "fieldtype": "Select",
                "is_custom_field": 1,
            },
            {"fieldname": "remaining", "fieldtype": "Data"},
        ],
    }

    selected = default_list_fields(schema, schema_fields(schema), limit=10)

    assert selected[:5] == ["name", "title", "list_field", "search_label", "ordinary_one"]
    assert selected[5:] == [
        "expected_deal_value",
        "deal_value",
        "currency",
        "custom_service_line",
        "ordinary_two",
    ]


@pytest.mark.asyncio
async def test_doctypes_success_query_filters_and_limit(server, monkeypatch):
    async def upstream(path, params):
        assert path == "/api/resource/DocType"
        assert json.loads(params["filters"]) == [
            ["DocType", "istable", "=", 0],
            ["DocType", "name", "like", "%CRM%"],
        ]
        assert params["limit_page_length"] == 500
        return [{"name": "CRM Deal"}]

    monkeypatch.setattr(frappe_doctypes, "get", upstream)
    assert plain_value(await invoke(server, "frappe_doctypes", {"query": "CRM", "limit": 900})) == [
        {"name": "CRM Deal"}
    ]


@pytest.mark.asyncio
async def test_doctypes_bad_upstream_shape_and_bad_input(server, monkeypatch):
    async def upstream(*args, **kwargs):
        return {"unexpected": "shape"}

    monkeypatch.setattr(frappe_doctypes, "get", upstream)
    with pytest.raises(ValueError, match="invalid DocType list"):
        await invoke(server, "frappe_doctypes", {})
    with pytest.raises(ValidationError):
        await invoke(server, "frappe_doctypes", {"limit": "many"})


@pytest.mark.asyncio
async def test_list_default_selects_metadata_driven_fields(server, monkeypatch):
    async def schema(_doctype):
        return SCHEMA

    calls = []

    async def upstream(path, params):
        calls.append((path, params))
        return [RECORD]

    monkeypatch.setattr(frappe_list, "doctype_schema", schema)
    monkeypatch.setattr(frappe_list, "get", upstream)
    result = await invoke(server, "frappe_list", {"doctype": "CRM Deal"})
    requested = json.loads(calls[0][1]["fields"])
    assert requested == [
        "name",
        "organization",
        "custom_service_line",
        "status",
        "owner",
        "creation",
        "modified",
    ]
    assert len(requested) <= 10
    assert "internal_note" not in requested
    assert result.structured_content["records"] == [RECORD]
    assert [column["key"] for column in result.structured_content["columns"]] == [
        fieldname for fieldname in requested if fieldname in RECORD
    ]
    assert "CRM-DEAL-0001" in text_of(result)
    assert "canvas" in text_of(result)


@pytest.mark.asyncio
async def test_list_bad_field_empty_response_and_417_fallback(server, monkeypatch):
    async def schema(_doctype):
        return SCHEMA

    calls = []

    async def no_records(*args, **kwargs):
        return []

    monkeypatch.setattr(frappe_list, "doctype_schema", schema)
    monkeypatch.setattr(frappe_list, "get", no_records)
    assert "Found 0 CRM Deal" in text_of(
        await invoke(server, "frappe_list", {"doctype": "CRM Deal"})
    )
    with pytest.raises(ValueError, match="Unknown fields"):
        await invoke(server, "frappe_list", {"doctype": "CRM Deal", "fields": ["not_a_field"]})
    with pytest.raises(ValueError, match=r"filters\[0\]"):
        await invoke(server, "frappe_list", {"doctype": "CRM Deal", "filters": [["status", "Won"]]})
    with pytest.raises(ValueError, match="doctype"):
        await invoke(server, "frappe_list", {"doctype": " "})

    async def malformed(*args, **kwargs):
        return {"unexpected": "shape"}

    monkeypatch.setattr(frappe_list, "get", malformed)
    with pytest.raises(ValueError, match="invalid record list"):
        await invoke(server, "frappe_list", {"doctype": "CRM Deal"})

    async def fallback(path, params):
        selected = json.loads(params["fields"])
        calls.append(selected)
        if len(selected) > 5:
            raise frappe_common.FrappeRequestError(417, "field rejected")
        return [{"name": "CRM-DEAL-0001"}]

    monkeypatch.setattr(frappe_list, "get", fallback)
    await invoke(server, "frappe_list", {"doctype": "CRM Deal"})
    assert calls == [
        [
            "name",
            "organization",
            "custom_service_line",
            "status",
            "owner",
            "creation",
            "modified",
        ],
        ["name", "organization", "custom_service_line", "status", "owner", "creation"],
        ["name", "organization", "custom_service_line", "status", "owner"],
    ]


@pytest.mark.asyncio
async def test_list_explicit_fields_are_name_plus_only_requested_fields(server, monkeypatch):
    calls = []

    async def schema(_doctype):
        return SCHEMA

    async def upstream(_path, params):
        calls.append(json.loads(params["fields"]))
        return [RECORD]

    monkeypatch.setattr(frappe_list, "doctype_schema", schema)
    monkeypatch.setattr(frappe_list, "get", upstream)
    result = await invoke(
        server,
        "frappe_list",
        {"doctype": "CRM Deal", "fields": ["status", "custom_service_line", "status"]},
    )

    assert calls == [["name", "status", "custom_service_line"]]
    assert [column["key"] for column in result.structured_content["columns"]] == calls[0]


@pytest.mark.asyncio
async def test_list_explicit_field_rejection_is_not_silently_reduced(server, monkeypatch):
    async def schema(_doctype):
        return SCHEMA

    async def rejected(*args, **kwargs):
        raise frappe_common.FrappeRequestError(417, "field rejected")

    monkeypatch.setattr(frappe_list, "doctype_schema", schema)
    monkeypatch.setattr(frappe_list, "get", rejected)
    with pytest.raises(frappe_common.FrappeRequestError, match="field rejected"):
        await invoke(server, "frappe_list", {"doctype": "CRM Deal", "fields": ["status"]})


@pytest.mark.asyncio
async def test_list_upstream_failure_and_invalid_input(server, monkeypatch):
    async def schema(_doctype):
        return SCHEMA

    async def unavailable(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(frappe_list, "doctype_schema", schema)
    monkeypatch.setattr(frappe_list, "get", unavailable)
    with pytest.raises(httpx.ConnectError):
        await invoke(server, "frappe_list", {"doctype": "CRM Deal"})
    with pytest.raises(ValidationError):
        await invoke(server, "frappe_list", {"doctype": "CRM Deal", "limit": "many"})


@pytest.mark.asyncio
async def test_search_success_and_empty_query(server, monkeypatch):
    async def schema(_doctype):
        return SCHEMA

    calls = []

    async def upstream(_path, params):
        calls.append(params)
        return [RECORD]

    monkeypatch.setattr(frappe_search, "doctype_schema", schema)
    monkeypatch.setattr(frappe_search, "get", upstream)
    result = await invoke(server, "frappe_search", {"doctype": "CRM Deal", "query": "Acme"})
    assert json.loads(calls[0]["or_filters"]) == [
        ["name", "like", "%Acme%"],
        ["organization", "like", "%Acme%"],
        ["custom_service_line", "like", "%Acme%"],
    ]
    assert result.structured_content["records"] == [RECORD]
    await invoke(server, "frappe_search", {"doctype": "CRM Deal"})
    assert "or_filters" not in calls[1]


@pytest.mark.asyncio
async def test_search_empty_bad_input_417_fallback_and_upstream_error(server, monkeypatch):
    async def schema(_doctype):
        return SCHEMA

    monkeypatch.setattr(frappe_search, "doctype_schema", schema)
    monkeypatch.setattr(frappe_search, "get", lambda *a, **k: asyncio.sleep(0, result=[]))
    assert "Found 0" in text_of(
        await invoke(server, "frappe_search", {"doctype": "CRM Deal", "query": "absent"})
    )
    with pytest.raises(ValidationError):
        await invoke(server, "frappe_search", {"doctype": "CRM Deal", "limit": "many"})

    async def malformed(*args, **kwargs):
        return {"unexpected": "shape"}

    monkeypatch.setattr(frappe_search, "get", malformed)
    with pytest.raises(ValueError, match="invalid search result"):
        await invoke(server, "frappe_search", {"doctype": "CRM Deal"})

    calls = []

    async def fallback(_path, params):
        calls.append(json.loads(params["fields"]))
        if len(calls) == 1:
            raise frappe_common.FrappeRequestError(417, "field rejected")
        return [{"name": "CRM-DEAL-0001"}]

    monkeypatch.setattr(frappe_search, "get", fallback)
    await invoke(server, "frappe_search", {"doctype": "CRM Deal", "query": "Acme"})
    assert calls[-1] == ["name"]

    async def unavailable(*args, **kwargs):
        raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr(frappe_search, "get", unavailable)
    with pytest.raises(httpx.ReadTimeout):
        await invoke(server, "frappe_search", {"doctype": "CRM Deal", "query": "Acme"})


@pytest.mark.asyncio
async def test_get_success_empty_result_and_bad_inputs(server, monkeypatch):
    async def upstream(path, params=None):
        assert path == "/api/resource/CRM%20Deal/CRM-DEAL-0001"
        return RECORD

    monkeypatch.setattr(frappe_get, "get", upstream)
    result = await invoke(server, "frappe_get", {"doctype": "CRM Deal", "name": "CRM-DEAL-0001"})
    assert result.structured_content["record"] == RECORD
    assert "CRM-DEAL-0001" in text_of(result)

    async def missing(*args, **kwargs):
        return {}

    monkeypatch.setattr(frappe_get, "get", missing)
    assert "No CRM Deal record" in text_of(
        await invoke(server, "frappe_get", {"doctype": "CRM Deal", "name": "missing"})
    )
    with pytest.raises(ValidationError):
        await invoke(server, "frappe_get", {"doctype": "CRM Deal"})
    with pytest.raises(ValueError, match="name"):
        await invoke(server, "frappe_get", {"doctype": "CRM Deal", "name": " "})

    async def malformed(*args, **kwargs):
        return [RECORD]

    monkeypatch.setattr(frappe_get, "get", malformed)
    with pytest.raises(ValueError, match="invalid record response"):
        await invoke(server, "frappe_get", {"doctype": "CRM Deal", "name": "CRM-DEAL-0001"})


@pytest.mark.asyncio
async def test_update_success_sends_partial_payload_and_returns_record(server, monkeypatch):
    calls = []

    async def schema(doctype):
        assert doctype == "CRM Deal"
        return SCHEMA

    async def upstream(path, values):
        calls.append((path, values))
        return {**RECORD, **values}

    monkeypatch.setattr(frappe_update, "doctype_schema", schema)
    monkeypatch.setattr(frappe_update, "put", upstream)
    result = await invoke(
        server,
        "frappe_update",
        {
            "doctype": "CRM Deal",
            "name": "CRM-DEAL-0001",
            "values": {"custom_service_line": "Product", "status": "Won"},
        },
    )

    assert calls == [
        (
            "/api/resource/CRM%20Deal/CRM-DEAL-0001",
            {"custom_service_line": "Product", "status": "Won"},
        )
    ]
    assert result.structured_content["name"] == "CRM-DEAL-0001"
    assert result.structured_content["updated_fields"] == ["custom_service_line", "status"]
    assert result.structured_content["record"]["status"] == "Won"
    assert "Fields changed: custom_service_line, status" in text_of(result)
    assert '"organization": "Acme"' in text_of(result)
    assert '"status": "Won"' in text_of(result)
    assert not result.meta or "ui" not in result.meta


@pytest.mark.asyncio
async def test_update_rejects_bad_fields_and_empty_payload_before_put(server, monkeypatch):
    schema_data = {
        **SCHEMA,
        "fields": SCHEMA["fields"]
        + [
            {"fieldname": "locked", "label": "Locked", "fieldtype": "Data", "read_only": 1},
            {"fieldname": "computed", "label": "Computed", "fieldtype": "Data", "is_virtual": 1},
        ],
    }

    async def schema(_doctype):
        return schema_data

    async def put_should_not_run(*args, **kwargs):
        pytest.fail("The update request must not run after local input validation fails")

    monkeypatch.setattr(frappe_update, "doctype_schema", schema)
    monkeypatch.setattr(frappe_update, "put", put_should_not_run)
    arguments = {"doctype": "CRM Deal", "name": "CRM-DEAL-0001"}

    with pytest.raises(ValueError, match="values.*non-empty"):
        await invoke(server, "frappe_update", {**arguments, "values": {}})
    with pytest.raises(ValueError, match="locked"):
        await invoke(server, "frappe_update", {**arguments, "values": {"locked": "x"}})
    with pytest.raises(ValueError, match="computed"):
        await invoke(server, "frappe_update", {**arguments, "values": {"computed": "x"}})
    with pytest.raises(ValueError, match="unknown, hidden, or unsupported.*internal_note"):
        await invoke(server, "frappe_update", {**arguments, "values": {"internal_note": "x"}})
    with pytest.raises(ValueError, match="unknown, hidden, or unsupported.*name"):
        await invoke(server, "frappe_update", {**arguments, "values": {"name": "NEW-NAME"}})
    with pytest.raises(ValueError, match="doctype"):
        await invoke(server, "frappe_update", {**arguments, "doctype": " ", "values": {"status": "Won"}})
    with pytest.raises(ValueError, match="name"):
        await invoke(server, "frappe_update", {**arguments, "name": " ", "values": {"status": "Won"}})


@pytest.mark.asyncio
async def test_update_passes_explicit_null_and_surfaces_frappe_validation(server, monkeypatch):
    async def schema(_doctype):
        return SCHEMA

    calls = []

    async def capture_null(path, values):
        calls.append(values)
        return {"name": "CRM-DEAL-0001"}

    monkeypatch.setattr(frappe_update, "doctype_schema", schema)
    monkeypatch.setattr(frappe_update, "put", capture_null)
    await invoke(
        server,
        "frappe_update",
        {"doctype": "CRM Deal", "name": "CRM-DEAL-0001", "values": {"status": None}},
    )
    assert calls == [{"status": None}]

    async def rejected(path, values):
        raise frappe_common.FrappeRequestError(417, "Invalid status option")

    monkeypatch.setattr(frappe_update, "put", rejected)
    with pytest.raises(frappe_common.FrappeRequestError, match="Invalid status option"):
        await invoke(
            server,
            "frappe_update",
            {"doctype": "CRM Deal", "name": "CRM-DEAL-0001", "values": {"status": "No Such Status"}},
        )


@pytest.mark.asyncio
async def test_create_prepare_builds_form_from_merged_schema_without_writing(server, monkeypatch):
    schema_data = {
        **SCHEMA,
        "fields": [
            {"fieldname": "organization", "label": "Organization", "fieldtype": "Data", "reqd": 1},
            {"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Open\nClosed", "default": "Open"},
            {"fieldname": "locked", "label": "Locked", "fieldtype": "Data", "read_only": 1},
            {"fieldname": "internal_note", "label": "Internal", "fieldtype": "Data", "hidden": 1},
        ],
    }

    async def schema(doctype):
        assert doctype == "CRM Deal"
        return schema_data

    async def no_write(*args, **kwargs):
        pytest.fail("Prepare must never make a write request")

    monkeypatch.setattr(frappe_create_prepare, "doctype_schema", schema)
    monkeypatch.setattr(frappe_create_prepare, "post", no_write, raising=False)
    result = await invoke(server, "frappe_create_prepare", {"doctype": "CRM Deal", "values": {"organization": "Acme"}})
    payload = result.structured_content
    assert payload["mode"] == "create_form"
    assert payload["values"] == {"status": "Open", "organization": "Acme"}
    assert payload["missing_required"] == []
    assert {field["fieldname"] for field in payload["fields"]} == {"organization", "status"}
    assert "nothing has been created" in text_of(result)
    assert result.meta["ui"]["resourceUri"]

    with pytest.raises(ValueError, match="unknown, hidden, read-only, or unsupported.*locked"):
        await invoke(server, "frappe_create_prepare", {"doctype": "CRM Deal", "values": {"locked": "x"}})
    with pytest.raises(ValueError, match="unknown, hidden, read-only, or unsupported.*internal_note"):
        await invoke(server, "frappe_create_prepare", {"doctype": "CRM Deal", "values": {"internal_note": "x"}})
    with pytest.raises(ValueError, match="non-empty exact"):
        await invoke(server, "frappe_create_prepare", {"doctype": " "})


@pytest.mark.asyncio
async def test_create_record_validates_then_posts_and_returns_created_record(server, monkeypatch):
    schema_data = {
        **SCHEMA,
        "fields": [
            {"fieldname": "organization", "label": "Organization", "fieldtype": "Data", "reqd": 1},
            {"fieldname": "status", "label": "Status", "fieldtype": "Select"},
            {"fieldname": "locked", "label": "Locked", "fieldtype": "Data", "read_only": 1},
        ],
    }

    async def schema(_doctype):
        return schema_data

    calls = []

    async def upstream(path, values):
        calls.append((path, values))
        return {"name": "CRM-DEAL-0002", **values}

    monkeypatch.setattr(frappe_create_record, "doctype_schema", schema)
    monkeypatch.setattr(frappe_create_record, "post", upstream)
    result = await invoke(server, "frappe_create_record", {"doctype": "CRM Deal", "values": {"organization": "Acme", "status": "Open"}})
    assert calls == [("/api/resource/CRM%20Deal", {"organization": "Acme", "status": "Open"})]
    assert result.structured_content == {
        "mode": "created_record", "doctype": "CRM Deal",
        "record": {"name": "CRM-DEAL-0002", "organization": "Acme", "status": "Open"},
    }
    assert "CRM-DEAL-0002" in text_of(result)
    assert not result.meta or "ui" not in result.meta

    async def no_post(*args, **kwargs):
        pytest.fail("Invalid create input must not be sent to Frappe")

    monkeypatch.setattr(frappe_create_record, "post", no_post)
    with pytest.raises(ValueError, match="required field.*Organization"):
        await invoke(server, "frappe_create_record", {"doctype": "CRM Deal", "values": {"status": "Open"}})
    with pytest.raises(ValueError, match="read-only, or unsupported.*locked"):
        await invoke(server, "frappe_create_record", {"doctype": "CRM Deal", "values": {"organization": "Acme", "locked": "x"}})
    with pytest.raises(ValueError, match="unknown, hidden, read-only, or unsupported.*internal_note"):
        await invoke(server, "frappe_create_record", {"doctype": "CRM Deal", "values": {"organization": "Acme", "internal_note": "x"}})
    with pytest.raises(ValueError, match="non-empty object"):
        await invoke(server, "frappe_create_record", {"doctype": "CRM Deal", "values": {}})

    async def rejected(path, values):
        raise frappe_common.FrappeRequestError(417, "Invalid organization")

    monkeypatch.setattr(frappe_create_record, "post", rejected)
    with pytest.raises(frappe_common.FrappeRequestError, match="Invalid organization"):
        await invoke(server, "frappe_create_record", {"doctype": "CRM Deal", "values": {"organization": "Acme"}})


@pytest.mark.asyncio
async def test_create_tools_resolve_and_validate_child_table_schemas(server, monkeypatch):
    parent_schema = {
        "name": "Contact",
        "fields": [
            {"fieldname": "first_name", "label": "First Name", "fieldtype": "Data", "reqd": 1},
            {"fieldname": "email_ids", "label": "Email Addresses", "fieldtype": "Table", "options": "Contact Email"},
        ],
    }
    child_schema = {
        "name": "Contact Email",
        "istable": 1,
        "fields": [
            {"fieldname": "email_id", "label": "Email Address", "fieldtype": "Data", "reqd": 1},
            {"fieldname": "is_primary", "label": "Is Primary", "fieldtype": "Check", "default": 0},
        ],
    }

    async def schema(doctype):
        return {"Contact": parent_schema, "Contact Email": child_schema}[doctype]

    monkeypatch.setattr(frappe_create_prepare, "doctype_schema", schema)
    prepared = await invoke(server, "frappe_create_prepare", {"doctype": "Contact"})
    table = next(field for field in prepared.structured_content["fields"] if field["fieldname"] == "email_ids")
    assert table["child_doctype"] == "Contact Email"
    assert [field["fieldname"] for field in table["child_fields"]] == ["email_id", "is_primary"]
    assert prepared.structured_content["values"]["email_ids"] == []

    calls = []

    async def post(path, values):
        calls.append((path, values))
        return {"name": "CONTACT-001", **values}

    monkeypatch.setattr(frappe_create_record, "doctype_schema", schema)
    monkeypatch.setattr(frappe_create_record, "post", post)
    values = {
        "first_name": "Alice",
        "email_ids": [{"email_id": "alice@example.com", "is_primary": 1}],
    }
    created = await invoke(server, "frappe_create_record", {"doctype": "Contact", "values": values})
    assert calls == [("/api/resource/Contact", values)]
    assert created.structured_content["record"]["email_ids"] == values["email_ids"]

    with pytest.raises(ValueError, match="email_ids\\[0\\].*unknown.*invalid_field"):
        await invoke(
            server,
            "frappe_create_record",
            {"doctype": "Contact", "values": {**values, "email_ids": [{"email_id": "alice@example.com", "invalid_field": "x"}]}},
        )
    with pytest.raises(ValueError, match="email_ids\\[0\\].*required field.*Email Address"):
        await invoke(
            server,
            "frappe_create_record",
            {"doctype": "Contact", "values": {**values, "email_ids": [{"is_primary": 1}]}},
        )
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_update_appends_child_rows_without_dropping_existing_rows(server, monkeypatch):
    parent_schema = {
        "name": "Contact",
        "fields": [
            {"fieldname": "first_name", "label": "First Name", "fieldtype": "Data"},
            {"fieldname": "email_ids", "label": "Email Addresses", "fieldtype": "Table", "options": "Contact Email"},
        ],
    }
    child_schema = {
        "name": "Contact Email",
        "istable": 1,
        "fields": [
            {"fieldname": "email_id", "label": "Email Address", "fieldtype": "Data", "reqd": 1},
            {"fieldname": "is_primary", "label": "Is Primary", "fieldtype": "Check"},
        ],
    }

    async def schema(doctype):
        return {"Contact": parent_schema, "Contact Email": child_schema}[doctype]

    existing = {
        "doctype": "Contact",
        "name": "CONTACT-001",
        "email_ids": [
            {"name": "ROW-1", "email_id": "old@example.com", "is_primary": 1, "parent": "CONTACT-001", "parentfield": "email_ids"}
        ],
    }
    reads = []
    writes = []

    async def get_for_update(path):
        reads.append(path)
        return existing

    async def put(path, values):
        writes.append((path, values))
        return {"name": "CONTACT-001", **values}

    monkeypatch.setattr(frappe_update, "doctype_schema", schema)
    monkeypatch.setattr(frappe_update, "get_for_update", get_for_update)
    monkeypatch.setattr(frappe_update, "put", put)
    result = await invoke(
        server,
        "frappe_update",
        {
            "doctype": "Contact",
            "name": "CONTACT-001",
            "child_table_changes": [
                {"fieldname": "email_ids", "operation": "append", "rows": [{"email_id": "new@example.com", "is_primary": 0}]}
            ],
        },
    )

    assert reads == ["/api/resource/Contact/CONTACT-001"]
    assert writes == [
        (
            "/api/resource/Contact/CONTACT-001",
            {"email_ids": [*existing["email_ids"], {"email_id": "new@example.com", "is_primary": 0}]},
        )
    ]
    assert result.structured_content["record"]["email_ids"][0]["name"] == "ROW-1"
    assert result.structured_content["record"]["email_ids"][1]["email_id"] == "new@example.com"

    with pytest.raises(ValueError, match="child_table_changes.*unknown.*bad_field"):
        await invoke(
            server,
            "frappe_update",
            {
                "doctype": "Contact",
                "name": "CONTACT-001",
                "child_table_changes": [
                    {"fieldname": "email_ids", "operation": "append", "rows": [{"bad_field": "x"}]}
                ],
            },
        )
    with pytest.raises(ValueError, match="cannot replace child table.*child_table_changes"):
        await invoke(
            server,
            "frappe_update",
            {"doctype": "Contact", "name": "CONTACT-001", "values": {"email_ids": []}},
        )
    assert len(reads) == 1
    assert len(writes) == 1


@pytest.mark.asyncio
async def test_shared_post_transport_and_ambiguous_timeout_hint(monkeypatch):
    requests = []

    class Response:
        status_code = 200
        text = ""

        def json(self):
            return {"data": {"name": "NEW-001", "organization": "Acme"}}

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def request(self, method, url, **kwargs):
            requests.append((method, url, kwargs))
            return Response()

    monkeypatch.setattr(frappe_common, "connection", lambda: asyncio.sleep(0, result=("https://frappe.invalid", "token a:b")))
    monkeypatch.setattr(frappe_common.httpx, "AsyncClient", Client)
    assert await frappe_common.post("/api/resource/CRM%20Deal", {"organization": "Acme"}) == {"name": "NEW-001", "organization": "Acme"}
    assert requests[0][0] == "POST"
    assert requests[0][1] == "https://frappe.invalid/api/resource/CRM%20Deal"
    assert requests[0][2]["json"] == {"organization": "Acme"}
    assert requests[0][2]["headers"]["Content-Type"] == "application/json"

    async def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("late response")

    monkeypatch.setattr(Client, "request", timeout)
    with pytest.raises(frappe_common.FrappeRequestError, match="outcome is unknown.*avoid creating a duplicate"):
        await frappe_common.post("/api/resource/CRM%20Deal", {"organization": "Acme"})


@pytest.mark.asyncio
async def test_count_success_filters_bad_response_and_upstream_error(server, monkeypatch):
    calls = []

    async def upstream(path, params):
        calls.append((path, params))
        return "7"

    monkeypatch.setattr(frappe_count, "get", upstream)
    assert plain_value(await invoke(server, "frappe_count", {"doctype": "CRM Deal", "filters": [["status", "=", "Won"]]})) == 7
    assert json.loads(calls[0][1]["filters"]) == [["status", "=", "Won"]]

    async def malformed(*args, **kwargs):
        return {"count": 7}

    monkeypatch.setattr(frappe_count, "get", malformed)
    with pytest.raises(ValueError, match="invalid record count"):
        await invoke(server, "frappe_count", {"doctype": "CRM Deal"})
    with pytest.raises(ValidationError):
        await invoke(server, "frappe_count", {})

    async def unavailable(*args, **kwargs):
        raise httpx.HTTPStatusError("bad gateway", request=None, response=None)

    monkeypatch.setattr(frappe_count, "get", unavailable)
    with pytest.raises(httpx.HTTPStatusError):
        await invoke(server, "frappe_count", {"doctype": "CRM Deal"})


@pytest.mark.asyncio
async def test_job_overview_success_missing_project_and_partial_failure(server, monkeypatch):
    calls = []

    async def upstream(path, params=None):
        calls.append((path, params))
        if path == "/api/resource/Project/PRJ-001":
            return {"name": "PRJ-001", "project_name": "Alpha"}
        return [{"name": path.split("/")[-1]}]

    monkeypatch.setattr(frappe_job_overview, "get", upstream)
    result = await invoke(server, "frappe_job_overview", {"project": "PRJ-001"})
    assert result.structured_content["record"]["project"]["project_name"] == "Alpha"
    assert len(calls) == 4

    async def partial(path, params=None):
        if path == "/api/resource/Project/PRJ-001":
            return {"name": "PRJ-001"}
        raise httpx.ConnectError("invoice endpoint offline")

    monkeypatch.setattr(frappe_job_overview, "get", partial)
    partial_result = await invoke(server, "frappe_job_overview", {"project": "PRJ-001"})
    assert "invoice endpoint offline" in str(partial_result.structured_content["record"]["sales_invoices"])

    async def no_project(path, params=None):
        return {} if path == "/api/resource/Project/PRJ-404" else []

    monkeypatch.setattr(frappe_job_overview, "get", no_project)
    assert "No project record" in text_of(
        await invoke(server, "frappe_job_overview", {"project": "PRJ-404"})
    )

    async def project_failure(path, params=None):
        if path == "/api/resource/Project/PRJ-001":
            raise httpx.ConnectError("project endpoint offline")
        return []

    monkeypatch.setattr(frappe_job_overview, "get", project_failure)
    with pytest.raises(httpx.ConnectError, match="project endpoint offline"):
        await invoke(server, "frappe_job_overview", {"project": "PRJ-001"})
    with pytest.raises(ValidationError):
        await invoke(server, "frappe_job_overview", {})


@pytest.mark.asyncio
async def test_shared_get_success_redaction_and_upstream_error_mapping(monkeypatch):
    requests = []

    class Response:
        status_code = 200
        text = ""

        def raise_for_status(self):
            if self.status_code >= 400:
                request = httpx.Request("GET", "https://frappe.invalid/api/resource/Test")
                response = httpx.Response(self.status_code, request=request)
                raise httpx.HTTPStatusError("upstream failure", request=request, response=response)
            return None

        def json(self):
            return {"data": {"name": "x", "api_secret": "hide", "nested": {"password": "hide", "ok": 1}}}

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def request(self, method, url, **kwargs):
            requests.append((method, url, kwargs))
            return Response()

    monkeypatch.setattr(frappe_common, "connection", lambda: asyncio.sleep(0, result=("https://frappe.invalid", "token x:y")))
    monkeypatch.setattr(frappe_common.httpx, "AsyncClient", Client)
    assert await frappe_common.get("/api/resource/Test") == {"name": "x", "nested": {"ok": 1}}
    updated = await frappe_common.put(
        "/api/resource/CRM%20Deal/CRM-DEAL-0001",
        {"status": "Won"},
    )
    assert updated == {"name": "x", "nested": {"ok": 1}}
    method, url, request_kwargs = requests[-1]
    assert method == "PUT"
    assert url == "https://frappe.invalid/api/resource/CRM%20Deal/CRM-DEAL-0001"
    assert request_kwargs["json"] == {"status": "Won"}
    assert request_kwargs["headers"]["Content-Type"] == "application/json"
    assert request_kwargs["headers"]["Authorization"] == "token x:y"

    class Failure(Response):
        def __init__(self, status, body="upstream failed"):
            self.status_code = status
            self.text = body

    for status, expected in ((401, "authentication failed"), (403, "read or write permission")):
        async def denied(*args, _status=status, **kwargs):
            return Failure(_status)

        monkeypatch.setattr(Client, "request", denied)
        with pytest.raises(PermissionError, match=expected):
            await frappe_common.get("/api/resource/Test")

    async def rejected(*args, **kwargs):
        return Failure(417)

    monkeypatch.setattr(Client, "request", rejected)
    with pytest.raises(frappe_common.FrappeRequestError, match="417"):
        await frappe_common.get("/api/resource/Test")

    class ValidationFailure(Failure):
        def json(self):
            return {
                "exc_type": "ValidationError",
                "_server_messages": json.dumps([json.dumps({"message": "First Name is required"})]),
            }

    async def invalid_document(*args, **kwargs):
        return ValidationFailure(417)

    monkeypatch.setattr(Client, "request", invalid_document)
    with pytest.raises(frappe_common.FrappeRequestError) as create_error:
        await frappe_common.post("/api/resource/Contact", {"email_id": "person@example.com"})
    assert "Frappe rejected the create request" in str(create_error.value)
    assert "this record was not created" in str(create_error.value)
    assert "First Name is required" in str(create_error.value)

    async def gateway_failure(*args, **kwargs):
        return Failure(502)

    monkeypatch.setattr(Client, "request", gateway_failure)
    with pytest.raises(frappe_common.FrappeRequestError, match=r"server error \(502\)"):
        await frappe_common.get("/api/resource/Test")

    async def not_found(*args, **kwargs):
        return Failure(404, '{"message":"CRM Deal does not exist"}')

    monkeypatch.setattr(Client, "request", not_found)
    with pytest.raises(frappe_common.FrappeRequestError, match="exact DocType and record name"):
        await frappe_common.get("/api/resource/CRM%20Deal/missing")

    async def limited(*args, **kwargs):
        return Failure(429)

    monkeypatch.setattr(Client, "request", limited)
    with pytest.raises(frappe_common.FrappeRequestError, match="rate-limited"):
        await frappe_common.get("/api/resource/Test")

    async def timed_out(*args, **kwargs):
        raise httpx.ReadTimeout("late")

    monkeypatch.setattr(Client, "request", timed_out)
    with pytest.raises(frappe_common.FrappeRequestError, match="timed out"):
        await frappe_common.get("/api/resource/Test")

    async def offline(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(Client, "request", offline)
    with pytest.raises(frappe_common.FrappeRequestError, match="Could not connect"):
        await frappe_common.get("/api/resource/Test")
