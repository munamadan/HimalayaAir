from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class WeatherLocation:
    location_id: int
    name: str
    latitude: float
    longitude: float
    elevation: int | None


@dataclass(frozen=True)
class WeatherReading:
    location_id: int
    location_name: str
    latitude: float
    longitude: float
    temp: float | None
    humidity: float | None
    wind_speed: float | None
    wind_dir: float | None
    precipitation: float | None
    timestamp: datetime
    source: str = "openmeteo_weather"
    quality_flag: str = "complete"


@dataclass(frozen=True)
class ModeledAQReading:
    model_location_id: int
    location_name: str
    latitude: float
    longitude: float
    pollutant: str
    value: float | None
    unit: str | None
    us_aqi: int | None
    timestamp: datetime
    model_run_at: datetime
    quality_flag: str
    source: str = "openmeteo_cams"
    observation_type: str = "modeled"
    coverage_mode: str = "MODELED_BASELINE"


@dataclass(frozen=True)
class WeatherPollRunResult:
    status: str
    records_processed: int
    locations_attempted: int
    locations_succeeded: int
    locations_failed: int
    weather_records: int
    modeled_aq_records: int
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    dry_run: bool
    error_message: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
