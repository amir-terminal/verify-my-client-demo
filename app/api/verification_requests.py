"""POST /verification-requests: a business asks for the claims it needs (specs GH-8, GH-14)."""

import sqlite3
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response, status

from app.auth.businesses import DemoBusiness, require_business
from app.links import tokens
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
    now: Annotated[datetime, Depends(tokens.utc_now)],
    request: Request,
    response: Response,
) -> VerificationRequestCreated:
    """Create a request for exactly the claims given, with its single client link.

    The response holds no expected values. Its raw token is stored only as a hash,
    and the response is marked not to be cached.
    """
    response.headers["Cache-Control"] = "no-store"
    claims = body.ordered_claims()
    expires_at = now + tokens.LINK_LIFETIME
    token = tokens.new_link_token()
    request_id = insert_verification_request(
        conn,
        business,
        claims,
        created_at=now,
        token_hash=tokens.hash_token(token),
        expires_at=expires_at,
    )
    return VerificationRequestCreated(
        id=request_id,
        claims=[claim.type for claim in claims],
        created_at=now.isoformat(),
        client_link=f"{request.base_url}client/{token}",
        expires_at=expires_at.isoformat(),
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
