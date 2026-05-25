from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services.worker.health_server import WorkerHealthState
from services.worker.main import _backoff_seconds, _next_tick


def test_fixed_rate_next_tick_skips_catchup_runs():
    base = datetime(2026, 5, 25, 0, 0, tzinfo=timezone.utc)
    delayed_now = base + timedelta(seconds=95)

    next_tick = _next_tick(base, delayed_now, 30)

    assert next_tick == base + timedelta(seconds=120)


def test_backoff_resets_after_success():
    health = WorkerHealthState(service_name="worker", enabled_components=["openaq"])
    health.set_backoff_calculator(lambda failures: _backoff_seconds(failures, 30, 900))
    started = datetime(2026, 5, 25, 0, 0, tzinfo=timezone.utc)

    health.mark_started("openaq", started)
    delay1 = health.mark_failed("openaq", started + timedelta(seconds=3), "upstream timeout", {"records_processed": 0})
    health.mark_succeeded("openaq", started + timedelta(seconds=40), {"records_processed": 5})
    delay2 = health.mark_failed("openaq", started + timedelta(seconds=70), "upstream timeout", {"records_processed": 0})

    payload = health.payload()
    component = payload["details"]["components"]["openaq"]
    assert delay1 == 30
    assert delay2 == 30
    assert component["consecutive_failures"] == 1


def test_disabled_component_not_in_health():
    health = WorkerHealthState(service_name="worker", enabled_components=["weather"])
    payload = health.payload()
    components = payload["details"]["components"]

    assert "weather" in components
    assert "forecast" not in components


def test_worker_health_status_transitions():
    health = WorkerHealthState(service_name="worker", enabled_components=["openaq", "weather"])
    start = datetime(2026, 5, 25, 0, 0, tzinfo=timezone.utc)

    assert health.payload()["details"]["aggregate_status"] == "down"
    health.mark_succeeded("openaq", start, {"records_processed": 1})
    assert health.payload()["details"]["aggregate_status"] == "healthy"
    health.mark_failed("weather", start + timedelta(seconds=10), "timeout", {"records_processed": 0})
    assert health.payload()["details"]["aggregate_status"] == "degraded"
