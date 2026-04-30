# PHASE-08 Summary - Airflow Backfills, Quality Checks, and FIRMS

## What was built

- `airflow/dags/openaq_historical_backfill.py`: Airflow DAG wrapper for archive-first OpenAQ historical backfill with sensor API fallback.
- `airflow/dags/weather_historical_backfill.py`: Airflow DAG wrapper for Open-Meteo historical weather backfill.
- `airflow/dags/air_quality_data_quality_check.py`: Scheduled two-hour data quality DAG wrapper.
- `airflow/dags/firms_daily_load.py`: Daily FIRMS fire-event load DAG wrapper.
- `airflow/dags/forecast_recompute_hook.py`: Hourly forecast recompute scheduling hook that records readiness without implementing Phase 10 forecasting.
- `airflow/dags/himalayaair/`: Shared Airflow task code for settings, DB writes, `pipeline_runs`, `backfill_manifest`, OpenAQ archive/API handling, Open-Meteo archive weather, data quality classification, FIRMS parsing, and forecast hook metadata.
- `docker-compose.yml`: Batch profile now includes TimescaleDB and Airflow can import read-only `shared` and `services` packages through `PYTHONPATH`.
- `.env.example`: Blank Airflow runtime and FIRMS configuration variables.
- `tests/airflow/`: Unit coverage for OpenAQ archive parsing, weather month windows, data quality degradation, and FIRMS hash parsing.
- `docs/airflow/manual-triggers.md`: Manual DAG trigger examples.
- `CHANGELOG.md`: Phase 08 changelog entry.

## Current system state

The repository now has five Airflow DAG files under `airflow/dags`. DAG task code records task outcomes in `pipeline_runs`; OpenAQ, weather, and FIRMS backfill-style work also writes `backfill_manifest` rows for idempotency and auditability.

OpenAQ historical backfill reads active `station_sensors`, tries the OpenAQ archive object for each location/day, writes archive rows with `source='openaq_archive'`, and falls back to sensor measurement API rows with observed provenance when the archive is unavailable. Weather history writes Open-Meteo archive weather rows directly to `weather_readings`. FIRMS parses acquisition fields and writes `fire_events` with stable `event_hash`. Data quality writes `coverage_snapshots` and returns `healthy`, `degraded`, or `down`; sparse fresh station coverage is degraded, not a hard DAG failure.

No live 5-minute ingestion, forecast model execution, API endpoint, WebSocket, frontend, replay service, or future-phase forecast writes were introduced.

## Commands run

```bash
python -m py_compile airflow/dags/*.py airflow/dags/himalayaair/*.py
# passed

pytest tests/airflow -q
# passed: 8 tests

docker compose --profile batch config --quiet
# passed

PYTHONPATH=airflow/dags:. python -c "import openaq_historical_backfill, weather_historical_backfill, air_quality_data_quality_check, firms_daily_load, forecast_recompute_hook; print('ok')"
# passed

pytest tests/unit tests/openaq tests/weather tests/integration tests/airflow -q
# passed: 41 tests

airflow dags list || true
# completed through shell fallback; host Airflow CLI is not installed

python -m py_compile airflow/dags/*.py
# passed

pytest tests/airflow -q
# passed: 8 tests
```

## Exit criteria verification

- [x] All in-scope tasks are complete or explicitly documented: OpenAQ historical backfill, weather historical backfill, data quality checks, FIRMS daily load, forecast scheduling hook, idempotent manifest writes, structured logs, `pipeline_runs`, and manual trigger docs are implemented.
- [x] Relevant verification commands were run: required Airflow, compile, and pytest commands were run; the host Airflow CLI is unavailable and documented.
- [x] `CHANGELOG.md` was updated with `PHASE-08 Airflow Backfills, Quality Checks, and FIRMS`.
- [x] `docs/phase-summaries/PHASE-08-summary.md` was written.
- [x] No future-phase work was introduced: the forecast DAG is only a scheduling hook and does not create `forecast_runs` or `forecasts`.
- [x] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced: API keys remain environment-only, OpenAQ rows preserve observed provenance, FIRMS missing-key failures are recorded visibly, and modeled data is not written as observed AQ.

## Problems encountered and resolutions

- Git index writes were blocked by the sandbox as a read-only filesystem. The commit was rerun with approved escalation and succeeded.
- The host environment does not have the `airflow` CLI installed. The required `airflow dags list || true` command completed through the shell fallback and the issue is documented.
- `docs/` and `CHANGELOG.md` are ignored by `.gitignore` even though phase workflow requires updates. New docs were added with forced Git staging.

## Deviations from the phase plan

- Added a `forecast_recompute_hook` DAG because the Phase 08 objective includes forecast scheduling hooks. It only records a `pipeline_runs` hook event and leaves actual forecast arbitration to Phase 10.
- Used sentinel `external_sensor_id` values for weather and FIRMS `backfill_manifest` rows so manifest idempotency works despite nullable columns in the existing unique constraint.
- Added batch-profile imports for `shared` and `services` through read-only mounts rather than copying shared code into Airflow DAGs.

## Known issues and technical debt

- Severity: Medium. Live DAG execution was not run in Docker because the required verification command only lists DAGs and the host Airflow CLI is unavailable. Start the batch profile and run `airflow dags list` inside `airflow-scheduler` for a full parse check.
- Severity: Medium. Airflow startup may need network access for `_PIP_ADDITIONAL_REQUIREMENTS` unless the image already has `structlog` and `httpx` cached or a custom Airflow image is built later.
- Severity: Medium. FIRMS live loads require a server-side `FIRMS_MAP_KEY`; missing-key runs fail visibly in `pipeline_runs`.
- Severity: Low. The OpenAQ archive path follows the current public S3 archive layout and falls back to the API when objects are missing.
- Severity: Low. Data quality deactivates sensors only after the configured sustained absence window, default 14 days.

## What the next phase needs to know

- The API phase can read `coverage_snapshots` for the latest quality/coverage state.
- FIRMS data is now stored in `fire_events` with acquisition fields and `event_hash`; do not reduce it to point plus date.
- Forecast scheduling exists as an Airflow hook only. Phase 10 must implement model arbitration and actual `forecast_runs`/`forecasts` writes.
- Manual trigger examples are in `docs/airflow/manual-triggers.md`.

## How to resume from scratch

```bash
docker compose --profile batch up -d airflow-postgres airflow-webserver airflow-scheduler
docker compose --profile batch exec airflow-scheduler airflow dags list
docker compose --profile batch exec airflow-scheduler airflow dags trigger air_quality_data_quality_check
pytest tests/airflow -q
```

## Next session prompt

```text
Follow AGENTS.md. Implement PHASE 09 only using docs/codex/phases/PHASE-09-api-websocket.md.
```
