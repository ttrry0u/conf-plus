#!/usr/bin/env bash
set -euo pipefail

# Развёртывание сервера приложения (app-srv).
# Требует Debian 12 без GUI.
#
# Запуск:
#   sudo ./deploy/setup-app.sh
#
# После завершения необходимо вручную создать /etc/conf-plus/app.env
# и запустить службу: sudo systemctl start conf-plus

APP_USER="appuser"
APP_DIR="/opt/conf-plus"
ENV_DIR="/etc/conf-plus"
REPO_URL="https://github.com/ttrry0u/conf-plus.git"
APP_PORT="8000"

echo "==> Установка пакетов"
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git ufw curl ca-certificates

echo "==> Установка клиента PostgreSQL 18"
sudo install -d /usr/share/postgresql-common/pgdg
sudo curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
    https://www.postgresql.org/media/keys/ACCC4CF8.asc
echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] \
https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" | \
    sudo tee /etc/apt/sources.list.d/pgdg.list > /dev/null
sudo apt update
sudo apt install -y postgresql-client-18

echo "==> Создание системного пользователя $APP_USER"
sudo adduser --system --no-create-home --shell /usr/sbin/nologin --group "$APP_USER" || true

echo "==> Каталог приложения"
sudo mkdir -p "$APP_DIR"
sudo chown "$APP_USER:$APP_USER" "$APP_DIR"
sudo chmod 750 "$APP_DIR"

echo "==> Клонирование репозитория"
sudo -u "$APP_USER" git clone "$REPO_URL" "$APP_DIR" || true

echo "==> Виртуальное окружение"
sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
sudo chmod 700 "$APP_DIR/venv"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "==> Каталог настроек"
sudo mkdir -p "$ENV_DIR"
sudo chown root:"$APP_USER" "$ENV_DIR"
sudo chmod 750 "$ENV_DIR"

if [ ! -f "$ENV_DIR/app.env" ]; then
    cat <<EOF

⚠️  Файл $ENV_DIR/app.env не создан.

Создайте его вручную:

  sudo nano $ENV_DIR/app.env

Пример содержимого (подставьте свои значения):

  DATABASE_URL=postgresql+psycopg://app_user:ВАШ_ПАРОЛЬ@192.168.64.22:5432/confplus
  SECRET_KEY=$(openssl rand -hex 32)
  ALGORITHM=HS256
  ACCESS_TOKEN_EXPIRE_MINUTES=1440
  DEBUG=false
  HOST=0.0.0.0
  PORT=${APP_PORT}

Затем:

  sudo chown root:$APP_USER $ENV_DIR/app.env
  sudo chmod 640 $ENV_DIR/app.env
  sudo systemctl start conf-plus

EOF
fi

echo "==> Установка systemd-службы"
sudo cp "$APP_DIR/deploy/conf-plus.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable conf-plus

echo "==> Firewall"
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow "${APP_PORT}/tcp"
sudo ufw --force enable

echo "==> Готово"
echo "Не забудьте создать $ENV_DIR/app.env и запустить: sudo systemctl start conf-plus"
