# HimalayaAir Demo Script

This script runs a provenance-aware demo using replayed data through the real pipeline.

## Preconditions

- `timescaledb`, `kafka`, `spark-stream`, `api`, and `frontend` are running.
- Kafka topics are created.
- Replay fixture exists at `fixtures/replay_sample.json`.

## 1. Reliable replay demo command

Run the full defense-day replay path:

```bash
./scripts/run_replay_demo.sh --build
```

This starts the `core` and `stream` profiles, creates Kafka topics, validates `fixtures/replay_sample.json`, publishes replay rows to `raw-aq-readings` with `--rebase-to-now`, waits for Spark/API persistence, and verifies frontend reachability plus API-visible replay provenance.

Expected:
- API station rows show `source=demo_replay`, `observation_type=replay`, `coverage_mode=REPLAY_DEMO`, and `confidence=demo`.
- `/api/stations` reports `replay_active=true`.
- The frontend at `http://localhost:3000` is reachable and uses the same API state.

## 2. Manual replay publisher validation

```bash
python -m services.replay_publisher.main --dry-run --fixture fixtures/replay_sample.json --rebase-to-now
```

Expected:
- Logs show `replay_dry_run`.
- Source is `demo_replay`.
- Observation type is `replay`.
- Coverage mode is `REPLAY_DEMO`.

## 3. Manual Kafka publish path

```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:29092 \
python -m services.replay_publisher.main \
  --fixture fixtures/replay_sample.json \
  --speed 500 \
  --rebase-to-now
```

Optional loop mode:

```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:29092 \
python -m services.replay_publisher.main \
  --fixture fixtures/replay_sample.json \
  --speed 60 \
  --rebase-to-now \
  --loop
```

## 4. Explicit direct DB fallback

Use direct DB fallback only if Kafka or Spark is unavailable during defense recovery. This does not prove the streaming pipeline.

```bash
python -m services.replay_publisher.main \
  --fixture fixtures/replay_sample.json \
  --speed 500 \
  --rebase-to-now \
  --publish-mode direct-db-fallback
```

## 5. Validate end-to-end flow

- Replay publisher publishes to Kafka topic `raw-aq-readings` by default.
- Spark consumes from `raw-aq-readings` and writes to `aq_readings` with `observation_type=replay`.
- API `/api/stations` exposes replay station rows as `REPLAY_DEMO` when replay data is current enough.
- Frontend banner and map controls show replay provenance and never label replay as live observed.

## 6. Spatial views to showcase

- Enable IDW heatmap.
- Show cigarette-equivalence counter.
- Show wind rose panel when weather support is available.

## 7. Stop demo stack

```bash
docker compose --profile stream --profile core down
```
