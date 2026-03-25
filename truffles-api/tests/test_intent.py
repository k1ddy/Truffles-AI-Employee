import json
import time
from unittest.mock import patch

import httpx

from app.core.intent_routing import (
    detect_controller_route_snapshot,
    detect_domain_routing_snapshot,
    detect_intent_routing_primitives,
    detect_policy_core_route_snapshot,
)
from app.services.intent_service import (
    DomainIntent,
    ESCALATION_INTENTS,
    REJECTION_INTENTS,
    Intent,
    _build_customer_name_hint_response_format,
    _build_policy_core_response_format,
    _build_service_query_hint_response_format,
    _build_specialist_hint_response_format,
    _load_policy_core_prompt,
    classify_intent,
    classify_domain_with_scores,
    extract_customer_name_hint_llm,
    get_dialogue_controller_override,
    get_domain_routing_override,
    get_intent_semantic_override,
    get_policy_core_override,
    extract_service_query_hint_llm,
    interpret_expected_reply,
    is_frustration_message,
    is_human_request_message,
    is_opt_out_message,
    is_rejection,
    route_dialogue_controller,
    route_llm_policy_core,
    should_escalate,
    use_dialogue_controller_override,
    use_domain_routing_override,
    use_intent_semantic_override,
    use_policy_core_override,
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


class TestIntentSemanticOverride:
    def test_override_matches_exact_normalized_text(self):
        override = {
            "normalized_text": "сколько стоит маникюр",
            "is_human_request": True,
            "intent": Intent.HUMAN_REQUEST.value,
        }

        with use_intent_semantic_override(override):
            assert get_intent_semantic_override() == override
            assert is_human_request_message("Сколько стоит маникюр") is True
            assert is_human_request_message("когда свободно") is False

    def test_override_resets_after_context_exit(self):
        with use_intent_semantic_override(
            {
                "normalized_text": "сколько стоит маникюр",
                "is_human_request": True,
                "intent": Intent.HUMAN_REQUEST.value,
            }
        ):
            assert get_intent_semantic_override() is not None

        assert get_intent_semantic_override() is None
        assert is_human_request_message("сколько стоит маникюр") is False

    def test_classify_intent_uses_override_without_llm(self):
        override = {
            "normalized_text": "сколько стоит маникюр",
            "is_human_request": False,
            "intent": Intent.GREETING.value,
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            with use_intent_semantic_override(override):
                assert classify_intent("Сколько стоит маникюр") == Intent.GREETING

        mock_llm.assert_not_called()

    def test_protective_flags_use_override_without_heuristic_match(self):
        override = {
            "normalized_text": "останови ответы",
            "is_opt_out": True,
            "is_frustration": False,
            "is_human_request": False,
            "intent": Intent.REJECTION.value,
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            with use_intent_semantic_override(override):
                assert is_opt_out_message("Останови ответы") is True
                assert is_frustration_message("Останови ответы") is False
                assert classify_intent("Останови ответы") == Intent.REJECTION

        mock_llm.assert_not_called()

    def test_frustration_flag_uses_override_without_heuristic_match(self):
        override = {
            "normalized_text": "это уже сломано",
            "is_opt_out": False,
            "is_frustration": True,
            "is_human_request": False,
            "intent": Intent.FRUSTRATION.value,
        }

        with patch("app.services.intent_service.get_llm_provider") as mock_llm:
            with use_intent_semantic_override(override):
                assert is_opt_out_message("Это уже сломано") is False
                assert is_frustration_message("Это уже сломано") is True
                assert classify_intent("Это уже сломано") == Intent.FRUSTRATION

        mock_llm.assert_not_called()


class TestIntentRoutingPrimitives:
    def test_detects_human_request_lexical_intent(self):
        primitives = detect_intent_routing_primitives("Хочу поговорить с менеджером")

        assert primitives is not None
        assert primitives.is_human_request is True
        assert primitives.lexical_intent == Intent.HUMAN_REQUEST

    def test_detects_greeting_lexical_intent(self):
        primitives = detect_intent_routing_primitives("Привет")

        assert primitives is not None
        assert primitives.is_greeting is True
        assert primitives.lexical_intent == Intent.GREETING

    def test_detects_opt_out_lexical_intent(self):
        primitives = detect_intent_routing_primitives("Отпишись")

        assert primitives is not None
        assert primitives.is_opt_out is True
        assert primitives.lexical_intent == Intent.REJECTION

    def test_detects_frustration_lexical_intent(self):
        primitives = detect_intent_routing_primitives("Заебал")

        assert primitives is not None
        assert primitives.is_frustration is True
        assert primitives.lexical_intent == Intent.FRUSTRATION

    def test_detects_domain_routing_snapshot(self):
        client_config = {
            "domain_router": {
                "anchors_in": ["маникюр"],
                "anchors_out": ["налоговая"],
            }
        }

        snapshot = detect_domain_routing_snapshot(
            "маникюр",
            client_config=client_config,
        )

        assert snapshot is not None
        assert snapshot.domain_intent == DomainIntent.IN_DOMAIN
        assert snapshot.in_score > snapshot.out_score


class TestDomainRoutingOverride:
    def test_override_matches_exact_normalized_text(self):
        override = {
            "normalized_text": "налоговая отчетность",
            "domain_intent": DomainIntent.OUT_OF_DOMAIN.value,
            "in_score": 0.1,
            "out_score": 0.9,
            "meta": {"out_hits": 1, "strict_in_hits": 0},
        }

        with use_domain_routing_override(override):
            assert get_domain_routing_override() == override
            result = classify_domain_with_scores("Налоговая отчетность", {"domain_router": {}})
            assert result[0] == DomainIntent.OUT_OF_DOMAIN
            assert result[2] == 0.9
            assert classify_domain_with_scores("маникюр", {"domain_router": {}})[0] == DomainIntent.UNKNOWN

    def test_override_resets_after_context_exit(self):
        with use_domain_routing_override(
            {
                "normalized_text": "налоговая отчетность",
                "domain_intent": DomainIntent.OUT_OF_DOMAIN.value,
                "in_score": 0.1,
                "out_score": 0.9,
                "meta": {"out_hits": 1, "strict_in_hits": 0},
            }
        ):
            assert get_domain_routing_override() is not None

        assert get_domain_routing_override() is None


class TestControllerRouteSnapshot:
    def test_detects_greeting_controller_route_snapshot(self):
        primitives = detect_intent_routing_primitives("Привет")

        snapshot = detect_controller_route_snapshot("Привет", primitives=primitives)

        assert snapshot is not None
        assert snapshot.controller_class == "greeting"
        assert snapshot.goal == "greeting"
        assert snapshot.intents == ("greeting",)

    def test_detects_strong_out_of_domain_controller_route_snapshot(self):
        domain_snapshot = detect_domain_routing_snapshot(
            "Налоговая отчетность",
            client_config={
                "domain_router": {
                    "anchors_in": ["маникюр"],
                    "anchors_out": ["налоговая"],
                }
            },
        )

        snapshot = detect_controller_route_snapshot(
            "Налоговая отчетность",
            domain_snapshot=domain_snapshot,
        )

        assert snapshot is not None
        assert snapshot.controller_class == "out_of_domain"
        assert snapshot.goal == "out_of_domain"
        assert snapshot.intents == ("out_of_domain",)


class TestPolicyCoreRouteSnapshot:
    def test_detects_human_request_policy_handoff_snapshot(self):
        primitives = detect_intent_routing_primitives("Хочу поговорить с менеджером")

        snapshot = detect_policy_core_route_snapshot(
            "Хочу поговорить с менеджером",
            primitives=primitives,
        )

        assert snapshot is not None
        assert snapshot.intent == "human_request"
        assert snapshot.action == "handoff"
        assert snapshot.tool_action == "handoff"

    def test_detects_frustration_policy_handoff_snapshot(self):
        primitives = detect_intent_routing_primitives("Заебал")

        snapshot = detect_policy_core_route_snapshot(
            "Заебал",
            primitives=primitives,
        )

        assert snapshot is not None
        assert snapshot.intent == "frustration"
        assert snapshot.action == "handoff"
        assert snapshot.tool_action == "handoff"

    def test_skips_opt_out_even_if_surface_is_hostile(self):
        primitives = detect_intent_routing_primitives("Отпишись и заткнись")

        snapshot = detect_policy_core_route_snapshot(
            "Отпишись и заткнись",
            primitives=primitives,
        )

        assert snapshot is None

    def test_detects_text_only_style_reference_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Я могу прислать фото своей прически?")

        snapshot = detect_policy_core_route_snapshot(
            "Я могу прислать фото своей прически?",
            primitives=primitives,
            has_media=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "style_reference"
        assert snapshot.action == "handoff"
        assert snapshot.tool_action == "handoff"
        assert snapshot.reason == "style_reference_text"
        assert snapshot.needs_manager is False

    def test_skips_style_reference_policy_snapshot_when_media_already_present(self):
        primitives = detect_intent_routing_primitives("Вот фото прически")

        snapshot = detect_policy_core_route_snapshot(
            "Вот фото прически",
            primitives=primitives,
            has_media=True,
        )

        assert snapshot is None

    def test_detects_booking_verification_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Проверьте, пожалуйста, мою запись")

        snapshot = detect_policy_core_route_snapshot(
            "Проверьте, пожалуйста, мою запись",
            primitives=primitives,
            has_media=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "check_booking"
        assert snapshot.action == "fact"
        assert snapshot.tool_action == "calendar.get_booking"
        assert snapshot.reason == "booking_verification_text"
        assert snapshot.goal == "booking"
        assert snapshot.needs_manager is False

    def test_skips_booking_verification_policy_snapshot_when_media_already_present(self):
        primitives = detect_intent_routing_primitives("Проверьте, пожалуйста, мою запись")

        snapshot = detect_policy_core_route_snapshot(
            "Проверьте, пожалуйста, мою запись",
            primitives=primitives,
            has_media=True,
        )

        assert snapshot is None

    def test_detects_services_overview_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Что вы предлагаете?")

        snapshot = detect_policy_core_route_snapshot(
            "Что вы предлагаете?",
            primitives=primitives,
            has_media=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "services_overview"
        assert snapshot.action == "fact"
        assert snapshot.tool_action == "catalog.service_query"
        assert snapshot.reason == "services_overview"
        assert snapshot.goal == "info"
        assert snapshot.needs_manager is False

    def test_skips_services_overview_policy_snapshot_when_media_already_present(self):
        primitives = detect_intent_routing_primitives("Что вы предлагаете?")

        snapshot = detect_policy_core_route_snapshot(
            "Что вы предлагаете?",
            primitives=primitives,
            has_media=True,
        )

        assert snapshot is None

    def test_detects_location_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Где вы находитесь?")

        snapshot = detect_policy_core_route_snapshot(
            "Где вы находитесь?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.intent == "info"
        assert snapshot.action == "fact"
        assert snapshot.tool_action == "catalog.location"
        assert snapshot.reason == "location_question"
        assert snapshot.goal == "info"
        assert snapshot.pack_refs == ("location",)
        assert snapshot.needs_manager is False

    def test_detects_parking_policy_snapshot_with_richer_pack_refs(self):
        primitives = detect_intent_routing_primitives("Парковка есть?")

        snapshot = detect_policy_core_route_snapshot(
            "Парковка есть?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.intent == "info"
        assert snapshot.action == "fact"
        assert snapshot.tool_action == "catalog.location"
        assert snapshot.reason == "parking_question"
        assert snapshot.goal == "info"
        assert snapshot.pack_refs == ("location", "parking")
        assert snapshot.needs_manager is False

    def test_skips_location_policy_snapshot_when_media_already_present(self):
        primitives = detect_intent_routing_primitives("Где вы находитесь?")

        snapshot = detect_policy_core_route_snapshot(
            "Где вы находитесь?",
            primitives=primitives,
            has_media=True,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_detects_hours_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Какие часы работы?")

        snapshot = detect_policy_core_route_snapshot(
            "Какие часы работы?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.intent == "hours"
        assert snapshot.action == "fact"
        assert snapshot.tool_action == "info"
        assert snapshot.reason == "hours_question"
        assert snapshot.goal == "info"
        assert snapshot.pack_refs == ("hours",)
        assert snapshot.capability == "hours"
        assert snapshot.needs_manager is False

    def test_skips_hours_policy_snapshot_when_media_already_present(self):
        primitives = detect_intent_routing_primitives("Какие часы работы?")

        snapshot = detect_policy_core_route_snapshot(
            "Какие часы работы?",
            primitives=primitives,
            has_media=True,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_skips_hours_policy_snapshot_for_location_mixed_query(self):
        primitives = detect_intent_routing_primitives("Где вы находитесь и до скольки работаете?")

        snapshot = detect_policy_core_route_snapshot(
            "Где вы находитесь и до скольки работаете?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.tool_action == "catalog.location"
        assert snapshot.pack_refs == ("location",)

    def test_detects_grounded_pricing_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Сколько стоит маникюр?")

        snapshot = detect_policy_core_route_snapshot(
            "Сколько стоит маникюр?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.intent == "info"
        assert snapshot.action == "fact"
        assert snapshot.tool_action == "catalog.service_query"
        assert snapshot.reason == "pricing_query"
        assert snapshot.goal == "booking"
        assert snapshot.tool_args == {"service_query": "Маникюр"}
        assert snapshot.pack_refs == ("pricing",)
        assert snapshot.capability == "pricing"
        assert snapshot.needs_manager is False

    def test_detects_active_booking_pricing_interrupt_snapshot_for_skolko_eto_stoit(self):
        primitives = detect_intent_routing_primitives("А сколько это стоит?")

        snapshot = detect_policy_core_route_snapshot(
            "А сколько это стоит?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="time",
            resume_reason="collect:datetime",
            active_service_referent="Маникюр",
            booking_active=True,
        )

        assert snapshot is not None
        assert snapshot.intent == "info"
        assert snapshot.action == "fact"
        assert snapshot.tool_action == "catalog.service_query"
        assert snapshot.reason == "pricing_query"
        assert snapshot.tool_args == {"service_query": "Маникюр"}
        assert snapshot.pack_refs == ("pricing",)

    def test_detects_pricing_collect_policy_snapshot_for_missing_service(self):
        primitives = detect_intent_routing_primitives("Сколько стоит?")

        snapshot = detect_policy_core_route_snapshot(
            "Сколько стоит?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.intent == "pricing"
        assert snapshot.action == "collect"
        assert snapshot.tool_action == "info"
        assert snapshot.reason == "need_service"
        assert snapshot.goal == "info"
        assert snapshot.tool_args == {}
        assert snapshot.pack_refs == ("pricing",)
        assert snapshot.capability == "pricing"
        assert snapshot.next_question == "service"
        assert snapshot.open_questions == ("service",)
        assert snapshot.subject_kind == "service"
        assert snapshot.resolution_mode == "clarify_missing_subject"
        assert snapshot.needs_manager is False

    def test_skips_pricing_collect_policy_snapshot_when_media_already_present(self):
        primitives = detect_intent_routing_primitives("Сколько стоит?")

        snapshot = detect_policy_core_route_snapshot(
            "Сколько стоит?",
            primitives=primitives,
            has_media=True,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_skips_pricing_collect_policy_snapshot_when_active_service_referent_exists(self):
        primitives = detect_intent_routing_primitives("Сколько стоит?")

        snapshot = detect_policy_core_route_snapshot(
            "Сколько стоит?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            has_active_service_referent=True,
        )

        assert snapshot is None

    def test_skips_grounded_pricing_policy_snapshot_when_media_already_present(self):
        primitives = detect_intent_routing_primitives("Сколько стоит маникюр?")

        snapshot = detect_policy_core_route_snapshot(
            "Сколько стоит маникюр?",
            primitives=primitives,
            has_media=True,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_skips_grounded_pricing_policy_snapshot_for_duration_mixed_query(self):
        primitives = detect_intent_routing_primitives("Сколько стоит и сколько длится маникюр?")

        snapshot = detect_policy_core_route_snapshot(
            "Сколько стоит и сколько длится маникюр?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_pricing_collect_policy_snapshot_yields_to_duration_mixed_query(self):
        primitives = detect_intent_routing_primitives("Сколько стоит и сколько длится?")

        snapshot = detect_policy_core_route_snapshot(
            "Сколько стоит и сколько длится?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_detects_duration_collect_policy_snapshot_for_missing_service(self):
        primitives = detect_intent_routing_primitives("Сколько длится?")

        snapshot = detect_policy_core_route_snapshot(
            "Сколько длится?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.intent == "duration"
        assert snapshot.action == "collect"
        assert snapshot.tool_action == "info"
        assert snapshot.reason == "need_service"
        assert snapshot.goal == "info"
        assert snapshot.tool_args == {}
        assert snapshot.pack_refs == ("duration",)
        assert snapshot.capability == "duration"
        assert snapshot.next_question == "service"
        assert snapshot.open_questions == ("service",)
        assert snapshot.subject_kind == "service"
        assert snapshot.resolution_mode == "clarify_missing_subject"
        assert snapshot.needs_manager is False

    def test_skips_duration_collect_policy_snapshot_when_media_already_present(self):
        primitives = detect_intent_routing_primitives("Сколько длится?")

        snapshot = detect_policy_core_route_snapshot(
            "Сколько длится?",
            primitives=primitives,
            has_media=True,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_skips_duration_collect_policy_snapshot_when_active_service_referent_exists(self):
        primitives = detect_intent_routing_primitives("Сколько длится?")

        snapshot = detect_policy_core_route_snapshot(
            "Сколько длится?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            has_active_service_referent=True,
        )

        assert snapshot is None

    def test_duration_collect_policy_snapshot_yields_to_pricing_mixed_query(self):
        primitives = detect_intent_routing_primitives("Сколько стоит и сколько длится?")

        snapshot = detect_policy_core_route_snapshot(
            "Сколько стоит и сколько длится?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_detects_bookability_time_collect_policy_snapshot_for_active_service_referent(self):
        primitives = detect_intent_routing_primitives("В какое время можно записаться?")

        snapshot = detect_policy_core_route_snapshot(
            "В какое время можно записаться?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            active_service_referent="Маникюр",
            booking_active=True,
        )

        assert snapshot is not None
        assert snapshot.intent == "booking"
        assert snapshot.action == "collect"
        assert snapshot.tool_action == "calendar.list_slots"
        assert snapshot.reason == "missing_temporal_scope"
        assert snapshot.goal == "booking"
        assert snapshot.tool_args == {"service_query": "Маникюр"}
        assert snapshot.slots == {"service": "Маникюр", "datetime": ""}
        assert snapshot.next_question == "datetime"
        assert snapshot.open_questions == ("datetime",)
        assert snapshot.capability == "bookability"
        assert snapshot.subject_kind == "service"
        assert snapshot.temporal_scope == "none"
        assert snapshot.resolution_mode == "clarify_missing_time"
        assert snapshot.pending_question_act == "ask_about_requested_slot"
        assert snapshot.pending_question_target == "time"
        assert snapshot.active_question_relation == "ask_about_requested_slot"
        assert snapshot.needs_manager is False

    def test_skips_bookability_time_collect_policy_snapshot_without_booking_active(self):
        primitives = detect_intent_routing_primitives("В какое время можно записаться?")

        snapshot = detect_policy_core_route_snapshot(
            "В какое время можно записаться?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            active_service_referent="Маникюр",
            booking_active=False,
        )

        assert snapshot is None

    def test_skips_bookability_time_collect_policy_snapshot_when_temporal_scope_present(self):
        primitives = detect_intent_routing_primitives("В какое время можно записаться завтра?")

        snapshot = detect_policy_core_route_snapshot(
            "В какое время можно записаться завтра?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            active_service_referent="Маникюр",
            booking_active=True,
        )

        assert snapshot is None

    def test_skips_bookability_time_collect_policy_snapshot_when_explicit_service_in_text(self):
        primitives = detect_intent_routing_primitives("На педикюр в какое время можно записаться?")

        snapshot = detect_policy_core_route_snapshot(
            "На педикюр в какое время можно записаться?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            active_service_referent="Маникюр",
            booking_active=True,
        )

        assert snapshot is None

    def test_detects_active_name_time_availability_followup_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("А есть ли свободные слоты на 15:00?")

        snapshot = detect_policy_core_route_snapshot(
            "А есть ли свободные слоты на 15:00?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="name",
            resume_reason="booking_time_availability_followup",
            active_service_referent="Маникюр",
            booking_active=True,
        )

        assert snapshot is not None
        assert snapshot.intent == "booking"
        assert snapshot.action == "collect"
        assert snapshot.tool_action == "collect"
        assert snapshot.reason == "booking_time_availability_followup"
        assert snapshot.goal == "booking"
        assert snapshot.slots == {
            "service": "Маникюр",
            "datetime": "15:00",
            "name": "",
        }
        assert snapshot.next_question == "name"
        assert snapshot.open_questions == ("name",)
        assert snapshot.subject_kind == "booking"
        assert snapshot.capability == "live_availability"
        assert snapshot.temporal_scope == "specific_time"
        assert snapshot.resolution_mode == "referent_followup"
        assert snapshot.pending_question_act == "ask_about_requested_slot"
        assert snapshot.pending_question_target == "time"
        assert snapshot.active_question_relation == "ask_about_requested_slot"
        assert snapshot.needs_manager is False

    def test_skips_active_name_time_availability_followup_policy_snapshot_without_resume_reason(self):
        primitives = detect_intent_routing_primitives("А есть ли свободные слоты на 15:00?")

        snapshot = detect_policy_core_route_snapshot(
            "А есть ли свободные слоты на 15:00?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="name",
            resume_reason="other_followup",
            active_service_referent="Маникюр",
            booking_active=True,
        )

        assert snapshot is None

    def test_skips_active_name_time_availability_followup_policy_snapshot_when_date_scope_present(self):
        primitives = detect_intent_routing_primitives("А есть ли свободные слоты завтра на 15:00?")

        snapshot = detect_policy_core_route_snapshot(
            "А есть ли свободные слоты завтра на 15:00?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="name",
            resume_reason="booking_time_availability_followup",
            active_service_referent="Маникюр",
            booking_active=True,
        )

        assert snapshot is None

    def test_detects_active_name_deictic_time_availability_followup_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("А есть ли у вас места в это время?")

        snapshot = detect_policy_core_route_snapshot(
            "А есть ли у вас места в это время?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="name",
            resume_reason="booking_prompt",
            active_service_referent="Маникюр",
            active_booking_time_token="15:00",
            booking_active=True,
        )

        assert snapshot is not None
        assert snapshot.intent == "booking"
        assert snapshot.action == "collect"
        assert snapshot.tool_action == "collect"
        assert snapshot.reason == "booking_time_availability_followup"
        assert snapshot.goal == "booking"
        assert snapshot.slots == {
            "service": "Маникюр",
            "datetime": "15:00",
            "name": "",
        }
        assert snapshot.next_question == "name"
        assert snapshot.open_questions == ("name",)
        assert snapshot.subject_kind == "booking"
        assert snapshot.capability == "live_availability"
        assert snapshot.temporal_scope == "specific_time"
        assert snapshot.resolution_mode == "referent_followup"
        assert snapshot.pending_question_act == "ask_about_requested_slot"
        assert snapshot.pending_question_target == "time"
        assert snapshot.active_question_relation == "ask_about_requested_slot"
        assert snapshot.needs_manager is False

    def test_skips_active_name_deictic_time_availability_followup_policy_snapshot_without_booking_time_token(
        self,
    ):
        primitives = detect_intent_routing_primitives("А есть ли у вас места в это время?")

        snapshot = detect_policy_core_route_snapshot(
            "А есть ли у вас места в это время?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="name",
            resume_reason="booking_prompt",
            active_service_referent="Маникюр",
            active_booking_time_token=None,
            booking_active=True,
        )

        assert snapshot is None

    def test_skips_active_name_deictic_time_availability_followup_policy_snapshot_when_explicit_time_supplied(
        self,
    ):
        primitives = detect_intent_routing_primitives("А есть ли у вас места на 16:00?")

        snapshot = detect_policy_core_route_snapshot(
            "А есть ли у вас места на 16:00?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="name",
            resume_reason="booking_prompt",
            active_service_referent="Маникюр",
            active_booking_time_token="15:00",
            booking_active=True,
        )

        assert snapshot is None

    def test_detects_active_name_relative_date_availability_followup_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("У вас есть свободные слоты на завтра?")

        snapshot = detect_policy_core_route_snapshot(
            "У вас есть свободные слоты на завтра?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="name",
            resume_reason="booking_prompt",
            active_service_referent="Маникюр",
            active_booking_time_token="15:00",
            booking_active=True,
        )

        assert snapshot is not None
        assert snapshot.intent == "booking"
        assert snapshot.action == "collect"
        assert snapshot.tool_action == "collect"
        assert snapshot.reason == "booking_time_availability_followup"
        assert snapshot.goal == "booking"
        assert snapshot.slots == {
            "service": "Маникюр",
            "datetime": "завтра",
            "name": "",
        }
        assert snapshot.next_question == "name"
        assert snapshot.open_questions == ("name",)
        assert snapshot.subject_kind == "booking"
        assert snapshot.capability == "bookability"
        assert snapshot.temporal_scope == "specific_time"
        assert snapshot.resolution_mode == "referent_followup"
        assert snapshot.pending_question_act == "ask_about_requested_slot"
        assert snapshot.pending_question_target == "time"
        assert snapshot.active_question_relation == "ask_about_requested_slot"
        assert snapshot.needs_manager is False

    def test_skips_active_name_relative_date_availability_followup_without_booking_time_token(
        self,
    ):
        primitives = detect_intent_routing_primitives("У вас есть свободные слоты на завтра?")

        snapshot = detect_policy_core_route_snapshot(
            "У вас есть свободные слоты на завтра?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="name",
            resume_reason="booking_prompt",
            active_service_referent="Маникюр",
            active_booking_time_token=None,
            booking_active=True,
        )

        assert snapshot is None

    def test_detects_active_name_relative_daypart_availability_followup_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("У вас есть свободные слоты на завтра вечером?")

        snapshot = detect_policy_core_route_snapshot(
            "У вас есть свободные слоты на завтра вечером?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="name",
            resume_reason="booking_prompt",
            active_service_referent="Маникюр",
            active_booking_time_token="15:00",
            booking_active=True,
        )

        assert snapshot is not None
        assert snapshot.intent == "booking"
        assert snapshot.action == "collect"
        assert snapshot.tool_action == "collect"
        assert snapshot.reason == "booking_time_availability_followup"
        assert snapshot.goal == "booking"
        assert snapshot.slots == {
            "service": "Маникюр",
            "datetime": "завтра вечером",
            "name": "",
        }
        assert snapshot.next_question == "name"
        assert snapshot.open_questions == ("name",)
        assert snapshot.subject_kind == "booking"
        assert snapshot.capability == "bookability"
        assert snapshot.temporal_scope == "specific_time"
        assert snapshot.resolution_mode == "referent_followup"
        assert snapshot.pending_question_act == "ask_about_requested_slot"
        assert snapshot.pending_question_target == "time"
        assert snapshot.active_question_relation == "ask_about_requested_slot"
        assert snapshot.needs_manager is False

    def test_skips_active_name_relative_daypart_availability_followup_without_booking_time_token(
        self,
    ):
        primitives = detect_intent_routing_primitives("У вас есть свободные слоты на завтра вечером?")

        snapshot = detect_policy_core_route_snapshot(
            "У вас есть свободные слоты на завтра вечером?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="name",
            resume_reason="booking_prompt",
            active_service_referent="Маникюр",
            active_booking_time_token=None,
            booking_active=True,
        )

        assert snapshot is None

    def test_skips_active_name_relative_daypart_availability_followup_when_explicit_time_supplied(
        self,
    ):
        primitives = detect_intent_routing_primitives(
            "У вас есть свободные слоты на завтра вечером в 18:00?"
        )

        snapshot = detect_policy_core_route_snapshot(
            "У вас есть свободные слоты на завтра вечером в 18:00?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="name",
            resume_reason="booking_prompt",
            active_service_referent="Маникюр",
            active_booking_time_token="15:00",
            booking_active=True,
        )

        assert snapshot is None

    def test_detects_specialist_date_range_availability_followup_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Какой мастер свободен на этой неделе?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер свободен на этой неделе?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="time",
            resume_reason="booking_prompt",
            active_service_referent="Маникюр",
            active_booking_time_token=None,
            booking_active=True,
        )

        assert snapshot is not None
        assert snapshot.intent == "booking"
        assert snapshot.action == "collect"
        assert snapshot.tool_action == "collect"
        assert snapshot.reason == "booking_specialist_availability_followup"
        assert snapshot.goal == "booking"
        assert snapshot.slots == {
            "service": "Маникюр",
            "datetime": "",
            "name": "",
        }
        assert snapshot.next_question == "datetime"
        assert snapshot.open_questions == ("datetime",)
        assert snapshot.subject_kind == "specialist"
        assert snapshot.capability == "live_availability"
        assert snapshot.temporal_scope == "date_range"
        assert snapshot.resolution_mode == "referent_followup"
        assert snapshot.pending_question_act == "ask_about_requested_slot"
        assert snapshot.pending_question_target == "specialist"
        assert snapshot.active_question_relation == "specialist_availability_followup"
        assert snapshot.needs_manager is False

    def test_specialist_date_range_availability_followup_falls_back_to_master_service_clarify_without_service_referent(
        self,
    ):
        primitives = detect_intent_routing_primitives("Какой мастер свободен на этой неделе?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер свободен на этой неделе?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="time",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            booking_active=True,
        )

        assert snapshot is not None
        assert snapshot.intent == "master_query"
        assert snapshot.action == "collect"
        assert snapshot.reason == "master_service_clarify"

    def test_specialist_date_range_availability_followup_falls_back_to_grounded_master_query_when_service_grounded_in_text(
        self,
    ):
        primitives = detect_intent_routing_primitives(
            "Какой мастер будет делать маникюр в субботу?"
        )

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер будет делать маникюр в субботу?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="time",
            resume_reason="booking_prompt",
            active_service_referent="Маникюр",
            active_booking_time_token=None,
            booking_active=True,
        )

        assert snapshot is not None
        assert snapshot.intent == "master_query"
        assert snapshot.action == "fact"
        assert snapshot.reason == "master_question"

    def test_detects_grounded_specialist_availability_followup_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("А какие мастера доступны?")

        snapshot = detect_policy_core_route_snapshot(
            "А какие мастера доступны?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="time",
            resume_reason="booking_prompt",
            active_service_referent="Маникюр",
            active_booking_time_token=None,
            active_booking_datetime_value="завтра",
            booking_active=True,
        )

        assert snapshot is not None
        assert snapshot.intent == "booking"
        assert snapshot.action == "collect"
        assert snapshot.tool_action == "collect"
        assert snapshot.reason == "booking_specialist_availability_followup"
        assert snapshot.goal == "booking"
        assert snapshot.slots == {
            "service": "Маникюр",
            "datetime": "завтра",
            "name": "",
        }
        assert snapshot.next_question == "name"
        assert snapshot.open_questions == ("name",)
        assert snapshot.subject_kind == "specialist"
        assert snapshot.capability == "live_availability"
        assert snapshot.temporal_scope == "specific_time"
        assert snapshot.resolution_mode == "referent_followup"
        assert snapshot.pending_question_act == "ask_about_requested_slot"
        assert snapshot.pending_question_target == "specialist"
        assert snapshot.active_question_relation == "specialist_availability_followup"
        assert snapshot.needs_manager is False

    def test_grounded_specialist_availability_followup_falls_back_to_master_service_clarify_without_active_booking_datetime(
        self,
    ):
        primitives = detect_intent_routing_primitives("А какие мастера доступны?")

        snapshot = detect_policy_core_route_snapshot(
            "А какие мастера доступны?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="time",
            resume_reason="booking_prompt",
            active_service_referent="Маникюр",
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=True,
        )

        assert snapshot is not None
        assert snapshot.intent == "master_query"
        assert snapshot.action == "collect"
        assert snapshot.reason == "master_service_clarify"

    def test_grounded_specialist_availability_followup_falls_back_to_grounded_master_query_when_service_grounded_in_text(
        self,
    ):
        primitives = detect_intent_routing_primitives("Какие мастера доступны по маникюру?")

        snapshot = detect_policy_core_route_snapshot(
            "Какие мастера доступны по маникюру?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="time",
            resume_reason="booking_prompt",
            active_service_referent="Маникюр",
            active_booking_time_token=None,
            active_booking_datetime_value="завтра",
            booking_active=True,
        )

        assert snapshot is not None
        assert snapshot.intent == "master_query"
        assert snapshot.action == "fact"
        assert snapshot.reason == "master_question"

    def test_detects_service_choice_specialist_day_followup_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Какой мастер будет делать маникюр в субботу?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер будет делать маникюр в субботу?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="service",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "info"
        assert snapshot.action == "collect"
        assert snapshot.tool_action == "collect"
        assert snapshot.reason == "day_followup"
        assert snapshot.goal == "info"
        assert snapshot.slots == {
            "service": "Маникюр",
            "datetime": "",
            "name": "",
        }
        assert snapshot.next_question == "datetime"
        assert snapshot.open_questions == ("datetime",)
        assert snapshot.subject_kind == "specialist"
        assert snapshot.capability == "live_availability"
        assert snapshot.temporal_scope == "specific_time"
        assert snapshot.resolution_mode == "clarify_missing_time"
        assert snapshot.pending_question_act == "ask_about_requested_slot"
        assert snapshot.pending_question_target == "specialist"
        assert snapshot.active_question_relation == "ask_about_requested_slot"
        assert snapshot.needs_manager is False

    def test_service_choice_specialist_day_followup_requires_service_reply_slot(self):
        primitives = detect_intent_routing_primitives("Какой мастер будет делать маникюр в субботу?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер будет делать маникюр в субботу?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="time",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "master_query"
        assert snapshot.action == "fact"
        assert snapshot.reason == "master_question"

    def test_detects_service_choice_specialist_daypart_followup_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Какой мастер будет делать маникюр завтра вечером?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер будет делать маникюр завтра вечером?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="service",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "info"
        assert snapshot.action == "collect"
        assert snapshot.tool_action == "collect"
        assert snapshot.reason == "daypart_followup"
        assert snapshot.goal == "info"
        assert snapshot.slots == {
            "service": "Маникюр",
            "datetime": "завтра вечером",
            "name": "",
        }
        assert snapshot.next_question == "datetime"
        assert snapshot.open_questions == ("datetime",)
        assert snapshot.subject_kind == "specialist"
        assert snapshot.capability == "live_availability"
        assert snapshot.temporal_scope == "specific_time"
        assert snapshot.resolution_mode == "clarify_missing_time"
        assert snapshot.pending_question_act == "ask_about_requested_slot"
        assert snapshot.pending_question_target == "specialist"
        assert snapshot.active_question_relation == "ask_about_requested_slot"
        assert snapshot.needs_manager is False

    def test_detects_service_choice_specialist_exact_time_followup_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Какой мастер будет делать маникюр завтра в 18:00?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер будет делать маникюр завтра в 18:00?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="service",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "booking"
        assert snapshot.action == "collect"
        assert snapshot.tool_action == "collect"
        assert snapshot.reason == "specialist_exact_time_followup"
        assert snapshot.goal == "booking"
        assert snapshot.slots == {
            "service": "Маникюр",
            "datetime": "завтра 18:00",
            "name": "",
        }
        assert snapshot.next_question == "name"
        assert snapshot.open_questions == ("name",)
        assert snapshot.subject_kind == "specialist"
        assert snapshot.capability == "live_availability"
        assert snapshot.temporal_scope == "specific_time"
        assert snapshot.resolution_mode == "referent_followup"
        assert snapshot.pending_question_act == "ask_about_requested_slot"
        assert snapshot.pending_question_target == "specialist"
        assert snapshot.active_question_relation == "specialist_availability_followup"
        assert snapshot.needs_manager is False

    def test_service_choice_specialist_exact_time_followup_requires_service_reply_slot(
        self,
    ):
        primitives = detect_intent_routing_primitives("Какой мастер будет делать маникюр завтра в 18:00?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер будет делать маникюр завтра в 18:00?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="time",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "master_query"
        assert snapshot.action == "fact"
        assert snapshot.reason == "master_question"

    def test_service_choice_specialist_exact_time_followup_yields_to_daypart_exact_time_fallback(
        self,
    ):
        primitives = detect_intent_routing_primitives(
            "Какой мастер будет делать маникюр завтра вечером в 18:00?"
        )

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер будет делать маникюр завтра вечером в 18:00?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="service",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "master_query"
        assert snapshot.action == "fact"
        assert snapshot.reason == "master_question"

    def test_service_choice_specialist_daypart_followup_requires_service_reply_slot(
        self,
    ):
        primitives = detect_intent_routing_primitives("Какой мастер будет делать маникюр завтра вечером?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер будет делать маникюр завтра вечером?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="time",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "master_query"
        assert snapshot.action == "fact"
        assert snapshot.reason == "master_question"

    def test_service_choice_specialist_daypart_followup_yields_to_weekend_bridge_for_weekend_hybrid(
        self,
    ):
        primitives = detect_intent_routing_primitives("Какой мастер будет делать маникюр на выходных вечером?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер будет делать маникюр на выходных вечером?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="service",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "info"
        assert snapshot.action == "collect"
        assert snapshot.reason == "weekend_followup"
        assert snapshot.temporal_scope == "weekend"

    def test_service_choice_specialist_daypart_followup_yields_to_master_query_with_exact_time(
        self,
    ):
        primitives = detect_intent_routing_primitives(
            "Какой мастер будет делать маникюр завтра вечером в 18:00?"
        )

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер будет делать маникюр завтра вечером в 18:00?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="service",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "master_query"
        assert snapshot.action == "fact"
        assert snapshot.reason == "master_question"

    def test_detects_service_choice_specialist_weekday_followup_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Какой мастер будет делать маникюр по будням?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер будет делать маникюр по будням?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="service",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "info"
        assert snapshot.action == "collect"
        assert snapshot.tool_action == "collect"
        assert snapshot.reason == "weekday_followup"
        assert snapshot.goal == "info"
        assert snapshot.slots == {
            "service": "Маникюр",
            "datetime": "",
            "name": "",
        }
        assert snapshot.next_question == "datetime"
        assert snapshot.open_questions == ("datetime",)
        assert snapshot.subject_kind == "specialist"
        assert snapshot.capability == "live_availability"
        assert snapshot.temporal_scope == "weekday"
        assert snapshot.resolution_mode == "clarify_missing_time"
        assert snapshot.pending_question_act == "ask_about_requested_slot"
        assert snapshot.pending_question_target == "specialist"
        assert snapshot.active_question_relation == "ask_about_requested_slot"
        assert snapshot.needs_manager is False

    def test_service_choice_specialist_weekday_followup_requires_service_reply_slot(self):
        primitives = detect_intent_routing_primitives("Какой мастер будет делать маникюр по будням?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер будет делать маникюр по будням?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="time",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "master_query"
        assert snapshot.action == "fact"
        assert snapshot.reason == "master_question"

    def test_service_choice_specialist_weekday_followup_specific_day_variant_uses_day_bridge(
        self,
    ):
        primitives = detect_intent_routing_primitives("Какой мастер будет делать маникюр во вторник?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер будет делать маникюр во вторник?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="service",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "info"
        assert snapshot.action == "collect"
        assert snapshot.reason == "day_followup"
        assert snapshot.temporal_scope == "specific_time"

    def test_detects_service_choice_specialist_weekend_followup_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Какой мастер будет делать маникюр на выходных?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер будет делать маникюр на выходных?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="service",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "info"
        assert snapshot.action == "collect"
        assert snapshot.tool_action == "collect"
        assert snapshot.reason == "weekend_followup"
        assert snapshot.goal == "info"
        assert snapshot.slots == {
            "service": "Маникюр",
            "datetime": "",
            "name": "",
        }
        assert snapshot.next_question == "datetime"
        assert snapshot.open_questions == ("datetime",)
        assert snapshot.subject_kind == "specialist"
        assert snapshot.capability == "live_availability"
        assert snapshot.temporal_scope == "weekend"
        assert snapshot.resolution_mode == "clarify_missing_time"
        assert snapshot.pending_question_act == "ask_about_requested_slot"
        assert snapshot.pending_question_target == "specialist"
        assert snapshot.active_question_relation == "ask_about_requested_slot"
        assert snapshot.needs_manager is False

    def test_service_choice_specialist_weekend_followup_requires_service_reply_slot(self):
        primitives = detect_intent_routing_primitives("Какой мастер будет делать маникюр на выходных?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер будет делать маникюр на выходных?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="time",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "hours"
        assert snapshot.action == "fact"
        assert snapshot.reason == "hours_question"

    def test_booking_prompt_service_followup_temporal_booking_request_defers_hours_snapshot(self):
        primitives = detect_intent_routing_primitives("Можно записаться на выходные?")

        snapshot = detect_policy_core_route_snapshot(
            "Можно записаться на выходные?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="service",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=True,
        )

        assert snapshot is None

    def test_booking_interrupt_service_followup_temporal_booking_request_defers_hours_snapshot(self):
        primitives = detect_intent_routing_primitives("Можно записаться на выходные?")

        snapshot = detect_policy_core_route_snapshot(
            "Можно записаться на выходные?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="service",
            resume_reason="booking_interrupt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=True,
        )

        assert snapshot is None

    def test_booking_interrupt_expected_service_followup_temporal_booking_request_defers_hours_snapshot(
        self,
    ):
        primitives = detect_intent_routing_primitives("Можно записаться на выходные?")

        snapshot = detect_policy_core_route_snapshot(
            "Можно записаться на выходные?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="service_choice",
            resume_reason="booking_interrupt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value="в субботу",
            booking_active=True,
        )

        assert snapshot is None

    def test_booking_interrupt_expected_time_slot_constraint_defers_hours_snapshot(self):
        primitives = detect_intent_routing_primitives("Важно, чтобы это было в выходные.")

        snapshot = detect_policy_core_route_snapshot(
            "Важно, чтобы это было в выходные.",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="time",
            resume_reason="booking_interrupt",
            active_service_referent="Маникюр",
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=True,
        )

        assert snapshot is None

    def test_booking_prompt_service_followup_explicit_hours_question_keeps_hours_snapshot(self):
        primitives = detect_intent_routing_primitives("А по выходным вы работаете?")

        snapshot = detect_policy_core_route_snapshot(
            "А по выходным вы работаете?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="service",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=True,
        )

        assert snapshot is not None
        assert snapshot.intent == "hours"
        assert snapshot.action == "fact"
        assert snapshot.reason == "hours_question"

    def test_service_choice_specialist_weekend_followup_specific_day_variant_uses_day_bridge(
        self,
    ):
        primitives = detect_intent_routing_primitives("Какой мастер будет делать маникюр в субботу?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер будет делать маникюр в субботу?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="service",
            resume_reason="booking_prompt",
            active_service_referent=None,
            active_booking_time_token=None,
            active_booking_datetime_value=None,
            booking_active=False,
        )

        assert snapshot is not None
        assert snapshot.intent == "info"
        assert snapshot.action == "collect"
        assert snapshot.reason == "day_followup"
        assert snapshot.temporal_scope == "specific_time"

    def test_detects_active_name_deictic_day_availability_followup_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("У вас есть свободные слоты на этот день?")

        snapshot = detect_policy_core_route_snapshot(
            "У вас есть свободные слоты на этот день?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="name",
            resume_reason="booking_prompt",
            active_service_referent="Маникюр",
            active_booking_time_token="03:00",
            booking_active=True,
        )

        assert snapshot is not None
        assert snapshot.intent == "booking"
        assert snapshot.action == "collect"
        assert snapshot.tool_action == "collect"
        assert snapshot.reason == "booking_time_availability_followup"
        assert snapshot.goal == "booking"
        assert snapshot.slots == {
            "service": "Маникюр",
            "datetime": "03:00",
            "name": "",
        }
        assert snapshot.next_question == "name"
        assert snapshot.open_questions == ("name",)
        assert snapshot.subject_kind == "booking"
        assert snapshot.capability == "bookability"
        assert snapshot.temporal_scope == "specific_time"
        assert snapshot.resolution_mode == "referent_followup"
        assert snapshot.pending_question_act == "ask_about_requested_slot"
        assert snapshot.pending_question_target == "time"
        assert snapshot.active_question_relation == "ask_about_requested_slot"
        assert snapshot.needs_manager is False

    def test_skips_active_name_deictic_day_availability_followup_policy_snapshot_without_booking_time_token(
        self,
    ):
        primitives = detect_intent_routing_primitives("У вас есть свободные слоты на этот день?")

        snapshot = detect_policy_core_route_snapshot(
            "У вас есть свободные слоты на этот день?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="name",
            resume_reason="booking_prompt",
            active_service_referent="Маникюр",
            active_booking_time_token=None,
            booking_active=True,
        )

        assert snapshot is None

    def test_skips_active_name_deictic_day_availability_followup_policy_snapshot_without_booking_prompt_reason(
        self,
    ):
        primitives = detect_intent_routing_primitives("У вас есть свободные слоты на этот день?")

        snapshot = detect_policy_core_route_snapshot(
            "У вас есть свободные слоты на этот день?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="name",
            resume_reason="other_followup",
            active_service_referent="Маникюр",
            active_booking_time_token="03:00",
            booking_active=True,
        )

        assert snapshot is None

    def test_detects_grounded_duration_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Сколько длится маникюр?")

        snapshot = detect_policy_core_route_snapshot(
            "Сколько длится маникюр?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.intent == "duration"
        assert snapshot.action == "fact"
        assert snapshot.tool_action == "catalog.service_query"
        assert snapshot.reason == "duration_info"
        assert snapshot.goal == "booking"
        assert snapshot.tool_args == {"service_query": "Маникюр"}
        assert snapshot.pack_refs == ("duration",)
        assert snapshot.capability == "duration"
        assert snapshot.needs_manager is False

    def test_detects_grounded_duration_policy_snapshot_for_vremya_na_service(self):
        primitives = detect_intent_routing_primitives(
            "Как вы оцениваете время на наращивание полигелем?"
        )

        snapshot = detect_policy_core_route_snapshot(
            "Как вы оцениваете время на наращивание полигелем?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
            reply_slot="service_choice",
            resume_reason="collect:service",
            booking_active=True,
        )

        assert snapshot is not None
        assert snapshot.intent == "duration"
        assert snapshot.action == "fact"
        assert snapshot.tool_action == "catalog.service_query"
        assert snapshot.reason == "duration_info"
        assert snapshot.tool_args == {"service_query": "Наращивание полигелем"}
        assert snapshot.pack_refs == ("duration",)

    def test_skips_grounded_duration_policy_snapshot_when_media_already_present(self):
        primitives = detect_intent_routing_primitives("Сколько длится маникюр?")

        snapshot = detect_policy_core_route_snapshot(
            "Сколько длится маникюр?",
            primitives=primitives,
            has_media=True,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_skips_grounded_duration_policy_snapshot_for_pricing_mixed_query(self):
        primitives = detect_intent_routing_primitives("Сколько длится и сколько стоит маникюр?")

        snapshot = detect_policy_core_route_snapshot(
            "Сколько длится и сколько стоит маникюр?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_detects_promotions_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Есть ли у вас акции?")

        snapshot = detect_policy_core_route_snapshot(
            "Есть ли у вас акции?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.intent == "promotions"
        assert snapshot.action == "fact"
        assert snapshot.tool_action == "info"
        assert snapshot.reason == "promotions_question"
        assert snapshot.goal == "info"
        assert snapshot.pack_refs == ("promotions",)
        assert snapshot.capability == "promotions"
        assert snapshot.needs_manager is False

    def test_detects_promotions_rules_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Скидки суммируются?")

        snapshot = detect_policy_core_route_snapshot(
            "Скидки суммируются?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.intent == "promotions_rules"
        assert snapshot.action == "fact"
        assert snapshot.tool_action == "info"
        assert snapshot.reason == "promotions_rules_question"
        assert snapshot.goal == "info"
        assert snapshot.pack_refs == ("promotions",)
        assert snapshot.capability == "promotions"
        assert snapshot.needs_manager is False

    def test_skips_promotions_policy_snapshot_when_media_already_present(self):
        primitives = detect_intent_routing_primitives("Есть ли у вас акции?")

        snapshot = detect_policy_core_route_snapshot(
            "Есть ли у вас акции?",
            primitives=primitives,
            has_media=True,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_skips_promotions_rules_policy_snapshot_when_media_already_present(self):
        primitives = detect_intent_routing_primitives("Скидки суммируются?")

        snapshot = detect_policy_core_route_snapshot(
            "Скидки суммируются?",
            primitives=primitives,
            has_media=True,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_promotions_policy_snapshot_yields_to_promotions_rules(self):
        primitives = detect_intent_routing_primitives("Скидки суммируются?")

        snapshot = detect_policy_core_route_snapshot(
            "Скидки суммируются?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.reason == "promotions_rules_question"

    def test_promotions_rules_policy_snapshot_yields_to_pricing_mixed_query(self):
        primitives = detect_intent_routing_primitives("Скидки суммируются и сколько стоит маникюр?")

        snapshot = detect_policy_core_route_snapshot(
            "Скидки суммируются и сколько стоит маникюр?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.reason == "pricing_query"

    def test_promotions_policy_snapshot_yields_to_pricing_mixed_query(self):
        primitives = detect_intent_routing_primitives("Есть ли скидки и сколько стоит маникюр?")

        snapshot = detect_policy_core_route_snapshot(
            "Есть ли скидки и сколько стоит маникюр?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.reason == "pricing_query"

    def test_detects_contact_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Какой у вас номер телефона?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой у вас номер телефона?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.intent == "contact"
        assert snapshot.action == "fact"
        assert snapshot.tool_action == "info"
        assert snapshot.reason == "contact_question"
        assert snapshot.goal == "info"
        assert snapshot.pack_refs == ("contact",)
        assert snapshot.capability is None
        assert snapshot.needs_manager is False

    def test_skips_contact_policy_snapshot_when_media_already_present(self):
        primitives = detect_intent_routing_primitives("Какой у вас номер телефона?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой у вас номер телефона?",
            primitives=primitives,
            has_media=True,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_skips_contact_policy_snapshot_for_integration_turn(self):
        primitives = detect_intent_routing_primitives("Есть интеграция с WhatsApp?")

        snapshot = detect_policy_core_route_snapshot(
            "Есть интеграция с WhatsApp?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_skips_contact_policy_snapshot_for_raw_phone_collection_payload(self):
        primitives = detect_intent_routing_primitives("Мой номер телефона +77001234567")

        snapshot = detect_policy_core_route_snapshot(
            "Мой номер телефона +77001234567",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_detects_portfolio_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Покажите примеры работ по маникюру")

        snapshot = detect_policy_core_route_snapshot(
            "Покажите примеры работ по маникюру",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.intent == "portfolio"
        assert snapshot.action == "fact"
        assert snapshot.tool_action == "catalog.portfolio"
        assert snapshot.reason == "portfolio_question"
        assert snapshot.goal == "info"
        assert snapshot.tool_args == {"service_query": "Маникюр"}
        assert snapshot.pack_refs == ("portfolio",)
        assert snapshot.capability == "portfolio"
        assert snapshot.needs_manager is False

    def test_skips_portfolio_policy_snapshot_when_media_already_present(self):
        primitives = detect_intent_routing_primitives("Покажите примеры работ по маникюру")

        snapshot = detect_policy_core_route_snapshot(
            "Покажите примеры работ по маникюру",
            primitives=primitives,
            has_media=True,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_portfolio_policy_snapshot_keeps_style_reference_precedence(self):
        primitives = detect_intent_routing_primitives("Хочу как на фото")

        snapshot = detect_policy_core_route_snapshot(
            "Хочу как на фото",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.intent == "style_reference"
        assert snapshot.reason == "style_reference_text"

    def test_portfolio_policy_snapshot_yields_to_pricing_mixed_query(self):
        primitives = detect_intent_routing_primitives("Покажите примеры работ по маникюру и сколько стоит маникюр?")

        snapshot = detect_policy_core_route_snapshot(
            "Покажите примеры работ по маникюру и сколько стоит маникюр?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.reason == "pricing_query"

    def test_detects_grounded_master_query_policy_snapshot(self):
        primitives = detect_intent_routing_primitives("Какие мастера делают маникюр?")

        snapshot = detect_policy_core_route_snapshot(
            "Какие мастера делают маникюр?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.intent == "master_query"
        assert snapshot.action == "fact"
        assert snapshot.tool_action == "catalog.service_query"
        assert snapshot.reason == "master_question"
        assert snapshot.goal == "info"
        assert snapshot.tool_args == {"service_query": "Маникюр"}
        assert snapshot.pack_refs == ("master",)
        assert snapshot.capability is None
        assert snapshot.needs_manager is False

    def test_skips_grounded_master_query_policy_snapshot_when_media_already_present(self):
        primitives = detect_intent_routing_primitives("Какие мастера делают маникюр?")

        snapshot = detect_policy_core_route_snapshot(
            "Какие мастера делают маникюр?",
            primitives=primitives,
            has_media=True,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_detects_master_query_collect_policy_snapshot_for_missing_service(self):
        primitives = detect_intent_routing_primitives("Какой мастер можете предложить?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер можете предложить?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.intent == "master_query"
        assert snapshot.action == "collect"
        assert snapshot.tool_action == "collect"
        assert snapshot.reason == "master_service_clarify"
        assert snapshot.goal == "info"
        assert snapshot.pack_refs == ("master",)
        assert snapshot.next_question == "service"
        assert snapshot.open_questions == ("service",)
        assert snapshot.subject_kind == "service"
        assert snapshot.resolution_mode == "clarify_missing_subject"
        assert snapshot.capability is None
        assert snapshot.needs_manager is False

    def test_skips_master_query_collect_policy_snapshot_when_media_already_present(self):
        primitives = detect_intent_routing_primitives("Какой мастер можете предложить?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер можете предложить?",
            primitives=primitives,
            has_media=True,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_skips_grounded_master_query_policy_snapshot_for_named_master_turn(self):
        primitives = detect_intent_routing_primitives("Алия по маникюру принимает?")

        snapshot = detect_policy_core_route_snapshot(
            "Алия по маникюру принимает?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is None

    def test_grounded_master_query_policy_snapshot_yields_to_pricing_mixed_query(self):
        primitives = detect_intent_routing_primitives("Какие мастера делают маникюр и сколько стоит маникюр?")

        snapshot = detect_policy_core_route_snapshot(
            "Какие мастера делают маникюр и сколько стоит маникюр?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is not None
        assert snapshot.reason == "pricing_query"

    def test_master_query_collect_policy_snapshot_yields_to_pricing_mixed_query(self):
        primitives = detect_intent_routing_primitives("Какой мастер можете предложить и сколько стоит?")

        snapshot = detect_policy_core_route_snapshot(
            "Какой мастер можете предложить и сколько стоит?",
            primitives=primitives,
            has_media=False,
            client_slug="demo_salon",
        )

        assert snapshot is None


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


class TestDialogueControllerOverride:
    def test_route_dialogue_controller_uses_override_without_llm(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        override = {
            "normalized_text": "привет",
            "class": "greeting",
            "goal": "greeting",
            "intents": ["greeting"],
            "confidence": 0.95,
            "reason": "ingress_lexical_greeting",
        }
        with use_dialogue_controller_override(override):
            with patch("app.services.intent_service.get_llm_provider") as mock_llm:
                result = route_dialogue_controller("Привет")

        assert result["ok"] is True
        assert result["error"] is None
        assert result["payload"]["class"] == "greeting"
        assert result["payload"]["goal"] == "greeting"
        assert result["payload"]["controller_error"] == "none"
        mock_llm.assert_not_called()

    def test_dialogue_controller_override_resets_after_context_exit(self):
        override = {
            "normalized_text": "привет",
            "class": "greeting",
            "goal": "greeting",
            "intents": ["greeting"],
            "confidence": 0.95,
            "reason": "ingress_lexical_greeting",
        }
        with use_dialogue_controller_override(override):
            assert get_dialogue_controller_override() is not None

        assert get_dialogue_controller_override() is None


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


class TestPolicyCoreOverride:
    def test_route_llm_policy_core_uses_override_without_llm(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "")
        override = {
            "normalized_text": "хочу поговорить с менеджером",
            "intent": "human_request",
            "action": "handoff",
            "tool_action": "handoff",
            "tool_args": {},
            "pack_refs": [],
            "slots": {},
            "open_questions": [],
            "needs_manager": True,
            "risk_signals": [],
            "confidence": 0.98,
            "reason": "ingress_explicit_human_request",
            "goal": "handoff",
            "entity_refs": [],
            "resolver_id": "consultant_core_ingress_override",
            "resolver_version": "2026-03-16",
        }
        with use_policy_core_override(override):
            with patch("app.services.intent_service.get_llm_provider") as mock_llm:
                result = route_llm_policy_core("Хочу поговорить с менеджером")

        assert result["ok"] is True
        assert result["error"] is None
        assert result["attempted"] is False
        assert result["payload"]["intent"] == "human_request"
        assert result["payload"]["action"] == "handoff"
        assert result["payload"]["tool_action"] == "handoff"
        assert result["payload"]["needs_manager"] is True
        mock_llm.assert_not_called()

    def test_policy_core_override_resets_after_context_exit(self):
        override = {
            "normalized_text": "хочу поговорить с менеджером",
            "intent": "human_request",
            "action": "handoff",
            "tool_action": "handoff",
            "tool_args": {},
            "pack_refs": [],
            "slots": {},
            "open_questions": [],
            "needs_manager": True,
            "risk_signals": [],
            "confidence": 0.98,
            "reason": "ingress_explicit_human_request",
            "goal": "handoff",
            "entity_refs": [],
            "resolver_id": "consultant_core_ingress_override",
            "resolver_version": "2026-03-16",
        }
        with use_policy_core_override(override):
            assert get_policy_core_override() is not None

        assert get_policy_core_override() is None


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

    def test_policy_core_respects_explicit_max_tokens_override(self, monkeypatch):
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
        assert result["payload"]["pending_question_act"] == "ask_about_requested_slot"
        assert result["payload"]["pending_question_target"] == "time"
        assert result["payload"]["active_question_relation"] == "ask_about_requested_slot"

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
        assert result["payload"]["pending_question_act"] == "slot_compare"
        assert result["payload"]["pending_question_target"] == "time"
        assert result["payload"]["active_question_relation"] == "slot_compare"

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
        assert result["payload"]["subject_kind"] == "specialist"
        assert result["payload"]["capability"] == "live_availability"
        assert result["payload"]["temporal_scope"] == "date_range"
        assert result["payload"]["pending_question_act"] == "ask_about_requested_slot"
        assert result["payload"]["pending_question_target"] == "specialist"
        assert (
            result["payload"]["active_question_relation"]
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
        assert result["payload"]["subject_kind"] == "specialist"
        assert result["payload"]["capability"] == "live_availability"
        assert result["payload"]["temporal_scope"] == "specific_time"
        assert result["payload"]["next_question"] == "name"
        assert result["payload"]["open_questions"] == ["name"]
        assert result["payload"]["pending_question_act"] == "ask_about_requested_slot"
        assert result["payload"]["pending_question_target"] == "specialist"
        assert (
            result["payload"]["active_question_relation"]
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
        assert result["payload"]["subject_kind"] == "booking"
        assert result["payload"]["capability"] == "live_availability"
        assert result["payload"]["temporal_scope"] == "specific_time"
        assert result["payload"]["next_question"] == "name"
        assert result["payload"]["open_questions"] == ["name"]
        assert result["payload"]["pending_question_act"] == "ask_about_requested_slot"
        assert result["payload"]["pending_question_target"] == "time"
        assert result["payload"]["active_question_relation"] == "ask_about_requested_slot"

    def test_policy_core_prompt_free_slots_question_keeps_pending_time_contract(self):
        prompt = _load_policy_core_prompt()

        assert "Когда у вас есть свободные слоты?" in prompt
        assert "Не используй `calendar.list_slots` без `temporal_scope`" in prompt
        assert '`pending_question_act="ask_about_requested_slot"`' in prompt
        assert '`pending_question_target="time"`' in prompt
        assert '`active_question_relation="ask_about_requested_slot"`' in prompt
        assert "Какой мастер свободен на этой неделе?" in prompt
        assert "А какие мастера доступны?" in prompt
        assert "А есть ли свободные слоты на 15:00?" in prompt
        assert '`active_question_relation="specialist_availability_followup"`' in prompt
        assert '`next_question="name"`' in prompt
        assert '`subject_kind="booking"`' in prompt
        assert "alternate-time availability follow-up" in prompt

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
        assert "pending_question_act" in schema["properties"]
        assert "pending_question_target" in schema["properties"]
        assert "active_question_relation" in schema["properties"]
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
