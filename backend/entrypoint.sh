#!/usr/bin/env sh
set -eu

tries="${DB_STARTUP_RETRIES:-20}"
delay="${DB_STARTUP_RETRY_DELAY:-3}"

for i in $(seq 1 "$tries"); do
  if alembic -c /app/backend/alembic.ini upgrade head; then
    exec uvicorn app.main:app --host 0.0.0.0 --port 8080
  fi
  if [ "$i" = "$tries" ]; then
    echo "database migration failed after $tries attempts" >&2
    exit 1
  fi
  echo "database unavailable, retrying in ${delay}s ($i/$tries)" >&2
  sleep "$delay"
done

