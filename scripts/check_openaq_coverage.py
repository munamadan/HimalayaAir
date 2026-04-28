from __future__ import annotations

import argparse
import sys

try:
    from scripts.source_validation import (
        KathmanduBoundingBox,
        OpenAQClient,
        SourceValidationError,
        build_coverage_report,
        load_json_file,
        normalize_openaq_locations,
        normalize_openaq_measurements,
        openaq_api_key_from_env,
        utc_window,
        write_json_report,
    )
except ModuleNotFoundError:
    from source_validation import (
        KathmanduBoundingBox,
        OpenAQClient,
        SourceValidationError,
        build_coverage_report,
        load_json_file,
        normalize_openaq_locations,
        normalize_openaq_measurements,
        openaq_api_key_from_env,
        utc_window,
        write_json_report,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure Kathmandu OpenAQ station and sensor freshness without writing to a database.",
    )
    parser.add_argument(
        "--bbox",
        default="85.20,27.55,85.50,27.80",
        help="OpenAQ bbox as min_lon,min_lat,max_lon,max_lat. Defaults to Kathmandu Valley bounds.",
    )
    parser.add_argument("--limit", type=int, default=100, help="OpenAQ locations page size.")
    parser.add_argument("--max-pages", type=int, default=5, help="Maximum OpenAQ location pages to fetch.")
    parser.add_argument(
        "--max-sensors",
        type=int,
        default=25,
        help="Maximum sensors to sample through /v3/sensors/{id}/measurements.",
    )
    parser.add_argument(
        "--measurement-limit",
        type=int,
        default=10,
        help="Maximum measurements fetched per sampled sensor.",
    )
    parser.add_argument("--window-hours", type=int, default=24, help="Measurement lookback window.")
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout in seconds.")
    parser.add_argument("--retries", type=int, default=2, help="Retry count for retryable HTTP failures.")
    parser.add_argument(
        "--api-key-env",
        default="OPENAQ_API_KEY",
        help="Environment variable containing the server-side OpenAQ API key.",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Use location and sensor datetimeLast metadata without polling measurement endpoints.",
    )
    parser.add_argument(
        "--modeled-available",
        action="store_true",
        help="Tell the recommendation logic that modeled AQ fallback has already been verified.",
    )
    parser.add_argument(
        "--fixture-location",
        help="Read an OpenAQ locations fixture instead of making a network call.",
    )
    parser.add_argument(
        "--fixture-measurement",
        action="append",
        default=[],
        help="Read an OpenAQ measurements fixture. Can be passed multiple times.",
    )
    parser.add_argument("--output", help="Write JSON report to this path instead of stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        bounds = KathmanduBoundingBox.from_csv(args.bbox)
        if args.fixture_location:
            location_payload = load_json_file(args.fixture_location)
            measurements = []
            for fixture_path in args.fixture_measurement:
                measurements.extend(normalize_openaq_measurements(load_json_file(fixture_path)))
            source = "fixture_measurements" if measurements else "fixture_metadata"
        else:
            client = OpenAQClient(
                openaq_api_key_from_env(args.api_key_env),
                timeout_seconds=args.timeout,
                retries=args.retries,
            )
            location_payload = client.discover_locations(bounds, limit=args.limit, max_pages=args.max_pages)
            measurements = []
            source = "openaq_metadata"

        normalization = normalize_openaq_locations(location_payload)

        if not args.fixture_location and not args.metadata_only:
            started_at, ended_at = utc_window(args.window_hours)
            client = OpenAQClient(
                openaq_api_key_from_env(args.api_key_env),
                timeout_seconds=args.timeout,
                retries=args.retries,
            )
            for sensor in normalization.sensors[: args.max_sensors]:
                payload = client.get_sensor_measurements(
                    sensor.openaq_sensor_id,
                    datetime_from=started_at,
                    datetime_to=ended_at,
                    limit=args.measurement_limit,
                )
                measurements.extend(
                    normalize_openaq_measurements(
                        payload,
                        sensor_id=sensor.openaq_sensor_id,
                        location_id=sensor.openaq_location_id,
                    )
                )
            source = "openaq_sensor_measurements"

        report = build_coverage_report(
            normalization,
            bounds=bounds,
            measurements=measurements if measurements else None,
            modeled_available=args.modeled_available,
            source=source,
        )
        write_json_report(report, args.output)
        return 0
    except SourceValidationError as exc:
        sys.stderr.write(f"source validation failed: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
