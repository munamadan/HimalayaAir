from __future__ import annotations

from datetime import datetime, timedelta

from shared.time_utils import ensure_utc

from services.openaq_poller.models import PollWindow


def compute_poll_window(
    *,
    now: datetime,
    last_success_at: datetime | None,
    overlap_minutes: int,
    fallback_lookback_hours: int,
) -> PollWindow:
    window_to = ensure_utc(now)
    fallback_start = window_to - timedelta(hours=max(fallback_lookback_hours, 1))
    if last_success_at is None:
        return PollWindow(datetime_from=fallback_start, datetime_to=window_to)

    overlapped_start = ensure_utc(last_success_at) - timedelta(minutes=overlap_minutes)
    return PollWindow(datetime_from=max(overlapped_start, fallback_start), datetime_to=window_to)


def status_from_counts(*, records_processed: int, sensors_succeeded: int, sensors_failed: int) -> str:
    if sensors_failed == 0:
        return "success"
    if records_processed > 0 or sensors_succeeded > 0:
        return "partial"
    return "failed"

