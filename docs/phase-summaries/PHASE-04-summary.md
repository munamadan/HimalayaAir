# PHASE-04 Summary - Kafka Topics and Shared Libraries

## What was built

- `requirements.txt`: Added Pydantic, structlog, and confluent-kafka.
- `shared/enums.py`: Added approved coverage mode, observation type, confidence, and source enums.
- `shared/settings.py`: Added environment-driven Kafka and app settings.
- `shared/logging_config.py`: Added central structlog configuration for services and scripts.
- `shared/time_utils.py`: Added UTC timestamp parse/format helpers.
- `shared/health.py`: Added a reusable health payload model.
- `shared/kafka/topics.py`: Added topic constants, retention settings, partition counts, and key documentation.
- `shared/kafka/messages.py`: Added Pydantic message schemas and serialization helpers for raw AQ, weather, modeled AQ, processed AQ, and DLQ messages.
- `shared/kafka/client.py`: Added bounded Kafka producer and consumer helper functions with visible error handling.
- `scripts/create_kafka_topics.sh`: Added `modeled-aq-data` and aligned Phase 04 topic retention settings.
- `scripts/verify_kafka.py`: Added fixture validation plus Kafka publish/consume round-trip verification.
- `fixtures/sample_raw_aq_message.json`: Added a replay-labeled raw AQ fixture.
- `tests/unit/test_kafka_messages.py`: Added schema, provenance, serialization, DLQ, modeled AQ, and topic tests.
- `docs/kafka-message-contracts.md`: Documented topic names, key formats, and provenance requirements.
- `CHANGELOG.md`: Recorded Phase 04 changes and verification.

## Current system state

The shared Python package now gives future services one source of truth for logging, settings, provenance enums, health payloads, Kafka topics, message schemas, serialization, and simple producer/consumer behavior.

Kafka now has the Phase 04 topic set available locally:

- `raw-aq-readings`
- `weather-data`
- `modeled-aq-data`
- `processed-aq-readings`
- `raw-aq-readings-dlq`
- `pipeline-events`

No live OpenAQ polling, Spark stream processing, Airflow DAGs, API endpoints, forecasting, frontend behavior, or database schema changes were introduced.

## Commands run

```bash
python -m pip install --user -r requirements.txt
# failed first: sandbox DNS/network access blocked
# passed with approved network escalation; installed structlog and confluent-kafka

python -m py_compile shared/*.py shared/kafka/*.py scripts/verify_kafka.py
# passed

pytest tests/unit -q
# passed: 11 tests

./scripts/create_kafka_topics.sh --dry-run
# passed; printed six topic creation commands

./scripts/create_kafka_topics.sh
# failed first: sandbox blocked Docker daemon access
# passed with approved Docker access; created modeled-aq-data and left existing topics unchanged

python scripts/verify_kafka.py --fixture fixtures/sample_raw_aq_message.json
# failed first: script path did not include repo root; fixed
# failed second: sandbox blocked localhost:29092 socket access
# passed with approved socket access; produced and consumed the replay fixture

pytest tests/unit -q
# passed again: 11 tests
```

## Exit criteria verification

- [x] All in-scope tasks are complete: shared settings, logging, time, health, source enums, message schemas, Kafka helpers, topic creation, verifier, docs, fixture, and tests were added.
- [x] Relevant verification commands were run: `./scripts/create_kafka_topics.sh`, `python scripts/verify_kafka.py --fixture fixtures/sample_raw_aq_message.json`, and `pytest tests/unit -q` passed after documented approvals/fixes.
- [x] `CHANGELOG.md` was updated with a Phase 04 entry.
- [x] `docs/phase-summaries/PHASE-04-summary.md` was written.
- [x] No future-phase work was introduced: there are no pollers, Spark jobs, Airflow DAGs, API endpoints, forecasts, or frontend changes.
- [x] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced: the Kafka fixture is explicitly `demo_replay`, `replay`, `REPLAY_DEMO`, and `demo`.

## Problems encountered and resolutions

- The environment was missing `structlog` and `confluent-kafka`. Added them to `requirements.txt`; the first install failed under sandbox DNS restrictions and passed with approved network escalation.
- Direct script execution of `scripts/verify_kafka.py` initially could not import `shared`. Added repo-root path setup at script startup.
- Docker daemon access and localhost Kafka socket access were blocked by the sandbox. The required commands passed with approved escalation.

## Deviations from the phase plan

- Added `docs/kafka-message-contracts.md` so topic names and message keys are documented without changing `README.md`.
- Kept one DLQ topic, `raw-aq-readings-dlq`, because that was the existing architecture topic and Phase 04 did not require per-topic DLQs.
- Added `pipeline-events` to the shared topic definitions because it already exists in the Phase 02 infrastructure topic set.

## Known issues and technical debt

- Severity: Low. Kafka helper functions are intentionally minimal and should be wrapped by service-specific poller, Spark, and API code in later phases.
- Severity: Low. `scripts/verify_kafka.py` verifies `raw-aq-readings` only; later phases should add service-level verification for weather, modeled AQ, processed AQ, and DLQ flows when those producers/consumers exist.
- Severity: Low. Local verification needs Docker/Kafka running and may require approval in this sandbox.

## What the next phase needs to know

- Phase 05 should import `RawAQReadingMessage`, `KafkaSettings`, `create_producer`, and `produce_message` instead of defining new wire contracts.
- OpenAQ messages must be sensor-based and include `source` plus `observation_type`; live OpenAQ should use `source=openaq_live` and `observation_type=observed`.
- Demo/replay messages must remain labeled with `source=demo_replay`, `observation_type=replay`, and `coverage_mode=REPLAY_DEMO`.
- Topic creation is idempotent through `scripts/create_kafka_topics.sh`.

## How to resume from scratch

```bash
python -m pip install --user -r requirements.txt
docker compose --profile core up -d
./scripts/create_kafka_topics.sh
python scripts/verify_kafka.py --fixture fixtures/sample_raw_aq_message.json
pytest tests/unit -q
```

## Next session prompt

```text
Follow AGENTS.md. Implement PHASE 05 only using docs/codex/phases/PHASE-05-openaq-live-ingestion.md.
```
