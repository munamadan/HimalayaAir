# Final Defense Script (Phase 14)

## 0-2 min: Architecture and Goal

- State the thesis contribution: provenance-aware degradation rather than fake live certainty.
- Show the pipeline path: OpenAQ/Open-Meteo/replay -> Kafka -> Spark -> TimescaleDB/PostGIS -> FastAPI/WebSocket -> React dashboard.

## 2-5 min: Startup Walkthrough

Run:

```bash
docker compose --profile core --profile stream up -d
./scripts/verify_env.sh --profile core
```

Explain expected result:
- `timescaledb`, `kafka`, `api`, `frontend` healthy.

## 5-8 min: Provenance and Coverage Mode Demo

- Open dashboard and API responses side by side.
- Call:

```bash
curl -sS http://localhost:8000/api/stations | jq '.coverage_mode, .confidence, .fresh_station_count, .recent_station_count'
```

Narrate that `LIVE_OBSERVED`, `RECENT_OBSERVED`, `MODELED_BASELINE`, `REPLAY_DEMO`, `STATION_ONLY`, `NO_DATA` are explicit and user-visible.

## 8-11 min: Replay Demo Path Through Real Pipeline

Run replay publish:

```bash
./scripts/run_replay_demo.sh --skip-compose-up --speed 500
```

Explain this is not frontend-only simulation; it publishes `demo_replay` records to Kafka, Spark persists them, and the API/frontend expose replay provenance.

## 11-13 min: Fallback Honesty and Forecast Explanation

- Use `/api/valley/current` and `/api/forecasts/{station_id}` to explain fallback logic.
- Explain arbitration order:
1. SARIMAX when observed + weather coverage is sufficient.
2. Bias-adjusted modeled AQ fallback.
3. Persistence fallback.

## 13-15 min: Recovery and Failure Handling

- Show `/api/pipeline/health` output.
- Explain degraded behavior when live coverage is sparse, and explicit metadata for source, freshness, and confidence.
- Highlight known risks: local Docker DNS flakiness and laptop resource variability.

## Closing

- Emphasize reproducibility scripts in `benchmarks/` and verifications in `docs/benchmark-results.md`.
