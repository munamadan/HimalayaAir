from __future__ import annotations

from datetime import UTC, datetime

from shared.enums import Confidence, CoverageMode, ObservationType, SourceName
from shared.kafka.messages import RawAQReadingMessage
from shared.kafka.topics import KafkaTopics
from shared.settings import KafkaSettings

from services.replay_publisher.main import ReplayOptions, ingest_messages


class _FakeProcessor:
    def __init__(self, *_args, **_kwargs):
        self.calls = []

    def ingest_messages(self, messages, *, dry_run, metadata):
        self.calls.append((messages, dry_run, metadata))
        return type("Result", (), {"records_written": len(messages)})()


def test_replay_publishes_to_kafka_by_default(monkeypatch) -> None:
    produced = []

    monkeypatch.setattr("services.replay_publisher.main.create_producer", lambda _settings: object())
    monkeypatch.setattr(
        "services.replay_publisher.main.produce_message",
        lambda _producer, *, topic, key, message, logger: produced.append((topic, key, message)),
    )
    options = ReplayOptions(
        fixture="x.json",
        start=None,
        end=None,
        speed=10.0,
        loop=False,
        dry_run=False,
        publish_mode="kafka",
    )
    messages = [_replay_message()]
    settings = KafkaSettings(
        bootstrap_servers="localhost:29092",
        client_id="test-replay",
        group_id="test-replay",
        request_timeout_ms=10_000,
        delivery_timeout_ms=30_000,
        consumer_poll_timeout_seconds=1.0,
        topics=KafkaTopics(raw_aq_readings="raw-aq-readings"),
    )

    written = ingest_messages(options, messages, kafka_settings=settings)

    assert written == 1
    assert len(produced) == 1
    assert produced[0][0] == "raw-aq-readings"
    assert produced[0][1] == messages[0].message_key()
    assert produced[0][2].source == SourceName.DEMO_REPLAY.value
    assert produced[0][2].observation_type == ObservationType.REPLAY.value


def test_replay_ingests_via_direct_processor_when_fallback_mode_is_explicit(monkeypatch) -> None:
    fake = _FakeProcessor()
    monkeypatch.setattr("services.replay_publisher.main.DirectAQIngestionProcessor", lambda *_a, **_k: fake)
    options = ReplayOptions(
        fixture="x.json",
        start=None,
        end=None,
        speed=10.0,
        loop=False,
        dry_run=False,
        publish_mode="direct-db-fallback",
    )
    messages = [_replay_message()]

    written = ingest_messages(options, messages, database_url="postgresql://unused")

    assert written == 1
    assert len(fake.calls) == 1
    assert fake.calls[0][1] is False


def _replay_message() -> RawAQReadingMessage:
    return RawAQReadingMessage(
        source=SourceName.DEMO_REPLAY.value,
        observation_type=ObservationType.REPLAY.value,
        station_id=1,
        sensor_id=10,
        pollutant="pm25",
        value=20.0,
        unit="ug/m3",
        timestamp=datetime(2026, 5, 1, 0, 0, tzinfo=UTC),
        coverage_mode=CoverageMode.REPLAY_DEMO.value,
        confidence=Confidence.DEMO.value,
    )
