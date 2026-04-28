# Data Source Validation

Phase 01 exists to prevent HimalayaAir from building against assumed Kathmandu sensor coverage. Run these checks before implementing ingestion, schema upserts, API responses, or frontend data-mode behavior.

## Scope

This workflow validates:

- OpenAQ API key access through server-side `OPENAQ_API_KEY`.
- OpenAQ Kathmandu location discovery using the approved bounding box.
- OpenAQ sensor discovery from location metadata.
- Sensor measurement freshness through `/v3/sensors/{id}/measurements`.
- Open-Meteo modeled AQ fallback availability for Kathmandu center.
- Coverage-mode recommendation using the approved source modes.

This workflow does not:

- Write to TimescaleDB.
- Require Docker, Kafka, Spark, FastAPI, Airflow, or React.
- Assume any hardcoded OpenAQ station or sensor ID is valid.
- Treat modeled AQ as observed sensor data.

## Source Contracts

OpenAQ observed data:

- Base URL: `https://api.openaq.org`
- Locations endpoint: `/v3/locations`
- Kathmandu bbox parameter: `85.2000,27.5500,85.5000,27.8000`
- Measurement endpoint: `/v3/sensors/{sensors_id}/measurements`
- Auth: `X-API-Key` header from server-side `OPENAQ_API_KEY`
- Normalized source: `openaq_live`
- Normalized observation type: `observed`

Open-Meteo modeled AQ fallback:

- Base URL: `https://air-quality-api.open-meteo.com`
- Endpoint: `/v1/air-quality`
- Kathmandu center: `27.7172,85.3240`
- Variables: `pm2_5`, `pm10`, `carbon_monoxide`, `nitrogen_dioxide`, `ozone`, `us_aqi`, `us_aqi_pm2_5`, `us_aqi_pm10`, `us_aqi_nitrogen_dioxide`, `us_aqi_ozone`, `us_aqi_carbon_monoxide`
- Normalized source: `openmeteo_cams`
- Normalized observation type: `modeled`
- Coverage mode when available: `MODELED_BASELINE`

## Commands

Run help checks first. These do not need credentials or network access.

```bash
python scripts/sync_openaq_metadata.py --help
python scripts/check_openaq_coverage.py --help
python scripts/check_openmeteo_aq.py --help
```

Run offline fixture checks next. These prove parser and report behavior without network access.

```bash
python scripts/sync_openaq_metadata.py --dry-run \
  --fixture-location fixtures/sample_openaq_location.json

python scripts/check_openaq_coverage.py \
  --fixture-location fixtures/sample_openaq_location.json \
  --fixture-measurement fixtures/sample_openaq_measurement.json

python scripts/check_openmeteo_aq.py \
  --fixture fixtures/sample_openmeteo_aq.json

pytest tests/unit -q
```

Run live Open-Meteo validation. This does not require a key.

```bash
python scripts/check_openmeteo_aq.py
```

Run live OpenAQ validation only when `OPENAQ_API_KEY` is set in the local shell or ignored `.env` workflow. Do not commit the key.

```bash
python scripts/sync_openaq_metadata.py --dry-run \
  --output tmp/openaq-metadata.json

python scripts/check_openaq_coverage.py \
  --modeled-available \
  --output tmp/openaq-coverage.json
```

Use `--metadata-only` when measurement endpoint calls need to be skipped temporarily.

```bash
python scripts/check_openaq_coverage.py \
  --metadata-only \
  --modeled-available
```

## Expected Output Fields

`sync_openaq_metadata.py` emits:

```json
{
  "dry_run": true,
  "write_target": "none_phase_01",
  "locations_found": 2,
  "sensors_found": 3,
  "pollutants": {
    "pm25": 1,
    "pm10": 1
  },
  "stations": [
    {
      "openaq_location_id": 11001
    }
  ],
  "sensors": [
    {
      "openaq_sensor_id": 21001,
      "openaq_location_id": 11001,
      "pollutant": "pm25"
    }
  ],
  "warnings": []
}
```

`check_openaq_coverage.py` emits:

```json
{
  "fresh_station_count": 1,
  "recent_station_count": 1,
  "modeled_available": false,
  "recommended_coverage_mode": "STATION_ONLY",
  "confidence": "low",
  "message": "Observed coverage is insufficient for a heatmap; show station markers only."
}
```

`check_openmeteo_aq.py` emits:

```json
{
  "result": {
    "source": "openmeteo_cams",
    "observation_type": "modeled",
    "coverage_mode": "MODELED_BASELINE",
    "modeled_available": true,
    "missing_variables": []
  }
}
```

Counts in fixture output are representative parser checks, not live measurements.

## Coverage Mode Rules

The coverage recommendation follows the approved source-mode order:

- `LIVE_OBSERVED`: at least 3 stations have readings from the last 2 hours.
- `RECENT_OBSERVED`: fewer than 3 fresh stations, but at least 3 stations have observed readings from the last 24 hours.
- `MODELED_BASELINE`: observed station coverage is sparse and Open-Meteo modeled AQ fallback has been verified.
- `STATION_ONLY`: stations exist, but coverage is insufficient for a heatmap and modeled fallback is not enabled for this report.
- `NO_DATA`: no OpenAQ stations were discovered in the configured Kathmandu bounds.

## Replay Dataset Strategy

The selected demo strategy remains pipeline replay, not frontend fake data.

Later phases should build the replay dataset from historical observed OpenAQ archive/API rows when available, preserving original timestamps and storing replayed records with:

- `source=demo_replay`
- `observation_type=replay`
- `coverage_mode=REPLAY_DEMO`

If live Kathmandu observed coverage is too sparse for a strong replay sample, a small explicitly labeled fixture dataset may be used for parser and pipeline tests. It must never be exposed as live observed data.

## Current Phase 01 Validation Notes

As of April 28, 2026:

- `OPENAQ_API_KEY` was added to local `.env`, which is ignored by Git.
- Live OpenAQ key validation passed after loading `.env`.
- Live OpenAQ metadata discovery found 52 Kathmandu-bounds locations and 256 sensors.
- Live OpenAQ coverage sampling found 1 fresh station and 4 recent stations.
- The recommended live dashboard mode is currently `RECENT_OBSERVED` with medium confidence.
- OpenAQ parser and coverage reports remain validated offline with fixtures.
- Live Open-Meteo AQ validation passed with all approved modeled fallback variables available for Kathmandu center.
- Generated live reports are kept under ignored `tmp/` paths and are not committed.
- The implementation introduced no database writes, Kafka publishing, Docker requirements, API endpoints, forecasting logic, or frontend behavior.

## Primary Documentation Checked

- OpenAQ locations API: `https://docs.openaq.org/api/operations/locations_get_v3_locations_get`
- OpenAQ sensor measurements API: `https://docs.openaq.org/api/operations/sensor_measurements_get_v3_sensors__sensors_id__measurements_get`
- Open-Meteo Air Quality API: `https://open-meteo.com/en/docs/air-quality-api`
