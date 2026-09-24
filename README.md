# FrappeERP MCP App

FrappeERP MCP App connects an MCP-compatible assistant to a user's Frappe site. It exposes schema-aware tools for discovering DocTypes, listing and searching records, loading complete records, updating records, and preparing new records for user review in an embedded UI.

The server uses the caller's saved Frappe base URL, API key, and API secret. Credentials are stored per user encrypted in PostgreSQL and are used only by the server when it calls Frappe. The MCP transport is protected by Twynity account-service authentication; Frappe's own permissions and validations remain authoritative for data access and writes.

## What it does

- Connects a user's Frappe site using its base URL, API key, and API secret.
- Discovers exact DocType names so the assistant can distinguish similar records, such as `Lead` and `CRM Lead`.
- Retrieves DocType schemas dynamically, including available custom fields and child-table metadata where Frappe exposes them.
- Lists, searches, counts, and fetches records across installed Frappe modules, including ERPNext, CRM, HRMS, and custom apps, subject to the configured API user's access.
- Updates explicitly requested fields on existing records and can append child-table rows without replacing existing rows.
- Prepares schema-driven create forms for user review. No record is written until the user presses **Create** in the UI.
- Renders list results and full record details in a reusable MCP App dashboard. `CRM Deal` list results use a pipeline board with a service-line filter when that field is present.

## Tools

| Tool | Purpose |
| --- | --- |
| `frappe_doctypes` | Discover available DocTypes and their modules. Use the exact returned DocType name in subsequent calls; ask the user if multiple DocTypes plausibly match. |
| `frappe_schema` | Inspect a DocType's fields and metadata, including custom fields when returned by Frappe. |
| `frappe_list` | List records, with optional filters, ordering, pagination, and field selection. By default it returns at most five fields total: the exact record `name` plus up to four metadata-selected preview fields. If `fields` is supplied, it returns `name` plus exactly those fields. The chat response is a compact record index containing count and exact record names; selected records and columns are returned for the canvas. |
| `frappe_search` | Search a DocType using its configured search fields, global-search fields, or record name. It discovers schema and searchable fields internally. |
| `frappe_count` | Count records in a DocType, optionally using Frappe filters. |
| `frappe_get` | Fetch a complete record using its exact DocType and Frappe `name` (the document ID). Use the `name` supplied by list/search results. |
| `frappe_job_overview` | Load a Project and related Sales Invoices, Purchase Invoices, and Timesheets. |
| `frappe_update` | Partially update explicitly requested fields on one record; may append child-table rows while preserving existing rows. Returns the updated record. |
| `frappe_create_prepare` | Fetch schema and open a prefilled, editable form. This does not save anything. |
| `frappe_create_record` | App-only tool invoked by the form's explicit **Create** button. Validates the submitted values, creates one record, and returns it for a read-only details view. It is not Frappe's document Submit workflow action. |

The assistant is instructed to discover DocTypes before querying or preparing a create form, avoid guessing between plausible DocTypes, use exact record IDs for `frappe_get`, and never invoke the app-only create tool on the user's behalf. When a requested visualization needs more than the default list preview, the assistant can inspect the schema and explicitly request its fields. Frappe validates permissions, required conditions, workflows, and document hooks on every write.

### Create flow

```text
User asks to create a record
        |
        v
Assistant identifies the exact DocType and calls frappe_create_prepare
        |
        v
Server loads schema and returns fields/defaults/child-table metadata
        |
        v
MCP App shows an editable form; user reviews and adjusts values
        |
        v
User clicks Create -> app.callServerTool("frappe_create_record", ...)
        |
        v
Server validates again, POSTs to Frappe, and returns the created record
        |
        v
MCP App displays the created record read-only
```

The browser never calls the Frappe REST API directly and never receives the API secret. Child-table rows are sent within the parent document payload and validated using the child DocType schema.

## UI behavior

`app/ui/frappe_ui/` contains the React MCP App. The reusable dashboard displays list data and record details, supports schema-driven create forms including child-row editing, and uses the host client's theme variables and fonts where available. `CRM Deal` gets a specialized pipeline board grouped by deal status, with a filter for service line. Other DocTypes use the generic record/list presentation.

Only tools with a view declare the UI resource in their MCP metadata. The create commit tool is app-only (`visibility=["app"]`); the model can prepare a form, but the explicit UI action is required to write the record.

## Configuration and authentication

Copy `.env.example` to `.env` for local development and configure the required deployment values. Do not commit populated secrets.

Server environment configuration includes:

- `ACCOUNT_SERVICE_URL`, `ACCOUNT_SERVICE_JWKS_ENDPOINT`, and `ACCOUNT_SERVICE_JWKS_CACHE_TTL` for verifying Twynity bearer tokens.
- `USAGE_REPORT_ENDPOINT` for usage reporting.
- `LICENSE_KEY`, `LICENSE_SERVER_BASE_URL`, and the license JWKS/activation endpoints.
- `DATABASE_URL` and `ENCRYPTION_KEY` for per-user Frappe connection storage. Generate a Fernet-compatible key for `ENCRYPTION_KEY`.
- `FRAPPE_TIMEOUT_SECONDS` (default `60`) and `FRAPPE_MAX_LIMIT` (default `100`, maximum records per list/search page).
- `PUBLIC_URL`, `ALLOWED_ORIGINS`, and `ENVIRONMENT` for public routing and CORS/runtime configuration.

The Frappe connection itself is **not** a global environment variable. The authenticated user submits these fields through the external-connection configuration flow:

```json
{
  "frappe_base_url": "https://your-site.example.com",
  "api_key": "your-api-key",
  "api_secret": "your-api-secret"
}
```

Connection routes:

- `GET /api/v1/.well-known/mcp.json` — MCP manifest and external-connection declaration.
- `GET /api/v1/schema` — configuration form schema.
- `POST /api/v1/configuration` — save/update the authenticated user's connection.
- `GET /api/v1/external-connection/me` — report whether that user has configured Frappe.
- `GET /api/v1/health` — health check.
- `/mcp` — authenticated Streamable HTTP MCP endpoint.

The base URL and credentials are encrypted before PostgreSQL storage. Each tool call resolves the connection for the authenticated user; Frappe permissions associated with that API-key user determine what can be read or changed.

## Run locally

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/), and Node.js 22 for the React UI.

```bash
cp .env.example .env
uv sync --locked
cd app/ui/frappe_ui
npm ci
npm run build
cd ../../..
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The UI build is served as a packaged MCP resource. Rebuild it after frontend changes:

```bash
cd app/ui/frappe_ui
npm run build
```

## Tests and lint

```bash
uv run pytest -q
uv run ruff check app tests
```

Tests cover tool success and error paths, input validation, upstream Frappe failures, authentication, and custom routes. Build the UI before running tests that verify the compiled resource.

## Docker

The multi-stage Dockerfile builds the React UI and copies the generated bundle into the Python runtime image:

```bash
docker build -t frappeerp-mcpapp:local .
docker run --rm --env-file .env -p 8000:8000 frappeerp-mcpapp:local
```

Use a persistent PostgreSQL database and production-grade secrets in deployment. Configure the public URL, allowed client origins, Twynity account/license services, usage endpoint, database URL, and encryption key for the target environment.
