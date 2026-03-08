#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-default}"
DB_API_SERVICE="${DB_API_SERVICE:-db-api-db-api}"
REDIS_SERVICE="${REDIS_SERVICE:-redis}"
DB_API_LOCAL_PORT="${DB_API_LOCAL_PORT:-8080}"
REDIS_LOCAL_PORT="${REDIS_LOCAL_PORT:-6379}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

need_cmd kubectl
need_cmd curl

PIDS_FILE="/tmp/news_bot_port_forward.pids"
: > "$PIDS_FILE"

echo "Starting port-forward for db_api svc/$DB_API_SERVICE -> localhost:$DB_API_LOCAL_PORT"
kubectl port-forward -n "$NAMESPACE" "svc/$DB_API_SERVICE" "$DB_API_LOCAL_PORT":80 >/tmp/news_bot_db_api_pf.log 2>&1 &
echo $! >> "$PIDS_FILE"

echo "Starting port-forward for redis svc/$REDIS_SERVICE -> localhost:$REDIS_LOCAL_PORT"
kubectl port-forward -n "$NAMESPACE" "svc/$REDIS_SERVICE" "$REDIS_LOCAL_PORT":6379 >/tmp/news_bot_redis_pf.log 2>&1 &
echo $! >> "$PIDS_FILE"

sleep 1
while read -r pid; do
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    echo "Port-forward process $pid is not running. Check logs:" >&2
    echo "  /tmp/news_bot_db_api_pf.log" >&2
    echo "  /tmp/news_bot_redis_pf.log" >&2
    exit 1
  fi
done < "$PIDS_FILE"

echo "Waiting for db_api on localhost:$DB_API_LOCAL_PORT"
for _ in $(seq 1 20); do
  if curl -sS --max-time 2 "http://127.0.0.1:${DB_API_LOCAL_PORT}/immediate-subscriptions" >/dev/null; then
    echo "db_api port-forward is ready"
    break
  fi
  sleep 1
done

if ! curl -sS --max-time 2 "http://127.0.0.1:${DB_API_LOCAL_PORT}/immediate-subscriptions" >/dev/null; then
  echo "db_api is not reachable through port-forward." >&2
  echo "Check /tmp/news_bot_db_api_pf.log for details." >&2
  exit 1
fi

echo "Port-forward started. PIDs saved in $PIDS_FILE"
echo "Logs: /tmp/news_bot_db_api_pf.log, /tmp/news_bot_redis_pf.log"
echo "To stop: xargs kill < $PIDS_FILE"
