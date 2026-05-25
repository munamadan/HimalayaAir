from __future__ import annotations

import json
from pathlib import Path

from shared.kafka.messages import RawAQReadingMessage

from services.common.aq_ingestion import DirectAQIngestionProcessor


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


class _FakeDatabase:
    def load_district_lookup(self, _station_ids):
        return {1: 10, 2: 20}

    def load_baseline_lookup(self, _messages):
        return {}

    def write_batch(self, readings):
        return type("WriteResult", (), {"records_written": len(readings), "records_skipped_duplicate": 0})()

    def record_pipeline_run(self, _component, _result):
        return None


def test_direct_ingestion_processor_matches_transform_behavior() -> None:
    payloads = json.loads((FIXTURES / "sample_raw_aq_batch.json").read_text(encoding="utf-8"))["records"]
    messages = [RawAQReadingMessage.model_validate(payload) for payload in payloads]

    processor = DirectAQIngestionProcessor("postgresql://unused", pipeline_component="test")
    processor.database = _FakeDatabase()
    result = processor.ingest_messages(messages, dry_run=False)

    assert result.records_received == 3
    assert result.records_processed == 3
    assert result.records_written == 3
    assert result.anomaly_count == 1
    assert result.status == "success"
