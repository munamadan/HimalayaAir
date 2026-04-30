from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DAGS_DIR = ROOT / "airflow" / "dags"
if str(DAGS_DIR) not in sys.path:
    sys.path.insert(0, str(DAGS_DIR))

from himalayaair.weather_backfill import month_windows_for_range


def test_month_windows_split_cross_month_range() -> None:
    windows = month_windows_for_range(date(2026, 1, 30), date(2026, 3, 2))

    assert [(window.start_date, window.end_date) for window in windows] == [
        (date(2026, 1, 30), date(2026, 1, 31)),
        (date(2026, 2, 1), date(2026, 2, 28)),
        (date(2026, 3, 1), date(2026, 3, 2)),
    ]
