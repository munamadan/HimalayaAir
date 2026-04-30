from __future__ import annotations

import csv
import gzip
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from io import BytesIO, StringIO
from typing import Any

import httpx

from services.common.aqi_calculator import calculate_aqi, normalize_pollutant
from services.openaq_poller.models import OpenAQMeasurement
from services.openaq_poller.openaq_client import OpenAQClient, OpenAQClientError
from shared.enums import Confidence, CoverageMode, ObservationType, SourceName
from shared.time_utils import ensure_utc, parse_utc

from himalayaair.database import HimalayaAirDatabase
from himalayaair.models import AQBackfillReading, BackfillManifestResult, StationSensorTarget
from himalayaair.run_utils import (
    configure_task_logger,
    date_window_from_conf,
    int_from_conf,
    iter_dates,
    record_outcome,
    start_clock,
)
from himalayaair.settings import AirflowTaskSettings


OPENAQ_ARCHIVE_BASE_URL = "https://openaq-data-archive.s3.amazonaws.com"
OPENAQ_HISTORICAL_MANIFEST_SOURCES = (SourceName.OPENAQ_ARCHIVE.value, SourceName.OPENAQ_LIVE.value)


class OpenAQArchiveClientError(RuntimeError):
    pass


class OpenAQArchiveNotFound(OpenAQArchiveClientError):
    pass


class OpenAQArchiveClient:
    def __init__(
        self,
        *,
        timeout_seconds: float,
        retries: int,
        client: httpx.Client | None = None,
        base_url: str = OPENAQ_ARCHIVE_BASE_URL,
    ) -> None:
        self.retries = retries
        self.client = client or httpx.Client(base_url=base_url, timeout=timeout_seconds)

    def close(self) -> None:
        self.client.close()

    def fetch_location_day(self, *, location_id: str, day: date) -> bytes:
        path = archive_path(location_id=location_id, day=day)
        for attempt in range(self.retries + 1):
            try:
                response = self.client.get(path)
            except httpx.HTTPError as exc:
                if attempt < self.retries:
                    continue
                raise OpenAQArchiveClientError(f"OpenAQ archive request failed: {exc}") from exc

            if response.status_code in {403, 404}:
                raise OpenAQArchiveNotFound(f"OpenAQ archive object not found: {path}")
            if response.status_code in {408, 429, 500, 502, 503, 504} and attempt < self.retries:
                continue
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise OpenAQArchiveClientError(f"OpenAQ archive returned HTTP {response.status_code}") from exc
            return response.content

        raise OpenAQArchiveClientError("OpenAQ archive retry loop ended unexpectedly")


def archive_path(*, location_id: str, day: date) -> str:
    return (
        f"/records/csv.gz/locationid={location_id}/year={day:%Y}/month={day:%m}/"
        f"location-{location_id}-{day:%Y%m%d}.csv.gz"
    )


def run_openaq_historical_backfill(conf: dict[str, Any] | None = None) -> dict[str, object]:
    settings = AirflowTaskSettings.from_env()
    logger = configure_task_logger("openaq_historical_backfill", settings)
    database = HimalayaAirDatabase(settings.database_url)
    archive_client = OpenAQArchiveClient(
        timeout_seconds=settings.http_timeout_seconds,
        retries=settings.http_retries,
    )
    api_client = (
        OpenAQClient(
            settings.openaq_api_key,
            timeout_seconds=settings.http_timeout_seconds,
            retries=settings.http_retries,
        )
        if settings.openaq_api_key
        else None
    )
    try:
        return _run_openaq_historical_backfill(
            conf or {},
            settings=settings,
            database=database,
            archive_client=archive_client,
            api_client=api_client,
            logger=logger,
        )
    finally:
        archive_client.close()
        if api_client is not None:
            api_client.close()


def _run_openaq_historical_backfill(
    conf: dict[str, Any],
    *,
    settings: AirflowTaskSettings,
    database: HimalayaAirDatabase,
    archive_client: OpenAQArchiveClient,
    api_client: OpenAQClient | None,
    logger: object,
) -> dict[str, object]:
    component = "airflow_openaq_historical_backfill"
    clock = start_clock()
    records_written = 0
    records_fetched = 0
    manifest_rows = 0
    skipped = 0
    failures = 0
    archive_hits = 0
    api_fallbacks = 0
    archive_errors: list[str] = []
    max_days = max(settings.openaq_backfill_max_days, 1)
    start_date, end_date = date_window_from_conf(conf, default_days=1, max_days=max_days)
    max_sensors = int_from_conf(conf, "max_sensors", settings.openaq_backfill_max_sensors)

    try:
        targets = database.fetch_active_sensors(max_sensors=max_sensors)
        days = iter_dates(start_date, end_date)
        by_location: dict[str, list[StationSensorTarget]] = defaultdict(list)
        for target in targets:
            if target.external_location_id is None:
                database.record_backfill_manifest(
                    BackfillManifestResult(
                        source=SourceName.OPENAQ_ARCHIVE.value,
                        external_location_id=None,
                        external_sensor_id=target.external_sensor_id,
                        date=start_date,
                        status="failed",
                        rows_fetched=0,
                        rows_written=0,
                        error_message="sensor has no external_location_id",
                    )
                )
                failures += 1
                continue
            by_location[target.external_location_id].append(target)

        for day in days:
            for location_id, location_targets in sorted(by_location.items()):
                eligible_targets = [
                    target
                    for target in location_targets
                    if not database.successful_manifest_exists(
                        sources=OPENAQ_HISTORICAL_MANIFEST_SOURCES,
                        external_location_id=location_id,
                        external_sensor_id=target.external_sensor_id,
                        run_date=day,
                    )
                ]
                skipped += len(location_targets) - len(eligible_targets)
                if not eligible_targets:
                    continue

                try:
                    archive_bytes = archive_client.fetch_location_day(location_id=location_id, day=day)
                    archive_hits += 1
                    parsed_by_sensor = parse_archive_records(
                        archive_bytes,
                        targets=eligible_targets,
                        source=SourceName.OPENAQ_ARCHIVE.value,
                    )
                    for target in eligible_targets:
                        readings = parsed_by_sensor.get(target.external_sensor_id, [])
                        written = database.insert_aq_readings(readings)
                        records_written += written
                        records_fetched += len(readings)
                        manifest_rows += 1
                        database.record_backfill_manifest(
                            BackfillManifestResult(
                                source=SourceName.OPENAQ_ARCHIVE.value,
                                external_location_id=location_id,
                                external_sensor_id=target.external_sensor_id,
                                date=day,
                                status="success",
                                rows_fetched=len(readings),
                                rows_written=written,
                            )
                        )
                    continue
                except OpenAQArchiveNotFound:
                    pass
                except OpenAQArchiveClientError as exc:
                    archive_errors.append(str(exc))
                    logger.warning("openaq_archive_fetch_failed", location_id=location_id, date=str(day), error=str(exc))

                if api_client is None:
                    for target in eligible_targets:
                        failures += 1
                        manifest_rows += 1
                        database.record_backfill_manifest(
                            BackfillManifestResult(
                                source=SourceName.OPENAQ_LIVE.value,
                                external_location_id=location_id,
                                external_sensor_id=target.external_sensor_id,
                                date=day,
                                status="failed",
                                rows_fetched=0,
                                rows_written=0,
                                error_message="OPENAQ_API_KEY is required for API fallback",
                            )
                        )
                    continue

                api_fallbacks += len(eligible_targets)
                for target in eligible_targets:
                    try:
                        readings = fetch_api_backfill_readings(api_client, target=target, day=day)
                        written = database.insert_aq_readings(readings)
                        records_written += written
                        records_fetched += len(readings)
                        manifest_rows += 1
                        database.record_backfill_manifest(
                            BackfillManifestResult(
                                source=SourceName.OPENAQ_LIVE.value,
                                external_location_id=location_id,
                                external_sensor_id=target.external_sensor_id,
                                date=day,
                                status="success",
                                rows_fetched=len(readings),
                                rows_written=written,
                            )
                        )
                    except OpenAQClientError as exc:
                        failures += 1
                        manifest_rows += 1
                        database.record_backfill_manifest(
                            BackfillManifestResult(
                                source=SourceName.OPENAQ_LIVE.value,
                                external_location_id=location_id,
                                external_sensor_id=target.external_sensor_id,
                                date=day,
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
            "sensor_count": len(targets),
            "manifest_rows": manifest_rows,
            "records_fetched": records_fetched,
            "records_written": records_written,
            "skipped_manifest_rows": skipped,
            "archive_hits": archive_hits,
            "api_fallbacks": api_fallbacks,
            "failures": failures,
            "archive_errors": archive_errors[:10],
        }
        outcome = record_outcome(
            database,
            component=component,
            status=status,
            records_processed=records_written,
            clock=clock,
            metadata=metadata,
            error_message=None if status != "failed" else "OpenAQ historical backfill failed",
        )
        logger.info("openaq_historical_backfill_complete", status=outcome.status, **metadata)
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
        logger.error("openaq_historical_backfill_failed", error=str(exc))
        raise


def parse_archive_records(
    archive_bytes: bytes,
    *,
    targets: list[StationSensorTarget],
    source: str,
) -> dict[str, list[AQBackfillReading]]:
    targets_by_external_sensor_id = {target.external_sensor_id: target for target in targets}
    grouped: dict[str, list[AQBackfillReading]] = defaultdict(list)
    with gzip.GzipFile(fileobj=BytesIO(archive_bytes)) as gzip_file:
        text = gzip_file.read().decode("utf-8")
    reader = csv.DictReader(StringIO(text))
    for row in reader:
        external_sensor_id = _row_text(row, "sensor_id", "sensors_id", "sensorid")
        if external_sensor_id is None:
            continue
        target = targets_by_external_sensor_id.get(external_sensor_id)
        if target is None:
            continue
        reading = _reading_from_archive_row(row, target=target, source=source)
        if reading is not None:
            grouped[target.external_sensor_id].append(reading)
    return dict(grouped)


def fetch_api_backfill_readings(
    api_client: OpenAQClient,
    *,
    target: StationSensorTarget,
    day: date,
) -> list[AQBackfillReading]:
    datetime_from = datetime.combine(day, time.min, tzinfo=UTC)
    datetime_to = datetime_from + timedelta(days=1)
    measurements = api_client.fetch_sensor_measurements(
        int(target.external_sensor_id),
        datetime_from=datetime_from,
        datetime_to=datetime_to,
        limit=1000,
        max_pages=10,
    )
    return [_reading_from_api_measurement(measurement, target=target) for measurement in measurements]


def _reading_from_archive_row(
    row: dict[str, str],
    *,
    target: StationSensorTarget,
    source: str,
) -> AQBackfillReading | None:
    value = _float_or_none(_row_text(row, "value"))
    raw_time = _row_text(row, "datetime", "date", "timestamp", "datetime_utc")
    if value is None or raw_time is None:
        return None
    try:
        timestamp = parse_utc(raw_time)
    except ValueError:
        return None
    pollutant = normalize_pollutant(_row_text(row, "parameter", "pollutant") or target.pollutant)
    unit = normalize_unit(_row_text(row, "unit", "units") or target.unit or "ug/m3")
    coverage_mode, confidence = observed_provenance(timestamp)
    return AQBackfillReading(
        sensor_id=target.sensor_id,
        station_id=target.station_id,
        pollutant=pollutant,
        value=value,
        unit=unit,
        aqi=calculate_aqi(pollutant, value, unit),
        timestamp=timestamp,
        quality_flag="processed",
        observation_type=ObservationType.OBSERVED.value,
        source=source,
        coverage_mode=coverage_mode,
        confidence=confidence,
        original_timestamp=timestamp,
    )


def _reading_from_api_measurement(measurement: OpenAQMeasurement, *, target: StationSensorTarget) -> AQBackfillReading:
    pollutant = normalize_pollutant(measurement.pollutant or target.pollutant)
    unit = normalize_unit(measurement.unit or target.unit or "ug/m3")
    timestamp = ensure_utc(measurement.timestamp)
    coverage_mode, confidence = observed_provenance(timestamp)
    return AQBackfillReading(
        sensor_id=target.sensor_id,
        station_id=target.station_id,
        pollutant=pollutant,
        value=measurement.value,
        unit=unit,
        aqi=calculate_aqi(pollutant, measurement.value, unit),
        timestamp=timestamp,
        quality_flag="processed",
        observation_type=ObservationType.OBSERVED.value,
        source=SourceName.OPENAQ_LIVE.value,
        coverage_mode=coverage_mode,
        confidence=confidence,
        original_timestamp=timestamp,
    )


def observed_provenance(timestamp: datetime, *, now: datetime | None = None) -> tuple[str, str]:
    reference = ensure_utc(now or datetime.now(UTC))
    age = reference - ensure_utc(timestamp)
    if age <= timedelta(hours=2):
        return CoverageMode.LIVE_OBSERVED.value, Confidence.HIGH.value
    return CoverageMode.RECENT_OBSERVED.value, Confidence.MEDIUM.value


def normalize_unit(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "")
    if normalized in {"ug/m3", "ug/m^3"}:
        return "ug/m3"
    return value.strip()


def _row_text(row: dict[str, str], *keys: str) -> str | None:
    normalized = {key.strip().lower(): value for key, value in row.items() if key is not None}
    for key in keys:
        value = normalized.get(key.lower())
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _status(*, failures: int, records_written: int, skipped: int, attempted: int) -> str:
    if failures == 0:
        return "success"
    if records_written > 0 or skipped > 0 or attempted > failures:
        return "partial"
    return "failed"
