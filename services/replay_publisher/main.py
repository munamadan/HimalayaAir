from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from shared.enums import Confidence, CoverageMode, ObservationType, SourceName
from shared.kafka.client import KafkaPublishError, create_producer, produce_message
from shared.kafka.messages import RawAQReadingMessage
from shared.logging_config import configure_logging, get_logger
from shared.settings import AppSettings
from shared.time_utils import ensure_utc, utc_now


@dataclass(frozen=True)
class ReplayOptions:
    fixture: str
    start: datetime | None
    end: datetime | None
    speed: float
    loop: bool
    dry_run: bool


class ReplayConfigurationError(RuntimeError):
    pass


def parse_args() -> ReplayOptions:
    parser = argparse.ArgumentParser(
        description="Replay historical or fixture AQ readings into Kafka with replay provenance."
    )
    parser.add_argument("--fixture", required=True, help="Path to replay fixture JSON file.")
    parser.add_argument("--start", default=None, help="Replay window start (ISO-8601, UTC recommended).")
    parser.add_argument("--end", default=None, help="Replay window end (ISO-8601, UTC recommended).")
    parser.add_argument("--speed", type=float, default=30.0, help="Replay speed multiplier against original timestamp gaps.")
    parser.add_argument("--loop", action="store_true", help="Loop the replay fixture continuously.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and schedule messages without publishing to Kafka.")
    args = parser.parse_args()

    start = ensure_utc(datetime.fromisoformat(args.start)) if args.start else None
    end = ensure_utc(datetime.fromisoformat(args.end)) if args.end else None
    if args.speed <= 0:
        raise ReplayConfigurationError("--speed must be greater than zero")
    if start and end and start > end:
        raise ReplayConfigurationError("--start must be earlier than or equal to --end")

    return ReplayOptions(
        fixture=args.fixture,
        start=start,
        end=end,
        speed=float(args.speed),
        loop=bool(args.loop),
        dry_run=bool(args.dry_run),
    )


def load_fixture(path: str) -> list[RawAQReadingMessage]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    records = payload.get("records") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise ReplayConfigurationError("fixture JSON must be a list or an object with a records array")

    validated: list[RawAQReadingMessage] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ReplayConfigurationError(f"record {index} is not an object")
        normalized = dict(record)
        normalized["source"] = SourceName.DEMO_REPLAY.value
        normalized["observation_type"] = ObservationType.REPLAY.value
        normalized["coverage_mode"] = CoverageMode.REPLAY_DEMO.value
        normalized["confidence"] = Confidence.DEMO.value
        normalized.setdefault("quality_flag", "replay")
        normalized.setdefault("ingested_at", utc_now().isoformat())
        if "original_timestamp" not in normalized and "timestamp" in normalized:
            normalized["original_timestamp"] = normalized["timestamp"]

        try:
            validated.append(RawAQReadingMessage.model_validate(normalized))
        except ValidationError as exc:
            raise ReplayConfigurationError(f"record {index} failed validation: {exc}") from exc

    validated.sort(key=lambda message: ensure_utc(message.timestamp))
    return validated


def filter_window(messages: list[RawAQReadingMessage], start: datetime | None, end: datetime | None) -> list[RawAQReadingMessage]:
    selected: list[RawAQReadingMessage] = []
    for message in messages:
        timestamp = ensure_utc(message.timestamp)
        if start and timestamp < start:
            continue
        if end and timestamp > end:
            continue
        selected.append(message)
    return selected


def publish_messages(options: ReplayOptions, messages: list[RawAQReadingMessage]) -> int:
    logger = get_logger(__name__)
    if not messages:
        logger.warning("replay_no_messages_selected", fixture=options.fixture)
        return 0

    if options.dry_run:
        logger.info(
            "replay_dry_run",
            fixture=options.fixture,
            records=len(messages),
            start=messages[0].timestamp.isoformat(),
            end=messages[-1].timestamp.isoformat(),
            speed=options.speed,
            loop=options.loop,
        )
        return len(messages)

    settings = AppSettings.from_env(service_name="replay-publisher")
    producer = create_producer(settings.kafka)
    topic = settings.kafka.topics.raw_aq_readings

    published = 0
    replay_started_at = utc_now()
    logger.info(
        "replay_started",
        fixture=options.fixture,
        topic=topic,
        records=len(messages),
        replay_start=messages[0].timestamp.isoformat(),
        replay_end=messages[-1].timestamp.isoformat(),
        speed=options.speed,
        loop=options.loop,
    )

    while True:
        previous_timestamp: datetime | None = None
        for message in messages:
            current_timestamp = ensure_utc(message.timestamp)
            if previous_timestamp is not None:
                wait_seconds = max((current_timestamp - previous_timestamp).total_seconds() / options.speed, 0.0)
                if wait_seconds > 0:
                    time.sleep(wait_seconds)
            previous_timestamp = current_timestamp

            published_message = message.model_copy(update={"ingested_at": utc_now()})
            try:
                produce_message(
                    producer,
                    topic=topic,
                    key=published_message.message_key(),
                    message=published_message,
                    logger=logger,
                )
            except KafkaPublishError as exc:
                logger.error(
                    "replay_publish_failed",
                    topic=topic,
                    key=published_message.message_key(),
                    error=str(exc),
                )
                raise
            published += 1

        logger.info("replay_loop_completed", published=published, loop=options.loop)
        if not options.loop:
            break

    producer.flush(10.0)
    logger.info(
        "replay_completed",
        published=published,
        duration_seconds=(utc_now() - replay_started_at).total_seconds(),
    )
    return published


def main() -> int:
    options = parse_args()
    settings = AppSettings.from_env(service_name="replay-publisher")
    configure_logging(service_name=settings.service_name, log_format=settings.log_format)
    logger = get_logger(__name__)

    messages = load_fixture(options.fixture)
    windowed = filter_window(messages, options.start, options.end)
    if not windowed:
        logger.warning("replay_window_empty", fixture=options.fixture, start=options.start, end=options.end)
        return 0

    publish_messages(options, windowed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
