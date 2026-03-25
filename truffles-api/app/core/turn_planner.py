from __future__ import annotations

import re
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DecisionOutcome = Literal["FACT", "COLLECT", "HANDOFF"]

_DEFAULT_INFO_REFS = [
    "pricing",
    "hours",
    "duration",
    "location",
    "parking",
    "promotions",
    "master",
    "contact",
]
_PLANNER_SLOT_ALIASES = {
    "service_query": "service",
    "time": "datetime",
    "date": "datetime",
    "datetime": "datetime",
    "customer_name": "name",
    "phone_number": "phone",
}


class InteractionContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner: str
    target: str | None = None
    relation: str | None = None


class PendingQuestionContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_reply_type: str | None = None
    pending_question_target: str | None = None
    active_question_relation: str | None = None
    next_question: str | None = None
    open_questions: list[str] = Field(default_factory=list)


class PolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "policy_decision.v1"
    outcome: DecisionOutcome
    action: str
    intent: str
    source: str = "policy_core"
    tool_action: str
    tool_args: dict[str, Any] = Field(default_factory=dict)
    slots: dict[str, str] = Field(default_factory=dict)
    pack_refs: list[str] = Field(default_factory=list)
    fact_refs: list[str] = Field(default_factory=list)
    capability_refs: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)
    interaction: InteractionContract
    pending_question_contract: PendingQuestionContract = Field(default_factory=PendingQuestionContract)
    meta: dict[str, Any] = Field(default_factory=dict)


class InboundTurnInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message_text: str | None = None
    message_type: str = "text"
    has_media: bool = False

    @field_validator("message_text", mode="before")
    @classmethod
    def _normalize_message_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        cleaned = value.strip()
        return cleaned or None

    @field_validator("message_type", mode="before")
    @classmethod
    def _normalize_message_type(cls, value: Any) -> str:
        if value is None:
            return "text"
        if not isinstance(value, str):
            value = str(value)
        cleaned = value.strip().lower()
        return cleaned or "text"

    def is_empty_non_media(self) -> bool:
        return not self.has_media and self.message_text is None

    def media_placeholder(self) -> str | None:
        if not self.has_media:
            return None
        label = self.message_type or "media"
        return f"[{label}]"

    def normalized_message_text(self, *, media_caption: str | None = None) -> str | None:
        if isinstance(media_caption, str):
            cleaned_caption = media_caption.strip()
            if cleaned_caption:
                return cleaned_caption
        if self.message_text is not None:
            return self.message_text
        return self.media_placeholder()


class TurnPlanner:
    """Typed seam for the future policy-core planner cutover."""

    _ACTION_TO_OUTCOME: dict[str, DecisionOutcome] = {
        "fact": "FACT",
        "collect": "COLLECT",
        "handoff": "HANDOFF",
    }

    def coerce(self, payload: dict[str, Any] | PolicyDecision) -> PolicyDecision:
        if isinstance(payload, PolicyDecision):
            return payload
        return PolicyDecision.model_validate(payload)

    def coerce_inbound(self, payload: dict[str, Any] | InboundTurnInput) -> InboundTurnInput:
        if isinstance(payload, InboundTurnInput):
            return payload
        return InboundTurnInput.model_validate(payload)

    def plan(
        self,
        *,
        message_text: str | None,
        client_slug: str | None,
        expected_reply_type: str | None,
        expected_reply_reason: str | None,
        current_goal: str | None,
        booking_state: dict[str, Any] | None,
        memory_summary: str | None = None,
        memory_profile: dict[str, Any] | None = None,
        timing_context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        from app.core.intent_routing import (
            detect_intent_routing_primitives,
            detect_policy_core_route_snapshot,
        )
        from app.services.booking_signal_service import has_pending_time_question_marker
        from app.services.consult_pack_service import load_consult_playbook
        from app.services.info_signal_service import (
            detect_booking_verification_mode,
            signal_any_match,
        )
        from app.services.intent_service import interpret_expected_reply, route_llm_policy_core
        from app.services.pack_runtime_service import _normalize_text, get_pack_service_hint

        normalized_message = self._normalize_token(message_text)
        if not normalized_message:
            return self.build_preflight_reject(
                reason_code="empty_message",
                action="reject",
                intent="empty_message",
                interaction_owner="turn_planner_preflight",
            )

        normalized_booking_state = self._normalize_booking_state(booking_state)
        consult_refs = self._load_consult_refs(load_consult_playbook, client_slug)
        time_question_contract_override = self._build_expected_time_question_contract_override(
            message_text=normalized_message,
            client_slug=client_slug,
            expected_reply_type=expected_reply_type,
            current_goal=current_goal,
        )
        if time_question_contract_override is not None:
            return time_question_contract_override
        booking_interrupt_override = self._build_active_booking_info_interrupt_override(
            message_text=normalized_message,
            client_slug=client_slug,
            expected_reply_type=expected_reply_type,
            expected_reply_reason=expected_reply_reason,
            current_goal=current_goal,
            normalized_booking_state=normalized_booking_state,
            detect_intent_routing_primitives_fn=detect_intent_routing_primitives,
            detect_policy_core_route_snapshot_fn=detect_policy_core_route_snapshot,
        )
        if booking_interrupt_override is not None:
            return booking_interrupt_override
        policy_result = route_llm_policy_core(
            normalized_message,
            expected_reply_type=expected_reply_type,
            current_goal=current_goal,
            slot_state=normalized_booking_state,
            info_refs=list(_DEFAULT_INFO_REFS),
            consult_refs=consult_refs,
            memory_summary=memory_summary,
            memory_profile=memory_profile,
            client_slug=client_slug,
            timing_context=timing_context,
        )
        payload = policy_result.get("payload") if isinstance(policy_result, dict) else None
        if isinstance(payload, dict):
            policy_decision = self._build_policy_core_decision(
                payload,
                current_goal=current_goal,
                expected_reply_type=expected_reply_type,
            )
            policy_decision = self._recover_booking_verification_contract(
                decision=policy_decision,
                message_text=normalized_message,
                detect_booking_verification_mode_fn=detect_booking_verification_mode,
            )
            return self._rescue_expected_reply_contract(
                decision=policy_decision,
                message_text=normalized_message,
                client_slug=client_slug,
                expected_reply_type=expected_reply_type,
                current_goal=current_goal,
                normalized_booking_state=normalized_booking_state,
                interpret_expected_reply_fn=interpret_expected_reply,
            )

        fallback_decision = self._build_expected_reply_fallback(
            message_text=normalized_message,
            client_slug=client_slug,
            expected_reply_type=expected_reply_type,
            current_goal=current_goal,
            normalized_booking_state=normalized_booking_state,
            interpret_expected_reply_fn=interpret_expected_reply,
        )
        if fallback_decision is not None:
            return fallback_decision

        if (
            current_goal == "booking"
            and expected_reply_type == "time"
            and has_pending_time_question_marker(_normalize_text(normalized_message))
        ):
            return self.build_from_policy_override(
                {
                    "action": "collect",
                    "intent": "booking",
                    "tool_action": "collect",
                    "slots": {},
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                    "goal": "booking",
                    "reason": "pending_time_guidance_fallback",
                },
                interaction_owner="turn_planner_fallback",
                interaction_relation="ask_about_requested_slot",
                source="turn_planner_fallback",
            )

        routing_fallback = self._build_intent_routing_fallback(
            message_text=normalized_message,
            client_slug=client_slug,
            expected_reply_type=expected_reply_type,
            expected_reply_reason=expected_reply_reason,
            current_goal=current_goal,
            normalized_booking_state=normalized_booking_state,
            detect_intent_routing_primitives_fn=detect_intent_routing_primitives,
            detect_policy_core_route_snapshot_fn=detect_policy_core_route_snapshot,
        )
        if routing_fallback is not None:
            return routing_fallback

        service_hint = get_pack_service_hint(normalized_message, client_slug=client_slug)
        booking_signal = signal_any_match(
            normalized_message.casefold(),
            client_slug,
            "booking_request",
            "booking_keywords",
        )
        if service_hint and current_goal == "booking":
            next_slot = self._select_missing_booking_slot(
                {**normalized_booking_state, "service": service_hint},
                expected_reply_type=expected_reply_type,
            )
            return self.build_from_policy_override(
                {
                    "action": "collect",
                    "intent": "booking",
                    "tool_action": "collect",
                    "slots": {"service": service_hint},
                    "next_question": next_slot or "datetime",
                    "open_questions": [next_slot or "datetime"],
                    "goal": "booking",
                    "reason": "service_hint_fallback",
                },
                interaction_owner="turn_planner_fallback",
                interaction_relation="fill_requested_slot",
                source="turn_planner_fallback",
            )
        if booking_signal:
            merged_slots = dict(normalized_booking_state)
            if service_hint:
                merged_slots["service"] = service_hint
            next_slot = self._select_missing_booking_slot(
                merged_slots,
                expected_reply_type=expected_reply_type,
            )
            tool_action = "calendar.book_slot" if next_slot is None else "collect"
            slot_payload = {"service": service_hint} if service_hint else {}
            return self.build_from_policy_override(
                {
                    "action": "collect",
                    "intent": "booking",
                    "tool_action": tool_action,
                    "slots": slot_payload,
                    "next_question": next_slot,
                    "open_questions": [next_slot] if next_slot else [],
                    "goal": "booking",
                    "reason": "booking_signal_fallback",
                },
                interaction_owner="turn_planner_fallback",
                interaction_relation="fill_requested_slot",
                source="turn_planner_fallback",
            )

        degrade_reason = self._normalize_token(
            policy_result.get("error") if isinstance(policy_result, dict) else None
        ) or "policy_core_unavailable"
        return self.build_controlled_degrade(
            reason_code=f"planner:{degrade_reason}",
            action="handoff",
            intent="planner_degrade",
            tool_action="handoff",
            interaction_owner="turn_planner_degrade",
        )

    def build_from_policy_override(
        self,
        payload: dict[str, Any],
        *,
        interaction_owner: str,
        interaction_relation: str | None = None,
        source: str = "policy_core",
    ) -> PolicyDecision:
        action = self._normalize_token(payload.get("action")) or "handoff"
        intent = self._normalize_token(payload.get("intent")) or "other"
        tool_action = self._normalize_tool_action(payload.get("tool_action"))
        outcome = self._ACTION_TO_OUTCOME.get(action)
        if outcome is None:
            raise ValueError(f"unsupported_policy_action:{action}")
        relation = interaction_relation or self._normalize_token(
            payload.get("active_question_relation")
        )
        capability = self._normalize_token(payload.get("capability"))
        pending_question = PendingQuestionContract(
            expected_reply_type=self._normalize_token(payload.get("expected_reply_type")),
            pending_question_target=self._normalize_token(payload.get("pending_question_target")),
            active_question_relation=self._normalize_token(payload.get("active_question_relation")),
            next_question=self._normalize_token(payload.get("next_question")),
            open_questions=self._normalize_list(payload.get("open_questions")),
        )
        meta = {
            "planner_source": "turn_planner",
            "synthetic_policy_decision": True,
        }
        for key in (
            "reason",
            "goal",
            "normalized_text",
            "needs_manager",
            "confidence",
            "resolver_id",
            "resolver_version",
            "subject_kind",
            "temporal_scope",
            "resolution_mode",
            "pending_question_act",
            "alternate_datetime",
            "question_contract",
        ):
            value = payload.get(key)
            if value is not None:
                meta[key] = value
        return PolicyDecision(
            outcome=outcome,
            action=action,
            intent=intent,
            source=source,
            tool_action=tool_action,
            tool_args=self._normalize_dict(payload.get("tool_args")),
            slots=self._normalize_string_dict(payload.get("slots")),
            pack_refs=self._normalize_list(payload.get("pack_refs")),
            capability_refs=[capability] if capability else [],
            risk_signals=self._normalize_list(payload.get("risk_signals")),
            interaction=InteractionContract(
                owner=interaction_owner,
                target=self._normalize_token(payload.get("pending_question_target")),
                relation=relation,
            ),
            pending_question_contract=pending_question,
            meta=meta,
        )

    def build_tool_reply_owner_decision(
        self,
        *,
        payload: dict[str, Any] | None,
        default_intent: str | None,
        reply_intent: str | None,
        tool_action: str | None,
        expected_reply_type: str | None,
        pending_question_tool_followup: bool = False,
        pending_question_act: str | None = None,
        collect_service_info_interrupt_active: bool = False,
        master_override_applied: bool = False,
    ) -> PolicyDecision:
        tool_reply_payload = dict(payload) if isinstance(payload, dict) else {}
        if not (
            isinstance(tool_reply_payload.get("intent"), str)
            and tool_reply_payload.get("intent").strip()
        ):
            tool_reply_payload["intent"] = (
                default_intent or reply_intent or tool_action or "other"
            )
        if not (
            isinstance(tool_reply_payload.get("action"), str)
            and tool_reply_payload.get("action").strip()
        ):
            tool_reply_payload["action"] = "collect" if expected_reply_type else "fact"
        if master_override_applied:
            tool_reply_payload["intent"] = default_intent or "master"
            tool_reply_payload["action"] = "fact"
        if not (
            isinstance(tool_reply_payload.get("tool_action"), str)
            and tool_reply_payload.get("tool_action").strip()
        ):
            tool_reply_payload["tool_action"] = tool_action or "info"

        interaction_owner = "tool_reply"
        interaction_relation = "tool_reply"
        if pending_question_tool_followup:
            interaction_owner = "booking_slot_guidance"
            interaction_relation = pending_question_act or "ask_about_requested_slot"
        elif collect_service_info_interrupt_active:
            interaction_owner = "booking_interrupt_info"
            interaction_relation = "generic_info_interrupt"
        elif master_override_applied:
            interaction_owner = "policy_core_guard"
            interaction_relation = "policy_guard"

        return self.build_from_policy_override(
            tool_reply_payload,
            interaction_owner=interaction_owner,
            interaction_relation=interaction_relation,
        )

    def build_controlled_degrade(
        self,
        *,
        reason_code: str,
        action: str,
        intent: str,
        outcome: DecisionOutcome = "HANDOFF",
        tool_action: str = "handoff",
        interaction_owner: str,
        interaction_target: str | None = None,
        interaction_relation: str | None = None,
    ) -> PolicyDecision:
        return PolicyDecision(
            outcome=outcome,
            action=action,
            intent=intent,
            tool_action=tool_action,
            interaction=InteractionContract(
                owner=interaction_owner,
                target=interaction_target,
                relation=interaction_relation,
            ),
            meta={
                "reason_code": reason_code,
                "degrade_path": True,
                "synthetic_policy_decision": True,
            },
        )

    def build_preflight_reject(
        self,
        *,
        reason_code: str,
        action: str,
        intent: str,
        interaction_owner: str,
        interaction_target: str | None = None,
        interaction_relation: str | None = None,
    ) -> PolicyDecision:
        return PolicyDecision(
            outcome="FACT",
            action=action,
            intent=intent,
            tool_action="noop",
            interaction=InteractionContract(
                owner=interaction_owner,
                target=interaction_target,
                relation=interaction_relation,
            ),
            meta={
                "reason_code": reason_code,
                "preflight_path": True,
                "synthetic_policy_decision": True,
            },
        )

    @staticmethod
    def _normalize_token(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned or None

    @staticmethod
    def _normalize_tool_action(value: Any) -> str:
        cleaned = TurnPlanner._normalize_token(value)
        if not cleaned:
            raise ValueError("tool_action_missing")
        return cleaned

    def _build_policy_core_decision(
        self,
        payload: dict[str, Any],
        *,
        current_goal: str | None,
        expected_reply_type: str | None,
    ) -> PolicyDecision:
        normalized_payload = dict(payload)
        normalized_payload["tool_action"] = self._normalize_policy_tool_action(
            normalized_payload.get("tool_action"),
            action=normalized_payload.get("action"),
        )
        normalized_payload["slots"] = self._normalize_planner_slots(
            normalized_payload.get("slots")
        )
        normalized_payload["next_question"] = self._normalize_booking_slot_name(
            normalized_payload.get("next_question"),
            expected_reply_type=expected_reply_type,
            booking_slots=normalized_payload["slots"],
        )
        normalized_payload["open_questions"] = [
            item
            for item in (
                self._normalize_booking_slot_name(
                    raw_item,
                    expected_reply_type=expected_reply_type,
                    booking_slots=normalized_payload["slots"],
                )
                for raw_item in self._normalize_list(normalized_payload.get("open_questions"))
            )
            if item
        ]
        normalized_payload.setdefault("goal", current_goal)
        if normalized_payload.get("goal") == "booking" or normalized_payload["slots"]:
            interaction_owner = "llm_policy_core_booking"
            interaction_relation = (
                normalized_payload.get("active_question_relation")
                or "fill_requested_slot"
            )
        elif normalized_payload.get("action") == "handoff":
            interaction_owner = "llm_policy_core_handoff"
            interaction_relation = "explicit_handoff"
        else:
            interaction_owner = "llm_policy_core_fact"
            interaction_relation = "grounded_fact"
        return self.build_from_policy_override(
            normalized_payload,
            interaction_owner=interaction_owner,
            interaction_relation=interaction_relation,
            source="llm_policy_core",
        )

    def _build_expected_reply_fallback(
        self,
        *,
        message_text: str,
        client_slug: str | None,
        expected_reply_type: str | None,
        current_goal: str | None,
        normalized_booking_state: dict[str, str],
        interpret_expected_reply_fn,
    ) -> PolicyDecision | None:
        if current_goal != "booking" or not expected_reply_type:
            return None
        interpreted = interpret_expected_reply_fn(
            message_text,
            expected_reply_type=expected_reply_type,
        )
        payload = interpreted.get("payload") if isinstance(interpreted, dict) else None
        slot_key = expected_reply_type
        try:
            from app.services.expected_reply_contract import expected_reply_slot_key

            slot_key = expected_reply_slot_key(expected_reply_type) or expected_reply_type
        except Exception:
            slot_key = expected_reply_type
        normalized_slot = self._normalize_booking_slot_name(slot_key)
        slot_value = self._normalize_token(payload.get("value")) if isinstance(payload, dict) else None
        slot_value = self._validate_expected_reply_slot_value(
            message_text,
            normalized_slot=normalized_slot,
            client_slug=client_slug,
            interpreted_value=slot_value,
        )
        if normalized_slot is None or slot_value is None:
            return None
        merged_slots = dict(normalized_booking_state)
        merged_slots[normalized_slot] = slot_value
        next_slot = self._select_missing_booking_slot(
            merged_slots,
            expected_reply_type=expected_reply_type,
        )
        return self.build_from_policy_override(
            {
                "action": "collect",
                "intent": "booking",
                "tool_action": "collect",
                "slots": {normalized_slot: slot_value},
                "next_question": next_slot,
                "open_questions": [next_slot] if next_slot else [],
                "goal": "booking",
                "reason": "answer_interpreter_fallback",
            },
            interaction_owner="turn_planner_fallback",
            interaction_relation="fill_requested_slot",
            source="answer_interpreter",
        )

    def _build_active_booking_info_interrupt_override(
        self,
        *,
        message_text: str,
        client_slug: str | None,
        expected_reply_type: str | None,
        expected_reply_reason: str | None,
        current_goal: str | None,
        normalized_booking_state: dict[str, str],
        detect_intent_routing_primitives_fn,
        detect_policy_core_route_snapshot_fn,
    ) -> PolicyDecision | None:
        if current_goal != "booking" or not expected_reply_type:
            return None
        if expected_reply_type == "time":
            matched_datetime, slot_constraint = self._match_expected_time_reply_candidate(
                message_text=message_text,
                client_slug=client_slug,
            )
            if matched_datetime and not slot_constraint:
                return None

        snapshot = detect_policy_core_route_snapshot_fn(
            message_text,
            primitives=detect_intent_routing_primitives_fn(message_text),
            has_media=False,
            client_slug=client_slug,
            reply_slot=expected_reply_type,
            resume_reason=expected_reply_reason,
            has_active_service_referent=bool(normalized_booking_state.get("service")),
            active_service_referent=normalized_booking_state.get("service"),
            active_booking_time_token=normalized_booking_state.get("datetime"),
            active_booking_datetime_value=normalized_booking_state.get("datetime"),
            booking_active=True,
        )
        if snapshot is None or snapshot.action != "fact":
            return None

        payload = snapshot.to_override()
        intent = self._normalize_token(payload.get("intent"))
        tool_action = self._normalize_token(payload.get("tool_action"))
        if intent in {"check_booking", "verify_booking", "confirm_booking"}:
            return None
        if tool_action == "calendar.get_booking":
            return None

        slot_values = self._normalize_string_dict(payload.get("slots"))
        service_query = self._normalize_token(
            self._normalize_dict(payload.get("tool_args")).get("service_query")
        )
        if normalized_booking_state.get("service") and "service" not in slot_values:
            slot_values["service"] = normalized_booking_state["service"]
        elif (
            expected_reply_type == "service_choice"
            and service_query
            and "service" not in slot_values
        ):
            slot_values["service"] = service_query
        if slot_values:
            payload["slots"] = slot_values

        return self.build_from_policy_override(
            payload,
            interaction_owner="turn_planner_intent_routing",
            interaction_relation="generic_info_interrupt",
            source="turn_planner_intent_routing",
        )

    def _build_expected_time_question_contract_override(
        self,
        *,
        message_text: str,
        client_slug: str | None,
        expected_reply_type: str | None,
        current_goal: str | None,
    ) -> PolicyDecision | None:
        if current_goal != "booking" or expected_reply_type != "time":
            return None
        matched_datetime, slot_constraint = self._match_expected_time_reply_candidate(
            message_text=message_text,
            client_slug=client_slug,
        )
        if not matched_datetime or not (
            slot_constraint or self._looks_like_explicit_time_availability_probe(message_text)
        ):
            return None
        return self.build_from_policy_override(
            {
                "action": "collect",
                "intent": "booking",
                "tool_action": "collect",
                "tool_args": {"candidate_datetime": matched_datetime},
                "slots": {"datetime": matched_datetime},
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "goal": "booking",
                "reason": "question_contract_slot_constraint",
                "question_contract": True,
                "pending_question_act": "slot_constraint",
                "pending_question_target": "time",
                "active_question_relation": "slot_constraint",
                "alternate_datetime": matched_datetime,
            },
            interaction_owner="question_contract",
            interaction_relation="slot_constraint",
            source="question_contract",
        )

    def _match_expected_time_reply_candidate(
        self,
        *,
        message_text: str,
        client_slug: str | None,
    ) -> tuple[str | None, bool]:
        from app.routers.webhook import decision as decision_router

        matched_slot, matched_value, _ = decision_router._match_expected_reply(
            expected_reply_type=decision_router.EXPECTED_REPLY_TIME,
            message_text=message_text,
            client_slug=client_slug,
        )
        normalized_value = self._normalize_token(matched_value) if matched_slot else None
        if normalized_value is None:
            return None, False
        slot_constraint = bool(
            decision_router._is_time_slot_constraint_candidate(
                message_text=message_text,
                candidate_value=normalized_value,
                client_slug=client_slug,
            )
        )
        return normalized_value, slot_constraint

    @staticmethod
    def _looks_like_explicit_time_availability_probe(message_text: str) -> bool:
        normalized = message_text.casefold()
        if "?" not in message_text:
            return False
        if not re.search(r"\b(?:мест|окн|свобод|занят|доступ)\w*\b", normalized):
            return False
        return bool(
            re.search(r"\b(?:есть ли|будет ли|найдется ли|свободно ли|доступно ли)\b", normalized)
            or re.search(r"\b(?:на|в)\s*(?:[01]?\d|2[0-3])(?::[0-5]\d)?\b", normalized)
        )

    def _rescue_expected_reply_contract(
        self,
        *,
        decision: PolicyDecision,
        message_text: str,
        client_slug: str | None,
        expected_reply_type: str | None,
        current_goal: str | None,
        normalized_booking_state: dict[str, str],
        interpret_expected_reply_fn,
    ) -> PolicyDecision:
        if current_goal != "booking" or not expected_reply_type:
            return decision
        if self._decision_satisfies_expected_reply_contract(decision):
            return decision
        fallback_decision = self._build_expected_reply_fallback(
            message_text=message_text,
            client_slug=client_slug,
            expected_reply_type=expected_reply_type,
            current_goal=current_goal,
            normalized_booking_state=normalized_booking_state,
            interpret_expected_reply_fn=interpret_expected_reply_fn,
        )
        return fallback_decision or decision

    def _recover_booking_verification_contract(
        self,
        *,
        decision: PolicyDecision,
        message_text: str,
        detect_booking_verification_mode_fn,
    ) -> PolicyDecision:
        if decision.tool_action != "calendar.get_booking":
            return decision
        appointment_id = self._normalize_token(decision.tool_args.get("appointment_id"))
        if appointment_id:
            return decision

        verification_mode = detect_booking_verification_mode_fn(message_text)
        if verification_mode == "confirm":
            return self.build_from_policy_override(
                {
                    "action": "collect",
                    "intent": "confirm_booking",
                    "tool_action": "collect",
                    "goal": "booking",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                    "reason": "booking_confirmation_recovery",
                },
                interaction_owner="llm_policy_core_booking",
                interaction_relation="fill_requested_slot",
                source="llm_policy_core",
            )
        if verification_mode == "check" and decision.intent != "check_booking":
            return decision.model_copy(
                update={
                    "intent": "check_booking",
                    "interaction": decision.interaction.model_copy(
                        update={"owner": "llm_policy_core_booking", "relation": "grounded_fact"}
                    ),
                }
            )
        return decision

    @staticmethod
    def _decision_satisfies_expected_reply_contract(decision: PolicyDecision) -> bool:
        if decision.outcome == "COLLECT" and decision.intent == "booking":
            return True
        if decision.outcome == "COLLECT" and decision.tool_action == "calendar.book_slot":
            return True
        return False

    def _validate_expected_reply_slot_value(
        self,
        message_text: str,
        *,
        normalized_slot: str | None,
        client_slug: str | None,
        interpreted_value: str | None,
    ) -> str | None:
        if normalized_slot == "datetime":
            from app.routers.webhook.booking import _validate_datetime_slot

            validated = _validate_datetime_slot(
                message_text,
                allow_freeform=True,
                client_slug=client_slug,
            )
            if validated:
                return self._normalize_token(validated)
            return None
        if normalized_slot == "name":
            from app.routers.webhook.booking import _validate_name_slot

            normalized_message = (message_text or "").strip().casefold()
            if "?" in normalized_message:
                return None
            if normalized_message.split()[:1] and normalized_message.split()[0] in {
                "как",
                "какая",
                "какой",
                "какие",
                "сколько",
                "есть",
                "где",
                "когда",
                "почем",
                "почему",
                "зачем",
                "можно",
            }:
                return None
            validated = _validate_name_slot(
                message_text,
                allow_freeform=True,
                client_slug=client_slug,
            )
            if validated:
                return self._normalize_token(validated)
            return None
        if normalized_slot == "service":
            from app.services.info_signal_service import (
                detect_grounded_duration_service_query,
                detect_grounded_pricing_service_query,
                detect_location_policy_pack_refs,
                looks_like_contact_policy_message,
                looks_like_duration_service_clarify_policy_message,
                looks_like_hours_policy_message,
                looks_like_promotions_policy_message,
                looks_like_promotions_rules_policy_message,
                looks_like_pricing_service_clarify_policy_message,
                looks_like_services_overview_message,
            )
            from app.routers.webhook.booking import _validate_service_slot

            if (
                detect_grounded_pricing_service_query(message_text, client_slug=client_slug)
                or detect_grounded_duration_service_query(message_text, client_slug=client_slug)
                or looks_like_pricing_service_clarify_policy_message(
                    message_text,
                    client_slug=client_slug,
                )
                or looks_like_duration_service_clarify_policy_message(
                    message_text,
                    client_slug=client_slug,
                )
                or looks_like_promotions_policy_message(message_text, client_slug=client_slug)
                or looks_like_promotions_rules_policy_message(
                    message_text,
                    client_slug=client_slug,
                )
                or looks_like_hours_policy_message(message_text, client_slug=client_slug)
                or looks_like_services_overview_message(message_text, client_slug=client_slug)
                or looks_like_contact_policy_message(message_text, client_slug=client_slug)
                or detect_location_policy_pack_refs(message_text, client_slug=client_slug)
            ):
                return None
            validated = _validate_service_slot(
                message_text,
                allow_freeform=True,
                client_slug=client_slug,
            )
            if validated:
                return self._normalize_token(validated)
            return None
        if normalized_slot == "phone":
            from app.routers.webhook.booking import _validate_phone_slot

            validated = _validate_phone_slot(
                message_text,
                allow_freeform=True,
                client_slug=client_slug,
            )
            if validated:
                return self._normalize_token(validated)
            return None
        if interpreted_value is not None:
            return interpreted_value
        return self._build_expected_reply_slot_fallback_value(
            message_text,
            normalized_slot=normalized_slot,
        )

    def _build_expected_reply_slot_fallback_value(
        self,
        message_text: str,
        *,
        normalized_slot: str | None,
    ) -> str | None:
        if normalized_slot == "datetime":
            from app.services.booking_signal_service import (
                extract_relative_date_token,
                extract_time_token,
                has_explicit_date_signal,
                normalize_resolved_datetime_value,
            )

            normalized_message = message_text.casefold()
            if (
                has_explicit_date_signal(message_text)
                or extract_time_token(message_text)
                or extract_relative_date_token(message_text)
                or normalize_resolved_datetime_value(
                    message_text,
                    normalized_text=normalized_message,
                )
            ):
                return self._normalize_token(message_text)
            return None
        if normalized_slot == "name":
            from app.services.booking_signal_service import clean_name_candidate

            cleaned = self._normalize_token(clean_name_candidate(message_text))
            if cleaned and any(ch.isalpha() for ch in cleaned):
                return cleaned
            return None
        if normalized_slot == "phone":
            from app.services.booking_signal_service import looks_like_phone, normalize_phone_digits

            if not looks_like_phone(message_text):
                return None
            return self._normalize_token(normalize_phone_digits(message_text))
        return self._normalize_token(message_text)

    def _build_intent_routing_fallback(
        self,
        *,
        message_text: str,
        client_slug: str | None,
        expected_reply_type: str | None,
        expected_reply_reason: str | None,
        current_goal: str | None,
        normalized_booking_state: dict[str, str],
        detect_intent_routing_primitives_fn,
        detect_policy_core_route_snapshot_fn,
    ) -> PolicyDecision | None:
        primitives = detect_intent_routing_primitives_fn(message_text)
        snapshot = detect_policy_core_route_snapshot_fn(
            message_text,
            primitives=primitives,
            has_media=False,
            client_slug=client_slug,
            reply_slot=expected_reply_type,
            resume_reason=expected_reply_reason,
            has_active_service_referent=bool(normalized_booking_state.get("service")),
            active_service_referent=normalized_booking_state.get("service"),
            active_booking_time_token=normalized_booking_state.get("datetime"),
            active_booking_datetime_value=normalized_booking_state.get("datetime"),
            booking_active=current_goal == "booking" or bool(normalized_booking_state),
        )
        if snapshot is None:
            return None
        payload = snapshot.to_override()
        action = self._normalize_token(payload.get("action"))
        relation = "grounded_fact"
        if action == "collect":
            relation = (
                self._normalize_token(payload.get("active_question_relation"))
                or "fill_requested_slot"
            )
        elif action == "handoff":
            relation = "explicit_handoff"
        return self.build_from_policy_override(
            payload,
            interaction_owner="turn_planner_intent_routing",
            interaction_relation=relation,
            source="turn_planner_intent_routing",
        )

    @classmethod
    def _normalize_list(cls, value: Any) -> list[str]:
        if not isinstance(value, Iterable) or isinstance(value, (str, bytes, dict)):
            return []
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            cleaned = cls._normalize_token(item)
            if not cleaned or cleaned in seen:
                continue
            normalized.append(cleaned)
            seen.add(cleaned)
        return normalized

    @classmethod
    def _normalize_string_dict(cls, value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        normalized: dict[str, str] = {}
        for key, item in value.items():
            cleaned_key = cls._normalize_token(key)
            cleaned_value = cls._normalize_token(item)
            if not cleaned_key or cleaned_value is None:
                continue
            normalized[cleaned_key] = cleaned_value
        return normalized

    @staticmethod
    def _normalize_dict(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    def _normalize_planner_slots(self, value: Any) -> dict[str, str]:
        normalized = self._normalize_string_dict(value)
        remapped: dict[str, str] = {}
        for key, item in normalized.items():
            canonical_key = self._normalize_booking_slot_name(key) or key
            remapped[canonical_key] = item
        return remapped

    def _normalize_booking_state(self, value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        return self._normalize_planner_slots(value)

    def _normalize_booking_slot_name(
        self,
        value: Any,
        *,
        expected_reply_type: str | None = None,
        booking_slots: dict[str, str] | None = None,
    ) -> str | None:
        cleaned = self._normalize_token(value)
        if not cleaned:
            fallback = self._normalize_token(expected_reply_type)
            if fallback == "time":
                return "datetime"
            if fallback in {"service_choice", "name", "phone"}:
                return {
                    "service_choice": "service",
                    "name": "name",
                    "phone": "phone",
                }.get(fallback)
            if isinstance(booking_slots, dict) and booking_slots:
                return self._select_missing_booking_slot(booking_slots)
            return None
        return _PLANNER_SLOT_ALIASES.get(cleaned, cleaned)

    def _select_missing_booking_slot(
        self,
        booking_slots: dict[str, str] | None,
        *,
        expected_reply_type: str | None = None,
    ) -> str | None:
        slots = dict(booking_slots or {})
        for candidate in ("service", "datetime", "name"):
            if candidate not in slots:
                return candidate
        if "phone" not in slots and self._normalize_token(expected_reply_type) == "phone":
            return "phone"
        return None

    def _normalize_policy_tool_action(self, value: Any, *, action: Any) -> str:
        cleaned = self._normalize_token(value)
        if cleaned:
            return cleaned
        normalized_action = self._normalize_token(action)
        if normalized_action == "handoff":
            return "handoff"
        if normalized_action == "collect":
            return "collect"
        return "info"

    def _load_consult_refs(self, loader, client_slug: str | None) -> list[str]:
        playbook, error = loader(client_slug)
        if error or not playbook:
            return []
        refs: list[str] = []
        for topic in getattr(playbook, "topics", []):
            topic_id = self._normalize_token(getattr(topic, "id", None))
            if topic_id:
                refs.append(topic_id)
        return refs


__all__ = [
    "DecisionOutcome",
    "InboundTurnInput",
    "InteractionContract",
    "PendingQuestionContract",
    "PolicyDecision",
    "TurnPlanner",
]
