#!/usr/bin/env bash
set -euo pipefail

profile="core"

usage() {
  cat <<USAGE
Usage: $0 [--profile core|stream|batch|weather|observed|demo|full]

Checks Docker Compose configuration and health state for the selected profile.
The default profile is core.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      profile="${2:-}"
      if [[ -z "$profile" ]]; then
        echo "missing value for --profile" >&2
        exit 2
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

services_for_profile() {
  case "$1" in
    core)
      echo "timescaledb kafka api frontend"
      ;;
    stream)
      echo "timescaledb kafka spark-stream"
      ;;
    batch)
      echo "airflow-postgres airflow-webserver airflow-scheduler"
      ;;
    weather)
      echo "timescaledb weather-poller openmeteo-aq-poller"
      ;;
    observed)
      echo "timescaledb kafka openaq-poller"
      ;;
    demo)
      echo "kafka replay-publisher"
      ;;
    full)
      echo "timescaledb kafka api frontend spark-stream airflow-postgres airflow-webserver airflow-scheduler weather-poller openmeteo-aq-poller openaq-poller replay-publisher"
      ;;
    *)
      echo "unknown profile: $1" >&2
      exit 2
      ;;
  esac
}

if ! command -v docker >/dev/null 2>&1; then
  echo "docker: missing"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose: missing or not available"
  exit 1
fi

if ! docker compose config --quiet >/dev/null 2>&1; then
  echo "compose_config: invalid"
  docker compose config --quiet
  exit 1
fi

echo "compose_config: ok"
status=0

for service in $(services_for_profile "$profile"); do
  container_id="$(docker compose ps -q "$service" 2>/dev/null || true)"
  if [[ -z "$container_id" ]]; then
    echo "$service: not_created"
    status=1
    continue
  fi

  state="$(docker inspect -f '{{.State.Status}}' "$container_id" 2>/dev/null || echo unknown)"
  health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id" 2>/dev/null || echo unknown)"

  if [[ "$state" == "running" && ( "$health" == "healthy" || "$health" == "none" ) ]]; then
    echo "$service: ok state=$state health=$health"
  else
    echo "$service: not_ready state=$state health=$health"
    status=1
  fi
done

exit "$status"
