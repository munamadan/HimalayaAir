from __future__ import annotations

from datetime import datetime, timedelta

from confluent_kafka import Producer

from shared.enums import Confidence, CoverageMode, ObservationType, SourceName
from shared.kafka.client import create_producer, produce_message
from shared.kafka.messages import RawAQReadingMessage
from shared.settings import KafkaSettings
from shared.time_utils import ensure_utc, utc_now

from services.openaq_poller.models import OpenAQMeasurement, SensorRegistryRow


class OpenAQReadingPublisher:
    def __init__(self, settings: KafkaSettings, *, logger: object | None = None) -> None:
        self.settings = settings
        self.logger = logger
        self.producer: Producer = create_producer(settings)

    def publish(self, messages: list[RawAQReadingMessage]) -> int:
        for message in messages:
            produce_message(
                self.producer,
                topic=self.settings.topics.raw_aq_readings,
                key=message.message_key(),
                message=message,
                logger=self.logger,
            )
        return len(messages)


def build_raw_message(
    *,
    sensor: SensorRegistryRow,
    measurement: OpenAQMeasurement,
    now: datetime | None = None,
) -> RawAQReadingMessage:
    coverage_mode, confidence = _observed_mode(measurement.timestamp, now=now or utc_now())
    return RawAQReadingMessage(
        source=SourceName.OPENAQ_LIVE,
        observation_type=ObservationType.OBSERVED,
        station_id=sensor.station_id,
        sensor_id=sensor.sensor_id,
        openaq_location_id=sensor.external_location_id or measurement.openaq_location_id,
        openaq_sensor_id=sensor.external_sensor_id,
        station_name=sensor.station_name,
        pollutant=measurement.pollutant or sensor.pollutant,
        value=measurement.value,
        unit=measurement.unit or sensor.unit or "unknown",
        timestamp=measurement.timestamp,
        latitude=measurement.latitude if measurement.latitude is not None else sensor.latitude,
        longitude=measurement.longitude if measurement.longitude is not None else sensor.longitude,
        quality_flag="openaq_flagged" if measurement.has_flags else "raw",
        coverage_mode=coverage_mode,
        confidence=confidence,
        original_timestamp=measurement.timestamp,
    )


def deduplicate_messages(messages: list[RawAQReadingMessage]) -> list[RawAQReadingMessage]:
    deduped: dict[str, RawAQReadingMessage] = {}
    for message in messages:
        deduped[message.message_key()] = message
    return list(deduped.values())


def _observed_mode(timestamp: datetime, *, now: datetime) -> tuple[CoverageMode, Confidence]:
    age = ensure_utc(now) - ensure_utc(timestamp)
    if age <= timedelta(hours=2):
        return CoverageMode.LIVE_OBSERVED, Confidence.HIGH
    return CoverageMode.RECENT_OBSERVED, Confidence.MEDIUM
