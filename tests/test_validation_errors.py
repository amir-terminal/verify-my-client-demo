"""Tests for the app-wide 422 handler (spec GH-8, AC4)."""

from fastapi.testclient import TestClient

from tests.synthetic import SOLICITOR_KEY, SYNTHETIC_NAME


def test_422_body_has_no_input(client: TestClient) -> None:
    body = {
        "claims": [{"type": "name", "expected": SYNTHETIC_NAME}],
        "date_of_birth": "1999-12-31",
    }

    response = client.post(
        "/verification-requests", json=body, headers={"X-API-Key": SOLICITOR_KEY}
    )

    assert response.status_code == 422
    assert SYNTHETIC_NAME not in response.text
    assert "1999-12-31" not in response.text
    errors = response.json()["detail"]
    assert errors
    for error in errors:
        assert set(error) == {"type", "loc", "msg"}


def test_422_messages_never_repeat_expected_values(client: TestClient) -> None:
    long_value = "Alex " * 50  # over 200 characters once trimmed
    bodies = [
        {"claims": [{"type": "over_18", "expected": SYNTHETIC_NAME}]},
        {"claims": [{"type": "name", "expected": long_value}]},
        {"claims": [{"type": "name", "expected": SYNTHETIC_NAME}] * 2},
    ]

    for body in bodies:
        response = client.post(
            "/verification-requests", json=body, headers={"X-API-Key": SOLICITOR_KEY}
        )
        assert response.status_code == 422
        assert SYNTHETIC_NAME not in response.text
        assert "Alex" not in response.text
