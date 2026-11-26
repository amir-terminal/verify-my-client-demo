# UAT plan: #5 Project skeleton: FastAPI app with /health so CI checks run for real

- **Issue:** #5 · **PR:** none yet (test-first: `/test` opens it) · **Spec:** docs/specs/GH-5-project-skeleton.md
- **Estimated time:** ~10 minutes

## Setup (local)
```bash
git fetch origin
git switch --detach origin/5-project-skeleton   # detached: works even while the agent's worktree has the branch
make setup
make dev
# when done: Ctrl+C, then git switch main
```
- Open: http://127.0.0.1:8000/health
- Test account(s): none (no data, no sign-in)
- Feature flag: none

## Test cases
| # | AC | Steps | Expected result | Pass? |
|---|---|---|---|---|
| 1 | AC3 | 1. Run `make setup`. 2. Run `git status`. | Setup installs Python 3.13 and the dependencies without errors. `git status` shows no changes (`uv.lock` unchanged, no new untracked files). | [ ] |
| 2 | AC4, AC5 | Run `make check`. | Four real steps: ruff ("All checks passed!", "files already formatted"), mypy ("Success: no issues found"), pytest ("4 passed"), build ("No [build-system] … nothing to build"). **No "No pyproject.toml yet: skipping" line.** | [ ] |
| 3 | AC8 | Run `make audit`. | "No known vulnerabilities found". | [ ] |
| 4 | AC1 | With `make dev` running, open http://127.0.0.1:8000/health. | Shows `{"status":"ok"}` and nothing else (no version, build or environment info). | [ ] |
| 5 | AC2 | Open http://127.0.0.1:8000/docs. | The API docs page lists exactly one endpoint: `GET /health`. | [ ] |
| 6 | Edge | Open http://127.0.0.1:8000/anything-else. | `{"detail":"Not Found"}` (404). | [ ] |
| 7 | AC6 | Run `git diff --stat origin/main -- tools/haam Makefile .github`. | Prints nothing: the kit, the Makefile and CI are untouched. | [ ] |
| 8 | AC9 | Skim `docs/product/ARCHITECTURE.md`. | Layout, Main modules, Testing and Gotchas describe `app/`, `tests/`, the three exclusions and why `.claude/worktrees/` needs none. | [ ] |

## Not in scope for this test
- Any business feature (verification requests, links, claims, audit). None exists yet.
- Deploy, hosting, `make smoke`.
- CI itself: it runs when `/test` opens the PR after your pass (first real `ci` and `dependencies` runs).

## Agent pre-check
- **Fully verified by the agent:** no  <!-- AC3/AC4/AC8 also need CI's first real run, which only happens once the PR opens -->
- **Needs a person:** no
- **Verified at:** da5c415189d06206e72d841c1158e275ca22a91b
- **Risk:** low: new files only; no production data, no protected areas.
- **Undo:** revert the commit; the `make` targets go back to skipping.
- Evidence:
  - AC1: `test_health_returns_ok` passes; `curl -i /health` on a running app → 200, `content-type: application/json`, `{"status":"ok"}`.
  - AC2: `test_only_health_route_is_exposed`, `test_health_rejects_post` (405), `test_unknown_path_is_404` pass; `/openapi.json` paths = `['/health']`.
  - AC3: `uv sync --locked` in this fresh worktree succeeded; `git status` after `make check` shows only the intended files.
  - AC4: `make check` → ruff, ruff format, mypy (3 files), pytest (4 passed), build ("nothing to build"); no "skipping" lines.
  - AC5: `strict = true`; `grep -rn "type: ignore" app tests` empty.
  - AC6: `git diff --stat origin/main -- tools/haam Makefile .github` empty; `haam.py protected` → none.
  - AC7: put `.claude/worktrees/ac7-check/bad.py` (unused import, wrong return type) in place; `make check` still passed, while `ruff check` on that file alone reports 2 errors. File removed.
  - AC8: `make audit` → "No known vulnerabilities found" (Makefile unchanged).
  - AC9: `ARCHITECTURE.md` updated; the wrong gotcha about mypy and `.claude/` is replaced.
  - Found while building: ruff 0.17 also format-checks Python code blocks in `*.md` files (passes today). Recorded as a gotcha in `ARCHITECTURE.md`.

## Results
Recorded as comments on the issue and the PR by `/test` (or `/uat-result`), so recording a result never changes the code that was tested.
