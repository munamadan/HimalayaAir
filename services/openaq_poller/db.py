from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg2
from psycopg2.extras import Json

from shared.time_utils import format_utc, parse_utc

from services.openaq_poller.models import PollRunResult, SensorRegistryRow


class PollerDatabaseError(RuntimeError):
    pass


class PollerDatabase:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def fetch_active_sensors(self) -> list[SensorRegistryRow]:
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            ss.id,
                            ss.station_id,
                            ss.external_sensor_id,
                            ss.external_location_id,
                            ss.pollutant,
                            ss.unit,
                            s.name,
                            ST_Y(s.location::geometry),
                            ST_X(s.location::geometry)
                        FROM station_sensors ss
                        JOIN stations s ON s.id = ss.station_id
                        WHERE ss.active = TRUE
                          AND s.active = TRUE
                          AND ss.source = 'openaq'
                        ORDER BY ss.priority DESC, ss.id ASC
                        """
                    )
                    return [_sensor_from_row(row) for row in cursor.fetchall()]
        except (psycopg2.Error, ValueError) as exc:
            raise PollerDatabaseError(f"failed to load active OpenAQ sensors: {exc}") from exc

    def latest_success_window_end(self, component: str) -> datetime | None:
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT metadata->>'window_to'
                        FROM pipeline_runs
                        WHERE component = %s
                          AND status IN ('success', 'partial')
                          AND metadata ? 'window_to'
                        ORDER BY run_at DESC
                        LIMIT 1
                        """,
                        (component,),
                    )
                    row = cursor.fetchone()
        except psycopg2.Error as exc:
            raise PollerDatabaseError(f"failed to load latest OpenAQ poller run: {exc}") from exc

        if row is None or row[0] is None:
            return None
        try:
            return parse_utc(str(row[0]))
        except ValueError as exc:
            raise PollerDatabaseError(f"latest OpenAQ poller window_to is invalid: {row[0]}") from exc

    def record_pipeline_run(self, component: str, result: PollRunResult) -> None:
        metadata = dict(result.metadata)
        if result.window is not None:
            metadata["window_from"] = format_utc(result.window.datetime_from)
            metadata["window_to"] = format_utc(result.window.datetime_to)
        metadata["dry_run"] = result.dry_run
        metadata["sensors_attempted"] = result.sensors_attempted
        metadata["sensors_succeeded"] = result.sensors_succeeded
        metadata["sensors_failed"] = result.sensors_failed

        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO pipeline_runs (
                            component,
                            run_at,
                            status,
                            records_processed,
                            error_message,
                            duration_seconds,
                            metadata
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            component,
                            result.finished_at,
                            result.status,
                            result.records_processed,
                            result.error_message,
                            round(result.duration_seconds, 2),
                            Json(metadata),
                        ),
                    )
                conn.commit()
        except psycopg2.Error as exc:
            raise PollerDatabaseError(f"failed to write OpenAQ pipeline run: {exc}") from exc


def _sensor_from_row(row: tuple[Any, ...]) -> SensorRegistryRow:
    external_sensor_id = _required_int(row[2], "external_sensor_id")
    external_location_id = _optional_int(row[3], "external_location_id")
    return SensorRegistryRow(
        sensor_id=int(row[0]),
        station_id=int(row[1]),
        external_sensor_id=external_sensor_id,
        external_location_id=external_location_id,
        pollutant=str(row[4]),
        unit=str(row[5]) if row[5] is not None else None,
        station_name=str(row[6]),
        latitude=float(row[7]) if row[7] is not None else None,
        longitude=float(row[8]) if row[8] is not None else None,
    )


def _required_int(value: object, field_name: str) -> int:
    parsed = _optional_int(value, field_name)
    if parsed is None:
        raise ValueError(f"{field_name} must be numeric")
    return parsed


def _optional_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be numeric") from exc

