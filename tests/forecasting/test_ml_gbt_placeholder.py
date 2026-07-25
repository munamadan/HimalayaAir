from __future__ import annotations

from services.forecasting.ml_gbt import (
    build_ml_placeholder_forecast,
    build_placeholder_feature_vector,
)
from services.forecasting.model_selection import choose_forecast_model
from services.forecasting.models import ForecastModel

from tests.forecasting.test_model_selection import _context, _settings


def test_forced_ml_placeholder_returns_48_hour_shape_and_labels():
    settings = _settings(force_model="ml_placeholder")
    context = _context(
        observed_hours=48,
        weather_history_hours=48,
        future_weather_hours=48,
        modeled_future_hours=48,
    )
    selection = choose_forecast_model(context, settings)

    result = build_ml_placeholder_forecast(context, settings, selection)

    assert selection.model == ForecastModel.ML_GBT_PLACEHOLDER
    assert result.model_name == "hist_gradient_boosting_placeholder"
    assert result.model_source == "synthetic_untrained_ml_placeholder"
    assert "not trained on HimalayaAir data" in str(result.fallback_reason)
    assert len(result.points) == 48
    assert result.points[0].horizon_hours == 1
    assert result.points[-1].horizon_hours == 48
    assert all(
        0 <= point.lower_bound <= point.predicted_aqi <= point.upper_bound <= 500
        for point in result.points
    )


def test_ml_placeholder_is_deterministic_for_same_context():
    settings = _settings(force_model="ml_placeholder")
    context = _context(
        observed_hours=48,
        weather_history_hours=48,
        future_weather_hours=48,
        modeled_future_hours=48,
    )
    selection = choose_forecast_model(context, settings)

    first = build_ml_placeholder_forecast(context, settings, selection)
    second = build_ml_placeholder_forecast(context, settings, selection)

    assert first == second


def test_ml_placeholder_feature_vector_uses_lag_weather_modeled_and_horizon():
    settings = _settings(force_model="ml_placeholder")
    context = _context(
        observed_hours=48,
        weather_history_hours=48,
        future_weather_hours=48,
        modeled_future_hours=48,
    )

    features = build_placeholder_feature_vector(context, settings, 24)

    assert features["horizon_hours"] == 24.0
    assert features["lag_aqi_1h"] > 0
    assert features["lag_aqi_24h"] > 0
    assert features["rolling_aqi_24h"] > 0
    assert features["temp"] == 20.0
    assert features["humidity"] == 65.0
    assert features["wind_speed"] == 5.0
    assert features["precipitation"] == 0.0
    assert features["modeled_aqi"] > 0
