"""Policy-Core v3 — single semantic owner for inbound customer turns.

Status: PoC, not wired into runtime.
Spec: SPECS/POLICY_CORE_V3.md

This package replaces the scenario-driven legacy `intent_service.py` with a
typed, pure, vertical-agnostic LLM invoker. It performs no I/O beyond calling
the LLM provider passed to it.
"""

from .pack_view import (
    PackRules,
    PackView,
    ServiceView,
    SpecialistView,
    EvidenceItem,
    ToolContract,
    Turn,
)
from .schema import (
    DegradeReason,
    DegradeVerdict,
    Intent,
    PolicyDecisionV3,
    PolicyTurnInput,
    Uncertainty,
)
from .prompt_builder import build_prompt
from .retry_policy import RetryDecision, classify_failure, next_retry_action
from .invoker import LLMCallable, PolicyCoreV3Invoker

__all__ = [
    "DegradeReason",
    "DegradeVerdict",
    "EvidenceItem",
    "Intent",
    "LLMCallable",
    "PackRules",
    "PackView",
    "PolicyCoreV3Invoker",
    "PolicyDecisionV3",
    "PolicyTurnInput",
    "RetryDecision",
    "ServiceView",
    "SpecialistView",
    "ToolContract",
    "Turn",
    "Uncertainty",
    "build_prompt",
    "classify_failure",
    "next_retry_action",
]
