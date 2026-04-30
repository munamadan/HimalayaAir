from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ForecastActualPair:
    station_id: int
    pollutant: str
    forecast_created_at: datetime
    horizon_hours: int
    predicted_aqi: int
    actual_aqi: float


@dataclass(frozen=True)
class ForecastAccuracyRecord:
    station_id: int
    pollutant: str
    forecast_created_at: datetime
    horizon_hours: int
    mae: float
    rmse: float

    @property
    def key(self) -> tuple[int, str, datetime, int]:
        return (self.station_id, self.pollutant, self.forecast_created_at, self.horizon_hours)


def build_accuracy_records(pairs: list[ForecastActualPair]) -> tuple[ForecastAccuracyRecord, ...]:
    records: dict[tuple[int, str, datetime, int], ForecastAccuracyRecord] = {}
    for pair in pairs:
        error = abs(float(pair.predicted_aqi) - float(pair.actual_aqi))
        record = ForecastAccuracyRecord(
            station_id=pair.station_id,
            pollutant=pair.pollutant,
            forecast_created_at=pair.forecast_created_at,
            horizon_hours=pair.horizon_hours,
            mae=round(error, 2),
            rmse=round(error, 2),
        )
        records[record.key] = record
    return tuple(records[key] for key in sorted(records))

