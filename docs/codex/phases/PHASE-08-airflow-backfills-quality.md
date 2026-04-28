# PHASE 08: Airflow Backfills, Quality Checks, and FIRMS

Risk level: HIGH

Objective: Use Airflow for historical backfill, data quality, weather history, forecast scheduling hooks, and FIRMS fire events.

## Codex session prompt

```text
Follow AGENTS.md.

Implement PHASE 08: Airflow Backfills, Quality Checks, and FIRMS only.

Before editing code, read:
- docs/himalayaair-system-overview.md
- docs/codex/PHASE_INDEX.md
- docs/codex/phases/PHASE-08-airflow-backfills-quality.md
- CHANGELOG.md if it exists
- prior summaries in docs/phase-summaries/ if they exist

Do not implement future phases. Do not change the approved architecture unless this phase file explicitly requires it.

At the end, run the verification commands, update CHANGELOG.md, write the phase summary, and report changed files, pass/fail results, and remaining risks.
```

## Entry criteria

- [ ] Phase 07 complete.
- [ ] Airflow metadata Postgres is configured.
- [ ] Core tables exist.

## Scope

- Create Airflow DAGs for historical OpenAQ archive/API backfill, weather historical backfill, data quality checks, and FIRMS daily load.
- Use backfill_manifest for idempotency and auditability.
- Use OpenAQ archive-first approach where implemented, API fallback otherwise.
- Make station coverage DEGRADED instead of failing the whole DAG.
- Write all task outcomes to pipeline_runs.
- Use corrected fire_events schema with acquisition fields and event_hash.

## Do not do in this phase

- Do not use Airflow for 5-minute live ingestion.
- Do not make sparse station coverage a hard failure.
- Do not reduce FIRMS to only point plus date.

## Implementation tasks

- Implement DAGs with idempotent writes and structured logs.
- Implement data quality state reporting that returns healthy, degraded, or down.
- Implement FIRMS CSV parser with duplicate-resistant event_hash.
- Document manual trigger examples.

## Verification commands

Run the commands that apply to the current environment. If a command cannot run because infrastructure or credentials are unavailable, record the reason in the phase summary.

```bash
airflow dags list || true
python -m py_compile airflow/dags/*.py
pytest tests/airflow -q
```

## Required changelog entry

Add a CHANGELOG.md entry with header `PHASE-08 Airflow Backfills, Quality Checks, and FIRMS` and include files changed, reason, impact, and verification performed.

## Required phase summary

Create `docs/phase-summaries/PHASE-08-summary.md` using `docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md`.

## Exit criteria

- [ ] All in-scope tasks are complete or explicitly documented as deferred within this phase.
- [ ] Relevant verification commands were run or blocked reasons were documented.
- [ ] CHANGELOG.md was updated.
- [ ] docs/phase-summaries/PHASE-08-summary.md was written.
- [ ] No future-phase work was introduced.
- [ ] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Deliverable

A repeatable orchestration layer for historical data, quality status, and fire-event enrichment.
