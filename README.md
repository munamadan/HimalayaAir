# HimalayaAir

HimalayaAir is a Kathmandu Valley air-quality intelligence platform. The approved architecture is documented in `docs/himalayaair-system-overview.md`.

## Current Phase

Phase 00 establishes the repository contract for future Codex sessions. It does not implement services, database migrations, Docker infrastructure, ingestion, APIs, forecasting, or frontend behavior.

## Codex Workflow

Use one bounded Codex session per phase.

1. Read `AGENTS.md`.
2. Read `docs/himalayaair-system-overview.md`.
3. Read `docs/codex/PHASE_INDEX.md`.
4. Read the active phase file under `docs/codex/phases/`.
5. Read `CHANGELOG.md` and prior phase summaries.
6. Implement exactly one phase.
7. Run the phase verification commands.
8. Update `CHANGELOG.md`.
9. Write the phase summary.

The phase workflow source of truth is `docs/codex/PHASE_INDEX.md`.

## Repository Layout

```text
AGENTS.md                         Codex standing instructions
docs/himalayaair-system-overview.md Approved system architecture
docs/codex/PHASE_INDEX.md         Phase index
docs/codex/phases/                Per-phase implementation instructions
docs/phase-summaries/             Completed phase summaries
prompts/                          Copy-ready phase prompts
api/                              Future FastAPI service
services/                         Future pollers and replay services
frontend/                         Future React dashboard
airflow/                          Future DAGs and orchestration
spark/                            Future stream processing jobs
db/                               Future migrations and database assets
```

## Environment

Copy `.env.example` to `.env` locally when a future phase requires runtime configuration. Keep `.env` out of version control.

