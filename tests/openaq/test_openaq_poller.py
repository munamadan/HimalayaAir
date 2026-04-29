from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx

from shared.enums import Confidence, CoverageMode, ObservationType, SourceName

from services.openaq_poller.models import OpenAQMeasurement, SensorRegistryRow
from services.openaq_poller.openaq_client import OpenAQClient
from services.openaq_poller.publisher import build_raw_message, deduplicate_messages
from services.openaq_poller.window import compute_poll_window, status_from_counts


def test_compute_poll_window_uses_last_success_overlap() -> None:
    now = datetime(2026, 4, 29, 8, 0, tzinfo=UTC)
    last_success = datetime(2026, 4, 29, 7, 30, tzinfo=UTC)

    window = compute_poll_window(
        now=now,
        last_success_at=last_success,
        overlap_minutes=10,
        fallback_lookback_hours=6,
    )

    assert window.datetime_from == datetime(2026, 4, 29, 7, 20, tzinfo=UTC)
    assert window.datetime_to == now


def test_compute_poll_window_bounds_old_success_by_fallback() -> None:
    now = datetime(2026, 4, 29, 8, 0, tzinfo=UTC)
    last_success = datetime(2026, 4, 28, 1, 0, tzinfo=UTC)

    window = compute_poll_window(
        now=now,
        last_success_at=last_success,
        overlap_minutes=10,
        fallback_lookback_hours=6,
    )

    assert window.datetime_from == datetime(2026, 4, 29, 2, 0, tzinfo=UTC)


def test_build_raw_message_preserves_observed_provenance() -> None:
    sensor = SensorRegistryRow(
        station_id=1,
        sensor_id=10,
        external_sensor_id=21001,
        external_location_id=11001,
        pollutant="pm25",
        unit="ug/m3",
        station_name="Kathmandu Station",
        latitude=27.7,
        longitude=85.3,
    )
    measurement = OpenAQMeasurement(
        openaq_sensor_id=21001,
        openaq_location_id=11001,
        pollutant="pm25",
        unit="ug/m3",
        value=42.5,
        timestamp=datetime(2026, 4, 29, 7, 30, tzinfo=UTC),
        has_flags=False,
    )

    message = build_raw_message(
        sensor=sensor,
        measurement=measurement,
        now=datetime(2026, 4, 29, 8, 0, tzinfo=UTC),
    )

    assert message.source == SourceName.OPENAQ_LIVE.value
    assert message.observation_type == ObservationType.OBSERVED.value
    assert message.coverage_mode == CoverageMode.LIVE_OBSERVED.value
    assert message.confidence == Confidence.HIGH.value
    assert message.station_id == 1
    assert message.sensor_id == 10
    assert message.openaq_sensor_id == 21001
    assert message.openaq_location_id == 11001
    assert message.message_key() == "1:10:pm25:2026-04-29T07:30:00+00:00"


def test_build_raw_message_marks_recent_observed_when_stale() -> None:
    sensor = _sensor()
    measurement = OpenAQMeasurement(
        openaq_sensor_id=21001,
        openaq_location_id=11001,
        pollutant="pm25",
        unit="ug/m3",
        value=35.0,
        timestamp=datetime(2026, 4, 29, 3, 0, tzinfo=UTC),
    )

    message = build_raw_message(
        sensor=sensor,
        measurement=measurement,
        now=datetime(2026, 4, 29, 8, 0, tzinfo=UTC),
    )

    assert message.coverage_mode == CoverageMode.RECENT_OBSERVED.value
    assert message.confidence == Confidence.MEDIUM.value


def test_deduplicate_messages_uses_kafka_message_key() -> None:
    sensor = _sensor()
    timestamp = datetime(2026, 4, 29, 7, 30, tzinfo=UTC)
    first = build_raw_message(
        sensor=sensor,
        measurement=OpenAQMeasurement(21001, 11001, "pm25", "ug/m3", 41.0, timestamp),
        now=timestamp + timedelta(minutes=1),
    )
    second = build_raw_message(
        sensor=sensor,
        measurement=OpenAQMeasurement(21001, 11001, "pm25", "ug/m3", 43.0, timestamp),
        now=timestamp + timedelta(minutes=1),
    )

    assert deduplicate_messages([first, second]) == [second]


def test_openaq_client_retries_429_with_retry_after() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(
            200,
            json={
                "meta": {"found": 1},
                "results": [
                    {
                        "value": 18.2,
                        "parameter": {"name": "pm2.5", "units": "ug/m3"},
                        "period": {"datetimeFrom": {"utc": "2026-04-29T07:00:00Z"}},
                        "coordinates": {"latitude": 27.7, "longitude": 85.3},
                        "sensorsId": 21001,
                        "locationsId": 11001,
                    }
                ],
            },
        )

    client = OpenAQClient(
        "test-key",
        timeout_seconds=1,
        retries=1,
        client=httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.openaq.org"),
    )

    measurements = client.fetch_sensor_measurements(
        21001,
        datetime_from=datetime(2026, 4, 29, 6, 0, tzinfo=UTC),
        datetime_to=datetime(2026, 4, 29, 8, 0, tzinfo=UTC),
        limit=100,
        max_pages=1,
    )

    assert calls == 2
    assert client.rate_limit_hits == 1
    assert measurements[0].pollutant == "pm25"
    assert measurements[0].timestamp == datetime(2026, 4, 29, 7, 0, tzinfo=UTC)


def test_status_from_counts_maps_partial_and_failed_runs() -> None:
    assert status_from_counts(records_processed=3, sensors_succeeded=1, sensors_failed=0) == "success"
    assert status_from_counts(records_processed=3, sensors_succeeded=1, sensors_failed=1) == "partial"
    assert status_from_counts(records_processed=0, sensors_succeeded=0, sensors_failed=2) == "failed"


def _sensor() -> SensorRegistryRow:
    return SensorRegistryRow(
        station_id=1,
        sensor_id=10,
        external_sensor_id=21001,
        external_location_id=11001,
        pollutant="pm25",
        unit="ug/m3",
        station_name="Kathmandu Station",
        latitude=27.7,
        longitude=85.3,
    )

