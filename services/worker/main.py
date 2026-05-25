from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable

from services.forecasting.run_once import run_forecast_once
from services.openaq_poller.config import OpenAQPollerSettings
from services.openaq_poller.main import OpenAQPoller
from services.weather_poller.config import WeatherPollerSettings
from services.weather_poller.main import WeatherPoller
from services.worker.health_server import WorkerHealthState, start_health_server
from shared.logging_config import configure_logging, get_logger
from shared.time_utils import utc_now


def _int_env(name: str, default_seconds: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default_seconds
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    return max(value, minimum)


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


def _next_tick(previous_tick: datetime, now: datetime, interval_seconds: int) -> datetime:
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")
    if now < previous_tick:
        return previous_tick
    elapsed = (now - previous_tick).total_seconds()
    increments = int(elapsed // interval_seconds) + 1
    return previous_tick + timedelta(seconds=increments * interval_seconds)


def _backoff_seconds(failures: int, initial: int, maximum: int) -> int:
    if failures <= 0:
        return 0
    delay = initial * (2 ** (failures - 1))
    return min(delay, maximum)


def _to_datetime(value: object) -> datetime | None:
    return value if isinstance(value, datetime) else None


@dataclass(frozen=True)
class WorkerComponent:
    name: str
    interval_seconds: int
    enabled: bool
    run: Callable[[], object]


class WorkerRunner:
    def __init__(
        self,
        *,
        components: list[WorkerComponent],
        health: WorkerHealthState,
        logger: object,
        backoff_initial_seconds: int,
        backoff_max_seconds: int,
    ) -> None:
        self.components = components
        self.health = health
        self.logger = logger
        self.backoff_initial_seconds = backoff_initial_seconds
        self.backoff_max_seconds = backoff_max_seconds

    async def run_forever(self) -> None:
        tasks = [asyncio.create_task(self._run_component_loop(component)) for component in self.components if component.enabled]
        if not tasks:
            return
        await asyncio.gather(*tasks)

    async def _run_component_loop(self, component: WorkerComponent) -> None:
        next_tick = utc_now()
        while True:
            now = utc_now()
            if now < next_tick:
                await asyncio.sleep((next_tick - now).total_seconds())
            started_at = utc_now()
            self.health.mark_started(component.name, started_at)
            result: object
            try:
                result = await asyncio.to_thread(component.run)
            except Exception as exc:
                backoff_delay = self.health.mark_failed(component.name, utc_now(), str(exc), self._fallback_metrics())
                self._log("error", "worker_component_failed", component=component.name, error=str(exc), backoff_seconds=backoff_delay)
                next_tick = max(_next_tick(next_tick, utc_now(), component.interval_seconds), utc_now() + timedelta(seconds=backoff_delay))
                continue

            status = str(getattr(result, "status", "success"))
            finished_at = _to_datetime(getattr(result, "finished_at", None)) or utc_now()
            metrics = self._extract_metrics(result)
            if status in {"failed", "error"}:
                error_message = str(getattr(result, "error_message", "component run failed"))
                backoff_delay = self.health.mark_failed(component.name, finished_at, error_message, metrics)
                self._log("warning", "worker_component_run_failed", component=component.name, error=error_message, backoff_seconds=backoff_delay)
                next_tick = max(_next_tick(next_tick, finished_at, component.interval_seconds), finished_at + timedelta(seconds=backoff_delay))
                continue

            self.health.mark_succeeded(component.name, finished_at, metrics, status=status)
            next_tick = _next_tick(next_tick, finished_at, component.interval_seconds)

    def _extract_metrics(self, result: object) -> dict[str, Any]:
        metrics = self._fallback_metrics()
        for key in (
            "records_processed",
            "sensors_attempted",
            "sensors_succeeded",
            "sensors_failed",
            "locations_attempted",
            "locations_succeeded",
            "locations_failed",
            "weather_records",
            "modeled_aq_records",
            "duration_seconds",
        ):
            value = getattr(result, key, None)
            if isinstance(value, (int, float)):
                metrics[key] = value
        return metrics

    def _fallback_metrics(self) -> dict[str, Any]:
        return {"records_processed": 0}

    def _log(self, level: str, event: str, **fields: object) -> None:
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(event, **fields)


def main() -> int:
    configure_logging(service_name="himalayaair-worker", log_format="json")
    logger = get_logger(__name__)

    openaq = OpenAQPoller(OpenAQPollerSettings.from_env(), logger=logger)
    weather = WeatherPoller(WeatherPollerSettings.from_env(), logger=logger)
    components = [
        WorkerComponent(
            name="openaq",
            interval_seconds=_int_env("WORKER_OPENAQ_INTERVAL_SECONDS", 300),
            enabled=_bool_env("WORKER_ENABLE_OPENAQ", True),
            run=lambda: openaq.run_once(dry_run=False),
        ),
        WorkerComponent(
            name="weather",
            interval_seconds=_int_env("WORKER_WEATHER_INTERVAL_SECONDS", 900),
            enabled=_bool_env("WORKER_ENABLE_WEATHER", True),
            run=lambda: weather.run_once(dry_run=False),
        ),
        WorkerComponent(
            name="forecast",
            interval_seconds=_int_env("WORKER_FORECAST_INTERVAL_SECONDS", 3600),
            enabled=_bool_env("WORKER_ENABLE_FORECAST", True),
            run=lambda: run_forecast_once(dry_run=False),
        ),
    ]
    backoff_initial_seconds = _int_env("WORKER_BACKOFF_INITIAL_SECONDS", 30)
    backoff_max_seconds = _int_env("WORKER_BACKOFF_MAX_SECONDS", 900)
    if backoff_max_seconds < backoff_initial_seconds:
        raise ValueError("WORKER_BACKOFF_MAX_SECONDS must be greater than or equal to WORKER_BACKOFF_INITIAL_SECONDS")

    service_name = os.getenv("SERVICE_NAME", "himalayaair-worker")
    enabled_components = [component.name for component in components if component.enabled]
    health = WorkerHealthState(service_name=service_name, enabled_components=enabled_components)
    health_server = start_health_server(
        host=os.getenv("WORKER_HEALTH_HOST", "0.0.0.0"),
        port=_int_env("WORKER_HEALTH_PORT", 9093, minimum=1),
        state=health,
        logger=logger,
    )

    runner = WorkerRunner(
        components=components,
        health=health,
        logger=logger,
        backoff_initial_seconds=backoff_initial_seconds,
        backoff_max_seconds=backoff_max_seconds,
    )
    health.set_backoff_calculator(lambda failures: _backoff_seconds(failures, backoff_initial_seconds, backoff_max_seconds))
    try:
        asyncio.run(runner.run_forever())
    except KeyboardInterrupt:
        logger.info("worker_stopping")
        return 0
    finally:
        health_server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
