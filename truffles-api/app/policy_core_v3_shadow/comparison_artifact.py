"""Comparison artifact types for shadow-run.

Spec: SPECS/SHADOW_RUN_V3.md section 3.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from .divergence import Divergence
from .legacy_summary import LegacySummary


class ComparisonRecord(BaseModel):
    """Typed snapshot of one shadow-run turn.

    Both `legacy_summary` and the v3 outcome are typed. `divergence` is a
    pure derivation populated by the runner; consumers may also recompute
    it via `divergence.compute_divergence(...)`.
    """

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    conversation_id: str
    turn_index: int = Field(..., ge=0)
    current_message: str
    legacy_summary: LegacySummary
    v3_outcome_kind: str  # "decision" or "degrade"
    v3_decision: dict[str, Any] | None = None
    v3_degrade: dict[str, Any] | None = None
    v3_latency_ms: float = Field(..., ge=0.0)
    v3_attempts: int = Field(..., ge=0)
    divergence: Divergence | None = None
    policy_version: str
    pack_id: str
    pack_version: int
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""


@runtime_checkable
class ArtifactSink(Protocol):
    """Where comparison records go.

    The default in-memory sink is suitable for tests and dry-run. Production
    will inject a JSONL or Postgres-backed sink (out of scope for B.1).
    """

    async def emit(self, record: ComparisonRecord) -> None: ...


class InMemoryArtifactSink:
    """Default sink that just keeps records in a list."""

    def __init__(self) -> None:
        self.records: list[ComparisonRecord] = []

    async def emit(self, record: ComparisonRecord) -> None:
        self.records.append(record)
