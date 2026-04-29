# PHASE-05 Summary - OpenAQ Sensor-Based Live Ingestion

## What was built

- `services/openaq_poller/`: OpenAQ live poller package with configuration, database registry reads, OpenAQ sensor measurement polling, Kafka publishing, poll-window handling, health state, and CLI loop.
- `services/openaq_poller/Dockerfile`: Buildable Python runtime for the observed-profile service.
- `docker-compose.yml`: Real `openaq-poller` service on the `observed` profile with TimescaleDB/Kafka dependencies and `/health` on port `9090`.
- `.env.example`: Non-secret OpenAQ poller runtime settings.
- `requirements.txt`: Added `httpx` for the service HTTP client.
- `scripts/source_validation.py`: Treats recognized AQ sensors as pollable even when OpenAQ omits last-seen metadata.
- `scripts/verify_kafka.py`: Supports validating existing topic messages through `--max-messages`.
- `scripts/verify_env.sh`: Includes TimescaleDB in observed-profile checks.
- `shared/logging_config.py`: Keeps noisy HTTP client logs out of service output.
- `tests/openaq/`: Focused OpenAQ poller tests.
- `tests/unit/test_source_validation.py`: Added coverage for pollable AQ sensors without last-seen metadata.

## Current system state

The OpenAQ poller can run with:

```bash
python -m services.openaq_poller.main --once --dry-run
python -m services.openaq_poller.main
```

The local database was populated from live OpenAQ metadata during verification: 52 stations and 256 sensors were upserted. Of those, 106 sensors are marked active, and 4 active station/sensor pairs are currently pollable through the Phase 05 query. A capped live poll published 10 observed PM2.5 messages to `raw-aq-readings` with `source=openaq_live` and `observation_type=observed`.

No Spark persistence, API endpoint, frontend behavior, weather fallback, forecasting, or future-phase work was introduced.

## Commands run

```bash
python -m py_compile services/openaq_poller/*.py scripts/verify_kafka.py
# passed

docker compose --profile observed config --quiet
# failed first due missing observed-profile TimescaleDB dependency
# passed after compose profile wiring fix

pytest tests/openaq -q
# passed: 7 tests

pytest tests/unit tests/openaq -q
# passed: 19 tests

python -m services.openaq_poller.main --once --dry-run
# failed first in sandbox because local DB access was blocked
# passed with approved DB access
# passed again after metadata sync with 4 sensors discovered and API calls skipped because the shell did not load OPENAQ_API_KEY

curl -fsS http://localhost:9090/health || true
# failed when no poller was running
# passed after starting the poller dry-run loop; returned status=ok

python scripts/verify_kafka.py --topic raw-aq-readings --max-messages 10 || true
# failed first in sandbox because Kafka socket access was blocked
# passed with approved Kafka access; validated replay and live observed OpenAQ messages

python scripts/verify_kafka.py --fixture fixtures/sample_raw_aq_message.json
# failed first in sandbox because Kafka socket access was blocked
# passed with approved Kafka access

set -a; source .env; set +a; python scripts/sync_openaq_metadata.py --write-db --output tmp/openaq-phase05-metadata-write.json
# failed first in sandbox because DNS/network access was blocked
# passed with approved network and DB access; upserted 52 stations and 256 sensors

OPENAQ_MAX_SENSORS=5 OPENAQ_MEASUREMENTS_LIMIT=10 OPENAQ_MAX_PAGES=1 OPENAQ_FALLBACK_LOOKBACK_HOURS=24 OPENAQ_POLL_OVERLAP_MINUTES=1440 python -m services.openaq_poller.main --once
# passed with approved network, DB, and Kafka access
# published 10 openaq_live / observed messages
```

## Exit criteria verification

- [x] All in-scope tasks are complete: sensor-based polling, OpenAQ client retry/rate-limit handling, Kafka publishing, `pipeline_runs`, health endpoint, structured logs, compose wiring, and tests are implemented.
- [x] Relevant verification commands were run: required dry-run, health curl, Kafka verification, and `pytest tests/openaq -q` were run with results documented.
- [x] `CHANGELOG.md` was updated with the Phase 05 entry.
- [x] `docs/phase-summaries/PHASE-05-summary.md` was written.
- [x] No future-phase work was introduced: no Spark, API, frontend, weather fallback, forecasting, or Airflow work was added.
- [x] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Problems encountered and resolutions

- Sandbox blocked local DB, Kafka socket, and external network access. The same verification commands passed with approved escalation.
- Current OpenAQ location metadata omitted sensor last-seen timestamps, which initially marked all synced sensors inactive. Recognized AQ pollutants are now kept pollable while non-AQ fields remain inactive.
- A zero-sensor run initially advanced the poll watermark. The poller now ignores zero-sensor runs when selecting the next successful window.
- The health curl naturally failed before a long-running poller was started. A dry-run loop was started briefly, `/health` was verified, and the process was stopped.

## Deviations from the phase plan

- Added `OPENAQ_MAX_SENSORS` to cap live polling during verification and laptop runs.
- Updated `scripts/verify_kafka.py` so the exact Phase 05 verification command can validate existing topic messages without requiring a fixture.
- Populated the local registry with live OpenAQ metadata as an operational verification step; the generated report remains ignored under `tmp/`.

## Known issues and technical debt

- Severity: Medium. Current live observed OpenAQ coverage is sparse: only 4 active station/sensor pairs are pollable in the local registry, and the live published records were recent observed historical measurements rather than fresh sub-hour readings.
- Severity: Low. The poller publishes raw observed messages only; persistence to TimescaleDB remains Phase 07 Spark work.
- Severity: Low. Docker image build was compose-config validated but not built in this session to avoid unnecessary dependency downloads after local Python verification passed.

## What the next phase needs to know

- The OpenAQ poller is sensor-based and publishes only `openaq_live` / `observed` messages to `raw-aq-readings`.
- `OPENAQ_API_KEY` remains server-side only. Dry-run without a loaded key skips OpenAQ calls visibly in logs and health details.
- `OPENAQ_MAX_SENSORS` can be used for capped verification; leave it `0` for no configured limit.
- Local Kafka now contains replay fixture messages and live observed OpenAQ messages from Phase 05 verification.

## How to resume from scratch

```bash
docker compose --profile core --profile observed up -d
set -a; source .env; set +a; python scripts/sync_openaq_metadata.py --write-db --output tmp/openaq-metadata.json
python -m services.openaq_poller.main --once --dry-run
set -a; source .env; set +a; OPENAQ_MAX_SENSORS=5 OPENAQ_MEASUREMENTS_LIMIT=10 OPENAQ_MAX_PAGES=1 python -m services.openaq_poller.main --once
python scripts/verify_kafka.py --topic raw-aq-readings --max-messages 10
pytest tests/openaq -q
```

## Next session prompt

```text
Follow AGENTS.md. Implement PHASE 06 only using docs/codex/phases/PHASE-06-weather-modeled-aq.md.
```

