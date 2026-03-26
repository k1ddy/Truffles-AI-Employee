from __future__ import annotations

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
    reason: str | None = None
    pending_question_act: str | None = None
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
        booking_state: dict[str, Any] | None,
        memory_summary: str | None = None,
        memory_profile: dict[str, Any] | None = None,
        timing_context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        from app.services.consult_pack_service import load_consult_playbook
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
        consult_refs = self._load_consult_refs(load_consult_playbook, client_slug)
        policy_result = route_llm_policy_core(
            normalized_message,
            info_refs=list(_DEFAULT_INFO_REFS),
            consult_refs=consult_refs,
            memory_summary=memory_summary,
            memory_profile=normalized_memory_profile,
            client_slug=client_slug,
            timing_context=timing_context,
        )
        payload = policy_result.get("payload") if isinstance(policy_result, dict) else None
        if isinstance(payload, dict):
            decision = self._build_policy_core_decision(payload)
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
        pending_question = self._build_pending_question_contract(payload)
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
        entity_refs = self._normalize_entity_refs(payload.get("entity_refs"))
        if entity_refs:
            meta["entity_refs"] = entity_refs
        semantic_contract = self._build_semantic_contract_payload(payload, entity_refs=entity_refs)
        if semantic_contract:
            meta["semantic_contract"] = semantic_contract
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

    def _build_semantic_contract_payload(
        self,
        payload: dict[str, Any],
        *,
        entity_refs: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        contract: dict[str, Any] = {"contract_version": "semantic_contract.v1"}
        for field_name in (
            "subject_kind",
            "capability",
            "temporal_scope",
            "resolution_mode",
            "pending_question_act",
            "pending_question_target",
            "active_question_relation",
            "alternate_datetime",
        ):
            value = self._normalize_token(payload.get(field_name))
            if value is not None:
                contract[field_name] = value
        referents = self._normalize_referents(payload.get("referents"))
        if referents:
            contract["referents"] = referents
        if entity_refs:
            contract["entity_refs"] = entity_refs
        return contract if len(contract) > 1 else None

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
        payload: dict[str, Any],
    ) -> PolicyDecision:
        normalized_payload = dict(payload)
        normalized_payload["tool_action"] = self._normalize_tool_action(
            normalized_payload.get("tool_action")
        )
        normalized_payload["slots"] = self._normalize_planner_slots(
            normalized_payload.get("slots")
        )
        normalized_payload["next_question"] = self._normalize_booking_slot_name(
            normalized_payload.get("next_question")
        )
        normalized_payload["open_questions"] = [
            item
            for item in (
                self._normalize_booking_slot_name(
                    raw_item,
                )
                for raw_item in self._normalize_list(normalized_payload.get("open_questions"))
            )
            if item
        ]
        if normalized_payload.get("next_question") and not normalized_payload["open_questions"]:
            normalized_payload["open_questions"] = [normalized_payload["next_question"]]
        if normalized_payload.get("action") == "handoff":
            normalized_payload = self._strip_pending_question_payload_if_handoff(
                normalized_payload
            )
        return self.build_from_policy_override(
            normalized_payload,
            interaction_owner="llm_policy_core",
            interaction_relation=self._normalize_token(
                normalized_payload.get("active_question_relation")
            ),
            source="llm_policy_core",
        )

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
