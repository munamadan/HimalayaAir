# PHASE-07 Summary - Spark Stream Processing and Timescale Persistence

## What was built

- `services/common/aqi_calculator.py`: Pure Python PM2.5 AQI calculator with EPA 2024 PM2.5 breakpoints, truncation, category, color, and invalid input handling.
- `services/spark/jobs/aq_stream_processor.py`: Spark Structured Streaming processor with fixture dry-run support, raw Kafka JSON validation, AQI calculation, district enrichment, range and baseline anomaly flags, idempotent TimescaleDB writes, station freshness updates, `pipeline_runs` recording, DLQ message construction, and processed batch summary notifications.
- `services/spark/Dockerfile`: Spark 3.5.x Python runtime image for the stream processor.
- `docker-compose.yml`: Real `spark-stream` service using `spark-submit`, Kafka connector package, checkpoint volume, stream profile dependencies, and stream processor environment settings.
- `.env.example`: Non-secret Spark processor environment knobs.
- `shared/kafka/messages.py`: Processed AQ batch summary schemas with per-station provenance.
- `docs/kafka-message-contracts.md`: `processed-aq-readings` documented as a best-effort batch summary notification topic.
- `fixtures/sample_raw_aq_batch.json`: Replay-labeled batch fixture for dry-run verification.
- `tests/unit/test_aqi_calculator.py`: Focused AQI calculator tests.
- `tests/unit/test_kafka_messages.py`: Processed AQ summary schema tests.
- `tests/integration/test_spark_batch_fixture.py`: Batch transformation tests for AQI, baseline flags, z-score/range anomaly handling, DLQ messages, and summaries.

## Current system state

The stream profile now has a real Spark processor definition instead of a sleeping placeholder. The processor reads `raw-aq-readings`, transforms each Spark micro-batch through Python code, writes `aq_readings` with `ON CONFLICT DO NOTHING`, updates `station_sensors.datetime_last` and `stations.last_seen`, records `pipeline_runs`, sends malformed payloads to `raw-aq-readings-dlq`, and publishes `processed-aq-readings` batch summaries as best-effort notifications.

The fixture dry-run path is working without Spark, DB, or Kafka. The live Docker stream service did not start in this environment because the Docker build could not resolve PyPI while installing Python dependencies.

## Commands run

```bash
pytest tests/unit/test_aqi_calculator.py -q
# passed: 4 tests

python services/spark/jobs/aq_stream_processor.py --fixture fixtures/sample_raw_aq_batch.json --dry-run
# passed: transformed 3 replay-labeled records, 1 range anomaly, 0 invalid records

python -m py_compile services/common/aqi_calculator.py services/spark/jobs/aq_stream_processor.py shared/kafka/messages.py
# passed

pytest tests/unit/test_aqi_calculator.py tests/unit/test_kafka_messages.py tests/integration/test_spark_batch_fixture.py -q
# passed: 15 tests

pytest tests/unit tests/openaq tests/weather tests/integration -q
# passed: 33 tests

docker compose --profile stream config --quiet
# passed

docker compose --profile stream up -d spark-stream || true
# failed first in sandbox due blocked Docker socket access
# failed with approved Docker access because bitnami/spark:3.5.1 was unavailable
# after switching to spark:3.5.8-python3, failed during Docker build because pip could not resolve PyPI DNS
```

## Exit criteria verification

- [x] All in-scope tasks are complete or explicitly documented: Spark job, AQI calculator, transform tests, fixture dry-run, Compose wiring, checkpoint volume, Timescale write path, station freshness updates, processed summaries, DLQ construction, and `pipeline_runs` recording are implemented.
- [x] Relevant verification commands were run: Python tests and dry-run passed; Docker stream startup was run and the network-related build blocker is documented.
- [x] `CHANGELOG.md` was updated with the Phase 07 entry.
- [x] `docs/phase-summaries/PHASE-07-summary.md` was written.
- [x] No future-phase work was introduced: no FastAPI endpoints, WebSocket consumers, Airflow DAGs, forecasts, frontend views, replay service, IDW, or FIRMS work was added.
- [x] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced: fixtures are explicitly `demo_replay`, `replay`, `REPLAY_DEMO`, and `demo`; Kafka notification failures are logged and included in pipeline metadata.

## Problems encountered and resolutions

- Direct script execution initially failed with `ModuleNotFoundError: No module named 'scripts'` because Python did not add the repo root when running a nested script path. Added repo-root path setup inside `aq_stream_processor.py`.
- Docker daemon access was blocked by the sandbox. The required Docker command was rerun with approval.
- The earlier Bitnami Spark image tag was unavailable. Switched to the current official `spark:3.5.8-python3` image and aligned the Spark Kafka connector package to `3.5.8`.
- Docker image build could not install Python dependencies because the Docker build could not resolve PyPI DNS. The stream service definition is valid, but the container was not started in this environment.

## Deviations from the phase plan

- Added `ProcessedAQBatchSummaryMessage` while keeping the existing per-reading message class, because Phase 07 requires a batch summary notification and Phase 04 already had a per-reading schema.
- Used the official Spark Docker image instead of Bitnami because the pinned Bitnami tag was no longer available.
- Did not run a live TimescaleDB write with the fixture because the required verification command is dry-run and fixture station/sensor IDs are replay-only test IDs.

## Known issues and technical debt

- Severity: Medium. `spark-stream` did not start locally because Docker build dependency installation could not reach PyPI. Retry when Docker build DNS/network resolution is available, or prebuild/cache the Python dependency layer.
- Severity: Medium. District assignment is implemented but will return `NULL` until trusted district boundary rows are loaded into `districts`.
- Severity: Low. AQI calculation is authoritative for PM2.5 only, as planned. PM10, NO2, O3, CO, and SO2 are persisted as raw readings with `aqi=NULL` until pollutant-specific calculators are added in a later phase.
- Severity: Low. The fixture dry-run validates transform behavior but does not exercise a live Kafka-to-Timescale micro-batch because the container build was blocked.

## What the next phase needs to know

- `processed-aq-readings` is now a best-effort batch summary keyed by `batch_id`; TimescaleDB remains authoritative.
- The Spark job records visible Kafka publish failures in pipeline metadata and logs instead of treating notifications as the source of truth.
- `quality_flag='insufficient_baseline'` is expected early in the project because sparse local history usually has fewer than 24 prior records per station/pollutant.
- Use `docker compose --profile stream up -d spark-stream` again after dependency build networking is fixed.

## How to resume from scratch

```bash
docker compose --profile core --profile stream up -d
PATH="$HOME/.local/bin:$PATH" alembic upgrade head
./scripts/create_kafka_topics.sh
pytest tests/unit/test_aqi_calculator.py -q
python services/spark/jobs/aq_stream_processor.py --fixture fixtures/sample_raw_aq_batch.json --dry-run
docker compose --profile stream up -d spark-stream
```

## Next session prompt

```text
Follow AGENTS.md. Implement PHASE 08 only using docs/codex/phases/PHASE-08-airflow-backfills-quality.md.
```
