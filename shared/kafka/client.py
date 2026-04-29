from __future__ import annotations

from threading import Event
from time import monotonic
from typing import TypeVar

from confluent_kafka import Consumer, KafkaException, Producer
from pydantic import ValidationError

from shared.kafka.messages import KafkaMessage, message_from_json
from shared.settings import KafkaSettings


MessageT = TypeVar("MessageT", bound=KafkaMessage)


class KafkaPublishError(RuntimeError):
    pass


class KafkaConsumeError(RuntimeError):
    pass


def create_producer(settings: KafkaSettings) -> Producer:
    return Producer(
        {
            "bootstrap.servers": settings.bootstrap_servers,
            "client.id": settings.client_id,
            "request.timeout.ms": settings.request_timeout_ms,
            "delivery.timeout.ms": settings.delivery_timeout_ms,
        }
    )


def create_consumer(settings: KafkaSettings, *, group_id: str, topics: list[str]) -> Consumer:
    consumer = Consumer(
        {
            "bootstrap.servers": settings.bootstrap_servers,
            "client.id": settings.client_id,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "session.timeout.ms": 10_000,
        }
    )
    consumer.subscribe(topics)
    return consumer


def produce_message(
    producer: Producer,
    *,
    topic: str,
    key: str,
    message: KafkaMessage,
    timeout_seconds: float = 15.0,
    logger: object | None = None,
) -> None:
    delivered = Event()
    errors: list[str] = []

    def on_delivery(error: object, record: object) -> None:
        if error is not None:
            errors.append(str(error))
        delivered.set()

    try:
        producer.produce(topic, key=key.encode("utf-8"), value=message.to_json_bytes(), on_delivery=on_delivery)
        producer.poll(0)
    except BufferError as exc:
        _log(logger, "error", "kafka_produce_buffer_full", topic=topic, key=key, error=str(exc))
        raise KafkaPublishError(f"Kafka producer buffer is full for topic={topic}") from exc
    except KafkaException as exc:
        _log(logger, "error", "kafka_produce_failed", topic=topic, key=key, error=str(exc))
        raise KafkaPublishError(f"Kafka produce failed for topic={topic}") from exc

    remaining = max(timeout_seconds, 0.1)
    undelivered = producer.flush(remaining)
    if undelivered:
        raise KafkaPublishError(f"Kafka flush timed out with {undelivered} undelivered message(s)")
    if not delivered.wait(0.1):
        raise KafkaPublishError("Kafka delivery callback did not complete")
    if errors:
        raise KafkaPublishError("; ".join(errors))
    _log(logger, "info", "kafka_message_produced", topic=topic, key=key)


def consume_message(
    consumer: Consumer,
    *,
    model_type: type[MessageT],
    expected_key: str | None = None,
    timeout_seconds: float = 30.0,
    logger: object | None = None,
) -> MessageT:
    deadline = monotonic() + timeout_seconds
    last_error: str | None = None

    while monotonic() < deadline:
        record = consumer.poll(1.0)
        if record is None:
            continue
        if record.error():
            last_error = str(record.error())
            _log(logger, "warning", "kafka_consume_poll_error", error=last_error)
            continue

        key = record.key().decode("utf-8") if record.key() else None
        if expected_key is not None and key != expected_key:
            continue

        try:
            message = message_from_json(model_type, record.value())
        except ValidationError as exc:
            raise KafkaConsumeError(f"Consumed message failed schema validation: {exc}") from exc

        _log(logger, "info", "kafka_message_consumed", topic=record.topic(), key=key)
        return message

    detail = f"; last Kafka error: {last_error}" if last_error else ""
    raise KafkaConsumeError(f"Timed out waiting for Kafka message{detail}")


def _log(logger: object | None, level: str, event: str, **fields: object) -> None:
    if logger is None:
        return
    log_method = getattr(logger, level, None)
    if callable(log_method):
        log_method(event, **fields)

