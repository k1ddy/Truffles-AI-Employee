"""Neutral pack runtime facade.

Current adapter delegates to `demo_salon_knowledge` while runtime callers
gradually migrate away from demo-specific service naming.
"""

from __future__ import annotations

from app.services.demo_salon_knowledge import (
    DemoSalonDecision,
    _detect_promotion_intent,
    _has_duration_signal,
    _has_price_signal,
    _match_service,
    _matches_service_request_lexicon,
    _normalize_text,
    build_evening_greeting,
    build_quiet_hours_notice,
    compose_multi_truth_reply,
    format_reply_from_truth,
    get_pack_decision,
    get_pack_price_item,
    get_pack_price_reply,
    get_pack_service_decision,
    get_pack_service_hint,
    get_signal_lexicon_list,
    get_system_anchor_groups,
    get_system_lexicon_list,
    load_policy_pack,
    load_system_lexicons,
    load_yaml_truth,
    semantic_question_type,
    semantic_service_match,
)

__all__ = [
    "DemoSalonDecision",
    "_detect_promotion_intent",
    "_has_duration_signal",
    "_has_price_signal",
    "_match_service",
    "_matches_service_request_lexicon",
    "_normalize_text",
    "build_evening_greeting",
    "build_quiet_hours_notice",
    "compose_multi_truth_reply",
    "format_reply_from_truth",
    "get_pack_decision",
    "get_pack_price_item",
    "get_pack_price_reply",
    "get_pack_service_decision",
    "get_pack_service_hint",
    "get_signal_lexicon_list",
    "get_system_anchor_groups",
    "get_system_lexicon_list",
    "load_policy_pack",
    "load_system_lexicons",
    "load_yaml_truth",
    "semantic_question_type",
    "semantic_service_match",
]
