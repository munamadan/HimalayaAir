# PHASE 05: OpenAQ Sensor-Based Live Ingestion

Risk level: HIGH

Objective: Poll OpenAQ by sensor, publish observed readings to Kafka, and expose a poller health endpoint.

## Codex session prompt

```text
Follow AGENTS.md.

Implement PHASE 05: OpenAQ Sensor-Based Live Ingestion only.

Before editing code, read:
- docs/himalayaair-system-overview.md
- docs/codex/PHASE_INDEX.md
- docs/codex/phases/PHASE-05-openaq-live-ingestion.md
- CHANGELOG.md if it exists
- prior summaries in docs/phase-summaries/ if they exist

Do not implement future phases. Do not change the approved architecture unless this phase file explicitly requires it.

At the end, run the verification commands, update CHANGELOG.md, write the phase summary, and report changed files, pass/fail results, and remaining risks.
```

## Entry criteria

- [ ] Phase 04 complete.
- [ ] station_sensors table exists.
- [ ] OPENAQ_API_KEY is documented and optional dry-run behavior exists.

## Scope

- Create services/openaq-poller service.
- Poll active station_sensors using sensor measurement endpoints.
- Use X-API-Key server-side only.
- Use datetime_from/datetime_to overlap windows and pagination.
- Publish normalized observed messages to raw-aq-readings.
- Write poller status into pipeline_runs.
- Expose GET /health on port 9090.
- Handle 429 rate-limit headers and network failures.

## Do not do in this phase

- Do not poll by OpenAQ location as the primary measurement source.
- Do not expose OPENAQ_API_KEY to frontend.
- Do not treat latest endpoint as complete ingestion source.

## Implementation tasks

- Implement OpenAQ client with retry, timeout, and rate-limit handling.
- Implement station_sensors query and last_success overlap logic.
- Implement normalized Kafka publishing with station_id, sensor_id, external_sensor_id, pollutant, timestamp, source, and observation_type.
- Implement health endpoint and structured logging.

## Verification commands

Run the commands that apply to the current environment. If a command cannot run because infrastructure or credentials are unavailable, record the reason in the phase summary.

```bash
python -m services.openaq_poller.main --once --dry-run
curl -fsS http://localhost:9090/health || true
python scripts/verify_kafka.py --topic raw-aq-readings --max-messages 10 || true
pytest tests/openaq -q
```

## Required changelog entry

Add a CHANGELOG.md entry with header `PHASE-05 OpenAQ Sensor-Based Live Ingestion` and include files changed, reason, impact, and verification performed.

## Required phase summary

Create `docs/phase-summaries/PHASE-05-summary.md` using `docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md`.

## Exit criteria

- [ ] All in-scope tasks are complete or explicitly documented as deferred within this phase.
- [ ] Relevant verification commands were run or blocked reasons were documented.
- [ ] CHANGELOG.md was updated.
- [ ] docs/phase-summaries/PHASE-05-summary.md was written.
- [ ] No future-phase work was introduced.
- [ ] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Deliverable

Live observed OpenAQ readings entering Kafka through the corrected sensor registry model.
