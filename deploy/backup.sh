#!/usr/bin/env bash
# Back up the MarketHub PostgreSQL database to ~/backups/markethub and keep
# the last 14 days.
#
#   bash ~/markethub/deploy/backup.sh
#
# Run it from cron (see deploy/DEPLOY.md, "Database backups"). Restore with:
#   gunzip -c ~/backups/markethub/markethub-YYYYmmdd-HHMM.sql.gz | \
#     docker compose -p markethub -f deploy/compose.prod.yml --env-file deploy/.env.prod \
#       exec -T db psql -U markethub -d markethub
set -euo pipefail

cd "$(dirname "$0")/.."
ENV_FILE="deploy/.env.prod"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/markethub}"
KEEP_DAYS="${KEEP_DAYS:-14}"

env_value() { grep -E "^$1=" "$ENV_FILE" | tail -n1 | cut -d= -f2- | tr -d '"' || true; }
DB_NAME="$(env_value POSTGRES_DB)"; DB_NAME="${DB_NAME:-markethub}"
DB_USER="$(env_value POSTGRES_USER)"; DB_USER="${DB_USER:-markethub}"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
FILE="$BACKUP_DIR/markethub-$(date -u +%Y%m%d-%H%M).sql.gz"

# Write to a temporary file first so a failed dump never looks like a backup.
docker compose -p markethub -f deploy/compose.prod.yml --env-file "$ENV_FILE" \
  exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" --no-owner --clean --if-exists \
  | gzip -9 > "$FILE.part"
mv "$FILE.part" "$FILE"
chmod 600 "$FILE"

find "$BACKUP_DIR" -name 'markethub-*.sql.gz' -mtime +"$KEEP_DAYS" -delete
echo "[backup $(date -u +%H:%M:%S)] $FILE ($(du -h "$FILE" | cut -f1))"
