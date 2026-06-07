from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from shared.enums import Confidence, CoverageMode, ObservationType, SourceName
from shared.kafka.client import create_producer, produce_message
from shared.kafka.messages import RawAQReadingMessage
from shared.logging_config import configure_logging, get_logger
from shared.settings import KafkaSettings
from shared.time_utils import ensure_utc, utc_now
from services.common.aq_ingestion import DirectAQIngestionProcessor

ReplayPublishMode = Literal["kafka", "direct-db-fallback"]


@dataclass(frozen=True)
class ReplayOptions:
    fixture: str
    start: datetime | None
    end: datetime | None
    speed: float
    loop: bool
    dry_run: bool
    publish_mode: ReplayPublishMode
    rebase_to_now: bool


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
    parser.add_argument("--dry-run", action="store_true", help="Validate and schedule messages without Kafka or DB writes.")
    parser.add_argument(
        "--rebase-to-now",
        action="store_true",
        help="Shift replay timestamps so the first selected fixture record is current while preserving original_timestamp.",
    )
    parser.add_argument(
        "--publish-mode",
        choices=["kafka", "direct-db-fallback"],
        default="kafka",
        help="Kafka publishes to raw-aq-readings. direct-db-fallback writes to TimescaleDB only for emergency demo recovery.",
    )
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
        publish_mode=args.publish_mode,
        rebase_to_now=bool(args.rebase_to_now),
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


def ingest_messages(
    options: ReplayOptions,
    messages: list[RawAQReadingMessage],
    *,
    database_url: str | None = None,
    kafka_settings: KafkaSettings | None = None,
) -> int:
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
            publish_mode=options.publish_mode,
            rebase_to_now=options.rebase_to_now,
        )
        return len(messages)

    if options.publish_mode == "direct-db-fallback":
        if database_url is None:
            raise ReplayConfigurationError("database_url is required for direct-db-fallback replay mode")
        return ingest_messages_direct_db_fallback(options, messages, database_url=database_url)

    settings = kafka_settings or KafkaSettings.from_env(service_name="replay-publisher")
    return publish_messages_to_kafka(options, messages, kafka_settings=settings)


def publish_messages_to_kafka(
    options: ReplayOptions,
    messages: list[RawAQReadingMessage],
    *,
    kafka_settings: KafkaSettings,
) -> int:
    logger = get_logger(__name__)
    producer = create_producer(kafka_settings)
    topic = kafka_settings.topics.raw_aq_readings
    published = 0
    replay_started_at = utc_now()
    logger.info(
        "replay_started",
        fixture=options.fixture,
        records=len(messages),
        replay_start=messages[0].timestamp.isoformat(),
        replay_end=messages[-1].timestamp.isoformat(),
        speed=options.speed,
        loop=options.loop,
        publish_mode=options.publish_mode,
        rebase_to_now=options.rebase_to_now,
        topic=topic,
    )

    iteration = 0
    while True:
        iteration += 1
        for replay_message in messages_for_replay_iteration(messages, rebase_to_now=options.rebase_to_now):
            produce_message(
                producer,
                topic=topic,
                key=replay_message.message_key(),
                message=replay_message,
                logger=logger,
            )
            published += 1
        logger.info("replay_loop_completed", published=published, loop=options.loop, iteration=iteration, topic=topic)
        if not options.loop:
            break

    logger.info(
        "replay_completed",
        published=published,
        duration_seconds=(utc_now() - replay_started_at).total_seconds(),
        publish_mode=options.publish_mode,
        topic=topic,
    )
    return published


def ingest_messages_direct_db_fallback(options: ReplayOptions, messages: list[RawAQReadingMessage], *, database_url: str) -> int:
    logger = get_logger(__name__)
    processor = DirectAQIngestionProcessor(database_url, pipeline_component="replay_publisher")

    published = 0
    replay_started_at = utc_now()
    logger.info(
        "replay_started",
        fixture=options.fixture,
        records=len(messages),
        replay_start=messages[0].timestamp.isoformat(),
        replay_end=messages[-1].timestamp.isoformat(),
        speed=options.speed,
        loop=options.loop,
        publish_mode=options.publish_mode,
        rebase_to_now=options.rebase_to_now,
    )

    iteration = 0
    while True:
        iteration += 1
        run_messages = messages_for_replay_iteration(messages, rebase_to_now=options.rebase_to_now)
        result = processor.ingest_messages(
            run_messages,
            dry_run=False,
            metadata={
                "fixture": options.fixture,
                "speed_multiplier": options.speed,
                "loop": options.loop,
                "iteration": iteration,
                "publish_mode": options.publish_mode,
                "rebase_to_now": options.rebase_to_now,
            },
        )
        published += result.records_written
        logger.info("replay_loop_completed", published=published, loop=options.loop, iteration=iteration)
        if not options.loop:
            break

    logger.info(
        "replay_completed",
        published=published,
        duration_seconds=(utc_now() - replay_started_at).total_seconds(),
        publish_mode=options.publish_mode,
    )
    return published


def messages_for_replay_iteration(messages: list[RawAQReadingMessage], *, rebase_to_now: bool) -> list[RawAQReadingMessage]:
    if not rebase_to_now:
        return [message.model_copy(update={"ingested_at": utc_now()}) for message in messages]

    base_timestamp = ensure_utc(messages[0].timestamp)
    replay_started_at = utc_now()
    rebased: list[RawAQReadingMessage] = []
    for message in messages:
        timestamp = ensure_utc(message.timestamp)
        rebased.append(
            message.model_copy(
                update={
                    "timestamp": replay_started_at + (timestamp - base_timestamp),
                    "ingested_at": utc_now(),
                    "original_timestamp": message.original_timestamp or timestamp,
                }
            )
        )
    return rebased


def main() -> int:
    options = parse_args()
    configure_logging(service_name="replay-publisher", log_format="json")
    logger = get_logger(__name__)

    messages = load_fixture(options.fixture)
    windowed = filter_window(messages, options.start, options.end)
    if not windowed:
        logger.warning("replay_window_empty", fixture=options.fixture, start=options.start, end=options.end)
        return 0

    database_url = None
    if options.publish_mode == "direct-db-fallback":
        from services.openaq_poller.config import _sync_database_url as sync_database_url

        database_url = sync_database_url()

    ingest_messages(options, windowed, database_url=database_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
