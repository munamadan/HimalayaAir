from __future__ import annotations

from datetime import timedelta
from statistics import median

from services.forecasting.config import ForecastSettings
from services.forecasting.models import ForecastContext, ForecastPoint, ForecastResult, ModelSelection
from services.forecasting.persistence import _clamp_aqi


def build_modeled_bias_forecast(context: ForecastContext, settings: ForecastSettings, selection: ModelSelection) -> ForecastResult:
    bias = _median_observed_modeled_bias(context)
    points: list[ForecastPoint] = []
    modeled_by_timestamp = {point.timestamp: point for point in context.modeled_future}
    for horizon in range(1, settings.horizon_hours + 1):
        target_timestamp = context.generated_at + timedelta(hours=horizon)
        modeled = modeled_by_timestamp.get(target_timestamp)
        predicted = _clamp_aqi((modeled.aqi if modeled is not None else context.persistence_baseline.aqi) + bias)
        spread = max(12, round(abs(bias))) + max(8, round(predicted * 0.12))
        points.append(
            ForecastPoint(
                station_id=context.station_id,
                pollutant=context.pollutant,
                target_timestamp=target_timestamp,
                horizon_hours=horizon,
                predicted_aqi=predicted,
                lower_bound=float(_clamp_aqi(predicted - spread)),
                upper_bound=float(_clamp_aqi(predicted + spread)),
            )
        )

    fallback_reason = selection.fallback_reason
    if not _bias_pairs(context):
        missing_bias_reason = "No overlapping observed and modeled history was available for bias adjustment; using zero modeled bias."
        fallback_reason = f"{fallback_reason}; {missing_bias_reason}" if fallback_reason else missing_bias_reason

    return ForecastResult(
        station_id=context.station_id,
        pollutant=context.pollutant,
        generated_at=context.generated_at,
        model_name=selection.model.value,
        model_source=selection.model_source,
        fallback_reason=fallback_reason,
        points=tuple(points),
    )


def _median_observed_modeled_bias(context: ForecastContext) -> float:
    pairs = _bias_pairs(context)
    if not pairs:
        return 0.0
    return float(median(observed - modeled for observed, modeled in pairs))


def _bias_pairs(context: ForecastContext) -> list[tuple[float, float]]:
    modeled_by_timestamp = {point.timestamp: point.aqi for point in context.modeled_history}
    return [(point.aqi, modeled_by_timestamp[point.timestamp]) for point in context.observed_history if point.timestamp in modeled_by_timestamp]

