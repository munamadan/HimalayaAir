from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from services.common.aqi_calculator import aqi_category
from shared.enums import Confidence, CoverageMode, ObservationType


@dataclass(frozen=True)
class AQPoint:
    id: int
    name: str
    lat: float
    lon: float
    aqi: int | None
    pollutant: str
    source: str
    observation_type: str
    timestamp: datetime


def choose_coverage_mode(
    *,
    fresh_station_count: int,
    recent_station_count: int,
    modeled_available: bool,
    replay_station_count: int,
    station_count: int,
) -> tuple[CoverageMode, Confidence, str]:
    if fresh_station_count >= 3:
        return (
            CoverageMode.LIVE_OBSERVED,
            Confidence.HIGH,
            "Using fresh observed station readings from the last 2 hours.",
        )
    if recent_station_count >= 3:
        return (
            CoverageMode.RECENT_OBSERVED,
            Confidence.MEDIUM,
            "Using latest observed readings from the last 24 hours because fewer than 3 stations reported in the last 2 hours.",
        )
    if modeled_available:
        return (
            CoverageMode.MODELED_BASELINE,
            Confidence.LOW,
            "Using Open-Meteo/CAMS modeled baseline because observed station coverage is sparse.",
        )
    if replay_station_count >= 3:
        return (
            CoverageMode.REPLAY_DEMO,
            Confidence.DEMO,
            "Using replayed historical readings from the live pipeline demo path.",
        )
    if station_count > 0:
        return (
            CoverageMode.STATION_ONLY,
            Confidence.LOW,
            "Insufficient coverage for interpolation; station markers should be shown without a heatmap.",
        )
    return (
        CoverageMode.NO_DATA,
        Confidence.LOW,
        "No safe current air-quality estimate is available.",
    )


def current_aqi_from_readings(readings: list[object]) -> tuple[int | None, str | None]:
    best_aqi: int | None = None
    dominant_pollutant: str | None = None
    for reading in readings:
        aqi = getattr(reading, "aqi", None)
        if aqi is None:
            continue
        if best_aqi is None or int(aqi) > best_aqi:
            best_aqi = int(aqi)
            dominant_pollutant = getattr(reading, "pollutant", None)
    return best_aqi, dominant_pollutant


def health_category(aqi: int | None) -> str | None:
    return aqi_category(aqi)


def health_recommendation(aqi: int | None, *, coverage_mode: CoverageMode | str | None = None) -> str:
    mode_value = coverage_mode.value if isinstance(coverage_mode, CoverageMode) else coverage_mode
    if mode_value == CoverageMode.NO_DATA.value or aqi is None:
        return "No safe current estimate is available. Check official advisories before outdoor activity."
    if aqi <= 50:
        return "Air quality is acceptable for most people."
    if aqi <= 100:
        return "Unusually sensitive people should consider reducing prolonged outdoor exertion."
    if aqi <= 150:
        return "Sensitive groups should limit prolonged outdoor exertion."
    if aqi <= 200:
        return "Everyone should reduce prolonged outdoor exertion; sensitive groups should avoid it."
    if aqi <= 300:
        return "Avoid prolonged outdoor exertion and consider indoor air filtration."
    return "Avoid outdoor activity where possible and follow local public-health guidance."


def interpolation_source_for_mode(mode: CoverageMode | str) -> str:
    mode_value = mode.value if isinstance(mode, CoverageMode) else mode
    if mode_value == CoverageMode.LIVE_OBSERVED.value:
        return "openaq_live"
    if mode_value == CoverageMode.RECENT_OBSERVED.value:
        return "openaq_live_recent"
    if mode_value == CoverageMode.MODELED_BASELINE.value:
        return "openmeteo_cams"
    if mode_value == CoverageMode.REPLAY_DEMO.value:
        return "demo_replay"
    return "none"


def observation_type_for_mode(mode: CoverageMode | str) -> ObservationType | None:
    mode_value = mode.value if isinstance(mode, CoverageMode) else mode
    if mode_value in {CoverageMode.LIVE_OBSERVED.value, CoverageMode.RECENT_OBSERVED.value}:
        return ObservationType.OBSERVED
    if mode_value == CoverageMode.REPLAY_DEMO.value:
        return ObservationType.REPLAY
    if mode_value == CoverageMode.MODELED_BASELINE.value:
        return ObservationType.MODELED
    return None
