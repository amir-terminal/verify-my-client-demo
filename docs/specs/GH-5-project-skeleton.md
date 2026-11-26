# Spec: #5 Project skeleton: FastAPI app with /health so CI checks run for real

- **Issue:** #5 · **Assessment:** docs/assessments/GH-5-project-skeleton.md · **ADRs:** [0002 Python quality tooling](../decisions/0002-python-quality-tooling.md)
- **Status:** Draft · **Approved by:** – on –
- **Protected areas:** none (see §5). `Makefile`, `.github/**` and `tools/haam/**` must not change.

## 1. Goal
Create the smallest real Python 3.13 + FastAPI project, managed with uv, so the `make` targets stop skipping and CI's `ci` and `dependencies` checks really lint, type-check, test and audit code. The app has one endpoint, `GET /health`, which returns exactly `{"status": "ok"}`. There's no business logic. This is option A of the assessment, as approved at G1 with the owner's notes (ADR 0002).

## 2. User stories
- As the product owner, I want `make check` and CI to really check code, so that a green check means something before the first feature lands.
- As an agent building the next feature, I want a project with strict typing and tests already wired, so that I add code, not setup.
- As whoever runs the app, I want a health endpoint, so that I (and later `make smoke`) can tell the app is up.

## 3. Acceptance criteria
**AC1: Health endpoint**
- Given the app is running
- When a client sends `GET /health`
- Then the response is HTTP 200 with `Content-Type: application/json` and the body is exactly `{"status": "ok"}`: no other keys, no version, build or environment details.

**AC2: Only the health route is exposed**
- Given the app is created
- When its routes are listed
- Then the only application route is `GET /health`, plus FastAPI's built-in documentation routes (`/docs`, `/redoc`, `/openapi.json`) left at their defaults.

**AC3: Dependencies install from the committed lockfile**
- Given a fresh clone or worktree with `pyproject.toml` and a committed `uv.lock`
- When `make setup` runs (`uv sync --locked`)
- Then it succeeds, installing Python 3.13 (from `.python-version`) and the locked dependencies without changing `uv.lock`.
- And after `make setup` and `make check`, `git status` shows no untracked files other than the intended new ones (§5).

**AC4: `make check` runs every step for real and passes**
- Given the project is set up
- When `make check` runs, locally and in CI
- Then lint (`ruff check .`, `ruff format --check .`), typecheck (`mypy .`, strict), test (`pytest -q`) and build all run: **no "No pyproject.toml yet: skipping" line**, and all pass.

**AC5: Strict typing is on**
- Given `pyproject.toml`
- When `mypy .` runs
- Then mypy uses `strict = true` and the project code has no `# type: ignore`.

**AC6: Exclusions are exactly `tools/haam`, `prototypes` and `.venv`**
- Given the kit's `tools/haam/haam.py` fails ruff and mypy with this project's settings (assessment §4)
- When ruff, mypy and pytest are configured
- Then each excludes exactly `tools/haam`, `prototypes` and `.venv`, and nothing else. `tools/haam/haam.py` is byte-for-byte unchanged (`git diff origin/main -- tools/haam` is empty).

**AC7: Agent worktrees aren't picked up**
- Given an agent worktree exists under `.claude/worktrees/` containing a file that fails lint and type checks
- When `make check` runs in the main folder
- Then it still passes. The reasons are verified, and no extra exclusion is needed: ruff skips the folder through `.gitignore`, mypy skips dot-folders, and pytest only collects from `testpaths = ["tests"]`.

**AC8: `make audit` runs against the real lockfile, unweakened**
- Given the committed `uv.lock`
- When `make audit` runs (locally and in CI's `dependencies` job)
- Then it audits the locked dependencies with `pip-audit --strict`, and the `Makefile` and its flags are unchanged. If it reports a vulnerability, the PR description says which package, version and advisory, and the check is **not** skipped, weakened or given `--ignore-vuln` (ADR 0002).

**AC9: Docs match the setup**
- Given the change is merged
- When an agent reads `docs/product/ARCHITECTURE.md`
- Then *Repository layout*, *Main modules*, *Testing* and *Gotchas* describe `app/`, `tests/`, the exact exclusions and why `.claude/worktrees/` needs none. The current Gotcha saying mypy doesn't skip `.claude/` is wrong (see §5) and is corrected.

## 4. Out of scope
- Any business logic: verification requests, links, claims, audit records, models, database, auth.
- Settings/config modules, env vars, `.env.example` entries, logging setup, CORS, middleware.
- Changes to `Makefile`, `.github/**` (CI, workflows, Dependabot), `tools/haam/**` or other kit files. If the build finds one unavoidable, stop and ask the owner (protected area).
- Reformatting, lint-fixing or type-fixing kit code.
- Deploy, hosting, `make deploy`, and the `make smoke` health check (`Makefile` `TODO(setup)`, a later change).
- Docker, pre-commit hooks for ruff/mypy, coverage thresholds, extra ruff rule sets beyond the defaults.
- Packaging the app as a distributable (no `[build-system]`, see §5).

## 5. Design notes
- **Files / modules (new unless marked):**
  - `pyproject.toml`
  - `uv.lock` (generated by `uv lock`, committed)
  - `app/__init__.py` (empty)
  - `app/main.py`: `app = FastAPI()` and the handler `def health() -> dict[str, str]: return {"status": "ok"}` on `@app.get("/health")`. Module-level `app`, so `fastapi dev` auto-discovers it (`make dev` = `uv run fastapi dev`).
  - `tests/test_health.py`: uses `fastapi.testclient.TestClient`.
  - `.gitignore` (changed): add `__pycache__/` and `*.pyc` on their own lines **below** the `# --- /HAAM ---` line, not inside the HAAM block.
  - `docs/product/ARCHITECTURE.md` (changed): AC9.
  - `docs/changes/GH-5.md`: release note, added by `/uat`.
- **`pyproject.toml` contents (intent; exact syntax is the builder's):**
  - `[project]`: `name = "verify-my-client"`, `version = "0.1.0"`, `requires-python = ">=3.13"`, `dependencies = ["fastapi[standard]>=<current>"]`. `[standard]` is required for the `fastapi dev` CLI.
  - `[dependency-groups] dev = ["pytest", "httpx", "ruff", "mypy"]`, each with a lower bound at the current release. `httpx` is needed by `TestClient`. uv installs the `dev` group by default in `uv sync` and `uv run`.
  - **No `[build-system]`:** uv treats the project as non-packaged, and `make build` then prints "No [build-system] in pyproject.toml: nothing to build" and passes. That's the existing `Makefile` behaviour, unchanged.
  - `[tool.ruff]`: `target-version = "py313"`, `extend-exclude = ["tools/haam", "prototypes", ".venv"]`, default rule set and line length. `extend-exclude` keeps ruff's own defaults, which already include `.venv`; naming it is the owner's explicit-list choice.
  - `[tool.mypy]`: `strict = true`, `python_version = "3.13"`, `exclude = ['^tools/haam/', '^prototypes/', '^\.venv/']`.
  - `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `pythonpath = ["."]` so `import app` works without packaging, `addopts = ["--ignore=tools/haam", "--ignore=prototypes", "--ignore=.venv"]`. Use `--ignore` (paths) rather than `norecursedirs` (basename patterns, where `tools/haam` wouldn't match).
- **Verified during spec (scratch experiment, mypy 2.4.1, ruff latest):** `mypy .` skipped a type error inside `.claude/worktrees/…` even when the folder wasn't git-ignored (mypy skips dot-folders). `ruff check .` reported a file there when it wasn't git-ignored, and skipped it when git-ignored, as `.gitignore` already does here. So AC7 needs no `.claude` exclusion, matching the owner's list of three.
- **PR size:** hand-written lines ≈ 120–150. `uv.lock` is generated and will be several hundred lines or more; it isn't hand-written, so it doesn't count toward the `max_pr_lines` target. Reviewers should skim it only for unexpected packages.
- **Data model / migrations:** none.
- **Config / env vars:** none. No `.env.example` changes.
- **External APIs:** none at runtime. Build time: PyPI (`uv lock`) and the PyPI advisory database (`pip-audit`).
- **Protected areas (`AGENTS.md` §4):** none. `app/main.py` and `app/__init__.py` match no protected pattern. `pyproject.toml` and `uv.lock` are not protected. So no `human-review` label. If the builder needs to touch `Makefile` or `.github/**`, that becomes protected: stop and ask.
- **Production code:** `app/**` (production paths = `app/**`). `tests/**`, `docs/**` are outside it.
- **Error states and edge cases:** an unknown path returns FastAPI's default 404. `POST /health` returns the default 405. Neither needs custom handling, and both are covered by one test each, so a later change can't silently turn `/health` into a catch-all.
- **CI:** the existing `ci.yml` (`astral-sh/setup-uv`, `uv python install`, `make setup`, `make check`) and `security.yml` (`make audit`) need no change. This PR is their first real run.

## 6. Test plan
| AC | Unit / integration test(s) | Notes |
|---|---|---|
| AC1 | `test_health_returns_ok`: 200, JSON content type, `response.json() == {"status": "ok"}` (exact equality, so extra keys fail) | `TestClient(app)` |
| AC2 | `test_only_health_route_is_exposed`: the app's routes minus `/docs`, `/docs/oauth2-redirect`, `/redoc`, `/openapi.json` are exactly `{("GET", "/health")}`; `test_health_rejects_post`: `POST /health` → 405; `test_unknown_path_is_404` | Guards against accidental extra endpoints |
| AC3 | CI `ci` job, step `make setup` (`uv sync --locked` fails if `uv.lock` is missing or stale) | Also run in a fresh worktree (UAT) |
| AC4 | CI `ci` job, step `make check`; the PR description pastes local `make check` output showing no "skipping" lines | |
| AC5 | `mypy .` in `make typecheck`; `grep -rn "type: ignore" app tests` is empty | |
| AC6 | Review of `pyproject.toml`; `git diff --stat origin/main -- tools/haam Makefile .github` is empty (noted in the PR) | |
| AC7 | Builder's check, written up in the PR: create `.claude/worktrees/ac7-check/bad.py` with a lint and a type error, run `make check` in the main folder (passes), delete it | Manual; can't be a committed test without committing a bad file |
| AC8 | CI `dependencies` job, `make audit`; result (pass, or findings) stated in the PR | |
| AC9 | Review of `ARCHITECTURE.md` diff | |

**UAT outline (owner, on the branch, ~10 min):**
1. `python3 tools/haam/haam.py worktree new uat-5` (or check out the branch), then in it: `make setup`. It installs, and `git status` shows `uv.lock` unchanged.
2. `make check`: four real steps, no "skipping", all green.
3. `make audit`: passes, or shows the findings the PR reports.
4. `make dev`, then open http://127.0.0.1:8000/health: `{"status":"ok"}`, nothing else. Open http://127.0.0.1:8000/docs: one endpoint, `GET /health`.
5. `git diff --stat origin/main -- tools/haam Makefile .github`: empty.

## 7. Rollout and rollback
- **Feature flag:** none (no user-facing behaviour, and no deploy target yet).
- **Rollout:** merge. With `deploy: manual` and no hosting, nothing goes live.
- **Rollback:** revert the PR. The `make` targets go back to skipping, because `pyproject.toml` is gone. No data to clean up.

## 8. Slices (if split)
Not split: about 150 hand-written lines, well under a day of agent work.

## 9. Open questions
None blocking. The owner's G1 notes answered mypy strictness, the `/health` body, exclusions, kit code and audit handling.
