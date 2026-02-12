import json
import random
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


def _load_module():
    base = Path(__file__).resolve()
    candidates = [
        base.parents[1] / "scripts" / "booking_dialog_scenarios.py",
        base.parents[2] / "scripts" / "booking_dialog_scenarios.py",
    ]
    script_path = next((path for path in candidates if path.exists()), candidates[0])
    if not script_path.exists():
        pytest.skip(
            "booking_dialog_scenarios.py not present in test runtime image",
            allow_module_level=True,
        )
    spec = spec_from_file_location("booking_dialog_scenarios", script_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_module = _load_module()
_merge_expectations = _module._merge_expectations


def test_merge_expectations_applies_override_fields():
    expect = _merge_expectations(
        ["booking", "time"],
        {
            "action": "handoff",
            "reply_type": "name",
            "state": "pending",
            "expected_reply": "false",
            "info_sections": ["master"],
        },
    )

    assert expect["action"] == "handoff"
    assert expect["reply_type"] == "name"
    assert expect["state"] == "pending"
    assert expect["expected_reply"] is False
    assert "master" in (expect.get("info_sections") or [])


def test_generate_llm_dialogs_retries_after_json_error(monkeypatch):
    calls = {"parse": 0, "openai": 0}

    def _fake_openai(prompt, *, api_key, model, base_url, max_tokens=1800):
        calls["openai"] += 1
        return "{}"

    def _fake_parse(_content, *, repair_fn=None):
        calls["parse"] += 1
        if calls["parse"] == 1:
            raise json.JSONDecodeError("bad", "{", 0)
        return {
            "dialogs": [
                {
                    "goal": "booking",
                    "turns": [
                        {
                            "kind": "text",
                            "text": "Хочу записаться",
                            "tags": ["booking"],
                            "expect": {
                                "action": None,
                                "info_sections": [],
                                "reply_type": "service_choice",
                                "state": "bot_active",
                                "expected_reply": True,
                                "allow_booking_stall": False,
                            },
                        }
                    ],
                }
            ]
        }

    monkeypatch.setenv("BOOKING_SCENARIO_LLM_BATCH_SIZE", "1")
    monkeypatch.setenv("BOOKING_SCENARIO_LLM_MAX_ATTEMPTS", "2")
    monkeypatch.setattr(_module, "_call_openai", _fake_openai)
    monkeypatch.setattr(_module, "_parse_llm_json", _fake_parse)
    monkeypatch.setattr(_module, "_infer_context_from_dialog", lambda _dialog, _rng: {"service": "Стрижка"})
    monkeypatch.setattr(_module, "_ensure_required_tags", lambda turns, _ctx, *, max_turns: turns)
    monkeypatch.setattr(_module, "_sanitize_llm_turns", lambda turns, _ctx, _rng: turns)
    monkeypatch.setattr(_module, "_prune_turns", lambda turns, _max_turns, _required: turns)
    monkeypatch.setattr(
        _module,
        "_media_turn",
        lambda _ctx, *, mode, kind: {"kind": mode, "text": kind, "tags": ["media"], "expect": {}},
    )

    dialogs = _module._generate_llm_dialogs(
        random.Random(7),
        count=1,
        min_turns=10,
        max_turns=15,
        include_media=False,
        media_mode="text",
        media_kind="photo",
        model="gpt-4o-mini",
        base_url="https://api.openai.com",
        api_key="test-key",
        coverage=["booking", "info", "interrupt", "handoff"],
        seed=7,
    )

    assert len(dialogs) == 1
    assert calls["openai"] == 2
    assert calls["parse"] == 2
