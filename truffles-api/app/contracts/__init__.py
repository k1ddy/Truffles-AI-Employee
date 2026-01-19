"""
Truffles Contracts Package

Контракты для единообразной обработки ошибок и результатов между модулями.
"""

from app.contracts.decision import (
    DECISION_GRAPH_STAGES,
    DecisionOutcome,
    DecisionPlan,
    DecisionSignals,
    DecisionStage,
    ExpectedReplyState,
    IntentDecompositionState,
    IntentRoutingState,
    build_action_contract,
    build_context_contract,
    build_decision_plan,
    build_fact_contract,
    build_intent_contract,
    build_response_contract,
)
from app.contracts.errors import (
    AuthError,
    ConfigError,
    ErrorCodes,
    IntegrationError,
    RateLimitError,
    StateError,
    TrufflesError,
    ValidationError,
)
from app.contracts.result import Err, Ok, Result

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

