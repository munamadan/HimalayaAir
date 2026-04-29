from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from time import monotonic
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg2
from confluent_kafka import KafkaException, Producer
from psycopg2.extras import Json
from pydantic import ValidationError

from scripts.db_config import sync_database_url
from services.common.aqi_calculator import calculate_aqi, normalize_pollutant
from shared.enums import Confidence, CoverageMode, ObservationType, SourceName
from shared.kafka.client import create_producer
from shared.kafka.messages import (
    DLQMessage,
    ProcessedAQBatchSummaryMessage,
    ProcessedAQStationSummary,
    RawAQReadingMessage,
)
from shared.logging_config import configure_logging, get_logger
from shared.settings import KafkaSettings
from shared.time_utils import ensure_utc, utc_now


PHYSICAL_RANGE_MAX: dict[str, float] = {
    "pm25": 1000.0,
    "pm10": 2000.0,
    "co": 1000.0,
    "no2": 5000.0,
    "o3": 5000.0,
    "so2": 5000.0,
}


@dataclass(frozen=True)
class BaselineStats:
    count: int
    mean: float | None
    stddev: float | None


@dataclass(frozen=True)
class ProcessedAQReading:
    station_id: int
    sensor_id: int
    pollutant: str
    value: float
    unit: str
    aqi: int | None
    timestamp: object
    district_id: int | None
    is_anomaly: bool
    anomaly_reason: str | None
    quality_flag: str
    observation_type: str
    source: str
    coverage_mode: str
    confidence: str
    original_timestamp: object | None
    station_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class InvalidAQPayload:
    payload: object
    kafka_key: str | None
    error_type: str
    error_message: str


@dataclass(frozen=True)
class BatchTransformResult:
    batch_id: int
    records_received: int
    readings: list[ProcessedAQReading]
    invalid_records: list[InvalidAQPayload]
    anomaly_count: int
    coverage_mode: CoverageMode
    confidence: Confidence


@dataclass(frozen=True)
class BatchWriteResult:
    records_written: int
    records_skipped_duplicate: int


@dataclass(frozen=True)
class ProcessorRunResult:
    status: str
    batch_id: int
    records_received: int
    records_processed: int
    records_written: int
    records_skipped_duplicate: int
    records_invalid: int
    anomaly_count: int
    started_at: object
    finished_at: object
    duration_seconds: float
    dry_run: bool
    error_message: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SparkProcessorSettings:
    service_name: str
    log_format: str
    database_url: str
    kafka: KafkaSettings
    checkpoint_location: str
    starting_offsets: str
    max_offsets_per_trigger: int
    trigger_processing_time: str
    pipeline_component: str
    publish_kafka: bool

    @classmethod
    def from_env(cls) -> "SparkProcessorSettings":
        service_name = os.getenv("SERVICE_NAME", "spark-stream")
        return cls(
            service_name=service_name,
            log_format=os.getenv("LOG_FORMAT", "json"),
            database_url=sync_database_url(os.getenv("SYNC_DATABASE_URL")),
            kafka=KafkaSettings.from_env(service_name=service_name),
            checkpoint_location=os.getenv("SPARK_CHECKPOINT_LOCATION", "/tmp/spark-checkpoints/aq-stream"),
            starting_offsets=os.getenv("SPARK_STARTING_OFFSETS", "latest"),
            max_offsets_per_trigger=_int_env("SPARK_MAX_OFFSETS_PER_TRIGGER", 1000),
            trigger_processing_time=os.getenv("SPARK_TRIGGER_PROCESSING_TIME", "30 seconds"),
            pipeline_component=os.getenv("SPARK_PIPELINE_COMPONENT", "spark_aq_stream"),
            publish_kafka=_bool_env("SPARK_PUBLISH_KAFKA", True),
        )


class SparkProcessorDatabaseError(RuntimeError):
    pass


class SparkAQDatabase:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def load_district_lookup(self, station_ids: set[int]) -> dict[int, int | None]:
        if not station_ids:
            return {}
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            s.id AS station_id,
                            COALESCE(covered.id, nearest.id) AS district_id
                        FROM stations s
                        LEFT JOIN LATERAL (
                            SELECT d.id
                            FROM districts d
                            WHERE ST_Covers(d.boundary, s.location)
                            ORDER BY d.id
                            LIMIT 1
                        ) covered ON TRUE
                        LEFT JOIN LATERAL (
                            SELECT d.id
                            FROM districts d
                            ORDER BY d.boundary <-> s.location
                            LIMIT 1
                        ) nearest ON covered.id IS NULL
                        WHERE s.id = ANY(%s::int[])
                        """,
                        (list(station_ids),),
                    )
                    return {int(row[0]): int(row[1]) if row[1] is not None else None for row in cursor.fetchall()}
        except psycopg2.Error as exc:
            raise SparkProcessorDatabaseError(f"failed to assign districts for Spark batch: {exc}") from exc

    def load_baseline_lookup(self, readings: list[RawAQReadingMessage]) -> dict[tuple[int, str], BaselineStats]:
        keyed = {
            (message.station_id, normalize_pollutant(message.pollutant))
            for message in readings
            if message.station_id is not None
        }
        if not keyed:
            return {}

        station_ids = sorted({station_id for station_id, _pollutant in keyed})
        pollutants = sorted({pollutant for _station_id, pollutant in keyed})
        latest_timestamp = max(ensure_utc(message.timestamp) for message in readings)
        earliest_timestamp = latest_timestamp - timedelta(days=7)

        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            station_id,
                            pollutant,
                            COUNT(*)::int,
                            AVG(value)::float8,
                            STDDEV_POP(value)::float8
                        FROM aq_readings
                        WHERE station_id = ANY(%s::int[])
                          AND pollutant = ANY(%s::text[])
                          AND timestamp >= %s
                          AND timestamp < %s
                          AND is_anomaly = FALSE
                        GROUP BY station_id, pollutant
                        """,
                        (station_ids, pollutants, earliest_timestamp, latest_timestamp),
                    )
                    return {
                        (int(row[0]), str(row[1])): BaselineStats(
                            count=int(row[2]),
                            mean=float(row[3]) if row[3] is not None else None,
                            stddev=float(row[4]) if row[4] is not None else None,
                        )
                        for row in cursor.fetchall()
                    }
        except psycopg2.Error as exc:
            raise SparkProcessorDatabaseError(f"failed to load anomaly baselines for Spark batch: {exc}") from exc

    def write_batch(self, readings: list[ProcessedAQReading]) -> BatchWriteResult:
        if not readings:
            return BatchWriteResult(records_written=0, records_skipped_duplicate=0)
        written = 0
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    for reading in readings:
                        cursor.execute(
                            """
                            INSERT INTO aq_readings (
                                sensor_id,
                                station_id,
                                pollutant,
                                value,
                                unit,
                                aqi,
                                timestamp,
                                district_id,
                                is_anomaly,
                                anomaly_reason,
                                quality_flag,
                                observation_type,
                                source,
                                coverage_mode,
                                confidence,
                                original_timestamp
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (sensor_id, timestamp) DO NOTHING
                            """,
                            (
                                reading.sensor_id,
                                reading.station_id,
                                reading.pollutant,
                                reading.value,
                                reading.unit,
                                reading.aqi,
                                reading.timestamp,
                                reading.district_id,
                                reading.is_anomaly,
                                reading.anomaly_reason,
                                reading.quality_flag,
                                reading.observation_type,
                                reading.source,
                                reading.coverage_mode,
                                reading.confidence,
                                reading.original_timestamp,
                            ),
                        )
                        written += cursor.rowcount

                    for reading in readings:
                        cursor.execute(
                            """
                            UPDATE station_sensors
                            SET datetime_last = GREATEST(COALESCE(datetime_last, %s), %s),
                                updated_at = NOW()
                            WHERE id = %s
                            """,
                            (reading.timestamp, reading.timestamp, reading.sensor_id),
                        )
                        cursor.execute(
                            """
                            UPDATE stations
                            SET last_seen = GREATEST(COALESCE(last_seen, %s), %s),
                                updated_at = NOW()
                            WHERE id = %s
                            """,
                            (reading.timestamp, reading.timestamp, reading.station_id),
                        )
                conn.commit()
        except psycopg2.Error as exc:
            raise SparkProcessorDatabaseError(f"failed to write Spark AQ batch: {exc}") from exc

        return BatchWriteResult(
            records_written=written,
            records_skipped_duplicate=max(len(readings) - written, 0),
        )

    def record_pipeline_run(self, component: str, result: ProcessorRunResult) -> None:
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO pipeline_runs (
                            component,
                            run_at,
                            status,
                            records_processed,
                            error_message,
                            duration_seconds,
                            metadata
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            component,
                            result.finished_at,
                            result.status,
                            result.records_processed,
                            result.error_message,
                            round(result.duration_seconds, 2),
                            Json(result.metadata),
                        ),
                    )
                conn.commit()
        except psycopg2.Error as exc:
            raise SparkProcessorDatabaseError(f"failed to write Spark pipeline run: {exc}") from exc


class SparkAQPublisher:
    def __init__(self, settings: KafkaSettings, *, logger: object | None = None) -> None:
        self.settings = settings
        self.logger = logger
        self.producer: Producer = create_producer(settings)

    def publish_summary(self, summary: ProcessedAQBatchSummaryMessage) -> None:
        self._produce(
            topic=self.settings.topics.processed_aq_readings,
            key=summary.message_key(),
            value=summary.to_json_bytes(),
            event="processed_aq_summary_produced",
        )

    def publish_dlq(self, messages: list[DLQMessage]) -> int:
        published = 0
        for message in messages:
            self._produce(
                topic=self.settings.topics.raw_aq_readings_dlq,
                key=message.message_key(),
                value=message.to_json_bytes(),
                event="raw_aq_dlq_message_produced",
            )
            published += 1
        return published

    def _produce(self, *, topic: str, key: str, value: bytes, event: str) -> None:
        self.producer.produce(topic, key=key.encode("utf-8"), value=value)
        undelivered = self.producer.flush(15.0)
        if undelivered:
            raise KafkaException(f"Kafka flush timed out with {undelivered} undelivered message(s)")
        _log(self.logger, "info", event, topic=topic, key=key)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process raw AQ Kafka readings with Spark and persist TimescaleDB rows.")
    parser.add_argument("--fixture", help="Process a JSON fixture batch instead of starting Spark streaming.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and transform without DB or Kafka writes.")
    parser.add_argument("--batch-id", type=int, default=0, help="Batch id used for fixture runs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = SparkProcessorSettings.from_env()
    configure_logging(service_name=settings.service_name, log_format=settings.log_format)
    logger = get_logger(__name__)

    if args.fixture:
        result = process_fixture(Path(args.fixture), batch_id=args.batch_id, dry_run=args.dry_run, settings=settings, logger=logger)
        return 0 if result.status in {"success", "partial"} else 1

    run_stream(settings=settings, logger=logger)
    return 0


def process_fixture(
    path: Path,
    *,
    batch_id: int,
    dry_run: bool,
    settings: SparkProcessorSettings,
    logger: object,
) -> ProcessorRunResult:
    payloads = _load_fixture_payloads(path)
    if dry_run:
        started_at = utc_now()
        started_monotonic = monotonic()
        transform = transform_raw_payloads(payloads, batch_id=batch_id)
        dry_write_result = BatchWriteResult(records_written=0, records_skipped_duplicate=0)
        summary = build_processed_summary(transform, write_result=dry_write_result)
        result = _processor_result(
            batch_id=batch_id,
            transform=transform,
            write_result=dry_write_result,
            started_at=started_at,
            started_monotonic=started_monotonic,
            dry_run=True,
            metadata={"fixture": str(path), "summary": summary.model_dump(mode="json")},
        )
        logger.info(
            "spark_fixture_batch_transformed",
            batch_id=batch_id,
            records_received=result.records_received,
            records_processed=result.records_processed,
            records_invalid=result.records_invalid,
            anomaly_count=result.anomaly_count,
            dry_run=True,
        )
        return result

    database = SparkAQDatabase(settings.database_url)
    return process_payload_batch(
        payloads,
        kafka_keys=[None for _ in payloads],
        batch_id=batch_id,
        settings=settings,
        database=database,
        logger=logger,
    )


def transform_raw_payloads(
    payloads: list[object],
    *,
    batch_id: int,
    kafka_keys: list[str | None] | None = None,
    district_lookup: dict[int, int | None] | None = None,
    baseline_lookup: dict[tuple[int, str], BaselineStats] | None = None,
) -> BatchTransformResult:
    keys = kafka_keys or [None for _ in payloads]
    districts = district_lookup or {}
    baselines = baseline_lookup or {}
    readings: list[ProcessedAQReading] = []
    invalid_records: list[InvalidAQPayload] = []

    for payload, kafka_key in zip(payloads, keys, strict=False):
        try:
            message = RawAQReadingMessage.model_validate(payload)
            readings.append(_process_message(message, district_lookup=districts, baseline_lookup=baselines))
        except (ValidationError, ValueError, TypeError) as exc:
            invalid_records.append(
                InvalidAQPayload(
                    payload=payload,
                    kafka_key=kafka_key,
                    error_type=exc.__class__.__name__,
                    error_message=str(exc),
                )
            )

    return BatchTransformResult(
        batch_id=batch_id,
        records_received=len(payloads),
        readings=readings,
        invalid_records=invalid_records,
        anomaly_count=sum(1 for reading in readings if reading.is_anomaly),
        coverage_mode=_batch_coverage_mode(readings),
        confidence=_batch_confidence(readings),
    )


def process_payload_batch(
    payloads: list[object],
    *,
    kafka_keys: list[str | None],
    batch_id: int,
    settings: SparkProcessorSettings,
    database: SparkAQDatabase,
    logger: object,
) -> ProcessorRunResult:
    started_at = utc_now()
    started_monotonic = monotonic()
    parsed_messages = _valid_raw_messages(payloads, kafka_keys)
    try:
        station_ids = {int(message.station_id) for message in parsed_messages if message.station_id is not None}
        district_lookup = database.load_district_lookup(station_ids)
        baseline_lookup = database.load_baseline_lookup(parsed_messages)
        transform = transform_raw_payloads(
            payloads,
            batch_id=batch_id,
            kafka_keys=kafka_keys,
            district_lookup=district_lookup,
            baseline_lookup=baseline_lookup,
        )
        write_result = database.write_batch(transform.readings)
        summary = build_processed_summary(transform, write_result=write_result)
        dlq_messages = build_dlq_messages(transform)
        kafka_metadata = publish_notifications(
            transform=transform,
            summary=summary,
            dlq_messages=dlq_messages,
            settings=settings,
            logger=logger,
        )
        result = _processor_result(
            batch_id=batch_id,
            transform=transform,
            write_result=write_result,
            started_at=started_at,
            started_monotonic=started_monotonic,
            dry_run=False,
            metadata=kafka_metadata | {
                "coverage_mode": transform.coverage_mode.value,
                "confidence": transform.confidence.value,
                "district_assignments": sum(1 for reading in transform.readings if reading.district_id is not None),
            },
        )
    except Exception as exc:
        result = _failed_result(
            batch_id=batch_id,
            payload_count=len(payloads),
            started_at=started_at,
            started_monotonic=started_monotonic,
            error_message=str(exc),
        )
        logger.error("spark_batch_failed", batch_id=batch_id, error=str(exc))
        try:
            database.record_pipeline_run(settings.pipeline_component, result)
        except SparkProcessorDatabaseError as db_exc:
            logger.error("spark_pipeline_run_write_failed", batch_id=batch_id, error=str(db_exc))
        raise

    database.record_pipeline_run(settings.pipeline_component, result)
    logger.info(
        "spark_batch_complete",
        batch_id=batch_id,
        input_rows=result.records_received,
        written=result.records_written,
        duplicates=result.records_skipped_duplicate,
        invalid=result.records_invalid,
        anomalies=result.anomaly_count,
        duration_ms=round(result.duration_seconds * 1000, 2),
    )
    return result


def build_processed_summary(
    transform: BatchTransformResult,
    *,
    write_result: BatchWriteResult,
) -> ProcessedAQBatchSummaryMessage:
    latest_by_station: dict[int, ProcessedAQReading] = {}
    for reading in transform.readings:
        previous = latest_by_station.get(reading.station_id)
        if previous is None or ensure_utc(reading.timestamp) > ensure_utc(previous.timestamp):
            latest_by_station[reading.station_id] = reading

    stations = [
        ProcessedAQStationSummary(
            station_id=reading.station_id,
            station_name=reading.station_name,
            aqi=reading.aqi,
            dominant_pollutant=reading.pollutant,
            district_id=reading.district_id,
            district=None,
            is_anomaly=reading.is_anomaly,
            source=reading.source,
            observation_type=reading.observation_type,
            latitude=reading.latitude,
            longitude=reading.longitude,
            timestamp=reading.timestamp,
        )
        for reading in sorted(latest_by_station.values(), key=lambda item: item.station_id)
    ]
    return ProcessedAQBatchSummaryMessage(
        batch_id=transform.batch_id,
        records_received=transform.records_received,
        records_written=write_result.records_written,
        records_skipped_duplicate=write_result.records_skipped_duplicate,
        records_invalid=len(transform.invalid_records),
        anomaly_count=transform.anomaly_count,
        coverage_mode=transform.coverage_mode,
        confidence=transform.confidence,
        stations=stations,
    )


def build_dlq_messages(transform: BatchTransformResult) -> list[DLQMessage]:
    messages: list[DLQMessage] = []
    for invalid in transform.invalid_records:
        source = _enum_or_default(SourceName, _field_from_payload(invalid.payload, "source"), SourceName.MANUAL_SEED)
        observation_type = _enum_or_default(
            ObservationType,
            _field_from_payload(invalid.payload, "observation_type"),
            ObservationType.SYNTHETIC,
        )
        messages.append(
            DLQMessage(
                source=source,
                observation_type=observation_type,
                original_topic="raw-aq-readings",
                original_key=invalid.kafka_key,
                original_payload=invalid.payload if isinstance(invalid.payload, (dict, list, str)) else str(invalid.payload),
                error_type=invalid.error_type,
                error_message=invalid.error_message,
            )
        )
    return messages


def publish_notifications(
    *,
    transform: BatchTransformResult,
    summary: ProcessedAQBatchSummaryMessage,
    dlq_messages: list[DLQMessage],
    settings: SparkProcessorSettings,
    logger: object,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "processed_summary_published": False,
        "dlq_records_published": 0,
        "kafka_publish_errors": [],
    }
    if not settings.publish_kafka:
        metadata["kafka_publish_disabled"] = True
        return metadata

    try:
        publisher = SparkAQPublisher(settings.kafka, logger=logger)
        publisher.publish_summary(summary)
        metadata["processed_summary_published"] = True
        metadata["dlq_records_published"] = publisher.publish_dlq(dlq_messages)
    except (BufferError, KafkaException, ValidationError, ValueError) as exc:
        logger.warning("spark_notification_publish_failed", batch_id=transform.batch_id, error=str(exc))
        metadata["kafka_publish_errors"] = [str(exc)]
    return metadata


def run_stream(*, settings: SparkProcessorSettings, logger: object) -> None:
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.appName("himalayaair-aq-stream").master("local[2]").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    raw_stream = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", settings.kafka.bootstrap_servers)
        .option("subscribe", settings.kafka.topics.raw_aq_readings)
        .option("startingOffsets", settings.starting_offsets)
        .option("failOnDataLoss", "false")
    )
    if settings.max_offsets_per_trigger > 0:
        raw_stream = raw_stream.option("maxOffsetsPerTrigger", settings.max_offsets_per_trigger)

    values = raw_stream.load().selectExpr("CAST(key AS STRING) AS kafka_key", "CAST(value AS STRING) AS payload")
    database = SparkAQDatabase(settings.database_url)

    def foreach_batch(batch_df: object, batch_id: int) -> None:
        rows = batch_df.collect()
        payloads = [_json_payload(row["payload"]) for row in rows]
        kafka_keys = [row["kafka_key"] for row in rows]
        process_payload_batch(
            payloads,
            kafka_keys=kafka_keys,
            batch_id=batch_id,
            settings=settings,
            database=database,
            logger=logger,
        )

    query = (
        values.writeStream.foreachBatch(foreach_batch)
        .option("checkpointLocation", settings.checkpoint_location)
        .trigger(processingTime=settings.trigger_processing_time)
        .start()
    )
    logger.info(
        "spark_stream_started",
        raw_topic=settings.kafka.topics.raw_aq_readings,
        checkpoint_location=settings.checkpoint_location,
        starting_offsets=settings.starting_offsets,
    )
    query.awaitTermination()


def _process_message(
    message: RawAQReadingMessage,
    *,
    district_lookup: dict[int, int | None],
    baseline_lookup: dict[tuple[int, str], BaselineStats],
) -> ProcessedAQReading:
    if message.station_id is None:
        raise ValueError("internal station_id is required for Timescale persistence")
    if message.sensor_id is None:
        raise ValueError("internal sensor_id is required for Timescale persistence")

    pollutant = normalize_pollutant(message.pollutant)
    timestamp = ensure_utc(message.timestamp)
    original_timestamp = ensure_utc(message.original_timestamp) if message.original_timestamp else None
    coverage_mode, confidence = _reading_provenance(message)
    aqi = calculate_aqi(pollutant, message.value, message.unit)
    baseline = baseline_lookup.get((message.station_id, pollutant), BaselineStats(count=0, mean=None, stddev=None))
    is_anomaly, anomaly_reason, quality_flag = _anomaly_state(
        pollutant=pollutant,
        value=message.value,
        baseline=baseline,
        aqi=aqi,
        unit=message.unit,
    )

    return ProcessedAQReading(
        station_id=message.station_id,
        sensor_id=message.sensor_id,
        pollutant=pollutant,
        value=message.value,
        unit=_normalize_unit(message.unit),
        aqi=aqi,
        timestamp=timestamp,
        district_id=district_lookup.get(message.station_id),
        is_anomaly=is_anomaly,
        anomaly_reason=anomaly_reason,
        quality_flag=quality_flag,
        observation_type=str(message.observation_type),
        source=str(message.source),
        coverage_mode=coverage_mode.value,
        confidence=confidence.value,
        original_timestamp=original_timestamp,
        station_name=message.station_name,
        latitude=message.latitude,
        longitude=message.longitude,
    )


def _anomaly_state(
    *,
    pollutant: str,
    value: float,
    baseline: BaselineStats,
    aqi: int | None,
    unit: str,
) -> tuple[bool, str | None, str]:
    if _range_anomaly(pollutant, value):
        return True, "range", "range_anomaly"
    if pollutant == "pm25" and not _supported_pm25_unit(unit):
        return False, "unsupported_unit", "unsupported_unit"
    if pollutant == "pm25" and aqi is None:
        return False, "aqi_unavailable", "aqi_unavailable"
    if baseline.count < 24:
        return False, "insufficient_baseline", "insufficient_baseline"
    if baseline.stddev is None or baseline.stddev == 0:
        return False, "zero_stddev", "zero_stddev"
    if baseline.mean is None:
        return False, "insufficient_baseline", "insufficient_baseline"

    zscore = abs((value - baseline.mean) / baseline.stddev)
    if zscore > 3:
        return True, "zscore", "zscore_anomaly"
    return False, None, "processed"


def _range_anomaly(pollutant: str, value: float) -> bool:
    if not isinstance(value, int | float) or not value == value:
        return True
    maximum = PHYSICAL_RANGE_MAX.get(pollutant)
    if maximum is None:
        return value < 0
    return value < 0 or value > maximum


def _reading_provenance(message: RawAQReadingMessage) -> tuple[CoverageMode, Confidence]:
    if message.coverage_mode is not None and message.confidence is not None:
        return CoverageMode(str(message.coverage_mode)), Confidence(str(message.confidence))
    if message.observation_type == ObservationType.REPLAY.value:
        return CoverageMode.REPLAY_DEMO, Confidence.DEMO
    if message.observation_type == ObservationType.MODELED.value:
        return CoverageMode.MODELED_BASELINE, Confidence.LOW

    age = utc_now() - ensure_utc(message.timestamp)
    if age <= timedelta(hours=2):
        return CoverageMode.LIVE_OBSERVED, Confidence.HIGH
    return CoverageMode.RECENT_OBSERVED, Confidence.MEDIUM


def _batch_coverage_mode(readings: list[ProcessedAQReading]) -> CoverageMode:
    modes = [CoverageMode(reading.coverage_mode) for reading in readings]
    for mode in (
        CoverageMode.LIVE_OBSERVED,
        CoverageMode.RECENT_OBSERVED,
        CoverageMode.MODELED_BASELINE,
        CoverageMode.REPLAY_DEMO,
        CoverageMode.STATION_ONLY,
    ):
        if mode in modes:
            return mode
    return CoverageMode.NO_DATA


def _batch_confidence(readings: list[ProcessedAQReading]) -> Confidence:
    confidences = [Confidence(reading.confidence) for reading in readings]
    for confidence in (Confidence.HIGH, Confidence.MEDIUM, Confidence.LOW, Confidence.DEMO):
        if confidence in confidences:
            return confidence
    return Confidence.LOW


def _valid_raw_messages(payloads: list[object], kafka_keys: list[str | None]) -> list[RawAQReadingMessage]:
    messages: list[RawAQReadingMessage] = []
    for payload, _key in zip(payloads, kafka_keys, strict=False):
        try:
            messages.append(RawAQReadingMessage.model_validate(payload))
        except ValidationError:
            continue
    return messages


def _processor_result(
    *,
    batch_id: int,
    transform: BatchTransformResult,
    write_result: BatchWriteResult,
    started_at: object,
    started_monotonic: float,
    dry_run: bool,
    metadata: dict[str, object],
) -> ProcessorRunResult:
    finished_at = utc_now()
    return ProcessorRunResult(
        status=_status(transform),
        batch_id=batch_id,
        records_received=transform.records_received,
        records_processed=len(transform.readings),
        records_written=write_result.records_written,
        records_skipped_duplicate=write_result.records_skipped_duplicate,
        records_invalid=len(transform.invalid_records),
        anomaly_count=transform.anomaly_count,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=monotonic() - started_monotonic,
        dry_run=dry_run,
        metadata=metadata | {
            "dry_run": dry_run,
            "batch_id": batch_id,
            "records_received": transform.records_received,
            "records_invalid": len(transform.invalid_records),
            "records_skipped_duplicate": write_result.records_skipped_duplicate,
            "anomaly_count": transform.anomaly_count,
            "invalid_errors": [
                {"error_type": invalid.error_type, "error_message": invalid.error_message[:300]}
                for invalid in transform.invalid_records[:10]
            ],
        },
    )


def _failed_result(
    *,
    batch_id: int,
    payload_count: int,
    started_at: object,
    started_monotonic: float,
    error_message: str,
) -> ProcessorRunResult:
    finished_at = utc_now()
    return ProcessorRunResult(
        status="failed",
        batch_id=batch_id,
        records_received=payload_count,
        records_processed=0,
        records_written=0,
        records_skipped_duplicate=0,
        records_invalid=0,
        anomaly_count=0,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=monotonic() - started_monotonic,
        dry_run=False,
        error_message=error_message,
        metadata={"batch_id": batch_id, "dry_run": False},
    )


def _status(transform: BatchTransformResult) -> str:
    if transform.records_received == 0:
        return "success"
    if transform.readings and transform.invalid_records:
        return "partial"
    if transform.invalid_records and not transform.readings:
        return "failed"
    return "success"


def _load_fixture_payloads(path: Path) -> list[object]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return list(payload["records"])
    if isinstance(payload, list):
        return payload
    return [payload]


def _json_payload(value: str) -> object:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _field_from_payload(payload: object, field_name: str) -> object | None:
    if isinstance(payload, dict):
        return payload.get(field_name)
    return None


def _enum_or_default(enum_type: object, value: object, default: object) -> object:
    try:
        return enum_type(str(value)) if value is not None else default
    except ValueError:
        return default


def _normalize_unit(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "")
    if normalized in {"ug/m3", "ug/m^3", "ug/m³", "µg/m3", "µg/m^3", "µg/m³", "μg/m3", "μg/m^3", "μg/m³"}:
        return "ug/m3"
    return value.strip()


def _supported_pm25_unit(value: str) -> bool:
    return _normalize_unit(value) == "ug/m3"


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _log(logger: object | None, level: str, event: str, **fields: object) -> None:
    if logger is None:
        return
    log_method = getattr(logger, level, None)
    if callable(log_method):
        log_method(event, **fields)


if __name__ == "__main__":
    sys.exit(main())
