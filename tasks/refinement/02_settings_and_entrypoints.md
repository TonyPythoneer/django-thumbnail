# 02 — Settings module & process entrypoints

**Lens:** CTO / Solution Architect **Risk:** Low **Est. LOC delta:** ~0 to +5
**Status:** Settings-module default — DONE. Makefile `DJANGO_SETTINGS_TEST` removed — DONE. Telemetry init move — **BLOCKED**, see the note in that subsection.

## Context

Two related fragilities around how the project boots:

1. **`django_thumbnail/settings/__init__.py` is empty**, but `manage.py:10`,
   `wsgi.py:5` and `asgi.py:5` all do
   `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_thumbnail.settings")`.
   That default points at the empty package. It only ever works because the
   environment *always* sets `DJANGO_SETTINGS_MODULE` explicitly (docker-compose
   sets `.local`, pytest sets `.test`). Run `python manage.py` with no env and
   Django loads an empty settings module and crashes. A reviewer reading
   `manage.py` sees a `setdefault` pointing at nothing.

2. **Telemetry init is in the wrong place.** `manage.py:12-14` calls
   `setup_otel_for_django_web()` unconditionally — so it runs for `migrate`,
   `shell`, `clean_db`, *every* management command, not just the web server.
   Meanwhile `wsgi.py` / `asgi.py` (the real production entrypoints) never init
   telemetry at all. The docstring in `telemetry.py:47` says "Call from
   `AppConfig.ready()`" — but `images/apps.py` is empty and nothing calls it from
   there. The intended design (per `telemetry.py` docstrings and
   `docs/OBSERVABILITY.md`) is `apps.py:ready()`; that is the correct Django hook
   and it runs once, after settings load, for server processes.

## Checklist

### Settings module default
- [x] **Option A applied** — `setdefault` default changed to
      `django_thumbnail.settings.local` in `manage.py`, `wsgi.py`, `asgi.py`.
      Verified: `env -u DJANGO_SETTINGS_MODULE python manage.py check` → no issues.
- [x] Confirmed `pyproject.toml` pytest config still pins
      `DJANGO_SETTINGS_MODULE = "django_thumbnail.settings.test"` — left as-is;
      `make test` green (24 passed).
- [x] Removed `DJANGO_SETTINGS_TEST` variable and prefix from `make test:` — redundant
      with `pyproject.toml` ini_options. `make smoke:` keeps `DJANGO_SETTINGS_LOCAL`
      override (different concern — needs `.local` not `.test`).

### Telemetry init location

> **BLOCKED — needs a decision before implementing.**
> Moving `setup_otel_for_django_web()` into `apps.py:ready()` is *not* a safe
> straight move. `ready()` fires during `django.setup()` in **every** process —
> including the Celery **worker parent** and management commands.
>
> Concrete risk to the worker: today the worker parent runs no telemetry, so each
> prefork child's `worker_process_init` → `setup_otel_for_celery_worker()` builds a
> **fresh** `TracerProvider` + OTLP exporter in the child. If `ready()` inits
> telemetry in the parent first, `_setup_provider()` (idempotent) and the
> `BaseInstrumentor` singletons turn the child's re-init into a **no-op** — the
> child then inherits the parent's provider and gRPC exporter **across `fork()`**,
> a known footgun that can silently break worker→Jaeger export. That export is the
> project's headline feature.
>
> Also entangled with **task 06**: `telemetry.py` uses `SimpleSpanProcessor` (no
> background thread), so the "BSP thread not inherited after fork" rationale behind
> the per-child signal may not even apply — the processor choice changes the
> correct answer here.
>
> **Recommendation:** resolve task 06's span-processor decision first, then design
> `ready()` so it does **not** run the web/`django=True` path inside the worker
> (detect the worker, or keep worker init exclusively in the signal). No blind move.

- [ ] Move telemetry wiring into `images/apps.py` `ImagesConfig.ready()` — call
      `setup_otel_for_django_web()` there. This is what the `telemetry.py:47`
      docstring already promises and what `docs/OBSERVABILITY.md` claims.
- [ ] Remove the `setup_otel_for_django_web()` call from `manage.py:12-14`. Keep
      `manage.py` as the stock Django utility.
- [ ] Verify the Celery worker path still works: `django_thumbnail/celery.py:12-15`
      wires `setup_otel_for_celery_worker()` via `worker_process_init` — that is
      correct, leave it. But note `ready()` *also* runs in the worker process when
      Django is set up; confirm `_instrument(django=False)` vs `django=True` don't
      double-instrument. `telemetry.py:_setup_provider` is already idempotent;
      verify `CeleryInstrumentor().instrument()` / `BotocoreInstrumentor()` are too,
      or guard them.
- [ ] Decide whether `wsgi.py` / `asgi.py` need anything: with init in
      `apps.py:ready()`, Django calls it for any entrypoint (runserver, gunicorn,
      uvicorn). That should be sufficient — confirm and document.
- [ ] Once done, this is the code that makes `docs/OBSERVABILITY.md` Symptom 1 & 3
      *true* — hand the corrected behaviour back to **task 01**.

## Acceptance

- [ ] `python manage.py check` works with no `DJANGO_SETTINGS_MODULE` set in the env.
- [ ] `make test` green (test settings disable OTel — confirm still skipped cleanly).
- [ ] `make up` brings up web + worker; a trace still appears in Jaeger for an
      upload → thumbnail flow (manual check, or run `make smoke`).
- [ ] Running a management command (e.g. `clean_db`) no longer initialises OTel.

## Readability guardrail

The win here is "boot path does the obvious thing." Don't add a settings-loader
abstraction — just make the default point at something real and put telemetry init
in the one Django-blessed hook.

## Open questions

- Do you run anything other than `runserver` in `docker-compose.yml`? If a real
  `gunicorn`/`uvicorn` entrypoint is planned, confirm `apps.py:ready()` is the
  agreed single place so we don't re-scatter init later.
