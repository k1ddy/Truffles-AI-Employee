from __future__ import annotations

import inspect
from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import UUID

import pytest

from app.core.booking_prompt_owner import resolve_pending_booking_reactivation_candidate
from app.models import Conversation
from app.routers.webhook import decision as decision_router
from app.routers.webhook import dedup as dedup_module
from app.routers.webhook import trace as trace_router
from app.schemas.webhook import WebhookBody, WebhookMetadata, WebhookRequest, WebhookResponse
from app.services import reasoning_core


def test_reasoning_core_stage_snapshot_matches_trace() -> None:
    assert reasoning_core.STAGE_ORDER_SNAPSHOT == trace_router.DECISION_STAGE_ORDER_SNAPSHOT


def test_reasoning_core_pending_booking_reactivation_candidate_restores_dialog_state_boundary_before_llm_owner() -> None:
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="На какое время лучше записаться?",
            metadata=WebhookMetadata(
                remoteJid="77000000042@s.whatsapp.net",
                messageId="msg-pending-booking-reactivation-boundary",
            ),
        ),
    )
    policy_core_calls: list[dict[str, object]] = []

    def _route_llm_policy_core(_message_text: str, **kwargs):
        policy_core_calls.append(dict(kwargs))
        return {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "tool_args": {},
                "goal": "booking",
                "reason": "booking_prompt",
                "next_question": "service",
                "open_questions": ["service"],
                "slots": {"service": "", "datetime": "20:00", "name": ""},
                "entity_refs": [],
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "general",
                "resolution_mode": "clarify_missing_service",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "needs_manager": False,
                "pack_refs": [],
                "risk_signals": [],
            },
        }

    candidate = resolve_pending_booking_reactivation_candidate(
        payload=payload,
        message_text=payload.body.message,
        booking_state={},
        context={
            "pending_resume": {
                "context_manager": {"current_goal": "booking"},
                "booking": {
                    "active": True,
                    "datetime": "20:00",
                    "last_question": "service",
                },
                "session_memory": {
                    "active_goal": "booking",
                    "last_question_type": decision_router.EXPECTED_REPLY_SERVICE,
                },
            }
        },
        now=datetime(2026, 3, 24, 7, 18, tzinfo=timezone.utc),
        route_llm_policy_core_fn=_route_llm_policy_core,
        initial_booking_policy_core_max_tokens=160,
    )

    assert candidate is not None
    assert candidate["collect_slot"] == "service"
    assert candidate["slot_values"] == {"datetime": "20:00"}
    assert candidate["merged_slot_values"] == {"datetime": "20:00"}
    assert len(policy_core_calls) == 1
    assert policy_core_calls[0]["expected_reply_type"] == decision_router.EXPECTED_REPLY_SERVICE
    assert policy_core_calls[0]["current_goal"] == "booking"
    assert policy_core_calls[0]["slot_state"] == {"datetime": "20:00"}
    assert policy_core_calls[0]["info_refs"] == sorted(decision_router.INFO_INTENTS)
    assert policy_core_calls[0]["client_slug"] == "demo_salon"
    assert policy_core_calls[0]["max_tokens_override"] is None
    assert policy_core_calls[0]["memory_profile"] == {
        "expected_reply_type": decision_router.EXPECTED_REPLY_SERVICE,
        "active_slots": ["datetime"],
        "pending_question_contract": {
            "expected_reply_type": decision_router.EXPECTED_REPLY_SERVICE,
        },
    }
    assert set(policy_core_calls[0]["consult_refs"]) == {
        "hair_aftercolor",
        "hair_damage",
        "hair_color_choice",
        "nails_care",
        "brows_lashes_care",
        "sensitive_skin",
        "style_reference",
        "general_consult",
    }


def test_reasoning_core_pending_invalid_schema_reactivation_keeps_booking_prompt() -> None:
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="На какое время лучше записаться?",
            metadata=WebhookMetadata(
                remoteJid="77000000043@s.whatsapp.net",
                messageId="msg-pending-booking-reactivation-invalid-schema",
            ),
        ),
    )
    policy_core_calls: list[dict[str, object]] = []

    def _route_llm_policy_core(_message_text: str, **kwargs):
        policy_core_calls.append(dict(kwargs))
        return {
            "ok": False,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "tool_args": {},
                "goal": "booking",
                "reason": "booking_prompt",
                "next_question": "service",
                "open_questions": ["service"],
                "slots": {"service": "", "datetime": "20:00", "name": ""},
                "entity_refs": [],
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "general",
                "resolution_mode": "ask_about_requested_slot",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
                "needs_manager": False,
                "pack_refs": [],
                "risk_signals": [],
            },
            "error": "invalid_schema",
        }

    candidate = resolve_pending_booking_reactivation_candidate(
        payload=payload,
        message_text=payload.body.message,
        booking_state={},
        context={
            "pending_resume": {
                "context_manager": {"current_goal": "booking"},
                "booking": {
                    "active": True,
                    "datetime": "20:00",
                    "last_question": "service",
                },
                "session_memory": {
                    "active_goal": "booking",
                    "last_question_type": decision_router.EXPECTED_REPLY_SERVICE,
                },
            }
        },
        now=datetime(2026, 3, 24, 7, 19, tzinfo=timezone.utc),
        route_llm_policy_core_fn=_route_llm_policy_core,
        initial_booking_policy_core_max_tokens=160,
    )

    assert candidate is not None
    assert candidate["collect_slot"] == "service"
    assert candidate["slot_values"] == {"datetime": "20:00"}
    assert candidate["merged_slot_values"] == {"datetime": "20:00"}
    assert candidate["policy_core_mode"] == "degraded_fallback"
    assert candidate["policy_core_degrade_reason"] == "policy_error:invalid_schema"
    assert candidate["policy_core_guard_recovery"] == "invalid_schema_collect_contract"
    assert len(policy_core_calls) == 1
    assert policy_core_calls[0]["expected_reply_type"] == decision_router.EXPECTED_REPLY_SERVICE
    assert policy_core_calls[0]["current_goal"] == "booking"


def test_reasoning_core_pending_booking_reactivation_passes_canonical_runtime_memory_profile() -> None:
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="На какое время лучше записаться?",
            metadata=WebhookMetadata(
                remoteJid="77000000044@s.whatsapp.net",
                messageId="msg-pending-booking-reactivation-canonical-runtime",
            ),
        ),
    )
    policy_core_calls: list[dict[str, object]] = []

    def _route_llm_policy_core(_message_text: str, **kwargs):
        policy_core_calls.append(dict(kwargs))
        return {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "tool_args": {},
                "goal": "booking",
                "reason": "booking_prompt",
                "next_question": "service",
                "open_questions": ["service"],
                "slots": {"service": "", "datetime": "20:00", "name": ""},
                "entity_refs": [],
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "general",
                "resolution_mode": "clarify_missing_service",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "needs_manager": False,
                "pack_refs": [],
                "risk_signals": [],
            },
        }

    candidate = resolve_pending_booking_reactivation_candidate(
        payload=payload,
        message_text=payload.body.message,
        booking_state={},
        context={
            "pending_resume": {
                "context_manager": {"current_goal": "booking"},
                "booking": {
                    "active": True,
                    "datetime": "20:00",
                    "last_question": "service",
                },
                "session_memory": {
                    "active_goal": "booking",
                    "last_question_type": decision_router.EXPECTED_REPLY_SERVICE,
                },
            },
            "consultant_runtime": {
                "schema_version": "consultant_runtime.v1",
                "booking": {
                    "active": True,
                    "datetime": "20:00",
                    "last_question": "service",
                },
                "expected_reply_type": "service_choice",
                "expected_reply_reason": "collect:service",
                "current_goal": "booking",
                "dialog_state": {
                    "semantic_state": {
                        "schema_version": "canonical_semantic_state.v1",
                        "materialized_frame": {
                            "schema_version": "semantic_frame.v2",
                            "user_goal": "booking",
                            "requested_effect": "collect_missing_input",
                            "subject": {
                                "kind": "specialist",
                                "value": "Айгерим",
                            },
                            "referents": {
                                "service": {
                                    "value": "Маникюр",
                                    "entity_id": "svc:manicure",
                                    "entity_type": "service",
                                    "source_ref": "memory",
                                },
                                "specialist": {
                                    "value": "Айгерим",
                                    "entity_id": "spec:aigerim",
                                    "entity_type": "specialist",
                                    "source_ref": "memory",
                                },
                            },
                            "constraints": {},
                            "preferences": {},
                            "continuation": {
                                "expected_reply_type": "service_choice",
                                "reason": "collect:service",
                                "pending_question_target": "specialist",
                                "active_question_relation": "referent_followup",
                                "next_question": "service",
                                "open_questions": ["service"],
                            },
                            "capability_selection": {"capability": "bookability"},
                            "needs_human": False,
                            "reason": "specialist_followup",
                        },
                        "event_log": [],
                    },
                    "current_referents": {
                        "service": "Педикюр",
                        "specialist": "Алина",
                    },
                    "pending_question_contract": {
                        "next_question": "name",
                        "open_questions": ["name"],
                        "expected_reply_type": "name",
                        "reason": "collect:name",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                    },
                    "interaction_state": {"interaction_owner": "booking_time_followup"},
                    "meta": {
                        "semantic_contract": {
                            "contract_version": "semantic_contract.v1",
                            "subject_kind": "service",
                            "capability": "pricing",
                            "resolution_mode": "policy_fact",
                            "pending_question_target": "time",
                            "active_question_relation": "ask_about_requested_slot",
                            "entity_refs": [
                                {
                                    "entity_id": "svc:pedicure",
                                    "entity_type": "service",
                                    "value": "Педикюр",
                                },
                            ],
                            "referents": {
                                "service": {
                                    "value": "Педикюр",
                                    "entity_id": "svc:pedicure",
                                    "entity_type": "service",
                                },
                            },
                        }
                    },
                },
            },
        },
        now=datetime(2026, 3, 24, 7, 20, tzinfo=timezone.utc),
        route_llm_policy_core_fn=_route_llm_policy_core,
        initial_booking_policy_core_max_tokens=160,
    )

    assert candidate is not None
    assert candidate["collect_slot"] == "service"
    assert candidate["slot_values"] == {"datetime": "20:00"}
    assert len(policy_core_calls) == 1
    assert policy_core_calls[0]["memory_profile"] == {
        "expected_reply_type": decision_router.EXPECTED_REPLY_SERVICE,
        "current_referents": {
            "service": "Маникюр",
            "specialist": "Айгерим",
        },
        "pending_question_contract": {
            "next_question": "service",
            "open_questions": ["service"],
            "expected_reply_type": decision_router.EXPECTED_REPLY_SERVICE,
            "reason": "collect:service",
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
        },
        "semantic_contract": {
            "contract_version": "semantic_contract.v1",
            "subject_kind": "specialist",
            "capability": "bookability",
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "memory",
                },
                "specialist": {
                    "value": "Айгерим",
                    "entity_id": "spec:aigerim",
                    "entity_type": "specialist",
                    "source_ref": "memory",
                },
            },
        },
    }


@pytest.mark.asyncio
async def test_run_reasoning_core_delegates_to_handle_webhook_payload(monkeypatch) -> None:
    payload = WebhookRequest(body=WebhookBody(message="hi"))
    db = object()
    conversation_id = UUID("00000000-0000-0000-0000-000000000000")
    outbox_created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    captured: dict[str, object] = {}

    async def _fake_handle(payload_arg, db_arg, **kwargs):
        captured["payload"] = payload_arg
        captured["db"] = db_arg
        captured["kwargs"] = kwargs
        return WebhookResponse(success=True, message="ok")

    monkeypatch.setattr(reasoning_core, "handle_webhook_payload", _fake_handle)

    request = reasoning_core.ReasoningCoreRequest(
        payload=payload,
        db=db,
        provided_secret="secret",
        enforce_secret=True,
        enqueue_only=True,
        skip_persist=True,
        conversation_id=conversation_id,
        batch_messages=["a", "b"],
        outbox_ids=["o1"],
        outbox_created_at=outbox_created_at,
    )

    response = await reasoning_core.run_reasoning_core(request)

    assert response.success is True
    assert captured["payload"] is payload
    assert captured["db"] is db
    assert captured["kwargs"] == {
        "provided_secret": "secret",
        "enforce_secret": True,
        "enqueue_only": True,
        "skip_persist": True,
        "conversation_id": conversation_id,
        "batch_messages": ["a", "b"],
        "outbox_ids": ["o1"],
        "outbox_created_at": outbox_created_at,
        "preflight_payload": None,
    }


@pytest.mark.asyncio
async def test_reasoning_core_handle_webhook_payload_delegates_directly_to_consultant_core_v2(monkeypatch) -> None:
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Привет",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-runtime-delegate-1",
            ),
        ),
    )
    captured: dict[str, object] = {}

    async def _delegate(payload_arg, db_arg, **kwargs):
        captured["payload"] = payload_arg
        captured["db"] = db_arg
        captured["kwargs"] = kwargs
        return WebhookResponse(success=True, message="delegated", bot_response="ok")

    monkeypatch.setattr("app.core.consultant_core_v2.handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret=None,
        enforce_secret=False,
        enqueue_only=True,
        skip_persist=True,
        conversation_id=UUID("00000000-0000-0000-0000-000000000144"),
        batch_messages=["m1"],
        outbox_ids=["o1"],
        outbox_created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        preflight_payload={"client": "cached"},
    )

    assert response.success is True
    assert response.message == "delegated"
    assert captured["payload"] is payload
    assert captured["kwargs"]["provided_secret"] is None
    assert captured["kwargs"]["enforce_secret"] is False
    assert captured["kwargs"]["enqueue_only"] is True
    assert captured["kwargs"]["skip_persist"] is True
    assert captured["kwargs"]["batch_messages"] == ["m1"]
    assert captured["kwargs"]["outbox_ids"] == ["o1"]
    assert captured["kwargs"]["preflight_payload"] == {"client": "cached"}


def test_reasoning_core_default_runtime_no_longer_contains_ingress_semantic_override_priming() -> None:
    source = inspect.getsource(reasoning_core.handle_webhook_payload)

    assert "_use_intent_routing_primitives_override" not in source
    assert "_use_domain_routing_snapshot_override" not in source
    assert "_use_controller_route_snapshot_override" not in source
    assert "_use_policy_core_route_snapshot_override" not in source
    assert "use_intent_signal_override" not in source
    assert "use_intent_semantic_override" not in source
    assert "use_dialogue_controller_override" not in source
    assert "use_domain_routing_override" not in source


def test_build_runtime_exception_artifact_uses_new_core_contracts() -> None:
    artifact = reasoning_core._build_runtime_exception_artifact(
        bot_response=decision_router.MSG_DELIVERY_FAILED,
        transport_status="failed",
        transport_reason="fallback_send_failed",
    )

    assert artifact.turn_result.contract_status == "degraded"
    assert artifact.turn_result.outcome == "HANDOFF"
    assert artifact.turn_result.boundary_override is not None
    assert artifact.turn_result.boundary_override.reason_code == reasoning_core.REASONING_CORE_DEGRADE_REASON
    assert artifact.turn_result.dialog_state.interaction_state.interaction_owner == "reasoning_core_exception_degrade"
    assert artifact.turn_result.reply.text == decision_router.MSG_DELIVERY_FAILED
    turn_outcome = artifact.turn_outcome.to_metadata()
    assert turn_outcome["contract_status"] == "degraded"
    assert turn_outcome["observability"]["transport_status"] == "failed"
    assert turn_outcome["meta"]["reply_kind"] == "handoff"


def test_build_conversation_snapshot_uses_routing_matrix_and_projection_bridge() -> None:
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000140"),
        client_id=UUID("00000000-0000-0000-0000-000000000141"),
        user_id=UUID("00000000-0000-0000-0000-000000000142"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="manager_active",
        bot_status="active",
        branch_id=UUID("00000000-0000-0000-0000-000000000143"),
        context={
            "expected_reply_type": " time ",
            "expected_reply_reason": " booking_time_availability_followup ",
            "current_goal": " booking ",
            "booking": {"active": True, "datetime": " 15:00 "},
        },
    )

    snapshot = reasoning_core._build_conversation_snapshot(conversation)

    assert snapshot.conversation_id == conversation.id
    assert snapshot.state == "manager_active"
    assert snapshot.branch_id == conversation.branch_id
    assert snapshot.reply_slot == "time"
    assert snapshot.resume_reason == "booking_time_availability_followup"
    assert snapshot.current_goal == "booking"
    assert snapshot.booking_active is True
    assert snapshot.allow_bot_reply is False
    assert snapshot.booking_time_token == "15:00"
    assert snapshot.booking_datetime_value == "15:00"
    assert snapshot.service_referent is None


def test_build_conversation_snapshot_prefers_canonical_question_contract_over_stale_projection() -> None:
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000144"),
        client_id=UUID("00000000-0000-0000-0000-000000000145"),
        user_id=UUID("00000000-0000-0000-0000-000000000146"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        bot_status="active",
        branch_id=None,
        context={
            "expected_reply_type": " name ",
            "expected_reply_reason": " stale_projection ",
            "context_manager": {
                "current_goal": "booking",
                "canonical_dialog_state": {
                    "pending_question_contract": {
                        "expected_reply_type": " time ",
                        "reason": " booking_interrupt ",
                        "next_question": " datetime ",
                        "open_questions": [" datetime "],
                    }
                },
            },
            "booking": {"active": True, "datetime": "2026-02-12 17:45"},
        },
    )

    snapshot = reasoning_core._build_conversation_snapshot(conversation)

    assert snapshot.reply_slot == "time"
    assert snapshot.resume_reason == "booking_interrupt"


def test_build_conversation_snapshot_projects_service_referent_from_canonical_state() -> None:
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000240"),
        client_id=UUID("00000000-0000-0000-0000-000000000241"),
        user_id=UUID("00000000-0000-0000-0000-000000000242"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        bot_status="active",
        branch_id=None,
        context={
            "context_manager": {
                "message_count": 6,
                "canonical_dialog_state": {
                    "owner_id": "context_manager.dialog_state.v1",
                    "version": "v1",
                    "current_referents": {
                        "service": {
                            "value": "маникюр",
                            "source": "semantic_match",
                            "message_count": 5,
                            "ttl": 4,
                        }
                    },
                },
            }
        },
    )

    snapshot = reasoning_core._build_conversation_snapshot(conversation)

    assert snapshot.service_referent == "маникюр"


def test_build_conversation_snapshot_projects_raw_booking_datetime_value() -> None:
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000244"),
        client_id=UUID("00000000-0000-0000-0000-000000000245"),
        user_id=UUID("00000000-0000-0000-0000-000000000246"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        bot_status="active",
        branch_id=None,
        context={"booking": {"active": True, "service": "Маникюр", "datetime": " завтра "}},
    )

    snapshot = reasoning_core._build_conversation_snapshot(conversation)

    assert snapshot.booking_active is True
    assert snapshot.booking_time_token is None
    assert snapshot.booking_datetime_value == "завтра"
    assert snapshot.service_referent == "Маникюр"


def test_build_conversation_snapshot_restores_session_memory_expected_reply_for_short_booking_reply() -> None:
    now = datetime.now(timezone.utc)
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000247"),
        client_id=UUID("00000000-0000-0000-0000-000000000248"),
        user_id=UUID("00000000-0000-0000-0000-000000000249"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        bot_status="active",
        branch_id=None,
        context={
            "booking": {
                "active": True,
                "datetime": "2026-02-12 17:45",
                "last_question": "service",
            },
            "session_memory": {
                "active_goal": "booking",
                "last_question_type": decision_router.EXPECTED_REPLY_SERVICE,
                "last_updated_at": now.isoformat(),
                "ttl_hours": 24,
            },
        },
    )

    snapshot = reasoning_core._build_conversation_snapshot(
        conversation,
        message_text="Маникюр",
        client_slug="demo_salon",
    )

    assert snapshot.reply_slot == decision_router.EXPECTED_REPLY_SERVICE
    assert snapshot.resume_reason is None
    assert snapshot.booking_active is True
    assert snapshot.booking_time_token == "17:45"
    assert snapshot.service_referent is None


def test_build_conversation_snapshot_prefers_session_memory_pending_question_contract() -> None:
    now = datetime.now(timezone.utc)
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000347"),
        client_id=UUID("00000000-0000-0000-0000-000000000348"),
        user_id=UUID("00000000-0000-0000-0000-000000000349"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        bot_status="active",
        branch_id=None,
        context={
            "booking": {
                "active": True,
                "datetime": "2026-02-12 17:45",
                "last_question": "datetime",
            },
            "session_memory": {
                "active_goal": "booking",
                "last_question_type": decision_router.EXPECTED_REPLY_SERVICE,
                "pending_question_contract": {
                    "expected_reply_type": decision_router.EXPECTED_REPLY_TIME,
                    "reason": "booking_interrupt",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                },
                "last_updated_at": now.isoformat(),
                "ttl_hours": 24,
            },
        },
    )

    snapshot = reasoning_core._build_conversation_snapshot(
        conversation,
        message_text="завтра в 18:00",
        client_slug="demo_salon",
    )

    assert snapshot.reply_slot == decision_router.EXPECTED_REPLY_TIME
    assert snapshot.resume_reason == "booking_interrupt"
    assert snapshot.booking_active is True
    assert snapshot.booking_time_token == "17:45"


def test_run_secret_enforced_preflight_reuses_http_preflight(monkeypatch) -> None:
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-secret-preflight-1",
            ),
        ),
    )
    captured: dict[str, object] = {}

    def _fake_run_preflight(payload_arg, db_arg, **kwargs):
        captured["payload"] = payload_arg
        captured["db"] = db_arg
        captured["kwargs"] = kwargs
        return None, {"client": "ok"}

    monkeypatch.setattr("app.routers.webhook.http._run_preflight", _fake_run_preflight)

    db = Mock()
    response, preflight_payload = reasoning_core._run_secret_enforced_preflight(
        payload,
        db,
        provided_secret="secret",
        conversation_id=UUID("00000000-0000-0000-0000-000000000099"),
    )

    assert response is None
    assert preflight_payload == {"client": "ok"}
    assert captured["payload"] is payload
    assert captured["db"] is db
    assert captured["kwargs"]["provided_secret"] == "secret"
    assert captured["kwargs"]["enforce_secret"] is True
    assert captured["kwargs"]["conversation_id"] == UUID("00000000-0000-0000-0000-000000000099")
    assert callable(captured["kwargs"]["resolve_trace_conversation"])
    assert callable(captured["kwargs"]["record_early_trace"])


def test_build_empty_message_artifact_uses_new_core_contracts() -> None:
    artifact = reasoning_core._build_empty_message_artifact()

    assert artifact.turn_result.contract_status == "blocked"
    assert artifact.turn_result.outcome == "FACT"
    assert artifact.turn_result.boundary_override is not None
    assert artifact.turn_result.boundary_override.reason_code == reasoning_core.REASONING_CORE_PREFLIGHT_REASON
    assert artifact.turn_result.reply.reply_kind == "system"
    assert artifact.turn_result.reply.text == ""
    turn_outcome = artifact.turn_outcome.to_metadata()
    assert turn_outcome["contract_status"] == "invalid"
    assert turn_outcome["observability"]["transport_reason"] == "empty_message"
    assert turn_outcome["meta"]["preflight_path"] is True


def test_build_sender_branch_ignore_artifact_uses_new_core_contracts() -> None:
    artifact = reasoning_core._build_sender_branch_ignore_artifact()

    assert artifact.turn_result.contract_status == "blocked"
    assert artifact.turn_result.outcome == "FACT"
    assert artifact.turn_result.boundary_override is not None
    assert artifact.turn_result.boundary_override.reason_code == reasoning_core.REASONING_CORE_SENDER_BRANCH_IGNORE_REASON
    assert artifact.turn_result.reply.reply_kind == "system"
    assert artifact.turn_result.reply.text == ""
    turn_outcome = artifact.turn_outcome.to_metadata()
    assert turn_outcome["action"] == "ignore"
    assert turn_outcome["intent"] == "sender_is_branch"
    assert turn_outcome["observability"]["transport_reason"] == "sender_is_branch"
    assert turn_outcome["meta"]["ignored_path"] is True


def test_build_missing_remote_jid_artifact_uses_new_core_contracts() -> None:
    artifact = reasoning_core._build_missing_remote_jid_artifact()

    assert artifact.turn_result.contract_status == "blocked"
    assert artifact.turn_result.outcome == "FACT"
    assert artifact.turn_result.boundary_override is not None
    assert artifact.turn_result.boundary_override.reason_code == reasoning_core.REASONING_CORE_MISSING_REMOTE_JID_REASON
    assert artifact.turn_result.reply.reply_kind == "system"
    assert artifact.turn_result.reply.text == ""
    turn_outcome = artifact.turn_outcome.to_metadata()
    assert turn_outcome["action"] == "reject"
    assert turn_outcome["intent"] == "missing_remote_jid"
    assert turn_outcome["observability"]["transport_reason"] == "missing_remote_jid"
    assert turn_outcome["meta"]["preflight_path"] is True


def test_build_missing_tenant_context_artifact_uses_new_core_contracts() -> None:
    artifact = reasoning_core._build_missing_tenant_context_artifact()

    assert artifact.turn_result.contract_status == "blocked"
    assert artifact.turn_result.outcome == "FACT"
    assert artifact.turn_result.boundary_override is not None
    assert artifact.turn_result.boundary_override.reason_code == reasoning_core.REASONING_CORE_MISSING_TENANT_CONTEXT_REASON
    assert artifact.turn_result.reply.reply_kind == "system"
    assert artifact.turn_result.reply.text == ""
    turn_outcome = artifact.turn_outcome.to_metadata()
    assert turn_outcome["action"] == "reject"
    assert turn_outcome["intent"] == "missing_tenant_context"
    assert turn_outcome["observability"]["transport_reason"] == "missing_tenant_context"
    assert turn_outcome["meta"]["preflight_path"] is True


def test_build_tenant_context_reject_artifact_uses_new_core_contracts() -> None:
    artifact = reasoning_core._build_tenant_context_reject_artifact(
        rejection=reasoning_core.ReasoningCoreTenantContextRejection(
            reason_code=reasoning_core.REASONING_CORE_TENANT_CONTEXT_INVALID_REASON,
            message="Invalid tenant_context",
            interaction_owner=reasoning_core.REASONING_CORE_TENANT_CONTEXT_INVALID_OWNER,
            trace_message="reasoning_core rejected invalid tenant_context contract",
            meta={"error": "$: invalid source"},
        ),
    )

    assert artifact.turn_result.contract_status == "blocked"
    assert artifact.turn_result.outcome == "FACT"
    assert artifact.turn_result.boundary_override is not None
    assert artifact.turn_result.boundary_override.reason_code == reasoning_core.REASONING_CORE_TENANT_CONTEXT_INVALID_REASON
    assert artifact.turn_result.reply.reply_kind == "system"
    assert artifact.turn_result.reply.text == ""
    turn_outcome = artifact.turn_outcome.to_metadata()
    assert turn_outcome["action"] == "reject"
    assert turn_outcome["intent"] == "tenant_context_contract_invalid"
    assert turn_outcome["observability"]["transport_reason"] == "tenant_context_contract_invalid"
    assert turn_outcome["meta"]["tenant_context_guard"] is True
    assert turn_outcome["meta"]["error"] == "$: invalid source"


def test_build_remote_branch_phone_ignore_artifact_uses_new_core_contracts() -> None:
    artifact = reasoning_core._build_remote_branch_phone_ignore_artifact(
        matched_phone="+7 (705) 574-04-56",
    )

    assert artifact.turn_result.contract_status == "blocked"
    assert artifact.turn_result.outcome == "FACT"
    assert artifact.turn_result.boundary_override is not None
    assert artifact.turn_result.boundary_override.reason_code == reasoning_core.REASONING_CORE_REMOTE_BRANCH_PHONE_REASON
    assert artifact.turn_result.reply.reply_kind == "system"
    assert artifact.turn_result.reply.text == ""
    turn_outcome = artifact.turn_outcome.to_metadata()
    assert turn_outcome["action"] == "ignore"
    assert turn_outcome["intent"] == "remote_is_branch_phone"
    assert turn_outcome["observability"]["transport_reason"] == "remote_is_branch_phone"
    assert turn_outcome["meta"]["matched_phone"] == "+7 (705) 574-04-56"
    assert turn_outcome["meta"]["ignored_path"] is True


def test_build_duplicate_message_artifact_uses_new_core_contracts() -> None:
    artifact = reasoning_core._build_duplicate_message_artifact(
        dedup_backend="message_dedup",
        dedup_fallback_reason=None,
    )

    assert artifact.turn_result.contract_status == "blocked"
    assert artifact.turn_result.outcome == "FACT"
    assert artifact.turn_result.boundary_override is not None
    assert artifact.turn_result.boundary_override.reason_code == reasoning_core.REASONING_CORE_DUPLICATE_REASON
    assert artifact.turn_result.reply.reply_kind == "system"
    assert artifact.turn_result.reply.text == ""
    turn_outcome = artifact.turn_outcome.to_metadata()
    assert turn_outcome["action"] == "ignore"
    assert turn_outcome["intent"] == "duplicate_message_id"
    assert turn_outcome["observability"]["transport_reason"] == "duplicate_message_id"
    assert turn_outcome["meta"]["dedup_backend"] == "message_dedup"
    assert turn_outcome["meta"]["preexisting_duplicate"] is True


def test_lookup_preexisting_duplicate_message_no_longer_contains_fast_bypass_logic() -> None:
    source = inspect.getsource(reasoning_core._lookup_preexisting_duplicate_message)

    assert "_is_fast_dedup_bypass_enabled" not in source


def test_lookup_preexisting_duplicate_message_delegates_to_dedup_owner(monkeypatch) -> None:
    db = Mock()
    delegated: dict[str, object] = {}

    def _fake_owner_probe(*args, **kwargs):
        delegated["args"] = args
        delegated["kwargs"] = kwargs
        return dedup_module.DuplicateMessageProbe(
            duplicate=True,
            backend="messages_table",
            fallback_reason="message_dedup_lookup_error",
        )

    monkeypatch.setattr(dedup_module, "_lookup_preexisting_duplicate_message", _fake_owner_probe)

    probe = reasoning_core._lookup_preexisting_duplicate_message(
        db,
        client_id=UUID("00000000-0000-0000-0000-000000000024"),
        message_id="msg-dedup-owner-1",
    )

    assert probe == reasoning_core.ReasoningCoreDuplicateProbe(
        duplicate=True,
        backend="messages_table",
        fallback_reason="message_dedup_lookup_error",
    )
    assert delegated["args"] == (db,)
    assert delegated["kwargs"] == {
        "client_id": UUID("00000000-0000-0000-0000-000000000024"),
        "message_id": "msg-dedup-owner-1",
    }


def test_normalize_payload_for_delegation_trims_empty_non_media_to_none() -> None:
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="   ",
            messageType="text",
            metadata=WebhookMetadata(messageId="msg-empty-2"),
        ),
    )

    normalized = reasoning_core._normalize_payload_for_delegation(payload)

    assert normalized is not payload
    assert normalized.body.message is None


def test_normalize_payload_for_delegation_promotes_media_caption_to_message() -> None:
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message=None,
            messageType="image",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-image-caption-1",
            ),
            mediaData={"type": "image", "caption": "  посмотрите варианты  "},
        ),
    )

    normalized = reasoning_core._normalize_payload_for_delegation(payload)

    assert normalized.body.message == "посмотрите варианты"
    assert payload.body.message is None
