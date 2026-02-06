import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.capabilities import CapabilitiesPayload

ONBOARDING_CONTRACT_SCHEMA_VERSION = "v1"


class OnboardingContractPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain_slug: Optional[str] = None
    purchased: CapabilitiesPayload = Field(default_factory=CapabilitiesPayload)

    @field_validator("domain_slug")
    @classmethod
    def validate_domain_slug(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if not re.match(r"^[a-z0-9_-]+$", cleaned):
            raise ValueError("domain_slug must be lowercase alphanum/underscore/hyphen")
        return cleaned
