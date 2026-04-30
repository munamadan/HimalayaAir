from __future__ import annotations

from services.forecasting.config import ForecastSettings
from services.forecasting.models import ForecastContext, ForecastModel, ModelSelection
from services.forecasting.sarimax import sarimax_available


def choose_forecast_model(context: ForecastContext, settings: ForecastSettings) -> ModelSelection:
    expected_history_hours = settings.history_days * 24
    observed_coverage = _coverage(len(context.observed_history), expected_history_hours)
    weather_history_coverage = _coverage(len(context.weather_history), expected_history_hours)
    future_weather_complete = len(context.future_weather) >= settings.horizon_hours
    modeled_future_complete = len(context.modeled_future) >= settings.horizon_hours
    sarimax_reasons = _sarimax_rejection_reasons(
        settings=settings,
        observed_coverage=observed_coverage,
        weather_history_coverage=weather_history_coverage,
        future_weather_complete=future_weather_complete,
    )

    if not sarimax_reasons:
        return ModelSelection(
            model=ForecastModel.SARIMAX,
            model_source="observed_aq_with_weather_covariates",
            fallback_reason=None,
            sarimax_rejection_reasons=(),
        )

    if modeled_future_complete:
        return ModelSelection(
            model=ForecastModel.MODELED_BIAS,
            model_source="modeled_aq_with_observed_bias" if context.modeled_history and context.observed_history else "modeled_aq_unadjusted",
            fallback_reason="; ".join(sarimax_reasons),
            sarimax_rejection_reasons=tuple(sarimax_reasons),
        )

    reasons = [*sarimax_reasons, f"Modeled AQ forecast has {len(context.modeled_future)} of {settings.horizon_hours} required future hour(s)."]
    return ModelSelection(
        model=ForecastModel.PERSISTENCE,
        model_source=f"persistence_{context.persistence_baseline.source}",
        fallback_reason="; ".join(reasons),
        sarimax_rejection_reasons=tuple(sarimax_reasons),
    )


def _sarimax_rejection_reasons(
    *,
    settings: ForecastSettings,
    observed_coverage: float,
    weather_history_coverage: float,
    future_weather_complete: bool,
) -> list[str]:
    reasons: list[str] = []
    if not settings.sarimax_enabled:
        reasons.append("SARIMAX is disabled by configuration.")
    elif not sarimax_available():
        reasons.append("SARIMAX dependency statsmodels is not available.")
    if observed_coverage < settings.min_observed_coverage:
        reasons.append(
            f"Observed 90-day hourly coverage is {observed_coverage:.1%}, below the {settings.min_observed_coverage:.0%} SARIMAX threshold."
        )
    if weather_history_coverage < settings.min_weather_history_coverage:
        reasons.append(
            f"Historical weather coverage is {weather_history_coverage:.1%}, below the {settings.min_weather_history_coverage:.0%} SARIMAX threshold."
        )
    if not future_weather_complete:
        reasons.append(f"Future weather covariates are incomplete for the next {settings.horizon_hours} hour(s).")
    return reasons


def _coverage(actual: int, expected: int) -> float:
    if expected <= 0:
        return 0.0
    return min(max(actual / expected, 0.0), 1.0)

