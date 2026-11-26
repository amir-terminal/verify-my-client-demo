-- 0001: verification requests and the claims they ask for (spec GH-8, ADR 0003).
-- Applied by app.models.database.init_schema inside one transaction.

CREATE TABLE verification_requests (
    id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,
    created_at TEXT NOT NULL -- ISO 8601 UTC
) STRICT;

CREATE TABLE request_claims (
    request_id TEXT NOT NULL REFERENCES verification_requests (id),
    claim_type TEXT NOT NULL
        CHECK (claim_type IN ('name', 'over_18', 'confirmed_address')),
    -- Nullable for name and confirmed_address too: #11 deletes it once the result exists.
    expected_value TEXT,
    PRIMARY KEY (request_id, claim_type),
    CHECK (claim_type <> 'over_18' OR expected_value IS NULL)
) STRICT;

PRAGMA user_version = 1;
