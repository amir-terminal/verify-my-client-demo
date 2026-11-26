"""Request and response models for creating a verification request (spec GH-8).

Every model forbids extra fields. Validation messages never include the
submitted values, so a refusal can't repeat a client's details.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.claims.types import CLAIM_ORDER, CLAIMS_WITH_EXPECTED_VALUE, ClaimType

EXPECTED_MAX_LENGTH = 200


class RequestedClaim(BaseModel):
    """One claim the business asks for, with the expected value where it needs one."""

    model_config = ConfigDict(extra="forbid")

    type: ClaimType
    expected: str | None = None

    @field_validator("expected")
    @classmethod
    def _trim_expected(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("expected must not be empty")
        if len(trimmed) > EXPECTED_MAX_LENGTH:
            raise ValueError(
                f"expected must be at most {EXPECTED_MAX_LENGTH} characters"
            )
        return trimmed

    @model_validator(mode="after")
    def _expected_matches_claim_type(self) -> Self:
        if self.type in CLAIMS_WITH_EXPECTED_VALUE:
            if self.expected is None:
                raise ValueError(f"{self.type.value} needs an expected value")
        elif "expected" in self.model_fields_set:
            raise ValueError(f"{self.type.value} takes no expected value")
        return self


class CreateVerificationRequest(BaseModel):
    """Body of POST /verification-requests."""

    model_config = ConfigDict(extra="forbid")

    claims: list[RequestedClaim] = Field(min_length=1, max_length=len(CLAIM_ORDER))

    @model_validator(mode="after")
    def _no_duplicate_claims(self) -> Self:
        types = [claim.type for claim in self.claims]
        if len(set(types)) != len(types):
            raise ValueError("each claim type may be requested only once")
        return self

    def ordered_claims(self) -> list[RequestedClaim]:
        """The claims in the fixed order name, over_18, confirmed_address."""
        return sorted(self.claims, key=lambda claim: CLAIM_ORDER.index(claim.type))


class VerificationRequestCreated(BaseModel):
    """Response of POST /verification-requests: no expected values, no business.

    `client_link` carries the raw token: this response is the only place it appears.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    claims: list[ClaimType]
    created_at: str
    client_link: str
    expires_at: str
