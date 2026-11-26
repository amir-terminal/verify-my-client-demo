# Spec: #14 Single-use client link for a verification request (token stored as a hash, 24 h expiry)

- **Issue:** #14 (slice 1b of epic #7, split out of #8 at G2) · **Epic brief:** [docs/epics/GH-7-core-flow.md](../epics/GH-7-core-flow.md) · **Assessment:** [docs/assessments/GH-7-core-flow.md](../assessments/GH-7-core-flow.md) (risk R2) · **ADRs:** [0002](../decisions/0002-python-quality-tooling.md), [0003](../decisions/0003-core-flow-storage-and-data-handling.md) · **Builds on:** #8 ([spec](GH-8-create-verification-request.md), merged in PR #16)
- **Status:** Draft · **Approved by:** – on –
- **Protected areas:** `**/links/**`, `**/models/**`, `**/migrations/**` and `app/api/**` (added to `protected_paths` in PR #17) → `human-review`. The owner reviews the code at G3, and this slice can't take the no-UAT lane.
- **Blocked by:** #8 (Done) · **Blocks:** #9

## 1. Goal
After #8 a business can create a verification request, but has nothing to send its client. This slice adds the **client link** to the same `POST /verification-requests` response: `client_link` (`<base URL>/client/<token>`) and `expires_at` (exactly 24 hours after creation). The token is unguessable, and **only its SHA-256 hash is stored** (owner's G2 answer on #8), so a copy of the database can't be used to open links. The link is stored as unused. Opening it, single use and expiry checks come in #9 and #10. This slice only creates and records them.

## 2. User stories
- As a business, I want a link for each request, so that I can send it to my client.
- As the product owner, I want link tokens that can't be guessed and can't be read from the database, so that a link works like a one-time password even if the database leaks.
- As the agent building #9 and #10, I want each link's expiry and "used" state recorded, so that I only have to check them.

## 3. Acceptance criteria
**AC1: The create response includes the link**
- Given a valid demo API key and a valid body (as in #8)
- When the business sends `POST /verification-requests`
- Then the response is **201** with exactly these keys: `id`, `claims`, `created_at`, `client_link`, `expires_at`.
- And `client_link` is the request's base URL followed by `client/<token>`: `http://127.0.0.1:8000/client/<token>` under `make dev`, `http://testserver/client/<token>` in tests.
- And `<token>` is 43 URL-safe characters (`^[A-Za-z0-9_-]{43}$`, from `secrets.token_urlsafe(32)`, 256 bits).
- And the response still holds no expected value, business id or API key (#8 AC1).

**AC2: Only a hash of the token is stored**
- Given a request has been created
- When the whole database is dumped (`Connection.iterdump()`)
- Then the raw token appears nowhere in it, and the SHA-256 hex digest of the token (`hashlib.sha256(token.encode("ascii")).hexdigest()`) is stored as that request's `client_links.token_hash`.

**AC3: Tokens and links are unique**
- Given 50 requests created one after another
- When their tokens and hashes are compared
- Then all 50 tokens are different, all 50 hashes are different, and each request has exactly one link row.

**AC4: Expiry is exactly 24 hours, and the link starts unused**
- Given the clock is fixed at *T* (a dependency override on `utc_now`)
- When a request is created
- Then `created_at` is *T* and `expires_at` is *T* + 24 h, both ISO 8601 UTC (`+00:00`), in the response and in the database.
- And the stored link's `used_at` is empty (NULL).

**AC5: One transaction for the request, its claims and its link**
- Given storing the link fails (e.g. a token-hash collision, simulated by making the token generator return an existing token)
- When the request is created
- Then the response is **500** with no detail, and nothing from that request remains: no request, claim or link row.

**AC6: Schema version 2, existing demo files upgrade in place**
- Given a new database file
- When the app starts
- Then it applies `0001_initial.sql` and then `0002_client_links.sql`, and `PRAGMA user_version` is 2.
- And given a version-1 file holding requests made under #8, when the app starts, then it upgrades to version 2 and keeps those rows unchanged. They have no link row (there's no backfill).
- And a file with an unknown version (e.g. 3) is still refused with the "reset the demo file" message (#8 AC5).

**AC7: The raw token is never logged**
- Given logging is captured at DEBUG for every logger
- When requests are created
- Then no captured line contains a raw token (nor, as in #8 AC7, an expected value or API key). The only place a raw token ever appears is the 201 response body.

**AC8: Nothing else changes**
- Given the change is merged
- When the app's routes are listed
- Then they are still exactly `GET /health`, `POST /verification-requests` and FastAPI's docs routes. There's no `/client/…` route yet (#9). 401 and 422 behaviour from #8 is unchanged. `make check` passes, strictly typed, with no new exclusions.

**AC9: The response carrying the token isn't cached**
- Given a request is created
- When the 201 response is returned
- Then it has the header `Cache-Control: no-store`, so browsers and proxies keep no copy of the token (owner's G2 answer, 2026-11-26).

## 4. Out of scope
- `GET /client/{token}` and checking expiry or "used" (#9). Consent and setting `used_at` (#10).
- Redacting tokens from the access log (ADR 0003: required from #9, the first route with a token in its path). This slice's only route has no token in its path.
- Re-issuing, revoking or extending a link; more than one link per request.
- Backfilling links for requests created under #8: they keep no link, and #9 will treat them like any unknown token.
- A configurable public base URL (e.g. behind a proxy or a real domain). The link uses the request's own base URL, as FastAPI sees it.
- Purging expired, unused requests and their expected values: idea #15.
- Showing the link again later: there's no read endpoint, and the raw token can't be recovered from the hash by design. A lost link means creating a new request.

## 5. Design notes
- **Files / modules (new unless marked):**
  | File | Change | Protected |
  |---|---|---|
  | `app/links/__init__.py`, `app/links/tokens.py` | `LINK_LIFETIME = timedelta(hours=24)`; `new_link_token() -> str` (`secrets.token_urlsafe(32)`); `hash_token(token: str) -> str` (SHA-256 hex; #9 reuses it to look a token up); `utc_now() -> datetime` (aware UTC), used as a FastAPI dependency so tests can fix the clock | yes |
  | `app/migrations/0002_client_links.sql` | The `client_links` table (below); `PRAGMA user_version = 2` | yes |
  | `app/models/repository.py` (changed) | `insert_verification_request(conn, business, claims, created_at, token_hash, expires_at) -> str`: also inserts the link row, **inside the same `with conn:` transaction** | yes |
  | `app/models/verification_request.py` (changed) | `VerificationRequestCreated` gains `client_link: str` and `expires_at: str` | yes |
  | `app/api/verification_requests.py` (changed) | Takes `now: datetime = Depends(utc_now)`, `request: Request` and `response: Response`, and sets `response.headers["Cache-Control"] = "no-store"` (AC9). Uses `now` for `created_at` (replacing `datetime.now(UTC)`), computes `expires_at = now + LINK_LIFETIME`, makes the token, stores only `hash_token(token)`, and builds `client_link = f"{request.base_url}client/{token}"`. The raw token lives only in a local variable and the response | yes (`app/api/**`) |
  | `tests/test_client_link.py` (new); `tests/test_create_verification_request.py`, `tests/test_database.py` (changed) | See §6 | no |
  | `docs/product/ARCHITECTURE.md` (changed) | `app/links/`, the `client_links` table, schema version 2, "the raw token exists only in the 201 response" | no |
- **Data model (`0002_client_links.sql`, `STRICT`):**
  ```sql
  CREATE TABLE client_links (
      token_hash TEXT PRIMARY KEY CHECK (length(token_hash) = 64),
      request_id TEXT NOT NULL UNIQUE REFERENCES verification_requests (id),
      expires_at TEXT NOT NULL, -- ISO 8601 UTC
      used_at TEXT              -- NULL until #10 uses the link up
  ) STRICT;
  PRAGMA user_version = 2;
  ```
  It's additive, so existing version-1 files upgrade in place (`init_schema` already applies scripts in order, each in its own transaction). There's no down-migration: rolling back means deleting the demo file (synthetic data only).
- **Personal data:** none added. The token is a credential, not personal data. It's held only as a hash.
- **Why SHA-256 without a salt or key:** the token is 256 random bits, so it can't be found by guessing or precomputed tables. An unsalted hash is enough, and it lets #9 find the link by hashing the presented token and looking up the primary key. No secret key is needed, so there's no config or env var.
- **Config / env vars:** none.
- **External APIs:** none.
- **Error states and edge cases:**
  - A token-hash collision is practically impossible. If it happens, the primary key rejects it, the whole transaction rolls back, and the response is 500 (AC5). Don't retry silently.
  - `request.base_url` follows the `Host` header the caller sent. That's acceptable: the caller is the authenticated business, and the link only goes back to them. A fixed public URL is out of scope (§4).
  - 401 and 422 paths make no token at all (the key and body checks run before the endpoint body), so nothing is generated or stored for a refused request.
- **Tests that change, and why (no test is weakened):**
  - `test_create_request_returns_201_with_exact_keys`: the exact key set grows from 3 to 5 (AC1). It stays an exact-equality check.
  - `test_init_schema_sets_user_version_1` becomes `test_init_schema_sets_latest_user_version`, asserting 2 (AC6).
  - `row_counts` in `tests/test_database.py` also counts `client_links`, so every "stores nothing" test covers the new table.
  - `test_failed_insert_leaves_no_rows` passes the new arguments.

## 6. Test plan
| AC | Unit / integration test(s) | Notes |
|---|---|---|
| AC1 | `test_create_request_returns_201_with_exact_keys` (updated, 5 keys); `test_client_link_format` (base URL `http://testserver/`, path `client/<token>`, token regex) | |
| AC2 | `test_token_stored_only_as_hash` (`iterdump()` text contains no raw token; `token_hash` equals its SHA-256) | |
| AC3 | `test_tokens_and_hashes_unique` (50 requests; one link row each) | |
| AC4 | `test_expiry_is_24h_after_fixed_clock` (`app.dependency_overrides[utc_now]`); `test_link_stored_unused` | |
| AC5 | `test_link_insert_failure_returns_500_and_stores_nothing` (monkeypatch `new_link_token` to return one fixed token, create twice: the second gets 500, and the counts show only the first request) | `TestClient(..., raise_server_exceptions=False)` |
| AC6 | `test_init_schema_sets_latest_user_version` (renamed, 2); `test_version_1_file_upgrades_and_keeps_requests` (build a v1 file with `0001` only and one request, start the app, check version 2 and the row is intact); `test_unknown_schema_version_refuses_start` (existing) | |
| AC7 | `test_raw_token_never_logged` (`caplog` at DEBUG on the root logger) | Or extend #8's log test |
| AC8 | `test_routes_are_exactly` (existing, unchanged); the #8 401/422 tests pass unchanged except the `row_counts` extension | |
| AC9 | `test_201_response_is_not_cached` (`response.headers["cache-control"] == "no-store"`) | |

**UAT outline (owner, about 10 minutes, on `/docs`):**
1. Keep your `var/verify-my-client.sqlite3` from #8's test, which is at version 1. `make dev`, then `sqlite3 var/verify-my-client.sqlite3 "pragma user_version; select count(*) from verification_requests;"` → version 2, and your #8 requests are still there.
2. **Authorize** with `demo-key-solicitor` and POST the full body from #8 → 201 with five keys, including `client_link` (`http://127.0.0.1:8000/client/…`) and `expires_at` exactly 24 hours after `created_at`. The response headers include `cache-control: no-store`.
3. POST again → a different `id` and a different token.
4. Copy the token (the part after `/client/`), then in a terminal: `printf %s '<token>' | shasum -a 256` and `sqlite3 var/verify-my-client.sqlite3 "select token_hash, expires_at, used_at from client_links;"` → your hash is in the list, the raw token isn't anywhere (`sqlite3 var/verify-my-client.sqlite3 .dump | grep '<token>'` prints nothing), and `used_at` is empty.
5. Open the `client_link` in a browser → 404. That's expected: opening links is #9.
6. Repeat #8's 401 and 422 checks (no key; `{"claims": [{"type": "passport"}]}`) → unchanged, and no new link rows.

## 7. Rollout and rollback
- **Feature flag:** none. It's an API with no users and no deploy target.
- **Rollout:** merge. Existing demo files upgrade to version 2 at the next start.
- **Rollback:** revert the PR. A demo file already at version 2 is then refused by the older code ("unknown version"): delete `var/verify-my-client.sqlite3` (synthetic data only).

## 8. Slices (if split)
Not split. Estimate: about 90 lines of app code and SQL, and about 130 lines of tests, so about 220 changed lines, within the 400 target.

## 9. Open questions
None. The owner answered at G2 (2026-11-26):
1. `app/api/**` is protected: added to `protected_paths` in PR #17, so the release gate lists the router too.
2. `Cache-Control: no-store` on the 201 response: yes, it's AC9.
