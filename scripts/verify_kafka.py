#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.kafka.client import KafkaConsumeError, KafkaPublishError, consume_message, create_consumer, create_producer, produce_message
from shared.kafka.messages import RawAQReadingMessage, load_message_fixture
from shared.logging_config import configure_logging, get_logger
from shared.settings import KafkaSettings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish and consume a fixture Kafka AQ message.")
    parser.add_argument("--fixture", required=True, help="Path to a raw AQ message JSON fixture.")
    parser.add_argument("--bootstrap-server", help="Kafka bootstrap server. Defaults to KAFKA_BOOTSTRAP_SERVERS or localhost:29092.")
    parser.add_argument("--topic", help="Topic to verify. Defaults to raw-aq-readings.")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(service_name="verify-kafka", log_format="console")
    logger = get_logger(__name__)

    fixture_path = Path(args.fixture)
    if not fixture_path.exists():
        logger.error("fixture_missing", fixture=str(fixture_path))
        return 2

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


if __name__ == "__main__":
    sys.exit(main())
