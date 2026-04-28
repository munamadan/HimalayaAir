# PHASE-01 Summary - Data Reality Check and Source Validation

## What was built

- `scripts/source_validation.py`: Shared typed source-validation module with OpenAQ/Open-Meteo clients, timeout/retry HTTP calls, normalization dataclasses, freshness reporting, and coverage-mode recommendation logic.
- `scripts/sync_openaq_metadata.py`: Dry-run OpenAQ metadata discovery CLI for Kathmandu location and sensor validation.
- `scripts/check_openaq_coverage.py`: Observed coverage CLI that reports locations, sensors, pollutants, freshness, and recommended coverage mode.
- `scripts/check_openmeteo_aq.py`: Modeled AQ availability CLI for Kathmandu center using Open-Meteo AQ variables.
- `scripts/__init__.py`: Allows tests to import shared script utilities.
- `fixtures/sample_openaq_location.json`: Offline OpenAQ locations fixture with nested sensors.
- `fixtures/sample_openaq_measurement.json`: Offline OpenAQ sensor measurement fixture.
- `fixtures/sample_openmeteo_aq.json`: Offline Open-Meteo AQ fixture for modeled fallback tests.
- `tests/conftest.py`: Minimal repository root import setup for pytest.
- `tests/unit/test_source_validation.py`: Offline unit coverage for OpenAQ station/sensor normalization, measurement normalization, coverage-mode priority, and Open-Meteo modeled AQ normalization.
- `docs/data-source-validation.md`: Manual workflow, expected outputs, source contracts, coverage-mode interpretation, and replay dataset strategy.
- `CHANGELOG.md`: Phase 01 changelog entry with verification and plan deviations.

## Current system state

Phase 01 is a source-validation-only phase.

No Docker services, database schema, TimescaleDB writes, Kafka topics, Spark jobs, Airflow DAGs, FastAPI endpoints, forecasting logic, or frontend views were introduced.

OpenAQ live validation has passed after `OPENAQ_API_KEY` was added to local `.env`. Live metadata discovery found 52 Kathmandu-bounds locations and 256 sensors. Live coverage sampling found 1 fresh station and 4 recent stations, so the current recommended mode is `RECENT_OBSERVED` with medium confidence.

The local `.env` file remains ignored by Git. Generated live validation reports are under ignored `tmp/` paths and are not committed.

Open-Meteo modeled AQ validation was run live with approved network escalation and returned all requested modeled fallback variables for Kathmandu center with `coverage_mode=MODELED_BASELINE`.

## Commands run

```bash
python scripts/check_openaq_coverage.py --help
# passed

python scripts/check_openmeteo_aq.py --help
# passed

python scripts/sync_openaq_metadata.py --help
# passed

python -m py_compile scripts/source_validation.py scripts/sync_openaq_metadata.py scripts/check_openaq_coverage.py scripts/check_openmeteo_aq.py
# passed

pytest tests/unit -q
# passed: 5 tests

python scripts/sync_openaq_metadata.py --dry-run --fixture-location fixtures/sample_openaq_location.json
# passed; produced valid JSON

python scripts/check_openaq_coverage.py --fixture-location fixtures/sample_openaq_location.json --fixture-measurement fixtures/sample_openaq_measurement.json
# passed; produced valid JSON with recommended_coverage_mode=STATION_ONLY

python scripts/check_openmeteo_aq.py --fixture fixtures/sample_openmeteo_aq.json
# passed; produced valid JSON with coverage_mode=MODELED_BASELINE

python scripts/check_openmeteo_aq.py
# failed in sandbox: DNS/network restriction
# passed with approved network escalation; all requested variables available

if [ -n "${OPENAQ_API_KEY:-}" ]; then echo OPENAQ_API_KEY_PRESENT; else echo OPENAQ_API_KEY_MISSING; fi
# OPENAQ_API_KEY_MISSING

python scripts/check_openaq_coverage.py --metadata-only
# exited 2; expected without OPENAQ_API_KEY

set -a; source .env; set +a
python scripts/sync_openaq_metadata.py --dry-run --output tmp/openaq-metadata.json
# passed with approved network escalation; 52 locations and 256 sensors discovered

set -a; source .env; set +a
python scripts/check_openaq_coverage.py --modeled-available --output tmp/openaq-coverage.json
# passed with approved network escalation; 1 fresh station, 4 recent stations, RECENT_OBSERVED

python -m json.tool tmp/openaq-metadata.json
# passed

python -m json.tool tmp/openaq-coverage.json
# passed
```

## Exit criteria verification

- [x] All in-scope tasks are complete: scripts, docs, fixtures, tests, live OpenAQ validation, and live Open-Meteo validation were completed.
- [x] Relevant verification commands were run: required help commands and unit tests passed; live OpenAQ and live Open-Meteo validations passed.
- [x] `CHANGELOG.md` was updated: Phase 01 entry added.
- [x] `docs/phase-summaries/PHASE-01-summary.md` was written.
- [x] No future-phase work was introduced: no Docker, database, Kafka, API, forecasting, or frontend implementation was added.
- [x] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced: fixtures are offline schema fixtures; Open-Meteo output is labeled `openmeteo_cams` and `modeled`.

## Problems encountered and resolutions

- Pytest initially failed with `ModuleNotFoundError: No module named 'scripts'` because the repository skeleton had no Python package/test path setup. Added `scripts/__init__.py` and `tests/conftest.py`.
- Live Open-Meteo validation initially failed inside the sandbox due DNS/network restriction. Re-ran the same command with approved network escalation and it passed.
- Git staging initially failed because `.git/index.lock` could not be created under the sandbox. Re-ran the commit command with approved escalation and committed the implementation milestone.
- Live OpenAQ validation initially could not be run because `OPENAQ_API_KEY` was missing from the environment. The key was then added to local `.env`, live validation was rerun, and the result was documented.

## Deviations from the phase plan

- Added `scripts/source_validation.py` to avoid duplicating adapter and normalization code across the three required scripts.
- Added `fixtures/sample_openmeteo_aq.json` so modeled fallback normalization is tested offline.
- Added `tests/conftest.py` because package/test path configuration does not exist until later foundation phases.
- These deviations are safe because they support Phase 01 only and do not alter the approved architecture.

## Known issues and technical debt

- Severity: Medium. Live Kathmandu observed coverage is sparse at this point in time: 1 fresh station and 4 recent stations. Later ingestion and dashboard phases must degrade to `RECENT_OBSERVED` or fallback modes instead of assuming dense live coverage.
- Severity: Low. The Phase 01 HTTP client is dependency-free and suitable for scripts, but future service clients should follow the system overview's `httpx` standard with service logging and health reporting.
- Severity: Low. The current coverage report samples a capped number of sensors by default to avoid excessive API calls; operators can raise `--max-sensors` when performing a full audit.

## What the next phase needs to know

- OpenAQ ingestion must remain sensor-based. Use the normalized `openaq_location_id` and `openaq_sensor_id` model from Phase 01 as the basis for the later `station_sensors` registry.
- Open-Meteo AQ is modeled fallback only. It must be stored separately in later phases and never labeled as observed.
- Demo replay strategy is historical or fixture data replayed through Kafka/Spark in later phases, not frontend-only fake data.
- Live OpenAQ coverage should be rerun before Phase 05 ingestion because public sensor freshness can change. Keep generated JSON reports out of Git.

## How to resume from scratch

```bash
python scripts/sync_openaq_metadata.py --dry-run --fixture-location fixtures/sample_openaq_location.json
python scripts/check_openaq_coverage.py --fixture-location fixtures/sample_openaq_location.json --fixture-measurement fixtures/sample_openaq_measurement.json
python scripts/check_openmeteo_aq.py --fixture fixtures/sample_openmeteo_aq.json
pytest tests/unit -q
```

For live OpenAQ validation:

```bash
# Set OPENAQ_API_KEY only in the local shell or ignored .env workflow.
python scripts/sync_openaq_metadata.py --dry-run --output tmp/openaq-metadata.json
python scripts/check_openaq_coverage.py --modeled-available --output tmp/openaq-coverage.json
```

## Next session prompt

```text
Follow AGENTS.md. Implement PHASE 02 only using docs/codex/phases/PHASE-02-infrastructure-foundation.md.
```
