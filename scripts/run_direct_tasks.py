from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from airflow.dags.himalayaair.data_quality import run_data_quality_check
from airflow.dags.himalayaair.firms import run_firms_daily_load
from airflow.dags.himalayaair.openaq_backfill import run_openaq_historical_backfill
from airflow.dags.himalayaair.weather_backfill import run_weather_historical_backfill
from services.forecasting.run_once import run_forecast_once


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run HimalayaAir batch tasks directly without Airflow runtime.")
    parser.add_argument("task", choices=["forecast", "quality", "firms", "openaq_backfill", "weather_backfill"])
    parser.add_argument("--conf", default=None, help="Optional JSON object config payload.")
    parser.add_argument("--dry-run", action="store_true", help="Use dry-run where the task supports it.")
    return parser.parse_args()


def _load_conf(raw: str | None) -> dict[str, object]:
    if raw is None:
        return {}
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("--conf must be a JSON object")
    return payload


def main() -> int:
    args = parse_args()
    conf = _load_conf(args.conf)

    if args.task == "forecast":
        result = run_forecast_once(dry_run=args.dry_run)
        print(json.dumps({"status": result.status, "forecasts_written": result.forecasts_written}, indent=2))
        return 0 if result.status in {"success", "partial"} else 1

    if args.task == "quality":
        result = run_data_quality_check(conf)
    elif args.task == "firms":
        result = run_firms_daily_load(conf)
    elif args.task == "openaq_backfill":
        result = run_openaq_historical_backfill(conf)
    else:
        result = run_weather_historical_backfill(conf)

    print(json.dumps(result, indent=2, default=str))
    status = str(result.get("status", "failed"))
    return 0 if status in {"success", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
