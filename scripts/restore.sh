#!/usr/bin/env bash
# Restore the Postgres database from a backup produced by backup.sh.
# Usage: scripts/restore.sh backups/trading-<timestamp>.sql.gz
set -euo pipefail
cd "$(dirname "$0")/.."

if [ $# -ne 1 ]; then
  echo "usage: scripts/restore.sh <backup.sql.gz>"
  exit 2
fi
BACKUP="$1"
[ -f "${BACKUP}" ] || { echo "file not found: ${BACKUP}"; exit 1; }

read -r -p "This will OVERWRITE the current database. Type 'yes' to continue: " ok
[ "${ok}" = "yes" ] || { echo "aborted"; exit 1; }

docker compose up -d db
docker compose exec -T db psql -U trading -d postgres \
  -c "DROP DATABASE IF EXISTS trading;" -c "CREATE DATABASE trading;"
gunzip -c "${BACKUP}" | docker compose exec -T db psql -U trading -d trading
echo "Restore complete from ${BACKUP}"
