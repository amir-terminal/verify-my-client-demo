"""Tests for the client link on POST /verification-requests (spec GH-14)."""

import hashlib
import logging
import re
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.links import tokens
from app.main import create_app
from tests.synthetic import (
    FULL_BODY,
    SOLICITOR_KEY,
    SYNTHETIC_ADDRESS,
    SYNTHETIC_NAME,
    row_counts,
)

URL = "/verification-requests"
LINK_PREFIX = "http://testserver/client/"
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")
FIXED_NOW = datetime(2026, 11, 26, 9, 30, 15, 123456, tzinfo=UTC)


def create(client: TestClient, key: str = SOLICITOR_KEY) -> Any:
    return client.post(URL, json=FULL_BODY, headers={"X-API-Key": key})


def token_of(body: dict[str, Any]) -> str:
    link = body["client_link"]
    assert isinstance(link, str)
    assert link.startswith(LINK_PREFIX)
    return link.removeprefix(LINK_PREFIX)


def link_rows(db_path: Path) -> list[tuple[Any, ...]]:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT token_hash, request_id, expires_at, used_at FROM client_links"
        ).fetchall()
    finally:
        conn.close()


# AC1: the create response includes the link


def test_client_link_format(client: TestClient) -> None:
    response = create(client)

    assert response.status_code == 201
    token = token_of(response.json())
    assert TOKEN_PATTERN.fullmatch(token)
    for value in (SYNTHETIC_NAME, SYNTHETIC_ADDRESS, SOLICITOR_KEY, "demo-solicitor"):
        assert value not in response.text


# AC2: only a hash of the token is stored


def test_token_stored_only_as_hash(client: TestClient, db_path: Path) -> None:
    body = create(client).json()
    token = token_of(body)

    conn = sqlite3.connect(db_path)
    try:
        dump = "\n".join(conn.iterdump())
        stored = conn.execute(
            "SELECT token_hash FROM client_links WHERE request_id = ?", (body["id"],)
        ).fetchone()
    finally:
        conn.close()

    assert token not in dump
    assert stored == (hashlib.sha256(token.encode("ascii")).hexdigest(),)
    assert tokens.hash_token(token) == stored[0]


# AC3: tokens and links are unique


def test_tokens_and_hashes_unique(client: TestClient, db_path: Path) -> None:
    bodies = [create(client).json() for _ in range(50)]
    created_tokens = {token_of(body) for body in bodies}
    rows = link_rows(db_path)

    assert len(created_tokens) == 50
    assert len({row[0] for row in rows}) == 50
    assert sorted(row[1] for row in rows) == sorted(body["id"] for body in bodies)


# AC4: expiry is exactly 24 hours, and the link starts unused


@pytest.fixture
def fixed_clock_client(db_path: Path) -> Iterator[TestClient]:
    app = create_app(db_path)
    app.dependency_overrides[tokens.utc_now] = lambda: FIXED_NOW
    with TestClient(app) as test_client:
        yield test_client


def test_expiry_is_24h_after_fixed_clock(
    fixed_clock_client: TestClient, db_path: Path
) -> None:
    body = create(fixed_clock_client).json()
    expected_expiry = FIXED_NOW + timedelta(hours=24)

    assert body["created_at"] == FIXED_NOW.isoformat()
    assert body["expires_at"] == expected_expiry.isoformat()
    assert body["expires_at"].endswith("+00:00")
    conn = sqlite3.connect(db_path)
    try:
        stored_created = conn.execute(
            "SELECT created_at FROM verification_requests WHERE id = ?", (body["id"],)
        ).fetchone()
    finally:
        conn.close()
    assert stored_created == (FIXED_NOW.isoformat(),)
    assert [row[2] for row in link_rows(db_path)] == [expected_expiry.isoformat()]


def test_link_stored_unused(client: TestClient, db_path: Path) -> None:
    body = create(client).json()

    rows = link_rows(db_path)

    assert len(rows) == 1
    assert rows[0][1] == body["id"]
    assert rows[0][3] is None


# AC5: one transaction for the request, its claims and its link


def test_link_insert_failure_returns_500_and_stores_nothing(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repeated = "A" * 43
    monkeypatch.setattr(tokens, "new_link_token", lambda: repeated)

    with TestClient(create_app(db_path), raise_server_exceptions=False) as client:
        first = create(client)
        second = create(client)

    assert first.status_code == 201
    assert second.status_code == 500
    assert second.text == "Internal Server Error"
    # Only the first request remains: its 1 request, 3 claims and 1 link.
    assert row_counts(db_path) == (1, 3, 1)
    assert [row[1] for row in link_rows(db_path)] == [first.json()["id"]]


# AC7: the raw token is never logged


def test_raw_token_never_logged(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)

    created = [token_of(create(client).json()) for _ in range(3)]

    logged = "\n".join(record.getMessage() for record in caplog.records)
    for value in (*created, SYNTHETIC_NAME, SYNTHETIC_ADDRESS, SOLICITOR_KEY):
        assert value not in logged


# AC9: the response carrying the token isn't cached


def test_201_response_is_not_cached(client: TestClient) -> None:
    response = create(client)

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
