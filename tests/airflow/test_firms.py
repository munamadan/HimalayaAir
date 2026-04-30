from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DAGS_DIR = ROOT / "airflow" / "dags"
if str(DAGS_DIR) not in sys.path:
    sys.path.insert(0, str(DAGS_DIR))

from himalayaair.firms import event_hash, parse_firms_csv


def test_parse_firms_csv_preserves_acquisition_fields_and_hash() -> None:
    csv_text = "\n".join(
        [
            "latitude,longitude,bright_ti4,acq_date,acq_time,satellite,instrument,confidence,frp",
            "27.717200,85.324000,332.1,2026-04-29,0342,N,VIIRS,n,12.5",
            "27.717200,85.324000,332.1,2026-04-29,0342,N,VIIRS,n,12.5",
        ]
    )

    events = parse_firms_csv(csv_text, source="VIIRS_SNPP_NRT")

    assert len(events) == 2
    assert events[0].latitude == 27.7172
    assert events[0].longitude == 85.324
    assert events[0].acq_date == date(2026, 4, 29)
    assert events[0].acq_time == 342
    assert events[0].satellite == "N"
    assert events[0].instrument == "VIIRS"
    assert events[0].confidence == "n"
    assert events[0].brightness == 332.1
    assert events[0].frp == 12.5
    assert events[0].event_hash == events[1].event_hash


def test_event_hash_uses_normalized_acquisition_identity() -> None:
    first = event_hash(
        latitude=27.7172,
        longitude=85.324,
        acq_date=date(2026, 4, 29),
        acq_time=342,
        satellite="N",
        instrument="VIIRS",
    )
    second = event_hash(
        latitude=27.7172001,
        longitude=85.3240001,
        acq_date=date(2026, 4, 29),
        acq_time=342,
        satellite="N",
        instrument="VIIRS",
    )

    assert first == second
