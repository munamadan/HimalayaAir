from __future__ import annotations

from datetime import date, datetime
from typing import Any

import psycopg2
from psycopg2.extras import Json

from himalayaair.models import (
    AQBackfillReading,
    BackfillManifestResult,
    DataQualityState,
    FireEvent,
    PipelineOutcome,
    StationSensorTarget,
)
from services.weather_poller.models import WeatherLocation, WeatherReading


class AirflowDatabaseError(RuntimeError):
    pass


class HimalayaAirDatabase:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def fetch_active_sensors(self, *, max_sensors: int = 0) -> list[StationSensorTarget]:
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
                        LIMIT NULLIF(%s, 0)
                        """,
                        (max_sensors,),
                    )
                    return [_sensor_from_row(row) for row in cursor.fetchall()]
        except (psycopg2.Error, ValueError) as exc:
            raise AirflowDatabaseError(f"failed to load active OpenAQ sensors: {exc}") from exc

    def fetch_active_weather_locations(self, *, max_locations: int = 0) -> list[WeatherLocation]:
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
                    return [_weather_location_from_row(row) for row in cursor.fetchall()]
        except (psycopg2.Error, ValueError) as exc:
            raise AirflowDatabaseError(f"failed to load active weather locations: {exc}") from exc

    def successful_manifest_exists(
        self,
        *,
        sources: tuple[str, ...],
        external_location_id: str | None,
        external_sensor_id: str | None,
        run_date: date,
    ) -> bool:
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT 1
                        FROM backfill_manifest
                        WHERE source = ANY(%s)
                          AND COALESCE(external_location_id, '') = COALESCE(%s, '')
                          AND COALESCE(external_sensor_id, '') = COALESCE(%s, '')
                          AND date = %s
                          AND status IN ('success', 'partial', 'skipped')
                        LIMIT 1
                        """,
                        (list(sources), external_location_id, external_sensor_id, run_date),
                    )
                    return cursor.fetchone() is not None
        except psycopg2.Error as exc:
            raise AirflowDatabaseError(f"failed to read backfill manifest: {exc}") from exc

    def insert_aq_readings(self, readings: list[AQBackfillReading]) -> int:
        if not readings:
            return 0
        inserted = 0
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    for reading in readings:
                        cursor.execute(
                            """
                            INSERT INTO aq_readings (
                                sensor_id,
                                station_id,
                                pollutant,
                                value,
                                unit,
                                aqi,
                                timestamp,
                                quality_flag,
                                observation_type,
                                source,
                                coverage_mode,
                                confidence,
                                original_timestamp
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (sensor_id, timestamp) DO NOTHING
                            """,
                            (
                                reading.sensor_id,
                                reading.station_id,
                                reading.pollutant,
                                reading.value,
                                reading.unit,
                                reading.aqi,
                                reading.timestamp,
                                reading.quality_flag,
                                reading.observation_type,
                                reading.source,
                                reading.coverage_mode,
                                reading.confidence,
                                reading.original_timestamp,
                            ),
                        )
                        inserted += cursor.rowcount

                    for reading in readings:
                        cursor.execute(
                            """
                            UPDATE station_sensors
                            SET datetime_last = GREATEST(COALESCE(datetime_last, %s), %s),
                                updated_at = NOW()
                            WHERE id = %s
                            """,
                            (reading.timestamp, reading.timestamp, reading.sensor_id),
                        )
                        cursor.execute(
                            """
                            UPDATE stations
                            SET last_seen = GREATEST(COALESCE(last_seen, %s), %s),
                                updated_at = NOW()
                            WHERE id = %s
                            """,
                            (reading.timestamp, reading.timestamp, reading.station_id),
                        )
                conn.commit()
        except psycopg2.Error as exc:
            raise AirflowDatabaseError(f"failed to write AQ backfill readings: {exc}") from exc
        return inserted

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
            raise AirflowDatabaseError(f"failed to write weather backfill readings: {exc}") from exc
        return inserted

    def record_backfill_manifest(self, result: BackfillManifestResult) -> None:
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO backfill_manifest (
                            source,
                            external_location_id,
                            external_sensor_id,
                            date,
                            status,
                            rows_fetched,
                            rows_written,
                            error_message,
                            started_at,
                            finished_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (source, external_location_id, external_sensor_id, date)
                        DO UPDATE SET
                            status = EXCLUDED.status,
                            rows_fetched = EXCLUDED.rows_fetched,
                            rows_written = EXCLUDED.rows_written,
                            error_message = EXCLUDED.error_message,
                            finished_at = EXCLUDED.finished_at
                        """,
                        (
                            result.source,
                            result.external_location_id,
                            result.external_sensor_id,
                            result.date,
                            result.status,
                            result.rows_fetched,
                            result.rows_written,
                            result.error_message,
                        ),
                    )
                conn.commit()
        except psycopg2.Error as exc:
            raise AirflowDatabaseError(f"failed to write backfill manifest: {exc}") from exc

    def insert_fire_events(self, events: list[FireEvent]) -> int:
        if not events:
            return 0
        inserted = 0
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    for event in events:
                        cursor.execute(
                            """
                            INSERT INTO fire_events (
                                location,
                                latitude,
                                longitude,
                                acq_date,
                                acq_time,
                                satellite,
                                instrument,
                                confidence,
                                frp,
                                brightness,
                                source,
                                event_hash
                            )
                            VALUES (
                                ST_SetSRID(ST_Point(%s, %s), 4326),
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s
                            )
                            ON CONFLICT (event_hash) DO NOTHING
                            """,
                            (
                                event.longitude,
                                event.latitude,
                                event.latitude,
                                event.longitude,
                                event.acq_date,
                                event.acq_time,
                                event.satellite,
                                event.instrument,
                                event.confidence,
                                event.frp,
                                event.brightness,
                                event.source,
                                event.event_hash,
                            ),
                        )
                        inserted += cursor.rowcount
                conn.commit()
        except psycopg2.Error as exc:
            raise AirflowDatabaseError(f"failed to write FIRMS fire events: {exc}") from exc
        return inserted

    def evaluate_data_quality(
        self,
        *,
        fresh_hours: int,
        recent_hours: int,
        dead_sensor_days: int,
    ) -> DataQualityState:
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    fresh_station_count = _count_distinct_stations(cursor, hours=fresh_hours)
                    recent_station_count = _count_distinct_stations(cursor, hours=recent_hours)
                    modeled_available = _modeled_available(cursor, hours=recent_hours)
                    replay_active = _replay_active(cursor, hours=recent_hours)
                    invalid_value_count = _invalid_value_count(cursor, hours=recent_hours)
                    anomaly_rate = _anomaly_rate(cursor, hours=recent_hours)
                    dead_sensors_deactivated = _deactivate_dead_sensors(cursor, days=dead_sensor_days)
                    state, coverage_mode, confidence, message = classify_quality_state(
                        fresh_station_count=fresh_station_count,
                        recent_station_count=recent_station_count,
                        modeled_available=modeled_available,
                        invalid_value_count=invalid_value_count,
                        anomaly_rate=anomaly_rate,
                    )
                    cursor.execute(
                        """
                        INSERT INTO coverage_snapshots (
                            coverage_mode,
                            confidence,
                            fresh_station_count,
                            recent_station_count,
                            modeled_available,
                            replay_active,
                            message
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            coverage_mode,
                            confidence,
                            fresh_station_count,
                            recent_station_count,
                            modeled_available,
                            replay_active,
                            message,
                        ),
                    )
                conn.commit()
        except psycopg2.Error as exc:
            raise AirflowDatabaseError(f"failed to evaluate data quality: {exc}") from exc

        return DataQualityState(
            state=state,
            coverage_mode=coverage_mode,
            confidence=confidence,
            fresh_station_count=fresh_station_count,
            recent_station_count=recent_station_count,
            modeled_available=modeled_available,
            replay_active=replay_active,
            invalid_value_count=invalid_value_count,
            anomaly_rate=anomaly_rate,
            dead_sensors_deactivated=dead_sensors_deactivated,
            message=message,
        )

    def record_pipeline_run(self, outcome: PipelineOutcome) -> None:
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
                            outcome.component,
                            outcome.finished_at,
                            outcome.status,
                            outcome.records_processed,
                            outcome.error_message,
                            round(outcome.duration_seconds, 2),
                            Json(outcome.metadata),
                        ),
                    )
                conn.commit()
        except psycopg2.Error as exc:
            raise AirflowDatabaseError(f"failed to write pipeline run: {exc}") from exc


def _sensor_from_row(row: tuple[Any, ...]) -> StationSensorTarget:
    return StationSensorTarget(
        sensor_id=int(row[0]),
        station_id=int(row[1]),
        external_sensor_id=str(row[2]),
        external_location_id=str(row[3]) if row[3] is not None else None,
        pollutant=str(row[4]),
        unit=str(row[5]) if row[5] is not None else None,
        station_name=str(row[6]),
        latitude=float(row[7]) if row[7] is not None else None,
        longitude=float(row[8]) if row[8] is not None else None,
    )


def _weather_location_from_row(row: tuple[Any, ...]) -> WeatherLocation:
    return WeatherLocation(
        location_id=int(row[0]),
        name=str(row[1]),
        latitude=float(row[2]),
        longitude=float(row[3]),
        elevation=int(row[4]) if row[4] is not None else None,
    )


def _count_distinct_stations(cursor: object, *, hours: int) -> int:
    cursor.execute(
        """
        SELECT COUNT(DISTINCT station_id)::int
        FROM aq_readings
        WHERE timestamp >= NOW() - (%s::text || ' hours')::interval
          AND observation_type = 'observed'
          AND source IN ('openaq_live', 'openaq_archive')
        """,
        (hours,),
    )
    return int(cursor.fetchone()[0] or 0)


def _modeled_available(cursor: object, *, hours: int) -> bool:
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM modeled_aq_readings
            WHERE timestamp >= NOW() - (%s::text || ' hours')::interval
              AND source = 'openmeteo_cams'
              AND observation_type = 'modeled'
              AND coverage_mode = 'MODELED_BASELINE'
        )
        """,
        (hours,),
    )
    return bool(cursor.fetchone()[0])


def _replay_active(cursor: object, *, hours: int) -> bool:
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM aq_readings
            WHERE timestamp >= NOW() - (%s::text || ' hours')::interval
              AND observation_type = 'replay'
              AND coverage_mode = 'REPLAY_DEMO'
        )
        """,
        (hours,),
    )
    return bool(cursor.fetchone()[0])


def _invalid_value_count(cursor: object, *, hours: int) -> int:
    cursor.execute(
        """
        SELECT COUNT(*)::int
        FROM aq_readings
        WHERE timestamp >= NOW() - (%s::text || ' hours')::interval
          AND (
            value < 0
            OR (pollutant = 'pm25' AND value > 1000)
            OR (pollutant = 'pm10' AND value > 2000)
            OR (pollutant IN ('co', 'no2', 'o3', 'so2') AND value > 5000)
          )
        """,
        (hours,),
    )
    return int(cursor.fetchone()[0] or 0)


def _anomaly_rate(cursor: object, *, hours: int) -> float | None:
    cursor.execute(
        """
        SELECT COUNT(*)::int, COUNT(*) FILTER (WHERE is_anomaly)::int
        FROM aq_readings
        WHERE timestamp >= NOW() - (%s::text || ' hours')::interval
        """,
        (hours,),
    )
    total, anomalies = cursor.fetchone()
    total_int = int(total or 0)
    if total_int == 0:
        return None
    return float(anomalies or 0) / total_int


def _deactivate_dead_sensors(cursor: object, *, days: int) -> int:
    cursor.execute(
        """
        UPDATE station_sensors
        SET active = FALSE,
            updated_at = NOW()
        WHERE active = TRUE
          AND (
            datetime_last < NOW() - (%s::text || ' days')::interval
            OR (datetime_last IS NULL AND created_at < NOW() - (%s::text || ' days')::interval)
          )
        """,
        (days, days),
    )
    return int(cursor.rowcount or 0)


def classify_quality_state(
    *,
    fresh_station_count: int,
    recent_station_count: int,
    modeled_available: bool,
    invalid_value_count: int,
    anomaly_rate: float | None,
) -> tuple[str, str, str, str]:
    if invalid_value_count > 0:
        return "down", "NO_DATA", "low", f"{invalid_value_count} invalid AQ value(s) found in the recent window"
    if anomaly_rate is not None and anomaly_rate > 0.5:
        return "down", "NO_DATA", "low", f"recent anomaly rate is {anomaly_rate:.2f}"
    if fresh_station_count >= 3:
        return "healthy", "LIVE_OBSERVED", "high", "fresh observed station coverage is sufficient"
    if recent_station_count >= 3:
        return "degraded", "RECENT_OBSERVED", "medium", "fresh station coverage is sparse; recent observed coverage is available"
    if modeled_available:
        return "degraded", "MODELED_BASELINE", "low", "observed station coverage is sparse; modeled AQ fallback is available"
    if recent_station_count > 0:
        return "degraded", "STATION_ONLY", "low", "fewer than 3 recent observed stations are available"
    return "down", "NO_DATA", "low", "no observed or modeled AQ data is available in the recent window"
