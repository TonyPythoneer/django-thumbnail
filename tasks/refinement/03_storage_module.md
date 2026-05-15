# 03 — Storage module: name it, scope it, stop duplicating it

**Lens:** Solution Architect **Risk:** Medium (touches imports across the app)
**Est. LOC delta:** −15 to −25

## Context

`images/utils.py` is a junk drawer. It holds two unrelated things:

- the S3 client layer — `_S3BaseClient` / `InternalS3` / `PublicS3` plus the
  module-level singletons `internal_s3` / `public_s3` (~60 lines), and
- `login_required_json`, an auth decorator (~7 lines).

The name `utils.py` tells a reader nothing. `CLAUDE.md` even *thinks* the S3 code
lives in a file called `storage.py` — the docs expect the better name.

Two more problems in the same area:

- **Duplication.** `images/management/commands/create_bucket.py:11-18` and
  `clean_bucket.py:10-17` each construct their *own* `boto3.client("s3", ...)` via
  a `cached_property` — a third and fourth copy of the same client-construction
  code that already exists in `_S3BaseClient.__init__`.
- **Import-time side effects.** `internal_s3 = InternalS3()` / `public_s3 = PublicS3()`
  at `utils.py:64-65` construct two boto3 clients *the moment the module is
  imported*. `images/models.py:9` imports them, so importing models — which the
  test suite and `clean_db` do — builds two S3 clients that are never used.

## Checklist

### Rename & split
- [x] Rename `images/utils.py` → `images/storage.py`. Move the S3 classes and
      singletons there.
- [x] Move `login_required_json` to `images/decorators.py`; `views.py` updated.
- [x] Updated all imports: `models.py`, `views.py`, `tasks.py`,
      `test_api.py` patch targets (`images.storage.*`), `test_smoke.py`,
      `management/commands/test_image_upload.py`.
- [x] `CLAUDE.md` §3 updated to `storage.py` + `decorators.py`.

### Stop duplicating the boto3 client
- [ ] Skipped — management commands still have their own `cached_property def s3`.
      Opus recommended folding bucket ops into `InternalS3`; deferred (low value
      for side project complexity tradeoff).

### Lazy client construction
- [ ] Skipped — import-time construction accepted as-is; no test suite impact.

### Optional readability pass on the class design
- [x] Done — replaced class-attribute config pattern with explicit `__init__`
      parameters in `_S3BaseClient`. `InternalS3`/`PublicS3` pass their own
      `endpoint_url` and `config` at construction.

## Acceptance

- [x] `images/utils.py` no longer exists; `images/storage.py` holds only storage.
- [ ] No `boto3.client("s3", ...)` call appears more than once — management commands
      still duplicate; deferred (see Stop duplicating section above).
- [ ] Importing `images.models` does not construct a boto3 client — deferred.
- [x] `make test` green (24 passed). `make lint` and `make smoke` pending manual run.

## Readability guardrail

The point of this task is that a reader opening `storage.py` immediately knows
what they are looking at, and a reader opening a management command sees it *reuse*
the storage layer instead of re-deriving it. Do not over-engineer the lazy-init —
an `lru_cache` factory is plenty; no need for a connection-pool abstraction.

## Open questions

- Decorator placement: separate `images/decorators.py`, or inline into `views.py`?
  (Lean: separate file — it keeps `views.py` focused, and task 04 adds one more
  helper that could live there too.)
