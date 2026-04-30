from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from himalayaair.data_quality import run_data_quality_check

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
        dag_id="air_quality_data_quality_check",
        schedule="0 */2 * * *",
        start_date=datetime(2026, 1, 1, tzinfo=UTC),
        catchup=False,
        tags=["himalayaair", "quality"],
    )
    def build_air_quality_data_quality_check() -> None:
        @task(task_id="evaluate_quality_state")
        def evaluate_quality_state() -> dict[str, object]:
            return run_data_quality_check(_dag_conf())

        evaluate_quality_state()

    air_quality_data_quality_check = build_air_quality_data_quality_check()

