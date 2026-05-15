# .claude/SKILLS_POLICY.md — Skills Enablement Policy

> This document governs how the ~36 skills bundled in the
> `python-engineering@jamie-bitflight-skills` plugin should be used (or
> ignored) for this project. The plugin is installed atomically — individual
> skills cannot be removed — so policy is the only available control.
>
> **Baseline**: 2026-05-16  **Branch**: `claude/skills`
>
> **Project stack divergence from plugin defaults** (read first):
> - **No** `src/` layout — Django app-per-folder (`images/`, `django_thumbnail/`)
> - **No** `prek` — pre-commit hook framework is not installed
> - **No** Astral `ty` — type-checking is done with `pyrefly` (Meta's checker, used by `make check`)
> - **Not** a CLI / TUI / PyPI package — this is a Django web app + Celery worker
> - **No** asyncio — synchronous Django views + Celery tasks
> - **No** Typer / Rich — Django views + bootstrap5 templates

---

## 1. Approved (use as conceptual reference)

The skills below are treated as **principle references**. **Do not copy
commands verbatim** — their tooling assumptions (`src/` layout, `prek`,
`ty`, etc.) do not match this project.

| Skill | Use | Caveats |
|---|---|---|
| `python-engineering:python3-web` | Django/Flask/FastAPI design principles | Apply Django sections only; ignore FastAPI/async parts |
| `python-engineering:python3-typing` | Typing strategy (Protocol, TypedDict, TypeIs) | Use with **pyrefly**; skip ty-specific directives |
| `python-engineering:python3-testing` | pytest fixture / coverage strategy | Concepts only; concrete fixtures live in local `pytest-django-patterns` |
| `python-engineering:python3-core` | Python 3.11+ SOLID / design signals | General-purpose, no conflict |
| `python-engineering:python3-tdd` | Five-phase red-green-refactor flow | Concept usable; align tool commands to ruff + pyrefly + pytest |
| `python-engineering:python3-test-design` | Test pyramid / coverage tiering | Pure strategy, no tooling conflict |
| `python-engineering:modernpython` | PEP 585 / 604 / 634 / 673 modern syntax | General-purpose, no conflict |
| `python-engineering:comprehensive-test-review` | Test-suite review checklist | Complements local `code-quality` (former is quality strategy, latter is command execution) |
| `python-engineering:analyze-test-failures` | Test-failure root-cause method | General-purpose, no conflict |
| `python-engineering:test-failure-mindset` | Dual-hypothesis investigation mindset | General-purpose, no conflict |
| `python-engineering:standards-for-python-development` | Shared Python 3.11+ standards | Concepts only; tool commands defer to this project |
| `python-engineering:uv` | uv usage | This project manages dev deps with uv; safe to consult |

**Total: 12 skills**

---

## 2. Disabled

These skills conflict with this project's stack or duplicate local tools.

### 2.1 CLI / TUI family (no CLI/TUI surface in this project)

- `python-engineering:typer`
- `python-engineering:typer-and-rich`
- `python-engineering:textual`
- `python-engineering:python3-cli`
- `python-engineering:designing-ui-for-cli`
- `python-engineering:python-cross-platform-smoothing`

### 2.2 Packaging / publishing family (this is not a PyPI package)

- `python-engineering:hatchling`
- `python-engineering:python3-packaging`
- `python-engineering:pypi-readme-creator`
- `python-engineering:python3-publish-release-pipeline`
- `python-engineering:shebangpython`
- `python-engineering:mkdocs`

### 2.3 Orchestrator / SAM family (conflicts with local task flow)

- `python-engineering:orchestrate`
- `python-engineering:orchestrating-python-development`
- `python-engineering:python3-add-feature`
- `python-engineering:create-feature-task`
- `python-engineering:specialist-skill-routing`

### 2.4 Tool assumptions mismatch this project

- `python-engineering:ty` — this project uses **pyrefly**, not Astral ty
- `python-engineering:stinkysnake` — assumes prek + ty + `src/` layout
- `python-engineering:snakepolish` — downstream of the stinkysnake workflow
- `python-engineering:pre-commit` — this project has no prek / pre-commit framework
- `python-engineering:toml-python` — this project does not need dynamic TOML read/write
- `python-engineering:python3-tools` — aggregator routing to ty / hatchling / prek skills already disabled here

### 2.5 Stack not applicable

- `python-engineering:async-python-patterns` — this project is synchronous Django + Celery, no asyncio
- `python-engineering:python3-data` — no pandas / polars / DuckDB usage
- `python-engineering:python3-stdlib-only` — this project has third-party deps, not airgapped

**Total: 24 skills**

---

## 3. Pending evaluation

Currently empty — all 36 plugin skills (12 approved + 24 disabled) are classified above.
When the plugin ships new skills, place them here first, then promote
to §1 or §2 after evaluation.

---

## 4. Mapping to local tools

| Need | Use local | Why not the python-engineering counterpart |
|---|---|---|
| Code review | `.claude/agents/code-reviewer.md` | `python-engineering`'s review flow depends on `dh:` / `holistic-linting` plugins not installed here |
| Lint / format / type / test bundle | `.claude/skills/code-quality/SKILL.md` | No equivalent plugin skill; **do not** substitute stinkysnake |
| In-edit fast check | `.claude/commands/fix.md` | No equivalent plugin skill |
| Celery patterns | `.claude/skills/celery-patterns/SKILL.md` | python-engineering has no Celery-specific skill |
| Django models / forms / templates | `.claude/skills/django-*/SKILL.md` | python-engineering's `python3-web` is concept-only reference |
| pytest + Django + Factory Boy | `.claude/skills/pytest-django-patterns/SKILL.md` | python-engineering's `python3-testing` is concept-only reference |

---

## 5. Quality-check chain (P4)

| Stage | Entry point | Tool scope |
|---|---|---|
| **Inner loop** (while editing) | `/fix` (local) | `ruff check` + `ruff format --check` + `pyrefly check` — on modified files only |
| **Pre-PR** (before submitting) | `/code-quality apps/` (local) + `code-reviewer` agent | Full sweep: lint + format + types + `pytest` + manual checklist |
| **Disabled** | python-engineering's command-style `lint` / `review` / `debug` / `cleanup` skills | Duplicate local tools; use local versions |

**Rules**:
1. During editing, run only `/fix` — fast, scoped to modified files.
2. Before submitting a PR, run `/code-quality apps/` and trigger the `code-reviewer` agent.
3. CI runs `make check` (pyrefly) + `make test` (pytest) — consistent with local tooling.
4. **Never** substitute `python-engineering:stinkysnake` or `:snakepolish` for the above (their tool assumptions do not match).

---

## 6. Maintenance

- Revisit this list when the python-engineering plugin upgrades (new skills go to §3 pending).
- When adding a new local skill that overlaps an existing python-engineering skill, **record the rationale for choosing the local version** in §4.
- If the django-extensions package is later installed (currently DORMANT — see `.claude/skills/django-extensions/SKILL.md`), the local `django-extensions` skill policy is handled separately — it is unrelated to python-engineering policy.
