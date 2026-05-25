#!/usr/bin/env bash
set -euo pipefail

frontend_url="${FRONTEND_URL:-http://localhost:3000}"
max_attempts="${RESET_FRONTEND_MAX_ATTEMPTS:-30}"
sleep_seconds="${RESET_FRONTEND_SLEEP_SECONDS:-2}"

log() {
  echo "[reset_frontend] $*"
}

fail_with_diagnostics() {
  log "frontend verification failed; collecting diagnostics"
  docker compose ps frontend || true
  docker compose logs frontend --tail 80 || true
  curl -sS "$frontend_url" | sed -n '1,60p' || true
  exit 1
}

if ! command -v docker >/dev/null 2>&1; then
  log "docker is not installed or not on PATH"
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  log "curl is not installed or not on PATH"
  exit 1
fi

log "building frontend image"
docker compose build frontend

log "recreating frontend container"
docker compose up -d --force-recreate --no-deps frontend

log "waiting for frontend health"
attempt=1
while [[ "$attempt" -le "$max_attempts" ]]; do
  container_id="$(docker compose ps -q frontend 2>/dev/null || true)"
  if [[ -n "$container_id" ]]; then
    status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id" 2>/dev/null || echo unknown)"
    if [[ "$status" == "healthy" || "$status" == "running" ]]; then
      break
    fi
  fi
  sleep "$sleep_seconds"
  attempt=$((attempt + 1))
done

if [[ "$attempt" -gt "$max_attempts" ]]; then
  log "frontend did not become healthy within timeout"
  fail_with_diagnostics
fi

log "verifying frontend content marker from $frontend_url"
html="$(curl -sS "$frontend_url")"

if echo "$html" | grep -q "Welcome to nginx"; then
  log "detected default nginx page"
  fail_with_diagnostics
fi

if ! echo "$html" | grep -Eq "HimalayaAir Dashboard|HimalayaAir"; then
  log "HimalayaAir marker not found in frontend HTML"
  fail_with_diagnostics
fi

log "frontend reset complete; HimalayaAir page is being served"
