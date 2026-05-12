"""Typed snapshot of a legacy intent_service decision for shadow-run comparison.

Spec: SPECS/SHADOW_RUN_V3.md (extends Phase B.1 with typed legacy projection).

This module is independent of legacy code: the projection from a real
`IntentResponse` to `LegacySummary` belongs to the future consultant_runtime
hook (Phase B.2). Here we only define the contract that Phase B.2 must
satisfy.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LegacySummary(BaseModel):
    """Stable, typed projection of one legacy intent_service decision.

    All fields are deliberately optional except `intent`, `action`, and
    `message_text`, which the legacy path always produces. Anything that
    does not fit cleanly belongs in `extras`.
    """

    model_config = ConfigDict(extra="forbid")

    intent: str
    action: str
    tool_action: str | None = None
    message_text: str = ""
    rescue_flag: bool = False
    policy_core_degrade: bool = False
    degrade_reason: str | None = None
    latency_ms: float | None = Field(default=None, ge=0.0)
    extras: dict[str, Any] = Field(default_factory=dict)
