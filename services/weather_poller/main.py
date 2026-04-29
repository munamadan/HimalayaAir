from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from time import monotonic

from pydantic import ValidationError

from shared.kafka.client import KafkaPublishError
from shared.logging_config import configure_logging, get_logger
from shared.time_utils import ensure_utc, utc_now

from services.weather_poller.config import WeatherPollerSettings
from services.weather_poller.db import WeatherPollerDatabase, WeatherPollerDatabaseError
from services.weather_poller.health_server import HealthState, start_health_server
from services.weather_poller.models import ModeledAQReading, WeatherLocation, WeatherPollRunResult, WeatherReading
from services.weather_poller.openmeteo_client import (
    OpenMeteoClient,
    OpenMeteoClientError,
    OpenMeteoRateLimitError,
    normalize_modeled_aq_response,
    normalize_weather_response,
    quality_counts,
)
from services.weather_poller.publisher import WeatherReadingPublisher


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Poll Open-Meteo weather and modeled AQ fallback data.")
    parser.add_argument("--once", action="store_true", help="Run one polling cycle and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and normalize without DB or Kafka writes.")
    return parser.parse_args()


class WeatherPoller:
    def __init__(self, settings: WeatherPollerSettings, *, logger: object) -> None:
        self.settings = settings
        self.logger = logger
        self.database = WeatherPollerDatabase(settings.database_url)

    def run_once(self, *, dry_run: bool) -> WeatherPollRunResult:
        started_at = utc_now()
        started_monotonic = monotonic()
        try:
            locations = self.database.fetch_active_locations(max_locations=self.settings.max_locations)
            result = self._poll_locations(
                locations=locations,
                started_at=started_at,
                started_monotonic=started_monotonic,
                dry_run=dry_run,
            )
        except (WeatherPollerDatabaseError, OpenMeteoClientError, KafkaPublishError, ValidationError, ValueError) as exc:
            result = _failed_result(
                started_at=started_at,
                started_monotonic=started_monotonic,
                dry_run=dry_run,
                error_message=str(exc),
            )
            self._log("error", "weather_poll_run_failed", error=str(exc), dry_run=dry_run)

        if not dry_run:
            try:
                self.database.record_pipeline_run(self.settings.pipeline_component, result)
            except WeatherPollerDatabaseError as exc:
                self._log("error", "weather_pipeline_run_write_failed", error=str(exc))
                result = _failed_result(
                    started_at=started_at,
                    started_monotonic=started_monotonic,
                    dry_run=dry_run,
                    error_message=str(exc),
                )

        self._log(
            "info",
            "weather_poll_run_completed",
            status=result.status,
            records_processed=result.records_processed,
            locations_attempted=result.locations_attempted,
            locations_succeeded=result.locations_succeeded,
            locations_failed=result.locations_failed,
            weather_records=result.weather_records,
            modeled_aq_records=result.modeled_aq_records,
            dry_run=dry_run,
        )
        return result

    def _poll_locations(
        self,
        *,
        locations: list[WeatherLocation],
        started_at: datetime,
        started_monotonic: float,
        dry_run: bool,
    ) -> WeatherPollRunResult:
        client = OpenMeteoClient(
            timeout_seconds=self.settings.http_timeout_seconds,
            retries=self.settings.http_retries,
        )
        publisher = None
        if self.settings.publish_kafka and not dry_run:
            publisher = WeatherReadingPublisher(self.settings.kafka, logger=self.logger)

        weather_readings: list[WeatherReading] = []
        modeled_aq_readings: list[ModeledAQReading] = []
        component_errors: list[dict[str, object]] = []
        locations_succeeded = 0
        locations_failed = 0
        model_run_at = _model_run_at(started_at)

        try:
            for location in locations:
                location_succeeded = False
                if "weather" in self.settings.components:
                    try:
                        payload = client.fetch_weather(
                            location,
                            forecast_days=self.settings.weather_forecast_days,
                            past_days=self.settings.weather_past_days,
                        )
                        weather_readings.extend(normalize_weather_response(location, payload))
                        location_succeeded = True
                    except OpenMeteoRateLimitError as exc:
                        component_errors.append(_location_error(location, "weather", "rate_limited", str(exc)))
                        self._log("warning", "weather_location_rate_limited", location_id=location.location_id, error=str(exc))
                    except OpenMeteoClientError as exc:
                        component_errors.append(_location_error(location, "weather", "failed", str(exc)))
                        self._log("warning", "weather_location_poll_failed", location_id=location.location_id, error=str(exc))

                if "modeled_aq" in self.settings.components:
                    try:
                        payload = client.fetch_modeled_aq(
                            location,
                            forecast_days=self.settings.modeled_aq_forecast_days,
                            past_days=self.settings.modeled_aq_past_days,
                        )
                        modeled_aq_readings.extend(
                            normalize_modeled_aq_response(location, payload, model_run_at=model_run_at)
                        )
                        location_succeeded = True
                    except OpenMeteoRateLimitError as exc:
                        component_errors.append(_location_error(location, "modeled_aq", "rate_limited", str(exc)))
                        self._log("warning", "modeled_aq_location_rate_limited", location_id=location.location_id, error=str(exc))
                    except OpenMeteoClientError as exc:
                        component_errors.append(_location_error(location, "modeled_aq", "failed", str(exc)))
                        self._log("warning", "modeled_aq_location_poll_failed", location_id=location.location_id, error=str(exc))

                if location_succeeded:
                    locations_succeeded += 1
                else:
                    locations_failed += 1
        finally:
            client.close()

        weather_inserted = 0
        modeled_aq_inserted = 0
        if not dry_run:
            if "weather" in self.settings.components:
                weather_inserted = self.database.insert_weather_readings(weather_readings)
            if "modeled_aq" in self.settings.components:
                modeled_aq_inserted = self.database.insert_modeled_aq_readings(modeled_aq_readings)

        kafka_errors: list[str] = []
        weather_published = 0
        modeled_aq_published = 0
        if publisher is not None:
            try:
                weather_published = publisher.publish_weather(weather_readings)
                modeled_aq_published = publisher.publish_modeled_aq(modeled_aq_readings)
            except (KafkaPublishError, ValidationError) as exc:
                kafka_errors.append(str(exc))
                self._log("warning", "weather_kafka_publish_failed", error=str(exc))

        records_processed = len(weather_readings) + len(modeled_aq_readings) if dry_run else weather_inserted + modeled_aq_inserted
        return _result(
            started_at=started_at,
            started_monotonic=started_monotonic,
            dry_run=dry_run,
            records_processed=records_processed,
            locations_attempted=len(locations),
            locations_succeeded=locations_succeeded,
            locations_failed=locations_failed,
            weather_records=len(weather_readings),
            modeled_aq_records=len(modeled_aq_readings),
            component_errors=component_errors,
            kafka_errors=kafka_errors,
            metadata={
                "components": sorted(self.settings.components),
                "publish_kafka": self.settings.publish_kafka,
                "weather_inserted": weather_inserted,
                "modeled_aq_inserted": modeled_aq_inserted,
                "weather_published": weather_published,
                "modeled_aq_published": modeled_aq_published,
                "weather_quality_counts": quality_counts(weather_readings),
                "modeled_aq_quality_counts": quality_counts(modeled_aq_readings),
                "rate_limit_hits": client.rate_limit_hits,
                "invalid_payloads": client.invalid_payloads,
                "max_locations": self.settings.max_locations,
            },
        )

    def _log(self, level: str, event: str, **fields: object) -> None:
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(event, **fields)


def main() -> int:
    args = parse_args()
    settings = WeatherPollerSettings.from_env()
    configure_logging(service_name=settings.service_name, log_format=settings.log_format)
    logger = get_logger(__name__)
    poller = WeatherPoller(settings, logger=logger)

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
        logger.info("weather_poller_stopping")
        return 0
    finally:
        server.shutdown()


def _result(
    *,
    started_at: datetime,
    started_monotonic: float,
    dry_run: bool,
    records_processed: int,
    locations_attempted: int,
    locations_succeeded: int,
    locations_failed: int,
    weather_records: int,
    modeled_aq_records: int,
    component_errors: list[dict[str, object]],
    kafka_errors: list[str],
    metadata: dict[str, object],
) -> WeatherPollRunResult:
    finished_at = utc_now()
    enriched_metadata = dict(metadata)
    enriched_metadata["component_errors"] = component_errors[:10]
    enriched_metadata["kafka_errors"] = kafka_errors[:3]
    return WeatherPollRunResult(
        status=_status(
            locations_attempted=locations_attempted,
            locations_succeeded=locations_succeeded,
            locations_failed=locations_failed,
            component_error_count=len(component_errors),
            kafka_error_count=len(kafka_errors),
        ),
        records_processed=records_processed,
        locations_attempted=locations_attempted,
        locations_succeeded=locations_succeeded,
        locations_failed=locations_failed,
        weather_records=weather_records,
        modeled_aq_records=modeled_aq_records,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=monotonic() - started_monotonic,
        dry_run=dry_run,
        metadata=enriched_metadata,
    )


def _failed_result(
    *,
    started_at: datetime,
    started_monotonic: float,
    dry_run: bool,
    error_message: str,
) -> WeatherPollRunResult:
    return WeatherPollRunResult(
        status="failed",
        records_processed=0,
        locations_attempted=0,
        locations_succeeded=0,
        locations_failed=0,
        weather_records=0,
        modeled_aq_records=0,
        started_at=started_at,
        finished_at=utc_now(),
        duration_seconds=monotonic() - started_monotonic,
        dry_run=dry_run,
        error_message=error_message,
        metadata={"error_type": "poller_run_failure"},
    )


def _status(
    *,
    locations_attempted: int,
    locations_succeeded: int,
    locations_failed: int,
    component_error_count: int,
    kafka_error_count: int,
) -> str:
    if locations_attempted == 0:
        return "failed"
    if locations_succeeded == 0:
        return "failed"
    if locations_failed > 0 or component_error_count > 0 or kafka_error_count > 0:
        return "partial"
    return "success"


def _location_error(location: WeatherLocation, component: str, error_type: str, message: str) -> dict[str, object]:
    return {
        "location_id": location.location_id,
        "location_name": location.name,
        "component": component,
        "error_type": error_type,
        "message": message[:300],
    }


def _model_run_at(value: datetime) -> datetime:
    current = ensure_utc(value)
    return current.replace(minute=0, second=0, microsecond=0)


if __name__ == "__main__":
    sys.exit(main())
