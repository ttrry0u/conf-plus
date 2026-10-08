#!/bin/bash
set -e

DB_NAME="confplus"
DB_USER="confplus_user"
DB_HOST="localhost"
DB_PORT="5432"
BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Использование: $0 <файл_бэкапа>"
    exit 1
fi

dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" --if-exists "$DB_NAME"
createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"
pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" "$BACKUP_FILE"
echo "Восстановлено из $BACKUP_FILE"
