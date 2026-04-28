from __future__ import annotations

import argparse
import sys
from dataclasses import asdict

try:
    from scripts.source_validation import (
        KATHMANDU_CENTER,
        OpenMeteoAQClient,
        SourceValidationError,
        load_json_file,
        normalize_openmeteo_aq_response,
        parse_variables,
        write_json_report,
    )
except ModuleNotFoundError:
    from source_validation import (
        KATHMANDU_CENTER,
        OpenMeteoAQClient,
        SourceValidationError,
        load_json_file,
        normalize_openmeteo_aq_response,
        parse_variables,
        write_json_report,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Open-Meteo modeled air-quality availability for Kathmandu center.",
    )
    parser.add_argument("--latitude", type=float, default=KATHMANDU_CENTER["lat"], help="Latitude to validate.")
    parser.add_argument("--longitude", type=float, default=KATHMANDU_CENTER["lon"], help="Longitude to validate.")
    parser.add_argument(
        "--variables",
        help="Comma-separated Open-Meteo AQ hourly variables. Defaults to the approved modeled fallback set.",
    )
    parser.add_argument("--forecast-days", type=int, default=1, help="Forecast days to request.")
    parser.add_argument("--past-days", type=int, default=1, help="Past days to request.")
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout in seconds.")
    parser.add_argument("--retries", type=int, default=2, help="Retry count for retryable HTTP failures.")
    parser.add_argument("--fixture", help="Read an Open-Meteo AQ fixture instead of making a network call.")
    parser.add_argument("--output", help="Write JSON report to this path instead of stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        variables = parse_variables(args.variables)
        if args.fixture:
            payload = load_json_file(args.fixture)
        else:
            client = OpenMeteoAQClient(timeout_seconds=args.timeout, retries=args.retries)
            payload = client.fetch_air_quality(
                latitude=args.latitude,
                longitude=args.longitude,
                variables=variables,
                forecast_days=args.forecast_days,
                past_days=args.past_days,
            )
        availability = normalize_openmeteo_aq_response(payload, requested_variables=variables)
        report = {
            "latitude": args.latitude,
            "longitude": args.longitude,
            "result": asdict(availability),
        }
        write_json_report(report, args.output)
        return 0
    except SourceValidationError as exc:
        sys.stderr.write(f"source validation failed: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
