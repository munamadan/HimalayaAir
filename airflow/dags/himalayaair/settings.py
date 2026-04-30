from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_SYNC_DATABASE_URL = "postgresql://himalayaair:himalayaair@timescaledb:5432/himalayaair"


@dataclass(frozen=True)
class AirflowTaskSettings:
    database_url: str
    log_format: str
    openaq_api_key: str | None
    firms_map_key: str | None
    http_timeout_seconds: float
    http_retries: int
    openaq_backfill_max_sensors: int
    openaq_backfill_max_days: int
    weather_backfill_max_locations: int
    weather_backfill_max_months: int
    quality_fresh_hours: int
    quality_recent_hours: int
    quality_dead_sensor_days: int
    firms_source: str
    firms_bbox: str
    firms_day_range: int

    @classmethod
    def from_env(cls) -> "AirflowTaskSettings":
        return cls(
            database_url=sync_database_url(os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL")),
            log_format=os.getenv("LOG_FORMAT", "json"),
            openaq_api_key=_optional_env("OPENAQ_API_KEY"),
            firms_map_key=_optional_env("FIRMS_MAP_KEY"),
            http_timeout_seconds=_float_env("AIRFLOW_HTTP_TIMEOUT_SECONDS", 20.0),
            http_retries=_int_env("AIRFLOW_HTTP_RETRIES", 2),
            openaq_backfill_max_sensors=_int_env("AIRFLOW_OPENAQ_BACKFILL_MAX_SENSORS", 0),
            openaq_backfill_max_days=_int_env("AIRFLOW_OPENAQ_BACKFILL_MAX_DAYS", 7),
            weather_backfill_max_locations=_int_env("AIRFLOW_WEATHER_BACKFILL_MAX_LOCATIONS", 0),
            weather_backfill_max_months=_int_env("AIRFLOW_WEATHER_BACKFILL_MAX_MONTHS", 3),
            quality_fresh_hours=_int_env("AIRFLOW_QUALITY_FRESH_HOURS", 2),
            quality_recent_hours=_int_env("AIRFLOW_QUALITY_RECENT_HOURS", 24),
            quality_dead_sensor_days=_int_env("AIRFLOW_QUALITY_DEAD_SENSOR_DAYS", 14),
            firms_source=os.getenv("FIRMS_SOURCE", "VIIRS_SNPP_NRT"),
            firms_bbox=os.getenv("FIRMS_AREA_BBOX", "80.0,26.0,89.0,31.0"),
            firms_day_range=_bounded_int_env("FIRMS_DAY_RANGE", 1, minimum=1, maximum=5),
        )


def sync_database_url(value: str | None) -> str:
    if not value or not value.strip():
        return DEFAULT_SYNC_DATABASE_URL
    if value.startswith("postgresql+asyncpg://"):
        return "postgresql://" + value.removeprefix("postgresql+asyncpg://")
    if value.startswith("postgresql+psycopg2://"):
        return "postgresql://" + value.removeprefix("postgresql+psycopg2://")
    return value


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return value.strip()


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


def _bounded_int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    parsed = _int_env(name, default)
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
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
