# Architecture map

> Agents read this at the start of every session (imported by `AGENTS.md`). It is a **map**, not full documentation: enough for a new agent to find its way in two minutes.
> Agents keep it current: if your PR changes structure or you discover a gotcha, update this file in the same PR.

> **Status (2026-11-26):** epic #7 slices 1 and 1b (#8, #14): `GET /health` plus `POST /verification-requests` (demo API keys, SQLite storage), whose response now carries the single-use client link. Opening the link (#9), consent, results and audit come in the next slices.

## Stack
- Language / framework: Python 3.13 (`.python-version`), FastAPI (`fastapi[standard]`, which brings the `fastapi dev` CLI)
- Packaging: [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + committed `uv.lock`; CI runs `uv sync --locked`). Non-packaged project: no `[build-system]`, so `make build` prints "nothing to build" and passes.
- Lint / format: ruff (default rules) · Types: mypy, `strict = true` · Tests: pytest (+ httpx for `TestClient`). Dev tools are in `[dependency-groups] dev`, which `uv sync` installs by default.
- Database: SQLite through stdlib `sqlite3`, no ORM (ADR 0003). One local file, `var/verify-my-client.sqlite3` (git-ignored), created on first start
- Hosting / deploy target: not chosen yet (`deploy: manual` in `haam.config.json`)
- Key external services: none yet

## Repository layout
```
.agents/ .claude/ .github/ tools/haam/   HAAM kit: agent skills, settings, workflows, tooling (protected)
app/                                     Production code (FastAPI app)
  api/ auth/ claims/ links/ models/      Endpoints, demo businesses, claim types, client link tokens, models + storage
  privacy/                               422 handler
  migrations/                            Numbered SQL schema scripts (0001_initial.sql, …)
tests/                                   pytest tests (synthetic data only)
docs/product/                            PRODUCT.md, ARCHITECTURE.md (this file)
docs/process/ docs/setup/                How we work; setup guides
pyproject.toml uv.lock                   Dependencies and tool config (ruff, mypy, pytest)
Makefile                                 The command contract: setup, dev, test, lint, typecheck, build, check, audit
```

## Main modules
| Module / path | Responsibility | Protected area? |
|---|---|---|
| `app/main.py` | `create_app(database_path)`: lifespan runs `init_schema`, registers routes and the 422 handler. Module-level `app = create_app(DEFAULT_DATABASE_PATH)` so `fastapi dev` finds it. `GET /health` returns exactly `{"status": "ok"}` | No |
| `app/api/verification_requests.py` | `POST /verification-requests`: authenticate, validate, store the request, claims and link in one transaction, respond with `id`, `claims`, `created_at`, `client_link`, `expires_at` (`Cache-Control: no-store`) | Yes (`app/api/**`) |
| `app/links/tokens.py` | `new_link_token` (`secrets.token_urlsafe(32)`), `hash_token` (SHA-256 hex, also the lookup key for #9), `LINK_LIFETIME` (24 h), `utc_now` (a dependency, so tests fix the clock) | Yes |
| `app/auth/businesses.py` | The three synthetic demo businesses and `require_business` (`X-API-Key`, constant-time compare, one 401 body for every failure) | Yes |
| `app/claims/types.py` | `ClaimType` (`name`, `over_18`, `confirmed_address`), which claims need an expected value, the fixed order | Yes |
| `app/models/verification_request.py` | Strict Pydantic models (`extra="forbid"`); validator messages never contain submitted values | Yes |
| `app/models/database.py` | `connect`, `init_schema` (applies `app/migrations/NNNN_*.sql`, refuses unknown versions), per-request `get_connection` | Yes |
| `app/models/repository.py` | Inserts (request + claims + link in one transaction), parameterised SQL only | Yes |
| `app/privacy/validation_errors.py` | App-wide 422 handler: each error keeps only `type`, `loc`, `msg` (drops `input`, `ctx`, `url`) | Yes |

## Data model (key entities)
Schema in `app/migrations/`, all tables `STRICT`, timestamps ISO 8601 UTC text. `PRAGMA user_version` = number of the last script applied.
- `verification_requests(id, business_id, created_at)`: `id` is a UUID4; `business_id` is a demo business id (code, not a table).
- `request_claims(request_id → verification_requests, claim_type, expected_value)`, primary key `(request_id, claim_type)`. `expected_value` (trimmed free text, 1–200 characters) is the only personal data, for `name` and `confirmed_address`; always NULL for `over_18`. #11 deletes it once the result exists (ADR 0003).
- `client_links(token_hash PK, request_id UNIQUE → verification_requests, expires_at, used_at)` (schema version 2, #14). One link per request. **The raw token is never stored or logged: it exists only in the 201 response.** `used_at` is NULL until #10 uses the link up. Requests from version-1 files have no link (no backfill).
- No down-migration: reset the demo file by deleting it (synthetic data only).

## Environments
| Env | URL | How it's deployed |
|---|---|---|
| Local | http://127.0.0.1:8000 | `make dev` (`uv run fastapi dev`) |
| Production | none yet | manual (no deploy target chosen) |

## Configuration
- Env vars are documented in `.env.example` (never commit real values).

## Testing
- Unit tests live in `tests/` and run with `make test` (`uv run pytest -q`). `pythonpath = ["."]` lets tests `import app` without packaging.
- API tests use the `client` fixture (`tests/conftest.py`): `with TestClient(create_app(tmp_path / ...))`, so each test gets its own database. Shared synthetic data and helpers live in `tests/synthetic.py` (import it; never import `conftest`). `tests/__init__.py` exists so mypy sees one module name per test file.
- Synthetic test fixtures only: never real personal data.
- E2E / browser: none.

## Gotchas
- **Exclusions are exactly `tools/haam`, `prototypes` and `.venv`** in ruff (`extend-exclude`), mypy (`exclude`) and pytest (`addopts --ignore=…`). The kit's `tools/haam/haam.py` fails this project's ruff and mypy settings; don't reformat or fix it, keep it excluded.
- **Agent worktrees in `.claude/worktrees/` need no exclusion:** ruff skips them through `.gitignore`, mypy skips dot-folders, and pytest only collects from `testpaths = ["tests"]`. (Checked in #5 with a deliberately broken file there.)
- **`ruff format --check` also checks Python code blocks in Markdown** (ruff 0.17 includes `*.md` by default, so the whole `docs/` and kit docs). A badly formatted ` ```python ` block in a doc fails `make lint`.
- **`uv.lock` must be committed** and kept current (`uv lock` after editing dependencies), or `make setup` (`uv sync --locked`) fails.
- `make dev` relies on `fastapi dev` auto-discovery of `app/main.py`; needs the `fastapi[standard]` extra.
- **`TestClient(app)` without `with` doesn't run the lifespan**, so it creates no database file (the `/health` tests rely on this). Use the `client` fixture for anything that touches storage.
- **Register routes with `app.add_api_route`, not `include_router`.** FastAPI 0.165 keeps an included router as one nested `_IncludedRouter` object in `app.routes`, which hides its routes from the exact route-list test (`tests/test_health.py`).
- **Per-request SQLite connections use `check_same_thread=False`:** FastAPI may run a request's sync dependency and endpoint on different pool threads. `with conn:` commits or rolls back but doesn't close; the dependency closes it.
- **The access log shows request paths in full.** No route has a token in its path yet, but a request to `/client/<token>` (even a 404) logs the token: #9 must redact it (ADR 0003) when it adds that route.
- **Order of checks on `POST /verification-requests`:** the API key is checked before the body. A bad key with a bad body gets 401; a good key with a bad body gets 422. Nothing is stored in either case.
