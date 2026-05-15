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

- [ ] **Add `[tool.ruff]` to `pyproject.toml`.** At minimum: `target-version`
      matching the Python pin, an explicit `line-length`, and a deliberate
      `[tool.ruff.lint] select` (the current code already passes — capture the
      intended rule set rather than relying on defaults that can shift between
      ruff releases). Keep it small and commented; this is config a human reads.
- [ ] **Add `ruff format --check` to CI** (`ci-app-integration-test.yml`) as a step
      alongside `ruff check`.
- [ ] **Add a type-check step to CI.** Run `pyright` (or `ty` — see open question)
      against the project. Expect to fix a few annotations; budget for it. If the
      type checker surfaces real issues, fold the fixes into the relevant earlier
      task rather than piling them here.
- [ ] **Decide `pytest-cov`'s fate.** Either:
      - wire it up — add `--cov=images --cov=django_thumbnail` to `addopts` and a
        `--cov-fail-under=N` threshold (pick a realistic `N` given task 08's new
        tests), or
      - drop it from the `dev` group if you don't want a coverage gate.
- [ ] **Make the two CI workflows consistent** — same `uv sync` invocation,
      same step style.
- [ ] **Add a `make ci` (or `make check`) target** that runs the full gate locally:
      `ruff check` + `ruff format --check` + type check + `pytest`. Point CI at the
      same commands so local and CI cannot drift. Hand the target name to **task 01**
      for the README.
- [ ] **Add a `make migrate` target** (and any other target the README/docs assume
      to exist) — or, in task 01, rewrite the docs to the real targets. Don't leave
      the gap; close it on one side.

## Acceptance

- [ ] `pyproject.toml` has a deliberate, commented `[tool.ruff]` section.
- [ ] CI fails on: lint error, format drift, type error, test failure.
- [ ] `pytest-cov` is either enforced with a threshold or removed — no dead dep.
- [ ] The two CI workflows install dependencies the same way.
- [ ] `make ci` reproduces the CI gate locally and passes.

## Readability guardrail

Config is code a human reads to understand "what does this project consider
correct". Keep `[tool.ruff]` minimal and comment *why* for any non-obvious choice.
Don't enable 200 lint rules for show — enable the ones the team will actually keep
green.

## Open questions

- **Type checker: `pyright` or `ty`?** `pyrightconfig.json` already exists, so
  `pyright` is the path of least resistance. But the project's skills/tooling lean
  Astral (`uv`, `ruff`) — `ty` (Astral's checker) would be consistent. Pick one and
  delete the other's config so there's no ambiguity.
- What coverage threshold is realistic *after* task 08? Suggest setting it once
  task 08's tests land, not before.
