from __future__ import annotations

from datetime import UTC, datetime

from services.forecasting.models import ForecastContext, ForecastModel, ModelSelection, PersistenceBaseline
from services.forecasting.persistence import build_persistence_forecast

from tests.forecasting.test_model_selection import _settings


def test_persistence_forecast_always_returns_full_horizon_shape():
    generated_at = datetime(2026, 4, 30, 8, 0, tzinfo=UTC)
    context = ForecastContext(
        station_id=1,
        station_name="Ratnapark",
        pollutant="pm25",
        generated_at=generated_at,
        weather_location_id=None,
        observed_history=(),
        weather_history=(),
        future_weather=(),
        modeled_history=(),
        modeled_future=(),
        persistence_baseline=PersistenceBaseline(aqi=91, source="openaq_live", timestamp=generated_at),
    )
    selection = ModelSelection(
        model=ForecastModel.PERSISTENCE,
        model_source="persistence_openaq_live",
        fallback_reason="test fallback",
        sarimax_rejection_reasons=("test fallback",),
    )

    result = build_persistence_forecast(context, _settings(), selection)

    assert result.model_name == "persistence"
    assert result.model_source == "persistence_openaq_live"
    assert result.fallback_reason == "test fallback"
    assert len(result.points) == 48
    assert result.points[0].horizon_hours == 1
    assert result.points[-1].horizon_hours == 48
    assert all(point.predicted_aqi == 91 for point in result.points)
    assert all(0 <= point.lower_bound <= point.upper_bound <= 500 for point in result.points)

