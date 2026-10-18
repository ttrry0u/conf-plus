#!/usr/bin/env bash
set -euo pipefail

echo "==> 1. Проверка пользователя (не root)"
APP_USER=$(docker compose exec -T app whoami | tr -d '\r')
if [ "$APP_USER" == "root" ]; then echo "FAIL: root!"; exit 1; fi
echo "OK: $APP_USER"

echo "==> 2. Проверка, что порт БД не опубликован"
if docker compose ps db | grep -q "0.0.0.0:5432"; then echo "FAIL: DB port open!"; exit 1; fi
echo "OK: DB port closed"

echo "==> 3. Проверка тега latest"
if docker compose config | grep -E "image:.*latest"; then echo "FAIL: latest tag!"; exit 1; fi
echo "OK: no latest"

echo "==> 4. Проверка healthcheck"
if ! docker compose config | grep -q "healthcheck:"; then echo "FAIL: no healthcheck!"; exit 1; fi
echo "OK: healthcheck present"

echo "==> 5. Проверка graceful shutdown"
docker compose stop app
sleep 2
if docker compose ps app | grep -q "Up"; then echo "FAIL: not stopped!"; exit 1; fi
echo "OK: graceful shutdown"
docker compose start app

echo "Все проверки пройдены!"
