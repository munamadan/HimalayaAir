from __future__ import annotations


def test_valley_current_contract(api_client):
    response = api_client.get("/api/valley/current")

    assert response.status_code == 200
    payload = response.json()
    assert payload["composite_aqi"] == 108
    assert payload["dominant_pollutant"] == "pm25"
    assert payload["coverage_mode"] == "RECENT_OBSERVED"
    assert "Sensitive groups" in payload["recommendation"]
    assert payload["source"] == "openaq_live"


def test_valley_history_contract(api_client):
    response = api_client.get("/api/valley/history?pollutant=pm25&granularity=hour")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pollutant"] == "pm25"
    assert payload["granularity"] == "hour"
    assert payload["points"][0]["avg_aqi"] == 95.5
    assert payload["points"][0]["station_count"] == 4
