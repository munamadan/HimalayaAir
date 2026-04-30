from __future__ import annotations

import asyncio

from services.api.websocket import ConnectionManager
from shared.enums import Confidence, CoverageMode, ObservationType, SourceName
from shared.kafka.messages import ProcessedAQBatchSummaryMessage, ProcessedAQStationSummary
from shared.time_utils import utc_now


def test_health_advisory_contract(api_client):
    response = api_client.get("/api/health-advisory?lat=27.71&lon=85.32")

    assert response.status_code == 200
    payload = response.json()
    assert payload["coverage_mode"] == "RECENT_OBSERVED"
    assert payload["aqi"] == 91
    assert payload["nearest_station"]["distance_km"] == 1.234
    assert payload["nearest_station"]["name"] == "Ratnapark"


def test_events_contract(api_client):
    response = api_client.get("/api/events?days=3&lat=27.71&lon=85.32")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["events"][0]["source"] == "VIIRS_SNPP_NRT"
    assert payload["events"][0]["distance_km"] == 8.5


def test_pipeline_health_contract(api_client):
    response = api_client.get("/api/pipeline/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["coverage"]["coverage_mode"] == "RECENT_OBSERVED"
    assert payload["checks"]["database"]["status"] == "ok"
    assert payload["checks"]["kafka"]["status"] == "disabled"
    assert payload["pipeline_runs"][0]["component"] == "spark_aq_stream"


def test_websocket_endpoint_is_registered(api_client):
    websocket_paths = {route.path for route in api_client.app.routes if getattr(route, "path", None)}

    assert "/ws/live-feed" in websocket_paths


def test_connection_manager_skips_duplicate_batches():
    async def run_check() -> tuple[bool, bool]:
        manager = ConnectionManager()
        summary = ProcessedAQBatchSummaryMessage(
            batch_id=42,
            processed_at=utc_now(),
            records_received=1,
            records_written=1,
            records_skipped_duplicate=0,
            records_invalid=0,
            anomaly_count=0,
            coverage_mode=CoverageMode.RECENT_OBSERVED,
            confidence=Confidence.MEDIUM,
            stations=[
                ProcessedAQStationSummary(
                    station_id=1,
                    station_name="Ratnapark",
                    aqi=91,
                    dominant_pollutant="pm25",
                    district=None,
                    is_anomaly=False,
                    source=SourceName.OPENAQ_LIVE,
                    observation_type=ObservationType.OBSERVED,
                    latitude=27.707,
                    longitude=85.314,
                    timestamp=utc_now(),
                )
            ],
        )
        return await manager.broadcast_processed_batch(summary), await manager.broadcast_processed_batch(summary)

    first, second = asyncio.run(run_check())

    assert first is True
    assert second is False
