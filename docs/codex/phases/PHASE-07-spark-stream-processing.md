# PHASE 07: Spark Stream Processing and Timescale Persistence

Risk level: HIGH

Objective: Process raw AQ messages through Spark, calculate AQI, assign districts, flag anomalies, write TimescaleDB, and notify FastAPI.

## Codex session prompt

```text
Follow AGENTS.md.

Implement PHASE 07: Spark Stream Processing and Timescale Persistence only.

Before editing code, read:
- docs/himalayaair-system-overview.md
- docs/codex/PHASE_INDEX.md
- docs/codex/phases/PHASE-07-spark-stream-processing.md
- CHANGELOG.md if it exists
- prior summaries in docs/phase-summaries/ if they exist

Do not implement future phases. Do not change the approved architecture unless this phase file explicitly requires it.

At the end, run the verification commands, update CHANGELOG.md, write the phase summary, and report changed files, pass/fail results, and remaining risks.
```

## Entry criteria

- [ ] Phase 06 complete.
- [ ] raw-aq-readings topic exists.
- [ ] aq_readings schema exists.

## Scope

- Create services/spark/jobs/aq_stream_processor.py.
- Create pure Python aqi_calculator.py with tests.
- Read raw-aq-readings from Kafka.
- Validate and normalize messages.
- Calculate PM2.5 AQI first, with safe handling for unsupported pollutants.
- Assign district using PostGIS with ST_Covers or fallback nearest district.
- Flag range and baseline anomalies without failing early sparse data.
- Write idempotently to aq_readings and update station last_seen.
- Publish processed-aq-readings summary as best-effort notification.
- Write pipeline_runs entries.

## Do not do in this phase

- Do not rely on exact pollutant timestamp alignment for composite AQI.
- Do not crash when baseline data is insufficient.
- Do not claim exactly-once semantics.

## Implementation tasks

- Implement Spark local mode job with checkpoint volume.
- Implement foreachBatch write path with psycopg2 and ON CONFLICT handling.
- Implement anomaly logic with explicit insufficient_baseline quality flag.
- Implement unit tests for AQI and integration fixture tests for batch transformation.

## Verification commands

Run the commands that apply to the current environment. If a command cannot run because infrastructure or credentials are unavailable, record the reason in the phase summary.

```bash
pytest tests/unit/test_aqi_calculator.py -q
python services/spark/jobs/aq_stream_processor.py --fixture fixtures/sample_raw_aq_batch.json --dry-run
docker compose --profile stream up -d spark-stream || true
```

## Required changelog entry

Add a CHANGELOG.md entry with header `PHASE-07 Spark Stream Processing and Timescale Persistence` and include files changed, reason, impact, and verification performed.

## Required phase summary

Create `docs/phase-summaries/PHASE-07-summary.md` using `docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md`.

## Exit criteria

- [ ] All in-scope tasks are complete or explicitly documented as deferred within this phase.
- [ ] Relevant verification commands were run or blocked reasons were documented.
- [ ] CHANGELOG.md was updated.
- [ ] docs/phase-summaries/PHASE-07-summary.md was written.
- [ ] No future-phase work was introduced.
- [ ] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Deliverable

A real streaming path from Kafka to TimescaleDB with observable processing summaries.
