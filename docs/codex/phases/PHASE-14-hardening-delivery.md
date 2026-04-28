# PHASE 14: Hardening, Benchmarks, Documentation, and Delivery

Risk level: MEDIUM

Objective: Prepare the project for final defense, recruiter review, clean setup, benchmarks, screenshots, and reproducible operation.

## Codex session prompt

```text
Follow AGENTS.md.

Implement PHASE 14: Hardening, Benchmarks, Documentation, and Delivery only.

Before editing code, read:
- docs/himalayaair-system-overview.md
- docs/codex/PHASE_INDEX.md
- docs/codex/phases/PHASE-14-hardening-delivery.md
- CHANGELOG.md if it exists
- prior summaries in docs/phase-summaries/ if they exist

Do not implement future phases. Do not change the approved architecture unless this phase file explicitly requires it.

At the end, run the verification commands, update CHANGELOG.md, write the phase summary, and report changed files, pass/fail results, and remaining risks.
```

## Entry criteria

- [ ] Phase 13 complete.
- [ ] Core demo path works end to end.

## Scope

- Create query benchmarks for continuous aggregates versus raw queries.
- Create API load test for around 20 concurrent users.
- Complete README with architecture diagram, setup, env vars, commands, screenshots, and limitations.
- Create docs/benchmark-results.md.
- Create docs/final-defense-script.md.
- Run full verification from clean checkout assumptions.
- Clean stale TODOs and dead code.
- Review security and secret handling.

## Do not do in this phase

- Do not add major new features.
- Do not change architecture late unless fixing a real bug.
- Do not leave failing tests unexplained.

## Implementation tasks

- Implement benchmark scripts and record results.
- Write final documentation and limitation notes honestly.
- Run all available tests and builds.
- Create final phase summary and readiness checklist.

## Verification commands

Run the commands that apply to the current environment. If a command cannot run because infrastructure or credentials are unavailable, record the reason in the phase summary.

```bash
./scripts/verify_env.sh
pytest -q
npm --prefix frontend run build
python benchmarks/query_benchmark.py || true
```

## Required changelog entry

Add a CHANGELOG.md entry with header `PHASE-14 Hardening, Benchmarks, Documentation, and Delivery` and include files changed, reason, impact, and verification performed.

## Required phase summary

Create `docs/phase-summaries/PHASE-14-summary.md` using `docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md`.

## Exit criteria

- [ ] All in-scope tasks are complete or explicitly documented as deferred within this phase.
- [ ] Relevant verification commands were run or blocked reasons were documented.
- [ ] CHANGELOG.md was updated.
- [ ] docs/phase-summaries/PHASE-14-summary.md was written.
- [ ] No future-phase work was introduced.
- [ ] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Deliverable

A defense-ready, reproducible, documented HimalayaAir project with known limitations clearly stated.
