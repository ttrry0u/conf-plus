# DEPLOY.md — развертывание «Конф+» в предэксплуатационном окружении (CD)

Документ описывает, как развернуть приложение на **любом** Linux-сервере (Debian/Ubuntu)
из готового образа в registry, без сборки на сервере, и как откатиться на предыдущую версию.

---

## 1. Требования к целевому серверу

| Компонент | Требование |
|---|---|
| ОС | Debian 12 / Ubuntu 22.04+ (Debian-like, apt) |
| RAM / CPU | >= 1 GB RAM, >= 1 vCPU |
| Docker | docker.io + docker compose plugin |
| Порты | 8080 свободен (nginx), 80 **не** обязателен |
| Сеть | сервер доступен по SSH с runner'а GitLab |
| Пользователь | deployer (создаётся скриптом scripts/server-bootstrap.sh) |
| Каталог | /opt/conf-plus-deploy (создаётся скриптом) |

> **Важно:** приложение в контейнере, но образ **не собирается на сервере**. Сервер только
> тянет готовый образ из registry по тегу APP_VERSION. Это требование ЛР6 п.3.

---

## 2. Подготовка целевого сервера (один раз)

### 2.1. Сгенерировать SSH-ключ для CI

На **локальной машине** (не на сервере):

    ssh-keygen -t ed25519 -C "conf-plus-ci" -f ~/.ssh/confplus_ci -N ""

Появятся два файла:
- ~/.ssh/confplus_ci — **приватный** ключ (пойдёт в GitLab CI/CD -> SSH_PRIVATE_KEY);
- ~/.ssh/confplus_ci.pub — **публичный** ключ (передаётся в bootstrap-скрипт).

### 2.2. Запустить bootstrap на сервере

Скопируйте на сервер scripts/server-bootstrap.sh и запустите от sudo:

    # на сервере
    sudo ./scripts/server-bootstrap.sh "$(cat confplus_ci.pub)"

Скрипт идемпотентен (можно запускать повторно). Он:
- создаст пользователя deployer;
- положит публичный ключ в ~deployer/.ssh/authorized_keys;
- поставит Docker + compose plugin (если ещё нет);
- добавит deployer в группу docker;
- создаст /opt/conf-plus-deploy;
- проверит, что порт 8080 свободен.

После — **перелогиньтесь** под deployer, чтобы применилась группа docker:

    ssh deployer@<IP_СЕРВЕРА>
    docker ps    # должно работать без sudo

### 2.3. Разложить файлы деплоя

На сервере, в /opt/conf-plus-deploy, должны лежать:
- docker-compose.deploy.yml
- nginx.deploy.conf
- scripts/deploy.sh
- scripts/rollback.sh
- .env.deploy (создать из .env.deploy.example)

deploy-job в CI сам копирует docker-compose.deploy.yml, nginx.deploy.conf и скрипты
через scp при каждом деплое. А .env.deploy (с секретами) **остаётся на сервере** и
не коммитится в репозиторий — это требование ЛР6 п.4.

---

## 3. Настройка .env.deploy на сервере

    cd /opt/conf-plus-deploy
    cp /path/to/repo/.env.deploy.example .env.deploy
    chmod 600 .env.deploy
    nano .env.deploy

Заполните реальными значениями:
- POSTGRES_PASSWORD: сильный пароль (например, openssl rand -hex 16)
- SECRET_KEY: openssl rand -hex 32
- DATABASE_URL: postgresql+psycopg://confplus_user:<пароль>@db:5432/confplus
- CI_REGISTRY_IMAGE: полный путь к образу, напр. registry.example.com/my_devops_group/conf-plus

> **Не коммитьте .env.deploy в Git.** Он уже в .gitignore.

---

## 4. Настройка GitLab CI/CD Variables

В GitLab: **Settings -> CI/CD -> Variables**. Создайте (тип Variable, защищённые — по желанию):

| Имя | Значение | Masked? |
|---|---|---|
| SSH_PRIVATE_KEY | содержимое ~/.ssh/confplus_ci (приватный ключ) | Да |
| DEPLOY_HOST | IP или DNS сервера (напр. 192.168.1.50) | Нет |
| DEPLOY_USER | deployer | Нет |

CI_REGISTRY_USER, CI_REGISTRY_PASSWORD, CI_REGISTRY_IMAGE GitLab обычно задаёт
автоматически (они доступны в job'ах из коробки).

---

## 5. Первый деплой

### 5.1. Через GitLab UI (ручной запуск)
1. Откройте **CI/CD -> Pipelines** для ветки/тега, который хотите развернуть.
2. Дождитесь, что стадии lint ... build ... scan-image ... publish зелёные.
3. На стадии deploy нажмите ▶ у deploy-job (он when: manual).
4. Дождитесь verify-deploy-job — он проверит /nginx-health, /health, /version и основной сценарий.
5. Если всё зелёное — релиз принят.

### 5.2. Проверка вручную с сервера
    curl http://localhost:8080/nginx-health    # ok
    curl http://localhost:8080/health          # {"status":"ok"}
    curl http://localhost:8080/version         # {"version":"v1.0.0",...}

---

## 6. Деплой конкретного тега

    # на сервере, в /opt/conf-plus-deploy
    ./scripts/deploy.sh v1.2.3

Скрипт:
1. тянет образ CI_REGISTRY_IMAGE:v1.2.3;
2. перезапускает docker compose;
3. проверяет /nginx-health, /health, /version == v1.2.3;
4. сохраняет предыдущую версию в .deploy-state/previous_version;
5. **если проверка не прошла — завершается с ошибкой** (релиз не принят).

---

## 7. Откат на предыдущую версию

### Вариант A — автоматически к предыдущей
    ./scripts/rollback.sh

### Вариант B — к конкретной версии
    ./scripts/rollback.sh v1.2.2

### Вариант C — из GitLab UI
На стадии deploy нажмите ▶ у rollback-job. Можно задать версию через переменную
ROLLBACK_TO в **CI/CD -> Variables** (или через **Run pipeline -> Variables**).

---

## 8. Troubleshooting

| Симптом | Причина | Решение |
|---|---|---|
| FAIL: /health не отвечает | приложение не поднялось / БД не готова | docker compose -f docker-compose.deploy.yml logs app |
| FAIL: версия не совпадает | образ собран с другим APP_VERSION | проверить build-job (передаётся ли --build-arg) |
| pull access denied | нет логина в registry | задать CI_REGISTRY_USER / CI_REGISTRY_PASSWORD |
| permission denied (publickey) | публичный ключ не в authorized_keys | перезапустить server-bootstrap.sh |
| port 8080 already in use | занят другим сервисом | остановить сервис или поменять порт |
| docker: command not found | группа docker не применилась | перелогиниться под deployer |

---

## 9. Чек-лист переносимости (для нового члена команды)

- [ ] Поднять Debian/Ubuntu VM
- [ ] Запустить sudo ./scripts/server-bootstrap.sh "<public-key>"
- [ ] Перелогиниться как deployer, проверить docker ps
- [ ] Создать /opt/conf-plus-deploy/.env.deploy из .env.deploy.example
- [ ] В GitLab: задать SSH_PRIVATE_KEY, DEPLOY_HOST, DEPLOY_USER
- [ ] Запустить пайплайн -> deploy-job -> verify-deploy-job
- [ ] Проверить curl http://<host>:8080/version
- [ ] Попробовать rollback-job (должен вернуть предыдущую версию)
