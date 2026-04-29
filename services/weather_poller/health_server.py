from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from shared.health import HealthPayload
from shared.time_utils import format_utc

from services.weather_poller.models import WeatherPollRunResult


class HealthState:
    def __init__(self, service_name: str) -> None:
        self.service_name = service_name
        self._lock = threading.Lock()
        self._status = "degraded"
        self._details: dict[str, Any] = {"message": "poller has not completed a run"}

    def update(self, result: WeatherPollRunResult) -> None:
        status = "ok" if result.status == "success" else "degraded"
        if result.status == "failed":
            status = "failed"
        details: dict[str, Any] = {
            "last_run_status": result.status,
            "records_processed": result.records_processed,
            "locations_attempted": result.locations_attempted,
            "locations_succeeded": result.locations_succeeded,
            "locations_failed": result.locations_failed,
            "weather_records": result.weather_records,
            "modeled_aq_records": result.modeled_aq_records,
            "modeled_available": result.modeled_aq_records > 0,
            "finished_at": format_utc(result.finished_at),
            "dry_run": result.dry_run,
        }
        if result.error_message:
            details["error_message"] = result.error_message
        details.update(result.metadata)
        with self._lock:
            self._status = status
            self._details = details

    def payload(self) -> dict[str, Any]:
        with self._lock:
            payload = HealthPayload(service=self.service_name, status=self._status, details=dict(self._details))
        return payload.model_dump(mode="json")


def start_health_server(host: str, port: int, state: HealthState, logger: object | None = None) -> ThreadingHTTPServer:
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
    _log(logger, "info", "weather_health_server_started", host=host, port=port)
    return server


def _log(logger: object | None, level: str, event: str, **fields: object) -> None:
    if logger is None:
        return
    log_method = getattr(logger, level, None)
    if callable(log_method):
        log_method(event, **fields)
