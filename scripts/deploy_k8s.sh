#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

USE_MINIKUBE="${USE_MINIKUBE:-1}"
MINIKUBE_CPUS="${MINIKUBE_CPUS:-4}"
MINIKUBE_MEMORY="${MINIKUBE_MEMORY:-8192}"
MINIKUBE_DRIVER="${MINIKUBE_DRIVER:-docker}"

NAMESPACE="${NAMESPACE:-default}"
DB_API_RELEASE="${DB_API_RELEASE:-db-api}"
POSTGRES_RELEASE="${POSTGRES_RELEASE:-postgres}"
REDIS_RELEASE="${REDIS_RELEASE:-redis}"
PG_BACKUP_RELEASE="${PG_BACKUP_RELEASE:-pg-backup}"

DB_API_IMAGE="${DB_API_IMAGE:-db-api:latest}"
BUILD_DB_API_IMAGE="${BUILD_DB_API_IMAGE:-1}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

need_cmd kubectl
need_cmd helm

if [[ "$USE_MINIKUBE" == "1" ]]; then
  need_cmd minikube
  need_cmd docker

  echo "[1/6] Starting minikube"
  minikube start --cpus="$MINIKUBE_CPUS" --memory="$MINIKUBE_MEMORY" --driver="$MINIKUBE_DRIVER"

  echo "[2/6] Switching docker env to minikube"
  eval "$(minikube -p minikube docker-env)"

  if [[ "$BUILD_DB_API_IMAGE" == "1" ]]; then
    echo "[3/6] Building db_api image: $DB_API_IMAGE"
    docker build -t "$DB_API_IMAGE" "$ROOT_DIR/db_api"
  fi
else
  if [[ "$BUILD_DB_API_IMAGE" == "1" ]]; then
    echo "[info] USE_MINIKUBE=0, skipping local docker build"
  fi
fi

echo "[4/7] Deploying Postgres"
helm upgrade --install "$POSTGRES_RELEASE" "$ROOT_DIR/charts/postgres" --namespace "$NAMESPACE" --create-namespace

echo "[5/7] Deploying Redis"
helm upgrade --install "$REDIS_RELEASE" "$ROOT_DIR/charts/redis" --namespace "$NAMESPACE"

echo "[6/7] Deploying db_api"
helm upgrade --install "$DB_API_RELEASE" "$ROOT_DIR/charts/db_api" --namespace "$NAMESPACE"

echo "[7/7] Deploying pg-backup CronJob"
helm upgrade --install "$PG_BACKUP_RELEASE" "$ROOT_DIR/charts/pg-backup" --namespace "$NAMESPACE"

echo "Waiting for workloads to become ready"
kubectl rollout status statefulset/postgres -n "$NAMESPACE" --timeout=180s
kubectl rollout status deployment/redis -n "$NAMESPACE" --timeout=180s
kubectl rollout status deployment/${DB_API_RELEASE}-db-api -n "$NAMESPACE" --timeout=180s

echo "\nKubernetes status:"
kubectl get pods -n "$NAMESPACE"
kubectl get svc -n "$NAMESPACE"

echo "\nDone."
if [[ "$USE_MINIKUBE" == "1" ]]; then
  cat <<EOM
Next for local userbot:
  kubectl port-forward -n $NAMESPACE svc/${DB_API_RELEASE}-db-api 8080:80
  kubectl port-forward -n $NAMESPACE svc/redis 6379:6379
EOM
fi
