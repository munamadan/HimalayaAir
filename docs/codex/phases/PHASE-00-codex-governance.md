# PHASE 00: Codex Governance and Repository Contract

Risk level: LOW

Objective: Create the AI-readable project contract, documentation structure, changelog, and phase workflow before implementation starts.

## Codex session prompt

```text
Follow AGENTS.md.

Implement PHASE 00: Codex Governance and Repository Contract only.

Before editing code, read:
- docs/himalayaair-system-overview.md
- docs/codex/PHASE_INDEX.md
- docs/codex/phases/PHASE-00-codex-governance.md
- CHANGELOG.md if it exists
- prior summaries in docs/phase-summaries/ if they exist

Do not implement future phases. Do not change the approved architecture unless this phase file explicitly requires it.

At the end, run the verification commands, update CHANGELOG.md, write the phase summary, and report changed files, pass/fail results, and remaining risks.
```

## Entry criteria

- [ ] Repository exists or is initialized.
- [ ] The fixed HimalayaAir system overview is available in docs or provided by the user.

## Scope

- Create or update AGENTS.md at repository root.
- Create docs/himalayaair-system-overview.md if not already present.
- Create docs/codex/PHASE_INDEX.md and docs/codex/phases/ directory.
- Create CHANGELOG.md with Phase 00 header.
- Create docs/phase-summaries/ directory and a summary template.
- Create .gitignore, .env.example, README skeleton, and package/service folder skeletons only if the repo is empty.

## Do not do in this phase

- Do not implement Docker services.
- Do not create database migrations.
- Do not call external APIs.

## Implementation tasks

- Add root instructions for Codex and one-phase-per-session workflow.
- Add documentation directories and phase summary template.
- Add empty service directories for api, services, frontend, airflow, spark, and db only if they do not exist.
- Initialize changelog with the first entry.

## Verification commands

Run the commands that apply to the current environment. If a command cannot run because infrastructure or credentials are unavailable, record the reason in the phase summary.

```bash
test -f AGENTS.md
test -f docs/himalayaair-system-overview.md
test -f CHANGELOG.md
test -d docs/codex/phases
test -d docs/phase-summaries
```

## Required changelog entry

Add a CHANGELOG.md entry with header `PHASE-00 Codex Governance and Repository Contract` and include files changed, reason, impact, and verification performed.

## Required phase summary

Create `docs/phase-summaries/PHASE-00-summary.md` using `docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md`.

## Exit criteria

- [ ] All in-scope tasks are complete or explicitly documented as deferred within this phase.
- [ ] Relevant verification commands were run or blocked reasons were documented.
- [ ] CHANGELOG.md was updated.
- [ ] docs/phase-summaries/PHASE-00-summary.md was written.
- [ ] No future-phase work was introduced.
- [ ] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Deliverable

A repo that Codex can navigate safely, with phase instructions and documentation structure in place.
