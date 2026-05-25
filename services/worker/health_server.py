from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

from shared.health import HealthPayload
from shared.time_utils import format_utc, utc_now


class WorkerHealthState:
    def __init__(self, *, service_name: str, enabled_components: list[str]) -> None:
        self.service_name = service_name
        self.enabled_components = tuple(enabled_components)
        self._lock = threading.Lock()
        self._components: dict[str, dict[str, Any]] = {
            name: {
                "last_started_at": None,
                "last_finished_at": None,
                "last_success_at": None,
                "last_status": "idle",
                "last_error": None,
                "consecutive_failures": 0,
                "in_backoff_until": None,
                "metrics": {},
            }
            for name in self.enabled_components
        }
        self._backoff_for_failures: Callable[[int], int] = lambda failures: 0 if failures < 1 else 30

    def set_backoff_calculator(self, fn: Callable[[int], int]) -> None:
        self._backoff_for_failures = fn

    def mark_started(self, component: str, started_at: datetime) -> None:
        with self._lock:
            state = self._components[component]
            state["last_started_at"] = started_at
            state["last_status"] = "running"
            state["last_error"] = None

    def mark_succeeded(self, component: str, finished_at: datetime, metrics: dict[str, Any], *, status: str = "success") -> None:
        with self._lock:
            state = self._components[component]
            state["last_finished_at"] = finished_at
            state["last_success_at"] = finished_at
            state["last_status"] = status
            state["last_error"] = None
            state["consecutive_failures"] = 0
            state["in_backoff_until"] = None
            state["metrics"] = dict(metrics)

    def mark_failed(self, component: str, finished_at: datetime, error: str, metrics: dict[str, Any]) -> int:
        with self._lock:
            state = self._components[component]
            state["last_finished_at"] = finished_at
            state["last_status"] = "failed"
            state["last_error"] = error
            state["consecutive_failures"] = int(state["consecutive_failures"]) + 1
            delay_seconds = max(self._backoff_for_failures(int(state["consecutive_failures"])), 0)
            state["in_backoff_until"] = finished_at + timedelta(seconds=delay_seconds) if delay_seconds > 0 else None
            state["metrics"] = dict(metrics)
            return delay_seconds

    def payload(self) -> dict[str, Any]:
        now = utc_now()
        with self._lock:
            components = {name: self._component_payload(data) for name, data in self._components.items()}
        aggregate_status = _aggregate_status(components, now)
        details = {
            "aggregate_status": aggregate_status,
            "components": components,
            "enabled_components": list(self.enabled_components),
        }
        payload = HealthPayload(service=self.service_name, status=_health_payload_status(aggregate_status), details=details)
        return payload.model_dump(mode="json")

    def _component_payload(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "last_started_at": _format_optional_datetime(_as_datetime(state["last_started_at"])),
            "last_finished_at": _format_optional_datetime(_as_datetime(state["last_finished_at"])),
            "last_success_at": _format_optional_datetime(_as_datetime(state["last_success_at"])),
            "last_status": str(state["last_status"]),
            "last_error": state["last_error"],
            "consecutive_failures": int(state["consecutive_failures"]),
            "in_backoff_until": _format_optional_datetime(_as_datetime(state["in_backoff_until"])),
            "metrics": dict(state["metrics"]),
        }


def _aggregate_status(components: dict[str, dict[str, Any]], now: datetime) -> str:
    healthy_count = 0
    failing_count = 0
    for details in components.values():
        last_success_at = details.get("last_success_at")
        in_backoff_until = details.get("in_backoff_until")
        if isinstance(last_success_at, str) and last_success_at:
            healthy_count += 1
        backoff_active = False
        if isinstance(in_backoff_until, str) and in_backoff_until:
            parsed = _parse_iso_datetime(in_backoff_until)
            backoff_active = parsed is not None and parsed > now
        if details.get("last_status") in {"failed", "error"} or backoff_active:
            failing_count += 1
    if healthy_count == 0:
        return "down"
    if failing_count > 0:
        return "degraded"
    return "healthy"


def _parse_iso_datetime(value: str) -> datetime | None:
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _as_datetime(value: object) -> datetime | None:
    return value if isinstance(value, datetime) else None


def _format_optional_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return format_utc(value)


def _health_payload_status(aggregate_status: str) -> str:
    if aggregate_status == "healthy":
        return "ok"
    if aggregate_status == "down":
        return "failed"
    return "degraded"


def start_health_server(host: str, port: int, state: WorkerHealthState, logger: object | None = None) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/health":
                self.send_response(404)
                self.end_headers()
                return
            body = json.dumps(state.payload(), sort_keys=True).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _log(logger, "info", "worker_health_server_started", host=host, port=port)
    return server


def _log(logger: object | None, level: str, event: str, **fields: object) -> None:
    if logger is None:
        return
    log_method = getattr(logger, level, None)
    if callable(log_method):
        log_method(event, **fields)
