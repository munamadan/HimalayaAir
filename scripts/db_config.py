from __future__ import annotations

import os

DEFAULT_SYNC_DATABASE_URL = "postgresql://himalayaair:himalayaair@localhost:55432/himalayaair"


def normalize_sync_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + url.removeprefix("postgresql+asyncpg://")
    if url.startswith("postgresql+psycopg2://"):
        return "postgresql://" + url.removeprefix("postgresql+psycopg2://")
    return url


def sync_database_url(explicit_url: str | None = None) -> str:
    if explicit_url:
        return normalize_sync_database_url(explicit_url)
    if os.environ.get("SYNC_DATABASE_URL"):
        return normalize_sync_database_url(os.environ["SYNC_DATABASE_URL"])
    if os.environ.get("DATABASE_URL"):
        return normalize_sync_database_url(os.environ["DATABASE_URL"])
    return DEFAULT_SYNC_DATABASE_URL
