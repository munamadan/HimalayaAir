#!/usr/bin/env bash
set -euo pipefail

bootstrap_server="${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}"
compose_service="kafka"
dry_run=false

topics=(
  "raw-aq-readings:3:86400000"
  "weather-data:1:86400000"
  "modeled-aq-data:1:259200000"
  "processed-aq-readings:1:86400000"
  "raw-aq-readings-dlq:1:604800000"
  "pipeline-events:1:86400000"
)

usage() {
  cat <<USAGE
Usage: $0 [--dry-run] [--bootstrap-server HOST:PORT] [--compose-service SERVICE]

Creates the Kafka topics defined by the HimalayaAir architecture.
Use --dry-run to print the commands without requiring Docker or Kafka.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      dry_run=true
      shift
      ;;
    --bootstrap-server)
      bootstrap_server="${2:-}"
      if [[ -z "$bootstrap_server" ]]; then
        echo "missing value for --bootstrap-server" >&2
        exit 2
      fi
      shift 2
      ;;
    --compose-service)
      compose_service="${2:-}"
      if [[ -z "$compose_service" ]]; then
        echo "missing value for --compose-service" >&2
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

run_topic_create() {
  local topic="$1"
  local partitions="$2"
  local retention_ms="$3"
  local command=(
    kafka-topics
    --bootstrap-server "$bootstrap_server"
    --create
    --if-not-exists
    --topic "$topic"
    --partitions "$partitions"
    --replication-factor 1
    --config "retention.ms=$retention_ms"
  )

  if [[ "$dry_run" == "true" ]]; then
    printf 'docker compose exec -T %q' "$compose_service"
    printf ' %q' "${command[@]}"
    printf '\n'
    return 0
  fi

  docker compose exec -T "$compose_service" "${command[@]}"
}

for definition in "${topics[@]}"; do
  IFS=":" read -r topic partitions retention_ms <<<"$definition"
  run_topic_create "$topic" "$partitions" "$retention_ms"
done
