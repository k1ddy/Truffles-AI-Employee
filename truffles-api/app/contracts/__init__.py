"""
Truffles Contracts Package

Контракты для единообразной обработки ошибок и результатов между модулями.
"""

from app.contracts.errors import (
    TrufflesError,
    ValidationError,
    IntegrationError,
    StateError,
    AuthError,
    ConfigError,
    RateLimitError,
    ErrorCodes,
)
from app.contracts.result import Result, Ok, Err
from app.contracts.decision import (
    DecisionStage,
    DECISION_GRAPH_STAGES,
    DecisionPlan,
    DecisionSignals,
    DecisionOutcome,
    ExpectedReplyState,
    IntentDecompositionState,
    IntentRoutingState,
    build_decision_plan,
    build_context_contract,
    build_intent_contract,
    build_fact_contract,
    build_action_contract,
    build_response_contract,
)

__all__ = [
    # Errors
    "TrufflesError",
    "ValidationError",
    "IntegrationError",
    "StateError",
    "AuthError",
    "ConfigError",
    "RateLimitError",
    "ErrorCodes",
    # Result
    "Result",
    "Ok",
    "Err",
    # Decision
    "DecisionStage",
    "DECISION_GRAPH_STAGES",
    "DecisionPlan",
    "DecisionSignals",
    "DecisionOutcome",
    "ExpectedReplyState",
    "IntentDecompositionState",
    "IntentRoutingState",
    "build_decision_plan",
    "build_context_contract",
    "build_intent_contract",
    "build_fact_contract",
    "build_action_contract",
    "build_response_contract",
]

