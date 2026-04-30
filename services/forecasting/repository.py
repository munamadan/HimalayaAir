from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import psycopg2
from psycopg2.extras import Json, execute_values

from services.common.aqi_calculator import calculate_aqi, normalize_pollutant
from services.forecasting.accuracy import ForecastActualPair, build_accuracy_records
from services.forecasting.config import ForecastSettings
from services.forecasting.models import (
    ForecastContext,
    ForecastResult,
    HourlyAQI,
    ModeledAQI,
    PersistenceBaseline,
    WeatherCovariates,
)
from shared.time_utils import ensure_utc


class ForecastRepositoryError(RuntimeError):
    pass


class ForecastRepository:
    def __init__(self, settings: ForecastSettings) -> None:
        self.settings = settings

    def fetch_active_station_ids(self) -> list[int]:
        try:
            with psycopg2.connect(self.settings.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id
                        FROM stations
                        WHERE active = TRUE
                        ORDER BY id ASC
                        LIMIT NULLIF(%s, 0)
                        """,
                        (self.settings.max_stations,),
                    )
                    return [int(row[0]) for row in cursor.fetchall()]
        except psycopg2.Error as exc:
            raise ForecastRepositoryError(f"failed to load active stations: {exc}") from exc

    def build_context(self, *, station_id: int, pollutant: str, generated_at: datetime) -> ForecastContext:
        normalized_pollutant = normalize_pollutant(pollutant)
        history_start = generated_at - timedelta(days=self.settings.history_days)
        bias_start = generated_at - timedelta(days=self.settings.bias_days)
        future_end = generated_at + timedelta(hours=self.settings.horizon_hours)
        try:
            with psycopg2.connect(self.settings.database_url) as conn:
                with conn.cursor() as cursor:
                    station_name = self._fetch_station_name(cursor, station_id)
                    weather_location_id = self._fetch_nearest_weather_location_id(cursor, station_id)
                    observed_history = self._fetch_observed_history(cursor, station_id, normalized_pollutant, history_start, generated_at)
                    weather_history = (
                        self._fetch_weather_covariates(cursor, weather_location_id, history_start, generated_at) if weather_location_id is not None else ()
                    )
                    future_weather = (
                        self._fetch_weather_covariates(cursor, weather_location_id, generated_at, future_end, future=True)
                        if weather_location_id is not None
                        else ()
                    )
                    modeled_history = (
                        self._fetch_modeled_aqi(cursor, weather_location_id, normalized_pollutant, bias_start, generated_at)
                        if weather_location_id is not None
                        else ()
                    )
                    modeled_future = (
                        self._fetch_modeled_aqi(cursor, weather_location_id, normalized_pollutant, generated_at, future_end, future=True)
                        if weather_location_id is not None
                        else ()
                    )
                    baseline = self._fetch_persistence_baseline(cursor, station_id, weather_location_id, normalized_pollutant, generated_at)
        except psycopg2.Error as exc:
            raise ForecastRepositoryError(f"failed to build forecast context for station {station_id}: {exc}") from exc

        return ForecastContext(
            station_id=station_id,
            station_name=station_name,
            pollutant=normalized_pollutant,
            generated_at=generated_at,
            weather_location_id=weather_location_id,
            observed_history=observed_history,
            weather_history=weather_history,
            future_weather=future_weather,
            modeled_history=modeled_history,
            modeled_future=modeled_future,
            persistence_baseline=baseline,
        )

    def write_forecast_run(
        self,
        *,
        generated_at: datetime,
        model_name: str,
        status: str,
        stations_attempted: int,
        stations_succeeded: int,
        fallback_reason: str | None,
        duration_seconds: float,
        results: list[ForecastResult],
    ) -> tuple[int, int]:
        try:
            with psycopg2.connect(self.settings.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO forecast_runs (
                            created_at,
                            model_name,
                            status,
                            stations_attempted,
                            stations_succeeded,
                            fallback_reason,
                            duration_seconds
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            generated_at,
                            model_name,
                            status,
                            stations_attempted,
                            stations_succeeded,
                            fallback_reason,
                            round(duration_seconds, 2),
                        ),
                    )
                    forecast_run_id = int(cursor.fetchone()[0])
                    rows = [
                        (
                            forecast_run_id,
                            result.station_id,
                            point.pollutant,
                            point.predicted_aqi,
                            point.lower_bound,
                            point.upper_bound,
                            point.target_timestamp,
                            result.model_name,
                            result.model_source,
                            result.fallback_reason,
                            result.generated_at,
                        )
                        for result in results
                        for point in result.points
                    ]
                    inserted = 0
                    if rows:
                        execute_values(
                            cursor,
                            """
                            INSERT INTO forecasts (
                                forecast_run_id,
                                station_id,
                                pollutant,
                                predicted_aqi,
                                lower_bound,
                                upper_bound,
                                target_timestamp,
                                model_name,
                                model_source,
                                fallback_reason,
                                created_at
                            )
                            VALUES %s
                            ON CONFLICT (forecast_run_id, station_id, pollutant, target_timestamp) DO NOTHING
                            """,
                            rows,
                        )
                        inserted = int(cursor.rowcount or 0)
                conn.commit()
        except psycopg2.Error as exc:
            raise ForecastRepositoryError(f"failed to write forecasts: {exc}") from exc
        return forecast_run_id, inserted

    def compute_elapsed_accuracy(self, *, now: datetime) -> int:
        try:
            with psycopg2.connect(self.settings.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            f.station_id,
                            f.pollutant,
                            f.created_at,
                            GREATEST(
                                1,
                                ROUND(EXTRACT(EPOCH FROM (f.target_timestamp - f.created_at)) / 3600.0)::int
                            ) AS horizon_hours,
                            f.predicted_aqi,
                            AVG(ar.aqi)::float8 AS actual_aqi
                        FROM forecasts f
                        JOIN aq_readings ar
                          ON ar.station_id = f.station_id
                         AND ar.pollutant = f.pollutant
                         AND ar.timestamp >= f.target_timestamp
                         AND ar.timestamp < f.target_timestamp + INTERVAL '1 hour'
                         AND ar.observation_type = 'observed'
                         AND ar.is_anomaly = FALSE
                         AND ar.aqi IS NOT NULL
                        WHERE f.target_timestamp <= %s
                        GROUP BY
                            f.station_id,
                            f.pollutant,
                            f.created_at,
                            f.target_timestamp,
                            f.predicted_aqi
                        """,
                        (now,),
                    )
                    pairs = [
                        ForecastActualPair(
                            station_id=int(row[0]),
                            pollutant=str(row[1]),
                            forecast_created_at=ensure_utc(row[2]),
                            horizon_hours=int(row[3]),
                            predicted_aqi=int(row[4]),
                            actual_aqi=float(row[5]),
                        )
                        for row in cursor.fetchall()
                    ]
                    records = build_accuracy_records(pairs)
                    if not records:
                        conn.commit()
                        return 0
                    execute_values(
                        cursor,
                        """
                        INSERT INTO forecast_accuracy (
                            station_id,
                            pollutant,
                            forecast_created_at,
                            horizon_hours,
                            mae,
                            rmse
                        )
                        VALUES %s
                        ON CONFLICT (station_id, pollutant, forecast_created_at, horizon_hours) DO NOTHING
                        """,
                        [
                            (
                                record.station_id,
                                record.pollutant,
                                record.forecast_created_at,
                                record.horizon_hours,
                                record.mae,
                                record.rmse,
                            )
                            for record in records
                        ],
                    )
                    inserted = int(cursor.rowcount or 0)
                conn.commit()
        except psycopg2.Error as exc:
            raise ForecastRepositoryError(f"failed to compute forecast accuracy: {exc}") from exc
        return inserted

    def record_pipeline_run(
        self,
        *,
        component: str,
        run_at: datetime,
        status: str,
        records_processed: int,
        duration_seconds: float,
        metadata: dict[str, object],
        error_message: str | None = None,
    ) -> None:
        try:
            with psycopg2.connect(self.settings.database_url) as conn:
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
                        (component, run_at, status, records_processed, error_message, round(duration_seconds, 2), Json(metadata)),
                    )
                conn.commit()
        except psycopg2.Error as exc:
            raise ForecastRepositoryError(f"failed to record forecast pipeline run: {exc}") from exc

    def _fetch_station_name(self, cursor: Any, station_id: int) -> str:
        cursor.execute("SELECT name FROM stations WHERE id = %s AND active = TRUE", (station_id,))
        row = cursor.fetchone()
        if row is None:
            raise ForecastRepositoryError(f"station {station_id} was not found or is inactive")
        return str(row[0])

    def _fetch_nearest_weather_location_id(self, cursor: Any, station_id: int) -> int | None:
        cursor.execute(
            """
            SELECT wl.id
            FROM weather_locations wl
            JOIN stations s ON s.id = %s
            WHERE wl.active = TRUE
            ORDER BY ST_Distance(wl.location::geography, s.location::geography)
            LIMIT 1
            """,
            (station_id,),
        )
        row = cursor.fetchone()
        return int(row[0]) if row is not None else None

    def _fetch_observed_history(
        self,
        cursor: Any,
        station_id: int,
        pollutant: str,
        start: datetime,
        end: datetime,
    ) -> tuple[HourlyAQI, ...]:
        cursor.execute(
            """
            SELECT
                date_trunc('hour', timestamp) AS bucket,
                AVG(aqi)::float8 AS avg_aqi
            FROM aq_readings
            WHERE station_id = %s
              AND pollutant = %s
              AND timestamp >= %s
              AND timestamp < %s
              AND observation_type = 'observed'
              AND source IN ('openaq_live', 'openaq_archive')
              AND is_anomaly = FALSE
              AND aqi IS NOT NULL
            GROUP BY bucket
            ORDER BY bucket ASC
            """,
            (station_id, pollutant, start, end),
        )
        return tuple(HourlyAQI(timestamp=ensure_utc(row[0]), aqi=float(row[1])) for row in cursor.fetchall())

    def _fetch_weather_covariates(
        self,
        cursor: Any,
        location_id: int,
        start: datetime,
        end: datetime,
        *,
        future: bool = False,
    ) -> tuple[WeatherCovariates, ...]:
        start_operator = ">" if future else ">="
        cursor.execute(
            f"""
            SELECT
                date_trunc('hour', timestamp) AS bucket,
                AVG(temp)::float8 AS temp,
                AVG(humidity)::float8 AS humidity,
                AVG(wind_speed)::float8 AS wind_speed,
                AVG(wind_dir)::float8 AS wind_dir,
                AVG(precipitation)::float8 AS precipitation
            FROM weather_readings
            WHERE location_id = %s
              AND timestamp {start_operator} %s
              AND timestamp <= %s
              AND quality_flag = 'complete'
              AND temp IS NOT NULL
              AND humidity IS NOT NULL
              AND wind_speed IS NOT NULL
              AND wind_dir IS NOT NULL
              AND precipitation IS NOT NULL
            GROUP BY bucket
            ORDER BY bucket ASC
            """,
            (location_id, start, end),
        )
        return tuple(
            WeatherCovariates(
                timestamp=ensure_utc(row[0]),
                temp=float(row[1]),
                humidity=float(row[2]),
                wind_speed=float(row[3]),
                wind_dir=float(row[4]),
                precipitation=float(row[5]),
            )
            for row in cursor.fetchall()
        )

    def _fetch_modeled_aqi(
        self,
        cursor: Any,
        location_id: int,
        pollutant: str,
        start: datetime,
        end: datetime,
        *,
        future: bool = False,
    ) -> tuple[ModeledAQI, ...]:
        start_operator = ">" if future else ">="
        cursor.execute(
            f"""
            SELECT DISTINCT ON (timestamp)
                timestamp,
                us_aqi,
                value::float8,
                unit
            FROM modeled_aq_readings
            WHERE model_location_id = %s
              AND pollutant = %s
              AND timestamp {start_operator} %s
              AND timestamp <= %s
              AND source = 'openmeteo_cams'
              AND observation_type = 'modeled'
              AND coverage_mode = 'MODELED_BASELINE'
              AND quality_flag = 'complete'
            ORDER BY timestamp ASC, model_run_at DESC
            """,
            (location_id, pollutant, start, end),
        )
        modeled: list[ModeledAQI] = []
        for row in cursor.fetchall():
            aqi = _modeled_aqi_value(row, pollutant)
            if aqi is not None:
                modeled.append(ModeledAQI(timestamp=ensure_utc(row[0]), aqi=float(aqi)))
        return tuple(modeled)

    def _fetch_persistence_baseline(
        self,
        cursor: Any,
        station_id: int,
        weather_location_id: int | None,
        pollutant: str,
        generated_at: datetime,
    ) -> PersistenceBaseline:
        cursor.execute(
            """
            SELECT aqi, source, timestamp
            FROM aq_readings
            WHERE station_id = %s
              AND pollutant = %s
              AND timestamp <= %s
              AND observation_type IN ('observed', 'replay')
              AND is_anomaly = FALSE
              AND aqi IS NOT NULL
            ORDER BY
              CASE WHEN observation_type = 'observed' THEN 0 ELSE 1 END,
              timestamp DESC
            LIMIT 1
            """,
            (station_id, pollutant, generated_at),
        )
        row = cursor.fetchone()
        if row is not None:
            return PersistenceBaseline(aqi=_clamp_int(row[0]), source=str(row[1]), timestamp=ensure_utc(row[2]))

        if weather_location_id is not None:
            cursor.execute(
                """
                SELECT DISTINCT ON (timestamp)
                    timestamp,
                    us_aqi,
                    value::float8,
                    unit
                FROM modeled_aq_readings
                WHERE model_location_id = %s
                  AND pollutant = %s
                  AND timestamp <= %s
                  AND source = 'openmeteo_cams'
                  AND observation_type = 'modeled'
                  AND coverage_mode = 'MODELED_BASELINE'
                  AND quality_flag = 'complete'
                ORDER BY timestamp DESC, model_run_at DESC
                LIMIT 1
                """,
                (weather_location_id, pollutant, generated_at + timedelta(hours=3)),
            )
            modeled_row = cursor.fetchone()
            if modeled_row is not None:
                aqi = _modeled_aqi_value(modeled_row, pollutant)
                if aqi is not None:
                    return PersistenceBaseline(aqi=_clamp_int(aqi), source="openmeteo_cams", timestamp=ensure_utc(modeled_row[0]))

        return PersistenceBaseline(aqi=self.settings.default_baseline_aqi, source="synthetic_seed", timestamp=None)


def _modeled_aqi_value(row: tuple[Any, ...], pollutant: str) -> int | None:
    if row[1] is not None:
        return _clamp_int(row[1])
    if row[2] is None:
        return None
    return calculate_aqi(pollutant, float(row[2]), str(row[3] or "ug/m3"))


def _clamp_int(value: Any) -> int:
    return max(0, min(500, int(round(float(value)))))
