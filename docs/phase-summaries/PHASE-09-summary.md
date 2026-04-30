# PHASE-09 Summary - FastAPI REST API and WebSocket Layer

## What was built

- `services/api/config.py`: API runtime settings for database URL normalization, freshness windows, caches, IDW grid shape, Kafka/WebSocket behavior, and health-check URLs.
- `services/api/db.py`: Lazy async SQLAlchemy engine/session handling using asyncpg, with visible 503 behavior when the driver or database is unavailable.
- `services/api/models.py`: Pydantic response models for station snapshots, current readings, histories, valley state, interpolation, health advisory, fire events, pipeline health, and WebSocket events.
- `services/api/repository.py`: Async SQL query repository for stations, latest per-pollutant station current state, histories, modeled AQ fallback, fire events, pipeline runs, and geography-based nearest-station distance.
- `services/api/service.py`: Endpoint orchestration for coverage-aware responses, valley composite AQI, IDW fallback selection, advisories, and pipeline health.
- `services/api/spatial.py`: IDW interpolation using local projected meter offsets for Kathmandu Valley instead of raw lat/lon degree distances.
- `services/api/cache.py`: In-process TTL caches for station snapshots and IDW responses.
- `services/api/health_checks.py`: Kafka and poller health checks that report degraded/down states without hiding failures.
- `services/api/websocket.py`: Connection manager with heartbeat support, duplicate processed-batch handling, and a retrying Kafka background consumer for `processed-aq-readings`.
- `services/api/main.py`: FastAPI application exposing REST endpoints and `/ws/live-feed`.
- `services/api/Dockerfile`: Container runtime for the API service.
- `docker-compose.yml`: Real API service wiring replacing the previous placeholder; Kafka is no longer a startup dependency for the API container.
- `.env.example`: Blank API configuration variables.
- `requirements.txt`: Added FastAPI, Uvicorn, asyncpg, and aiokafka.
- `tests/api/`: API contract tests using fixture repository data.
- `CHANGELOG.md`: Phase 09 entry with files changed, reason, impact, verification, and plan changes.

## Current system state

The backend API can be imported and run with:

```bash
uvicorn services.api.main:app --host 0.0.0.0 --port 8000
```

Implemented endpoints:

- `GET /health`
- `GET /api/stations`
- `GET /api/stations/{station_id}/current`
- `GET /api/stations/{station_id}/history`
- `GET /api/valley/current`
- `GET /api/valley/history`
- `GET /api/interpolation/current`
- `GET /api/health-advisory`
- `GET /api/events`
- `GET /api/pipeline/health`
- `WebSocket /ws/live-feed`

The local database is reachable from the host after installing `asyncpg`. A live `/api/stations` curl returned `MODELED_BASELINE` because current observed coverage is sparse, while modeled AQ fallback is available. This is expected and preserves provenance.

The old Phase 02 placeholder `api` container was stopped during verification because it occupied port `8000` and returned `404` for `/health`. The Compose file now points at the real API image, but the service should be rebuilt/restarted when Docker build network access is available.

No forecast endpoint, frontend code, replay publisher, or future-phase forecasting behavior was introduced.

## Commands run

```bash
python -m py_compile services/api/*.py
# passed

docker compose --profile core config --quiet
# passed

pytest tests/api -q
# passed: 12 tests

pytest tests/unit tests/api -q
# passed: 29 tests

pytest tests/unit tests/openaq tests/weather tests/integration tests/airflow tests/api -q
# passed: 53 tests

timeout 6s uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload || true
# failed first in sandbox: local socket creation blocked
# failed next with approved socket access: old placeholder API container occupied port 8000
# passed after stopping only the old placeholder API container

curl -fsS http://localhost:8000/health || true
# failed first in sandbox: local socket access blocked
# returned 404 while the old placeholder API container still owned port 8000
# passed against a temporary FastAPI process after runtime dependency installation

python -m pip install --user asyncpg aiokafka
# failed first in sandbox: DNS/network blocked
# passed with approved network access
```

Additional live check:

```bash
uvicorn services.api.main:app --host 0.0.0.0 --port 8000
curl -fsS http://localhost:8000/api/stations
# passed against the local database; returned MODELED_BASELINE with modeled provenance visible
```

## Exit criteria verification

- [x] All in-scope tasks are complete or documented: REST endpoints, Pydantic models, async SQLAlchemy sessions, TTL caches, coverage-aware current state, IDW, health advisory, events, pipeline health, WebSocket manager, retrying Kafka consumer, and API tests are implemented.
- [x] Relevant verification commands were run: required pytest, Uvicorn, and curl checks were run with blocked reasons and successful reruns documented.
- [x] `CHANGELOG.md` was updated with `PHASE-09 FastAPI REST API and WebSocket Layer`.
- [x] `docs/phase-summaries/PHASE-09-summary.md` was written.
- [x] No future-phase work was introduced: `/api/forecasts/{station_id}` remains Phase 10 work.
- [x] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced.

## Problems encountered and resolutions

- Sandbox socket restrictions blocked Uvicorn and curl. The same checks were rerun with approved local socket access.
- Port `8000` was occupied by the old placeholder API container from Phase 02. Stopped only that placeholder container, then reran Uvicorn verification successfully.
- Host Python initially lacked `asyncpg` and `aiokafka`. Added both to `requirements.txt`; local install failed under sandbox DNS restrictions and passed with approved network access.
- FastAPI `TestClient` hangs in this environment because sync threadpool execution blocks. API contract tests use `httpx.ASGITransport` with async dependencies instead.

## Deviations from the phase plan

- API contract tests use fixture repository data instead of a live fixture database to keep tests deterministic without requiring TimescaleDB/PostGIS in CI-like environments. A live `/api/stations` curl was still run against the local database.
- `/api/forecasts/{station_id}` was not implemented because the active phase explicitly excludes future work and forecasting belongs to Phase 10.
- The WebSocket route sends a visible error event if the station snapshot cannot be loaded after connection acceptance, rather than rejecting the socket before the client receives feedback.

## Known issues and technical debt

- Severity: Medium. The Compose `api` service has not been rebuilt from the new `services/api/Dockerfile` in this session. Rebuild when Docker build network access is available.
- Severity: Medium. Current local observed coverage is sparse, so live station current fields are mostly empty and the API selects `MODELED_BASELINE`. This is expected but should be rechecked after Spark writes fresher observed readings.
- Severity: Low. Kafka consumer lag is reported as `null`; the health endpoint checks Kafka connectivity/topic presence but does not compute group lag yet.
- Severity: Low. District names remain unavailable until trusted district boundary rows are loaded.

## What the next phase needs to know

- Phase 10 can add forecast APIs and model arbitration without changing the Phase 09 route structure.
- `processed-aq-readings` remains a best-effort WebSocket notification topic; REST snapshots from TimescaleDB remain authoritative.
- API fallback order is live observed, recent observed, modeled baseline, replay demo, station-only, no-data.
- The API Compose service no longer depends on Kafka health at startup by design.

## How to resume from scratch

```bash
docker compose --profile core up -d timescaledb kafka
python -m pip install --user -r requirements.txt
PATH="$HOME/.local/bin:$PATH" alembic upgrade head
python scripts/seed_weather_locations.py
uvicorn services.api.main:app --host 0.0.0.0 --port 8000
curl -fsS http://localhost:8000/health
pytest tests/api -q
```

To run the containerized API after rebuilding:

```bash
docker compose --profile core up -d --build api
curl -fsS http://localhost:8000/health
```

## Next session prompt

```text
Follow AGENTS.md. Implement PHASE 10 only using docs/codex/phases/PHASE-10-forecasting.md.
```
