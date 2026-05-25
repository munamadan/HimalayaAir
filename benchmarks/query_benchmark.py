from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras

DEFAULT_DB_URL = "postgresql://himalayaair:himalayaair@localhost:55432/himalayaair"


@dataclass(frozen=True)
class QueryCase:
    name: str
    query: str
    params: tuple[Any, ...]



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark continuous aggregate queries against raw equivalents.")
    parser.add_argument("--database-url", default=DEFAULT_DB_URL)
    parser.add_argument("--hours", type=int, default=72)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--output", default="tmp/benchmark-results/query-benchmark.json")
    return parser.parse_args()



def percentile(samples: list[float], value: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    idx = int(round((len(ordered) - 1) * value))
    return ordered[idx]



def run_case(cur: psycopg2.extensions.cursor, case: QueryCase, iterations: int, warmup: int) -> dict[str, Any]:
    for _ in range(warmup):
        cur.execute(case.query, case.params)
        cur.fetchall()

    durations: list[float] = []
    row_count = 0
    for _ in range(iterations):
        started = time.perf_counter()
        cur.execute(case.query, case.params)
        rows = cur.fetchall()
        durations.append((time.perf_counter() - started) * 1000.0)
        row_count = len(rows)

    return {
        "name": case.name,
        "query": case.query,
        "params": list(case.params),
        "row_count": row_count,
        "iterations": iterations,
        "latency_ms": {
            "avg": round(statistics.fmean(durations), 3),
            "p50": round(percentile(durations, 0.50), 3),
            "p95": round(percentile(durations, 0.95), 3),
            "p99": round(percentile(durations, 0.99), 3),
            "min": round(min(durations), 3),
            "max": round(max(durations), 3),
        },
    }



def build_cases(window_start: datetime, window_end: datetime) -> list[tuple[QueryCase, QueryCase]]:
    return [
        (
            QueryCase(
                name="aq_hourly_cagg",
                query=(
                    """
                    SELECT station_id, pollutant, hour_bucket, avg_value, avg_aqi, max_aqi, reading_count
                    FROM aq_hourly
                    WHERE hour_bucket >= %s AND hour_bucket < %s
                    ORDER BY hour_bucket, station_id, pollutant
                    """
                ).strip(),
                params=(window_start, window_end),
            ),
            QueryCase(
                name="aq_hourly_raw",
                query=(
                    """
                    SELECT
                        station_id,
                        pollutant,
                        time_bucket('1 hour', timestamp) AS hour_bucket,
                        AVG(value) AS avg_value,
                        AVG(aqi) AS avg_aqi,
                        MAX(aqi) AS max_aqi,
                        COUNT(*) AS reading_count
                    FROM aq_readings
                    WHERE NOT is_anomaly AND timestamp >= %s AND timestamp < %s
                    GROUP BY station_id, pollutant, hour_bucket
                    ORDER BY hour_bucket, station_id, pollutant
                    """
                ).strip(),
                params=(window_start, window_end),
            ),
        ),
        (
            QueryCase(
                name="aq_daily_cagg",
                query=(
                    """
                    SELECT station_id, pollutant, day_bucket, avg_value, avg_aqi, max_aqi, reading_count
                    FROM aq_daily
                    WHERE day_bucket >= %s AND day_bucket < %s
                    ORDER BY day_bucket, station_id, pollutant
                    """
                ).strip(),
                params=(window_start, window_end),
            ),
            QueryCase(
                name="aq_daily_raw",
                query=(
                    """
                    SELECT
                        station_id,
                        pollutant,
                        time_bucket('1 day', timestamp) AS day_bucket,
                        AVG(value) AS avg_value,
                        AVG(aqi) AS avg_aqi,
                        MAX(aqi) AS max_aqi,
                        COUNT(*) AS reading_count
                    FROM aq_readings
                    WHERE NOT is_anomaly AND timestamp >= %s AND timestamp < %s
                    GROUP BY station_id, pollutant, day_bucket
                    ORDER BY day_bucket, station_id, pollutant
                    """
                ).strip(),
                params=(window_start, window_end),
            ),
        ),
        (
            QueryCase(
                name="valley_daily_cagg",
                query=(
                    """
                    SELECT day_bucket, avg_aqi, max_aqi, station_count
                    FROM valley_daily
                    WHERE day_bucket >= %s AND day_bucket < %s
                    ORDER BY day_bucket
                    """
                ).strip(),
                params=(window_start, window_end),
            ),
            QueryCase(
                name="valley_daily_raw",
                query=(
                    """
                    SELECT
                        time_bucket('1 day', timestamp) AS day_bucket,
                        AVG(aqi) AS avg_aqi,
                        MAX(aqi) AS max_aqi,
                        COUNT(DISTINCT station_id) AS station_count
                    FROM aq_readings
                    WHERE NOT is_anomaly AND timestamp >= %s AND timestamp < %s
                    GROUP BY day_bucket
                    ORDER BY day_bucket
                    """
                ).strip(),
                params=(window_start, window_end),
            ),
        ),
    ]



def main() -> int:
    args = parse_args()
    now = datetime.now(tz=timezone.utc)
    window_end = now.replace(minute=0, second=0, microsecond=0)
    window_start = window_end - timedelta(hours=args.hours)

    result: dict[str, Any] = {
        "timestamp_utc": now.isoformat(),
        "database_url_redacted": args.database_url.split("@")[-1],
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "hours": args.hours,
        "iterations": args.iterations,
        "warmup": args.warmup,
        "families": [],
    }

    with psycopg2.connect(args.database_url) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT count(*)::bigint AS rows FROM aq_readings WHERE timestamp >= %s AND timestamp < %s", (window_start, window_end))
            total_rows = int(cur.fetchone()["rows"])
            result["window_aq_readings"] = total_rows

            for cagg_case, raw_case in build_cases(window_start, window_end):
                cagg_out = run_case(cur, cagg_case, args.iterations, args.warmup)
                raw_out = run_case(cur, raw_case, args.iterations, args.warmup)
                speedup = None
                if cagg_out["latency_ms"]["avg"] > 0:
                    speedup = round(raw_out["latency_ms"]["avg"] / cagg_out["latency_ms"]["avg"], 3)
                result["families"].append(
                    {
                        "family": cagg_case.name.replace("_cagg", ""),
                        "cagg": cagg_out,
                        "raw": raw_out,
                        "avg_speedup_x": speedup,
                    }
                )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output_path), "window_aq_readings": result.get("window_aq_readings")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
