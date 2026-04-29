from __future__ import annotations

from typing import Any

import psycopg2
from psycopg2.extras import Json

from services.weather_poller.models import ModeledAQReading, WeatherLocation, WeatherPollRunResult, WeatherReading


class WeatherPollerDatabaseError(RuntimeError):
    pass


class WeatherPollerDatabase:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def fetch_active_locations(self, *, max_locations: int = 0) -> list[WeatherLocation]:
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            id,
                            name,
                            ST_Y(location::geometry),
                            ST_X(location::geometry),
                            elevation
                        FROM weather_locations
                        WHERE active = TRUE
                        ORDER BY id ASC
                        LIMIT NULLIF(%s, 0)
                        """,
                        (max_locations,),
                    )
                    return [_location_from_row(row) for row in cursor.fetchall()]
        except (psycopg2.Error, ValueError) as exc:
            raise WeatherPollerDatabaseError(f"failed to load active weather locations: {exc}") from exc

    def insert_weather_readings(self, readings: list[WeatherReading]) -> int:
        if not readings:
            return 0
        inserted = 0
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    for reading in readings:
                        cursor.execute(
                            """
                            INSERT INTO weather_readings (
                                location_id,
                                temp,
                                humidity,
                                wind_speed,
                                wind_dir,
                                precipitation,
                                timestamp,
                                source,
                                quality_flag
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (location_id, timestamp) DO NOTHING
                            """,
                            (
                                reading.location_id,
                                reading.temp,
                                reading.humidity,
                                reading.wind_speed,
                                reading.wind_dir,
                                reading.precipitation,
                                reading.timestamp,
                                reading.source,
                                reading.quality_flag,
                            ),
                        )
                        inserted += cursor.rowcount
                conn.commit()
        except psycopg2.Error as exc:
            raise WeatherPollerDatabaseError(f"failed to write weather readings: {exc}") from exc
        return inserted

    def insert_modeled_aq_readings(self, readings: list[ModeledAQReading]) -> int:
        if not readings:
            return 0
        inserted = 0
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    for reading in readings:
                        cursor.execute(
                            """
                            INSERT INTO modeled_aq_readings (
                                model_location_id,
                                source,
                                observation_type,
                                coverage_mode,
                                pollutant,
                                value,
                                unit,
                                us_aqi,
                                timestamp,
                                model_run_at,
                                quality_flag
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (model_location_id, pollutant, timestamp, model_run_at) DO NOTHING
                            """,
                            (
                                reading.model_location_id,
                                reading.source,
                                reading.observation_type,
                                reading.coverage_mode,
                                reading.pollutant,
                                reading.value,
                                reading.unit,
                                reading.us_aqi,
                                reading.timestamp,
                                reading.model_run_at,
                                reading.quality_flag,
                            ),
                        )
                        inserted += cursor.rowcount
                conn.commit()
        except psycopg2.Error as exc:
            raise WeatherPollerDatabaseError(f"failed to write modeled AQ readings: {exc}") from exc
        return inserted

    def record_pipeline_run(self, component: str, result: WeatherPollRunResult) -> None:
        metadata = dict(result.metadata)
        metadata["dry_run"] = result.dry_run
        metadata["locations_attempted"] = result.locations_attempted
        metadata["locations_succeeded"] = result.locations_succeeded
        metadata["locations_failed"] = result.locations_failed
        metadata["weather_records"] = result.weather_records
        metadata["modeled_aq_records"] = result.modeled_aq_records

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
            raise WeatherPollerDatabaseError(f"failed to write weather poller pipeline run: {exc}") from exc


def _location_from_row(row: tuple[Any, ...]) -> WeatherLocation:
    latitude = _required_float(row[2], "latitude")
    longitude = _required_float(row[3], "longitude")
    return WeatherLocation(
        location_id=int(row[0]),
        name=str(row[1]),
        latitude=latitude,
        longitude=longitude,
        elevation=int(row[4]) if row[4] is not None else None,
    )


def _required_float(value: object, field_name: str) -> float:
    if value is None:
        raise ValueError(f"{field_name} is required")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
