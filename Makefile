.PHONY: dev migrate makemigrations shell test lint format up down logs worker test-image-upload clean-db clean-bucket clean-all

# Config
PROJECT = django_thumbnail
PYTHON_CMD = uv run python
MANAGE_PY = $(PYTHON_CMD) $(PROJECT)/manage.py
DJANGO_SETTINGS_LOCAL = DJANGO_SETTINGS_MODULE=$(PROJECT).settings.local
DJANGO_SETTINGS_TEST = DJANGO_SETTINGS_MODULE=$(PROJECT).settings.test

# Services
API_BASE_URL = http://localhost:8000
OTEL_ENDPOINT = $(or $(OTEL_EXPORTER_OTLP_ENDPOINT),http://localhost:4317)
JAEGER_UI = http://localhost:16686
MINIO_CONSOLE = http://localhost:9001

# Celery
CELERY_APP = $(PROJECT)
CELERY_LOG_LEVEL = info

# OTEL
OTEL_FLAGS = \
	--exporter_otlp_traces_endpoint=$(OTEL_ENDPOINT) \
	--traces_exporter=otlp \
	--service_name=$(PROJECT) \
	--metrics_exporter=none \
	--logs_exporter=none

dev:
	$(DJANGO_SETTINGS_LOCAL) OTEL_SERVICE_NAME=$(PROJECT)-app $(MANAGE_PY) runserver

migrate:
	$(MANAGE_PY) migrate

makemigrations:
	$(MANAGE_PY) makemigrations

shell:
	$(MANAGE_PY) shell

test:
	$(DJANGO_SETTINGS_TEST) $(PYTHON_CMD) -m pytest

lint:
	$(PYTHON_CMD) -m ruff check

format:
	$(PYTHON_CMD) -m ruff check --fix
	$(PYTHON_CMD) -m ruff format

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

worker:
	cd $(PROJECT) && $(DJANGO_SETTINGS_LOCAL) OTEL_SERVICE_NAME=$(PROJECT)-worker \
		$(PYTHON_CMD) -m celery -A $(CELERY_APP) worker -l $(CELERY_LOG_LEVEL)

test-image-upload:
	$(MANAGE_PY) test_image_upload

clean-db:
	$(MANAGE_PY) clean_db

clean-bucket:
	$(MANAGE_PY) clean_bucket

clean-all: clean-db clean-bucket
