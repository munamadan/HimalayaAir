from __future__ import annotations

from datetime import UTC, datetime

from shared.enums import Confidence, CoverageMode, ObservationType, SourceName
from shared.kafka.messages import RawAQReadingMessage

from services.replay_publisher.main import ReplayOptions, ingest_messages


class _FakeProcessor:
    def __init__(self, *_args, **_kwargs):
        self.calls = []

    def ingest_messages(self, messages, *, dry_run, metadata):
        self.calls.append((messages, dry_run, metadata))
        return type("Result", (), {"records_written": len(messages)})()


def test_replay_ingests_via_direct_processor(monkeypatch) -> None:
    fake = _FakeProcessor()
    monkeypatch.setattr("services.replay_publisher.main.DirectAQIngestionProcessor", lambda *_a, **_k: fake)
    options = ReplayOptions(fixture="x.json", start=None, end=None, speed=10.0, loop=False, dry_run=False)
    messages = [
        RawAQReadingMessage(
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
    ]

    written = ingest_messages(options, messages, database_url="postgresql://unused")

    assert written == 1
    assert len(fake.calls) == 1
    assert fake.calls[0][1] is False
