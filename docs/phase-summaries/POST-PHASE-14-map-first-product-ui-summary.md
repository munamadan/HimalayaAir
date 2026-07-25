# Post-Phase-14 Summary - Map-First Product UI Redesign

## What was built

- Reworked the React dashboard into a map-first product UI: the first viewport is now a near full-screen Kathmandu Valley air-quality map.
- Removed public pipeline/provenance/method surfaces from the frontend while leaving backend provenance and pipeline endpoints unchanged.
- Added default-on map layers for AQI heatmap, wind context, and place labels, with a compact `Layers` menu to toggle them.
- Changed station map rendering from large AQI circles to cleaner place-name labels with AQI below and a small AQI color accent.
- Replaced the always-visible station panel with a compact station sheet that appears only after selecting a place.
- Replaced raw source-mode wording in visible UI with product labels such as `Live station data`, `Recent station data`, and `Estimated air quality`.
- Simplified below-map content into `Overview`, `Forecast`, and `History` product tabs.

## Current system state

- This is a frontend-only maintenance pass.
- No backend APIs, database schemas, ingestion services, Spark jobs, Airflow DAGs, or forecasting behavior changed.
- Exact API provenance values still exist in frontend types/helpers where needed, but raw technical mode labels are no longer rendered in the main product UI.
- The old public technical frontend components were removed: `CoverageRibbon`, `GreetingSummaryDialog`, `PipelineHealth`, `ProvenancePanel`, and `WindRose`.
- The Vite dev server is running at `http://localhost:3001/` for local preview in this session.

## Commands run

```bash
npm --prefix frontend run build
# passed

npm --prefix frontend run lint
# passed

npm --prefix frontend run test -- --run
# passed: 1 test file, 4 tests

npm --prefix frontend run dev -- --port 3001
# passed with elevated local socket access

curl -sS -o /dev/null -w '%{http_code}' http://localhost:3001/
# passed with elevated local socket access: 200
```

## Exit criteria verification

- [x] First screen is map-first.
- [x] Pipeline tab and pipeline health panel are removed from the public frontend.
- [x] Technical provenance panels and method copy are removed from the public frontend.
- [x] AQI heatmap, wind context, and place labels are enabled by default.
- [x] Layer controls can disable AQI heatmap, wind context, and place labels.
- [x] Station details no longer take over the map.
- [x] Main visible UI avoids raw technical source-mode labels.
- [x] Frontend build, lint, and unit tests pass.
- [x] No backend provenance, schema, API, or pipeline behavior was changed.

## Known issues and technical debt

- Severity: Medium. The wind layer uses existing aggregate wind-rose data as visual context. A true Windy-style vector particle field would require gridded wind data from the backend.
- Severity: Low. The map uses tighter practical rectangular bounds around Kathmandu/Lalitpur/Bhaktapur because trusted district boundary geometry is not loaded in the repo.
- Severity: Low. Manual browser inspection should still be performed for mobile sheet behavior and map label density.

## What the next session needs to know

- Preview the redesign at `http://localhost:3001/` while the dev server from this session is running.
- `localhost:3000` may still point to the Docker frontend build from before this source change unless the frontend container is rebuilt.
- The API and backend still expose technical provenance for system correctness and defense/debug use; the public frontend now presents product-facing labels.
