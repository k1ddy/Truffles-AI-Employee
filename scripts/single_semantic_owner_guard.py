from __future__ import annotations

import argparse
import ast
from collections import Counter
from pathlib import Path
import re
import subprocess
import sys


CANONICAL_FIELDS = (
    "action",
    "outcome",
    "expected_reply_type",
    "expected_reply_reason",
    "pending_question_target",
    "active_question_relation",
    "semantic_contract",
    "semantic_frame",
)

HARDCODE_CORE_PREFIXES = (
    "truffles-api/app/core/consultant_runtime.py",
    "truffles-api/app/core/turn_executor.py",
    "truffles-api/app/core/turn_planner.py",
    "truffles-api/app/routers/webhook/decision.py",
    "truffles-api/app/routers/webhook/booking.py",
    "truffles-api/app/routers/webhook/info.py",
    "truffles-api/app/services/tool_registry_service.py",
    "truffles-api/app/services/booking_signal_service.py",
    "truffles-api/app/services/info_signal_service.py",
)
HARDCODE_SCOPE_CORE_PREFIX = "truffles-api/app/core/"
HARDCODE_SCOPE_WEBHOOK_PREFIX = "truffles-api/app/routers/webhook/"
HARDCODE_SCOPE_SERVICE_PREFIX = "truffles-api/app/services/"
HARDCODE_SCOPE_SERVICE_FILES = (
    "truffles-api/app/services/tool_registry_service.py",
    "truffles-api/app/services/pack_runtime_service.py",
)
HARDCODE_SCOPE_SERVICE_SUFFIXES = (
    "_signal_service.py",
    "_runtime_service.py",
)
HARDCODE_ALLOW_MARKER = "hardcode-gate: allow"
HARDCODE_TECHNICAL_ALLOW_SNIPPETS = (
    're.findall(r"\\w+",',
    're.search(r"[а-яё]"',
    're.search(r"[a-z]"',
    're.findall(r"[a-z]"',
    're.match(r"^(?P<year>\\d{4})-(?P<month>\\d{2})-(?P<day>\\d{2})',
    're.search(r"\\d{4}-\\d{2}-\\d{2}"',
    're.search(r"\\b\\d{1,2}[./-]\\d{1,2}(?:[./-]\\d{2,4})?\\b"',
    're.fullmatch(r"([01]?\\d|2[0-3]):([0-5]\\d)"',
    "str.maketrans(",
)

CANONICAL_WRITE_SCAN_PATHS = (
    "truffles-api/app/services/intent_service.py",
    "truffles-api/app/core/turn_planner.py",
    "truffles-api/app/core/dialog_state_service.py",
    "truffles-api/app/core/consultant_runtime.py",
    "truffles-api/app/core/turn_executor.py",
    "truffles-api/app/core/response_realizer.py",
    "truffles-api/app/routers/webhook/decision.py",
    "truffles-api/app/routers/webhook/info.py",
    "truffles-api/app/routers/webhook/booking.py",
    "truffles-api/app/routers/webhook/response.py",
    "truffles-api/app/routers/webhook/class_router_runtime.py",
    "truffles-api/app/routers/webhook/booking_compat.py",
    "truffles-api/app/routers/webhook/decision_compat.py",
    "truffles-api/app/routers/webhook/info_compat.py",
    "truffles-api/app/routers/webhook/info_followup_compat.py",
    "truffles-api/app/routers/webhook/policy_compat.py",
    "truffles-api/app/routers/webhook/response_compat.py",
    "truffles-api/app/services/pack_runtime_compat.py",
    "truffles-api/app/services/demo_salon_knowledge_compat.py",
)

LEGAL_CANONICAL_WRITE_PATHS = {
    "truffles-api/app/services/intent_service.py",
    "truffles-api/app/core/turn_planner.py",
    "truffles-api/app/core/dialog_state_service.py",
}

KNOWN_NON_OWNER_CANONICAL_WRITE_SIGNATURES = {
    ("truffles-api/app/core/consultant_runtime.py", "_build_policy_core_memory_profile", "profile", "semantic_contract", "subscript_assign"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "decision_meta", "action", "dict_literal"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "decision_meta", "active_question_relation", "subscript_assign"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "decision_meta", "expected_reply_reason", "subscript_assign"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "decision_meta", "expected_reply_type", "subscript_assign"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "decision_meta", "outcome", "dict_literal"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "decision_meta", "pending_question_target", "subscript_assign"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "decision_meta", "semantic_contract", "subscript_assign"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "decision_meta", "semantic_frame", "subscript_assign"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "interaction_entry", "active_question_relation", "dict_literal"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "interaction_entry", "expected_reply_type", "dict_literal"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "interaction_entry", "pending_question_target", "dict_literal"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "question_contract_entry", "active_question_relation", "subscript_assign"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "question_contract_entry", "expected_reply_type", "dict_literal"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "question_contract_entry", "pending_question_target", "dict_literal"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "trace_event", "active_question_relation", "subscript_assign"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "trace_event", "expected_reply_reason", "subscript_assign"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "trace_event", "expected_reply_type", "subscript_assign"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "trace_event", "outcome", "dict_literal"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "trace_event", "pending_question_target", "subscript_assign"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "trace_event", "semantic_contract", "subscript_assign"): 1,
    ("truffles-api/app/core/consultant_runtime.py", "_record_turn_trace", "trace_event", "semantic_frame", "subscript_assign"): 1,
    ("truffles-api/app/core/response_realizer.py", "realize", "meta", "outcome", "subscript_assign"): 1,
    ("truffles-api/app/core/turn_executor.py", "_attach_semantic_contract_meta", "payload", "semantic_contract", "subscript_assign"): 1,
    ("truffles-api/app/routers/webhook/booking.py", "_handle_booking_interrupt", "message_meta_updates", "pending_question_target", "subscript_assign"): 1,
    ("truffles-api/app/routers/webhook/booking.py", "_handle_booking_interrupt", "trace_payload", "pending_question_target", "subscript_assign"): 1,
    ("truffles-api/app/routers/webhook/decision.py", "_apply_expected_reply_contract", "bypass_trace", "expected_reply_type", "dict_literal"): 1,
    ("truffles-api/app/routers/webhook/decision.py", "_apply_expected_reply_contract", "bypass_updates", "expected_reply_type", "dict_literal"): 1,
    ("truffles-api/app/routers/webhook/decision.py", "_apply_expected_reply_contract", "interaction_trace", "expected_reply_type", "dict_literal"): 1,
    ("truffles-api/app/routers/webhook/decision.py", "_apply_expected_reply_contract", "interaction_trace", "pending_question_target", "dict_literal"): 1,
    ("truffles-api/app/routers/webhook/decision.py", "_apply_expected_reply_contract", "interaction_updates", "pending_question_target", "dict_literal"): 1,
    ("truffles-api/app/routers/webhook/decision.py", "_apply_expected_reply_contract", "trace_payload", "expected_reply_type", "dict_literal"): 1,
    ("truffles-api/app/routers/webhook/decision.py", "_apply_expected_reply_contract", "updates", "expected_reply_type", "dict_literal"): 1,
    ("truffles-api/app/routers/webhook/decision.py", "_run_intent_decomposition", "intent_queue_event", "expected_reply_type", "dict_literal"): 1,
    ("truffles-api/app/routers/webhook/decision.py", "_run_intent_decomposition", "trace_payload", "expected_reply_reason", "subscript_assign"): 1,
    ("truffles-api/app/routers/webhook/decision.py", "_run_intent_decomposition", "trace_payload", "expected_reply_type", "subscript_assign"): 1,
    ("truffles-api/app/routers/webhook/info.py", "_handle_truth_gate_fallback", "override_meta", "expected_reply_type", "call.update"): 1,
    ("truffles-api/app/routers/webhook/info.py", "_handle_truth_gate_fallback", "trace_payload", "expected_reply_type", "dict_literal"): 1,
    ("truffles-api/app/routers/webhook/response.py", "_apply_locked_consult_topic_shift", "consult_meta", "expected_reply_reason", "subscript_assign"): 1,
    ("truffles-api/app/routers/webhook/response.py", "_apply_locked_consult_topic_shift", "consult_meta", "expected_reply_type", "subscript_assign"): 1,
    ("truffles-api/app/routers/webhook/response.py", "_handle_consult_flow", "consult_flow_trace", "expected_reply_type", "subscript_assign"): 1,
    ("truffles-api/app/routers/webhook/response.py", "_handle_consult_flow", "consult_meta", "expected_reply_reason", "subscript_assign"): 1,
    ("truffles-api/app/routers/webhook/response.py", "_handle_consult_flow", "consult_meta", "expected_reply_type", "subscript_assign"): 4,
}


GLOBAL_FORBIDDEN = (
    "synthetic_policy_decision",
    "build_controlled_degrade(",
    "build_preflight_reject(",
    "_semantic_contract_from_frame(",
    "resolve_timeout_owner_boundary(",
    "owner_replacement_cutover",
)

CONTAINED_PACK_API_TOKENS = (
    "get_pack_decision(",
    "get_pack_service_decision(",
    "get_pack_service_hint(",
    "get_pack_price_item(",
    "get_pack_price_reply(",
    "semantic_service_match(",
    "semantic_question_type(",
    "phrase_match_intent(",
    "resolve_master_intent(",
)

CONTAINED_PACK_API_ALLOWED_FILES = {
    "truffles-api/app/services/pack_runtime_compat.py",
    "truffles-api/app/services/demo_salon_knowledge_compat.py",
}

COMPAT_IMPORT_ALLOWED_FILES = {
    "truffles-api/app/routers/webhook/_legacy.py",
}

CLASS_ROUTER_COMPAT_TOKENS = (
    "_resolve_class_router_result(",
    "route_dialogue_controller(",
)

CLASS_ROUTER_COMPAT_ALLOWED_FILES = {
    "truffles-api/app/routers/webhook/_legacy.py",
    "truffles-api/app/routers/webhook/class_router_runtime.py",
    "truffles-api/app/services/intent_service.py",
}

FILE_RULES = {
    "truffles-api/app/services/intent_service.py": {
        "must_absent": (
            "from app.services.pack_runtime_service import get_pack_service_hint",
            "return get_pack_service_hint(message, client_slug=normalized_client_slug)",
        ),
    },
    "truffles-api/app/services/pack_runtime_service.py": {
        "must_absent": (
            "semantic_query = get_pack_service_hint(message_text, client_slug=client_slug)",
            "if not resolved_service and message_text:",
            "_pack_query_service_context(\n            message_text,",
            "def _resolve_compat_master_service_query(",
            '"compat_hint"',
            "def _compat_service_semantics(",
            "def _compat_service_hint(",
            "def _compat_price_item_lookup(",
            "def _compat_price_reply_builder(",
            "def _compat_truth_gate_builder(",
            "def _compat_service_decision_builder(",
            "def _compat_master_resolver(",
            "def get_pack_decision(",
            "def get_pack_service_decision(",
            "def get_pack_service_hint(",
            "def get_pack_price_item(",
            "def get_pack_price_reply(",
            "def resolve_master_intent(",
            "def semantic_service_match(",
            '"get_pack_decision",',
            '"get_pack_service_decision",',
            '"get_pack_service_hint",',
            '"get_pack_price_item",',
            '"get_pack_price_reply",',
            '"resolve_master_intent",',
            '"semantic_service_match",',
            '"phrase_match_intent",',
            '"semantic_question_type",',
        ),
    },
    "truffles-api/app/services/pack_runtime_default.py": {
        "must_absent": (
            "def get_pack_decision(",
            "def get_pack_service_decision(",
            "def get_pack_service_hint(",
            "def get_pack_price_item(",
            "def get_pack_price_reply(",
            "def semantic_service_match(",
            "def semantic_question_type(",
            "def phrase_match_intent(",
            "def _compat_truth_gate_builder(",
            "def _compat_service_decision_builder(",
            "def _compat_price_reply_builder(",
            "def _compat_price_item_lookup(",
            "def _compat_service_hint(",
            "def _compat_phrase_intents(",
            "def _compat_question_classifier(",
            "def _compat_service_semantics(",
            '"get_pack_decision",',
            '"get_pack_service_decision",',
            '"get_pack_service_hint",',
            '"get_pack_price_item",',
            '"get_pack_price_reply",',
            '"semantic_service_match",',
            '"semantic_question_type",',
            '"phrase_match_intent",',
        ),
    },
    "truffles-api/app/services/pack_runtime_neutral_adapter.py": {
        "must_absent": (
            "def get_pack_decision(",
            "def get_pack_service_decision(",
            "def get_pack_service_hint(",
            "def get_pack_price_item(",
            "def get_pack_price_reply(",
            "def semantic_service_match(",
            "def semantic_question_type(",
            "def phrase_match_intent(",
            "def _compat_truth_gate_builder(",
            "def _compat_service_decision_builder(",
            "def _compat_price_reply_builder(",
            "def _compat_price_item_lookup(",
            "def _compat_service_hint(",
            "def _compat_phrase_intents(",
            "def _compat_question_classifier(",
            "def _compat_service_semantics(",
            '"get_pack_decision",',
            '"get_pack_service_decision",',
            '"get_pack_service_hint",',
            '"get_pack_price_item",',
            '"get_pack_price_reply",',
            '"semantic_service_match",',
            '"semantic_question_type",',
            '"phrase_match_intent",',
        ),
    },
    "truffles-api/app/services/demo_salon_knowledge.py": {
        "must_absent": (
            "def _compat_demo_service_decision(",
            "def _compat_demo_decision(",
            "def _compat_demo_price_reply(",
            "def _compat_demo_price_item(",
            "def _compat_demo_service_hint(",
            "def get_pack_decision(",
            "def get_pack_service_decision(",
            "def get_pack_service_hint(",
            "def get_pack_price_item(",
            "def get_pack_price_reply(",
            "def semantic_service_match(",
            "def semantic_question_type(",
            "def phrase_match_intent(",
            "def _compat_truth_gate_builder(",
            "def _compat_service_decision_builder(",
            "def _compat_price_reply_builder(",
            "def _compat_price_item_lookup(",
            "def _compat_service_hint(",
            "def _compat_phrase_intents(",
            "def _compat_question_classifier(",
            "def _compat_service_semantics(",
            "def get_demo_salon_decision(",
            "def get_demo_salon_service_decision(",
            "def get_demo_salon_service_hint(",
            "def get_demo_salon_price_reply(",
            "def get_demo_salon_price_item(",
        ),
    },
    "truffles-api/app/services/pack_runtime_demo_adapter.py": {
        "must_absent": (
            '"get_pack_decision",',
            '"get_pack_service_decision",',
            '"get_pack_service_hint",',
            '"get_pack_price_item",',
            '"get_pack_price_reply",',
            '"semantic_service_match",',
            '"semantic_question_type",',
            '"phrase_match_intent",',
        ),
        "must_present": (
            "_COMPAT_EXPORTS = [",
            '"_build_pack_query_truth_decision",',
            '"_build_pack_query_service_decision",',
            '"_resolve_pack_query_service_hint",',
        ),
    },
    "truffles-api/app/routers/webhook/info.py": {
        "must_absent": (
            "from ._legacy import",
            "info_followup_runtime",
            "_looks_like_carryover_followup(",
            "_looks_like_hours_followup(",
            "def _looks_like_services_overview_message(",
            "def _detect_location_policy_pack_refs(",
            "def _looks_like_hours_policy_message(",
            "def _looks_like_promotions_policy_message(",
            "def _looks_like_promotions_rules_policy_message(",
            "def _detect_info_anchor_hits(",
            "def _looks_like_daypart_preference_statement(",
            "def _detect_info_class_intents(",
            "def _looks_like_info_query(",
            "get_pack_price_reply(",
            "get_pack_price_item(",
            "message=message_text if not resolved_service_query else None",
            "_build_controller_meta_output(",
            "_ensure_controller_output_meta(",
            "_resolve_controller_signal_class(",
            "_has_price_signal(normalized_message, message_text)",
            "_has_duration_signal(normalized_message, message_text)",
            "router_service_query",
            'slots.get("service_query")',
            'info_semantic_lock = guest_policy_lock or info_bundle_lock or controller_low_confidence',
            'skip_reason = "controller_low_confidence"',
            'base_info_override = bool(info_signals.get("parking") or info_signals.get("guest"))',
            'include_base_bundle = bool({"location"} & info_class_intents_for_reply)',
            'for key in ("parking", "guest", "location")',
            "_has_parking_signal(",
            "_has_guest_waiting_signal(",
            "location_signal = _signal_any_match(",
            "intent in {\"location\", \"hours\"} or location_signal or parking_signal or guest_signal",
            "phrase_match_intent(",
            "semantic_question_type(",
            "reason\": \"short_noisy_followup\"",
            "def _handle_offline_info_class(",
            "def _handle_info_flow(",
            "_resolve_class_router_result(",
            "response_compat",
        ),
        "must_present": (
            "build_master_reply_from_pack(\n            client_slug=client_slug,\n            message_text=None,",
            "build_observer_class_router_result(",
        ),
    },
    "truffles-api/app/routers/webhook/booking.py": {
        "must_absent": (
            "get_pack_price_item(",
            "def _looks_like_booking_reschedule_request(",
            "_looks_like_promotions_request(",
            "_build_controller_meta_output(",
            "_ensure_controller_output_meta(",
            "_resolve_class_router_result(",
            "_resolve_controller_signal_class(",
        ),
        "must_present": (
            "resolve_explicit_master_intent(\n            client_slug=client_slug,",
            "build_observer_class_router_result(",
        ),
    },
    "truffles-api/app/routers/webhook/policy.py": {
        "must_absent": (
            "price_reply = get_pack_price_reply(message, client_slug=client_slug)",
            '"price_item": get_pack_price_item',
            "def _looks_like_policy_topic(",
            "def _looks_like_promotions_request(",
        ),
    },
    "truffles-api/app/routers/webhook/decision.py": {
        "must_absent": (
            "def _is_timeout_pending_time_slot_question(",
            "def _is_timeout_master_info_interrupt_candidate(",
            "def _is_timeout_active_time_specialist_interrupt_candidate(",
            "info_followup_runtime",
            "_looks_like_carryover_followup(",
            "_looks_like_hours_followup(",
            "def _looks_like_promo_code_request(",
            "def _format_discounts_reply_for_message(",
            "resolve_master_intent(",
            "_has_duration_signal(normalized_service_message, message_text)",
            "def _build_router_state(",
            "def _controller_meta_updates_from_router_state(",
            "route_dialogue_controller(",
            "_resolve_class_router_result(",
            "response_compat",
        ),
    },
    "truffles-api/app/routers/webhook/expected_reply_interrupt_runtime.py": {
        "must_absent": (
            "_has_price_signal(",
            "_has_duration_signal(",
        ),
    },
    "truffles-api/app/routers/webhook/response.py": {
        "must_absent": (
            "_build_controller_meta_output(",
            "_ensure_controller_output_meta(",
            "_resolve_class_router_result(",
            "_resolve_controller_signal_class(",
            'router_output_class == "out_of_domain"',
            "controller_service_query",
            'slots.get("service_query")',
            'router_intents = class_router_result.get("intents")',
            'if out_of_domain_signal and not expected_reply_shortcircuit:',
            'in_signals = class_router_result.get("in_signals") or []',
            'anchors_in_hits = int(class_router_result.get("anchors_in_hits") or 0)',
            '"decision": "domain_anchor"',
            '"decision": "service_semantic_guard"',
            '"decision": "no_response_guard"',
            '"decision": "router_low_confidence"',
            'def _handle_ai_response_action(',
            "response_compat",
        ),
        "must_present": (
            "build_observer_class_router_result(",
        ),
    },
    "truffles-api/app/routers/webhook/class_router_runtime.py": {
        "must_absent": (
            'result["classes"] = [controller_class]',
            'result["intents"] = sorted(info_controller_intents)',
            'controller_used_reason = "deterministic"',
            'controller_output = {**controller_output, "class": controller_class, "goal": controller_goal}',
        ),
    },
    "truffles-api/app/services/tool_registry_service.py": {
        "must_absent": (
            ".get_pack_price_item(",
            ".get_pack_price_reply(",
        ),
        "must_present": (
            "resolve_runtime_service_price_item(",
            "format_runtime_price_item_reply(",
        ),
    },
    "truffles-api/app/services/demo_salon_knowledge_compat.py": {
        "must_present": (
            "_build_demo_truth_decision as get_demo_salon_decision",
            "_resolve_demo_price_item as get_demo_salon_price_item",
            "_build_demo_price_reply as get_demo_salon_price_reply",
            "_build_demo_service_decision as get_demo_salon_service_decision",
            "_resolve_demo_service_hint as get_demo_salon_service_hint",
            "_pack_query_phrase_intents as phrase_match_intent",
            "_pack_query_question_classifier as semantic_question_type",
            "_resolve_pack_query_semantic_match as semantic_service_match",
        ),
    },
    "truffles-api/app/services/pack_runtime_compat.py": {
        "must_present": (
            "_build_pack_query_truth_decision as get_pack_decision",
            "_build_pack_query_service_decision as get_pack_service_decision",
            "_resolve_pack_query_service_hint as get_pack_service_hint",
            "_resolve_pack_query_semantic_match as semantic_service_match",
            "_resolve_pack_query_master_intent as resolve_master_intent",
            "def phrase_match_intent(",
            "def semantic_question_type(",
        ),
    },
    "truffles-api/app/routers/webhook/booking_compat.py": {
        "must_present": (
            "def _looks_like_booking_reschedule_request(",
        ),
    },
    "truffles-api/app/routers/webhook/decision_compat.py": {
        "must_present": (
            "def _looks_like_promo_code_request(",
            "def _format_discounts_reply_for_message(",
        ),
    },
    "truffles-api/app/routers/webhook/info_compat.py": {
        "must_present": (
            "from ._legacy import (",
            "_detect_info_class_intents",
            "_looks_like_info_query",
            "_looks_like_services_overview_message",
        ),
    },
    "truffles-api/app/routers/webhook/info_followup_compat.py": {
        "must_present": (
            "def _looks_like_carryover_followup(",
            "def _looks_like_hours_followup(",
        ),
    },
    "truffles-api/app/routers/webhook/policy_compat.py": {
        "must_present": (
            "def _looks_like_policy_topic(",
            "def _looks_like_promotions_request(",
        ),
    },
}

LOCAL_SUBGUARD_SCRIPTS = (
    "semantic_contract_sync_guard.py",
    "boundary_rewrite_guard.py",
)


def _source_segment(source: str, node: ast.AST | None) -> str | None:
    if node is None:
        return None
    return (ast.get_source_segment(source, node) or "").strip() or None


def _literal_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _assignment_targets(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.Assign):
        return list(node.targets)
    if isinstance(node, ast.AnnAssign):
        return [node.target]
    if isinstance(node, ast.AugAssign):
        return [node.target]
    return []


def _assignment_value(node: ast.AST) -> ast.AST | None:
    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        return getattr(node, "value", None)
    return None


def _iter_dict_entries(node: ast.Dict) -> list[tuple[str, ast.AST]]:
    entries: list[tuple[str, ast.AST]] = []
    for key, value in zip(node.keys, node.values):
        key_token = _literal_string(key)
        if key_token is not None:
            entries.append((key_token, value))
    return entries


class _CanonicalWriteScanner(ast.NodeVisitor):
    def __init__(self, *, relative_path: str, source: str):
        self.relative_path = relative_path
        self.source = source
        self.function_stack: list[str] = []
        self.signatures: list[tuple[str, str | None, str | None, str, str]] = []

    def _record(self, *, field: str, kind: str, container: str | None) -> None:
        if self.relative_path in LEGAL_CANONICAL_WRITE_PATHS:
            return
        self.signatures.append(
            (
                self.relative_path,
                self.function_stack[-1] if self.function_stack else None,
                container,
                field,
                kind,
            )
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        self._scan_assignment(node)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._scan_assignment(node)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._scan_assignment(node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute):
            container = _source_segment(self.source, func.value)
            if func.attr == "setdefault" and node.args:
                key = _literal_string(node.args[0])
                if key in CANONICAL_FIELDS:
                    self._record(field=key, kind="call.setdefault", container=container)
            if func.attr == "update" and node.args and isinstance(node.args[0], ast.Dict):
                for key, _value in _iter_dict_entries(node.args[0]):
                    if key in CANONICAL_FIELDS:
                        self._record(field=key, kind="call.update", container=container)
            if func.attr == "model_copy":
                for keyword in node.keywords:
                    if keyword.arg == "update" and isinstance(keyword.value, ast.Dict):
                        for key, _value in _iter_dict_entries(keyword.value):
                            if key in CANONICAL_FIELDS:
                                self._record(
                                    field=key,
                                    kind="call.model_copy_update",
                                    container=container,
                                )
        self.generic_visit(node)

    def _scan_assignment(self, node: ast.AST) -> None:
        targets = _assignment_targets(node)
        value = _assignment_value(node)
        if isinstance(value, ast.Dict):
            containers = [_source_segment(self.source, target) for target in targets] or [None]
            container = next((item for item in containers if item), None)
            for key, _entry_value in _iter_dict_entries(value):
                if key in CANONICAL_FIELDS:
                    self._record(field=key, kind="dict_literal", container=container)
        for target in targets:
            if isinstance(target, ast.Subscript):
                key = _literal_string(target.slice)
                if key in CANONICAL_FIELDS:
                    self._record(
                        field=key,
                        kind="subscript_assign",
                        container=_source_segment(self.source, target.value),
                    )


def _collect_canonical_write_signatures(repo_root: Path) -> Counter[tuple[str, str | None, str | None, str, str]]:
    signatures: Counter[tuple[str, str | None, str | None, str, str]] = Counter()
    for relative_path in CANONICAL_WRITE_SCAN_PATHS:
        path = repo_root / relative_path
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        scanner = _CanonicalWriteScanner(relative_path=relative_path, source=source)
        scanner.visit(tree)
        signatures.update(scanner.signatures)
    return signatures


def _canonical_write_violations(repo_root: Path) -> list[str]:
    violations: list[str] = []
    current = _collect_canonical_write_signatures(repo_root)
    for signature, count in sorted(current.items()):
        allowed_count = KNOWN_NON_OWNER_CANONICAL_WRITE_SIGNATURES.get(signature, 0)
        if count <= allowed_count:
            continue
        path, function, container, field, kind = signature
        violations.append(
            f"{path} contains unexpected canonical write signature "
            f"(function={function or '<module>'}, container={container or '<unknown>'}, "
            f"field={field}, kind={kind}, allowed_count={allowed_count}, actual_count={count})"
        )
    return violations


def _collect_git_changed_files(repo_root: Path, base_ref: str) -> tuple[list[str], list[str]]:
    changed: set[str] = set()
    scan_warnings: list[str] = []
    commands = [
        (
            [
                "git",
                "-C",
                str(repo_root),
                "diff",
                "--name-only",
                f"{base_ref}...HEAD",
                "--",
            ],
            "base_diff",
        ),
        (["git", "-C", str(repo_root), "diff", "--name-only", "--"], "worktree_diff"),
        (["git", "-C", str(repo_root), "diff", "--name-only", "--cached", "--"], "staged_diff"),
    ]
    for cmd, label in commands:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except Exception as exc:
            scan_warnings.append(f"{label}_exec_error:{exc.__class__.__name__}")
            continue
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            if stderr:
                scan_warnings.append(f"{label}_error:{stderr[:120]}")
            else:
                scan_warnings.append(f"{label}_error:rc{result.returncode}")
            continue
        for line in (result.stdout or "").splitlines():
            path = line.strip().replace("\\", "/")
            if path:
                changed.add(path)
    return sorted(changed), scan_warnings


def _is_hardcode_scope_file(path: str) -> bool:
    normalized = str(path or "").strip().replace("\\", "/")
    if not normalized:
        return False
    if normalized in HARDCODE_CORE_PREFIXES:
        return True
    if normalized.startswith(HARDCODE_SCOPE_CORE_PREFIX) and normalized.endswith(".py"):
        return True
    if normalized.startswith(HARDCODE_SCOPE_WEBHOOK_PREFIX) and normalized.endswith(".py"):
        return True
    if not normalized.startswith(HARDCODE_SCOPE_SERVICE_PREFIX):
        return False
    if normalized in HARDCODE_SCOPE_SERVICE_FILES:
        return True
    return normalized.endswith(HARDCODE_SCOPE_SERVICE_SUFFIXES)


def _line_has_phrase_branching(line: str, *, path: str | None = None) -> bool:
    if not isinstance(line, str):
        return False
    stripped = line.strip()
    if not stripped:
        return False
    lowered = stripped.casefold()
    normalized_path = str(path or "").strip().replace("\\", "/").casefold()
    is_signal_file = normalized_path.endswith("_signal_service.py")
    if lowered.startswith("#"):
        return False
    if HARDCODE_ALLOW_MARKER in lowered:
        return False
    if any(token in lowered for token in HARDCODE_TECHNICAL_ALLOW_SNIPPETS):
        return False
    if any(
        token in lowered
        for token in (
            "get_signal_lexicon_list(",
            "get_system_lexicon_list(",
            "phrase_match_intent(",
            "has_walkin_without_booking_signal(",
        )
    ):
        return False
    has_context_token = any(
        token in lowered
        for token in (
            "message_text",
            "normalized",
            "normalize_for_matching",
            "_normalize_text",
        )
    )
    if not has_context_token and not is_signal_file:
        return False
    has_branch_operator = any(
        token in lowered
        for token in (
            " in ",
            ".startswith(",
            ".endswith(",
            "re.search(",
            "re.match(",
            "re.compile(",
            "=",
        )
    )
    if not has_branch_operator:
        return False
    literals: list[str] = []
    pattern = r'"([^"\\]{3,}|[^"\\]{2,}\s[^"\\]*)"|\'([^\'\\]{3,}|[^\'\\]{2,}\s[^\'\\]*)\''
    for match in re.finditer(pattern, stripped):
        literal = match.group(1) or match.group(2)
        if not isinstance(literal, str):
            continue
        literal = literal.strip()
        if literal:
            literals.append(literal)
    if not literals:
        return False
    for literal in literals:
        if re.fullmatch(r"[a-z_][a-z0-9_]{1,63}", literal.strip().casefold()):
            continue
        letters = sum(1 for ch in literal if ch.isalpha())
        if letters >= 3:
            return True
    return False


def _collect_hardcode_core_violations(
    *,
    repo_root: Path,
    base_ref: str,
    core_files: list[str],
) -> tuple[list[dict[str, str]], list[str]]:
    violations: list[dict[str, str]] = []
    scan_warnings: list[str] = []
    if not core_files:
        return violations, scan_warnings
    command_specs = [
        (
            [
                "git",
                "-C",
                str(repo_root),
                "diff",
                "--unified=0",
                f"{base_ref}...HEAD",
                "--",
            ],
            "base_diff",
        ),
        (["git", "-C", str(repo_root), "diff", "--unified=0", "--"], "worktree_diff"),
        (["git", "-C", str(repo_root), "diff", "--unified=0", "--cached", "--"], "staged_diff"),
    ]
    for command_prefix, source in command_specs:
        cmd = [*command_prefix, *core_files]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except Exception as exc:
            scan_warnings.append(f"{source}_exec_error:{exc.__class__.__name__}")
            continue
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            if stderr:
                scan_warnings.append(f"{source}_error:{stderr[:120]}")
            else:
                scan_warnings.append(f"{source}_error:rc{result.returncode}")
            continue
        current_file: str | None = None
        for raw_line in (result.stdout or "").splitlines():
            if raw_line.startswith("+++ b/"):
                current_file = raw_line.replace("+++ b/", "", 1).strip()
                continue
            if not raw_line.startswith("+") or raw_line.startswith("+++"):
                continue
            content = raw_line[1:]
            if not _line_has_phrase_branching(content, path=current_file):
                continue
            violations.append(
                {
                    "path": current_file or "<unknown>",
                    "source": source,
                    "line": content.strip(),
                }
            )
    deduped: dict[tuple[str, str], dict[str, str]] = {}
    for item in violations:
        key = (str(item.get("path") or "").strip(), str(item.get("line") or "").strip())
        deduped.setdefault(key, item)
    return list(deduped.values()), scan_warnings


def _hardcode_core_diff_violations(repo_root: Path, *, base_ref: str = "HEAD") -> list[str]:
    if not (repo_root / ".git").exists():
        return []
    changed_files, _scan_warnings = _collect_git_changed_files(repo_root, base_ref)
    core_changed_files = [path for path in changed_files if _is_hardcode_scope_file(path)]
    violations, _scan_warnings_extra = _collect_hardcode_core_violations(
        repo_root=repo_root,
        base_ref=base_ref,
        core_files=core_changed_files,
    )
    return [
        f"{item['path']} contains forbidden semantic hardcode diff line via {item['source']}: {item['line']}"
        for item in violations
    ]


def _local_subguard_violations(repo_root: Path) -> list[str]:
    violations: list[str] = []
    scripts_root = Path(__file__).resolve().parent
    for script_name in LOCAL_SUBGUARD_SCRIPTS:
        script_path = scripts_root / script_name
        if not script_path.exists():
            violations.append(f"required local subguard missing: scripts/{script_name}")
            continue
        result = subprocess.run(
            [sys.executable, str(script_path), "--repo-root", str(repo_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            continue
        stderr_lines = [line.strip() for line in (result.stderr or "").splitlines() if line.strip()]
        stdout_lines = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
        messages = stderr_lines or stdout_lines or [f"{script_name} exited with code {result.returncode}"]
        for message in messages:
            violations.append(f"{script_name}: {message}")
    return violations


def evaluate(repo_root: Path, *, base_ref: str = "HEAD") -> list[str]:
    violations: list[str] = []
    app_root = repo_root / "truffles-api" / "app"
    for path in app_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in GLOBAL_FORBIDDEN:
            if token in text:
                violations.append(f"{path.relative_to(repo_root)} contains forbidden token {token!r}")

    for relative_path, rules in FILE_RULES.items():
        path = repo_root / relative_path
        text = path.read_text(encoding="utf-8")
        for token in rules.get("must_absent", ()):
            if token in text:
                violations.append(f"{relative_path} still contains forbidden snippet {token!r}")
        for token in rules.get("must_present", ()):
            if token not in text:
                violations.append(f"{relative_path} is missing required snippet {token!r}")

    for path in app_root.rglob("*.py"):
        relative_path = str(path.relative_to(repo_root))
        if relative_path.endswith("_legacy.py"):
            continue
        if relative_path in CONTAINED_PACK_API_ALLOWED_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        for token in CONTAINED_PACK_API_TOKENS:
            if token in text:
                violations.append(
                    f"{relative_path} contains contained pack API token {token!r} outside the allowed service boundary"
                )
        if "pack_runtime_compat" in text and relative_path not in COMPAT_IMPORT_ALLOWED_FILES:
            violations.append(
                f"{relative_path} imports compatibility-only pack runtime helpers outside the allowed legacy surface"
            )
        if "response_compat" in text:
            violations.append(
                f"{relative_path} imports compatibility-only response helpers outside tests/compat surfaces"
            )
        for token in CLASS_ROUTER_COMPAT_TOKENS:
            if token in text and relative_path not in CLASS_ROUTER_COMPAT_ALLOWED_FILES:
                violations.append(
                    f"{relative_path} contains class-router compatibility token {token!r} outside the allowed boundary"
                )
    violations.extend(_canonical_write_violations(repo_root))
    violations.extend(_hardcode_core_diff_violations(repo_root, base_ref=base_ref))
    violations.extend(_local_subguard_violations(repo_root))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repository root to scan",
    )
    parser.add_argument(
        "--base-ref",
        default="HEAD",
        help="Git base ref for diff-scoped hardcode detection",
    )
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    violations = evaluate(repo_root, base_ref=args.base_ref)
    if violations:
        for item in violations:
            print(item)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
