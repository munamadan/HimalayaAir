# PHASE-06 Summary - Weather and Modeled AQ Fallback

## What was built

- `services/weather_poller/`: Open-Meteo poller package with configuration, typed models, retrying weather and air-quality clients, normalization, DB writes, optional Kafka diagnostic publishing, CLI loop, and health server.
- `services/weather_poller/Dockerfile`: Runtime image for both weather-profile Open-Meteo services.
- `docker-compose.yml`: Real `weather-poller` and `openmeteo-aq-poller` services on the `weather` profile. `weather-poller` serves `/health` on host port `9091`; `openmeteo-aq-poller` has an internal healthcheck on `9092`.
- `.env.example`: Non-secret Open-Meteo poller configuration and `WEATHER_POLLER_HOST_PORT`.
- `db/alembic/versions/0006_weather_modeled_quality_flags.py`: `quality_flag` columns and checks for `weather_readings` and `modeled_aq_readings`.
- `scripts/verify_db_schema.py`: Verification now checks the Phase 06 quality constraints.
- `shared/kafka/messages.py`: Weather and modeled AQ messages include `quality_flag`.
- `tests/weather/test_weather_poller.py`: Unit tests for normalization, provenance, quality flags, diagnostic messages, and retry behavior.
- `CHANGELOG.md`: Phase 06 implementation and verification history.

## Current system state

The local database is upgraded to Alembic revision `0006_weather_quality_flags`.

The Phase 06 poller can run both components together from the host:

```bash
python -m services.weather_poller.main --once --dry-run
python -m services.weather_poller.main --once
python -m services.weather_poller.main
```

The Compose weather profile keeps the approved two-service shape:

- `weather-poller`: `WEATHER_POLL_COMPONENTS=weather`, direct writes to `weather_readings`, health on `9091`.
- `openmeteo-aq-poller`: `WEATHER_POLL_COMPONENTS=modeled_aq`, direct writes to `modeled_aq_readings`, internal health on `9092`.
- `timescaledb`: included in the `weather` profile.

A live local run inserted 480 weather rows and 2,880 modeled AQ rows for the five seeded weather locations. A second live run in the same model-run hour inserted 0 duplicate rows. A read-only verification query confirmed:

- 480 rows with `source='openmeteo_weather'` and `quality_flag='complete'`.
- 2,880 rows with `source='openmeteo_cams'`, `observation_type='modeled'`, `coverage_mode='MODELED_BASELINE'`, and `quality_flag='complete'`.

No Spark processing, FastAPI endpoint, frontend behavior, forecasting model, Airflow DAG, backfill workflow, or observed-AQ overwrite path was introduced.

## Commands run

```bash
python -m py_compile services/weather_poller/*.py shared/kafka/messages.py db/alembic/versions/0006_weather_modeled_quality_flags.py scripts/verify_db_schema.py
# passed

pytest tests/weather -q
# passed: 5 tests

pytest tests/unit tests/weather -q
# passed: 17 tests

docker compose --profile weather config --quiet
# passed

docker compose --profile weather config --services | sort
# passed; listed openmeteo-aq-poller, timescaledb, weather-poller

docker compose --profile full config --quiet
# passed

python -m services.weather_poller.main --once --dry-run
# failed first in the sandbox because local DB access was blocked
# passed with approved DB/network access; normalized 480 weather and 2,880 modeled AQ rows

PATH="$HOME/.local/bin:$PATH" alembic upgrade head
# failed first in the sandbox because local DB access was blocked
# failed next because the initial revision id was longer than alembic_version.version_num VARCHAR(32)
# passed after shortening the revision id to 0006_weather_quality_flags

python -m services.weather_poller.main --once
# passed with approved DB/network access; inserted 3,360 rows

python -m services.weather_poller.main --once
# passed with approved DB/network access; inserted 0 rows on the second same-hour run

python scripts/verify_db_schema.py
# failed first in the sandbox because local DB access was blocked
# passed with approved DB access

curl -fsS http://localhost:9091/health || true
# failed first in the sandbox because local socket access was blocked
# passed with approved socket access while a dry-run poller loop was running; returned status=ok

python -c "..."
# read-only DB provenance query failed first in the sandbox because DB access was blocked
# passed with approved DB access; confirmed weather and modeled AQ provenance counts
```

## Exit criteria verification

- [x] All in-scope tasks are complete: Open-Meteo clients, typed normalized outputs, direct DB writes, modeled provenance, quality flags, optional Kafka diagnostics, Compose wiring, and health endpoint are implemented.
- [x] Relevant verification commands were run: required dry-run, health curl, and `pytest tests/weather -q` passed after documented approvals where needed.
- [x] `CHANGELOG.md` was updated with the Phase 06 entry.
- [x] `docs/phase-summaries/PHASE-06-summary.md` was written.
- [x] No future-phase work was introduced: no Spark, API, frontend, forecasting model, Airflow DAG, or backfill implementation was added.
- [x] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Problems encountered and resolutions

- Sandbox restrictions blocked local DB sockets, local health sockets, and external Open-Meteo calls. The same commands passed with approved escalation.
- The first migration revision id, `0006_weather_modeled_quality_flags`, exceeded the existing Alembic version column length. The migration id was shortened to `0006_weather_quality_flags` and rerun successfully.
- The Phase 03 schema did not include row-level quality flags for weather or modeled AQ data. A Phase 06 Alembic migration added constrained `quality_flag` columns instead of storing quality only in logs or health metadata.

## Deviations from the phase plan

- Kept both architecture service names in Compose by sharing one Python package between `weather-poller` and `openmeteo-aq-poller`.
- Kafka diagnostic publishing is implemented but disabled by default with `WEATHER_PUBLISH_KAFKA=false` so the direct DB path does not require Kafka for weather-profile operation.
- Ran one actual write poll and one idempotence poll in addition to the required dry-run verification.

## Known issues and technical debt

- Severity: Low. Optional Kafka diagnostics were schema/unit tested but not live-published because the direct DB write path is the Phase 06 delivery path and `WEATHER_PUBLISH_KAFKA` defaults to false.
- Severity: Low. Open-Meteo forecast values are inserted idempotently with `ON CONFLICT DO NOTHING`, so updated forecasts for the same weather timestamp are not overwritten in this phase.
- Severity: Low. The Open-Meteo AQ model run timestamp is the poll start hour, which keeps same-hour reruns idempotent while still allowing later model refreshes to coexist.

## What the next phase needs to know

- `modeled_aq_readings` now contains modeled fallback rows only. Do not mix them into observed `aq_readings`.
- Spark in Phase 07 should persist observed/replay AQ from Kafka to `aq_readings`; it does not need to consume weather or modeled AQ to satisfy Phase 06.
- `WEATHER_PUBLISH_KAFKA=true` can enable `weather-data` and `modeled-aq-data` diagnostics, but the weather profile does not start Kafka by default.
- Current local DB has Phase 06 live Open-Meteo rows from verification.

## How to resume from scratch

```bash
docker compose --profile core up -d
PATH="$HOME/.local/bin:$PATH" alembic upgrade head
python scripts/seed_weather_locations.py
python -m services.weather_poller.main --once --dry-run
python -m services.weather_poller.main --once
python scripts/verify_db_schema.py
pytest tests/weather -q
```

## Next session prompt

```text
Follow AGENTS.md. Implement PHASE 07 only using docs/codex/phases/PHASE-07-spark-stream-processing.md.
```
