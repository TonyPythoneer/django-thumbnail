# Image Thumbnail Worker — Claude Context

## 0. Current State

**Branch**: `ty/thumbnail-worker-setup`
**Phase**: 3 ⬜ — next: 3.1 telemetry.py OTel setup
**Task file**: `tasks/THUMBNAIL_WORKER.md` — read at session start, update as tasks complete

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
- Storage: `django-storages[s3]` + boto3 → MinIO
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
├── pyproject.toml
├── tasks/
│   └── THUMBNAIL_WORKER.md     ← task status & architecture decisions
├── django_thumbnail/
│   ├── django_thumbnail/
│   │   ├── settings/
│   │   │   ├── base.py          ← env vars & defaults here
│   │   │   ├── local.py
│   │   │   └── test.py          ← InMemoryStorage, CELERY_TASK_ALWAYS_EAGER
│   │   ├── celery.py
│   │   └── urls.py
│   └── images/                  ← main app
│       ├── models.py            ← need schema? read this (Image + ImageTask)
│       ├── migrations/          ✅
│       ├── admin.py             ← ✅ 1.3
│       ├── views.py
│       ├── urls.py
│       ├── tasks.py             ← Celery task: generate_thumbnail (⬜ 2.1)
│       ├── storage.py           ← MinIO helpers
│       ├── management/commands/
│       │   ├── create_test_users.py    ← ✅ 1.4
│       │   ├── generate_placeholders.py ← ✅ 1.5
│       │   └── createbucket.py         ← ✅ 1.6
│       └── tests/
```

---

## 4. Domain Decisions

- `Image` + `ImageTask` split — **why**: retry → new `ImageTask` record → full history, Image stays clean
- Owner isolation: always `Image.objects.for_user(request.user)` — never expose cross-user data
- No DRF — plain `JsonResponse` + `@login_required`
- Test accounts: `test1@example.com/test1`, `test2@example.com/test2` (permanent, no registration)
- Thumbnail naming: `{stem}_thumbnail{ext}`, 300×300 preserving aspect ratio

---

## 5. Claude Execution Rules

1. **Session start**: read `tasks/THUMBNAIL_WORKER.md` for phase + task status
2. **Commands**: read `Makefile`, never construct `manage.py` calls manually
3. **Schema**: read `images/models.py`, don't trust memory
4. **Before implementing**: restate task, ask if ambiguous
5. **After each task**: mark complete in `tasks/THUMBNAIL_WORKER.md`, update §0
6. **Scope change**: update `tasks/THUMBNAIL_WORKER.md` first, then implement
7. **No web search** unless user allows
8. **Idempotency**: all Celery tasks safe to retry
9. **Owner isolation**: every queryset scoped to `request.user`
