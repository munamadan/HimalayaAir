from __future__ import annotations

import math
from datetime import datetime, timezone

import httpx

from services.api.cache import TTLCache
from services.api.models import GridBounds, WindGridPoint, WindGridResponse
from shared.logging_config import get_logger

logger = get_logger(__name__)

GRID_ROWS = 6
GRID_COLS = 8
BOUNDS = GridBounds(min_lat=27.57, max_lat=27.77, min_lon=85.225, max_lon=85.49)
CACHE_TTL_SECONDS = 900.0
OPENMETEO_TIMEOUT_SECONDS = 15.0

_cache: TTLCache[WindGridResponse] = TTLCache(ttl_seconds=CACHE_TTL_SECONDS)
_CACHE_KEY = "wind_grid"


def _build_grid_coordinates() -> tuple[list[float], list[float]]:
    lats: list[float] = []
    lons: list[float] = []
    lat_step = (BOUNDS.max_lat - BOUNDS.min_lat) / (GRID_ROWS - 1)
    lon_step = (BOUNDS.max_lon - BOUNDS.min_lon) / (GRID_COLS - 1)
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            lats.append(round(BOUNDS.min_lat + row * lat_step, 4))
            lons.append(round(BOUNDS.min_lon + col * lon_step, 4))
    return lats, lons


def _speed_dir_to_uv(speed: float, direction: float) -> tuple[float, float]:
    rad = math.radians(direction)
    u = -speed * math.sin(rad)
    v = -speed * math.cos(rad)
    return round(u, 3), round(v, 3)


async def fetch_wind_grid_from_openmeteo() -> WindGridResponse | None:
    lats, lons = _build_grid_coordinates()
    lat_csv = ",".join(str(lat) for lat in lats)
    lon_csv = ",".join(str(lon) for lon in lons)

    params = {
        "latitude": lat_csv,
        "longitude": lon_csv,
        "hourly": "wind_speed_10m,wind_direction_10m",
        "forecast_days": "1",
        "timezone": "UTC",
    }

    try:
        async with httpx.AsyncClient(timeout=OPENMETEO_TIMEOUT_SECONDS) as client:
            response = await client.get(
                "https://api.open-meteo.com/v1/forecast", params=params
            )

        if response.status_code == 429:
            logger.warning("wind_grid_rate_limited")
            return None

        if response.status_code != 200:
            logger.warning("wind_grid_fetch_failed", status=response.status_code)
            return None

        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("wind_grid_fetch_error", error=str(exc))
        return None

    now_utc = datetime.now(timezone.utc)
    current_hour_iso = now_utc.strftime("%Y-%m-%dT%H:00")

    grid: list[list[WindGridPoint]] = []
    locations = payload if isinstance(payload, list) else [payload]

    if len(locations) != GRID_ROWS * GRID_COLS:
        logger.warning(
            "wind_grid_unexpected_location_count",
            expected=GRID_ROWS * GRID_COLS,
            got=len(locations),
        )
        return None

    for row in range(GRID_ROWS):
        row_points: list[WindGridPoint] = []
        for col in range(GRID_COLS):
            idx = row * GRID_COLS + col
            loc_data = locations[idx]
            hourly = loc_data.get("hourly", {})
            times = hourly.get("time", [])
            speeds = hourly.get("wind_speed_10m", [])
            directions = hourly.get("wind_direction_10m", [])

            speed = 0.0
            direction = 0.0
            try:
                hour_idx = times.index(current_hour_iso)
                speed = float(speeds[hour_idx] or 0)
                direction = float(directions[hour_idx] or 0)
            except (ValueError, IndexError, TypeError):
                if speeds and directions:
                    speed = float(speeds[0] or 0)
                    direction = float(directions[0] or 0)

            u, v = _speed_dir_to_uv(speed, direction)
            row_points.append(WindGridPoint(u=u, v=v))
        grid.append(row_points)

    return WindGridResponse(
        rows=GRID_ROWS,
        cols=GRID_COLS,
        bounds=BOUNDS,
        timestamp=now_utc,
        grid=grid,
    )


async def get_wind_grid() -> WindGridResponse | None:
    cached = await _cache.get(_CACHE_KEY)
    if cached is not None:
        return cached

    result = await fetch_wind_grid_from_openmeteo()
    if result is not None:
        await _cache.set(_CACHE_KEY, result)
    return result
