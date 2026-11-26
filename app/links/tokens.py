"""Client link tokens (spec GH-14).

A token is 256 random bits, URL-safe. Only its SHA-256 hash is stored, so a copy
of the database can't open links. The raw token exists only in the 201 response.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

LINK_LIFETIME = timedelta(hours=24)


def new_link_token() -> str:
    """A fresh unguessable token: 43 URL-safe characters (32 random bytes)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """The SHA-256 hex digest stored for a token, and used to look it up (#9).

    No salt or key is needed: the token itself is 256 random bits.
    """
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def utc_now() -> datetime:
    """The current time, aware UTC. A FastAPI dependency, so tests can fix the clock."""
    return datetime.now(UTC)
