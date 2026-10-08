#!/bin/bash
set -e

echo "=== Виртуальное окружение ==="
python -m venv .venv
source .venv/Scripts/activate

echo "=== Установка зависимостей ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== .env ==="
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Создан .env — отредактируйте его!"
fi

echo "=== Миграции ==="
alembic upgrade head

echo "=== Готово! ==="
