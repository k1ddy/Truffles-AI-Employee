"""Compatibility-only demo salon semantic helpers."""

from __future__ import annotations

from app.services.demo_salon_knowledge import (
    DemoSalonDecision,
    SemanticQuestionType,
    SemanticServiceMatch,
)
from app.services.demo_salon_knowledge import (
    _build_demo_price_reply as get_demo_salon_price_reply,
)
from app.services.demo_salon_knowledge import (
    _build_demo_service_decision as get_demo_salon_service_decision,
)
from app.services.demo_salon_knowledge import (
    _build_demo_truth_decision as get_demo_salon_decision,
)
from app.services.demo_salon_knowledge import (
    _pack_query_phrase_intents as phrase_match_intent,
)
from app.services.demo_salon_knowledge import (
    _pack_query_question_classifier as semantic_question_type,
)
from app.services.demo_salon_knowledge import (
    _resolve_demo_price_item as get_demo_salon_price_item,
)
from app.services.demo_salon_knowledge import (
    _resolve_demo_service_hint as get_demo_salon_service_hint,
)
from app.services.demo_salon_knowledge import (
    _resolve_pack_query_semantic_match as semantic_service_match,
)

__all__ = [
    "DemoSalonDecision",
    "SemanticQuestionType",
    "SemanticServiceMatch",
    "get_demo_salon_decision",
    "get_demo_salon_price_item",
    "get_demo_salon_price_reply",
    "get_demo_salon_service_decision",
    "get_demo_salon_service_hint",
    "phrase_match_intent",
    "semantic_question_type",
    "semantic_service_match",
]
