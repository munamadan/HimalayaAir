from __future__ import annotations

from enum import Enum


class StrValueEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class CoverageMode(StrValueEnum):
    LIVE_OBSERVED = "LIVE_OBSERVED"
    RECENT_OBSERVED = "RECENT_OBSERVED"
    MODELED_BASELINE = "MODELED_BASELINE"
    REPLAY_DEMO = "REPLAY_DEMO"
    STATION_ONLY = "STATION_ONLY"
    NO_DATA = "NO_DATA"


class ObservationType(StrValueEnum):
    OBSERVED = "observed"
    MODELED = "modeled"
    REPLAY = "replay"
    SYNTHETIC = "synthetic"


class Confidence(StrValueEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    DEMO = "demo"


class SourceName(StrValueEnum):
    OPENAQ_LIVE = "openaq_live"
    OPENAQ_ARCHIVE = "openaq_archive"
    OPENMETEO_CAMS = "openmeteo_cams"
    OPENMETEO_WEATHER = "openmeteo_weather"
    DEMO_REPLAY = "demo_replay"
    MANUAL_SEED = "manual_seed"

