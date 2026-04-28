from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


OPENAQ_BASE_URL = "https://api.openaq.org"
OPENMETEO_AQ_BASE_URL = "https://air-quality-api.open-meteo.com"

KATHMANDU_BOUNDS = {
    "min_lat": 27.55,
    "max_lat": 27.80,
    "min_lon": 85.20,
    "max_lon": 85.50,
}
KATHMANDU_CENTER = {"lat": 27.7172, "lon": 85.3240}

LIVE_OBSERVED = "LIVE_OBSERVED"
RECENT_OBSERVED = "RECENT_OBSERVED"
MODELED_BASELINE = "MODELED_BASELINE"
STATION_ONLY = "STATION_ONLY"
NO_DATA = "NO_DATA"

OPENMETEO_AQ_VARIABLES = (
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

POLLUTANT_ALIASES = {
    "pm2.5": "pm25",
    "pm2_5": "pm25",
    "pm25": "pm25",
    "pm10": "pm10",
    "co": "co",
    "carbon monoxide": "co",
    "no2": "no2",
    "nitrogen dioxide": "no2",
    "o3": "o3",
    "ozone": "o3",
    "so2": "so2",
    "sulphur dioxide": "so2",
    "sulfur dioxide": "so2",
}


class SourceValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class KathmanduBoundingBox:
    min_lon: float = KATHMANDU_BOUNDS["min_lon"]
    min_lat: float = KATHMANDU_BOUNDS["min_lat"]
    max_lon: float = KATHMANDU_BOUNDS["max_lon"]
    max_lat: float = KATHMANDU_BOUNDS["max_lat"]

    @classmethod
    def from_csv(cls, value: str) -> "KathmanduBoundingBox":
        parts = [part.strip() for part in value.split(",")]
        if len(parts) != 4:
            raise SourceValidationError("bbox must be min_lon,min_lat,max_lon,max_lat")
        try:
            min_lon, min_lat, max_lon, max_lat = (float(part) for part in parts)
        except ValueError as exc:
            raise SourceValidationError("bbox contains a non-numeric value") from exc
        return cls(min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat)

    def to_openaq_param(self) -> str:
        return f"{self.min_lon:.4f},{self.min_lat:.4f},{self.max_lon:.4f},{self.max_lat:.4f}"

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class OpenAQStation:
    openaq_location_id: int
    name: str
    locality: str | None
    latitude: float
    longitude: float
    country_code: str | None
    provider: str | None
    owner: str | None
    is_mobile: bool
    is_monitor: bool
    first_seen_utc: str | None
    last_seen_utc: str | None
    sensor_count: int


@dataclass(frozen=True)
class OpenAQSensor:
    openaq_sensor_id: int
    openaq_location_id: int
    station_name: str
    pollutant: str
    parameter_id: int | None
    unit: str | None
    first_seen_utc: str | None
    last_seen_utc: str | None
    active: bool


@dataclass(frozen=True)
class OpenAQMeasurement:
    openaq_sensor_id: int | None
    openaq_location_id: int | None
    pollutant: str
    unit: str | None
    value: float
    timestamp_utc: str
    latitude: float | None
    longitude: float | None
    has_flags: bool | None
    source: str = "openaq_live"
    observation_type: str = "observed"


@dataclass(frozen=True)
class OpenAQNormalizationResult:
    stations: list[OpenAQStation]
    sensors: list[OpenAQSensor]
    warnings: list[str]


@dataclass(frozen=True)
class OpenMeteoAQAvailability:
    source: str
    observation_type: str
    coverage_mode: str
    modeled_available: bool
    requested_variables: list[str]
    available_variables: list[str]
    missing_variables: list[str]
    first_timestamp: str | None
    latest_timestamp: str | None
    non_null_counts: dict[str, int]
    confidence: str
    message: str


class HttpJsonClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 15.0,
        retries: int = 2,
        user_agent: str = "HimalayaAir-source-validation/1.0",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.user_agent = user_agent

    def get_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = self._url(path, params or {})
        request_headers = {
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        request_headers.update(headers or {})

        for attempt in range(self.retries + 1):
            request = Request(url, headers=request_headers, method="GET")
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    body = response.read().decode("utf-8")
                    parsed = json.loads(body)
                    if not isinstance(parsed, dict):
                        raise SourceValidationError(f"Expected JSON object from {url}")
                    return parsed
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:500]
                if exc.code in {408, 429, 500, 502, 503, 504} and attempt < self.retries:
                    time.sleep(self._retry_delay(exc, attempt))
                    continue
                raise SourceValidationError(f"HTTP {exc.code} from {url}: {detail}") from exc
            except URLError as exc:
                if attempt < self.retries:
                    time.sleep(self._retry_delay(None, attempt))
                    continue
                raise SourceValidationError(f"Network error from {url}: {exc.reason}") from exc
            except json.JSONDecodeError as exc:
                raise SourceValidationError(f"Invalid JSON from {url}") from exc

        raise SourceValidationError(f"Request failed after retries: {url}")

    def _url(self, path: str, params: dict[str, Any]) -> str:
        clean_path = path if path.startswith("/") else f"/{path}"
        filtered_params = {key: value for key, value in params.items() if value is not None}
        if not filtered_params:
            return f"{self.base_url}{clean_path}"
        return f"{self.base_url}{clean_path}?{urlencode(filtered_params)}"

    @staticmethod
    def _retry_delay(exc: HTTPError | None, attempt: int) -> float:
        if exc is not None:
            retry_after = exc.headers.get("Retry-After")
            if retry_after:
                try:
                    return min(float(retry_after), 10.0)
                except ValueError:
                    pass
        return min(0.5 * (2**attempt), 5.0)


class OpenAQClient:
    def __init__(
        self,
        api_key: str | None,
        *,
        http_client: HttpJsonClient | None = None,
        timeout_seconds: float = 15.0,
        retries: int = 2,
    ) -> None:
        if not api_key:
            raise SourceValidationError("OPENAQ_API_KEY is required for live OpenAQ validation calls")
        self.api_key = api_key
        self.http_client = http_client or HttpJsonClient(
            OPENAQ_BASE_URL,
            timeout_seconds=timeout_seconds,
            retries=retries,
        )

    def get_locations(self, bounds: KathmanduBoundingBox, *, page: int, limit: int) -> dict[str, Any]:
        return self.http_client.get_json(
            "/v3/locations",
            params={
                "bbox": bounds.to_openaq_param(),
                "iso": "NP",
                "limit": limit,
                "page": page,
                "order_by": "id",
                "sort_order": "asc",
            },
            headers={"X-API-Key": self.api_key},
        )

    def discover_locations(
        self,
        bounds: KathmanduBoundingBox,
        *,
        limit: int = 100,
        max_pages: int = 5,
    ) -> dict[str, Any]:
        all_results: list[dict[str, Any]] = []
        last_meta: dict[str, Any] = {}
        for page in range(1, max_pages + 1):
            payload = self.get_locations(bounds, page=page, limit=limit)
            results = _results(payload)
            all_results.extend(results)
            last_meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
            found = _int_or_none(last_meta.get("found"))
            if len(results) < limit or (found is not None and len(all_results) >= found):
                break
        return {"meta": last_meta, "results": all_results}

    def get_sensor_measurements(
        self,
        sensor_id: int,
        *,
        datetime_from: datetime,
        datetime_to: datetime,
        limit: int,
    ) -> dict[str, Any]:
        return self.http_client.get_json(
            f"/v3/sensors/{sensor_id}/measurements",
            params={
                "datetime_from": format_utc(datetime_from),
                "datetime_to": format_utc(datetime_to),
                "limit": limit,
                "page": 1,
            },
            headers={"X-API-Key": self.api_key},
        )


class OpenMeteoAQClient:
    def __init__(
        self,
        *,
        http_client: HttpJsonClient | None = None,
        timeout_seconds: float = 15.0,
        retries: int = 2,
    ) -> None:
        self.http_client = http_client or HttpJsonClient(
            OPENMETEO_AQ_BASE_URL,
            timeout_seconds=timeout_seconds,
            retries=retries,
        )

    def fetch_air_quality(
        self,
        *,
        latitude: float,
        longitude: float,
        variables: list[str],
        forecast_days: int,
        past_days: int,
    ) -> dict[str, Any]:
        return self.http_client.get_json(
            "/v1/air-quality",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "hourly": ",".join(variables),
                "timezone": "UTC",
                "forecast_days": forecast_days,
                "past_days": past_days,
            },
        )


def load_json_file(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        parsed = json.load(file)
    if not isinstance(parsed, dict):
        raise SourceValidationError(f"{path} must contain a JSON object")
    return parsed


def write_json_report(report: dict[str, Any], output_path: str | None = None) -> None:
    if output_path:
        with Path(output_path).open("w", encoding="utf-8") as file:
            json.dump(report, file, indent=2, sort_keys=True)
            file.write("\n")
        return
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def normalize_openaq_locations(payload: dict[str, Any]) -> OpenAQNormalizationResult:
    stations: list[OpenAQStation] = []
    sensors: list[OpenAQSensor] = []
    warnings: list[str] = []

    for raw_location in _results(payload):
        location_id = _int_or_none(raw_location.get("id"))
        name = _text_or_none(raw_location.get("name")) or "Unnamed OpenAQ location"
        coordinates = raw_location.get("coordinates") if isinstance(raw_location.get("coordinates"), dict) else {}
        latitude = _float_or_none(coordinates.get("latitude"))
        longitude = _float_or_none(coordinates.get("longitude"))

        if location_id is None:
            warnings.append(f"Skipped OpenAQ location without numeric id: {name}")
            continue
        if latitude is None or longitude is None:
            warnings.append(f"Skipped OpenAQ location {location_id} without coordinates")
            continue

        country = raw_location.get("country") if isinstance(raw_location.get("country"), dict) else {}
        provider = raw_location.get("provider") if isinstance(raw_location.get("provider"), dict) else {}
        owner = raw_location.get("owner") if isinstance(raw_location.get("owner"), dict) else {}
        raw_sensors = raw_location.get("sensors") if isinstance(raw_location.get("sensors"), list) else []
        normalized_sensors = [
            sensor
            for sensor in (
                _normalize_openaq_sensor(raw_sensor, location_id, name, warnings) for raw_sensor in raw_sensors
            )
            if sensor is not None
        ]

        stations.append(
            OpenAQStation(
                openaq_location_id=location_id,
                name=name,
                locality=_text_or_none(raw_location.get("locality")),
                latitude=latitude,
                longitude=longitude,
                country_code=_text_or_none(country.get("code")),
                provider=_text_or_none(provider.get("name")),
                owner=_text_or_none(owner.get("name")),
                is_mobile=bool(raw_location.get("isMobile", False)),
                is_monitor=bool(raw_location.get("isMonitor", False)),
                first_seen_utc=_datetime_text(raw_location.get("datetimeFirst")),
                last_seen_utc=_datetime_text(raw_location.get("datetimeLast")),
                sensor_count=len(normalized_sensors),
            )
        )
        sensors.extend(normalized_sensors)

    return OpenAQNormalizationResult(stations=stations, sensors=sensors, warnings=warnings)


def normalize_openaq_measurements(
    payload: dict[str, Any],
    *,
    sensor_id: int | None = None,
    location_id: int | None = None,
) -> list[OpenAQMeasurement]:
    measurements: list[OpenAQMeasurement] = []
    for raw in _results(payload):
        value = _float_or_none(raw.get("value"))
        parameter = raw.get("parameter") if isinstance(raw.get("parameter"), dict) else {}
        timestamp = _measurement_timestamp(raw)
        if value is None or timestamp is None:
            continue
        coordinates = raw.get("coordinates") if isinstance(raw.get("coordinates"), dict) else {}
        flag_info = raw.get("flagInfo") if isinstance(raw.get("flagInfo"), dict) else {}
        measurements.append(
            OpenAQMeasurement(
                openaq_sensor_id=_int_or_none(raw.get("sensorsId")) or sensor_id,
                openaq_location_id=_int_or_none(raw.get("locationsId")) or location_id,
                pollutant=normalize_pollutant_name(parameter.get("name")),
                unit=_text_or_none(parameter.get("units")),
                value=value,
                timestamp_utc=timestamp,
                latitude=_float_or_none(coordinates.get("latitude")),
                longitude=_float_or_none(coordinates.get("longitude")),
                has_flags=_bool_or_none(flag_info.get("hasFlags")),
            )
        )
    return measurements


def normalize_openmeteo_aq_response(
    payload: dict[str, Any],
    *,
    requested_variables: list[str],
) -> OpenMeteoAQAvailability:
    hourly = payload.get("hourly") if isinstance(payload.get("hourly"), dict) else {}
    times = hourly.get("time") if isinstance(hourly.get("time"), list) else []
    available: list[str] = []
    missing: list[str] = []
    counts: dict[str, int] = {}
    latest_index: int | None = None
    first_index: int | None = None

    for variable in requested_variables:
        values = hourly.get(variable)
        if not isinstance(values, list):
            missing.append(variable)
            counts[variable] = 0
            continue

        non_null_indexes = [index for index, value in enumerate(values) if value is not None]
        counts[variable] = len(non_null_indexes)
        if non_null_indexes:
            available.append(variable)
            variable_first = non_null_indexes[0]
            variable_latest = non_null_indexes[-1]
            first_index = variable_first if first_index is None else min(first_index, variable_first)
            latest_index = variable_latest if latest_index is None else max(latest_index, variable_latest)
        else:
            missing.append(variable)

    modeled_available = any(variable in available for variable in ("pm2_5", "pm10", "us_aqi"))
    coverage_mode = MODELED_BASELINE if modeled_available else NO_DATA
    confidence = "medium" if modeled_available else "low"
    message = (
        "Open-Meteo modeled AQ is available for Kathmandu center."
        if modeled_available
        else "Open-Meteo response did not include usable modeled PM or AQI values."
    )

    return OpenMeteoAQAvailability(
        source="openmeteo_cams",
        observation_type="modeled",
        coverage_mode=coverage_mode,
        modeled_available=modeled_available,
        requested_variables=requested_variables,
        available_variables=available,
        missing_variables=missing,
        first_timestamp=_time_at(times, first_index),
        latest_timestamp=_time_at(times, latest_index),
        non_null_counts=counts,
        confidence=confidence,
        message=message,
    )


def build_metadata_report(
    normalization: OpenAQNormalizationResult,
    *,
    bounds: KathmanduBoundingBox,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "generated_at": format_utc(datetime.now(timezone.utc)),
        "dry_run": dry_run,
        "write_target": "none_phase_01",
        "bounds": bounds.as_dict(),
        "locations_found": len(normalization.stations),
        "sensors_found": len(normalization.sensors),
        "pollutants": pollutant_counts(normalization.sensors),
        "stations": [asdict(station) for station in normalization.stations],
        "sensors": [asdict(sensor) for sensor in normalization.sensors],
        "warnings": normalization.warnings,
    }


def build_coverage_report(
    normalization: OpenAQNormalizationResult,
    *,
    bounds: KathmanduBoundingBox,
    measurements: list[OpenAQMeasurement] | None = None,
    now: datetime | None = None,
    modeled_available: bool = False,
    source: str = "openaq_metadata",
) -> dict[str, Any]:
    current_time = now or datetime.now(timezone.utc)
    station_latest = _station_latest_times(normalization, measurements)
    station_reports = [
        _station_coverage_report(station, station_latest.get(station.openaq_location_id), current_time)
        for station in normalization.stations
    ]
    fresh_station_count = sum(1 for station in station_reports if station["freshness_minutes"] is not None and station["freshness_minutes"] <= 120)
    recent_station_count = sum(1 for station in station_reports if station["freshness_minutes"] is not None and station["freshness_minutes"] <= 1440)
    mode, confidence, message = recommend_coverage_mode(
        fresh_station_count=fresh_station_count,
        recent_station_count=recent_station_count,
        station_count=len(normalization.stations),
        modeled_available=modeled_available,
    )

    return {
        "generated_at": format_utc(current_time),
        "bounds": bounds.as_dict(),
        "source": source,
        "locations_found": len(normalization.stations),
        "sensors_found": len(normalization.sensors),
        "pollutants": pollutant_counts(normalization.sensors),
        "fresh_station_count": fresh_station_count,
        "recent_station_count": recent_station_count,
        "modeled_available": modeled_available,
        "recommended_coverage_mode": mode,
        "confidence": confidence,
        "message": message,
        "stations": station_reports,
        "warnings": normalization.warnings,
    }


def recommend_coverage_mode(
    *,
    fresh_station_count: int,
    recent_station_count: int,
    station_count: int,
    modeled_available: bool,
) -> tuple[str, str, str]:
    if fresh_station_count >= 3:
        return LIVE_OBSERVED, "high", "At least three stations have readings from the last 2 hours."
    if recent_station_count >= 3:
        return RECENT_OBSERVED, "medium", "Using recent observed readings because fewer than three stations are fresh."
    if modeled_available:
        return MODELED_BASELINE, "medium", "Observed station coverage is sparse; modeled AQ fallback is available."
    if station_count > 0:
        return STATION_ONLY, "low", "Observed coverage is insufficient for a heatmap; show station markers only."
    return NO_DATA, "low", "No OpenAQ stations were discovered in the configured Kathmandu bounds."


def pollutant_counts(sensors: list[OpenAQSensor]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for sensor in sensors:
        counts[sensor.pollutant] = counts.get(sensor.pollutant, 0) + 1
    return dict(sorted(counts.items()))


def parse_variables(value: str | None) -> list[str]:
    if not value:
        return list(OPENMETEO_AQ_VARIABLES)
    variables = [item.strip() for item in value.split(",") if item.strip()]
    if not variables:
        raise SourceValidationError("At least one Open-Meteo AQ variable is required")
    return variables


def openaq_api_key_from_env(env_name: str) -> str | None:
    value = os.getenv(env_name)
    if value is None or not value.strip():
        return None
    return value.strip()


def normalize_pollutant_name(value: Any) -> str:
    raw = _text_or_none(value)
    if not raw:
        return "unknown"
    compact = raw.strip().lower().replace("_", ".")
    return POLLUTANT_ALIASES.get(compact, compact.replace(" ", "_").replace(".", ""))


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_openaq_sensor(
    raw_sensor: dict[str, Any],
    location_id: int,
    station_name: str,
    warnings: list[str],
) -> OpenAQSensor | None:
    sensor_id = _int_or_none(raw_sensor.get("id"))
    if sensor_id is None:
        warnings.append(f"Skipped sensor without numeric id at OpenAQ location {location_id}")
        return None
    parameter = raw_sensor.get("parameter") if isinstance(raw_sensor.get("parameter"), dict) else {}
    first_seen = _datetime_text(raw_sensor.get("datetimeFirst"))
    last_seen = _datetime_text(raw_sensor.get("datetimeLast"))
    return OpenAQSensor(
        openaq_sensor_id=sensor_id,
        openaq_location_id=location_id,
        station_name=station_name,
        pollutant=normalize_pollutant_name(parameter.get("name") or raw_sensor.get("name")),
        parameter_id=_int_or_none(parameter.get("id")),
        unit=_text_or_none(parameter.get("units")),
        first_seen_utc=first_seen,
        last_seen_utc=last_seen,
        active=last_seen is not None,
    )


def _results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = payload.get("results")
    if not isinstance(results, list):
        raise SourceValidationError("Expected OpenAQ response object with a results array")
    return [item for item in results if isinstance(item, dict)]


def _station_latest_times(
    normalization: OpenAQNormalizationResult,
    measurements: list[OpenAQMeasurement] | None,
) -> dict[int, datetime]:
    latest_by_location: dict[int, datetime] = {}
    sensor_to_location = {sensor.openaq_sensor_id: sensor.openaq_location_id for sensor in normalization.sensors}

    if measurements is not None:
        for measurement in measurements:
            location_id = measurement.openaq_location_id
            if location_id is None and measurement.openaq_sensor_id is not None:
                location_id = sensor_to_location.get(measurement.openaq_sensor_id)
            timestamp = parse_datetime(measurement.timestamp_utc)
            if location_id is None or timestamp is None:
                continue
            latest_by_location[location_id] = max(timestamp, latest_by_location.get(location_id, timestamp))
        return latest_by_location

    for sensor in normalization.sensors:
        timestamp = parse_datetime(sensor.last_seen_utc)
        if timestamp is None:
            continue
        current = latest_by_location.get(sensor.openaq_location_id)
        latest_by_location[sensor.openaq_location_id] = timestamp if current is None else max(timestamp, current)
    return latest_by_location


def _station_coverage_report(
    station: OpenAQStation,
    latest: datetime | None,
    now: datetime,
) -> dict[str, Any]:
    freshness_minutes = None
    if latest is not None:
        freshness_minutes = max(0, int((now - latest).total_seconds() // 60))
    return {
        "openaq_location_id": station.openaq_location_id,
        "name": station.name,
        "latitude": station.latitude,
        "longitude": station.longitude,
        "sensor_count": station.sensor_count,
        "latest_observed_utc": format_utc(latest) if latest else None,
        "freshness_minutes": freshness_minutes,
        "status": _freshness_status(freshness_minutes),
    }


def _freshness_status(freshness_minutes: int | None) -> str:
    if freshness_minutes is None:
        return "no_recent_measurement"
    if freshness_minutes <= 120:
        return "fresh"
    if freshness_minutes <= 1440:
        return "recent"
    return "stale"


def _measurement_timestamp(raw: dict[str, Any]) -> str | None:
    direct = (
        raw.get("datetime")
        or raw.get("date")
        or raw.get("datetimeTo")
        or raw.get("datetimeFrom")
    )
    timestamp = _datetime_text(direct)
    if timestamp is not None:
        return timestamp

    period = raw.get("period") if isinstance(raw.get("period"), dict) else {}
    return _datetime_text(period.get("datetimeTo") or period.get("datetimeFrom"))


def _datetime_text(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("utc")
    if not isinstance(value, str) or not value.strip():
        return None
    parsed = parse_datetime(value)
    return format_utc(parsed) if parsed else None


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _time_at(times: list[Any], index: int | None) -> str | None:
    if index is None or index >= len(times):
        return None
    value = times[index]
    if not isinstance(value, str):
        return None
    parsed = parse_datetime(value)
    if parsed:
        return format_utc(parsed)
    return value


def _text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return None


def utc_window(hours: int, *, now: datetime | None = None) -> tuple[datetime, datetime]:
    end = now or datetime.now(timezone.utc)
    return end - timedelta(hours=hours), end
