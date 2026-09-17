"""Encrypted per-user Frappe connection storage."""

import psycopg
from cryptography.fernet import Fernet

from app.config import settings

_cipher = Fernet(settings.ENCRYPTION_KEY.encode())


async def ensure_schema() -> None:
    async with await psycopg.AsyncConnection.connect(settings.DATABASE_URL) as conn:
        await conn.execute("""CREATE TABLE IF NOT EXISTS frappe_connections (
            user_id TEXT PRIMARY KEY, frappe_base_url TEXT NOT NULL, api_key BYTEA NOT NULL,
            api_secret BYTEA NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
        await conn.commit()


async def save_connection(user_id: str, frappe_url: str, api_key: str, api_secret: str) -> None:
    async with await psycopg.AsyncConnection.connect(settings.DATABASE_URL) as conn:
        await conn.execute(
            """INSERT INTO frappe_connections
            (user_id, frappe_base_url, api_key, api_secret) VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET frappe_base_url=EXCLUDED.frappe_base_url,
            api_key=EXCLUDED.api_key, api_secret=EXCLUDED.api_secret, updated_at=NOW()""",
            (
                user_id,
                frappe_url.rstrip("/"),
                _cipher.encrypt(api_key.encode()),
                _cipher.encrypt(api_secret.encode()),
            ),
        )
        await conn.commit()


async def get_connection(user_id: str) -> tuple[str, str, str] | None:
    async with await psycopg.AsyncConnection.connect(settings.DATABASE_URL) as conn:
        cur = await conn.execute(
            "SELECT frappe_base_url, api_key, api_secret FROM frappe_connections WHERE user_id=%s",
            (user_id,),
        )
        row = await cur.fetchone()
    if row is None:
        return None
    return row[0], _cipher.decrypt(bytes(row[1])).decode(), _cipher.decrypt(bytes(row[2])).decode()
