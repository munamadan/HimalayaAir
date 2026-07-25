from __future__ import annotations

from datetime import datetime, timedelta

from services.forecasting.config import ForecastSettings
from services.forecasting.models import (
    ForecastContext,
    ForecastPoint,
    ForecastResult,
    ModelSelection,
    WeatherCovariates,
)
from services.forecasting.persistence import _clamp_aqi

ML_PLACEHOLDER_FEATURE_NAMES = (
    "lag_aqi_1h",
    "lag_aqi_24h",
    "rolling_aqi_24h",
    "hour_of_day",
    "temp",
    "humidity",
    "wind_speed",
    "precipitation",
    "modeled_aqi",
    "horizon_hours",
)


def build_ml_placeholder_forecast(
    context: ForecastContext, settings: ForecastSettings, selection: ModelSelection
) -> ForecastResult:
    points: list[ForecastPoint] = []
    for horizon in range(1, settings.horizon_hours + 1):
        features = build_placeholder_feature_vector(context, settings, horizon)
        predicted = _predict_placeholder_aqi(context, settings, features)
        spread = _placeholder_spread(context.persistence_baseline.aqi, horizon)
        points.append(
            ForecastPoint(
                station_id=context.station_id,
                pollutant=context.pollutant,
                target_timestamp=context.generated_at + timedelta(hours=horizon),
                horizon_hours=horizon,
                predicted_aqi=predicted,
                lower_bound=float(_clamp_aqi(predicted - spread)),
                upper_bound=float(_clamp_aqi(predicted + spread)),
            )
        )

    return ForecastResult(
        station_id=context.station_id,
        pollutant=context.pollutant,
        generated_at=context.generated_at,
        model_name=selection.model.value,
        model_source=selection.model_source,
        fallback_reason=selection.fallback_reason,
        points=tuple(points),
    )


def build_placeholder_feature_vector(
    context: ForecastContext, settings: ForecastSettings, horizon: int
) -> dict[str, float]:
    target_timestamp = context.generated_at + timedelta(hours=horizon)
    observed_by_timestamp = {
        point.timestamp: point.aqi for point in context.observed_history
    }
    latest_observed_at = max(observed_by_timestamp, default=None)
    baseline = float(context.persistence_baseline.aqi)
    lag_1h = float(
        observed_by_timestamp.get(context.generated_at - timedelta(hours=1), baseline)
    )
    lag_24h = float(
        observed_by_timestamp.get(context.generated_at - timedelta(hours=24), baseline)
    )
    recent_24h = [
        point.aqi
        for point in context.observed_history
        if latest_observed_at is not None
        and point.timestamp > latest_observed_at - timedelta(hours=24)
    ]
    rolling_24h = float(sum(recent_24h) / len(recent_24h)) if recent_24h else baseline
    weather = _future_weather_by_timestamp(context.future_weather).get(target_timestamp)
    modeled_aqi = {point.timestamp: point.aqi for point in context.modeled_future}.get(
        target_timestamp, baseline
    )
    return {
        "lag_aqi_1h": lag_1h,
        "lag_aqi_24h": lag_24h,
        "rolling_aqi_24h": rolling_24h,
        "hour_of_day": float(target_timestamp.hour),
        "temp": weather.temp if weather is not None else 20.0,
        "humidity": weather.humidity if weather is not None else 65.0,
        "wind_speed": weather.wind_speed if weather is not None else 4.0,
        "precipitation": weather.precipitation if weather is not None else 0.0,
        "modeled_aqi": float(modeled_aqi),
        "horizon_hours": float(horizon),
    }


def _predict_placeholder_aqi(
    context: ForecastContext, settings: ForecastSettings, features: dict[str, float]
) -> int:
    baseline = float(context.persistence_baseline.aqi)
    horizon = features["horizon_hours"]
    history_weight = max(
        0.25, 1.0 - (horizon / max(float(settings.horizon_hours), 1.0)) * 0.45
    )
    station_offset = ((context.station_id % 7) - 3) * 1.5
    diurnal_adjustment = _diurnal_adjustment(int(features["hour_of_day"])) * max(
        0.35, 1.0 - horizon / 96.0
    )
    weather_adjustment = _weather_adjustment(features) * max(
        0.40, 1.0 - horizon / 120.0
    )
    predicted = (
        baseline * 0.45
        + features["lag_aqi_1h"] * 0.20 * history_weight
        + features["lag_aqi_24h"] * 0.15 * history_weight
        + features["rolling_aqi_24h"] * 0.10 * history_weight
        + features["modeled_aqi"] * 0.10
        + diurnal_adjustment
        + weather_adjustment
        + station_offset
    )
    return _clamp_aqi(predicted)


def _diurnal_adjustment(hour: int) -> float:
    if 7 <= hour <= 10:
        return 14.0
    if 18 <= hour <= 21:
        return 11.0
    if 0 <= hour <= 5:
        return -3.0
    if 12 <= hour <= 16:
        return -7.0
    return 2.0


def _weather_adjustment(features: dict[str, float]) -> float:
    wind_relief = -min(18.0, max(0.0, features["wind_speed"] - 5.0) * 2.2)
    rain_relief = -min(25.0, max(0.0, features["precipitation"]) * 4.0)
    humidity_pressure = 5.0 if features["humidity"] >= 85.0 else 0.0
    heat_pressure = 4.0 if features["temp"] >= 32.0 else 0.0
    return wind_relief + rain_relief + humidity_pressure + heat_pressure


def _placeholder_spread(baseline_aqi: int, horizon: int) -> int:
    return min(140, max(18, round(baseline_aqi * 0.10)) + round(horizon * 1.6))


def _future_weather_by_timestamp(
    points: tuple[WeatherCovariates, ...],
) -> dict[datetime, WeatherCovariates]:
    return {point.timestamp: point for point in points}
