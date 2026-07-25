from __future__ import annotations

from datetime import datetime
from typing import Protocol

from services.api.cache import ApiCaches
from services.api.config import ApiSettings
from services.api.domain import AQPoint, current_aqi_from_readings, health_category, health_recommendation, interpolation_source_for_mode
from services.api.health_checks import check_external_services, check_kafka_connectivity
from services.api.models import (
    BasicHealthResponse,
    CoverageMetadata,
    EventsResponse,
    ForecastResponse,
    HealthAdvisoryResponse,
    InterpolationGrid,
    InterpolationResponse,
    InterpolationTimelineResponse,
    PipelineHealthResponse,
    StationCurrentResponse,
    StationHistoryResponse,
    StationsResponse,
    TimelineFrame,
    ValleyCurrentResponse,
    ValleyHistoryResponse,
    WindRoseResponse,
)
from services.api.spatial import KATHMANDU_BOUNDS, build_idw_grid
from shared.enums import Confidence, CoverageMode
from shared.time_utils import utc_now


class ApiRepositoryProtocol(Protocol):
    async def ping(self) -> bool: ...
    async def fetch_coverage_metadata(self) -> CoverageMetadata: ...
    async def fetch_station_summaries(self) -> list[object]: ...
    async def fetch_station_identity(self, station_id: int) -> object: ...
    async def fetch_station_current_readings(self, station_id: int) -> list[object]: ...
    async def fetch_station_history(self, station_id: int, *, pollutant: str | None, hours: int, limit: int) -> StationHistoryResponse: ...
    async def fetch_valley_history(self, *, pollutant: str | None, hours: int, granularity: str) -> list[object]: ...
    async def fetch_interpolation_points(self, *, mode: CoverageMode, pollutant: str) -> list[AQPoint]: ...
    async def fetch_hourly_interpolation_points(self, *, pollutant: str, hours: int) -> dict[datetime, list[AQPoint]]: ...
    async def fetch_modeled_points(self, *, pollutant: str) -> list[AQPoint]: ...
    async def fetch_nearest_station(self, *, lat: float, lon: float) -> object | None: ...
    async def fetch_fire_events(self, *, days: int, limit: int, lat: float | None, lon: float | None) -> list[object]: ...
    async def fetch_wind_rose(self, *, hours: int, bins: int) -> list[object]: ...
    async def fetch_forecast(self, station_id: int, *, pollutant: str) -> ForecastResponse: ...
    async def fetch_pipeline_runs(self) -> list[object]: ...
    async def fetch_latest_aq_timestamp(self) -> datetime | None: ...
    async def fetch_latest_modeled_timestamp(self) -> datetime | None: ...


async def get_stations_response(repo: ApiRepositoryProtocol, caches: ApiCaches) -> StationsResponse:
    cached = await caches.station_snapshots.get("stations")
    if isinstance(cached, StationsResponse):
        return cached

    coverage = await repo.fetch_coverage_metadata()
    stations = await repo.fetch_station_summaries()
    valley_aqi = _max_station_aqi(stations)
    if valley_aqi is None and _coverage_mode(coverage) == CoverageMode.MODELED_BASELINE:
        valley_aqi = _max_point_aqi(await repo.fetch_modeled_points(pollutant="pm25"))

    response = StationsResponse(
        timestamp=utc_now(),
        valley_composite_aqi=valley_aqi,
        stations=list(stations),
        **coverage.model_dump(),
    )
    await caches.station_snapshots.set("stations", response)
    return response


async def get_station_current_response(repo: ApiRepositoryProtocol, station_id: int) -> StationCurrentResponse:
    coverage = await repo.fetch_coverage_metadata()
    station = await repo.fetch_station_identity(station_id)
    readings = await repo.fetch_station_current_readings(station_id)
    current_aqi, dominant_pollutant = current_aqi_from_readings(readings)
    return StationCurrentResponse(
        station=station,
        current_aqi=current_aqi,
        dominant_pollutant=dominant_pollutant,
        readings=list(readings),
        **coverage.model_dump(),
    )


async def get_valley_current_response(repo: ApiRepositoryProtocol) -> ValleyCurrentResponse:
    coverage = await repo.fetch_coverage_metadata()
    mode = _coverage_mode(coverage)
    source: str | None = None
    timestamp: datetime | None = None
    dominant_pollutant: str | None = None
    composite_aqi: int | None = None

    if mode == CoverageMode.MODELED_BASELINE:
        points = await repo.fetch_modeled_points(pollutant="pm25")
        best_point = _max_point(points)
        if best_point is not None:
            composite_aqi = best_point.aqi
            dominant_pollutant = best_point.pollutant
            timestamp = best_point.timestamp
            source = best_point.source
    else:
        stations = await repo.fetch_station_summaries()
        best_station = _max_station(stations)
        if best_station is not None:
            composite_aqi = getattr(best_station, "current_aqi", None)
            dominant_pollutant = getattr(best_station, "dominant_pollutant", None)
            timestamp = getattr(best_station, "last_seen", None)
            source = getattr(best_station, "source", None)

    return ValleyCurrentResponse(
        timestamp=timestamp,
        composite_aqi=composite_aqi,
        dominant_pollutant=dominant_pollutant,
        recommendation=health_recommendation(composite_aqi, coverage_mode=mode),
        source=source,
        **coverage.model_dump(),
    )


async def get_valley_history_response(repo: ApiRepositoryProtocol, *, pollutant: str | None, hours: int, granularity: str) -> ValleyHistoryResponse:
    points = await repo.fetch_valley_history(pollutant=pollutant, hours=hours, granularity=granularity)
    return ValleyHistoryResponse(pollutant=pollutant, hours=hours, granularity=granularity, points=list(points))


async def get_interpolation_response(repo: ApiRepositoryProtocol, settings: ApiSettings, caches: ApiCaches, *, pollutant: str) -> InterpolationResponse:
    coverage = await repo.fetch_coverage_metadata()
    mode = _coverage_mode(coverage)
    cache_key = f"{mode.value}:{pollutant}:{settings.idw_rows}:{settings.idw_cols}:{settings.idw_power}"
    cached = await caches.idw.get(cache_key)
    if isinstance(cached, InterpolationResponse):
        return cached

    points: list[AQPoint] = []
    if mode in {CoverageMode.LIVE_OBSERVED, CoverageMode.RECENT_OBSERVED, CoverageMode.MODELED_BASELINE, CoverageMode.REPLAY_DEMO}:
        points = await repo.fetch_interpolation_points(mode=mode, pollutant=pollutant)

    source = interpolation_source_for_mode(mode)
    if len([point for point in points if point.aqi is not None]) < 3:
        response = InterpolationResponse(
            grid=InterpolationGrid(rows=settings.idw_rows, cols=settings.idw_cols, bounds=KATHMANDU_BOUNDS, values=[]),
            station_count=len(points),
            coverage_mode=mode,
            confidence=_coverage_confidence(coverage),
            source=source,
            computed_at=utc_now(),
            insufficient_data=True,
            message="Insufficient current data for IDW interpolation; clients should show station markers only.",
        )
    else:
        response = InterpolationResponse(
            grid=build_idw_grid(points, rows=settings.idw_rows, cols=settings.idw_cols, power=settings.idw_power),
            station_count=len(points),
            coverage_mode=mode,
            confidence=_coverage_confidence(coverage),
            source=source,
            computed_at=utc_now(),
            insufficient_data=False,
            message=coverage.message or "Interpolated current AQI using local meter distances.",
        )
    await caches.idw.set(cache_key, response)
    return response


TIMELINE_GRID_ROWS = 30
TIMELINE_GRID_COLS = 30


async def get_interpolation_timeline_response(
    repo: ApiRepositoryProtocol, settings: ApiSettings, caches: ApiCaches, *, pollutant: str, hours: int
) -> InterpolationTimelineResponse:
    cache_key = f"timeline:{pollutant}:{hours}"
    cached = await caches.idw.get(cache_key)
    if isinstance(cached, InterpolationTimelineResponse):
        return cached

    coverage = await repo.fetch_coverage_metadata()
    mode = _coverage_mode(coverage)
    source = interpolation_source_for_mode(mode)

    hourly_points = await repo.fetch_hourly_interpolation_points(pollutant=pollutant, hours=hours)

    now = utc_now()
    frames: list[TimelineFrame] = []
    for bucket in sorted(hourly_points.keys(), reverse=True):
        points = hourly_points[bucket]
        usable = [p for p in points if p.aqi is not None]
        insufficient = len(usable) < 3
        if insufficient:
            grid = InterpolationGrid(rows=TIMELINE_GRID_ROWS, cols=TIMELINE_GRID_COLS, bounds=KATHMANDU_BOUNDS, values=[])
        else:
            grid = build_idw_grid(points, rows=TIMELINE_GRID_ROWS, cols=TIMELINE_GRID_COLS, power=settings.idw_power)
        offset_hours = int((bucket - now).total_seconds() // 3600)
        offset_hours = max(offset_hours, -(hours - 1))
        frames.append(TimelineFrame(
            hour_offset=offset_hours,
            hour_bucket=bucket,
            grid=grid,
            station_count=len(points),
            insufficient_data=insufficient,
        ))

    frames = frames[:hours]

    response = InterpolationTimelineResponse(
        frames=frames,
        coverage_mode=mode,
        confidence=_coverage_confidence(coverage),
        source=source,
        computed_at=utc_now(),
        message=f"Timeline with {len(frames)} hourly frames" if frames else "No historical hourly data available",
    )
    await caches.idw.set(cache_key, response)
    return response


async def get_health_advisory_response(repo: ApiRepositoryProtocol, *, lat: float | None, lon: float | None) -> HealthAdvisoryResponse:
    coverage = await repo.fetch_coverage_metadata()
    nearest_station = None
    aqi: int | None = None
    if lat is not None and lon is not None:
        nearest_station = await repo.fetch_nearest_station(lat=lat, lon=lon)
        if nearest_station is not None:
            aqi = getattr(nearest_station, "current_aqi", None)
    if aqi is None:
        valley = await get_valley_current_response(repo)
        aqi = valley.composite_aqi
    return HealthAdvisoryResponse(
        aqi=aqi,
        category=health_category(aqi),
        recommendation=health_recommendation(aqi, coverage_mode=_coverage_mode(coverage)),
        nearest_station=nearest_station,
        **coverage.model_dump(),
    )


async def get_events_response(repo: ApiRepositoryProtocol, *, days: int, limit: int, lat: float | None, lon: float | None) -> EventsResponse:
    events = await repo.fetch_fire_events(days=days, limit=limit, lat=lat, lon=lon)
    return EventsResponse(events=list(events), count=len(events))


async def get_forecast_response(repo: ApiRepositoryProtocol, *, station_id: int, pollutant: str) -> ForecastResponse:
    return await repo.fetch_forecast(station_id, pollutant=pollutant)


async def get_wind_rose_response(repo: ApiRepositoryProtocol, *, hours: int, bins: int) -> WindRoseResponse:
    values = await repo.fetch_wind_rose(hours=hours, bins=bins)
    total_samples = sum(int(getattr(item, "sample_count", 0)) for item in values)
    return WindRoseResponse(hours=hours, bins=list(values), total_samples=total_samples)


async def get_pipeline_health_response(repo: ApiRepositoryProtocol, settings: ApiSettings) -> PipelineHealthResponse:
    now = utc_now()
    db_check = {"status": "ok"}
    try:
        await repo.ping()
    except Exception as exc:
        db_check = {"status": "down", "detail": str(exc)}

    try:
        coverage = await repo.fetch_coverage_metadata()
    except Exception as exc:
        coverage = CoverageMetadata(
            coverage_mode=CoverageMode.NO_DATA,
            confidence=Confidence.LOW,
            fresh_station_count=0,
            recent_station_count=0,
            modeled_available=False,
            replay_active=False,
            message=f"Coverage query failed: {exc}",
        )
    try:
        pipeline_runs = await repo.fetch_pipeline_runs()
    except Exception as exc:
        pipeline_runs = []
        db_check = {"status": "down", "detail": str(exc)}
    try:
        latest_aq_timestamp = await repo.fetch_latest_aq_timestamp()
    except Exception:
        latest_aq_timestamp = None
    try:
        latest_modeled_timestamp = await repo.fetch_latest_modeled_timestamp()
    except Exception:
        latest_modeled_timestamp = None
    kafka_check = await check_kafka_connectivity(settings)
    external_checks = await check_external_services(settings)

    checks = {
        "database": db_check,
        "kafka": kafka_check,
        "external_services": external_checks,
        "latest_aq_timestamp": latest_aq_timestamp.isoformat() if latest_aq_timestamp else None,
        "latest_modeled_timestamp": latest_modeled_timestamp.isoformat() if latest_modeled_timestamp else None,
        "coverage_mode": coverage.coverage_mode,
        "consumer_lag": kafka_check.get("consumer_lag"),
    }
    status = _overall_pipeline_status(checks=checks, coverage=coverage)
    return PipelineHealthResponse(
        status=status,
        service=settings.service_name,
        timestamp=now,
        checks=checks,
        pipeline_runs=list(pipeline_runs),
        coverage=coverage,
    )


def get_basic_health_response(settings: ApiSettings) -> BasicHealthResponse:
    driver_status = _async_driver_status(settings.database_url)
    status = "healthy" if driver_status["status"] == "ok" else "degraded"
    return BasicHealthResponse(
        status=status,
        service=settings.service_name,
        timestamp=utc_now(),
        checks={
            "api": "ok",
            "database_driver": driver_status,
            "kafka_consumer_enabled": settings.kafka_consumer_enabled,
        },
    )


def _overall_pipeline_status(*, checks: dict[str, object], coverage: CoverageMetadata) -> str:
    if _nested_status(checks.get("database")) == "down" or _coverage_mode(coverage) == CoverageMode.NO_DATA:
        return "down"
    statuses = {_nested_status(value) for value in checks.values()}
    if "down" in statuses or "degraded" in statuses:
        return "degraded"
    if _coverage_mode(coverage) != CoverageMode.LIVE_OBSERVED:
        return "degraded"
    return "healthy"


def _nested_status(value: object) -> str:
    if isinstance(value, dict):
        status = value.get("status")
        if isinstance(status, str):
            return status
    return "ok"


def _async_driver_status(database_url: str) -> dict[str, str]:
    if database_url.startswith("postgresql+asyncpg://"):
        try:
            import asyncpg  # noqa: F401
        except ModuleNotFoundError as exc:
            return {"status": "down", "detail": f"missing driver: {exc.name}"}
    return {"status": "ok"}


def _coverage_mode(coverage: CoverageMetadata) -> CoverageMode:
    return CoverageMode(str(coverage.coverage_mode))


def _coverage_confidence(coverage: CoverageMetadata) -> Confidence:
    return Confidence(str(coverage.confidence))


def _max_station_aqi(stations: list[object]) -> int | None:
    best = _max_station(stations)
    return int(getattr(best, "current_aqi")) if best is not None and getattr(best, "current_aqi", None) is not None else None


def _max_station(stations: list[object]) -> object | None:
    with_aqi = [station for station in stations if getattr(station, "current_aqi", None) is not None]
    if not with_aqi:
        return None
    return max(with_aqi, key=lambda station: int(getattr(station, "current_aqi")))


def _max_point(points: list[AQPoint]) -> AQPoint | None:
    with_aqi = [point for point in points if point.aqi is not None]
    if not with_aqi:
        return None
    return max(with_aqi, key=lambda point: int(point.aqi or 0))


def _max_point_aqi(points: list[AQPoint]) -> int | None:
    point = _max_point(points)
    return point.aqi if point is not None else None
