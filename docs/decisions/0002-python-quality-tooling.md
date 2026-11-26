# ADR 0002: Python quality tooling: strict types, minimal exclusions, kit code left as shipped

- **Status:** Accepted
- **Date:** 2026-11-26
- **Deciders:** Product owner (@amir-terminal), at G1 for #5
- **Issue:** #5

## Context
The app is Python 3.13 + FastAPI, managed with uv. `make lint` and `make typecheck` run `ruff check .`, `ruff format --check .` and `mypy .` over the whole repository. The repository also holds the HAAM kit's own Python (`tools/haam/haam.py`), which doesn't pass ruff or mypy with this project's settings (the #5 assessment measured 70 ruff errors and 4 mypy errors). Changing that file would make every kit `update` report a local conflict. Without a rule, an agent fixing a red `make check` could silence it in the wrong place: by reformatting kit code, adding broad exclusions, or relaxing `make audit`.

## Decision
- **mypy runs in strict mode** (`strict = true` in `pyproject.toml`) for all project code. Don't relax it globally. A narrow, commented `# type: ignore[code]` or a per-module override needs the owner's agreement in the PR.
- **Exclusions are explicit and minimal:** ruff, mypy and pytest exclude only `tools/haam`, `prototypes` and `.venv`. Adding another exclusion is an owner decision, recorded in this ADR or a later one.
- **The kit's Python is left as shipped:** never reformat, lint-fix or type-fix `tools/haam/**`. Kit bugs are reported upstream and come back through `haam.py update`.
- **`make audit` is never weakened or skipped.** A finding against the real `uv.lock` is reported in the PR and fixed by upgrading or pinning, or the owner decides.
- **`GET /health` returns exactly `{"status": "ok"}`.** No version, build or environment details.

## Consequences
- `make check` stays meaningful: a red check means project code needs fixing, not the tool's configuration.
- Strict typing costs a little more effort per change while the codebase is small, and keeps the code consistent as it grows.
- Kit updates stay clean, because `tools/haam/**` matches what the kit shipped, apart from the documented fixes awaiting upstream.
- This rules out "fix the build by excluding the failing folder" and "add `--ignore-vuln` to pass the audit" without the owner's decision.

## Alternatives considered
- mypy with its default (non-strict) settings: easier at first, but harder to tighten once code exists.
- Formatting and type-fixing `tools/haam/haam.py` so no exclusion is needed: rejected, because it conflicts with every kit update.
- Broad exclusions (e.g. every dot-folder, `scripts/`, `docs/`): rejected, because they hide what's checked.
