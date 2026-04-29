# PHASE-02 Summary - Infrastructure Foundation

## What was built

- `docker-compose.yml`: Profile-based local stack for TimescaleDB/PostGIS, Kafka, Airflow PostgreSQL metadata, Airflow webserver/scheduler, API placeholder, frontend placeholder, Spark placeholder, weather placeholders, OpenAQ placeholder, and replay placeholder services.
- `.env.example`: Blank environment contract for required runtime names plus local infrastructure override names.
- `scripts/verify_env.sh`: Profile-aware health checker for Docker Compose services.
- `scripts/create_kafka_topics.sh`: Kafka topic creation script with dry-run support.
- `README.md`: Profile usage, verification commands, Kafka topic setup, host port defaults, and placeholder limitations.
- `airflow/dags/.gitkeep`: Trackable Airflow DAG mount directory.
- `airflow/plugins/.gitkeep`: Trackable Airflow plugin mount directory.
- `CHANGELOG.md`: Phase 02 implementation and verification history.

## Current system state

The `core` profile has been started locally and verified healthy:

- `timescaledb`: running and healthy, exposed on host port `55432`, container port `5432`.
- `kafka`: running and healthy, exposed on host port `29092`.
- `api`: placeholder HTTP service running and healthy on host port `8000`.
- `frontend`: placeholder Nginx service running and healthy on host port `3000`.

Kafka topics created in the local broker:

- `raw-aq-readings`
- `processed-aq-readings`
- `raw-aq-readings-dlq`
- `weather-data`
- `pipeline-events`

The `stream`, `batch`, `weather`, `observed`, `demo`, and `full` profiles are defined and pass Compose configuration validation, but their runtime services were not started in this phase except as dependencies of the core verification. No database schema, migrations, producers, consumers, Spark jobs, Airflow DAGs, API endpoints, forecasting logic, or frontend product behavior were introduced.

## Commands run

```bash
bash -n scripts/verify_env.sh scripts/create_kafka_topics.sh
# passed

./scripts/create_kafka_topics.sh --dry-run
# passed; printed the five expected Kafka topic creation commands

docker compose --profile full config --quiet
# passed

docker compose --profile full config --services | sort
# passed; listed all configured profile services

docker compose --profile core up -d
# failed first attempt; host port 5432 was already in use

docker compose --profile core up -d
# passed after changing TimescaleDB host port default to 55432

./scripts/verify_env.sh
# passed; timescaledb, kafka, api, and frontend were running and healthy

docker compose config
# passed; rendered no default services because runtime services are profile-gated

./scripts/create_kafka_topics.sh
# passed; created all five architecture topics

docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --list | sort
# passed; listed all five expected topics
```

## Exit criteria verification

- [x] All in-scope tasks are complete: Compose profiles, infrastructure services, placeholders, memory limits, health checks, verification script, topic script, README docs, changelog, and phase summary were added.
- [x] Relevant verification commands were run: required config, health, and topic dry-run checks passed; core startup and actual Kafka topic creation also passed.
- [x] `CHANGELOG.md` was updated: Phase 02 entry added.
- [x] `docs/phase-summaries/PHASE-02-summary.md` was written.
- [x] No future-phase work was introduced: no schemas, migrations, producers, consumers, DAGs, API endpoints, Spark jobs, forecasting logic, or frontend product implementation were added.
- [x] No secrets, fake live data, silent fallbacks, or unlabeled modeled/replay data were introduced: `.env.example` values remain blank and placeholders serve static infrastructure health only.

## Problems encountered and resolutions

- Docker daemon access was blocked by the sandbox. The Docker commands were rerun with approved escalation.
- The first `docker compose --profile core up -d` failed because host port `5432` was already in use. The compose file now defaults TimescaleDB host exposure to `55432` and Airflow PostgreSQL host exposure to `55433`, while keeping normal container ports for service-to-service traffic.
- Pulling `timescale/timescaledb-ha:pg16` was slow because the image is large. The pull completed and the service became healthy.

## Deviations from the phase plan

- Added the `observed` profile as a placeholder because the system overview defines it as part of the approved Compose architecture.
- Ran actual `core` profile startup and Kafka topic creation in addition to the required dry-run verification.
- Added local host port override names to `.env.example` to make the stack usable on laptops that already run PostgreSQL.

## Known issues and technical debt

- Severity: Low. Placeholder services use generic HTTP containers only for infrastructure health checks. Later phases must replace them with real FastAPI, React, Spark, poller, and replay implementations.
- Severity: Low. `stream`, `batch`, `weather`, `observed`, and `demo` profile service definitions were config-validated but not runtime-started in this phase to avoid pulling every heavy image at once.
- Severity: Low. The TimescaleDB/PostGIS image is large. This is expected for the bundled extension image, but first startup may be slow on a limited connection.

## What the next phase needs to know

- The `core` profile is currently running locally after verification.
- Internal service URLs should use container names and normal ports, for example `timescaledb:5432` and `kafka:9092`.
- Host access to TimescaleDB defaults to `localhost:55432`, not `localhost:5432`, to avoid local PostgreSQL conflicts.
- The five Kafka topics already exist in the local broker, but topic creation remains idempotent through `scripts/create_kafka_topics.sh`.
- Phase 03 should add Alembic/database schema work only through migrations.

## How to resume from scratch

```bash
docker compose --profile core up -d
./scripts/verify_env.sh
./scripts/create_kafka_topics.sh --dry-run
./scripts/create_kafka_topics.sh
```

To stop the core stack after local work:

```bash
docker compose --profile core down
```

## Next session prompt

```text
Follow AGENTS.md. Implement PHASE 03 only using docs/codex/phases/PHASE-03-database-schema-seed-data.md.
```
