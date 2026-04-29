from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TopicDefinition:
    name: str
    partitions: int
    retention_ms: int
    message_key: str


@dataclass(frozen=True)
class KafkaTopics:
    raw_aq_readings: str = "raw-aq-readings"
    weather_data: str = "weather-data"
    modeled_aq_data: str = "modeled-aq-data"
    processed_aq_readings: str = "processed-aq-readings"
    raw_aq_readings_dlq: str = "raw-aq-readings-dlq"
    pipeline_events: str = "pipeline-events"

    @classmethod
    def from_env(cls) -> "KafkaTopics":
        return cls(
            raw_aq_readings=os.getenv("KAFKA_TOPIC_RAW_AQ_READINGS", cls.raw_aq_readings),
            weather_data=os.getenv("KAFKA_TOPIC_WEATHER_DATA", cls.weather_data),
            modeled_aq_data=os.getenv("KAFKA_TOPIC_MODELED_AQ_DATA", cls.modeled_aq_data),
            processed_aq_readings=os.getenv(
                "KAFKA_TOPIC_PROCESSED_AQ_READINGS",
                cls.processed_aq_readings,
            ),
            raw_aq_readings_dlq=os.getenv("KAFKA_TOPIC_RAW_AQ_READINGS_DLQ", cls.raw_aq_readings_dlq),
            pipeline_events=os.getenv("KAFKA_TOPIC_PIPELINE_EVENTS", cls.pipeline_events),
        )


TOPIC_DEFINITIONS = (
    TopicDefinition(
        name="raw-aq-readings",
        partitions=3,
        retention_ms=86_400_000,
        message_key="station_id:sensor_id:pollutant:timestamp",
    ),
    TopicDefinition(
        name="weather-data",
        partitions=1,
        retention_ms=86_400_000,
        message_key="location_id:timestamp",
    ),
    TopicDefinition(
        name="modeled-aq-data",
        partitions=1,
        retention_ms=259_200_000,
        message_key="model_location_id:pollutant:timestamp:model_run_at",
    ),
    TopicDefinition(
        name="processed-aq-readings",
        partitions=1,
        retention_ms=86_400_000,
        message_key="station_id:sensor_id:pollutant:timestamp",
    ),
    TopicDefinition(
        name="raw-aq-readings-dlq",
        partitions=1,
        retention_ms=604_800_000,
        message_key="original_topic:original_key:failed_at",
    ),
    TopicDefinition(
        name="pipeline-events",
        partitions=1,
        retention_ms=86_400_000,
        message_key="component:event_type:created_at",
    ),
)
