#!/usr/bin/env bash
# Run database migrations before starting the web service on Render (or similar hosts).
# Pre-deploy: apply migrations only — do not drop schema or run destructive DB scripts here.
#
# Render: set Root Directory to `backend` (or cd into backend first), then:
#   bash render_predeploy.sh
# Equivalent one-liner:
#   PYTHONPATH=src poetry run alembic upgrade head
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export PYTHONPATH=src
exec poetry run alembic upgrade head
