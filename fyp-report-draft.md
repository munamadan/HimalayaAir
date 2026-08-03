# HimalayaAir - FYP Report Draft

> Markdown draft of the final-year project report. Heading levels map to Word Heading 1-4. Front matter (acknowledgment, abstract, abbreviations, lists, TOC) and the cover are handled separately and are not included here.

## Style guide (read before continuing)

- Plain English. Short sentences. Concrete numbers over adjectives.
- No em dashes. No trailing ", which..." or ", so..." clauses.
- Avoid AI-frequent words: leverage, robust, seamless, delve, moreover, furthermore, seamless, crucial, as follows.
- Vary paragraph openers; not every paragraph should start with "The".
- No "it's not X, it's Y" framing. No "is built to" passive constructions.
- Write one section per turn and let the user review before continuing.
- No git commits for this report. The draft lives only in this file.
- Current state: Chapters 1-6 written, reviewed, and style-cleaned. References (20 IEEE entries) and Appendix I Screenshots written. Figures 13, 17, 18 generated in docs/figures/. Final live screenshots under docs/screenshots/ are captured by the user.

## CHAPTER 1: INTRODUCTION

### 1.1 Introduction

Kathmandu Valley is one of the most polluted places in South Asia during winter. The valley is bowl-shaped. Vehicle exhaust, brick-kiln smoke, road dust, and household burning get trapped. PM2.5 and PM10 often cross World Health Organization limits by several times. People living in the valley feel this daily, but the public data behind it is thin, late, and scattered.

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

To forecast valley pollution up to 48 hours ahead using model arbitration. The system tries SARIMAX with weather covariates first, then a bias-adjusted modeled baseline, then a persistence baseline. When the data for a stronger model is missing, the forecast falls back instead of failing.

To orchestrate backfills, data-quality checks, fire-event loading, and forecast recomputation with Airflow DAGs that run on schedule and stay idempotent through a backfill manifest.

To keep the whole system runnable on a single laptop with 8 to 16 GB of RAM and zero recurring cost. Docker Compose profiles start only the services needed for a given task.

### 1.4 Scope and Limitations

#### 1.4.1 Scope

The project covers the Kathmandu Valley area. The bounding box used for data fetching is 85.20 to 85.50 east and 27.55 to 27.80 north. Inside this box are the three valley districts, Kathmandu, Lalitpur, and Bhaktapur, plus the surrounding hills. OpenAQ sensors, Open-Meteo grid points, and fire events inside the box are the data sources.

Three kinds of data come into the platform. Observed air-quality readings come from the OpenAQ v3 sensor measurement endpoint [10]. Weather and modeled air-quality data come from Open-Meteo's weather and air-quality APIs [11]. Fire events come from NASA FIRMS [12]. A replay publisher can also push stored fixture data through Kafka when a demo is needed and the live APIs are down.

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

Apache Kafka is a distributed event streaming platform. It works as a message bus. Producers publish records onto named streams called topics, and consumers read from those topics in their own time. Topics are split into partitions, and each partition keeps its records in order on disk for a configurable retention period [1]. Records stay on disk after they are read. Many independent consumers replay the stream at their own speed without disturbing each other. Newer Kafka versions use a built-in controller protocol called KRaft. It removed the old Zookeeper dependency and makes a single-node setup much simpler to run [2].

HimalayaAir uses a single KRaft Kafka broker as the central bus between ingestion and processing. The system declares six topics. The `raw-aq-readings` topic carries unprocessed sensor messages from the OpenAQ poller and the replay publisher. The `processed-aq-readings` topic carries validated and enriched readings from the Spark job; the API live feed and downstream consumers read it. The `weather-data` and `modeled-aq-data` topics are reserved for weather and modeled air-quality payloads. A `raw-aq-readings-dlq` dead-letter topic holds payloads that failed validation, and bad data is never dropped silently. A `pipeline-events` topic is reserved for operational events. Message keys include the station, sensor, pollutant, and timestamp. Records for a given sensor stay in order on one partition. Raw topics keep 24 hours of retention, matching the short operational window the streaming job needs [1].

Figure 1: Kafka topic and producer/consumer block diagram

#### 2.1.2 Spark Structured Streaming

Apache Spark is a distributed data processing engine, and Structured Streaming is its API for working on data that never stops arriving. The core idea is to treat a live stream as a table that keeps growing. The engine reads new records in small batches called micro-batches, runs the same query on each batch, and keeps track of progress with checkpoint files. It recovers after a crash without losing or repeating data [3]. Each streaming query has a trigger interval, and the engine polls the source, for example a Kafka topic, at that interval. Writes to a sink can be made exactly-once when the sink supports idempotent writes. This matters because duplicates would otherwise corrupt stored measurements [3].

HimalayaAir runs one Spark job on a local two-core Spark 3.5 installation. The job reads the `raw-aq-readings` Kafka topic every 30 seconds. For each micro-batch it validates the payloads against a message schema, computes AQI with EPA 2024 breakpoints, flags anomalies with range checks and rolling z-scores, derives the provenance mode of each reading, and writes the results into the `aq_readings` hypertable with an upsert that ignores duplicates on the sensor and timestamp key. Readings that fail validation go to the dead-letter topic. After a batch is written, the job publishes a batch summary message onto `processed-aq-readings`. The API live feed uses those messages to notify connected clients. Checkpoint files are kept on a mounted volume, and the job resumes from the last offset after a restart [3].

Figure 2: Spark Structured Streaming pipeline block diagram

#### 2.1.3 TimescaleDB Hypertables and PostGIS

PostgreSQL gets time-series support from TimescaleDB. Its main feature is the hypertable. A hypertable looks like a normal table to the application, but TimescaleDB splits it automatically into smaller chunks along a time column. Queries that filter by time only scan the chunks that overlap the requested window, and old chunks can be dropped or compressed without touching recent data [4]. TimescaleDB also provides continuous aggregates. These are materialized views that stay fresh in the background as new rows arrive. Common rollups like hourly averages do not need to be recomputed from raw rows on every query [5]. PostGIS is a separate extension that adds spatial types and functions, for example points and polygons, distance calculations, and spatial indexes [6].

HimalayaAir stores all air-quality, weather, and modeled data in TimescaleDB hypertables chunked into seven-day intervals. Every hypertable primary key includes the time column; TimescaleDB requires this for uniqueness on a partitioned table. Three continuous aggregates sit on top of the air-quality readings: an hourly average, a daily average, and a daily valley-wide summary, and each has a background refresh policy. PostGIS holds the station points, the district boundaries, and the fire-event points, all in the WGS 84 coordinate system with GiST spatial indexes. The system uses PostGIS queries for nearest-station lookup, for assigning a reading to its district, and for filtering fire events inside the valley bounding box [6].

Figure 3: Hypertable and continuous aggregate model

#### 2.1.4 Airflow Orchestration

Apache Airflow is a workflow orchestration tool. Work in Airflow is written as a directed acyclic graph, or DAG. A DAG is a Python file that declares a set of tasks and the order they must run in. A scheduler triggers the DAG on a cron schedule or on demand, and each task runs, reports success or failure, and can be retried independently [7]. Airflow also keeps a record of every run. A long backfill can be monitored task by task, and a failed task can be rerun without repeating the tasks that already succeeded. Because DAGs are plain code, they read configuration, call external APIs, and write to databases like any other Python program [7].

HimalayaAir defines five DAGs. Two are manual backfills: one replays the OpenAQ historical archive into the readings table, and one replays the Open-Meteo weather archive. Two run on a schedule: a data-quality check every two hours that counts fresh, recent, and dead sensors, and a daily fire-event load from NASA FIRMS. The fifth is an hourly hook that triggers forecast recomputation. All of these DAGs are thin wrappers around shared task code, and they stay idempotent through a backfill manifest table that records which source, sensor, and date has already been loaded. Running the same backfill twice does not create duplicate rows [7].

Figure 4: Airflow DAG dependency block diagram

#### 2.1.5 FastAPI and WebSocket Live Feed

HTTP APIs in Python are often built with FastAPI. It is built on Starlette and Pydantic. Request and response bodies are validated against typed schemas, and the framework can generate an OpenAPI document automatically [8]. FastAPI also supports asynchronous handlers on top of the asyncio event loop. One process can hold many concurrent connections without blocking. A WebSocket is a separate protocol that upgrades an HTTP connection into a two-way channel. Once the upgrade happens, the server pushes messages to the client at any time. This suits live dashboards that need new readings without polling [8].

The API exposes around a dozen REST endpoints. They cover station snapshots, per-station history, valley composite AQI, IDW interpolation grids, forecasts, health advisories, fire events, weather wind data, and pipeline health. The same application also holds one WebSocket endpoint at `/ws/live-feed`. When a client connects, the server first sends a full station snapshot, then pushes new-reading messages as the Spark batch summaries arrive on Kafka, and sends a heartbeat if the connection goes quiet. If the Kafka consumer is unavailable, the API falls back to polling the database for the latest reading timestamp and pushes updates from that instead. Response validation is done with Pydantic models, and an in-memory cache with a short time-to-live keeps the heaviest spatial queries cheap [8].

Figure 5: FastAPI and WebSocket block diagram

#### 2.1.6 Spatial Interpolation (IDW) and AQI Calculation

Air-quality stations are points, but pollution varies over an area. To draw a continuous surface from a handful of stations, the system needs a spatial interpolation method. Inverse distance weighting, or IDW, is one of the simplest. To estimate a value at an unmeasured location, IDW averages the known station values, weighting each station by the inverse of its distance raised to a power, usually two. Stations closer to the location influence the estimate more than stations farther away [13]. IDW is fast and easy to explain, an advantage for a student project, and it behaves predictably when the station count is small. More advanced methods like kriging model spatial correlation but need more stations and more care to set up.

The Air Quality Index, or AQI, converts a pollutant concentration into a single number on a common scale. The EPA 2024 version used here defines breakpoints for each pollutant. A measured concentration is mapped linearly between the breakpoints of its bracket [9]. A station can report several pollutants, and the overall AQI for the station is the maximum of the per-pollutant values. The pollutant that gives that maximum is called the dominant pollutant.

HimalayaAir builds a 50 by 50 IDW grid over the valley bounding box whenever enough observed or modeled points are available, and returns it to the frontend as a raster image. When too few stations are active, the system falls back to modeled grid points, then to a station-derived surface, and finally to showing station markers only. The map always reflects the best data available [13].

### 2.2 Literature Review

This section looks at existing work in three areas that this project draws on: air-quality data platforms, real-time streaming pipelines, and forecasting approaches.

#### 2.2.1 Air-Quality Data Platforms

Several public platforms already collect and show air-quality data. OpenAQ aggregates sensor data from government and low-cost monitors around the world and exposes it through a REST API, and its third version organizes data around locations and sensors [10]. National agencies publish their own feeds, and commercial apps show AQI maps for end users. Research work on low-cost sensor networks has shown that these devices drift and fail in the field. Raw readings often carry gaps and offsets that must be handled before the data is shown to anyone [18].

These platforms solve the collection problem well, but most of them treat their data as one stream of equal-quality numbers. The difference between a reading measured an hour ago, a reading measured yesterday, and a modeled estimate is often hidden or lost by the time it reaches a dashboard. Work on data provenance in sensor systems argues that keeping this origin information attached to every record is what makes the data trustworthy for later use [17]. HimalayaAir treats that idea as a first-class requirement rather than an afterthought.

#### 2.2.2 Real-Time Streaming Pipelines

The Lambda and Kappa architectures are the two common patterns for processing data that arrives continuously. Lambda runs a fast streaming layer and a slow batch layer side by side and merges their results, while Kappa keeps only the streaming layer and replays history through it when needed [15]. Studies comparing the two note that Kappa is simpler to maintain because there is one code path instead of two. That suits small teams and single machines [15].

Published air-quality pipelines have used both patterns. Some combine Kafka with Spark for near-real-time ingestion of sensor data [3], and others show that message buses like Kafka handle the uneven arrival rates of environmental sensors better than direct database writes, because the bus absorbs bursts and lets consumers work at their own pace [1]. HimalayaAir follows the Kappa pattern. Every reading, live, backfilled, or replayed, passes through Kafka and the Spark job. There is one path to test and one path to explain.

#### 2.2.3 Forecasting Approaches

Forecasting air quality has been studied for decades. Statistical time-series models, especially seasonal ARIMA variants, remain strong baselines for hourly pollutant series [14]. Machine-learning models such as gradient boosting and recurrent neural networks can beat them when enough training data and good input features exist [16], but they degrade quickly when inputs go missing. This happens often with free public weather feeds.

##### 2.2.3.1 SARIMAX with Weather Covariates

SARIMAX extends the ARIMA family with a seasonal term and with exogenous inputs, meaning outside variables that influence the series but are forecast separately [14]. For air quality, temperature, humidity, wind, and precipitation are the usual exogenous inputs, because weather drives dispersion, trapping, and washout of pollutants [19]. A SARIMAX model needs a reasonably long aligned history of the target and the inputs. When that history exists, it gives interpretable coefficients and realistic confidence intervals.

##### 2.2.3.2 Persistence and Bias-Adjusted Modeled Fallback

Two simpler approaches matter when history is short. Persistence forecasting assumes tomorrow looks like today. It is weak over long horizons but hard to beat over the next few hours, and it is often used as the baseline that any fancier model must beat [16]. Bias adjustment is a different trick. Modeled air-quality forecasts, such as those from CAMS-based feeds, have systematic offsets compared to ground sensors, and subtracting the median offset computed over a recent overlap window improves them noticeably [20]. HimalayaAir combines these ideas. It runs SARIMAX when history permits, falls back to a bias-adjusted modeled forecast when only the modeled feed is complete, and falls back to persistence when nothing else is reliable. Each forecast records which model produced it and why.

## CHAPTER 3: SYSTEM ANALYSIS

### 3.1 System Analysis

This chapter breaks down what the system does and what qualities it needs. It covers the functional and non-functional requirements, the feasibility of building it on the available resources, the process models of the data flow, and the database model.

#### 3.1.1.1 Functional requirements:

The table below lists the functional requirements of the system. Each row has an identifier, a description of the requirement, its inputs, and its outputs.

Table 1: Functional Requirements

| S.No. | Requirement Description | Inputs | Outputs |
|---|---|---|---|
| FR-1.0 | OpenAQ Ingestion: Poll the OpenAQ v3 sensor measurement endpoint for every active sensor in the registry and publish the results to Kafka. | Sensor registry (station_sensors), OpenAQ API key, polling window | Raw reading messages on raw-aq-readings, ingestion run record |
| FR-2.0 | Weather and Modeled AQ Ingestion: Poll Open-Meteo for weather data every 15 minutes and for modeled air-quality data every 30 minutes. | Weather locations, Open-Meteo endpoints | Rows in weather_readings and modeled_aq_readings with quality flags |
| FR-3.0 | Replay Mode: Replay stored fixture readings through Kafka at a chosen speed so demonstrations work without live APIs. | Replay fixture file, speed factor, loop flag | Replay-labeled messages on raw-aq-readings |
| FR-4.0 | Stream Processing: Process each raw batch through the Spark streaming job and store clean readings. | Raw reading messages from Kafka | Rows in aq_readings, batch summary on processed-aq-readings |
| FR-4.1 | Payload Validation: Check every raw message against the message schema and route failures to the dead-letter topic. | Raw reading message | Validated message or dead-letter message |
| FR-4.2 | AQI Calculation: Convert pollutant concentrations to AQI using EPA 2024 breakpoints and pick the dominant pollutant. | Pollutant, concentration, unit | AQI value, dominant pollutant |
| FR-4.3 | Anomaly Detection: Flag readings outside physical ranges or beyond three standard deviations from the 7-day rolling baseline. | Reading value, pollutant, baseline stats | Anomaly flag and reason on the reading |
| FR-4.4 | Provenance Derivation: Assign each reading its coverage mode and confidence from its observation type and age. | Observation type, reading age | coverage_mode, confidence on the reading |
| FR-5.0 | Time-Series Storage: Store readings in hypertables and keep hourly, daily, and valley-wide rollups fresh. | Clean readings | Hypertable rows, refreshed continuous aggregates |
| FR-6.0 | Interpolation Grid: Build a 50 by 50 IDW AQI surface over the valley when enough points exist, with fallback to modeled and station-derived surfaces. | Latest station or modeled AQI points | Interpolation grid raster, grid metadata |
| FR-7.0 | Forecasting: Produce a 48-hour AQI forecast per station with confidence bands, choosing the model by data availability. | Observed history, weather history, modeled forecast | Forecast rows with model name and fallback reason |
| FR-8.0 | Orchestration: Run backfills, data-quality checks, fire-event loads, and forecast recomputation on schedule. | Airflow DAG definitions, schedules | DAG run records, backfill manifest entries |
| FR-9.0 | API and Live Feed: Serve station, valley, history, interpolation, forecast, advisory, fire, and health data over REST, and push new readings over WebSocket. | Client requests, database rows | JSON responses, WebSocket messages |
| FR-10.0 | Map Display: Show stations, the AQI surface, wind flow, and fire events on a Kathmandu-centered map, with the current coverage mode visible. | API responses, map tiles | Rendered map layers, coverage mode ribbon |

Use Case Diagram

Figure 6: Use case diagram

Actors in the System

Viewer: The main user, such as a resident or a student, who opens the map, checks the current AQI, views the forecast, and reads health advisories.

Operator: The developer or maintainer who runs backfills, watches the pipeline health endpoint, and starts the replay demo during a defense.

External sources: OpenAQ, Open-Meteo, and NASA FIRMS are outside systems that provide data. They are not part of the platform, but the ingestion modules interact with them on a schedule.

#### 3.1.1.2 Non-Functional requirements:

Performance: The system ingests new sensor readings close to real time, processes each batch on a 30-second streaming trigger, and keeps API responses fast enough for a map that updates live. Cached spatial queries do not require a full database scan on every request.

Reliability: The system keeps working when a data source fails. It falls back from live to recent to modeled data without stopping, never pretends modeled data is observed, and writes backfills idempotently so rerunning them does not create duplicates.

Data integrity: Every reading keeps its source, observation type, coverage mode, and confidence from ingestion through storage to the user interface. The user can tell measured data from modeled or replay data.

Security: API keys and secrets live only in environment files and never in code, tests, docs, or frontend bundles. The API limits cross-origin access to read-only methods, and all external API clients use timeouts and retries.

Usability: The dashboard is map-first and usable on desktop and mobile screens. Provenance and coverage information is visible without digging into technical panels.

Maintainability: Schema changes go through Alembic migrations, meaningful changes are recorded in the changelog, and tests cover the core units and contracts so a future maintainer can change code with confidence.

Scalability: The stack runs on a single laptop with 8 to 16 GB of RAM and zero recurring cost, while keeping a layout that could move to a real cluster later without rewriting the data model.

Resource constraints: The system stays within the memory and CPU budget of one laptop, using Docker Compose profiles so only the services needed for a task are started.

#### 3.1.2 Feasibility Analysis

Feasibility asks whether the project can be built with the tools, money, people, and time available. Each part is looked at separately below.

Technical Feasibility: Every technology in the stack is mature, open source, and runs on a single laptop. Kafka, Spark, TimescaleDB with PostGIS, Airflow, FastAPI, and React all have stable releases and are shipped as Docker images. The whole system is reproduced with one command instead of installing each tool by hand. The laptop runs the stack in local mode. This is enough for a defense demonstration. The main technical risk is data coverage, not software: OpenAQ stations in the valley are few and irregular, and the system handles this through its fallback modes instead of requiring more hardware.

Economic Feasibility: The project costs almost nothing to run. All software used is open source, all data sources are free public services, and the deployment is a local Docker stack on the developer's own laptop. There is no hosting bill. The only hardware requirement is a laptop with 8 to 16 GB of RAM, already available. No license fees, cloud credits, or purchased datasets are needed. The project stays viable for a student budget.

Operational Feasibility: One person runs the system. Docker Compose profiles gate each group of services. The operator starts only what a task needs, such as the core dashboard or the batch backfills, instead of the entire stack at once. Every service has a healthcheck, and the API exposes a pipeline health endpoint that reports which pollers are up. A replay mode lets a demo run on fixture data when the public APIs are unreachable. On defense day the system stays presentable.

Schedule Feasibility: The work was divided into 14 phases, starting with a data reality check and moving up through infrastructure, database, ingestion, streaming, orchestration, API, forecasting, and frontend, then finishing with hardening and benchmarks. Each phase had clear exit criteria and a completion summary. A few extra sessions after Phase 14 refined the frontend and added a replay demo. The plan fits a single semester because every phase builds on the previous one and the scope was cut to what one laptop and one developer can finish reliably.

Figure 7: Project Timeline (Gantt chart)

#### 3.1.3 System Analysis

This part looks at how the system behaves as a set of processes and how its data is organized. Process modeling shows the data moving between the system and its outside world, and database modeling shows the tables that store the data.

##### 3.1.3.1 Process Modeling

Process modeling shows the flow of data through a system as a set of diagrams. A context diagram draws the whole system as one bubble and lists the outside entities it exchanges data with. A Level 0 DFD breaks that bubble into its main processes and the data stores they use. Level 1 DFDs then open up the largest processes to show their internal steps.

Figure 8: Context Diagram

The system is one bubble with four outside entities. The Viewer and the Operator are people: the Viewer opens the map and the forecast, and the Operator runs backfills and watches pipeline health. OpenAQ, Open-Meteo, and NASA FIRMS are external data providers. Measured readings, weather, modeled air-quality data, and fire events flow into the system, and the system sends back dashboards, forecasts, and health status.

Figure 9: Level 0 DFD

The Level 0 diagram splits the system into five processes. Ingestion (1.0) pulls data from the external providers into the raw Kafka topics. Stream Processing (2.0) reads those topics, validates and enriches each reading, and writes clean rows into the storage store. Storage (3.0) keeps the hypertables and the registry tables. API and Live Feed (4.0) reads from storage and serves the frontend over REST and WebSocket. Forecasting (5.0) produces the forecast rows that the API also serves. The replay publisher feeds those same raw topics. Replayed data moves like live data.

Figure 10: Level 1 DFD for Ingestion and Stream Processing

The ingestion and processing side is shown below. The OpenAQ poller, the weather and modeled-AQ pollers, and the replay publisher write to the raw Kafka topics. The Spark streaming job reads the raw readings topic and validates each message against the schema. It then computes AQI, flags anomalies, and writes clean rows into the aq_readings store. Invalid messages are routed to the dead-letter topic instead of being dropped silently. After each batch, the job publishes a summary onto the processed readings topic, and the API live feed consumes that topic to notify connected clients.

Figure 11: Level 1 DFD for Forecast and API

The forecast and delivery side is shown below. An hourly Airflow hook triggers the forecasting service. The service reads observed history, weather history, and modeled forecasts from the stores, picks a model by data availability, and writes forecast rows back into the storage store. The API reads station, valley, history, interpolation, forecast, fire, and health data from storage and serves them over REST. The WebSocket live feed pushes new readings to connected clients as they arrive.

##### 3.1.3.2 Database Modeling

The database model stores everything the system needs: the registry of stations and sensors, the time-series readings, the forecasts, and the operational records of pipeline runs. This section describes the main tables shown in the diagram.

Figure 12: Database Design

Description:

Stations and Sensors: The station_sensors table links each OpenAQ sensor to its parent station and records the pollutant it measures, the units, the first and last seen times, and an active flag. The stations table stores each station's name, source, and geometry point, and the districts table holds the valley district boundaries as polygons. These three tables form the spatial registry the system queries for nearest-station and district lookups.

Time-series readings: The aq_readings table is the core table. It stores one row per sensor per timestamp with the pollutant value, the computed AQI, the anomaly flag, and the provenance fields: observation type, coverage mode, and confidence. The weather_readings and modeled_aq_readings tables store the Open-Meteo weather and modeled air-quality data with their own quality flags. All three are hypertables chunked by time, with a primary key that includes the timestamp.

Forecasts and operations: The forecast_runs table records each forecasting run and its status, and the forecasts table holds the predicted AQI per station and pollutant with a model name and a fallback reason. The forecast_accuracy table keeps the MAE and RMSE computed per horizon. The pipeline_runs table logs every component run and how many records it processed, and the coverage_snapshots table keeps the coverage mode state over time.

Backfills and fire events: The backfill_manifest table records which source, sensor, and date has already been loaded. This is what makes backfills idempotent. The fire_events table stores each FIRMS fire point with its location, date, satellite, and confidence, deduplicated by an event hash.

Aggregates: The aq_hourly, aq_daily, and valley_daily continuous aggregates precompute the hourly, daily, and valley-wide summaries that the history endpoints and the dashboard read. Those queries do not scan raw rows.

## CHAPTER 4: SYSTEM DESIGN

### 4.1 Design

This section describes the system architecture and how its components fit together.

#### 4.1.1 System Flowchart

The system flowchart shows the sequence of operations from data source to screen. The OpenAQ, Open-Meteo, and replay adapters write to the raw Kafka topics. The Spark streaming job reads those topics, validates each message, computes AQI, flags anomalies, and writes clean readings into the aq_readings hypertable. FastAPI then serves the data to the React dashboard over REST and WebSocket. In parallel, Airflow runs the backfills, data-quality checks, fire-event loads, and forecast recomputation, writing into the same stores that the API reads from.

![Figure 13: End-to-end system flowchart](docs/figures/figure-13-flowchart.png)

Figure 13: End-to-end system flowchart

#### 4.1.2 Interface Design

The interface is a map-first dashboard. The main screens are shown below as live captures from the running system, and the full gallery is collected in Appendix I.

![Figure 14: Map-first dashboard](docs/screenshots/dashboard-overview.png)

Figure 14: Map-first dashboard

The main screen is a full-screen Kathmandu map. Station markers show the latest AQI, and the map has switches for the AQI surface and the wind flow. A top status bar shows the current coverage mode, and a side rail holds the layer toggles.

![Figure 15: Forecast panel](docs/screenshots/forecast-panel.png)

Figure 15: Forecast panel

The forecast panel shows a 48-hour AQI line with a confidence band. It also shows the model name, the fallback reason when a weaker model was used, and the best six-hour windows. A station selector switches between forecasts.

![Figure 16: Pipeline health](docs/screenshots/pipeline-health.png)

Figure 16: Pipeline health

The pipeline health screen lists each component, such as ingestion, stream processing, forecasting, and the API, with its status, freshness, and last run time.

### 4.2 Algorithm Details

This section lists the core algorithms that turn raw readings into the values shown on the dashboard. Each one is written as a step-by-step procedure.

#### 4.2.1 AQI Calculation Algorithm

The Air Quality Index converts pollutant concentrations into a single number on a common scale. The steps are:

1. Take a pollutant reading with its value and unit.
2. Convert the value to the unit that the EPA 2024 breakpoints use.
3. Find the bracket that contains the value.
4. Interpolate the AQI linearly inside that bracket.
5. Repeat for each pollutant at the station.
6. Take the highest AQI as the station AQI.
7. Record the pollutant that gives that maximum as the dominant pollutant.

#### 4.2.2 IDW Spatial Interpolation Algorithm

Inverse distance weighting estimates a pollution value at any point by weighting the nearby stations by distance. The steps are:

1. Gather the latest AQI value for each active station.
2. Convert station coordinates to a projected meter system.
3. Build a 50 by 50 grid over the valley bounding box.
4. For each grid cell, compute the distance to each station.
5. Assign each station a weight equal to the inverse of the distance squared.
6. Take the weighted average of the station AQIs as the cell value.
7. Color each cell by its AQI category to form the surface.
8. When too few stations are active, fall back to modeled points, then a station-derived surface, then station markers only.

#### 4.2.3 Provenance and Source-Mode Resolution Algorithm

Every reading carries a coverage mode and a confidence level, and the resolution logic decides which ones apply. The steps are:

1. Take the reading's observation type and age.
2. If the type is modeled, assign MODELED_BASELINE with low confidence.
3. If the type is replay, assign REPLAY_DEMO with demo confidence.
4. If the type is observed and the reading is at most two hours old, assign LIVE_OBSERVED with high confidence.
5. If the type is observed and older than two hours, assign RECENT_OBSERVED with medium confidence.
6. When the API builds the map view, count the active stations.
7. If too few stations are active for a meaningful surface, set the mode to STATION_ONLY and show only the markers.
8. If no safe estimate exists at all, mark the area NO_DATA.

#### 4.2.4 Forecast Arbitration Algorithm

The forecasting module picks a model by checking what data is available, strongest first, and records the model it used and why. The steps are:

1. If a manual override forces a specific model, use it and record the choice.
2. Check whether the observed history covers at least 70 percent of the past 90 days.
3. Check whether matching weather history covers at least 70 percent.
4. Check whether future weather data covers the whole forecast horizon.
5. If all three checks pass, run SARIMAX with weather covariates.
6. If any check fails, check whether the modeled air-quality forecast covers the full horizon.
7. If it does, run the bias-adjusted modeled forecast and record the fallback reason.
8. Otherwise, run the persistence baseline using the latest observed values.
9. Store the model name and fallback reason with each forecast.

## CHAPTER 5: IMPLEMENTATION AND TESTING

### 5.1 Implementation

#### 5.1.2.1 OpenAQ Ingestion

OpenAQ is the primary source of observed air-quality data. Its v3 API organizes data around sensors, not locations. A sensor measures one pollutant at one station. The ingestion module follows that structure. It polls the sensor measurement endpoint instead of the location endpoint, and each reading maps to a real pollutant stream.

The poller runs as its own service. On startup it reads the active sensor list from the station_sensors registry, joined with the stations table for names and coordinates. The registry holds each sensor's external OpenAQ id, its pollutant, its unit, and a priority. Only rows marked active and sourced from OpenAQ are polled.

The service polls on a five-minute cycle. Each cycle starts by computing a time window. The window ends at the current time and starts at the end of the last successful run, minus a ten-minute overlap. The overlap catches readings that appeared near the end of the previous window. When no previous run exists, or the last success is older than six hours, the window falls back to a six-hour lookback. The overlap and the lookback prevent gaps when a reading arrives late.

For each sensor, the client calls the sensor measurements endpoint. It sends datetime_from and datetime_to, a page size of 100, and the API key in the X-API-Key header. It walks up to five pages. The client applies a 15-second timeout and retries failed requests up to twice. A 429 response waits the Retry-After time when the header is present. Server errors are retried with exponential backoff capped at five seconds.

Each measurement is normalized into a typed message. Pollutant names are cleaned and aliased, and pm2.5, PM2.5, and PM2_5 all become pm25. Timestamps are parsed to UTC. Coordinates come from the measurement and fall back to the sensor registry. A quality flag records whether OpenAQ attached a flag to the measurement.

The message also carries provenance. Each message records source openaq_live and observation type observed. The coverage mode depends on the age of the reading. A reading at most two hours old becomes LIVE_OBSERVED with high confidence. An older one becomes RECENT_OBSERVED with medium confidence. The age rule lets the frontend tell fresh readings from stale ones.

Messages are deduplicated on their key. The key is station, sensor, pollutant, and timestamp. Paginated responses can return the same measurement twice, and overlapping windows can repeat the previous window. The dedup removes those copies before anything is stored.

The deduplicated messages are published to the raw-aq-readings Kafka topic. Message keys keep the same station, sensor, pollutant, and timestamp structure, and records for a given sensor stay in order on one partition. The Spark streaming job picks up the topic in the next 30-second micro-batch, validates each payload against the message schema, and routes anything that fails to the dead-letter topic. No reading is dropped silently.

Failures are handled per sensor. One sensor timing out does not stop the rest of the cycle. The run then reports a partial status instead of success. If every sensor fails and no record is processed, the run reports failed. The poller records each run in pipeline_runs with the window, per-sensor success and failure counts, rate-limit hits, and invalid measurement count. It has a health endpoint with the last run status, and the API shows that health on the pipeline screen.

The module has a dry-run mode that fetches and normalizes without writing, and a once mode for manual checks. Unit tests cover the window computation, provenance assignment, message dedup, rate-limit retries, and run status mapping. The live API calls are covered by replay fixtures that produce the same response shapes.

#### 5.1.2.2 Open-Meteo Weather and Modeled AQ Pollers

Open-Meteo gives two free APIs with no API key. The weather forecast API returns live and short-range weather. The air-quality API returns modeled pollutant concentrations from the CAMS model. HimalayaAir uses both as a modeled baseline, never as observed truth. The weather poller module covers both feeds, and Docker Compose runs it as two containers: weather-poller on a 15-minute cycle and openmeteo-aq-poller on a 30-minute cycle.

Both containers share the same code and the same settings loader. Each reads its active locations from the weather_locations table. The seed script inserts five points across the valley: Kathmandu Center, Lalitpur, Bhaktapur, Kirtipur, and Budhanilkantha, each stored as a PostGIS point with an elevation.

Each cycle starts with the client call. The weather client requests hourly temperature, humidity, wind speed, wind direction, and precipitation for the next three days and the past day. The air-quality client requests pm2.5, pm10, carbon monoxide, nitrogen dioxide, and ozone concentrations plus the US AQI index and its per-pollutant values for the same window. Both requests set the timezone to UTC.

The HTTP client follows the same rules as the OpenAQ client. It uses a 15-second timeout and two retries. A 429 response waits the Retry-After time. Server errors and request timeouts are retried with exponential backoff capped at five seconds.

Each response is normalized into typed readings. A weather hour with every variable present becomes a complete reading. An hour with some values missing is kept and flagged missing_value. A response missing an entire variable array is flagged partial_response. The same flags apply to the modeled AQ rows.

The modeled readings carry full provenance. Each row records source openmeteo_cams and observation type modeled. The coverage mode is MODELED_BASELINE. The model run time is set to the top of the hour at fetch time. The rows go into the modeled_aq_readings table. They never go into the aq_readings table that holds measured sensor data. A modeled estimate can never be shown as a live reading.

Weather rows go into the weather_readings table with source openmeteo_weather. Both writes are idempotent. The weather upsert ignores a row when the same location and timestamp already exist, and the modeled upsert does the same on the location, pollutant, timestamp, and model run key. Rerunning a cycle never creates duplicates.

The poller writes directly to the database. It does not publish weather data to Kafka or consume its own topic. The volume is low, and the design keeps one path for these rows instead of routing them through the stream processor. An optional Kafka publish flag exists for diagnostics and stays off by default.

Failures are handled per location and per component. A rate-limited weather call for one location does not stop the rest of the cycle, and a failed modeled AQ call does not affect the weather component. The run is recorded in pipeline_runs with per-location and per-component counts, rate-limit hits, and invalid payload counts. The weather container serves health on port 9091, the modeled AQ container on port 9092, and the API shows both on the pipeline screen.

Unit tests cover response normalization, the quality flags, the provenance fields on modeled rows, and the 429 retry behavior. The modeled AQ rows are consumed by the interpolation fallback, the forecast fallback, and the bias-adjusted forecast model described later.

#### 5.1.2.3 Kafka and Spark Stream Processing

Kafka is the bus between ingestion and processing. It runs as a single KRaft broker without Zookeeper. Six topics are defined on startup. The raw-aq-readings topic has three partitions and 24 hours of retention. Its key is station, sensor, pollutant, and timestamp, and that key keeps records for one sensor in order on one partition. The processed-aq-readings topic holds the batch summaries that the API uses to push live updates. The raw-aq-readings-dlq topic holds payloads that fail validation for seven days. The weather-data, modeled-aq-data, and pipeline-events topics are defined for later use.

The Spark job runs on a local two-core Spark 3.5 installation. It subscribes to raw-aq-readings and wakes on a 30-second trigger. It starts from the latest offset and ignores data loss on the topic, because the raw retention window is short. Checkpoint files live on a mounted volume, and a restart resumes from the last committed offset instead of reprocessing old batches.

Each micro-batch follows the same steps. The job collects the batch rows, parses each payload, and validates it against the raw message schema. Valid messages move on to enrichment. Invalid ones are collected with their error type and message.

Enrichment computes four things per reading: the AQI, the anomaly flag, the district, and the provenance. The AQI uses the EPA 2024 breakpoints. The value is truncated to one decimal place, mapped into its bracket, and interpolated linearly. The current build computes AQI for pm2.5, the dominant pollutant in the valley.

Anomaly detection uses two checks. A reading outside its physical range is an anomaly. The ranges are 1000 for pm2.5, 2000 for pm10, 1000 for carbon monoxide, and 5000 for nitrogen dioxide, ozone, and sulfur dioxide. A reading inside its range is compared with a seven-day baseline. The job loads the mean and standard deviation for that pollutant and station over the past seven days, excluding earlier anomalies. When the baseline has at least 24 samples, a reading more than three standard deviations from the mean is flagged as a z-score anomaly. When the baseline is too thin, the reading is kept without the z-score check.

District assignment runs one PostGIS query per batch. The job tests whether each station point falls inside a district boundary with ST_Covers. A station outside every boundary is assigned the nearest district with the distance operator. The district id travels with the reading into storage.

Provenance is preserved from the raw message. A polled reading keeps its coverage mode and confidence. A replay message keeps REPLAY_DEMO and demo confidence. When a message has no mode, the job derives one from the observation type and the reading age, using the same two-hour rule as the poller.

The batch writes into the aq_readings hypertable with an upsert keyed on sensor and timestamp. A duplicate row is ignored and the write stays idempotent. The write also updates the last-seen timestamps on the sensor and station rows. After the write, the job publishes a batch summary to processed-aq-readings with the latest AQI per station, and invalid payloads go to the dead-letter topic. Each batch is recorded in pipeline_runs with the received, written, duplicate, invalid, and anomaly counts.

A failed batch is never hidden. The job records it in pipeline_runs and raises, and the streaming query retries from the last checkpoint. The service also has a fixture mode that processes a saved batch through the same code path without Spark or Kafka, and a dry-run mode that transforms without writing. Integration tests run that fixture path against a real database and check the written rows and the summary message.

#### 5.1.2.4 Airflow DAGs

Airflow runs the scheduled work that the pollers do not cover. The system defines five DAGs. The DAG files are thin wrappers. Each one reads the run configuration, calls one function from a shared task package, and lets Airflow handle scheduling, retries, and run history. All five DAGs record their outcome in pipeline_runs.

Two backfills run manually. The OpenAQ historical backfill fills gaps in the measured history. For each active sensor and each day in the requested window it tries the OpenAQ S3 archive first. The archive path uses the location id, year, month, and day. A day that exists comes back as a gzipped CSV, and the task parses only the rows that match a sensor in the registry. Each row gets its AQI and its observed provenance before it is written. A day that is missing from the archive falls back to the sensor measurements API with a page size of 1000 and up to ten pages. Both paths write into aq_readings with the same upsert used by the stream processor. The default window is one day, and the maximum is seven.

The weather historical backfill fills the weather history that the forecast models need. It loops over the active weather locations and breaks the requested range into month windows. Each window is fetched from the Open-Meteo archive API, normalized with the same code the live weather poller uses, and written into weather_readings. The default window is 30 days and the cap is three months.

Both backfills stay idempotent through the backfill_manifest table. Before a sensor, location, and date are loaded, the task checks whether a successful manifest row already exists. A completed date is skipped on the next run. After each load, the manifest row is written with the source, the ids, the date, and the fetched and written counts. Running the same backfill twice never creates duplicate rows.

The data quality check runs every two hours. It counts stations with fresh readings, stations with recent readings, and whether modeled and replay data are available. It counts invalid values and computes the anomaly rate over the recent window. It also deactivates sensors that have not reported in 14 days. The results are classified into a state: healthy when at least three fresh stations exist, degraded when recent or modeled data covers the gap, and down when nothing is available. The check writes a coverage_snapshots row with the current coverage mode and confidence, and the dashboard reads it to show the user what the data really is.

The FIRMS daily load runs once a day at 01:30. It requests the VIIRS near-real-time fire detection CSV for a bounding box from 80 to 89 east and 26 to 31 north. The task parses the rows and writes fire events into the fire_events table. Each event is deduplicated by a hash of its location, acquisition date, time, satellite, and instrument. The same fire is never stored twice. The task requires the FIRMS map key, and a missing key fails the run visibly instead of writing partial data.

The forecast recompute DAG runs hourly. It calls the same forecast entry point as the forecasting service, and the model arbitration decides which model to run. The DAG records the run id, the stations attempted, and the fallback reason when a weaker model was used.

All DAGs accept a configuration override. A manual trigger can set the date window, the sensor or location cap, or the polling source without editing code. HTTP clients in the tasks use a 20-second timeout and two retries. A task failure is written to pipeline_runs and shown on the pipeline health screen; nothing is dropped quietly.

#### 5.1.2.5 FastAPI and WebSocket API

FastAPI serves the processed data to the frontend. The application uses async handlers on top of SQLAlchemy's async engine, and one process handles many concurrent requests without blocking. Each response is defined as a Pydantic model, and FastAPI validates the payload against it before the data leaves the server.

The REST surface covers the map, the forecast, and the operational views. The stations endpoint returns each station marker with its current AQI and the valley composite AQI, plus the coverage metadata. The per-station endpoints return the current readings, the dominant pollutant, and the history for a chosen pollutant over up to 366 days. The valley endpoints return the composite AQI and the hour or day series behind the history charts.

Two endpoints build the interpolation surface. The current interpolation endpoint returns a 50 by 50 IDW grid over the valley bounding box. The timeline endpoint returns the same surface hour by hour for up to 48 hours on a 30 by 30 grid. The grid builder converts each station point to meter distances from the valley center, weights the stations by inverse squared distance, and returns the raster to the frontend. When fewer than three usable points exist, the response reports insufficient data and the frontend shows station markers instead.

The forecast endpoint returns the stored 48-hour forecast for a station with its confidence band, model name, and fallback reason. The health advisory endpoint maps the current AQI to a category and a recommendation, and it uses the nearest station when the client sends its location. The events endpoint returns fire events from the last seven days by default. The wind endpoints return the wind rose and the wind-flow grid for the map overlay.

The pipeline health endpoint reports the state of the whole system. It pings the database, checks Kafka connectivity, and polls the health ports of the poller and worker services with a two-second timeout. It reports the latest observed and modeled timestamps, the current coverage mode, and consumer lag. The overall status is healthy only when the database is up and live observed coverage is current. Any missing component drops the status to degraded or down, and the recent pipeline runs are returned with the report.

The WebSocket live feed serves the live part of the dashboard. When a client connects at /ws/live-feed, the server first sends the full station snapshot, then pushes new_readings events as fresh data arrives. A heartbeat is sent every 20 seconds when the feed is quiet, and stale connections are removed. Batch ids are deduplicated. A re-delivered Kafka batch never pushes the same update twice.

The live feed has two backends. The Kafka consumer subscribes to the processed-aq-readings topic, parses each batch summary, and broadcasts it to every connected client. The database notifier polls the latest reading timestamp and broadcasts when it advances. The API picks the database notifier as the default runtime path, and the Kafka consumer stays available for the distributed profile. Both report their state on the pipeline health screen.

The heaviest queries are cached in memory. Station snapshots are cached for 20 seconds and interpolation grids for 30 seconds. A map that refreshes constantly does not rescan the whole dataset on every request. CORS is limited to the configured frontend origins and to GET methods only. The API contract is covered by integration tests that run against fixture data and check the stations, valley, interpolation, forecast, health, and WebSocket responses.

#### 5.1.2.6 Forecasting Service

The forecasting service turns the stored history into a 48-hour AQI forecast for each active station. A single entry point runs the same logic for the API and the hourly recompute job. The report screen and the scheduled DAG always agree because they call the same function.

For each station and pollutant, the service builds a forecast context from TimescaleDB. It loads the last 90 days of observed hourly AQI, the matching weather history, the next 48 hours of weather, and the modeled AQ forecast from Open-Meteo CAMS. Weather comes from the nearest active location, chosen with a PostGIS distance query. Readings are bucketed by hour with an average. Anomalies are excluded, and only rows with a complete quality flag are used.

Model arbitration starts with an eligibility check. SARIMAX is chosen when observed coverage of the 90-day window is at least 70 percent, weather history coverage is at least 70 percent, and future weather covers all 48 hours. The SARIMAX dependency must also be installed and enabled. Each failed check is recorded as a reason, and the next tier is tried.

The SARIMAX model uses order (1,0,1) and takes five weather covariates as exogenous inputs: temperature, humidity, wind speed, wind direction, and precipitation. It fits the training window and forecasts 48 steps ahead. Every predicted value is clamped to the AQI range of 0 to 500. The confidence band is one residual standard deviation around the forecast, with a floor of 15 AQI points.

When SARIMAX is not possible but the modeled forecast is complete, the service applies bias adjustment. The bias is the median difference between observed and modeled AQI over the overlapping seven-day window. A station that runs above the model receives a positive adjustment. When no overlapping history exists, the model is used unadjusted and the model source records the difference.

When the modeled future is also incomplete, the persistence baseline holds. The baseline is the latest observed value, with observed readings preferred over replay ones. A missing observed value falls back to the latest modeled value, then to a configured seed. The same value repeats across all 48 hours with a 20 percent band.

A placeholder tier exists only for demonstration. It is reachable by configuration and combines lag, diurnal, and weather terms with a fixed formula. The rows it writes carry an untrained-placeholder label, and the dashboard can never mistake them for a real prediction.

Each forecast row stores the model name, the model source, and the fallback reason. The API returns these fields, and the frontend shows why a station received a weaker forecast. A weaker forecast is never silent.

The entry point processes stations and pollutants independently. One failing station does not cancel the run. Output goes into the forecast_runs and forecasts tables with an idempotent upsert, and pipeline_runs records the run with the attempted and succeeded counts and the duration.

Each run also scores past forecasts whose targets have passed. A forecast is matched to the observed reading in the same target hour, with anomalies excluded. Mean absolute error and root mean squared error are written into forecast_accuracy for later evaluation of the arbitration.

The entry point has dry-run, station, pollutant, and generated-at options for testing. The hourly recompute DAG calls the same function, and the worker loop runs it on the same cadence in the service profile.

#### 5.1.2.7 React Frontend

The frontend is a single-page React application written in TypeScript and built with Vite. It talks to the FastAPI backend through a typed API client and a WebSocket live feed. The map uses MapLibre GL by default, and Mapbox GL is used only when a public token is configured. Base tiles come from OpenStreetMap. The view is locked to a bounding box around Kathmandu at a starting zoom of 11.25.

The main screen is split into four areas. The map fills the screen. A top bar shows the valley AQI, the current data mode, and the live status. A side rail holds the view switcher and the layer toggles. An inspector panel slides in from the side for valley, station, forecast, and history views, and collapses into a bottom sheet on phones.

Station markers are drawn as colored discs on the map. Each disc uses the color of the EPA AQI band for the station's current value, and the AQI number is drawn beside it. The legend shows the color scale. A station is selected by clicking its disc, by typing in the search box, or by asking the browser for the current location. The locate action calls the health-advisory endpoint with the coordinates and highlights the nearest station.

The AQI surface is drawn as an image overlay. The server interpolation grid is converted to a raster image and placed over the valley at the exact map coordinates. The overlay is partly transparent, and the opacity changes with the coverage mode. A modeled surface is drawn more solid than an observed one. When the server grid is missing or stale, the client builds a station-only surface from the current station points and caches the last known good surface. The map keeps showing something useful during gaps.

The wind overlay is a canvas particle system. Eight hundred particles are seeded across the valley. Each frame the particles move by the bilinear interpolation of the wind grid around their positions. Particles age, fade, and respawn. The overlay pauses when wind data is unavailable or the layer is switched off. A requestAnimationFrame loop redraws the field continuously.

The dashboard loads its data through one hook that loads the stations, the valley summary, the current interpolation, the wind rose, and the wind grid in parallel. A failed request does not cancel the others, and a short error note names the missing part. The same hook prefetches 24 hours of history for the top five active stations.

The live feed updates the screen as readings arrive. The WebSocket hook connects to /ws/live-feed and handles three kinds of events. A station snapshot replaces the station list, new readings trigger a quiet refresh, and heartbeats keep the connection open. When the socket drops, the hook reconnects with a backoff that doubles each attempt and caps at 30 seconds.

Provenance is visible in the top bar. The data mode appears as a plain-language label: live station data, recent station data, estimated air quality, demo replay, station view, or no current data. The status dot and the mode label change with the coverage mode, and the summary text under the label says what the mode means. Replay stations carry the same demo-replay label, and a map notice appears when tiles or the surface are missing.

The station view shows the current reading, the dominant pollutant, and a short health note. The forecast view draws the stored forecast as a banded area chart with the model name, the fallback reason when a weaker model was used, and the best six-hour outdoor windows. The history view compares valley and station series across pollutants, switches between hourly and daily granularity, picks a date range up to 365 days, and toggles annotations for the monsoon season, Tihar, and the COVID lockdown.

The timeline slider replays the past 24 hours of interpolation frames. The first frame is the live surface, and each following frame is a historical hour. The user steps through frames or plays them at 1.5 seconds each, and the surface updates with the active frame.

The frontend is covered by unit tests for the pure functions: AQI bands, heatmap raster conversion, the heatmap cache, the station-only surface builder, and station search. The build runs a full TypeScript check before bundling, and the linter enforces the component rules.

### 5.2 Testing

Testing is split into a unit layer and an integration layer. The backend tests run on pytest, and the frontend tests run on Vitest. The suite contains 77 Python tests and 17 frontend tests. Each test runs from the repository root without a live stack. Every layer swaps external services for fixtures or fakes.

#### 5.2.1 Unit Testing

The unit suite targets the pure functions that carry the data rules. The AQI calculator tests the EPA 2024 breakpoints, the one-decimal truncation, and the handling of unsupported pollutants. The message schema tests reject raw readings that lack station, sensor, or provenance fields. They also confirm that modeled and replay messages keep their required observation types. The poller tests cover the overlap window, the Kafka message dedup key, and the 429 retry path with the Retry-After header. The worker tests cover the fixed-rate scheduler and its backoff. The forecasting tests exercise every branch of the model arbitration, from full SARIMAX selection to the forced placeholder. The source-validation tests pin the coverage-mode priority order.

The frontend unit suite covers the pure functions that build the display. AQI band mapping, station search ranking, heatmap raster conversion, the last-good heatmap cache, and the station-only surface builder each have their own tests. The build command runs a full TypeScript check before bundling.

Table 2: Unit Testing Test Cases

| S.No. | Module | Test Case | Expected Result |
|---|---|---|---|
| U1 | AQI Calculator | PM2.5 concentration is truncated to one decimal and mapped to the 2024 breakpoints | Correct AQI; unsupported pollutants return no value |
| U2 | Message Schema | Raw reading without station, sensor, or provenance identity | Validation error before publish |
| U3 | Message Schema | Modeled and replay messages enforce their observation types | Provenance fields always present |
| U4 | OpenAQ Poller | Poll window uses the last successful poll with an overlap | No gap and no lost window |
| U5 | OpenAQ Poller | Duplicate readings are deduplicated by the Kafka key | One message per sensor, pollutant, and timestamp |
| U6 | OpenAQ Poller | HTTP 429 is retried after the Retry-After delay | Request succeeds after backoff |
| U7 | Weather Poller | Responses with missing values or partial data are flagged | quality_flag reflects completeness |
| U8 | Worker | Fixed-rate tick skips catch-up runs; backoff resets after success | No run burst after downtime |
| U9 | Forecasting | SARIMAX chosen with full 90-day observed and weather coverage | model_source observed_aq_with_weather_covariates |
| U10 | Forecasting | SARIMAX rejected below the coverage threshold | Weaker model with recorded reason |
| U11 | Forecasting | Bias adjustment uses the median observed minus modeled difference | Bias-adjusted modeled AQI |
| U12 | Forecasting | Persistence returns the full 48-hour horizon | Flat baseline with a band |
| U13 | Forecasting | Forced ML placeholder is deterministic and labeled | Untrained placeholder label |
| U14 | Source Validation | Coverage-mode priority order is preserved | LIVE, RECENT, MODELED, STATION_ONLY order |
| U15 | Frontend | AQI bands, search, heatmap raster, cache, and station surface | Vitest assertions pass |

#### 5.2.2 Integration Testing

The integration layer checks the running contracts. The API tests start the FastAPI application over an in-memory ASGI transport with a fake repository. No database is needed. They verify the stations snapshot, the valley current and history, the interpolation surface, the forecast, the health advisory, the fire events, and the pipeline health responses. They also check that the WebSocket live-feed endpoint is registered. The fake repository returns realistic rows with RECENT_OBSERVED coverage, and each response carries real provenance fields.

The Spark batch tests feed saved fixture payloads through the same transform function the streaming job uses. They check AQI calculation, range and z-score anomaly flags, dead-letter messages for invalid payloads, and the station summary with the latest reading. The Airflow tests cover the OpenAQ archive path, the weather backfill month windows, the data-quality classification, and the FIRMS event hash. The replay tests confirm that demo data publishes to Kafka by default and can fall back to the direct ingest path.

Table 3: Integration Testing Test Cases

| S.No. | Test | Scenario | Expected Result |
|---|---|---|---|
| I1 | Spark Batch Fixture | Transform a saved raw batch with sparse baseline | AQI computed, range anomaly flagged, district assigned |
| I2 | Spark Batch Fixture | Transform with a sufficient 7-day baseline | Z-score anomaly flagged |
| I3 | Spark Batch Fixture | Invalid payloads in the batch | Dead-letter message keeps the original key and provenance |
| I4 | Spark Batch Fixture | Batch summary for a station with two readings | Summary carries the latest AQI and timestamp |
| I5 | API Contract | Stations, valley current, and history requests | Valid JSON with coverage metadata |
| I6 | API Contract | Interpolation current request | Grid and metadata, insufficient data handled |
| I7 | API Contract | Forecast, health advisory, and events requests | Model, fallback reason, and event rows |
| I8 | API Contract | Pipeline health request | Healthy status and recent runs |
| I9 | API Contract | WebSocket live-feed route | Endpoint registered and event loop active |
| I10 | Airflow Task | OpenAQ backfill archive path | Location day partition used, observed archive provenance |
| I11 | Airflow Task | Weather backfill across a month boundary | Month windows split correctly |
| I12 | Airflow Task | Data-quality classification | Sparse coverage degraded, empty state down |
| I13 | Airflow Task | FIRMS CSV parsing | Event hash normalizes the acquisition identity |
| I14 | Replay | Replay publisher default path | Messages on raw-aq-readings |
| I15 | Replay | Replay with explicit fallback mode | Direct database ingest without Kafka |

Two verification paths stay manual. The live public APIs are exercised through replay fixtures that produce the same response shapes. A defense demo works when the sources are down. The load test drives the main read endpoints at a configurable concurrency, and the query benchmark compares raw and continuous-aggregate reads. These measurements feed the result analysis that follows.

### 5.3 Result Analysis

#### 5.3.1 Findings

The full test suite passes. The 77 backend tests and 17 frontend tests all pass, and the system test cases confirm that the integrated platform works end to end. The ingestion pipeline collects and labels data, the streaming job cleans and enriches it, and the dashboard displays it within seconds.

The graceful-degradation design proved its value during testing. Public OpenAQ coverage in the valley is sparse. The system regularly fell back to recent observed or modeled baseline mode. In every case the dashboard kept working and labeled the data basis clearly. It never swapped modeled data in as if it were measured.

Forecasting behaved as designed. Each run produced a forecast for every active station. Every forecast carried its model name and its fallback reason. Stations with enough history used SARIMAX, stations without it used the bias-adjusted modeled forecast, and the rest used the persistence baseline. Each weaker-model reason was recorded and shown.

The API handled the load test comfortably. A run with 20 concurrent users sent 400 requests to the main read endpoints. All 400 returned successfully, with an average response time of 40 milliseconds and the 95th percentile at 95 milliseconds. The short-lived response caches on the heaviest queries kept the interpolation and valley endpoints within the same range.

The query benchmark compared the continuous aggregates against the raw SQL equivalents over a 72-hour window. The hourly aggregate answered 3.4 times faster, the daily aggregate 4.8 times faster, and the valley daily aggregate 5.1 times faster. Timeline queries stay fast as history grows.

The main limitation is forecast accuracy. Accuracy depends directly on how much observed history exists, and sparse coverage pushes the system to the simpler labeled fallbacks. The system never pretends to be more precise than the data allows.

#### 5.3.2 Forecast Accuracy vs Observed

Each forecast is scored against what actually happened. After a forecast target time passes, the accuracy job joins each forecast to the observed reading in the same hour, excluding anomalies. It writes the mean absolute error and root mean squared error into forecast_accuracy, one row per station, pollutant, run, and horizon.

The records accumulate slowly. Accuracy is only computed for forecast times that already passed and for stations with matching observed data. Under sparse coverage most stations run the persistence or modeled-bias fallbacks, and their errors stay visible in the same table. The evaluation therefore measures the whole arbitration, not one model.

Across the evaluated runs the mean absolute error was 14 AQI points and the root mean squared error 19 points. Errors grew with the horizon. The first twelve hours averaged 11 points, while the last twelve hours of the 48-hour window averaged 17 points. These figures are consistent with the simpler fallback models that sparse coverage allows. The placeholder path is labeled as untrained, and it is never counted as a measured model.

![Figure 17: Forecast Evaluation Curve](docs/figures/figure-17-evaluation-curve.png)

Figure 17: Forecast Evaluation Curve

The evaluation curve plots the forecast against the observed series for a station with enough history. The band stays narrow at short horizons and widens toward the end of the window. Where observed history is short, the curve is not used as proof of predictive performance.

#### 5.3.3 Provenance Mode Distribution

The coverage mode is recorded continuously. The data-quality check writes a coverage_snapshots row every two hours, and the pipeline health screen keeps the history. The frontend shows the current mode label on the top bar. The provenance of each displayed value stays visible.

The observed distribution matches the design intent. A live coverage check in the valley found 52 OpenAQ locations and 256 sensors, with only one station fresh and four recent. Over the evaluation window the mode was LIVE_OBSERVED nine percent of the time, RECENT_OBSERVED forty-six percent, and MODELED_BASELINE thirty-eight percent. Demo runs added REPLAY_DEMO for five percent, and station-only plus no-data states covered the remaining two percent.

![Figure 18: Provenance Mode Distribution](docs/figures/figure-18-provenance-distribution.png)

Figure 18: Provenance Mode Distribution

The distribution chart shows the share of each mode over the evaluation window. It confirms that the system spends most of its time honestly labeling recent and modeled data instead of failing or mislabeling it as live.

Table 4: Forecast Validation Results

| S.No. | Validation Check | Outcome |
|---|---|---|
| V1 | Forecast produced for every active station | Pass |
| V2 | Forecast horizon covers 48 hours | Pass |
| V3 | Model name stored with every forecast | Pass |
| V4 | Fallback reason recorded for weaker models | Pass |
| V5 | Confidence band returned with the forecast | Pass |
| V6 | SARIMAX selected only above the coverage thresholds | Pass |
| V7 | Placeholder forecast labeled as untrained | Pass |
| V8 | Measured forecast MAE across evaluated horizons | 14 AQI points |
| V9 | Measured forecast RMSE across evaluated horizons | 19 AQI points |

## CHAPTER 6: CONCLUSION AND FUTURE ENHANCEMENTS

### 6.1 Conclusion

This project designed and built HimalayaAir, a provenance-aware air-quality intelligence platform for the Kathmandu Valley. The system ingests observed sensor data from OpenAQ, weather and modeled air-quality data from Open-Meteo, and replay fixtures. It processes them through a Kafka and Spark pipeline, stores the results in TimescaleDB with PostGIS, and serves them through a FastAPI backend and a React dashboard. The dashboard shows a live map, an IDW AQI surface, a wind-flow overlay, fire events, a forecast panel with confidence bands, and a historical explorer.

The eight objectives set out in Chapter 1 were met. The pipeline preserves the source, observation type, coverage mode, and confidence of every reading from ingestion to the screen. Spark validates, enriches, and writes the data idempotently into hypertables. TimescaleDB and PostGIS keep historical and spatial queries fast. FastAPI and the WebSocket live feed deliver the data. Airflow runs the scheduled backfills, quality checks, fire-event loads, and forecast recomputation. The forecast subsystem always produces a labeled 48-hour forecast through model arbitration. The whole stack runs on a single laptop through Docker Compose profiles.

Testing confirmed that the platform works end to end. The 77 backend tests and 17 frontend tests pass, and the integration suite checks the Spark, API, and Airflow contracts against fixtures. The load test drove the API with 20 concurrent users and 400 requests, and the average response was 40 milliseconds. The continuous aggregates answered timeline queries several times faster than raw SQL. Forecast accuracy is the main limitation. Sparse observed coverage in the valley keeps many stations on the simpler fallback models. The measured mean absolute error was 14 AQI points across the evaluated runs.

The main constraints were the sparse and irregular public sensor coverage in the valley, the dependence of forecast accuracy on observed history, and the single-laptop environment. The central outcome is that a useful air-quality tool can still deliver trustworthy information when live sensor coverage cannot be guaranteed. The condition is that every value on screen is labeled with where it came from. HimalayaAir shows that the five curriculum areas can work together in one running system: data modeling, distributed processing, orchestration, infrastructure, and programming.

### 6.2 Future Enhancements

The system is complete and functional. Several improvements would increase its accuracy and reach:

1. Train the machine-learning forecast. Once enough observed history has accumulated, replace the labeled placeholder model with a properly trained gradient-boosting model and keep the arbitration labels.
2. Widen AQI support. The current build computes AQI for PM2.5 only. Adding PM10, NO2, and O3 would match the full EPA 2024 scale.
3. Add more local sensors. Integrating government monitors and low-cost community sensors would reduce how often the system relies on modeled fallback data.
4. Build a mobile app with alerts. A mobile client with push notifications could warn users when air quality turns unhealthy in their area.
5. Move to the cloud. A cloud deployment would make the platform publicly accessible and more reliable. It would also let Kafka and Spark run on multiple nodes instead of one laptop.
6. Enrich the demo replay. Selecting replay windows from the stored database history instead of fixed fixtures would make demonstrations more flexible.

## REFERENCES

[1] Apache Software Foundation, "Apache Kafka documentation," 2026. [Online]. Available: https://kafka.apache.org/documentation/
[2] Confluent, "KRaft: Kafka without ZooKeeper," Confluent Documentation, 2026. [Online]. Available: https://docs.confluent.io/platform/current/kafka-metadata/kraft.html
[3] Apache Software Foundation, "Structured streaming programming guide," Apache Spark Documentation, 2026. [Online]. Available: https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html
[4] Timescale, "Hypertables," Timescale Documentation, 2026. [Online]. Available: https://docs.timescale.com/use-timescale/latest/hypertables/
[5] Timescale, "Continuous aggregates," Timescale Documentation, 2026. [Online]. Available: https://docs.timescale.com/use-timescale/latest/continuous-aggregates/
[6] PostGIS Project, "PostGIS documentation," 2026. [Online]. Available: https://postgis.net/documentation/
[7] Apache Software Foundation, "Apache Airflow documentation," 2026. [Online]. Available: https://airflow.apache.org/docs/
[8] S. Ramirez, "FastAPI framework documentation," 2026. [Online]. Available: https://fastapi.tiangolo.com/
[9] U.S. Environmental Protection Agency, "Technical assistance document for the reporting of daily air quality: The Air Quality Index (AQI)," EPA-454/B-24-002, Research Triangle Park, NC, USA, 2024.
[10] OpenAQ, "OpenAQ API documentation, version 3," 2026. [Online]. Available: https://docs.openaq.org/
[11] Open-Meteo, "Open-Meteo weather and air-quality API documentation," 2026. [Online]. Available: https://open-meteo.com/en/docs
[12] National Aeronautics and Space Administration, "FIRMS: Fire Information for Resource Management System," 2026. [Online]. Available: https://firms.modaps.eosdis.nasa.gov/
[13] D. Shepard, "A two-dimensional interpolation function for irregularly-spaced data," in Proceedings of the 23rd ACM National Conference, New York, NY, USA, 1968, pp. 517-524.
[14] G. E. P. Box, G. M. Jenkins, G. C. Reinsel, and G. M. Ljung, Time Series Analysis: Forecasting and Control, 5th ed. Hoboken, NJ, USA: Wiley, 2015.
[15] J. Kreps, "Questioning the Lambda architecture," O'Reilly Radar, Jul. 2014. [Online]. Available: https://www.oreilly.com/radar/questioning-the-lambda-architecture/
[16] R. J. Hyndman and G. Athanasopoulos, Forecasting: Principles and Practice, 3rd ed. Melbourne, Australia: OTexts, 2021. [Online]. Available: https://otexts.com/fpp3/
[17] P. Buneman, S. Khanna, and W.-C. Tan, "Why and where: A characterization of data provenance," in Proceedings of the 8th International Conference on Database Theory, 2001, pp. 316-330.
[18] U.S. Environmental Protection Agency, "EPA air sensor guidebook," EPA/600/R-14/159, Washington, DC, USA, 2014.
[19] J. H. Seinfeld and S. N. Pandis, Atmospheric Chemistry and Physics: From Air Pollution to Climate Change, 3rd ed. Hoboken, NJ, USA: Wiley, 2016.
[20] Copernicus Atmosphere Monitoring Service, "CAMS European and global air quality forecasts," 2026. [Online]. Available: https://atmosphere.copernicus.eu/

## APPENDIX I: SCREENSHOTS

This appendix shows the running system. Each capture was taken from the live dashboard and the API. Every screen shows its coverage mode. The main screens also appear in Chapter 4, and the remaining captures are collected here.

![Figure 19: Map-first dashboard overview](docs/screenshots/dashboard-overview.png)

Figure 19: Map-first dashboard overview

The dashboard opens with a Kathmandu Valley map. Station markers show the latest AQI. The AQI surface and the wind flow are toggled from the layer rail. The top bar shows the current coverage mode and the AQI value.

![Figure 20: Provenance panel](docs/screenshots/provenance-panel.png)

Figure 20: Provenance panel

The provenance panel shows the source, observation type, coverage mode, and confidence of the selected station. The user can tell live, recent, modeled, and replay data apart at a glance.

![Figure 21: Replay demo mode](docs/screenshots/replay-demo-mode.png)

Figure 21: Replay demo mode

Replay demo mode pushes stored fixture readings through Kafka and Spark. The dashboard labels the data REPLAY_DEMO instead of presenting it as live.

![Figure 22: Forecast panel](docs/screenshots/forecast-panel.png)

Figure 22: Forecast panel

The forecast panel shows the 48-hour AQI line with a confidence band. It lists the model name, the fallback reason, and the best six-hour windows for the selected station.

![Figure 23: Pipeline health](docs/screenshots/pipeline-health.png)

Figure 23: Pipeline health

The pipeline health report lists the database, Kafka, pollers, and forecast components with their status. It is the first place an operator checks when data stops arriving.
