from __future__ import annotations

import json
from pathlib import Path

from services.spark.jobs.aq_stream_processor import (
    BaselineStats,
    BatchWriteResult,
    build_dlq_messages,
    build_processed_summary,
    transform_raw_payloads,
)


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def test_transform_raw_payloads_calculates_aqi_and_flags_sparse_baseline() -> None:
    payloads = json.loads((FIXTURES / "sample_raw_aq_batch.json").read_text(encoding="utf-8"))["records"]

    result = transform_raw_payloads(
        payloads,
        batch_id=7,
        district_lookup={1: 10, 2: 20},
        baseline_lookup={},
    )

    assert result.records_received == 3
    assert len(result.readings) == 3
    assert result.invalid_records == []
    assert result.anomaly_count == 1
    assert result.readings[0].aqi == 80
    assert result.readings[0].quality_flag == "insufficient_baseline"
    assert result.readings[0].district_id == 10
    assert result.readings[1].aqi is None
    assert result.readings[1].quality_flag == "insufficient_baseline"
    assert result.readings[2].is_anomaly is True
    assert result.readings[2].anomaly_reason == "range"
    assert result.readings[2].quality_flag == "range_anomaly"


def test_transform_raw_payloads_flags_zscore_when_baseline_is_sufficient() -> None:
    payload = json.loads((FIXTURES / "sample_raw_aq_message.json").read_text(encoding="utf-8"))

    result = transform_raw_payloads(
        [payload | {"value": 32.0}],
        batch_id=8,
        baseline_lookup={(1, "pm25"): BaselineStats(count=30, mean=20.0, stddev=2.0)},
    )

    assert result.readings[0].is_anomaly is True
    assert result.readings[0].anomaly_reason == "zscore"
    assert result.readings[0].quality_flag == "zscore_anomaly"


def test_invalid_raw_payloads_build_dlq_messages() -> None:
    result = transform_raw_payloads(
        [{"schema_version": "1.0", "source": "demo_replay", "observation_type": "replay", "value": 1}],
        batch_id=9,
        kafka_keys=["bad-key"],
    )

    dlq_messages = build_dlq_messages(result)

    assert len(result.invalid_records) == 1
    assert len(dlq_messages) == 1
    assert dlq_messages[0].original_key == "bad-key"
    assert dlq_messages[0].source == "demo_replay"
    assert dlq_messages[0].observation_type == "replay"


def test_processed_summary_uses_latest_station_readings() -> None:
    payload = json.loads((FIXTURES / "sample_raw_aq_message.json").read_text(encoding="utf-8"))
    later_payload = payload | {
        "value": 35.4,
        "timestamp": "2026-04-28T07:00:00Z",
        "ingested_at": "2026-04-28T07:00:05Z",
    }
    result = transform_raw_payloads([payload, later_payload], batch_id=10)

    summary = build_processed_summary(
        result,
        write_result=BatchWriteResult(records_written=2, records_skipped_duplicate=0),
    )

    assert summary.batch_id == 10
    assert summary.records_written == 2
    assert len(summary.stations) == 1
    assert summary.stations[0].aqi == 100
    assert summary.stations[0].timestamp.isoformat() == "2026-04-28T07:00:00+00:00"
