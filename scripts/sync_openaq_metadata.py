from __future__ import annotations

import argparse
import sys

try:
    from scripts.source_validation import (
        KathmanduBoundingBox,
        OpenAQClient,
        SourceValidationError,
        build_metadata_report,
        load_json_file,
        normalize_openaq_locations,
        openaq_api_key_from_env,
        write_json_report,
    )
except ModuleNotFoundError:
    from source_validation import (
        KathmanduBoundingBox,
        OpenAQClient,
        SourceValidationError,
        build_metadata_report,
        load_json_file,
        normalize_openaq_locations,
        openaq_api_key_from_env,
        write_json_report,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover OpenAQ Kathmandu locations and sensors without writing to a database.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and print normalized metadata. Phase 01 supports dry-run output only.",
    )
    parser.add_argument(
        "--bbox",
        default="85.20,27.55,85.50,27.80",
        help="OpenAQ bbox as min_lon,min_lat,max_lon,max_lat. Defaults to Kathmandu Valley bounds.",
    )
    parser.add_argument("--limit", type=int, default=100, help="OpenAQ page size.")
    parser.add_argument("--max-pages", type=int, default=5, help="Maximum OpenAQ pages to fetch.")
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout in seconds.")
    parser.add_argument("--retries", type=int, default=2, help="Retry count for retryable HTTP failures.")
    parser.add_argument(
        "--api-key-env",
        default="OPENAQ_API_KEY",
        help="Environment variable containing the server-side OpenAQ API key.",
    )
    parser.add_argument(
        "--fixture-location",
        help="Read an OpenAQ locations fixture instead of making a network call.",
    )
    parser.add_argument("--output", help="Write JSON report to this path instead of stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        bounds = KathmanduBoundingBox.from_csv(args.bbox)
        if not args.dry_run:
            raise SourceValidationError("Phase 01 only supports --dry-run metadata validation")

        if args.fixture_location:
            payload = load_json_file(args.fixture_location)
        else:
            client = OpenAQClient(
                openaq_api_key_from_env(args.api_key_env),
                timeout_seconds=args.timeout,
                retries=args.retries,
            )
            payload = client.discover_locations(bounds, limit=args.limit, max_pages=args.max_pages)

        normalization = normalize_openaq_locations(payload)
        report = build_metadata_report(normalization, bounds=bounds, dry_run=True)
        write_json_report(report, args.output)
        return 0
    except SourceValidationError as exc:
        sys.stderr.write(f"source validation failed: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
