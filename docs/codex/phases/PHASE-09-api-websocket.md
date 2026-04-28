# PHASE 09: FastAPI REST API and WebSocket Layer

Risk level: HIGH

Objective: Expose all core API endpoints, coverage-aware responses, IDW interpolation, health status, and WebSocket live feed.

## Codex session prompt

```text
Follow AGENTS.md.

Implement PHASE 09: FastAPI REST API and WebSocket Layer only.

Before editing code, read:
- docs/himalayaair-system-overview.md
- docs/codex/PHASE_INDEX.md
- docs/codex/phases/PHASE-09-api-websocket.md
- CHANGELOG.md if it exists
- prior summaries in docs/phase-summaries/ if they exist

Do not implement future phases. Do not change the approved architecture unless this phase file explicitly requires it.

At the end, run the verification commands, update CHANGELOG.md, write the phase summary, and report changed files, pass/fail results, and remaining risks.
```

## Entry criteria

- [ ] Phase 08 complete.
- [ ] Database has schema and at least fixture or real readings.

## Scope

- Create FastAPI app with Pydantic response models.
- Implement stations, station current, station history, valley current, valley history, interpolation, health advisory, events, pipeline health, and WebSocket endpoints.
- Return coverage_mode and confidence where live coverage may be sparse.
- Compute current state using latest reading per pollutant within freshness windows.
- Compute distance using geography, not raw degrees.
- Compute IDW using projected/local meter distances where practical.
- Start Kafka WebSocket consumer in a retrying background task without blocking API startup.

## Do not do in this phase

- Do not fail API startup just because Kafka is unavailable.
- Do not hide stale or modeled data provenance.
- Do not return raw geometry distance as kilometers.

## Implementation tasks

- Implement async SQLAlchemy session handling.
- Implement in-process TTL caches for station snapshots and IDW.
- Implement ConnectionManager with heartbeat and duplicate batch handling.
- Add API contract tests with fixture DB data.

## Verification commands

Run the commands that apply to the current environment. If a command cannot run because infrastructure or credentials are unavailable, record the reason in the phase summary.

```bash
pytest tests/api -q
uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload || true
curl -fsS http://localhost:8000/health || true
```

## Required changelog entry

Add a CHANGELOG.md entry with header `PHASE-09 FastAPI REST API and WebSocket Layer` and include files changed, reason, impact, and verification performed.

## Required phase summary

Create `docs/phase-summaries/PHASE-09-summary.md` using `docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md`.

## Exit criteria

- [ ] All in-scope tasks are complete or explicitly documented as deferred within this phase.
- [ ] Relevant verification commands were run or blocked reasons were documented.
- [ ] CHANGELOG.md was updated.
- [ ] docs/phase-summaries/PHASE-09-summary.md was written.
- [ ] No future-phase work was introduced.
- [ ] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Deliverable

A curl-testable backend API with live/degraded/modeled/replay provenance visible to clients.
