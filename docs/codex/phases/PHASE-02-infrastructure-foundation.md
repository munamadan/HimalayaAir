# PHASE 02: Infrastructure Foundation

Risk level: MEDIUM

Objective: Start the local infrastructure stack with Docker Compose profiles and health checks.

## Codex session prompt

```text
Follow AGENTS.md.

Implement PHASE 02: Infrastructure Foundation only.

Before editing code, read:
- docs/himalayaair-system-overview.md
- docs/codex/PHASE_INDEX.md
- docs/codex/phases/PHASE-02-infrastructure-foundation.md
- CHANGELOG.md if it exists
- prior summaries in docs/phase-summaries/ if they exist

Do not implement future phases. Do not change the approved architecture unless this phase file explicitly requires it.

At the end, run the verification commands, update CHANGELOG.md, write the phase summary, and report changed files, pass/fail results, and remaining risks.
```

## Entry criteria

- [ ] Phase 01 complete.
- [ ] Docker is available locally or the session records why checks cannot be run.

## Scope

- Create docker-compose.yml with profiles: core, stream, batch, weather, demo, full.
- Add TimescaleDB/PostGIS, Kafka, Airflow Postgres, Airflow, API placeholder, frontend placeholder, Spark placeholder services as appropriate.
- Add memory limits suitable for 8-16 GB laptops.
- Create scripts/verify_env.sh that checks service health.
- Create scripts/create_kafka_topics.sh but do not implement producers yet.
- Add .env.example with all required environment variable names and blank values.

## Do not do in this phase

- Do not implement application service logic.
- Do not put secrets in .env.example.
- Do not collapse Airflow metadata into SQLite.

## Implementation tasks

- Configure Airflow with PostgreSQL metadata database and LocalExecutor.
- Configure Kafka for single-broker local development.
- Add health checks for database, Kafka, Airflow, and placeholder app services.
- Document profile usage in README.

## Verification commands

Run the commands that apply to the current environment. If a command cannot run because infrastructure or credentials are unavailable, record the reason in the phase summary.

```bash
docker compose config
./scripts/verify_env.sh || true
./scripts/create_kafka_topics.sh --dry-run || true
```

## Required changelog entry

Add a CHANGELOG.md entry with header `PHASE-02 Infrastructure Foundation` and include files changed, reason, impact, and verification performed.

## Required phase summary

Create `docs/phase-summaries/PHASE-02-summary.md` using `docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md`.

## Exit criteria

- [ ] All in-scope tasks are complete or explicitly documented as deferred within this phase.
- [ ] Relevant verification commands were run or blocked reasons were documented.
- [ ] CHANGELOG.md was updated.
- [ ] docs/phase-summaries/PHASE-02-summary.md was written.
- [ ] No future-phase work was introduced.
- [ ] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Deliverable

A local infrastructure foundation that can be started by profile and checked by one script.
