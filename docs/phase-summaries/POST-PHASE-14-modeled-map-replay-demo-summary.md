# Post-Phase-14 Summary - Modeled Map Visibility and Replay Demo Reliability

## What was built

- `frontend/src/App.tsx`: Auto-enables the AQI heatmap when `/api/interpolation/current` returns a usable `MODELED_BASELINE` grid, unless the user has already changed the heatmap toggle in that browser session.
- `frontend/src/components/LiveMap.tsx`: Adds a compact `Modeled baseline map` chip, uses stronger raster opacity for modeled baseline grids, and keeps station WebGL layers above the raster.
- `frontend/src/services/mapEngine.ts`: Allows map adapters to update raster paint properties after a layer already exists.
- `frontend/src/styles/global.css`: Adds the modeled baseline map chip style.
- `services/replay_publisher/main.py`: Publishes replay fixture messages to Kafka topic `raw-aq-readings` by default, keeps direct DB ingestion behind `--publish-mode direct-db-fallback`, and adds `--rebase-to-now` so replay rows are current enough for defense-day API visibility while preserving `original_timestamp`.
- `tests/openaq/test_replay_direct_ingest.py`: Covers Kafka-first publishing, explicit direct DB fallback, and timestamp rebasing provenance.
- `docker-compose.yml`: Provides `SYNC_DATABASE_URL` to `replay-publisher` for explicit direct DB fallback.
- `scripts/run_replay_demo.sh`: Adds a single replay demo helper that starts `core` and `stream`, creates Kafka topics, dry-runs the fixture, publishes replay rows through Kafka, waits for Spark/API visibility, and verifies frontend reachability.
- `docs/demo-script.md` and `docs/final-defense-script.md`: Point the defense runbook at the Kafka-first helper and label direct DB ingestion as fallback only.
- `CHANGELOG.md`: Adds the post-Phase-14 changelog entry.

## Current system state

- Modeled AQ remains labeled `MODELED_BASELINE` and `modeled`; no modeled output is presented as live observed data.
- The map starts with the heatmap visible for modeled baseline interpolation, making sparse-coverage fallback visually legible without fabricating station data.
- Replay publisher default behavior is now Kafka-first: `replay-publisher -> raw-aq-readings -> Spark -> TimescaleDB -> FastAPI -> React` when the stream profile is running.
- Direct DB replay still exists for defense recovery, but it must be requested explicitly with `--publish-mode direct-db-fallback`.
- `--rebase-to-now` shifts replay timestamps for API freshness while preserving replay provenance and original timestamps.

## Commands run

```bash
npm --prefix frontend run build
# passed

npm --prefix frontend run lint
# passed

python -m py_compile services/replay_publisher/main.py
# passed

python -m services.replay_publisher.main --dry-run --fixture fixtures/replay_sample.json
# passed

python -m services.replay_publisher.main --dry-run --fixture fixtures/replay_sample.json --rebase-to-now
# passed

pytest tests/openaq/test_replay_direct_ingest.py -q
# passed: 3 tests

pytest tests/openaq tests/unit -q
# passed: 28 tests

bash -n scripts/run_replay_demo.sh
# passed

docker compose --profile core --profile stream config --quiet
# passed

./scripts/run_replay_demo.sh --wait-seconds 90
# failed once without Docker socket permission
# passed with elevated Docker access

./scripts/run_replay_demo.sh --skip-compose-up --wait-seconds 90
# passed with elevated Docker access against the running core+stream stack
```

## Exit criteria verification

- [x] Modeled baseline map raster is visible by default for usable modeled interpolation responses.
- [x] Modeled map output has a stronger raster style while station markers remain on top.
- [x] The map shows a compact modeled baseline chip using API interpolation metadata.
- [x] Replay publisher publishes to Kafka by default.
- [x] Direct DB replay exists only as an explicitly named fallback mode.
- [x] Demo fixture provenance remains `demo_replay`, `replay`, `REPLAY_DEMO`, and `demo`.
- [x] A single helper command exists for defense-day replay verification.
- [x] `CHANGELOG.md` was updated.
- [x] No fake live data, unlabeled modeled/replay data, secrets, schemas, or forecast changes were introduced.

## Problems encountered and resolutions

- The sandbox could not write `.git/index.lock`; commits were created with elevated git access.
- Docker access failed without elevated permissions; the replay helper passed after rerunning with approved Docker access.
- In the live helper run, `/api/stations` reported `replay_active=true` and replay station rows as `REPLAY_DEMO`, while valley/interpolation coverage remained `MODELED_BASELINE` because modeled fallback data was also available. This preserves the existing source-priority behavior and still makes replay provenance visible in the frontend API state.

## Known issues and technical debt

- Severity: Low. Manual browser clicking was not performed; frontend build/lint and HTTP reachability passed, and the API state consumed by the frontend was verified.
- Severity: Low. The helper verifies station-level replay provenance. If a future defense script requires valley coverage itself to switch to `REPLAY_DEMO` even when modeled fallback is available, that should be treated as an explicit source-priority policy change.

## What the next session needs to know

- Post-Phase-14 maintenance remains the active state.
- Use `./scripts/run_replay_demo.sh --build` for the full defense-day replay setup.
- Use `--publish-mode direct-db-fallback` only when Kafka or Spark is unavailable and the operator accepts that the fallback does not prove the streaming path.

## How to resume from scratch

```bash
npm --prefix frontend run build
npm --prefix frontend run lint
pytest tests/openaq tests/unit -q
./scripts/run_replay_demo.sh --build --wait-seconds 90
```
