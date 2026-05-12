"""Oracle/drift mock LLM for corpus replay.

Spec: SPECS/SHADOW_RUN_V3.md (Phase B.3).

Modes:
- `oracle`: return the corpus turn's `oracle_v3` verbatim. Proves the pipeline
  end-to-end and, when oracle is owner-approved, anchors the histogram at
  ~100% intent_match.
- `drift`: deterministically corrupt a fraction of oracle outputs (wrong
  intent / empty / unknown tool) to exercise the aggregator and to surface
  divergence flag distributions for analysis.
- `degrade`: always return an empty string, forcing v3 into degrade for
  smoke testing.

The mode is set at corpus runner construction time. The LLM callable is then
indexed by the *current message* of the active turn — the runner sets the
active turn before invoking shadow.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum

from app.policy_core_v3 import LLMCallable
from app.policy_core_v3.schema import (
    CandidateAction,
    Intent,
    PolicyDecisionV3,
    Uncertainty,
)


class OracleLLMMode(str, Enum):
    oracle = "oracle"
    drift = "drift"
    degrade = "degrade"


@dataclass
class OracleLLMConfig:
    mode: OracleLLMMode = OracleLLMMode.oracle
    drift_rate: float = 0.2  # only used in drift mode
    drift_seed: str = "policy_core_v3_corpus"


class _OracleRegistry:
    """Holds the active turn's oracle. Set by the runner before invoke."""

    def __init__(self) -> None:
        self.active: PolicyDecisionV3 | None = None
        self.active_turn_token: str | None = None  # used as drift hash key

    def set_active(self, oracle: PolicyDecisionV3 | None, token: str) -> None:
        self.active = oracle
        self.active_turn_token = token

    def clear(self) -> None:
        self.active = None
        self.active_turn_token = None


def build_oracle_llm(
    registry: _OracleRegistry,
    config: OracleLLMConfig | None = None,
) -> LLMCallable:
    """Build an `LLMCallable` driven by an `_OracleRegistry`.

    The runner installs the next turn's oracle into the registry, calls
    `invoker.invoke(...)`, then clears.
    """
    cfg = config or OracleLLMConfig()

    async def _llm(prompt: str) -> str:
        if cfg.mode is OracleLLMMode.degrade:
            return ""
        oracle = registry.active
        if oracle is None:
            # No oracle for this turn → degrade by definition.
            return ""
        if cfg.mode is OracleLLMMode.oracle:
            return _serialize(oracle)
        # drift mode
        if _should_drift(registry.active_turn_token or "", cfg):
            return _serialize(_drifted(oracle))
        return _serialize(oracle)

    return _llm


def _serialize(decision: PolicyDecisionV3) -> str:
    return json.dumps(decision.model_dump(mode="json"), ensure_ascii=False)


def _should_drift(token: str, cfg: OracleLLMConfig) -> bool:
    if cfg.drift_rate <= 0.0:
        return False
    if cfg.drift_rate >= 1.0:
        return True
    h = hashlib.sha256((cfg.drift_seed + ":" + token).encode("utf-8")).digest()
    bucket = h[0] / 255.0
    return bucket < cfg.drift_rate


def _drifted(oracle: PolicyDecisionV3) -> PolicyDecisionV3:
    """Deterministic small corruption: rotate intent to a sibling.

    Preserves schema validity; just flips the semantic content so divergence
    flags `intent_mismatch` show up in aggregator output.
    """
    siblings = {
        Intent.fact_question: Intent.smalltalk,
        Intent.smalltalk: Intent.fact_question,
        Intent.booking_request: Intent.slot_collect,
        Intent.slot_collect: Intent.booking_request,
        Intent.booking_manage: Intent.handoff_request,
        Intent.handoff_request: Intent.booking_manage,
        Intent.unsupported: Intent.unknown,
        Intent.unknown: Intent.unsupported,
    }
    new_intent = siblings.get(oracle.intent, Intent.unknown)
    return oracle.model_copy(
        update={
            "intent": new_intent,
            "uncertainty": Uncertainty.high,
            "candidate_action": oracle.candidate_action or CandidateAction(tool="none"),
            "notes": (oracle.notes + " | drifted").strip(" |"),
        }
    )


# Public alias of the registry type for runner code.
OracleRegistry = _OracleRegistry
