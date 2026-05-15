# 04 — Slim down views.py

**Lens:** Solution Architect **Risk:** Low **Est. LOC delta:** −30 to −45

## Context

`images/views.py` is 200 lines and the longest source file in the project. Two
patterns inflate it without adding clarity:

1. **JSON body parsing is copy-pasted three times.** The identical
   `try: json.loads(request.body or b"{}") except JSONDecodeError: return 400`
   block appears in `images_list` (`views.py:24-29`), `tasks_create`
   (`views.py:64-67`), and `auth_login` (`views.py:108-111`).

2. **Two serializers for one model.** `Image.to_dict()` (`models.py:84-97`)
   serializes an image, but the `gallery` view (`views.py:158-178`) hand-builds a
   *different* dict for the same model — overlapping fields, different shape. A
   reviewer reading `gallery` reasonably asks "why doesn't this use `to_dict()`?"
   and there is no good answer.

Also minor: `login_required_json` (in `utils.py`, moving in task 03) does not use
`functools.wraps`, so decorated views lose their `__name__` / `__doc__`.

## Checklist

### Kill the JSON-parse boilerplate
- [x] Add one small helper — `parse_json_body(request) -> dict | None` (returns
      `None` on malformed JSON), or a `@json_body` decorator that attaches the
      parsed dict and short-circuits with a 400. Put it next to `login_required_json`
      (see task 03's decorator-location decision).
- [x] Replace the three inline blocks in `images_list`, `tasks_create`,
      `auth_login` with the helper.
- [x] Keep the per-field validation (`filename required`, `image_id required`)
      *in the view* — that is real business logic, not boilerplate. Only the
      parse-or-400 step is shared.

### Unify image serialization
- [x] Decide the relationship between `Image.to_dict()` and the `gallery` row dict:
      adopted second-named-helper path — `_gallery_row(img, latest_task)` near views,
      `to_dict()` remains for JSON API. Two named serializers, no anonymous inline dict.
- [x] Whichever path: the `gallery` view should not contain a 15-line
      `rows.append({...})` literal. — `gallery` is now one list-comp over `_gallery_row`.
- [x] This task and **task 05** both touch the gallery query — coordinate so the
      N+1 fix and the serializer change land cleanly together.

### Decorator hygiene
- [x] Add `functools.wraps` to `login_required_json` (and to any new decorator
      from this task / task 03).

## Acceptance

- [x] `views.py` is meaningfully shorter and every view body reads as
      "parse → validate → act → respond" with no plumbing noise.
- [x] There is exactly one place that knows how to turn an `Image` into a dict per
      output format — no anonymous duplicate.
- [x] `make test` green — existing `test_api.py` covers the JSON-error paths
      (`test_create_missing_filename`, etc.); they must still pass unchanged.

## Readability guardrail

`parse_json_body` must be boring and obvious — a reviewer should not have to read
its body to trust it. Do **not** fold validation into it; a magic do-everything
decorator is harder to read than three explicit `if not x: return 400` lines.
The goal is less *noise*, not less *code at any cost*.

## Open questions

- Should the JSON API and the HTML gallery share a serializer at all? They serve
  different consumers. Confirm your preference: unify, or two clearly-named methods.
