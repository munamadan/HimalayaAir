from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from shared.enums import CoverageMode, ObservationType, SourceName
from shared.kafka.messages import (
    DLQMessage,
    ModeledAQDataMessage,
    ProcessedAQBatchSummaryMessage,
    RawAQReadingMessage,
    message_from_json,
    message_to_json,
)
from shared.kafka.topics import TOPIC_DEFINITIONS


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def load_fixture() -> dict[str, object]:
    return json.loads((FIXTURES / "sample_raw_aq_message.json").read_text(encoding="utf-8"))


def test_raw_aq_message_validates_fixture_and_round_trips() -> None:
    message = RawAQReadingMessage.model_validate(load_fixture())

    assert message.source == SourceName.DEMO_REPLAY.value
    assert message.observation_type == ObservationType.REPLAY.value
    assert message.coverage_mode == CoverageMode.REPLAY_DEMO.value
    assert message.pollutant == "pm25"
    assert message.message_key() == "1:1:pm25:2026-04-28T06:00:00+00:00"

    decoded = message_from_json(RawAQReadingMessage, message_to_json(message))

    assert decoded == message


def test_raw_aq_message_rejects_missing_provenance() -> None:
    payload = load_fixture()
    del payload["source"]

    with pytest.raises(ValidationError):
        RawAQReadingMessage.model_validate(payload)


def test_raw_aq_message_requires_station_and_sensor_identity() -> None:
    payload = load_fixture()
    for field in ("sensor_id", "openaq_sensor_id", "station_id", "openaq_location_id"):
        del payload[field]

    with pytest.raises(ValidationError):
        RawAQReadingMessage.model_validate(payload)


def test_modeled_aq_message_requires_modeled_provenance() -> None:
    valid_payload = {
        "schema_version": "1.0",
        "source": "openmeteo_cams",
        "observation_type": "modeled",
        "coverage_mode": "MODELED_BASELINE",
        "model_location_id": 1,
        "location_name": "Kathmandu Center",
        "latitude": 27.7172,
        "longitude": 85.3240,
        "pollutant": "pm2_5",
        "value": 21.5,
        "unit": "ug/m3",
        "us_aqi": 68,
        "timestamp": "2026-04-28T06:00:00Z",
        "model_run_at": "2026-04-28T00:00:00Z",
    }

    message = ModeledAQDataMessage.model_validate(valid_payload)

    assert message.pollutant == "pm25"
    assert message.message_key() == "1:pm25:2026-04-28T06:00:00+00:00:2026-04-28T00:00:00+00:00"

    invalid_payload = valid_payload | {"observation_type": "observed"}
    with pytest.raises(ValidationError):
        ModeledAQDataMessage.model_validate(invalid_payload)


def test_dlq_message_preserves_failure_context_and_provenance() -> None:
    message = DLQMessage.model_validate(
        {
            "schema_version": "1.0",
            "source": "demo_replay",
            "observation_type": "replay",
            "original_topic": "raw-aq-readings",
            "original_key": "1:1:pm25:2026-04-28T06:00:00Z",
            "original_payload": {"bad": "payload"},
            "error_type": "ValidationError",
            "error_message": "source is required",
            "failed_at": "2026-04-28T06:00:10Z",
            "retry_count": 1,
        }
    )

    assert message.message_key() == "raw-aq-readings:1:1:pm25:2026-04-28T06:00:00Z:2026-04-28T06:00:10+00:00"


def test_processed_aq_batch_summary_preserves_station_provenance() -> None:
    message = ProcessedAQBatchSummaryMessage.model_validate(
        {
            "schema_version": "1.0",
            "batch_id": 42,
            "processed_at": "2026-04-28T06:00:10Z",
            "records_received": 2,
            "records_written": 1,
            "records_skipped_duplicate": 1,
            "records_invalid": 0,
            "anomaly_count": 0,
            "coverage_mode": "REPLAY_DEMO",
            "confidence": "demo",
            "stations": [
                {
                    "station_id": 1,
                    "station_name": "Ratnapark fixture station",
                    "aqi": 80,
                    "dominant_pollutant": "pm2.5",
                    "district_id": 1,
                    "district": "Kathmandu",
                    "is_anomaly": False,
                    "source": "demo_replay",
                    "observation_type": "replay",
                    "latitude": 27.7103,
                    "longitude": 85.315,
                    "timestamp": "2026-04-28T06:00:00Z",
                }
            ],
        }
    )

    assert message.message_key() == "42"
    assert message.stations[0].dominant_pollutant == "pm25"
    assert message.to_json_bytes().startswith(b"{")


def test_topic_definitions_include_phase_04_topics() -> None:
    names = {topic.name for topic in TOPIC_DEFINITIONS}

    assert {
        "raw-aq-readings",
        "weather-data",
        "modeled-aq-data",
        "processed-aq-readings",
        "raw-aq-readings-dlq",
    }.issubset(names)
