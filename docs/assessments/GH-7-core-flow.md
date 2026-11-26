# Assessment: #7 Verify My Client core flow: request, client link, minimal disclosure, verified result, audit

- **Issue:** #7 (epic; slices #8, #9, #10, #11, #12) · **Brief:** `docs/epics/GH-7-core-flow.md`
- **Author:** Claude Code agent session (owner's main chat) · **Date:** 2026-11-26
- **Recommendation:** Approve, built slice by slice (option A) · **Suggested priority:** High (epic and all five slices)
- **Size:** L in total (sum of the slices: M + S + S + M + S–M), with storage A or B; about L+ with C; XL with D

## 1. Problem and users
The app is a skeleton (`GET /health`, #5). None of the five core journeys exists. This epic delivers them as a JSON API on synthetic data:
1. a business creates a request for chosen claims and gets a single-use, 24-hour client link;
2. the client sees only what was requested;
3. the client consents through a synthetic identity provider to exactly those claims, and anything extra, unknown or missing is refused;
4. the business reads a yes/no result;
5. every verification leaves an append-only audit record.

It's for the demo's two users: the business (solicitor, estate agent, accountant) and its client.

## 2. Value
- It is the product: `PRODUCT.md` priorities 1–3 and journeys 1–5. Without it, the demo shows nothing.
- It proves the non-negotiables in code (data minimisation, no raw documents stored, yes/no results, audit), each with an automated test.
- Evidence: the owner's priorities. There's no customer evidence yet, because it's a demo.

## 3. Options
| Option | Description | Size | Pros | Cons |
|---|---|---|---|---|
| A | **Slice by slice:** five PRs, #8 → #12, each specced, built, tested and shipped on its own (`grouping: per-issue`, the current setting) | L total; each slice S or M | Each PR stays near `max_pr_lines` 400, and every slice is protected, so each code review stays small. A problem in one slice doesn't hold the others back. The owner sees progress after every slice. | Five UAT sittings and five rounds of CI and reviews. Some cross-slice rework if a later slice shows an early model was wrong. |
| B | **Epic build mode** (`mode:epic-build`): one lead agent builds all five slices on one branch, with a checkpoint per slice; the owner tests and ships once | L in one PR | One UAT sitting and one CI/review run; the design stays consistent across slices | One PR of roughly 1,000–1,400 changed lines (estimate), far over `max_pr_lines` 400, and all of it protected code: a very large review for the owner. A failure anywhere holds everything. |
| Do nothing | Keep the skeleton | – | No work | The demo has no product; the priorities aren't met |

## 4. Technical feasibility
- **Modules affected (all new):** `app/models/`, `app/links/`, `app/claims/`, `app/disclosure/`, `app/verification/`, `app/audit/`, `app/auth/` (the demo businesses), `app/integrations/synthetic_idp/` (the fixture provider), and the storage layer. `app/main.py` gains routers. Tests in `tests/`.
- **Verified in this assessment:**
  - FastAPI 0.165 / Pydantic 2.14 (the locked versions): a request model with `extra="forbid"` returns **422 `extra_forbidden`** for an unrequested field. Slice 3's refusal is built-in; "missing" and "unknown claim" need explicit checks against the request's allow-list.
  - uvicorn 0.54 (the locked version) **writes the full path, including the client-link token, to its access log**: `"GET /client/SECRET-TOKEN-abc HTTP/1.1" 200`. See risk R1.
- **Data / storage:** depends on the owner's G1 choice. The data is the same in every option:
  - demo businesses (fixed);
  - verification requests (claims, and the expected `name` and `confirmed_address` values the business supplies);
  - link tokens (stored as a hash, not the raw token: see R2);
  - consents;
  - results (yes/no per claim);
  - audit records (append-only).

  Per option:
  | Storage | Effect on the slices | New dependencies | Extra protected areas |
  |---|---|---|---|
  | A. In memory | Smallest; a repository interface keeps a later switch cheap. Data is lost on restart, so UAT runs in one `make dev` session. | none | none beyond `models` |
  | B. SQLite (`sqlite3`) | +~50–100 lines (schema, queries) mostly in slice 1; survives restarts | none | schema script (keep it under `migrations/`) |
  | C. SQLite + SQLAlchemy + Alembic | +1 size step on #8, #11, #12 (models + migrations) | `sqlalchemy`, `alembic`: new `make audit` surface | `migrations` in three slices |
  | D. PostgreSQL | As C, plus a CI service container, Docker locally, and shared test-database runs | as C + a driver (`psycopg`) | `.github/**` (the owner's review), `heavy_runs` |
  | Defer | Build #8 on A behind the interface; revisit before #12 | none | as A |

  The choice is the owner's (they asked not to have it picked for them). What I'd want confirmed, whatever it is: does the audit trail need to survive a restart for the demo? If yes, A is out.
- **External services:** none. The identity provider is a synthetic fixture in `app/integrations/synthetic_idp/`, with made-up identities only.
- **Protected areas touched (AGENTS.md §4):** every slice (by design, see the brief). All need `human-review` and the owner's code review, and none can take the no-UAT lane.
- **Unknowns:**
  - How the 24-hour expiry is tested: the clock must be injectable, a small design point for #8's spec.
  - Whether `make audit` stays clean if C or D adds dependencies.
  - Whether the expected `name` and `address` values the business supplies should be kept after verification, or deleted once the yes/no result exists (question 2).
- **Spike:** not needed. The two assumptions I could test were tested directly (above); the rest is standard FastAPI.

## 5. Risks
| # | Risk | Area | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|
| R1 | **Client-link tokens written to the server's access log** (verified above); anyone with log access could use an unused link within 24 h | security | High if unaddressed | Medium (synthetic data, but it's the credential) | Options in question 1: redact `/client/…` paths in the access log with a logging filter in the app, or keep the token out of the URL path |
| R2 | Link tokens readable from storage | security | Medium | Medium | Store only a hash (SHA-256) of each token; compare in constant time; tokens from `secrets.token_urlsafe(32)` |
| R3 | More data disclosed than requested (in `/client/{token}`, results, audit, error messages) | data protection | Medium | High (the core promise) | Response models listing exactly the allowed fields; tests that assert whole response bodies, not single keys; 422 bodies that don't echo submitted values |
| R4 | Personal details in logs or errors (expected name/address, fixture identities) | data protection | Medium | High | No logging of request bodies; a test that captures logs during a full journey and checks they contain no fixture values |
| R5 | Wrong "verified" result | correctness | Low–medium | High | Deterministic fixtures; a match and a mismatch test per claim type; `over_18` computed with an injectable clock, tested on a boundary birthday |
| R6 | One business reads another's request, result or audit | security | Medium | High | Every read is scoped by the business from the API key; return 404, not 403, for other businesses' ids; a test per endpoint |
| R7 | Demo API keys mistaken for real secrets, or replaced by random-looking ones | operational | Low | Low | Keep `demo-key-*` names (gitleaks checked, no leaks); compare with `hmac.compare_digest` |
| R8 | Option B's one big protected PR is hard to review | delivery | High under option B | Medium | Prefer option A |

## 6. Recommendation
**Approve option A** (five slices, #8 → #12, each with its own spec, test and ship), **priority High** for the epic and all slices. Every slice is protected code, and option A keeps each review near the 400-line target. Option B would put roughly three times that into one protected PR.

**Storage:** the owner's decision at G1 (§4 table). It's needed before #8 is specced, because it changes #8, #11 and #12.

R1 (tokens in the access log) should be settled before #9 is specced (question 1). I'd change my mind towards option B only if the owner would rather test the whole flow once, and accepts one large review.

## 7. Questions for the decision maker
1. **Link tokens in the access log (R1):** (a) keep `/client/{token}` URLs and redact them in the app's access log (recommended: the link stays a simple URL, and the fix is one logging filter, tested), or (b) move the token out of the path (e.g. sent in a header or body), which makes the link less of a plain link.
2. **The expected name and address the business supplies:** (a) delete them once the yes/no result is computed (recommended: data minimisation, and the audit doesn't need them), or (b) keep them with the request.
3. **Storage:** A, B, C, D or defer, and whether the audit must survive a restart.
4. **How to build:** option A (slice by slice, recommended) or option B (epic build mode)?
