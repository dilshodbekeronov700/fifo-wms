#!/usr/bin/env bash
#
# WMS PostgreSQL backup — nightly logical dump with rotation.
#
# Usage:
#   DATABASE_URL=postgresql://wms:wms@localhost:5432/wms \
#   BACKUP_DIR=/var/backups/wms RETENTION_DAYS=14 ./scripts/backup_db.sh
#
# Cron (nightly at 02:30), e.g. /etc/cron.d/wms-backup:
#   30 2 * * *  wms  DATABASE_URL=... BACKUP_DIR=/var/backups/wms /opt/wms/scripts/backup_db.sh >> /var/log/wms-backup.log 2>&1
#
# For point-in-time recovery you additionally need WAL archiving
# (archive_mode=on + archive_command) — see docs/backup.md.
set -euo pipefail

DATABASE_URL="${DATABASE_URL:?DATABASE_URL required (plain postgresql:// form, not +asyncpg)}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

# SQLAlchemy'ning +asyncpg/+psycopg driver qo'shimchasini pg_dump uchun olib tashlaymiz.
PG_URL="${DATABASE_URL/+asyncpg/}"
PG_URL="${PG_URL/+psycopg/}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/wms_${STAMP}.dump"

echo "[$(date -Iseconds)] Backing up → $OUT"
# -Fc = custom format (pg_restore bilan tiklanadi, siqilgan).
pg_dump --format=custom --no-owner --no-privileges --dbname="$PG_URL" --file="$OUT"

# Yaxlitlikni tekshiramiz (buzuq dump jimgina o'tib ketmasin).
pg_restore --list "$OUT" > /dev/null
echo "[$(date -Iseconds)] OK ($(du -h "$OUT" | cut -f1))"

# Eski nusxalarni tozalaymiz.
find "$BACKUP_DIR" -name 'wms_*.dump' -type f -mtime "+${RETENTION_DAYS}" -print -delete

echo "[$(date -Iseconds)] Retention: kept last ${RETENTION_DAYS} days"
