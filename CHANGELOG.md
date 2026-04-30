# Changelog

All meaningful project changes are recorded here so future Codex sessions can resume with the implemented phase history.

## PHASE-11 Frontend Core Dashboard - 2026-04-30

### Files changed

- `frontend/`: Added the Vite React 18 TypeScript dashboard app with native fetch API wrapper, typed response assumptions, dashboard data hooks, reconnecting WebSocket hook, Mapbox/MapLibre adapter, AQI helpers, IDW-grid raster conversion, core components, dark responsive CSS, and focused AQI helper tests.
- `frontend/Dockerfile` and `frontend/nginx.conf`: Added a production static frontend container served by Nginx.
- `frontend/.env.example`: Documented public frontend runtime variables without committing secrets.
- `docker-compose.yml`: Replaced the placeholder frontend image with the real frontend build service using public `VITE_` build arguments.
- `docs/phase-summaries/PHASE-11-summary.md`: Added the Phase 11 completion summary.

### Reason

Phase 11 requires a visually impressive core dashboard that works with the existing FastAPI and WebSocket layer while making coverage mode, confidence, source, observation type, freshness, and fallback provenance visible to users.

### Impact

The frontend now renders a defense-ready live dashboard shell with navigation, loading/error states, valley AQI gauge, station markers, station detail popup/card, IDW heatmap raster toggle, PM2.5 multi-station chart, provenance panel, pipeline health panel, and WebSocket-driven refresh behavior. The map initializes once and updates markers/heatmap sources in place. The app does not use Redux and does not invent frontend data when API history or current readings are unavailable.

### Verification performed

- `npm --prefix frontend install`: initial sandbox invocation did not produce a lockfile; approved network install with `--loglevel=info` passed and created `package-lock.json`.
- `npm --prefix frontend run build`: failed once on ES2021 `replaceAll` usage, then passed after ES2020-compatible fixes. Final build passed with an expected large map-library chunk warning.
- `npm --prefix frontend run lint || true`: failed once on map adapter `any` types, then passed after adding narrow local map interfaces.
- `npm --prefix frontend run test -- --run`: passed with 3 tests.
- `docker compose --profile core config --quiet`: passed.
- `npm --prefix frontend audit --omit=dev`: failed first in the sandbox due registry DNS resolution, then passed with approved network and found 0 production vulnerabilities.

### Plan changes

- Used MapLibre as the no-token local default while keeping Mapbox support when `VITE_MAP_PROVIDER=mapbox` and a public `VITE_MAPBOX_TOKEN` are provided.
- Did not implement historical explorer, forecast UI panel, replay controls, or fire overlays because those belong to later phases.
- Did not add frontend fixture fallback data, so the dashboard never presents fabricated live readings.

### Phase result

Phase 11 is complete at the code/build verification level. The next phase is safe to start after reviewing the summary and running a browser check against a live API/frontend pair when convenient.

## PHASE-10 Forecasting and Accuracy Tracking - 2026-04-30

### Files changed

- `services/forecasting/`: Added forecast settings, typed model inputs/results, arbitration, persistence baseline, Open-Meteo modeled bias adjustment, SARIMAX execution, retrospective accuracy record building, sync TimescaleDB repository writes, and a `run_once` CLI.
- `db/alembic/versions/0007_forecast_fallback_reason.py`: Added `forecasts.fallback_reason` so station-level forecast rows preserve visible fallback reasons.
- `airflow/dags/forecast_recompute_hook.py` and `airflow/dags/himalayaair/forecast_hook.py`: Replaced the Phase 08 hook behavior with a real hourly `forecast_recompute` DAG task that calls the Phase 10 runner.
- `services/api/`: Added forecast response schemas, repository query support, service wiring, and `GET /api/forecasts/{station_id}`.
- `docker-compose.yml`, `.env.example`, and `requirements.txt`: Added forecast runtime knobs and the `statsmodels` SARIMAX dependency.
- `scripts/verify_db_schema.py`: Added verification for the new `forecasts.fallback_reason` column.
- `tests/forecasting/` and `tests/api/test_forecasts_contract.py`: Added arbitration, persistence shape, modeled-bias, forecast-accuracy idempotency, and forecast API contract coverage.
- `docs/phase-summaries/PHASE-10-summary.md`: Added the Phase 10 completion summary.

### Reason

Phase 10 requires 72-hour forecasts that always return a valid forecast while honestly exposing whether the model came from SARIMAX, modeled AQ with observed bias, or persistence fallback.

### Impact

Forecast recomputation now writes `forecast_runs` and `forecasts` with `model_name`, `model_source`, and `fallback_reason`. SARIMAX is selected only when observed AQ history, historical weather, and future weather covariates meet configured coverage thresholds. Modeled AQ is used only from `modeled_aq_readings` with `MODELED_BASELINE` provenance, and persistence falls back to the latest observed/replay/modeled AQI or an explicit synthetic seed when no baseline exists. Retrospective accuracy inserts are idempotent through the existing unique key. The API now exposes the latest forecast run for a station with confidence bounds and historical MAE when available.

### Verification performed

- `pytest tests/forecasting -q`: passed with 9 tests.
- `python -m services.forecasting.run_once --dry-run`: failed first in the sandbox due blocked local DB socket, then passed with approved DB access. After installing `statsmodels`, it selected persistence for 2 stations because local observed/weather/future modeled coverage is currently insufficient.
- `curl -fsS http://localhost:8000/api/forecasts/1`: failed first in the sandbox due blocked local socket, then failed because no API server was running, then passed against a temporary FastAPI server after writing a real forecast run.
- `PATH="$HOME/.local/bin:$PATH" alembic upgrade head`: failed first in the sandbox due blocked local DB socket, then passed with approved DB access and applied `0007_forecast_fallback_reason`.
- `python scripts/verify_db_schema.py`: failed before the migration completed during a parallel check, then passed and verified `forecasts.fallback_reason`.
- `python -m pip install --user "statsmodels>=0.14,<1.0"`: failed first under sandbox DNS restrictions, then passed with approved network access.
- `pytest tests/api tests/forecasting -q`: passed with 22 tests.
- `pytest tests/unit tests/openaq tests/weather tests/integration tests/airflow tests/api tests/forecasting -q`: passed with 63 tests.
- `python -m py_compile services/forecasting/*.py services/api/*.py airflow/dags/*.py airflow/dags/himalayaair/*.py db/alembic/versions/*.py scripts/verify_db_schema.py`: passed.
- `docker compose --profile core config --quiet`, `docker compose --profile batch config --quiet`, and `docker compose --profile full config --quiet`: passed.

### Plan changes

- Kept the existing Phase 08 filename `forecast_recompute_hook.py` but changed the DAG id to `forecast_recompute` and the task to real forecast execution.
- Added a Phase 10 migration because the existing `forecasts` table did not have row-level `fallback_reason`, and mixed station/model runs need station-specific explanations.
- The local verification wrote forecast runs using persistence because the current local database has no sufficient 90-day observed AQ history, incomplete 90-day weather coverage, and fewer than 72 future modeled AQ hours.

### Phase result

Phase 10 is complete at the code and local verification level. Forecasting is available, source-aware, and measurable; the next phase is safe to start after reviewing the summary.

## PHASE-09 FastAPI REST API and WebSocket Layer - 2026-04-30

### Files changed

- `services/api/`: Added the FastAPI service package with environment settings, async SQLAlchemy session setup, Pydantic response contracts, coverage/provenance helpers, PostGIS-aware repository queries, IDW interpolation using local meter projection, in-process TTL caches, health checks, and WebSocket/Kafka live-feed management.
- `services/api/Dockerfile`: Added the runtime image for the Compose `api` service.
- `docker-compose.yml`: Replaced the Phase 02 HTTP placeholder with the real FastAPI API service and removed Kafka as an API startup dependency so Kafka outages do not block API startup.
- `.env.example`: Added blank non-secret API runtime knobs for coverage windows, caches, IDW grid size, WebSocket heartbeat, Kafka health, and poller health URLs.
- `requirements.txt`: Added FastAPI, Uvicorn, asyncpg, and aiokafka runtime dependencies.
- `tests/api/`: Added API contract tests with fixture repository data for stations, station current/history, valley current/history, interpolation, health advisory, events, pipeline health, route registration, and WebSocket duplicate batch handling.
- `docs/phase-summaries/PHASE-09-summary.md`: Added the Phase 09 completion summary.

### Reason

Phase 09 requires a curl-testable backend API that exposes coverage-aware REST endpoints, provenance, IDW interpolation, health status, and a WebSocket live feed without starting future forecasting or frontend work.

### Impact

The backend now exposes `/health`, `/api/stations`, `/api/stations/{id}/current`, `/api/stations/{id}/history`, `/api/valley/current`, `/api/valley/history`, `/api/interpolation/current`, `/api/health-advisory`, `/api/events`, `/api/pipeline/health`, and `/ws/live-feed`. Responses preserve `coverage_mode`, `confidence`, source, observation type, freshness, and fallback messaging. Current station state selects latest readings per pollutant within the configured freshness window. Distance outputs use PostGIS geography in SQL, and IDW uses local projected meter offsets instead of raw degree distance. The WebSocket Kafka consumer retries in the background and does not block API startup.

### Verification performed

- `pytest tests/api -q`: passed with 12 tests.
- `python -m py_compile services/api/*.py`: passed.
- `docker compose --profile core config --quiet`: passed.
- `pytest tests/unit tests/api -q`: passed with 29 tests.
- `pytest tests/unit tests/openaq tests/weather tests/integration tests/airflow tests/api -q`: passed with 53 tests.
- `timeout 6s uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload || true`: first failed inside the sandbox with socket permission denied; then failed because the old Phase 02 placeholder API container was still bound to port 8000; passed after stopping only that placeholder container and rerunning with approved local socket access.
- `curl -fsS http://localhost:8000/health || true`: first failed inside the sandbox due blocked local socket access, then hit the old placeholder and returned 404, then passed against the new temporary FastAPI server and returned `status=healthy` after installing runtime dependencies locally.
- `python -m pip install --user asyncpg aiokafka`: first failed under sandbox DNS restrictions, then passed with approved network access.
- Temporary live curl check against `/api/stations`: passed and returned a provenance-aware `MODELED_BASELINE` response from the local database because fresh/recent observed coverage is currently sparse.

### Plan changes

- API contract tests use a fixture repository rather than a live test database so they remain deterministic and do not require TimescaleDB/PostGIS during unit verification. Live `/api/stations` was still curl-tested against the local database after installing runtime dependencies.
- `/api/forecasts/{station_id}` was intentionally not implemented because forecast model execution and forecast API behavior belong to Phase 10.
- The old placeholder `api` container was stopped during verification to free port 8000. Recreate the Compose API service with the new image when Docker build network access is available.

### Phase result

Phase 09 is complete at the code and local verification level. The REST API and WebSocket layer are implemented with visible provenance and degradation behavior. The next phase is safe to start after reviewing the summary and rebuilding/restarting the Compose API service if containerized runtime verification is needed.

## PHASE-08 Airflow Backfills, Quality Checks, and FIRMS - 2026-04-30

### Files changed

- `airflow/dags/*.py`: Added manually triggerable Airflow DAG wrappers for OpenAQ historical backfill, Open-Meteo weather history, data quality checks, FIRMS daily load, and a forecast recompute scheduling hook.
- `airflow/dags/himalayaair/`: Added Airflow task helpers for environment settings, structured logging setup, DB writes, `pipeline_runs`, `backfill_manifest`, OpenAQ archive/API backfill, weather archive backfill, data quality state reporting, FIRMS CSV parsing, and the Phase 08 forecast hook.
- `docker-compose.yml`: Added TimescaleDB to the `batch` profile, mounted only `shared` and `services` into Airflow read-only, set Airflow `PYTHONPATH`, and exposed non-secret Airflow DAG runtime environment knobs.
- `.env.example`: Added blank FIRMS and Airflow DAG runtime variables.
- `tests/airflow/`: Added focused tests for OpenAQ archive parsing, FIRMS event hashing, weather month windows, and degraded data quality behavior.
- `docs/airflow/manual-triggers.md`: Documented manual DAG trigger examples without changing `README.md`.
- `docs/phase-summaries/PHASE-08-summary.md`: Added the Phase 08 completion summary.

### Reason

Phase 08 requires Airflow orchestration for historical observed AQ backfills, historical weather, data quality checks, forecast scheduling hooks, and FIRMS fire-event enrichment while preserving provenance, idempotency, structured logs, and visible task outcomes.

### Impact

The batch profile now has a repeatable orchestration layer. OpenAQ backfill tries the public archive path by location/day before falling back to the sensor measurements API, writes observed readings idempotently, and records per-sensor/day audit rows in `backfill_manifest`. Weather history writes Open-Meteo archive rows by location/month manifest units. Data quality writes `coverage_snapshots`, reports `healthy`, `degraded`, or `down`, and treats sparse fresh station coverage as a degraded `pipeline_runs` row instead of a DAG failure. FIRMS daily load parses acquisition fields and inserts duplicate-resistant `fire_events` using `event_hash`. The forecast DAG is a Phase 08 scheduling hook only; forecast model execution remains Phase 10.

### Verification performed

- `airflow dags list || true`: completed with the expected local fallback because the host environment does not have the `airflow` CLI installed (`airflow: command not found`).
- `python -m py_compile airflow/dags/*.py`: passed.
- `pytest tests/airflow -q`: passed with 8 tests.
- `python -m py_compile airflow/dags/*.py airflow/dags/himalayaair/*.py`: passed.
- `PYTHONPATH=airflow/dags:. python -c "import openaq_historical_backfill, weather_historical_backfill, air_quality_data_quality_check, firms_daily_load, forecast_recompute_hook; print('ok')"`: passed.
- `docker compose --profile batch config --quiet`: passed.
- `pytest tests/unit tests/openaq tests/weather tests/integration tests/airflow -q`: passed with 41 tests.

### Plan changes

- Added `forecast_recompute_hook` as a no-forecast scheduling hook because Phase 08 mentions forecast scheduling, while Phase 10 remains responsible for model arbitration and forecast writes.
- Used non-null `backfill_manifest.external_sensor_id` sentinel values for weather and FIRMS manifest rows so the existing nullable unique constraint does not allow duplicate manifest rows.
- Mounted `shared` and `services` into Airflow read-only instead of the full project root to avoid exposing ignored local files while still reusing existing project code.

### Phase result

Phase 08 is complete at the code and local-test level. The only blocked runtime verification is live Airflow CLI/DAG listing on the host because Apache Airflow is not installed outside the Docker batch profile.

## PHASE-07 Spark Stream Processing and Timescale Persistence - 2026-04-29

### Files changed

- `services/common/aqi_calculator.py`: Added a pure Python PM2.5 AQI calculator using current EPA PM2.5 breakpoints, category helpers, color helpers, unit handling, and out-of-range handling.
- `services/spark/jobs/aq_stream_processor.py`: Added the Spark Structured Streaming processor with fixture dry-run support, Kafka JSON parsing, raw-message validation, AQI calculation, district lookup, baseline/range anomaly flags, idempotent TimescaleDB writes, station freshness updates, `pipeline_runs` recording, DLQ message construction, and best-effort processed-batch notifications.
- `services/spark/Dockerfile`: Added a Spark 3.5.x Python runtime image for the stream processor.
- `docker-compose.yml`: Replaced the `spark-stream` placeholder with a real `spark-submit` service, checkpoint volume, stream-profile TimescaleDB/Kafka dependencies, and stream processor environment settings.
- `.env.example`: Added non-secret Spark processor runtime settings.
- `shared/kafka/messages.py`: Added processed AQ batch summary schemas that preserve per-station source and observation type for WebSocket notifications.
- `docs/kafka-message-contracts.md`: Documented `processed-aq-readings` as a batch summary notification topic with `batch_id` keys.
- `fixtures/sample_raw_aq_batch.json`: Added a replay-labeled batch fixture for Spark dry-run verification.
- `tests/unit/test_aqi_calculator.py`: Added AQI breakpoint, truncation, category, color, and invalid-input tests.
- `tests/unit/test_kafka_messages.py`: Added processed AQ batch summary schema coverage.
- `tests/integration/test_spark_batch_fixture.py`: Added fixture transformation tests for AQI, sparse baseline flags, z-score anomalies, range anomalies, DLQ construction, and processed summaries.

### Reason

Phase 07 requires raw AQ Kafka messages to be processed by Spark, normalized, enriched with AQI/district/anomaly metadata, persisted idempotently to `aq_readings`, reflected in station freshness, recorded in `pipeline_runs`, and surfaced through best-effort processed notifications.

### Impact

The stream profile now points at a real Spark job instead of a sleeping placeholder. The job can run as Spark Structured Streaming from `raw-aq-readings` and process each micro-batch through a psycopg2 `foreachBatch` write path with `ON CONFLICT DO NOTHING`. Dry-run fixture execution works without Spark, which keeps local verification fast and deterministic. Processed rows preserve `source`, `observation_type`, `coverage_mode`, and `confidence`; sparse anomaly baselines are visible as `quality_flag='insufficient_baseline'` instead of silently passing as fully scored data.

### Verification performed

- `pytest tests/unit/test_aqi_calculator.py -q`: passed with 4 tests.
- `python services/spark/jobs/aq_stream_processor.py --fixture fixtures/sample_raw_aq_batch.json --dry-run`: passed and transformed 3 replay-labeled records with 1 range anomaly.
- `python -m py_compile services/common/aqi_calculator.py services/spark/jobs/aq_stream_processor.py shared/kafka/messages.py`: passed.
- `pytest tests/unit/test_aqi_calculator.py tests/unit/test_kafka_messages.py tests/integration/test_spark_batch_fixture.py -q`: passed with 15 tests.
- `pytest tests/unit tests/openaq tests/weather tests/integration -q`: passed with 33 tests.
- `docker compose --profile stream config --quiet`: passed.
- `docker compose --profile stream up -d spark-stream || true`: failed first in the sandbox due blocked Docker socket access, then with approved Docker access failed because `bitnami/spark:3.5.1` was unavailable. After switching to the current official `spark:3.5.8-python3` image, the command downloaded the Spark image but the build failed during `pip install` because the Docker build could not resolve PyPI DNS for Python dependencies. The command is documented as blocked by Docker build network resolution; `spark-stream` did not start.

### Plan changes

- Used the current official Docker `spark:3.5.8-python3` image because the previous Bitnami Spark tag no longer exists on Docker Hub.
- Kept `ProcessedAQReadingMessage` for backward compatibility and added `ProcessedAQBatchSummaryMessage` for Phase 07's batch-summary notification requirement.
- Did not add a schema migration because `aq_readings`, `station_sensors.last_seen` targets, and `pipeline_runs` already support the Phase 07 write path.

### Phase result

Phase 07 implementation is complete at the code and local-test level. Required Python verification passed, stream Compose configuration passed, and the only blocked verification is starting the Docker stream service because dependency installation inside the Docker build could not reach PyPI.

## PHASE-06 Weather and Modeled AQ Fallback - 2026-04-29

### Files changed

- `services/weather_poller/`: Added the Open-Meteo weather and modeled AQ poller package with environment settings, typed normalized outputs, retrying HTTP clients, DB reads/writes, optional Kafka diagnostics, loop/CLI execution, and `/health` serving on port `9091`.
- `services/weather_poller/Dockerfile`: Added a buildable runtime image shared by the weather and Open-Meteo AQ poller containers.
- `docker-compose.yml`: Replaced weather placeholders with real `weather-poller` and `openmeteo-aq-poller` services, added the `weather` profile to TimescaleDB, and wired healthchecks plus runtime settings.
- `.env.example`: Added non-secret Open-Meteo poller settings and the weather poller host-port override.
- `db/alembic/versions/0006_weather_modeled_quality_flags.py`: Added `quality_flag` columns and checks to `weather_readings` and `modeled_aq_readings`.
- `scripts/verify_db_schema.py`: Added Phase 06 quality-flag checks to schema verification.
- `shared/kafka/messages.py`: Added `quality_flag` fields to weather and modeled AQ diagnostic Kafka messages.
- `tests/weather/`: Added focused tests for Open-Meteo normalization, quality flags, modeled provenance, diagnostic messages, and 429 retry handling.
- `docs/phase-summaries/PHASE-06-summary.md`: Added the Phase 06 completion summary.
- `CHANGELOG.md`: Recorded Phase 06 implementation and verification.

### Reason

Phase 06 requires Open-Meteo weather enrichment and Open-Meteo/CAMS modeled AQ fallback data to be available with explicit provenance, idempotent database writes, visible quality flags, optional Kafka diagnostics, and poller health.

### Impact

The weather profile now runs real Open-Meteo pollers. `weather-poller` writes weather rows to `weather_readings`, while `openmeteo-aq-poller` uses the same package in modeled-AQ mode for `modeled_aq_readings`. The default CLI can run both components together. Modeled AQ rows are stored separately from observed AQ and preserve `source=openmeteo_cams`, `observation_type=modeled`, `coverage_mode=MODELED_BASELINE`, and `quality_flag`. A live local run inserted 480 weather rows and 2,880 modeled AQ rows for the five seeded Kathmandu Valley weather locations; a second run in the same model-run hour inserted 0 duplicate rows.

### Verification performed

- `python -m py_compile services/weather_poller/*.py shared/kafka/messages.py db/alembic/versions/0006_weather_modeled_quality_flags.py scripts/verify_db_schema.py`: passed.
- `pytest tests/weather -q`: passed with 5 tests.
- `pytest tests/unit tests/weather -q`: passed with 17 tests.
- `docker compose --profile weather config --quiet`: passed.
- `docker compose --profile weather config --services | sort`: passed and listed `openmeteo-aq-poller`, `timescaledb`, and `weather-poller`.
- `docker compose --profile full config --quiet`: passed.
- `python -m services.weather_poller.main --once --dry-run`: failed first in the sandbox due blocked DB access, then passed with approved DB/network access and normalized 480 weather plus 2,880 modeled AQ rows across 5 locations.
- `PATH="$HOME/.local/bin:$PATH" alembic upgrade head`: failed first in the sandbox due blocked DB access; then failed because the initial revision id exceeded `alembic_version.version_num VARCHAR(32)`; passed after shortening the revision id to `0006_weather_quality_flags`.
- `python -m services.weather_poller.main --once`: passed with approved DB/network access and inserted 3,360 total rows.
- `python -m services.weather_poller.main --once`: passed a second time with approved DB/network access and inserted 0 rows, confirming `ON CONFLICT DO NOTHING` idempotence for the current model-run hour.
- `python scripts/verify_db_schema.py`: failed first in the sandbox due blocked DB access, then passed with approved DB access and verified the new quality-flag checks.
- `curl -fsS http://localhost:9091/health || true`: failed first in the sandbox due blocked local socket access, then passed with approved socket access while a dry-run poller loop was running and returned `status=ok`.
- Read-only DB provenance query: failed first in the sandbox due blocked DB access, then passed with approved DB access and confirmed 480 `openmeteo_weather` rows plus 2,880 `openmeteo_cams` / `modeled` / `MODELED_BASELINE` rows.

### Plan changes

- Kept the approved two-container weather profile by running the same `services.weather_poller` package in `weather` mode for `weather-poller` and `modeled_aq` mode for `openmeteo-aq-poller`.
- Added an Alembic migration for `quality_flag` because the Phase 03 schema did not have columns where weather/modeled AQ row quality could be stored.
- Made Kafka publishing disabled by default through `WEATHER_PUBLISH_KAFKA=false`; diagnostics can be enabled without changing the direct DB write path.

### Phase result

Phase 06 is complete. Weather and modeled AQ fallback data are available in TimescaleDB with explicit source, modeled provenance, coverage mode, and quality flags; required verification passed after documented local approvals; and Phase 07 is safe to start.

## PHASE-05 OpenAQ Sensor-Based Live Ingestion - 2026-04-29

### Files changed

- `services/openaq_poller/`: Added the OpenAQ live poller package with environment settings, database registry access, sensor measurement client, Kafka publishing, dry-run support, poll-window handling, and `/health` serving on port `9090`.
- `services/openaq_poller/Dockerfile`: Added a buildable runtime image for the observed-profile poller.
- `docker-compose.yml`: Replaced the OpenAQ placeholder with the real poller service, healthcheck, database/Kafka dependencies, port `9090`, and poller environment settings.
- `.env.example`: Added OpenAQ poller runtime and host-port settings without secrets.
- `requirements.txt`: Added `httpx` for service-grade HTTP client behavior.
- `scripts/source_validation.py`: Kept recognized OpenAQ AQ sensors pollable when current OpenAQ location metadata omits `datetimeLast`.
- `scripts/verify_env.sh`: Included TimescaleDB in observed-profile health expectations because the poller reads `station_sensors` and writes `pipeline_runs`.
- `scripts/verify_kafka.py`: Added fixtureless `--max-messages` validation so Phase 05 can verify existing `raw-aq-readings` messages.
- `shared/logging_config.py`: Suppressed noisy third-party HTTP logs so service output remains structured.
- `tests/openaq/`: Added focused tests for poll windows, observed message provenance, de-duplication, 429 retry handling, and run status mapping.
- `tests/unit/test_source_validation.py`: Added coverage for pollable AQ sensors without last-seen metadata.
- `docs/phase-summaries/PHASE-05-summary.md`: Added the Phase 05 completion summary.
- `CHANGELOG.md`: Recorded Phase 05 implementation and verification.

### Reason

Phase 05 requires sensor-based OpenAQ live ingestion through the corrected `station_sensors` registry, server-side API key usage, normalized observed Kafka messages, visible poller health, and `pipeline_runs` status recording.

### Impact

The observed profile now has a real OpenAQ poller. It queries active OpenAQ sensors from TimescaleDB, polls `/v3/sensors/{sensor_id}/measurements`, publishes `RawAQReadingMessage` records to `raw-aq-readings` with `source=openaq_live` and `observation_type=observed`, records run metadata in `pipeline_runs`, and reports health at `/health`. A capped live verification populated the local registry with 52 stations and 256 sensors, found 4 active station/sensor pairs, and published 10 observed PM2.5 messages to Kafka.

### Verification performed

- `python -m py_compile services/openaq_poller/*.py scripts/verify_kafka.py`: passed.
- `docker compose --profile observed config --quiet`: failed first because the observed profile did not include the TimescaleDB dependency, then passed after adding TimescaleDB and Kafka to the observed profile dependencies.
- `pytest tests/openaq -q`: passed with 7 tests.
- `pytest tests/unit tests/openaq -q`: passed with 19 tests.
- `python -m services.openaq_poller.main --once --dry-run`: failed first in the sandbox due blocked local DB access, then passed with approved DB access; after registry sync it passed with 4 sensors discovered and OpenAQ calls skipped because no API key was loaded into that shell.
- `curl -fsS http://localhost:9090/health || true`: failed when no poller process was running, then passed after starting the poller dry-run loop and returned `status=ok`.
- `python scripts/verify_kafka.py --topic raw-aq-readings --max-messages 10 || true`: failed first in the sandbox due blocked Kafka socket access, then passed with approved Kafka access and validated replay plus live observed OpenAQ messages.
- `python scripts/verify_kafka.py --fixture fixtures/sample_raw_aq_message.json`: failed first in the sandbox due blocked Kafka socket access, then passed with approved Kafka access.
- `set -a; source .env; set +a; python scripts/sync_openaq_metadata.py --write-db --output tmp/openaq-phase05-metadata-write.json`: failed first in the sandbox due DNS/network restriction, then passed with approved network and DB access; wrote 52 stations and 256 sensors.
- `OPENAQ_MAX_SENSORS=5 OPENAQ_MEASUREMENTS_LIMIT=10 OPENAQ_MAX_PAGES=1 OPENAQ_FALLBACK_LOOKBACK_HOURS=24 OPENAQ_POLL_OVERLAP_MINUTES=1440 python -m services.openaq_poller.main --once`: passed with approved network, DB, and Kafka access; published 10 `openaq_live` / `observed` messages.

### Plan changes

- Added `OPENAQ_MAX_SENSORS` so live verification and laptop runs can cap OpenAQ requests without changing the sensor-based model.
- Updated OpenAQ metadata normalization because the current OpenAQ locations response can omit sensor last-seen timestamps while sensor measurement endpoints remain pollable.
- Ignored zero-sensor runs when choosing the next poll watermark so an empty registry does not shorten the first real polling window.

### Phase result

Phase 05 is complete. Live observed OpenAQ readings were published to Kafka through the sensor registry model, poller health is available, `pipeline_runs` records poll status, required verification passed after documented local approvals, and Phase 06 is safe to start.

## PHASE-04 Kafka Topics and Shared Libraries - 2026-04-29

### Files changed

- `requirements.txt`: Added Pydantic, structlog, and confluent-kafka runtime dependencies.
- `shared/`: Added shared settings, logging, time, health, source/provenance enums, Kafka topic definitions, Kafka message schemas, and Kafka producer/consumer helpers.
- `scripts/create_kafka_topics.sh`: Added the `modeled-aq-data` topic and aligned Phase 04 topic retention settings.
- `scripts/verify_kafka.py`: Added a Kafka round-trip verifier that validates, publishes, consumes, and revalidates a fixture raw AQ message.
- `fixtures/sample_raw_aq_message.json`: Added a replay-labeled raw AQ fixture with explicit source, observation type, coverage mode, and confidence.
- `tests/unit/test_kafka_messages.py`: Added schema validation, provenance enforcement, serialization, DLQ, modeled AQ, and topic-definition tests.
- `docs/kafka-message-contracts.md`: Documented topic names, message keys, and required provenance fields.
- `docs/phase-summaries/PHASE-04-summary.md`: Added the Phase 04 completion summary.
- `CHANGELOG.md`: Recorded Phase 04 implementation and verification.

### Reason

Phase 04 requires a shared foundation so all later services use the same Kafka topic names, message schemas, provenance values, logging configuration, settings, health payloads, and serialization behavior.

### Impact

Later pollers, replay publishers, Spark jobs, and API/WebSocket consumers can now share one typed message contract. Kafka messages cannot validate without `source` and `observation_type`, modeled AQ messages are constrained to `MODELED_BASELINE`, and the verification fixture is explicitly labeled as replay data.

### Verification performed

- `python -m pip install --user -r requirements.txt`: failed first in the sandbox because DNS/network access was blocked, then passed with approved network escalation and installed `structlog` and `confluent-kafka`.
- `python -m py_compile shared/*.py shared/kafka/*.py scripts/verify_kafka.py`: passed.
- `pytest tests/unit -q`: passed with 11 tests.
- `./scripts/create_kafka_topics.sh --dry-run`: passed and printed all six topic creation commands.
- `./scripts/create_kafka_topics.sh`: failed first because Docker daemon access was blocked by the sandbox, then passed with approved Docker access and created `modeled-aq-data`; existing topics remained idempotent.
- `python scripts/verify_kafka.py --fixture fixtures/sample_raw_aq_message.json`: failed first because direct script execution did not include the repo root on `sys.path`; fixed in the script.
- `python scripts/verify_kafka.py --fixture fixtures/sample_raw_aq_message.json`: failed in the sandbox because local Kafka socket access was blocked, then passed with approved socket access and produced/consumed the replay fixture on `raw-aq-readings`.
- `pytest tests/unit -q`: passed again with 11 tests after the verifier fix.

### Plan changes

- Added `docs/kafka-message-contracts.md` so topic names and message keys are explicit without changing `README.md`.
- Kept a single Phase 04 DLQ topic, `raw-aq-readings-dlq`, rather than inventing future per-topic DLQs.
- Used a replay-labeled fixture for Kafka verification to avoid any fake-live-data ambiguity.

### Phase result

Phase 04 is complete. Shared Kafka schemas and helpers are implemented, required verification passed after documented sandbox approvals, and Phase 05 is safe to start.

## PHASE-03 Database Schema and Seed Data - 2026-04-29

### Files changed

- `requirements.txt`: Added Alembic, SQLAlchemy, and psycopg2 migration dependencies.
- `alembic.ini`: Added Alembic configuration for the local TimescaleDB default.
- `db/alembic/env.py`: Added environment-driven sync DB URL resolution for migrations.
- `db/alembic/versions/0001_extensions_core_schema.py`: Added TimescaleDB/PostGIS extensions and core station, sensor, district, and weather-location tables.
- `db/alembic/versions/0002_timeseries_readings.py`: Added provenance-aware AQ, weather, and modeled-AQ hypertables.
- `db/alembic/versions/0003_forecast_operations.py`: Added forecast, pipeline, coverage, and monthly report tables.
- `db/alembic/versions/0004_backfill_fire_events.py`: Added backfill manifest and fire event tables.
- `db/alembic/versions/0005_continuous_aggregates.py`: Added `aq_hourly`, `aq_daily`, and `valley_daily` continuous aggregates with refresh policies.
- `scripts/db_config.py`: Added shared sync database URL normalization.
- `scripts/seed_weather_locations.py`: Added dry-run and idempotent seed support for five Kathmandu Valley weather locations.
- `scripts/verify_db_schema.py`: Added schema verification for extensions, tables, hypertables, continuous aggregates, indexes, checks, and Timescale unique-index rules.
- `scripts/sync_openaq_metadata.py`: Added optional `--write-db` support for upserting OpenAQ stations and station_sensors.
- `README.md`: Replaced detailed phase workflow text with a brief general project description, per user request.
- `AGENTS.md`: Added the rule that `README.md` must not be changed unless the user explicitly requests it.
- `docs/phase-summaries/PHASE-03-summary.md`: Added the Phase 03 completion summary.
- `CHANGELOG.md`: Recorded Phase 03 implementation, verification, and operational notes.

### Reason

Phase 03 requires a corrected database foundation for sensor-based ingestion, provenance-aware readings, modeled fallback, replay support, forecasts, pipeline observability, backfills, reports, and geospatial context.

### Impact

The local TimescaleDB/PostGIS database now upgrades through Alembic to a schema that supports the approved architecture. AQ-related hypertables preserve source and observation type, modeled AQ remains separate from observed readings, and all hypertable primary keys include the `timestamp` partition column. Weather location seed data can be previewed or written idempotently.

### Verification performed

- `python -m py_compile scripts/db_config.py scripts/seed_weather_locations.py scripts/verify_db_schema.py scripts/sync_openaq_metadata.py db/alembic/env.py db/alembic/versions/*.py`: passed.
- `python scripts/seed_weather_locations.py --dry-run`: passed and reported five weather seed rows.
- `python scripts/sync_openaq_metadata.py --dry-run --fixture-location fixtures/sample_openaq_location.json`: passed and preserved dry-run metadata output.
- `python -m pip install --user -r requirements.txt`: passed with approval; installed Alembic and Mako.
- `docker compose --profile core up -d`: passed with approval; started TimescaleDB, Kafka, API placeholder, and frontend placeholder.
- `alembic upgrade head`: failed in the sandbox because host access to the Docker-exposed database port was blocked.
- `PATH="$HOME/.local/bin:$PATH" alembic upgrade head`: passed with approval and applied all five revisions through `0005_continuous_aggregates`.
- `python scripts/verify_db_schema.py`: passed with approval and verified required schema objects.
- `python scripts/seed_weather_locations.py --dry-run`: passed as the required Phase 03 seed verification command.
- `python scripts/seed_weather_locations.py`: passed with approval and inserted or updated five `weather_locations` rows.
- `python scripts/verify_db_schema.py`: passed again after seeding.
- `pytest tests/unit -q`: passed with 5 tests.

### Plan changes

- Added `coverage_snapshots` because the system overview defines it as the storage point for coverage mode, confidence, modeled availability, and replay activity.
- Added `coverage_mode` and `confidence` columns to `aq_readings`, and `observation_type` plus `coverage_mode` to `modeled_aq_readings`, to keep stored AQ provenance explicit.
- Added a unique constraint on `weather_locations.name` so seed writes are idempotent.
- Did not load district boundaries because the repository has no trusted district geometry fixture or source file; the schema enforces `MULTIPOLYGON` and is ready for a later explicit load.

### Phase result

Phase 03 is complete. The database foundation is migrated and verified, weather locations are seeded, required documentation is updated, and Phase 04 is safe to start.


## PHASE-02 Infrastructure Foundation - 2026-04-29

### Files changed

- `docker-compose.yml`: Added Docker Compose profiles for `core`, `stream`, `batch`, `weather`, `observed`, `demo`, and `full` with TimescaleDB/PostGIS, Kafka, Airflow PostgreSQL metadata, Airflow webserver/scheduler, Spark placeholder, API placeholder, frontend placeholder, weather placeholders, OpenAQ placeholder, and replay placeholder services.
- `.env.example`: Added blank infrastructure override names for Airflow local user, Kafka cluster ID, and host ports without committing secrets.
- `scripts/verify_env.sh`: Added a profile-aware Docker Compose health verification script.
- `scripts/create_kafka_topics.sh`: Added a Kafka topic creation script with dry-run support for the architecture topics.
- `README.md`: Documented profile usage, health checks, Kafka topic setup, placeholder scope, and host port defaults.
- `airflow/dags/.gitkeep`: Added the Airflow DAG mount directory placeholder.
- `airflow/plugins/.gitkeep`: Added the Airflow plugin mount directory placeholder.
- `docs/phase-summaries/PHASE-02-summary.md`: Added the Phase 02 completion summary.
- `CHANGELOG.md`: Recorded Phase 02 implementation, verification, and operational notes.

### Reason

Phase 02 requires a local infrastructure foundation that can be started by Docker Compose profile, checked by one script, and prepared for later Kafka, Spark, Airflow, API, and frontend phases without implementing application logic early.

### Impact

The `core` profile now starts TimescaleDB/PostGIS, Kafka, an API placeholder, and a frontend placeholder. Kafka topics can be created reproducibly, and later phases can replace placeholders with real service implementations without changing the approved architecture. Database host ports default to higher local ports to avoid conflicts with existing PostgreSQL installations while preserving normal container network ports.

### Verification performed

- `bash -n scripts/verify_env.sh scripts/create_kafka_topics.sh`: passed.
- `docker compose config`: passed; rendered no default services because runtime services are profile-gated.
- `docker compose --profile full config --quiet`: passed.
- `docker compose --profile full config --services | sort`: passed and listed all profile services.
- `./scripts/create_kafka_topics.sh --dry-run`: passed and printed the five expected topic creation commands.
- `docker compose --profile core up -d`: initially failed because host port `5432` was already in use.
- `docker compose --profile core up -d`: passed after changing host database port defaults to `55432` and `55433`.
- `./scripts/verify_env.sh`: passed with `timescaledb`, `kafka`, `api`, and `frontend` healthy.
- `./scripts/create_kafka_topics.sh`: passed and created `raw-aq-readings`, `processed-aq-readings`, `raw-aq-readings-dlq`, `weather-data`, and `pipeline-events`.
- `docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --list | sort`: passed and listed all five expected topics.

### Plan changes

- Added the `observed` profile as an architecture-preserving placeholder because `docs/himalayaair-system-overview.md` defines it, even though the Phase 02 checklist only named the other profiles.
- Added configurable host port environment variables with safe local defaults after the first core startup found an existing PostgreSQL service on `5432`.
- Ran actual core profile startup and Kafka topic creation in addition to the required dry-run checks.
- No application service logic, database schema, ingestion, Spark processing, Airflow DAGs, API endpoints, forecasting, or frontend product behavior was introduced.

### Phase result

Phase 02 is complete. The core infrastructure profile starts successfully, required verification passed, and the next phase is safe to start after reviewing this summary.

## PHASE-01 Data Reality Check and Source Validation - 2026-04-28

### Files changed

- `scripts/source_validation.py`: Added shared dataclasses, HTTP JSON client, OpenAQ and Open-Meteo source clients, normalization helpers, coverage-mode recommendation logic, and JSON report helpers.
- `scripts/sync_openaq_metadata.py`: Added dry-run OpenAQ Kathmandu location and sensor discovery without database writes.
- `scripts/check_openaq_coverage.py`: Added Kathmandu observed coverage reporting using sensor metadata or sensor measurement endpoint sampling.
- `scripts/check_openmeteo_aq.py`: Added Open-Meteo modeled AQ availability validation labeled as `openmeteo_cams` and `modeled`.
- `scripts/__init__.py`: Added a package marker so tests can import script utilities.
- `fixtures/sample_openaq_location.json`: Added an offline OpenAQ locations schema fixture with nested sensors.
- `fixtures/sample_openaq_measurement.json`: Added an offline OpenAQ sensor measurement schema fixture.
- `fixtures/sample_openmeteo_aq.json`: Added an offline Open-Meteo AQ fixture for modeled fallback tests.
- `tests/conftest.py`: Added minimal test path setup for the repository skeleton.
- `tests/unit/test_source_validation.py`: Added offline unit tests for OpenAQ normalization, modeled AQ normalization, and coverage-mode priority logic.
- `docs/data-source-validation.md`: Added manual source-validation workflow, expected outputs, coverage-mode interpretation, and replay dataset strategy.
- `docs/phase-summaries/PHASE-01-summary.md`: Added the Phase 01 completion summary.
- `CHANGELOG.md`: Recorded Phase 01 implementation, verification, live OpenAQ closure results, and plan deviations.

### Reason

Phase 01 requires a repeatable source-validation workflow before ingestion or database work begins. The project must discover real OpenAQ stations and sensors, measure observed freshness honestly, validate modeled fallback availability, and document when credentials or live coverage are unavailable.

### Impact

Future phases can build sensor-based OpenAQ ingestion against normalized station and sensor metadata instead of hardcoded station assumptions. The modeled fallback path is explicitly separated from observed data and reports `MODELED_BASELINE` only for Open-Meteo/CAMS modeled AQ.

### Verification performed

- `python scripts/check_openaq_coverage.py --help`: passed.
- `python scripts/check_openmeteo_aq.py --help`: passed.
- `python scripts/sync_openaq_metadata.py --help`: passed.
- `python -m py_compile scripts/source_validation.py scripts/sync_openaq_metadata.py scripts/check_openaq_coverage.py scripts/check_openmeteo_aq.py`: passed.
- `pytest tests/unit -q`: passed with 5 tests.
- `python scripts/sync_openaq_metadata.py --dry-run --fixture-location fixtures/sample_openaq_location.json`: passed and produced valid JSON.
- `python scripts/check_openaq_coverage.py --fixture-location fixtures/sample_openaq_location.json --fixture-measurement fixtures/sample_openaq_measurement.json`: passed and produced valid JSON with `STATION_ONLY` for sparse observed fixture coverage.
- `python scripts/check_openmeteo_aq.py --fixture fixtures/sample_openmeteo_aq.json`: passed and produced valid JSON with `MODELED_BASELINE`.
- `python scripts/check_openmeteo_aq.py`: initially failed in the sandbox due DNS/network restriction, then passed with approved network escalation and returned `MODELED_BASELINE` with all requested variables available.
- `OPENAQ_API_KEY` environment check: blocked live OpenAQ validation because the key was not present in the environment.
- `python scripts/check_openaq_coverage.py --metadata-only`: exited 2 with the expected message that `OPENAQ_API_KEY` is required for live OpenAQ validation calls.
- `set -a; source .env; set +a; python scripts/sync_openaq_metadata.py --dry-run --output tmp/openaq-metadata.json`: passed with approved network escalation after the OpenAQ key was added to local `.env`; discovered 52 Kathmandu-bounds locations and 256 sensors.
- `set -a; source .env; set +a; python scripts/check_openaq_coverage.py --modeled-available --output tmp/openaq-coverage.json`: passed with approved network escalation; measured 1 fresh station, 4 recent stations, and `recommended_coverage_mode=RECENT_OBSERVED`.
- `python -m json.tool tmp/openaq-metadata.json` and `python -m json.tool tmp/openaq-coverage.json`: passed; generated reports are valid JSON and remain uncommitted under ignored `tmp/`.

### Plan changes

- Added `scripts/source_validation.py` as a shared Phase 01 utility module so the three CLI scripts and tests use one normalization path.
- Added `fixtures/sample_openmeteo_aq.json` to keep modeled fallback tests offline, although the phase only explicitly named OpenAQ fixtures.
- Added `tests/conftest.py` because the repository skeleton did not yet have Python package/test path configuration.
- No architecture changes were made.
- No future-phase implementation was introduced.

### Phase result

Phase 01 implementation and live OpenAQ closure are complete. Live coverage is currently sparse but usable as `RECENT_OBSERVED`: 1 fresh station, 4 recent stations, and modeled fallback available. The next phase is safe to start.

## PHASE-00 Codex Governance and Repository Contract - 2026-04-28

### Files changed

- `AGENTS.md`: Existing Codex standing instructions verified as the repository contract.
- `docs/himalayaair-system-overview.md`: Existing architecture source of truth verified.
- `docs/codex/PHASE_INDEX.md`: Existing one-phase workflow index verified.
- `docs/codex/phases/`: Existing phase instruction directory verified.
- `docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md`: Existing summary template verified.
- `.gitignore`: Added local secret, cache, build, log, and editor exclusions.
- `.env.example`: Added blank environment variable contract with no committed secrets.
- `README.md`: Added repository skeleton and phase workflow entrypoint.
- `api/.gitkeep`, `services/.gitkeep`, `frontend/.gitkeep`, `airflow/.gitkeep`, `spark/.gitkeep`, `db/.gitkeep`: Added trackable empty skeleton directories for future phases.
- `docs/phase-summaries/PHASE-00-summary.md`: Added the Phase 00 completion summary.
- `CHANGELOG.md`: Created phase history file.

### Reason

Phase 00 requires an AI-readable repository contract, documentation structure, changelog, safe environment template, and bootstrap folder layout before implementation starts.

### Impact

Future Codex sessions can follow the one-phase workflow, locate the authoritative architecture and phase instructions, and avoid committing local secrets or generated files.

### Verification performed

- `test -f AGENTS.md`: passed.
- `test -f docs/himalayaair-system-overview.md`: passed.
- `test -f CHANGELOG.md`: passed.
- `test -d docs/codex/phases`: passed.
- `test -d docs/phase-summaries`: passed.
- `test -f AGENTS.md && test -f docs/himalayaair-system-overview.md && test -f CHANGELOG.md && test -d docs/codex/phases && test -d docs/phase-summaries && test -f docs/phase-summaries/PHASE-00-summary.md`: passed.
- `find api services frontend airflow spark db -maxdepth 2 -type f | sort`: confirmed only `.gitkeep` placeholders exist in skeleton directories.
- `rg -n "(OPENAQ_API_KEY|FIRMS_MAP_KEY|VITE_MAPBOX_TOKEN)=.\\S" .env.example || true`: no non-empty secret/token values found.
- `git status --short`: confirmed Phase 00 files are untracked until reviewed and committed; no existing tracked implementation files were modified.

### Plan changes

- No architecture changes were made.
- No future-phase implementation was introduced.

### Phase result

Phase 00 exit criteria are met. The next phase is safe to start after this phase is reviewed and committed.
