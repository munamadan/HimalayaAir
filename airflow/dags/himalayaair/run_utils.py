from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from time import monotonic
from typing import Any

from shared.logging_config import configure_logging, get_logger
from shared.time_utils import ensure_utc

from himalayaair.database import HimalayaAirDatabase
from himalayaair.models import PipelineOutcome
from himalayaair.settings import AirflowTaskSettings


@dataclass(frozen=True)
class RunClock:
    started_at: datetime
    started_monotonic: float


def configure_task_logger(component: str, settings: AirflowTaskSettings) -> object:
    configure_logging(service_name=component, log_format=settings.log_format)
    return get_logger(component)


def start_clock() -> RunClock:
    return RunClock(started_at=datetime.now(UTC), started_monotonic=monotonic())


def finish_clock(clock: RunClock) -> tuple[datetime, float]:
    finished_at = datetime.now(UTC)
    return finished_at, monotonic() - clock.started_monotonic


def record_outcome(
    database: HimalayaAirDatabase,
    *,
    component: str,
    status: str,
    records_processed: int,
    clock: RunClock,
    metadata: dict[str, object],
    error_message: str | None = None,
) -> PipelineOutcome:
    finished_at, duration_seconds = finish_clock(clock)
    outcome = PipelineOutcome(
        component=component,
        status=status,
        records_processed=records_processed,
        started_at=clock.started_at,
        finished_at=finished_at,
        duration_seconds=duration_seconds,
        metadata=metadata,
        error_message=error_message,
    )
    database.record_pipeline_run(outcome)
    return outcome


def parse_date(value: object, *, field_name: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return ensure_utc(value).date()
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be an ISO date")
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO date") from exc


def date_window_from_conf(
    conf: dict[str, Any],
    *,
    default_days: int,
    max_days: int,
    today: date | None = None,
) -> tuple[date, date]:
    anchor = today or datetime.now(UTC).date()
    if "start_date" in conf or "end_date" in conf:
        start_date = parse_date(conf.get("start_date"), field_name="start_date")
        end_date = parse_date(conf.get("end_date"), field_name="end_date")
    else:
        end_date = anchor - timedelta(days=1)
        start_date = end_date - timedelta(days=max(default_days - 1, 0))
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    if (end_date - start_date).days + 1 > max_days:
        raise ValueError(f"date window cannot exceed {max_days} day(s)")
    return start_date, end_date


def iter_dates(start_date: date, end_date: date) -> list[date]:
    return [start_date + timedelta(days=offset) for offset in range((end_date - start_date).days + 1)]


def int_from_conf(conf: dict[str, Any], key: str, default: int) -> int:
    value = conf.get(key, default)
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be an integer") from exc
    if parsed < 0:
        raise ValueError(f"{key} must be non-negative")
    return parsed


def str_from_conf(conf: dict[str, Any], key: str, default: str) -> str:
    value = conf.get(key, default)
    if value is None:
        return default
    text = str(value).strip()
    return text or default
