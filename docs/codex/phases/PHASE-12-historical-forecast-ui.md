# PHASE 12: Historical Explorer and Forecast UI

Risk level: MEDIUM

Objective: Add historical analysis, calendar heatmap, event annotations, zoomable time series, and forecast visualization.

## Codex session prompt

```text
Follow AGENTS.md.

Implement PHASE 12: Historical Explorer and Forecast UI only.

Before editing code, read:
- docs/himalayaair-system-overview.md
- docs/codex/PHASE_INDEX.md
- docs/codex/phases/PHASE-12-historical-forecast-ui.md
- CHANGELOG.md if it exists
- prior summaries in docs/phase-summaries/ if they exist

Do not implement future phases. Do not change the approved architecture unless this phase file explicitly requires it.

At the end, run the verification commands, update CHANGELOG.md, write the phase summary, and report changed files, pass/fail results, and remaining risks.
```

## Entry criteria

- [ ] Phase 11 complete.
- [ ] API endpoints for valley history, station history, events, and forecasts exist.

## Scope

- Implement HistoricalExplorer view.
- Implement D3 calendar heatmap.
- Implement D3 zoomable and brushable time-series chart.
- Implement Tihar, monsoon, COVID, and fire annotation toggles where data exists.
- Implement ForecastPanel with 72h confidence band and best time windows.
- Use loading, empty, degraded, and error states consistently.

## Do not do in this phase

- Do not fetch unbounded historical data.
- Do not make missing data look like clean air.
- Do not mix D3 DOM ownership with React state carelessly.

## Implementation tasks

- Implement bounded API queries with date controls.
- Implement calendar cells with no-data state.
- Implement forecast chart labels for model_source and fallback_reason.
- Add manual QA notes to phase summary.

## Verification commands

Run the commands that apply to the current environment. If a command cannot run because infrastructure or credentials are unavailable, record the reason in the phase summary.

```bash
npm --prefix frontend run build
npm --prefix frontend run lint || true
```

## Required changelog entry

Add a CHANGELOG.md entry with header `PHASE-12 Historical Explorer and Forecast UI` and include files changed, reason, impact, and verification performed.

## Required phase summary

Create `docs/phase-summaries/PHASE-12-summary.md` using `docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md`.

## Exit criteria

- [ ] All in-scope tasks are complete or explicitly documented as deferred within this phase.
- [ ] Relevant verification commands were run or blocked reasons were documented.
- [ ] CHANGELOG.md was updated.
- [ ] docs/phase-summaries/PHASE-12-summary.md was written.
- [ ] No future-phase work was introduced.
- [ ] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Deliverable

A historical and forecast experience suitable for final-year defense storytelling.
