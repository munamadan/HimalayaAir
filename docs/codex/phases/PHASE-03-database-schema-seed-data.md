# PHASE 03: Database Schema and Seed Data

Risk level: HIGH

Objective: Create the corrected TimescaleDB/PostGIS schema with provenance-aware readings, sensor registry, modeled AQ, forecasts, and seed data.

## Codex session prompt

```text
Follow AGENTS.md.

Implement PHASE 03: Database Schema and Seed Data only.

Before editing code, read:
- docs/himalayaair-system-overview.md
- docs/codex/PHASE_INDEX.md
- docs/codex/phases/PHASE-03-database-schema-seed-data.md
- CHANGELOG.md if it exists
- prior summaries in docs/phase-summaries/ if they exist

Do not implement future phases. Do not change the approved architecture unless this phase file explicitly requires it.

At the end, run the verification commands, update CHANGELOG.md, write the phase summary, and report changed files, pass/fail results, and remaining risks.
```

## Entry criteria

- [ ] Phase 02 complete.
- [ ] TimescaleDB service starts successfully or limitations are documented.

## Scope

- Initialize Alembic.
- Create migrations for extensions, stations, station_sensors, districts, weather_locations, fire_events, aq_readings, modeled_aq_readings, weather_readings, forecast_runs, forecasts, forecast_accuracy, pipeline_runs, backfill_manifest, monthly_reports.
- Create continuous aggregates after hypertables exist.
- Use MULTIPOLYGON for district boundaries or normalize polygons to ST_Multi.
- Use valid hypertable primary keys or unique constraints that include timestamp.
- Seed weather_locations and minimal station placeholders only when metadata sync has no DB target yet.

## Do not do in this phase

- Do not run raw schema edits outside Alembic.
- Do not create a unique index on a hypertable unless it includes the time partition column.
- Do not model OpenAQ readings by location only.

## Implementation tasks

- Create SQLAlchemy metadata models or migration-only schema definitions.
- Add seed script for Kathmandu weather locations and optional district loading.
- Add tests or scripts that verify all expected tables and constraints exist.
- Update data-source scripts from Phase 01 so they can optionally upsert stations and station_sensors.

## Verification commands

Run the commands that apply to the current environment. If a command cannot run because infrastructure or credentials are unavailable, record the reason in the phase summary.

```bash
alembic upgrade head
python scripts/verify_db_schema.py
python scripts/seed_weather_locations.py --dry-run
```

## Required changelog entry

Add a CHANGELOG.md entry with header `PHASE-03 Database Schema and Seed Data` and include files changed, reason, impact, and verification performed.

## Required phase summary

Create `docs/phase-summaries/PHASE-03-summary.md` using `docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md`.

## Exit criteria

- [ ] All in-scope tasks are complete or explicitly documented as deferred within this phase.
- [ ] Relevant verification commands were run or blocked reasons were documented.
- [ ] CHANGELOG.md was updated.
- [ ] docs/phase-summaries/PHASE-03-summary.md was written.
- [ ] No future-phase work was introduced.
- [ ] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Deliverable

A corrected database foundation that supports sensor-based ingestion, provenance, modeled fallback, replay, forecasts, and backfills.
