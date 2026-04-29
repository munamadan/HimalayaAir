from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from math import isfinite


@dataclass(frozen=True)
class AQIBreakpoint:
    concentration_low: Decimal
    concentration_high: Decimal
    index_low: int
    index_high: int
    category: str
    color: str


PM25_BREAKPOINTS: tuple[AQIBreakpoint, ...] = (
    AQIBreakpoint(Decimal("0.0"), Decimal("9.0"), 0, 50, "Good", "#00e400"),
    AQIBreakpoint(Decimal("9.1"), Decimal("35.4"), 51, 100, "Moderate", "#ffff00"),
    AQIBreakpoint(Decimal("35.5"), Decimal("55.4"), 101, 150, "Unhealthy for Sensitive Groups", "#ff7e00"),
    AQIBreakpoint(Decimal("55.5"), Decimal("125.4"), 151, 200, "Unhealthy", "#ff0000"),
    AQIBreakpoint(Decimal("125.5"), Decimal("225.4"), 201, 300, "Very Unhealthy", "#8f3f97"),
    AQIBreakpoint(Decimal("225.5"), Decimal("325.4"), 301, 500, "Hazardous", "#7e0023"),
)

PM25_SUPPORTED_UNITS = {
    "ug/m3",
    "ug/m^3",
    "ug/m³",
    "µg/m3",
    "µg/m^3",
    "µg/m³",
    "μg/m3",
    "μg/m^3",
    "μg/m³",
}

PM25_EXTENDED_MAX_UG_M3 = Decimal("1000.0")


def normalize_pollutant(value: str) -> str:
    normalized = value.strip().lower().replace(".", "").replace("_", "")
    aliases = {
        "pm25": "pm25",
        "pm10": "pm10",
        "co": "co",
        "carbonmonoxide": "co",
        "no2": "no2",
        "nitrogendioxide": "no2",
        "o3": "o3",
        "ozone": "o3",
        "so2": "so2",
        "sulphurdioxide": "so2",
        "sulfurdioxide": "so2",
    }
    return aliases.get(normalized, normalized)


def calculate_aqi(pollutant: str, value: float, unit: str = "ug/m3") -> int | None:
    if normalize_pollutant(pollutant) != "pm25":
        return None
    if not _is_supported_pm25_unit(unit):
        return None
    if not isfinite(value):
        return None

    concentration = _truncate_decimal(value, decimal_places=1)
    if concentration < Decimal("0.0") or concentration > PM25_EXTENDED_MAX_UG_M3:
        return None

    breakpoint = _pm25_breakpoint_for(concentration)
    if breakpoint is None:
        breakpoint = PM25_BREAKPOINTS[-1]

    return _linear_aqi(concentration, breakpoint)


def aqi_category(aqi: int | None) -> str | None:
    if aqi is None:
        return None
    for breakpoint in PM25_BREAKPOINTS:
        if breakpoint.index_low <= aqi <= breakpoint.index_high:
            return breakpoint.category
    if aqi > PM25_BREAKPOINTS[-1].index_high:
        return PM25_BREAKPOINTS[-1].category
    return None


def aqi_color(aqi: int | None) -> str | None:
    if aqi is None:
        return None
    for breakpoint in PM25_BREAKPOINTS:
        if breakpoint.index_low <= aqi <= breakpoint.index_high:
            return breakpoint.color
    if aqi > PM25_BREAKPOINTS[-1].index_high:
        return PM25_BREAKPOINTS[-1].color
    return None


def _is_supported_pm25_unit(value: str) -> bool:
    normalized = value.strip().lower().replace(" ", "")
    return normalized in PM25_SUPPORTED_UNITS


def _truncate_decimal(value: float, *, decimal_places: int) -> Decimal:
    quantizer = Decimal("1").scaleb(-decimal_places)
    return Decimal(str(value)).quantize(quantizer, rounding=ROUND_DOWN)


def _pm25_breakpoint_for(concentration: Decimal) -> AQIBreakpoint | None:
    for breakpoint in PM25_BREAKPOINTS:
        if breakpoint.concentration_low <= concentration <= breakpoint.concentration_high:
            return breakpoint
    return None


def _linear_aqi(concentration: Decimal, breakpoint: AQIBreakpoint) -> int:
    numerator = Decimal(breakpoint.index_high - breakpoint.index_low)
    denominator = breakpoint.concentration_high - breakpoint.concentration_low
    index = (numerator / denominator) * (concentration - breakpoint.concentration_low) + breakpoint.index_low
    return int(index.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
