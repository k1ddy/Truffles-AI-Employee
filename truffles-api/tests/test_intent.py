import json
import time
from unittest.mock import patch

import httpx

from app.services.intent_service import (
    ESCALATION_INTENTS,
    REJECTION_INTENTS,
    Intent,
    _build_customer_name_hint_response_format,
    _build_policy_core_response_format,
    _build_service_query_hint_response_format,
    _build_specialist_hint_response_format,
    extract_customer_name_hint_llm,
    extract_service_query_hint_llm,
    interpret_expected_reply,
    is_frustration_message,
    is_human_request_message,
    is_opt_out_message,
    is_rejection,
    route_dialogue_controller,
    route_llm_policy_core,
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
        monkeypatch.setenv("OPENAI_API_KEY", "")
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

    def test_slot_mismatch_preserves_detected_slot(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "slot": "name",
            "value": "Лена",
            "confidence": 0.92,
            "reason": "name_provided",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps(payload, ensure_ascii=False)
            )
            result = interpret_expected_reply("Меня зовут Лена", expected_reply_type="time")

        assert result["ok"] is False
        assert result["error"] == "slot_mismatch"
        assert result["payload"]["slot"] == "datetime"
        assert result["payload"]["detected_slot"] == "name"
        assert result["payload"]["value"] == "Лена"


class TestPolicyCoreTimeoutRetry:
    @staticmethod
    def _policy_payload() -> dict:
        return {
            "intent": "booking",
            "action": "collect",
            "tool_action": "calendar.list_slots",
            "tool_args": {},
            "pack_refs": [],
            "language": "ru",
            "confidence": 0.8,
            "reason": "ask_time",
            "goal": "booking",
            "slots": {},
            "open_questions": ["datetime"],
            "expected_reply_type": "time",
        }

    def test_master_query_fact_without_service_fails_schema(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action": "info",
            "tool_args": {},
            "pack_refs": ["master"],
            "language": "ru",
            "confidence": 0.8,
            "reason": "master_lookup",
            "goal": "info",
            "slots": {"service": "", "datetime": "", "name": ""},
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core("Кто лучший мастер?")

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"

    def test_retries_once_after_timeout_and_succeeds(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_RETRY_ON_TIMEOUT",
            "1",
        )

        payload = self._policy_payload()
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                httpx.TimeoutException("timeout"),
                DummyResponse(json.dumps(payload)),
            ]
            result = route_llm_policy_core("Нужно время", expected_reply_type="time")

        assert result["ok"] is True
        assert result["error"] is None
        assert mock_llm.return_value.generate.call_count == 2

    def test_timeout_retry_switches_to_compact_payload(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_RETRY_ON_TIMEOUT",
            "1",
        )
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_COMPACT_TRIGGER_TIMEOUT_SECONDS",
            0.2,
        )
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_COMPACT_MESSAGE_MAX_CHARS",
            80,
        )

        payload = self._policy_payload()
        long_message = "Нужно забронировать услугу " + ("срочно " * 60)
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                httpx.TimeoutException("timeout"),
                DummyResponse(json.dumps(payload)),
            ]
            result = route_llm_policy_core(long_message, expected_reply_type="time")

        assert result["ok"] is True
        assert result["compact_input_used"] is True
        assert result["compact_retry_used"] is True
        assert mock_llm.return_value.generate.call_count == 2
        first_call_input = json.loads(
            mock_llm.return_value.generate.call_args_list[0].kwargs["messages"][1]["content"]
        )
        second_call_input = json.loads(
            mock_llm.return_value.generate.call_args_list[1].kwargs["messages"][1]["content"]
        )
        assert first_call_input["message"] == long_message
        assert len(second_call_input["message"]) <= 80
        assert second_call_input["message"] != long_message

    def test_timeout_retry_uses_fallback_model_when_primary_times_out(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_RETRY_ON_TIMEOUT",
            "1",
        )
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_MODEL",
            "gpt-primary",
        )
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_TIMEOUT_FALLBACK_MODEL",
            "gpt-fallback",
        )

        payload = self._policy_payload()
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                httpx.TimeoutException("timeout-1"),
                httpx.TimeoutException("timeout-2"),
                DummyResponse(json.dumps(payload)),
            ]
            result = route_llm_policy_core("Нужно время", expected_reply_type="time")

        assert result["ok"] is True
        assert result["error"] is None
        assert mock_llm.return_value.generate.call_count == 3
        models = [call.kwargs.get("model") for call in mock_llm.return_value.generate.call_args_list]
        assert models[:2] == ["gpt-primary", "gpt-primary"]
        assert models[2] == "gpt-fallback"

    def test_retries_once_after_transient_connection_error(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_RETRY_ON_TIMEOUT",
            "0",
        )
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_RETRY_ON_TRANSIENT",
            "1",
        )

        payload = self._policy_payload()
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                Exception("Connection refused while calling upstream provider"),
                DummyResponse(json.dumps(payload)),
            ]
            result = route_llm_policy_core("Нужно время", expected_reply_type="time")

        assert result["ok"] is True
        assert result["error"] is None
        assert mock_llm.return_value.generate.call_count == 2

    def test_uses_adaptive_timeout_when_pipeline_budget_is_tight(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_RETRY_ON_TIMEOUT",
            "0",
        )
        payload = self._policy_payload()
        timing_context = {
            "pipeline_deadline": time.monotonic() + 2.2,
            "pipeline_budget_ms": 2200,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Нужно время",
                expected_reply_type="time",
                timing_context=timing_context,
            )

        assert result["ok"] is True
        assert result["error"] is None
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        assert kwargs["timeout_seconds"] < 5.0
        assert kwargs["timeout_seconds"] >= 1.0

    def test_uses_micro_deadline_attempt_when_budget_below_min_timeout(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_RETRY_ON_TIMEOUT",
            "0",
        )
        payload = self._policy_payload()
        timing_context = {
            "pipeline_deadline": time.monotonic() + 0.9,
            "pipeline_budget_ms": 900,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Нужно время",
                expected_reply_type="time",
                timing_context=timing_context,
            )

        assert result["ok"] is True
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        assert kwargs["timeout_seconds"] < 1.2
        assert kwargs["timeout_seconds"] >= 0.3

    def test_uses_compact_payload_on_first_attempt_for_tight_timeout(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_COMPACT_TRIGGER_TIMEOUT_SECONDS",
            10.0,
        )
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_COMPACT_MESSAGE_MAX_CHARS",
            90,
        )
        payload = self._policy_payload()
        long_message = "Запишите меня на маникюр " + ("пожалуйста " * 40)
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(long_message, expected_reply_type="time")

        assert result["ok"] is True
        assert result["compact_input_used"] is True
        assert result["compact_retry_used"] is False
        policy_input = json.loads(mock_llm.return_value.generate.call_args.kwargs["messages"][1]["content"])
        assert len(policy_input["message"]) <= 90
        assert policy_input["message"] != long_message

    def test_returns_deadline_when_budget_below_min_policy_timeout(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        timing_context = {
            "pipeline_deadline": time.monotonic() + 0.2,
            "pipeline_budget_ms": 200,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            result = route_llm_policy_core(
                "Нужно время",
                expected_reply_type="time",
                timing_context=timing_context,
            )

        assert result["ok"] is False
        assert result["error"] == "deadline_exceeded"
        mock_llm.assert_not_called()

    def test_policy_core_includes_memory_payload_when_provided(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = self._policy_payload()
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Нужно время",
                expected_reply_type="time",
                memory_summary=("  Клиент хочет стрижку и просит завтра после 15:00. " * 12),
                memory_profile={
                    "consent_status": "granted",
                    "active_goal": "booking",
                    "expected_reply_type": "time",
                    "active_slots": ["service", "datetime", "service"],
                    "current_referents": {
                        "service": "маникюр",
                        "booking_ref": "ref-123",
                        "ignored": "skip",
                    },
                    "pending_question_contract": {
                        "slot": "datetime",
                        "expected_reply_type": "time",
                        "reason": "booking_followup",
                        "value": "завтра после 15",
                        "ignored": "skip",
                    },
                    "consult_state": {
                        "active": True,
                        "topic": "уход за волосами",
                        "question": "что лучше после окрашивания",
                        "questions": ["первый вопрос", "второй вопрос", "", 1],
                    },
                    "stored_keys": [
                        "preferred_master",
                        "preferred_master",
                        "parking_near",
                    ],
                    "retrieved_items": [
                        {"key": "preferred_master", "value": "Алия"},
                        {"key": "preferred_master", "value": "Алия"},
                        {
                            "key": "parking_note",
                            "value": "Рядом со входом",
                            "source": "booking_slot",
                        },
                        {"key": "", "value": "skip"},
                        {"value": "skip"},
                    ],
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        llm_messages = mock_llm.return_value.generate.call_args.kwargs["messages"]
        policy_input = json.loads(llm_messages[1]["content"])
        memory_payload = policy_input.get("memory")
        assert isinstance(memory_payload, dict)
        assert memory_payload.get("summary")
        assert len(memory_payload.get("summary")) <= 360
        assert memory_payload.get("profile", {}).get("consent_status") == "granted"
        assert memory_payload.get("profile", {}).get("active_goal") == "booking"
        assert memory_payload.get("profile", {}).get("expected_reply_type") == "time"
        assert memory_payload.get("profile", {}).get("active_slots") == ["service", "datetime"]
        assert memory_payload.get("profile", {}).get("stored_keys") == [
            "preferred_master",
            "parking_near",
        ]
        assert memory_payload.get("profile", {}).get("current_referents") == {
            "service": "маникюр",
            "booking_ref": "ref-123",
        }
        assert memory_payload.get("profile", {}).get("pending_question_contract") == {
            "slot": "datetime",
            "expected_reply_type": "time",
            "reason": "booking_followup",
            "value": "завтра после 15",
        }
        assert memory_payload.get("profile", {}).get("consult_state") == {
            "active": True,
            "topic": "уход за волосами",
            "question": "что лучше после окрашивания",
            "questions": ["первый вопрос", "второй вопрос"],
        }
        assert memory_payload.get("profile", {}).get("retrieved_items") == [
            {"key": "preferred_master", "value": "Алия"},
            {"key": "parking_note", "value": "Рядом со входом", "source": "booking_slot"},
        ]

    def test_retries_without_response_format_when_provider_rejects_it(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = self._policy_payload()
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                Exception("OpenAI API error: 400 - response_format json_schema is not supported"),
                DummyResponse(json.dumps(payload)),
            ]
            result = route_llm_policy_core("нужна запись")

        assert result["ok"] is True
        assert result["structured_output_enabled"] is True
        assert result["structured_output_fallback_used"] is True
        assert mock_llm.return_value.generate.call_count == 2
        first_kwargs = mock_llm.return_value.generate.call_args_list[0].kwargs
        second_kwargs = mock_llm.return_value.generate.call_args_list[1].kwargs
        assert isinstance(first_kwargs.get("response_format"), dict)
        assert "response_format" not in second_kwargs or second_kwargs.get("response_format") is None

    def test_policy_core_response_format_is_provider_compatible_and_keeps_dynamic_objects(self):
        response_format = _build_policy_core_response_format(["calendar.book_slot"])
        assert response_format["json_schema"]["strict"] is False
        schema = response_format["json_schema"]["schema"]
        assert schema["type"] == "object"
        assert schema["properties"]["tool_args"]["additionalProperties"] is True
        assert schema["properties"]["slots"]["additionalProperties"] == {"type": "string"}
        assert "entity_refs" in schema["properties"]
        assert "subject_kind" in schema["properties"]
        assert "capability" in schema["properties"]
        assert "temporal_scope" in schema["properties"]
        assert "resolution_mode" in schema["properties"]
        assert "resolver_id" in schema["properties"]
        assert "resolver_version" in schema["properties"]
        for keyword in ("allOf", "oneOf", "anyOf", "not", "enum"):
            assert keyword not in schema


class TestPolicyCoreErrorClassification:
    def test_maps_insufficient_quota_error(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = Exception(
                "OpenAI API error: 429 - "
                "{\"error\":{\"message\":\"quota\",\"type\":\"insufficient_quota\",\"code\":\"insufficient_quota\"}}"
            )
            result = route_llm_policy_core("нужна запись")

        assert result["ok"] is False
        assert result["error"] == "insufficient_quota"

    def test_maps_connection_error(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = Exception(
                "Connection refused while calling upstream provider"
            )
            result = route_llm_policy_core("нужна запись")

        assert result["ok"] is False
        assert result["error"] == "connection_error"

    def test_maps_model_not_found_error(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = Exception(
                "The model gpt-x does not exist"
            )
            result = route_llm_policy_core("нужна запись")

        assert result["ok"] is False
        assert result["error"] == "model_not_found"


class TestCustomerNameHint:
    def test_response_format_requires_all_declared_fields(self):
        specialist_schema = _build_specialist_hint_response_format()["json_schema"]["schema"]
        customer_schema = _build_customer_name_hint_response_format()["json_schema"]["schema"]
        service_schema = _build_service_query_hint_response_format()["json_schema"]["schema"]

        assert set(specialist_schema["required"]) == set(specialist_schema["properties"].keys())
        assert set(customer_schema["required"]) == set(customer_schema["properties"].keys())
        assert set(service_schema["required"]) == set(service_schema["properties"].keys())

    def test_extracts_explicit_customer_name(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "customer_name": "Лена",
            "confidence": 0.95,
            "reason": "explicit_name_marker",
            "language": "ru",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = extract_customer_name_hint_llm(
                "Запишите меня к Айгерим на маникюр, имя Лена.",
                specialist_name="Айгерим",
            )

        assert result["ok"] is True
        assert result["customer_name"] == "Лена"
        assert result["error"] is None

    def test_rejects_name_matching_specialist(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "customer_name": "Айгерим",
            "confidence": 0.99,
            "reason": "name_found",
            "language": "ru",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = extract_customer_name_hint_llm(
                "Запишите меня к Айгерим на маникюр.",
                specialist_name="Айгерим",
            )

        assert result["ok"] is False
        assert result["customer_name"] is None
        assert result["error"] == "matches_specialist"


class TestServiceQueryHint:
    def test_extracts_explicit_service_query(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "service_query": "маникюр",
            "confidence": 0.93,
            "reason": "explicit_service_in_text",
            "language": "ru",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = extract_service_query_hint_llm(
                "Запиши меня завтра на маникюр к Айгерим",
            )

        assert result["ok"] is True
        assert result["service_query"] == "маникюр"
        assert result["error"] is None

    def test_returns_low_confidence_when_service_missing(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "service_query": None,
            "confidence": 0.21,
            "reason": "service_not_explicit",
            "language": "ru",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = extract_service_query_hint_llm(
                "Запиши меня к Айгерим завтра в 15:00",
            )

        assert result["ok"] is False
        assert result["service_query"] is None
        assert result["error"] == "low_confidence_or_empty"
