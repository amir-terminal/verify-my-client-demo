"""POST /verification-requests: a business asks for the claims it needs (spec GH-8)."""

import sqlite3
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, status

from app.auth.businesses import DemoBusiness, require_business
from app.models.database import get_connection
from app.models.repository import insert_verification_request
from app.models.verification_request import (
    CreateVerificationRequest,
    VerificationRequestCreated,
)


def create_verification_request(
    body: CreateVerificationRequest,
    business: Annotated[DemoBusiness, Depends(require_business)],
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> VerificationRequestCreated:
    """Create a request for exactly the claims given. The response holds no expected values."""
    claims = body.ordered_claims()
    created_at = datetime.now(UTC)
    request_id = insert_verification_request(conn, business, claims, created_at)
    return VerificationRequestCreated(
        id=request_id,
        claims=[claim.type for claim in claims],
        created_at=created_at.isoformat(),
    )


def add_routes(app: FastAPI) -> None:
    """Register the routes directly on the app.

    Not `include_router`: FastAPI 0.165 keeps an included router as one nested
    route object, which hides its routes from `app.routes` and the route-list test.
    """
    app.add_api_route(
        "/verification-requests",
        create_verification_request,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=VerificationRequestCreated,
    )
