import re
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.capabilities import CapabilitiesPayload

ONBOARDING_CONTRACT_SCHEMA_VERSION = "v1"

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class OnboardingProviderBindingWhatsApp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Optional[str] = None
    instance_id: Optional[str] = None
    webhook_status: Optional[Literal["configured", "pending", "rebind_required"]] = None
    paid_until: Optional[str] = None
    owner: Optional[str] = None
    next_renewal_at: Optional[str] = None
    last_rebind_at: Optional[str] = None
    rebind_required: Optional[bool] = None
    alert_state: Optional[Literal["ok", "warn", "critical"]] = None
    notes: Optional[str] = None

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        if not re.match(r"^[a-z0-9_-]+$", cleaned):
            raise ValueError("provider must be lowercase alphanum/underscore/hyphen")
        return cleaned

    @field_validator("instance_id")
    @classmethod
    def validate_instance_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        return cleaned

    @field_validator("paid_until")
    @classmethod
    def validate_paid_until(cls, value: Optional[str]) -> Optional[str]:
        return cls._validate_iso_date_field("paid_until", value)

    @field_validator("next_renewal_at")
    @classmethod
    def validate_next_renewal_at(cls, value: Optional[str]) -> Optional[str]:
        return cls._validate_iso_date_field("next_renewal_at", value)

    @field_validator("last_rebind_at")
    @classmethod
    def validate_last_rebind_at(cls, value: Optional[str]) -> Optional[str]:
        return cls._validate_iso_date_field("last_rebind_at", value)

    @classmethod
    def _validate_iso_date_field(cls, field_name: str, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if not _DATE_RE.match(cleaned):
            raise ValueError(f"{field_name} must be YYYY-MM-DD")
        try:
            date.fromisoformat(cleaned)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a valid calendar date") from exc
        return cleaned

    @field_validator("owner")
    @classmethod
    def validate_owner(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        return cleaned

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        return cleaned


class OnboardingProviderBindingPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    whatsapp: Optional[OnboardingProviderBindingWhatsApp] = None


class OnboardingContractPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain_slug: Optional[str] = None
    purchased: CapabilitiesPayload = Field(default_factory=CapabilitiesPayload)
    provider_binding: OnboardingProviderBindingPayload = Field(default_factory=OnboardingProviderBindingPayload)

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
