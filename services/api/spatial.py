from __future__ import annotations

from dataclasses import dataclass
from math import cos, hypot, radians
from typing import Sequence

from services.api.domain import AQPoint
from services.api.models import GridBounds, InterpolationGrid


KATHMANDU_BOUNDS = GridBounds(min_lat=27.55, max_lat=27.80, min_lon=85.20, max_lon=85.50)
KATHMANDU_CENTER_LAT = 27.7172
KATHMANDU_CENTER_LON = 85.3240
METERS_PER_DEGREE_LAT = 111_320.0
METERS_PER_DEGREE_LON = METERS_PER_DEGREE_LAT * cos(radians(KATHMANDU_CENTER_LAT))


@dataclass(frozen=True)
class ProjectedPoint:
    x: float
    y: float
    value: float


def build_idw_grid(
    points: Sequence[AQPoint],
    *,
    rows: int,
    cols: int,
    power: float,
    bounds: GridBounds = KATHMANDU_BOUNDS,
) -> InterpolationGrid:
    usable_points = [
        ProjectedPoint(
            x=_x_meters(point.lon),
            y=_y_meters(point.lat),
            value=float(point.aqi),
        )
        for point in points
        if point.aqi is not None
    ]
    if not usable_points:
        return InterpolationGrid(rows=rows, cols=cols, bounds=bounds, values=[])

    lat_step = 0.0 if rows <= 1 else (bounds.max_lat - bounds.min_lat) / (rows - 1)
    lon_step = 0.0 if cols <= 1 else (bounds.max_lon - bounds.min_lon) / (cols - 1)
    values: list[list[float | None]] = []

    for row_index in range(rows):
        lat = bounds.min_lat + row_index * lat_step
        row_values: list[float | None] = []
        y = _y_meters(lat)
        for col_index in range(cols):
            lon = bounds.min_lon + col_index * lon_step
            x = _x_meters(lon)
            row_values.append(round(_idw_value(usable_points, x=x, y=y, power=power), 2))
        values.append(row_values)

    return InterpolationGrid(rows=rows, cols=cols, bounds=bounds, values=values)


def _idw_value(points: Sequence[ProjectedPoint], *, x: float, y: float, power: float) -> float:
    weighted_sum = 0.0
    weight_total = 0.0
    for point in points:
        distance_m = hypot(point.x - x, point.y - y)
        if distance_m <= 1.0:
            return point.value
        weight = 1.0 / (distance_m**power)
        weighted_sum += weight * point.value
        weight_total += weight
    return weighted_sum / weight_total


def _x_meters(lon: float) -> float:
    return (lon - KATHMANDU_CENTER_LON) * METERS_PER_DEGREE_LON


def _y_meters(lat: float) -> float:
    return (lat - KATHMANDU_CENTER_LAT) * METERS_PER_DEGREE_LAT
