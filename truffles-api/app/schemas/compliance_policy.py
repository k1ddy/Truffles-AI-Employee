from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CompliancePolicyPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_name: str = Field(default="default", min_length=1, max_length=120)
    legal_basis: Literal[
        "consent",
        "contract",
        "legal_obligation",
        "legitimate_interest",
        "vital_interest",
        "other",
    ] = "legal_obligation"
    retention_days: int = Field(default=365, ge=1, le=36500)
    export_mode: Literal["on_demand", "scheduled", "disabled"] = "on_demand"
    destruction_mode: Literal["delete", "anonymize", "archive"] = "delete"
    kz_storage_required: bool = True
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None
