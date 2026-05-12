"""Typed PackV1 manifest.

Spec: SPECS/PACK_V1.md section 4.

Strict pydantic models — extra fields are rejected so that pack files cannot
silently grow undocumented sections.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


PackCapability = Literal["FACT", "COLLECT", "BOOKING", "MANAGE", "HANDOFF"]


class PackContacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone: str | None = None
    instagram: str | None = None
    website: str | None = None


class PackBranch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    address: str | None = None


class PackBusiness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    summary: str
    address: str | None = None
    hours: str | None = None
    contacts: PackContacts | None = None
    branches: list[PackBranch] = Field(default_factory=list)


class PackRulesV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bot_can_confirm: bool
    required_for_booking: list[str]
    identity_for_lookup: list[str]
    escalate_topics: list[str]
    cancellation_policy: str | None = None
    reschedule_policy: str | None = None


class PackService(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    duration_min: int | None = None
    price_display: str | None = None
    description: str | None = None
    category: str | None = None
    escalate: bool = False


class PackSpecialist(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    service_ids: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    bio: str | None = None


class PackToolContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    description: str
    args_schema: dict[str, str] = Field(default_factory=dict)
    requires_capability: PackCapability | None = None


class PackV1(BaseModel):
    """Typed tenant pack.

    All vertical/tenant differences live here as data. Verticals scale by
    adding pack files, not Python code.
    """

    model_config = ConfigDict(extra="forbid")

    pack_id: str
    pack_version: int = Field(..., ge=1)
    vertical: str
    locale: str
    business: PackBusiness
    rules: PackRulesV1
    capabilities: list[PackCapability]
    services: list[PackService]
    specialists: list[PackSpecialist] = Field(default_factory=list)
    tools: list[PackToolContract]
    knowledge_sources: list[str] = Field(default_factory=list)
    aliases: dict[str, dict[str, list[str]]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_internal_consistency(self) -> "PackV1":
        if not self.pack_id:
            raise ValueError("pack_id must be non-empty")
        if not self.services:
            raise ValueError("services must be non-empty for v1 acceptance")

        service_ids = [s.id for s in self.services]
        if len(service_ids) != len(set(service_ids)):
            raise ValueError("services[].id must be unique")
        service_id_set = set(service_ids)

        specialist_ids = [s.id for s in self.specialists]
        if len(specialist_ids) != len(set(specialist_ids)):
            raise ValueError("specialists[].id must be unique")
        for sp in self.specialists:
            unknown = set(sp.service_ids) - service_id_set
            if unknown:
                raise ValueError(
                    f"specialist {sp.id!r} references unknown service ids: "
                    f"{sorted(unknown)}"
                )

        capability_set = set(self.capabilities)
        if len(capability_set) != len(self.capabilities):
            raise ValueError("capabilities must be unique")

        for tool in self.tools:
            if tool.requires_capability is not None and tool.requires_capability not in capability_set:
                raise ValueError(
                    f"tool {tool.id!r} requires_capability "
                    f"{tool.requires_capability!r} not in pack.capabilities"
                )

        tool_ids = [t.id for t in self.tools]
        if len(tool_ids) != len(set(tool_ids)):
            raise ValueError("tools[].id must be unique")

        return self
