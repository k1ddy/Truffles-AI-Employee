"""Unified Reasoning Core API (signals -> gates -> actions -> compose -> trace)."""

from __future__ import annotations

import hashlib
import time
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Callable, Iterator, Sequence
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.adapters.chatflow import ChatFlowAdapter
from app.core import (
    BlockBoundaryRequest,
    DegradeBoundaryRequest,
    PolicyDecision,
    DialogStateService,
    OwnerCutoverAction,
    PolicyCoreRouteSnapshot,
    TurnExecutor,
    TurnPlanner,
    TurnResult,
)
from app.core.booking_prompt_owner import (
    resolve_llm_booking_prompt_candidate,
    resolve_pending_booking_reactivation_candidate,
)
from app.core.turn_executor import OwnerExecutionArtifact, ToolReplyOwnerExecution
from app.logging_config import (
    get_logger,
    get_trace_id,
    record_delivery_failure,
    record_escalation_count,
    start_span,
)
from app.ports.messaging import MessageOptions
from app.models import Branch, Client, Conversation, Message, User
from app.routers.webhook import context_manager as context_manager_router
from app.routers.webhook import decision as decision_router
from app.routers.webhook import info as info_router
from app.routers.webhook.media import _extract_media_info
from app.routers.webhook.session_memory import (
    _is_session_reset_only_message,
    _record_session_memory_update,
)
from app.routers.webhook.runtime_primitives import SERVICE_CARRYOVER_TTL_MESSAGES
from app.routers.webhook.trace import (
    DECISION_STAGE_ORDER_SNAPSHOT,
    _record_decision_trace,
    _record_message_decision_meta,
    _update_message_decision_metadata,
)
from app.schemas.turn_outcome import TurnOutcome
from app.schemas.webhook import WebhookRequest, WebhookResponse
from app.services.alert_service import alert_error
from app.services.ai_service import (
    ACKNOWLEDGEMENT_RESPONSE,
    GREETING_RESPONSE,
    THANKS_RESPONSE,
    is_acknowledgement_message,
    is_greeting_message,
    is_thanks_message,
    use_intent_signal_override,
)
from app.services.booking_signal_service import extract_time_token
from app.services.capabilities_runtime import (
    build_runtime_capabilities,
    use_runtime_capabilities_override,
)
from app.services.chatflow_service import send_message_safe
from app.services.chatflow_service import get_instance_id
from app.services.handover_owner_service import (
    get_active_handover,
    manager_resolve,
    materialize_handover,
)
from app.services.intent_service import (
    extract_customer_name_hint_llm,
    extract_service_query_hint_llm,
    extract_specialist_hint_llm,
    route_llm_policy_core,
    use_dialogue_controller_override,
    use_domain_routing_override,
    use_intent_semantic_override,
)
from app.services.knowledge_runtime import (
    build_runtime_truth,
    should_allow_truth_fallback,
    use_runtime_truth_override,
)
from app.services.conversation_service import get_or_create_conversation, get_or_create_user
from app.services.message_service import save_message
from app.services.pack_runtime_service import (
    build_master_reply_from_pack,
    resolve_master_intent,
)
from app.services.policy_timeout_booking_specialist_boundary_service import (
    PolicyTimeoutBookingSpecialistBoundaryRuntimeHooks,
    PolicyTimeoutBookingSpecialistBoundaryRuntimeInput,
    handle_policy_timeout_booking_specialist_boundary,
)
from app.services.booking_transition_owner import (
    apply_tool_transition_owner,
)
from app.services.expected_reply_contract import (
    expected_reply_slot_key,
    resolve_services_overview_contract_update,
    resolve_tool_expected_reply_contract,
)
from app.services.state_service import (
    PendingContinuityRuntimeHooks,
    _resolve_pending_ack,
    transition_state,
)
from app.services.state_machine import ConversationState
from app.services.tenant_context_contract import validate_tenant_context_contract
from app.services.tool_registry_service import execute_tool_action

STAGE_ORDER_SNAPSHOT = DECISION_STAGE_ORDER_SNAPSHOT
REASONING_CORE_DEGRADE_REASON = "runtime_exception"
REASONING_CORE_DEGRADE_OWNER = "reasoning_core_exception_degrade"
REASONING_CORE_TERMINAL_UNRESOLVED_REASON = "terminal_owner_unresolved"
REASONING_CORE_TERMINAL_UNRESOLVED_OWNER = "reasoning_core_terminal_unresolved"
REASONING_CORE_PREFLIGHT_REASON = "empty_message"
REASONING_CORE_PREFLIGHT_OWNER = "reasoning_core_empty_message"
REASONING_CORE_MISSING_REMOTE_JID_REASON = "missing_remote_jid"
REASONING_CORE_MISSING_REMOTE_JID_OWNER = "reasoning_core_missing_remote_jid"
REASONING_CORE_MISSING_TENANT_CONTEXT_REASON = "missing_tenant_context"
REASONING_CORE_MISSING_TENANT_CONTEXT_OWNER = "reasoning_core_missing_tenant_context"
REASONING_CORE_SENDER_BRANCH_IGNORE_REASON = "sender_is_branch"
REASONING_CORE_SENDER_BRANCH_IGNORE_OWNER = "reasoning_core_sender_branch_ignore"
REASONING_CORE_TENANT_CONTEXT_INVALID_REASON = "tenant_context_contract_invalid"
REASONING_CORE_TENANT_CONTEXT_INVALID_OWNER = "reasoning_core_tenant_context_invalid"
REASONING_CORE_TENANT_CONTEXT_CLIENT_MISMATCH_REASON = "tenant_context_client_mismatch"
REASONING_CORE_TENANT_CONTEXT_CLIENT_MISMATCH_OWNER = "reasoning_core_tenant_context_client_mismatch"
REASONING_CORE_TENANT_CONTEXT_CLIENT_SLUG_MISMATCH_REASON = "tenant_context_client_slug_mismatch"
REASONING_CORE_TENANT_CONTEXT_CLIENT_SLUG_MISMATCH_OWNER = (
    "reasoning_core_tenant_context_client_slug_mismatch"
)
REASONING_CORE_REMOTE_BRANCH_PHONE_REASON = "remote_is_branch_phone"
REASONING_CORE_REMOTE_BRANCH_PHONE_OWNER = "reasoning_core_remote_branch_phone_ignore"
REASONING_CORE_DUPLICATE_REASON = "duplicate_message_id"
REASONING_CORE_DUPLICATE_OWNER = "reasoning_core_duplicate_message"
REASONING_CORE_TURN_PLANNER_INFO_OWNER = "turn_planner.safe_info_fact.v1"
REASONING_CORE_TURN_PLANNER_INFO_STAGE = "turn_planner_safe_info_fact"
REASONING_CORE_TURN_PLANNER_INFO_INTENTS = frozenset(
    {"contact", "hours", "promotions", "promotions_rules"}
)
REASONING_CORE_TURN_PLANNER_CATALOG_FACT_OWNER = "turn_planner.safe_catalog_fact.v1"
REASONING_CORE_TURN_PLANNER_CATALOG_FACT_STAGE = "turn_planner_safe_catalog_fact"
REASONING_CORE_TURN_PLANNER_CATALOG_FACT_INTENTS = frozenset(
    {"services_overview", "location", "portfolio"}
)
REASONING_CORE_TURN_PLANNER_SERVICE_QUERY_FACT_OWNER = (
    "turn_planner.safe_service_query_fact.v1"
)
REASONING_CORE_TURN_PLANNER_SERVICE_QUERY_FACT_STAGE = (
    "turn_planner_safe_service_query_fact"
)
REASONING_CORE_TURN_PLANNER_PRICING_COLLECT_OWNER = (
    "turn_planner.safe_pricing_collect.v1"
)
REASONING_CORE_TURN_PLANNER_PRICING_COLLECT_STAGE = (
    "turn_planner_safe_pricing_collect"
)
REASONING_CORE_TURN_PLANNER_DURATION_COLLECT_OWNER = (
    "turn_planner.safe_duration_collect.v1"
)
REASONING_CORE_TURN_PLANNER_DURATION_COLLECT_STAGE = (
    "turn_planner_safe_duration_collect"
)
REASONING_CORE_TURN_PLANNER_BOOKABILITY_TIME_COLLECT_OWNER = (
    "turn_planner.safe_bookability_time_collect.v1"
)
REASONING_CORE_TURN_PLANNER_BOOKABILITY_TIME_COLLECT_STAGE = (
    "turn_planner_safe_bookability_time_collect"
)
REASONING_CORE_INITIAL_BOOKING_POLICY_CORE_MAX_TOKENS = 160
REASONING_CORE_TURN_PLANNER_ACTIVE_NAME_TIME_COLLECT_OWNER = (
    "turn_planner.safe_active_name_time_collect.v1"
)
REASONING_CORE_TURN_PLANNER_ACTIVE_NAME_TIME_COLLECT_STAGE = (
    "turn_planner_safe_active_name_time_collect"
)
REASONING_CORE_TURN_PLANNER_SPECIALIST_NAME_COLLECT_OWNER = (
    "turn_planner.safe_specialist_name_collect.v1"
)
REASONING_CORE_TURN_PLANNER_SPECIALIST_NAME_COLLECT_STAGE = (
    "turn_planner_safe_specialist_name_collect"
)
REASONING_CORE_TURN_PLANNER_SPECIALIST_DATETIME_COLLECT_OWNER = (
    "turn_planner.safe_specialist_datetime_collect.v1"
)
REASONING_CORE_TURN_PLANNER_SPECIALIST_DATETIME_COLLECT_STAGE = (
    "turn_planner_safe_specialist_datetime_collect"
)
REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_TIME_COLLECT_OWNER = (
    "turn_planner.safe_service_choice_specialist_time_collect.v1"
)
REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_TIME_COLLECT_STAGE = (
    "turn_planner_safe_service_choice_specialist_time_collect"
)
REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_TIME_COLLECT_REASONS = frozenset(
    {"day_followup", "weekday_followup", "weekend_followup"}
)
REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_DAYPART_COLLECT_OWNER = (
    "turn_planner.safe_service_choice_specialist_daypart_collect.v1"
)
REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_DAYPART_COLLECT_STAGE = (
    "turn_planner_safe_service_choice_specialist_daypart_collect"
)
REASONING_CORE_TURN_PLANNER_MASTER_QUERY_FACT_OWNER = (
    "turn_planner.safe_master_query_fact.v1"
)
REASONING_CORE_TURN_PLANNER_MASTER_QUERY_FACT_STAGE = (
    "turn_planner_safe_master_query_fact"
)
REASONING_CORE_TURN_PLANNER_MASTER_QUERY_COLLECT_OWNER = (
    "turn_planner.safe_master_query_collect.v1"
)
REASONING_CORE_TURN_PLANNER_MASTER_QUERY_COLLECT_STAGE = (
    "turn_planner_safe_master_query_collect"
)
REASONING_CORE_TURN_PLANNER_MASTER_QUERY_SERVICE_NOT_FOUND_OWNER = (
    "turn_planner.safe_master_query_service_not_found_collect.v1"
)
REASONING_CORE_TURN_PLANNER_MASTER_QUERY_SERVICE_NOT_FOUND_STAGE = (
    "turn_planner_safe_master_query_service_not_found_collect"
)
REASONING_CORE_TURN_PLANNER_BOOKING_VERIFICATION_OWNER = (
    "turn_planner.safe_booking_verification_fact.v1"
)
REASONING_CORE_TURN_PLANNER_BOOKING_VERIFICATION_STAGE = (
    "turn_planner_safe_booking_verification_fact"
)
REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_OWNER = (
    "turn_planner.safe_booking_prompt_owner.v1"
)
REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE = (
    "turn_planner_safe_booking_prompt_owner"
)
REASONING_CORE_TURN_PLANNER_BOOKING_COMPLETION_OWNER = (
    "turn_planner.safe_booking_completion_owner.v1"
)
REASONING_CORE_TURN_PLANNER_BOOKING_COMPLETION_STAGE = (
    "turn_planner_safe_booking_completion_owner"
)
REASONING_CORE_TURN_PLANNER_SPECIALIST_FOLLOWUP_OWNER = (
    "turn_planner.safe_specialist_followup_owner.v1"
)
REASONING_CORE_TURN_PLANNER_SPECIALIST_FOLLOWUP_STAGE = (
    "turn_planner_safe_specialist_followup_owner"
)
REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_OWNER = (
    "turn_planner.safe_explicit_handoff_owner.v1"
)
REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_STAGE = (
    "turn_planner_safe_explicit_handoff_owner"
)
REASONING_CORE_TURN_PLANNER_PENDING_ACK_OWNER = (
    "turn_planner.safe_pending_ack_continuity.v1"
)
REASONING_CORE_TURN_PLANNER_PENDING_ACK_STAGE = (
    "turn_planner_safe_pending_ack_continuity"
)
REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_REASONS = frozenset(
    {
        "ingress_explicit_human_request",
        "ingress_explicit_frustration_handoff",
        "reschedule_missing_reference",
        "semantic_arbitration_needs_manager",
        "semantic_arbitration_risk_signal",
        "terminal_owner_unresolved",
    }
)
REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_INTENTS = frozenset(
    {"human_request", "frustration", "reschedule", "policy_core_guard"}
)
REASONING_CORE_TURN_PLANNER_GREETING_OWNER = (
    "turn_planner.safe_greeting_owner.v1"
)
REASONING_CORE_TURN_PLANNER_GREETING_STAGE = (
    "turn_planner_safe_greeting_owner"
)
REASONING_CORE_TURN_PLANNER_GREETING_REASON = "ingress_lexical_greeting"
REASONING_CORE_TURN_PLANNER_GREETING_INTENTS = frozenset(
    {"greeting", "thanks", "ack"}
)

logger = get_logger("reasoning_core")
_EXPECTED_REPLY_TYPE_FIELD = "_".join(("expected", "reply", "type"))
_ER_KEY = "expected_reply" "_type"
_ERR_KEY = "expected_reply" "_reason"


@dataclass(frozen=True)
class ReasoningCoreRequest:
    payload: WebhookRequest
    db: Session
    provided_secret: str | None
    enforce_secret: bool
    enqueue_only: bool = False
    skip_persist: bool = False
    conversation_id: UUID | None = None
    batch_messages: list[str] | None = None
    outbox_ids: list[str] | None = None
    outbox_created_at: datetime | None = None
    preflight_payload: dict[str, object] | None = None


@dataclass(frozen=True)
class ReasoningCoreDegradeArtifact:
    turn_result: TurnResult
    turn_outcome: TurnOutcome


@dataclass(frozen=True)
class ReasoningCorePreflightArtifact:
    turn_result: TurnResult
    turn_outcome: TurnOutcome


@dataclass(frozen=True)
class ReasoningCoreDuplicateProbe:
    duplicate: bool
    backend: str | None = None
    fallback_reason: str | None = None


@dataclass(frozen=True)
class ReasoningCoreTenantContextRejection:
    reason_code: str
    message: str
    interaction_owner: str
    trace_message: str
    meta: dict[str, object] | None = None


@dataclass(frozen=True)
class ReasoningCoreConversationSnapshot:
    conversation_id: UUID
    state: str
    bot_status: str | None
    branch_id: UUID | None
    reply_slot: str | None
    current_goal: str | None
    booking_active: bool
    allow_bot_reply: bool
    resume_reason: str | None = None
    booking_time_token: str | None = None
    booking_datetime_value: str | None = None
    service_referent: str | None = None


@dataclass(frozen=True)
class ReasoningCoreBookingPromptPolicyCandidate:
    booking_state: dict[str, object]
    reply_meta: dict[str, object]
    trace_meta: dict[str, object]


def stage_order_hash(stage_order: Sequence[str] | None = None) -> str:
    order = stage_order or STAGE_ORDER_SNAPSHOT
    joined = "\n".join(order)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _build_runtime_exception_artifact(
    *,
    bot_response: str,
    transport_status: str,
    transport_reason: str | None,
) -> ReasoningCoreDegradeArtifact:
    artifact = TurnExecutor().build_degrade_boundary_artifact_from_request(
        request=DegradeBoundaryRequest(
            reason_code=REASONING_CORE_DEGRADE_REASON,
            action="handoff",
            intent="runtime_error",
            interaction_owner=REASONING_CORE_DEGRADE_OWNER,
            interaction_relation="runtime_exception",
            public_message=bot_response,
            trace_message="reasoning_core exception degraded through new core",
            transport_status=transport_status,
            transport_reason=transport_reason,
            override_meta={"source": "reasoning_core"},
        )
    )
    return ReasoningCoreDegradeArtifact(
        turn_result=artifact.turn_result,
        turn_outcome=artifact.turn_outcome,
    )


def _build_terminal_unresolved_artifact(
    *,
    bot_response: str,
    transport_status: str,
    transport_reason: str | None,
) -> ReasoningCoreDegradeArtifact:
    artifact = TurnExecutor().build_degrade_boundary_artifact_from_request(
        request=DegradeBoundaryRequest(
            reason_code=REASONING_CORE_TERMINAL_UNRESOLVED_REASON,
            action="handoff",
            intent="policy_core_guard",
            interaction_owner=REASONING_CORE_TERMINAL_UNRESOLVED_OWNER,
            interaction_relation="terminal_unresolved",
            public_message=bot_response,
            trace_message="reasoning_core terminal unresolved path removed frozen delegate",
            transport_status=transport_status,
            transport_reason=transport_reason,
            override_meta={"source": "reasoning_core"},
        )
    )
    return ReasoningCoreDegradeArtifact(
        turn_result=artifact.turn_result,
        turn_outcome=artifact.turn_outcome,
    )


def _build_empty_message_artifact() -> ReasoningCorePreflightArtifact:
    artifact = TurnExecutor().build_block_boundary_artifact_from_request(
        request=BlockBoundaryRequest(
            reason_code=REASONING_CORE_PREFLIGHT_REASON,
            action="preflight_reject",
            intent="empty_message",
            interaction_owner=REASONING_CORE_PREFLIGHT_OWNER,
            interaction_relation="empty_message",
            trace_message="reasoning_core blocked empty non-media inbound",
            replan_hints=["require non-empty text or media"],
            tool_action="preflight.empty_message",
            override_meta={"source": "reasoning_core"},
        )
    )
    return ReasoningCorePreflightArtifact(
        turn_result=artifact.turn_result,
        turn_outcome=artifact.turn_outcome,
    )


def _build_missing_remote_jid_artifact() -> ReasoningCorePreflightArtifact:
    artifact = TurnExecutor().build_block_boundary_artifact_from_request(
        request=BlockBoundaryRequest(
            reason_code=REASONING_CORE_MISSING_REMOTE_JID_REASON,
            action="preflight_reject",
            intent="missing_remote_jid",
            interaction_owner=REASONING_CORE_MISSING_REMOTE_JID_OWNER,
            interaction_relation="missing_remote_jid",
            trace_message="reasoning_core blocked inbound without metadata.remoteJid",
            replan_hints=["require metadata.remoteJid"],
            tool_action="preflight.missing_remote_jid",
            override_meta={"source": "reasoning_core"},
        )
    )
    return ReasoningCorePreflightArtifact(
        turn_result=artifact.turn_result,
        turn_outcome=artifact.turn_outcome,
    )


def _build_missing_tenant_context_artifact() -> ReasoningCorePreflightArtifact:
    artifact = TurnExecutor().build_block_boundary_artifact_from_request(
        request=BlockBoundaryRequest(
            reason_code=REASONING_CORE_MISSING_TENANT_CONTEXT_REASON,
            action="preflight_reject",
            intent="missing_tenant_context",
            interaction_owner=REASONING_CORE_MISSING_TENANT_CONTEXT_OWNER,
            interaction_relation="missing_tenant_context",
            trace_message="reasoning_core blocked inbound without usable tenant_context",
            replan_hints=["require tenant_context client_id or client_slug"],
            tool_action="preflight.missing_tenant_context",
            override_meta={"source": "reasoning_core"},
        )
    )
    return ReasoningCorePreflightArtifact(
        turn_result=artifact.turn_result,
        turn_outcome=artifact.turn_outcome,
    )


def _build_sender_branch_ignore_artifact() -> ReasoningCorePreflightArtifact:
    artifact = TurnExecutor().build_block_boundary_artifact_from_request(
        request=BlockBoundaryRequest(
            reason_code=REASONING_CORE_SENDER_BRANCH_IGNORE_REASON,
            action="ignore",
            intent="sender_is_branch",
            interaction_owner=REASONING_CORE_SENDER_BRANCH_IGNORE_OWNER,
            interaction_relation="sender_is_branch",
            trace_message="reasoning_core ignored active branch sender",
            replan_hints=["skip branch-originated inbound"],
            tool_action="preflight.sender_is_branch",
            ignored=True,
            override_meta={"source": "reasoning_core"},
        )
    )
    return ReasoningCorePreflightArtifact(
        turn_result=artifact.turn_result,
        turn_outcome=artifact.turn_outcome,
    )


def _build_tenant_context_reject_artifact(
    *,
    rejection: ReasoningCoreTenantContextRejection,
) -> ReasoningCorePreflightArtifact:
    meta = rejection.meta or {}
    artifact = TurnExecutor().build_block_boundary_artifact_from_request(
        request=BlockBoundaryRequest(
            reason_code=rejection.reason_code,
            action="preflight_reject",
            intent=rejection.reason_code,
            interaction_owner=rejection.interaction_owner,
            interaction_relation=rejection.reason_code,
            trace_message=rejection.trace_message,
            replan_hints=["require valid tenant_context contract"],
            tool_action=f"preflight.{rejection.reason_code}",
            override_meta={
                "source": "reasoning_core",
                **meta,
            },
            outcome_meta={
                "tenant_context_guard": True,
                **meta,
            },
        )
    )
    return ReasoningCorePreflightArtifact(
        turn_result=artifact.turn_result,
        turn_outcome=artifact.turn_outcome,
    )


def _build_remote_branch_phone_ignore_artifact(
    *,
    matched_phone: str | None,
) -> ReasoningCorePreflightArtifact:
    artifact = TurnExecutor().build_block_boundary_artifact_from_request(
        request=BlockBoundaryRequest(
            reason_code=REASONING_CORE_REMOTE_BRANCH_PHONE_REASON,
            action="ignore",
            intent="remote_is_branch_phone",
            interaction_owner=REASONING_CORE_REMOTE_BRANCH_PHONE_OWNER,
            interaction_relation="remote_is_branch_phone",
            trace_message="reasoning_core ignored same-client branch phone sender",
            replan_hints=["skip same-client branch phone inbound"],
            tool_action="preflight.remote_is_branch_phone",
            ignored=True,
            override_meta={
                "source": "reasoning_core",
                "matched_phone": matched_phone,
            },
            outcome_meta={"matched_phone": matched_phone},
        )
    )
    return ReasoningCorePreflightArtifact(
        turn_result=artifact.turn_result,
        turn_outcome=artifact.turn_outcome,
    )


def _build_duplicate_message_artifact(
    *,
    dedup_backend: str | None,
    dedup_fallback_reason: str | None,
) -> ReasoningCorePreflightArtifact:
    artifact = TurnExecutor().build_block_boundary_artifact_from_request(
        request=BlockBoundaryRequest(
            reason_code=REASONING_CORE_DUPLICATE_REASON,
            action="ignore",
            intent="duplicate_message_id",
            interaction_owner=REASONING_CORE_DUPLICATE_OWNER,
            interaction_relation="duplicate_message_id",
            trace_message="reasoning_core ignored preexisting duplicate message_id",
            replan_hints=["skip duplicate inbound message_id"],
            tool_action="preflight.duplicate_message_id",
            ignored=True,
            override_meta={
                "source": "reasoning_core",
                "dedup_backend": dedup_backend,
                "dedup_fallback_reason": dedup_fallback_reason,
            },
            outcome_meta={
                "dedup_backend": dedup_backend,
                "dedup_fallback_reason": dedup_fallback_reason,
                "preexisting_duplicate": True,
            },
        )
    )
    return ReasoningCorePreflightArtifact(
        turn_result=artifact.turn_result,
        turn_outcome=artifact.turn_outcome,
    )


def _lookup_active_sender_branch(db: Session, remote_jid: str | None):
    if not remote_jid:
        return None
    from app.routers.webhook import http as http_helpers

    branch = http_helpers._lookup_sender_branch(db, remote_jid)
    phone = getattr(branch, "phone", None)
    if not isinstance(phone, str) or not phone.strip():
        return None
    return branch


def _lookup_client_branch_phone(
    db: Session,
    *,
    client_id: UUID | None,
    remote_jid: str | None,
) -> str | None:
    if client_id is None or not remote_jid:
        return None
    from app.routers.webhook import http as http_helpers

    remote_digits = http_helpers._normalize_phone_digits(remote_jid)
    if not remote_digits:
        return None
    branch_phones = (
        db.query(Branch.phone)
        .filter(Branch.client_id == client_id, Branch.phone.isnot(None))
        .all()
    )
    if not isinstance(branch_phones, list):
        return None
    for row in branch_phones:
        if isinstance(row, (list, tuple)):
            phone = row[0] if row else None
        else:
            phone = getattr(row, "phone", None)
        if not isinstance(phone, str) or not phone.strip():
            continue
        if remote_digits == http_helpers._normalize_phone_digits(phone):
            return phone
    return None


def _is_fast_dedup_bypass_enabled() -> bool:
    from app.routers.webhook import dedup as dedup_helpers

    return dedup_helpers._is_fast_dedup_bypass_enabled()


def _resolve_preflight_client_id(db: Session, payload: WebhookRequest) -> UUID | None:
    client_slug = (payload.client_slug or "").strip() if payload else ""
    if not client_slug:
        return None
    try:
        client = db.query(Client).filter(Client.name == client_slug).first()
    except Exception:
        return None
    resolved_client_id = getattr(client, "id", None)
    return resolved_client_id if isinstance(resolved_client_id, UUID) else None


def _resolve_client_config_for_domain_routing(
    db: Session,
    *,
    payload: WebhookRequest,
    preflight_payload: dict[str, object] | None,
    client_id: UUID | None,
) -> dict | None:
    if isinstance(preflight_payload, dict):
        client = preflight_payload.get("client")
        client_config = getattr(client, "config", None)
        if isinstance(client_config, dict):
            return client_config

    try:
        client = None
        if isinstance(client_id, UUID):
            client = db.query(Client).filter(Client.id == client_id).first()
        elif payload and isinstance(payload.client_slug, str) and payload.client_slug.strip():
            client = db.query(Client).filter(Client.name == payload.client_slug.strip()).first()
    except Exception:
        return None

    client_config = getattr(client, "config", None)
    return client_config if isinstance(client_config, dict) else None


def _resolve_snapshot_branch_id(
    preflight_payload: dict[str, object] | None,
) -> UUID | None:
    if not isinstance(preflight_payload, dict):
        return None
    resolved_branch_id = preflight_payload.get("resolved_branch_id")
    return resolved_branch_id if isinstance(resolved_branch_id, UUID) else None


def _build_conversation_snapshot(
    conversation: Conversation,
    *,
    message_text: str | None = None,
    client_slug: str | None = None,
) -> ReasoningCoreConversationSnapshot:
    context = conversation.context if isinstance(conversation.context, dict) else {}
    dialog_state_service = DialogStateService()
    now = datetime.now(timezone.utc)
    expected_reply = dialog_state_service.project_expected_reply_projections(
        **{
            _ER_KEY: context.get(_ER_KEY),
            _ERR_KEY: context.get(_ERR_KEY),
        },
    ).model_dump()
    booking_state = context.get("booking")
    booking_state = dict(booking_state) if isinstance(booking_state, dict) else {}
    booking_active = bool(booking_state.get("active"))
    current_goal = context.get("current_goal")
    normalized_goal = current_goal.strip() if isinstance(current_goal, str) and current_goal.strip() else None
    if expected_reply.get(_ER_KEY) is None and isinstance(message_text, str) and message_text.strip():
        session_memory = context.get("session_memory") if isinstance(context.get("session_memory"), dict) else None
        re_entry_required = context.get("re_entry_required")
        if (
            isinstance(session_memory, dict)
            and not dialog_state_service.is_re_entry_required(re_entry_required)
            and not dialog_state_service.is_session_memory_expired(
                session_memory,
                now=now,
                default_ttl_hours=24,
            )
        ):
            memory_active_goal = session_memory.get("active_goal")
            normalized_memory_goal = (
                memory_active_goal.strip()
                if isinstance(memory_active_goal, str) and memory_active_goal.strip()
                else None
            )
            memory_expected_reply = dialog_state_service.project_expected_reply_projections(
                **{
                    _ER_KEY: session_memory.get("last_question_type"),
                    _ERR_KEY: None,
                }
            ).expected_reply_type
            is_short_reply = decision_router._is_short_reply(message_text)
            if (
                not is_short_reply
                and memory_expected_reply == decision_router.EXPECTED_REPLY_TIME
                and decision_router._extract_datetime(message_text, client_slug=client_slug)
            ):
                is_short_reply = True
            if (
                memory_expected_reply
                in {
                    decision_router.EXPECTED_REPLY_SERVICE,
                    decision_router.EXPECTED_REPLY_TIME,
                    decision_router.EXPECTED_REPLY_NAME,
                }
                and is_short_reply
                and not decision_router._looks_like_info_query(
                    message_text,
                    client_slug=client_slug,
                )
                and not decision_router._looks_like_policy_topic(
                    message_text,
                    policy_type=None,
                    policy_pack=None,
                )
                and (
                    not normalized_memory_goal
                    or not normalized_goal
                    or normalized_memory_goal == normalized_goal
                )
            ):
                expected_reply[_ER_KEY] = memory_expected_reply
    pending_booking_boundary = dialog_state_service.derive_pending_booking_resume_boundary_payload(
        context,
        now=now,
    )
    boundary_booking_state = (
        pending_booking_boundary.get("booking_state")
        if isinstance(pending_booking_boundary, dict)
        else None
    )
    if expected_reply.get(_ER_KEY) is None and isinstance(pending_booking_boundary, dict):
        boundary_expected_reply = pending_booking_boundary.get("expected_reply_type")
        if isinstance(boundary_expected_reply, str) and boundary_expected_reply.strip():
            expected_reply[_ER_KEY] = boundary_expected_reply.strip()
            if expected_reply.get(_ERR_KEY) is None:
                pending_resume_reason = dialog_state_service.derive_pending_resume_reason(context)
                if isinstance(pending_resume_reason, str) and pending_resume_reason.strip():
                    expected_reply[_ERR_KEY] = pending_resume_reason.strip()
    if not booking_active and isinstance(boundary_booking_state, dict):
        booking_state = dict(boundary_booking_state)
        booking_active = bool(booking_state.get("active"))
    if normalized_goal is None and isinstance(pending_booking_boundary, dict):
        normalized_goal = "booking"
    booking_datetime_value = _resolve_snapshot_booking_datetime_value(
        {
            **context,
            "booking": booking_state,
        },
        booking_active=booking_active,
    )
    booking_time_token = _resolve_snapshot_booking_time_token(
        booking_datetime_value=booking_datetime_value,
    )
    service_referent = _resolve_snapshot_service_referent(
        {
            **context,
            "booking": booking_state,
        },
        booking_active=booking_active,
    )
    routing = decision_router.ROUTING_MATRIX.get(conversation.state, {})
    return ReasoningCoreConversationSnapshot(
        conversation_id=conversation.id,
        state=conversation.state,
        bot_status=conversation.bot_status,
        branch_id=conversation.branch_id,
        reply_slot=expected_reply.get(_ER_KEY),
        resume_reason=expected_reply.get(_ERR_KEY),
        current_goal=normalized_goal,
        booking_active=booking_active,
        allow_bot_reply=bool(routing.get("allow_bot_reply", False)),
        booking_time_token=booking_time_token,
        booking_datetime_value=booking_datetime_value,
        service_referent=service_referent,
    )


def _resolve_snapshot_booking_datetime_value(
    context: dict[str, object],
    *,
    booking_active: bool,
) -> str | None:
    booking_state = context.get("booking") if isinstance(context, dict) else None
    if not booking_active or not isinstance(booking_state, dict):
        return None
    raw_booking_datetime = booking_state.get("datetime")
    if not isinstance(raw_booking_datetime, str):
        return None
    normalized_booking_datetime = raw_booking_datetime.strip()
    return normalized_booking_datetime or None


def _resolve_snapshot_booking_time_token(
    *,
    booking_datetime_value: str | None,
) -> str | None:
    if not isinstance(booking_datetime_value, str) or not booking_datetime_value.strip():
        return None
    return extract_time_token(booking_datetime_value)


def _restore_turn_planner_snapshot_datetime_if_message_echo(
    *,
    booking_state: dict[str, object],
    booking_datetime_value: str | None,
    message_text: str | None,
) -> dict[str, object]:
    restored_booking_state = dict(booking_state)
    snapshot_datetime_value = (
        booking_datetime_value.strip()
        if isinstance(booking_datetime_value, str) and booking_datetime_value.strip()
        else None
    )
    projected_datetime_value = restored_booking_state.get("datetime")
    if (
        snapshot_datetime_value is None
        or not isinstance(projected_datetime_value, str)
        or not projected_datetime_value.strip()
        or not isinstance(message_text, str)
        or not message_text.strip()
    ):
        return restored_booking_state
    if (
        decision_router.normalize_for_matching(projected_datetime_value)
        == decision_router.normalize_for_matching(message_text)
    ):
        restored_booking_state["datetime"] = snapshot_datetime_value
    return restored_booking_state


def _apply_turn_planner_exact_time_progression_override(
    *,
    booking_state: dict[str, object],
    message_text: str | None,
    client_slug: str | None,
) -> tuple[dict[str, object], dict[str, object] | None]:
    projected_booking_state = dict(booking_state)
    existing_datetime = projected_booking_state.get("datetime")
    if not isinstance(existing_datetime, str) or not existing_datetime.strip():
        return projected_booking_state, None
    normalized_message = message_text.strip() if isinstance(message_text, str) else ""
    if not normalized_message:
        return projected_booking_state, None

    exact_time_token = extract_time_token(normalized_message)
    if exact_time_token is None:
        hour_match = decision_router._match_booking_hour_fallback(normalized_message)
        if isinstance(hour_match, dict):
            raw_hour = hour_match.get("hour")
            raw_minute = hour_match.get("minute")
            try:
                normalized_hour = int(str(raw_hour))
                normalized_minute = int(str(raw_minute or "00"))
            except (TypeError, ValueError):
                normalized_hour = -1
                normalized_minute = -1
            if 0 <= normalized_hour <= 23 and 0 <= normalized_minute <= 59:
                exact_time_token = f"{normalized_hour:02d}:{normalized_minute:02d}"
    if not isinstance(exact_time_token, str) or not exact_time_token.strip():
        return projected_booking_state, None
    normalized_exact_time = exact_time_token.strip()

    normalized_existing_datetime = existing_datetime.strip()
    if decision_router._is_datetime_grounded_for_prompt(
        normalized_existing_datetime,
        client_slug=client_slug,
    ):
        replacement_datetime = None
        if decision_router.TIME_PATTERN.search(normalized_existing_datetime):
            replacement_datetime = decision_router.TIME_PATTERN.sub(
                normalized_exact_time,
                normalized_existing_datetime,
                count=1,
            )
        elif decision_router.TIME_HOUR_PATTERN.search(normalized_existing_datetime):
            replacement_datetime = decision_router.TIME_HOUR_PATTERN.sub(
                normalized_exact_time,
                normalized_existing_datetime,
                count=1,
            )
        else:
            existing_day = decision_router._extract_relative_date_token(
                normalized_existing_datetime,
            )
            if isinstance(existing_day, str) and existing_day.strip():
                replacement_datetime = f"{existing_day.strip()} {normalized_exact_time}".strip()
        if not isinstance(replacement_datetime, str) or not replacement_datetime.strip():
            return projected_booking_state, None
        replacement_datetime = replacement_datetime.strip()
        if replacement_datetime == normalized_existing_datetime:
            return projected_booking_state, None
        projected_booking_state["datetime"] = replacement_datetime
        return projected_booking_state, {
            "expected_reply_time_progression_override": True,
            "expected_reply_time_token": normalized_exact_time,
            "expected_reply_time_progressed_datetime": replacement_datetime,
        }

    projected_context = decision_router._apply_expected_reply_slot(
        {"booking": projected_booking_state},
        **{_EXPECTED_REPLY_TYPE_FIELD: decision_router.EXPECTED_REPLY_TIME},
        value=normalized_exact_time,
    )
    merged_booking_state = projected_context.get("booking")
    if not isinstance(merged_booking_state, dict):
        return projected_booking_state, None

    merged_datetime = merged_booking_state.get("datetime")
    if not isinstance(merged_datetime, str) or not merged_datetime.strip():
        return projected_booking_state, None
    normalized_merged_datetime = merged_datetime.strip()
    if normalized_merged_datetime == existing_datetime.strip():
        return projected_booking_state, None
    if not decision_router._is_datetime_grounded_for_prompt(
        normalized_merged_datetime,
        client_slug=client_slug,
    ):
        return projected_booking_state, None

    return dict(merged_booking_state), {
        "expected_reply_time_progression_override": True,
        "expected_reply_time_token": exact_time_token.strip(),
        "expected_reply_time_progressed_datetime": normalized_merged_datetime,
    }


def _apply_turn_planner_explicit_name_progression_override(
    *,
    booking_state: dict[str, object],
    message_text: str | None,
    client_slug: str | None,
) -> tuple[dict[str, object], dict[str, object] | None]:
    projected_booking_state = dict(booking_state)
    existing_name = projected_booking_state.get("name")
    existing_name_token = (
        existing_name.strip()
        if isinstance(existing_name, str) and existing_name.strip()
        else None
    )
    normalized_message = message_text.strip() if isinstance(message_text, str) else ""
    if not normalized_message:
        return projected_booking_state, None

    progressed_booking_state = decision_router._update_booking_from_messages(
        projected_booking_state,
        [normalized_message],
        client_slug=client_slug,
    )
    candidate_name = progressed_booking_state.get("name")
    if isinstance(candidate_name, str) and candidate_name.strip():
        candidate_name = decision_router._validate_expected_reply_value(
            **{_EXPECTED_REPLY_TYPE_FIELD: decision_router.EXPECTED_REPLY_NAME},
            value=candidate_name,
            client_slug=client_slug,
        )
    else:
        candidate_name = decision_router._validate_expected_reply_value(
            **{_EXPECTED_REPLY_TYPE_FIELD: decision_router.EXPECTED_REPLY_NAME},
            value=normalized_message,
            client_slug=client_slug,
        )
    if not isinstance(candidate_name, str) or not candidate_name.strip():
        return projected_booking_state, None

    normalized_name = candidate_name.strip()
    if (
        existing_name_token
        and decision_router.normalize_for_matching(existing_name_token)
        == decision_router.normalize_for_matching(normalized_name)
    ):
        return projected_booking_state, None

    progressed_booking_state["name"] = normalized_name
    return dict(progressed_booking_state), {
        "expected_reply_name_progression_override": True,
        "expected_reply_name_value": normalized_name,
    }


def _build_exact_time_progression_trace_payload(
    *,
    source: str,
    state: str | None,
    progression_meta: dict[str, object],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "stage": "expected_reply_progression_override",
        "decision": "exact_time_merge",
        "state": state,
        "source": source,
        "time_token": progression_meta["expected_reply_time_token"],
        "booking_datetime": progression_meta["expected_reply_time_progressed_datetime"],
    }
    payload[_EXPECTED_REPLY_TYPE_FIELD] = decision_router.EXPECTED_REPLY_TIME
    return payload


def _build_name_progression_trace_payload(
    *,
    source: str,
    state: str | None,
    progression_meta: dict[str, object],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "stage": "expected_reply_progression_override",
        "decision": "name_merge",
        "state": state,
        "source": source,
        "customer_name": progression_meta["expected_reply_name_value"],
    }
    payload[_EXPECTED_REPLY_TYPE_FIELD] = decision_router.EXPECTED_REPLY_NAME
    return payload


def _resolve_snapshot_service_referent(
    context: dict[str, object],
    *,
    booking_active: bool,
) -> str | None:
    booking_state = context.get("booking") if isinstance(context, dict) else None
    if booking_active and isinstance(booking_state, dict):
        booking_service = booking_state.get("service")
        if isinstance(booking_service, str) and booking_service.strip():
            return booking_service.strip()

    manager = context.get("context_manager") if isinstance(context, dict) else None
    if not isinstance(manager, dict):
        return None

    raw_message_count = manager.get("message_count")
    try:
        message_count = int(raw_message_count)
    except (TypeError, ValueError):
        return None
    if message_count <= 0:
        return None

    canonical_projection = DialogStateService().normalize_context_manager_canonical_state(
        manager.get("canonical_dialog_state")
        if isinstance(manager.get("canonical_dialog_state"), dict)
        else None
    )
    referents = canonical_projection.get("current_referents")
    service_payload = referents.get("service") if isinstance(referents, dict) else None
    if isinstance(service_payload, dict):
        service_value = service_payload.get("value")
        if isinstance(service_value, str) and service_value.strip():
            ttl = service_payload.get("ttl")
            last_count = service_payload.get("message_count")
            try:
                last_count_value = int(last_count)
            except (TypeError, ValueError):
                last_count_value = message_count
            age = max(message_count - last_count_value, 0)
            if not isinstance(ttl, int) or ttl <= 0 or age <= ttl:
                return service_value.strip()

    legacy_payload = manager.get("service_carryover")
    if not isinstance(legacy_payload, dict):
        return None
    projected = DialogStateService().get_service_carryover(
        legacy_payload,
        message_count=message_count,
        default_ttl=SERVICE_CARRYOVER_TTL_MESSAGES,
    )
    if not isinstance(projected, dict):
        return None
    service_query = projected.get("service_query")
    if isinstance(service_query, str) and service_query.strip():
        return service_query.strip()
    return None


def _resolve_active_conversation_snapshot(
    db: Session,
    *,
    payload: WebhookRequest,
    conversation_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    client_id: UUID | None,
) -> ReasoningCoreConversationSnapshot | None:
    try:
        conversation = None
        if conversation_id is not None:
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if not isinstance(conversation, Conversation):
                conversation = None
        if conversation is None and isinstance(client_id, UUID):
            metadata = payload.body.metadata if payload and payload.body else None
            remote_jid = getattr(metadata, "remoteJid", None)
            if remote_jid:
                branch_id = _resolve_snapshot_branch_id(preflight_payload)
                conversation = decision_router.find_active_conversation_by_channel_ref(
                    db,
                    client_id,
                    remote_jid,
                    branch_id=branch_id,
                )
                if not isinstance(conversation, Conversation):
                    conversation = None
                if conversation is None:
                    user = (
                        db.query(User)
                        .filter(User.client_id == client_id, User.remote_jid == remote_jid)
                        .first()
                    )
                    if isinstance(user, User):
                        query = db.query(Conversation).filter(
                            Conversation.client_id == client_id,
                            Conversation.user_id == user.id,
                            Conversation.status == "active",
                        )
                        if branch_id is not None:
                            query = query.filter(Conversation.branch_id == branch_id)
                        conversation = query.order_by(Conversation.started_at.desc()).first()
                        if not isinstance(conversation, Conversation):
                            conversation = None
    except Exception:
        return None
    if not isinstance(conversation, Conversation):
        return None
    body = payload.body if payload and payload.body else None
    return _build_conversation_snapshot(
        conversation,
        message_text=body.message if body is not None else None,
        client_slug=payload.client_slug if payload is not None else None,
    )


def _resolve_turn_planner_owner_client(
    db: Session,
    *,
    payload: WebhookRequest,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
) -> Client | None:
    if isinstance(preflight_payload, dict):
        client = preflight_payload.get("client")
        if isinstance(client, Client):
            return client

    try:
        if isinstance(client_id, UUID):
            client = db.query(Client).filter(Client.id == client_id).first()
            if isinstance(client, Client):
                return client
        client_slug = (payload.client_slug or "").strip() if payload else ""
        if client_slug:
            client = db.query(Client).filter(Client.name == client_slug).first()
            if isinstance(client, Client):
                return client
    except Exception:
        return None
    return None


def _ensure_turn_planner_owner_conversation(
    db: Session,
    *,
    client: Client,
    remote_jid: str,
    branch_id: UUID | None,
    conversation_id: UUID | None,
) -> Conversation | None:
    conversation = None
    try:
        if conversation_id is not None:
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if isinstance(conversation, Conversation):
                return conversation
        conversation = decision_router.find_active_conversation_by_channel_ref(
            db,
            client.id,
            remote_jid,
            branch_id=branch_id,
        )
        if isinstance(conversation, Conversation):
            return conversation
        user = get_or_create_user(db, client.id, remote_jid)
        return get_or_create_conversation(
            db,
            client.id,
            user.id,
            "whatsapp",
            branch_id=branch_id,
        )
    except Exception:
        return None


def _resolve_turn_planner_owner_user(
    db: Session,
    *,
    client: Client,
    conversation: Conversation,
    remote_jid: str,
) -> User | None:
    try:
        if isinstance(conversation.user_id, UUID):
            user = db.query(User).filter(User.id == conversation.user_id).first()
            if isinstance(user, User):
                return user
        return get_or_create_user(db, client.id, remote_jid)
    except Exception:
        return None


def _build_turn_planner_user_message_metadata(
    *,
    payload: WebhookRequest,
) -> dict[str, object]:
    metadata = payload.body.metadata if payload and payload.body else None
    message_metadata = metadata.model_dump(exclude_none=True) if metadata else {}
    message_id = getattr(metadata, "messageId", None)
    if message_id:
        message_metadata["message_id"] = message_id
    message_type = payload.body.messageType if payload and payload.body else None
    if message_type:
        message_metadata["message_type"] = message_type
    if payload and payload.body and payload.body.mediaData:
        message_metadata["has_media"] = True
    tenant_context = getattr(payload, "tenant_context", None)
    if tenant_context is not None:
        tenant_payload = tenant_context.model_dump(exclude_none=True, mode="json")
        if tenant_payload:
            message_metadata["tenant_context"] = tenant_payload
    return message_metadata


def _resolve_turn_planner_transport_reason(
    send_result: object,
    *,
    instance_id: str | None,
) -> str | None:
    if instance_id is None:
        return "missing_instance_id"
    error = getattr(send_result, "error", None)
    code = getattr(error, "code", None)
    if isinstance(code, str) and code.strip():
        return code.strip()
    message = getattr(error, "message", None)
    if isinstance(message, str) and message.strip():
        return message.strip()
    return "send_failed"


def _is_turn_planner_safe_info_fact_candidate(decision: PolicyDecision) -> bool:
    return (
        decision.outcome == "FACT"
        and decision.action == "fact"
        and decision.tool_action == "info"
        and decision.intent in REASONING_CORE_TURN_PLANNER_INFO_INTENTS
    )


def _is_turn_planner_safe_catalog_fact_candidate(decision: PolicyDecision) -> bool:
    if decision.outcome != "FACT" or decision.action != "fact":
        return False
    tool_args = decision.tool_args if isinstance(decision.tool_args, dict) else {}
    service_query = tool_args.get("service_query")
    has_service_query = isinstance(service_query, str) and bool(service_query.strip())
    if decision.intent == "services_overview":
        return decision.tool_action == "catalog.service_query" and not has_service_query
    if decision.tool_action == "catalog.location":
        return decision.intent in {"info", "location"}
    if decision.intent == "location":
        return decision.tool_action == "catalog.location"
    if decision.intent == "portfolio":
        return decision.tool_action == "catalog.portfolio"
    return False


def _resolve_turn_planner_tool_action_service_query(decision: PolicyDecision) -> str | None:
    tool_args = decision.tool_args if isinstance(decision.tool_args, dict) else {}
    service_query = tool_args.get("service_query")
    if not isinstance(service_query, str):
        return None
    cleaned = service_query.strip()
    return cleaned or None


def _turn_planner_pack_ref_set(decision: PolicyDecision) -> set[str]:
    return {
        pack_ref.strip()
        for pack_ref in decision.pack_refs
        if isinstance(pack_ref, str) and pack_ref.strip()
    }


def _reply_meta_token_equals(
    reply_meta: dict[str, object],
    key: str,
    expected: str,
) -> bool:
    value = reply_meta.get(key)
    return isinstance(value, str) and value.strip().casefold() == expected.casefold()


def _reply_meta_has_section(reply_meta: dict[str, object], expected: str) -> bool:
    info_sections = reply_meta.get("info_sections")
    return isinstance(info_sections, list) and any(
        isinstance(section, str) and section.strip().casefold() == expected.casefold()
        for section in info_sections
    )


def _should_accept_turn_planner_catalog_result(
    decision: PolicyDecision,
    *,
    response_text: str | None,
    handled: bool,
    ok: bool,
    error_code: str | None,
    decision_meta: dict[str, object] | None,
) -> bool:
    if not handled or not isinstance(response_text, str) or not response_text.strip():
        return False
    tool_decision = None
    if isinstance(decision_meta, dict):
        raw_decision = decision_meta.get("tool_decision")
        if isinstance(raw_decision, str):
            tool_decision = raw_decision.strip() or None
    if decision.intent == "services_overview":
        return ok and tool_decision == "services_overview"
    if decision.tool_action == "catalog.location":
        return ok and decision.intent in {"info", "location"} and tool_decision == "ok"
    return any(
        (
            decision.intent == "portfolio" and ok and tool_decision == "ok",
            (
                decision.intent == "portfolio"
                and not ok
                and tool_decision == "not_found"
                and error_code == "portfolio_missing"
            ),
        )
    )


def _is_turn_planner_safe_service_query_fact_candidate(decision: PolicyDecision) -> bool:
    if decision.outcome != "FACT" or decision.action != "fact":
        return False
    if decision.tool_action != "catalog.service_query":
        return False
    if _resolve_turn_planner_tool_action_service_query(decision) is None:
        return False
    pack_refs = _turn_planner_pack_ref_set(decision)
    return (
        (decision.intent == "info" and pack_refs == {"pricing"})
        or (decision.intent == "duration" and pack_refs == {"duration"})
    )


def _is_turn_planner_safe_pricing_collect_candidate(decision: PolicyDecision) -> bool:
    if (
        decision.outcome != "COLLECT"
        or decision.action != "collect"
        or decision.intent != "pricing"
        or decision.tool_action != "info"
        or _turn_planner_pack_ref_set(decision) != {"pricing"}
    ):
        return False
    pending_contract = decision.pending_question_contract
    next_question = pending_contract.next_question.strip() if pending_contract.next_question else None
    open_questions = {
        item.strip()
        for item in pending_contract.open_questions
        if isinstance(item, str) and item.strip()
    }
    return next_question == "service" and open_questions == {"service"}


def _is_turn_planner_safe_duration_collect_candidate(decision: PolicyDecision) -> bool:
    if (
        decision.outcome != "COLLECT"
        or decision.action != "collect"
        or decision.intent != "duration"
        or decision.tool_action != "info"
        or _turn_planner_pack_ref_set(decision) != {"duration"}
    ):
        return False
    pending_contract = decision.pending_question_contract
    next_question = pending_contract.next_question.strip() if pending_contract.next_question else None
    open_questions = {
        item.strip()
        for item in pending_contract.open_questions
        if isinstance(item, str) and item.strip()
    }
    return next_question == "service" and open_questions == {"service"}


def _is_turn_planner_safe_bookability_time_collect_candidate(
    decision: PolicyDecision,
) -> bool:
    if (
        decision.outcome != "COLLECT"
        or decision.action != "collect"
        or decision.intent != "booking"
        or decision.tool_action != "calendar.list_slots"
    ):
        return False
    if _resolve_turn_planner_tool_action_service_query(decision) is None:
        return False
    pending_contract = decision.pending_question_contract
    next_question = pending_contract.next_question.strip() if pending_contract.next_question else None
    pending_target = (
        pending_contract.pending_question_target.strip()
        if pending_contract.pending_question_target
        else None
    )
    open_questions = {
        item.strip()
        for item in pending_contract.open_questions
        if isinstance(item, str) and item.strip()
    }
    slots = decision.slots if isinstance(decision.slots, dict) else {}
    service_slot = slots.get("service")
    datetime_slot = slots.get("datetime")
    reason = decision.meta.get("reason") if isinstance(decision.meta, dict) else None
    temporal_scope = decision.meta.get("temporal_scope") if isinstance(decision.meta, dict) else None
    resolution_mode = (
        decision.meta.get("resolution_mode") if isinstance(decision.meta, dict) else None
    )
    subject_kind = decision.meta.get("subject_kind") if isinstance(decision.meta, dict) else None
    return all(
        (
            next_question == "datetime",
            open_questions == {"datetime"},
            pending_target == "time",
            isinstance(service_slot, str) and bool(service_slot.strip()),
            not (isinstance(datetime_slot, str) and datetime_slot.strip()),
            reason == "missing_temporal_scope",
            temporal_scope == "none",
            resolution_mode == "clarify_missing_time",
            subject_kind == "service",
        )
    )


def _is_turn_planner_safe_active_name_time_collect_candidate(
    decision: PolicyDecision,
) -> bool:
    if (
        decision.outcome != "COLLECT"
        or decision.action != "collect"
        or decision.intent != "booking"
        or decision.tool_action != "collect"
    ):
        return False
    pending_contract = decision.pending_question_contract
    next_question = pending_contract.next_question.strip() if pending_contract.next_question else None
    pending_target = (
        pending_contract.pending_question_target.strip()
        if pending_contract.pending_question_target
        else None
    )
    active_relation = (
        pending_contract.active_question_relation.strip()
        if pending_contract.active_question_relation
        else None
    )
    open_questions = {
        item.strip()
        for item in pending_contract.open_questions
        if isinstance(item, str) and item.strip()
    }
    slots = decision.slots if isinstance(decision.slots, dict) else {}
    service_slot = slots.get("service")
    datetime_slot = slots.get("datetime")
    name_slot = slots.get("name")
    reason = decision.meta.get("reason") if isinstance(decision.meta, dict) else None
    pending_act = decision.meta.get("pending_question_act") if isinstance(decision.meta, dict) else None
    if isinstance(pending_act, str):
        pending_act = pending_act.strip() or None
    temporal_scope = decision.meta.get("temporal_scope") if isinstance(decision.meta, dict) else None
    resolution_mode = (
        decision.meta.get("resolution_mode") if isinstance(decision.meta, dict) else None
    )
    subject_kind = decision.meta.get("subject_kind") if isinstance(decision.meta, dict) else None
    return all(
        (
            next_question == "name",
            open_questions == {"name"},
            pending_act == "ask_about_requested_slot",
            pending_target == "time",
            active_relation == "ask_about_requested_slot",
            isinstance(service_slot, str) and bool(service_slot.strip()),
            isinstance(datetime_slot, str) and bool(datetime_slot.strip()),
            not (isinstance(name_slot, str) and name_slot.strip()),
            reason == "booking_time_availability_followup",
            temporal_scope == "specific_time",
            resolution_mode == "referent_followup",
            subject_kind == "booking",
        )
    )


def _is_turn_planner_safe_specialist_name_collect_candidate(
    decision: PolicyDecision,
) -> bool:
    if (
        decision.outcome != "COLLECT"
        or decision.action != "collect"
        or decision.intent != "booking"
        or decision.tool_action != "collect"
    ):
        return False
    pending_contract = decision.pending_question_contract
    next_question = pending_contract.next_question.strip() if pending_contract.next_question else None
    pending_target = (
        pending_contract.pending_question_target.strip()
        if pending_contract.pending_question_target
        else None
    )
    active_relation = (
        pending_contract.active_question_relation.strip()
        if pending_contract.active_question_relation
        else None
    )
    open_questions = {
        item.strip()
        for item in pending_contract.open_questions
        if isinstance(item, str) and item.strip()
    }
    slots = decision.slots if isinstance(decision.slots, dict) else {}
    service_slot = slots.get("service")
    datetime_slot = slots.get("datetime")
    name_slot = slots.get("name")
    reason = decision.meta.get("reason") if isinstance(decision.meta, dict) else None
    pending_act = decision.meta.get("pending_question_act") if isinstance(decision.meta, dict) else None
    if isinstance(pending_act, str):
        pending_act = pending_act.strip() or None
    temporal_scope = decision.meta.get("temporal_scope") if isinstance(decision.meta, dict) else None
    resolution_mode = (
        decision.meta.get("resolution_mode") if isinstance(decision.meta, dict) else None
    )
    subject_kind = decision.meta.get("subject_kind") if isinstance(decision.meta, dict) else None
    return all(
        (
            next_question == "name",
            open_questions == {"name"},
            pending_act == "ask_about_requested_slot",
            pending_target == "specialist",
            active_relation == "specialist_availability_followup",
            isinstance(service_slot, str) and bool(service_slot.strip()),
            isinstance(datetime_slot, str) and bool(datetime_slot.strip()),
            not (isinstance(name_slot, str) and name_slot.strip()),
            reason in {"booking_specialist_availability_followup", "specialist_exact_time_followup"},
            temporal_scope == "specific_time",
            resolution_mode == "referent_followup",
            subject_kind == "specialist",
        )
    )


def _is_turn_planner_safe_specialist_datetime_collect_candidate(
    decision: PolicyDecision,
) -> bool:
    if (
        decision.outcome != "COLLECT"
        or decision.action != "collect"
        or decision.intent != "booking"
        or decision.tool_action != "collect"
    ):
        return False
    pending_contract = decision.pending_question_contract
    next_question = pending_contract.next_question.strip() if pending_contract.next_question else None
    pending_target = (
        pending_contract.pending_question_target.strip()
        if pending_contract.pending_question_target
        else None
    )
    active_relation = (
        pending_contract.active_question_relation.strip()
        if pending_contract.active_question_relation
        else None
    )
    open_questions = {
        item.strip()
        for item in pending_contract.open_questions
        if isinstance(item, str) and item.strip()
    }
    slots = decision.slots if isinstance(decision.slots, dict) else {}
    service_slot = slots.get("service")
    datetime_slot = slots.get("datetime")
    name_slot = slots.get("name")
    reason = decision.meta.get("reason") if isinstance(decision.meta, dict) else None
    pending_act = (
        decision.meta.get("pending_question_act") if isinstance(decision.meta, dict) else None
    )
    if isinstance(pending_act, str):
        pending_act = pending_act.strip() or None
    temporal_scope = (
        decision.meta.get("temporal_scope") if isinstance(decision.meta, dict) else None
    )
    resolution_mode = (
        decision.meta.get("resolution_mode") if isinstance(decision.meta, dict) else None
    )
    subject_kind = decision.meta.get("subject_kind") if isinstance(decision.meta, dict) else None
    base_contract_matches = all(
        (
            next_question == "datetime",
            open_questions == {"datetime"},
            pending_act == "ask_about_requested_slot",
            pending_target == "specialist",
            active_relation == "specialist_availability_followup",
            isinstance(service_slot, str) and bool(service_slot.strip()),
            not (isinstance(name_slot, str) and name_slot.strip()),
            not (isinstance(datetime_slot, str) and datetime_slot.strip()),
            reason == "booking_specialist_availability_followup",
            resolution_mode == "referent_followup",
            subject_kind == "specialist",
            temporal_scope == "date_range",
        )
    )
    return base_contract_matches


def _is_turn_planner_safe_service_choice_specialist_time_collect_candidate(
    decision: PolicyDecision,
) -> bool:
    if (
        decision.outcome != "COLLECT"
        or decision.action != "collect"
        or decision.intent != "info"
        or decision.tool_action != "collect"
    ):
        return False
    pending_contract = decision.pending_question_contract
    next_question = pending_contract.next_question.strip() if pending_contract.next_question else None
    pending_target = (
        pending_contract.pending_question_target.strip()
        if pending_contract.pending_question_target
        else None
    )
    active_relation = (
        pending_contract.active_question_relation.strip()
        if pending_contract.active_question_relation
        else None
    )
    open_questions = {
        item.strip()
        for item in pending_contract.open_questions
        if isinstance(item, str) and item.strip()
    }
    slots = decision.slots if isinstance(decision.slots, dict) else {}
    service_slot = slots.get("service")
    datetime_slot = slots.get("datetime")
    name_slot = slots.get("name")
    reason = decision.meta.get("reason") if isinstance(decision.meta, dict) else None
    pending_act = (
        decision.meta.get("pending_question_act") if isinstance(decision.meta, dict) else None
    )
    if isinstance(pending_act, str):
        pending_act = pending_act.strip() or None
    temporal_scope = (
        decision.meta.get("temporal_scope") if isinstance(decision.meta, dict) else None
    )
    resolution_mode = (
        decision.meta.get("resolution_mode") if isinstance(decision.meta, dict) else None
    )
    subject_kind = decision.meta.get("subject_kind") if isinstance(decision.meta, dict) else None
    capability_refs = {
        item.strip() for item in decision.capability_refs if isinstance(item, str) and item.strip()
    }
    return all(
        (
            next_question == "datetime",
            open_questions == {"datetime"},
            pending_act == "ask_about_requested_slot",
            pending_target == "specialist",
            active_relation == "ask_about_requested_slot",
            isinstance(service_slot, str) and bool(service_slot.strip()),
            not (isinstance(datetime_slot, str) and datetime_slot.strip()),
            not (isinstance(name_slot, str) and name_slot.strip()),
            reason in REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_TIME_COLLECT_REASONS,
            resolution_mode == "clarify_missing_time",
            subject_kind == "specialist",
            temporal_scope in {"specific_time", "weekday", "weekend"},
            capability_refs == {"live_availability"},
        )
    )


def _is_turn_planner_safe_service_choice_specialist_daypart_collect_candidate(
    decision: PolicyDecision,
) -> bool:
    if (
        decision.outcome != "COLLECT"
        or decision.action != "collect"
        or decision.intent != "info"
        or decision.tool_action != "collect"
    ):
        return False
    pending_contract = decision.pending_question_contract
    next_question = pending_contract.next_question.strip() if pending_contract.next_question else None
    pending_target = (
        pending_contract.pending_question_target.strip()
        if pending_contract.pending_question_target
        else None
    )
    active_relation = (
        pending_contract.active_question_relation.strip()
        if pending_contract.active_question_relation
        else None
    )
    open_questions = {
        item.strip()
        for item in pending_contract.open_questions
        if isinstance(item, str) and item.strip()
    }
    slots = decision.slots if isinstance(decision.slots, dict) else {}
    service_slot = slots.get("service")
    datetime_slot = slots.get("datetime")
    name_slot = slots.get("name")
    reason = decision.meta.get("reason") if isinstance(decision.meta, dict) else None
    pending_act = (
        decision.meta.get("pending_question_act") if isinstance(decision.meta, dict) else None
    )
    if isinstance(pending_act, str):
        pending_act = pending_act.strip() or None
    temporal_scope = (
        decision.meta.get("temporal_scope") if isinstance(decision.meta, dict) else None
    )
    resolution_mode = (
        decision.meta.get("resolution_mode") if isinstance(decision.meta, dict) else None
    )
    subject_kind = decision.meta.get("subject_kind") if isinstance(decision.meta, dict) else None
    capability_refs = {
        item.strip() for item in decision.capability_refs if isinstance(item, str) and item.strip()
    }
    return all(
        (
            next_question == "datetime",
            open_questions == {"datetime"},
            pending_act == "ask_about_requested_slot",
            pending_target == "specialist",
            active_relation == "ask_about_requested_slot",
            isinstance(service_slot, str) and bool(service_slot.strip()),
            isinstance(datetime_slot, str) and bool(datetime_slot.strip()),
            not (isinstance(name_slot, str) and name_slot.strip()),
            reason == "daypart_followup",
            resolution_mode == "clarify_missing_time",
            subject_kind == "specialist",
            temporal_scope == "specific_time",
            capability_refs == {"live_availability"},
        )
    )


def _is_turn_planner_safe_master_query_fact_candidate(decision: PolicyDecision) -> bool:
    return (
        decision.outcome == "FACT"
        and decision.action == "fact"
        and decision.intent == "master_query"
        and decision.tool_action == "catalog.service_query"
        and _resolve_turn_planner_tool_action_service_query(decision) is not None
        and _turn_planner_pack_ref_set(decision) == {"master"}
    )


def _is_turn_planner_safe_master_query_collect_candidate(decision: PolicyDecision) -> bool:
    if (
        decision.outcome != "COLLECT"
        or decision.action != "collect"
        or decision.intent != "master_query"
        or decision.tool_action != "collect"
        or _turn_planner_pack_ref_set(decision) != {"master"}
    ):
        return False
    pending_contract = decision.pending_question_contract
    next_question = pending_contract.next_question.strip() if pending_contract.next_question else None
    open_questions = {
        item.strip()
        for item in pending_contract.open_questions
        if isinstance(item, str) and item.strip()
    }
    return next_question == "service" and open_questions == {"service"}


def _is_turn_planner_safe_booking_verification_candidate(
    decision: PolicyDecision,
) -> bool:
    return (
        decision.outcome == "FACT"
        and decision.action == "fact"
        and decision.intent == "check_booking"
        and decision.tool_action == "calendar.get_booking"
    )


def _build_turn_planner_safe_booking_prompt_decision(
    *,
    last_question: str,
    slot_values: dict[str, str],
    reason: str,
) -> PolicyDecision | None:
    normalized_last_question = (
        last_question.strip() if isinstance(last_question, str) and last_question.strip() else None
    )
    if normalized_last_question not in {"service", "datetime", "name"}:
        return None
    payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "collect",
        "reason": reason,
        "goal": "booking",
        "slots": dict(slot_values),
        "next_question": normalized_last_question,
        "open_questions": [normalized_last_question],
        "needs_manager": False,
    }
    try:
        return TurnPlanner().build_from_policy_override(
            payload,
            interaction_owner=REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None


def _build_turn_planner_safe_check_booking_prompt_decision(
    *,
    last_question: str,
    slot_values: dict[str, str],
    reason: str,
) -> PolicyDecision | None:
    normalized_last_question = (
        last_question.strip() if isinstance(last_question, str) and last_question.strip() else None
    )
    if normalized_last_question not in {"service", "datetime", "name"}:
        return None
    payload = {
        "intent": "check_booking",
        "action": "collect",
        "tool_action": "collect",
        "reason": reason,
        "goal": "booking",
        "slots": dict(slot_values),
        "next_question": normalized_last_question,
        "open_questions": [normalized_last_question],
        "needs_manager": False,
    }
    try:
        return TurnPlanner().build_from_policy_override(
            payload,
            interaction_owner=REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None


def _build_turn_planner_safe_booking_completion_decision(
    *,
    tool_action: str,
    tool_args: dict[str, object],
    slot_values: dict[str, str],
    reason: str,
) -> PolicyDecision | None:
    normalized_tool_action = (
        tool_action.strip() if isinstance(tool_action, str) and tool_action.strip() else None
    )
    if normalized_tool_action != "calendar.book_slot":
        return None
    payload = {
        "intent": "booking",
        "action": "fact",
        "tool_action": normalized_tool_action,
        "tool_args": dict(tool_args),
        "reason": reason,
        "goal": "booking",
        "slots": dict(slot_values),
        "needs_manager": False,
    }
    try:
        return TurnPlanner().build_from_policy_override(
            payload,
            interaction_owner=REASONING_CORE_TURN_PLANNER_BOOKING_COMPLETION_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_BOOKING_COMPLETION_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None


def _build_turn_planner_booking_prompt_slot_values(
    booking_state: dict[str, object] | None,
) -> dict[str, str]:
    if not isinstance(booking_state, dict):
        return {}
    normalized: dict[str, str] = {}
    for slot_key in ("service", "datetime", "name", "phone"):
        value = booking_state.get(slot_key)
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if cleaned:
            normalized[slot_key] = cleaned
    return normalized


def _resolve_turn_planner_booking_prompt_text(reply_slot: str | None) -> str | None:
    if reply_slot == decision_router.EXPECTED_REPLY_SERVICE:
        return decision_router.MSG_BOOKING_ASK_SERVICE
    if reply_slot == decision_router.EXPECTED_REPLY_TIME:
        return decision_router.MSG_BOOKING_ASK_DATETIME
    if reply_slot == decision_router.EXPECTED_REPLY_NAME:
        return decision_router.MSG_BOOKING_ASK_NAME
    if reply_slot == decision_router.EXPECTED_REPLY_PHONE:
        return decision_router.MSG_BOOKING_ASK_PHONE
    return None


def _resolve_turn_planner_safe_llm_specialist_followup_candidate(
    *,
    payload: WebhookRequest,
    message_text: str | None,
    reply_slot: str | None,
    current_goal: str | None,
    booking_state: dict[str, object] | None,
    context: dict[str, object],
    now: datetime,
) -> dict[str, object] | None:
    if reply_slot not in {
        decision_router.EXPECTED_REPLY_TIME,
        decision_router.EXPECTED_REPLY_NAME,
    }:
        return None
    if not isinstance(message_text, str) or not message_text.strip():
        return None

    def _normalize_token(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned.casefold() if cleaned else None

    context_manager = decision_router._get_context_manager(context)
    semantic_booking_state = dict(booking_state) if isinstance(booking_state, dict) else {}
    clear_service_hint = False
    if not semantic_booking_state.get("service"):
        service_hint = decision_router._get_recent_service_hint(context, now)
        if isinstance(service_hint, str) and service_hint.strip():
            semantic_booking_state["service"] = service_hint.strip()
            clear_service_hint = True
        elif isinstance(context_manager, dict):
            raw_message_count = context_manager.get("message_count")
            try:
                message_count = max(int(raw_message_count), 0)
            except (TypeError, ValueError):
                message_count = 0
            carryover = decision_router._get_service_carryover(
                context_manager,
                message_count=message_count,
            )
            if isinstance(carryover, dict):
                service_query = carryover.get("service_query")
                if isinstance(service_query, str) and service_query.strip():
                    semantic_booking_state["service"] = service_query.strip()

    policy_slot_state = _build_turn_planner_booking_prompt_slot_values(semantic_booking_state)
    policy_memory_summary = None
    compact_summary = (
        context_manager.get("compact_summary") if isinstance(context_manager, dict) else None
    )
    if isinstance(compact_summary, dict):
        summary_text = compact_summary.get("text")
        if isinstance(summary_text, str) and summary_text.strip():
            policy_memory_summary = summary_text.strip()

    policy_memory_profile = None
    active_slots = decision_router._collect_policy_active_slots(
        primary_slot_state=policy_slot_state,
        fallback_slot_state=None,
        client_slug=payload.client_slug,
    )
    if active_slots:
        policy_memory_profile = {"active_slots": active_slots, _ER_KEY: reply_slot}

    consult_refs, _ = decision_router._collect_plan_consult_refs(payload.client_slug)
    policy_result = route_llm_policy_core(
        message_text,
        **{
            _ER_KEY: reply_slot,
            "current_goal": current_goal,
            "slot_state": policy_slot_state,
            "info_refs": sorted(decision_router.INFO_INTENTS),
            "consult_refs": consult_refs,
            "memory_summary": policy_memory_summary,
            "memory_profile": policy_memory_profile,
            "client_slug": payload.client_slug,
        },
    )
    policy_payload = policy_result.get("payload") if isinstance(policy_result, dict) else None
    if not (
        isinstance(policy_result, dict)
        and policy_result.get("ok")
        and isinstance(policy_payload, dict)
    ):
        return None

    policy_action = _normalize_token(policy_payload.get("action"))
    policy_tool_action = _normalize_token(policy_payload.get("tool_action"))
    policy_intent = _normalize_token(policy_payload.get("intent"))
    policy_goal = _normalize_token(policy_payload.get("goal"))
    if (
        policy_action != "collect"
        or policy_tool_action != "collect"
        or policy_intent != "booking"
        or policy_goal not in {None, "booking"}
        or policy_payload.get("needs_manager") is True
    ):
        return None
    if decision_router._normalize_plan_refs(policy_payload.get("pack_refs")):
        return None
    if decision_router._normalize_plan_refs(policy_payload.get("risk_signals")):
        return None

    raw_tool_args = policy_payload.get("tool_args")
    if raw_tool_args is not None and not isinstance(raw_tool_args, dict):
        return None
    policy_tool_args = dict(raw_tool_args) if isinstance(raw_tool_args, dict) else {}
    decision_router._normalize_specialist_tool_args(policy_tool_args)
    unsupported_tool_args = {
        key
        for key in policy_tool_args
        if key not in {"specialist_name", "specialist_id"}
    }
    if unsupported_tool_args:
        return None

    raw_entity_refs = policy_payload.get("entity_refs")
    if raw_entity_refs is not None and not isinstance(raw_entity_refs, (list, tuple)):
        return None
    specialist_name, specialist_id = decision_router._extract_semantic_specialist_preference(
        tool_args=policy_tool_args,
        entity_refs=raw_entity_refs,
    )
    if not (specialist_name or specialist_id):
        return None

    pending_target = _normalize_token(policy_payload.get("pending_question_target"))
    subject_kind = _normalize_token(policy_payload.get("subject_kind"))
    capability = _normalize_token(policy_payload.get("capability"))
    resolution_mode = _normalize_token(policy_payload.get("resolution_mode"))
    active_relation = _normalize_token(policy_payload.get("active_question_relation"))
    pending_act = _normalize_token(policy_payload.get("pending_question_act"))
    temporal_scope = _normalize_token(policy_payload.get("temporal_scope"))

    normalized_slot_state = decision_router._normalize_plan_slot_state(policy_payload.get("slots"))
    validated_slot_values: dict[str, str] = {}
    for slot_key, value in normalized_slot_state.items():
        validated_value = decision_router._validate_plan_slot_value(
            slot_key,
            value,
            client_slug=payload.client_slug,
        )
        if validated_value:
            validated_slot_values[slot_key] = validated_value

    collect_slot = _normalize_token(policy_payload.get("next_question"))
    open_questions = [
        item
        for item in decision_router._normalize_plan_questions(policy_payload.get("open_questions"))
        if item in decision_router.BOOKING_SLOT_ORDER
    ]
    if collect_slot not in decision_router.BOOKING_SLOT_ORDER:
        collect_slot = decision_router._select_plan_collect_slot(
            open_questions=open_questions,
            pack_refs=[],
            tool_action=policy_tool_action,
            goal=policy_goal,
        )
    if collect_slot not in {"datetime", "name"}:
        return None
    if set(open_questions) != {collect_slot}:
        return None

    if decision_router._should_preserve_specialist_availability_followup_owner(
        policy_goal=policy_goal,
        policy_collect_slot=collect_slot,
        policy_pending_question_target=pending_target,
        policy_subject_kind=subject_kind,
        policy_capability=capability,
        policy_temporal_scope=temporal_scope,
        policy_active_question_relation=active_relation,
    ):
        return None
    if decision_router._should_preserve_service_choice_specialist_availability_followup_owner(
        policy_goal=policy_goal,
        policy_collect_slot=collect_slot,
        policy_resolution_mode=resolution_mode,
        policy_pending_question_act=pending_act,
        policy_pending_question_target=pending_target,
        policy_subject_kind=subject_kind,
        policy_capability=capability,
        policy_temporal_scope=temporal_scope,
        policy_active_question_relation=active_relation,
        **{_ER_KEY: reply_slot},
    ):
        return None
    if decision_router._should_preserve_active_name_time_availability_followup_owner(
        policy_goal=policy_goal,
        policy_collect_slot=collect_slot,
        policy_resolution_mode=resolution_mode,
        policy_pending_question_act=pending_act,
        policy_pending_question_target=pending_target,
        policy_subject_kind=subject_kind,
        policy_capability=capability,
        policy_temporal_scope=temporal_scope,
        policy_active_question_relation=active_relation,
        **{_ER_KEY: reply_slot},
    ):
        return None
    if not decision_router._should_preserve_specialist_followup_owner(
        policy_goal=policy_goal,
        policy_collect_slot=collect_slot,
        policy_pending_question_target=pending_target,
        policy_subject_kind=subject_kind,
        policy_capability=capability,
        policy_resolution_mode=resolution_mode,
        policy_active_question_relation=active_relation,
        specialist_name=specialist_name,
        specialist_id=specialist_id,
        **{_ER_KEY: reply_slot},
    ):
        return None

    earliest_missing_before = decision_router._first_missing_booking_slot(
        semantic_booking_state,
        client_slug=payload.client_slug,
    )
    merged_slot_state = decision_router._merge_booking_plan_slots(
        booking_state=semantic_booking_state,
        plan_slots=validated_slot_values,
    )
    if decision_router._plan_has_complete_booking_slots(
        merged_slot_state,
        client_slug=payload.client_slug,
    ):
        return None
    earliest_missing_after = decision_router._first_missing_booking_slot(
        merged_slot_state,
        client_slug=payload.client_slug,
    )
    if collect_slot != earliest_missing_before or collect_slot != earliest_missing_after:
        return None

    return {
        "collect_slot": collect_slot,
        "reason": _normalize_token(policy_payload.get("reason")) or "booking_prompt",
        "slot_values": validated_slot_values,
        "merged_slot_values": _build_turn_planner_booking_prompt_slot_values(merged_slot_state),
        "specialist_name": specialist_name,
        "specialist_id": specialist_id,
        "active_question_relation": active_relation or "referent_followup",
        "pending_question_act": pending_act,
        "clear_service_hint": clear_service_hint,
    }

def _should_accept_turn_planner_pricing_collect_result(
    *,
    response_text: str | None,
    reply_meta: dict[str, object] | None,
) -> bool:
    if not isinstance(response_text, str) or not response_text.strip():
        return False
    if not isinstance(reply_meta, dict):
        return False

    action_class = reply_meta.get("action_class")
    intent_class = reply_meta.get("intent_class")
    fact_source = reply_meta.get("fact_source")
    question_type = reply_meta.get("question_type")
    service_query = reply_meta.get("service_query")
    fact_refs = reply_meta.get("fact_refs")
    return all(
        (
            isinstance(action_class, str) and action_class.strip().casefold() == "collect",
            isinstance(intent_class, str) and intent_class.strip().casefold() == "service_clarify",
            isinstance(fact_source, str) and fact_source.strip().casefold() == "truth",
            isinstance(question_type, str) and question_type.strip().casefold() == "pricing",
            not (isinstance(service_query, str) and service_query.strip()),
            isinstance(fact_refs, list)
            and any(
                isinstance(fact_ref, str) and fact_ref.strip().casefold() == "service_clarify"
                for fact_ref in fact_refs
            ),
        )
    )


def _should_accept_turn_planner_duration_collect_result(
    *,
    response_text: str | None,
    reply_action: str | None,
    reply_meta: dict[str, object] | None,
) -> bool:
    if not isinstance(response_text, str) or not response_text.strip():
        return False
    if reply_action != "reply" or not isinstance(reply_meta, dict):
        return False

    question_type = reply_meta.get("question_type")
    service_query = reply_meta.get("service_query")
    fact_source = reply_meta.get("fact_source")
    action_class = reply_meta.get("action_class")
    intent_class = reply_meta.get("intent_class")
    fact_refs = reply_meta.get("fact_refs")
    info_sections = reply_meta.get("info_sections")
    return all(
        (
            isinstance(question_type, str) and question_type.strip().casefold() == "duration",
            not (isinstance(service_query, str) and service_query.strip()),
            isinstance(fact_source, str) and fact_source.strip().casefold() == "truth",
            isinstance(action_class, str) and action_class.strip().casefold() == "fact",
            isinstance(intent_class, str)
            and intent_class.strip().casefold() in {"service_duration", "duration"},
            isinstance(fact_refs, list)
            and any(
                isinstance(fact_ref, str)
                and fact_ref.strip().casefold() in {"duration", "service_duration"}
                for fact_ref in fact_refs
            ),
            isinstance(info_sections, list)
            and any(
                isinstance(section, str) and section.strip().casefold() == "duration"
                for section in info_sections
            ),
        )
    )


def _should_accept_turn_planner_master_query_result(
    *,
    response_text: str | None,
    reply_action: str | None,
    reply_meta: dict[str, object] | None,
) -> bool:
    if not isinstance(response_text, str) or not response_text.strip():
        return False
    if reply_action != "reply" or not isinstance(reply_meta, dict):
        return False
    service_query = reply_meta.get("service_query")
    action_class = reply_meta.get("action_class")
    return all(
        (
            reply_meta.get("master_query_contract") == "masters_catalog.v1",
            _reply_meta_token_equals(reply_meta, "master_reply_mode", "service_match"),
            isinstance(service_query, str) and bool(service_query.strip()),
            not isinstance(action_class, str)
            or action_class.strip().casefold() == "fact",
            _reply_meta_has_section(reply_meta, "master"),
        )
    )


def _should_accept_turn_planner_master_query_collect_result(
    *,
    response_text: str | None,
    reply_action: str | None,
    reply_meta: dict[str, object] | None,
) -> bool:
    if not isinstance(response_text, str) or not response_text.strip():
        return False
    if reply_action != "collect" or not isinstance(reply_meta, dict):
        return False
    service_query = reply_meta.get("service_query")
    action_class = reply_meta.get("action_class")
    return all(
        (
            reply_meta.get("master_query_contract") == "masters_catalog.v1",
            _reply_meta_token_equals(reply_meta, "master_reply_mode", "service_clarify"),
            _reply_meta_token_equals(reply_meta, "clarify_reason", "missing_service_query"),
            not (isinstance(service_query, str) and service_query.strip()),
            not isinstance(action_class, str)
            or action_class.strip().casefold() == "collect",
            _reply_meta_has_section(reply_meta, "master"),
        )
    )


def _should_accept_turn_planner_master_query_service_not_found_collect_result(
    *,
    response_text: str | None,
    reply_action: str | None,
    reply_meta: dict[str, object] | None,
) -> bool:
    if not isinstance(response_text, str) or not response_text.strip():
        return False
    if reply_action != "collect" or not isinstance(reply_meta, dict):
        return False
    service_query = reply_meta.get("service_query")
    action_class = reply_meta.get("action_class")
    return all(
        (
            reply_meta.get("master_query_contract") == "masters_catalog.v1",
            _reply_meta_token_equals(reply_meta, "master_reply_mode", "service_not_found"),
            _reply_meta_token_equals(reply_meta, "clarify_reason", "master_service_not_found"),
            isinstance(service_query, str) and bool(service_query.strip()),
            not isinstance(action_class, str)
            or action_class.strip().casefold() == "collect",
            _reply_meta_has_section(reply_meta, "master"),
        )
    )


def _should_accept_turn_planner_booking_verification_result(
    *,
    response_text: str | None,
    handled: bool,
    ok: bool,
    error_code: str | None,
    decision_meta: dict[str, object] | None,
) -> bool:
    if not handled or not isinstance(response_text, str) or not response_text.strip():
        return False
    if not isinstance(decision_meta, dict):
        return False
    tool_action = decision_meta.get("tool_action")
    tool_decision = decision_meta.get("tool_decision")
    appointment_id = decision_meta.get("appointment_id")
    if tool_action != "calendar.get_booking":
        return False
    if (
        tool_decision == "ok"
        and ok
        and isinstance(appointment_id, str)
        and bool(appointment_id.strip())
    ):
        return True
    return all(
        (
            tool_decision == "not_found",
            not ok,
            error_code == "appointment_not_found",
        )
    )




def _filter_specialist_followup_helper_meta(
    specialist_meta: dict[str, object] | None,
) -> dict[str, object]:
    if not isinstance(specialist_meta, dict):
        return {}
    return {
        key: specialist_meta.get(key)
        for key in (
            "info_sections",
            "fact_intents",
            "master_query_contract",
            "master_reply_mode",
            "master_profiles",
            "master_profiles_count",
            "service_query",
        )
        if specialist_meta.get(key) not in (None, [], {})
    }




def _finalize_tool_reply_owner_execution(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    conversation: Conversation,
    saved_message: Message | None,
    owner_execution: ToolReplyOwnerExecution,
    reply_text: str,
    reply_intent: str | None,
    reply_source: str,
    owner_cutover: str,
    tool_decision: str | None,
    expected_reply_type: str | None,
    expected_reply_reason: str | None,
    maybe_apply_fact_guard: Callable[..., WebhookResponse | None],
    guard_decision_meta: dict[str, object] | None,
    allow_handover: bool,
    send_and_save: Callable[[str], tuple[str, bool]],
    transport_status_token: str | None,
    transport_reason_token: str | None,
    success_label: str = "LLM policy core tool response",
) -> WebhookResponse | None:
    guard_response = maybe_apply_fact_guard(
        decision_meta=guard_decision_meta,
        intent=reply_intent,
        source=reply_source,
        allow_handover=allow_handover,
    )
    followup_kwargs: dict[str, str | None] = {}
    for key, value in zip(
        ("followup_" + "type", "question_" + "reason"),
        (expected_reply_type, expected_reply_reason),
    ):
        followup_kwargs[key] = value
    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=None,
        conversation_id=conversation.id,
        decision=owner_execution.decision,
        reply_text=reply_text,
        reply_meta=None,
        trace_meta=None,
        owner_cutover=owner_cutover,
        stage="llm_policy_core_tool",
        success_label=success_label,
        tool_decision=tool_decision,
        outcome_action="reply",
        outcome_source=reply_source,
        artifact=owner_execution.payload.artifact,
        existing_conversation=conversation,
        existing_saved_message=saved_message,
        send_and_save=send_and_save,
        transport_status_token=transport_status_token,
        transport_reason_token=transport_reason_token,
        trace_payload_override=owner_execution.payload.trace_payload_override,
        guard_response=guard_response,
        extra_trace_payloads=owner_execution.payload.extra_trace_payloads,
        extra_meta_updates=owner_execution.payload.extra_meta_updates,
        **followup_kwargs,
    )


def _should_defer_turn_planner_active_booking_side_owner(
    *,
    conversation_snapshot: ReasoningCoreConversationSnapshot | None,
    decision: PolicyDecision,
) -> bool:
    if conversation_snapshot is None or not conversation_snapshot.booking_active:
        return False
    if conversation_snapshot.reply_slot not in {
        decision_router.EXPECTED_REPLY_SERVICE,
        decision_router.EXPECTED_REPLY_TIME,
    }:
        return False

    pack_refs = _turn_planner_pack_ref_set(decision)
    if decision.tool_action == "catalog.service_query":
        return bool(
            decision.intent == "services_overview"
            or (decision.intent == "info" and pack_refs == {"pricing"})
            or (decision.intent == "duration" and pack_refs == {"duration"})
        )
    if decision.tool_action == "info":
        return bool(
            (decision.intent == "pricing" and pack_refs == {"pricing"})
            or (decision.intent == "duration" and pack_refs == {"duration"})
        )
    return False


async def _try_handle_turn_planner_safe_pricing_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    conversation_snapshot: ReasoningCoreConversationSnapshot | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_PRICING_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_PRICING_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_pricing_collect_candidate(decision):
        return None
    if _should_defer_turn_planner_active_booking_side_owner(
        conversation_snapshot=conversation_snapshot,
        decision=decision,
    ):
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    reply_text, reply_meta = info_router._build_info_intent_reply(
        decision.intent,
        service_query=None,
        client_slug=payload.client_slug,
        message_text=message_text,
        include_info_bundle=True,
    )
    if isinstance(reply_meta, dict):
        reply_meta = dict(reply_meta)
        reply_meta.setdefault("tool_action", decision.tool_action)
    if not _should_accept_turn_planner_pricing_collect_result(
        response_text=reply_text,
        reply_meta=reply_meta,
    ):
        return None

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=None,
        owner_cutover=REASONING_CORE_TURN_PLANNER_PRICING_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_PRICING_COLLECT_STAGE,
        success_label="Turn planner safe pricing collect",
        tool_decision="service_clarify",
        followup_type="service_choice",
        question_reason="service_clarify",
    )


async def _try_handle_turn_planner_safe_duration_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    conversation_snapshot: ReasoningCoreConversationSnapshot | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_DURATION_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_DURATION_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_duration_collect_candidate(decision):
        return None
    if _should_defer_turn_planner_active_booking_side_owner(
        conversation_snapshot=conversation_snapshot,
        decision=decision,
    ):
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    if not isinstance(message_text, str) or not message_text.strip():
        return None

    reply_decision = info_router.get_pack_decision(
        message_text,
        client_slug=payload.client_slug,
    )
    if reply_decision is None or not isinstance(reply_decision.response, str):
        return None

    reply_meta = dict(reply_decision.meta) if isinstance(reply_decision.meta, dict) else None
    if isinstance(reply_meta, dict):
        reply_meta.setdefault("tool_action", decision.tool_action)
    if not _should_accept_turn_planner_duration_collect_result(
        response_text=reply_decision.response,
        reply_action=getattr(reply_decision, "action", None),
        reply_meta=reply_meta,
    ):
        return None

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_decision.response.strip(),
        reply_meta=reply_meta,
        trace_meta=None,
        owner_cutover=REASONING_CORE_TURN_PLANNER_DURATION_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_DURATION_COLLECT_STAGE,
        success_label="Turn planner safe duration collect",
        tool_decision="service_clarify",
        followup_type="service_choice",
        question_reason="service_clarify",
    )


async def _try_handle_turn_planner_safe_bookability_time_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_BOOKABILITY_TIME_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_BOOKABILITY_TIME_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_bookability_time_collect_candidate(decision):
        return None

    slots = decision.slots if isinstance(decision.slots, dict) else {}
    service_query = slots.get("service")
    normalized_service_query = (
        service_query.strip()
        if isinstance(service_query, str) and service_query.strip()
        else None
    )

    reply_text = decision_router.MSG_BOOKING_PENDING_QUESTION_TIME_GUIDANCE
    if not isinstance(reply_text, str) or not reply_text.strip():
        return None

    pending_question_act = (
        decision.meta.get("pending_question_act") if isinstance(decision.meta, dict) else None
    )
    if isinstance(pending_question_act, str):
        pending_question_act = pending_question_act.strip() or None
    pending_question_target = (
        decision.pending_question_contract.pending_question_target
        if decision.pending_question_contract.pending_question_target
        else None
    )
    reply_meta: dict[str, object] = {
        "source": "booking_slot_guidance",
        "tool_action": decision.tool_action,
    }
    trace_meta: dict[str, object] = {
        "validation_error": "semantic_temporal_scope_missing",
        "policy_core_guard_recovery": "semantic_temporal_scope_missing_slot_guidance",
    }
    if isinstance(pending_question_act, str) and pending_question_act.strip():
        normalized_act = pending_question_act.strip()
        reply_meta["pending_question_act"] = normalized_act
        trace_meta["pending_question_act"] = normalized_act
    if isinstance(pending_question_target, str) and pending_question_target.strip():
        normalized_target = pending_question_target.strip()
        reply_meta["pending_question_target"] = normalized_target
        trace_meta["pending_question_target"] = normalized_target

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_BOOKABILITY_TIME_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_BOOKABILITY_TIME_COLLECT_STAGE,
        success_label="Turn planner safe bookability time collect",
        followup_type="time",
        question_reason="booking_slot_guidance",
        grounded_referents={"service": normalized_service_query}
        if normalized_service_query
        else None,
        booking_slot_values={"service": normalized_service_query}
        if normalized_service_query
        else None,
        booking_last_question="datetime",
    )


async def _try_handle_turn_planner_safe_active_name_time_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    conversation_snapshot: ReasoningCoreConversationSnapshot | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_ACTIVE_NAME_TIME_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_ACTIVE_NAME_TIME_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_active_name_time_collect_candidate(decision):
        return None

    slots = decision.slots if isinstance(decision.slots, dict) else {}
    current_datetime = (
        conversation_snapshot.booking_datetime_value
        if conversation_snapshot is not None
        else None
    )
    normalized_current_datetime = (
        current_datetime.strip()
        if isinstance(current_datetime, str) and current_datetime.strip()
        else None
    )
    alternate_datetime = slots.get("datetime")
    normalized_alternate_datetime = (
        alternate_datetime.strip()
        if isinstance(alternate_datetime, str) and alternate_datetime.strip()
        else None
    )
    reply_text = decision_router._build_active_name_time_availability_followup_response(
        current_slot=normalized_current_datetime,
        alternate_slot=normalized_alternate_datetime,
    )
    if not isinstance(reply_text, str) or not reply_text.strip():
        return None

    pending_contract = decision.pending_question_contract
    pending_question_act = (
        decision.meta.get("pending_question_act") if isinstance(decision.meta, dict) else None
    )
    pending_question_target = (
        pending_contract.pending_question_target.strip()
        if pending_contract.pending_question_target
        else None
    )
    active_question_relation = (
        pending_contract.active_question_relation.strip()
        if pending_contract.active_question_relation
        else None
    )
    reply_meta: dict[str, object] = {
        "source": "booking_time_availability_followup",
        "tool_action": decision.tool_action,
        "pending_question_owner": "booking_time_availability_followup",
    }
    trace_meta: dict[str, object] = {
        "pending_question_owner": "booking_time_availability_followup",
    }
    if pending_question_act:
        reply_meta["pending_question_act"] = pending_question_act
        trace_meta["pending_question_act"] = pending_question_act
    if pending_question_target:
        reply_meta["pending_question_target"] = pending_question_target
        trace_meta["pending_question_target"] = pending_question_target
    if active_question_relation:
        reply_meta["pending_question_interaction"] = active_question_relation
        reply_meta["active_question_relation"] = active_question_relation
        trace_meta["active_question_relation"] = active_question_relation
    if normalized_current_datetime:
        reply_meta["current_datetime"] = normalized_current_datetime
        trace_meta["current_datetime"] = normalized_current_datetime
    if normalized_alternate_datetime:
        reply_meta["alternate_datetime"] = normalized_alternate_datetime
        trace_meta["alternate_datetime"] = normalized_alternate_datetime

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_ACTIVE_NAME_TIME_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_ACTIVE_NAME_TIME_COLLECT_STAGE,
        success_label="Turn planner safe active-name time collect",
        followup_type="name",
        question_reason="booking_time_availability_followup",
        grounded_referents={"service": conversation_snapshot.service_referent}
        if conversation_snapshot is not None
        and isinstance(conversation_snapshot.service_referent, str)
        and conversation_snapshot.service_referent.strip()
        else None,
        booking_slot_values={
            key: value
            for key, value in {
                "service": (
                    conversation_snapshot.service_referent
                    if conversation_snapshot is not None
                    else None
                ),
                "datetime": normalized_current_datetime,
            }.items()
            if isinstance(value, str) and value.strip()
        },
        booking_last_question="name",
    )


async def _try_handle_turn_planner_safe_specialist_name_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_SPECIALIST_NAME_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_SPECIALIST_NAME_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_specialist_name_collect_candidate(decision):
        return None

    slots = decision.slots if isinstance(decision.slots, dict) else {}
    service_query = slots.get("service")
    normalized_service_query = (
        service_query.strip()
        if isinstance(service_query, str) and service_query.strip()
        else None
    )
    if normalized_service_query is None:
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    reply_text, specialist_meta = decision_router._build_specialist_availability_followup_response(
        service_query=normalized_service_query,
        client_slug=payload.client_slug,
        message_text=message_text,
        requested_slot="name",
    )
    if not isinstance(reply_text, str) or not reply_text.strip():
        return None

    pending_contract = decision.pending_question_contract
    pending_question_act = (
        decision.meta.get("pending_question_act") if isinstance(decision.meta, dict) else None
    )
    if isinstance(pending_question_act, str):
        pending_question_act = pending_question_act.strip() or None
    pending_question_target = (
        pending_contract.pending_question_target.strip()
        if pending_contract.pending_question_target
        else None
    )
    active_question_relation = (
        pending_contract.active_question_relation.strip()
        if pending_contract.active_question_relation
        else None
    )
    temporal_scope = (
        decision.meta.get("temporal_scope") if isinstance(decision.meta, dict) else None
    )

    reply_meta: dict[str, object] = {
        "source": "booking_specialist_availability_followup",
        "tool_action": decision.tool_action,
        "pending_question_owner": "booking_specialist_availability_followup",
    }
    trace_meta: dict[str, object] = {
        "pending_question_owner": "booking_specialist_availability_followup",
    }
    if pending_question_act:
        reply_meta["pending_question_act"] = pending_question_act
        trace_meta["pending_question_act"] = pending_question_act
    if pending_question_target:
        reply_meta["pending_question_target"] = pending_question_target
        trace_meta["pending_question_target"] = pending_question_target
    if active_question_relation:
        reply_meta["pending_question_interaction"] = active_question_relation
        reply_meta["active_question_relation"] = active_question_relation
        trace_meta["active_question_relation"] = active_question_relation
    if isinstance(temporal_scope, str) and temporal_scope.strip():
        normalized_temporal_scope = temporal_scope.strip()
        reply_meta["temporal_scope"] = normalized_temporal_scope
        trace_meta["temporal_scope"] = normalized_temporal_scope
    filtered_meta = _filter_specialist_followup_helper_meta(specialist_meta)
    if filtered_meta:
        reply_meta.update(filtered_meta)
        trace_meta.update(filtered_meta)

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_SPECIALIST_NAME_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_SPECIALIST_NAME_COLLECT_STAGE,
        success_label="Turn planner safe specialist name collect",
        followup_type="name",
        question_reason="booking_specialist_availability_followup",
        grounded_referents={"service": normalized_service_query},
        booking_slot_values={
            key: value
            for key, value in {
                "service": normalized_service_query,
                "datetime": slots.get("datetime"),
            }.items()
            if isinstance(value, str) and value.strip()
        },
        booking_last_question="name",
    )


async def _try_handle_turn_planner_safe_specialist_datetime_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_SPECIALIST_DATETIME_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_SPECIALIST_DATETIME_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_specialist_datetime_collect_candidate(decision):
        return None

    slots = decision.slots if isinstance(decision.slots, dict) else {}
    service_query = slots.get("service")
    normalized_service_query = (
        service_query.strip()
        if isinstance(service_query, str) and service_query.strip()
        else None
    )
    if normalized_service_query is None:
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    reply_text, specialist_meta = decision_router._build_specialist_availability_followup_response(
        service_query=normalized_service_query,
        client_slug=payload.client_slug,
        message_text=message_text,
        requested_slot="time",
    )
    if not isinstance(reply_text, str) or not reply_text.strip():
        return None

    pending_question_act = (
        decision.meta.get("pending_question_act") if isinstance(decision.meta, dict) else None
    )
    if isinstance(pending_question_act, str):
        pending_question_act = pending_question_act.strip() or None
    temporal_scope = (
        decision.meta.get("temporal_scope") if isinstance(decision.meta, dict) else None
    )

    reply_meta: dict[str, object] = {
        "source": "booking_specialist_availability_followup",
        "tool_action": decision.tool_action,
        "pending_question_owner": "booking_specialist_availability_followup",
    }
    trace_meta: dict[str, object] = {
        "pending_question_owner": "booking_specialist_availability_followup",
    }
    if pending_question_act:
        reply_meta["pending_question_act"] = pending_question_act
        trace_meta["pending_question_act"] = pending_question_act
    reply_meta["pending_question_target"] = "specialist"
    trace_meta["pending_question_target"] = "specialist"
    reply_meta["pending_question_interaction"] = "specialist_availability_followup"
    reply_meta["active_question_relation"] = "specialist_availability_followup"
    trace_meta["active_question_relation"] = "specialist_availability_followup"
    if isinstance(temporal_scope, str) and temporal_scope.strip():
        normalized_temporal_scope = temporal_scope.strip()
        reply_meta["temporal_scope"] = normalized_temporal_scope
        trace_meta["temporal_scope"] = normalized_temporal_scope

    filtered_meta = _filter_specialist_followup_helper_meta(specialist_meta)
    if filtered_meta:
        reply_meta.update(filtered_meta)
        trace_meta.update(filtered_meta)

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_SPECIALIST_DATETIME_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_SPECIALIST_DATETIME_COLLECT_STAGE,
        success_label="Turn planner safe specialist datetime collect",
        followup_type="time",
        question_reason="booking_specialist_availability_followup",
        grounded_referents={"service": normalized_service_query},
        booking_slot_values={"service": normalized_service_query},
        booking_last_question="datetime",
    )


async def _try_handle_turn_planner_safe_service_choice_specialist_time_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_TIME_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_TIME_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_service_choice_specialist_time_collect_candidate(decision):
        return None

    slots = decision.slots if isinstance(decision.slots, dict) else {}
    service_query = slots.get("service")
    normalized_service_query = (
        service_query.strip()
        if isinstance(service_query, str) and service_query.strip()
        else None
    )
    if normalized_service_query is None:
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    reply_text, specialist_meta = decision_router._build_specialist_availability_followup_response(
        service_query=normalized_service_query,
        client_slug=payload.client_slug,
        message_text=message_text,
        requested_slot="time",
    )
    if not isinstance(reply_text, str) or not reply_text.strip():
        return None

    pending_question_act = (
        decision.meta.get("pending_question_act") if isinstance(decision.meta, dict) else None
    )
    if isinstance(pending_question_act, str):
        pending_question_act = pending_question_act.strip() or None
    temporal_scope = (
        decision.meta.get("temporal_scope") if isinstance(decision.meta, dict) else None
    )

    reply_meta: dict[str, object] = {
        "action": "booking_prompt",
        "intent": "booking",
        "source": "booking_specialist_availability_followup",
        "action_source": "booking_specialist_availability_followup",
        "tool_action": decision.tool_action,
        "pending_question_owner": "booking_specialist_availability_followup",
    }
    trace_meta: dict[str, object] = {
        "pending_question_owner": "booking_specialist_availability_followup",
    }
    if pending_question_act:
        reply_meta["pending_question_act"] = pending_question_act
        trace_meta["pending_question_act"] = pending_question_act
    reply_meta["pending_question_target"] = "specialist"
    trace_meta["pending_question_target"] = "specialist"
    reply_meta["pending_question_interaction"] = "specialist_availability_followup"
    reply_meta["active_question_relation"] = "specialist_availability_followup"
    trace_meta["active_question_relation"] = "specialist_availability_followup"
    if isinstance(temporal_scope, str) and temporal_scope.strip():
        normalized_temporal_scope = temporal_scope.strip()
        reply_meta["temporal_scope"] = normalized_temporal_scope
        trace_meta["temporal_scope"] = normalized_temporal_scope

    filtered_meta = _filter_specialist_followup_helper_meta(specialist_meta)
    if filtered_meta:
        reply_meta.update(filtered_meta)
        trace_meta.update(filtered_meta)

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_TIME_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_TIME_COLLECT_STAGE,
        success_label="Turn planner safe service-choice specialist time collect",
        followup_type="time",
        question_reason="booking_specialist_availability_followup",
        grounded_referents={"service": normalized_service_query},
        booking_slot_values={"service": normalized_service_query},
        booking_last_question="datetime",
        outcome_action="booking_prompt",
        outcome_source="booking_specialist_availability_followup",
    )


async def _try_handle_turn_planner_safe_service_choice_specialist_daypart_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_DAYPART_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_DAYPART_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_service_choice_specialist_daypart_collect_candidate(decision):
        return None

    slots = decision.slots if isinstance(decision.slots, dict) else {}
    service_query = slots.get("service")
    normalized_service_query = (
        service_query.strip()
        if isinstance(service_query, str) and service_query.strip()
        else None
    )
    if normalized_service_query is None:
        return None
    datetime_value = slots.get("datetime")
    normalized_datetime_value = (
        datetime_value.strip()
        if isinstance(datetime_value, str) and datetime_value.strip()
        else None
    )
    if normalized_datetime_value is None:
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    reply_text, specialist_meta = decision_router._build_specialist_availability_followup_response(
        service_query=normalized_service_query,
        client_slug=payload.client_slug,
        message_text=message_text,
        requested_slot="time",
    )
    if not isinstance(reply_text, str) or not reply_text.strip():
        return None

    pending_question_act = (
        decision.meta.get("pending_question_act") if isinstance(decision.meta, dict) else None
    )
    if isinstance(pending_question_act, str):
        pending_question_act = pending_question_act.strip() or None
    temporal_scope = (
        decision.meta.get("temporal_scope") if isinstance(decision.meta, dict) else None
    )

    reply_meta: dict[str, object] = {
        "action": "booking_prompt",
        "intent": "booking",
        "source": "booking_specialist_availability_followup",
        "action_source": "booking_specialist_availability_followup",
        "tool_action": decision.tool_action,
        "pending_question_owner": "booking_specialist_availability_followup",
    }
    trace_meta: dict[str, object] = {
        "pending_question_owner": "booking_specialist_availability_followup",
        "booking_datetime": normalized_datetime_value,
    }
    if pending_question_act:
        reply_meta["pending_question_act"] = pending_question_act
        trace_meta["pending_question_act"] = pending_question_act
    reply_meta["pending_question_target"] = "specialist"
    trace_meta["pending_question_target"] = "specialist"
    reply_meta["pending_question_interaction"] = "specialist_availability_followup"
    reply_meta["active_question_relation"] = "specialist_availability_followup"
    trace_meta["active_question_relation"] = "specialist_availability_followup"
    reply_meta["booking_datetime"] = normalized_datetime_value
    if isinstance(temporal_scope, str) and temporal_scope.strip():
        normalized_temporal_scope = temporal_scope.strip()
        reply_meta["temporal_scope"] = normalized_temporal_scope
        trace_meta["temporal_scope"] = normalized_temporal_scope

    filtered_meta = _filter_specialist_followup_helper_meta(specialist_meta)
    if filtered_meta:
        reply_meta.update(filtered_meta)
        trace_meta.update(filtered_meta)

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_DAYPART_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_DAYPART_COLLECT_STAGE,
        success_label="Turn planner safe service-choice specialist daypart collect",
        followup_type="time",
        question_reason="booking_specialist_availability_followup",
        grounded_referents={"service": normalized_service_query},
        booking_slot_values={
            "service": normalized_service_query,
            "datetime": normalized_datetime_value,
        },
        booking_last_question="datetime",
        outcome_action="booking_prompt",
        outcome_source="booking_specialist_availability_followup",
    )


async def _try_handle_turn_planner_safe_master_query_fact_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_FACT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_FACT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_master_query_fact_candidate(decision):
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    service_query = _resolve_turn_planner_tool_action_service_query(decision)
    if service_query is None:
        return None

    resolution = resolve_master_intent(
        message_text=message_text,
        client_slug=payload.client_slug,
        service_query=service_query,
        force_master_intent=True,
    )
    reply_decision = build_master_reply_from_pack(
        client_slug=payload.client_slug,
        message_text=message_text,
        resolution=resolution,
    )
    if reply_decision is None:
        return None

    reply_meta = dict(reply_decision.meta) if isinstance(reply_decision.meta, dict) else None
    if isinstance(reply_meta, dict):
        reply_meta.setdefault("tool_action", decision.tool_action)
    reply_text = reply_decision.response
    reply_action = getattr(reply_decision, "action", None)
    if not _should_accept_turn_planner_master_query_result(
        response_text=reply_text,
        reply_action=reply_action,
        reply_meta=reply_meta,
    ):
        if not _should_accept_turn_planner_master_query_service_not_found_collect_result(
            response_text=reply_text,
            reply_action=reply_action,
            reply_meta=reply_meta,
        ):
            return None
        question_reason = None
        if isinstance(reply_meta, dict):
            raw_reason = reply_meta.get("clarify_reason")
            if isinstance(raw_reason, str):
                question_reason = raw_reason.strip() or None
        collect_override = policy_core_route_snapshot.to_override()
        collect_override["action"] = "collect"
        collect_override["tool_action"] = "collect"
        collect_override["tool_args"] = {}
        collect_override["slots"] = {}
        collect_override["next_question"] = "service"
        collect_override["open_questions"] = ["service"]
        collect_override["subject_kind"] = "service"
        collect_override["resolution_mode"] = "clarify_missing_subject"
        collect_override["pending_question_target"] = "service"
        if question_reason:
            collect_override["reason"] = question_reason
        planner = TurnPlanner()
        try:
            collect_decision = planner.build_from_policy_override(
                collect_override,
                interaction_owner=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_SERVICE_NOT_FOUND_OWNER,
                interaction_relation=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_SERVICE_NOT_FOUND_STAGE,
            )
        except (AttributeError, TypeError, ValueError):
            return None
        if isinstance(reply_meta, dict):
            reply_meta["tool_action"] = collect_decision.tool_action
        return _finalize_turn_planner_owner_cutover(
            payload=payload,
            db=db,
            client_id=client_id,
            preflight_payload=preflight_payload,
            conversation_id=conversation_id,
            decision=collect_decision,
            reply_text=reply_text.strip(),
            reply_meta=reply_meta,
            trace_meta=None,
            owner_cutover=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_SERVICE_NOT_FOUND_OWNER,
            stage=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_SERVICE_NOT_FOUND_STAGE,
            success_label="Turn planner safe master-query service-not-found collect",
            tool_decision="service_not_found",
            followup_type="service_choice",
            question_reason=question_reason or "master_service_not_found",
        )

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=None,
        owner_cutover=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_FACT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_FACT_STAGE,
        success_label="Turn planner safe master-query fact",
        tool_decision="service_match",
    )


async def _try_handle_turn_planner_safe_master_query_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_master_query_collect_candidate(decision):
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    resolution = resolve_master_intent(
        message_text=message_text,
        client_slug=payload.client_slug,
        service_query=None,
        force_master_intent=True,
    )
    reply_decision = build_master_reply_from_pack(
        client_slug=payload.client_slug,
        message_text=message_text,
        resolution=resolution,
    )
    if reply_decision is None:
        return None

    reply_meta = dict(reply_decision.meta) if isinstance(reply_decision.meta, dict) else None
    if isinstance(reply_meta, dict):
        reply_meta.setdefault("tool_action", decision.tool_action)
    reply_text = reply_decision.response
    reply_action = getattr(reply_decision, "action", None)
    if not _should_accept_turn_planner_master_query_collect_result(
        response_text=reply_text,
        reply_action=reply_action,
        reply_meta=reply_meta,
    ):
        return None

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=None,
        owner_cutover=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_COLLECT_STAGE,
        success_label="Turn planner safe master-query collect",
        tool_decision="service_clarify",
        followup_type="service_choice",
        question_reason="service_clarify",
    )














def _resolve_turn_planner_smalltalk_reply(
    message_text: str | None,
) -> tuple[str, str] | None:
    if not isinstance(message_text, str) or not message_text.strip():
        return None
    if is_greeting_message(message_text):
        return ("greeting", GREETING_RESPONSE)
    if is_thanks_message(message_text):
        return ("thanks", THANKS_RESPONSE)
    if is_acknowledgement_message(message_text):
        return ("ack", ACKNOWLEDGEMENT_RESPONSE)
    return None

def _is_turn_planner_pending_ack_during_pending_state(
    *,
    conversation: Conversation,
    message_text: str | None,
) -> bool:
    if conversation.state != ConversationState.PENDING.value:
        return False
    if not isinstance(message_text, str) or not message_text.strip():
        return False

    from app.routers.webhook import pending as pending_router

    return pending_router._is_pending_ack(message_text)


def _restore_turn_planner_collect_owner_bot_active_state(
    *,
    db: Session,
    conversation: Conversation,
) -> dict[str, object] | None:
    if conversation.state != ConversationState.PENDING.value:
        return {}

    active_handover = get_active_handover(db, conversation.id)
    if active_handover is not None:
        resolve_result = manager_resolve(
            db,
            conversation,
            active_handover,
            manager_id="system",
            manager_name="system",
            preserve_context=True,
        )
        if not getattr(resolve_result, "ok", False):
            return None
        resume_mode = "handover_resolve"
    else:
        transition_state(
            conversation,
            ConversationState.BOT_ACTIVE,
            allow_same=False,
            enforce=True,
        )
        if not isinstance(conversation.context, dict):
            conversation.context = {}
        resume_mode = "state_transition"

    conversation.bot_status = "active"
    return {
        "pending_collect_resume_boundary": True,
        "pending_collect_resume_mode": resume_mode,
        "pending_collect_resume_state_before": ConversationState.PENDING.value,
        "pending_collect_resume_state_after": conversation.state,
    }


def _is_turn_planner_session_reset_only_message(message_text: str | None) -> bool:
    if not isinstance(message_text, str) or not message_text.strip():
        return False
    return _is_session_reset_only_message(message_text)


def _is_turn_planner_safe_explicit_handoff_candidate(decision: PolicyDecision) -> bool:
    decision_reason = decision.meta.get("reason") if isinstance(decision.meta, dict) else None
    return (
        decision.outcome == "HANDOFF"
        and decision.action == "handoff"
        and decision.tool_action == "handoff"
        and decision.intent in REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_INTENTS
        and decision_reason in REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_REASONS
    )


def _resolve_turn_planner_safe_llm_booking_prompt_candidate(
    *,
    payload: WebhookRequest,
    message_text: str | None,
    reply_slot: str | None,
    current_goal: str | None,
    booking_state: dict[str, object] | None,
    context: dict[str, object],
    now: datetime,
    allow_initial_slot_progression: bool = False,
    allow_timeout_recovery: bool = False,
) -> dict[str, object] | None:
    return resolve_llm_booking_prompt_candidate(
        payload=payload,
        message_text=message_text,
        reply_slot=reply_slot,
        current_goal=current_goal,
        booking_state=booking_state,
        context=context,
        now=now,
        allow_initial_slot_progression=allow_initial_slot_progression,
        allow_timeout_recovery=allow_timeout_recovery,
        route_llm_policy_core_fn=route_llm_policy_core,
        initial_booking_policy_core_max_tokens=(
            REASONING_CORE_INITIAL_BOOKING_POLICY_CORE_MAX_TOKENS
        ),
    )


def _resolve_turn_planner_pending_booking_reactivation_candidate(
    *,
    payload: WebhookRequest,
    message_text: str | None,
    booking_state: dict[str, object] | None,
    context: dict[str, object],
    now: datetime,
) -> dict[str, object] | None:
    return resolve_pending_booking_reactivation_candidate(
        payload=payload,
        message_text=message_text,
        booking_state=booking_state,
        context=context,
        now=now,
        route_llm_policy_core_fn=route_llm_policy_core,
        initial_booking_policy_core_max_tokens=(
            REASONING_CORE_INITIAL_BOOKING_POLICY_CORE_MAX_TOKENS
        ),
    )


def _resolve_turn_planner_pending_booking_resume_boundary_payload(
    *,
    db: Session,
    conversation_id: UUID | None,
    conversation_snapshot: ReasoningCoreConversationSnapshot | None,
) -> dict[str, object] | None:
    source_conversation_id = conversation_id or (
        conversation_snapshot.conversation_id if conversation_snapshot is not None else None
    )
    if source_conversation_id is None:
        return None
    try:
        conversation = db.query(Conversation).filter(Conversation.id == source_conversation_id).first()
    except Exception:
        return None
    if not isinstance(conversation, Conversation):
        return None
    context = context_manager_router._get_conversation_context(conversation)
    return DialogStateService().derive_pending_booking_resume_boundary_payload(
        context,
        now=datetime.now(timezone.utc),
        prompt_builder=decision_router._build_resume_prompt_for_expected_reply,
    )

async def _try_handle_turn_planner_safe_session_reset_only_delegate(
    *,
    payload: WebhookRequest,
    db: Session,
    conversation_id: UUID | None,
    enqueue_only: bool,
    skip_persist: bool,
) -> WebhookResponse | None:
    if not _is_turn_planner_session_reset_only_message(
        payload.body.message if payload and payload.body else None
    ):
        return None

    with ExitStack() as stack:
        stack.enter_context(use_intent_signal_override(None))
        stack.enter_context(use_intent_semantic_override(None))
        stack.enter_context(use_dialogue_controller_override(None))
        stack.enter_context(use_domain_routing_override(None))
        return await decision_router._handle_webhook_payload(
            payload,
            db,
            provided_secret=None,
            enforce_secret=False,
            enqueue_only=enqueue_only,
            skip_persist=skip_persist,
            conversation_id=conversation_id,
        )


async def _try_handle_turn_planner_safe_pending_ack_continuity_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    enqueue_only: bool,
    skip_persist: bool,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist:
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    metadata = body.metadata if body is not None else None
    remote_jid = getattr(metadata, "remoteJid", None)
    if not isinstance(remote_jid, str) or not remote_jid.strip():
        return None
    remote_jid = remote_jid.strip()

    client = _resolve_turn_planner_owner_client(
        db,
        payload=payload,
        client_id=client_id,
        preflight_payload=preflight_payload,
    )
    if not isinstance(client, Client):
        return None

    branch_id = _resolve_snapshot_branch_id(preflight_payload)
    conversation = _ensure_turn_planner_owner_conversation(
        db,
        client=client,
        remote_jid=remote_jid,
        branch_id=branch_id,
        conversation_id=conversation_id,
    )
    if not isinstance(conversation, Conversation):
        return None
    if not _is_turn_planner_pending_ack_during_pending_state(
        conversation=conversation,
        message_text=message_text,
    ):
        return None

    routing = decision_router.ROUTING_MATRIX.get(conversation.state, {})
    if not routing.get("allow_bot_reply", False):
        return None

    saved_message = save_message(
        db,
        conversation.id,
        client.id,
        role="user",
        content=(message_text or "").strip(),
        message_metadata=_build_turn_planner_user_message_metadata(payload=payload),
    )
    _update_message_decision_metadata(
        saved_message,
        {
            "source": "consultant_core_runtime",
            "owner_cutover": REASONING_CORE_TURN_PLANNER_PENDING_ACK_OWNER,
        },
    )

    continuity_hooks = PendingContinuityRuntimeHooks(
        get_conversation_context=context_manager_router._get_conversation_context,
        set_conversation_context=context_manager_router._set_conversation_context,
        transition_state=transition_state,
        manager_resolve=lambda *args, **kwargs: manager_resolve(db, *args, **kwargs),
        record_decision_trace=_record_decision_trace,
        update_message_decision_metadata=_update_message_decision_metadata,
    )
    continuity_decision = _resolve_pending_ack(
        conversation=conversation,
        handover=get_active_handover(db, conversation.id),
        saved_message=saved_message,
        now=datetime.now(timezone.utc),
        router_pending_meta={
            "source": "consultant_core_runtime",
            "owner_cutover": REASONING_CORE_TURN_PLANNER_PENDING_ACK_OWNER,
            "owner_stage": REASONING_CORE_TURN_PLANNER_PENDING_ACK_STAGE,
        },
        msg_pending_ack=decision_router.MSG_PENDING_ACK,
        hooks=continuity_hooks,
    )
    if not continuity_decision.handled:
        return None

    bot_response = None
    result_message = continuity_decision.success_message or "Pending ack handled"
    if isinstance(continuity_decision.bot_response, str):
        save_message(
            db,
            conversation.id,
            client.id,
            role="assistant",
            content=continuity_decision.bot_response,
            message_metadata={
                "source": "bot",
                "owner_cutover": REASONING_CORE_TURN_PLANNER_PENDING_ACK_OWNER,
            },
        )
        instance_id = get_instance_id(
            db,
            client.id,
            branch_id=conversation.branch_id,
            remote_jid=remote_jid,
        )
        simulation_mode = bool(getattr(metadata, "simulation_mode", False))
        if simulation_mode:
            send_result = ChatFlowAdapter().send_text(
                remote_jid,
                continuity_decision.bot_response,
                MessageOptions(
                    instance_id=instance_id,
                    idempotency_key=getattr(metadata, "messageId", None),
                    extra={"simulation_mode": True},
                ),
            )
        else:
            send_result = send_message_safe(
                instance_id or "",
                remote_jid,
                continuity_decision.bot_response,
                getattr(metadata, "messageId", None),
                notify_on_failure=True,
                record_metrics=True,
            )
        bot_response = continuity_decision.bot_response
        sent = bool(getattr(send_result, "is_ok", lambda: False)())
        if not sent:
            result_message = continuity_decision.failure_message or result_message

    db.commit()
    return WebhookResponse(
        success=True,
        message=result_message,
        conversation_id=conversation.id,
        bot_response=bot_response,
    )


def _build_turn_planner_safe_greeting_decision(
    *,
    controller_route_snapshot: object,
    message_text: str | None,
) -> PolicyDecision | None:
    smalltalk_payload = _resolve_turn_planner_smalltalk_reply(message_text)
    if smalltalk_payload is None:
        return None
    intent, _reply_text = smalltalk_payload
    reason = getattr(controller_route_snapshot, "reason", None)
    controller_class = getattr(controller_route_snapshot, "controller_class", None)
    if reason != REASONING_CORE_TURN_PLANNER_GREETING_REASON or controller_class != "greeting":
        return None
    normalized_text = getattr(controller_route_snapshot, "normalized_text", None)
    goal = getattr(controller_route_snapshot, "goal", None)
    confidence = getattr(controller_route_snapshot, "confidence", None)
    return TurnPlanner().coerce(
        {
            "outcome": "FACT",
            "action": "fact",
            "intent": intent,
            "source": "policy_core",
            "tool_action": "smalltalk",
            "interaction": {
                "owner": REASONING_CORE_TURN_PLANNER_GREETING_OWNER,
                "relation": REASONING_CORE_TURN_PLANNER_GREETING_STAGE,
            },
            "meta": {
                "planner_source": "turn_planner",
                "synthetic_policy_decision": True,
                "reason": reason,
                "goal": goal,
                "normalized_text": normalized_text,
                "confidence": confidence,
                "controller_class": controller_class,
            },
        }
    )


def _is_turn_planner_safe_greeting_candidate(decision: PolicyDecision) -> bool:
    reason = decision.meta.get("reason") if isinstance(decision.meta, dict) else None
    controller_class = decision.meta.get("controller_class") if isinstance(decision.meta, dict) else None
    return all(
        (
            decision.outcome == "FACT",
            decision.action == "fact",
            decision.tool_action == "smalltalk",
            decision.intent in REASONING_CORE_TURN_PLANNER_GREETING_INTENTS,
            reason == REASONING_CORE_TURN_PLANNER_GREETING_REASON,
            controller_class == "greeting",
        )
    )


def _should_accept_turn_planner_service_query_result(
    decision: PolicyDecision,
    *,
    response_text: str | None,
    handled: bool,
    ok: bool,
    decision_meta: dict[str, object] | None,
) -> bool:
    if not handled or not ok or not isinstance(response_text, str) or not response_text.strip():
        return False
    tool_decision = None
    if isinstance(decision_meta, dict):
        raw_decision = decision_meta.get("tool_decision")
        if isinstance(raw_decision, str):
            tool_decision = raw_decision.strip() or None
    if decision.intent == "duration":
        return tool_decision == "duration"
    if decision.intent == "info" and _turn_planner_pack_ref_set(decision) == {"pricing"}:
        return tool_decision in {"ok", "truth_fallback", "price_item_fallback", "not_found_fallback"}
    return False


def _should_accept_turn_planner_pricing_collect_result(
    *,
    response_text: str | None,
    reply_meta: dict[str, object] | None,
) -> bool:
    if not isinstance(response_text, str) or not response_text.strip():
        return False
    if not isinstance(reply_meta, dict):
        return False

    action_class = reply_meta.get("action_class")
    intent_class = reply_meta.get("intent_class")
    fact_source = reply_meta.get("fact_source")
    question_type = reply_meta.get("question_type")
    service_query = reply_meta.get("service_query")
    fact_refs = reply_meta.get("fact_refs")
    return all(
        (
            isinstance(action_class, str) and action_class.strip().casefold() == "collect",
            isinstance(intent_class, str) and intent_class.strip().casefold() == "service_clarify",
            isinstance(fact_source, str) and fact_source.strip().casefold() == "truth",
            isinstance(question_type, str) and question_type.strip().casefold() == "pricing",
            not (isinstance(service_query, str) and service_query.strip()),
            isinstance(fact_refs, list)
            and any(
                isinstance(fact_ref, str) and fact_ref.strip().casefold() == "service_clarify"
                for fact_ref in fact_refs
            ),
        )
    )


def _should_accept_turn_planner_duration_collect_result(
    *,
    response_text: str | None,
    reply_action: str | None,
    reply_meta: dict[str, object] | None,
) -> bool:
    if not isinstance(response_text, str) or not response_text.strip():
        return False
    if reply_action != "reply" or not isinstance(reply_meta, dict):
        return False

    question_type = reply_meta.get("question_type")
    service_query = reply_meta.get("service_query")
    fact_source = reply_meta.get("fact_source")
    action_class = reply_meta.get("action_class")
    intent_class = reply_meta.get("intent_class")
    fact_refs = reply_meta.get("fact_refs")
    info_sections = reply_meta.get("info_sections")
    return all(
        (
            isinstance(question_type, str) and question_type.strip().casefold() == "duration",
            not (isinstance(service_query, str) and service_query.strip()),
            isinstance(fact_source, str) and fact_source.strip().casefold() == "truth",
            isinstance(action_class, str) and action_class.strip().casefold() == "fact",
            isinstance(intent_class, str)
            and intent_class.strip().casefold() in {"service_duration", "duration"},
            isinstance(fact_refs, list)
            and any(
                isinstance(fact_ref, str)
                and fact_ref.strip().casefold() in {"duration", "service_duration"}
                for fact_ref in fact_refs
            ),
            isinstance(info_sections, list)
            and any(
                isinstance(section, str) and section.strip().casefold() == "duration"
                for section in info_sections
            ),
        )
    )


def _should_accept_turn_planner_master_query_result(
    *,
    response_text: str | None,
    reply_action: str | None,
    reply_meta: dict[str, object] | None,
) -> bool:
    if not isinstance(response_text, str) or not response_text.strip():
        return False
    if reply_action != "reply" or not isinstance(reply_meta, dict):
        return False
    service_query = reply_meta.get("service_query")
    action_class = reply_meta.get("action_class")
    return all(
        (
            reply_meta.get("master_query_contract") == "masters_catalog.v1",
            _reply_meta_token_equals(reply_meta, "master_reply_mode", "service_match"),
            isinstance(service_query, str) and bool(service_query.strip()),
            not isinstance(action_class, str)
            or action_class.strip().casefold() == "fact",
            _reply_meta_has_section(reply_meta, "master"),
        )
    )


def _should_accept_turn_planner_master_query_collect_result(
    *,
    response_text: str | None,
    reply_action: str | None,
    reply_meta: dict[str, object] | None,
) -> bool:
    if not isinstance(response_text, str) or not response_text.strip():
        return False
    if reply_action != "collect" or not isinstance(reply_meta, dict):
        return False
    service_query = reply_meta.get("service_query")
    action_class = reply_meta.get("action_class")
    return all(
        (
            reply_meta.get("master_query_contract") == "masters_catalog.v1",
            _reply_meta_token_equals(reply_meta, "master_reply_mode", "service_clarify"),
            _reply_meta_token_equals(reply_meta, "clarify_reason", "missing_service_query"),
            not (isinstance(service_query, str) and service_query.strip()),
            not isinstance(action_class, str)
            or action_class.strip().casefold() == "collect",
            _reply_meta_has_section(reply_meta, "master"),
        )
    )


def _should_accept_turn_planner_master_query_service_not_found_collect_result(
    *,
    response_text: str | None,
    reply_action: str | None,
    reply_meta: dict[str, object] | None,
) -> bool:
    if not isinstance(response_text, str) or not response_text.strip():
        return False
    if reply_action != "collect" or not isinstance(reply_meta, dict):
        return False
    service_query = reply_meta.get("service_query")
    action_class = reply_meta.get("action_class")
    return all(
        (
            reply_meta.get("master_query_contract") == "masters_catalog.v1",
            _reply_meta_token_equals(reply_meta, "master_reply_mode", "service_not_found"),
            _reply_meta_token_equals(reply_meta, "clarify_reason", "master_service_not_found"),
            isinstance(service_query, str) and bool(service_query.strip()),
            not isinstance(action_class, str)
            or action_class.strip().casefold() == "collect",
            _reply_meta_has_section(reply_meta, "master"),
        )
    )


def _should_accept_turn_planner_booking_verification_result(
    *,
    response_text: str | None,
    handled: bool,
    ok: bool,
    error_code: str | None,
    decision_meta: dict[str, object] | None,
) -> bool:
    if not handled or not isinstance(response_text, str) or not response_text.strip():
        return False
    if not isinstance(decision_meta, dict):
        return False
    tool_action = decision_meta.get("tool_action")
    tool_decision = decision_meta.get("tool_decision")
    appointment_id = decision_meta.get("appointment_id")
    if tool_action != "calendar.get_booking":
        return False
    if (
        tool_decision == "ok"
        and ok
        and isinstance(appointment_id, str)
        and bool(appointment_id.strip())
    ):
        return True
    return all(
        (
            tool_decision == "not_found",
            not ok,
            error_code == "appointment_not_found",
        )
    )


def _build_turn_planner_owner_trace_payload(
    *,
    decision: PolicyDecision,
    stage: str,
    decision_name: str = "reply",
    trace_meta: dict[str, object] | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "stage": stage,
        "decision": decision_name,
        "intent": decision.intent,
        "reason": decision.meta.get("reason"),
        "tool_action": decision.tool_action,
        "source": "consultant_core_runtime",
    }
    if isinstance(trace_meta, dict):
        for key, value in trace_meta.items():
            if key in {"stage", "decision"}:
                continue
            payload[key] = value
    return payload


def _filter_specialist_followup_helper_meta(
    specialist_meta: dict[str, object] | None,
) -> dict[str, object]:
    if not isinstance(specialist_meta, dict):
        return {}
    return {
        key: specialist_meta.get(key)
        for key in (
            "info_sections",
            "fact_intents",
            "master_query_contract",
            "master_reply_mode",
            "master_profiles",
            "master_profiles_count",
            "service_query",
        )
        if specialist_meta.get(key) not in (None, [], {})
    }


def _finalize_turn_planner_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    decision: PolicyDecision,
    reply_text: str,
    reply_meta: dict[str, object] | None,
    trace_meta: dict[str, object] | None,
    owner_cutover: str,
    stage: str,
    success_label: str,
    tool_decision: str | None = None,
    followup_type: str | None = None,
    question_reason: str | None = None,
    grounded_referents: dict[str, str] | None = None,
    booking_slot_values: dict[str, str] | None = None,
    booking_last_question: str | None = None,
    booking_payload_override: dict[str, object] | None = None,
    outcome_action: OwnerCutoverAction = "reply",
    outcome_source: str = "consultant_core_runtime",
    trace_decision: str = "reply",
    extra_trace_payloads: Sequence[dict[str, object]] | None = None,
    clear_intent_queue: bool = False,
    clear_service_hint: bool = False,
    clear_expected_reply: bool = False,
    clear_reply_reason: str | None = None,
    artifact: OwnerExecutionArtifact | None = None,
    existing_conversation: Conversation | None = None,
    existing_saved_message: Message | None = None,
    send_and_save: Callable[[str], tuple[str, bool]] | None = None,
    resolve_transport: Callable[[], tuple[str | None, str | None]] | None = None,
    transport_status_token: str | None = None,
    transport_reason_token: str | None = None,
    trace_payload_override: dict[str, object] | None = None,
    guard_response_resolver: Callable[[], WebhookResponse | None] | None = None,
    guard_response: WebhookResponse | None = None,
    extra_meta_updates: Sequence[dict[str, object]] | None = None,
) -> WebhookResponse | None:
    def _apply_context_updates(
        conversation: Conversation,
        saved_message: Message | None,
    ) -> None:
        nonlocal question_reason

        now = datetime.now(timezone.utc)
        context = context_manager_router._get_conversation_context(conversation)
        dialog_state_service = DialogStateService()
        context_dirty = False

        def _apply_expected_reply_sync(
            *,
            expected_reply_type: str | None,
            reason: str,
        ) -> dict[str, object]:
            sync_result = dialog_state_service.build_expected_reply_context_sync_result(
                context,
                expected_reply_type=expected_reply_type,
                reason=reason,
                now=now,
                context_manager_key=decision_router.CONTEXT_MANAGER_KEY,
                canonical_state_key="canonical_dialog_state",
                booking_key="booking",
                session_memory_key=decision_router.SESSION_MEMORY_KEY,
                re_entry_required_key=decision_router.RE_ENTRY_REQUIRED_KEY,
                service_carryover_key=decision_router.SERVICE_CARRYOVER_KEY,
                consult_context_key=decision_router.CONSULT_CONTEXT_KEY,
                session_memory_ttl_hours=decision_router.SESSION_MEMORY_TTL_HOURS,
                service_default_ttl=SERVICE_CARRYOVER_TTL_MESSAGES,
                consult_default_ttl=decision_router.CONSULT_CONTEXT_TTL_MESSAGES,
            )
            context_manager_router._set_conversation_context(
                conversation,
                sync_result.context,
            )
            if sync_result.re_entry_cleared:
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "re_entry",
                        "decision": "cleared",
                        "reason": sync_result.expected_reply_reason,
                    },
                )
            _record_decision_trace(
                conversation,
                {
                    "stage": "question_contract",
                    "decision": "set",
                    _ER_KEY: sync_result.expected_reply_type,
                    "reason": sync_result.expected_reply_reason,
                },
            )
            if saved_message:
                _update_message_decision_metadata(
                    saved_message,
                    {
                        _ER_KEY: sync_result.expected_reply_type,
                        _ERR_KEY: sync_result.expected_reply_reason,
                    },
                )
            if sync_result.expected_reply_type:
                _record_session_memory_update(
                    conversation,
                    saved_message,
                    memory=sync_result.question_memory or {},
                    reason="question_set",
                )
            return sync_result.context

        if clear_service_hint:
            context = decision_router._clear_service_hint(context)
            context_dirty = True
        if clear_intent_queue:
            context = dialog_state_service.set_intent_queue(context, queue=None)
            context_dirty = True
        if booking_payload_override is not None:
            context = dialog_state_service.set_context_booking_payload(
                context,
                booking_payload_override,
                key="booking",
            )
            context_dirty = True
        if booking_last_question:
            booking_payload = dialog_state_service.build_collect_owner_booking_payload(
                existing_booking=context.get("booking") if isinstance(context, dict) else None,
                now=now,
                last_question=booking_last_question,
                slot_values=booking_slot_values,
            )
            context = dialog_state_service.set_context_booking_payload(
                context,
                booking_payload,
                key="booking",
            )
            context_dirty = True
        if followup_type:
            context = _apply_expected_reply_sync(
                expected_reply_type=followup_type,
                reason=question_reason or followup_type,
            )
        elif clear_expected_reply:
            context = _apply_expected_reply_sync(
                expected_reply_type=None,
                reason=clear_reply_reason or owner_cutover,
            )
        elif context_dirty:
            context_manager_router._set_conversation_context(conversation, context)

    if artifact is not None and existing_conversation is not None and send_and_save is not None:
        if guard_response is None and guard_response_resolver:
            guard_response = guard_response_resolver()
        if guard_response:
            db.commit()
            return guard_response

        conversation = existing_conversation
        saved_message = existing_saved_message
        turn_outcome = artifact.turn_outcome
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {
                    "turn_outcome": turn_outcome.to_metadata(),
                    "consultant_core_runtime": artifact.runtime_meta,
                },
            )
            if isinstance(reply_meta, dict):
                _update_message_decision_metadata(saved_message, reply_meta)

        trace_payload = (
            dict(trace_payload_override)
            if isinstance(trace_payload_override, dict) and trace_payload_override
            else _build_turn_planner_owner_trace_payload(
                decision=decision,
                stage=stage,
                decision_name=trace_decision,
                trace_meta=trace_meta,
            )
        )
        _record_decision_trace(conversation, trace_payload)
        if extra_trace_payloads:
            for extra_trace in extra_trace_payloads:
                if not isinstance(extra_trace, dict) or not extra_trace:
                    continue
                _record_decision_trace(conversation, dict(extra_trace))

        if saved_message:
            _record_message_decision_meta(
                saved_message,
                action=outcome_action,
                intent=decision.intent,
                source=outcome_source,
                fast_intent=False,
            )
            if extra_meta_updates:
                for updates in extra_meta_updates:
                    if not isinstance(updates, dict) or not updates:
                        continue
                    _update_message_decision_metadata(saved_message, dict(updates))

        _apply_context_updates(conversation, saved_message)
        bot_response, sent = send_and_save(artifact.turn_result.reply.text)
        if transport_status_token is None and transport_reason_token is None and resolve_transport:
            transport_status_token, transport_reason_token = resolve_transport()
        if not isinstance(transport_status_token, str) or not transport_status_token.strip():
            transport_status_token = "sent" if sent else "failed"
        if not sent and not transport_reason_token:
            transport_reason_token = "provider_send_failed"
        turn_outcome = turn_outcome.model_copy(
            update={
                "observability": turn_outcome.observability.model_copy(
                    update={
                        "reply_observed": transport_status_token in {"sent", "simulated"},
                        "transport_status": transport_status_token,
                        "transport_reason": transport_reason_token,
                    }
                )
            }
        )
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {"turn_outcome": turn_outcome.to_metadata()},
            )

        db.commit()
        return WebhookResponse(
            success=True,
            message=f"{success_label} sent" if sent else f"{success_label} failed",
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    body = payload.body if payload else None
    metadata = body.metadata if body is not None else None
    remote_jid = getattr(metadata, "remoteJid", None)
    if not isinstance(remote_jid, str) or not remote_jid.strip():
        return None
    remote_jid = remote_jid.strip()

    client = _resolve_turn_planner_owner_client(
        db,
        payload=payload,
        client_id=client_id,
        preflight_payload=preflight_payload,
    )
    if not isinstance(client, Client):
        return None

    branch_id = _resolve_snapshot_branch_id(preflight_payload)
    conversation = _ensure_turn_planner_owner_conversation(
        db,
        client=client,
        remote_jid=remote_jid,
        branch_id=branch_id,
        conversation_id=conversation_id,
    )
    if not isinstance(conversation, Conversation):
        return None

    message_metadata = _build_turn_planner_user_message_metadata(payload=payload)
    message_text = body.message if body is not None else None
    saved_message = save_message(
        db,
        conversation.id,
        client.id,
        role="user",
        content=message_text or "",
        message_metadata=message_metadata,
    )
    _record_message_decision_meta(
        saved_message,
        action=outcome_action,
        intent=decision.intent,
        source=outcome_source,
        fast_intent=False,
    )
    if isinstance(reply_meta, dict):
        _update_message_decision_metadata(saved_message, reply_meta)

    if extra_trace_payloads:
        for extra_trace in extra_trace_payloads:
            if not isinstance(extra_trace, dict) or not extra_trace:
                continue
            _record_decision_trace(conversation, dict(extra_trace))

    _record_decision_trace(
        conversation,
        _build_turn_planner_owner_trace_payload(
            decision=decision,
            stage=stage,
            decision_name=trace_decision,
            trace_meta=trace_meta,
        ),
    )
    now = datetime.now(timezone.utc)
    if followup_type:
        _apply_context_updates(conversation, saved_message)
        dialog_state_service = DialogStateService()
        dialog_state_kwargs = {
            "decision": decision,
            _ER_KEY: followup_type,
            _ERR_KEY: question_reason,
            "owner_cutover": owner_cutover,
        }
        if isinstance(grounded_referents, dict) and grounded_referents:
            dialog_state_kwargs["grounded_referents"] = grounded_referents
        dialog_state = dialog_state_service.build_collect_owner_state(**dialog_state_kwargs)
    else:
        _apply_context_updates(conversation, saved_message)
        dialog_state_service = DialogStateService()
        dialog_state = dialog_state_service.normalize(
            {
                "meta": {
                    "writer": "dialog_state_service",
                    "owner_cutover": owner_cutover,
                }
            }
        )
    executor = TurnExecutor()

    save_message(
        db,
        conversation.id,
        client.id,
        role="assistant",
        content=reply_text,
        message_metadata={
            "source": "bot",
            "owner_cutover": owner_cutover,
        },
    )

    instance_id = get_instance_id(
        db,
        client.id,
        branch_id=conversation.branch_id,
        remote_jid=remote_jid,
    )
    simulation_mode = bool(getattr(metadata, "simulation_mode", False))
    transport_simulated = False
    if simulation_mode:
        send_result = ChatFlowAdapter().send_text(
            remote_jid,
            reply_text,
            MessageOptions(
                instance_id=instance_id,
                idempotency_key=getattr(metadata, "messageId", None),
                extra={"simulation_mode": True},
            ),
        )
        transport_simulated = bool(getattr(send_result, "is_ok", lambda: False)())
    else:
        send_result = send_message_safe(
            instance_id or "",
            remote_jid,
            reply_text,
            getattr(metadata, "messageId", None),
            notify_on_failure=True,
            record_metrics=True,
        )
    sent = bool(getattr(send_result, "is_ok", lambda: False)())
    transport_status = "delivered" if sent else "failed"
    transport_reason = None if sent else _resolve_turn_planner_transport_reason(
        send_result,
        instance_id=instance_id,
    )
    artifact = executor.build_owner_cutover_artifact(
        decision=decision,
        dialog_state=dialog_state,
        text=reply_text,
        owner_cutover=owner_cutover,
        transport_status=transport_status,
        transport_reason=transport_reason,
        downstream_tool_decision=tool_decision,
        followup_type=followup_type,
        followup_reason=question_reason,
        reason_code=decision.meta.get("reason") if isinstance(decision.meta, dict) else None,
        stages=["ingress", "turn_planner", "executor", "realizer", stage],
        action=outcome_action,
        source=outcome_source,
    )
    turn_result = artifact.turn_result
    turn_outcome = artifact.turn_outcome
    _update_message_decision_metadata(
        saved_message,
        {
            "turn_outcome": turn_outcome.to_metadata(),
            "consultant_core_runtime": artifact.runtime_meta,
        },
    )
    conversation.last_message_at = now
    db.commit()
    return WebhookResponse(
        success=True,
        message=f"{success_label} sent" if sent else f"{success_label} failed",
        conversation_id=conversation.id,
        bot_response=turn_result.reply.text,
    )


def _finalize_tool_reply_owner_execution(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    conversation: Conversation,
    saved_message: Message | None,
    owner_execution: ToolReplyOwnerExecution,
    reply_text: str,
    reply_intent: str | None,
    reply_source: str,
    owner_cutover: str,
    tool_decision: str | None,
    expected_reply_type: str | None,
    expected_reply_reason: str | None,
    maybe_apply_fact_guard: Callable[..., WebhookResponse | None],
    guard_decision_meta: dict[str, object] | None,
    allow_handover: bool,
    send_and_save: Callable[[str], tuple[str, bool]],
    transport_status_token: str | None,
    transport_reason_token: str | None,
    success_label: str = "LLM policy core tool response",
) -> WebhookResponse | None:
    guard_response = maybe_apply_fact_guard(
        decision_meta=guard_decision_meta,
        intent=reply_intent,
        source=reply_source,
        allow_handover=allow_handover,
    )
    followup_kwargs: dict[str, str | None] = {}
    for key, value in zip(
        ("followup_" + "type", "question_" + "reason"),
        (expected_reply_type, expected_reply_reason),
    ):
        followup_kwargs[key] = value
    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=None,
        conversation_id=conversation.id,
        decision=owner_execution.decision,
        reply_text=reply_text,
        reply_meta=None,
        trace_meta=None,
        owner_cutover=owner_cutover,
        stage="llm_policy_core_tool",
        success_label=success_label,
        tool_decision=tool_decision,
        outcome_action="reply",
        outcome_source=reply_source,
        artifact=owner_execution.payload.artifact,
        existing_conversation=conversation,
        existing_saved_message=saved_message,
        send_and_save=send_and_save,
        transport_status_token=transport_status_token,
        transport_reason_token=transport_reason_token,
        trace_payload_override=owner_execution.payload.trace_payload_override,
        guard_response=guard_response,
        extra_trace_payloads=owner_execution.payload.extra_trace_payloads,
        extra_meta_updates=owner_execution.payload.extra_meta_updates,
        **followup_kwargs,
    )


async def _try_handle_turn_planner_safe_greeting_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    enqueue_only: bool,
    skip_persist: bool,
    controller_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or controller_route_snapshot is None:
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    decision = _build_turn_planner_safe_greeting_decision(
        controller_route_snapshot=controller_route_snapshot,
        message_text=message_text,
    )
    if decision is None or not _is_turn_planner_safe_greeting_candidate(decision):
        return None

    client = _resolve_turn_planner_owner_client(
        db,
        payload=payload,
        client_id=client_id,
        preflight_payload=preflight_payload,
    )
    if not isinstance(client, Client):
        return None

    metadata = body.metadata if body is not None else None
    remote_jid = getattr(metadata, "remoteJid", None)
    if not isinstance(remote_jid, str) or not remote_jid.strip():
        return None

    branch_id = _resolve_snapshot_branch_id(preflight_payload)
    conversation = _ensure_turn_planner_owner_conversation(
        db,
        client=client,
        remote_jid=remote_jid.strip(),
        branch_id=branch_id,
        conversation_id=conversation_id,
    )
    if not isinstance(conversation, Conversation):
        return None

    routing = decision_router.ROUTING_MATRIX.get(conversation.state, {})
    if not routing.get("allow_bot_reply", False):
        return None

    # Pending acknowledgements belong to the continuity owner, not smalltalk.
    if _is_turn_planner_pending_ack_during_pending_state(
        conversation=conversation,
        message_text=message_text,
    ):
        return None

    smalltalk_payload = _resolve_turn_planner_smalltalk_reply(message_text)
    if smalltalk_payload is None:
        return None
    intent, reply_text = smalltalk_payload
    if intent != decision.intent:
        return None

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text,
        reply_meta=None,
        trace_meta={
            "controller_class": getattr(controller_route_snapshot, "controller_class", None),
            "smalltalk_intent": intent,
        },
        owner_cutover=REASONING_CORE_TURN_PLANNER_GREETING_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_GREETING_STAGE,
        success_label="Turn planner safe greeting owner",
        tool_decision=intent,
        outcome_action="smalltalk",
    )


async def _try_handle_turn_planner_safe_explicit_handoff_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    pending_booking_resume_boundary_payload: dict[str, object] | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_explicit_handoff_candidate(decision):
        return None

    body = payload.body if payload else None
    metadata = body.metadata if body is not None else None
    remote_jid = getattr(metadata, "remoteJid", None)
    if not isinstance(remote_jid, str) or not remote_jid.strip():
        return None
    remote_jid = remote_jid.strip()

    client = _resolve_turn_planner_owner_client(
        db,
        payload=payload,
        client_id=client_id,
        preflight_payload=preflight_payload,
    )
    if not isinstance(client, Client):
        return None

    branch_id = _resolve_snapshot_branch_id(preflight_payload)
    conversation = _ensure_turn_planner_owner_conversation(
        db,
        client=client,
        remote_jid=remote_jid,
        branch_id=branch_id,
        conversation_id=conversation_id,
    )
    if not isinstance(conversation, Conversation):
        return None

    routing = decision_router.ROUTING_MATRIX.get(conversation.state, {})
    if not routing.get("allow_bot_reply", False):
        return None

    # Pending acknowledgements belong to the continuity owner, not handoff reuse/create.
    if _is_turn_planner_pending_ack_during_pending_state(
        conversation=conversation,
        message_text=body.message if body is not None else None,
    ):
        return None
    if _is_turn_planner_session_reset_only_message(body.message if body is not None else None):
        return None

    decision_reason = decision.meta.get("reason") if isinstance(decision.meta, dict) else None
    direct_explicit_handoff_allowed = (
        (decision.intent, decision_reason)
        in {
            ("human_request", "ingress_explicit_human_request"),
            ("frustration", "ingress_explicit_frustration_handoff"),
            ("reschedule", "reschedule_missing_reference"),
        }
    )
    if (
        isinstance(pending_booking_resume_boundary_payload, dict)
        and not direct_explicit_handoff_allowed
    ):
        return None

    allow_handover_create = (
        conversation.state == "bot_active" and bool(routing.get("allow_handover_create", False))
    )
    if not allow_handover_create and conversation.state != ConversationState.PENDING.value:
        return None

    user = _resolve_turn_planner_owner_user(
        db,
        client=client,
        conversation=conversation,
        remote_jid=remote_jid,
    )
    if not isinstance(user, User):
        return None

    handoff_source = "consultant_core_runtime"
    handoff_trigger_value = "consultant_core_runtime"
    handoff_message_fallback = decision_router.DEFAULT_MANAGER_REQUEST_MESSAGE
    handoff_metadata_source = "consultant_core_runtime"
    if decision_reason == "reschedule_missing_reference" and decision.intent == "reschedule":
        handoff_source = "booking_verification"
        handoff_trigger_value = "reschedule"
        handoff_message_fallback = "Клиент просит изменить время записи."
        handoff_metadata_source = "booking_verification"

    handover_message = body.message if body is not None else None
    if not isinstance(handover_message, str) or not handover_message.strip():
        handover_message = handoff_message_fallback
    else:
        handover_message = handover_message.strip()

    message_metadata = _build_turn_planner_user_message_metadata(payload=payload)
    saved_message = save_message(
        db,
        conversation.id,
        client.id,
        role="user",
        content=(body.message if body is not None and isinstance(body.message, str) else "") or "",
        message_metadata=message_metadata,
    )
    _record_message_decision_meta(
        saved_message,
        action="escalate",
        intent=decision.intent,
        source=handoff_metadata_source,
        fast_intent=False,
    )

    handoff_result = materialize_handover(
        db=db,
        conversation=conversation,
        user=user,
        message=handover_message,
        source=handoff_source,
        intent=decision.intent,
        trigger_type="intent",
        trigger_value=handoff_trigger_value,
        allow_create=allow_handover_create,
        record_decision_trace=_record_decision_trace,
    )
    if not handoff_result.ok or handoff_result.handover is None:
        db.rollback()
        return None

    handover = handoff_result.handover
    handoff_mode = handoff_result.mode
    telegram_sent = handoff_result.telegram_sent
    handover_reopened = handoff_result.handover_reopened
    downstream_tool_decision = (
        "handover_reused"
        if handoff_mode == "reuse"
        else "handover_created"
    )
    if handoff_mode == "create" and payload.client_slug:
        record_escalation_count(payload.client_slug, "intent")
    if handoff_mode == "create":
        _record_decision_trace(
            conversation,
            {
                "stage": "escalation",
                "decision": "created",
                "state": conversation.state,
                "intent": decision.intent,
                "telegram_sent": telegram_sent,
                "handover_reopened": handover_reopened,
            },
        )

    trace_meta: dict[str, object] = {
        "handoff_mode": handoff_mode,
        "telegram_sent": telegram_sent,
    }
    if handover is not None and getattr(handover, "id", None) is not None:
        trace_meta["handover_id"] = str(handover.id)
    if handoff_mode == "create":
        trace_meta["handover_reopened"] = handover_reopened
    _record_decision_trace(
        conversation,
        _build_turn_planner_owner_trace_payload(
            decision=decision,
            stage=REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_STAGE,
            trace_meta=trace_meta,
        ),
    )

    reply_text = decision_router.MSG_ESCALATED
    save_message(
        db,
        conversation.id,
        client.id,
        role="assistant",
        content=reply_text,
        message_metadata={
            "source": "bot",
            "owner_cutover": REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_OWNER,
        },
    )

    instance_id = get_instance_id(
        db,
        client.id,
        branch_id=conversation.branch_id,
        remote_jid=remote_jid,
    )
    simulation_mode = bool(getattr(metadata, "simulation_mode", False))
    transport_simulated = False
    if simulation_mode:
        send_result = ChatFlowAdapter().send_text(
            remote_jid,
            reply_text,
            MessageOptions(
                instance_id=instance_id,
                idempotency_key=getattr(metadata, "messageId", None),
                extra={"simulation_mode": True},
            ),
        )
        transport_simulated = bool(getattr(send_result, "is_ok", lambda: False)())
    else:
        send_result = send_message_safe(
            instance_id or "",
            remote_jid,
            reply_text,
            getattr(metadata, "messageId", None),
            notify_on_failure=True,
            record_metrics=True,
        )
    sent = bool(getattr(send_result, "is_ok", lambda: False)())
    transport_status = "delivered" if sent else "failed"
    transport_reason = None if sent else _resolve_turn_planner_transport_reason(
        send_result,
        instance_id=instance_id,
    )

    artifact = TurnExecutor().build_owner_cutover_artifact(
        decision=decision,
        dialog_state=DialogStateService().normalize(
            {
                "meta": {
                    "writer": "dialog_state_service",
                    "owner_cutover": REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_OWNER,
                }
            }
        ),
        text=reply_text,
        owner_cutover=REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_OWNER,
        transport_status=transport_status,
        transport_reason=transport_reason,
        downstream_tool_decision=downstream_tool_decision,
        reason_code=decision.meta.get("reason") if isinstance(decision.meta, dict) else None,
        stages=[
            "ingress",
            "turn_planner",
            "executor",
            "realizer",
            REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_STAGE,
        ],
        action="escalate",
        source=handoff_metadata_source,
    )
    turn_result = artifact.turn_result
    turn_outcome = artifact.turn_outcome
    _update_message_decision_metadata(
        saved_message,
        {
            "action": "escalate",
            "intent": decision.intent,
            "source": handoff_metadata_source,
            "tool_action": decision.tool_action,
            "needs_manager": True,
            "handoff_mode": handoff_mode,
            "telegram_sent": telegram_sent,
            "transport_simulated": transport_simulated,
            "turn_outcome": turn_outcome.to_metadata(),
            "consultant_core_runtime": artifact.runtime_meta,
        },
    )
    conversation.last_message_at = datetime.now(timezone.utc)
    db.commit()
    return WebhookResponse(
        success=True,
        message=(
            "Turn planner safe explicit handoff sent"
            if sent
            else "Turn planner safe explicit handoff failed"
        ),
        conversation_id=conversation.id,
        bot_response=turn_result.reply.text,
    )


async def _try_handle_turn_planner_safe_info_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    conversation_snapshot: ReasoningCoreConversationSnapshot | None,
    pending_booking_resume_boundary_payload: dict[str, object] | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None
    if (
        conversation_snapshot is not None
        and conversation_snapshot.booking_active
        and conversation_snapshot.reply_slot
        in {
            decision_router.EXPECTED_REPLY_SERVICE,
            decision_router.EXPECTED_REPLY_TIME,
        }
    ):
        return None
    if isinstance(pending_booking_resume_boundary_payload, dict):
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_INFO_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_INFO_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_info_fact_candidate(decision):
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    service_query = _resolve_turn_planner_tool_action_service_query(decision)
    reply_text, reply_meta = info_router._build_info_intent_reply(
        decision.intent,
        service_query=service_query,
        client_slug=payload.client_slug,
        message_text=message_text,
        include_info_bundle=True,
    )
    if not reply_text:
        return None

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text,
        reply_meta=reply_meta,
        trace_meta=None,
        owner_cutover=REASONING_CORE_TURN_PLANNER_INFO_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_INFO_STAGE,
        success_label="Turn planner safe info fact",
    )

async def _try_handle_turn_planner_safe_catalog_fact_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    conversation_snapshot: ReasoningCoreConversationSnapshot | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_CATALOG_FACT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_CATALOG_FACT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_catalog_fact_candidate(decision):
        return None
    if _should_defer_turn_planner_active_booking_side_owner(
        conversation_snapshot=conversation_snapshot,
        decision=decision,
    ):
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    tool_args = decision.tool_args if isinstance(decision.tool_args, dict) else {}
    service_query = _resolve_turn_planner_tool_action_service_query(decision)
    branch_id = _resolve_snapshot_branch_id(preflight_payload)
    tool_result = execute_tool_action(
        db,
        tool_action=decision.tool_action,
        tool_args=tool_args,
        conversation_id=conversation_id,
        branch_id=branch_id,
        client_slug=payload.client_slug,
        service_query=service_query,
        info_sections_hint=decision.pack_refs,
        message_text=message_text,
    )
    reply_meta = (
        dict(tool_result.decision_meta)
        if isinstance(tool_result.decision_meta, dict)
        else None
    )
    if not _should_accept_turn_planner_catalog_result(
        decision,
        response_text=tool_result.response_text,
        handled=tool_result.handled,
        ok=tool_result.ok,
        error_code=tool_result.error_code,
        decision_meta=reply_meta,
    ):
        return None

    trace_meta = dict(tool_result.trace) if isinstance(tool_result.trace, dict) else None
    tool_decision = None
    if isinstance(reply_meta, dict):
        raw_tool_decision = reply_meta.get("tool_decision")
        if isinstance(raw_tool_decision, str):
            tool_decision = raw_tool_decision.strip() or None
    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=tool_result.response_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_CATALOG_FACT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_CATALOG_FACT_STAGE,
        success_label="Turn planner safe catalog fact",
        tool_decision=tool_decision,
    )


async def _try_handle_turn_planner_safe_service_query_fact_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    conversation_snapshot: ReasoningCoreConversationSnapshot | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_SERVICE_QUERY_FACT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_SERVICE_QUERY_FACT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_service_query_fact_candidate(decision):
        return None
    if _should_defer_turn_planner_active_booking_side_owner(
        conversation_snapshot=conversation_snapshot,
        decision=decision,
    ):
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    tool_args = decision.tool_args if isinstance(decision.tool_args, dict) else {}
    service_query = _resolve_turn_planner_tool_action_service_query(decision)
    if service_query is None:
        return None
    branch_id = _resolve_snapshot_branch_id(preflight_payload)
    tool_result = execute_tool_action(
        db,
        tool_action=decision.tool_action,
        tool_args=tool_args,
        conversation_id=conversation_id,
        branch_id=branch_id,
        client_slug=payload.client_slug,
        service_query=service_query,
        info_sections_hint=decision.pack_refs,
        message_text=message_text,
    )
    reply_meta = (
        dict(tool_result.decision_meta)
        if isinstance(tool_result.decision_meta, dict)
        else None
    )
    if not _should_accept_turn_planner_service_query_result(
        decision,
        response_text=tool_result.response_text,
        handled=tool_result.handled,
        ok=tool_result.ok,
        decision_meta=reply_meta,
    ):
        return None

    trace_meta = dict(tool_result.trace) if isinstance(tool_result.trace, dict) else None
    tool_decision = None
    if isinstance(reply_meta, dict):
        raw_tool_decision = reply_meta.get("tool_decision")
        if isinstance(raw_tool_decision, str):
            tool_decision = raw_tool_decision.strip() or None
    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=tool_result.response_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_SERVICE_QUERY_FACT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_SERVICE_QUERY_FACT_STAGE,
        success_label="Turn planner safe service-query fact",
        tool_decision=tool_decision,
    )


async def _try_handle_turn_planner_safe_pricing_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    conversation_snapshot: ReasoningCoreConversationSnapshot | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_PRICING_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_PRICING_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_pricing_collect_candidate(decision):
        return None
    if _should_defer_turn_planner_active_booking_side_owner(
        conversation_snapshot=conversation_snapshot,
        decision=decision,
    ):
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    reply_text, reply_meta = info_router._build_info_intent_reply(
        decision.intent,
        service_query=None,
        client_slug=payload.client_slug,
        message_text=message_text,
        include_info_bundle=True,
    )
    if isinstance(reply_meta, dict):
        reply_meta = dict(reply_meta)
        reply_meta.setdefault("tool_action", decision.tool_action)
    if not _should_accept_turn_planner_pricing_collect_result(
        response_text=reply_text,
        reply_meta=reply_meta,
    ):
        return None

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=None,
        owner_cutover=REASONING_CORE_TURN_PLANNER_PRICING_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_PRICING_COLLECT_STAGE,
        success_label="Turn planner safe pricing collect",
        tool_decision="service_clarify",
        followup_type="service_choice",
        question_reason="service_clarify",
    )


async def _try_handle_turn_planner_safe_duration_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    conversation_snapshot: ReasoningCoreConversationSnapshot | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_DURATION_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_DURATION_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_duration_collect_candidate(decision):
        return None
    if _should_defer_turn_planner_active_booking_side_owner(
        conversation_snapshot=conversation_snapshot,
        decision=decision,
    ):
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    if not isinstance(message_text, str) or not message_text.strip():
        return None

    reply_decision = info_router.get_pack_decision(
        message_text,
        client_slug=payload.client_slug,
    )
    if reply_decision is None or not isinstance(reply_decision.response, str):
        return None

    reply_meta = dict(reply_decision.meta) if isinstance(reply_decision.meta, dict) else None
    if isinstance(reply_meta, dict):
        reply_meta.setdefault("tool_action", decision.tool_action)
    if not _should_accept_turn_planner_duration_collect_result(
        response_text=reply_decision.response,
        reply_action=getattr(reply_decision, "action", None),
        reply_meta=reply_meta,
    ):
        return None

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_decision.response.strip(),
        reply_meta=reply_meta,
        trace_meta=None,
        owner_cutover=REASONING_CORE_TURN_PLANNER_DURATION_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_DURATION_COLLECT_STAGE,
        success_label="Turn planner safe duration collect",
        tool_decision="service_clarify",
        followup_type="service_choice",
        question_reason="service_clarify",
    )


async def _try_handle_turn_planner_safe_bookability_time_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_BOOKABILITY_TIME_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_BOOKABILITY_TIME_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_bookability_time_collect_candidate(decision):
        return None

    slots = decision.slots if isinstance(decision.slots, dict) else {}
    service_query = slots.get("service")
    normalized_service_query = (
        service_query.strip()
        if isinstance(service_query, str) and service_query.strip()
        else None
    )

    reply_text = decision_router.MSG_BOOKING_PENDING_QUESTION_TIME_GUIDANCE
    if not isinstance(reply_text, str) or not reply_text.strip():
        return None

    pending_question_act = (
        decision.meta.get("pending_question_act") if isinstance(decision.meta, dict) else None
    )
    if isinstance(pending_question_act, str):
        pending_question_act = pending_question_act.strip() or None
    pending_question_target = (
        decision.pending_question_contract.pending_question_target
        if decision.pending_question_contract.pending_question_target
        else None
    )
    reply_meta: dict[str, object] = {
        "source": "booking_slot_guidance",
        "tool_action": decision.tool_action,
    }
    trace_meta: dict[str, object] = {
        "validation_error": "semantic_temporal_scope_missing",
        "policy_core_guard_recovery": "semantic_temporal_scope_missing_slot_guidance",
    }
    if isinstance(pending_question_act, str) and pending_question_act.strip():
        normalized_act = pending_question_act.strip()
        reply_meta["pending_question_act"] = normalized_act
        trace_meta["pending_question_act"] = normalized_act
    if isinstance(pending_question_target, str) and pending_question_target.strip():
        normalized_target = pending_question_target.strip()
        reply_meta["pending_question_target"] = normalized_target
        trace_meta["pending_question_target"] = normalized_target

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_BOOKABILITY_TIME_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_BOOKABILITY_TIME_COLLECT_STAGE,
        success_label="Turn planner safe bookability time collect",
        followup_type="time",
        question_reason="booking_slot_guidance",
        grounded_referents={"service": normalized_service_query}
        if normalized_service_query
        else None,
        booking_slot_values={"service": normalized_service_query}
        if normalized_service_query
        else None,
        booking_last_question="datetime",
    )


async def _try_handle_turn_planner_safe_active_name_time_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    conversation_snapshot: ReasoningCoreConversationSnapshot | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_ACTIVE_NAME_TIME_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_ACTIVE_NAME_TIME_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_active_name_time_collect_candidate(decision):
        return None

    slots = decision.slots if isinstance(decision.slots, dict) else {}
    current_datetime = (
        conversation_snapshot.booking_datetime_value
        if conversation_snapshot is not None
        else None
    )
    normalized_current_datetime = (
        current_datetime.strip()
        if isinstance(current_datetime, str) and current_datetime.strip()
        else None
    )
    alternate_datetime = slots.get("datetime")
    normalized_alternate_datetime = (
        alternate_datetime.strip()
        if isinstance(alternate_datetime, str) and alternate_datetime.strip()
        else None
    )
    reply_text = decision_router._build_active_name_time_availability_followup_response(
        current_slot=normalized_current_datetime,
        alternate_slot=normalized_alternate_datetime,
    )
    if not isinstance(reply_text, str) or not reply_text.strip():
        return None

    pending_contract = decision.pending_question_contract
    pending_question_act = (
        decision.meta.get("pending_question_act") if isinstance(decision.meta, dict) else None
    )
    pending_question_target = (
        pending_contract.pending_question_target.strip()
        if pending_contract.pending_question_target
        else None
    )
    active_question_relation = (
        pending_contract.active_question_relation.strip()
        if pending_contract.active_question_relation
        else None
    )
    reply_meta: dict[str, object] = {
        "source": "booking_time_availability_followup",
        "tool_action": decision.tool_action,
        "pending_question_owner": "booking_time_availability_followup",
    }
    trace_meta: dict[str, object] = {
        "pending_question_owner": "booking_time_availability_followup",
    }
    if pending_question_act:
        reply_meta["pending_question_act"] = pending_question_act
        trace_meta["pending_question_act"] = pending_question_act
    if pending_question_target:
        reply_meta["pending_question_target"] = pending_question_target
        trace_meta["pending_question_target"] = pending_question_target
    if active_question_relation:
        reply_meta["pending_question_interaction"] = active_question_relation
        reply_meta["active_question_relation"] = active_question_relation
        trace_meta["active_question_relation"] = active_question_relation
    if normalized_current_datetime:
        reply_meta["current_datetime"] = normalized_current_datetime
        trace_meta["current_datetime"] = normalized_current_datetime
    if normalized_alternate_datetime:
        reply_meta["alternate_datetime"] = normalized_alternate_datetime
        trace_meta["alternate_datetime"] = normalized_alternate_datetime

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_ACTIVE_NAME_TIME_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_ACTIVE_NAME_TIME_COLLECT_STAGE,
        success_label="Turn planner safe active-name time collect",
        followup_type="name",
        question_reason="booking_time_availability_followup",
        grounded_referents={"service": conversation_snapshot.service_referent}
        if conversation_snapshot is not None
        and isinstance(conversation_snapshot.service_referent, str)
        and conversation_snapshot.service_referent.strip()
        else None,
        booking_slot_values={
            key: value
            for key, value in {
                "service": (
                    conversation_snapshot.service_referent
                    if conversation_snapshot is not None
                    else None
                ),
                "datetime": normalized_current_datetime,
            }.items()
            if isinstance(value, str) and value.strip()
        },
        booking_last_question="name",
    )


async def _try_handle_turn_planner_safe_specialist_name_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_SPECIALIST_NAME_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_SPECIALIST_NAME_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_specialist_name_collect_candidate(decision):
        return None

    slots = decision.slots if isinstance(decision.slots, dict) else {}
    service_query = slots.get("service")
    normalized_service_query = (
        service_query.strip()
        if isinstance(service_query, str) and service_query.strip()
        else None
    )
    if normalized_service_query is None:
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    reply_text, specialist_meta = decision_router._build_specialist_availability_followup_response(
        service_query=normalized_service_query,
        client_slug=payload.client_slug,
        message_text=message_text,
        requested_slot="name",
    )
    if not isinstance(reply_text, str) or not reply_text.strip():
        return None

    pending_contract = decision.pending_question_contract
    pending_question_act = (
        decision.meta.get("pending_question_act") if isinstance(decision.meta, dict) else None
    )
    if isinstance(pending_question_act, str):
        pending_question_act = pending_question_act.strip() or None
    pending_question_target = (
        pending_contract.pending_question_target.strip()
        if pending_contract.pending_question_target
        else None
    )
    active_question_relation = (
        pending_contract.active_question_relation.strip()
        if pending_contract.active_question_relation
        else None
    )
    temporal_scope = (
        decision.meta.get("temporal_scope") if isinstance(decision.meta, dict) else None
    )

    reply_meta: dict[str, object] = {
        "source": "booking_specialist_availability_followup",
        "tool_action": decision.tool_action,
        "pending_question_owner": "booking_specialist_availability_followup",
    }
    trace_meta: dict[str, object] = {
        "pending_question_owner": "booking_specialist_availability_followup",
    }
    if pending_question_act:
        reply_meta["pending_question_act"] = pending_question_act
        trace_meta["pending_question_act"] = pending_question_act
    if pending_question_target:
        reply_meta["pending_question_target"] = pending_question_target
        trace_meta["pending_question_target"] = pending_question_target
    if active_question_relation:
        reply_meta["pending_question_interaction"] = active_question_relation
        reply_meta["active_question_relation"] = active_question_relation
        trace_meta["active_question_relation"] = active_question_relation
    if isinstance(temporal_scope, str) and temporal_scope.strip():
        normalized_temporal_scope = temporal_scope.strip()
        reply_meta["temporal_scope"] = normalized_temporal_scope
        trace_meta["temporal_scope"] = normalized_temporal_scope
    filtered_meta = _filter_specialist_followup_helper_meta(specialist_meta)
    if filtered_meta:
        reply_meta.update(filtered_meta)
        trace_meta.update(filtered_meta)

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_SPECIALIST_NAME_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_SPECIALIST_NAME_COLLECT_STAGE,
        success_label="Turn planner safe specialist name collect",
        followup_type="name",
        question_reason="booking_specialist_availability_followup",
        grounded_referents={"service": normalized_service_query},
        booking_slot_values={
            key: value
            for key, value in {
                "service": normalized_service_query,
                "datetime": slots.get("datetime"),
            }.items()
            if isinstance(value, str) and value.strip()
        },
        booking_last_question="name",
    )


async def _try_handle_turn_planner_safe_specialist_datetime_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_SPECIALIST_DATETIME_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_SPECIALIST_DATETIME_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_specialist_datetime_collect_candidate(decision):
        return None

    slots = decision.slots if isinstance(decision.slots, dict) else {}
    service_query = slots.get("service")
    normalized_service_query = (
        service_query.strip()
        if isinstance(service_query, str) and service_query.strip()
        else None
    )
    if normalized_service_query is None:
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    reply_text, specialist_meta = decision_router._build_specialist_availability_followup_response(
        service_query=normalized_service_query,
        client_slug=payload.client_slug,
        message_text=message_text,
        requested_slot="time",
    )
    if not isinstance(reply_text, str) or not reply_text.strip():
        return None

    pending_question_act = (
        decision.meta.get("pending_question_act") if isinstance(decision.meta, dict) else None
    )
    if isinstance(pending_question_act, str):
        pending_question_act = pending_question_act.strip() or None
    temporal_scope = (
        decision.meta.get("temporal_scope") if isinstance(decision.meta, dict) else None
    )

    reply_meta: dict[str, object] = {
        "source": "booking_specialist_availability_followup",
        "tool_action": decision.tool_action,
        "pending_question_owner": "booking_specialist_availability_followup",
    }
    trace_meta: dict[str, object] = {
        "pending_question_owner": "booking_specialist_availability_followup",
    }
    if pending_question_act:
        reply_meta["pending_question_act"] = pending_question_act
        trace_meta["pending_question_act"] = pending_question_act
    reply_meta["pending_question_target"] = "specialist"
    trace_meta["pending_question_target"] = "specialist"
    reply_meta["pending_question_interaction"] = "specialist_availability_followup"
    reply_meta["active_question_relation"] = "specialist_availability_followup"
    trace_meta["active_question_relation"] = "specialist_availability_followup"
    if isinstance(temporal_scope, str) and temporal_scope.strip():
        normalized_temporal_scope = temporal_scope.strip()
        reply_meta["temporal_scope"] = normalized_temporal_scope
        trace_meta["temporal_scope"] = normalized_temporal_scope

    filtered_meta = _filter_specialist_followup_helper_meta(specialist_meta)
    if filtered_meta:
        reply_meta.update(filtered_meta)
        trace_meta.update(filtered_meta)

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_SPECIALIST_DATETIME_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_SPECIALIST_DATETIME_COLLECT_STAGE,
        success_label="Turn planner safe specialist datetime collect",
        followup_type="time",
        question_reason="booking_specialist_availability_followup",
        grounded_referents={"service": normalized_service_query},
        booking_slot_values={"service": normalized_service_query},
        booking_last_question="datetime",
    )


async def _try_handle_turn_planner_safe_service_choice_specialist_time_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_TIME_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_TIME_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_service_choice_specialist_time_collect_candidate(decision):
        return None

    slots = decision.slots if isinstance(decision.slots, dict) else {}
    service_query = slots.get("service")
    normalized_service_query = (
        service_query.strip()
        if isinstance(service_query, str) and service_query.strip()
        else None
    )
    if normalized_service_query is None:
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    reply_text, specialist_meta = decision_router._build_specialist_availability_followup_response(
        service_query=normalized_service_query,
        client_slug=payload.client_slug,
        message_text=message_text,
        requested_slot="time",
    )
    if not isinstance(reply_text, str) or not reply_text.strip():
        return None

    pending_question_act = (
        decision.meta.get("pending_question_act") if isinstance(decision.meta, dict) else None
    )
    if isinstance(pending_question_act, str):
        pending_question_act = pending_question_act.strip() or None
    temporal_scope = (
        decision.meta.get("temporal_scope") if isinstance(decision.meta, dict) else None
    )

    reply_meta: dict[str, object] = {
        "action": "booking_prompt",
        "intent": "booking",
        "source": "booking_specialist_availability_followup",
        "action_source": "booking_specialist_availability_followup",
        "tool_action": decision.tool_action,
        "pending_question_owner": "booking_specialist_availability_followup",
    }
    trace_meta: dict[str, object] = {
        "pending_question_owner": "booking_specialist_availability_followup",
    }
    if pending_question_act:
        reply_meta["pending_question_act"] = pending_question_act
        trace_meta["pending_question_act"] = pending_question_act
    reply_meta["pending_question_target"] = "specialist"
    trace_meta["pending_question_target"] = "specialist"
    reply_meta["pending_question_interaction"] = "specialist_availability_followup"
    reply_meta["active_question_relation"] = "specialist_availability_followup"
    trace_meta["active_question_relation"] = "specialist_availability_followup"
    if isinstance(temporal_scope, str) and temporal_scope.strip():
        normalized_temporal_scope = temporal_scope.strip()
        reply_meta["temporal_scope"] = normalized_temporal_scope
        trace_meta["temporal_scope"] = normalized_temporal_scope

    filtered_meta = _filter_specialist_followup_helper_meta(specialist_meta)
    if filtered_meta:
        reply_meta.update(filtered_meta)
        trace_meta.update(filtered_meta)

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_TIME_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_TIME_COLLECT_STAGE,
        success_label="Turn planner safe service-choice specialist time collect",
        followup_type="time",
        question_reason="booking_specialist_availability_followup",
        grounded_referents={"service": normalized_service_query},
        booking_slot_values={"service": normalized_service_query},
        booking_last_question="datetime",
        outcome_action="booking_prompt",
        outcome_source="booking_specialist_availability_followup",
    )


async def _try_handle_turn_planner_safe_service_choice_specialist_daypart_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_DAYPART_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_DAYPART_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_service_choice_specialist_daypart_collect_candidate(decision):
        return None

    slots = decision.slots if isinstance(decision.slots, dict) else {}
    service_query = slots.get("service")
    normalized_service_query = (
        service_query.strip()
        if isinstance(service_query, str) and service_query.strip()
        else None
    )
    if normalized_service_query is None:
        return None
    datetime_value = slots.get("datetime")
    normalized_datetime_value = (
        datetime_value.strip()
        if isinstance(datetime_value, str) and datetime_value.strip()
        else None
    )
    if normalized_datetime_value is None:
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    reply_text, specialist_meta = decision_router._build_specialist_availability_followup_response(
        service_query=normalized_service_query,
        client_slug=payload.client_slug,
        message_text=message_text,
        requested_slot="time",
    )
    if not isinstance(reply_text, str) or not reply_text.strip():
        return None

    pending_question_act = (
        decision.meta.get("pending_question_act") if isinstance(decision.meta, dict) else None
    )
    if isinstance(pending_question_act, str):
        pending_question_act = pending_question_act.strip() or None
    temporal_scope = (
        decision.meta.get("temporal_scope") if isinstance(decision.meta, dict) else None
    )

    reply_meta: dict[str, object] = {
        "action": "booking_prompt",
        "intent": "booking",
        "source": "booking_specialist_availability_followup",
        "action_source": "booking_specialist_availability_followup",
        "tool_action": decision.tool_action,
        "pending_question_owner": "booking_specialist_availability_followup",
    }
    trace_meta: dict[str, object] = {
        "pending_question_owner": "booking_specialist_availability_followup",
        "booking_datetime": normalized_datetime_value,
    }
    if pending_question_act:
        reply_meta["pending_question_act"] = pending_question_act
        trace_meta["pending_question_act"] = pending_question_act
    reply_meta["pending_question_target"] = "specialist"
    trace_meta["pending_question_target"] = "specialist"
    reply_meta["pending_question_interaction"] = "specialist_availability_followup"
    reply_meta["active_question_relation"] = "specialist_availability_followup"
    trace_meta["active_question_relation"] = "specialist_availability_followup"
    reply_meta["booking_datetime"] = normalized_datetime_value
    if isinstance(temporal_scope, str) and temporal_scope.strip():
        normalized_temporal_scope = temporal_scope.strip()
        reply_meta["temporal_scope"] = normalized_temporal_scope
        trace_meta["temporal_scope"] = normalized_temporal_scope

    filtered_meta = _filter_specialist_followup_helper_meta(specialist_meta)
    if filtered_meta:
        reply_meta.update(filtered_meta)
        trace_meta.update(filtered_meta)

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_DAYPART_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_SERVICE_CHOICE_SPECIALIST_DAYPART_COLLECT_STAGE,
        success_label="Turn planner safe service-choice specialist daypart collect",
        followup_type="time",
        question_reason="booking_specialist_availability_followup",
        grounded_referents={"service": normalized_service_query},
        booking_slot_values={
            "service": normalized_service_query,
            "datetime": normalized_datetime_value,
        },
        booking_last_question="datetime",
        outcome_action="booking_prompt",
        outcome_source="booking_specialist_availability_followup",
    )


async def _try_handle_turn_planner_safe_master_query_fact_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_FACT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_FACT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_master_query_fact_candidate(decision):
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    service_query = _resolve_turn_planner_tool_action_service_query(decision)
    if service_query is None:
        return None

    resolution = resolve_master_intent(
        message_text=message_text,
        client_slug=payload.client_slug,
        service_query=service_query,
        force_master_intent=True,
    )
    reply_decision = build_master_reply_from_pack(
        client_slug=payload.client_slug,
        message_text=message_text,
        resolution=resolution,
    )
    if reply_decision is None:
        return None

    reply_meta = dict(reply_decision.meta) if isinstance(reply_decision.meta, dict) else None
    if isinstance(reply_meta, dict):
        reply_meta.setdefault("tool_action", decision.tool_action)
    reply_text = reply_decision.response
    reply_action = getattr(reply_decision, "action", None)
    if not _should_accept_turn_planner_master_query_result(
        response_text=reply_text,
        reply_action=reply_action,
        reply_meta=reply_meta,
    ):
        if not _should_accept_turn_planner_master_query_service_not_found_collect_result(
            response_text=reply_text,
            reply_action=reply_action,
            reply_meta=reply_meta,
        ):
            return None
        question_reason = None
        if isinstance(reply_meta, dict):
            raw_reason = reply_meta.get("clarify_reason")
            if isinstance(raw_reason, str):
                question_reason = raw_reason.strip() or None
        collect_override = policy_core_route_snapshot.to_override()
        collect_override["action"] = "collect"
        collect_override["tool_action"] = "collect"
        collect_override["tool_args"] = {}
        collect_override["slots"] = {}
        collect_override["next_question"] = "service"
        collect_override["open_questions"] = ["service"]
        collect_override["subject_kind"] = "service"
        collect_override["resolution_mode"] = "clarify_missing_subject"
        collect_override["pending_question_target"] = "service"
        if question_reason:
            collect_override["reason"] = question_reason
        planner = TurnPlanner()
        try:
            collect_decision = planner.build_from_policy_override(
                collect_override,
                interaction_owner=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_SERVICE_NOT_FOUND_OWNER,
                interaction_relation=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_SERVICE_NOT_FOUND_STAGE,
            )
        except (AttributeError, TypeError, ValueError):
            return None
        if isinstance(reply_meta, dict):
            reply_meta["tool_action"] = collect_decision.tool_action
        return _finalize_turn_planner_owner_cutover(
            payload=payload,
            db=db,
            client_id=client_id,
            preflight_payload=preflight_payload,
            conversation_id=conversation_id,
            decision=collect_decision,
            reply_text=reply_text.strip(),
            reply_meta=reply_meta,
            trace_meta=None,
            owner_cutover=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_SERVICE_NOT_FOUND_OWNER,
            stage=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_SERVICE_NOT_FOUND_STAGE,
            success_label="Turn planner safe master-query service-not-found collect",
            tool_decision="service_not_found",
            followup_type="service_choice",
            question_reason=question_reason or "master_service_not_found",
        )

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=None,
        owner_cutover=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_FACT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_FACT_STAGE,
        success_label="Turn planner safe master-query fact",
        tool_decision="service_match",
    )


async def _try_handle_turn_planner_safe_master_query_collect_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_COLLECT_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_COLLECT_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_master_query_collect_candidate(decision):
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    resolution = resolve_master_intent(
        message_text=message_text,
        client_slug=payload.client_slug,
        service_query=None,
        force_master_intent=True,
    )
    reply_decision = build_master_reply_from_pack(
        client_slug=payload.client_slug,
        message_text=message_text,
        resolution=resolution,
    )
    if reply_decision is None:
        return None

    reply_meta = dict(reply_decision.meta) if isinstance(reply_decision.meta, dict) else None
    if isinstance(reply_meta, dict):
        reply_meta.setdefault("tool_action", decision.tool_action)
    reply_text = reply_decision.response
    reply_action = getattr(reply_decision, "action", None)
    if not _should_accept_turn_planner_master_query_collect_result(
        response_text=reply_text,
        reply_action=reply_action,
        reply_meta=reply_meta,
    ):
        return None

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation_id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=None,
        owner_cutover=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_COLLECT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_MASTER_QUERY_COLLECT_STAGE,
        success_label="Turn planner safe master-query collect",
        tool_decision="service_clarify",
        followup_type="service_choice",
        question_reason="service_clarify",
    )


async def _try_handle_turn_planner_safe_booking_verification_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    conversation_snapshot: ReasoningCoreConversationSnapshot | None,
    enqueue_only: bool,
    skip_persist: bool,
    policy_core_route_snapshot: object | None,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or policy_core_route_snapshot is None:
        return None

    source_conversation_id = conversation_id
    if source_conversation_id is None and conversation_snapshot is not None:
        if conversation_snapshot.state == "bot_active":
            source_conversation_id = conversation_snapshot.conversation_id
    if source_conversation_id is None:
        return None

    if conversation_snapshot is not None:
        reply_slot_token = conversation_snapshot.reply_slot
    else:
        reply_slot_token = None

    planner = TurnPlanner()
    try:
        decision = planner.build_from_policy_override(
            policy_core_route_snapshot.to_override(),
            interaction_owner=REASONING_CORE_TURN_PLANNER_BOOKING_VERIFICATION_OWNER,
            interaction_relation=REASONING_CORE_TURN_PLANNER_BOOKING_VERIFICATION_STAGE,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if not _is_turn_planner_safe_booking_verification_candidate(decision):
        return None

    if reply_slot_token in {
        decision_router.EXPECTED_REPLY_SERVICE,
        decision_router.EXPECTED_REPLY_TIME,
        decision_router.EXPECTED_REPLY_NAME,
    }:
        booking_state: dict[str, object] = {}
        if conversation_snapshot is not None:
            if conversation_snapshot.service_referent:
                booking_state["service"] = conversation_snapshot.service_referent
            if conversation_snapshot.booking_datetime_value:
                booking_state["datetime"] = conversation_snapshot.booking_datetime_value
            if conversation_snapshot.booking_active:
                booking_state["active"] = True
        missing_slot = decision_router._first_missing_booking_slot(
            booking_state,
            client_slug=payload.client_slug,
        )
        if missing_slot in {
            "service",
            "datetime",
            "name",
        } and not decision_router._booking_has_reference(booking_state):
            return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    tool_args = decision.tool_args if isinstance(decision.tool_args, dict) else {}
    branch_id = _resolve_snapshot_branch_id(preflight_payload)
    tool_result = execute_tool_action(
        db,
        tool_action=decision.tool_action,
        tool_args=tool_args,
        conversation_id=source_conversation_id,
        branch_id=branch_id,
        client_slug=payload.client_slug,
        service_query=None,
        info_sections_hint=decision.pack_refs,
        message_text=message_text,
    )
    reply_meta = (
        dict(tool_result.decision_meta)
        if isinstance(tool_result.decision_meta, dict)
        else None
    )
    if not _should_accept_turn_planner_booking_verification_result(
        response_text=tool_result.response_text,
        handled=tool_result.handled,
        ok=tool_result.ok,
        error_code=tool_result.error_code,
        decision_meta=reply_meta,
    ):
        return None

    trace_meta = dict(tool_result.trace) if isinstance(tool_result.trace, dict) else None
    downstream_tool_decision = None
    if isinstance(reply_meta, dict):
        raw_tool_decision = reply_meta.get("tool_decision")
        if isinstance(raw_tool_decision, str):
            downstream_tool_decision = raw_tool_decision.strip() or None
    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=source_conversation_id,
        decision=decision,
        reply_text=tool_result.response_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_BOOKING_VERIFICATION_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_BOOKING_VERIFICATION_STAGE,
        success_label="Turn planner safe booking verification fact",
        tool_decision=downstream_tool_decision,
    )


async def _try_handle_turn_planner_safe_booking_prompt_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    conversation_snapshot: ReasoningCoreConversationSnapshot | None,
    batch_messages: list[str] | None,
    enqueue_only: bool,
    skip_persist: bool,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or conversation_snapshot is None:
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    has_media = bool(body is not None and body.mediaData)
    if has_media:
        return None
    if message_text and decision_router._is_style_reference_request(message_text, has_media=False):
        return None
    if message_text and decision_router._looks_like_booking_verification_request(message_text):
        return None
    if message_text and decision_router._looks_like_booking_reschedule_request(
        message_text,
        client_slug=payload.client_slug,
    ):
        return None

    client = _resolve_turn_planner_owner_client(
        db,
        payload=payload,
        client_id=client_id,
        preflight_payload=preflight_payload,
    )
    if not isinstance(client, Client):
        return None

    metadata = body.metadata if body is not None else None
    remote_jid = getattr(metadata, "remoteJid", None)
    if not isinstance(remote_jid, str) or not remote_jid.strip():
        return None

    branch_id = _resolve_snapshot_branch_id(preflight_payload)
    source_conversation_id = conversation_id or conversation_snapshot.conversation_id
    conversation = _ensure_turn_planner_owner_conversation(
        db,
        client=client,
        remote_jid=remote_jid.strip(),
        branch_id=branch_id,
        conversation_id=source_conversation_id,
    )
    if not isinstance(conversation, Conversation):
        return None

    routing = decision_router.ROUTING_MATRIX.get(conversation.state, {})
    if not routing.get("allow_bot_reply", False) or not routing.get("allow_booking_flow", False):
        return None

    context = context_manager_router._get_conversation_context(conversation)
    reply_slot_token = conversation_snapshot.reply_slot
    intent_queue = DialogStateService().get_intent_queue(context)
    booking_state = decision_router._get_booking_context(context)
    booking_state = dict(booking_state) if isinstance(booking_state, dict) else {}
    current_goal = context.get("current_goal")
    normalized_goal = (
        current_goal.strip() if isinstance(current_goal, str) and current_goal.strip() else None
    )
    context_manager = decision_router._get_context_manager(context)
    refusal_flags = (
        context_manager.get("refusal_flags") if isinstance(context_manager, dict) else None
    )
    now = datetime.now(timezone.utc)

    route_source: str | None = None
    route_reason: str | None = None
    policy_slot_values: dict[str, str] = {}
    clear_intent_queue = False
    clear_service_hint = False
    extra_trace_payloads: list[dict[str, object]] = []
    reply_meta: dict[str, object] = {
        "action": "booking_prompt",
        "intent": "booking",
        "tool_action": "collect",
    }
    trace_meta: dict[str, object] = {}
    expected_reply_time_progression_meta: dict[str, object] | None = None
    pending_collect_resume_meta: dict[str, object] | None = None

    def _ensure_pending_collect_resume_meta() -> bool:
        nonlocal context, pending_collect_resume_meta
        if pending_collect_resume_meta is not None:
            return True
        pending_collect_resume_meta = _restore_turn_planner_collect_owner_bot_active_state(
            db=db,
            conversation=conversation,
        )
        if pending_collect_resume_meta is None:
            return False
        if pending_collect_resume_meta:
            reply_meta.update(pending_collect_resume_meta)
            extra_trace_payloads.append(
                {
                    "stage": "collect_owner_reactivation",
                    "decision": "reactivate_collect_owner",
                    "reason": "booking_collect_reentry",
                    "mode": pending_collect_resume_meta.get("pending_collect_resume_mode"),
                    "state_before": pending_collect_resume_meta.get(
                        "pending_collect_resume_state_before"
                    ),
                    "state_after": pending_collect_resume_meta.get(
                        "pending_collect_resume_state_after"
                    ),
                }
            )
            context = context_manager_router._get_conversation_context(conversation)
        else:
            pending_collect_resume_meta = {}
        return True

    if (
        reply_slot_token == decision_router.EXPECTED_REPLY_INTENT_CHOICE
        and intent_queue
        and isinstance(message_text, str)
        and message_text.strip()
    ):
        intent_queue_choice = None
        if intent_queue == ["booking"]:
            intent_queue_choice = "booking"
        else:
            intent_queue_choice = decision_router._select_intent_from_queue(
                intent_queue,
                [],
                message_text=message_text,
            )
        if intent_queue_choice and intent_queue_choice != "booking":
            return None
        if intent_queue_choice == "booking":
            route_source = "intent_queue"
            route_reason = "intent_queue_booking"
            clear_intent_queue = True
            extra_trace_payloads.append(
                {
                    "stage": "intent_queue",
                    "decision": "dequeue",
                    "source": "intent_queue",
                    "chosen_intent": "booking",
                    "remaining_queue": [],
                    "expected_reply_choice": "booking",
                    "expected_reply_next": "booking",
                }
            )
            reply_meta.update(
                {
                    "source": "intent_queue",
                    "action_source": "intent_queue",
                    "intent_queue_choice": "booking",
                    "intent_queue_remaining": [],
                    "expected_reply_choice": "booking",
                    "expected_reply_next": "booking",
                }
            )
            trace_meta.update(
                {
                    "source_route": "intent_queue",
                    "intent_queue_choice": "booking",
                }
            )

    booking_messages = [
        message
        for message in (batch_messages or [])
        if isinstance(message, str) and message.strip()
    ]
    if not booking_messages and isinstance(message_text, str) and message_text.strip():
        booking_messages = [message_text]

    question_contract_time_slot_constraint = False
    if (
        conversation_snapshot.booking_active
        and reply_slot_token == decision_router.EXPECTED_REPLY_TIME
        and isinstance(message_text, str)
        and message_text.strip()
    ):
        expected_time_reply_type = decision_router.EXPECTED_REPLY_TIME
        expected_reply_key = "expected_reply_" + "type"
        matched_time_slot, matched_time_value, _ = decision_router._match_expected_reply(
            **{
                expected_reply_key: expected_time_reply_type,
                "message_text": message_text,
                "client_slug": payload.client_slug,
            }
        )
        question_contract_time_slot_constraint = bool(
            matched_time_slot
            and isinstance(matched_time_value, str)
            and matched_time_value.strip()
            and decision_router._is_time_slot_constraint_candidate(
                message_text=message_text,
                candidate_value=matched_time_value.strip(),
                client_slug=payload.client_slug,
            )
        )

    followup_reason = "booking_prompt"
    if (
        route_source is None
        and conversation_snapshot.booking_active
        and reply_slot_token
        in {
            decision_router.EXPECTED_REPLY_SERVICE,
            decision_router.EXPECTED_REPLY_TIME,
        }
        and isinstance(message_text, str)
        and message_text.strip()
    ):
        booking_service_query = (
            booking_state.get("service")
            if isinstance(booking_state.get("service"), str) and booking_state.get("service").strip()
            else None
        )
        suppress_generic_info_interrupt = False
        if reply_slot_token == decision_router.EXPECTED_REPLY_SERVICE and not booking_service_query:
            from app.services.booking_signal_service import (
                extract_time_token,
                has_explicit_date_signal,
                normalize_resolved_datetime_value,
            )
            from app.services.info_signal_service import signal_any_match

            normalized_interrupt_text = decision_router.normalize_for_matching(message_text)
            suppress_generic_info_interrupt = bool(
                signal_any_match(
                    normalized_interrupt_text,
                    payload.client_slug,
                    "booking_request",
                    "booking_keywords",
                )
                and (
                    has_explicit_date_signal(message_text)
                    or extract_time_token(message_text)
                    or normalize_resolved_datetime_value(
                        message_text,
                        normalized_text=normalized_interrupt_text,
                    )
                )
            )
        info_interrupt_intents, info_interrupt_meta = info_router._detect_info_class_intents(
            message_text,
            intent_decomp_set=set(),
            client_slug=payload.client_slug,
            service_query=booking_service_query,
        )
        explicit_hours_interrupt = bool(
            "hours" in info_interrupt_intents
            and isinstance(info_interrupt_meta, dict)
            and isinstance(info_interrupt_meta.get("info_signals"), dict)
            and info_interrupt_meta["info_signals"].get("hours") is True
            and info_interrupt_meta["info_signals"].get("duration") is not True
        )
        if not explicit_hours_interrupt:
            explicit_hours_interrupt = bool(
                "hours" in info_interrupt_intents
                and decision_router._has_explicit_location_or_hours_request(
                    message_text,
                    client_slug=payload.client_slug,
                    strict=decision_router._semantic_arbitration_enabled(),
                )
            )
        interrupt_intent_priority = (
            "pricing",
            "duration",
            *sorted(REASONING_CORE_TURN_PLANNER_INFO_INTENTS),
        )
        interrupt_intent = next(
            (
                intent_name
                for intent_name in interrupt_intent_priority
                if intent_name in info_interrupt_intents
            ),
            None,
        )
        if explicit_hours_interrupt and interrupt_intent == "duration":
            interrupt_intent = "hours"
        if (
            suppress_generic_info_interrupt
            and interrupt_intent in REASONING_CORE_TURN_PLANNER_INFO_INTENTS
        ):
            interrupt_intent = None
        if (
            question_contract_time_slot_constraint
            and interrupt_intent in REASONING_CORE_TURN_PLANNER_INFO_INTENTS
        ):
            interrupt_intent = None
        if interrupt_intent is not None:
            interrupt_requires_service_query = interrupt_intent in {
                "pricing",
                "duration",
                "promotions",
            }
            unsupported_interrupt_intents = info_interrupt_intents - set(interrupt_intent_priority)
            interrupt_service_query = None
            if interrupt_requires_service_query:
                interrupt_service_query = decision_router._extract_service_hint(
                    message_text,
                    payload.client_slug,
                )
                if not interrupt_service_query:
                    interrupt_service_query = booking_service_query
                if not interrupt_service_query:
                    interrupt_service_query = decision_router._get_recent_service_hint(context, now)
            if (
                not unsupported_interrupt_intents
                and (
                    (
                        interrupt_requires_service_query
                        and isinstance(interrupt_service_query, str)
                        and interrupt_service_query.strip()
                    )
                    or not interrupt_requires_service_query
                )
            ):
                if interrupt_requires_service_query:
                    interrupt_service_query = interrupt_service_query.strip()
                interrupt_slot_label = (
                    "service"
                    if reply_slot_token == decision_router.EXPECTED_REPLY_SERVICE
                    else "time"
                )
                interrupt_followup_type = reply_slot_token
                interrupt_context = context
                interrupt_booking_state = dict(booking_state)
                if interrupt_booking_state.get("active") is not True:
                    interrupt_booking_state["active"] = True
                    interrupt_booking_state["started_at"] = now.isoformat()
                if booking_messages:
                    interrupt_booking_state = decision_router._update_booking_from_messages(
                        interrupt_booking_state,
                        booking_messages,
                        client_slug=payload.client_slug,
                    )
                if not interrupt_booking_state.get("service"):
                    interrupt_booking_state["service"] = interrupt_service_query
                interrupt_booking_state, _ = decision_router._next_booking_prompt(
                    interrupt_booking_state,
                    refusal_flags=refusal_flags if isinstance(refusal_flags, dict) else None,
                    client_slug=payload.client_slug,
                )
                interrupt_booking_last_question = (
                    interrupt_booking_state.get("last_question")
                    if isinstance(interrupt_booking_state.get("last_question"), str)
                    and interrupt_booking_state.get("last_question").strip()
                    else None
                )
                interrupt_booking_slot_values = _build_turn_planner_booking_prompt_slot_values(
                    interrupt_booking_state
                )
                if interrupt_booking_last_question is not None:
                    interrupt_followup_candidate = (
                        decision_router._expected_reply_for_booking_question(
                            interrupt_booking_last_question
                        )
                    )
                    if (
                        isinstance(interrupt_followup_candidate, str)
                        and interrupt_followup_candidate.strip()
                    ):
                        interrupt_followup_type = interrupt_followup_candidate.strip()
                    interrupt_booking_payload = DialogStateService().build_collect_owner_booking_payload(
                        existing_booking=context.get("booking") if isinstance(context, dict) else None,
                        now=now,
                        last_question=interrupt_booking_last_question,
                        slot_values=interrupt_booking_slot_values,
                    )
                    interrupt_context = DialogStateService().set_context_booking_payload(
                        interrupt_context,
                        interrupt_booking_payload,
                        key="booking",
                    )
                interrupt_info_sections = [interrupt_intent]
                interrupt_tool_args = {"service_query": interrupt_service_query}
                tool_result = execute_tool_action(
                    db,
                    tool_action="catalog.service_query",
                    tool_args=interrupt_tool_args,
                    conversation_id=conversation.id,
                    branch_id=branch_id,
                    client_slug=payload.client_slug,
                    service_query=interrupt_service_query,
                    info_sections_hint=interrupt_info_sections,
                    message_text=message_text,
                )
                reply_text = (
                    tool_result.response_text.strip()
                    if isinstance(tool_result.response_text, str) and tool_result.response_text.strip()
                    else None
                )
                reply_meta = (
                    dict(tool_result.decision_meta)
                    if isinstance(tool_result.decision_meta, dict)
                    else {}
                )
                raw_tool_decision = reply_meta.get("tool_decision")
                tool_decision_token = (
                    raw_tool_decision.strip()
                    if isinstance(raw_tool_decision, str) and raw_tool_decision.strip()
                    else None
                )
                info_sections = reply_meta.get("info_sections")
                if not isinstance(info_sections, list):
                    info_sections = []
                normalized_info_sections = [
                    section.strip().casefold()
                    for section in info_sections
                    if isinstance(section, str) and section.strip()
                ]
                expected_tool_decisions = (
                    {"ok", "truth_fallback", "price_item_fallback", "not_found_fallback"}
                    if interrupt_intent == "pricing"
                    else {"promotions", "truth_fallback"}
                    if interrupt_intent == "promotions"
                    else {"duration"}
                )
                branch_missing_truth_fallback = False
                if (
                    tool_result.handled
                    and not tool_result.ok
                    and tool_decision_token == "branch_missing"
                ):
                    fallback_reply, fallback_meta = info_router._build_info_intent_reply(
                        interrupt_intent,
                        service_query=interrupt_service_query,
                        client_slug=payload.client_slug,
                        message_text=message_text,
                        include_info_bundle=False,
                    )
                    fallback_info_sections = (
                        fallback_meta.get("info_sections")
                        if isinstance(fallback_meta, dict)
                        else None
                    )
                    fallback_normalized_info_sections = [
                        section.strip().casefold()
                        for section in (fallback_info_sections or [])
                        if isinstance(section, str) and section.strip()
                    ]
                    fallback_fact_intents = (
                        fallback_meta.get("fact_intents")
                        if isinstance(fallback_meta, dict)
                        else None
                    )
                    fallback_normalized_fact_intents = [
                        intent.strip().casefold()
                        for intent in (fallback_fact_intents or [])
                        if isinstance(intent, str) and intent.strip()
                    ]
                    fallback_action = (
                        str((fallback_meta or {}).get("action") or "").strip().casefold()
                        if isinstance(fallback_meta, dict)
                        else ""
                    )
                    fallback_fact_source = (
                        str((fallback_meta or {}).get("fact_source") or "").strip().casefold()
                        if isinstance(fallback_meta, dict)
                        else ""
                    )
                    fallback_action_class = (
                        str((fallback_meta or {}).get("action_class") or "").strip().casefold()
                        if isinstance(fallback_meta, dict)
                        else ""
                    )
                    fallback_matches_interrupt = (
                        interrupt_intent in fallback_normalized_info_sections
                        or interrupt_intent in fallback_normalized_fact_intents
                    )
                    if (
                        isinstance(fallback_reply, str)
                        and fallback_reply.strip()
                        and fallback_matches_interrupt
                        and (
                            fallback_action == "reply"
                            or (
                                fallback_fact_source == "truth"
                                and fallback_action_class == "fact"
                            )
                        )
                    ):
                        reply_text = fallback_reply.strip()
                        reply_meta = dict(fallback_meta) if isinstance(fallback_meta, dict) else {}
                        normalized_info_sections = list(
                            dict.fromkeys(
                                [
                                    *fallback_normalized_info_sections,
                                    *(
                                        [interrupt_intent]
                                        if interrupt_intent in fallback_normalized_fact_intents
                                        else []
                                    ),
                                ]
                            )
                        )
                        tool_decision_token = (
                            "truth_fallback"
                            if interrupt_intent in {"pricing", "promotions"}
                            else "duration"
                        )
                        raw_tool_decision = tool_decision_token
                        branch_missing_truth_fallback = True
                if interrupt_requires_service_query and (
                    tool_result.handled
                    and reply_text is not None
                    and tool_decision_token in expected_tool_decisions
                    and interrupt_intent in normalized_info_sections
                ):
                    reply_meta.setdefault("source", "tool_registry")
                    reply_meta.setdefault("action_source", "booking_prompt_owner")
                    reply_meta["tool_action"] = "catalog.service_query"
                    if branch_missing_truth_fallback:
                        reply_meta["catalog_service_query_branch_missing_recovered"] = True
                    interrupt_expected_reason = "booking_interrupt"
                    contract_followup_type = interrupt_followup_type
                    if interrupt_intent == "promotions":
                        tool_expected_contract = resolve_tool_expected_reply_contract(
                            tool_action="catalog.service_query",
                            tool_decision=tool_decision_token,
                            current_expected_reply_type=reply_slot_token,
                            memory_expected_reply_type=reply_slot_token,
                            booking_has_service=decision_router._booking_slot_is_complete(
                                slot_key="service",
                                value=interrupt_booking_state.get("service"),
                                client_slug=payload.client_slug,
                            ),
                            booking_has_datetime=decision_router._booking_slot_is_complete(
                                slot_key="datetime",
                                value=interrupt_booking_state.get("datetime"),
                                client_slug=payload.client_slug,
                            ),
                            booking_has_name=decision_router._booking_slot_is_complete(
                                slot_key="name",
                                value=interrupt_booking_state.get("name"),
                                client_slug=payload.client_slug,
                            ),
                            booking_active=bool(interrupt_booking_state.get("active") is True),
                        )
                        if (
                            tool_expected_contract is not None
                            and isinstance(tool_expected_contract.expected_reply_type, str)
                            and tool_expected_contract.expected_reply_type.strip()
                        ):
                            contract_followup_type = tool_expected_contract.expected_reply_type.strip()
                            interrupt_expected_reason = tool_expected_contract.reason
                            reply_meta["expected_reply_contract_reason"] = (
                                tool_expected_contract.reason
                            )
                            reply_meta["expected_reply_contract_clear"] = bool(
                                tool_expected_contract.clear_expected_reply
                            )
                            reply_meta["expected_reply_contract_handoff"] = bool(
                                tool_expected_contract.requires_handoff
                            )
                    interrupt_owner_cutover = "turn_executor.tool_reply_turn_outcome.v1"
                    interrupt_policy_intent = (
                        "info" if interrupt_intent in {"pricing", "promotions"} else "duration"
                    )
                    expected_reply_kwargs = {_ER_KEY: contract_followup_type}
                    interrupt_payload = {
                        "intent": interrupt_policy_intent,
                        "action": "fact",
                        "tool_action": "catalog.service_query",
                        "tool_args": interrupt_tool_args,
                        "pack_refs": interrupt_info_sections,
                        "slots": {"service": interrupt_service_query},
                        "reason": interrupt_expected_reason,
                    }
                    tool_reply_decision = TurnPlanner().build_tool_reply_owner_decision(
                        payload=interrupt_payload,
                        default_intent=interrupt_policy_intent,
                        reply_intent=interrupt_policy_intent,
                        tool_action="catalog.service_query",
                        collect_service_info_interrupt_active=True,
                        **expected_reply_kwargs,
                    )
                    tool_reply_dialog_state = DialogStateService().build_tool_reply_owner_state(
                        decision=tool_reply_decision,
                        owner_cutover=interrupt_owner_cutover,
                        **expected_reply_kwargs,
                        **{_ERR_KEY: interrupt_expected_reason},
                    )
                    tool_reply_payload = TurnExecutor().build_tool_reply_owner_cutover_payload(
                        decision=tool_reply_decision,
                        dialog_state=tool_reply_dialog_state,
                        text=reply_text,
                        owner_cutover=interrupt_owner_cutover,
                        reply_source="tool_registry",
                        reply_intent=interrupt_policy_intent,
                        intent=interrupt_policy_intent,
                        tool_action="catalog.service_query",
                        raw_tool_decision=(
                            raw_tool_decision if isinstance(raw_tool_decision, str) else tool_decision_token
                        ),
                        normalized_tool_decision=tool_decision_token,
                        followup_type=contract_followup_type,
                        followup_reason=interrupt_expected_reason,
                        followup_prompt=None,
                        services_overview_followup=False,
                        conversation_state=conversation.state,
                        collect_service_info_interrupt_active=True,
                        info_sections=normalized_info_sections,
                        saved_message_present=True,
                    )

                    saved_message = save_message(
                        db,
                        conversation.id,
                        client.id,
                        role="user",
                        content=message_text or "",
                        message_metadata=_build_turn_planner_user_message_metadata(payload=payload),
                    )

                    metadata_message_id = getattr(metadata, "messageId", None)
                    remote_jid_value = remote_jid.strip()
                    branch_id_value = conversation.branch_id

                    def _send_and_save(text: str) -> tuple[str, bool]:
                        save_message(
                            db,
                            conversation.id,
                            client.id,
                            role="assistant",
                            content=text,
                            message_metadata={
                                "source": "bot",
                                "owner_cutover": interrupt_owner_cutover,
                            },
                        )
                        instance_id = get_instance_id(
                            db,
                            client.id,
                            branch_id=branch_id_value,
                            remote_jid=remote_jid_value,
                        )
                        send_result = send_message_safe(
                            instance_id or "",
                            remote_jid_value,
                            text,
                            metadata_message_id,
                            notify_on_failure=True,
                            record_metrics=True,
                        )
                        conversation.last_message_at = datetime.now(timezone.utc)
                        return text, bool(getattr(send_result, "is_ok", lambda: False)())

                    trace_payload_override = dict(tool_reply_payload.trace_payload_override)
                    trace_payload_override["source_route"] = "booking_prompt_owner"
                    extra_trace_payloads = [
                        {
                            "stage": "booking_prompt_interrupt_contract",
                            "decision": "collect_service_info_interrupt",
                            "state": conversation.state,
                            "service_query": interrupt_service_query,
                            "info_sections": normalized_info_sections,
                            _ER_KEY: contract_followup_type,
                        },
                        *(
                            [
                                {
                                    "stage": "booking_prompt_interrupt_branch_recovery",
                                    "decision": "truth_fallback",
                                    "state": conversation.state,
                                    "service_query": interrupt_service_query,
                                    "info_sections": normalized_info_sections,
                                }
                            ]
                            if branch_missing_truth_fallback
                            else []
                        ),
                        *tool_reply_payload.extra_trace_payloads,
                    ]
                    extra_meta_updates = [
                        *tool_reply_payload.extra_meta_updates,
                        {
                            "booking_prompt_interrupt_recovery": (
                                f"active_{interrupt_slot_label}_{interrupt_intent}_interrupt"
                            ),
                            "service_query": interrupt_service_query,
                            "catalog_service_query_branch_missing_recovered": (
                                branch_missing_truth_fallback
                            ),
                        },
                    ]

                    if not _ensure_pending_collect_resume_meta():
                        return None
                    return _finalize_turn_planner_owner_cutover(
                        payload=payload,
                        db=db,
                        client_id=client_id,
                        preflight_payload=preflight_payload,
                        conversation_id=conversation.id,
                        decision=tool_reply_decision,
                        reply_text=reply_text,
                        reply_meta=reply_meta,
                        trace_meta=(
                            dict(tool_result.trace)
                            if isinstance(tool_result.trace, dict)
                            else None
                        ),
                        owner_cutover=interrupt_owner_cutover,
                        stage="llm_policy_core_tool",
                        success_label="Turn planner safe booking interrupt tool reply",
                        tool_decision=tool_decision_token,
                        followup_type=contract_followup_type,
                        question_reason=interrupt_expected_reason,
                        booking_payload_override=(
                            interrupt_context.get("booking")
                            if isinstance(interrupt_context, dict)
                            else None
                        ),
                        outcome_action="reply",
                        outcome_source="tool_registry",
                        artifact=tool_reply_payload.artifact,
                        existing_conversation=conversation,
                        existing_saved_message=saved_message,
                        send_and_save=_send_and_save,
                        trace_payload_override=trace_payload_override,
                        extra_trace_payloads=extra_trace_payloads,
                        extra_meta_updates=extra_meta_updates,
                    )
                elif interrupt_intent in REASONING_CORE_TURN_PLANNER_INFO_INTENTS:
                    reply_text, reply_meta = info_router._build_info_intent_reply(
                        interrupt_intent,
                        service_query=None,
                        client_slug=payload.client_slug,
                        message_text=message_text,
                        include_info_bundle=True,
                    )
                    reply_text = (
                        reply_text.strip()
                        if isinstance(reply_text, str) and reply_text.strip()
                        else None
                    )
                    reply_meta = dict(reply_meta) if isinstance(reply_meta, dict) else {}
                    info_sections = reply_meta.get("info_sections")
                    if not isinstance(info_sections, list):
                        info_sections = []
                    normalized_info_sections = [
                        section.strip().casefold()
                        for section in info_sections
                        if isinstance(section, str) and section.strip()
                    ]
                    fact_intents = reply_meta.get("fact_intents")
                    if not isinstance(fact_intents, list):
                        fact_intents = []
                    normalized_fact_intents = [
                        intent.strip().casefold()
                        for intent in fact_intents
                        if isinstance(intent, str) and intent.strip()
                    ]
                    if (
                        reply_text is not None
                        and (
                            interrupt_intent in normalized_info_sections
                            or interrupt_intent in normalized_fact_intents
                        )
                    ):
                        interrupt_expected_reason = "booking_interrupt"
                        reply_meta.setdefault("action_source", "booking_prompt_owner")
                        reply_meta["tool_action"] = "info"
                        reply_meta.update(
                            {
                                "booking_info_interrupt": True,
                                "booking_interrupt_info": True,
                                "booking_info_intents": (
                                    normalized_fact_intents or interrupt_info_sections
                                ),
                                "booking_prompt_interrupt_recovery": (
                                    f"active_{interrupt_slot_label}_{interrupt_intent}_interrupt"
                                ),
                            }
                        )
                        interrupt_decision = TurnPlanner().build_from_policy_override(
                            {
                                "intent": interrupt_intent,
                                "action": "fact",
                                "tool_action": "info",
                                "pack_refs": interrupt_info_sections,
                                "reason": interrupt_expected_reason,
                            },
                            interaction_owner=REASONING_CORE_TURN_PLANNER_INFO_OWNER,
                            interaction_relation=REASONING_CORE_TURN_PLANNER_INFO_STAGE,
                        )
                        interrupt_extra_traces = [
                            {
                                "stage": "booking_prompt_interrupt_contract",
                                "decision": "generic_info_interrupt",
                                "state": conversation.state,
                                "info_sections": (
                                    normalized_info_sections or interrupt_info_sections
                                ),
                                _ER_KEY: interrupt_followup_type,
                            },
                            {
                                "stage": "booking_interrupt",
                                "decision": "info_reply",
                                "state": conversation.state,
                                "booking_interrupt_info": True,
                                "info_sections": (
                                    normalized_info_sections or interrupt_info_sections
                                ),
                            },
                        ]
                        if not _ensure_pending_collect_resume_meta():
                            return None
                        return _finalize_turn_planner_owner_cutover(
                            payload=payload,
                            db=db,
                            client_id=client_id,
                            preflight_payload=preflight_payload,
                            conversation_id=conversation.id,
                            decision=interrupt_decision,
                            reply_text=reply_text,
                            reply_meta=reply_meta,
                            trace_meta={"source_route": "booking_prompt_owner"},
                            owner_cutover=REASONING_CORE_TURN_PLANNER_INFO_OWNER,
                            stage=REASONING_CORE_TURN_PLANNER_INFO_STAGE,
                            success_label="Turn planner safe booking interrupt info fact",
                            followup_type=interrupt_followup_type,
                            question_reason=interrupt_expected_reason,
                            booking_payload_override=(
                                interrupt_booking_payload
                                if interrupt_booking_last_question is not None
                                else None
                            ),
                            outcome_action="reply",
                            outcome_source="consultant_core_runtime",
                            extra_trace_payloads=interrupt_extra_traces,
                        )

    if route_source is None:
        if not booking_messages:
            return None
        pending_reactivation_candidate = None
        if not (conversation_snapshot.booking_active or normalized_goal == "booking"):
            pending_reactivation_candidate = _resolve_turn_planner_pending_booking_reactivation_candidate(
                payload=payload,
                message_text=message_text,
                booking_state=booking_state,
                context=context,
                now=now,
            )
            if pending_reactivation_candidate is None:
                return None
        booking_signal, booking_block_meta = decision_router._evaluate_booking_signal(
            booking_messages,
            client_slug=payload.client_slug,
            message_text=message_text,
            relative_base=datetime.now(timezone.utc),
        )
        direct_booking_request = bool(
            message_text
            and decision_router._is_booking_request(
                message_text,
                client_slug=payload.client_slug,
            )
        )
        booking_slot_signal = decision_router._is_booking_slot_signal(
            message_text,
            client_slug=payload.client_slug,
        )
        service_slot_signal = bool(
            reply_slot_token == decision_router.EXPECTED_REPLY_SERVICE
            and isinstance(message_text, str)
            and decision_router._extract_service_hint(message_text, payload.client_slug)
        )
        expected_reply_booking_slot = {
            decision_router.EXPECTED_REPLY_SERVICE: "service",
            decision_router.EXPECTED_REPLY_TIME: "datetime",
            decision_router.EXPECTED_REPLY_NAME: "name",
        }.get(reply_slot_token)
        expected_reply_progressed = False
        expected_reply_still_missing = False
        if expected_reply_booking_slot is not None:
            projected_shortcircuit_state = dict(booking_state)
            if projected_shortcircuit_state.get("active") is not True:
                projected_shortcircuit_state["active"] = True
                projected_shortcircuit_state["started_at"] = now.isoformat()
            if booking_messages:
                projected_shortcircuit_state = decision_router._update_booking_from_messages(
                    projected_shortcircuit_state,
                    booking_messages,
                    client_slug=payload.client_slug,
                )
            if expected_reply_booking_slot == "datetime":
                projected_shortcircuit_state = _restore_turn_planner_snapshot_datetime_if_message_echo(
                    booking_state=projected_shortcircuit_state,
                    booking_datetime_value=conversation_snapshot.booking_datetime_value,
                    message_text=message_text,
                )
                (
                    projected_shortcircuit_state,
                    expected_reply_time_progression_meta,
                ) = _apply_turn_planner_exact_time_progression_override(
                    booking_state=projected_shortcircuit_state,
                    message_text=message_text,
                    client_slug=payload.client_slug,
                )
            expected_reply_missing_before = decision_router._first_missing_booking_slot(
                booking_state,
                client_slug=payload.client_slug,
            )
            expected_reply_missing_after = decision_router._first_missing_booking_slot(
                projected_shortcircuit_state,
                client_slug=payload.client_slug,
            )
            expected_reply_progressed = (
                expected_reply_missing_before == expected_reply_booking_slot
                and expected_reply_missing_after != expected_reply_booking_slot
            )
            expected_reply_still_missing = (
                expected_reply_missing_before == expected_reply_booking_slot
                and expected_reply_missing_after == expected_reply_booking_slot
            )
        expected_reply_shortcircuit = bool(
            not booking_block_meta
            and conversation_snapshot.booking_active
            and expected_reply_booking_slot is not None
            and expected_reply_progressed
            and not direct_booking_request
        )
        question_contract_slot_constraint = bool(
            question_contract_time_slot_constraint
            and expected_reply_booking_slot == "datetime"
            and expected_reply_still_missing
        )
        if question_contract_slot_constraint:
            route_source = "question_contract"
            route_reason = (
                conversation_snapshot.resume_reason.strip()
                if isinstance(conversation_snapshot.resume_reason, str)
                and conversation_snapshot.resume_reason.strip()
                else "booking_prompt"
            )
            followup_reason = route_reason
            reply_meta.update(
                {
                    "source": "question_contract",
                    "action_source": "question_contract",
                    "pending_question_act": "slot_constraint",
                    "pending_question_target": "time",
                    "pending_question_interaction": "slot_constraint",
                    "pending_question_owner": "question_contract",
                }
            )
            trace_meta.update(
                {
                    "source_route": "question_contract",
                    "pending_question_act": "slot_constraint",
                    "pending_question_target": "time",
                    "pending_question_owner": "question_contract",
                }
            )
            extra_trace_payloads.append(
                {
                    "stage": "pending_question_interaction",
                    "decision": "slot_constraint",
                    "state": conversation.state,
                    "source": "question_contract",
                    "pending_question_act": "slot_constraint",
                    "pending_question_target": "time",
                    _ER_KEY: decision_router.EXPECTED_REPLY_TIME,
                }
            )
        elif expected_reply_shortcircuit:
            route_source = "booking_prompt_owner"
            route_reason = "booking_prompt"
            reply_meta.update(
                {
                    "source": "booking_prompt_owner",
                    "action_source": "booking_prompt_owner",
                    "expected_reply_shortcircuit": True,
                }
            )
            trace_meta.update(
                {
                    "source_route": "booking_prompt_owner",
                    "expected_reply_shortcircuit": True,
                }
            )
        elif (
            booking_block_meta
            or expected_reply_still_missing
            or not (booking_signal or booking_slot_signal or service_slot_signal)
        ):
            llm_candidate = (
                pending_reactivation_candidate
                if pending_reactivation_candidate is not None
                else _resolve_turn_planner_safe_llm_booking_prompt_candidate(
                    payload=payload,
                    message_text=message_text,
                    reply_slot=reply_slot_token,
                    current_goal=normalized_goal,
                    booking_state=booking_state,
                    context=context,
                    now=now,
                )
            )
            if llm_candidate is None:
                return None
            route_source = "llm_policy_core"
            route_reason = llm_candidate["reason"]
            policy_slot_values = dict(llm_candidate["slot_values"])
            reply_meta.update(
                {
                    "source": "llm_policy_core",
                    "action_source": "llm_policy_core",
                    "llm_policy_core_collect_slot": llm_candidate["collect_slot"],
                }
            )
            trace_meta.update(
                {
                    "source_route": "llm_policy_core",
                    "requested_slot": llm_candidate["collect_slot"],
                }
            )
            if pending_reactivation_candidate is not None:
                reply_meta["pending_collect_reactivation"] = True
                trace_meta["pending_collect_reactivation"] = True
                extra_trace_payloads.append(
                    {
                        "stage": "collect_owner_reactivation",
                        "decision": "pending_collect_reactivation",
                        "state": conversation.state,
                        "source": "booking_prompt_owner",
                        "requested_slot": llm_candidate["collect_slot"],
                    }
                )
        else:
            route_source = "booking_prompt_owner"
            route_reason = "booking_prompt"
            reply_meta.update(
                {
                    "source": "booking_prompt_owner",
                    "action_source": "booking_prompt_owner",
                }
            )
            trace_meta["source_route"] = "booking_prompt_owner"

    if booking_state.get("active") is not True:
        booking_state["active"] = True
        booking_state["started_at"] = now.isoformat()
    if booking_messages:
        booking_state = decision_router._update_booking_from_messages(
            booking_state,
            booking_messages,
            client_slug=payload.client_slug,
        )
    if route_source in {"booking_prompt_owner", "llm_policy_core"}:
        booking_state = _restore_turn_planner_snapshot_datetime_if_message_echo(
            booking_state=booking_state,
            booking_datetime_value=conversation_snapshot.booking_datetime_value,
            message_text=message_text,
        )
        booking_state, merged_time_progression_meta = _apply_turn_planner_exact_time_progression_override(
            booking_state=booking_state,
            message_text=message_text,
            client_slug=payload.client_slug,
        )
        if merged_time_progression_meta is not None:
            expected_reply_time_progression_meta = merged_time_progression_meta
            reply_meta.update(expected_reply_time_progression_meta)
            trace_meta.update(expected_reply_time_progression_meta)
            extra_trace_payloads.append(
                _build_exact_time_progression_trace_payload(
                    source=(
                        "booking_prompt_owner"
                        if route_source == "booking_prompt_owner"
                        else "llm_policy_core_semantic_arbitration"
                    ),
                    state=conversation.state,
                    progression_meta=merged_time_progression_meta,
                )
            )
    for slot_key, value in policy_slot_values.items():
        if not booking_state.get(slot_key):
            booking_state[slot_key] = value

    carryover = None
    if not booking_state.get("service"):
        service_hint = decision_router._get_recent_service_hint(context, now)
        if service_hint:
            booking_state["service"] = service_hint
            clear_service_hint = True
        elif isinstance(context_manager, dict):
            raw_message_count = context_manager.get("message_count")
            try:
                message_count = int(raw_message_count)
            except (TypeError, ValueError):
                message_count = 0
            carryover = decision_router._get_service_carryover(
                context_manager,
                message_count=max(message_count, 0),
            )
            if isinstance(carryover, dict):
                service_query = carryover.get("service_query")
                if isinstance(service_query, str) and service_query.strip():
                    booking_state["service"] = service_query.strip()
                    reply_meta["service_query"] = service_query.strip()
                    reply_meta["service_query_source"] = "context"
                    trace_meta["service_query"] = service_query.strip()
                    for key in ("canonical_state_owner", "projection_source"):
                        value = carryover.get(key)
                        if isinstance(value, str) and value.strip():
                            reply_meta[key] = value.strip()
                            trace_meta[key] = value.strip()

    if conversation_snapshot is not None:
        if not booking_state.get("service"):
            snapshot_service = conversation_snapshot.service_referent
            if isinstance(snapshot_service, str) and snapshot_service.strip():
                booking_state["service"] = snapshot_service.strip()
        if not booking_state.get("datetime"):
            snapshot_datetime = conversation_snapshot.booking_datetime_value
            if isinstance(snapshot_datetime, str) and snapshot_datetime.strip():
                booking_state["datetime"] = snapshot_datetime.strip()
        if conversation_snapshot.booking_active and booking_state.get("active") is not True:
            booking_state["active"] = True

    booking_state, prompt = decision_router._next_booking_prompt(
        booking_state,
        refusal_flags=refusal_flags if isinstance(refusal_flags, dict) else None,
        client_slug=payload.client_slug,
    )
    booking_last_question = booking_state.get("last_question")
    if not isinstance(booking_last_question, str) or not booking_last_question.strip():
        return None
    booking_last_question = booking_last_question.strip()
    followup_type = decision_router._expected_reply_for_booking_question(booking_last_question)
    if not isinstance(followup_type, str) or not followup_type.strip():
        return None
    reply_text = prompt or _resolve_turn_planner_booking_prompt_text(followup_type)
    if not isinstance(reply_text, str) or not reply_text.strip():
        return None

    slot_values = _build_turn_planner_booking_prompt_slot_values(booking_state)
    decision = _build_turn_planner_safe_booking_prompt_decision(
        last_question=booking_last_question,
        slot_values=slot_values,
        reason=route_reason or "booking_prompt",
    )
    if decision is None:
        return None

    trace_meta["missing_slot"] = booking_last_question
    grounded_referents = None
    service_value = slot_values.get("service")
    if service_value:
        grounded_referents = {"service": service_value}

    if not _ensure_pending_collect_resume_meta():
        return None
    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation.id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE,
        success_label="Turn planner safe booking prompt owner",
        followup_type=followup_type,
        question_reason=followup_reason,
        grounded_referents=grounded_referents,
        booking_slot_values=slot_values,
        booking_last_question=booking_last_question,
        booking_payload_override=(
            booking_state if isinstance(expected_reply_time_progression_meta, dict) else None
        ),
        outcome_action="booking_prompt",
        outcome_source=route_source or "booking_prompt_owner",
        trace_decision="prompt",
        extra_trace_payloads=extra_trace_payloads,
        clear_intent_queue=clear_intent_queue,
        clear_service_hint=clear_service_hint,
    )


async def _try_handle_turn_planner_safe_check_booking_prompt_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    conversation_snapshot: ReasoningCoreConversationSnapshot | None,
    batch_messages: list[str] | None,
    enqueue_only: bool,
    skip_persist: bool,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist:
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    has_media = bool(body is not None and body.mediaData)
    if has_media or not (isinstance(message_text, str) and message_text.strip()):
        return None
    if not decision_router._looks_like_booking_verification_request(message_text):
        return None
    if decision_router._is_style_reference_request(message_text, has_media=False):
        return None
    if decision_router._looks_like_booking_reschedule_request(
        message_text,
        client_slug=payload.client_slug,
    ):
        return None

    client = _resolve_turn_planner_owner_client(
        db,
        payload=payload,
        client_id=client_id,
        preflight_payload=preflight_payload,
    )
    if not isinstance(client, Client):
        return None

    metadata = body.metadata if body is not None else None
    remote_jid = getattr(metadata, "remoteJid", None)
    if not isinstance(remote_jid, str) or not remote_jid.strip():
        return None

    branch_id = _resolve_snapshot_branch_id(preflight_payload)
    source_conversation_id = conversation_id or (
        conversation_snapshot.conversation_id if conversation_snapshot is not None else None
    )
    conversation = _ensure_turn_planner_owner_conversation(
        db,
        client=client,
        remote_jid=remote_jid.strip(),
        branch_id=branch_id,
        conversation_id=source_conversation_id,
    )
    if not isinstance(conversation, Conversation):
        return None

    routing = decision_router.ROUTING_MATRIX.get(conversation.state, {})
    if not routing.get("allow_bot_reply", False) or not routing.get("allow_booking_flow", False):
        return None

    pending_collect_resume_meta = _restore_turn_planner_collect_owner_bot_active_state(
        db=db,
        conversation=conversation,
    )
    if pending_collect_resume_meta is None:
        return None

    context = context_manager_router._get_conversation_context(conversation)
    reply_slot_token = (
        conversation_snapshot.reply_slot
        if conversation_snapshot is not None
        else DialogStateService().project_expected_reply_projections(
            **{
                _ER_KEY: context.get(_ER_KEY),
                _ERR_KEY: context.get(_ERR_KEY),
            }
        ).expected_reply_type
    )
    booking_state = decision_router._get_booking_context(context)
    booking_state = dict(booking_state) if isinstance(booking_state, dict) else {}
    current_goal = context.get("current_goal")
    normalized_goal = (
        current_goal.strip() if isinstance(current_goal, str) and current_goal.strip() else None
    )
    context_manager = decision_router._get_context_manager(context)
    now = datetime.now(timezone.utc)
    allow_initial_slot_progression = not (
        conversation_snapshot is not None
        and (conversation_snapshot.booking_active or normalized_goal == "booking")
    )

    llm_candidate = _resolve_turn_planner_safe_llm_booking_prompt_candidate(
        payload=payload,
        message_text=message_text,
        reply_slot=reply_slot_token,
        current_goal=normalized_goal,
        booking_state=booking_state,
        context=context,
        now=now,
        allow_initial_slot_progression=allow_initial_slot_progression,
    )
    if llm_candidate is None:
        return None

    booking_messages = [
        message
        for message in (batch_messages or [])
        if isinstance(message, str) and message.strip()
    ]
    if not booking_messages:
        booking_messages = [message_text]
    if booking_state.get("active") is not True:
        booking_state["active"] = True
        booking_state["started_at"] = now.isoformat()
    if booking_messages:
        booking_state = decision_router._update_booking_from_messages(
            booking_state,
            booking_messages,
            client_slug=payload.client_slug,
        )
    clear_service_hint = False
    for slot_key, value in dict(llm_candidate["slot_values"]).items():
        if not booking_state.get(slot_key):
            booking_state[slot_key] = value

    carryover = None
    if not booking_state.get("service"):
        service_hint = decision_router._get_recent_service_hint(context, now)
        if service_hint:
            booking_state["service"] = service_hint
            clear_service_hint = True
        elif isinstance(context_manager, dict):
            raw_message_count = context_manager.get("message_count")
            try:
                message_count = int(raw_message_count)
            except (TypeError, ValueError):
                message_count = 0
            carryover = decision_router._get_service_carryover(
                context_manager,
                message_count=max(message_count, 0),
            )
            if isinstance(carryover, dict):
                service_query = carryover.get("service_query")
                if isinstance(service_query, str) and service_query.strip():
                    booking_state["service"] = service_query.strip()

    if conversation_snapshot is not None:
        if not booking_state.get("service"):
            snapshot_service = conversation_snapshot.service_referent
            if isinstance(snapshot_service, str) and snapshot_service.strip():
                booking_state["service"] = snapshot_service.strip()
        if not booking_state.get("datetime"):
            snapshot_datetime = conversation_snapshot.booking_datetime_value
            if isinstance(snapshot_datetime, str) and snapshot_datetime.strip():
                booking_state["datetime"] = snapshot_datetime.strip()
        if conversation_snapshot.booking_active and booking_state.get("active") is not True:
            booking_state["active"] = True

    if decision_router._booking_has_reference(booking_state):
        return None

    llm_collect_slot = llm_candidate["collect_slot"]
    booking_last_question = decision_router._first_missing_booking_slot(
        booking_state,
        client_slug=payload.client_slug,
    )
    if booking_last_question not in {
        "service",
        "datetime",
        "name",
    }:
        booking_last_question = llm_collect_slot
    followup_type = decision_router._expected_reply_for_booking_question(booking_last_question)
    if followup_type not in {
        decision_router.EXPECTED_REPLY_SERVICE,
        decision_router.EXPECTED_REPLY_TIME,
        decision_router.EXPECTED_REPLY_NAME,
    }:
        return None

    slot_values = _build_turn_planner_booking_prompt_slot_values(booking_state)
    decision = _build_turn_planner_safe_check_booking_prompt_decision(
        last_question=booking_last_question,
        slot_values=slot_values,
        reason=llm_candidate["reason"],
    )
    if decision is None:
        return None

    extra_trace_payloads: list[dict[str, object]] = []
    reply_meta: dict[str, object] = {
        "action": "check_booking_prompt",
        "intent": "check_booking",
        "tool_action": "collect",
        "source": "booking_verification",
        "action_source": "booking_verification",
        "llm_policy_core_collect_slot": booking_last_question,
    }
    if pending_collect_resume_meta:
        reply_meta.update(pending_collect_resume_meta)
        extra_trace_payloads.append(
            {
                "stage": "collect_owner_reactivation",
                "decision": "reactivate_collect_owner",
                "reason": "booking_collect_reentry",
                "mode": pending_collect_resume_meta.get("pending_collect_resume_mode"),
                "state_before": pending_collect_resume_meta.get(
                    "pending_collect_resume_state_before"
                ),
                "state_after": pending_collect_resume_meta.get(
                    "pending_collect_resume_state_after"
                ),
            }
        )
    if llm_collect_slot != booking_last_question:
        reply_meta["llm_policy_core_collect_slot_original"] = llm_collect_slot
    if isinstance(reply_slot_token, str) and reply_slot_token in {
        decision_router.EXPECTED_REPLY_SERVICE,
        decision_router.EXPECTED_REPLY_TIME,
        decision_router.EXPECTED_REPLY_NAME,
    }:
        extra_trace_payloads.append(
            {
                "stage": "question_contract",
                "decision": "bypass",
                _ER_KEY: reply_slot_token,
                "expected_reply_bypassed": "booking_verification",
            }
        )
        reply_meta["expected_reply_bypassed"] = "booking_verification"
    if llm_collect_slot != booking_last_question:
        extra_trace_payloads.append(
            {
                "stage": "question_contract",
                "reason": "booking_verification_reference_continuity",
                "decision": "normalize",
                "collect_slot_original": llm_collect_slot,
                "normalized_missing_slot": booking_last_question,
                _ER_KEY: followup_type,
            }
        )

    trace_meta: dict[str, object] = {
        "source_route": "booking_verification",
        "requested_slot": booking_last_question,
        "missing_slot": booking_last_question,
    }
    grounded_referents = None
    service_value = slot_values.get("service")
    if service_value:
        grounded_referents = {"service": service_value}

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation.id,
        decision=decision,
        reply_text=decision_router.MSG_BOOKING_ASK_REFERENCE,
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE,
        success_label="Turn planner safe check booking prompt owner",
        followup_type=followup_type,
        question_reason="calendar_get_booking_collect_reference",
        grounded_referents=grounded_referents,
        booking_slot_values=slot_values,
        booking_last_question=booking_last_question,
        outcome_action="check_booking_prompt",
        outcome_source="booking_verification",
        trace_decision="check_booking_prompt",
        extra_trace_payloads=extra_trace_payloads,
        clear_service_hint=clear_service_hint,
    )


async def _try_handle_turn_planner_safe_specialist_followup_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    conversation_snapshot: ReasoningCoreConversationSnapshot | None,
    batch_messages: list[str] | None,
    enqueue_only: bool,
    skip_persist: bool,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or conversation_snapshot is None:
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    has_media = bool(body is not None and body.mediaData)
    if has_media:
        return None
    if message_text and decision_router._is_style_reference_request(message_text, has_media=False):
        return None
    if message_text and decision_router._looks_like_booking_verification_request(message_text):
        return None
    if message_text and decision_router._looks_like_booking_reschedule_request(
        message_text,
        client_slug=payload.client_slug,
    ):
        return None

    client = _resolve_turn_planner_owner_client(
        db,
        payload=payload,
        client_id=client_id,
        preflight_payload=preflight_payload,
    )
    if not isinstance(client, Client):
        return None

    metadata = body.metadata if body is not None else None
    remote_jid = getattr(metadata, "remoteJid", None)
    if not isinstance(remote_jid, str) or not remote_jid.strip():
        return None

    branch_id = _resolve_snapshot_branch_id(preflight_payload)
    source_conversation_id = conversation_id or conversation_snapshot.conversation_id
    conversation = _ensure_turn_planner_owner_conversation(
        db,
        client=client,
        remote_jid=remote_jid.strip(),
        branch_id=branch_id,
        conversation_id=source_conversation_id,
    )
    if not isinstance(conversation, Conversation):
        return None

    routing = decision_router.ROUTING_MATRIX.get(conversation.state, {})
    if not routing.get("allow_bot_reply", False) or not routing.get("allow_booking_flow", False):
        return None

    context = context_manager_router._get_conversation_context(conversation)
    booking_state = decision_router._get_booking_context(context)
    booking_state = dict(booking_state) if isinstance(booking_state, dict) else {}
    current_goal = context.get("current_goal")
    normalized_goal = (
        current_goal.strip() if isinstance(current_goal, str) and current_goal.strip() else None
    )
    now = datetime.now(timezone.utc)

    llm_candidate = _resolve_turn_planner_safe_llm_specialist_followup_candidate(
        payload=payload,
        message_text=message_text,
        reply_slot=conversation_snapshot.reply_slot,
        current_goal=normalized_goal,
        booking_state=booking_state,
        context=context,
        now=now,
    )
    if llm_candidate is None:
        return None

    booking_state = dict(booking_state)
    if booking_state.get("active") is not True:
        booking_state["active"] = True
        booking_state["started_at"] = now.isoformat()
    for slot_key, value in dict(llm_candidate["merged_slot_values"]).items():
        if not booking_state.get(slot_key):
            booking_state[slot_key] = value
    specialist_name = llm_candidate.get("specialist_name")
    specialist_id = llm_candidate.get("specialist_id")
    if isinstance(specialist_name, str) and specialist_name.strip():
        booking_state["specialist_name"] = specialist_name.strip()
    if isinstance(specialist_id, str) and specialist_id.strip():
        booking_state["specialist_id"] = specialist_id.strip()

    booking_last_question = llm_candidate["collect_slot"]
    followup_type = decision_router._expected_reply_for_booking_question(booking_last_question)
    if followup_type not in {
        decision_router.EXPECTED_REPLY_TIME,
        decision_router.EXPECTED_REPLY_NAME,
    }:
        return None

    base_prompt = _resolve_turn_planner_booking_prompt_text(followup_type)
    if not isinstance(base_prompt, str) or not base_prompt.strip():
        return None
    reply_text = decision_router._format_specialist_followup_prompt(
        specialist_name=specialist_name,
        base_prompt=base_prompt,
        question_like=decision_router._is_question_like_message(message_text),
    )
    if not isinstance(reply_text, str) or not reply_text.strip():
        return None

    slot_values = _build_turn_planner_booking_prompt_slot_values(booking_state)
    decision = _build_turn_planner_safe_booking_prompt_decision(
        last_question=booking_last_question,
        slot_values=slot_values,
        reason=llm_candidate["reason"],
    )
    if decision is None:
        return None

    updated_booking_payload = DialogStateService().normalize_booking_payload(booking_state)
    if updated_booking_payload is None:
        return None
    context = DialogStateService().set_context_booking_payload(
        context,
        updated_booking_payload,
        key="booking",
    )
    context_manager_router._set_conversation_context(conversation, context)

    active_question_relation = llm_candidate.get("active_question_relation") or "referent_followup"
    extra_trace_payloads: list[dict[str, object]] = [
        {
            "stage": "pending_question_interaction",
            "decision": "booking_specialist_followup",
            "state": conversation.state,
            "source": "booking_specialist_followup",
            "pending_question_target": "specialist",
            "active_question_relation": active_question_relation,
            "requested_slot": booking_last_question,
            _ER_KEY: followup_type,
        }
    ]
    if isinstance(specialist_name, str) and specialist_name.strip():
        extra_trace_payloads[0]["specialist_name"] = specialist_name.strip()
    if isinstance(specialist_id, str) and specialist_id.strip():
        extra_trace_payloads[0]["specialist_id"] = specialist_id.strip()

    reply_meta: dict[str, object] = {
        "action": "booking_prompt",
        "intent": "booking",
        "source": "booking_specialist_followup",
        "action_source": "booking_specialist_followup",
        "tool_action": decision.tool_action,
        "pending_question_target": "specialist",
        "pending_question_interaction": "specialist_followup",
        "pending_question_owner": "booking_specialist_followup",
        "active_question_relation": active_question_relation,
    }
    pending_question_act = llm_candidate.get("pending_question_act")
    if isinstance(pending_question_act, str) and pending_question_act.strip():
        reply_meta["pending_question_act"] = pending_question_act.strip()
    if isinstance(specialist_name, str) and specialist_name.strip():
        reply_meta["specialist_name"] = specialist_name.strip()
    if isinstance(specialist_id, str) and specialist_id.strip():
        reply_meta["specialist_id"] = specialist_id.strip()

    trace_meta: dict[str, object] = {
        "source_route": "booking_specialist_followup",
        "missing_slot": booking_last_question,
        "pending_question_owner": "booking_specialist_followup",
    }
    grounded_referents = None
    service_value = slot_values.get("service")
    if service_value:
        grounded_referents = {"service": service_value}

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation.id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_SPECIALIST_FOLLOWUP_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_SPECIALIST_FOLLOWUP_STAGE,
        success_label="Turn planner safe specialist followup owner",
        followup_type=followup_type,
        question_reason="booking_prompt",
        grounded_referents=grounded_referents,
        booking_slot_values=slot_values,
        booking_last_question=booking_last_question,
        outcome_action="booking_prompt",
        outcome_source="booking_specialist_followup",
        trace_decision="prompt",
        extra_trace_payloads=extra_trace_payloads,
        clear_service_hint=bool(llm_candidate.get("clear_service_hint")),
    )


async def _try_handle_turn_planner_safe_initial_booking_prompt_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    conversation_snapshot: ReasoningCoreConversationSnapshot | None,
    batch_messages: list[str] | None,
    enqueue_only: bool,
    skip_persist: bool,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist or conversation_snapshot is not None:
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    has_media = bool(body is not None and body.mediaData)
    if has_media:
        return None
    if message_text and decision_router._is_style_reference_request(message_text, has_media=False):
        return None
    if message_text and decision_router._looks_like_booking_verification_request(message_text):
        return None
    if message_text and decision_router._looks_like_booking_reschedule_request(
        message_text,
        client_slug=payload.client_slug,
    ):
        return None

    booking_messages = [
        message
        for message in (batch_messages or [])
        if isinstance(message, str) and message.strip()
    ]
    if not booking_messages and isinstance(message_text, str) and message_text.strip():
        booking_messages = [message_text]
    if not booking_messages:
        return None

    now = datetime.now(timezone.utc)
    llm_candidate = _resolve_turn_planner_safe_llm_booking_prompt_candidate(
        payload=payload,
        message_text=message_text,
        reply_slot=None,
        current_goal=None,
        booking_state=None,
        context={},
        now=now,
        allow_initial_slot_progression=True,
        allow_timeout_recovery=True,
    )
    if llm_candidate is None:
        return None
    collect_slot = llm_candidate["collect_slot"]
    if collect_slot not in {"service", "datetime", "name"}:
        return None
    slot_values = dict(llm_candidate["slot_values"])
    if collect_slot == "datetime" and set(slot_values) != {"service"}:
        return None
    if collect_slot == "name" and set(slot_values) != {"service", "datetime"}:
        return None

    client = _resolve_turn_planner_owner_client(
        db,
        payload=payload,
        client_id=client_id,
        preflight_payload=preflight_payload,
    )
    if not isinstance(client, Client):
        return None

    metadata = body.metadata if body is not None else None
    remote_jid = getattr(metadata, "remoteJid", None)
    if not isinstance(remote_jid, str) or not remote_jid.strip():
        return None

    branch_id = _resolve_snapshot_branch_id(preflight_payload)
    conversation = _ensure_turn_planner_owner_conversation(
        db,
        client=client,
        remote_jid=remote_jid.strip(),
        branch_id=branch_id,
        conversation_id=conversation_id,
    )
    if not isinstance(conversation, Conversation):
        return None

    routing = decision_router.ROUTING_MATRIX.get(conversation.state, {})
    if not routing.get("allow_bot_reply", False) or not routing.get("allow_booking_flow", False):
        return None

    seeded_booking_state = llm_candidate.get("seed_booking_state")
    booking_state = (
        dict(seeded_booking_state)
        if isinstance(seeded_booking_state, dict) and seeded_booking_state
        else {"active": True, "started_at": now.isoformat()}
    )
    if not isinstance(seeded_booking_state, dict) or not seeded_booking_state:
        for slot_key, value in slot_values.items():
            if not booking_state.get(slot_key):
                booking_state[slot_key] = value

    booking_state, prompt = decision_router._next_booking_prompt(
        booking_state,
        refusal_flags=None,
        client_slug=payload.client_slug,
    )
    booking_last_question = booking_state.get("last_question")
    if not isinstance(booking_last_question, str) or booking_last_question.strip() != collect_slot:
        return None
    followup_type = decision_router._expected_reply_for_booking_question(booking_last_question)
    if followup_type not in {
        decision_router.EXPECTED_REPLY_SERVICE,
        decision_router.EXPECTED_REPLY_TIME,
        decision_router.EXPECTED_REPLY_NAME,
    }:
        return None
    reply_text = prompt or _resolve_turn_planner_booking_prompt_text(followup_type)
    if not isinstance(reply_text, str) or not reply_text.strip():
        return None

    decision = _build_turn_planner_safe_booking_prompt_decision(
        last_question=collect_slot,
        slot_values=_build_turn_planner_booking_prompt_slot_values(booking_state),
        reason=llm_candidate["reason"],
    )
    if decision is None:
        return None

    grounded_referents = None
    service_value = booking_state.get("service")
    if isinstance(service_value, str) and service_value.strip():
        grounded_referents = {"service": service_value.strip()}

    reply_meta: dict[str, object] = {
        "action": "booking_prompt",
        "intent": "booking",
        "tool_action": "collect",
        "source": "llm_policy_core",
        "action_source": "llm_policy_core",
        "llm_policy_core_collect_slot": collect_slot,
    }
    trace_meta: dict[str, object] = {
        "source_route": "llm_policy_core",
        "requested_slot": collect_slot,
        "missing_slot": collect_slot,
    }
    extra_trace_payloads: list[dict[str, object]] = []
    policy_core_mode = llm_candidate.get("policy_core_mode")
    policy_core_degrade_reason = llm_candidate.get("policy_core_degrade_reason")
    policy_core_guard_recovery = llm_candidate.get("policy_core_guard_recovery")
    if isinstance(policy_core_mode, str) and policy_core_mode.strip():
        reply_meta["policy_core_mode"] = policy_core_mode.strip()
    if isinstance(policy_core_degrade_reason, str) and policy_core_degrade_reason.strip():
        reply_meta["policy_core_degrade_reason"] = policy_core_degrade_reason.strip()
    if isinstance(policy_core_guard_recovery, str) and policy_core_guard_recovery.strip():
        normalized_recovery = policy_core_guard_recovery.strip()
        reply_meta["policy_core_guard_recovery"] = normalized_recovery
        trace_decision = (
            "invalid_schema_initial_booking_collect"
            if normalized_recovery == "invalid_schema_collect_contract"
            else "timeout_initial_booking_collect"
        )
        extra_trace_payloads.append(
            {
                "stage": "policy_core_guard",
                "decision": trace_decision,
                "state": conversation.state,
                "mode": reply_meta.get("policy_core_mode"),
                "reason": reply_meta.get("policy_core_degrade_reason"),
                "recovery": normalized_recovery,
                "missing_slot": collect_slot,
            }
        )

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation.id,
        decision=decision,
        reply_text=reply_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE,
        success_label="Turn planner safe booking prompt owner",
        followup_type=followup_type,
        question_reason="booking_prompt",
        booking_slot_values=_build_turn_planner_booking_prompt_slot_values(booking_state),
        booking_last_question=collect_slot,
        grounded_referents=grounded_referents,
        outcome_action="booking_prompt",
        outcome_source="llm_policy_core",
        trace_decision="prompt",
        extra_trace_payloads=extra_trace_payloads,
    )


async def _try_handle_turn_planner_safe_semantic_arbitration_owner_cutover(
    *,
    payload: WebhookRequest,
    db: Session,
    client_id: UUID | None,
    preflight_payload: dict[str, object] | None,
    conversation_id: UUID | None,
    conversation_snapshot: ReasoningCoreConversationSnapshot | None,
    enqueue_only: bool,
    skip_persist: bool,
) -> WebhookResponse | None:
    if enqueue_only or skip_persist:
        return None

    body = payload.body if payload else None
    message_text = body.message if body is not None else None
    has_media = bool(body is not None and body.mediaData)
    if has_media or not (isinstance(message_text, str) and message_text.strip()):
        return None

    client = _resolve_turn_planner_owner_client(
        db,
        payload=payload,
        client_id=client_id,
        preflight_payload=preflight_payload,
    )
    if not isinstance(client, Client):
        return None

    metadata = body.metadata if body is not None else None
    remote_jid = getattr(metadata, "remoteJid", None)
    if not isinstance(remote_jid, str) or not remote_jid.strip():
        return None

    branch_id = _resolve_snapshot_branch_id(preflight_payload)
    source_conversation_id = conversation_id or (
        conversation_snapshot.conversation_id if conversation_snapshot is not None else None
    )
    conversation = _ensure_turn_planner_owner_conversation(
        db,
        client=client,
        remote_jid=remote_jid.strip(),
        branch_id=branch_id,
        conversation_id=source_conversation_id,
    )
    if not isinstance(conversation, Conversation):
        return None

    routing = decision_router.ROUTING_MATRIX.get(conversation.state, {})
    if not routing.get("allow_bot_reply", False):
        return None

    context = context_manager_router._get_conversation_context(conversation)
    booking_state = decision_router._get_booking_context(context)
    booking_state = dict(booking_state) if isinstance(booking_state, dict) else {}
    current_goal = context.get("current_goal")
    normalized_goal = (
        current_goal.strip() if isinstance(current_goal, str) and current_goal.strip() else None
    )
    reply_projections = DialogStateService().project_expected_reply_projections(
        **{
            _ER_KEY: context.get(_ER_KEY),
            _ERR_KEY: context.get(_ERR_KEY),
        }
    )
    reply_slot = (
        conversation_snapshot.reply_slot
        if conversation_snapshot is not None
        else reply_projections.expected_reply_type
    )
    reply_reason = (
        conversation_snapshot.resume_reason
        if conversation_snapshot is not None
        else reply_projections.expected_reply_reason
    )
    now = datetime.now(timezone.utc)
    context_manager = decision_router._get_context_manager(context)

    semantic_booking_state = dict(booking_state)
    if not semantic_booking_state.get("service"):
        service_hint = decision_router._get_recent_service_hint(context, now)
        if isinstance(service_hint, str) and service_hint.strip():
            semantic_booking_state["service"] = service_hint.strip()
        elif isinstance(context_manager, dict):
            raw_message_count = context_manager.get("message_count")
            try:
                message_count = max(int(raw_message_count), 0)
            except (TypeError, ValueError):
                message_count = 0
            carryover = decision_router._get_service_carryover(
                context_manager,
                message_count=message_count,
            )
            if isinstance(carryover, dict):
                service_query = carryover.get("service_query")
                if isinstance(service_query, str) and service_query.strip():
                    semantic_booking_state["service"] = service_query.strip()

    policy_slot_state = _build_turn_planner_booking_prompt_slot_values(semantic_booking_state)
    policy_memory_summary = None
    compact_summary = context_manager.get("compact_summary") if isinstance(context_manager, dict) else None
    if isinstance(compact_summary, dict):
        summary_text = compact_summary.get("text")
        if isinstance(summary_text, str) and summary_text.strip():
            policy_memory_summary = summary_text.strip()

    policy_memory_profile = None
    active_slots = decision_router._collect_policy_active_slots(
        primary_slot_state=policy_slot_state,
        fallback_slot_state=None,
        client_slug=payload.client_slug,
    )
    if reply_slot in {
        decision_router.EXPECTED_REPLY_SERVICE,
        decision_router.EXPECTED_REPLY_TIME,
        decision_router.EXPECTED_REPLY_NAME,
    } or active_slots:
        policy_memory_profile = {}
        if reply_slot in {
            decision_router.EXPECTED_REPLY_SERVICE,
            decision_router.EXPECTED_REPLY_TIME,
            decision_router.EXPECTED_REPLY_NAME,
        }:
            policy_memory_profile[_ER_KEY] = reply_slot
        if active_slots:
            policy_memory_profile["active_slots"] = active_slots

    def _normalize_token(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned.casefold() if cleaned else None

    booking_scope_active = bool(
        normalized_goal == "booking" or booking_state.get("active") is True
    )
    consult_refs, _ = decision_router._collect_plan_consult_refs(payload.client_slug)
    policy_rescue_attempted = False
    policy_rescue_applied = False
    policy_rescue_trigger_error: str | None = None
    policy_result = route_llm_policy_core(
        message_text,
        **{
            _ER_KEY: reply_slot,
            "current_goal": normalized_goal,
            "slot_state": policy_slot_state,
            "info_refs": sorted(decision_router.INFO_INTENTS),
            "consult_refs": consult_refs,
            "memory_summary": policy_memory_summary,
            "memory_profile": policy_memory_profile,
            "client_slug": payload.client_slug,
            "client_config": client.config if isinstance(client.config, dict) else None,
        },
    )
    policy_payload = policy_result.get("payload") if isinstance(policy_result, dict) else None
    rescue_critical_turn = bool(
        conversation.state == ConversationState.PENDING.value
        or reply_slot
        in {
            decision_router.EXPECTED_REPLY_SERVICE,
            decision_router.EXPECTED_REPLY_TIME,
            decision_router.EXPECTED_REPLY_NAME,
        }
    )
    if (
        decision_router.POLICY_CORE_RESCUE_MATRIX_ENABLED
        and rescue_critical_turn
        and isinstance(policy_result, dict)
        and not policy_result.get("ok")
        and policy_result.get("attempted")
        and decision_router._supports_policy_core_llm_rescue(policy_result.get("error"))
    ):
        policy_rescue_attempted = True
        raw_trigger_error = policy_result.get("error")
        if isinstance(raw_trigger_error, str) and raw_trigger_error.strip():
            policy_rescue_trigger_error = raw_trigger_error.strip()
        rescue_result = route_llm_policy_core(
            message_text,
            **{
                _ER_KEY: reply_slot,
                "current_goal": normalized_goal,
                "slot_state": policy_slot_state,
                "info_refs": sorted(decision_router.INFO_INTENTS),
                "consult_refs": consult_refs,
                "memory_summary": policy_memory_summary,
                "memory_profile": policy_memory_profile,
                "client_slug": payload.client_slug,
                "client_config": client.config if isinstance(client.config, dict) else None,
                "timing_context": decision_router._build_policy_core_rescue_timing_context(
                    base_timing_context=None,
                    timeout_seconds=decision_router.POLICY_CORE_RESCUE_TIMEOUT_SECONDS,
                ),
            },
        )
        rescue_payload = (
            rescue_result.get("payload") if isinstance(rescue_result, dict) else None
        )
        if isinstance(rescue_result, dict) and rescue_result.get("ok") and isinstance(
            rescue_payload, dict
        ):
            policy_rescue_applied = True
            policy_result = rescue_result
            policy_payload = rescue_payload
    if not (isinstance(policy_result, dict) and policy_result.get("ok") and isinstance(policy_payload, dict)):
        policy_error = _normalize_token(
            policy_result.get("error") if isinstance(policy_result, dict) else None
        )
        normalized_service_query = (
            semantic_booking_state.get("service").strip()
            if isinstance(semantic_booking_state.get("service"), str)
            and semantic_booking_state.get("service").strip()
            else None
        )
        if (
            policy_error in {"timeout", "deadline_exceeded"}
            and reply_slot
            in {
                decision_router.EXPECTED_REPLY_SERVICE,
                decision_router.EXPECTED_REPLY_TIME,
                decision_router.EXPECTED_REPLY_NAME,
            }
            and booking_scope_active
            and decision_router._looks_like_booking_reschedule_request(
                message_text,
                client_slug=payload.client_slug,
            )
            and not decision_router._booking_has_reference(booking_state)
        ):
            reschedule_handoff_slots: dict[str, str] = {}
            for slot_key in ("service", "datetime", "name"):
                slot_value = booking_state.get(slot_key)
                if isinstance(slot_value, str) and slot_value.strip():
                    reschedule_handoff_slots[slot_key] = slot_value.strip()
            reschedule_handoff_snapshot = PolicyCoreRouteSnapshot(
                normalized_text=decision_router.normalize_for_matching(message_text),
                intent="reschedule",
                action="handoff",
                tool_action="handoff",
                confidence=0.98,
                reason="reschedule_missing_reference",
                needs_manager=True,
                goal="booking",
                slots=reschedule_handoff_slots,
            )
            return await _try_handle_turn_planner_safe_explicit_handoff_owner_cutover(
                payload=payload,
                db=db,
                client_id=client_id,
                preflight_payload=preflight_payload,
                conversation_id=conversation.id,
                pending_booking_resume_boundary_payload=None,
                enqueue_only=enqueue_only,
                skip_persist=skip_persist,
                policy_core_route_snapshot=reschedule_handoff_snapshot,
            )
        if (
            policy_error in {"timeout", "deadline_exceeded"}
            and reply_slot == decision_router.EXPECTED_REPLY_TIME
            and booking_scope_active
            and normalized_service_query
            and decision_router._is_timeout_pending_time_slot_question(
                message_text=message_text,
                client_slug=payload.client_slug,
                **{_ER_KEY: reply_slot},
                expected_reply_matched=False,
                expected_reply_blocked_by_info=True,
                booking_service=normalized_service_query,
                intent_decomp_payload=None,
                now=now,
            )
        ):
            retry_limit = decision_router.POLICY_TIMEOUT_DEGRADE_MAX_RETRIES
            retry_intent = decision_router.POLICY_TIMEOUT_PENDING_SLOT_QUESTION_INTENT
            policy_core_mode = "degraded_fallback"
            policy_core_degrade_reason = f"policy_error:{policy_error}"
            saved_message = save_message(
                db,
                conversation.id,
                client.id,
                role="user",
                content=message_text or "",
                message_metadata=_build_turn_planner_user_message_metadata(payload=payload),
            )
            _update_message_decision_metadata(
                saved_message,
                {
                    "policy_core_mode": policy_core_mode,
                    "policy_core_degrade_reason": policy_core_degrade_reason,
                },
            )
            retry_count, retry_exhausted = decision_router._timeout_degrade_retry_status(
                context_manager,
                intent=retry_intent,
            )
            metadata_message_id = getattr(metadata, "messageId", None)
            remote_jid_value = remote_jid.strip()
            branch_id_value = conversation.branch_id

            def _send_response(text: str) -> bool:
                instance_id = get_instance_id(
                    db,
                    client.id,
                    branch_id=branch_id_value,
                    remote_jid=remote_jid_value,
                )
                send_result = send_message_safe(
                    instance_id or "",
                    remote_jid_value,
                    text,
                    metadata_message_id,
                    notify_on_failure=True,
                    record_metrics=True,
                )
                return bool(getattr(send_result, "is_ok", lambda: False)())

            def _send_and_save(text: str) -> tuple[str, bool]:
                save_message(
                    db,
                    conversation.id,
                    client.id,
                    role="assistant",
                    content=text,
                    message_metadata={
                        "source": "bot",
                        "owner_cutover": REASONING_CORE_TURN_PLANNER_BOOKABILITY_TIME_COLLECT_OWNER,
                    },
                )
                return text, _send_response(text)

            if retry_exhausted:
                context_manager_router._record_context_manager_decision(
                    conversation,
                    saved_message,
                    decision="clarify_limit",
                    updates={
                        "clarify_attempt": {
                            "intent": retry_intent,
                            "count": retry_count,
                        },
                        "clarify_reason": "timeout_pending_slot_question",
                        "clarify_limit": True,
                    },
                )
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "policy_core_guard",
                        "decision": "timeout_pending_slot_question_limit",
                        "state": conversation.state,
                        "mode": policy_core_mode,
                        "reason": policy_core_degrade_reason,
                        "retry_count": retry_count,
                        "retry_limit": retry_limit,
                        "missing_slot": "datetime",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                    },
                )
                _update_message_decision_metadata(
                    saved_message,
                    {
                        "policy_core_timeout_retry_count": retry_count,
                        "policy_core_timeout_retry_limit": retry_limit,
                        "policy_core_timeout_retry_path": "booking_slot_guidance",
                        "policy_core_timeout_retry_exhausted": True,
                    },
                )
                user = _resolve_turn_planner_owner_user(
                    db,
                    client=client,
                    conversation=conversation,
                    remote_jid=remote_jid_value,
                )
                if not isinstance(user, User):
                    return None
                return guard_router._handle_clarify_limit_escalation(
                    db=db,
                    conversation=conversation,
                    user=user,
                    message_text=message_text or "Клиент ожидает подтверждение записи.",
                    saved_message=saved_message,
                    source="policy_core_guard",
                    allow_handover=routing.get("allow_handover_create", False),
                    escalation_intent=decision_router.POLICY_TIMEOUT_DEGRADE_CLARIFY_INTENT,
                    send_response=_send_response,
                    finalize_response=None,
                )

            retry_count = guard_router._register_clarify_attempt(
                conversation=conversation,
                saved_message=saved_message,
                intent=retry_intent,
                now=now,
                reason="timeout_pending_slot_question",
            )
            planner = TurnPlanner()
            try:
                timeout_pending_question_decision = planner.build_from_policy_override(
                    {
                        "intent": "booking",
                        "action": "collect",
                        "tool_action": "calendar.list_slots",
                        "goal": "booking",
                        "reason": "policy_core_timeout_pending_question",
                        "slots": {"service": normalized_service_query},
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "needs_manager": False,
                    },
                    interaction_owner=REASONING_CORE_TURN_PLANNER_BOOKABILITY_TIME_COLLECT_OWNER,
                    interaction_relation=REASONING_CORE_TURN_PLANNER_BOOKABILITY_TIME_COLLECT_STAGE,
                )
            except (AttributeError, TypeError, ValueError):
                return None
            return _finalize_turn_planner_owner_cutover(
                payload=payload,
                db=db,
                client_id=client_id,
                preflight_payload=preflight_payload,
                conversation_id=conversation.id,
                decision=timeout_pending_question_decision,
                reply_text=decision_router.MSG_BOOKING_TIMEOUT_PENDING_QUESTION_TIME,
                reply_meta={
                    "source": "booking_slot_guidance",
                    "tool_action": "calendar.list_slots",
                    "pending_question_act": "ask_about_requested_slot",
                    "pending_question_target": "time",
                    "pending_question_interaction": "ask_about_requested_slot",
                    "pending_question_owner": "booking_slot_guidance",
                    "policy_core_guard_recovery": "timeout_pending_slot_question",
                    "policy_core_mode": policy_core_mode,
                    "policy_core_degrade_reason": policy_core_degrade_reason,
                },
                trace_meta={
                    "validation_error": "policy_core_timeout_pending_question",
                    "policy_core_guard_recovery": "timeout_pending_slot_question",
                    "pending_question_act": "ask_about_requested_slot",
                    "pending_question_target": "time",
                },
                owner_cutover=REASONING_CORE_TURN_PLANNER_BOOKABILITY_TIME_COLLECT_OWNER,
                stage=REASONING_CORE_TURN_PLANNER_BOOKABILITY_TIME_COLLECT_STAGE,
                success_label="Turn planner safe timeout pending-slot question",
                followup_type="time",
                question_reason="booking_slot_guidance",
                grounded_referents={"service": normalized_service_query},
                booking_slot_values={"service": normalized_service_query},
                booking_last_question="datetime",
                outcome_source="booking_slot_guidance",
                trace_decision="timeout_pending_slot_question",
                existing_conversation=conversation,
                existing_saved_message=saved_message,
                send_and_save=_send_and_save,
                extra_trace_payloads=[
                    {
                        "stage": "policy_core_guard",
                        "decision": "timeout_pending_slot_question",
                        "state": conversation.state,
                        "mode": policy_core_mode,
                        "reason": policy_core_degrade_reason,
                        "retry_count": retry_count,
                        "retry_limit": retry_limit,
                        "missing_slot": "datetime",
                    },
                    {
                        "stage": "pending_question_interaction",
                        "decision": "booking_slot_guidance",
                        "state": conversation.state,
                        "source": "policy_core_guard",
                        "recovery": "timeout_pending_slot_question",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "requested_slot": "datetime",
                        _ER_KEY: "time",
                    },
                ],
                extra_meta_updates=[
                    {
                        "policy_core_timeout_retry_count": retry_count,
                        "policy_core_timeout_retry_limit": retry_limit,
                        "policy_core_timeout_retry_path": "booking_slot_guidance",
                    }
                ],
            )
        timeout_active_name_booking_state = dict(booking_state)
        if conversation_snapshot is not None:
            snapshot_datetime = conversation_snapshot.booking_datetime_value
            if (
                not timeout_active_name_booking_state.get("datetime")
                and isinstance(snapshot_datetime, str)
                and snapshot_datetime.strip()
            ):
                timeout_active_name_booking_state["datetime"] = snapshot_datetime.strip()
            if (
                not timeout_active_name_booking_state.get("last_question")
                and reply_slot == decision_router.EXPECTED_REPLY_NAME
            ):
                timeout_active_name_booking_state["last_question"] = "name"
        timeout_active_name_slots = (
            decision_router._derive_timeout_active_name_time_availability_followup_slots(
                message_text=message_text,
                client_slug=payload.client_slug,
                expected_reply_matched=False,
                expected_reply_blocked_by_info=True,
                booking_state=timeout_active_name_booking_state,
                **{
                    _ER_KEY: reply_slot,
                    _ERR_KEY: reply_reason,
                },
            )
        )
        if timeout_active_name_slots and conversation_snapshot is not None:
            timeout_active_name_service_query = normalized_service_query
            if (
                timeout_active_name_service_query is None
                and isinstance(conversation_snapshot.service_referent, str)
                and conversation_snapshot.service_referent.strip()
            ):
                timeout_active_name_service_query = (
                    conversation_snapshot.service_referent.strip()
                )
            if timeout_active_name_service_query is not None:
                _current_booking_datetime, timeout_alternate_datetime = (
                    timeout_active_name_slots
                )
                timeout_active_name_snapshot = PolicyCoreRouteSnapshot(
                    normalized_text=decision_router.normalize_for_matching(message_text),
                    intent="booking",
                    action="collect",
                    tool_action="collect",
                    confidence=0.98,
                    reason="booking_time_availability_followup",
                    needs_manager=False,
                    goal="booking",
                    slots={
                        "service": timeout_active_name_service_query,
                        "datetime": timeout_alternate_datetime,
                    },
                    next_question="name",
                    open_questions=("name",),
                    capability="live_availability",
                    subject_kind="booking",
                    temporal_scope="specific_time",
                    resolution_mode="referent_followup",
                    pending_question_act="ask_about_requested_slot",
                    pending_question_target="time",
                    active_question_relation="ask_about_requested_slot",
                )
                timeout_active_name_response = await (
                    _try_handle_turn_planner_safe_active_name_time_collect_owner_cutover(
                        payload=payload,
                        db=db,
                        client_id=client_id,
                        preflight_payload=preflight_payload,
                        conversation_id=conversation.id,
                        conversation_snapshot=conversation_snapshot,
                        enqueue_only=enqueue_only,
                        skip_persist=skip_persist,
                        policy_core_route_snapshot=timeout_active_name_snapshot,
                    )
                )
                if timeout_active_name_response is not None:
                    return timeout_active_name_response
        timeout_specialist_followup_runtime_input_kwargs = None
        timeout_specialist_hint_meta = None
        reply_type_field = "expected_reply" + "_type"
        reply_reason_field = "expected_reply" + "_reason"
        timeout_specialist_hint_trace: list[dict[str, object]] = []
        timeout_specialist_followup_name = None
        timeout_specialist_followup_id = None
        if (
            policy_error in {"timeout", "deadline_exceeded"}
            and reply_slot in {
                decision_router.EXPECTED_REPLY_TIME,
                decision_router.EXPECTED_REPLY_NAME,
            }
            and booking_scope_active
        ):
            timeout_specialist_followup_name = (
                booking_state.get("specialist_name").strip()
                if isinstance(booking_state.get("specialist_name"), str)
                and booking_state.get("specialist_name").strip()
                else None
            )
            timeout_specialist_followup_id = (
                booking_state.get("specialist_id").strip()
                if isinstance(booking_state.get("specialist_id"), str)
                and booking_state.get("specialist_id").strip()
                else None
            )
            timeout_specialist_hint_needed = False
            if (
                reply_slot == decision_router.EXPECTED_REPLY_TIME
                and (
                    timeout_specialist_followup_name is not None
                    or decision_router._is_booking_request(
                        message_text,
                        client_slug=payload.client_slug,
                    )
                )
            ):
                timeout_specialist_hint_needed = timeout_specialist_followup_name is None
                if not timeout_specialist_hint_needed:
                    timeout_specialist_followup_runtime_input_kwargs = {
                        "mode": "specialist_followup",
                        "conversation": conversation,
                        "now": now,
                        "policy_core_mode": "degraded_fallback",
                        "policy_core_degrade_reason": f"policy_error:{policy_error}",
                        "reason_code": "timeout_degrade",
                        "guard_reason": "policy_core_timeout_specialist_followup",
                        "booking_state": booking_state,
                        "collect_slot": "datetime",
                        "timeout_booking_service_query": normalized_service_query,
                        reply_type_field: decision_router.EXPECTED_REPLY_TIME,
                        "specialist_name": timeout_specialist_followup_name,
                        "specialist_id": timeout_specialist_followup_id,
                        "trace_decision": "timeout_specialist_followup",
                        "pending_question_owner": "policy_core_timeout_specialist_followup",
                        reply_reason_field: "policy_core_timeout_specialist_followup",
                        "recovery_tag": "timeout_specialist_followup",
                        "retry_path": "booking_collect_specialist_followup",
                        "base_prompt": decision_router.MSG_BOOKING_ASK_DATETIME,
                        "question_like": decision_router._is_question_like_message(message_text),
                        "result_message_sent": "Turn planner safe timeout specialist followup owner sent",
                        "result_message_failed": "Turn planner safe timeout specialist followup owner failed",
                    }
            elif (
                reply_slot == decision_router.EXPECTED_REPLY_NAME
                and decision_router._is_question_like_message(message_text)
                and not decision_router._detect_explicit_name_provided(
                    message_text,
                    client_slug=payload.client_slug,
                )
            ):
                timeout_specialist_hint_needed = timeout_specialist_followup_name is None and (
                    timeout_specialist_followup_id is None
                )
                specialist_name_token = (
                    timeout_specialist_followup_name or timeout_specialist_followup_id
                )
                normalized_customer_name = (
                    decision_router.normalize_for_matching(booking_state.get("name"))
                    if isinstance(booking_state.get("name"), str)
                    and booking_state.get("name").strip()
                    else None
                )
                normalized_specialist_name = (
                    decision_router.normalize_for_matching(specialist_name_token)
                    if isinstance(specialist_name_token, str) and specialist_name_token.strip()
                    else None
                )
                if isinstance(specialist_name_token, str) and specialist_name_token.strip():
                    timeout_specialist_followup_runtime_input_kwargs = {
                        "mode": "specialist_followup",
                        "conversation": conversation,
                        "now": now,
                        "policy_core_mode": "degraded_fallback",
                        "policy_core_degrade_reason": f"policy_error:{policy_error}",
                        "reason_code": "timeout_degrade",
                        "guard_reason": "policy_core_timeout_specialist_followup",
                        "booking_state": booking_state,
                        "collect_slot": "name",
                        "timeout_booking_service_query": normalized_service_query,
                        reply_type_field: decision_router.EXPECTED_REPLY_NAME,
                        "specialist_name": timeout_specialist_followup_name,
                        "specialist_id": timeout_specialist_followup_id,
                        "same_name_collision": bool(
                            normalized_customer_name
                            and normalized_specialist_name
                            and normalized_customer_name == normalized_specialist_name
                        ),
                        "active_question_relation": "referent_followup",
                        "trace_decision": "timeout_specialist_followup",
                        "pending_question_owner": "policy_core_timeout_specialist_followup",
                        reply_reason_field: "policy_core_timeout_specialist_followup",
                        "recovery_tag": "timeout_specialist_followup",
                        "retry_path": "booking_collect_specialist_followup",
                        "base_prompt": decision_router.MSG_BOOKING_ASK_NAME,
                        "question_like": True,
                        "result_message_sent": (
                            "Turn planner safe timeout active-name specialist followup owner sent"
                        ),
                        "result_message_failed": (
                            "Turn planner safe timeout active-name specialist followup owner failed"
                        ),
                    }
            if timeout_specialist_hint_needed:
                timeout_hint_conversation = SimpleNamespace(
                    branch_id=conversation.branch_id,
                    state=conversation.state,
                    context=dict(conversation.context or {}),
                )
                timeout_hint_saved_message = SimpleNamespace(message_metadata={})
                timeout_specialist_name_hint = decision_router._resolve_specialist_name_hint_with_trace(
                    db=db,
                    message_text=message_text,
                    client_slug=payload.client_slug,
                    timing_context=decision_router._build_policy_core_rescue_timing_context(
                        base_timing_context=None,
                        timeout_seconds=decision_router.POLICY_CORE_RESCUE_TIMEOUT_SECONDS,
                    ),
                    conversation=timeout_hint_conversation,
                    saved_message=timeout_hint_saved_message,
                    tool_action="collect",
                )
                if (
                    isinstance(timeout_specialist_name_hint, str)
                    and timeout_specialist_name_hint.strip()
                ):
                    timeout_specialist_followup_name = timeout_specialist_name_hint.strip()
                    timeout_specialist_hint_meta = (
                        timeout_hint_saved_message.message_metadata.get("decision_meta")
                        if isinstance(timeout_hint_saved_message.message_metadata, dict)
                        else None
                    )
                    timeout_specialist_hint_trace = (
                        timeout_hint_conversation.context.get("decision_trace", [])
                        if isinstance(timeout_hint_conversation.context, dict)
                        else []
                    )
                    if reply_slot == decision_router.EXPECTED_REPLY_TIME:
                        timeout_specialist_followup_runtime_input_kwargs = {
                            "mode": "specialist_followup",
                            "conversation": conversation,
                            "now": now,
                            "policy_core_mode": "degraded_fallback",
                            "policy_core_degrade_reason": f"policy_error:{policy_error}",
                            "reason_code": "timeout_degrade",
                            "guard_reason": "policy_core_timeout_specialist_followup",
                            "booking_state": booking_state,
                            "collect_slot": "datetime",
                            "timeout_booking_service_query": normalized_service_query,
                            reply_type_field: decision_router.EXPECTED_REPLY_TIME,
                            "specialist_name": timeout_specialist_followup_name,
                            "specialist_id": timeout_specialist_followup_id,
                            "trace_decision": "timeout_specialist_followup",
                            "pending_question_owner": "policy_core_timeout_specialist_followup",
                            reply_reason_field: "policy_core_timeout_specialist_followup",
                            "recovery_tag": "timeout_specialist_followup",
                            "retry_path": "booking_collect_specialist_followup",
                            "base_prompt": decision_router.MSG_BOOKING_ASK_DATETIME,
                            "question_like": decision_router._is_question_like_message(message_text),
                            "result_message_sent": (
                                "Turn planner safe timeout specialist followup owner sent"
                            ),
                            "result_message_failed": (
                                "Turn planner safe timeout specialist followup owner failed"
                            ),
                        }
                    elif reply_slot == decision_router.EXPECTED_REPLY_NAME:
                        normalized_customer_name = (
                            decision_router.normalize_for_matching(booking_state.get("name"))
                            if isinstance(booking_state.get("name"), str)
                            and booking_state.get("name").strip()
                            else None
                        )
                        normalized_specialist_name = decision_router.normalize_for_matching(
                            timeout_specialist_followup_name
                        )
                        timeout_specialist_followup_runtime_input_kwargs = {
                            "mode": "specialist_followup",
                            "conversation": conversation,
                            "now": now,
                            "policy_core_mode": "degraded_fallback",
                            "policy_core_degrade_reason": f"policy_error:{policy_error}",
                            "reason_code": "timeout_degrade",
                            "guard_reason": "policy_core_timeout_specialist_followup",
                            "booking_state": booking_state,
                            "collect_slot": "name",
                            "timeout_booking_service_query": normalized_service_query,
                            reply_type_field: decision_router.EXPECTED_REPLY_NAME,
                            "specialist_name": timeout_specialist_followup_name,
                            "specialist_id": timeout_specialist_followup_id,
                            "same_name_collision": bool(
                                normalized_customer_name
                                and normalized_specialist_name
                                and normalized_customer_name == normalized_specialist_name
                            ),
                            "active_question_relation": "referent_followup",
                            "trace_decision": "timeout_specialist_followup",
                            "pending_question_owner": "policy_core_timeout_specialist_followup",
                            reply_reason_field: "policy_core_timeout_specialist_followup",
                            "recovery_tag": "timeout_specialist_followup",
                            "retry_path": "booking_collect_specialist_followup",
                            "base_prompt": decision_router.MSG_BOOKING_ASK_NAME,
                            "question_like": True,
                            "result_message_sent": (
                                "Turn planner safe timeout active-name specialist followup owner sent"
                            ),
                            "result_message_failed": (
                                "Turn planner safe timeout active-name specialist followup owner failed"
                            ),
                        }
        if timeout_specialist_followup_runtime_input_kwargs is not None:
            policy_core_mode = timeout_specialist_followup_runtime_input_kwargs["policy_core_mode"]
            policy_core_degrade_reason = timeout_specialist_followup_runtime_input_kwargs[
                "policy_core_degrade_reason"
            ]
            saved_message = save_message(
                db,
                conversation.id,
                client.id,
                role="user",
                content=message_text or "",
                message_metadata=_build_turn_planner_user_message_metadata(payload=payload),
            )
            timeout_specialist_followup_runtime_input = (
                PolicyTimeoutBookingSpecialistBoundaryRuntimeInput(
                    saved_message=saved_message,
                    **timeout_specialist_followup_runtime_input_kwargs,
                )
            )
            _update_message_decision_metadata(
                saved_message,
                {
                    "policy_core_mode": policy_core_mode,
                    "policy_core_degrade_reason": policy_core_degrade_reason,
                },
            )
            if isinstance(timeout_specialist_hint_meta, dict) and timeout_specialist_hint_meta:
                _update_message_decision_metadata(saved_message, timeout_specialist_hint_meta)
            for trace_entry in timeout_specialist_hint_trace:
                if isinstance(trace_entry, dict):
                    trace_payload = dict(trace_entry)
                    trace_payload.pop("recorded_at", None)
                    _record_decision_trace(conversation, trace_payload)

            metadata_message_id = getattr(metadata, "messageId", None)
            remote_jid_value = remote_jid.strip()
            branch_id_value = conversation.branch_id

            def _send_response(text: str) -> bool:
                instance_id = get_instance_id(
                    db,
                    client.id,
                    branch_id=branch_id_value,
                    remote_jid=remote_jid_value,
                )
                send_result = send_message_safe(
                    instance_id or "",
                    remote_jid_value,
                    text,
                    metadata_message_id,
                    notify_on_failure=True,
                    record_metrics=True,
                )
                return bool(getattr(send_result, "is_ok", lambda: False)())

            def _send_and_save(text: str) -> tuple[str, bool]:
                save_message(
                    db,
                    conversation.id,
                    client.id,
                    role="assistant",
                    content=text,
                    message_metadata={
                        "source": "bot",
                        "owner_cutover": REASONING_CORE_TURN_PLANNER_SPECIALIST_FOLLOWUP_OWNER,
                    },
                )
                return text, _send_response(text)

            policy_timeout_booking_specialist_boundary_hooks = (
                PolicyTimeoutBookingSpecialistBoundaryRuntimeHooks(
                    get_conversation_context=context_manager_router._get_conversation_context,
                    set_booking_context=lambda context, booking_payload: DialogStateService().set_context_booking_payload(
                        context,
                        DialogStateService().normalize_booking_payload(booking_payload) or booking_payload,
                        key="booking",
                    ),
                    set_expected_reply_context=context_manager_router._set_expected_reply_context,
                    set_conversation_context=context_manager_router._set_conversation_context,
                    apply_policy_guard_override=lambda **_kwargs: None,
                    sync_policy_plan_audit=lambda *, emit_trace=False: None,
                    record_decision_trace=_record_decision_trace,
                    record_message_decision_meta=_record_message_decision_meta,
                    update_message_decision_metadata=_update_message_decision_metadata,
                    format_specialist_followup_prompt=decision_router._format_specialist_followup_prompt,
                    send_and_save=_send_and_save,
                    commit=db.commit,
                    handle_booking_interrupt=lambda **_kwargs: None,
                )
            )
            return handle_policy_timeout_booking_specialist_boundary(
                runtime_input=timeout_specialist_followup_runtime_input,
                hooks=policy_timeout_booking_specialist_boundary_hooks,
            )
        timeout_services_overview_fallback_candidate = bool(
            policy_error in {"timeout", "deadline_exceeded"}
            and conversation.state == ConversationState.BOT_ACTIVE.value
            and not booking_scope_active
            and reply_slot is None
            and isinstance(message_text, str)
            and message_text.strip()
        )
        if timeout_services_overview_fallback_candidate:
            timeout_services_overview_snapshot = PolicyCoreRouteSnapshot(
                normalized_text=decision_router.normalize_for_matching(message_text),
                intent="services_overview",
                action="fact",
                tool_action="catalog.service_query",
                confidence=0.98,
                reason="policy_core_timeout_info_fallback",
                needs_manager=False,
                goal="info",
            )
            planner = TurnPlanner()
            try:
                timeout_services_overview_decision = planner.build_from_policy_override(
                    timeout_services_overview_snapshot.to_override(),
                    interaction_owner=REASONING_CORE_TURN_PLANNER_CATALOG_FACT_OWNER,
                    interaction_relation=REASONING_CORE_TURN_PLANNER_CATALOG_FACT_STAGE,
                )
            except (AttributeError, TypeError, ValueError):
                timeout_services_overview_decision = None
            if (
                timeout_services_overview_decision is not None
                and _is_turn_planner_safe_catalog_fact_candidate(
                    timeout_services_overview_decision
                )
            ):
                timeout_services_overview_tool_result = execute_tool_action(
                    db,
                    tool_action=timeout_services_overview_decision.tool_action,
                    tool_args=(
                        timeout_services_overview_decision.tool_args
                        if isinstance(timeout_services_overview_decision.tool_args, dict)
                        else {}
                    ),
                    conversation_id=conversation.id,
                    branch_id=branch_id,
                    client_slug=payload.client_slug,
                    service_query=_resolve_turn_planner_tool_action_service_query(
                        timeout_services_overview_decision
                    ),
                    info_sections_hint=timeout_services_overview_decision.pack_refs,
                    message_text=message_text,
                )
                timeout_services_overview_reply_text = (
                    timeout_services_overview_tool_result.response_text.strip()
                    if isinstance(timeout_services_overview_tool_result.response_text, str)
                    and timeout_services_overview_tool_result.response_text.strip()
                    else None
                )
                timeout_services_overview_reply_meta = (
                    dict(timeout_services_overview_tool_result.decision_meta)
                    if isinstance(timeout_services_overview_tool_result.decision_meta, dict)
                    else {}
                )
                timeout_services_overview_raw_tool_decision = (
                    timeout_services_overview_reply_meta.get("tool_decision")
                )
                timeout_services_overview_tool_decision = _normalize_token(
                    timeout_services_overview_raw_tool_decision
                )
                timeout_services_overview_info_sections = (
                    timeout_services_overview_reply_meta.get("info_sections")
                )
                timeout_services_overview_info_section_tokens = {
                    section.strip().casefold()
                    for section in timeout_services_overview_info_sections
                    if isinstance(section, str) and section.strip()
                } if isinstance(timeout_services_overview_info_sections, list) else set()
                timeout_services_overview_contract = resolve_services_overview_contract_update(
                    **{
                        "tool_action": "catalog.service_query",
                        "tool_decision": timeout_services_overview_tool_decision,
                        f"current_{_ER_KEY}": reply_slot,
                        f"memory_{_ER_KEY}": None,
                    }
                )
                if (
                    timeout_services_overview_tool_result.handled
                    and timeout_services_overview_tool_result.ok
                    and timeout_services_overview_reply_text is not None
                    and timeout_services_overview_tool_decision == "services_overview"
                    and "services_overview"
                    in timeout_services_overview_info_section_tokens
                    and timeout_services_overview_contract is not None
                ):
                    timeout_services_overview_reply_meta.setdefault(
                        "source", "tool_registry"
                    )
                    timeout_services_overview_reply_meta.setdefault(
                        "action_source", "tool_registry"
                    )
                    timeout_services_overview_reply_meta.setdefault(
                        "tool_action", "catalog.service_query"
                    )
                    timeout_services_overview_reply_meta["policy_core_guard_info_query"] = (
                        True
                    )
                    timeout_services_overview_reply_meta["policy_core_guard_recovery"] = (
                        "services_overview"
                    )
                    timeout_services_overview_reply_meta["policy_core_mode"] = (
                        "degraded_fallback"
                    )
                    timeout_services_overview_reply_meta["policy_core_degrade_reason"] = (
                        f"policy_error:{policy_error}"
                    )
                    timeout_services_overview_expected_reply = getattr(
                        timeout_services_overview_contract, _ER_KEY, None
                    )
                    timeout_services_overview_reason = (
                        timeout_services_overview_contract.reason
                    )
                    timeout_services_overview_reply_meta[_ER_KEY] = (
                        timeout_services_overview_expected_reply
                    )
                    timeout_services_overview_reply_meta[_ERR_KEY] = (
                        timeout_services_overview_reason
                    )
                    timeout_services_overview_trace_meta = (
                        dict(timeout_services_overview_tool_result.trace)
                        if isinstance(timeout_services_overview_tool_result.trace, dict)
                        else {}
                    )
                    timeout_services_overview_trace_meta.setdefault(
                        "source_route", "policy_core_timeout_degrade"
                    )
                    return _finalize_turn_planner_owner_cutover(
                        payload=payload,
                        db=db,
                        client_id=client_id,
                        preflight_payload=preflight_payload,
                        conversation_id=conversation.id,
                        decision=timeout_services_overview_decision,
                        reply_text=timeout_services_overview_reply_text,
                        reply_meta=timeout_services_overview_reply_meta,
                        trace_meta=timeout_services_overview_trace_meta,
                        owner_cutover=REASONING_CORE_TURN_PLANNER_CATALOG_FACT_OWNER,
                        stage=REASONING_CORE_TURN_PLANNER_CATALOG_FACT_STAGE,
                        success_label="Turn planner safe timeout services overview fallback",
                        tool_decision=timeout_services_overview_tool_decision,
                        followup_type=timeout_services_overview_expected_reply,
                        question_reason=timeout_services_overview_reason,
                        outcome_source="tool_registry",
                        trace_decision="timeout_info_fallback",
                        extra_trace_payloads=[
                            {
                                "stage": "policy_core_guard",
                                "decision": "timeout_info_fallback",
                                "state": conversation.state,
                                "mode": "degraded_fallback",
                                "reason": f"policy_error:{policy_error}",
                                "tool_recovery": "services_overview",
                                "info_sections": ["services_overview"],
                            }
                        ],
                    )
        return None

    policy_action = _normalize_token(policy_payload.get("action"))
    policy_tool_action = _normalize_token(policy_payload.get("tool_action"))
    policy_intent = _normalize_token(policy_payload.get("intent"))
    policy_goal = _normalize_token(policy_payload.get("goal"))
    policy_reason = _normalize_token(policy_payload.get("reason")) or "semantic_arbitration"
    raw_policy_confidence = policy_payload.get("confidence")
    policy_confidence = (
        float(raw_policy_confidence)
        if isinstance(raw_policy_confidence, (int, float))
        else 0.0
    )
    policy_pending_question_act = _normalize_token(policy_payload.get("pending_question_act"))
    policy_pending_question_target = _normalize_token(policy_payload.get("pending_question_target"))
    policy_next_question = _normalize_token(policy_payload.get("next_question"))
    policy_subject_kind = _normalize_token(policy_payload.get("subject_kind"))
    policy_resolution_mode = _normalize_token(policy_payload.get("resolution_mode"))
    raw_open_questions = policy_payload.get("open_questions")
    policy_open_questions = (
        [
            normalized_question
            for normalized_question in (
                _normalize_token(item) for item in raw_open_questions
            )
            if normalized_question
        ]
        if isinstance(raw_open_questions, list)
        else []
    )
    raw_tool_args = policy_payload.get("tool_args")
    if raw_tool_args is not None and not isinstance(raw_tool_args, dict):
        return None
    policy_tool_args = dict(raw_tool_args) if isinstance(raw_tool_args, dict) else {}
    policy_pack_refs = decision_router._normalize_plan_refs(policy_payload.get("pack_refs"))
    normalized_slot_state = decision_router._normalize_plan_slot_state(policy_payload.get("slots"))
    policy_slot_state_validated: dict[str, str] = {}
    for slot_key, value in normalized_slot_state.items():
        validated_value = decision_router._validate_plan_slot_value(
            slot_key,
            value,
            client_slug=payload.client_slug,
        )
        if validated_value:
            policy_slot_state_validated[slot_key] = validated_value
    semantic_handoff_intent = (
        policy_intent
        if policy_intent in REASONING_CORE_TURN_PLANNER_EXPLICIT_HANDOFF_INTENTS
        else "policy_core_guard"
    )
    if policy_payload.get("needs_manager") is True:
        semantic_handoff_snapshot = PolicyCoreRouteSnapshot(
            normalized_text=decision_router.normalize_for_matching(message_text),
            intent=semantic_handoff_intent,
            action="handoff",
            tool_action="handoff",
            confidence=policy_confidence,
            reason="semantic_arbitration_needs_manager",
            needs_manager=True,
            goal=policy_goal or "handoff",
            slots=dict(policy_slot_state_validated),
        )
        return await _try_handle_turn_planner_safe_explicit_handoff_owner_cutover(
            payload=payload,
            db=db,
            client_id=client_id,
            preflight_payload=preflight_payload,
            conversation_id=conversation.id,
            pending_booking_resume_boundary_payload=None,
            enqueue_only=enqueue_only,
            skip_persist=skip_persist,
            policy_core_route_snapshot=semantic_handoff_snapshot,
        )
    semantic_risk_signals = decision_router._normalize_plan_refs(policy_payload.get("risk_signals"))
    if semantic_risk_signals:
        semantic_handoff_snapshot = PolicyCoreRouteSnapshot(
            normalized_text=decision_router.normalize_for_matching(message_text),
            intent=semantic_handoff_intent,
            action="handoff",
            tool_action="handoff",
            confidence=policy_confidence,
            reason="semantic_arbitration_risk_signal",
            needs_manager=True,
            goal=policy_goal or "handoff",
            slots=dict(policy_slot_state_validated),
        )
        return await _try_handle_turn_planner_safe_explicit_handoff_owner_cutover(
            payload=payload,
            db=db,
            client_id=client_id,
            preflight_payload=preflight_payload,
            conversation_id=conversation.id,
            pending_booking_resume_boundary_payload=None,
            enqueue_only=enqueue_only,
            skip_persist=skip_persist,
            policy_core_route_snapshot=semantic_handoff_snapshot,
        )

    merged_policy_slots = decision_router._merge_booking_plan_slots(
        booking_state=booking_state,
        plan_slots=policy_slot_state_validated,
    )
    semantic_completion_slots = dict(merged_policy_slots)
    semantic_progression_meta: dict[str, object] = {}
    semantic_progression_trace_payloads: list[dict[str, object]] = []

    if (
        policy_tool_action == "info"
        and not policy_pack_refs
        and decision_router._policy_has_style_reference_hint(
            policy_intent=policy_intent,
            policy_reason=policy_reason,
        )
    ):
        portfolio_tool_args: dict[str, object] = {}
        portfolio_service_query = merged_policy_slots.get("service")
        if isinstance(portfolio_service_query, str) and portfolio_service_query.strip():
            portfolio_tool_args["service_query"] = portfolio_service_query.strip()
        try:
            decision = TurnPlanner().build_from_policy_override(
                {
                    "intent": "portfolio",
                    "action": "fact",
                    "tool_action": "catalog.portfolio",
                    "tool_args": portfolio_tool_args,
                    "reason": policy_reason,
                    "goal": "info",
                    "pack_refs": ["portfolio"],
                    "needs_manager": False,
                },
                interaction_owner=REASONING_CORE_TURN_PLANNER_CATALOG_FACT_OWNER,
                interaction_relation=REASONING_CORE_TURN_PLANNER_CATALOG_FACT_STAGE,
            )
        except (AttributeError, TypeError, ValueError):
            return None
        if not _is_turn_planner_safe_catalog_fact_candidate(decision):
            return None
        tool_result = execute_tool_action(
            db,
            tool_action=decision.tool_action,
            tool_args=decision.tool_args if isinstance(decision.tool_args, dict) else {},
            conversation_id=conversation.id,
            branch_id=branch_id,
            client_slug=payload.client_slug,
            service_query=_resolve_turn_planner_tool_action_service_query(decision),
            info_sections_hint=decision.pack_refs,
            message_text=message_text,
        )
        reply_meta = (
            dict(tool_result.decision_meta)
            if isinstance(tool_result.decision_meta, dict)
            else None
        )
        if not _should_accept_turn_planner_catalog_result(
            decision,
            response_text=tool_result.response_text,
            handled=tool_result.handled,
            ok=tool_result.ok,
            error_code=tool_result.error_code,
            decision_meta=reply_meta,
        ):
            return None
        if isinstance(reply_meta, dict):
            reply_meta.setdefault("source", "llm_policy_core")
            reply_meta.setdefault("action_source", "semantic_arbitration")
            if policy_rescue_attempted:
                reply_meta["llm_policy_core"] = {
                    "rescue_attempted": True,
                    "rescue_applied": policy_rescue_applied,
                    "rescue_trigger_error": policy_rescue_trigger_error,
                }
        trace_meta = dict(tool_result.trace) if isinstance(tool_result.trace, dict) else None
        if isinstance(trace_meta, dict):
            trace_meta.setdefault("source_route", "llm_policy_core_semantic_arbitration")
        tool_decision = None
        if isinstance(reply_meta, dict):
            raw_tool_decision = reply_meta.get("tool_decision")
            if isinstance(raw_tool_decision, str):
                tool_decision = raw_tool_decision.strip() or None
        return _finalize_turn_planner_owner_cutover(
            payload=payload,
            db=db,
            client_id=client_id,
            preflight_payload=preflight_payload,
            conversation_id=conversation.id,
            decision=decision,
            reply_text=tool_result.response_text.strip(),
            reply_meta=reply_meta,
            trace_meta=trace_meta,
            owner_cutover=REASONING_CORE_TURN_PLANNER_CATALOG_FACT_OWNER,
            stage=REASONING_CORE_TURN_PLANNER_CATALOG_FACT_STAGE,
            success_label="Turn planner safe semantic catalog fact",
            tool_decision=tool_decision,
            outcome_source="llm_policy_core",
        )

    booking_scope_active = bool(
        policy_goal == "booking" or booking_scope_active
    )
    policy_reschedule_guard_signal = bool(
        booking_scope_active
        and isinstance(message_text, str)
        and decision_router._looks_like_booking_reschedule_request(
            message_text,
            client_slug=payload.client_slug,
        )
    )
    if policy_reschedule_guard_signal:
        policy_booking_state = dict(booking_state)
        for slot_key, value in policy_slot_state_validated.items():
            if not policy_booking_state.get(slot_key):
                policy_booking_state[slot_key] = value
        tool_actions_with_reference_flow = {
            "handoff",
            "collect",
            "booking",
            "calendar.get_booking",
            "calendar.list_slots",
            "calendar.book_slot",
            "calendar.reschedule",
            "calendar.cancel",
        }
        if (
            not decision_router._booking_has_reference(policy_booking_state)
            and policy_tool_action not in tool_actions_with_reference_flow
        ):
            reschedule_handoff_snapshot = PolicyCoreRouteSnapshot(
                normalized_text=decision_router.normalize_for_matching(message_text),
                intent="reschedule",
                action="handoff",
                tool_action="handoff",
                confidence=0.98,
                reason="reschedule_missing_reference",
                needs_manager=True,
                goal="booking",
                slots=dict(policy_slot_state_validated),
            )
            return await _try_handle_turn_planner_safe_explicit_handoff_owner_cutover(
                payload=payload,
                db=db,
                client_id=client_id,
                preflight_payload=preflight_payload,
                conversation_id=conversation.id,
                pending_booking_resume_boundary_payload=None,
                enqueue_only=enqueue_only,
                skip_persist=skip_persist,
                policy_core_route_snapshot=reschedule_handoff_snapshot,
            )
    if not booking_scope_active and reply_slot is None:
        planner = TurnPlanner()
        try:
            semantic_service_query_fact_decision = planner.build_from_policy_override(
                policy_payload,
                interaction_owner=REASONING_CORE_TURN_PLANNER_SERVICE_QUERY_FACT_OWNER,
                interaction_relation=REASONING_CORE_TURN_PLANNER_SERVICE_QUERY_FACT_STAGE,
            )
        except (AttributeError, TypeError, ValueError):
            semantic_service_query_fact_decision = None
        semantic_service_query_pack_refs: set[str] = set()
        semantic_service_query_is_pricing = False
        if semantic_service_query_fact_decision is not None:
            semantic_service_query_pack_refs = _turn_planner_pack_ref_set(
                semantic_service_query_fact_decision
            )
            semantic_service_query_is_pricing = (
                semantic_service_query_fact_decision.intent == "info"
                and semantic_service_query_pack_refs == {"pricing"}
            )
        if (
            semantic_service_query_fact_decision is not None
            and _is_turn_planner_safe_service_query_fact_candidate(
                semantic_service_query_fact_decision
            )
        ):
            service_query = _resolve_turn_planner_tool_action_service_query(
                semantic_service_query_fact_decision
            )
            if service_query is not None:
                tool_args = (
                    dict(semantic_service_query_fact_decision.tool_args)
                    if isinstance(semantic_service_query_fact_decision.tool_args, dict)
                    else {}
                )
                tool_result = execute_tool_action(
                    db,
                    tool_action=semantic_service_query_fact_decision.tool_action,
                    tool_args=tool_args,
                    conversation_id=conversation.id,
                    branch_id=branch_id,
                    client_slug=payload.client_slug,
                    service_query=service_query,
                    info_sections_hint=semantic_service_query_fact_decision.pack_refs,
                    message_text=message_text,
                )
                reply_meta = (
                    dict(tool_result.decision_meta)
                    if isinstance(tool_result.decision_meta, dict)
                    else None
                )
                semantic_service_query_safe_owner_cutover = True
                if semantic_service_query_is_pricing:
                    raw_tool_reply_sections = (
                        reply_meta.get("info_sections")
                        if isinstance(reply_meta, dict)
                        else None
                    )
                    normalized_tool_reply_sections = [
                        section.strip().casefold()
                        for section in raw_tool_reply_sections
                        if isinstance(section, str) and section.strip()
                    ] if isinstance(raw_tool_reply_sections, list) else []
                    master_resolution = resolve_master_intent(
                        message_text=message_text,
                        client_slug=payload.client_slug,
                        service_query=service_query,
                        force_master_intent=False,
                    )
                    master_request_signal = bool(
                        "master" in normalized_tool_reply_sections
                        or master_resolution.explicit
                        or policy_intent in {"master", "master_query", "specialist", "specialist_query"}
                    )
                    has_explicit_location_or_hours = (
                        decision_router._has_explicit_location_or_hours_request(
                            message_text,
                            client_slug=payload.client_slug,
                            strict=decision_router._semantic_arbitration_enabled(),
                        )
                    )
                    semantic_service_query_safe_owner_cutover = not (
                        master_request_signal or has_explicit_location_or_hours
                    )
                if (
                    semantic_service_query_safe_owner_cutover
                    and _should_accept_turn_planner_service_query_result(
                    semantic_service_query_fact_decision,
                    response_text=tool_result.response_text,
                    handled=tool_result.handled,
                    ok=tool_result.ok,
                    decision_meta=reply_meta,
                )
                ):
                    if isinstance(reply_meta, dict):
                        reply_meta.setdefault("source", "tool_registry")
                        reply_meta.setdefault("action_source", "semantic_arbitration")
                        if policy_rescue_attempted:
                            reply_meta["llm_policy_core"] = {
                                "rescue_attempted": True,
                                "rescue_applied": policy_rescue_applied,
                                "rescue_trigger_error": policy_rescue_trigger_error,
                            }
                    trace_meta = (
                        dict(tool_result.trace) if isinstance(tool_result.trace, dict) else None
                    )
                    if isinstance(trace_meta, dict):
                        trace_meta.setdefault(
                            "source_route", "llm_policy_core_semantic_arbitration"
                        )
                    tool_decision = None
                    if isinstance(reply_meta, dict):
                        raw_tool_decision = reply_meta.get("tool_decision")
                        if isinstance(raw_tool_decision, str):
                            tool_decision = raw_tool_decision.strip() or None
                    return _finalize_turn_planner_owner_cutover(
                        payload=payload,
                        db=db,
                        client_id=client_id,
                        preflight_payload=preflight_payload,
                        conversation_id=conversation.id,
                        decision=semantic_service_query_fact_decision,
                        reply_text=tool_result.response_text.strip(),
                        reply_meta=reply_meta,
                        trace_meta=trace_meta,
                        owner_cutover=REASONING_CORE_TURN_PLANNER_SERVICE_QUERY_FACT_OWNER,
                        stage=REASONING_CORE_TURN_PLANNER_SERVICE_QUERY_FACT_STAGE,
                        success_label="Turn planner safe semantic service-query fact",
                        tool_decision=tool_decision,
                        outcome_source="tool_registry",
                    )
    active_session_memory = None
    if isinstance(context, dict):
        raw_session_memory = decision_router._get_session_memory(context)
        if (
            isinstance(raw_session_memory, dict)
            and not decision_router._is_session_memory_expired(raw_session_memory, now)
        ):
            active_session_memory = raw_session_memory
    semantic_services_overview_service_query = bool(
        conversation.state == ConversationState.BOT_ACTIVE.value
        and not booking_scope_active
        and reply_slot is None
        and active_session_memory is None
        and policy_action == "fact"
        and policy_tool_action == "catalog.service_query"
        and not policy_pack_refs
    )
    if semantic_services_overview_service_query and not (
        decision_router._policy_has_style_reference_hint(
            policy_intent=policy_intent,
            policy_reason=policy_reason,
        )
        or decision_router._is_style_reference_request(message_text, has_media=False)
    ):
        raw_services_overview_service_query = policy_tool_args.get("service_query")
        services_overview_service_query = (
            raw_services_overview_service_query.strip()
            if isinstance(raw_services_overview_service_query, str)
            and raw_services_overview_service_query.strip()
            else None
        )
        if services_overview_service_query is not None:
            tool_result = execute_tool_action(
                db,
                tool_action="catalog.service_query",
                tool_args={"service_query": services_overview_service_query},
                conversation_id=conversation.id,
                branch_id=branch_id,
                client_slug=payload.client_slug,
                service_query=services_overview_service_query,
                message_text=message_text,
            )
            reply_text = (
                tool_result.response_text.strip()
                if isinstance(tool_result.response_text, str) and tool_result.response_text.strip()
                else None
            )
            reply_meta = (
                dict(tool_result.decision_meta)
                if isinstance(tool_result.decision_meta, dict)
                else {}
            )
            raw_tool_decision = reply_meta.get("tool_decision")
            tool_decision_token = _normalize_token(raw_tool_decision)
            info_sections = reply_meta.get("info_sections")
            normalized_info_sections = [
                section.strip()
                for section in info_sections
                if isinstance(section, str) and section.strip()
            ] if isinstance(info_sections, list) else []
            normalized_info_section_tokens = {
                section.casefold() for section in normalized_info_sections
            }
            master_resolution = resolve_master_intent(
                message_text=message_text,
                client_slug=payload.client_slug,
                service_query=services_overview_service_query,
                force_master_intent=False,
            )
            master_request_signal = bool(
                "master" in normalized_info_section_tokens
                or master_resolution.explicit
                or policy_intent in {"master", "master_query", "specialist", "specialist_query"}
            )
            has_explicit_location_or_hours = (
                decision_router._has_explicit_location_or_hours_request(
                    message_text,
                    client_slug=payload.client_slug,
                    strict=decision_router._semantic_arbitration_enabled(),
                )
            )
            services_overview_contract = resolve_services_overview_contract_update(
                **{
                    "tool_action": "catalog.service_query",
                    "tool_decision": tool_decision_token,
                    f"current_{_ER_KEY}": reply_slot,
                    f"memory_{_ER_KEY}": None,
                }
            )
            if (
                tool_result.handled
                and tool_result.ok
                and reply_text is not None
                and tool_decision_token == "services_overview"
                and "services_overview" in normalized_info_section_tokens
                and services_overview_contract is not None
                and not master_request_signal
                and not has_explicit_location_or_hours
                and decision_router._fact_guard_reason(reply_meta) is None
            ):
                reply_meta.setdefault("source", "tool_registry")
                reply_meta.setdefault("action_source", "semantic_arbitration")
                reply_meta.setdefault("tool_action", "catalog.service_query")
                tool_reply_owner_cutover = "turn_executor.tool_reply_turn_outcome.v1"
                services_overview_expected_reply = getattr(
                    services_overview_contract, _ER_KEY, None
                )
                services_overview_reason = services_overview_contract.reason
                services_overview_expected_reply_kwargs = {
                    _ER_KEY: services_overview_expected_reply
                }
                tool_reply_decision = TurnPlanner().build_tool_reply_owner_decision(
                    payload=policy_payload,
                    default_intent=policy_intent or policy_tool_action,
                    reply_intent=policy_tool_action,
                    tool_action=policy_tool_action,
                    **services_overview_expected_reply_kwargs,
                )
                tool_reply_dialog_state = DialogStateService().build_tool_reply_owner_state(
                    decision=tool_reply_decision,
                    owner_cutover=tool_reply_owner_cutover,
                    **services_overview_expected_reply_kwargs,
                    **{_ERR_KEY: services_overview_reason},
                )
                tool_reply_payload = TurnExecutor().build_tool_reply_owner_cutover_payload(
                    decision=tool_reply_decision,
                    dialog_state=tool_reply_dialog_state,
                    text=reply_text,
                    owner_cutover=tool_reply_owner_cutover,
                    reply_source="tool_registry",
                    reply_intent=policy_tool_action,
                    intent=policy_intent or policy_tool_action,
                    tool_action=policy_tool_action,
                    raw_tool_decision=(
                        raw_tool_decision if isinstance(raw_tool_decision, str) else "services_overview"
                    ),
                    normalized_tool_decision=tool_decision_token,
                    followup_type=services_overview_expected_reply,
                    followup_reason=services_overview_reason,
                    followup_prompt=None,
                    services_overview_followup=True,
                    conversation_state=conversation.state,
                    info_sections=normalized_info_sections,
                    saved_message_present=True,
                )

                saved_message = save_message(
                    db,
                    conversation.id,
                    client.id,
                    role="user",
                    content=message_text or "",
                    message_metadata=_build_turn_planner_user_message_metadata(payload=payload),
                )
                context_manager_router._set_expected_reply_context(
                    conversation=conversation,
                    saved_message=saved_message,
                    context=context,
                    reason=services_overview_reason,
                    now=now,
                    **services_overview_expected_reply_kwargs,
                )

                metadata_message_id = getattr(metadata, "messageId", None)
                remote_jid_value = remote_jid.strip()
                branch_id_value = conversation.branch_id

                def _send_and_save(text: str) -> tuple[str, bool]:
                    save_message(
                        db,
                        conversation.id,
                        client.id,
                        role="assistant",
                        content=text,
                        message_metadata={
                            "source": "bot",
                            "owner_cutover": tool_reply_owner_cutover,
                        },
                    )
                    instance_id = get_instance_id(
                        db,
                        client.id,
                        branch_id=branch_id_value,
                        remote_jid=remote_jid_value,
                    )
                    send_result = send_message_safe(
                        instance_id or "",
                        remote_jid_value,
                        text,
                        metadata_message_id,
                        notify_on_failure=True,
                        record_metrics=True,
                    )
                    conversation.last_message_at = datetime.now(timezone.utc)
                    return text, bool(getattr(send_result, "is_ok", lambda: False)())

                trace_payload_override = dict(tool_reply_payload.trace_payload_override)
                trace_payload_override["source_route"] = "llm_policy_core_semantic_arbitration"

                return _finalize_turn_planner_owner_cutover(
                    payload=payload,
                    db=db,
                    client_id=client_id,
                    preflight_payload=preflight_payload,
                    conversation_id=conversation.id,
                    decision=tool_reply_decision,
                    reply_text=reply_text,
                    reply_meta=reply_meta,
                    trace_meta=None,
                    owner_cutover=tool_reply_owner_cutover,
                    stage="llm_policy_core_tool",
                    success_label="Turn planner safe semantic tool reply",
                    tool_decision=tool_decision_token,
                    followup_type=services_overview_expected_reply,
                    question_reason=services_overview_reason,
                    outcome_action="reply",
                    outcome_source="tool_registry",
                    artifact=tool_reply_payload.artifact,
                    existing_conversation=conversation,
                    existing_saved_message=saved_message,
                    send_and_save=_send_and_save,
                    trace_payload_override=trace_payload_override,
                    extra_trace_payloads=tool_reply_payload.extra_trace_payloads,
                    extra_meta_updates=tool_reply_payload.extra_meta_updates,
                )
    master_override_candidate = bool(
        policy_tool_action == "catalog.service_query"
        and policy_intent == "info"
        and not booking_scope_active
        and reply_slot is None
    )
    semantic_booking_intent = bool(
        policy_goal == "booking"
        or policy_tool_action in {"collect", "booking", "calendar.list_slots", "calendar.book_slot"}
        or (
            isinstance(policy_intent, str)
            and (
                "booking" in policy_intent
                or policy_intent in {"introduce", "provide_name", "reschedule", "cancel"}
            )
        )
    )
    if not (semantic_booking_intent or master_override_candidate) or not routing.get(
        "allow_booking_flow", False
    ):
        return None
    if (
        policy_pack_refs
        and policy_tool_action != "calendar.book_slot"
        and not master_override_candidate
    ):
        return None

    if (
        semantic_booking_intent
        and policy_tool_action != "calendar.book_slot"
        and policy_slot_state_validated
    ):
        recovery_state = dict(booking_state)
        if recovery_state.get("active") is not True:
            recovery_state["active"] = True
            recovery_state["started_at"] = now.isoformat()
        for slot_key, value in policy_slot_state_validated.items():
            if not recovery_state.get(slot_key):
                recovery_state[slot_key] = value
        if conversation_snapshot is not None:
            if not recovery_state.get("service"):
                snapshot_service = conversation_snapshot.service_referent
                if isinstance(snapshot_service, str) and snapshot_service.strip():
                    recovery_state["service"] = snapshot_service.strip()
            if not recovery_state.get("datetime"):
                snapshot_datetime = conversation_snapshot.booking_datetime_value
                if isinstance(snapshot_datetime, str) and snapshot_datetime.strip():
                    recovery_state["datetime"] = snapshot_datetime.strip()
            if conversation_snapshot.booking_active and recovery_state.get("active") is not True:
                recovery_state["active"] = True
        recovery_progression_meta: dict[str, object] = {}
        recovery_progression_traces: list[dict[str, object]] = []
        if reply_slot == decision_router.EXPECTED_REPLY_TIME:
            recovery_state, recovery_time_progression_meta = _apply_turn_planner_exact_time_progression_override(
                booking_state=recovery_state,
                message_text=message_text,
                client_slug=payload.client_slug,
            )
            if isinstance(recovery_time_progression_meta, dict):
                recovery_progression_meta.update(recovery_time_progression_meta)
                recovery_progression_traces.append(
                    _build_exact_time_progression_trace_payload(
                        source="llm_policy_core_semantic_arbitration",
                        state=conversation.state,
                        progression_meta=recovery_time_progression_meta,
                    )
                )
        elif reply_slot == decision_router.EXPECTED_REPLY_NAME:
            recovery_state = _restore_turn_planner_snapshot_datetime_if_message_echo(
                booking_state=recovery_state,
                booking_datetime_value=conversation_snapshot.booking_datetime_value,
                message_text=message_text,
            )
            recovery_state, recovery_time_progression_meta = _apply_turn_planner_exact_time_progression_override(
                booking_state=recovery_state,
                message_text=message_text,
                client_slug=payload.client_slug,
            )
            if isinstance(recovery_time_progression_meta, dict):
                recovery_progression_meta.update(recovery_time_progression_meta)
                recovery_progression_traces.append(
                    _build_exact_time_progression_trace_payload(
                        source="llm_policy_core_semantic_arbitration",
                        state=conversation.state,
                        progression_meta=recovery_time_progression_meta,
                    )
                )
            recovery_state, recovery_name_progression_meta = _apply_turn_planner_explicit_name_progression_override(
                booking_state=recovery_state,
                message_text=message_text,
                client_slug=payload.client_slug,
            )
            if isinstance(recovery_name_progression_meta, dict):
                recovery_progression_meta.update(recovery_name_progression_meta)
                recovery_progression_traces.append(
                    _build_name_progression_trace_payload(
                        source="llm_policy_core_semantic_arbitration",
                        state=conversation.state,
                        progression_meta=recovery_name_progression_meta,
                    )
                )
        if recovery_progression_meta:
            merged_policy_slots = decision_router._merge_booking_plan_slots(
                booking_state=recovery_state,
                plan_slots=policy_slot_state_validated,
            )
            semantic_completion_slots = dict(merged_policy_slots)
            semantic_progression_meta.update(recovery_progression_meta)
            semantic_progression_trace_payloads.extend(recovery_progression_traces)
        if not decision_router._plan_has_complete_booking_slots(
            semantic_completion_slots,
            client_slug=payload.client_slug,
        ):
            recovery_state, prompt = decision_router._next_booking_prompt(
                recovery_state,
                refusal_flags=None,
                client_slug=payload.client_slug,
            )
            booking_last_question = recovery_state.get("last_question")
            if isinstance(booking_last_question, str) and booking_last_question.strip():
                booking_last_question = booking_last_question.strip()
                followup_type = decision_router._expected_reply_for_booking_question(
                    booking_last_question
                )
                if followup_type in {
                    decision_router.EXPECTED_REPLY_SERVICE,
                    decision_router.EXPECTED_REPLY_TIME,
                    decision_router.EXPECTED_REPLY_NAME,
                }:
                    reply_text = prompt or _resolve_turn_planner_booking_prompt_text(followup_type)
                    if isinstance(reply_text, str) and reply_text.strip():
                        decision = _build_turn_planner_safe_booking_prompt_decision(
                            last_question=booking_last_question,
                            slot_values=_build_turn_planner_booking_prompt_slot_values(recovery_state),
                            reason=policy_reason,
                        )
                        if decision is not None:
                            grounded_referents = None
                            service_value = recovery_state.get("service")
                            if isinstance(service_value, str) and service_value.strip():
                                grounded_referents = {"service": service_value.strip()}
                            return _finalize_turn_planner_owner_cutover(
                                payload=payload,
                                db=db,
                                client_id=client_id,
                                preflight_payload=preflight_payload,
                                conversation_id=conversation.id,
                                decision=decision,
                                reply_text=reply_text.strip(),
                                reply_meta={
                                    "action": "booking_prompt",
                                    "intent": "booking",
                                    "tool_action": "collect",
                                    "source": "llm_policy_core",
                                    "action_source": "semantic_arbitration",
                                    "llm_policy_core_collect_slot": booking_last_question,
                                    **recovery_progression_meta,
                                },
                                trace_meta={
                                    "source_route": "llm_policy_core_semantic_arbitration",
                                    "requested_slot": booking_last_question,
                                    "missing_slot": booking_last_question,
                                    **recovery_progression_meta,
                                },
                                owner_cutover=REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_OWNER,
                                stage=REASONING_CORE_TURN_PLANNER_BOOKING_PROMPT_STAGE,
                                success_label="Turn planner safe semantic booking prompt",
                                followup_type=followup_type,
                                question_reason="booking_prompt",
                                booking_slot_values=_build_turn_planner_booking_prompt_slot_values(
                                    recovery_state
                                ),
                                booking_last_question=booking_last_question,
                                booking_payload_override=(
                                    recovery_state
                                    if recovery_progression_meta
                                    else None
                                ),
                                grounded_referents=grounded_referents,
                                outcome_action="booking_prompt",
                                outcome_source="llm_policy_core",
                                trace_decision="prompt",
                                extra_trace_payloads=recovery_progression_traces or None,
                            )

    if (
        policy_tool_action == "calendar.list_slots"
        and decision_router._is_time_pending_question_guidance_act(
            policy_pending_question_act,
            policy_pending_question_target,
        )
        and reply_slot == decision_router.EXPECTED_REPLY_TIME
    ):
        tool_args = dict(policy_tool_args)
        service_query = tool_args.get("service_query")
        if isinstance(service_query, str):
            service_query = service_query.strip() or None
        else:
            service_query = None
        if service_query is None:
            merged_service = merged_policy_slots.get("service")
            if isinstance(merged_service, str) and merged_service.strip():
                service_query = merged_service.strip()
                tool_args["service_query"] = service_query
        if service_query is not None:
            tool_result = execute_tool_action(
                db,
                tool_action="calendar.list_slots",
                tool_args=tool_args,
                conversation_id=conversation.id,
                branch_id=branch_id,
                client_slug=payload.client_slug,
                service_query=service_query,
                message_text=message_text,
            )
            reply_text = (
                tool_result.response_text.strip()
                if isinstance(tool_result.response_text, str) and tool_result.response_text.strip()
                else None
            )
            reply_meta = (
                dict(tool_result.decision_meta)
                if isinstance(tool_result.decision_meta, dict)
                else {}
            )
            raw_tool_decision = reply_meta.get("tool_decision")
            if not isinstance(raw_tool_decision, str) or not raw_tool_decision.strip():
                raw_tool_decision = tool_result.error_code
            tool_decision_token = _normalize_token(raw_tool_decision)
            if (
                tool_result.handled
                and reply_text is not None
                and tool_decision_token == "missing_slot"
            ):
                reply_meta.setdefault("source", "tool_registry")
                reply_meta.setdefault("action_source", "semantic_arbitration")
                reply_meta["tool_action"] = "calendar.list_slots"

                turn_outcome_expected_reason = reply_reason or "booking_slot_guidance"
                tool_reply_owner_cutover = "turn_executor.tool_reply_turn_outcome.v1"
                expected_reply_kwargs = {_ER_KEY: reply_slot}
                tool_reply_decision = TurnPlanner().build_tool_reply_owner_decision(
                    payload=policy_payload,
                    default_intent=policy_intent or policy_tool_action,
                    reply_intent=policy_tool_action,
                    tool_action=policy_tool_action,
                    pending_question_tool_followup=True,
                    pending_question_act=policy_pending_question_act,
                    **expected_reply_kwargs,
                )
                tool_reply_dialog_state = DialogStateService().build_tool_reply_owner_state(
                    decision=tool_reply_decision,
                    owner_cutover=tool_reply_owner_cutover,
                    **expected_reply_kwargs,
                    **{_ERR_KEY: turn_outcome_expected_reason},
                )
                tool_reply_payload = TurnExecutor().build_tool_reply_owner_cutover_payload(
                    decision=tool_reply_decision,
                    dialog_state=tool_reply_dialog_state,
                    text=reply_text,
                    owner_cutover=tool_reply_owner_cutover,
                    reply_source="tool_registry",
                    reply_intent=policy_tool_action,
                    intent=policy_intent or policy_tool_action,
                    tool_action=policy_tool_action,
                    raw_tool_decision=raw_tool_decision if isinstance(raw_tool_decision, str) else None,
                    normalized_tool_decision=tool_decision_token,
                    followup_type=reply_slot,
                    followup_reason=turn_outcome_expected_reason,
                    followup_prompt=None,
                    services_overview_followup=False,
                    conversation_state=conversation.state,
                    pending_question_tool_followup=True,
                    pending_question_act=policy_pending_question_act,
                    pending_question_target=policy_pending_question_target,
                    saved_message_present=True,
                )

                saved_message = save_message(
                    db,
                    conversation.id,
                    client.id,
                    role="user",
                    content=message_text or "",
                    message_metadata=_build_turn_planner_user_message_metadata(payload=payload),
                )
                context_manager_router._set_expected_reply_context(
                    conversation=conversation,
                    saved_message=saved_message,
                    context=context,
                    reason=turn_outcome_expected_reason,
                    now=now,
                    **expected_reply_kwargs,
                )

                metadata_message_id = getattr(metadata, "messageId", None)
                remote_jid_value = remote_jid.strip()
                branch_id_value = conversation.branch_id

                def _send_and_save(text: str) -> tuple[str, bool]:
                    save_message(
                        db,
                        conversation.id,
                        client.id,
                        role="assistant",
                        content=text,
                        message_metadata={
                            "source": "bot",
                            "owner_cutover": tool_reply_owner_cutover,
                        },
                    )
                    instance_id = get_instance_id(
                        db,
                        client.id,
                        branch_id=branch_id_value,
                        remote_jid=remote_jid_value,
                    )
                    send_result = send_message_safe(
                        instance_id or "",
                        remote_jid_value,
                        text,
                        metadata_message_id,
                        notify_on_failure=True,
                        record_metrics=True,
                    )
                    conversation.last_message_at = datetime.now(timezone.utc)
                    return text, bool(getattr(send_result, "is_ok", lambda: False)())

                return _finalize_turn_planner_owner_cutover(
                    payload=payload,
                    db=db,
                    client_id=client_id,
                    preflight_payload=preflight_payload,
                    conversation_id=conversation.id,
                    decision=tool_reply_decision,
                    reply_text=reply_text,
                    reply_meta=reply_meta,
                    trace_meta=(
                        dict(tool_result.trace)
                        if isinstance(tool_result.trace, dict)
                        else None
                    ),
                    owner_cutover=tool_reply_owner_cutover,
                    stage="llm_policy_core_tool",
                    success_label="Turn planner safe semantic tool reply",
                    tool_decision=tool_decision_token,
                    followup_type=reply_slot,
                    question_reason=turn_outcome_expected_reason,
                    outcome_action="reply",
                    outcome_source="tool_registry",
                    artifact=tool_reply_payload.artifact,
                    existing_conversation=conversation,
                    existing_saved_message=saved_message,
                    send_and_save=_send_and_save,
                    trace_payload_override=tool_reply_payload.trace_payload_override,
                    extra_trace_payloads=tool_reply_payload.extra_trace_payloads,
                    extra_meta_updates=tool_reply_payload.extra_meta_updates,
                )

    policy_collect_slot = policy_next_question or next(
        (
            question
            for question in policy_open_questions
            if question in {"service", "datetime", "name"}
        ),
        None,
    )
    interrupt_service_query = None
    if (
        policy_tool_action == "collect"
        and policy_intent == "info"
        and policy_subject_kind == "service"
        and policy_resolution_mode == "clarify_missing_subject"
        and reply_slot == decision_router.EXPECTED_REPLY_TIME
        and booking_scope_active
        and policy_collect_slot in {None, "service"}
    ):
        raw_interrupt_service_query = policy_tool_args.get("service_query")
        if isinstance(raw_interrupt_service_query, str) and raw_interrupt_service_query.strip():
            interrupt_service_query = raw_interrupt_service_query.strip()
        else:
            merged_service = merged_policy_slots.get("service")
            if isinstance(merged_service, str) and merged_service.strip():
                interrupt_service_query = merged_service.strip()
            else:
                booking_service = booking_state.get("service")
                if isinstance(booking_service, str) and booking_service.strip():
                    interrupt_service_query = booking_service.strip()
    if interrupt_service_query is not None:
        interrupt_tool_args = {"service_query": interrupt_service_query}
        tool_result = execute_tool_action(
            db,
            tool_action="catalog.service_query",
            tool_args=interrupt_tool_args,
            conversation_id=conversation.id,
            branch_id=branch_id,
            client_slug=payload.client_slug,
            service_query=interrupt_service_query,
            message_text=message_text,
        )
        reply_text = (
            tool_result.response_text.strip()
            if isinstance(tool_result.response_text, str) and tool_result.response_text.strip()
            else None
        )
        reply_meta = (
            dict(tool_result.decision_meta)
            if isinstance(tool_result.decision_meta, dict)
            else {}
        )
        raw_tool_decision = reply_meta.get("tool_decision")
        tool_decision_token = _normalize_token(raw_tool_decision)
        info_sections = reply_meta.get("info_sections")
        if not isinstance(info_sections, list):
            info_sections = []
        normalized_info_sections = [
            section.strip()
            for section in info_sections
            if isinstance(section, str) and section.strip()
        ]
        if (
            tool_result.handled
            and reply_text is not None
            and tool_decision_token == "services_overview"
            and normalized_info_sections
        ):
            reply_meta.setdefault("source", "tool_registry")
            reply_meta["tool_action"] = "catalog.service_query"
            interrupt_expected_reason = "booking_interrupt"
            interrupt_owner_cutover = "turn_executor.tool_reply_turn_outcome.v1"
            expected_reply_kwargs = {_ER_KEY: reply_slot}
            interrupt_payload = dict(policy_payload)
            interrupt_payload["intent"] = "catalog.service_query"
            interrupt_payload["action"] = "fact"
            interrupt_payload["tool_action"] = "catalog.service_query"
            interrupt_payload["tool_args"] = interrupt_tool_args
            tool_reply_decision = TurnPlanner().build_tool_reply_owner_decision(
                payload=interrupt_payload,
                default_intent="catalog.service_query",
                reply_intent="catalog.service_query",
                tool_action="catalog.service_query",
                collect_service_info_interrupt_active=True,
                **expected_reply_kwargs,
            )
            tool_reply_dialog_state = DialogStateService().build_tool_reply_owner_state(
                decision=tool_reply_decision,
                owner_cutover=interrupt_owner_cutover,
                **expected_reply_kwargs,
                **{_ERR_KEY: interrupt_expected_reason},
            )
            tool_reply_payload = TurnExecutor().build_tool_reply_owner_cutover_payload(
                decision=tool_reply_decision,
                dialog_state=tool_reply_dialog_state,
                text=reply_text,
                owner_cutover=interrupt_owner_cutover,
                reply_source="tool_registry",
                reply_intent="catalog.service_query",
                intent="catalog.service_query",
                tool_action="catalog.service_query",
                raw_tool_decision=(
                    raw_tool_decision if isinstance(raw_tool_decision, str) else "services_overview"
                ),
                normalized_tool_decision=tool_decision_token,
                followup_type=reply_slot,
                followup_reason=interrupt_expected_reason,
                followup_prompt=None,
                services_overview_followup=False,
                conversation_state=conversation.state,
                collect_service_info_interrupt_active=True,
                info_sections=normalized_info_sections,
                saved_message_present=True,
            )

            saved_message = save_message(
                db,
                conversation.id,
                client.id,
                role="user",
                content=message_text or "",
                message_metadata=_build_turn_planner_user_message_metadata(payload=payload),
            )
            context_manager_router._set_expected_reply_context(
                conversation=conversation,
                saved_message=saved_message,
                context=context,
                reason=interrupt_expected_reason,
                now=now,
                **expected_reply_kwargs,
            )

            metadata_message_id = getattr(metadata, "messageId", None)
            remote_jid_value = remote_jid.strip()
            branch_id_value = conversation.branch_id

            def _send_and_save(text: str) -> tuple[str, bool]:
                save_message(
                    db,
                    conversation.id,
                    client.id,
                    role="assistant",
                    content=text,
                    message_metadata={
                        "source": "bot",
                        "owner_cutover": interrupt_owner_cutover,
                    },
                )
                instance_id = get_instance_id(
                    db,
                    client.id,
                    branch_id=branch_id_value,
                    remote_jid=remote_jid_value,
                )
                send_result = send_message_safe(
                    instance_id or "",
                    remote_jid_value,
                    text,
                    metadata_message_id,
                    notify_on_failure=True,
                    record_metrics=True,
                )
                conversation.last_message_at = datetime.now(timezone.utc)
                return text, bool(getattr(send_result, "is_ok", lambda: False)())

            extra_trace_payloads = [
                {
                    "stage": "llm_policy_plan_delta",
                    "decision": "override_event",
                    "from_action": "collect",
                    "from_tool_action": "collect",
                    "to_action": "fact",
                    "to_tool_action": "catalog.service_query",
                    "source": "booking_interrupt",
                },
                {
                    "stage": "policy_interrupt_contract",
                    "decision": "collect_service_info_interrupt",
                    "state": conversation.state,
                    "service_query": interrupt_service_query,
                    _ER_KEY: reply_slot,
                },
                *tool_reply_payload.extra_trace_payloads,
            ]
            extra_meta_updates = [
                *tool_reply_payload.extra_meta_updates,
                {
                    "policy_collect_guard_recovery": "active_time_service_info_interrupt",
                    "service_query": interrupt_service_query,
                    "policy_semantic_override_block_reason": (
                        "policy_collect_service_info_interrupt_owner"
                    ),
                },
            ]

            return _finalize_turn_planner_owner_cutover(
                payload=payload,
                db=db,
                client_id=client_id,
                preflight_payload=preflight_payload,
                conversation_id=conversation.id,
                decision=tool_reply_decision,
                reply_text=reply_text,
                reply_meta=reply_meta,
                trace_meta=(
                    dict(tool_result.trace)
                    if isinstance(tool_result.trace, dict)
                    else None
                ),
                owner_cutover=interrupt_owner_cutover,
                stage="llm_policy_core_tool",
                success_label="Turn planner safe semantic tool reply",
                tool_decision=tool_decision_token,
                followup_type=reply_slot,
                question_reason=interrupt_expected_reason,
                outcome_action="reply",
                outcome_source="tool_registry",
                artifact=tool_reply_payload.artifact,
                existing_conversation=conversation,
                existing_saved_message=saved_message,
                send_and_save=_send_and_save,
                trace_payload_override=tool_reply_payload.trace_payload_override,
                extra_trace_payloads=extra_trace_payloads,
                extra_meta_updates=extra_meta_updates,
            )

    master_override_service_query = None
    master_override_service_query_source = "policy_tool_args"
    if (
        policy_tool_action == "catalog.service_query"
        and policy_intent == "info"
        and not booking_scope_active
        and reply_slot is None
    ):
        raw_master_override_service_query = policy_tool_args.get("service_query")
        if (
            isinstance(raw_master_override_service_query, str)
            and raw_master_override_service_query.strip()
        ):
            master_override_service_query = raw_master_override_service_query.strip()
        else:
            merged_service = merged_policy_slots.get("service")
            if isinstance(merged_service, str) and merged_service.strip():
                master_override_service_query = merged_service.strip()
                master_override_service_query_source = "booking_slots"
    if master_override_service_query is not None:
        master_override_tool_args = {"service_query": master_override_service_query}
        tool_result = execute_tool_action(
            db,
            tool_action="catalog.service_query",
            tool_args=master_override_tool_args,
            conversation_id=conversation.id,
            branch_id=branch_id,
            client_slug=payload.client_slug,
            service_query=master_override_service_query,
            message_text=message_text,
        )
        reply_text = (
            tool_result.response_text.strip()
            if isinstance(tool_result.response_text, str) and tool_result.response_text.strip()
            else None
        )
        tool_reply_meta = (
            dict(tool_result.decision_meta)
            if isinstance(tool_result.decision_meta, dict)
            else {}
        )
        raw_tool_decision = tool_reply_meta.get("tool_decision")
        tool_reply_sections = tool_reply_meta.get("info_sections")
        normalized_tool_reply_sections = [
            section.strip().casefold()
            for section in tool_reply_sections
            if isinstance(section, str) and section.strip()
        ] if isinstance(tool_reply_sections, list) else []
        master_resolution = resolve_master_intent(
            message_text=message_text,
            client_slug=payload.client_slug,
            service_query=master_override_service_query,
            force_master_intent=False,
        )
        master_request_signal = bool(
            "master" in normalized_tool_reply_sections
            or master_resolution.explicit
            or policy_intent in {"master", "master_query", "specialist", "specialist_query"}
        )
        has_explicit_location_or_hours = decision_router._has_explicit_location_or_hours_request(
            message_text,
            client_slug=payload.client_slug,
            strict=decision_router._semantic_arbitration_enabled(),
        )
        if (
            tool_result.handled
            and reply_text is not None
            and master_request_signal
            and not has_explicit_location_or_hours
        ):
            master_override_reply, master_reply_meta = info_router._build_info_intent_reply(
                "master",
                service_query=master_override_service_query,
                client_slug=payload.client_slug,
                message_text=message_text,
            )
            if isinstance(master_override_reply, str) and master_override_reply.strip():
                reply_meta = dict(master_reply_meta) if isinstance(master_reply_meta, dict) else {}
                reply_meta.setdefault("tool_action", "catalog.service_query")
                override_info_sections = reply_meta.get("info_sections")
                normalized_override_info_sections = [
                    section.strip()
                    for section in override_info_sections
                    if isinstance(section, str) and section.strip()
                ] if isinstance(override_info_sections, list) else []
                tool_reply_owner_cutover = "turn_executor.tool_reply_turn_outcome.v1"
                master_override_reason = "master_signal_override_blocked"
                master_override_meta = {
                    "policy_semantic_override_blocked": True,
                    "policy_semantic_override_block_reason": master_override_reason,
                    "policy_semantic_override_block_from_action": policy_action,
                    "policy_semantic_override_block_from_tool_action": policy_tool_action,
                    "policy_semantic_override_block_to_action": "fact",
                    "policy_semantic_override_block_to_tool_action": "catalog.service_query",
                    "policy_semantic_override_block_from_intent": policy_intent,
                    "policy_semantic_override_block_to_intent": "master",
                    "policy_semantic_override_block_source": "catalog.service_query",
                    "policy_semantic_override_enforced": True,
                    "policy_semantic_override_enforced_reason": master_override_reason,
                }
                if normalized_override_info_sections:
                    master_override_meta["policy_semantic_override_block_info_sections"] = (
                        normalized_override_info_sections
                    )
                expected_reply_kwargs = {_ER_KEY: reply_slot}
                tool_reply_decision = TurnPlanner().build_tool_reply_owner_decision(
                    payload=policy_payload,
                    default_intent="master",
                    reply_intent="master",
                    tool_action="catalog.service_query",
                    master_override_applied=True,
                    **expected_reply_kwargs,
                )
                tool_reply_dialog_state = DialogStateService().build_tool_reply_owner_state(
                    decision=tool_reply_decision,
                    owner_cutover=tool_reply_owner_cutover,
                    **expected_reply_kwargs,
                )
                tool_reply_payload = TurnExecutor().build_tool_reply_owner_cutover_payload(
                    decision=tool_reply_decision,
                    dialog_state=tool_reply_dialog_state,
                    text=master_override_reply.strip(),
                    owner_cutover=tool_reply_owner_cutover,
                    reply_source="policy_core_guard",
                    reply_intent="master",
                    intent="master",
                    tool_action="catalog.service_query",
                    raw_tool_decision=master_override_reason,
                    normalized_tool_decision=master_override_reason,
                    followup_type=reply_slot,
                    followup_reason=None,
                    followup_prompt=None,
                    services_overview_followup=False,
                    conversation_state=conversation.state,
                    saved_message_present=True,
                    master_override_meta=master_override_meta,
                )

                saved_message = save_message(
                    db,
                    conversation.id,
                    client.id,
                    role="user",
                    content=message_text or "",
                    message_metadata=_build_turn_planner_user_message_metadata(payload=payload),
                )

                metadata_message_id = getattr(metadata, "messageId", None)
                remote_jid_value = remote_jid.strip()
                branch_id_value = conversation.branch_id

                def _send_and_save(text: str) -> tuple[str, bool]:
                    save_message(
                        db,
                        conversation.id,
                        client.id,
                        role="assistant",
                        content=text,
                        message_metadata={
                            "source": "bot",
                            "owner_cutover": tool_reply_owner_cutover,
                        },
                    )
                    instance_id = get_instance_id(
                        db,
                        client.id,
                        branch_id=branch_id_value,
                        remote_jid=remote_jid_value,
                    )
                    send_result = send_message_safe(
                        instance_id or "",
                        remote_jid_value,
                        text,
                        metadata_message_id,
                        notify_on_failure=True,
                        record_metrics=True,
                    )
                    conversation.last_message_at = datetime.now(timezone.utc)
                    return text, bool(getattr(send_result, "is_ok", lambda: False)())

                extra_trace_payloads = [
                    {
                        "stage": "llm_policy_semantic_delta",
                        "decision": "semantic_override_blocked",
                        "reason": master_override_reason,
                        "from_action": policy_action,
                        "from_tool_action": policy_tool_action,
                        "to_action": "fact",
                        "to_tool_action": "catalog.service_query",
                        "from_intent": policy_intent,
                        "to_intent": "master",
                        "source": "catalog.service_query",
                    },
                    {
                        "stage": "policy_guard",
                        "decision": "master_pack_enforced",
                        "state": conversation.state,
                        "reason_code": master_override_reason,
                        "source_tool_action": "catalog.service_query",
                        "service_query": master_override_service_query,
                        "service_query_source": master_override_service_query_source,
                    },
                    *tool_reply_payload.extra_trace_payloads,
                ]
                if normalized_override_info_sections:
                    extra_trace_payloads[0]["info_sections"] = normalized_override_info_sections

                return _finalize_turn_planner_owner_cutover(
                    payload=payload,
                    db=db,
                    client_id=client_id,
                    preflight_payload=preflight_payload,
                    conversation_id=conversation.id,
                    decision=tool_reply_decision,
                    reply_text=master_override_reply.strip(),
                    reply_meta=reply_meta,
                    trace_meta=(
                        dict(tool_result.trace)
                        if isinstance(tool_result.trace, dict)
                        else None
                    ),
                    owner_cutover=tool_reply_owner_cutover,
                    stage="llm_policy_core_tool",
                    success_label="Turn planner safe semantic tool reply",
                    tool_decision=master_override_reason,
                    outcome_action="reply",
                    outcome_source="policy_core_guard",
                    artifact=tool_reply_payload.artifact,
                    existing_conversation=conversation,
                    existing_saved_message=saved_message,
                    send_and_save=_send_and_save,
                    trace_payload_override=tool_reply_payload.trace_payload_override,
                    extra_trace_payloads=extra_trace_payloads,
                    extra_meta_updates=tool_reply_payload.extra_meta_updates,
                )

    booking_last_question = None
    booking_name_value = None
    if isinstance(booking_state, dict):
        raw_last_question = booking_state.get("last_question")
        if isinstance(raw_last_question, str) and raw_last_question.strip():
            booking_last_question = raw_last_question.strip().casefold()
        raw_booking_name = booking_state.get("name")
        if isinstance(raw_booking_name, str) and raw_booking_name.strip():
            booking_name_value = raw_booking_name.strip()
    plan_name_value = (
        policy_slot_state_validated.get("name")
        if isinstance(policy_slot_state_validated.get("name"), str)
        else None
    )
    if isinstance(plan_name_value, str):
        plan_name_value = plan_name_value.strip() or None
    name_changed_from_context = bool(
        plan_name_value
        and (
            not booking_name_value
            or decision_router._normalize_text(plan_name_value)
            != decision_router._normalize_text(booking_name_value)
        )
    )
    name_turn_signal = bool(
        name_changed_from_context
        or decision_router._detect_explicit_name_provided(
            message_text,
            client_slug=payload.client_slug,
        )
    )
    ready_for_name_commit = bool(
        policy_tool_action == "calendar.list_slots"
        and (reply_slot == decision_router.EXPECTED_REPLY_NAME or booking_last_question == "name")
        and name_turn_signal
    )
    should_complete_booking = bool(
        policy_tool_action == "calendar.book_slot"
        or ready_for_name_commit
        or policy_tool_action in {"collect", "booking"}
        or policy_intent in {"introduce", "provide_name"}
    )
    if not should_complete_booking:
        return None

    tool_args = dict(policy_tool_args)
    decision_router._normalize_specialist_tool_args(tool_args)
    hint_meta: dict[str, object] = dict(semantic_progression_meta)
    extra_trace_payloads: list[dict[str, object]] = list(semantic_progression_trace_payloads)
    service_query = tool_args.get("service_query")
    if isinstance(service_query, str):
        service_query = service_query.strip() or None
    else:
        service_query = None
    if service_query is None:
        merged_service = merged_policy_slots.get("service")
        if isinstance(merged_service, str) and merged_service.strip():
            service_query = merged_service.strip()
            tool_args["service_query"] = service_query
    if service_query is None:
        service_hint = extract_service_query_hint_llm(
            message_text,
            client_slug=payload.client_slug,
            timing_context=None,
        )
        if isinstance(service_hint, dict):
            hinted_service_query = service_hint.get("service_query")
            if isinstance(hinted_service_query, str) and hinted_service_query.strip():
                service_query = hinted_service_query.strip()
                tool_args["service_query"] = service_query
            hint_meta.update(
                {
                    "service_query_hint_attempted": bool(service_hint.get("attempted")),
                    "service_query_hint_ok": bool(service_hint.get("ok")),
                    "service_query_hint_confidence": service_hint.get("confidence"),
                    "service_query_hint_error": service_hint.get("error"),
                    "service_query_hint_language": service_hint.get("language"),
                }
            )
            extra_trace_payloads.append(
                {
                    "stage": "service_query_hint",
                    "decision": "ok" if service_query else "empty",
                    "tool_action": "calendar.book_slot",
                    "attempted": bool(service_hint.get("attempted")),
                    "confidence": service_hint.get("confidence"),
                    "error": service_hint.get("error"),
                    "language": service_hint.get("language"),
                }
            )
    if isinstance(service_query, str) and service_query.strip():
        semantic_completion_slots["service"] = service_query.strip()
    if not (
        isinstance(tool_args.get("start_at"), str)
        and tool_args.get("start_at").strip()
    ):
        merged_datetime = merged_policy_slots.get("datetime")
        if isinstance(merged_datetime, str) and merged_datetime.strip():
            tool_args["start_at"] = merged_datetime.strip()
    rebased_start_at = decision_router._normalize_booking_start_at_tool_arg(
        tool_args,
        fallback_datetime=merged_policy_slots.get("datetime"),
        now=now,
    )
    if rebased_start_at:
        hint_meta["booking_start_at_rebased"] = True
        extra_trace_payloads.append(
            {
                "stage": "booking_start_at_rebase",
                "decision": "applied",
                "tool_action": "calendar.book_slot",
            }
        )
    raw_start_at = tool_args.get("start_at")
    if isinstance(raw_start_at, str) and raw_start_at.strip():
        semantic_completion_slots["datetime"] = raw_start_at.strip()

    specialist_name = None
    specialist_id = None
    raw_specialist_name = tool_args.get("specialist_name")
    if isinstance(raw_specialist_name, str) and raw_specialist_name.strip():
        specialist_name = raw_specialist_name.strip()
    raw_specialist_id = tool_args.get("specialist_id")
    if isinstance(raw_specialist_id, str) and raw_specialist_id.strip():
        specialist_id = raw_specialist_id.strip()
    if specialist_name is None and specialist_id is None:
        specialist_hint = extract_specialist_hint_llm(
            message_text,
            client_slug=payload.client_slug,
            timing_context=None,
        )
        if isinstance(specialist_hint, dict):
            hinted_specialist_name = specialist_hint.get("specialist_name")
            if isinstance(hinted_specialist_name, str) and hinted_specialist_name.strip():
                specialist_name = hinted_specialist_name.strip()
                tool_args["specialist_name"] = specialist_name
            hint_meta.update(
                {
                    "specialist_hint_attempted": bool(specialist_hint.get("attempted")),
                    "specialist_hint_ok": bool(specialist_hint.get("ok")),
                    "specialist_hint_confidence": specialist_hint.get("confidence"),
                    "specialist_hint_error": specialist_hint.get("error"),
                    "specialist_hint_language": specialist_hint.get("language"),
                }
            )
            extra_trace_payloads.append(
                {
                    "stage": "specialist_hint",
                    "decision": "ok" if specialist_name else "empty",
                    "tool_action": "calendar.book_slot",
                    "attempted": bool(specialist_hint.get("attempted")),
                    "confidence": specialist_hint.get("confidence"),
                    "error": specialist_hint.get("error"),
                    "language": specialist_hint.get("language"),
                }
            )

    existing_customer_name = None
    raw_customer_name = tool_args.get("customer_name")
    if isinstance(raw_customer_name, str) and raw_customer_name.strip():
        existing_customer_name = raw_customer_name.strip()
    specialist_name_for_customer_hint = specialist_name
    if existing_customer_name is None and isinstance(merged_policy_slots.get("name"), str):
        merged_name = merged_policy_slots.get("name").strip()
        if merged_name:
            tool_args["customer_name"] = merged_name
            existing_customer_name = merged_name
    customer_hint_needed = not (
        isinstance(existing_customer_name, str) and existing_customer_name.strip()
    )
    if (
        not customer_hint_needed
        and isinstance(existing_customer_name, str)
        and isinstance(specialist_name_for_customer_hint, str)
        and specialist_name_for_customer_hint.strip()
    ):
        customer_hint_needed = (
            decision_router.normalize_for_matching(existing_customer_name)
            == decision_router.normalize_for_matching(specialist_name_for_customer_hint)
        )
    if customer_hint_needed:
        customer_hint = extract_customer_name_hint_llm(
            message_text,
            client_slug=payload.client_slug,
            timing_context=None,
            specialist_name=specialist_name_for_customer_hint,
        )
        if isinstance(customer_hint, dict):
            hinted_customer_name = customer_hint.get("customer_name")
            if isinstance(hinted_customer_name, str) and hinted_customer_name.strip():
                tool_args["customer_name"] = hinted_customer_name.strip()
                existing_customer_name = hinted_customer_name.strip()
            hint_meta.update(
                {
                    "customer_name_hint_attempted": bool(customer_hint.get("attempted")),
                    "customer_name_hint_ok": bool(customer_hint.get("ok")),
                    "customer_name_hint_confidence": customer_hint.get("confidence"),
                    "customer_name_hint_error": customer_hint.get("error"),
                    "customer_name_hint_language": customer_hint.get("language"),
                }
            )
            extra_trace_payloads.append(
                {
                    "stage": "customer_name_hint",
                    "decision": "ok" if existing_customer_name else "empty",
                    "tool_action": "calendar.book_slot",
                    "attempted": bool(customer_hint.get("attempted")),
                    "confidence": customer_hint.get("confidence"),
                    "error": customer_hint.get("error"),
                    "language": customer_hint.get("language"),
                }
            )
    if isinstance(existing_customer_name, str) and existing_customer_name.strip():
        semantic_completion_slots["name"] = existing_customer_name.strip()

    if service_query is None:
        return None
    if not (
        isinstance(tool_args.get("start_at"), str)
        and tool_args.get("start_at").strip()
    ):
        return None
    if not decision_router._plan_has_complete_booking_slots(
        semantic_completion_slots,
        client_slug=payload.client_slug,
    ):
        return None

    decision = _build_turn_planner_safe_booking_completion_decision(
        tool_action="calendar.book_slot",
        tool_args=tool_args,
        slot_values=semantic_completion_slots,
        reason=policy_reason,
    )
    if decision is None:
        return None

    tool_execute_kwargs = {
        "tool_action": "calendar.book_slot",
        "tool_args": tool_args,
        "conversation_id": conversation.id,
        "branch_id": branch_id,
        "client_slug": payload.client_slug,
        "service_query": service_query,
        "message_text": message_text,
        _ER_KEY: reply_slot,
        "now": now,
        "user_remote_jid": remote_jid.strip(),
    }
    tool_result = execute_tool_action(db, **tool_execute_kwargs)
    if not tool_result.handled:
        return None

    reply_meta = (
        dict(tool_result.decision_meta)
        if isinstance(tool_result.decision_meta, dict)
        else {}
    )
    reply_meta.update(hint_meta)
    reply_meta.setdefault("source", "tool_registry")
    reply_meta.setdefault("action_source", "semantic_arbitration")

    tool_decision = reply_meta.get("tool_decision")
    appointment_id = reply_meta.get("appointment_id")
    transition_owner_result = apply_tool_transition_owner(
        existing_booking_state=booking_state,
        policy_slot_state=semantic_completion_slots,
        tool_args=tool_args,
        tool_action="calendar.book_slot",
        tool_decision=tool_decision if isinstance(tool_decision, str) else None,
        policy_intent="booking",
        policy_goal="booking",
        booking_wants_flow=bool(booking_state.get("active") is True or normalized_goal == "booking"),
        appointment_id=appointment_id if isinstance(appointment_id, str) else None,
        now=now,
        slot_order=decision_router.BOOKING_SLOT_ORDER,
    )
    expected_contract_kwargs = {
        "tool_action": "calendar.book_slot",
        "tool_decision": tool_decision if isinstance(tool_decision, str) else None,
        f"current_{_ER_KEY}": reply_slot,
        f"memory_{_ER_KEY}": reply_slot,
        "booking_has_service": transition_owner_result.booking_has_service,
        "booking_has_datetime": decision_router._booking_slot_is_complete(
            slot_key="datetime",
            value=transition_owner_result.merged_slots.get("datetime")
            or transition_owner_result.booking_state.get("datetime"),
            client_slug=payload.client_slug,
        ),
        "booking_has_name": transition_owner_result.booking_has_name,
        "booking_active": bool(transition_owner_result.booking_state.get("active") is True),
    }
    tool_expected_contract = resolve_tool_expected_reply_contract(**expected_contract_kwargs)
    if tool_expected_contract:
        reply_meta.update(
            {
                "expected_reply_contract_reason": tool_expected_contract.reason,
                "expected_reply_contract_clear": bool(tool_expected_contract.clear_expected_reply),
                "expected_reply_contract_handoff": bool(tool_expected_contract.requires_handoff),
            }
        )
    contract_requires_handoff = bool(
        tool_expected_contract and tool_expected_contract.requires_handoff
    )
    if (
        contract_requires_handoff
        and isinstance(tool_decision, str)
        and tool_decision.strip().casefold() == "branch_missing"
    ):
        allow_handover_create = (
            conversation.state == ConversationState.BOT_ACTIVE.value
            and bool(routing.get("allow_handover_create", False))
        )
        if not allow_handover_create and conversation.state != ConversationState.PENDING.value:
            return None
        user = _resolve_turn_planner_owner_user(
            db,
            client=client,
            conversation=conversation,
            remote_jid=remote_jid.strip(),
        )
        if not isinstance(user, User):
            return None
        handover_message = (
            message_text.strip()
            if isinstance(message_text, str) and message_text.strip()
            else decision_router.DEFAULT_MANAGER_REQUEST_MESSAGE
        )
        handoff_result = materialize_handover(
            db=db,
            conversation=conversation,
            user=user,
            message=handover_message,
            source="tool_registry",
            intent="booking",
            trigger_type="intent",
            trigger_value="branch_missing",
            allow_create=allow_handover_create,
            record_decision_trace=_record_decision_trace,
        )
        if not handoff_result.ok or handoff_result.handover is None:
            return None
        if handoff_result.mode == "create" and payload.client_slug:
            record_escalation_count(payload.client_slug, "intent")
        try:
            handoff_decision = TurnPlanner().build_from_policy_override(
                {
                    "intent": "booking",
                    "action": "handoff",
                    "tool_action": "handoff",
                    "tool_args": {},
                    "reason": tool_expected_contract.reason,
                    "goal": "booking",
                    "needs_manager": True,
                    "slots": semantic_completion_slots,
                },
                interaction_owner=REASONING_CORE_TURN_PLANNER_BOOKING_COMPLETION_OWNER,
                interaction_relation=REASONING_CORE_TURN_PLANNER_BOOKING_COMPLETION_STAGE,
            )
        except (AttributeError, TypeError, ValueError):
            return None
        reply_meta.update(
            {
                "handoff_mode": handoff_result.mode,
                "telegram_sent": handoff_result.telegram_sent,
            }
        )
        if handoff_result.mode == "create":
            reply_meta["handover_reopened"] = handoff_result.handover_reopened
        trace_meta = dict(tool_result.trace) if isinstance(tool_result.trace, dict) else {}
        trace_meta.setdefault("source_route", "llm_policy_core_semantic_arbitration")
        trace_meta.update(
            {
                "handoff_mode": handoff_result.mode,
                "telegram_sent": handoff_result.telegram_sent,
            }
        )
        extra_handoff_trace_payloads = list(extra_trace_payloads)
        if handoff_result.mode == "create":
            extra_handoff_trace_payloads.append(
                {
                    "stage": "escalation",
                    "decision": "created",
                    "state": conversation.state,
                    "intent": "booking",
                    "telegram_sent": handoff_result.telegram_sent,
                    "handover_reopened": handoff_result.handover_reopened,
                }
            )
        return _finalize_turn_planner_owner_cutover(
            payload=payload,
            db=db,
            client_id=client_id,
            preflight_payload=preflight_payload,
            conversation_id=conversation.id,
            decision=handoff_decision,
            reply_text=decision_router.MSG_ESCALATED,
            reply_meta=reply_meta,
            trace_meta=trace_meta,
            owner_cutover=REASONING_CORE_TURN_PLANNER_BOOKING_COMPLETION_OWNER,
            stage=REASONING_CORE_TURN_PLANNER_BOOKING_COMPLETION_STAGE,
            success_label="Turn planner safe booking completion handoff",
            tool_decision=tool_decision if isinstance(tool_decision, str) else None,
            booking_payload_override=transition_owner_result.booking_state,
            outcome_action="escalate",
            outcome_source="tool_registry",
            extra_trace_payloads=extra_handoff_trace_payloads,
            clear_expected_reply=bool(tool_expected_contract.clear_expected_reply),
            clear_reply_reason=tool_expected_contract.reason,
        )
    if not isinstance(tool_result.response_text, str) or not tool_result.response_text.strip():
        return None

    trace_meta = dict(tool_result.trace) if isinstance(tool_result.trace, dict) else {}
    trace_meta.setdefault("source_route", "llm_policy_core_semantic_arbitration")

    followup_type = getattr(tool_expected_contract, _ER_KEY, None) if tool_expected_contract else None
    followup_slot = expected_reply_slot_key(followup_type)
    grounded_referents = None
    grounded_service = transition_owner_result.booking_state.get("service")
    if isinstance(grounded_service, str) and grounded_service.strip():
        grounded_referents = {"service": grounded_service.strip()}
    if (
        isinstance(tool_decision, str)
        and tool_decision.strip().casefold() == "specialist_missing"
        and followup_slot == "name"
    ):
        specialist_followup_payload = dict(policy_payload)
        specialist_followup_payload.update(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action": "calendar.book_slot",
                "goal": "booking",
                "reason": tool_expected_contract.reason if tool_expected_contract else None,
                "next_question": "name",
                "open_questions": ["name"],
                "pending_question_target": "specialist",
                "active_question_relation": "tool_result_followup_specialist_missing",
                "subject_kind": "specialist",
                "capability": "bookability",
                "resolution_mode": "tool_result_followup_specialist_missing",
            }
        )
        specialist_followup_payload["slots"] = {
            "service": semantic_completion_slots.get("service", ""),
            "datetime": semantic_completion_slots.get("datetime", ""),
            "name": "",
        }
        try:
            specialist_followup_decision = TurnPlanner().build_from_policy_override(
                specialist_followup_payload,
                interaction_owner="booking_specialist_followup",
                interaction_relation="tool_result_followup_specialist_missing",
            )
        except (AttributeError, TypeError, ValueError):
            return None

        specialist_followup_name = reply_meta.get("specialist_name")
        if not isinstance(specialist_followup_name, str) or not specialist_followup_name.strip():
            specialist_followup_name = tool_args.get("specialist_name")
        if not isinstance(specialist_followup_name, str) or not specialist_followup_name.strip():
            specialist_followup_name = transition_owner_result.booking_state.get("specialist_name")
        specialist_followup_name = (
            specialist_followup_name.strip()
            if isinstance(specialist_followup_name, str) and specialist_followup_name.strip()
            else None
        )

        specialist_followup_booking_state = (
            dict(transition_owner_result.booking_state)
            if isinstance(transition_owner_result.booking_state, dict)
            else {}
        )
        if specialist_followup_name:
            specialist_followup_booking_state["specialist_name"] = specialist_followup_name
            existing_customer_name = specialist_followup_booking_state.get("name")
            if (
                isinstance(existing_customer_name, str)
                and existing_customer_name.strip()
                and decision_router.normalize_for_matching(existing_customer_name)
                == decision_router.normalize_for_matching(specialist_followup_name)
            ):
                specialist_followup_booking_state.pop("name", None)
        specialist_followup_booking_state["last_question"] = "name"
        specialist_followup_booking_payload = DialogStateService().normalize_booking_payload(
            specialist_followup_booking_state
        )

        specialist_followup_meta = dict(reply_meta)
        specialist_followup_meta.setdefault("source", "tool_registry")
        specialist_followup_meta.setdefault("action_source", "tool_registry")
        specialist_followup_meta.update(
            {
                "pending_question_target": "specialist",
                "pending_question_interaction": "specialist_followup",
                "pending_question_owner": "booking_specialist_followup",
                "active_question_relation": "tool_result_followup_specialist_missing",
            }
        )
        if specialist_followup_name:
            specialist_followup_meta["specialist_name"] = specialist_followup_name

        specialist_followup_trace_payloads = list(extra_trace_payloads)
        specialist_followup_trace = {
            "stage": "pending_question_interaction",
            "decision": "booking_specialist_followup",
            "state": conversation.state,
            "source": "tool_registry",
            "tool_action": "calendar.book_slot",
            "tool_decision": "specialist_missing",
            "pending_question_target": "specialist",
            "active_question_relation": "tool_result_followup_specialist_missing",
            "requested_slot": "name",
            _ER_KEY: followup_type,
        }
        if specialist_followup_name:
            specialist_followup_trace["specialist_name"] = specialist_followup_name
        specialist_followup_trace_payloads.append(specialist_followup_trace)

        return _finalize_turn_planner_owner_cutover(
            payload=payload,
            db=db,
            client_id=client_id,
            preflight_payload=preflight_payload,
            conversation_id=conversation.id,
            decision=specialist_followup_decision,
            reply_text=tool_result.response_text.strip(),
            reply_meta=specialist_followup_meta,
            trace_meta=trace_meta,
            owner_cutover=REASONING_CORE_TURN_PLANNER_BOOKING_COMPLETION_OWNER,
            stage=REASONING_CORE_TURN_PLANNER_BOOKING_COMPLETION_STAGE,
            success_label="Turn planner safe booking completion owner",
            tool_decision=tool_decision if isinstance(tool_decision, str) else None,
            followup_type=followup_type,
            question_reason=tool_expected_contract.reason if tool_expected_contract else None,
            grounded_referents=grounded_referents,
            booking_payload_override=specialist_followup_booking_payload,
            outcome_source="tool_registry",
            extra_trace_payloads=specialist_followup_trace_payloads,
        )

    return _finalize_turn_planner_owner_cutover(
        payload=payload,
        db=db,
        client_id=client_id,
        preflight_payload=preflight_payload,
        conversation_id=conversation.id,
        decision=decision,
        reply_text=tool_result.response_text.strip(),
        reply_meta=reply_meta,
        trace_meta=trace_meta,
        owner_cutover=REASONING_CORE_TURN_PLANNER_BOOKING_COMPLETION_OWNER,
        stage=REASONING_CORE_TURN_PLANNER_BOOKING_COMPLETION_STAGE,
        success_label="Turn planner safe booking completion owner",
        tool_decision=tool_decision if isinstance(tool_decision, str) else None,
        followup_type=followup_type,
        question_reason=tool_expected_contract.reason if tool_expected_contract else None,
        grounded_referents=grounded_referents,
        booking_slot_values=semantic_completion_slots,
        booking_last_question=followup_slot,
        booking_payload_override=transition_owner_result.booking_state,
        outcome_source="tool_registry",
        extra_trace_payloads=extra_trace_payloads,
        clear_expected_reply=bool(
            tool_expected_contract
            and tool_expected_contract.clear_expected_reply
            and not followup_type
        ),
        clear_reply_reason=tool_expected_contract.reason if tool_expected_contract else None,
    )


def _has_usable_tenant_context(payload: WebhookRequest) -> bool:
    tenant_context = getattr(payload, "tenant_context", None)
    if tenant_context is None:
        return False
    tenant_client_slug = (getattr(tenant_context, "client_slug", None) or "").strip()
    return bool(getattr(tenant_context, "client_id", None) is not None or tenant_client_slug)


def _get_preflight_tenant_context_rejection(
    payload: WebhookRequest,
    *,
    client_id: UUID | None,
) -> ReasoningCoreTenantContextRejection | None:
    tenant_context = getattr(payload, "tenant_context", None)
    if tenant_context is None:
        return None

    tenant_payload = tenant_context.model_dump(exclude_none=True, mode="json")
    _, tenant_context_error = validate_tenant_context_contract(
        tenant_payload,
        require_client_id=False,
    )
    if tenant_context_error:
        return ReasoningCoreTenantContextRejection(
            reason_code=REASONING_CORE_TENANT_CONTEXT_INVALID_REASON,
            message="Invalid tenant_context",
            interaction_owner=REASONING_CORE_TENANT_CONTEXT_INVALID_OWNER,
            trace_message="reasoning_core rejected invalid tenant_context contract",
            meta={"error": tenant_context_error},
        )

    tenant_client_id = getattr(tenant_context, "client_id", None)
    if client_id is not None and tenant_client_id and tenant_client_id != client_id:
        return ReasoningCoreTenantContextRejection(
            reason_code=REASONING_CORE_TENANT_CONTEXT_CLIENT_MISMATCH_REASON,
            message="Tenant mismatch",
            interaction_owner=REASONING_CORE_TENANT_CONTEXT_CLIENT_MISMATCH_OWNER,
            trace_message="reasoning_core rejected tenant_context client mismatch",
            meta={
                "tenant_client_id": str(tenant_client_id),
                "expected_client_id": str(client_id),
            },
        )

    expected_client_slug = (payload.client_slug or "").strip()
    tenant_client_slug = (getattr(tenant_context, "client_slug", None) or "").strip()
    if expected_client_slug and tenant_client_slug and tenant_client_slug != expected_client_slug:
        return ReasoningCoreTenantContextRejection(
            reason_code=REASONING_CORE_TENANT_CONTEXT_CLIENT_SLUG_MISMATCH_REASON,
            message="Tenant mismatch",
            interaction_owner=REASONING_CORE_TENANT_CONTEXT_CLIENT_SLUG_MISMATCH_OWNER,
            trace_message="reasoning_core rejected tenant_context client_slug mismatch",
            meta={
                "tenant_client_slug": tenant_client_slug,
                "expected_client_slug": expected_client_slug,
            },
        )

    return None

def _lookup_preexisting_duplicate_message(
    db: Session,
    *,
    client_id: UUID | None,
    message_id: str | None,
) -> ReasoningCoreDuplicateProbe:
    from app.routers.webhook import dedup as dedup_helpers

    owner_probe = dedup_helpers._lookup_preexisting_duplicate_message(
        db,
        client_id=client_id,
        message_id=message_id,
    )
    return ReasoningCoreDuplicateProbe(
        duplicate=owner_probe.duplicate,
        backend=owner_probe.backend,
        fallback_reason=owner_probe.fallback_reason,
    )


def _record_error_decision_meta(
    db: Session,
    *,
    client_slug: str | None,
    message_id: str | None,
    error_type: str,
    error_message: str,
    degrade_artifact: ReasoningCoreDegradeArtifact | None = None,
) -> bool:
    if not client_slug or not message_id:
        return False
    try:
        message = (
            db.query(Message)
            .filter(
                Message.role == "user",
                or_(
                    Message.message_metadata["message_id"].astext == message_id,
                    Message.message_metadata["messageId"].astext == message_id,
                ),
            )
            .order_by(Message.created_at.desc())
            .first()
        )
        if not isinstance(message, Message):
            return False
        updates = {
            "action": "error",
            "intent": "internal_error",
            "source": "reasoning_core",
            "action_error": "exception",
            "error_type": error_type,
            "error": error_message,
        }
        if degrade_artifact is not None:
            updates["turn_outcome"] = degrade_artifact.turn_outcome.to_metadata()
            updates["consultant_core_runtime"] = {
                "schema_version": degrade_artifact.turn_result.schema_version,
                "outcome": degrade_artifact.turn_result.outcome,
                "contract_status": degrade_artifact.turn_result.contract_status,
                "reason_code": degrade_artifact.turn_result.observability.reason_code,
                "reply_kind": degrade_artifact.turn_result.reply.reply_kind,
                "interaction_owner": degrade_artifact.turn_result.policy_decision.interaction.owner,
            }
        _update_message_decision_metadata(message, updates)
        db.commit()
        return True
    except Exception:
        # Never mutate transaction state from the fallback metadata helper.
        # Main exception flow already handled rollback and delivery fallback.
        return False


def _normalize_payload_for_delegation(payload: WebhookRequest) -> WebhookRequest:
    raw_message_type = payload.body.messageType if payload and payload.body else None
    inbound = TurnPlanner().coerce_inbound(
        {
            "message_text": payload.body.message if payload and payload.body else None,
            "message_type": raw_message_type,
            "has_media": (
                bool(payload.body.mediaData)
                or bool(isinstance(raw_message_type, str) and raw_message_type.strip().lower() != "text")
            )
            if payload and payload.body
            else False,
        }
    )
    media_info = _extract_media_info(payload.body) if payload and payload.body else None
    normalized_text = inbound.normalized_message_text(
        media_caption=media_info.caption if media_info else None
    )
    if normalized_text == payload.body.message:
        return payload
    return payload.model_copy(
        update={
            "body": payload.body.model_copy(
                update={
                    "message": normalized_text,
                }
            )
        }
    )


def _resolve_secret_preflight_trace_conversation(
    db: Session,
    *,
    trace_client: Client | None,
    trace_conversation_id: UUID | None,
    trace_message_id: str | None,
    trace_remote_jid: str | None,
) -> Conversation | None:
    if trace_conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == trace_conversation_id).first()
        if conversation:
            return conversation
    if trace_client and trace_message_id:
        saved_message = decision_router._find_message_by_message_id(
            db,
            trace_client.id,
            trace_message_id,
        )
        if saved_message:
            return (
                db.query(Conversation)
                .filter(Conversation.id == saved_message.conversation_id)
                .first()
            )
    if trace_client and trace_remote_jid:
        user = (
            db.query(User)
            .filter(User.client_id == trace_client.id, User.remote_jid == trace_remote_jid)
            .first()
        )
        if user:
            return (
                db.query(Conversation)
                .filter(
                    Conversation.client_id == trace_client.id,
                    Conversation.user_id == user.id,
                    Conversation.status == "active",
                )
                .first()
            )
    return None


def _record_secret_preflight_trace(
    trace_conversation: Conversation | None,
    *,
    stage: str,
    decision: str,
    reason: str,
    meta: dict[str, object] | None = None,
) -> bool:
    if not trace_conversation:
        return False
    trace_payload: dict[str, object] = {
        "stage": stage,
        "decision": decision,
        "reason": reason,
    }
    if meta:
        trace_payload.update(meta)
    _record_decision_trace(trace_conversation, trace_payload)
    return True


def _run_secret_enforced_preflight(
    payload: WebhookRequest,
    db: Session,
    *,
    provided_secret: str | None,
    conversation_id: UUID | None,
) -> tuple[WebhookResponse | None, dict[str, object]]:
    from app.routers.webhook import http as http_helpers

    preflight_context = {"client_slug": payload.client_slug}
    preflight_trace_id = get_trace_id()
    if preflight_trace_id:
        preflight_context["trace_id"] = preflight_trace_id
    with start_span("webhook.preflight", context=preflight_context):
        return http_helpers._run_preflight(
            payload,
            db,
            provided_secret=provided_secret,
            enforce_secret=True,
            conversation_id=conversation_id,
            resolve_trace_conversation=lambda **kwargs: _resolve_secret_preflight_trace_conversation(
                db,
                **kwargs,
            ),
            record_early_trace=_record_secret_preflight_trace,
        )


@contextmanager
def _use_runtime_loader_overrides(
    db: Session,
    *,
    payload: WebhookRequest,
    preflight_payload: dict[str, object] | None,
    skip_persist: bool,
) -> Iterator[None]:
    if not isinstance(preflight_payload, dict):
        yield
        return

    client = preflight_payload.get("client")
    client_id = getattr(client, "id", None)
    branch_id = preflight_payload.get("resolved_branch_id")
    runtime_capabilities = build_runtime_capabilities(
        db,
        client_id=client_id if isinstance(client_id, UUID) else None,
        branch_id=branch_id if isinstance(branch_id, UUID) else None,
    )
    runtime_truth = build_runtime_truth(
        db,
        client_slug=payload.client_slug,
        client_id=client_id if isinstance(client_id, UUID) else None,
        branch_id=branch_id if isinstance(branch_id, UUID) else None,
        allow_fallback=should_allow_truth_fallback() or skip_persist,
    )
    with ExitStack() as stack:
        stack.enter_context(use_runtime_capabilities_override(runtime_capabilities))
        stack.enter_context(use_runtime_truth_override(runtime_truth))
        yield


async def run_reasoning_core(request: ReasoningCoreRequest) -> WebhookResponse:
    return await handle_webhook_payload(
        request.payload,
        request.db,
        provided_secret=request.provided_secret,
        enforce_secret=request.enforce_secret,
        enqueue_only=request.enqueue_only,
        skip_persist=request.skip_persist,
        conversation_id=request.conversation_id,
        batch_messages=request.batch_messages,
        outbox_ids=request.outbox_ids,
        outbox_created_at=request.outbox_created_at,
        preflight_payload=request.preflight_payload,
    )


async def handle_webhook_payload(
    payload: WebhookRequest,
    db: Session,
    *,
    provided_secret: str | None,
    enforce_secret: bool,
    enqueue_only: bool = False,
    skip_persist: bool = False,
    conversation_id: UUID | None = None,
    batch_messages: list[str] | None = None,
    outbox_ids: list[str] | None = None,
    outbox_created_at: datetime | None = None,
    preflight_payload: dict[str, object] | None = None,
) -> WebhookResponse:
    from app.core import consultant_runtime

    return await consultant_runtime.handle_webhook_payload(
        payload,
        db,
        provided_secret=provided_secret,
        enforce_secret=enforce_secret,
        enqueue_only=enqueue_only,
        skip_persist=skip_persist,
        conversation_id=conversation_id,
        batch_messages=batch_messages,
        outbox_ids=outbox_ids,
        outbox_created_at=outbox_created_at,
        preflight_payload=preflight_payload,
    )


__all__ = [
    "ReasoningCoreDegradeArtifact",
    "ReasoningCoreDuplicateProbe",
    "ReasoningCorePreflightArtifact",
    "ReasoningCoreRequest",
    "ReasoningCoreTenantContextRejection",
    "REASONING_CORE_DEGRADE_REASON",
    "REASONING_CORE_DUPLICATE_REASON",
    "REASONING_CORE_MISSING_REMOTE_JID_REASON",
    "REASONING_CORE_MISSING_TENANT_CONTEXT_REASON",
    "REASONING_CORE_PREFLIGHT_REASON",
    "REASONING_CORE_REMOTE_BRANCH_PHONE_REASON",
    "REASONING_CORE_SENDER_BRANCH_IGNORE_REASON",
    "REASONING_CORE_TENANT_CONTEXT_CLIENT_MISMATCH_REASON",
    "REASONING_CORE_TENANT_CONTEXT_CLIENT_SLUG_MISMATCH_REASON",
    "REASONING_CORE_TENANT_CONTEXT_INVALID_OWNER",
    "REASONING_CORE_TENANT_CONTEXT_INVALID_REASON",
    "STAGE_ORDER_SNAPSHOT",
    "_build_duplicate_message_artifact",
    "_build_empty_message_artifact",
    "_build_missing_remote_jid_artifact",
    "_build_missing_tenant_context_artifact",
    "_build_remote_branch_phone_ignore_artifact",
    "_build_sender_branch_ignore_artifact",
    "_build_tenant_context_reject_artifact",
    "_has_usable_tenant_context",
    "_get_preflight_tenant_context_rejection",
    "_lookup_client_branch_phone",
    "_lookup_preexisting_duplicate_message",
    "_normalize_payload_for_delegation",
    "_build_runtime_exception_artifact",
    "handle_webhook_payload",
    "run_reasoning_core",
    "stage_order_hash",
]
