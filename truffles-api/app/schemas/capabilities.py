import re
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

CAPABILITIES_SCHEMA_VERSION = "v1"


class CapabilityChannels(BaseModel):
    model_config = ConfigDict(extra="forbid")

    whatsapp: Optional[bool] = None
    telegram: Optional[bool] = None
    instagram: Optional[bool] = None


class CapabilityProviders(BaseModel):
    model_config = ConfigDict(extra="forbid")

    availability_provider: Optional[
        Literal["none", "google_calendar", "bitrix", "amocrm", "manual"]
    ] = None
    crm_provider: Optional[Literal["none", "amocrm", "bitrix", "custom"]] = None
    calendar_provider: Optional[Literal["none", "google_calendar", "local"]] = None


class CapabilityFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    booking_mode: Optional[Literal["collect_preferences", "confirm_slots"]] = None
    knowledge_upload: Optional[bool] = None
    analytics: Optional[bool] = None
    auto_learn: Optional[bool] = None


class CapabilitiesPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain_slug: Optional[str] = None
    channels: CapabilityChannels = Field(default_factory=CapabilityChannels)
    providers: CapabilityProviders = Field(default_factory=CapabilityProviders)
    features: CapabilityFeatures = Field(default_factory=CapabilityFeatures)

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
