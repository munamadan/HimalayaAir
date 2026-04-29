from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from shared.enums import Confidence, CoverageMode, ObservationType, SourceName
from shared.time_utils import ensure_utc, utc_now


SCHEMA_VERSION = "1.0"
MessageT = TypeVar("MessageT", bound="KafkaMessage")


class KafkaMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True, validate_default=True)

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    source: SourceName
    observation_type: ObservationType

    @field_validator(
        "timestamp",
        "original_timestamp",
        "ingested_at",
        "processed_at",
        "fetched_at",
        "model_run_at",
        "failed_at",
        mode="after",
        check_fields=False,
    )
    @classmethod
    def _ensure_datetimes_are_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    def to_json_bytes(self) -> bytes:
        return self.model_dump_json().encode("utf-8")


class PollutantMixin(BaseModel):
    pollutant: str = Field(min_length=1, max_length=20)

    @field_validator("pollutant")
    @classmethod
    def _normalize_pollutant(cls, value: str) -> str:
        normalized = value.strip().lower().replace(".", "").replace("_", "")
        aliases = {
            "pm25": "pm25",
            "pm10": "pm10",
            "co": "co",
            "carbonmonoxide": "co",
            "no2": "no2",
            "nitrogendioxide": "no2",
            "o3": "o3",
            "ozone": "o3",
            "so2": "so2",
            "sulphurdioxide": "so2",
            "sulfurdioxide": "so2",
        }
        return aliases.get(normalized, normalized)


class RawAQReadingMessage(PollutantMixin, KafkaMessage):
    station_id: int | None = Field(default=None, ge=1)
    sensor_id: int | None = Field(default=None, ge=1)
    openaq_location_id: int | None = Field(default=None, ge=1)
    openaq_sensor_id: int | None = Field(default=None, ge=1)
    station_name: str | None = Field(default=None, max_length=200)
    value: float
    unit: str = Field(min_length=1, max_length=30)
    timestamp: datetime
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    quality_flag: str = Field(default="raw", min_length=1, max_length=50)
    coverage_mode: CoverageMode | None = None
    confidence: Confidence | None = None
    original_timestamp: datetime | None = None
    ingested_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _require_sensor_identity(self) -> "RawAQReadingMessage":
        if self.sensor_id is None and self.openaq_sensor_id is None:
            raise ValueError("sensor_id or openaq_sensor_id is required")
        if self.station_id is None and self.openaq_location_id is None:
            raise ValueError("station_id or openaq_location_id is required")
        return self

    def message_key(self) -> str:
        station = self.station_id if self.station_id is not None else self.openaq_location_id
        sensor = self.sensor_id if self.sensor_id is not None else self.openaq_sensor_id
        return f"{station}:{sensor}:{self.pollutant}:{self.timestamp.isoformat()}"


class ProcessedAQReadingMessage(PollutantMixin, KafkaMessage):
    station_id: int = Field(ge=1)
    sensor_id: int = Field(ge=1)
    district_id: int | None = Field(default=None, ge=1)
    value: float
    unit: str = Field(min_length=1, max_length=30)
    aqi: int | None = Field(default=None, ge=0)
    timestamp: datetime
    is_anomaly: bool = False
    anomaly_reason: str | None = Field(default=None, max_length=80)
    quality_flag: str = Field(default="processed", min_length=1, max_length=50)
    coverage_mode: CoverageMode
    confidence: Confidence
    processed_at: datetime = Field(default_factory=utc_now)

    def message_key(self) -> str:
        return f"{self.station_id}:{self.sensor_id}:{self.pollutant}:{self.timestamp.isoformat()}"


class WeatherDataMessage(KafkaMessage):
    location_id: int | None = Field(default=None, ge=1)
    location_name: str = Field(min_length=1, max_length=120)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    temp: float | None = None
    humidity: float | None = Field(default=None, ge=0, le=100)
    wind_speed: float | None = Field(default=None, ge=0)
    wind_dir: float | None = Field(default=None, ge=0, le=360)
    precipitation: float | None = Field(default=None, ge=0)
    timestamp: datetime
    fetched_at: datetime = Field(default_factory=utc_now)

    def message_key(self) -> str:
        location = self.location_id if self.location_id is not None else self.location_name
        return f"{location}:{self.timestamp.isoformat()}"


class ModeledAQDataMessage(PollutantMixin, KafkaMessage):
    model_location_id: int | None = Field(default=None, ge=1)
    location_name: str = Field(min_length=1, max_length=120)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    value: float | None = None
    unit: str | None = Field(default=None, max_length=30)
    us_aqi: int | None = Field(default=None, ge=0)
    timestamp: datetime
    model_run_at: datetime = Field(default_factory=utc_now)
    coverage_mode: CoverageMode = CoverageMode.MODELED_BASELINE

    @model_validator(mode="after")
    def _require_modeled_provenance(self) -> "ModeledAQDataMessage":
        if self.source != SourceName.OPENMETEO_CAMS.value:
            raise ValueError("modeled AQ messages must use source=openmeteo_cams")
        if self.observation_type != ObservationType.MODELED.value:
            raise ValueError("modeled AQ messages must use observation_type=modeled")
        if self.coverage_mode != CoverageMode.MODELED_BASELINE.value:
            raise ValueError("modeled AQ messages must use coverage_mode=MODELED_BASELINE")
        return self

    def message_key(self) -> str:
        location = self.model_location_id if self.model_location_id is not None else self.location_name
        return f"{location}:{self.pollutant}:{self.timestamp.isoformat()}:{self.model_run_at.isoformat()}"


class DLQMessage(KafkaMessage):
    original_topic: str = Field(min_length=1)
    original_key: str | None = None
    original_payload: dict[str, Any] | list[Any] | str
    error_type: str = Field(min_length=1, max_length=120)
    error_message: str = Field(min_length=1)
    failed_at: datetime = Field(default_factory=utc_now)
    retry_count: int = Field(default=0, ge=0)

    def message_key(self) -> str:
        original_key = self.original_key or "no-key"
        return f"{self.original_topic}:{original_key}:{self.failed_at.isoformat()}"


def message_to_json(message: KafkaMessage) -> str:
    return message.model_dump_json()


def message_from_json(model_type: type[MessageT], payload: bytes | str) -> MessageT:
    raw_payload = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    return model_type.model_validate_json(raw_payload)


def load_message_fixture(path: str) -> RawAQReadingMessage:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return RawAQReadingMessage.model_validate(payload)
