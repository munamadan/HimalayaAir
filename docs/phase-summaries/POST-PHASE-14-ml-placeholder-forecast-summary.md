# POST-PHASE-14 Summary - Forced 48-Hour ML Placeholder Forecast

## What was built

- Added a demo-only forced forecast model path for `hist_gradient_boosting_placeholder`.
- Changed the default forecast horizon from 72 hours to 48 hours.
- Added `FORECAST_FORCE_MODEL=ml_placeholder` as the only way to select the placeholder path.
- Added a deterministic untrained ML-style forecast builder using lag AQI, rolling AQI, diurnal adjustment, weather adjustment, modeled AQ input, station offset, and horizon-based uncertainty.
- Kept normal forecast arbitration unchanged when the placeholder is not forced: SARIMAX, then modeled AQ bias, then persistence.
- Added tests for forced selection, output shape, labels, deterministic behavior, and placeholder feature contents.

## Current system state

- The placeholder forecast is not trained and does not claim predictive accuracy.
- Forced placeholder output is labeled through `model_name`, `model_source`, and `fallback_reason`.
- The API contract is unchanged; forecast responses already carry the provenance fields needed for honest display.
- No frontend files were changed.

## Commands run

```bash
python -m py_compile services/forecasting/*.py
# passed

pytest tests/forecasting -q
# passed: 13 tests

pytest -q
# passed: 77 tests

docker compose --profile core config --quiet
# passed

FORECAST_FORCE_MODEL=ml_placeholder FORECAST_HORIZON_HOURS=48 timeout 20s python -m services.forecasting.run_once --dry-run
# passed: two stations selected the labeled placeholder and the dry run completed successfully

git diff --check
# passed
```

## Problems encountered and resolutions

- The repository already had unrelated uncommitted frontend and API changes. Forecast changes were implemented without touching frontend files, and commits need to stage only the forecast-related files.

## Deviations from the original plan

- The frontend was not updated because the latest instruction explicitly said not to change frontend files. The existing API response already exposes `model`, `model_source`, and `fallback_reason` for any frontend/report screenshot that needs honest labeling.

## Known issues and technical debt

- Severity: Medium. The placeholder path is useful for demonstrating the forecasting pipeline, but it must never be described as a trained or evaluated ML model.
- Severity: Medium. `FORECAST_FORCE_MODEL=ml_placeholder` bypasses normal arbitration; it should be used only for demo/report runs.
- Severity: Low. The current frontend does not render forecast model provenance, even though the API returns it.

## What the next session needs to know

- To produce the placeholder demo forecast, run forecast recompute with `FORECAST_FORCE_MODEL=ml_placeholder` and `FORECAST_HORIZON_HOURS=48`.
- Remove or unset `FORECAST_FORCE_MODEL` to return to normal SARIMAX/modeled/persistence arbitration.
- If the report includes metrics, do not present placeholder MAE/RMSE as learned-model performance.

## Resume commands

```bash
pytest tests/forecasting -q
FORECAST_FORCE_MODEL=ml_placeholder FORECAST_HORIZON_HOURS=48 python -m services.forecasting.run_once --dry-run
docker compose --profile core config --quiet
```
