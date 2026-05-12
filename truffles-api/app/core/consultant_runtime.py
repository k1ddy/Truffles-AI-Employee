from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.core.binding_plan import BindingPlanV1
from app.core.boundary_validator import BoundaryOverride, BoundaryValidator
from app.core.dialog_state_service import DialogState, DialogStateService
from app.core.response_realizer import ReplyEnvelope, ResponseRealizer
from app.core.runtime_trace_contract import build_runtime_trace_contract
from app.core.turn_executor import RuntimeExecutionResult, TurnExecutor
from app.core.turn_planner import PlannerBoundarySignal, PolicyDecision, TurnPlanner
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
    _update_message_decision_metadata,
)
from app.schemas.outbox_payload import validate_outbox_payload
from app.schemas.webhook import WebhookRequest, WebhookResponse
from app.services.booking_transition_owner import PHONE_SOURCE_REMOTE_JID, PHONE_SOURCE_USER_PROFILE
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
from app.services.outbox_service import build_inbound_message_id, enqueue_outbox_message
from app.services.state_machine import ConversationState
from app.services.state_service import apply_simulation_context, transition_state

logger = get_logger("consultant_runtime")

_RUNTIME_ENTRYPOINT_NAME = "consultant_runtime"
_RUNTIME_TRACE_KEY = "decision_trace"
_TURN_TRACE_REFRESH_STAGES = frozenset(
    {
        "policy_core",
        "pending_question_interaction",
        "question_contract",
        _RUNTIME_ENTRYPOINT_NAME,
    }
)
_RUNTIME_ALLOWED_OUTCOMES = {"FACT", "COLLECT", "HANDOFF"}
_NO_SEND_SOURCES = {"message_api", "console_simulation", "simulation"}
_PROTECTED_RUNTIME_DECISION_META_FIELDS = frozenset(
    {
        "source",
        "runtime_entrypoint",
        "semantic_runtime_path",
        "action",
        "intent",
        "outcome",
        "tool_action",
        "tool_decision",
        "interaction_owner",
        "decision_trace",
        "reason_code",
        "earliest_failed_stage",
        "root_reason_code",
        "control_label",
        "expected_reply_type",
        "expected_reply_reason",
        "pending_question_act",
        "pending_question_contract",
        "question_contract",
        "pending_question_target",
        "active_question_relation",
        "semantic_contract",
        "semantic_frame",
        "semantic_state_before",
        "semantic_state_after",
        "source_detail",
        "policy_core_trace",
        "runtime_trace_contract",
    }
)


@dataclass(frozen=True)
class LoadedRuntimeState:
    context: dict[str, Any]
    dialog_state: DialogState
    booking_state: dict[str, Any]


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
    def __init__(self, *, semantic_runtime_path: str = "consultant_core_v2") -> None:
        self.planner = TurnPlanner()
        self.boundary = BoundaryValidator()
        self.dialog_state = DialogStateService()
        self.executor = TurnExecutor()
        self.realizer = ResponseRealizer()
        self.semantic_runtime_path = semantic_runtime_path

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
            if enqueue_only and not skip_persist:
                return self._enqueue_inbound_for_outbox(
                    db,
                    payload=payload,
                    prepared=prepared,
                )
            runtime_state = self._load_runtime_state(
                prepared.conversation,
                state_hint=(payload.body.message or ""),
            )
            control_response, runtime_state, control_bot_response = self._handle_control_turn(
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
                self._raise_delivery_failure_after_commit(
                    skip_persist=skip_persist,
                    bot_response=control_bot_response,
                )
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
            if isinstance(decision, PolicyDecision):
                decision.meta.setdefault("semantic_runtime_path", self.semantic_runtime_path)
                decision.meta.setdefault("client_id", prepared.client.id)
                decision.meta.setdefault("conversation_id", prepared.conversation.id)
                if outbox_ids:
                    decision.meta.setdefault("outbox_ids", list(outbox_ids))
                if batch_messages:
                    decision.meta.setdefault("batch_messages", list(batch_messages))
                if outbox_created_at is not None:
                    decision.meta.setdefault("outbox_created_at", outbox_created_at.isoformat())

            # Policy-Core v3 shadow-run (DL-2026-05-11-020). Off by default;
            # gated by settings.policy_core_v3_enabled AND env wiring. Fire-
            # and-forget; never affects the customer reply.
            if settings.policy_core_v3_enabled:
                try:
                    from app.policy_core_v3_shadow_hook import (
                        dispatch_fire_and_forget as _v3_shadow_dispatch,
                    )

                    _v3_shadow_dispatch(
                        tenant_id=str(prepared.client.id),
                        conversation_id=str(prepared.conversation.id),
                        current_message=payload.body.message or "",
                        legacy_decision=decision,
                    )
                except Exception:  # pragma: no cover - rule §1: shadow never affects hot path
                    pass

            planner_boundary_artifact = self._build_planner_boundary_artifact(
                decision=decision,
                boundary_override=boundary_override,
            )
            if planner_boundary_artifact is not None:
                self._write_planner_boundary_state(
                    prepared=prepared,
                    runtime_state=runtime_state,
                    planner_boundary_artifact=planner_boundary_artifact,
                    boundary_override=boundary_override,
                    now=now,
                )
                if self._should_activate_handoff(
                    decision=decision,
                    boundary_override=boundary_override,
                ):
                    self._activate_handoff(
                        db,
                        prepared=prepared,
                        decision=decision,
                        boundary_override=boundary_override,
                        user_message_text=payload.body.message or "",
                    )
                else:
                    self._resume_bot_if_needed(db, prepared=prepared)

                reply = planner_boundary_artifact.turn_result.reply
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
                    runtime_state_before=runtime_state,
                    decision=decision,
                    execution=self._build_boundary_execution_result(
                        boundary_override=boundary_override,
                        reply=reply,
                    ),
                    turn_result=planner_boundary_artifact.turn_result,
                    delivered=bool(bot_response),
                )
                db.commit()
                self._raise_delivery_failure_after_commit(
                    skip_persist=skip_persist,
                    bot_response=bot_response,
                )
                return WebhookResponse(
                    success=True,
                    message="Handled",
                    conversation_id=prepared.conversation.id,
                    bot_response=reply.text,
                )

            execution = self._execute_turn(
                db,
                prepared=prepared,
                decision=decision,
                payload=payload,
                runtime_state=runtime_state,
                now=now,
            )
            decision, boundary_override = self._apply_execution_boundary_override(
                decision=decision,
                execution=execution,
                boundary_override=boundary_override,
            )
            effective_decision = decision
            updated_context, dialog_state = self._write_runtime_state(
                prepared=prepared,
                runtime_state=runtime_state,
                decision=effective_decision,
                execution=execution,
                now=now,
            )
            prepared.conversation.context = updated_context

            if self._should_activate_handoff(
                decision=effective_decision,
                boundary_override=boundary_override,
                execution=execution,
            ):
                self._activate_handoff(
                    db,
                    prepared=prepared,
                    decision=effective_decision,
                    boundary_override=boundary_override,
                    user_message_text=payload.body.message or "",
                )
            else:
                self._resume_bot_if_needed(db, prepared=prepared)

            reply = self.realizer.realize(
                effective_decision,
                override=boundary_override,
                text=execution.text,
                channel=prepared.conversation.channel,
                reply_kind_override="handoff" if execution.request_handoff else None,
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
                runtime_state_before=runtime_state,
                decision=effective_decision,
                execution=execution,
                turn_result=turn_result,
                delivered=bool(bot_response),
            )
            db.commit()
            self._raise_delivery_failure_after_commit(
                skip_persist=skip_persist,
                bot_response=bot_response,
            )
            return WebhookResponse(
                success=True,
                message="Handled",
                conversation_id=prepared.conversation.id,
                bot_response=reply.text,
            )
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - runtime safety net
            if (
                skip_persist
                and isinstance(exc, RuntimeError)
                and str(exc).strip().startswith("ChatFlow delivery failed")
            ):
                raise
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

        if skip_persist:
            user_message = self._find_existing_user_message(
                db,
                client_id=client.id,
                conversation_id=conversation.id,
                message_id=getattr(metadata, "messageId", None) if metadata else None,
            )
        else:
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

    def _find_existing_user_message(
        self,
        db: Session,
        *,
        client_id: UUID,
        conversation_id: UUID,
        message_id: str | None,
    ) -> Message | None:
        if not message_id:
            return None
        token = message_id.strip()
        if not token:
            return None
        return (
            db.query(Message)
            .filter(
                Message.client_id == client_id,
                Message.conversation_id == conversation_id,
                Message.role == "user",
                or_(
                    Message.message_metadata["message_id"].astext == token,
                    Message.message_metadata["messageId"].astext == token,
                ),
            )
            .order_by(Message.created_at.desc())
            .first()
        )

    def _enqueue_inbound_for_outbox(
        self,
        db: Session,
        *,
        payload: WebhookRequest,
        prepared: PreparedConversation,
    ) -> WebhookResponse:
        metadata = payload.body.metadata
        message_id = getattr(metadata, "messageId", None) if metadata else None
        timestamp = getattr(metadata, "timestamp", None) if metadata else None
        inbound_message_id = build_inbound_message_id(
            message_id,
            prepared.remote_jid,
            timestamp,
            payload.body.message,
        )
        payload_json = payload.model_dump(exclude_none=True, mode="json")
        tenant_context = dict(payload_json.get("tenant_context") or {})
        tenant_context.update(
            {
                "client_id": str(prepared.client.id),
                "client_slug": prepared.client.name,
                "source": prepared.source or tenant_context.get("source") or "webhook",
            }
        )
        if prepared.branch_id:
            tenant_context["branch_id"] = str(prepared.branch_id)
        if prepared.instance_id:
            tenant_context["instance_id"] = prepared.instance_id
        payload_json["tenant_context"] = {
            key: value for key, value in tenant_context.items() if value is not None
        }
        payload_json["client_slug"] = prepared.client.name

        validated_payload, payload_error = validate_outbox_payload(
            payload_json,
            expected_client_slug=prepared.client.name,
        )
        if payload_error:
            _record_decision_trace(
                prepared.conversation,
                {
                    "stage": "outbox_payload_guard",
                    "decision": "reject",
                    "reason": payload_error,
                    "state": prepared.conversation.state,
                },
            )
            if prepared.user_message is not None:
                _update_message_decision_metadata(
                    prepared.user_message,
                    {
                        "action_error": "outbox_payload_invalid",
                        "outbox_payload_error": payload_error,
                    },
                )
            db.commit()
            return WebhookResponse(
                success=False,
                message="Invalid outbox payload",
                conversation_id=prepared.conversation.id,
            )

        outbox_payload = validated_payload.model_dump(exclude_none=True, mode="json")
        enqueued = enqueue_outbox_message(
            db,
            client_id=prepared.client.id,
            conversation_id=prepared.conversation.id,
            branch_id=prepared.branch_id,
            inbound_message_id=inbound_message_id,
            payload_json=outbox_payload,
        )
        _record_decision_trace(
            prepared.conversation,
            {
                "stage": "outbox",
                "decision": "enqueue_only",
                "reason": "enqueued" if enqueued else "duplicate",
                "state": prepared.conversation.state,
            },
        )
        if prepared.user_message is not None:
            _update_message_decision_metadata(
                prepared.user_message,
                {
                    "outbox_enqueue": "enqueued" if enqueued else "duplicate",
                    "outbox_inbound_message_id": inbound_message_id,
                },
            )
        db.commit()
        return WebhookResponse(
            success=True,
            message="Accepted",
            conversation_id=prepared.conversation.id,
            bot_response=None,
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
        return LoadedRuntimeState(
            context=context,
            dialog_state=payload["dialog_state"],
            booking_state=booking_state,
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
    ) -> tuple[WebhookResponse | None, LoadedRuntimeState, Message | None]:
        message_text = payload.body.message
        if not _should_reset_session_memory(message_text):
            return None, runtime_state, None

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
            return None, runtime_state, None

        reply = ReplyEnvelope(
            channel=prepared.conversation.channel or "whatsapp",
            reply_kind="system",
            text="Ок, давайте новую тему. Чем могу помочь?",
            meta={"outcome": "FACT", "control_action": "session_reset"},
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
            "control_action": "session_reset",
            "control_reason": "explicit_reset",
            "control_source": "session_memory",
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
            bot_response,
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
    ) -> tuple[PolicyDecision | None, BoundaryOverride | None]:
        def _planner_override_meta(
            *,
            reason_code: str,
            control_label: str,
            meta: dict[str, Any] | None = None,
            interaction_owner: str | None = None,
            interaction_target: str | None = None,
            interaction_relation: str | None = None,
            handoff_activation_requested: bool = True,
        ) -> dict[str, Any]:
            override_meta = {
                "degrade_stage": "planner",
                "planner_boundary_signal": True,
                "control_label": control_label,
                "handoff_activation_requested": handoff_activation_requested,
                "earliest_failed_stage": "planner",
                "root_reason_code": reason_code,
            }
            if interaction_owner:
                override_meta["interaction_owner"] = interaction_owner
            if interaction_target:
                override_meta["interaction_target"] = interaction_target
            if interaction_relation:
                override_meta["interaction_relation"] = interaction_relation
            if isinstance(meta, dict) and meta:
                override_meta.update(meta)
            return override_meta

        if prepared.conversation.state == ConversationState.MANAGER_ACTIVE.value:
            signal = self.planner.build_controlled_degrade_signal(
                reason_code="manager_active",
                control_label="manager_active",
                interaction_owner="pending_gate",
                public_message="Менеджер уже подключился к диалогу.",
                trace_message="manager_active_gate",
                meta={"handoff_activation_requested": False},
            )
            signal_meta = dict(signal.meta)
            signal_meta.setdefault("planner_boundary_signal", True)
            signal_meta.setdefault("control_label", signal.control_label)
            signal_meta.setdefault("interaction_owner", signal.interaction_owner)
            if signal.interaction_target:
                signal_meta.setdefault("interaction_target", signal.interaction_target)
            if signal.interaction_relation:
                signal_meta.setdefault("interaction_relation", signal.interaction_relation)
            return None, self.boundary.build_degrade_override(
                reason_code=signal.reason_code,
                public_message=signal.public_message
                or "Передаю диалог менеджеру, чтобы не потерять ваш запрос.",
                trace_message=signal.trace_message or signal.reason_code,
                meta=_planner_override_meta(
                    reason_code=signal.reason_code,
                    control_label=signal.control_label,
                    meta=signal_meta,
                    interaction_owner=signal.interaction_owner,
                    interaction_target=signal.interaction_target,
                    interaction_relation=signal.interaction_relation,
                    handoff_activation_requested=bool(
                        signal_meta.pop("handoff_activation_requested", True)
                    ),
                ),
            )

        recent_summary = self._build_memory_summary(db, prepared.conversation)
        memory_profile = self._build_policy_core_memory_profile(runtime_state)
        plan_result = self.planner.plan(
            message_text=payload.body.message,
            client_slug=payload.client_slug,
            booking_state=dict(runtime_state.booking_state or {}),
            memory_summary=recent_summary,
            memory_profile=memory_profile,
        )
        if isinstance(plan_result, PolicyDecision):
            decision = plan_result
            boundary_signal = None
        else:
            decision = plan_result.decision
            boundary_signal = plan_result.boundary_signal
            if isinstance(plan_result.boundary_signal, PlannerBoundarySignal):
                boundary_signal = plan_result.boundary_signal
        override = None
        if isinstance(boundary_signal, PlannerBoundarySignal):
            signal = boundary_signal
            signal_meta = dict(signal.meta)
            signal_meta.setdefault("planner_boundary_signal", True)
            signal_meta.setdefault("control_label", signal.control_label)
            signal_meta.setdefault("interaction_owner", signal.interaction_owner)
            if signal.interaction_target:
                signal_meta.setdefault("interaction_target", signal.interaction_target)
            if signal.interaction_relation:
                signal_meta.setdefault("interaction_relation", signal.interaction_relation)
            if signal.decision == "block":
                return decision, self.boundary.build_block_override(
                    reason_code=signal.reason_code,
                    trace_message=signal.trace_message or signal.reason_code,
                    replan_hints=["preserve preflight block contract"],
                    public_message=signal.public_message or "",
                    meta=signal_meta,
                )
            return decision, self.boundary.build_degrade_override(
                reason_code=signal.reason_code,
                public_message=signal.public_message
                or "Передаю диалог менеджеру, чтобы не потерять ваш запрос.",
                trace_message=signal.trace_message or signal.reason_code,
                meta=_planner_override_meta(
                    reason_code=signal.reason_code,
                    control_label=signal.control_label,
                    meta=signal_meta,
                    interaction_owner=signal.interaction_owner,
                    interaction_target=signal.interaction_target,
                    interaction_relation=signal.interaction_relation,
                    handoff_activation_requested=bool(
                        signal_meta.pop("handoff_activation_requested", True)
                    ),
                ),
            )
        if decision is None:
            raise ValueError("planner_decision_missing")
        missing_owner_guard = self.planner.detect_missing_semantic_owner(decision)
        if missing_owner_guard:
            override = self.boundary.build_degrade_override(
                reason_code="planner:missing_semantic_owner",
                public_message="Передаю диалог менеджеру, чтобы не потерять ваш запрос.",
                trace_message="missing_semantic_owner_guard_failed",
                meta={
                    **_planner_override_meta(
                        reason_code="planner:missing_semantic_owner",
                        control_label="planner_missing_semantic_owner",
                    ),
                    "missing_semantic_owner_guard": missing_owner_guard,
                },
            )
            return decision, override
        missing_binding_plan_guard = self.planner.detect_missing_binding_plan(decision)
        if missing_binding_plan_guard:
            override = self.boundary.build_degrade_override(
                reason_code="planner:missing_binding_plan",
                public_message="Передаю диалог менеджеру, чтобы не потерять ваш запрос.",
                trace_message="missing_binding_plan_guard_failed",
                meta={
                    **_planner_override_meta(
                        reason_code="planner:missing_binding_plan",
                        control_label="planner_missing_binding_plan",
                    ),
                    "missing_binding_plan_guard": missing_binding_plan_guard,
                },
            )
            return decision, override
        if decision.outcome not in _RUNTIME_ALLOWED_OUTCOMES:
            override = self.boundary.build_degrade_override(
                reason_code="planner:invalid_outcome",
                public_message="Передаю диалог менеджеру, чтобы не потерять ваш запрос.",
                trace_message="planner_invalid_outcome_guard_failed",
                meta=_planner_override_meta(
                    reason_code="planner:invalid_outcome",
                    control_label="planner_invalid_outcome",
                ),
            )
            return decision, override
        mutation_guard = self.planner.detect_semantic_mutation(decision)
        if mutation_guard:
            override = self.boundary.build_degrade_override(
                reason_code="planner:semantic_decision_post_owner_mutation",
                public_message="Передаю диалог менеджеру, чтобы не потерять ваш запрос.",
                trace_message="semantic_decision_guard_failed",
                meta={
                    **_planner_override_meta(
                        reason_code="planner:semantic_decision_post_owner_mutation",
                        control_label="planner_semantic_decision_guard",
                    ),
                    "semantic_mutation_guard": mutation_guard,
                },
            )
            return decision, override
        return decision, override

    def _build_planner_boundary_artifact(
        self,
        *,
        decision: PolicyDecision | None,
        boundary_override: BoundaryOverride | None,
    ):
        if boundary_override is None:
            return None
        override_meta = boundary_override.meta if isinstance(boundary_override.meta, dict) else {}
        if not (
            override_meta.get("planner_boundary_signal") is True
            or override_meta.get("degrade_stage") == "planner"
        ):
            return None
        control_label = override_meta.get("control_label")
        interaction_owner = (
            decision.interaction.owner
            if isinstance(decision, PolicyDecision)
            else override_meta.get("interaction_owner")
        )
        interaction_target = (
            decision.interaction.target
            if isinstance(decision, PolicyDecision)
            else override_meta.get("interaction_target")
        )
        interaction_relation = (
            decision.interaction.relation
            if isinstance(decision, PolicyDecision)
            else override_meta.get("interaction_relation")
        )
        artifact_meta = (
            {"control_label": control_label}
            if isinstance(control_label, str) and control_label.strip()
            else None
        )
        if boundary_override.decision == "block":
            dialog_state = self.dialog_state.build_blocked_state(
                reason_code=boundary_override.reason_code,
                interaction_owner=interaction_owner or "planner_boundary_block",
                interaction_target=interaction_target,
                interaction_relation=interaction_relation,
            )
            return self.executor.build_block_boundary_artifact(
                decision=decision,
                dialog_state=dialog_state,
                boundary_override=boundary_override,
                tool_action="noop",
                text=boundary_override.public_message or "",
                intent=str(control_label or boundary_override.reason_code),
                meta=artifact_meta,
            )
        dialog_state = self.dialog_state.build_degraded_state(
            reason_code=boundary_override.reason_code,
            interaction_owner=interaction_owner or "planner_boundary_degrade",
            interaction_target=interaction_target,
            interaction_relation=interaction_relation,
        )
        return self.executor.build_degrade_boundary_artifact(
            decision=decision,
            dialog_state=dialog_state,
            boundary_override=boundary_override,
            text=boundary_override.public_message or "",
            transport_status="skipped",
            transport_reason=boundary_override.reason_code,
            tool_action="handoff",
            tool_decision="planner_boundary_override",
            intent=str(control_label or boundary_override.reason_code),
            meta=artifact_meta,
        )

    @staticmethod
    def _build_boundary_execution_result(
        *,
        boundary_override: BoundaryOverride,
        reply: ReplyEnvelope,
    ) -> RuntimeExecutionResult:
        tool_action = "handoff" if boundary_override.decision == "degrade" else "noop"
        tool_decision = (
            "planner_boundary_override"
            if boundary_override.decision == "degrade"
            else "planner_block_override"
        )
        execution_meta = {
            "reason_code": boundary_override.reason_code,
        }
        override_meta = boundary_override.meta if isinstance(boundary_override.meta, dict) else {}
        for field_name in (
            "earliest_failed_stage",
            "root_reason_code",
            "control_label",
        ):
            value = override_meta.get(field_name)
            if isinstance(value, str) and value.strip():
                execution_meta[field_name] = value
        return RuntimeExecutionResult(
            text=reply.text,
            tool_action=tool_action,
            tool_decision=tool_decision,
            meta=execution_meta,
            request_handoff=bool(override_meta.get("handoff_activation_requested")),
        )

    def _build_policy_core_memory_profile(
        self,
        runtime_state: LoadedRuntimeState,
    ) -> dict[str, Any]:
        profile: dict[str, Any] = {}
        dialog_state = runtime_state.dialog_state
        pending_contract = deepcopy(
            self.dialog_state.project_pending_question_contract(
                dialog_state.pending_question_contract,
            )
            or {}
        )
        active_goal = None
        if isinstance(dialog_state.meta, dict):
            active_goal = self.dialog_state._canonical_current_goal_token(
                dialog_state.meta.get("current_goal")
            )
        if active_goal is None and self.dialog_state._pending_contract_implies_booking_followup_goal(
            pending_contract,
            runtime_state.booking_state,
        ):
            active_goal = "booking"
        if isinstance(active_goal, str) and active_goal.strip():
            profile["active_goal"] = active_goal.strip()

        slot_state: dict[str, str] = {}
        explicit_slot_state = (
            dict(dialog_state.meta.get("slot_state"))
            if isinstance(dialog_state.meta, dict)
            and isinstance(dialog_state.meta.get("slot_state"), dict)
            else {}
        )
        for field_name, value in explicit_slot_state.items():
            if field_name in {"service", "datetime", "name", "phone", "media"} and isinstance(value, str) and value.strip():
                slot_state[field_name] = value.strip()
        if slot_state:
            profile["slot_state"] = slot_state

        semantic_contract = (
            deepcopy(dialog_state.meta.get("semantic_contract"))
            if isinstance(dialog_state.meta, dict)
            and isinstance(dialog_state.meta.get("semantic_contract"), dict)
            else {}
        )
        if semantic_contract:
            profile["semantic_contract"] = semantic_contract

        if pending_contract:
            profile["pending_question_contract"] = pending_contract
            resume_pending_contract = self.dialog_state.project_interrupt_resume_pending_question_contract(
                pending_contract,
                current_goal=active_goal,
                booking_payload=runtime_state.booking_state,
                semantic_contract=semantic_contract,
            )
            if resume_pending_contract:
                profile["resume_pending_question_contract"] = resume_pending_contract

        return profile

    def _project_runtime_semantic_frame(
        self,
        dialog_state: DialogState,
        *,
        booking_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.dialog_state.project_runtime_semantic_frame(
            dialog_state,
            booking_payload=booking_state,
        ) or {}

    def _execution_semantic_enrichment(
        self,
        execution: RuntimeExecutionResult | None,
    ) -> dict[str, Any]:
        execution_meta = getattr(execution, "meta", None)
        if not isinstance(execution_meta, dict):
            return {}
        enrichment = execution_meta.get("semantic_enrichment")
        if isinstance(enrichment, dict) and enrichment:
            return dict(enrichment)
        semantic_contract = execution_meta.get("semantic_contract")
        if not isinstance(semantic_contract, dict):
            return {}
        enrichment_payload: dict[str, Any] = {}
        entity_refs = self.dialog_state._normalize_semantic_entity_refs(
            semantic_contract.get("entity_refs")
        )
        if entity_refs:
            enrichment_payload["entity_refs"] = entity_refs
        referents = self.dialog_state._normalize_semantic_referents(
            semantic_contract.get("referents")
        )
        if referents:
            enrichment_payload["referents"] = referents
        grounding_provenance = self.dialog_state._normalize_grounding_provenance(
            semantic_contract.get("grounding_provenance")
        )
        if grounding_provenance:
            enrichment_payload["grounding_provenance"] = grounding_provenance
        return enrichment_payload

    @staticmethod
    def _has_canonical_semantic_owner(
        decision: PolicyDecision | None,
    ) -> bool:
        return isinstance(decision, PolicyDecision) and getattr(decision, "semantic_decision", None) is not None

    def _semantic_contract_enrichment(
        self,
        semantic_contract: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not isinstance(semantic_contract, dict):
            return {}
        enrichment: dict[str, Any] = {}
        entity_refs = self.dialog_state._normalize_semantic_entity_refs(
            semantic_contract.get("entity_refs")
        )
        if entity_refs:
            enrichment["entity_refs"] = entity_refs
        referents = self.dialog_state._normalize_semantic_referents(
            semantic_contract.get("referents")
        )
        if referents:
            enrichment["referents"] = referents
        grounding_provenance = self.dialog_state._normalize_grounding_provenance(
            semantic_contract.get("grounding_provenance")
        )
        if grounding_provenance:
            enrichment["grounding_provenance"] = grounding_provenance
        return enrichment

    def _merge_semantic_enrichment(
        self,
        contract: dict[str, Any] | None,
        enrichment: dict[str, Any] | None,
    ) -> dict[str, Any]:
        base = dict(contract) if isinstance(contract, dict) else {}
        if not isinstance(enrichment, dict) or not enrichment:
            return base
        if not base:
            base = {"contract_version": "semantic_contract.v1"}

        grounding_provenance = self.dialog_state._normalize_grounding_provenance(
            enrichment.get("grounding_provenance")
        )
        if grounding_provenance:
            base["grounding_provenance"] = dict(grounding_provenance)

        merged_entity_refs = self.dialog_state._normalize_semantic_entity_refs(
            base.get("entity_refs")
        )
        merged_entity_refs.extend(
            self.dialog_state._normalize_semantic_entity_refs(enrichment.get("entity_refs"))
        )
        merged_entity_refs = self.dialog_state._normalize_semantic_entity_refs(merged_entity_refs)
        if merged_entity_refs:
            base["entity_refs"] = merged_entity_refs
        else:
            base.pop("entity_refs", None)

        merged_referents = self.dialog_state._normalize_semantic_referents(
            base.get("referents")
        )
        incoming_referents = self.dialog_state._normalize_semantic_referents(
            enrichment.get("referents")
        )
        for referent_key, referent_payload in incoming_referents.items():
            current_referent = merged_referents.get(referent_key)
            if isinstance(current_referent, dict):
                current_value = self.dialog_state._normalize_projection_token(
                    current_referent.get("value")
                )
                incoming_value = self.dialog_state._normalize_projection_token(
                    referent_payload.get("value")
                )
                if (
                    current_value
                    and incoming_value
                    and current_value.casefold() != incoming_value.casefold()
                ):
                    continue
                merged = dict(current_referent)
                merged.update(referent_payload)
                merged_referents[referent_key] = merged
                continue
            merged_referents[referent_key] = dict(referent_payload)
        if merged_referents:
            base["referents"] = merged_referents
        else:
            base.pop("referents", None)
        return base

    def _project_runtime_semantic_contract(
        self,
        dialog_state: DialogState,
        *,
        booking_state: dict[str, Any] | None = None,
        decision: PolicyDecision | None = None,
        execution: RuntimeExecutionResult | None = None,
    ) -> dict[str, Any]:
        semantic_contract = self.dialog_state.project_runtime_semantic_contract(
            dialog_state,
            booking_payload=booking_state,
        )
        owner_semantic_contract = (
            self.planner.canonical_semantic_contract(decision)
            if isinstance(decision, PolicyDecision)
            else None
        )
        if self._has_canonical_semantic_owner(decision):
            contract = (
                dict(owner_semantic_contract)
                if isinstance(owner_semantic_contract, dict) and owner_semantic_contract
                else {}
            )
            contract = self._merge_semantic_enrichment(
                contract,
                self._execution_semantic_enrichment(execution),
            )
            return contract
        contract = dict(semantic_contract) if isinstance(semantic_contract, dict) else {}
        if isinstance(owner_semantic_contract, dict) and owner_semantic_contract:
            if not contract:
                contract = dict(owner_semantic_contract)
            else:
                for key in (
                    "subject_kind",
                    "capability",
                    "temporal_scope",
                    "resolution_mode",
                    "pending_question_act",
                    "pending_question_target",
                    "active_question_relation",
                    "alternate_datetime",
                    "requested_effect",
                    "tool_action_hint",
                    "needs_human",
                    "grounding_provenance",
                ):
                    if key not in contract and key in owner_semantic_contract:
                        contract[key] = owner_semantic_contract[key]
                if "entity_refs" not in contract and isinstance(owner_semantic_contract.get("entity_refs"), list):
                    contract["entity_refs"] = list(owner_semantic_contract["entity_refs"])
                if "referents" not in contract and isinstance(owner_semantic_contract.get("referents"), dict):
                    contract["referents"] = dict(owner_semantic_contract["referents"])
        execution_semantic_enrichment = self._execution_semantic_enrichment(execution)
        if execution_semantic_enrichment:
            contract = self._merge_semantic_enrichment(contract, execution_semantic_enrichment)
            return contract
        execution_meta = getattr(execution, "meta", None)
        execution_semantic_contract = (
            dict(execution_meta.get("semantic_contract"))
            if isinstance(execution_meta, dict)
            and isinstance(execution_meta.get("semantic_contract"), dict)
            else {}
        )
        if not execution_semantic_contract:
            return contract
        if not contract:
            return execution_semantic_contract
        for key in (
            "subject_kind",
            "capability",
            "temporal_scope",
            "resolution_mode",
            "pending_question_act",
            "pending_question_target",
            "active_question_relation",
            "requested_effect",
            "tool_action_hint",
            "needs_human",
            "grounding_provenance",
        ):
            if key not in contract and key in execution_semantic_contract:
                contract[key] = execution_semantic_contract[key]
        if "entity_refs" not in contract and isinstance(execution_semantic_contract.get("entity_refs"), list):
            contract["entity_refs"] = list(execution_semantic_contract["entity_refs"])
        if "referents" not in contract and isinstance(execution_semantic_contract.get("referents"), dict):
            contract["referents"] = dict(execution_semantic_contract["referents"])
        return contract

    def _project_runtime_pending_question_contract(
        self,
        dialog_state: DialogState,
        *,
        booking_state: dict[str, Any] | None = None,
        decision: PolicyDecision | None = None,
    ) -> dict[str, Any]:
        runtime_pending_question_contract = self.dialog_state.project_runtime_pending_question_contract(
            dialog_state,
            booking_payload=booking_state,
        )
        owner_contract = self.dialog_state.project_pending_question_contract(
            (
                self.planner.canonical_pending_question_contract(decision)
                if isinstance(decision, PolicyDecision)
                else None
            ),
        )
        if self._has_canonical_semantic_owner(decision):
            return dict(owner_contract) if isinstance(owner_contract, dict) and owner_contract else {}
        if isinstance(runtime_pending_question_contract, dict) and runtime_pending_question_contract:
            return dict(runtime_pending_question_contract)
        return dict(owner_contract) if isinstance(owner_contract, dict) and owner_contract else {}

    @classmethod
    def _observer_execution_meta(
        cls,
        *,
        decision: PolicyDecision | None,
        execution: RuntimeExecutionResult,
    ) -> dict[str, Any]:
        execution_meta = getattr(execution, "meta", None)
        if not isinstance(execution_meta, dict):
            return {}
        payload = dict(execution_meta)
        if not cls._has_canonical_semantic_owner(decision):
            return payload
        for key in _PROTECTED_RUNTIME_DECISION_META_FIELDS:
            payload.pop(key, None)
        return payload

    @classmethod
    def _merge_runtime_decision_meta(
        cls,
        existing: Any,
        current: dict[str, Any],
    ) -> dict[str, Any]:
        merged = dict(existing) if isinstance(existing, dict) else {}
        for key in _PROTECTED_RUNTIME_DECISION_META_FIELDS:
            if key not in current:
                merged.pop(key, None)
        merged.update(current)
        return merged

    @staticmethod
    def _fresh_turn_trace_seed(existing_trace: Any) -> list[dict[str, Any]]:
        trace_items = []
        if isinstance(existing_trace, list):
            trace_items = [item for item in existing_trace if isinstance(item, dict)]
        elif isinstance(existing_trace, dict):
            trace_items = [existing_trace]
        if not trace_items:
            return []
        # Keep non-core guard/boundary entries, but replace prior turn core stages
        # with the current turn's canonical policy/question/runtime sequence.
        return [
            item
            for item in trace_items
            if str(item.get("stage") or "").strip() not in _TURN_TRACE_REFRESH_STAGES
        ]

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
        user_phone_source = PHONE_SOURCE_USER_PROFILE if user_phone else None
        if not user_phone and prepared.remote_jid:
            digits = "".join(ch for ch in prepared.remote_jid.split("@", 1)[0] if ch.isdigit())
            user_phone = digits or None
            if user_phone:
                user_phone_source = PHONE_SOURCE_REMOTE_JID
        return self.executor.execute(
            decision,
            db=db,
            message_text=payload.body.message,
            client_slug=payload.client_slug,
            branch_id=prepared.branch_id,
            booking_state=runtime_state.booking_state,
            user_name=prepared.user.name,
            user_phone=user_phone,
            user_phone_source=user_phone_source,
            now=now,
            conversation_id=prepared.conversation.id,
        )

    def _apply_execution_boundary_override(
        self,
        *,
        decision: PolicyDecision,
        execution: RuntimeExecutionResult,
        boundary_override: BoundaryOverride | None,
    ) -> tuple[PolicyDecision, BoundaryOverride | None]:
        return decision, boundary_override

    @staticmethod
    def _should_activate_handoff(
        *,
        decision: PolicyDecision | None,
        boundary_override: BoundaryOverride | None,
        execution: RuntimeExecutionResult | None = None,
    ) -> bool:
        if ConsultantRuntime._decision_requests_handoff(decision):
            return True
        if isinstance(execution, RuntimeExecutionResult) and execution.request_handoff:
            return True
        if boundary_override is None or boundary_override.decision != "degrade":
            return False
        override_meta = boundary_override.meta if isinstance(boundary_override.meta, dict) else {}
        if override_meta.get("handoff_activation_requested") is True:
            return True
        return boundary_override.reason_code == "executor:handoff_requested"

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
        if self._decision_collects(decision) and execution.tool_decision:
            execution_meta.setdefault("next_slot", execution.tool_decision)
        conversation = getattr(prepared, "conversation", None)
        conversation_id = None
        if conversation is not None and getattr(conversation, "id", None) is not None:
            conversation_id = str(conversation.id)
        updated_context, dialog_state, _booking_payload = self.dialog_state.write_runtime_payload(
            runtime_state.context,
            decision=decision,
            execution_meta=execution_meta,
            now=now,
            conversation_id=conversation_id,
            trace_id=get_trace_id(),
        )
        runtime_payload = (
            updated_context.get("consultant_runtime")
            if isinstance(updated_context.get("consultant_runtime"), dict)
            else None
        )
        if isinstance(runtime_payload, dict):
            runtime_payload["semantic_runtime_path"] = self.semantic_runtime_path
        return updated_context, dialog_state

    def _write_planner_boundary_state(
        self,
        *,
        prepared: PreparedConversation,
        runtime_state: LoadedRuntimeState,
        planner_boundary_artifact: Any,
        boundary_override: BoundaryOverride | None,
        now: datetime,
    ) -> dict[str, Any]:
        reason_code = (
            boundary_override.reason_code
            if isinstance(boundary_override, BoundaryOverride)
            else "planner_boundary"
        )
        updated_context = self.dialog_state.reset_runtime_continuity(
            runtime_state.context,
            now=now,
            reason=reason_code,
        )
        dialog_state = planner_boundary_artifact.turn_result.dialog_state
        runtime_payload = {
            "schema_version": "consultant_runtime.v1",
            "dialog_state": dialog_state.model_dump(mode="json", exclude_none=True),
            "updated_at": now.isoformat(),
            "semantic_runtime_path": self.semantic_runtime_path,
            "boundary_state": {
                "reason_code": reason_code,
                "planner_boundary_signal": True,
            },
        }
        updated_context["consultant_runtime"] = runtime_payload
        prepared.conversation.context = updated_context
        return updated_context

    def _activate_handoff(
        self,
        db: Session,
        *,
        prepared: PreparedConversation,
        decision: PolicyDecision | None,
        boundary_override: BoundaryOverride | None = None,
        user_message_text: str,
    ) -> None:
        trigger_value = None
        if isinstance(decision, PolicyDecision):
            trigger_value = decision.intent
        elif boundary_override is not None:
            override_meta = boundary_override.meta if isinstance(boundary_override.meta, dict) else {}
            trigger_value = override_meta.get("control_label") or boundary_override.reason_code
        handover = get_active_handover(db, prepared.conversation.id)
        if handover is None:
            handover = create_handover(
                db,
                prepared.conversation,
                prepared.user,
                trigger_type="intent",
                trigger_value=trigger_value,
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

        if enqueue_only or self._should_skip_send(prepared, metadata):
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
                    transport_reason = str(result.error) if result.error else "delivery_failed"
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

    @staticmethod
    def _delivery_failure_reason(bot_response: Message | None) -> str | None:
        if bot_response is None:
            return None
        metadata = bot_response.message_metadata
        if not isinstance(metadata, dict):
            return None
        if metadata.get("transport_status") != "failed":
            return None
        reason = metadata.get("transport_reason") or "delivery_failed"
        return str(reason)

    def _raise_delivery_failure_after_commit(
        self,
        *,
        skip_persist: bool,
        bot_response: Message | None,
    ) -> None:
        if not skip_persist:
            return
        reason = self._delivery_failure_reason(bot_response)
        if reason:
            raise RuntimeError(f"ChatFlow delivery failed: {reason}")

    def _record_turn_trace(
        self,
        *,
        conversation: Conversation,
        user_message: Message | None,
        bot_response: Message | None,
        runtime_state_before: LoadedRuntimeState | None = None,
        decision: PolicyDecision | None,
        execution: RuntimeExecutionResult,
        turn_result: Any,
        delivered: bool,
    ) -> None:
        dialog_state = turn_result.dialog_state
        execution_meta = self._observer_execution_meta(
            decision=decision,
            execution=execution,
        )
        runtime_payload = self.dialog_state.load_runtime_payload(conversation.context or {})
        runtime_projection = runtime_payload.get("conversation_projection")
        runtime_turn_journal = runtime_payload.get("turn_journal")
        trace_id = get_trace_id()
        if not trace_id and runtime_turn_journal is not None:
            for journal_event in reversed(runtime_turn_journal.events):
                if isinstance(journal_event.trace_id, str) and journal_event.trace_id.strip():
                    trace_id = journal_event.trace_id.strip()
                    break
        semantic_frame_before = None
        if isinstance(runtime_state_before, LoadedRuntimeState):
            semantic_frame_before = self._project_runtime_semantic_frame(
                runtime_state_before.dialog_state,
                booking_state=runtime_state_before.booking_state,
            )
        semantic_frame_after = self._project_runtime_semantic_frame(
            dialog_state,
        ) or (
            self.dialog_state.project_semantic_frame(self.planner.canonical_semantic_frame(decision))
            if isinstance(decision, PolicyDecision)
            else None
        )
        contract_action = self._derive_contract_action(
            decision=decision,
            execution=execution,
            turn_result=turn_result,
        )
        contract_source = self._derive_contract_source(decision)
        pending_question_contract = self._project_runtime_pending_question_contract(
            dialog_state,
            decision=decision,
        )
        expected_reply_type = pending_question_contract.get("expected_reply_type")
        expected_reply_reason = pending_question_contract.get("reason")
        interaction_owner = (
            decision.interaction.owner
            if isinstance(decision, PolicyDecision)
            else getattr(dialog_state.interaction_state, "interaction_owner", None)
        )
        interaction_relation = (
            decision.interaction.relation
            if isinstance(decision, PolicyDecision)
            else getattr(dialog_state.interaction_state, "interaction_relation", None)
        )
        interaction_target = (
            decision.interaction.target
            if isinstance(decision, PolicyDecision)
            else getattr(dialog_state.interaction_state, "interaction_target", None)
        )
        turn_outcome = getattr(turn_result, "outcome", None)
        if turn_outcome is None and isinstance(decision, PolicyDecision):
            turn_outcome = decision.outcome
        if turn_outcome is None:
            boundary_override = getattr(turn_result, "boundary_override", None)
            turn_outcome = "HANDOFF" if getattr(boundary_override, "decision", None) == "degrade" else "FACT"
        trace_event = {
            "stage": _RUNTIME_ENTRYPOINT_NAME,
            "semantic_runtime_path": self.semantic_runtime_path,
            "decision": contract_action,
            "intent": (
                decision.intent
                if isinstance(decision, PolicyDecision)
                else (
                    (
                        turn_result.boundary_override.meta.get("control_label")
                        if getattr(turn_result, "boundary_override", None) is not None
                        and isinstance(turn_result.boundary_override.meta, dict)
                        else None
                    )
                    or (
                        turn_result.boundary_override.reason_code
                        if getattr(turn_result, "boundary_override", None) is not None
                        else None
                    )
                )
            ),
            "outcome": turn_outcome,
            "tool_action": execution.tool_action,
            "tool_decision": execution.tool_decision,
            "reply_kind": turn_result.reply.reply_kind,
            "interaction_owner": interaction_owner,
            "source": contract_source,
            "trace_id": trace_id,
            "delivered": delivered,
        }
        earliest_failed_stage = None
        root_reason_code = None
        reason_code = None
        observability = getattr(turn_result, "observability", None)
        if observability is not None:
            reason_code = getattr(observability, "reason_code", None)
        if not reason_code and isinstance(decision, PolicyDecision) and isinstance(decision.meta, dict):
            reason_code = decision.meta.get("reason_code")
        if not reason_code:
            reason_code = execution_meta.get("reason_code")
        override_meta = (
            dict(turn_result.boundary_override.meta)
            if getattr(turn_result, "boundary_override", None) is not None
            and isinstance(turn_result.boundary_override.meta, dict)
            else {}
        )
        if isinstance(decision, PolicyDecision) and isinstance(decision.meta, dict):
            earliest_failed_stage = decision.meta.get("earliest_failed_stage")
            root_reason_code = decision.meta.get("root_reason_code")
        if not earliest_failed_stage:
            earliest_failed_stage = execution_meta.get("earliest_failed_stage")
        if not root_reason_code:
            root_reason_code = execution_meta.get("root_reason_code")
        if not earliest_failed_stage:
            earliest_failed_stage = override_meta.get("earliest_failed_stage")
        if not root_reason_code:
            root_reason_code = override_meta.get("root_reason_code")
        if not root_reason_code:
            root_reason_code = reason_code
        if isinstance(reason_code, str) and reason_code.strip():
            trace_event["reason_code"] = reason_code.strip()
        if isinstance(earliest_failed_stage, str) and earliest_failed_stage.strip():
            trace_event["earliest_failed_stage"] = earliest_failed_stage.strip()
        if isinstance(root_reason_code, str) and root_reason_code.strip():
            trace_event["root_reason_code"] = root_reason_code.strip()
        control_label = None
        if isinstance(decision, PolicyDecision) and isinstance(decision.meta, dict):
            control_label = decision.meta.get("control_label")
        if not control_label:
            control_label = override_meta.get("control_label")
        if isinstance(control_label, str) and control_label.strip():
            trace_event["control_label"] = control_label.strip()
        if expected_reply_type:
            trace_event["expected_reply_type"] = expected_reply_type
        if expected_reply_reason:
            trace_event["expected_reply_reason"] = expected_reply_reason
        if pending_question_contract:
            trace_event["pending_question_contract"] = pending_question_contract
        pending_question_act = None
        pending_question_target = None
        active_question_relation = pending_question_contract.get(
            "active_question_relation"
        ) or interaction_relation
        question_contract_active = False
        if not self._has_canonical_semantic_owner(decision):
            pending_question_act = execution_meta.get("pending_question_act")
            pending_question_target = execution_meta.get("pending_question_target")
            question_contract_active = bool(execution_meta.get("question_contract"))
        if isinstance(decision, PolicyDecision) and isinstance(decision.meta, dict):
            pending_question_act = pending_question_act or decision.meta.get("pending_question_act")
            pending_question_target = pending_question_target or decision.meta.get(
                "pending_question_target"
            )
            question_contract_active = question_contract_active or bool(
                decision.meta.get("question_contract")
            )
        if not pending_question_act:
            pending_question_act = pending_question_contract.get("pending_question_act")
        if not pending_question_target:
            pending_question_target = pending_question_contract.get(
                "pending_question_target"
            ) or interaction_target
        if not question_contract_active and pending_question_contract:
            question_contract_active = self._decision_collects(decision) or bool(
                pending_question_act and expected_reply_type
            )
        if pending_question_target:
            trace_event["pending_question_target"] = pending_question_target
        if active_question_relation:
            trace_event["active_question_relation"] = active_question_relation
        semantic_contract = self._project_runtime_semantic_contract(
            dialog_state,
            decision=decision,
            execution=execution,
        )
        if semantic_contract:
            trace_event["semantic_contract"] = semantic_contract
        if semantic_frame_after:
            trace_event["semantic_frame"] = semantic_frame_after
        if semantic_frame_before:
            trace_event["semantic_state_before"] = semantic_frame_before
        if semantic_frame_after:
            trace_event["semantic_state_after"] = semantic_frame_after
        if isinstance(execution_meta.get("tool_execution_projection"), dict):
            trace_event["tool_execution_projection"] = dict(
                execution_meta["tool_execution_projection"]
            )
        runtime_trace_contract = build_runtime_trace_contract(
            trace_id=trace_event["trace_id"],
            runtime_entrypoint=_RUNTIME_ENTRYPOINT_NAME,
            semantic_runtime_path=self.semantic_runtime_path,
            decision=decision,
            boundary_override=getattr(turn_result, "boundary_override", None),
            dialog_state=dialog_state,
            contract_source=contract_source,
            contract_action=contract_action,
            reply_kind=turn_result.reply.reply_kind,
            delivered=delivered,
            execution_tool_action=execution.tool_action,
            execution_tool_decision=execution.tool_decision,
            reason_code=reason_code,
            earliest_failed_stage=earliest_failed_stage,
            root_reason_code=root_reason_code,
            projection=runtime_projection,
            turn_journal=runtime_turn_journal,
            pending_question_contract=pending_question_contract,
            semantic_contract=semantic_contract,
            semantic_state_before=semantic_frame_before,
            semantic_state_after=semantic_frame_after,
        )
        runtime_trace_contract_payload = runtime_trace_contract.model_dump(
            mode="json",
            exclude_none=True,
        )
        trace_event["runtime_trace_contract"] = runtime_trace_contract_payload
        context = dict(conversation.context or {})
        trace = self._fresh_turn_trace_seed(context.get(_RUNTIME_TRACE_KEY))
        policy_core_trace = (
            dict(decision.meta.get("policy_core_trace"))
            if isinstance(decision, PolicyDecision)
            and isinstance(decision.meta, dict)
            and isinstance(decision.meta.get("policy_core_trace"), dict)
            else None
        )
        if policy_core_trace is None and isinstance(override_meta.get("policy_core_trace"), dict):
            policy_core_trace = dict(override_meta["policy_core_trace"])
        if isinstance(policy_core_trace, dict):
            policy_core_entry = {
                "stage": "policy_core",
                "source": "llm_policy_core",
            }
            policy_core_entry.update(policy_core_trace)
            trace.append(policy_core_entry)
        if pending_question_act and expected_reply_type:
            interaction_entry = {
                "stage": "pending_question_interaction",
                "decision": pending_question_act,
                "state": getattr(conversation, "state", None),
                "source": contract_source,
                "pending_question_act": pending_question_act,
                "pending_question_target": pending_question_target or "time",
                "active_question_relation": active_question_relation or pending_question_act,
                "expected_reply_type": expected_reply_type,
            }
            if pending_question_contract:
                interaction_entry["pending_question_contract"] = pending_question_contract
            trace.append(interaction_entry)
        if question_contract_active and expected_reply_type:
            question_contract_entry = {
                "stage": "question_contract",
                "decision": pending_question_act or contract_action,
                "state": getattr(conversation, "state", None),
                "source": contract_source,
                "expected_reply_type": expected_reply_type,
                "reason": expected_reply_reason,
                "pending_question_act": pending_question_act,
                "pending_question_target": pending_question_target or "time",
            }
            if active_question_relation:
                question_contract_entry["active_question_relation"] = active_question_relation
            if pending_question_contract:
                question_contract_entry["pending_question_contract"] = pending_question_contract
            trace.append(question_contract_entry)
        trace.append(trace_event)
        context[_RUNTIME_TRACE_KEY] = trace[-20:]
        conversation.context = context

        decision_meta = {
            "source": contract_source,
            "runtime_entrypoint": _RUNTIME_ENTRYPOINT_NAME,
            "semantic_runtime_path": self.semantic_runtime_path,
            "action": contract_action,
            "intent": trace_event["intent"],
            "outcome": turn_outcome,
            "tool_action": execution.tool_action,
            "tool_decision": execution.tool_decision,
            "interaction_owner": interaction_owner,
            "decision_trace": trace_event,
        }
        if isinstance(reason_code, str) and reason_code.strip():
            decision_meta["reason_code"] = reason_code.strip()
        if isinstance(earliest_failed_stage, str) and earliest_failed_stage.strip():
            decision_meta["earliest_failed_stage"] = earliest_failed_stage.strip()
        if isinstance(root_reason_code, str) and root_reason_code.strip():
            decision_meta["root_reason_code"] = root_reason_code.strip()
        if isinstance(control_label, str) and control_label.strip():
            decision_meta["control_label"] = control_label.strip()
        if expected_reply_type:
            decision_meta["expected_reply_type"] = expected_reply_type
        if expected_reply_reason:
            decision_meta["expected_reply_reason"] = expected_reply_reason
        if pending_question_contract:
            decision_meta["pending_question_contract"] = pending_question_contract
        if question_contract_active:
            decision_meta["question_contract"] = True
        if pending_question_target:
            decision_meta["pending_question_target"] = pending_question_target
        if active_question_relation:
            decision_meta["active_question_relation"] = active_question_relation
        if semantic_contract:
            decision_meta["semantic_contract"] = semantic_contract
        if semantic_frame_after:
            decision_meta["semantic_frame"] = semantic_frame_after
        if semantic_frame_before:
            decision_meta["semantic_state_before"] = semantic_frame_before
        if semantic_frame_after:
            decision_meta["semantic_state_after"] = semantic_frame_after
        if isinstance(decision, PolicyDecision) and contract_source != decision.source:
            decision_meta["source_detail"] = decision.source
        if policy_core_trace:
            decision_meta["policy_core_trace"] = policy_core_trace
            boundary_normalization_used = policy_core_trace.get("boundary_normalization_used")
            if boundary_normalization_used is not None:
                decision_meta["boundary_normalization_used"] = bool(
                    boundary_normalization_used
                )
            boundary_normalization_events = policy_core_trace.get(
                "boundary_normalization_events"
            )
            if isinstance(boundary_normalization_events, list) and boundary_normalization_events:
                decision_meta["boundary_normalization_events"] = list(
                    boundary_normalization_events
                )
            override_reason_code = policy_core_trace.get("llm_policy_override_reason_code")
            if isinstance(override_reason_code, str) and override_reason_code.strip():
                decision_meta["llm_policy_override_reason_code"] = override_reason_code.strip()
            override_reason_codes = policy_core_trace.get("llm_policy_override_reason_codes")
            if isinstance(override_reason_codes, list) and override_reason_codes:
                decision_meta["llm_policy_override_reason_codes"] = list(
                    override_reason_codes
                )
            semantic_intent_overrides = policy_core_trace.get("semantic_intent_overrides")
            semantic_arbiter_audit = policy_core_trace.get("semantic_arbiter_audit")
            llm_policy_core_meta: dict[str, Any] = {}
            if isinstance(semantic_intent_overrides, list) and semantic_intent_overrides:
                llm_policy_core_meta["semantic_intent_overrides"] = list(
                    semantic_intent_overrides
                )
            if isinstance(semantic_arbiter_audit, dict) and semantic_arbiter_audit:
                llm_policy_core_meta["semantic_arbiter"] = {
                    "audit": dict(semantic_arbiter_audit)
                }
            if llm_policy_core_meta:
                decision_meta["llm_policy_core"] = llm_policy_core_meta
        if execution_meta:
            decision_meta.update(execution_meta)
        decision_meta["runtime_trace_contract"] = runtime_trace_contract_payload
        if getattr(turn_result, "trace", None) is not None and hasattr(turn_result.trace, "runtime_trace_contract"):
            turn_result.trace.runtime_trace_contract = runtime_trace_contract
        if user_message is not None:
            user_meta = dict(user_message.message_metadata or {})
            existing = (
                dict(user_meta.get("decision_meta"))
                if isinstance(user_meta.get("decision_meta"), dict)
                else {}
            )
            user_meta["decision_meta"] = self._merge_runtime_decision_meta(
                existing,
                decision_meta,
            )
            user_message.message_metadata = user_meta
        if bot_response is not None:
            bot_meta = dict(bot_response.message_metadata or {})
            existing = (
                dict(bot_meta.get("decision_meta"))
                if isinstance(bot_meta.get("decision_meta"), dict)
                else {}
            )
            bot_meta["decision_meta"] = self._merge_runtime_decision_meta(
                existing,
                decision_meta,
            )
            bot_response.message_metadata = bot_meta

    def _derive_contract_action(
        self,
        *,
        decision: PolicyDecision | None,
        execution: RuntimeExecutionResult,
        turn_result: Any,
    ) -> str:
        if (
            execution.tool_action == "calendar.book_slot"
            and execution.tool_decision == "ok"
            and isinstance(execution.meta, dict)
            and execution.meta.get("appointment_id")
        ):
            return "booking_confirm"
        if isinstance(decision, PolicyDecision):
            action = str(decision.action or "").strip()
            if action:
                # Keep canonical trace/meta aligned with the owner decision.
                # Booking-prompt presentation can be derived by observer layers.
                return action
        boundary_override = getattr(turn_result, "boundary_override", None)
        if boundary_override is not None and boundary_override.decision == "block":
            return "reject"
        if boundary_override is not None and boundary_override.decision == "degrade":
            return "handoff"
        return execution.tool_action or "boundary_override"

    @staticmethod
    def _binding_outcome_type(decision: PolicyDecision | None) -> str | None:
        binding_plan = getattr(decision, "binding_plan", None)
        if isinstance(binding_plan, BindingPlanV1):
            return binding_plan.binding_outcome_type
        return None

    @classmethod
    def _decision_requests_handoff(cls, decision: PolicyDecision | None) -> bool:
        return cls._binding_outcome_type(decision) in {"handoff", "degrade"}

    @classmethod
    def _decision_collects(cls, decision: PolicyDecision | None) -> bool:
        return cls._binding_outcome_type(decision) in {"workflow_start", "workflow_advance"}

    @staticmethod
    def _derive_contract_source(decision: PolicyDecision | None) -> str:
        if decision is None:
            return _RUNTIME_ENTRYPOINT_NAME
        if isinstance(decision.source, str) and decision.source.strip():
            source = decision.source.strip()
            if source == "policy_core" or source.startswith("turn_planner"):
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

    def _is_reset_boundary_message(self, message: Message) -> bool:
        metadata = message.message_metadata if isinstance(message.message_metadata, dict) else {}
        decision_meta = metadata.get("decision_meta") if isinstance(metadata, dict) else None
        if isinstance(decision_meta, dict):
            control_action = decision_meta.get("control_action")
            if isinstance(control_action, str) and control_action.strip() == "session_reset":
                return True
            session_memory_reset = decision_meta.get("session_memory_reset")
            if isinstance(session_memory_reset, str) and session_memory_reset.strip() == "explicit_reset":
                return True
        return _is_session_reset_only_message(message.content)

    def _trim_messages_after_last_reset(self, messages: list[Message]) -> list[Message]:
        last_reset_index: int | None = None
        for index, message in enumerate(messages):
            if self._is_reset_boundary_message(message):
                last_reset_index = index
        if last_reset_index is None:
            return messages
        return messages[last_reset_index + 1 :]

    def _build_memory_summary(self, db: Session, conversation: Conversation) -> str | None:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(24)
            .all()
        )
        if not messages:
            return None
        recent = self._trim_messages_after_last_reset(list(reversed(messages)))
        if len(recent) > 6:
            recent = recent[-6:]
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
    from app.core.consultant_core_v2 import handle_webhook_payload as handle_consultant_core_v2

    return await handle_consultant_core_v2(
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
