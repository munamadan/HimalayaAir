from __future__ import annotations

from datetime import datetime, timezone

from services.api.domain import AQPoint
from services.api.spatial import GridBounds, build_idw_grid


def test_interpolation_current_contract(api_client):
    response = api_client.get("/api/interpolation/current?pollutant=pm25")

    assert response.status_code == 200
    payload = response.json()
    assert payload["coverage_mode"] == "RECENT_OBSERVED"
    assert payload["confidence"] == "medium"
    assert payload["source"] == "openaq_live_recent"
    assert payload["insufficient_data"] is False
    assert payload["station_count"] == 4
    assert payload["grid"]["rows"] == 5
    assert payload["grid"]["cols"] == 5
    assert len(payload["grid"]["values"]) == 5
    assert len(payload["grid"]["values"][0]) == 5


def test_idw_uses_meter_projection_not_degree_distance():
    timestamp = datetime(2026, 4, 30, 8, tzinfo=timezone.utc)
    bounds = GridBounds(min_lat=27.70, max_lat=27.72, min_lon=85.30, max_lon=85.32)
    grid = build_idw_grid(
        [
            AQPoint(id=1, name="a", lat=27.70, lon=85.30, aqi=50, pollutant="pm25", source="openaq_live", observation_type="observed", timestamp=timestamp),
            AQPoint(id=2, name="b", lat=27.72, lon=85.30, aqi=100, pollutant="pm25", source="openaq_live", observation_type="observed", timestamp=timestamp),
            AQPoint(id=3, name="c", lat=27.70, lon=85.32, aqi=150, pollutant="pm25", source="openaq_live", observation_type="observed", timestamp=timestamp),
        ],
        rows=2,
        cols=2,
        power=2.0,
        bounds=bounds,
    )

    assert grid.values[0][0] == 50
    assert grid.values[1][0] == 100
    assert grid.values[0][1] == 150
