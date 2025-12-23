from pathlib import Path

import yaml

from app.services.demo_salon_knowledge import get_demo_salon_decision

EVAL_PATH = Path(__file__).resolve().parents[1] / "app" / "knowledge" / "demo_salon" / "EVAL.yaml"


def _normalize(text: str) -> str:
    return (text or "").casefold()


def _assert_contains_all(response: str, items: list[str], case_id: str, label: str) -> None:
    normalized = _normalize(response)
    for item in items:
        assert _normalize(item) in normalized, f"{case_id}: missing {label} '{item}'"


def _assert_contains_any(response: str, items: list[str], case_id: str, label: str) -> None:
    normalized = _normalize(response)
    if not any(_normalize(item) in normalized for item in items):
        raise AssertionError(f"{case_id}: none of {label} matched: {items}")


def _assert_not_contains(response: str, items: list[str], case_id: str) -> None:
    normalized = _normalize(response)
    for item in items:
        assert _normalize(item) not in normalized, f"{case_id}: must_not contains '{item}'"


def test_demo_salon_eval_cases():
    data = yaml.safe_load(EVAL_PATH.read_text(encoding="utf-8"))
    cases = data.get("eval_cases", []) if isinstance(data, dict) else []

    for case in cases:
        case_id = case.get("id", "<unknown>")
        user_text = case.get("user", "")
        expected = case.get("expected", {})

        decision = get_demo_salon_decision(user_text)
        assert decision is not None, f"{case_id}: no decision for '{user_text}'"
        assert decision.action == expected.get("action"), (
            f"{case_id}: action mismatch: {decision.action} != {expected.get('action')}"
        )

        response = decision.response or ""
        if expected.get("must_include"):
            _assert_contains_all(response, expected["must_include"], case_id, "must_include")
        if expected.get("must_include_any"):
            _assert_contains_any(response, expected["must_include_any"], case_id, "must_include_any")
        if expected.get("must_tell_user"):
            _assert_contains_all(response, expected["must_tell_user"], case_id, "must_tell_user")
        if expected.get("must_tell_user_any"):
            _assert_contains_any(response, expected["must_tell_user_any"], case_id, "must_tell_user_any")
        if expected.get("must_not"):
            _assert_not_contains(response, expected["must_not"], case_id)

        if expected.get("collect"):
            _assert_contains_all(response, expected["collect"], case_id, "collect")
        if expected.get("must_do"):
            if "ask_fields_missing" in expected["must_do"] and expected.get("collect"):
                _assert_contains_all(response, expected["collect"], case_id, "collect")
