# Assessment: #5 Project skeleton: FastAPI app with /health so CI checks run for real

- **Issue:** #5
- **Author:** Claude Code agent session (owner's main chat) · **Date:** 2026-11-26
- **Recommendation:** Approve (option A) · **Suggested priority:** High
- **Size:** S

## 1. Problem and users
The repository has no application code, so every `make` target skips with "No pyproject.toml yet". CI's `ci` and `dependencies` checks pass without checking anything. The idea is the smallest real app: a `pyproject.toml` (uv, ruff, mypy, pytest), a committed `uv.lock`, an `app/` package with `GET /health`, and one test. It's for the owner and the agents: every later feature PR builds on it, and from then on CI really checks code.

## 2. Value
- It unblocks the first product priority in `PRODUCT.md`, "Create a verification request and its client link", which needs an app to live in.
- It turns the quality gates on. Until then, a green `ci` check means nothing.
- `GET /health` also gives the `make smoke` target the health endpoint its `TODO(setup)` asks for, once a deploy target exists.
- Evidence: owner request during HAAM setup. There's no user-facing value on its own.

## 3. Options
| Option | Description | Size | Pros | Cons |
|---|---|---|---|---|
| A | Minimal skeleton as the issue describes it: `pyproject.toml` with tool settings, `uv.lock`, `app/main.py` with `GET /health`, `tests/test_health.py`; update `ARCHITECTURE.md` | S | Small and easy to review and test; activates every gate; no business decisions baked in | Little to show a user |
| B | Skeleton plus groundwork for priority 1 (settings module, request/response models, a stub router for verification requests) | M | Faster start on the first feature | Mixes structure with product decisions not yet specified; touches protected patterns (`**/models/**`, and `**/verification/**` if named that way), so it needs code review; bigger PR |
| Do nothing | Keep the guarded no-op `make` targets | – | No work | CI stays meaningless; the first feature PR must also set up the project and gets bigger and riskier |

## 4. Technical feasibility
- **Modules affected (new):** `pyproject.toml`, `uv.lock`, `app/__init__.py`, `app/main.py`, `tests/test_health.py`. Update `docs/product/ARCHITECTURE.md` (layout, modules, testing, gotchas).
- **Data / migrations:** none.
- **External services:** none. Dependencies only: `fastapi[standard]` (needed for `make dev` → `fastapi dev`); dev group `pytest`, `httpx` (for FastAPI's `TestClient`), `ruff`, `mypy`.
- **Protected areas touched (AGENTS.md §4):** none for option A. `Makefile`, `.github/**` and `tools/haam/**` should not need changes. If the build finds a `Makefile` change unavoidable, it becomes protected and needs the owner's code review.
- **Production code:** `app/**` (all of option A's app code); `tests/**` and docs are outside it.
- **Finding from this assessment (verified, not assumed):** `make lint` and `make typecheck` run `ruff check .` and `mypy .` over the whole repository, which includes the kit's `tools/haam/haam.py` (8,905 lines). Run against it today with default settings: **ruff reports 70 errors, `ruff format --check` would reformat the file, and mypy reports 4 errors.** So the settings listed in `ARCHITECTURE.md` (Gotchas) are **not enough**: as soon as `pyproject.toml` exists, `make check` would fail on kit code. The spec must also exclude it:
  - ruff: `extend-exclude = ["tools/haam", "prototypes"]` (`.claude/worktrees/` is already skipped through `.gitignore`)
  - mypy: `exclude` also covers `^tools/haam/` and `^\.venv/`, in addition to `^\.claude/` and `^prototypes/`
  - pytest: `testpaths = ["tests"]`, `norecursedirs` as in `ARCHITECTURE.md`

  Don't reformat or fix kit code: that would make every kit `update` report a conflict.
- **Unknowns:**
  - Whether `make audit` (`uv export … | uvx pip-audit --strict -r …`) runs cleanly on the first real lockfile. It hasn't run against one yet. A finding there would be a real one, not a setup error.
  - mypy strictness (`strict = true` or the defaults): the owner's choice, and best set now while there's almost no code.
  - The CI runner gets Python 3.13 through `astral-sh/setup-uv` and `uv python install`; that has only run with no project so far.
- **Spike:** not needed. The one risk I could check by reading (kit code under lint/types) was checked directly; the rest is standard uv/FastAPI setup.

## 5. Risks
| Risk | Area | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Lint/typecheck picks up kit code or agent worktrees and fails `make check` | delivery | High without the extra excludes | Medium: blocks the PR | Excludes for `tools/haam`, `.claude`, `prototypes`, `.venv` (see §4); acceptance criterion that `make check` passes in a fresh worktree |
| First real `make audit` reports a vulnerable dependency | security | Low–medium | Low: pin or bump | Treat as a real finding; never weaken `--strict` |
| `uv.lock` not committed or out of date → `uv sync --locked` fails in CI | delivery | Medium | Low | Acceptance criterion: `uv.lock` committed; `make setup` passes in a clean worktree |
| Scope creep into business logic | delivery | Low | Medium | Spec says no business logic; option B is a separate decision |

## 6. Recommendation
**Approve option A, priority High**: it comes before priority 1 and unblocks it. It's small, touches no protected area, and is the first PR where `ci` and `dependencies` really check something. The spec should carry the extra excludes from §4 and update `ARCHITECTURE.md`'s Gotchas to match. I'd change my mind if the owner wants option B's groundwork in the same PR, though I'd still keep it separate.

## 7. Questions for the decision maker
1. mypy: `strict = true` from the start (recommended while the code is tiny), or mypy's defaults?
2. Should `GET /health` return only `{"status": "ok"}`, or also the app version? Recommended: `{"status": "ok"}` only. A version string is harmless but adds a decision.
