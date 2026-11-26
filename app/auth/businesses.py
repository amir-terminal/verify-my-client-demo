"""Synthetic demo businesses and their API-key check (spec GH-8, AC2).

The keys are obviously fake, readable names that hold no secret. They stand in
for real sign-in in this demo and must never be replaced by random-looking strings.
"""

import hmac
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader


@dataclass(frozen=True)
class DemoBusiness:
    """A synthetic business that can create verification requests."""

    id: str
    display_name: str
    api_key: str


DEMO_BUSINESSES: tuple[DemoBusiness, ...] = (
    DemoBusiness("demo-solicitor", "Demo Solicitors (synthetic)", "demo-key-solicitor"),
    DemoBusiness(
        "demo-estate-agent", "Demo Estate Agents (synthetic)", "demo-key-estate-agent"
    ),
    DemoBusiness(
        "demo-accountant", "Demo Accountants (synthetic)", "demo-key-accountant"
    ),
)

UNAUTHORISED_DETAIL = "Missing or unknown API key"

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def find_business(api_key: str | None) -> DemoBusiness | None:
    """Return the business whose key matches, comparing every key in constant time."""
    if not api_key:
        return None
    supplied = api_key.encode()
    match: DemoBusiness | None = None
    for business in DEMO_BUSINESSES:
        # Check every key (no early exit) so timing doesn't reveal which one matched.
        if hmac.compare_digest(supplied, business.api_key.encode()):
            match = business
    return match


def require_business(
    api_key: Annotated[str | None, Depends(api_key_header)],
) -> DemoBusiness:
    """FastAPI dependency: the calling business, or 401 with the same body every time."""
    business = find_business(api_key)
    if business is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=UNAUTHORISED_DETAIL
        )
    return business
