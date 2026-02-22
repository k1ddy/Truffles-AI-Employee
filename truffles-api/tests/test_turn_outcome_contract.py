from pydantic import ValidationError

from app.schemas.turn_outcome import TurnOutcome


def test_turn_outcome_normalizes_tokens_and_metadata():
    outcome = TurnOutcome(
        action=" Reply ",
        intent=" Booking ",
        source=" Tool_Registry ",
        tool_action=" Catalog.Service_Query ",
        tool_decision=" Services_Overview ",
        expected_reply_type=" Service_Choice ",
        expected_reply_reason="services_overview",
        followup_prompt="Выберите услугу, пожалуйста.",
    )

    payload = outcome.to_metadata()

    assert payload["action"] == "reply"
    assert payload["intent"] == "booking"
    assert payload["source"] == "tool_registry"
    assert payload["tool_action"] == "catalog.service_query"
    assert payload["tool_decision"] == "services_overview"
    assert payload["expected_reply_type"] == "service_choice"
    assert payload["expected_reply_reason"] == "services_overview"
    assert payload["observability"]["reply_observed"] is False


def test_turn_outcome_rejects_invalid_expected_reply_type():
    try:
        TurnOutcome(expected_reply_type="unsupported")
    except ValidationError as exc:
        assert "expected_reply_type_invalid" in str(exc)
    else:
        raise AssertionError("ValidationError was not raised")
