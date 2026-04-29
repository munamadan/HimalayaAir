"""create time-series reading hypertables

Revision ID: 0002_timeseries_readings
Revises: 0001_extensions_core_schema
Create Date: 2026-04-29 00:00:01
"""
from __future__ import annotations

from alembic import op

revision = "0002_timeseries_readings"
down_revision = "0001_extensions_core_schema"
branch_labels = None
depends_on = None

OBSERVATION_TYPES = "'observed', 'modeled', 'replay', 'synthetic'"
COVERAGE_MODES = "'LIVE_OBSERVED', 'RECENT_OBSERVED', 'MODELED_BASELINE', 'REPLAY_DEMO', 'STATION_ONLY', 'NO_DATA'"
CONFIDENCE_VALUES = "'high', 'medium', 'low', 'demo'"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE aq_readings (
            sensor_id INTEGER NOT NULL REFERENCES station_sensors(id),
            station_id INTEGER NOT NULL REFERENCES stations(id),
            pollutant VARCHAR(20) NOT NULL,
            value NUMERIC(8, 2) NOT NULL,
            unit VARCHAR(30) NOT NULL,
            aqi INTEGER,
            timestamp TIMESTAMPTZ NOT NULL,
            district_id INTEGER REFERENCES districts(id),
            is_anomaly BOOLEAN NOT NULL DEFAULT FALSE,
            anomaly_reason VARCHAR(80),
            quality_flag VARCHAR(50) NOT NULL DEFAULT 'raw',
            observation_type VARCHAR(30) NOT NULL DEFAULT 'observed',
            source VARCHAR(50) NOT NULL DEFAULT 'openaq_live',
            coverage_mode VARCHAR(40),
            confidence VARCHAR(20),
            original_timestamp TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (sensor_id, timestamp),
            CONSTRAINT ck_aq_observation_type CHECK (observation_type IN ({OBSERVATION_TYPES})),
            CONSTRAINT ck_aq_coverage_mode CHECK (coverage_mode IS NULL OR coverage_mode IN ({COVERAGE_MODES})),
            CONSTRAINT ck_aq_confidence CHECK (confidence IS NULL OR confidence IN ({CONFIDENCE_VALUES}))
        )
        """
    )
    op.execute(
        "SELECT create_hypertable('aq_readings', 'timestamp', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE)"
    )
    op.execute("CREATE INDEX idx_aq_station_time ON aq_readings(station_id, timestamp DESC)")
    op.execute("CREATE INDEX idx_aq_station_pollutant_time ON aq_readings(station_id, pollutant, timestamp DESC)")
    op.execute("CREATE INDEX idx_aq_district_time ON aq_readings(district_id, timestamp DESC)")
    op.execute("CREATE INDEX idx_aq_source_type_time ON aq_readings(source, observation_type, timestamp DESC)")

    op.execute(
        """
        CREATE TABLE weather_readings (
            location_id INTEGER NOT NULL REFERENCES weather_locations(id),
            temp NUMERIC(5, 2),
            humidity NUMERIC(5, 2),
            wind_speed NUMERIC(6, 2),
            wind_dir NUMERIC(5, 1),
            precipitation NUMERIC(6, 2),
            timestamp TIMESTAMPTZ NOT NULL,
            source VARCHAR(50) NOT NULL DEFAULT 'openmeteo_weather',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (location_id, timestamp)
        )
        """
    )
    op.execute(
        "SELECT create_hypertable('weather_readings', 'timestamp', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE)"
    )
    op.execute("CREATE INDEX idx_weather_location_time ON weather_readings(location_id, timestamp DESC)")

    op.execute(
        f"""
        CREATE TABLE modeled_aq_readings (
            model_location_id INTEGER NOT NULL REFERENCES weather_locations(id),
            source VARCHAR(50) NOT NULL DEFAULT 'openmeteo_cams',
            observation_type VARCHAR(30) NOT NULL DEFAULT 'modeled',
            coverage_mode VARCHAR(40) NOT NULL DEFAULT 'MODELED_BASELINE',
            pollutant VARCHAR(20) NOT NULL,
            value NUMERIC(8, 2),
            unit VARCHAR(30),
            us_aqi INTEGER,
            timestamp TIMESTAMPTZ NOT NULL,
            model_run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (model_location_id, pollutant, timestamp, model_run_at),
            CONSTRAINT ck_modeled_observation_type CHECK (observation_type IN ({OBSERVATION_TYPES})),
            CONSTRAINT ck_modeled_coverage_mode CHECK (coverage_mode IN ({COVERAGE_MODES}))
        )
        """
    )
    op.execute(
        "SELECT create_hypertable('modeled_aq_readings', 'timestamp', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE)"
    )
    op.execute("CREATE INDEX idx_modeled_location_time ON modeled_aq_readings(model_location_id, timestamp DESC)")
    op.execute("CREATE INDEX idx_modeled_pollutant_time ON modeled_aq_readings(pollutant, timestamp DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS modeled_aq_readings CASCADE")
    op.execute("DROP TABLE IF EXISTS weather_readings CASCADE")
    op.execute("DROP TABLE IF EXISTS aq_readings CASCADE")
