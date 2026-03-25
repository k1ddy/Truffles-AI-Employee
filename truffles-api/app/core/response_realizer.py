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
        decision: PolicyDecision,
        *,
        override: BoundaryOverride | None = None,
        text: str = "",
        channel: str = "whatsapp",
    ) -> ReplyEnvelope:
        if override and override.decision == "block":
            reply_kind: ReplyKind = "system"
            body = override.public_message or text
        elif decision.outcome == "FACT":
            reply_kind = "fact"
            body = text
        elif decision.outcome == "COLLECT":
            reply_kind = "collect"
            body = text
        else:
            reply_kind = "handoff"
            body = text
        return ReplyEnvelope(channel=channel, reply_kind=reply_kind, text=body, meta={"outcome": decision.outcome})


__all__ = ["ReplyEnvelope", "ReplyKind", "ResponseRealizer"]
