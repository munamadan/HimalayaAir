from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from himalayaair.firms import run_firms_daily_load

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
        dag_id="firms_daily_load",
        schedule="30 1 * * *",
        start_date=datetime(2026, 1, 1, tzinfo=UTC),
        catchup=False,
        tags=["himalayaair", "firms", "fire-events"],
    )
    def build_firms_daily_load() -> None:
        @task(task_id="load_firms_area_csv")
        def load_firms_area_csv() -> dict[str, object]:
            return run_firms_daily_load(_dag_conf())

        load_firms_area_csv()

    firms_daily_load = build_firms_daily_load()

