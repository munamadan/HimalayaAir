from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from shared.enums import Confidence, CoverageMode, ObservationType


class APIModel(BaseModel):
    model_config = ConfigDict(use_enum_values=True, validate_default=True)


class CoverageMetadata(APIModel):
    coverage_mode: CoverageMode
    confidence: Confidence
    fresh_station_count: int = Field(ge=0)
    recent_station_count: int = Field(ge=0)
    modeled_available: bool
    replay_active: bool = False
    message: str | None = None


class StationSummary(APIModel):
    id: int
    name: str
    lat: float
    lon: float
    active: bool
    status: str
    last_seen: datetime | None = None
    current_aqi: int | None = Field(default=None, ge=0)
    dominant_pollutant: str | None = None
    source: str | None = None
    observation_type: ObservationType | None = None
    coverage_mode: CoverageMode | None = None
    confidence: Confidence | None = None
    freshness_minutes: int | None = Field(default=None, ge=0)
    health_category: str | None = None


class StationsResponse(CoverageMetadata):
    timestamp: datetime
    valley_composite_aqi: int | None = Field(default=None, ge=0)
    stations: list[StationSummary]


class StationIdentity(APIModel):
    id: int
    name: str
    lat: float
    lon: float
    active: bool
    status: str
    last_seen: datetime | None = None


class PollutantCurrent(APIModel):
    pollutant: str
    value: float
    unit: str
    aqi: int | None = Field(default=None, ge=0)
    timestamp: datetime
    freshness_minutes: int | None = Field(default=None, ge=0)
    is_anomaly: bool
    anomaly_reason: str | None = None
    quality_flag: str
    source: str
    observation_type: ObservationType
    coverage_mode: CoverageMode | None = None
    confidence: Confidence | None = None
    health_category: str | None = None


class StationCurrentResponse(CoverageMetadata):
    station: StationIdentity
    current_aqi: int | None = Field(default=None, ge=0)
    dominant_pollutant: str | None = None
    readings: list[PollutantCurrent]


class HistoryPoint(APIModel):
    timestamp: datetime
    pollutant: str
    value: float
    unit: str
    aqi: int | None = Field(default=None, ge=0)
    is_anomaly: bool
    quality_flag: str
    source: str
    observation_type: ObservationType
    coverage_mode: CoverageMode | None = None
    confidence: Confidence | None = None


class StationHistoryResponse(APIModel):
    station_id: int
    pollutant: str | None = None
    hours: int
    readings: list[HistoryPoint]


class ValleyCurrentResponse(CoverageMetadata):
    timestamp: datetime | None = None
    composite_aqi: int | None = Field(default=None, ge=0)
    dominant_pollutant: str | None = None
    recommendation: str
    source: str | None = None


class ValleyHistoryPoint(APIModel):
    bucket_start: datetime
    pollutant: str
    avg_aqi: float | None = None
    max_aqi: int | None = Field(default=None, ge=0)
    station_count: int = Field(ge=0)
    reading_count: int = Field(ge=0)


class ValleyHistoryResponse(APIModel):
    pollutant: str | None = None
    hours: int
    granularity: str
    points: list[ValleyHistoryPoint]


class GridBounds(APIModel):
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float


class InterpolationGrid(APIModel):
    rows: int
    cols: int
    bounds: GridBounds
    values: list[list[float | None]]


class InterpolationResponse(APIModel):
    grid: InterpolationGrid
    station_count: int = Field(ge=0)
    coverage_mode: CoverageMode
    confidence: Confidence
    source: str
    computed_at: datetime
    insufficient_data: bool
    message: str


class NearestStation(APIModel):
    id: int
    name: str
    lat: float
    lon: float
    distance_km: float
    current_aqi: int | None = Field(default=None, ge=0)


class HealthAdvisoryResponse(CoverageMetadata):
    aqi: int | None = Field(default=None, ge=0)
    category: str | None = None
    recommendation: str
    nearest_station: NearestStation | None = None


class FireEvent(APIModel):
    id: int
    lat: float
    lon: float
    acq_date: date
    acq_time: int | None = None
    satellite: str | None = None
    instrument: str | None = None
    confidence: str | None = None
    frp: float | None = None
    brightness: float | None = None
    source: str
    event_hash: str
    distance_km: float | None = None


class EventsResponse(APIModel):
    events: list[FireEvent]
    count: int = Field(ge=0)


class WindRoseBin(APIModel):
    direction_start: int = Field(ge=0, le=359)
    direction_end: int = Field(ge=1, le=360)
    avg_speed: float | None = Field(default=None, ge=0)
    sample_count: int = Field(ge=0)


class WindRoseResponse(APIModel):
    hours: int = Field(ge=1, le=24 * 31)
    bins: list[WindRoseBin]
    total_samples: int = Field(ge=0)


class ForecastPoint(APIModel):
    target_timestamp: datetime
    horizon_hours: int = Field(ge=1)
    predicted_aqi: int = Field(ge=0)
    lower_bound: float | None = None
    upper_bound: float | None = None


class ForecastResponse(APIModel):
    station_id: int
    pollutant: str
    generated_at: datetime
    model: str
    model_source: str
    fallback_reason: str | None = None
    historical_mae: float | None = None
    forecasts: list[ForecastPoint]


class PipelineRunHealth(APIModel):
    component: str
    run_at: datetime | None = None
    status: str
    records_processed: int | None = None
    error_message: str | None = None
    duration_seconds: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineHealthResponse(APIModel):
    status: str
    service: str
    timestamp: datetime
    checks: dict[str, Any]
    pipeline_runs: list[PipelineRunHealth]
    coverage: CoverageMetadata


class BasicHealthResponse(APIModel):
    status: str
    service: str
    timestamp: datetime
    checks: dict[str, Any]


class WebSocketEvent(APIModel):
    event: str
    timestamp: datetime
    data: dict[str, Any] = Field(default_factory=dict)
