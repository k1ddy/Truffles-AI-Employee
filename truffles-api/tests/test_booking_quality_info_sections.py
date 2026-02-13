import ast
from datetime import datetime, timedelta
from pathlib import Path
import re

from app.services import demo_salon_knowledge


def _load_expected_section_matcher():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    wanted_assignments = {
        "LLM_QUALITY_INFO_TAGS",
        "LLM_QUALITY_INFO_SECTION_MAP",
        "LLM_QUALITY_SECTION_TAG_MAP",
        "LLM_QUALITY_INTENT_TAG_MAP",
        "LLM_QUALITY_INFO_TRACE_LOOKBACK",
        "LLM_QUALITY_TRACE_WINDOW_PADDING_SECONDS",
    }
    wanted_functions = {
        "_parse_iso_datetime",
        "_llm_quality_current_turn_trace_entries",
        "_llm_quality_collect_info_signals",
        "_llm_quality_token_to_info_tags",
        "_llm_quality_expected_section_answered",
    }
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if names & wanted_assignments:
                selected_nodes.append(node)
        elif isinstance(node, ast.For):
            source_segment = ast.get_source_segment(source, node) or ""
            if "LLM_QUALITY_SECTION_TAG_MAP" in source_segment:
                selected_nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {"datetime": datetime, "timedelta": timedelta}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace["_llm_quality_expected_section_answered"]


_expected_section_answered = _load_expected_section_matcher()


def _load_info_tag_infer():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    wanted_assignments = {"LLM_QUALITY_TAG_HINTS", "LLM_QUALITY_TAG_HINTS_RE"}
    wanted_functions = {"_llm_quality_infer_info_tags"}
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if names & wanted_assignments:
                selected_nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {"re": re}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace["_llm_quality_infer_info_tags"]


_infer_info_tags = _load_info_tag_infer()


def test_expected_sections_match_promotions_synonyms():
    matched, info_sections, intents = _expected_section_answered(
        ["discounts", "discount", "promo", "promotion"],
        {"info_sections": ["promotions"], "intent": "promotions"},
        [],
    )
    assert matched is True
    assert "promotions" in info_sections
    assert "promotions" in intents


def test_expected_sections_match_location_aliases_from_trace():
    matched, info_sections, _intents = _expected_section_answered(
        ["location"],
        {},
        [{"info_sections": ["address"]}],
    )
    assert matched is True
    assert "address" in info_sections


def test_expected_sections_keep_mismatch_when_unrelated():
    matched, _info_sections, _intents = _expected_section_answered(
        ["hours"],
        {"info_sections": ["promotions"], "intent": "promotions"},
        [],
    )
    assert matched is False


def test_expected_sections_ignore_stale_trace_outside_current_pipeline_window():
    matched, info_sections, intents = _expected_section_answered(
        ["location"],
        {
            "intent": "booking",
            "timing": {
                "pipeline_started_at": "2026-02-08T10:00:00+00:00",
                "pipeline_finished_at": "2026-02-08T10:00:10+00:00",
            },
        },
        [
            {"recorded_at": "2026-02-08T09:58:00+00:00", "info_sections": ["address"]},
            {"recorded_at": "2026-02-08T10:00:06+00:00", "stage": "booking"},
        ],
    )
    assert matched is False
    assert "address" not in info_sections
    assert "booking" in intents


def test_expected_sections_do_not_fallback_to_tail_when_window_is_empty():
    matched, info_sections, intents = _expected_section_answered(
        ["location"],
        {
            "intent": "booking",
            "timing": {
                "pipeline_started_at": "2026-02-08T11:00:00+00:00",
                "pipeline_finished_at": "2026-02-08T11:00:05+00:00",
            },
        },
        [
            {"recorded_at": "2026-02-08T10:30:00+00:00", "info_sections": ["address"]},
            {"recorded_at": "2026-02-08T10:30:01+00:00", "intent": "hours"},
        ],
    )
    assert matched is False
    assert "address" not in info_sections
    assert intents == {"booking"}


def test_parking_signal_ignores_machine_haircut_phrase():
    normalized = demo_salon_knowledge._normalize_text("Сколько стоит стрижка машинкой?")
    assert demo_salon_knowledge._has_parking_signal(normalized, client_slug="demo_salon") is False


def test_parking_signal_accepts_machine_phrase_with_parking_context():
    normalized = demo_salon_knowledge._normalize_text("Машинку можно оставить во дворе?")
    assert demo_salon_knowledge._has_parking_signal(normalized, client_slug="demo_salon") is True


def test_info_tag_infer_detects_duration_from_how_long_question():
    tags = _infer_info_tags("Какая длительность процедуры?")
    assert "duration" in tags


def test_parking_signal_accepts_colloquial_parking_wording():
    normalized = demo_salon_knowledge._normalize_text("Подскажите, есть ли паркинг возле салона?")
    assert demo_salon_knowledge._has_parking_signal(normalized, client_slug="demo_salon") is True
