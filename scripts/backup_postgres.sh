#!/usr/bin/env bash
# Backup PostgreSQL to S3-compatible storage.
# Required env vars:
#   POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
#   S3_BUCKET, S3_ENDPOINT, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
# Optional:
#   S3_PREFIX        - prefix inside bucket (default: "backups")
#   BACKUP_RETAIN    - number of daily backups to keep (default: 7)
set -euo pipefail

: "${POSTGRES_HOST:?POSTGRES_HOST required}"
: "${POSTGRES_DB:?POSTGRES_DB required}"
: "${S3_BUCKET:?S3_BUCKET required}"
: "${S3_ENDPOINT:?S3_ENDPOINT required}"
: "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID required}"
: "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY required}"

POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-user}"
S3_PREFIX="${S3_PREFIX:-backups}"
BACKUP_RETAIN="${BACKUP_RETAIN:-7}"

TIMESTAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"
FILENAME="${POSTGRES_DB}_${TIMESTAMP}.sql.gz"
S3_PATH="s3://${S3_BUCKET}/${S3_PREFIX}/${FILENAME}"

export PGPASSWORD="${POSTGRES_PASSWORD}"

echo "[backup] starting pg_dump ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT}"
pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gzip > "/tmp/${FILENAME}"

SIZE=$(du -h "/tmp/${FILENAME}" | cut -f1)
echo "[backup] dump complete: ${FILENAME} (${SIZE})"

S3_ARGS="--endpoint-url ${S3_ENDPOINT}"

echo "[backup] uploading to ${S3_PATH}"
aws s3 cp "/tmp/${FILENAME}" "$S3_PATH" $S3_ARGS
echo "[backup] upload complete"

rm -f "/tmp/${FILENAME}"

# Rotate old backups: list files, sort, delete oldest if count > BACKUP_RETAIN
echo "[backup] checking retention (keep last ${BACKUP_RETAIN})"
EXISTING=$(aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}/" $S3_ARGS \
  | awk '{print $4}' \
  | grep "^${POSTGRES_DB}_.*\.sql\.gz$" \
  | sort)

COUNT=$(echo "$EXISTING" | grep -c . || true)

if [ "$COUNT" -gt "$BACKUP_RETAIN" ]; then
  DELETE_COUNT=$((COUNT - BACKUP_RETAIN))
  echo "[backup] deleting ${DELETE_COUNT} old backup(s)"
  echo "$EXISTING" | head -n "$DELETE_COUNT" | while read -r old_file; do
    aws s3 rm "s3://${S3_BUCKET}/${S3_PREFIX}/${old_file}" $S3_ARGS
    echo "[backup] deleted ${old_file}"
  done
fi

echo "[backup] done"
