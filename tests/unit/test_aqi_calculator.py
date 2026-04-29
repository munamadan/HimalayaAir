from __future__ import annotations

from services.common.aqi_calculator import aqi_category, aqi_color, calculate_aqi


def test_calculate_pm25_aqi_uses_2024_breakpoints() -> None:
    assert calculate_aqi("pm2.5", 0.0) == 0
    assert calculate_aqi("pm25", 9.0) == 50
    assert calculate_aqi("pm25", 9.1) == 51
    assert calculate_aqi("pm25", 35.4) == 100
    assert calculate_aqi("pm25", 35.5) == 101
    assert calculate_aqi("pm25", 55.4) == 150
    assert calculate_aqi("pm25", 55.5) == 151
    assert calculate_aqi("pm25", 125.4) == 200
    assert calculate_aqi("pm25", 125.5) == 201
    assert calculate_aqi("pm25", 225.4) == 300
    assert calculate_aqi("pm25", 225.5) == 301
    assert calculate_aqi("pm25", 325.4) == 500


def test_calculate_pm25_aqi_truncates_concentration_before_interpolation() -> None:
    assert calculate_aqi("pm25", 9.09) == 50
    assert calculate_aqi("pm25", 9.19) == 51


def test_calculate_aqi_returns_none_for_unsupported_or_invalid_inputs() -> None:
    assert calculate_aqi("pm10", 90.0) is None
    assert calculate_aqi("pm25", -1.0) is None
    assert calculate_aqi("pm25", 12.0, unit="ppm") is None
    assert calculate_aqi("pm25", 1000.1) is None


def test_category_and_color_helpers() -> None:
    assert aqi_category(87) == "Moderate"
    assert aqi_color(87) == "#ffff00"
    assert aqi_category(501) == "Hazardous"
    assert aqi_color(501) == "#7e0023"
    assert aqi_category(None) is None
    assert aqi_color(None) is None
