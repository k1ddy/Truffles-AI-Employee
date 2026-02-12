"""Neutral pack runtime facade.

Runtime callers depend on this module instead of concrete pack implementation.
"""

from __future__ import annotations

from app.services.pack_runtime_default import (
    _build_fact_meta,
    _has_contact_signal,
    _detect_promotion_intent,
    _format_service_not_found_reply,
    _has_duration_signal,
    _has_guest_waiting_signal,
    _has_parking_signal,
    _has_price_signal,
    _match_service,
    _matches_service_request_lexicon,
    _normalize_text,
    build_evening_greeting,
    build_info_combined_reply,
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
    phrase_match_intent,
    semantic_question_type,
    semantic_service_match,
)
from app.services.pack_runtime_types import PackDecision

# Backward compatibility alias for existing imports.
DemoSalonDecision = PackDecision

__all__ = [
    "PackDecision",
    "DemoSalonDecision",
    "_build_fact_meta",
    "_has_contact_signal",
    "_detect_promotion_intent",
    "_format_service_not_found_reply",
    "_has_guest_waiting_signal",
    "_has_duration_signal",
    "_has_parking_signal",
    "_has_price_signal",
    "_match_service",
    "_matches_service_request_lexicon",
    "_normalize_text",
    "build_evening_greeting",
    "build_info_combined_reply",
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
    "phrase_match_intent",
    "semantic_question_type",
    "semantic_service_match",
]
