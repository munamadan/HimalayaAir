from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import httpx

from shared.time_utils import ensure_utc, parse_utc

from services.weather_poller.models import ModeledAQReading, WeatherLocation, WeatherReading


OPENMETEO_WEATHER_BASE_URL = "https://api.open-meteo.com"
OPENMETEO_AQ_BASE_URL = "https://air-quality-api.open-meteo.com"

WEATHER_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "precipitation",
)

MODELED_AQ_VARIABLES = (
    "pm2_5",
    "pm10",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "ozone",
    "us_aqi",
    "us_aqi_pm2_5",
    "us_aqi_pm10",
    "us_aqi_nitrogen_dioxide",
    "us_aqi_ozone",
    "us_aqi_carbon_monoxide",
)

AQ_CONCENTRATION_FIELDS = {
    "pm2_5": ("pm25", "us_aqi_pm2_5"),
    "pm10": ("pm10", "us_aqi_pm10"),
    "carbon_monoxide": ("co", "us_aqi_carbon_monoxide"),
    "nitrogen_dioxide": ("no2", "us_aqi_nitrogen_dioxide"),
    "ozone": ("o3", "us_aqi_ozone"),
}


class OpenMeteoClientError(RuntimeError):
    pass


class OpenMeteoRateLimitError(OpenMeteoClientError):
    def __init__(self, message: str, *, retry_after_seconds: float | None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class OpenMeteoClient:
    def __init__(
        self,
        *,
        timeout_seconds: float,
        retries: int,
        weather_client: httpx.Client | None = None,
        aq_client: httpx.Client | None = None,
    ) -> None:
        self.retries = retries
        self.rate_limit_hits = 0
        self.invalid_payloads = 0
        self.weather_client = weather_client or httpx.Client(
            base_url=OPENMETEO_WEATHER_BASE_URL,
            timeout=timeout_seconds,
        )
        self.aq_client = aq_client or httpx.Client(base_url=OPENMETEO_AQ_BASE_URL, timeout=timeout_seconds)

    def close(self) -> None:
        self.weather_client.close()
        self.aq_client.close()

    def fetch_weather(
        self,
        location: WeatherLocation,
        *,
        forecast_days: int,
        past_days: int,
    ) -> dict[str, Any]:
        return self._get_json(
            self.weather_client,
            "/v1/forecast",
            params={
                "latitude": location.latitude,
                "longitude": location.longitude,
                "hourly": ",".join(WEATHER_VARIABLES),
                "timezone": "UTC",
                "forecast_days": max(forecast_days, 1),
                "past_days": past_days,
            },
        )

    def fetch_modeled_aq(
        self,
        location: WeatherLocation,
        *,
        forecast_days: int,
        past_days: int,
    ) -> dict[str, Any]:
        return self._get_json(
            self.aq_client,
            "/v1/air-quality",
            params={
                "latitude": location.latitude,
                "longitude": location.longitude,
                "hourly": ",".join(MODELED_AQ_VARIABLES),
                "timezone": "UTC",
                "forecast_days": max(forecast_days, 1),
                "past_days": past_days,
            },
        )

    def _get_json(self, client: httpx.Client, path: str, *, params: dict[str, object]) -> dict[str, Any]:
        retry_after_seconds: float | None = None
        filtered_params = {key: value for key, value in params.items() if value is not None}
        for attempt in range(self.retries + 1):
            try:
                response = client.get(path, params=filtered_params)
            except httpx.HTTPError as exc:
                if attempt < self.retries:
                    time.sleep(_retry_delay(None, attempt))
                    continue
                raise OpenMeteoClientError(f"Open-Meteo request failed: {exc}") from exc

            if response.status_code == 429:
                self.rate_limit_hits += 1
                retry_after_seconds = _retry_after_seconds(response)
                if attempt < self.retries:
                    time.sleep(_retry_delay(retry_after_seconds, attempt))
                    continue
                raise OpenMeteoRateLimitError("Open-Meteo rate limit exceeded", retry_after_seconds=retry_after_seconds)

            if response.status_code in {408, 500, 502, 503, 504} and attempt < self.retries:
                time.sleep(_retry_delay(None, attempt))
                continue

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise OpenMeteoClientError(f"Open-Meteo returned HTTP {response.status_code}") from exc

            try:
                payload = response.json()
            except ValueError as exc:
                raise OpenMeteoClientError("Open-Meteo returned invalid JSON") from exc
            if not isinstance(payload, dict):
                raise OpenMeteoClientError("Open-Meteo response must be a JSON object")
            return payload

        raise OpenMeteoClientError("Open-Meteo request retry loop ended unexpectedly")


def normalize_weather_response(location: WeatherLocation, payload: dict[str, Any]) -> list[WeatherReading]:
    hourly = _hourly(payload)
    times = _times(hourly)
    readings: list[WeatherReading] = []
    for index, raw_time in enumerate(times):
        timestamp = _parse_time(raw_time)
        values = {
            "temp": _float_at(hourly, "temperature_2m", index),
            "humidity": _float_at(hourly, "relative_humidity_2m", index),
            "wind_speed": _float_at(hourly, "wind_speed_10m", index),
            "wind_dir": _float_at(hourly, "wind_direction_10m", index),
            "precipitation": _float_at(hourly, "precipitation", index),
        }
        if all(value is None for value in values.values()):
            continue
        readings.append(
            WeatherReading(
                location_id=location.location_id,
                location_name=location.name,
                latitude=location.latitude,
                longitude=location.longitude,
                timestamp=timestamp,
                quality_flag=_quality_flag(hourly, WEATHER_VARIABLES, index),
                **values,
            )
        )
    return readings


def normalize_modeled_aq_response(
    location: WeatherLocation,
    payload: dict[str, Any],
    *,
    model_run_at: datetime,
) -> list[ModeledAQReading]:
    hourly = _hourly(payload)
    hourly_units = payload.get("hourly_units") if isinstance(payload.get("hourly_units"), dict) else {}
    times = _times(hourly)
    run_at = ensure_utc(model_run_at)
    readings: list[ModeledAQReading] = []

    for index, raw_time in enumerate(times):
        timestamp = _parse_time(raw_time)
        for variable, (pollutant, aqi_variable) in AQ_CONCENTRATION_FIELDS.items():
            value = _float_at(hourly, variable, index)
            us_aqi = _int_at(hourly, aqi_variable, index)
            if value is None and us_aqi is None:
                continue
            readings.append(
                ModeledAQReading(
                    model_location_id=location.location_id,
                    location_name=location.name,
                    latitude=location.latitude,
                    longitude=location.longitude,
                    pollutant=pollutant,
                    value=value,
                    unit=_unit(hourly_units, variable),
                    us_aqi=us_aqi,
                    timestamp=timestamp,
                    model_run_at=run_at,
                    quality_flag=_quality_flag(hourly, (variable, aqi_variable), index),
                )
            )

        general_aqi = _int_at(hourly, "us_aqi", index)
        if general_aqi is not None:
            readings.append(
                ModeledAQReading(
                    model_location_id=location.location_id,
                    location_name=location.name,
                    latitude=location.latitude,
                    longitude=location.longitude,
                    pollutant="us_aqi",
                    value=float(general_aqi),
                    unit=_unit(hourly_units, "us_aqi") or "US AQI",
                    us_aqi=general_aqi,
                    timestamp=timestamp,
                    model_run_at=run_at,
                    quality_flag=_quality_flag(hourly, ("us_aqi",), index),
                )
            )
    return readings


def quality_counts(readings: list[WeatherReading] | list[ModeledAQReading]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for reading in readings:
        counts[reading.quality_flag] = counts.get(reading.quality_flag, 0) + 1
    return dict(sorted(counts.items()))


def _hourly(payload: dict[str, Any]) -> dict[str, Any]:
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise OpenMeteoClientError("Open-Meteo response missing hourly object")
    return hourly


def _times(hourly: dict[str, Any]) -> list[Any]:
    times = hourly.get("time")
    if not isinstance(times, list):
        raise OpenMeteoClientError("Open-Meteo response missing hourly time array")
    return times


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise OpenMeteoClientError("Open-Meteo hourly timestamp must be a string")
    try:
        return parse_utc(value)
    except ValueError as exc:
        raise OpenMeteoClientError(f"Open-Meteo hourly timestamp is invalid: {value}") from exc


def _quality_flag(hourly: dict[str, Any], variables: tuple[str, ...], index: int) -> str:
    missing_variables = [variable for variable in variables if not isinstance(hourly.get(variable), list)]
    if missing_variables:
        return "partial_response"
    missing_values = [
        variable
        for variable in variables
        if index >= len(hourly[variable]) or hourly[variable][index] is None
    ]
    if missing_values:
        return "missing_value"
    return "complete"


def _float_at(hourly: dict[str, Any], variable: str, index: int) -> float | None:
    value = _value_at(hourly, variable, index)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_at(hourly: dict[str, Any], variable: str, index: int) -> int | None:
    value = _value_at(hourly, variable, index)
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _value_at(hourly: dict[str, Any], variable: str, index: int) -> object | None:
    values = hourly.get(variable)
    if not isinstance(values, list) or index >= len(values):
        return None
    return values[index]


def _unit(hourly_units: dict[str, Any], variable: str) -> str | None:
    value = hourly_units.get(variable)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _retry_after_seconds(response: httpx.Response) -> float | None:
    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return None
    try:
        return max(float(retry_after), 0.0)
    except ValueError:
        return None


def _retry_delay(retry_after_seconds: float | None, attempt: int) -> float:
    if retry_after_seconds is not None:
        return min(retry_after_seconds, 30.0)
    return min(0.5 * (2**attempt), 5.0)
