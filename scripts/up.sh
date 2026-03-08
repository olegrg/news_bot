#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDS_FILE="/tmp/news_bot_port_forward.pids"

DEPLOY="${DEPLOY:-1}"
PORT_FORWARD="${PORT_FORWARD:-1}"

cleanup() {
  if [[ -f "$PIDS_FILE" ]]; then
    if [[ -s "$PIDS_FILE" ]]; then
      echo "Stopping port-forward processes"
      xargs kill < "$PIDS_FILE" 2>/dev/null || true
    fi
    rm -f "$PIDS_FILE"
  fi
}

trap cleanup EXIT INT TERM

if [[ "$DEPLOY" == "1" ]]; then
  echo "[up] Deploying Kubernetes stack"
  "$ROOT_DIR/scripts/deploy_k8s.sh"
fi

if [[ "$PORT_FORWARD" == "1" ]]; then
  echo "[up] Starting port-forwards"
  "$ROOT_DIR/scripts/dev_port_forward.sh"
  sleep 2
fi

echo "[up] Starting userbot"
exec "$ROOT_DIR/scripts/run_userbot.sh"
