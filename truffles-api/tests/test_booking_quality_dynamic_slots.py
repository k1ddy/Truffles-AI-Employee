import ast
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _load_dynamic_slot_helpers():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))

    wanted_assignments = {
        "LLM_QUALITY_DYNAMIC_SLOT_TIME_TOKEN",
        "LLM_QUALITY_DYNAMIC_SLOT_DATE_TOKEN",
        "LLM_QUALITY_DYNAMIC_SLOT_SPECIALIST_TOKEN",
    }
    wanted_functions = {
        "_llm_quality_parse_slot_candidates",
        "_llm_quality_pick_slot_candidate",
        "_llm_quality_resolve_dynamic_slot_date",
        "_llm_quality_prepare_turn_text",
        "_llm_quality_update_dialog_runtime_slots",
        "_llm_quality_normalize_tool_token",
    }

    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if names & wanted_assignments:
                selected_nodes.append(node)
        if isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)

    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {
        "re": re,
        "datetime": datetime,
        "timedelta": timedelta,
        "timezone": timezone,
    }
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace


def test_parse_slot_candidates_extracts_specialists_and_times():
    ns = _load_dynamic_slot_helpers()
    parse_slots = ns["_llm_quality_parse_slot_candidates"]

    text = (
        "На какую дату и время вам удобно?\\n\\n"
        "Свободные слоты: Айгерим Болатова: 10:00, 12:00 | "
        "Алия Нурланова: 11:00, 13:30"
    )
    parsed = parse_slots(text)

    assert parsed[0]["specialist"] == "Айгерим Болатова"
    assert parsed[0]["time"] == "10:00"
    assert parsed[1]["time"] == "12:00"
    assert parsed[2]["specialist"] == "Алия Нурланова"
    assert parsed[3]["time"] == "13:30"


def test_prepare_turn_text_replaces_auto_slot_tokens():
    ns = _load_dynamic_slot_helpers()
    prepare_turn_text = ns["_llm_quality_prepare_turn_text"]

    runtime_state = {
        "slot_candidates": [
            {"specialist": "Алия Нурланова", "time": "11:00"},
            {"specialist": "Айгерим Болатова", "time": "12:00"},
        ]
    }
    turn = {
        "text": "Запишите к {{AUTO_SLOT_SPECIALIST}} на маникюр {{AUTO_SLOT_DATE}} {{AUTO_SLOT_TIME}}, имя Лена.",
        "dynamic_booking": {"prefer_specialist": "Айгерим", "date": "2026-02-18"},
    }

    text, meta = prepare_turn_text(turn, runtime_state, now=datetime(2026, 2, 17, tzinfo=timezone.utc))

    assert "Айгерим Болатова" in text
    assert "2026-02-18" in text
    assert "12:00" in text
    assert meta["resolved"] is True
    assert meta["specialist"] == "Айгерим Болатова"


def test_update_runtime_slots_saves_candidates_after_list_slots_ok():
    ns = _load_dynamic_slot_helpers()
    update_runtime = ns["_llm_quality_update_dialog_runtime_slots"]

    runtime_state = {}
    meta = {"tool_action": "calendar.list_slots", "tool_decision": "ok"}
    outbox_text = "Свободные слоты: Айгерим: 10:00, 11:00"

    update_runtime(runtime_state, meta=meta, outbox_text=outbox_text)

    assert "slot_candidates" in runtime_state
    assert runtime_state["slot_candidates"][0]["time"] == "10:00"


def test_prepare_turn_text_reports_missing_slot_candidates():
    ns = _load_dynamic_slot_helpers()
    prepare_turn_text = ns["_llm_quality_prepare_turn_text"]

    turn = {
        "text": "Запишите на {{AUTO_SLOT_DATE}} {{AUTO_SLOT_TIME}}.",
        "dynamic_booking": {"date": "tomorrow"},
    }

    text, meta = prepare_turn_text(turn, {"slot_candidates": []}, now=datetime(2026, 2, 17, tzinfo=timezone.utc))

    assert text == turn["text"]
    assert meta["resolved"] is False
    assert meta["reason"] == "slot_candidates_missing"
