from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from time import monotonic

from pydantic import ValidationError

from shared.logging_config import configure_logging, get_logger
from shared.time_utils import format_utc, utc_now
from services.common.aq_ingestion import DirectAQIngestionProcessor

from services.openaq_poller.config import OpenAQPollerSettings
from services.openaq_poller.db import PollerDatabase, PollerDatabaseError
from services.openaq_poller.health_server import HealthState, start_health_server
from services.openaq_poller.models import PollRunResult, PollWindow, SensorRegistryRow
from services.openaq_poller.openaq_client import OpenAQClient, OpenAQClientError, OpenAQRateLimitError
from services.openaq_poller.publisher import build_raw_message, deduplicate_messages
from services.openaq_poller.window import compute_poll_window, status_from_counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Poll active OpenAQ station_sensors and publish observed readings to Kafka.")
    parser.add_argument("--once", action="store_true", help="Run one polling cycle and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and normalize without Kafka or pipeline_runs writes.")
    return parser.parse_args()


class OpenAQPoller:
    def __init__(self, settings: OpenAQPollerSettings, *, logger: object) -> None:
        self.settings = settings
        self.logger = logger
        self.database = PollerDatabase(settings.database_url)
        self.ingestion = DirectAQIngestionProcessor(settings.database_url, pipeline_component=settings.pipeline_component)

    def run_once(self, *, dry_run: bool) -> PollRunResult:
        started_at = utc_now()
        started_monotonic = monotonic()
        window: PollWindow | None = None
        result: PollRunResult

        try:
            sensors = self.database.fetch_active_sensors(max_sensors=self.settings.max_sensors)
            last_success = self.database.latest_success_window_end(self.settings.pipeline_component)
            window = compute_poll_window(
                now=utc_now(),
                last_success_at=last_success,
                overlap_minutes=self.settings.overlap_minutes,
                fallback_lookback_hours=self.settings.fallback_lookback_hours,
            )
            result = self._poll_sensors(
                sensors=sensors,
                window=window,
                dry_run=dry_run,
                started_at=started_at,
                started_monotonic=started_monotonic,
            )
        except (PollerDatabaseError, OpenAQClientError, ValidationError, ValueError) as exc:
            result = _failed_result(
                started_at=started_at,
                started_monotonic=started_monotonic,
                dry_run=dry_run,
                window=window,
                error_message=str(exc),
            )
            self._log("error", "openaq_poll_run_failed", error=str(exc), dry_run=dry_run)

        self._log(
            "info",
            "openaq_poll_run_completed",
            status=result.status,
            records_processed=result.records_processed,
            sensors_attempted=result.sensors_attempted,
            sensors_succeeded=result.sensors_succeeded,
            sensors_failed=result.sensors_failed,
            dry_run=dry_run,
        )
        return result

    def _poll_sensors(
        self,
        *,
        sensors: list[SensorRegistryRow],
        window: PollWindow,
        dry_run: bool,
        started_at: datetime,
        started_monotonic: float,
    ) -> PollRunResult:
        if dry_run and not self.settings.openaq_api_key:
            return _result(
                started_at=started_at,
                started_monotonic=started_monotonic,
                dry_run=dry_run,
                window=window,
                records_processed=0,
                sensors_attempted=len(sensors),
                sensors_succeeded=0,
                sensors_failed=0,
                metadata={
                    "api_key_present": False,
                    "api_calls_skipped": True,
                    "message": "dry run skipped OpenAQ calls because OPENAQ_API_KEY is not set",
                },
            )

        if not self.settings.openaq_api_key:
            raise OpenAQClientError("OPENAQ_API_KEY is required unless --dry-run is used")

        client = OpenAQClient(
            self.settings.openaq_api_key,
            timeout_seconds=self.settings.http_timeout_seconds,
            retries=self.settings.http_retries,
        )
        all_messages = []
        sensors_succeeded = 0
        sensors_failed = 0
        sensor_errors: list[dict[str, object]] = []

        try:
            for sensor in sensors:
                try:
                    measurements = client.fetch_sensor_measurements(
                        sensor.external_sensor_id,
                        datetime_from=window.datetime_from,
                        datetime_to=window.datetime_to,
                        limit=max(self.settings.measurements_limit, 1),
                        max_pages=max(self.settings.max_pages, 1),
                    )
                    messages = deduplicate_messages(
                        [
                            build_raw_message(sensor=sensor, measurement=measurement, now=window.datetime_to)
                            for measurement in measurements
                        ]
                    )
                    all_messages.extend(messages)
                    sensors_succeeded += 1
                except OpenAQRateLimitError as exc:
                    sensors_failed += 1
                    sensor_errors.append(_sensor_error(sensor, "rate_limited", str(exc)))
                    self._log("warning", "openaq_sensor_rate_limited", sensor_id=sensor.sensor_id, error=str(exc))
                except (OpenAQClientError, ValidationError, ValueError) as exc:
                    sensors_failed += 1
                    sensor_errors.append(_sensor_error(sensor, "failed", str(exc)))
                    self._log("warning", "openaq_sensor_poll_failed", sensor_id=sensor.sensor_id, error=str(exc))
        finally:
            client.close()

        ingestion_result = self.ingestion.ingest_messages(
            all_messages,
            dry_run=dry_run,
            metadata={
                "window_from": format_utc(window.datetime_from),
                "window_to": format_utc(window.datetime_to),
                "sensors_attempted": len(sensors),
                "sensors_succeeded": sensors_succeeded,
                "sensors_failed": sensors_failed,
                "rate_limit_hits": client.rate_limit_hits,
                "invalid_measurements": client.invalid_measurements,
            },
        )
        return _result(
            started_at=started_at,
            started_monotonic=started_monotonic,
            dry_run=dry_run,
            window=window,
            records_processed=ingestion_result.records_written if not dry_run else ingestion_result.records_processed,
            sensors_attempted=len(sensors),
            sensors_succeeded=sensors_succeeded,
            sensors_failed=sensors_failed,
            metadata={
                "api_key_present": True,
                "records_invalid": ingestion_result.records_invalid,
                "anomaly_count": ingestion_result.anomaly_count,
                "max_sensors": self.settings.max_sensors,
                "sensor_errors": sensor_errors[:10],
            },
        )

    def _log(self, level: str, event: str, **fields: object) -> None:
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(event, **fields)


def main() -> int:
    args = parse_args()
    settings = OpenAQPollerSettings.from_env()
    configure_logging(service_name=settings.service_name, log_format=settings.log_format)
    logger = get_logger(__name__)
    poller = OpenAQPoller(settings, logger=logger)

    if args.once:
        result = poller.run_once(dry_run=args.dry_run)
        return 0 if result.status in {"success", "partial"} else 1

    health_state = HealthState(settings.service_name)
    server = start_health_server(settings.health_host, settings.health_port, health_state, logger=logger)
    try:
        while True:
            result = poller.run_once(dry_run=args.dry_run)
            health_state.update(result)
            time.sleep(max(settings.poll_interval_seconds, 1))
    except KeyboardInterrupt:
        logger.info("openaq_poller_stopping")
        return 0
    finally:
        server.shutdown()


def _result(
    *,
    started_at: datetime,
    started_monotonic: float,
    dry_run: bool,
    window: PollWindow,
    records_processed: int,
    sensors_attempted: int,
    sensors_succeeded: int,
    sensors_failed: int,
    metadata: dict[str, object],
) -> PollRunResult:
    finished_at = utc_now()
    enriched_metadata = dict(metadata)
    enriched_metadata["window_from"] = format_utc(window.datetime_from)
    enriched_metadata["window_to"] = format_utc(window.datetime_to)
    return PollRunResult(
        status=status_from_counts(
            records_processed=records_processed,
            sensors_succeeded=sensors_succeeded,
            sensors_failed=sensors_failed,
        ),
        records_processed=records_processed,
        sensors_attempted=sensors_attempted,
        sensors_succeeded=sensors_succeeded,
        sensors_failed=sensors_failed,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=monotonic() - started_monotonic,
        dry_run=dry_run,
        window=window,
        metadata=enriched_metadata,
    )


def _failed_result(
    *,
    started_at: datetime,
    started_monotonic: float,
    dry_run: bool,
    window: PollWindow | None,
    error_message: str,
) -> PollRunResult:
    return PollRunResult(
        status="failed",
        records_processed=0,
        sensors_attempted=0,
        sensors_succeeded=0,
        sensors_failed=0,
        started_at=started_at,
        finished_at=utc_now(),
        duration_seconds=monotonic() - started_monotonic,
        dry_run=dry_run,
        window=window,
        error_message=error_message,
        metadata={"error_type": "poller_run_failure"},
    )


def _sensor_error(sensor: SensorRegistryRow, error_type: str, message: str) -> dict[str, object]:
    return {
        "sensor_id": sensor.sensor_id,
        "external_sensor_id": sensor.external_sensor_id,
        "pollutant": sensor.pollutant,
        "error_type": error_type,
        "message": message[:300],
    }


if __name__ == "__main__":
    sys.exit(main())
