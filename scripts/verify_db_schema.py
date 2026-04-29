from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import psycopg2
from psycopg2.extensions import connection as PgConnection

try:
    from scripts.db_config import sync_database_url
except ModuleNotFoundError:
    from db_config import sync_database_url


REQUIRED_EXTENSIONS = {"timescaledb", "postgis"}
REQUIRED_TABLES = {
    "stations",
    "station_sensors",
    "districts",
    "weather_locations",
    "aq_readings",
    "weather_readings",
    "modeled_aq_readings",
    "forecast_runs",
    "forecasts",
    "forecast_accuracy",
    "pipeline_runs",
    "coverage_snapshots",
    "backfill_manifest",
    "monthly_reports",
    "fire_events",
}
REQUIRED_HYPERTABLES = {"aq_readings", "weather_readings", "modeled_aq_readings"}
REQUIRED_CONTINUOUS_AGGREGATES = {"aq_hourly", "aq_daily", "valley_daily"}
REQUIRED_INDEXES = {
    "idx_stations_location_gist",
    "idx_station_sensors_station",
    "idx_station_sensors_active_pollutant",
    "idx_aq_station_time",
    "idx_aq_station_pollutant_time",
    "idx_aq_source_type_time",
    "idx_weather_location_time",
    "idx_modeled_location_time",
    "idx_modeled_pollutant_time",
    "idx_pipeline_component_run",
    "idx_fire_location_gist",
    "idx_fire_date",
}
REQUIRED_CHECKS = {
    "ck_aq_observation_type",
    "ck_aq_coverage_mode",
    "ck_aq_confidence",
    "ck_modeled_observation_type",
    "ck_modeled_coverage_mode",
    "ck_weather_quality_flag",
    "ck_modeled_quality_flag",
    "ck_coverage_mode",
    "ck_coverage_confidence",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the Phase 03 TimescaleDB/PostGIS schema.")
    parser.add_argument("--database-url", help="Override SYNC_DATABASE_URL or DATABASE_URL for local verification.")
    return parser.parse_args()


def fetch_set(conn: PgConnection, sql: str, params: tuple[Any, ...] = ()) -> set[str]:
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        return {str(row[0]) for row in cursor.fetchall()}


def fetch_rows(conn: PgConnection, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        return list(cursor.fetchall())


def verify(conn: PgConnection) -> dict[str, Any]:
    failures: list[str] = []
    extensions = fetch_set(conn, "SELECT extname FROM pg_extension")
    tables = fetch_set(
        conn,
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """,
    )
    hypertables = fetch_set(conn, "SELECT hypertable_name FROM timescaledb_information.hypertables WHERE hypertable_schema = 'public'")
    continuous_aggregates = fetch_set(
        conn,
        "SELECT view_name FROM timescaledb_information.continuous_aggregates WHERE view_schema = 'public'",
    )
    indexes = fetch_set(conn, "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")
    checks = fetch_set(
        conn,
        """
        SELECT conname
        FROM pg_constraint
        WHERE contype = 'c' AND connamespace = 'public'::regnamespace
        """,
    )

    missing_extensions = sorted(REQUIRED_EXTENSIONS - extensions)
    missing_tables = sorted(REQUIRED_TABLES - tables)
    missing_hypertables = sorted(REQUIRED_HYPERTABLES - hypertables)
    missing_continuous_aggregates = sorted(REQUIRED_CONTINUOUS_AGGREGATES - continuous_aggregates)
    missing_indexes = sorted(REQUIRED_INDEXES - indexes)
    missing_checks = sorted(REQUIRED_CHECKS - checks)

    for label, missing in (
        ("extensions", missing_extensions),
        ("tables", missing_tables),
        ("hypertables", missing_hypertables),
        ("continuous_aggregates", missing_continuous_aggregates),
        ("indexes", missing_indexes),
        ("checks", missing_checks),
    ):
        if missing:
            failures.append(f"missing {label}: {', '.join(missing)}")

    invalid_unique_indexes = unique_hypertable_indexes_without_timestamp(conn)
    if invalid_unique_indexes:
        failures.append("hypertable unique indexes missing timestamp: " + ", ".join(invalid_unique_indexes))

    return {
        "ok": not failures,
        "failures": failures,
        "extensions": sorted(extensions & REQUIRED_EXTENSIONS),
        "tables": sorted(tables & REQUIRED_TABLES),
        "hypertables": sorted(hypertables & REQUIRED_HYPERTABLES),
        "continuous_aggregates": sorted(continuous_aggregates & REQUIRED_CONTINUOUS_AGGREGATES),
        "indexes_checked": sorted(indexes & REQUIRED_INDEXES),
        "checks_checked": sorted(checks & REQUIRED_CHECKS),
    }


def unique_hypertable_indexes_without_timestamp(conn: PgConnection) -> list[str]:
    rows = fetch_rows(
        conn,
        """
        SELECT idx.relname AS index_name,
               tbl.relname AS table_name,
               ARRAY_AGG(att.attname ORDER BY key_position.ordinality) AS indexed_columns
        FROM pg_index ix
        JOIN pg_class idx ON idx.oid = ix.indexrelid
        JOIN pg_class tbl ON tbl.oid = ix.indrelid
        JOIN timescaledb_information.hypertables ht ON ht.hypertable_name = tbl.relname
        JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY AS key_position(attnum, ordinality) ON TRUE
        JOIN pg_attribute att ON att.attrelid = tbl.oid AND att.attnum = key_position.attnum
        WHERE ix.indisunique AND ht.hypertable_schema = 'public'
        GROUP BY idx.relname, tbl.relname
        """,
    )
    invalid: list[str] = []
    for index_name, table_name, indexed_columns in rows:
        if "timestamp" not in indexed_columns:
            invalid.append(f"{table_name}.{index_name}")
    return invalid


def write_json(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def main() -> int:
    args = parse_args()
    try:
        with psycopg2.connect(sync_database_url(args.database_url)) as conn:
            result = verify(conn)
    except psycopg2.Error as exc:
        sys.stderr.write(f"schema verification failed: {exc}\n")
        return 2

    write_json(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
