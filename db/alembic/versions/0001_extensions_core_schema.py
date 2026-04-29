"""create extensions and core registry tables

Revision ID: 0001_extensions_core_schema
Revises:
Create Date: 2026-04-29 00:00:00
"""
from __future__ import annotations

from alembic import op

revision = "0001_extensions_core_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute(
        """
        CREATE TABLE stations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            source VARCHAR(50) NOT NULL DEFAULT 'openaq',
            source_location_id VARCHAR(100),
            location GEOMETRY(POINT, 4326) NOT NULL,
            elevation INTEGER,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            status VARCHAR(30) NOT NULL DEFAULT 'active',
            last_seen TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_stations_source_location UNIQUE (source, source_location_id),
            CONSTRAINT ck_stations_status CHECK (status IN ('active', 'inactive', 'unknown'))
        )
        """
    )
    op.execute("CREATE INDEX idx_stations_location_gist ON stations USING GIST(location)")
    op.execute("CREATE INDEX idx_stations_active_last_seen ON stations(active, last_seen DESC)")
    op.execute(
        """
        CREATE TABLE station_sensors (
            id SERIAL PRIMARY KEY,
            station_id INTEGER NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
            source VARCHAR(30) NOT NULL DEFAULT 'openaq',
            external_sensor_id VARCHAR(100) NOT NULL,
            external_location_id VARCHAR(100),
            pollutant VARCHAR(20) NOT NULL,
            unit VARCHAR(30),
            datetime_first TIMESTAMPTZ,
            datetime_last TIMESTAMPTZ,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            priority INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_station_sensors_source_external UNIQUE (source, external_sensor_id)
        )
        """
    )
    op.execute("CREATE INDEX idx_station_sensors_station ON station_sensors(station_id)")
    op.execute("CREATE INDEX idx_station_sensors_active_pollutant ON station_sensors(active, pollutant)")
    op.execute(
        """
        CREATE TABLE districts (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            boundary GEOMETRY(MULTIPOLYGON, 4326) NOT NULL,
            population INTEGER,
            district_code VARCHAR(20) UNIQUE
        )
        """
    )
    op.execute("CREATE INDEX idx_districts_boundary_gist ON districts USING GIST(boundary)")
    op.execute(
        """
        CREATE TABLE weather_locations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            location GEOMETRY(POINT, 4326) NOT NULL,
            elevation INTEGER,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            CONSTRAINT uq_weather_locations_name UNIQUE (name)
        )
        """
    )
    op.execute("CREATE INDEX idx_weather_locations_location_gist ON weather_locations USING GIST(location)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS weather_locations CASCADE")
    op.execute("DROP TABLE IF EXISTS districts CASCADE")
    op.execute("DROP TABLE IF EXISTS station_sensors CASCADE")
    op.execute("DROP TABLE IF EXISTS stations CASCADE")
    op.execute("DROP EXTENSION IF EXISTS postgis")
    op.execute("DROP EXTENSION IF EXISTS timescaledb")
