.PHONY: shell test smoke lint format up-infra up down logs-app logs-infra test-image-upload clean-db clean-bucket clean-all help

# ============================================================
# Config
# ============================================================
PROJECT          = django_thumbnail
PYTHON_CMD       = uv run python
DJANGO_SETTINGS_LOCAL = DJANGO_SETTINGS_MODULE=$(PROJECT).settings.local

# ============================================================
# Django shell (inside web container)
# ============================================================
shell:              ## Django shell (requires: make up)
	docker compose exec web python manage.py shell

# ============================================================
# Code quality
# ============================================================
test:               ## Run pytest suite in local host
	$(PYTHON_CMD) -m pytest

smoke:              ## Smoke test docker-compose stack from host (requires: make up)
	$(DJANGO_SETTINGS_LOCAL) $(PYTHON_CMD) -m pytest -m smoke -v

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

up:                 ## Start full stack (infra + init + web + worker)
	docker compose --profile app up -d --build --force-recreate init web worker

down:               ## Stop all containers (infra + app)
	docker compose --profile app down

logs-app:           ## Tail app logs (web, worker)
	docker compose logs -f web worker

logs-infra:         ## Tail infra logs (db, redis, minio, jaeger)
	docker compose logs -f db redis minio jaeger

# ============================================================
# Cleanup
# ============================================================
clean-db:           ## Wipe database records
	docker compose exec web python manage.py clean_db

clean-bucket:       ## Wipe MinIO bucket
	docker compose exec web python manage.py clean_bucket

clean-all: clean-db clean-bucket  ## Wipe DB + bucket

# ============================================================
# Help
# ============================================================
help:               ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
