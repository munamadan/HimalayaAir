from __future__ import annotations

from datetime import UTC, datetime

import httpx

from shared.enums import CoverageMode, ObservationType, SourceName

from services.weather_poller.models import ModeledAQReading, WeatherLocation, WeatherReading
from services.weather_poller.openmeteo_client import (
    OpenMeteoClient,
    normalize_modeled_aq_response,
    normalize_weather_response,
)
from services.weather_poller.publisher import build_modeled_aq_message, build_weather_message


def test_normalize_weather_response_flags_missing_values() -> None:
    location = _location()
    payload = {
        "hourly": {
            "time": ["2026-04-29T00:00", "2026-04-29T01:00"],
            "temperature_2m": [18.1, 18.4],
            "relative_humidity_2m": [72, None],
            "wind_speed_10m": [4.5, 4.9],
            "wind_direction_10m": [180, 190],
            "precipitation": [0.0, 0.1],
        }
    }

    readings = normalize_weather_response(location, payload)

    assert len(readings) == 2
    assert readings[0].quality_flag == "complete"
    assert readings[1].quality_flag == "missing_value"
    assert readings[0].timestamp == datetime(2026, 4, 29, 0, 0, tzinfo=UTC)
    assert readings[0].source == "openmeteo_weather"


def test_normalize_weather_response_flags_partial_response() -> None:
    payload = {
        "hourly": {
            "time": ["2026-04-29T00:00"],
            "temperature_2m": [18.1],
            "relative_humidity_2m": [72],
            "wind_speed_10m": [4.5],
            "wind_direction_10m": [180],
        }
    }

    readings = normalize_weather_response(_location(), payload)

    assert len(readings) == 1
    assert readings[0].quality_flag == "partial_response"
    assert readings[0].precipitation is None


def test_normalize_modeled_aq_response_preserves_provenance_and_quality() -> None:
    location = _location()
    model_run_at = datetime(2026, 4, 29, 6, 30, tzinfo=UTC)
    payload = {
        "hourly_units": {
            "pm2_5": "ug/m3",
            "pm10": "ug/m3",
            "carbon_monoxide": "ug/m3",
            "nitrogen_dioxide": "ug/m3",
            "ozone": "ug/m3",
            "us_aqi": "US AQI",
        },
        "hourly": {
            "time": ["2026-04-29T06:00"],
            "pm2_5": [22.4],
            "pm10": [55.1],
            "carbon_monoxide": [310.0],
            "nitrogen_dioxide": [12.2],
            "ozone": [67.0],
            "us_aqi": [71],
            "us_aqi_pm2_5": [71],
            "us_aqi_pm10": [52],
            "us_aqi_nitrogen_dioxide": [12],
            "us_aqi_ozone": [31],
        },
    }

    readings = normalize_modeled_aq_response(location, payload, model_run_at=model_run_at)
    by_pollutant = {reading.pollutant: reading for reading in readings}

    assert by_pollutant["pm25"].source == "openmeteo_cams"
    assert by_pollutant["pm25"].observation_type == "modeled"
    assert by_pollutant["pm25"].coverage_mode == "MODELED_BASELINE"
    assert by_pollutant["pm25"].value == 22.4
    assert by_pollutant["pm25"].us_aqi == 71
    assert by_pollutant["pm25"].quality_flag == "complete"
    assert by_pollutant["co"].quality_flag == "partial_response"
    assert by_pollutant["us_aqi"].unit == "US AQI"


def test_weather_and_modeled_messages_use_expected_sources() -> None:
    weather_message = build_weather_message(
        WeatherReading(
            location_id=1,
            location_name="Kathmandu Center",
            latitude=27.7172,
            longitude=85.324,
            temp=18.1,
            humidity=72,
            wind_speed=4.5,
            wind_dir=180,
            precipitation=0,
            timestamp=datetime(2026, 4, 29, 6, 0, tzinfo=UTC),
            quality_flag="complete",
        )
    )
    modeled_message = build_modeled_aq_message(
        ModeledAQReading(
            model_location_id=1,
            location_name="Kathmandu Center",
            latitude=27.7172,
            longitude=85.324,
            pollutant="pm25",
            value=22.4,
            unit="ug/m3",
            us_aqi=71,
            timestamp=datetime(2026, 4, 29, 6, 0, tzinfo=UTC),
            model_run_at=datetime(2026, 4, 29, 6, 0, tzinfo=UTC),
            quality_flag="complete",
        )
    )

    assert weather_message.source == SourceName.OPENMETEO_WEATHER.value
    assert weather_message.observation_type == ObservationType.MODELED.value
    assert weather_message.quality_flag == "complete"
    assert modeled_message.source == SourceName.OPENMETEO_CAMS.value
    assert modeled_message.observation_type == ObservationType.MODELED.value
    assert modeled_message.coverage_mode == CoverageMode.MODELED_BASELINE.value
    assert modeled_message.quality_flag == "complete"


def test_openmeteo_client_retries_429_with_retry_after() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"hourly": {"time": ["2026-04-29T06:00"], "temperature_2m": [18.1]}})

    mock_client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.open-meteo.com")
    client = OpenMeteoClient(timeout_seconds=1, retries=1, weather_client=mock_client, aq_client=mock_client)

    payload = client.fetch_weather(_location(), forecast_days=1, past_days=0)

    assert payload["hourly"]["temperature_2m"] == [18.1]
    assert calls == 2
    assert client.rate_limit_hits == 1


def _location() -> WeatherLocation:
    return WeatherLocation(
        location_id=1,
        name="Kathmandu Center",
        latitude=27.7172,
        longitude=85.3240,
        elevation=1400,
    )
