# PHASE 11: Frontend Core Dashboard

Risk level: MEDIUM

Objective: Build the React/Vite dashboard shell, live map markers, station popup, AQI gauge, PM2.5 chart, and WebSocket state updates.

## Codex session prompt

```text
Follow AGENTS.md.

Implement PHASE 11: Frontend Core Dashboard only.

Before editing code, read:
- docs/himalayaair-system-overview.md
- docs/codex/PHASE_INDEX.md
- docs/codex/phases/PHASE-11-frontend-core.md
- CHANGELOG.md if it exists
- prior summaries in docs/phase-summaries/ if they exist

Do not implement future phases. Do not change the approved architecture unless this phase file explicitly requires it.

At the end, run the verification commands, update CHANGELOG.md, write the phase summary, and report changed files, pass/fail results, and remaining risks.
```

## Entry criteria

- [ ] Phase 10 complete or API fixture mode is available.
- [ ] Frontend environment variables are documented.

## Scope

- Create Vite React app if not present.
- Implement API wrapper, hooks, dark design system, navigation, and loading states.
- Implement live map with Mapbox or MapLibre adapter.
- Implement station markers and station popup.
- Implement AQI badge/gauge and PM2.5 multi-station chart.
- Implement WebSocket hook with reconnection and pong response.
- Display coverage mode, confidence, and source provenance clearly.

## Do not do in this phase

- Do not use Redux.
- Do not reinitialize the map on every update.
- Do not put secrets in frontend env files.
- Do not add decorative emojis.

## Implementation tasks

- Create components and hooks with clear boundaries.
- Use native fetch wrapper and typed response assumptions.
- Add responsive layout for 375px width.
- Add frontend tests where tooling exists or document manual checks.

## Verification commands

Run the commands that apply to the current environment. If a command cannot run because infrastructure or credentials are unavailable, record the reason in the phase summary.

```bash
npm --prefix frontend install
npm --prefix frontend run build
npm --prefix frontend run lint || true
```

## Required changelog entry

Add a CHANGELOG.md entry with header `PHASE-11 Frontend Core Dashboard` and include files changed, reason, impact, and verification performed.

## Required phase summary

Create `docs/phase-summaries/PHASE-11-summary.md` using `docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md`.

## Exit criteria

- [ ] All in-scope tasks are complete or explicitly documented as deferred within this phase.
- [ ] Relevant verification commands were run or blocked reasons were documented.
- [ ] CHANGELOG.md was updated.
- [ ] docs/phase-summaries/PHASE-11-summary.md was written.
- [ ] No future-phase work was introduced.
- [ ] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Deliverable

A visually impressive live dashboard core that works with real or fixture API data.
