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
        "_llm_quality_has_timeout_degrade_booking_generic",
        "_llm_quality_has_expected_followup_prompt",
        "_llm_quality_normalize_expect_token",
        "_llm_quality_text_has_billing_block_marker",
        "_llm_quality_payload_has_billing_block_marker",
        "_llm_quality_is_delivery_billing_waiver",
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
