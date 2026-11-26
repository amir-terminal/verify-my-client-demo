"""Shared fixtures. Every test database is a temporary file, never the demo file."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.sqlite3"


@pytest.fixture
def client(db_path: Path) -> Iterator[TestClient]:
    # `with` runs the lifespan, which creates the schema in the temporary file.
    with TestClient(create_app(db_path)) as test_client:
        yield test_client
