#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
import uuid
from time import monotonic
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.kafka.client import KafkaConsumeError, KafkaPublishError, consume_message, create_consumer, create_producer, produce_message
from shared.kafka.messages import RawAQReadingMessage, load_message_fixture, message_from_json
from shared.logging_config import configure_logging, get_logger
from shared.settings import KafkaSettings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish and consume a fixture Kafka AQ message.")
    parser.add_argument("--fixture", help="Path to a raw AQ message JSON fixture.")
    parser.add_argument("--bootstrap-server", help="Kafka bootstrap server. Defaults to KAFKA_BOOTSTRAP_SERVERS or localhost:29092.")
    parser.add_argument("--topic", help="Topic to verify. Defaults to raw-aq-readings.")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--max-messages", type=int, default=10, help="When no fixture is provided, consume and validate up to this many messages.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(service_name="verify-kafka", log_format="console")
    logger = get_logger(__name__)

    settings = KafkaSettings.from_env(service_name="verify-kafka")
    if args.bootstrap_server:
        settings = KafkaSettings(
            bootstrap_servers=args.bootstrap_server,
            client_id=settings.client_id,
            group_id=settings.group_id,
            request_timeout_ms=settings.request_timeout_ms,
            delivery_timeout_ms=settings.delivery_timeout_ms,
            consumer_poll_timeout_seconds=settings.consumer_poll_timeout_seconds,
            topics=settings.topics,
        )

    topic = args.topic or settings.topics.raw_aq_readings
    group_id = f"verify-kafka-{uuid.uuid4()}"

    if not args.fixture:
        return consume_existing_messages(
            settings=settings,
            topic=topic,
            group_id=group_id,
            timeout_seconds=args.timeout_seconds,
            max_messages=args.max_messages,
            logger=logger,
        )

    fixture_path = Path(args.fixture)
    if not fixture_path.exists():
        logger.error("fixture_missing", fixture=str(fixture_path))
        return 2

    fixture_message = load_message_fixture(str(fixture_path))
    key = fixture_message.message_key()

    producer = create_producer(settings)
    consumer = create_consumer(settings, group_id=group_id, topics=[topic])

    try:
        produce_message(
            producer,
            topic=topic,
            key=key,
            message=fixture_message,
            timeout_seconds=args.timeout_seconds,
            logger=logger,
        )
        consumed_message = consume_message(
            consumer,
            model_type=RawAQReadingMessage,
            expected_key=key,
            timeout_seconds=args.timeout_seconds,
            logger=logger,
        )
    except (KafkaPublishError, KafkaConsumeError) as exc:
        logger.error("kafka_verification_failed", error=str(exc), topic=topic)
        return 1
    finally:
        consumer.close()

    if consumed_message.model_dump(mode="json") != fixture_message.model_dump(mode="json"):
        logger.error("kafka_round_trip_mismatch", topic=topic, key=key)
        return 1

    logger.info(
        "kafka_verification_passed",
        bootstrap_servers=settings.bootstrap_servers,
        topic=topic,
        key=key,
        source=fixture_message.source,
        observation_type=fixture_message.observation_type,
    )
    return 0


def consume_existing_messages(
    *,
    settings: KafkaSettings,
    topic: str,
    group_id: str,
    timeout_seconds: float,
    max_messages: int,
    logger: object,
) -> int:
    consumer = create_consumer(settings, group_id=group_id, topics=[topic])
    deadline = monotonic() + timeout_seconds
    consumed = 0
    try:
        while consumed < max(max_messages, 1) and monotonic() < deadline:
            record = consumer.poll(1.0)
            if record is None:
                continue
            if record.error():
                logger.warning("kafka_consume_poll_error", error=str(record.error()), topic=topic)
                continue
            try:
                message = message_from_json(RawAQReadingMessage, record.value())
            except ValidationError as exc:
                logger.error("kafka_message_validation_failed", topic=topic, error=str(exc))
                return 1
            consumed += 1
            logger.info(
                "kafka_existing_message_valid",
                topic=topic,
                key=record.key().decode("utf-8") if record.key() else None,
                source=message.source,
                observation_type=message.observation_type,
            )
    finally:
        consumer.close()

    logger.info("kafka_existing_messages_checked", topic=topic, messages_checked=consumed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
