#!/bin/bash
set -e

DB_NAME="confplus"
DB_USER="confplus_user"
DB_HOST="localhost"
DB_PORT="5432"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -Fc -f "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.dump"
echo "Бэкап создан: $BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.dump"
