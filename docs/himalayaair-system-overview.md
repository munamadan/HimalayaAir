# HimalayaAir - Fixed System Overview Prompt v2.0

> Copy-ready master prompt/specification for building the Kathmandu Valley Air Quality Intelligence Platform.
>
> Document status: corrected, provenance-aware, fallback-capable, and ready for implementation planning.
>
> Updated: April 27, 2026.
>
> Supersedes the previous HimalayaAir master specification by preserving the original vision while fixing the implementation blockers around OpenAQ, sparse live coverage, forecasting, Airflow metadata, TimescaleDB uniqueness, demo reliability, and laptop resource limits.

---

## 0. How to use this prompt

Paste this entire Markdown document into Claude Code, Cursor, or another AI coding session before asking it to generate code or implementation phases.

The AI assistant must treat this document as authoritative. If there is conflict between this document and an earlier HimalayaAir document, this v2.0 document wins.

The central principle is:

```text
Do not reduce the ambition of HimalayaAir.
Instead, make the system honest, source-aware, and resilient when real public data is sparse or delayed.
```

The project must still deliver:

- Real-time or near-real-time air quality ingestion.
- Kafka and Spark streaming.
- TimescaleDB and PostGIS storage.
- Airflow orchestration.
- Historical backfill.
- Kathmandu Valley map visualization.
- IDW heatmap.
- Forecasting.
- Health advisories.
- Fire/festival/seasonal context.
- Demo mode.
- Pipeline health observability.
- A visually impressive frontend suitable for final-year defense and recruiter demonstration.

But it must no longer depend on a fragile assumption that OpenAQ live Kathmandu station data will always be fresh, dense, and perfectly available.

---

## 1. Project vision

HimalayaAir is a full-stack real-time data engineering platform for Kathmandu Valley air quality intelligence. It ingests observed, archived, modeled, and replayed air-quality data; normalizes it into a shared pipeline; stores it in a time-series/geospatial database; and visualizes pollution patterns, spatial heatmaps, health advisories, seasonal/festival correlations, fire context, and 72-hour forecasts.

### Core tagline

```text
A provenance-aware Kathmandu Valley air-quality intelligence platform with live ingestion, spatial visualization, historical analysis, pipeline observability, and 72-hour pollution forecasting.
```

### Thesis framing

Use this framing in reports and viva:

```text
Public air-quality networks in Kathmandu have irregular sensor coverage, delayed publication, and changing API structures. HimalayaAir addresses this through a provenance-aware data fusion architecture. The platform prioritizes observed measurements, falls back to recent observations or modeled atmospheric data when live coverage is insufficient, and provides a replay mode for reproducible demonstrations. Every output exposes its data mode, source, freshness, and confidence level.
```

This is not a compromise. It is the engineering contribution.

---

## 2. Hard constraints

| Constraint | Requirement |
|---|---|
| Developer | One final-year CS student in Kathmandu, Nepal |
| Coding method | AI-assisted using Claude Code / Cursor |
| Hardware | Personal laptop, 8-16 GB RAM |
| Budget | Prefer USD 0; absolute max USD 20 |
| Timeline | 10-12 weeks |
| Academic requirement | Must demonstrate all 5 data engineering curriculum topics |
| Demo requirement | Must impress both non-technical supervisor and technical recruiters |

---

## 3. Academic data engineering coverage

| Topic | HimalayaAir implementation |
|---|---|
| Data modeling and database systems | TimescaleDB hypertables, continuous aggregates, PostGIS spatial tables, normalized station/sensor schema, provenance-aware readings |
| Distributed systems and big data processing | Kafka message bus, Spark Structured Streaming, replayable event pipeline |
| Pipeline and orchestration | Airflow DAGs, idempotent backfill, data quality checks, forecast recomputation, FIRMS ingestion |
| Cloud and infrastructure | Docker Compose profiles, healthchecks, optional Cloud Run deployment |
| Programming and data structures | Python adapters, AQI algorithms, IDW interpolation, forecast model arbitration, React state and map rendering |

---

## 4. Non-negotiable design principles

### 4.1 Observed data first, fallback second

The source priority order is:

```text
1. LIVE_OBSERVED
   Fresh measured OpenAQ sensor data, normally less than 2 hours old.

2. RECENT_OBSERVED
   Real observed OpenAQ data, but stale/recent, normally 2-24 hours old.

3. MODELED_BASELINE
   Open-Meteo/CAMS modeled air-quality data, clearly labeled as modeled.

4. REPLAY_DEMO
   Historical observed or modeled data replayed through Kafka/Spark for reproducible demos.

5. STATION_ONLY
   Not enough stations for heatmap; show station markers only.

6. NO_DATA
   No safe current estimate available.
```

The frontend must display the current mode clearly. Never pretend modeled or replay data is live sensor truth.

### 4.2 The dashboard must degrade, not break

If fewer than 3 fresh stations are available, the system must not fail. It must degrade:

```text
fresh stations >= 3      -> live observed IDW
recent stations >= 3     -> recent observed IDW with stale-data warning
modeled AQ available     -> modeled baseline heatmap
replay active            -> replay heatmap
otherwise                -> station markers only
```

### 4.3 Demo mode must exercise the real pipeline

Demo mode must not be a frontend-only animation. It must replay historical records through:

```text
replay-publisher -> Kafka -> Spark -> TimescaleDB -> FastAPI -> WebSocket -> React
```

This proves the actual architecture during defense even when live data is quiet.

### 4.4 All data must carry provenance

Every AQ value exposed to the user must be traceable by:

```text
source: openaq_live | openaq_archive | openmeteo_cams | demo_replay | manual_seed
observation_type: observed | modeled | replay | synthetic
coverage_mode: LIVE_OBSERVED | RECENT_OBSERVED | MODELED_BASELINE | REPLAY_DEMO | STATION_ONLY | NO_DATA
confidence: high | medium | low | demo
freshness_minutes: integer or null
```

---

## 5. Kathmandu Valley parameters

```text
Bounding box:  lat 27.55 to 27.80 | lon 85.20 to 85.50
Center:        lat 27.7172        | lon 85.3240
Default zoom:  11
SRID:          4326 WGS84 for stored geometries
Distance math: use geography or projected coordinates, not raw degree distance
IDW projection: use local meter offsets or EPSG:32645 for distance weighting
```

---

## 6. Corrected technology stack

### 6.1 Infrastructure

| Layer | Technology | Version / rule | Reason |
|---|---|---|---|
| Container orchestration | Docker Compose | Compose profiles required | Keeps full vision while allowing 8 GB development |
| Time-series DB | TimescaleDB/PostgreSQL | pg16 image | Hypertables, continuous aggregates, SQL analytics |
| Geospatial | PostGIS | bundled with DB | District assignment, nearest station, spatial overlays |
| Message bus | Apache Kafka | Confluent CP 7.6.x or pinned equivalent | Academic DE requirement and replayable pipeline |
| Stream processor | Apache Spark | 3.5.x local mode | Academic DE requirement, structured streaming |
| Orchestrator | Apache Airflow | 2.9.x or pinned equivalent | Backfill, forecasts, data quality, reports |
| Airflow metadata DB | PostgreSQL | separate airflow-postgres service | Do not use SQLite with LocalExecutor |
| Schema migrations | Alembic | latest stable | Required for all schema changes |
| Cache | In-process TTL cache | no Redis | Redis is unnecessary for <=20 demo users |

### 6.2 Backend

| Component | Technology | Rule |
|---|---|---|
| API framework | FastAPI | async endpoints, Pydantic response schemas |
| DB access for API | SQLAlchemy 2.x + asyncpg | async SQL, raw SQL allowed for PostGIS/Timescale queries |
| DB access for Spark | psycopg2 or JDBC | batch inserts with ON CONFLICT handling |
| HTTP client | httpx | timeouts, retries, structured error handling |
| Kafka producer | confluent-kafka | used by pollers and replay-publisher |
| Kafka consumer | aiokafka | used by FastAPI WebSocket broadcaster |
| Forecasting | statsmodels SARIMAX plus persistence baseline | SARIMAX only when data coverage is sufficient |
| Logging | structlog | mandatory in every Python service |

### 6.3 Frontend

| Component | Technology | Rule |
|---|---|---|
| Build tool | Vite | React 18 project |
| UI framework | React | no Redux unless proven necessary |
| Map | Mapbox GL JS with MapLibre fallback | keep Mapbox visual polish, but avoid token lock-in |
| Charts | Recharts + limited D3 | Recharts for standard charts, D3 only where needed |
| WebSocket | native WebSocket | reconnect with exponential backoff |
| HTTP | native fetch wrapper | no Axios required |
| Styling | CSS variables, dark mode first | mobile responsive |

---

## 7. Docker Compose profiles

Do not require all services to run at once. Define Compose profiles.

```text
core profile:
  timescaledb
  kafka
  api
  frontend

stream profile:
  spark-stream

weather profile:
  weather-poller
  openmeteo-aq-poller

batch profile:
  airflow-postgres
  airflow-webserver
  airflow-scheduler

observed profile:
  openaq-poller

demo profile:
  replay-publisher

full profile:
  everything
```

Common commands:

```bash
docker compose --profile core up -d
docker compose --profile core --profile observed --profile stream up -d
docker compose --profile weather up -d
docker compose --profile batch up -d
docker compose --profile demo up replay-publisher
docker compose --profile full up -d
```

Memory guidance:

```text
8 GB laptop:
  use core + one profile at a time

16 GB laptop:
  full profile is acceptable if memory limits are set
```

---

## 8. Environment variables

Create `.env.example` with blanks only. Never commit real secrets.

```bash
# Database
POSTGRES_USER=himalayaair
POSTGRES_PASSWORD=himalayaair
POSTGRES_DB=himalayaair
DATABASE_URL=postgresql+asyncpg://himalayaair:himalayaair@timescaledb:5432/himalayaair
SYNC_DATABASE_URL=postgresql://himalayaair:himalayaair@timescaledb:5432/himalayaair

# Airflow metadata DB
AIRFLOW_POSTGRES_USER=airflow
AIRFLOW_POSTGRES_PASSWORD=airflow
AIRFLOW_POSTGRES_DB=airflow
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@airflow-postgres:5432/airflow

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# External APIs
OPENAQ_API_KEY=
FIRMS_MAP_KEY=

# Frontend
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/live-feed
VITE_MAP_PROVIDER=mapbox
VITE_MAPBOX_TOKEN=
VITE_MAP_STYLE_URL=mapbox://styles/mapbox/dark-v11

# Runtime
LOG_FORMAT=json
ALLOWED_ORIGINS=http://localhost:3000
DEMO_MODE_ALLOWED=true
```

Rules:

- `OPENAQ_API_KEY` is server-side only.
- `FIRMS_MAP_KEY` is server-side only.
- `VITE_MAPBOX_TOKEN` is public but should be domain-restricted if deployed.
- `.env` must be in `.gitignore`.

---

## 9. External data sources

### 9.1 OpenAQ API v3 - observed live data

OpenAQ is the primary source for observed air-quality data.

Correct assumptions:

```text
Auth: server-side API key using X-API-Key header
Metadata discovery: /v3/locations with Kathmandu bounding box
Measurement polling: /v3/sensors/{sensors_id}/measurements
Time params: datetime_from and datetime_to
Primary identity: sensor_id, not location_id
```

The system must model OpenAQ locations and sensors separately:

```text
OpenAQ location -> logical monitoring station
OpenAQ sensor   -> one pollutant stream at that station
```

### 9.2 OpenAQ AWS archive - historical observed backfill

Historical OpenAQ backfill should prefer the OpenAQ S3 archive before using the API.

Backfill order:

```text
1. Try OpenAQ AWS archive by locationid/year/month/day.
2. If available, ingest CSV.gz records.
3. If missing, fall back to OpenAQ sensor measurement API.
4. Record result in backfill_manifest.
```

### 9.3 Open-Meteo weather - weather enrichment

Use Open-Meteo weather forecast and historical APIs for:

```text
temperature_2m
relative_humidity_2m
wind_speed_10m
wind_direction_10m
precipitation
```

Live weather is used for dashboard context. Historical and future weather are used for forecasting covariates.

### 9.4 Open-Meteo Air Quality / CAMS - modeled AQ fallback

Use Open-Meteo Air Quality API as a modeled fallback, not as observed truth.

Variables:

```text
pm2_5
pm10
carbon_monoxide
nitrogen_dioxide
ozone
us_aqi
us_aqi_pm2_5
us_aqi_pm10
us_aqi_nitrogen_dioxide
us_aqi_ozone
us_aqi_carbon_monoxide
```

Store this in `modeled_aq_readings`, not as normal observed sensor readings.

Use for:

```text
MODELED_BASELINE heatmap
forecast fallback
bias-adjusted forecast model
```

### 9.5 NASA FIRMS - fire events

Use NASA FIRMS Area API for VIIRS active fire detections.

Store all important fields:

```text
lat, lon, acq_date, acq_time, satellite, instrument, confidence, frp, brightness, source, event_hash
```

Do not deduplicate only by location and date. Use a stable hash.

---

## 10. Corrected system architecture

```text
                                  +-------------------------+
                                  | Phase -1 Data Validation|
                                  | sync_openaq_metadata.py |
                                  | check_coverage.py       |
                                  +------------+------------+
                                               |
                                               v
+-------------------+      +-------------------------+      +-------------------+
| OpenAQ API v3     | ---> | openaq-poller           | ---> | Kafka             |
| locations/sensors |      | sensor-based polling    |      | raw-aq-readings   |
+-------------------+      +-------------------------+      +---------+---------+
                                                                        |
+-------------------+      +-------------------------+                  |
| Replay dataset    | ---> | replay-publisher        | -----------------+
| historical rows   |      | demo through pipeline   |
+-------------------+      +-------------------------+
                                                                        v
                                                              +-------------------+
                                                              | Spark Structured  |
                                                              | Streaming         |
                                                              | AQI, district,    |
                                                              | anomaly, upsert   |
                                                              +---------+---------+
                                                                        |
                                                                        v
+-------------------+      +-------------------------+      +-------------------+
| Open-Meteo Weather| ---> | weather-poller          | ---> | TimescaleDB       |
| live + historical |      | direct DB write         |      | + PostGIS         |
+-------------------+      +-------------------------+      | aq_readings       |
                                                             | modeled_aq        |
+-------------------+      +-------------------------+      | weather_readings  |
| Open-Meteo AQ     | ---> | openmeteo-aq-poller     | ---> | forecasts         |
| CAMS model        |      | modeled fallback        |      | pipeline_runs     |
+-------------------+      +-------------------------+      +---------+---------+
                                                                        |
+-------------------+      +-------------------------+                  |
| NASA FIRMS        | ---> | Airflow firms_daily     | -----------------+
+-------------------+      +-------------------------+                  |
                                                                        v
                                                              +-------------------+
                                                              | FastAPI           |
                                                              | REST + WebSocket  |
                                                              | coverage modes    |
                                                              | IDW + health      |
                                                              +---------+---------+
                                                                        |
                                                                        v
                                                              +-------------------+
                                                              | React Dashboard   |
                                                              | Map, charts,      |
                                                              | heatmap, forecast,|
                                                              | provenance labels |
                                                              +-------------------+
```

---

## 11. Database schema

All schema changes must be applied through Alembic migrations. No direct schema edits after Phase 0.

### 11.1 Migration 001 - Extensions and spatial core

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE stations (
    id                    SERIAL PRIMARY KEY,
    name                  VARCHAR(200) NOT NULL,
    source                VARCHAR(50) NOT NULL DEFAULT 'openaq',
    source_location_id    VARCHAR(100),
    location              GEOMETRY(POINT, 4326) NOT NULL,
    elevation             INTEGER,
    active                BOOLEAN DEFAULT TRUE,
    status                VARCHAR(30) DEFAULT 'active',
    last_seen             TIMESTAMPTZ,
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source, source_location_id)
);
CREATE INDEX idx_stations_location_gist ON stations USING GIST(location);
CREATE INDEX idx_stations_active_last_seen ON stations(active, last_seen DESC);

CREATE TABLE station_sensors (
    id                    SERIAL PRIMARY KEY,
    station_id             INTEGER NOT NULL REFERENCES stations(id),
    source                 VARCHAR(30) NOT NULL DEFAULT 'openaq',
    external_sensor_id     VARCHAR(100) NOT NULL,
    external_location_id   VARCHAR(100),
    pollutant              VARCHAR(20) NOT NULL,
    unit                   VARCHAR(30),
    datetime_first         TIMESTAMPTZ,
    datetime_last          TIMESTAMPTZ,
    active                 BOOLEAN DEFAULT TRUE,
    priority               INTEGER DEFAULT 0,
    created_at             TIMESTAMPTZ DEFAULT NOW(),
    updated_at             TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source, external_sensor_id)
);
CREATE INDEX idx_station_sensors_station ON station_sensors(station_id);
CREATE INDEX idx_station_sensors_active_pollutant ON station_sensors(active, pollutant);

CREATE TABLE districts (
    id                    SERIAL PRIMARY KEY,
    name                  VARCHAR(100) NOT NULL,
    boundary              GEOMETRY(MULTIPOLYGON, 4326) NOT NULL,
    population            INTEGER,
    district_code         VARCHAR(20) UNIQUE
);
CREATE INDEX idx_districts_boundary_gist ON districts USING GIST(boundary);

CREATE TABLE weather_locations (
    id                    SERIAL PRIMARY KEY,
    name                  VARCHAR(100) NOT NULL,
    location              GEOMETRY(POINT, 4326) NOT NULL,
    elevation             INTEGER,
    active                BOOLEAN DEFAULT TRUE
);
CREATE INDEX idx_weather_locations_location_gist ON weather_locations USING GIST(location);
```

### 11.2 Migration 002 - Time-series readings

Important TimescaleDB rule:

```text
Any primary key or unique index on a hypertable must include the time partition column.
```

Therefore time-series tables use composite primary keys or unique constraints that include `timestamp`.

```sql
CREATE TABLE aq_readings (
    sensor_id             INTEGER NOT NULL REFERENCES station_sensors(id),
    station_id            INTEGER NOT NULL REFERENCES stations(id),
    pollutant             VARCHAR(20) NOT NULL,
    value                 NUMERIC(8, 2) NOT NULL,
    unit                  VARCHAR(30) NOT NULL,
    aqi                   INTEGER,
    timestamp             TIMESTAMPTZ NOT NULL,
    district_id           INTEGER REFERENCES districts(id),
    is_anomaly            BOOLEAN DEFAULT FALSE,
    anomaly_reason        VARCHAR(80),
    quality_flag          VARCHAR(50) DEFAULT 'raw',
    observation_type      VARCHAR(30) DEFAULT 'observed',
    source                VARCHAR(50) DEFAULT 'openaq_live',
    original_timestamp    TIMESTAMPTZ,
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (sensor_id, timestamp)
);

SELECT create_hypertable('aq_readings', 'timestamp', chunk_time_interval => INTERVAL '7 days');

CREATE INDEX idx_aq_station_time ON aq_readings(station_id, timestamp DESC);
CREATE INDEX idx_aq_station_pollutant_time ON aq_readings(station_id, pollutant, timestamp DESC);
CREATE INDEX idx_aq_district_time ON aq_readings(district_id, timestamp DESC);
CREATE INDEX idx_aq_source_type_time ON aq_readings(source, observation_type, timestamp DESC);

CREATE TABLE weather_readings (
    location_id           INTEGER NOT NULL REFERENCES weather_locations(id),
    temp                  NUMERIC(5, 2),
    humidity              NUMERIC(5, 2),
    wind_speed            NUMERIC(6, 2),
    wind_dir              NUMERIC(5, 1),
    precipitation         NUMERIC(6, 2),
    timestamp             TIMESTAMPTZ NOT NULL,
    source                VARCHAR(50) DEFAULT 'openmeteo_weather',
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (location_id, timestamp)
);

SELECT create_hypertable('weather_readings', 'timestamp', chunk_time_interval => INTERVAL '7 days');
CREATE INDEX idx_weather_location_time ON weather_readings(location_id, timestamp DESC);

CREATE TABLE modeled_aq_readings (
    model_location_id     INTEGER NOT NULL REFERENCES weather_locations(id),
    source                VARCHAR(50) NOT NULL DEFAULT 'openmeteo_cams',
    pollutant             VARCHAR(20) NOT NULL,
    value                 NUMERIC(8, 2),
    unit                  VARCHAR(30),
    us_aqi                INTEGER,
    timestamp             TIMESTAMPTZ NOT NULL,
    model_run_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (model_location_id, pollutant, timestamp, model_run_at)
);

SELECT create_hypertable('modeled_aq_readings', 'timestamp', chunk_time_interval => INTERVAL '7 days');
CREATE INDEX idx_modeled_location_time ON modeled_aq_readings(model_location_id, timestamp DESC);
CREATE INDEX idx_modeled_pollutant_time ON modeled_aq_readings(pollutant, timestamp DESC);
```

### 11.3 Migration 003 - Forecasting and operations

```sql
CREATE TABLE forecast_runs (
    id                    BIGSERIAL PRIMARY KEY,
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    model_name            VARCHAR(80) NOT NULL,
    status                VARCHAR(30) NOT NULL,
    stations_attempted    INTEGER DEFAULT 0,
    stations_succeeded    INTEGER DEFAULT 0,
    fallback_reason       TEXT,
    error_message         TEXT,
    duration_seconds      NUMERIC(8, 2)
);

CREATE TABLE forecasts (
    forecast_run_id       BIGINT NOT NULL REFERENCES forecast_runs(id) ON DELETE CASCADE,
    station_id            INTEGER NOT NULL REFERENCES stations(id),
    pollutant             VARCHAR(20) NOT NULL,
    predicted_aqi         INTEGER NOT NULL,
    lower_bound           NUMERIC(6, 2),
    upper_bound           NUMERIC(6, 2),
    target_timestamp      TIMESTAMPTZ NOT NULL,
    model_name            VARCHAR(80) NOT NULL,
    model_source          VARCHAR(80) NOT NULL,
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (forecast_run_id, station_id, pollutant, target_timestamp)
);
CREATE INDEX idx_forecasts_latest ON forecasts(station_id, pollutant, target_timestamp DESC);
CREATE INDEX idx_forecasts_created ON forecasts(created_at DESC);

CREATE TABLE forecast_accuracy (
    id                    SERIAL PRIMARY KEY,
    station_id             INTEGER NOT NULL REFERENCES stations(id),
    pollutant              VARCHAR(20) NOT NULL,
    forecast_created_at    TIMESTAMPTZ NOT NULL,
    horizon_hours          INTEGER NOT NULL,
    mae                   NUMERIC(6, 2),
    rmse                  NUMERIC(6, 2),
    computed_at            TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (station_id, pollutant, forecast_created_at, horizon_hours)
);

CREATE TABLE pipeline_runs (
    id                    BIGSERIAL PRIMARY KEY,
    component             VARCHAR(80) NOT NULL,
    run_at                TIMESTAMPTZ DEFAULT NOW(),
    status                VARCHAR(30) NOT NULL,
    records_processed     INTEGER,
    error_message         TEXT,
    duration_seconds      NUMERIC(8, 2),
    metadata              JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX idx_pipeline_component_run ON pipeline_runs(component, run_at DESC);

CREATE TABLE coverage_snapshots (
    id                    BIGSERIAL PRIMARY KEY,
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    coverage_mode         VARCHAR(40) NOT NULL,
    confidence            VARCHAR(20) NOT NULL,
    fresh_station_count   INTEGER DEFAULT 0,
    recent_station_count  INTEGER DEFAULT 0,
    modeled_available     BOOLEAN DEFAULT FALSE,
    replay_active         BOOLEAN DEFAULT FALSE,
    message               TEXT
);
CREATE INDEX idx_coverage_created ON coverage_snapshots(created_at DESC);

CREATE TABLE monthly_reports (
    id                    SERIAL PRIMARY KEY,
    year                  INTEGER NOT NULL,
    month                 INTEGER NOT NULL,
    avg_aqi               NUMERIC(6, 2),
    max_aqi               INTEGER,
    worst_day             DATE,
    dominant_pollutant    VARCHAR(20),
    station_count         INTEGER,
    generated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (year, month)
);
```

### 11.4 Migration 004 - Backfill and fire events

```sql
CREATE TABLE backfill_manifest (
    id                    BIGSERIAL PRIMARY KEY,
    source                VARCHAR(50) NOT NULL,
    external_location_id  VARCHAR(100),
    external_sensor_id    VARCHAR(100),
    date                  DATE NOT NULL,
    status                VARCHAR(30) NOT NULL,
    rows_fetched          INTEGER DEFAULT 0,
    rows_written          INTEGER DEFAULT 0,
    error_message         TEXT,
    started_at            TIMESTAMPTZ DEFAULT NOW(),
    finished_at           TIMESTAMPTZ,
    UNIQUE (source, external_location_id, external_sensor_id, date)
);

CREATE TABLE fire_events (
    id                    BIGSERIAL PRIMARY KEY,
    location              GEOMETRY(POINT, 4326) NOT NULL,
    latitude              NUMERIC(9, 6) NOT NULL,
    longitude             NUMERIC(9, 6) NOT NULL,
    acq_date              DATE NOT NULL,
    acq_time              INTEGER,
    satellite             VARCHAR(20),
    instrument            VARCHAR(20),
    confidence            VARCHAR(30),
    frp                   NUMERIC(8, 2),
    brightness            NUMERIC(8, 2),
    source                VARCHAR(50) DEFAULT 'VIIRS_SNPP_NRT',
    event_hash            TEXT NOT NULL UNIQUE,
    created_at            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_fire_location_gist ON fire_events USING GIST(location);
CREATE INDEX idx_fire_date ON fire_events(acq_date DESC);
```

### 11.5 Migration 005 - Continuous aggregates

```sql
CREATE MATERIALIZED VIEW aq_hourly
WITH (timescaledb.continuous) AS
SELECT
    station_id,
    pollutant,
    time_bucket('1 hour', timestamp) AS hour_bucket,
    AVG(value) AS avg_value,
    AVG(aqi) AS avg_aqi,
    MAX(aqi) AS max_aqi,
    COUNT(*) AS reading_count
FROM aq_readings
WHERE NOT is_anomaly
GROUP BY station_id, pollutant, hour_bucket;

CREATE MATERIALIZED VIEW aq_daily
WITH (timescaledb.continuous) AS
SELECT
    station_id,
    pollutant,
    time_bucket('1 day', timestamp) AS day_bucket,
    AVG(value) AS avg_value,
    AVG(aqi) AS avg_aqi,
    MAX(aqi) AS max_aqi,
    COUNT(*) AS reading_count
FROM aq_readings
WHERE NOT is_anomaly
GROUP BY station_id, pollutant, day_bucket;

CREATE MATERIALIZED VIEW valley_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS day_bucket,
    AVG(aqi) AS avg_aqi,
    MAX(aqi) AS max_aqi,
    COUNT(DISTINCT station_id) AS station_count
FROM aq_readings
WHERE NOT is_anomaly
GROUP BY day_bucket;

SELECT add_continuous_aggregate_policy('aq_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

SELECT add_continuous_aggregate_policy('aq_daily',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '6 hours');

SELECT add_continuous_aggregate_policy('valley_daily',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '6 hours');
```

API endpoints that need the current hour must combine continuous aggregate output with raw recent rows, because continuous aggregates may intentionally lag.

---

## 12. Seed data and validation

### 12.1 Required weather locations

```text
1. Kathmandu Center:       lat 27.7172, lon 85.3240
2. Lalitpur:               lat 27.6644, lon 85.3238
3. Bhaktapur:              lat 27.6710, lon 85.4298
4. Kirtipur:               lat 27.6780, lon 85.2768
5. Budhanilkantha:         lat 27.7811, lon 85.3639
```

### 12.2 District geometry

Load Kathmandu, Lalitpur, and Bhaktapur district boundaries as `MULTIPOLYGON` with SRID 4326.

During load:

```sql
ST_Multi(ST_SetSRID(geom, 4326))
```

For assigning stations/readings to districts, use `ST_Covers`, not `ST_Contains`, so boundary points do not get missed.

---

## 13. Phase -1: Data reality check

This phase is mandatory before Phase 0.

### Files

```text
scripts/sync_openaq_metadata.py
scripts/check_coverage.py
docs/data-source-validation.md
```

### sync_openaq_metadata.py

Responsibilities:

```text
1. Read OPENAQ_API_KEY.
2. Query OpenAQ locations in the Kathmandu bbox.
3. Extract location id, name, coordinates, provider, datetimeFirst, datetimeLast.
4. Insert/update stations.
5. Extract nested sensors or fetch sensors per location.
6. Insert/update station_sensors.
7. Write a human-readable report.
```

### check_coverage.py

Responsibilities:

```text
1. Count stations found.
2. Count sensors found by pollutant.
3. Check freshness in last 2 hours.
4. Check recent availability in last 24 hours.
5. Check 30-day observed coverage.
6. Check whether >=3 fresh or recent stations exist for IDW.
7. Check Open-Meteo modeled AQ availability.
8. Recommend operating mode.
```

Example output:

```text
Kathmandu OpenAQ discovery report
---------------------------------
Locations found: 5
Sensors found: 8
PM2.5 sensors: 4
Fresh in last 2h: 2
Recent in last 24h: 4
IDW live mode: unavailable
IDW recent mode: available
Modeled fallback: available
Recommended dashboard mode: RECENT_OBSERVED + MODELED_BASELINE
```

Exit criteria:

```bash
python scripts/sync_openaq_metadata.py
python scripts/check_coverage.py --days 30
```

Expected:

```text
PASS: OpenAQ API key works
PASS: metadata tables populated
WARN or PASS: observed coverage reported honestly
PASS: modeled fallback available
PASS: demo dataset can be generated
```

---

## 14. Kafka topic design

| Topic | Partitions | Retention | Key | Producer | Consumer |
|---|---:|---|---|---|---|
| raw-aq-readings | 3 | 24 hours | sensor_id | openaq-poller, replay-publisher | Spark stream |
| processed-aq-readings | 1 | 1 hour | batch_id | Spark stream | FastAPI WebSocket task |
| raw-aq-readings-dlq | 1 | 7 days | sensor_id | Spark stream or validation layer | manual/replay tool |
| weather-data | 1 | 24 hours | location_id | weather-poller | optional diagnostics only |
| pipeline-events | 1 | 24 hours | component | all services | optional diagnostics only |

Important rule:

```text
API poll failures are not DLQ messages because no raw message exists yet.
API poll failures go to pipeline_runs and service health.
Malformed or unprocessable existing Kafka messages go to raw-aq-readings-dlq.
```

### raw-aq-readings schema v1.1

```json
{
  "schema_version": "1.1",
  "source": "openaq_live",
  "observation_type": "observed",
  "station_id": 1,
  "sensor_id": 7,
  "external_sensor_id": "23534",
  "external_location_id": "8118",
  "station_name": "Kathmandu Station",
  "lat": 27.7172,
  "lon": 85.3240,
  "pollutant": "pm25",
  "value": 47.3,
  "unit": "ug/m3",
  "measurement_timestamp": "2026-04-27T06:00:00Z",
  "original_timestamp": null,
  "ingested_at": "2026-04-27T06:02:14Z"
}
```

### processed-aq-readings schema v1.1

```json
{
  "batch_id": 42,
  "processed_at": "2026-04-27T06:05:00Z",
  "records_written": 23,
  "records_skipped_duplicate": 7,
  "anomaly_count": 1,
  "coverage_mode": "LIVE_OBSERVED",
  "confidence": "high",
  "stations": [
    {
      "station_id": 1,
      "station_name": "Kathmandu Station",
      "aqi": 87,
      "dominant_pollutant": "pm25",
      "district": "Kathmandu",
      "is_anomaly": false,
      "source": "openaq_live",
      "observation_type": "observed",
      "lat": 27.7172,
      "lon": 85.3240
    }
  ]
}
```

`processed-aq-readings` is a best-effort notification channel. The database remains the source of truth.

---

## 15. OpenAQ live ingestion service

Service:

```text
services/openaq-poller/
```

Behavior:

```text
Port: 9090 /health
Poll interval: 5 minutes
Startup: poll once immediately
Auth: X-API-Key from OPENAQ_API_KEY
Polling target: active rows in station_sensors where source='openaq'
Endpoint: /v3/sensors/{external_sensor_id}/measurements
Window: last_success - 15 minutes overlap to now
Pagination: use limit/page or documented API pagination
Rate limit: respect 429 and x-ratelimit headers where available
Output: raw-aq-readings Kafka topic
DB updates: station_sensors.datetime_last, stations.last_seen
Failures: pipeline_runs + health endpoint, not raw DLQ unless a message exists
```

Pseudocode:

```python
def poll_once():
    sensors = load_active_station_sensors(source="openaq")
    for sensor in sensors:
        start = get_last_success(sensor) - timedelta(minutes=15)
        end = utcnow()
        for page in pages:
            response = client.get(
                f"/v3/sensors/{sensor.external_sensor_id}/measurements",
                params={"datetime_from": start, "datetime_to": end, "limit": 100},
                headers={"X-API-Key": OPENAQ_API_KEY},
                timeout=30,
            )
            handle_rate_limit_headers(response.headers)
            records = parse_response(response)
            for record in records:
                producer.produce("raw-aq-readings", key=sensor.id, value=normalize(record))
```

---

## 16. Open-Meteo weather and modeled AQ services

### 16.1 weather-poller

Service:

```text
services/weather-poller/
```

Behavior:

```text
Port: 9091 /health
Poll interval: 15 minutes
Input: weather_locations table
API: Open-Meteo forecast API
Write: direct insert into weather_readings ON CONFLICT DO NOTHING
Optional publish: weather-data topic for diagnostics
```

Do not consume its own Kafka topic for DB writes. That is unnecessary and fragile for low-volume data.

### 16.2 openmeteo-aq-poller

Service:

```text
services/openmeteo-aq-poller/
```

Behavior:

```text
Port: 9092 /health if exposed; otherwise internal only
Poll interval: 30 minutes or hourly
Input: weather_locations table
API: Open-Meteo Air Quality API
Write: modeled_aq_readings ON CONFLICT DO NOTHING
Use: MODELED_BASELINE heatmap and forecast fallback
```

Never mix modeled rows into `aq_readings` unless explicitly marked as `observation_type='modeled'`. Preferred design is to keep modeled AQ in `modeled_aq_readings`.

---

## 17. Replay publisher service

Service:

```text
services/replay-publisher/
```

Purpose:

```text
Replays historical rows through the same live pipeline for controlled demos.
```

Config:

```bash
REPLAY_START=2025-01-14T00:00:00Z
REPLAY_END=2025-01-15T00:00:00Z
REPLAY_SPEED=10
REPLAY_LOOP=true
REPLAY_SOURCE=aq_readings
```

Behavior:

```text
1. Read historical rows from aq_readings or fixture CSV.
2. Shift timestamps to current time window.
3. Publish to raw-aq-readings with source='demo_replay' and observation_type='replay'.
4. Store original_timestamp separately.
5. Stop or loop based on config.
```

Replay message example:

```json
{
  "schema_version": "1.1",
  "source": "demo_replay",
  "observation_type": "replay",
  "station_id": 1,
  "sensor_id": 7,
  "pollutant": "pm25",
  "value": 83.2,
  "unit": "ug/m3",
  "measurement_timestamp": "2026-04-27T10:15:00Z",
  "original_timestamp": "2025-01-14T08:00:00Z",
  "ingested_at": "2026-04-27T10:15:03Z"
}
```

Frontend banner:

```text
DEMO MODE - replaying historical data through the live Kafka/Spark pipeline
```

---

## 18. Spark Structured Streaming

Service:

```text
services/spark/jobs/aq_stream_processor.py
```

Run as a real `spark-stream` service using `spark-submit`, not just a passive Spark container.

Required packages:

```text
spark-sql-kafka connector
PostgreSQL JDBC or psycopg2 path
checkpoint volume mounted at /tmp/spark-checkpoints/aq-stream
```

Per-batch logic:

```text
1. Parse Kafka JSON.
2. Validate schema_version, station_id, sensor_id, pollutant, value, unit, timestamp.
3. Normalize units where supported.
4. Calculate AQI.
   - PM2.5 authoritative first.
   - Other pollutants can be raw until tested.
5. Assign district using ST_Covers.
6. Detect anomalies safely.
7. Write aq_readings with ON CONFLICT DO NOTHING.
8. Update station_sensors.datetime_last and stations.last_seen.
9. Insert pipeline_runs row.
10. Publish processed-aq-readings summary.
11. Route malformed messages to raw-aq-readings-dlq.
```

Anomaly rules:

```text
If baseline_count < 24:
  is_anomaly = false
  anomaly_reason = 'insufficient_baseline'

If stddev is null or 0:
  is_anomaly = false
  anomaly_reason = 'zero_stddev'

If value is physically impossible:
  is_anomaly = true
  anomaly_reason = 'range'

If abs(zscore) > 3 and baseline_count sufficient:
  is_anomaly = true
  anomaly_reason = 'zscore'
```

District query:

```sql
SELECT s.id AS station_id, d.id AS district_id
FROM stations s
LEFT JOIN districts d ON ST_Covers(d.boundary, s.location)
WHERE s.id = ANY(%(station_ids)s::int[]);
```

---

## 19. AQI calculation policy

Implement PM2.5 first as the authoritative pollutant.

```text
Phase A:
  PM2.5 AQI authoritative.
  PM10, NO2, O3, CO displayed as raw readings where available.

Phase B:
  Add pollutant-specific AQI calculators with unit tests.

Phase C:
  Composite AQI = max(valid pollutant AQI values).
```

PM2.5 calculation module:

```text
services/common/aqi_calculator.py
```

Requirements:

```text
- pure Python
- no Spark dependency
- pytest testable
- handles out-of-range values
- returns AQI integer or None
- exposes category and color helper
```

Composite AQI is not stored. It is computed at query time from latest valid pollutant AQI values.

---

## 20. Forecasting system

Forecasting must not depend only on SARIMAX.

Use model arbitration:

```text
Tier 1: SARIMAX
  Use when station has >=70 percent observed PM2.5 coverage over last 90 days
  and future weather covariates are available for 72h.

Tier 2: CAMS/Open-Meteo bias-adjusted forecast
  Use when modeled AQ forecast exists but observed history is insufficient for SARIMAX.

Tier 3: Persistence baseline
  Always available. Use latest observed/recent/modeled AQI as baseline.
```

Selection pseudocode:

```python
def choose_forecast_model(station_id, pollutant):
    if observed_coverage(station_id, pollutant, days=90) >= 0.70 and future_weather_available(hours=72):
        return "sarimax"
    if modeled_aq_forecast_available(station_id, pollutant, hours=72):
        return "openmeteo_cams_bias_adjusted"
    return "persistence"
```

SARIMAX data alignment:

```text
Training target:
  last 90 days hourly observed AQI

Training exogenous variables:
  same last 90 days hourly weather variables

Prediction exogenous variables:
  next 72 hours hourly weather forecast
```

Bias-adjusted modeled forecast:

```text
bias = median(observed_aqi_last_7d - modeled_aqi_last_7d)
forecast = modeled_future_aqi + bias
```

Forecast API must expose:

```text
model_name
model_source
fallback_reason if not SARIMAX
historical_mae if available
confidence band
```

---

## 21. Airflow DAGs

Airflow must run with PostgreSQL metadata DB. Do not use SQLite for LocalExecutor.

All DAGs must:

```text
- use structlog
- write pipeline_runs on success and failure
- be idempotent
- be manually triggerable
- avoid side effects when rerun for same date range
```

### 21.1 historical_backfill

Purpose:

```text
Load observed historical AQ data from OpenAQ archive first, API second.
```

Behavior:

```text
1. Read station_sensors.
2. For each location/day, try OpenAQ S3 archive CSV.gz.
3. Parse and map sensor_id/parameter/unit/value/datetime.
4. Insert into aq_readings with source='openaq_archive'.
5. If archive missing, call OpenAQ sensor measurements API.
6. Record every day in backfill_manifest.
```

### 21.2 weather_historical_backfill

Purpose:

```text
Load historical weather for forecast training.
```

Behavior:

```text
Open-Meteo archive, one location-month per task, direct DB insert.
```

### 21.3 modeled_aq_backfill_or_refresh

Purpose:

```text
Populate modeled AQ baseline and future forecasts from Open-Meteo Air Quality.
```

Can be Airflow batch or standalone service. If frequent, prefer standalone poller.

### 21.4 forecast_recompute

Schedule:

```text
@hourly
```

Tasks:

```text
1. check_data_sources
2. run_forecast_arbitration
3. write forecast_runs and forecasts
4. compute_accuracy for elapsed forecasts
```

Do not fail just because live observed AQ is stale. Fall back and log.

### 21.5 data_quality_check

Schedule:

```text
every 2 hours
```

Checks:

```text
station coverage:
  records DEGRADED if fewer than 3 fresh stations, not FAIL

value ranges:
  warn for invalid or extreme values

dead sensors:
  set station_sensors.active=false only after sustained absence, not temporary outage

anomaly rate:
  warn or critical if detector seems broken

coverage snapshot:
  write coverage_snapshots row
```

### 21.6 firms_daily

Purpose:

```text
Download VIIRS fire events around Nepal/South Asia and load fire_events.
```

Use stable event hash:

```python
event_hash = sha256(f"{lat}|{lon}|{acq_date}|{acq_time}|{satellite}|{instrument}".encode()).hexdigest()
```

---

## 22. API contract

Base URL:

```text
http://localhost:8000
```

Development auth:

```text
None
```

Public deployment auth:

```text
Optional X-API-Key for backend API
```

All endpoints must include provenance where relevant.

### 22.1 GET /api/stations

Returns station snapshot.

Required response additions:

```json
{
  "valley_composite_aqi": 94,
  "coverage_mode": "RECENT_OBSERVED",
  "confidence": "medium",
  "fresh_station_count": 2,
  "recent_station_count": 4,
  "modeled_available": true,
  "stations": [
    {
      "id": 1,
      "name": "Kathmandu Station",
      "lat": 27.7172,
      "lon": 85.324,
      "active": true,
      "status": "active",
      "last_seen": "2026-04-27T05:55:00Z",
      "current_aqi": 87,
      "dominant_pollutant": "pm25",
      "source": "openaq_live",
      "observation_type": "observed",
      "freshness_minutes": 18,
      "health_category": "Moderate"
    }
  ]
}
```

### 22.2 GET /api/stations/{id}/current

Important: do not require pollutants to share exact timestamps. Select latest per pollutant within a freshness window.

SQL pattern:

```sql
SELECT DISTINCT ON (pollutant)
  pollutant, value, unit, aqi, timestamp, is_anomaly, source, observation_type
FROM aq_readings
WHERE station_id = $1
  AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY pollutant, timestamp DESC;
```

### 22.3 GET /api/valley/current

Must return:

```json
{
  "timestamp": "2026-04-27T06:00:00Z",
  "composite_aqi": 94,
  "dominant_pollutant": "pm25",
  "coverage_mode": "RECENT_OBSERVED",
  "confidence": "medium",
  "fresh_station_count": 2,
  "recent_station_count": 4,
  "modeled_available": true,
  "recommendation": "Sensitive groups should limit prolonged outdoor exertion.",
  "message": "Using latest observed readings from the last 24 hours because fewer than 3 stations reported in the last 2 hours."
}
```

### 22.4 GET /api/interpolation/current

Fallback order:

```text
1. live observed IDW
2. recent observed IDW
3. modeled baseline grid
4. replay grid
5. insufficient data response
```

Required response:

```json
{
  "grid": {
    "rows": 50,
    "cols": 50,
    "bounds": {"min_lat": 27.55, "max_lat": 27.80, "min_lon": 85.20, "max_lon": 85.50},
    "values": [[87, 91, 94]]
  },
  "station_count": 4,
  "coverage_mode": "RECENT_OBSERVED",
  "confidence": "medium",
  "source": "openaq_live_recent",
  "computed_at": "2026-04-27T06:00:00Z",
  "insufficient_data": false,
  "message": "Recent observed data used because live station coverage is sparse."
}
```

Distance math must use projected meters or geography, not raw lat/lon degree distance.

### 22.5 GET /api/forecasts/{station_id}

Required response:

```json
{
  "station_id": 1,
  "pollutant": "pm25",
  "generated_at": "2026-04-27T06:00:00Z",
  "model": "openmeteo_cams_bias_adjusted",
  "model_source": "modeled_aq_with_observed_bias",
  "fallback_reason": "Insufficient 90-day observed coverage for SARIMAX.",
  "historical_mae": 12.4,
  "forecasts": [
    {
      "target_timestamp": "2026-04-27T07:00:00Z",
      "horizon_hours": 1,
      "predicted_aqi": 91,
      "lower_bound": 74,
      "upper_bound": 108
    }
  ]
}
```

### 22.6 GET /api/health-advisory

Distance must be computed using geography:

```sql
ST_Distance(
  stations.location::geography,
  ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
) / 1000.0 AS distance_km
```

### 22.7 GET /api/pipeline/health

Must combine:

```text
- pipeline_runs latest row per component
- DB ping
- latest AQ timestamp
- Kafka connectivity
- Kafka consumer lag if available
- OpenAQ poller /health
- weather poller /health
- modeled AQ freshness
- coverage_snapshots latest row
```

Overall statuses:

```text
healthy
  core services are alive and data is fresh enough for current selected mode

degraded
  one or more sources are stale but fallback mode is working

down
  core API/DB/Kafka unavailable or no data mode possible
```

### 22.8 WebSocket /ws/live-feed

On connect:

```text
Send current /api/stations snapshot.
```

On Kafka `processed-aq-readings`:

```text
Broadcast new_readings event.
```

On reconnect:

```text
Client refreshes station snapshot from REST.
```

This protects against missed best-effort Kafka notifications.

---

## 23. Frontend specification

### 23.1 Required views

```text
1. Live Map
2. Live Charts
3. Historical Explorer
4. Forecast Panel
5. Pipeline Health
6. About / Methodology
```

### 23.2 Live Map

Must show:

```text
- Kathmandu dark basemap
- station markers colored by AQI category
- marker radius proportional to AQI
- provenance badge: LIVE_OBSERVED / RECENT_OBSERVED / MODELED_BASELINE / REPLAY_DEMO
- confidence label
- last updated timestamp
- WebSocket status dot
- heatmap toggle
- fire overlay toggle
```

Heatmap rendering:

```text
1. Fetch /api/interpolation/current.
2. Convert 50x50 grid to canvas.
3. Convert canvas to image source.
4. Add/update Mapbox/MapLibre raster layer.
5. Do not reinitialize the map on each update.
```

### 23.3 Demo mode

Demo mode frontend toggle must call backend/replay service or switch UI into replay-awareness. It must not fake values locally without provenance.

UI label:

```text
DEMO MODE - historical data replayed through Kafka/Spark
```

### 23.4 Map provider adapter

Add:

```text
src/services/mapEngine.js
```

Behavior:

```javascript
export async function loadMapEngine() {
  if (import.meta.env.VITE_MAP_PROVIDER === 'maplibre') {
    return await import('maplibre-gl');
  }
  return await import('mapbox-gl');
}
```

### 23.5 Historical explorer

Must include:

```text
- station selector
- valley-wide option
- date range picker
- hourly/daily toggle
- D3 calendar heatmap
- D3 zoom/brush time series
- Tihar bands
- monsoon bands
- COVID lockdown band if data range includes it
- fire-event overlays where relevant
```

### 23.6 Forecast panel

Must include:

```text
- model name
- fallback reason if not SARIMAX
- 72-hour area chart
- confidence band
- best 6-hour outdoor windows
- historical MAE if available
```

### 23.7 Pipeline health dashboard

Must show:

```text
- OpenAQ poller status
- weather poller status
- Open-Meteo AQ status
- Spark stream status
- Airflow status
- Kafka status
- DB latest reading timestamp
- current coverage mode
- last replay status
```

---

## 24. Logging standards

All Python services must use structlog.

Prohibited:

```text
print()
logging.info() without structured context
except: pass
silent fallback without warning
```

Required event examples:

```python
log.info("openaq_poll_completed", sensors_polled=n, messages_published=m, duration_ms=ms)
log.warning("coverage_degraded", fresh_station_count=2, recent_station_count=4, coverage_mode="RECENT_OBSERVED")
log.info("forecast_model_selected", station_id=id, model="persistence", reason="insufficient_coverage")
log.error("api_request_failed", source="openaq", endpoint=endpoint, status_code=code, error=str(e))
log.info("replay_started", start=start, end=end, speed=10)
log.info("spark_batch_complete", batch_id=batch_id, input_rows=n, written=w, anomalies=a, duration_ms=ms)
```

Every service must expose `/health` if it is long-running.

Health response:

```json
{
  "status": "healthy",
  "service": "openaq-poller",
  "timestamp": "2026-04-27T06:00:00Z",
  "checks": {
    "kafka": "ok",
    "external_api": "ok",
    "database": "ok",
    "last_successful_poll": "2026-04-27T05:57:00Z",
    "last_error": null
  }
}
```

---

## 25. Testing requirements

Minimum tests:

```text
tests/unit/test_aqi_calculator.py
tests/unit/test_coverage_mode.py
tests/unit/test_idw.py
tests/unit/test_openaq_parser.py
tests/unit/test_openmeteo_aq_parser.py
tests/unit/test_weather_parser.py
tests/unit/test_firms_parser.py
tests/api/test_stations_contract.py
tests/api/test_valley_current_contract.py
tests/api/test_interpolation_contract.py
tests/api/test_forecast_contract.py
tests/integration/test_db_migrations.py
tests/integration/test_kafka_roundtrip.py
tests/integration/test_replay_publisher.py
tests/integration/test_spark_batch_fixture.py
```

Critical fixtures:

```text
- OpenAQ sensor measurement valid
- OpenAQ API error
- missing unit
- unknown pollutant
- duplicate reading
- out-of-range PM2.5
- no station coverage
- sparse live coverage with modeled fallback
- replay message with original_timestamp
- FIRMS CSV with duplicate rows
- weather response missing fields
```

---

## 26. Architecture Decision Record

| ID | Component | Decision | Rejected alternative | Reason |
|---|---|---|---|---|
| D-01 | Live ingestion | Standalone services for OpenAQ/weather/model AQ polling | Airflow for 5-minute live ingestion | Lower latency and lower scheduler overhead |
| D-02 | OpenAQ model | Treat OpenAQ sensors as ingestion units and stations as logical frontend locations | Poll only by location_id | OpenAQ measurements are sensor-based |
| D-03 | Provenance | Store source and observation_type on every AQ reading | Mix observed/modeled/replay values without labels | Prevents misleading output |
| D-04 | Coverage | Dashboard uses coverage modes and graceful degradation | Fail when fewer than 3 stations are fresh | Public station coverage is irregular |
| D-05 | Backfill | OpenAQ archive first, API fallback second | API-only historical backfill | Faster, less rate-limit prone |
| D-06 | Demo | Replay historical records through Kafka/Spark | Frontend-only animation | Proves actual pipeline during demo |
| D-07 | Forecast | Model arbitration: SARIMAX, bias-adjusted modeled AQ, persistence | SARIMAX-only | Always returns a forecast honestly |
| D-08 | Airflow DB | Airflow uses PostgreSQL metadata DB | SQLite metadata DB | LocalExecutor needs a real DB for credible runs |
| D-09 | Timescale keys | Hypertable unique keys include timestamp | id-only primary keys | Required by TimescaleDB uniqueness rules |
| D-10 | District geometry | Use MULTIPOLYGON and ST_Covers | POLYGON and ST_Contains only | Real boundaries can be multipolygon; boundary points matter |
| D-11 | Weather writes | Weather poller writes directly to DB | Weather poller consumes its own Kafka topic | Low volume does not need self-consume complexity |
| D-12 | IDW distance | Use projected/geography distance | Raw lat/lon degree distance | Technically correct spatial weighting |
| D-13 | Docker | Use Compose profiles | Run everything all the time | Keeps architecture but supports 8 GB laptops |
| D-14 | Map | Mapbox with MapLibre fallback | Mapbox-only hard dependency | Preserves visual polish without token lock-in |
| D-15 | AQI scope | PM2.5 authoritative first; other pollutant AQI after tests | Claim all pollutant AQI is correct from day one | Avoids scientific errors |
| D-16 | Notification | processed-aq-readings is best-effort | Treat Kafka notification as source of truth | DB is authoritative; WebSocket can miss events |
| D-17 | FIRMS | Use event_hash for idempotency | UNIQUE(location, event_date) | Multiple events can occur at same location/day |

---

## 27. Anti-patterns to enforce

| ID | Anti-pattern | What it looks like | Correct approach |
|---|---|---|---|
| AP-01 | Fake live data | Demo data shown as if live observed data | Label as REPLAY_DEMO or MODELED_BASELINE |
| AP-02 | OpenAQ location-only polling | `/v3/measurements?location_id=...` | Use sensor registry and `/v3/sensors/{id}/measurements` |
| AP-03 | Airflow SQLite LocalExecutor | Airflow starts with SQLite and LocalExecutor | Add airflow-postgres service |
| AP-04 | Failing on sparse coverage | `count < 3` raises exception | Record DEGRADED and use fallback mode |
| AP-05 | Weather self-consumer | Poller publishes weather then consumes own topic | Direct DB write, optional Kafka event only |
| AP-06 | Unlabeled modeled data | CAMS/Open-Meteo AQ shown as observed | Store in modeled_aq_readings and label in UI |
| AP-07 | SARIMAX theater | Forecast silently falls back with no explanation | Expose model_source and fallback_reason |
| AP-08 | Timescale invalid key | PRIMARY KEY(id) on hypertable | Include timestamp in primary/unique key |
| AP-09 | Frontend-only demo | Values animated locally | Replay through Kafka/Spark |
| AP-10 | Scope creep before core | Wind rose, terrain, fire overlay before ingestion/API stable | Build core pipeline first |
| AP-11 | Silent failures | `except: pass` or no pipeline_runs row | structured logs and health records |
| AP-12 | Raw-degree distance | distance in EPSG:4326 degrees | geography or projected meters |

---

## 28. Updated implementation phase breakdown

### Phase -1: Data reality check

Build:

```text
scripts/sync_openaq_metadata.py
scripts/check_coverage.py
docs/data-source-validation.md
```

Exit:

```text
OpenAQ API key works.
Stations and sensors are discovered.
Coverage is measured honestly.
Modeled AQ fallback is verified.
Demo replay dataset strategy is selected.
```

### Phase 0: Foundation

Build:

```text
docker-compose.yml with profiles
Airflow PostgreSQL metadata service
TimescaleDB/PostGIS
Alembic migrations 001-005
Kafka topic creation
logging_config.py
verify_env.sh
seed weather locations
district loader
```

### Phase 1: Source registry and OpenAQ live ingestion

Build:

```text
station_sensors sync
openaq-poller sensor-based ingestion
rate-limit handling
health endpoint
raw-aq-readings publishing
pipeline_runs errors
```

### Phase 2: Replay publisher and Spark streaming

Build:

```text
replay-publisher
aq_stream_processor.py
aqi_calculator.py
anomaly handling
district assignment with ST_Covers
Timescale upserts
processed-aq-readings notifications
```

### Phase 3: Weather and modeled AQ enrichment

Build:

```text
weather-poller direct DB write
openmeteo-aq-poller modeled_aq_readings
weather historical backfill
modeled AQ refresh/backfill
```

### Phase 4: Historical backfill and FIRMS

Build:

```text
historical_backfill archive-first DAG
backfill_manifest
firms_daily DAG
fire_events with event_hash
continuous aggregate refresh verification
```

### Phase 5: Forecasting

Build:

```text
forecast_runs
forecast model arbitration
persistence baseline
bias-adjusted modeled AQ forecast
SARIMAX when coverage permits
forecast_accuracy
/api/forecasts/{station_id}
```

### Phase 6: API layer

Build:

```text
all REST endpoints
coverage_mode computation
IDW fallback logic
pipeline health
WebSocket broadcaster
Pydantic schemas
tests/api
```

### Phase 7: Frontend core

Build:

```text
React/Vite app
Mapbox/MapLibre adapter
Live Map
station markers
AQI badge
coverage/provenance banner
WebSocket hook
basic charts
Pipeline health panel
```

### Phase 8: Historical and forecast UI

Build:

```text
Historical Explorer
D3 calendar heatmap
D3 brush/zoom time series
event annotations
Forecast Panel
best outdoor windows
model fallback explanation
```

### Phase 9: Advanced polish

Build:

```text
IDW heatmap raster layer
wind rose
cigarette equivalence counter
fire overlay
optional 3D terrain
```

### Phase 10: Hardening and delivery

Build:

```text
benchmarks
load test
README
architecture diagram
screenshots
setup verification
phase summaries
final demo script
```

---

## 29. Updated LLM phase planning prompt

Paste the following after this system overview when asking an AI assistant to generate the full phase plan.

```text
You have read the complete HimalayaAir Fixed System Overview Prompt v2.0 above.
Every section is authoritative and binding.

Your task: produce a complete implementation plan for HimalayaAir using the corrected, provenance-aware architecture.

Constraints:
- One final-year CS student.
- AI-assisted coding with Claude Code / Cursor.
- 8-16 GB RAM laptop.
- Budget: prefer USD 0.
- Timeline: 10-12 weeks.
- Preserve the original product vision. Do not remove Kafka, Spark, Airflow, forecasting, IDW, or the visual dashboard.
- Fix fragility through source adapters, coverage modes, modeled fallback, replay mode, and honest provenance.

Mandatory phase order:
- Phase -1: Data reality check
- Phase 0: Foundation
- Phase 1: Source registry and OpenAQ live ingestion
- Phase 2: Replay publisher and Spark streaming
- Phase 3: Weather and modeled AQ enrichment
- Phase 4: Historical backfill and FIRMS
- Phase 5: Forecasting
- Phase 6: API layer
- Phase 7: Frontend core
- Phase 8: Historical and forecast UI
- Phase 9: Advanced polish
- Phase 10: Hardening and delivery

Every phase must use this exact structure:

PHASE [N]: [NAME]
Timeline:
Objective:
Risk Level: LOW | MEDIUM | HIGH

ENTRY CRITERIA:
- verifiable condition

COMPONENTS BUILT:
- exact file path
- what it does
- key functions/classes
- input/output contracts

KEY DECISIONS MADE:
- reference ADR IDs from this document

FAILURE MODES AND MITIGATIONS:
- what breaks
- how to detect
- how to recover

AI CODING TASKS:
- task name
- exact implementation prompt hint
- libraries to use
- schemas to follow
- structlog events to emit
- tests to write
- CHANGELOG entry to add

EXIT CRITERIA:
- exact command to run
- expected output
- DB query if applicable
- endpoint curl if applicable
- test command if applicable

DELIVERABLE:
- what can be demonstrated immediately to a supervisor

Validation checklist:
- No OpenAQ location-only measurement polling.
- OPENAQ_API_KEY is required server-side.
- station_sensors table exists and is used.
- All hypertable unique keys include timestamp.
- Airflow uses PostgreSQL metadata DB.
- Sparse station coverage degrades, not fails.
- Modeled AQ is labeled and separated.
- Demo mode replays through Kafka/Spark.
- Forecasting uses model arbitration.
- Docker profiles exist.
- Every Python service uses structlog.
- Every phase updates CHANGELOG.md.
- Every phase writes a phase summary.

Begin with Phase -1 and continue through Phase 10 without stopping.
```

---

## 30. Reference links checked for this v2.0 design

Use official documentation during implementation. Verify again at the start of coding because external APIs can change.

```text
OpenAQ API key docs:
https://docs.openaq.org/using-the-api/api-key

OpenAQ measurements resources:
https://docs.openaq.org/resources/measurements

OpenAQ AWS archive:
https://docs.openaq.org/aws/about

Open-Meteo Air Quality API:
https://open-meteo.com/en/docs/air-quality-api

TimescaleDB hypertable unique indexes:
https://www.tigerdata.com/docs/use-timescale/latest/hypertables/hypertables-and-unique-indexes

Airflow database backend:
https://airflow.apache.org/docs/apache-airflow/stable/howto/set-up-database.html

NASA FIRMS Area API:
https://firms.modaps.eosdis.nasa.gov/api/area/
```

---

## 31. Final build philosophy

HimalayaAir should not be judged by whether public sensors happen to report perfectly on demo day. It should be judged by whether it handles real-world environmental data conditions intelligently.

The strongest version of the project is:

```text
Observed when possible.
Recent when necessary.
Modeled when useful.
Replayed when demonstrating.
Always labeled.
Always explainable.
Always visually impressive.
```

That is the fixed system.
