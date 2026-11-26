# Architecture map

> Agents read this at the start of every session (imported by `AGENTS.md`). It is a **map**, not full documentation: enough for a new agent to find its way in two minutes.
> Agents keep it current: if your PR changes structure or you discover a gotcha, update this file in the same PR.

> **Status (2026-11-26):** project skeleton only (#5): a FastAPI app with `GET /health`, no business logic yet. The layout, modules and data model get filled in by the PRs that create them.

## Stack
- Language / framework: Python 3.13 (`.python-version`), FastAPI (`fastapi[standard]`, which brings the `fastapi dev` CLI)
- Packaging: [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + committed `uv.lock`; CI runs `uv sync --locked`). Non-packaged project: no `[build-system]`, so `make build` prints "nothing to build" and passes.
- Lint / format: ruff (default rules) · Types: mypy, `strict = true` · Tests: pytest (+ httpx for `TestClient`). Dev tools are in `[dependency-groups] dev`, which `uv sync` installs by default.
- Database: not chosen yet
- Hosting / deploy target: not chosen yet (`deploy: manual` in `haam.config.json`)
- Key external services: none yet

## Repository layout
```
.agents/ .claude/ .github/ tools/haam/   HAAM kit: agent skills, settings, workflows, tooling (protected)
app/                                     Production code (FastAPI app)
tests/                                   pytest tests (synthetic data only)
docs/product/                            PRODUCT.md, ARCHITECTURE.md (this file)
docs/process/ docs/setup/                How we work; setup guides
pyproject.toml uv.lock                   Dependencies and tool config (ruff, mypy, pytest)
Makefile                                 The command contract: setup, dev, test, lint, typecheck, build, check, audit
```

## Main modules
| Module / path | Responsibility | Protected area? |
|---|---|---|
| `app/main.py` | Creates the FastAPI `app` (module-level, so `fastapi dev` finds it); `GET /health` returns exactly `{"status": "ok"}` | No |

## Data model (key entities)
Not defined yet.

## Environments
| Env | URL | How it's deployed |
|---|---|---|
| Local | http://127.0.0.1:8000 | `make dev` (`uv run fastapi dev`) |
| Production | none yet | manual (no deploy target chosen) |

## Configuration
- Env vars are documented in `.env.example` (never commit real values).

## Testing
- Unit tests live in `tests/` and run with `make test` (`uv run pytest -q`). `pythonpath = ["."]` lets tests `import app` without packaging.
- API tests use `fastapi.testclient.TestClient(app)`.
- Synthetic test fixtures only: never real personal data.
- E2E / browser: none.

## Gotchas
- **Exclusions are exactly `tools/haam`, `prototypes` and `.venv`** in ruff (`extend-exclude`), mypy (`exclude`) and pytest (`addopts --ignore=…`). The kit's `tools/haam/haam.py` fails this project's ruff and mypy settings; don't reformat or fix it, keep it excluded.
- **Agent worktrees in `.claude/worktrees/` need no exclusion:** ruff skips them through `.gitignore`, mypy skips dot-folders, and pytest only collects from `testpaths = ["tests"]`. (Checked in #5 with a deliberately broken file there.)
- **`ruff format --check` also checks Python code blocks in Markdown** (ruff 0.17 includes `*.md` by default, so the whole `docs/` and kit docs). A badly formatted ` ```python ` block in a doc fails `make lint`.
- **`uv.lock` must be committed** and kept current (`uv lock` after editing dependencies), or `make setup` (`uv sync --locked`) fails.
- `make dev` relies on `fastapi dev` auto-discovery of `app/main.py`; needs the `fastapi[standard]` extra.
