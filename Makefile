.PHONY: dev migrate makemigrations shell test lint format up-infra down-infra up-app down-app logs-app logs-infra worker test-image-upload clean-db clean-bucket clean-all smoke help

# ============================================================
# Config
# ============================================================
PROJECT          = django_thumbnail
PYTHON_CMD       = uv run python
MANAGE_PY        = $(PYTHON_CMD) manage.py
DJANGO_SETTINGS_LOCAL = DJANGO_SETTINGS_MODULE=$(PROJECT).settings.local
DJANGO_SETTINGS_TEST  = DJANGO_SETTINGS_MODULE=$(PROJECT).settings.test

# Services
API_BASE_URL  = http://localhost:8000
OTEL_ENDPOINT = $(or $(OTEL_EXPORTER_OTLP_ENDPOINT),http://localhost:4317)
JAEGER_UI     = http://localhost:16686
MINIO_CONSOLE = http://localhost:9001

# Celery
CELERY_LOG_LEVEL = info

# OTEL
OTEL_FLAGS = \
	--exporter_otlp_traces_endpoint=$(OTEL_ENDPOINT) \
	--traces_exporter=otlp \
	--service_name=$(PROJECT) \
	--metrics_exporter=none \
	--logs_exporter=none
OTEL_SVC_DJANGO_APP    = 'django-thumbnail-app'
OTEL_SVC_DJANGO_WORKER = 'django-thumbnail-worker'

# ============================================================
# Local dev
# ============================================================
dev:                ## Run Django dev server (local, with OTel)
	$(DJANGO_SETTINGS_LOCAL) OTEL_SERVICE_NAME=$(OTEL_SVC_DJANGO_APP) $(MANAGE_PY) runserver

worker:             ## Run Celery worker (local, with OTel)
	$(DJANGO_SETTINGS_LOCAL) OTEL_SERVICE_NAME=$(OTEL_SVC_DJANGO_WORKER) \
		$(PYTHON_CMD) -m celery -A $(PROJECT) worker -l $(CELERY_LOG_LEVEL)

shell:              ## Django shell
	$(DJANGO_SETTINGS_LOCAL) $(MANAGE_PY) shell

# ============================================================
# Database
# ============================================================
migrate:            ## Apply migrations
	$(MANAGE_PY) migrate

makemigrations:     ## Generate migrations
	$(MANAGE_PY) makemigrations

# ============================================================
# Code quality
# ============================================================
test:               ## Run pytest suite
	$(DJANGO_SETTINGS_TEST) $(PYTHON_CMD) -m pytest

lint:               ## Ruff lint check
	$(PYTHON_CMD) -m ruff check

format:             ## Ruff auto-fix + format
	$(PYTHON_CMD) -m ruff check --fix
	$(PYTHON_CMD) -m ruff format

# ============================================================
# Docker Compose
# ============================================================
up-infra:           ## Start infra only (db, redis, minio, jaeger)
	docker compose up -d

down-infra:         ## Stop infra only (stops app first if running)
	docker compose --profile app down

up-app:             ## Start full stack (infra + init + web + worker)
	docker compose --profile app up -d --build --force-recreate init web worker

down-app:           ## Stop all containers (infra + app)
	docker compose --profile app down

logs-app:           ## Tail app logs (web, worker)
	docker compose logs -f web worker

logs-infra:         ## Tail infra logs (db, redis, minio, jaeger)
	docker compose logs -f db redis minio jaeger

# ============================================================
# Integration / smoke tests
# ============================================================
smoke:              ## Full upload smoke test (requires docker compose up)
	./scripts/smoke_test_image_upload.sh

test-image-upload:  ## Management command smoke test
	$(MANAGE_PY) test_image_upload

# ============================================================
# Cleanup
# ============================================================
clean-db:           ## Wipe database records
	$(MANAGE_PY) clean_db

clean-bucket:       ## Wipe MinIO bucket
	$(MANAGE_PY) clean_bucket

clean-all: clean-db clean-bucket  ## Wipe DB + bucket

# ============================================================
# Help
# ============================================================
help:               ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
