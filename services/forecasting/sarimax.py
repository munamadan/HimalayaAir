from __future__ import annotations

from datetime import timedelta

from services.forecasting.config import ForecastSettings
from services.forecasting.models import ForecastContext, ForecastPoint, ForecastResult, ModelSelection
from services.forecasting.persistence import _clamp_aqi


class SarimaxForecastError(RuntimeError):
    pass


def sarimax_available() -> bool:
    try:
        import statsmodels  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


def build_sarimax_forecast(context: ForecastContext, settings: ForecastSettings, selection: ModelSelection) -> ForecastResult:
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX
    except ModuleNotFoundError as exc:
        raise SarimaxForecastError("statsmodels is not installed") from exc

    if len(context.future_weather) < settings.horizon_hours:
        raise SarimaxForecastError("future weather covariates are incomplete")
    if not context.observed_history or not context.weather_history:
        raise SarimaxForecastError("observed AQ or weather history is empty")

    observed_by_timestamp = {point.timestamp: point.aqi for point in context.observed_history}
    weather_by_timestamp = {point.timestamp: point for point in context.weather_history}
    aligned_timestamps = sorted(set(observed_by_timestamp) & set(weather_by_timestamp))
    if len(aligned_timestamps) < max(24, int(settings.history_days * 24 * settings.min_observed_coverage)):
        raise SarimaxForecastError("aligned observed AQ and weather history is insufficient")

    endog = [observed_by_timestamp[timestamp] for timestamp in aligned_timestamps]
    exog = [weather_by_timestamp[timestamp].as_vector() for timestamp in aligned_timestamps]
    future_exog = [point.as_vector() for point in context.future_weather[: settings.horizon_hours]]

    try:
        model = SARIMAX(
            endog,
            exog=exog,
            order=(1, 0, 1),
            seasonal_order=(0, 0, 0, 0),
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        fitted = model.fit(disp=False)
        predicted_values = fitted.forecast(steps=settings.horizon_hours, exog=future_exog)
    except Exception as exc:
        raise SarimaxForecastError(f"SARIMAX fit or forecast failed: {exc}") from exc

    points: list[ForecastPoint] = []
    residual_spread = _residual_spread(endog, fallback=context.persistence_baseline.aqi)
    for index, value in enumerate(predicted_values, start=1):
        predicted = _clamp_aqi(float(value))
        spread = max(15, residual_spread)
        points.append(
            ForecastPoint(
                station_id=context.station_id,
                pollutant=context.pollutant,
                target_timestamp=context.generated_at + timedelta(hours=index),
                horizon_hours=index,
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
        fallback_reason=None,
        points=tuple(points),
    )


def _residual_spread(values: list[float], *, fallback: int) -> int:
    if len(values) < 2:
        return max(15, round(fallback * 0.15))
    mean_value = sum(values) / len(values)
    variance = sum((value - mean_value) ** 2 for value in values) / len(values)
    return max(15, round(variance**0.5))

