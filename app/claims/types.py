"""The fixed set of claims a business can request (spec GH-8)."""

from enum import StrEnum


class ClaimType(StrEnum):
    """A detail a business can ask its client to share."""

    NAME = "name"
    OVER_18 = "over_18"
    CONFIRMED_ADDRESS = "confirmed_address"


# Claims the business must give an expected value for; the others must not have one.
CLAIMS_WITH_EXPECTED_VALUE = frozenset({ClaimType.NAME, ClaimType.CONFIRMED_ADDRESS})

# The order claims are always returned in, whatever order they were requested in.
CLAIM_ORDER: tuple[ClaimType, ...] = (
    ClaimType.NAME,
    ClaimType.OVER_18,
    ClaimType.CONFIRMED_ADDRESS,
)
