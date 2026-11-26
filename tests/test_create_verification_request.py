"""Tests for POST /verification-requests (spec GH-8, AC1–AC3 and AC7; GH-14 AC1)."""

import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.auth.businesses import DEMO_BUSINESSES
from tests.synthetic import (
    FULL_BODY,
    SOLICITOR_KEY,
    SYNTHETIC_ADDRESS,
    SYNTHETIC_NAME,
    row_counts,
)

URL = "/verification-requests"
DEMO_KEYS = [business.api_key for business in DEMO_BUSINESSES]
UNAUTHORISED = {"detail": "Missing or unknown API key"}


def post(client: TestClient, body: Any, key: str | None = SOLICITOR_KEY) -> Any:
    headers = {} if key is None else {"X-API-Key": key}
    return client.post(URL, json=body, headers=headers)


# AC1: create a request with a demo key


@pytest.mark.parametrize("key", DEMO_KEYS)
def test_create_request_returns_201_with_exact_keys(
    client: TestClient, key: str
) -> None:
    response = post(client, FULL_BODY, key)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "claims", "created_at", "client_link", "expires_at"}
    assert uuid.UUID(body["id"]).version == 4
    created_at = datetime.fromisoformat(body["created_at"])
    assert created_at.utcoffset() is not None
    assert created_at.utcoffset().total_seconds() == 0  # type: ignore[union-attr]


def test_claims_returned_in_fixed_order(client: TestClient) -> None:
    body = {"claims": list(reversed(FULL_BODY["claims"]))}

    response = post(client, body)

    assert response.json()["claims"] == ["name", "over_18", "confirmed_address"]


def test_response_has_no_expected_values_or_business(client: TestClient) -> None:
    text = post(client, FULL_BODY).text

    for value in (SYNTHETIC_NAME, SYNTHETIC_ADDRESS, SOLICITOR_KEY, "demo-solicitor"):
        assert value not in text


@pytest.mark.parametrize(
    "claims",
    [
        [{"type": "over_18"}],
        [{"type": "name", "expected": SYNTHETIC_NAME}],
        [{"type": "confirmed_address", "expected": SYNTHETIC_ADDRESS}],
        [{"type": "over_18"}, {"type": "name", "expected": SYNTHETIC_NAME}],
    ],
)
def test_single_claim_subset(client: TestClient, claims: list[dict[str, str]]) -> None:
    response = post(client, {"claims": claims})

    assert response.status_code == 201
    requested = {claim["type"] for claim in claims}
    fixed_order = ["name", "over_18", "confirmed_address"]
    assert response.json()["claims"] == [c for c in fixed_order if c in requested]


def test_ids_unique(client: TestClient) -> None:
    first = post(client, FULL_BODY).json()["id"]
    second = post(client, FULL_BODY, "demo-key-accountant").json()["id"]

    assert first != second


# AC2: missing or unknown API key → 401


def test_missing_key_401(client: TestClient, db_path: Path) -> None:
    response = post(client, FULL_BODY, key=None)

    assert response.status_code == 401
    assert response.json() == UNAUTHORISED
    assert row_counts(db_path) == (0, 0, 0)


@pytest.mark.parametrize("key", ["demo-key-nobody", "DEMO-KEY-SOLICITOR", ""])
def test_unknown_key_401(client: TestClient, key: str) -> None:
    response = post(client, FULL_BODY, key)

    assert response.status_code == 401
    assert response.json() == UNAUTHORISED


@pytest.mark.parametrize("key", [None, "demo-key-nobody", ""])
def test_401_stores_nothing(client: TestClient, db_path: Path, key: str | None) -> None:
    post(client, FULL_BODY, key)

    assert row_counts(db_path) == (0, 0, 0)


# AC3: invalid claims → 422, nothing stored

NAME = {"type": "name", "expected": SYNTHETIC_NAME}
INVALID_BODIES: dict[str, Any] = {
    "empty claims": {"claims": []},
    "unknown claim type": {"claims": [{"type": "passport"}]},
    "duplicate claim": {"claims": [{"type": "over_18"}, {"type": "over_18"}]},
    "name without expected": {"claims": [{"type": "name"}]},
    "address without expected": {"claims": [{"type": "confirmed_address"}]},
    "name with null expected": {"claims": [{"type": "name", "expected": None}]},
    "empty expected": {"claims": [{"type": "name", "expected": ""}]},
    "whitespace expected": {"claims": [{"type": "name", "expected": "   "}]},
    "expected over 200": {"claims": [{"type": "name", "expected": "x" * 201}]},
    "expected on over_18": {"claims": [{"type": "over_18", "expected": "yes"}]},
    "null expected on over_18": {"claims": [{"type": "over_18", "expected": None}]},
    "extra top-level field": {"claims": [NAME], "date_of_birth": "2000-01-01"},
    "extra claim field": {"claims": [{**NAME, "date_of_birth": "2000-01-01"}]},
    "claims as object": {"claims": {"type": "over_18"}},
    "expected wrongly typed": {"claims": [{"type": "name", "expected": 42}]},
    "body is a list": [NAME],
    "no body": None,
}


@pytest.mark.parametrize("body", INVALID_BODIES.values(), ids=INVALID_BODIES.keys())
def test_invalid_body_422_stores_nothing(
    client: TestClient, db_path: Path, body: Any
) -> None:
    response = post(client, body)

    assert response.status_code == 422
    assert row_counts(db_path) == (0, 0, 0)


def test_non_json_body_422_stores_nothing(client: TestClient, db_path: Path) -> None:
    response = client.post(
        URL,
        content=b"claims=name",
        headers={"X-API-Key": SOLICITOR_KEY, "Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert row_counts(db_path) == (0, 0, 0)


def test_expected_value_stored_trimmed(client: TestClient, db_path: Path) -> None:
    body = {
        "claims": [
            {"type": "name", "expected": "  Zoë Example \n"},
            {"type": "confirmed_address", "expected": " " + "y" * 200 + " "},
        ]
    }

    assert post(client, body).status_code == 201

    conn = sqlite3.connect(db_path)
    try:
        rows = dict(
            conn.execute("SELECT claim_type, expected_value FROM request_claims")
        )
    finally:
        conn.close()
    assert rows == {"name": "Zoë Example", "confirmed_address": "y" * 200}


def test_bad_key_with_bad_body_stores_nothing(
    client: TestClient, db_path: Path
) -> None:
    response = post(client, {"claims": [{"type": "passport"}]}, key="demo-key-nobody")

    assert response.status_code in (401, 422)
    assert row_counts(db_path) == (0, 0, 0)


# AC7: no personal data in logs


def test_no_personal_data_in_logs(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)

    post(client, FULL_BODY)
    post(client, FULL_BODY, key="demo-key-nobody")
    post(client, {"claims": [{**NAME, "date_of_birth": "2000-01-01"}]})

    logged = "\n".join(record.getMessage() for record in caplog.records)
    secrets = (SYNTHETIC_NAME, SYNTHETIC_ADDRESS, "2000-01-01", "demo-key-nobody")
    for value in (*secrets, *DEMO_KEYS):
        assert value not in logged
