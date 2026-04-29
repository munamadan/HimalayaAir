from __future__ import annotations

import os
from dataclasses import dataclass

from shared.settings import KafkaSettings


DEFAULT_SYNC_DATABASE_URL = "postgresql://himalayaair:himalayaair@localhost:55432/himalayaair"


@dataclass(frozen=True)
class WeatherPollerSettings:
    service_name: str
    log_format: str
    database_url: str
    kafka: KafkaSettings
    poll_interval_seconds: int
    components: frozenset[str]
    weather_forecast_days: int
    weather_past_days: int
    modeled_aq_forecast_days: int
    modeled_aq_past_days: int
    max_locations: int
    publish_kafka: bool
    http_timeout_seconds: float
    http_retries: int
    health_host: str
    health_port: int
    pipeline_component: str

    @classmethod
    def from_env(cls) -> "WeatherPollerSettings":
        service_name = os.getenv("SERVICE_NAME", "weather-poller")
        components = _components_env("WEATHER_POLL_COMPONENTS", frozenset({"weather", "modeled_aq"}))
        return cls(
            service_name=service_name,
            log_format=os.getenv("LOG_FORMAT", "json"),
            database_url=_sync_database_url(),
            kafka=KafkaSettings.from_env(service_name=service_name),
            poll_interval_seconds=_int_env("WEATHER_POLL_INTERVAL_SECONDS", 900),
            components=components,
            weather_forecast_days=_int_env("WEATHER_FORECAST_DAYS", 3),
            weather_past_days=_int_env("WEATHER_PAST_DAYS", 1),
            modeled_aq_forecast_days=_int_env("MODELED_AQ_FORECAST_DAYS", 3),
            modeled_aq_past_days=_int_env("MODELED_AQ_PAST_DAYS", 1),
            max_locations=_int_env("WEATHER_MAX_LOCATIONS", 0),
            publish_kafka=_bool_env("WEATHER_PUBLISH_KAFKA", False),
            http_timeout_seconds=_float_env("OPENMETEO_HTTP_TIMEOUT_SECONDS", 15.0),
            http_retries=_int_env("OPENMETEO_HTTP_RETRIES", 2),
            health_host=os.getenv("WEATHER_HEALTH_HOST", "0.0.0.0"),
            health_port=_int_env("WEATHER_HEALTH_PORT", 9091),
            pipeline_component=os.getenv("WEATHER_PIPELINE_COMPONENT", service_name.replace("-", "_")),
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


def _components_env(name: str, default: frozenset[str]) -> frozenset[str]:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    components = frozenset(part.strip() for part in raw.split(",") if part.strip())
    allowed = {"weather", "modeled_aq"}
    unknown = components - allowed
    if unknown:
        raise ValueError(f"{name} contains unsupported component(s): {', '.join(sorted(unknown))}")
    if not components:
        raise ValueError(f"{name} must include at least one component")
    return components


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
