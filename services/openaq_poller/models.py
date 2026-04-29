from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class SensorRegistryRow:
    station_id: int
    sensor_id: int
    external_sensor_id: int
    external_location_id: int | None
    pollutant: str
    unit: str | None
    station_name: str
    latitude: float | None
    longitude: float | None


@dataclass(frozen=True)
class OpenAQMeasurement:
    openaq_sensor_id: int
    openaq_location_id: int | None
    pollutant: str
    unit: str | None
    value: float
    timestamp: datetime
    latitude: float | None = None
    longitude: float | None = None
    has_flags: bool | None = None


@dataclass(frozen=True)
class PollWindow:
    datetime_from: datetime
    datetime_to: datetime


@dataclass(frozen=True)
class PollRunResult:
    status: str
    records_processed: int
    sensors_attempted: int
    sensors_succeeded: int
    sensors_failed: int
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    dry_run: bool
    window: PollWindow | None = None
    error_message: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

