#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/loan_radar_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[INFO] Starting PostgreSQL backup..."
docker compose exec -T postgres pg_dump -U loan_radar loan_radar | gzip > "${BACKUP_FILE}"

FILE_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "[INFO] Backup completed: ${BACKUP_FILE} (${FILE_SIZE})"

KEEP_DAYS="${KEEP_DAYS:-30}"
echo "[INFO] Cleaning up backups older than ${KEEP_DAYS} days..."
find "${BACKUP_DIR}" -name "loan_radar_*.sql.gz" -mtime +${KEEP_DAYS} -delete 2>/dev/null || true

echo "[INFO] Done."
