from __future__ import annotations


def test_stations_snapshot_contract(api_client):
    response = api_client.get("/api/stations")

    assert response.status_code == 200
    payload = response.json()
    assert payload["coverage_mode"] == "RECENT_OBSERVED"
    assert payload["confidence"] == "medium"
    assert payload["fresh_station_count"] == 2
    assert payload["recent_station_count"] == 4
    assert payload["modeled_available"] is True
    assert payload["valley_composite_aqi"] == 108
    assert len(payload["stations"]) == 4
    assert payload["stations"][0]["source"] == "openaq_live"
    assert payload["stations"][0]["observation_type"] == "observed"


def test_station_current_uses_latest_per_pollutant_contract(api_client):
    response = api_client.get("/api/stations/1/current")

    assert response.status_code == 200
    payload = response.json()
    assert payload["station"]["id"] == 1
    assert payload["current_aqi"] == 91
    assert payload["dominant_pollutant"] == "pm25"
    assert [reading["pollutant"] for reading in payload["readings"]] == ["pm25", "pm10"]
    assert payload["readings"][0]["timestamp"] != payload["readings"][1]["timestamp"]
    assert all(reading["source"] == "openaq_live" for reading in payload["readings"])


def test_station_history_contract(api_client):
    response = api_client.get("/api/stations/1/history?pollutant=pm25&hours=24")

    assert response.status_code == 200
    payload = response.json()
    assert payload["station_id"] == 1
    assert payload["pollutant"] == "pm25"
    assert payload["readings"][0]["coverage_mode"] == "RECENT_OBSERVED"
