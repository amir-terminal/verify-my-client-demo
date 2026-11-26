# Epic brief: #7 Verify My Client core flow: request, client link, minimal disclosure, verified result, audit

- **Epic issue:** #7 · **Status:** Backlog
- **Owner:** @amir-terminal · **Last updated:** 2026-11-26

## Problem and who it's for
The app is a skeleton (`GET /health` only, #5). None of the five core journeys in `docs/product/PRODUCT.md` exists. A UK business (solicitor, estate agent, accountant) can't yet request a verification, and its client can't share only what was asked. This epic delivers the core flow end to end as an API, on synthetic data only. Evidence: the product's own priorities 1–3. There's no customer evidence yet; this is a demo.

## Outcome and success signal
Through the API alone (FastAPI's `/docs` page is enough), a person can:
1. create a verification request as a synthetic business, choosing the details they need;
2. open the client link and see only those details;
3. as the client, consent to exactly those claims, where anything extra, unknown or missing is refused;
4. read the verified result as the business;
5. read the audit record, which holds no more personal data than the result.

**Success signal:** the owner walks journeys 1–5 in one UAT sitting with the synthetic fixtures, and every data-minimisation check (extra, unknown or missing claim refused; result and audit hold nothing unrequested) has an automated test.

## What the issues in it say
No issues existed before this epic: the five slices were created with it on 2026-11-26.

| Issue | Stream | What it asks for (one line) | Notes |
|---|---|---|---|
| #8 | idea | Create a verification request and single-use client link (demo API keys) | Slice 1 |
| #9 | idea | Client opens the link and sees only the requested claims | Slice 2 |
| #10 | idea | Client consents to exactly the requested claims; anything extra, unknown or missing is refused with 422 and nothing is stored | Slice 3 |
| #11 | idea | Business gets a yes/no verified result from the synthetic identity provider | Slice 4 |
| #12 | idea | Append-only audit record on every verification, readable by the requesting business | Slice 5 |

## Scope
- **Must have:**
  - Journeys 1–5 as JSON API endpoints. UAT runs on FastAPI's `/docs` page; there's no UI.
  - A fixed set of requestable claims: `name`, `over_18`, `confirmed_address`. For `name` and `confirmed_address`, the business supplies the expected value when it creates the request.
  - Fixed synthetic businesses, each identified by an obviously fake static API key in a header (`demo-key-solicitor`, `demo-key-estate-agent`, `demo-key-accountant`).
  - An unguessable client link that's single use and expires after 24 hours.
  - Client consent through a synthetic identity provider: the client signs in to a fixture identity and consents to exactly the requested claims, typing no personal details. Anything extra, unknown or missing is refused with 422 and nothing is stored.
  - Yes/no results per claim (`name`: matched, `over_18`: true/false, `confirmed_address`: confirmed).
  - One append-only audit record per verification.
- **Nice to have:** none in this epic.
- **Out of scope:** real identity providers, real documents or real personal data of any kind. Sending emails or SMS (the API returns the link; the person copies it). Payments. A business admin UI. Deployment and hosting. Business sign-up and real authentication (the fixed demo keys stand in). A client web page (a later, separate idea). Returning verified values (results are yes/no only).
- **Must not change:** `GET /health` returns exactly `{"status": "ok"}` (ADR 0002). Strict mypy and the exclusions in ADR 0002. `make check` and `make audit` stay unweakened.

## Constraints
- Synthetic data only (`PRODUCT.md` non-negotiables). Fixtures live under `tests/` or a clearly named synthetic-data module and must never resemble real people.
- Data minimisation, no raw identity documents stored, no personal details in logs, built as if UK GDPR applies.
- `max_pr_lines` 400 per PR: each slice must fit, or it splits.
- **Storage is undecided: a G1 decision for the owner** (options below). Every slice except possibly slice 2 needs it, so it's decided before slice 1 is specified.

### Storage options (for the owner to decide at G1)
| Option | What it is | Pros | Cons | Protected areas / new pieces |
|---|---|---|---|---|
| A. In memory | Python dicts in the app process, behind a small repository interface | No dependency, no migrations, fastest to build and test; nothing persists, which fits "synthetic only" | Everything is lost on restart, so UAT must run in one `make dev` session; not a real audit trail | `**/models/**` only |
| B. SQLite, stdlib `sqlite3` | One local file (git-ignored); tables created at startup from a schema script | No new dependency; survives restarts; real SQL constraints | Hand-written SQL and schema changes; no migration tool, so schema changes mean resetting the file | `**/models/**`; schema script (put under `**/migrations/**` to keep it protected) |
| C. SQLite + SQLAlchemy 2 + Alembic | ORM models and versioned migrations | Typed models, real migrations; the path to Postgres is a URL change | Two new dependencies; more code per slice; migrations in every schema slice | `**/models/**`, `**/migrations/**` (every slice that changes the schema) |
| D. PostgreSQL | A database service locally (Docker) and in CI | Closest to production | Needs Docker locally and a CI service container (`.github/**` change, protected); heaviest setup; tests share a database (`heavy_runs`) | `**/models/**`, `**/migrations/**`, `.github/**` |
| Do nothing (defer) | Build slice 1 on option A behind an interface; decide later | Starts now | Rework when storage changes; the audit isn't durable meanwhile | as A |

**Not a recommendation, just the trade-off:** A or B keep each slice smallest. C costs the most per slice and buys real migrations. D is heavier than a demo needs unless hosting is near. The owner decides.

## Gaps and risks
- **Gap, now covered: who the business is.** Answer 3a: fixed synthetic businesses with static API keys in an `X-API-Key` header. Each business sees only its own requests, results and audit records. This is sign-in and permissions (`**/auth/**`), a protected area.
- **The demo keys are fake by design.** They're plain readable names that hold no secret (`demo-key-solicitor`, `demo-key-estate-agent`, `demo-key-accountant`). Checked on 2026-11-26: the repo's gitleaks config (all default rules) reports no leaks for them, including in `api_key = "demo-key-solicitor"` form. They must never be replaced by random-looking strings. Unknown or missing key → 401.
- **Gap: journey 4/5 read endpoints.** The business needs `GET` endpoints for the result and the audit record, restricted to the business that made the request. These are inside slices 4 and 5.
- **Gap, now covered: how a claim is verified.** Answer 1b: a synthetic identity provider fixture. The client signs in to a fixture identity (a synthetic identity code) and consents. The provider asserts the claims, and the client types nothing personal. The fixture holds only made-up identities.
- **Risk (data protection):** extra data slipping through: unrequested fields accepted, results or audit carrying raw values, personal details in logs or error messages. Mitigation: explicit allow-lists per request, strict Pydantic models (`extra="forbid"`), tests for every refusal, a "no personal data in logs" test.
- **Risk (security):** guessable or reusable client links. Mitigation: `secrets.token_urlsafe` (≥ 128 bits), single use, and expiry after 24 h (answer 4a). Used, expired and unknown links return the same 404.
- **Risk (correctness):** a wrong "verified". Mitigation: deterministic fixtures, and one test per claim type for both match and mismatch.
- **Note:** almost everything here is protected by design (`**/models/**`, `**/links/**`, `**/claims/**`, `**/disclosure/**`, `**/verification/**`, `**/audit/**`, `**/auth/**`). Every slice gets `human-review` and the owner's code review, and none can take the no-UAT lane. The module layout below puts code in the protected folders on purpose, so the gate catches every change there.

## Slices and order
Proposed modules: `app/models/` (request, claim types), `app/links/` (client link tokens), `app/claims/` (claim definitions and the allow-list), `app/disclosure/` (what the client sees and may submit), `app/verification/` (checking claims against the fixture), `app/audit/`, plus `app/auth/` for the business stand-in. The synthetic identity provider fixture lives in `app/integrations/synthetic_idp/`, so it's protected like a real provider. Sizes assume storage option A or B; C adds about +1 size step to slices 1, 4 and 5 for migrations.

| # | Issue | Slice (shippable on its own) | Protected areas | Size | Blocked by |
|---|---|---|---|---|---|
| 1 | #8 | **Create a verification request.** `POST /verification-requests` with a demo API key: pick claims from the fixed set (`name`, `over_18`, `confirmed_address`), with the expected value (free text, trimmed, 1–200 characters) for `name` and `confirmed_address`; unknown or duplicate claims refused (422, never echoing submitted values); no or unknown key → 401. Returns the request id and claims. Includes the SQLite storage layer and the demo businesses. Split at G2: the link moved to #14. | `models`, `claims`, `auth`, `migrations`, `privacy`, `api` | M | G1 storage decision (done) |
| 1b | #14 | **Single-use client link.** The create response also returns `client_link` and `expires_at` (24 h). Token from `secrets.token_urlsafe(32)`, stored only as its SHA-256 hash; stored unused. | `links`, `migrations`, `models`, `api` | S | #8 |
| 2 | #9 | **The client opens the link and sees only what was requested.** `GET /client/{token}`: the requested claims and the business's display name, nothing else (no other requests, no internal ids). Unknown, expired or used tokens return 404, the same for all three, so nothing leaks. | `links`, `disclosure` | S | #14 |
| 3 | #10 | **Client consents to exactly the requested claims; anything extra, unknown or missing is refused with 422 and nothing is stored.** `POST /client/{token}/consent`, with the synthetic identity code from the fixture provider and the list of claims consented to, which must equal the request's claims. The link is used up only on success. | `disclosure`, `claims`, `integrations` | S | #9 |
| 4 | #11 | **The business gets a verified result from a synthetic identity fixture.** On consent, the fixture provider asserts each consented claim, and verification compares it with the request: `name` matched or not, `over_18` true/false, `confirmed_address` confirmed or not. Yes/no only, no values returned. The business reads `GET /verification-requests/{id}/result` for its own requests only; another business's request → 404. | `verification`, `integrations`, `models`, `auth` | M | #10 |
| 5 | #12 | **An audit record on every verification.** Written in the same step as the result. It holds who requested, when, which claims, the outcome and the request id, and no more personal data than the result. `GET /verification-requests/{id}/audit` for the requesting business; append-only (no update or delete endpoint). | `audit`, `models` (+ `migrations` if C/D) | S–M | #11 |

Each slice is about one PR within `max_pr_lines` 400. Slices 1 and 4 are the likeliest to come close; if a spec shows more, it splits.

**Added at G2 for #8 (2026-11-26):** #14 (above), and idea **#15** *Purge expected name and address from requests that expire unused*. ADR 0003 deletes expected values only once a result exists, so a request that never gets one would keep them indefinitely. #15 is in Triage for the owner to assess and decide; it isn't part of the approved scope yet.

## Questions and answers
**Round 1 (2026-11-26):**
1. *How does a claim get verified?* **b**: a synthetic identity provider fixture asserts the claims; the client signs in to a fixture identity and only consents, typing nothing personal.
2. *What does the business receive per claim?* **a**: yes/no only (`name` matched, `over_18` true/false, `confirmed_address` confirmed). The business supplies the expected name and address when it creates the request.
3. *Who is the business in the demo?* **a**: fixed synthetic businesses with static, obviously fake API keys (e.g. `demo-key-solicitor`) in a header. The owner asked they be obviously fake so the secret scan doesn't trip; checked, no leaks.
4. *Client link rules?* **a, 24 h**: single use, and expiry after 24 hours; used, expired and unknown links return the same 404.
5. *UI?* **a**: API only; UAT on `/docs`. A client page would be a later, separate idea.

Owner's wording for slice 3 (#10) (2026-11-26): "client consents to exactly the requested claims; anything extra, unknown or missing is refused with 422 and nothing is stored".

Nothing blocking is open.

**For G1 (not in this interview):** storage option A / B / C / D / defer.

## Decision
**Approved at G1 on 2026-11-26 by @amir-terminal**, priority **High** for the epic and all five slices, which moved to Backlog as `stream:feature`. Recorded in [ADR 0003](../decisions/0003-core-flow-storage-and-data-handling.md):
- Build slice by slice (#8 → #12), one PR each; no epic build mode.
- Storage: **B**, SQLite with stdlib `sqlite3`; the audit must survive a restart.
- Client-link tokens: plain `/client/<token>` links, tokens redacted from the access log (in place from #9).
- The expected name and address are deleted once the yes/no result exists.
