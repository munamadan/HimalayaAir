from __future__ import annotations

from typing import Any

from himalayaair.database import HimalayaAirDatabase
from himalayaair.run_utils import configure_task_logger, record_outcome, start_clock
from himalayaair.settings import AirflowTaskSettings


QUALITY_PIPELINE_STATUS = {
    "healthy": "success",
    "degraded": "partial",
    "down": "failed",
}


def run_data_quality_check(conf: dict[str, Any] | None = None) -> dict[str, object]:
    settings = AirflowTaskSettings.from_env()
    logger = configure_task_logger("air_quality_data_quality_check", settings)
    database = HimalayaAirDatabase(settings.database_url)
    return _run_data_quality_check(conf or {}, settings=settings, database=database, logger=logger)


def _run_data_quality_check(
    conf: dict[str, Any],
    *,
    settings: AirflowTaskSettings,
    database: HimalayaAirDatabase,
    logger: object,
) -> dict[str, object]:
    component = "airflow_data_quality_check"
    clock = start_clock()
    try:
        quality = database.evaluate_data_quality(
            fresh_hours=int(conf.get("fresh_hours") or settings.quality_fresh_hours),
            recent_hours=int(conf.get("recent_hours") or settings.quality_recent_hours),
            dead_sensor_days=int(conf.get("dead_sensor_days") or settings.quality_dead_sensor_days),
        )
        metadata = {
            "quality_state": quality.state,
            "coverage_mode": quality.coverage_mode,
            "confidence": quality.confidence,
            "fresh_station_count": quality.fresh_station_count,
            "recent_station_count": quality.recent_station_count,
            "modeled_available": quality.modeled_available,
            "replay_active": quality.replay_active,
            "invalid_value_count": quality.invalid_value_count,
            "anomaly_rate": quality.anomaly_rate,
            "dead_sensors_deactivated": quality.dead_sensors_deactivated,
            "message": quality.message,
        }
        pipeline_status = QUALITY_PIPELINE_STATUS[quality.state]
        record_outcome(
            database,
            component=component,
            status=pipeline_status,
            records_processed=quality.fresh_station_count + quality.recent_station_count,
            clock=clock,
            metadata=metadata,
            error_message=quality.message if quality.state == "down" else None,
        )
        logger.info("data_quality_check_complete", pipeline_status=pipeline_status, **metadata)
        return metadata | {"status": pipeline_status}
    except Exception as exc:
        record_outcome(
            database,
            component=component,
            status="failed",
            records_processed=0,
            clock=clock,
            metadata={"quality_state": "down"},
            error_message=str(exc),
        )
        logger.error("data_quality_check_failed", error=str(exc))
        raise
