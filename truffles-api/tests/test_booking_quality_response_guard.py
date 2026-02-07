import ast
import math
from pathlib import Path
from types import SimpleNamespace


def _load_retry_helper():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_llm_quality_retry_outbox_for_expected_reply":
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
    }
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if "LLM_QUALITY_KNOWN_STATES" in names:
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
    }
    selected_nodes = []
    for node in tree.body:
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
        expected_state="bot_active",
        state="pending",
        meta={"action": "escalate"},
        conv_meta={},
        handover_meta={},
    )
