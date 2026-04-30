"""add fallback reason to forecast rows

Revision ID: 0007_forecast_fallback_reason
Revises: 0006_weather_quality_flags
Create Date: 2026-04-30 00:00:06
"""
from __future__ import annotations

from alembic import op

revision = "0007_forecast_fallback_reason"
down_revision = "0006_weather_quality_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE forecasts ADD COLUMN fallback_reason TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS fallback_reason")

