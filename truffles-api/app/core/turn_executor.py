from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import Any, Literal, NamedTuple
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.boundary_validator import BoundaryOverride, BoundaryValidator
from app.core.dialog_state_service import DialogState, DialogStateService
from app.core.response_realizer import ReplyEnvelope, ResponseRealizer
from app.core.turn_planner import DecisionOutcome, PolicyDecision, TurnPlanner
from app.schemas.intent import validate_tool_args_shape
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


class TurnExecutor:
    """Assembles the typed turn result while runtime cutover is still pending."""

    _POLICY_INFO_TOOL_ACTION_MAP = {
        "pricing": "catalog.service_query",
        "duration": "catalog.service_query",
        "promotions": "catalog.service_query",
        "services_overview": "catalog.service_query",
        "location": "catalog.location",
        "hours": "catalog.location",
        "parking": "catalog.location",
    }
    _DIRECT_INFO_TRUTH_REFS = {
        "location",
        "hours",
        "parking",
        "promotions",
        "services_overview",
    }
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
        if decision.outcome == "HANDOFF":
            return RuntimeExecutionResult(
                text="Передаю диалог менеджеру. Он скоро подключится.",
                tool_action="handoff",
                tool_decision="pending",
                meta={"handoff_requested": True},
                request_handoff=True,
            )
        if decision.tool_action == "calendar.book_slot":
            return self._execute_booking_confirmation(
                decision,
                db=db,
                branch_id=branch_id,
                booking_state=merged_booking,
                user_name=user_name,
                user_phone=user_phone,
                now=now,
            )
        if decision.outcome == "FACT":
            return self._execute_fact(
                decision,
                db=db,
                message_text=message_text,
                client_slug=client_slug,
                branch_id=branch_id,
                booking_state=merged_booking,
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
        semantic_contract = self._build_execution_semantic_contract(
            decision,
            booking_state=merged_slots,
        )
        pending_question_contract = self._build_execution_pending_question_contract(decision)
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
            candidate_datetime = self._normalize_booking_slot(
                decision.meta.get("alternate_datetime")
            ) if isinstance(decision.meta, dict) else None
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
    ) -> RuntimeExecutionResult:
        from app.services.pack_runtime_service import (
            build_master_reply_from_pack,
            format_reply_from_truth,
            get_pack_decision,
            resolve_master_intent,
        )
        from app.services.tool_registry_service import execute_tool_action, is_tool_action

        query_text = (message_text or "").strip()
        merged_slots = self._merge_booking_slots(booking_state, decision.slots)
        service_name = merged_slots.get("service")
        semantic_contract = self._build_execution_semantic_contract(
            decision,
            booking_state=merged_slots,
            service_name=service_name,
        )
        pending_question_contract = self._build_execution_pending_question_contract(decision)
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
                meta=self._attach_semantic_contract_meta(
                    {"booking_verification_prompt": True},
                    semantic_contract=semantic_contract,
                    pending_question_contract=pending_question_contract,
                ),
            )
        policy_info_refs = self._resolve_policy_info_refs(decision)
        fact_refs = {
            str(item).strip().casefold()
            for item in (
                list(decision.pack_refs)
                + list(decision.fact_refs)
                + list(decision.capability_refs)
                + policy_info_refs
            )
            if isinstance(item, str) and item.strip()
        }
        unresolved_info_meta: dict[str, Any] | None = None
        if decision.intent == "master_query" or "master" in fact_refs:
            master_service = self._resolve_fact_service_query(
                decision=decision,
                service_name=service_name,
                semantic_contract=semantic_contract,
            )
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
                semantic_contract = self._merge_pack_grounding_semantic_contract(
                    semantic_contract,
                    master_meta,
                )
                return RuntimeExecutionResult(
                    text=master_reply.response.strip(),
                    tool_action=decision.tool_action,
                    tool_decision=master_reply.intent or "master",
                    meta=self._attach_semantic_contract_meta(
                        master_meta,
                        semantic_contract=semantic_contract,
                        pending_question_contract=pending_question_contract,
                    ),
                )
        resolved_tool_action = self._resolve_fact_tool_action(
            decision=decision,
            policy_info_refs=policy_info_refs,
        )
        projected_tool_args, tool_execution_projection = self._build_tool_execution_projection(
            decision=decision,
            semantic_contract=semantic_contract,
            service_name=service_name,
            tool_action=resolved_tool_action,
        )
        if db is not None and branch_id is not None and is_tool_action(resolved_tool_action):
            service_query = self._resolve_fact_service_query(
                decision=decision,
                service_name=service_name,
                semantic_contract=semantic_contract,
            )
            tool_result = execute_tool_action(
                db,
                tool_action=resolved_tool_action,
                tool_args=projected_tool_args,
                conversation_id=None,
                branch_id=branch_id,
                client_slug=client_slug,
                service_query=service_query,
                info_sections_hint=self._resolve_fact_info_sections(fact_refs),
                message_text=query_text,
                expected_reply_type=None,
                now=now,
                semantic_contract=semantic_contract,
            )
            if tool_result.handled and isinstance(tool_result.response_text, str) and tool_result.response_text.strip():
                tool_meta = dict(tool_result.decision_meta) if isinstance(tool_result.decision_meta, dict) else {}
                if tool_execution_projection:
                    tool_meta["tool_execution_projection"] = tool_execution_projection
                tool_meta = self._attach_semantic_contract_meta(
                    tool_meta,
                    semantic_contract=semantic_contract,
                    pending_question_contract=pending_question_contract,
                )
                return RuntimeExecutionResult(
                    text=tool_result.response_text.strip(),
                    tool_action=resolved_tool_action,
                    tool_decision=str(tool_meta.get("tool_decision") or tool_result.error_code or "ok"),
                    meta=tool_meta,
                )
        if decision.tool_action == "info":
            direct_info_ref, direct_info_reply = self._build_direct_policy_info_reply(
                policy_info_refs=policy_info_refs,
                client_slug=client_slug,
                format_reply_from_truth=format_reply_from_truth,
            )
            if direct_info_ref and direct_info_reply:
                direct_meta: dict[str, Any] = {
                    "info_sections": [direct_info_ref],
                    "info_ref_execution": True,
                    "info_ref_source": "policy_core",
                }
                if tool_execution_projection:
                    direct_meta["tool_execution_projection"] = tool_execution_projection
                return RuntimeExecutionResult(
                    text=direct_info_reply,
                    tool_action=resolved_tool_action,
                    tool_decision=direct_info_ref,
                    meta=self._attach_semantic_contract_meta(
                        direct_meta,
                        semantic_contract=semantic_contract,
                        pending_question_contract=pending_question_contract,
                    ),
                )
            unresolved_info_meta = {
                "fact_fallback": True,
                "fact_fallback_reason": "policy_info_unresolved",
                "info_ref_source": "policy_core",
                "policy_info_refs": policy_info_refs,
            }
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
            semantic_contract = self._merge_pack_grounding_semantic_contract(
                semantic_contract,
                pack_meta,
            )
            return RuntimeExecutionResult(
                text=pack_decision.response.strip(),
                tool_action=decision.tool_action,
                tool_decision=pack_decision.intent or pack_decision.action,
                meta=self._attach_semantic_contract_meta(
                    pack_meta,
                    semantic_contract=semantic_contract,
                    pending_question_contract=pending_question_contract,
                ),
            )
        if unresolved_info_meta is not None:
            return RuntimeExecutionResult(
                text="Я уточню это для вас.",
                tool_action=resolved_tool_action,
                tool_decision="info_ref_unresolved",
                meta=self._attach_semantic_contract_meta(
                    unresolved_info_meta,
                    semantic_contract=semantic_contract,
                    pending_question_contract=pending_question_contract,
                ),
            )
        fallback_text = (message_text or "").strip() or "Я уточню это для вас."
        return RuntimeExecutionResult(
            text=fallback_text,
            tool_action=decision.tool_action,
            tool_decision="passthrough",
            meta=self._attach_semantic_contract_meta(
                {"fact_fallback": True},
                semantic_contract=semantic_contract,
                pending_question_contract=pending_question_contract,
            ),
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
    def _looks_like_uuid(cls, value: Any) -> bool:
        token = cls._normalize_execution_text(value)
        if token is None:
            return False
        try:
            UUID(token)
        except (ValueError, TypeError):
            return False
        return True

    @classmethod
    def _semantic_referents(cls, semantic_contract: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
        referents = semantic_contract.get("referents") if isinstance(semantic_contract, dict) else None
        return referents if isinstance(referents, dict) else {}

    def _build_tool_execution_projection(
        self,
        *,
        decision: PolicyDecision,
        semantic_contract: dict[str, Any] | None,
        service_name: str | None = None,
        tool_action: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        projected_args: dict[str, Any] = {}
        referents = self._semantic_referents(semantic_contract)
        resolved_tool_action = self._normalize_fact_hint(tool_action) or self._normalize_fact_hint(
            decision.tool_action
        )

        service_payload = referents.get("service") if isinstance(referents.get("service"), dict) else {}
        projected_service = self._normalize_execution_text(
            service_payload.get("value")
            or service_name
        )
        if projected_service and resolved_tool_action in {
            "calendar.list_slots",
            "calendar.book_slot",
            "catalog.service_query",
            "catalog.portfolio",
        }:
            projected_args["service_query"] = projected_service

        specialist_payload = (
            referents.get("specialist")
            if isinstance(referents.get("specialist"), dict)
            else {}
        )
        projected_specialist_name = self._normalize_execution_text(
            specialist_payload.get("value")
        )
        if projected_specialist_name and resolved_tool_action in {
            "calendar.list_slots",
            "calendar.book_slot",
        }:
            projected_args["specialist_name"] = projected_specialist_name

        projected_specialist_id = self._normalize_execution_text(
            specialist_payload.get("entity_id")
        )
        if (
            projected_specialist_id
            and resolved_tool_action in {"calendar.list_slots", "calendar.book_slot"}
            and self._looks_like_uuid(projected_specialist_id)
        ):
            projected_args["specialist_id"] = projected_specialist_id
        else:
            projected_args.pop("specialist_id", None)

        booking_ref_payload = (
            referents.get("booking_ref")
            if isinstance(referents.get("booking_ref"), dict)
            else {}
        )
        projected_booking_id = self._normalize_execution_text(
            booking_ref_payload.get("entity_id") or booking_ref_payload.get("value")
        )
        if (
            projected_booking_id
            and resolved_tool_action in {"calendar.get_booking", "calendar.reschedule", "calendar.cancel"}
            and self._looks_like_uuid(projected_booking_id)
        ):
            projected_args["appointment_id"] = projected_booking_id

        projected_args = self._sanitize_projected_tool_args(
            tool_action=resolved_tool_action,
            projected_args=projected_args,
        )
        projection: dict[str, Any] = {"projection_source": "semantic_contract"}
        for key in ("service_query", "specialist_name", "specialist_id", "appointment_id"):
            value = projected_args.get(key)
            if isinstance(value, str) and value.strip():
                projection[key] = value.strip()
        if len(projection) == 1:
            return projected_args, {}
        return projected_args, projection

    @staticmethod
    def _sanitize_projected_tool_args(
        *,
        tool_action: str | None,
        projected_args: dict[str, Any],
    ) -> dict[str, Any]:
        if not projected_args:
            return {}
        cleaned_args = dict(projected_args)
        while True:
            normalized_args, error = validate_tool_args_shape(
                tool_action=tool_action,
                tool_args=cleaned_args,
            )
            if error is None:
                return normalized_args or {}
            if not error.startswith("tool_args_unknown_field:"):
                return cleaned_args
            unknown_key = error.split(":", 1)[1].strip()
            if not unknown_key or unknown_key not in cleaned_args:
                return cleaned_args
            cleaned_args.pop(unknown_key, None)

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
    def _attach_semantic_contract_meta(
        meta: dict[str, Any] | None,
        *,
        semantic_contract: dict[str, Any] | None,
        pending_question_contract: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = dict(meta) if isinstance(meta, dict) else {}
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
        frame_pending_question_contract = dialog_state_service._pending_question_from_frame(
            decision.semantic_frame
        )
        if isinstance(frame_pending_question_contract, dict):
            return dialog_state_service.project_pending_question_contract(
                frame_pending_question_contract,
                expected_reply_type=(
                    None
                    if frame_pending_question_contract.get("expected_reply_type")
                    else decision.pending_question_contract.expected_reply_type
                ),
                expected_reply_reason=(
                    None
                    if frame_pending_question_contract.get("reason")
                    else decision.pending_question_contract.reason
                ),
            )
        return dialog_state_service.project_pending_question_contract(
            decision.pending_question_contract,
        )

    def _build_execution_semantic_contract(
        self,
        decision: PolicyDecision,
        *,
        booking_state: dict[str, Any] | None,
        service_name: str | None = None,
    ) -> dict[str, Any] | None:
        base_contract = DialogStateService()._semantic_contract_from_frame(
            decision.semantic_frame
        ) or (
            dict(decision.meta.get("semantic_contract"))
            if isinstance(decision.meta.get("semantic_contract"), dict)
            else {}
        )
        if not base_contract:
            return None
        contract = dict(base_contract)
        contract["contract_version"] = "semantic_contract.v1"
        referents = dict(contract.get("referents") or {})

        def _remember(
            referent_key: str,
            *,
            value: Any = None,
            entity_type: str | None = None,
            source_ref: str | None = None,
        ) -> None:
            if referent_key not in {"service", "specialist", "branch", "booking_ref", "customer"}:
                return
            payload = dict(referents.get(referent_key) or {})
            normalized_value = self._normalize_execution_text(value)
            if normalized_value:
                payload["value"] = normalized_value
            has_identity = bool(
                self._normalize_execution_text(payload.get("value"))
                or self._normalize_execution_text(payload.get("entity_id"))
            )
            if entity_type and has_identity:
                payload.setdefault("entity_type", entity_type)
            if source_ref and has_identity:
                payload.setdefault("source_ref", source_ref)
            if has_identity:
                referents[referent_key] = payload

        if isinstance(contract.get("entity_refs"), list):
            for row in contract["entity_refs"]:
                if not isinstance(row, dict):
                    continue
                entity_type = self._normalize_fact_hint(row.get("entity_type"))
                referent_key = {
                    "service": "service",
                    "specialist": "specialist",
                    "branch": "branch",
                    "booking": "booking_ref",
                    "booking_ref": "booking_ref",
                    "customer": "customer",
                }.get(entity_type or "")
                if not referent_key:
                    continue
                _remember(
                    referent_key,
                    value=row.get("value") or row.get("entity_id"),
                    entity_type=entity_type,
                    source_ref=row.get("source_ref"),
                )
                if isinstance(row.get("entity_id"), str) and row.get("entity_id").strip():
                    referents.setdefault(referent_key, {})["entity_id"] = row["entity_id"].strip()

        if isinstance(booking_state, dict):
            _remember("service", value=booking_state.get("service"), entity_type="service", source_ref="booking_state")
            _remember(
                "specialist",
                value=booking_state.get("specialist_name") or booking_state.get("specialist_id"),
                entity_type="specialist",
                source_ref="booking_state",
            )
            _remember("customer", value=booking_state.get("name"), entity_type="customer", source_ref="booking_state")
            _remember(
                "booking_ref",
                value=booking_state.get("appointment_id") or booking_state.get("reference_id"),
                entity_type="booking",
                source_ref="booking_state",
            )
        if "service" not in referents and isinstance(service_name, str) and service_name.strip():
            _remember("service", value=service_name, entity_type="service", source_ref="service_query")
        if referents:
            contract["referents"] = referents
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

        semantic_contract = decision.meta.get("semantic_contract") if isinstance(decision.meta, dict) else None
        if isinstance(semantic_contract, dict):
            _remember(semantic_contract.get("capability"))
        return refs

    def _resolve_fact_tool_action(
        self,
        *,
        decision: PolicyDecision,
        policy_info_refs: list[str],
    ) -> str:
        if decision.tool_action != "info":
            return decision.tool_action
        for info_ref in policy_info_refs:
            projected = self._POLICY_INFO_TOOL_ACTION_MAP.get(info_ref)
            if projected:
                return projected
        return decision.tool_action

    def _build_direct_policy_info_reply(
        self,
        *,
        policy_info_refs: list[str],
        client_slug: str | None,
        format_reply_from_truth: Any,
    ) -> tuple[str | None, str | None]:
        for info_ref in policy_info_refs:
            if info_ref not in self._DIRECT_INFO_TRUTH_REFS:
                continue
            reply = format_reply_from_truth(info_ref, client_slug=client_slug)
            if isinstance(reply, str) and reply.strip():
                return info_ref, reply.strip()
        return None, None

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
        if isinstance(service_name, str) and service_name.strip():
            return service_name.strip()
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

__all__ = [
    "BlockBoundaryRequest",
    "BoundaryExecutionArtifact",
    "DegradeBoundaryRequest",
    "OwnerExecutionArtifact",
    "OwnerCutoverAction",
    "RuntimeExecutionResult",
    "ToolOutcome",
    "ToolStatus",
    "TurnContractStatus",
    "TurnExecutor",
    "TurnObservability",
    "TurnResult",
    "TurnTrace",
]
