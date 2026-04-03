from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, NamedTuple

from pydantic import BaseModel, ConfigDict, Field

from app.core.binding_plan import BindingPlanV1
from app.core.boundary_validator import BoundaryOverride, BoundaryValidator
from app.core.dialog_state_service import DialogState, DialogStateService
from app.core.fact_plane import (
    FactPlanV1,
    FactRequestV1,
    FactResultV1,
    build_fact_contract_meta,
    normalize_fact_ref_list,
)
from app.core.response_realizer import ReplyEnvelope, ResponseRealizer
from app.core.runtime_trace_contract import RuntimeTraceContractV1
from app.core.turn_planner import DecisionOutcome, PolicyDecision, TurnPlanner
from app.schemas.turn_outcome import TurnOutcome, TurnOutcomeObservability

ToolStatus = Literal["ok", "degraded", "blocked", "skipped"]
TurnContractStatus = Literal["ok", "degraded", "blocked"]


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
    runtime_trace_contract: RuntimeTraceContractV1 | None = None


class TurnResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "turn_result.v1"
    outcome: DecisionOutcome
    contract_status: TurnContractStatus = "ok"
    policy_decision: PolicyDecision | None = None
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



class TurnExecutor:
    """Assembles the typed turn result while runtime cutover is still pending."""

    _FIRST_FACT_FAMILY_ID = "location_hours_parking"
    _FIRST_FACT_FAMILY_REFS = {
        "location",
        "hours",
        "parking",
    }
    _BOOKING_PROMPTS = {
        "service": "На какую услугу хотите записаться?",
        "datetime": "На какую дату и время вам удобно?",
        "name": "Как вас зовут?",
        "phone": "Подскажите, пожалуйста, номер телефона для подтверждения.",
    }
    _CONSULT_PROMPTS = {
        "media": "Пришлите, пожалуйста, фото-пример желаемого результата.",
    }
    _BOOKING_VERIFICATION_PROMPTS = {
        "datetime": "Подскажите точную дату и время записи, чтобы я проверил ее.",
        "name": "Как вас зовут, чтобы я нашел запись?",
        "phone": "Подскажите номер телефона, на который оформляли запись.",
    }

    @staticmethod
    def _validate_boundary_override(
        *,
        decision: PolicyDecision | None,
        boundary_override: BoundaryOverride,
    ) -> tuple[PolicyDecision | None, BoundaryOverride]:
        validated = BoundaryValidator().validate(decision, override=boundary_override)
        if validated.override is None:
            raise ValueError("boundary_override_required")
        return validated.decision, validated.override

    def _build_boundary_turn_result(
        self,
        *,
        decision: PolicyDecision | None,
        dialog_state: DialogState,
        reply: ReplyEnvelope,
        boundary_override: BoundaryOverride,
        contract_status: TurnContractStatus,
        stages: list[str],
        outcome: DecisionOutcome,
    ) -> TurnResult:
        return self.assemble(
            decision=decision,
            outcome=outcome,
            dialog_state=dialog_state,
            reply=reply,
            boundary_override=boundary_override,
            contract_status=contract_status,
            reason_code=boundary_override.reason_code,
            stages=stages,
        )

    def assemble(
        self,
        *,
        decision: PolicyDecision | None,
        outcome: DecisionOutcome | None = None,
        dialog_state: DialogState,
        reply: ReplyEnvelope,
        boundary_override: BoundaryOverride | None = None,
        tool_outcomes: list[ToolOutcome] | None = None,
        contract_status: TurnContractStatus = "ok",
        reason_code: str | None = None,
        stages: list[str] | None = None,
    ) -> TurnResult:
        resolved_outcome = outcome or (decision.outcome if isinstance(decision, PolicyDecision) else None)
        if resolved_outcome is None:
            raise ValueError("turn_result_outcome_required")
        return TurnResult(
            outcome=resolved_outcome,
            contract_status=contract_status,
            policy_decision=decision,
            boundary_override=boundary_override,
            reply=reply,
            tool_outcomes=tool_outcomes or [],
            dialog_state=dialog_state,
            observability=TurnObservability(reason_code=reason_code, meta={"outcome": resolved_outcome}),
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
        conversation_id: Any | None = None,
    ) -> RuntimeExecutionResult:
        merged_booking = self._merge_booking_slots(booking_state, decision.slots)
        binding_plan = self._binding_plan(decision)
        if not isinstance(binding_plan, BindingPlanV1):
            return self._execute_binding_gap("executor:missing_binding_plan")

        binding_outcome_type = binding_plan.binding_outcome_type
        bound_ref = self._normalize_fact_hint(binding_plan.selected_tool_or_workflow_ref)

        if binding_outcome_type == "handoff":
            return self._execute_binding_handoff(
                "handoff",
                handoff_reason_code=binding_plan.handoff_reason_code,
            )
        if binding_outcome_type == "degrade":
            return self._execute_binding_handoff(
                "degrade",
                handoff_reason_code=binding_plan.degrade_reason_code,
            )
        if binding_outcome_type == "deny":
            return RuntimeExecutionResult(
                text="",
                tool_action="noop",
                tool_decision="blocked",
                meta={"reason_code": binding_plan.deny_reason_code or "binding_deny"},
            )
        if binding_outcome_type in {"workflow_start", "workflow_advance"}:
            return self._execute_collect(decision, booking_state=merged_booking)
        if binding_outcome_type != "tool_call":
            return self._execute_binding_gap(
                f"executor:unsupported_binding_outcome:{binding_outcome_type}"
            )
        if bound_ref == "calendar.book_slot":
            return self._execute_booking_confirmation(
                decision,
                db=db,
                branch_id=branch_id,
                booking_state=merged_booking,
                user_name=user_name,
                user_phone=user_phone,
                now=now,
            )
        return self._execute_fact(
            decision,
            db=db,
            message_text=message_text,
            client_slug=client_slug,
            branch_id=branch_id,
            booking_state=merged_booking,
            now=now,
            conversation_id=conversation_id,
        )

    @staticmethod
    def _execute_binding_handoff(
        tool_decision: str,
        *,
        handoff_reason_code: str | None,
    ) -> RuntimeExecutionResult:
        meta: dict[str, Any] = {"handoff_requested": True}
        if isinstance(handoff_reason_code, str) and handoff_reason_code.strip():
            meta["reason_code"] = handoff_reason_code.strip()
        return RuntimeExecutionResult(
            text="Передаю диалог менеджеру. Он скоро подключится.",
            tool_action="handoff",
            tool_decision=tool_decision,
            meta=meta,
            request_handoff=True,
        )

    @classmethod
    def _execute_binding_gap(cls, reason_code: str) -> RuntimeExecutionResult:
        return cls._execute_binding_handoff("binding_gap", handoff_reason_code=reason_code)

    def _execute_collect(
        self,
        decision: PolicyDecision,
        *,
        booking_state: dict[str, Any] | None,
    ) -> RuntimeExecutionResult:
        merged_slots = self._merge_booking_slots(booking_state, decision.slots)
        canonical_pending_question = TurnPlanner().canonical_pending_question_contract(decision)
        semantic_contract = self._build_execution_semantic_contract(
            decision,
            booking_state=merged_slots,
        )
        pending_question_contract = self._build_execution_pending_question_contract(decision)
        next_slot = (
            self._normalize_booking_slot(canonical_pending_question.next_question)
            or self._first_missing_booking_slot(merged_slots)
        )
        prompt_map = self._BOOKING_PROMPTS
        if decision.intent == "consult":
            prompt_map = {**self._BOOKING_PROMPTS, **self._CONSULT_PROMPTS}
        elif decision.intent in {
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
        if not pending_question_act:
            pending_question_act = self._normalize_booking_slot(
                canonical_pending_question.pending_question_act
            )
        if not pending_question_act:
            pending_question_act = self._normalize_booking_slot(
                (pending_question_contract or {}).get("pending_question_act")
            )
        if not pending_question_act:
            pending_question_act = self._normalize_booking_slot(
                (semantic_contract or {}).get("pending_question_act")
            )
        if pending_question_act == "slot_constraint" and next_slot == "datetime":
            candidate_datetime = self._normalize_booking_slot(
                decision.meta.get("alternate_datetime")
            ) if isinstance(decision.meta, dict) else None
            if not candidate_datetime:
                candidate_datetime = self._normalize_booking_slot(
                    (pending_question_contract or {}).get("alternate_datetime")
                )
            if not candidate_datetime:
                candidate_datetime = self._normalize_booking_slot(
                    (semantic_contract or {}).get("alternate_datetime")
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
                    meta=self._attach_semantic_contract_meta(
                        decision,
                        {
                            "slot_values": merged_slots,
                            "next_slot": next_slot,
                            "pending_question_act": "slot_constraint",
                            "pending_question_target": "time",
                            "question_contract": True,
                            "alternate_datetime": candidate_datetime,
                        },
                        semantic_contract=semantic_contract,
                        pending_question_contract=pending_question_contract,
                    ),
                )
        prompt = self._build_collect_prompt(
            next_slot=next_slot,
            prompt_map=prompt_map,
            semantic_contract=semantic_contract,
            pending_question_contract=pending_question_contract,
        )
        meta: dict[str, Any] = self._attach_semantic_contract_meta(
            decision,
            {"slot_values": merged_slots},
            semantic_contract=semantic_contract,
            pending_question_contract=pending_question_contract,
        )
        if next_slot:
            meta["next_slot"] = next_slot
        return RuntimeExecutionResult(
            text=prompt,
            tool_action=decision.tool_action,
            tool_decision=next_slot or "collect",
            meta=meta,
        )

    def _build_collect_prompt(
        self,
        *,
        next_slot: str | None,
        prompt_map: dict[str, str],
        semantic_contract: dict[str, Any] | None,
        pending_question_contract: dict[str, Any] | None,
    ) -> str:
        prompt = prompt_map.get(
            next_slot or "",
            "Подскажите, пожалуйста, следующий удобный слот.",
        )
        pending_target = self._normalize_fact_hint(
            (pending_question_contract or {}).get("pending_question_target")
            or (semantic_contract or {}).get("pending_question_target")
        )
        relation = self._normalize_fact_hint(
            (pending_question_contract or {}).get("active_question_relation")
            or (semantic_contract or {}).get("active_question_relation")
        )
        if pending_target != "specialist" or relation != "referent_followup":
            return prompt
        specialist_payload = self._semantic_referents(semantic_contract).get("specialist")
        if not isinstance(specialist_payload, dict):
            return prompt
        specialist_name = self._normalize_execution_text(specialist_payload.get("value"))
        if not specialist_name:
            return prompt
        return f"Хорошо, ориентир по мастеру — {specialist_name}. {prompt}"

    @staticmethod
    def _lowercase_sentence_start(value: str) -> str:
        if not value:
            return value
        return value[:1].lower() + value[1:]

    def _build_booking_verification_followup_text(
        self,
        *,
        message_text: str | None,
        pending_question_contract: dict[str, Any] | None,
    ) -> str:
        pending_contract = pending_question_contract or {}
        next_slot = self._normalize_booking_slot(pending_contract.get("next_question"))
        if next_slot is None:
            expected_reply_type = self._normalize_booking_slot(
                pending_contract.get("expected_reply_type")
            )
            if expected_reply_type == "time":
                next_slot = "datetime"
            elif expected_reply_type in {"name", "phone"}:
                next_slot = expected_reply_type
        prompt = self._BOOKING_VERIFICATION_PROMPTS.get(next_slot or "")
        if not prompt:
            return (
                "Чтобы проверить запись, подскажите примерную дату и время "
                "или имя, на которое оформляли запись."
            )
        return prompt

    def _execute_fact(
        self,
        decision: PolicyDecision,
        *,
        db: Any,
        message_text: str | None,
        client_slug: str | None,
        branch_id: Any,
        booking_state: dict[str, Any] | None,
        now: datetime,
        conversation_id: Any | None,
    ) -> RuntimeExecutionResult:
        from app.services.pack_runtime_service import get_pack_runtime
        from app.services.tool_registry_service import execute_tool_action, is_tool_action

        pack_runtime = get_pack_runtime(client_slug)
        merged_slots = self._merge_booking_slots(booking_state, decision.slots)
        service_name = merged_slots.get("service")
        resolved_tool_action, projected_tool_args, tool_execution_projection = (
            self._binding_tool_call_payload(decision)
        )
        semantic_contract = self._build_execution_semantic_contract(
            decision,
            booking_state=merged_slots,
            service_name=service_name,
        )
        pending_question_contract = self._build_execution_pending_question_contract(decision)
        fact_request = self._build_fact_request(decision)
        fact_plan = self._build_fact_plan(
            decision=decision,
            fact_request=fact_request,
        )
        fact_scope_violations: list[dict[str, Any]] = []

        def _fact_meta(
            base_meta: dict[str, Any] | None,
            *,
            response_text: str | None,
            resolution_source: str,
            current_semantic_contract: dict[str, Any] | None,
            fallback_fact_refs: list[str] | None = None,
            resolution_reason: str | None = None,
        ) -> dict[str, Any] | None:
            fact_result = self._build_fact_result(
                fact_plan,
                resolution_source=resolution_source,
                response_text=response_text,
                meta=base_meta,
                fallback_fact_refs=fallback_fact_refs,
                resolution_reason=resolution_reason,
            )
            if fact_result.scope_verdict == "out_of_scope":
                fact_scope_violations.append(
                    {
                        "resolution_source": resolution_source,
                        "out_of_scope_fact_refs": list(fact_result.out_of_scope_fact_refs),
                    }
                )
                return None
            return self._attach_semantic_contract_meta(
                decision,
                build_fact_contract_meta(
                    base_meta,
                    fact_request=fact_request,
                    fact_plan=fact_plan,
                    fact_result=fact_result,
                ),
                semantic_contract=current_semantic_contract,
                pending_question_contract=pending_question_contract,
            )

        if fact_request.requested_fact_refs and not fact_plan.allowed_emitted_fact_refs and fact_plan.blocked_scopes:
            blocked_meta = _fact_meta(
                {
                    "fact_fallback": True,
                    "fact_fallback_reason": "fact_scope_blocked",
                    "blocked_scopes": list(fact_plan.blocked_scopes),
                },
                response_text=None,
                resolution_source="scope_policy",
                current_semantic_contract=semantic_contract,
                resolution_reason="fact_scope_blocked",
            )
            return RuntimeExecutionResult(
                text="Я уточню это для вас.",
                tool_action=resolved_tool_action,
                tool_decision="fact_scope_blocked",
                meta=blocked_meta or {},
            )
        policy_info_refs = self._resolve_policy_info_refs(decision)
        fact_refs = set(normalize_fact_ref_list(list(fact_request.requested_fact_refs) + policy_info_refs))
        mixed_first_fact_family_refs = sorted(fact_refs & self._FIRST_FACT_FAMILY_REFS)
        mixed_first_fact_family_scope = bool(mixed_first_fact_family_refs) and bool(
            fact_refs - self._FIRST_FACT_FAMILY_REFS
        )
        unresolved_info_meta: dict[str, Any] | None = None
        if decision.intent == "master_query" or "master" in fact_refs:
            master_service = self._resolve_fact_service_query(
                decision=decision,
                service_name=service_name,
                semantic_contract=semantic_contract,
            )
            master_resolution = pack_runtime.resolve_explicit_master_intent(
                service_query=master_service,
                force_master_intent=bool(master_service),
            )
            master_reply = pack_runtime.build_master_reply_from_pack(
                message_text=None,
                resolution=master_resolution,
            )
            if master_reply and isinstance(master_reply.response, str) and master_reply.response.strip():
                master_meta = dict(master_reply.meta) if isinstance(master_reply.meta, dict) else {}
                semantic_contract = self._merge_pack_grounding_semantic_contract(
                    semantic_contract,
                    master_meta,
                )
                finalized_master_meta = _fact_meta(
                    master_meta,
                    response_text=master_reply.response.strip(),
                    resolution_source="master_pack",
                    current_semantic_contract=semantic_contract,
                    fallback_fact_refs=["master"],
                    resolution_reason=master_reply.intent or "master",
                )
                if finalized_master_meta is not None:
                    return RuntimeExecutionResult(
                        text=master_reply.response.strip(),
                        tool_action=resolved_tool_action,
                        tool_decision=master_reply.intent or "master",
                        meta=finalized_master_meta,
                    )
        if self._can_execute_tool_action(
            tool_action=resolved_tool_action,
            db=db,
            branch_id=branch_id,
        ) and is_tool_action(resolved_tool_action):
            service_query = self._resolve_fact_service_query(
                decision=decision,
                service_name=service_name,
                semantic_contract=semantic_contract,
            )
            tool_result = execute_tool_action(
                db,
                tool_action=resolved_tool_action,
                tool_args=projected_tool_args,
                conversation_id=conversation_id,
                branch_id=branch_id,
                client_slug=client_slug,
                service_query=service_query,
                info_sections_hint=list(fact_plan.allowed_info_sections),
                allowed_fact_refs=list(fact_plan.allowed_emitted_fact_refs),
                message_text=None,
                expected_reply_type=None,
                now=now,
                semantic_contract=semantic_contract,
            )
            if tool_result.handled and isinstance(tool_result.response_text, str) and tool_result.response_text.strip():
                tool_meta = dict(tool_result.decision_meta) if isinstance(tool_result.decision_meta, dict) else {}
                if tool_execution_projection:
                    tool_meta["tool_execution_projection"] = tool_execution_projection
                finalized_tool_meta = _fact_meta(
                    tool_meta,
                    response_text=tool_result.response_text.strip(),
                    resolution_source="tool_registry",
                    current_semantic_contract=semantic_contract,
                    fallback_fact_refs=[
                        str(tool_meta.get("tool_decision") or tool_result.error_code or "").strip()
                    ],
                    resolution_reason=str(tool_meta.get("tool_decision") or tool_result.error_code or "ok"),
                )
                if finalized_tool_meta is not None:
                    return RuntimeExecutionResult(
                        text=tool_result.response_text.strip(),
                        tool_action=resolved_tool_action,
                        tool_decision=str(tool_meta.get("tool_decision") or tool_result.error_code or "ok"),
                        meta=finalized_tool_meta,
                    )
        if mixed_first_fact_family_scope:
            mixed_family_meta = {
                "fact_fallback": True,
                "fact_fallback_reason": "first_fact_family_mixed_scope_unresolved",
                "fact_family_cutover": self._FIRST_FACT_FAMILY_ID,
                "family_overlap_fact_refs": mixed_first_fact_family_refs,
                "required_tool_action": "catalog.location",
            }
            if tool_execution_projection:
                mixed_family_meta["tool_execution_projection"] = tool_execution_projection
            if fact_scope_violations:
                mixed_family_meta["fact_scope_violations"] = fact_scope_violations
            unresolved_meta = _fact_meta(
                mixed_family_meta,
                response_text=None,
                resolution_source="fact_family_cutover",
                current_semantic_contract=semantic_contract,
                resolution_reason="first_fact_family_mixed_scope_unresolved",
            )
            return RuntimeExecutionResult(
                text="Я уточню это для вас.",
                tool_action=resolved_tool_action,
                tool_decision="fact_family_unresolved",
                meta=unresolved_meta or {},
            )
        explicit_pack_result = self._execute_owner_bound_pack_fact(
            decision=decision,
            pack_runtime=pack_runtime,
            client_slug=client_slug,
            tool_action=resolved_tool_action,
            service_name=service_name,
            semantic_contract=semantic_contract,
            pending_question_contract=pending_question_contract,
            fact_request=fact_request,
            fact_plan=fact_plan,
            tool_execution_projection=tool_execution_projection,
        )
        if explicit_pack_result is not None:
            return explicit_pack_result
        should_attempt_info_resolution = decision.tool_action == "info" or (
            self._has_canonical_semantic_owner(decision) and bool(policy_info_refs)
        )
        if should_attempt_info_resolution:
            unresolved_info_meta = {
                "fact_fallback": True,
                "fact_fallback_reason": "policy_info_unresolved",
                "info_ref_source": "policy_core",
                "policy_info_refs": policy_info_refs,
            }
            if resolved_tool_action == "info":
                if fact_scope_violations:
                    unresolved_info_meta["fact_scope_violations"] = fact_scope_violations
                unresolved_meta = _fact_meta(
                    unresolved_info_meta,
                    response_text=None,
                    resolution_source="policy_info_unresolved",
                    current_semantic_contract=semantic_contract,
                    resolution_reason="policy_info_unresolved",
                )
                return RuntimeExecutionResult(
                    text="Я уточню это для вас.",
                    tool_action=resolved_tool_action,
                    tool_decision="info_ref_unresolved",
                    meta=unresolved_meta or {},
                )
        if unresolved_info_meta is not None:
            if fact_scope_violations:
                unresolved_info_meta["fact_scope_violations"] = fact_scope_violations
            unresolved_meta = _fact_meta(
                unresolved_info_meta,
                response_text=None,
                resolution_source="policy_info_unresolved",
                current_semantic_contract=semantic_contract,
                resolution_reason="policy_info_unresolved",
            )
            return RuntimeExecutionResult(
                text="Я уточню это для вас.",
                tool_action=resolved_tool_action,
                tool_decision="info_ref_unresolved",
                meta=unresolved_meta or {},
            )
        unresolved_meta_payload = {
            "fact_fallback": True,
            "fact_fallback_reason": "fact_execution_unresolved",
        }
        if fact_scope_violations:
            unresolved_meta_payload["fact_scope_violations"] = fact_scope_violations
        unresolved_meta = _fact_meta(
            unresolved_meta_payload,
            response_text=None,
            resolution_source="fact_unresolved",
            current_semantic_contract=semantic_contract,
            resolution_reason="fact_execution_unresolved",
        )
        return RuntimeExecutionResult(
            text="Я уточню это для вас.",
            tool_action=resolved_tool_action,
            tool_decision="fact_unresolved",
            meta=unresolved_meta or {},
        )

    @staticmethod
    def _normalize_fact_hint(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip().casefold()
        return cleaned or None

    @staticmethod
    def _normalize_execution_text(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned or None

    @classmethod
    def _semantic_referents(cls, semantic_contract: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
        referents = semantic_contract.get("referents") if isinstance(semantic_contract, dict) else None
        return referents if isinstance(referents, dict) else {}

    @classmethod
    def _normalize_semantic_entity_refs(cls, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        cleaned: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str, str]] = set()
        for item in value:
            if not isinstance(item, dict):
                continue
            payload: dict[str, Any] = {}
            entity_id = cls._normalize_execution_text(item.get("entity_id") or item.get("id"))
            entity_type = cls._normalize_execution_text(item.get("entity_type") or item.get("type"))
            source_ref = cls._normalize_execution_text(item.get("source_ref"))
            entity_value = cls._normalize_execution_text(item.get("value") or item.get("label"))
            if entity_id:
                payload["entity_id"] = entity_id
            if entity_type:
                payload["entity_type"] = entity_type
            if source_ref:
                payload["source_ref"] = source_ref
            if entity_value:
                payload["value"] = entity_value
            confidence = item.get("confidence")
            if isinstance(confidence, (int, float)):
                payload["confidence"] = max(0.0, min(float(confidence), 1.0))
            if not payload:
                continue
            fingerprint = (
                str(payload.get("entity_id") or ""),
                str(payload.get("entity_type") or ""),
                str(payload.get("source_ref") or ""),
                str(payload.get("value") or ""),
            )
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            cleaned.append(payload)
        return cleaned

    @classmethod
    def _normalize_semantic_referents(cls, value: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(value, dict):
            return {}
        referents: dict[str, dict[str, Any]] = {}
        for referent_key in ("service", "specialist", "branch", "booking_ref", "customer"):
            raw_payload = value.get(referent_key)
            if not isinstance(raw_payload, dict):
                continue
            payload: dict[str, Any] = {}
            for source_key in ("value", "entity_id", "entity_type", "source_ref"):
                token = cls._normalize_execution_text(raw_payload.get(source_key))
                if token:
                    payload[source_key] = token
            if payload:
                referents[referent_key] = payload
        return referents

    @classmethod
    def _normalize_grounding_provenance(cls, value: Any) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            return None
        payload: dict[str, Any] = {}
        for key in ("pack_id", "entity_id", "source_ref", "resolver_id", "resolver_version"):
            token = cls._normalize_execution_text(value.get(key))
            if token:
                payload[key] = token
        confidence = value.get("confidence")
        if isinstance(confidence, (int, float)):
            payload["confidence"] = max(0.0, min(float(confidence), 1.0))
        retrieval = value.get("retrieval")
        if isinstance(retrieval, dict) and retrieval:
            payload["retrieval"] = dict(retrieval)
        return payload or None

    @classmethod
    def _pack_semantic_grounding(cls, meta: dict[str, Any] | None) -> dict[str, Any] | None:
        grounding = meta.get("semantic_grounding") if isinstance(meta, dict) else None
        source = grounding if isinstance(grounding, dict) else meta
        if not isinstance(source, dict):
            return None
        payload: dict[str, Any] = {"contract_version": "semantic_contract.v1"}
        entity_refs = cls._normalize_semantic_entity_refs(source.get("entity_refs"))
        referents = cls._normalize_semantic_referents(source.get("referents"))
        grounding_provenance = cls._normalize_grounding_provenance(
            source.get("grounding_provenance") or source.get("provenance")
        )
        if entity_refs:
            payload["entity_refs"] = entity_refs
        if referents:
            payload["referents"] = referents
        if grounding_provenance:
            payload["grounding_provenance"] = grounding_provenance
        return payload if len(payload) > 1 else None

    @classmethod
    def _merge_pack_grounding_semantic_contract(
        cls,
        semantic_contract: dict[str, Any] | None,
        pack_meta: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        grounding = cls._pack_semantic_grounding(pack_meta)
        if not grounding:
            return semantic_contract
        contract = dict(semantic_contract) if isinstance(semantic_contract, dict) else {}
        contract["contract_version"] = "semantic_contract.v1"

        merged_entity_refs = cls._normalize_semantic_entity_refs(contract.get("entity_refs"))
        merged_entity_refs.extend(
            cls._normalize_semantic_entity_refs(grounding.get("entity_refs"))
        )
        if merged_entity_refs:
            contract["entity_refs"] = cls._normalize_semantic_entity_refs(merged_entity_refs)

        merged_referents = cls._normalize_semantic_referents(contract.get("referents"))
        for referent_key, payload in cls._normalize_semantic_referents(
            grounding.get("referents")
        ).items():
            existing = merged_referents.get(referent_key)
            if not isinstance(existing, dict):
                merged_referents[referent_key] = payload
                continue
            existing_value = cls._normalize_execution_text(existing.get("value"))
            grounded_value = cls._normalize_execution_text(payload.get("value"))
            if existing_value and grounded_value and existing_value.casefold() != grounded_value.casefold():
                continue
            merged_referents[referent_key] = {**existing, **payload}
        if merged_referents:
            contract["referents"] = merged_referents

        grounding_provenance = cls._normalize_grounding_provenance(
            grounding.get("grounding_provenance")
        )
        if grounding_provenance:
            contract["grounding_provenance"] = grounding_provenance
        return contract

    @staticmethod
    def _has_canonical_semantic_owner(decision: PolicyDecision) -> bool:
        return getattr(decision, "semantic_decision", None) is not None

    @staticmethod
    def _binding_plan(decision: PolicyDecision) -> BindingPlanV1 | None:
        binding_plan = getattr(decision, "binding_plan", None)
        if isinstance(binding_plan, BindingPlanV1):
            return binding_plan
        return None

    @classmethod
    def _binding_tool_call_payload(
        cls,
        decision: PolicyDecision,
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        binding_plan = cls._binding_plan(decision)
        if (
            not isinstance(binding_plan, BindingPlanV1)
            or binding_plan.binding_outcome_type != "tool_call"
        ):
            raise ValueError("binding_tool_call_required")
        resolved_tool_action = (
            cls._normalize_fact_hint(binding_plan.selected_tool_or_workflow_ref) or "noop"
        )
        projected_tool_args = dict(binding_plan.resolved_args)
        tool_execution_projection = {
            "projection_source": "binding_plan.v1",
            "binding_id": binding_plan.binding_id,
            "tool_action": resolved_tool_action,
            **projected_tool_args,
        }
        return resolved_tool_action, projected_tool_args, tool_execution_projection

    @classmethod
    def _build_execution_semantic_enrichment(
        cls,
        semantic_contract: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(semantic_contract, dict) or not semantic_contract:
            return None
        enrichment: dict[str, Any] = {}
        referents = cls._normalize_semantic_referents(semantic_contract.get("referents"))
        if referents:
            enrichment["referents"] = deepcopy(referents)
        entity_refs = cls._normalize_semantic_entity_refs(semantic_contract.get("entity_refs"))
        if entity_refs:
            enrichment["entity_refs"] = deepcopy(entity_refs)
        grounding_provenance = cls._normalize_grounding_provenance(
            semantic_contract.get("grounding_provenance")
        )
        if grounding_provenance:
            enrichment["grounding_provenance"] = deepcopy(grounding_provenance)
        return enrichment or None

    @staticmethod
    def _semantic_entity_ref_key(payload: dict[str, Any]) -> tuple[str, str, str, str]:
        return (
            str(payload.get("entity_id") or ""),
            str(payload.get("entity_type") or ""),
            str(payload.get("source_ref") or ""),
            str(payload.get("value") or ""),
        )

    @classmethod
    def _build_owner_only_execution_semantic_enrichment(
        cls,
        decision: PolicyDecision,
        semantic_contract: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        enrichment = cls._build_execution_semantic_enrichment(semantic_contract)
        if not enrichment:
            return None
        owner_contract = TurnPlanner().canonical_semantic_contract(decision)
        if not isinstance(owner_contract, dict) or not owner_contract:
            return enrichment
        owner_enrichment = cls._build_execution_semantic_enrichment(owner_contract) or {}
        delta: dict[str, Any] = {}

        owner_referents = cls._normalize_semantic_referents(owner_enrichment.get("referents"))
        referents = cls._normalize_semantic_referents(enrichment.get("referents"))
        referent_delta = {
            referent_key: payload
            for referent_key, payload in referents.items()
            if owner_referents.get(referent_key) != payload
        }
        if referent_delta:
            delta["referents"] = deepcopy(referent_delta)

        owner_entity_refs = {
            cls._semantic_entity_ref_key(item)
            for item in cls._normalize_semantic_entity_refs(owner_enrichment.get("entity_refs"))
        }
        entity_ref_delta = [
            item
            for item in cls._normalize_semantic_entity_refs(enrichment.get("entity_refs"))
            if cls._semantic_entity_ref_key(item) not in owner_entity_refs
        ]
        if entity_ref_delta:
            delta["entity_refs"] = deepcopy(entity_ref_delta)

        grounding_provenance = cls._normalize_grounding_provenance(
            enrichment.get("grounding_provenance")
        )
        owner_grounding_provenance = cls._normalize_grounding_provenance(
            owner_enrichment.get("grounding_provenance")
        )
        if grounding_provenance and grounding_provenance != owner_grounding_provenance:
            delta["grounding_provenance"] = deepcopy(grounding_provenance)

        return delta or None

    @classmethod
    def _attach_semantic_contract_meta(
        cls,
        decision: PolicyDecision,
        meta: dict[str, Any] | None,
        *,
        semantic_contract: dict[str, Any] | None,
        pending_question_contract: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = dict(meta) if isinstance(meta, dict) else {}
        if cls._has_canonical_semantic_owner(decision):
            semantic_enrichment = cls._build_owner_only_execution_semantic_enrichment(
                decision,
                semantic_contract,
            )
            if isinstance(semantic_enrichment, dict) and semantic_enrichment:
                payload["semantic_enrichment"] = semantic_enrichment
            return payload
        if isinstance(semantic_contract, dict) and semantic_contract:
            payload["semantic_contract"] = semantic_contract
        if isinstance(pending_question_contract, dict) and pending_question_contract:
            payload["pending_question_contract"] = pending_question_contract
        return payload

    @staticmethod
    def _build_execution_pending_question_contract(
        decision: PolicyDecision,
    ) -> dict[str, Any] | None:
        dialog_state_service = DialogStateService()
        pending_question_contract = dialog_state_service.project_pending_question_contract(
            TurnPlanner().canonical_pending_question_contract(decision)
        )
        if pending_question_contract:
            return pending_question_contract
        return dialog_state_service.project_pending_question_contract(
            decision.pending_question_contract
        )

    def _build_execution_semantic_contract(
        self,
        decision: PolicyDecision,
        *,
        booking_state: dict[str, Any] | None,
        service_name: str | None = None,
    ) -> dict[str, Any] | None:
        base_contract = TurnPlanner().canonical_semantic_contract(decision) or {}
        if not base_contract:
            return None
        contract = dict(base_contract)
        contract["contract_version"] = "semantic_contract.v1"
        return contract

    def _resolve_fact_info_sections(self, fact_refs: set[str]) -> list[str] | None:
        sections: list[str] = []
        for token in fact_refs:
            normalized = self._normalize_fact_hint(token)
            if normalized in {
                "pricing",
                "promotions",
                "duration",
                "services_overview",
                "location",
                "hours",
                "parking",
                "contact",
                "master",
            }:
                sections.append(normalized)
        return sections or None

    @staticmethod
    def _build_fact_request(decision: PolicyDecision) -> FactRequestV1:
        return FactRequestV1.build_from_policy_decision(decision)

    @staticmethod
    def _build_fact_plan(
        *,
        decision: PolicyDecision,
        fact_request: FactRequestV1,
    ) -> FactPlanV1:
        return FactPlanV1.build_from_request(fact_request, decision=decision)

    @staticmethod
    def _build_fact_result(
        fact_plan: FactPlanV1,
        *,
        resolution_source: str,
        response_text: str | None,
        meta: dict[str, Any] | None,
        fallback_fact_refs: list[str] | None = None,
        resolution_reason: str | None = None,
    ) -> FactResultV1:
        return FactResultV1.build_from_runtime_payload(
            fact_plan,
            resolution_source=resolution_source,
            response_text=response_text,
            meta=meta,
            fallback_fact_refs=fallback_fact_refs,
            resolution_reason=resolution_reason,
        )

    @staticmethod
    def _can_execute_tool_action(
        *,
        tool_action: str,
        db: Any,
        branch_id: Any,
    ) -> bool:
        if db is None:
            return False
        if tool_action == "catalog.location":
            return True
        return branch_id is not None

    def _resolve_policy_info_refs(self, decision: PolicyDecision) -> list[str]:
        refs: list[str] = []
        seen: set[str] = set()

        def _remember(value: Any) -> None:
            normalized = self._normalize_fact_hint(value)
            if normalized is None or normalized in seen:
                return
            seen.add(normalized)
            refs.append(normalized)

        _remember(decision.intent)
        for item in decision.pack_refs:
            _remember(item)
        for item in decision.fact_refs:
            _remember(item)
        for item in decision.capability_refs:
            _remember(item)

        semantic_contract = TurnPlanner().canonical_semantic_contract(decision)
        if isinstance(semantic_contract, dict):
            _remember(semantic_contract.get("capability"))
        return refs

    def _execute_owner_bound_pack_fact(
        self,
        *,
        decision: PolicyDecision,
        pack_runtime: Any,
        client_slug: str | None,
        tool_action: str,
        service_name: str | None,
        semantic_contract: dict[str, Any] | None,
        pending_question_contract: dict[str, Any] | None,
        fact_request: FactRequestV1,
        fact_plan: FactPlanV1,
        tool_execution_projection: dict[str, Any] | None,
    ) -> RuntimeExecutionResult | None:
        from app.services.pack_runtime_service import ensure_resolver_meta

        requested_fact_refs = normalize_fact_ref_list(list(fact_request.requested_fact_refs))
        allowed_fact_refs = normalize_fact_ref_list(list(fact_plan.allowed_emitted_fact_refs))
        if not allowed_fact_refs:
            return None
        primary_fact_ref = next(
            (ref for ref in requested_fact_refs if ref in allowed_fact_refs),
            allowed_fact_refs[0] if len(allowed_fact_refs) == 1 else None,
        )
        if primary_fact_ref is None or primary_fact_ref in self._FIRST_FACT_FAMILY_REFS:
            return None

        service_query = self._resolve_fact_service_query(
            decision=decision,
            service_name=service_name,
            semantic_contract=semantic_contract,
        )
        service_query_source = "semantic_contract" if service_query and self._semantic_referents(semantic_contract).get("service") else "slot_state"
        reply_text: str | None = None
        resolver_intent: str | None = None
        resolver_meta: dict[str, Any] = {}
        if primary_fact_ref == "pricing":
            if not service_query:
                return None
            reply_text = pack_runtime.build_runtime_service_truth_reply(service_query)
            resolver_intent = "price_query"
            resolver_meta = {
                "service_query": service_query,
                "service_query_source": service_query_source,
                "fact_source": "truth",
                "fact_intents": ["price_query"],
                "info_sections": ["pricing"],
                "owner_fact_execution": True,
                "owner_fact_ref": primary_fact_ref,
            }
        elif primary_fact_ref in {"duration", "service_duration"}:
            if not service_query:
                return None
            reply_text = pack_runtime.build_runtime_service_duration_reply(
                service_label=service_query,
            )
            resolver_intent = "service_duration"
            resolver_meta = {
                "service_query": service_query,
                "service_query_source": service_query_source,
                "fact_source": "truth",
                "fact_intents": ["service_duration"],
                "info_sections": ["duration"],
                "duration_item": service_query,
                "owner_fact_execution": True,
                "owner_fact_ref": primary_fact_ref,
            }
        else:
            truth_slots = {"promotion_intent": "promotions"} if primary_fact_ref == "promotions" else None
            reply_text = pack_runtime.format_reply_from_truth(
                primary_fact_ref,
                truth=None,
                slots=truth_slots,
            )
            resolver_intent = primary_fact_ref
            resolver_meta = {
                "fact_source": "truth",
                "fact_intents": [primary_fact_ref],
                "info_sections": [primary_fact_ref],
                "info_ref_execution": True,
                "info_ref_source": "policy_core",
                "owner_fact_execution": True,
                "owner_fact_ref": primary_fact_ref,
            }

        normalized_reply = self._normalize_execution_text(reply_text)
        if normalized_reply is None or resolver_intent is None:
            return None

        pack_meta = ensure_resolver_meta(
            resolver_meta,
            action="reply",
            intent=resolver_intent,
            resolver_id="pack_runtime.owner_fact",
            client_slug=client_slug,
        )
        if tool_execution_projection:
            pack_meta["tool_execution_projection"] = tool_execution_projection
        enriched_semantic_contract = self._merge_pack_grounding_semantic_contract(
            semantic_contract,
            pack_meta,
        )
        fact_result = self._build_fact_result(
            fact_plan,
            resolution_source="owner_bound_pack_runtime",
            response_text=normalized_reply,
            meta=pack_meta,
            fallback_fact_refs=[primary_fact_ref],
            resolution_reason=resolver_intent,
        )
        if fact_result.scope_verdict == "out_of_scope":
            return None
        finalized_meta = self._attach_semantic_contract_meta(
            decision,
            build_fact_contract_meta(
                pack_meta,
                fact_request=fact_request,
                fact_plan=fact_plan,
                fact_result=fact_result,
            ),
            semantic_contract=enriched_semantic_contract,
            pending_question_contract=pending_question_contract,
        )
        return RuntimeExecutionResult(
            text=normalized_reply,
            tool_action=tool_action,
            tool_decision=resolver_intent,
            meta=finalized_meta,
        )

    def _resolve_fact_service_query(
        self,
        *,
        decision: PolicyDecision,
        service_name: str | None,
        semantic_contract: dict[str, Any] | None = None,
    ) -> str | None:
        referents = self._semantic_referents(semantic_contract)
        service_payload = referents.get("service") if isinstance(referents.get("service"), dict) else {}
        projected_referent = self._normalize_execution_text(service_payload.get("value"))
        if projected_referent:
            return projected_referent
        return None

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
        semantic_contract = self._build_execution_semantic_contract(
            decision,
            booking_state=merged_slots,
            service_name=merged_slots.get("service"),
        )
        pending_question_contract = self._build_execution_pending_question_contract(decision)
        missing_slot = self._first_missing_booking_slot(merged_slots)
        if missing_slot is not None:
            prompt = self._BOOKING_PROMPTS.get(missing_slot, self._BOOKING_PROMPTS["service"])
            return RuntimeExecutionResult(
                text=prompt,
                tool_action="collect",
                tool_decision=missing_slot,
                meta=self._attach_semantic_contract_meta(
                    decision,
                    {"slot_values": merged_slots, "booking_incomplete": True},
                    semantic_contract=semantic_contract,
                    pending_question_contract=pending_question_contract,
                ),
            )

        if branch_id is None:
            return RuntimeExecutionResult(
                text="Чтобы завершить запись, мне нужен активный филиал. Передаю диалог менеджеру.",
                tool_action="handoff",
                tool_decision="branch_missing",
                meta=self._attach_semantic_contract_meta(
                    decision,
                    {"slot_values": merged_slots},
                    semantic_contract=semantic_contract,
                    pending_question_contract=pending_question_contract,
                ),
                request_handoff=True,
            )

        start_at = self._parse_booking_datetime(merged_slots.get("datetime"), now=now)
        if start_at is None:
            return RuntimeExecutionResult(
                text=self._BOOKING_PROMPTS["datetime"],
                tool_action="collect",
                tool_decision="datetime_invalid",
                meta=self._attach_semantic_contract_meta(
                    decision,
                    {"slot_values": merged_slots, "booking_incomplete": True},
                    semantic_contract=semantic_contract,
                    pending_question_contract=pending_question_contract,
                ),
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
                meta=self._attach_semantic_contract_meta(
                    decision,
                    {
                    "slot_values": merged_slots,
                    "next_slot": "datetime",
                    "booking_incomplete": True,
                    },
                    semantic_contract=semantic_contract,
                    pending_question_contract=pending_question_contract,
                ),
            )
        confirmation_text = (
            f"Готово, записал вас на {merged_slots['service']} "
            f"на {start_at.astimezone(start_at.tzinfo).strftime('%d.%m %H:%M')}."
        )
        return RuntimeExecutionResult(
            text=confirmation_text,
            tool_action="calendar.book_slot",
            tool_decision="ok",
            meta=self._attach_semantic_contract_meta(
                decision,
                {
                "slot_values": merged_slots,
                "appointment_id": str(appointment.id),
                "service": merged_slots.get("service"),
                "datetime": merged_slots.get("datetime"),
                },
                semantic_contract=semantic_contract,
                pending_question_contract=pending_question_contract,
            ),
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
        decision: PolicyDecision | None,
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
            outcome="FACT",
        )

    def build_degrade_boundary_turn_result(
        self,
        *,
        decision: PolicyDecision | None,
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
            outcome="HANDOFF",
        )

    def build_block_boundary_artifact(
        self,
        *,
        decision: PolicyDecision | None,
        dialog_state: DialogState,
        boundary_override: BoundaryOverride,
        tool_action: str,
        text: str = "",
        ignored: bool = False,
        intent: str | None = None,
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
            intent=intent,
            meta=meta,
        )
        return BoundaryExecutionArtifact(turn_result=turn_result, turn_outcome=turn_outcome)

    def build_degrade_boundary_artifact(
        self,
        *,
        decision: PolicyDecision | None,
        dialog_state: DialogState,
        boundary_override: BoundaryOverride,
        text: str,
        transport_status: str,
        transport_reason: str | None,
        tool_action: str = "handoff",
        tool_decision: str = "runtime_exception",
        intent: str | None = None,
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
            intent=intent,
            meta=meta,
        )
        return BoundaryExecutionArtifact(turn_result=turn_result, turn_outcome=turn_outcome)

    def build_block_boundary_artifact_from_request(
        self,
        *,
        request: BlockBoundaryRequest,
    ) -> BoundaryExecutionArtifact:
        boundary_override = BoundaryValidator().build_block_override(
            reason_code=request.reason_code,
            trace_message=request.trace_message,
            replan_hints=list(request.replan_hints),
            public_message=request.public_message,
            meta={
                "control_label": request.intent,
                **dict(request.override_meta),
            },
        )
        dialog_state = DialogStateService().build_blocked_state(
            reason_code=request.reason_code,
            interaction_owner=request.interaction_owner,
            interaction_target=request.interaction_target,
            interaction_relation=request.interaction_relation,
        )
        outcome_meta = {"control_label": request.intent}
        outcome_meta.update(dict(request.outcome_meta))
        return self.build_block_boundary_artifact(
            decision=None,
            dialog_state=dialog_state,
            boundary_override=boundary_override,
            tool_action=request.tool_action,
            text=request.public_message,
            ignored=request.ignored,
            intent=request.intent,
            meta=outcome_meta,
        )

    def build_degrade_boundary_artifact_from_request(
        self,
        *,
        request: DegradeBoundaryRequest,
    ) -> BoundaryExecutionArtifact:
        boundary_override = BoundaryValidator().build_degrade_override(
            reason_code=request.reason_code,
            public_message=request.public_message,
            trace_message=request.trace_message,
            meta={
                "control_label": request.intent,
                **dict(request.override_meta),
            },
        )
        dialog_state = DialogStateService().build_degraded_state(
            reason_code=request.reason_code,
            interaction_owner=request.interaction_owner,
            interaction_target=request.interaction_target,
            interaction_relation=request.interaction_relation,
        )
        outcome_meta = {"control_label": request.intent}
        outcome_meta.update(dict(request.outcome_meta))
        return self.build_degrade_boundary_artifact(
            decision=None,
            dialog_state=dialog_state,
            boundary_override=boundary_override,
            text=request.public_message,
            transport_status=request.transport_status,
            transport_reason=request.transport_reason,
            tool_action=request.tool_action,
            tool_decision=request.tool_decision,
            intent=request.intent,
            meta=outcome_meta,
        )

__all__ = [
    "BlockBoundaryRequest",
    "BoundaryExecutionArtifact",
    "DegradeBoundaryRequest",
    "RuntimeExecutionResult",
    "ToolOutcome",
    "ToolStatus",
    "TurnContractStatus",
    "TurnExecutor",
    "TurnObservability",
    "TurnResult",
    "TurnTrace",
]
