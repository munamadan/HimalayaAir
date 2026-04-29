"""add quality flags for weather and modeled aq

Revision ID: 0006_weather_quality_flags
Revises: 0005_continuous_aggregates
Create Date: 2026-04-29 00:00:05
"""
from __future__ import annotations

from alembic import op

revision = "0006_weather_quality_flags"
down_revision = "0005_continuous_aggregates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE weather_readings ADD COLUMN quality_flag VARCHAR(50) NOT NULL DEFAULT 'complete'")
    op.execute("ALTER TABLE modeled_aq_readings ADD COLUMN quality_flag VARCHAR(50) NOT NULL DEFAULT 'complete'")
    op.execute(
        """
        ALTER TABLE weather_readings
        ADD CONSTRAINT ck_weather_quality_flag
        CHECK (quality_flag IN ('complete', 'missing_value', 'partial_response'))
        """
    )
    op.execute(
        """
        ALTER TABLE modeled_aq_readings
        ADD CONSTRAINT ck_modeled_quality_flag
        CHECK (quality_flag IN ('complete', 'missing_value', 'partial_response'))
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE modeled_aq_readings DROP CONSTRAINT IF EXISTS ck_modeled_quality_flag")
    op.execute("ALTER TABLE weather_readings DROP CONSTRAINT IF EXISTS ck_weather_quality_flag")
    op.execute("ALTER TABLE modeled_aq_readings DROP COLUMN IF EXISTS quality_flag")
    op.execute("ALTER TABLE weather_readings DROP COLUMN IF EXISTS quality_flag")
