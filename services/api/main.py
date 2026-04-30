from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import HTTPConnection

from services.api.cache import ApiCaches
from services.api.config import ApiSettings
from services.api.db import close_database_engine, get_db_session, get_session_factory
from services.api.models import (
    BasicHealthResponse,
    EventsResponse,
    ForecastResponse,
    HealthAdvisoryResponse,
    InterpolationResponse,
    PipelineHealthResponse,
    StationCurrentResponse,
    StationHistoryResponse,
    StationsResponse,
    ValleyCurrentResponse,
    ValleyHistoryResponse,
)
from services.api.repository import ApiNotFoundError, ApiRepository
from services.api.service import (
    get_basic_health_response,
    get_events_response,
    get_forecast_response,
    get_health_advisory_response,
    get_interpolation_response,
    get_pipeline_health_response,
    get_station_current_response,
    get_stations_response,
    get_valley_current_response,
    get_valley_history_response,
)
from services.api.websocket import ConnectionManager, KafkaLiveFeedConsumer
from shared.logging_config import configure_logging, get_logger


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    resolved_settings = settings or ApiSettings.from_env()
    configure_logging(service_name=resolved_settings.service_name, log_format=resolved_settings.log_format)
    logger = get_logger(__name__)
    caches = ApiCaches.build(
        station_ttl_seconds=resolved_settings.station_cache_ttl_seconds,
        idw_ttl_seconds=resolved_settings.idw_cache_ttl_seconds,
    )
    manager = ConnectionManager()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = resolved_settings
        app.state.caches = caches
        app.state.connection_manager = manager
        kafka_consumer: KafkaLiveFeedConsumer | None = None
        if resolved_settings.kafka_consumer_enabled:
            kafka_consumer = KafkaLiveFeedConsumer(settings=resolved_settings, manager=manager)
            kafka_consumer.start()
            logger.info("api_kafka_consumer_started", topic=resolved_settings.processed_aq_topic)
        else:
            manager.consumer_status = {"status": "disabled"}
        try:
            yield
        finally:
            if kafka_consumer is not None:
                await kafka_consumer.stop()
            await close_database_engine()

    app = FastAPI(title="HimalayaAir API", version="0.10.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.exception_handler(ApiNotFoundError)
    async def not_found_handler(_request: Request, exc: ApiNotFoundError):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.get("/health", response_model=BasicHealthResponse)
    async def health(settings_dep: ApiSettings = Depends(get_settings)) -> BasicHealthResponse:
        return get_basic_health_response(settings_dep)

    @app.get("/api/stations", response_model=StationsResponse)
    async def stations(
        repo: ApiRepository = Depends(get_repository),
        caches_dep: ApiCaches = Depends(get_caches),
    ) -> StationsResponse:
        return await get_stations_response(repo, caches_dep)

    @app.get("/api/stations/{station_id}/current", response_model=StationCurrentResponse)
    async def station_current(station_id: int, repo: ApiRepository = Depends(get_repository)) -> StationCurrentResponse:
        return await get_station_current_response(repo, station_id)

    @app.get("/api/stations/{station_id}/history", response_model=StationHistoryResponse)
    async def station_history(
        station_id: int,
        pollutant: str | None = Query(default=None, min_length=1, max_length=20),
        hours: int = Query(default=24, ge=1, le=24 * 366),
        limit: int = Query(default=5000, ge=1, le=20_000),
        repo: ApiRepository = Depends(get_repository),
    ) -> StationHistoryResponse:
        return await repo.fetch_station_history(station_id, pollutant=pollutant, hours=hours, limit=limit)

    @app.get("/api/valley/current", response_model=ValleyCurrentResponse)
    async def valley_current(repo: ApiRepository = Depends(get_repository)) -> ValleyCurrentResponse:
        return await get_valley_current_response(repo)

    @app.get("/api/valley/history", response_model=ValleyHistoryResponse)
    async def valley_history(
        pollutant: str | None = Query(default=None, min_length=1, max_length=20),
        hours: int = Query(default=24, ge=1, le=24 * 366),
        granularity: Literal["hour", "day"] = Query(default="hour"),
        repo: ApiRepository = Depends(get_repository),
    ) -> ValleyHistoryResponse:
        return await get_valley_history_response(repo, pollutant=pollutant, hours=hours, granularity=granularity)

    @app.get("/api/interpolation/current", response_model=InterpolationResponse)
    async def interpolation_current(
        pollutant: str = Query(default="pm25", min_length=1, max_length=20),
        repo: ApiRepository = Depends(get_repository),
        settings_dep: ApiSettings = Depends(get_settings),
        caches_dep: ApiCaches = Depends(get_caches),
    ) -> InterpolationResponse:
        return await get_interpolation_response(repo, settings_dep, caches_dep, pollutant=pollutant)

    @app.get("/api/health-advisory", response_model=HealthAdvisoryResponse)
    async def health_advisory(
        lat: float | None = Query(default=None, ge=-90, le=90),
        lon: float | None = Query(default=None, ge=-180, le=180),
        repo: ApiRepository = Depends(get_repository),
    ) -> HealthAdvisoryResponse:
        if (lat is None) != (lon is None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="lat and lon must be supplied together")
        return await get_health_advisory_response(repo, lat=lat, lon=lon)

    @app.get("/api/events", response_model=EventsResponse)
    async def events(
        days: int = Query(default=7, ge=1, le=366),
        limit: int = Query(default=100, ge=1, le=1000),
        lat: float | None = Query(default=None, ge=-90, le=90),
        lon: float | None = Query(default=None, ge=-180, le=180),
        repo: ApiRepository = Depends(get_repository),
    ) -> EventsResponse:
        if (lat is None) != (lon is None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="lat and lon must be supplied together")
        return await get_events_response(repo, days=days, limit=limit, lat=lat, lon=lon)

    @app.get("/api/forecasts/{station_id}", response_model=ForecastResponse)
    async def forecast(
        station_id: int,
        pollutant: str = Query(default="pm25", min_length=1, max_length=20),
        repo: ApiRepository = Depends(get_repository),
    ) -> ForecastResponse:
        return await get_forecast_response(repo, station_id=station_id, pollutant=pollutant)

    @app.get("/api/pipeline/health", response_model=PipelineHealthResponse)
    async def pipeline_health(
        repo: ApiRepository = Depends(get_repository),
        settings_dep: ApiSettings = Depends(get_settings),
    ) -> PipelineHealthResponse:
        return await get_pipeline_health_response(repo, settings_dep)

    @app.websocket("/ws/live-feed")
    async def live_feed(
        websocket: WebSocket,
        caches_dep: ApiCaches = Depends(get_caches),
        manager_dep: ConnectionManager = Depends(get_connection_manager),
        settings_dep: ApiSettings = Depends(get_settings),
    ) -> None:
        await manager_dep.connect(websocket)
        try:
            try:
                session_factory = get_session_factory(settings_dep)
                async with session_factory() as session:
                    repo = ApiRepository(session, settings_dep)
                    snapshot = await get_stations_response(repo, caches_dep)
                    await manager_dep.send_event(websocket, event="station_snapshot", data=snapshot.model_dump(mode="json"))
            except Exception as exc:
                logger.warning("websocket_station_snapshot_failed", error=str(exc))
                await manager_dep.send_event(websocket, event="error", data={"message": str(exc)})
            await manager_dep.websocket_loop(websocket, heartbeat_seconds=settings_dep.websocket_heartbeat_seconds)
        except Exception as exc:
            logger.warning("websocket_live_feed_failed", error=str(exc))
            await manager_dep.send_event(websocket, event="error", data={"message": str(exc)})
        finally:
            await manager_dep.disconnect(websocket)

    return app


async def get_settings(connection: HTTPConnection) -> ApiSettings:
    return connection.app.state.settings


async def get_caches(connection: HTTPConnection) -> ApiCaches:
    return connection.app.state.caches


async def get_connection_manager(connection: HTTPConnection) -> ConnectionManager:
    return connection.app.state.connection_manager


async def get_repository(
    connection: HTTPConnection,
    session: AsyncSession = Depends(get_db_session),
) -> ApiRepository:
    return ApiRepository(session, connection.app.state.settings)


app = create_app()
