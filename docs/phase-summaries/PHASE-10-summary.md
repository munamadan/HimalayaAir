# PHASE-10 Summary - Forecasting and Accuracy Tracking

## What was built

- `services/forecasting/`: Forecast settings, typed model context/results, model arbitration, persistence baseline, modeled AQ bias adjustment, SARIMAX wrapper, retrospective accuracy helpers, sync TimescaleDB repository, and `python -m services.forecasting.run_once`.
- `db/alembic/versions/0007_forecast_fallback_reason.py`: Adds `forecasts.fallback_reason`.
- `airflow/dags/forecast_recompute_hook.py`: Existing Phase 08 hook file now registers the hourly `forecast_recompute` DAG.
- `airflow/dags/himalayaair/forecast_hook.py`: Airflow task adapter for forecast recompute DAG conf.
- `services/api/`: Forecast response models, latest forecast repository query, service helper, and `GET /api/forecasts/{station_id}`.
- `docker-compose.yml`, `.env.example`, `requirements.txt`: Forecast runtime configuration and `statsmodels` dependency.
- `scripts/verify_db_schema.py`: Verifies the new forecast fallback column.
- `tests/forecasting/`: Arbitration, persistence output shape, modeled bias, and forecast accuracy idempotency tests.
- `tests/api/test_forecasts_contract.py`: Forecast API contract test.
- `CHANGELOG.md`: Phase 10 changelog entry.

## Current system state

The local database is upgraded to Alembic revision `0007_forecast_fallback_reason`.

The forecast runner can be called with:

```bash
python -m services.forecasting.run_once --dry-run
python -m services.forecasting.run_once
```

The latest local write created forecast run `3`, attempted 2 active stations, succeeded for both, and wrote 144 forecast rows. The current local data selected persistence with `model_source=persistence_openmeteo_cams` because 90-day observed AQ history is insufficient, historical weather coverage is only 2.6 percent, future weather is incomplete, and only 39 of 72 modeled AQ forecast hours are available. This is an honest fallback, not a silent SARIMAX downgrade.

`GET /api/forecasts/1` returns a 72-hour forecast with `model`, `model_source`, `fallback_reason`, bounds, and `historical_mae` when available.

## Commands run

```bash
pytest tests/forecasting -q
# passed: 9 tests

python -m services.forecasting.run_once --dry-run
# failed first in sandbox due blocked local DB socket
# passed with approved DB access
# passed again after installing statsmodels

curl -fsS http://localhost:8000/api/forecasts/1
# failed first in sandbox due blocked local socket
# failed next because no API server was running
# passed against a temporary FastAPI server after writing a real forecast run

PATH="$HOME/.local/bin:$PATH" alembic upgrade head
# failed first in sandbox due blocked local DB socket
# passed with approved DB access

python scripts/verify_db_schema.py
# failed during a parallel race before migration completion
# passed after rerun and verified forecasts.fallback_reason

python -m pip install --user "statsmodels>=0.14,<1.0"
# failed first under sandbox DNS restrictions
# passed with approved network access

python -m services.forecasting.run_once
# passed with approved DB access; latest run wrote 144 forecasts

python -m py_compile services/forecasting/*.py services/api/*.py airflow/dags/*.py airflow/dags/himalayaair/*.py db/alembic/versions/*.py scripts/verify_db_schema.py
# passed

pytest tests/api tests/forecasting -q
# passed: 22 tests

pytest tests/unit tests/openaq tests/weather tests/integration tests/airflow tests/api tests/forecasting -q
# passed: 63 tests

docker compose --profile core config --quiet
# passed

docker compose --profile batch config --quiet
# passed

docker compose --profile full config --quiet
# passed
```

## Exit criteria verification

- [x] All in-scope tasks are complete: model arbitration, persistence, modeled bias adjustment, SARIMAX module, forecast writes, accuracy computation, Airflow DAG, API endpoint, and tests are implemented.
- [x] Relevant verification commands were run: required pytest, dry-run, and curl checks passed after documented local approvals/setup.
- [x] `CHANGELOG.md` was updated with `PHASE-10 Forecasting and Accuracy Tracking`.
- [x] `docs/phase-summaries/PHASE-10-summary.md` was written.
- [x] No future-phase work was introduced: no frontend, replay UI, historical explorer UI, or delivery hardening work was added.
- [x] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced: modeled data remains in `modeled_aq_readings`, persistence fallback exposes `model_source` and `fallback_reason`, and the synthetic seed is labeled only as a forecast baseline source when no AQ baseline exists.

## Problems encountered and resolutions

- Sandbox restrictions blocked local DB, local HTTP socket, and PyPI access. The same commands passed with approved escalation.
- The first schema verification ran in parallel with Alembic and observed the pre-migration schema. Rerunning after migration completion passed.
- `execute_values` reported only the last insert page row count, so forecast write reporting initially showed 44 rows instead of 144. The repository now reports the number of rows submitted for the new forecast run.
- The forecast API initially selected an older same-hour run because it ordered only by `created_at`. It now orders by `created_at DESC, forecast_run_id DESC`.

## Deviations from the phase plan

- Kept the Phase 08 hook filename but changed the Airflow DAG id to `forecast_recompute`, which satisfies the Phase 10 DAG requirement without adding a duplicate hourly DAG.
- Added a migration for `forecasts.fallback_reason` because run-level fallback reasons are not enough when stations in the same run can use different models.
- Wrote a live local forecast run in addition to the required dry-run so the API endpoint could be curl-tested against real forecast rows.

## Known issues and technical debt

- Severity: Medium. The local database does not yet have sufficient 90-day observed AQ and aligned 90-day weather history for SARIMAX selection.
- Severity: Medium. Current local Open-Meteo future modeled AQ coverage is 39 of 72 hours, so the latest run uses persistence rather than modeled bias.
- Severity: Low. Forecast accuracy remains empty until elapsed forecast targets have matching observed AQ rows.
- Severity: Low. SARIMAX is implemented with a conservative non-seasonal order to keep laptop runtime practical; tune order/seasonality only after enough historical data exists.

## What the next phase needs to know

- Forecast API output is available at `/api/forecasts/{station_id}` and returns 72 rows when a forecast run exists.
- The forecast runner is safe to schedule hourly through Airflow and records visible fallback reasons.
- Install project requirements before expecting SARIMAX selection; `statsmodels` is now part of `requirements.txt` and Airflow `_PIP_ADDITIONAL_REQUIREMENTS`.
- The current local forecast rows are valid persistence forecasts, not SARIMAX forecasts, because data coverage is insufficient.

## How to resume from scratch

```bash
docker compose --profile core up -d timescaledb
PATH="$HOME/.local/bin:$PATH" alembic upgrade head
python -m pip install --user -r requirements.txt
python -m services.forecasting.run_once --dry-run
python -m services.forecasting.run_once
uvicorn services.api.main:app --host 0.0.0.0 --port 8000
curl -fsS http://localhost:8000/api/forecasts/1
pytest tests/forecasting -q
```

## Next session prompt

```text
Follow AGENTS.md. Implement PHASE 11 only using docs/codex/phases/PHASE-11-frontend-core.md.
```

