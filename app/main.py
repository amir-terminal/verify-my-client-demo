"""Verify My Client web app."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api import verification_requests
from app.models.database import init_schema
from app.privacy.validation_errors import validation_error_handler

# Relative to the working folder; `var/` is git-ignored. Synthetic data only.
DEFAULT_DATABASE_PATH = Path("var/verify-my-client.sqlite3")


def create_app(database_path: Path) -> FastAPI:
    """Build the app on the given SQLite file (tests pass a temporary one)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        init_schema(database_path)
        yield

    app = FastAPI(title="Verify My Client", lifespan=lifespan)
    app.state.database_path = database_path
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Report that the app is up, with no version, build or environment details."""
        return {"status": "ok"}

    verification_requests.add_routes(app)
    return app


app = create_app(DEFAULT_DATABASE_PATH)
