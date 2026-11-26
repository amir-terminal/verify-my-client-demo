# UAT plan: #8 Create a verification request (demo API keys, SQLite storage)

- **Issue:** #8 (slice 1 of epic #7) · **PR:** none yet (test-first: `/test` opens it after your pass) · **Spec:** docs/specs/GH-8-create-verification-request.md
- **Estimated time:** ~10 minutes

## Setup (local)
```bash
git fetch origin
git switch --detach origin/8-create-verification-request   # detached: works even while the agent's worktree has the branch
make setup
make dev
# when done: git switch main
```
- Open: http://127.0.0.1:8000/docs
- Test accounts (synthetic, obviously fake API keys): `demo-key-solicitor`, `demo-key-estate-agent`, `demo-key-accountant`
- Feature flag: none
- The database is created at `var/verify-my-client.sqlite3` on first start (git-ignored, synthetic data only). To start clean, stop `make dev` and delete that file.

**How to send a request on `/docs`:** open **POST /verification-requests** → **Try it out**, paste the body, then **Execute**. To use a key, click **Authorize** (top right), paste the key and click **Authorize**. Use **Logout** in the same dialog to remove it.

The full valid body (synthetic data) used below:
```json
{"claims": [{"type": "name", "expected": "Alex Example"}, {"type": "over_18"}, {"type": "confirmed_address", "expected": "1 Example Street, Testtown, ZZ1 1ZZ"}]}
```

## Test cases
| # | AC | Steps | Expected result | Pass? |
|---|---|---|---|---|
| 1 | AC8 | 1. Open `/docs`. | Exactly two endpoints: `GET /health` and `POST /verification-requests`. | [ ] |
| 2 | AC2 | 1. Don't authorise. 2. POST the full valid body. | **401**, body `{"detail": "Missing or unknown API key"}`. | [ ] |
| 3 | AC2 | 1. **Authorize** with `demo-key-nobody`. 2. POST the full valid body. 3. Repeat with `DEMO-KEY-SOLICITOR`. 4. **Logout** afterwards. | **401** with the same body as case 2, both times. | [ ] |
| 4 | AC1 | 1. **Authorize** with `demo-key-solicitor`. 2. POST the full valid body. | **201** with exactly `id` (a UUID), `claims` = `["name", "over_18", "confirmed_address"]` and `created_at` (a UTC time ending `+00:00`). No name, address, key or business in the response. | [ ] |
| 5 | AC1 | 1. Still authorised, POST the claims in reverse order (`confirmed_address`, `over_18`, `name`). 2. POST `{"claims": [{"type": "over_18"}]}`. | 1. **201**, claims still in the order `name`, `over_18`, `confirmed_address`. 2. **201**, `claims` = `["over_18"]`. | [ ] |
| 6 | AC3, AC4 | Still authorised, POST each body in turn: a. `{"claims": [{"type": "passport"}]}` b. `{"claims": [{"type": "over_18"}, {"type": "over_18"}]}` c. `{"claims": [{"type": "over_18", "expected": "Alex Example"}]}` d. `{"claims": [{"type": "name", "expected": "Alex Example"}], "date_of_birth": "1999-12-31"}` e. `{"claims": [{"type": "name"}]}` f. `{"claims": [{"type": "name", "expected": "   "}]}` g. `{"claims": []}` | Each one gets **422**. Each error has only `type`, `loc` and `msg`. None of the values you typed (`Alex Example`, `1999-12-31`) appear anywhere in the response. | [ ] |
| 7 | AC5, AC3 | 1. Stop `make dev` (Ctrl+C) and start it again. 2. In another terminal: `sqlite3 var/verify-my-client.sqlite3 "select count(*) from verification_requests; select claim_type, expected_value from request_claims;"` | The requests from cases 4–5 are still there (3 if you started clean). Expected values are stored as typed, with the spaces at each end trimmed. None of the refused requests from cases 2, 3 and 6 were stored. | [ ] |
| 8 | AC3 edge | 1. Authorised, POST `{"claims": [{"type": "name", "expected": "   Zoë Example  "}]}`. 2. Run the `sqlite3` command from case 7 again. | **201**. The newest `name` row reads `Zoë Example`, with no spaces at either end. | [ ] |
| 9 | AC1 | 1. **Authorize** with `demo-key-accountant`. 2. POST the full valid body. | **201** with an `id` different from every earlier one. | [ ] |
| 10 | AC7 | Look over the `make dev` terminal output from all the cases above. | Request lines show only method, path and status: no name, address, date or API key. | [ ] |
| 11 | Regression | Open http://127.0.0.1:8000/health. | `{"status":"ok"}`, exactly as before. | [ ] |

## Not in scope for this test
- The client link (`client_link`, `expires_at`): that's #14.
- Opening the link, consent, results and audit records: #9–#12.
- How names and addresses are matched (case, postcode format): #11.
- Listing, reading or deleting requests: there's no endpoint for it in this slice.
- Removing expected values from requests that never get a result: idea #15.

## Agent pre-check
- **Fully verified by the agent:** no (a protected area: `human-review`, so you review the code and test it yourself)
- **Needs a person:** yes (protected areas: auth, claims, models, migrations, privacy, api)
- **Verified at:** 31687dd12fc4463169e6ff3db600113760c9584d
- **Risk:** medium: the first storage and auth code that later slices build on. No users, and nothing is deployed.
- **Undo:** revert the PR, and delete `var/verify-my-client.sqlite3` locally (synthetic data only).
- Evidence (`make check`: ruff, strict mypy, 49 tests pass; `make audit` unaffected, since no dependency changed):
  - AC1: `test_create_request_returns_201_with_exact_keys` (all 3 keys), `test_claims_returned_in_fixed_order`, `test_response_has_no_expected_values_or_business`, `test_single_claim_subset`, `test_ids_unique`
  - AC2: `test_missing_key_401`, `test_unknown_key_401` (wrong, wrong case, empty), `test_401_stores_nothing`
  - AC3: `test_invalid_body_422_stores_nothing` (17 cases), `test_non_json_body_422_stores_nothing`, `test_expected_value_stored_trimmed`, `test_bad_key_with_bad_body_stores_nothing`
  - AC4: `test_422_body_has_no_input`, `test_422_messages_never_repeat_expected_values`
  - AC5: `test_survives_restart`, `test_init_schema_sets_user_version_1`, `test_unknown_schema_version_refuses_start`
  - AC6: `test_failed_insert_leaves_no_rows`, `test_failed_insert_through_api_returns_500_and_stores_nothing`
  - AC7: `test_no_personal_data_in_logs` (caplog at DEBUG, root logger)
  - AC8: `test_routes_are_exactly` (the #5 route test, extended), the `/health` tests unchanged. After the test run `git status` is clean and no `var/` is created.
  - Smoke run of the real module-level app: create, restart, then read back the rows with `sqlite3`. `user_version` is 1.
  - Security self-review (`/security-review`): no findings at high confidence.

## Results
Recorded as comments on the issue and the PR by `/test` (or `/uat-result`), so recording a result never changes the code that was tested.
