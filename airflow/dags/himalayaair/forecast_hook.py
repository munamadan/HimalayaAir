from __future__ import annotations

from typing import Any

from services.forecasting.config import ForecastSettings
from services.forecasting.run_once import run_forecast_once
from shared.time_utils import parse_utc


def run_forecast_recompute(conf: dict[str, Any] | None = None) -> dict[str, object]:
    resolved_conf = conf or {}
    settings = ForecastSettings.from_env()
    result = run_forecast_once(
        settings=settings,
        dry_run=_bool_conf(resolved_conf, "dry_run", False),
        station_id=_optional_int_conf(resolved_conf, "station_id"),
        pollutants=_pollutants_conf(resolved_conf),
        generated_at=parse_utc(str(resolved_conf["generated_at"])) if resolved_conf.get("generated_at") else None,
    )
    return {
        "status": result.status,
        "forecast_run_id": result.forecast_run_id,
        "stations_attempted": result.stations_attempted,
        "stations_succeeded": result.stations_succeeded,
        "forecasts_written": result.forecasts_written,
        "accuracy_records_written": result.accuracy_records_written,
        "fallback_reason": result.fallback_reason,
        "error_message": result.error_message,
    }


def run_forecast_recompute_hook(conf: dict[str, Any] | None = None) -> dict[str, object]:
    return run_forecast_recompute(conf)


def _optional_int_conf(conf: dict[str, Any], key: str) -> int | None:
    value = conf.get(key)
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be an integer") from exc
    if parsed < 0:
        raise ValueError(f"{key} must be non-negative")
    return parsed


def _pollutants_conf(conf: dict[str, Any]) -> tuple[str, ...] | None:
    value = conf.get("pollutants") or conf.get("pollutant")
    if value is None or value == "":
        return None
    if isinstance(value, str):
        pollutants = tuple(part.strip() for part in value.split(",") if part.strip())
    elif isinstance(value, list):
        pollutants = tuple(str(part).strip() for part in value if str(part).strip())
    else:
        raise ValueError("pollutants must be a string or list")
    return pollutants or None


def _bool_conf(conf: dict[str, Any], key: str, default: bool) -> bool:
    value = conf.get(key, default)
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{key} must be a boolean")
