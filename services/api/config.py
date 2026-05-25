from __future__ import annotations

import os
from dataclasses import dataclass

from shared.kafka.topics import KafkaTopics


DEFAULT_DATABASE_URL = "postgresql+asyncpg://himalayaair:himalayaair@localhost:55432/himalayaair"


@dataclass(frozen=True)
class ApiSettings:
    service_name: str
    log_format: str
    database_url: str
    allowed_origins: tuple[str, ...]
    fresh_hours: int
    recent_hours: int
    modeled_hours: int
    station_cache_ttl_seconds: float
    idw_cache_ttl_seconds: float
    idw_rows: int
    idw_cols: int
    idw_power: float
    websocket_heartbeat_seconds: float
    kafka_consumer_enabled: bool
    kafka_health_enabled: bool
    external_health_enabled: bool
    kafka_bootstrap_servers: str
    kafka_group_id: str
    processed_aq_topic: str
    kafka_retry_seconds: float
    openaq_health_url: str
    weather_health_url: str
    modeled_aq_health_url: str
    worker_health_url: str
    external_health_mode: str
    external_health_timeout_seconds: float

    @classmethod
    def from_env(cls) -> "ApiSettings":
        service_name = os.getenv("SERVICE_NAME", "himalayaair-api")
        topics = KafkaTopics.from_env()
        return cls(
            service_name=service_name,
            log_format=os.getenv("LOG_FORMAT", "json"),
            database_url=normalize_async_database_url(os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)),
            allowed_origins=_csv_env("ALLOWED_ORIGINS", "http://localhost:3000"),
            fresh_hours=_int_env("API_FRESH_HOURS", 2),
            recent_hours=_int_env("API_RECENT_HOURS", 24),
            modeled_hours=_int_env("API_MODELED_HOURS", 24),
            station_cache_ttl_seconds=_float_env("API_STATION_CACHE_TTL_SECONDS", 20.0),
            idw_cache_ttl_seconds=_float_env("API_IDW_CACHE_TTL_SECONDS", 30.0),
            idw_rows=_int_env("API_IDW_ROWS", 50),
            idw_cols=_int_env("API_IDW_COLS", 50),
            idw_power=_float_env("API_IDW_POWER", 2.0),
            websocket_heartbeat_seconds=_float_env("API_WEBSOCKET_HEARTBEAT_SECONDS", 20.0),
            kafka_consumer_enabled=_bool_env("API_KAFKA_CONSUMER_ENABLED", True),
            kafka_health_enabled=_bool_env("API_KAFKA_HEALTH_ENABLED", False),
            external_health_enabled=_bool_env("API_EXTERNAL_HEALTH_ENABLED", True),
            kafka_bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092"),
            kafka_group_id=os.getenv("API_KAFKA_GROUP_ID", "himalayaair-api-live-feed"),
            processed_aq_topic=os.getenv("KAFKA_PROCESSED_AQ_READINGS_TOPIC", topics.processed_aq_readings),
            kafka_retry_seconds=_float_env("API_KAFKA_RETRY_SECONDS", 5.0),
            openaq_health_url=os.getenv("API_OPENAQ_HEALTH_URL", "http://openaq-poller:9090/health"),
            weather_health_url=os.getenv("API_WEATHER_HEALTH_URL", "http://weather-poller:9091/health"),
            modeled_aq_health_url=os.getenv("API_MODELED_AQ_HEALTH_URL", "http://openmeteo-aq-poller:9092/health"),
            worker_health_url=os.getenv("API_WORKER_HEALTH_URL", "http://worker:9093/health"),
            external_health_mode=os.getenv("API_EXTERNAL_HEALTH_MODE", "worker").strip().lower(),
            external_health_timeout_seconds=_float_env("API_EXTERNAL_HEALTH_TIMEOUT_SECONDS", 2.0),
        )


def normalize_async_database_url(value: str | None) -> str:
    if value is None or not value.strip():
        return DEFAULT_DATABASE_URL
    normalized = value.strip()
    if normalized.startswith("postgresql+asyncpg://"):
        return normalized
    if normalized.startswith("postgresql+psycopg2://"):
        return normalized.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if normalized.startswith("postgresql://"):
        return normalized.replace("postgresql://", "postgresql+asyncpg://", 1)
    return normalized


def _csv_env(name: str, default: str) -> tuple[str, ...]:
    raw_value = os.getenv(name, default)
    values = tuple(item.strip() for item in raw_value.split(",") if item.strip())
    return values or tuple(item.strip() for item in default.split(",") if item.strip())


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")
