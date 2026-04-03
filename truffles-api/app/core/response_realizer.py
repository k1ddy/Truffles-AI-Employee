from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.boundary_validator import BoundaryOverride
from app.core.turn_planner import PolicyDecision

ReplyKind = Literal["fact", "collect", "handoff", "system"]


class ReplyEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: str
    reply_kind: ReplyKind
    text: str
    meta: dict[str, Any] = Field(default_factory=dict)


class ResponseRealizer:
    """Maps typed turn outcome into a transport-ready reply envelope."""

    def realize(
        self,
        decision: PolicyDecision | None,
        *,
        override: BoundaryOverride | None = None,
        text: str = "",
        channel: str = "whatsapp",
        reply_kind_override: ReplyKind | None = None,
    ) -> ReplyEnvelope:
        if reply_kind_override is not None:
            reply_kind = reply_kind_override
            body = text
        elif override and override.decision == "block":
            reply_kind: ReplyKind = "system"
            body = override.public_message or text
        elif override and override.decision == "degrade":
            reply_kind = "handoff"
            body = override.public_message or text
        elif decision is None:
            raise ValueError("policy_decision_required_without_boundary_override")
        elif decision.outcome == "FACT":
            reply_kind = "fact"
            body = text
        elif decision.outcome == "COLLECT":
            reply_kind = "collect"
            body = text
        else:
            reply_kind = "handoff"
            body = text
        meta: dict[str, Any] = {}
        if override is not None:
            meta["boundary_decision"] = override.decision
        return ReplyEnvelope(channel=channel, reply_kind=reply_kind, text=body, meta=meta)


__all__ = ["ReplyEnvelope", "ReplyKind", "ResponseRealizer"]
