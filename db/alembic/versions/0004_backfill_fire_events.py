"""create backfill and fire event tables

Revision ID: 0004_backfill_fire_events
Revises: 0003_forecast_operations
Create Date: 2026-04-29 00:00:03
"""
from __future__ import annotations

from alembic import op

revision = "0004_backfill_fire_events"
down_revision = "0003_forecast_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE backfill_manifest (
            id BIGSERIAL PRIMARY KEY,
            source VARCHAR(50) NOT NULL,
            external_location_id VARCHAR(100),
            external_sensor_id VARCHAR(100),
            date DATE NOT NULL,
            status VARCHAR(30) NOT NULL,
            rows_fetched INTEGER NOT NULL DEFAULT 0,
            rows_written INTEGER NOT NULL DEFAULT 0,
            error_message TEXT,
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            finished_at TIMESTAMPTZ,
            CONSTRAINT uq_backfill_manifest_source_sensor_date UNIQUE (source, external_location_id, external_sensor_id, date),
            CONSTRAINT ck_backfill_manifest_status CHECK (status IN ('success', 'partial', 'failed', 'running', 'skipped'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE fire_events (
            id BIGSERIAL PRIMARY KEY,
            location GEOMETRY(POINT, 4326) NOT NULL,
            latitude NUMERIC(9, 6) NOT NULL,
            longitude NUMERIC(9, 6) NOT NULL,
            acq_date DATE NOT NULL,
            acq_time INTEGER,
            satellite VARCHAR(20),
            instrument VARCHAR(20),
            confidence VARCHAR(30),
            frp NUMERIC(8, 2),
            brightness NUMERIC(8, 2),
            source VARCHAR(50) NOT NULL DEFAULT 'VIIRS_SNPP_NRT',
            event_hash TEXT NOT NULL UNIQUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX idx_fire_location_gist ON fire_events USING GIST(location)")
    op.execute("CREATE INDEX idx_fire_date ON fire_events(acq_date DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS fire_events CASCADE")
    op.execute("DROP TABLE IF EXISTS backfill_manifest CASCADE")
