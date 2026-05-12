"""Minimum read-only pack interface for Policy-Core v3.

This is intentionally a *subset* of the future PackV1 contract — only what
the v3 prompt builder needs. PackV1 will subsume this Protocol in a later
session. Consumers of v3 must not depend on anything beyond `PackView`.

Spec: SPECS/POLICY_CORE_V3.md section 4.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ServiceView:
    id: str
    name: str
    aliases: tuple[str, ...] = ()
    duration_min: int | None = None
    price: str | None = None  # display string; numeric typing belongs in PackV1


@dataclass(frozen=True)
class SpecialistView:
    id: str
    name: str
    service_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class PackRules:
    bot_can_confirm: bool
    required_for_booking: tuple[str, ...]
    identity_for_lookup: tuple[str, ...]
    escalate_topics: tuple[str, ...]


@runtime_checkable
class PackView(Protocol):
    """Read-only subset of a tenant pack used by Policy-Core v3."""

    pack_id: str
    services: list[ServiceView]
    specialists: list[SpecialistView]
    rules: PackRules
    business_summary: str


@dataclass(frozen=True)
class Turn:
    role: str  # "customer" | "bot"
    text: str


@dataclass(frozen=True)
class EvidenceItem:
    """Deterministic candidate fact produced by upstream evidence layers
    (RAG, lexicon, datetime parsers, phone normalizers).

    The model may cite these via `evidence_refs` in PolicyDecisionV3.
    """

    id: str
    source: str  # e.g. "rag", "lexicon", "datetime_parser", "phone_normalizer"
    kind: str   # e.g. "service_alias", "datetime_candidate", "phone_candidate", "knowledge_chunk"
    payload: dict
    confidence: float = 1.0


@dataclass(frozen=True)
class ToolContract:
    """Declarative tool description visible to the model.

    The args schema is a JSON-schema-ish dict; v3 does not validate args
    deeply (planner does). It only checks that the chosen `tool` id is in
    the allowed set.
    """

    id: str
    description: str
    args_schema: dict = field(default_factory=dict)


@dataclass(frozen=True)
class StaticPackView:
    """In-memory PackView implementation for tests and PoC."""

    pack_id: str
    services: list[ServiceView]
    specialists: list[SpecialistView]
    rules: PackRules
    business_summary: str
