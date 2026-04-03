import inspect
import json
import time
from unittest.mock import patch
from uuid import uuid4

import httpx

from app.schemas.capabilities import CapabilitiesPayload
from app.schemas.consult import ConsultPlaybook
from app.schemas.intent import validate_llm_policy_core_output
from app.services.capabilities_runtime import RuntimeCapabilities, set_runtime_capabilities
from app.services.intent_service import (
    ESCALATION_INTENTS,
    REJECTION_INTENTS,
    DomainIntent,
    Intent,
    _build_customer_name_hint_response_format,
    _build_policy_core_contract_repair_instruction,
    _build_service_query_hint_response_format,
    _build_specialist_hint_response_format,
    _load_policy_core_prompt,
    _normalize_policy_core_memory_profile,
    _policy_core_context_service_hint,
    _resolve_model_temperature,
    _resolve_policy_core_max_tokens_with_cap,
    _resolve_policy_core_reasoning_effort,
    _sanitize_policy_core_payload,
    _validate_policy_core_runtime_contract,
    classify_domain_with_scores,
    classify_intent,
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
from app.services.policy_prompt_snapshot_service import load_policy_core_compact_prompt_snapshot
from app.services.policy_vocabulary_snapshot_service import build_policy_core_response_format


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


def test_classify_intent_no_longer_contains_override_short_circuit():
    source = inspect.getsource(classify_intent)

    assert "_resolve_override_intent" not in source
    assert "_resolve_intent_override_flag" not in source


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


class TestDialogueControllerRetired:
    def test_returns_explicit_shadow_owner_removed_error(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            result = route_dialogue_controller("Привет")

        assert result["error"] == "secondary_semantic_owner_removed"
        assert result["ok"] is False
        payload = result["payload"]
        assert payload["class"] is None
        assert payload["goal"] is None
        assert payload["controller_error"] == "secondary_semantic_owner_removed"
        mock_llm.assert_not_called()


def test_route_dialogue_controller_no_longer_contains_override_short_circuit():
    assert "_resolve_dialogue_controller_override" not in inspect.getsource(route_dialogue_controller)


class TestDialogueControllerLegacySurface:
    def test_carryover_payload_is_preserved_for_legacy_callers(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            result = route_dialogue_controller(
                "Привет",
                carryover={"class": "booking", "intents": ["booking"], "info_sections": ["pricing"]},
            )

        assert result["error"] == "secondary_semantic_owner_removed"
        assert result["payload"]["carryover"]["class"] == "booking"
        assert result["payload"]["carryover"]["intents"] == ["booking"]
        assert result["payload"]["carryover"]["info_sections"] == ["pricing"]
        mock_llm.assert_not_called()


def test_classify_domain_with_scores_no_longer_contains_override_short_circuit():
    assert "_resolve_domain_routing_override" not in inspect.getsource(classify_domain_with_scores)


class TestPolicyCoreOverride:
    def test_route_llm_policy_core_no_longer_contains_override_short_circuit(self):
        source = inspect.getsource(route_llm_policy_core)

        assert "_resolve_policy_core_override" not in source

    def test_route_llm_policy_core_returns_no_api_key_without_override_escape(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            result = route_llm_policy_core("Хочу поговорить с менеджером")

        assert result["ok"] is False
        assert result["error"] == "no_api_key"
        assert result["attempted"] is False
        mock_llm.assert_not_called()


class TestAnswerInterpreterRetired:
    def test_returns_explicit_shadow_owner_removed_error(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            result = interpret_expected_reply("Alex", expected_reply_type="name")

        assert result["ok"] is False
        assert result["error"] == "secondary_semantic_owner_removed"
        assert result["payload"] == {
            "slot": "name",
            "detected_slot": "",
            "value": "",
            "confidence": 0.0,
            "reason": "secondary_semantic_owner_removed",
        }
        mock_llm.assert_not_called()

    def test_unsupported_slot_still_returns_explicit_removed_error(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            result = interpret_expected_reply("Alex", expected_reply_type="unsupported")

        assert result["ok"] is False
        assert result["error"] == "secondary_semantic_owner_removed"
        assert result["payload"]["slot"] == ""
        mock_llm.assert_not_called()


class TestPolicyCoreTimeoutRetry:
    @staticmethod
    def _policy_payload() -> dict:
        return {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "entity_refs": [],
            "referents": {},
            "language": "ru",
            "confidence": 0.8,
            "reason": "ask_time",
            "goal": "booking",
            "slots": {},
            "next_question": None,
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "subject_kind": None,
            "capability": None,
            "temporal_scope": None,
            "resolution_mode": None,
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
            "expected_reply_type": "time",
        }

    def test_master_query_fact_without_service_fails_schema(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": [],
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

    def test_master_query_fact_with_referent_service_passes_schema(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": [],
            "language": "ru",
            "confidence": 0.8,
            "reason": "master_lookup",
            "goal": "info",
            "slots": {"service": "", "datetime": "", "name": "", "phone": ""},
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "entity_refs": [
                {
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                    "value": "маникюр",
                    "confidence": 0.94,
                }
            ],
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "subject_kind": "service",
            "capability": "portfolio",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": "master_lookup",
            "resolver_version": "2026-03-25",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core("Кто делает маникюр?")

        assert result["ok"] is True
        assert "semantic_frame" not in result
        assert result["payload"]["schema_version"] == "semantic_decision.v1"
        assert result["payload"]["grounding_requirements"]["referents"]["service"] == {
            "value": "маникюр",
            "entity_id": "svc:manicure",
            "entity_type": "service",
            "source_ref": "message",
        }
        assert result["binding"] == {
            "tool_action": "info",
            "tool_args": {},
        }
        assert result["binding_plan"]["schema_version"] == "binding_plan.v1"
        assert result["binding_plan"]["decision_id"] == result["payload"]["decision_id"]
        assert result["binding_plan"]["binding_outcome_type"] == "tool_call"
        assert result["binding_plan"]["selected_tool_or_workflow_ref"] == "info"
        assert result["binding_plan"]["resolved_args"] == {}
        assert "tool_args" not in result["payload"]

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
        assert result["compact_retry_used"] is False
        assert mock_llm.return_value.generate.call_count == 2
        first_call_input = json.loads(
            mock_llm.return_value.generate.call_args_list[0].kwargs["messages"][1]["content"]
        )
        second_call_input = json.loads(
            mock_llm.return_value.generate.call_args_list[1].kwargs["messages"][1]["content"]
        )
        assert mock_llm.return_value.generate.call_args_list[0].kwargs["max_tokens"] == 560
        assert mock_llm.return_value.generate.call_args_list[1].kwargs["max_tokens"] == 560
        assert len(first_call_input["message"]) <= 80
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
            "primary-model",
        )
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_TIMEOUT_FALLBACK_MODEL",
            "gpt-5.4-nano-2026-03-17",
        )
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_REASONING_EFFORT",
            "low",
        )
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_GPT5_MIN_MAX_TOKENS",
            400,
        )
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_FALLBACK_TIMEOUT_SECONDS",
            6.0,
        )

        payload = self._policy_payload()
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                httpx.TimeoutException("timeout-1"),
                DummyResponse(json.dumps(payload)),
            ]
            result = route_llm_policy_core("Нужно время", expected_reply_type="time")

        assert result["ok"] is True
        assert result["error"] is None
        assert mock_llm.return_value.generate.call_count == 2
        models = [call.kwargs.get("model") for call in mock_llm.return_value.generate.call_args_list]
        assert models == ["primary-model", "gpt-5.4-nano-2026-03-17"]
        fallback_kwargs = mock_llm.return_value.generate.call_args_list[1].kwargs
        assert fallback_kwargs["reasoning_effort"] == "low"
        assert fallback_kwargs["max_tokens"] >= 400
        assert fallback_kwargs["temperature"] is None
        assert fallback_kwargs["timeout_seconds"] == 6.0

    def test_policy_core_gpt5_compatibility_helpers_use_chat_safe_defaults(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_REASONING_EFFORT",
            "minimal",
        )

        assert _resolve_policy_core_reasoning_effort("gpt-5.4-nano-2026-03-17") == "low"
        assert _resolve_policy_core_reasoning_effort("legacy-model") is None
        assert _resolve_model_temperature("gpt-5.4-nano-2026-03-17") is None
        assert _resolve_model_temperature("legacy-model") == 0.0

    def test_policy_core_payload_sanitizer_drops_invalid_optional_tool_args(self):
        payload, sanitized = _sanitize_policy_core_payload(
            {
                "intent": "booking",
                "action": "fact",
                "tool_action": "calendar.list_slots",
                "tool_args": {
                    "service_query": "Маникюр",
                    "date": "tomorrow",
                    "duration_min": "null? nope invalid?",
                },
            }
        )

        assert sanitized is True
        assert "tool_args" not in payload

    def test_policy_core_route_salvages_invalid_optional_tool_args(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "fact",
            "tool_action_hint": "calendar.list_slots",
            "tool_args": {
                "service_query": "Маникюр",
                "date": "tomorrow",
                "duration_min": "null? nope invalid?",
            },
            "pack_refs": [],
            "slots": {"service": "Маникюр"},
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "booking_availability_for_tomorrow",
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "slot_state",
                }
            },
            "subject_kind": "service",
            "capability": "live_availability",
            "temporal_scope": "day",
            "resolution_mode": "live_calendar",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Можно записаться на завтра?",
                expected_reply_type="time",
            )

        assert result["ok"] is True
        assert result["tool_args_sanitized"] is True
        assert result["binding"]["tool_args"] == {"service_query": "Маникюр"}
        assert result["binding_plan"]["binding_outcome_type"] == "tool_call"
        assert result["binding_plan"]["selected_tool_or_workflow_ref"] == "calendar.list_slots"
        assert result["binding_plan"]["resolved_args"] == {"service_query": "Маникюр"}

    def test_policy_core_route_rejects_collect_tool_action_hint_conflict(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "handoff",
            "pack_refs": [],
            "slots": {"service": "Маникюр"},
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "bad_collect_binding",
            "subject_kind": "service",
            "capability": "bookability",
            "temporal_scope": "day",
            "resolution_mode": "ask_about_requested_slot",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core("Можно записаться на завтра?")

        assert result["ok"] is False
        assert result["error"] == "invalid_projection"
        assert result["projection_error"] == "collect_tool_action_hint_conflict"

    def test_policy_core_repairs_booking_manage_reference_contract(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "check_booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "reason": "calendar_get_booking_collect_reference",
            "subject_kind": "booking",
            "capability": "booking_manage",
            "temporal_scope": "none",
            "resolution_mode": "direct",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
        }
        repaired_payload = {
            **invalid_payload,
            "action": "fact",
            "tool_action_hint": "calendar.get_booking",
            "reason": "calendar_get_booking_collect_reference",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core("Проверьте мою запись")

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is True
        assert result["contract_repair_reason"] == "llm_policy_core_error:booking_manage_reference_action_invalid"
        assert result["binding"]["tool_action"] == "calendar.get_booking"
        assert result["binding_plan"]["binding_outcome_type"] == "tool_call"
        assert result["binding_plan"]["selected_tool_or_workflow_ref"] == "calendar.get_booking"
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["tool_action_hint"] == "calendar.get_booking"

    def test_policy_core_repairs_booking_commit_action_contract(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "calendar.book_slot",
            "pack_refs": [],
            "slots": {
                "service": "Маникюр",
                "datetime": "2026-04-04T15:00:00+05:00",
                "name": "Алина",
            },
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "reason": "booking_commit_ready_after_name",
            "subject_kind": "service",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "resolution_mode": "live_calendar",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": "fill_requested_slot",
        }
        repaired_payload = {
            **invalid_payload,
            "action": "fact",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Алина",
                current_goal="booking",
                memory_summary=(
                    "user: Хочу записаться на маникюр assistant: На какую дату и время вам удобно? "
                    "user: Завтра в 15:00 assistant: Как вас зовут? user: Алина"
                ),
                memory_profile={
                    "slot_state": {
                        "service": "Маникюр",
                        "datetime": "2026-04-04T15:00:00+05:00",
                    },
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                    },
                    "semantic_contract": {
                        "subject_kind": "service",
                        "capability": "bookability",
                        "resolution_mode": "referent_followup",
                        "referents": {
                            "service": {
                                "value": "Маникюр",
                                "entity_id": "svc:manicure",
                                "source_ref": "carryover",
                                "entity_type": "service",
                            }
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is True
        assert result["contract_repair_reason"] == "llm_policy_core_error:booking_commit_action_invalid"
        assert result["binding"]["tool_action"] == "calendar.book_slot"
        assert result["binding_plan"]["binding_outcome_type"] == "tool_call"
        assert result["binding_plan"]["selected_tool_or_workflow_ref"] == "calendar.book_slot"
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["tool_action_hint"] == "calendar.book_slot"

    def test_policy_core_repairs_generic_info_interrupt_followup_contract(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "pricing",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["pricing"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "reason": "user_asks_price_for_known_service",
            "subject_kind": "service",
            "capability": "pricing",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "active_question_relation": "generic_info_interrupt",
            "pending_question_act": None,
            "pending_question_target": None,
        }
        repaired_payload = {
            **invalid_payload,
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Какая цена?",
                expected_reply_type="time",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is True
        assert result["contract_repair_reason"] == "llm_policy_core_error:generic_info_interrupt_expected_reply_invalid"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert result["payload"]["missing_information"]["pending_question_act"] == "ask_about_requested_slot"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"

    def test_policy_core_repairs_catalog_location_interrupt_with_exact_parking_pack_ref(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "catalog.location",
            "pack_refs": [],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "reason": "parking_question_interrupt_during_booking_time_collect_preserve_requested_slot_contract",
            "subject_kind": "service",
            "capability": "location",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "active_question_relation": "generic_info_interrupt",
            "pending_question_act": None,
            "pending_question_target": None,
        }
        repaired_payload = {
            **invalid_payload,
            "pack_refs": ["parking"],
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Есть ли парковка рядом?",
                expected_reply_type="time",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is True
        assert result["contract_repair_reason"] == "llm_policy_core_error:generic_info_interrupt_expected_reply_invalid"
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["parking"]
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"

    def test_policy_core_repairs_active_media_interrupt_to_preserve_booking_resume(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "consult",
            "action": "collect",
            "tool_action_hint": "consult",
            "pack_refs": ["style_reference"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "media",
            "next_question": "media",
            "open_questions": ["media"],
            "needs_manager": False,
            "reason": "user_offers_photos_for_style_reference_continuation_and_photo_needed_for_style_alignment_with_specialist_query",
            "goal": "booking",
            "entity_refs": [
                {
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                    "value": "маникюр",
                    "confidence": 0.91,
                }
            ],
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "service",
            "capability": "consultation",
            "temporal_scope": "none",
            "resolution_mode": "direct",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "resolver_id": None,
            "resolver_version": None,
        }
        repaired_payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["master"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "user_asked_master_with_active_booking_media_interrupt",
            "goal": "booking",
            "entity_refs": [
                {
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                    "value": "маникюр",
                    "confidence": 0.91,
                }
            ],
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "service",
            "capability": "portfolio",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": "master_lookup",
            "resolver_version": "2026-04-01",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Кто из специалистов делает маникюр?",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "media",
                        "next_question": "media",
                        "open_questions": ["media"],
                        "reason": "user_offers_photos_for_style_reference",
                    },
                    "resume_pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "service",
                        "resolution_mode": "direct",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:active_followup_interrupt_reclassification_required"
        )
        assert result["binding"]["tool_action"] == "info"
        assert result["binding_plan"]["selected_tool_or_workflow_ref"] == "info"
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"

    def test_policy_core_repairs_active_media_master_query_live_availability_interrupt(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "master_query",
            "action": "collect",
            "tool_action_hint": "calendar.list_slots",
            "pack_refs": [],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "user_asks_specialists_for_service_need_time_to_check_availability",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "specialist",
            "capability": "live_availability",
            "temporal_scope": "none",
            "resolution_mode": "live_calendar",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "specialist_availability_followup",
        }
        repaired_payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["master"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "user_asked_master_with_active_booking_media_interrupt",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "service",
            "capability": "portfolio",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": "master_lookup",
            "resolver_version": "2026-04-01",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Кто из специалистов делает маникюр?",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "media",
                        "next_question": "media",
                        "open_questions": ["media"],
                        "reason": "user_offers_photos_for_style_reference",
                    },
                    "resume_pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "service",
                        "resolution_mode": "direct",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:active_followup_master_query_reclassification_required"
        )
        assert result["binding"]["tool_action"] == "info"
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"

    def test_policy_core_rejects_master_query_time_collect_during_active_media_followup(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "master_query",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "user_asks_specialists_for_service_need_time_to_check_availability",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "specialist",
            "capability": "live_availability",
            "temporal_scope": "none",
            "resolution_mode": "live_calendar",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "specialist_availability_followup",
        }
        repaired_payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["master"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "user_asked_master_with_active_booking_media_interrupt",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "service",
            "capability": "portfolio",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Кто из специалистов делает маникюр?",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "media",
                        "next_question": "media",
                        "open_questions": ["media"],
                        "reason": "user_offers_photos_for_style_reference",
                    },
                    "resume_pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:active_followup_master_query_reclassification_required"
        )
        assert result["binding"]["tool_action"] == "info"
        assert result["payload"]["requested_outcome"] == "fact"

    def test_policy_core_repairs_active_booking_live_availability_followup_from_master_query(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "master_query",
            "action": "collect",
            "tool_action_hint": "calendar.list_slots",
            "pack_refs": [],
            "slots": {"service": "маникюр", "datetime": "11:30"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "candidate_time_availability_followup_needs_date",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "service",
            "capability": "live_availability",
            "temporal_scope": "specific_time",
            "resolution_mode": "clarify_missing_time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }
        repaired_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр", "datetime": "11:30"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "candidate_time_availability_followup_needs_date",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "booking",
            "capability": "live_availability",
            "temporal_scope": "specific_time",
            "resolution_mode": "clarify_missing_time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": "booking_availability_followup",
            "resolver_version": "2026-04-03",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Есть свободные слоты на 11:30?",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "after 10:00"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр", "datetime": "after 10:00"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "generic_info_interrupt",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "service",
                        "resolution_mode": "clarify_missing_time",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["compact_retry_used"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["binding"]["tool_action"] == "collect"
        assert result["payload"]["requested_outcome"] == "collect"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "booking"
        assert result["payload"]["capability_id"] == "live_availability"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"

    def test_policy_core_repairs_active_booking_temporal_clue_followup_into_slot_constraint(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "candidate_weekday_daypart_followup_needs_exact_slot",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "service",
            "capability": "bookability",
            "temporal_scope": "weekday",
            "resolution_mode": "ask_about_requested_slot",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
        }
        repaired_payload = {
            **invalid_payload,
            "subject_kind": "booking",
            "pending_question_act": "slot_constraint",
            "active_question_relation": "slot_constraint",
            "alternate_datetime": "пятницу утром",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "А как насчет пятницы на утро?",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "service",
                        "resolution_mode": "ask_about_requested_slot",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:active_booking_temporal_clue_followup_reclassification_required"
        )
        assert result["binding"]["tool_action"] == "collect"
        assert result["payload"]["requested_outcome"] == "collect"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "booking"
        assert result["payload"]["grounding_requirements"]["temporal_scope"] == "weekday"
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "пятницу утром"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert result["payload"]["missing_information"]["pending_question_act"] == "slot_constraint"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "slot_constraint"

    def test_policy_core_repairs_active_booking_specialist_preference_into_referent_followup(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "named_specialist_preference_during_booking_time_collect",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "specialist": {
                    "value": "Айгерим",
                    "entity_id": "spec:aigerim",
                    "entity_type": "specialist",
                    "source_ref": "user",
                },
            },
            "subject_kind": "service",
            "capability": "bookability",
            "temporal_scope": "date_range",
            "resolution_mode": "ask_about_requested_slot",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
        }
        repaired_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "named_specialist_preference_during_booking_time_collect",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "specialist": {
                    "value": "Айгерим",
                    "entity_id": "spec:aigerim",
                    "entity_type": "specialist",
                    "source_ref": "user",
                },
            },
            "subject_kind": "specialist",
            "capability": "bookability",
            "temporal_scope": "date_range",
            "resolution_mode": "referent_followup",
            "pending_question_act": None,
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
            "resolver_id": "booking_specialist_followup",
            "resolver_version": "2026-04-03",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Мне нужен мастер Айгерим.",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "service",
                        "resolution_mode": "ask_about_requested_slot",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:active_booking_specialist_followup_reclassification_required"
        )
        assert result["binding"]["tool_action"] == "collect"
        assert result["payload"]["requested_outcome"] == "collect"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "specialist"
        assert result["payload"]["grounding_requirements"]["resolution_mode"] == "referent_followup"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert result["payload"]["missing_information"]["pending_question_target"] == "specialist"
        assert result["payload"]["missing_information"]["active_question_relation"] == "referent_followup"
        assert result["payload"]["grounding_requirements"]["referents"]["specialist"] == {
            "value": "Айгерим",
            "entity_id": "spec:aigerim",
            "entity_type": "specialist",
            "source_ref": "user",
        }

    def test_policy_core_specialist_preference_preempts_temporal_clue_repair_during_active_booking(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр", "datetime": None},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "active_booking_named_specialist_after_candidate_day",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "specialist": {
                    "value": "Айгерим",
                    "entity_id": "spec:aigerim",
                    "entity_type": "specialist",
                    "source_ref": "user_utterance",
                },
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "day",
            "alternate_datetime": "завтра",
            "resolution_mode": "ask_about_requested_slot",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
        }
        repaired_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "active_booking_named_specialist_after_candidate_day",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "specialist": {
                    "value": "Айгерим",
                    "entity_id": "spec:aigerim",
                    "entity_type": "specialist",
                    "source_ref": "user_utterance",
                },
            },
            "subject_kind": "specialist",
            "capability": "bookability",
            "temporal_scope": "day",
            "resolution_mode": "referent_followup",
            "pending_question_act": None,
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
            "resolver_id": "booking_specialist_followup",
            "resolver_version": "2026-04-03",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Я бы хотела записаться к Айгерим.",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "tomorrow"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр", "datetime": "tomorrow"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "booking",
                        "temporal_scope": "day",
                        "resolution_mode": "ask_about_requested_slot",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:active_booking_specialist_followup_reclassification_required"
        )
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "specialist"
        assert result["payload"]["grounding_requirements"]["resolution_mode"] == "referent_followup"
        assert result["payload"]["missing_information"]["pending_question_target"] == "specialist"
        assert result["payload"]["missing_information"]["active_question_relation"] == "referent_followup"

    def test_policy_core_repairs_active_booking_generic_specialist_query_into_master_interrupt(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "user_requests_specialist_for_known_service_manicure_query_with_booking_continuity",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "specialist": None,
            },
            "subject_kind": "specialist",
            "capability": "bookability",
            "temporal_scope": "none",
            "resolution_mode": "referent_followup",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
        }
        repaired_payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["master"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "user_asked_master_with_active_booking_interrupt",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "service",
            "capability": "portfolio",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": "master_lookup",
            "resolver_version": "2026-04-03",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Какой специалист будет делать маникюр?",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр", "datetime": "после 17:00"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "service",
                        "resolution_mode": "ask_about_requested_slot",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:active_booking_generic_specialist_query_reclassification_required"
        )
        assert result["binding"]["tool_action"] == "info"
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["master"]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "generic_info_interrupt"

    def test_policy_core_rejects_master_query_collect_during_active_booking_availability_followup(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "master_query",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр", "datetime": "11:30"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "candidate_time_availability_followup_needs_date",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "specialist",
            "capability": "live_availability",
            "temporal_scope": "specific_time",
            "resolution_mode": "clarify_missing_time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }
        repaired_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр", "datetime": "11:30"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "candidate_time_availability_followup_needs_date",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "booking",
            "capability": "live_availability",
            "temporal_scope": "specific_time",
            "resolution_mode": "clarify_missing_time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Есть свободные слоты на 11:30?",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "after 10:00"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр", "datetime": "after 10:00"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "generic_info_interrupt",
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:active_booking_live_availability_reclassification_required"
        )
        assert result["binding"]["tool_action"] == "collect"
        assert result["payload"]["requested_outcome"] == "collect"

    def test_policy_core_reclassifies_master_query_carryover_mismatch_during_active_media_followup(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["master"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "media",
            "next_question": "media",
            "open_questions": ["media"],
            "needs_manager": False,
            "reason": "user_asked_master_with_active_booking_media_interrupt",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "specialist",
            "capability": "bookability",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
        }
        repaired_payload = {
            **invalid_payload,
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "active_question_relation": "generic_info_interrupt",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Кто из специалистов делает маникюр?",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "media",
                        "next_question": "media",
                        "open_questions": ["media"],
                        "reason": "user_offers_photos_for_style_reference",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                    },
                    "resume_pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:active_followup_master_query_reclassification_required"
        )
        assert result["binding"]["tool_action"] == "info"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["active_question_relation"] == "generic_info_interrupt"

    def test_policy_core_repairs_invalid_master_query_consult_tool_action_during_active_media_followup(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "consult",
            "pack_refs": [],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "fact_side_specialist_question_interrupt_preserve_resume_datetime_collect_contract",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_message",
                }
            },
            "subject_kind": "specialist",
            "capability": "live_availability",
            "temporal_scope": "none",
            "resolution_mode": "direct",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
        }
        repaired_payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["master"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "user_asked_master_with_active_booking_media_interrupt",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "specialist",
            "capability": "bookability",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Кто из специалистов делает маникюр?",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "media",
                        "next_question": "media",
                        "open_questions": ["media"],
                        "reason": "user_offers_photos_for_style_reference",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                    },
                    "resume_pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:active_followup_master_query_reclassification_required"
        )
        assert result["binding"]["tool_action"] == "info"
        assert result["payload"]["missing_information"]["active_question_relation"] == "generic_info_interrupt"

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
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_TIMEOUT_FALLBACK_MODEL",
            "",
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

    def test_sanitizes_service_query_shadow_to_referent_for_policy_fact(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = self._policy_payload()
        invalid_payload.update(
            {
                "intent": "pricing",
                "action": "fact",
                "tool_action_hint": "catalog.service_query",
                "tool_args": {"service_query": "маникюр с дизайном"},
                "pack_refs": [],
                "slots": {"service": "маникюр"},
                "next_question": "name",
                "open_questions": ["name"],
                "needs_manager": False,
                "reason": "pricing_interrupt_keep_name_collect",
                "referents": {
                    "service": {
                        "value": "маникюр",
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                },
                "subject_kind": "service",
                "capability": "pricing",
                "temporal_scope": "specific_time",
                "resolution_mode": "policy_fact",
                "pending_question_act": "fill_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "generic_info_interrupt",
            }
        )
        repaired_payload = {
            **invalid_payload,
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Сколько стоит маникюр с дизайном?",
                expected_reply_type="name",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "завтра 15:00"},
                memory_profile={
                    "active_goal": "booking",
                    "current_referents": {"service": "маникюр"},
                    "pending_question_contract": {
                        "next_question": "name",
                        "open_questions": ["name"],
                        "expected_reply_type": "name",
                        "reason": "collect:name",
                        "pending_question_act": "fill_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "fill_requested_slot",
                    },
                },
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is True
        assert result["contract_repair_reason"] == "llm_policy_core_error:generic_info_interrupt_expected_reply_invalid"
        assert result["tool_args_sanitized"] is True
        assert result["binding"]["tool_args"] == {"service_query": "маникюр"}

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
            20.0,
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
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        policy_input = json.loads(kwargs["messages"][1]["content"])
        assert kwargs["max_tokens"] == 560
        assert len(policy_input["message"]) <= 90
        assert policy_input["message"] != long_message

    def test_check_booking_retry_caps_compact_tokens_after_timeout(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            "app.services.intent_service.POLICY_CORE_RETRY_ON_TIMEOUT",
            "1",
        )

        payload = self._policy_payload()
        payload.update(
            {
                "intent": "check_booking",
                "action": "fact",
                "tool_action_hint": "calendar.get_booking",
                "pack_refs": [],
                "slots": {},
                "reason": "calendar_get_booking_collect_reference",
                "next_question": "name",
                "open_questions": ["name"],
                "needs_manager": False,
                "subject_kind": "booking",
                "capability": "booking_manage",
                "temporal_scope": "none",
                "resolution_mode": "direct",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
            }
        )
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                httpx.TimeoutException("timeout"),
                DummyResponse(json.dumps(payload)),
            ]
            result = route_llm_policy_core(
                "проверь запись",
                expected_reply_type="name",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_summary=(
                    "assistant: Как вас зовут? user: Алина assistant: Готово, записал вас "
                    "на маникюр на завтра в 15:00. user: проверь запись"
                ),
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "reason": "calendar_get_booking_collect_reference",
                        "next_question": "name",
                        "open_questions": ["name"],
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "booking_manage",
                        "resolution_mode": "direct",
                    },
                },
            )

        assert result["attempted"] is True
        assert result["compact_input_used"] is True
        assert result["compact_retry_used"] is False
        assert mock_llm.return_value.generate.call_args_list[0].kwargs["max_tokens"] == 560
        assert mock_llm.return_value.generate.call_args_list[1].kwargs["max_tokens"] == 560

    def test_compact_retry_drops_consult_scope_for_non_media_pending_followup(self, monkeypatch):
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
            result = route_llm_policy_core(
                "проверь запись",
                expected_reply_type="phone",
                current_goal="booking",
                memory_summary=(
                    "assistant: Как вас зовут? user: Алина assistant: Подскажите, пожалуйста, "
                    "номер телефона для подтверждения. user: проверь запись"
                ),
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "phone",
                        "reason": "collect:phone",
                        "next_question": "phone",
                        "open_questions": ["phone"],
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "resolution_mode": "ask_about_requested_slot",
                    },
                },
            )

        assert result["ok"] is True
        assert result["compact_input_used"] is True
        second_call_input = json.loads(
            mock_llm.return_value.generate.call_args_list[1].kwargs["messages"][1]["content"]
        )
        assert not second_call_input["allowed"].get("consult_refs")
        assert "context" not in second_call_input or "consult_cards" not in second_call_input["context"]

    def test_active_non_media_pending_followup_uses_compact_first_attempt(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        payload = self._policy_payload()
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Завтра в 15:00",
                expected_reply_type="time",
                current_goal="booking",
                memory_summary=(
                    "user: Хочу записаться на маникюр assistant: На какую дату и время вам удобно? "
                    "user: Завтра в 15:00"
                ),
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "reason": "collect:datetime",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                    },
                    "semantic_contract": {
                        "subject_kind": "service",
                        "capability": "bookability",
                        "resolution_mode": "ask_about_requested_slot",
                    },
                },
            )

        assert result["ok"] is True
        assert result["compact_input_used"] is True
        assert result["compact_retry_used"] is False
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        policy_input = json.loads(kwargs["messages"][1]["content"])
        assert "LLM Policy Core Compact Prompt" in kwargs["messages"][0]["content"]
        assert kwargs["max_tokens"] == 560
        assert not policy_input["allowed"].get("consult_refs")
        assert "context" not in policy_input or "consult_cards" not in policy_input["context"]

    def test_compact_gpt5_path_keeps_reasoning_headroom(self):
        assert _resolve_policy_core_max_tokens_with_cap(
            15.0,
            None,
            "gpt-5.4-nano-2026-03-17",
            compact_mode=True,
        ) == 560

    def test_policy_core_respects_explicit_max_tokens_override_with_gpt5_floor(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = self._policy_payload()
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Нужно время",
                expected_reply_type="time",
                max_tokens_override=120,
            )

        assert result["ok"] is True
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        assert kwargs["max_tokens"] == 800

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
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "expected_reply_type": "time",
                        "reason": "booking_followup",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
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
        assert "expected_reply_type" not in (memory_payload.get("profile") or {})
        assert memory_payload.get("profile", {}).get("active_slots") == ["service", "datetime"]
        assert memory_payload.get("profile", {}).get("stored_keys") == [
            "preferred_master",
            "parking_near",
        ]
        assert "current_referents" not in (memory_payload.get("profile") or {})
        assert memory_payload.get("profile", {}).get("pending_question_contract") == {
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "expected_reply_type": "time",
            "reason": "booking_followup",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
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

    def test_policy_core_backfills_canonical_memory_from_legacy_args(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = self._policy_payload()
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Нужно время",
                expected_reply_type="time",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "завтра 15:00"},
            )

        assert result["ok"] is True
        llm_messages = mock_llm.return_value.generate.call_args.kwargs["messages"]
        policy_input = json.loads(llm_messages[1]["content"])
        assert "expected_reply_type" not in policy_input
        assert "current_goal" not in policy_input
        assert "slot_state" not in policy_input
        assert policy_input["memory"]["profile"]["active_goal"] == "booking"
        assert policy_input["memory"]["profile"]["slot_state"] == {
            "service": "маникюр",
            "datetime": "завтра 15:00",
        }
        assert policy_input["memory"]["profile"]["pending_question_contract"] == {
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        }

    def test_policy_core_assembles_manifest_scoped_dynamic_context(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        runtime = RuntimeCapabilities(
            payload=CapabilitiesPayload.model_validate(
                {
                    "domain_slug": "beauty_salon",
                    "providers": {"calendar_provider": "google_calendar"},
                    "features": {"booking_mode": "confirm_slots"},
                    "tools": {"allow": ["calendar.get_booking", "catalog.location"]},
                    "allowed_fact_scopes": ["info.location", "consult.hair_damage"],
                    "handoff_policy": "manager_request_only",
                    "policy_overrides": {
                        "payment_info": {"response": "Оплата только по счету"}
                    },
                }
            ),
            client_id=uuid4(),
            branch_id=None,
            source="client_capabilities",
            has_records=True,
            has_tool_policy_records=True,
        )
        playbook = ConsultPlaybook.model_validate(
            {
                "version": "v1",
                "topics": [
                    {
                        "id": "hair_damage",
                        "title": "Восстановление волос",
                        "summary": "Советы по уходу после осветления и признаки риска.",
                        "allowed_advice": ["Используйте мягкий уход."],
                        "required_questions": ["Когда было окрашивание?"],
                        "optional_questions": [],
                        "disallowed_claims": [],
                        "fact_requirements": ["service_exists"],
                        "risk_tags": ["none"],
                        "clarify_limit": 1,
                        "escalate_when": ["missing_fact"],
                        "next_step": "Если есть жжение, нужен мастер.",
                    }
                ],
            }
        )
        payload = self._policy_payload()
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            monkeypatch.setattr(
                "app.services.consult_pack_service.load_consult_playbook",
                lambda _client_slug: (playbook, None),
            )
            set_runtime_capabilities(runtime)
            try:
                result = route_llm_policy_core(
                    "Где вы находитесь?",
                    info_refs=["pricing", "location"],
                    consult_refs=None,
                    client_slug="demo_salon",
                )
            finally:
                set_runtime_capabilities(None)

        assert result["ok"] is True
        llm_messages = mock_llm.return_value.generate.call_args.kwargs["messages"]
        policy_input = json.loads(llm_messages[1]["content"])
        assert policy_input["allowed"] == {
            "tool_actions": [
                "info",
                "consult",
                "booking",
                "handoff",
                "collect",
                "calendar.get_booking",
                "catalog.location",
            ],
            "info_refs": ["location"],
            "consult_refs": ["hair_damage"],
        }
        assert policy_input["context"]["capability_cards"] == [
            {
                "kind": "domain",
                "source": "client_capabilities",
                "domain_slug": "beauty_salon",
            },
            {
                "kind": "providers",
                "source": "client_capabilities",
                "calendar_provider": "google_calendar",
            },
            {
                "kind": "features",
                "source": "client_capabilities",
                "booking_mode": "confirm_slots",
            },
            {
                "kind": "tool_policy",
                "source": "client_capabilities",
                "allow": ["calendar.get_booking", "catalog.location"],
            },
            {
                "kind": "fact_scope",
                "source": "client_capabilities",
                "allowed_scopes": ["info.location", "consult.hair_damage"],
            },
            {
                "kind": "handoff_policy",
                "source": "client_capabilities",
                "policy": "manager_request_only",
            },
        ]
        assert policy_input["context"]["policy_cards"] == [
            {
                "section": "payment_info",
                "response": "Оплата только по счету",
                "source": "client_capabilities",
            }
        ]
        assert any(
            card.get("id") == "hair"
            and "укладка" in list(card.get("includes") or [])
            and "парикмахер" in list(card.get("synonyms") or [])
            for card in policy_input["context"]["service_cards"]
        )
        assert policy_input["context"]["consult_cards"] == [
            {
                "id": "hair_damage",
                "title": "Восстановление волос",
                "summary": "Советы по уходу после осветления и признаки риска.",
                "risk_tags": ["none"],
                "fact_requirements": ["service_exists"],
                "next_step": "Если есть жжение, нужен мастер.",
            }
        ]

    def test_policy_core_honors_explicit_booking_only_context_envelope(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = self._policy_payload()
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Хочу записаться на маникюр",
                info_refs=[],
                consult_refs=[],
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        llm_messages = mock_llm.return_value.generate.call_args.kwargs["messages"]
        policy_input = json.loads(llm_messages[1]["content"])
        assert policy_input["allowed"] == {
            "tool_actions": [
                "booking",
                "handoff",
                "collect",
                "calendar.book_slot",
                "calendar.cancel",
                "calendar.get_booking",
                "calendar.list_slots",
                "calendar.reschedule",
            ],
            "info_refs": [],
            "consult_refs": [],
        }
        assert "context" not in policy_input or "consult_cards" not in policy_input.get("context", {})

    def test_policy_core_preserves_pending_question_contract(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = self._policy_payload()
        payload.update(
            {
                "slots": {"service": "маникюр", "datetime": "", "name": ""},
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "resolution_mode": "ask_about_requested_slot",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
            }
        )
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "На какое время лучше записаться?",
                expected_reply_type="time",
            )

        assert result["ok"] is True
        assert result["payload"]["grounding_requirements"]["resolution_mode"] == "ask_about_requested_slot"
        assert result["payload"]["missing_information"]["pending_question_act"] == "ask_about_requested_slot"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "ask_about_requested_slot"

    def test_policy_core_normalizes_collect_resolution_mode_to_direct(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = self._policy_payload()
        payload.update(
            {
                "slots": {"service": "маникюр", "datetime": "", "name": ""},
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "resolution_mode": "collect",
            }
        )
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Хотел бы записаться на маникюр.",
                expected_reply_type="time",
            )

        assert result["ok"] is True
        assert result["payload"]["grounding_requirements"]["resolution_mode"] == "direct"

    def test_policy_core_drops_relation_token_from_pending_question_act(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = self._policy_payload()
        payload.update(
            {
                "slots": {"service": "маникюр", "datetime": "", "name": ""},
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "tool_args": {"specialist_name": "Айгерим"},
                "entity_refs": [
                    {"entity_id": "svc:manicure", "entity_type": "service"},
                    {"entity_id": "spec:aigerim", "entity_type": "specialist"},
                ],
                "referents": {
                    "service": {
                        "value": "маникюр",
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "message",
                    },
                    "specialist": {
                        "value": "Айгерим",
                        "entity_id": "spec:aigerim",
                        "entity_type": "specialist",
                        "source_ref": "message",
                    },
                },
                "subject_kind": "specialist",
                "capability": "bookability",
                "resolution_mode": "referent_followup",
                "pending_question_act": "referent_followup",
                "pending_question_target": "specialist",
                "active_question_relation": "referent_followup",
            }
        )
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Можно выбрать Айгерим?",
                expected_reply_type="time",
            )

        assert result["ok"] is True
        assert "pending_question_act" not in result["payload"]
        assert result["payload"]["missing_information"]["pending_question_target"] == "specialist"
        assert result["payload"]["missing_information"]["active_question_relation"] == "referent_followup"
        assert result["payload"]["grounding_requirements"]["referents"]["specialist"] == {
            "value": "Айгерим",
            "entity_id": "spec:aigerim",
            "entity_type": "specialist",
            "source_ref": "message",
        }
        assert "tool_args" not in result["payload"]

    def test_policy_core_strips_stale_time_axes_from_check_booking_reference_followup(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = self._policy_payload()
        payload.update(
            {
                "intent": "booking",
                "action": "fact",
                "tool_action_hint": "calendar.get_booking",
                "pack_refs": [],
                "slots": {},
                "next_question": "name",
                "open_questions": ["name"],
                "needs_manager": False,
                "reason": "calendar_get_booking_collect_reference",
                "subject_kind": "booking",
                "capability": "booking_manage",
                "resolution_mode": "direct",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
            }
        )
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Когда я записан?",
                expected_reply_type="name",
                current_goal="booking",
                slot_state={"service": "наращивание гелем"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "reason": "calendar_get_booking_collect_reference",
                        "next_question": "name",
                        "open_questions": ["name"],
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "booking_manage",
                        "resolution_mode": "direct",
                    },
                },
            )

        assert result["ok"] is True
        assert result["binding"]["tool_action"] == "calendar.get_booking"
        assert result["binding_plan"]["selected_tool_or_workflow_ref"] == "calendar.get_booking"
        assert result["payload"]["missing_information"]["next_question"] == "name"
        assert result["payload"]["missing_information"].get("pending_question_act") is None
        assert result["payload"]["missing_information"].get("pending_question_target") is None
        assert result["payload"]["missing_information"].get("active_question_relation") is None

    def test_policy_core_allows_direct_check_booking_lookup_from_existing_booking_context(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = self._policy_payload()
        payload.update(
            {
                "intent": "check_booking",
                "action": "fact",
                "tool_action_hint": "calendar.get_booking",
                "pack_refs": [],
                "slots": {
                    "service": "маникюр",
                    "datetime": "завтра 15:00",
                    "name": "Алина",
                },
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "reason": (
                    "calendar_get_booking_from_existing_booking_context("
                    "service+datetime+customer_name_without_booking_ref)"
                ),
                "subject_kind": "booking",
                "capability": "booking_manage",
                "temporal_scope": "specific_time",
                "resolution_mode": "direct",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "referents": {
                    "service": {
                        "value": "маникюр",
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    },
                    "customer": {
                        "value": "Алина",
                        "entity_type": "customer",
                        "source_ref": "decision_slots",
                    },
                },
            }
        )
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "проверь запись",
                current_goal=None,
                memory_profile={
                    "slot_state": {
                        "service": "маникюр",
                        "datetime": "завтра 15:00",
                        "name": "Алина",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "contract_version": "semantic_contract.v1",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["binding"]["tool_action"] == "calendar.get_booking"
        assert "expected_reply_type" not in result["payload"]
        assert "next_question" not in result["payload"]
        assert "open_questions" not in result["payload"]

    def test_policy_core_binding_plan_resolves_info_capability_to_executable_tool(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "promotions",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["promotions"],
            "needs_manager": False,
            "reason": "promo_question",
            "subject_kind": "service",
            "capability": "promotions",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core("У вас есть акции?")

        assert result["ok"] is True
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["binding_plan"]["binding_outcome_type"] == "tool_call"
        assert result["binding_plan"]["selected_tool_or_workflow_ref"] == "catalog.service_query"

    def test_policy_core_binding_plan_types_handoff_explicitly(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = self._policy_payload()
        payload.update(
            {
                "intent": "manager",
                "action": "handoff",
                "tool_action_hint": "handoff",
                "reason": "manager_requested",
                "goal": "handoff",
                "needs_manager": True,
                "subject_kind": "general",
                "capability": "other",
                "temporal_scope": "none",
                "resolution_mode": "direct",
                "next_question": None,
                "open_questions": [],
                "expected_reply_type": None,
            }
        )
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core("Позовите менеджера")

        assert result["ok"] is True
        assert result["binding"]["tool_action"] == "handoff"
        assert result["binding_plan"]["binding_outcome_type"] == "handoff"
        assert result["binding_plan"]["handoff_reason_code"] == "manager_requested"

    def test_policy_core_rejects_conflicting_service_shadow_against_canonical_referent(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = self._policy_payload()
        payload.update(
            {
                "action": "fact",
                "intent": "pricing",
                "tool_action_hint": "catalog.service_query",
                "tool_args": {"service_query": "педикюр"},
                "pack_refs": [],
                "entity_refs": [
                    {
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "message",
                        "value": "маникюр",
                        "confidence": 0.93,
                    }
                ],
                "referents": {
                    "service": {
                        "value": "маникюр",
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "message",
                    }
                },
                "subject_kind": "service",
                "capability": "pricing",
                "temporal_scope": "none",
                "resolution_mode": "policy_fact",
                "active_question_relation": "generic_info_interrupt",
            }
        )
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core("Сколько стоит маникюр?")

        assert result["ok"] is True
        assert result.get("tool_args_sanitized") is True
        assert result["binding"]["tool_args"] == {"service_query": "маникюр"}

    def test_policy_core_preserves_slot_compare_pending_question_contract(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = self._policy_payload()
        payload.update(
            {
                "slots": {"service": "маникюр", "datetime": "", "name": ""},
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "pending_question_act": "slot_compare",
                "pending_question_target": "time",
                "active_question_relation": "slot_compare",
            }
        )
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "А на какое время?",
                expected_reply_type="time",
            )

        assert result["ok"] is True
        assert result["payload"]["missing_information"]["pending_question_act"] == "slot_compare"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "slot_compare"

    def test_policy_core_preserves_specialist_availability_followup_contract(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = self._policy_payload()
        payload.update(
            {
                "slots": {"service": "маникюр", "datetime": "", "name": ""},
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "subject_kind": "specialist",
                "capability": "live_availability",
                "temporal_scope": "date_range",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "specialist",
                "active_question_relation": "specialist_availability_followup",
            }
        )
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Какой мастер свободен на этой неделе?",
                expected_reply_type="time",
            )

        assert result["ok"] is True
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "specialist"
        assert result["payload"]["capability_id"] == "live_availability"
        assert result["payload"]["grounding_requirements"]["temporal_scope"] == "date_range"
        assert result["payload"]["missing_information"]["pending_question_act"] == "ask_about_requested_slot"
        assert result["payload"]["missing_information"]["pending_question_target"] == "specialist"
        assert (
            result["payload"]["missing_information"]["active_question_relation"]
            == "specialist_availability_followup"
        )

    def test_policy_core_preserves_grounded_specialist_availability_transition_contract(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = self._policy_payload()
        payload.update(
            {
                "slots": {"service": "маникюр", "datetime": "завтра", "name": ""},
                "next_question": "name",
                "open_questions": ["name"],
                "needs_manager": False,
                "risk_signals": [],
                "subject_kind": "specialist",
                "capability": "live_availability",
                "temporal_scope": "specific_time",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "specialist",
                "active_question_relation": "specialist_availability_followup",
            }
        )
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "А какие мастера доступны?",
                expected_reply_type="time",
            )

        assert result["ok"] is True
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "specialist"
        assert result["payload"]["capability_id"] == "live_availability"
        assert result["payload"]["grounding_requirements"]["temporal_scope"] == "specific_time"
        assert result["payload"]["missing_information"]["next_question"] == "name"
        assert result["payload"]["missing_information"]["open_questions"] == ["name"]
        assert result["payload"]["missing_information"]["pending_question_act"] == "ask_about_requested_slot"
        assert result["payload"]["missing_information"]["pending_question_target"] == "specialist"
        assert (
            result["payload"]["missing_information"]["active_question_relation"]
            == "specialist_availability_followup"
        )

    def test_policy_core_preserves_active_name_time_availability_followup_contract(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = self._policy_payload()
        payload.pop("expected_reply_type", None)
        payload.update(
            {
                "tool_action": "collect",
                "slots": {"service": "маникюр", "datetime": "15:00", "name": ""},
                "next_question": "name",
                "open_questions": ["name"],
                "needs_manager": False,
                "risk_signals": [],
                "subject_kind": "booking",
                "capability": "live_availability",
                "temporal_scope": "specific_time",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
            }
        )
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "А есть ли свободные слоты на 15:00?",
                expected_reply_type="name",
            )

        assert result["ok"] is True
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "booking"
        assert result["payload"]["capability_id"] == "live_availability"
        assert result["payload"]["grounding_requirements"]["temporal_scope"] == "specific_time"
        assert result["payload"]["missing_information"]["next_question"] == "name"
        assert result["payload"]["missing_information"]["open_questions"] == ["name"]
        assert result["payload"]["missing_information"]["pending_question_act"] == "ask_about_requested_slot"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "ask_about_requested_slot"

    def test_policy_core_prompt_free_slots_question_keeps_pending_time_contract(self):
        prompt = _load_policy_core_prompt()

        assert "Когда у вас есть свободные слоты?" in prompt
        assert "Не используй `calendar.list_slots` без `temporal_scope`" in prompt
        assert '`pending_question_act="ask_about_requested_slot"`' in prompt
        assert '`pending_question_target="time"`' in prompt
        assert '`active_question_relation="ask_about_requested_slot"`' in prompt
        assert "ask_about_requested_slot" in prompt
        assert "Какой мастер свободен на этой неделе?" in prompt
        assert "А какие мастера доступны?" in prompt
        assert "А есть ли свободные слоты на 15:00?" in prompt
        assert '`active_question_relation="specialist_availability_followup"`' in prompt
        assert '`next_question="name"`' in prompt
        assert '`subject_kind="booking"`' in prompt
        assert "alternate-time availability follow-up" in prompt
        assert '"Есть свободные слоты на 11:30?"' in prompt
        assert 'не переключайся в `master_query`' in prompt

    def test_policy_core_compact_prompt_keeps_booking_owner_for_candidate_time_availability(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "candidate time is available" in prompt
        assert "intent=booking, action=collect, tool_action_hint=collect" in prompt
        assert "Do NOT switch to intent=master_query" in prompt
        assert "calendar.list_slots while the requested booking slot is still incomplete" in prompt

    def test_policy_core_compact_prompt_temporal_clue_followup_uses_slot_constraint(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "А как насчет пятницы на утро?" in prompt
        assert "pending_question_act=slot_constraint" in prompt
        assert "active_question_relation=slot_constraint" in prompt
        assert "alternate_datetime=<grounded candidate slot>" in prompt
        assert 'Do NOT fall back to the generic "На какую дату и время вам удобно?"' in prompt

    def test_policy_core_compact_prompt_named_specialist_preference_under_active_time_collect_is_referent_followup(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "Мне нужен мастер Айгерим." in prompt
        assert "subject_kind=specialist" in prompt
        assert "resolution_mode=referent_followup" in prompt
        assert "pending_question_target=specialist" in prompt
        assert "active_question_relation=referent_followup" in prompt
        assert "Do NOT keep generic" in prompt

    def test_policy_core_compact_prompt_generic_specialist_query_under_active_time_collect_is_info_interrupt(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "Какой специалист будет делать маникюр?" in prompt
        assert "Кто делает маникюр?" in prompt
        assert "intent=master_query, action=fact, tool_action_hint=info" in prompt
        assert "pack_refs=[master]" in prompt
        assert "active_question_relation=generic_info_interrupt" in prompt
        assert "Do NOT ask the generic" in prompt

    def test_policy_core_prompt_booking_photo_offer_uses_media_followup_contract(self):
        prompt = _load_policy_core_prompt()

        assert '"Могу прислать фото ногтей для примера."' in prompt
        assert '`intent="consult"`' in prompt
        assert '`tool_action_hint="consult"`' in prompt
        assert '`reason="user_offers_photo_reference_before_time_selection"`' in prompt
        assert '`expected_reply_type="media"`' in prompt
        assert '`goal="booking"`' in prompt
        assert 'Forbidden: `action="fact"`' in prompt
        assert 'reply `"Я уточню это для вас."' in prompt

    def test_policy_core_compact_prompt_keeps_booking_media_offer_on_consult_path(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "user offers photo/reference/example media" in prompt
        assert "switch to consult-media follow-up under the same booking continuity" in prompt
        assert "intent=consult, action=collect, tool_action_hint=consult" in prompt
        assert "Do NOT answer this media offer as fact/info" in prompt

    def test_policy_core_prompt_media_time_interrupt_returns_to_booking_collect(self):
        prompt = _load_policy_core_prompt()

        assert '"Вы можете предложить время на утро?"' in prompt
        assert '"Мне нужно время после 10:00."' in prompt
        assert '"Есть свободные слоты на 11:30?"' in prompt
        assert 'media continuation больше не владеет смыслом хода' in prompt
        assert '`expected_reply_type="media"`' in prompt
        assert 'Forbidden: `expected_reply_type="media"`' in prompt

    def test_policy_core_compact_prompt_media_time_interrupt_returns_to_booking_collect(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "time/slot after that media follow-up" in prompt
        assert "Restore the booking collect contract" in prompt
        assert "Do NOT keep expected_reply_type=media" in prompt

    def test_policy_core_compact_prompt_advances_post_media_clock_time_fill_to_name_collect(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert 'If that later post-media turn already supplies a concrete clock time' in prompt
        assert 'expected_reply_type=name, next_question=name, open_questions=[name]' in prompt
        assert "pending_question_act=fill_requested_slot" in prompt
        assert "Do NOT keep pending_question_target=specialist" in prompt

    def test_policy_core_prompt_wait_time_interrupt_stays_duration_fact(self):
        prompt = _load_policy_core_prompt()

        assert '"Долго ли ждать?"' in prompt
        assert '"Как долго длится процедура?"' in prompt
        assert '"Сколько по времени занимает услуга?"' in prompt
        assert 'Верни `intent="duration"`, `action="fact"`, `tool_action_hint="catalog.service_query"`' in prompt
        assert '`capability="duration"`' in prompt
        assert '`active_question_relation="generic_info_interrupt"`' in prompt
        assert 'Booking continuity сохрани через `next_question="datetime"`' in prompt
        assert 'Forbidden: `action="collect"`, `capability="bookability"`' in prompt
        assert 'generic prompt `"На какую дату и время вам удобно?"`' in prompt

    def test_policy_core_prompt_inline_service_grounding_examples_stay_fact(self):
        prompt = _load_policy_core_prompt()

        assert "context.service_cards" in prompt
        assert '"Сколько времени занимает укладка?"' in prompt
        assert 'slots.service="укладка"' in prompt
        assert 'reason="service_missing_for_duration_query"' in prompt
        assert '"Кто делает укладку?"' in prompt
        assert '`pack_refs=["master"]`' in prompt
        assert 'forbidden: `action="collect"`' in prompt.casefold()

    def test_policy_core_prompt_catalog_location_uses_exact_location_family_pack_refs(self):
        prompt = _load_policy_core_prompt()

        assert '"Есть ли парковка рядом?"' in prompt
        assert '`pack_refs=["parking"]`' in prompt
        assert '"До скольки вы работаете?"' in prompt
        assert '`pack_refs=["hours"]`' in prompt
        assert '`pack_refs=["location"]`' in prompt
        assert "не добавляй лишние секции" in prompt

    def test_policy_core_prompt_catalog_service_query_uses_exact_fact_family_pack_refs(self):
        prompt = _load_policy_core_prompt()

        assert '`["pricing"]`' in prompt
        assert '`["duration"]`' in prompt
        assert '`["promotions"]`' in prompt
        assert '`pack_refs=["master"]`' in prompt
        assert "Не тащи `pack_refs` из предыдущего fact interrupt" in prompt
        assert "Standalone fact rule" in prompt
        assert '`expected_reply_type=null`' in prompt

    def test_policy_core_prompt_initial_booking_prompt_keeps_requested_slot_contract(self):
        prompt = _load_policy_core_prompt()

        assert '"Я хочу записаться на маникюр."' in prompt
        assert "это canonical `ask_about_requested_slot(time)`" in prompt
        assert "Не оставляй `active_question_relation` пустым на первом booking prompt." in prompt
        assert "не используй `fill_requested_slot` для первого booking prompt" in prompt

    def test_policy_core_prompt_reschedule_without_reference_escalates(self):
        prompt = _load_policy_core_prompt()

        assert '"Я хочу изменить время записи."' in prompt
        assert '`action=handoff`, `tool_action_hint="handoff"`' in prompt
        assert '`capability="booking_manage"`' in prompt
        assert "Не перезапускай generic `next_question=\"datetime\"` collect" in prompt

    def test_policy_core_prompt_check_booking_without_reference_stays_bot_active(self):
        prompt = _load_policy_core_prompt()

        assert '"Я хотел бы проверить свою запись."' in prompt
        assert '"Когда я записан?"' in prompt
        assert '"intent": "booking|check_booking|verify_booking|' in prompt
        assert '`intent="check_booking"`' in prompt
        assert '`tool_action_hint="calendar.get_booking"`' in prompt
        assert '`reason="calendar_get_booking_collect_reference"`' in prompt
        assert '`expected_reply_type="name"`' in prompt
        assert '`next_question="name"`' in prompt
        assert "это НЕ handoff по умолчанию" in prompt
        assert "Сохрани bot-active follow-up contract" in prompt

    def test_policy_core_prompt_existing_booking_detail_question_stays_check_booking(self):
        prompt = _load_policy_core_prompt()

        assert '"Какой специалист меня ждет?"' in prompt
        assert '"Кто мой мастер?"' in prompt
        assert '"Во сколько моя запись?"' in prompt
        assert "это не live availability и не новый booking collect" in prompt
        assert 'фразы с `моя запись`, `мой мастер`, `меня ждет` => detail query про уже существующую запись, значит `check_booking`' in prompt
        assert 'memory semantic context: `capability="booking_manage"` + активный `pending_question_contract` по `datetime`' in prompt
        assert 'forbidden: `intent="master_query"`, `action="collect"`' in prompt
        assert 'Не возвращай `master_query` с generic `next_question="datetime"`' in prompt
        assert 'не спрашивай `"На какую дату и время вам удобно?"`' in prompt
        assert 'Omit `pending_question_act`, `pending_question_target`, `active_question_relation`' in prompt
        assert '`pending_question_target="time"`' in prompt
        assert '`reason="calendar_get_booking_collect_reference"`' in prompt

    def test_policy_core_prompt_keeps_customer_name_distinct_from_specialist_preference(self):
        prompt = _load_policy_core_prompt()

        assert "`slots.name` и `next_question=\"name\"` означают только имя клиента" in prompt
        assert "Предпочтение конкретного мастера/специалиста НЕ записывай в `slots.name`." in prompt
        assert "`memory.profile.semantic_contract` и `memory.profile.pending_question_contract`" in prompt
        assert "Не возвращай `tool_args`" in prompt

    def test_policy_core_prompt_uses_dynamic_context_cards(self):
        prompt = _load_policy_core_prompt()

        assert '"context": {' in prompt
        assert '"capability_cards"' in prompt
        assert '"policy_cards"' in prompt
        assert '"consult_cards"' in prompt
        assert "dynamic context assembly envelope" in prompt

    def test_policy_core_prompt_named_specialist_preference_under_active_time_collect_is_referent_followup(self):
        prompt = _load_policy_core_prompt()

        assert '"Мне нужно, чтобы мастер был Айгерим."' in prompt
        assert '"Хочу к Айгерим."' in prompt
        assert '"Можно к Айгерим?"' in prompt
        assert '`subject_kind="specialist"`' in prompt
        assert '`resolution_mode="referent_followup"`' in prompt
        assert '`pending_question_target="specialist"`' in prompt
        assert '`active_question_relation="referent_followup"`' in prompt
        assert "Forbidden: generic `subject_kind=\"service\"`" in prompt

    def test_policy_core_prompt_generic_specialist_query_under_active_time_collect_is_info_interrupt(self):
        prompt = _load_policy_core_prompt()

        assert '"Какой специалист будет делать маникюр?"' in prompt
        assert '"Кто делает маникюр?"' in prompt
        assert '"Какой мастер работает с маникюром?"' in prompt
        assert 'Верни `intent="master_query"`, `action="fact"`, `tool_action_hint="info"`' in prompt
        assert '`pack_refs=["master"]`' in prompt
        assert '`active_question_relation="generic_info_interrupt"`' in prompt
        assert 'Forbidden: `action="collect"`' in prompt

    def test_policy_core_prompt_consult_media_offer_uses_media_followup_contract(self):
        prompt = _load_policy_core_prompt()

        assert '"Я могу прислать фото своих ногтей."' in prompt or "фото/референс/пример" in prompt
        assert '`reason="user_offers_photos_for_style_reference"`' in prompt
        assert '`expected_reply_type="media"`' in prompt
        assert '`next_question="media"`' in prompt
        assert '`open_questions=["media"]`' in prompt
        assert 'Forbidden: `next_question="service"`' in prompt

    def test_policy_core_response_format_allows_media_followup_contract(self):
        schema = build_policy_core_response_format(["collect", "consult"])
        properties = schema["json_schema"]["schema"]["properties"]

        assert "media" in properties["expected_reply_type"]["anyOf"][0]["enum"]
        assert "media" in properties["next_question"]["anyOf"][0]["enum"]

    def test_policy_core_runtime_contract_enforces_consult_media_followup(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "consult",
                "action": "collect",
                "tool_action_hint": "consult",
                "pack_refs": ["style_reference"],
                "slots": {},
                "expected_reply_type": "service_choice",
                "next_question": "service",
                "open_questions": ["service"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.93,
                "reason": "user_offers_photos_for_style_reference",
                "goal": "consult",
                "entity_refs": [],
                "referents": {},
                "subject_kind": "general",
                "capability": "consultation",
                "temporal_scope": "none",
                "resolution_mode": "direct",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        assert _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile=None,
        ) == "llm_policy_core_error:consult_media_expected_reply_invalid"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:consult_media_expected_reply_invalid",
            normalized_memory_profile=None,
        )
        assert repair is not None
        assert '`expected_reply_type="media"`' in repair
        assert '`next_question="media"`' in repair

    def test_policy_core_runtime_contract_accepts_booking_media_reason_family_with_resume_axes(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "consult",
                "action": "collect",
                "tool_action_hint": "consult",
                "pack_refs": ["style_reference"],
                "slots": {"service": "Наращивание гелем"},
                "expected_reply_type": "media",
                "next_question": "media",
                "open_questions": ["media"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.93,
                "reason": "user_offers_photo_reference_before_time_selection",
                "goal": "booking",
                "entity_refs": [],
                "referents": {
                    "service": {
                        "value": "Наращивание гелем",
                        "entity_id": "svc:gel_extension",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                },
                "subject_kind": "service",
                "capability": "bookability",
                "temporal_scope": "none",
                "resolution_mode": "direct",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None

    def test_policy_core_runtime_contract_rejects_active_media_time_interrupt_that_keeps_media_contract(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action_hint": "collect",
                "pack_refs": [],
                "slots": {"service": "Маникюр"},
                "expected_reply_type": "media",
                "next_question": "media",
                "open_questions": ["media"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.91,
                "reason": "pending_media_reference_contract_interrupted_by_time_question",
                "goal": "booking",
                "entity_refs": [],
                "referents": {
                    "service": {
                        "value": "Маникюр",
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                },
                "subject_kind": "service",
                "capability": "consultation",
                "temporal_scope": "none",
                "resolution_mode": "ask_about_requested_slot",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        normalized_memory_profile = {
            "pending_question_contract": {
                "expected_reply_type": "media",
                "next_question": "media",
                "open_questions": ["media"],
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
            },
            "resume_pending_question_contract": {
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
            },
        }

        assert _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile=normalized_memory_profile,
        ) == "llm_policy_core_error:active_media_time_interrupt_reclassification_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:active_media_time_interrupt_reclassification_required",
            normalized_memory_profile=normalized_memory_profile,
        )
        assert repair is not None
        assert '`intent="booking"`' in repair
        assert '`expected_reply_type="time"`' in repair
        assert '`next_question="datetime"`' in repair
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile={
                    "active_goal": "booking",
                    "resume_pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                    },
                },
            )
            is None
        )

    def test_policy_core_runtime_contract_rejects_generic_time_collect_for_named_specialist_preference(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action_hint": "collect",
                "pack_refs": [],
                "slots": {"service": "Маникюр"},
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.89,
                "reason": "named_specialist_preference_during_booking_time_collect",
                "goal": "booking",
                "entity_refs": [],
                "referents": {
                    "service": {
                        "value": "Маникюр",
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    },
                    "specialist": {
                        "value": "Айгерим",
                        "entity_id": "spec:aigerim",
                        "entity_type": "specialist",
                        "source_ref": "user",
                    },
                },
                "subject_kind": "service",
                "capability": "bookability",
                "temporal_scope": "date_range",
                "resolution_mode": "ask_about_requested_slot",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        normalized_memory_profile = {
            "active_goal": "booking",
            "slot_state": {"service": "Маникюр"},
            "pending_question_contract": {
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
            },
            "semantic_contract": {
                "capability": "bookability",
                "subject_kind": "service",
                "resolution_mode": "ask_about_requested_slot",
                "referents": {
                    "service": {
                        "value": "Маникюр",
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                },
            },
        }

        assert _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile=normalized_memory_profile,
        ) == "llm_policy_core_error:active_booking_specialist_followup_reclassification_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:active_booking_specialist_followup_reclassification_required",
            normalized_memory_profile=normalized_memory_profile,
            contract=contract,
        )
        assert repair is not None
        assert '`subject_kind="specialist"`' in repair
        assert '`resolution_mode="referent_followup"`' in repair
        assert '`pending_question_target="specialist"`' in repair
        assert '`active_question_relation="referent_followup"`' in repair
        assert '`expected_reply_type="time"`' in repair
        assert '`next_question="datetime"`' in repair

    def test_policy_core_runtime_contract_reclassifies_generic_specialist_query_during_active_booking_time_collect(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action_hint": "collect",
                "pack_refs": [],
                "slots": {"service": "маникюр"},
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.86,
                "reason": "user_requests_specialist_for_known_service_manicure_query_with_booking_continuity",
                "goal": "booking",
                "entity_refs": [],
                "referents": {
                    "service": {
                        "value": "маникюр",
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    },
                    "specialist": None,
                },
                "subject_kind": "specialist",
                "capability": "bookability",
                "temporal_scope": "none",
                "resolution_mode": "referent_followup",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "specialist",
                "active_question_relation": "referent_followup",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        normalized_memory_profile = {
            "active_goal": "booking",
            "slot_state": {"service": "маникюр", "datetime": "после 17:00"},
            "pending_question_contract": {
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
            },
            "semantic_contract": {
                "capability": "bookability",
                "subject_kind": "service",
                "resolution_mode": "ask_about_requested_slot",
                "referents": {
                    "service": {
                        "value": "маникюр",
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                },
            },
        }

        assert _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile=normalized_memory_profile,
        ) == "llm_policy_core_error:active_booking_generic_specialist_query_reclassification_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:active_booking_generic_specialist_query_reclassification_required",
            normalized_memory_profile=normalized_memory_profile,
            contract=contract,
        )
        assert repair is not None
        assert '`intent="master_query"`' in repair
        assert '`action="fact"`' in repair
        assert '`tool_action_hint="info"`' in repair
        assert '`pack_refs=["master"]`' in repair
        assert '`active_question_relation="generic_info_interrupt"`' in repair
        assert '`expected_reply_type="time"`' in repair
        assert '`next_question="datetime"`' in repair

    def test_policy_core_runtime_contract_rejects_stale_specialist_followup_when_clock_time_already_fills_booking_slot(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action_hint": "collect",
                "pack_refs": [],
                "slots": {"service": "маникюр"},
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.87,
                "reason": "switch_to_specialist_referent_followup_while_preserving_time_collect_contract",
                "goal": "booking",
                "entity_refs": [],
                "referents": {
                    "service": {
                        "value": "маникюр",
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    },
                    "specialist": {
                        "value": "Айгерим",
                        "entity_type": "specialist",
                        "source_ref": "user_text",
                    },
                },
                "subject_kind": "specialist",
                "capability": "bookability",
                "temporal_scope": "day",
                "resolution_mode": "referent_followup",
                "pending_question_act": None,
                "pending_question_target": "specialist",
                "active_question_relation": "referent_followup",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        normalized_memory_profile = {
            "active_goal": "booking",
            "slot_state": {"service": "маникюр", "datetime": "tomorrow"},
            "pending_question_contract": {
                "expected_reply_type": "media",
                "next_question": "media",
                "open_questions": ["media"],
                "reason": "collect:media",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
            },
            "resume_pending_question_contract": {
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
            },
            "semantic_contract": {
                "capability": "consultation",
                "subject_kind": "booking",
                "temporal_scope": "day",
                "resolution_mode": "referent_followup",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
                "referents": {
                    "service": {
                        "value": "маникюр",
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    },
                    "specialist": {
                        "value": "Айгерим",
                        "entity_type": "specialist",
                        "source_ref": "user_text",
                    },
                },
            },
        }

        assert _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile=normalized_memory_profile,
            current_message="Можно на 17:45?",
        ) == "llm_policy_core_error:active_booking_time_fill_progression_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:active_booking_time_fill_progression_required",
            normalized_memory_profile=normalized_memory_profile,
            contract=contract,
            current_message="Можно на 17:45?",
        )
        assert repair is not None
        assert '`expected_reply_type="name"`' in repair
        assert '`next_question="name"`' in repair
        assert '`pending_question_act="fill_requested_slot"`' in repair
        assert '`pending_question_target="time"`' in repair
        assert '`active_question_relation="fill_requested_slot"`' in repair
        assert 'Do NOT keep `pending_question_target="specialist"`' in repair

    def test_policy_core_runtime_contract_requires_catalog_location_exact_pack_refs(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "location",
                "action": "fact",
                "tool_action_hint": "catalog.location",
                "pack_refs": [],
                "slots": {},
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.81,
                "reason": "parking_question_interrupt_during_booking_time_collect_preserve_requested_slot_contract",
                "goal": "booking",
                "entity_refs": [],
                "referents": {},
                "subject_kind": "service",
                "capability": "location",
                "temporal_scope": "none",
                "resolution_mode": "policy_fact",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "generic_info_interrupt",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile=None,
            )
            == "llm_policy_core_error:catalog_location_pack_refs_missing"
        )
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:catalog_location_pack_refs_missing",
            normalized_memory_profile=None,
            contract=contract,
        )
        assert repair is not None
        assert '`pack_refs=["parking"]`' in repair
        assert '`pack_refs=["hours"]`' in repair
        assert '`pack_refs=["location"]`' in repair

    def test_policy_core_runtime_contract_requires_catalog_service_query_exact_pack_ref(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "pricing",
                "action": "fact",
                "tool_action_hint": "catalog.service_query",
                "pack_refs": ["pricing", "promotions"],
                "slots": {"service": "маникюр"},
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.82,
                "reason": "pricing_info_interrupt_keep_requested_time_contract",
                "goal": "booking",
                "entity_refs": [],
                "referents": {
                    "service": {
                        "value": "маникюр",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                },
                "subject_kind": "service",
                "capability": "pricing",
                "temporal_scope": "none",
                "resolution_mode": "policy_fact",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "generic_info_interrupt",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                    },
                },
            )
            == "llm_policy_core_error:catalog_service_query_pack_refs_invalid"
        )
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:catalog_service_query_pack_refs_invalid",
            normalized_memory_profile={
                "active_goal": "booking",
                "pending_question_contract": {
                    "expected_reply_type": "time",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                    "pending_question_act": "ask_about_requested_slot",
                    "pending_question_target": "time",
                    "active_question_relation": "ask_about_requested_slot",
                },
            },
            contract=contract,
        )
        assert repair is not None
        assert '`pack_refs=["pricing"]`' in repair
        assert '`pack_refs=["duration"]`' in repair
        assert '`pack_refs=["promotions"]`' in repair
        assert '`pack_refs=["master"]`' in repair

    def test_policy_core_runtime_contract_rejects_standalone_fact_followup_contract(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "hours",
                "action": "fact",
                "tool_action_hint": "catalog.location",
                "pack_refs": ["hours"],
                "slots": {},
                "expected_reply_type": "media",
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.77,
                "reason": "user_asks_business_hours",
                "goal": "info",
                "entity_refs": [],
                "referents": {},
                "subject_kind": "general",
                "capability": "hours",
                "temporal_scope": "none",
                "resolution_mode": "policy_fact",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile=None,
            )
            == "llm_policy_core_error:standalone_fact_followup_contract_invalid"
        )
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:standalone_fact_followup_contract_invalid",
            normalized_memory_profile=None,
            contract=contract,
        )
        assert repair is not None
        assert "`expected_reply_type=null`" in repair
        assert "`next_question=null`" in repair
        assert "`open_questions=[]`" in repair

    def test_policy_core_runtime_contract_rejects_duration_collect_when_current_turn_already_names_service(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "duration",
                "action": "collect",
                "tool_action_hint": "collect",
                "pack_refs": [],
                "slots": {},
                "expected_reply_type": "service_choice",
                "next_question": "service",
                "open_questions": ["service"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.91,
                "reason": "service_missing_for_duration_query",
                "goal": "info",
                "entity_refs": [],
                "referents": {},
                "subject_kind": "service",
                "capability": "duration",
                "temporal_scope": "none",
                "resolution_mode": "clarify_missing_subject",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile=None,
                current_message="Сколько времени занимает укладка?",
                context_payload={"service_cards": [{"includes": ["укладка", "стрижка"]}]},
            )
            == "llm_policy_core_error:service_scoped_query_collect_invalid"
        )
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:service_scoped_query_collect_invalid",
            normalized_memory_profile=None,
            contract=contract,
            current_message="Сколько времени занимает укладка?",
            context_payload={"service_cards": [{"includes": ["укладка", "стрижка"]}]},
        )
        assert repair is not None
        assert '`action="fact"`' in repair
        assert '`slots.service="укладка"`' in repair

    def test_policy_core_runtime_contract_repair_instruction_for_booking_commit(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action_hint": "calendar.book_slot",
                "pack_refs": [],
                "slots": {
                    "service": "Маникюр",
                    "datetime": "2026-04-04T15:00:00+05:00",
                    "name": "Алина",
                },
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "reason": "booking_commit_ready_after_name",
                "subject_kind": "service",
                "capability": "bookability",
                "temporal_scope": "specific_time",
                "resolution_mode": "live_calendar",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": "fill_requested_slot",
            }
        )

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile={
                    "slot_state": {
                        "service": "Маникюр",
                        "datetime": "2026-04-04T15:00:00+05:00",
                    }
                },
                current_message="Алина",
                context_payload=None,
            )
            == "llm_policy_core_error:booking_commit_action_invalid"
        )
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:booking_commit_action_invalid",
            normalized_memory_profile={
                "slot_state": {
                    "service": "Маникюр",
                    "datetime": "2026-04-04T15:00:00+05:00",
                    "name": "Алина",
                }
            },
            contract=contract,
            current_message="Алина",
            context_payload=None,
        )
        assert repair is not None
        assert '`action="fact"`' in repair
        assert '`tool_action_hint="calendar.book_slot"`' in repair

    def test_policy_core_runtime_contract_rejects_master_collect_when_current_turn_already_names_service(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "master_query",
                "action": "collect",
                "tool_action_hint": "collect",
                "pack_refs": [],
                "slots": {},
                "expected_reply_type": "service_choice",
                "next_question": "service",
                "open_questions": ["service"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.87,
                "reason": "service_missing_for_master_query",
                "goal": "info",
                "entity_refs": [],
                "referents": {},
                "subject_kind": "service",
                "capability": "live_availability",
                "temporal_scope": "none",
                "resolution_mode": "clarify_missing_subject",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile=None,
                current_message="Кто делает укладку?",
                context_payload={"service_cards": [{"includes": ["укладка", "стрижка"]}]},
                client_slug="demo_salon",
            )
            == "llm_policy_core_error:service_scoped_query_collect_invalid"
        )

    def test_policy_core_context_service_hint_requires_explicit_service_cards(self):
        assert (
            _policy_core_context_service_hint(
                "Сколько времени занимает укладка?",
                None,
                client_slug="demo_salon",
            )
            is None
        )
        assert (
            _policy_core_context_service_hint(
                "Сколько времени занимает укладка?",
                {},
                client_slug="demo_salon",
            )
            is None
        )

    def test_policy_core_runtime_contract_does_not_infer_service_from_raw_message_without_context_cards(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "duration",
                "action": "collect",
                "tool_action_hint": "collect",
                "pack_refs": [],
                "slots": {},
                "expected_reply_type": "service_choice",
                "next_question": "service",
                "open_questions": ["service"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.91,
                "reason": "service_missing_for_duration_query",
                "goal": "info",
                "entity_refs": [],
                "referents": {},
                "subject_kind": "service",
                "capability": "duration",
                "temporal_scope": "none",
                "resolution_mode": "clarify_missing_subject",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile=None,
                current_message="Сколько времени занимает укладка?",
                context_payload=None,
                client_slug="demo_salon",
            )
            is None
        )

    def test_policy_core_runtime_contract_rejects_service_collect_when_carryover_already_has_service(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "duration",
                "action": "collect",
                "tool_action_hint": "collect",
                "pack_refs": [],
                "slots": {},
                "expected_reply_type": "service_choice",
                "next_question": "service",
                "open_questions": ["service"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.88,
                "reason": "service_missing_for_duration_query",
                "goal": "booking",
                "entity_refs": [],
                "referents": {},
                "subject_kind": "service",
                "capability": "duration",
                "temporal_scope": "none",
                "resolution_mode": "clarify_missing_subject",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "generic_info_interrupt",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр"},
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "service",
                        "resolution_mode": "ask_about_requested_slot",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                    },
                },
                current_message="А сколько это занимает?",
                context_payload=None,
            )
            == "llm_policy_core_error:service_scoped_query_collect_invalid"
        )

    def test_policy_core_repairs_duration_collect_to_fact_when_service_named_in_current_turn(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "duration",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.91,
            "reason": "service_missing_for_duration_query",
            "goal": "info",
            "entity_refs": [],
            "referents": {},
            "subject_kind": "service",
            "capability": "duration",
            "temporal_scope": "none",
            "resolution_mode": "clarify_missing_subject",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        repaired_payload = {
            **invalid_payload,
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "slots": {"service": "укладка"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "reason": "service_duration_question",
            "entity_refs": [
                {
                    "entity_id": "svc:styling",
                    "entity_type": "service",
                    "source_ref": "message",
                    "value": "укладка",
                }
            ],
            "referents": {
                "service": {
                    "value": "укладка",
                    "entity_id": "svc:styling",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "resolution_mode": "policy_fact",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Сколько времени занимает укладка?",
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:service_scoped_query_collect_invalid"
        )
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["binding"]["tool_args"] == {"service_query": "укладка"}

    def test_policy_core_repairs_pricing_interrupt_to_exact_catalog_service_query_pack_ref(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "pricing",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["pricing", "promotions"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.84,
            "reason": "pricing_info_interrupt_keep_requested_time_contract",
            "goal": "booking",
            "entity_refs": [],
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "service",
            "capability": "pricing",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }
        repaired_payload = {
            **invalid_payload,
            "pack_refs": ["pricing"],
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Какая цена?",
                expected_reply_type="time",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                    },
                },
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:catalog_service_query_pack_refs_invalid"
        )
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["binding"]["tool_args"] == {"service_query": "маникюр"}
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["pricing"]

    def test_policy_core_memory_profile_strips_duplicate_semantic_carriers(self):
        normalized = _normalize_policy_core_memory_profile(
            {
                "active_goal": " booking ",
                "expected_reply_type": " time ",
                "active_slots": [" service ", " datetime ", " phone "],
                "current_referents": {
                    "service": " Маникюр ",
                    "specialist": " Айгерим ",
                    "customer": " Марина ",
                    "booking_ref": " BK-1 ",
                },
                "pending_question_contract": {
                    "next_question": " time ",
                    "open_questions": [" time ", " "],
                    "expected_reply_type": " time ",
                    "reason": " booking_followup ",
                    "pending_question_act": " ask_about_requested_slot ",
                    "pending_question_target": " time ",
                    "active_question_relation": " ask_about_requested_slot ",
                },
                "resume_pending_question_contract": {
                    "next_question": " time ",
                    "open_questions": [" time ", " "],
                    "expected_reply_type": " time ",
                    "pending_question_act": " ask_about_requested_slot ",
                    "pending_question_target": " time ",
                    "active_question_relation": " ask_about_requested_slot ",
                },
                "interaction_state": {
                    "resume_slot": " datetime ",
                    "interaction_target": " specialist ",
                    "interaction_relation": " referent_followup ",
                    "interaction_owner": " llm_policy_core_booking ",
                    "grounded_referents": {
                        "service": " Маникюр ",
                        "specialist": " Айгерим ",
                        "customer": " Марина ",
                    },
                },
            }
        )

        assert normalized == {
            "active_goal": "booking",
            "active_slots": ["service", "datetime", "phone"],
            "pending_question_contract": {
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "expected_reply_type": "time",
                "reason": "booking_followup",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
            },
            "resume_pending_question_contract": {
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "expected_reply_type": "time",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
            },
        }

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
        assert result["structured_output_fallback_reason"] == "response_format_invalid_request"
        assert "response_format json_schema is not supported" in result["response_format_error"]
        assert mock_llm.return_value.generate.call_count == 2
        first_kwargs = mock_llm.return_value.generate.call_args_list[0].kwargs
        second_kwargs = mock_llm.return_value.generate.call_args_list[1].kwargs
        assert isinstance(first_kwargs.get("response_format"), dict)
        assert "response_format" not in second_kwargs or second_kwargs.get("response_format") is None

    def test_retries_without_response_format_when_structured_output_is_empty(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = self._policy_payload()
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(""),
                DummyResponse(json.dumps(payload)),
            ]
            result = route_llm_policy_core("нужна запись")

        assert result["ok"] is True
        assert result["structured_output_enabled"] is True
        assert result["structured_output_fallback_used"] is True
        assert result["structured_output_fallback_reason"] == "response_format_empty_response"
        assert result["attempt_count"] == 2
        first_kwargs = mock_llm.return_value.generate.call_args_list[0].kwargs
        second_kwargs = mock_llm.return_value.generate.call_args_list[1].kwargs
        assert isinstance(first_kwargs.get("response_format"), dict)
        assert "response_format" not in second_kwargs or second_kwargs.get("response_format") is None

    def test_compact_specialist_followup_empty_response_retries_with_full_prompt(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        repaired_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.86,
            "reason": "user_requests_specific_master_aigerim_during_booking_datetime_collect_continuity",
            "goal": "booking",
            "entity_refs": [],
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "specialist": {
                    "value": "Айгерим",
                    "entity_type": "specialist",
                    "source_ref": "user_message",
                },
            },
            "subject_kind": "specialist",
            "capability": "bookability",
            "temporal_scope": "none",
            "resolution_mode": "referent_followup",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(""),
                DummyResponse(""),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Мне нужен мастер Айгерим.",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_summary="user: Здравствуйте, хочу записаться на маникюр. assistant: На какую дату и время вам удобно? user: У вас есть свободные слоты на завтра? assistant: На какую дату и время вам удобно? user: Мне нужен мастер Айгерим.",
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "service",
                        "resolution_mode": "ask_about_requested_slot",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["compact_input_used"] is True
        assert result["compact_retry_used"] is True
        assert result["attempt_count"] == 3

    def test_route_policy_core_repairs_post_media_clock_time_fill_into_name_collect(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.87,
            "reason": "switch_to_specialist_referent_followup_while_preserving_time_collect_contract",
            "goal": "booking",
            "entity_refs": [],
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "specialist": {
                    "value": "Айгерим",
                    "entity_type": "specialist",
                    "source_ref": "user_text",
                },
            },
            "subject_kind": "specialist",
            "capability": "bookability",
            "temporal_scope": "day",
            "resolution_mode": "referent_followup",
            "pending_question_act": None,
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
            "resolver_id": None,
            "resolver_version": None,
        }
        repaired_payload = {
            **invalid_payload,
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "fill_requested_slot",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Можно на 17:45?",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "tomorrow"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр", "datetime": "tomorrow"},
                    "pending_question_contract": {
                        "expected_reply_type": "media",
                        "next_question": "media",
                        "open_questions": ["media"],
                        "reason": "collect:media",
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "resume_pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "capability": "consultation",
                        "subject_kind": "booking",
                        "temporal_scope": "day",
                        "resolution_mode": "referent_followup",
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            },
                            "specialist": {
                                "value": "Айгерим",
                                "entity_type": "specialist",
                                "source_ref": "user_text",
                            },
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:active_booking_time_fill_progression_required"
        )
        missing = result["payload"]["missing_information"]
        assert missing["expected_reply_type"] == "name"
        assert missing["next_question"] == "name"
        assert missing["pending_question_act"] == "fill_requested_slot"
        assert missing["pending_question_target"] == "time"
        assert missing["active_question_relation"] == "fill_requested_slot"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "specialist"

    def test_policy_core_response_format_is_strict_and_canonical(self):
        response_format = build_policy_core_response_format(["calendar.book_slot"])
        assert response_format["json_schema"]["strict"] is True
        schema = response_format["json_schema"]["schema"]
        assert schema["type"] == "object"
        assert schema["required"] == list(schema["properties"].keys())
        assert "check_booking" in schema["properties"]["intent"]["enum"]
        assert "verify_booking" in schema["properties"]["intent"]["enum"]
        assert "referents" in schema["properties"]
        assert "entity_refs" in schema["properties"]
        assert "subject_kind" in schema["properties"]
        assert "capability" in schema["properties"]
        assert "temporal_scope" in schema["properties"]
        assert "resolution_mode" in schema["properties"]
        assert "expected_reply_type" in schema["properties"]
        assert "risk_signals" in schema["properties"]
        assert "language" in schema["properties"]
        assert "confidence" in schema["properties"]
        assert "goal" in schema["properties"]
        assert "pending_question_act" in schema["properties"]
        assert "pending_question_target" in schema["properties"]
        assert "active_question_relation" in schema["properties"]
        assert "resolver_id" in schema["properties"]
        assert "resolver_version" in schema["properties"]
        assert "tool_args" not in schema["properties"]
        assert schema["properties"]["tool_action_hint"]["enum"] == ["calendar.book_slot"]
        slots_schema = schema["properties"]["slots"]
        referents_schema = schema["properties"]["referents"]
        assert "anyOf" in slots_schema
        assert "anyOf" in referents_schema
        slot_variants = next(
            variant["anyOf"]
            for variant in slots_schema["anyOf"]
            if isinstance(variant, dict) and "anyOf" in variant
        )
        referent_variants = next(
            variant["anyOf"]
            for variant in referents_schema["anyOf"]
            if isinstance(variant, dict) and "anyOf" in variant
        )
        assert any(
            variant["required"] == ["service"]
            and list(variant["properties"].keys()) == ["service"]
            for variant in slot_variants
        )
        assert any(
            variant["required"] == ["service"]
            and list(variant["properties"].keys()) == ["service"]
            for variant in referent_variants
        )


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
                "The model missing-model does not exist"
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
