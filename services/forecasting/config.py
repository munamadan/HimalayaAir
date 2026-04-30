from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_SYNC_DATABASE_URL = "postgresql://himalayaair:himalayaair@localhost:55432/himalayaair"

@dataclass(frozen=True)
class ForecastSettings:
    database_url: str
    service_name: str
    log_format: str
    pollutants: tuple[str, ...]
    horizon_hours: int
    history_days: int
    bias_days: int
    min_observed_coverage: float
    min_weather_history_coverage: float
    max_stations: int
    default_baseline_aqi: int
    sarimax_enabled: bool
    pipeline_component: str

    @classmethod
    def from_env(cls) -> "ForecastSettings":
        return cls(
            database_url=_sync_database_url(os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL")),
            service_name=os.getenv("SERVICE_NAME", "forecast-recompute"),
            log_format=os.getenv("LOG_FORMAT", "json"),
            pollutants=_csv_env("FORECAST_POLLUTANTS", ("pm25",)),
            horizon_hours=_bounded_int_env("FORECAST_HORIZON_HOURS", 72, minimum=1, maximum=168),
            history_days=_bounded_int_env("FORECAST_HISTORY_DAYS", 90, minimum=1, maximum=366),
            bias_days=_bounded_int_env("FORECAST_BIAS_DAYS", 7, minimum=1, maximum=60),
            min_observed_coverage=_coverage_env("FORECAST_MIN_OBSERVED_COVERAGE", 0.70),
            min_weather_history_coverage=_coverage_env("FORECAST_MIN_WEATHER_HISTORY_COVERAGE", 0.70),
            max_stations=_int_env("FORECAST_MAX_STATIONS", 0),
            default_baseline_aqi=_bounded_int_env("FORECAST_DEFAULT_BASELINE_AQI", 50, minimum=0, maximum=500),
            sarimax_enabled=_bool_env("FORECAST_SARIMAX_ENABLED", True),
            pipeline_component=os.getenv("FORECAST_PIPELINE_COMPONENT", "forecast_recompute"),
        )


def _csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    values = tuple(part.strip().lower() for part in raw.split(",") if part.strip())
    return values or default


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


def _coverage_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if parsed < 0 or parsed > 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return parsed


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


def _sync_database_url(value: str | None) -> str:
    if value is None or not value.strip():
        return DEFAULT_SYNC_DATABASE_URL
    if value.startswith("postgresql+asyncpg://"):
        return "postgresql://" + value.removeprefix("postgresql+asyncpg://")
    if value.startswith("postgresql+psycopg2://"):
        return "postgresql://" + value.removeprefix("postgresql+psycopg2://")
    return value
