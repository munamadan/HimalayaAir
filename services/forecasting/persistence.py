from __future__ import annotations

from datetime import timedelta

from services.forecasting.config import ForecastSettings
from services.forecasting.models import ForecastContext, ForecastPoint, ForecastResult, ModelSelection


def build_persistence_forecast(context: ForecastContext, settings: ForecastSettings, selection: ModelSelection) -> ForecastResult:
    baseline = _clamp_aqi(context.persistence_baseline.aqi)
    spread = max(15, round(baseline * 0.20))
    points = tuple(
        ForecastPoint(
            station_id=context.station_id,
            pollutant=context.pollutant,
            target_timestamp=context.generated_at + timedelta(hours=horizon),
            horizon_hours=horizon,
            predicted_aqi=baseline,
            lower_bound=float(_clamp_aqi(baseline - spread)),
            upper_bound=float(_clamp_aqi(baseline + spread)),
        )
        for horizon in range(1, settings.horizon_hours + 1)
    )
    return ForecastResult(
        station_id=context.station_id,
        pollutant=context.pollutant,
        generated_at=context.generated_at,
        model_name=selection.model.value,
        model_source=selection.model_source,
        fallback_reason=selection.fallback_reason,
        points=points,
    )


def _clamp_aqi(value: float | int) -> int:
    return max(0, min(500, int(round(value))))

