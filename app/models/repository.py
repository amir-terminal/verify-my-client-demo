"""Writes verification requests to SQLite. Parameterised SQL only (ADR 0003)."""

import sqlite3
import uuid
from collections.abc import Sequence
from datetime import datetime

from app.auth.businesses import DemoBusiness
from app.models.verification_request import RequestedClaim


def insert_verification_request(
    conn: sqlite3.Connection,
    business: DemoBusiness,
    claims: Sequence[RequestedClaim],
    created_at: datetime,
) -> str:
    """Store a request and its claims in one transaction; return the new id."""
    request_id = str(uuid.uuid4())
    with conn:  # commits on success, rolls back everything on any error
        conn.execute(
            "INSERT INTO verification_requests (id, business_id, created_at)"
            " VALUES (?, ?, ?)",
            (request_id, business.id, created_at.isoformat()),
        )
        _insert_claims(conn, request_id, claims)
    return request_id


def _insert_claims(
    conn: sqlite3.Connection, request_id: str, claims: Sequence[RequestedClaim]
) -> None:
    conn.executemany(
        "INSERT INTO request_claims (request_id, claim_type, expected_value)"
        " VALUES (?, ?, ?)",
        [(request_id, claim.type.value, claim.expected) for claim in claims],
    )
