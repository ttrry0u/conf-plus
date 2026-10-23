#!/usr/bin/env bash
# Откат к предыдущей (или указанной) версии.
# Использование:
#   ./scripts/rollback.sh            # откат к .deploy-state/previous_version
#   ./scripts/rollback.sh <version>  # откат к конкретной версии
set -euo pipefail
COMPOSE_CMD="docker compose"
if ! docker compose version >/dev/null 2>&1; then
    if docker-compose version >/dev/null 2>&1; then
        COMPOSE_CMD="docker-compose"
    fi
fi


COMPOSE_FILE="docker-compose.deploy.yml"
STATE_DIR=".deploy-state"

if [ -f .env.deploy ]; then
    set -a
    . ./.env.deploy
    set +a
fi
: "${CI_REGISTRY_IMAGE:?CI_REGISTRY_IMAGE не задан (должен быть в .env.deploy)}"

if [ -n "${1:-}" ]; then
    TARGET="$1"
else
    if [ ! -f "$STATE_DIR/previous_version" ]; then
        echo "FAIL: нет $STATE_DIR/previous_version — нечего откатывать."
        echo "      Укажите версию явно: $0 <version>"
        exit 1
    fi
    TARGET=$(cat "$STATE_DIR/previous_version")
fi

CUR=""
[ -f "$STATE_DIR/current_version" ] && CUR=$(cat "$STATE_DIR/current_version")

if [ "$TARGET" = "$CUR" ]; then
    echo "Целевая версия совпадает с текущей ($TARGET) — откат не требуется."
    exit 0
fi

echo "==> Откат с '$CUR' на '$TARGET'"

if [ -n "${CI_REGISTRY_USER:-}" ] && [ -n "${CI_REGISTRY_PASSWORD:-}" ]; then
    REGISTRY_HOST=$(echo "$CI_REGISTRY_IMAGE" | cut -d/ -f1)
    echo "$CI_REGISTRY_PASSWORD" | docker login "$REGISTRY_HOST" -u "$CI_REGISTRY_USER" --password-stdin
fi

export APP_VERSION="$TARGET"
$COMPOSE_CMD -f "$COMPOSE_FILE" pull app
$COMPOSE_CMD -f "$COMPOSE_FILE" up -d --force-recreate --remove-orphans

echo "==> Проверка после отката"
for i in $(seq 1 60); do
    if curl -sf http://localhost:8080/health >/dev/null; then
        echo "OK: /health"
        break
    fi
    sleep 2
    if [ "$i" -eq 60 ]; then
        echo "FAIL: /health не отвечает после отката"
        exit 1
    fi
done

ACTUAL=$(curl -sf http://localhost:8080/version | sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
if [ "$ACTUAL" != "$TARGET" ]; then
    echo "FAIL: ожидалась версия '$TARGET', получена '$ACTUAL'"
    exit 1
fi

# Обновляем состояние: current ← TARGET, previous ← что было (CUR)
if [ -n "$CUR" ]; then
    echo "$CUR" > "$STATE_DIR/previous_version"
fi
echo "$TARGET" > "$STATE_DIR/current_version"

echo "==> Откат успешен: $TARGET"
