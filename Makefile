.PHONY: dev migrate makemigrations shell test up down logs worker

MANAGE = uv run python django_thumbnail/manage.py

dev:
	$(MANAGE) runserver

migrate:
	$(MANAGE) migrate

makemigrations:
	$(MANAGE) makemigrations

shell:
	$(MANAGE) shell

test:
	uv run pytest

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

worker:
	uv run celery -A django_thumbnail worker -l info
