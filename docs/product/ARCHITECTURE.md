# Architecture map

> Agents read this at the start of every session (imported by `AGENTS.md`). It is a **map**, not full documentation: enough for a new agent to find its way in two minutes.
> Agents keep it current: if your PR changes structure or you discover a gotcha, update this file in the same PR.

> **Status (2026-11-25):** no application code yet. The stack below is decided; the layout, modules and data model get filled in by the first PRs that create them.

## Stack
- Language / framework: Python 3.13 (`.python-version`), FastAPI
- Packaging: [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + committed `uv.lock`; CI runs `uv sync --locked`)
- Lint / format: ruff · Types: mypy · Tests: pytest
- Database: not chosen yet
- Hosting / deploy target: not chosen yet (`deploy: manual` in `haam.config.json`)
- Key external services: none yet

## Repository layout
```
.agents/ .claude/ .github/ tools/haam/   HAAM kit: agent skills, settings, workflows, tooling (protected)
docs/product/                            PRODUCT.md, ARCHITECTURE.md (this file)
docs/process/ docs/setup/                How we work; setup guides
Makefile                                 The command contract: setup, dev, test, lint, typecheck, build, check, audit
(app code: not created yet)
```

## Main modules
| Module / path | Responsibility | Protected area? |
|---|---|---|
| _none yet_ | | |

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
- Unit tests run with `make test` (`uv run pytest -q`); location to be set by the first app PR (suggested: `tests/`).
- Synthetic test fixtures only: never real personal data.
- E2E / browser: none.

## Gotchas
- **Makefile guard:** every target skips with "No pyproject.toml yet" until `pyproject.toml` exists. Once it does, `uv.lock` must be committed too, or `make setup` (`uv sync --locked`) fails.
- **Agent worktrees live in `.claude/worktrees/`.** ruff skips them through `.gitignore`, but pytest and mypy don't. The PR that creates `pyproject.toml` must add:
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  norecursedirs = [".claude", ".venv", "prototypes"]

  [tool.mypy]
  exclude = ['^\.claude/', '^prototypes/']
  ```
- `make dev` relies on `fastapi dev` auto-discovery (`main.py` or `app/main.py`); needs the `fastapi[standard]` extra.
