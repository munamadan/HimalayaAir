from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from services.spark.jobs.aq_stream_processor import (
    BatchWriteResult,
    SparkAQDatabase,
    SparkProcessorDatabaseError,
    _processor_result,
    _status,
    build_processed_summary,
    transform_raw_payloads,
)
from shared.kafka.messages import RawAQReadingMessage
from shared.time_utils import utc_now


@dataclass(frozen=True)
class DirectIngestionResult:
    status: str
    records_received: int
    records_processed: int
    records_written: int
    records_skipped_duplicate: int
    records_invalid: int
    anomaly_count: int
    started_at: object
    finished_at: object
    duration_seconds: float
    metadata: dict[str, object]


class DirectAQIngestionProcessor:
    def __init__(self, database_url: str, *, pipeline_component: str) -> None:
        self.database = SparkAQDatabase(database_url)
        self.pipeline_component = pipeline_component

    def ingest_messages(
        self,
        messages: list[RawAQReadingMessage],
        *,
        dry_run: bool,
        metadata: dict[str, object] | None = None,
    ) -> DirectIngestionResult:
        started_at = utc_now()
        started_monotonic = monotonic()
        payloads = [message.model_dump(mode="json") for message in messages]
        kafka_keys = [message.message_key() for message in messages]

        station_ids = {message.station_id for message in messages if message.station_id is not None}
        district_lookup = self.database.load_district_lookup({int(station_id) for station_id in station_ids})
        baseline_lookup = self.database.load_baseline_lookup(messages)
        transform = transform_raw_payloads(
            payloads,
            batch_id=0,
            kafka_keys=kafka_keys,
            district_lookup=district_lookup,
            baseline_lookup=baseline_lookup,
        )

        if dry_run:
            records_written = 0
            records_skipped_duplicate = 0
        else:
            write_result = self.database.write_batch(transform.readings)
            records_written = write_result.records_written
            records_skipped_duplicate = write_result.records_skipped_duplicate

        write_result = BatchWriteResult(
            records_written=records_written,
            records_skipped_duplicate=records_skipped_duplicate,
        )
        summary = build_processed_summary(transform, write_result=write_result)

        result = _processor_result(
            batch_id=0,
            transform=transform,
            write_result=write_result,
            started_at=started_at,
            started_monotonic=started_monotonic,
            dry_run=dry_run,
            metadata={
                "ingestion_mode": "direct_db",
                "summary": summary.model_dump(mode="json"),
                **(metadata or {}),
            },
        )

        if not dry_run:
            self.database.record_pipeline_run(self.pipeline_component, result)

        return DirectIngestionResult(
            status=_status(transform),
            records_received=result.records_received,
            records_processed=result.records_processed,
            records_written=result.records_written,
            records_skipped_duplicate=result.records_skipped_duplicate,
            records_invalid=result.records_invalid,
            anomaly_count=result.anomaly_count,
            started_at=result.started_at,
            finished_at=result.finished_at,
            duration_seconds=result.duration_seconds,
            metadata=result.metadata,
        )


__all__ = ["DirectAQIngestionProcessor", "DirectIngestionResult", "SparkProcessorDatabaseError"]
