#!/usr/bin/env sh
# Render start: migratsiya → demo seed (idempotent) → server ($PORT).
set -e
python -m scripts.init_db          # create_all (idempotent, to'liq sxema)
alembic stamp head                 # migratsiyalarni "bajarilgan" deb belgilaydi
python -m scripts.seed_admin       # demo tenant/admin/ombor (idempotent)
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
