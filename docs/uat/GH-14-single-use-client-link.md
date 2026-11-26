# UAT plan: #14 Single-use client link for a verification request (token stored as a hash, 24 h expiry)

- **Issue:** #14 (slice 1b of epic #7) · **PR:** none yet (test-first: `/test` opens it after your pass) · **Spec:** docs/specs/GH-14-single-use-client-link.md
- **Estimated time:** ~10 minutes

## Setup (local)
```bash
git fetch origin
git switch --detach origin/14-single-use-client-link   # detached: works even while the agent's worktree has the branch
make setup
# Before the first start: keep var/verify-my-client.sqlite3 from your #8 test (it's at version 1), for case 1.
make dev
# when done: git switch main
```
- Open: http://127.0.0.1:8000/docs
- Test accounts (synthetic, obviously fake API keys): `demo-key-solicitor`, `demo-key-estate-agent`, `demo-key-accountant`
- Feature flag: none
- No #8 file any more? Skip case 1's "still there" part: a new file is created at version 2.

**How to send a request on `/docs`:** open **POST /verification-requests** → **Try it out**, paste the body, then **Execute**. Use **Authorize** (top right) to set the key. The response headers are shown under the response body.

The full valid body (synthetic data) used below:
```json
{"claims": [{"type": "name", "expected": "Alex Example"}, {"type": "over_18"}, {"type": "confirmed_address", "expected": "1 Example Street, Testtown, ZZ1 1ZZ"}]}
```

## Test cases
| # | AC | Steps | Expected result | Pass? |
|---|---|---|---|---|
| 1 | AC6 | 1. Before starting, note your count: `sqlite3 var/verify-my-client.sqlite3 "pragma user_version; select count(*) from verification_requests;"` 2. `make dev`. 3. Run the same command again. | Before: `1` and your #8 count. After: `2` and the same count. | [ ] |
| 2 | AC1, AC4, AC9 | 1. **Authorize** with `demo-key-solicitor`. 2. POST the full valid body. | **201** with exactly `id`, `claims`, `created_at`, `client_link`, `expires_at`. `client_link` looks like `http://127.0.0.1:8000/client/` + 43 letters, digits, `-` or `_`. `expires_at` is exactly 24 hours after `created_at`, both ending `+00:00`. Response headers include `cache-control: no-store`. No name, address, key or business in the body. | [ ] |
| 3 | AC3 | POST the same body again. | A different `id` and a different token in `client_link`. | [ ] |
| 4 | AC2, AC4 | Copy the token from case 2 (everything after `/client/`). In a terminal: a. `printf %s '<token>' \| shasum -a 256` b. `sqlite3 var/verify-my-client.sqlite3 "select token_hash, expires_at, used_at from client_links;"` c. `sqlite3 var/verify-my-client.sqlite3 .dump \| grep -c '<token>'` | a's hash is one of the `token_hash` values in b, with the `expires_at` from case 2 and an empty `used_at`. c prints `0`: the raw token isn't stored anywhere. | [ ] |
| 5 | AC7 | Look over the `make dev` terminal output from cases 2–3. | Only lines like `"POST /verification-requests HTTP/1.1" 201`: no token, name, address or key. | [ ] |
| 6 | AC6 | `sqlite3 var/verify-my-client.sqlite3 "select count(*) from verification_requests where id not in (select request_id from client_links);"` | Your #8 count from case 1: old requests have no link (no backfill), every new one has exactly one. | [ ] |
| 7 | AC8 | 1. **Logout**, POST the full body (no key). 2. **Authorize** with `demo-key-solicitor`, POST `{"claims": [{"type": "passport"}]}`. 3. Run 4b again. | 1. **401** `{"detail": "Missing or unknown API key"}`. 2. **422**. 3. No new link rows. | [ ] |
| 8 | AC8 | 1. Refresh `/docs`. 2. Open http://127.0.0.1:8000/health. | 1. Still only `GET /health` and `POST /verification-requests`. 2. `{"status":"ok"}`. | [ ] |

## Not in scope for this test
- Opening the link: `client_link` gives **404** for now, and that is expected (#9). **Don't paste a real link into the browser while `make dev` runs if you mind it in the terminal:** uvicorn's access log prints the full path of any request, so a 404 for `/client/<token>` shows that token. #9 redacts `/client/…` paths from the log when it adds the route (ADR 0003).
- Expiry and single use being enforced (#9, #10). Re-issuing or revoking a link.
- Seeing a link again later: only its hash is kept, so a lost link means a new request.

## Agent pre-check
- **Fully verified by the agent:** no (a protected area: `human-review`, so you review the code and test it yourself)
- **Needs a person:** yes (protected areas: api, links, models, migrations)
- **Verified at:** fb402501399bd1a5987e1fdb444086a3f6103d6a
- **Risk:** medium: a new credential (the link token) and the first schema upgrade on existing files. No users, nothing deployed.
- **Undo:** revert the PR, and delete `var/verify-my-client.sqlite3` locally (older code refuses a version-2 file; synthetic data only).
- Evidence (`make check`: ruff, strict mypy, 58 tests pass; no dependency changed):
  - AC1: `test_create_request_returns_201_with_exact_keys` (5 keys, all 3 demo keys), `test_client_link_format`
  - AC2: `test_token_stored_only_as_hash` (`iterdump()` holds no raw token; stored hash = SHA-256)
  - AC3: `test_tokens_and_hashes_unique` (50 requests, one link row each)
  - AC4: `test_expiry_is_24h_after_fixed_clock` (clock fixed through `utc_now` override), `test_link_stored_unused`
  - AC5: `test_link_insert_failure_returns_500_and_stores_nothing` (repeated token → 500, counts `(1, 3, 1)`)
  - AC6: `test_init_schema_sets_latest_user_version`, `test_version_1_file_upgrades_and_keeps_requests`, `test_unknown_schema_version_refuses_start`
  - AC7: `test_raw_token_never_logged` (caplog at DEBUG), `test_no_personal_data_in_logs`
  - AC8: `test_routes_are_exactly` (unchanged); all #8 401/422 tests, with `row_counts` now also counting `client_links`
  - AC9: `test_201_response_is_not_cached`
  - Smoke run of the real app under uvicorn on a version-1 file: upgraded to 2 with the old row kept; 201 with 5 keys and `cache-control: no-store`; stored hash matches `shasum -a 256`; raw token in neither `.dump` nor the server log; `/client/<token>` → 404.
  - Security self-review (`/security-review`): no findings at high confidence.

## Results
Recorded as comments on the issue and the PR by `/test` (or `/uat-result`), so recording a result never changes the code that was tested.
