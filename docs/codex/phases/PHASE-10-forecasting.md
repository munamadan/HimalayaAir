# PHASE 10: Forecasting and Accuracy Tracking

Risk level: HIGH

Objective: Generate reliable 72-hour forecasts using persistence, modeled bias adjustment, and SARIMAX when data supports it.

## Codex session prompt

```text
Follow AGENTS.md.

Implement PHASE 10: Forecasting and Accuracy Tracking only.

Before editing code, read:
- docs/himalayaair-system-overview.md
- docs/codex/PHASE_INDEX.md
- docs/codex/phases/PHASE-10-forecasting.md
- CHANGELOG.md if it exists
- prior summaries in docs/phase-summaries/ if they exist

Do not implement future phases. Do not change the approved architecture unless this phase file explicitly requires it.

At the end, run the verification commands, update CHANGELOG.md, write the phase summary, and report changed files, pass/fail results, and remaining risks.
```

## Entry criteria

- [ ] Phase 09 complete.
- [ ] weather_readings, modeled_aq_readings, and aq_hourly or equivalent history are available.

## Scope

- Implement forecast model arbitration.
- Implement persistence baseline that always returns a valid forecast.
- Implement bias-adjusted modeled AQ forecast when modeled future AQ exists.
- Implement SARIMAX only when observed history and future weather covariates are sufficient.
- Write forecast_runs and forecasts with model_source and fallback_reason.
- Compute forecast_accuracy retrospectively.
- Expose forecasts through existing API endpoint if not already complete.

## Do not do in this phase

- Do not silently fall back from SARIMAX.
- Do not train with 90 days AQ and only 7 days weather.
- Do not forecast with missing future exogenous variables.

## Implementation tasks

- Create services/forecasting package with model selection, persistence, modeled_bias, and sarimax modules.
- Create Airflow forecast_recompute DAG or update it if created in Phase 08.
- Add tests for arbitration logic and persistence output shape.
- Add forecast accuracy idempotency tests.

## Verification commands

Run the commands that apply to the current environment. If a command cannot run because infrastructure or credentials are unavailable, record the reason in the phase summary.

```bash
pytest tests/forecasting -q
python -m services.forecasting.run_once --dry-run
curl -fsS http://localhost:8000/api/forecasts/1 || true
```

## Required changelog entry

Add a CHANGELOG.md entry with header `PHASE-10 Forecasting and Accuracy Tracking` and include files changed, reason, impact, and verification performed.

## Required phase summary

Create `docs/phase-summaries/PHASE-10-summary.md` using `docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md`.

## Exit criteria

- [ ] All in-scope tasks are complete or explicitly documented as deferred within this phase.
- [ ] Relevant verification commands were run or blocked reasons were documented.
- [ ] CHANGELOG.md was updated.
- [ ] docs/phase-summaries/PHASE-10-summary.md was written.
- [ ] No future-phase work was introduced.
- [ ] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Deliverable

A forecast system that is always available, honest about model source, and measurable over time.
