#!/usr/bin/env sh
# Render start: migratsiya → demo seed (idempotent) → server ($PORT).
set -e
alembic upgrade head
python -m scripts.seed_admin
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
