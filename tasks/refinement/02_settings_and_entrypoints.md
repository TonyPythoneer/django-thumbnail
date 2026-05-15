# 02 — Settings module & process entrypoints

**Lens:** CTO / Solution Architect **Risk:** Low **Est. LOC delta:** ~0 to +5
**Status:** Settings-module default — DONE. Makefile `DJANGO_SETTINGS_TEST` removed — DONE. Telemetry init move — DONE (gated on web-server detection to dodge fork inheritance in the Celery worker parent; see implementation note below).

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

> **Resolved.** Task 06 kept `SimpleSpanProcessor` only — no background BSP thread
> to lose across fork. The remaining concrete risk (gRPC channel inheritance from
> parent to forked child) is sidestepped by *not* initialising telemetry in the
> worker parent at all: `CoreConfig.ready()` (`django_thumbnail/apps.py`) only
> fires `setup_otel_for_django_web()` when `_is_web_server_process()` matches
> (`runserver` / `gunicorn` / `uvicorn`). The worker keeps its per-child
> `worker_process_init` handler. `CoreConfig` is a project-level `AppConfig` —
> domain apps (`images`, etc.) carry no instrumentation responsibility.

- [x] Move telemetry wiring into `django_thumbnail/apps.py` `CoreConfig.ready()` —
      call `setup_otel_for_django_web()` there, gated by `_is_web_server_process()`.
      Added `"django_thumbnail.apps.CoreConfig"` to `INSTALLED_APPS` (first entry so
      OTel init precedes other apps' `ready()`).
- [x] Remove the `setup_otel_for_django_web()` call from `manage.py:12-14`. Keep
      `manage.py` as the stock Django utility.
- [x] Verify the Celery worker path still works: `django_thumbnail/celery.py:12-15`
      wires `setup_otel_for_celery_worker()` via `worker_process_init` — left as-is.
      `ready()` runs in the worker parent too, but `_is_web_server_process()` returns
      False there (argv0 is `celery`, no `runserver`), so no parent-side init —
      worker child stays the sole initialiser.
- [x] Decide whether `wsgi.py` / `asgi.py` need anything: no — `gunicorn` /
      `uvicorn` trigger `django.setup()` → `ready()` → `_is_web_server_process()`
      returns True via `argv0` match. Both files left as stock Django.
- [x] Once done, this is the code that makes `docs/OBSERVABILITY.md` Symptom 1 & 3
      *true* — Symptom 1/3 fix sections rewritten to describe `CoreConfig.ready()`
      (`django_thumbnail/apps.py`) + web-server gate.

## Acceptance

- [x] `python manage.py check` works with no `DJANGO_SETTINGS_MODULE` set in the env.
- [x] `make test` green (test settings disable OTel — confirm still skipped cleanly).
- [ ] `make up` brings up web + worker; a trace still appears in Jaeger for an
      upload → thumbnail flow (manual check, or run `make smoke`).
      *(user-driven — needs docker stack; deferred to task 10.)*
- [x] Running a management command (e.g. `clean_db`) no longer initialises OTel.
      Probed via `django.setup()` with `sys.argv = ['manage.py', 'check']` →
      `trace.get_tracer_provider()` is `ProxyTracerProvider` (no-op). The
      `runserver` argv path yields `TracerProvider` as expected.

## Readability guardrail

The win here is "boot path does the obvious thing." Don't add a settings-loader
abstraction — just make the default point at something real and put telemetry init
in the one Django-blessed hook.

## Open questions

- Do you run anything other than `runserver` in `docker-compose.yml`? If a real
  `gunicorn`/`uvicorn` entrypoint is planned, confirm `apps.py:ready()` is the
  agreed single place so we don't re-scatter init later.
