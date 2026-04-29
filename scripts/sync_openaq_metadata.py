from __future__ import annotations

import argparse
import sys
from typing import Any

import psycopg2
from psycopg2.extensions import connection as PgConnection

try:
    from scripts.db_config import sync_database_url
    from scripts.source_validation import (
        KathmanduBoundingBox,
        OpenAQClient,
        OpenAQNormalizationResult,
        OpenAQSensor,
        OpenAQStation,
        SourceValidationError,
        build_metadata_report,
        load_json_file,
        normalize_openaq_locations,
        openaq_api_key_from_env,
        parse_datetime,
        write_json_report,
    )
except ModuleNotFoundError:
    from db_config import sync_database_url
    from source_validation import (
        KathmanduBoundingBox,
        OpenAQClient,
        OpenAQNormalizationResult,
        OpenAQSensor,
        OpenAQStation,
        SourceValidationError,
        build_metadata_report,
        load_json_file,
        normalize_openaq_locations,
        openaq_api_key_from_env,
        parse_datetime,
        write_json_report,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover OpenAQ Kathmandu locations and sensors, then optionally upsert station metadata.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and print normalized metadata without writing to the database.",
    )
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Upsert normalized stations and station_sensors into the configured database.",
    )
    parser.add_argument(
        "--database-url",
        help="Override SYNC_DATABASE_URL or DATABASE_URL when --write-db is used.",
    )
    parser.add_argument(
        "--bbox",
        default="85.20,27.55,85.50,27.80",
        help="OpenAQ bbox as min_lon,min_lat,max_lon,max_lat. Defaults to Kathmandu Valley bounds.",
    )
    parser.add_argument("--limit", type=int, default=100, help="OpenAQ page size.")
    parser.add_argument("--max-pages", type=int, default=5, help="Maximum OpenAQ pages to fetch.")
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout in seconds.")
    parser.add_argument("--retries", type=int, default=2, help="Retry count for retryable HTTP failures.")
    parser.add_argument(
        "--api-key-env",
        default="OPENAQ_API_KEY",
        help="Environment variable containing the server-side OpenAQ API key.",
    )
    parser.add_argument(
        "--fixture-location",
        help="Read an OpenAQ locations fixture instead of making a network call.",
    )
    parser.add_argument("--output", help="Write JSON report to this path instead of stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.dry_run and args.write_db:
            raise SourceValidationError("Use either --dry-run or --write-db, not both")
        if not args.dry_run and not args.write_db:
            raise SourceValidationError("Use --dry-run to inspect metadata or --write-db to upsert it")

        bounds = KathmanduBoundingBox.from_csv(args.bbox)
        if args.fixture_location:
            payload = load_json_file(args.fixture_location)
        else:
            client = OpenAQClient(
                openaq_api_key_from_env(args.api_key_env),
                timeout_seconds=args.timeout,
                retries=args.retries,
            )
            payload = client.discover_locations(bounds, limit=args.limit, max_pages=args.max_pages)

        normalization = normalize_openaq_locations(payload)
        report = build_metadata_report(normalization, bounds=bounds, dry_run=args.dry_run)
        if args.write_db:
            write_result = upsert_metadata(normalization, sync_database_url(args.database_url))
            report["write_target"] = "stations,station_sensors"
            report["dry_run"] = False
            report["db_write"] = write_result
        write_json_report(report, args.output)
        return 0
    except SourceValidationError as exc:
        sys.stderr.write(f"source validation failed: {exc}\n")
        return 2


def upsert_metadata(normalization: OpenAQNormalizationResult, database_url: str) -> dict[str, Any]:
    try:
        with psycopg2.connect(database_url) as conn:
            return upsert_openaq_metadata(conn, normalization)
    except psycopg2.Error as exc:
        raise SourceValidationError(f"OpenAQ metadata database upsert failed: {exc}") from exc


def upsert_openaq_metadata(conn: PgConnection, normalization: OpenAQNormalizationResult) -> dict[str, Any]:
    station_ids: dict[int, int] = {}
    stations_written = 0
    sensors_written = 0
    with conn.cursor() as cursor:
        for station in normalization.stations:
            station_id = upsert_station(cursor, station)
            station_ids[station.openaq_location_id] = station_id
            stations_written += 1
        for sensor in normalization.sensors:
            station_id = station_ids.get(sensor.openaq_location_id)
            if station_id is None:
                continue
            upsert_sensor(cursor, sensor, station_id)
            sensors_written += 1
    conn.commit()
    return {"stations_upserted": stations_written, "sensors_upserted": sensors_written}


def upsert_station(cursor: Any, station: OpenAQStation) -> int:
    cursor.execute(
        """
        INSERT INTO stations (name, source, source_location_id, location, active, status, last_seen)
        VALUES (%s, 'openaq', %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s)
        ON CONFLICT (source, source_location_id) DO UPDATE SET
            name = EXCLUDED.name,
            location = EXCLUDED.location,
            active = EXCLUDED.active,
            status = EXCLUDED.status,
            last_seen = EXCLUDED.last_seen,
            updated_at = NOW()
        RETURNING id
        """,
        (
            station.name,
            str(station.openaq_location_id),
            station.longitude,
            station.latitude,
            bool(station.is_monitor),
            "active" if station.is_monitor else "unknown",
            parse_datetime(station.last_seen_utc) if station.last_seen_utc else None,
        ),
    )
    row = cursor.fetchone()
    if row is None:
        raise SourceValidationError(f"OpenAQ station upsert returned no id for {station.openaq_location_id}")
    return int(row[0])


def upsert_sensor(cursor: Any, sensor: OpenAQSensor, station_id: int) -> None:
    cursor.execute(
        """
        INSERT INTO station_sensors (
            station_id,
            source,
            external_sensor_id,
            external_location_id,
            pollutant,
            unit,
            datetime_first,
            datetime_last,
            active,
            priority
        )
        VALUES (%s, 'openaq', %s, %s, %s, %s, %s, %s, %s, 0)
        ON CONFLICT (source, external_sensor_id) DO UPDATE SET
            station_id = EXCLUDED.station_id,
            external_location_id = EXCLUDED.external_location_id,
            pollutant = EXCLUDED.pollutant,
            unit = EXCLUDED.unit,
            datetime_first = EXCLUDED.datetime_first,
            datetime_last = EXCLUDED.datetime_last,
            active = EXCLUDED.active,
            updated_at = NOW()
        """,
        (
            station_id,
            str(sensor.openaq_sensor_id),
            str(sensor.openaq_location_id),
            sensor.pollutant,
            sensor.unit,
            parse_datetime(sensor.first_seen_utc) if sensor.first_seen_utc else None,
            parse_datetime(sensor.last_seen_utc) if sensor.last_seen_utc else None,
            sensor.active,
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
