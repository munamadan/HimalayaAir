# PHASE 01: Data Reality Check and Source Validation

Risk level: HIGH

Objective: Validate that Kathmandu data sources are reachable and produce a documented coverage report before building the pipeline.

## Codex session prompt

```text
Follow AGENTS.md.

Implement PHASE 01: Data Reality Check and Source Validation only.

Before editing code, read:
- docs/himalayaair-system-overview.md
- docs/codex/PHASE_INDEX.md
- docs/codex/phases/PHASE-01-data-reality-check.md
- CHANGELOG.md if it exists
- prior summaries in docs/phase-summaries/ if they exist

Do not implement future phases. Do not change the approved architecture unless this phase file explicitly requires it.

At the end, run the verification commands, update CHANGELOG.md, write the phase summary, and report changed files, pass/fail results, and remaining risks.
```

## Entry criteria

- [ ] Phase 00 complete.
- [ ] .env.example exists and documents OPENAQ_API_KEY and FIRMS_MAP_KEY.

## Scope

- Create scripts/sync_openaq_metadata.py with a dry-run mode.
- Create scripts/check_openaq_coverage.py for Kathmandu bounding box coverage.
- Create scripts/check_openmeteo_aq.py for modeled AQ availability.
- Create docs/data-source-validation.md with expected outputs and manual run instructions.
- Create fixtures/sample_openaq_location.json and fixtures/sample_openaq_measurement.json for tests.
- Add unit tests for source response normalization without requiring network access.

## Do not do in this phase

- Do not require Docker.
- Do not write to TimescaleDB yet.
- Do not assume hardcoded OpenAQ station IDs are valid.

## Implementation tasks

- Implement OpenAQ metadata discovery client using a typed adapter and timeout-aware HTTP calls.
- Normalize OpenAQ locations into logical stations and sensors in plain Python data classes or Pydantic models.
- Produce a coverage report showing locations found, sensors found, pollutants, freshness, and recommended coverage mode.
- Implement offline tests using fixtures.

## Verification commands

Run the commands that apply to the current environment. If a command cannot run because infrastructure or credentials are unavailable, record the reason in the phase summary.

```bash
python scripts/check_openaq_coverage.py --help
python scripts/check_openmeteo_aq.py --help
pytest tests/unit -q
```

## Required changelog entry

Add a CHANGELOG.md entry with header `PHASE-01 Data Reality Check and Source Validation` and include files changed, reason, impact, and verification performed.

## Required phase summary

Create `docs/phase-summaries/PHASE-01-summary.md` using `docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md`.

## Exit criteria

- [ ] All in-scope tasks are complete or explicitly documented as deferred within this phase.
- [ ] Relevant verification commands were run or blocked reasons were documented.
- [ ] CHANGELOG.md was updated.
- [ ] docs/phase-summaries/PHASE-01-summary.md was written.
- [ ] No future-phase work was introduced.
- [ ] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Deliverable

A repeatable data-source validation workflow and a written report template that prevents building against imaginary sensor coverage.
