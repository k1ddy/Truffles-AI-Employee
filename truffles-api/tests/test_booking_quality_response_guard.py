import ast
import json
import math
import re
from pathlib import Path
from types import SimpleNamespace


def _load_retry_helper():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    selected_nodes = []
    wanted_functions = {
        "_llm_quality_retry_outbox_for_expected_reply",
        "_llm_quality_has_bot_reply",
        "_llm_quality_outbox_delivery_state",
        "_llm_quality_resolve_outbox_status",
        "_llm_quality_normalize_outbox_status",
    }
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if {
                "LLM_QUALITY_OUTBOX_SUCCESS_STATUSES",
                "LLM_QUALITY_OUTBOX_FAILURE_STATUSES",
                "LLM_QUALITY_OUTBOX_PENDING_STATUSES",
            } & names:
                selected_nodes.append(node)
        if isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {"math": math, "time": SimpleNamespace(sleep=lambda _sec: None)}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace


def _load_evaluate_turn():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    wanted_functions = {
        "_llm_quality_evaluate_turn",
        "_llm_quality_effective_intent",
        "_llm_quality_has_catalog_service_choice_info_fallback",
        "_llm_quality_has_master_query_missing_subject_info_fallback",
        "_llm_quality_has_pricing_service_clarify_info_fallback",
        "_llm_quality_has_general_consult_fallback",
        "_llm_quality_is_booking_confirmation_text",
        "_llm_quality_is_unobserved_turn",
        "_llm_quality_normalize_tool_token",
        "_llm_quality_parse_slot_candidates",
        "_llm_quality_normalize_time_token",
        "_llm_quality_is_time_like_token",
        "_llm_quality_extract_availability_claim",
        "_llm_quality_extract_available_slots_by_specialist",
        "_llm_quality_has_booking_prompt_leak",
        "_llm_quality_has_stale_booking_carryover",
        "_llm_quality_has_missing_canonical_service_projection",
        "_llm_quality_has_missing_resolved_referent_trace",
        "_llm_quality_collect_fact_evidence_refs",
        "_llm_quality_is_fact_like_reply",
        "_llm_quality_has_fact_without_evidence",
        "_llm_quality_has_booking_commit_without_required_contact",
        "_llm_quality_has_irrelevant_fact",
        "_llm_quality_has_stale_state_leak",
        "_llm_quality_has_timeout_degrade_booking_generic",
        "_llm_quality_has_expected_followup_prompt",
        "_llm_quality_has_pending_question_interaction_contract",
        "_llm_quality_normalize_expect_token",
        "_llm_quality_value_matches",
        "_llm_quality_normalize_expect_mapping",
        "_llm_quality_normalize_expect_contains_mapping",
        "_llm_quality_normalize_expect_trace_contains",
        "_llm_quality_entry_matches_expected",
        "_llm_quality_meta_matches_expected",
        "_llm_quality_meta_matches_timeout_grounded_slot_constraint_name_resume",
        "_llm_quality_trace_has_expected_entries",
        "_llm_quality_text_has_billing_block_marker",
        "_llm_quality_payload_has_billing_block_marker",
        "_llm_quality_is_delivery_billing_waiver",
        "_normalize_phone_digits",
        "_llm_quality_outbox_delivery_state",
        "_llm_quality_resolve_outbox_status",
        "_llm_quality_normalize_outbox_status",
        "_llm_quality_trace_missing_soft",
    }
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if {
                "LLM_QUALITY_KNOWN_STATES",
                "LLM_QUALITY_BOOKING_CONFIRM_STATUS_HINTS",
                "LLM_QUALITY_BOOKING_CONFIRM_PHRASES",
                "LLM_QUALITY_CALENDAR_INTENTS",
                "LLM_QUALITY_OUTBOX_SUCCESS_STATUSES",
                "LLM_QUALITY_OUTBOX_FAILURE_STATUSES",
                "LLM_QUALITY_OUTBOX_PENDING_STATUSES",
                "CHAOS_PENDING_ACTIONS",
            } & names:
                selected_nodes.append(node)
        if isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {
        "re": re,
        "_llm_quality_value_matches": lambda *_args, **_kwargs: True,
        "_chaos_reply_type_fallback_ok": lambda *_args, **_kwargs: False,
        "_llm_quality_collect_info_signals": lambda *_args, **_kwargs: (set(), set()),
        "_llm_quality_expected_section_answered": lambda *_args, **_kwargs: (False, set(), set()),
        "_llm_quality_state_matches_expected": lambda *_args, **_kwargs: True,
        "_llm_quality_action_matches_expected": lambda *_args, **_kwargs: True,
        "_llm_quality_expected_reply_matches": lambda *_args, **_kwargs: True,
    }
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace["_llm_quality_evaluate_turn"]


def _load_dry_run_contract_helper():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    selected_nodes = []
    for node in tree.body:
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == "_llm_quality_apply_dry_run_response_contract"
        ):
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace["_llm_quality_apply_dry_run_response_contract"]


def _load_expectation_helpers():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    wanted_functions = {
        "_llm_quality_value_matches",
        "_llm_quality_state_matches_expected",
        "_llm_quality_action_matches_expected",
        "_llm_quality_expected_reply_matches",
        "_llm_quality_normalize_tool_token",
    }
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if {"CHAOS_PENDING_ACTIONS", "CHAOS_BOOKING_REPLY_TYPES"} & names:
                selected_nodes.append(node)
        if isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {
        "_chaos_state_fallback_ok": (
            lambda expected, actual, meta, _conv_meta, _handover: (
                expected == "bot_active"
                and actual == "pending"
                and (meta or {}).get("action") == "escalate"
            )
        ),
        "_chaos_matches_action": (
            lambda meta, expected_actions: (meta or {}).get("action") in set(expected_actions)
        ),
        "_chaos_action_fallback_ok": (
            lambda expected, meta, _conv_meta, _trace, _info_ok: (
                "booking_escalated" in set(expected.get("action_any") or [])
                and (meta or {}).get("action") in {"booking_prompt", "booking_confirm", "reply"}
            )
        ),
        "_llm_quality_expected_section_answered": lambda *_args, **_kwargs: (False, set(), set()),
    }
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace


def _load_duplicate_ack_helpers():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    wanted_functions = {
        "_llm_quality_payload_is_duplicate_ack",
        "_llm_quality_should_infer_bot_response_from_duplicate_ack",
    }
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if {"CHAOS_PENDING_ACTIONS"} & names:
                selected_nodes.append(node)
        if isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {"json": json}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace


def _load_message_recovery_helper():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    wanted_functions = {
        "_escape_sql_literal",
        "_llm_quality_fetch_assistant_reply_from_messages",
    }
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {"json": json}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace


def _load_calendar_outcome_helper():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    wanted_functions = {
        "_llm_quality_normalize_tool_token",
        "_llm_quality_calendar_outcome_from_meta",
    }
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if {
                "LLM_QUALITY_BOOKING_CONFIRM_STATUS_HINTS",
                "LLM_QUALITY_CALENDAR_SUCCESS_DECISIONS",
                "LLM_QUALITY_CALENDAR_FAILURE_DECISIONS",
            } & names:
                selected_nodes.append(node)
        if isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace["_llm_quality_calendar_outcome_from_meta"]


def test_retry_helper_marks_bot_response_when_outbox_appears():
    namespace = _load_retry_helper()
    helper = namespace["_llm_quality_retry_outbox_for_expected_reply"]

    calls = {"summary": 0}

    def _fetch_summary(_db_user, _client_id, _inbound_message_id):
        calls["summary"] += 1
        if calls["summary"] < 2:
            return {"count": 0, "status": None}, None
        return {"count": 1, "status": "SENT"}, None

    def _fetch_payload(_db_user, _client_id, _inbound_message_id):
        if calls["summary"] < 2:
            return None, None, None
        return {"body": {"text": "ok"}}, "SENT", None

    namespace["_fetch_outbox_summary"] = _fetch_summary
    namespace["_llm_quality_fetch_outbox_payload"] = _fetch_payload
    namespace["_llm_quality_extract_outbox_text"] = (
        lambda payload: payload["body"]["text"] if payload else None
    )

    outbox_summary, _payload, _status, outbox_text, bot_response = helper(
        expected_response=True,
        bot_response=False,
        db_user="postgres",
        client_id="client",
        inbound_message_id="msg",
        inline_response_text=None,
        outbox_summary={"count": 0, "status": None},
        outbox_payload=None,
        outbox_payload_status=None,
        outbox_text=None,
        outbox_wait_seconds=0.6,
        poll_interval=0.2,
    )

    assert calls["summary"] >= 2
    assert bot_response is True
    assert outbox_summary["count"] == 1
    assert outbox_text == "ok"


def test_retry_helper_keeps_missing_when_outbox_failed_only():
    namespace = _load_retry_helper()
    helper = namespace["_llm_quality_retry_outbox_for_expected_reply"]

    calls = {"summary": 0}

    def _fetch_summary(_db_user, _client_id, _inbound_message_id):
        calls["summary"] += 1
        return {"count": 1, "status": "FAILED"}, None

    def _fetch_payload(_db_user, _client_id, _inbound_message_id):
        return {"body": {"text": "unsent"}}, "FAILED", None

    namespace["_fetch_outbox_summary"] = _fetch_summary
    namespace["_llm_quality_fetch_outbox_payload"] = _fetch_payload
    namespace["_llm_quality_extract_outbox_text"] = (
        lambda payload: payload["body"]["text"] if payload else None
    )

    outbox_summary, _payload, status, outbox_text, bot_response = helper(
        expected_response=True,
        bot_response=False,
        db_user="postgres",
        client_id="client",
        inbound_message_id="msg",
        inline_response_text=None,
        outbox_summary={"count": 0, "status": None},
        outbox_payload=None,
        outbox_payload_status=None,
        outbox_text=None,
        outbox_wait_seconds=0.6,
        poll_interval=0.2,
    )

    assert calls["summary"] >= 1
    assert outbox_summary["status"] == "FAILED"
    assert status == "FAILED"
    assert outbox_text == "unsent"
    assert bot_response is False


def test_booking_slot_stall_not_reported_in_pending_state():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={},
        trace_entries=[{"stage": "booking_commit"}],
        state="pending",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=False,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="service_choice",
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=True,
        booking_progressed=False,
        allow_booking_stall=False,
    )
    assert "booking_slot_stall" not in reasons


def test_booking_slot_stall_reported_in_bot_active_state():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={},
        trace_entries=[{"stage": "booking"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="service_choice",
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=True,
        booking_progressed=False,
        allow_booking_stall=False,
    )
    assert "booking_slot_stall" in reasons


def test_booking_slot_stall_not_reported_for_calendar_get_booking_reply():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={"action": "reply", "intent": "calendar.get_booking", "tool_decision": "ok"},
        trace_entries=[{"stage": "booking"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="service_choice",
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=True,
        booking_progressed=False,
        allow_booking_stall=False,
    )
    assert "booking_slot_stall" not in reasons


def test_booking_slot_stall_not_reported_for_calendar_list_slots_with_followup_prompt():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={"action": "reply", "intent": "calendar.list_slots", "tool_decision": "ok"},
        trace_entries=[{"stage": "booking"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="name",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=True,
        booking_progressed=False,
        allow_booking_stall=False,
        outbox_text=(
            "Свободные слоты: Айжан: 10:00, 11:00 | Алина: 12:00. "
            "Как вас зовут?"
        ),
    )
    assert "booking_slot_stall" not in reasons


def test_booking_slot_stall_not_reported_for_calendar_list_slots_with_success_signal():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={"action": "reply", "intent": "calendar.list_slots", "tool_decision": "ok"},
        trace_entries=[{"stage": "booking"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=True,
        booking_progressed=False,
        allow_booking_stall=False,
        outbox_text=(
            "Свободные слоты: Айжан: 10:00, 11:00 | "
            "Алина: 12:00, 13:00"
        ),
        tool_signals={
            "calendar": {
                "intent": "calendar.list_slots",
                "tool_decision": "ok",
                "outcome": "success",
            }
        },
    )
    assert "booking_slot_stall" not in reasons


def test_booking_slot_stall_not_reported_for_explicit_pending_question_interaction_contract():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={
            "action": "reply",
            "pending_question_act": "slot_compare",
            "expected_reply_type": "time",
        },
        trace_entries=[
            {"stage": "pending_question_interaction", "pending_question_act": "slot_compare"},
            {"stage": "question_contract", "expected_reply_type": "time"},
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=True,
        booking_progressed=False,
        allow_booking_stall=False,
    )
    assert "booking_slot_stall" not in reasons


def test_booking_slot_stall_not_reported_for_ask_about_requested_slot_contract():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={
            "action": "reply",
            "pending_question_act": "ask_about_requested_slot",
            "expected_reply_type": "time",
        },
        trace_entries=[
            {
                "stage": "pending_question_interaction",
                "pending_question_act": "ask_about_requested_slot",
            },
            {"stage": "question_contract", "expected_reply_type": "time"},
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=True,
        booking_progressed=False,
        allow_booking_stall=False,
    )
    assert "booking_slot_stall" not in reasons


def test_booking_slot_stall_not_reported_for_temporal_scope_guidance_recovery():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={
            "action": "reply",
            "source": "booking_slot_guidance",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "expected_reply_type": "time",
            "policy_core_degrade_reason": "policy_validation:semantic_temporal_scope_missing",
            "policy_core_guard_recovery": "semantic_temporal_scope_missing_slot_guidance",
        },
        trace_entries=[
            {
                "stage": "policy_core_guard",
                "decision": "semantic_temporal_scope_missing_slot_guidance",
                "validation_error": "semantic_temporal_scope_missing",
            },
            {
                "stage": "pending_question_interaction",
                "decision": "booking_slot_guidance",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "booking_slot_guidance",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=True,
        booking_progressed=False,
        allow_booking_stall=False,
    )
    assert "booking_slot_stall" not in reasons


def test_booking_slot_stall_not_reported_for_slot_compare_guidance_recovery():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={
            "action": "reply",
            "source": "booking_slot_guidance",
            "pending_question_act": "slot_compare",
            "pending_question_target": "time",
            "expected_reply_type": "time",
            "policy_core_degrade_reason": "policy_validation:semantic_temporal_scope_missing",
            "policy_core_guard_recovery": "semantic_temporal_scope_missing_slot_guidance",
        },
        trace_entries=[
            {
                "stage": "policy_core_guard",
                "decision": "semantic_temporal_scope_missing_slot_guidance",
                "validation_error": "semantic_temporal_scope_missing",
            },
            {
                "stage": "pending_question_interaction",
                "decision": "booking_slot_guidance",
                "pending_question_act": "slot_compare",
                "pending_question_target": "time",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "booking_slot_guidance",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=True,
        booking_progressed=False,
        allow_booking_stall=False,
    )
    assert "booking_slot_stall" not in reasons


def test_booking_slot_stall_not_reported_for_slot_constraint_contract():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={
            "action": "booking_prompt",
            "source": "booking",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "pending_question_interaction": "slot_constraint",
            "expected_reply_type": "time",
        },
        trace_entries=[
            {
                "stage": "pending_question_interaction",
                "decision": "slot_constraint",
                "source": "question_contract",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "expected_reply_type": "time",
            },
            {
                "stage": "question_contract",
                "decision": "matched",
                "expected_reply_type": "time",
                "value": "в пятницу",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=True,
        booking_progressed=False,
        allow_booking_stall=False,
    )
    assert "booking_slot_stall" not in reasons


def test_booking_slot_stall_not_reported_for_tool_registry_missing_slot_pending_question():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={
            "action": "reply",
            "source": "tool_registry",
            "intent": "calendar.list_slots",
            "tool_action": "calendar.list_slots",
            "tool_decision": "missing_slot",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "pending_question_interaction": "ask_about_requested_slot",
            "expected_reply_type": "time",
        },
        trace_entries=[
            {
                "stage": "tool_registry",
                "decision": "missing_slot",
                "tool_action": "calendar.list_slots",
            },
            {
                "stage": "pending_question_interaction",
                "decision": "booking_slot_guidance",
                "source": "tool_registry",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "expected_reply_type": "time",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "llm_policy_core_tool",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=True,
        booking_progressed=False,
        allow_booking_stall=False,
    )
    assert "booking_slot_stall" not in reasons


def test_booking_slot_stall_not_reported_for_tool_registry_missing_slot_slot_compare():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={
            "action": "reply",
            "source": "tool_registry",
            "intent": "calendar.list_slots",
            "tool_action": "calendar.list_slots",
            "tool_decision": "missing_slot",
            "pending_question_act": "slot_compare",
            "pending_question_target": "time",
            "pending_question_interaction": "slot_compare",
            "expected_reply_type": "time",
        },
        trace_entries=[
            {
                "stage": "tool_registry",
                "decision": "missing_slot",
                "tool_action": "calendar.list_slots",
            },
            {
                "stage": "pending_question_interaction",
                "decision": "booking_slot_guidance",
                "source": "tool_registry",
                "pending_question_act": "slot_compare",
                "pending_question_target": "time",
                "expected_reply_type": "time",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "llm_policy_core_tool",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=True,
        booking_progressed=False,
        allow_booking_stall=False,
    )
    assert "booking_slot_stall" not in reasons


def test_booking_slot_stall_still_reported_without_pending_question_resume_contract():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={
            "action": "reply",
            "pending_question_act": "slot_compare",
        },
        trace_entries=[
            {"stage": "pending_question_interaction", "pending_question_act": "slot_compare"},
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=True,
        booking_progressed=False,
        allow_booking_stall=False,
    )
    assert "booking_slot_stall" in reasons


def test_expected_info_section_miss_not_reported_for_pending_escalation():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={"action": "escalate"},
        trace_entries=[{"stage": "policy_gate"}],
        state="pending",
        conv_meta={},
        handover_meta={"handover_id": "h-1"},
        bot_response=True,
        expected_response=False,
        expected_action=None,
        expected_info_sections=["promotions"],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
    )
    assert "expected_info_section_miss" not in reasons


def test_missing_bot_reply_marks_outbox_failed_reason():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={"action": "reply"},
        trace_entries=[{"stage": "booking"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=False,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_summary={"count": 1, "status": "FAILED"},
        outbox_payload_status="FAILED",
    )
    assert "missing_bot_reply" in reasons
    assert "outbox_delivery_failed" in reasons
    assert "unobserved_turn" not in reasons
    assert "outbox_delivery_timeout" not in reasons


def test_missing_bot_reply_uses_delivery_billing_waiver():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={"action": "reply", "delivery_error_code": "CHATFLOW_BILLING_BLOCKED"},
        trace_entries=[{"stage": "transport", "reason": "provider_billing_blocked"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=False,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_summary={"count": 1, "status": "FAILED"},
        outbox_payload_status="FAILED",
        outbox_payload={"error": {"code": "CHATFLOW_BILLING_BLOCKED"}},
    )
    assert "delivery_waiver_billing" in reasons
    assert "missing_bot_reply" not in reasons
    assert "outbox_delivery_failed" not in reasons
    assert "outbox_delivery_timeout" not in reasons


def test_missing_bot_reply_marks_outbox_timeout_reason():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={"action": "reply"},
        trace_entries=[{"stage": "booking"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=False,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_summary={"count": 1, "status": "PROCESSING"},
        outbox_payload_status="PROCESSING",
    )
    assert "missing_bot_reply" in reasons
    assert "outbox_delivery_timeout" in reasons
    assert "outbox_delivery_failed" not in reasons


def test_missing_bot_reply_suppressed_on_infra_webhook_error():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={"action": "reply"},
        trace_entries=[{"stage": "booking"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=False,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        webhook_error="timeout while posting webhook",
    )
    assert "missing_bot_reply" not in reasons
    assert "outbox_delivery_failed" not in reasons
    assert "outbox_delivery_timeout" not in reasons


def test_dry_run_contract_marks_missing_bot_reply_for_expected_turn():
    apply_contract = _load_dry_run_contract_helper()
    reasons = apply_contract(
        [],
        dry_run=True,
        expected_response=True,
        bot_response=False,
    )

    assert "missing_bot_reply" in reasons


def test_dry_run_contract_keeps_existing_reasons_without_duplicate_missing_reply():
    apply_contract = _load_dry_run_contract_helper()
    reasons = apply_contract(
        ["missing_bot_reply", "judge_fail"],
        dry_run=True,
        expected_response=True,
        bot_response=False,
    )

    assert reasons.count("missing_bot_reply") == 1
    assert "judge_fail" in reasons


def test_dry_run_contract_is_noop_when_not_dry_run():
    apply_contract = _load_dry_run_contract_helper()
    reasons = apply_contract(
        ["judge_fail"],
        dry_run=False,
        expected_response=True,
        bot_response=False,
    )

    assert reasons == ["judge_fail"]


def test_duplicate_ack_detector_handles_nested_string_payload():
    helpers = _load_duplicate_ack_helpers()
    fn = helpers["_llm_quality_payload_is_duplicate_ack"]
    payload = {
        "success": True,
        "response": json.dumps({"message": "Duplicate message_id detected"}),
    }
    assert fn(payload) is True


def test_duplicate_ack_infers_bot_response_for_reply_action():
    helpers = _load_duplicate_ack_helpers()
    fn = helpers["_llm_quality_should_infer_bot_response_from_duplicate_ack"]
    assert fn(
        bot_response=False,
        expected_response=True,
        response_payload={"message": "duplicate message_id"},
        attempts=2,
        meta={"action": "reply"},
        meta_error=None,
        state="bot_active",
    )


def test_duplicate_ack_does_not_infer_for_pending_actions():
    helpers = _load_duplicate_ack_helpers()
    fn = helpers["_llm_quality_should_infer_bot_response_from_duplicate_ack"]
    assert not fn(
        bot_response=False,
        expected_response=True,
        response_payload={"message": "duplicate message_id"},
        attempts=2,
        meta={"action": "booking_captured_pending"},
        meta_error=None,
        state="pending",
    )


def test_duplicate_ack_does_not_infer_when_outbox_failed():
    helpers = _load_duplicate_ack_helpers()
    fn = helpers["_llm_quality_should_infer_bot_response_from_duplicate_ack"]
    assert not fn(
        bot_response=False,
        expected_response=True,
        response_payload={"message": "duplicate message_id"},
        attempts=2,
        meta={"action": "reply", "delivery_error_code": "CHATFLOW_BILLING_BLOCKED"},
        meta_error=None,
        state="bot_active",
        outbox_payload_status="FAILED",
        outbox_summary={"count": 1, "status": "FAILED"},
    )


def test_duplicate_ack_does_not_infer_when_transport_trace_is_billing_blocked():
    helpers = _load_duplicate_ack_helpers()
    fn = helpers["_llm_quality_should_infer_bot_response_from_duplicate_ack"]
    assert not fn(
        bot_response=False,
        expected_response=True,
        response_payload={"message": "duplicate message_id"},
        attempts=2,
        meta={"action": "reply"},
        meta_error=None,
        state="bot_active",
        trace_entries=[{"stage": "transport", "reason": "provider_billing_blocked"}],
    )


def test_duplicate_ack_infers_when_skip_outbox_ignores_transport_trace_block():
    helpers = _load_duplicate_ack_helpers()
    fn = helpers["_llm_quality_should_infer_bot_response_from_duplicate_ack"]
    assert fn(
        bot_response=False,
        expected_response=True,
        response_payload={"message": "duplicate message_id"},
        attempts=2,
        meta={"action": "reply"},
        meta_error=None,
        state="bot_active",
        trace_entries=[{"stage": "transport", "reason": "provider_billing_blocked"}],
        ignore_transport_block=True,
    )


def test_message_recovery_helper_returns_assistant_text():
    helpers = _load_message_recovery_helper()
    fn = helpers["_llm_quality_fetch_assistant_reply_from_messages"]
    captured = {}

    def _run_psql_query(_db_user, query):
        captured["query"] = query
        return json.dumps({"content": "  Отлично, время подходит. Как вас зовут?  "}), None

    helpers["_run_psql_query"] = _run_psql_query
    text, error = fn(
        "postgres",
        "conv-id",
        "msg-id",
        window_seconds=30,
    )

    assert error is None
    assert text == "Отлично, время подходит. Как вас зовут?"
    assert "interval '30 seconds'" in captured["query"]


def test_message_recovery_helper_clamps_window_and_handles_empty_payload():
    helpers = _load_message_recovery_helper()
    fn = helpers["_llm_quality_fetch_assistant_reply_from_messages"]
    captured = {}

    def _run_psql_query(_db_user, query):
        captured["query"] = query
        return "{}", None

    helpers["_run_psql_query"] = _run_psql_query
    text, error = fn(
        "postgres",
        "conv-id",
        "msg-id",
        window_seconds=999,
    )

    assert error is None
    assert text is None
    assert "interval '180 seconds'" in captured["query"]


def test_false_booking_confirmation_is_reported_without_calendar_proof():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={"action": "reply"},
        trace_entries=[{"stage": "booking"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Вы записаны на завтра в 18:30.",
        tool_signals={},
    )
    assert "false_booking_confirmation" in reasons


def test_calendar_contract_miss_reported_when_appointment_has_no_calendar_success():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={"action": "booking_escalated", "appointment_id": "apt-1", "appointment_status": "PENDING_CONFIRMATION"},
        trace_entries=[{"stage": "booking_commit"}],
        state="pending",
        conv_meta={},
        handover_meta={"handover_id": "h-1"},
        bot_response=True,
        expected_response=False,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Передал менеджеру.",
        tool_signals={"calendar": {"outcome": "pending"}},
    )
    assert "calendar_tool_contract_miss" in reasons


def test_calendar_contract_passes_when_calendar_success_present():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={"action": "booking_escalated", "appointment_id": "apt-1", "appointment_status": "PENDING_CONFIRMATION"},
        trace_entries=[{"stage": "booking_commit"}],
        state="pending",
        conv_meta={},
        handover_meta={"handover_id": "h-1"},
        bot_response=True,
        expected_response=False,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Передал менеджеру.",
        tool_signals={"calendar": {"outcome": "success"}},
    )
    assert "calendar_tool_contract_miss" not in reasons


def test_calendar_contract_miss_not_reported_for_slot_lookup_provider_unavailable():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={"action": "reply", "intent": "calendar.list_slots", "tool_decision": "provider_unavailable"},
        trace_entries=[{"stage": "booking"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=True,
        booking_progressed=False,
        allow_booking_stall=True,
        outbox_text="Сейчас календарь недоступен. Напишите удобное время, и мы уточним.",
        tool_signals={"calendar": {"outcome": "failure"}},
    )
    assert "calendar_tool_contract_miss" not in reasons


def test_calendar_contract_miss_reported_for_get_booking_without_success():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={"action": "reply", "intent": "calendar.get_booking", "tool_decision": "provider_unavailable"},
        trace_entries=[{"stage": "booking"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Не вижу активной записи. Уточните номер телефона и дату/время.",
        tool_signals={"calendar": {"outcome": "failure"}},
    )
    assert "calendar_tool_contract_miss" in reasons


def test_calendar_outcome_not_found_not_forced_to_failure_by_booking_blocked_reason():
    resolve_outcome = _load_calendar_outcome_helper()
    outcome = resolve_outcome(
        appointment_id=None,
        appointment_status=None,
        blocked_reason="intent_decomp_missing",
        tool_decision="not_found",
    )
    assert outcome == "success"


def test_calendar_outcome_without_decision_keeps_blocked_reason_failure():
    resolve_outcome = _load_calendar_outcome_helper()
    outcome = resolve_outcome(
        appointment_id=None,
        appointment_status=None,
        blocked_reason="intent_signal",
        tool_decision=None,
    )
    assert outcome == "failure"


def test_calendar_contract_miss_not_reported_for_slot_confirmation_prompt_without_calendar_outcome():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={"action": "booking_confirm", "intent": "booking", "slot_confirmation_required": True},
        trace_entries=[{"stage": "booking_confirm", "decision": "prompt"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=True,
        booking_progressed=True,
        allow_booking_stall=False,
        outbox_text="Я понял дату и время: 18:30. Верно?",
        tool_signals={"confirm": {"required": True, "outcome": "pending"}},
    )
    assert "calendar_tool_contract_miss" not in reasons


def test_calendar_contract_miss_reported_for_booking_confirm_without_slot_confirmation_flag():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={"action": "booking_confirm", "intent": "booking", "slot_confirmation_required": False},
        trace_entries=[{"stage": "booking_confirm", "decision": "confirmed"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=True,
        booking_progressed=True,
        allow_booking_stall=False,
        outbox_text="Подтвердите, пожалуйста, запись.",
        tool_signals={"confirm": {"required": True, "outcome": "success"}},
    )
    assert "calendar_tool_contract_miss" in reasons


def test_calendar_contract_miss_not_reported_for_booking_verification_handoff_in_pending():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={
            "action": "escalate",
            "intent": "check_booking",
            "source": "booking_verification",
        },
        trace_entries=[{"stage": "booking_verification"}],
        state="pending",
        conv_meta={},
        handover_meta={"handover_id": "h-1"},
        bot_response=True,
        expected_response=False,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Передал менеджеру.",
        tool_signals={"calendar": {"outcome": "pending"}},
    )
    assert "calendar_tool_contract_miss" not in reasons


def test_calendar_contract_miss_not_reported_for_capability_blocked_handoff():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={
            "action": "escalate",
            "intent": "check_booking",
            "source": "tool_registry",
            "tool_action": "calendar.get_booking",
            "tool_decision": "capability_blocked",
        },
        trace_entries=[{"stage": "tool_registry", "decision": "capability_blocked"}],
        state="pending",
        conv_meta={},
        handover_meta={"handover_id": "h-2"},
        bot_response=True,
        expected_response=False,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Передал менеджеру для ручной проверки записи.",
        tool_signals={"calendar": {"outcome": "blocked"}},
    )
    assert "calendar_tool_contract_miss" not in reasons


def test_calendar_contract_miss_not_reported_for_check_booking_prompt():
    evaluate_turn = _load_evaluate_turn()
    reasons = evaluate_turn(
        meta={
            "action": "check_booking_prompt",
            "intent": "check_booking",
            "source": "llm_policy_core",
        },
        trace_entries=[{"stage": "llm_policy_core"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Чтобы проверить запись, подскажите номер телефона и дату.",
        tool_signals={"calendar": {"outcome": "pending"}},
    )
    assert "calendar_tool_contract_miss" not in reasons


def test_state_fallback_allows_pending_when_expected_bot_active():
    helpers = _load_expectation_helpers()
    fn = helpers["_llm_quality_state_matches_expected"]
    assert fn(
        "bot_active",
        "pending",
        {"action": "escalate"},
        {},
        {},
    )


def test_action_fallback_allows_booking_escalated_vs_booking_prompt():
    helpers = _load_expectation_helpers()
    fn = helpers["_llm_quality_action_matches_expected"]
    assert fn(
        ["booking_escalated"],
        {"action": "booking_prompt"},
        {},
        [],
        [],
        None,
    )


def test_expected_reply_fallback_allows_pending_transition():
    helpers = _load_expectation_helpers()
    fn = helpers["_llm_quality_expected_reply_matches"]
    assert fn(
        expected_reply=True,
        expected_response=False,
        expected_reply_type="time",
        expected_state="bot_active",
        state="pending",
        meta={"action": "escalate"},
        conv_meta={},
        handover_meta={},
    )


def test_expected_reply_fallback_allows_manager_active_booking_escalated():
    helpers = _load_expectation_helpers()
    fn = helpers["_llm_quality_expected_reply_matches"]
    assert fn(
        expected_reply=True,
        expected_response=False,
        expected_reply_type="time",
        expected_state="bot_active",
        state="manager_active",
        meta={"action": "booking_escalated"},
        conv_meta={},
        handover_meta={},
    )


def test_expected_reply_fallback_allows_pending_provider_unavailable_booking_reply():
    helpers = _load_expectation_helpers()
    fn = helpers["_llm_quality_expected_reply_matches"]
    assert fn(
        expected_reply=True,
        expected_response=False,
        expected_reply_type="time",
        expected_state="pending",
        state="pending",
        meta={"action": "reply", "tool_decision": "provider_unavailable"},
        conv_meta={},
        handover_meta={},
    )


def test_expected_reply_fallback_allows_pending_booking_prompt():
    helpers = _load_expectation_helpers()
    fn = helpers["_llm_quality_expected_reply_matches"]
    assert fn(
        expected_reply=True,
        expected_response=False,
        expected_reply_type="time",
        expected_state=None,
        state="pending",
        meta={"action": "booking_prompt"},
        conv_meta={},
        handover_meta={},
    )


def test_expected_reply_fallback_allows_pending_info_reply():
    helpers = _load_expectation_helpers()
    fn = helpers["_llm_quality_expected_reply_matches"]
    assert fn(
        expected_reply=True,
        expected_response=False,
        expected_reply_type=None,
        expected_state="bot_active",
        state="pending",
        meta={"action": "reply", "intent": "catalog.location", "tool_decision": "ok"},
        conv_meta={},
        handover_meta={"status": "active"},
    )


def test_evaluate_turn_allows_contract_cleared_expected_reply_mismatch():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "calendar.reschedule",
            "tool_action": "calendar.reschedule",
            "tool_decision": "ok",
            "expected_reply_contract_clear": True,
            "expected_reply_contract_reason": "calendar_reschedule_resolved",
        },
        trace_entries=[{"stage": "tool_registry"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="name",
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=False,
        allow_booking_stall=False,
        outbox_text="Перенос оформлен. Менеджер подтвердит новое время.",
    )

    assert "expected_reply_type_mismatch" not in reasons


def test_evaluate_turn_allows_calendar_list_slots_without_expected_reply_type():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "calendar.list_slots",
            "tool_action": "calendar.list_slots",
            "tool_decision": "ok",
        },
        trace_entries=[{"stage": "tool_registry"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="service_choice",
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=False,
        allow_booking_stall=False,
        outbox_text="Свободные слоты: Айгерим Болатова: 10:00, 11:00.",
        tool_signals={"calendar": {"outcome": "success"}},
    )

    assert "expected_reply_type_mismatch" not in reasons


def test_evaluate_turn_flags_slot_date_resolution_miss():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "calendar.list_slots",
            "tool_action": "calendar.list_slots",
            "tool_decision": "missing_slot",
            "slot_contract_error": "slot_date_resolution_miss",
        },
        trace_entries=[{"stage": "tool_registry"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="На какую дату и время вам удобно?",
        tool_signals={"calendar": {"outcome": "pending"}},
    )

    assert "slot_date_resolution_miss" in reasons


def test_evaluate_turn_flags_slot_availability_contradiction():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "calendar.list_slots",
            "tool_action": "calendar.list_slots",
            "tool_decision": "ok",
            "availability_claim": "yes",
            "requested_time": "19:00",
            "available_slots_by_specialist": {"Айгерим": ["10:00", "11:00"]},
        },
        trace_entries=[{"stage": "tool_registry"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text=(
            "Да, на 19:00 есть свободное окно. "
            "Свободные слоты: Айгерим: 10:00, 11:00"
        ),
        tool_signals={"calendar": {"outcome": "success"}},
    )

    assert "slot_availability_contradiction" in reasons


def test_evaluate_turn_flags_fabricated_conflict_time():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "calendar.book_slot",
            "tool_action": "calendar.book_slot",
            "tool_decision": "conflict",
            "requested_time": None,
        },
        trace_entries=[{"stage": "tool_registry"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="На 00:00 свободного окна нет. Доступны: 10:00, 11:00.",
        tool_signals={"calendar": {"outcome": "pending"}},
    )

    assert "fabricated_conflict_time" in reasons


def test_evaluate_turn_flags_booking_transition_evidence_missing():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "calendar.book_slot",
            "tool_action": "calendar.book_slot",
            "tool_decision": "ok",
            "appointment_id": "apt-1",
        },
        trace_entries=[{"stage": "tool_registry", "decision": "ok"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Запись подтверждена.",
        tool_signals={"calendar": {"outcome": "success"}},
    )

    assert "booking_transition_evidence_missing" in reasons


def test_evaluate_turn_allows_booking_transition_evidence_when_present():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "calendar.book_slot",
            "tool_action": "calendar.book_slot",
            "tool_decision": "ok",
            "appointment_id": "apt-1",
            "transition_owner": "booking_profile_single_writer_v1",
            "user_phone_source_for_tool": "remote_jid",
            "profile_sync": {
                "applied": True,
                "name_synced": True,
                "phone_synced": True,
                "phone_source": "remote_jid",
                "phone_available": True,
            },
        },
        trace_entries=[{"stage": "tool_registry", "decision": "ok"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Запись подтверждена.",
        tool_signals={"calendar": {"outcome": "success"}},
    )

    assert "booking_transition_evidence_missing" not in reasons


def test_evaluate_turn_allows_booking_commit_with_profile_name_and_remote_jid_phone_sources():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "calendar.book_slot",
            "tool_action": "calendar.book_slot",
            "tool_decision": "ok",
            "appointment_id": "apt-1",
            "transition_owner": "booking_profile_single_writer_v1",
            "customer_name_source": "user_profile",
            "customer_phone_source": "remote_jid",
            "user_phone_source_for_tool": "remote_jid",
            "profile_sync": {
                "applied": True,
                "name_synced": False,
                "phone_synced": True,
                "phone_source": "remote_jid",
                "phone_available": True,
            },
            "tool_args": {
                "service_query": "Маникюр",
                "start_at": "2026-03-08T15:00:00+05:00",
            },
            "slots": {
                "service": "Маникюр",
                "datetime": "завтра 15:00",
            },
        },
        trace_entries=[{"stage": "tool_registry", "decision": "ok"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Заявка на запись принята. Менеджер подтвердит время.",
        tool_signals={"calendar": {"outcome": "success"}},
    )

    assert "booking_commit_without_required_contact" not in reasons


def test_evaluate_turn_flags_booking_commit_without_required_contact():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "calendar.book_slot",
            "tool_action": "calendar.book_slot",
            "tool_decision": "ok",
            "appointment_id": "apt-1",
            "transition_owner": "booking_profile_single_writer_v1",
            "user_phone_source_for_tool": "missing",
            "profile_sync": {
                "applied": False,
                "name_synced": False,
                "phone_synced": False,
                "phone_source": "missing",
                "phone_available": False,
            },
            "tool_args": {},
            "slots": {},
        },
        trace_entries=[{"stage": "tool_registry", "decision": "ok"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Запись подтверждена.",
        tool_signals={"calendar": {"outcome": "success"}},
    )

    assert "booking_commit_without_required_contact" in reasons


def test_evaluate_turn_flags_fact_without_evidence_and_irrelevant_fact():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "location",
            "source": "truth_gate",
            "tool_action": "catalog.location",
            "tool_decision": "ok",
        },
        trace_entries=[{"stage": "truth_gate", "decision": "reply"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=["hours"],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=["hours"],
        info_answered={"hours": False},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Мы находимся на Абая, 10.",
        tool_signals={},
    )

    assert "fact_without_evidence" in reasons
    assert "irrelevant_fact" in reasons


def test_evaluate_turn_does_not_flag_fact_without_evidence_for_service_clarify_collect():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "service_clarify",
            "source": "llm_policy_core",
            "expected_reply_type": "service_choice",
            "expected_reply_reason": "llm_policy_core_collect",
        },
        trace_entries=[
            {
                "stage": "question_contract",
                "decision": "llm_policy_core_collect",
                "missing_slot": "service",
            }
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="service_choice",
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="service_choice",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Уточните, пожалуйста, какая именно услуга интересует (маникюр, педикюр или ресницы)?",
        tool_signals={},
    )

    assert "fact_without_evidence" not in reasons


def test_evaluate_turn_does_not_flag_fact_without_evidence_for_timeout_pending_slot_guidance():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "booking",
            "source": "booking_slot_guidance",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "pending_question_interaction": "ask_about_requested_slot",
            "pending_question_owner": "booking_slot_guidance",
            "expected_reply_type": "time",
            "expected_reply_reason": "booking_slot_guidance",
            "policy_core_guard_recovery": "timeout_pending_slot_question",
            "policy_core_timeout_retry_path": "booking_slot_guidance",
        },
        trace_entries=[
            {
                "stage": "policy_core_guard",
                "decision": "timeout_pending_slot_question",
                "reason": "policy_error:timeout",
            },
            {
                "stage": "pending_question_interaction",
                "decision": "booking_slot_guidance",
                "recovery": "timeout_pending_slot_question",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "booking_slot_guidance",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Могу помочь подобрать свободное время. На какую дату и время вам удобно?",
        tool_signals={},
    )

    assert "fact_without_evidence" not in reasons


def test_evaluate_turn_accepts_timeout_pending_slot_guidance_after_hours_info_lock():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "booking",
            "source": "booking_slot_guidance",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "pending_question_interaction": "ask_about_requested_slot",
            "pending_question_owner": "booking_slot_guidance",
            "expected_reply_type": "time",
            "expected_reply_reason": "booking_slot_guidance",
            "expected_reply_blocked_by_info": True,
            "policy_core_guard_recovery": "timeout_pending_slot_question",
            "policy_core_timeout_retry_path": "booking_slot_guidance",
            "timeout_slot_question_info_lock_surface": True,
            "suppressed_info_intents": ["hours"],
        },
        trace_entries=[
            {
                "stage": "policy_core_guard",
                "decision": "suppress_time_preference_info_signal",
                "suppression_surfaces": ["timeout_slot_question_info_lock_surface"],
                "suppressed_info_intents": ["hours"],
            },
            {
                "stage": "policy_core_guard",
                "decision": "timeout_pending_slot_question",
                "reason": "policy_error:timeout",
            },
            {
                "stage": "pending_question_interaction",
                "decision": "booking_slot_guidance",
                "recovery": "timeout_pending_slot_question",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "booking_slot_guidance",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Могу помочь подобрать свободное время. На какую дату и время вам удобно?",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "source": ["booking_slot_guidance"],
            "pending_question_act": ["ask_about_requested_slot"],
            "pending_question_target": ["time"],
            "pending_question_interaction": ["ask_about_requested_slot"],
            "expected_reply_reason": ["booking_slot_guidance"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "pending_question_interaction",
                "decision": "booking_slot_guidance",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "booking_slot_guidance",
            },
        ],
    )

    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons
    assert "fact_without_evidence" not in reasons


def test_evaluate_turn_accepts_timeout_booking_slot_fill_followup():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "policy_core_guard",
            "expected_reply_type": "time",
            "expected_reply_reason": "policy_core_timeout_booking_slot_fill_followup",
            "policy_core_guard_recovery": "timeout_booking_slot_fill_followup",
            "policy_core_timeout_retry_path": "booking_slot_fill_followup",
            "booking_slot_fill_applied": ["name"],
        },
        trace_entries=[
            {
                "stage": "policy_core_guard",
                "decision": "timeout_booking_slot_fill_followup",
                "reason": "policy_error:timeout",
                "missing_slot": "datetime",
                "filled_slots": ["name"],
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "policy_core_timeout_booking_slot_fill_followup",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Понял, в субботу по услуге «Маникюр». Подскажите, пожалуйста, точное время.",
        tool_signals={},
    )

    assert "fact_without_evidence" not in reasons
    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_accepts_timeout_owner_boundary_collect():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "policy_core_guard",
            "expected_reply_type": "time",
            "expected_reply_reason": "policy_core_timeout_owner_boundary",
            "policy_core_guard_recovery": "timeout_owner_boundary_collect",
            "policy_core_timeout_retry_path": "booking_owner_boundary_collect",
            "timeout_owner_boundary_source": "matched_expected_reply",
            "booking_slot_fill_applied": ["name"],
            "owner_resolution_reason_code": "timeout_owner_boundary_matched_expected_reply",
        },
        trace_entries=[
            {
                "stage": "owner_resolver",
                "decision": "timeout_owner_boundary_match",
                "reason_code": "timeout_owner_boundary_matched_expected_reply",
                "source": "matched_expected_reply",
            },
            {
                "stage": "policy_core_guard",
                "decision": "timeout_owner_boundary_collect",
                "reason": "policy_error:timeout",
                "missing_slot": "datetime",
                "filled_slots": ["name"],
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "policy_core_timeout_owner_boundary",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Понял, завтра по услуге «Маникюр». Подскажите, пожалуйста, точное время.",
        tool_signals={},
    )

    assert "fact_without_evidence" not in reasons
    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_accepts_timeout_owner_boundary_slot_constraint_collect():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "policy_core_guard",
            "expected_reply_type": "time",
            "expected_reply_reason": "policy_core_timeout_owner_boundary",
            "policy_core_guard_recovery": "timeout_owner_boundary_collect",
            "policy_core_timeout_retry_path": "booking_owner_boundary_collect",
            "timeout_owner_boundary_source": "matched_expected_reply",
            "booking_slot_fill_applied": ["datetime"],
            "owner_resolution_reason_code": "timeout_owner_boundary_matched_expected_reply",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "pending_question_interaction": "slot_constraint",
            "pending_question_owner": "question_contract",
        },
        trace_entries=[
            {
                "stage": "question_contract",
                "decision": "matched",
                "answer_slot": "datetime",
                "answer_value": "во вторник",
                "expected_reply_type": "time",
            },
            {
                "stage": "owner_resolver",
                "decision": "timeout_owner_boundary_match",
                "reason_code": "timeout_owner_boundary_matched_expected_reply",
                "source": "matched_expected_reply",
            },
            {
                "stage": "policy_core_guard",
                "decision": "timeout_owner_boundary_collect",
                "reason": "policy_error:timeout",
                "missing_slot": "datetime",
                "filled_slots": ["datetime"],
            },
            {
                "stage": "pending_question_interaction",
                "decision": "slot_constraint",
                "source": "question_contract",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "expected_reply_type": "time",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "policy_core_timeout_owner_boundary",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Понял, во вторник по услуге «Маникюр». Подскажите, пожалуйста, точное время.",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "pending_question_act": ["slot_constraint"],
            "pending_question_target": ["time"],
            "expected_reply_type": ["time"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "pending_question_interaction",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
            },
            {
                "stage": "question_contract",
                "expected_reply_type": "time",
            },
        ],
    )

    assert "fact_without_evidence" not in reasons
    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_accepts_timeout_resume_contract_boundary_collect():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "policy_core_guard",
            "expected_reply_type": "time",
            "expected_reply_reason": "policy_core_timeout_owner_boundary",
            "policy_core_guard_recovery": "timeout_owner_boundary_collect",
            "policy_core_timeout_retry_path": "booking_resume_collect_boundary",
            "timeout_owner_boundary_source": "resume_contract",
            "owner_resolution_reason_code": "timeout_owner_boundary_resume_contract",
        },
        trace_entries=[
            {
                "stage": "owner_resolver",
                "decision": "timeout_owner_boundary_match",
                "reason_code": "timeout_owner_boundary_resume_contract",
                "source": "resume_contract",
            },
            {
                "stage": "boundary_state",
                "decision": "resume_collect",
                "source": "booking_interrupt",
                "missing_slot": "datetime",
            },
            {
                "stage": "policy_core_guard",
                "decision": "timeout_owner_boundary_collect",
                "reason": "policy_error:timeout",
                "missing_slot": "datetime",
                "filled_slots": [],
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "policy_core_timeout_owner_boundary",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="На какую дату и время вам удобно?",
        tool_signals={},
    )

    assert "fact_without_evidence" not in reasons
    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_flags_booking_prompt_leak():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "catalog.service_query",
            "tool_action": "catalog.service_query",
            "tool_decision": "duration",
        },
        trace_entries=[{"stage": "tool_registry"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Стрижка занимает 30 минут.\n\nОтлично, время подходит. Как вас зовут?",
        tool_signals={},
    )

    assert "booking_prompt_leak" in reasons


def test_evaluate_turn_does_not_flag_booking_prompt_leak_for_services_overview():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "catalog.service_query",
            "tool_action": "catalog.service_query",
            "tool_decision": "services_overview",
        },
        trace_entries=[{"stage": "tool_registry"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text=(
            "Мы салон красоты: парикмахерские услуги, маникюр и педикюр.\n\n"
            "На какую услугу хотите записаться?"
        ),
        tool_signals={},
    )

    assert "booking_prompt_leak" not in reasons


def test_evaluate_turn_does_not_flag_booking_prompt_leak_for_missing_slot_collect():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "catalog.service_query",
            "tool_action": "catalog.service_query",
            "tool_decision": "missing_slot",
        },
        trace_entries=[{"stage": "tool_registry"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text=(
            "На какую услугу хотите записаться? После этого сразу проверю свободное время."
        ),
        tool_signals={},
    )

    assert "booking_prompt_leak" not in reasons


def test_evaluate_turn_does_not_flag_mix_info_booking_for_service_query_missing_slot():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "catalog.service_query",
            "tool_action": "catalog.service_query",
            "tool_decision": "missing_slot",
            "expected_reply_type": "service_choice",
            "expected_reply_reason": "llm_policy_core_tool",
        },
        trace_entries=[{"stage": "tool_registry"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="На какую услугу хотите записаться? После этого сразу проверю свободное время.",
        tool_signals={},
    )

    assert "mix_info_booking" not in reasons


def test_evaluate_turn_allows_service_choice_info_fallback_for_missing_slot():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "catalog.service_query",
            "tool_action": "catalog.service_query",
            "tool_decision": "missing_slot",
            "expected_reply_type": "service_choice",
        },
        trace_entries=[{"stage": "tool_registry"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=["master", "specialist", "service_duration"],
        expected_reply_type="service_choice",
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="service_choice",
        info_tags=["master"],
        info_answered={"master": False, "specialist": False, "service_duration": False},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="На какую услугу хотите записаться? После этого сразу проверю свободное время.",
        tool_signals={},
    )

    assert "expected_info_section_miss" not in reasons
    assert "info_section_miss" not in reasons


def test_evaluate_turn_allows_master_query_missing_subject_service_clarify_fallback():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "service_clarify",
            "source": "llm_policy_core",
            "expected_reply_type": "service_choice",
            "llm_policy_core": {
                "intent": "master_query",
                "subject_kind": "specialist",
                "resolution_mode": "clarify_missing_subject",
                "next_question": "service",
                "open_questions": ["service"],
                "payload": {
                    "intent": "master_query",
                    "subject_kind": "specialist",
                    "resolution_mode": "clarify_missing_subject",
                    "next_question": "service",
                    "open_questions": ["service"],
                },
            },
        },
        trace_entries=[
            {
                "stage": "llm_policy_core",
                "intent": "master_query",
                "subject_kind": "specialist",
                "resolution_mode": "clarify_missing_subject",
                "next_question": "service",
            },
            {
                "stage": "question_contract",
                "decision": "llm_policy_core_collect",
                "missing_slot": "service",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=["master", "specialist"],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="service_choice",
        info_tags=["master"],
        info_answered={"master": False, "specialist": False},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Уточните, пожалуйста, какая именно услуга интересует?",
        tool_signals={},
    )

    assert "expected_info_section_miss" not in reasons
    assert "info_section_miss" not in reasons


def test_evaluate_turn_allows_pricing_service_clarify_fallback_under_booking_interrupt():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "service_clarify",
            "source": "llm_policy_core",
            "expected_reply_type": "service_choice",
            "llm_policy_core": {
                "intent": "info",
                "capability": "pricing",
                "resolution_mode": "clarify_missing_time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "payload": {
                    "intent": "info",
                    "capability": "pricing",
                    "resolution_mode": "clarify_missing_time",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                },
            },
            "info_sections": ["pricing"],
            "policy_collect_interrupt_guard_deferred": True,
            "policy_collect_interrupt_guard_info_sections": ["pricing"],
        },
        trace_entries=[
            {
                "stage": "policy_interrupt_contract",
                "decision": "defer_slot_order_guard",
                "missing_slot": "service",
                "requested_slot": "datetime",
                "info_sections": ["pricing"],
            },
            {
                "stage": "policy_interrupt_contract",
                "decision": "semantic_override_blocked",
                "reason_code": "policy_collect_info_interrupt_owner",
                "info_sections": ["pricing"],
            },
            {
                "stage": "question_contract",
                "decision": "llm_policy_core_collect",
                "missing_slot": "service",
                "info_sections": ["pricing"],
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=["pricing"],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="service_choice",
        info_tags=["price"],
        info_answered={"pricing": False},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Уточните, пожалуйста, какая именно услуга интересует?",
        tool_signals={},
    )

    assert "expected_info_section_miss" not in reasons
    assert "info_section_miss" not in reasons


def test_evaluate_turn_flags_requested_date_time_like():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "calendar.list_slots",
            "tool_action": "calendar.list_slots",
            "tool_decision": "ok",
            "requested_date": "16:30",
        },
        trace_entries=[{"stage": "tool_registry"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="На 16:30 свободного окна нет. Доступны: 17:00, 18:00.",
        tool_signals={"calendar": {"outcome": "success"}},
    )

    assert "requested_date_time_like" in reasons


def test_evaluate_turn_flags_stale_booking_carryover():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "discounts",
            "source": "policy_pack",
            "tool_decision": "ok",
        },
        trace_entries=[{"stage": "policy_gate"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="name",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text=(
            "Ещё был вопрос по записи. Уточните, пожалуйста.\n\n"
            "Официальные акции: ..."
        ),
        tool_signals={},
    )

    assert "stale_booking_carryover" in reasons
    assert "stale_state_leak" in reasons


def test_canonical_state_projection_evidence_required_for_service_referent():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "pricing",
            "source": "policy_pack",
            "tool_decision": "ok",
            "service_query": "маникюр",
            "service_query_source": "context",
        },
        trace_entries=[
            {
                "stage": "service_carryover",
                "decision": "used",
                "service_query": "маникюр",
                "service_query_source": "context",
            }
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Маникюр стоит 3000 тг.",
        tool_signals={},
    )

    assert "canonical_projection_evidence_missing" in reasons
    assert "stale_state_leak" in reasons


def test_evaluate_turn_allows_canonical_state_projection_evidence():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "pricing",
            "source": "policy_pack",
            "tool_decision": "ok",
            "service_query": "маникюр",
            "service_query_source": "context",
            "projection_source": "canonical_dialog_state",
            "canonical_state_owner": "context_manager.dialog_state.v1",
        },
        trace_entries=[
            {
                "stage": "service_carryover",
                "decision": "used",
                "service_query": "маникюр",
                "service_query_source": "context",
                "projection_source": "canonical_dialog_state",
                "canonical_state_owner": "context_manager.dialog_state.v1",
            }
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Маникюр стоит 3000 тг.",
        tool_signals={},
    )

    assert "canonical_projection_evidence_missing" not in reasons


def test_weekend_availability_requires_resolved_referent_trace():
    evaluate = _load_evaluate_turn()

    base_kwargs = dict(
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=["hours"],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={"hours": True},
        booking_active=False,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Работаем ежедневно, без выходных с 9:00 до 21:00.",
        tool_signals={},
    )

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "hours",
            "source": "llm_policy_core",
            "subject_kind": "service",
            "capability": "hours",
            "temporal_scope": "weekend",
            "resolution_mode": "referent_followup",
            "capability_resolution_mode": "policy_fact",
            "projection_source": "canonical_dialog_state",
            "canonical_state_owner": "context_manager.dialog_state.v1",
        },
        trace_entries=[
            {
                "stage": "service_carryover",
                "decision": "used",
                "service_query": "маникюр",
                "service_query_source": "consult_context",
                "projection_source": "canonical_dialog_state",
                "canonical_state_owner": "context_manager.dialog_state.v1",
            }
        ],
        **base_kwargs,
    )

    assert "resolved_referent_trace_missing" in reasons

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "hours",
            "source": "llm_policy_core",
            "subject_kind": "service",
            "capability": "hours",
            "temporal_scope": "weekend",
            "resolution_mode": "referent_followup",
            "capability_resolution_mode": "policy_fact",
            "resolved_referent": "маникюр",
            "referent_source": "consult_context",
            "projection_source": "canonical_dialog_state",
            "canonical_state_owner": "context_manager.dialog_state.v1",
        },
        trace_entries=[
            {
                "stage": "referent_resolver",
                "decision": "resolved",
                "subject_kind": "service",
                "capability": "hours",
                "temporal_scope": "weekend",
                "resolution_mode": "referent_followup",
                "capability_resolution_mode": "policy_fact",
                "resolved_referent": "маникюр",
                "referent_source": "consult_context",
                "projection_source": "canonical_dialog_state",
                "canonical_state_owner": "context_manager.dialog_state.v1",
            }
        ],
        **base_kwargs,
    )

    assert "resolved_referent_trace_missing" not in reasons


def test_policy_core_guard_referent_followup_booking_prompt_requires_referent_trace():
    evaluate = _load_evaluate_turn()

    base_kwargs = dict(
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type=None,
        expected_state=None,
        expected_reply=None,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=True,
        booking_progressed=False,
        allow_booking_stall=False,
        outbox_text="На какую дату и время вам удобно?",
        tool_signals={},
    )

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "policy_core_guard",
            "subject_kind": "service",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "resolution_mode": "referent_followup",
            "capability_resolution_mode": "live_calendar",
            "expected_reply_type": "time",
        },
        trace_entries=[
            {
                "stage": "policy_core_guard",
                "decision": "collect_slot_order_collect_prompt",
                "validation_error": "collect_slot_order_invalid",
            }
        ],
        **base_kwargs,
    )
    assert "resolved_referent_trace_missing" in reasons

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "policy_core_guard",
            "subject_kind": "service",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "resolution_mode": "referent_followup",
            "capability_resolution_mode": "live_calendar",
            "resolved_referent": "Маникюр",
            "referent_source": "policy_slot_state",
            "expected_reply_type": "time",
            "llm_policy_core": {
                "subject_kind": "service",
                "capability": "bookability",
                "temporal_scope": "specific_time",
                "resolution_mode": "referent_followup",
                "capability_resolution_mode": "live_calendar",
                "referent_resolution": {
                    "decision": "resolved",
                    "resolved_referent": "Маникюр",
                    "referent_source": "policy_slot_state",
                },
            },
        },
        trace_entries=[
            {
                "stage": "referent_resolver",
                "decision": "resolved",
                "subject_kind": "service",
                "capability": "bookability",
                "temporal_scope": "specific_time",
                "capability_resolution_mode": "live_calendar",
                "resolved_referent": "Маникюр",
                "referent_source": "policy_slot_state",
            },
            {
                "stage": "policy_core_guard",
                "decision": "collect_slot_order_collect_prompt",
                "validation_error": "collect_slot_order_invalid",
            },
        ],
        **base_kwargs,
    )
    assert "resolved_referent_trace_missing" not in reasons


def test_evaluate_turn_flags_expected_meta_mismatch_for_structured_oracle():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "booking",
            "expected_reply_type": "service_choice",
        },
        trace_entries=[
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "service_choice",
            }
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action="booking_prompt",
        expected_info_sections=[],
        expected_reply_type="service_choice",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="service_choice",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="На какую услугу хотите записаться?",
        tool_signals={},
        expected_meta={"expected_reply_type": "time", "source": "booking"},
        expected_meta_any={},
        expected_meta_contains={},
        expected_trace_contains=[],
    )

    assert "expected_meta_mismatch" in reasons


def test_evaluate_turn_accepts_structured_meta_and_trace_oracle():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "booking",
            "expected_reply_type": "time",
            "expected_reply_reason": "booking_prompt",
        },
        trace_entries=[
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "booking_prompt",
            }
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action="booking_prompt",
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Подскажите, пожалуйста, точное время.",
        tool_signals={},
        expected_meta={
            "source": "booking",
            "expected_reply_type": "time",
        },
        expected_meta_any={},
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
            }
        ],
    )

    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_accepts_timeout_grounded_slot_constraint_name_resume_meta():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "policy_core_guard",
            "source": "llm_policy_core",
            "expected_reply_type": "name",
            "expected_reply_reason": "policy_core_degraded_collect",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "pending_question_interaction": "slot_constraint",
            "policy_core_degrade_reason": "policy_error:timeout",
        },
        trace_entries=[
            {
                "stage": "pending_question_interaction",
                "source": "question_contract",
                "decision": "slot_constraint",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "expected_reply_type": "time",
            },
            {
                "stage": "question_contract",
                "decision": "matched",
                "answer_slot": "datetime",
                "answer_value": "завтра",
                "expected_reply_type": "time",
            },
            {
                "stage": "policy_core_guard",
                "decision": "timeout_booking_collect",
                "reason": "policy_error:timeout",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "reason": "policy_core_degraded_collect",
                "expected_reply_type": "name",
            },
            {
                "stage": "policy_core_guard",
                "decision": "degraded_collect",
                "reason": "policy_error:timeout",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Отлично, время подходит. Как вас зовут?",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "pending_question_act": ["slot_constraint"],
            "pending_question_target": ["time"],
            "expected_reply_type": ["time"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "question_contract",
                "decision": "matched",
                "answer_slot": "datetime",
                "expected_reply_type": "time",
            }
        ],
    )

    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_accepts_collect_slot_order_time_window_slot_constraint_guidance():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "booking",
            "source": "booking_slot_guidance",
            "expected_reply_type": "time",
            "expected_reply_reason": "booking_slot_guidance",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "pending_question_interaction": "slot_constraint",
            "policy_core_degrade_reason": "policy_validation:collect_slot_order_invalid",
        },
        trace_entries=[
            {
                "stage": "policy_core_guard",
                "decision": "collect_slot_order_slot_constraint_guidance",
                "validation_error": "collect_slot_order_invalid",
                "missing_slot": "datetime",
                "requested_slot": "name",
            },
            {
                "stage": "pending_question_interaction",
                "source": "policy_core_guard",
                "decision": "booking_slot_guidance",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "expected_reply_type": "time",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "reason": "booking_slot_guidance",
                "expected_reply_type": "time",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Подскажите, пожалуйста, точное время.",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "pending_question_act": ["slot_constraint"],
            "pending_question_target": ["time"],
            "expected_reply_type": ["time"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "pending_question_interaction",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
            },
            {
                "stage": "question_contract",
                "expected_reply_type": "time",
            },
        ],
    )

    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_flags_timeout_grounded_slot_constraint_name_resume_without_timeout_trace():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "policy_core_guard",
            "source": "llm_policy_core",
            "expected_reply_type": "name",
            "expected_reply_reason": "policy_core_degraded_collect",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "pending_question_interaction": "slot_constraint",
            "policy_core_degrade_reason": "policy_error:timeout",
        },
        trace_entries=[
            {
                "stage": "pending_question_interaction",
                "source": "question_contract",
                "decision": "slot_constraint",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "expected_reply_type": "time",
            },
            {
                "stage": "question_contract",
                "decision": "matched",
                "answer_slot": "datetime",
                "answer_value": "завтра",
                "expected_reply_type": "time",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Отлично, время подходит. Как вас зовут?",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "pending_question_act": ["slot_constraint"],
            "pending_question_target": ["time"],
            "expected_reply_type": ["time"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "question_contract",
                "decision": "matched",
                "answer_slot": "datetime",
                "expected_reply_type": "time",
            }
        ],
    )

    assert "expected_meta_mismatch" in reasons


def test_evaluate_turn_flags_invalid_schema_truth_gate_for_specialist_followup():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "master",
            "source": "truth_gate",
            "expected_reply_type": "time",
            "booking_interrupt_info": True,
            "policy_core_mode": "degraded_fallback",
            "policy_core_degrade_reason": "policy_error:invalid_schema",
        },
        trace_entries=[
            {
                "stage": "question_contract",
                "decision": "missed",
                "expected_reply_type": "time",
                "answer_error": "blocked_by_info",
            },
            {
                "stage": "llm_policy_core",
                "error": "invalid_schema",
            },
            {
                "stage": "policy_core_guard",
                "decision": "degraded_fallback",
                "reason": "policy_error:invalid_schema",
            },
            {
                "stage": "booking_interrupt",
                "decision": "info_reply",
                "info_sections": ["master"],
            },
            {
                "stage": "truth_gate",
                "decision": "reply",
                "intent": "master",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="У нас работает мастер Асем. На какую дату и время вам удобно?",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "pending_question_target": ["specialist"],
            "expected_reply_type": ["time"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "pending_question_interaction",
                "decision": "booking_specialist_followup",
                "pending_question_target": "specialist",
                "expected_reply_type": "time",
            }
        ],
    )

    assert "expected_meta_mismatch" in reasons
    assert "expected_trace_miss" in reasons


def test_evaluate_turn_accepts_invalid_schema_booking_request_specialist_followup():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "policy_core_guard",
            "expected_reply_type": "time",
            "pending_question_target": "specialist",
            "pending_question_interaction": "specialist_followup",
            "pending_question_owner": "policy_core_invalid_schema_specialist_followup",
            "active_question_relation": "referent_followup",
            "specialist_name": "Айгерим",
            "policy_core_mode": "degraded_fallback",
            "policy_core_degrade_reason": "policy_error:invalid_schema",
        },
        trace_entries=[
            {
                "stage": "question_contract",
                "decision": "missed",
                "expected_reply_type": "time",
                "answer_error": "blocked_by_info",
            },
            {
                "stage": "llm_policy_core",
                "error": "invalid_schema",
            },
            {
                "stage": "specialist_hint",
                "decision": "ok",
                "tool_action": "collect",
                "specialist_name": "Айгерим",
            },
            {
                "stage": "policy_core_guard",
                "decision": "invalid_schema_specialist_followup",
                "reason": "policy_error:invalid_schema",
            },
            {
                "stage": "pending_question_interaction",
                "decision": "booking_specialist_followup",
                "pending_question_target": "specialist",
                "active_question_relation": "referent_followup",
                "expected_reply_type": "time",
                "specialist_name": "Айгерим",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "reason": "policy_core_invalid_schema_specialist_followup",
                "expected_reply_type": "time",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=None,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Айгерим доступна. На какую дату и время вам удобно?",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "pending_question_target": ["specialist"],
            "active_question_relation": ["referent_followup"],
            "expected_reply_type": ["time"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "pending_question_interaction",
                "decision": "booking_specialist_followup",
                "pending_question_target": "specialist",
                "active_question_relation": "referent_followup",
                "expected_reply_type": "time",
            }
        ],
    )

    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_accepts_active_name_deictic_time_availability_followup():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "llm_policy_core",
            "expected_reply_type": "name",
            "expected_reply_reason": "booking_time_availability_followup",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "pending_question_interaction": "ask_about_requested_slot",
            "pending_question_owner": "booking_time_availability_followup",
            "active_question_relation": "ask_about_requested_slot",
            "current_datetime": "15:00",
            "alternate_datetime": "15:00",
        },
        trace_entries=[
            {
                "stage": "pending_question_interaction",
                "decision": "booking_time_availability_followup",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
                "expected_reply_type": "name",
                "current_datetime": "15:00",
                "alternate_datetime": "15:00",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "reason": "booking_time_availability_followup",
                "expected_reply_type": "name",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="name",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="name",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Сейчас в заявке отмечено 15:00. Если хотите оставить именно это время и продолжить запись, скажите об этом. Как вас зовут?",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "pending_question_act": ["ask_about_requested_slot"],
            "pending_question_target": ["time"],
            "active_question_relation": ["ask_about_requested_slot"],
            "expected_reply_type": ["name"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "pending_question_interaction",
                "decision": "booking_time_availability_followup",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
                "expected_reply_type": "name",
            },
            {
                "stage": "question_contract",
                "expected_reply_type": "name",
            },
        ],
    )

    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_accepts_active_name_named_specialist_followup():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "llm_policy_core",
            "expected_reply_type": "name",
            "expected_reply_reason": "booking_prompt",
            "pending_question_target": "specialist",
            "pending_question_interaction": "specialist_followup",
            "pending_question_owner": "booking_specialist_followup",
            "active_question_relation": "referent_followup",
            "specialist_name": "Айгерим",
        },
        trace_entries=[
            {
                "stage": "policy_core_guard",
                "decision": "active_name_specialist_followup",
                "reason": "contract_validation_failure",
                "pending_question_target": "specialist",
                "expected_reply_type": "name",
            },
            {
                "stage": "pending_question_interaction",
                "decision": "booking_specialist_followup",
                "pending_question_target": "specialist",
                "active_question_relation": "referent_followup",
                "expected_reply_type": "name",
                "specialist_name": "Айгерим",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "reason": "booking_prompt",
                "expected_reply_type": "name",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="name",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="name",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Как вас зовут?",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "pending_question_target": ["specialist"],
            "active_question_relation": ["referent_followup"],
            "expected_reply_type": ["name"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "pending_question_interaction",
                "decision": "booking_specialist_followup",
                "pending_question_target": "specialist",
                "active_question_relation": "referent_followup",
                "expected_reply_type": "name",
            },
            {
                "stage": "question_contract",
                "expected_reply_type": "name",
            },
        ],
    )

    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_accepts_invalid_schema_specialist_followup_with_generalized_expectation():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "policy_core_guard",
            "expected_reply_type": "time",
            "expected_reply_reason": "policy_core_invalid_schema_specialist_followup",
            "pending_question_target": "specialist",
            "pending_question_interaction": "specialist_followup",
            "pending_question_owner": "policy_core_invalid_schema_specialist_followup",
            "active_question_relation": "referent_followup",
            "specialist_name": "Айгерим",
            "policy_core_mode": "degraded_fallback",
            "policy_core_degrade_reason": "policy_error:invalid_schema",
            "policy_core_guard_recovery": "invalid_schema_specialist_followup",
        },
        trace_entries=[
            {
                "stage": "question_contract",
                "decision": "missed",
                "expected_reply_type": "time",
                "answer_error": "blocked_by_info",
            },
            {
                "stage": "llm_policy_core",
                "error": "invalid_schema",
            },
            {
                "stage": "specialist_hint",
                "decision": "ok",
                "tool_action": "collect",
                "specialist_name": "Айгерим",
            },
            {
                "stage": "policy_core_guard",
                "decision": "invalid_schema_specialist_followup",
                "reason": "policy_error:invalid_schema",
            },
            {
                "stage": "pending_question_interaction",
                "decision": "booking_specialist_followup",
                "pending_question_target": "specialist",
                "active_question_relation": "referent_followup",
                "expected_reply_type": "time",
                "specialist_name": "Айгерим",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "reason": "policy_core_invalid_schema_specialist_followup",
                "expected_reply_type": "time",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=None,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Понял, ориентир по специалисту — Айгерим. На какую дату и время вам удобно?",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "pending_question_target": ["specialist"],
            "pending_question_interaction": ["specialist_followup"],
            "active_question_relation": ["referent_followup"],
            "expected_reply_type": ["time"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "pending_question_interaction",
                "decision": "booking_specialist_followup",
                "pending_question_target": "specialist",
                "active_question_relation": "referent_followup",
                "expected_reply_type": "time",
            },
            {
                "stage": "question_contract",
                "expected_reply_type": "time",
            },
        ],
    )

    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_accepts_invalid_schema_specialist_followup_with_surface_hint():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "policy_core_guard",
            "expected_reply_type": "time",
            "expected_reply_reason": "policy_core_invalid_schema_specialist_followup",
            "pending_question_target": "specialist",
            "pending_question_interaction": "specialist_followup",
            "pending_question_owner": "policy_core_invalid_schema_specialist_followup",
            "active_question_relation": "referent_followup",
            "specialist_name": "Мадина",
            "specialist_hint_source": "message_surface",
            "policy_core_mode": "degraded_fallback",
            "policy_core_degrade_reason": "policy_error:invalid_schema",
            "policy_core_guard_recovery": "invalid_schema_specialist_followup",
        },
        trace_entries=[
            {
                "stage": "question_contract",
                "decision": "missed",
                "expected_reply_type": "time",
                "answer_error": "blocked_by_info",
            },
            {
                "stage": "llm_policy_core",
                "error": "invalid_schema",
            },
            {
                "stage": "specialist_hint",
                "decision": "ok",
                "tool_action": "collect",
                "source": "message_surface",
                "specialist_name": "Мадина",
            },
            {
                "stage": "policy_core_guard",
                "decision": "invalid_schema_specialist_followup",
                "reason": "policy_error:invalid_schema",
            },
            {
                "stage": "pending_question_interaction",
                "decision": "booking_specialist_followup",
                "pending_question_target": "specialist",
                "active_question_relation": "referent_followup",
                "expected_reply_type": "time",
                "specialist_name": "Мадина",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "reason": "policy_core_invalid_schema_specialist_followup",
                "expected_reply_type": "time",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=None,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Понял, ориентир по специалисту — Мадина. На какую дату и время вам удобно?",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "pending_question_target": ["specialist"],
            "active_question_relation": ["referent_followup"],
            "expected_reply_type": ["time"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "pending_question_interaction",
                "decision": "booking_specialist_followup",
                "pending_question_target": "specialist",
                "active_question_relation": "referent_followup",
                "expected_reply_type": "time",
            }
        ],
    )

    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_accepts_timeout_active_name_named_specialist_followup():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "policy_core_guard",
            "expected_reply_type": "name",
            "expected_reply_reason": "policy_core_timeout_specialist_followup",
            "pending_question_target": "specialist",
            "pending_question_interaction": "specialist_followup",
            "pending_question_owner": "policy_core_timeout_specialist_followup",
            "active_question_relation": "referent_followup",
            "specialist_name": "Айгерим",
            "policy_core_guard_recovery": "timeout_specialist_followup",
        },
        trace_entries=[
            {
                "stage": "policy_core_guard",
                "decision": "timeout_specialist_followup",
                "reason": "policy_error:timeout",
                "missing_slot": "name",
            },
            {
                "stage": "pending_question_interaction",
                "decision": "booking_specialist_followup",
                "pending_question_target": "specialist",
                "active_question_relation": "referent_followup",
                "expected_reply_type": "name",
                "specialist_name": "Айгерим",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "reason": "policy_core_timeout_specialist_followup",
                "expected_reply_type": "name",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="name",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="name",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Понял, ориентир по специалисту — Айгерим. Как вас зовут?",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "pending_question_target": ["specialist"],
            "active_question_relation": ["referent_followup"],
            "expected_reply_type": ["name"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "pending_question_interaction",
                "decision": "booking_specialist_followup",
                "pending_question_target": "specialist",
                "active_question_relation": "referent_followup",
                "expected_reply_type": "name",
            },
            {
                "stage": "question_contract",
                "expected_reply_type": "name",
            },
        ],
    )

    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_accepts_timeout_master_info_interrupt_for_generic_specialist_change():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "master",
            "source": "booking_info_contract",
            "expected_reply_type": "time",
            "pending_question_target": "specialist",
            "active_question_relation": "specialist_availability_interrupt",
            "booking_interrupt_info": True,
            "info_sections": ["master"],
            "policy_core_guard_recovery": "timeout_master_info_interrupt",
            "policy_core_timeout_retry_path": "booking_interrupt_master_info",
        },
        trace_entries=[
            {
                "stage": "policy_core_guard",
                "decision": "timeout_master_info_interrupt",
                "reason": "policy_error:timeout",
                "missing_slot": "datetime",
                "pending_question_target": "specialist",
                "active_question_relation": "specialist_availability_interrupt",
            },
            {
                "stage": "booking_interrupt",
                "decision": "info_reply",
                "pending_question_target": "specialist",
                "booking_interrupt_info": True,
                "info_sections": ["master"],
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "reason": "booking_prompt",
                "expected_reply_type": "time",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Да, специалиста можно поменять. На какую дату и время вам удобно?",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "pending_question_target": ["specialist"],
            "active_question_relation": ["specialist_availability_interrupt"],
            "expected_reply_type": ["time"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "booking_interrupt",
                "decision": "info_reply",
                "pending_question_target": "specialist",
                "info_sections": ["master"],
            },
            {
                "stage": "question_contract",
                "expected_reply_type": "time",
            },
        ],
    )

    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_accepts_active_time_generic_master_info_interrupt():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "master",
            "source": "booking_info_contract",
            "expected_reply_type": "time",
            "pending_question_target": "time",
            "booking_interrupt_info": True,
            "info_sections": ["master"],
        },
        trace_entries=[
            {
                "stage": "policy_interrupt_contract",
                "decision": "semantic_override_blocked",
                "reason_code": "policy_collect_info_interrupt_owner",
                "info_sections": ["master"],
            },
            {
                "stage": "booking_interrupt",
                "decision": "info_reply",
                "pending_question_target": "time",
                "booking_interrupt_info": True,
                "info_sections": ["master"],
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "reason": "booking_interrupt",
                "expected_reply_type": "time",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=["master"],
        info_answered={"master": True},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="По маникюру у нас работают Айгерим и Динара. На какую дату и время вам удобно?",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "pending_question_target": ["time"],
            "expected_reply_type": ["time"],
            "source": ["booking_info_contract"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "booking_interrupt",
                "decision": "info_reply",
                "pending_question_target": "time",
                "info_sections": ["master"],
            },
            {
                "stage": "question_contract",
                "expected_reply_type": "time",
            },
        ],
    )

    assert "info_section_miss" not in reasons
    assert "expected_info_section_miss" not in reasons
    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_accepts_duration_info_interrupt_with_time_resume():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "service_duration",
            "source": "truth_gate",
            "expected_reply_type": "time",
            "pending_question_target": "time",
            "info_sections": ["duration", "service_duration"],
        },
        trace_entries=[
            {
                "stage": "policy_interrupt_contract",
                "decision": "semantic_override_blocked",
                "reason_code": "policy_collect_info_interrupt_owner",
                "info_sections": ["duration"],
            },
            {
                "stage": "policy_interrupt_contract",
                "decision": "service_query_carryover",
                "source": "booking_state",
                "service_query": "Маникюр",
                "info_sections": ["duration"],
            },
            {
                "stage": "truth_gate",
                "decision": "reply",
                "intent": "service_duration",
                "service_query": "Маникюр",
                "info_sections": ["duration", "service_duration"],
            },
            {
                "stage": "booking_interrupt",
                "decision": "info_reply",
                "pending_question_target": "time",
                "info_sections": ["duration", "service_duration"],
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=["duration", "service_duration"],
        info_answered={"duration": True, "service_duration": True},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Маникюр занимает около 90 минут.",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "pending_question_target": ["time"],
            "expected_reply_type": ["time"],
            "source": ["truth_gate"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "booking_interrupt",
                "decision": "info_reply",
                "pending_question_target": "time",
                "info_sections": ["duration", "service_duration"],
            },
            {
                "stage": "question_contract",
                "expected_reply_type": "time",
            },
        ],
    )

    assert "expected_info_section_miss" not in reasons
    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons
    assert "irrelevant_fact" not in reasons


def test_evaluate_turn_accepts_collect_service_info_interrupt_under_active_time():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "catalog.service_query",
            "source": "tool_registry",
            "tool_action": "catalog.service_query",
            "tool_decision": "services_overview",
            "expected_reply_type": "time",
            "booking_interrupt_info": True,
            "info_sections": ["services_overview"],
            "policy_collect_guard_recovery": "active_time_service_info_interrupt",
        },
        trace_entries=[
            {
                "stage": "llm_policy_plan_delta",
                "decision": "override_event",
                "from_tool_action": "collect",
                "to_tool_action": "catalog.service_query",
            },
            {
                "stage": "policy_interrupt_contract",
                "decision": "collect_service_info_interrupt",
                "service_query": "Стрижка",
                "expected_reply_type": "time",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "reason": "booking_interrupt",
                "expected_reply_type": "time",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=["info"],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="По стрижке у нас есть женская, мужская и детская стрижка.",
        tool_signals={},
        expected_meta={},
        expected_meta_any={"expected_reply_type": ["time"]},
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "policy_interrupt_contract",
                "decision": "collect_service_info_interrupt",
            },
            {
                "stage": "question_contract",
                "expected_reply_type": "time",
            },
        ],
    )

    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_accepts_service_choice_price_interrupt_booking_progress():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "catalog.service_query",
            "source": "tool_registry",
            "tool_action": "catalog.service_query",
            "tool_decision": "truth_fallback",
            "expected_reply_type": "time",
            "expected_reply_reason": "catalog_service_booking_progress",
            "expected_reply_contract_reason": "catalog_service_booking_progress",
            "info_sections": ["pricing"],
        },
        trace_entries=[
            {
                "stage": "tool_registry",
                "decision": "truth_fallback",
                "tool_action": "catalog.service_query",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "reason": "catalog_service_booking_progress",
                "expected_reply_type": "time",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=["price"],
        info_answered={"price": True},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Маникюр классический — 2 500 ₸.",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "expected_reply_type": ["time"],
            "expected_reply_contract_reason": ["catalog_service_booking_progress"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "question_contract",
                "expected_reply_type": "time",
                "reason": "catalog_service_booking_progress",
            },
        ],
    )

    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_flags_hours_info_tag_on_booking_time_daypart_preference():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "policy_core_guard",
            "expected_reply_type": "time",
            "expected_reply_reason": "policy_core_degraded_collect",
            "expected_reply_matched": True,
        },
        trace_entries=[
            {
                "stage": "question_contract",
                "decision": "matched",
                "expected_reply_type": "time",
                "answer_slot": "datetime",
                "value": "утром",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "reason": "policy_core_degraded_collect",
                "expected_reply_type": "time",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=["hours"],
        info_answered={"hours": False},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="На какую дату и время вам удобно?",
        tool_signals={},
    )

    assert "info_section_miss" in reasons


def test_evaluate_turn_accepts_booking_time_daypart_preference_without_hours_info_tag():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "policy_core_guard",
            "expected_reply_type": "time",
            "expected_reply_reason": "policy_core_degraded_collect",
            "expected_reply_matched": True,
        },
        trace_entries=[
            {
                "stage": "question_contract",
                "decision": "matched",
                "expected_reply_type": "time",
                "answer_slot": "datetime",
                "value": "утром",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "reason": "policy_core_degraded_collect",
                "expected_reply_type": "time",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="На какую дату и время вам удобно?",
        tool_signals={},
    )

    assert "info_section_miss" not in reasons


def test_evaluate_turn_accepts_question_like_daypart_exact_time_fill_name_resume():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "question_contract",
            "expected_reply_type": "name",
            "expected_reply_reason": "booking_prompt",
            "expected_reply_matched": True,
        },
        trace_entries=[
            {
                "stage": "question_contract",
                "decision": "matched",
                "expected_reply_type": "time",
                "value": "10:00",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "reason": "booking_prompt",
                "expected_reply_type": "name",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="name",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="name",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Записала на завтра в 10:00. Как вас зовут?",
        tool_signals={},
        expected_meta={},
        expected_meta_any={"expected_reply_type": ["name"]},
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "question_contract",
                "expected_reply_type": "name",
            }
        ],
    )

    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_flags_policy_core_success_specialist_followup_owner_gap():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "llm_policy_core",
            "policy_core_mode": "policy_core",
            "expected_reply_type": "time",
        },
        trace_entries=[
            {
                "stage": "question_contract",
                "decision": "missed",
                "expected_reply_type": "time",
                "answer_error": "blocked_by_info",
            },
            {
                "stage": "llm_policy_core",
                "decision": "collect",
                "intent": "booking",
                "subject_kind": "specialist",
                "capability": "bookability",
                "resolution_mode": "clarify_missing_time",
                "next_question": "datetime",
                "pending_question_target": None,
                "active_question_relation": None,
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "booking_prompt",
            },
            {
                "stage": "booking",
                "decision": "prompt",
                "source": "llm_policy_core",
                "missing_slot": "datetime",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="На какую дату и время вам удобно?",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "pending_question_target": ["specialist"],
            "active_question_relation": ["referent_followup"],
            "expected_reply_type": ["time"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "pending_question_interaction",
                "decision": "booking_specialist_followup",
                "pending_question_target": "specialist",
                "active_question_relation": "referent_followup",
                "expected_reply_type": "time",
            }
        ],
    )

    assert "expected_meta_mismatch" in reasons
    assert "expected_trace_miss" in reasons


def test_evaluate_turn_accepts_choose_specialist_master_interrupt():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "master",
            "source": "booking_info_contract",
            "booking_interrupt_info": True,
            "pending_question_target": "time",
            "expected_reply_type": "time",
            "info_sections": ["master"],
        },
        trace_entries=[
            {
                "stage": "booking_interrupt",
                "decision": "info_reply",
                "pending_question_target": "time",
                "info_sections": ["master"],
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "booking_prompt",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=["master"],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=["master"],
        info_answered={"master": True},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Да, специалиста выбрать можно. По маникюру у нас работают Айгерим и Динара. На какую дату и время вам удобно?",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "pending_question_target": ["time"],
            "expected_reply_type": ["time"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "booking_interrupt",
                "decision": "info_reply",
                "pending_question_target": "time",
                "info_sections": ["master"],
            }
        ],
    )

    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons
    assert "info_section_miss" not in reasons


def test_evaluate_turn_flags_invalid_schema_service_grounded_booking_service_choice_gap():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "llm_policy_core",
            "policy_core_mode": "degraded_fallback",
            "policy_core_degrade_reason": "policy_error:invalid_schema",
            "expected_reply_type": "service_choice",
            "service_query": None,
        },
        trace_entries=[
            {
                "stage": "llm_policy_core",
                "error": "invalid_schema",
            },
            {
                "stage": "policy_core_guard",
                "decision": "degraded_collect",
                "reason": "policy_error:invalid_schema",
                "missing_slot": "service",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "service_choice",
                "reason": "policy_core_degraded_collect",
            },
            {
                "stage": "booking",
                "decision": "prompt",
                "source": "llm_policy_core",
                "missing_slot": "service",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="service_choice",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="На какую услугу хотите записаться? После этого сразу проверю свободное время.",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "expected_reply_type": ["time"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "policy_core_guard",
                "decision": "invalid_schema_service_grounded_booking",
                "reason": "policy_error:invalid_schema",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "policy_core_invalid_schema_service_grounded_booking",
            },
        ],
    )

    assert "expected_meta_mismatch" in reasons
    assert "expected_trace_miss" in reasons


def test_evaluate_turn_flags_active_time_consult_topic_shift_service_choice_gap():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "calendar.list_slots",
            "source": "tool_registry",
            "tool_action": "calendar.list_slots",
            "expected_reply_type": "time",
        },
        trace_entries=[
            {
                "stage": "consult",
                "decision": "reply",
                "intent": "consult_reply",
                "consult_topic": "nails_design",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "policy_core_degraded_collect",
            },
            {
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.list_slots",
            },
        ],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="service_choice",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="На 20:00 свободного окна нет. Доступны: 09:00, 10:00, 11:00.",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "expected_reply_type": ["service_choice"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "question_contract",
                "expected_reply_type": "service_choice",
                "reason": "consult_topic_shift",
            }
        ],
    )

    assert "expected_meta_mismatch" in reasons
    assert "expected_trace_miss" in reasons


def test_evaluate_turn_flags_timeout_degrade_booking_generic():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "policy_core_guard",
            "policy_core_mode": "degraded_fallback",
            "policy_core_degrade_reason": "policy_error:timeout",
        },
        trace_entries=[{"stage": "policy_core_guard"}],
        state="bot_active",
        conv_meta={},
        handover_meta={},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state=None,
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Подскажите, пожалуйста, что именно вас интересует?",
        tool_signals={},
    )

    assert "timeout_degrade_booking_generic" in reasons


def test_evaluate_turn_accepts_pending_handoff_pricing_interrupt_keeps_time_followup():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "reply",
            "intent": "catalog.service_query",
            "source": "tool_registry",
            "pending_guard": "soft_pass",
            "pending_action": "pending_pass",
            "pending_resume_restored": True,
            "pending_handoff_resume_boundary": True,
            "expected_reply_type": "time",
            "expected_reply_reason": "booking_time_availability_followup",
        },
        trace_entries=[
            {
                "stage": "pending_resume",
                "decision": "restore_soft_pass",
                "reason": "handover_soft_pass",
            },
            {
                "stage": "session_memory",
                "decision": "preserve",
                "reason": "pending_handoff_resume_boundary",
            },
            {
                "stage": "pending_guard",
                "decision": "soft_pass",
                "state": "pending",
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "booking_time_availability_followup",
            },
            {
                "stage": "tool_registry",
                "decision": "truth_fallback",
                "tool_action": "catalog.service_query",
                "info_sections": ["pricing"],
            },
        ],
        state="pending",
        conv_meta={},
        handover_meta={"status": "pending"},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=["pricing"],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=["price"],
        info_answered={"pricing": True},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="Маникюр классический — 2 500 ₸.",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "expected_reply_type": ["time"],
            "pending_guard": ["soft_pass"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "question_contract",
                "expected_reply_type": "time",
            }
        ],
    )

    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons


def test_evaluate_turn_accepts_pending_soft_pass_timeout_booking_resume_boundary():
    evaluate = _load_evaluate_turn()

    reasons = evaluate(
        meta={
            "action": "booking_prompt",
            "intent": "booking",
            "source": "policy_core_guard",
            "pending_guard": "soft_pass",
            "pending_action": "pending_pass",
            "pending_handoff_resume_boundary": True,
            "session_memory_reset_skipped": "pending_handoff_resume_boundary",
            "expected_reply_type": "time",
            "expected_reply_reason": "policy_core_timeout_owner_boundary",
            "policy_core_guard_recovery": "timeout_owner_boundary_collect",
            "policy_core_timeout_retry_path": "booking_resume_collect_boundary",
            "timeout_owner_boundary_source": "resume_contract",
            "owner_resolution_reason_code": "timeout_owner_boundary_resume_contract",
            "interaction_owner": "timeout booking resume contract boundary",
        },
        trace_entries=[
            {
                "stage": "session_memory",
                "decision": "preserve",
                "reason": "pending_handoff_resume_boundary",
            },
            {
                "stage": "pending_guard",
                "decision": "soft_pass",
                "state": "pending",
            },
            {
                "stage": "owner_resolver",
                "decision": "timeout_owner_boundary_match",
                "reason_code": "timeout_owner_boundary_resume_contract",
                "source": "resume_contract",
            },
            {
                "stage": "boundary_state",
                "decision": "resume_collect",
                "source": "pending_handoff",
                "missing_slot": "datetime",
            },
            {
                "stage": "policy_core_guard",
                "decision": "timeout_owner_boundary_collect",
                "missing_slot": "datetime",
                "filled_slots": [],
            },
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "time",
                "reason": "policy_core_timeout_owner_boundary",
            },
        ],
        state="pending",
        conv_meta={},
        handover_meta={"status": "pending"},
        bot_response=True,
        expected_response=True,
        expected_action=None,
        expected_info_sections=[],
        expected_reply_type="time",
        expected_state="bot_active",
        expected_reply=True,
        actual_expected_reply_type="time",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=False,
        outbox_text="На какую дату и время вам удобно?",
        tool_signals={},
        expected_meta={},
        expected_meta_any={
            "pending_guard": ["soft_pass"],
            "expected_reply_type": ["time"],
        },
        expected_meta_contains={},
        expected_trace_contains=[
            {
                "stage": "question_contract",
                "expected_reply_type": "time",
            }
        ],
    )

    assert "expected_state_mismatch" not in reasons
    assert "expected_meta_mismatch" not in reasons
    assert "expected_trace_miss" not in reasons
