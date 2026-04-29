"""create air-quality continuous aggregates

Revision ID: 0005_continuous_aggregates
Revises: 0004_backfill_fire_events
Create Date: 2026-04-29 00:00:04
"""
from __future__ import annotations

from alembic import op

revision = "0005_continuous_aggregates"
down_revision = "0004_backfill_fire_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE MATERIALIZED VIEW aq_hourly
        WITH (timescaledb.continuous) AS
        SELECT
            station_id,
            pollutant,
            time_bucket('1 hour', timestamp) AS hour_bucket,
            AVG(value) AS avg_value,
            AVG(aqi) AS avg_aqi,
            MAX(aqi) AS max_aqi,
            COUNT(*) AS reading_count
        FROM aq_readings
        WHERE NOT is_anomaly
        GROUP BY station_id, pollutant, hour_bucket
        WITH NO DATA
        """
    )
    op.execute(
        """
        CREATE MATERIALIZED VIEW aq_daily
        WITH (timescaledb.continuous) AS
        SELECT
            station_id,
            pollutant,
            time_bucket('1 day', timestamp) AS day_bucket,
            AVG(value) AS avg_value,
            AVG(aqi) AS avg_aqi,
            MAX(aqi) AS max_aqi,
            COUNT(*) AS reading_count
        FROM aq_readings
        WHERE NOT is_anomaly
        GROUP BY station_id, pollutant, day_bucket
        WITH NO DATA
        """
    )
    op.execute(
        """
        CREATE MATERIALIZED VIEW valley_daily
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('1 day', timestamp) AS day_bucket,
            AVG(aqi) AS avg_aqi,
            MAX(aqi) AS max_aqi,
            COUNT(DISTINCT station_id) AS station_count
        FROM aq_readings
        WHERE NOT is_anomaly
        GROUP BY day_bucket
        WITH NO DATA
        """
    )
    op.execute(
        """
        SELECT add_continuous_aggregate_policy(
            'aq_hourly',
            start_offset => INTERVAL '3 hours',
            end_offset => INTERVAL '1 hour',
            schedule_interval => INTERVAL '1 hour'
        )
        """
    )
    op.execute(
        """
        SELECT add_continuous_aggregate_policy(
            'aq_daily',
            start_offset => INTERVAL '3 days',
            end_offset => INTERVAL '1 day',
            schedule_interval => INTERVAL '6 hours'
        )
        """
    )
    op.execute(
        """
        SELECT add_continuous_aggregate_policy(
            'valley_daily',
            start_offset => INTERVAL '3 days',
            end_offset => INTERVAL '1 day',
            schedule_interval => INTERVAL '6 hours'
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS valley_daily CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS aq_daily CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS aq_hourly CASCADE")
