#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-default}"
DB_API_SERVICE="${DB_API_SERVICE:-db-api-db-api}"
REDIS_SERVICE="${REDIS_SERVICE:-redis}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

need_cmd kubectl

PIDS_FILE="/tmp/news_bot_port_forward.pids"
: > "$PIDS_FILE"

echo "Starting port-forward for db_api svc/$DB_API_SERVICE -> localhost:8080"
kubectl port-forward -n "$NAMESPACE" "svc/$DB_API_SERVICE" 8080:80 >/tmp/news_bot_db_api_pf.log 2>&1 &
echo $! >> "$PIDS_FILE"

echo "Starting port-forward for redis svc/$REDIS_SERVICE -> localhost:6379"
kubectl port-forward -n "$NAMESPACE" "svc/$REDIS_SERVICE" 6379:6379 >/tmp/news_bot_redis_pf.log 2>&1 &
echo $! >> "$PIDS_FILE"

echo "Port-forward started. PIDs saved in $PIDS_FILE"
echo "Logs: /tmp/news_bot_db_api_pf.log, /tmp/news_bot_redis_pf.log"
echo "To stop: xargs kill < $PIDS_FILE"
