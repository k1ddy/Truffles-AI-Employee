from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SlaThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_response_minutes: int = Field(default=5, ge=1, le=1440)
    handoff_ack_minutes: int = Field(default=15, ge=1, le=1440)
    resolution_minutes: int = Field(default=120, ge=1, le=10080)
    fallback_rate_max: float = Field(default=0.20, ge=0.0, le=1.0)


class SlaViolationActions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    warning: str = Field(default="notify_manager", pattern=r"^(none|notify_manager|escalate)$")
    breach: str = Field(default="escalate", pattern=r"^(none|notify_manager|escalate|collect_only)$")
    severe_breach: str = Field(default="collect_only", pattern=r"^(none|notify_manager|escalate|collect_only)$")


class SlaProfilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_name: str = Field(default="default", min_length=1, max_length=120)
    thresholds: SlaThresholds = Field(default_factory=SlaThresholds)
    actions: SlaViolationActions = Field(default_factory=SlaViolationActions)
