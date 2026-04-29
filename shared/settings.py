from __future__ import annotations

import os
from dataclasses import dataclass

from shared.kafka.topics import KafkaTopics


@dataclass(frozen=True)
class KafkaSettings:
    bootstrap_servers: str
    client_id: str
    group_id: str
    request_timeout_ms: int
    delivery_timeout_ms: int
    consumer_poll_timeout_seconds: float
    topics: KafkaTopics

    @classmethod
    def from_env(cls, *, service_name: str = "himalayaair") -> "KafkaSettings":
        return cls(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092"),
            client_id=os.getenv("KAFKA_CLIENT_ID", service_name),
            group_id=os.getenv("KAFKA_GROUP_ID", f"{service_name}-verify"),
            request_timeout_ms=_int_env("KAFKA_REQUEST_TIMEOUT_MS", 10_000),
            delivery_timeout_ms=_int_env("KAFKA_DELIVERY_TIMEOUT_MS", 30_000),
            consumer_poll_timeout_seconds=_float_env("KAFKA_CONSUMER_POLL_TIMEOUT_SECONDS", 1.0),
            topics=KafkaTopics.from_env(),
        )


@dataclass(frozen=True)
class AppSettings:
    service_name: str
    log_format: str
    kafka: KafkaSettings

    @classmethod
    def from_env(cls, *, service_name: str = "himalayaair") -> "AppSettings":
        resolved_service_name = os.getenv("SERVICE_NAME", service_name)
        return cls(
            service_name=resolved_service_name,
            log_format=os.getenv("LOG_FORMAT", "json"),
            kafka=KafkaSettings.from_env(service_name=resolved_service_name),
        )


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc

