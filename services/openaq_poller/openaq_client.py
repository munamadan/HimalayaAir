from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import httpx

from shared.time_utils import format_utc, parse_utc

from services.openaq_poller.models import OpenAQMeasurement


OPENAQ_BASE_URL = "https://api.openaq.org"


class OpenAQClientError(RuntimeError):
    pass


class OpenAQRateLimitError(OpenAQClientError):
    def __init__(self, message: str, *, retry_after_seconds: float | None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class OpenAQClient:
    def __init__(
        self,
        api_key: str,
        *,
        timeout_seconds: float,
        retries: int,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise OpenAQClientError("OPENAQ_API_KEY is required for live OpenAQ polling")
        self.api_key = api_key
        self.retries = retries
        self.rate_limit_hits = 0
        self.invalid_measurements = 0
        self.client = client or httpx.Client(base_url=OPENAQ_BASE_URL, timeout=timeout_seconds)

    def close(self) -> None:
        self.client.close()

    def fetch_sensor_measurements(
        self,
        sensor_id: int,
        *,
        datetime_from: datetime,
        datetime_to: datetime,
        limit: int,
        max_pages: int,
    ) -> list[OpenAQMeasurement]:
        measurements: list[OpenAQMeasurement] = []
        for page in range(1, max_pages + 1):
            payload = self._get_json(
                f"/v3/sensors/{sensor_id}/measurements",
                params={
                    "datetime_from": format_utc(datetime_from),
                    "datetime_to": format_utc(datetime_to),
                    "limit": limit,
                    "page": page,
                },
            )
            results = _results(payload)
            for result in results:
                try:
                    measurements.append(_measurement_from_result(result, fallback_sensor_id=sensor_id))
                except OpenAQClientError:
                    self.invalid_measurements += 1
            found = _found(payload)
            if len(results) < limit or (found is not None and len(measurements) >= found):
                break
        return measurements

    def _get_json(self, path: str, *, params: dict[str, object]) -> dict[str, Any]:
        retry_after_seconds: float | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self.client.get(path, params=params, headers={"X-API-Key": self.api_key})
            except httpx.HTTPError as exc:
                if attempt < self.retries:
                    time.sleep(_retry_delay(None, attempt))
                    continue
                raise OpenAQClientError(f"OpenAQ request failed: {exc}") from exc

            if response.status_code == 429:
                self.rate_limit_hits += 1
                retry_after_seconds = _retry_after_seconds(response)
                if attempt < self.retries:
                    time.sleep(_retry_delay(retry_after_seconds, attempt))
                    continue
                raise OpenAQRateLimitError(
                    "OpenAQ rate limit exceeded",
                    retry_after_seconds=retry_after_seconds,
                )

            if response.status_code in {500, 502, 503, 504} and attempt < self.retries:
                time.sleep(_retry_delay(None, attempt))
                continue

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise OpenAQClientError(f"OpenAQ returned HTTP {response.status_code}") from exc

            try:
                parsed = response.json()
            except ValueError as exc:
                raise OpenAQClientError("OpenAQ returned invalid JSON") from exc
            if not isinstance(parsed, dict):
                raise OpenAQClientError("OpenAQ response must be a JSON object")
            return parsed

        raise OpenAQClientError("OpenAQ request retry loop ended unexpectedly")


def _measurement_from_result(raw: dict[str, Any], *, fallback_sensor_id: int) -> OpenAQMeasurement:
    value = _float_or_none(raw.get("value"))
    timestamp = _measurement_timestamp(raw)
    if value is None or timestamp is None:
        raise OpenAQClientError("OpenAQ measurement missing value or timestamp")

    parameter = raw.get("parameter") if isinstance(raw.get("parameter"), dict) else {}
    coordinates = raw.get("coordinates") if isinstance(raw.get("coordinates"), dict) else {}
    flag_info = raw.get("flagInfo") if isinstance(raw.get("flagInfo"), dict) else {}

    return OpenAQMeasurement(
        openaq_sensor_id=_int_or_none(raw.get("sensorsId")) or fallback_sensor_id,
        openaq_location_id=_int_or_none(raw.get("locationsId")),
        pollutant=normalize_pollutant_name(_text_or_none(parameter.get("name"))),
        unit=_text_or_none(parameter.get("units")),
        value=value,
        timestamp=timestamp,
        latitude=_float_or_none(coordinates.get("latitude")),
        longitude=_float_or_none(coordinates.get("longitude")),
        has_flags=_bool_or_none(flag_info.get("hasFlags")),
    )


def normalize_pollutant_name(value: str | None) -> str:
    raw = (value or "unknown").strip().lower().replace("_", "").replace(".", "")
    aliases = {
        "pm25": "pm25",
        "pm10": "pm10",
        "co": "co",
        "carbonmonoxide": "co",
        "no2": "no2",
        "nitrogendioxide": "no2",
        "o3": "o3",
        "ozone": "o3",
        "so2": "so2",
        "sulphurdioxide": "so2",
        "sulfurdioxide": "so2",
    }
    return aliases.get(raw, raw)


def _measurement_timestamp(raw: dict[str, Any]) -> datetime | None:
    period = raw.get("period") if isinstance(raw.get("period"), dict) else {}
    datetime_from = period.get("datetimeFrom") if isinstance(period.get("datetimeFrom"), dict) else {}
    candidates = [
        datetime_from.get("utc"),
        raw.get("datetime"),
        raw.get("date"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return parse_utc(candidate)
    return None


def _results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = payload.get("results")
    if not isinstance(results, list):
        raise OpenAQClientError("OpenAQ response missing results array")
    return [result for result in results if isinstance(result, dict)]


def _found(payload: dict[str, Any]) -> int | None:
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    return _int_or_none(meta.get("found"))


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


def _text_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value))
    except ValueError:
        return None


def _bool_or_none(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return None
