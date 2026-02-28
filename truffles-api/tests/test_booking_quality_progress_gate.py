import ast
from pathlib import Path


def _load_progress_gate():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    wanted_assignments = {
        "CHAOS_BOOKING_REPLY_TYPES",
        "LLM_QUALITY_PROGRESS_TAGS_BY_REPLY_TYPE",
        "LLM_QUALITY_PROGRESS_SKIP_TAGS",
    }
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            if names & wanted_assignments:
                selected_nodes.append(node)
        if isinstance(node, ast.FunctionDef) and node.name in {
            "_llm_quality_should_expect_booking_progress",
            "_llm_quality_normalize_tool_token",
            "_llm_quality_effective_intent",
            "_llm_quality_value_matches",
            "_llm_quality_booking_progress_from_contract",
        }:
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return (
        namespace["_llm_quality_should_expect_booking_progress"],
        namespace["_llm_quality_booking_progress_from_contract"],
    )


def _load_slots_progress():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_llm_quality_booking_slots_progressed":
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace["_llm_quality_booking_slots_progressed"]


def _load_booking_tool_answered():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    selected_nodes = []
    wanted_functions = {
        "_llm_quality_normalize_tool_token",
        "_llm_quality_effective_intent",
        "_llm_quality_check_booking_tool_answered",
    }
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace["_llm_quality_check_booking_tool_answered"]


_should_expect_progress, _progress_from_contract = _load_progress_gate()
_slots_progressed = _load_slots_progress()
_booking_tool_answered = _load_booking_tool_answered()


def test_progress_gate_ignores_generic_booking_tag_for_service_choice():
    assert _should_expect_progress("service_choice", ["booking"]) is False
    assert _should_expect_progress("service_choice", ["service"]) is True


def test_progress_gate_time_requires_time_or_date_signal():
    assert _should_expect_progress("time", ["booking"]) is False
    assert _should_expect_progress("time", ["date"]) is True


def test_progress_gate_keeps_no_tag_fallback():
    assert _should_expect_progress("time", []) is True


def test_progress_gate_skips_slot_progress_for_calendar_missing_slot_reply():
    meta = {"intent": "calendar.list_slots", "tool_decision": "missing_slot"}
    assert _should_expect_progress("time", ["time"], meta) is False


def test_progress_gate_skips_slot_progress_for_policy_core_degraded_collect():
    meta = {
        "intent": "booking",
        "action": "booking_prompt",
        "expected_reply_type": "time",
        "expected_reply_reason": "policy_core_degraded_collect",
    }
    assert _should_expect_progress("time", ["time"], meta) is False


def test_slots_progress_detects_new_slot_even_when_count_stays_one():
    assert _slots_progressed({"service": "Стрижка"}, {"datetime": "15:00"}) is True


def test_slots_progress_detects_same_slot_value_as_no_progress():
    assert _slots_progressed({"datetime": "15:00"}, {"datetime": "15:00"}) is False


def test_slots_progress_detects_slot_value_change():
    assert _slots_progressed({"datetime": "15:00"}, {"datetime": "15:30"}) is True


def test_progress_from_contract_accepts_expected_reply_transition_for_list_slots():
    meta = {
        "intent": "calendar.list_slots",
        "tool_action": "calendar.list_slots",
        "tool_decision": "ok",
        "expected_reply_type": "name",
    }
    assert _progress_from_contract(
        booking_progressed=False,
        expected_reply_matched=False,
        meta=meta,
        expected_reply_type="name",
    )


def test_progress_from_contract_rejects_non_list_slots_intent():
    meta = {
        "intent": "catalog.location",
        "tool_action": "catalog.location",
        "tool_decision": "ok",
        "expected_reply_type": "name",
    }
    assert not _progress_from_contract(
        booking_progressed=False,
        expected_reply_matched=False,
        meta=meta,
        expected_reply_type="name",
    )


def test_progress_from_contract_rejects_mismatched_expected_reply_type():
    meta = {
        "intent": "calendar.list_slots",
        "tool_action": "calendar.list_slots",
        "tool_decision": "ok",
        "expected_reply_type": "time",
    }
    assert not _progress_from_contract(
        booking_progressed=False,
        expected_reply_matched=False,
        meta=meta,
        expected_reply_type="name",
    )


def test_booking_tool_answered_accepts_time_mismatch_with_requested_time_echo():
    meta = {
        "action": "reply",
        "intent": "calendar.get_booking",
        "tool_decision": "time_mismatch",
        "requested_time": "15:30",
    }
    assert _booking_tool_answered(
        meta,
        ["check_booking", "confirm"],
        "На 15:30 записи не вижу. Хотите проверить другую дату/время?",
    )


def test_booking_tool_answered_rejects_irrelevant_reply_without_requested_time_echo():
    meta = {
        "action": "reply",
        "intent": "calendar.get_booking",
        "tool_decision": "time_mismatch",
        "requested_time": "15:30",
    }
    assert not _booking_tool_answered(
        meta,
        ["check_booking", "confirm"],
        "Проверьте, пожалуйста, другую дату.",
    )
