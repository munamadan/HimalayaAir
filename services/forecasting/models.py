from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ForecastModel(str, Enum):
    SARIMAX = "sarimax"
    MODELED_BIAS = "openmeteo_cams_bias_adjusted"
    PERSISTENCE = "persistence"


@dataclass(frozen=True)
class HourlyAQI:
    timestamp: datetime
    aqi: float


@dataclass(frozen=True)
class WeatherCovariates:
    timestamp: datetime
    temp: float
    humidity: float
    wind_speed: float
    wind_dir: float
    precipitation: float

    def as_vector(self) -> tuple[float, float, float, float, float]:
        return (self.temp, self.humidity, self.wind_speed, self.wind_dir, self.precipitation)


@dataclass(frozen=True)
class ModeledAQI:
    timestamp: datetime
    aqi: float


@dataclass(frozen=True)
class PersistenceBaseline:
    aqi: int
    source: str
    timestamp: datetime | None


@dataclass(frozen=True)
class ForecastContext:
    station_id: int
    station_name: str
    pollutant: str
    generated_at: datetime
    weather_location_id: int | None
    observed_history: tuple[HourlyAQI, ...]
    weather_history: tuple[WeatherCovariates, ...]
    future_weather: tuple[WeatherCovariates, ...]
    modeled_history: tuple[ModeledAQI, ...]
    modeled_future: tuple[ModeledAQI, ...]
    persistence_baseline: PersistenceBaseline


@dataclass(frozen=True)
class ModelSelection:
    model: ForecastModel
    model_source: str
    fallback_reason: str | None
    sarimax_rejection_reasons: tuple[str, ...]


@dataclass(frozen=True)
class ForecastPoint:
    station_id: int
    pollutant: str
    target_timestamp: datetime
    horizon_hours: int
    predicted_aqi: int
    lower_bound: float
    upper_bound: float


@dataclass(frozen=True)
class ForecastResult:
    station_id: int
    pollutant: str
    generated_at: datetime
    model_name: str
    model_source: str
    fallback_reason: str | None
    points: tuple[ForecastPoint, ...]


@dataclass(frozen=True)
class ForecastRunResult:
    status: str
    forecast_run_id: int | None
    stations_attempted: int
    stations_succeeded: int
    forecasts_written: int
    accuracy_records_written: int
    fallback_reason: str | None
    error_message: str | None = None

