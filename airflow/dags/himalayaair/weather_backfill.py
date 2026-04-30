from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import httpx

from services.weather_poller.models import WeatherLocation
from services.weather_poller.openmeteo_client import WEATHER_VARIABLES, OpenMeteoClientError, normalize_weather_response

from himalayaair.database import HimalayaAirDatabase
from himalayaair.models import BackfillManifestResult
from himalayaair.run_utils import (
    configure_task_logger,
    date_window_from_conf,
    int_from_conf,
    record_outcome,
    start_clock,
)
from himalayaair.settings import AirflowTaskSettings


OPENMETEO_ARCHIVE_BASE_URL = "https://archive-api.open-meteo.com"
WEATHER_HISTORY_MANIFEST_SOURCE = "openmeteo_weather_history"
WEATHER_HISTORY_MANIFEST_SENSOR = "weather_history"


@dataclass(frozen=True)
class MonthWindow:
    start_date: date
    end_date: date


class OpenMeteoHistoricalClient:
    def __init__(
        self,
        *,
        timeout_seconds: float,
        retries: int,
        client: httpx.Client | None = None,
        base_url: str = OPENMETEO_ARCHIVE_BASE_URL,
    ) -> None:
        self.retries = retries
        self.client = client or httpx.Client(base_url=base_url, timeout=timeout_seconds)

    def close(self) -> None:
        self.client.close()

    def fetch_weather_history(self, location: WeatherLocation, *, start_date: date, end_date: date) -> dict[str, Any]:
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "hourly": ",".join(WEATHER_VARIABLES),
            "timezone": "UTC",
        }
        for attempt in range(self.retries + 1):
            try:
                response = self.client.get("/v1/archive", params=params)
            except httpx.HTTPError as exc:
                if attempt < self.retries:
                    continue
                raise OpenMeteoClientError(f"Open-Meteo archive request failed: {exc}") from exc

            if response.status_code in {408, 429, 500, 502, 503, 504} and attempt < self.retries:
                continue
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise OpenMeteoClientError(f"Open-Meteo archive returned HTTP {response.status_code}") from exc
            try:
                payload = response.json()
            except ValueError as exc:
                raise OpenMeteoClientError("Open-Meteo archive returned invalid JSON") from exc
            if not isinstance(payload, dict):
                raise OpenMeteoClientError("Open-Meteo archive response must be a JSON object")
            return payload

        raise OpenMeteoClientError("Open-Meteo archive retry loop ended unexpectedly")


def run_weather_historical_backfill(conf: dict[str, Any] | None = None) -> dict[str, object]:
    settings = AirflowTaskSettings.from_env()
    logger = configure_task_logger("weather_historical_backfill", settings)
    database = HimalayaAirDatabase(settings.database_url)
    client = OpenMeteoHistoricalClient(
        timeout_seconds=settings.http_timeout_seconds,
        retries=settings.http_retries,
    )
    try:
        return _run_weather_historical_backfill(
            conf or {},
            settings=settings,
            database=database,
            client=client,
            logger=logger,
        )
    finally:
        client.close()


def _run_weather_historical_backfill(
    conf: dict[str, Any],
    *,
    settings: AirflowTaskSettings,
    database: HimalayaAirDatabase,
    client: OpenMeteoHistoricalClient,
    logger: object,
) -> dict[str, object]:
    component = "airflow_weather_historical_backfill"
    clock = start_clock()
    records_written = 0
    records_fetched = 0
    manifest_rows = 0
    skipped = 0
    failures = 0
    max_days = max(settings.weather_backfill_max_months * 31, 1)
    start_date, end_date = date_window_from_conf(conf, default_days=30, max_days=max_days)
    max_locations = int_from_conf(conf, "max_locations", settings.weather_backfill_max_locations)

    try:
        locations = database.fetch_active_weather_locations(max_locations=max_locations)
        month_windows = month_windows_for_range(start_date, end_date)
        for location in locations:
            for month_window in month_windows:
                manifest_date = month_window.start_date.replace(day=1)
                location_id = str(location.location_id)
                if database.successful_manifest_exists(
                    sources=(WEATHER_HISTORY_MANIFEST_SOURCE,),
                    external_location_id=location_id,
                    external_sensor_id=WEATHER_HISTORY_MANIFEST_SENSOR,
                    run_date=manifest_date,
                ):
                    skipped += 1
                    continue
                try:
                    payload = client.fetch_weather_history(
                        location,
                        start_date=month_window.start_date,
                        end_date=month_window.end_date,
                    )
                    readings = normalize_weather_response(location, payload)
                    written = database.insert_weather_readings(readings)
                    records_fetched += len(readings)
                    records_written += written
                    manifest_rows += 1
                    database.record_backfill_manifest(
                        BackfillManifestResult(
                            source=WEATHER_HISTORY_MANIFEST_SOURCE,
                            external_location_id=location_id,
                            external_sensor_id=WEATHER_HISTORY_MANIFEST_SENSOR,
                            date=manifest_date,
                            status="success",
                            rows_fetched=len(readings),
                            rows_written=written,
                        )
                    )
                except OpenMeteoClientError as exc:
                    failures += 1
                    manifest_rows += 1
                    database.record_backfill_manifest(
                        BackfillManifestResult(
                            source=WEATHER_HISTORY_MANIFEST_SOURCE,
                            external_location_id=location_id,
                            external_sensor_id=WEATHER_HISTORY_MANIFEST_SENSOR,
                            date=manifest_date,
                            status="failed",
                            rows_fetched=0,
                            rows_written=0,
                            error_message=str(exc)[:500],
                        )
                    )

        status = _status(failures=failures, records_written=records_written, skipped=skipped, attempted=manifest_rows)
        metadata = {
            "start_date": str(start_date),
            "end_date": str(end_date),
            "location_count": len(locations),
            "month_windows": len(month_windows),
            "manifest_rows": manifest_rows,
            "records_fetched": records_fetched,
            "records_written": records_written,
            "skipped_manifest_rows": skipped,
            "failures": failures,
        }
        outcome = record_outcome(
            database,
            component=component,
            status=status,
            records_processed=records_written,
            clock=clock,
            metadata=metadata,
            error_message=None if status != "failed" else "weather historical backfill failed",
        )
        logger.info("weather_historical_backfill_complete", status=outcome.status, **metadata)
        return metadata | {"status": status}
    except Exception as exc:
        record_outcome(
            database,
            component=component,
            status="failed",
            records_processed=records_written,
            clock=clock,
            metadata={
                "start_date": str(start_date),
                "end_date": str(end_date),
                "records_written": records_written,
                "records_fetched": records_fetched,
            },
            error_message=str(exc),
        )
        logger.error("weather_historical_backfill_failed", error=str(exc))
        raise


def month_windows_for_range(start_date: date, end_date: date) -> list[MonthWindow]:
    windows: list[MonthWindow] = []
    current = start_date
    while current <= end_date:
        next_month = _first_day_next_month(current)
        window_end = min(end_date, next_month - timedelta(days=1))
        windows.append(MonthWindow(start_date=current, end_date=window_end))
        current = window_end + timedelta(days=1)
    return windows


def _first_day_next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _status(*, failures: int, records_written: int, skipped: int, attempted: int) -> str:
    if failures == 0:
        return "success"
    if records_written > 0 or skipped > 0 or attempted > failures:
        return "partial"
    return "failed"
