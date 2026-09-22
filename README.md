# Конф+ — система управления конференциями

MVP по дисциплине «Методология и практики DevOps». Тема №4 — «Конференция».

## Возможности

- Регистрация / вход (JWT), роли: `participant`, `speaker`, `admin`.
- CRUD конференций (только администратор).
- Регистрация участников на конференцию с проверкой дедлайна.
- Подача, редактирование и модерация докладов (тезисов).
- Оценки докладов (1–5) с отзывом после завершения конференции.
- Приглашения, оргвзносы, бронирование гостиницы, рассылки.
- Отчёты по конференции (администратор).
- Служебный эндпоинт `GET /health` → `{"status":"ok"}`.

## Стек

- Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2
- PostgreSQL 18
- JWT (PyJWT), bcrypt
- Vanilla HTML/CSS/JS SPA

## Установка

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # и отредактируйте DATABASE_URL и SECRET_KEY