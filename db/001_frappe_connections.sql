CREATE TABLE IF NOT EXISTS frappe_connections (
    user_id TEXT PRIMARY KEY,
    frappe_base_url TEXT NOT NULL,
    api_key BYTEA NOT NULL,
    api_secret BYTEA NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
