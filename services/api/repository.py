from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.config import ApiSettings
from services.api.domain import AQPoint, choose_coverage_mode, current_aqi_from_readings, health_category
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
from services.common.aqi_calculator import calculate_aqi, normalize_pollutant
from shared.enums import Confidence, CoverageMode, ObservationType, SourceName
from shared.time_utils import ensure_utc, utc_now


class ApiNotFoundError(RuntimeError):
    pass


class ApiRepository:
    def __init__(self, session: AsyncSession, settings: ApiSettings) -> None:
        self.session = session
        self.settings = settings

    async def ping(self) -> bool:
        await self.session.execute(text("SELECT 1"))
        return True

    async def fetch_coverage_metadata(self) -> CoverageMetadata:
        counts_result = await self.session.execute(
            text(
                """
                SELECT
                    COUNT(DISTINCT station_id) FILTER (
                        WHERE observation_type = 'observed'
                          AND timestamp >= NOW() - (:fresh_hours * INTERVAL '1 hour')
                    )::int AS fresh_station_count,
                    COUNT(DISTINCT station_id) FILTER (
                        WHERE observation_type = 'observed'
                          AND timestamp >= NOW() - (:recent_hours * INTERVAL '1 hour')
                    )::int AS recent_station_count,
                    COUNT(DISTINCT station_id) FILTER (
                        WHERE observation_type = 'replay'
                          AND timestamp >= NOW() - (:recent_hours * INTERVAL '1 hour')
                    )::int AS replay_station_count
                FROM aq_readings
                WHERE timestamp >= NOW() - (:recent_hours * INTERVAL '1 hour')
                """
            ),
            {"fresh_hours": self.settings.fresh_hours, "recent_hours": self.settings.recent_hours},
        )
        counts = counts_result.mappings().one()
        station_count_result = await self.session.execute(text("SELECT COUNT(*)::int FROM stations WHERE active = TRUE"))
        station_count = int(station_count_result.scalar_one() or 0)
        modeled_available = await self._modeled_available()
        snapshot_message = await self._latest_coverage_snapshot_message()

        mode, confidence, generated_message = choose_coverage_mode(
            fresh_station_count=int(counts["fresh_station_count"] or 0),
            recent_station_count=int(counts["recent_station_count"] or 0),
            modeled_available=modeled_available,
            replay_station_count=int(counts["replay_station_count"] or 0),
            station_count=station_count,
        )
        return CoverageMetadata(
            coverage_mode=mode,
            confidence=confidence,
            fresh_station_count=int(counts["fresh_station_count"] or 0),
            recent_station_count=int(counts["recent_station_count"] or 0),
            modeled_available=modeled_available,
            replay_active=int(counts["replay_station_count"] or 0) > 0,
            message=snapshot_message or generated_message,
        )

    async def fetch_station_summaries(self) -> list[StationSummary]:
        result = await self.session.execute(
            text(
                """
                WITH latest AS (
                    SELECT DISTINCT ON (ar.station_id, ar.pollutant)
                        ar.station_id,
                        ar.pollutant,
                        ar.aqi,
                        ar.timestamp,
                        ar.source,
                        ar.observation_type,
                        ar.coverage_mode,
                        ar.confidence
                    FROM aq_readings ar
                    WHERE ar.timestamp >= NOW() - (:recent_hours * INTERVAL '1 hour')
                      AND ar.is_anomaly = FALSE
                    ORDER BY ar.station_id, ar.pollutant, ar.timestamp DESC
                ),
                ranked AS (
                    SELECT
                        latest.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY latest.station_id
                            ORDER BY latest.aqi DESC NULLS LAST, latest.timestamp DESC
                        ) AS reading_rank
                    FROM latest
                )
                SELECT
                    s.id,
                    s.name,
                    ST_Y(s.location)::float8 AS lat,
                    ST_X(s.location)::float8 AS lon,
                    s.active,
                    s.status,
                    s.last_seen,
                    r.aqi,
                    r.pollutant,
                    r.timestamp,
                    r.source,
                    r.observation_type,
                    r.coverage_mode,
                    r.confidence
                FROM stations s
                LEFT JOIN ranked r ON r.station_id = s.id AND r.reading_rank = 1
                ORDER BY s.name, s.id
                """
            ),
            {"recent_hours": self.settings.recent_hours},
        )
        now = utc_now()
        stations: list[StationSummary] = []
        for row in result.mappings():
            timestamp = _optional_datetime(row["timestamp"])
            aqi = _optional_int(row["aqi"])
            stations.append(
                StationSummary(
                    id=int(row["id"]),
                    name=str(row["name"]),
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    active=bool(row["active"]),
                    status=str(row["status"]),
                    last_seen=_optional_datetime(row["last_seen"]),
                    current_aqi=aqi,
                    dominant_pollutant=_optional_str(row["pollutant"]),
                    source=_optional_str(row["source"]),
                    observation_type=_optional_str(row["observation_type"]),
                    coverage_mode=_fallback_coverage_mode(
                        row["coverage_mode"],
                        row["observation_type"],
                        timestamp,
                        now=now,
                        fresh_hours=self.settings.fresh_hours,
                    ),
                    confidence=_fallback_confidence(row["confidence"], row["observation_type"], timestamp, now, self.settings.fresh_hours),
                    freshness_minutes=_freshness_minutes(timestamp, now=now),
                    health_category=health_category(aqi),
                )
            )
        return stations

    async def fetch_station_identity(self, station_id: int) -> StationIdentity:
        result = await self.session.execute(
            text(
                """
                SELECT
                    id,
                    name,
                    ST_Y(location)::float8 AS lat,
                    ST_X(location)::float8 AS lon,
                    active,
                    status,
                    last_seen
                FROM stations
                WHERE id = :station_id
                """
            ),
            {"station_id": station_id},
        )
        row = result.mappings().first()
        if row is None:
            raise ApiNotFoundError(f"station {station_id} was not found")
        return StationIdentity(
            id=int(row["id"]),
            name=str(row["name"]),
            lat=float(row["lat"]),
            lon=float(row["lon"]),
            active=bool(row["active"]),
            status=str(row["status"]),
            last_seen=_optional_datetime(row["last_seen"]),
        )

    async def fetch_station_current_readings(self, station_id: int) -> list[PollutantCurrent]:
        result = await self.session.execute(
            text(
                """
                SELECT DISTINCT ON (pollutant)
                    pollutant,
                    value::float8 AS value,
                    unit,
                    aqi,
                    timestamp,
                    is_anomaly,
                    anomaly_reason,
                    quality_flag,
                    source,
                    observation_type,
                    coverage_mode,
                    confidence
                FROM aq_readings
                WHERE station_id = :station_id
                  AND timestamp >= NOW() - (:recent_hours * INTERVAL '1 hour')
                ORDER BY pollutant, timestamp DESC
                """
            ),
            {"station_id": station_id, "recent_hours": self.settings.recent_hours},
        )
        now = utc_now()
        readings: list[PollutantCurrent] = []
        for row in result.mappings():
            timestamp = ensure_utc(row["timestamp"])
            aqi = _optional_int(row["aqi"])
            readings.append(
                PollutantCurrent(
                    pollutant=normalize_pollutant(str(row["pollutant"])),
                    value=float(row["value"]),
                    unit=str(row["unit"]),
                    aqi=aqi,
                    timestamp=timestamp,
                    freshness_minutes=_freshness_minutes(timestamp, now=now),
                    is_anomaly=bool(row["is_anomaly"]),
                    anomaly_reason=_optional_str(row["anomaly_reason"]),
                    quality_flag=str(row["quality_flag"]),
                    source=str(row["source"]),
                    observation_type=str(row["observation_type"]),
                    coverage_mode=_fallback_coverage_mode(
                        row["coverage_mode"],
                        row["observation_type"],
                        timestamp,
                        now=now,
                        fresh_hours=self.settings.fresh_hours,
                    ),
                    confidence=_fallback_confidence(row["confidence"], row["observation_type"], timestamp, now, self.settings.fresh_hours),
                    health_category=health_category(aqi),
                )
            )
        return readings

    async def fetch_station_history(self, station_id: int, *, pollutant: str | None, hours: int, limit: int) -> StationHistoryResponse:
        await self.fetch_station_identity(station_id)
        normalized_pollutant = normalize_pollutant(pollutant) if pollutant else None
        result = await self.session.execute(
            text(
                """
                SELECT
                    timestamp,
                    pollutant,
                    value::float8 AS value,
                    unit,
                    aqi,
                    is_anomaly,
                    quality_flag,
                    source,
                    observation_type,
                    coverage_mode,
                    confidence
                FROM aq_readings
                WHERE station_id = :station_id
                  AND timestamp >= NOW() - (:hours * INTERVAL '1 hour')
                  AND (:pollutant IS NULL OR pollutant = :pollutant)
                ORDER BY timestamp ASC
                LIMIT :limit
                """
            ),
            {"station_id": station_id, "hours": hours, "pollutant": normalized_pollutant, "limit": limit},
        )
        readings = [
            HistoryPoint(
                timestamp=ensure_utc(row["timestamp"]),
                pollutant=normalize_pollutant(str(row["pollutant"])),
                value=float(row["value"]),
                unit=str(row["unit"]),
                aqi=_optional_int(row["aqi"]),
                is_anomaly=bool(row["is_anomaly"]),
                quality_flag=str(row["quality_flag"]),
                source=str(row["source"]),
                observation_type=str(row["observation_type"]),
                coverage_mode=_optional_str(row["coverage_mode"]),
                confidence=_optional_str(row["confidence"]),
            )
            for row in result.mappings()
        ]
        return StationHistoryResponse(station_id=station_id, pollutant=normalized_pollutant, hours=hours, readings=readings)

    async def fetch_valley_history(self, *, pollutant: str | None, hours: int, granularity: str) -> list[ValleyHistoryPoint]:
        normalized_pollutant = normalize_pollutant(pollutant) if pollutant else None
        bucket_sql = "hour" if granularity == "hour" else "day"
        result = await self.session.execute(
            text(
                f"""
                SELECT
                    date_trunc('{bucket_sql}', timestamp) AS bucket_start,
                    pollutant,
                    AVG(aqi)::float8 AS avg_aqi,
                    MAX(aqi)::int AS max_aqi,
                    COUNT(DISTINCT station_id)::int AS station_count,
                    COUNT(*)::int AS reading_count
                FROM aq_readings
                WHERE timestamp >= NOW() - (:hours * INTERVAL '1 hour')
                  AND aqi IS NOT NULL
                  AND is_anomaly = FALSE
                  AND (:pollutant IS NULL OR pollutant = :pollutant)
                GROUP BY bucket_start, pollutant
                ORDER BY bucket_start ASC, pollutant ASC
                """
            ),
            {"hours": hours, "pollutant": normalized_pollutant},
        )
        return [
            ValleyHistoryPoint(
                bucket_start=ensure_utc(row["bucket_start"]),
                pollutant=normalize_pollutant(str(row["pollutant"])),
                avg_aqi=float(row["avg_aqi"]) if row["avg_aqi"] is not None else None,
                max_aqi=_optional_int(row["max_aqi"]),
                station_count=int(row["station_count"]),
                reading_count=int(row["reading_count"]),
            )
            for row in result.mappings()
        ]

    async def fetch_interpolation_points(self, *, mode: CoverageMode, pollutant: str) -> list[AQPoint]:
        if mode == CoverageMode.MODELED_BASELINE:
            return await self.fetch_modeled_points(pollutant=pollutant)
        observation_type = ObservationType.REPLAY.value if mode == CoverageMode.REPLAY_DEMO else ObservationType.OBSERVED.value
        hours = self.settings.fresh_hours if mode == CoverageMode.LIVE_OBSERVED else self.settings.recent_hours
        result = await self.session.execute(
            text(
                """
                SELECT DISTINCT ON (ar.station_id)
                    ar.station_id,
                    s.name,
                    ST_Y(s.location)::float8 AS lat,
                    ST_X(s.location)::float8 AS lon,
                    ar.pollutant,
                    ar.value::float8 AS value,
                    ar.unit,
                    ar.aqi,
                    ar.source,
                    ar.observation_type,
                    ar.timestamp
                FROM aq_readings ar
                JOIN stations s ON s.id = ar.station_id
                WHERE ar.pollutant = :pollutant
                  AND ar.observation_type = :observation_type
                  AND ar.timestamp >= NOW() - (:hours * INTERVAL '1 hour')
                  AND ar.is_anomaly = FALSE
                ORDER BY ar.station_id, ar.timestamp DESC
                """
            ),
            {"pollutant": normalize_pollutant(pollutant), "observation_type": observation_type, "hours": hours},
        )
        return [_point_from_station_row(row) for row in result.mappings()]

    async def fetch_modeled_points(self, *, pollutant: str) -> list[AQPoint]:
        result = await self.session.execute(
            text(
                """
                SELECT DISTINCT ON (m.model_location_id)
                    m.model_location_id AS id,
                    wl.name,
                    ST_Y(wl.location)::float8 AS lat,
                    ST_X(wl.location)::float8 AS lon,
                    m.pollutant,
                    m.value::float8 AS value,
                    m.unit,
                    m.us_aqi,
                    m.source,
                    m.observation_type,
                    m.timestamp
                FROM modeled_aq_readings m
                JOIN weather_locations wl ON wl.id = m.model_location_id
                WHERE m.pollutant = :pollutant
                  AND m.coverage_mode = 'MODELED_BASELINE'
                  AND m.timestamp >= NOW() - (:modeled_hours * INTERVAL '1 hour')
                  AND m.timestamp <= NOW() + INTERVAL '3 hours'
                ORDER BY m.model_location_id, m.timestamp DESC, m.model_run_at DESC
                """
            ),
            {"pollutant": normalize_pollutant(pollutant), "modeled_hours": self.settings.modeled_hours},
        )
        points: list[AQPoint] = []
        for row in result.mappings():
            value = float(row["value"]) if row["value"] is not None else None
            aqi = _optional_int(row["us_aqi"])
            if aqi is None and value is not None:
                aqi = calculate_aqi(str(row["pollutant"]), value, str(row["unit"] or "ug/m3"))
            points.append(
                AQPoint(
                    id=int(row["id"]),
                    name=str(row["name"]),
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    aqi=aqi,
                    pollutant=normalize_pollutant(str(row["pollutant"])),
                    source=str(row["source"]),
                    observation_type=str(row["observation_type"]),
                    timestamp=ensure_utc(row["timestamp"]),
                )
            )
        return points

    async def fetch_nearest_station(self, *, lat: float, lon: float) -> NearestStation | None:
        result = await self.session.execute(
            text(
                """
                SELECT
                    id,
                    name,
                    ST_Y(location)::float8 AS lat,
                    ST_X(location)::float8 AS lon,
                    (
                        ST_Distance(
                            location::geography,
                            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                        ) / 1000.0
                    )::float8 AS distance_km
                FROM stations
                WHERE active = TRUE
                ORDER BY ST_Distance(
                    location::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                )
                LIMIT 1
                """
            ),
            {"lat": lat, "lon": lon},
        )
        row = result.mappings().first()
        if row is None:
            return None
        readings = await self.fetch_station_current_readings(int(row["id"]))
        current_aqi, _dominant_pollutant = current_aqi_from_readings(readings)
        return NearestStation(
            id=int(row["id"]),
            name=str(row["name"]),
            lat=float(row["lat"]),
            lon=float(row["lon"]),
            distance_km=round(float(row["distance_km"]), 3),
            current_aqi=current_aqi,
        )

    async def fetch_fire_events(self, *, days: int, limit: int, lat: float | None, lon: float | None) -> list[FireEvent]:
        if lat is not None and lon is not None:
            sql = """
                SELECT
                    id,
                    latitude::float8 AS lat,
                    longitude::float8 AS lon,
                    acq_date,
                    acq_time,
                    satellite,
                    instrument,
                    confidence,
                    frp::float8 AS frp,
                    brightness::float8 AS brightness,
                    source,
                    event_hash,
                    (
                        ST_Distance(
                            location::geography,
                            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                        ) / 1000.0
                    )::float8 AS distance_km
                FROM fire_events
                WHERE acq_date >= CURRENT_DATE - (:days * INTERVAL '1 day')
                ORDER BY distance_km ASC, acq_date DESC
                LIMIT :limit
            """
        else:
            sql = """
                SELECT
                    id,
                    latitude::float8 AS lat,
                    longitude::float8 AS lon,
                    acq_date,
                    acq_time,
                    satellite,
                    instrument,
                    confidence,
                    frp::float8 AS frp,
                    brightness::float8 AS brightness,
                    source,
                    event_hash,
                    NULL::float8 AS distance_km
                FROM fire_events
                WHERE acq_date >= CURRENT_DATE - (:days * INTERVAL '1 day')
                ORDER BY acq_date DESC, acq_time DESC NULLS LAST
                LIMIT :limit
            """
        result = await self.session.execute(text(sql), {"days": days, "limit": limit, "lat": lat, "lon": lon})
        return [
            FireEvent(
                id=int(row["id"]),
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                acq_date=row["acq_date"],
                acq_time=_optional_int(row["acq_time"]),
                satellite=_optional_str(row["satellite"]),
                instrument=_optional_str(row["instrument"]),
                confidence=_optional_str(row["confidence"]),
                frp=float(row["frp"]) if row["frp"] is not None else None,
                brightness=float(row["brightness"]) if row["brightness"] is not None else None,
                source=str(row["source"]),
                event_hash=str(row["event_hash"]),
                distance_km=round(float(row["distance_km"]), 3) if row["distance_km"] is not None else None,
            )
            for row in result.mappings()
        ]

    async def fetch_pipeline_runs(self) -> list[PipelineRunHealth]:
        result = await self.session.execute(
            text(
                """
                SELECT DISTINCT ON (component)
                    component,
                    run_at,
                    status,
                    records_processed,
                    error_message,
                    duration_seconds::float8 AS duration_seconds,
                    metadata
                FROM pipeline_runs
                ORDER BY component, run_at DESC
                """
            )
        )
        return [
            PipelineRunHealth(
                component=str(row["component"]),
                run_at=_optional_datetime(row["run_at"]),
                status=str(row["status"]),
                records_processed=_optional_int(row["records_processed"]),
                error_message=_optional_str(row["error_message"]),
                duration_seconds=float(row["duration_seconds"]) if row["duration_seconds"] is not None else None,
                metadata=dict(row["metadata"] or {}),
            )
            for row in result.mappings()
        ]

    async def fetch_latest_aq_timestamp(self) -> datetime | None:
        result = await self.session.execute(text("SELECT MAX(timestamp) FROM aq_readings"))
        return _optional_datetime(result.scalar_one_or_none())

    async def fetch_latest_modeled_timestamp(self) -> datetime | None:
        result = await self.session.execute(text("SELECT MAX(timestamp) FROM modeled_aq_readings WHERE timestamp <= NOW() + INTERVAL '3 hours'"))
        return _optional_datetime(result.scalar_one_or_none())

    async def _modeled_available(self) -> bool:
        result = await self.session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM modeled_aq_readings
                    WHERE coverage_mode = 'MODELED_BASELINE'
                      AND timestamp >= NOW() - (:modeled_hours * INTERVAL '1 hour')
                      AND timestamp <= NOW() + INTERVAL '3 hours'
                )
                """
            ),
            {"modeled_hours": self.settings.modeled_hours},
        )
        return bool(result.scalar_one())

    async def _latest_coverage_snapshot_message(self) -> str | None:
        result = await self.session.execute(
            text(
                """
                SELECT message
                FROM coverage_snapshots
                WHERE created_at >= NOW() - (:recent_hours * INTERVAL '1 hour')
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"recent_hours": self.settings.recent_hours},
        )
        value = result.scalar_one_or_none()
        return _optional_str(value)


def _point_from_station_row(row: Any) -> AQPoint:
    value = float(row["value"]) if row["value"] is not None else None
    aqi = _optional_int(row["aqi"])
    if aqi is None and value is not None:
        aqi = calculate_aqi(str(row["pollutant"]), value, str(row["unit"] or "ug/m3"))
    return AQPoint(
        id=int(row["station_id"]),
        name=str(row["name"]),
        lat=float(row["lat"]),
        lon=float(row["lon"]),
        aqi=aqi,
        pollutant=normalize_pollutant(str(row["pollutant"])),
        source=str(row["source"]),
        observation_type=str(row["observation_type"]),
        timestamp=ensure_utc(row["timestamp"]),
    )


def _freshness_minutes(timestamp: datetime | None, *, now: datetime) -> int | None:
    if timestamp is None:
        return None
    delta = now - ensure_utc(timestamp)
    return max(int(delta.total_seconds() // 60), 0)


def _optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return ensure_utc(value)
    return ensure_utc(datetime.fromisoformat(str(value)))


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text_value = str(value)
    return text_value if text_value else None


def _fallback_coverage_mode(
    stored_value: Any,
    observation_type: Any,
    timestamp: datetime | None,
    *,
    now: datetime,
    fresh_hours: int,
) -> str | None:
    if stored_value:
        return str(stored_value)
    if observation_type == ObservationType.REPLAY.value:
        return CoverageMode.REPLAY_DEMO.value
    if observation_type == ObservationType.MODELED.value:
        return CoverageMode.MODELED_BASELINE.value
    if observation_type == ObservationType.OBSERVED.value and timestamp is not None:
        freshness = _freshness_minutes(timestamp, now=now)
        if freshness is not None and freshness <= fresh_hours * 60:
            return CoverageMode.LIVE_OBSERVED.value
        return CoverageMode.RECENT_OBSERVED.value
    return None


def _fallback_confidence(stored_value: Any, observation_type: Any, timestamp: datetime | None, now: datetime, fresh_hours: int) -> str | None:
    if stored_value:
        return str(stored_value)
    if observation_type == ObservationType.REPLAY.value:
        return Confidence.DEMO.value
    if observation_type == ObservationType.MODELED.value:
        return Confidence.LOW.value
    if observation_type == ObservationType.OBSERVED.value and timestamp is not None:
        freshness = _freshness_minutes(timestamp, now=now)
        if freshness is not None and freshness <= fresh_hours * 60:
            return Confidence.HIGH.value
        return Confidence.MEDIUM.value
    return None
