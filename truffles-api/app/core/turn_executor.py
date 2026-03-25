from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import Any, Literal, NamedTuple

from pydantic import BaseModel, ConfigDict, Field

from app.core.boundary_validator import BoundaryOverride, BoundaryValidator
from app.core.dialog_state_service import DialogState, DialogStateService
from app.core.response_realizer import ReplyEnvelope, ResponseRealizer
from app.core.turn_planner import DecisionOutcome, PolicyDecision, TurnPlanner
from app.schemas.turn_outcome import TurnOutcome, TurnOutcomeObservability

ToolStatus = Literal["ok", "degraded", "blocked", "skipped"]
TurnContractStatus = Literal["ok", "degraded", "blocked"]
OwnerCutoverAction = Literal["reply", "booking_prompt", "check_booking_prompt", "escalate", "smalltalk"]


class ToolOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    status: ToolStatus
    reason_code: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class TurnObservability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason_code: str | None = None
    decision_stage: str = "turn_executor"
    meta: dict[str, Any] = Field(default_factory=dict)


class TurnTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason_code: str | None = None
    stages: list[str] = Field(default_factory=list)


class TurnResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "turn_result.v1"
    outcome: DecisionOutcome
    contract_status: TurnContractStatus = "ok"
    policy_decision: PolicyDecision
    boundary_override: BoundaryOverride | None = None
    reply: ReplyEnvelope
    tool_outcomes: list[ToolOutcome] = Field(default_factory=list)
    dialog_state: DialogState
    observability: TurnObservability = Field(default_factory=TurnObservability)
    trace: TurnTrace = Field(default_factory=TurnTrace)


class RuntimeExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    tool_action: str
    tool_decision: str
    meta: dict[str, Any] = Field(default_factory=dict)
    clear_booking: bool = False
    request_handoff: bool = False


class BoundaryExecutionArtifact(NamedTuple):
    turn_result: TurnResult
    turn_outcome: TurnOutcome


@dataclass(frozen=True)
class BlockBoundaryRequest:
    reason_code: str
    action: str
    intent: str
    interaction_owner: str
    tool_action: str
    trace_message: str
    replan_hints: list[str] = field(default_factory=list)
    interaction_target: str | None = None
    interaction_relation: str | None = None
    public_message: str = ""
    ignored: bool = False
    override_meta: dict[str, Any] = field(default_factory=dict)
    outcome_meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DegradeBoundaryRequest:
    reason_code: str
    action: str
    intent: str
    interaction_owner: str
    public_message: str
    trace_message: str
    transport_status: str
    transport_reason: str | None
    interaction_target: str | None = None
    interaction_relation: str | None = None
    tool_action: str = "handoff"
    tool_decision: str = "runtime_exception"
    override_meta: dict[str, Any] = field(default_factory=dict)
    outcome_meta: dict[str, Any] = field(default_factory=dict)


class OwnerExecutionArtifact(NamedTuple):
    turn_result: TurnResult
    turn_outcome: TurnOutcome
    runtime_meta: dict[str, Any]


class ToolReplyOwnerCutoverPayload(NamedTuple):
    artifact: OwnerExecutionArtifact
    trace_payload_override: dict[str, Any]
    extra_trace_payloads: list[dict[str, Any]]
    extra_meta_updates: list[dict[str, Any]]


class ToolReplyOwnerExecution(NamedTuple):
    decision: PolicyDecision
    dialog_state: DialogState
    payload: ToolReplyOwnerCutoverPayload


class TurnExecutor:
    """Assembles the typed turn result while runtime cutover is still pending."""

    _BOOKING_PROMPTS = {
        "service": "На какую услугу хотите записаться?",
        "datetime": "На какую дату и время вам удобно?",
        "name": "Как вас зовут?",
        "phone": "Подскажите, пожалуйста, номер телефона для подтверждения.",
    }
    _BOOKING_VERIFICATION_PROMPTS = {
        "datetime": "Подскажите точную дату и время записи, чтобы я проверил ее.",
        "name": "Как вас зовут, чтобы я нашел запись?",
        "phone": "Подскажите номер телефона, на который оформляли запись.",
    }

    @staticmethod
    def _validate_boundary_override(
        *,
        decision: PolicyDecision,
        boundary_override: BoundaryOverride,
    ) -> tuple[PolicyDecision, BoundaryOverride]:
        validated = BoundaryValidator().validate(decision, override=boundary_override)
        if validated.override is None:
            raise ValueError("boundary_override_required")
        return validated.decision, validated.override

    def _build_boundary_turn_result(
        self,
        *,
        decision: PolicyDecision,
        dialog_state: DialogState,
        reply: ReplyEnvelope,
        boundary_override: BoundaryOverride,
        contract_status: TurnContractStatus,
        stages: list[str],
    ) -> TurnResult:
        return self.assemble(
            decision=decision,
            dialog_state=dialog_state,
            reply=reply,
            boundary_override=boundary_override,
            contract_status=contract_status,
            reason_code=boundary_override.reason_code,
            stages=stages,
        )

    @staticmethod
    def _build_owner_cutover_turn_outcome_meta(
        *,
        turn_result: TurnResult,
        owner_cutover: str,
        downstream_tool_decision: str | None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": turn_result.schema_version,
            "reason_code": turn_result.observability.reason_code,
            "reply_kind": turn_result.reply.reply_kind,
            "interaction_owner": turn_result.policy_decision.interaction.owner,
            "owner_cutover": owner_cutover,
            "owner_replacement_cutover": True,
        }
        if isinstance(downstream_tool_decision, str) and downstream_tool_decision.strip():
            payload["downstream_tool_decision"] = downstream_tool_decision.strip()
        if isinstance(meta, dict) and meta:
            payload.update(meta)
        return payload

    @staticmethod
    def _build_owner_cutover_runtime_meta(
        *,
        turn_result: TurnResult,
        owner_cutover: str,
        downstream_tool_decision: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": turn_result.schema_version,
            "outcome": turn_result.outcome,
            "contract_status": turn_result.contract_status,
            "reason_code": turn_result.observability.reason_code,
            "reply_kind": turn_result.reply.reply_kind,
            "interaction_owner": turn_result.policy_decision.interaction.owner,
            "owner_cutover": owner_cutover,
            "owner_replacement_cutover": True,
        }
        if isinstance(downstream_tool_decision, str) and downstream_tool_decision.strip():
            payload["downstream_tool_decision"] = downstream_tool_decision.strip()
        return payload

    def assemble(
        self,
        *,
        decision: PolicyDecision,
        dialog_state: DialogState,
        reply: ReplyEnvelope,
        boundary_override: BoundaryOverride | None = None,
        tool_outcomes: list[ToolOutcome] | None = None,
        contract_status: TurnContractStatus = "ok",
        reason_code: str | None = None,
        stages: list[str] | None = None,
    ) -> TurnResult:
        return TurnResult(
            outcome=decision.outcome,
            contract_status=contract_status,
            policy_decision=decision,
            boundary_override=boundary_override,
            reply=reply,
            tool_outcomes=tool_outcomes or [],
            dialog_state=dialog_state,
            observability=TurnObservability(reason_code=reason_code, meta={"outcome": decision.outcome}),
            trace=TurnTrace(reason_code=reason_code, stages=stages or ["planner", "boundary", "executor", "realizer"]),
        )

    def execute(
        self,
        decision: PolicyDecision,
        *,
        db: Any,
        message_text: str | None,
        client_slug: str | None,
        branch_id: Any,
        booking_state: dict[str, Any] | None,
        user_name: str | None,
        user_phone: str | None,
        now: datetime,
    ) -> RuntimeExecutionResult:
        merged_booking = self._merge_booking_slots(booking_state, decision.slots)
        if decision.outcome == "FACT":
            return self._execute_fact(
                decision,
                message_text=message_text,
                client_slug=client_slug,
                booking_state=merged_booking,
            )
        if decision.outcome == "HANDOFF":
            return RuntimeExecutionResult(
                text="Передаю диалог менеджеру. Он скоро подключится.",
                tool_action="handoff",
                tool_decision="pending",
                meta={"handoff_requested": True},
                request_handoff=True,
            )
        if decision.tool_action == "calendar.book_slot" or (
            decision.outcome == "COLLECT"
            and decision.intent == "booking"
            and self._first_missing_booking_slot(merged_booking) is None
        ):
            return self._execute_booking_confirmation(
                decision,
                db=db,
                branch_id=branch_id,
                booking_state=merged_booking,
                user_name=user_name,
                user_phone=user_phone,
                now=now,
            )
        return self._execute_collect(decision, booking_state=merged_booking)

    def _execute_collect(
        self,
        decision: PolicyDecision,
        *,
        booking_state: dict[str, Any] | None,
    ) -> RuntimeExecutionResult:
        merged_slots = self._merge_booking_slots(booking_state, decision.slots)
        next_slot = (
            self._normalize_booking_slot(decision.pending_question_contract.next_question)
            or self._first_missing_booking_slot(merged_slots)
        )
        prompt_map = self._BOOKING_PROMPTS
        if decision.intent in {
            "check_booking",
            "verify_booking",
            "confirm_booking",
            "booking_confirmation",
        }:
            prompt_map = {**self._BOOKING_PROMPTS, **self._BOOKING_VERIFICATION_PROMPTS}
        pending_question_act = None
        if isinstance(decision.meta, dict):
            pending_question_act = self._normalize_booking_slot(
                decision.meta.get("pending_question_act")
            )
        if pending_question_act == "slot_constraint" and next_slot == "datetime":
            candidate_datetime = None
            if isinstance(decision.tool_args, dict):
                candidate_datetime = self._normalize_booking_slot(
                    decision.tool_args.get("candidate_datetime")
                )
            if candidate_datetime:
                prompt = (
                    "Проверить наличие именно на "
                    f"{candidate_datetime} "
                    "автоматически не подтверждаю. Если хотите продолжить запись на это время, "
                    "подтвердите его или назовите другой удобный слот."
                )
                return RuntimeExecutionResult(
                    text=prompt,
                    tool_action=decision.tool_action,
                    tool_decision="slot_constraint",
                    meta={
                        "slot_values": merged_slots,
                        "next_slot": next_slot,
                        "pending_question_act": "slot_constraint",
                        "pending_question_target": "time",
                        "question_contract": True,
                        "alternate_datetime": candidate_datetime,
                    },
                )
        prompt = prompt_map.get(next_slot or "", "Подскажите, пожалуйста, следующий удобный слот.")
        meta: dict[str, Any] = {"slot_values": merged_slots}
        if next_slot:
            meta["next_slot"] = next_slot
        return RuntimeExecutionResult(
            text=prompt,
            tool_action=decision.tool_action,
            tool_decision=next_slot or "collect",
            meta=meta,
        )

    def _execute_fact(
        self,
        decision: PolicyDecision,
        *,
        message_text: str | None,
        client_slug: str | None,
        booking_state: dict[str, Any] | None,
    ) -> RuntimeExecutionResult:
        from app.services.pack_runtime_service import (
            build_master_reply_from_pack,
            get_pack_decision,
            resolve_master_intent,
        )

        if decision.tool_action == "calendar.get_booking" and decision.intent in {
            "check_booking",
            "verify_booking",
        }:
            return RuntimeExecutionResult(
                text=(
                    "Чтобы проверить запись, подскажите примерную дату и время "
                    "или имя, на которое оформляли запись."
                ),
                tool_action=decision.tool_action,
                tool_decision="not_found",
                meta={"booking_verification_prompt": True},
            )

        query_text = (message_text or "").strip()
        merged_slots = self._merge_booking_slots(booking_state, decision.slots)
        service_name = merged_slots.get("service")
        fact_refs = {
            str(item).strip().casefold()
            for item in (
                list(decision.pack_refs)
                + list(decision.fact_refs)
                + list(decision.capability_refs)
            )
            if isinstance(item, str) and item.strip()
        }
        if decision.intent == "master_query" or "master" in fact_refs:
            master_service = None
            if isinstance(decision.tool_args, dict):
                raw_master_service = decision.tool_args.get("service_query")
                if isinstance(raw_master_service, str) and raw_master_service.strip():
                    master_service = raw_master_service.strip()
            if master_service is None:
                master_service = service_name
            master_resolution = resolve_master_intent(
                message_text=query_text,
                client_slug=client_slug,
                service_query=master_service,
                intent_decomp=None,
                force_master_intent=bool(master_service),
            )
            master_reply = build_master_reply_from_pack(
                client_slug=client_slug,
                message_text=query_text,
                resolution=master_resolution,
            )
            if master_reply and isinstance(master_reply.response, str) and master_reply.response.strip():
                master_meta = dict(master_reply.meta) if isinstance(master_reply.meta, dict) else {}
                info_sections = [
                    item
                    for item in master_meta.get("info_sections", [])
                    if isinstance(item, str) and item.strip()
                ]
                if "master" not in info_sections:
                    info_sections.append("master")
                master_meta["info_sections"] = info_sections
                return RuntimeExecutionResult(
                    text=master_reply.response.strip(),
                    tool_action=decision.tool_action,
                    tool_decision=master_reply.intent or "master",
                    meta=master_meta,
                    request_handoff=master_reply.action == "escalate",
                )
        pack_decision = get_pack_decision(query_text, client_slug=client_slug)
        if pack_decision and isinstance(pack_decision.response, str) and pack_decision.response.strip():
            pack_meta = dict(pack_decision.meta) if isinstance(pack_decision.meta, dict) else {}
            info_sections = [
                item
                for item in (pack_meta.get("info_sections") or [])
                if isinstance(item, str) and item.strip()
            ]
            if (
                pack_decision.intent in {"price_query", "price_manicure"}
                or decision.intent == "pricing"
                or "pricing" in fact_refs
            ) and "pricing" not in info_sections:
                info_sections.append("pricing")
            if (
                pack_decision.intent in {"service_duration", "duration"}
                or decision.intent == "duration"
                or "duration" in fact_refs
            ) and "duration" not in info_sections:
                info_sections.append("duration")
            if pack_decision.intent == "services_overview" and "services_overview" not in info_sections:
                info_sections.append("services_overview")
            if info_sections:
                pack_meta["info_sections"] = info_sections
            request_handoff = pack_decision.action == "escalate"
            return RuntimeExecutionResult(
                text=pack_decision.response.strip(),
                tool_action=decision.tool_action,
                tool_decision=pack_decision.intent or pack_decision.action,
                meta=pack_meta,
                request_handoff=request_handoff,
            )
        fallback_text = (message_text or "").strip() or "Я уточню это для вас."
        return RuntimeExecutionResult(
            text=fallback_text,
            tool_action=decision.tool_action,
            tool_decision="passthrough",
            meta={"fact_fallback": True},
        )

    def _execute_booking_confirmation(
        self,
        decision: PolicyDecision,
        *,
        db: Any,
        branch_id: Any,
        booking_state: dict[str, Any] | None,
        user_name: str | None,
        user_phone: str | None,
        now: datetime,
    ) -> RuntimeExecutionResult:
        from app.services.appointment_service import AppointmentConflictError, SchedulingService

        merged_slots = self._merge_booking_slots(booking_state, decision.slots)
        missing_slot = self._first_missing_booking_slot(merged_slots)
        if missing_slot is not None:
            prompt = self._BOOKING_PROMPTS.get(missing_slot, self._BOOKING_PROMPTS["service"])
            return RuntimeExecutionResult(
                text=prompt,
                tool_action="collect",
                tool_decision=missing_slot,
                meta={"slot_values": merged_slots, "booking_incomplete": True},
            )

        if branch_id is None:
            return RuntimeExecutionResult(
                text="Чтобы завершить запись, мне нужен активный филиал. Передаю диалог менеджеру.",
                tool_action="handoff",
                tool_decision="branch_missing",
                meta={"slot_values": merged_slots},
                request_handoff=True,
            )

        start_at = self._parse_booking_datetime(merged_slots.get("datetime"), now=now)
        if start_at is None:
            return RuntimeExecutionResult(
                text=self._BOOKING_PROMPTS["datetime"],
                tool_action="collect",
                tool_decision="datetime_invalid",
                meta={"slot_values": merged_slots, "booking_incomplete": True},
            )

        duration_minutes = self._resolve_duration_minutes(db, branch_id=branch_id, service_name=merged_slots["service"])
        end_at = start_at + timedelta(minutes=duration_minutes)
        customer_name = merged_slots.get("name") or user_name or "Клиент"
        customer_phone = merged_slots.get("phone") or user_phone
        try:
            appointment = SchedulingService(db).create_appointment(
                client_id=decision.meta["client_id"],
                branch_id=branch_id,
                specialist_id=None,
                start_at=start_at,
                end_at=end_at,
                customer_name=customer_name,
                customer_phone=customer_phone,
                service_type=merged_slots.get("service"),
                conversation_id=decision.meta.get("conversation_id"),
                status="CONFIRMED",
                source="bot",
                confirmation_policy="client",
                commit=False,
            )
        except AppointmentConflictError:
            return RuntimeExecutionResult(
                text="Это время уже занято. Подскажите другую дату и время, пожалуйста.",
                tool_action="collect",
                tool_decision="datetime_conflict",
                meta={
                    "slot_values": merged_slots,
                    "next_slot": "datetime",
                    "booking_incomplete": True,
                },
            )
        confirmation_text = (
            f"Готово, записал вас на {merged_slots['service']} "
            f"на {start_at.astimezone(start_at.tzinfo).strftime('%d.%m %H:%M')}."
        )
        return RuntimeExecutionResult(
            text=confirmation_text,
            tool_action="calendar.book_slot",
            tool_decision="ok",
            meta={
                "slot_values": merged_slots,
                "appointment_id": str(appointment.id),
                "service": merged_slots.get("service"),
                "datetime": merged_slots.get("datetime"),
            },
            clear_booking=True,
        )

    @staticmethod
    def _normalize_booking_slot(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip().casefold()
        if not cleaned:
            return None
        mapping = {
            "time": "datetime",
            "date": "datetime",
            "service_query": "service",
            "customer_name": "name",
            "phone_number": "phone",
        }
        return mapping.get(cleaned, cleaned)

    def _merge_booking_slots(
        self,
        booking_state: dict[str, Any] | None,
        decision_slots: dict[str, str] | None,
    ) -> dict[str, str]:
        merged: dict[str, str] = {}
        for source in (booking_state or {}, decision_slots or {}):
            if not isinstance(source, dict):
                continue
            for raw_key, raw_value in source.items():
                slot_key = self._normalize_booking_slot(raw_key)
                if slot_key is None or slot_key not in {"service", "datetime", "name", "phone"}:
                    continue
                if not isinstance(raw_value, str):
                    continue
                cleaned = raw_value.strip()
                if cleaned:
                    merged[slot_key] = cleaned
        return merged

    @staticmethod
    def _first_missing_booking_slot(booking_slots: dict[str, str]) -> str | None:
        for slot_key in ("service", "datetime", "name"):
            if slot_key not in booking_slots:
                return slot_key
        return None

    @staticmethod
    def _parse_booking_datetime(value: str | None, *, now: datetime) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        normalized_now = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            parsed = None
        if parsed is None:
            try:
                import dateparser

                parsed = dateparser.parse(
                    value,
                    languages=["ru", "en"],
                    settings={
                        "RELATIVE_BASE": normalized_now,
                        "TIMEZONE": "Asia/Almaty",
                        "RETURN_AS_TIMEZONE_AWARE": True,
                        "PREFER_DATES_FROM": "future",
                    },
                )
            except Exception:
                parsed = None
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=normalized_now.tzinfo)
        return parsed

    @staticmethod
    def _resolve_duration_minutes(db: Any, *, branch_id: Any, service_name: str | None) -> int:
        if not service_name:
            return 60
        try:
            from app.models.service import Service

            service = (
                db.query(Service)
                .filter(Service.branch_id == branch_id, Service.name == service_name)
                .first()
            )
        except Exception:
            service = None
        if service and isinstance(getattr(service, "duration_min", None), int) and service.duration_min > 0:
            return int(service.duration_min)
        return 60

    def build_block_boundary_turn_result(
        self,
        *,
        decision: PolicyDecision,
        dialog_state: DialogState,
        reply: ReplyEnvelope,
        boundary_override: BoundaryOverride,
    ) -> TurnResult:
        return self._build_boundary_turn_result(
            decision=decision,
            dialog_state=dialog_state,
            reply=reply,
            boundary_override=boundary_override,
            contract_status="blocked",
            stages=["ingress", "planner", "boundary", "executor", "realizer"],
        )

    def build_degrade_boundary_turn_result(
        self,
        *,
        decision: PolicyDecision,
        dialog_state: DialogState,
        reply: ReplyEnvelope,
        boundary_override: BoundaryOverride,
    ) -> TurnResult:
        return self._build_boundary_turn_result(
            decision=decision,
            dialog_state=dialog_state,
            reply=reply,
            boundary_override=boundary_override,
            contract_status="degraded",
            stages=["planner", "boundary", "executor", "realizer", "reasoning_core_exception"],
        )

    def build_block_boundary_artifact(
        self,
        *,
        decision: PolicyDecision,
        dialog_state: DialogState,
        boundary_override: BoundaryOverride,
        tool_action: str,
        text: str = "",
        ignored: bool = False,
        meta: dict[str, Any] | None = None,
    ) -> BoundaryExecutionArtifact:
        validated_decision, validated_override = self._validate_boundary_override(
            decision=decision,
            boundary_override=boundary_override,
        )
        reply = ResponseRealizer().realize(
            validated_decision,
            override=validated_override,
            text=text,
        )
        turn_result = self.build_block_boundary_turn_result(
            decision=validated_decision,
            dialog_state=dialog_state,
            reply=reply,
            boundary_override=validated_override,
        )
        turn_outcome = BoundaryValidator().build_block_turn_outcome(
            turn_result=turn_result,
            tool_action=tool_action,
            ignored=ignored,
            meta=meta,
        )
        return BoundaryExecutionArtifact(turn_result=turn_result, turn_outcome=turn_outcome)

    def build_degrade_boundary_artifact(
        self,
        *,
        decision: PolicyDecision,
        dialog_state: DialogState,
        boundary_override: BoundaryOverride,
        text: str,
        transport_status: str,
        transport_reason: str | None,
        tool_action: str = "handoff",
        tool_decision: str = "runtime_exception",
        meta: dict[str, Any] | None = None,
    ) -> BoundaryExecutionArtifact:
        validated_decision, validated_override = self._validate_boundary_override(
            decision=decision,
            boundary_override=boundary_override,
        )
        reply = ResponseRealizer().realize(
            validated_decision,
            override=validated_override,
            text=text,
        )
        turn_result = self.build_degrade_boundary_turn_result(
            decision=validated_decision,
            dialog_state=dialog_state,
            reply=reply,
            boundary_override=validated_override,
        )
        turn_outcome = BoundaryValidator().build_degrade_turn_outcome(
            turn_result=turn_result,
            transport_status=transport_status,
            transport_reason=transport_reason,
            tool_action=tool_action,
            tool_decision=tool_decision,
            meta=meta,
        )
        return BoundaryExecutionArtifact(turn_result=turn_result, turn_outcome=turn_outcome)

    def build_block_boundary_artifact_from_request(
        self,
        *,
        request: BlockBoundaryRequest,
    ) -> BoundaryExecutionArtifact:
        decision = TurnPlanner().build_preflight_reject(
            reason_code=request.reason_code,
            action=request.action,
            intent=request.intent,
            interaction_owner=request.interaction_owner,
            interaction_target=request.interaction_target,
            interaction_relation=request.interaction_relation,
        )
        boundary_override = BoundaryValidator().build_block_override(
            reason_code=request.reason_code,
            trace_message=request.trace_message,
            replan_hints=list(request.replan_hints),
            public_message=request.public_message,
            meta=dict(request.override_meta),
        )
        dialog_state = DialogStateService().build_blocked_state(
            reason_code=request.reason_code,
            interaction_owner=request.interaction_owner,
            interaction_target=request.interaction_target,
            interaction_relation=request.interaction_relation,
        )
        return self.build_block_boundary_artifact(
            decision=decision,
            dialog_state=dialog_state,
            boundary_override=boundary_override,
            tool_action=request.tool_action,
            text=request.public_message,
            ignored=request.ignored,
            meta=dict(request.outcome_meta),
        )

    def build_degrade_boundary_artifact_from_request(
        self,
        *,
        request: DegradeBoundaryRequest,
    ) -> BoundaryExecutionArtifact:
        decision = TurnPlanner().build_controlled_degrade(
            reason_code=request.reason_code,
            action=request.action,
            intent=request.intent,
            interaction_owner=request.interaction_owner,
            interaction_target=request.interaction_target,
            interaction_relation=request.interaction_relation,
        )
        boundary_override = BoundaryValidator().build_degrade_override(
            reason_code=request.reason_code,
            public_message=request.public_message,
            trace_message=request.trace_message,
            meta=dict(request.override_meta),
        )
        dialog_state = DialogStateService().build_degraded_state(
            reason_code=request.reason_code,
            interaction_owner=request.interaction_owner,
            interaction_target=request.interaction_target,
            interaction_relation=request.interaction_relation,
        )
        return self.build_degrade_boundary_artifact(
            decision=decision,
            dialog_state=dialog_state,
            boundary_override=boundary_override,
            text=request.public_message,
            transport_status=request.transport_status,
            transport_reason=request.transport_reason,
            tool_action=request.tool_action,
            tool_decision=request.tool_decision,
            meta=dict(request.outcome_meta),
        )

    def build_owner_cutover_turn_outcome(
        self,
        *,
        turn_result: TurnResult,
        transport_status: str,
        transport_reason: str | None,
        owner_cutover: str,
        downstream_tool_decision: str | None = None,
        followup_type: str | None = None,
        followup_reason: str | None = None,
        action: OwnerCutoverAction = "reply",
        source: str = "consultant_core_runtime",
        intent: str | None = None,
        tool_action: str | None = None,
        tool_decision: str | None = "planner_owner_cutover",
        followup_prompt: str | None = None,
        contract_status: TurnContractStatus = "ok",
        meta: dict[str, Any] | None = None,
    ) -> TurnOutcome:
        return TurnOutcome(
            action=action,
            intent=intent or turn_result.policy_decision.intent,
            source=source,
            tool_action=tool_action or turn_result.policy_decision.tool_action,
            tool_decision=tool_decision,
            expected_reply_type=followup_type,
            expected_reply_reason=followup_reason,
            followup_prompt=followup_prompt,
            contract_status=contract_status,
            observability=TurnOutcomeObservability(
                reply_observed=transport_status == "delivered",
                transport_status=transport_status,
                transport_reason=transport_reason,
            ),
            meta=self._build_owner_cutover_turn_outcome_meta(
                turn_result=turn_result,
                owner_cutover=owner_cutover,
                downstream_tool_decision=downstream_tool_decision,
                meta=meta,
            ),
        )

    def build_owner_cutover_artifact(
        self,
        *,
        decision: PolicyDecision,
        dialog_state: DialogState,
        text: str,
        owner_cutover: str,
        transport_status: str,
        transport_reason: str | None,
        downstream_tool_decision: str | None = None,
        followup_type: str | None = None,
        followup_reason: str | None = None,
        reason_code: str | None = None,
        stages: list[str] | None = None,
        action: OwnerCutoverAction = "reply",
        source: str = "consultant_core_runtime",
        intent: str | None = None,
        tool_action: str | None = None,
        tool_decision: str | None = "planner_owner_cutover",
        followup_prompt: str | None = None,
        contract_status: TurnContractStatus = "ok",
        meta: dict[str, Any] | None = None,
    ) -> OwnerExecutionArtifact:
        reply = ResponseRealizer().realize(decision, text=text)
        turn_result = self.assemble(
            decision=decision,
            dialog_state=dialog_state,
            reply=reply,
            contract_status=contract_status,
            reason_code=reason_code,
            stages=stages,
        )
        turn_outcome = self.build_owner_cutover_turn_outcome(
            turn_result=turn_result,
            transport_status=transport_status,
            transport_reason=transport_reason,
            owner_cutover=owner_cutover,
            downstream_tool_decision=downstream_tool_decision,
            followup_type=followup_type,
            followup_reason=followup_reason,
            action=action,
            source=source,
            intent=intent,
            tool_action=tool_action,
            tool_decision=tool_decision,
            followup_prompt=followup_prompt,
            contract_status=contract_status,
            meta=meta,
        )
        runtime_meta = self._build_owner_cutover_runtime_meta(
            turn_result=turn_result,
            owner_cutover=owner_cutover,
            downstream_tool_decision=downstream_tool_decision,
        )
        return OwnerExecutionArtifact(
            turn_result=turn_result,
            turn_outcome=turn_outcome,
            runtime_meta=runtime_meta,
        )

    def build_tool_reply_owner_cutover_payload(
        self,
        *,
        decision: PolicyDecision,
        dialog_state: DialogState,
        text: str,
        owner_cutover: str,
        reply_source: str,
        reply_intent: str,
        intent: str | None,
        tool_action: str | None,
        raw_tool_decision: str | None,
        normalized_tool_decision: str | None,
        followup_type: str | None,
        followup_reason: str | None,
        followup_prompt: str | None,
        services_overview_followup: bool,
        conversation_state: str,
        pending_question_tool_followup: bool = False,
        pending_question_act: str | None = None,
        pending_question_target: str | None = None,
        collect_service_info_interrupt_active: bool = False,
        info_sections: list[str] | None = None,
        saved_message_present: bool = False,
        master_override_meta: dict[str, Any] | None = None,
    ) -> ToolReplyOwnerCutoverPayload:
        contract_status: TurnContractStatus = (
            "degraded"
            if normalized_tool_decision in {"contract_invalid", "verifier_blocked"}
            else "ok"
        )
        artifact = self.build_owner_cutover_artifact(
            decision=decision,
            dialog_state=dialog_state,
            text=text,
            owner_cutover=owner_cutover,
            transport_status="pending",
            transport_reason=None,
            downstream_tool_decision=normalized_tool_decision,
            followup_type=followup_type,
            followup_reason=followup_reason,
            reason_code=decision.meta.get("reason") if isinstance(decision.meta, dict) else None,
            stages=[
                "ingress",
                "decision_router",
                "executor",
                "realizer",
                "llm_policy_core_tool",
            ],
            action="reply",
            source=reply_source,
            intent=intent,
            tool_action=tool_action,
            tool_decision=normalized_tool_decision,
            followup_prompt=followup_prompt,
            contract_status=contract_status,
            meta={"services_overview_followup": services_overview_followup},
        )
        extra_trace_payloads: list[dict[str, Any]] = []
        if pending_question_tool_followup:
            extra_trace_payloads.append(
                {
                    "stage": "pending_question_interaction",
                    "decision": "booking_slot_guidance",
                    "state": conversation_state,
                    "source": "tool_registry",
                    "tool_action": tool_action,
                    "tool_decision": normalized_tool_decision,
                    "pending_question_act": pending_question_act,
                    "pending_question_target": pending_question_target or "time",
                    "expected_reply_type": followup_type,
                }
            )
        if collect_service_info_interrupt_active:
            interrupt_sections = (
                list(info_sections)
                if isinstance(info_sections, list) and info_sections
                else ["services_overview"]
            )
            extra_trace_payloads.append(
                {
                    "stage": "booking_interrupt",
                    "decision": "info_reply",
                    "state": conversation_state,
                    "booking_interrupt_info": True,
                    "info_sections": interrupt_sections,
                }
            )

        extra_meta_updates: list[dict[str, Any]] = [{"intent": reply_intent}]
        if collect_service_info_interrupt_active and saved_message_present:
            interrupt_sections = (
                list(info_sections)
                if isinstance(info_sections, list) and info_sections
                else ["services_overview"]
            )
            extra_meta_updates.append(
                {
                    "booking_info_interrupt": True,
                    "booking_interrupt_info": True,
                    "booking_info_intents": interrupt_sections,
                }
            )
        if pending_question_tool_followup and saved_message_present:
            extra_meta_updates.append(
                {
                    "pending_question_act": pending_question_act,
                    "pending_question_target": pending_question_target or "time",
                    "pending_question_interaction": pending_question_act,
                    "pending_question_owner": "booking_slot_guidance",
                }
            )
        if isinstance(master_override_meta, dict):
            extra_meta_updates.append(dict(master_override_meta))

        return ToolReplyOwnerCutoverPayload(
            artifact=artifact,
            trace_payload_override={
                "stage": "llm_policy_core_tool",
                "decision": "reply",
                "state": conversation_state,
                "tool_action": tool_action,
                "tool_decision": raw_tool_decision,
                "reply_source": reply_source,
                "turn_outcome": artifact.turn_outcome.to_metadata(),
            },
            extra_trace_payloads=extra_trace_payloads,
            extra_meta_updates=extra_meta_updates,
        )

    def build_tool_reply_owner_execution(
        self,
        *,
        payload: dict[str, Any] | None,
        default_intent: str | None,
        reply_intent: str | None,
        tool_action: str | None,
        expected_reply_type: str | None,
        expected_reply_reason: str | None,
        text: str,
        owner_cutover: str,
        reply_source: str,
        intent: str | None,
        raw_tool_decision: str | None,
        normalized_tool_decision: str | None,
        followup_prompt: str | None,
        services_overview_followup: bool,
        conversation_state: str,
        pending_question_tool_followup: bool = False,
        pending_question_act: str | None = None,
        pending_question_target: str | None = None,
        collect_service_info_interrupt_active: bool = False,
        info_sections: list[str] | None = None,
        saved_message_present: bool = False,
        master_override_applied: bool = False,
        master_override_meta: dict[str, Any] | None = None,
    ) -> ToolReplyOwnerExecution:
        tool_reply_decision = TurnPlanner().build_tool_reply_owner_decision(
            payload=payload,
            default_intent=default_intent,
            reply_intent=reply_intent,
            tool_action=tool_action,
            expected_reply_type=expected_reply_type,
            pending_question_tool_followup=pending_question_tool_followup,
            pending_question_act=pending_question_act,
            collect_service_info_interrupt_active=collect_service_info_interrupt_active,
            master_override_applied=master_override_applied,
        )
        tool_reply_dialog_state = DialogStateService().build_tool_reply_owner_state(
            decision=tool_reply_decision,
            expected_reply_type=expected_reply_type,
            expected_reply_reason=expected_reply_reason,
            owner_cutover=owner_cutover,
        )
        tool_reply_payload = self.build_tool_reply_owner_cutover_payload(
            decision=tool_reply_decision,
            dialog_state=tool_reply_dialog_state,
            text=text,
            owner_cutover=owner_cutover,
            reply_source=reply_source,
            reply_intent=reply_intent or tool_action or default_intent or "info",
            intent=intent,
            tool_action=tool_action,
            raw_tool_decision=raw_tool_decision,
            normalized_tool_decision=normalized_tool_decision,
            followup_type=expected_reply_type,
            followup_reason=expected_reply_reason,
            followup_prompt=followup_prompt,
            services_overview_followup=services_overview_followup,
            conversation_state=conversation_state,
            pending_question_tool_followup=pending_question_tool_followup,
            pending_question_act=pending_question_act,
            pending_question_target=pending_question_target,
            collect_service_info_interrupt_active=collect_service_info_interrupt_active,
            info_sections=info_sections,
            saved_message_present=saved_message_present,
            master_override_meta=master_override_meta,
        )
        return ToolReplyOwnerExecution(
            decision=tool_reply_decision,
            dialog_state=tool_reply_dialog_state,
            payload=tool_reply_payload,
        )


__all__ = [
    "BlockBoundaryRequest",
    "BoundaryExecutionArtifact",
    "DegradeBoundaryRequest",
    "OwnerExecutionArtifact",
    "OwnerCutoverAction",
    "RuntimeExecutionResult",
    "ToolReplyOwnerExecution",
    "ToolReplyOwnerCutoverPayload",
    "ToolOutcome",
    "ToolStatus",
    "TurnContractStatus",
    "TurnExecutor",
    "TurnObservability",
    "TurnResult",
    "TurnTrace",
]
