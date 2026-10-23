#!/usr/bin/env bash
# Деплой образа из registry в предэксплуатационное окружение.
# Использование: ./scripts/deploy.sh <version>
# Требования: docker, docker compose, curl; файл .env.deploy в текущем каталоге.
set -euo pipefail
COMPOSE_CMD="docker compose"
if ! docker compose version >/dev/null 2>&1; then
    if docker-compose version >/dev/null 2>&1; then
        COMPOSE_CMD="docker-compose"
    fi
fi


VERSION="${1:?Использование: $0 <version>  (например, v1.0.0 или commit SHA)}"
COMPOSE_FILE="docker-compose.deploy.yml"
STATE_DIR=".deploy-state"

# Подхватить настройки окружения (.env.deploy содержит CI_REGISTRY_IMAGE)
if [ -f .env.deploy ]; then
    set -a
    . ./.env.deploy
    set +a
fi
: "${CI_REGISTRY_IMAGE:?CI_REGISTRY_IMAGE не задан (должен быть в .env.deploy)}"

mkdir -p "$STATE_DIR"

# Опционально — логин в registry, если переданы креды
if [ -n "${CI_REGISTRY_USER:-}" ] && [ -n "${CI_REGISTRY_PASSWORD:-}" ]; then
    REGISTRY_HOST=$(echo "$CI_REGISTRY_IMAGE" | cut -d/ -f1)
    echo "$CI_REGISTRY_PASSWORD" | docker login "$REGISTRY_HOST" -u "$CI_REGISTRY_USER" --password-stdin
fi

# Запомнить текущую версию (может отсутствовать при первом деплое)
CUR=""
[ -f "$STATE_DIR/current_version" ] && CUR=$(cat "$STATE_DIR/current_version")

export APP_VERSION="$VERSION"

echo "==> Pulling $CI_REGISTRY_IMAGE:$VERSION"
$COMPOSE_CMD -f "$COMPOSE_FILE" pull app

echo "==> Restarting services"
$COMPOSE_CMD -f "$COMPOSE_FILE" up -d --remove-orphans

echo "==> Waiting for /nginx-health"
for i in $(seq 1 20); do
    if curl -sf http://localhost:8080/nginx-health >/dev/null 2>&1; then
        echo "OK: nginx alive"
        break
    fi
    sleep 2
    if [ "$i" -eq 20 ]; then
        echo "FAIL: nginx не отвечает на /nginx-health"
        exit 1
    fi
done

echo "==> Waiting for /health"
for i in $(seq 1 20); do
    if curl -sf http://localhost:8080/health | grep -q '"status":"ok"'; then
        echo "OK: /health"
        break
    fi
    sleep 2
    if [ "$i" -eq 20 ]; then
        echo "FAIL: /health не отвечает"
        exit 1
    fi
done

echo "==> Checking /version"
ACTUAL=$(curl -sf http://localhost:8080/version | sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
if [ "$ACTUAL" != "$VERSION" ]; then
    echo "FAIL: ожидалась версия '$VERSION', получена '$ACTUAL'"
    exit 1
fi
echo "OK: /version = $ACTUAL"

# Успех: обновить состояние (previous ← что было до этого, current ← новая)
if [ -n "$CUR" ] && [ "$CUR" != "$VERSION" ]; then
    echo "$CUR" > "$STATE_DIR/previous_version"
fi
echo "$VERSION" > "$STATE_DIR/current_version"

echo "==> Деплой успешен: $VERSION"
