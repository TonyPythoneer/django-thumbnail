# Image Thumbnail Worker — Claude Context

## 0. Known Pitfalls

- `django.tasks` has no Redis backend/worker → use Celery
- Never call `manage.py` directly → use `make` commands

---

## 1. Overview

Async thumbnail generation. User uploads image → Django saves to MinIO → Celery task generates a thumbnail → saves back to MinIO → status tracked in PostgreSQL.

---

## 2. Stack

**App** (Django):
- Worker: Celery + Redis broker, `@shared_task`
- Storage: `boto3` → MinIO (no django-storages)
- Frontend: `django-bootstrap5`, 3 pages
- Observability: OpenTelemetry → Jaeger, `telemetry.py`

**Infra**: read `docker-compose.yml`

---

## 3. Project Structure

```
django-thumbnail/
├── CLAUDE.md
├── Makefile                     ← need commands? read this
├── docker-compose.yml
├── Dockerfile.dev
├── pyproject.toml
├── manage.py
├── django_thumbnail/
│   ├── settings/
│   │   ├── base.py              ← env vars & defaults here
│   │   ├── local.py
│   │   └── test.py              ← eager Celery, OTel disabled
│   ├── celery.py
│   ├── telemetry.py
│   ├── urls.py
│   └── wsgi.py / asgi.py
└── images/                      ← main app
    ├── models.py                ← need schema? read this (Image + ImageTask)
    ├── migrations/
    ├── admin.py
    ├── apps.py
    ├── forms.py
    ├── views.py · urls.py
    ├── tasks.py                 ← Celery task: generate_thumbnail
    ├── storage.py               ← S3 helpers (MinIO)
    ├── decorators.py            ← login_required_json
    ├── management/commands/     ← create_bucket, create_test_users, clean_db, clean_bucket, ...
    └── tests/
```

---

## 4. Domain Decisions

- `Image` + `ImageTask` split — **why**: retry → new `ImageTask` record → full history, Image stays clean
- Owner isolation: always `Image.objects.for_user(request.user)` — never expose cross-user data
- No DRF — plain `JsonResponse` + `@login_required`
- Test accounts: `test1@example.com/test1`, `test2@example.com/test2` (permanent, no registration)
- Thumbnail naming: `{stem}_thumbnail{ext}`

---

## 5. Claude Execution Rules

1. **Commands**: read `Makefile`, never construct `manage.py` calls manually
2. **Schema**: read `images/models.py`, don't trust memory
3. **Before implementing**: restate task, ask if ambiguous
4. **No web search** unless user allows
5. **Idempotency**: all Celery tasks safe to retry
6. **Owner isolation**: every queryset scoped to `request.user`
