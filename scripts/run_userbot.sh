#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USERBOT_DIR="$ROOT_DIR/userbot_service"

export API_BASE_URL="${API_BASE_URL:-http://localhost:8080}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export DELIVERY_WORKERS="${DELIVERY_WORKERS:-1}"
export DELIVERY_MIN_INTERVAL_SEC="${DELIVERY_MIN_INTERVAL_SEC:-0.35}"

if [[ ! -f "$USERBOT_DIR/main.py" ]]; then
  echo "userbot_service/main.py not found" >&2
  exit 1
fi

echo "Starting userbot with:"
echo "  API_BASE_URL=$API_BASE_URL"
echo "  REDIS_URL=$REDIS_URL"
echo "  DELIVERY_WORKERS=$DELIVERY_WORKERS"
echo "  DELIVERY_MIN_INTERVAL_SEC=$DELIVERY_MIN_INTERVAL_SEC"

cd "$USERBOT_DIR"
python3 main.py
