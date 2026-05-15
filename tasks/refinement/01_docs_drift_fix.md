# 01 — Fix documentation drift

**Lens:** CTO **Risk:** Low **Est. LOC delta:** ~0 (accuracy, not size)
**Status:** Partially done — do-now subset committed (`a19a4aa`). Unchecked items
below are deferred and ride with tasks 02 / 03 / 06.

## Context

For a portfolio repo, the README is the front door — and right now it lies.
The project layout was flattened to the repo root (commit `f52a34a`) and several
`make` targets were renamed, but the docs were never updated. A reviewer who
clones and follows the Quick Start hits an error on the first command.

Three documents are stale:

- `README.md` — broken Quick Start, wrong repo layout, claims a dependency that
  isn't installed.
- `docs/OBSERVABILITY.md` — describes telemetry wiring that does not exist in the
  code.
- `CLAUDE.md` — wrong branch, wrong phase, references files that don't exist.

## Checklist

### README.md
- [x] Fixed the **Quick start** block: real targets (`make up`, `make smoke`), with
      a short note on what `make up` does (init container: migrate + bucket + seed).
- [x] Fixed the **Repository layout** block: redrawn flat — `images/` and
      `django_thumbnail/` at repo root, `manage.py` at root.
- [x] Fixed the **Stack** table: now says `boto3` → MinIO (no `django-storages`).
- [x] Fixed the layout block's per-file notes: `apps.py` → "Django app config"
      (truthful now; task 02 makes it more specific). `utils.py` kept as-is —
      `utils.py`→`storage.py` rename is tracked in **task 03**.
- [x] Fixed dangling links: `.github/workflows/` and `tasks/refinement/`.

### docs/OBSERVABILITY.md
- [x] Symptom 1 & 3 (`OBSERVABILITY.md:33-42`, `87-97`) say instrumentors are wired
      in `images/apps.py:ready()`. They are **not** — `apps.py` is empty; telemetry
      is initialised in `manage.py` via `setup_otel_for_django_web()`. Rewrote doc
      to match reality (manage.py path, telemetry.py functions).
- [x] Symptom 5 — replaced the stale `Makefile` `dev:` / `worker:` snippet with the
      real `docker-compose.yml` per-process `OTEL_SERVICE_NAME` wiring.
      (Framing-agnostic edit — works whether the doc stays a post-mortem or is
      rewritten current-state.)
- [x] The code samples reference a `setup_telemetry(...)` function that does not
      exist (`telemetry.py` exposes `setup_otel_for_django_web` /
      `setup_otel_for_celery_worker`). Aligned Symptom 3 sample to actual call path.
- [x] README claims "`SimpleSpanProcessor` in dev, `BatchSpanProcessor` in prod"
      — `telemetry.py` only ever uses `SimpleSpanProcessor`. Task 06 kept Simple only;
      updated Symptom 4 to reflect this (noted as future production consideration).

- [x] §0 Current State — branch `refactor/simply`, phase → Refinement, task-file
      pointer → `tasks/refinement/00_overview.md`.
- [x] §0 Known pitfalls — removed the stale `cd django_thumbnail` pitfall.
- [x] §3 Project Structure — redrawn flat; `createbucket.py` corrected. `utils.py`
      kept (rename tracked in task 03).
- [x] §5 Execution Rules — rules 1 / 5 / 6 repointed to `tasks/refinement/`.

## Acceptance

- [ ] Clone-and-follow test: every command in the README Quick Start runs without
      error against a fresh checkout. (user-driven — needs docker stack)
      - [x] Static verification: every `make` target in Quick Start exists in
            `Makefile` (`up`, `smoke`, `up-infra`, `down`, `logs-app`, `logs-infra`);
            port mappings `:8000` / `:16686` present in `docker-compose.yml`; test
            accounts seeded by `init` container.
      - [ ] Runtime verification: deferred to **task 10** §"Follow the README Quick
            Start literally on a fresh clone".
- [x] Every file path and link in all three docs resolves to a real file.
- [x] `docs/OBSERVABILITY.md` describes the code as it actually is.

## Readability guardrail

Docs exist so a human can trust them. Accuracy over polish — a short true README
beats a long aspirational one.

## Open questions

- Do you want `docs/OBSERVABILITY.md` kept as a *post-mortem* (past tense, "here is
  what went wrong") or rewritten as *current-state* documentation? That changes how
  much of it survives task 02.
