"""create forecast and operations tables

Revision ID: 0003_forecast_operations
Revises: 0002_timeseries_readings
Create Date: 2026-04-29 00:00:02
"""
from __future__ import annotations

from alembic import op

revision = "0003_forecast_operations"
down_revision = "0002_timeseries_readings"
branch_labels = None
depends_on = None

COVERAGE_MODES = "'LIVE_OBSERVED', 'RECENT_OBSERVED', 'MODELED_BASELINE', 'REPLAY_DEMO', 'STATION_ONLY', 'NO_DATA'"
CONFIDENCE_VALUES = "'high', 'medium', 'low', 'demo'"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE forecast_runs (
            id BIGSERIAL PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            model_name VARCHAR(80) NOT NULL,
            status VARCHAR(30) NOT NULL,
            stations_attempted INTEGER NOT NULL DEFAULT 0,
            stations_succeeded INTEGER NOT NULL DEFAULT 0,
            fallback_reason TEXT,
            error_message TEXT,
            duration_seconds NUMERIC(8, 2),
            CONSTRAINT ck_forecast_runs_status CHECK (status IN ('success', 'partial', 'failed', 'running'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE forecasts (
            forecast_run_id BIGINT NOT NULL REFERENCES forecast_runs(id) ON DELETE CASCADE,
            station_id INTEGER NOT NULL REFERENCES stations(id),
            pollutant VARCHAR(20) NOT NULL,
            predicted_aqi INTEGER NOT NULL,
            lower_bound NUMERIC(6, 2),
            upper_bound NUMERIC(6, 2),
            target_timestamp TIMESTAMPTZ NOT NULL,
            model_name VARCHAR(80) NOT NULL,
            model_source VARCHAR(80) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (forecast_run_id, station_id, pollutant, target_timestamp)
        )
        """
    )
    op.execute("CREATE INDEX idx_forecasts_latest ON forecasts(station_id, pollutant, target_timestamp DESC)")
    op.execute("CREATE INDEX idx_forecasts_created ON forecasts(created_at DESC)")
    op.execute(
        """
        CREATE TABLE forecast_accuracy (
            id SERIAL PRIMARY KEY,
            station_id INTEGER NOT NULL REFERENCES stations(id),
            pollutant VARCHAR(20) NOT NULL,
            forecast_created_at TIMESTAMPTZ NOT NULL,
            horizon_hours INTEGER NOT NULL,
            mae NUMERIC(6, 2),
            rmse NUMERIC(6, 2),
            computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_forecast_accuracy UNIQUE (station_id, pollutant, forecast_created_at, horizon_hours)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE pipeline_runs (
            id BIGSERIAL PRIMARY KEY,
            component VARCHAR(80) NOT NULL,
            run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            status VARCHAR(30) NOT NULL,
            records_processed INTEGER,
            error_message TEXT,
            duration_seconds NUMERIC(8, 2),
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            CONSTRAINT ck_pipeline_runs_status CHECK (status IN ('success', 'partial', 'failed', 'running'))
        )
        """
    )
    op.execute("CREATE INDEX idx_pipeline_component_run ON pipeline_runs(component, run_at DESC)")
    op.execute(
        f"""
        CREATE TABLE coverage_snapshots (
            id BIGSERIAL PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            coverage_mode VARCHAR(40) NOT NULL,
            confidence VARCHAR(20) NOT NULL,
            fresh_station_count INTEGER NOT NULL DEFAULT 0,
            recent_station_count INTEGER NOT NULL DEFAULT 0,
            modeled_available BOOLEAN NOT NULL DEFAULT FALSE,
            replay_active BOOLEAN NOT NULL DEFAULT FALSE,
            message TEXT,
            CONSTRAINT ck_coverage_mode CHECK (coverage_mode IN ({COVERAGE_MODES})),
            CONSTRAINT ck_coverage_confidence CHECK (confidence IN ({CONFIDENCE_VALUES}))
        )
        """
    )
    op.execute("CREATE INDEX idx_coverage_created ON coverage_snapshots(created_at DESC)")
    op.execute(
        """
        CREATE TABLE monthly_reports (
            id SERIAL PRIMARY KEY,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            avg_aqi NUMERIC(6, 2),
            max_aqi INTEGER,
            worst_day DATE,
            dominant_pollutant VARCHAR(20),
            station_count INTEGER,
            generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_monthly_reports_year_month UNIQUE (year, month),
            CONSTRAINT ck_monthly_reports_month CHECK (month BETWEEN 1 AND 12)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS monthly_reports CASCADE")
    op.execute("DROP TABLE IF EXISTS coverage_snapshots CASCADE")
    op.execute("DROP TABLE IF EXISTS pipeline_runs CASCADE")
    op.execute("DROP TABLE IF EXISTS forecast_accuracy CASCADE")
    op.execute("DROP TABLE IF EXISTS forecasts CASCADE")
    op.execute("DROP TABLE IF EXISTS forecast_runs CASCADE")
