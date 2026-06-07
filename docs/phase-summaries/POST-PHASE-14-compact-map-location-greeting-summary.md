# Post-Phase-14 Summary - Compact Map and Location Greeting

## What was built

- `frontend/src/App.tsx`: Added first-open session state, browser geolocation lookup, typed health-advisory call, nearest-station selection, default-station fallback messages, and controlled forecast station state.
- `frontend/src/components/GreetingSummaryDialog.tsx`: Added a dismissible first-open dialog with greeting, current AQI summary, coverage mode, fresh/recent station counts, source/observation provenance, last update time, selected/nearest station, and a 72-hour PM2.5 forecast summary.
- `frontend/src/components/ForecastPanel.tsx`: Changed the station selector to be controlled by `App`, while keeping manual station changes available to the user.
- `frontend/src/components/LiveMap.tsx`: Added Kathmandu Valley `maxBounds` and `minZoom` values to keep the map focused on lon `85.20-85.50` and lat `27.55-27.80`.
- `frontend/src/services/mapEngine.ts`: Extended the local map abstraction with `maxBounds` and `minZoom` create options.
- `frontend/src/services/api.ts` and `frontend/src/types/api.ts`: Added typed frontend support for `GET /api/health-advisory`.
- `frontend/src/styles/global.css`: Compacted the map to about 60vh on desktop and 460px on mobile, converted the command bar to a fixed floating widget, added page offsets for responsive layouts, and styled the greeting dialog.
- `CHANGELOG.md`: Added the post-Phase-14 compact map and location greeting entry.

## Current system state

- No backend API, database schema, ingestion, Spark, Airflow, or forecasting model code was changed.
- The first screen is now a compact Kathmandu Valley map instead of a full-height hero map.
- The command bar remains visible while scrolling to trends, forecast, and pipeline sections.
- The map adapter now passes Kathmandu Valley bounds and a minimum zoom to MapLibre/Mapbox.
- On first open per browser session, the frontend requests browser geolocation. If allowed, it calls `/api/health-advisory?lat=&lon=`, selects the returned nearest station, and points the forecast panel/dialog at that station.
- If geolocation is denied, unavailable, or health-advisory lookup fails, the UI uses the default sorted Kathmandu station and surfaces the fallback in visible text.
- The forecast panel still allows manual station changes after the location/default selection.

## Commands run

```bash
npm --prefix frontend run build
# failed once on a TypeScript narrowing issue in GreetingSummaryDialog forecast loading
# passed after copying forecastStationId to a local number before the async call

npm --prefix frontend run lint
# passed

npm --prefix frontend run test -- --run
# passed: 1 test file, 3 tests

docker compose --profile core up -d --build
# failed once without Docker socket permission
# passed with elevated Docker access

./scripts/verify_env.sh --profile core
# passed with elevated Docker/local socket access

docker compose ps
# passed; api, frontend, timescaledb, and worker were healthy

curl -sS -o /dev/null -w '%{http_code}' http://localhost:3000
# passed: 200

curl -sS -o /dev/null -w '%{http_code}' http://localhost:8000/health
# passed: 200

curl -sS http://localhost:3000 | rg -n "HimalayaAir|Welcome to nginx"
# passed with HimalayaAir markers and no default Nginx page

curl -sS 'http://localhost:8000/api/health-advisory?lat=27.71&lon=85.32'
# passed and returned health-advisory JSON with coverage metadata and a nearest station
```

## Exit criteria verification

- [x] Map is compacted and remains centered on Kathmandu Valley.
- [x] MapLibre/Mapbox create options support `maxBounds` and `minZoom`.
- [x] Existing station WebGL layers and AQI heatmap toggle remain in place.
- [x] Greeting/menu command bar is fixed and available while scrolling.
- [x] First-open greeting dialog appears once per browser session until dismissed.
- [x] Dialog uses API/dashboard values or explicit unavailable/fallback text; no frontend fake data was added.
- [x] Browser geolocation selects the nearest station through the existing health-advisory API when permitted.
- [x] Location denial/unavailability/advisory failure visibly falls back to the default Kathmandu station.
- [x] Forecast station can still be changed manually.
- [x] Frontend build, lint, test, Docker core rebuild, and core environment verification pass.
- [x] `CHANGELOG.md` was updated.

## Known issues and technical debt

- Severity: Low. Manual browser interaction was not performed in this session because the repo does not include Playwright/Puppeteer browser automation. Remaining manual checks are geolocation allow/deny flows, map pan bounding behavior, fixed-widget scrolling, and mobile overlap at `http://localhost:3000`.
- Severity: Low. The dialog and forecast panel each fetch the 72-hour forecast for the selected station. This keeps the component boundary simple; shared forecast caching can be added later if needed.
- Severity: Low. Vite still reports large map/chart chunks during production builds. This was already present before this maintenance change.

## What the next session needs to know

- Post-Phase-14 maintenance remains the current project state.
- The greeting dialog session keys are `himalayaair.greeting.dismissed.v1` and `himalayaair.locationForecast.v1`.
- To retest first-open behavior in the browser, clear those two session storage keys for `localhost:3000`.
- Manual browser verification should cover geolocation allowed, geolocation denied, mobile fixed-commandbar scrolling, and map panning at the Kathmandu Valley bounds.
