from __future__ import annotations

from typing import Any

from himalayaair.database import HimalayaAirDatabase
from himalayaair.run_utils import configure_task_logger, record_outcome, start_clock
from himalayaair.settings import AirflowTaskSettings


def run_forecast_recompute_hook(conf: dict[str, Any] | None = None) -> dict[str, object]:
    settings = AirflowTaskSettings.from_env()
    logger = configure_task_logger("forecast_recompute_hook", settings)
    database = HimalayaAirDatabase(settings.database_url)
    component = "airflow_forecast_recompute_hook"
    clock = start_clock()
    metadata = {
        "forecast_runner_configured": False,
        "phase": "PHASE-08",
        "deferred_to_phase": "PHASE-10",
        "dag_conf_keys": sorted((conf or {}).keys()),
    }
    record_outcome(
        database,
        component=component,
        status="success",
        records_processed=0,
        clock=clock,
        metadata=metadata,
    )
    logger.info("forecast_recompute_hook_complete", **metadata)
    return metadata | {"status": "success"}
