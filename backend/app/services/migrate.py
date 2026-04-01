"""Lightweight schema evolution sqlite/postgres without Alembic."""

from __future__ import annotations

import uuid
from typing import Set

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _tables(engine: Engine) -> Set[str]:
    return set(inspect(engine).get_table_names())


def _existing_columns(engine: Engine, table: str) -> Set[str]:
    if table not in _tables(engine):
        return set()
    return {c["name"] for c in inspect(engine).get_columns(table)}


def run_schema_migrations(engine: Engine) -> None:
    with engine.begin() as conn:
        tables = _tables(engine)

        if "users" in tables:
            user_cols = _existing_columns(engine, "users")
            if "role" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(32) NOT NULL DEFAULT 'citizen'"))
            if "password_hash" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))

        if "reports" in tables:
            report_cols = _existing_columns(engine, "reports")
            if "public_id" not in report_cols:
                conn.execute(text("ALTER TABLE reports ADD COLUMN public_id VARCHAR(36)"))
            if "status" not in report_cols:
                conn.execute(text("ALTER TABLE reports ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'pending'"))
            if "latitude" not in report_cols:
                conn.execute(text("ALTER TABLE reports ADD COLUMN latitude DOUBLE PRECISION"))
            if "longitude" not in report_cols:
                conn.execute(text("ALTER TABLE reports ADD COLUMN longitude DOUBLE PRECISION"))
            if "user_email" not in report_cols:
                conn.execute(text("ALTER TABLE reports ADD COLUMN user_email VARCHAR(255)"))
            if "is_panic" not in report_cols:
                if engine.dialect.name == "sqlite":
                    conn.execute(text("ALTER TABLE reports ADD COLUMN is_panic BOOLEAN NOT NULL DEFAULT 0"))
                else:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN is_panic BOOLEAN NOT NULL DEFAULT false"))

            if "voice_file_name" not in report_cols:
                conn.execute(text("ALTER TABLE reports ADD COLUMN voice_file_name VARCHAR(255)"))
            if "voice_content_type" not in report_cols:
                conn.execute(text("ALTER TABLE reports ADD COLUMN voice_content_type VARCHAR(128)"))
            if "voice_bytes" not in report_cols:
                if engine.dialect.name == "sqlite":
                    conn.execute(text("ALTER TABLE reports ADD COLUMN voice_bytes BLOB"))
                else:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN voice_bytes BYTEA"))
            if "voice_transcript" not in report_cols:
                conn.execute(text("ALTER TABLE reports ADD COLUMN voice_transcript TEXT"))

            rows = conn.execute(text("SELECT id FROM reports WHERE public_id IS NULL OR public_id = ''")).fetchall()
            for (rid,) in rows:
                conn.execute(
                    text("UPDATE reports SET public_id = :pid WHERE id = :id"),
                    {"pid": str(uuid.uuid4()), "id": rid},
                )
