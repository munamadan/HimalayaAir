from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from himalayaair.forecast_hook import run_forecast_recompute

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
        dag_id="forecast_recompute",
        schedule="@hourly",
        start_date=datetime(2026, 1, 1, tzinfo=UTC),
        catchup=False,
        tags=["himalayaair", "forecast"],
    )
    def build_forecast_recompute() -> None:
        @task(task_id="run_forecast_recompute")
        def run_forecast_recompute_task() -> dict[str, object]:
            return run_forecast_recompute(_dag_conf())

        run_forecast_recompute_task()

    forecast_recompute = build_forecast_recompute()
