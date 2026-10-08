SHELL := /bin/bash
.SHELLFLAGS := -c

VENV_BIN := .venv/Scripts
RUFF := $(VENV_BIN)/ruff.exe
PYTEST := $(VENV_BIN)/pytest.exe
ALEMBIC := $(VENV_BIN)/alembic.exe

DB_NAME := confplus
DB_USER := confplus_user
DB_HOST := localhost
DB_PORT := 5432

.PHONY: help install setup lint format test security migrate backup restore verify clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:
	pip install -r requirements.txt

setup: ## Первоначальная настройка проекта
	python -m venv .venv
	pip install -r requirements.txt
	alembic upgrade head

lint:
	$(RUFF) check app/ tests/

format:
	$(RUFF) format app/ tests/
	$(RUFF) check --fix app/ tests/

test:
	$(PYTEST) --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=40

security:
	$(RUFF) check --select S app/

migrate:
	$(ALEMBIC) upgrade head

backup: ## Создать резервную копию
	@mkdir -p backups
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	pg_dump -h $(DB_HOST) -p $(DB_PORT) -U $(DB_USER) -d $(DB_NAME) -Fc -f backups/$(DB_NAME)_$$TIMESTAMP.dump; \
	echo "Бэкап создан: backups/$(DB_NAME)_$$TIMESTAMP.dump"

restore: ## Восстановить: make restore FILE=backups/xxx.dump
	@if [ -z "$(FILE)" ]; then echo "Использование: make restore FILE=backups/xxx.dump"; exit 1; fi
	dropdb -h $(DB_HOST) -p $(DB_PORT) -U $(DB_USER) --if-exists $(DB_NAME)
	createdb -h $(DB_HOST) -p $(DB_PORT) -U $(DB_USER) $(DB_NAME)
	pg_restore -h $(DB_HOST) -p $(DB_PORT) -U $(DB_USER) -d $(DB_NAME) --no-owner $(FILE)
	@echo "Восстановлено из $(FILE)"

verify: lint test security
	@echo ""
	@echo "=========================================="
	@echo "  Все проверки пройдены успешно!"
	@echo "=========================================="

clean:
	rm -rf htmlcov .coverage .pytest_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
