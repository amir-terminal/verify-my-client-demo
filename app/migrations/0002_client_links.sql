-- 0002: one client link per verification request (spec GH-14, ADR 0003).
-- Only the SHA-256 hash of the token is stored, never the token itself.
-- Applied by app.models.database.init_schema inside one transaction.

CREATE TABLE client_links (
    token_hash TEXT PRIMARY KEY CHECK (length(token_hash) = 64),
    request_id TEXT NOT NULL UNIQUE REFERENCES verification_requests (id),
    expires_at TEXT NOT NULL, -- ISO 8601 UTC
    used_at TEXT              -- NULL until #10 uses the link up
) STRICT;

PRAGMA user_version = 2;
