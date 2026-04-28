# PHASE 13: Replay Demo Mode and Spatial Polish

Risk level: MEDIUM

Objective: Make demos reliable by replaying historical data through the pipeline and add advanced map layers without compromising provenance.

## Codex session prompt

```text
Follow AGENTS.md.

Implement PHASE 13: Replay Demo Mode and Spatial Polish only.

Before editing code, read:
- docs/himalayaair-system-overview.md
- docs/codex/PHASE_INDEX.md
- docs/codex/phases/PHASE-13-demo-spatial-polish.md
- CHANGELOG.md if it exists
- prior summaries in docs/phase-summaries/ if they exist

Do not implement future phases. Do not change the approved architecture unless this phase file explicitly requires it.

At the end, run the verification commands, update CHANGELOG.md, write the phase summary, and report changed files, pass/fail results, and remaining risks.
```

## Entry criteria

- [ ] Phase 12 complete.
- [ ] Kafka, Spark, API, and frontend core are functional or fixture-compatible.

## Scope

- Create services/replay-publisher.
- Replay historical or fixture readings into raw-aq-readings with observation_type=replay.
- Add frontend Demo Mode controls that display REPLAY_DEMO state.
- Implement IDW heatmap raster/image layer.
- Implement fire events overlay.
- Implement cigarette equivalence counter.
- Implement wind rose if weather data supports it.
- Keep 3D terrain optional and only after core demo works.

## Do not do in this phase

- Do not create a frontend-only fake replay unless explicitly marked temporary.
- Do not hide replay provenance.
- Do not implement 3D terrain before replay and IDW are stable.

## Implementation tasks

- Implement replay publisher CLI with start, end, speed, loop, and dry-run options.
- Update API and frontend so replay data is visible and labeled.
- Render IDW grid from compact API response without bloated GeoJSON.
- Add manual demo script in docs/demo-script.md.

## Verification commands

Run the commands that apply to the current environment. If a command cannot run because infrastructure or credentials are unavailable, record the reason in the phase summary.

```bash
python -m services.replay_publisher.main --help
python -m services.replay_publisher.main --dry-run --fixture fixtures/replay_sample.json
npm --prefix frontend run build
```

## Required changelog entry

Add a CHANGELOG.md entry with header `PHASE-13 Replay Demo Mode and Spatial Polish` and include files changed, reason, impact, and verification performed.

## Required phase summary

Create `docs/phase-summaries/PHASE-13-summary.md` using `docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md`.

## Exit criteria

- [ ] All in-scope tasks are complete or explicitly documented as deferred within this phase.
- [ ] Relevant verification commands were run or blocked reasons were documented.
- [ ] CHANGELOG.md was updated.
- [ ] docs/phase-summaries/PHASE-13-summary.md was written.
- [ ] No future-phase work was introduced.
- [ ] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Deliverable

A reliable demo mode that exercises the real pipeline and keeps the dashboard impressive even when live data is sparse.
