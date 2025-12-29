from pathlib import Path
from unittest.mock import patch

import yaml

from app.routers import webhook as webhook_router
from app.services import demo_salon_knowledge
from app.services.demo_salon_knowledge import get_demo_salon_decision

EVAL_PATH = Path(__file__).resolve().parents[1] / "app" / "knowledge" / "demo_salon" / "EVAL.yaml"


def _normalize(text: str) -> str:
    return (text or "").casefold()


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


def _local_service_search(text: str, client_slug: str, limit: int) -> list[dict]:
    if not text or not client_slug:
        return []
    query_vec = demo_salon_knowledge._local_text_embedding(text)
    if not query_vec:
        return []
    candidates: list[dict] = []
    for entry in demo_salon_knowledge._build_service_index():
        name = entry.get("name")
        if not name:
            continue
        best_score = 0.0
        for alias_tokens in entry.get("aliases", []):
            if not alias_tokens:
                continue
            alias_text = " ".join(alias_tokens)
            alias_vec = demo_salon_knowledge._local_text_embedding(alias_text)
            score = demo_salon_knowledge._cosine_similarity(query_vec, alias_vec)
            if score > best_score:
                best_score = score
        if best_score > 0:
            candidates.append({"score": best_score, "payload": {"canonical_name": name}})
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:limit]


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

    with patch(
        "app.services.demo_salon_knowledge._search_services_index",
        side_effect=_local_service_search,
    ):
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
