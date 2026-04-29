# HimalayaAir

HimalayaAir is a Kathmandu Valley air-quality intelligence platform.

## Phase Workflow

Use one Codex session per phase. The architecture source of truth is
`docs/himalayaair-system-overview.md`, and the phase workflow source of truth is
`docs/codex/PHASE_INDEX.md`.

## Local Infrastructure

Phase 02 provides Docker Compose profiles so the stack can run on an 8-16 GB
laptop without starting every service at once.

Profiles:

- `core`: TimescaleDB/PostGIS, Kafka, API placeholder, frontend placeholder.
- `stream`: Spark stream placeholder with Kafka and TimescaleDB dependencies.
- `batch`: Airflow PostgreSQL metadata DB, Airflow webserver, Airflow scheduler.
- `weather`: weather and modeled-AQ poller placeholders with TimescaleDB.
- `observed`: OpenAQ poller placeholder with Kafka.
- `demo`: replay publisher placeholder with Kafka.
- `full`: all services.

Common commands:

```bash
docker compose --profile core up -d
docker compose --profile core --profile observed --profile stream up -d
docker compose --profile weather up -d
docker compose --profile batch up -d
docker compose --profile demo up replay-publisher
docker compose --profile full up -d
```

Health checks:

```bash
./scripts/verify_env.sh
./scripts/verify_env.sh --profile batch
./scripts/verify_env.sh --profile full
```

Kafka topic setup:

```bash
./scripts/create_kafka_topics.sh --dry-run
./scripts/create_kafka_topics.sh
```

The placeholder services exist only to validate infrastructure wiring. They do
not implement ingestion, API behavior, Spark processing, forecasting, or
frontend product features.
