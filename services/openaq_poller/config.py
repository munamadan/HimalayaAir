from __future__ import annotations

import os
from dataclasses import dataclass

from shared.settings import KafkaSettings


DEFAULT_SYNC_DATABASE_URL = "postgresql://himalayaair:himalayaair@localhost:55432/himalayaair"


@dataclass(frozen=True)
class OpenAQPollerSettings:
    service_name: str
    log_format: str
    openaq_api_key: str | None
    database_url: str
    kafka: KafkaSettings
    poll_interval_seconds: int
    overlap_minutes: int
    fallback_lookback_hours: int
    measurements_limit: int
    max_pages: int
    http_timeout_seconds: float
    http_retries: int
    health_host: str
    health_port: int
    pipeline_component: str = "openaq_poller"

    @classmethod
    def from_env(cls) -> "OpenAQPollerSettings":
        service_name = os.getenv("SERVICE_NAME", "openaq-poller")
        return cls(
            service_name=service_name,
            log_format=os.getenv("LOG_FORMAT", "json"),
            openaq_api_key=_optional_env("OPENAQ_API_KEY"),
            database_url=_sync_database_url(),
            kafka=KafkaSettings.from_env(service_name=service_name),
            poll_interval_seconds=_int_env("OPENAQ_POLL_INTERVAL_SECONDS", 300),
            overlap_minutes=_int_env("OPENAQ_POLL_OVERLAP_MINUTES", 10),
            fallback_lookback_hours=_int_env("OPENAQ_FALLBACK_LOOKBACK_HOURS", 6),
            measurements_limit=_int_env("OPENAQ_MEASUREMENTS_LIMIT", 100),
            max_pages=_int_env("OPENAQ_MAX_PAGES", 5),
            http_timeout_seconds=_float_env("OPENAQ_HTTP_TIMEOUT_SECONDS", 15.0),
            http_retries=_int_env("OPENAQ_HTTP_RETRIES", 2),
            health_host=os.getenv("OPENAQ_HEALTH_HOST", "0.0.0.0"),
            health_port=_int_env("OPENAQ_HEALTH_PORT", 9090),
        )


def _sync_database_url() -> str:
    explicit = os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not explicit:
        return DEFAULT_SYNC_DATABASE_URL
    if explicit.startswith("postgresql+asyncpg://"):
        return "postgresql://" + explicit.removeprefix("postgresql+asyncpg://")
    if explicit.startswith("postgresql+psycopg2://"):
        return "postgresql://" + explicit.removeprefix("postgresql+psycopg2://")
    return explicit


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return value


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if parsed < 0:
        raise ValueError(f"{name} must be non-negative")
    return parsed


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if parsed < 0:
        raise ValueError(f"{name} must be non-negative")
    return parsed

