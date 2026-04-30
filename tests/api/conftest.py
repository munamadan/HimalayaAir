from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
import httpx

from services.api.config import ApiSettings
from services.api.domain import AQPoint
from services.api.main import create_app, get_repository
from services.api.models import (
    CoverageMetadata,
    FireEvent,
    HistoryPoint,
    NearestStation,
    PipelineRunHealth,
    PollutantCurrent,
    StationHistoryResponse,
    StationIdentity,
    StationSummary,
    ValleyHistoryPoint,
)
from shared.enums import Confidence, CoverageMode, ObservationType


NOW = datetime(2026, 4, 30, 8, 0, tzinfo=timezone.utc)


class FakeApiRepository:
    def __init__(self) -> None:
        self.coverage = CoverageMetadata(
            coverage_mode=CoverageMode.RECENT_OBSERVED,
            confidence=Confidence.MEDIUM,
            fresh_station_count=2,
            recent_station_count=4,
            modeled_available=True,
            replay_active=False,
            message="Using latest observed readings from the last 24 hours because fewer than 3 stations reported in the last 2 hours.",
        )
        self.station_rows = [
            StationSummary(
                id=1,
                name="Ratnapark",
                lat=27.707,
                lon=85.314,
                active=True,
                status="active",
                last_seen=NOW,
                current_aqi=91,
                dominant_pollutant="pm25",
                source="openaq_live",
                observation_type=ObservationType.OBSERVED,
                coverage_mode=CoverageMode.RECENT_OBSERVED,
                confidence=Confidence.MEDIUM,
                freshness_minutes=180,
                health_category="Moderate",
            ),
            StationSummary(
                id=2,
                name="Patan",
                lat=27.664,
                lon=85.324,
                active=True,
                status="active",
                last_seen=NOW,
                current_aqi=108,
                dominant_pollutant="pm25",
                source="openaq_live",
                observation_type=ObservationType.OBSERVED,
                coverage_mode=CoverageMode.RECENT_OBSERVED,
                confidence=Confidence.MEDIUM,
                freshness_minutes=210,
                health_category="Unhealthy for Sensitive Groups",
            ),
            StationSummary(
                id=3,
                name="Bhaktapur",
                lat=27.671,
                lon=85.43,
                active=True,
                status="active",
                last_seen=NOW,
                current_aqi=84,
                dominant_pollutant="pm25",
                source="openaq_live",
                observation_type=ObservationType.OBSERVED,
                coverage_mode=CoverageMode.RECENT_OBSERVED,
                confidence=Confidence.MEDIUM,
                freshness_minutes=230,
                health_category="Moderate",
            ),
            StationSummary(
                id=4,
                name="Kirtipur",
                lat=27.678,
                lon=85.277,
                active=True,
                status="active",
                last_seen=NOW,
                current_aqi=99,
                dominant_pollutant="pm25",
                source="openaq_live",
                observation_type=ObservationType.OBSERVED,
                coverage_mode=CoverageMode.RECENT_OBSERVED,
                confidence=Confidence.MEDIUM,
                freshness_minutes=240,
                health_category="Moderate",
            ),
        ]

    async def ping(self) -> bool:
        return True

    async def fetch_coverage_metadata(self) -> CoverageMetadata:
        return self.coverage

    async def fetch_station_summaries(self) -> list[StationSummary]:
        return self.station_rows

    async def fetch_station_identity(self, station_id: int) -> StationIdentity:
        station = next(row for row in self.station_rows if row.id == station_id)
        return StationIdentity(
            id=station.id,
            name=station.name,
            lat=station.lat,
            lon=station.lon,
            active=station.active,
            status=station.status,
            last_seen=station.last_seen,
        )

    async def fetch_station_current_readings(self, station_id: int) -> list[PollutantCurrent]:
        return [
            PollutantCurrent(
                pollutant="pm25",
                value=32.5,
                unit="ug/m3",
                aqi=91,
                timestamp=NOW,
                freshness_minutes=180,
                is_anomaly=False,
                anomaly_reason=None,
                quality_flag="processed",
                source="openaq_live",
                observation_type=ObservationType.OBSERVED,
                coverage_mode=CoverageMode.RECENT_OBSERVED,
                confidence=Confidence.MEDIUM,
                health_category="Moderate",
            ),
            PollutantCurrent(
                pollutant="pm10",
                value=74.0,
                unit="ug/m3",
                aqi=None,
                timestamp=datetime(2026, 4, 30, 7, 15, tzinfo=timezone.utc),
                freshness_minutes=225,
                is_anomaly=False,
                anomaly_reason=None,
                quality_flag="processed",
                source="openaq_live",
                observation_type=ObservationType.OBSERVED,
                coverage_mode=CoverageMode.RECENT_OBSERVED,
                confidence=Confidence.MEDIUM,
                health_category=None,
            ),
        ]

    async def fetch_station_history(self, station_id: int, *, pollutant: str | None, hours: int, limit: int) -> StationHistoryResponse:
        return StationHistoryResponse(
            station_id=station_id,
            pollutant=pollutant,
            hours=hours,
            readings=[
                HistoryPoint(
                    timestamp=datetime(2026, 4, 30, 6, 0, tzinfo=timezone.utc),
                    pollutant="pm25",
                    value=28.1,
                    unit="ug/m3",
                    aqi=84,
                    is_anomaly=False,
                    quality_flag="processed",
                    source="openaq_live",
                    observation_type=ObservationType.OBSERVED,
                    coverage_mode=CoverageMode.RECENT_OBSERVED,
                    confidence=Confidence.MEDIUM,
                )
            ],
        )

    async def fetch_valley_history(self, *, pollutant: str | None, hours: int, granularity: str) -> list[ValleyHistoryPoint]:
        return [
            ValleyHistoryPoint(
                bucket_start=datetime(2026, 4, 30, 6, 0, tzinfo=timezone.utc),
                pollutant=pollutant or "pm25",
                avg_aqi=95.5,
                max_aqi=108,
                station_count=4,
                reading_count=4,
            )
        ]

    async def fetch_interpolation_points(self, *, mode: CoverageMode, pollutant: str) -> list[AQPoint]:
        return [
            AQPoint(id=row.id, name=row.name, lat=row.lat, lon=row.lon, aqi=row.current_aqi, pollutant=pollutant, source="openaq_live", observation_type="observed", timestamp=NOW)
            for row in self.station_rows
        ]

    async def fetch_modeled_points(self, *, pollutant: str) -> list[AQPoint]:
        return [
            AQPoint(id=10, name="Kathmandu Center", lat=27.7172, lon=85.324, aqi=88, pollutant=pollutant, source="openmeteo_cams", observation_type="modeled", timestamp=NOW)
        ]

    async def fetch_nearest_station(self, *, lat: float, lon: float) -> NearestStation:
        return NearestStation(id=1, name="Ratnapark", lat=27.707, lon=85.314, distance_km=1.234, current_aqi=91)

    async def fetch_fire_events(self, *, days: int, limit: int, lat: float | None, lon: float | None) -> list[FireEvent]:
        return [
            FireEvent(
                id=1,
                lat=27.61,
                lon=85.21,
                acq_date=date(2026, 4, 29),
                acq_time=930,
                satellite="NPP",
                instrument="VIIRS",
                confidence="nominal",
                frp=7.5,
                brightness=322.4,
                source="VIIRS_SNPP_NRT",
                event_hash="fixture-fire-event",
                distance_km=8.5 if lat is not None and lon is not None else None,
            )
        ]

    async def fetch_pipeline_runs(self) -> list[PipelineRunHealth]:
        return [
            PipelineRunHealth(
                component="spark_aq_stream",
                run_at=NOW,
                status="success",
                records_processed=4,
                error_message=None,
                duration_seconds=1.5,
                metadata={"coverage_mode": "RECENT_OBSERVED"},
            )
        ]

    async def fetch_latest_aq_timestamp(self) -> datetime:
        return NOW

    async def fetch_latest_modeled_timestamp(self) -> datetime:
        return NOW


def api_test_settings() -> ApiSettings:
    return ApiSettings(
        service_name="himalayaair-api-test",
        log_format="json",
        database_url="postgresql+asyncpg://user:pass@localhost/db",
        allowed_origins=("http://localhost:3000",),
        fresh_hours=2,
        recent_hours=24,
        modeled_hours=24,
        station_cache_ttl_seconds=0.1,
        idw_cache_ttl_seconds=0.1,
        idw_rows=5,
        idw_cols=5,
        idw_power=2.0,
        websocket_heartbeat_seconds=0.5,
        kafka_consumer_enabled=False,
        kafka_health_enabled=False,
        external_health_enabled=False,
        kafka_bootstrap_servers="localhost:29092",
        kafka_group_id="test-api",
        processed_aq_topic="processed-aq-readings",
        kafka_retry_seconds=0.1,
        openaq_health_url="http://openaq-poller:9090/health",
        weather_health_url="http://weather-poller:9091/health",
        modeled_aq_health_url="http://openmeteo-aq-poller:9092/health",
        external_health_timeout_seconds=0.1,
    )


@pytest.fixture
def fake_repo() -> FakeApiRepository:
    return FakeApiRepository()


@pytest.fixture
def api_client(fake_repo: FakeApiRepository):
    app = create_app(settings=api_test_settings())

    async def override_repository() -> FakeApiRepository:
        return fake_repo

    app.dependency_overrides[get_repository] = override_repository
    return ASGIClient(app)


class ASGIClient:
    def __init__(self, app) -> None:
        self.app = app

    def get(self, path: str):
        return asyncio_run(self._get(path))

    async def _get(self, path: str):
        async with self.app.router.lifespan_context(self.app):
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.get(path)


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)
