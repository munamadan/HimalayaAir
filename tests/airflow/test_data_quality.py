from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DAGS_DIR = ROOT / "airflow" / "dags"
if str(DAGS_DIR) not in sys.path:
    sys.path.insert(0, str(DAGS_DIR))

from himalayaair.database import classify_quality_state
from himalayaair.data_quality import QUALITY_PIPELINE_STATUS


def test_sparse_fresh_station_coverage_is_degraded_not_failed() -> None:
    state, coverage_mode, confidence, message = classify_quality_state(
        fresh_station_count=1,
        recent_station_count=4,
        modeled_available=False,
        invalid_value_count=0,
        anomaly_rate=0.0,
    )

    assert state == "degraded"
    assert coverage_mode == "RECENT_OBSERVED"
    assert confidence == "medium"
    assert QUALITY_PIPELINE_STATUS[state] == "partial"
    assert "fresh station coverage is sparse" in message


def test_no_recent_or_modeled_data_is_down() -> None:
    state, coverage_mode, confidence, _message = classify_quality_state(
        fresh_station_count=0,
        recent_station_count=0,
        modeled_available=False,
        invalid_value_count=0,
        anomaly_rate=None,
    )

    assert state == "down"
    assert coverage_mode == "NO_DATA"
    assert confidence == "low"
