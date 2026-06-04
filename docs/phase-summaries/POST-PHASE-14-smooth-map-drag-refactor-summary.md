# Post-Phase-14 Summary - Smooth Map Drag Refactor

## What was built

- `frontend/src/components/LiveMap.tsx`: Replaced DOM station markers with a `himalayaair-stations` GeoJSON source, AQI circle layer, AQI label symbol layer, and selected-station highlight layer.
- `frontend/src/components/LiveMap.tsx`: Preserved station click selection and pointer cursor behavior on station circle and label layers.
- `frontend/src/components/LiveMap.tsx`: Kept the selected-station map popup as a single selected-station-only popup and left the side panel as the primary detail view.
- `frontend/src/components/LiveMap.tsx`: Lowered heatmap raster opacity, removed raster fade, and inserted the heatmap below station layers.
- `frontend/src/components/LiveMap.tsx`: Removed the fire layer entirely after the smooth-drag refactor because it is no longer needed.
- `frontend/src/hooks/useDashboardData.ts`, `frontend/src/services/api.ts`, `frontend/src/types/api.ts`, `frontend/src/components/HistoricalExplorer.tsx`, `frontend/src/components/HistoricalTimeSeries.tsx`, and `frontend/src/lib/historical.ts`: Removed frontend fire event fetches, types, annotations, and UI state.
- `frontend/src/services/mapEngine.ts`: Added local adapter support for GeoJSON `setData`, layer events, `getCanvas()`, and optional layer insertion order.
- `frontend/src/App.tsx`: Changed the default heatmap state to off.
- `frontend/src/styles/global.css`: Removed obsolete DOM marker and fire annotation styles.
- `CHANGELOG.md`: Added this post-Phase-14 maintenance entry.

## Current system state

- No backend API, schema, ingestion, forecasting, or provenance contract changes were made.
- Station points now render inside the map canvas through native MapLibre/Mapbox layers.
- The heatmap toggle still exists, but AQI heatmap rendering starts off by default.
- The frontend no longer renders fire overlays or calls `/api/events`.
- The core Docker profile was rebuilt and is running healthy in this environment.

## Commands run

```bash
npm --prefix frontend run build
# passed

npm --prefix frontend run lint
# passed

rg -n "fire|Fire|FIRES|himalayaair-fires|getEvents|EventsResponse|FireEvent|showFire|eventPromise|/api/events" frontend/src
# passed with no matches

docker compose --profile core up -d --build
# passed with elevated Docker access

docker compose ps
# passed with api, frontend, timescaledb, and worker healthy

curl -sS -o /dev/null -w '%{http_code}' http://localhost:3000
# passed with elevated local socket access, returned 200

curl -sS -o /dev/null -w '%{http_code}' http://localhost:8000/health
# passed with elevated local socket access, returned 200

./scripts/verify_env.sh --profile core
# passed with elevated Docker/local socket access
```

## Exit criteria verification

- [x] Station and AQI label rendering moved from DOM markers to native map layers.
- [x] Fire layer, fire toggle, fire frontend fetches, and fire historical annotations were removed.
- [x] Station click selection behavior is preserved through layer click handlers.
- [x] Cursor pointer behavior is preserved over station layers.
- [x] Heatmap defaults to off.
- [x] Heatmap rendering cost is reduced when enabled.
- [x] Frontend build and lint pass.
- [x] Core Docker profile rebuild and health checks pass.
- [x] `CHANGELOG.md` was updated.
- [x] No backend APIs, schemas, secrets, fake live data, or provenance behavior were changed.

## Known issues and technical debt

- Severity: Low. Browser drag smoothness and mobile touch behavior were not directly verified with Playwright or manual browser interaction in this session. The implementation path now uses canvas-native map layers, and runtime availability was verified.
- Severity: Low. The selected-station popup remains a single DOM overlay. If manual testing still shows drag jank, it can be removed without affecting the side-panel detail workflow.

## What the next session needs to know

- Post-Phase-14 maintenance is still the active project state; do not start a new phase unless the user explicitly requests one.
- The map layer IDs are `himalayaair-stations-selected`, `himalayaair-stations-circles`, and `himalayaair-stations-labels`.
- Manual browser verification should focus on dragging, station click selection, mobile label density, and heatmap toggle behavior at `http://localhost:3000`.

## How to resume from scratch

```bash
npm --prefix frontend run build
npm --prefix frontend run lint
docker compose --profile core up -d --build
./scripts/verify_env.sh --profile core
```
