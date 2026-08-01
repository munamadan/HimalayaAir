# HimalayaAir - FYP Report Draft

> Markdown draft of the final-year project report. Heading levels map to Word Heading 1-4. Front matter (acknowledgment, abstract, abbreviations, lists, TOC) and the cover are handled separately and are not included here.

## CHAPTER 1: INTRODUCTION

### 1.1 Introduction

Kathmandu Valley is one of the most polluted places in South Asia during winter. The valley is bowl-shaped, so vehicle exhaust, brick-kiln smoke, road dust, and household burning get trapped. PM2.5 and PM10 often cross World Health Organization limits by several times. People living in the valley feel this daily, but the public data behind it is thin, late, and scattered.

A few government and OpenAQ shared sensors operate in the valley, but they report irregularly. A station can stop sending for hours or days. The OpenAQ v3 API can change without warning. Fresh values can take hours to show up. Free modeled datasets like Open-Meteo Air Quality cover the area without gaps, but they are estimates, not measured truth. A dashboard that shows only the latest OpenAQ number will be empty or old much of the time. A dashboard that quietly puts modeled data in place of live data misleads the user about what they are seeing.

HimalayaAir is a full-stack data engineering platform built around this problem. It pulls measured sensor data first. When live coverage is not enough, it falls back to recent measured values, then to modeled data labeled as modeled. A replay mode keeps demonstrations reproducible when public APIs are down. Every reading carries its source, observation type, coverage mode, and confidence from ingestion through storage to the screen.

Data moves through Kafka. Spark Structured Streaming processes it. TimescaleDB with PostGIS stores it. FastAPI and WebSocket serve it. React draws it on a Kathmandu-centered map. Airflow runs the backfills, data-quality checks, fire-event loading, and forecast recomputation. For forecasting, the system picks between a SARIMAX model with weather covariates, a bias-adjusted modeled fallback, and a persistence baseline, depending on what data is available.

The rest of this report explains how the system was built, why each part was chosen, how it was tested, and what the results show.

### 1.2 Problem Statement

Air pollution in Kathmandu Valley is a public health issue, and anyone building a useful air-quality tool quickly runs into a data problem. The measured data is unreliable in three ways.

Sensor coverage is sparse. Only a handful of OpenAQ shared and government stations sit inside the valley, and they are not evenly placed. One or more stations can stop reporting for hours or days. At times there are not enough active stations to draw a meaningful pollution surface across the valley.

The data is also delayed, and it changes without notice. OpenAQ v3 is a free public API. It updates on its own schedule, its structure has changed between versions, and a fresh reading can take hours to appear. Any tool that assumes live data is always there will break on the days it is not.

Falling back to modeled data has its own risk. Open-Meteo Air Quality gives continuous modeled coverage over Kathmandu. But modeled data is an estimate, not a sensor reading. If a platform swaps modeled values into the same display as live measured values without telling the user, the tool becomes misleading. Someone looking at a red hotspot cannot tell whether a station measured that pollution or a model guessed it.

HimalayaAir solves these problems together. The goal is to give the valley a working air-quality intelligence tool that prioritizes measured data, falls back to modeled or replay data when needed, and never hides which is which. Every reading keeps enough provenance information that the user can trust what the screen shows.

The platform also needs to cover the five data engineering topics taught in the final-year curriculum: data modeling and database systems, distributed systems and big data processing, pipeline and orchestration, cloud and infrastructure, and programming and data structures. The internal stack has to demonstrate all five areas for the project to qualify academically.

### 1.3 Objectives

The project has eight objectives:

To build a provenance-aware data pipeline that ingests OpenAQ observed sensor data, Open-Meteo weather and modeled air-quality data, and replay fixtures into a shared Kafka bus. Every reading carries its source, observation type, coverage mode, and confidence from ingestion to the user interface.

To process raw readings through Spark Structured Streaming: validate payloads, compute AQI with EPA 2024 breakpoints, detect anomalies with range checks and rolling z-scores, and write idempotently into TimescaleDB hypertables with PostGIS spatial support.

To store data in a time-series and geospatial database that uses hypertables chunked by time, continuous aggregates for hourly and daily summaries, and GiST indexes on station and district geometry. Historical and spatial queries need to stay fast as the dataset grows.

To expose the processed data through a FastAPI REST API and a WebSocket live feed, with endpoints for station snapshots, valley composite AQI, IDW interpolation grids, forecasts, health advisories, fire events, and pipeline health.

To display the data on a Kathmandu-centered React map with station markers, an AQI surface generated by inverse distance weighting interpolation, a wind-flow overlay, fire-event overlays, a forecast panel with confidence bands, a historical explorer with time-series and calendar views, and a demo replay mode.

To forecast valley pollution up to 72 hours ahead using model arbitration. The system tries SARIMAX with weather covariates first, then a bias-adjusted modeled baseline, then a persistence baseline. When the data for a stronger model is missing, the forecast falls back instead of failing.

To orchestrate backfills, data-quality checks, fire-event loading, and forecast recomputation with Airflow DAGs that run on schedule and stay idempotent through a backfill manifest.

To keep the whole system runnable on a single laptop with 8 to 16 GB of RAM and zero recurring cost. Docker Compose profiles start only the services needed for a given task.

### 1.4 Scope and Limitations

#### 1.4.1 Scope

The project covers the Kathmandu Valley area. The bounding box used for data fetching is 85.20 to 85.50 east and 27.55 to 27.80 north. Inside this box are the three valley districts, Kathmandu, Lalitpur, and Bhaktapur, plus the surrounding hills. OpenAQ sensors, Open-Meteo grid points, and fire events inside the box are the data sources.

Three kinds of data come into the platform. Observed air-quality readings come from the OpenAQ v3 sensor measurement endpoint. Weather and modeled air-quality data come from Open-Meteo's weather and air-quality APIs. Fire events come from NASA FIRMS. A replay publisher can also push stored fixture data through Kafka when a demo is needed and the live APIs are down.

From there, data moves through Kafka onto Spark Structured Streaming and into TimescaleDB with PostGIS. FastAPI serves it to a React frontend over REST and WebSocket. Airflow runs the scheduled backfills, quality checks, fire-event loads, and forecast recomputation. For forecasting, the system tries SARIMAX with weather covariates, then a bias-adjusted modeled fallback, then a persistence baseline.

On screen, the user sees a Kathmandu-centered map with station markers, an AQI surface from inverse distance weighting interpolation, a wind-flow overlay, and fire-event overlays. Other screens include a forecast panel with confidence bands, a historical explorer with time-series and calendar views, and a replay demo mode. Provenance is shown on screen, and the user can tell live, recent, modeled, and replay data apart.

Everything runs locally through Docker Compose profiles. A profile starts only the services needed for a given task, such as core, stream, batch, or demo, and the laptop is not overloaded.

#### 1.4.2 Limitation

Everything is built by one final-year student on a personal laptop with 8 to 16 GB of RAM, and the infrastructure is sized for one machine. Kafka runs as a single KRaft broker without Zookeeper, not a multi-node cluster. Spark runs in local mode with two executor cores, not on a real cluster. These choices are fine for a defense demo. They would not carry real production load.

The data sources are free public APIs. OpenAQ v3, Open-Meteo weather, Open-Meteo Air Quality, and NASA FIRMS all have rate limits and no guaranteed uptime. The OpenAQ structure has changed between versions, and a fresh reading can take hours to appear. The system handles this by falling back to recent or modeled data, but it cannot invent measured data that the public sources do not provide.

Station coverage inside the valley is thin. Only a handful of OpenAQ shared and government stations sit inside the bounding box, and they report irregularly. When too few stations are active, the interpolation surface becomes coarse, and the display switches to station-only or modeled-baseline mode.

Forecasting is constrained by how much history the project can store and how complete the weather covariates are. SARIMAX needs roughly 90 days of observed data and matching weather history to run well. When coverage is short, the system falls back to a bias-adjusted modeled forecast or a persistence baseline.

The ML gradient-boosting model in the code is a placeholder for demonstration. It is not trained on HimalayaAir data, and the forecast panel labels it as a placeholder, not a working learned model.

### 1.5 Development Methodology

The project follows an iterative and incremental development methodology. Work was done with AI assistance using Codex, in short focused sessions, and each piece of the system was tested against the real running stack before the next session started. That approach suits a data engineering project, where the behavior of public APIs, the size of the data, and the limits of a single laptop only become clear once the code runs.

The development was split into 14 phases. Each phase had a written plan, a set of exit criteria, and a completion summary before the next phase started. The phases moved bottom up, from the data reality check and infrastructure, through the database, Kafka, and Spark layers, into the API, forecasting, and frontend, and finished with hardening and benchmarks. A few extra sessions after Phase 14 refined the frontend layout, added a replay demo, and added a placeholder ML forecast path.

A few rules ran across all phases. Schema changes always went through Alembic migrations, never by hand. TimescaleDB hypertable primary keys always included the time column. Every air-quality reading kept its source and observation type. Code was not allowed to swallow exceptions silently or use bare excepts. External API calls always used timeouts, retries, and rate-limit handling. No secrets went into code, tests, docs, or frontend bundles. Every meaningful change was recorded in a changelog, and every phase ended with a summary.

Testing grew with the system. Backend tests run on pytest and cover AQI calculation, message schemas and provenance checks, Spark anomaly detection, forecast model arbitration, OpenAQ ingestion, weather pollers, Airflow tasks, and API contracts against fixture data. Frontend tests run on Vitest and cover AQI category mapping, station search, and heatmap rasterization. Integration tests run the Spark job against a fixture batch and check the database and message outputs.

Most of the system is exercised by tests. The parts that depend on live public APIs are exercised by replay fixtures that produce the same shape of data. A defense demo stays reproducible even when the public sources are down.

### 1.6 Report Organization

The report is organized into six chapters.

Chapter 1 gives the introduction. It explains the air pollution context in Kathmandu Valley, the problem with sparse and delayed public sensor data, the objectives of the project, the scope and limitations, and the development methodology used to build the system.

Chapter 2 covers the background study and literature review. It explains the core technologies used in the platform, including Kafka, Spark Structured Streaming, TimescaleDB with PostGIS, Airflow, FastAPI and WebSocket, and inverse distance weighting interpolation with AQI calculation. It then reviews related work on air-quality platforms, real-time streaming pipelines, and forecasting approaches.

Chapter 3 presents the system analysis. It lists the functional and non-functional requirements, the feasibility analysis, the process models in the form of use case, context, and data flow diagrams, and the database model in the form of an entity relationship diagram.

Chapter 4 presents the system design. It gives the end-to-end system flowchart, the interface design as wireframe mockups of the main screens, and the algorithm details for AQI calculation, IDW interpolation, provenance resolution, and forecast arbitration.

Chapter 5 describes implementation and testing. It explains how each module was built, the unit and integration tests run against it, and the result analysis covering forecast accuracy and provenance mode distribution.

Chapter 6 closes with the conclusion and future enhancements. It summarizes what was built, what was learned, and what could be improved or extended next.

The references are listed after Chapter 6. Appendix I at the end holds the screenshots of the live running system.

## CHAPTER 2: BACKGROUND STUDY AND LITERATURE REVIEW

### 2.1 Background Study

This section explains the core technologies the platform is built on, one at a time, and how each one is used inside HimalayaAir.

#### 2.1.1 Kafka Message Bus

Apache Kafka is a distributed event streaming platform. In simple terms it works as a message bus. Producers publish records onto named streams called topics, and consumers read from those topics in their own time. Topics are split into partitions, and each partition keeps its records in order on disk for a configurable retention period [(Author, Year)]. Because records stay on disk after they are read, many independent consumers can replay the same stream at different speeds without disturbing each other. Newer Kafka versions use a built-in controller protocol called KRaft, which removed the old Zookeeper dependency and makes a single-node setup much simpler to run [(Author, Year)].

HimalayaAir uses a single KRaft Kafka broker as the central bus between ingestion and processing. The system declares six topics. The `raw-aq-readings` topic carries unprocessed sensor messages from the OpenAQ poller and the replay publisher. The `processed-aq-readings` topic carries validated and enriched readings from the Spark job, which the API live feed and downstream consumers read. The `weather-data` and `modeled-aq-data` topics are reserved for weather and modeled air-quality payloads. A `raw-aq-readings-dlq` dead-letter topic holds payloads that failed validation, so bad data is never silently dropped. A `pipeline-events` topic is reserved for operational events. Message keys include the station, sensor, pollutant, and timestamp, so records for the same sensor stay in order on the same partition. Raw topics keep 24 hours of retention, which matches the short operational window the streaming job needs [(Author, Year)].

Figure 1: Kafka topic and producer/consumer block diagram
