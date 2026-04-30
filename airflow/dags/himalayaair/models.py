from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class StationSensorTarget:
    sensor_id: int
    station_id: int
    external_sensor_id: str
    external_location_id: str | None
    pollutant: str
    unit: str | None
    station_name: str
    latitude: float | None
    longitude: float | None


@dataclass(frozen=True)
class AQBackfillReading:
    sensor_id: int
    station_id: int
    pollutant: str
    value: float
    unit: str
    aqi: int | None
    timestamp: datetime
    quality_flag: str
    observation_type: str
    source: str
    coverage_mode: str
    confidence: str
    original_timestamp: datetime | None = None


@dataclass(frozen=True)
class BackfillManifestResult:
    source: str
    external_location_id: str | None
    external_sensor_id: str | None
    date: date
    status: str
    rows_fetched: int
    rows_written: int
    error_message: str | None = None


@dataclass(frozen=True)
class PipelineOutcome:
    component: str
    status: str
    records_processed: int
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    metadata: dict[str, object] = field(default_factory=dict)
    error_message: str | None = None


@dataclass(frozen=True)
class FireEvent:
    latitude: float
    longitude: float
    acq_date: date
    acq_time: int | None
    satellite: str | None
    instrument: str | None
    confidence: str | None
    frp: float | None
    brightness: float | None
    source: str
    event_hash: str


@dataclass(frozen=True)
class DataQualityState:
    state: str
    coverage_mode: str
    confidence: str
    fresh_station_count: int
    recent_station_count: int
    modeled_available: bool
    replay_active: bool
    invalid_value_count: int
    anomaly_rate: float | None
    dead_sensors_deactivated: int
    message: str
