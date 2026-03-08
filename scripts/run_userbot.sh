#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USERBOT_DIR="$ROOT_DIR/userbot_service"
VENV_DIR="${VENV_DIR:-$USERBOT_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

export API_BASE_URL="${API_BASE_URL:-http://localhost:8080}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export DELIVERY_WORKERS="${DELIVERY_WORKERS:-1}"
export DELIVERY_MIN_INTERVAL_SEC="${DELIVERY_MIN_INTERVAL_SEC:-0.35}"

if [[ ! -f "$USERBOT_DIR/main.py" ]]; then
  echo "userbot_service/main.py not found" >&2
  exit 1
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python not found: $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -d "$VENV_DIR" || ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "Creating virtualenv at $VENV_DIR"
  rm -rf "$VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "Virtualenv activation script not found: $VENV_DIR/bin/activate" >&2
  echo "Install python venv package: sudo apt-get install -y python3-venv" >&2
  exit 1
fi

source "$VENV_DIR/bin/activate"

REQ_FILE="$USERBOT_DIR/requirments.txt"
if [[ ! -f "$REQ_FILE" ]]; then
  REQ_FILE="$USERBOT_DIR/requirements.txt"
fi

if [[ ! -f "$REQ_FILE" ]]; then
  echo "Requirements file not found in $USERBOT_DIR" >&2
  exit 1
fi

echo "Installing dependencies from $REQ_FILE"
python -m pip install --upgrade pip
python -m pip install --upgrade -r "$REQ_FILE"
python -m pip check

echo "Starting userbot with:"
echo "  API_BASE_URL=$API_BASE_URL"
echo "  REDIS_URL=$REDIS_URL"
echo "  DELIVERY_WORKERS=$DELIVERY_WORKERS"
echo "  DELIVERY_MIN_INTERVAL_SEC=$DELIVERY_MIN_INTERVAL_SEC"

cd "$USERBOT_DIR"
python main.py
