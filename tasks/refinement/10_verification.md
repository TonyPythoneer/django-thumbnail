# 10 — Final verification

**Lens:** QA **Risk:** — **Est. LOC delta:** 0

## Context

The closing gate. After tasks 01–09, prove the refinement actually achieved its
three goals — **better performance, fewer lines, no readability regression** — and
that nothing broke on the way. Do this as one deliberate pass, not piecemeal.

## Checklist

### The suite & gates
- [x] `make test` — green (38 passed).
- [x] `make lint` — clean (`ruff check`).
- [x] `ruff format --check` — clean (no drift; 41 files already formatted).
- [x] Type check — clean (`pyrefly`, 0 errors, 3 suppressed). Note: task 09 chose
      `pyrefly` over the original `pyright` / `ty` mention.
- [x] Full-gate target reproduced locally: `make check` = ruff check + ruff
      format-check + pyrefly check. Task 09 wired CI to `make check`.
      (No separate `make ci` target — `make check` + `make test` is the gate.)
- [ ] `make up` then `make smoke` — green against the real docker-compose stack.
      *(user-driven — requires docker stack.)*

### Behaviour still works (manual) — user-driven
- [ ] `make up`, open `http://localhost:8000`, log in as `test1@example.com`.
- [ ] Upload an image → it appears in the gallery → status moves
      `pending → processing → done` → a thumbnail renders.
- [ ] Confirm the thumbnail is the **intended size** (task 06) — not 20px.
- [ ] Delete an image → it disappears and is gone from storage.
- [ ] Open Jaeger (`http://localhost:16686`) → one trace spans app + worker + S3
      with correct parent/child nesting (the project's headline feature still
      works after the task 02 telemetry-init move).

### Goal: performance
- [x] Re-check the queries: `gallery` and `images_list` GET are flat (constant
      query count) regardless of image count. Verified by task 08 tests
      (`test_gallery_query_count_constant`, `test_list_query_count_constant`,
      `test_latest_task_uses_prefetch_cache`) — all pass at 4 queries with 5
      images + tasks.
- [~] Confirm importing `images.models` no longer constructs a boto3 client at
      import time. *Deferred from task 03.* `storage.py:62-63` still constructs
      the `InternalS3()` / `PublicS3()` singletons at module load, which `cached_property`
      then materialises on first attribute touch. Task 03 explicitly accepted this
      as-is; no test suite impact. Marked deferred there → consistent here.

### Goal: fewer lines
- [x] Measured against merge-base `d6ac5ce`: production code 1,595 → 1,523
      (**−72, −4.5%**); tests 514 → 651 (+137, task 08). Recorded in
      `00_overview.md` "Outcome" section. Below the ~15% aspiration; rationale
      noted there (some wins were clarity-positive but line-neutral).
- [x] No file got *longer* without a good reason. Two production files grew:
      `django_thumbnail/apps.py` (+23, new `CoreConfig` for project-level OTel hook,
      task 02) and `images/decorators.py` (+21, `login_required_json` to remove
      auth-decorator duplication, task 04). Test files grew by design (task 08).

### Goal: readability (the real one)
- [x] Cold re-read of `views.py`, `tasks.py`, `models.py`, `storage.py`. Each
      function reads top-to-bottom as a small story. No clever density introduced —
      `next(iter(self.tasks.all()), None)` (latest_task) is the only edge of
      "idiom over plain" and is documented in task 05's guardrail.
- [x] No new helper exists without an obvious, self-explaining name. Audit:
      `_fmt_ts`, `_gallery_row`, `_is_web_server_process`, `_S3BaseClient` /
      `InternalS3` / `PublicS3`, `_make_thumbnail` / `_process_thumbnail`,
      `login_required_json` — all self-describing.
- [ ] Follow the README Quick Start **literally** on a fresh clone.
      *Static portion verified in task 01* (every `make` target + URL resolves).
      *Runtime portion user-driven — needs docker stack.*
- [x] `CLAUDE.md` §0 reflects reality: branch `refactor/simply`, phase "Refinement
      closing", LOC outcome, pointer to `00_overview.md`.

### Close out
- [x] Every box in `01`–`09` ticked or marked deferred with rationale. Deferred:
      task 03 import-time S3 client construction; task 05 Debug Toolbar manual
      check (superseded by task 08 automated query-count tests).
- [x] `00_overview.md` updated with LOC table and one-line outcome summary
      under the new "Outcome (2026-05-16)" section.
- [ ] Confirm the working tree is in reviewable shape — coherent commits, one
      logical change each (per the global guardrail). **Do not commit without
      explicit approval.** *(Auditing this commit after user approves.)*

## Acceptance

- [x] All automated gates green (`make test` + `make check`). End-to-end docker
      gate (`make up` + `make smoke` + browser walkthrough + Jaeger) deferred to
      the user.
- [x] Performance goals verified — programmatic query-count tests (task 08) prove
      `gallery` and `images_list` stay at 4 queries regardless of image count.
- [x] LOC delta measured (`d6ac5ce` → HEAD): production −72 (−4.5%), tests +137.
      Recorded in `00_overview.md`.
- [x] Cold re-read confirms readability is improved — fewer one-off helpers
      duplicated across files, single home for OTel init, decorator dedup,
      `_fmt_ts` shared, lazy imports reduced from 2 → 1. No file got cleverer.

## Readability guardrail

This task *is* the readability guardrail. If the honest answer to "is this easier
to review now?" is no for any file, the refinement isn't done for that file —
go back, don't rationalise.
