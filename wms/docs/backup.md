# WMS — Backup & Disaster Recovery

## 1. Logik backup (kunlik)

`scripts/backup_db.sh` `pg_dump -Fc` orqali siqilgan nusxa oladi, yaxlitligini
tekshiradi va eskilarini rotatsiya qiladi.

```bash
DATABASE_URL=postgresql://wms:wms@db:5432/wms \
BACKUP_DIR=/var/backups/wms RETENTION_DAYS=14 \
  ./scripts/backup_db.sh
```

Cron (har kecha 02:30):

```
30 2 * * *  wms  DATABASE_URL=... BACKUP_DIR=/var/backups/wms /opt/wms/scripts/backup_db.sh >> /var/log/wms-backup.log 2>&1
```

Nusxalarni **boshqa hostga/S3'ga** ko'chiring (bir diskda saqlash DR emas):

```bash
aws s3 sync /var/backups/wms s3://acme-wms-backups/ --storage-class STANDARD_IA
```

## 2. Tiklash (restore)

```bash
createdb wms_restore
pg_restore --no-owner --no-privileges --dbname=postgresql://wms:wms@db:5432/wms_restore  wms_20260717_023000.dump
```

Tiklashni **muntazam sinab ko'ring** — sinovdan o'tmagan backup = backup emas.

## 3. Point-in-Time Recovery (PITR) — RPO ≈ 0

Logik dump kunlik (RPO ≈ 24 soat). Yo'qotishni minimallashtirish uchun WAL arxivlash:

`postgresql.conf`:
```
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://acme-wms-wal/%f'
```

Bazaviy nusxa: `pg_basebackup -D /var/backups/base -Ft -z -P`.
Tiklashda `restore_command` + `recovery_target_time` ishlatiladi.

## 4. Maqsadlar

| Ko'rsatkich | Logik (kunlik) | PITR (WAL) |
|-------------|----------------|------------|
| RPO         | ≤ 24 soat      | ≤ 1 daqiqa |
| RTO         | ~30 daqiqa     | ~1 soat    |

Kelajak: standby replica (streaming replication) + avtomatik failover.
