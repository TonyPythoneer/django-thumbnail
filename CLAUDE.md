# Image Thumbnail Worker — Claude Context

## 0. Current State

**Branch**: `refactor/simply`
**Phase**: Refinement — perf, LOC reduction, readability (no behaviour change)
**Task file**: `tasks/refinement/00_overview.md` — read at session start; numbered checklists `01`–`10`, tick as you go

**Known pitfalls**:
- `django.tasks` has no Redis backend/worker → use Celery
- Never call `manage.py` directly → use `make` commands

---

## 1. Overview

Async thumbnail generation. User uploads image → Django saves to MinIO → Celery task generates 300×300 thumbnail → saves back to MinIO → status tracked in PostgreSQL.

---

## 2. Stack

**App** (Django):
- Worker: Celery + Redis broker, `@shared_task`
- Storage: `boto3` → MinIO (no django-storages)
- Frontend: `django-bootstrap5`, 3 pages
- Observability: OpenTelemetry → Jaeger, `telemetry.py`

**Infra**: read `docker-compose.yml`

---

## 3. Project Structure (current)

```
django-thumbnail/
├── CLAUDE.md
├── Makefile                     ← need commands? read this
├── docker-compose.yml
├── Dockerfile.dev
├── pyproject.toml
├── manage.py
├── tasks/
│   └── refinement/              ← refinement plan + numbered checklists 01–10
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
    ├── utils.py                 ← S3 helpers (MinIO)
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

1. **Session start**: read `tasks/refinement/00_overview.md` for the refinement plan + checklist status
2. **Commands**: read `Makefile`, never construct `manage.py` calls manually
3. **Schema**: read `images/models.py`, don't trust memory
4. **Before implementing**: restate task, ask if ambiguous
5. **After each task**: tick the boxes in the relevant `tasks/refinement/NN_*.md`, update §0
6. **Scope change**: update the relevant `tasks/refinement/NN_*.md` first, then implement
7. **No web search** unless user allows
8. **Idempotency**: all Celery tasks safe to retry
9. **Owner isolation**: every queryset scoped to `request.user`
