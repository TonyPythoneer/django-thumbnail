# 09 — Tooling & CI consistency

**Lens:** CTO / QA **Risk:** Low **Est. LOC delta:** +20 to +30 (config)

## Context

The project showcases tooling discipline (`uv`, `ruff`, `pytest-django`,
`pyright`/`django-stubs`) — but the configuration and CI don't fully back that up.

1. **No `[tool.ruff]` config.** `pyproject.toml` has `[tool.pytest.ini_options]`
   but no ruff section at all — ruff runs on pure defaults. No explicit line
   length, no rule selection, no `target-version` (the project pins
   `requires-python = ">=3.14"` but ruff is not told).

2. **CI lints but doesn't format-check or type-check.**
   `ci-app-integration-test.yml:39-45` runs `ruff check` and `pytest` — good. But
   not `ruff format --check` (formatting drift won't fail CI) and not `pyright`
   (`pyrightconfig.json` exists, `django-stubs` + `boto3-stubs` are dev deps, but
   nothing runs the type checker anywhere).

3. **`pytest-cov` installed, doing nothing.** It is in the `dev` group, but
   `pyproject.toml` pytest `addopts` has no `--cov` and there is no coverage
   threshold. A dependency that earns its place or gets dropped.

4. **CI workflow inconsistency.** `ci-app-integration-test.yml` runs
   `uv sync --group dev` (explicit); `ci-smoke-test.yml` runs `uv sync` (implicit).
   Same intent, two spellings — pick one.

5. **`Makefile` ↔ CI ↔ README mismatch.** `make lint` is `ruff check`; `make format`
   is `ruff check --fix` + `ruff format`. There is no `make` target that does what
   CI *should* do (check + format-check + types + test). Adding one keeps "what CI
   runs" reproducible locally — and gives task 01 a real command to put in the
   README.

## Checklist

- [x] **`[tool.ruff]` added.** `target-version = "py314"`, `line-length = 100`,
      `lint.select = ["E", "W", "F", "I", "UP", "B", "SIM"]` with rationale comments.
      Code adjusted to pass: split long `__str__` f-strings, `raise ... from exc`
      on Celery retry, narrowed `Exception` → `ConnectionError` in tests.
- [x] **`ruff format --check` in CI** via `make check` (CI now runs `make check`).
- [x] **Type checker chosen: pyrefly.** Migrated `pyrightconfig.json` → `pyrefly.toml`
      via `pyrefly init`. Dropped `pyright` dev dep. Added type annotations + casts
      in `models.py`/`views.py` so `uv run pyrefly check` passes with 0 errors.
      Zed IDE wired to pyrefly LSP via `.venv/bin/pyrefly lsp` + `ruff` LSP for
      format-on-save (`.zed/settings.json`). **CI step still pending.**
- [x] **`pytest-cov` removed** from dev group (decided against coverage gate for now).
- [x] **CI workflows consistent** — both use `uv sync --group dev` + `setup-uv@v5`
      with `enable-cache: true`.
- [x] **`make check` + `make fix` targets added.** `make check` =
      `ruff check` + `ruff format --check` + `pyrefly check` (CI-safe, read-only).
      `make fix` = `ruff check --fix` + `ruff format`. CI still needs to be pointed
      at `make check` (next item).
- [x] **CI points at `make check` + `make test`** — local and CI run identical commands.
      Hand `make check` to **task 01** for the README.
- [x] **`make migrate` added** (`docker compose exec web python manage.py migrate`).
      Other doc gaps → task 01.

## Acceptance

- [x] `pyproject.toml` has a deliberate, commented `[tool.ruff]` section.
- [x] CI fails on: lint error, format drift, type error, test failure.
- [x] `pytest-cov` removed — no dead dep.
- [x] The two CI workflows install dependencies the same way.
- [x] `make check` reproduces the CI gate locally and passes.

## Readability guardrail

Config is code a human reads to understand "what does this project consider
correct". Keep `[tool.ruff]` minimal and comment *why* for any non-obvious choice.
Don't enable 200 lint rules for show — enable the ones the team will actually keep
green.

## Open questions

- **Type checker: ~~`pyright` or `ty`~~ → `pyrefly`.** Resolved. `pyrefly.toml`
  is now the single source of truth; `pyrightconfig.json` deleted.
- What coverage threshold is realistic *after* task 08? Suggest setting it once
  task 08's tests land, not before.
