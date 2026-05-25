from __future__ import annotations

import asyncio

from services.api.config import ApiSettings
from services.api.health_checks import check_external_services


class _Response:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class _Client:
    def __init__(self, response: _Response):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url: str):
        return self._response


def _settings() -> ApiSettings:
    return ApiSettings(
        service_name="test",
        log_format="json",
        database_url="postgresql+asyncpg://user:pass@localhost/db",
        allowed_origins=("http://localhost:3000",),
        fresh_hours=2,
        recent_hours=24,
        modeled_hours=24,
        station_cache_ttl_seconds=1.0,
        idw_cache_ttl_seconds=1.0,
        idw_rows=5,
        idw_cols=5,
        idw_power=2.0,
        websocket_heartbeat_seconds=1.0,
        kafka_consumer_enabled=False,
        kafka_health_enabled=False,
        external_health_enabled=True,
        kafka_bootstrap_servers="localhost:29092",
        kafka_group_id="test",
        processed_aq_topic="processed-aq-readings",
        kafka_retry_seconds=0.1,
        openaq_health_url="http://openaq-poller:9090/health",
        weather_health_url="http://weather-poller:9091/health",
        modeled_aq_health_url="http://openmeteo-aq-poller:9092/health",
        worker_health_url="http://worker:9093/health",
        external_health_mode="worker",
        external_health_timeout_seconds=0.2,
    )


def test_worker_external_health_mapping(monkeypatch):
    import httpx

    payload = {
        "status": "healthy",
        "service": "himalayaair-worker",
        "details": {
            "components": {
                "openaq": {"last_status": "success", "last_success_at": "2026-05-25T00:00:00+00:00", "in_backoff_until": None},
                "weather": {"last_status": "success", "last_success_at": "2026-05-25T00:00:00+00:00", "in_backoff_until": None},
            }
        },
    }

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: _Client(_Response(200, payload)))
    result = asyncio.run(check_external_services(_settings()))

    assert result["status"] == "ok"
    assert result["services"]["openaq_poller"]["status"] == "ok"
    assert result["services"]["weather_poller"]["status"] == "ok"
    assert result["services"]["openmeteo_aq_poller"]["status"] == "ok"

