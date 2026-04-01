from app.routers.webhook import decision as decision_router
from app.schemas.intent import validate_llm_plan_output, validate_llm_policy_core_output


def test_validate_llm_policy_core_output_valid():
    payload = {
        "intent": "pricing",
        "action": "fact",
        "tool_action": "info",
        "tool_args": {"service_query": "маникюр"},
        "pack_refs": ["pricing"],
        "slots": {"service": "маникюр"},
        "next_question": "service",
        "open_questions": ["service"],
        "needs_manager": False,
        "risk_signals": ["discounts"],
        "language": "ru",
        "confidence": 0.7,
        "reason": "pricing",
        "goal": "info",
        "entity_refs": [{"entity_id": "svc:manicure", "entity_type": "service"}],
        "resolver_id": "llm_policy_core",
        "resolver_version": "v1",
    }

    contract, error = validate_llm_policy_core_output(payload)

    assert error is None
    assert contract is not None
    assert contract.action == "fact"
    assert contract.tool_action_hint == "info"
    assert contract.resolver_id == "llm_policy_core"
    assert contract.resolver_version == "v1"
    assert contract.entity_refs and contract.entity_refs[0].get("entity_id") == "svc:manicure"


def test_validate_llm_policy_core_output_accepts_semantic_envelope_fields():
    payload = {
        "intent": "hours",
        "action": "fact",
        "tool_action": "info",
        "tool_args": {},
        "pack_refs": ["hours"],
        "slots": {"service": "маникюр"},
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "confidence": 0.84,
        "entity_refs": [{"entity_id": "svc:manicure", "entity_type": "service"}],
        "subject_kind": "service",
        "capability": "hours",
        "temporal_scope": "weekend",
        "resolution_mode": "referent_followup",
        "resolver_id": "llm_policy_core",
        "resolver_version": "v1",
    }

    contract, error = validate_llm_policy_core_output(payload)

    assert error is None
    assert contract is not None
    assert contract.subject_kind == "service"
    assert contract.capability == "hours"
    assert contract.temporal_scope == "weekend"
    assert contract.resolution_mode == "referent_followup"


def test_validate_llm_policy_core_output_accepts_sparse_location_projection():
    payload = {
        "intent": "location",
        "action": "fact",
        "tool_action": "catalog.location",
        "tool_args": {},
        "pack_refs": ["location"],
        "slots": {},
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "confidence": 0.72,
        "reason": "location_interrupt",
        "goal": "info",
        "entity_refs": [],
        "referents": {},
        "subject_kind": "branch",
        "capability": "location",
        "temporal_scope": "none",
        "resolution_mode": "direct",
        "resolver_id": "llm_policy_core",
        "resolver_version": "v1",
    }

    contract, error = validate_llm_policy_core_output(payload)

    assert error is None
    assert contract is not None
    assert contract.tool_action_hint == "catalog.location"
    assert contract.referents == {}


def test_validate_llm_policy_core_output_accepts_sparse_booking_collect_projection():
    payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "collect",
        "tool_args": {},
        "pack_refs": [],
        "slots": {"service": "маникюр"},
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "needs_manager": False,
        "risk_signals": [],
        "confidence": 0.88,
        "reason": "collect:datetime",
        "goal": "booking",
        "entity_refs": [
            {
                "entity_id": "svc:manicure",
                "entity_type": "service",
                "value": "маникюр",
                "source_ref": "message",
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
        "capability": "bookability",
        "temporal_scope": "specific_time",
        "resolution_mode": "clarify_missing_time",
        "resolver_id": "llm_policy_core",
        "resolver_version": "v1",
    }

    contract, error = validate_llm_policy_core_output(payload)

    assert error is None
    assert contract is not None
    assert contract.slots == {"service": "маникюр"}
    assert contract.next_question == "datetime"
    assert contract.referents["service"]["entity_id"] == "svc:manicure"


def test_validate_llm_policy_core_output_normalizes_nullable_confidence():
    payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "collect",
        "tool_args": {},
        "pack_refs": [],
        "slots": {"service": "маникюр"},
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "needs_manager": False,
        "risk_signals": [],
        "confidence": None,
        "reason": "collect:datetime",
    }

    contract, error = validate_llm_policy_core_output(payload)

    assert error is None
    assert contract is not None
    assert contract.confidence == 0.0


def test_validate_llm_policy_core_output_invalid():
    payload = {"action": "", "tool_action": "info", "slots": {}, "confidence": 1.2}

    contract, error = validate_llm_policy_core_output(payload)

    assert contract is None
    assert error is not None


def test_validate_llm_policy_core_output_ignores_legacy_calendar_tool_args():
    payload = {
        "intent": "booking",
        "action": "fact",
        "tool_action": "calendar.book_slot",
        "tool_args": {"service_query": "маникюр", "start_at": "2026-02-17T13:00:00", "foo": "bar"},
        "pack_refs": [],
        "slots": {"service": "маникюр", "datetime": "2026-02-17 13:00", "name": "Алия"},
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "confidence": 0.9,
    }

    contract, error = validate_llm_policy_core_output(payload)

    assert error is None
    assert contract is not None
    assert contract.tool_action_hint == "calendar.book_slot"


def test_validate_llm_policy_core_output_ignores_legacy_catalog_tool_args_shape():
    payload = {
        "intent": "location",
        "action": "fact",
        "tool_action": "catalog.location",
        "tool_args": {"info_refs": "parking"},
        "pack_refs": ["location"],
        "slots": {},
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "confidence": 0.9,
    }

    contract, error = validate_llm_policy_core_output(payload)

    assert error is None
    assert contract is not None
    assert contract.tool_action_hint == "catalog.location"


def test_validate_llm_policy_core_output_accepts_master_query_fact_with_service():
    payload = {
        "intent": "master_query",
        "action": "fact",
        "tool_action": "catalog.service_query",
        "tool_args": {"service_query": "маникюр"},
        "pack_refs": ["master"],
        "slots": {"service": "маникюр"},
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "confidence": 0.91,
    }

    contract, error = validate_llm_policy_core_output(payload)

    assert error is None
    assert contract is not None
    assert contract.intent == "master_query"
    assert contract.tool_action_hint == "catalog.service_query"
    assert contract.slots.get("service") == "маникюр"


def test_validate_llm_policy_core_output_rejects_master_query_fact_without_service():
    payload = {
        "intent": "master_query",
        "action": "fact",
        "tool_action": "info",
        "tool_args": {},
        "pack_refs": ["master"],
        "slots": {"service": ""},
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "confidence": 0.82,
    }

    contract, error = validate_llm_policy_core_output(payload)

    assert contract is None
    assert error is not None
    assert "master_query_service_required" in error


def test_validate_llm_policy_core_output_accepts_master_query_collect_service_clarify():
    payload = {
        "intent": "master_query",
        "action": "collect",
        "tool_action": "collect",
        "tool_args": {},
        "pack_refs": [],
        "slots": {"service": ""},
        "next_question": "service",
        "open_questions": ["service"],
        "needs_manager": False,
        "risk_signals": [],
        "confidence": 0.76,
    }

    contract, error = validate_llm_policy_core_output(payload)

    assert error is None
    assert contract is not None
    assert contract.action == "collect"
    assert contract.next_question == "service"


def test_validate_llm_policy_core_output_normalizes_legacy_master_intent_alias():
    payload = {
        "intent": "master",
        "action": "fact",
        "tool_action": "info",
        "tool_args": {"service_query": "стрижка"},
        "pack_refs": ["master"],
        "slots": {"service": "стрижка"},
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "confidence": 0.88,
    }

    contract, error = validate_llm_policy_core_output(payload)

    assert error is None
    assert contract is not None
    assert contract.intent == "master_query"


def test_validate_llm_plan_output_rejects_invalid_tool_args_shape():
    payload = {
        "outcome": "fact",
        "tool_action": "catalog.location",
        "tool_args": {"info_refs": "parking"},
        "confidence": 0.8,
    }

    contract, error = validate_llm_plan_output(payload)

    assert contract is None
    assert error is not None
    assert "tool_args_type_invalid:info_refs" in error


def test_low_confidence_allowlist_includes_reschedule():
    assert "calendar.reschedule" in decision_router.LLM_POLICY_CORE_LOW_CONFIDENCE_TOOL_ALLOWLIST


def test_derive_policy_info_refs_accepts_slot_style_hours_hint():
    refs = decision_router._derive_policy_info_refs(
        policy_intent="hours",
        message_text="а как у вас там",
        client_slug="demo_salon",
    )

    assert "hours" in refs


def test_derive_policy_info_refs_accepts_capability_fallback_without_explicit_text():
    refs = decision_router._derive_policy_info_refs(
        policy_intent="other",
        policy_capability="pricing",
        message_text="А на новый день как это работает?",
        client_slug="demo_salon",
    )

    assert "pricing" in refs


def test_should_collect_service_for_info_only_when_service_dependent():
    assert decision_router._should_collect_service_for_info({"pricing"}) is True
    assert decision_router._should_collect_service_for_info({"duration"}) is True
    assert decision_router._should_collect_service_for_info({"duration", "hours"}) is False
    assert decision_router._should_collect_service_for_info({"pricing", "location"}) is False
