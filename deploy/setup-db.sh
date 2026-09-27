#!/usr/bin/env bash
set -euo pipefail

DB_IP="${DB_IP:-192.168.64.22}"
APP_IP="${APP_IP:-192.168.64.20}"
DB_ADMIN_PASS="${DB_ADMIN_PASS:?DB_ADMIN_PASS is required}"
APP_USER_PASS="${APP_USER_PASS:?APP_USER_PASS is required}"

echo "==> Установка пакетов"
sudo apt update
sudo apt install -y curl ca-certificates ufw

echo "==> Подключение репозитория PGDG"
sudo install -d /usr/share/postgresql-common/pgdg
sudo curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
    https://www.postgresql.org/media/keys/ACCC4CF8.asc

echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] \
https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" | \
    sudo tee /etc/apt/sources.list.d/pgdg.list > /dev/null

echo "==> Установка PostgreSQL 18"
sudo apt update
sudo apt install -y postgresql-18 postgresql-client-18

echo "==> Настройка listen_addresses"
sudo sed -i "s/^#*listen_addresses.*/listen_addresses = '${DB_IP}'/" \
    /etc/postgresql/18/main/postgresql.conf

echo "==> Разрешение подключений с app-srv"
sudo tee -a /etc/postgresql/18/main/pg_hba.conf > /dev/null <<EOF
host    confplus    app_user    ${APP_IP}/32    scram-sha-256
host    confplus    db_admin    ${APP_IP}/32    scram-sha-256
EOF

sudo systemctl restart postgresql

echo "==> Создание ролей и БД"
sudo -u postgres psql --set=admin_pass="${DB_ADMIN_PASS}" \
                      --set=app_pass="${APP_USER_PASS}" <<'SQL'
CREATE ROLE db_admin LOGIN PASSWORD :'admin_pass' CREATEDB;
CREATE ROLE app_user LOGIN PASSWORD :'app_pass'
    NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE DATABASE confplus OWNER db_admin;
\c confplus
GRANT CONNECT ON DATABASE confplus TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES FOR ROLE db_admin IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES FOR ROLE db_admin IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO app_user;
SQL

echo "==> Firewall"
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow from "${APP_IP}" to any port 5432 proto tcp
sudo ufw --force enable

echo "==> Готово"
sudo systemctl status postgresql --no-pager
