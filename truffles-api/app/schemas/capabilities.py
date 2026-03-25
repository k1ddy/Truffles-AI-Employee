import re
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

CAPABILITIES_SCHEMA_VERSION = "v1"
_CAPABILITY_TOKEN_RE = re.compile(
    r"^(?:\*|[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*|\.\*))$"
)


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


class CapabilityTools(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow: Optional[list[str]] = None
    deny: Optional[list[str]] = None

    @field_validator("allow", "deny")
    @classmethod
    def validate_tool_tokens(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        if value is None:
            return None
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            token = str(item or "").strip().casefold()
            if not token:
                continue
            if not _CAPABILITY_TOKEN_RE.match(token):
                raise ValueError(
                    "tool policy token must be '*', '<group>.*' or '<group>.<action>'"
                )
            if token in seen:
                continue
            seen.add(token)
            normalized.append(token)
        return normalized or None


class CapabilityPolicySectionOverride(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response: Optional[str] = None

    @field_validator("response", mode="before")
    @classmethod
    def normalize_response(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class CapabilityPolicyOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Operational policy sections. hard_law is intentionally excluded.
    payment_info: Optional[CapabilityPolicySectionOverride] = None
    discounts: Optional[CapabilityPolicySectionOverride] = None


class CapabilitiesPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain_slug: Optional[str] = None
    channels: CapabilityChannels = Field(default_factory=CapabilityChannels)
    providers: CapabilityProviders = Field(default_factory=CapabilityProviders)
    features: CapabilityFeatures = Field(default_factory=CapabilityFeatures)
    tools: CapabilityTools = Field(default_factory=CapabilityTools)
    policy_overrides: CapabilityPolicyOverrides = Field(default_factory=CapabilityPolicyOverrides)
    allowed_fact_scopes: Optional[list[str]] = None
    handoff_policy: Optional[Literal["allow", "manager_request_only", "deny"]] = None

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

    @field_validator("allowed_fact_scopes")
    @classmethod
    def validate_allowed_fact_scopes(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        if value is None:
            return None
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            token = str(item or "").strip().casefold()
            if not token:
                continue
            if not _CAPABILITY_TOKEN_RE.match(token):
                raise ValueError(
                    "fact scope token must be '*', '<group>.*' or '<group>.<scope>'"
                )
            if token in seen:
                continue
            seen.add(token)
            normalized.append(token)
        return normalized or None

    @field_validator("handoff_policy", mode="before")
    @classmethod
    def normalize_handoff_policy(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return None
        token = str(value).strip().casefold()
        return token or None
