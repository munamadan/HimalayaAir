# PHASE 04: Kafka Topics and Shared Libraries

Risk level: MEDIUM

Objective: Create shared schemas, logging, settings, Kafka topic management, and reusable source-adapter foundations.

## Codex session prompt

```text
Follow AGENTS.md.

Implement PHASE 04: Kafka Topics and Shared Libraries only.

Before editing code, read:
- docs/himalayaair-system-overview.md
- docs/codex/PHASE_INDEX.md
- docs/codex/phases/PHASE-04-kafka-shared-libraries.md
- CHANGELOG.md if it exists
- prior summaries in docs/phase-summaries/ if they exist

Do not implement future phases. Do not change the approved architecture unless this phase file explicitly requires it.

At the end, run the verification commands, update CHANGELOG.md, write the phase summary, and report changed files, pass/fail results, and remaining risks.
```

## Entry criteria

- [ ] Phase 03 complete.
- [ ] Kafka and database services can be started or dry-run mode is documented.

## Scope

- Create shared Python package for settings, logging_config, time utilities, health payloads, and source enums.
- Define normalized message schemas for raw-aq-readings, weather-data, modeled-aq-data, processed-aq-readings, and DLQ messages.
- Create scripts/create_kafka_topics.sh with required topics and retention settings.
- Create scripts/verify_kafka.py for publishing and consuming fixture messages.
- Add unit tests for schema validation and serialization.

## Do not do in this phase

- Do not implement live OpenAQ polling yet.
- Do not implement Spark yet.
- Do not publish messages that lack source and observation_type.

## Implementation tasks

- Create Pydantic message models with schema_version fields.
- Add structlog configuration used by every Python service.
- Create Kafka producer and consumer helper functions with timeout and error logging.
- Document topic names and message keys.

## Verification commands

Run the commands that apply to the current environment. If a command cannot run because infrastructure or credentials are unavailable, record the reason in the phase summary.

```bash
./scripts/create_kafka_topics.sh
python scripts/verify_kafka.py --fixture fixtures/sample_raw_aq_message.json
pytest tests/unit -q
```

## Required changelog entry

Add a CHANGELOG.md entry with header `PHASE-04 Kafka Topics and Shared Libraries` and include files changed, reason, impact, and verification performed.

## Required phase summary

Create `docs/phase-summaries/PHASE-04-summary.md` using `docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md`.

## Exit criteria

- [ ] All in-scope tasks are complete or explicitly documented as deferred within this phase.
- [ ] Relevant verification commands were run or blocked reasons were documented.
- [ ] CHANGELOG.md was updated.
- [ ] docs/phase-summaries/PHASE-04-summary.md was written.
- [ ] No future-phase work was introduced.
- [ ] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Deliverable

A shared foundation so all services speak the same message and logging language.
