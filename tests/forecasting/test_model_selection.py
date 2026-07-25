from __future__ import annotations

from datetime import UTC, datetime, timedelta

from services.forecasting.config import ForecastSettings
from services.forecasting.model_selection import choose_forecast_model
from services.forecasting.models import ForecastContext, ForecastModel, HourlyAQI, ModeledAQI, PersistenceBaseline, WeatherCovariates


GENERATED_AT = datetime(2026, 4, 30, 8, 0, tzinfo=UTC)


def test_selects_sarimax_when_observed_and_weather_coverage_are_sufficient(monkeypatch):
    monkeypatch.setattr("services.forecasting.model_selection.sarimax_available", lambda: True)
    settings = _settings()
    context = _context(
        observed_hours=1512,
        weather_history_hours=1512,
        future_weather_hours=72,
        modeled_future_hours=72,
    )

    selection = choose_forecast_model(context, settings)

    assert selection.model == ForecastModel.SARIMAX
    assert selection.fallback_reason is None


def test_rejects_sarimax_when_weather_history_is_only_seven_days(monkeypatch):
    monkeypatch.setattr("services.forecasting.model_selection.sarimax_available", lambda: True)
    settings = _settings()
    context = _context(
        observed_hours=2160,
        weather_history_hours=168,
        future_weather_hours=72,
        modeled_future_hours=72,
    )

    selection = choose_forecast_model(context, settings)

    assert selection.model == ForecastModel.MODELED_BIAS
    assert "Historical weather coverage" in str(selection.fallback_reason)


def test_selects_modeled_bias_when_observed_history_is_insufficient(monkeypatch):
    monkeypatch.setattr("services.forecasting.model_selection.sarimax_available", lambda: True)
    settings = _settings()
    context = _context(
        observed_hours=200,
        weather_history_hours=2160,
        future_weather_hours=72,
        modeled_future_hours=72,
    )

    selection = choose_forecast_model(context, settings)

    assert selection.model == ForecastModel.MODELED_BIAS
    assert selection.model_source == "modeled_aq_with_observed_bias"
    assert "Observed 90-day hourly coverage" in str(selection.fallback_reason)


def test_selects_persistence_when_modeled_future_is_incomplete(monkeypatch):
    monkeypatch.setattr("services.forecasting.model_selection.sarimax_available", lambda: True)
    settings = _settings()
    context = _context(
        observed_hours=200,
        weather_history_hours=2160,
        future_weather_hours=20,
        modeled_future_hours=12,
    )

    selection = choose_forecast_model(context, settings)

    assert selection.model == ForecastModel.PERSISTENCE
    assert "Future weather covariates are incomplete" in str(selection.fallback_reason)
    assert "Modeled AQ forecast has 12 of 48" in str(selection.fallback_reason)


def test_statsmodels_unavailable_is_visible_in_fallback_reason(monkeypatch):
    monkeypatch.setattr("services.forecasting.model_selection.sarimax_available", lambda: False)
    settings = _settings()
    context = _context(
        observed_hours=2160,
        weather_history_hours=2160,
        future_weather_hours=72,
        modeled_future_hours=72,
    )

    selection = choose_forecast_model(context, settings)

    assert selection.model == ForecastModel.MODELED_BIAS
    assert "statsmodels is not available" in str(selection.fallback_reason)


def test_forced_ml_placeholder_bypasses_normal_arbitration():
    settings = _settings(force_model="ml_placeholder")
    context = _context(
        observed_hours=0,
        weather_history_hours=0,
        future_weather_hours=0,
        modeled_future_hours=0,
    )

    selection = choose_forecast_model(context, settings)

    assert selection.model == ForecastModel.ML_GBT_PLACEHOLDER
    assert selection.model_source == "synthetic_untrained_ml_placeholder"
    assert "not trained on HimalayaAir data" in str(selection.fallback_reason)
    assert "bypassed" in selection.sarimax_rejection_reasons[0]


def _settings(force_model: str | None = None) -> ForecastSettings:
    return ForecastSettings(
        database_url="postgresql://example/example",
        service_name="forecast-test",
        log_format="json",
        pollutants=("pm25",),
        horizon_hours=48,
        history_days=90,
        bias_days=7,
        min_observed_coverage=0.70,
        min_weather_history_coverage=0.70,
        max_stations=0,
        default_baseline_aqi=50,
        sarimax_enabled=True,
        force_model=force_model,
        pipeline_component="forecast_recompute",
    )


def _context(
    *,
    observed_hours: int,
    weather_history_hours: int,
    future_weather_hours: int,
    modeled_future_hours: int,
) -> ForecastContext:
    history_start = GENERATED_AT - timedelta(days=90)
    bias_start = GENERATED_AT - timedelta(days=7)
    return ForecastContext(
        station_id=1,
        station_name="Ratnapark",
        pollutant="pm25",
        generated_at=GENERATED_AT,
        weather_location_id=1,
        observed_history=_observed(history_start, observed_hours),
        weather_history=_weather(history_start, weather_history_hours),
        future_weather=_weather(GENERATED_AT + timedelta(hours=1), future_weather_hours),
        modeled_history=_modeled(bias_start, 168),
        modeled_future=_modeled(GENERATED_AT + timedelta(hours=1), modeled_future_hours),
        persistence_baseline=PersistenceBaseline(aqi=91, source="openaq_live", timestamp=GENERATED_AT),
    )


def _observed(start: datetime, count: int) -> tuple[HourlyAQI, ...]:
    return tuple(HourlyAQI(timestamp=start + timedelta(hours=index), aqi=80 + index % 20) for index in range(count))


def _weather(start: datetime, count: int) -> tuple[WeatherCovariates, ...]:
    return tuple(
        WeatherCovariates(
            timestamp=start + timedelta(hours=index),
            temp=20.0,
            humidity=65.0,
            wind_speed=5.0,
            wind_dir=180.0,
            precipitation=0.0,
        )
        for index in range(count)
    )


def _modeled(start: datetime, count: int) -> tuple[ModeledAQI, ...]:
    return tuple(ModeledAQI(timestamp=start + timedelta(hours=index), aqi=70 + index % 10) for index in range(count))

