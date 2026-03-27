from __future__ import annotations

from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.semantic_decision import SemanticDecisionV1

DecisionOutcome = Literal["FACT", "COLLECT", "HANDOFF"]
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
    reason: str | None = None
    pending_question_act: str | None = None
    pending_question_target: str | None = None
    active_question_relation: str | None = None
    next_question: str | None = None
    open_questions: list[str] = Field(default_factory=list)


class SemanticFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "semantic_frame.v2"
    user_goal: str | None = None
    requested_effect: str | None = None
    subject: dict[str, Any] = Field(default_factory=dict)
    referents: dict[str, dict[str, Any]] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    preferences: dict[str, Any] = Field(default_factory=dict)
    continuation: dict[str, Any] = Field(default_factory=dict)
    capability_selection: dict[str, Any] = Field(default_factory=dict)
    needs_human: bool = False
    reason: str | None = None


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
    semantic_frame: SemanticFrame = Field(default_factory=SemanticFrame)
    pending_question_contract: PendingQuestionContract = Field(default_factory=PendingQuestionContract)
    semantic_decision: SemanticDecisionV1 | None = None
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
        booking_state: dict[str, Any] | None,
        memory_summary: str | None = None,
        memory_profile: dict[str, Any] | None = None,
        timing_context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        from app.services.intent_service import route_llm_policy_core

        normalized_message = self._normalize_token(message_text)
        if not normalized_message:
            return self.build_preflight_reject(
                reason_code="empty_message",
                action="reject",
                intent="empty_message",
                interaction_owner="turn_planner_preflight",
            )

        normalized_booking_state = self._normalize_booking_state(booking_state)
        normalized_memory_profile = self._merge_booking_slot_state_into_memory_profile(
            memory_profile,
            slot_state=normalized_booking_state,
        )
        policy_result = route_llm_policy_core(
            normalized_message,
            memory_summary=memory_summary,
            memory_profile=normalized_memory_profile,
            client_slug=client_slug,
            timing_context=timing_context,
        )
        payload = policy_result.get("payload") if isinstance(policy_result, dict) else None
        if isinstance(payload, dict):
            raw_payload = dict(payload)
            binding_payload = (
                dict(policy_result.get("binding"))
                if isinstance(policy_result.get("binding"), dict)
                else {}
            )
            if not binding_payload:
                binding_payload = {
                    "tool_action": raw_payload.get("tool_action"),
                    "tool_args": raw_payload.get("tool_args"),
                }
            decision = self._build_policy_core_decision(
                semantic_decision=self._coerce_semantic_decision(raw_payload),
                binding_payload=binding_payload,
            )
            decision.meta["policy_core_trace"] = self._build_policy_core_trace_payload(
                policy_result,
                schema_verdict="ok",
                projection_verdict=str(
                    (
                        policy_result.get("projection_trace") or {}
                    ).get("status")
                    or "ok"
                ),
            )
            return decision

        degrade_reason = self._normalize_token(
            policy_result.get("error") if isinstance(policy_result, dict) else None
        ) or "policy_core_unavailable"
        projection_error = self._normalize_token(
            policy_result.get("projection_error") if isinstance(policy_result, dict) else None
        )
        if degrade_reason == "invalid_projection":
            earliest_failed_stage = "policy_projection"
            root_reason_code = f"policy_projection:{projection_error or 'invalid_projection'}"
            projection_verdict = projection_error or "invalid_projection"
            schema_verdict = "ok"
        else:
            earliest_failed_stage = "policy_core"
            root_reason_code = f"policy_core:{degrade_reason}"
            projection_verdict = "skipped"
            schema_verdict = (
                "invalid_schema"
                if degrade_reason == "invalid_schema"
                else degrade_reason
            )
        decision = self.build_controlled_degrade(
            reason_code=f"planner:{degrade_reason}",
            action="handoff",
            intent="planner_degrade",
            tool_action="handoff",
            interaction_owner="turn_planner_degrade",
        )
        decision.meta["earliest_failed_stage"] = earliest_failed_stage
        decision.meta["root_reason_code"] = root_reason_code
        decision.meta["policy_core_trace"] = self._build_policy_core_trace_payload(
            policy_result,
            schema_verdict=schema_verdict,
            projection_verdict=projection_verdict,
        )
        return decision

    def build_from_semantic_decision(
        self,
        semantic_decision: SemanticDecisionV1,
        *,
        binding_tool_action: str,
        binding_tool_args: dict[str, Any] | None = None,
        interaction_owner: str,
        source: str = "policy_core",
    ) -> PolicyDecision:
        semantic_payload = self._normalized_semantic_payload(semantic_decision)
        action = semantic_decision.requested_outcome
        outcome = self._ACTION_TO_OUTCOME.get(action)
        if outcome is None:
            raise ValueError(f"unsupported_policy_action:{action}")
        meta: dict[str, Any] = {
            "planner_source": "turn_planner",
            "semantic_decision_id": semantic_decision.decision_id,
            "semantic_decision_schema_version": semantic_decision.schema_version,
        }
        for key in (
            "reason",
            "goal",
            "needs_manager",
            "resolver_id",
            "resolver_version",
        ):
            value = semantic_payload.get(key)
            if value is not None:
                meta[key] = value
        return PolicyDecision(
            outcome=outcome,
            action=action,
            intent=semantic_decision.intent,
            source=source,
            tool_action=self._normalize_tool_action(binding_tool_action),
            tool_args=self._normalize_dict(binding_tool_args),
            slots=dict(semantic_decision.semantic_slots),
            pack_refs=list(semantic_decision.grounding_requirements.pack_refs),
            capability_refs=[semantic_decision.capability_id]
            if semantic_decision.capability_id
            else [],
            risk_signals=list(semantic_decision.risk_signals),
            interaction=InteractionContract(
                owner=interaction_owner,
                target=semantic_decision.missing_information.pending_question_target,
                relation=semantic_decision.missing_information.active_question_relation,
            ),
            semantic_decision=semantic_decision,
            meta=meta,
        )

    def canonical_pending_question_contract(
        self,
        decision: PolicyDecision,
    ) -> PendingQuestionContract:
        if isinstance(decision.semantic_decision, SemanticDecisionV1):
            semantic_payload = self._normalized_semantic_payload(decision.semantic_decision)
            return self._build_pending_question_contract(semantic_payload)
        return decision.pending_question_contract

    def canonical_semantic_frame(
        self,
        decision: PolicyDecision,
    ) -> SemanticFrame:
        if isinstance(decision.semantic_decision, SemanticDecisionV1):
            semantic_payload = self._normalized_semantic_payload(decision.semantic_decision)
            entity_refs = self._normalize_entity_refs(semantic_payload.get("entity_refs"))
            pending_question = self._build_pending_question_contract(semantic_payload)
            return self._build_semantic_frame_payload(
                semantic_payload,
                entity_refs=entity_refs,
                pending_question=pending_question,
            )
        return decision.semantic_frame

    def canonical_semantic_contract(
        self,
        decision: PolicyDecision,
    ) -> dict[str, Any] | None:
        if isinstance(decision.semantic_decision, SemanticDecisionV1):
            semantic_payload = self._normalized_semantic_payload(decision.semantic_decision)
            entity_refs = self._normalize_entity_refs(semantic_payload.get("entity_refs"))
            semantic_frame = self._build_semantic_frame_payload(
                semantic_payload,
                entity_refs=entity_refs,
                pending_question=self._build_pending_question_contract(semantic_payload),
            )
            return self._build_semantic_contract_payload(
                semantic_payload,
                entity_refs=entity_refs,
                semantic_frame=semantic_frame,
            )
        semantic_contract = decision.meta.get("semantic_contract") if isinstance(decision.meta, dict) else None
        if isinstance(semantic_contract, dict):
            return dict(semantic_contract)
        fallback = self._build_semantic_contract_payload(
            {},
            entity_refs=[],
            semantic_frame=decision.semantic_frame,
        )
        return dict(fallback) if isinstance(fallback, dict) else None

    def detect_semantic_mutation(
        self,
        decision: PolicyDecision,
    ) -> dict[str, Any] | None:
        semantic_decision = decision.semantic_decision
        if not isinstance(semantic_decision, SemanticDecisionV1):
            return None
        diffs: dict[str, Any] = {}
        if decision.action != semantic_decision.requested_outcome:
            diffs["action"] = {
                "expected": semantic_decision.requested_outcome,
                "actual": decision.action,
            }
        if decision.intent != semantic_decision.intent:
            diffs["intent"] = {
                "expected": semantic_decision.intent,
                "actual": decision.intent,
            }
        if dict(decision.slots) != dict(semantic_decision.semantic_slots):
            diffs["slots"] = {
                "expected": dict(semantic_decision.semantic_slots),
                "actual": dict(decision.slots),
            }
        if list(decision.pack_refs) != list(semantic_decision.grounding_requirements.pack_refs):
            diffs["pack_refs"] = {
                "expected": list(semantic_decision.grounding_requirements.pack_refs),
                "actual": list(decision.pack_refs),
            }
        expected_capability_refs = [semantic_decision.capability_id] if semantic_decision.capability_id else []
        if list(decision.capability_refs) != expected_capability_refs:
            diffs["capability_refs"] = {
                "expected": expected_capability_refs,
                "actual": list(decision.capability_refs),
            }
        if list(decision.risk_signals) != list(semantic_decision.risk_signals):
            diffs["risk_signals"] = {
                "expected": list(semantic_decision.risk_signals),
                "actual": list(decision.risk_signals),
            }
        expected_target = semantic_decision.missing_information.pending_question_target
        if decision.interaction.target != expected_target:
            diffs["interaction.target"] = {
                "expected": expected_target,
                "actual": decision.interaction.target,
            }
        expected_relation = semantic_decision.missing_information.active_question_relation
        if decision.interaction.relation != expected_relation:
            diffs["interaction.relation"] = {
                "expected": expected_relation,
                "actual": decision.interaction.relation,
            }
        shadow_pending = PendingQuestionContract().model_dump(mode="python", exclude_none=True)
        actual_pending = decision.pending_question_contract.model_dump(mode="python", exclude_none=True)
        if actual_pending != shadow_pending:
            diffs["pending_question_contract"] = {
                "expected": shadow_pending,
                "actual": actual_pending,
            }
        shadow_frame = SemanticFrame().model_dump(mode="python", exclude_none=True)
        actual_frame = decision.semantic_frame.model_dump(mode="python", exclude_none=True)
        if actual_frame != shadow_frame:
            diffs["semantic_frame"] = {
                "expected": shadow_frame,
                "actual": actual_frame,
            }
        shadow_contract: dict[str, Any] = {}
        actual_contract = (
            dict(decision.meta.get("semantic_contract"))
            if isinstance(decision.meta, dict) and isinstance(decision.meta.get("semantic_contract"), dict)
            else {}
        )
        if actual_contract != shadow_contract:
            diffs["meta.semantic_contract"] = {
                "expected": shadow_contract,
                "actual": actual_contract,
            }
        if not diffs:
            return None
        return {
            "reason_code": "semantic_decision_post_owner_mutation",
            "semantic_decision_id": semantic_decision.decision_id,
            "diffs": diffs,
        }

    def detect_missing_semantic_owner(
        self,
        decision: PolicyDecision,
    ) -> dict[str, Any] | None:
        if isinstance(decision.semantic_decision, SemanticDecisionV1):
            return None
        meta = dict(decision.meta) if isinstance(decision.meta, dict) else {}
        if meta.get("degrade_path") or meta.get("preflight_path"):
            return None
        return {
            "reason_code": "missing_semantic_owner",
            "source": decision.source,
            "outcome": decision.outcome,
            "action": decision.action,
            "tool_action": decision.tool_action,
            "synthetic_policy_decision": bool(meta.get("synthetic_policy_decision")),
        }

    def _build_semantic_contract_payload(
        self,
        payload: dict[str, Any],
        *,
        entity_refs: list[dict[str, Any]] | None = None,
        semantic_frame: SemanticFrame | None = None,
    ) -> dict[str, Any] | None:
        contract: dict[str, Any] = {"contract_version": "semantic_contract.v1"}
        frame_payload = (
            semantic_frame.model_dump(mode="python", exclude_none=True)
            if isinstance(semantic_frame, SemanticFrame)
            else {}
        )
        subject = frame_payload.get("subject") if isinstance(frame_payload.get("subject"), dict) else {}
        constraints = (
            frame_payload.get("constraints")
            if isinstance(frame_payload.get("constraints"), dict)
            else {}
        )
        continuation = (
            frame_payload.get("continuation")
            if isinstance(frame_payload.get("continuation"), dict)
            else {}
        )
        capability_selection = (
            frame_payload.get("capability_selection")
            if isinstance(frame_payload.get("capability_selection"), dict)
            else {}
        )
        field_sources = (
            ("subject_kind", subject.get("kind")),
            ("capability", capability_selection.get("capability")),
            ("temporal_scope", constraints.get("temporal_scope")),
            ("resolution_mode", capability_selection.get("resolution_mode")),
            ("pending_question_act", continuation.get("pending_question_act")),
            ("pending_question_target", continuation.get("pending_question_target")),
            ("active_question_relation", continuation.get("active_question_relation")),
            ("alternate_datetime", constraints.get("alternate_datetime")),
        )
        for field_name, semantic_value in field_sources:
            value = self._normalize_token(semantic_value)
            if value is None:
                value = self._normalize_token(payload.get(field_name))
            if value is not None:
                contract[field_name] = value
        referents = self._normalize_referents(
            frame_payload.get("referents")
            if isinstance(frame_payload.get("referents"), dict)
            else payload.get("referents")
        )
        if referents:
            contract["referents"] = referents
        if entity_refs:
            contract["entity_refs"] = entity_refs
        return contract if len(contract) > 1 else None

    def _build_semantic_frame_payload(
        self,
        payload: dict[str, Any],
        *,
        entity_refs: list[dict[str, Any]] | None = None,
        pending_question: PendingQuestionContract | None = None,
    ) -> SemanticFrame:
        normalized_slots = self._normalize_planner_slots(payload.get("slots"))
        normalized_referents = self._normalize_referents(payload.get("referents"))
        action = self._normalize_token(payload.get("action")) or "handoff"
        tool_action_hint = self._normalize_token(
            payload.get("tool_action_hint") or payload.get("tool_action")
        )
        subject_kind = self._normalize_token(payload.get("subject_kind"))
        preferred_referent_key = {
            "service": "service",
            "specialist": "specialist",
            "branch": "branch",
            "booking": "booking_ref",
        }.get(subject_kind or "")
        preferred_referent = (
            normalized_referents.get(preferred_referent_key)
            if preferred_referent_key is not None
            else None
        )
        subject: dict[str, Any] = {}
        if subject_kind:
            subject["kind"] = subject_kind
        subject_value = None
        if isinstance(preferred_referent, dict):
            subject_value = self._normalize_token(preferred_referent.get("value"))
        if subject_value is None:
            subject_value = self._normalize_token(normalized_slots.get("service"))
        if subject_value:
            subject["value"] = subject_value
        if entity_refs:
            subject["entity_refs"] = list(entity_refs)

        continuation: dict[str, Any] = {}
        pending_payload = (
            pending_question.model_dump(mode="python", exclude_none=True)
            if isinstance(pending_question, PendingQuestionContract)
            else {}
        )
        for field_name in (
            "expected_reply_type",
            "pending_question_act",
            "pending_question_target",
            "active_question_relation",
            "next_question",
        ):
            value = self._normalize_token(pending_payload.get(field_name))
            if value:
                continuation[field_name] = value
        open_questions = self._normalize_list(pending_payload.get("open_questions"))
        if open_questions:
            continuation["open_questions"] = open_questions
        if normalized_slots:
            continuation["slot_values"] = dict(normalized_slots)

        constraints: dict[str, Any] = {}
        temporal_scope = self._normalize_token(payload.get("temporal_scope"))
        if temporal_scope:
            constraints["temporal_scope"] = temporal_scope
        alternate_datetime = self._normalize_token(payload.get("alternate_datetime"))
        if alternate_datetime:
            constraints["alternate_datetime"] = alternate_datetime
        risk_signals = self._normalize_list(payload.get("risk_signals"))
        if risk_signals:
            constraints["risk_signals"] = risk_signals

        preferences: dict[str, Any] = {}
        specialist_referent = normalized_referents.get("specialist")
        if isinstance(specialist_referent, dict) and specialist_referent:
            preferences["specialist"] = dict(specialist_referent)

        capability_selection: dict[str, Any] = {}
        capability = self._normalize_token(payload.get("capability"))
        if capability:
            capability_selection["capability"] = capability
        resolution_mode = self._normalize_token(payload.get("resolution_mode"))
        if resolution_mode:
            capability_selection["resolution_mode"] = resolution_mode
        if tool_action_hint:
            capability_selection["tool_action_hint"] = tool_action_hint
        pack_refs = self._normalize_list(payload.get("pack_refs"))
        if pack_refs:
            capability_selection["pack_refs"] = pack_refs

        requested_effect = self._resolve_requested_effect(
            action=action,
            tool_action_hint=tool_action_hint,
        )
        user_goal = self._normalize_token(payload.get("goal")) or self._normalize_token(
            payload.get("intent")
        )
        reason = self._normalize_token(payload.get("reason"))

        return SemanticFrame(
            user_goal=user_goal,
            requested_effect=requested_effect,
            subject=subject,
            referents=normalized_referents,
            constraints=constraints,
            preferences=preferences,
            continuation=continuation,
            capability_selection=capability_selection,
            needs_human=bool(payload.get("needs_manager")) or action == "handoff",
            reason=reason,
        )

    def _resolve_requested_effect(
        self,
        *,
        action: str,
        tool_action_hint: str | None,
    ) -> str:
        if action == "collect":
            return "collect_missing_input"
        if action == "handoff":
            return "handoff_to_human"
        if tool_action_hint == "calendar.book_slot":
            return "commit_booking"
        if tool_action_hint == "calendar.get_booking":
            return "retrieve_booking"
        return "deliver_grounded_fact"

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

    def _build_policy_core_trace_payload(
        self,
        policy_result: dict[str, Any] | None,
        *,
        schema_verdict: str,
        projection_verdict: str,
    ) -> dict[str, Any]:
        payload = policy_result if isinstance(policy_result, dict) else {}
        trace_payload: dict[str, Any] = {
            "attempted": bool(payload.get("attempted")),
            "status": "ok" if isinstance(payload.get("payload"), dict) else "error",
            "schema_verdict": schema_verdict,
            "projection_verdict": projection_verdict,
        }
        for field_name, result_key in (
            ("input", "policy_input"),
            ("semantic_frame", "semantic_frame"),
            ("raw_output", "raw"),
            ("error", "error"),
            ("schema_error", "schema_error"),
            ("projection_error", "projection_error"),
            ("projection", "projection_trace"),
            ("elapsed_ms", "elapsed_ms"),
            ("model_name", "model_name"),
            ("attempt_count", "attempt_count"),
            ("compact_input_used", "compact_input_used"),
            ("compact_retry_used", "compact_retry_used"),
            ("structured_output_enabled", "structured_output_enabled"),
            ("structured_output_fallback_used", "structured_output_fallback_used"),
        ):
            value = payload.get(result_key)
            if value is not None:
                trace_payload[field_name] = value
        return trace_payload

    def _build_policy_core_decision(
        self,
        payload: dict[str, Any] | None = None,
        *,
        semantic_decision: SemanticDecisionV1 | None = None,
        binding_payload: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        if payload is not None:
            legacy_binding = dict(binding_payload) if isinstance(binding_payload, dict) else {
                "tool_action": payload.get("tool_action"),
                "tool_args": payload.get("tool_args"),
            }
            semantic_decision = self._coerce_semantic_decision(payload)
            binding_payload = legacy_binding
        if not isinstance(semantic_decision, SemanticDecisionV1):
            raise ValueError("semantic_decision_required")
        normalized_binding = dict(binding_payload) if isinstance(binding_payload, dict) else {}
        return self.build_from_semantic_decision(
            semantic_decision,
            binding_tool_action=self._normalize_tool_action(normalized_binding.get("tool_action")),
            binding_tool_args=self._normalize_dict(normalized_binding.get("tool_args")),
            interaction_owner="llm_policy_core",
            source="llm_policy_core",
        )

    def _coerce_semantic_decision(
        self,
        payload: dict[str, Any],
    ) -> SemanticDecisionV1:
        if payload.get("schema_version") == "semantic_decision.v1":
            return SemanticDecisionV1.model_validate(payload)
        return SemanticDecisionV1.from_policy_core_payload(payload)

    def _normalized_semantic_payload(
        self,
        semantic_decision: SemanticDecisionV1,
    ) -> dict[str, Any]:
        normalized_payload = semantic_decision.as_policy_payload()
        normalized_payload["slots"] = self._normalize_planner_slots(
            normalized_payload.get("slots")
        )
        normalized_payload["next_question"] = self._normalize_booking_slot_name(
            normalized_payload.get("next_question")
        )
        normalized_payload["open_questions"] = [
            item
            for item in (
                self._normalize_booking_slot_name(raw_item)
                for raw_item in self._normalize_list(normalized_payload.get("open_questions"))
            )
            if item
        ]
        if normalized_payload.get("next_question") and not normalized_payload["open_questions"]:
            normalized_payload["open_questions"] = [normalized_payload["next_question"]]
        if semantic_decision.requested_outcome == "handoff":
            normalized_payload = self._strip_pending_question_payload_if_handoff(
                normalized_payload
            )
        return normalized_payload

    @classmethod
    def _strip_pending_question_payload_if_handoff(
        cls,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if cls._normalize_token(payload.get("action")) != "handoff":
            return payload
        normalized = dict(payload)
        normalized.pop("next_question", None)
        normalized["open_questions"] = []
        for key in (
            "pending_question_act",
            "pending_question_target",
            "active_question_relation",
        ):
            normalized.pop(key, None)
        return normalized

    def _build_pending_question_contract(
        self,
        payload: dict[str, Any],
    ) -> PendingQuestionContract:
        expected_reply_type = self._normalize_token(payload.get("expected_reply_type"))
        pending_question_act = self._normalize_token(payload.get("pending_question_act"))
        pending_question_target = self._normalize_token(payload.get("pending_question_target"))
        active_question_relation = self._normalize_token(payload.get("active_question_relation"))
        next_question = self._normalize_token(payload.get("next_question"))
        open_questions = self._normalize_list(payload.get("open_questions"))
        contract_active = bool(
            expected_reply_type
            or pending_question_act
            or pending_question_target
            or active_question_relation
            or next_question
            or open_questions
        )
        reason = self._normalize_token(payload.get("reason")) if contract_active else None
        return PendingQuestionContract(
            expected_reply_type=expected_reply_type,
            reason=reason,
            pending_question_act=pending_question_act,
            pending_question_target=pending_question_target,
            active_question_relation=active_question_relation,
            next_question=next_question,
            open_questions=open_questions,
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

    def _normalize_entity_refs(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        normalized: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str, str]] = set()
        for item in value:
            entry: dict[str, Any] = {}
            if isinstance(item, dict):
                entity_id = self._normalize_token(item.get("entity_id")) or self._normalize_token(
                    item.get("id")
                )
                entity_type = self._normalize_token(item.get("entity_type")) or self._normalize_token(
                    item.get("type")
                )
                source_ref = self._normalize_token(item.get("source_ref"))
                value_token = self._normalize_token(item.get("value")) or self._normalize_token(
                    item.get("label")
                )
                if entity_id:
                    entry["entity_id"] = entity_id
                if entity_type:
                    entry["entity_type"] = entity_type
                if source_ref:
                    entry["source_ref"] = source_ref
                if value_token:
                    entry["value"] = value_token
                confidence = item.get("confidence")
                if isinstance(confidence, (int, float)):
                    entry["confidence"] = max(0.0, min(float(confidence), 1.0))
            elif isinstance(item, str):
                entity_id = self._normalize_token(item)
                if entity_id:
                    entry["entity_id"] = entity_id
            if not entry:
                continue
            dedupe_key = (
                str(entry.get("entity_id") or ""),
                str(entry.get("entity_type") or ""),
                str(entry.get("source_ref") or ""),
                str(entry.get("value") or ""),
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            normalized.append(entry)
        return normalized

    def _normalize_referents(self, value: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(value, dict):
            return {}
        normalized: dict[str, dict[str, Any]] = {}
        allowed_keys = {"service", "specialist", "branch", "booking_ref", "customer"}
        for raw_key, raw_payload in value.items():
            referent_key = self._normalize_token(raw_key)
            if referent_key not in allowed_keys or not isinstance(raw_payload, dict):
                continue
            entry: dict[str, Any] = {}
            for source_key, target_key in (
                ("value", "value"),
                ("entity_id", "entity_id"),
                ("entity_type", "entity_type"),
                ("source_ref", "source_ref"),
            ):
                token = self._normalize_token(raw_payload.get(source_key))
                if token:
                    entry[target_key] = token
            if entry:
                normalized[referent_key] = entry
        return normalized

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

    def _merge_booking_slot_state_into_memory_profile(
        self,
        memory_profile: dict[str, Any] | None,
        *,
        slot_state: dict[str, str] | None,
    ) -> dict[str, Any] | None:
        normalized_profile = dict(memory_profile) if isinstance(memory_profile, dict) else {}
        normalized_slot_state = self._normalize_planner_slots(slot_state)
        if normalized_slot_state and not isinstance(normalized_profile.get("slot_state"), dict):
            normalized_profile["slot_state"] = normalized_slot_state
        return normalized_profile or None

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

__all__ = [
    "DecisionOutcome",
    "InboundTurnInput",
    "InteractionContract",
    "PendingQuestionContract",
    "PolicyDecision",
    "SemanticDecisionV1",
    "SemanticFrame",
    "TurnPlanner",
]
