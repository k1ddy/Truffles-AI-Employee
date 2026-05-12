"""Pure divergence analysis between legacy decision and v3 outcome.

Spec: SPECS/SHADOW_RUN_V3.md (B.1.5 extension; consumed by B.3 corpus runs).

This module is a deterministic, scenario-free classifier. It does not invent
business meaning; it tags structural differences that a human reviewer or a
later metrics pass can aggregate.
"""
from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from app.policy_core_v3.schema import (
    DegradeVerdict,
    PolicyDecisionV3,
)

from .legacy_summary import LegacySummary


# Divergence flag vocabulary. Closed set on purpose — adding a flag is an
# explicit decision, not a per-corpus tweak.
INTENT_MATCH = "intent_match"
INTENT_MISMATCH = "intent_mismatch"
LEGACY_RESCUE = "legacy_rescue"
LEGACY_DEGRADE = "legacy_degrade"
V3_DEGRADE = "v3_degrade"
BOTH_DEGRADE = "both_degrade"
V3_DECISION_WHILE_LEGACY_DEGRADE = "v3_decision_while_legacy_degrade"
LEGACY_DECISION_WHILE_V3_DEGRADE = "legacy_decision_while_v3_degrade"
TOOL_ACTION_MATCH = "tool_action_match"
TOOL_ACTION_MISMATCH = "tool_action_mismatch"
HIGH_UNCERTAINTY = "high_uncertainty"


class Divergence(BaseModel):
    """Structural diff between legacy decision and v3 outcome.

    Pure derivation — no I/O, no LLM, no scenario-specific logic.
    """

    model_config = ConfigDict(extra="forbid")

    intent_match: bool
    legacy_intent: str
    v3_intent: str | None
    v3_degraded: bool
    legacy_rescue: bool
    legacy_degrade: bool
    legacy_tool_action: str | None
    v3_tool: str | None
    flags: list[str] = Field(default_factory=list)
    notes: str = ""


def compute_divergence(
    legacy: LegacySummary,
    v3_outcome: PolicyDecisionV3 | DegradeVerdict,
) -> Divergence:
    """Tag structural differences. No business interpretation."""
    v3_degraded = isinstance(v3_outcome, DegradeVerdict)

    if v3_degraded:
        v3_intent: str | None = None
        v3_tool: str | None = None
        v3_uncertainty: str | None = None
    else:
        v3_intent = v3_outcome.intent.value
        v3_tool = v3_outcome.candidate_action.tool
        v3_uncertainty = v3_outcome.uncertainty.value

    intent_match = (not v3_degraded) and (legacy.intent == v3_intent)

    flags: list[str] = []
    if intent_match:
        flags.append(INTENT_MATCH)
    elif not v3_degraded:
        flags.append(INTENT_MISMATCH)

    if legacy.rescue_flag:
        flags.append(LEGACY_RESCUE)
    if legacy.policy_core_degrade:
        flags.append(LEGACY_DEGRADE)
    if v3_degraded:
        flags.append(V3_DEGRADE)
    if legacy.policy_core_degrade and v3_degraded:
        flags.append(BOTH_DEGRADE)
    if (not v3_degraded) and legacy.policy_core_degrade:
        flags.append(V3_DECISION_WHILE_LEGACY_DEGRADE)
    if (not legacy.policy_core_degrade) and v3_degraded:
        flags.append(LEGACY_DECISION_WHILE_V3_DEGRADE)

    if legacy.tool_action is not None and v3_tool is not None:
        if legacy.tool_action == v3_tool:
            flags.append(TOOL_ACTION_MATCH)
        else:
            flags.append(TOOL_ACTION_MISMATCH)

    if v3_uncertainty == "high":
        flags.append(HIGH_UNCERTAINTY)

    return Divergence(
        intent_match=intent_match,
        legacy_intent=legacy.intent,
        v3_intent=v3_intent,
        v3_degraded=v3_degraded,
        legacy_rescue=legacy.rescue_flag,
        legacy_degrade=legacy.policy_core_degrade,
        legacy_tool_action=legacy.tool_action,
        v3_tool=v3_tool,
        flags=_dedup_preserve_order(flags),
    )


def _dedup_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
