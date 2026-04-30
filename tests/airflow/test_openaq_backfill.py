from __future__ import annotations

import gzip
import sys
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DAGS_DIR = ROOT / "airflow" / "dags"
if str(DAGS_DIR) not in sys.path:
    sys.path.insert(0, str(DAGS_DIR))

from himalayaair.models import StationSensorTarget
from himalayaair.openaq_backfill import archive_path, observed_provenance, parse_archive_records


def test_archive_path_uses_location_day_partition() -> None:
    assert (
        archive_path(location_id="2178", day=date(2026, 4, 29))
        == "/records/csv.gz/locationid=2178/year=2026/month=04/location-2178-20260429.csv.gz"
    )


def test_parse_archive_records_preserves_observed_archive_provenance() -> None:
    csv_text = "\n".join(
        [
            "datetime,location_id,sensors_id,parameter,units,value",
            "2026-04-29T07:00:00Z,100,21001,pm2.5,ug/m3,42.5",
            "2026-04-29T07:00:00Z,100,99999,pm2.5,ug/m3,99.9",
        ]
    )
    target = StationSensorTarget(
        sensor_id=10,
        station_id=1,
        external_sensor_id="21001",
        external_location_id="100",
        pollutant="pm25",
        unit="ug/m3",
        station_name="Kathmandu Station",
        latitude=27.7,
        longitude=85.3,
    )

    parsed = parse_archive_records(gzip.compress(csv_text.encode("utf-8")), targets=[target], source="openaq_archive")

    readings = parsed["21001"]
    assert len(readings) == 1
    assert readings[0].sensor_id == 10
    assert readings[0].station_id == 1
    assert readings[0].pollutant == "pm25"
    assert readings[0].source == "openaq_archive"
    assert readings[0].observation_type == "observed"
    assert readings[0].coverage_mode in {"LIVE_OBSERVED", "RECENT_OBSERVED"}
    assert readings[0].aqi is not None


def test_observed_provenance_marks_stale_data_recent_not_live() -> None:
    coverage_mode, confidence = observed_provenance(
        datetime(2026, 4, 29, 2, 0, tzinfo=UTC),
        now=datetime(2026, 4, 29, 8, 0, tzinfo=UTC),
    )

    assert coverage_mode == "RECENT_OBSERVED"
    assert confidence == "medium"
