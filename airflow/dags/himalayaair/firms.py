from __future__ import annotations

import csv
import hashlib
from datetime import date
from io import StringIO
from typing import Any

import httpx

from himalayaair.database import HimalayaAirDatabase
from himalayaair.models import BackfillManifestResult, FireEvent
from himalayaair.run_utils import (
    configure_task_logger,
    date_window_from_conf,
    int_from_conf,
    iter_dates,
    parse_date,
    record_outcome,
    start_clock,
    str_from_conf,
)
from himalayaair.settings import AirflowTaskSettings


FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov"
FIRMS_MANIFEST_SOURCE = "firms_daily"


class FirmsClientError(RuntimeError):
    pass


class FirmsClient:
    def __init__(
        self,
        map_key: str,
        *,
        timeout_seconds: float,
        retries: int,
        client: httpx.Client | None = None,
        base_url: str = FIRMS_BASE_URL,
    ) -> None:
        if not map_key:
            raise FirmsClientError("FIRMS_MAP_KEY is required for FIRMS daily load")
        self.map_key = map_key
        self.retries = retries
        self.client = client or httpx.Client(base_url=base_url, timeout=timeout_seconds)

    def close(self) -> None:
        self.client.close()

    def fetch_area_csv(self, *, source: str, bbox: str, day_range: int, request_date: date) -> str:
        path = f"/api/area/csv/{self.map_key}/{source}/{bbox}/{day_range}/{request_date.isoformat()}"
        for attempt in range(self.retries + 1):
            try:
                response = self.client.get(path)
            except httpx.HTTPError as exc:
                if attempt < self.retries:
                    continue
                raise FirmsClientError(f"FIRMS request failed: {exc}") from exc

            if response.status_code in {408, 429, 500, 502, 503, 504} and attempt < self.retries:
                continue
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise FirmsClientError(f"FIRMS returned HTTP {response.status_code}") from exc
            return response.text

        raise FirmsClientError("FIRMS retry loop ended unexpectedly")


def run_firms_daily_load(conf: dict[str, Any] | None = None) -> dict[str, object]:
    settings = AirflowTaskSettings.from_env()
    logger = configure_task_logger("firms_daily_load", settings)
    database = HimalayaAirDatabase(settings.database_url)
    if not settings.firms_map_key:
        clock = start_clock()
        record_outcome(
            database,
            component="airflow_firms_daily_load",
            status="failed",
            records_processed=0,
            clock=clock,
            metadata={"credential_available": False},
            error_message="FIRMS_MAP_KEY is required for FIRMS daily load",
        )
        logger.error("firms_daily_load_failed", error="FIRMS_MAP_KEY is required")
        raise FirmsClientError("FIRMS_MAP_KEY is required for FIRMS daily load")
    client = FirmsClient(
        settings.firms_map_key,
        timeout_seconds=settings.http_timeout_seconds,
        retries=settings.http_retries,
    )
    try:
        return _run_firms_daily_load(conf or {}, settings=settings, database=database, client=client, logger=logger)
    finally:
        client.close()


def _run_firms_daily_load(
    conf: dict[str, Any],
    *,
    settings: AirflowTaskSettings,
    database: HimalayaAirDatabase,
    client: FirmsClient,
    logger: object,
) -> dict[str, object]:
    component = "airflow_firms_daily_load"
    clock = start_clock()
    records_written = 0
    records_fetched = 0
    manifest_rows = 0
    failures = 0
    skipped = 0
    source = str_from_conf(conf, "source", settings.firms_source)
    bbox = str_from_conf(conf, "bbox", settings.firms_bbox)
    day_range = max(int_from_conf(conf, "day_range", settings.firms_day_range), 1)
    date_conf = dict(conf)
    if "date" in date_conf and "start_date" not in date_conf and "end_date" not in date_conf:
        requested_date = parse_date(date_conf["date"], field_name="date")
        date_conf["start_date"] = requested_date.isoformat()
        date_conf["end_date"] = requested_date.isoformat()
    start_date, end_date = date_window_from_conf(date_conf, default_days=1, max_days=5)
    request_dates = iter_dates(start_date, end_date)
    if len(request_dates) > 1:
        day_range = 1

    try:
        for request_date in request_dates:
            manifest_location = f"{source}:{bbox}"
            if database.successful_manifest_exists(
                sources=(FIRMS_MANIFEST_SOURCE,),
                external_location_id=manifest_location,
                external_sensor_id=source,
                run_date=request_date,
            ):
                skipped += 1
                continue
            try:
                csv_text = client.fetch_area_csv(
                    source=source,
                    bbox=bbox,
                    day_range=day_range,
                    request_date=request_date,
                )
                events = parse_firms_csv(csv_text, source=source)
                written = database.insert_fire_events(events)
                records_fetched += len(events)
                records_written += written
                manifest_rows += 1
                database.record_backfill_manifest(
                    BackfillManifestResult(
                        source=FIRMS_MANIFEST_SOURCE,
                        external_location_id=manifest_location,
                        external_sensor_id=source,
                        date=request_date,
                        status="success",
                        rows_fetched=len(events),
                        rows_written=written,
                    )
                )
            except FirmsClientError as exc:
                failures += 1
                manifest_rows += 1
                database.record_backfill_manifest(
                    BackfillManifestResult(
                        source=FIRMS_MANIFEST_SOURCE,
                        external_location_id=manifest_location,
                        external_sensor_id=source,
                        date=request_date,
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
            "source": source,
            "bbox": bbox,
            "day_range": day_range,
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
            error_message=None if status != "failed" else "FIRMS daily load failed",
        )
        logger.info("firms_daily_load_complete", status=outcome.status, **metadata)
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
                "source": source,
                "bbox": bbox,
                "records_written": records_written,
                "records_fetched": records_fetched,
            },
            error_message=str(exc),
        )
        logger.error("firms_daily_load_failed", error=str(exc))
        raise


def parse_firms_csv(csv_text: str, *, source: str) -> list[FireEvent]:
    events: list[FireEvent] = []
    reader = csv.DictReader(StringIO(csv_text))
    for row in reader:
        event = _event_from_row(row, source=source)
        if event is not None:
            events.append(event)
    return events


def event_hash(
    *,
    latitude: float,
    longitude: float,
    acq_date: date,
    acq_time: int | None,
    satellite: str | None,
    instrument: str | None,
) -> str:
    acq_time_text = f"{acq_time:04d}" if acq_time is not None else ""
    payload = (
        f"{latitude:.6f}|{longitude:.6f}|{acq_date.isoformat()}|"
        f"{acq_time_text}|{satellite or ''}|{instrument or ''}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _event_from_row(row: dict[str, str], *, source: str) -> FireEvent | None:
    latitude = _float_or_none(_row_text(row, "latitude", "lat"))
    longitude = _float_or_none(_row_text(row, "longitude", "lon"))
    raw_date = _row_text(row, "acq_date", "acquisition_date")
    if latitude is None or longitude is None or raw_date is None:
        return None
    try:
        acquisition_date = date.fromisoformat(raw_date)
    except ValueError:
        return None
    acq_time = _int_or_none(_row_text(row, "acq_time", "acquisition_time"))
    satellite = _row_text(row, "satellite")
    instrument = _row_text(row, "instrument")
    return FireEvent(
        latitude=latitude,
        longitude=longitude,
        acq_date=acquisition_date,
        acq_time=acq_time,
        satellite=satellite,
        instrument=instrument,
        confidence=_row_text(row, "confidence"),
        frp=_float_or_none(_row_text(row, "frp")),
        brightness=_float_or_none(_row_text(row, "brightness", "bright_ti4", "bright_t31")),
        source=source,
        event_hash=event_hash(
            latitude=latitude,
            longitude=longitude,
            acq_date=acquisition_date,
            acq_time=acq_time,
            satellite=satellite,
            instrument=instrument,
        ),
    )


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


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _status(*, failures: int, records_written: int, skipped: int, attempted: int) -> str:
    if failures == 0:
        return "success"
    if records_written > 0 or skipped > 0 or attempted > failures:
        return "partial"
    return "failed"
