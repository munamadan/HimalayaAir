from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from scripts.source_validation import (
    LIVE_OBSERVED,
    MODELED_BASELINE,
    RECENT_OBSERVED,
    STATION_ONLY,
    KathmanduBoundingBox,
    build_coverage_report,
    load_json_file,
    normalize_openaq_locations,
    normalize_openaq_measurements,
    normalize_openmeteo_aq_response,
    parse_variables,
    recommend_coverage_mode,
)


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def test_normalize_openaq_locations_preserves_station_sensor_model() -> None:
    payload = load_json_file(FIXTURES / "sample_openaq_location.json")

    result = normalize_openaq_locations(payload)

    assert result.warnings == []
    assert len(result.stations) == 2
    assert len(result.sensors) == 3
    assert result.stations[0].openaq_location_id == 11001
    assert result.stations[0].sensor_count == 2
    assert result.sensors[0].openaq_sensor_id == 21001
    assert result.sensors[0].openaq_location_id == 11001
    assert result.sensors[0].pollutant == "pm25"
    assert result.sensors[1].pollutant == "pm10"


def test_normalize_openaq_locations_keeps_aq_sensors_pollable_without_last_seen() -> None:
    payload = {
        "results": [
            {
                "id": 11001,
                "name": "Kathmandu Station",
                "coordinates": {"latitude": 27.7, "longitude": 85.3},
                "isMonitor": True,
                "sensors": [
                    {
                        "id": 21001,
                        "parameter": {"id": 2, "name": "pm2.5", "units": "ug/m3"},
                    },
                    {
                        "id": 21002,
                        "parameter": {"id": 99, "name": "temperature", "units": "c"},
                    },
                ],
            }
        ]
    }

    result = normalize_openaq_locations(payload)

    assert result.sensors[0].pollutant == "pm25"
    assert result.sensors[0].active is True
    assert result.sensors[1].pollutant == "temperature"
    assert result.sensors[1].active is False


def test_normalize_openaq_measurements_labels_observed_source() -> None:
    payload = load_json_file(FIXTURES / "sample_openaq_measurement.json")

    measurements = normalize_openaq_measurements(payload)

    assert len(measurements) == 1
    measurement = measurements[0]
    assert measurement.openaq_sensor_id == 21001
    assert measurement.openaq_location_id == 11001
    assert measurement.pollutant == "pm25"
    assert measurement.value == 24.6
    assert measurement.timestamp_utc == "2026-04-28T06:00:00Z"
    assert measurement.source == "openaq_live"
    assert measurement.observation_type == "observed"


def test_coverage_report_uses_recent_observed_when_live_station_count_is_sparse() -> None:
    payload = load_json_file(FIXTURES / "sample_openaq_location.json")
    normalization = normalize_openaq_locations(payload)
    now = datetime(2026, 4, 28, 7, 0, tzinfo=timezone.utc)

    report = build_coverage_report(
        normalization,
        bounds=KathmanduBoundingBox(),
        now=now,
    )

    assert report["fresh_station_count"] == 1
    assert report["recent_station_count"] == 1
    assert report["recommended_coverage_mode"] == STATION_ONLY
    assert report["stations"][0]["freshness_minutes"] == 80
    assert report["stations"][1]["status"] == "stale"


def test_recommend_coverage_mode_priority_order() -> None:
    assert recommend_coverage_mode(
        fresh_station_count=3,
        recent_station_count=3,
        station_count=3,
        modeled_available=False,
    )[0] == LIVE_OBSERVED
    assert recommend_coverage_mode(
        fresh_station_count=2,
        recent_station_count=3,
        station_count=3,
        modeled_available=False,
    )[0] == RECENT_OBSERVED
    assert recommend_coverage_mode(
        fresh_station_count=0,
        recent_station_count=1,
        station_count=2,
        modeled_available=True,
    )[0] == MODELED_BASELINE
    assert recommend_coverage_mode(
        fresh_station_count=0,
        recent_station_count=1,
        station_count=2,
        modeled_available=False,
    )[0] == STATION_ONLY


def test_openmeteo_aq_response_marks_modeled_baseline() -> None:
    payload = load_json_file(FIXTURES / "sample_openmeteo_aq.json")
    variables = parse_variables(None)

    availability = normalize_openmeteo_aq_response(payload, requested_variables=variables)

    assert availability.source == "openmeteo_cams"
    assert availability.observation_type == "modeled"
    assert availability.coverage_mode == MODELED_BASELINE
    assert availability.modeled_available is True
    assert "pm2_5" in availability.available_variables
    assert availability.latest_timestamp == "2026-04-28T02:00:00Z"
