from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


@dataclass(frozen=True)
class Endpoint:
    name: str
    path: str


ENDPOINTS: tuple[Endpoint, ...] = (
    Endpoint("health", "/health"),
    Endpoint("stations", "/api/stations"),
    Endpoint("valley_current", "/api/valley/current"),
    Endpoint("valley_history", "/api/valley/history?hours=72&granularity=hour"),
    Endpoint("interpolation_current", "/api/interpolation/current?pollutant=pm25"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Async API load test for HimalayaAir read endpoints.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--requests-per-user", type=int, default=20)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--output", default="tmp/benchmark-results/api-load-test.json")
    return parser.parse_args()


def percentile(samples: list[float], value: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    idx = int(round((len(ordered) - 1) * value))
    return ordered[idx]


async def exercise(
    client: httpx.AsyncClient,
    endpoint: Endpoint,
    request_count: int,
    latencies: dict[str, list[float]],
    statuses: dict[str, dict[str, int]],
    errors: dict[str, int],
) -> None:
    for _ in range(request_count):
        started = time.perf_counter()
        status_key = "exception"
        try:
            response = await client.get(endpoint.path)
            status_key = str(response.status_code)
        except httpx.HTTPError:
            errors[endpoint.name] = errors.get(endpoint.name, 0) + 1
        finally:
            latencies[endpoint.name].append((time.perf_counter() - started) * 1000.0)
            statuses[endpoint.name][status_key] = statuses[endpoint.name].get(status_key, 0) + 1


async def run_load(args: argparse.Namespace) -> dict[str, Any]:
    timeout = httpx.Timeout(args.timeout_seconds)
    limits = httpx.Limits(max_connections=max(200, args.concurrency * 10), max_keepalive_connections=max(100, args.concurrency * 5))

    latencies: dict[str, list[float]] = {endpoint.name: [] for endpoint in ENDPOINTS}
    statuses: dict[str, dict[str, int]] = {endpoint.name: {} for endpoint in ENDPOINTS}
    errors: dict[str, int] = {endpoint.name: 0 for endpoint in ENDPOINTS}

    started = time.perf_counter()
    async with httpx.AsyncClient(base_url=args.base_url, timeout=timeout, limits=limits) as client:
        tasks = []
        for endpoint in ENDPOINTS:
            for _ in range(args.concurrency):
                tasks.append(exercise(client, endpoint, args.requests_per_user, latencies, statuses, errors))
        await asyncio.gather(*tasks)
    duration_ms = (time.perf_counter() - started) * 1000.0

    endpoints_result = []
    total_requests = 0
    total_non_2xx = 0
    for endpoint in ENDPOINTS:
        samples = latencies[endpoint.name]
        requests = len(samples)
        total_requests += requests
        status_counts = statuses[endpoint.name]
        non_2xx = sum(count for code, count in status_counts.items() if not code.startswith("2"))
        total_non_2xx += non_2xx
        endpoints_result.append(
            {
                "endpoint": endpoint.name,
                "path": endpoint.path,
                "requests": requests,
                "non_2xx": non_2xx,
                "error_count": errors[endpoint.name],
                "status_counts": status_counts,
                "latency_ms": {
                    "avg": round(statistics.fmean(samples), 3) if samples else 0.0,
                    "p50": round(percentile(samples, 0.50), 3),
                    "p95": round(percentile(samples, 0.95), 3),
                    "p99": round(percentile(samples, 0.99), 3),
                    "min": round(min(samples), 3) if samples else 0.0,
                    "max": round(max(samples), 3) if samples else 0.0,
                },
            }
        )

    return {
        "timestamp_utc": datetime.now(tz=timezone.utc).isoformat(),
        "base_url": args.base_url,
        "concurrency": args.concurrency,
        "requests_per_user": args.requests_per_user,
        "duration_ms": round(duration_ms, 3),
        "total_requests": total_requests,
        "total_non_2xx": total_non_2xx,
        "error_rate": round((total_non_2xx / total_requests), 6) if total_requests else 0.0,
        "endpoints": endpoints_result,
    }


def main() -> int:
    args = parse_args()
    result = asyncio.run(run_load(args))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output_path), "total_requests": result["total_requests"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
