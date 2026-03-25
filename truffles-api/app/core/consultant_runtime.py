from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.boundary_validator import BoundaryOverride, BoundaryValidator
from app.core.dialog_state_service import DialogState, DialogStateService
from app.core.response_realizer import ReplyEnvelope, ResponseRealizer
from app.core.turn_executor import RuntimeExecutionResult, TurnExecutor
from app.core.turn_planner import PolicyDecision, TurnPlanner
from app.logging_config import get_logger, get_trace_id
from app.models import Client, Conversation, Message, User
from app.routers.webhook import http as http_helpers
from app.routers.webhook.runtime_primitives import MSG_AI_ERROR, MSG_DELIVERY_FAILED
from app.routers.webhook.session_memory import (
    _get_session_memory,
    _is_session_reset_only_message,
    _normalize_session_memory,
    _session_memory_snapshot,
    _should_reset_session_memory,
)
from app.routers.webhook.trace import (
    _record_decision_trace,
    _record_message_decision_meta,
    _update_message_decision_metadata,
)
from app.schemas.webhook import WebhookRequest, WebhookResponse
from app.services.capabilities_runtime import build_runtime_capabilities, set_runtime_capabilities
from app.services.chatflow_service import get_instance_id, send_message_safe
from app.services.conversation_service import get_or_create_conversation, get_or_create_user
from app.services.handover_owner_service import (
    create_handover,
    get_active_handover,
    send_telegram_notification,
)
from app.services.knowledge_runtime import (
    build_runtime_truth,
    set_runtime_truth,
    should_allow_truth_fallback,
)
from app.services.message_service import save_message
from app.services.pack_runtime_service import get_pack_service_hint, semantic_service_match
from app.services.state_machine import ConversationState
from app.services.state_service import apply_simulation_context, transition_state

logger = get_logger("consultant_runtime")

_RUNTIME_ENTRYPOINT_NAME = "consultant_runtime"
_RUNTIME_TRACE_KEY = "decision_trace"
_RUNTIME_ALLOWED_OUTCOMES = {"FACT", "COLLECT", "HANDOFF"}
_NO_SEND_SOURCES = {"message_api", "console_simulation", "simulation"}


@dataclass(frozen=True)
class LoadedRuntimeState:
    context: dict[str, Any]
    dialog_state: DialogState
    booking_state: dict[str, Any]
    expected_reply_type: str | None
    expected_reply_reason: str | None
    current_goal: str | None


@dataclass(frozen=True)
class PreparedConversation:
    client: Client
    user: User
    conversation: Conversation
    user_message: Message | None
    remote_jid: str
    branch_id: UUID | None
    tenant_context: dict[str, Any]
    instance_id: str | None
    source: str | None


class ConsultantRuntime:
    def __init__(self) -> None:
        self.planner = TurnPlanner()
        self.boundary = BoundaryValidator()
        self.dialog_state = DialogStateService()
        self.executor = TurnExecutor()
        self.realizer = ResponseRealizer()

    async def handle_webhook_payload(
        self,
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
        now = datetime.now(timezone.utc)
        try:
            preflight = self._resolve_preflight(
                payload,
                db,
                provided_secret=provided_secret,
                enforce_secret=enforce_secret,
                conversation_id=conversation_id,
                preflight_payload=preflight_payload,
            )
            if isinstance(preflight, WebhookResponse):
                return preflight

            prepared = self._prepare_conversation(
                db,
                payload=payload,
                preflight=preflight,
                now=now,
                skip_persist=skip_persist,
            )
            runtime_state = self._load_runtime_state(
                prepared.conversation,
                state_hint=(payload.body.message or ""),
            )
            control_response, runtime_state = self._handle_control_turn(
                db,
                payload=payload,
                prepared=prepared,
                runtime_state=runtime_state,
                now=now,
                enqueue_only=enqueue_only,
                skip_persist=skip_persist,
            )
            if control_response is not None:
                db.commit()
                return control_response
            self._prime_runtime_context(
                db,
                client=prepared.client,
                branch_id=prepared.branch_id,
                payload=payload,
            )

            decision, boundary_override = self._plan_turn(
                db,
                payload=payload,
                prepared=prepared,
                runtime_state=runtime_state,
            )
            boundary_result = self.boundary.validate(
                decision,
                override=boundary_override,
            )
            decision = boundary_result.decision
            boundary_override = boundary_result.override
            decision.meta.setdefault("client_id", prepared.client.id)
            decision.meta.setdefault("conversation_id", prepared.conversation.id)
            if outbox_ids:
                decision.meta.setdefault("outbox_ids", list(outbox_ids))
            if batch_messages:
                decision.meta.setdefault("batch_messages", list(batch_messages))
            if outbox_created_at is not None:
                decision.meta.setdefault("outbox_created_at", outbox_created_at.isoformat())

            execution = self._execute_turn(
                db,
                prepared=prepared,
                decision=decision,
                payload=payload,
                runtime_state=runtime_state,
                now=now,
            )
            if execution.request_handoff and decision.outcome != "HANDOFF":
                decision = self.planner.build_controlled_degrade(
                    reason_code="executor:handoff_requested",
                    action="handoff",
                    intent="executor_handoff",
                    interaction_owner="turn_executor",
                )
                boundary_override = self.boundary.build_degrade_override(
                    reason_code="executor:handoff_requested",
                    public_message=execution.text,
                    trace_message="execution_requested_handoff",
                )

            effective_decision = self._finalize_execution_decision(
                decision=decision,
                execution=execution,
            )
            updated_context, dialog_state = self._write_runtime_state(
                prepared=prepared,
                runtime_state=runtime_state,
                decision=effective_decision,
                execution=execution,
                now=now,
            )
            prepared.conversation.context = updated_context

            if effective_decision.outcome == "HANDOFF":
                self._activate_handoff(
                    db,
                    prepared=prepared,
                    decision=effective_decision,
                    user_message_text=payload.body.message or "",
                )
            else:
                self._resume_bot_if_needed(db, prepared=prepared)

            reply = self.realizer.realize(
                effective_decision,
                override=boundary_override,
                text=execution.text,
                channel=prepared.conversation.channel,
            )
            turn_result = self.executor.assemble(
                decision=effective_decision,
                dialog_state=dialog_state,
                reply=reply,
                boundary_override=boundary_override,
                contract_status="degraded" if boundary_override else "ok",
                reason_code=(boundary_override.reason_code if boundary_override else None),
                stages=["ingress", "planner", "boundary", "state", "executor", "realizer"],
            )
            bot_response = self._send_and_persist_reply(
                db,
                prepared=prepared,
                reply=reply,
                payload=payload,
                enqueue_only=enqueue_only,
                skip_persist=skip_persist,
            )
            self._record_turn_trace(
                conversation=prepared.conversation,
                user_message=prepared.user_message,
                bot_response=bot_response,
                decision=effective_decision,
                execution=execution,
                turn_result=turn_result,
                delivered=bool(bot_response),
            )
            db.commit()
            return WebhookResponse(
                success=True,
                message="Handled",
                conversation_id=prepared.conversation.id,
                bot_response=reply.text,
            )
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - runtime safety net
            logger.exception(
                "Consultant runtime failed",
                extra={
                    "context": {
                        "trace_id": get_trace_id(),
                        "client_slug": payload.client_slug,
                        "error": str(exc)[:200],
                        "error_type": type(exc).__name__,
                    }
                },
            )
            try:
                db.rollback()
            except Exception:
                logger.warning("Consultant runtime rollback failed")
            return WebhookResponse(
                success=True,
                message="Runtime fallback",
                bot_response=MSG_DELIVERY_FAILED if not skip_persist else MSG_AI_ERROR,
            )

    def _resolve_preflight(
        self,
        payload: WebhookRequest,
        db: Session,
        *,
        provided_secret: str | None,
        enforce_secret: bool,
        conversation_id: UUID | None,
        preflight_payload: dict[str, object] | None,
    ) -> dict[str, Any] | WebhookResponse:
        if isinstance(preflight_payload, dict):
            return dict(preflight_payload)

        response, derived = http_helpers._run_preflight(
            payload,
            db,
            provided_secret=provided_secret,
            enforce_secret=enforce_secret,
            conversation_id=conversation_id,
            resolve_trace_conversation=lambda **_: None,
            record_early_trace=lambda *_, **__: False,
        )
        if response is not None:
            return response
        return derived

    def _prepare_conversation(
        self,
        db: Session,
        *,
        payload: WebhookRequest,
        preflight: dict[str, Any],
        now: datetime,
        skip_persist: bool,
    ) -> PreparedConversation:
        client = preflight["client"]
        remote_jid = preflight["remote_jid"]
        branch_id = preflight.get("resolved_branch_id")
        user = get_or_create_user(db, client.id, remote_jid)
        conversation = get_or_create_conversation(
            db,
            client.id,
            user.id,
            channel="whatsapp",
            branch_id=branch_id,
        )
        conversation.last_message_at = now
        if branch_id and conversation.branch_id != branch_id:
            conversation.branch_id = branch_id
        user.last_active_at = now

        tenant_context = dict(preflight.get("tenant_context") or {})
        metadata = payload.body.metadata
        if metadata is not None:
            tenant_origin_source = (
                tenant_context.get("origin_source")
                if isinstance(tenant_context, dict)
                else None
            )
            internal_simulation_source = bool(
                isinstance(tenant_context, dict)
                and (tenant_origin_source or tenant_context.get("source"))
                == "console_consultant_verification"
            )
            apply_simulation_context(
                conversation,
                metadata,
                allow_internal_source=internal_simulation_source,
            )

        user_message = None
        if not skip_persist:
            user_message = self._persist_user_message(
                db,
                conversation=conversation,
                client_id=client.id,
                payload=payload,
                preflight=preflight,
                now=now,
            )

        source = tenant_context.get("source") if isinstance(tenant_context, dict) else None
        instance_id = getattr(metadata, "instanceId", None) or tenant_context.get("instance_id")
        return PreparedConversation(
            client=client,
            user=user,
            conversation=conversation,
            user_message=user_message,
            remote_jid=remote_jid,
            branch_id=branch_id,
            tenant_context=tenant_context,
            instance_id=instance_id,
            source=source,
        )

    def _load_runtime_state(
        self,
        conversation: Conversation,
        *,
        state_hint: str,
    ) -> LoadedRuntimeState:
        context = dict(conversation.context or {})
        payload = self.dialog_state.load_runtime_payload(context)
        booking_state = dict(payload.get("booking_payload") or {})
        current_goal = payload.get("current_goal")
        if current_goal is None and booking_state:
            current_goal = "booking"
        return LoadedRuntimeState(
            context=context,
            dialog_state=payload["dialog_state"],
            booking_state=booking_state,
            expected_reply_type=payload.get("expected_reply_type"),
            expected_reply_reason=payload.get("expected_reply_reason"),
            current_goal=current_goal,
        )

    def _handle_control_turn(
        self,
        db: Session,
        *,
        payload: WebhookRequest,
        prepared: PreparedConversation,
        runtime_state: LoadedRuntimeState,
        now: datetime,
        enqueue_only: bool,
        skip_persist: bool,
    ) -> tuple[WebhookResponse | None, LoadedRuntimeState]:
        message_text = payload.body.message
        if not _should_reset_session_memory(message_text):
            return None, runtime_state

        reset_snapshot = self._reset_runtime_context(
            prepared.conversation,
            now=now,
            reason="explicit_reset",
        )
        if prepared.user_message is not None:
            _update_message_decision_metadata(
                prepared.user_message,
                {"session_memory_reset": "explicit_reset"},
            )
        _record_decision_trace(
            prepared.conversation,
            {
                "stage": "session_memory",
                "decision": "reset",
                "reason": "explicit_reset",
                **reset_snapshot,
            },
        )
        runtime_state = self._load_runtime_state(
            prepared.conversation,
            state_hint=(message_text or ""),
        )
        if not _is_session_reset_only_message(message_text):
            return None, runtime_state

        reply = ReplyEnvelope(
            channel=prepared.conversation.channel or "whatsapp",
            reply_kind="system",
            text="Ок, давайте новую тему. Чем могу помочь?",
            meta={"outcome": "FACT", "control_action": "session_reset"},
        )
        if prepared.user_message is not None:
            _record_message_decision_meta(
                prepared.user_message,
                action="smalltalk",
                intent="reset",
                source="session_memory",
                fast_intent=False,
            )
        _record_decision_trace(
            prepared.conversation,
            {
                "stage": "session_memory",
                "decision": "reset_ack",
                "reason": "explicit_reset",
            },
        )
        bot_response = self._send_and_persist_reply(
            db,
            prepared=prepared,
            reply=reply,
            payload=payload,
            enqueue_only=enqueue_only,
            skip_persist=skip_persist,
        )
        decision_meta = {
            "source": _RUNTIME_ENTRYPOINT_NAME,
            "action": "smalltalk",
            "intent": "reset",
            "outcome": "FACT",
            "tool_action": "session_reset",
            "interaction_owner": "session_memory",
            "session_memory_reset": "explicit_reset",
        }
        if prepared.user_message is not None:
            _update_message_decision_metadata(prepared.user_message, decision_meta)
        if bot_response is not None:
            _update_message_decision_metadata(bot_response, decision_meta)
        return (
            WebhookResponse(
                success=True,
                message="Handled",
                conversation_id=prepared.conversation.id,
                bot_response=reply.text,
            ),
            runtime_state,
        )

    def _reset_runtime_context(
        self,
        conversation: Conversation,
        *,
        now: datetime,
        reason: str,
    ) -> dict[str, Any]:
        context = dict(conversation.context or {})
        raw_session_memory = _get_session_memory(context)
        session_memory, _ = _normalize_session_memory(raw_session_memory)
        snapshot = _session_memory_snapshot(session_memory)
        snapshot["memory_keys"] = sorted(
            key for key in session_memory.keys() if isinstance(key, str)
        )
        updated_context = self.dialog_state.reset_runtime_continuity(
            context,
            now=now,
            reason=reason,
        )
        conversation.context = updated_context
        return snapshot

    def _prime_runtime_context(
        self,
        db: Session,
        *,
        client: Client,
        branch_id: UUID | None,
        payload: WebhookRequest,
    ) -> None:
        runtime_capabilities = build_runtime_capabilities(
            db,
            client_id=client.id,
            branch_id=branch_id,
        )
        set_runtime_capabilities(runtime_capabilities)
        runtime_truth = build_runtime_truth(
            db,
            client_slug=payload.client_slug,
            client_id=client.id,
            branch_id=branch_id,
            allow_fallback=should_allow_truth_fallback(),
        )
        set_runtime_truth(runtime_truth)

    def _plan_turn(
        self,
        db: Session,
        *,
        payload: WebhookRequest,
        prepared: PreparedConversation,
        runtime_state: LoadedRuntimeState,
    ) -> tuple[PolicyDecision, BoundaryOverride | None]:
        if prepared.conversation.state == ConversationState.MANAGER_ACTIVE.value:
            decision = self.planner.build_controlled_degrade(
                reason_code="manager_active",
                action="handoff",
                intent="manager_active",
                interaction_owner="pending_gate",
            )
            override = self.boundary.build_degrade_override(
                reason_code="manager_active",
                public_message="Менеджер уже подключился к диалогу.",
                trace_message="manager_active_gate",
            )
            return decision, override

        recent_summary = self._build_memory_summary(db, prepared.conversation)
        grounded_service = self._resolve_explicit_service_grounding(
            payload.body.message,
            client_slug=payload.client_slug,
            branch_id=prepared.branch_id,
        )
        grounded_booking_state = dict(runtime_state.booking_state or {})
        if grounded_service and not (
            isinstance(grounded_booking_state.get("service"), str)
            and grounded_booking_state.get("service", "").strip()
        ):
            grounded_booking_state["service"] = grounded_service
        memory_profile = self._build_policy_core_memory_profile(
            runtime_state,
            grounded_service=grounded_service,
        )
        decision = self.planner.plan(
            message_text=payload.body.message,
            client_slug=payload.client_slug,
            expected_reply_type=runtime_state.expected_reply_type,
            expected_reply_reason=runtime_state.expected_reply_reason,
            current_goal=runtime_state.current_goal,
            booking_state=grounded_booking_state,
            memory_summary=recent_summary,
            memory_profile=memory_profile,
        )
        override = None
        if decision.outcome not in _RUNTIME_ALLOWED_OUTCOMES:
            decision = self.planner.build_controlled_degrade(
                reason_code="planner:invalid_outcome",
                action="handoff",
                intent="planner_invalid_outcome",
                interaction_owner="turn_planner",
            )
        if decision.meta.get("degrade_path"):
            override = self.boundary.build_degrade_override(
                reason_code=str(decision.meta.get("reason_code") or "planner_degrade"),
                public_message="Передаю диалог менеджеру, чтобы не потерять ваш запрос.",
                trace_message="planner_degrade",
            )
        return decision, override

    def _build_policy_core_memory_profile(
        self,
        runtime_state: LoadedRuntimeState,
        *,
        grounded_service: str | None = None,
    ) -> dict[str, Any]:
        profile: dict[str, Any] = {}
        if runtime_state.current_goal:
            profile["active_goal"] = runtime_state.current_goal
        if runtime_state.expected_reply_type:
            profile["expected_reply_type"] = runtime_state.expected_reply_type

        active_slots = [
            slot_key
            for slot_key in ("service", "datetime", "name", "phone")
            if isinstance(runtime_state.booking_state.get(slot_key), str)
            and runtime_state.booking_state.get(slot_key, "").strip()
        ]
        if active_slots:
            profile["active_slots"] = active_slots

        dialog_state = runtime_state.dialog_state
        current_referents: dict[str, str] = {}
        referent_map = {
            "service": dialog_state.current_referents.service,
            "specialist": dialog_state.current_referents.specialist,
            "branch": dialog_state.current_referents.branch,
            "booking_ref": dialog_state.current_referents.booking,
            "customer": dialog_state.current_referents.customer,
        }
        for key, raw_value in referent_map.items():
            if isinstance(raw_value, str) and raw_value.strip():
                current_referents[key] = raw_value.strip()
        if grounded_service and "service" not in current_referents:
            current_referents["service"] = grounded_service
        if current_referents:
            profile["current_referents"] = current_referents

        semantic_contract = (
            dict(dialog_state.meta.get("semantic_contract"))
            if isinstance(dialog_state.meta.get("semantic_contract"), dict)
            else {}
        )
        if semantic_contract:
            semantic_referents = semantic_contract.get("referents")
            if isinstance(semantic_referents, dict):
                for referent_key, payload in semantic_referents.items():
                    if referent_key in current_referents:
                        continue
                    if not isinstance(payload, dict):
                        continue
                    referent_value = payload.get("value")
                    if isinstance(referent_value, str) and referent_value.strip():
                        current_referents[referent_key] = referent_value.strip()
                if current_referents:
                    profile["current_referents"] = current_referents
            profile["semantic_contract"] = semantic_contract

        pending_contract: dict[str, Any] = {}
        next_question = dialog_state.pending_question_contract.next_question
        if isinstance(next_question, str) and next_question.strip():
            pending_contract["slot"] = next_question.strip()
        elif runtime_state.expected_reply_type:
            pending_contract["slot"] = {
                "service_choice": "service",
                "time": "datetime",
                "name": "name",
                "phone": "phone",
            }.get(runtime_state.expected_reply_type)
        if runtime_state.expected_reply_type:
            pending_contract["expected_reply_type"] = runtime_state.expected_reply_type
        if runtime_state.expected_reply_reason:
            pending_contract["reason"] = runtime_state.expected_reply_reason
        if pending_contract:
            profile["pending_question_contract"] = pending_contract

        interaction_state: dict[str, Any] = {}
        if dialog_state.interaction_state.resume_slot:
            interaction_state["resume_slot"] = dialog_state.interaction_state.resume_slot
        if dialog_state.interaction_state.interaction_target:
            interaction_state["interaction_target"] = (
                dialog_state.interaction_state.interaction_target
            )
        if dialog_state.interaction_state.interaction_relation:
            interaction_state["interaction_relation"] = (
                dialog_state.interaction_state.interaction_relation
            )
        if dialog_state.interaction_state.interaction_owner:
            interaction_state["interaction_owner"] = dialog_state.interaction_state.interaction_owner
        grounded_referents = dict(dialog_state.interaction_state.grounded_referents or {})
        if not grounded_referents:
            grounded_referents = dict(current_referents)
        if grounded_referents:
            interaction_state["grounded_referents"] = grounded_referents
        if interaction_state:
            profile["interaction_state"] = interaction_state

        return profile

    @staticmethod
    def _resolve_explicit_service_grounding(
        message_text: str | None,
        *,
        client_slug: str | None,
        branch_id: UUID | None,
    ) -> str | None:
        if not isinstance(message_text, str) or not message_text.strip():
            return None
        match = semantic_service_match(
            message_text,
            client_slug,
            branch_id=str(branch_id) if branch_id else None,
        )
        if match and getattr(match, "action", None) == "match":
            canonical_name = getattr(match, "canonical_name", None)
            if isinstance(canonical_name, str) and canonical_name.strip():
                return canonical_name.strip()
        fallback = get_pack_service_hint(
            message_text,
            client_slug=client_slug,
            branch_id=str(branch_id) if branch_id else None,
        )
        if not isinstance(fallback, str):
            return None
        cleaned = fallback.strip()
        return cleaned or None

    def _execute_turn(
        self,
        db: Session,
        *,
        prepared: PreparedConversation,
        decision: PolicyDecision,
        payload: WebhookRequest,
        runtime_state: LoadedRuntimeState,
        now: datetime,
    ) -> RuntimeExecutionResult:
        user_phone = prepared.user.phone
        if not user_phone and prepared.remote_jid:
            digits = "".join(ch for ch in prepared.remote_jid.split("@", 1)[0] if ch.isdigit())
            user_phone = digits or None
        return self.executor.execute(
            decision,
            db=db,
            message_text=payload.body.message,
            client_slug=payload.client_slug,
            branch_id=prepared.branch_id,
            booking_state=runtime_state.booking_state,
            user_name=prepared.user.name,
            user_phone=user_phone,
            now=now,
        )

    def _write_runtime_state(
        self,
        *,
        prepared: PreparedConversation,
        runtime_state: LoadedRuntimeState,
        decision: PolicyDecision,
        execution: RuntimeExecutionResult,
        now: datetime,
    ) -> tuple[dict[str, Any], DialogState]:
        execution_meta = dict(execution.meta)
        if execution.clear_booking:
            execution_meta["clear_booking"] = True
        if decision.outcome == "COLLECT" and execution.tool_decision:
            execution_meta.setdefault("next_slot", execution.tool_decision)
        updated_context, dialog_state, _booking_payload = self.dialog_state.write_runtime_payload(
            runtime_state.context,
            decision=decision,
            execution_meta=execution_meta,
            now=now,
        )
        return updated_context, dialog_state

    @staticmethod
    def _finalize_execution_decision(
        *,
        decision: PolicyDecision,
        execution: RuntimeExecutionResult,
    ) -> PolicyDecision:
        if (
            execution.tool_action == "calendar.book_slot"
            and execution.tool_decision == "ok"
            and isinstance(execution.meta, dict)
            and execution.meta.get("appointment_id")
        ):
            return decision.model_copy(update={"outcome": "FACT"})
        return decision

    def _activate_handoff(
        self,
        db: Session,
        *,
        prepared: PreparedConversation,
        decision: PolicyDecision,
        user_message_text: str,
    ) -> None:
        handover = get_active_handover(db, prepared.conversation.id)
        if handover is None:
            handover = create_handover(
                db,
                prepared.conversation,
                prepared.user,
                trigger_type="intent",
                trigger_value=decision.intent,
                user_message=user_message_text,
            )
        transition_state(
            prepared.conversation,
            ConversationState.PENDING,
            allow_same=True,
            enforce=False,
            handover=handover,
        )
        if prepared.conversation.state == ConversationState.PENDING.value:
            try:
                send_telegram_notification(
                    db,
                    handover,
                    prepared.conversation,
                    prepared.user,
                    user_message_text,
                )
            except Exception:
                logger.warning(
                    "Failed to notify handoff transport",
                    extra={"context": {"conversation_id": str(prepared.conversation.id)}},
                )

    def _resume_bot_if_needed(self, db: Session, *, prepared: PreparedConversation) -> None:
        if prepared.conversation.state not in {
            ConversationState.PENDING.value,
            ConversationState.MANAGER_ACTIVE.value,
        }:
            return
        active_handover = get_active_handover(db, prepared.conversation.id)
        transition_state(
            prepared.conversation,
            ConversationState.BOT_ACTIVE,
            allow_same=True,
            enforce=False,
            handover=active_handover,
        )
        if active_handover is not None:
            active_handover.status = "bot_handling"

    def _send_and_persist_reply(
        self,
        db: Session,
        *,
        prepared: PreparedConversation,
        reply: ReplyEnvelope,
        payload: WebhookRequest,
        enqueue_only: bool,
        skip_persist: bool,
    ) -> Message | None:
        metadata = payload.body.metadata
        transport_status = "skipped"
        transport_reason = None
        if not skip_persist:
            assistant_message = save_message(
                db,
                prepared.conversation.id,
                prepared.client.id,
                "assistant",
                reply.text,
                message_metadata={
                    "source": _RUNTIME_ENTRYPOINT_NAME,
                    "reply_kind": reply.reply_kind,
                },
            )
        else:
            assistant_message = None

        if enqueue_only or skip_persist or self._should_skip_send(prepared, metadata):
            transport_reason = "transport_suppressed"
        else:
            instance_id = prepared.instance_id or get_instance_id(
                db,
                prepared.client.id,
                branch_id=prepared.branch_id,
                remote_jid=prepared.remote_jid,
            )
            if instance_id:
                result = send_message_safe(
                    instance_id,
                    prepared.remote_jid,
                    reply.text,
                    getattr(metadata, "messageId", None),
                    notify_on_failure=True,
                    record_metrics=True,
                )
                if result.is_ok():
                    transport_status = "delivered"
                    transport_reason = None
                else:
                    transport_status = "failed"
                    transport_reason = type(result.error).__name__ if result.error else "delivery_failed"
            else:
                transport_status = "failed"
                transport_reason = "transport_target_missing"

        if assistant_message is not None:
            assistant_meta = dict(assistant_message.message_metadata or {})
            assistant_meta["transport_status"] = transport_status
            if transport_reason:
                assistant_meta["transport_reason"] = transport_reason
            assistant_message.message_metadata = assistant_meta
        return assistant_message

    def _record_turn_trace(
        self,
        *,
        conversation: Conversation,
        user_message: Message | None,
        bot_response: Message | None,
        decision: PolicyDecision,
        execution: RuntimeExecutionResult,
        turn_result: Any,
        delivered: bool,
    ) -> None:
        dialog_state = turn_result.dialog_state
        contract_action = self._derive_contract_action(
            decision=decision,
            execution=execution,
            turn_result=turn_result,
        )
        contract_source = self._derive_contract_source(decision)
        expected_reply_type = dialog_state.projections.expected_reply_type
        expected_reply_reason = dialog_state.projections.expected_reply_reason
        trace_event = {
            "stage": _RUNTIME_ENTRYPOINT_NAME,
            "decision": contract_action,
            "intent": decision.intent,
            "outcome": decision.outcome,
            "tool_action": execution.tool_action,
            "tool_decision": execution.tool_decision,
            "reply_kind": turn_result.reply.reply_kind,
            "interaction_owner": decision.interaction.owner,
            "source": contract_source,
            "trace_id": get_trace_id(),
            "delivered": delivered,
        }
        if expected_reply_type:
            trace_event["expected_reply_type"] = expected_reply_type
        if expected_reply_reason:
            trace_event["expected_reply_reason"] = expected_reply_reason
        pending_question_act = None
        pending_question_target = None
        active_question_relation = decision.interaction.relation
        question_contract_active = False
        if isinstance(execution.meta, dict):
            pending_question_act = execution.meta.get("pending_question_act")
            pending_question_target = execution.meta.get("pending_question_target")
            question_contract_active = bool(execution.meta.get("question_contract"))
        if isinstance(decision.meta, dict):
            pending_question_act = pending_question_act or decision.meta.get("pending_question_act")
            pending_question_target = pending_question_target or decision.meta.get(
                "pending_question_target"
            )
            question_contract_active = question_contract_active or bool(
                decision.meta.get("question_contract")
            )
        if not pending_question_target:
            pending_question_target = decision.interaction.target
        if pending_question_target:
            trace_event["pending_question_target"] = pending_question_target
        if active_question_relation:
            trace_event["active_question_relation"] = active_question_relation
        semantic_contract = (
            dict(dialog_state.meta.get("semantic_contract"))
            if isinstance(dialog_state.meta.get("semantic_contract"), dict)
            else {}
        )
        if not semantic_contract and isinstance(decision.meta.get("semantic_contract"), dict):
            semantic_contract = dict(decision.meta.get("semantic_contract"))
        if semantic_contract:
            trace_event["semantic_contract"] = semantic_contract
        context = dict(conversation.context or {})
        trace = context.get(_RUNTIME_TRACE_KEY)
        if not isinstance(trace, list):
            trace = []
        if pending_question_act and expected_reply_type:
            trace.append(
                {
                    "stage": "pending_question_interaction",
                    "decision": pending_question_act,
                    "state": getattr(conversation, "state", None),
                    "source": contract_source,
                    "pending_question_act": pending_question_act,
                    "pending_question_target": pending_question_target or "time",
                    "active_question_relation": active_question_relation or pending_question_act,
                    "expected_reply_type": expected_reply_type,
                }
            )
        if question_contract_active and expected_reply_type:
            trace.append(
                {
                    "stage": "question_contract",
                    "decision": pending_question_act or contract_action,
                    "state": getattr(conversation, "state", None),
                    "source": contract_source,
                    "expected_reply_type": expected_reply_type,
                    "reason": expected_reply_reason,
                    "pending_question_act": pending_question_act,
                    "pending_question_target": pending_question_target or "time",
                }
            )
        trace.append(trace_event)
        context[_RUNTIME_TRACE_KEY] = trace[-20:]
        conversation.context = context

        decision_meta = {
            "source": contract_source,
            "runtime_entrypoint": _RUNTIME_ENTRYPOINT_NAME,
            "action": contract_action,
            "intent": decision.intent,
            "outcome": decision.outcome,
            "tool_action": execution.tool_action,
            "tool_decision": execution.tool_decision,
            "interaction_owner": decision.interaction.owner,
            "decision_trace": trace_event,
        }
        if expected_reply_type:
            decision_meta["expected_reply_type"] = expected_reply_type
        if expected_reply_reason:
            decision_meta["expected_reply_reason"] = expected_reply_reason
        if pending_question_target:
            decision_meta["pending_question_target"] = pending_question_target
        if active_question_relation:
            decision_meta["active_question_relation"] = active_question_relation
        if semantic_contract:
            decision_meta["semantic_contract"] = semantic_contract
        if contract_source != decision.source:
            decision_meta["source_detail"] = decision.source
        if isinstance(execution.meta, dict):
            decision_meta.update(execution.meta)
        if user_message is not None:
            user_meta = dict(user_message.message_metadata or {})
            existing = (
                dict(user_meta.get("decision_meta"))
                if isinstance(user_meta.get("decision_meta"), dict)
                else {}
            )
            user_meta["decision_meta"] = {**existing, **decision_meta}
            user_message.message_metadata = user_meta
        if bot_response is not None:
            bot_meta = dict(bot_response.message_metadata or {})
            existing = (
                dict(bot_meta.get("decision_meta"))
                if isinstance(bot_meta.get("decision_meta"), dict)
                else {}
            )
            bot_meta["decision_meta"] = {**existing, **decision_meta}
            bot_response.message_metadata = bot_meta

    def _derive_contract_action(
        self,
        *,
        decision: PolicyDecision,
        execution: RuntimeExecutionResult,
        turn_result: Any,
    ) -> str:
        dialog_state = turn_result.dialog_state
        current_goal = (
            dialog_state.meta.get("current_goal")
            if isinstance(dialog_state.meta, dict)
            else None
        )
        expected_reply_type = dialog_state.projections.expected_reply_type
        if (
            execution.tool_action == "calendar.book_slot"
            and execution.tool_decision == "ok"
            and isinstance(execution.meta, dict)
            and execution.meta.get("appointment_id")
        ):
            return "booking_confirm"
        if decision.outcome == "COLLECT" and current_goal == "booking" and expected_reply_type:
            return "booking_prompt"
        return decision.action

    @staticmethod
    def _derive_contract_source(decision: PolicyDecision) -> str:
        if isinstance(decision.source, str) and decision.source.strip():
            source = decision.source.strip()
            if source == "policy_core" or source == "answer_interpreter" or source.startswith(
                "turn_planner"
            ):
                return "llm_policy_core"
            return source
        return _RUNTIME_ENTRYPOINT_NAME

    def _persist_user_message(
        self,
        db: Session,
        *,
        conversation: Conversation,
        client_id: UUID,
        payload: WebhookRequest,
        preflight: dict[str, Any],
        now: datetime,
    ) -> Message | None:
        metadata = payload.body.metadata
        message_id = getattr(metadata, "messageId", None)
        if message_id:
            existing = self._find_message_by_message_id(db, client_id=client_id, message_id=message_id)
            if existing is not None:
                return existing
        message = save_message(
            db,
            conversation.id,
            client_id,
            "user",
            preflight.get("message_text") or payload.body.message or "",
            message_metadata={
                "message_id": message_id,
                "messageId": message_id,
                "remote_jid": preflight.get("remote_jid"),
                "instance_id": getattr(metadata, "instanceId", None),
                "instanceId": getattr(metadata, "instanceId", None),
                "tenant_context": preflight.get("tenant_context"),
                "received_at": now.isoformat(),
                "source": _RUNTIME_ENTRYPOINT_NAME,
            },
        )
        return message

    def _find_message_by_message_id(
        self,
        db: Session,
        *,
        client_id: UUID,
        message_id: str,
    ) -> Message | None:
        return (
            db.query(Message)
            .filter(
                Message.client_id == client_id,
                or_(
                    Message.message_metadata["message_id"].astext == message_id,
                    Message.message_metadata["messageId"].astext == message_id,
                ),
            )
            .order_by(Message.created_at.desc())
            .first()
        )

    def _build_memory_summary(self, db: Session, conversation: Conversation) -> str | None:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(6)
            .all()
        )
        if not messages:
            return None
        recent = list(reversed(messages))
        parts: list[str] = []
        for message in recent:
            role = "user" if message.role == "user" else "assistant"
            content = (message.content or "").strip()
            if not content:
                continue
            parts.append(f"{role}: {content}")
        summary = "\n".join(parts).strip()
        return summary or None

    def _should_skip_send(self, prepared: PreparedConversation, metadata: Any) -> bool:
        if prepared.source in _NO_SEND_SOURCES:
            return True
        if metadata and getattr(metadata, "simulation_mode", None):
            return True
        return False


_RUNTIME = ConsultantRuntime()


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
    return await _RUNTIME.handle_webhook_payload(
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
