from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from himalayaair.weather_backfill import run_weather_historical_backfill

try:
    from airflow.decorators import dag, task
    from airflow.operators.python import get_current_context
except ImportError:
    dag = None
    task = None
    get_current_context = None


def _dag_conf() -> dict[str, Any]:
    if get_current_context is None:
        return {}
    context = get_current_context()
    dag_run = context.get("dag_run")
    conf = getattr(dag_run, "conf", None) or {}
    return dict(conf)


if dag is not None and task is not None:

    @dag(
        dag_id="weather_historical_backfill",
        schedule=None,
        start_date=datetime(2026, 1, 1, tzinfo=UTC),
        catchup=False,
        tags=["himalayaair", "backfill", "weather"],
    )
    def build_weather_historical_backfill() -> None:
        @task(task_id="openmeteo_archive_weather_backfill")
        def openmeteo_archive_weather_backfill() -> dict[str, object]:
            return run_weather_historical_backfill(_dag_conf())

        openmeteo_archive_weather_backfill()

    weather_historical_backfill = build_weather_historical_backfill()

