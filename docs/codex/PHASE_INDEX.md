# HimalayaAir Codex Phase Index

Use this file to run one bounded Codex session per phase.

## Rules

- Start every session by telling Codex the exact phase number and file.
- Codex must read AGENTS.md, this index, the active phase file, CHANGELOG.md, and prior phase summaries.
- Codex must not implement future phases unless explicitly instructed.
- Every phase ends with tests/checks, CHANGELOG.md update, and a phase summary.

## Phase table

| Phase | Name | Risk | Deliverable |
|---|---|---|---|
| 00 | [Codex Governance and Repository Contract](phases/PHASE-00-codex-governance.md) | LOW | A repo that Codex can navigate safely, with phase instructions and documentation structure in place. |
| 01 | [Data Reality Check and Source Validation](phases/PHASE-01-data-reality-check.md) | HIGH | A repeatable data-source validation workflow and a written report template that prevents building against imaginary sensor coverage. |
| 02 | [Infrastructure Foundation](phases/PHASE-02-infrastructure-foundation.md) | MEDIUM | A local infrastructure foundation that can be started by profile and checked by one script. |
| 03 | [Database Schema and Seed Data](phases/PHASE-03-database-schema-seed-data.md) | HIGH | A corrected database foundation that supports sensor-based ingestion, provenance, modeled fallback, replay, forecasts, and backfills. |
| 04 | [Kafka Topics and Shared Libraries](phases/PHASE-04-kafka-shared-libraries.md) | MEDIUM | A shared foundation so all services speak the same message and logging language. |
| 05 | [OpenAQ Sensor-Based Live Ingestion](phases/PHASE-05-openaq-live-ingestion.md) | HIGH | Live observed OpenAQ readings entering Kafka through the corrected sensor registry model. |
| 06 | [Weather and Modeled AQ Fallback](phases/PHASE-06-weather-modeled-aq.md) | MEDIUM | Weather readings and modeled baseline AQ data available for fallback rendering and forecasts. |
| 07 | [Spark Stream Processing and Timescale Persistence](phases/PHASE-07-spark-stream-processing.md) | HIGH | A real streaming path from Kafka to TimescaleDB with observable processing summaries. |
| 08 | [Airflow Backfills, Quality Checks, and FIRMS](phases/PHASE-08-airflow-backfills-quality.md) | HIGH | A repeatable orchestration layer for historical data, quality status, and fire-event enrichment. |
| 09 | [FastAPI REST API and WebSocket Layer](phases/PHASE-09-api-websocket.md) | HIGH | A curl-testable backend API with live/degraded/modeled/replay provenance visible to clients. |
| 10 | [Forecasting and Accuracy Tracking](phases/PHASE-10-forecasting.md) | HIGH | A forecast system that is always available, honest about model source, and measurable over time. |
| 11 | [Frontend Core Dashboard](phases/PHASE-11-frontend-core.md) | MEDIUM | A visually impressive live dashboard core that works with real or fixture API data. |
| 12 | [Historical Explorer and Forecast UI](phases/PHASE-12-historical-forecast-ui.md) | MEDIUM | A historical and forecast experience suitable for final-year defense storytelling. |
| 13 | [Replay Demo Mode and Spatial Polish](phases/PHASE-13-demo-spatial-polish.md) | MEDIUM | A reliable demo mode that exercises the real pipeline and keeps the dashboard impressive even when live data is sparse. |
| 14 | [Hardening, Benchmarks, Documentation, and Delivery](phases/PHASE-14-hardening-delivery.md) | MEDIUM | A defense-ready, reproducible, documented HimalayaAir project with known limitations clearly stated. |

## Recommended session prompt

Use this shape:

```text
Follow AGENTS.md.
Implement PHASE XX only using docs/codex/phases/PHASE-XX-name.md.
Do not implement future phases.
Run the phase verification commands, update CHANGELOG.md, write the phase summary, then report risks.
```
