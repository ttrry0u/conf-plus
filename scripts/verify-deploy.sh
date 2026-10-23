#!/usr/bin/env bash
set -euo pipefail

# В CI переменные CI_COMMIT_TAG и CI_COMMIT_SHA передаются автоматически
APP_VERSION="${CI_COMMIT_TAG:-$CI_COMMIT_SHA}"
DEPLOY_URL="http://${DEPLOY_HOST}:8080"

echo "==> Проверка /nginx-health"
curl -sf "${DEPLOY_URL}/nginx-health"

echo "==> Проверка /health"
curl -sf "${DEPLOY_URL}/health" | grep -q '"status":"ok"'
echo "OK: /health"

echo "==> Проверка /version"
ACTUAL=$(curl -sf "${DEPLOY_URL}/version" | sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
echo "Ожидаемая версия: $APP_VERSION, Фактическая: $ACTUAL"
if [ "$ACTUAL" != "$APP_VERSION" ]; then
    echo "FAIL: версия не совпадает!"
    exit 1
fi
echo "OK: /version = $ACTUAL"

echo "==> Проверка основного сценария (регистрация)"
EMAIL="ci-$(date +%s)@example.com"
curl -sf -X POST "${DEPLOY_URL}/api/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"full_name\":\"CI Test\",\"email\":\"$EMAIL\",\"password\":\"testpass123\",\"role\":\"participant\",\"consent_152fz\":true}" \
  | grep -q "access_token"
echo "OK: основной сценарий работает"

echo "Все проверки релиза пройдены успешно!"
