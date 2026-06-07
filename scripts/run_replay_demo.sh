#!/usr/bin/env bash
set -euo pipefail

fixture="fixtures/replay_sample.json"
speed="500"
wait_seconds="60"
api_base_url="${API_BASE_URL:-http://localhost:8000}"
frontend_url="${FRONTEND_URL:-http://localhost:3000}"
kafka_bootstrap="${KAFKA_BOOTSTRAP_SERVERS:-localhost:29092}"
build=false
skip_compose_up=false

usage() {
  cat <<USAGE
Usage: $0 [--fixture PATH] [--speed N] [--wait-seconds N] [--build] [--skip-compose-up]

Starts the core+stream profiles, publishes replay fixture data through Kafka, and verifies API/frontend-visible replay provenance.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fixture)
      fixture="${2:-}"
      if [[ -z "$fixture" ]]; then
        echo "missing value for --fixture" >&2
        exit 2
      fi
      shift 2
      ;;
    --speed)
      speed="${2:-}"
      if [[ -z "$speed" ]]; then
        echo "missing value for --speed" >&2
        exit 2
      fi
      shift 2
      ;;
    --wait-seconds)
      wait_seconds="${2:-}"
      if [[ -z "$wait_seconds" ]]; then
        echo "missing value for --wait-seconds" >&2
        exit 2
      fi
      shift 2
      ;;
    --build)
      build=true
      shift
      ;;
    --skip-compose-up)
      skip_compose_up=true
      shift
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

if [[ "$skip_compose_up" != "true" ]]; then
  compose_cmd=(docker compose --profile core --profile stream up -d)
  if [[ "$build" == "true" ]]; then
    compose_cmd+=(--build)
  fi
  "${compose_cmd[@]}"
fi

./scripts/create_kafka_topics.sh
./scripts/verify_env.sh --profile core
./scripts/verify_env.sh --profile stream

python -m services.replay_publisher.main --dry-run --fixture "$fixture" --speed "$speed" --rebase-to-now
KAFKA_BOOTSTRAP_SERVERS="$kafka_bootstrap" python -m services.replay_publisher.main --fixture "$fixture" --speed "$speed" --rebase-to-now

python - "$api_base_url" "$frontend_url" "$wait_seconds" <<'PY'
import json
import sys
import time
import urllib.error
import urllib.request

api_base_url = sys.argv[1].rstrip("/")
frontend_url = sys.argv[2].rstrip("/")
wait_seconds = int(sys.argv[3])


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_status(url: str) -> int:
    with urllib.request.urlopen(url, timeout=5) as response:
        return int(response.status)


deadline = time.time() + wait_seconds
last_error = "not checked"
stations_payload: dict | None = None

while time.time() < deadline:
    try:
        stations_payload = fetch_json(f"{api_base_url}/api/stations")
        replay_stations = [
            station for station in stations_payload.get("stations", [])
            if station.get("observation_type") == "replay" and station.get("coverage_mode") == "REPLAY_DEMO"
        ]
        if stations_payload.get("replay_active") is True and len(replay_stations) >= 3:
            break
        last_error = (
            f"replay_active={stations_payload.get('replay_active')} "
            f"replay_station_rows={len(replay_stations)} "
            f"coverage_mode={stations_payload.get('coverage_mode')}"
        )
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        last_error = str(exc)
    time.sleep(3)
else:
    raise SystemExit(f"replay API verification failed: {last_error}")

interpolation_payload = fetch_json(f"{api_base_url}/api/interpolation/current?pollutant=pm25")
frontend_status = fetch_status(frontend_url)
if frontend_status != 200:
    raise SystemExit(f"frontend verification failed: status={frontend_status}")

print(
    json.dumps(
        {
            "stations_coverage_mode": stations_payload.get("coverage_mode") if stations_payload else None,
            "stations_replay_active": stations_payload.get("replay_active") if stations_payload else None,
            "interpolation_coverage_mode": interpolation_payload.get("coverage_mode"),
            "frontend_status": frontend_status,
        },
        indent=2,
    )
)
PY
