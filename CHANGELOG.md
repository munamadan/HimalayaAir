# Changelog

All meaningful project changes are recorded here so future Codex sessions can resume with the implemented phase history.

## Post-Phase-14 Forced 48-Hour ML Placeholder Forecast - 2026-07-26

### Files changed

- `services/forecasting/models.py`: Added the explicit `hist_gradient_boosting_placeholder` forecast model enum value.
- `services/forecasting/config.py`: Changed the default forecast horizon to 48 hours and added blank `FORECAST_FORCE_MODEL` parsing.
- `services/forecasting/model_selection.py`: Added a demo-only forced model branch that bypasses normal arbitration only when `FORECAST_FORCE_MODEL=ml_placeholder` is set.
- `services/forecasting/ml_gbt.py`: Added the deterministic untrained ML-style 48-hour forecast builder with lag, rolling, diurnal, weather, modeled-AQ, station-offset, and horizon features.
- `services/forecasting/run_once.py`: Routed the forced placeholder model into the normal forecast run path.
- `.env.example` and `docker-compose.yml`: Documented `FORECAST_FORCE_MODEL` and changed the Compose forecast horizon default to 48 hours.
- `tests/forecasting/test_model_selection.py`, `test_persistence.py`, `test_modeled_bias.py`, and `test_ml_gbt_placeholder.py`: Updated expectations to 48 hours and covered forced placeholder selection, labels, deterministic output, and feature-vector contents.
- `docs/phase-summaries/POST-PHASE-14-ml-placeholder-forecast-summary.md`: Added this maintenance-session summary.

### Reason

The final-year project needs a visible 48-hour ML-style forecast code path for the report and demo, but laptop resources and sparse observed coverage make real model training unreliable right now. The safe implementation is a forced, clearly labeled placeholder that proves the forecasting path without pretending a trained model is running.

### Impact

Normal forecast arbitration remains SARIMAX first, then modeled AQ bias, then persistence. The ML placeholder is used only when explicitly forced with `FORECAST_FORCE_MODEL=ml_placeholder`; API rows then expose `hist_gradient_boosting_placeholder`, `synthetic_untrained_ml_placeholder`, and fallback text stating that the forecast is untrained and not learned from HimalayaAir data. Forecast horizon defaults are now 48 hours. No frontend files were changed.

### Verification performed

- `python -m py_compile services/forecasting/*.py`: passed.
- `pytest tests/forecasting -q`: passed, 13 tests.
- `pytest -q`: passed, 77 tests.
- `docker compose --profile core config --quiet`: passed.
- `FORECAST_FORCE_MODEL=ml_placeholder FORECAST_HORIZON_HOURS=48 timeout 20s python -m services.forecasting.run_once --dry-run`: passed; two stations selected the labeled placeholder and the dry run completed successfully.
- `git diff --check`: passed.

## Post-Phase-14 Welcoming Air-Quality Map UI - 2026-07-19

### Files changed

- `frontend/package.json` and `frontend/package-lock.json`: Added `lucide-react` for familiar, accessible product controls.
- `frontend/src/App.tsx`: Reworked the first viewport into a welcoming AQI status panel over a full-screen Kathmandu Valley map, added station selection, clearer live/update context, health guidance, and icon-led Now/Forecast/History navigation.
- `frontend/src/components/LiveMap.tsx`: Replaced the text layer menu with compact AQI, wind, station, and reset-map icon controls; kept station selection and provenance-aware map behavior; added a friendly basemap connectivity fallback.
- `frontend/src/components/TimelineSlider.tsx`: Added Lucide play/pause controls and fixed the conditional React hook lint failure.
- `frontend/src/components/StationPopup.tsx` and `frontend/src/components/MetricCard.tsx`: Added compact icon actions and a more scannable selected-place/current-summary presentation.
- `frontend/src/components/ForecastPanel.tsx` and `frontend/src/components/Pm25Chart.tsx`: Aligned chart tooltip styling with the shared visual system.
- `frontend/src/styles/global.css`: Replaced accumulated dashboard overrides with one responsive green, sky, coral, and AQI-color product system covering the map shell, station sheet, timeline, tabs, details panels, forecast, history, loading, errors, and mobile layouts.
- `docs/phase-summaries/POST-PHASE-14-welcoming-map-ui-summary.md`: Added the maintenance-session implementation and verification summary.

### Reason

The public frontend needed to feel more approachable and product-like, using the immediate AQI hierarchy of air-quality products and the map-led interaction model of modern weather tools without copying another product's branding.

### Impact

HimalayaAir now opens with a clear AQI reading, health guidance, station jump control, live/update context, and direct forecast action over the map. Map layers use familiar icon controls, selected-station details remain compact, and the lower experience is organized around current conditions, forecast planning, and historical exploration. Existing provenance modes, API contracts, ingestion, forecasting, and replay behavior are unchanged.

### Verification performed

- `npm --prefix frontend run build`: passed; Vite reported the existing large-chunk warning.
- `npm --prefix frontend run lint`: passed.
- `npm --prefix frontend run test -- --run`: passed, 4 tests.
- Playwright production-origin audit at `1440x1000` and `390x844`: passed with no viewport overflow or checked control overlaps.
- Playwright interaction checks: Forecast tab visible, 53 station options loaded, and the selected-station sheet opened.
- `docker compose --profile core up -d --build frontend`: passed; frontend and API containers were recreated healthy.
- `./scripts/verify_env.sh --profile core`: passed after the frontend healthcheck settled.
- `curl http://localhost:3000` and `curl http://localhost:8000/health`: passed with HTTP 200.

## Wind Particle Animation — 2026-07-18

### Files changed

- `services/api/wind_grid.py` (new): Fetches a 6×8 wind vector grid from Open-Meteo for the Kathmandu Valley, converts speed/direction to u/v components, caches for 15 minutes.
- `services/api/models.py`: Added `WindGridPoint` and `WindGridResponse` Pydantic models.
- `services/api/main.py`: Added `GET /api/weather/wind-grid` endpoint.
- `frontend/src/lib/windParticles.ts` (new): Canvas 2D particle flow renderer with bilinear interpolation over the wind vector grid, ~800 particles, trailing fade effect.
- `frontend/src/types/api.ts`: Added `WindGridPoint` and `WindGridResponse` interfaces.
- `frontend/src/services/api.ts`: Added `getWindGrid()` API client function.
- `frontend/src/services/mapEngine.ts`: Extended `MapInstance` interface with `project`, `unproject`, `on`/`off` for move/resize events.
- `frontend/src/hooks/useDashboardData.ts`: Fetches wind grid alongside other dashboard data.
- `frontend/src/components/LiveMap.tsx`: Replaced CSS wind-drift overlay with canvas-based particle renderer integrated with map projection.
- `frontend/src/App.tsx`: Passes `windGrid` prop to `LiveMap`.
- `frontend/src/styles/global.css`: Removed `.wind-flow-overlay` CSS animation, added `.wind-particle-canvas` positioning.

### Reason

The original wind layer was a CSS-only illusion (uniform parallel lines in one direction). The new implementation shows real spatially-varying wind flow across the valley using actual Open-Meteo forecast vectors, rendered as Windy-style flowing particles.

## Post-Phase-14 Map-First Product UI Redesign - 2026-07-09

### Files changed

- `frontend/src/App.tsx`: Reworked the public dashboard into a map-first product shell with a compact header, default AQI heatmap/wind/station layers, product tabs for overview/forecast/history, and no pipeline/provenance/method sections.
- `frontend/src/components/LiveMap.tsx`: Added a Windy-style layer menu, default wind context overlay, tighter Kathmandu/Lalitpur/Bhaktapur-focused bounds, stronger AQI heatmap rendering, and text-first station labels.
- `frontend/src/components/StationPopup.tsx`, `ForecastPanel.tsx`, `Pm25Chart.tsx`, `HistoricalExplorer.tsx`, and `ErrorPanel.tsx`: Replaced technical dashboard wording with user-facing AQI, health, trend, forecast, and history language.
- `frontend/src/hooks/useDashboardData.ts`, `frontend/src/services/api.ts`, and `frontend/src/types/api.ts`: Removed pipeline health loading and frontend pipeline response wrappers from the public dashboard path.
- `frontend/src/lib/aqi.ts` and `frontend/src/lib/aqi.test.ts`: Added product-facing data-mode labels and concise AQI health advice helpers.
- `frontend/src/styles/global.css`: Added the full-viewport map layout, compact product header, layer drawer, wind overlay, station sheet, legend, and responsive map-first styling.
- Deleted unused public frontend components for the old technical dashboard: `CoverageRibbon`, `GreetingSummaryDialog`, `PipelineHealth`, `ProvenancePanel`, and `WindRose`.
- `docs/phase-summaries/POST-PHASE-14-map-first-product-ui-summary.md`: Added this maintenance session summary.

### Reason

The frontend needed to feel like a real air-quality map product rather than a data engineering project dashboard. The first screen should be the map, with AQI heatmap and wind context on by default, compact station details, and no visible pipeline/provenance terminology.

### Impact

The app now opens on a near full-screen Kathmandu Valley map with product-facing AQI labels, Windy-style map controls, a compact station sheet, and simplified overview/forecast/history panels below the map. Backend provenance, source modes, and pipeline endpoints remain unchanged; only the public React UI was simplified.

### Verification performed

- `npm --prefix frontend run build`: passed.
- `npm --prefix frontend run lint`: passed.
- `npm --prefix frontend run test -- --run`: passed.
- `npm --prefix frontend run dev -- --port 3001`: passed with elevated local socket access; Vite served `http://localhost:3001/`.
- `curl -sS -o /dev/null -w '%{http_code}' http://localhost:3001/`: passed with elevated local socket access (`200`).

## Post-Phase-14 Data Source Outreach Emails - 2026-07-09

### Files changed

- `data-source-outreach-emails.txt`: Added copy-paste-ready outreach emails for OpenAQ, Australian Embassy in Nepal, International French School of Kathmandu, GD Labs, AE RESEARCH, and an IQAir follow-up request.

### Reason

The project needs practical outreach text for requesting Kathmandu Valley observed air-quality data access from likely station owners and data platforms.

### Impact

Dipan Kharel now has plain-text messages with verified contact routes where available and clear notes where public emails were not verified. No code, schemas, API behavior, or data provenance rules were changed.

### Verification performed

- `sed -n '1,260p' data-source-outreach-emails.txt`: passed.
- `rg -n "\\[|\\]|Your Name|PLACEHOLDER|TODO" data-source-outreach-emails.txt`: passed with no matches.

## Post-Phase-14 Modeled Map Visibility and Replay Demo Reliability - 2026-06-07

### Files changed

- `frontend/src/App.tsx`: Auto-enables the AQI heatmap for a modeled baseline interpolation response until the user manually changes the heatmap toggle.
- `frontend/src/components/LiveMap.tsx`, `frontend/src/services/mapEngine.ts`, and `frontend/src/styles/global.css`: Added a compact modeled baseline map chip, stronger modeled raster opacity, and map paint updates while keeping station layers above the raster.
- `services/replay_publisher/main.py`: Made Kafka publishing to `raw-aq-readings` the default replay path, added explicit `--publish-mode direct-db-fallback`, and added `--rebase-to-now` for current defense-day replay without removing original timestamp provenance.
- `tests/openaq/test_replay_direct_ingest.py`: Added focused tests for Kafka-first publishing, explicit direct DB fallback, and timestamp rebasing provenance.
- `docker-compose.yml`: Added `SYNC_DATABASE_URL` to `replay-publisher` so explicit direct DB fallback can run inside Compose when needed.
- `scripts/run_replay_demo.sh`: Added a single helper that starts core+stream profiles, creates Kafka topics, publishes replay fixture rows through Kafka, and verifies API/frontend-visible replay provenance.
- `docs/demo-script.md` and `docs/final-defense-script.md`: Updated the defense runbook to use the Kafka-first helper and name direct DB ingestion as fallback only.
- `docs/phase-summaries/POST-PHASE-14-modeled-map-replay-demo-summary.md`: Added this maintenance session summary and verification notes.

### Reason

Modeled baseline map output was too easy to miss when observed coverage was sparse, and the replay demo path had drifted back toward direct DB ingestion despite the approved Kafka/Spark defense architecture.

### Impact

Modeled fallback maps now show a visible raster by default with honest `MODELED_BASELINE` labeling. Replay fixture demos publish to Kafka by default, Spark can persist them when the stream profile is running, and direct DB replay is clearly marked as an emergency fallback. Replay rows remain labeled `demo_replay`, `replay`, `REPLAY_DEMO`, and `demo`.

### Verification performed

- `npm --prefix frontend run build`: passed.
- `npm --prefix frontend run lint`: passed.
- `python -m py_compile services/replay_publisher/main.py`: passed.
- `python -m services.replay_publisher.main --dry-run --fixture fixtures/replay_sample.json`: passed.
- `python -m services.replay_publisher.main --dry-run --fixture fixtures/replay_sample.json --rebase-to-now`: passed.
- `pytest tests/openaq/test_replay_direct_ingest.py -q`: passed.
- `pytest tests/openaq tests/unit -q`: passed.
- `bash -n scripts/run_replay_demo.sh`: passed.
- `docker compose --profile core --profile stream config --quiet`: passed.
- `./scripts/run_replay_demo.sh --wait-seconds 90`: passed with elevated Docker access; Kafka published three replay messages, API reported `replay_active=true`, station replay rows were verified as `REPLAY_DEMO`, and frontend returned HTTP 200. Valley/interpolation coverage remained `MODELED_BASELINE` because modeled fallback data was also available.
- `./scripts/run_replay_demo.sh --skip-compose-up --wait-seconds 90`: passed with elevated Docker access against the running core+stream stack.

## Post-Phase-14 Compact Map and Location Greeting - 2026-06-07

### Files changed

- `frontend/src/App.tsx`: Added session-scoped first-open greeting state, browser geolocation lookup, health-advisory integration, nearest/default forecast station selection, and controlled forecast station state.
- `frontend/src/components/GreetingSummaryDialog.tsx`: Added first-open summary dialog with current AQI/provenance fields and a 72-hour PM2.5 forecast summary for the selected forecast station.
- `frontend/src/components/ForecastPanel.tsx`: Changed the forecast panel to accept a controlled station id from `App` while still allowing manual station changes.
- `frontend/src/components/LiveMap.tsx` and `frontend/src/services/mapEngine.ts`: Added Kathmandu Valley map bounds and minimum zoom support through the local map adapter.
- `frontend/src/services/api.ts` and `frontend/src/types/api.ts`: Added typed frontend support for `GET /api/health-advisory`.
- `frontend/src/styles/global.css`: Converted the command bar into a persistent fixed widget, compacted the map section, added responsive mobile offsets, and styled the greeting dialog.
- `docs/phase-summaries/POST-PHASE-14-compact-map-location-greeting-summary.md`: Added this maintenance session summary and verification notes.

### Reason

The first screen needed to shift from a full-height map hero to a compact Kathmandu Valley map while keeping the greeting/navigation controls available during scrolling. The forecast experience also needed to use the user's browser location when permitted, with honest fallback to the default Kathmandu station.

### Impact

The dashboard now opens with a compact bounded Kathmandu Valley map, a fixed greeting/menu widget, and a first-open dialog that summarizes current AQI/provenance and PM2.5 forecast context. Browser location permission selects the nearest station through the existing health-advisory API; denial or failure is surfaced as default-station fallback text. No backend API, schema, ingestion, or forecast model behavior was changed.

### Verification performed

- `npm --prefix frontend run build`: passed.
- `npm --prefix frontend run lint`: passed.
- `npm --prefix frontend run test -- --run`: passed.
- `docker compose --profile core up -d --build`: passed with elevated Docker access.
- `./scripts/verify_env.sh --profile core`: passed with elevated Docker/local socket access.
- `docker compose ps`: passed with `api`, `frontend`, `timescaledb`, and `worker` healthy.
- `curl -sS -o /dev/null -w '%{http_code}' http://localhost:3000`: passed (`200`).
- `curl -sS -o /dev/null -w '%{http_code}' http://localhost:8000/health`: passed (`200`).
- `curl -sS http://localhost:3000 | rg -n "HimalayaAir|Welcome to nginx"`: passed with HimalayaAir markers and no default Nginx page.
- `curl -sS 'http://localhost:8000/api/health-advisory?lat=27.71&lon=85.32'`: passed and returned health-advisory JSON with coverage metadata and a nearest station.

## Post-Phase-14 Fire Layer Removal - 2026-06-04

### Files changed

- `frontend/src/App.tsx`: Removed fire-layer toggle state and LiveMap props.
- `frontend/src/components/LiveMap.tsx`: Removed the fire GeoJSON source, fire circle layer, fire layer update effect, and fire toggle control.
- `frontend/src/hooks/useDashboardData.ts`: Removed dashboard fire-event fetching and state.
- `frontend/src/services/api.ts` and `frontend/src/types/api.ts`: Removed unused frontend `/api/events` client helper and fire event response types.
- `frontend/src/components/HistoricalExplorer.tsx`, `frontend/src/components/HistoricalTimeSeries.tsx`, and `frontend/src/lib/historical.ts`: Removed fire-event historical annotations, event fetches, and related annotation kind support.
- `frontend/src/styles/global.css`: Removed fire annotation band styling.
- `docs/phase-summaries/POST-PHASE-14-smooth-map-drag-refactor-summary.md`: Updated the current maintenance summary to reflect station-only map overlays.

### Reason

The fire layer is no longer needed in the product UI and should not consume frontend state, API calls, map layers, controls, or historical annotation space.

### Impact

The frontend no longer calls `/api/events` or renders fire overlays anywhere. The live map is now station markers plus optional AQI heatmap only. Backend FIRMS ingestion/API code remains intact because removing those data-pipeline pieces would be a broader architecture change.

### Verification performed

- `rg -n "fire|Fire|FIRES|himalayaair-fires|getEvents|EventsResponse|FireEvent|showFire|eventPromise|/api/events" frontend/src`: passed with no matches.
- `npm --prefix frontend run build`: passed.
- `npm --prefix frontend run lint`: passed.

## Post-Phase-14 Smooth Map Drag Refactor - 2026-06-04

### Files changed

- `frontend/src/components/LiveMap.tsx`: Replaced DOM station and fire markers with MapLibre/Mapbox GeoJSON sources and WebGL circle/symbol layers, preserved station click selection and pointer cursor behavior, kept selected-station popup updates lightweight, and inserted heatmap raster below station layers.
- `frontend/src/services/mapEngine.ts`: Extended the local map abstraction with GeoJSON `setData`, layer-specific events, canvas access, and optional layer insertion order.
- `frontend/src/App.tsx`: Changed the default AQI heatmap state to off.
- `frontend/src/styles/global.css`: Removed obsolete DOM marker styles now that stations and fire points render inside the map canvas.

### Reason

Station and fire points were rendered as DOM overlay markers, which could visually lag behind the map during mouse drag. Moving those points into native map layers keeps them attached to the WebGL map canvas and prioritizes interaction smoothness.

### Impact

The map now renders station AQI circles, AQI labels, selected-station highlight, and fire points as native map layers. Station clicks still update the selected-station side panel. The AQI heatmap remains available through the existing toggle, but starts disabled and uses lower-cost raster paint settings when enabled.

### Verification performed

- `npm --prefix frontend run build`: passed.
- `npm --prefix frontend run lint`: passed.
- `docker compose --profile core up -d --build`: passed with elevated Docker access.
- `docker compose ps`: passed with `api`, `frontend`, `timescaledb`, and `worker` healthy.
- `curl -sS -o /dev/null -w '%{http_code}' http://localhost:3000`: passed (`200`) with elevated local socket access.
- `curl -sS -o /dev/null -w '%{http_code}' http://localhost:8000/health`: passed (`200`) with elevated local socket access.
- `./scripts/verify_env.sh --profile core`: passed with elevated Docker/local socket access.

## Post-Phase-14 Frontend Map-First UI Refactor - 2026-06-04

### Files changed

- `frontend/src/App.tsx`: Replaced the previous hero-first dashboard shell with a map-led control room layout, place-based Kathmandu greeting, compact coverage/status strip, refresh action, and floating selected-station panel.
- `frontend/src/components/LiveMap.tsx`: Simplified the map chrome into compact layer controls and switched the initial map camera to a flatter navigation-map presentation.
- `frontend/src/services/mapEngine.ts`: Changed default MapLibre/Mapbox styles from dark basemaps to light basemaps.
- `frontend/src/styles/global.css`: Replaced the dark teal glass theme with a lighter Nepal Editorial visual system, roomier spacing, map-first responsive layout, and updated component styling.

### Reason

The previous frontend felt congested, overly dark, and too much like a landing/dashboard hybrid. The requested direction was a cleaner Google Maps-like control room with a greeting, calmer colors, and the map as the first-viewport product surface.

### Impact

The app now opens on a large Kathmandu map with floating navigation, live status, AQI layer controls, and station detail context. Historical, forecast, provenance, wind, pipeline, and method content remain available below the map without changing backend APIs or data provenance behavior.

### Verification performed

- `npm --prefix frontend run build`: passed.
- `npm --prefix frontend run lint`: passed.
- `docker compose --profile core up -d --build`: passed.
- `./scripts/verify_env.sh --profile core`: passed with elevated Docker access.
- `curl -sS -o /dev/null -w '%{http_code}' http://localhost:3000`: passed (`200`).
- `curl -sS -o /dev/null -w '%{http_code}' http://localhost:8000/health`: passed (`200`).

## Architecture Reset Session 1 Refinement - Worker Scheduling and Health Stabilization - 2026-05-25

### Files changed

- `services/worker/main.py`: Replaced sequential blocking loop with concurrent per-component async loops (`openaq`, `weather`, `forecast`) using fixed-rate scheduling, per-component enable flags, and isolated failure/backoff behavior.
- `services/worker/health_server.py`: Added worker health state model and `/health` HTTP server with aggregate status and per-component runtime/metrics fields.
- `services/api/config.py`: Added `API_WORKER_HEALTH_URL` and `API_EXTERNAL_HEALTH_MODE` settings.
- `services/api/health_checks.py`: Added worker-mode external health checks that map worker component health into stable `openaq_poller`, `weather_poller`, and `openmeteo_aq_poller` keys; kept legacy URL checks available behind mode selection.
- `docker-compose.yml`: Added worker healthcheck and worker runtime env defaults (`WORKER_ENABLE_*`, backoff, and health host/port), and set API external health defaults for worker mode in core runtime.
- `.env.example`: Documented new API/worker health and worker scheduling/backoff environment variables.
- `tests/worker/test_worker_runtime.py`: Added worker scheduling/backoff/health aggregation tests.
- `tests/api/test_external_health_worker_mapping.py`: Added worker-health mapping unit test for API external checks.
- `tests/api/conftest.py`: Updated API settings fixtures for new config fields.

### Reason

The monolith worker introduced in Architecture Reset Session 01 still used one sequential blocking loop, which allowed one failing/slow component to delay all others and did not provide worker-level health truth for core runtime pipeline checks.

### Impact

Core runtime now has isolated component loops with deterministic fixed-rate scheduling that skips catch-up bursts, per-component exponential backoff, and worker-native `/health` observability. API pipeline external checks can use worker health as the source of truth while preserving the existing response shape and service key contract.

### Verification performed

- `pytest -q tests/worker/test_worker_runtime.py tests/api/test_external_health_worker_mapping.py tests/api/test_health_events_websocket_contract.py`: passed.
- `pytest -q`: passed (71 tests).
- `docker compose --profile core config --quiet`: passed.
- `docker compose --profile legacy config --quiet`: passed.
- `docker compose --profile core up -d --build`: passed.
- `./scripts/verify_env.sh --profile core`: passed.
- `npm --prefix frontend run build`: passed.
- `docker compose exec -T worker python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:9093/health', timeout=3).read().decode())"`: passed.
- `docker compose exec -T api python -c "import urllib.request, json; data=json.loads(urllib.request.urlopen('http://127.0.0.1:8000/api/pipeline/health', timeout=5).read().decode()); print(data['checks']['external_services'])"`: passed and confirmed worker-derived mapping keys.

## Post-Phase-14 Data Pipeline Startup Fixes - 2026-05-09

### Files changed

- `docker-compose.yml`: Added explicit host-network build mode for project-built images, added Kafka to the `demo` profile, removed Spark runtime Maven resolution, and set Spark Ivy/HOME paths to writable absolute locations.
- `services/api/repository.py`: Cast optional pollutant bind parameters in historical AQ queries so asyncpg can prepare station and valley history SQL reliably.
- `services/spark/Dockerfile`: Pre-resolves Spark Kafka connector jars during image build, keeps them on Spark's runtime classpath, adds a named UID 1001 user entry for compatibility, and runs the local Spark stream container as root so named checkpoint volumes can be created reliably.
- `shared/time_utils.py`: Replaced the Python 3.11-only `datetime.UTC` import with a Python 3.10-compatible `timezone.utc` alias for the Spark base image.

### Reason

Observed, weather, demo, and stream profiles did not reliably start. Builds failed on Docker DNS during dependency installation, Spark restarted on invalid Ivy cache paths, runtime Maven access, Python 3.10 incompatibility, missing UID metadata, and checkpoint-volume permissions. The demo profile also omitted Kafka even though replay publishing depends on it. A replay-backed API history check also exposed an asyncpg ambiguous-parameter error in optional pollutant filters.

### Impact

Core, observed, weather, stream, and demo profile startup is now reproducible in the local Docker environment when public DNS is available during image builds. Spark no longer depends on Maven access at container startup, and replay fixture records now flow through Kafka and Spark into TimescaleDB with `REPLAY_DEMO` provenance.

### Verification performed

- `docker compose --profile full config --quiet`: passed.
- `docker compose --profile observed --profile weather --profile stream up -d --build`: passed after fixes.
- `./scripts/verify_env.sh --profile observed`: passed.
- `./scripts/verify_env.sh --profile weather`: passed.
- `./scripts/verify_env.sh --profile stream`: passed.
- `docker compose --profile demo config --quiet`: passed.
- `docker compose --profile demo run --rm replay-publisher python -m services.replay_publisher.main --fixture fixtures/replay_sample.json --speed 60`: passed.
- TimescaleDB verification after replay: `aq_readings` increased from 0 to 3 replay rows.
- `curl 'http://localhost:8000/api/stations/1/history?pollutant=pm25&hours=4000'`: passed after rebuilding the API image.
- External live polling remains blocked by local DNS resolution failures for `api.openaq.org`, `api.open-meteo.com`, and `air-quality-api.open-meteo.com`; pollers report these failures visibly in logs and pipeline status.

## PHASE-14 Frontend Reset Script for Nginx Fallback - 2026-05-06

### Files changed

- `scripts/reset_frontend.sh`: Added deterministic frontend-only recovery script that rebuilds/recreates `frontend`, waits for health, and verifies HimalayaAir HTML markers while rejecting default `Welcome to nginx` content.
- `README.md`: Added a frontend recovery section with the one-command fix path.

### Reason

`localhost:3000` intermittently appeared as default Nginx despite the expected frontend container. A repeatable, low-scope recovery path was needed.

### Impact

Developers now have a single command to recover frontend runtime state without restarting the full stack or deleting local data. The script also fails fast with diagnostics when content verification fails.

### Verification performed

- `./scripts/reset_frontend.sh`: passed in a running core environment.
- `curl -sS http://localhost:3000 | rg -n "HimalayaAir|Welcome to nginx"`: passed with HimalayaAir markers and no default nginx content.

## PHASE-14 Hardening, Benchmarks, Documentation, and Delivery - 2026-05-06

### Files changed

- `benchmarks/query_benchmark.py`: Added continuous aggregate vs raw SQL benchmark CLI with latency percentiles and row-count output.
- `benchmarks/api_load_test.py`: Added async ~20-user load test CLI for core read endpoints with non-2xx/error-rate and latency summaries.
- `benchmarks/seed_repro_data.py`: Added deterministic seed/check workflow for reproducible benchmark setup and table-count snapshots.
- `docker-compose.yml`: Removed stale unused `x-python-placeholder` compose anchor.
- `README.md`: Expanded to defense-ready architecture/setup/env/verification/limitations/screenshot documentation.
- `docs/benchmark-results.md`: Added benchmark workflow, artifact contract, and reproducibility notes.
- `docs/final-defense-script.md`: Added timed final-defense walkthrough script.
- `docs/screenshots/README.md` and `docs/screenshots/*.png`: Added screenshot capture guide and placeholder PNGs.
- `docs/phase-summaries/PHASE-14-summary.md`: Added Phase 14 completion summary and exit checklist.

### Reason

Phase 14 requires final hardening and delivery readiness: reproducible benchmark tooling, load-test coverage, cleanup of stale config, and defense-quality documentation without changing public API behavior.

### Impact

HimalayaAir now includes repeatable benchmark/load-test CLIs and delivery docs suitable for defense and recruiter review. The stale compose placeholder anchor was removed. Public REST/WebSocket contracts remain unchanged.

### Verification performed

- `python -m py_compile benchmarks/query_benchmark.py benchmarks/api_load_test.py benchmarks/seed_repro_data.py`: passed.
- `./scripts/verify_env.sh`: failed in this run because core containers were not created/running.
- `pytest -q`: passed (63 tests).
- `npm --prefix frontend run build`: passed.
- `python benchmarks/query_benchmark.py`: failed in this run with `psycopg2.OperationalError` (local DB unavailable).
- `python benchmarks/seed_repro_data.py --skip-compose-up --skip-replay`: completed and recorded DB connection errors in JSON summary.
- `python benchmarks/api_load_test.py --base-url http://127.0.0.1:8765 --concurrency 20 --requests-per-user 2 --timeout-seconds 1 --output tmp/benchmark-results/api-load-test.json`: passed against local temporary HTTP server to validate artifact generation.
- `rg -n "(OPENAQ_API_KEY|FIRMS_MAP_KEY|VITE_MAPBOX_TOKEN|BEGIN PRIVATE KEY|AKIA|AIza|xoxb-)" -S .`: passed with expected references only (no committed secrets).


## PHASE-14 Frontend Docker Runtime Fix (`localhost:3000`) - 2026-05-06

### Files changed

- `frontend/Dockerfile`: Switched frontend build stage from `node:25-alpine` to `node:22` (LTS) and kept deterministic install with `npm ci --no-audit --no-fund`.
- `.dockerignore`: Added repository-level Docker ignore rules to reduce build context size and avoid shipping local artifacts into image builds.

### Reason

`localhost:3000` was serving the default Nginx page from a stale old container image; frontend rebuilds were unstable with Node 25 npm behavior during `npm ci`.

### Impact

Frontend Docker builds are now pinned to stable Node 22 LTS, with leaner build context and lower chance of npm install failures. Rebuilding and recreating `frontend` now serves the Vite-built HimalayaAir app on port 3000, while API runtime contract remains unchanged.

### Verification performed

- `docker compose build frontend api`: failed in this environment due container DNS resolution (`EAI_AGAIN`) during `npm ci` and `pip install`.
- `docker build --network host -f frontend/Dockerfile -t himalayaair-frontend:latest .`: passed.
- `docker build --network host -f services/api/Dockerfile -t himalayaair-api:latest .`: passed.
- `docker compose --profile core up -d --no-build`: passed after removing stale containers and clearing a transient host port `8000` conflict from a leftover `uvicorn` process.
- `docker compose ps`: passed (`api` and `frontend` running/healthy with published ports).
- `curl -sS -o /dev/null -w "%{http_code}" http://localhost:3000`: passed (`200`).
- `curl -sS http://localhost:8000/health`: passed (healthy JSON).
- `curl -sS http://localhost:3000`: passed (contains `HimalayaAir` app content, not Nginx default page).
- `npm --prefix frontend run build`: passed.

## PHASE-13 Replay Demo Mode and Spatial Polish - 2026-05-06

### Files changed

- `services/replay_publisher/main.py`: Added replay publisher CLI with `--fixture`, `--start`, `--end`, `--speed`, `--loop`, and `--dry-run` options that enforce replay provenance and publish to `raw-aq-readings`.
- `services/replay_publisher/Dockerfile` and `services/replay_publisher/__init__.py`: Added runnable service packaging for Docker and module execution.
- `fixtures/replay_sample.json`: Added fixture replay dataset for dry-run and demo publishing checks.
- `docker-compose.yml`: Replaced demo replay placeholder with the real `replay-publisher` service wiring.
- `services/api/models.py`, `services/api/repository.py`, `services/api/service.py`, and `services/api/main.py`: Added weather-driven wind rose API support via `GET /api/weather/wind-rose`.
- `frontend/src/components/LiveMap.tsx`: Added fire-events overlay toggle/markers on top of the existing IDW map layer.
- `frontend/src/components/WindRose.tsx`: Added frontend wind rose panel with graceful no-data fallback.
- `frontend/src/hooks/useDashboardData.ts`: Added fire events and wind rose fetches into dashboard state.
- `frontend/src/services/api.ts` and `frontend/src/types/api.ts`: Added typed client support for wind rose responses.
- `frontend/src/App.tsx`: Added demo-spatial controls wiring and cigarette-equivalence metric display.
- `frontend/src/styles/global.css`: Added fire marker and wind rose styling.
- `docs/demo-script.md`: Added manual demo runbook for replay mode through Kafka/Spark/API/frontend.

### Reason

Phase 13 requires reliable replay-mode demonstrations through the real pipeline and spatial UI polish that keeps provenance visible instead of faking data in the frontend.

### Impact

The project now has a replay publisher service that can validate or publish replay-labeled AQ records into Kafka with controllable windows, speed, and loop behavior. The frontend can visibly toggle fire overlays, surface replay/demo context, display a cigarette-equivalence indicator, and show a wind rose when weather rows are available. API support for wind rose is compact and avoids large geospatial payloads.

### Verification performed

- `python -m services.replay_publisher.main --help`: passed.
- `python -m services.replay_publisher.main --dry-run --fixture fixtures/replay_sample.json`: passed.
- `npm --prefix frontend run build`: passed.
- `python -m py_compile services/replay_publisher/main.py services/api/main.py services/api/models.py services/api/repository.py services/api/service.py`: passed.

## PHASE-12 Historical Explorer and Forecast UI - 2026-05-06

### Files changed

- `frontend/src/components/HistoricalExplorer.tsx`: Added a bounded historical explorer view with valley/station scope, station selector, all-pollutant selector, date-range controls, hourly/daily toggle, annotation toggles, and consistent loading/empty/error rendering.
- `frontend/src/components/CalendarHeatmap.tsx`: Added a D3-backed calendar heatmap with explicit no-data cells and Nepal-local day framing.
- `frontend/src/components/HistoricalTimeSeries.tsx`: Added a D3 zoomable and brushable historical AQI series with annotation overlays.
- `frontend/src/components/ForecastPanel.tsx`: Added an independent-station forecast panel with 72-hour confidence band visualization, model/fallback labeling, and best 6-hour outdoor windows.
- `frontend/src/lib/historical.ts`: Added bounded-range, history normalization, daily aggregation, calendar cell generation, event filtering, and best-window utilities.
- `frontend/src/services/api.ts` and `frontend/src/types/api.ts`: Added typed frontend contracts and API helpers for valley history, events, and station forecasts.
- `frontend/src/App.tsx`: Integrated Historical Explorer and Forecast Panel sections into dashboard navigation and layout.
- `frontend/src/styles/global.css`: Added responsive styling for explorer controls, annotation toggles, D3 chart surfaces, calendar states, and forecast-window cards.
- `frontend/package.json` and `frontend/package-lock.json`: Added D3 and required D3 type packages for explicit frontend chart dependencies.
- `docs/phase-summaries/PHASE-12-summary.md`: Added the Phase 12 completion summary.

### Reason

Phase 12 requires a historical storytelling surface and forecast visualization that stay provenance-aware, bounded in data requests, and explicit about model fallback behavior.

### Impact

The frontend now supports bounded historical exploration with date controls (default 90 days, max 365 days), valley/station comparison, all-pollutant exploration, D3 calendar and zoom/brush timelines, curated Tihar/monsoon/COVID annotation bands, fire-event overlays where events are returned, and a 72-hour forecast panel with confidence context and best-outdoor-window extraction. Missing historical/forecast data is rendered as explicit empty/degraded states rather than implied clean-air values.

### Verification performed

- `npm --prefix frontend install`: first failed in sandbox with DNS (`EAI_AGAIN`), then passed with approved network access to install new D3 dependencies.
- `npm --prefix frontend run build`: passed.
- `npm --prefix frontend run lint || true`: passed.

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

## Architecture Reset Session 1 - Monolith Runtime Path - 2026-05-25

### Files changed

- `services/common/aq_ingestion.py`: Added shared direct-DB AQ ingestion processor that reuses Spark transform logic for AQI, anomaly detection, district assignment, dedup, station/station_sensor updates, and `pipeline_runs` metadata writes.
- `services/openaq_poller/main.py`: Refactored OpenAQ poll flow from Kafka publish to direct DB ingestion through the shared processor.
- `services/replay_publisher/main.py`: Refactored replay path from Kafka publish to direct DB ingestion with replay provenance.
- `services/weather_poller/main.py`: Removed optional Kafka publish behavior and kept direct DB persistence path only.
- `services/api/websocket.py`: Added DB-driven live notifier (`DBLiveFeedNotifier`) and timestamp-advance broadcast for `new_readings` events while keeping websocket event contracts.
- `services/api/main.py`: Replaced Kafka websocket background consumer startup with DB notifier startup.
- `services/api/config.py`: Changed Kafka health default to disabled compatibility mode for the transition session.
- `services/worker/main.py`, `services/worker/__init__.py`, `services/worker/Dockerfile`: Added monolith worker runtime entrypoint and container image.
- `docker-compose.yml`: Added `worker` to default `core` runtime, removed `kafka` from `core`, and moved distributed stack services under explicit `legacy` profile (while retaining existing service definitions).
- `scripts/verify_env.sh`: Updated `core` expected services and added `legacy` profile verification target.
- `scripts/run_direct_tasks.py`: Added direct Python task wrappers for forecast, quality, FIRMS, and backfill tasks without Airflow runtime.
- `tests/unit/test_direct_ingestion_processor.py`: Added direct ingestion processor behavior test.
- `tests/openaq/test_replay_direct_ingest.py`: Added replay direct-ingestion path test.
- `tests/api/test_health_events_websocket_contract.py`: Added DB timestamp-driven `new_readings` websocket emission test.

### Reason

Session 1 of the architecture reset introduces a simplified monolith-style runtime path and keeps public API/websocket contracts stable while retaining legacy distributed services behind an explicit profile.

### Impact

- Default Compose runtime is now `timescaledb + api + worker + frontend`.
- OpenAQ observed ingestion and replay demo ingestion write directly to DB with provenance preserved.
- Weather/model pollers continue direct DB writes with Kafka publish removed.
- `/ws/live-feed` remains stable and now emits `new_readings` based on DB timestamp advancement instead of Kafka processed-batch messages.
- Legacy Kafka/Spark/Airflow services remain available behind `legacy` profile for transition validation.

### Verification performed

- `python -m py_compile services/common/aq_ingestion.py services/openaq_poller/main.py services/replay_publisher/main.py services/api/websocket.py services/api/main.py services/worker/main.py scripts/run_direct_tasks.py`: passed.
- `docker compose config --quiet`: passed.
- `docker compose --profile core config --quiet && docker compose --profile legacy config --quiet`: passed.
- `pytest -q`: passed (66 tests).
- `npm --prefix frontend run build`: passed.
- `./scripts/verify_env.sh --profile core`: failed in this environment because core services were not created/running (`not_created` for all core services).
