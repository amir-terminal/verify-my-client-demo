"""Synthetic test data and helpers shared by the tests. Never real personal data."""

import sqlite3
from pathlib import Path
from typing import Any

# Synthetic values only: made-up people and places that resemble no one real.
SYNTHETIC_NAME = "Alex Example"
SYNTHETIC_ADDRESS = "1 Example Street, Testtown, ZZ1 1ZZ"
SOLICITOR_KEY = "demo-key-solicitor"

FULL_BODY: dict[str, Any] = {
    "claims": [
        {"type": "name", "expected": SYNTHETIC_NAME},
        {"type": "over_18"},
        {"type": "confirmed_address", "expected": SYNTHETIC_ADDRESS},
    ]
}


def row_counts(db_path: Path) -> tuple[int, int, int]:
    """Rows in (verification_requests, request_claims, client_links)."""
    conn = sqlite3.connect(db_path)
    try:
        counts = tuple(
            int(conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
            for table in ("verification_requests", "request_claims", "client_links")
        )
    finally:
        conn.close()
    return counts[0], counts[1], counts[2]
