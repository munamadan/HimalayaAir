# PHASE-03 Summary - Database Schema and Seed Data

## What was built

- `requirements.txt`: Added reproducible Python migration dependencies for Alembic, SQLAlchemy, and psycopg2.
- `alembic.ini`: Added Alembic configuration for the local Phase 02 TimescaleDB default.
- `db/alembic/env.py`: Added Alembic environment setup with sync DB URL resolution from `SYNC_DATABASE_URL`, `DATABASE_URL`, or the local `localhost:55432` default.
- `db/alembic/versions/0001_extensions_core_schema.py`: Added TimescaleDB/PostGIS extensions and core registry tables for stations, station_sensors, districts, and weather_locations.
- `db/alembic/versions/0002_timeseries_readings.py`: Added `aq_readings`, `weather_readings`, and `modeled_aq_readings` hypertables with timestamp-inclusive primary keys and provenance checks.
- `db/alembic/versions/0003_forecast_operations.py`: Added forecast, forecast accuracy, pipeline run, coverage snapshot, and monthly report tables.
- `db/alembic/versions/0004_backfill_fire_events.py`: Added backfill manifest and fire event tables.
- `db/alembic/versions/0005_continuous_aggregates.py`: Added `aq_hourly`, `aq_daily`, and `valley_daily` continuous aggregates and refresh policies.
- `scripts/db_config.py`: Added shared sync database URL normalization for scripts and Alembic.
- `scripts/seed_weather_locations.py`: Added dry-run and idempotent write support for the five Kathmandu Valley weather locations.
- `scripts/verify_db_schema.py`: Added schema verification for extensions, tables, hypertables, continuous aggregates, indexes, checks, and Timescale unique-index rules.
- `scripts/sync_openaq_metadata.py`: Added `--write-db` support to upsert OpenAQ stations and station_sensors while preserving `--dry-run` inspection.
- `README.md`: Replaced detailed phase workflow text with a brief general project description, per user request.
- `AGENTS.md`: Added the rule that `README.md` must not be changed unless the user explicitly requests it.
- `CHANGELOG.md`: Recorded the Phase 03 implementation, verification, and operational notes.

## Current system state

The local `core` Docker Compose profile is running. TimescaleDB/PostGIS is available on host port `55432`, and Alembic has upgraded the database to revision `0005_continuous_aggregates`.

The database now has the Phase 03 foundation for sensor-based ingestion, provenance-aware observed/replay readings, modeled AQ fallback, weather readings, forecasts, pipeline observability, backfills, monthly reports, and fire-event enrichment. The three time-series reading tables are Timescale hypertables, and all unique constraints on hypertables include `timestamp`.

Five `weather_locations` rows were seeded: Kathmandu Center, Lalitpur, Bhaktapur, Kirtipur, and Budhanilkantha.

No API endpoints, Kafka producers/consumers, Spark jobs, Airflow DAGs, forecast execution, district boundary data, or frontend behavior were implemented.

## Commands run

```bash
python -m py_compile scripts/db_config.py scripts/seed_weather_locations.py scripts/verify_db_schema.py scripts/sync_openaq_metadata.py db/alembic/env.py db/alembic/versions/*.py
# passed

python scripts/seed_weather_locations.py --dry-run
# passed; reported 5 Kathmandu Valley weather seed rows without DB writes

python scripts/sync_openaq_metadata.py --dry-run --fixture-location fixtures/sample_openaq_location.json
# passed; preserved fixture metadata dry-run behavior

python -m pip install --user -r requirements.txt
# passed with approval; installed Alembic and Mako into the user site

docker compose --profile core up -d
# passed with approval; started TimescaleDB, Kafka, API placeholder, and frontend placeholder

alembic upgrade head
# failed in the sandbox because host access to the Docker-exposed database port was blocked

PATH="$HOME/.local/bin:$PATH" alembic upgrade head
# passed with approval; applied all five Alembic revisions through 0005_continuous_aggregates

python scripts/verify_db_schema.py
# passed with approval; verified required tables, hypertables, continuous aggregates, constraints, and indexes

python scripts/seed_weather_locations.py --dry-run
# passed; required Phase 03 verification command

python scripts/seed_weather_locations.py
# passed with approval; inserted or updated 5 weather_locations rows

python scripts/verify_db_schema.py
# passed with approval after seeding

pytest tests/unit -q
# passed: 5 tests
```

## Exit criteria verification

- [x] All in-scope tasks are complete: Alembic, schema migrations, hypertables, continuous aggregates, seed script, schema verifier, and OpenAQ metadata DB upsert support were added.
- [x] Relevant verification commands were run: `alembic upgrade head`, `python scripts/verify_db_schema.py`, and `python scripts/seed_weather_locations.py --dry-run` passed after the required environment setup.
- [x] `CHANGELOG.md` was updated with a Phase 03 entry.
- [x] `docs/phase-summaries/PHASE-03-summary.md` was written.
- [x] No future-phase work was introduced: no ingestion runtime, Kafka message contracts, Spark persistence job, Airflow DAG, API endpoint, forecast runner, or frontend implementation was added.
- [x] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Problems encountered and resolutions

- Alembic was not installed in the local Python environment. Added `requirements.txt` and installed the dependencies with approval.
- `alembic` installed under `~/.local/bin`, which is not on the shell PATH. The migration was run with `PATH="$HOME/.local/bin:$PATH"`.
- The first Alembic run failed in the sandbox because the host could not connect to Docker's exposed TimescaleDB port. The same command passed with approved escalation.
- Docker daemon access requires approval in this environment. Docker Compose checks and database-connected Python scripts were run with approved escalation.

## Deviations from the phase plan

- Added `coverage_snapshots` because the system overview defines it as the storage point for coverage mode, confidence, modeled availability, and replay activity.
- Added `coverage_mode` and `confidence` columns to `aq_readings`, and `observation_type` plus `coverage_mode` to `modeled_aq_readings`, to keep stored AQ provenance explicit.
- Added a unique constraint on `weather_locations.name` so the seed script can upsert idempotently.
- District boundary loading was not implemented because the repository does not contain a trusted district geometry fixture or source file. The `districts` table enforces `MULTIPOLYGON` geometry and is ready for a later explicit load.

## Known issues and technical debt

- Severity: Medium. District boundary rows are not populated yet, so later district assignment must wait for a trusted Kathmandu/Lalitpur/Bhaktapur boundary source.
- Severity: Low. Alembic is installed in the user site and may require `PATH="$HOME/.local/bin:$PATH"` unless the user's shell already includes `~/.local/bin`.
- Severity: Low. `scripts/sync_openaq_metadata.py --write-db` was added and syntax/dry-run verified, but live DB upsert was not run to avoid inserting fixture station metadata as real OpenAQ metadata.

## What the next phase needs to know

- Use `stations` and `station_sensors` for OpenAQ. Poll by active `station_sensors`, not locations only.
- Host database URL defaults to `postgresql://himalayaair:himalayaair@localhost:55432/himalayaair`.
- Internal Docker services should still use `timescaledb:5432`.
- Modeled AQ belongs in `modeled_aq_readings` with `observation_type='modeled'` and `coverage_mode='MODELED_BASELINE'`.
- `README.md` is now protected by `AGENTS.md`; do not change it in future phases unless the user explicitly asks.

## How to resume from scratch

```bash
docker compose --profile core up -d
python -m pip install --user -r requirements.txt
PATH="$HOME/.local/bin:$PATH" alembic upgrade head
python scripts/verify_db_schema.py
python scripts/seed_weather_locations.py --dry-run
python scripts/seed_weather_locations.py
```

## Next session prompt

```text
Follow AGENTS.md. Implement PHASE 04 only using docs/codex/phases/PHASE-04-kafka-shared-libraries.md.
```
