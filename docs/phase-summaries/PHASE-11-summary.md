# PHASE-11 Summary - Frontend Core Dashboard

## What was built

- `frontend/package.json` and `frontend/package-lock.json`: Added the Vite React 18 frontend package with TypeScript, Recharts, Mapbox GL, MapLibre GL, ESLint, and Vitest.
- `frontend/index.html`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, and `frontend/eslint.config.js`: Added the frontend build, type-check, lint, and dev-server configuration.
- `frontend/.env.example`: Documented public frontend environment variables for API URL, WebSocket URL, map provider, optional public Mapbox token, and map style URL.
- `frontend/Dockerfile` and `frontend/nginx.conf`: Added a production frontend container that builds the Vite app and serves static assets through Nginx with SPA fallback.
- `frontend/src/services/api.ts`: Added a native fetch wrapper and typed API functions for stations, valley current, interpolation, station current, station history, and pipeline health.
- `frontend/src/services/mapEngine.ts`: Added a Mapbox/MapLibre adapter with MapLibre fallback when no public Mapbox token is configured.
- `frontend/src/hooks/useDashboardData.ts`: Added dashboard state loading for station snapshot, valley state, interpolation, pipeline health, and PM2.5 station histories.
- `frontend/src/hooks/useLiveFeed.ts`: Added native WebSocket state with reconnect backoff and JSON `pong` responses to heartbeat/ping events.
- `frontend/src/hooks/useStationCurrent.ts`: Added selected-station current reading loading.
- `frontend/src/types/api.ts`: Added frontend TypeScript assumptions for Phase 09 and Phase 10 API responses.
- `frontend/src/lib/aqi.ts`, `frontend/src/lib/time.ts`, and `frontend/src/lib/heatmapCanvas.ts`: Added AQI display helpers, time/freshness formatting, and IDW-grid-to-raster image conversion.
- `frontend/src/components/`: Added the dashboard shell pieces: AQI badge/gauge, coverage ribbon, live map, station popup, PM2.5 chart, provenance panel, pipeline health panel, loading state, error panel, and metric cards.
- `frontend/src/styles/global.css`: Added the dark responsive design system, map marker styling, map popup styling, motion, and 375px layout handling.
- `frontend/src/lib/aqi.test.ts`: Added unit tests for AQI category, coverage-mode label, and marker radius helpers.
- `docker-compose.yml`: Replaced the placeholder frontend Nginx image with the real frontend build service while keeping public `VITE_` build arguments only.

## Current system state

The frontend can be run locally with:

```bash
npm --prefix frontend run dev
```

The production build can be generated with:

```bash
npm --prefix frontend run build
```

The dashboard reads the existing FastAPI endpoints:

- `GET /api/stations`
- `GET /api/valley/current`
- `GET /api/interpolation/current?pollutant=pm25`
- `GET /api/stations/{station_id}/current`
- `GET /api/stations/{station_id}/history?pollutant=pm25`
- `GET /api/pipeline/health`
- `WebSocket /ws/live-feed`

The map initializes once, then updates station markers and the heatmap image source in place. The UI displays coverage mode, confidence, freshness, source, observation type, and replay/modeled availability without inventing frontend data.

No Redux, frontend-only fake replay, future historical explorer UI, future forecast panel UI, or fire overlay was added.

## Commands run

```bash
npm --prefix frontend install
# initial sandbox invocation produced no lockfile/node_modules and no useful output
# rerun with approved network as `npm --prefix frontend install --loglevel=info`: passed and created package-lock.json/node_modules
# final exact invocation left no file changes, but the tool session did not return output even though no npm process remained

npm --prefix frontend run build
# failed once because replaceAll required ES2021 while the project targets ES2020
# passed after replacing replaceAll calls with ES2020-compatible regex replacements
# final pass: built Vite production assets; warning remained for large map-engine chunks

npm --prefix frontend run lint || true
# failed once on explicit any types in the map adapter and one cleanup warning
# passed after adding narrow local Mapbox/MapLibre interfaces

npm --prefix frontend run test -- --run
# passed: 1 test file, 3 tests

docker compose --profile core config --quiet
# passed

npm --prefix frontend audit --omit=dev
# failed first in sandbox with registry DNS EAI_AGAIN
# passed with approved network; found 0 production vulnerabilities
```

## Exit criteria verification

- [x] All in-scope tasks are complete or explicitly documented: Vite React app, API wrapper, hooks, design system, navigation, loading/error states, live map, markers, station popup, AQI gauge, PM2.5 chart, WebSocket reconnect/pong behavior, and provenance display are implemented.
- [x] Relevant verification commands were run: required npm install/build/lint commands were run, plus Vitest, Compose config, and production audit checks.
- [x] `CHANGELOG.md` was updated with `PHASE-11 Frontend Core Dashboard`.
- [x] `docs/phase-summaries/PHASE-11-summary.md` was written.
- [x] No future-phase work was introduced: historical explorer, forecast UI panel, replay controls, spatial polish/fire overlay, and delivery hardening remain future phases.
- [x] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced: Mapbox token remains optional/public and blank by default; the UI shows empty states instead of fabricated data; modeled/replay states come only from API provenance fields.

## Problems encountered and resolutions

- `npm install` needed registry access. The sandboxed attempt did not produce a lockfile, so the install was rerun with approved network access and completed.
- `tsc` rejected `String.replaceAll` under the ES2020 target. Replaced those calls with regex-based replacements.
- ESLint rejected broad `any` map-engine types. Added local narrow interfaces for the subset of Mapbox/MapLibre APIs the dashboard uses.
- Vite reports large chunks for map libraries. This is expected for Mapbox/MapLibre; the map engine is dynamically imported so it remains separated from the main dashboard bundle.

## Deviations from the phase plan

- Used MapLibre as the no-token default in `frontend/.env.example` and Compose build args. This preserves the approved Mapbox/MapLibre adapter architecture while ensuring the dashboard can run locally without a public Mapbox token.
- Added a production frontend Dockerfile because the existing Compose service was only a placeholder Nginx image. This is within Phase 11 because the phase creates the real frontend app.
- Did not add a frontend fixture-data fallback. This avoids frontend-only fake live data; fixture compatibility should be provided by the API or a fixture server returning the same typed API contracts.

## Known issues and technical debt

- Severity: Medium. Browser-level manual verification against a running FastAPI service was not performed in this session. The frontend build and type/lint/test checks pass, but runtime API rendering should be checked after starting the API and frontend together.
- Severity: Medium. Mapbox/MapLibre bundles are large even with dynamic import. This is acceptable for Phase 11; delivery hardening can tune chunking or map-provider loading later.
- Severity: Low. The chart fetches PM2.5 history for the top five active stations. A later historical explorer phase should provide richer pollutant/time-window controls.
- Severity: Low. The map heatmap uses the API interpolation raster grid but does not add fire overlays; fire overlay polish remains a future phase.

## What the next phase needs to know

- Frontend source lives under `frontend/src/` and uses no Redux.
- Public runtime config is documented in `frontend/.env.example`; server-side secrets remain outside the frontend.
- `useLiveFeed` responds to `heartbeat` and `ping` messages with a JSON `pong` event and refreshes dashboard data after `new_readings` events.
- The map adapter falls back to MapLibre if `VITE_MAP_PROVIDER=mapbox` but `VITE_MAPBOX_TOKEN` is empty.
- Phase 12 can build historical and forecast UI on top of the existing API wrapper and design system without replacing the Phase 11 shell.

## How to resume from scratch

```bash
npm --prefix frontend install
npm --prefix frontend run build
npm --prefix frontend run lint || true
npm --prefix frontend run test -- --run
docker compose --profile core config --quiet
```

To run the dashboard locally against the API:

```bash
npm --prefix frontend run dev
```

## Next session prompt

```text
Follow AGENTS.md. Implement PHASE 12 only using docs/codex/phases/PHASE-12-historical-forecast-ui.md.
```
