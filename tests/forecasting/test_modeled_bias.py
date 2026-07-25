from __future__ import annotations

from datetime import UTC, datetime, timedelta

from services.forecasting.modeled_bias import build_modeled_bias_forecast
from services.forecasting.models import ForecastContext, ForecastModel, HourlyAQI, ModeledAQI, ModelSelection, PersistenceBaseline

from tests.forecasting.test_model_selection import _settings


def test_modeled_bias_uses_median_observed_minus_modeled_bias():
    generated_at = datetime(2026, 4, 30, 8, 0, tzinfo=UTC)
    history_start = generated_at - timedelta(hours=3)
    future_start = generated_at + timedelta(hours=1)
    context = ForecastContext(
        station_id=1,
        station_name="Ratnapark",
        pollutant="pm25",
        generated_at=generated_at,
        weather_location_id=1,
        observed_history=(
            HourlyAQI(history_start, 100),
            HourlyAQI(history_start + timedelta(hours=1), 110),
            HourlyAQI(history_start + timedelta(hours=2), 120),
        ),
        weather_history=(),
        future_weather=(),
        modeled_history=(
            ModeledAQI(history_start, 90),
            ModeledAQI(history_start + timedelta(hours=1), 95),
            ModeledAQI(history_start + timedelta(hours=2), 100),
        ),
        modeled_future=tuple(ModeledAQI(future_start + timedelta(hours=index), 80) for index in range(48)),
        persistence_baseline=PersistenceBaseline(aqi=70, source="openaq_live", timestamp=generated_at),
    )
    selection = ModelSelection(
        model=ForecastModel.MODELED_BIAS,
        model_source="modeled_aq_with_observed_bias",
        fallback_reason="insufficient observed coverage",
        sarimax_rejection_reasons=("insufficient observed coverage",),
    )

    result = build_modeled_bias_forecast(context, _settings(), selection)

    assert len(result.points) == 48
    assert result.points[0].predicted_aqi == 95
    assert result.model_source == "modeled_aq_with_observed_bias"

