from __future__ import annotations

import asyncio
from typing import Any

import httpx

from services.api.config import ApiSettings


async def check_kafka_connectivity(settings: ApiSettings) -> dict[str, Any]:
    if not settings.kafka_health_enabled:
        return {"status": "disabled", "detail": "Kafka health checks are disabled"}
    try:
        from confluent_kafka.admin import AdminClient
    except ModuleNotFoundError as exc:
        return {"status": "down", "detail": f"Kafka client unavailable: {exc.name}"}

    def _list_topics() -> dict[str, Any]:
        admin = AdminClient({"bootstrap.servers": settings.kafka_bootstrap_servers})
        metadata = admin.list_topics(timeout=2.0)
        topics = sorted(metadata.topics.keys())
        topic_present = settings.processed_aq_topic in topics
        return {
            "status": "ok" if topic_present else "degraded",
            "bootstrap_servers": settings.kafka_bootstrap_servers,
            "processed_topic": settings.processed_aq_topic,
            "processed_topic_present": topic_present,
            "consumer_lag": None,
        }

    try:
        return await asyncio.to_thread(_list_topics)
    except Exception as exc:
        return {
            "status": "down",
            "bootstrap_servers": settings.kafka_bootstrap_servers,
            "processed_topic": settings.processed_aq_topic,
            "consumer_lag": None,
            "detail": str(exc),
        }


async def check_external_services(settings: ApiSettings) -> dict[str, Any]:
    if not settings.external_health_enabled:
        return {"status": "disabled", "services": {}}
    if settings.external_health_mode == "worker":
        return await _check_worker_health(settings)
    if settings.external_health_mode == "legacy":
        return await _check_legacy_external_services(settings)
    return {
        "status": "degraded",
        "services": {},
        "detail": f"Unsupported API_EXTERNAL_HEALTH_MODE: {settings.external_health_mode}",
    }


async def _check_legacy_external_services(settings: ApiSettings) -> dict[str, Any]:
    targets = {
        "openaq_poller": settings.openaq_health_url,
        "weather_poller": settings.weather_health_url,
        "openmeteo_aq_poller": settings.modeled_aq_health_url,
    }
    results: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=settings.external_health_timeout_seconds) as client:
        for name, url in targets.items():
            results[name] = await _check_http_health(client, url)
    status = "ok"
    if any(value["status"] == "down" for value in results.values()):
        status = "degraded"
    return {"status": status, "services": results}


async def _check_worker_health(settings: ApiSettings) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=settings.external_health_timeout_seconds) as client:
        worker = await _check_http_health(client, settings.worker_health_url)
    if worker.get("status") == "down":
        return {
            "status": "degraded",
            "services": {
                "openaq_poller": {"status": "down", "detail": "worker health unavailable"},
                "weather_poller": {"status": "down", "detail": "worker health unavailable"},
                "openmeteo_aq_poller": {"status": "down", "detail": "worker health unavailable"},
            },
            "worker": worker,
        }

    payload = worker.get("payload")
    components: dict[str, Any] = {}
    if isinstance(payload, dict):
        details = payload.get("details")
        if isinstance(details, dict):
            raw_components = details.get("components")
            if isinstance(raw_components, dict):
                components = raw_components
    services = {
        "openaq_poller": _from_worker_component(components.get("openaq")),
        "weather_poller": _from_worker_component(components.get("weather")),
        "openmeteo_aq_poller": _from_worker_component(components.get("weather")),
    }
    status = "ok"
    if any(service.get("status") == "down" for service in services.values()):
        status = "degraded"
    return {"status": status, "services": services, "worker": worker}


def _from_worker_component(details: Any) -> dict[str, Any]:
    if not isinstance(details, dict):
        return {"status": "down", "detail": "component missing from worker health"}
    last_status = str(details.get("last_status", "unknown"))
    backoff_until = details.get("in_backoff_until")
    status = "ok"
    if last_status in {"failed", "error"}:
        status = "down"
    elif isinstance(backoff_until, str) and backoff_until:
        status = "degraded"
    elif details.get("last_success_at") is None:
        status = "degraded"
    return {"status": status, "source": "worker", "component": details}


async def _check_http_health(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
    try:
        response = await client.get(url)
        if response.status_code >= 500:
            return {"status": "down", "url": url, "status_code": response.status_code}
        payload: Any
        try:
            payload = response.json()
        except ValueError:
            payload = None
        return {"status": "ok" if response.status_code < 400 else "degraded", "url": url, "status_code": response.status_code, "payload": payload}
    except httpx.HTTPError as exc:
        return {"status": "down", "url": url, "detail": str(exc)}
