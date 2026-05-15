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
- [ ] Rename `images/utils.py` → `images/storage.py`. Move the S3 classes and
      singletons there.
- [ ] Move `login_required_json` out of the storage file. It is one small
      decorator used only by `images/views.py` — put it in `images/decorators.py`,
      or inline it into `views.py` if you prefer fewer files. Either is fine; pick
      the one that reads cleaner to you.
- [ ] Update all imports: `images/models.py:9`, `images/views.py:15`,
      `images/tasks.py:11`, `images/tests/test_api.py` patch targets
      (`images.utils.public_s3...` → `images.storage.public_s3...`),
      `images/tests/test_tasks.py` patch targets (`images.tasks.internal_s3` is via
      re-import — confirm), `images/tests/test_smoke.py:23`.
- [ ] Note for **task 01**: update `CLAUDE.md` §3 and `README.md` layout to the new
      filename.

### Stop duplicating the boto3 client
- [ ] Give the storage module one place that builds a plain boto3 S3 client (the
      management commands need a raw client, not the `InternalS3` wrapper, because
      they call `head_bucket` / `create_bucket` / `list_objects_v2`). Options:
      expose `internal_s3._client` as a public attribute, or add a small
      `make_s3_client()` factory. Pick one.
- [ ] Rewrite `create_bucket.py` and `clean_bucket.py` to use that single source —
      delete both `cached_property def s3` blocks.

### Lazy client construction
- [ ] Make the `boto3.client(...)` build lazily instead of at import. Simplest
      readable option: a module-level `functools.lru_cache`'d factory, or build the
      client on first use inside the wrapper. The module-level names
      `internal_s3` / `public_s3` can stay as the public API — just don't do real
      I/O-capable object construction at import time.
- [ ] Confirm `images/tests/test_api.py` and `test_tasks.py` still patch correctly
      after this — they patch *methods* (`presign_put`, `internal_s3.upload`, …),
      which should be unaffected, but re-run the suite to be sure.

### Optional readability pass on the class design
- [ ] `_S3BaseClient` configures itself through class attributes
      (`AWS_S3_ENDPOINT_URL = settings....` evaluated in the class body, overridden
      in `PublicS3`). It works, but it is an unusual pattern that makes a reviewer
      pause. **Consider** plain `__init__` parameters or a small frozen config
      object instead. This is a judgement call — only do it if it genuinely reads
      better; skip if it just churns lines.

## Acceptance

- [ ] `images/utils.py` no longer exists; `images/storage.py` holds only storage.
- [ ] No `boto3.client("s3", ...)` call appears more than once in the codebase.
- [ ] Importing `images.models` does not construct a boto3 client (verify: import
      it in a `python -c` with botocore patched, or just confirm construction is
      behind a function/cache).
- [ ] `make test` and `make lint` green. `make smoke` still passes against `make up`.

## Readability guardrail

The point of this task is that a reader opening `storage.py` immediately knows
what they are looking at, and a reader opening a management command sees it *reuse*
the storage layer instead of re-deriving it. Do not over-engineer the lazy-init —
an `lru_cache` factory is plenty; no need for a connection-pool abstraction.

## Open questions

- Decorator placement: separate `images/decorators.py`, or inline into `views.py`?
  (Lean: separate file — it keeps `views.py` focused, and task 04 adds one more
  helper that could live there too.)
