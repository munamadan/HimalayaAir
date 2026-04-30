from __future__ import annotations

from datetime import UTC, datetime

from services.forecasting.accuracy import ForecastActualPair, build_accuracy_records


def test_accuracy_records_are_idempotent_by_unique_key():
    created_at = datetime(2026, 4, 30, 8, 0, tzinfo=UTC)
    pair = ForecastActualPair(
        station_id=1,
        pollutant="pm25",
        forecast_created_at=created_at,
        horizon_hours=1,
        predicted_aqi=90,
        actual_aqi=102.2,
    )

    records = build_accuracy_records([pair, pair])

    assert len(records) == 1
    assert records[0].key == (1, "pm25", created_at, 1)
    assert records[0].mae == 12.2
    assert records[0].rmse == 12.2


def test_accuracy_records_keep_distinct_horizons():
    created_at = datetime(2026, 4, 30, 8, 0, tzinfo=UTC)
    records = build_accuracy_records(
        [
            ForecastActualPair(1, "pm25", created_at, 1, 90, 100),
            ForecastActualPair(1, "pm25", created_at, 2, 90, 110),
        ]
    )

    assert len(records) == 2
    assert [record.horizon_hours for record in records] == [1, 2]

