# ADR 0003: Core flow storage and data handling: SQLite via stdlib, tokens redacted from logs, expected values deleted after the result

- **Status:** Accepted
- **Date:** 2026-11-26
- **Deciders:** Product owner (@amir-terminal), at G1 for epic #7
- **Issue:** #7 (slices #8–#12)

## Context
Epic #7 builds the core flow (request, client link, consent, verified result, audit) as an API on synthetic data. Its assessment (`docs/assessments/GH-7-core-flow.md`) left four choices to the owner: storage, build mode, how to stop client-link tokens reaching the access log (risk R1, verified: uvicorn logs the full path), and whether the expected name and address the business supplies are kept. Every slice depends on these, so they are fixed before slice 1 is specced.

## Decision
- **Storage is SQLite through Python's standard-library `sqlite3`** (option B). No ORM and no new database dependency. The database is one local file, git-ignored, never committed. Tables are created at startup from a schema script that lives under a `migrations/` folder, so it stays a protected path. There is no migration tool: a schema change that can't be applied to an existing file means resetting the demo file, and the spec says so.
- **The audit record must survive an app restart.** In-memory storage (option A) is ruled out for the audit, and for anything the audit refers to.
- **Build slice by slice** (option A): #8 → #12, one PR each, within `max_pr_lines`. No `mode:epic-build`.
- **Client links stay plain URLs, `/client/<token>`; the app redacts tokens from the access log** (R1, option a). Any log line the app or its server writes for a `/client/…` path shows the token replaced (e.g. `/client/[redacted]`). A test proves the raw token never appears in captured log output. This must be in place in the slice that first adds a `/client/…` route (#9).
- **The expected name and address are deleted once the yes/no result exists** (option a). After verification, the request keeps only the claim list and the results; the business-supplied expected values are removed in the same transaction that stores the result. A test proves they are gone.
- Unchanged: ADR 0002 (strict mypy, minimal exclusions, unweakened `make audit`, `/health` body).

## Consequences
- No new dependency, so `make audit` and the lockfile are unaffected. UAT can stop and restart `make dev` and still see results and audit records.
- Hand-written SQL: every query is reviewed by the owner (the code sits in protected folders). Queries must be parameterised, never string-built.
- No migration history: fine for a demo; a later move to SQLAlchemy/Alembic or PostgreSQL is a new decision (a later ADR).
- Tests need an isolated database per test (a temporary file or `:memory:` connection), never the demo file.
- Deleting expected values means a result can't be re-checked later; the business must create a new request. This is the intended data-minimisation trade-off.
- Rules out: logging raw client paths, keeping expected values "just in case", and an in-memory audit.

## Alternatives considered
- A. In memory: smallest, but the audit would be lost on restart (owner requires it to survive).
- C. SQLite + SQLAlchemy + Alembic: real migrations, but two new dependencies and about one size step more per schema slice.
- D. PostgreSQL: closest to production, but needs Docker and CI changes; too heavy for the demo.
- Token out of the URL path (R1 option b): avoids the log issue, but the link stops being a simple link.
- Keeping the expected name and address with the request: allows re-checking, but holds personal data longer than the result needs.
