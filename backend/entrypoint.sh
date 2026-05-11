#!/bin/sh
set -e

# -----------------------------------------------------------------------------
# Migrations
# -----------------------------------------------------------------------------
# By default we run Alembic before starting the API (similar to Render predeploy).
# For multiple backend replicas in production, disable inline migrations and run
# a one-off migration job instead (e.g. `docker compose run --rm backend poetry run alembic upgrade head`
# or your orchestrator's Job) so only one process applies migrations at deploy time.
#
# Skip auto-migration: RUN_MIGRATIONS=0
# -----------------------------------------------------------------------------
if [ "${RUN_MIGRATIONS:-1}" != "0" ]; then
  poetry run alembic upgrade head
fi

# PORT is honored for parity with Render; default 8000 for local Docker Compose.
exec poetry run uvicorn src.app:app --host 0.0.0.0 --port "${PORT:-8000}"
