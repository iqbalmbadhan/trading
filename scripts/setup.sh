#!/usr/bin/env bash
# One-command setup: generate secrets, start data services, run migrations,
# create the admin user. Safe to re-run (idempotent).
set -euo pipefail
cd "$(dirname "$0")/.."

ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-changeme-admin-pass}"

gen() { python3 -c "import secrets;print(secrets.token_urlsafe(48))"; }

if [ ! -f .env ]; then
  cp .env.example .env
  MASTER_KEY="$(gen)"
  JWT_SECRET="$(gen)"
  # Replace the insecure dev defaults with generated values.
  sed -i.bak "s|^MASTER_KEY=.*|MASTER_KEY=${MASTER_KEY}|" .env
  sed -i.bak "s|^JWT_SECRET=.*|JWT_SECRET=${JWT_SECRET}|" .env
  rm -f .env.bak
  echo "Generated .env with fresh MASTER_KEY and JWT_SECRET."
else
  echo ".env already exists; leaving it untouched."
fi

echo "Starting database and redis..."
docker compose up -d db redis

echo "Running migrations..."
docker compose run --rm backend alembic upgrade head

echo "Creating admin user (${ADMIN_EMAIL})..."
docker compose run --rm backend \
  python -m app.scripts.create_admin "${ADMIN_EMAIL}" "${ADMIN_PASSWORD}"

cat <<EOF

Setup complete.
  Start everything:  docker compose up -d
  Backend health:    http://localhost:8000/health
  Frontend:          http://localhost:3000
  Admin login:       ${ADMIN_EMAIL}

IMPORTANT: change the admin password after first login. Trading defaults to
paper mode; live trading requires the typed confirmation phrase.
EOF
