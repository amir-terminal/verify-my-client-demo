# Command contract shared by agents, CI and humans.
# Agents and CI only ever call these targets, so each project fills them in once.
# Stack: Python + FastAPI, managed with uv; ruff (lint/format), mypy (types), pytest (tests).
# Until pyproject.toml exists, each target prints a skip message and succeeds.

.PHONY: setup hooks dev test lint typecheck build check audit secrets e2e smoke deploy

setup:  ## Install dependencies
	@if [ ! -f pyproject.toml ]; then echo "No pyproject.toml yet: skipping setup"; exit 0; fi; uv sync --locked

hooks:  ## Turn on the secret scan before every commit (keeps your own git hooks working). Run once per clone.
	python3 tools/haam/haam.py hooks --apply

dev:  ## Run the app locally (used for UAT)
	@if [ ! -f pyproject.toml ]; then echo "No pyproject.toml yet: skipping dev"; exit 0; fi; uv run fastapi dev

test:  ## Unit tests
	@if [ ! -f pyproject.toml ]; then echo "No pyproject.toml yet: skipping test"; exit 0; fi; uv run pytest -q

lint:  ## Lint and format check
	@if [ ! -f pyproject.toml ]; then echo "No pyproject.toml yet: skipping lint"; exit 0; fi; uv run ruff check . && uv run ruff format --check .

typecheck:  ## Type checks (make it a no-op if your stack has none)
	@if [ ! -f pyproject.toml ]; then echo "No pyproject.toml yet: skipping typecheck"; exit 0; fi; uv run mypy .

build:  ## Production build
	@if [ ! -f pyproject.toml ]; then echo "No pyproject.toml yet: skipping build"; exit 0; fi; if grep -q "^\[build-system\]" pyproject.toml; then uv build; else echo "No [build-system] in pyproject.toml: nothing to build"; fi

check: lint typecheck test build  ## Everything CI runs. Must pass before any PR.

audit:  ## Dependency vulnerability audit (pip-audit: fails on any known vulnerability in uv.lock)
	@if [ ! -f pyproject.toml ]; then echo "No pyproject.toml yet: skipping audit"; exit 0; fi; uv export --locked --format requirements-txt --no-emit-project --quiet -o .audit-requirements.txt && uvx pip-audit --strict -r .audit-requirements.txt; status=$$?; rm -f .audit-requirements.txt; exit $$status

secrets:  ## Scan uncommitted changes for secrets (same check as the pre-commit hook)
	@bash scripts/scan-secrets.sh

e2e:  ## End-to-end / browser tests (optional)
	@echo "No e2e tests configured yet"

smoke:  ## Post-deploy smoke test. Usage: SMOKE_URL=https://... make smoke
	@test -n "$(SMOKE_URL)" || (echo "SMOKE_URL not set"; exit 1)
	@curl -fsS -o /dev/null -w "%{http_code} $(SMOKE_URL)\n" "$(SMOKE_URL)"
#   TODO(setup): add a health endpoint check, e.g. curl -fsS "$(SMOKE_URL)/health"

deploy:  ## Production deploy. Only ever run by deploy.yml in GitHub Actions.
	@test "$(CI)" = "true" || (echo "Refusing to deploy outside CI"; exit 1)
	@echo "TODO(setup): make deploy"; exit 1
