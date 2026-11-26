"""Tests for GET /health (spec GH-5, AC1 and AC2) and the route list (spec GH-8, AC8)."""

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

DOCS_PATHS = {"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}


def test_routes_are_exactly() -> None:
    other_routes = [
        route for route in app.routes if getattr(route, "path", None) not in DOCS_PATHS
    ]
    exposed = {
        (method, route.path)
        for route in other_routes
        if isinstance(route, APIRoute)
        for method in route.methods or set()
    }

    assert all(isinstance(route, APIRoute) for route in other_routes)
    assert exposed == {("GET", "/health"), ("POST", "/verification-requests")}


def test_health_rejects_post() -> None:
    assert client.post("/health").status_code == 405


def test_unknown_path_is_404() -> None:
    assert client.get("/no-such-path").status_code == 404
