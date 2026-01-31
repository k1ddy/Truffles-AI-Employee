import json
import time
from unittest.mock import patch

from app.services.intent_service import (
    ESCALATION_INTENTS,
    REJECTION_INTENTS,
    Intent,
    interpret_expected_reply,
    is_frustration_message,
    is_human_request_message,
    is_opt_out_message,
    is_rejection,
    route_dialogue_controller,
    should_escalate,
)


class DummyResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class TestIntentEnum:
    def test_all_intents_defined(self):
        expected = {
            "human_request",
            "frustration",
            "rejection",
            "question",
            "greeting",
            "thanks",
            "out_of_domain",
            "other",
        }
        actual = {i.value for i in Intent}
        assert actual == expected


class TestShouldEscalate:
    def test_human_request_escalates(self):
        assert should_escalate(Intent.HUMAN_REQUEST) is True

    def test_frustration_escalates(self):
        assert should_escalate(Intent.FRUSTRATION) is True

    def test_rejection_does_not_escalate(self):
        assert should_escalate(Intent.REJECTION) is False

    def test_question_does_not_escalate(self):
        assert should_escalate(Intent.QUESTION) is False

    def test_greeting_does_not_escalate(self):
        assert should_escalate(Intent.GREETING) is False

    def test_thanks_does_not_escalate(self):
        assert should_escalate(Intent.THANKS) is False

    def test_other_does_not_escalate(self):
        assert should_escalate(Intent.OTHER) is False


class TestIsRejection:
    def test_rejection_is_rejection(self):
        assert is_rejection(Intent.REJECTION) is True

    def test_human_request_not_rejection(self):
        assert is_rejection(Intent.HUMAN_REQUEST) is False

    def test_question_not_rejection(self):
        assert is_rejection(Intent.QUESTION) is False


class TestEscalationIntents:
    def test_only_two_escalation_intents(self):
        assert len(ESCALATION_INTENTS) == 2
        assert Intent.HUMAN_REQUEST in ESCALATION_INTENTS
        assert Intent.FRUSTRATION in ESCALATION_INTENTS


class TestRejectionIntents:
    def test_only_one_rejection_intent(self):
        assert len(REJECTION_INTENTS) == 1
        assert Intent.REJECTION in REJECTION_INTENTS


class TestHumanRequestHeuristics:
    def test_detects_manager_request(self):
        assert is_human_request_message("можете позвать менеджера пожалуйста") is True

    def test_detects_live_operator_request(self):
        assert is_human_request_message("хочу поговорить с живым человеком") is True

    def test_ignores_regular_question(self):
        assert is_human_request_message("сколько стоит маникюр?") is False


class TestOptOutHeuristics:
    def test_detects_opt_out(self):
        assert is_opt_out_message("я не хочу чтобы ты писал мне") is True
        assert is_opt_out_message("отпишись") is True
        assert is_opt_out_message("заткнись") is True
        assert is_opt_out_message("я не хочу чтобы ты писал мне, pfrnyb, иди нахуй") is True

    def test_ignores_regular_text(self):
        assert is_opt_out_message("сколько стоит маникюр?") is False


class TestFrustrationHeuristics:
    def test_detects_frustration(self):
        assert is_frustration_message("заткнись") is True
        assert is_frustration_message("заебал") is True

    def test_ignores_regular_text(self):
        assert is_frustration_message("спасибо") is False


class TestDialogueControllerOffline:
    def test_returns_fixed_class_and_goal_without_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            result = route_dialogue_controller("Привет")

        assert result["error"] == "no_api_key"
        assert result["ok"] is False
        payload = result["payload"]
        assert payload["class"] == "other"
        assert payload["goal"] == "other"
        assert payload["controller_error"] == "no_api_key"
        mock_llm.assert_not_called()


class TestDialogueControllerBudget:
    def test_budget_deadline_skips_llm(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        timing_context = {"pipeline_deadline": time.monotonic() - 1.0, "pipeline_budget_ms": 10}
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            result = route_dialogue_controller("Привет", timing_context=timing_context)

        assert result["error"] == "deadline_exceeded"
        assert result["ok"] is False
        payload = result["payload"]
        assert payload["controller_error"] == "deadline_exceeded"
        mock_llm.assert_not_called()


class TestDialogueControllerSchema:
    def test_valid_schema(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "class": "booking",
            "goal": "booking",
            "intents": ["booking"],
            "slots": {"service_query": "service"},
            "followups": [],
            "safety_flags": [],
            "confidence": 0.7,
            "reason": "booking request",
            "carryover": {},
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps(payload)
            )
            result = route_dialogue_controller("I want to book")

        assert result["ok"] is True
        assert result["error"] is None
        assert result["payload"]["class"] == "booking"
        assert result["payload"]["goal"] == "booking"

    def test_invalid_schema(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps({"goal": "booking", "confidence": 0.4})
            )
            result = route_dialogue_controller("I want to book")

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"


class TestAnswerInterpreterSchema:
    def test_valid_schema(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "slot": "name",
            "value": "Alex",
            "confidence": 0.6,
            "reason": "name provided",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps(payload)
            )
            result = interpret_expected_reply("Alex", expected_reply_type="name")

        assert result["ok"] is True
        assert result["error"] is None
        assert result["payload"]["slot"] == "name"
        assert result["payload"]["value"] == "Alex"

    def test_invalid_schema(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps({"slot": 123, "confidence": 0.5})
            )
            result = interpret_expected_reply("Alex", expected_reply_type="name")

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
