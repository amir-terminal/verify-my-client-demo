# Spec: #8 Create a verification request and single-use client link (demo API keys)

- **Issue:** #8 (slice 1 of epic #7) · **Epic brief:** docs/epics/GH-7-core-flow.md · **Assessment:** docs/assessments/GH-7-core-flow.md · **ADRs:** [0002 Python quality tooling](../decisions/0002-python-quality-tooling.md), [0003 Core flow storage and data handling](../decisions/0003-core-flow-storage-and-data-handling.md) (the epic docs and ADR 0003 are in docs PR #13)
- **Status:** Draft · **Approved by:** – on –
- **Protected areas:** `**/auth/**`, `**/claims/**`, `**/models/**`, `**/links/**`, `**/migrations/**`, `**/privacy/**` → `human-review`. The owner reviews the code at G3, and this slice can't take the no-UAT lane.

## 1. Goal
A synthetic business, identified by an obviously fake demo API key, creates a verification request through `POST /verification-requests`. It picks claims from the fixed set `name`, `over_18`, `confirmed_address` and supplies the expected value for `name` and `confirmed_address`. It gets back the request id and a single-use client link that expires in 24 hours. Anything invalid is refused, and nothing is stored when it is. The request lives in SQLite through stdlib `sqlite3` (ADR 0003), so it survives a restart. This is product priority 1, and it lays the storage, demo businesses and claim definitions the other four slices build on.

## 2. User stories
- As a business (a solicitor, estate agent or accountant), I want to create a request for exactly the details I need, so that I never collect more than I asked for.
- As a business, I want a link to send my client, so that they can share those details.
- As the product owner, I want invalid requests refused with nothing stored, so that the data model only ever holds well-formed, minimal requests.
- As the product owner, I want link tokens that are unguessable and not readable from the database, so that a link works like a one-time password.

## 3. Acceptance criteria
**AC1: Create a request with a demo key**
- Given the demo API key `demo-key-solicitor` (likewise `demo-key-estate-agent` and `demo-key-accountant`)
- When the business sends `POST /verification-requests` with header `X-API-Key` and body
  `{"claims": [{"type": "name", "expected": "Alex Example"}, {"type": "over_18"}, {"type": "confirmed_address", "expected": "1 Example Street, Testtown, ZZ1 1ZZ"}]}`
- Then the response is **201** with exactly these keys: `id` (a random UUID4 string), `claims` (the requested claim types in the fixed order `name`, `over_18`, `confirmed_address`), `client_link` (`<base URL>/client/<token>`) and `expires_at` (ISO 8601 UTC, exactly 24 hours after creation).
- And the response does **not** contain the expected values or the business's id or key.
- And any non-empty subset of the three claims works (e.g. only `over_18`).

**AC2: Missing or unknown API key → 401**
- Given no `X-API-Key` header, or one that isn't a demo key (e.g. `demo-key-nobody`, `DEMO-KEY-SOLICITOR`, empty)
- When it sends `POST /verification-requests` with a valid body
- Then the response is **401** with the same body in every case, `{"detail": "Missing or unknown API key"}`, and nothing is stored.
- And keys are compared in constant time (`hmac.compare_digest`).

**AC3: Invalid claims → 422, nothing stored**
- Given a valid demo key
- When the body has any of these: an empty `claims` list; an unknown claim type (e.g. `passport`); the same claim twice; `name` or `confirmed_address` without `expected`; `expected` that is empty or only whitespace, or over 200 characters after trimming; `expected` on `over_18`; an extra field anywhere (top level or inside a claim, e.g. `"date_of_birth"`); a non-JSON or wrongly typed body
- Then the response is **422**, and no row is added to any table.

**AC4: Error responses never repeat submitted values**
- Given any request the app refuses with 422 (this endpoint or any other)
- When the error body is built
- Then each error keeps `type`, `loc` and `msg` and drops `input`, `ctx` and `url`, so no submitted value (a name, an address, an extra field's value) appears in the response. The default FastAPI 422 body does include `input`: checked on the locked versions while writing this spec.

**AC5: Link tokens are unguessable, unique and stored only as a hash**
- Given a request has been created
- When its token (the last path segment of `client_link`) is examined
- Then it comes from `secrets.token_urlsafe(32)` (256 bits). The database holds only its SHA-256 hex digest, and the raw token appears in no table and no log line. Two requests created one after another get different tokens and different ids.

**AC6: Expiry and single use are recorded**
- Given a fixed clock at time *T*
- When a request is created
- Then its link's `expires_at` is *T* + 24 h, stored and returned, and the link is stored as unused (`used_at` empty). Using it up and checking expiry happen in #9 and #10. This slice only records both.

**AC7: Stored in SQLite, and it survives a restart**
- Given the app with a database file
- When a request is created, the app is stopped and started again on the same file
- Then the request, its claims (with expected values) and its link hash are still there. The tables are created at startup from `app/migrations/0001_initial.sql` when the file is new (`PRAGMA user_version` 0 → 1). If the file has a newer or unknown version, the app refuses to start and says the demo file must be reset (ADR 0003).

**AC8: One transaction**
- Given a request is being stored
- When any insert fails part-way
- Then nothing from that request remains: request, claims and link are written in one transaction.

**AC9: No personal data in logs**
- Given logging is captured at DEBUG for every logger
- When the requests of AC1–AC3 run
- Then no captured line contains an expected value, an API key or a raw token.

**AC10: Nothing else changes**
- Given the change is merged
- When the app's routes are listed
- Then they are exactly `GET /health` (body still exactly `{"status": "ok"}`, ADR 0002), `POST /verification-requests`, and FastAPI's docs routes. `make check` passes with strict mypy and no new exclusions. Running the tests creates no file outside pytest's temporary folders, and `git status` is clean afterwards.

## 4. Out of scope
- Opening the link (`GET /client/{token}`, #9), consent and using the link up (#10), verification and results (#11), audit records (#12).
- Redacting tokens from the access log: ADR 0003 requires it from #9, the first slice with a `/client/…` route. This slice's only route carries no token in its path.
- Listing, reading, updating or deleting requests. Any endpoint other than `POST /verification-requests`.
- Real authentication, business sign-up, key rotation, rate limiting.
- How `name` and `confirmed_address` are matched (normalisation, case, postcode format): #11's spec. This slice stores the trimmed strings as given.
- Deleting expected values after the result (ADR 0003): #11, where the result is created.
- A migration tool, SQLAlchemy, PostgreSQL. Env vars or a settings module.

## 5. Design notes
- **Files / modules (new unless marked):**
  | File | What it holds | Protected |
  |---|---|---|
  | `app/main.py` (changed) | `create_app(database_path: Path) -> FastAPI` with a lifespan that runs `init_schema`; module-level `app = create_app(DEFAULT_DATABASE_PATH)` so `fastapi dev` still finds it; registers the router and the 422 handler; `/health` unchanged | no |
  | `app/auth/businesses.py` | `DemoBusiness` (frozen dataclass: `id`, `display_name`, `api_key`), the three demo businesses, and the dependency `require_business` using `fastapi.security.APIKeyHeader(name="X-API-Key", auto_error=False)`, so `/docs` shows an **Authorize** button | yes |
  | `app/claims/types.py` | `ClaimType(StrEnum)`: `name`, `over_18`, `confirmed_address`; `CLAIMS_WITH_EXPECTED_VALUE = {name, confirmed_address}`; the fixed order | yes |
  | `app/models/verification_request.py` | Pydantic models, all `extra="forbid"`: `RequestedClaim`, `CreateVerificationRequest` (1–3 claims; validators for duplicates and expected-value rules, whose messages never include values), `VerificationRequestCreated` (exactly the AC1 keys) | yes |
  | `app/models/database.py` | `connect(path)` (`PRAGMA foreign_keys = ON`), `init_schema(path)` (applies `0001_initial.sql` at `user_version` 0, refuses unknown versions), `get_connection` dependency (one connection per request, closed afterwards) | yes |
  | `app/models/repository.py` | `insert_verification_request(conn, business, claims, token_hash, created_at, expires_at) -> str`: one transaction (`with conn:`), parameterised SQL only | yes |
  | `app/migrations/0001_initial.sql` | The schema (below) | yes |
  | `app/links/tokens.py` | `LINK_LIFETIME = timedelta(hours=24)`; `new_link_token() -> tuple[str, str]` (raw token, SHA-256 hex); `utc_now()` as a dependency, so tests can fix the clock | yes |
  | `app/privacy/validation_errors.py` | The app-wide `RequestValidationError` handler for AC4 | yes |
  | `app/api/verification_requests.py` | The `POST /verification-requests` router: authenticates, validates, creates the token, stores, and builds `client_link` from `request.base_url` | **no**: see question 3 |
  | `.gitignore` (changed) | `var/`, below the Python lines | no |
  | `tests/conftest.py`, `tests/test_create_verification_request.py`, `tests/test_database.py`, `tests/test_validation_errors.py` | Tests (§6); a fixture builds `create_app(tmp_path / "test.sqlite3")` with a fixed clock | no |
  | `docs/product/ARCHITECTURE.md` (changed) | Modules, data model, the `var/` database file, the gotchas below | no |
- **Demo businesses (synthetic, obviously fake):**
  | id | display_name | API key |
  |---|---|---|
  | `demo-solicitor` | Demo Solicitors (synthetic) | `demo-key-solicitor` |
  | `demo-estate-agent` | Demo Estate Agents (synthetic) | `demo-key-estate-agent` |
  | `demo-accountant` | Demo Accountants (synthetic) | `demo-key-accountant` |

  The keys are plain readable names and never random-looking strings; gitleaks was checked against them (epic brief). They live in code, not the database.
- **Data model (`0001_initial.sql`, all tables `STRICT`; SQLite 3.53 ships with the locked Python 3.13.14):**
  - `verification_requests(id TEXT PRIMARY KEY, business_id TEXT NOT NULL, created_at TEXT NOT NULL)`
  - `request_claims(request_id TEXT NOT NULL REFERENCES verification_requests(id), claim_type TEXT NOT NULL CHECK (claim_type IN ('name','over_18','confirmed_address')), expected_value TEXT, PRIMARY KEY (request_id, claim_type), CHECK (claim_type <> 'over_18' OR expected_value IS NULL))`. `expected_value` stays nullable for `name` and `confirmed_address` because #11 deletes it after the result (ADR 0003).
  - `client_links(token_hash TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE REFERENCES verification_requests(id), expires_at TEXT NOT NULL, used_at TEXT)`
  - Timestamps are ISO 8601 UTC text. Ends with `PRAGMA user_version = 1`.
  - Reversibility: there's no down-migration. Resetting means deleting `var/verify-my-client.sqlite3` (synthetic data only).
- **Database file:** `var/verify-my-client.sqlite3`, relative to the working folder and created on first start (`var/` is git-ignored). Tests always pass a `tmp_path` file and never touch it. There are **no env vars** and no `.env.example` change.
- **Personal data held:** the expected name and address, only until #11 deletes them. Nothing else personal. The business's display name is synthetic.
- **External APIs:** none.
- **UI notes / copy:** none (API only). The 401 message is `Missing or unknown API key`.
- **Error states and edge cases:**
  - Header present but empty → 401.
  - `claims` as an object instead of a list → 422.
  - Unicode names are accepted and trimmed (e.g. `Zoë Example`).
  - A token-hash collision is practically impossible. If the insert hits the unique constraint, the transaction rolls back and the request returns 500 with no detail, never a partial row.
  - On a 401 the body isn't validated first: the API-key check runs as a dependency before body validation, so an unauthenticated caller with a bad body gets 401, not 422. *Check while building:* FastAPI may validate the body before dependencies. If it does, either order is acceptable, as long as nothing is stored and AC2's and AC3's bodies hold. Write down which one it is in ARCHITECTURE.md.
- **Gotchas for the builder:**
  - FastAPI runs sync dependencies and sync endpoints in a thread pool, possibly on different threads. Open the per-request connection with `check_same_thread=False`. It's safe because each connection is used by one request only.
  - `with conn:` commits or rolls back, but doesn't close: close in the dependency's `finally`.
  - `TestClient(app)` without `with` doesn't run the lifespan, so the existing `/health` tests never create a database file. Keep it that way.

## 6. Test plan
| AC | Unit / integration test(s) | Notes |
|---|---|---|
| AC1 | `test_create_request_returns_201_with_exact_keys` (parametrised over the 3 demo keys); `test_claims_returned_in_fixed_order`; `test_response_has_no_expected_values_or_business`; `test_single_claim_subset` | Compare whole bodies (keys set), not single fields |
| AC2 | `test_missing_key_401`, `test_unknown_key_401` (parametrised: wrong, wrong case, empty); `test_401_stores_nothing` | Same body in every case |
| AC3 | `test_invalid_body_422_stores_nothing` (parametrised over every case in AC3) | Counts rows in all three tables before and after |
| AC4 | `test_422_body_has_no_input` (submits a synthetic name and an extra `date_of_birth`; the response text contains neither value) | |
| AC5 | `test_token_stored_only_as_hash` (the raw token isn't in any table dump; the SHA-256 of it is); `test_tokens_and_ids_unique` (50 requests) | |
| AC6 | `test_expiry_is_24h_after_fixed_clock`; `test_link_stored_unused` | Clock via dependency override |
| AC7 | `test_survives_restart` (create, then a second `create_app` on the same file reads the rows); `test_init_schema_sets_user_version_1`; `test_unknown_schema_version_refuses_start` | |
| AC8 | `test_failed_insert_leaves_no_rows` (forces the claims insert to fail, e.g. a duplicate pre-seeded token hash) | |
| AC9 | `test_no_personal_data_in_logs` (`caplog` at DEBUG on the root logger over AC1–AC3 requests) | |
| AC10 | `test_routes_are_exactly` (extends the #5 route test); existing `/health` tests unchanged; `make check` | |

**UAT outline (owner, about 15 minutes, on `/docs`):**
1. `make dev`, open http://127.0.0.1:8000/docs. Two endpoints: `GET /health`, `POST /verification-requests`.
2. Without authorising, try the POST: 401, `Missing or unknown API key`.
3. **Authorize** with `demo-key-solicitor`. POST the AC1 body: 201, with an id, the three claims, a `client_link` and an `expires_at` 24 hours from now. No name or address in the response.
4. POST with `{"type": "passport"}`, then with a duplicate claim, then `over_18` with an `expected`, then an extra `date_of_birth` field: each 422, and none of the values you typed appear in the error.
5. Stop `make dev` and start it again. In a terminal, `sqlite3 var/verify-my-client.sqlite3 "select count(*) from verification_requests; select token_hash from client_links;"` shows your request(s), and the hash isn't the token in your link.
6. Repeat step 3 with `demo-key-accountant`: a different id and a different link.

## 7. Rollout and rollback
- **Feature flag:** none. It's an API with no users and no deploy target yet.
- **Rollout:** merge. With `deploy: manual` and no hosting, nothing goes live.
- **Rollback:** revert the PR, and delete `var/verify-my-client.sqlite3` locally if present (synthetic data only).

## 8. Slices (if split)
**Size estimate:** about 330 lines of app code and 250–300 lines of tests, so about 600 changed lines: over the 400 target (`max_pr_lines`). Proposed split (question 1), each shippable on its own:

| Slice | Scope | Depends on | Size |
|---|---|---|---|
| #8 (narrowed) **Create a verification request** | AC1 without `client_link`/`expires_at`; AC2, AC3, AC4, AC7, AC8, AC9, AC10. Schema 0001 without `client_links`. Demo businesses, claims, storage, 422 handler | – | about 380 |
| new sub-issue of #7 **Single-use client link for a verification request** | AC5, AC6, and AC1's `client_link`/`expires_at`. Schema script `0002_client_links.sql` (`user_version` 1 → 2), `app/links/tokens.py`, the clock | #8 | about 220 |

If the owner prefers one PR, this spec stands as written, and the PR description says it's over the target.

## 9. Open questions
1. **Size:** split as in §8 into #8 plus a new slice "Single-use client link" in epic #7 (recommended: both protected PRs stay near 400 lines), or one PR of about 600 lines?
2. **Store only a hash of each link token** (SHA-256, AC5; assessment risk R2)? Recommended: yes, so a database dump can't be used to open links. Your G1 notes didn't cover it, so it needs your yes here.
3. **The HTTP layer (`app/api/**`) isn't a protected path.** The router handles the expected name and address before they reach protected code. Recommended: protect it, by running `python3 tools/haam/haam.py config --protected "app/api/**" --human` yourself, so later changes to routes also get your review. Otherwise it stays as is, and the PR gets `human-review` anyway because of the other protected files.
4. **Expected-value format:** `name` and `confirmed_address` are each one free-text string (trimmed, 1–200 characters), and how they're matched is left to #11. Recommended: yes, it's the simplest. The alternative is a structured address (lines, town, postcode) now.
