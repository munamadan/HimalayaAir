# Changelog

All meaningful project changes are recorded here so future Codex sessions can resume with the implemented phase history.

## PHASE-03 Database Schema and Seed Data - 2026-04-29

### Files changed

- `requirements.txt`: Added Alembic, SQLAlchemy, and psycopg2 migration dependencies.
- `alembic.ini`: Added Alembic configuration for the local TimescaleDB default.
- `db/alembic/env.py`: Added environment-driven sync DB URL resolution for migrations.
- `db/alembic/versions/0001_extensions_core_schema.py`: Added TimescaleDB/PostGIS extensions and core station, sensor, district, and weather-location tables.
- `db/alembic/versions/0002_timeseries_readings.py`: Added provenance-aware AQ, weather, and modeled-AQ hypertables.
- `db/alembic/versions/0003_forecast_operations.py`: Added forecast, pipeline, coverage, and monthly report tables.
- `db/alembic/versions/0004_backfill_fire_events.py`: Added backfill manifest and fire event tables.
- `db/alembic/versions/0005_continuous_aggregates.py`: Added `aq_hourly`, `aq_daily`, and `valley_daily` continuous aggregates with refresh policies.
- `scripts/db_config.py`: Added shared sync database URL normalization.
- `scripts/seed_weather_locations.py`: Added dry-run and idempotent seed support for five Kathmandu Valley weather locations.
- `scripts/verify_db_schema.py`: Added schema verification for extensions, tables, hypertables, continuous aggregates, indexes, checks, and Timescale unique-index rules.
- `scripts/sync_openaq_metadata.py`: Added optional `--write-db` support for upserting OpenAQ stations and station_sensors.
- `README.md`: Replaced detailed phase workflow text with a brief general project description, per user request.
- `AGENTS.md`: Added the rule that `README.md` must not be changed unless the user explicitly requests it.
- `docs/phase-summaries/PHASE-03-summary.md`: Added the Phase 03 completion summary.
- `CHANGELOG.md`: Recorded Phase 03 implementation, verification, and operational notes.

### Reason

Phase 03 requires a corrected database foundation for sensor-based ingestion, provenance-aware readings, modeled fallback, replay support, forecasts, pipeline observability, backfills, reports, and geospatial context.

### Impact

The local TimescaleDB/PostGIS database now upgrades through Alembic to a schema that supports the approved architecture. AQ-related hypertables preserve source and observation type, modeled AQ remains separate from observed readings, and all hypertable primary keys include the `timestamp` partition column. Weather location seed data can be previewed or written idempotently.

### Verification performed

- `python -m py_compile scripts/db_config.py scripts/seed_weather_locations.py scripts/verify_db_schema.py scripts/sync_openaq_metadata.py db/alembic/env.py db/alembic/versions/*.py`: passed.
- `python scripts/seed_weather_locations.py --dry-run`: passed and reported five weather seed rows.
- `python scripts/sync_openaq_metadata.py --dry-run --fixture-location fixtures/sample_openaq_location.json`: passed and preserved dry-run metadata output.
- `python -m pip install --user -r requirements.txt`: passed with approval; installed Alembic and Mako.
- `docker compose --profile core up -d`: passed with approval; started TimescaleDB, Kafka, API placeholder, and frontend placeholder.
- `alembic upgrade head`: failed in the sandbox because host access to the Docker-exposed database port was blocked.
- `PATH="$HOME/.local/bin:$PATH" alembic upgrade head`: passed with approval and applied all five revisions through `0005_continuous_aggregates`.
- `python scripts/verify_db_schema.py`: passed with approval and verified required schema objects.
- `python scripts/seed_weather_locations.py --dry-run`: passed as the required Phase 03 seed verification command.
- `python scripts/seed_weather_locations.py`: passed with approval and inserted or updated five `weather_locations` rows.
- `python scripts/verify_db_schema.py`: passed again after seeding.
- `pytest tests/unit -q`: passed with 5 tests.

### Plan changes

- Added `coverage_snapshots` because the system overview defines it as the storage point for coverage mode, confidence, modeled availability, and replay activity.
- Added `coverage_mode` and `confidence` columns to `aq_readings`, and `observation_type` plus `coverage_mode` to `modeled_aq_readings`, to keep stored AQ provenance explicit.
- Added a unique constraint on `weather_locations.name` so seed writes are idempotent.
- Did not load district boundaries because the repository has no trusted district geometry fixture or source file; the schema enforces `MULTIPOLYGON` and is ready for a later explicit load.

### Phase result

Phase 03 is complete. The database foundation is migrated and verified, weather locations are seeded, required documentation is updated, and Phase 04 is safe to start.


## PHASE-02 Infrastructure Foundation - 2026-04-29

### Files changed

- `docker-compose.yml`: Added Docker Compose profiles for `core`, `stream`, `batch`, `weather`, `observed`, `demo`, and `full` with TimescaleDB/PostGIS, Kafka, Airflow PostgreSQL metadata, Airflow webserver/scheduler, Spark placeholder, API placeholder, frontend placeholder, weather placeholders, OpenAQ placeholder, and replay placeholder services.
- `.env.example`: Added blank infrastructure override names for Airflow local user, Kafka cluster ID, and host ports without committing secrets.
- `scripts/verify_env.sh`: Added a profile-aware Docker Compose health verification script.
- `scripts/create_kafka_topics.sh`: Added a Kafka topic creation script with dry-run support for the architecture topics.
- `README.md`: Documented profile usage, health checks, Kafka topic setup, placeholder scope, and host port defaults.
- `airflow/dags/.gitkeep`: Added the Airflow DAG mount directory placeholder.
- `airflow/plugins/.gitkeep`: Added the Airflow plugin mount directory placeholder.
- `docs/phase-summaries/PHASE-02-summary.md`: Added the Phase 02 completion summary.
- `CHANGELOG.md`: Recorded Phase 02 implementation, verification, and operational notes.

### Reason

Phase 02 requires a local infrastructure foundation that can be started by Docker Compose profile, checked by one script, and prepared for later Kafka, Spark, Airflow, API, and frontend phases without implementing application logic early.

### Impact

The `core` profile now starts TimescaleDB/PostGIS, Kafka, an API placeholder, and a frontend placeholder. Kafka topics can be created reproducibly, and later phases can replace placeholders with real service implementations without changing the approved architecture. Database host ports default to higher local ports to avoid conflicts with existing PostgreSQL installations while preserving normal container network ports.

### Verification performed

- `bash -n scripts/verify_env.sh scripts/create_kafka_topics.sh`: passed.
- `docker compose config`: passed; rendered no default services because runtime services are profile-gated.
- `docker compose --profile full config --quiet`: passed.
- `docker compose --profile full config --services | sort`: passed and listed all profile services.
- `./scripts/create_kafka_topics.sh --dry-run`: passed and printed the five expected topic creation commands.
- `docker compose --profile core up -d`: initially failed because host port `5432` was already in use.
- `docker compose --profile core up -d`: passed after changing host database port defaults to `55432` and `55433`.
- `./scripts/verify_env.sh`: passed with `timescaledb`, `kafka`, `api`, and `frontend` healthy.
- `./scripts/create_kafka_topics.sh`: passed and created `raw-aq-readings`, `processed-aq-readings`, `raw-aq-readings-dlq`, `weather-data`, and `pipeline-events`.
- `docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --list | sort`: passed and listed all five expected topics.

### Plan changes

- Added the `observed` profile as an architecture-preserving placeholder because `docs/himalayaair-system-overview.md` defines it, even though the Phase 02 checklist only named the other profiles.
- Added configurable host port environment variables with safe local defaults after the first core startup found an existing PostgreSQL service on `5432`.
- Ran actual core profile startup and Kafka topic creation in addition to the required dry-run checks.
- No application service logic, database schema, ingestion, Spark processing, Airflow DAGs, API endpoints, forecasting, or frontend product behavior was introduced.

### Phase result

Phase 02 is complete. The core infrastructure profile starts successfully, required verification passed, and the next phase is safe to start after reviewing this summary.

## PHASE-01 Data Reality Check and Source Validation - 2026-04-28

### Files changed

- `scripts/source_validation.py`: Added shared dataclasses, HTTP JSON client, OpenAQ and Open-Meteo source clients, normalization helpers, coverage-mode recommendation logic, and JSON report helpers.
- `scripts/sync_openaq_metadata.py`: Added dry-run OpenAQ Kathmandu location and sensor discovery without database writes.
- `scripts/check_openaq_coverage.py`: Added Kathmandu observed coverage reporting using sensor metadata or sensor measurement endpoint sampling.
- `scripts/check_openmeteo_aq.py`: Added Open-Meteo modeled AQ availability validation labeled as `openmeteo_cams` and `modeled`.
- `scripts/__init__.py`: Added a package marker so tests can import script utilities.
- `fixtures/sample_openaq_location.json`: Added an offline OpenAQ locations schema fixture with nested sensors.
- `fixtures/sample_openaq_measurement.json`: Added an offline OpenAQ sensor measurement schema fixture.
- `fixtures/sample_openmeteo_aq.json`: Added an offline Open-Meteo AQ fixture for modeled fallback tests.
- `tests/conftest.py`: Added minimal test path setup for the repository skeleton.
- `tests/unit/test_source_validation.py`: Added offline unit tests for OpenAQ normalization, modeled AQ normalization, and coverage-mode priority logic.
- `docs/data-source-validation.md`: Added manual source-validation workflow, expected outputs, coverage-mode interpretation, and replay dataset strategy.
- `docs/phase-summaries/PHASE-01-summary.md`: Added the Phase 01 completion summary.
- `CHANGELOG.md`: Recorded Phase 01 implementation, verification, live OpenAQ closure results, and plan deviations.

### Reason

Phase 01 requires a repeatable source-validation workflow before ingestion or database work begins. The project must discover real OpenAQ stations and sensors, measure observed freshness honestly, validate modeled fallback availability, and document when credentials or live coverage are unavailable.

### Impact

Future phases can build sensor-based OpenAQ ingestion against normalized station and sensor metadata instead of hardcoded station assumptions. The modeled fallback path is explicitly separated from observed data and reports `MODELED_BASELINE` only for Open-Meteo/CAMS modeled AQ.

### Verification performed

- `python scripts/check_openaq_coverage.py --help`: passed.
- `python scripts/check_openmeteo_aq.py --help`: passed.
- `python scripts/sync_openaq_metadata.py --help`: passed.
- `python -m py_compile scripts/source_validation.py scripts/sync_openaq_metadata.py scripts/check_openaq_coverage.py scripts/check_openmeteo_aq.py`: passed.
- `pytest tests/unit -q`: passed with 5 tests.
- `python scripts/sync_openaq_metadata.py --dry-run --fixture-location fixtures/sample_openaq_location.json`: passed and produced valid JSON.
- `python scripts/check_openaq_coverage.py --fixture-location fixtures/sample_openaq_location.json --fixture-measurement fixtures/sample_openaq_measurement.json`: passed and produced valid JSON with `STATION_ONLY` for sparse observed fixture coverage.
- `python scripts/check_openmeteo_aq.py --fixture fixtures/sample_openmeteo_aq.json`: passed and produced valid JSON with `MODELED_BASELINE`.
- `python scripts/check_openmeteo_aq.py`: initially failed in the sandbox due DNS/network restriction, then passed with approved network escalation and returned `MODELED_BASELINE` with all requested variables available.
- `OPENAQ_API_KEY` environment check: blocked live OpenAQ validation because the key was not present in the environment.
- `python scripts/check_openaq_coverage.py --metadata-only`: exited 2 with the expected message that `OPENAQ_API_KEY` is required for live OpenAQ validation calls.
- `set -a; source .env; set +a; python scripts/sync_openaq_metadata.py --dry-run --output tmp/openaq-metadata.json`: passed with approved network escalation after the OpenAQ key was added to local `.env`; discovered 52 Kathmandu-bounds locations and 256 sensors.
- `set -a; source .env; set +a; python scripts/check_openaq_coverage.py --modeled-available --output tmp/openaq-coverage.json`: passed with approved network escalation; measured 1 fresh station, 4 recent stations, and `recommended_coverage_mode=RECENT_OBSERVED`.
- `python -m json.tool tmp/openaq-metadata.json` and `python -m json.tool tmp/openaq-coverage.json`: passed; generated reports are valid JSON and remain uncommitted under ignored `tmp/`.

### Plan changes

- Added `scripts/source_validation.py` as a shared Phase 01 utility module so the three CLI scripts and tests use one normalization path.
- Added `fixtures/sample_openmeteo_aq.json` to keep modeled fallback tests offline, although the phase only explicitly named OpenAQ fixtures.
- Added `tests/conftest.py` because the repository skeleton did not yet have Python package/test path configuration.
- No architecture changes were made.
- No future-phase implementation was introduced.

### Phase result

Phase 01 implementation and live OpenAQ closure are complete. Live coverage is currently sparse but usable as `RECENT_OBSERVED`: 1 fresh station, 4 recent stations, and modeled fallback available. The next phase is safe to start.

## PHASE-00 Codex Governance and Repository Contract - 2026-04-28

### Files changed

- `AGENTS.md`: Existing Codex standing instructions verified as the repository contract.
- `docs/himalayaair-system-overview.md`: Existing architecture source of truth verified.
- `docs/codex/PHASE_INDEX.md`: Existing one-phase workflow index verified.
- `docs/codex/phases/`: Existing phase instruction directory verified.
- `docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md`: Existing summary template verified.
- `.gitignore`: Added local secret, cache, build, log, and editor exclusions.
- `.env.example`: Added blank environment variable contract with no committed secrets.
- `README.md`: Added repository skeleton and phase workflow entrypoint.
- `api/.gitkeep`, `services/.gitkeep`, `frontend/.gitkeep`, `airflow/.gitkeep`, `spark/.gitkeep`, `db/.gitkeep`: Added trackable empty skeleton directories for future phases.
- `docs/phase-summaries/PHASE-00-summary.md`: Added the Phase 00 completion summary.
- `CHANGELOG.md`: Created phase history file.

### Reason

Phase 00 requires an AI-readable repository contract, documentation structure, changelog, safe environment template, and bootstrap folder layout before implementation starts.

### Impact

Future Codex sessions can follow the one-phase workflow, locate the authoritative architecture and phase instructions, and avoid committing local secrets or generated files.

### Verification performed

- `test -f AGENTS.md`: passed.
- `test -f docs/himalayaair-system-overview.md`: passed.
- `test -f CHANGELOG.md`: passed.
- `test -d docs/codex/phases`: passed.
- `test -d docs/phase-summaries`: passed.
- `test -f AGENTS.md && test -f docs/himalayaair-system-overview.md && test -f CHANGELOG.md && test -d docs/codex/phases && test -d docs/phase-summaries && test -f docs/phase-summaries/PHASE-00-summary.md`: passed.
- `find api services frontend airflow spark db -maxdepth 2 -type f | sort`: confirmed only `.gitkeep` placeholders exist in skeleton directories.
- `rg -n "(OPENAQ_API_KEY|FIRMS_MAP_KEY|VITE_MAPBOX_TOKEN)=.\\S" .env.example || true`: no non-empty secret/token values found.
- `git status --short`: confirmed Phase 00 files are untracked until reviewed and committed; no existing tracked implementation files were modified.

### Plan changes

- No architecture changes were made.
- No future-phase implementation was introduced.

### Phase result

Phase 00 exit criteria are met. The next phase is safe to start after this phase is reviewed and committed.
