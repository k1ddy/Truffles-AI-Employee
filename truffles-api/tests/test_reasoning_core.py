from __future__ import annotations

import inspect
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from fastapi import HTTPException

import app.services.ai_service as ai_service
import app.services.intent_service as intent_service
import app.services.pack_runtime_service as pack_runtime_service
from app.contracts.result import Ok
from app.core.booking_prompt_owner import resolve_pending_booking_reactivation_candidate
from app.models import Client, Conversation, Message, User
from app.routers.webhook import context_manager as context_manager_router
from app.routers.webhook import decision as decision_router
from app.routers.webhook import dedup as dedup_module
from app.routers.webhook import http as http_router
from app.routers.webhook import info as info_router
from app.routers.webhook import pending as pending_router
from app.routers.webhook import trace as trace_router
from app.schemas.capabilities import CapabilitiesPayload
from app.schemas.webhook import (
    WebhookBody,
    WebhookMetadata,
    WebhookRequest,
    WebhookResponse,
    WebhookTenantContext,
)
from app.services import reasoning_core
from app.services.capabilities_runtime import RuntimeCapabilities, get_runtime_capabilities
from app.services.knowledge_runtime import RuntimeTruth, get_runtime_truth
from app.services.tool_registry_service import ToolExecutionResult


def test_reasoning_core_stage_snapshot_matches_trace():
    assert reasoning_core.STAGE_ORDER_SNAPSHOT == trace_router.DECISION_STAGE_ORDER_SNAPSHOT


def test_reasoning_core_missing_remote_jid_artifact_uses_boundary_block_override():
    artifact = reasoning_core._build_missing_remote_jid_artifact()

    assert artifact.turn_result.boundary_override is not None
    assert artifact.turn_result.boundary_override.decision == "block"
    assert artifact.turn_result.boundary_override.reason_code == "missing_remote_jid"
    assert artifact.turn_result.boundary_override.preserve_fields == [
        "outcome",
        "interaction_owner",
        "interaction_target",
        "interaction_relation",
        "pending_question_contract",
    ]
    assert artifact.turn_outcome.meta["boundary_decision"] == "block"


def test_reasoning_core_pending_booking_reactivation_candidate_restores_dialog_state_boundary_before_llm_owner():
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
                "slots": {
                    "service": "",
                    "datetime": "20:00",
                    "name": "",
                },
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


def test_reasoning_core_pending_invalid_schema_reactivation_keeps_booking_prompt():
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
                "slots": {
                    "service": "",
                    "datetime": "20:00",
                    "name": "",
                },
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


@pytest.mark.asyncio
async def test_reasoning_core_delegates_to_decision(monkeypatch):
    payload = WebhookRequest(body=WebhookBody(message="hi"))
    db = object()
    conversation_id = UUID("00000000-0000-0000-0000-000000000000")
    outbox_created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    captured: dict[str, object] = {}
    bridge_calls: list[dict[str, object]] = []

    async def fake_handle(payload, db, **kwargs):
        captured["payload"] = payload
        captured["db"] = db
        captured["kwargs"] = kwargs
        return WebhookResponse(success=True, message="ok")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", fake_handle)
    monkeypatch.setattr(
        reasoning_core,
        "_run_secret_enforced_preflight",
        lambda payload, db, *, provided_secret, conversation_id: (
            bridge_calls.append(
                {
                    "payload": payload,
                    "db": db,
                    "provided_secret": provided_secret,
                    "conversation_id": conversation_id,
                }
            )
            or (None, {})
        ),
    )

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
    assert bridge_calls == [
        {
            "payload": payload,
            "db": db,
            "provided_secret": "secret",
            "conversation_id": conversation_id,
        }
    ]
    assert captured["payload"] is payload
    assert captured["db"] is db
    assert captured["kwargs"]["provided_secret"] == "secret"
    assert captured["kwargs"]["enforce_secret"] is False
    assert captured["kwargs"]["enqueue_only"] is True
    assert captured["kwargs"]["skip_persist"] is True
    assert captured["kwargs"]["conversation_id"] == conversation_id
    assert captured["kwargs"]["batch_messages"] == ["a", "b"]
    assert captured["kwargs"]["outbox_ids"] == ["o1"]
    assert captured["kwargs"]["outbox_created_at"] == outbox_created_at


@pytest.mark.asyncio
async def test_reasoning_core_fallback_on_exception(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hi",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                instanceId="inst-1",
                messageId="msg-1",
            ),
        ),
    )
    db = Mock()
    saved_message = Message(
        conversation_id=UUID("00000000-0000-0000-0000-000000000001"),
        client_id=UUID("00000000-0000-0000-0000-000000000002"),
        role="user",
        content="hi",
        message_metadata={},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = saved_message

    async def boom(*args, **kwargs):
        raise RuntimeError("boom")

    send_calls: dict[str, object] = {}

    def fake_send_message_safe(*args, **kwargs):
        send_calls["called"] = True
        return Ok("ok")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", boom)
    monkeypatch.setattr(reasoning_core, "send_message_safe", fake_send_message_safe)
    monkeypatch.setattr(reasoning_core, "alert_error", lambda *args, **kwargs: None)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        db,
        provided_secret=None,
        enforce_secret=False,
        enqueue_only=False,
        skip_persist=False,
        conversation_id=None,
        batch_messages=None,
        outbox_ids=None,
        outbox_created_at=None,
    )

    assert response.success is True
    assert response.bot_response == decision_router.MSG_DELIVERY_FAILED
    assert send_calls.get("called") is True
    db.rollback.assert_called_once()
    db.commit.assert_called_once()
    decision_meta = saved_message.message_metadata.get("decision_meta") or {}
    turn_outcome = decision_meta.get("turn_outcome") or {}
    assert turn_outcome.get("contract_status") == "degraded"
    assert turn_outcome.get("tool_decision") == "runtime_exception"
    assert turn_outcome.get("observability", {}).get("transport_status") == "delivered"
    runtime_contract = decision_meta.get("consultant_core_runtime") or {}
    assert runtime_contract.get("outcome") == "HANDOFF"
    assert runtime_contract.get("reason_code") == reasoning_core.REASONING_CORE_DEGRADE_REASON


@pytest.mark.asyncio
async def test_reasoning_core_fallback_on_exception_send_failure_keeps_bot_response(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hi",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                instanceId="inst-1",
                messageId="msg-2",
            ),
        ),
    )
    db = Mock()

    async def boom(*args, **kwargs):
        raise RuntimeError("boom")

    class _SendResult:
        def is_ok(self) -> bool:
            return False

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", boom)
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: _SendResult())
    monkeypatch.setattr(reasoning_core, "alert_error", lambda *args, **kwargs: None)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        db,
        provided_secret=None,
        enforce_secret=False,
        enqueue_only=False,
        skip_persist=False,
        conversation_id=None,
        batch_messages=None,
        outbox_ids=None,
        outbox_created_at=None,
    )

    assert response.success is True
    assert response.message == "Fallback response skipped"
    assert response.bot_response == decision_router.MSG_DELIVERY_FAILED


def test_build_runtime_exception_artifact_uses_new_core_contracts():
    artifact = reasoning_core._build_runtime_exception_artifact(
        bot_response=decision_router.MSG_DELIVERY_FAILED,
        transport_status="failed",
        transport_reason="fallback_send_failed",
    )

    assert artifact.turn_result.contract_status == "degraded"
    assert artifact.turn_result.outcome == "HANDOFF"
    assert artifact.turn_result.boundary_override is not None
    assert artifact.turn_result.boundary_override.reason_code == reasoning_core.REASONING_CORE_DEGRADE_REASON
    assert (
        artifact.turn_result.dialog_state.interaction_state.interaction_owner
        == "reasoning_core_exception_degrade"
    )
    assert artifact.turn_result.reply.text == decision_router.MSG_DELIVERY_FAILED
    turn_outcome = artifact.turn_outcome.to_metadata()
    assert turn_outcome["contract_status"] == "degraded"
    assert turn_outcome["observability"]["transport_status"] == "failed"
    assert turn_outcome["meta"]["reply_kind"] == "handoff"


def test_build_conversation_snapshot_uses_routing_matrix_and_projection_bridge():
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


def test_build_conversation_snapshot_projects_service_referent_from_canonical_state():
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


def test_build_conversation_snapshot_projects_raw_booking_datetime_value():
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
        context={
            "booking": {"active": True, "service": "Маникюр", "datetime": " завтра "},
        },
    )

    snapshot = reasoning_core._build_conversation_snapshot(conversation)

    assert snapshot.booking_active is True
    assert snapshot.booking_time_token is None
    assert snapshot.booking_datetime_value == "завтра"
    assert snapshot.service_referent == "Маникюр"


def test_build_conversation_snapshot_restores_session_memory_expected_reply_for_short_booking_reply():
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


@pytest.mark.asyncio
async def test_reasoning_core_empty_message_preflight_does_not_delegate(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="   ",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-empty-1",
            ),
        ),
    )

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("legacy delegate should not be called for empty non-media inbound")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is False
    assert response.message == "Empty message"
    assert response.bot_response is None


@pytest.mark.asyncio
async def test_reasoning_core_media_without_text_still_delegates(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message=None,
            messageType="image",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-image-1",
            ),
        ),
    )
    captured: dict[str, object] = {}

    async def _delegate(payload, db, **kwargs):
        captured["payload"] = payload
        return WebhookResponse(success=True, message="delegated", bot_response="ok")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    delegated_payload = captured["payload"]
    assert delegated_payload is not payload
    assert delegated_payload.body.message == "[image]"
    assert payload.body.message is None


@pytest.mark.asyncio
async def test_reasoning_core_ignores_active_branch_sender_before_delegate(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77055740455@s.whatsapp.net",
                messageId="msg-branch-sender-1",
            ),
        ),
    )
    branch = Mock(
        id=UUID("00000000-0000-0000-0000-000000000011"),
        client_id=UUID("00000000-0000-0000-0000-000000000012"),
        phone="+77055740455",
    )

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("legacy delegate should not be called for active branch sender inbound")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda db, remote_jid: branch)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Ignored sender (branch number)"
    assert response.conversation_id is None
    assert response.bot_response is None


@pytest.mark.asyncio
async def test_reasoning_core_missing_remote_jid_rejects_before_delegate(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                messageId="msg-missing-remote-jid-1",
                remoteJid=None,
            ),
        ),
    )

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("legacy delegate should not be called for missing metadata.remoteJid")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is False
    assert response.message == "Missing metadata.remoteJid"
    assert response.conversation_id is None
    assert response.bot_response is None


@pytest.mark.asyncio
async def test_reasoning_core_missing_tenant_context_rejects_before_delegate(monkeypatch):
    payload = WebhookRequest(
        client_slug="",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                messageId="msg-missing-tenant-context-1",
                remoteJid="77000000000@s.whatsapp.net",
            ),
        ),
    )

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("legacy delegate should not be called for missing tenant_context")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is False
    assert response.message == "Missing tenant_context"
    assert response.conversation_id is None
    assert response.bot_response is None


@pytest.mark.asyncio
async def test_reasoning_core_invalid_tenant_context_rejects_before_delegate(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77055740456@s.whatsapp.net",
                messageId="msg-tenant-invalid-1",
            ),
        ),
        tenant_context=WebhookTenantContext(
            client_slug="demo_salon",
            source="broken",
        ),
    )

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("legacy delegate should not be called for invalid tenant_context")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is False
    assert response.message == "Invalid tenant_context"
    assert response.conversation_id is None
    assert response.bot_response is None


@pytest.mark.asyncio
async def test_reasoning_core_tenant_context_client_mismatch_rejects_before_delegate(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77055740456@s.whatsapp.net",
                messageId="msg-tenant-mismatch-1",
            ),
        ),
        tenant_context=WebhookTenantContext(
            client_id=UUID("00000000-0000-0000-0000-000000000030"),
            client_slug="demo_salon",
            source="webhook",
        ),
    )

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("legacy delegate should not be called for tenant_context client mismatch")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_preflight_client_id",
        lambda db, payload: UUID("00000000-0000-0000-0000-000000000031"),
    )

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is False
    assert response.message == "Tenant mismatch"
    assert response.conversation_id is None
    assert response.bot_response is None


@pytest.mark.asyncio
async def test_reasoning_core_tenant_context_client_slug_mismatch_rejects_before_delegate(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77055740456@s.whatsapp.net",
                messageId="msg-tenant-slug-mismatch-1",
            ),
        ),
        tenant_context=WebhookTenantContext(
            client_slug="other_salon",
            source="webhook",
        ),
    )

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("legacy delegate should not be called for tenant_context client_slug mismatch")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_preflight_client_id",
        lambda db, payload: UUID("00000000-0000-0000-0000-000000000032"),
    )

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is False
    assert response.message == "Tenant mismatch"
    assert response.conversation_id is None
    assert response.bot_response is None


@pytest.mark.asyncio
async def test_reasoning_core_ignores_same_client_branch_phone_before_delegate(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77055740456@s.whatsapp.net",
                messageId="msg-client-branch-phone-1",
            ),
        ),
    )

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("legacy delegate should not be called for same-client branch phone inbound")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_preflight_client_id",
        lambda db, payload: UUID("00000000-0000-0000-0000-000000000020"),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_client_branch_phone",
        lambda *args, **kwargs: "+7 (705) 574-04-56",
    )

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Ignored branch sender"
    assert response.conversation_id is None
    assert response.bot_response is None


@pytest.mark.asyncio
async def test_reasoning_core_duplicate_message_id_skips_preexisting_duplicate_before_delegate(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-dup-1",
            ),
        ),
    )

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("legacy delegate should not be called for duplicate message_id inbound")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_preflight_client_id",
        lambda db, payload: UUID("00000000-0000-0000-0000-000000000021"),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(
            duplicate=True,
            backend="message_dedup",
            fallback_reason=None,
        ),
    )

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Duplicate message_id"
    assert response.conversation_id is None
    assert response.bot_response is None


@pytest.mark.asyncio
async def test_reasoning_core_non_duplicate_message_id_still_delegates(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-dup-2",
            ),
        ),
    )
    captured: dict[str, object] = {}

    async def _delegate(payload, db, **kwargs):
        captured["payload"] = payload
        return WebhookResponse(success=True, message="delegated", bot_response="ok")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_preflight_client_id",
        lambda db, payload: UUID("00000000-0000-0000-0000-000000000022"),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(
            duplicate=False,
            backend="message_dedup",
            fallback_reason=None,
        ),
    )

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert captured["payload"] == payload


@pytest.mark.asyncio
async def test_reasoning_core_duplicate_probe_does_not_bypass_secret_enforcement(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-dup-secret-1",
            ),
        ),
    )
    captured: dict[str, object] = {}

    async def _delegate(payload, db, **kwargs):
        captured["payload"] = payload
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)
    monkeypatch.setattr(
        reasoning_core,
        "_run_secret_enforced_preflight",
        lambda *args, **kwargs: (None, {}),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(
            duplicate=True,
            backend="message_dedup",
            fallback_reason=None,
        ),
    )

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret="secret",
        enforce_secret=True,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert captured["payload"] == payload


@pytest.mark.asyncio
async def test_reasoning_core_duplicate_probe_does_not_run_for_skip_persist(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-dup-skip-persist-1",
            ),
        ),
    )
    captured: dict[str, object] = {}

    async def _delegate(payload, db, **kwargs):
        captured["payload"] = payload
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(
            duplicate=True,
            backend="message_dedup",
            fallback_reason=None,
        ),
    )

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret=None,
        enforce_secret=False,
        skip_persist=True,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert captured["payload"] == payload


@pytest.mark.asyncio
async def test_reasoning_core_same_client_branch_phone_does_not_bypass_secret_enforcement(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77055740456@s.whatsapp.net",
                messageId="msg-client-branch-phone-secret-1",
            ),
        ),
    )
    captured: dict[str, object] = {}

    async def _delegate(payload, db, **kwargs):
        captured["payload"] = payload
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)
    monkeypatch.setattr(
        reasoning_core,
        "_run_secret_enforced_preflight",
        lambda *args, **kwargs: (None, {}),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_client_branch_phone",
        lambda *args, **kwargs: "+7 (705) 574-04-56",
    )

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret="secret",
        enforce_secret=True,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert captured["payload"] == payload


@pytest.mark.asyncio
async def test_reasoning_core_tenant_context_guard_does_not_bypass_secret_enforcement(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77055740456@s.whatsapp.net",
                messageId="msg-tenant-secret-1",
            ),
        ),
        tenant_context=WebhookTenantContext(
            client_slug="demo_salon",
            source="broken",
        ),
    )
    captured: dict[str, object] = {}

    async def _delegate(payload, db, **kwargs):
        captured["payload"] = payload
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)
    monkeypatch.setattr(
        reasoning_core,
        "_run_secret_enforced_preflight",
        lambda *args, **kwargs: (None, {}),
    )

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret="secret",
        enforce_secret=True,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert captured["payload"] == payload


@pytest.mark.asyncio
async def test_reasoning_core_missing_remote_jid_does_not_bypass_secret_enforcement(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                messageId="msg-missing-remote-jid-secret-1",
                remoteJid=None,
            ),
        ),
    )
    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("legacy delegate should not be called when secret preflight rejects")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)
    monkeypatch.setattr(
        reasoning_core,
        "_run_secret_enforced_preflight",
        lambda *args, **kwargs: (WebhookResponse(success=False, message="Missing metadata.remoteJid"), {}),
    )

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret="secret",
        enforce_secret=True,
    )

    assert response.success is False
    assert response.message == "Missing metadata.remoteJid"


@pytest.mark.asyncio
async def test_reasoning_core_missing_tenant_context_does_not_bypass_secret_enforcement(monkeypatch):
    payload = WebhookRequest(
        client_slug="",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                messageId="msg-missing-tenant-context-secret-1",
                remoteJid="77000000000@s.whatsapp.net",
            ),
        ),
    )
    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("legacy delegate should not be called when secret preflight rejects")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)
    monkeypatch.setattr(
        reasoning_core,
        "_run_secret_enforced_preflight",
        lambda *args, **kwargs: (WebhookResponse(success=False, message="Missing tenant_context"), {}),
    )

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret="secret",
        enforce_secret=True,
    )

    assert response.success is False
    assert response.message == "Missing tenant_context"


@pytest.mark.asyncio
async def test_reasoning_core_sender_branch_ignore_does_not_bypass_secret_preflight(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77055740455@s.whatsapp.net",
                messageId="msg-branch-sender-secret-1",
            ),
        ),
    )
    branch = Mock(
        id=UUID("00000000-0000-0000-0000-000000000011"),
        client_id=UUID("00000000-0000-0000-0000-000000000012"),
        phone="+77055740455",
    )

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("legacy delegate should not be called when secret preflight raises")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda db, remote_jid: branch)

    def _raise_invalid_secret(*args, **kwargs):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    monkeypatch.setattr(reasoning_core, "_run_secret_enforced_preflight", _raise_invalid_secret)

    with pytest.raises(HTTPException, match="Invalid webhook secret") as exc_info:
        await reasoning_core.handle_webhook_payload(
            payload,
            Mock(),
            provided_secret="secret",
            enforce_secret=True,
        )

    assert exc_info.value.status_code == 401


def test_run_secret_enforced_preflight_reuses_legacy_http_preflight(monkeypatch):
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

    def _fake_run_preflight(payload, db, **kwargs):
        captured["payload"] = payload
        captured["db"] = db
        captured["kwargs"] = kwargs
        return None, {"client": "ok"}

    monkeypatch.setattr(
        "app.routers.webhook.http._run_preflight",
        _fake_run_preflight,
    )

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


def test_http_preflight_bridge_cache_short_circuits_duplicate_non_secret_preflight():
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(message="hello"),
    )
    db = Mock()
    cached_payload = {"client": "cached", "message_text": "hello"}
    conversation_id = UUID("00000000-0000-0000-0000-000000000120")

    with http_router._use_preflight_bridge_cache(
        payload,
        db,
        conversation_id=conversation_id,
        preflight_payload=cached_payload,
    ):
        response, preflight_payload = http_router._run_preflight(
            payload,
            db,
            provided_secret=None,
            enforce_secret=False,
            conversation_id=conversation_id,
            resolve_trace_conversation=lambda **kwargs: (_ for _ in ()).throw(
                AssertionError("resolve_trace_conversation should not run on cached preflight")
            ),
            record_early_trace=lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("record_early_trace should not run on cached preflight")
            ),
        )

    assert response is None
    assert preflight_payload is cached_payload


def test_http_preflight_bridge_cache_resets_after_context_exit():
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(message="hello"),
    )
    db = Mock()
    cached_payload = {"client": "cached"}
    conversation_id = UUID("00000000-0000-0000-0000-000000000121")

    with http_router._use_preflight_bridge_cache(
        payload,
        db,
        conversation_id=conversation_id,
        preflight_payload=cached_payload,
    ):
        assert (
            http_router._get_preflight_bridge_cache_payload(
                payload,
                db,
                conversation_id=conversation_id,
                enforce_secret=False,
            )
            is cached_payload
        )

    assert (
        http_router._get_preflight_bridge_cache_payload(
            payload,
            db,
            conversation_id=conversation_id,
            enforce_secret=False,
        )
        is None
    )


@pytest.mark.asyncio
async def test_reasoning_core_secret_preflight_bridge_primes_duplicate_http_preflight(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hello",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-secret-preflight-cache-1",
            ),
        ),
    )
    db = Mock()
    conversation_id = UUID("00000000-0000-0000-0000-000000000122")
    cached_preflight_payload = {
        "client": "cached",
        "settings": None,
        "body": payload.body,
        "metadata": payload.body.metadata,
        "message_id": payload.body.metadata.messageId,
        "remote_jid": payload.body.metadata.remoteJid,
        "message_text": payload.body.message,
        "message_type": payload.body.messageType,
        "has_media": False,
        "is_media_without_text": False,
        "media_info": None,
        "tenant_context": {"client_slug": "demo_salon", "source": "webhook"},
    }

    monkeypatch.setattr(
        reasoning_core,
        "_run_secret_enforced_preflight",
        lambda *args, **kwargs: (None, cached_preflight_payload),
    )

    async def _greeting_owner(**kwargs):
        response, preflight_payload = http_router._run_preflight(
            kwargs["payload"],
            kwargs["db"],
            provided_secret="secret",
            enforce_secret=False,
            conversation_id=kwargs["conversation_id"],
            resolve_trace_conversation=lambda **trace_kwargs: None,
            record_early_trace=lambda *trace_args, **trace_kwargs: False,
        )
        assert response is None
        assert preflight_payload is cached_preflight_payload
        return WebhookResponse(success=True, message="owner")

    monkeypatch.setattr(
        reasoning_core,
        "_try_handle_turn_planner_safe_greeting_owner_cutover",
        _greeting_owner,
    )

    response = await reasoning_core.handle_webhook_payload(
        payload,
        db,
        provided_secret="secret",
        enforce_secret=True,
        conversation_id=conversation_id,
    )

    assert response.success is True
    assert response.message == "owner"


@pytest.mark.asyncio
async def test_reasoning_core_non_secret_preflight_payload_primes_owner_path(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Привет",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-direct-preflight-1",
            ),
        ),
        tenant_context=WebhookTenantContext(
            client_id="00000000-0000-0000-0000-000000000130",
            client_slug="demo_salon",
            source="webhook",
        ),
    )
    db = Mock()
    client_id = UUID("00000000-0000-0000-0000-000000000130")
    branch_id = UUID("00000000-0000-0000-0000-000000000131")
    conversation_id = UUID("00000000-0000-0000-0000-000000000132")
    capability_runtime = RuntimeCapabilities(
        payload=CapabilitiesPayload(),
        client_id=client_id,
        branch_id=branch_id,
        source="reasoning_core",
        has_records=False,
    )
    truth_runtime = RuntimeTruth(
        truth={"salon": {"name": "Bridge"}},
        client_slug="demo_salon",
        branch_id=branch_id,
        source="reasoning_core",
        allow_fallback=False,
    )
    cached_preflight_payload = {
        "client": SimpleNamespace(id=client_id, config={}),
        "settings": None,
        "body": payload.body,
        "metadata": payload.body.metadata,
        "message_id": payload.body.metadata.messageId,
        "remote_jid": payload.body.metadata.remoteJid,
        "message_text": payload.body.message,
        "message_type": payload.body.messageType,
        "has_media": False,
        "is_media_without_text": False,
        "media_info": None,
        "resolved_branch_id": branch_id,
        "tenant_context": {
            "client_id": str(client_id),
            "client_slug": "demo_salon",
            "source": "webhook",
            "branch_id": str(branch_id),
        },
    }
    captured: dict[str, object] = {}

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_get_preflight_tenant_context_rejection",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_preflight_client_id",
        lambda *args, **kwargs: client_id,
    )
    def _resolve_snapshot(*args, **kwargs):
        captured["preflight_payload"] = kwargs.get("preflight_payload")
        return reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation_id,
            state="bot_active",
            bot_status="active",
            branch_id=branch_id,
            reply_slot=None,
            current_goal=None,
            booking_active=False,
            allow_bot_reply=True,
        )

    monkeypatch.setattr(reasoning_core, "_resolve_active_conversation_snapshot", _resolve_snapshot)
    monkeypatch.setattr(
        reasoning_core,
        "build_runtime_capabilities",
        lambda *args, **kwargs: capability_runtime,
    )
    monkeypatch.setattr(
        reasoning_core,
        "build_runtime_truth",
        lambda *args, **kwargs: truth_runtime,
    )

    async def _greeting_owner(**kwargs):
        assert kwargs["preflight_payload"] is cached_preflight_payload
        assert get_runtime_capabilities() is capability_runtime
        assert get_runtime_truth() is truth_runtime
        response, bridged_payload = http_router._run_preflight(
            kwargs["payload"],
            kwargs["db"],
            provided_secret=None,
            enforce_secret=False,
            conversation_id=kwargs["conversation_id"],
            resolve_trace_conversation=lambda **trace_kwargs: None,
            record_early_trace=lambda *trace_args, **trace_kwargs: False,
        )
        assert response is None
        assert bridged_payload is cached_preflight_payload
        return WebhookResponse(success=True, message="owner")

    monkeypatch.setattr(
        reasoning_core,
        "_try_handle_turn_planner_safe_greeting_owner_cutover",
        _greeting_owner,
    )

    response = await reasoning_core.handle_webhook_payload(
        payload,
        db,
        provided_secret=None,
        enforce_secret=False,
        conversation_id=conversation_id,
        preflight_payload=cached_preflight_payload,
    )

    assert response.success is True
    assert response.message == "owner"
    assert captured["preflight_payload"] is cached_preflight_payload
    assert get_runtime_capabilities() is None
    assert get_runtime_truth() is None


def test_reasoning_core_default_runtime_no_longer_contains_ingress_semantic_override_priming():
    source = inspect.getsource(reasoning_core.handle_webhook_payload)

    assert "_use_intent_routing_primitives_override" not in source
    assert "_use_domain_routing_snapshot_override" not in source
    assert "_use_controller_route_snapshot_override" not in source
    assert "_use_policy_core_route_snapshot_override" not in source
    assert "use_intent_signal_override" not in source
    assert "use_intent_semantic_override" not in source
    assert "use_dialogue_controller_override" not in source
    assert "use_domain_routing_override" not in source


@pytest.mark.asyncio
async def test_reasoning_core_handle_webhook_payload_delegates_directly_to_consultant_runtime(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Привет",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-reasoning-core-direct-delegate-1",
            ),
        ),
    )
    db = Mock()
    captured: dict[str, object] = {}

    async def _delegate(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return WebhookResponse(success=True, message="delegated-runtime")

    monkeypatch.setattr("app.core.consultant_runtime.handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        db,
        provided_secret="secret",
        enforce_secret=True,
        enqueue_only=True,
        skip_persist=True,
        conversation_id=UUID("00000000-0000-0000-0000-000000000191"),
        batch_messages=["a", "b"],
        outbox_ids=["outbox-1"],
    )

    assert response.message == "delegated-runtime"
    assert captured["args"] == (payload, db)
    assert captured["kwargs"]["provided_secret"] == "secret"
    assert captured["kwargs"]["enforce_secret"] is True
    assert captured["kwargs"]["enqueue_only"] is True
    assert captured["kwargs"]["skip_persist"] is True
    assert captured["kwargs"]["batch_messages"] == ["a", "b"]
    assert captured["kwargs"]["outbox_ids"] == ["outbox-1"]


@pytest.mark.asyncio
async def test_decision_router_handle_webhook_payload_delegates_directly_to_consultant_runtime(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Привет",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-webhook-router-direct-delegate-1",
            ),
        ),
    )
    db = Mock()
    captured: dict[str, object] = {}

    async def _delegate(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return WebhookResponse(success=True, message="delegated-router")

    monkeypatch.setattr("app.core.consultant_runtime.handle_webhook_payload", _delegate)

    response = await decision_router._handle_webhook_payload(
        payload,
        db,
        provided_secret=None,
        enforce_secret=False,
        enqueue_only=False,
        skip_persist=False,
        conversation_id=UUID("00000000-0000-0000-0000-000000000192"),
        batch_messages=["x"],
        outbox_ids=["outbox-2"],
    )

    assert response.message == "delegated-router"
    assert captured["args"] == (payload, db)
    assert captured["kwargs"]["provided_secret"] is None
    assert captured["kwargs"]["enforce_secret"] is False
    assert captured["kwargs"]["batch_messages"] == ["x"]
    assert captured["kwargs"]["outbox_ids"] == ["outbox-2"]


@pytest.mark.asyncio
async def test_reasoning_core_primes_policy_core_handoff_override_for_manager_request_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу поговорить с менеджером",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-policy-handoff-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == "хочу поговорить с менеджером"
        assert policy_override["intent"] == "human_request"
        assert policy_override["action"] == "handoff"
        assert policy_override["tool_action"] == "handoff"
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("Хочу поговорить с менеджером")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["needs_manager"] is True
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_explicit_handoff_owner_bypasses_frozen_delegate_create_path(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу поговорить с менеджером",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-explicit-handoff-owner-create-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000180"),
        client_id=UUID("00000000-0000-0000-0000-000000000280"),
        user_id=UUID("00000000-0000-0000-0000-000000000380"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    user = User(
        id=conversation.user_id,
        client_id=conversation.client_id,
        remote_jid="77000000000@s.whatsapp.net",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    handover = Mock(id=UUID("00000000-0000-0000-0000-000000000480"), _reopened=False)
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []
    escalation_metrics: list[tuple[str | None, str]] = []
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(reasoning_core, "_resolve_turn_planner_owner_client", lambda *args, **kwargs: client)
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_user",
        lambda *args, **kwargs: user,
    )
    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    def _materialize_handover(**kwargs):
        conversation.state = "pending"
        return SimpleNamespace(
            ok=True,
            handover=handover,
            mode="create",
            telegram_sent=True,
            handover_reopened=False,
        )

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "record_escalation_count", lambda client_slug, trigger: escalation_metrics.append((client_slug, trigger)))
    monkeypatch.setattr(reasoning_core, "materialize_handover", _materialize_handover)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe explicit handoff sent"
    assert response.bot_response == decision_router.MSG_ESCALATED
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert escalation_metrics == [("demo_salon", "intent")]
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "escalate"
    assert user_metadata.get("intent") == "human_request"
    assert user_metadata.get("source") == "consultant_core_runtime"
    assert user_metadata.get("tool_action") == "handoff"
    assert user_metadata.get("needs_manager") is True
    assert user_metadata.get("handoff_mode") == "create"
    assert user_metadata.get("telegram_sent") is True
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_OWNER
    )
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("downstream_tool_decision")
        == "handover_created"
    )
    turn_outcome = user_metadata.get("turn_outcome") or {}
    assert turn_outcome.get("action") == "escalate"
    assert turn_outcome.get("intent") == "human_request"
    assert turn_outcome.get("tool_action") == "handoff"
    assert turn_outcome.get("tool_decision") == "planner_owner_cutover"
    assert turn_outcome.get("observability", {}).get("transport_status") == "delivered"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "escalation"
        and entry.get("decision") == "created"
        and entry.get("intent") == "human_request"
        and entry.get("telegram_sent") is True
        for entry in trace
    )
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_STAGE
        and entry.get("handoff_mode") == "create"
        and entry.get("telegram_sent") is True
        for entry in trace
    )
    assert conversation.state == "pending"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_explicit_handoff_owner_uses_simulation_safe_transport(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу поговорить с менеджером",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-explicit-handoff-owner-sim-1",
                simulation_mode=True,
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-0000000001a0"),
        client_id=UUID("00000000-0000-0000-0000-0000000002a0"),
        user_id=UUID("00000000-0000-0000-0000-0000000003a0"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    user = User(
        id=conversation.user_id,
        client_id=conversation.client_id,
        remote_jid="77000000000@s.whatsapp.net",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    handover = Mock(id=UUID("00000000-0000-0000-0000-0000000004a0"), _reopened=False)
    saved_messages: list[Message] = []
    adapter_calls: list[dict[str, object]] = []
    direct_send_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(reasoning_core, "_resolve_turn_planner_owner_client", lambda *args, **kwargs: client)
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_user",
        lambda *args, **kwargs: user,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    def _materialize_handover(**kwargs):
        conversation.state = "pending"
        return SimpleNamespace(
            ok=True,
            handover=handover,
            mode="create",
            telegram_sent=True,
            handover_reopened=False,
        )

    class _FakeAdapter:
        def send_text(self, to, text, options):
            adapter_calls.append(
                {
                    "to": to,
                    "text": text,
                    "instance_id": options.instance_id,
                    "idempotency_key": options.idempotency_key,
                    "extra": dict(options.extra),
                }
            )
            return Ok("simulated")

    async def _delegate(*args, **kwargs):
        return WebhookResponse(success=True, message="delegated")

    def _direct_send(*args, **kwargs):
        direct_send_calls.append((args, kwargs))
        raise AssertionError("send_message_safe should be bypassed in simulation mode")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "record_escalation_count", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "materialize_handover", _materialize_handover)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "ChatFlowAdapter", _FakeAdapter)
    monkeypatch.setattr(reasoning_core, "send_message_safe", _direct_send)
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe explicit handoff sent"
    assert response.bot_response == decision_router.MSG_ESCALATED
    assert direct_send_calls == []
    assert len(adapter_calls) == 1
    assert adapter_calls[0]["to"] == "77000000000@s.whatsapp.net"
    assert adapter_calls[0]["instance_id"] == "inst-1"
    assert adapter_calls[0]["idempotency_key"] == "msg-explicit-handoff-owner-sim-1"
    assert adapter_calls[0]["extra"] == {"simulation_mode": True}

    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("transport_simulated") is True
    assert user_metadata.get("handoff_mode") == "create"
    turn_outcome = user_metadata.get("turn_outcome") or {}
    assert turn_outcome.get("observability", {}).get("transport_status") == "delivered"
    assert conversation.state == "pending"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_explicit_handoff_owner_bypasses_frozen_delegate_reuse_path(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Заебал",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-explicit-handoff-owner-reuse-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000181"),
        client_id=UUID("00000000-0000-0000-0000-000000000281"),
        user_id=UUID("00000000-0000-0000-0000-000000000381"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="pending",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    user = User(
        id=conversation.user_id,
        client_id=conversation.client_id,
        remote_jid="77000000000@s.whatsapp.net",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    active_handover = Mock(id=UUID("00000000-0000-0000-0000-000000000481"))
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(reasoning_core, "_resolve_turn_planner_owner_client", lambda *args, **kwargs: client)
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_user",
        lambda *args, **kwargs: user,
    )
    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    def _materialize_handover(**kwargs):
        return SimpleNamespace(
            ok=True,
            handover=active_handover,
            mode="reuse",
            telegram_sent=False,
            handover_reopened=False,
        )

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "materialize_handover", _materialize_handover)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe explicit handoff sent"
    assert response.bot_response == decision_router.MSG_ESCALATED
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "escalate"
    assert user_metadata.get("intent") == "frustration"
    assert user_metadata.get("handoff_mode") == "reuse"
    assert user_metadata.get("telegram_sent") is False
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("downstream_tool_decision")
        == "handover_reused"
    )
    turn_outcome = user_metadata.get("turn_outcome") or {}
    assert turn_outcome.get("action") == "escalate"
    assert turn_outcome.get("intent") == "frustration"
    assert turn_outcome.get("tool_action") == "handoff"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_STAGE
        and entry.get("handoff_mode") == "reuse"
        and entry.get("telegram_sent") is False
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_explicit_handoff_owner_family_defers_pending_ack(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="ок",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-explicit-handoff-owner-pending-ack",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000182"),
        client_id=UUID("00000000-0000-0000-0000-000000000282"),
        user_id=UUID("00000000-0000-0000-0000-000000000382"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="pending",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    user_calls: list[bool] = []

    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(pending_router, "_is_pending_ack", lambda text: True)
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_user",
        lambda *args, **kwargs: user_calls.append(True) or None,
    )

    response = await reasoning_core._try_handle_turn_planner_safe_explicit_handoff_owner_cutover(
        payload=payload,
        db=mock_db,
        client_id=conversation.client_id,
        preflight_payload=None,
        conversation_id=conversation.id,
        pending_booking_resume_boundary_payload=None,
        enqueue_only=False,
        skip_persist=False,
        policy_core_route_snapshot=SimpleNamespace(
            to_override=lambda: {
                "intent": "human_request",
                "action": "handoff",
                "tool_action": "handoff",
                "reason": "ingress_explicit_human_request",
                "goal": "handoff",
                "slots": {},
                "next_question": None,
                "open_questions": [],
                "needs_manager": True,
            }
        ),
    )

    assert response is None
    assert user_calls == []


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_explicit_handoff_owner_family_defers_session_reset_only_message(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="начнем сначала",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-explicit-handoff-owner-session-reset",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000183"),
        client_id=UUID("00000000-0000-0000-0000-000000000283"),
        user_id=UUID("00000000-0000-0000-0000-000000000383"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    user_calls: list[bool] = []

    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_user",
        lambda *args, **kwargs: user_calls.append(True) or None,
    )

    response = await reasoning_core._try_handle_turn_planner_safe_explicit_handoff_owner_cutover(
        payload=payload,
        db=mock_db,
        client_id=conversation.client_id,
        preflight_payload=None,
        conversation_id=conversation.id,
        pending_booking_resume_boundary_payload=None,
        enqueue_only=False,
        skip_persist=False,
        policy_core_route_snapshot=SimpleNamespace(
            to_override=lambda: {
                "intent": "human_request",
                "action": "handoff",
                "tool_action": "handoff",
                "reason": "ingress_explicit_human_request",
                "goal": "handoff",
                "slots": {},
                "next_question": None,
                "open_questions": [],
                "needs_manager": True,
            }
        ),
    )

    assert response is None
    assert user_calls == []


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_reschedule_guard_handoff_bypasses_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Что если я захочу изменить время?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-reschedule-guard-handoff-owner-create-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000183"),
        client_id=UUID("00000000-0000-0000-0000-000000000283"),
        user_id=UUID("00000000-0000-0000-0000-000000000383"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "booking": {"active": True, "service": "Маникюр"},
            "current_goal": "booking",
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    user = User(
        id=conversation.user_id,
        client_id=conversation.client_id,
        remote_jid="77000000000@s.whatsapp.net",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    handover = Mock(id=UUID("00000000-0000-0000-0000-000000000483"), _reopened=False)
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []
    escalation_metrics: list[tuple[str | None, str]] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=None,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason=None,
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(reasoning_core, "_resolve_turn_planner_owner_client", lambda *args, **kwargs: client)
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_user",
        lambda *args, **kwargs: user,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "consult",
                "action": "fact",
                "tool_action": "info",
                "goal": "consult",
                "reason": "consult_info_reply",
                "tool_args": {"service_query": "Маникюр"},
                "pack_refs": ["hours"],
                "slots": {"service": "Маникюр"},
                "needs_manager": False,
                "risk_signals": [],
            },
        },
    )
    monkeypatch.setattr(
        decision_router,
        "_looks_like_booking_reschedule_request",
        lambda *args, **kwargs: True,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    def _materialize_handover(**kwargs):
        conversation.state = "pending"
        return SimpleNamespace(
            ok=True,
            handover=handover,
            mode="create",
            telegram_sent=True,
            handover_reopened=False,
        )

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(
        reasoning_core,
        "record_escalation_count",
        lambda client_slug, trigger: escalation_metrics.append((client_slug, trigger)),
    )
    monkeypatch.setattr(reasoning_core, "materialize_handover", _materialize_handover)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe explicit handoff sent"
    assert response.bot_response == decision_router.MSG_ESCALATED
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert escalation_metrics == [("demo_salon", "intent")]
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "escalate"
    assert user_metadata.get("intent") == "reschedule"
    assert user_metadata.get("source") == "booking_verification"
    assert user_metadata.get("tool_action") == "handoff"
    assert user_metadata.get("handoff_mode") == "create"
    assert user_metadata.get("telegram_sent") is True
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_OWNER
    )
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("downstream_tool_decision")
        == "handover_created"
    )
    turn_outcome = user_metadata.get("turn_outcome") or {}
    assert turn_outcome.get("action") == "escalate"
    assert turn_outcome.get("intent") == "reschedule"
    assert turn_outcome.get("tool_action") == "handoff"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "escalation"
        and entry.get("decision") == "created"
        and entry.get("intent") == "reschedule"
        and entry.get("telegram_sent") is True
        for entry in trace
    )
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_STAGE
        and entry.get("intent") == "reschedule"
        and entry.get("reason") == "reschedule_missing_reference"
        and entry.get("handoff_mode") == "create"
        for entry in trace
    )
    assert conversation.state == "pending"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_timeout_degraded_collect_reschedule_handoff_bypasses_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Мне нужно перенести запись",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-timeout-degraded-collect-reschedule-handoff-owner-create-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000184"),
        client_id=UUID("00000000-0000-0000-0000-000000000284"),
        user_id=UUID("00000000-0000-0000-0000-000000000384"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "last_question": "datetime",
            },
            "current_goal": "booking",
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    user = User(
        id=conversation.user_id,
        client_id=conversation.client_id,
        remote_jid="77000000000@s.whatsapp.net",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    handover = Mock(id=UUID("00000000-0000-0000-0000-000000000484"), _reopened=False)
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []
    escalation_metrics: list[tuple[str | None, str]] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="time",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(reasoning_core, "_resolve_turn_planner_owner_client", lambda *args, **kwargs: client)
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_user",
        lambda *args, **kwargs: user,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": False,
            "payload": None,
            "error": "timeout",
            "attempted": True,
            "elapsed_ms": 42.0,
        },
    )
    monkeypatch.setattr(
        decision_router,
        "_looks_like_booking_reschedule_request",
        lambda *args, **kwargs: True,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    def _materialize_handover(**kwargs):
        conversation.state = "pending"
        return SimpleNamespace(
            ok=True,
            handover=handover,
            mode="create",
            telegram_sent=True,
            handover_reopened=False,
        )

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(
        reasoning_core,
        "record_escalation_count",
        lambda client_slug, trigger: escalation_metrics.append((client_slug, trigger)),
    )
    monkeypatch.setattr(reasoning_core, "materialize_handover", _materialize_handover)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe explicit handoff sent"
    assert response.bot_response == decision_router.MSG_ESCALATED
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert escalation_metrics == [("demo_salon", "intent")]
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "escalate"
    assert user_metadata.get("intent") == "reschedule"
    assert user_metadata.get("source") == "booking_verification"
    assert user_metadata.get("tool_action") == "handoff"
    assert user_metadata.get("handoff_mode") == "create"
    assert user_metadata.get("telegram_sent") is True
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_OWNER
    )
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("downstream_tool_decision")
        == "handover_created"
    )
    turn_outcome = user_metadata.get("turn_outcome") or {}
    assert turn_outcome.get("action") == "escalate"
    assert turn_outcome.get("intent") == "reschedule"
    assert turn_outcome.get("tool_action") == "handoff"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "escalation"
        and entry.get("decision") == "created"
        and entry.get("intent") == "reschedule"
        and entry.get("telegram_sent") is True
        for entry in trace
    )
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_STAGE
        and entry.get("intent") == "reschedule"
        and entry.get("reason") == "reschedule_missing_reference"
        and entry.get("handoff_mode") == "create"
        for entry in trace
    )
    assert conversation.state == "pending"
    assert mock_db.commit.call_count == 1


async def test_reasoning_core_turn_planner_safe_explicit_handoff_owner_returns_terminal_unresolved_without_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу поговорить с менеджером",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-explicit-handoff-owner-fallback-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000182"),
        client_id=UUID("00000000-0000-0000-0000-000000000282"),
        user_id=UUID("00000000-0000-0000-0000-000000000382"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="pending",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(reasoning_core, "_resolve_turn_planner_owner_client", lambda *args, **kwargs: client)
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("frozen delegate must stay dead")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Reasoning core terminal unresolved response sent"
    assert response.bot_response == decision_router.MSG_AI_ERROR
    assert intent_service.get_policy_core_override() is None
    assert mock_db.commit.call_count == 0


@pytest.mark.asyncio
async def test_reasoning_core_primes_style_reference_policy_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Я могу прислать фото своей прически?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-style-reference-policy-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == "я могу прислать фото своей прически"
        assert policy_override["intent"] == "portfolio"
        assert policy_override["action"] == "fact"
        assert policy_override["tool_action"] == "catalog.portfolio"
        assert policy_override["reason"] == "style_reference_text"
        assert policy_override["goal"] == "info"
        assert policy_override["pack_refs"] == ["portfolio"]
        assert policy_override["capability"] == "portfolio"
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("Я могу прислать фото своей прически?")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["intent"] == "portfolio"
        assert policy_result["payload"]["action"] == "fact"
        assert policy_result["payload"]["tool_action"] == "catalog.portfolio"
        assert policy_result["payload"]["goal"] == "info"
        assert policy_result["payload"]["pack_refs"] == ["portfolio"]
        assert policy_result["payload"]["capability"] == "portfolio"
        assert policy_result["payload"]["needs_manager"] is False
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_primes_booking_verification_policy_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Проверьте, пожалуйста, мою запись",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-verification-policy-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == "проверьте, пожалуйста, мою запись"
        assert policy_override["intent"] == "check_booking"
        assert policy_override["action"] == "fact"
        assert policy_override["tool_action"] == "calendar.get_booking"
        assert policy_override["reason"] == "booking_verification_text"
        assert policy_override["goal"] == "booking"
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("Проверьте, пожалуйста, мою запись")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["intent"] == "check_booking"
        assert policy_result["payload"]["action"] == "fact"
        assert policy_result["payload"]["tool_action"] == "calendar.get_booking"
        assert policy_result["payload"]["goal"] == "booking"
        assert policy_result["payload"]["needs_manager"] is False
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_primes_services_overview_policy_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Что вы предлагаете?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-services-overview-policy-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == "что вы предлагаете"
        assert policy_override["intent"] == "services_overview"
        assert policy_override["action"] == "fact"
        assert policy_override["tool_action"] == "catalog.service_query"
        assert policy_override["reason"] == "services_overview"
        assert policy_override["goal"] == "info"
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("Что вы предлагаете?")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["intent"] == "services_overview"
        assert policy_result["payload"]["action"] == "fact"
        assert policy_result["payload"]["tool_action"] == "catalog.service_query"
        assert policy_result["payload"]["goal"] == "info"
        assert policy_result["payload"]["needs_manager"] is False
        assert policy_result["payload"]["tool_args"] == {}
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_primes_location_policy_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Где вы находитесь?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-location-policy-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == "где вы находитесь"
        assert policy_override["intent"] == "info"
        assert policy_override["action"] == "fact"
        assert policy_override["tool_action"] == "catalog.location"
        assert policy_override["reason"] == "location_question"
        assert policy_override["goal"] == "info"
        assert policy_override["pack_refs"] == ["location"]
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("Где вы находитесь?")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["intent"] == "info"
        assert policy_result["payload"]["action"] == "fact"
        assert policy_result["payload"]["tool_action"] == "catalog.location"
        assert policy_result["payload"]["reason"] == "location_question"
        assert policy_result["payload"]["goal"] == "info"
        assert policy_result["payload"]["pack_refs"] == ["location"]
        assert policy_result["payload"]["needs_manager"] is False
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_primes_hours_policy_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какие часы работы?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-hours-policy-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == "какие часы работы"
        assert policy_override["intent"] == "hours"
        assert policy_override["action"] == "fact"
        assert policy_override["tool_action"] == "info"
        assert policy_override["reason"] == "hours_question"
        assert policy_override["goal"] == "info"
        assert policy_override["pack_refs"] == ["hours"]
        assert policy_override["capability"] == "hours"
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("Какие часы работы?")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["intent"] == "hours"
        assert policy_result["payload"]["action"] == "fact"
        assert policy_result["payload"]["tool_action"] == "info"
        assert policy_result["payload"]["reason"] == "hours_question"
        assert policy_result["payload"]["goal"] == "info"
        assert policy_result["payload"]["pack_refs"] == ["hours"]
        assert policy_result["payload"]["capability"] == "hours"
        assert policy_result["payload"]["needs_manager"] is False
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_primes_pricing_policy_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько стоит маникюр?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-pricing-policy-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == "сколько стоит маникюр"
        assert policy_override["intent"] == "info"
        assert policy_override["action"] == "fact"
        assert policy_override["tool_action"] == "catalog.service_query"
        assert policy_override["tool_args"] == {"service_query": "Маникюр"}
        assert policy_override["reason"] == "pricing_query"
        assert policy_override["goal"] == "booking"
        assert policy_override["pack_refs"] == ["pricing"]
        assert policy_override["capability"] == "pricing"
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("Сколько стоит маникюр?")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["intent"] == "info"
        assert policy_result["payload"]["action"] == "fact"
        assert policy_result["payload"]["tool_action"] == "catalog.service_query"
        assert policy_result["payload"]["tool_args"] == {"service_query": "Маникюр"}
        assert policy_result["payload"]["reason"] == "pricing_query"
        assert policy_result["payload"]["goal"] == "booking"
        assert policy_result["payload"]["pack_refs"] == ["pricing"]
        assert policy_result["payload"]["capability"] == "pricing"
        assert policy_result["payload"]["needs_manager"] is False
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_primes_duration_policy_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько длится маникюр?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-duration-policy-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == "сколько длится маникюр"
        assert policy_override["intent"] == "duration"
        assert policy_override["action"] == "fact"
        assert policy_override["tool_action"] == "catalog.service_query"
        assert policy_override["tool_args"] == {"service_query": "Маникюр"}
        assert policy_override["reason"] == "duration_info"
        assert policy_override["goal"] == "booking"
        assert policy_override["pack_refs"] == ["duration"]
        assert policy_override["capability"] == "duration"
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("Сколько длится маникюр?")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["intent"] == "duration"
        assert policy_result["payload"]["action"] == "fact"
        assert policy_result["payload"]["tool_action"] == "catalog.service_query"
        assert policy_result["payload"]["tool_args"] == {"service_query": "Маникюр"}
        assert policy_result["payload"]["reason"] == "duration_info"
        assert policy_result["payload"]["goal"] == "booking"
        assert policy_result["payload"]["pack_refs"] == ["duration"]
        assert policy_result["payload"]["capability"] == "duration"
        assert policy_result["payload"]["needs_manager"] is False
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_primes_active_service_duration_policy_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="А сколько по времени?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-duration-policy-bridge-active-service-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000111"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_TIME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_slot_guidance",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent="Маникюр",
        ),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["intent"] == "duration"
        assert policy_override["action"] == "fact"
        assert policy_override["tool_action"] == "catalog.service_query"
        assert policy_override["tool_args"] == {"service_query": "Маникюр"}
        assert policy_override["reason"] == "duration_info"
        assert policy_override["goal"] == "booking"
        assert policy_override["pack_refs"] == ["duration"]
        assert policy_override["capability"] == "duration"
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("А сколько по времени?")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["intent"] == "duration"
        assert policy_result["payload"]["action"] == "fact"
        assert policy_result["payload"]["tool_action"] == "catalog.service_query"
        assert policy_result["payload"]["tool_args"] == {"service_query": "Маникюр"}
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_info_owner_handles_promotions_without_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Есть ли у вас акции?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-promotions-policy-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000611"),
        client_id=UUID("00000000-0000-0000-0000-000000000612"),
        user_id=UUID("00000000-0000-0000-0000-000000000613"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        info_router,
        "_build_info_intent_reply",
        lambda *args, **kwargs: (
            "Да, сейчас действует скидка 10% на первое посещение.",
            {"info_sections": ["promotions"], "resolver_id": "webhook.info_intent"},
        ),
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe info fact sent"
    assert response.bot_response == "Да, сейчас действует скидка 10% на первое посещение."
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "reply"
    assert user_metadata.get("intent") == "promotions"
    assert user_metadata.get("consultant_core_runtime", {}).get("outcome") == "FACT"
    assert user_metadata.get("turn_outcome", {}).get("tool_decision") == "planner_owner_cutover"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_info_owner_handles_promotions_rules_without_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Скидки суммируются?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-promotions-rules-policy-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000621"),
        client_id=UUID("00000000-0000-0000-0000-000000000622"),
        user_id=UUID("00000000-0000-0000-0000-000000000623"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        info_router,
        "_build_info_intent_reply",
        lambda *args, **kwargs: (
            "Скидки и акции не суммируются между собой.",
            {"info_sections": ["promotions"], "resolver_id": "webhook.info_intent"},
        ),
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe info fact sent"
    assert response.bot_response == "Скидки и акции не суммируются между собой."
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "reply"
    assert user_metadata.get("intent") == "promotions_rules"
    assert user_metadata.get("consultant_core_runtime", {}).get("outcome") == "FACT"
    assert user_metadata.get("turn_outcome", {}).get("tool_decision") == "planner_owner_cutover"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_primes_contact_policy_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой у вас номер телефона?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-contact-policy-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == ai_service.normalize_for_matching(
            "Какой у вас номер телефона?"
        )
        assert policy_override["intent"] == "contact"
        assert policy_override["action"] == "fact"
        assert policy_override["tool_action"] == "info"
        assert policy_override["reason"] == "contact_question"
        assert policy_override["goal"] == "info"
        assert policy_override["pack_refs"] == ["contact"]
        assert policy_override["capability"] is None
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("Какой у вас номер телефона?")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["intent"] == "contact"
        assert policy_result["payload"]["action"] == "fact"
        assert policy_result["payload"]["tool_action"] == "info"
        assert policy_result["payload"]["reason"] == "contact_question"
        assert policy_result["payload"]["goal"] == "info"
        assert policy_result["payload"]["pack_refs"] == ["contact"]
        assert policy_result["payload"]["capability"] is None
        assert policy_result["payload"]["needs_manager"] is False
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_info_owner_falls_back_when_truth_reply_missing(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой у вас номер телефона?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-contact-owner-cutover-2",
            ),
        ),
    )
    mock_db = Mock()
    saved_messages: list[Message] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(info_router, "_build_info_intent_reply", lambda *args, **kwargs: (None, None))
    monkeypatch.setattr(
        reasoning_core,
        "save_message",
        lambda *args, **kwargs: saved_messages.append(True),
    )

    async def _delegate(*args, **kwargs):
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Reasoning core terminal unresolved response skipped"
    assert saved_messages == []


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_catalog_owner_bypasses_frozen_delegate_for_services_overview(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Что вы предлагаете?",
            metadata=WebhookMetadata(
                remoteJid="77000000002@s.whatsapp.net",
                messageId="msg-services-overview-owner-cutover-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000621"),
        client_id=UUID("00000000-0000-0000-0000-000000000622"),
        user_id=UUID("00000000-0000-0000-0000-000000000623"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "execute_tool_action",
        lambda *args, **kwargs: ToolExecutionResult(
            handled=True,
            ok=True,
            response_text="У нас есть маникюр и педикюр.",
            error_code=None,
            decision_meta={
                "tool_action": "catalog.service_query",
                "tool_decision": "services_overview",
                "info_sections": ["services_overview"],
            },
            trace={
                "stage": "tool_registry",
                "decision": "services_overview",
                "tool_action": "catalog.service_query",
                "info_sections": ["services_overview"],
            },
        ),
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe catalog fact sent"
    assert response.bot_response == "У нас есть маникюр и педикюр."
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("intent") == "services_overview"
    assert user_metadata.get("tool_action") == "catalog.service_query"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("downstream_tool_decision")
        == "services_overview"
    )
    assert user_metadata.get("turn_outcome", {}).get("tool_decision") == "planner_owner_cutover"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_catalog_owner_falls_back_when_tool_result_not_safe(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Где вы находитесь?",
            metadata=WebhookMetadata(
                remoteJid="77000000003@s.whatsapp.net",
                messageId="msg-location-owner-cutover-2",
            ),
        ),
    )
    mock_db = Mock()
    saved_messages: list[Message] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "execute_tool_action",
        lambda *args, **kwargs: ToolExecutionResult(
            handled=True,
            ok=False,
            response_text="Адрес сейчас недоступен.",
            error_code="not_found",
            decision_meta={
                "tool_action": "catalog.location",
                "tool_decision": "not_found",
            },
            trace={
                "stage": "tool_registry",
                "decision": "not_found",
                "tool_action": "catalog.location",
            },
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "save_message",
        lambda *args, **kwargs: saved_messages.append(True),
    )

    async def _delegate(*args, **kwargs):
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert saved_messages == []


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_catalog_owner_bypasses_portfolio_not_found(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Покажите примеры работ по маникюру",
            metadata=WebhookMetadata(
                remoteJid="77000000004@s.whatsapp.net",
                messageId="msg-portfolio-owner-cutover-2",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000626"),
        client_id=UUID("00000000-0000-0000-0000-000000000627"),
        user_id=UUID("00000000-0000-0000-0000-000000000628"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "execute_tool_action",
        lambda *args, **kwargs: ToolExecutionResult(
            handled=True,
            ok=False,
            response_text="Портфолио сейчас недоступно. Могу помочь подобрать услугу.",
            error_code="portfolio_missing",
            decision_meta={
                "tool_action": "catalog.portfolio",
                "tool_decision": "not_found",
            },
            trace={
                "stage": "tool_registry",
                "decision": "not_found",
                "tool_action": "catalog.portfolio",
            },
        ),
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe catalog fact sent"
    assert response.bot_response == "Портфолио сейчас недоступно. Могу помочь подобрать услугу."
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("intent") == "portfolio"
    assert user_metadata.get("tool_action") == "catalog.portfolio"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("downstream_tool_decision")
        == "not_found"
    )
    assert user_metadata.get("turn_outcome", {}).get("tool_decision") == "planner_owner_cutover"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_service_query_owner_bypasses_frozen_delegate_for_pricing(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько стоит маникюр?",
            metadata=WebhookMetadata(
                remoteJid="77000000004@s.whatsapp.net",
                messageId="msg-pricing-owner-cutover-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000631"),
        client_id=UUID("00000000-0000-0000-0000-000000000632"),
        user_id=UUID("00000000-0000-0000-0000-000000000633"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "execute_tool_action",
        lambda *args, **kwargs: ToolExecutionResult(
            handled=True,
            ok=True,
            response_text="Маникюр стоит 10000 тг.",
            error_code=None,
            decision_meta={
                "tool_action": "catalog.service_query",
                "tool_decision": "truth_fallback",
                "info_sections": ["pricing"],
            },
            trace={
                "stage": "tool_registry",
                "decision": "truth_fallback",
                "tool_action": "catalog.service_query",
                "info_sections": ["pricing"],
            },
        ),
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe service-query fact sent"
    assert response.bot_response == "Маникюр стоит 10000 тг."
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("intent") == "info"
    assert user_metadata.get("tool_action") == "catalog.service_query"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_SERVICE_QUERY_FACT_OWNER
    )
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("downstream_tool_decision")
        == "truth_fallback"
    )
    assert user_metadata.get("turn_outcome", {}).get("tool_decision") == "planner_owner_cutover"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_service_query_owner_bypasses_frozen_delegate_for_duration(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько длится маникюр?",
            metadata=WebhookMetadata(
                remoteJid="77000000005@s.whatsapp.net",
                messageId="msg-duration-owner-cutover-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000641"),
        client_id=UUID("00000000-0000-0000-0000-000000000642"),
        user_id=UUID("00000000-0000-0000-0000-000000000643"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "execute_tool_action",
        lambda *args, **kwargs: ToolExecutionResult(
            handled=True,
            ok=True,
            response_text="Маникюр занимает 90 минут.",
            error_code=None,
            decision_meta={
                "tool_action": "catalog.service_query",
                "tool_decision": "duration",
                "info_sections": ["duration"],
            },
            trace={
                "stage": "tool_registry",
                "decision": "duration",
                "tool_action": "catalog.service_query",
                "info_sections": ["duration"],
            },
        ),
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe service-query fact sent"
    assert response.bot_response == "Маникюр занимает 90 минут."
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("intent") == "duration"
    assert user_metadata.get("tool_action") == "catalog.service_query"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("downstream_tool_decision")
        == "duration"
    )
    assert user_metadata.get("turn_outcome", {}).get("tool_decision") == "planner_owner_cutover"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_service_query_owner_falls_back_on_unapproved_result(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько стоит маникюр?",
            metadata=WebhookMetadata(
                remoteJid="77000000006@s.whatsapp.net",
                messageId="msg-pricing-owner-cutover-2",
            ),
        ),
    )
    mock_db = Mock()
    saved_messages: list[Message] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "execute_tool_action",
        lambda *args, **kwargs: ToolExecutionResult(
            handled=True,
            ok=True,
            response_text="Да, такая услуга есть.",
            error_code=None,
            decision_meta={
                "tool_action": "catalog.service_query",
                "tool_decision": "presence_fallback",
                "info_sections": ["pricing"],
            },
            trace={
                "stage": "tool_registry",
                "decision": "presence_fallback",
                "tool_action": "catalog.service_query",
                "info_sections": ["pricing"],
            },
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "save_message",
        lambda *args, **kwargs: saved_messages.append(True),
    )

    async def _delegate(*args, **kwargs):
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert saved_messages == []


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_pricing_collect_owner_bypasses_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько стоит?",
            metadata=WebhookMetadata(
                remoteJid="77000000006@s.whatsapp.net",
                messageId="msg-pricing-collect-owner-cutover-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000651"),
        client_id=UUID("00000000-0000-0000-0000-000000000652"),
        user_id=UUID("00000000-0000-0000-0000-000000000653"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        info_router,
        "_build_info_intent_reply",
        lambda *args, **kwargs: (
            "Уточните, пожалуйста, какая именно услуга интересует?",
            {
                "action_class": "COLLECT",
                "intent_class": "service_clarify",
                "fact_source": "truth",
                "fact_refs": ["service_clarify"],
                "question_type": "pricing",
                "service_query": None,
            },
        ),
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe pricing collect sent"
    assert response.bot_response == "Уточните, пожалуйста, какая именно услуга интересует?"
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("intent") == "pricing"
    assert user_metadata.get("tool_action") == "info"
    assert user_metadata.get("expected_reply_type") == "service_choice"
    assert user_metadata.get("expected_reply_reason") == "service_clarify"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_PRICING_COLLECT_OWNER
    )
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("downstream_tool_decision")
        == "service_clarify"
    )
    assert user_metadata.get("turn_outcome", {}).get("expected_reply_type") == "service_choice"
    assert user_metadata.get("turn_outcome", {}).get("expected_reply_reason") == "service_clarify"
    assert conversation.context.get("expected_reply_type") == "service_choice"
    assert conversation.context.get("expected_reply_reason") == "service_clarify"
    session_memory = conversation.context.get("session_memory") or {}
    assert session_memory.get("last_question_type") == "service_choice"
    canonical_state = (conversation.context.get("context_manager") or {}).get("canonical_dialog_state") or {}
    assert canonical_state.get("pending_question_contract", {}).get("expected_reply_type") == "service_choice"
    assert canonical_state.get("interaction_state", {}).get("resume_slot") == "service"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_pricing_collect_owner_falls_back_on_unapproved_reply(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько стоит?",
            metadata=WebhookMetadata(
                remoteJid="77000000006@s.whatsapp.net",
                messageId="msg-pricing-collect-owner-cutover-2",
            ),
        ),
    )
    mock_db = Mock()
    saved_messages: list[Message] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        info_router,
        "_build_info_intent_reply",
        lambda *args, **kwargs: (
            "Уточните услугу.",
            {
                "action_class": "COLLECT",
                "intent_class": "duration_or_price_clarify",
                "fact_source": "truth",
                "fact_refs": ["duration_or_price_clarify"],
                "question_type": "pricing",
                "service_query": None,
            },
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "save_message",
        lambda *args, **kwargs: saved_messages.append(True),
    )

    async def _delegate(*args, **kwargs):
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert saved_messages == []


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_duration_collect_owner_bypasses_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько длится?",
            metadata=WebhookMetadata(
                remoteJid="77000000009@s.whatsapp.net",
                messageId="msg-duration-collect-owner-cutover-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000691"),
        client_id=UUID("00000000-0000-0000-0000-000000000692"),
        user_id=UUID("00000000-0000-0000-0000-000000000693"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        info_router,
        "get_pack_decision",
        lambda *args, **kwargs: pack_runtime_service.PackDecision(
            action="reply",
            intent="service_duration",
            response="По времени зависит от услуги. Какая именно?",
            meta={
                "question_type": "duration",
                "service_query": None,
                "fact_source": "truth",
                "action_class": "FACT",
                "intent_class": "service_duration",
                "fact_refs": ["duration", "service_duration"],
                "info_sections": ["duration"],
            },
        ),
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe duration collect sent"
    assert response.bot_response == "По времени зависит от услуги. Какая именно?"
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("intent") == "duration"
    assert user_metadata.get("tool_action") == "info"
    assert user_metadata.get("expected_reply_type") == "service_choice"
    assert user_metadata.get("expected_reply_reason") == "service_clarify"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_DURATION_COLLECT_OWNER
    )
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("downstream_tool_decision")
        == "service_clarify"
    )
    assert user_metadata.get("turn_outcome", {}).get("expected_reply_type") == "service_choice"
    assert user_metadata.get("turn_outcome", {}).get("expected_reply_reason") == "service_clarify"
    assert conversation.context.get("expected_reply_type") == "service_choice"
    assert conversation.context.get("expected_reply_reason") == "service_clarify"
    session_memory = conversation.context.get("session_memory") or {}
    assert session_memory.get("last_question_type") == "service_choice"
    canonical_state = (conversation.context.get("context_manager") or {}).get("canonical_dialog_state") or {}
    assert canonical_state.get("pending_question_contract", {}).get("expected_reply_type") == "service_choice"
    assert canonical_state.get("interaction_state", {}).get("resume_slot") == "service"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_duration_collect_owner_falls_back_on_unapproved_reply(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько длится?",
            metadata=WebhookMetadata(
                remoteJid="77000000009@s.whatsapp.net",
                messageId="msg-duration-collect-owner-cutover-2",
            ),
        ),
    )
    mock_db = Mock()
    saved_messages: list[Message] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        info_router,
        "get_pack_decision",
        lambda *args, **kwargs: pack_runtime_service.PackDecision(
            action="reply",
            intent="service_duration",
            response="По времени зависит от услуги. Какая именно?",
            meta={
                "question_type": "duration",
                "service_query": "маникюр",
                "fact_source": "truth",
                "action_class": "FACT",
                "intent_class": "service_duration",
                "fact_refs": ["duration", "service_duration"],
                "info_sections": ["duration"],
            },
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "save_message",
        lambda *args, **kwargs: saved_messages.append(True),
    )

    async def _delegate(*args, **kwargs):
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert saved_messages == []


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_master_query_owner_bypasses_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какие мастера делают маникюр?",
            metadata=WebhookMetadata(
                remoteJid="77000000007@s.whatsapp.net",
                messageId="msg-master-query-owner-cutover-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000651"),
        client_id=UUID("00000000-0000-0000-0000-000000000652"),
        user_id=UUID("00000000-0000-0000-0000-000000000653"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "resolve_master_intent",
        lambda **kwargs: pack_runtime_service.MasterIntentResolution(
            explicit=True,
            service_query="Маникюр",
            service_query_source="policy_override",
            needs_service_clarify=False,
            reason="forced_master_intent",
            matched_signals=[],
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "build_master_reply_from_pack",
        lambda **kwargs: pack_runtime_service.MasterReplyDecision(
            response="По услуге \"Маникюр\" работают Айгерим и Динара.",
            action="reply",
            intent="master",
            meta={
                "info_sections": ["master"],
                "master_query_contract": "masters_catalog.v1",
                "master_reply_mode": "service_match",
                "service_query": "Маникюр",
                "service_query_source": "policy_override",
                "master_profiles": ["Айгерим", "Динара"],
            },
        ),
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe master-query fact sent"
    assert response.bot_response == "По услуге \"Маникюр\" работают Айгерим и Динара."
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("intent") == "master_query"
    assert user_metadata.get("tool_action") == "catalog.service_query"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_MASTER_QUERY_FACT_OWNER
    )
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("downstream_tool_decision")
        == "service_match"
    )
    assert user_metadata.get("turn_outcome", {}).get("tool_decision") == "planner_owner_cutover"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_master_query_collect_owner_bypasses_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой мастер можете предложить?",
            metadata=WebhookMetadata(
                remoteJid="77000000008@s.whatsapp.net",
                messageId="msg-master-query-collect-owner-cutover-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000661"),
        client_id=UUID("00000000-0000-0000-0000-000000000662"),
        user_id=UUID("00000000-0000-0000-0000-000000000663"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "resolve_master_intent",
        lambda **kwargs: pack_runtime_service.MasterIntentResolution(
            explicit=True,
            service_query=None,
            service_query_source="policy_override",
            needs_service_clarify=True,
            reason="forced_master_intent",
            matched_signals=[],
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "build_master_reply_from_pack",
        lambda **kwargs: pack_runtime_service.MasterReplyDecision(
            response="Подскажите, по какой услуге нужно подобрать мастера?",
            action="collect",
            intent="master",
            meta={
                "info_sections": ["master"],
                "master_query_contract": "masters_catalog.v1",
                "master_reply_mode": "service_clarify",
                "clarify_reason": "missing_service_query",
                "service_query": None,
                "service_query_source": "policy_override",
            },
        ),
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe master-query collect sent"
    assert response.bot_response == "Подскажите, по какой услуге нужно подобрать мастера?"
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("intent") == "master_query"
    assert user_metadata.get("tool_action") == "collect"
    assert user_metadata.get("expected_reply_type") == "service_choice"
    assert user_metadata.get("expected_reply_reason") == "service_clarify"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_MASTER_QUERY_COLLECT_OWNER
    )
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("downstream_tool_decision")
        == "service_clarify"
    )
    assert user_metadata.get("turn_outcome", {}).get("expected_reply_type") == "service_choice"
    assert user_metadata.get("turn_outcome", {}).get("expected_reply_reason") == "service_clarify"
    assert conversation.context.get("expected_reply_type") == "service_choice"
    assert conversation.context.get("expected_reply_reason") == "service_clarify"
    session_memory = conversation.context.get("session_memory") or {}
    assert session_memory.get("last_question_type") == "service_choice"
    canonical_state = (conversation.context.get("context_manager") or {}).get("canonical_dialog_state") or {}
    assert canonical_state.get("pending_question_contract", {}).get("expected_reply_type") == "service_choice"
    assert canonical_state.get("interaction_state", {}).get("resume_slot") == "service"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_master_query_service_not_found_owner_bypasses_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какие мастера делают маникюр?",
            metadata=WebhookMetadata(
                remoteJid="77000000008@s.whatsapp.net",
                messageId="msg-master-query-service-not-found-owner-cutover-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000664"),
        client_id=UUID("00000000-0000-0000-0000-000000000665"),
        user_id=UUID("00000000-0000-0000-0000-000000000666"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "resolve_master_intent",
        lambda **kwargs: pack_runtime_service.MasterIntentResolution(
            explicit=True,
            service_query="Маникюр",
            service_query_source="policy_override",
            needs_service_clarify=False,
            reason="forced_master_intent",
            matched_signals=[],
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "build_master_reply_from_pack",
        lambda **kwargs: pack_runtime_service.MasterReplyDecision(
            response="По этой услуге мастеров не найдено. Подскажите другую услугу.",
            action="collect",
            intent="master",
            meta={
                "info_sections": ["master"],
                "master_query_contract": "masters_catalog.v1",
                "master_reply_mode": "service_not_found",
                "clarify_reason": "master_service_not_found",
                "service_query": "Маникюр",
                "service_query_source": "policy_override",
            },
        ),
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe master-query service-not-found collect sent"
    assert response.bot_response == "По этой услуге мастеров не найдено. Подскажите другую услугу."
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("intent") == "master_query"
    assert user_metadata.get("tool_action") == "collect"
    assert user_metadata.get("expected_reply_type") == "service_choice"
    assert user_metadata.get("expected_reply_reason") == "master_service_not_found"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_MASTER_QUERY_SERVICE_NOT_FOUND_OWNER
    )
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("downstream_tool_decision")
        == "service_not_found"
    )
    assert user_metadata.get("turn_outcome", {}).get("expected_reply_type") == "service_choice"
    assert (
        user_metadata.get("turn_outcome", {}).get("expected_reply_reason")
        == "master_service_not_found"
    )
    assert conversation.context.get("expected_reply_type") == "service_choice"
    assert conversation.context.get("expected_reply_reason") == "master_service_not_found"
    session_memory = conversation.context.get("session_memory") or {}
    assert session_memory.get("last_question_type") == "service_choice"
    canonical_state = (conversation.context.get("context_manager") or {}).get("canonical_dialog_state") or {}
    assert canonical_state.get("pending_question_contract", {}).get("expected_reply_type") == "service_choice"
    assert canonical_state.get("interaction_state", {}).get("resume_slot") == "service"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_master_query_service_not_found_owner_falls_back_on_unapproved_metadata(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какие мастера делают маникюр?",
            metadata=WebhookMetadata(
                remoteJid="77000000010@s.whatsapp.net",
                messageId="msg-master-query-service-not-found-owner-cutover-2",
            ),
        ),
    )
    mock_db = Mock()
    saved_messages: list[Message] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "resolve_master_intent",
        lambda **kwargs: pack_runtime_service.MasterIntentResolution(
            explicit=True,
            service_query="Маникюр",
            service_query_source="policy_override",
            needs_service_clarify=False,
            reason="forced_master_intent",
            matched_signals=[],
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "build_master_reply_from_pack",
        lambda **kwargs: pack_runtime_service.MasterReplyDecision(
            response="По этой услуге мастеров не найдено. Подскажите другую услугу.",
            action="collect",
            intent="master",
            meta={
                "info_sections": ["master"],
                "master_query_contract": "masters_catalog.v1",
                "master_reply_mode": "service_not_found",
                "clarify_reason": "master_service_not_found",
            },
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "save_message",
        lambda *args, **kwargs: saved_messages.append(True),
    )

    async def _delegate(*args, **kwargs):
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert saved_messages == []


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_master_query_owner_falls_back_when_reply_missing(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какие мастера делают маникюр?",
            metadata=WebhookMetadata(
                remoteJid="77000000009@s.whatsapp.net",
                messageId="msg-master-query-owner-cutover-3",
            ),
        ),
    )
    mock_db = Mock()
    saved_messages: list[Message] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "resolve_master_intent",
        lambda **kwargs: pack_runtime_service.MasterIntentResolution(
            explicit=True,
            service_query="Маникюр",
            service_query_source="policy_override",
            needs_service_clarify=False,
            reason="forced_master_intent",
            matched_signals=[],
        ),
    )
    monkeypatch.setattr(reasoning_core, "build_master_reply_from_pack", lambda **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "save_message",
        lambda *args, **kwargs: saved_messages.append(True),
    )

    async def _delegate(*args, **kwargs):
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert saved_messages == []


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_booking_verification_owner_bypasses_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Проверьте, пожалуйста, мою запись",
            metadata=WebhookMetadata(
                remoteJid="77000000010@s.whatsapp.net",
                messageId="msg-booking-verification-owner-cutover-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000671"),
        client_id=UUID("00000000-0000-0000-0000-000000000672"),
        user_id=UUID("00000000-0000-0000-0000-000000000673"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=None,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "execute_tool_action",
        lambda *args, **kwargs: ToolExecutionResult(
            handled=True,
            ok=True,
            response_text="Запись: Маникюр, Айгерим, 17.03 18:00.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.get_booking",
                "tool_decision": "ok",
                "appointment_id": "appt-123",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.get_booking",
            },
            expected_reply_type=None,
        ),
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking verification fact sent"
    assert response.bot_response == "Запись: Маникюр, Айгерим, 17.03 18:00."
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("intent") == "check_booking"
    assert user_metadata.get("tool_action") == "calendar.get_booking"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_VERIFICATION_OWNER
    )
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("downstream_tool_decision")
        == "ok"
    )
    assert user_metadata.get("turn_outcome", {}).get("tool_decision") == "planner_owner_cutover"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_booking_verification_owner_bypasses_not_found(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Проверьте, пожалуйста, мою запись",
            metadata=WebhookMetadata(
                remoteJid="77000000011@s.whatsapp.net",
                messageId="msg-booking-verification-owner-cutover-2",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000681"),
        client_id=UUID("00000000-0000-0000-0000-000000000682"),
        user_id=UUID("00000000-0000-0000-0000-000000000683"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=None,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "execute_tool_action",
        lambda *args, **kwargs: ToolExecutionResult(
            handled=True,
            ok=False,
            response_text="Проверил: пока не вижу подтверждённой записи.",
            error_code="appointment_not_found",
            decision_meta={
                "tool_action": "calendar.get_booking",
                "tool_decision": "not_found",
            },
            trace={
                "stage": "tool_registry",
                "decision": "not_found",
                "tool_action": "calendar.get_booking",
            },
            expected_reply_type="time",
        ),
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking verification fact sent"
    assert (
        response.bot_response
        == "Проверил: пока не вижу подтверждённой записи."
    )
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("intent") == "check_booking"
    assert user_metadata.get("tool_action") == "calendar.get_booking"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_VERIFICATION_OWNER
    )
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("downstream_tool_decision")
        == "not_found"
    )
    assert user_metadata.get("turn_outcome", {}).get("tool_decision") == "planner_owner_cutover"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_booking_verification_owner_falls_back_on_time_mismatch(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Проверьте, пожалуйста, мою запись",
            metadata=WebhookMetadata(
                remoteJid="77000000012@s.whatsapp.net",
                messageId="msg-booking-verification-owner-cutover-3",
            ),
        ),
    )
    mock_db = Mock()
    saved_messages: list[Message] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000691"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=None,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "execute_tool_action",
        lambda *args, **kwargs: ToolExecutionResult(
            handled=True,
            ok=False,
            response_text="Проверил: на это время подтверждённой записи не вижу.",
            error_code="booking_time_mismatch",
            decision_meta={
                "tool_action": "calendar.get_booking",
                "tool_decision": "time_mismatch",
                "appointment_time": "18:00",
            },
            trace={
                "stage": "tool_registry",
                "decision": "time_mismatch",
                "tool_action": "calendar.get_booking",
            },
            expected_reply_type="time",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "save_message",
        lambda *args, **kwargs: saved_messages.append(True),
    )

    async def _delegate(*args, **kwargs):
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Reasoning core terminal unresolved response skipped"
    assert saved_messages == []


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_booking_prompt_owner_bypasses_frozen_delegate_for_active_booking_slot_signal(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Маникюр",
            metadata=WebhookMetadata(
                remoteJid="77000000020@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000701"),
        client_id=UUID("00000000-0000-0000-0000-000000000702"),
        user_id=UUID("00000000-0000-0000-0000-000000000703"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "expected_reply_type": decision_router.EXPECTED_REPLY_SERVICE,
            "expected_reply_reason": "booking_prompt",
            "booking": {
                "active": True,
                "last_question": "service",
            },
            "context_manager": {
                "message_count": 7,
            },
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_SERVICE,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent=None,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_DATETIME
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "booking_prompt"
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("tool_action") == "collect"
    assert user_metadata.get("source") == "booking_prompt_owner"
    assert user_metadata.get("expected_reply_type") == "time"
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_OWNER
    )
    assert user_metadata.get("turn_outcome", {}).get("action") == "booking_prompt"
    assert user_metadata.get("turn_outcome", {}).get("expected_reply_type") == "time"
    assert user_metadata.get("turn_outcome", {}).get("expected_reply_reason") == "booking_prompt"
    assert conversation.context.get("expected_reply_type") == "time"
    assert conversation.context.get("expected_reply_reason") == "booking_prompt"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("service") == "Маникюр"
    assert booking.get("last_question") == "datetime"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE
        and entry.get("decision") == "prompt"
        and entry.get("source_route") == "booking_prompt_owner"
        and entry.get("missing_slot") == "datetime"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_booking_prompt_owner_shortcircuits_active_expected_reply(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Меня зовут Амина.",
            metadata=WebhookMetadata(
                remoteJid="77000000021@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-expected-reply",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000711"),
        client_id=UUID("00000000-0000-0000-0000-000000000712"),
        user_id=UUID("00000000-0000-0000-0000-000000000713"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "expected_reply_type": decision_router.EXPECTED_REPLY_SERVICE,
            "expected_reply_reason": "consult_clarify",
            "booking": {
                "active": True,
                "last_question": "service",
            },
            "context_manager": {
                "message_count": 7,
            },
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_SERVICE,
            current_goal="consult",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="consult_clarify",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent=None,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        decision_router,
        "_evaluate_booking_signal",
        lambda *args, **kwargs: (False, None),
    )
    monkeypatch.setattr(
        decision_router,
        "_is_booking_slot_signal",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("active expected reply should bypass policy-core booking candidate")
        ),
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_SERVICE
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "booking_prompt"
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("source") == "booking_prompt_owner"
    assert user_metadata.get("expected_reply_type") == "service_choice"
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    assert user_metadata.get("expected_reply_shortcircuit") is True
    assert user_metadata.get("turn_outcome", {}).get("action") == "booking_prompt"
    assert conversation.context.get("expected_reply_type") == "service_choice"
    assert conversation.context.get("expected_reply_reason") == "booking_prompt"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("last_question") == "service"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE
        and entry.get("decision") == "prompt"
        and entry.get("source_route") == "booking_prompt_owner"
        and entry.get("expected_reply_shortcircuit") is True
        and entry.get("missing_slot") == "service"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_intent_queue_booking_prompt_owner_bypasses_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Да, хочу записаться",
            metadata=WebhookMetadata(
                remoteJid="77000000021@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-2",
            ),
        ),
    )
    mock_db = Mock()
    context = {
        "expected_reply_type": decision_router.EXPECTED_REPLY_INTENT_CHOICE,
        "intent_queue": ["booking"],
        "context_manager": {
            "message_count": 4,
        },
    }
    context = decision_router._set_service_hint(
        context,
        "Маникюр",
        datetime.now(timezone.utc),
    )
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000711"),
        client_id=UUID("00000000-0000-0000-0000-000000000712"),
        user_id=UUID("00000000-0000-0000-0000-000000000713"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context=context,
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_INTENT_CHOICE,
            current_goal="info",
            booking_active=False,
            allow_bot_reply=True,
            resume_reason=None,
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent=None,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_DATETIME
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "booking_prompt"
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("source") == "intent_queue"
    assert user_metadata.get("intent_queue_choice") == "booking"
    assert user_metadata.get("intent_queue_remaining") == []
    assert user_metadata.get("expected_reply_choice") == "booking"
    assert user_metadata.get("expected_reply_next") == "booking"
    assert user_metadata.get("expected_reply_type") == "time"
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_OWNER
    )
    assert conversation.context.get("expected_reply_type") == "time"
    assert conversation.context.get("expected_reply_reason") == "booking_prompt"
    assert "intent_queue" not in conversation.context
    assert decision_router.SERVICE_HINT_KEY not in conversation.context
    assert decision_router.SERVICE_HINT_AT_KEY not in conversation.context
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("service") == "Маникюр"
    assert booking.get("last_question") == "datetime"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "intent_queue"
        and entry.get("decision") == "dequeue"
        and entry.get("chosen_intent") == "booking"
        for entry in trace
    )
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE
        and entry.get("decision") == "prompt"
        and entry.get("source_route") == "intent_queue"
        and entry.get("missing_slot") == "datetime"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_booking_prompt_owner_keeps_temporal_booking_followup_when_service_still_missing(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Можно записаться на выходные?",
            metadata=WebhookMetadata(
                remoteJid="77000000026@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-weekend-booking-followup-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000736"),
        client_id=UUID("00000000-0000-0000-0000-000000000737"),
        user_id=UUID("00000000-0000-0000-0000-000000000738"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "expected_reply_type": decision_router.EXPECTED_REPLY_SERVICE,
            "expected_reply_reason": "service_clarify",
            "booking": {
                "active": True,
                "last_question": "service",
            },
            "context_manager": {
                "message_count": 8,
            },
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_SERVICE,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent=None,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        decision_router,
        "_extract_service_hint",
        lambda *args, **kwargs: None,
    )
    def _route_llm_policy_core(*args, **kwargs):
        assert intent_service.get_policy_core_override() is None
        return {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "tool_args": {},
                "pack_refs": [],
                "slots": {"service": "", "datetime": "", "name": ""},
                "next_question": "service",
                "open_questions": ["service"],
                "needs_manager": False,
                "risk_signals": [],
                "language": None,
                "confidence": 0.0,
                "reason": "Пользователь хочет записаться, но не указал услугу.",
                "goal": "booking",
                "entity_refs": [],
                "subject_kind": "service",
                "capability": "bookability",
                "temporal_scope": "weekend",
                "resolution_mode": "clarify_missing_subject",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
            },
        }

    monkeypatch.setattr(reasoning_core, "route_llm_policy_core", _route_llm_policy_core)

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_SERVICE
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "booking_prompt"
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("source") == "llm_policy_core"
    assert user_metadata.get("llm_policy_core_collect_slot") == "service"
    assert user_metadata.get("tool_action") == "collect"
    assert user_metadata.get("expected_reply_type") == decision_router.EXPECTED_REPLY_SERVICE
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("datetime") == "в субботу"
    assert booking.get("last_question") == "service"
    assert conversation.context.get("expected_reply_type") == decision_router.EXPECTED_REPLY_SERVICE
    assert conversation.context.get("expected_reply_reason") == "booking_prompt"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE
        and entry.get("missing_slot") == "service"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_llm_booking_prompt_candidate_accepts_service_collect_with_stale_time_followup_metadata(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="На какое время лучше записаться?",
            metadata=WebhookMetadata(
                remoteJid="77000000027@s.whatsapp.net",
                messageId="msg-booking-prompt-candidate-stale-time-followup-1",
            ),
        ),
    )

    monkeypatch.setattr(
        decision_router,
        "_collect_plan_consult_refs",
        lambda *args, **kwargs: ([], None),
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "tool_args": {},
                "pack_refs": [],
                "slots": {
                    "service": "",
                    "datetime": "2023-10-03T16:00:00Z",
                    "name": "",
                },
                "next_question": "service",
                "open_questions": ["service"],
                "needs_manager": False,
                "risk_signals": [],
                "language": None,
                "confidence": 0.0,
                "reason": "Сначала нужно уточнить услугу, чтобы предложить подходящее время.",
                "goal": "booking",
                "entity_refs": [],
                "subject_kind": "service",
                "capability": "live_availability",
                "temporal_scope": "specific_time",
                "resolution_mode": "ask_about_requested_slot",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
            },
        },
    )

    candidate = reasoning_core._resolve_turn_planner_safe_llm_booking_prompt_candidate(
        payload=payload,
        message_text="На какое время лучше записаться?",
        reply_slot=decision_router.EXPECTED_REPLY_SERVICE,
        current_goal="booking",
        booking_state={"datetime": "2023-10-03T16:00:00Z"},
        context={},
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert candidate is not None
    assert candidate["collect_slot"] == "service"
    assert candidate["reason"] == "сначала нужно уточнить услугу, чтобы предложить подходящее время."
    assert candidate["slot_values"] == {"datetime": "2023-10-03T16:00:00Z"}
    assert candidate["merged_slot_values"] == {"datetime": "2023-10-03T16:00:00Z"}


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_llm_booking_prompt_candidate_recovers_initial_booking_timeout_with_parser_state(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Я хочу записаться на маникюр на завтра.",
            metadata=WebhookMetadata(
                remoteJid="77000000029@s.whatsapp.net",
                messageId="msg-booking-prompt-candidate-timeout-recovery-1",
            ),
        ),
    )

    monkeypatch.setattr(
        decision_router,
        "_collect_plan_consult_refs",
        lambda *args, **kwargs: ([], None),
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": False,
            "payload": None,
            "error": "timeout",
            "raw": "{}",
            "attempted": True,
            "elapsed_ms": 2500.0,
        },
    )

    candidate = reasoning_core._resolve_turn_planner_safe_llm_booking_prompt_candidate(
        payload=payload,
        message_text="Я хочу записаться на маникюр на завтра.",
        reply_slot=None,
        current_goal=None,
        booking_state=None,
        context={},
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
        allow_initial_slot_progression=True,
        allow_timeout_recovery=True,
    )

    assert candidate is not None
    assert candidate["collect_slot"] == "datetime"
    assert candidate["slot_values"] == {"service": "Маникюр"}
    assert candidate["seed_booking_state"]["service"] == "Маникюр"
    assert candidate["seed_booking_state"]["datetime"] == "завтра"
    assert candidate["policy_core_mode"] == "degraded_fallback"
    assert candidate["policy_core_degrade_reason"] == "policy_error:timeout"
    assert candidate["policy_core_guard_recovery"] == "initial_booking_parser"


def test_reasoning_core_turn_planner_safe_llm_booking_prompt_candidate_caps_initial_booking_policy_core_tokens(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Я хочу записаться на маникюр на завтра.",
            metadata=WebhookMetadata(
                remoteJid="77000000029@s.whatsapp.net",
                messageId="msg-booking-prompt-candidate-max-tokens-1",
            ),
        ),
    )
    captured_kwargs: dict[str, object] = {}

    monkeypatch.setattr(
        decision_router,
        "_collect_plan_consult_refs",
        lambda *args, **kwargs: ([], None),
    )
    monkeypatch.setattr(
        decision_router,
        "_extract_service_hint",
        lambda *args, **kwargs: "Маникюр",
    )
    monkeypatch.setattr(
        decision_router,
        "_get_recent_service_hint",
        lambda *args, **kwargs: "Педикюр",
    )

    def _route_llm_policy_core(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "tool_args": {},
                "pack_refs": [],
                "slots": {"service": "Маникюр", "datetime": "", "name": ""},
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "language": None,
                "confidence": 0.0,
                "reason": "Нужно уточнить время.",
                "goal": "booking",
                "entity_refs": [],
                "subject_kind": "service",
                "capability": "bookability",
                "temporal_scope": "specific_time",
                "resolution_mode": "clarify_missing_time",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
            },
        }

    monkeypatch.setattr(reasoning_core, "route_llm_policy_core", _route_llm_policy_core)

    candidate = reasoning_core._resolve_turn_planner_safe_llm_booking_prompt_candidate(
        payload=payload,
        message_text="Я хочу записаться на маникюр на завтра.",
        reply_slot=None,
        current_goal=None,
        booking_state=None,
        context={},
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
        allow_initial_slot_progression=True,
        allow_timeout_recovery=True,
    )

    assert candidate is not None
    assert captured_kwargs["slot_state"] == {"service": "Маникюр"}
    assert captured_kwargs["info_refs"] == []
    assert captured_kwargs["consult_refs"] == []
    assert captured_kwargs["max_tokens_override"] == (
        reasoning_core.REASONING_CORE_INITIAL_BOOKING_POLICY_CORE_MAX_TOKENS
    )


def test_reasoning_core_turn_planner_safe_llm_booking_prompt_candidate_keeps_service_only_initial_entry_booking_only(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Я хочу записаться на маникюр.",
            metadata=WebhookMetadata(
                remoteJid="77000000031@s.whatsapp.net",
                messageId="msg-booking-prompt-candidate-service-only-1",
            ),
        ),
    )
    captured_kwargs: dict[str, object] = {}

    monkeypatch.setattr(
        decision_router,
        "_collect_plan_consult_refs",
        lambda *args, **kwargs: (["consult_a", "consult_b"], None),
    )
    monkeypatch.setattr(
        decision_router,
        "_extract_service_hint",
        lambda *args, **kwargs: "Маникюр",
    )

    def _route_llm_policy_core(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "tool_args": {},
                "pack_refs": [],
                "slots": {"service": "Маникюр", "datetime": "", "name": ""},
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "language": None,
                "confidence": 0.0,
                "reason": "Нужно уточнить время.",
                "goal": "booking",
                "entity_refs": [],
                "subject_kind": "service",
                "capability": "bookability",
                "temporal_scope": "specific_time",
                "resolution_mode": "clarify_missing_time",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
            },
        }

    monkeypatch.setattr(reasoning_core, "route_llm_policy_core", _route_llm_policy_core)

    candidate = reasoning_core._resolve_turn_planner_safe_llm_booking_prompt_candidate(
        payload=payload,
        message_text="Я хочу записаться на маникюр.",
        reply_slot=None,
        current_goal=None,
        booking_state=None,
        context={},
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
        allow_initial_slot_progression=True,
        allow_timeout_recovery=True,
    )

    assert candidate is not None
    assert candidate["collect_slot"] == "datetime"
    assert captured_kwargs["slot_state"] == {"service": "Маникюр"}
    assert captured_kwargs["info_refs"] == []
    assert captured_kwargs["consult_refs"] == []
    assert captured_kwargs["max_tokens_override"] == (
        reasoning_core.REASONING_CORE_INITIAL_BOOKING_POLICY_CORE_MAX_TOKENS
    )


def test_reasoning_core_turn_planner_safe_llm_booking_prompt_candidate_keeps_general_policy_budget_outside_initial_entry(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="А на какое время есть запись?",
            metadata=WebhookMetadata(
                remoteJid="77000000030@s.whatsapp.net",
                messageId="msg-booking-prompt-candidate-max-tokens-2",
            ),
        ),
    )
    captured_kwargs: dict[str, object] = {}

    monkeypatch.setattr(
        decision_router,
        "_collect_plan_consult_refs",
        lambda *args, **kwargs: ([], None),
    )

    def _route_llm_policy_core(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "tool_args": {},
                "pack_refs": [],
                "slots": {"service": "Маникюр", "datetime": "", "name": ""},
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "language": None,
                "confidence": 0.0,
                "reason": "Нужно уточнить время.",
                "goal": "booking",
                "entity_refs": [],
                "subject_kind": "service",
                "capability": "bookability",
                "temporal_scope": "specific_time",
                "resolution_mode": "clarify_missing_time",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
            },
        }

    monkeypatch.setattr(reasoning_core, "route_llm_policy_core", _route_llm_policy_core)

    candidate = reasoning_core._resolve_turn_planner_safe_llm_booking_prompt_candidate(
        payload=payload,
        message_text="А на какое время есть запись?",
        reply_slot=decision_router.EXPECTED_REPLY_TIME,
        current_goal="booking",
        booking_state={"service": "Маникюр"},
        context={},
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
        allow_initial_slot_progression=True,
    )

    assert candidate is not None
    assert captured_kwargs["info_refs"] == sorted(decision_router.INFO_INTENTS)
    assert captured_kwargs["max_tokens_override"] is None


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_booking_prompt_owner_keeps_service_collect_for_reschedule_guidance_with_missing_service(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="На какое время лучше записаться?",
            metadata=WebhookMetadata(
                remoteJid="77000000028@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-stale-time-followup-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000739"),
        client_id=UUID("00000000-0000-0000-0000-000000000740"),
        user_id=UUID("00000000-0000-0000-0000-000000000741"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "expected_reply_type": decision_router.EXPECTED_REPLY_SERVICE,
            "expected_reply_reason": "booking_prompt",
            "booking": {
                "active": True,
                "datetime": "2023-10-03T16:00:00Z",
                "last_question": "service",
            },
            "context_manager": {
                "message_count": 9,
            },
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_SERVICE,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token="16:00",
            booking_datetime_value="2023-10-03T16:00:00Z",
            service_referent=None,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        decision_router,
        "_collect_plan_consult_refs",
        lambda *args, **kwargs: ([], None),
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "tool_args": {},
                "pack_refs": [],
                "slots": {
                    "service": "",
                    "datetime": "2023-10-03T16:00:00Z",
                    "name": "",
                },
                "next_question": "service",
                "open_questions": ["service"],
                "needs_manager": False,
                "risk_signals": [],
                "language": None,
                "confidence": 0.0,
                "reason": "Сначала нужно уточнить услугу, чтобы предложить подходящее время.",
                "goal": "booking",
                "entity_refs": [],
                "subject_kind": "service",
                "capability": "live_availability",
                "temporal_scope": "specific_time",
                "resolution_mode": "ask_about_requested_slot",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
            },
        },
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_SERVICE
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "booking_prompt"
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("source") == "llm_policy_core"
    assert user_metadata.get("action_source") == "llm_policy_core"
    assert user_metadata.get("llm_policy_core_collect_slot") == "service"
    assert user_metadata.get("expected_reply_type") == decision_router.EXPECTED_REPLY_SERVICE
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("datetime") == "2023-10-03T16:00:00Z"
    assert booking.get("last_question") == "service"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE
        and entry.get("decision") == "prompt"
        and entry.get("source_route") == "llm_policy_core"
        and entry.get("missing_slot") == "service"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_booking_prompt_owner_preserves_time_slot_constraint_after_pricing_interrupt(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Важно, чтобы это было в выходные.",
            metadata=WebhookMetadata(
                remoteJid="77000000027@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-time-slot-constraint-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000739"),
        client_id=UUID("00000000-0000-0000-0000-000000000740"),
        user_id=UUID("00000000-0000-0000-0000-000000000741"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "expected_reply_type": decision_router.EXPECTED_REPLY_TIME,
            "expected_reply_reason": "booking_interrupt",
            "booking": {
                "active": True,
                "service": "Маникюр",
                "last_question": "datetime",
            },
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_TIME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_interrupt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    def _unexpected_policy_core(*args, **kwargs):
        raise AssertionError("llm policy core must stay bypassed for time slot-constraint")

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("frozen delegate must stay dead")

    booking_after_update = decision_router._update_booking_from_messages(
        {"active": True, "service": "Маникюр", "last_question": "datetime"},
        [payload.body.message],
        client_slug=payload.client_slug,
    )
    booking_after_update, expected_prompt = decision_router._next_booking_prompt(
        booking_after_update,
        client_slug=payload.client_slug,
    )

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(
        reasoning_core,
        "_try_handle_turn_planner_safe_check_booking_prompt_owner_cutover",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_try_handle_turn_planner_safe_specialist_followup_owner_cutover",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(reasoning_core, "route_llm_policy_core", _unexpected_policy_core)
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking prompt owner sent"
    assert response.bot_response == expected_prompt
    assert response.conversation_id == conversation.id
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "booking_prompt"
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("source") == "question_contract"
    assert user_metadata.get("action_source") == "question_contract"
    assert user_metadata.get("tool_action") == "collect"
    assert user_metadata.get("pending_question_act") == "slot_constraint"
    assert user_metadata.get("pending_question_target") == "time"
    assert user_metadata.get("pending_question_interaction") == "slot_constraint"
    assert user_metadata.get("pending_question_owner") == "question_contract"
    assert user_metadata.get("expected_reply_type") == decision_router.EXPECTED_REPLY_TIME
    assert user_metadata.get("expected_reply_reason") == "booking_interrupt"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("service") == "Маникюр"
    assert booking.get("datetime") == "в субботу"
    assert booking.get("last_question") == "datetime"
    assert conversation.context.get("expected_reply_type") == decision_router.EXPECTED_REPLY_TIME
    assert conversation.context.get("expected_reply_reason") == "booking_interrupt"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "slot_constraint"
        and entry.get("source") == "question_contract"
        and entry.get("pending_question_act") == "slot_constraint"
        and entry.get("pending_question_target") == "time"
        and entry.get("expected_reply_type") == "time"
        for entry in trace
    )
    assert not any(
        isinstance(entry, dict)
        and entry.get("stage")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_STAGE
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_booking_prompt_owner_repairs_booking_interrupt_exact_time_progression(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Я хочу записаться на 10 утра в субботу.",
            metadata=WebhookMetadata(
                remoteJid="77000000028@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-interrupt-exact-time-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000742"),
        client_id=UUID("00000000-0000-0000-0000-000000000743"),
        user_id=UUID("00000000-0000-0000-0000-000000000744"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "expected_reply_type": decision_router.EXPECTED_REPLY_TIME,
            "expected_reply_reason": "booking_interrupt",
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "в субботу",
                "last_question": "datetime",
            },
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_TIME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_interrupt",
            booking_time_token=None,
            booking_datetime_value="в субботу",
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    def _unexpected_policy_core(*args, **kwargs):
        raise AssertionError("llm policy core must stay bypassed for booking interrupt exact-time progression")

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("frozen delegate must stay dead")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(
        reasoning_core,
        "_try_handle_turn_planner_safe_check_booking_prompt_owner_cutover",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_try_handle_turn_planner_safe_specialist_followup_owner_cutover",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(reasoning_core, "route_llm_policy_core", _unexpected_policy_core)
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_NAME
    assert response.conversation_id == conversation.id
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "booking_prompt"
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("source") == "booking_prompt_owner"
    assert user_metadata.get("action_source") == "booking_prompt_owner"
    assert user_metadata.get("expected_reply_type") == decision_router.EXPECTED_REPLY_NAME
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    assert user_metadata.get("expected_reply_time_progression_override") is True
    assert user_metadata.get("expected_reply_time_token") == "10:00"
    assert user_metadata.get("expected_reply_time_progressed_datetime") == "в субботу 10:00"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("service") == "Маникюр"
    assert booking.get("datetime") == "в субботу 10:00"
    assert booking.get("last_question") == "name"
    assert conversation.context.get("expected_reply_type") == decision_router.EXPECTED_REPLY_NAME
    assert conversation.context.get("expected_reply_reason") == "booking_prompt"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "expected_reply_progression_override"
        and entry.get("decision") == "exact_time_merge"
        and entry.get("source") == "booking_prompt_owner"
        and entry.get("expected_reply_type") == decision_router.EXPECTED_REPLY_TIME
        and entry.get("time_token") == "10:00"
        and entry.get("booking_datetime") == "в субботу 10:00"
        for entry in trace
    )
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "question_contract"
        and entry.get("decision") == "set"
        and entry.get("expected_reply_type") == decision_router.EXPECTED_REPLY_NAME
        for entry in trace
    )
    assert not any(
        isinstance(entry, dict)
        and entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_constraint"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_booking_prompt_owner_falls_back_without_active_conversation_snapshot(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Маникюр",
            metadata=WebhookMetadata(
                remoteJid="77000000022@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-3",
            ),
        ),
    )
    mock_db = Mock()

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: None,
    )

    async def _delegate(*args, **kwargs):
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_llm_booking_prompt_owner_bypasses_frozen_delegate_for_generic_collect(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу продолжить запись",
            metadata=WebhookMetadata(
                remoteJid="77000000023@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-4",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000721"),
        client_id=UUID("00000000-0000-0000-0000-000000000722"),
        user_id=UUID("00000000-0000-0000-0000-000000000723"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "expected_reply_type": decision_router.EXPECTED_REPLY_TIME,
            "expected_reply_reason": "booking_prompt",
            "booking": {
                "active": True,
                "service": "Маникюр",
                "last_question": "datetime",
            },
            "context_manager": {
                "message_count": 8,
            },
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_TIME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        decision_router,
        "_evaluate_booking_signal",
        lambda *args, **kwargs: (False, None),
    )
    monkeypatch.setattr(
        decision_router,
        "_is_booking_slot_signal",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "reason": "Пользователь хочет записаться на маникюр, но не указал дату и время.",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "slots": {"service": "маникюр", "datetime": "", "name": ""},
                "needs_manager": False,
                "capability": "bookability",
                "subject_kind": "service",
                "temporal_scope": "none",
                "resolution_mode": "clarify_missing_time",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "entity_refs": [
                    {
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                ],
                "pack_refs": [],
                "risk_signals": [],
                "tool_args": {},
                "confidence": 0.0,
                "resolver_id": None,
                "resolver_version": None,
            },
        },
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_DATETIME
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "booking_prompt"
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("tool_action") == "collect"
    assert user_metadata.get("source") == "llm_policy_core"
    assert user_metadata.get("llm_policy_core_collect_slot") == "datetime"
    assert user_metadata.get("expected_reply_type") == "time"
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_OWNER
    )
    assert user_metadata.get("turn_outcome", {}).get("action") == "booking_prompt"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE
        and entry.get("decision") == "prompt"
        and entry.get("source_route") == "llm_policy_core"
        and entry.get("requested_slot") == "datetime"
        and entry.get("missing_slot") == "datetime"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_llm_booking_prompt_owner_falls_back_for_richer_collect_envelope(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу продолжить запись",
            metadata=WebhookMetadata(
                remoteJid="77000000024@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-5",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000731"),
        client_id=UUID("00000000-0000-0000-0000-000000000732"),
        user_id=UUID("00000000-0000-0000-0000-000000000733"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "expected_reply_type": decision_router.EXPECTED_REPLY_TIME,
            "expected_reply_reason": "booking_prompt",
            "booking": {
                "active": True,
                "service": "Маникюр",
                "last_question": "datetime",
            },
            "context_manager": {
                "message_count": 8,
            },
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[object] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_TIME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        decision_router,
        "_evaluate_booking_signal",
        lambda *args, **kwargs: (False, None),
    )
    monkeypatch.setattr(
        decision_router,
        "_is_booking_slot_signal",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "reason": "llm_policy_core_booking_prompt",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "slots": {"service": "Маникюр"},
                "pending_question_target": "specialist",
                "needs_manager": False,
            },
        },
    )
    monkeypatch.setattr(
        reasoning_core,
        "_try_handle_turn_planner_safe_semantic_arbitration_owner_cutover",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(reasoning_core, "save_message", lambda *args, **kwargs: saved_messages.append(True))

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Reasoning core terminal unresolved response skipped"
    assert delegate_calls == []
    assert saved_messages == []


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_initial_llm_booking_prompt_owner_bypasses_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу записаться",
            metadata=WebhookMetadata(
                remoteJid="77000000025@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-6",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000741"),
        client_id=UUID("00000000-0000-0000-0000-000000000742"),
        user_id=UUID("00000000-0000-0000-0000-000000000743"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "reason": "Пользователь хочет записаться, но не указал услугу.",
                "next_question": "service",
                "open_questions": ["service"],
                "slots": {"service": "", "datetime": "", "name": ""},
                "needs_manager": False,
                "capability": "bookability",
                "subject_kind": "service",
                "temporal_scope": "none",
                "resolution_mode": "clarify_missing_subject",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "entity_refs": [],
                "pack_refs": [],
                "risk_signals": [],
                "tool_args": {},
                "confidence": 0.0,
                "resolver_id": "llm_policy_core",
                "resolver_version": "v1",
            },
        },
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_SERVICE
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "booking_prompt"
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("source") == "llm_policy_core"
    assert user_metadata.get("llm_policy_core_collect_slot") == "service"
    assert user_metadata.get("expected_reply_type") == "service_choice"
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("last_question") == "service"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE
        and entry.get("decision") == "prompt"
        and entry.get("source_route") == "llm_policy_core"
        and entry.get("requested_slot") == "service"
        and entry.get("missing_slot") == "service"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_initial_llm_booking_prompt_owner_falls_back_on_slot_progression(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Маникюр",
            metadata=WebhookMetadata(
                remoteJid="77000000026@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-7",
            ),
        ),
    )
    mock_db = Mock()
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "reason": "Пользователь хочет записаться на маникюр, но не указал дату и время.",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "slots": {"service": "маникюр", "datetime": "", "name": ""},
                "needs_manager": False,
                "capability": "bookability",
                "subject_kind": "service",
                "temporal_scope": "none",
                "resolution_mode": "clarify_missing_time",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "entity_refs": [
                    {
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                ],
                "pack_refs": [],
                "risk_signals": [],
                "tool_args": {},
                "confidence": 0.0,
            },
        },
    )

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Reasoning core terminal unresolved response skipped"
    assert delegate_calls == []


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_initial_llm_booking_prompt_owner_bypasses_frozen_delegate_for_service_to_datetime_progression(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу на маникюр",
            metadata=WebhookMetadata(
                remoteJid="77000000027@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-8",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000751"),
        client_id=UUID("00000000-0000-0000-0000-000000000752"),
        user_id=UUID("00000000-0000-0000-0000-000000000753"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "reason": "llm_policy_core_booking_prompt",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "slots": {"service": "Маникюр"},
                "needs_manager": False,
            },
        },
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_DATETIME
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "booking_prompt"
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("source") == "llm_policy_core"
    assert user_metadata.get("llm_policy_core_collect_slot") == "datetime"
    assert user_metadata.get("expected_reply_type") == "time"
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("service") == "Маникюр"
    assert booking.get("last_question") == "datetime"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE
        and entry.get("decision") == "prompt"
        and entry.get("source_route") == "llm_policy_core"
        and entry.get("requested_slot") == "datetime"
        and entry.get("missing_slot") == "datetime"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_initial_llm_booking_prompt_owner_bypasses_frozen_delegate_for_service_datetime_to_name_progression(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу на маникюр завтра в 15:00",
            metadata=WebhookMetadata(
                remoteJid="77000000029@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-10",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000761"),
        client_id=UUID("00000000-0000-0000-0000-000000000762"),
        user_id=UUID("00000000-0000-0000-0000-000000000763"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "reason": "Запрос на запись на маникюр с указанным временем.",
                "next_question": "name",
                "open_questions": ["name"],
                "slots": {
                    "service": "маникюр",
                    "datetime": "2023-10-06T15:00:00",
                },
                "needs_manager": False,
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "specific_time",
                "resolution_mode": "direct",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "entity_refs": [
                    {
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                ],
                "pack_refs": [],
                "risk_signals": [],
                "tool_args": {},
                "confidence": 0.0,
                "resolver_id": "llm_policy_core",
                "resolver_version": "v1",
            },
        },
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_NAME
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "booking_prompt"
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("source") == "llm_policy_core"
    assert user_metadata.get("llm_policy_core_collect_slot") == "name"
    assert user_metadata.get("expected_reply_type") == "name"
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("service") == "Маникюр"
    assert isinstance(booking.get("datetime"), str)
    assert booking.get("datetime").strip()
    assert booking.get("last_question") == "name"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE
        and entry.get("decision") == "prompt"
        and entry.get("source_route") == "llm_policy_core"
        and entry.get("requested_slot") == "name"
        and entry.get("missing_slot") == "name"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_initial_llm_booking_prompt_owner_falls_back_for_richer_datetime_progression(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу на маникюр",
            metadata=WebhookMetadata(
                remoteJid="77000000028@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-9",
            ),
        ),
    )
    mock_db = Mock()
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "reason": "llm_policy_core_booking_prompt",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "slots": {"service": "Маникюр", "name": "Айжан"},
                "needs_manager": False,
            },
        },
    )

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert delegate_calls == [True]


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_initial_llm_booking_prompt_owner_falls_back_for_richer_name_progression(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Хочу на маникюр завтра в 15:00",
            metadata=WebhookMetadata(
                remoteJid="77000000030@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-11",
            ),
        ),
    )
    mock_db = Mock()
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "reason": "llm_policy_core_booking_prompt",
                "next_question": "name",
                "open_questions": ["name"],
                "slots": {"service": "Маникюр", "datetime": "завтра в 15:00", "phone": "+77000000000"},
                "needs_manager": False,
            },
        },
    )

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert delegate_calls == [True]


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_booking_completion_owner_bypasses_frozen_delegate_for_complete_name_turn(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Лена",
            metadata=WebhookMetadata(
                remoteJid="77000000031@s.whatsapp.net",
                messageId="msg-booking-completion-owner-cutover-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000771"),
        client_id=UUID("00000000-0000-0000-0000-000000000772"),
        user_id=UUID("00000000-0000-0000-0000-000000000773"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "2026-02-12 13:00",
            },
            "expected_reply_type": decision_router.EXPECTED_REPLY_NAME,
            "expected_reply_reason": "booking_prompt",
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []
    captured_tool_call: dict[str, object] = {}

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_NAME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value="2026-02-12 13:00",
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "reason": "slot_complete_but_collect",
                "slots": {
                    "service": "Маникюр",
                    "datetime": "2026-02-12 13:00",
                    "name": "Лена",
                },
                "needs_manager": False,
            },
        },
    )
    monkeypatch.setattr(
        decision_router,
        "_evaluate_booking_signal",
        lambda *args, **kwargs: (False, None),
    )
    monkeypatch.setattr(
        decision_router,
        "_is_booking_slot_signal",
        lambda *args, **kwargs: False,
    )

    def _execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return ToolExecutionResult(
            handled=True,
            ok=True,
            response_text="Запись создана.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.book_slot",
                "tool_decision": "ok",
                "appointment_id": "apt-1",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.book_slot",
                "appointment_id": "apt-1",
            },
        )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "execute_tool_action", _execute_tool_action)
    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking completion owner sent"
    assert response.bot_response == "Запись создана."
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert captured_tool_call.get("tool_action") == "calendar.book_slot"
    tool_args = captured_tool_call.get("tool_args") or {}
    assert tool_args.get("service_query") == "Маникюр"
    assert tool_args.get("start_at") == "2026-02-12 13:00"
    assert tool_args.get("customer_name") == "Лена"
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("source") == "tool_registry"
    assert user_metadata.get("tool_action") == "calendar.book_slot"
    assert user_metadata.get("appointment_id") == "apt-1"
    booking = conversation.context.get("booking") or {}
    assert booking.get("appointment_id") == "apt-1"
    assert conversation.context.get("expected_reply_type") is None
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_COMPLETION_STAGE
        and entry.get("decision") == "reply"
        and entry.get("tool_action") == "calendar.book_slot"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_booking_completion_owner_bypasses_frozen_delegate_for_book_slot_hint_backfill(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Запиши меня завтра в 15:00 к Айгерим на маникюр",
            metadata=WebhookMetadata(
                remoteJid="77000000032@s.whatsapp.net",
                messageId="msg-booking-completion-owner-cutover-2",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000781"),
        client_id=UUID("00000000-0000-0000-0000-000000000782"),
        user_id=UUID("00000000-0000-0000-0000-000000000783"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={"booking": {"active": True}},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []
    captured_tool_call: dict[str, object] = {}

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=None,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason=None,
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent=None,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "fact",
                "tool_action": "calendar.book_slot",
                "goal": "booking",
                "reason": "book_slot",
                "tool_args": {"start_at": "2026-02-18 15:00"},
                "slots": {"service": "", "datetime": "2026-02-18 15:00", "name": "Айгерим"},
                "needs_manager": False,
            },
        },
    )
    monkeypatch.setattr(
        decision_router,
        "_evaluate_booking_signal",
        lambda *args, **kwargs: (False, None),
    )
    monkeypatch.setattr(
        decision_router,
        "_is_booking_slot_signal",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        reasoning_core,
        "extract_service_query_hint_llm",
        lambda *args, **kwargs: {
            "attempted": True,
            "ok": True,
            "service_query": "Маникюр",
            "confidence": 0.93,
            "language": "ru",
            "error": None,
        },
    )
    monkeypatch.setattr(
        reasoning_core,
        "extract_specialist_hint_llm",
        lambda *args, **kwargs: {
            "attempted": True,
            "ok": True,
            "specialist_name": "Айгерим",
            "confidence": 0.92,
            "language": "ru",
            "error": None,
        },
    )
    monkeypatch.setattr(
        reasoning_core,
        "extract_customer_name_hint_llm",
        lambda *args, **kwargs: {
            "attempted": True,
            "ok": True,
            "customer_name": "Лена",
            "confidence": 0.95,
            "language": "ru",
            "error": None,
        },
    )

    def _execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return ToolExecutionResult(
            handled=True,
            ok=True,
            response_text="Запись создана.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.book_slot",
                "tool_decision": "ok",
                "appointment_id": "apt-2",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.book_slot",
                "appointment_id": "apt-2",
            },
        )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "execute_tool_action", _execute_tool_action)
    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking completion owner sent"
    assert response.bot_response == "Запись создана."
    assert delegate_calls == []
    assert captured_tool_call.get("tool_action") == "calendar.book_slot"
    tool_args = captured_tool_call.get("tool_args") or {}
    assert tool_args.get("service_query") == "Маникюр"
    assert tool_args.get("start_at") == "2026-02-18 15:00"
    assert tool_args.get("specialist_name") == "Айгерим"
    assert tool_args.get("customer_name") == "Лена"
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("service_query_hint_ok") is True
    assert user_metadata.get("specialist_hint_ok") is True
    assert user_metadata.get("customer_name_hint_ok") is True
    assert conversation.context.get("booking", {}).get("appointment_id") == "apt-2"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_booking_completion_branch_missing_handoffs(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Мне нужно на 14:00.",
            metadata=WebhookMetadata(
                remoteJid="77000000033@s.whatsapp.net",
                messageId="msg-booking-completion-owner-cutover-branch-missing",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000791"),
        client_id=UUID("00000000-0000-0000-0000-000000000792"),
        user_id=UUID("00000000-0000-0000-0000-000000000793"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="pending",
        context={
            "booking": {
                "active": True,
                "service": "Педикюр",
                "datetime": "2026-02-12 14:00",
                "name": "Амина",
            },
            "expected_reply_type": decision_router.EXPECTED_REPLY_NAME,
            "expected_reply_reason": "booking_prompt",
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    user = User(
        id=conversation.user_id,
        client_id=conversation.client_id,
        remote_jid="77000000033@s.whatsapp.net",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    handover = SimpleNamespace(id=UUID("00000000-0000-0000-0000-000000000794"))
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="pending",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_NAME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value="2026-02-12 14:00",
            service_referent="Педикюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_user",
        lambda *args, **kwargs: user,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "fact",
                "tool_action": "calendar.book_slot",
                "goal": "booking",
                "reason": "book_slot",
                "tool_args": {"start_at": "2026-02-12 14:00"},
                "slots": {
                    "service": "Педикюр",
                    "datetime": "2026-02-12 14:00",
                    "name": "Амина",
                },
                "needs_manager": False,
            },
        },
    )
    monkeypatch.setattr(
        decision_router,
        "_evaluate_booking_signal",
        lambda *args, **kwargs: (False, None),
    )
    monkeypatch.setattr(
        decision_router,
        "_is_booking_slot_signal",
        lambda *args, **kwargs: False,
    )

    def _execute_tool_action(*_args, **_kwargs):
        return ToolExecutionResult(
            handled=True,
            ok=False,
            response_text="Не могу определить филиал для записи. Уточните, пожалуйста, филиал.",
            error_code="branch_missing",
            decision_meta={
                "tool_action": "calendar.book_slot",
                "tool_decision": "branch_missing",
            },
            trace={
                "stage": "tool_registry",
                "decision": "branch_missing",
                "tool_action": "calendar.book_slot",
            },
        )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "execute_tool_action", _execute_tool_action)
    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(
        reasoning_core,
        "materialize_handover",
        lambda **_kwargs: SimpleNamespace(
            ok=True,
            handover=handover,
            mode="reuse",
            telegram_sent=True,
            handover_reopened=False,
        ),
    )
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking completion handoff sent"
    assert response.bot_response == decision_router.MSG_ESCALATED
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "escalate"
    assert user_metadata.get("source") == "tool_registry"
    assert user_metadata.get("tool_decision") == "branch_missing"
    assert user_metadata.get("expected_reply_contract_reason") == "calendar_book_slot_branch_missing_handoff"
    assert user_metadata.get("expected_reply_contract_handoff") is True
    assert user_metadata.get("expected_reply_contract_clear") is True
    assert user_metadata.get("handoff_mode") == "reuse"
    assert user_metadata.get("telegram_sent") is True
    turn_outcome = user_metadata.get("turn_outcome") or {}
    assert turn_outcome.get("action") == "escalate"
    assert turn_outcome.get("tool_decision") == "planner_owner_cutover"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("downstream_tool_decision")
        == "branch_missing"
    )
    assert conversation.context.get("expected_reply_type") is None
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_check_booking_prompt_owner_bypasses_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Подтвердите, пожалуйста, запись.",
            metadata=WebhookMetadata(
                remoteJid="77000000031@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-12",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000771"),
        client_id=UUID("00000000-0000-0000-0000-000000000772"),
        user_id=UUID("00000000-0000-0000-0000-000000000773"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "booking": {
                "active": True,
                "service": "Стрижка",
                "datetime": "2026-03-18 15:00",
            },
            "expected_reply_type": decision_router.EXPECTED_REPLY_NAME,
            "expected_reply_reason": "calendar_get_booking_collect_reference",
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_NAME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="calendar_get_booking_collect_reference",
            booking_time_token="15:00",
            booking_datetime_value="2026-03-18 15:00",
            service_referent="Стрижка",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "reason": "collect_name",
                "next_question": "name",
                "open_questions": ["name"],
                "slots": {"service": "Стрижка", "datetime": "2026-03-18 15:00"},
                "needs_manager": False,
            },
        },
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe check booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_REFERENCE
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "check_booking_prompt"
    assert user_metadata.get("intent") == "check_booking"
    assert user_metadata.get("tool_action") == "collect"
    assert user_metadata.get("source") == "booking_verification"
    assert user_metadata.get("llm_policy_core_collect_slot") == "name"
    assert user_metadata.get("expected_reply_type") == "name"
    assert user_metadata.get("expected_reply_reason") == "calendar_get_booking_collect_reference"
    assert user_metadata.get("turn_outcome", {}).get("action") == "check_booking_prompt"
    assert user_metadata.get("turn_outcome", {}).get("intent") == "check_booking"
    assert conversation.context.get("expected_reply_type") == "name"
    assert conversation.context.get("expected_reply_reason") == "calendar_get_booking_collect_reference"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("service") == "Стрижка"
    assert booking.get("datetime")
    assert booking.get("last_question") == "name"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE
        and entry.get("decision") == "check_booking_prompt"
        and entry.get("source_route") == "booking_verification"
        and entry.get("missing_slot") == "name"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_check_booking_prompt_owner_marks_expected_reply_bypass(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Проверьте, пожалуйста, мою запись на пятницу на 20:00.",
            metadata=WebhookMetadata(
                remoteJid="77000000032@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-13",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000781"),
        client_id=UUID("00000000-0000-0000-0000-000000000782"),
        user_id=UUID("00000000-0000-0000-0000-000000000783"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "expected_reply_type": decision_router.EXPECTED_REPLY_SERVICE,
            "expected_reply_reason": "consult_booking_cta",
            "context_manager": {"current_goal": "consult"},
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_SERVICE,
            current_goal="consult",
            booking_active=False,
            allow_bot_reply=True,
            resume_reason="consult_booking_cta",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent=None,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "reason": "collect_name",
                "next_question": "name",
                "open_questions": ["name"],
                "slots": {"service": "Маникюр", "datetime": "в пятницу 20:00"},
                "needs_manager": False,
            },
        },
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe check booking prompt owner sent"
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("expected_reply_bypassed") == "booking_verification"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "question_contract"
        and entry.get("decision") == "bypass"
        and entry.get("expected_reply_bypassed") == "booking_verification"
        for entry in trace
    )


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_initial_check_booking_prompt_owner_bypasses_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Проверьте, пожалуйста, запись.",
            metadata=WebhookMetadata(
                remoteJid="77000000034@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-15",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000791"),
        client_id=UUID("00000000-0000-0000-0000-000000000792"),
        user_id=UUID("00000000-0000-0000-0000-000000000793"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "reason": "collect_name",
                "next_question": "name",
                "open_questions": ["name"],
                "slots": {"service": "Стрижка", "datetime": "2026-03-18 15:00"},
                "needs_manager": False,
            },
        },
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe check booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_REFERENCE
    assert delegate_calls == []
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "check_booking_prompt"
    assert user_metadata.get("intent") == "check_booking"
    assert user_metadata.get("source") == "booking_verification"
    assert user_metadata.get("llm_policy_core_collect_slot") == "name"
    assert user_metadata.get("expected_reply_type") == "name"
    assert user_metadata.get("expected_reply_reason") == "calendar_get_booking_collect_reference"


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_check_booking_prompt_owner_accepts_verification_recovery_envelope(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Можете подтвердить мою запись?",
            metadata=WebhookMetadata(
                remoteJid="77000000035@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-16",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000794"),
        client_id=UUID("00000000-0000-0000-0000-000000000795"),
        user_id=UUID("00000000-0000-0000-0000-000000000796"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "в субботу после обеда",
            },
            "expected_reply_type": decision_router.EXPECTED_REPLY_NAME,
            "expected_reply_reason": "booking_prompt",
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_NAME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token="после обеда",
            booking_datetime_value="в субботу после обеда",
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "fact",
                "tool_action": "calendar.get_booking",
                "tool_args": {"appointment_id": ""},
                "goal": "booking",
                "reason": "Запрос на подтверждение записи.",
                "next_question": "name",
                "open_questions": ["name"],
                "slots": {
                    "service": "Маникюр",
                    "datetime": "в субботу после обеда",
                    "name": "",
                },
                "entity_refs": [
                    {
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                ],
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "none",
                "resolution_mode": "direct",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "needs_manager": False,
                "pack_refs": [],
                "risk_signals": [],
            },
        },
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "execute_tool_action",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected execute_tool_action")),
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe check booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_REFERENCE
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "check_booking_prompt"
    assert user_metadata.get("intent") == "check_booking"
    assert user_metadata.get("source") == "booking_verification"
    assert user_metadata.get("action_source") == "booking_verification"
    assert user_metadata.get("expected_reply_bypassed") == "booking_verification"
    assert user_metadata.get("llm_policy_core_collect_slot") == "name"
    assert user_metadata.get("expected_reply_type") == "name"
    assert user_metadata.get("expected_reply_reason") == "calendar_get_booking_collect_reference"
    assert conversation.context.get("expected_reply_type") == "name"
    assert conversation.context.get("expected_reply_reason") == "calendar_get_booking_collect_reference"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("service") == "Маникюр"
    assert booking.get("datetime") == "в субботу после обеда"
    assert booking.get("last_question") == "name"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE
        and entry.get("decision") == "check_booking_prompt"
        and entry.get("source_route") == "booking_verification"
        and entry.get("missing_slot") == "name"
        for entry in trace
    )
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "question_contract"
        and entry.get("decision") == "bypass"
        and entry.get("expected_reply_bypassed") == "booking_verification"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_check_booking_prompt_owner_repairs_repeated_reference_continuity_from_snapshot(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Подтвердите, пожалуйста, запись на маникюр.",
            metadata=WebhookMetadata(
                remoteJid="77000000037@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-18",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-0000000008a1"),
        client_id=UUID("00000000-0000-0000-0000-0000000008a2"),
        user_id=UUID("00000000-0000-0000-0000-0000000008a3"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "booking": {
                "active": True,
            },
            "expected_reply_type": decision_router.EXPECTED_REPLY_SERVICE,
            "expected_reply_reason": "calendar_get_booking_collect_reference",
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_safe_llm_booking_prompt_candidate",
        lambda **kwargs: {
            "collect_slot": "service",
            "reason": "collect_service",
            "slot_values": {"service": "Маникюр"},
        },
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    response = await reasoning_core._try_handle_turn_planner_safe_check_booking_prompt_owner_cutover(
        payload=payload,
        db=mock_db,
        client_id=conversation.client_id,
        preflight_payload=None,
        conversation_id=conversation.id,
        conversation_snapshot=reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_SERVICE,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="calendar_get_booking_collect_reference",
            booking_time_token="11:00",
            booking_datetime_value="в субботу 11:00",
            service_referent="Маникюр",
        ),
        batch_messages=None,
        enqueue_only=False,
        skip_persist=False,
    )

    assert response is not None
    assert response.success is True
    assert response.message == "Turn planner safe check booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_REFERENCE
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "check_booking_prompt"
    assert user_metadata.get("intent") == "check_booking"
    assert user_metadata.get("source") == "booking_verification"
    assert user_metadata.get("action_source") == "booking_verification"
    assert user_metadata.get("expected_reply_bypassed") == "booking_verification"
    assert user_metadata.get("llm_policy_core_collect_slot") == "name"
    assert user_metadata.get("llm_policy_core_collect_slot_original") == "service"
    assert user_metadata.get("expected_reply_type") == "name"
    assert user_metadata.get("expected_reply_reason") == "calendar_get_booking_collect_reference"
    assert conversation.context.get("expected_reply_type") == "name"
    assert conversation.context.get("expected_reply_reason") == "calendar_get_booking_collect_reference"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("service") == "Маникюр"
    assert booking.get("datetime") == "в субботу 11:00"
    assert booking.get("last_question") == "name"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "question_contract"
        and entry.get("decision") == "normalize"
        and entry.get("reason") == "booking_verification_reference_continuity"
        and entry.get("collect_slot_original") == "service"
        and entry.get("normalized_missing_slot") == "name"
        and entry.get("expected_reply_type") == "name"
        for entry in trace
    )
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE
        and entry.get("decision") == "check_booking_prompt"
        and entry.get("source_route") == "booking_verification"
        and entry.get("missing_slot") == "name"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_check_booking_prompt_owner_recovers_ambiguous_time_verification_request(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Можете подтвердить мою запись?",
            metadata=WebhookMetadata(
                remoteJid="77000000036@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-17",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000797"),
        client_id=UUID("00000000-0000-0000-0000-000000000798"),
        user_id=UUID("00000000-0000-0000-0000-000000000799"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "в субботу",
            },
            "expected_reply_type": decision_router.EXPECTED_REPLY_TIME,
            "expected_reply_reason": "booking_prompt",
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_TIME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value="в субботу",
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "fact",
                "tool_action": "calendar.get_booking",
                "tool_args": {"appointment_id": ""},
                "goal": "booking",
                "reason": "Подтверждение записи на маникюр в субботу.",
                "next_question": "name",
                "open_questions": ["name"],
                "slots": {
                    "service": "Маникюр",
                    "datetime": "в субботу",
                    "name": "",
                },
                "entity_refs": [
                    {
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                ],
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "specific_time",
                "resolution_mode": "referent_followup",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "needs_manager": False,
                "pack_refs": [],
                "risk_signals": [],
            },
        },
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "execute_tool_action",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected execute_tool_action")),
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe semantic booking prompt sent"
    assert "точное время" in (response.bot_response or "")
    assert delegate_calls == []
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "booking_prompt"
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("source") == "llm_policy_core"
    assert user_metadata.get("action_source") == "semantic_arbitration"
    assert user_metadata.get("llm_policy_core_collect_slot") == "datetime"
    assert user_metadata.get("expected_reply_type") == "time"
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    assert conversation.context.get("expected_reply_type") == "time"
    assert conversation.context.get("expected_reply_reason") == "booking_prompt"
    assert conversation.context.get("booking", {}).get("last_question") == "datetime"
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_check_booking_prompt_owner_falls_back_for_richer_envelope(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Подтвердите, пожалуйста, запись.",
            metadata=WebhookMetadata(
                remoteJid="77000000033@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-14",
            ),
        ),
    )
    mock_db = Mock()
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "reason": "collect_name",
                "next_question": "name",
                "open_questions": ["name"],
                "slots": {"service": "Стрижка", "datetime": "2026-03-18 15:00"},
                "pending_question_target": "specialist",
                "needs_manager": False,
            },
        },
    )

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Reasoning core terminal unresolved response skipped"
    assert delegate_calls == []


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_specialist_followup_owner_bypasses_frozen_delegate_for_time_collect(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Есть ли возможность сделать это у Айгерим?",
            metadata=WebhookMetadata(
                remoteJid="77000000035@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-16",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000801"),
        client_id=UUID("00000000-0000-0000-0000-000000000802"),
        user_id=UUID("00000000-0000-0000-0000-000000000803"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
            },
            "expected_reply_type": decision_router.EXPECTED_REPLY_TIME,
            "expected_reply_reason": "booking_prompt",
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_TIME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "reason": "specialist_followup",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "slots": {"service": "Маникюр", "datetime": "", "name": ""},
                "entity_refs": [
                    {
                        "entity_id": "master:Айгерим",
                        "entity_type": "specialist",
                        "source_ref": "carryover",
                    }
                ],
                "subject_kind": "specialist",
                "capability": "bookability",
                "resolution_mode": "referent_followup",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "specialist",
                "needs_manager": False,
            },
        },
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe specialist followup owner sent"
    assert "Айгерим" in (response.bot_response or "")
    assert decision_router.MSG_BOOKING_ASK_DATETIME in (response.bot_response or "")
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "booking_prompt"
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("tool_action") == "collect"
    assert user_metadata.get("source") == "booking_specialist_followup"
    assert user_metadata.get("pending_question_target") == "specialist"
    assert user_metadata.get("pending_question_interaction") == "specialist_followup"
    assert user_metadata.get("pending_question_owner") == "booking_specialist_followup"
    assert user_metadata.get("active_question_relation") == "referent_followup"
    assert user_metadata.get("pending_question_act") == "ask_about_requested_slot"
    assert user_metadata.get("specialist_name") == "Айгерим"
    assert user_metadata.get("expected_reply_type") == "time"
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    assert user_metadata.get("turn_outcome", {}).get("action") == "booking_prompt"
    booking = conversation.context.get("booking") or {}
    assert booking.get("service") == "Маникюр"
    assert booking.get("specialist_name") == "Айгерим"
    assert booking.get("last_question") == "datetime"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "booking_specialist_followup"
        and entry.get("pending_question_target") == "specialist"
        and entry.get("expected_reply_type") == "time"
        and entry.get("specialist_name") == "Айгерим"
        for entry in trace
    )
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_SPECIALIST_FOLLOWUP_STAGE
        and entry.get("decision") == "prompt"
        and entry.get("source_route") == "booking_specialist_followup"
        and entry.get("missing_slot") == "datetime"
        for entry in trace
    )


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_specialist_followup_owner_bypasses_frozen_delegate_for_name_collect(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Я хочу записаться к Айгерим.",
            metadata=WebhookMetadata(
                remoteJid="77000000036@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-17",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000811"),
        client_id=UUID("00000000-0000-0000-0000-000000000812"),
        user_id=UUID("00000000-0000-0000-0000-000000000813"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "15:00",
            },
            "expected_reply_type": decision_router.EXPECTED_REPLY_NAME,
            "expected_reply_reason": "booking_prompt",
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_NAME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token="15:00",
            booking_datetime_value="15:00",
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "reason": "specialist_followup",
                "next_question": "name",
                "open_questions": ["name"],
                "slots": {"service": "Маникюр", "datetime": "15:00", "name": ""},
                "entity_refs": [
                    {
                        "entity_id": "master:Айгерим",
                        "entity_type": "specialist",
                        "source_ref": "carryover",
                    }
                ],
                "subject_kind": "specialist",
                "capability": "bookability",
                "resolution_mode": "referent_followup",
                "pending_question_target": "specialist",
                "needs_manager": False,
            },
        },
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe specialist followup owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_NAME
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "booking_prompt"
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("tool_action") == "collect"
    assert user_metadata.get("source") == "booking_specialist_followup"
    assert user_metadata.get("pending_question_target") == "specialist"
    assert user_metadata.get("pending_question_interaction") == "specialist_followup"
    assert user_metadata.get("pending_question_owner") == "booking_specialist_followup"
    assert user_metadata.get("active_question_relation") == "referent_followup"
    assert user_metadata.get("specialist_name") == "Айгерим"
    assert user_metadata.get("expected_reply_type") == "name"
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    booking = conversation.context.get("booking") or {}
    assert booking.get("service") == "Маникюр"
    assert booking.get("datetime") == "15:00"
    assert booking.get("specialist_name") == "Айгерим"
    assert booking.get("last_question") == "name"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "pending_question_interaction"
        and entry.get("decision") == "booking_specialist_followup"
        and entry.get("pending_question_target") == "specialist"
        and entry.get("expected_reply_type") == "name"
        and entry.get("specialist_name") == "Айгерим"
        for entry in trace
    )


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_specialist_followup_owner_falls_back_for_media_envelope(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Есть ли возможность сделать это у Айгерим?",
            mediaData={"mimeType": "image/jpeg"},
            metadata=WebhookMetadata(
                remoteJid="77000000037@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-cutover-18",
            ),
        ),
    )
    mock_db = Mock()
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000821"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_TIME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent="Маникюр",
        ),
    )

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert delegate_calls == [True]


@pytest.mark.asyncio
async def test_reasoning_core_primes_portfolio_policy_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Покажите примеры работ по маникюру",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-portfolio-policy-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == ai_service.normalize_for_matching(
            "Покажите примеры работ по маникюру"
        )
        assert policy_override["intent"] == "portfolio"
        assert policy_override["action"] == "fact"
        assert policy_override["tool_action"] == "catalog.portfolio"
        assert policy_override["tool_args"] == {"service_query": "Маникюр"}
        assert policy_override["reason"] == "portfolio_question"
        assert policy_override["goal"] == "info"
        assert policy_override["pack_refs"] == ["portfolio"]
        assert policy_override["capability"] == "portfolio"
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("Покажите примеры работ по маникюру")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["intent"] == "portfolio"
        assert policy_result["payload"]["action"] == "fact"
        assert policy_result["payload"]["tool_action"] == "catalog.portfolio"
        assert policy_result["payload"]["tool_args"] == {"service_query": "Маникюр"}
        assert policy_result["payload"]["reason"] == "portfolio_question"
        assert policy_result["payload"]["goal"] == "info"
        assert policy_result["payload"]["pack_refs"] == ["portfolio"]
        assert policy_result["payload"]["capability"] == "portfolio"
        assert policy_result["payload"]["needs_manager"] is False
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_primes_master_query_policy_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какие мастера делают маникюр?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-master-query-policy-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == ai_service.normalize_for_matching(
            "Какие мастера делают маникюр?"
        )
        assert policy_override["intent"] == "master_query"
        assert policy_override["action"] == "fact"
        assert policy_override["tool_action"] == "catalog.service_query"
        assert policy_override["tool_args"] == {"service_query": "Маникюр"}
        assert policy_override["reason"] == "master_question"
        assert policy_override["goal"] == "info"
        assert policy_override["pack_refs"] == ["master"]
        assert policy_override["capability"] is None
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("Какие мастера делают маникюр?")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["intent"] == "master_query"
        assert policy_result["payload"]["action"] == "fact"
        assert policy_result["payload"]["tool_action"] == "catalog.service_query"
        assert policy_result["payload"]["tool_args"] == {"service_query": "Маникюр"}
        assert policy_result["payload"]["reason"] == "master_question"
        assert policy_result["payload"]["goal"] == "info"
        assert policy_result["payload"]["pack_refs"] == ["master"]
        assert policy_result["payload"]["capability"] is None
        assert policy_result["payload"]["needs_manager"] is False
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_primes_master_query_collect_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой мастер можете предложить?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-master-query-collect-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == ai_service.normalize_for_matching(
            "Какой мастер можете предложить?"
        )
        assert policy_override["intent"] == "master_query"
        assert policy_override["action"] == "collect"
        assert policy_override["tool_action"] == "collect"
        assert policy_override["tool_args"] == {}
        assert policy_override["reason"] == "master_service_clarify"
        assert policy_override["goal"] == "info"
        assert policy_override["pack_refs"] == ["master"]
        assert policy_override["next_question"] == "service"
        assert policy_override["open_questions"] == ["service"]
        assert policy_override["subject_kind"] == "service"
        assert policy_override["resolution_mode"] == "clarify_missing_subject"
        assert policy_override["capability"] is None
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("Какой мастер можете предложить?")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["intent"] == "master_query"
        assert policy_result["payload"]["action"] == "collect"
        assert policy_result["payload"]["tool_action"] == "collect"
        assert policy_result["payload"]["tool_args"] == {}
        assert policy_result["payload"]["reason"] == "master_service_clarify"
        assert policy_result["payload"]["goal"] == "info"
        assert policy_result["payload"]["pack_refs"] == ["master"]
        assert policy_result["payload"]["next_question"] == "service"
        assert policy_result["payload"]["open_questions"] == ["service"]
        assert policy_result["payload"]["subject_kind"] == "service"
        assert policy_result["payload"]["resolution_mode"] == "clarify_missing_subject"
        assert policy_result["payload"]["needs_manager"] is False
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_primes_active_service_master_query_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Я хотел бы получить больше информации о мастерах.",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-master-query-policy-bridge-active-service-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000112"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_NAME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value="16:00",
            service_referent="Маникюр",
        ),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["intent"] == "master_query"
        assert policy_override["action"] == "fact"
        assert policy_override["tool_action"] == "catalog.service_query"
        assert policy_override["tool_args"] == {"service_query": "Маникюр"}
        assert policy_override["reason"] == "master_question"
        assert policy_override["goal"] == "info"
        assert policy_override["pack_refs"] == ["master"]
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core(
            "Я хотел бы получить больше информации о мастерах."
        )
        assert policy_result["ok"] is True
        assert policy_result["payload"]["intent"] == "master_query"
        assert policy_result["payload"]["action"] == "fact"
        assert policy_result["payload"]["tool_action"] == "catalog.service_query"
        assert policy_result["payload"]["tool_args"] == {"service_query": "Маникюр"}
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_primes_pricing_collect_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько стоит?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-pricing-collect-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == ai_service.normalize_for_matching("Сколько стоит?")
        assert policy_override["intent"] == "pricing"
        assert policy_override["action"] == "collect"
        assert policy_override["tool_action"] == "info"
        assert policy_override["tool_args"] == {}
        assert policy_override["reason"] == "need_service"
        assert policy_override["goal"] == "info"
        assert policy_override["pack_refs"] == ["pricing"]
        assert policy_override["next_question"] == "service"
        assert policy_override["open_questions"] == ["service"]
        assert policy_override["subject_kind"] == "service"
        assert policy_override["resolution_mode"] == "clarify_missing_subject"
        assert policy_override["capability"] == "pricing"
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("Сколько стоит?")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["intent"] == "pricing"
        assert policy_result["payload"]["action"] == "collect"
        assert policy_result["payload"]["tool_action"] == "info"
        assert policy_result["payload"]["reason"] == "need_service"
        assert policy_result["payload"]["goal"] == "info"
        assert policy_result["payload"]["pack_refs"] == ["pricing"]
        assert policy_result["payload"]["next_question"] == "service"
        assert policy_result["payload"]["open_questions"] == ["service"]
        assert policy_result["payload"]["subject_kind"] == "service"
        assert policy_result["payload"]["resolution_mode"] == "clarify_missing_subject"
        assert policy_result["payload"]["capability"] == "pricing"
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_skips_pricing_collect_override_when_service_referent_present(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько стоит?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-pricing-collect-bridge-2",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000146"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=None,
            current_goal="info",
            booking_active=False,
            allow_bot_reply=True,
            service_referent="Маникюр",
        ),
    )

    async def _delegate(*args, **kwargs):
        assert intent_service.get_policy_core_override() is None
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_primes_duration_collect_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько длится?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-duration-collect-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == ai_service.normalize_for_matching("Сколько длится?")
        assert policy_override["intent"] == "duration"
        assert policy_override["action"] == "collect"
        assert policy_override["tool_action"] == "info"
        assert policy_override["tool_args"] == {}
        assert policy_override["reason"] == "need_service"
        assert policy_override["goal"] == "info"
        assert policy_override["pack_refs"] == ["duration"]
        assert policy_override["next_question"] == "service"
        assert policy_override["open_questions"] == ["service"]
        assert policy_override["subject_kind"] == "service"
        assert policy_override["resolution_mode"] == "clarify_missing_subject"
        assert policy_override["capability"] == "duration"
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("Сколько длится?")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["intent"] == "duration"
        assert policy_result["payload"]["action"] == "collect"
        assert policy_result["payload"]["tool_action"] == "info"
        assert policy_result["payload"]["reason"] == "need_service"
        assert policy_result["payload"]["goal"] == "info"
        assert policy_result["payload"]["pack_refs"] == ["duration"]
        assert policy_result["payload"]["next_question"] == "service"
        assert policy_result["payload"]["open_questions"] == ["service"]
        assert policy_result["payload"]["subject_kind"] == "service"
        assert policy_result["payload"]["resolution_mode"] == "clarify_missing_subject"
        assert policy_result["payload"]["capability"] == "duration"
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_skips_duration_collect_override_when_service_referent_present(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Сколько длится?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-duration-collect-bridge-2",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000147"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=None,
            current_goal="info",
            booking_active=False,
            allow_bot_reply=True,
            service_referent="Маникюр",
        ),
    )

    async def _delegate(*args, **kwargs):
        assert intent_service.get_policy_core_override() is None
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_bookability_time_collect_owner_bypasses_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="В какое время можно записаться?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-bookability-time-collect-owner-cutover-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000148"),
        client_id=UUID("00000000-0000-0000-0000-000000000149"),
        user_id=UUID("00000000-0000-0000-0000-000000000150"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=None,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Turn planner safe bookability time collect sent"
    assert response.bot_response == decision_router.MSG_BOOKING_PENDING_QUESTION_TIME_GUIDANCE
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("tool_action") == "calendar.list_slots"
    assert user_metadata.get("source") == "booking_slot_guidance"
    assert user_metadata.get("expected_reply_type") == "time"
    assert user_metadata.get("expected_reply_reason") == "booking_slot_guidance"
    assert user_metadata.get("pending_question_act") == "ask_about_requested_slot"
    assert user_metadata.get("pending_question_target") == "time"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKABILITY_TIME_COLLECT_OWNER
    )
    assert user_metadata.get("turn_outcome", {}).get("expected_reply_type") == "time"
    assert user_metadata.get("turn_outcome", {}).get("expected_reply_reason") == "booking_slot_guidance"
    assert conversation.context.get("expected_reply_type") == "time"
    assert conversation.context.get("expected_reply_reason") == "booking_slot_guidance"
    session_memory = conversation.context.get("session_memory") or {}
    assert session_memory.get("last_question_type") == "time"
    canonical_state = (conversation.context.get("context_manager") or {}).get("canonical_dialog_state") or {}
    assert canonical_state.get("pending_question_contract", {}).get("expected_reply_type") == "time"
    assert canonical_state.get("interaction_state", {}).get("resume_slot") == "datetime"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("service") == "Маникюр"
    assert booking.get("last_question") == "datetime"
    assert not booking.get("datetime")
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKABILITY_TIME_COLLECT_STAGE
        and entry.get("validation_error") == "semantic_temporal_scope_missing"
        and entry.get("policy_core_guard_recovery") == "semantic_temporal_scope_missing_slot_guidance"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_bookability_time_collect_owner_returns_terminal_unresolved_without_owner_conversation(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="В какое время можно записаться?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-bookability-time-collect-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000148"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=None,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: None,
    )

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("frozen delegate must stay dead")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Reasoning core terminal unresolved response skipped"
    assert response.bot_response == decision_router.MSG_AI_ERROR
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_skips_bookability_time_collect_override_without_booking_active(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="В какое время можно записаться?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-bookability-time-collect-bridge-2",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000149"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=None,
            current_goal="info",
            booking_active=False,
            allow_bot_reply=True,
            service_referent="Маникюр",
        ),
    )

    async def _delegate(*args, **kwargs):
        assert intent_service.get_policy_core_override() is None
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_active_name_time_collect_owner_bypasses_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="А есть ли свободные слоты на 15:00?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-active-name-time-followup-owner-cutover-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000151"),
        client_id=UUID("00000000-0000-0000-0000-000000000152"),
        user_id=UUID("00000000-0000-0000-0000-000000000153"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="name",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_time_availability_followup",
            booking_time_token="14:00",
            booking_datetime_value="14:00",
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    expected_reply = decision_router._build_active_name_time_availability_followup_response(
        current_slot="14:00",
        alternate_slot="15:00",
    )

    assert response.success is True
    assert response.message == "Turn planner safe active-name time collect sent"
    assert response.bot_response == expected_reply
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("tool_action") == "collect"
    assert user_metadata.get("source") == "booking_time_availability_followup"
    assert user_metadata.get("pending_question_act") == "ask_about_requested_slot"
    assert user_metadata.get("pending_question_target") == "time"
    assert user_metadata.get("pending_question_interaction") == "ask_about_requested_slot"
    assert user_metadata.get("pending_question_owner") == "booking_time_availability_followup"
    assert user_metadata.get("active_question_relation") == "ask_about_requested_slot"
    assert user_metadata.get("current_datetime") == "14:00"
    assert user_metadata.get("alternate_datetime") == "15:00"
    assert user_metadata.get("expected_reply_type") == "name"
    assert user_metadata.get("expected_reply_reason") == "booking_time_availability_followup"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_ACTIVE_NAME_TIME_COLLECT_OWNER
    )
    assert user_metadata.get("turn_outcome", {}).get("expected_reply_type") == "name"
    assert (
        user_metadata.get("turn_outcome", {}).get("expected_reply_reason")
        == "booking_time_availability_followup"
    )
    assert conversation.context.get("expected_reply_type") == "name"
    assert conversation.context.get("expected_reply_reason") == "booking_time_availability_followup"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("service") == "Маникюр"
    assert booking.get("datetime") == "14:00"
    assert booking.get("last_question") == "name"
    session_memory = conversation.context.get("session_memory") or {}
    assert session_memory.get("last_question_type") == "name"
    canonical_state = (conversation.context.get("context_manager") or {}).get("canonical_dialog_state") or {}
    assert canonical_state.get("pending_question_contract", {}).get("expected_reply_type") == "name"
    assert canonical_state.get("interaction_state", {}).get("resume_slot") == "name"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_ACTIVE_NAME_TIME_COLLECT_STAGE
        and entry.get("pending_question_owner") == "booking_time_availability_followup"
        and entry.get("active_question_relation") == "ask_about_requested_slot"
        and entry.get("current_datetime") == "14:00"
        and entry.get("alternate_datetime") == "15:00"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "message_text",
        "message_id",
        "current_time_token",
        "booking_datetime_value",
        "alternate_datetime",
    ),
    [
        (
            "А есть ли у вас места в это время?",
            "msg-active-name-deictic-time-owner-cutover-1",
            "15:00",
            "15:00",
            "15:00",
        ),
        (
            "У вас есть свободные слоты на этот день?",
            "msg-active-name-deictic-day-owner-cutover-1",
            "03:00",
            "03:00",
            "03:00",
        ),
        (
            "У вас есть свободные слоты на завтра?",
            "msg-active-name-relative-date-owner-cutover-1",
            "15:00",
            "15:00",
            "завтра",
        ),
        (
            "У вас есть свободные слоты на завтра вечером?",
            "msg-active-name-relative-daypart-owner-cutover-1",
            "15:00",
            "15:00",
            "завтра вечером",
        ),
    ],
)
async def test_reasoning_core_turn_planner_safe_active_name_time_collect_owner_bypasses_frozen_delegate_for_remaining_followup_family(
    monkeypatch,
    message_text,
    message_id,
    current_time_token,
    booking_datetime_value,
    alternate_datetime,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message=message_text,
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId=message_id,
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000174"),
        client_id=UUID("00000000-0000-0000-0000-000000000175"),
        user_id=UUID("00000000-0000-0000-0000-000000000176"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="name",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=current_time_token,
            booking_datetime_value=booking_datetime_value,
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    current_datetime = booking_datetime_value
    expected_reply = decision_router._build_active_name_time_availability_followup_response(
        current_slot=current_datetime,
        alternate_slot=alternate_datetime,
    )

    assert response.success is True
    assert response.message == "Turn planner safe active-name time collect sent"
    assert response.bot_response == expected_reply
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("tool_action") == "collect"
    assert user_metadata.get("source") == "booking_time_availability_followup"
    assert user_metadata.get("pending_question_act") == "ask_about_requested_slot"
    assert user_metadata.get("pending_question_target") == "time"
    assert user_metadata.get("pending_question_interaction") == "ask_about_requested_slot"
    assert user_metadata.get("pending_question_owner") == "booking_time_availability_followup"
    assert user_metadata.get("active_question_relation") == "ask_about_requested_slot"
    assert user_metadata.get("current_datetime") == current_datetime
    assert user_metadata.get("alternate_datetime") == alternate_datetime
    assert user_metadata.get("expected_reply_type") == "name"
    assert user_metadata.get("expected_reply_reason") == "booking_time_availability_followup"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_ACTIVE_NAME_TIME_COLLECT_OWNER
    )
    assert user_metadata.get("turn_outcome", {}).get("expected_reply_type") == "name"
    assert (
        user_metadata.get("turn_outcome", {}).get("expected_reply_reason")
        == "booking_time_availability_followup"
    )
    assert conversation.context.get("expected_reply_type") == "name"
    assert conversation.context.get("expected_reply_reason") == "booking_time_availability_followup"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("service") == "Маникюр"
    assert booking.get("datetime") == current_datetime
    assert booking.get("last_question") == "name"
    session_memory = conversation.context.get("session_memory") or {}
    assert session_memory.get("last_question_type") == "name"
    canonical_state = (conversation.context.get("context_manager") or {}).get("canonical_dialog_state") or {}
    assert canonical_state.get("pending_question_contract", {}).get("expected_reply_type") == "name"
    assert canonical_state.get("interaction_state", {}).get("resume_slot") == "name"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_ACTIVE_NAME_TIME_COLLECT_STAGE
        and entry.get("pending_question_owner") == "booking_time_availability_followup"
        and entry.get("active_question_relation") == "ask_about_requested_slot"
        and entry.get("current_datetime") == current_datetime
        and entry.get("alternate_datetime") == alternate_datetime
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_active_name_time_collect_owner_returns_terminal_unresolved_without_owner_conversation(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="А есть ли свободные слоты на 15:00?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-active-name-time-followup-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000150"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="name",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_time_availability_followup",
            booking_time_token="14:00",
            booking_datetime_value="14:00",
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: None,
    )

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("frozen delegate must stay dead")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Reasoning core terminal unresolved response skipped"
    assert response.bot_response == decision_router.MSG_AI_ERROR
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_skips_active_name_time_availability_followup_override_without_resume_reason(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="А есть ли свободные слоты на 15:00?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-active-name-time-followup-bridge-2",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000151"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="name",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="other_followup",
            service_referent="Маникюр",
        ),
    )

    async def _delegate(*args, **kwargs):
        assert intent_service.get_policy_core_override() is None
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_primes_active_name_deictic_time_availability_followup_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="А есть ли у вас места в это время?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-active-name-deictic-time-followup-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000152"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="name",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token="15:00",
            service_referent="Маникюр",
        ),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == ai_service.normalize_for_matching(
            "А есть ли у вас места в это время?"
        )
        assert policy_override["intent"] == "booking"
        assert policy_override["action"] == "collect"
        assert policy_override["tool_action"] == "collect"
        assert policy_override["reason"] == "booking_time_availability_followup"
        assert policy_override["goal"] == "booking"
        assert policy_override["slots"] == {
            "service": "Маникюр",
            "datetime": "15:00",
            "name": "",
        }
        assert policy_override["next_question"] == "name"
        assert policy_override["open_questions"] == ["name"]
        assert policy_override["subject_kind"] == "booking"
        assert policy_override["capability"] == "live_availability"
        assert policy_override["temporal_scope"] == "specific_time"
        assert policy_override["resolution_mode"] == "referent_followup"
        assert policy_override["pending_question_act"] == "ask_about_requested_slot"
        assert policy_override["pending_question_target"] == "time"
        assert policy_override["active_question_relation"] == "ask_about_requested_slot"
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("А есть ли у вас места в это время?")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["slots"] == {
            "service": "Маникюр",
            "datetime": "15:00",
            "name": "",
        }
        assert policy_result["payload"]["next_question"] == "name"
        assert policy_result["payload"]["open_questions"] == ["name"]
        assert policy_result["payload"]["temporal_scope"] == "specific_time"
        assert policy_result["payload"]["resolution_mode"] == "referent_followup"
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_skips_active_name_deictic_time_availability_followup_without_booking_time_token(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="А есть ли у вас места в это время?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-active-name-deictic-time-followup-bridge-2",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000153"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="name",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            service_referent="Маникюр",
        ),
    )

    async def _delegate(*args, **kwargs):
        assert intent_service.get_policy_core_override() is None
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_booking_prompt_owner_uses_session_memory_expected_reply_before_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Маникюр",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-session-memory-expected-reply-booking-owner",
            ),
        ),
    )
    mock_db = Mock()
    now = datetime.now(timezone.utc)
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000560"),
        client_id=UUID("00000000-0000-0000-0000-000000000561"),
        user_id=UUID("00000000-0000-0000-0000-000000000562"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
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
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core._build_conversation_snapshot(
            conversation,
            message_text="Маникюр",
            client_slug="demo_salon",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {"ok": False, "payload": None},
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
        conversation_id=conversation.id,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_NAME
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("source") == "booking_prompt_owner"
    assert user_metadata.get("expected_reply_shortcircuit") is True
    assert user_metadata.get("expected_reply_type") == decision_router.EXPECTED_REPLY_NAME
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    assert conversation.context.get("booking", {}).get("service") == "Маникюр"
    assert conversation.context.get("booking", {}).get("last_question") == "name"
    assert conversation.context.get("expected_reply_type") == decision_router.EXPECTED_REPLY_NAME
    assert conversation.context.get("expected_reply_reason") == "booking_prompt"


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_booking_prompt_owner_keeps_time_followup_for_ambiguous_daypart_reply(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="В субботу после обеда.",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-ambiguous-time-followup",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000563"),
        client_id=UUID("00000000-0000-0000-0000-000000000564"),
        user_id=UUID("00000000-0000-0000-0000-000000000565"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "last_question": "datetime",
            },
            "expected_reply_type": decision_router.EXPECTED_REPLY_TIME,
            "expected_reply_reason": "booking_prompt",
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_TIME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "tool_args": {},
                "pack_refs": [],
                "slots": {"service": "Маникюр", "datetime": ""},
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "needs_manager": False,
                "risk_signals": [],
                "reason": "Пользователь указал время для записи, но не предоставил точное время.",
                "goal": "booking",
                "entity_refs": [
                    {
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                ],
                "subject_kind": "booking",
                "capability": "bookability",
                "temporal_scope": "specific_time",
                "resolution_mode": "clarify_missing_time",
                "pending_question_act": "fill_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": None,
            },
        },
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
        conversation_id=conversation.id,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_NAME
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("source") == "booking_prompt_owner"
    assert user_metadata.get("expected_reply_shortcircuit") is True
    assert user_metadata.get("expected_reply_type") == decision_router.EXPECTED_REPLY_NAME
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    assert conversation.context.get("booking", {}).get("service") == "Маникюр"
    assert conversation.context.get("booking", {}).get("datetime") == "в субботу днем"
    assert conversation.context.get("booking", {}).get("last_question") == "name"
    assert conversation.context.get("expected_reply_type") == decision_router.EXPECTED_REPLY_NAME
    assert conversation.context.get("expected_reply_reason") == "booking_prompt"


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_semantic_booking_prompt_merges_question_like_exact_time_progression(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Могу ли я изменить время на 11 утра?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-question-like-exact-time",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000571"),
        client_id=UUID("00000000-0000-0000-0000-000000000572"),
        user_id=UUID("00000000-0000-0000-0000-000000000573"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "в субботу",
                "last_question": "datetime",
            },
            "expected_reply_type": decision_router.EXPECTED_REPLY_TIME,
            "expected_reply_reason": "booking_prompt",
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_TIME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value="в субботу",
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "tool_args": {},
                "goal": "booking",
                "reason": "reschedule_time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "slots": {
                    "service": "Маникюр",
                    "datetime": "",
                    "name": "",
                },
                "entity_refs": [
                    {
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                ],
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "specific_time",
                "resolution_mode": "clarify_missing_time",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "needs_manager": False,
                "pack_refs": [],
                "risk_signals": [],
            },
        },
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
        conversation_id=conversation.id,
    )

    assert response.success is True
    assert response.message == "Turn planner safe semantic booking prompt sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_NAME
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("source") == "llm_policy_core"
    assert user_metadata.get("action_source") == "semantic_arbitration"
    assert user_metadata.get("llm_policy_core_collect_slot") == "name"
    assert user_metadata.get("expected_reply_type") == decision_router.EXPECTED_REPLY_NAME
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    assert user_metadata.get("expected_reply_time_progression_override") is True
    assert user_metadata.get("expected_reply_time_token") == "11:00"
    assert user_metadata.get("expected_reply_time_progressed_datetime") == "в субботу 11:00"
    assert conversation.context.get("booking", {}).get("service") == "Маникюр"
    assert conversation.context.get("booking", {}).get("datetime") == "в субботу 11:00"
    assert conversation.context.get("booking", {}).get("last_question") == "name"
    assert conversation.context.get("expected_reply_type") == decision_router.EXPECTED_REPLY_NAME
    assert conversation.context.get("expected_reply_reason") == "booking_prompt"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "expected_reply_progression_override"
        and entry.get("decision") == "exact_time_merge"
        and entry.get("source") == "llm_policy_core_semantic_arbitration"
        and entry.get("expected_reply_type") == decision_router.EXPECTED_REPLY_TIME
        and entry.get("time_token") == "11:00"
        and entry.get("booking_datetime") == "в субботу 11:00"
        for entry in trace
    )


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_semantic_booking_prompt_updates_grounded_datetime_while_name_pending(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Могу ли я изменить время на 11 утра?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-grounded-datetime-reschedule",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000574"),
        client_id=UUID("00000000-0000-0000-0000-000000000575"),
        user_id=UUID("00000000-0000-0000-0000-000000000576"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "в субботу 10:00",
                "last_question": "name",
            },
            "expected_reply_type": decision_router.EXPECTED_REPLY_NAME,
            "expected_reply_reason": "booking_prompt",
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_NAME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token="10:00",
            booking_datetime_value="в субботу 10:00",
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "tool_args": {},
                "goal": "booking",
                "reason": "reschedule_time",
                "next_question": "name",
                "open_questions": ["name"],
                "slots": {
                    "service": "Маникюр",
                    "datetime": "",
                    "name": "",
                },
                "entity_refs": [
                    {
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                ],
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "specific_time",
                "resolution_mode": "clarify_missing_name",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "needs_manager": False,
                "pack_refs": [],
                "risk_signals": [],
            },
        },
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
        conversation_id=conversation.id,
    )

    assert response.success is True
    assert response.message == "Turn planner safe semantic booking prompt sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_NAME
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("source") == "llm_policy_core"
    assert user_metadata.get("action_source") == "semantic_arbitration"
    assert user_metadata.get("llm_policy_core_collect_slot") == "name"
    assert user_metadata.get("expected_reply_type") == decision_router.EXPECTED_REPLY_NAME
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    assert user_metadata.get("expected_reply_time_progression_override") is True
    assert user_metadata.get("expected_reply_time_token") == "11:00"
    assert user_metadata.get("expected_reply_time_progressed_datetime") == "в субботу 11:00"
    assert conversation.context.get("booking", {}).get("service") == "Маникюр"
    assert conversation.context.get("booking", {}).get("datetime") == "в субботу 11:00"
    assert conversation.context.get("booking", {}).get("last_question") == "name"
    assert conversation.context.get("expected_reply_type") == decision_router.EXPECTED_REPLY_NAME
    assert conversation.context.get("expected_reply_reason") == "booking_prompt"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "expected_reply_progression_override"
        and entry.get("decision") == "exact_time_merge"
        and entry.get("source") == "llm_policy_core_semantic_arbitration"
        and entry.get("expected_reply_type") == decision_router.EXPECTED_REPLY_TIME
        and entry.get("time_token") == "11:00"
        and entry.get("booking_datetime") == "в субботу 11:00"
        for entry in trace
    )


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_booking_prompt_owner_restores_snapshot_service_for_post_verification_reschedule(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Можно на 18:30?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-post-verification-reschedule",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000612"),
        client_id=UUID("00000000-0000-0000-0000-000000000613"),
        user_id=UUID("00000000-0000-0000-0000-000000000614"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "booking": {
                "active": True,
                "datetime": "15:00",
                "last_question": "name",
            },
            "expected_reply_type": decision_router.EXPECTED_REPLY_NAME,
            "expected_reply_reason": "calendar_get_booking_collect_reference",
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_NAME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="calendar_get_booking_collect_reference",
            booking_time_token="15:00",
            booking_datetime_value="15:00",
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "tool_args": {},
                "goal": "booking",
                "reason": "пользователь предлагает конкретное время для записи, но не указал услугу.",
                "next_question": "service",
                "open_questions": ["service"],
                "slots": {
                    "service": "",
                    "datetime": "18:30",
                    "name": "",
                },
                "entity_refs": [],
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "specific_time",
                "resolution_mode": "clarify_missing_service",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "needs_manager": False,
                "pack_refs": [],
                "risk_signals": [],
            },
        },
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
        conversation_id=conversation.id,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_NAME
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("source") == "booking_prompt_owner"
    assert user_metadata.get("action_source") == "booking_prompt_owner"
    assert user_metadata.get("expected_reply_type") == decision_router.EXPECTED_REPLY_NAME
    assert user_metadata.get("expected_reply_reason") == "booking_prompt"
    assert user_metadata.get("expected_reply_time_progression_override") is True
    assert user_metadata.get("expected_reply_time_token") == "18:30"
    assert user_metadata.get("expected_reply_time_progressed_datetime") == "18:30"
    assert conversation.context.get("booking", {}).get("service") == "Маникюр"
    assert conversation.context.get("booking", {}).get("datetime") == "18:30"
    assert conversation.context.get("booking", {}).get("last_question") == "name"
    assert conversation.context.get("expected_reply_type") == decision_router.EXPECTED_REPLY_NAME
    assert conversation.context.get("expected_reply_reason") == "booking_prompt"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "expected_reply_progression_override"
        and entry.get("decision") == "exact_time_merge"
        and entry.get("source") == "booking_prompt_owner"
        and entry.get("expected_reply_type") == decision_router.EXPECTED_REPLY_TIME
        and entry.get("time_token") == "18:30"
        and entry.get("booking_datetime") == "18:30"
        for entry in trace
    )
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE
        and entry.get("decision") == "prompt"
        and entry.get("source_route") == "booking_prompt_owner"
        and entry.get("missing_slot") == "name"
        for entry in trace
    )


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_booking_prompt_owner_reactivates_pending_post_cancel_rebooking_state(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Когда я могу записаться снова?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-post-cancel-rebooking",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-0000000006b2"),
        client_id=UUID("00000000-0000-0000-0000-0000000006b3"),
        user_id=UUID("00000000-0000-0000-0000-0000000006b4"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="pending",
        context={
            "current_goal": "booking",
            "booking": {
                "active": True,
            },
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []
    manager_resolve_calls: list[dict[str, object]] = []
    handover = SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-0000000006b5"),
        status="pending",
    )

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="pending",
            bot_status="active",
            branch_id=None,
            reply_slot=None,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason=None,
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent=None,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "tool_args": {},
                "goal": "booking",
                "reason": "необходимо уточнить, на какую услугу планируется запись.",
                "next_question": "service",
                "open_questions": ["service"],
                "slots": {
                    "service": "",
                    "datetime": "",
                    "name": "",
                },
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
        },
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_safe_llm_booking_prompt_candidate",
        lambda **kwargs: {
            "collect_slot": "service",
            "reason": "post_cancel_rebooking_collect",
            "slot_values": {},
        },
    )
    monkeypatch.setattr(reasoning_core, "get_active_handover", lambda *args, **kwargs: handover)

    def _manager_resolve(db, conversation_arg, handover_arg, manager_id, manager_name, *, preserve_context=False):
        manager_resolve_calls.append(
            {
                "conversation_id": conversation_arg.id,
                "handover_id": handover_arg.id,
                "preserve_context": preserve_context,
            }
        )
        conversation_arg.state = "bot_active"
        handover_arg.status = "resolved"
        return SimpleNamespace(ok=True)

    monkeypatch.setattr(reasoning_core, "manager_resolve", _manager_resolve)

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
        conversation_id=conversation.id,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_SERVICE
    assert delegate_calls == []
    assert manager_resolve_calls == [
        {
            "conversation_id": conversation.id,
            "handover_id": handover.id,
            "preserve_context": True,
        }
    ]
    assert handover.status == "resolved"
    assert conversation.state == "bot_active"
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "booking_prompt"
    assert user_metadata.get("expected_reply_type") == decision_router.EXPECTED_REPLY_SERVICE
    assert user_metadata.get("pending_collect_resume_boundary") is True
    assert user_metadata.get("pending_collect_resume_mode") == "handover_resolve"
    assert conversation.context.get("expected_reply_type") == decision_router.EXPECTED_REPLY_SERVICE
    assert conversation.context.get("expected_reply_reason") == "booking_prompt"
    assert conversation.context.get("booking", {}).get("last_question") == "service"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "collect_owner_reactivation"
        and entry.get("decision") == "reactivate_collect_owner"
        and entry.get("reason") == "booking_collect_reentry"
        and entry.get("mode") == "handover_resolve"
        and entry.get("state_after") == "bot_active"
        for entry in trace
    )


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_infers_post_cancel_rebooking_boundary_before_semantic_handoff(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Когда я могу записаться снова?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-post-cancel-boundary",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-0000000006b6"),
        client_id=UUID("00000000-0000-0000-0000-0000000006b7"),
        user_id=UUID("00000000-0000-0000-0000-0000000006b8"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="pending",
        context={
            "booking": {
                "active": True,
            },
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    semantic_calls: list[bool] = []
    handover = SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-0000000006b9"),
        status="pending",
    )

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core._build_conversation_snapshot(
            conversation,
            message_text=payload.body.message,
            client_slug=payload.client_slug,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "tool_args": {},
                "goal": "booking",
                "reason": "необходимо уточнить, на какую услугу планируется запись.",
                "next_question": "service",
                "open_questions": ["service"],
                "slots": {
                    "service": "",
                    "datetime": "",
                    "name": "",
                },
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
        },
    )
    monkeypatch.setattr(reasoning_core, "get_active_handover", lambda *args, **kwargs: handover)
    monkeypatch.setattr(
        reasoning_core,
        "manager_resolve",
        lambda *args, **kwargs: (
            setattr(conversation, "state", "bot_active"),
            setattr(handover, "status", "resolved"),
            SimpleNamespace(ok=True),
        )[-1],
    )
    monkeypatch.setattr(
        reasoning_core,
        "_try_handle_turn_planner_safe_semantic_arbitration_owner_cutover",
        lambda *args, **kwargs: semantic_calls.append(True) or None,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
        conversation_id=conversation.id,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking prompt owner sent"
    assert response.bot_response == decision_router.MSG_BOOKING_ASK_SERVICE
    assert semantic_calls == []
    assert handover.status == "resolved"
    assert conversation.state == "bot_active"
    assert conversation.context.get("expected_reply_type") == decision_router.EXPECTED_REPLY_SERVICE
    assert conversation.context.get("expected_reply_reason") == "booking_prompt"
    assert conversation.context.get("booking", {}).get("last_question") == "service"
    assert saved_messages[0].message_metadata.get("decision_meta", {}).get(
        "pending_collect_resume_boundary"
    ) is True


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_semantic_booking_prompt_completes_explicit_name_progression(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Меня зовут Амина.",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-booking-prompt-owner-explicit-name-progress",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000574"),
        client_id=UUID("00000000-0000-0000-0000-000000000575"),
        user_id=UUID("00000000-0000-0000-0000-000000000576"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "в субботу 11:00",
                "last_question": "name",
            },
            "expected_reply_type": decision_router.EXPECTED_REPLY_NAME,
            "expected_reply_reason": "booking_prompt",
        },
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []
    captured_tool_call: dict[str, object] = {}

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot=decision_router.EXPECTED_REPLY_NAME,
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token="11:00",
            booking_datetime_value="в субботу 11:00",
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(
        reasoning_core,
        "route_llm_policy_core",
        lambda *args, **kwargs: {
            "ok": True,
            "payload": {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "tool_args": {},
                "goal": "booking",
                "reason": "booking_collect_name",
                "next_question": "name",
                "open_questions": ["name"],
                "slots": {
                    "service": "Маникюр",
                    "datetime": "в субботу 11:00",
                    "name": "",
                },
                "entity_refs": [
                    {
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "source_ref": "carryover",
                    }
                ],
                "capability": "bookability",
                "subject_kind": "booking",
                "temporal_scope": "specific_time",
                "resolution_mode": "collect_missing_name",
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "needs_manager": False,
                "pack_refs": [],
                "risk_signals": [],
            },
        },
    )

    def _execute_tool_action(*_args, **kwargs):
        captured_tool_call.update(kwargs)
        return ToolExecutionResult(
            handled=True,
            ok=True,
            response_text="Запись создана.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.book_slot",
                "tool_decision": "ok",
                "appointment_id": "apt-turn13",
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.book_slot",
                "appointment_id": "apt-turn13",
            },
        )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "execute_tool_action", _execute_tool_action)
    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
        conversation_id=conversation.id,
    )

    assert response.success is True
    assert response.message == "Turn planner safe booking completion owner sent"
    assert response.bot_response == "Запись создана."
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    assert captured_tool_call.get("tool_action") == "calendar.book_slot"
    tool_args = captured_tool_call.get("tool_args") or {}
    assert tool_args.get("service_query") == "Маникюр"
    assert tool_args.get("start_at") == "в субботу 11:00"
    assert tool_args.get("customer_name") == "Амина"
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("source") == "tool_registry"
    assert user_metadata.get("action_source") == "semantic_arbitration"
    assert user_metadata.get("expected_reply_name_progression_override") is True
    assert user_metadata.get("expected_reply_name_value") == "Амина"
    assert user_metadata.get("appointment_id") == "apt-turn13"
    runtime_meta = user_metadata.get("consultant_core_runtime") or {}
    assert (
        runtime_meta.get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_COMPLETION_OWNER
    )
    booking = conversation.context.get("booking") or {}
    assert booking.get("appointment_id") == "apt-turn13"
    assert booking.get("name") == "Амина"
    assert conversation.context.get("expected_reply_type") is None
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "expected_reply_progression_override"
        and entry.get("decision") == "name_merge"
        and entry.get("source") == "llm_policy_core_semantic_arbitration"
        and entry.get("expected_reply_type") == decision_router.EXPECTED_REPLY_NAME
        and entry.get("customer_name") == "Амина"
        for entry in trace
    )
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_BOOKING_COMPLETION_STAGE
        and entry.get("decision") == "reply"
        and entry.get("tool_action") == "calendar.book_slot"
        and entry.get("source_route") == "llm_policy_core_semantic_arbitration"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_primes_active_name_relative_date_availability_followup_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="У вас есть свободные слоты на завтра?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-active-name-relative-date-followup-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000156"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="name",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token="15:00",
            service_referent="Маникюр",
        ),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == ai_service.normalize_for_matching(
            "У вас есть свободные слоты на завтра?"
        )
        assert policy_override["intent"] == "booking"
        assert policy_override["action"] == "collect"
        assert policy_override["tool_action"] == "collect"
        assert policy_override["reason"] == "booking_time_availability_followup"
        assert policy_override["goal"] == "booking"
        assert policy_override["slots"] == {
            "service": "Маникюр",
            "datetime": "завтра",
            "name": "",
        }
        assert policy_override["next_question"] == "name"
        assert policy_override["open_questions"] == ["name"]
        assert policy_override["subject_kind"] == "booking"
        assert policy_override["capability"] == "bookability"
        assert policy_override["temporal_scope"] == "specific_time"
        assert policy_override["resolution_mode"] == "referent_followup"
        assert policy_override["pending_question_act"] == "ask_about_requested_slot"
        assert policy_override["pending_question_target"] == "time"
        assert policy_override["active_question_relation"] == "ask_about_requested_slot"
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("У вас есть свободные слоты на завтра?")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["slots"] == {
            "service": "Маникюр",
            "datetime": "завтра",
            "name": "",
        }
        assert policy_result["payload"]["capability"] == "bookability"
        assert policy_result["payload"]["temporal_scope"] == "specific_time"
        assert policy_result["payload"]["resolution_mode"] == "referent_followup"
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_skips_active_name_relative_date_availability_followup_without_booking_time_token(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="У вас есть свободные слоты на завтра?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-active-name-relative-date-followup-bridge-2",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000157"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="name",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            service_referent="Маникюр",
        ),
    )

    async def _delegate(*args, **kwargs):
        assert intent_service.get_policy_core_override() is None
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_primes_active_name_relative_daypart_availability_followup_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="У вас есть свободные слоты на завтра вечером?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-active-name-relative-daypart-followup-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000158"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="name",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token="15:00",
            service_referent="Маникюр",
        ),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == ai_service.normalize_for_matching(
            "У вас есть свободные слоты на завтра вечером?"
        )
        assert policy_override["intent"] == "booking"
        assert policy_override["action"] == "collect"
        assert policy_override["tool_action"] == "collect"
        assert policy_override["reason"] == "booking_time_availability_followup"
        assert policy_override["goal"] == "booking"
        assert policy_override["slots"] == {
            "service": "Маникюр",
            "datetime": "завтра вечером",
            "name": "",
        }
        assert policy_override["next_question"] == "name"
        assert policy_override["open_questions"] == ["name"]
        assert policy_override["subject_kind"] == "booking"
        assert policy_override["capability"] == "bookability"
        assert policy_override["temporal_scope"] == "specific_time"
        assert policy_override["resolution_mode"] == "referent_followup"
        assert policy_override["pending_question_act"] == "ask_about_requested_slot"
        assert policy_override["pending_question_target"] == "time"
        assert policy_override["active_question_relation"] == "ask_about_requested_slot"
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core(
            "У вас есть свободные слоты на завтра вечером?"
        )
        assert policy_result["ok"] is True
        assert policy_result["payload"]["slots"] == {
            "service": "Маникюр",
            "datetime": "завтра вечером",
            "name": "",
        }
        assert policy_result["payload"]["capability"] == "bookability"
        assert policy_result["payload"]["temporal_scope"] == "specific_time"
        assert policy_result["payload"]["resolution_mode"] == "referent_followup"
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_skips_active_name_relative_daypart_availability_followup_without_booking_time_token(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="У вас есть свободные слоты на завтра вечером?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-active-name-relative-daypart-followup-bridge-2",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000159"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="name",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            service_referent="Маникюр",
        ),
    )

    async def _delegate(*args, **kwargs):
        assert intent_service.get_policy_core_override() is None
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_specialist_datetime_collect_owner_bypasses_frozen_delegate_for_date_range_followup(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой мастер свободен на этой неделе?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-specialist-date-range-followup-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000160"),
        client_id=UUID("00000000-0000-0000-0000-000000000260"),
        user_id=UUID("00000000-0000-0000-0000-000000000360"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="time",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    expected_reply, specialist_meta = decision_router._build_specialist_availability_followup_response(
        service_query="Маникюр",
        client_slug="demo_salon",
        message_text="Какой мастер свободен на этой неделе?",
        requested_slot="time",
    )

    assert response.success is True
    assert response.message == "Turn planner safe specialist datetime collect sent"
    assert response.bot_response == expected_reply
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("tool_action") == "collect"
    assert user_metadata.get("source") == "booking_specialist_availability_followup"
    assert user_metadata.get("pending_question_act") == "ask_about_requested_slot"
    assert user_metadata.get("pending_question_target") == "specialist"
    assert user_metadata.get("pending_question_interaction") == "specialist_availability_followup"
    assert user_metadata.get("pending_question_owner") == "booking_specialist_availability_followup"
    assert user_metadata.get("active_question_relation") == "specialist_availability_followup"
    assert user_metadata.get("temporal_scope") == "date_range"
    assert user_metadata.get("expected_reply_type") == "time"
    assert user_metadata.get("expected_reply_reason") == "booking_specialist_availability_followup"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_SPECIALIST_DATETIME_COLLECT_OWNER
    )
    assert user_metadata.get("turn_outcome", {}).get("expected_reply_type") == "time"
    assert (
        user_metadata.get("turn_outcome", {}).get("expected_reply_reason")
        == "booking_specialist_availability_followup"
    )
    if isinstance(specialist_meta, dict):
        for key in (
            "info_sections",
            "fact_intents",
            "master_query_contract",
            "master_reply_mode",
            "master_profiles",
            "master_profiles_count",
            "service_query",
        ):
            value = specialist_meta.get(key)
            if value not in (None, [], {}):
                assert user_metadata.get(key) == value
    assert conversation.context.get("expected_reply_type") == "time"
    assert conversation.context.get("expected_reply_reason") == "booking_specialist_availability_followup"
    session_memory = conversation.context.get("session_memory") or {}
    assert session_memory.get("last_question_type") == "time"
    canonical_state = (conversation.context.get("context_manager") or {}).get("canonical_dialog_state") or {}
    assert canonical_state.get("pending_question_contract", {}).get("expected_reply_type") == "time"
    assert canonical_state.get("interaction_state", {}).get("resume_slot") == "datetime"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_SPECIALIST_DATETIME_COLLECT_STAGE
        and entry.get("pending_question_owner") == "booking_specialist_availability_followup"
        and entry.get("pending_question_target") == "specialist"
        and entry.get("active_question_relation") == "specialist_availability_followup"
        and entry.get("temporal_scope") == "date_range"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_specialist_datetime_collect_owner_returns_terminal_unresolved_without_owner_conversation(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой мастер свободен на этой неделе?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-specialist-date-range-followup-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000160"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="time",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: None,
    )

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("frozen delegate must stay dead")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Reasoning core terminal unresolved response skipped"
    assert response.bot_response == decision_router.MSG_AI_ERROR
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_specialist_date_range_availability_followup_falls_back_to_master_service_clarify_without_service_referent(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой мастер свободен на этой неделе?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-specialist-date-range-followup-bridge-2",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000161"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="time",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            service_referent=None,
        ),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["intent"] == "master_query"
        assert policy_override["action"] == "collect"
        assert policy_override["reason"] == "master_service_clarify"
        assert policy_override["next_question"] == "service"
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_specialist_name_collect_owner_bypasses_frozen_delegate_for_grounded_specialist_followup(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="А какие мастера доступны?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-grounded-specialist-transition-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000162"),
        client_id=UUID("00000000-0000-0000-0000-000000000262"),
        user_id=UUID("00000000-0000-0000-0000-000000000362"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="time",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value="завтра",
            service_referent="Маникюр",
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    expected_reply, specialist_meta = decision_router._build_specialist_availability_followup_response(
        service_query="Маникюр",
        client_slug="demo_salon",
        message_text="А какие мастера доступны?",
        requested_slot="name",
    )

    assert response.success is True
    assert response.message == "Turn planner safe specialist name collect sent"
    assert response.bot_response == expected_reply
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("tool_action") == "collect"
    assert user_metadata.get("source") == "booking_specialist_availability_followup"
    assert user_metadata.get("pending_question_act") == "ask_about_requested_slot"
    assert user_metadata.get("pending_question_target") == "specialist"
    assert user_metadata.get("pending_question_interaction") == "specialist_availability_followup"
    assert user_metadata.get("pending_question_owner") == "booking_specialist_availability_followup"
    assert user_metadata.get("active_question_relation") == "specialist_availability_followup"
    assert user_metadata.get("temporal_scope") == "specific_time"
    assert user_metadata.get("expected_reply_type") == "name"
    assert user_metadata.get("expected_reply_reason") == "booking_specialist_availability_followup"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_SPECIALIST_NAME_COLLECT_OWNER
    )
    assert user_metadata.get("turn_outcome", {}).get("expected_reply_type") == "name"
    assert (
        user_metadata.get("turn_outcome", {}).get("expected_reply_reason")
        == "booking_specialist_availability_followup"
    )
    if isinstance(specialist_meta, dict):
        for key in (
            "info_sections",
            "fact_intents",
            "master_query_contract",
            "master_reply_mode",
            "master_profiles",
            "master_profiles_count",
            "service_query",
        ):
            value = specialist_meta.get(key)
            if value not in (None, [], {}):
                assert user_metadata.get(key) == value
    assert conversation.context.get("expected_reply_type") == "name"
    assert conversation.context.get("expected_reply_reason") == "booking_specialist_availability_followup"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("service") == "Маникюр"
    assert booking.get("datetime") == "завтра"
    assert booking.get("last_question") == "name"
    session_memory = conversation.context.get("session_memory") or {}
    assert session_memory.get("last_question_type") == "name"
    canonical_state = (conversation.context.get("context_manager") or {}).get("canonical_dialog_state") or {}
    assert canonical_state.get("pending_question_contract", {}).get("expected_reply_type") == "name"
    assert canonical_state.get("interaction_state", {}).get("resume_slot") == "name"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_SPECIALIST_NAME_COLLECT_STAGE
        and entry.get("pending_question_owner") == "booking_specialist_availability_followup"
        and entry.get("pending_question_target") == "specialist"
        and entry.get("active_question_relation") == "specialist_availability_followup"
        and entry.get("temporal_scope") == "specific_time"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_grounded_specialist_availability_transition_falls_back_to_master_service_clarify_without_active_booking_datetime(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="А какие мастера доступны?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-grounded-specialist-transition-bridge-2",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000163"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="time",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent="Маникюр",
        ),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["intent"] == "master_query"
        assert policy_override["action"] == "collect"
        assert policy_override["reason"] == "master_service_clarify"
        assert policy_override["next_question"] == "service"
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message_text", "message_id", "reason", "temporal_scope"),
    [
        (
            "Какой мастер будет делать маникюр в субботу?",
            "msg-service-choice-specialist-day-owner-1",
            "day_followup",
            "specific_time",
        ),
        (
            "Какой мастер будет делать маникюр по будням?",
            "msg-service-choice-specialist-weekday-owner-1",
            "weekday_followup",
            "weekday",
        ),
        (
            "Какой мастер будет делать маникюр на выходных?",
            "msg-service-choice-specialist-weekend-owner-1",
            "weekend_followup",
            "weekend",
        ),
    ],
)
async def test_reasoning_core_turn_planner_safe_service_choice_specialist_time_collect_owner_bypasses_frozen_delegate(
    monkeypatch,
    message_text,
    message_id,
    reason,
    temporal_scope,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message=message_text,
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId=message_id,
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000168"),
        client_id=UUID("00000000-0000-0000-0000-000000000268"),
        user_id=UUID("00000000-0000-0000-0000-000000000368"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="service",
            current_goal="booking",
            booking_active=False,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent=None,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    expected_reply, specialist_meta = decision_router._build_specialist_availability_followup_response(
        service_query="Маникюр",
        client_slug="demo_salon",
        message_text=message_text,
        requested_slot="time",
    )

    assert response.success is True
    assert response.message == "Turn planner safe service-choice specialist time collect sent"
    assert response.bot_response == expected_reply
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "booking_prompt"
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("tool_action") == "collect"
    assert user_metadata.get("source") == "booking_specialist_availability_followup"
    assert user_metadata.get("pending_question_act") == "ask_about_requested_slot"
    assert user_metadata.get("pending_question_target") == "specialist"
    assert user_metadata.get("pending_question_interaction") == "specialist_availability_followup"
    assert user_metadata.get("pending_question_owner") == "booking_specialist_availability_followup"
    assert user_metadata.get("active_question_relation") == "specialist_availability_followup"
    assert user_metadata.get("temporal_scope") == temporal_scope
    assert user_metadata.get("expected_reply_type") == "time"
    assert user_metadata.get("expected_reply_reason") == "booking_specialist_availability_followup"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_TIME_COLLECT_OWNER
    )
    assert user_metadata.get("turn_outcome", {}).get("action") == "booking_prompt"
    assert user_metadata.get("turn_outcome", {}).get("expected_reply_type") == "time"
    assert (
        user_metadata.get("turn_outcome", {}).get("expected_reply_reason")
        == "booking_specialist_availability_followup"
    )
    if isinstance(specialist_meta, dict):
        for key in (
            "info_sections",
            "fact_intents",
            "master_query_contract",
            "master_reply_mode",
            "master_profiles",
            "master_profiles_count",
            "service_query",
        ):
            value = specialist_meta.get(key)
            if value not in (None, [], {}):
                assert user_metadata.get(key) == value
    assert conversation.context.get("expected_reply_type") == "time"
    assert conversation.context.get("expected_reply_reason") == "booking_specialist_availability_followup"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("service") == "Маникюр"
    assert "datetime" not in booking
    assert booking.get("last_question") == "datetime"
    session_memory = conversation.context.get("session_memory") or {}
    assert session_memory.get("last_question_type") == "time"
    canonical_state = (conversation.context.get("context_manager") or {}).get("canonical_dialog_state") or {}
    assert canonical_state.get("pending_question_contract", {}).get("expected_reply_type") == "time"
    assert canonical_state.get("interaction_state", {}).get("resume_slot") == "datetime"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_TIME_COLLECT_STAGE
        and entry.get("pending_question_owner") == "booking_specialist_availability_followup"
        and entry.get("pending_question_target") == "specialist"
        and entry.get("active_question_relation") == "specialist_availability_followup"
        and entry.get("temporal_scope") == temporal_scope
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_service_choice_specialist_time_collect_owner_returns_terminal_unresolved_without_owner_conversation(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой мастер будет делать маникюр на выходных?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-service-choice-specialist-weekend-owner-fallback-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000164"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="service",
            current_goal="booking",
            booking_active=False,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent=None,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: None,
    )

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("frozen delegate must stay dead")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Reasoning core terminal unresolved response skipped"
    assert response.bot_response == decision_router.MSG_AI_ERROR
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_specialist_name_collect_owner_bypasses_frozen_delegate_for_specialist_exact_time_followup(

    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой мастер будет делать маникюр завтра в 18:00?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-service-choice-specialist-exact-time-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000171"),
        client_id=UUID("00000000-0000-0000-0000-000000000271"),
        user_id=UUID("00000000-0000-0000-0000-000000000371"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="service",
            current_goal="booking",
            booking_active=False,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent=None,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    expected_reply, specialist_meta = decision_router._build_specialist_availability_followup_response(
        service_query="Маникюр",
        client_slug="demo_salon",
        message_text="Какой мастер будет делать маникюр завтра в 18:00?",
        requested_slot="name",
    )

    assert response.success is True
    assert response.message == "Turn planner safe specialist name collect sent"
    assert response.bot_response == expected_reply
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("tool_action") == "collect"
    assert user_metadata.get("source") == "booking_specialist_availability_followup"
    assert user_metadata.get("pending_question_target") == "specialist"
    assert user_metadata.get("pending_question_interaction") == "specialist_availability_followup"
    assert user_metadata.get("pending_question_owner") == "booking_specialist_availability_followup"
    assert user_metadata.get("active_question_relation") == "specialist_availability_followup"
    assert user_metadata.get("temporal_scope") == "specific_time"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_SPECIALIST_NAME_COLLECT_OWNER
    )
    if isinstance(specialist_meta, dict):
        for key in ("service_query", "master_reply_mode", "info_sections"):
            value = specialist_meta.get(key)
            if value not in (None, [], {}):
                assert user_metadata.get(key) == value
    assert conversation.context.get("expected_reply_type") == "name"
    assert conversation.context.get("expected_reply_reason") == "booking_specialist_availability_followup"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("service") == "Маникюр"
    assert booking.get("datetime") == "завтра 18:00"
    assert booking.get("last_question") == "name"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == reasoning_core.REASONING_CORE_TURN_PLANNER_SPECIALIST_NAME_COLLECT_STAGE
        and entry.get("pending_question_owner") == "booking_specialist_availability_followup"
        and entry.get("pending_question_target") == "specialist"
        and entry.get("active_question_relation") == "specialist_availability_followup"
        and entry.get("temporal_scope") == "specific_time"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_specialist_name_collect_owner_returns_terminal_unresolved_without_owner_conversation(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой мастер будет делать маникюр завтра в 18:00?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-service-choice-specialist-exact-time-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000171"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="service",
            current_goal="booking",
            booking_active=False,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent=None,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: None,
    )

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("frozen delegate must stay dead")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Reasoning core terminal unresolved response skipped"
    assert response.bot_response == decision_router.MSG_AI_ERROR
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_service_choice_specialist_exact_time_followup_falls_back_to_master_query_with_daypart(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой мастер будет делать маникюр завтра вечером в 18:00?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-service-choice-specialist-exact-time-bridge-2",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000172"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="service",
            current_goal="booking",
            booking_active=False,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent=None,
        ),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["intent"] == "master_query"
        assert policy_override["action"] == "fact"
        assert policy_override["reason"] == "master_question"
        assert policy_override["tool_args"] == {"service_query": "Маникюр"}
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_service_choice_specialist_daypart_collect_owner_bypasses_frozen_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой мастер будет делать маникюр завтра вечером?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-service-choice-specialist-day-bridge-2",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000169"),
        client_id=UUID("00000000-0000-0000-0000-000000000269"),
        user_id=UUID("00000000-0000-0000-0000-000000000369"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="bot_active",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []
    delegate_calls: list[bool] = []
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="service",
            current_goal="booking",
            booking_active=False,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent=None,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    async def _delegate(*args, **kwargs):
        delegate_calls.append(True)
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))
    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    expected_reply, specialist_meta = decision_router._build_specialist_availability_followup_response(
        service_query="Маникюр",
        client_slug="demo_salon",
        message_text="Какой мастер будет делать маникюр завтра вечером?",
        requested_slot="time",
    )

    assert response.success is True
    assert response.message == "Turn planner safe service-choice specialist daypart collect sent"
    assert response.bot_response == expected_reply
    assert response.conversation_id == conversation.id
    assert delegate_calls == []
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("action") == "booking_prompt"
    assert user_metadata.get("intent") == "booking"
    assert user_metadata.get("tool_action") == "collect"
    assert user_metadata.get("source") == "booking_specialist_availability_followup"
    assert user_metadata.get("pending_question_act") == "ask_about_requested_slot"
    assert user_metadata.get("pending_question_target") == "specialist"
    assert user_metadata.get("pending_question_interaction") == "specialist_availability_followup"
    assert user_metadata.get("pending_question_owner") == "booking_specialist_availability_followup"
    assert user_metadata.get("active_question_relation") == "specialist_availability_followup"
    assert user_metadata.get("booking_datetime") == "завтра вечером"
    assert user_metadata.get("temporal_scope") == "specific_time"
    assert user_metadata.get("expected_reply_type") == "time"
    assert user_metadata.get("expected_reply_reason") == "booking_specialist_availability_followup"
    assert (
        user_metadata.get("consultant_core_runtime", {}).get("owner_cutover")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_DAYPART_COLLECT_OWNER
    )
    assert user_metadata.get("turn_outcome", {}).get("action") == "booking_prompt"
    assert user_metadata.get("turn_outcome", {}).get("expected_reply_type") == "time"
    assert (
        user_metadata.get("turn_outcome", {}).get("expected_reply_reason")
        == "booking_specialist_availability_followup"
    )
    if isinstance(specialist_meta, dict):
        for key in (
            "info_sections",
            "fact_intents",
            "master_query_contract",
            "master_reply_mode",
            "master_profiles",
            "master_profiles_count",
            "service_query",
        ):
            value = specialist_meta.get(key)
            if value not in (None, [], {}):
                assert user_metadata.get(key) == value
    assert conversation.context.get("expected_reply_type") == "time"
    assert conversation.context.get("expected_reply_reason") == "booking_specialist_availability_followup"
    booking = conversation.context.get("booking") or {}
    assert booking.get("active") is True
    assert booking.get("service") == "Маникюр"
    assert booking.get("datetime") == "завтра вечером"
    assert booking.get("last_question") == "datetime"
    session_memory = conversation.context.get("session_memory") or {}
    assert session_memory.get("last_question_type") == "time"
    canonical_state = (conversation.context.get("context_manager") or {}).get("canonical_dialog_state") or {}
    assert canonical_state.get("pending_question_contract", {}).get("expected_reply_type") == "time"
    assert canonical_state.get("interaction_state", {}).get("resume_slot") == "datetime"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage")
        == reasoning_core.REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_DAYPART_COLLECT_STAGE
        and entry.get("pending_question_owner") == "booking_specialist_availability_followup"
        and entry.get("pending_question_target") == "specialist"
        and entry.get("active_question_relation") == "specialist_availability_followup"
        and entry.get("booking_datetime") == "завтра вечером"
        and entry.get("temporal_scope") == "specific_time"
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_service_choice_specialist_daypart_collect_owner_returns_terminal_unresolved_without_owner_conversation(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой мастер будет делать маникюр завтра вечером?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-service-choice-specialist-daypart-owner-fallback-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000173"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="service",
            current_goal="booking",
            booking_active=False,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent=None,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_turn_planner_owner_client",
        lambda *args, **kwargs: None,
    )

    async def _unexpected_delegate(*args, **kwargs):
        raise AssertionError("frozen delegate must stay dead")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _unexpected_delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Reasoning core terminal unresolved response skipped"
    assert response.bot_response == decision_router.MSG_AI_ERROR
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_service_choice_specialist_daypart_followup_falls_back_to_master_query_with_exact_time(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой мастер будет делать маникюр завтра вечером в 18:00?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-service-choice-specialist-daypart-bridge-2",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000170"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="service",
            current_goal="booking",
            booking_active=False,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent=None,
        ),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["intent"] == "master_query"
        assert policy_override["action"] == "fact"
        assert policy_override["reason"] == "master_question"
        assert policy_override["tool_args"] == {"service_query": "Маникюр"}
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_service_choice_specialist_weekday_followup_falls_back_to_master_query_without_service_reply_slot(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой мастер будет делать маникюр по будням?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-service-choice-specialist-weekday-bridge-2",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000167"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="time",
            current_goal="booking",
            booking_active=False,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent=None,
        ),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["intent"] == "master_query"
        assert policy_override["action"] == "fact"
        assert policy_override["reason"] == "master_question"
        assert policy_override["tool_args"] == {"service_query": "Маникюр"}
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_service_choice_specialist_weekend_followup_falls_back_to_hours_without_service_reply_slot(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Какой мастер будет делать маникюр на выходных?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-service-choice-specialist-weekend-bridge-2",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000165"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="time",
            current_goal="booking",
            booking_active=False,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token=None,
            booking_datetime_value=None,
            service_referent=None,
        ),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["intent"] == "hours"
        assert policy_override["action"] == "fact"
        assert policy_override["reason"] == "hours_question"
        assert policy_override["pack_refs"] == ["hours"]
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_primes_active_name_deictic_day_availability_followup_override_for_delegate(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="У вас есть свободные слоты на этот день?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-active-name-deictic-day-followup-bridge-1",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000154"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="name",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="booking_prompt",
            booking_time_token="03:00",
            service_referent="Маникюр",
        ),
    )

    async def _delegate(*args, **kwargs):
        policy_override = intent_service.get_policy_core_override()
        assert policy_override is not None
        assert policy_override["normalized_text"] == ai_service.normalize_for_matching(
            "У вас есть свободные слоты на этот день?"
        )
        assert policy_override["intent"] == "booking"
        assert policy_override["action"] == "collect"
        assert policy_override["tool_action"] == "collect"
        assert policy_override["reason"] == "booking_time_availability_followup"
        assert policy_override["goal"] == "booking"
        assert policy_override["slots"] == {
            "service": "Маникюр",
            "datetime": "03:00",
            "name": "",
        }
        assert policy_override["next_question"] == "name"
        assert policy_override["open_questions"] == ["name"]
        assert policy_override["subject_kind"] == "booking"
        assert policy_override["capability"] == "bookability"
        assert policy_override["temporal_scope"] == "specific_time"
        assert policy_override["resolution_mode"] == "referent_followup"
        assert policy_override["pending_question_act"] == "ask_about_requested_slot"
        assert policy_override["pending_question_target"] == "time"
        assert policy_override["active_question_relation"] == "ask_about_requested_slot"
        mock_llm = Mock()
        monkeypatch.setattr(intent_service, "get_llm_provider", mock_llm)
        policy_result = intent_service.route_llm_policy_core("У вас есть свободные слоты на этот день?")
        assert policy_result["ok"] is True
        assert policy_result["payload"]["slots"] == {
            "service": "Маникюр",
            "datetime": "03:00",
            "name": "",
        }
        assert policy_result["payload"]["capability"] == "bookability"
        assert policy_result["payload"]["temporal_scope"] == "specific_time"
        assert policy_result["payload"]["resolution_mode"] == "referent_followup"
        mock_llm.assert_not_called()
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_skips_active_name_deictic_day_availability_followup_without_booking_prompt_reason(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="У вас есть свободные слоты на этот день?",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-active-name-deictic-day-followup-bridge-2",
            ),
        ),
    )
    mock_db = Mock()
    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=UUID("00000000-0000-0000-0000-000000000155"),
            state="bot_active",
            bot_status="active",
            branch_id=None,
            reply_slot="name",
            current_goal="booking",
            booking_active=True,
            allow_bot_reply=True,
            resume_reason="other_followup",
            booking_time_token="03:00",
            service_referent="Маникюр",
        ),
    )

    async def _delegate(*args, **kwargs):
        assert intent_service.get_policy_core_override() is None
        return WebhookResponse(success=True, message="delegated")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "delegated"
    assert intent_service.get_policy_core_override() is None


@pytest.mark.asyncio
async def test_reasoning_core_primes_runtime_loader_overrides_for_delegate(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="Привет",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-runtime-loader-1",
            ),
        ),
    )
    client_id = UUID("00000000-0000-0000-0000-000000000130")
    branch_id = UUID("00000000-0000-0000-0000-000000000131")
    capability_runtime = RuntimeCapabilities(
        payload=CapabilitiesPayload(),
        client_id=client_id,
        branch_id=branch_id,
        source="reasoning_core",
        has_records=False,
    )
    truth_runtime = RuntimeTruth(
        truth={"salon": {"name": "Bridge"}},
        client_slug="demo_salon",
        branch_id=branch_id,
        source="reasoning_core",
        allow_fallback=False,
    )
    cached_preflight_payload = {
        "client": Mock(id=client_id),
        "settings": None,
        "body": payload.body,
        "metadata": payload.body.metadata,
        "message_id": payload.body.metadata.messageId,
        "remote_jid": payload.body.metadata.remoteJid,
        "message_text": payload.body.message,
        "message_type": payload.body.messageType,
        "has_media": False,
        "is_media_without_text": False,
        "media_info": None,
        "resolved_branch_id": branch_id,
        "tenant_context": {"client_slug": "demo_salon", "source": "webhook"},
    }

    monkeypatch.setattr(
        reasoning_core,
        "_run_secret_enforced_preflight",
        lambda *args, **kwargs: (None, cached_preflight_payload),
    )
    monkeypatch.setattr(
        reasoning_core,
        "build_runtime_capabilities",
        lambda *args, **kwargs: capability_runtime,
    )
    monkeypatch.setattr(
        reasoning_core,
        "build_runtime_truth",
        lambda *args, **kwargs: truth_runtime,
    )

    async def _greeting_owner(**kwargs):
        assert get_runtime_capabilities() is capability_runtime
        assert get_runtime_truth() is truth_runtime
        return WebhookResponse(success=True, message="owner")

    monkeypatch.setattr(
        reasoning_core,
        "_try_handle_turn_planner_safe_greeting_owner_cutover",
        _greeting_owner,
    )

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret="secret",
        enforce_secret=True,
    )

    assert response.success is True
    assert response.message == "owner"
    assert get_runtime_capabilities() is None
    assert get_runtime_truth() is None


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_safe_greeting_owner_family_defers_pending_ack(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="ок",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-greeting-owner-pending-ack",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000149"),
        client_id=UUID("00000000-0000-0000-0000-000000000249"),
        user_id=UUID("00000000-0000-0000-0000-000000000349"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="pending",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    finalize_calls: list[dict[str, object]] = []

    monkeypatch.setattr(reasoning_core, "_resolve_turn_planner_owner_client", lambda *args, **kwargs: client)
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(pending_router, "_is_pending_ack", lambda text: True)
    monkeypatch.setattr(
        reasoning_core,
        "_finalize_turn_planner_owner_cutover",
        lambda **kwargs: finalize_calls.append(kwargs) or WebhookResponse(success=True, message="owner"),
    )

    response = await reasoning_core._try_handle_turn_planner_safe_greeting_owner_cutover(
        payload=payload,
        db=mock_db,
        client_id=conversation.client_id,
        preflight_payload=None,
        conversation_id=conversation.id,
        enqueue_only=False,
        skip_persist=False,
        controller_route_snapshot=SimpleNamespace(
            reason=reasoning_core.REASONING_CORE_TURN_PLANNER_GREETING_REASON,
            controller_class="greeting",
            normalized_text="ок",
            goal=None,
            confidence=0.99,
        ),
    )

    assert response is None
    assert finalize_calls == []


@pytest.mark.asyncio
async def test_reasoning_core_turn_planner_pending_ack_continuity_family_clears_pending_before_terminal_unresolved(
    monkeypatch,
):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="ок",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-pending-ack-continuity-owner",
            ),
        ),
    )
    mock_db = Mock()
    conversation = Conversation(
        id=UUID("00000000-0000-0000-0000-000000000150"),
        client_id=UUID("00000000-0000-0000-0000-000000000250"),
        user_id=UUID("00000000-0000-0000-0000-000000000350"),
        channel="whatsapp",
        status="active",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        state="pending",
        context={},
    )
    client = Client(
        id=conversation.client_id,
        name="demo_salon",
        status="active",
        config={"instance_id": "inst-1"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    saved_messages: list[Message] = []

    monkeypatch.setattr(reasoning_core, "_lookup_active_sender_branch", lambda *args, **kwargs: None)
    monkeypatch.setattr(reasoning_core, "_lookup_client_branch_phone", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reasoning_core,
        "_lookup_preexisting_duplicate_message",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreDuplicateProbe(duplicate=False),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_active_conversation_snapshot",
        lambda *args, **kwargs: reasoning_core.ReasoningCoreConversationSnapshot(
            conversation_id=conversation.id,
            state="pending",
            bot_status="active",
            branch_id=None,
            reply_slot=None,
            current_goal=None,
            booking_active=False,
            allow_bot_reply=True,
        ),
    )
    monkeypatch.setattr(
        reasoning_core,
        "_resolve_client_config_for_domain_routing",
        lambda *args, **kwargs: {
            "domain_router": {
                "anchors_in": ["маникюр"],
                "anchors_out": ["налоговая"],
            }
        },
    )
    monkeypatch.setattr(reasoning_core, "_resolve_turn_planner_owner_client", lambda *args, **kwargs: client)
    monkeypatch.setattr(
        reasoning_core,
        "_ensure_turn_planner_owner_conversation",
        lambda *args, **kwargs: conversation,
    )
    monkeypatch.setattr(reasoning_core, "get_active_handover", lambda *args, **kwargs: None)
    monkeypatch.setattr(pending_router, "_is_pending_ack", lambda text: True)

    def _save_message(db, conversation_id, client_id, role, content, message_metadata=None):
        message = Message(
            conversation_id=conversation_id,
            client_id=client_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        saved_messages.append(message)
        return message

    monkeypatch.setattr(reasoning_core, "save_message", _save_message)
    monkeypatch.setattr(reasoning_core, "get_instance_id", lambda *args, **kwargs: "inst-1")
    monkeypatch.setattr(reasoning_core, "send_message_safe", lambda *args, **kwargs: Ok("ok"))

    response = await reasoning_core.handle_webhook_payload(
        payload,
        mock_db,
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    assert response.message == "Pending ack response sent"
    assert response.bot_response == decision_router.MSG_PENDING_ACK
    assert response.conversation_id == conversation.id
    assert conversation.state == "bot_active"
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    user_metadata = saved_messages[0].message_metadata.get("decision_meta") or {}
    assert user_metadata.get("owner_cutover") == reasoning_core.REASONING_CORE_TURN_PLANNER_PENDING_ACK_OWNER
    assert user_metadata.get("pending_action") == "pending_ack"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        isinstance(entry, dict)
        and entry.get("stage") == "pending_sla"
        and entry.get("decision") == "pending_ack"
        and entry.get("owner_cutover") == reasoning_core.REASONING_CORE_TURN_PLANNER_PENDING_ACK_OWNER
        for entry in trace
    )
    assert mock_db.commit.call_count == 1


def test_build_empty_message_artifact_uses_new_core_contracts():
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


def test_build_sender_branch_ignore_artifact_uses_new_core_contracts():
    artifact = reasoning_core._build_sender_branch_ignore_artifact()

    assert artifact.turn_result.contract_status == "blocked"
    assert artifact.turn_result.outcome == "FACT"
    assert artifact.turn_result.boundary_override is not None
    assert (
        artifact.turn_result.boundary_override.reason_code
        == reasoning_core.REASONING_CORE_SENDER_BRANCH_IGNORE_REASON
    )
    assert artifact.turn_result.reply.reply_kind == "system"
    assert artifact.turn_result.reply.text == ""
    turn_outcome = artifact.turn_outcome.to_metadata()
    assert turn_outcome["action"] == "ignore"
    assert turn_outcome["intent"] == "sender_is_branch"
    assert turn_outcome["observability"]["transport_reason"] == "sender_is_branch"
    assert turn_outcome["meta"]["ignored_path"] is True


def test_build_missing_remote_jid_artifact_uses_new_core_contracts():
    artifact = reasoning_core._build_missing_remote_jid_artifact()

    assert artifact.turn_result.contract_status == "blocked"
    assert artifact.turn_result.outcome == "FACT"
    assert artifact.turn_result.boundary_override is not None
    assert (
        artifact.turn_result.boundary_override.reason_code
        == reasoning_core.REASONING_CORE_MISSING_REMOTE_JID_REASON
    )
    assert artifact.turn_result.reply.reply_kind == "system"
    assert artifact.turn_result.reply.text == ""
    turn_outcome = artifact.turn_outcome.to_metadata()
    assert turn_outcome["action"] == "reject"
    assert turn_outcome["intent"] == "missing_remote_jid"
    assert turn_outcome["observability"]["transport_reason"] == "missing_remote_jid"
    assert turn_outcome["meta"]["preflight_path"] is True


def test_build_missing_tenant_context_artifact_uses_new_core_contracts():
    artifact = reasoning_core._build_missing_tenant_context_artifact()

    assert artifact.turn_result.contract_status == "blocked"
    assert artifact.turn_result.outcome == "FACT"
    assert artifact.turn_result.boundary_override is not None
    assert (
        artifact.turn_result.boundary_override.reason_code
        == reasoning_core.REASONING_CORE_MISSING_TENANT_CONTEXT_REASON
    )
    assert artifact.turn_result.reply.reply_kind == "system"
    assert artifact.turn_result.reply.text == ""
    turn_outcome = artifact.turn_outcome.to_metadata()
    assert turn_outcome["action"] == "reject"
    assert turn_outcome["intent"] == "missing_tenant_context"
    assert turn_outcome["observability"]["transport_reason"] == "missing_tenant_context"
    assert turn_outcome["meta"]["preflight_path"] is True


def test_build_tenant_context_reject_artifact_uses_new_core_contracts():
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
    assert (
        artifact.turn_result.boundary_override.reason_code
        == reasoning_core.REASONING_CORE_TENANT_CONTEXT_INVALID_REASON
    )
    assert artifact.turn_result.reply.reply_kind == "system"
    assert artifact.turn_result.reply.text == ""
    turn_outcome = artifact.turn_outcome.to_metadata()
    assert turn_outcome["action"] == "reject"
    assert turn_outcome["intent"] == "tenant_context_contract_invalid"
    assert turn_outcome["observability"]["transport_reason"] == "tenant_context_contract_invalid"
    assert turn_outcome["meta"]["tenant_context_guard"] is True
    assert turn_outcome["meta"]["error"] == "$: invalid source"


def test_build_remote_branch_phone_ignore_artifact_uses_new_core_contracts():
    artifact = reasoning_core._build_remote_branch_phone_ignore_artifact(
        matched_phone="+7 (705) 574-04-56",
    )

    assert artifact.turn_result.contract_status == "blocked"
    assert artifact.turn_result.outcome == "FACT"
    assert artifact.turn_result.boundary_override is not None
    assert (
        artifact.turn_result.boundary_override.reason_code
        == reasoning_core.REASONING_CORE_REMOTE_BRANCH_PHONE_REASON
    )
    assert artifact.turn_result.reply.reply_kind == "system"
    assert artifact.turn_result.reply.text == ""
    turn_outcome = artifact.turn_outcome.to_metadata()
    assert turn_outcome["action"] == "ignore"
    assert turn_outcome["intent"] == "remote_is_branch_phone"
    assert turn_outcome["observability"]["transport_reason"] == "remote_is_branch_phone"
    assert turn_outcome["meta"]["matched_phone"] == "+7 (705) 574-04-56"
    assert turn_outcome["meta"]["ignored_path"] is True


def test_build_duplicate_message_artifact_uses_new_core_contracts():
    artifact = reasoning_core._build_duplicate_message_artifact(
        dedup_backend="message_dedup",
        dedup_fallback_reason=None,
    )

    assert artifact.turn_result.contract_status == "blocked"
    assert artifact.turn_result.outcome == "FACT"
    assert artifact.turn_result.boundary_override is not None
    assert (
        artifact.turn_result.boundary_override.reason_code
        == reasoning_core.REASONING_CORE_DUPLICATE_REASON
    )
    assert artifact.turn_result.reply.reply_kind == "system"
    assert artifact.turn_result.reply.text == ""
    turn_outcome = artifact.turn_outcome.to_metadata()
    assert turn_outcome["action"] == "ignore"
    assert turn_outcome["intent"] == "duplicate_message_id"
    assert turn_outcome["observability"]["transport_reason"] == "duplicate_message_id"
    assert turn_outcome["meta"]["dedup_backend"] == "message_dedup"
    assert turn_outcome["meta"]["preexisting_duplicate"] is True


def test_lookup_preexisting_duplicate_message_respects_fast_bypass(monkeypatch):
    db = Mock()

    monkeypatch.setattr(reasoning_core, "_is_fast_dedup_bypass_enabled", lambda: True)

    probe = reasoning_core._lookup_preexisting_duplicate_message(
        db,
        client_id=UUID("00000000-0000-0000-0000-000000000023"),
        message_id="msg-fast-dedup",
    )

    assert probe.duplicate is False
    assert probe.backend == "fast_test_bypass"
    assert probe.fallback_reason == "test_mode_fast_dedup"
    db.execute.assert_not_called()
    db.query.assert_not_called()


def test_lookup_preexisting_duplicate_message_delegates_to_dedup_owner(monkeypatch):
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


@pytest.mark.asyncio
async def test_reasoning_core_media_caption_promotes_to_message_before_delegate(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message=None,
            messageType="image",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-image-caption-1",
            ),
            mediaData={
                "type": "image",
                "caption": "  посмотрите варианты  ",
            },
        ),
    )
    captured: dict[str, object] = {}

    async def _delegate(payload, db, **kwargs):
        captured["payload"] = payload
        return WebhookResponse(success=True, message="delegated", bot_response="ok")

    monkeypatch.setattr(decision_router, "_handle_webhook_payload", _delegate)

    response = await reasoning_core.handle_webhook_payload(
        payload,
        Mock(),
        provided_secret=None,
        enforce_secret=False,
    )

    assert response.success is True
    delegated_payload = captured["payload"]
    assert delegated_payload.body.message == "посмотрите варианты"
    assert payload.body.message is None


def test_normalize_payload_for_delegation_trims_empty_non_media_to_none():
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
