import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import yaml
from zoneinfo import ZoneInfo

from app.routers import webhook as webhook_router
from app.services.demo_salon_knowledge import (
    build_quiet_hours_notice,
    get_demo_salon_decision,
    get_salon_timezone,
)
from app.services.state_machine import ConversationState

EVAL_PATH = Path(__file__).resolve().parents[1] / "app" / "knowledge" / "demo_salon" / "EVAL.yaml"
EVAL_TIER = os.environ.get("EVAL_TIER", "").strip().lower()
CORE_EVAL_IDS = {
    "E001",
    "E002",
    "E003",
    "E003a",
    "E003b",
    "E003c",
    "E003f",
    "E003g",
    "E003h",
    "E003j",
    "E003k",
    "E004",
    "E005",
    "E006",
    "E007",
    "E008",
    "E009",
    "E010a",
    "E010b",
    "E010d",
    "E010e",
    "E010f",
    "E011",
    "E012",
    "E013",
    "E014",
    "E014c",
    "E015",
    "E016",
    "E017",
    "E018",
    "E019",
    "E020",
    "E021",
    "E022",
    "E023",
    "E026",
    "E028",
    "E031",
    "E032",
    "E033",
    "E034",
    "E035",
    "E037",
    "E038",
    "E039",
    "E040",
    "E047",
    "E057",
    "E060",
}


def _normalize(text: str) -> str:
    return (text or "").casefold()


def _build_local_datetime(value: str, tz_name: str | None) -> datetime:
    parts = [part for part in (value or "").split(":") if part.strip()]
    if len(parts) < 2:
        raise ValueError(f"Invalid local_time '{value}'")
    hour = int(parts[0])
    minute = int(parts[1])
    second = int(parts[2]) if len(parts) > 2 else 0
    tz = timezone.utc
    if tz_name:
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = timezone.utc
    return datetime(2025, 1, 1, hour, minute, second, tzinfo=tz)


def _fake_service_hint(text: str, client_slug: str | None) -> str | None:
    normalized = (text or "").casefold()
    if "маник" in normalized:
        return "маникюр"
    if "педик" in normalized:
        return "педикюр"
    if "стриж" in normalized:
        return "стрижка"
    if "массаж" in normalized and "ног" in normalized:
        return "массаж ног"
    if "бров" in normalized:
        return "брови"
    if "ресниц" in normalized:
        return "ресницы"
    return None


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


def _filter_cases(cases: list[dict]) -> list[dict]:
    if EVAL_TIER in {"all", "full"}:
        return cases
    if EVAL_TIER in {"core", "ci"} or (not EVAL_TIER and os.environ.get("CI")):
        core_cases = [case for case in cases if case.get("id") in CORE_EVAL_IDS]
        assert core_cases, "Core eval set is empty"
        return core_cases
    return cases


def test_demo_salon_eval_cases():
    data = yaml.safe_load(EVAL_PATH.read_text(encoding="utf-8"))
    cases = data.get("eval_cases", []) if isinstance(data, dict) else []
    cases = _filter_cases(cases)

    for case in cases:
        case_id = case.get("id", "<unknown>")
        user_text = case.get("user", "")
        expected = case.get("expected", {})

        expected_action = expected.get("action")
        if expected_action == "booking_flow":
            messages = [user_text] if user_text else []
            with patch("app.routers.webhook._extract_service_hint", side_effect=_fake_service_hint):
                booking_signal = webhook_router._has_booking_signal(
                    messages,
                    client_slug="demo_salon",
                    message_text=messages[-1] if messages else None,
                )
                assert booking_signal is True, f"{case_id}: booking signal not detected"
                booking_state = webhook_router._update_booking_from_messages(
                    {},
                    messages,
                    client_slug="demo_salon",
                )
            for slot in expected.get("booking_slots", []):
                assert booking_state.get(slot), f"{case_id}: booking slot missing '{slot}'"
            continue

        decision = get_demo_salon_decision(user_text)
        assert decision is not None, f"{case_id}: no decision for '{user_text}'"
        assert decision.action == expected_action, (
            f"{case_id}: action mismatch: {decision.action} != {expected_action}"
        )

        response = decision.response or ""
        if decision.action == "reply":
            intent = decision.intent or ""
            cta_intents = set(webhook_router.BOOKING_CTA_SERVICE_INTENTS) | {"hours", "location", "multi_truth"}
            if intent in cta_intents:
                response = webhook_router._maybe_append_booking_cta(
                    response,
                    conversation_state=ConversationState.BOT_ACTIVE.value,
                    allow_booking_flow=True,
                ) or response
        local_time = case.get("local_time")
        if local_time:
            tz_name = get_salon_timezone()
            now_local = _build_local_datetime(str(local_time), tz_name)
            notice = build_quiet_hours_notice(now_local=now_local)
            response = webhook_router._apply_quiet_hours_notice(response, notice)
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
