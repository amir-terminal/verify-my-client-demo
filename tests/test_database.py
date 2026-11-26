"""Tests for SQLite storage (spec GH-8, AC5 and AC6; GH-14 AC6)."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

import pytest
from fastapi.testclient import TestClient

from app.auth.businesses import DEMO_BUSINESSES
from app.links.tokens import LINK_LIFETIME, hash_token
from app.main import create_app
from app.models import repository
from app.models.database import (
    MIGRATIONS_DIR,
    SchemaVersionError,
    connect,
    init_schema,
)
from app.models.verification_request import CreateVerificationRequest
from tests.synthetic import FULL_BODY, SOLICITOR_KEY, SYNTHETIC_NAME, row_counts


def test_survives_restart(db_path: Path) -> None:
    with TestClient(create_app(db_path)) as first:
        created = first.post(
            "/verification-requests",
            json=FULL_BODY,
            headers={"X-API-Key": SOLICITOR_KEY},
        ).json()

    # A second app on the same file: the schema is already there and the rows remain.
    with TestClient(create_app(db_path)):
        conn = sqlite3.connect(db_path)
        try:
            business_id = conn.execute(
                "SELECT business_id FROM verification_requests WHERE id = ?",
                (created["id"],),
            ).fetchone()
            claims = conn.execute(
                "SELECT claim_type, expected_value FROM request_claims"
                " WHERE request_id = ? ORDER BY claim_type",
                (created["id"],),
            ).fetchall()
        finally:
            conn.close()

    assert business_id == ("demo-solicitor",)
    assert claims == [
        ("confirmed_address", "1 Example Street, Testtown, ZZ1 1ZZ"),
        ("name", SYNTHETIC_NAME),
        ("over_18", None),
    ]


def test_init_schema_sets_latest_user_version(db_path: Path) -> None:
    init_schema(db_path)
    init_schema(db_path)  # running again on an up-to-date file changes nothing

    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("PRAGMA user_version").fetchone() == (2,)
    finally:
        conn.close()
    assert row_counts(db_path) == (0, 0, 0)


# GH-14 AC6: a version-1 file from #8 upgrades in place and keeps its rows


def test_version_1_file_upgrades_and_keeps_requests(db_path: Path) -> None:
    migration_0001 = MIGRATIONS_DIR / "0001_initial.sql"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(migration_0001.read_text())
        conn.execute(
            "INSERT INTO verification_requests (id, business_id, created_at)"
            " VALUES ('v1-request', 'demo-solicitor', '2026-11-01T09:00:00+00:00')"
        )
        conn.execute(
            "INSERT INTO request_claims (request_id, claim_type, expected_value)"
            " VALUES ('v1-request', 'name', ?)",
            (SYNTHETIC_NAME,),
        )
        conn.commit()
        assert conn.execute("PRAGMA user_version").fetchone() == (1,)
    finally:
        conn.close()

    with TestClient(create_app(db_path)):
        pass

    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("PRAGMA user_version").fetchone() == (2,)
        assert conn.execute("SELECT * FROM verification_requests").fetchall() == [
            ("v1-request", "demo-solicitor", "2026-11-01T09:00:00+00:00")
        ]
        assert conn.execute("SELECT * FROM request_claims").fetchall() == [
            ("v1-request", "name", SYNTHETIC_NAME)
        ]
    finally:
        conn.close()
    assert row_counts(db_path) == (1, 1, 0)  # no backfill: the old request has no link


def test_unknown_schema_version_refuses_start(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA user_version = 99")
    conn.close()

    app = create_app(db_path)
    with (
        pytest.raises(SchemaVersionError, match="Reset the demo file"),
        TestClient(app),
    ):
        pass


def test_failed_insert_leaves_no_rows(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    init_schema(db_path)

    def fail_after_first_insert(*args: object) -> NoReturn:
        raise sqlite3.OperationalError("simulated failure")

    monkeypatch.setattr(repository, "_insert_claims", fail_after_first_insert)
    claims = CreateVerificationRequest.model_validate(FULL_BODY).ordered_claims()
    conn = connect(db_path)
    try:
        with pytest.raises(sqlite3.OperationalError):
            now = datetime.now(UTC)
            repository.insert_verification_request(
                conn,
                DEMO_BUSINESSES[0],
                claims,
                created_at=now,
                token_hash=hash_token("synthetic-token"),
                expires_at=now + LINK_LIFETIME,
            )
    finally:
        conn.close()

    assert row_counts(db_path) == (0, 0, 0)


def test_failed_insert_through_api_returns_500_and_stores_nothing(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: object) -> NoReturn:
        raise sqlite3.OperationalError("simulated failure")

    monkeypatch.setattr(repository, "_insert_claims", fail)
    with TestClient(create_app(db_path), raise_server_exceptions=False) as client:
        response = client.post(
            "/verification-requests",
            json=FULL_BODY,
            headers={"X-API-Key": SOLICITOR_KEY},
        )

    assert response.status_code == 500
    assert SYNTHETIC_NAME not in response.text
    assert row_counts(db_path) == (0, 0, 0)
