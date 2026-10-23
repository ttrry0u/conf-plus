#!/usr/bin/env bash
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-deployer}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/conf-plus-deploy}"
PUBKEY="${1:-}"

log()  { printf '\033[1;36m[bootstrap]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

if [ "$(id -u)" -ne 0 ]; then
    die "Запустите от root: sudo $0 [PUBLIC_SSH_KEY]"
fi

if command -v apt-get >/dev/null 2>&1; then
    OS_FAMILY="debian"
elif command -v dnf >/dev/null 2>&1; then
    OS_FAMILY="redhat"
else
    die "Поддерживаются только Debian/Ubuntu и RED OS/RHEL."
fi
log "Обнаружена ОС: $OS_FAMILY"

if id "$DEPLOY_USER" >/dev/null 2>&1; then
    log "Пользователь $DEPLOY_USER уже существует"
else
    log "Создаю пользователя $DEPLOY_USER"
    useradd -m -s /bin/bash "$DEPLOY_USER"
fi

if [ -n "$PUBKEY" ]; then
    install -d -m 700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
    AUTH="/home/$DEPLOY_USER/.ssh/authorized_keys"
    touch "$AUTH"; chmod 600 "$AUTH"; chown "$DEPLOY_USER:$DEPLOY_USER" "$AUTH"
    if ! grep -qF "$PUBKEY" "$AUTH"; then
        echo "$PUBKEY" >> "$AUTH"
        log "SSH-ключ добавлен в $AUTH"
    fi
else
    warn "Публичный SSH-ключ не передан"
fi

if command -v docker >/dev/null 2>&1; then
    log "Docker уже установлен"
else
    log "Устанавливаю Docker/Podman..."
    if [ "$OS_FAMILY" = "debian" ]; then
        apt-get update -y && apt-get install -y docker.io docker-compose-plugin curl ca-certificates
    else
        dnf install -y docker-compose curl ca-certificates podman-docker || dnf install -y docker-compose curl ca-certificates
        if systemctl list-unit-files | grep -q docker.service; then
            systemctl enable --now docker
        fi
    fi
fi

# Проверяем наличие любой из команд compose
if ! docker compose version >/dev/null 2>&1 && ! docker-compose version >/dev/null 2>&1; then
    die "docker compose недоступен."
fi

if getent group docker >/dev/null 2>&1; then
    if id -nG "$DEPLOY_USER" | grep -qw docker; then
        log "$DEPLOY_USER уже в группе docker"
    else
        usermod -aG docker "$DEPLOY_USER"
        log "$DEPLOY_USER добавлен в группу docker (нужен релогин)"
    fi
else
    log "Группа 'docker' не найдена (используется Podman). Пропускаем добавление в группу."
fi

install -d -m 750 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$DEPLOY_DIR"
log "Каталог $DEPLOY_DIR готов"

if command -v firewall-cmd >/dev/null 2>&1; then
    log "Открываю порт 8080 в firewalld"
    firewall-cmd --permanent --add-port=8080/tcp || true
    firewall-cmd --reload || true
elif command -v ufw >/dev/null 2>&1; then
    log "Открываю порт 8080 в ufw"
    ufw allow 8080/tcp || true
fi

cat <<EOF

============================================================
Готово! Дальше:
1) Перелогиньтесь как $DEPLOY_USER
2) Скопируйте в $DEPLOY_DIR файл .env.deploy
3) В GitLab задайте SSH_PRIVATE_KEY, DEPLOY_HOST, DEPLOY_USER
============================================================
EOF
