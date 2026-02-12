import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


def _load_module():
    base = Path(__file__).resolve()
    candidates = [
        base.parents[1] / "scripts" / "llm_quality_digest.py",
        base.parents[2] / "scripts" / "llm_quality_digest.py",
    ]
    script_path = next((path for path in candidates if path.exists()), candidates[0])
    if not script_path.exists():
        pytest.skip(
            "llm_quality_digest.py not present in test runtime image",
            allow_module_level=True,
        )
    spec = spec_from_file_location("llm_quality_digest", script_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_module = _load_module()


def test_detect_logic_issues_flags_price_gap_on_booking_prompt():
    row = {
        "turn_text": "Сколько стоит маникюр?",
        "outbox_text": "Уточните, пожалуйста, филиал и имя.",
        "decision_meta": {"action": "booking_prompt", "info_sections": []},
    }
    issues = _module.detect_logic_issues(row)
    assert "price_unanswered" in issues
    assert "info_to_booking_prompt" in issues


def test_detect_logic_issues_accepts_price_in_reply_text():
    row = {
        "turn_text": "Сколько стоит маникюр?",
        "outbox_text": "Маникюр от 5000 тг, зависит от мастера.",
        "decision_meta": {"action": "reply", "info_sections": []},
    }
    issues = _module.detect_logic_issues(row)
    assert "price_unanswered" not in issues


def test_build_gap_scenarios_infers_info_sections_from_logic_issues():
    rows = [
        {
            "conversation_id": "conv-1",
            "turn_index": 3,
            "message_id": "msg-1",
            "turn_text": "Есть ли парковка и сколько стоит маникюр?",
            "outbox_text": "Подскажите имя для записи.",
            "decision_meta": {"action": "booking_prompt", "info_sections": []},
            "evaluation": {"reasons": ["expected_info_section_miss"]},
            "conversation_state": "bot_active",
            "expected_reply_type": "time",
        }
    ]
    payload = _module.build_gap_scenarios(rows, max_dialogs=5)
    dialogs = payload.get("dialogs") or []
    assert len(dialogs) == 1
    expect = dialogs[0]["turns"][0]["expect"]
    assert sorted(expect.get("info_sections") or []) == ["parking", "pricing"]
    tags = dialogs[0]["turns"][0]["tags"]
    assert "expected_info_section_miss" in tags
    assert "info_to_booking_prompt" in tags


def test_build_digest_aggregates_failures_and_logic_examples():
    summary = {
        "run_id": "run-1",
        "infra_valid": True,
        "semantic_valid": False,
        "metrics": {
            "rates": {"strict_pass_rate": 0.7, "info_answer_rate": 0.5},
            "counts": {"turns_failed": 3},
        },
    }
    rows = [
        {
            "conversation_id": "conv-1",
            "turn_index": 1,
            "message_id": "m-1",
            "turn_text": "Сколько стоит маникюр?",
            "outbox_text": "Уточните, пожалуйста, филиал и имя.",
            "decision_meta": {"action": "booking_prompt", "intent": "booking", "info_sections": []},
            "evaluation": {"reasons": ["expected_info_section_miss"]},
        },
        {
            "conversation_id": "conv-2",
            "turn_index": 2,
            "message_id": "m-2",
            "turn_text": "Где вы находитесь?",
            "outbox_text": "На какую дату записать?",
            "decision_meta": {"action": "booking_prompt", "intent": "booking", "info_sections": []},
            "evaluation": {"reasons": ["info_section_miss"]},
        },
    ]
    digest = _module.build_digest(summary, rows, max_examples=3)

    top_failures = dict(digest.get("top_failures") or [])
    assert top_failures.get("expected_info_section_miss") == 1
    assert top_failures.get("info_section_miss") == 1
    logic_counts = (digest.get("logic_findings") or {}).get("counts") or {}
    assert logic_counts.get("price_unanswered") == 1
    assert logic_counts.get("location_unanswered") == 1
    assert logic_counts.get("info_to_booking_prompt") == 2


def test_main_writes_digest_files(tmp_path, monkeypatch, capsys):
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    responses_path = run_dir / "responses.jsonl"
    summary_path = run_dir / "summary.json"
    responses = [
        {
            "conversation_id": "conv-1",
            "turn_index": 1,
            "message_id": "m-1",
            "turn_text": "Сколько стоит маникюр?",
            "outbox_text": "Подскажите филиал.",
            "decision_meta": {"action": "booking_prompt", "intent": "booking", "info_sections": []},
            "evaluation": {"reasons": ["expected_info_section_miss"]},
        }
    ]
    responses_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in responses) + "\n",
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(
            {
                "run_id": "run-cli",
                "infra_valid": True,
                "semantic_valid": True,
                "metrics": {"rates": {"strict_pass_rate": 1.0}, "counts": {"turns_failed": 0}},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "llm_quality_digest.py",
            "--run-dir",
            str(run_dir),
            "--max-examples",
            "2",
            "--max-gap-dialogs",
            "2",
        ],
    )
    rc = _module.main()
    assert rc == 0

    digest_json = run_dir / "digest.json"
    digest_md = run_dir / "digest.md"
    gaps_json = run_dir / "gaps_scenarios.json"
    assert digest_json.exists()
    assert digest_md.exists()
    assert gaps_json.exists()

    digest_payload = json.loads(digest_json.read_text(encoding="utf-8"))
    assert digest_payload.get("run_id") == "run-cli"
    assert "logic_findings" in digest_payload

    stdout_payload = json.loads(capsys.readouterr().out.strip())
    assert stdout_payload["rows"] == 1
    assert stdout_payload["digest_json"] == str(digest_json)
