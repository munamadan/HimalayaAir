from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from typing import Any

import psycopg2
from psycopg2.extensions import connection as PgConnection

try:
    from scripts.db_config import sync_database_url
except ModuleNotFoundError:
    from db_config import sync_database_url


@dataclass(frozen=True)
class WeatherLocationSeed:
    name: str
    latitude: float
    longitude: float
    elevation: int | None = None


WEATHER_LOCATIONS = [
    WeatherLocationSeed("Kathmandu Center", 27.7172, 85.3240, 1400),
    WeatherLocationSeed("Lalitpur", 27.6644, 85.3238, 1350),
    WeatherLocationSeed("Bhaktapur", 27.6710, 85.4298, 1401),
    WeatherLocationSeed("Kirtipur", 27.6780, 85.2768, 1410),
    WeatherLocationSeed("Budhanilkantha", 27.7811, 85.3639, 1500),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed Kathmandu Valley Open-Meteo weather locations.")
    parser.add_argument("--dry-run", action="store_true", help="Report rows that would be upserted without writing to the database.")
    parser.add_argument("--database-url", help="Override SYNC_DATABASE_URL or DATABASE_URL for local verification.")
    return parser.parse_args()


def write_json(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def upsert_weather_locations(conn: PgConnection) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with conn.cursor() as cursor:
        for location in WEATHER_LOCATIONS:
            cursor.execute(
                """
                INSERT INTO weather_locations (name, location, elevation, active)
                VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, TRUE)
                ON CONFLICT (name) DO UPDATE SET
                    location = EXCLUDED.location,
                    elevation = EXCLUDED.elevation,
                    active = EXCLUDED.active
                RETURNING id, name
                """,
                (location.name, location.longitude, location.latitude, location.elevation),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError(f"weather location upsert returned no row for {location.name}")
            rows.append({"id": row[0], "name": row[1]})
    conn.commit()
    return rows


def main() -> int:
    args = parse_args()
    seed_rows = [asdict(location) for location in WEATHER_LOCATIONS]
    if args.dry_run:
        write_json({"dry_run": True, "write_target": "weather_locations", "rows": seed_rows, "row_count": len(seed_rows)})
        return 0

    try:
        with psycopg2.connect(sync_database_url(args.database_url)) as conn:
            written_rows = upsert_weather_locations(conn)
    except psycopg2.Error as exc:
        sys.stderr.write(f"weather location seed failed: {exc}\n")
        return 2
    except RuntimeError as exc:
        sys.stderr.write(f"weather location seed failed: {exc}\n")
        return 2

    write_json({"dry_run": False, "write_target": "weather_locations", "rows": written_rows, "row_count": len(written_rows)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
