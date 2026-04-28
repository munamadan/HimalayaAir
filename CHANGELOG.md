# Changelog

All meaningful project changes are recorded here so future Codex sessions can resume with the implemented phase history.

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
