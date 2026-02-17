import ast
import json
import math
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
        "_llm_quality_is_booking_confirmation_text",
        "_llm_quality_normalize_tool_token",
        "_llm_quality_outbox_delivery_state",
        "_llm_quality_resolve_outbox_status",
        "_llm_quality_normalize_outbox_status",
    }
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if {
                "LLM_QUALITY_KNOWN_STATES",
                "LLM_QUALITY_BOOKING_CONFIRM_STATUS_HINTS",
                "LLM_QUALITY_BOOKING_CONFIRM_PHRASES",
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
        "_llm_quality_value_matches": lambda *_args, **_kwargs: True,
        "_chaos_reply_type_fallback_ok": lambda *_args, **_kwargs: False,
        "_llm_quality_expected_section_answered": lambda *_args, **_kwargs: (False, set(), set()),
        "_llm_quality_state_matches_expected": lambda *_args, **_kwargs: True,
        "_llm_quality_action_matches_expected": lambda *_args, **_kwargs: True,
        "_llm_quality_expected_reply_matches": lambda *_args, **_kwargs: True,
    }
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace["_llm_quality_evaluate_turn"]


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
