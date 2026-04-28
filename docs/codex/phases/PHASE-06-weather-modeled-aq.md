# PHASE 06: Weather and Modeled AQ Fallback

Risk level: MEDIUM

Objective: Ingest Open-Meteo weather and modeled AQ data as a clearly labeled fallback source.

## Codex session prompt

```text
Follow AGENTS.md.

Implement PHASE 06: Weather and Modeled AQ Fallback only.

Before editing code, read:
- docs/himalayaair-system-overview.md
- docs/codex/PHASE_INDEX.md
- docs/codex/phases/PHASE-06-weather-modeled-aq.md
- CHANGELOG.md if it exists
- prior summaries in docs/phase-summaries/ if they exist

Do not implement future phases. Do not change the approved architecture unless this phase file explicitly requires it.

At the end, run the verification commands, update CHANGELOG.md, write the phase summary, and report changed files, pass/fail results, and remaining risks.
```

## Entry criteria

- [ ] Phase 05 complete.
- [ ] weather_locations table is seeded.

## Scope

- Create services/weather-poller service.
- Poll Open-Meteo weather every 15 minutes and write weather_readings.
- Poll Open-Meteo air quality for modeled PM2.5, PM10, gases, and US AQI where available.
- Write modeled_aq_readings with source=openmeteo_cams and observation_type=modeled.
- Publish optional weather-data and modeled-aq-data Kafka messages.
- Expose GET /health on port 9091.

## Do not do in this phase

- Do not label Open-Meteo modeled AQ as observed.
- Do not use modeled data to overwrite observed data.
- Do not require API keys for Open-Meteo unless the user explicitly configures commercial access.

## Implementation tasks

- Implement Open-Meteo clients with typed normalized outputs.
- Implement idempotent DB writes for weather and modeled AQ.
- Implement quality flags for missing values and partial API responses.
- Update API-facing coverage helpers if they exist.

## Verification commands

Run the commands that apply to the current environment. If a command cannot run because infrastructure or credentials are unavailable, record the reason in the phase summary.

```bash
python -m services.weather_poller.main --once --dry-run
curl -fsS http://localhost:9091/health || true
pytest tests/weather -q
```

## Required changelog entry

Add a CHANGELOG.md entry with header `PHASE-06 Weather and Modeled AQ Fallback` and include files changed, reason, impact, and verification performed.

## Required phase summary

Create `docs/phase-summaries/PHASE-06-summary.md` using `docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md`.

## Exit criteria

- [ ] All in-scope tasks are complete or explicitly documented as deferred within this phase.
- [ ] Relevant verification commands were run or blocked reasons were documented.
- [ ] CHANGELOG.md was updated.
- [ ] docs/phase-summaries/PHASE-06-summary.md was written.
- [ ] No future-phase work was introduced.
- [ ] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Deliverable

Weather readings and modeled baseline AQ data available for fallback rendering and forecasts.
