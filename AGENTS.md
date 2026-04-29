# AGENTS.md

You are working on HimalayaAir, a Kathmandu Valley air-quality intelligence platform.

This file is the standing instruction file for Codex. Follow it for every task in this repository. The product and architecture source of truth is `docs/himalayaair-system-overview.md`. The phase workflow source of truth is `docs/codex/PHASE_INDEX.md`.

## Required startup routine

Before making code changes in any Codex session:

1. Read this `AGENTS.md`.
2. Read `docs/himalayaair-system-overview.md` when the task touches architecture, data flow, schemas, APIs, services, forecasting, frontend behavior, or deployment.
3. Read `docs/codex/PHASE_INDEX.md`.
4. Read the current phase file under `docs/codex/phases/`.
5. Read `CHANGELOG.md` if it exists.
6. Read prior phase summaries under `docs/phase-summaries/` when they exist.

## One-phase-per-session rule

Implement exactly one phase per Codex session unless the user explicitly says otherwise.

Do not start future phases. Do not opportunistically build frontend while working on ingestion. Do not implement forecasting while working on API foundations. If useful supporting files are needed, create only the minimum required for the current phase.

When a phase is too large for one session, split it inside the same phase using TODOs or follow-up notes. Do not advance to the next phase until the current phase exit criteria are met.

## Authority order

When instructions conflict, follow this order:

1. The user's latest explicit instruction.
2. `docs/himalayaair-system-overview.md`.
3. The active phase file under `docs/codex/phases/`.
4. This `AGENTS.md`.
5. Existing code conventions in the repository.

Never silently override the approved architecture. If a requested change conflicts with the system overview, state the conflict and implement the smallest safe change.

## Engineering standards

Write like a senior engineer.

Prefer clear names, small functions, explicit types, narrow interfaces, and boring reliable code. Avoid clever abstractions. Keep the repository understandable for one final-year student maintaining the project under time pressure.

Avoid comments. Use naming and structure instead. If a comment is unavoidable, keep it short and explain why the code exists, not what the code literally does.

No emojis anywhere in backend code, database migrations, scripts, tests, logs, generated data, commit messages, documentation, or API responses. Frontend visible UI may use an emoji only when it is deliberately part of the design and there is no cleaner icon or text alternative.

## Non-negotiable project rules

- Preserve Kafka, Spark, Airflow, TimescaleDB/PostGIS, FastAPI, React, and provenance-aware data modes unless the user explicitly changes the architecture.
- All schema changes must use Alembic migrations.
- TimescaleDB hypertable unique constraints must include the time partition column.
- Every air-quality record must preserve source and observation type: observed, modeled, replay, or synthetic.
- Never fake live data without labeling it as replay, modeled, or synthetic.
- No secrets in code, tests, docs, logs, examples, screenshots, or frontend bundles.
- No direct `print()` in Python services. Use `structlog`.
- No bare `except`, `except: pass`, swallowed exceptions, or silent fallbacks.
- Every fallback must be visible through logs, API metadata, health status, or stored provenance.
- External API clients must use timeouts, retries, rate-limit handling where relevant, and typed normalized outputs.
- Update `CHANGELOG.md` for every meaningful change.
- Append a `CHANGELOG.md` entry when each phase is completed.
- Write a phase completion summary before ending a phase.
- Do not change `README.md` unless the user's latest explicit instruction asks for a README change.
- Commit changes early and often during implementation.
- Use lowercase commit messages unless the user explicitly requests another style.

## Approved source modes

Use these exact values where source mode appears in code, schemas, API responses, and UI copy:

- `LIVE_OBSERVED`
- `RECENT_OBSERVED`
- `MODELED_BASELINE`
- `REPLAY_DEMO`
- `STATION_ONLY`
- `NO_DATA`

Use these exact observation types in stored readings:

- `observed`
- `modeled`
- `replay`
- `synthetic`

## Architecture guardrails

OpenAQ ingestion is sensor-based, not location-based. Use a `station_sensors` registry and poll sensor measurement endpoints through a source adapter. OpenAQ API keys are server-side only.

Open-Meteo weather and air-quality data are allowed as modeled baseline and forecast fallback, but they must never be mislabeled as live observed sensor data.

Demo Mode must replay historical or fixture data through Kafka and Spark where practical. Do not implement a frontend-only fake demo unless the user explicitly requests a temporary UI prototype.

Forecasting must use model arbitration:

1. SARIMAX when observed history and future weather covariates are sufficient.
2. Bias-adjusted modeled AQ fallback when modeled AQ forecast is available.
3. Persistence baseline when nothing else is reliable.

## Final response format for Codex sessions

End each session with:

- What changed.
- Files modified.
- Commands run and whether they passed.
- Phase exit criteria status.
- Known risks or follow-up items.
- Whether the next phase is safe to start.
