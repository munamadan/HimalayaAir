from __future__ import annotations


def test_forecasts_contract(api_client):
    response = api_client.get("/api/forecasts/1?pollutant=pm25")

    assert response.status_code == 200
    payload = response.json()
    assert payload["station_id"] == 1
    assert payload["pollutant"] == "pm25"
    assert payload["model"] == "openmeteo_cams_bias_adjusted"
    assert payload["model_source"] == "modeled_aq_with_observed_bias"
    assert payload["fallback_reason"] == "Insufficient 90-day observed coverage for SARIMAX."
    assert payload["historical_mae"] == 12.4
    assert payload["forecasts"][0]["horizon_hours"] == 1
    assert payload["forecasts"][0]["predicted_aqi"] == 91

