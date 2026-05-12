import inspect
import json
import time
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest

import app.services.intent_service as intent_service_module
from app.schemas.capabilities import CapabilitiesPayload
from app.schemas.consult import ConsultPlaybook
from app.schemas.intent import validate_llm_policy_core_output
from app.services.capabilities_runtime import RuntimeCapabilities, set_runtime_capabilities
from app.services.intent_service import (
    ESCALATION_INTENTS,
    REJECTION_INTENTS,
    DomainIntent,
    Intent,
    _build_policy_core_compact_input,
    _build_customer_name_hint_response_format,
    _build_policy_core_contract_repair_instruction,
    _build_service_query_hint_response_format,
    _build_specialist_hint_response_format,
    _load_policy_core_prompt,
    _normalize_policy_core_memory_profile,
    _policy_core_context_service_hint,
    _policy_core_contract_grounded_service,
    _policy_core_contract_has_unsupported_service_availability_grounding_gap,
    _policy_core_contract_has_unsupported_service_booking_continuation_gap,
    _policy_core_contract_error_disallows_repair,
    _policy_core_current_message_exact_datetime_surface,
    _policy_core_current_message_grounded_temporal_scope_hint,
    _policy_core_current_message_has_service_presence_query,
    _policy_core_current_message_hours_location_booking_followup_pack_refs,
    _policy_core_current_message_hours_location_fact_pack_refs,
    _policy_core_current_message_hours_location_service_fact_pack_refs,
    _policy_core_current_message_hours_service_fact_pack_refs,
    _policy_core_current_message_location_service_fact_pack_refs,
    _policy_core_current_message_promotions_location_pack_refs,
    _policy_core_current_message_service_multifact_pack_refs,
    _policy_core_focused_contract_error,
    _policy_core_resolve_current_message_service_hint,
    _policy_core_resolve_missing_service_grounded_fact_interrupt_variant,
    _policy_core_service_choice_slot_carryover_forced_fields,
    _policy_core_temporal_clue_requires_message_grounded_alternate_datetime,
    _policy_core_unknown_service_candidate_from_booking_request,
    _policy_core_unsupported_service_availability_forced_fields,
    _policy_core_unsupported_service_booking_continuation_forced_fields,
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
from app.services.knowledge_runtime import RuntimeTruth, use_runtime_truth_override
from app.services.policy_context_snapshot_service import build_policy_core_context_snapshot
from app.services.policy_prompt_snapshot_service import (
    iter_policy_core_booking_info_interrupt_variants,
    policy_core_generated_contract_boundary_payload_template_ids,
    iter_policy_core_generated_contract_blocks,
    load_policy_core_compact_prompt_snapshot,
    render_policy_core_generated_contract_boundary_payload_template,
    render_policy_core_generated_contract_repair_template,
    policy_core_generated_contract_repair_template_ids,
    policy_core_generated_contract_semantic_tokens,
)
from app.services.policy_vocabulary_snapshot_service import (
    build_policy_core_response_format,
    build_policy_core_vocabulary_snapshot,
)


class DummyResponse:
    def __init__(self, content: str) -> None:
        self.content = content


def focused_contract_response(messages, *_args, **_kwargs) -> DummyResponse:
    payload = json.loads(messages[-1]["content"])
    forced_fields = payload["focus_contract"]["forced_fields"]
    return DummyResponse(json.dumps(forced_fields, ensure_ascii=False))


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

        assert result["ok"] is True
        assert result["error"] is None

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
        assert mock_llm.return_value.generate.call_args_list[0].kwargs["max_tokens"] == 320
        assert mock_llm.return_value.generate.call_args_list[1].kwargs["max_tokens"] == 320
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
        assert fallback_kwargs["max_tokens"] == 320
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
            "slots": {"service": "маникюр"},
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

    def test_policy_core_rejects_invalid_booking_manage_reference_contract(self, monkeypatch):
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
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core("Проверьте мою запись")

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:booking_manage_reference_action_invalid"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 2
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 2

    def test_policy_core_focuses_standalone_cancel_request_to_admin_handoff(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = focused_contract_response
            result = route_llm_policy_core(
                "Отмените мою запись на маникюр 25 августа в 11:00",
                client_slug="demo_salon",
            )

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["error"] is None
        assert result["focused_owner_contract_used"] is True
        assert result["focused_policy_handoff"] is True
        assert forced_fields["capability"] == "booking_manage"
        assert forced_fields["tool_action_hint"] == "handoff"
        assert forced_fields["needs_manager"] is True
        assert forced_fields["open_questions"] == []
        assert result["binding"]["tool_action"] == "handoff"
        assert result["payload"]["requested_outcome"] == "handoff"
        assert result["payload"]["intent"] == "cancel_request"

    def test_policy_core_focuses_standalone_reschedule_request_to_admin_handoff(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = focused_contract_response
            result = route_llm_policy_core(
                "Мне нужно перенести запись с 25 на 26 августа в 15:00",
                client_slug="demo_salon",
            )

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["error"] is None
        assert result["focused_owner_contract_used"] is True
        assert result["focused_policy_handoff"] is True
        assert forced_fields["capability"] == "booking_manage"
        assert forced_fields["tool_action_hint"] == "handoff"
        assert forced_fields["needs_manager"] is True
        assert forced_fields["open_questions"] == []
        assert result["binding"]["tool_action"] == "handoff"
        assert result["payload"]["requested_outcome"] == "handoff"
        assert result["payload"]["intent"] == "reschedule"

    def test_policy_core_focuses_medical_policy_question_to_handoff(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = focused_contract_response
            result = route_llm_policy_core(
                "Можно ли делать депиляцию, если есть раздражение кожи?",
                client_slug="demo_salon",
            )

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["error"] is None
        assert result["focused_owner_contract_used"] is True
        assert result["focused_policy_handoff"] is True
        assert forced_fields["tool_action_hint"] == "handoff"
        assert forced_fields["risk_signals"] == ["medical"]
        assert result["binding"]["tool_action"] == "handoff"
        assert result["binding_plan"]["binding_outcome_type"] == "handoff"

    def test_policy_core_focuses_unknown_service_booking_to_service_not_found_fact(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "services_overview",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["services_overview"],
            "slots": {"service": "татуаж", "datetime": "завтра в 12"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "goal": "booking",
            "subject_kind": "service",
            "capability": "other",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра в 12",
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "reason": "unsupported_service_booking_request",
            "referents": {
                "service": {
                    "value": "татуаж",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "message_candidate",
                }
            },
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Хочу татуаж завтра в 12",
                client_slug="demo_salon",
            )

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["error"] is None
        assert result["focused_owner_contract_used"] is True
        assert result["focused_unknown_service_booking"] is True
        assert forced_fields["tool_action_hint"] == "catalog.service_query"
        assert forced_fields["pack_refs"] == ["services_overview"]
        assert forced_fields["slots"]["service"] == "татуаж"
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["binding"]["tool_args"] == {"service_query": "татуаж"}

    def test_policy_core_unknown_service_booking_rejects_conditional_residue(self):
        assert (
            _policy_core_unknown_service_candidate_from_booking_request(
                "если да хочу записаться сегодня вечером",
                client_slug="demo_salon",
                grounded_service=None,
            )
            is None
        )
        assert (
            _policy_core_unknown_service_candidate_from_booking_request(
                "Хочу татуаж завтра в 12",
                client_slug="demo_salon",
                grounded_service=None,
            )
            == "татуаж"
        )

    def test_policy_core_rejects_ungrounded_unsupported_service_availability_referent(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "out_of_domain",
                "action": "fact",
                "tool_action_hint": "catalog.service_query",
                "pack_refs": ["services_overview"],
                "slots": {"service": "маникюр"},
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.82,
                "reason": "unsupported_service_availability",
                "goal": None,
                "entity_refs": [],
                "referents": {
                    "service": {
                        "value": "маникюр",
                        "entity_type": "service",
                        "source_ref": "catalog_alias",
                    }
                },
                "subject_kind": "service",
                "capability": "other",
                "temporal_scope": "none",
                "alternate_datetime": None,
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
        assert _policy_core_contract_has_unsupported_service_availability_grounding_gap(
            contract,
            current_message="делаете пирсинг?",
            context_payload=None,
            client_slug="demo_salon",
        )
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile=None,
                current_message="делаете пирсинг?",
                client_slug="demo_salon",
            )
            == "llm_policy_core_error:unsupported_service_availability_grounding_required"
        )
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:unsupported_service_availability_grounding_required",
            normalized_memory_profile=None,
            contract=contract,
            current_message="делаете пирсинг?",
            client_slug="demo_salon",
        )
        assert repair is not None
        assert 'slots.service="пирсинг"' in repair
        assert "Do not substitute a supported catalog service" in repair

    def test_policy_core_focuses_unsupported_service_availability_fact(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        forced_fields = _policy_core_unsupported_service_availability_forced_fields(
            None,
            current_message="делаете пирсинг?",
            grounded_service=None,
        )

        assert forced_fields is not None
        assert forced_fields["action"] == "fact"
        assert forced_fields["tool_action_hint"] == "catalog.service_query"
        assert forced_fields["pack_refs"] == ["services_overview"]
        assert forced_fields["slots"] == {"service": "пирсинг"}
        assert forced_fields["referents"]["service"]["value"] == "пирсинг"

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = focused_contract_response
            result = route_llm_policy_core(
                "делаете пирсинг?",
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["focused_owner_contract_used"] is True
        assert result["focused_unsupported_service_availability"] is True
        assert result["focused_response_format_mode"] == "json_object"
        assert result["payload"]["semantic_slots"] == {"service": "пирсинг"}
        assert result["payload"]["capability_id"] == "other"
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["binding"]["tool_args"] == {"service_query": "пирсинг"}

    def test_policy_core_rejects_focused_unsupported_service_availability_drift(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_COMPACT_FIRST_ATTEMPT",
            False,
        )
        invalid_payload = {
            "intent": "out_of_domain",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["services_overview"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.82,
            "reason": "unsupported_service_availability",
            "goal": None,
            "entity_refs": [],
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_type": "service",
                    "source_ref": "catalog_alias",
                }
            },
            "subject_kind": "service",
            "capability": "other",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps(invalid_payload)
            )
            result = route_llm_policy_core(
                "делаете пирсинг?",
                client_slug="demo_salon",
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert result["focused_contract_error"] == (
            "llm_policy_core_error:focused_contract_mismatch:slots.service"
        )
        assert result["focused_unsupported_service_availability"] is True

    def test_policy_core_focuses_unsupported_service_booking_continuation_fact(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        memory_profile = {
            "active_goal": "out_of_domain",
            "slot_state": {"service": "пирсинг"},
            "semantic_contract": {
                "subject_kind": "service",
                "capability": "other",
                "resolution_mode": "policy_fact",
                "referents": {
                    "service": {
                        "value": "пирсинг",
                        "entity_type": "service",
                        "source_ref": "user_message",
                    }
                },
            },
        }
        forced_fields = _policy_core_unsupported_service_booking_continuation_forced_fields(
            memory_profile,
            current_message="если да хочу записаться сегодня вечером",
            grounded_service=None,
            client_slug="demo_salon",
        )

        assert forced_fields is not None
        assert forced_fields["action"] == "fact"
        assert forced_fields["tool_action_hint"] == "catalog.service_query"
        assert forced_fields["slots"] == {"service": "пирсинг"}
        assert forced_fields["referents"]["service"]["source_ref"] == "memory.semantic_contract"

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = focused_contract_response
            result = route_llm_policy_core(
                "если да хочу записаться сегодня вечером",
                client_slug="demo_salon",
                memory_profile=memory_profile,
            )

        assert result["ok"] is True
        assert result["focused_owner_contract_used"] is True
        assert result["focused_unsupported_service_booking_continuation"] is True
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["semantic_slots"] == {"service": "пирсинг"}
        assert result["binding"]["tool_action"] == "catalog.service_query"

    def test_policy_core_keeps_unsupported_service_identity_followup_on_fact_path(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        memory_profile = {
            "active_goal": "out_of_domain",
            "slot_state": {"service": "пирсинг"},
            "semantic_contract": {
                "subject_kind": "service",
                "capability": "other",
                "resolution_mode": "policy_fact",
                "referents": {
                    "service": {
                        "value": "пирсинг",
                        "entity_type": "service",
                        "source_ref": "user_message",
                    }
                },
            },
        }
        forced_fields = _policy_core_unsupported_service_booking_continuation_forced_fields(
            memory_profile,
            current_message="Катя 87025556677",
            grounded_service=None,
            client_slug="demo_salon",
        )

        assert forced_fields is not None
        assert forced_fields["intent"] == "out_of_domain"
        assert forced_fields["action"] == "handoff"
        assert forced_fields["tool_action_hint"] == "handoff"
        assert forced_fields["slots"] == {
            "service": "пирсинг",
            "name": "Катя",
            "phone": "87025556677",
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = focused_contract_response
            result = route_llm_policy_core(
                "Катя 87025556677",
                client_slug="demo_salon",
                memory_profile=memory_profile,
            )

        assert result["ok"] is True
        assert result["focused_unsupported_service_booking_continuation"] is True
        assert result.get("focused_identity_first_booking") is not True
        assert result["payload"]["requested_outcome"] == "handoff"
        assert result["binding"]["tool_action"] == "handoff"
        assert result["payload"]["semantic_slots"]["service"] == "пирсинг"
        assert result["payload"]["semantic_slots"]["phone"] == "87025556677"

    def test_policy_core_rejects_booking_collect_for_unsupported_service_continuation(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action_hint": "collect",
                "pack_refs": [],
                "slots": {"service": None, "datetime": None, "name": None, "phone": None},
                "expected_reply_type": "service_choice",
                "next_question": "service",
                "open_questions": ["service"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.72,
                "reason": "unsupported_service_booking_attempt",
                "goal": "booking",
                "entity_refs": [],
                "referents": {
                    "service": {
                        "value": "пирсинг",
                        "entity_type": "service",
                        "source_ref": "user_message",
                    }
                },
                "subject_kind": "general",
                "capability": "bookability",
                "temporal_scope": "day",
                "alternate_datetime": "сегодня вечером",
                "resolution_mode": "clarify_missing_subject",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "resolver_id": None,
                "resolver_version": None,
            }
        )
        memory_profile = {
            "active_goal": "out_of_domain",
            "slot_state": {"service": "пирсинг"},
            "semantic_contract": {
                "subject_kind": "service",
                "capability": "other",
                "resolution_mode": "policy_fact",
                "referents": {
                    "service": {
                        "value": "пирсинг",
                        "entity_type": "service",
                        "source_ref": "user_message",
                    }
                },
            },
        }

        assert schema_error is None
        assert contract is not None
        assert _policy_core_contract_has_unsupported_service_booking_continuation_gap(
            contract,
            memory_profile,
            current_message="если да хочу записаться сегодня вечером",
            context_payload=None,
            client_slug="demo_salon",
        )
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile=memory_profile,
                current_message="если да хочу записаться сегодня вечером",
                client_slug="demo_salon",
            )
            == "llm_policy_core_error:unsupported_service_booking_continuation_requires_fact"
        )

    def test_policy_core_keeps_unsupported_service_booking_continuation_on_fact_path(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_COMPACT_FIRST_ATTEMPT",
            False,
        )
        invalid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": None, "datetime": None, "name": None, "phone": None},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.72,
            "reason": "unsupported_service_booking_attempt",
            "goal": "booking",
            "entity_refs": [],
            "referents": {
                "service": {
                    "value": "пирсинг",
                    "entity_type": "service",
                    "source_ref": "user_message",
                }
            },
            "subject_kind": "general",
            "capability": "bookability",
            "temporal_scope": "day",
            "alternate_datetime": "сегодня вечером",
            "resolution_mode": "clarify_missing_subject",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        repaired_payload = {
            "intent": "services_overview",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["services_overview"],
            "slots": {"service": "пирсинг"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.82,
            "reason": "unsupported_service_booking_continuation_requires_supported_service_choice",
            "goal": None,
            "entity_refs": [],
            "referents": {
                "service": {
                    "value": "пирсинг",
                    "entity_type": "service",
                    "source_ref": "memory.semantic_contract",
                }
            },
            "subject_kind": "service",
            "capability": "other",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "если да хочу записаться сегодня вечером",
                client_slug="demo_salon",
                memory_profile={
                    "active_goal": "out_of_domain",
                    "slot_state": {"service": "пирсинг"},
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "reason": "legacy_contract_repair_path",
                    },
                    "semantic_contract": {
                        "subject_kind": "service",
                        "capability": "other",
                        "resolution_mode": "policy_fact",
                        "referents": {
                            "service": {
                                "value": "пирсинг",
                                "entity_type": "service",
                                "source_ref": "user_message",
                            }
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["semantic_slots"] == {"service": "пирсинг"}
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["binding"]["tool_args"] == {"service_query": "пирсинг"}

    def test_policy_core_rejects_fact_consult_tool_action_before_projection(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "out_of_domain",
                "action": "fact",
                "tool_action_hint": "consult",
                "pack_refs": ["services_overview"],
                "slots": {"service": "пирсинг"},
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.82,
                "reason": "unsupported_service_availability",
                "goal": None,
                "entity_refs": [],
                "referents": {
                    "service": {
                        "value": "пирсинг",
                        "entity_type": "service",
                        "source_ref": "message_candidate",
                    }
                },
                "subject_kind": "service",
                "capability": "other",
                "temporal_scope": "none",
                "alternate_datetime": None,
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
                current_message="делаете пирсинг?",
                client_slug="demo_salon",
            )
            == "llm_policy_core_error:fact_consult_tool_action_invalid"
        )
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:fact_consult_tool_action_invalid",
            normalized_memory_profile=None,
            contract=contract,
            current_message="делаете пирсинг?",
            client_slug="demo_salon",
        )
        assert repair is not None
        assert '`tool_action_hint="catalog.service_query"`' in repair
        assert '`tool_action_hint="consult"` is only valid' in repair

    def test_policy_core_rejects_unsupported_service_focused_contract_mismatch(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_COMPACT_FIRST_ATTEMPT",
            False,
        )
        invalid_payload = {
            "intent": "out_of_domain",
            "action": "fact",
            "tool_action_hint": "consult",
            "pack_refs": ["services_overview"],
            "slots": {"service": "пирсинг"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.82,
            "reason": "unsupported_service_availability",
            "goal": None,
            "entity_refs": [],
            "referents": {
                "service": {
                    "value": "пирсинг",
                    "entity_type": "service",
                    "source_ref": "message_candidate",
                }
            },
            "subject_kind": "service",
            "capability": "other",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps(invalid_payload)
            )
            result = route_llm_policy_core(
                "делаете пирсинг?",
                client_slug="demo_salon",
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:focused_contract_mismatch:tool_action_hint"
        )
        assert result["focused_owner_contract_used"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_focuses_customer_identity_before_booking_details(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"name": "Мадина", "phone": "+77055667788"},
            "referents": {
                "customer": {
                    "value": "Мадина",
                    "entity_id": None,
                    "entity_type": "customer",
                    "source_ref": "message_grounding",
                }
            },
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "goal": "booking",
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "clarify_missing_subject",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "reason": "customer_identity_provided_before_booking_details",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Я Мадина, мой номер +77055667788",
                client_slug="demo_salon",
            )

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["focused_identity_first_booking"] is True
        assert forced_fields["slots"] == {"name": "Мадина", "phone": "+77055667788"}
        assert forced_fields["expected_reply_type"] == "service_choice"
        assert forced_fields["next_question"] == "service"
        assert "service" not in forced_fields["slots"]

    def test_policy_core_attaches_contact_to_active_handoff_instead_of_booking_collect(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = focused_contract_response
            result = route_llm_policy_core(
                "Марина 87024445566",
                client_slug="demo_salon",
                memory_profile={
                    "active_goal": "handoff",
                    "semantic_contract": {
                        "subject_kind": "service",
                        "capability": "consultation",
                        "resolution_mode": "direct",
                        "referents": {
                            "service": {
                                "value": "Маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                },
            )

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["focused_handoff_context_contact"] is True
        assert "focused_identity_first_booking" not in result
        assert forced_fields["action"] == "handoff"
        assert forced_fields["tool_action_hint"] == "handoff"
        assert forced_fields["slots"] == {"name": "Марина", "phone": "87024445566"}
        assert forced_fields["referents"]["service"]["value"] == "Маникюр"
        assert result["binding"]["tool_action"] == "handoff"
        assert result["payload"]["requested_outcome"] == "handoff"

    def test_policy_core_keeps_booking_manage_detail_update_on_handoff_context(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = focused_contract_response
            result = route_llm_policy_core(
                "маникюр завтра на 7 вечера",
                client_slug="demo_salon",
                memory_profile={
                    "active_goal": "handoff",
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "booking_manage",
                        "resolution_mode": "direct",
                    },
                },
            )

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["focused_booking_manage_handoff_context"] is True
        assert forced_fields["action"] == "handoff"
        assert forced_fields["tool_action_hint"] == "handoff"
        assert forced_fields["capability"] == "booking_manage"
        assert forced_fields["subject_kind"] == "booking"
        assert forced_fields["slots"]["service"] == "Маникюр"
        assert forced_fields["slots"]["datetime"] == "завтра на 7 вечера"
        assert "focused_start_booking_exact_datetime" not in result
        assert result["binding"]["tool_action"] == "handoff"
        assert result["payload"]["requested_outcome"] == "handoff"

    def test_policy_core_keeps_booking_manage_contact_update_out_of_new_booking_collect(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = focused_contract_response
            result = route_llm_policy_core(
                "Амина, телефон 87073334455",
                client_slug="demo_salon",
                memory_profile={
                    "active_goal": "booking",
                    "semantic_contract": {
                        "subject_kind": "general",
                        "capability": "booking_manage",
                        "requested_effect": "handoff_to_human",
                        "tool_action_hint": "handoff",
                        "needs_human": True,
                        "resolution_mode": "direct",
                    },
                },
            )

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["focused_booking_manage_handoff_context"] is True
        assert "focused_identity_first_booking" not in result
        assert forced_fields["action"] == "handoff"
        assert forced_fields["tool_action_hint"] == "handoff"
        assert forced_fields["slots"] == {"name": "Амина", "phone": "87073334455"}
        assert forced_fields["capability"] == "booking_manage"
        assert forced_fields["subject_kind"] == "general"
        assert result["binding"]["tool_action"] == "handoff"
        assert result["payload"]["requested_outcome"] == "handoff"

    def test_policy_core_does_not_treat_generic_other_service_fact_as_handoff_context(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = focused_contract_response
            result = route_llm_policy_core(
                "Катя 87025556677",
                client_slug="demo_salon",
                current_goal="booking",
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {
                        "service": "пирсинг",
                    },
                    "semantic_contract": {
                        "subject_kind": "service",
                        "capability": "other",
                        "resolution_mode": "policy_fact",
                        "referents": {
                            "service": {
                                "value": "пирсинг",
                                "entity_type": "service",
                                "source_ref": "message_candidate",
                            }
                        },
                    },
                },
            )

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["focused_identity_first_booking"] is True
        assert "focused_handoff_context_contact" not in result
        assert forced_fields["action"] == "collect"
        assert forced_fields["tool_action_hint"] == "collect"
        assert forced_fields["expected_reply_type"] == "service_choice"
        assert result["binding"]["tool_action"] == "collect"
        assert result["payload"]["requested_outcome"] == "collect"

    def test_policy_core_focuses_active_booking_contact_carryover(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = focused_contract_response
            result = route_llm_policy_core(
                "87073334455",
                client_slug="demo_salon",
                current_goal="booking",
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {
                        "service": "Окрашивание",
                        "datetime": "пятница после 18:00",
                        "name": "Айгуль",
                    },
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "resolution_mode": "direct",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "пятница после 18:00",
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                        "referents": {
                            "service": {
                                "value": "Окрашивание",
                                "entity_id": "svc:hair_coloring",
                                "entity_type": "service",
                                "source_ref": "memory.semantic_contract",
                            },
                            "customer": {
                                "value": "Айгуль",
                                "entity_type": "customer",
                                "source_ref": "decision_slots",
                            },
                        },
                    },
                },
            )

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["focused_active_booking_contact_carryover"] is True
        assert forced_fields["goal"] == "booking"
        assert forced_fields["slots"]["service"] == "Окрашивание"
        assert forced_fields["slots"]["datetime"] == "пятница после 18:00"
        assert forced_fields["slots"]["name"] == "Айгуль"
        assert forced_fields["slots"]["phone"] == "87073334455"
        assert forced_fields["alternate_datetime"] == "пятница после 18:00"
        assert forced_fields["expected_reply_type"] == "time"
        assert forced_fields["pending_question_target"] == "time"
        assert result["binding"]["tool_action"] == "collect"
        assert result["payload"]["requested_outcome"] == "collect"
        assert result["payload"]["semantic_slots"]["phone"] == "87073334455"

    def test_policy_core_does_not_treat_booking_confirmation_as_customer_name(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {
                "service": "Окрашивание",
                "datetime": "пятница после 18:00",
                "name": "Айгуль",
                "phone": "87073334455",
            },
            "referents": {
                "service": {
                    "value": "Окрашивание",
                    "entity_id": "svc:hair_coloring",
                    "entity_type": "service",
                    "source_ref": "memory.semantic_contract",
                },
                "customer": {
                    "value": "Айгуль",
                    "entity_type": "customer",
                    "source_ref": "memory.slot_state",
                },
            },
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "goal": "booking",
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "weekday",
            "alternate_datetime": "пятница после 18:00",
            "resolution_mode": "direct",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "reason": "booking_confirmation_does_not_fill_identity",
        }
        memory_profile = {
            "active_goal": "booking",
            "slot_state": {
                "service": "Окрашивание",
                "datetime": "пятница после 18:00",
                "name": "Айгуль",
                "phone": "87073334455",
            },
            "pending_question_contract": {
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
            },
            "semantic_contract": {
                "subject_kind": "booking",
                "capability": "bookability",
                "resolution_mode": "direct",
                "temporal_scope": "weekday",
                "alternate_datetime": "пятница после 18:00",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
                "referents": {
                    "service": {
                        "value": "Окрашивание",
                        "entity_id": "svc:hair_coloring",
                        "entity_type": "service",
                        "source_ref": "memory.semantic_contract",
                    },
                    "customer": {
                        "value": "Айгуль",
                        "entity_type": "customer",
                        "source_ref": "memory.slot_state",
                    },
                },
            },
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "да подтверждаю",
                client_slug="demo_salon",
                current_goal="booking",
                memory_profile=memory_profile,
        )

        assert result["ok"] is True
        assert result.get("focused_active_booking_contact_carryover") is not True
        assert result["focused_active_booking_time_pending_ack"] is True
        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert forced_fields["expected_reply_type"] == "time"
        assert forced_fields["next_question"] == "datetime"
        assert forced_fields["slots"]["datetime"] == "пятница после 18:00"
        assert forced_fields["slots"]["phone"] == "87073334455"
        assert result["payload"]["semantic_slots"]["name"] == "Айгуль"
        assert result["payload"]["semantic_slots"]["phone"] == "87073334455"

    def test_policy_core_focuses_service_datetime_after_identity_to_booking_commit(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "fact",
            "tool_action_hint": "calendar.book_slot",
            "pack_refs": [],
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "goal": "booking",
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "26 октября в 14:00",
            "resolution_mode": "live_calendar",
            "slots": {
                "service": "окрашивание",
                "datetime": "26 октября в 14:00",
                "name": "мадина",
                "phone": "+77055667788",
            },
            "referents": {
                "service": {
                    "value": "окрашивание",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "message_grounding",
                }
            },
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "reason": "active_booking_service_and_datetime_fill_after_identity",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Хочу окрашивание 26 октября в 14:00",
                expected_reply_type="service_choice",
                current_goal="booking",
                slot_state={"name": "мадина", "phone": "+77055667788"},
                client_slug="demo_salon",
                memory_profile={
                    "slot_state": {"name": "мадина", "phone": "+77055667788"},
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                    },
                },
            )

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["focused_active_booking_service_datetime_fill"] is True
        assert forced_fields["tool_action_hint"] == "calendar.book_slot"
        assert forced_fields["slots"]["service"] == "окрашивание"
        assert forced_fields["slots"]["name"] == "мадина"
        assert result["binding"]["tool_action"] == "calendar.book_slot"

    def test_policy_core_focuses_modifier_exact_time_to_memory_service(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "goal": "booking",
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "27 октября в 10:00",
            "resolution_mode": "direct",
            "slots": {"service": "маникюр", "datetime": "27 октября в 10:00"},
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "memory.semantic_contract",
                }
            },
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "fill_requested_slot",
            "reason": "booking_exact_datetime_uses_grounded_memory_service",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Хочу с покрытием 27 октября в 10:00",
                client_slug="demo_salon",
                memory_profile={
                    "semantic_contract": {
                        "subject_kind": "service",
                        "capability": "pricing",
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

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["focused_contextual_memory_service_exact_datetime"] is True
        assert result.get("focused_unknown_service_booking") is not True
        assert forced_fields["slots"]["service"] == "маникюр"
        assert forced_fields["expected_reply_type"] == "name"

    def test_policy_core_focuses_multiple_service_single_visit_to_service_choice(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {
                "service": "маникюр и педикюр",
                "datetime": "22 августа после обеда",
            },
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "goal": "booking",
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "day",
            "alternate_datetime": "22 августа после обеда",
            "resolution_mode": "clarify_missing_subject",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "reason": "multiple_services_require_single_service_choice",
            "referents": {
                "service": {
                    "value": "маникюр и педикюр",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "message_grounding",
                }
            },
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Можно записаться на маникюр и педикюр 22 августа после обеда?",
                client_slug="demo_salon",
            )

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["focused_multiple_service_booking"] is True
        assert forced_fields["tool_action_hint"] == "collect"
        assert forced_fields["expected_reply_type"] == "service_choice"
        assert forced_fields["next_question"] == "service"
        assert forced_fields["open_questions"] == ["service"]
        assert forced_fields["needs_manager"] is False
        assert "маникюр" in forced_fields["slots"]["service"]
        assert "педикюр" in forced_fields["slots"]["service"]

    def test_policy_core_focuses_connectorless_multiple_service_booking_to_service_choice(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр и педикюр"},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "goal": "booking",
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "clarify_missing_subject",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "reason": "multiple_services_require_single_service_choice",
            "referents": {
                "service": {
                    "value": "маникюр и педикюр",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "message_grounding",
                }
            },
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "маникюр педикюр керек",
                client_slug="demo_salon",
            )

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["focused_multiple_service_booking"] is True
        assert forced_fields["expected_reply_type"] == "service_choice"
        assert "маникюр" in forced_fields["slots"]["service"]
        assert "педикюр" in forced_fields["slots"]["service"]

    def test_policy_core_preserves_service_choice_slots_from_messy_followups(self):
        forced_fields = _policy_core_service_choice_slot_carryover_forced_fields(
            {
                "active_goal": "booking",
                "slot_state": {
                    "service": "маникюр и педикюр",
                    "datetime": "ертең",
                },
                "pending_question_contract": {
                    "expected_reply_type": "service_choice",
                    "next_question": "service",
                    "open_questions": ["service"],
                },
                "semantic_contract": {
                    "subject_kind": "booking",
                    "capability": "bookability",
                    "temporal_scope": "day",
                    "alternate_datetime": "ертең",
                },
            },
            current_message="примерно 5 30 вечера",
            grounded_service=None,
        )

        assert forced_fields is not None
        assert forced_fields["expected_reply_type"] == "service_choice"
        assert forced_fields["next_question"] == "service"
        assert forced_fields["slots"]["service"] == "маникюр и педикюр"
        assert forced_fields["slots"]["datetime"] == "ертең 5 30 вечера"
        assert forced_fields["temporal_scope"] == "specific_time"

    def test_policy_core_focuses_service_choice_temporal_carryover(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = focused_contract_response
            result = route_llm_policy_core(
                "ертең",
                client_slug="demo_salon",
                current_goal="booking",
                slot_state={"service": "маникюр и педикюр"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр и педикюр"},
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "referents": {
                            "service": {
                                "value": "маникюр и педикюр",
                                "entity_id": None,
                                "entity_type": "service",
                                "source_ref": "message_grounding",
                            }
                        },
                    },
                },
            )

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["focused_service_choice_slot_carryover"] is True
        assert forced_fields["expected_reply_type"] == "service_choice"
        assert forced_fields["next_question"] == "service"
        assert forced_fields["slots"]["service"] == "маникюр и педикюр"
        assert forced_fields["slots"]["datetime"] == "ертең"

    def test_policy_core_does_not_treat_category_alias_as_multiple_services(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {
                "service": "Брови и ресницы",
                "datetime": "завтра 6 30 вечера",
            },
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "goal": "booking",
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра 6 30 вечера",
            "resolution_mode": "direct",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "reason": "booking_collect_name_for_grounded_service_and_time",
            "referents": {
                "service": {
                    "value": "Брови и ресницы",
                    "entity_id": "svc:brows_lashes",
                    "entity_type": "service",
                    "source_ref": "message_grounding",
                }
            },
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "можно на брови завтра 6 30 вечера",
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result.get("focused_multiple_service_booking") is not True
        assert (
            result["policy_input"].get("focus_contract", {}).get("forced_fields", {}).get("expected_reply_type")
            != "service_choice"
        )

    def test_policy_core_focuses_partial_datetime_with_service_to_time_collect(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "Брови"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "Брови",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "message_grounding",
                }
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "day",
            "alternate_datetime": "29 октября после работы",
            "resolution_mode": "direct",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "reason": "start_booking_partial_datetime_collect_exact_time",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Мне нужно на брови 29 октября после работы",
                client_slug="demo_salon",
            )

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["focused_start_booking_partial_datetime"] is True
        assert forced_fields["slots"]["service"] == "Брови"
        assert forced_fields["alternate_datetime"] == "29 октября после работы"
        assert forced_fields["pending_question_act"] == "slot_constraint"
        assert forced_fields["expected_reply_type"] == "time"

    def test_policy_core_focuses_specialist_relaxation_back_to_name_collect(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "goal": "booking",
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "20 августа в 12:00",
            "resolution_mode": "direct",
            "slots": {"service": "маникюр", "datetime": "20 августа в 12:00"},
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "memory.semantic_contract",
                }
            },
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "fill_requested_slot",
            "reason": "specialist_preference_relaxed_resume_customer_name_collect",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Если Айгерим занята, можно к любому мастеру",
                expected_reply_type="name",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "20 августа в 12:00"},
                client_slug="demo_salon",
                memory_profile={
                    "slot_state": {
                        "service": "маникюр",
                        "datetime": "20 августа в 12:00",
                    },
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "20 августа в 12:00",
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

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["focused_specialist_relaxation"] is True
        assert forced_fields["expected_reply_type"] == "name"
        assert forced_fields["slots"] == {
            "service": "маникюр",
            "datetime": "20 августа в 12:00",
        }

    def test_policy_core_rejects_invalid_booking_manage_reference_inside_booking_collect_time_pending(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "check_booking",
            "action": "fact",
            "tool_action_hint": "calendar.get_booking",
            "pack_refs": [],
            "slots": {},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "Нужно найти существующую запись для отмены, booking_ref отсутствует; запускаем поиск через calendar.get_booking и запрашиваем дату/время.",
            "subject_kind": "booking",
            "capability": "booking_manage",
            "temporal_scope": "none",
            "resolution_mode": "direct",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "А если я захочу отменить запись?",
                client_slug="demo_salon",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "завтра"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "resolution_mode": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
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

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert result["schema_error"].startswith(
            "llm_policy_core_error:focused_contract_mismatch:"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_rejects_invalid_booking_manage_reference_followup_after_slot_constraint_interrupt(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "calendar.cancel",
            "pack_refs": [],
            "slots": {},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "reason": (
                "Пользователь интересуется отменой записи. Для выполнения отмены нужна "
                "идентификация записи, поэтому запрашиваем недостающий идентификатор. "
                "Активный контракт по выбору времени сохраняем без изменения."
            ),
            "subject_kind": "booking",
            "capability": "booking_manage",
            "temporal_scope": "day",
            "alternate_datetime": "завтра",
            "resolution_mode": "clarify_missing_time",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "А если я захочу отменить запись?",
                client_slug="demo_salon",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "завтра"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "resolution_mode": "ask_about_requested_slot",
                        "alternate_datetime": "завтра",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
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

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert result["schema_error"].startswith(
            "llm_policy_core_error:focused_contract_mismatch:"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_rejects_invalid_booking_manage_name_required_followup_after_time_answer(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {
                "service": "маникюр",
                "datetime": "завтра 19:00",
            },
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "reason": (
                "Пользователь согласовал время 19:00 для услуги «маникюр» на завтра; "
                "теперь нужно уточнить имя клиента для поиска/подтверждения записи."
            ),
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "day",
            "resolution_mode": "clarify_missing_time",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "fill_requested_slot",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Можно на 19:00?",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "завтра"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                        "reason": "calendar_get_booking_collect_reference",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "booking_manage",
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

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:booking_manage_reference_action_invalid"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_rejects_booking_manage_reference_stale_axes_when_missing_customer(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "check_booking",
            "action": "fact",
            "tool_action_hint": "calendar.get_booking",
            "pack_refs": [],
            "slots": {},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "reason": (
                "Пользователь просит подтвердить запись, но booking_ref не подтверждён. "
                "Нужна проверка записи через calendar.get_booking; для поиска требуется имя "
                "(pending question_contract ожидает имя). Активный pending slot по времени "
                "не заполнен, поэтому он сохраняется без изменения."
            ),
            "subject_kind": "booking",
            "capability": "booking_manage",
            "temporal_scope": "day",
            "resolution_mode": "direct",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Подтвердите, что я записан на маникюр.",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "сегодня"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                        "reason": (
                            "Пользователь спрашивает гипотетически про отмену записи. "
                            "Прямое выполнение отмены без подтверждённого booking_ref нельзя"
                        ),
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "resolution_mode": "ask_about_requested_slot",
                        "temporal_scope": "day",
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
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

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:booking_manage_reference_stale_axes"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_allows_explicit_manager_handoff_inside_booking_manage_reference_followup(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = focused_contract_response
            result = route_llm_policy_core(
                "Можно связаться с менеджером?",
                current_goal="booking",
                slot_state={"service": "маникюр", "name": "Амина"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "reason": "calendar_get_booking_collect_reference",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "booking_manage",
                        "resolution_mode": "clarify_missing_time",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            },
                            "customer": {
                                "value": "Амина",
                                "entity_id": None,
                                "entity_type": "customer",
                                "source_ref": "runtime_grounding",
                            },
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is False
        assert result["binding"]["tool_action"] == "handoff"
        assert result["binding_plan"]["binding_outcome_type"] == "handoff"
        assert result["payload"]["requested_outcome"] == "handoff"
        assert result["payload"]["tool_action_hint"] == "handoff"
        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert forced_fields["expected_reply_type"] is None
        assert forced_fields["next_question"] is None
        assert forced_fields["open_questions"] == []
        assert forced_fields["pending_question_act"] is None
        assert forced_fields["pending_question_target"] is None
        assert forced_fields["active_question_relation"] is None
        assert forced_fields["referents"]["customer"]["value"] == "Амина"

    def test_policy_core_forces_cancel_interrupt_to_admin_handoff(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = focused_contract_response
            result = route_llm_policy_core(
                "А если я захочу отменить запись?",
                client_slug="demo_salon",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "завтра"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "resolution_mode": "ask_about_requested_slot",
                        "alternate_datetime": "завтра",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
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
        assert result["focused_policy_handoff"] is True
        assert result["binding"]["tool_action"] == "handoff"
        assert result["binding_plan"]["binding_outcome_type"] == "handoff"
        assert result["payload"]["requested_outcome"] == "handoff"
        assert result["payload"]["capability_id"] == "booking_manage"
        assert result["payload"]["intent"] == "cancel_request"
        assert result["payload"]["risk_signals"] == ["cancel"]
        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert forced_fields["open_questions"] == []
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_hypothetical_cancel_with_booking_ref_forces_admin_handoff(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = focused_contract_response
            result = route_llm_policy_core(
                "А если я захочу отменить запись?",
                client_slug="demo_salon",
                current_goal="booking",
                slot_state={
                    "service": "маникюр",
                    "datetime": "завтра 18:00",
                    "name": "Амина",
                },
                memory_profile={
                    "slot_state": {
                        "service": "маникюр",
                        "datetime": "завтра 18:00",
                        "name": "Амина",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "booking_manage",
                        "resolution_mode": "direct",
                        "referents": {
                            "booking_ref": {
                                "value": "apt-1",
                                "entity_type": "booking_ref",
                                "source_ref": "execution",
                            },
                            "customer": {
                                "value": "Амина",
                                "entity_type": "customer",
                                "source_ref": "decision_slots",
                            },
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            },
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["focused_policy_handoff"] is True
        assert result["binding"]["tool_action"] == "handoff"
        assert result["binding_plan"]["binding_outcome_type"] == "handoff"
        assert result["payload"]["requested_outcome"] == "handoff"
        assert result["payload"]["capability_id"] == "booking_manage"
        assert result["payload"]["intent"] == "cancel_request"
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_direct_cancel_with_booking_ref_forces_admin_handoff(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = focused_contract_response
            result = route_llm_policy_core(
                "Тогда отмените запись.",
                client_slug="demo_salon",
                current_goal="booking",
                slot_state={
                    "service": "маникюр",
                    "datetime": "завтра 18:00",
                    "name": "Амина",
                },
                memory_profile={
                    "slot_state": {
                        "service": "маникюр",
                        "datetime": "завтра 18:00",
                        "name": "Амина",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "booking_manage",
                        "resolution_mode": "direct",
                        "referents": {
                            "booking_ref": {
                                "value": "apt-1",
                                "entity_type": "booking_ref",
                                "source_ref": "execution",
                            },
                            "customer": {
                                "value": "Амина",
                                "entity_type": "customer",
                                "source_ref": "decision_slots",
                            },
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            },
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is False
        assert result["binding"]["tool_action"] == "handoff"
        assert result["binding_plan"]["binding_outcome_type"] == "handoff"
        assert result["payload"]["requested_outcome"] == "handoff"
        assert result["payload"]["tool_action_hint"] == "handoff"
        assert result["payload"]["capability_id"] == "booking_manage"
        assert result["payload"]["intent"] == "cancel_request"
        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert forced_fields["referents"]["booking_ref"]["value"] == "apt-1"
        assert forced_fields["slots"]["name"] == "Амина"

    def test_policy_core_rejects_invalid_active_booking_manage_interrupt_out_of_generic_info(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": [],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "Пользователь спрашивает, как отменить запись. Это информационный запрос о процедуре отмены.",
            "subject_kind": "booking",
            "capability": "booking_manage",
            "temporal_scope": "day",
            "resolution_mode": "policy_fact",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "А если я захочу отменить запись?",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "завтра"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "resolution_mode": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
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

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:booking_manage_reference_tool_action_invalid"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_rejects_invalid_booking_manage_name_fill_followup_contract(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"name": "Амина", "service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "Укажите, пожалуйста, примерную дату и время для записи на маникюр.",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "active booking_manage follow-up requires customer name to find an existing record; user provided the customer name",
            "subject_kind": "booking",
            "capability": "booking_manage",
            "temporal_scope": "day",
            "resolution_mode": "clarify_missing_time",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Меня зовут Амина.",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "booking_manage",
                        "resolution_mode": "clarify_missing_subject",
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

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:booking_manage_name_fill_followup_invalid"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_rejects_invalid_booking_manage_name_fill_followup_after_stale_name_retry(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "check_booking",
            "action": "fact",
            "tool_action_hint": "calendar.get_booking",
            "pack_refs": [],
            "slots": {"name": "Амина"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "reason": "Для проверки существующей записи нет referents.booking_ref, поэтому выполняем calendar.get_booking и запрашиваем/подтверждаем имя клиента.",
            "subject_kind": "booking",
            "capability": "booking_manage",
            "temporal_scope": "none",
            "resolution_mode": "direct",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Меня зовут Амина.",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "booking_manage",
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

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:booking_manage_name_fill_followup_invalid"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_rejects_booking_manage_name_fill_followup_when_only_stale_memory_time_exists(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "check_booking",
            "action": "fact",
            "tool_action_hint": "calendar.get_booking",
            "pack_refs": [],
            "slots": {"name": "Амина", "service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "reason": "Контекст booking-manage уже содержит клиента (Амина) и время (19:00); для проверки существующей записи выполняем calendar.get_booking без follow-up вопросов.",
            "subject_kind": "booking",
            "capability": "booking_manage",
            "temporal_scope": "day",
            "resolution_mode": "direct",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Меня зовут Амина.",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "19:00"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "booking_manage",
                        "resolution_mode": "clarify_missing_time",
                        "alternate_datetime": "19:00",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                    "slot_state": {"service": "маникюр", "datetime": "19:00"},
                },
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:booking_manage_name_fill_followup_invalid"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_keeps_booking_manage_name_fill_progression_on_full_prompt(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        valid_payload = {
            "intent": "check_booking",
            "action": "fact",
            "tool_action_hint": "calendar.get_booking",
            "pack_refs": [],
            "slots": {"name": "Амина", "service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": (
                "Пользователь сообщил имя для проверки существующей записи; "
                "booking_ref еще не найден, поэтому продолжаем поиск через "
                "calendar.get_booking и просим дату/время записи."
            ),
            "subject_kind": "booking",
            "capability": "booking_manage",
            "temporal_scope": "none",
            "resolution_mode": "direct",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "referents": {
                "customer": {
                    "value": "Амина",
                    "entity_type": "customer",
                    "source_ref": "user_text",
                },
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
            },
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
            result = route_llm_policy_core(
                "Меня зовут Амина.",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                        "reason": "user_requests_check_existing_booking_without_booking_ref",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "booking_manage",
                        "resolution_mode": "direct",
                        "temporal_scope": "none",
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
        assert result["compact_input_used"] is False
        assert result["compact_retry_used"] is False
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["binding"]["tool_action"] == "calendar.get_booking"
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["tool_action_hint"] == "calendar.get_booking"
        assert result["payload"]["semantic_slots"]["name"] == "Амина"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_allows_booking_manage_name_fill_followup_when_current_turn_supplies_datetime(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        valid_payload = {
            "intent": "check_booking",
            "action": "fact",
            "tool_action_hint": "calendar.get_booking",
            "pack_refs": [],
            "slots": {"name": "Амина", "service": "маникюр", "datetime": "19:00"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "reason": "Имя клиента и время уже заземлены в текущем сообщении, поэтому для проверки существующей записи выполняем calendar.get_booking без дополнительных follow-up вопросов.",
            "subject_kind": "booking",
            "capability": "booking_manage",
            "temporal_scope": "day",
            "resolution_mode": "direct",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [DummyResponse(json.dumps(valid_payload))]
            result = route_llm_policy_core(
                "Меня зовут Амина, можно на 19:00?",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "19:00"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "booking_manage",
                        "resolution_mode": "clarify_missing_time",
                        "alternate_datetime": "19:00",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                    "slot_state": {"service": "маникюр", "datetime": "19:00"},
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "calendar.get_booking"
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["tool_action_hint"] == "calendar.get_booking"
        assert result["payload"]["missing_information"]["open_questions"] == []

    def test_policy_core_allows_booking_manage_datetime_fill_followup_when_customer_already_grounded(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        valid_payload = {
            "intent": "check_booking",
            "action": "fact",
            "tool_action_hint": "calendar.get_booking",
            "pack_refs": [],
            "slots": {"name": "Амина", "datetime": "завтра в 18:00"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "reason": (
                "Customer and exact datetime are already grounded for the existing "
                "booking lookup, so we execute calendar.get_booking without another "
                "follow-up question."
            ),
            "subject_kind": "booking",
            "capability": "booking_manage",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра в 18:00",
            "resolution_mode": "direct",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "referents": {
                "customer": {
                    "value": "Амина",
                    "entity_id": "cust:amina",
                    "entity_type": "customer",
                    "source_ref": "user",
                }
            },
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [DummyResponse(json.dumps(valid_payload))]
            result = route_llm_policy_core(
                "На завтра в 18:00.",
                current_goal="booking",
                slot_state={"name": "Амина"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "reason": "calendar_get_booking_collect_reference_name_provided",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "booking_manage",
                        "resolution_mode": "direct",
                        "temporal_scope": "none",
                        "referents": {
                            "customer": {
                                "value": "Амина",
                                "entity_id": "cust:amina",
                                "entity_type": "customer",
                                "source_ref": "user",
                            }
                        },
                    },
                    "slot_state": {"name": "Амина"},
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["compact_input_used"] is False
        assert result["compact_retry_used"] is False
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["binding"]["tool_action"] == "calendar.get_booking"
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["tool_action_hint"] == "calendar.get_booking"
        assert result["payload"]["semantic_slots"]["name"] == "Амина"
        assert result["payload"]["semantic_slots"]["datetime"] == "завтра в 18:00"
        assert result["payload"]["missing_information"]["open_questions"] == []

    def test_policy_core_rejects_invalid_booking_manage_name_fill_followup_when_llm_switches_to_booking_collect(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"name": "Амина"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "Имя пользователя получено и соответствует ожидаемому ответу по активному pending_question_contract (name). Для завершения записи далее нужен желаемый день/время.",
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "none",
            "resolution_mode": "direct",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Меня зовут Амина.",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "booking_manage",
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

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:booking_manage_name_fill_followup_invalid"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_rejects_invalid_active_booking_customer_name_carryover_contract(
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
            "reason": "active booking slot-constraint still waits for precise time, but the current turn already grounded the customer name",
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра вечером",
            "resolution_mode": "direct",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "entity_refs": [
                {
                    "entity_type": "customer",
                    "value": "Амина",
                    "confidence": 0.8,
                }
            ],
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
                    "source_ref": "carryover",
                },
            },
        }
        repaired_payload = {
            **invalid_payload,
            "slots": {"service": "маникюр", "name": "Амина"},
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Меня зовут Амина.",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "resolution_mode": "direct",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "завтра вечером",
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
                                "source_ref": "carryover",
                            },
                        },
                    },
                },
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:active_booking_customer_name_carryover_required"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_allows_canonical_active_booking_customer_name_carryover_contract(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр", "name": "Амина"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "active_booking_customer_name_carryover",
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра вечером",
            "resolution_mode": "direct",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
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
                    "source_ref": "carryover",
                },
            },
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Меня зовут Амина.",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "resolution_mode": "direct",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "завтра вечером",
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
                                "source_ref": "carryover",
                            },
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["compact_input_used"] is False
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["binding"]["tool_action"] == "collect"
        assert result["payload"]["requested_outcome"] == "collect"
        assert result["payload"]["tool_action_hint"] == "collect"
        assert result["payload"]["semantic_slots"]["name"] == "Амина"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert result["payload"]["missing_information"]["pending_question_act"] == "slot_constraint"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "slot_constraint"

    def test_policy_core_service_choice_temporal_followup_does_not_reclassify_as_time(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action_hint": "collect",
                "pack_refs": [],
                "slots": {"service": None, "datetime": None, "name": None, "phone": None},
                "expected_reply_type": "service_choice",
                "next_question": "service",
                "open_questions": ["service"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.72,
                "reason": "time clue while service choice is still missing",
                "goal": "booking",
                "entity_refs": [],
                "referents": {},
                "subject_kind": "general",
                "capability": "bookability",
                "temporal_scope": "day",
                "alternate_datetime": "завтра",
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
                normalized_memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                    },
                    "semantic_contract": {
                        "subject_kind": "general",
                        "capability": "bookability",
                        "resolution_mode": "clarify_missing_subject",
                        "temporal_scope": "day",
                        "alternate_datetime": "завтра",
                        "referents": {"service": {"value": "Маникюр"}},
                    },
                },
                current_message="после работы",
            )
            is None
        )

    def test_policy_core_rejects_invalid_active_booking_bare_customer_name_carryover_contract(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр", "name": "Аружан"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "specialist carry-over incorrectly stole a bare customer-name reply",
            "subject_kind": "specialist",
            "capability": "bookability",
            "temporal_scope": "day",
            "alternate_datetime": "завтра вечером",
            "resolution_mode": "referent_followup",
            "pending_question_act": None,
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
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
                    "source_ref": "carryover",
                },
            },
        }
        repaired_payload = {
            **invalid_payload,
            "subject_kind": "booking",
            "resolution_mode": "direct",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Аружан",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "завтра вечером"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "resolution_mode": "direct",
                        "temporal_scope": "day",
                        "alternate_datetime": "завтра вечером",
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
                                "source_ref": "carryover",
                            },
                        },
                    },
                },
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:active_booking_customer_name_carryover_required"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_allows_canonical_active_booking_bare_customer_name_carryover_contract(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр", "name": "Аружан"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "active_booking_customer_name_carryover",
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "day",
            "alternate_datetime": "завтра вечером",
            "resolution_mode": "direct",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
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
                    "source_ref": "carryover",
                },
            },
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Аружан",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "завтра вечером"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "resolution_mode": "direct",
                        "temporal_scope": "day",
                        "alternate_datetime": "завтра вечером",
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
                                "source_ref": "carryover",
                            },
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["payload"]["semantic_slots"]["name"] == "Аружан"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "booking"
        assert result["payload"]["grounding_requirements"]["resolution_mode"] == "direct"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "slot_constraint"

    def test_policy_core_rejects_invalid_active_booking_time_completion_after_name_carryover(
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
            "reason": "active booking slot-constraint still waits for precise time even though the user supplied a concrete clock time",
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра 18:00",
            "resolution_mode": "direct",
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
                    "source_ref": "carryover",
                },
            },
        }
        repaired_payload = {
            **invalid_payload,
            "action": "fact",
            "tool_action_hint": "calendar.book_slot",
            "slots": {
                "service": "маникюр",
                "datetime": "завтра 18:00",
                "name": "Амина",
                "phone": "87011234567",
            },
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "reason": "booking_commit_ready_after_explicit_time_completion",
            "entity_refs": [
                {
                    "entity_type": "customer",
                    "value": "Амина",
                    "confidence": 0.8,
                }
            ],
            "resolution_mode": "live_calendar",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Давайте в 18:00.",
                current_goal="booking",
                slot_state={
                    "service": "маникюр",
                    "datetime": "завтра вечером",
                    "name": "Амина",
                    "phone": "87011234567",
                },
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "resolution_mode": "direct",
                        "temporal_scope": "day",
                        "alternate_datetime": "завтра вечером",
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
                                "source_ref": "carryover",
                            },
                            "customer": {
                                "value": "Амина",
                                "entity_type": "customer",
                                "source_ref": "slot_state",
                            },
                        },
                    },
                },
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:active_booking_commit_progression_required"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_allows_canonical_active_booking_commit_after_name_carryover(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "fact",
            "tool_action_hint": "calendar.book_slot",
            "pack_refs": [],
            "slots": {
                "service": "маникюр",
                "datetime": "завтра 18:00",
                "name": "Амина",
                "phone": "87011234567",
            },
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "reason": "booking_commit_ready_after_explicit_time_completion",
            "entity_refs": [
                {
                    "entity_type": "customer",
                    "value": "Амина",
                    "confidence": 0.8,
                }
            ],
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра 18:00",
            "resolution_mode": "live_calendar",
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
                "specialist": {
                    "value": "Айгерим",
                    "entity_type": "specialist",
                    "source_ref": "carryover",
                },
                "customer": {
                    "value": "Амина",
                    "entity_type": "customer",
                    "source_ref": "slot_state",
                },
            },
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Давайте в 18:00.",
                current_goal="booking",
                slot_state={
                    "service": "маникюр",
                    "datetime": "завтра вечером",
                    "name": "Амина",
                    "phone": "87011234567",
                },
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "resolution_mode": "direct",
                        "temporal_scope": "day",
                        "alternate_datetime": "завтра вечером",
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
                                "source_ref": "carryover",
                            },
                            "customer": {
                                "value": "Амина",
                                "entity_type": "customer",
                                "source_ref": "slot_state",
                            },
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["binding"]["tool_action"] == "calendar.book_slot"
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["tool_action_hint"] == "calendar.book_slot"
        assert result["payload"]["semantic_slots"]["name"] == "Амина"
        assert result["payload"]["semantic_slots"]["phone"] == "87011234567"
        assert result["payload"]["semantic_slots"]["datetime"] == "завтра 18:00"
        assert result["payload"]["missing_information"] == {"open_questions": []}

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
                "phone": "87011234567",
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
                        "phone": "87011234567",
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

    def test_policy_core_rejects_invalid_generic_info_interrupt_followup_contract(
        self, monkeypatch
    ):
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
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
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

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:generic_info_interrupt_expected_reply_invalid"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_allows_generic_info_interrupt_with_slot_constraint_carryover(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "promotions",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["promotions"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "user_asked_promotions_during_active_booking_continuity",
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
            "capability": "promotions",
            "temporal_scope": "day",
            "alternate_datetime": "завтра вечером",
            "resolution_mode": "policy_fact",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Есть ли акции?",
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
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "temporal_scope": "day",
                        "alternate_datetime": "завтра вечером",
                        "resolution_mode": "direct",
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
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
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["promotions"]
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "завтра вечером"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["pending_question_act"] == "slot_constraint"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "generic_info_interrupt"

    def test_policy_core_rejects_invalid_catalog_location_interrupt_without_carryover_followup(
        self, monkeypatch
    ):
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
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
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

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:generic_info_interrupt_expected_reply_invalid"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

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
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "alternate_datetime": "11:30",
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
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "11:30"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert result["payload"]["missing_information"]["pending_question_act"] == "slot_constraint"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "slot_constraint"

    def test_policy_core_rejects_invalid_start_booking_partial_day_clue_into_slot_constraint(
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
            "reason": "booking_start_collect_datetime_for_requested_service",
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
            "temporal_scope": "none",
            "resolution_mode": "direct",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
        }
        repaired_payload = {
            **invalid_payload,
            "subject_kind": "booking",
            "temporal_scope": "weekday",
            "pending_question_act": "slot_constraint",
            "active_question_relation": "slot_constraint",
            "alternate_datetime": "понедельник",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Я хочу записаться на маникюр на понедельник.",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр"},
                },
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:start_booking_temporal_clue_reclassification_required"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_allows_canonical_start_booking_partial_day_clue_into_slot_constraint(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "start_booking_temporal_clue_slot_constraint",
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
            "capability": "bookability",
            "temporal_scope": "day",
            "alternate_datetime": "завтра вечером",
            "resolution_mode": "direct",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Хочу записаться на маникюр завтра вечером.",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр"},
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["binding"]["tool_action"] == "collect"
        assert result["payload"]["requested_outcome"] == "collect"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "booking"
        assert result["payload"]["grounding_requirements"]["temporal_scope"] == "day"
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "завтра вечером"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert result["payload"]["missing_information"]["pending_question_act"] == "slot_constraint"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "slot_constraint"

    def test_policy_core_rejects_start_booking_partial_day_clue_that_keeps_subject_kind_service(
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
            "reason": "user_provided_service_and_daypart_but_no_exact_time_yet",
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
            "temporal_scope": "day",
            "alternate_datetime": "завтра вечером",
            "resolution_mode": "direct",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps(invalid_payload)
            )
            result = route_llm_policy_core(
                "Хочу записаться на маникюр завтра вечером.",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр"},
                },
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:start_booking_temporal_clue_reclassification_required"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False

    def test_validate_policy_core_runtime_contract_flags_start_booking_exact_datetime_progression(
        self,
    ):
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "booking_needs_datetime_slot_value",
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
            "capability": "bookability",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "ask_about_requested_slot",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
        }
        contract, schema_error = validate_llm_policy_core_output(payload)
        normalized_memory_profile = _normalize_policy_core_memory_profile(
            {
                "slot_state": {"service": "маникюр"},
                "semantic_contract": {
                    "capability": "pricing",
                    "subject_kind": "service",
                    "resolution_mode": "policy_fact",
                    "temporal_scope": "none",
                    "referents": {
                        "service": {
                            "value": "маникюр",
                            "entity_type": "service",
                            "source_ref": "carryover",
                        }
                    },
                },
            }
        )

        assert schema_error is None
        assert contract is not None
        assert (
            _policy_core_current_message_exact_datetime_surface(
                "Хочу записаться завтра в 18:00"
            )
            == "завтра в 18:00"
        )
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile=normalized_memory_profile,
                current_message="Хочу записаться завтра в 18:00",
            )
            == "llm_policy_core_error:start_booking_exact_datetime_progression_required"
        )

        instruction = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:start_booking_exact_datetime_progression_required",
            current_message="Хочу записаться завтра в 18:00",
            contract=contract,
            normalized_memory_profile=normalized_memory_profile,
        )
        assert instruction is not None
        assert '`capability="bookability"`' in instruction
        assert '`resolution_mode="direct"`' in instruction
        assert '`expected_reply_type="name"`' in instruction
        assert '`active_question_relation="fill_requested_slot"`' in instruction
        assert 'slots.datetime="завтра в 18:00"' in instruction
        assert 'alternate_datetime="завтра в 18:00"' in instruction
        assert '`alternate_datetime=null`' in instruction
        assert 'Do NOT ask for date/time again' in instruction

    def test_policy_core_rejects_start_booking_exact_datetime_owner_mismatch_without_boundary_normalization(
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
            "reason": "booking_needs_datetime_slot_value",
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
            "capability": "bookability",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "ask_about_requested_slot",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Хочу записаться завтра в 18:00",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "slot_state": {"service": "маникюр"},
                    "semantic_contract": {
                        "capability": "pricing",
                        "subject_kind": "service",
                        "resolution_mode": "policy_fact",
                        "temporal_scope": "none",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                },
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert result["schema_error"] == (
            "llm_policy_core_error:focused_contract_mismatch:expected_reply_type"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["focused_contextual_memory_service_exact_datetime"] is True
        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert forced_fields["expected_reply_type"] == "name"
        assert forced_fields["next_question"] == "name"
        assert forced_fields["slots"]["service"] == "маникюр"
        assert forced_fields["slots"]["datetime"] == "завтра в 18:00"
        assert (
            forced_fields["referents"]["service"]["source_ref"]
            == "memory.semantic_contract"
        )
        assert result["attempt_count"] == 1
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_rejects_start_booking_exact_datetime_overcommit_without_customer(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "fact",
            "tool_action_hint": "calendar.book_slot",
            "pack_refs": [],
            "slots": {"service": "педикюр", "datetime": "пятницу 15:30"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "reason": "service_and_requested_time_provided",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "педикюр",
                    "entity_id": "svc:pedicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": None,
            "resolution_mode": "live_calendar",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Запишите меня на пятницу в 15:30",
                current_goal="booking",
                slot_state={"service": "педикюр"},
                memory_profile={
                    "slot_state": {"service": "педикюр"},
                    "semantic_contract": {
                        "capability": "duration",
                        "subject_kind": "service",
                        "resolution_mode": "policy_fact",
                        "temporal_scope": "none",
                        "referents": {
                            "service": {
                                "value": "педикюр",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                },
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert result["schema_error"] == (
            "llm_policy_core_error:focused_contract_mismatch:action"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["focused_contextual_memory_service_exact_datetime"] is True
        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert forced_fields["action"] == "collect"
        assert forced_fields["tool_action_hint"] == "collect"
        assert forced_fields["slots"]["service"] == "педикюр"
        assert forced_fields["slots"]["datetime"] == "пятницу в 15:30"
        assert forced_fields["expected_reply_type"] == "name"
        assert result["attempt_count"] == 1
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_boundary_preserves_start_booking_exact_datetime_without_normalization(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        canonical_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр", "datetime": "завтра в 18:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "reason": "booking_exact_datetime_uses_grounded_memory_service",
            "goal": "booking",
            "entity_refs": {"service": "маникюр"},
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "memory.semantic_contract",
                }
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра в 18:00",
            "resolution_mode": "direct",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "fill_requested_slot",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(canonical_payload))
            result = route_llm_policy_core(
                "Хочу записаться завтра в 18:00",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "slot_state": {"service": "маникюр"},
                    "semantic_contract": {
                        "capability": "pricing",
                        "subject_kind": "service",
                        "resolution_mode": "policy_fact",
                        "temporal_scope": "none",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["focused_contextual_memory_service_exact_datetime"] is True
        assert result["binding"]["tool_action"] == "collect"
        assert result["payload"]["requested_outcome"] == "collect"
        assert result["payload"]["grounding_requirements"]["resolution_mode"] == "direct"
        assert (
            result["payload"]["grounding_requirements"]["alternate_datetime"]
            == "завтра в 18:00"
        )
        assert result["payload"]["missing_information"]["expected_reply_type"] == "name"

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

    def test_validate_policy_core_runtime_contract_flags_hybrid_availability_question_with_day_clue(
        self,
    ):
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
            "reason": "active_booking_availability_question_with_day_clue",
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
            "capability": "bookability",
            "temporal_scope": "none",
            "resolution_mode": "ask_about_requested_slot",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
        }
        contract, schema_error = validate_llm_policy_core_output(invalid_payload)

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile={
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
                        "subject_kind": "booking",
                        "temporal_scope": "none",
                        "resolution_mode": "ask_about_requested_slot",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                        "referents": invalid_payload["referents"],
                    },
                },
                current_message="У вас есть время на сегодня?",
            )
            == "llm_policy_core_error:active_booking_temporal_clue_followup_reclassification_required"
        )

    def test_policy_core_grounded_temporal_scope_hint_for_hybrid_availability_question(self):
        assert (
            _policy_core_current_message_grounded_temporal_scope_hint(
                "У вас есть время на сегодня?"
            )
            == "day"
        )
        assert (
            _policy_core_current_message_grounded_temporal_scope_hint(
                "А как насчет пятницы на утро?"
            )
            == "weekday"
        )
        assert (
            _policy_core_current_message_grounded_temporal_scope_hint(
                "Можно после 17:00?"
            )
            == "specific_time"
        )

    def test_policy_core_repairs_hybrid_availability_question_with_day_clue_into_slot_constraint(
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
            "reason": "active_booking_availability_question_with_day_clue",
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
            "capability": "bookability",
            "temporal_scope": "none",
            "resolution_mode": "ask_about_requested_slot",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
        }
        repaired_payload = {
            **invalid_payload,
            "temporal_scope": "day",
            "pending_question_act": "slot_constraint",
            "active_question_relation": "slot_constraint",
            "alternate_datetime": "сегодня",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "У вас есть время на сегодня?",
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
                        "subject_kind": "booking",
                        "temporal_scope": "none",
                        "resolution_mode": "ask_about_requested_slot",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                        "referents": invalid_payload["referents"],
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
        assert result["payload"]["grounding_requirements"]["temporal_scope"] == "day"
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "сегодня"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert result["payload"]["missing_information"]["pending_question_act"] == "slot_constraint"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "slot_constraint"

    def test_validate_policy_core_runtime_contract_flags_booking_availability_without_service_day_clue(
        self,
    ):
        invalid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "user_requests_availability_for_tomorrow_service_known",
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
            "capability": "bookability",
            "temporal_scope": "day",
            "alternate_datetime": "на завтра",
            "resolution_mode": "ask_about_requested_slot",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
        }
        contract, schema_error = validate_llm_policy_core_output(invalid_payload)

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile=None,
                current_message="На завтра есть время?",
                context_payload=None,
                client_slug="demo_salon",
            )
            == "llm_policy_core_error:booking_availability_missing_service_reclassification_required"
        )

    def test_validate_policy_core_runtime_contract_flags_missing_service_when_day_scope_is_widened(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action_hint": "collect",
                "pack_refs": [],
                "slots": {"service": None, "datetime": None, "name": None, "phone": None},
                "expected_reply_type": "service_choice",
                "next_question": "service",
                "open_questions": ["service"],
                "needs_manager": False,
                "reason": "service_missing_for_time_availability_request",
                "goal": "booking",
                "entity_refs": [],
                "referents": {},
                "subject_kind": "general",
                "capability": "bookability",
                "temporal_scope": "date_range",
                "alternate_datetime": None,
                "resolution_mode": "clarify_missing_subject",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile=None,
                current_message="На завтра есть время?",
                context_payload=None,
                client_slug="demo_salon",
            )
            == "llm_policy_core_error:booking_availability_missing_service_reclassification_required"
        )

    def test_policy_core_normalizes_invalid_booking_availability_without_service_day_clue(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "user_requests_availability_for_tomorrow_service_known",
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
            "capability": "bookability",
            "temporal_scope": "day",
            "alternate_datetime": "на завтра",
            "resolution_mode": "ask_about_requested_slot",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "На завтра есть время?",
                current_goal="booking",
                slot_state={},
                memory_profile=None,
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is True
        assert result["attempt_count"] == 1
        assert result["binding"]["tool_action"] == "collect"
        assert result["payload"]["requested_outcome"] == "collect"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "general"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "service_choice"
        assert result["payload"]["missing_information"]["next_question"] == "service"
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_allows_canonical_booking_availability_without_service_day_clue(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "reason": "service_missing_for_time_availability_request",
            "goal": "booking",
            "referents": {},
            "subject_kind": "general",
            "capability": "bookability",
            "temporal_scope": "day",
            "alternate_datetime": "на завтра",
            "resolution_mode": "clarify_missing_subject",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "На завтра есть время?",
                current_goal="booking",
                slot_state={},
                memory_profile=None,
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["binding"]["tool_action"] == "collect"
        assert result["payload"]["requested_outcome"] == "collect"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "general"
        assert result["payload"]["grounding_requirements"]["temporal_scope"] == "day"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "service_choice"
        assert result["payload"]["missing_information"]["next_question"] == "service"
        assert result["payload"]["missing_information"]["open_questions"] == ["service"]

    def test_policy_core_allows_canonical_booking_availability_without_service_exact_time(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"datetime": "завтра в 18:00"},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "reason": "requested_slot_time_provided_but_service_not_grounded_in_current_turn",
            "goal": "booking",
            "referents": {},
            "subject_kind": "general",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра в 18:00",
            "resolution_mode": "clarify_missing_subject",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "На завтра в 18:00 есть время?",
                current_goal="booking",
                slot_state={},
                memory_profile=None,
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["binding"]["tool_action"] == "collect"
        assert result["payload"]["requested_outcome"] == "collect"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "general"
        assert result["payload"]["grounding_requirements"]["temporal_scope"] == "specific_time"
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "завтра в 18:00"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "service_choice"
        assert result["payload"]["missing_information"]["next_question"] == "service"
        assert result["payload"]["missing_information"]["open_questions"] == ["service"]

    def test_policy_core_allows_service_grounding_fact_interrupt_to_advance_missing_service_exact_datetime_progression(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["master"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "reason": "missing_service_exact_datetime_grounded_via_fact_interrupt_progression",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "subject_kind": "service",
            "capability": "master",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра в 18:00",
            "resolution_mode": "policy_fact",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Кто делает маникюр?",
                current_goal="booking",
                slot_state={},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"datetime": "завтра в 18:00"},
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "reason": "booking_availability_with_exact_datetime_but_service_missing",
                    },
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "capability": "bookability",
                        "subject_kind": "general",
                        "resolution_mode": "clarify_missing_subject",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "завтра в 18:00",
                    },
                },
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["binding"]["tool_action"] == "info"
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["grounding_requirements"]["temporal_scope"] == "specific_time"
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "завтра в 18:00"
        assert (
            result["payload"]["grounding_requirements"]["resolution_mode"]
            == "policy_fact"
        )
        assert result["payload"]["missing_information"]["expected_reply_type"] == "name"
        assert result["payload"]["missing_information"]["next_question"] == "name"
        assert result["payload"]["missing_information"]["open_questions"] == ["name"]
        assert result["payload"]["missing_information"]["pending_question_act"] == (
            "fill_requested_slot"
        )
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == (
            "generic_info_interrupt"
        )

    def test_policy_core_allows_promotions_service_grounding_fact_interrupt_to_preserve_booking_goal(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "promotions",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["promotions"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "reason": "user_asked_promotions_for_grounded_service_promotions_fact_and_continue_booking_from_carried_exact_datetime_to_name",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "subject_kind": "service",
            "capability": "promotions",
            "temporal_scope": "specific_time",
            "alternate_datetime": "пятницу в 15:30",
            "resolution_mode": "policy_fact",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Есть ли акции на маникюр?",
                current_goal="booking",
                slot_state={},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"datetime": "пятницу в 15:30"},
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "reason": "collect:service",
                    },
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "capability": "bookability",
                        "subject_kind": "general",
                        "resolution_mode": "clarify_missing_subject",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "пятницу в 15:30",
                    },
                },
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["goal"] == "booking"
        assert (
            result["payload"]["grounding_requirements"]["resolution_mode"]
            == "policy_fact"
        )
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == (
            "пятницу в 15:30"
        )
        assert result["payload"]["missing_information"]["expected_reply_type"] == "name"
        assert result["payload"]["missing_information"]["pending_question_act"] == (
            "fill_requested_slot"
        )
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == (
            "generic_info_interrupt"
        )

    @pytest.mark.parametrize(
        "variant",
        iter_policy_core_booking_info_interrupt_variants(
            family="service_grounding_progression"
        ),
        ids=lambda variant: variant.head_intent,
    )
    def test_policy_core_allows_booking_info_interrupt_registry_family_to_advance_missing_service_exact_datetime_progression(
        self,
        monkeypatch,
        variant,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        alternate_datetime = variant.example_alternate_datetime
        service_value = "Маникюр"
        payload = {
            "intent": variant.head_intent,
            "action": "fact",
            "tool_action_hint": variant.tool_action_hint,
            "pack_refs": list(variant.pack_refs),
            "slots": {"service": service_value, "datetime": alternate_datetime},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "reason": f"{variant.head_intent}_fact_interrupt_advances_missing_service_exact_datetime_progression",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": service_value,
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "subject_kind": "service",
            "capability": variant.capability,
            "temporal_scope": "specific_time",
            "alternate_datetime": alternate_datetime,
            "resolution_mode": "policy_fact",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                variant.example_message,
                current_goal="booking",
                slot_state={},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"datetime": alternate_datetime},
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "reason": "collect:service",
                    },
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "capability": "bookability",
                        "subject_kind": "general",
                        "resolution_mode": "clarify_missing_subject",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": alternate_datetime,
                    },
                },
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["binding"]["tool_action"] == variant.tool_action_hint
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["goal"] == "booking"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert (
            result["payload"]["grounding_requirements"]["resolution_mode"]
            == "policy_fact"
        )
        assert (
            result["payload"]["grounding_requirements"]["alternate_datetime"]
            == alternate_datetime
        )
        assert result["payload"]["missing_information"]["expected_reply_type"] == "name"
        assert result["payload"]["missing_information"]["next_question"] == "name"
        assert result["payload"]["missing_information"]["open_questions"] == ["name"]
        assert result["payload"]["missing_information"]["pending_question_act"] == (
            "fill_requested_slot"
        )
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == (
            "generic_info_interrupt"
        )

    def test_policy_core_rejects_service_grounding_fact_interrupt_that_keeps_service_choice_contract(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "promotions",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["promotions"],
            "slots": {"service": None},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "reason": "promotions_fact_with_active_booking_continuity_preserve_service_choice_contract",
            "goal": "booking",
            "referents": {},
            "subject_kind": "general",
            "capability": "promotions",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра в 18:00",
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Какие скидки на маникюр?",
                current_goal="booking",
                slot_state={},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"datetime": "завтра в 18:00"},
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "reason": "booking_availability_with_exact_datetime_but_service_missing",
                    },
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "capability": "bookability",
                        "subject_kind": "general",
                        "resolution_mode": "clarify_missing_subject",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "завтра в 18:00",
                    },
                },
                client_slug="demo_salon",
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert result["schema_error"] == (
            "llm_policy_core_error:"
            "missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False

    def test_policy_core_rejects_service_grounding_fact_interrupt_missing_pending_axes(
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
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "reason": "user asks who does manicure; service is grounded and booking continuation advances to customer name",
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
            "capability": "master",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра в 18:00",
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": "generic_info_interrupt",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps(invalid_payload)
            )
            result = route_llm_policy_core(
                "Кто делает маникюр?",
                current_goal="booking",
                slot_state={},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"datetime": "на завтра в 18:00"},
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "reason": "collect:service",
                    },
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "capability": "bookability",
                        "subject_kind": "general",
                        "resolution_mode": "clarify_missing_subject",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "на завтра в 18:00",
                    },
                },
                client_slug="demo_salon",
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert result["schema_error"] == (
            "llm_policy_core_error:"
            "missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False

    def test_policy_core_rejects_service_grounding_fact_interrupt_with_direct_resolution_mode(
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
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "reason": "user_asks_master_on_grounded_service_during_missing-service exact-datetime booking continuity",
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
            "capability": "master",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра в 18:00",
            "resolution_mode": "direct",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps(invalid_payload)
            )
            result = route_llm_policy_core(
                "Кто делает маникюр?",
                current_goal="booking",
                slot_state={},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"datetime": "на завтра в 18:00"},
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "reason": "collect:service",
                    },
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "capability": "bookability",
                        "subject_kind": "general",
                        "resolution_mode": "clarify_missing_subject",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "на завтра в 18:00",
                    },
                },
                client_slug="demo_salon",
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert result["schema_error"] == (
            "llm_policy_core_error:"
            "missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False

    def test_policy_core_accepts_duration_grounding_interrupt_progression_to_name_collect(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "duration",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["duration"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "reason": (
                "Пользователь спрашивает длительность маникюра; услуга заземлена, "
                "при активном ожидании сервиса и точном времени продвигаем к сбору имени."
            ),
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
            "capability": "promotions",
            "temporal_scope": "specific_time",
            "alternate_datetime": "на завтра в 18:00",
            "resolution_mode": "policy_fact",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps(owner_payload)
            )
            result = route_llm_policy_core(
                "Сколько длится маникюр?",
                current_goal="booking",
                slot_state={},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"datetime": "на завтра в 18:00"},
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "reason": "collect:service",
                    },
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "capability": "bookability",
                        "subject_kind": "general",
                        "resolution_mode": "clarify_missing_subject",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "на завтра в 18:00",
                    },
                },
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["goal"] == "booking"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["duration"]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert (
            result["payload"]["grounding_requirements"]["alternate_datetime"]
            == "на завтра в 18:00"
        )
        assert result["payload"]["missing_information"]["expected_reply_type"] == "name"
        assert result["payload"]["missing_information"]["next_question"] == "name"
        assert result["payload"]["missing_information"]["pending_question_act"] == "fill_requested_slot"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert (
            result["payload"]["missing_information"]["active_question_relation"]
            == "generic_info_interrupt"
        )

    def test_policy_core_rejects_promotions_grounded_fact_interrupt_that_drops_booking_goal_and_followup(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "promotions",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["promotions"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "reason": "user_asks_promotions_for_grounded_service_manicure",
            "goal": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_message",
                }
            },
            "subject_kind": "service",
            "capability": "promotions",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps(invalid_payload)
            )
            result = route_llm_policy_core(
                "Есть ли акции на маникюр?",
                current_goal="booking",
                slot_state={},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"datetime": "пятницу в 15:30"},
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "reason": "collect:service",
                    },
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "capability": "bookability",
                        "subject_kind": "general",
                        "resolution_mode": "clarify_missing_subject",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "пятницу в 15:30",
                    },
                },
                client_slug="demo_salon",
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert result["schema_error"] == (
            "llm_policy_core_error:"
            "missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False

    def test_policy_core_contract_grounded_service_ignores_bare_internal_entity_id_without_value(
        self,
    ):
        contract, error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action_hint": "collect",
                "pack_refs": [],
                "slots": {},
                "expected_reply_type": "service_choice",
                "next_question": "service",
                "open_questions": ["service"],
                "needs_manager": False,
                "reason": "booking_availability_exact_datetime_missing_service",
                "goal": "booking",
                "referents": {
                    "service": {
                        "value": None,
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                },
                "subject_kind": "general",
                "capability": "bookability",
                "temporal_scope": "specific_time",
                "alternate_datetime": "завтра в 18:00",
                "resolution_mode": "clarify_missing_subject",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
            }
        )

        assert error is None
        assert _policy_core_contract_grounded_service(contract) is None

    def test_policy_core_owner_input_marks_current_message_service_grounding_hint(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "promotions",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["promotions"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "reason": "promotions_fact_for_grounded_service_advances_missing_service_continuity",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "subject_kind": "service",
            "capability": "promotions",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра в 18:00",
            "resolution_mode": "policy_fact",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Какие скидки на маникюр?",
                current_goal="booking",
                slot_state={},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"datetime": "завтра в 18:00"},
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "reason": "booking_availability_with_exact_datetime_but_service_missing",
                    },
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "capability": "bookability",
                        "subject_kind": "general",
                        "resolution_mode": "clarify_missing_subject",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "завтра в 18:00",
                    },
                },
                client_slug="demo_salon",
            )

        policy_input = json.loads(
            mock_llm.return_value.generate.call_args.kwargs["messages"][1]["content"]
        )
        assert result["ok"] is True
        assert policy_input["context"]["message_grounding_hints"]["service"] == "маникюр"

    def test_policy_core_allows_customer_name_fill_to_commit_booking_after_service_grounding_interrupt(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "fact",
            "tool_action_hint": "calendar.book_slot",
            "pack_refs": [],
            "slots": {
                "service": "маникюр",
                "datetime": "завтра в 18:00",
                "name": "Амина",
            },
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "reason": "user_provided_customer_name_and_carried_datetime_service_are_ready_for_booking_commit",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "customer": {
                    "value": "Амина",
                    "entity_id": None,
                    "entity_type": "customer",
                    "source_ref": "user_message",
                },
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра в 18:00",
            "resolution_mode": "live_calendar",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Меня зовут Амина.",
                current_goal="booking",
                slot_state={},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {
                        "service": "маникюр",
                        "datetime": "завтра в 18:00",
                    },
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                        "pending_question_act": "fill_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "generic_info_interrupt",
                        "reason": "service_grounded_fact_interrupt_waiting_customer_name",
                    },
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "capability": "bookability",
                        "subject_kind": "service",
                        "resolution_mode": "policy_fact",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "завтра в 18:00",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "memory_carried",
                            }
                        },
                    },
                },
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["binding"]["tool_action"] == "calendar.book_slot"
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "booking"
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "завтра в 18:00"
        assert "expected_reply_type" not in result["payload"]["missing_information"]
        response_format = mock_llm.return_value.generate.call_args.kwargs["response_format"]
        slots_schema = response_format["json_schema"]["schema"]["properties"]["slots"]
        assert slots_schema["required"] == ["service", "datetime", "name"]
        assert slots_schema["properties"]["service"]["enum"] == ["маникюр"]
        assert slots_schema["properties"]["datetime"]["enum"] == ["завтра в 18:00"]
        assert slots_schema["properties"]["name"]["type"] == "string"
        assert slots_schema["properties"]["name"]["minLength"] == 1

    def test_policy_core_compact_input_keeps_service_cards_and_message_grounding_hints(self):
        snapshot = build_policy_core_context_snapshot(
            client_slug="demo_salon",
            info_refs=None,
            consult_refs=None,
        )
        compact_input = _build_policy_core_compact_input(
            {
                "task": "llm_policy_core",
                "message": "Какие скидки на маникюр?",
                "allowed": snapshot.as_allowed_payload(),
                "context": {
                    **(snapshot.as_context_payload() or {}),
                    "message_grounding_hints": {"service": "маникюр"},
                },
                "memory": {
                    "profile": {
                        "active_goal": "booking",
                        "pending_question_contract": {
                            "expected_reply_type": "service_choice",
                            "next_question": "service",
                            "open_questions": ["service"],
                            "reason": "collect:service",
                        }
                    }
                },
            }
        )

        compact_context = compact_input["context"]
        assert compact_context["service_cards"]
        assert compact_context["message_grounding_hints"]["service"] == "маникюр"

    def test_policy_core_prompt_booking_availability_without_service_day_clue(self):
        prompt = _load_policy_core_prompt()

        assert '"На завтра есть время?"' in prompt
        assert '`expected_reply_type="service_choice"`' in prompt
        assert "не придумывай `slots.service` / `referents.service`" in prompt
        assert "должны остаться пустыми" in prompt
        assert '`temporal_scope="day"`' in prompt
        assert "а не `date_range`" in prompt
        assert '`resolution_mode="clarify_missing_subject"`' in prompt

    def test_policy_core_compact_prompt_booking_availability_without_service_day_clue(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert '"На завтра есть время?"' in prompt
        assert "expected_reply_type=service_choice, next_question=service, open_questions=[service]" in prompt
        assert "do NOT invent slots.service or referents.service" in prompt
        assert "must stay empty" in prompt
        assert 'Do NOT widen a single day/daypart clue like "завтра" to date_range' in prompt
        assert "resolution_mode=clarify_missing_subject" in prompt

    def test_policy_core_repairs_mixed_first_turn_hours_and_pricing_collect_to_fact(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "hours",
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
            "confidence": 0.74,
            "reason": "user asks working hours and price for a service, but service is not grounded in memory",
            "goal": "info",
            "entity_refs": [],
            "referents": {},
            "subject_kind": "general",
            "capability": "bookability",
            "temporal_scope": "none",
            "alternate_datetime": None,
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
            "tool_action_hint": "info",
            "pack_refs": ["hours", "pricing"],
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "reason": "user asks working hours and pricing for grounded pedicure service",
            "goal": "info",
            "referents": {
                "service": {
                    "value": "педикюр",
                    "entity_id": "svc:pedicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "subject_kind": "service",
            "capability": "hours",
            "resolution_mode": "policy_fact",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Здравствуйте! Вы сегодня работаете? Сколько стоит педикюр?",
                current_goal="info",
                slot_state={},
                memory_profile=None,
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:mixed_first_turn_hours_service_fact_reclassification_required"
        )
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["tool_action_hint"] == "info"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["grounding_requirements"]["referents"]["service"]["value"] == "педикюр"

    def test_policy_core_repairs_hours_pricing_service_presence_noun_head_to_full_scope(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "hours",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["hours", "pricing"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.81,
            "reason": "user asks hours plus what services are available and manicure pricing",
            "goal": None,
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
            "capability": "hours",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        repaired_payload = {
            **invalid_payload,
            "pack_refs": ["hours", "pricing", "services_overview"],
            "reason": "user asks working hours plus service list and manicure pricing",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Вы сегодня работаете, какие услуги есть и сколько стоит маникюр?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:mixed_first_turn_hours_service_fact_reclassification_required"
        )
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "hours",
            "pricing",
            "services_overview",
        ]

    def test_validate_policy_core_runtime_contract_flags_partial_date_already_in_slots_datetime(
        self,
    ):
        invalid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр", "datetime": "завтра"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "user_returns_to_booking_after_duration_interrupt_with_partial_date",
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
            "capability": "bookability",
            "temporal_scope": "day",
            "resolution_mode": "ask_about_requested_slot",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }
        contract, schema_error = validate_llm_policy_core_output(invalid_payload)

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр"},
                    "pending_question_contract": {
                        "reason": "duration_info_interrupt_during_booking_continuity",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "expected_reply_type": "time",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "generic_info_interrupt",
                    },
                    "semantic_contract": {
                        "capability": "duration",
                        "subject_kind": "service",
                        "temporal_scope": "none",
                        "resolution_mode": "ask_about_requested_slot",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "generic_info_interrupt",
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
                current_message="Мне нужно перенести запись на завтра.",
            )
            == "llm_policy_core_error:active_booking_temporal_clue_followup_reclassification_required"
        )

    def test_policy_core_repairs_reschedule_temporal_clue_when_partial_date_is_already_in_slots_datetime(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр", "datetime": "завтра"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "user_returns_to_booking_after_duration_interrupt_with_partial_date",
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
            "capability": "bookability",
            "temporal_scope": "day",
            "resolution_mode": "ask_about_requested_slot",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }
        repaired_payload = {
            **invalid_payload,
            "pending_question_act": "slot_constraint",
            "active_question_relation": "slot_constraint",
            "alternate_datetime": "завтра",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Мне нужно перенести запись на завтра.",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр"},
                    "pending_question_contract": {
                        "reason": "duration_info_interrupt_during_booking_continuity",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "expected_reply_type": "time",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "generic_info_interrupt",
                    },
                    "semantic_contract": {
                        "capability": "duration",
                        "subject_kind": "service",
                        "temporal_scope": "none",
                        "resolution_mode": "ask_about_requested_slot",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "generic_info_interrupt",
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
        assert result["payload"]["grounding_requirements"]["temporal_scope"] == "day"
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "завтра"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert result["payload"]["missing_information"]["pending_question_act"] == "slot_constraint"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "slot_constraint"

    def test_validate_policy_core_runtime_contract_prefers_temporal_clue_over_carried_specialist(
        self,
    ):
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
            "reason": "active_booking_temporal_clue_after_grounded_specialist",
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
                    "source_ref": "carryover",
                },
            },
            "subject_kind": "specialist",
            "capability": "bookability",
            "temporal_scope": "none",
            "resolution_mode": "referent_followup",
            "pending_question_act": None,
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
        }
        contract, schema_error = validate_llm_policy_core_output(invalid_payload)

        assert schema_error is None
        assert contract is not None
        normalized_memory_profile = {
            "active_goal": "booking",
            "slot_state": {"service": "маникюр"},
            "pending_question_contract": {
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
            },
            "semantic_contract": {
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "specific_time",
                "alternate_datetime": "11:30",
                "resolution_mode": "ask_about_requested_slot",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
                "referents": invalid_payload["referents"],
            },
        }

        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile=normalized_memory_profile,
                current_message="Давайте на завтра вечером.",
            )
            == "llm_policy_core_error:active_booking_temporal_clue_followup_reclassification_required"
        )
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:active_booking_temporal_clue_followup_reclassification_required",
            normalized_memory_profile=normalized_memory_profile,
            contract=contract,
            current_message="Давайте на завтра вечером.",
        )
        assert repair is not None
        assert '`referents.specialist.value="Айгерим"`' in repair
        assert "do NOT switch `subject_kind`, `active_question_relation`, or `resolution_mode` back" in repair

    def test_policy_core_repairs_carried_specialist_temporal_clue_into_booking_slot_constraint(
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
            "reason": "active_booking_temporal_clue_after_grounded_specialist",
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
                    "source_ref": "carryover",
                },
            },
            "subject_kind": "specialist",
            "capability": "bookability",
            "temporal_scope": "none",
            "resolution_mode": "referent_followup",
            "pending_question_act": None,
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
        }
        repaired_payload = {
            **invalid_payload,
            "subject_kind": "booking",
            "temporal_scope": "day",
            "alternate_datetime": "завтра вечером",
            "resolution_mode": "ask_about_requested_slot",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Давайте на завтра вечером.",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "booking",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "11:30",
                        "resolution_mode": "ask_about_requested_slot",
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                        "referents": invalid_payload["referents"],
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
        assert result["payload"]["grounding_requirements"]["temporal_scope"] == "day"
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "завтра вечером"
        assert (
            result["payload"]["grounding_requirements"]["resolution_mode"]
            == "ask_about_requested_slot"
        )
        assert (
            result["payload"]["grounding_requirements"]["referents"]["specialist"]["value"]
            == "Айгерим"
        )
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert result["payload"]["missing_information"]["pending_question_act"] == "slot_constraint"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "slot_constraint"

    def test_policy_core_repairs_active_media_time_interrupt_with_specialist_resume(
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
            "reason": "user_requests_availability_for_specific_time_after_active_media_followup",
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
                    "source_ref": "user_message",
                },
            },
            "subject_kind": "specialist",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "resolution_mode": "ask_about_requested_slot",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
        }
        repaired_payload = {
            **invalid_payload,
            "subject_kind": "booking",
            "alternate_datetime": "11:30",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Есть свободные слоты на 11:30?",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр"},
                    "pending_question_contract": {
                        "expected_reply_type": "media",
                        "next_question": "media",
                        "open_questions": ["media"],
                        "pending_question_target": "specialist",
                        "active_question_relation": "referent_followup",
                    },
                    "resume_pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                    },
                    "semantic_contract": {
                        "capability": "consultation",
                        "subject_kind": "booking",
                        "temporal_scope": "none",
                        "resolution_mode": "referent_followup",
                        "pending_question_target": "specialist",
                        "active_question_relation": "referent_followup",
                        "referents": invalid_payload["referents"],
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
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "11:30"
        assert result["payload"]["grounding_requirements"]["temporal_scope"] == "specific_time"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert result["payload"]["missing_information"]["pending_question_act"] == "slot_constraint"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "slot_constraint"

    def test_policy_core_temporal_clue_requires_message_grounded_alternate_datetime_for_russian_message(self):
        assert (
            _policy_core_temporal_clue_requires_message_grounded_alternate_datetime(
                "tomorrow evening",
                "Давайте на завтра вечером.",
            )
            is True
        )
        assert (
            _policy_core_temporal_clue_requires_message_grounded_alternate_datetime(
                "завтра вечером",
                "Давайте на завтра вечером.",
            )
            is False
        )

    def test_policy_core_repairs_translated_alternate_datetime_back_to_user_language(
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
            "reason": "user_time_clue_tomorrow_evening_for_requested_slot",
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
                    "entity_type": "specialist",
                    "source_ref": "user_message",
                },
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "tomorrow evening",
            "resolution_mode": "ask_about_requested_slot",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
        }
        repaired_payload = {
            **invalid_payload,
            "alternate_datetime": "завтра вечером",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Давайте на завтра вечером.",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "booking",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "11:30",
                        "resolution_mode": "ask_about_requested_slot",
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                        "referents": invalid_payload["referents"],
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
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "завтра вечером"
        assert result["payload"]["grounding_requirements"]["temporal_scope"] == "specific_time"
        assert result["payload"]["missing_information"]["pending_question_act"] == "slot_constraint"
        assert result["payload"]["missing_information"]["active_question_relation"] == "slot_constraint"

    def test_policy_core_rejects_invalid_active_booking_specialist_preference_into_referent_followup(
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

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:active_booking_specialist_followup_reclassification_required"
        )
        assert result["compact_input_used"] is False
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

    def test_policy_core_allows_canonical_active_booking_specialist_preference_into_referent_followup(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
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
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Хочу к Айгерим.",
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
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
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

    def test_policy_core_rejects_invalid_specialist_preference_during_active_booking_temporal_clue(
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

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:active_booking_specialist_followup_reclassification_required"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

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
            "slots": {"service": "маникюр"},
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
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "alternate_datetime": "11:30",
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
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "11:30"
        assert result["payload"]["missing_information"]["pending_question_act"] == "slot_constraint"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "slot_constraint"

    def test_policy_core_repairs_active_booking_generic_availability_hours_misroute(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "hours",
            "action": "fact",
            "tool_action_hint": "catalog.location",
            "pack_refs": ["hours"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "user_asks_when_can_book",
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
            "capability": "hours",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
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
            "reason": "active_booking_requested_slot_availability_followup",
            "goal": "booking",
            "referents": invalid_payload["referents"],
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "none",
            "resolution_mode": "ask_about_requested_slot",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Когда можно записаться?",
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
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:active_booking_requested_slot_availability_resolution_required"
        )
        assert result["binding"]["tool_action"] == "collect"
        assert result["payload"]["requested_outcome"] == "collect"
        assert result["payload"]["missing_information"]["pending_question_act"] == "ask_about_requested_slot"
        assert result["payload"]["missing_information"]["active_question_relation"] == "ask_about_requested_slot"

    def test_policy_core_repairs_active_booking_generic_availability_slot_constraint_overclaim(
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
            "reason": "generic_availability_with_carried_weekday",
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
            "capability": "bookability",
            "temporal_scope": "weekday",
            "alternate_datetime": "в понедельник",
            "resolution_mode": "ask_about_requested_slot",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
        }
        repaired_payload = {
            **invalid_payload,
            "temporal_scope": "weekday",
            "alternate_datetime": None,
            "pending_question_act": "ask_about_requested_slot",
            "active_question_relation": "ask_about_requested_slot",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Какое время доступно?",
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
                        "subject_kind": "booking",
                        "temporal_scope": "weekday",
                        "resolution_mode": "ask_about_requested_slot",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                        "referents": invalid_payload["referents"],
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:active_booking_requested_slot_availability_resolution_required"
        )
        assert result["binding"]["tool_action"] == "collect"
        assert result["payload"]["missing_information"]["pending_question_act"] == "ask_about_requested_slot"
        assert result["payload"]["missing_information"]["active_question_relation"] == "ask_about_requested_slot"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"

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

    def test_policy_core_repairs_active_booking_promotions_interrupt_contract(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "promotions",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["promotions"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "user_asked_promotions_and_service_is_grounded_from_carryover;keep_booking_requested_datetime_contract",
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
            "capability": "promotions",
            "temporal_scope": "day",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
        }
        repaired_payload = {
            **invalid_payload,
            "alternate_datetime": "завтра вечером",
            "active_question_relation": "generic_info_interrupt",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "Есть ли акции?",
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
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "temporal_scope": "day",
                        "alternate_datetime": "завтра вечером",
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
            == "llm_policy_core_error:active_booking_info_interrupt_contract_invalid"
        )
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["promotions"]
        assert result["payload"]["grounding_requirements"]["temporal_scope"] == "day"
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "завтра вечером"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
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

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:generic_info_interrupt_expected_reply_invalid"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["tool_args_sanitized"] is True
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

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
        assert result["tool_args_sanitized"] is True
        assert result["compact_input_used"] is True
        assert result["compact_retry_used"] is False
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        policy_input = json.loads(kwargs["messages"][1]["content"])
        assert kwargs["max_tokens"] == 320
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
        assert result["compact_retry_used"] is True
        assert mock_llm.return_value.generate.call_args_list[0].kwargs["max_tokens"] == 560
        assert mock_llm.return_value.generate.call_args_list[1].kwargs["max_tokens"] == 320

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

    def test_active_bookability_pending_followup_uses_full_prompt_first_attempt(
        self, monkeypatch
    ):
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
        assert result["compact_input_used"] is False
        assert result["compact_retry_used"] is False
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        policy_input = json.loads(kwargs["messages"][1]["content"])
        assert "LLM Policy Core Focused Contract" in kwargs["messages"][0]["content"]
        assert result["focused_owner_contract_used"] is True
        assert policy_input["memory"]["profile"]["semantic_contract"]["capability"] == "bookability"

    def test_grounded_start_booking_temporal_request_uses_full_prompt_first_attempt(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            "app.services.intent_service._policy_core_resolve_current_message_service_hint",
            lambda **_kwargs: "маникюр",
        )

        payload = self._policy_payload()
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Хочу записаться на маникюр завтра вечером.",
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["compact_input_used"] is False
        assert result["compact_retry_used"] is False
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        assert "LLM Policy Core Prompt" in kwargs["messages"][0]["content"]
        assert "LLM Policy Core Compact Prompt" not in kwargs["messages"][0]["content"]

    def test_first_turn_temporal_booking_side_ask_uses_focused_owner_contract(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        payload = self._policy_payload()
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "На завтра в 18:00 есть время?",
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["compact_input_used"] is False
        assert result["compact_retry_used"] is False
        assert result["focused_owner_contract_used"] is True
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        assert "LLM Policy Core Focused Contract" in kwargs["messages"][0]["content"]

    def test_first_turn_temporal_booking_side_ask_timeout_retry_stays_on_full_prompt(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        valid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {
                "service": None,
                "datetime": "на завтра в 18:00",
                "name": None,
                "phone": None,
            },
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.78,
            "reason": "booking_availability_exact_time_missing_service",
            "goal": "booking",
            "entity_refs": None,
            "referents": None,
            "subject_kind": "general",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "на завтра в 18:00",
            "resolution_mode": "clarify_missing_subject",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                httpx.TimeoutException("timed out"),
                DummyResponse(json.dumps(valid_payload)),
            ]
            result = route_llm_policy_core(
                "На завтра в 18:00 есть время?",
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["attempt_count"] == 2
        assert result["compact_input_used"] is False
        assert result["compact_retry_used"] is False
        first_kwargs = mock_llm.return_value.generate.call_args_list[0].kwargs
        second_kwargs = mock_llm.return_value.generate.call_args_list[1].kwargs
        assert "LLM Policy Core Focused Contract" in first_kwargs["messages"][0]["content"]
        assert "LLM Policy Core Focused Contract" in second_kwargs["messages"][0]["content"]
        assert second_kwargs["timeout_seconds"] == intent_service_module.POLICY_CORE_TIMEOUT_SECONDS

    def test_focused_start_booking_generic_provider_error_retries_once(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            "app.services.intent_service._policy_core_resolve_current_message_service_hint",
            lambda **_kwargs: "Маникюр",
        )

        valid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "Маникюр", "datetime": "20 июня в 10:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "message_grounding",
                }
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "20 июня в 10:00",
            "resolution_mode": "direct",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "fill_requested_slot",
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                RuntimeError("upstream closed connection"),
                DummyResponse(json.dumps(valid_payload)),
            ]
            result = route_llm_policy_core(
                "Хочу записаться на маникюр 20 июня в 10:00",
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["focused_owner_contract_used"] is True
        assert result["attempt_count"] == 2
        first_kwargs = mock_llm.return_value.generate.call_args_list[0].kwargs
        second_kwargs = mock_llm.return_value.generate.call_args_list[1].kwargs
        assert "LLM Policy Core Focused Contract" in first_kwargs["messages"][0]["content"]
        assert "LLM Policy Core Focused Contract" in second_kwargs["messages"][0]["content"]

    def test_compact_gpt5_path_uses_tuned_hot_path_floor(self):
        assert _resolve_policy_core_max_tokens_with_cap(
            15.0,
            None,
            "gpt-5.4-nano-2026-03-17",
            compact_mode=True,
        ) == 320

    def test_full_gpt5_path_clamps_to_safe_cap_even_when_floor_env_drift_is_higher(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_GPT5_MIN_MAX_TOKENS",
            800,
        )
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_GPT5_SAFE_MAX_TOKENS",
            480,
        )

        assert _resolve_policy_core_max_tokens_with_cap(
            15.0,
            None,
            "gpt-5.4-nano-2026-03-17",
            compact_mode=False,
        ) == 480

    def test_policy_core_respects_explicit_max_tokens_override_for_gpt5(self, monkeypatch):
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
        assert kwargs["max_tokens"] == 120

    def test_booking_manage_name_fill_uses_booking_manage_safe_cap(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        valid_payload = {
            "intent": "check_booking",
            "action": "fact",
            "tool_action_hint": "calendar.get_booking",
            "pack_refs": [],
            "slots": {"name": "Амина", "service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": (
                "Пользователь сообщил имя для проверки существующей записи; "
                "booking_ref еще не найден, поэтому продолжаем поиск через "
                "calendar.get_booking и просим дату/время записи."
            ),
            "subject_kind": "booking",
            "capability": "booking_manage",
            "temporal_scope": "none",
            "resolution_mode": "direct",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "referents": {
                "customer": {
                    "value": "Амина",
                    "entity_type": "customer",
                    "source_ref": "user_text",
                },
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
            },
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
            result = route_llm_policy_core(
                "Меня зовут Амина.",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                        "reason": "user_requests_check_existing_booking_without_booking_ref",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "booking_manage",
                        "resolution_mode": "direct",
                        "temporal_scope": "none",
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
        assert result["compact_input_used"] is False
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        assert kwargs["max_tokens"] == 560

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

    def test_policy_core_context_snapshot_reads_service_taxonomy_from_nested_client_pack_domain_pack(
        self,
    ):
        runtime_truth = RuntimeTruth(
            truth={
                "client_pack": {
                    "domain_pack": {
                        "service_taxonomy": {
                            "categories": [
                                {
                                    "id": "nails",
                                    "label_ru": "Ногтевой сервис",
                                    "includes_ru": ["маникюр", "педикюр"],
                                    "synonyms_ru": ["ногти"],
                                }
                            ]
                        }
                    }
                }
            },
            client_slug="demo_salon",
            branch_id=uuid4(),
            source="test_intent",
            allow_fallback=False,
        )

        with use_runtime_truth_override(runtime_truth):
            snapshot = build_policy_core_context_snapshot(
                client_slug="demo_salon",
                info_refs=None,
                consult_refs=[],
            )

        context_payload = snapshot.as_context_payload() or {}
        assert any(
            card.get("id") == "nails"
            and "маникюр" in list(card.get("includes") or [])
            for card in context_payload.get("service_cards") or []
        )

    def test_policy_core_context_snapshot_keeps_catalog_aliases_with_domain_taxonomy(
        self,
    ):
        runtime_truth = RuntimeTruth(
            truth={
                "client_pack": {
                    "domain_pack": {
                        "service_taxonomy": {
                            "categories": [
                                {
                                    "id": "nails",
                                    "label_ru": "Ногтевой сервис",
                                    "includes_ru": ["маникюр", "педикюр"],
                                }
                            ]
                        }
                    }
                },
                "services_catalog": {
                    "services": [
                        {
                            "name": "Маникюр",
                            "aliases": ["маник", "маникюр"],
                            "quick_price_key": "manicure",
                        }
                    ]
                },
            },
            client_slug="demo_salon",
            branch_id=uuid4(),
            source="test_intent",
            allow_fallback=False,
        )

        with use_runtime_truth_override(runtime_truth):
            snapshot = build_policy_core_context_snapshot(
                client_slug="demo_salon",
                info_refs=None,
                consult_refs=[],
            )

        context_payload = snapshot.as_context_payload() or {}
        service_cards = context_payload.get("service_cards") or []
        assert any(card.get("id") == "nails" for card in service_cards)
        assert any(
            card.get("id") == "manicure"
            and "маник" in list(card.get("includes") or [])
            for card in service_cards
        )
        assert (
            _policy_core_resolve_current_message_service_hint(
                current_message="Сколько стоит маник?",
                context_payload=context_payload,
                client_slug="demo_salon",
            )
            == "Маникюр"
        )

    def test_policy_core_context_snapshot_falls_back_to_services_catalog_when_runtime_truth_has_no_taxonomy(
        self,
    ):
        runtime_truth = RuntimeTruth(
            truth={
                "services_catalog": {
                    "services": [
                        {
                            "name": "Маникюр",
                            "aliases": [
                                "маникюр",
                                "аппаратный маникюр",
                            ],
                            "price_items": ["Маникюр с покрытием"],
                            "quick_price_key": "manicure",
                        }
                    ]
                }
            },
            client_slug="clinic_pack",
            branch_id=uuid4(),
            source="test_intent",
            allow_fallback=False,
        )

        with use_runtime_truth_override(runtime_truth):
            snapshot = build_policy_core_context_snapshot(
                client_slug="clinic_pack",
                info_refs=None,
                consult_refs=[],
            )

        context_payload = snapshot.as_context_payload() or {}
        assert any(
            card.get("id") == "manicure"
            and any(item.casefold() == "маникюр" for item in list(card.get("includes") or []))
            for card in context_payload.get("service_cards") or []
        )

    def test_policy_core_context_snapshot_preserves_static_domain_taxonomy_for_runtime_truth_without_domain_pack(
        self,
    ):
        runtime_truth = RuntimeTruth(
            truth={
                "services_catalog": {
                    "services": [
                        {
                            "name": "Маникюр",
                            "aliases": ["маникюр"],
                            "quick_price_key": "manicure",
                        }
                    ]
                }
            },
            client_slug="demo_salon",
            branch_id=uuid4(),
            source="test_intent",
            allow_fallback=False,
        )

        with use_runtime_truth_override(runtime_truth):
            snapshot = build_policy_core_context_snapshot(
                client_slug="demo_salon",
                info_refs=None,
                consult_refs=[],
            )

        context_payload = snapshot.as_context_payload() or {}
        service_cards = context_payload.get("service_cards") or []
        assert any(
            card.get("id") == "hair"
            and "стрижка" in list(card.get("includes") or [])
            for card in service_cards
        )

    def test_policy_core_start_booking_exact_datetime_uses_domain_taxonomy_when_runtime_truth_lacks_domain_pack(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        runtime_truth = RuntimeTruth(
            truth={
                "services_catalog": {
                    "services": [
                        {
                            "name": "Маникюр",
                            "aliases": ["маникюр"],
                            "quick_price_key": "manicure",
                        }
                    ]
                }
            },
            client_slug="demo_salon",
            branch_id=uuid4(),
            source="test_intent",
            allow_fallback=False,
        )

        with use_runtime_truth_override(runtime_truth), patch(
            "app.services.intent_service.get_llm_provider"
        ) as mock_llm:
            mock_llm.return_value.generate.side_effect = lambda *_, **kwargs: DummyResponse(
                json.dumps(json.loads(kwargs["messages"][1]["content"])["focus_contract"]["forced_fields"])
            )
            result = route_llm_policy_core(
                "Можно на стрижку к Айгерим 19 августа в 13:00?",
                client_slug="demo_salon",
            )

        policy_input = json.loads(mock_llm.return_value.generate.call_args.kwargs["messages"][1]["content"])
        forced_fields = policy_input["focus_contract"]["forced_fields"]
        assert forced_fields["expected_reply_type"] == "name"
        assert forced_fields["slots"]["service"] == "Стрижка"
        assert forced_fields["slots"]["datetime"] == "19 августа в 13:00"
        assert result["ok"] is True

    def test_policy_core_rejects_promotions_followup_when_nested_runtime_truth_exposes_service_taxonomy(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        runtime_truth = RuntimeTruth(
            truth={
                "client_pack": {
                    "domain_pack": {
                        "service_taxonomy": {
                            "categories": [
                                {
                                    "id": "nails",
                                    "label_ru": "Ногтевой сервис",
                                    "includes_ru": ["маникюр", "педикюр"],
                                }
                            ]
                        }
                    }
                }
            },
            client_slug="demo_salon",
            branch_id=uuid4(),
            source="test_intent",
            allow_fallback=False,
        )
        payload = {
            "intent": "promotions",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["promotions"],
            "slots": {"service": None, "datetime": None, "name": None, "phone": None},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "risk_signals": None,
            "language": None,
            "confidence": None,
            "reason": "active booking continuity expects missing service; user asked for promotions on маникюр while time is already set",
            "goal": "booking",
            "entity_refs": None,
            "referents": {"service": {"value": None, "entity_id": None, "entity_type": "service", "source_ref": None}},
            "subject_kind": "general",
            "capability": "promotions",
            "temporal_scope": "specific_time",
            "alternate_datetime": "пятница в 15:30",
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }

        with use_runtime_truth_override(runtime_truth):
            with patch("app.services.intent_service.get_llm_provider") as mock_llm:
                mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
                result = route_llm_policy_core(
                    "Есть ли акции на маникюр?",
                    memory_summary=(
                        "user: На пятницу в 15:30 есть время? assistant: На какую услугу хотите записаться? "
                        "user: Есть ли акции на маникюр?"
                    ),
                    memory_profile={
                        "active_goal": "booking",
                        "pending_question_contract": {
                            "expected_reply_type": "service_choice",
                            "next_question": "service",
                            "open_questions": ["service"],
                            "reason": "collect:service",
                        },
                        "semantic_contract": {
                            "alternate_datetime": "пятница в 15:30",
                            "capability": "bookability",
                            "contract_version": "semantic_contract.v1",
                            "resolution_mode": "clarify_missing_subject",
                            "subject_kind": "general",
                            "temporal_scope": "specific_time",
                        },
                        "slot_state": {"datetime": "пятница в 15:30"},
                    },
                    client_slug="demo_salon",
                )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert result["schema_error"] in {
            "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required",
            "llm_policy_core_error:service_scoped_query_grounding_missing",
        }

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
        invalid_payload = self._policy_payload()
        invalid_payload.pop("expected_reply_type", None)
        invalid_payload.update(
            {
                "tool_action_hint": "collect",
                "slots": {"service": "маникюр", "datetime": "15:00", "name": ""},
                "next_question": "name",
                "open_questions": ["name"],
                "needs_manager": False,
                "risk_signals": [],
                "subject_kind": "booking",
                "capability": "live_availability",
                "temporal_scope": "specific_time",
                "resolution_mode": "direct",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
            }
        )
        repaired_payload = {
            **invalid_payload,
            "pending_question_act": "slot_constraint",
            "active_question_relation": "slot_constraint",
            "alternate_datetime": "15:00",
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(repaired_payload)),
            ]
            result = route_llm_policy_core(
                "А есть ли свободные слоты на 15:00?",
                expected_reply_type="name",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр"},
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "live_availability",
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
        assert result["contract_repair_retry_used"] is True
        assert (
            result["contract_repair_reason"]
            == "llm_policy_core_error:active_booking_temporal_clue_followup_reclassification_required"
        )
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "booking"
        assert result["payload"]["capability_id"] == "live_availability"
        assert result["payload"]["grounding_requirements"]["temporal_scope"] == "specific_time"
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "15:00"
        assert result["payload"]["missing_information"]["next_question"] == "name"
        assert result["payload"]["missing_information"]["open_questions"] == ["name"]
        assert result["payload"]["missing_information"]["pending_question_act"] == "slot_constraint"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "slot_constraint"

    def test_policy_core_prompt_free_slots_question_keeps_pending_time_contract(self):
        prompt = _load_policy_core_prompt()

        assert "Когда у вас есть свободные слоты?" in prompt
        assert "Какое время доступно?" in prompt
        assert "Не используй `calendar.list_slots` без `temporal_scope`" in prompt
        assert "не переводи ход в `hours/location` fact" in prompt
        assert '`pending_question_act="ask_about_requested_slot"`' in prompt
        assert '`pending_question_target="time"`' in prompt
        assert '`active_question_relation="ask_about_requested_slot"`' in prompt
        assert "не оставляй его `null`" in prompt
        assert '`alternate_datetime="завтра вечером"`' in prompt
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

    def test_policy_core_prompt_hybrid_availability_question_with_day_clue_uses_slot_constraint(self):
        prompt = _load_policy_core_prompt()

        assert '"У вас есть время на сегодня?"' in prompt
        assert "message-grounded clue (`сегодня`, `завтра`, weekday, time/daypart) делает ход `slot_constraint`" in prompt
        assert 'Forbidden: generic prompt `"На какую дату и время вам удобно?"`' in prompt
        assert '`pending_question_act="slot_constraint"`' in prompt
        assert '`temporal_scope="<grounded non-none scope>"`' in prompt

    def test_policy_core_prompt_first_turn_day_clue_uses_slot_constraint(self):
        prompt = _load_policy_core_prompt()

        assert '"Я хочу записаться на маникюр на понедельник."' in prompt
        assert '"Хочу записаться на маникюр завтра вечером."' in prompt
        assert "самый первый booking collect" in prompt
        assert '`subject_kind="booking"`' in prompt
        assert 'не возвращай generic prompt `"На какую дату и время вам удобно?"`' in prompt
        assert '`alternate_datetime="<grounded candidate slot>"`' in prompt
        assert '`resolution_mode="direct"`' in prompt
        assert '`alternate_datetime="завтра вечером"`' in prompt

    def test_policy_core_prompt_start_booking_exact_datetime_collects_name(self):
        prompt = _load_policy_core_prompt()

        assert '"Хочу записаться завтра в 18:00"' in prompt
        assert "полный слот день/дата + точное время" in prompt
        assert '`capability="bookability"`' in prompt
        assert '`resolution_mode="direct"`' in prompt
        assert '`expected_reply_type="name"`' in prompt
        assert '`slots.datetime="<grounded datetime surface>"`' in prompt
        assert '`alternate_datetime="<grounded datetime surface>"`' in prompt
        assert '`active_question_relation="fill_requested_slot"`' in prompt
        assert 'не используй `resolution_mode="live_calendar"`' in prompt
        assert 'не оставляй `alternate_datetime=null`' in prompt
        assert 'а НЕ `weekday`' in prompt
        assert '`subject_kind="service"`' in prompt
        assert 'Forbidden: generic prompt `"На какую дату и время вам удобно?"`' in prompt

    def test_policy_core_prompt_supports_thanks_smalltalk_intent(self):
        prompt = _load_policy_core_prompt()

        assert "|consult|greeting|thanks|out_of_domain|other" in prompt
        assert '"Спасибо"' in prompt
        assert '`intent="thanks"`' in prompt
        assert "Не своди благодарность к `greeting`" in prompt

    def test_policy_core_prompt_temporal_clue_preserves_specialist(self):
        prompt = _load_policy_core_prompt()

        assert "`referents.specialist` уже grounded из предыдущих ходов" in prompt
        assert "НЕ переключай `subject_kind` / `active_question_relation` / `resolution_mode` обратно" in prompt

    def test_policy_core_compact_prompt_keeps_booking_owner_for_candidate_time_availability(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "candidate time is available" in prompt
        assert "intent=booking, action=collect, tool_action_hint=collect" in prompt
        assert "Do NOT switch to intent=master_query" in prompt
        assert "calendar.list_slots while the requested booking slot is still incomplete" in prompt
        assert 'alternate_datetime="завтра вечером"' in prompt
        assert "temporal_scope=day" in prompt
        assert "instead of dropping alternate_datetime to null" in prompt

    def test_policy_core_compact_prompt_temporal_clue_followup_uses_slot_constraint(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "А как насчет пятницы на утро?" in prompt
        assert "У вас есть время на сегодня?" in prompt
        assert "resolution_mode=direct" in prompt
        assert "pending_question_act=slot_constraint" in prompt
        assert "active_question_relation=slot_constraint" in prompt
        assert "alternate_datetime=<grounded candidate slot>" in prompt
        assert "temporal_scope=<grounded non-none scope>" in prompt
        assert 'Do NOT fall back to the generic "На какую дату и время вам удобно?"' in prompt
        assert "previous JSON left temporal_scope as none" in prompt

    def test_policy_core_compact_prompt_first_turn_day_clue_uses_slot_constraint(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "Я хочу записаться на маникюр на понедельник." in prompt
        assert 'alternate_datetime="завтра вечером"' in prompt
        assert "first booking collect" in prompt
        assert "start directly on the slot-constraint path" in prompt
        assert "subject_kind=booking" in prompt
        assert "alternate_datetime=<grounded candidate slot>" in prompt

    def test_policy_core_compact_prompt_start_booking_exact_datetime_collects_name(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "Хочу записаться завтра в 18:00" in prompt
        assert "full day/date + exact clock time" in prompt
        assert "capability=bookability" in prompt
        assert "resolution_mode=direct" in prompt
        assert "expected_reply_type=name, next_question=name" in prompt
        assert "slots.datetime=<grounded datetime surface>" in prompt
        assert "alternate_datetime=<grounded datetime surface>" in prompt
        assert "active_question_relation=fill_requested_slot" in prompt
        assert "do NOT use resolution_mode=live_calendar" in prompt
        assert "do NOT leave alternate_datetime null" in prompt
        assert "subject_kind=service" in prompt
        assert "temporal_scope=specific_time instead of weekday" in prompt

    def test_policy_core_compact_prompt_supports_thanks_smalltalk_intent(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "Use intent=thanks for pure gratitude" in prompt
        assert '"Спасибо"' in prompt
        assert "Do NOT collapse gratitude into greeting." in prompt

    def test_policy_core_compact_prompt_temporal_clue_preserves_specialist(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "preserve referents.specialist" in prompt
        assert "do not revert resolution_mode to referent_followup" in prompt

    def test_policy_core_prompt_temporal_clue_preserves_user_language(self):
        prompt = _load_policy_core_prompt()

        assert "`alternate_datetime` должен оставаться в surface пользователя" in prompt
        assert "`tomorrow evening`" in prompt

    def test_policy_core_prompt_active_booking_name_fill_preserves_time_contract(self):
        prompt = _load_policy_core_prompt()
        compact_prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert '"Меня зовут Амина."' in prompt
        assert '"Аружан"' in prompt
        assert '"87015705555"' in prompt
        assert '"7015705555"' in prompt
        assert '`slots.phone="<phone>"`' in prompt
        assert '`goal="booking"`' in prompt
        assert '`slots.name="<customer name>"`' in prompt
        assert "не игнорируй customer identity" in prompt
        assert '`expected_reply_type="time"`' in prompt
        assert "сохрани carried `alternate_datetime` и `temporal_scope`" in prompt
        assert '`alternate_datetime="завтра вечером"`' in prompt
        assert "не переключай `subject_kind` / `pending_question_target` / `active_question_relation` / `resolution_mode` обратно в specialist follow-up" in prompt
        assert "Bare human-name/contact reply без явного specialist marker тоже остаётся customer/contact carryover" in prompt
        assert "Не переключай ход в `booking_manage`" in prompt
        assert "phone-only \"87015705555\"" in compact_prompt
        assert "slots.phone=<phone>" in compact_prompt
        assert "planner_degrade" in compact_prompt

    def test_policy_core_prompt_active_booking_time_completion_after_name_carryover(
        self,
    ):
        prompt = _load_policy_core_prompt()

        assert '"Давайте в 18:00."' in prompt
        assert '`tool_action_hint="calendar.book_slot"`' in prompt
        assert "`slots.datetime` объединяет новый точный time" in prompt
        assert '`slots.datetime="завтра 18:00"`' in prompt
        assert "Очисти stale collect axes" in prompt

    def test_policy_core_compact_prompt_temporal_clue_preserves_user_language(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "Keep alternate_datetime in the user's message surface" in prompt
        assert '"tomorrow evening"' in prompt

    def test_policy_core_compact_prompt_active_booking_name_fill_preserves_time_contract(
        self,
    ):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "Меня зовут Амина." in prompt
        assert "Аружан" in prompt
        assert "ground the customer canonically through slots.name=<customer name>" in prompt
        assert "expected_reply_type=time, next_question=datetime, open_questions=[datetime]" in prompt
        assert "keep the carried alternate_datetime/temporal_scope" in prompt
        assert 'alternate_datetime is already "завтра вечером"' in prompt
        assert "Do NOT revert this turn to specialist referent-followup" in prompt
        assert "Bare human-name replies without an explicit specialist marker" in prompt
        assert "Do NOT switch this turn to booking_manage" in prompt

    def test_policy_core_compact_prompt_active_booking_time_completion_after_name_carryover(
        self,
    ):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "Давайте в 18:00." in prompt
        assert "this completes the booking input set" in prompt
        assert "tool_action_hint=calendar.book_slot" in prompt
        assert 'slots.datetime="завтра 18:00"' in prompt
        assert "Clear stale collect follow-up fields" in prompt
        assert "expected_reply_type can no longer stay time" in prompt

    def test_policy_core_compact_prompt_existing_booking_datetime_fill_completes_direct_lookup(
        self,
    ):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "На завтра в 18:00." in prompt
        assert "current message now supplies an exact datetime surface" in prompt
        assert "intent=check_booking" in prompt
        assert "tool_action_hint=calendar.get_booking" in prompt
        assert "capability=booking_manage" in prompt
        assert "slots.datetime=<grounded datetime surface>" in prompt
        assert "alternate_datetime=<grounded datetime surface>" in prompt
        assert "clear expected_reply_type / next_question / open_questions" in prompt
        assert "do NOT keep stale time-follow-up axes" in prompt

    def test_policy_core_prompt_cancel_interrupt_uses_admin_handoff(self):
        prompt = _load_policy_core_prompt()

        assert '"А если я захочу отменить запись?"' in prompt
        assert "Для cancel/reschedule/admin-confirm без `referents.booking_ref` верни `action=\"handoff\"`" in prompt
        assert "`tool_action_hint=\"handoff\"`" in prompt
        assert "отмену, перенос и подтверждение администратором бот не делает" in prompt
        assert "выполнять `calendar.cancel`/`calendar.reschedule` из customer chat" in prompt

    def test_policy_core_compact_prompt_cancel_interrupt_uses_admin_handoff(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "For cancel/reschedule/admin-confirm requests" in prompt
        assert "do NOT execute calendar.cancel or calendar.reschedule from customer chat" in prompt
        assert "Return action=handoff" in prompt

    def test_policy_core_prompt_existing_booking_cancel_with_booking_ref_uses_handoff(self):
        prompt = _load_policy_core_prompt()

        assert '`referents.booking_ref` уже grounded' in prompt
        assert '"Тогда отмените запись."' in prompt
        assert '`tool_action_hint="handoff"`' in prompt
        assert "customer bot всё равно НЕ выполняет `calendar.cancel`/`calendar.reschedule`" in prompt

    def test_policy_core_compact_prompt_existing_booking_cancel_with_booking_ref_uses_handoff(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "including grounded booking_ref cases" in prompt
        assert '"Тогда отмените запись."' in prompt
        assert "tool_action_hint=handoff" in prompt
        assert "preserve booking_ref/customer/contact context" in prompt

    def test_policy_core_prompt_grounded_booking_ref_hypothetical_cancel_uses_admin_handoff(self):
        prompt = _load_policy_core_prompt()

        assert '"А если я захочу отменить запись?"' in prompt
        assert '"Как отменить эту запись?"' in prompt
        assert 'НЕ выполняй `calendar.cancel`' in prompt
        assert '`tool_action_hint="handoff"`' in prompt

    def test_policy_core_compact_prompt_grounded_booking_ref_hypothetical_cancel_uses_admin_handoff(
        self,
    ):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "including grounded booking_ref cases" in prompt
        assert "do NOT execute calendar.cancel" in prompt
        assert "tool_action_hint=handoff" in prompt

    def test_policy_core_compact_prompt_keeps_generic_active_booking_availability_on_requested_slot(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text
        lowered = prompt.casefold()

        assert "Какое время доступно?" in prompt
        assert "Do NOT switch to hours/location fact" in prompt
        assert "do not infer alternate_datetime" in lowered
        assert "carried context alone" in lowered
        assert "pending_question_act=ask_about_requested_slot" in prompt

    def test_policy_core_prompt_injects_generated_booking_progression_contract_block(self):
        prompt = _load_policy_core_prompt()

        assert "Canonical booking progression hard contract" in prompt
        assert "Do not drop carried `alternate_datetime` / `temporal_scope` while progression is still active." in prompt
        assert '`expected_reply_type="service_choice"`' in prompt
        assert "current message now supplies an explicit clock time" in prompt
        assert '"Давайте в 18:00."' in prompt
        assert 'must NOT ground `slots.service="маникюр"`' in prompt
        assert "Only the service-grounding variants (`pricing` / `promotions` / `duration` / `master_query`) may switch" in prompt
        assert 'Invalid shadow example: carried `alternate_datetime="на завтра в 18:00"` + `"Сколько длится маникюр?"`' in prompt
        assert '"К Айдане."' in prompt
        assert 'do NOT clear `expected_reply_type` / `next_question` on that specialist turn' in prompt

    def test_policy_core_compact_prompt_injects_generated_booking_progression_contract_block(
        self,
    ):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "Canonical booking progression hard contract" in prompt
        assert "Do not drop carried alternate_datetime / temporal_scope while progression is still active." in prompt
        assert "expected_reply_type=service_choice" in prompt
        assert "current message now gives an explicit clock time" in prompt
        assert "must not invent slots.service=маникюр" in prompt
        assert "Only service-grounding variants pricing / promotions / duration / master_query may switch service_choice to name" in prompt
        assert 'Invalid shadow example: carried alternate_datetime="на завтра в 18:00" + "Сколько длится маникюр?"' in prompt
        assert '"К Айдане."' in prompt
        assert "do not clear expected_reply_type / next_question on that specialist turn" in prompt

    def test_policy_core_compact_prompt_named_specialist_preference_under_active_time_collect_is_referent_followup(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "Мне нужен мастер Айгерим." in prompt
        assert "К Айдане." in prompt
        assert "subject_kind=specialist" in prompt
        assert "resolution_mode=referent_followup" in prompt
        assert "pending_question_act=null" in prompt
        assert "pending_question_target=specialist" in prompt
        assert "active_question_relation=referent_followup" in prompt
        assert "pending_question_act=slot_constraint" in prompt
        assert "only for the customer name" in prompt
        assert "must switch from time to specialist" in prompt
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
        assert '"Сколько это длится?"' in prompt
        assert 'media continuation больше не владеет смыслом хода' in prompt
        assert '`expected_reply_type="media"`' in prompt
        assert 'Forbidden: `expected_reply_type="media"`' in prompt
        assert '`memory.profile.resume_pending_question_contract`' in prompt

    def test_policy_core_compact_prompt_media_time_interrupt_returns_to_booking_collect(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "time/slot after that media follow-up" in prompt
        assert "Restore the booking collect contract" in prompt
        assert "Do NOT keep expected_reply_type=media" in prompt
        assert '"Сколько это длится?"' in prompt
        assert "resume_pending_question_contract" in prompt

    def test_policy_core_compact_prompt_advances_post_media_clock_time_fill_to_name_collect(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert 'If that later post-media turn already supplies a concrete clock time' in prompt
        assert '"А в 16:45 можно?"' in prompt
        assert "subject_kind=booking, capability=bookability, resolution_mode=direct" in prompt
        assert 'expected_reply_type=name, next_question=name, open_questions=[name]' in prompt
        assert "slots.datetime and alternate_datetime" in prompt
        assert "pending_question_act=fill_requested_slot" in prompt
        assert 'executor-parseable exact-time surface such as "завтра 17:45"' in prompt
        assert "do NOT keep pending_question_target=specialist" in prompt
        assert "expected_reply_type can no longer stay time" in prompt
        assert "generic_info_interrupt only answers the side fact turn" in prompt

    def test_policy_core_prompt_advances_exact_clock_time_after_specialist_or_media_carryover(
        self,
    ):
        prompt = _load_policy_core_prompt()

        assert '"Можно на 17:45?"' in prompt
        assert '"А в 16:45 можно?"' in prompt
        assert '`expected_reply_type="name"`' in prompt
        assert '`pending_question_act="fill_requested_slot"`' in prompt
        assert '`slots.datetime="<carried day/date + exact clock time in user-language surface>"`' in prompt
        assert '`expected_reply_type` больше не может оставаться `time`' in prompt
        assert '`generic_info_interrupt` only answers the side fact turn' in prompt
        assert "executor-parseable" in prompt
        assert "`завтра вечером в 18:00`" in prompt
        assert 'translated carry-over вроде `"tomorrow 16:45"`' in prompt

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

    def test_policy_core_prompt_active_booking_manage_interrupt_does_not_fall_back_to_generic_info(self):
        prompt = _load_policy_core_prompt()

        assert '"А если я захочу отменить запись?"' in prompt
        assert '`capability="booking_manage"`' in prompt
        assert '`action="handoff"`' in prompt
        assert '`tool_action_hint="handoff"`' in prompt
        assert "Forbidden: выполнять `calendar.cancel`/`calendar.reschedule` из customer chat" in prompt
        assert '`tool_action_hint="info"`' in prompt
        assert 'generic reply `"Я уточню это для вас."' in prompt

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

    def test_policy_core_prompt_mixed_first_turn_fact_scope_preserves_hours_and_services_overview(self):
        prompt = _load_policy_core_prompt()

        assert '"Вы сегодня работаете? Вы маникюром занимаетесь?"' in prompt
        assert '`tool_action_hint="info"`' in prompt
        assert '`["hours","services_overview"]`' in prompt
        assert '"Здравствуйте! Вы сегодня работаете? Сколько стоит педикюр?"' in prompt
        assert '"Вы сегодня работаете, есть акции на педикюр и как с вами связаться?"' in prompt
        assert '"Вы сегодня работаете, есть акции и где находитесь?"' in prompt
        assert '"Вы сегодня работаете, есть акции, где находитесь и как с вами связаться?"' in prompt
        assert '`["hours","pricing"]`' in prompt
        assert '`["hours","duration"]`' in prompt
        assert '`["hours","promotions"]`' in prompt
        assert '`["hours","promotions","contact"]`' in prompt
        assert '`["hours","location","promotions"]`' in prompt
        assert '`["hours","location","promotions","contact"]`' in prompt
        assert '`subject_kind="general"`' in prompt
        assert '`slots.service` / `referents.service`' in prompt
        assert '`expected_reply_type="service_choice"`' in prompt
        assert '`services_overview` разрешён только если текущий message явно спрашивает service presence' in prompt
        assert '"Вы сегодня работаете, где вы находитесь и сколько стоит маникюр?"' in prompt
        assert 'Forbidden: `"Вы сегодня работаете, где вы находитесь и сколько стоит маникюр?"` -> `pack_refs=["hours","location","pricing","services_overview"]`' in prompt

    def test_policy_core_prompt_location_service_fact_scope_preserves_location_head_intent(self):
        prompt = _load_policy_core_prompt()

        assert '"Сколько длится маникюр, кто делает маникюр и где вы находитесь?"' in prompt
        assert '"Кто делает маникюр, сколько стоит и где вы находитесь?"' in prompt
        assert '`intent="location"`' in prompt
        assert '`["location","pricing","duration"]`' in prompt
        assert '`["location","master"]`' in prompt
        assert '`["location","pricing","master"]`' in prompt
        assert "surface order" in prompt
        assert "`services_overview` разрешён только если текущий message явно спрашивает service presence" in prompt
        assert "Forbidden: выдумывать `hours`" in prompt

    def test_policy_core_prompt_location_service_booking_followup_preserves_location_head_intent(self):
        prompt = _load_policy_core_prompt()

        assert '"Где вы находитесь и сколько длится педикюр, можно записаться завтра вечером?"' in prompt
        assert '"Сколько стоит маникюр, сколько длится, где находитесь и можно записаться?"' in prompt
        assert '`intent="location"`' in prompt
        assert '`goal="booking"`' in prompt
        assert '`["location","duration"]`' in prompt
        assert '`["location","pricing","duration"]`' in prompt
        assert '`expected_reply_type="time"`' in prompt
        assert "Forbidden: схлопывать такой turn до fact-only" in prompt
        assert "не добавляй `services_overview`" in prompt

    def test_policy_core_prompt_service_fact_head_beats_temporal_side_booking(self):
        prompt = _load_policy_core_prompt()

        assert '"Сколько стоит педикюр и можно завтра в 6?"' in prompt
        assert '"Сколько стоит маникюр, можно записаться завтра вечером?"' in prompt
        assert '`tool_action_hint="catalog.service_query"`' in prompt
        assert '`pack_refs=["pricing"]`' in prompt
        assert '`pack_refs=["duration"]`' in prompt
        assert '`goal="booking"`' in prompt
        assert '`expected_reply_type="time"`' in prompt
        assert "Forbidden: переводить такой turn в booking collect" in prompt
        assert "fact-only ответ без booking follow-up" in prompt

    def test_policy_core_prompt_hours_service_booking_followup_preserves_hours_head_intent(self):
        prompt = _load_policy_core_prompt()

        assert '"Вы сегодня работаете и сколько стоит маникюр, можно записаться на 7?"' in prompt
        assert '"До скольки открыты и сколько длится педикюр, можно записаться?"' in prompt
        assert '`intent="hours"`' in prompt
        assert '`goal="booking"`' in prompt
        assert '`["hours","pricing"]`' in prompt
        assert '`["hours","duration"]`' in prompt
        assert '`expected_reply_type="time"`' in prompt
        assert "Forbidden: схлопывать такой turn до `intent=\"pricing\"`" in prompt

    def test_policy_core_prompt_hours_location_booking_followup_preserves_combined_scope(self):
        prompt = _load_policy_core_prompt()

        assert '"Вы сегодня работаете, где вы находитесь, можно записаться?"' in prompt
        assert '"Вы сегодня работаете, где вы находитесь, хочу записаться."' in prompt
        assert '`pack_refs=["hours","location"]`' in prompt
        assert '`goal="booking"`' in prompt
        assert '`expected_reply_type="service_choice"`' in prompt
        assert '`resolution_mode="policy_fact"`' in prompt
        assert '`capability="bookability"`' in prompt
        assert '`resolution_mode="clarify_missing_subject"`' in prompt
        assert 'location-only fact scope' in prompt

    def test_policy_core_prompt_service_query_multifact_preserves_full_scope(self):
        prompt = _load_policy_core_prompt()

        assert '"Сколько стоит маникюр и сколько длится маникюр?"' in prompt
        assert '`["pricing","duration"]`' in prompt
        assert "не должны схлопываться до одной секции" in prompt

    def test_policy_core_prompt_service_query_multifact_booking_followup_preserves_progression(self):
        prompt = _load_policy_core_prompt()

        assert '"Сколько стоит маникюр и сколько длится, можно записаться завтра вечером?"' in prompt
        assert '"Сколько стоит педикюр и сколько длится, можно записаться сегодня после 6?"' in prompt
        assert '"Кто делает маникюр и как с вами связаться, можно записаться?"' in prompt
        assert '`goal="booking"`' in prompt
        assert '`["pricing","duration"]`' in prompt
        assert '`["master","contact"]`' in prompt
        assert '`expected_reply_type="time"`' in prompt
        assert "Explicit `contact` / `parking` side asks" in prompt
        assert "схлопывать такой turn до fact-only без follow-up" in prompt

    def test_policy_core_prompt_mixed_first_turn_promotions_precedence_over_side_asks(self):
        prompt = _load_policy_core_prompt()

        assert '"Есть скидки, хочу записаться и адрес, пожалуйста."' in prompt
        assert '`intent="promotions"`' in prompt
        assert "Forbidden competing head intents for this family" in prompt
        assert '`intent="booking"`' in prompt
        assert '`intent="location"`' in prompt
        assert '`intent="pricing"`' in prompt
        assert '`intent="consult"`' in prompt
        assert '`pack_refs=["promotions","location"]`' in prompt
        assert '`subject_kind="general"`' in prompt
        assert "Forbidden: отвечать только адресом/локацией" in prompt
        assert "молча выбрасывать явно запрошенный address/location" in prompt

    def test_policy_core_prompt_promotions_location_booking_preserves_service_followup(self):
        prompt = _load_policy_core_prompt()

        assert '"Есть скидки, хочу записаться и адрес, пожалуйста."' in prompt
        assert '"Есть акции и где вы находитесь, хочу записаться."' in prompt
        assert '`pack_refs=["promotions","location"]`' in prompt
        assert '`goal="booking"`' in prompt
        assert '`expected_reply_type="service_choice"`' in prompt
        assert "promotions+location without booking follow-up" in prompt

    def test_policy_core_prompt_promotions_booking_preserves_service_followup(self):
        prompt = _load_policy_core_prompt()

        assert '"Есть скидки, хочу записаться."' in prompt
        assert '`intent="promotions"`' in prompt
        assert '`pack_refs=["promotions"]`' in prompt
        assert '`goal="booking"`' in prompt
        assert '`expected_reply_type="service_choice"`' in prompt
        assert "promotions-only reply without booking follow-up" in prompt

    def test_policy_core_prompt_promotions_grounded_service_booking_preserves_time_followup(self):
        prompt = _load_policy_core_prompt()

        assert '"Есть акции на маникюр, хочу записаться."' in prompt
        assert '"Есть скидки на педикюр, хочу записаться."' in prompt
        assert '`intent="promotions"`' in prompt
        assert '`pack_refs=["promotions"]`' in prompt
        assert '`subject_kind="service"`' in prompt
        assert '`expected_reply_type="time"`' in prompt
        assert '`next_question="datetime"`' in prompt
        assert '`pending_question_act="ask_about_requested_slot"`' in prompt
        assert '`open_questions=["service"]`, когда concrete service уже grounded' in prompt
        assert "снова спрашивать услугу" in prompt

    def test_policy_core_prompt_promotions_grounded_service_location_booking_preserves_time_followup(
        self,
    ):
        prompt = _load_policy_core_prompt()

        assert '"Есть акции на маникюр, хочу записаться и адрес, пожалуйста."' in prompt
        assert '`pack_refs=["promotions","location"]`' in prompt
        assert '`subject_kind="service"`' in prompt
        assert '`expected_reply_type="time"`' in prompt
        assert '`next_question="datetime"`' in prompt
        assert "молча выбрасывать explicit location/address" in prompt

    def test_policy_core_prompt_promotions_grounded_service_contact_booking_preserves_time_followup(
        self,
    ):
        prompt = _load_policy_core_prompt()

        assert '"Есть акции на маникюр, хочу записаться и как с вами связаться?"' in prompt
        assert '`pack_refs=["promotions","contact"]`' in prompt
        assert '`subject_kind="service"`' in prompt
        assert '`expected_reply_type="time"`' in prompt
        assert '`next_question="datetime"`' in prompt
        assert "explicit address/location/contact/parking" in prompt

    def test_policy_core_prompt_promotions_grounded_service_location_contact_booking_preserves_time_followup(
        self,
    ):
        prompt = _load_policy_core_prompt()

        assert '"Есть акции на маникюр, хочу записаться, где вы находитесь и как с вами связаться?"' in prompt
        assert '["promotions","location","contact"]' in prompt
        assert '`expected_reply_type="time"`' in prompt
        assert "с пустыми `pending_question_act` / `pending_question_target` / `active_question_relation`" in prompt
        assert "location-head/service-fact override" in prompt

    def test_policy_core_prompt_catalog_service_query_uses_exact_fact_family_pack_refs(self):
        prompt = _load_policy_core_prompt()

        assert '`["pricing"]`' in prompt
        assert '`["duration"]`' in prompt
        assert '`["promotions"]`' in prompt
        assert '`pack_refs=["master"]`' in prompt
        assert '`tool_action_hint="info"`' in prompt
        assert "Не тащи `pack_refs` из предыдущего fact interrupt" in prompt
        assert "не оставляй `pricing` / `duration` / `master` head по аналогии" in prompt
        assert "если в том же message явно спрашиваются `location/address` или `working hours`" in prompt
        assert "держи general fact head первым в `pack_refs`" in prompt
        assert "Standalone fact rule" in prompt
        assert '`expected_reply_type=null`' in prompt

    def test_policy_core_compact_prompt_master_query_uses_info_tool_family(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "- master_query -> info with pack_refs=[master], capability=master" in prompt

    def test_policy_core_generated_contract_block_is_injected_into_full_and_compact_prompts(self):
        full_prompt = _load_policy_core_prompt()
        compact_prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "{{GENERATED_MIXED_FIRST_TURN_FACT_CONTRACT_BLOCK}}" not in full_prompt
        assert "{{GENERATED_MIXED_FIRST_TURN_FACT_CONTRACT_BLOCK}}" not in compact_prompt

        for block in iter_policy_core_generated_contract_blocks():
            assert block.full_prompt_text in full_prompt
            assert block.compact_prompt_text in compact_prompt

    def test_policy_core_generated_contract_tokens_remain_allowed_by_vocabulary_snapshot(self):
        snapshot = build_policy_core_vocabulary_snapshot()
        required = policy_core_generated_contract_semantic_tokens()
        allowlists = {
            "intents": set(snapshot.intents),
            "actions": set(snapshot.actions),
            "expected_reply_types": set(snapshot.expected_reply_types),
            "next_questions": set(snapshot.next_questions),
            "subject_kinds": set(snapshot.subject_kinds),
            "capabilities": set(snapshot.capabilities),
            "temporal_scopes": set(snapshot.temporal_scopes),
            "resolution_modes": set(snapshot.resolution_modes),
            "pending_question_acts": set(snapshot.pending_question_acts),
            "pending_question_targets": set(snapshot.pending_question_targets),
            "active_question_relations": set(snapshot.active_question_relations),
        }

        for category, values in required.items():
            assert set(values) <= allowlists[category]

    def test_policy_core_generated_contract_repair_templates_cover_mixed_booking_envelope(self):
        assert {
            "mixed_first_turn_location_service_fact_scope",
            "mixed_first_turn_location_service_fact_booking_followup",
            "mixed_first_turn_hours_service_booking_followup",
            "mixed_first_turn_hours_location_booking_followup",
            "mixed_first_turn_hours_location_fact_scope",
            "mixed_first_turn_service_fact_booking_side_precedence",
            "service_query_multifact_booking_followup",
            "mixed_first_turn_hours_service_fact_scope",
            "mixed_first_turn_promotions_precedence_fact_scope",
            "mixed_first_turn_promotions_precedence_missing_service_booking_followup",
            "mixed_first_turn_promotions_precedence_grounded_service_booking_followup",
            "promotions_booking_followup",
            "promotions_location_booking_followup",
            "promotions_grounded_service_booking_followup",
            "active_booking_requested_slot_availability_followup",
            "active_booking_info_interrupt_contract",
        } <= policy_core_generated_contract_repair_template_ids()

    def test_policy_core_generated_active_booking_info_interrupt_repair_template_supports_general_subject_kind(
        self,
    ):
        rendered = render_policy_core_generated_contract_repair_template(
            "active_booking_info_interrupt_contract",
            head_intent="location",
            tool_action_hint="catalog.location",
            expected_pack_refs='["parking"]',
            expected_capability="location",
            expected_subject_kind="general",
            carry_reply_type="service_choice",
            carry_next_question="service",
            open_questions='["service"]',
            carry_pending_act="ask_about_requested_slot",
            carry_pending_target="time",
            carry_temporal_scope_clause='Keep `temporal_scope="specific_time"`.',
            carry_alternate_datetime_clause='Keep `alternate_datetime="на завтра в 18:00"`.',
            interrupt_subject_grounding_clause='Keep `slots.service` / `referents.service` empty.',
        )

        assert '`subject_kind="general"`' in rendered
        assert 'Keep `slots.service` / `referents.service` empty.' in rendered

    def test_route_llm_policy_core_prefers_compact_first_attempt_and_retries_full_prompt(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_COMPACT_FIRST_ATTEMPT",
            True,
        )

        valid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": None,
            "slots": {"service": None, "datetime": None},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "reason": "start_booking_missing_service_collect",
            "goal": "booking",
            "referents": {},
            "subject_kind": "general",
            "capability": "bookability",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "direct",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
        }

        class CompactFirstProvider:
            def __init__(self) -> None:
                self.system_prompt_lengths: list[int] = []
                self.call_count = 0

            def generate(self, *, messages, **_kwargs):
                self.call_count += 1
                self.system_prompt_lengths.append(len(messages[0]["content"]))
                if self.call_count == 1:
                    return DummyResponse("{")
                return DummyResponse(json.dumps(valid_payload))

        provider = CompactFirstProvider()
        with patch("app.services.intent_service.get_llm_provider", return_value=provider):
            result = route_llm_policy_core(
                "Хочу записаться",
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["compact_input_used"] is True
        assert result["compact_retry_used"] is True
        assert provider.call_count == 2
        assert provider.system_prompt_lengths[0] < provider.system_prompt_lengths[1]

    def test_route_llm_policy_core_uses_full_prompt_for_first_turn_exact_booking(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_COMPACT_FIRST_ATTEMPT",
            True,
        )

        valid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": None,
            "slots": {"service": "маникюр", "datetime": "8 мая в 10:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "reason": "start_booking_exact_datetime_direct_name_collect",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message_grounding",
                }
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "8 мая в 10:00",
            "resolution_mode": "direct",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "fill_requested_slot",
        }

        class CompactPromptProvider:
            def __init__(self) -> None:
                self.system_prompt_lengths: list[int] = []
                self.policy_inputs: list[dict] = []

            def generate(self, *, messages, **_kwargs):
                self.system_prompt_lengths.append(len(messages[0]["content"]))
                self.policy_inputs.append(json.loads(messages[1]["content"]))
                return DummyResponse(json.dumps(valid_payload))

        provider = CompactPromptProvider()
        with patch("app.services.intent_service.get_llm_provider", return_value=provider):
            result = route_llm_policy_core(
                "Хочу записаться на маникюр 8 мая в 10:00",
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["compact_input_used"] is False
        assert result["compact_retry_used"] is False
        assert result["focused_start_booking_exact_datetime"] is True
        assert result["policy_input"]["allowed"]["info_refs"] == []
        assert result["policy_input"]["allowed"]["consult_refs"] == []
        assert result["policy_input"]["allowed"]["tool_actions"] == ["collect", "handoff"]
        assert provider.policy_inputs[0]["allowed"]["tool_actions"] == ["collect", "handoff"]
        assert provider.system_prompt_lengths == [
            len(intent_service_module._load_policy_core_prompt())
        ]

    def test_route_llm_policy_core_focuses_full_detail_exact_booking_to_book_slot(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        valid_payload = {
            "intent": "booking",
            "action": "fact",
            "tool_action_hint": "calendar.book_slot",
            "pack_refs": [],
            "slots": {
                "service": "Маникюр",
                "datetime": "8 мая в 10:00",
                "name": "Диана",
                "phone": "+77010101010",
            },
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "reason": "start_booking_exact_datetime_direct_book_slot",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "message_grounding",
                }
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "8 мая в 10:00",
            "resolution_mode": "live_calendar",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps(valid_payload)
            )
            result = route_llm_policy_core(
                "Еще раз: хочу маникюр 8 мая в 10:00, Диана +77010101010",
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["focused_start_booking_exact_datetime"] is True
        assert result["boundary_normalization_used"] is False
        assert result["binding"]["tool_action"] == "calendar.book_slot"
        assert result["binding"]["tool_args"]["customer_name"] == "Диана"
        assert result["binding"]["tool_args"]["customer_phone"] == "+77010101010"
        assert result["policy_input"]["allowed"]["tool_actions"] == [
            "calendar.book_slot"
        ]

    def test_route_llm_policy_core_forces_direct_missing_service_exact_time_to_service_collect(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_COMPACT_FIRST_ATTEMPT",
            True,
        )

        valid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": None,
            "slots": {"datetime": "11 мая в 12:00"},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.75,
            "reason": "direct_booking_exact_datetime_missing_service",
            "goal": "booking",
            "entity_refs": None,
            "referents": {},
            "subject_kind": "general",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "11 мая в 12:00",
            "resolution_mode": "clarify_missing_subject",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
            result = route_llm_policy_core(
                "Хочу записаться 11 мая в 12:00",
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["compact_input_used"] is False
        assert result["focused_start_booking_exact_datetime_missing_service"] is True
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        assert kwargs["response_format"] == {"type": "json_object"}
        forced_fields = json.loads(kwargs["messages"][1]["content"])["focus_contract"]["forced_fields"]
        assert forced_fields["intent"] == "booking"
        assert forced_fields["tool_action_hint"] == "collect"
        assert forced_fields["expected_reply_type"] == "service_choice"
        assert forced_fields["next_question"] == "service"
        assert forced_fields["alternate_datetime"] == "11 мая в 12:00"
        assert forced_fields["slots"] == {"datetime": "11 мая в 12:00"}

    def test_route_llm_policy_core_forces_missing_service_exact_time_carryover(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_COMPACT_FIRST_ATTEMPT",
            True,
        )

        valid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": None,
            "slots": {"datetime": "11 мая в 12:00"},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.75,
            "reason": "missing_service_with_exact_datetime_availability_request",
            "goal": "booking",
            "entity_refs": None,
            "referents": {},
            "subject_kind": "general",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "11 мая в 12:00",
            "resolution_mode": "clarify_missing_subject",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
            result = route_llm_policy_core(
                "На 11 мая в 12:00 есть время?",
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["compact_input_used"] is False
        assert result["focused_owner_contract_used"] is True
        assert result["focused_booking_availability_missing_service"] is True
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        assert kwargs["response_format"] == {"type": "json_object"}
        forced_fields = json.loads(kwargs["messages"][1]["content"])["focus_contract"]["forced_fields"]
        assert forced_fields["intent"] == "booking"
        assert forced_fields["tool_action_hint"] == "collect"
        assert forced_fields["expected_reply_type"] == "service_choice"
        assert forced_fields["next_question"] == "service"
        assert forced_fields["open_questions"] == ["service"]
        assert forced_fields["alternate_datetime"] == "11 мая в 12:00"
        assert forced_fields["slots"] == {"datetime": "11 мая в 12:00"}

    def test_route_llm_policy_core_forces_service_only_booking_to_time_collect(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            "app.services.intent_service._policy_core_resolve_current_message_service_hint",
            lambda **_kwargs: "Маникюр",
        )

        valid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "Маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "message_grounding",
                }
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "direct",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
            result = route_llm_policy_core(
                "Хочу записаться на маникюр",
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["focused_start_booking_service_collect"] is True
        assert result["focused_owner_contract_used"] is True
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        assert "LLM Policy Core Focused Contract" in kwargs["messages"][0]["content"]
        policy_input = json.loads(kwargs["messages"][1]["content"])
        assert "context" not in policy_input
        assert policy_input["focus_contract"]["forced_fields"]["slots"] == {
            "service": "Маникюр"
        }
        assert kwargs["response_format"] == {"type": "json_object"}
        assert policy_input["focus_contract"]["forced_fields"]["expected_reply_type"] == "time"
        assert policy_input["focus_contract"]["forced_fields"]["next_question"] == "datetime"

    def test_route_llm_policy_core_forces_active_booking_time_fill_to_name_collect(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_COMPACT_FIRST_ATTEMPT",
            True,
        )

        valid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр", "datetime": "28 мая в 11:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "memory.semantic_contract",
                }
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "28 мая в 11:00",
            "resolution_mode": "direct",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "fill_requested_slot",
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
            result = route_llm_policy_core(
                "28 мая в 11:00",
                client_slug="demo_salon",
                current_goal="booking",
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "contract_version": "semantic_contract.v1",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                    "slot_state": {"service": "маникюр"},
                },
            )

        assert result["ok"] is True
        assert result["compact_input_used"] is False
        assert result["focused_active_booking_time_fill"] is True
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        assert kwargs["response_format"] == {"type": "json_object"}
        forced_fields = json.loads(kwargs["messages"][1]["content"])["focus_contract"]["forced_fields"]
        assert forced_fields["intent"] == "booking"
        assert forced_fields["action"] == "collect"
        assert forced_fields["tool_action_hint"] == "collect"
        assert forced_fields["expected_reply_type"] == "name"
        assert forced_fields["next_question"] == "name"
        assert forced_fields["alternate_datetime"] == "28 мая в 11:00"
        assert forced_fields["slots"]["datetime"] == "28 мая в 11:00"

    def test_route_llm_policy_core_forces_active_booking_partial_datetime_to_time_collect(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_COMPACT_FIRST_ATTEMPT",
            True,
        )

        valid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "окрашивание"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "окрашивание",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "memory.semantic_contract",
                }
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "weekday",
            "alternate_datetime": "пятница вечер",
            "resolution_mode": "direct",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "reason": "active_booking_partial_datetime_slot_constraint",
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
            result = route_llm_policy_core(
                "ок тогда пятница вечер",
                client_slug="demo_salon",
                current_goal="booking",
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "окрашивание"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "generic_info_interrupt",
                    },
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "capability": "pricing",
                        "subject_kind": "service",
                        "temporal_scope": "none",
                        "resolution_mode": "policy_fact",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "generic_info_interrupt",
                        "referents": {
                            "service": {
                                "value": "окрашивание",
                                "entity_type": "service",
                                "source_ref": "memory.semantic_contract",
                            }
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["compact_input_used"] is False
        assert result["focused_active_booking_partial_datetime"] is True
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        assert kwargs["response_format"] == {"type": "json_object"}
        forced_fields = json.loads(kwargs["messages"][1]["content"])["focus_contract"]["forced_fields"]
        assert forced_fields["slots"] == {"service": "окрашивание"}
        assert forced_fields["expected_reply_type"] == "time"
        assert forced_fields["next_question"] == "datetime"
        assert forced_fields["alternate_datetime"] == "пятница вечер"
        assert forced_fields["pending_question_act"] == "slot_constraint"

    def test_active_booking_partial_datetime_forced_fields_preserves_carried_scope(
        self,
    ):
        fields = intent_service_module._policy_core_active_booking_partial_datetime_collect_forced_fields(
            {
                "active_goal": "booking",
                "slot_state": {"service": "окрашивание"},
                "pending_question_contract": {
                    "expected_reply_type": "time",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                    "pending_question_act": "slot_constraint",
                    "pending_question_target": "time",
                    "active_question_relation": "slot_constraint",
                },
                "semantic_contract": {
                    "contract_version": "semantic_contract.v1",
                    "capability": "bookability",
                    "subject_kind": "booking",
                    "temporal_scope": "weekday",
                    "alternate_datetime": "пятница вечер",
                    "resolution_mode": "direct",
                    "pending_question_act": "slot_constraint",
                    "pending_question_target": "time",
                    "active_question_relation": "slot_constraint",
                    "referents": {
                        "service": {
                            "value": "окрашивание",
                            "entity_type": "service",
                            "source_ref": "carryover",
                        }
                    },
                },
            },
            current_message="если после шести есть",
        )

        assert fields is not None
        assert fields["slots"] == {"service": "окрашивание"}
        assert fields["expected_reply_type"] == "time"
        assert fields["next_question"] == "datetime"
        assert fields["temporal_scope"] == "weekday"
        assert fields["alternate_datetime"] == "после шести есть"
        assert fields["active_question_relation"] == "slot_constraint"

    def test_route_llm_policy_core_forces_active_booking_service_fill_to_name_collect(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            "app.services.intent_service._policy_core_resolve_current_message_service_hint",
            lambda **_kwargs: "Маникюр",
        )

        valid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "Маникюр", "datetime": "12 июня в 12:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "message_grounding",
                }
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "12 июня в 12:00",
            "resolution_mode": "direct",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "fill_requested_slot",
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
            result = route_llm_policy_core(
                "маникюр",
                client_slug="demo_salon",
                current_goal="booking",
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "contract_version": "semantic_contract.v1",
                        "subject_kind": "general",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "12 июня в 12:00",
                        "resolution_mode": "clarify_missing_subject",
                    },
                    "slot_state": {"datetime": "12 июня в 12:00"},
                },
            )

        assert result["ok"] is True
        assert result["compact_input_used"] is False
        assert result["focused_owner_contract_used"] is True
        assert result["focused_active_booking_service_fill"] is True
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        assert "LLM Policy Core Focused Contract" in kwargs["messages"][0]["content"]
        policy_input = json.loads(kwargs["messages"][1]["content"])
        assert policy_input["focus_contract"]["forced_fields"]["slots"] == {
            "service": "Маникюр",
            "datetime": "12 июня в 12:00",
        }
        assert kwargs["response_format"] == {"type": "json_object"}
        assert policy_input["focus_contract"]["forced_fields"]["expected_reply_type"] == "name"

    def test_route_llm_policy_core_forces_active_booking_price_interrupt_to_preserve_time_followup(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_COMPACT_FIRST_ATTEMPT",
            True,
        )
        monkeypatch.setattr(
            "app.services.intent_service._policy_core_resolve_current_message_service_hint",
            lambda **_kwargs: "маникюр",
        )

        valid_payload = {
            "intent": "pricing",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["pricing"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "memory.semantic_contract",
                }
            },
            "subject_kind": "service",
            "capability": "pricing",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
            result = route_llm_policy_core(
                "Сколько стоит маникюр?",
                client_slug="demo_salon",
                current_goal="booking",
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "contract_version": "semantic_contract.v1",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                    "slot_state": {"service": "маникюр"},
                },
            )

        assert result["ok"] is True
        assert result["compact_input_used"] is False
        assert result["focused_active_booking_info_interrupt"] == "pricing"
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        assert kwargs["response_format"] == {"type": "json_object"}
        forced_fields = json.loads(kwargs["messages"][1]["content"])["focus_contract"]["forced_fields"]
        assert forced_fields["intent"] == "pricing"
        assert forced_fields["tool_action_hint"] == "catalog.service_query"
        assert forced_fields["expected_reply_type"] == "time"
        assert forced_fields["next_question"] == "datetime"
        assert forced_fields["active_question_relation"] == "generic_info_interrupt"

    def test_route_llm_policy_core_forces_active_booking_price_duration_interrupt(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_COMPACT_FIRST_ATTEMPT",
            True,
        )

        valid_payload = {
            "intent": "pricing",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["pricing", "duration"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "memory.semantic_contract",
                }
            },
            "subject_kind": "service",
            "capability": "pricing",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
            result = route_llm_policy_core(
                "А сколько стоит и сколько по времени?",
                client_slug="demo_salon",
                current_goal="booking",
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "contract_version": "semantic_contract.v1",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                    "slot_state": {"service": "маникюр"},
                },
            )

        assert result["ok"] is True
        assert result["focused_active_booking_info_interrupt"] == "pricing"
        forced_fields = json.loads(
            mock_llm.return_value.generate.call_args.kwargs["messages"][1]["content"]
        )["focus_contract"]["forced_fields"]
        assert forced_fields["pack_refs"] == ["pricing", "duration"]
        assert forced_fields["tool_action_hint"] == "catalog.service_query"
        assert forced_fields["expected_reply_type"] == "time"
        assert forced_fields["next_question"] == "datetime"
        assert forced_fields["active_question_relation"] == "generic_info_interrupt"

    def test_route_llm_policy_core_blocks_compact_first_for_booking_continuity(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_COMPACT_FIRST_ATTEMPT",
            True,
        )

        valid_payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["master"],
            "slots": {"service": "маникюр", "datetime": None, "name": None, "phone": None},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "reason": "user_asks_master_for_grounded_service_interrupting_active_booking_datetime_slot",
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
            "capability": "master",
            "temporal_scope": "day",
            "alternate_datetime": "завтра вечером",
            "resolution_mode": "policy_fact",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        }

        memory_profile = {
            "active_goal": "booking",
            "pending_question_contract": {
                "active_question_relation": "slot_constraint",
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "reason": "collect:datetime",
            },
            "semantic_contract": {
                "active_question_relation": "slot_constraint",
                "alternate_datetime": "завтра вечером",
                "capability": "bookability",
                "contract_version": "semantic_contract.v1",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "resolution_mode": "direct",
                "subject_kind": "booking",
                "temporal_scope": "day",
            },
            "slot_state": {"datetime": "завтра вечером"},
        }

        class FullPromptProvider:
            def __init__(self) -> None:
                self.system_prompt_lengths: list[int] = []

            def generate(self, *, messages, **_kwargs):
                self.system_prompt_lengths.append(len(messages[0]["content"]))
                return DummyResponse(json.dumps(valid_payload))

        provider = FullPromptProvider()
        with patch("app.services.intent_service.get_llm_provider", return_value=provider):
            result = route_llm_policy_core(
                "Кто делает маникюр?",
                client_slug="demo_salon",
                current_goal="booking",
                memory_profile=memory_profile,
                memory_summary=(
                    "user: Хочу записаться на маникюр завтра вечером. assistant: "
                    "Понял, завтра вечером. Подскажите, пожалуйста, точное время."
                ),
            )

        assert result["ok"] is True
        assert result["compact_input_used"] is False
        assert result["compact_retry_used"] is False
        assert len(provider.system_prompt_lengths) == 1

    def test_route_llm_policy_core_uses_compact_first_for_missing_service_grounded_interrupt_progression(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_COMPACT_FIRST_ATTEMPT",
            True,
        )

        valid_payload = {
            "intent": "promotions",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["promotions"],
            "slots": {"service": "маникюр", "datetime": "завтра в 18:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.72,
            "reason": (
                "Пользователь спрашивает об акциях на маникюр; это служебный "
                "интерапт, который одновременно завершает уточнение услуги в "
                "активной записи и переводит сбор к имени клиента при сохранении "
                "переносимого слота 'на завтра в 18:00'."
            ),
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": None,
                    "entity_type": None,
                    "source_ref": None,
                }
            },
            "subject_kind": "service",
            "capability": "promotions",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра в 18:00",
            "resolution_mode": "policy_fact",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }

        memory_profile = {
            "active_goal": "booking",
            "pending_question_contract": {
                "expected_reply_type": "service_choice",
                "next_question": "service",
                "open_questions": ["service"],
                "reason": "collect:service",
            },
            "semantic_contract": {
                "alternate_datetime": "завтра в 18:00",
                "capability": "bookability",
                "contract_version": "semantic_contract.v1",
                "resolution_mode": "clarify_missing_subject",
                "subject_kind": "general",
                "temporal_scope": "specific_time",
            },
            "slot_state": {"datetime": "завтра в 18:00"},
        }

        class CompactSafeContinuityProvider:
            def __init__(self) -> None:
                self.system_prompt_lengths: list[int] = []

            def generate(self, *, messages, **_kwargs):
                self.system_prompt_lengths.append(len(messages[0]["content"]))
                return DummyResponse(json.dumps(valid_payload))

        provider = CompactSafeContinuityProvider()
        with patch("app.services.intent_service.get_llm_provider", return_value=provider):
            result = route_llm_policy_core(
                "Есть ли акции на маникюр?",
                client_slug="demo_salon",
                current_goal="booking",
                memory_profile=memory_profile,
                memory_summary=(
                    "user: На завтра в 18:00 есть время? assistant: На какую услугу "
                    "хотите записаться?"
                ),
            )

        assert result["compact_input_used"] is False
        assert result["focused_owner_contract_used"] is True
        assert result["compact_retry_used"] is False
        assert len(provider.system_prompt_lengths) == 1

    def test_route_llm_policy_core_uses_compact_first_for_master_missing_service_continuity(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_COMPACT_FIRST_ATTEMPT",
            True,
        )

        valid_payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["master"],
            "slots": {"service": "маникюр", "datetime": "на завтра в 18:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.62,
            "reason": (
                "Пользователь в активном контексте бронирования спрашивает "
                "«Кто делает маникюр?», тем самым уточняет услугу и запрашивает "
                "состав мастеров."
            ),
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": None,
                    "entity_type": None,
                    "source_ref": "context.message_grounding_hints.service",
                }
            },
            "subject_kind": "service",
            "capability": "master",
            "temporal_scope": "specific_time",
            "alternate_datetime": "на завтра в 18:00",
            "resolution_mode": "policy_fact",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }

        memory_profile = {
            "active_goal": "booking",
            "pending_question_contract": {
                "expected_reply_type": "service_choice",
                "next_question": "service",
                "open_questions": ["service"],
                "reason": "collect:service",
            },
            "semantic_contract": {
                "alternate_datetime": "на завтра в 18:00",
                "capability": "bookability",
                "contract_version": "semantic_contract.v1",
                "resolution_mode": "clarify_missing_subject",
                "subject_kind": "general",
                "temporal_scope": "specific_time",
            },
            "slot_state": {"datetime": "на завтра в 18:00"},
        }

        class MasterContinuityProvider:
            def __init__(self) -> None:
                self.system_prompt_lengths: list[int] = []

            def generate(self, *, messages, **_kwargs):
                self.system_prompt_lengths.append(len(messages[0]["content"]))
                return DummyResponse(json.dumps(valid_payload))

        provider = MasterContinuityProvider()
        with patch("app.services.intent_service.get_llm_provider", return_value=provider):
            result = route_llm_policy_core(
                "Кто делает маникюр?",
                client_slug="demo_salon",
                current_goal="booking",
                memory_profile=memory_profile,
                memory_summary=(
                    "user: На завтра в 18:00 есть время? assistant: На какую услугу "
                    "хотите записаться?"
                ),
            )

        assert result["compact_input_used"] is False
        assert result["focused_owner_contract_used"] is True
        assert result["compact_retry_used"] is False
        assert len(provider.system_prompt_lengths) == 1

    def test_route_llm_policy_core_uses_slot_state_datetime_for_missing_service_master_interrupt(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_COMPACT_FIRST_ATTEMPT",
            True,
        )
        monkeypatch.setattr(
            "app.services.intent_service._policy_core_resolve_current_message_service_hint",
            lambda **_kwargs: "маникюр",
        )
        monkeypatch.setattr(
            "app.services.intent_service._policy_core_current_message_has_master_query_signal",
            lambda *_args, **_kwargs: True,
        )

        valid_payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["master"],
            "slots": {"service": "маникюр", "datetime": "11 мая в 12:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.62,
            "reason": "master_interrupt_uses_slot_state_datetime_carryover",
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "context.message_grounding_hints.service",
                }
            },
            "subject_kind": "service",
            "capability": "master",
            "temporal_scope": "specific_time",
            "alternate_datetime": "11 мая в 12:00",
            "resolution_mode": "policy_fact",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
            result = route_llm_policy_core(
                "Кто делает маникюр?",
                client_slug="demo_salon",
                current_goal="booking",
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "reason": "collect:service",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "contract_version": "semantic_contract.v1",
                        "resolution_mode": "clarify_missing_subject",
                        "subject_kind": "general",
                        "temporal_scope": "specific_time",
                    },
                    "slot_state": {"datetime": "11 мая в 12:00"},
                },
            )

        assert result["ok"] is True
        assert result["focused_interrupt_variant"] == "master_query"
        assert result["compact_input_used"] is False
        assert result["focused_owner_contract_used"] is True
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        assert kwargs["response_format"] == {"type": "json_object"}
        forced_fields = json.loads(kwargs["messages"][1]["content"])["focus_contract"]["forced_fields"]
        assert forced_fields["alternate_datetime"] == "11 мая в 12:00"
        assert forced_fields["pending_question_act"] == "fill_requested_slot"
        assert forced_fields["pending_question_target"] == "time"
        assert forced_fields["active_question_relation"] == "generic_info_interrupt"

    def test_route_llm_policy_core_uses_strict_response_format_for_master_interrupt_progression(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        valid_payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["master"],
            "slots": {"service": "маникюр", "datetime": "на завтра в 18:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.62,
            "reason": "master_interrupt_for_grounded_service_and_name_progression",
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "context.message_grounding_hints.service",
                }
            },
            "subject_kind": "service",
            "capability": "master",
            "temporal_scope": "specific_time",
            "alternate_datetime": "на завтра в 18:00",
            "resolution_mode": "policy_fact",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
            result = route_llm_policy_core(
                "Кто делает маникюр?",
                client_slug="demo_salon",
                current_goal="booking",
                memory_summary=(
                    "user: На завтра в 18:00 есть время? assistant: На какую услугу "
                    "хотите записаться?"
                ),
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "reason": "collect:service",
                    },
                    "semantic_contract": {
                        "alternate_datetime": "на завтра в 18:00",
                        "capability": "bookability",
                        "contract_version": "semantic_contract.v1",
                        "resolution_mode": "clarify_missing_subject",
                        "subject_kind": "general",
                        "temporal_scope": "specific_time",
                    },
                    "slot_state": {"datetime": "на завтра в 18:00"},
                },
            )

        assert result["ok"] is True
        assert result["compact_input_used"] is False
        assert result["focused_owner_contract_used"] is True
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        assert kwargs["max_tokens"] == intent_service_module.POLICY_CORE_GPT5_FOCUSED_SAFE_MAX_TOKENS
        assert kwargs["response_format"] == {"type": "json_object"}
        forced_fields = json.loads(kwargs["messages"][1]["content"])["focus_contract"]["forced_fields"]
        assert forced_fields["intent"] == "master_query"
        assert forced_fields["tool_action_hint"] == "info"
        assert forced_fields["goal"] == "booking"
        assert forced_fields["alternate_datetime"] == "на завтра в 18:00"
        assert forced_fields["pending_question_act"] == "fill_requested_slot"
        assert forced_fields["pending_question_target"] == "time"
        assert forced_fields["active_question_relation"] == "generic_info_interrupt"
        assert forced_fields["pack_refs"] == ["master"]
        assert forced_fields["open_questions"] == ["name"]

    def test_master_missing_service_runtime_contract_failure_fails_closed_under_focused_contract(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_COMPACT_FIRST_ATTEMPT",
            True,
        )
        monkeypatch.setattr(
            "app.services.intent_service._policy_core_resolve_current_message_service_hint",
            lambda **_kwargs: "маникюр",
        )

        invalid_payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["master"],
            "slots": {"service": "маникюр", "datetime": None, "name": None, "phone": None},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.61,
            "reason": "user_service_grounded_master_query_interrupt_advances_booking_to_name",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message_grounding_hints.service",
                }
            },
            "subject_kind": "service",
            "capability": "master",
            "temporal_scope": "specific_time",
            "resolution_mode": "policy_fact",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }
        valid_payload = {
            **invalid_payload,
            "slots": {"service": "маникюр", "datetime": "на завтра в 18:00"},
            "goal": "booking",
            "alternate_datetime": "на завтра в 18:00",
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(json.dumps(invalid_payload)),
                DummyResponse(json.dumps(valid_payload)),
            ]
            result = route_llm_policy_core(
                "Кто делает маникюр?",
                client_slug="demo_salon",
                current_goal="booking",
                memory_summary=(
                    "user: На завтра в 18:00 есть время? assistant: На какую услугу "
                    "хотите записаться?"
                ),
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "reason": "collect:service",
                    },
                    "semantic_contract": {
                        "alternate_datetime": "на завтра в 18:00",
                        "capability": "bookability",
                        "contract_version": "semantic_contract.v1",
                        "resolution_mode": "clarify_missing_subject",
                        "subject_kind": "general",
                        "temporal_scope": "specific_time",
                    },
                    "slot_state": {"datetime": "на завтра в 18:00"},
                },
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert result["compact_input_used"] is False
        assert result["compact_retry_used"] is False
        assert result["focused_owner_contract_used"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert mock_llm.return_value.generate.call_count == 1
        first_kwargs = mock_llm.return_value.generate.call_args_list[0].kwargs
        assert "LLM Policy Core Focused Contract" in first_kwargs["messages"][0]["content"]

    def test_route_llm_policy_core_uses_strict_response_format_for_booking_commit_after_name_fill(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        valid_payload = {
            "intent": "booking",
            "action": "fact",
            "tool_action_hint": "calendar.book_slot",
            "pack_refs": [],
            "slots": {
                "service": "маникюр",
                "datetime": "на завтра в 18:00",
                "name": "Амина",
                "phone": "+77011234567",
            },
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.79,
            "reason": "user_name_provided_to_fill_requested_slot_and_datetime_already_carried",
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "customer": {
                    "value": "Амина",
                    "entity_id": None,
                    "entity_type": "customer",
                    "source_ref": "message",
                },
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "на завтра в 18:00",
            "resolution_mode": "live_calendar",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
            result = route_llm_policy_core(
                "Меня зовут Амина, телефон +77011234567",
                client_slug="demo_salon",
                current_goal="booking",
                memory_summary=(
                    "user: На завтра в 18:00 есть время? assistant: На какую услугу "
                    "хотите записаться? user: Кто делает маникюр? assistant: Как вас зовут?"
                ),
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                        "pending_question_act": "fill_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "generic_info_interrupt",
                    },
                    "semantic_contract": {
                        "alternate_datetime": "на завтра в 18:00",
                        "capability": "bookability",
                        "contract_version": "semantic_contract.v1",
                        "resolution_mode": "policy_fact",
                        "subject_kind": "service",
                        "temporal_scope": "specific_time",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                    "slot_state": {
                        "service": "маникюр",
                        "datetime": "на завтра в 18:00",
                    },
                },
            )

        assert result["ok"] is True
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        assert kwargs["response_format"] == {"type": "json_object"}
        forced_fields = json.loads(kwargs["messages"][1]["content"])["focus_contract"]["forced_fields"]
        assert forced_fields["intent"] == "booking"
        assert forced_fields["action"] == "fact"
        assert forced_fields["tool_action_hint"] == "calendar.book_slot"
        assert forced_fields["goal"] == "booking"
        assert forced_fields["subject_kind"] == "booking"
        assert forced_fields["capability"] == "bookability"
        assert forced_fields["alternate_datetime"] == "на завтра в 18:00"
        assert forced_fields["resolution_mode"] == "live_calendar"
        assert forced_fields["open_questions"] == []
        assert forced_fields["expected_reply_type"] is None
        assert forced_fields["next_question"] is None
        assert forced_fields["pending_question_act"] is None
        assert forced_fields["pending_question_target"] is None
        assert forced_fields["active_question_relation"] is None
        assert forced_fields["slots"]["name"] == "Амина"
        assert forced_fields["slots"]["phone"] == "+77011234567"

    def test_route_llm_policy_core_collects_phone_for_bare_name_after_datetime(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        valid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {
                "service": "Маникюр",
                "datetime": "8 мая в 17:00",
                "name": "Амина",
            },
            "expected_reply_type": "phone",
            "next_question": "phone",
            "open_questions": ["phone"],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.79,
            "reason": "active_booking_name_fill_requires_contact_phone",
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "customer": {
                    "value": "Амина",
                    "entity_type": "customer",
                    "source_ref": "message",
                },
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "8 мая в 17:00",
            "resolution_mode": "direct",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "phone",
            "active_question_relation": "fill_requested_slot",
            "resolver_id": None,
            "resolver_version": None,
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
            result = route_llm_policy_core(
                "Амина",
                client_slug="demo_salon",
                current_goal="booking",
                memory_summary=(
                    "user: На 8 мая в 17:00 есть время? assistant: На какую услугу "
                    "хотите записаться? user: Кто делает маникюр? assistant: Как вас зовут?"
                ),
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                        "pending_question_act": "fill_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "generic_info_interrupt",
                    },
                    "semantic_contract": {
                        "alternate_datetime": "8 мая в 17:00",
                        "capability": "master",
                        "contract_version": "semantic_contract.v1",
                        "resolution_mode": "policy_fact",
                        "subject_kind": "service",
                        "temporal_scope": "specific_time",
                        "referents": {
                            "service": {
                                "value": "Маникюр",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                    "slot_state": {
                        "service": "Маникюр",
                        "datetime": "8 мая в 17:00",
                    },
                },
            )

        assert result["ok"] is True
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        assert kwargs["response_format"] == {"type": "json_object"}
        forced_fields = json.loads(kwargs["messages"][1]["content"])["focus_contract"]["forced_fields"]
        assert forced_fields["intent"] == "booking"
        assert forced_fields["action"] == "collect"
        assert forced_fields["tool_action_hint"] == "collect"
        assert forced_fields["goal"] == "booking"
        assert forced_fields["subject_kind"] == "booking"
        assert forced_fields["alternate_datetime"] == "8 мая в 17:00"
        assert forced_fields["expected_reply_type"] == "phone"
        assert forced_fields["next_question"] == "phone"
        assert forced_fields["pending_question_act"] == "fill_requested_slot"
        assert forced_fields["pending_question_target"] == "phone"
        assert forced_fields["slots"]["name"] == "Амина"

    @pytest.mark.parametrize(
        ("message", "expected_head_intent"),
        [
            ("Есть ли акции на маникюр?", "promotions"),
            ("Сколько длится маникюр?", "duration"),
            ("Кто делает маникюр?", "master_query"),
        ],
    )
    def test_resolve_missing_service_grounded_fact_interrupt_variant(
        self,
        monkeypatch,
        message,
        expected_head_intent,
    ):
        memory_profile = {
            "active_goal": "booking",
            "pending_question_contract": {
                "expected_reply_type": "service_choice",
                "next_question": "service",
                "open_questions": ["service"],
            },
            "semantic_contract": {
                "alternate_datetime": "на завтра в 18:00",
                "capability": "bookability",
                "contract_version": "semantic_contract.v1",
                "resolution_mode": "clarify_missing_subject",
                "subject_kind": "general",
                "temporal_scope": "specific_time",
            },
            "slot_state": {"datetime": "на завтра в 18:00"},
        }

        monkeypatch.setattr(
            "app.services.intent_service._policy_core_resolve_current_message_service_hint",
            lambda **_kwargs: "маникюр",
        )
        class FakePackRuntime:
            @staticmethod
            def has_duration_signal(normalized_message, *, message=None):
                del normalized_message
                return "дл" in (message or "").casefold()

            @staticmethod
            def has_price_signal(normalized_message, *, message=None):
                del normalized_message
                return "сколько стоит" in (message or "").casefold()

            @staticmethod
            def has_master_signal(message):
                return "кто делает" in (message or "").casefold()

        monkeypatch.setattr(
            "app.services.pack_runtime_service.get_pack_runtime",
            lambda _client_slug: FakePackRuntime(),
        )

        variant = _policy_core_resolve_missing_service_grounded_fact_interrupt_variant(
            memory_profile,
            current_message=message,
            context_payload={"message_grounding_hints": {"service": "маникюр"}},
            client_slug="demo_salon",
        )

        assert variant is not None
        assert variant.head_intent == expected_head_intent

    def test_route_llm_policy_core_narrows_owner_envelope_for_missing_service_promotions_interrupt(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            "app.services.intent_service._policy_core_resolve_current_message_service_hint",
            lambda **_kwargs: "маникюр",
        )

        valid_payload = {
            "intent": "promotions",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["promotions"],
            "slots": {"service": "маникюр", "datetime": "на завтра в 18:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.77,
            "reason": "promotions_interrupt_for_grounded_service_manicure_and_advance_booking_to_name",
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "context.message_grounding_hints.service",
                }
            },
            "subject_kind": "service",
            "capability": "promotions",
            "temporal_scope": "specific_time",
            "alternate_datetime": "на завтра в 18:00",
            "resolution_mode": "policy_fact",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
            result = route_llm_policy_core(
                "Есть ли акции на маникюр?",
                client_slug="demo_salon",
                current_goal="booking",
                memory_summary=(
                    "user: На завтра в 18:00 есть время? assistant: На какую услугу "
                    "хотите записаться?"
                ),
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "reason": "collect:service",
                    },
                    "semantic_contract": {
                        "alternate_datetime": "на завтра в 18:00",
                        "capability": "bookability",
                        "contract_version": "semantic_contract.v1",
                        "resolution_mode": "clarify_missing_subject",
                        "subject_kind": "general",
                        "temporal_scope": "specific_time",
                    },
                    "slot_state": {"datetime": "на завтра в 18:00"},
                },
            )

        assert result["ok"] is True
        assert result["compact_input_used"] is False
        assert result["focused_interrupt_variant"] == "promotions"
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        policy_input = json.loads(kwargs["messages"][1]["content"])
        assert policy_input["allowed"]["info_refs"] == ["promotions"]
        assert policy_input["allowed"]["consult_refs"] == []
        assert policy_input["allowed"]["tool_actions"] == [
            "catalog.service_query",
            "collect",
            "handoff",
        ]
        assert "consult_cards" not in policy_input.get("context", {})
        assert policy_input["context"]["message_grounding_hints"]["service"] == "маникюр"

    def test_route_llm_policy_core_derives_master_interrupt_service_hint_from_services_catalog_runtime_truth(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        runtime_truth = RuntimeTruth(
            truth={
                "services_catalog": {
                    "services": [
                        {
                            "name": "Маникюр",
                            "aliases": [
                                "маникюр",
                                "аппаратный маникюр",
                            ],
                            "quick_price_key": "manicure",
                        }
                    ]
                }
            },
            client_slug="demo_salon",
            branch_id=uuid4(),
            source="test_intent",
            allow_fallback=False,
        )
        valid_payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["master"],
            "slots": {"service": "маникюр", "datetime": "на завтра в 18:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.77,
            "reason": "master_interrupt_for_grounded_service_manicure_and_advance_booking_to_name",
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "context.message_grounding_hints.service",
                }
            },
            "subject_kind": "service",
            "capability": "master",
            "temporal_scope": "specific_time",
            "alternate_datetime": "на завтра в 18:00",
            "resolution_mode": "policy_fact",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }

        with use_runtime_truth_override(runtime_truth):
            with patch("app.services.intent_service.get_llm_provider") as mock_llm:
                mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
                result = route_llm_policy_core(
                    "Кто делает маникюр?",
                    client_slug="demo_salon",
                    current_goal="booking",
                    memory_summary=(
                        "user: На завтра в 18:00 есть время? assistant: На какую услугу "
                        "хотите записаться?"
                    ),
                    memory_profile={
                        "active_goal": "booking",
                        "pending_question_contract": {
                            "expected_reply_type": "service_choice",
                            "next_question": "service",
                            "open_questions": ["service"],
                            "reason": "collect:service",
                        },
                        "semantic_contract": {
                            "alternate_datetime": "на завтра в 18:00",
                            "capability": "bookability",
                            "contract_version": "semantic_contract.v1",
                            "resolution_mode": "clarify_missing_subject",
                            "subject_kind": "general",
                            "temporal_scope": "specific_time",
                        },
                        "slot_state": {"datetime": "на завтра в 18:00"},
                    },
                )

        assert result["ok"] is True
        assert result["focused_interrupt_variant"] == "master_query"
        kwargs = mock_llm.return_value.generate.call_args.kwargs
        policy_input = json.loads(kwargs["messages"][1]["content"])
        assert policy_input["allowed"]["info_refs"] == ["master"]
        assert any(
            card.get("id") == "manicure"
            and any(item.casefold() == "маникюр" for item in list(card.get("includes") or []))
            for card in policy_input["context"]["service_cards"]
        )
        assert policy_input["context"]["message_grounding_hints"]["service"].casefold() == "маникюр"

    def test_route_llm_policy_core_blocks_compact_first_for_booking_manage_followup(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(
            intent_service_module,
            "POLICY_CORE_COMPACT_FIRST_ATTEMPT",
            True,
        )

        valid_payload = {
            "intent": "check_booking",
            "action": "fact",
            "tool_action_hint": "calendar.get_booking",
            "pack_refs": None,
            "slots": {"service": None, "datetime": None, "name": None, "phone": None},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.74,
            "reason": "Пользователь просит проверить запись, нужен поиск по имени клиента.",
            "goal": "booking",
            "entity_refs": None,
            "referents": {},
            "subject_kind": "booking",
            "capability": "booking_manage",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "direct",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }

        memory_profile = {
            "pending_question_contract": {
                "expected_reply_type": "name",
                "next_question": "name",
                "open_questions": ["name"],
                "reason": "lookup_by_name",
            },
            "semantic_contract": {
                "capability": "booking_manage",
                "contract_version": "semantic_contract.v1",
                "resolution_mode": "direct",
                "subject_kind": "booking",
                "temporal_scope": "none",
            },
        }

        class BookingManageProvider:
            def __init__(self) -> None:
                self.system_prompt_lengths: list[int] = []

            def generate(self, *, messages, **_kwargs):
                self.system_prompt_lengths.append(len(messages[0]["content"]))
                return DummyResponse(json.dumps(valid_payload))

        provider = BookingManageProvider()
        with patch("app.services.intent_service.get_llm_provider", return_value=provider):
            result = route_llm_policy_core(
                "На завтра в 18:00.",
                client_slug="demo_salon",
                current_goal="booking",
                memory_profile=memory_profile,
                memory_summary="user: Проверьте мою запись. assistant: Как вас зовут?",
            )

        assert result["compact_input_used"] is False
        assert result["compact_retry_used"] is False
        assert len(provider.system_prompt_lengths) == 1

    def test_policy_core_generated_contract_boundary_templates_cover_mixed_booking_envelope(self):
        assert {
            "mixed_first_turn_location_service_fact_scope_boundary",
            "mixed_first_turn_location_service_fact_booking_followup_boundary",
            "mixed_first_turn_hours_location_booking_followup_boundary",
            "mixed_first_turn_hours_location_fact_scope_boundary",
            "mixed_first_turn_hours_service_fact_scope_boundary",
            "mixed_first_turn_hours_service_booking_followup_boundary",
            "mixed_first_turn_hours_location_service_fact_scope_boundary",
            "mixed_first_turn_service_fact_booking_side_precedence_boundary",
            "service_query_multifact_scope_boundary",
            "service_query_multifact_booking_followup_boundary",
            "mixed_first_turn_promotions_precedence_fact_scope_boundary",
            "promotions_booking_followup_boundary",
            "promotions_location_booking_followup_boundary",
            "promotions_grounded_service_booking_followup_boundary",
        } <= policy_core_generated_contract_boundary_payload_template_ids()

    def test_policy_core_generated_contract_boundary_template_renders_dynamic_lists_and_followup(self):
        payload = render_policy_core_generated_contract_boundary_payload_template(
            "promotions_grounded_service_booking_followup_boundary",
            language="ru",
            confidence=0.77,
            reason="standalone_promotions_head_with_grounded_service_booking_request",
            pack_refs=["promotions", "location", "contact"],
            slots={"service": "маникюр"},
            referents={
                "service": {
                    "value": "маникюр",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
        )

        assert payload["intent"] == "promotions"
        assert payload["pack_refs"] == ["promotions", "location", "contact"]
        assert payload["expected_reply_type"] == "time"
        assert payload["next_question"] == "datetime"
        assert payload["open_questions"] == ["datetime"]
        assert payload["pending_question_act"] == "ask_about_requested_slot"
        assert payload["slots"] == {"service": "маникюр"}
        assert payload["referents"]["service"]["source_ref"] == "user_text"

    def test_policy_core_compact_prompt_mixed_first_turn_fact_scope_preserves_hours_and_services_overview(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "asks both working hours and another service fact" in prompt
        assert "without grounding a concrete service" in prompt
        assert "tool_action_hint=info" in prompt
        assert "pack refs: [hours, services_overview]" in prompt
        assert "[hours, pricing] for" in prompt
        assert "[hours, duration] for duration" in prompt
        assert "[hours, promotions]" in prompt
        assert "[hours, promotions, contact]" in prompt
        assert "[hours, location, promotions]" in prompt
        assert "[hours, location, promotions, contact]" in prompt
        assert "subject_kind=general" in prompt
        assert "slots.service / referents.service" in prompt
        assert "expected_reply_type=service_choice" in prompt
        assert "services_overview is allowed only when the current message explicitly asks service" in prompt
        assert 'Forbidden: "Вы сегодня работаете, где вы' in prompt
        assert 'находитесь и сколько стоит маникюр?" -> [hours, location, pricing,' in prompt

    def test_policy_core_compact_prompt_location_service_fact_scope_preserves_location_head_intent(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "asks about location/address" in prompt
        assert "intent=location" in prompt
        assert "[location, pricing, duration]" in prompt
        assert "[location, master]" in prompt
        assert "[location, pricing, master]" in prompt
        assert "appears later than pricing / duration / master in surface order" in prompt
        assert "services_overview is allowed only when the current" in prompt
        assert "plain location + pricing/duration/master" in prompt
        assert "Do NOT invent hours" in prompt
        assert "switch to booking collect" in prompt

    def test_policy_core_compact_prompt_location_service_booking_followup_preserves_location_head_intent(
        self,
    ):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "also adds booking as a side request" in prompt
        assert "goal=booking" in prompt
        assert "[location, pricing]" in prompt
        assert "[location, duration]" in prompt
        assert "expected_reply_type=time" in prompt
        assert "Do NOT collapse this family to fact-only" in prompt
        assert "services_overview without an explicit service-presence question" in prompt

    def test_policy_core_compact_prompt_service_fact_head_beats_temporal_side_booking(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "asks for a grounded service fact and only adds" in prompt
        assert "intent=pricing or" in prompt
        assert "pack_refs=[pricing]" in prompt
        assert "goal=booking" in prompt
        assert "expected_reply_type=time" in prompt
        assert "calendar.book_slot" in prompt
        assert "fact-only reply without booking follow-up" in prompt

    def test_policy_core_compact_prompt_hours_service_booking_followup_preserves_hours_head_intent(
        self,
    ):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "asks working hours and a grounded" in prompt
        assert "non-promotions service fact" in prompt
        assert "goal=booking" in prompt
        assert "[hours, pricing]" in prompt
        assert "[hours, duration]" in prompt
        assert "expected_reply_type=time" in prompt
        assert "Do NOT collapse the turn to pricing-only" in prompt

    def test_policy_core_compact_prompt_hours_location_booking_followup_preserves_combined_scope(
        self,
    ):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "explicitly asks working hours, location/address, and" in prompt
        assert "also asks to book while no concrete service is grounded" in prompt
        assert "exact pack_refs=[hours, location]" in prompt
        assert "goal=booking" in prompt
        assert "expected_reply_type=service_choice" in prompt
        assert "resolution_mode=policy_fact" in prompt
        assert "intent=booking / action=collect / capability=bookability" in prompt
        assert "collapse the fact scope to [location]" in prompt
        assert "hours/location facts only" in prompt

    def test_policy_core_compact_prompt_service_query_multifact_preserves_full_scope(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "multiple fact families" in prompt
        assert "pack_refs=[pricing," in prompt
        assert "duration]" in prompt
        assert "Do NOT answer only" in prompt

    def test_policy_core_compact_prompt_service_query_multifact_booking_followup_preserves_progression(
        self,
    ):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "multiple grounded service fact families" in prompt
        assert "booking is only a side request with a temporal clue" in prompt
        assert "[master, contact]" in prompt
        assert "goal=booking" in prompt
        assert "expected_reply_type=time" in prompt
        assert "Explicit contact or parking side asks stay inside the same pure" in prompt
        assert "do NOT clear booking follow-up" in prompt

    def test_policy_core_compact_prompt_mixed_first_turn_promotions_precedence_over_side_asks(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "asks about promotions/discounts and also adds" in prompt
        assert "promotions/discounts is the only" in prompt
        assert "allowed head intent" in prompt
        assert "Do NOT use intent=booking" in prompt
        assert "intent=location" in prompt
        assert "intent=pricing" in prompt
        assert "intent=consult" in prompt
        assert "pack_refs=[promotions, location]" in prompt
        assert "subject_kind=general" in prompt
        assert "Do NOT answer only location/address" in prompt

    def test_policy_core_compact_prompt_promotions_location_booking_preserves_service_followup(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "address/location" in prompt
        assert "pack_refs=[promotions, location]" in prompt
        assert "goal=booking" in prompt
        assert "expected_reply_type=service_choice" in prompt
        assert "promotions +" in prompt
        assert "location only" in prompt

    def test_policy_core_compact_prompt_promotions_booking_preserves_service_followup(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "asks about promotions/discounts and also asks to" in prompt
        assert "pack_refs=[promotions]" in prompt
        assert "goal=booking" in prompt
        assert "expected_reply_type=service_choice" in prompt
        assert "reply with promotions only" in prompt

    def test_policy_core_compact_prompt_promotions_grounded_service_booking_preserves_time_followup(self):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "already grounds the concrete service" in prompt
        assert "pack_refs=[promotions]" in prompt
        assert "subject_kind=service" in prompt
        assert "expected_reply_type=time" in prompt
        assert "next_question=datetime" in prompt
        assert "pending_question_act=ask_about_requested_slot" in prompt
        assert "open_questions=[service] once the service is already grounded" in prompt
        assert "ask for the service again" in prompt

    def test_policy_core_compact_prompt_promotions_grounded_service_location_booking_preserves_time_followup(
        self,
    ):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "already grounds the concrete service" in prompt
        assert "pack_refs=[promotions, location]" in prompt
        assert "expected_reply_type=time" in prompt
        assert "next_question=datetime" in prompt
        assert "drop explicit location/address" in prompt

    def test_policy_core_compact_prompt_promotions_grounded_service_contact_booking_preserves_time_followup(
        self,
    ):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "pack_refs=[promotions, contact]" in prompt
        assert "expected_reply_type=time" in prompt
        assert "next_question=datetime" in prompt
        assert "address/location/contact/parking" in prompt

    def test_policy_core_compact_prompt_promotions_grounded_service_location_contact_booking_preserves_time_followup(
        self,
    ):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "promotions, location, contact" in prompt
        assert "do NOT keep pricing or" in prompt
        assert "Do NOT leave any of those follow-up" in prompt
        assert "location-head/service-fact override" in prompt
        assert "expected_reply_type=time" in prompt

    def test_policy_core_detects_promotions_plus_location_scope(self):
        assert _policy_core_current_message_promotions_location_pack_refs(
            "Есть акции и где вы находитесь?",
        ) == ["promotions", "location"]

    def test_policy_core_context_snapshot_mixed_first_turn_fact_scope_allows_services_overview(self):
        snapshot = build_policy_core_context_snapshot(
            client_slug="demo_salon",
            info_refs=None,
            consult_refs=None,
        )
        allowed_payload = snapshot.as_allowed_payload()

        assert "services_overview" in allowed_payload["info_refs"]

    def test_policy_core_prompt_preserves_promotions_interrupt_during_booking_continuity(self):
        prompt = _load_policy_core_prompt()

        assert '"Есть ли акции?"' in prompt
        assert '`intent="promotions"`' in prompt
        assert '`pack_refs=["promotions"]`' in prompt
        assert '`capability="promotions"`' in prompt
        assert 'Forbidden: `pack_refs=["pricing"]`' in prompt
        assert 'silently dropping carried `alternate_datetime`' in prompt
        assert '`active_question_relation="generic_info_interrupt"`' in prompt
        assert "carried `temporal_scope`" in prompt
        assert '`temporal_scope="day"`' in prompt
        assert 'carried `alternate_datetime="на завтра в 18:00"` + `"Есть ли акции на маникюр?"`' in prompt
        assert '`pending_question_act="fill_requested_slot"`' in prompt
        assert 'standalone fact+booking follow-up rules ниже' in prompt
        assert 'а НЕ `ask_about_requested_slot`' in prompt

    def test_policy_core_compact_prompt_keeps_relative_exact_datetime_promotions_progression_example(
        self,
    ):
        prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert 'alternate_datetime="на завтра в 18:00" + "Есть ли акции на маникюр?"' in prompt
        assert "intent=promotions" in prompt
        assert "expected_reply_type=name" in prompt
        assert "pending_question_act=fill_requested_slot" in prompt

    def test_policy_core_prompt_initial_booking_prompt_keeps_requested_slot_contract(self):
        prompt = _load_policy_core_prompt()

        assert '"Я хочу записаться на маникюр."' in prompt
        assert "это canonical `ask_about_requested_slot(time)`" in prompt
        assert "generic first-booking rule применяется только когда текущий message сам НЕ grounded partial/exact temporal clue" in prompt
        assert "используй более узкий canonical `slot_constraint` / `fill_requested_slot` progression ниже" in prompt
        assert "Не оставляй `active_question_relation` пустым на первом booking prompt." in prompt
        assert "не используй `fill_requested_slot` для первого booking prompt" in prompt

    def test_policy_core_prompt_reschedule_without_reference_escalates(self):
        prompt = _load_policy_core_prompt()

        assert '"Я хочу изменить время записи."' in prompt
        assert '`action="handoff"`' in prompt
        assert '`tool_action_hint="handoff"`' in prompt
        assert '`capability="booking_manage"`' in prompt
        assert "не выполняй cancel/reschedule tool из customer chat" in prompt

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

    def test_policy_core_prompt_existing_booking_name_fill_stays_check_booking(self):
        prompt = _load_policy_core_prompt()

        assert "active existing-booking reference follow-up уже спрашивал имя клиента" in prompt
        assert 'оставайся на `intent="check_booking"`' in prompt
        assert '`expected_reply_type="time"`' in prompt
        assert '`next_question="datetime"`' in prompt
        assert 'Forbidden: переключаться в `intent="booking"` / `action="collect"`' in prompt
        assert "натуральный текст-подсказку в `next_question`" in prompt

    def test_policy_core_prompt_existing_booking_datetime_fill_completes_direct_lookup(self):
        prompt = _load_policy_core_prompt()

        assert '"На завтра в 18:00."' in prompt
        assert "current message сам даёт exact datetime surface" in prompt
        assert '`intent="check_booking"`' in prompt
        assert '`tool_action_hint="calendar.get_booking"`' in prompt
        assert '`capability="booking_manage"`' in prompt
        assert '`slots.datetime="<grounded datetime surface>"`' in prompt
        assert '`alternate_datetime="<grounded datetime surface>"`' in prompt
        assert "clear `expected_reply_type`, `next_question`, `open_questions`" in prompt
        assert "do NOT keep stale time-follow-up axes" in prompt

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
        assert '"К Айдане."' in prompt
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
        assert '"К Айдане."' in prompt
        assert '`subject_kind="specialist"`' in prompt
        assert '`resolution_mode="referent_followup"`' in prompt
        assert '`pending_question_act=null`' in prompt
        assert '`pending_question_target="specialist"`' in prompt
        assert '`active_question_relation="referent_followup"`' in prompt
        assert '`pending_question_act="slot_constraint"`' in prompt
        assert "обязательно должен переключиться c `time` на `specialist`" in prompt
        assert "Forbidden: generic `subject_kind=\"service\"`" in prompt

    def test_policy_core_prompt_generic_specialist_query_under_active_time_collect_is_info_interrupt(self):
        prompt = _load_policy_core_prompt()

        assert '"Какой специалист будет делать маникюр?"' in prompt
        assert '"Кто делает маникюр?"' in prompt
        assert '"Какой мастер работает с маникюром?"' in prompt
        assert 'Верни `intent="master_query"`, `action="fact"`, `tool_action_hint="info"`' in prompt
        assert '`pack_refs=["master"]`' in prompt
        assert '`active_question_relation="generic_info_interrupt"`' in prompt
        assert '`alternate_datetime="завтра вечером"`' in prompt
        assert '`temporal_scope="day"`' in prompt
        assert 'Forbidden: `action="collect"`' in prompt

    def test_policy_core_generated_booking_continuity_interrupt_contract_requires_non_null_temporal_scope(self):
        full_prompt = _load_policy_core_prompt()
        compact_prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert 'Carried `alternate_datetime` without matching non-null `temporal_scope` is invalid.' in full_prompt
        assert (
            'Concrete example: carried `alternate_datetime="завтра вечером"` + message '
            '`"Когда можно записаться?"` must keep that same `alternate_datetime` and stay '
            'on `ask_about_requested_slot`'
        ) in full_prompt
        assert (
            "Service-grounding interrupts under active booking continuity — `pricing`, "
            "`promotions`, `duration`, and `master_query` — must keep the exact current "
            "fact family"
        ) in full_prompt
        assert '`active_question_relation="generic_info_interrupt"`' in full_prompt
        assert (
            '`subject_kind="service"`, ground `slots.service` / `referents.service`, and '
            "switch the follow-up to `name`"
        ) in full_prompt
        assert "Carried alternate_datetime without matching non-null temporal_scope is invalid." in compact_prompt
        assert (
            'carried alternate_datetime="завтра вечером" + message "Когда можно записаться?" '
            "must keep the same alternate_datetime and stay on ask_about_requested_slot"
        ) in compact_prompt
        assert (
            "Service-grounding interrupts pricing / promotions / duration / master under "
            "active booking continuity must keep the exact current fact family"
        ) in compact_prompt
        assert "active_question_relation=generic_info_interrupt" in compact_prompt
        assert (
            "use subject_kind=service, ground slots.service / referents.service, and "
            "switch the follow-up to expected_reply_type=name"
        ) in compact_prompt

    def test_policy_core_generated_booking_continuity_interrupt_contract_covers_non_direct_followups(self):
        full_prompt = _load_policy_core_prompt()
        compact_prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert (
            'carried `pending_question_target="specialist"` + `"Сколько это длится?"` must keep '
            '`expected_reply_type="time"`, `next_question="datetime"`, '
            '`pending_question_target="specialist"`, and `active_question_relation="generic_info_interrupt"`'
        ) in full_prompt
        assert (
            'carried `expected_reply_type="service_choice"` + `"Есть ли парковка?"` must keep '
            '`expected_reply_type="service_choice"`, `next_question="service"`, '
            '`open_questions=["service"]`, `subject_kind="general"`, and '
            '`active_question_relation="generic_info_interrupt"`'
        ) in full_prompt
        assert '`slots.service` / `referents.service` empty' in full_prompt
        assert '"Где вы находитесь?"' in full_prompt
        assert '`pack_refs=["location"]`' in full_prompt
        assert '`subject_kind="general"`' in full_prompt
        assert 'active_question_relation="slot_constraint"' in full_prompt
        assert 'must NOT keep `active_question_relation="slot_constraint"` on the fact turn' in full_prompt
        assert (
            'Counterexample invalid: carried `alternate_datetime="на завтра в 18:00"` + '
            '`"Сколько длится маникюр?"`'
        ) in full_prompt
        assert (
            'must use `subject_kind="service"`, ground `slots.service` / '
            '`referents.service`, and switch the follow-up to `name`'
        ) in full_prompt
        assert '`expected_reply_type="time"`' in full_prompt
        assert (
            'carried pending_question_target=specialist + message "Сколько это длится?" '
            "must keep pending_question_target=specialist"
        ) in compact_prompt
        assert (
            'carried expected_reply_type=service_choice + message "Есть ли парковка?" '
            "must keep expected_reply_type=service_choice, next_question=service, "
            "open_questions=[service], subject_kind=general, "
            "active_question_relation=generic_info_interrupt"
        ) in compact_prompt
        assert "slots.service / referents.service stay empty" in compact_prompt
        assert '"Где вы находитесь?"' in compact_prompt
        assert "pack_refs=[location]" in compact_prompt
        assert "subject_kind=general" in compact_prompt
        assert "active_question_relation=slot_constraint" in compact_prompt
        assert '"Где вы находитесь?" -> active_question_relation=slot_constraint.' in compact_prompt
        assert (
            'Counterexample invalid: carried alternate_datetime="на завтра в 18:00" + '
            '"Сколько длится маникюр?"'
        ) in compact_prompt
        assert (
            "must use subject_kind=service, ground slots.service/referents.service, and "
            "switch the follow-up to name"
        ) in compact_prompt
        assert "expected_reply_type=time" in compact_prompt
        assert (
            'carried active media pending + resume `expected_reply_type="time"` + specialist carry '
            '+ `"Сколько это длится?"` must return the duration fact family with '
            '`expected_reply_type="time"`, `next_question="datetime"`, `open_questions=["datetime"]`, '
            '`pending_question_target="specialist"`, and `active_question_relation="generic_info_interrupt"`'
        ) in full_prompt
        assert (
            'active media pending + resume time/datetime + specialist carry + message "Сколько это длится?" '
            "must keep expected_reply_type=time, next_question=datetime, "
            "open_questions=[datetime], pending_question_target=specialist"
        ) in compact_prompt
        assert "media no longer owns the turn" in compact_prompt

    def test_policy_core_generated_booking_progression_contract_promotes_missing_service_fill_with_exact_datetime(self):
        full_prompt = _load_policy_core_prompt()
        compact_prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert (
            'service-only reply like `"Маникюр."` must advance directly to customer-name collect '
            "instead of reopening time"
        ) in full_prompt
        assert '`expected_reply_type="name"`' in full_prompt
        assert '`pending_question_act="fill_requested_slot"`' in full_prompt
        assert (
            'service-only reply like "Маникюр." must advance directly to name collect'
        ) in compact_prompt
        assert "expected_reply_type=name" in compact_prompt
        assert "pending_question_act=fill_requested_slot" in compact_prompt

    def test_policy_core_generated_booking_progression_contract_keeps_missing_service_exact_time_on_service_collect(
        self,
    ):
        full_prompt = _load_policy_core_prompt()
        compact_prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert '"На завтра в 18:00 есть время?"' in full_prompt
        assert '`slots.datetime="<grounded exact datetime surface>"`' in full_prompt
        assert '`alternate_datetime="<same exact surface>"`' in full_prompt
        assert '`temporal_scope="specific_time"`' in full_prompt
        assert '`expected_reply_type="service_choice"`' in full_prompt
        assert "do not widen this exact slot clue to `day` or `date_range`" in full_prompt.casefold()
        assert 'must NOT ground `slots.service="маникюр"`' in full_prompt
        assert 'do NOT output `subject_kind="booking"`' in full_prompt
        assert 'do NOT jump to `expected_reply_type="name"` or `expected_reply_type="time"`' in full_prompt
        assert '"На завтра в 18:00 есть время?"' in compact_prompt
        assert "slots.datetime=<grounded exact datetime surface>" in compact_prompt
        assert "alternate_datetime=<same exact surface>" in compact_prompt
        assert "temporal_scope=specific_time" in compact_prompt
        assert "expected_reply_type=service_choice" in compact_prompt
        assert "do not widen this exact slot clue to day or date_range" in compact_prompt.casefold()
        assert 'must not invent slots.service=маникюр' in compact_prompt
        assert 'do not emit subject_kind=booking, resolution_mode=direct' in compact_prompt
        assert 'expected_reply_type=name' in compact_prompt
        assert 'expected_reply_type=time' in compact_prompt

    def test_policy_core_generated_booking_progression_contract_promotes_service_grounding_fact_interrupt_to_name_collect(
        self,
    ):
        full_prompt = _load_policy_core_prompt()
        compact_prompt = load_policy_core_compact_prompt_snapshot().prompt_text

        assert "context.message_grounding_hints.service" in full_prompt
        for variant in iter_policy_core_booking_info_interrupt_variants(
            family="service_grounding_progression"
        ):
            assert f'"{variant.example_message}"' in full_prompt
        assert '"Меня зовут Амина."' in full_prompt
        assert '`tool_action_hint="calendar.book_slot"`' in full_prompt
        assert '`expected_reply_type="name"`' in full_prompt
        assert '`goal="booking"`' in full_prompt
        assert '`resolution_mode="policy_fact"`' in full_prompt
        assert '`pending_question_act="fill_requested_slot"`' in full_prompt
        assert '`pending_question_target="time"`' in full_prompt
        assert '`active_question_relation="generic_info_interrupt"`' in full_prompt
        assert 'null or empty values are invalid' in full_prompt.casefold()
        assert 'do not switch this fact interrupt to `resolution_mode="direct"`' in full_prompt.casefold()
        assert 'Do NOT keep `expected_reply_type="service_choice"`' in full_prompt
        assert "context.message_grounding_hints.service" in compact_prompt
        for variant in iter_policy_core_booking_info_interrupt_variants(
            family="service_grounding_progression"
        ):
            assert f'"{variant.example_message}"' in compact_prompt
        assert '"Меня зовут Амина."' in compact_prompt
        assert "tool_action_hint=calendar.book_slot" in compact_prompt
        assert "expected_reply_type=name" in compact_prompt
        assert "goal=booking" in compact_prompt
        assert "resolution_mode=policy_fact" in compact_prompt
        assert "pending_question_act=fill_requested_slot" in compact_prompt
        assert "pending_question_target=time" in compact_prompt
        assert "active_question_relation=generic_info_interrupt" in compact_prompt
        assert "null or empty values are invalid" in compact_prompt.casefold()
        assert "do not switch this fact interrupt to resolution_mode=direct" in compact_prompt.casefold()

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

    def test_policy_core_runtime_contract_repairs_mixed_first_turn_fact_scope(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "hours",
                "action": "fact",
                "tool_action_hint": "catalog.location",
                "pack_refs": ["hours"],
                "slots": {},
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.83,
                "reason": "user_asks_working_hours_and_service_is_manicure",
                "goal": "info",
                "entity_refs": [],
                "referents": {
                    "service": {
                        "value": "маникюр",
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "user_text",
                    }
                },
                "subject_kind": "service",
                "capability": "hours",
                "temporal_scope": "none",
                "alternate_datetime": None,
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
        assert _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile={},
            current_message="Здравствуйте! Вы сегодня работаете? Вы маникюром занимаетесь?",
            context_payload={"service_cards": [{"includes": ["маникюр", "педикюр"]}]},
            client_slug="demo_salon",
        ) == "llm_policy_core_error:mixed_first_turn_hours_service_fact_reclassification_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:mixed_first_turn_hours_service_fact_reclassification_required",
            normalized_memory_profile={},
            contract=contract,
            current_message="Здравствуйте! Вы сегодня работаете? Вы маникюром занимаетесь?",
            context_payload={"service_cards": [{"includes": ["маникюр", "педикюр"]}]},
            client_slug="demo_salon",
        )
        assert repair is not None
        assert '`intent="hours"`' in repair
        assert '`tool_action_hint="info"`' in repair
        assert '`pack_refs=["hours", "services_overview"]`' in repair
        assert '`subject_kind="service"`' in repair

    def test_policy_core_hours_service_fact_pack_refs_detect_noun_head_service_presence(self):
        message = "Вы сегодня работаете, какие услуги есть и сколько стоит маникюр?"
        standalone_multifact_message = "Сколько стоит маникюр и сколько длится маникюр?"
        combined_message = "Вы сегодня работаете, какие услуги есть, сколько стоит маникюр и где находитесь?"
        combined_price_without_presence_message = "Вы сегодня работаете, где вы находитесь и сколько стоит маникюр?"
        promotions_message = "Вы сегодня работаете, есть акции на маникюр и как с вами связаться?"
        promotions_location_message = "Вы сегодня работаете, есть акции на маникюр и где находитесь?"
        general_promotions_location_message = "Вы сегодня работаете, есть акции и где находитесь?"
        general_promotions_location_contact_message = "Вы сегодня работаете, есть акции, где находитесь и как с вами связаться?"

        assert _policy_core_current_message_has_service_presence_query(message) is True
        assert _policy_core_current_message_has_service_presence_query(
            combined_price_without_presence_message
        ) is False
        assert _policy_core_current_message_hours_service_fact_pack_refs(
            message,
            client_slug="demo_salon",
        ) == ["hours", "pricing", "services_overview"]
        assert _policy_core_current_message_hours_service_fact_pack_refs(
            promotions_message,
            client_slug="demo_salon",
        ) == ["hours", "promotions", "contact"]
        assert _policy_core_current_message_hours_service_fact_pack_refs(
            standalone_multifact_message,
            client_slug="demo_salon",
        ) is None
        assert _policy_core_current_message_service_multifact_pack_refs(
            message,
            client_slug="demo_salon",
        ) is None
        assert _policy_core_current_message_service_multifact_pack_refs(
            standalone_multifact_message,
            client_slug="demo_salon",
        ) == ["pricing", "duration"]
        assert set(
            _policy_core_current_message_hours_location_service_fact_pack_refs(
                combined_message,
                client_slug="demo_salon",
            )
            or []
        ) == {"hours", "location", "pricing", "services_overview"}
        assert set(
            _policy_core_current_message_hours_location_service_fact_pack_refs(
                combined_price_without_presence_message,
                client_slug="demo_salon",
            )
            or []
        ) == {"hours", "location", "pricing"}
        assert set(
            _policy_core_current_message_hours_location_service_fact_pack_refs(
                promotions_location_message,
                client_slug="demo_salon",
            )
            or []
        ) == {"hours", "location", "promotions"}
        assert _policy_core_current_message_hours_location_fact_pack_refs(
            "Вы сегодня работаете и где находитесь?",
            client_slug="demo_salon",
        ) == ["hours", "location"]
        assert _policy_core_current_message_hours_location_fact_pack_refs(
            general_promotions_location_message,
            client_slug="demo_salon",
        ) == ["hours", "location", "promotions"]
        assert _policy_core_current_message_hours_location_fact_pack_refs(
            general_promotions_location_contact_message,
            client_slug="demo_salon",
        ) == ["hours", "location", "promotions", "contact"]
        assert _policy_core_current_message_hours_location_fact_pack_refs(
            combined_message,
            client_slug="demo_salon",
        ) is None
        assert _policy_core_current_message_hours_location_booking_followup_pack_refs(
            "Вы сегодня работаете, где находитесь, хочу записаться.",
            client_slug="demo_salon",
        ) == ["hours", "location"]
        assert _policy_core_current_message_hours_location_booking_followup_pack_refs(
            "Вы сегодня работаете и где находитесь?",
            client_slug="demo_salon",
        ) is None

    def test_policy_core_runtime_contract_repair_instruction_preserves_general_hours_location_promotions_scope(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "hours",
                "action": "fact",
                "tool_action_hint": "info",
                "pack_refs": ["hours", "location"],
                "slots": {},
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.8,
                "reason": "user asks working hours, promotions, and location without concrete service",
                "goal": None,
                "entity_refs": [],
                "referents": {},
                "subject_kind": "general",
                "capability": "hours",
                "temporal_scope": "none",
                "alternate_datetime": None,
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
        assert _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile={},
            current_message="Вы сегодня работаете, есть акции и где находитесь?",
            context_payload=None,
            client_slug="demo_salon",
        ) == "llm_policy_core_error:mixed_first_turn_hours_location_fact_scope_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:mixed_first_turn_hours_location_fact_scope_required",
            normalized_memory_profile={},
            contract=contract,
            current_message="Вы сегодня работаете, есть акции и где находитесь?",
            context_payload=None,
            client_slug="demo_salon",
        )
        assert repair is not None
        assert '`pack_refs=["hours", "location", "promotions"]`' in repair
        assert "promotions/discounts" in repair
        assert '`subject_kind="general"`' in repair

    def test_policy_core_runtime_contract_repair_instruction_preserves_hours_location_booking_followup(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "hours",
                "action": "fact",
                "tool_action_hint": "info",
                "pack_refs": ["hours", "location"],
                "slots": {},
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.8,
                "reason": "user asks hours and location and also wants to book without naming service",
                "goal": None,
                "entity_refs": [],
                "referents": {},
                "subject_kind": "general",
                "capability": "hours",
                "temporal_scope": "none",
                "alternate_datetime": None,
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
        assert _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile={},
            current_message="Вы сегодня работаете, где вы находитесь, хочу записаться.",
            context_payload=None,
            client_slug="demo_salon",
        ) == "llm_policy_core_error:mixed_first_turn_hours_location_fact_scope_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:mixed_first_turn_hours_location_fact_scope_required",
            normalized_memory_profile={},
            contract=contract,
            current_message="Вы сегодня работаете, где вы находитесь, хочу записаться.",
            context_payload=None,
            client_slug="demo_salon",
        )

        assert repair is not None
        assert '`pack_refs=["hours", "location"]`' in repair
        assert '`goal="booking"`' in repair
        assert '`expected_reply_type="service_choice"`' in repair
        assert "Do NOT answer only with hours/location" in repair

    def test_policy_core_runtime_contract_repair_instruction_preserves_hours_promotions_contact_scope(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "hours",
                "action": "fact",
                "tool_action_hint": "info",
                "pack_refs": ["hours", "contact"],
                "slots": {"service": "маникюр"},
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.8,
                "reason": "user asks working hours, promotions, and contact for manicure",
                "goal": None,
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
                "capability": "hours",
                "temporal_scope": "none",
                "alternate_datetime": None,
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
        assert _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile={},
            current_message="Вы сегодня работаете, есть акции на маникюр и как с вами связаться?",
            context_payload=None,
            client_slug="demo_salon",
        ) == "llm_policy_core_error:mixed_first_turn_hours_service_fact_reclassification_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:mixed_first_turn_hours_service_fact_reclassification_required",
            normalized_memory_profile={},
            contract=contract,
            current_message="Вы сегодня работаете, есть акции на маникюр и как с вами связаться?",
            context_payload=None,
            client_slug="demo_salon",
        )
        assert repair is not None
        assert '`pack_refs=["hours", "promotions", "contact"]`' in repair
        assert '`subject_kind="service"`' in repair

    def test_policy_core_boundary_normalizes_hours_promotions_contact_service_grounding(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "hours",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["hours", "promotions", "contact"],
            "slots": {},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.62,
            "reason": "user asks about working hours + promotions on pedicure + how to contact; service specifics not grounded in provided context",
            "goal": None,
            "entity_refs": [],
            "referents": {},
            "subject_kind": "general",
            "capability": "hours",
            "temporal_scope": None,
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Вы сегодня работаете, есть акции на педикюр и как с вами связаться?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "hours"
        assert result["payload"]["semantic_slots"]["service"] == "педикюр"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "hours",
            "promotions",
            "contact",
        ]

    def test_policy_core_boundary_normalizes_hours_location_promotions_combined_scope(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "hours",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["hours", "promotions"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.74,
            "reason": "mixed_fact_hours_and_promotions_for_manicure",
            "goal": "service_facts",
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
            "capability": "hours",
            "temporal_scope": None,
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Вы сегодня работаете, есть акции на маникюр и где находитесь?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "hours"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "hours",
            "location",
            "promotions",
        ]

    def test_policy_core_boundary_normalizes_general_hours_location_promotions_scope(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "hours",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["hours", "location"],
            "slots": {},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.74,
            "reason": "mixed_fact_hours_location_without_promotions_scope",
            "goal": "info",
            "entity_refs": [],
            "referents": {},
            "subject_kind": "general",
            "capability": "hours",
            "temporal_scope": None,
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Вы сегодня работаете, есть акции и где находитесь?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "hours"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "general"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "hours",
            "location",
            "promotions",
        ]
        assert result["payload"].get("semantic_slots") in ({}, None)

    def test_policy_core_boundary_preserves_general_hours_location_promotions_contact_scope(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["hours", "promotions", "location", "contact"],
            "slots": {},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.74,
            "reason": "user_requests combined hours+promotions+location+contact facts",
            "goal": "info",
            "entity_refs": [],
            "referents": {},
            "subject_kind": "general",
            "capability": "hours",
            "temporal_scope": None,
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Вы сегодня работаете, есть акции, где находитесь и как с вами связаться?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "location"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "general"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "hours",
            "location",
            "promotions",
            "contact",
        ]

    def test_policy_core_runtime_contract_rejects_mixed_first_turn_hours_and_pricing_collect_when_service_is_named(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "hours",
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
                "confidence": 0.74,
                "reason": "user asks working hours and price for a service, but service is not grounded in memory",
                "goal": "info",
                "entity_refs": [],
                "referents": {},
                "subject_kind": "general",
                "capability": "bookability",
                "temporal_scope": "none",
                "alternate_datetime": None,
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
        assert _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile={},
            current_message="Здравствуйте! Вы сегодня работаете? Сколько стоит педикюр?",
            context_payload=None,
            client_slug="demo_salon",
        ) == "llm_policy_core_error:mixed_first_turn_hours_service_fact_reclassification_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:mixed_first_turn_hours_service_fact_reclassification_required",
            normalized_memory_profile={},
            contract=contract,
            current_message="Здравствуйте! Вы сегодня работаете? Сколько стоит педикюр?",
            context_payload=None,
            client_slug="demo_salon",
        )
        assert repair is not None
        assert '`action="fact"`' in repair
        assert '`pack_refs=["hours", "pricing"]`' in repair
        assert '`subject_kind="service"`' in repair

    def test_policy_core_runtime_contract_rejects_location_service_fact_side_booking_misroute_to_hours(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "hours",
                "action": "fact",
                "tool_action_hint": "info",
                "pack_refs": ["hours", "pricing"],
                "slots": {"service": "маникюр"},
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.77,
                "reason": "user asks for working hours plus price for manicure in same message",
                "goal": "info",
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
                "capability": "hours",
                "temporal_scope": "none",
                "alternate_datetime": None,
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
        assert _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile={},
            current_message="Сколько стоит маникюр, сколько длится, где находитесь и можно записаться?",
            context_payload={"service_cards": [{"includes": ["маникюр", "педикюр"]}]},
            client_slug="demo_salon",
        ) == "llm_policy_core_error:mixed_first_turn_location_service_fact_reclassification_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:mixed_first_turn_location_service_fact_reclassification_required",
            normalized_memory_profile={},
            contract=contract,
            current_message="Сколько стоит маникюр, сколько длится, где находитесь и можно записаться?",
            context_payload={"service_cards": [{"includes": ["маникюр", "педикюр"]}]},
            client_slug="demo_salon",
        )
        assert repair is not None
        assert '`intent="location"`' in repair
        assert '`tool_action_hint="info"`' in repair
        assert '`pack_refs=["location", "pricing", "duration"]`' in repair
        assert '`goal="booking"`' in repair
        assert '`expected_reply_type="time"`' in repair
        assert 'Do NOT switch this turn to `intent="hours"`' in repair

    def test_policy_core_runtime_contract_accepts_location_service_booking_followup(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "location",
                "action": "fact",
                "tool_action_hint": "info",
                "pack_refs": ["location", "duration"],
                "slots": {"service": "педикюр"},
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.79,
                "reason": "user asks location and pedicure duration, then adds booking as a side request",
                "goal": "booking",
                "entity_refs": [],
                "referents": {
                    "service": {
                        "value": "педикюр",
                        "entity_id": "svc:pedicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                },
                "subject_kind": "service",
                "capability": "location",
                "temporal_scope": "specific_time",
                "alternate_datetime": "завтра вечером",
                "resolution_mode": "policy_fact",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile={},
                current_message="Где вы находитесь и сколько длится педикюр, можно записаться завтра вечером?",
                context_payload={"service_cards": [{"includes": ["маникюр", "педикюр"]}]},
                client_slug="demo_salon",
            )
            is None
        )

    def test_policy_core_runtime_contract_accepts_location_service_booking_followup_with_implicit_temporal_side_ask(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "location",
                "action": "fact",
                "tool_action_hint": "info",
                "pack_refs": ["location", "duration"],
                "slots": {"service": "педикюр"},
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.74,
                "reason": "location_head_duration_fact_with_implicit_temporal_booking_side_request",
                "goal": "booking",
                "entity_refs": [],
                "referents": {
                    "service": {
                        "value": "педикюр",
                        "entity_id": "svc:pedicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                },
                "subject_kind": "service",
                "capability": "location",
                "temporal_scope": "day",
                "alternate_datetime": None,
                "resolution_mode": "policy_fact",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile={},
                current_message="Где вы находитесь и сколько длится педикюр, можно сегодня после 6?",
                context_payload={"service_cards": [{"includes": ["маникюр", "педикюр"]}]},
                client_slug="demo_salon",
            )
            is None
        )

    def test_policy_core_location_service_fact_pack_refs_detect_noun_head_service_presence(self):
        message = "Какие услуги у вас есть и сколько стоит маникюр и где находитесь?"
        parking_message = "Где вы находитесь, сколько стоит маникюр и есть парковка?"
        contact_message = "Где вы находитесь, сколько стоит маникюр и как с вами связаться?"
        master_contact_message = (
            "Где вы находитесь, сколько стоит маникюр, кто делает маникюр и как с вами связаться?"
        )

        assert _policy_core_current_message_has_service_presence_query(message) is True
        assert _policy_core_current_message_location_service_fact_pack_refs(
            message,
            client_slug="demo_salon",
        ) == ["location", "pricing", "services_overview"]
        assert _policy_core_current_message_location_service_fact_pack_refs(
            parking_message,
            client_slug="demo_salon",
        ) == ["location", "pricing", "parking"]
        assert _policy_core_current_message_location_service_fact_pack_refs(
            contact_message,
            client_slug="demo_salon",
        ) == ["location", "pricing", "contact"]
        assert _policy_core_current_message_location_service_fact_pack_refs(
            master_contact_message,
            client_slug="demo_salon",
        ) == ["location", "pricing", "master", "contact"]

    def test_policy_core_runtime_contract_rejects_service_fact_head_temporal_side_booking_misroute(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "fact",
                "tool_action_hint": "calendar.book_slot",
                "pack_refs": [],
                "slots": {"service": "педикюр"},
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.79,
                "reason": "user wants to know the price and asks if tomorrow at 6 works",
                "goal": "booking",
                "entity_refs": [],
                "referents": {
                    "service": {
                        "value": "педикюр",
                        "entity_id": "svc:pedicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                },
                "subject_kind": "service",
                "capability": "bookability",
                "temporal_scope": "day",
                "alternate_datetime": "завтра в 6",
                "resolution_mode": "live_calendar",
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
            normalized_memory_profile={},
            current_message="Сколько стоит педикюр и можно завтра в 6?",
            context_payload={"service_cards": [{"includes": ["педикюр", "маникюр"]}]},
            client_slug="demo_salon",
        ) == "llm_policy_core_error:mixed_first_turn_service_fact_booking_side_precedence_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:mixed_first_turn_service_fact_booking_side_precedence_required",
            normalized_memory_profile={},
            contract=contract,
            current_message="Сколько стоит педикюр и можно завтра в 6?",
            context_payload={"service_cards": [{"includes": ["педикюр", "маникюр"]}]},
            client_slug="demo_salon",
        )
        assert repair is not None
        assert '`intent="pricing"`' in repair
        assert '`tool_action_hint="catalog.service_query"`' in repair
        assert '`pack_refs=["pricing"]`' in repair
        assert '`goal="booking"`' in repair
        assert '`expected_reply_type="time"`' in repair
        assert 'Do NOT switch this turn to booking collect' in repair

    def test_policy_core_runtime_contract_accepts_service_fact_booking_followup(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "pricing",
                "action": "fact",
                "tool_action_hint": "catalog.service_query",
                "pack_refs": ["pricing"],
                "slots": {"service": "педикюр"},
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.79,
                "reason": "user wants to know the price and asks if tomorrow at 6 works",
                "goal": "booking",
                "entity_refs": [],
                "referents": {
                    "service": {
                        "value": "педикюр",
                        "entity_id": "svc:pedicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                },
                "subject_kind": "service",
                "capability": "pricing",
                "temporal_scope": "day",
                "alternate_datetime": "завтра в 6",
                "resolution_mode": "policy_fact",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile={},
                current_message="Сколько стоит педикюр и можно завтра в 6?",
                context_payload={"service_cards": [{"includes": ["педикюр", "маникюр"]}]},
                client_slug="demo_salon",
            )
            is None
        )

    def test_policy_core_runtime_contract_accepts_hours_service_booking_followup(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "hours",
                "action": "fact",
                "tool_action_hint": "info",
                "pack_refs": ["hours", "pricing"],
                "slots": {"service": "маникюр"},
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.74,
                "reason": "user asks hours and manicure pricing, then adds booking as a side request",
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
                "capability": "hours",
                "temporal_scope": "none",
                "alternate_datetime": None,
                "resolution_mode": "policy_fact",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile={},
                current_message="Вы сегодня работаете и сколько стоит маникюр, можно записаться на 7?",
                context_payload={"service_cards": [{"includes": ["маникюр", "педикюр"]}]},
                client_slug="demo_salon",
            )
            is None
        )

    def test_policy_core_runtime_contract_accepts_service_query_multifact_booking_followup(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "pricing",
                "action": "fact",
                "tool_action_hint": "catalog.service_query",
                "pack_refs": ["pricing", "duration"],
                "slots": {"service": "маникюр"},
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.72,
                "reason": "user_asks_pricing_and_duration_for_grounded_service_and_requests_booking_with_temporal_clue",
                "goal": "booking",
                "entity_refs": [],
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
                "temporal_scope": "specific_time",
                "alternate_datetime": "завтра вечером",
                "resolution_mode": "policy_fact",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile={},
                current_message="Сколько стоит маникюр и сколько длится, можно записаться завтра вечером?",
                context_payload={"service_cards": [{"includes": ["маникюр", "педикюр"]}]},
                client_slug="demo_salon",
            )
            is None
        )

    def test_policy_core_runtime_contract_accepts_master_contact_service_query_multifact_booking_followup(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "master_query",
                "action": "fact",
                "tool_action_hint": "catalog.service_query",
                "pack_refs": ["master", "contact"],
                "slots": {"service": "маникюр"},
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.71,
                "reason": "user_asks_who_performs_manicure_how_to_contact_and_requests_booking",
                "goal": "booking",
                "entity_refs": [],
                "referents": {
                    "service": {
                        "value": "маникюр",
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "message",
                    }
                },
                "subject_kind": "service",
                "capability": "master",
                "temporal_scope": "none",
                "alternate_datetime": None,
                "resolution_mode": "policy_fact",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile={},
                current_message="Кто делает маникюр и как с вами связаться, можно записаться?",
                context_payload={"service_cards": [{"includes": ["маникюр", "педикюр"]}]},
                client_slug="demo_salon",
            )
            is None
        )

    def test_sanitize_policy_core_payload_preserves_supported_service_query_multifact_pack_refs(self):
        payload, sanitized = _sanitize_policy_core_payload(
            {
                "intent": "pricing",
                "action": "fact",
                "tool_action_hint": "catalog.service_query",
                "pack_refs": ["duration", "pricing"],
                "slots": {"service": "маникюр"},
                "subject_kind": "service",
                "capability": "pricing",
                "temporal_scope": "none",
            }
        )

        assert sanitized is True
        assert payload["pack_refs"] == ["pricing", "duration"]

    def test_sanitize_policy_core_payload_normalizes_master_query_portfolio_capability(self):
        payload, sanitized = _sanitize_policy_core_payload(
            {
                "intent": "master_query",
                "action": "fact",
                "tool_action_hint": "info",
                "pack_refs": ["services_overview", "master", "contact"],
                "slots": {"service": "маникюр"},
                "subject_kind": "service",
                "capability": "portfolio",
                "temporal_scope": "none",
                "resolution_mode": "policy_fact",
            }
        )

        assert sanitized is True
        assert payload["capability"] == "master"

    def test_service_query_multifact_detects_master_services_and_parking_scope(self):
        assert _policy_core_current_message_service_multifact_pack_refs(
            "Какие услуги есть, кто делает маникюр и есть парковка?",
            client_slug="demo_salon",
        ) == ["master", "services_overview", "parking"]

    def test_policy_core_runtime_contract_rejects_service_query_multifact_collapse(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "pricing",
                "action": "fact",
                "tool_action_hint": "catalog.service_query",
                "pack_refs": ["pricing"],
                "slots": {"service": "маникюр"},
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.9,
                "reason": "user asks pricing and duration for grounded service маникюр",
                "goal": None,
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
                "alternate_datetime": None,
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
        assert _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile={},
            current_message="Сколько стоит маникюр и сколько длится маникюр?",
            context_payload={"service_cards": [{"includes": ["маникюр", "педикюр"]}]},
            client_slug="demo_salon",
        ) == "llm_policy_core_error:service_query_multifact_reclassification_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:service_query_multifact_reclassification_required",
            normalized_memory_profile={},
            contract=contract,
            current_message="Сколько стоит маникюр и сколько длится маникюр?",
            context_payload={"service_cards": [{"includes": ["маникюр", "педикюр"]}]},
            client_slug="demo_salon",
        )
        assert repair is not None
        assert '`tool_action_hint="catalog.service_query"`' in repair
        assert '`pack_refs=["pricing", "duration"]`' in repair
        assert "Do NOT collapse this turn" in repair

    def test_policy_core_runtime_contract_trims_unasked_services_overview_from_pricing_contact(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "pricing",
                "action": "fact",
                "tool_action_hint": "catalog.service_query",
                "pack_refs": ["pricing", "services_overview", "contact"],
                "slots": {"service": "маникюр"},
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.9,
                "reason": "standalone fact: user asks price for manicure and how to contact",
                "goal": None,
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
                "alternate_datetime": None,
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
        assert _policy_core_current_message_service_multifact_pack_refs(
            "Сколько стоит маникюр и как с вами связаться?",
            client_slug="demo_salon",
        ) == ["pricing", "contact"]
        assert _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile={},
            current_message="Сколько стоит маникюр и как с вами связаться?",
            context_payload={"service_cards": [{"includes": ["маникюр", "педикюр"]}]},
            client_slug="demo_salon",
        ) == "llm_policy_core_error:service_query_multifact_reclassification_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:service_query_multifact_reclassification_required",
            normalized_memory_profile={},
            contract=contract,
            current_message="Сколько стоит маникюр и как с вами связаться?",
            context_payload={"service_cards": [{"includes": ["маникюр", "педикюр"]}]},
            client_slug="demo_salon",
        )
        assert repair is not None
        assert '`pack_refs=["pricing", "contact"]`' in repair

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
        assert '`subject_kind="booking"`' in repair
        assert '`capability="bookability"`' in repair
        assert '`resolution_mode="direct"`' in repair
        assert '`expected_reply_type="name"`' in repair
        assert '`next_question="name"`' in repair
        assert '`slots.datetime` and `alternate_datetime`' in repair
        assert '`pending_question_act="fill_requested_slot"`' in repair
        assert '`pending_question_target="time"`' in repair
        assert '`active_question_relation="fill_requested_slot"`' in repair
        assert 'Do NOT keep `expected_reply_type="time"`' in repair
        assert '`pending_question_target="specialist"`' in repair
        assert 'translated carry-over' in repair

    def test_policy_core_runtime_contract_requires_active_booking_customer_name_carryover(
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
                "confidence": 0.82,
                "reason": "active booking slot-constraint still waits for precise time, but the current turn already grounded the customer name",
                "goal": "booking",
                "entity_refs": [
                    {
                        "entity_type": "customer",
                        "value": "Амина",
                        "confidence": 0.8,
                    }
                ],
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
                        "source_ref": "carryover",
                    },
                },
                "subject_kind": "booking",
                "capability": "bookability",
                "temporal_scope": "specific_time",
                "alternate_datetime": "завтра вечером",
                "resolution_mode": "direct",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        normalized_memory_profile = {
            "pending_question_contract": {
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
            },
            "semantic_contract": {
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "specific_time",
                "alternate_datetime": "завтра вечером",
                "resolution_mode": "direct",
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
                        "source_ref": "carryover",
                    },
                },
            },
        }

        assert _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile=normalized_memory_profile,
            current_message="Меня зовут Амина.",
        ) == "llm_policy_core_error:active_booking_customer_name_carryover_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:active_booking_customer_name_carryover_required",
            normalized_memory_profile=normalized_memory_profile,
            contract=contract,
            current_message="Меня зовут Амина.",
        )
        assert repair is not None
        assert '`slots.name="Амина"`' in repair
        assert '`subject_kind="booking"`' in repair
        assert '`expected_reply_type="time"`' in repair
        assert '`next_question="datetime"`' in repair
        assert '`pending_question_act="slot_constraint"`' in repair
        assert '`active_question_relation="slot_constraint"`' in repair

    def test_policy_core_runtime_contract_allows_confirmed_book_slot_from_memory(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "fact",
                "tool_action_hint": "calendar.book_slot",
                "pack_refs": [],
                "slots": {
                    "service": "маникюр",
                    "datetime": "завтра в 17:30",
                    "name": "Амина",
                    "phone": "7014445566",
                },
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.82,
                "reason": "user_confirmed_slot_yes_full_booking_slots_present",
                "goal": "booking",
                "entity_refs": [],
                "referents": {
                    "service": {
                        "value": "маникюр",
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    },
                    "customer": {
                        "value": "Амина",
                        "entity_type": "customer",
                        "source_ref": "memory.slot_state",
                    },
                },
                "subject_kind": "booking",
                "capability": "bookability",
                "temporal_scope": "specific_time",
                "alternate_datetime": None,
                "resolution_mode": "live_calendar",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        normalized_memory_profile = {
            "active_goal": "booking",
            "slot_state": {
                "service": "маникюр",
                "datetime": "завтра в 17:30",
                "name": "Амина",
                "phone": "7014445566",
            },
            "pending_question_contract": {
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
            },
            "semantic_contract": {
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "specific_time",
                "alternate_datetime": "завтра в 17:30",
                "resolution_mode": "direct",
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
                    "customer": {
                        "value": "Амина",
                        "entity_type": "customer",
                        "source_ref": "memory.slot_state",
                    },
                },
            },
        }

        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile=normalized_memory_profile,
                current_message="да",
            )
            is None
        )

    def test_policy_core_runtime_contract_keeps_service_choice_on_daypart_reply(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
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
                "confidence": 0.81,
                "reason": "active_multi_service_booking_needs_single_service_choice",
                "goal": "booking",
                "entity_refs": [],
                "referents": {},
                "subject_kind": "general",
                "capability": "bookability",
                "temporal_scope": "day",
                "alternate_datetime": "после работы",
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
        normalized_memory_profile = {
            "active_goal": "booking",
            "slot_state": {},
            "pending_question_contract": {
                "expected_reply_type": "service_choice",
                "next_question": "service",
                "open_questions": ["service"],
                "pending_question_act": "disambiguate",
                "pending_question_target": "service",
                "active_question_relation": "service_choice",
            },
            "semantic_contract": {
                "capability": "bookability",
                "subject_kind": "booking",
                "resolution_mode": "direct",
                "referents": {
                    "service": {
                        "value": "маникюр",
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "candidate",
                    }
                },
            },
        }

        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile=normalized_memory_profile,
                current_message="после работы",
            )
            is None
        )

    def test_policy_core_contract_repair_instruction_copies_focused_fields_exactly(
        self,
    ):
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:focused_contract_mismatch:goal",
            normalized_memory_profile={},
            current_message="chek mogu skinut",
        )

        assert repair is not None
        assert "focus_contract.forced_fields" in repair
        assert "Field `goal`" in repair
        assert "copy every forced field exactly" in repair

    def test_policy_core_booking_manage_reference_contract_is_repairable(
        self,
    ):
        assert (
            _policy_core_contract_error_disallows_repair(
                "llm_policy_core_error:booking_manage_reference_action_invalid",
                normalized_memory_profile={},
            )
            is False
        )

    def test_policy_core_runtime_contract_customer_name_intro_preempts_specialist_followup(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action_hint": "collect",
                "pack_refs": [],
                "slots": {"service": "маникюр", "name": "Амина."},
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.84,
                "reason": "Активный booking slot-контракт уже сузился до «завтра вечером», и предпочтение по мастеру (Айгерим) зафиксировано; дальнейшее уточнение времени ведем как specialist referent follow-up.",
                "goal": "booking",
                "entity_refs": [
                    {
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                        "value": "маникюр",
                        "confidence": 0.9,
                    },
                    {
                        "entity_type": "specialist",
                        "source_ref": "user",
                        "value": "Айгерим",
                        "confidence": 0.8,
                    },
                ],
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
                        "source_ref": "user",
                    },
                },
                "subject_kind": "specialist",
                "capability": "bookability",
                "temporal_scope": "day",
                "alternate_datetime": "завтра вечером",
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
            "slot_state": {"service": "маникюр", "datetime": "завтра вечером"},
            "pending_question_contract": {
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
            },
            "semantic_contract": {
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "day",
                "alternate_datetime": "завтра вечером",
                "resolution_mode": "ask_about_requested_slot",
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
                        "source_ref": "user",
                    },
                },
            },
        }

        assert _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile=normalized_memory_profile,
            current_message="Меня зовут Амина.",
        ) == "llm_policy_core_error:active_booking_customer_name_carryover_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:active_booking_customer_name_carryover_required",
            normalized_memory_profile=normalized_memory_profile,
            contract=contract,
            current_message="Меня зовут Амина.",
        )
        assert repair is not None
        assert '`subject_kind="booking"`' in repair
        assert 'Do NOT keep `subject_kind="specialist"`' in repair
        assert '`pending_question_target="time"`' in repair

    def test_policy_core_runtime_contract_bare_customer_name_preempts_specialist_followup(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action_hint": "collect",
                "pack_refs": [],
                "slots": {"service": "маникюр", "name": "Аружан"},
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.81,
                "reason": "carried specialist preference incorrectly stole a bare customer-name reply",
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
                        "source_ref": "carryover",
                    },
                },
                "subject_kind": "specialist",
                "capability": "bookability",
                "temporal_scope": "day",
                "alternate_datetime": "завтра вечером",
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
            "slot_state": {"service": "маникюр", "datetime": "завтра вечером"},
            "pending_question_contract": {
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
            },
            "semantic_contract": {
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "day",
                "alternate_datetime": "завтра вечером",
                "resolution_mode": "direct",
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
                        "source_ref": "carryover",
                    },
                },
            },
        }

        assert _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile=normalized_memory_profile,
            current_message="Аружан",
        ) == "llm_policy_core_error:active_booking_customer_name_carryover_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:active_booking_customer_name_carryover_required",
            normalized_memory_profile=normalized_memory_profile,
            contract=contract,
            current_message="Аружан",
        )
        assert repair is not None
        assert '`slots.name="аружан"`' in repair
        assert '`subject_kind="booking"`' in repair
        assert 'Do NOT keep `subject_kind="specialist"`' in repair
        assert '`pending_question_target="time"`' in repair

    def test_policy_core_runtime_contract_bare_customer_name_preserves_carried_temporal_candidate(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action_hint": "collect",
                "pack_refs": [],
                "slots": {"service": "маникюр", "name": "Аружан"},
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.81,
                "reason": "bare_customer_name_reply_dropped_carried_temporal_candidate",
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
                "subject_kind": "booking",
                "capability": "bookability",
                "temporal_scope": "day",
                "alternate_datetime": None,
                "resolution_mode": "direct",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        normalized_memory_profile = {
            "active_goal": "booking",
            "slot_state": {"service": "маникюр", "datetime": "завтра вечером"},
            "alternate_datetime": "завтра вечером",
            "temporal_scope": "day",
            "pending_question_contract": {
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
            },
            "semantic_contract": {
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "day",
                "alternate_datetime": "завтра вечером",
                "resolution_mode": "direct",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
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
            current_message="Аружан",
        ) == "llm_policy_core_error:active_booking_customer_name_carryover_required"

    def test_policy_core_runtime_contract_customer_name_intro_preserves_carried_temporal_candidate(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action_hint": "collect",
                "pack_refs": [],
                "slots": {"service": "маникюр", "name": "Амина"},
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.78,
                "reason": "active booking time follow-up still needs exact clock time after customer name fill",
                "goal": "booking",
                "entity_refs": [
                    {
                        "entity_type": "customer",
                        "value": "Амина",
                        "confidence": 0.82,
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
                "subject_kind": "booking",
                "capability": "bookability",
                "temporal_scope": "day",
                "alternate_datetime": "Меня зовут Амина.",
                "resolution_mode": "ask_about_requested_slot",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        normalized_memory_profile = {
            "slot_state": {"service": "маникюр", "datetime": "завтра вечером"},
            "pending_question_contract": {
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
            },
            "semantic_contract": {
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "day",
                "alternate_datetime": "завтра вечером",
                "resolution_mode": "ask_about_requested_slot",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
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
            current_message="Меня зовут Амина.",
        ) == "llm_policy_core_error:active_booking_customer_name_carryover_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:active_booking_customer_name_carryover_required",
            normalized_memory_profile=normalized_memory_profile,
            contract=contract,
            current_message="Меня зовут Амина.",
        )
        assert repair is not None
        assert '`alternate_datetime="завтра вечером"`' in repair
        assert '`temporal_scope="day"`' in repair
        assert "Do NOT rewrite `alternate_datetime` from the current self-intro text" in repair

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

    def test_policy_core_runtime_contract_accepts_promotions_booking_fact_followup(self):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "promotions",
                "action": "fact",
                "tool_action_hint": "catalog.service_query",
                "pack_refs": ["promotions"],
                "slots": {},
                "expected_reply_type": "service_choice",
                "next_question": "service",
                "open_questions": ["service"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.79,
                "reason": "standalone_promotions_head_with_missing_service_booking_request",
                "goal": "booking",
                "entity_refs": [],
                "referents": {},
                "subject_kind": "general",
                "capability": "promotions",
                "temporal_scope": "none",
                "alternate_datetime": None,
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
                current_message="Есть скидки, хочу записаться.",
                context_payload=None,
                client_slug="demo_salon",
            )
            is None
        )

    def test_policy_core_runtime_contract_accepts_promotions_location_booking_followup_with_implicit_temporal_side_ask(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "promotions",
                "action": "fact",
                "tool_action_hint": "catalog.service_query",
                "pack_refs": ["promotions", "location"],
                "slots": {},
                "expected_reply_type": "service_choice",
                "next_question": "service",
                "open_questions": ["service"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.74,
                "reason": "promotions + address + implicit temporal booking side ask without grounded service",
                "goal": "booking",
                "entity_refs": [],
                "referents": {},
                "subject_kind": "general",
                "capability": "promotions",
                "temporal_scope": "none",
                "alternate_datetime": None,
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
                current_message="Есть акции и адрес, можно сегодня после 6?",
                context_payload=None,
                client_slug="demo_salon",
            )
            is None
        )

    def test_policy_core_runtime_contract_accepts_promotions_booking_followup_with_implicit_temporal_side_ask(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "promotions",
                "action": "fact",
                "tool_action_hint": "catalog.service_query",
                "pack_refs": ["promotions"],
                "slots": {},
                "expected_reply_type": "service_choice",
                "next_question": "service",
                "open_questions": ["service"],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.74,
                "reason": "promotions + implicit temporal booking side ask without grounded service",
                "goal": "booking",
                "entity_refs": [],
                "referents": {},
                "subject_kind": "general",
                "capability": "promotions",
                "temporal_scope": "none",
                "alternate_datetime": None,
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
                current_message="Есть скидки, можно сегодня после 6?",
                context_payload=None,
                client_slug="demo_salon",
            )
            is None
        )

    def test_policy_core_runtime_contract_repair_instruction_preserves_promotions_grounded_service_location_contact_booking_scope(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "fact",
                "tool_action_hint": "catalog.service_query",
                "pack_refs": ["promotions"],
                "slots": {"service": "маникюр"},
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.71,
                "reason": "user asks promotions + location + contact for manicure and wants to book",
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
                "capability": "promotions",
                "temporal_scope": "none",
                "alternate_datetime": None,
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
                current_message="Есть акции на маникюр, хочу записаться, где вы находитесь и как с вами связаться?",
                context_payload={"service_cards": [{"includes": ["маникюр", "педикюр"]}]},
                client_slug="demo_salon",
            )
            == "llm_policy_core_error:promotions_grounded_service_booking_followup_reclassification_required"
        )
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:promotions_grounded_service_booking_followup_reclassification_required",
            normalized_memory_profile=None,
            contract=contract,
            current_message="Есть акции на маникюр, хочу записаться, где вы находитесь и как с вами связаться?",
            context_payload={"service_cards": [{"includes": ["маникюр", "педикюр"]}]},
            client_slug="demo_salon",
        )

        assert repair is not None
        assert '`pack_refs=["promotions", "location", "contact"]`' in repair
        assert '`expected_reply_type="time"`' in repair
        assert '`next_question="datetime"`' in repair
        assert '`pending_question_act="ask_about_requested_slot"`' in repair
        assert '`slots.service="маникюр"`' in repair

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

    def test_policy_core_runtime_contract_requires_active_booking_commit_progression_after_name_carryover(
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
                "confidence": 0.84,
                "reason": "active booking slot-constraint still waits for precise time even though the user supplied a concrete clock time",
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
                        "entity_type": "specialist",
                        "source_ref": "carryover",
                    },
                },
                "subject_kind": "booking",
                "capability": "bookability",
                "temporal_scope": "specific_time",
                "alternate_datetime": "завтра 18:00",
                "resolution_mode": "direct",
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        normalized_memory_profile = {
            "slot_state": {
                "service": "маникюр",
                "datetime": "завтра вечером",
                "name": "Амина",
                "phone": "87011234567",
            },
            "pending_question_contract": {
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
            },
            "semantic_contract": {
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "day",
                "alternate_datetime": "завтра вечером",
                "resolution_mode": "direct",
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
                        "source_ref": "carryover",
                    },
                    "customer": {
                        "value": "Амина",
                        "entity_type": "customer",
                        "source_ref": "slot_state",
                    },
                },
            },
        }

        assert _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile=normalized_memory_profile,
            current_message="Давайте в 18:00.",
            context_payload=None,
        ) == "llm_policy_core_error:active_booking_commit_progression_required"
        repair = _build_policy_core_contract_repair_instruction(
            schema_error="llm_policy_core_error:active_booking_commit_progression_required",
            normalized_memory_profile=normalized_memory_profile,
            contract=contract,
            current_message="Давайте в 18:00.",
            context_payload=None,
        )
        assert repair is not None
        assert '`action="fact"`' in repair
        assert '`tool_action_hint="calendar.book_slot"`' in repair
        assert '`resolution_mode="live_calendar"`' in repair
        assert '`slots.name="Амина"`' in repair
        assert "Ground `slots.datetime` by combining the explicit clock time" in repair
        assert "executor-parseable exact datetime surface" in repair
        assert "`slots.datetime` and `alternate_datetime`" in repair

    def test_policy_core_runtime_contract_requires_parseable_exact_datetime_for_booking_commit(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "fact",
                "tool_action_hint": "calendar.book_slot",
                "pack_refs": [],
                "slots": {
                    "service": "маникюр",
                    "datetime": "завтра вечером",
                    "name": "Амина",
                    "phone": "87011234567",
                },
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.84,
                "reason": "booking_commit_ready_after_explicit_time_completion",
                "goal": "booking",
                "entity_refs": [
                    {
                        "entity_type": "customer",
                        "value": "Амина",
                        "confidence": 0.8,
                    }
                ],
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
                        "source_ref": "carryover",
                    },
                    "customer": {
                        "value": "Амина",
                        "entity_type": "customer",
                        "source_ref": "decision_slots",
                    },
                },
                "subject_kind": "booking",
                "capability": "bookability",
                "temporal_scope": "specific_time",
                "alternate_datetime": "завтра вечером",
                "resolution_mode": "live_calendar",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        normalized_memory_profile = {
            "slot_state": {
                "service": "маникюр",
                "datetime": "завтра вечером",
                "name": "Амина",
                "phone": "87011234567",
            },
            "pending_question_contract": {
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
            },
            "semantic_contract": {
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "day",
                "alternate_datetime": "завтра вечером",
                "resolution_mode": "direct",
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
                        "source_ref": "carryover",
                    },
                    "customer": {
                        "value": "Амина",
                        "entity_type": "customer",
                        "source_ref": "decision_slots",
                    },
                },
            },
        }

        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile=normalized_memory_profile,
                current_message="Давайте в 18:00.",
                context_payload=None,
            )
            == "llm_policy_core_error:active_booking_commit_progression_required"
        )

    def test_policy_core_runtime_contract_allows_canonical_booking_commit_after_name_carryover(
        self,
    ):
        contract, schema_error = validate_llm_policy_core_output(
            {
                "intent": "booking",
                "action": "fact",
                "tool_action_hint": "calendar.book_slot",
                "pack_refs": [],
                "slots": {
                    "service": "маникюр",
                    "datetime": "завтра 18:00",
                    "name": "Амина",
                    "phone": "87011234567",
                },
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "needs_manager": False,
                "risk_signals": [],
                "language": "ru",
                "confidence": 0.84,
                "reason": "booking_commit_ready_after_explicit_time_completion",
                "goal": "booking",
                "entity_refs": [
                    {
                        "entity_type": "customer",
                        "value": "Амина",
                        "confidence": 0.8,
                    }
                ],
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
                        "source_ref": "carryover",
                    },
                    "customer": {
                        "value": "Амина",
                        "entity_type": "customer",
                        "source_ref": "decision_slots",
                    },
                },
                "subject_kind": "booking",
                "capability": "bookability",
                "temporal_scope": "specific_time",
                "alternate_datetime": "завтра 18:00",
                "resolution_mode": "live_calendar",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "resolver_id": None,
                "resolver_version": None,
            }
        )

        assert schema_error is None
        assert contract is not None
        normalized_memory_profile = {
            "slot_state": {
                "service": "маникюр",
                "datetime": "завтра вечером",
                "name": "Амина",
                "phone": "87011234567",
            },
            "pending_question_contract": {
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
            },
            "semantic_contract": {
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "specific_time",
                "alternate_datetime": "завтра вечером",
                "resolution_mode": "ask_about_requested_slot",
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
                        "source_ref": "carryover",
                    },
                    "customer": {
                        "value": "Амина",
                        "entity_type": "customer",
                        "source_ref": "decision_slots",
                    },
                },
            },
        }

        assert (
            _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile=normalized_memory_profile,
                current_message="Давайте в 18:00.",
                context_payload=None,
            )
            is None
        )

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

    def test_policy_core_context_service_hint_uses_label_parts_and_synonyms(self):
        context_payload = {
            "service_cards": [
                {
                    "id": "brows_lashes",
                    "label": "Брови и ресницы",
                    "includes": ["коррекция бровей", "окрашивание бровей"],
                    "synonyms": ["бровки", "реснички"],
                }
            ]
        }

        assert (
            _policy_core_context_service_hint(
                "Мне нужно на брови завтра после работы",
                context_payload,
                client_slug="demo_salon",
            )
            == "Брови"
        )
        assert (
            _policy_core_context_service_hint(
                "Хочу реснички на завтра",
                context_payload,
                client_slug="demo_salon",
            )
            == "реснички"
        )

    def test_route_policy_core_focuses_standalone_catalog_alias_price_fact_without_repair(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        focused_payload = {
            "intent": "pricing",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["pricing"],
            "slots": {"service": "Маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.91,
            "reason": "standalone_service_fact_grounded_from_catalog_alias",
            "goal": None,
            "entity_refs": [],
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "message_grounding",
                }
            },
            "subject_kind": "service",
            "capability": "pricing",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps(focused_payload)
            )
            result = route_llm_policy_core(
                "Сколько стоит маник?",
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["focused_owner_contract_used"] is True
        assert result["focused_standalone_service_fact"] == "pricing"
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["binding"]["tool_args"] == {"service_query": "Маникюр"}
        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert forced_fields["slots"] == {"service": "Маникюр"}

    def test_policy_core_customer_contact_surface_keeps_name_and_phone(self):
        assert (
            intent_service_module._policy_core_current_message_customer_name_surface(
                "Меня зовут Алина, телефон +77011234567"
            )
            == "Алина"
        )
        assert (
            intent_service_module._policy_core_current_message_customer_phone_surface(
                "Меня зовут Алина, телефон +77011234567"
            )
            == "+77011234567"
        )
        assert (
            intent_service_module._policy_core_current_message_customer_name_surface(
                "Гульнара, +77022334455"
            )
            == "Гульнара"
        )

    def test_policy_core_customer_name_surface_rejects_booking_action_phrase(self):
        assert (
            intent_service_module._policy_core_current_message_customer_name_surface(
                "проверь запись"
            )
            is None
        )
        assert (
            intent_service_module._policy_core_current_message_customer_name_surface(
                "Здравствуйте можно проверить мою запись?"
            )
            is None
        )
        assert (
            intent_service_module._policy_core_current_message_customer_name_surface(
                "Меня зовут Айгуль, проверьте мою запись"
            )
            == "Айгуль"
        )

    def test_policy_core_customer_name_surface_rejects_contact_delay_phrase(self):
        assert (
            intent_service_module._policy_core_current_message_customer_name_surface(
                "номер потом напишу"
            )
            is None
        )
        assert (
            intent_service_module._policy_core_current_message_customer_name_surface(
                "телефон позже скину"
            )
            is None
        )

    def test_policy_core_pending_phone_contact_delay_preserves_phone_collect(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {
                "service": "Брови",
                "datetime": "завтра 6 30 вечера",
                "name": "Амина",
            },
            "expected_reply_type": "phone",
            "next_question": "phone",
            "open_questions": ["phone"],
            "needs_manager": False,
            "goal": "booking",
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра 6 30 вечера",
            "resolution_mode": "direct",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "phone",
            "active_question_relation": "fill_requested_slot",
            "reason": "active_booking_phone_fill_contact_delayed",
            "referents": {
                "service": {
                    "value": "Брови",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "memory.semantic_contract",
                },
                "customer": {
                    "value": "Амина",
                    "entity_id": None,
                    "entity_type": "customer",
                    "source_ref": "memory.slot_state",
                },
            },
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "номер потом напишу",
                client_slug="demo_salon",
                current_goal="booking",
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {
                        "service": "Брови",
                        "datetime": "завтра 6 30 вечера",
                        "name": "Амина",
                    },
                    "pending_question_contract": {
                        "expected_reply_type": "phone",
                        "next_question": "phone",
                        "open_questions": ["phone"],
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "завтра 6 30 вечера",
                        "resolution_mode": "direct",
                        "referents": {
                            "service": {
                                "value": "Брови",
                                "entity_type": "service",
                                "source_ref": "memory.semantic_contract",
                            },
                            "customer": {
                                "value": "Амина",
                                "entity_type": "customer",
                                "source_ref": "memory.slot_state",
                            },
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["focused_active_booking_phone_fill"] is True
        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert forced_fields["expected_reply_type"] == "phone"
        assert forced_fields["slots"]["name"] == "Амина"
        assert "phone" not in forced_fields["slots"]
        assert result["payload"]["requested_outcome"] == "collect"

    def test_policy_core_pending_phone_number_commits_booking(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "fact",
            "tool_action_hint": "calendar.book_slot",
            "pack_refs": [],
            "slots": {
                "service": "Брови",
                "datetime": "завтра 6 30 вечера",
                "name": "Амина",
                "phone": "7015705555",
            },
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "goal": "booking",
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра 6 30 вечера",
            "resolution_mode": "live_calendar",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "reason": "active_booking_phone_fill_ready_for_book_slot",
            "referents": {
                "service": {
                    "value": "Брови",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "memory.semantic_contract",
                },
                "customer": {
                    "value": "Амина",
                    "entity_id": None,
                    "entity_type": "customer",
                    "source_ref": "memory.slot_state",
                },
            },
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "7015705555",
                client_slug="demo_salon",
                current_goal="booking",
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {
                        "service": "Брови",
                        "datetime": "завтра 6 30 вечера",
                        "name": "Амина",
                    },
                    "pending_question_contract": {
                        "expected_reply_type": "phone",
                        "next_question": "phone",
                        "open_questions": ["phone"],
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "завтра 6 30 вечера",
                        "resolution_mode": "direct",
                        "referents": {
                            "service": {
                                "value": "Брови",
                                "entity_type": "service",
                                "source_ref": "memory.semantic_contract",
                            },
                            "customer": {
                                "value": "Амина",
                                "entity_type": "customer",
                                "source_ref": "memory.slot_state",
                            },
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["focused_active_booking_phone_fill"] is True
        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert forced_fields["tool_action_hint"] == "calendar.book_slot"
        assert forced_fields["slots"]["phone"] == "7015705555"
        assert result["binding"]["tool_action"] == "calendar.book_slot"

    def test_policy_core_memory_profile_drops_booking_action_phrase_customer(self):
        profile = intent_service_module._normalize_policy_core_memory_profile(
            {
                "slot_state": {"name": "проверь запись", "service": "маникюр"},
                "semantic_contract": {
                    "subject_kind": "booking",
                    "capability": "booking_manage",
                    "referents": {
                        "customer": {
                            "value": "проверь запись",
                            "entity_type": "customer",
                            "source_ref": "message_grounding",
                        }
                    },
                },
            }
        )

        assert profile is not None
        assert profile["slot_state"] == {"service": "маникюр"}
        assert "referents" not in profile["semantic_contract"]

    def test_policy_core_booking_manage_reference_does_not_carry_fake_customer_name(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = focused_contract_response
            result = route_llm_policy_core(
                "вроде завтра вечером маникюр",
                client_slug="demo_salon",
                memory_profile={
                    "slot_state": {"name": "проверь запись"},
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                    },
                    "semantic_contract": {
                        "subject_kind": "booking",
                        "capability": "booking_manage",
                        "resolution_mode": "direct",
                        "referents": {
                            "customer": {
                                "value": "проверь запись",
                                "entity_type": "customer",
                                "source_ref": "message_grounding",
                            }
                        },
                    },
                },
            )

        forced_fields = result["policy_input"]["focus_contract"]["forced_fields"]
        assert result["ok"] is True
        assert result["focused_booking_manage_reference_carryover"] is True
        assert "name" not in forced_fields["slots"]
        assert "customer" not in forced_fields["referents"]
        assert forced_fields["slots"]["service"] == "маникюр"
        assert forced_fields["slots"]["datetime"] == "завтра вечером"
        assert forced_fields["expected_reply_type"] == "name"
        assert forced_fields["next_question"] == "name"
        assert forced_fields["open_questions"] == ["name"]

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

    def test_policy_core_focuses_duration_fact_when_service_named_in_current_turn(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        focused_payload = {
            "intent": "duration",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["duration"],
            "slots": {"service": "укладка"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.91,
            "reason": "standalone_service_fact_grounded_from_catalog_alias",
            "goal": None,
            "entity_refs": [
                {
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "message_grounding",
                    "value": "укладка",
                }
            ],
            "referents": {
                "service": {
                    "value": "укладка",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "message_grounding",
                }
            },
            "subject_kind": "service",
            "capability": "duration",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps(focused_payload)
            )
            result = route_llm_policy_core(
                "Сколько времени занимает укладка?",
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["focused_owner_contract_used"] is True
        assert result["focused_standalone_service_fact"] == "duration"
        assert result["contract_repair_retry_used"] is False
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

    def test_policy_core_preserves_exact_promotions_pack_ref_over_coarse_pricing_alias(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "pricing",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["promotions"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.78,
            "reason": "user_asked_promotions_during_booking_continuity",
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
            "capability": "bookability",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Есть ли акции?",
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
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["binding"]["tool_args"] == {"service_query": "маникюр"}
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["promotions"]
        assert result["payload"]["intent"] == "pricing"

    def test_policy_core_preserves_exact_promotions_pack_ref_over_master_query_alias(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["promotions"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.62,
            "reason": "user_asked_promotions_during_booking_continuity",
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
            "capability": "promotions",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Есть ли акции?",
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
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["promotions"]
        assert result["payload"]["intent"] == "master_query"

    def test_policy_core_accepts_specialist_duration_interrupt_with_specialist_followup_carryover(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "duration",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["duration"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.79,
            "reason": "duration_info_interrupt_during_active_booking_specialist_followup",
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
            "capability": "duration",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": "specialist",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Сколько это длится?",
                current_goal="booking",
                slot_state={"service": "маникюр"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": None,
                        "pending_question_target": "specialist",
                        "active_question_relation": "referent_followup",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "specialist",
                        "resolution_mode": "referent_followup",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            },
                            "specialist": {
                                "value": "Айдана",
                                "entity_id": "spec:aidana",
                                "entity_type": "specialist",
                                "source_ref": "carryover",
                            },
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["binding"]["tool_args"] == {"service_query": "маникюр"}
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["duration"]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["pending_question_target"] == "specialist"
        assert result["payload"]["missing_information"]["active_question_relation"] == "generic_info_interrupt"

    def test_policy_core_accepts_missing_service_parking_interrupt_with_service_choice_carryover(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "catalog.location",
            "pack_refs": ["parking"],
            "slots": {},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.77,
            "reason": "parking_info_interrupt_during_active_booking_missing_service_followup",
            "goal": "booking",
            "entity_refs": [],
            "referents": {},
            "subject_kind": "general",
            "capability": "location",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра в 18:00",
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Есть ли парковка?",
                current_goal="booking",
                slot_state={"datetime": "завтра в 18:00"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"datetime": "завтра в 18:00"},
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "pending_question_act": None,
                        "pending_question_target": None,
                        "active_question_relation": None,
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "booking",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "завтра в 18:00",
                        "resolution_mode": "clarify_missing_subject",
                    },
                },
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["goal"] == "booking"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["parking"]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "general"
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "завтра в 18:00"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "service_choice"
        assert result["payload"]["missing_information"]["next_question"] == "service"
        assert result["payload"]["missing_information"]["open_questions"] == ["service"]
        assert result["payload"]["missing_information"].get("pending_question_target") is None
        assert result["payload"]["missing_information"]["active_question_relation"] == "generic_info_interrupt"

    def test_policy_core_rejects_missing_service_parking_interrupt_without_generic_info_relation(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "catalog.location",
            "pack_refs": ["parking"],
            "slots": {},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.77,
            "reason": "booking_continuity_waits_service_choice__user_asked_parking_fact_interrupt",
            "goal": "booking",
            "entity_refs": [],
            "referents": {"service": None},
            "subject_kind": "general",
            "capability": "location",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра в 18:00",
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps(invalid_payload)
            )
            result = route_llm_policy_core(
                "Есть ли парковка?",
                current_goal="booking",
                slot_state={"datetime": "завтра в 18:00"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"datetime": "завтра в 18:00"},
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "general",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "завтра в 18:00",
                        "resolution_mode": "clarify_missing_subject",
                    },
                },
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:generic_info_interrupt_relation_invalid"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False

    def test_policy_core_rejects_missing_service_parking_interrupt_that_invents_service_grounding(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "catalog.location",
            "pack_refs": ["parking"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.77,
            "reason": "booking_continuation_missing_service_interrupted_by_parking_fact",
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
            "subject_kind": "general",
            "capability": "location",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра в 18:00",
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps(invalid_payload)
            )
            result = route_llm_policy_core(
                "Есть ли парковка?",
                current_goal="booking",
                slot_state={"datetime": "завтра в 18:00"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"datetime": "завтра в 18:00"},
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "pending_question_act": None,
                        "pending_question_target": None,
                        "active_question_relation": None,
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "general",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "завтра в 18:00",
                        "resolution_mode": "clarify_missing_subject",
                    },
                },
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:missing_service_exact_datetime_info_interrupt_carryover_invalid"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False

    def test_policy_core_accepts_active_booking_location_interrupt_with_time_followup(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "catalog.location",
            "pack_refs": ["location"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.78,
            "reason": "location_info_interrupt_during_active_booking_time_followup",
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
            "subject_kind": "general",
            "capability": "location",
            "temporal_scope": "day",
            "alternate_datetime": "завтра вечером",
            "resolution_mode": "policy_fact",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Где вы находитесь?",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "завтра вечером"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр", "datetime": "завтра вечером"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "booking",
                        "temporal_scope": "day",
                        "alternate_datetime": "завтра вечером",
                        "resolution_mode": "direct",
                    },
                },
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["goal"] == "booking"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["location"]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "general"
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "завтра вечером"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["pending_question_act"] == "slot_constraint"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "generic_info_interrupt"

    def test_policy_core_accepts_active_booking_parking_interrupt_with_time_followup(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "catalog.location",
            "pack_refs": ["parking"],
            "slots": {"service": None},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.76,
            "reason": "parking_fact_interrupt_preserve_booking_datetime_contract",
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
            "subject_kind": "general",
            "capability": "location",
            "temporal_scope": "day",
            "alternate_datetime": "завтра вечером",
            "resolution_mode": "policy_fact",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Есть ли парковка?",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "завтра вечером"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр", "datetime": "завтра вечером"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "booking",
                        "temporal_scope": "day",
                        "alternate_datetime": "завтра вечером",
                        "resolution_mode": "direct",
                    },
                },
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["goal"] == "booking"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["parking"]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "general"
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "завтра вечером"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["pending_question_act"] == "slot_constraint"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert result["payload"]["missing_information"]["active_question_relation"] == "generic_info_interrupt"

    def test_policy_core_rejects_active_booking_location_interrupt_that_keeps_slot_constraint_relation(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "catalog.location",
            "pack_refs": ["location"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.71,
            "reason": "location_question_during_active_booking_continuity_keep_datetime_contract",
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
            "capability": "location",
            "temporal_scope": "day",
            "alternate_datetime": "завтра вечером",
            "resolution_mode": "policy_fact",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Где вы находитесь?",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "завтра вечером"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр", "datetime": "завтра вечером"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "booking",
                        "temporal_scope": "day",
                        "alternate_datetime": "завтра вечером",
                        "resolution_mode": "direct",
                    },
                },
            )

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert result["schema_error"] == (
            "llm_policy_core_error:active_booking_info_interrupt_contract_invalid"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False

    def test_policy_core_resume_after_specialist_info_interrupt_keeps_full_prompt_first_attempt(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр", "datetime": "завтра в 18:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.83,
            "reason": "user_provided_exact_time_with_carried_day_date_in_booking_continuity",
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
                    "value": "Айдане",
                    "entity_id": "sp:aidane",
                    "entity_type": "specialist",
                    "source_ref": "user_message",
                },
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра в 18:00",
            "resolution_mode": "direct",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "fill_requested_slot",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "В 18:00.",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "завтра вечером"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр", "datetime": "завтра вечером"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": None,
                        "pending_question_target": "specialist",
                        "active_question_relation": "generic_info_interrupt",
                    },
                    "semantic_contract": {
                        "capability": "duration",
                        "subject_kind": "service",
                        "temporal_scope": "day",
                        "alternate_datetime": "завтра вечером",
                        "resolution_mode": "policy_fact",
                        "pending_question_target": "specialist",
                        "active_question_relation": "generic_info_interrupt",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            },
                            "specialist": {
                                "value": "Айдане",
                                "entity_id": "sp:aidane",
                                "entity_type": "specialist",
                                "source_ref": "user_message",
                            },
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["compact_input_used"] is False
        assert result["compact_retry_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"]["requested_outcome"] == "collect"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "name"
        assert result["payload"]["missing_information"]["next_question"] == "name"

    def test_policy_core_rejects_specialist_preference_followup_that_clears_time_contract(
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
            "expected_reply_type": None,
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.86,
            "reason": "user_named_preferred_specialist_during_booking_time_selection",
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
                    "value": "Айдане",
                    "entity_id": None,
                    "entity_type": "specialist",
                    "source_ref": "user",
                },
            },
            "subject_kind": "specialist",
            "capability": "bookability",
            "temporal_scope": "day",
            "alternate_datetime": "завтра вечером",
            "resolution_mode": "referent_followup",
            "pending_question_act": None,
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(
                json.dumps(invalid_payload)
            )
            result = route_llm_policy_core(
                "К Айдане.",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "завтра вечером"},
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр", "datetime": "завтра вечером"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "capability": "bookability",
                        "subject_kind": "booking",
                        "temporal_scope": "day",
                        "alternate_datetime": "завтра вечером",
                        "resolution_mode": "direct",
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
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

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:active_booking_specialist_followup_reclassification_required"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False

    def test_policy_core_resume_after_missing_service_info_interrupt_keeps_full_prompt_first_attempt(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр", "datetime": "завтра в 18:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.84,
            "reason": "service_provided_while_datetime_already_known_ask_for_name",
            "goal": "booking",
            "entity_refs": [],
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_message",
                }
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра в 18:00",
            "resolution_mode": "direct",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "fill_requested_slot",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Маникюр.",
                current_goal="booking",
                slot_state={},
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "pending_question_act": None,
                        "pending_question_target": None,
                        "active_question_relation": "generic_info_interrupt",
                    },
                    "semantic_contract": {
                        "capability": "location",
                        "subject_kind": "general",
                        "temporal_scope": "specific_time",
                        "alternate_datetime": "завтра в 18:00",
                        "resolution_mode": "policy_fact",
                        "active_question_relation": "generic_info_interrupt",
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["compact_input_used"] is False
        assert result["compact_retry_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"]["requested_outcome"] == "collect"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "name"
        assert result["payload"]["missing_information"]["next_question"] == "name"

    def test_policy_core_boundary_normalizes_mixed_first_turn_promotions_precedence_over_side_asks(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "catalog.location",
            "pack_refs": ["location"],
            "slots": {"service": None},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.78,
            "reason": "user_requested_address",
            "goal": None,
            "entity_refs": [],
            "referents": {"service": None},
            "subject_kind": "general",
            "capability": "location",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Есть скидки, хочу записаться и адрес, пожалуйста.",
                memory_profile={},
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["intent"] == "promotions"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "general"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["promotions", "location"]

    def test_policy_core_boundary_preserves_promotions_location_booking_followup(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "booking",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["promotions", "location"],
            "slots": {"service": None},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.72,
            "reason": "user_wants_promotions_and_booking_and_address_without_specifying_service",
            "goal": "booking",
            "entity_refs": [],
            "referents": {"service": None},
            "subject_kind": "general",
            "capability": "promotions",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Есть скидки, хочу записаться и адрес, пожалуйста.",
                memory_profile={},
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["intent"] == "promotions"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["promotions", "location"]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "general"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "service_choice"
        assert result["payload"]["missing_information"]["next_question"] == "service"
        assert result["payload"]["missing_information"]["open_questions"] == ["service"]

    def test_policy_core_boundary_preserves_promotions_location_booking_followup_for_implicit_temporal_side_ask(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "promotions",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["promotions", "location"],
            "slots": {},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.72,
            "reason": "promotions + address + implicit temporal booking side ask without grounded service",
            "goal": "booking",
            "entity_refs": [],
            "referents": {},
            "subject_kind": "general",
            "capability": "promotions",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Есть акции и адрес, можно сегодня после 6?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["intent"] == "promotions"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["promotions", "location"]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "general"
        assert result["payload"]["goal"] == "booking"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "service_choice"
        assert result["payload"]["missing_information"]["next_question"] == "service"
        assert result["payload"]["missing_information"]["open_questions"] == ["service"]

    def test_policy_core_boundary_normalizes_promotions_booking_followup_without_service(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": None},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.66,
            "reason": "user_requests_discounts_with_booking_but_service_not_grounded",
            "goal": "booking",
            "entity_refs": [],
            "referents": {},
            "subject_kind": "general",
            "capability": "bookability",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "clarify_missing_subject",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Есть скидки, хочу записаться.",
                memory_profile={},
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["intent"] == "promotions"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["promotions"]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "general"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "service_choice"
        assert result["payload"]["missing_information"]["next_question"] == "service"
        assert result["payload"]["missing_information"]["open_questions"] == ["service"]
        assert result["payload"]["missing_information"].get("pending_question_act") is None
        assert result["payload"]["missing_information"].get("pending_question_target") is None
        assert result["payload"]["missing_information"].get("active_question_relation") is None

    def test_policy_core_boundary_preserves_promotions_booking_followup_without_service_for_implicit_temporal_side_ask(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "promotions",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["promotions"],
            "slots": {},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.72,
            "reason": "promotions + implicit temporal booking side ask without grounded service",
            "goal": "booking",
            "entity_refs": [],
            "referents": {},
            "subject_kind": "general",
            "capability": "promotions",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Есть скидки, можно сегодня после 6?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["intent"] == "promotions"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["promotions"]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "general"
        assert result["payload"]["goal"] == "booking"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "service_choice"
        assert result["payload"]["missing_information"]["next_question"] == "service"
        assert result["payload"]["missing_information"]["open_questions"] == ["service"]
        assert result["payload"]["missing_information"].get("pending_question_act") is None
        assert result["payload"]["missing_information"].get("pending_question_target") is None
        assert result["payload"]["missing_information"].get("active_question_relation") is None

    def test_policy_core_boundary_normalizes_promotions_grounded_service_booking_followup(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
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
            "confidence": 0.66,
            "reason": "need_service_for_booking_followup_even_when_promotions_mentioned",
            "goal": "booking",
            "entity_refs": [],
            "referents": {},
            "subject_kind": "general",
            "capability": "bookability",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "clarify_missing_subject",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Есть акции на маникюр, хочу записаться.",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["binding"]["tool_args"] == {"service_query": "маникюр"}
        assert result["payload"]["intent"] == "promotions"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["promotions"]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["semantic_slots"]["service"] == "маникюр"
        assert (
            result["payload"]["grounding_requirements"]["referents"]["service"]["value"]
            == "маникюр"
        )
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert (
            result["payload"]["missing_information"]["pending_question_act"]
            == "ask_about_requested_slot"
        )
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"

    def test_policy_core_boundary_normalization_audit_records_prevalidate_override(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
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
            "confidence": 0.66,
            "reason": "need_service_for_booking_followup_even_when_promotions_mentioned",
            "goal": "booking",
            "entity_refs": [],
            "referents": {},
            "subject_kind": "general",
            "capability": "bookability",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "clarify_missing_subject",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Есть акции на маникюр, хочу записаться.",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["boundary_normalization_used"] is True
        assert result["llm_policy_override_reason_code"] == "boundary_semantic_normalization"
        assert result["llm_policy_override_reason_codes"] == ["boundary_semantic_normalization"]
        assert result["semantic_arbiter_audit"] == {
            "intent_override_count": 1,
            "intent_override_reason_codes": ["boundary_semantic_normalization"],
            "action_changed": True,
            "intent_changed": True,
            "tool_action_changed": True,
        }
        assert result["semantic_intent_overrides"] == [
            {
                "reason_code": "boundary_semantic_normalization",
                "stage": "prevalidate",
                "template_id": "promotions_grounded_service_booking_followup_boundary",
                "trigger_reason": "prevalidate_boundary_normalization",
                "from_intent": "booking",
                "to_intent": "promotions",
                "from_action": "collect",
                "to_action": "fact",
                "from_tool_action": "collect",
                "to_tool_action": "catalog.service_query",
            }
        ]
        event = result["boundary_normalization_events"][0]
        assert event["stage"] == "prevalidate"
        assert event["template_id"] == "promotions_grounded_service_booking_followup_boundary"
        assert event["trigger_reason"] == "prevalidate_boundary_normalization"
        assert event["changes"]["intent"] == {"before": "booking", "after": "promotions"}
        assert event["changes"]["action"] == {"before": "collect", "after": "fact"}
        assert event["changes"]["tool_action"] == {
            "before": "collect",
            "after": "catalog.service_query",
        }
        assert event["changes"]["expected_reply_type"] == {
            "before": "service_choice",
            "after": "time",
        }
        assert (
            result["payload"]["missing_information"]["active_question_relation"]
            == "ask_about_requested_slot"
        )

    def test_policy_core_boundary_normalizes_promotions_grounded_service_location_booking_followup(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["promotions", "location"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.74,
            "reason": "user_asks_promotions_for_manicure_and_requests_address_and_booking",
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
            "capability": "promotions",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Есть акции на маникюр, хочу записаться и адрес, пожалуйста.",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["binding"]["tool_args"] == {"service_query": "маникюр"}
        assert result["payload"]["intent"] == "promotions"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["promotions", "location"]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["semantic_slots"]["service"] == "маникюр"
        assert (
            result["payload"]["grounding_requirements"]["referents"]["service"]["value"]
            == "маникюр"
        )
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert (
            result["payload"]["missing_information"]["pending_question_act"]
            == "ask_about_requested_slot"
        )
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert (
            result["payload"]["missing_information"]["active_question_relation"]
            == "ask_about_requested_slot"
        )

    def test_policy_core_boundary_normalizes_promotions_grounded_service_contact_booking_followup(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["promotions", "contact"],
            "slots": {"service": "маникюр", "datetime": None, "name": None, "phone": None},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.74,
            "reason": "user asks for promotions on manicure and how to contact; preserve grounded service",
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
            "capability": "promotions",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Есть акции на маникюр, хочу записаться и как с вами связаться?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["binding"]["tool_args"] == {"service_query": "маникюр"}
        assert result["payload"]["intent"] == "promotions"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["promotions", "contact"]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["semantic_slots"]["service"] == "маникюр"
        assert (
            result["payload"]["grounding_requirements"]["referents"]["service"]["value"]
            == "маникюр"
        )
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert (
            result["payload"]["missing_information"]["pending_question_act"]
            == "ask_about_requested_slot"
        )
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert (
            result["payload"]["missing_information"]["active_question_relation"]
            == "ask_about_requested_slot"
        )

    def test_policy_core_boundary_normalizes_promotions_grounded_service_location_contact_booking_followup(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["location", "contact"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": None,
            "confidence": None,
            "reason": "user_requested_location_and_contact_for_booking_with_grounded_service_manicure",
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "service",
            "capability": "location",
            "temporal_scope": None,
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Есть акции на маникюр, хочу записаться, где вы находитесь и как с вами связаться?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["binding"]["tool_args"] == {"service_query": "маникюр"}
        assert result["payload"]["intent"] == "promotions"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "promotions",
            "location",
            "contact",
        ]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["semantic_slots"]["service"] == "маникюр"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert (
            result["payload"]["missing_information"]["pending_question_act"]
            == "ask_about_requested_slot"
        )
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert (
            result["payload"]["missing_information"]["active_question_relation"]
            == "ask_about_requested_slot"
        )
        assert result["boundary_normalization_used"] is True

    def test_policy_core_boundary_preserves_promotions_grounded_service_location_contact_booking_followup_without_normalization(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "promotions",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["promotions", "location", "contact"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.79,
            "reason": "user_requested_promotions_location_contact_and_booking_for_grounded_manicure",
            "goal": "booking",
            "entity_refs": [],
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
            "subject_kind": "service",
            "capability": "promotions",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Есть акции на маникюр, хочу записаться, где вы находитесь и как с вами связаться?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["boundary_normalization_used"] is False
        assert result["llm_policy_override_reason_codes"] in (None, [])
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["binding"]["tool_args"] == {"service_query": "маникюр"}
        assert result["payload"]["intent"] == "promotions"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "promotions",
            "location",
            "contact",
        ]
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert (
            result["payload"]["missing_information"]["pending_question_act"]
            == "ask_about_requested_slot"
        )
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert (
            result["payload"]["missing_information"]["active_question_relation"]
            == "ask_about_requested_slot"
        )

    def test_service_query_multifact_detects_promotions_master_and_contact_scope(self):
        assert _policy_core_current_message_service_multifact_pack_refs(
            "Есть акции на маникюр, кто делает маникюр и как с вами связаться?",
            client_slug="demo_salon",
        ) == ["promotions", "master", "contact"]

    def test_policy_core_boundary_normalizes_promotions_master_contact_multifact_scope(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["promotions"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.67,
            "reason": "user_asks_promotions_and_master_and_contact_for_manicure",
            "goal": None,
            "entity_refs": [],
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
            "subject_kind": "service",
            "capability": "promotions",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Есть акции на маникюр, кто делает маникюр и как с вами связаться?",
                memory_profile={},
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["binding"]["tool_args"] == {"service_query": "маникюр"}
        assert result["payload"]["intent"] == "promotions"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "promotions",
            "master",
            "contact",
        ]

    def test_policy_core_boundary_normalizes_mixed_first_turn_location_service_fact_over_hours_misroute(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "hours",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["hours", "pricing"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.78,
            "reason": "user asks for working hours plus price for manicure in same message",
            "goal": None,
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
            "capability": "hours",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Сколько стоит маникюр, сколько длится, где находитесь и можно записаться?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "location"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["location", "pricing", "duration"]
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"

    def test_policy_core_boundary_normalization_audit_records_runtime_contract_override(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "hours",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["hours", "pricing"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.78,
            "reason": "user asks for working hours plus price for manicure in same message",
            "goal": None,
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
            "capability": "hours",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Сколько стоит маникюр, сколько длится, где находитесь и можно записаться?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["boundary_normalization_used"] is True
        assert result["llm_policy_override_reason_codes"] == ["boundary_semantic_normalization"]
        assert result["semantic_arbiter_audit"] == {
            "intent_override_count": 1,
            "intent_override_reason_codes": ["boundary_semantic_normalization"],
            "action_changed": False,
            "intent_changed": True,
            "tool_action_changed": False,
        }
        assert result["semantic_intent_overrides"] == [
            {
                "reason_code": "boundary_semantic_normalization",
                "stage": "runtime_contract",
                "template_id": "mixed_first_turn_location_service_fact_booking_followup_boundary",
                "trigger_reason": "llm_policy_core_error:mixed_first_turn_location_service_fact_reclassification_required",
                "from_intent": "hours",
                "to_intent": "location",
                "from_action": "fact",
                "to_action": "fact",
                "from_tool_action": "info",
                "to_tool_action": "info",
            }
        ]
        event = result["boundary_normalization_events"][0]
        assert event["stage"] == "runtime_contract"
        assert (
            event["template_id"]
            == "mixed_first_turn_location_service_fact_booking_followup_boundary"
        )
        assert (
            event["trigger_reason"]
            == "llm_policy_core_error:mixed_first_turn_location_service_fact_reclassification_required"
        )
        assert event["changes"]["intent"] == {"before": "hours", "after": "location"}
        assert event["changes"]["pack_refs"] == {
            "before": ["hours", "pricing"],
            "after": ["location", "pricing", "duration"],
        }
        assert event["changes"]["expected_reply_type"] == {"before": None, "after": "time"}

    def test_policy_core_boundary_preserves_location_service_booking_followup_scope(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["location", "duration"],
            "slots": {"service": "педикюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.74,
            "reason": "location_head_duration_fact_with_booking_side_request",
            "goal": "booking",
            "entity_refs": [],
            "referents": {
                "service": {
                    "value": "педикюр",
                    "entity_id": "svc:pedicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "service",
            "capability": "location",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра вечером",
            "resolution_mode": "policy_fact",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Где вы находитесь и сколько длится педикюр, можно записаться завтра вечером?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "location"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["location", "duration"]
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"

    def test_policy_core_boundary_preserves_location_service_multifact_booking_followup_without_normalization(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["location", "pricing", "duration"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.78,
            "reason": "location_head_multifact_booking_followup",
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
            "capability": "location",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Сколько стоит маникюр и сколько длится, где находитесь и можно записаться?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["boundary_normalization_used"] is False
        assert result["llm_policy_override_reason_codes"] in (None, [])
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "location"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "location",
            "pricing",
            "duration",
        ]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert (
            result["payload"]["missing_information"]["pending_question_act"]
            == "ask_about_requested_slot"
        )
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"
        assert (
            result["payload"]["missing_information"]["active_question_relation"]
            == "ask_about_requested_slot"
        )

    def test_policy_core_boundary_preserves_location_service_booking_followup_for_implicit_temporal_side_ask(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["location", "duration"],
            "slots": {"service": "педикюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.74,
            "reason": "location_head_duration_fact_with_implicit_temporal_booking_side_request",
            "goal": "booking",
            "entity_refs": [],
            "referents": {
                "service": {
                    "value": "педикюр",
                    "entity_id": "svc:pedicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "service",
            "capability": "location",
            "temporal_scope": "day",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Где вы находитесь и сколько длится педикюр, можно сегодня после 6?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "location"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["location", "duration"]
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"

    def test_policy_core_boundary_preserves_location_service_presence_with_pricing(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "hours",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["hours", "pricing"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.8,
            "reason": "user asks what services are available plus price and location for manicure",
            "goal": None,
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
            "capability": "hours",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Какие услуги у вас есть и сколько стоит маникюр и где находитесь?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "location"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "location",
            "pricing",
            "services_overview",
        ]

    def test_policy_core_boundary_preserves_valid_location_service_presence_with_pricing(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        valid_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["location", "pricing", "services_overview"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.82,
            "reason": "user asks what services are available plus price and location for manicure",
            "goal": None,
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
            "capability": "location",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
            result = route_llm_policy_core(
                "Какие услуги у вас есть и сколько стоит маникюр и где находитесь?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "location",
            "pricing",
            "services_overview",
        ]

    def test_policy_core_boundary_preserves_location_pricing_contact_scope(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        valid_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["location", "contact", "pricing"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.82,
            "reason": "user asks location, contact, and price for manicure",
            "goal": None,
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
            "capability": "location",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(valid_payload))
            result = route_llm_policy_core(
                "Где вы находитесь, сколько стоит маникюр и как с вами связаться?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "location",
            "pricing",
            "contact",
        ]

    def test_policy_core_boundary_preserves_location_pricing_master_contact_scope(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        overclaimed_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["location", "pricing", "services_overview", "master", "contact"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.82,
            "reason": "user asks location, price, master, and contact for manicure",
            "goal": None,
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
            "capability": "location",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(overclaimed_payload))
            result = route_llm_policy_core(
                "Где вы находитесь, сколько стоит маникюр, кто делает маникюр и как с вами связаться?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "location",
            "pricing",
            "master",
            "contact",
        ]

    def test_policy_core_boundary_preserves_location_pricing_master_scope_when_location_is_late(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["location", "pricing", "master"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.84,
            "reason": "location_head_price_master_scope_even_when_location_is_sentence_final",
            "goal": None,
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
            "capability": "location",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Кто делает маникюр, сколько стоит и где вы находитесь?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["boundary_normalization_used"] is False
        assert result["llm_policy_override_reason_codes"] in (None, [])
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "location"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "location",
            "pricing",
            "master",
        ]

    def test_policy_core_boundary_preserves_location_duration_master_scope_when_location_is_late(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["location", "duration", "master"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.84,
            "reason": "location_head_duration_master_scope_even_when_location_is_sentence_final",
            "goal": None,
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
            "capability": "location",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Сколько длится маникюр, кто делает маникюр и где вы находитесь?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["boundary_normalization_used"] is False
        assert result["llm_policy_override_reason_codes"] in (None, [])
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "location"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "location",
            "duration",
            "master",
        ]

    def test_policy_core_boundary_normalizes_service_fact_head_over_temporal_side_booking(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
            "action": "fact",
            "tool_action_hint": "calendar.book_slot",
            "pack_refs": [],
            "slots": {"service": "педикюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.81,
            "reason": "user wants to know the price and asks if tomorrow at 6 works",
            "goal": None,
            "entity_refs": [],
            "referents": {
                "service": {
                    "value": "педикюр",
                    "entity_id": "svc:pedicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "subject_kind": "service",
            "capability": "bookability",
            "temporal_scope": "day",
            "alternate_datetime": "завтра в 6",
            "resolution_mode": "live_calendar",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Сколько стоит педикюр и можно завтра в 6?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["intent"] == "pricing"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["pricing"]
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"

    def test_policy_core_boundary_preserves_hours_service_booking_followup_scope(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "hours",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["hours", "pricing"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.72,
            "reason": "mixed_fact_hours_pricing_with_booking_side_request",
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
            "capability": "hours",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Вы сегодня работаете и сколько стоит маникюр, можно записаться на 7?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "hours"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["hours", "pricing"]
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"

    def test_policy_core_boundary_normalizes_hours_service_booking_followup_over_pricing_only_misroute(
        self,
        monkeypatch,
    ):
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
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.68,
            "reason": "booking side request caused pricing-only collapse",
            "goal": None,
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
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Вы сегодня работаете и сколько стоит маникюр, можно записаться на 7?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "hours"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["hours", "pricing"]
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"

    def test_policy_core_boundary_preserves_service_query_multifact_scope(
        self,
        monkeypatch,
    ):
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
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.88,
            "reason": "user asks pricing and duration for grounded service маникюр",
            "goal": None,
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
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Сколько стоит маникюр и сколько длится маникюр?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["intent"] == "pricing"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["pricing", "duration"]

    def test_policy_core_boundary_preserves_service_query_multifact_booking_followup_scope(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "pricing",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["pricing", "duration"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.72,
            "reason": "user_asks_pricing_and_duration_for_grounded_service_and_requests_booking_with_temporal_clue",
            "goal": "booking",
            "entity_refs": [],
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
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра вечером",
            "resolution_mode": "policy_fact",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Сколько стоит маникюр и сколько длится, можно записаться завтра вечером?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["intent"] == "pricing"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["pricing", "duration"]
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"

    def test_policy_core_boundary_preserves_master_contact_service_query_multifact_booking_followup_scope(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["master", "contact"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.71,
            "reason": "user_asks_who_performs_manicure_how_to_contact_and_requests_booking",
            "goal": "booking",
            "entity_refs": [],
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "subject_kind": "service",
            "capability": "master",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Кто делает маникюр и как с вами связаться, можно записаться?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["boundary_normalization_used"] is False
        assert result["llm_policy_override_reason_codes"] in (None, [])
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["intent"] == "master_query"
        assert result["payload"]["capability_id"] == "master"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["master", "contact"]
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"

    def test_policy_core_boundary_normalizes_service_query_multifact_booking_followup_over_fact_only_misroute(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "pricing",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["pricing", "duration"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.72,
            "reason": "multifact booking side ask collapsed to fact only",
            "goal": None,
            "entity_refs": [],
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
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Сколько стоит маникюр и сколько длится, можно записаться завтра вечером?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["intent"] == "pricing"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["pricing", "duration"]
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["pending_question_target"] == "time"

    def test_policy_core_boundary_preserves_master_head_services_contact_multifact_scope(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["services_overview", "master", "contact"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.88,
            "reason": "user asks services, who does manicure, and contact",
            "goal": None,
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
            "capability": "portfolio",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Какие услуги есть, кто делает маникюр и как с вами связаться?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["intent"] == "master_query"
        assert result["payload"]["capability_id"] == "master"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "master",
            "services_overview",
            "contact",
        ]

    def test_policy_core_boundary_preserves_master_head_services_parking_multifact_scope(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["services_overview", "master", "parking"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.88,
            "reason": "user asks services, who does manicure, and parking",
            "goal": None,
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
            "capability": "master",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Какие услуги есть, кто делает маникюр и есть парковка?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["intent"] == "master_query"
        assert result["payload"]["capability_id"] == "master"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "master",
            "services_overview",
            "parking",
        ]

    def test_policy_core_boundary_trims_service_query_contact_overclaim(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "pricing",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["pricing", "services_overview", "contact"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.88,
            "reason": "standalone fact: user asks price for manicure and how to contact",
            "goal": None,
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
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Сколько стоит маникюр и как с вами связаться?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["intent"] == "pricing"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "service"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["pricing", "contact"]

    def test_policy_core_boundary_preserves_hours_head_multifact_scope_over_service_query(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        canonical_payload = {
            "intent": "hours",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["hours", "services_overview", "pricing", "duration"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.87,
            "reason": "user asks multiple facts: hours, service overview, price, and duration for manicure",
            "goal": None,
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
            "capability": "hours",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(canonical_payload))
            result = route_llm_policy_core(
                "Вы сегодня работаете, какие услуги есть, сколько стоит и сколько длится маникюр?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "hours"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == [
            "hours",
            "services_overview",
            "pricing",
            "duration",
        ]

    def test_policy_core_boundary_preserves_canonical_hours_location_service_fact_scope(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        canonical_payload = {
            "intent": "hours",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["hours", "services_overview", "location", "pricing"],
            "slots": {"service": "маникюр"},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.83,
            "reason": "user asks hours, service list, location, and manicure pricing",
            "goal": None,
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
            "capability": "hours",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(canonical_payload))
            result = route_llm_policy_core(
                "Вы сегодня работаете, какие услуги есть, сколько стоит маникюр и где находитесь?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "hours"
        assert set(result["payload"]["grounding_requirements"]["pack_refs"]) == {
            "hours",
            "location",
            "pricing",
            "services_overview",
        }

    def test_policy_core_boundary_trims_unasked_service_scope_from_hours_location_fact(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        overgrounded_payload = {
            "intent": "hours",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["hours", "services_overview", "location", "contact"],
            "slots": {},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.83,
            "reason": "user asks hours and location",
            "goal": None,
            "entity_refs": [],
            "referents": {},
            "subject_kind": "general",
            "capability": "hours",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(overgrounded_payload))
            result = route_llm_policy_core(
                "Вы сегодня работаете и где находитесь?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "hours"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "general"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["hours", "location"]

    def test_policy_core_boundary_preserves_hours_location_booking_followup_without_service(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        owner_payload = {
            "intent": "location",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["hours", "location"],
            "slots": {},
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.79,
            "reason": "user asks hours and location and also wants booking without grounded service",
            "goal": "booking",
            "entity_refs": [],
            "referents": {},
            "subject_kind": "general",
            "capability": "location",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(owner_payload))
            result = route_llm_policy_core(
                "Вы сегодня работаете, где вы находитесь, можно записаться?",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "location"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["hours", "location"]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "general"
        assert result["payload"]["goal"] == "booking"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "service_choice"
        assert result["payload"]["missing_information"]["next_question"] == "service"
        assert result["payload"]["missing_information"]["open_questions"] == ["service"]
        assert result["payload"]["missing_information"].get("pending_question_act") is None
        assert result["payload"]["missing_information"].get("pending_question_target") is None
        assert result["payload"]["missing_information"].get("active_question_relation") is None

    def test_policy_core_boundary_normalizes_hours_location_booking_followup_without_service(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        invalid_payload = {
            "intent": "booking",
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
            "confidence": 0.68,
            "reason": "user asks hours and location and wants to book without service",
            "goal": "booking",
            "entity_refs": [],
            "referents": {},
            "subject_kind": "general",
            "capability": "bookability",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "clarify_missing_subject",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(invalid_payload))
            result = route_llm_policy_core(
                "Вы сегодня работаете, где вы находитесь, хочу записаться.",
                memory_profile={},
                client_slug="demo_salon",
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.location"
        assert result["payload"]["intent"] == "hours"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["hours", "location"]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "general"
        assert result["payload"]["goal"] == "booking"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "service_choice"
        assert result["payload"]["missing_information"]["next_question"] == "service"
        assert result["payload"]["missing_information"]["open_questions"] == ["service"]
        assert result["payload"]["missing_information"].get("pending_question_act") is None
        assert result["payload"]["missing_information"].get("pending_question_target") is None
        assert result["payload"]["missing_information"].get("active_question_relation") is None

    def test_policy_core_accepts_mixed_first_turn_promotions_fact_with_booking_intent_alias(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["promotions", "location"],
            "slots": {},
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.61,
            "reason": "standalone_promotions_head_intent_with_side_requests",
            "goal": None,
            "entity_refs": [],
            "referents": {},
            "subject_kind": "general",
            "capability": "promotions",
            "temporal_scope": "none",
            "alternate_datetime": None,
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Есть скидки, хочу записаться и адрес, пожалуйста.",
                memory_profile={},
            )

        assert result["ok"] is True
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["promotions", "location"]
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "general"

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

    def test_focused_interrupt_empty_response_retry_keeps_strict_response_format(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        valid_payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["master"],
            "slots": {"service": "маникюр", "datetime": "на завтра в 18:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.71,
            "reason": "master_interrupt_for_grounded_service_and_name_progression",
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "context.message_grounding_hints.service",
                }
            },
            "subject_kind": "service",
            "capability": "master",
            "temporal_scope": "specific_time",
            "alternate_datetime": "на завтра в 18:00",
            "resolution_mode": "policy_fact",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }

        monkeypatch.setattr(
            "app.services.intent_service._policy_core_resolve_current_message_service_hint",
            lambda **_kwargs: "маникюр",
        )
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(""),
                DummyResponse(json.dumps(valid_payload)),
            ]
            result = route_llm_policy_core(
                "Кто делает маникюр?",
                client_slug="demo_salon",
                current_goal="booking",
                memory_summary=(
                    "user: На завтра в 18:00 есть время? assistant: На какую услугу "
                    "хотите записаться?"
                ),
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "reason": "collect:service",
                    },
                    "semantic_contract": {
                        "alternate_datetime": "на завтра в 18:00",
                        "capability": "bookability",
                        "contract_version": "semantic_contract.v1",
                        "resolution_mode": "clarify_missing_subject",
                        "subject_kind": "general",
                        "temporal_scope": "specific_time",
                    },
                    "slot_state": {"datetime": "на завтра в 18:00"},
                },
            )

        assert result["ok"] is True
        assert result["structured_output_enabled"] is True
        assert result["structured_output_fallback_used"] is True
        assert result["structured_output_fallback_reason"] == "response_format_empty_response"
        assert result["attempt_count"] == 2
        first_kwargs = mock_llm.return_value.generate.call_args_list[0].kwargs
        second_kwargs = mock_llm.return_value.generate.call_args_list[1].kwargs
        assert first_kwargs.get("response_format") == {"type": "json_object"}
        assert second_kwargs.get("response_format") == {"type": "json_object"}
        assert '"goal": "booking"' in second_kwargs["messages"][-1]["content"]

    def test_focused_interrupt_timeout_retry_stays_on_focused_owner_contract(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        valid_payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["master"],
            "slots": {"service": "маникюр", "datetime": "на завтра в 18:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.71,
            "reason": "master_interrupt_for_grounded_service_and_name_progression",
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "context.message_grounding_hints.service",
                }
            },
            "subject_kind": "service",
            "capability": "master",
            "temporal_scope": "specific_time",
            "alternate_datetime": "на завтра в 18:00",
            "resolution_mode": "policy_fact",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }

        monkeypatch.setattr(
            "app.services.intent_service._policy_core_resolve_current_message_service_hint",
            lambda **_kwargs: "маникюр",
        )
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                httpx.TimeoutException("timed out"),
                DummyResponse(json.dumps(valid_payload)),
            ]
            result = route_llm_policy_core(
                "Кто делает маникюр?",
                client_slug="demo_salon",
                current_goal="booking",
                memory_summary=(
                    "user: На завтра в 18:00 есть время? assistant: На какую услугу "
                    "хотите записаться?"
                ),
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "reason": "collect:service",
                    },
                    "semantic_contract": {
                        "alternate_datetime": "на завтра в 18:00",
                        "capability": "bookability",
                        "contract_version": "semantic_contract.v1",
                        "resolution_mode": "clarify_missing_subject",
                        "subject_kind": "general",
                        "temporal_scope": "specific_time",
                    },
                    "slot_state": {"datetime": "на завтра в 18:00"},
                },
            )

        assert result["ok"] is True
        assert result["attempt_count"] == 2
        assert result["compact_input_used"] is False
        assert result["compact_retry_used"] is False
        first_kwargs = mock_llm.return_value.generate.call_args_list[0].kwargs
        second_kwargs = mock_llm.return_value.generate.call_args_list[1].kwargs
        assert "LLM Policy Core Focused Contract" in first_kwargs["messages"][0]["content"]
        assert "LLM Policy Core Focused Contract" in second_kwargs["messages"][0]["content"]
        assert second_kwargs["timeout_seconds"] == intent_service_module.POLICY_CORE_TIMEOUT_SECONDS

    def test_focused_interrupt_double_empty_response_retries_with_contract_instruction_under_response_format(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        valid_payload = {
            "intent": "master_query",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["master"],
            "slots": {"service": "маникюр", "datetime": "на завтра в 18:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.71,
            "reason": "master_interrupt_for_grounded_service_and_name_progression",
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "context.message_grounding_hints.service",
                }
            },
            "subject_kind": "service",
            "capability": "master",
            "temporal_scope": "specific_time",
            "alternate_datetime": "на завтра в 18:00",
            "resolution_mode": "policy_fact",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }

        monkeypatch.setattr(
            "app.services.intent_service._policy_core_resolve_current_message_service_hint",
            lambda **_kwargs: "маникюр",
        )
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(""),
                DummyResponse(""),
                DummyResponse(json.dumps(valid_payload)),
            ]
            result = route_llm_policy_core(
                "Кто делает маникюр?",
                client_slug="demo_salon",
                current_goal="booking",
                memory_summary=(
                    "user: На завтра в 18:00 есть время? assistant: На какую услугу "
                    "хотите записаться?"
                ),
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "service_choice",
                        "next_question": "service",
                        "open_questions": ["service"],
                        "reason": "collect:service",
                    },
                    "semantic_contract": {
                        "alternate_datetime": "на завтра в 18:00",
                        "capability": "bookability",
                        "contract_version": "semantic_contract.v1",
                        "resolution_mode": "clarify_missing_subject",
                        "subject_kind": "general",
                        "temporal_scope": "specific_time",
                    },
                    "slot_state": {"datetime": "на завтра в 18:00"},
                },
            )

        assert result["ok"] is True
        assert result["structured_output_fallback_used"] is True
        assert result["structured_output_fallback_reason"] == "response_format_empty_response"
        assert result["attempt_count"] == 3
        first_kwargs = mock_llm.return_value.generate.call_args_list[0].kwargs
        second_kwargs = mock_llm.return_value.generate.call_args_list[1].kwargs
        third_kwargs = mock_llm.return_value.generate.call_args_list[2].kwargs
        assert isinstance(first_kwargs.get("response_format"), dict)
        assert isinstance(second_kwargs.get("response_format"), dict)
        assert "response_format" not in third_kwargs or third_kwargs.get("response_format") is None
        assert second_kwargs["messages"][-1]["role"] == "user"
        assert '"goal": "booking"' in second_kwargs["messages"][-1]["content"]
        assert '"active_question_relation": "generic_info_interrupt"' in second_kwargs["messages"][-1]["content"]
        assert third_kwargs["messages"][-1] == second_kwargs["messages"][-1]

    def test_booking_commit_timeout_retry_stays_on_focused_owner_contract(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        valid_payload = {
            "intent": "booking",
            "action": "fact",
            "tool_action_hint": "calendar.book_slot",
            "pack_refs": [],
            "slots": {
                "service": "маникюр",
                "datetime": "на завтра в 18:00",
                "name": "Амина",
                "phone": None,
            },
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.79,
            "reason": "user_name_provided_to_fill_requested_slot_and_datetime_already_carried",
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "customer": {
                    "value": "Амина",
                    "entity_id": None,
                    "entity_type": "customer",
                    "source_ref": "message",
                },
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "на завтра в 18:00",
            "resolution_mode": "live_calendar",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                httpx.TimeoutException("timed out"),
                DummyResponse(json.dumps(valid_payload)),
            ]
            result = route_llm_policy_core(
                "Меня зовут Амина.",
                client_slug="demo_salon",
                current_goal="booking",
                memory_summary=(
                    "user: На завтра в 18:00 есть время? assistant: На какую услугу "
                    "хотите записаться? user: Кто делает маникюр? assistant: Как вас зовут?"
                ),
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                        "pending_question_act": "fill_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "generic_info_interrupt",
                    },
                    "semantic_contract": {
                        "alternate_datetime": "на завтра в 18:00",
                        "capability": "bookability",
                        "contract_version": "semantic_contract.v1",
                        "resolution_mode": "policy_fact",
                        "subject_kind": "service",
                        "temporal_scope": "specific_time",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                    "slot_state": {
                        "service": "маникюр",
                        "datetime": "на завтра в 18:00",
                    },
                },
            )

        assert result["ok"] is True
        assert result["attempt_count"] == 2
        assert result["compact_input_used"] is False
        assert result["compact_retry_used"] is False
        first_kwargs = mock_llm.return_value.generate.call_args_list[0].kwargs
        second_kwargs = mock_llm.return_value.generate.call_args_list[1].kwargs
        assert "LLM Policy Core Focused Contract" in first_kwargs["messages"][0]["content"]
        assert "LLM Policy Core Focused Contract" in second_kwargs["messages"][0]["content"]
        assert second_kwargs["timeout_seconds"] == intent_service_module.POLICY_CORE_TIMEOUT_SECONDS

    def test_booking_commit_double_empty_response_falls_back_to_plain_retry_with_contract_instruction(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        valid_payload = {
            "intent": "booking",
            "action": "fact",
            "tool_action_hint": "calendar.book_slot",
            "pack_refs": [],
            "slots": {
                "service": "маникюр",
                "datetime": "на завтра в 18:00",
                "name": "Амина",
                "phone": None,
            },
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.79,
            "reason": "user_name_provided_to_fill_requested_slot_and_datetime_already_carried",
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "customer": {
                    "value": "Амина",
                    "entity_id": None,
                    "entity_type": "customer",
                    "source_ref": "message",
                },
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "на завтра в 18:00",
            "resolution_mode": "live_calendar",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(""),
                DummyResponse(""),
                DummyResponse(json.dumps(valid_payload)),
            ]
            result = route_llm_policy_core(
                "Меня зовут Амина.",
                client_slug="demo_salon",
                current_goal="booking",
                memory_summary=(
                    "user: На завтра в 18:00 есть время? assistant: На какую услугу "
                    "хотите записаться? user: Кто делает маникюр? assistant: Как вас зовут?"
                ),
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                        "pending_question_act": "fill_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "generic_info_interrupt",
                    },
                    "semantic_contract": {
                        "alternate_datetime": "на завтра в 18:00",
                        "capability": "bookability",
                        "contract_version": "semantic_contract.v1",
                        "resolution_mode": "policy_fact",
                        "subject_kind": "service",
                        "temporal_scope": "specific_time",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                    "slot_state": {
                        "service": "маникюр",
                        "datetime": "на завтра в 18:00",
                    },
                },
            )

        assert result["ok"] is True
        assert result["structured_output_fallback_used"] is True
        assert result["structured_output_fallback_reason"] == "response_format_empty_response"
        assert result["attempt_count"] == 3
        first_kwargs = mock_llm.return_value.generate.call_args_list[0].kwargs
        second_kwargs = mock_llm.return_value.generate.call_args_list[1].kwargs
        third_kwargs = mock_llm.return_value.generate.call_args_list[2].kwargs
        assert isinstance(first_kwargs.get("response_format"), dict)
        assert isinstance(second_kwargs.get("response_format"), dict)
        assert "response_format" not in third_kwargs or third_kwargs.get("response_format") is None
        assert second_kwargs["messages"][-1]["role"] == "user"
        assert '"tool_action_hint": "calendar.book_slot"' in second_kwargs["messages"][-1]["content"]
        assert '"resolution_mode": "live_calendar"' in second_kwargs["messages"][-1]["content"]
        assert third_kwargs["messages"][-1] == second_kwargs["messages"][-1]

    def test_booking_commit_empty_response_timeout_continues_to_plain_contract_retry(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        valid_payload = {
            "intent": "booking",
            "action": "fact",
            "tool_action_hint": "calendar.book_slot",
            "pack_refs": [],
            "slots": {
                "service": "маникюр",
                "datetime": "на завтра в 18:00",
                "name": "Амина",
                "phone": None,
            },
            "expected_reply_type": None,
            "next_question": None,
            "open_questions": [],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.79,
            "reason": "user_name_provided_to_fill_requested_slot_and_datetime_already_carried",
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "customer": {
                    "value": "Амина",
                    "entity_id": None,
                    "entity_type": "customer",
                    "source_ref": "message",
                },
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "на завтра в 18:00",
            "resolution_mode": "live_calendar",
            "pending_question_act": None,
            "pending_question_target": None,
            "active_question_relation": None,
            "resolver_id": None,
            "resolver_version": None,
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.side_effect = [
                DummyResponse(""),
                httpx.TimeoutException("timed out"),
                DummyResponse(json.dumps(valid_payload)),
            ]
            result = route_llm_policy_core(
                "Меня зовут Амина.",
                client_slug="demo_salon",
                current_goal="booking",
                memory_summary=(
                    "user: На завтра в 18:00 есть время? assistant: На какую услугу "
                    "хотите записаться? user: Кто делает маникюр? assistant: Как вас зовут?"
                ),
                memory_profile={
                    "active_goal": "booking",
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "next_question": "name",
                        "open_questions": ["name"],
                        "pending_question_act": "fill_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "generic_info_interrupt",
                    },
                    "semantic_contract": {
                        "alternate_datetime": "на завтра в 18:00",
                        "capability": "bookability",
                        "contract_version": "semantic_contract.v1",
                        "resolution_mode": "policy_fact",
                        "subject_kind": "service",
                        "temporal_scope": "specific_time",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                    },
                    "slot_state": {
                        "service": "маникюр",
                        "datetime": "на завтра в 18:00",
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["payload"]["tool_action_hint"] == "calendar.book_slot"
        assert result["structured_output_fallback_used"] is True
        assert result["structured_output_fallback_reason"] == "response_format_empty_response"
        assert mock_llm.return_value.generate.call_count == 3
        first_kwargs = mock_llm.return_value.generate.call_args_list[0].kwargs
        second_kwargs = mock_llm.return_value.generate.call_args_list[1].kwargs
        third_kwargs = mock_llm.return_value.generate.call_args_list[2].kwargs
        expected_retry_timeout = min(
            max(
                intent_service_module.POLICY_CORE_RETRY_TIMEOUT_SECONDS,
                intent_service_module.POLICY_CORE_MIN_TIMEOUT_SECONDS,
            ),
            intent_service_module.POLICY_CORE_TIMEOUT_SECONDS,
        )
        assert isinstance(first_kwargs.get("response_format"), dict)
        assert isinstance(second_kwargs.get("response_format"), dict)
        assert second_kwargs["timeout_seconds"] == expected_retry_timeout
        assert second_kwargs["messages"][-1]["role"] == "user"
        assert '"tool_action_hint": "calendar.book_slot"' in second_kwargs["messages"][-1]["content"]
        assert "response_format" not in third_kwargs or third_kwargs.get("response_format") is None
        assert third_kwargs["timeout_seconds"] == expected_retry_timeout
        assert third_kwargs["messages"][-1] == second_kwargs["messages"][-1]

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

    def test_route_policy_core_rejects_invalid_post_media_clock_time_fill_into_name_collect(
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

        assert result["ok"] is False
        assert result["error"] == "invalid_schema"
        assert (
            result["schema_error"]
            == "llm_policy_core_error:active_booking_time_fill_progression_required"
        )
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        assert result["attempt_count"] == 1
        assert result["payload"] is None
        assert result["binding"] is None
        assert mock_llm.return_value.generate.call_count == 1

    def test_route_policy_core_allows_canonical_post_media_clock_time_fill_into_name_collect(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "маникюр", "datetime": "завтра 17:45"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "risk_signals": [],
            "language": "ru",
            "confidence": 0.87,
            "reason": "post_media_explicit_clock_time_advances_to_customer_name",
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
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра 17:45",
            "resolution_mode": "direct",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "fill_requested_slot",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
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
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        missing = result["payload"]["missing_information"]
        assert missing["expected_reply_type"] == "name"
        assert missing["next_question"] == "name"
        assert missing["pending_question_act"] == "fill_requested_slot"
        assert missing["pending_question_target"] == "time"
        assert missing["active_question_relation"] == "fill_requested_slot"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "booking"
        assert result["payload"]["semantic_slots"]["datetime"] == "завтра 17:45"

    def test_route_policy_core_allows_month_date_with_time_preposition_fill_into_name_collect(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": [],
            "slots": {"service": "Брови", "datetime": "16 августа на 11:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.82,
            "reason": "user_filled_exact_date_and_time_for_active_booking_datetime_step",
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "Брови",
                    "entity_id": None,
                    "entity_type": "service",
                    "source_ref": "memory.semantic_contract",
                }
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "16 августа на 11:00",
            "resolution_mode": "direct",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "fill_requested_slot",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "16 августа на 11:00",
                client_slug="demo_salon",
                current_goal="booking",
                slot_state={"service": "Брови", "datetime": "завтра после работы"},
                memory_summary=(
                    "user: Мне нужно на брови завтра после работы assistant: Понял, завтра "
                    "после работы по услуге «Брови». Подскажите, пожалуйста, точное время."
                ),
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {
                        "service": "Брови",
                        "datetime": "завтра после работы",
                    },
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "reason": "collect:datetime",
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                    },
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "capability": "bookability",
                        "subject_kind": "booking",
                        "temporal_scope": "day",
                        "alternate_datetime": "завтра после работы",
                        "resolution_mode": "direct",
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "active_question_relation": "slot_constraint",
                        "referents": {
                            "service": {
                                "value": "Брови",
                                "source_ref": "decision_slots",
                            }
                        },
                    },
                },
            )

        assert intent_service_module._policy_core_booking_datetime_surface_is_executable(
            "16 августа на 11:00"
        )
        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is False
        assert result["boundary_normalization_used"] is False
        missing = result["payload"]["missing_information"]
        assert missing["expected_reply_type"] == "name"
        assert missing["next_question"] == "name"
        assert missing["pending_question_act"] == "fill_requested_slot"
        assert missing["pending_question_target"] == "time"
        assert missing["active_question_relation"] == "fill_requested_slot"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "booking"
        assert result["payload"]["semantic_slots"]["datetime"] == "16 августа на 11:00"

    def test_active_booking_time_fill_forced_fields_accept_datetime_correction_before_name(
        self,
    ):
        fields = intent_service_module._policy_core_active_booking_time_fill_forced_fields(
            {
                "active_goal": "booking",
                "slot_state": {
                    "service": "педикюр",
                    "datetime": "17 августа в 12:00",
                },
                "pending_question_contract": {
                    "expected_reply_type": "name",
                    "next_question": "name",
                    "open_questions": ["name"],
                    "pending_question_act": "fill_requested_slot",
                    "pending_question_target": "time",
                    "active_question_relation": "fill_requested_slot",
                },
                "semantic_contract": {
                    "contract_version": "semantic_contract.v1",
                    "capability": "bookability",
                    "subject_kind": "booking",
                    "temporal_scope": "specific_time",
                    "alternate_datetime": "17 августа в 12:00",
                    "resolution_mode": "direct",
                    "pending_question_act": "fill_requested_slot",
                    "pending_question_target": "time",
                    "active_question_relation": "fill_requested_slot",
                    "referents": {
                        "service": {
                            "value": "педикюр",
                            "entity_id": "svc:pedicure",
                            "entity_type": "service",
                            "source_ref": "carryover",
                        }
                    },
                },
            },
            current_message="Ой, не 17, давайте 18 августа в 12:00",
        )

        assert fields is not None
        assert fields["expected_reply_type"] == "name"
        assert fields["next_question"] == "name"
        assert fields["slots"] == {
            "service": "педикюр",
            "datetime": "18 августа в 12:00",
        }
        assert fields["alternate_datetime"] == "18 августа в 12:00"
        assert fields["pending_question_act"] == "fill_requested_slot"
        assert fields["active_question_relation"] == "fill_requested_slot"

    def test_route_policy_core_allows_post_media_specialist_duration_interrupt_without_repair(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "duration",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "pack_refs": ["duration"],
            "slots": {"service": None, "datetime": None, "name": None, "phone": None},
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": None,
            "language": None,
            "confidence": None,
            "reason": "duration_info_interrupt_during_active_booking_referent_followup_preserve_resume_contract",
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "specialist": {
                    "value": "Айдане",
                    "entity_id": None,
                    "entity_type": "specialist",
                    "source_ref": "user",
                },
            },
            "subject_kind": "specialist",
            "capability": "duration",
            "temporal_scope": "day",
            "alternate_datetime": "завтра вечером",
            "resolution_mode": "policy_fact",
            "pending_question_act": None,
            "pending_question_target": "specialist",
            "active_question_relation": "generic_info_interrupt",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "Сколько это длится?",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "завтра вечером"},
                memory_summary=(
                    "assistant: Понял, завтра вечером по услуге «маникюр». Подскажите, пожалуйста, "
                    "точное время. user: К Айдане. assistant: Хорошо, ориентир по мастеру — Айдане. "
                    "На какое время вам удобно? user: Могу прислать фото ногтей для примера. "
                    "assistant: Хорошо, ориентир по мастеру — Айдане. Пришлите, пожалуйста, "
                    "фото-пример желаемого результата. user: Сколько это длится?"
                ),
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр", "datetime": "завтра вечером"},
                    "pending_question_contract": {
                        "expected_reply_type": "media",
                        "next_question": "media",
                        "open_questions": ["media"],
                        "reason": "collect:media",
                        "pending_question_target": "specialist",
                        "active_question_relation": "referent_followup",
                    },
                    "resume_pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_target": "specialist",
                        "active_question_relation": "referent_followup",
                    },
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "capability": "consultation",
                        "subject_kind": "specialist",
                        "resolution_mode": "referent_followup",
                        "pending_question_target": "specialist",
                        "active_question_relation": "referent_followup",
                        "temporal_scope": "day",
                        "alternate_datetime": "завтра вечером",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            },
                            "specialist": {
                                "value": "Айдане",
                                "entity_type": "specialist",
                                "source_ref": "user",
                            },
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        assert result["binding"]["tool_action"] == "catalog.service_query"
        assert result["binding"]["tool_args"] == {"service_query": "маникюр"}
        assert result["payload"]["requested_outcome"] == "fact"
        assert result["payload"]["grounding_requirements"]["pack_refs"] == ["duration"]
        assert result["payload"]["grounding_requirements"]["alternate_datetime"] == "завтра вечером"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "specialist"
        assert result["payload"]["missing_information"]["expected_reply_type"] == "time"
        assert result["payload"]["missing_information"]["next_question"] == "datetime"
        assert result["payload"]["missing_information"]["open_questions"] == ["datetime"]
        assert result["payload"]["missing_information"]["pending_question_target"] == "specialist"
        assert result["payload"]["missing_information"]["active_question_relation"] == "generic_info_interrupt"

    def test_route_policy_core_advances_exact_time_after_specialist_info_interrupt_to_name_collect(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        payload = {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "pack_refs": None,
            "slots": {"service": "маникюр", "datetime": "завтра 18:00"},
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "needs_manager": False,
            "risk_signals": None,
            "language": "ru",
            "confidence": 0.78,
            "reason": "user_filled_exact_time_for_active_booking_datetime_step",
            "goal": "booking",
            "entity_refs": None,
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "specialist": {
                    "value": "Айдане",
                    "entity_id": None,
                    "entity_type": "specialist",
                    "source_ref": "user",
                },
            },
            "subject_kind": "booking",
            "capability": "bookability",
            "temporal_scope": "specific_time",
            "alternate_datetime": "завтра 18:00",
            "resolution_mode": "direct",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "fill_requested_slot",
            "resolver_id": None,
            "resolver_version": None,
        }
        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            mock_llm.return_value.generate.return_value = DummyResponse(json.dumps(payload))
            result = route_llm_policy_core(
                "В 18:00.",
                current_goal="booking",
                slot_state={"service": "маникюр", "datetime": "завтра вечером"},
                memory_summary=(
                    "assistant: Хорошо, ориентир по мастеру — Айдане. Пришлите, пожалуйста, "
                    "фото-пример желаемого результата. user: Сколько это длится? assistant: "
                    "маникюр — Обычно 45–90 минут, зависит от вида и покрытия. На какую дату и время вам удобно?"
                ),
                memory_profile={
                    "active_goal": "booking",
                    "slot_state": {"service": "маникюр", "datetime": "завтра вечером"},
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_target": "specialist",
                        "active_question_relation": "generic_info_interrupt",
                    },
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "capability": "duration",
                        "subject_kind": "specialist",
                        "resolution_mode": "policy_fact",
                        "pending_question_target": "specialist",
                        "active_question_relation": "generic_info_interrupt",
                        "temporal_scope": "day",
                        "alternate_datetime": "завтра вечером",
                        "referents": {
                            "service": {
                                "value": "маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            },
                            "specialist": {
                                "value": "Айдане",
                                "entity_type": "specialist",
                                "source_ref": "user",
                            },
                        },
                    },
                },
            )

        assert result["ok"] is True
        assert result["error"] is None
        assert result["contract_repair_retry_used"] is False
        assert result["contract_repair_reason"] is None
        missing = result["payload"]["missing_information"]
        assert missing["expected_reply_type"] == "name"
        assert missing["next_question"] == "name"
        assert missing["open_questions"] == ["name"]
        assert missing["pending_question_act"] == "fill_requested_slot"
        assert missing["pending_question_target"] == "time"
        assert missing["active_question_relation"] == "fill_requested_slot"
        assert result["payload"]["grounding_requirements"]["subject_kind"] == "booking"
        assert result["payload"]["semantic_slots"]["datetime"] == "завтра 18:00"

    def test_policy_core_response_format_is_strict_and_canonical(self):
        response_format = build_policy_core_response_format(["calendar.book_slot"])
        assert response_format["json_schema"]["strict"] is True
        schema = response_format["json_schema"]["schema"]
        assert schema["type"] == "object"
        assert schema["required"] == list(schema["properties"].keys())
        assert "check_booking" in schema["properties"]["intent"]["enum"]
        assert "verify_booking" in schema["properties"]["intent"]["enum"]
        assert "promotions" in schema["properties"]["intent"]["enum"]
        assert "thanks" in schema["properties"]["intent"]["enum"]
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

    def test_policy_core_response_format_supports_thanks_intent(self):
        response_format = build_policy_core_response_format(["info"])
        schema = response_format["json_schema"]["schema"]

        assert "thanks" in schema["properties"]["intent"]["enum"]

    def test_policy_core_response_format_can_force_canonical_interrupt_fields(self):
        response_format = build_policy_core_response_format(
            ["info", "collect", "handoff"],
            forced_field_values={
                "intent": "master_query",
                "action": "fact",
                "tool_action_hint": "info",
                "pack_refs": ["master"],
                "goal": "booking",
                "subject_kind": "service",
                "capability": "master",
                "temporal_scope": "specific_time",
                "alternate_datetime": "на завтра в 18:00",
                "resolution_mode": "policy_fact",
                "expected_reply_type": "name",
                "next_question": "name",
                "open_questions": ["name"],
                "pending_question_act": "fill_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "generic_info_interrupt",
                "needs_manager": False,
            },
        )
        properties = response_format["json_schema"]["schema"]["properties"]

        assert properties["intent"]["enum"] == ["master_query"]
        assert properties["action"]["enum"] == ["fact"]
        assert properties["tool_action_hint"]["enum"] == ["info"]
        assert properties["goal"]["enum"] == ["booking"]
        assert properties["subject_kind"]["enum"] == ["service"]
        assert properties["capability"]["enum"] == ["master"]
        assert properties["temporal_scope"]["enum"] == ["specific_time"]
        assert properties["alternate_datetime"]["enum"] == ["на завтра в 18:00"]
        assert properties["resolution_mode"]["enum"] == ["policy_fact"]
        assert properties["expected_reply_type"]["enum"] == ["name"]
        assert properties["next_question"]["enum"] == ["name"]
        assert properties["pending_question_act"]["enum"] == ["fill_requested_slot"]
        assert properties["pending_question_target"]["enum"] == ["time"]
        assert properties["active_question_relation"]["enum"] == ["generic_info_interrupt"]
        assert properties["needs_manager"]["enum"] == [False]
        assert properties["pack_refs"]["items"]["enum"] == ["master"]
        assert properties["pack_refs"]["minItems"] == 1
        assert properties["pack_refs"]["maxItems"] == 1
        assert properties["open_questions"]["items"]["enum"] == ["name"]
        assert properties["open_questions"]["minItems"] == 1
        assert properties["open_questions"]["maxItems"] == 1

    def test_policy_core_response_format_can_force_nested_booking_commit_slots(self):
        response_format = build_policy_core_response_format(
            ["calendar.book_slot"],
            forced_field_values={
                "intent": "booking",
                "action": "fact",
                "tool_action_hint": "calendar.book_slot",
                "slots": {
                    "service": "маникюр",
                    "datetime": "завтра в 18:00",
                    "name": {"type": "string", "minLength": 1},
                },
            },
        )
        properties = response_format["json_schema"]["schema"]["properties"]
        slots_schema = properties["slots"]

        assert properties["intent"]["enum"] == ["booking"]
        assert properties["action"]["enum"] == ["fact"]
        assert properties["tool_action_hint"]["enum"] == ["calendar.book_slot"]
        assert slots_schema["type"] == "object"
        assert slots_schema["required"] == ["service", "datetime", "name"]
        assert slots_schema["properties"]["service"]["enum"] == ["маникюр"]
        assert slots_schema["properties"]["datetime"]["enum"] == ["завтра в 18:00"]
        assert slots_schema["properties"]["name"]["type"] == "string"
        assert slots_schema["properties"]["name"]["minLength"] == 1

    def test_focused_contract_error_rejects_volatile_slot_mismatch(self):
        schema_error = _policy_core_focused_contract_error(
            {
                "slots": {
                    "service": "маникюр",
                    "datetime": "завтра в 18:00",
                    "name": "Дана",
                }
            },
            {
                "slots": {
                    "service": "маникюр",
                    "datetime": "завтра в 18:00",
                    "name": "Амина",
                }
            },
        )

        assert schema_error == "llm_policy_core_error:focused_contract_mismatch:slots.name"

    def test_focused_contract_error_allows_missing_empty_structural_fields(self):
        schema_error = _policy_core_focused_contract_error(
            {
                "intent": "booking",
                "action": "fact",
                "tool_action_hint": "calendar.book_slot",
                "slots": {
                    "service": "Брови",
                    "datetime": "16 августа на 11:00",
                    "name": "Гульнара",
                    "phone": "+77022334455",
                },
            },
            {
                "intent": "booking",
                "action": "fact",
                "tool_action_hint": "calendar.book_slot",
                "slots": {
                    "service": "Брови",
                    "datetime": "16 августа на 11:00",
                    "name": "Гульнара",
                    "phone": "+77022334455",
                },
                "pack_refs": [],
                "expected_reply_type": None,
                "next_question": None,
                "open_questions": [],
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
            },
        )

        assert schema_error is None

    def test_policy_core_vocabulary_snapshot_supports_promotions_intent(self):
        snapshot = build_policy_core_vocabulary_snapshot()

        assert "promotions" in snapshot.intents


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
