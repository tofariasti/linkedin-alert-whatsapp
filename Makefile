.DEFAULT_GOAL := help

PYTHON := .venv/bin/python
export PLAYWRIGHT_BROWSERS_PATH := $(HOME)/.cache/ms-playwright

.PHONY: help run dry-run log db login cron cron-install check test lint format install

help:
	@echo "make run           busca e envia o alerta"
	@echo "make dry-run       busca e grava no SQLite, sem WhatsApp"
	@echo "make log           final do log de hoje"
	@echo "make db            últimas vagas em data/jobs.db"
	@echo "make login         abre o LinkedIn e grava storage_state.json"
	@echo "make cron          mostra o bloco do crontab"
	@echo "make cron-install  grava a linha no crontab do usuário"
	@echo "make check         ruff check e pytest"
	@echo "make test          pytest"
	@echo "make lint          ruff check"
	@echo "make format        ruff format"
	@echo "make install       instala o pacote no .venv e o Chromium"

run:
	$(PYTHON) -m linkedin_alert

dry-run:
	$(PYTHON) -m linkedin_alert --dry-run

log:
	@f=$$(ls -1 logs/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].log 2>/dev/null | sort | tail -n 1); \
	if [ -z "$$f" ]; then echo "nenhum log em logs/"; exit 1; fi; \
	tail -n 40 "$$f"

db:
	sqlite3 -header -column data/jobs.db \
		"SELECT linkedin_id, title, applicants, opened_at, notified_at FROM jobs ORDER BY id DESC LIMIT 20;"

login:
	$(PYTHON) -m linkedin_alert.login

cron:
	$(PYTHON) -m linkedin_alert.cron --print

cron-install:
	$(PYTHON) -m linkedin_alert.cron --install

check: lint test

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

install:
	$(PYTHON) -m pip install -e ".[dev]"
	$(PYTHON) -m playwright install chromium
