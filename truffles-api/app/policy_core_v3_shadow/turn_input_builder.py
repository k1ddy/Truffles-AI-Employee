"""Pure builder: LegacyTurnContext → policy_core_v3.PolicyTurnInput.

Spec: SPECS/SHADOW_RUN_V3.md section 3.

This is the only bridge between legacy runtime data and v3 inputs. It must
stay pure: no DB, no LLM, no network. Production callers fill
`LegacyTurnContext` from whatever sources the legacy runtime already has.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.pack_v1 import PackV1, to_pack_view
from app.policy_core_v3 import (
    EvidenceItem,
    PolicyTurnInput,
    ToolContract,
    Turn,
)


@dataclass(frozen=True)
class LegacyTurnContext:
    """Minimum bridge from legacy turn data to v3 inputs.

    Frozen so the builder cannot accidentally mutate caller state.
    """

    tenant_id: str
    conversation_id: str
    current_message: str
    pack: PackV1
    now: datetime
    history: list[Turn] = field(default_factory=list)
    state_slots: dict[str, Any] = field(default_factory=dict)
    evidence_bundle: list[EvidenceItem] = field(default_factory=list)
    locale: str | None = None
    policy_version: str = "v3-shadow"
    history_max_turns: int = 12


def to_policy_turn_input(ctx: LegacyTurnContext) -> PolicyTurnInput:
    """Build a `PolicyTurnInput` for v3 from the legacy context.

    Pure function. Same input → equal output.
    """
    pack_view = to_pack_view(ctx.pack)
    tools = [
        ToolContract(
            id=t.id,
            description=t.description,
            args_schema=dict(t.args_schema),
        )
        for t in ctx.pack.tools
    ]
    return PolicyTurnInput(
        tenant_id=ctx.tenant_id,
        conversation_id=ctx.conversation_id,
        current_message=ctx.current_message,
        conversation_history=list(ctx.history),
        state_slots=dict(ctx.state_slots),
        pack_view=pack_view,
        capabilities=list(ctx.pack.capabilities),
        tool_contracts=tools,
        evidence_bundle=list(ctx.evidence_bundle),
        now=ctx.now,
        locale=ctx.locale or ctx.pack.locale,
        policy_version=ctx.policy_version,
        history_max_turns=ctx.history_max_turns,
    )
