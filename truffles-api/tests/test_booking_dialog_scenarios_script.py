from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_merge_expectations():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "booking_dialog_scenarios.py"
    spec = spec_from_file_location("booking_dialog_scenarios", script_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._merge_expectations


_merge_expectations = _load_merge_expectations()


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
