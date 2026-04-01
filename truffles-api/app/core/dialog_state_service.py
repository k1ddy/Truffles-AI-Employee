from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.conversation_projection import ConversationProjectionV1
from app.core.turn_journal import TurnJournalV1, build_turn_journal_events
from app.core.turn_planner import PendingQuestionContract, PolicyDecision, SemanticFrame, TurnPlanner
from app.schemas.webhook import InteractionStateContract, MemoryContract

_SESSION_MEMORY_INTERACTION_RESUME_SLOTS = {"service", "datetime", "name", "phone", "media"}
_SESSION_MEMORY_QUESTION_TYPES = {"service_choice", "time", "name", "media"}
_SESSION_MEMORY_PENDING_SLOT_BY_REPLY_TYPE = {
    "service_choice": "service",
    "time": "datetime",
    "name": "name",
    "media": "media",
}
_RUNTIME_CONTEXT_KEY = "consultant_runtime"
_RUNTIME_PENDING_RESUME_SNAPSHOT_KEYS = {
    "context_manager",
    "booking",
    "expected_reply_type",
    "expected_reply_reason",
}
_SESSION_MEMORY_INTERACTION_TARGETS = {"time", "specialist"}
_SESSION_MEMORY_INTERACTION_RELATIONS = {
    "fill_requested_slot",
    "ask_about_requested_slot",
    "slot_constraint",
    "slot_compare",
    "mixed_fill_plus_question",
    "referent_followup",
    "generic_info_interrupt",
    "specialist_availability_interrupt",
    "specialist_availability_followup",
    "tool_result_followup_specialist_missing",
}
_SESSION_MEMORY_INTERACTION_REFERENT_KEYS = {"service", "specialist", "branch", "booking_ref"}
_BOOKING_CONTEXT_SLOT_KEYS = {"service", "datetime", "name", "phone"}
_BOOKING_CONTEXT_STRING_KEYS = {
    "started_at",
    "service",
    "datetime",
    "name",
    "phone",
    "specialist_name",
    "specialist_id",
    "appointment_id",
    "reference_id",
}
_CANONICAL_DIALOG_STATE_OWNER = "context_manager.dialog_state.v1"
_CANONICAL_DIALOG_STATE_VERSION = "v1"
_CANONICAL_REFERENT_KEYS = {"service", "master", "branch", "booking_ref"}
_CANONICAL_PENDING_SLOTS = {"service", "datetime", "name", "phone", "media"}
_CANONICAL_PENDING_SLOT_ORDER = ("service", "datetime", "name", "phone")
_CANONICAL_EXPECTED_REPLY_SLOT_BY_TYPE = {
    "service_choice": "service",
    "time": "datetime",
    "name": "name",
    "phone": "phone",
    "media": "media",
}
_PENDING_RESUME_BOUNDARY_REPLY_BY_SLOT = {
    "service": "service_choice",
    "datetime": "time",
    "name": "name",
}
_PENDING_RESUME_BOUNDARY_REPLY_TYPES = set(_PENDING_RESUME_BOUNDARY_REPLY_BY_SLOT.values())
_CANONICAL_INTERACTION_TARGET_VALUES = {"time", "specialist"}
_CANONICAL_INTERACTION_RELATION_VALUES = {
    "fill_requested_slot",
    "ask_about_requested_slot",
    "slot_constraint",
    "slot_compare",
    "mixed_fill_plus_question",
    "referent_followup",
    "generic_info_interrupt",
    "specialist_availability_interrupt",
    "specialist_availability_followup",
    "tool_result_followup_specialist_missing",
}
_CANONICAL_INTERACTION_REFERENT_KEYS = {"service", "specialist", "branch", "booking_ref"}
_MEMORY_PROFILE_CONSENT_STATUSES = {"unknown", "asked", "granted", "declined"}
_TOUCHED_SLICE_CLASS_CARRYOVER_FAMILY_ID = "location_hours_parking"
_TOUCHED_SLICE_CLASS_CARRYOVER_CLASS = "info_bundle"
_TOUCHED_SLICE_CLASS_CARRYOVER_TTL_MESSAGES = 4
_TOUCHED_SLICE_CLASS_CARRYOVER_INTENTS = {"location", "hours", "parking"}
_CLASS_CARRYOVER_SECTION_INTENT_MAP = {
    "address": "location",
    "location": "location",
    "hours": "hours",
    "parking": "parking",
    "guest_policy": "guest_policy",
    "pricing": "pricing",
    "price": "pricing",
    "duration": "duration",
    "service_duration": "duration",
    "promotions": "promotions",
    "promotion": "promotions",
    "promo": "promotions",
    "discounts": "promotions",
    "discount": "promotions",
    "master": "master",
    "specialist": "master",
    "contact": "contact",
}


class CurrentReferents(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str | None = None
    specialist: str | None = None
    branch: str | None = None
    booking: str | None = None
    customer: str | None = None


class InteractionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_slot: str | None = None
    interaction_target: str | None = None
    interaction_relation: str | None = None
    interaction_owner: str | None = None
    grounded_referents: dict[str, str] = Field(default_factory=dict)
    confirmation_state: str | None = None
    degrade_reason: str | None = None


class DialogStateProjections(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_reply_type: str | None = None
    expected_reply_reason: str | None = None
    session_memory_interaction_state: InteractionState = Field(default_factory=InteractionState)


class ReEntryRequiredState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: bool
    reason: str | None = None
    set_at: str | None = None
    cleared_at: str | None = None


class HandoverConfirmationState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asked_at: str | None = None
    status: str | None = None
    trigger_type: str | None = None
    trigger_value: str | None = None
    user_message: str | None = None


class ReengageConfirmationState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asked_at: str | None = None
    booking_messages: list[str] = Field(default_factory=list)


class AsrConfirmationState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asked_at: str | None = None
    transcript: str | None = None
    attempt: int | None = None


class AsrInflightState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    started_at: str | None = None
    expires_at: str | None = None


class StyleReferenceMediaState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_type: str | None = None
    raw_type: str | None = None
    mime: str | None = None
    size_bytes: int | None = None
    duration_seconds: int | None = None
    url: str | None = None
    file_name: str | None = None
    caption: str | None = None
    ptt: bool | None = None


class StyleReferencePendingState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None
    created_at: str | None = None
    requested_at: str | None = None
    expires_at: str | None = None
    media: StyleReferenceMediaState | None = None
    storage_path: str | None = None
    public_url: str | None = None
    public_url_expires_at: str | None = None
    sha256: str | None = None


class SemanticStateEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    at: str | None = None
    source: str | None = None
    outcome: str | None = None
    action: str | None = None
    intent: str | None = None
    tool_action: str | None = None
    reason_code: str | None = None
    semantic_frame: SemanticFrame = Field(default_factory=SemanticFrame)


class CanonicalSemanticState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "canonical_semantic_state.v1"
    materialized_frame: SemanticFrame = Field(default_factory=SemanticFrame)
    event_log: list[SemanticStateEvent] = Field(default_factory=list)


class DialogState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "dialog_state.v1"
    semantic_state: CanonicalSemanticState = Field(default_factory=CanonicalSemanticState)
    current_referents: CurrentReferents = Field(default_factory=CurrentReferents)
    pending_question_contract: PendingQuestionContract = Field(default_factory=PendingQuestionContract)
    interaction_state: InteractionState = Field(default_factory=InteractionState)
    projections: DialogStateProjections = Field(default_factory=DialogStateProjections)
    meta: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class ExpectedReplyContextSyncResult:
    context: dict[str, Any]
    context_manager: dict[str, Any]
    expected_reply_type: str | None
    expected_reply_reason: str | None
    pending_question_contract: dict[str, Any] | None
    question_memory: dict[str, Any] | None
    re_entry_cleared: bool


class DialogStateService:
    """Typed normalization seam for the future single continuity writer."""

    def normalize(self, payload: dict[str, Any] | DialogState) -> DialogState:
        if isinstance(payload, DialogState):
            return payload
        return DialogState.model_validate(payload)

    def normalize_runtime_turn_journal(
        self,
        payload: dict[str, Any] | TurnJournalV1 | None,
    ) -> TurnJournalV1 | None:
        if isinstance(payload, TurnJournalV1):
            return payload
        if not isinstance(payload, dict):
            return None
        return TurnJournalV1.model_validate(payload)

    def normalize_runtime_conversation_projection(
        self,
        payload: dict[str, Any] | ConversationProjectionV1 | None,
    ) -> ConversationProjectionV1 | None:
        if isinstance(payload, ConversationProjectionV1):
            return payload
        if not isinstance(payload, dict):
            return None
        return ConversationProjectionV1.model_validate(payload)

    @staticmethod
    def _compatibility_view_refs() -> dict[str, str]:
        return {
            "dialog_state": "consultant_runtime.dialog_state.v1",
            "context_manager": "context_manager.canonical_dialog_state.v1",
            "session_memory": "session_memory.v1",
            "pending_resume": "pending_resume.v1",
        }

    def _build_conversation_projection(
        self,
        *,
        conversation_id: str | None,
        existing_projection: ConversationProjectionV1 | None,
        decision: PolicyDecision | None,
        semantic_state: CanonicalSemanticState,
        semantic_contract: dict[str, Any] | None,
        pending_question_contract: dict[str, Any] | None,
        current_goal: str | None,
        booking_payload: dict[str, Any] | None,
        last_reply_ref: str | None = None,
    ) -> ConversationProjectionV1:
        frame = (
            semantic_state.materialized_frame.model_copy(deep=True)
            if isinstance(semantic_state, CanonicalSemanticState)
            else SemanticFrame()
        )
        pending_contract = self.project_pending_question_contract(pending_question_contract) or {}
        contract = dict(semantic_contract) if isinstance(semantic_contract, dict) else {}
        if not contract and not self._is_synthetic_control_decision(decision):
            contract = self._semantic_contract_from_frame(frame) or {}
        slot_values = (
            frame.continuation.get("slot_values")
            if isinstance(frame.continuation, dict)
            and isinstance(frame.continuation.get("slot_values"), dict)
            else {}
        )
        semantic_slots = {
            key: value
            for key, value in (
                (field_name, self._normalize_projection_token(raw_value))
                for field_name, raw_value in slot_values.items()
            )
            if value
        }
        if not semantic_slots and isinstance(booking_payload, dict):
            for field_name in ("service", "datetime", "name", "phone"):
                value = self._normalize_projection_token(booking_payload.get(field_name))
                if value:
                    semantic_slots[field_name] = value
        active_capability = self._normalize_projection_token(
            frame.capability_selection.get("capability")
            if isinstance(frame.capability_selection, dict)
            else None
        ) or self._normalize_projection_token(contract.get("capability"))
        active_workflow_ref = None
        if isinstance(decision, PolicyDecision) and decision.binding_plan is not None:
            active_workflow_ref = self._normalize_projection_token(
                decision.binding_plan.selected_tool_or_workflow_ref
            )
        if active_workflow_ref is None and isinstance(decision, PolicyDecision):
            active_workflow_ref = self._normalize_projection_token(
                decision.tool_action
            )
        if active_workflow_ref is None and isinstance(existing_projection, ConversationProjectionV1):
            active_workflow_ref = self._normalize_projection_token(
                existing_projection.active_workflow_ref
            )
        pending_handoff_state: dict[str, Any] = {}
        if isinstance(decision, PolicyDecision) and (
            decision.outcome == "HANDOFF" or bool(decision.meta.get("degrade_path"))
        ):
            pending_handoff_state = {
                "active": True,
                "outcome": "handoff" if decision.outcome == "HANDOFF" else "degrade",
            }
            reason_code = self._normalize_projection_token(decision.meta.get("reason_code"))
            if reason_code:
                pending_handoff_state["reason_code"] = reason_code
        elif isinstance(existing_projection, ConversationProjectionV1) and isinstance(
            existing_projection.pending_handoff_state, dict
        ):
            pending_handoff_state = dict(existing_projection.pending_handoff_state)

        semantic_decision_ref = (
            decision.semantic_decision.decision_id
            if isinstance(decision, PolicyDecision) and decision.semantic_decision is not None
            else (
                existing_projection.current_semantic_decision_ref
                if isinstance(existing_projection, ConversationProjectionV1)
                else None
            )
        )
        last_turn_id = (
            semantic_decision_ref
            or (
                decision.binding_plan.decision_id
                if isinstance(decision, PolicyDecision) and decision.binding_plan is not None
                else (
                    existing_projection.last_turn_id
                    if isinstance(existing_projection, ConversationProjectionV1)
                    else None
                )
            )
        )
        projection = ConversationProjectionV1(
            conversation_id=conversation_id
            or (
                existing_projection.conversation_id
                if isinstance(existing_projection, ConversationProjectionV1)
                else None
            ),
            last_turn_id=last_turn_id,
            current_semantic_decision_ref=semantic_decision_ref,
            active_capability=active_capability,
            semantic_slots=semantic_slots,
            missing_information=dict(pending_contract),
            active_workflow_ref=active_workflow_ref,
            pending_handoff_state=pending_handoff_state,
            last_reply_ref=last_reply_ref
            or (
                existing_projection.last_reply_ref
                if isinstance(existing_projection, ConversationProjectionV1)
                else None
            ),
            compatibility_view_refs=self._compatibility_view_refs(),
            semantic_frame=frame,
            semantic_contract=contract,
            pending_question_contract=pending_contract,
            current_goal=self._normalize_projection_token(current_goal)
            or self.project_current_goal_from_frame(
                self.project_semantic_frame(frame)
            ),
            booking_state=self.normalize_booking_payload(booking_payload) or {},
        )
        return projection

    def _derive_dialog_state_from_projection(
        self,
        *,
        base_state: DialogState,
        projection: ConversationProjectionV1,
    ) -> DialogState:
        frame = projection.semantic_frame.model_copy(deep=True)
        pending_contract_payload = self.project_pending_question_contract(
            projection.pending_question_contract
        ) or {}
        expected = self.project_expected_reply_projections(
            expected_reply_type=pending_contract_payload.get("expected_reply_type"),
            expected_reply_reason=pending_contract_payload.get("reason"),
        )
        grounded_referents = self.project_grounded_referents_from_frame(
            self.project_semantic_frame(frame)
        )
        interaction_state = InteractionState(
            resume_slot=self._normalize_projection_token(
                pending_contract_payload.get("next_question")
            ),
            interaction_target=self._normalize_projection_token(
                pending_contract_payload.get("pending_question_target")
            ),
            interaction_relation=self._normalize_projection_token(
                pending_contract_payload.get("active_question_relation")
            ),
            interaction_owner=base_state.interaction_state.interaction_owner or "conversation_projection",
            grounded_referents=grounded_referents,
            confirmation_state=base_state.interaction_state.confirmation_state,
            degrade_reason=base_state.interaction_state.degrade_reason,
        )
        semantic_state = base_state.semantic_state.model_copy(
            update={"materialized_frame": frame},
            deep=True,
        )
        meta = dict(base_state.meta)
        meta["writer"] = "conversation_projection.v1"
        if projection.current_goal:
            meta["current_goal"] = projection.current_goal
        else:
            meta.pop("current_goal", None)
        if projection.semantic_contract:
            meta["semantic_contract"] = dict(projection.semantic_contract)
        else:
            meta.pop("semantic_contract", None)
        state = base_state.model_copy(
            update={
                "semantic_state": semantic_state,
                "current_referents": self._current_referents_from_grounded_referents(
                    grounded_referents
                ),
                "pending_question_contract": PendingQuestionContract.model_validate(
                    pending_contract_payload
                ),
                "interaction_state": interaction_state,
                "projections": DialogStateProjections(
                    expected_reply_type=expected.expected_reply_type,
                    expected_reply_reason=expected.expected_reply_reason,
                    session_memory_interaction_state=interaction_state,
                ),
                "meta": meta,
            },
            deep=True,
        )
        return self.project_state_compatibility_fields(
            state,
            expected_reply_type=expected.expected_reply_type,
            expected_reply_reason=expected.expected_reply_reason,
        )

    @staticmethod
    def project_semantic_frame(
        payload: SemanticFrame | dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if isinstance(payload, SemanticFrame):
            frame = payload.model_dump(mode="python", exclude_none=True)
        elif isinstance(payload, dict):
            try:
                frame = SemanticFrame.model_validate(payload).model_dump(
                    mode="python",
                    exclude_none=True,
                )
            except ValidationError:
                return None
        else:
            return None
        projected: dict[str, Any] = {}
        for key, value in frame.items():
            if key == "needs_human" and value is False:
                continue
            if value in (None, {}, []):
                continue
            projected[key] = value
        if projected == {"schema_version": "semantic_frame.v2"}:
            return None
        return projected or None

    def _normalize_semantic_referents(
        self,
        payload: Any,
    ) -> dict[str, dict[str, Any]]:
        if not isinstance(payload, dict):
            return {}
        normalized: dict[str, dict[str, Any]] = {}
        for referent_key in ("service", "specialist", "branch", "booking_ref", "customer"):
            raw_payload = payload.get(referent_key)
            if not isinstance(raw_payload, dict):
                continue
            item: dict[str, Any] = {}
            for field_name in ("value", "entity_id", "entity_type", "source_ref"):
                token = self._normalize_projection_token(raw_payload.get(field_name))
                if token:
                    item[field_name] = token
            if item:
                normalized[referent_key] = item
        return normalized

    def _current_referent_payloads(
        self,
        payload: CurrentReferents | dict[str, Any] | None,
    ) -> dict[str, dict[str, str]]:
        if isinstance(payload, CurrentReferents):
            source = payload.model_dump(mode="python", exclude_none=True)
        elif isinstance(payload, dict):
            source = dict(payload)
        else:
            source = {}
        normalized: dict[str, dict[str, str]] = {}
        for source_key, referent_key, entity_type in (
            ("service", "service", "service"),
            ("specialist", "specialist", "specialist"),
            ("branch", "branch", "branch"),
            ("booking", "booking_ref", "booking"),
            ("booking_ref", "booking_ref", "booking"),
            ("customer", "customer", "customer"),
        ):
            value = self._normalize_projection_token(source.get(source_key))
            if not value:
                continue
            normalized[referent_key] = {
                "value": value,
                "entity_type": entity_type,
                "source_ref": "carryover",
            }
        return normalized

    def project_current_goal_from_frame(
        self,
        frame: SemanticFrame | dict[str, Any] | None,
    ) -> str | None:
        payload = self.project_semantic_frame(frame)
        if not isinstance(payload, dict):
            return None
        return self._normalize_projection_token(payload.get("user_goal"))

    def project_current_referents_from_frame(
        self,
        frame: SemanticFrame | dict[str, Any] | None,
    ) -> CurrentReferents:
        referents = self._normalize_semantic_referents(
            (self.project_semantic_frame(frame) or {}).get("referents")
        )

        def _value(referent_key: str) -> str | None:
            payload = referents.get(referent_key)
            if not isinstance(payload, dict):
                return None
            return self._normalize_projection_token(
                payload.get("value") or payload.get("entity_id")
            )

        return CurrentReferents(
            service=_value("service"),
            specialist=_value("specialist"),
            branch=_value("branch"),
            booking=_value("booking_ref"),
            customer=_value("customer"),
        )

    def project_grounded_referents_from_frame(
        self,
        frame: SemanticFrame | dict[str, Any] | None,
    ) -> dict[str, str]:
        current_referents = self.project_current_referents_from_frame(frame)
        grounded: dict[str, str] = {}
        for source_key, value in (
            ("service", current_referents.service),
            ("specialist", current_referents.specialist),
            ("branch", current_referents.branch),
            ("booking_ref", current_referents.booking),
            ("customer", current_referents.customer),
        ):
            token = self._normalize_projection_token(value)
            if token:
                grounded[source_key] = token
        return grounded

    def _legacy_semantic_frame(
        self,
        *,
        current_goal: str | None,
        semantic_contract: dict[str, Any] | None,
        pending_question_contract: dict[str, Any] | None,
        booking_payload: dict[str, Any] | None,
        current_referents_payload: CurrentReferents | dict[str, Any] | None = None,
    ) -> SemanticFrame:
        contract = dict(semantic_contract) if isinstance(semantic_contract, dict) else {}
        pending = (
            dict(pending_question_contract)
            if isinstance(pending_question_contract, dict)
            else {}
        )
        booking = dict(booking_payload) if isinstance(booking_payload, dict) else {}
        subject: dict[str, Any] = {}
        subject_kind = self._normalize_projection_token(contract.get("subject_kind"))
        if subject_kind:
            subject["kind"] = subject_kind
        subject_value = None
        referents = self._normalize_semantic_referents(contract.get("referents"))
        for referent_key, payload in self._current_referent_payloads(
            current_referents_payload
        ).items():
            referents.setdefault(referent_key, payload)
        preferred_subject_key = {
            "service": "service",
            "specialist": "specialist",
            "branch": "branch",
            "booking": "booking_ref",
        }.get(subject_kind or "")
        if preferred_subject_key and isinstance(referents.get(preferred_subject_key), dict):
            subject_value = self._normalize_projection_token(
                referents[preferred_subject_key].get("value")
            )
        if subject_value is None:
            subject_value = self._normalize_projection_token(booking.get("service"))
        if subject_value:
            subject["value"] = subject_value
        entity_refs = contract.get("entity_refs")
        if isinstance(entity_refs, list) and entity_refs:
            subject["entity_refs"] = list(entity_refs)

        constraints: dict[str, Any] = {}
        for field_name in ("temporal_scope", "alternate_datetime", "grounding_provenance"):
            value = contract.get(field_name)
            if value not in (None, {}, []):
                constraints[field_name] = value
        preferences: dict[str, Any] = {}
        specialist = referents.get("specialist")
        if isinstance(specialist, dict) and specialist:
            preferences["specialist"] = dict(specialist)
        continuation: dict[str, Any] = {}
        for field_name in (
            "expected_reply_type",
            "reason",
            "pending_question_act",
            "pending_question_target",
            "active_question_relation",
            "next_question",
        ):
            value = pending.get(field_name)
            if value not in (None, {}, []):
                continuation[field_name] = value
        open_questions = pending.get("open_questions")
        if isinstance(open_questions, list) and open_questions:
            continuation["open_questions"] = list(open_questions)
        slot_values = {
            key: value
            for key, value in booking.items()
            if key in _BOOKING_CONTEXT_SLOT_KEYS and isinstance(value, str) and value.strip()
        }
        if slot_values:
            continuation["slot_values"] = slot_values

        capability_selection: dict[str, Any] = {}
        for field_name in ("capability", "resolution_mode"):
            value = contract.get(field_name)
            if value not in (None, {}, []):
                capability_selection[field_name] = value
        pack_id = constraints.get("grounding_provenance", {}).get("pack_id") if isinstance(
            constraints.get("grounding_provenance"), dict
        ) else None
        if isinstance(pack_id, str) and pack_id.strip():
            capability_selection["pack_refs"] = [pack_id.strip()]

        return SemanticFrame(
            user_goal=self._normalize_projection_token(current_goal),
            requested_effect=None,
            subject=subject,
            referents=referents,
            constraints=constraints,
            preferences=preferences,
            continuation=continuation,
            capability_selection=capability_selection,
            needs_human=bool(self._normalize_projection_token(current_goal) == "handoff"),
            reason=self._normalize_projection_token(pending.get("reason")),
        )

    def _merge_semantic_frame(
        self,
        *,
        existing: SemanticFrame | None,
        decision: PolicyDecision,
        execution_payload: dict[str, Any] | None,
        current_goal: str | None,
        booking_payload: dict[str, Any] | None,
    ) -> SemanticFrame:
        owner_frame = self._canonical_decision_semantic_frame(decision)
        owner_payload = self.project_semantic_frame(owner_frame) or {}
        existing_payload = self.project_semantic_frame(existing) or {}
        decision_payload = owner_payload
        if (
            not decision_payload
            and not self._has_canonical_semantic_owner(decision)
            and not self._is_synthetic_control_decision(decision)
        ):
            decision_payload = self.project_semantic_frame(decision.semantic_frame) or {}
        materialized = deepcopy(owner_payload) if owner_payload else deepcopy(existing_payload)
        for section_name in (
            "subject",
            "referents",
            "constraints",
            "preferences",
            "continuation",
            "capability_selection",
        ):
            materialized.setdefault(section_name, {})
        for key in ("user_goal", "requested_effect", "needs_human", "reason"):
            if decision_payload.get(key) not in (None, {}, []):
                materialized[key] = decision_payload[key]
        for section_name in (
            "subject",
            "constraints",
            "preferences",
            "continuation",
            "capability_selection",
        ):
            incoming = decision_payload.get(section_name)
            if isinstance(incoming, dict) and incoming:
                materialized[section_name].update(incoming)
        incoming_pending_contract = self._canonical_decision_pending_question_contract(decision)
        if (
            not incoming_pending_contract
            and not self._has_canonical_semantic_owner(decision)
            and not self._is_synthetic_control_decision(decision)
        ):
            incoming_pending_contract = (
                self.project_pending_question_contract(decision.pending_question_contract) or {}
            )
        if isinstance(incoming_pending_contract, dict) and incoming_pending_contract:
            for field_name in (
                "expected_reply_type",
                "reason",
                "pending_question_act",
                "pending_question_target",
                "active_question_relation",
                "next_question",
                "open_questions",
            ):
                materialized["continuation"].pop(field_name, None)
            for field_name in (
                "expected_reply_type",
                "reason",
                "pending_question_act",
                "pending_question_target",
                "active_question_relation",
                "next_question",
            ):
                value = incoming_pending_contract.get(field_name)
                if value not in (None, {}, []):
                    materialized["continuation"][field_name] = value
            open_questions = incoming_pending_contract.get("open_questions")
            if isinstance(open_questions, list) and open_questions:
                materialized["continuation"]["open_questions"] = list(open_questions)
        incoming_referents = decision_payload.get("referents")
        if isinstance(incoming_referents, dict) and incoming_referents:
            for referent_key, referent_payload in incoming_referents.items():
                if not isinstance(referent_payload, dict):
                    continue
                current_referent = materialized["referents"].get(referent_key)
                if isinstance(current_referent, dict):
                    merged = dict(current_referent)
                    merged.update(referent_payload)
                    materialized["referents"][referent_key] = merged
                else:
                    materialized["referents"][referent_key] = dict(referent_payload)

        execution = dict(execution_payload) if isinstance(execution_payload, dict) else {}
        execution_contract = self._execution_semantic_payload(
            execution,
            owner_only=self._has_canonical_semantic_owner(decision),
        )
        if execution_contract:
            execution_entity_refs = execution_contract.get("entity_refs")
            if isinstance(execution_entity_refs, list) and execution_entity_refs:
                existing_entity_refs = self._normalize_semantic_entity_refs(
                    materialized["subject"].get("entity_refs")
                )
                existing_entity_refs.extend(
                    self._normalize_semantic_entity_refs(execution_entity_refs)
                )
                normalized_entity_refs = self._normalize_semantic_entity_refs(existing_entity_refs)
                if normalized_entity_refs:
                    materialized["subject"]["entity_refs"] = normalized_entity_refs
            grounding_provenance = self._normalize_grounding_provenance(
                execution_contract.get("grounding_provenance")
            )
            if grounding_provenance:
                materialized["constraints"]["grounding_provenance"] = grounding_provenance
            execution_referents = self._normalize_semantic_referents(
                execution_contract.get("referents")
            )
            for referent_key, referent_payload in execution_referents.items():
                current_referent = materialized["referents"].get(referent_key)
                if isinstance(current_referent, dict):
                    current_value = self._normalize_projection_token(current_referent.get("value"))
                    incoming_value = self._normalize_projection_token(referent_payload.get("value"))
                    if current_value and incoming_value and current_value.casefold() != incoming_value.casefold():
                        continue
                    merged = dict(current_referent)
                    merged.update(referent_payload)
                    materialized["referents"][referent_key] = merged
                else:
                    materialized["referents"][referent_key] = referent_payload

        slot_values = execution.get("slot_values")
        if isinstance(slot_values, dict) and slot_values:
            cleaned_slots = {
                key: value.strip()
                for key, value in slot_values.items()
                if key in _BOOKING_CONTEXT_SLOT_KEYS and isinstance(value, str) and value.strip()
            }
            if cleaned_slots:
                materialized["continuation"]["slot_values"] = cleaned_slots
        if owner_payload:
            materialized["user_goal"] = decision_payload.get("user_goal")
        elif not materialized.get("user_goal"):
            goal = self._normalize_projection_token(current_goal)
            if goal:
                materialized["user_goal"] = goal
            elif isinstance(booking_payload, dict) and booking_payload:
                materialized["user_goal"] = "booking"
        if decision.outcome == "HANDOFF":
            materialized["needs_human"] = True
            materialized["requested_effect"] = "handoff_to_human"
            materialized["continuation"] = {}

        cleaned = {
            key: value
            for key, value in materialized.items()
            if value not in (None, {}, [])
        }
        return SemanticFrame.model_validate(cleaned)

    def _build_semantic_state(
        self,
        *,
        existing_state: DialogState,
        decision: PolicyDecision,
        execution_payload: dict[str, Any] | None,
        current_goal: str | None,
        booking_payload: dict[str, Any] | None,
        now: datetime,
    ) -> CanonicalSemanticState:
        existing_semantic_state = (
            existing_state.semantic_state
            if isinstance(existing_state.semantic_state, CanonicalSemanticState)
            else CanonicalSemanticState()
        )
        base_frame = existing_semantic_state.materialized_frame
        if not self.project_semantic_frame(base_frame):
            base_frame = self._legacy_semantic_frame(
                current_goal=current_goal,
                semantic_contract=(
                    dict(existing_state.meta.get("semantic_contract"))
                    if isinstance(existing_state.meta.get("semantic_contract"), dict)
                    else None
                ),
                pending_question_contract=self.project_pending_question_contract_with_projection_fallback(
                    existing_state.pending_question_contract,
                    expected_reply_type=existing_state.projections.expected_reply_type,
                    expected_reply_reason=existing_state.projections.expected_reply_reason,
                ),
                booking_payload=booking_payload,
                current_referents_payload=existing_state.current_referents,
            )
        materialized_frame = self._merge_semantic_frame(
            existing=base_frame,
            decision=decision,
            execution_payload=execution_payload,
            current_goal=current_goal,
            booking_payload=booking_payload,
        )
        event = SemanticStateEvent(
            at=now.isoformat(),
            source=decision.source,
            outcome=decision.outcome,
            action=decision.action,
            intent=decision.intent,
            tool_action=decision.tool_action,
            reason_code=self._normalize_projection_token(
                (execution_payload or {}).get("reason_code")
                or decision.meta.get("reason_code")
            ),
            semantic_frame=materialized_frame,
        )
        return CanonicalSemanticState(
            materialized_frame=materialized_frame,
            event_log=[*existing_semantic_state.event_log, event],
        )

    @staticmethod
    def _has_canonical_semantic_owner(decision: PolicyDecision) -> bool:
        return isinstance(getattr(decision, "semantic_decision", None), BaseModel)

    @staticmethod
    def _is_synthetic_control_decision(decision: PolicyDecision | None) -> bool:
        return bool(
            isinstance(decision, PolicyDecision) and decision.is_synthetic_control_decision()
        )

    def _canonical_decision_semantic_frame(
        self,
        decision: PolicyDecision,
    ) -> SemanticFrame | None:
        if not self._has_canonical_semantic_owner(decision):
            return None
        frame = TurnPlanner().canonical_semantic_frame(decision)
        if not isinstance(frame, SemanticFrame):
            return None
        return frame.model_copy(deep=True)

    def _canonical_decision_semantic_contract(
        self,
        decision: PolicyDecision,
    ) -> dict[str, Any]:
        if not self._has_canonical_semantic_owner(decision):
            return {}
        contract = TurnPlanner().canonical_semantic_contract(decision)
        return dict(contract) if isinstance(contract, dict) else {}

    def _canonical_decision_pending_question_contract(
        self,
        decision: PolicyDecision,
    ) -> dict[str, Any]:
        if not self._has_canonical_semantic_owner(decision):
            return {}
        pending_question = TurnPlanner().canonical_pending_question_contract(decision)
        return self.project_pending_question_contract(pending_question) or {}

    def _decision_pending_question_contract(
        self,
        decision: PolicyDecision,
    ) -> PendingQuestionContract:
        if self._has_canonical_semantic_owner(decision):
            return TurnPlanner().canonical_pending_question_contract(decision)
        if self._is_synthetic_control_decision(decision):
            return PendingQuestionContract()
        return decision.pending_question_contract

    def _decision_semantic_contract(
        self,
        decision: PolicyDecision,
    ) -> dict[str, Any]:
        canonical_contract = self._canonical_decision_semantic_contract(decision)
        if canonical_contract:
            return canonical_contract
        if self._is_synthetic_control_decision(decision):
            return {}
        return (
            self._semantic_contract_from_frame(decision.semantic_frame)
            or (
                dict(decision.meta.get("semantic_contract"))
                if isinstance(decision.meta.get("semantic_contract"), dict)
                else {}
            )
        )

    def _execution_semantic_enrichment_from_contract(
        self,
        semantic_contract: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not isinstance(semantic_contract, dict):
            return {}
        enrichment: dict[str, Any] = {}
        referents = self._normalize_semantic_referents(semantic_contract.get("referents"))
        if referents:
            enrichment["referents"] = deepcopy(referents)
        entity_refs = self._normalize_semantic_entity_refs(semantic_contract.get("entity_refs"))
        if entity_refs:
            enrichment["entity_refs"] = deepcopy(entity_refs)
        grounding_provenance = self._normalize_grounding_provenance(
            semantic_contract.get("grounding_provenance")
        )
        if grounding_provenance:
            enrichment["grounding_provenance"] = deepcopy(grounding_provenance)
        return enrichment

    def _execution_semantic_payload(
        self,
        payload: dict[str, Any] | None,
        *,
        owner_only: bool,
    ) -> dict[str, Any]:
        execution_payload = dict(payload) if isinstance(payload, dict) else {}
        enrichment = execution_payload.get("semantic_enrichment")
        if isinstance(enrichment, dict) and enrichment:
            return dict(enrichment)
        semantic_contract = execution_payload.get("semantic_contract")
        if not isinstance(semantic_contract, dict):
            return {}
        if owner_only:
            return self._execution_semantic_enrichment_from_contract(semantic_contract)
        return dict(semantic_contract)

    def _semantic_contract_from_frame(
        self,
        frame: SemanticFrame | dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        payload = self.project_semantic_frame(frame)
        if not isinstance(payload, dict):
            return None
        subject = payload.get("subject") if isinstance(payload.get("subject"), dict) else {}
        constraints = (
            payload.get("constraints")
            if isinstance(payload.get("constraints"), dict)
            else {}
        )
        continuation = (
            payload.get("continuation")
            if isinstance(payload.get("continuation"), dict)
            else {}
        )
        capability_selection = (
            payload.get("capability_selection")
            if isinstance(payload.get("capability_selection"), dict)
            else {}
        )
        contract: dict[str, Any] = {"contract_version": "semantic_contract.v1"}
        for field_name, value in (
            ("subject_kind", subject.get("kind")),
            ("capability", capability_selection.get("capability")),
            ("temporal_scope", constraints.get("temporal_scope")),
            ("resolution_mode", capability_selection.get("resolution_mode")),
            ("pending_question_act", continuation.get("pending_question_act")),
            ("pending_question_target", continuation.get("pending_question_target")),
            ("active_question_relation", continuation.get("active_question_relation")),
            ("alternate_datetime", constraints.get("alternate_datetime")),
        ):
            if value not in (None, {}, []):
                contract[field_name] = value
        grounding_provenance = self._normalize_grounding_provenance(
            constraints.get("grounding_provenance")
        )
        if grounding_provenance:
            contract["grounding_provenance"] = grounding_provenance
        referents = self._normalize_semantic_referents(payload.get("referents"))
        if referents:
            contract["referents"] = referents
        entity_refs = subject.get("entity_refs")
        if isinstance(entity_refs, list) and entity_refs:
            contract["entity_refs"] = list(entity_refs)
        return contract if len(contract) > 1 else None

    def _pending_question_from_frame(
        self,
        frame: SemanticFrame | dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        payload = self.project_semantic_frame(frame)
        if not isinstance(payload, dict):
            return None
        continuation = (
            payload.get("continuation")
            if isinstance(payload.get("continuation"), dict)
            else {}
        )
        projected = self.project_pending_question_contract(
            continuation,
            expected_reply_reason=self._normalize_projection_token(
                (
                    continuation.get("reason")
                    if isinstance(continuation, dict)
                    else None
                )
                or payload.get("reason")
            ),
        )
        if not isinstance(projected, dict):
            return None
        if not any(
            projected.get(field_name)
            for field_name in (
                "expected_reply_type",
                "pending_question_act",
                "pending_question_target",
                "active_question_relation",
                "next_question",
            )
        ) and not projected.get("open_questions"):
            return None
        return projected

    def project_runtime_semantic_frame(
        self,
        state: DialogState,
        *,
        booking_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        frame = self.project_semantic_frame(state.semantic_state.materialized_frame)
        if isinstance(frame, dict):
            return frame
        return self.project_semantic_frame(
            self._legacy_semantic_frame(
                current_goal=(
                    state.meta.get("current_goal")
                    if isinstance(state.meta, dict)
                    else None
                ),
                semantic_contract=(
                    dict(state.meta.get("semantic_contract"))
                    if isinstance(state.meta, dict)
                    and isinstance(state.meta.get("semantic_contract"), dict)
                    else None
                ),
                pending_question_contract=self.project_pending_question_contract_with_projection_fallback(
                    state.pending_question_contract,
                    expected_reply_type=state.projections.expected_reply_type,
                    expected_reply_reason=state.projections.expected_reply_reason,
                ),
                booking_payload=self.normalize_booking_payload(booking_payload),
                current_referents_payload=state.current_referents,
            )
        )

    def project_runtime_current_goal(
        self,
        state: DialogState,
        *,
        booking_payload: dict[str, Any] | None = None,
    ) -> str | None:
        return self.project_current_goal_from_frame(
            self.project_runtime_semantic_frame(
                state,
                booking_payload=booking_payload,
            )
        )

    def project_runtime_semantic_contract(
        self,
        state: DialogState,
        *,
        booking_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return self._semantic_contract_from_frame(
            self.project_runtime_semantic_frame(
                state,
                booking_payload=booking_payload,
            )
        )

    def project_runtime_pending_question_contract(
        self,
        state: DialogState,
        *,
        booking_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        frame_pending_question_contract = self._pending_question_from_frame(
            self.project_runtime_semantic_frame(
                state,
                booking_payload=booking_payload,
            )
        )
        return self.project_pending_question_contract(
            frame_pending_question_contract,
            expected_reply_type=(
                None
                if isinstance(frame_pending_question_contract, dict)
                and frame_pending_question_contract.get("expected_reply_type")
                else state.projections.expected_reply_type
            ),
            expected_reply_reason=(
                None
                if isinstance(frame_pending_question_contract, dict)
                and frame_pending_question_contract.get("reason")
                else state.projections.expected_reply_reason
            ),
        )

    def project_state_compatibility_fields(
        self,
        state: DialogState,
        *,
        expected_reply_type: str | None = None,
        expected_reply_reason: str | None = None,
    ) -> DialogState:
        frame = state.semantic_state.materialized_frame
        derived_pending_question_contract = self._pending_question_from_frame(frame)
        if isinstance(derived_pending_question_contract, dict):
            pending_question_contract = self.project_pending_question_contract(
                derived_pending_question_contract,
                expected_reply_type=(
                    None
                    if derived_pending_question_contract.get("expected_reply_type")
                    else expected_reply_type
                ),
                expected_reply_reason=(
                    None
                    if derived_pending_question_contract.get("reason")
                    else expected_reply_reason
                ),
            ) or {}
        else:
            pending_question_contract = self.project_pending_question_contract_with_projection_fallback(
                state.pending_question_contract,
                expected_reply_type=expected_reply_type,
                expected_reply_reason=expected_reply_reason,
            ) or {}
        projections = self.project_expected_reply_projections(
            state.projections,
            expected_reply_type=(
                pending_question_contract.get("expected_reply_type") or expected_reply_type
            ),
            expected_reply_reason=(
                pending_question_contract.get("reason") or expected_reply_reason
            ),
        )
        grounded_referents = self.project_grounded_referents_from_frame(frame)
        interaction_update: dict[str, Any] = {}
        if grounded_referents:
            interaction_update["grounded_referents"] = grounded_referents
        meta = dict(state.meta)
        current_goal = self.project_current_goal_from_frame(frame)
        if current_goal:
            meta["current_goal"] = current_goal
        else:
            meta.pop("current_goal", None)
        semantic_contract = self._semantic_contract_from_frame(frame)
        if semantic_contract:
            meta["semantic_contract"] = semantic_contract
        else:
            meta.pop("semantic_contract", None)
        return state.model_copy(
            update={
                "current_referents": self.project_current_referents_from_frame(frame),
                "pending_question_contract": PendingQuestionContract.model_validate(
                    pending_question_contract
                ),
                "interaction_state": state.interaction_state.model_copy(
                    update=interaction_update
                ),
                "projections": projections,
                "meta": meta,
            }
        )

    def build_degraded_state(
        self,
        *,
        reason_code: str,
        interaction_owner: str,
        interaction_target: str | None = None,
        interaction_relation: str | None = None,
    ) -> DialogState:
        interaction_state = InteractionState(
            interaction_target=interaction_target,
            interaction_relation=interaction_relation,
            interaction_owner=interaction_owner,
            degrade_reason=reason_code,
        )
        return DialogState(
            interaction_state=interaction_state,
            projections=DialogStateProjections(
                session_memory_interaction_state=interaction_state,
            ),
            meta={
                "writer": "dialog_state_service",
                "degrade_path": True,
            },
        )

    def build_blocked_state(
        self,
        *,
        reason_code: str,
        interaction_owner: str,
        interaction_target: str | None = None,
        interaction_relation: str | None = None,
    ) -> DialogState:
        interaction_state = InteractionState(
            interaction_target=interaction_target,
            interaction_relation=interaction_relation,
            interaction_owner=interaction_owner,
            degrade_reason=reason_code,
        )
        return DialogState(
            interaction_state=interaction_state,
            projections=DialogStateProjections(
                session_memory_interaction_state=interaction_state,
            ),
            meta={
                "writer": "dialog_state_service",
                "block_path": True,
            },
        )

    def build_collect_owner_state(
        self,
        *,
        decision: PolicyDecision,
        expected_reply_type: str,
        expected_reply_reason: str | None = None,
        grounded_referents: dict[str, str] | None = None,
        owner_cutover: str | None = None,
    ) -> DialogState:
        expected_reply_token = self._normalize_projection_token(expected_reply_type)
        if not expected_reply_token:
            raise ValueError("expected_reply_type_invalid")

        reason_token = self._normalize_projection_token(expected_reply_reason)
        pending_contract = self._decision_pending_question_contract(decision)
        next_question = self._normalize_projection_token(pending_contract.next_question)
        open_questions = [
            token
            for token in (
                self._normalize_projection_token(item)
                for item in pending_contract.open_questions
            )
            if token
        ]
        if not open_questions and next_question:
            open_questions = [next_question]

        interaction_target = (
            self._normalize_projection_token(decision.interaction.target)
            or self._normalize_projection_token(pending_contract.pending_question_target)
        )
        interaction_relation = (
            self._normalize_projection_token(decision.interaction.relation)
            or self._normalize_projection_token(pending_contract.active_question_relation)
        )
        pending_question_act = (
            self._normalize_projection_token(pending_contract.pending_question_act)
            or self._normalize_projection_token(decision.meta.get("pending_question_act"))
        )
        interaction_owner = self.build_interaction_owner(
            explicit_owner=decision.interaction.owner,
            interaction_relation=interaction_relation,
            question_reason=reason_token,
        )
        resume_slot = (
            _CANONICAL_EXPECTED_REPLY_SLOT_BY_TYPE.get(expected_reply_token)
            or next_question
            or interaction_target
        )

        normalized_grounded: dict[str, str] = {}
        current_referents: dict[str, str] = {}
        referent_map = {
            "service": "service",
            "specialist": "specialist",
            "branch": "branch",
            "booking_ref": "booking",
            "customer": "customer",
        }
        if isinstance(grounded_referents, dict):
            for source_key, state_key in referent_map.items():
                referent_value = self._normalize_projection_token(grounded_referents.get(source_key))
                if not referent_value:
                    continue
                normalized_grounded[source_key] = referent_value
                current_referents[state_key] = referent_value

        interaction_state = InteractionState(
            resume_slot=resume_slot,
            interaction_target=interaction_target,
            interaction_relation=interaction_relation,
            interaction_owner=interaction_owner,
            grounded_referents=normalized_grounded,
        )
        meta: dict[str, Any] = {
            "writer": "dialog_state_service",
            "owner_replacement_cutover": True,
        }
        if owner_cutover:
            meta["owner_cutover"] = owner_cutover
        pending_question_payload = self.project_pending_question_contract(
            pending_contract,
            expected_reply_type=expected_reply_token,
            expected_reply_reason=reason_token,
            pending_question_act=pending_question_act,
            pending_question_target=interaction_target,
            active_question_relation=interaction_relation,
            next_question=next_question,
            open_questions=open_questions,
        )
        return DialogState(
            current_referents=CurrentReferents(**current_referents),
            pending_question_contract=PendingQuestionContract.model_validate(
                pending_question_payload or {}
            ),
            interaction_state=interaction_state,
            projections=DialogStateProjections(
                expected_reply_type=expected_reply_token,
                expected_reply_reason=reason_token,
                session_memory_interaction_state=interaction_state,
            ),
            meta=meta,
        )

    def project_pending_question_contract(
        self,
        contract: PendingQuestionContract | dict[str, Any] | None,
        *,
        expected_reply_type: str | None = None,
        expected_reply_reason: str | None = None,
        pending_question_act: str | None = None,
        pending_question_target: str | None = None,
        active_question_relation: str | None = None,
        next_question: str | None = None,
        open_questions: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any] | None:
        base_payload: dict[str, Any]
        if isinstance(contract, PendingQuestionContract):
            base_payload = contract.model_dump(mode="json", exclude_none=True)
        elif isinstance(contract, dict):
            base_payload = dict(contract)
        else:
            base_payload = {}
        normalized_next_question = self._normalize_projection_token(
            next_question
            if next_question is not None
            else base_payload.get("next_question") or base_payload.get("slot")
        )
        normalized_open_questions = [
            token
            for token in (
                self._normalize_projection_token(item)
                for item in (
                    open_questions
                    if isinstance(open_questions, (list, tuple))
                    else base_payload.get("open_questions", ())
                )
            )
            if token
        ]
        if not normalized_open_questions and normalized_next_question:
            normalized_open_questions = [normalized_next_question]
        normalized_expected_reply_type = self._normalize_projection_token(
            expected_reply_type if expected_reply_type is not None else base_payload.get("expected_reply_type")
        )
        if not normalized_expected_reply_type and normalized_next_question:
            normalized_expected_reply_type = {
                "service": "service_choice",
                "datetime": "time",
                "name": "name",
                "phone": "phone",
                "media": "media",
            }.get(normalized_next_question)
        normalized_reason = self._normalize_projection_token(
            expected_reply_reason if expected_reply_reason is not None else base_payload.get("reason")
        )
        normalized_pending_question_act = self._normalize_projection_token(
            pending_question_act
            if pending_question_act is not None
            else base_payload.get("pending_question_act")
        )
        normalized_pending_question_target = self._normalize_projection_token(
            pending_question_target
            if pending_question_target is not None
            else base_payload.get("pending_question_target")
        )
        normalized_active_question_relation = self._normalize_projection_token(
            active_question_relation
            if active_question_relation is not None
            else base_payload.get("active_question_relation")
        )
        payload: dict[str, Any] = {}
        if normalized_expected_reply_type:
            payload["expected_reply_type"] = normalized_expected_reply_type
        if normalized_reason:
            payload["reason"] = normalized_reason
        if normalized_pending_question_act:
            payload["pending_question_act"] = normalized_pending_question_act
        if normalized_pending_question_target:
            payload["pending_question_target"] = normalized_pending_question_target
        if normalized_active_question_relation:
            payload["active_question_relation"] = normalized_active_question_relation
        if normalized_next_question:
            payload["next_question"] = normalized_next_question
        if normalized_open_questions:
            payload["open_questions"] = normalized_open_questions
        return payload or None

    def project_interrupt_resume_pending_question_contract(
        self,
        pending_question_contract: PendingQuestionContract | dict[str, Any] | None,
        *,
        current_goal: str | None,
        booking_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        projected = self.project_pending_question_contract(pending_question_contract) or {}
        if projected.get("expected_reply_type") != "media":
            return None
        if self._normalize_projection_token(current_goal) != "booking":
            return None
        normalized_booking = self.normalize_booking_payload(booking_payload) or {}
        pending_question_act = self._normalize_projection_token(
            projected.get("pending_question_act")
        )
        pending_question_target = self._normalize_projection_token(
            projected.get("pending_question_target")
        )
        active_question_relation = self._normalize_projection_token(
            projected.get("active_question_relation")
        )
        if (
            not pending_question_target
            and self._normalize_projection_token(normalized_booking.get("service"))
            and not self._normalize_projection_token(normalized_booking.get("datetime"))
        ):
            pending_question_act = pending_question_act or "ask_about_requested_slot"
            pending_question_target = "time"
            active_question_relation = (
                active_question_relation or "ask_about_requested_slot"
            )
        if pending_question_target != "time":
            return None
        return self.project_pending_question_contract(
            {
                "expected_reply_type": "time",
                "next_question": "datetime",
                "open_questions": ["datetime"],
                "pending_question_act": pending_question_act,
                "pending_question_target": pending_question_target,
                "active_question_relation": active_question_relation,
            }
        )

    def project_context_pending_question_contract(
        self,
        context: dict[str, Any] | None,
        *,
        runtime_key: str = _RUNTIME_CONTEXT_KEY,
        context_manager_key: str = "context_manager",
        canonical_state_key: str = "canonical_dialog_state",
        session_memory_key: str = "session_memory",
        expected_reply_type_key: str = "expected_reply_type",
        expected_reply_reason_key: str = "expected_reply_reason",
    ) -> dict[str, Any] | None:
        if not isinstance(context, dict):
            return None

        runtime_payload = context.get(runtime_key) if isinstance(context.get(runtime_key), dict) else None
        runtime_projection = self.normalize_runtime_conversation_projection(
            runtime_payload.get("conversation_projection")
            if isinstance(runtime_payload, dict)
            else None
        )
        if isinstance(runtime_projection, ConversationProjectionV1):
            projected = self.project_pending_question_contract(
                runtime_projection.pending_question_contract,
                expected_reply_type=(
                    runtime_projection.missing_information.get("expected_reply_type")
                    if isinstance(runtime_projection.missing_information, dict)
                    else None
                ),
                expected_reply_reason=(
                    runtime_projection.missing_information.get("reason")
                    if isinstance(runtime_projection.missing_information, dict)
                    else None
                ),
            )
            if projected is not None:
                return projected
        runtime_dialog_state = (
            runtime_payload.get("dialog_state") if isinstance(runtime_payload, dict) else None
        )
        runtime_semantic_state = (
            runtime_dialog_state.get("semantic_state")
            if isinstance(runtime_dialog_state, dict)
            and isinstance(runtime_dialog_state.get("semantic_state"), dict)
            else None
        )
        runtime_frame = (
            runtime_semantic_state.get("materialized_frame")
            if isinstance(runtime_semantic_state, dict)
            and isinstance(runtime_semantic_state.get("materialized_frame"), dict)
            else None
        )
        runtime_projections = self.project_expected_reply_projections(
            expected_reply_type=(
                runtime_dialog_state.get("projections", {}).get("expected_reply_type")
                if isinstance(runtime_dialog_state, dict)
                and isinstance(runtime_dialog_state.get("projections"), dict)
                else (runtime_payload.get("expected_reply_type") if isinstance(runtime_payload, dict) else None)
            ),
            expected_reply_reason=(
                runtime_dialog_state.get("projections", {}).get("expected_reply_reason")
                if isinstance(runtime_dialog_state, dict)
                and isinstance(runtime_dialog_state.get("projections"), dict)
                else (runtime_payload.get("expected_reply_reason") if isinstance(runtime_payload, dict) else None)
            ),
        )
        runtime_pending_question_contract = self._pending_question_from_frame(
            runtime_frame
        ) or self.project_pending_question_contract(
            runtime_dialog_state.get("pending_question_contract")
            if isinstance(runtime_dialog_state, dict)
            else (
                runtime_payload.get("pending_question_contract")
                if isinstance(runtime_payload, dict)
                else None
            )
        )
        if runtime_pending_question_contract is not None:
            return self.project_pending_question_contract(
                runtime_pending_question_contract,
                expected_reply_type=(
                    None
                    if runtime_pending_question_contract.get("expected_reply_type")
                    else runtime_projections.expected_reply_type
                ),
                expected_reply_reason=(
                    None
                    if runtime_pending_question_contract.get("reason")
                    else runtime_projections.expected_reply_reason
                ),
            )
        if runtime_projections.expected_reply_type or runtime_projections.expected_reply_reason:
            return self.project_pending_question_contract(
                None,
                expected_reply_type=runtime_projections.expected_reply_type,
                expected_reply_reason=runtime_projections.expected_reply_reason,
            )

        projections = self.project_expected_reply_projections(
            expected_reply_type=context.get(expected_reply_type_key),
            expected_reply_reason=context.get(expected_reply_reason_key),
        )

        context_manager = (
            context.get(context_manager_key)
            if isinstance(context.get(context_manager_key), dict)
            else None
        )
        canonical_state = self.normalize_context_manager_canonical_state(
            context_manager.get(canonical_state_key)
            if isinstance(context_manager, dict)
            else None
        )
        pending_question_contract = self.project_pending_question_contract(
            canonical_state.get("pending_question_contract")
            if isinstance(canonical_state, dict)
            else None
        )
        if pending_question_contract is None:
            session_memory = (
                context.get(session_memory_key)
                if isinstance(context.get(session_memory_key), dict)
                else None
            )
            pending_question_contract = self.project_pending_question_contract(
                session_memory.get("pending_question_contract")
                if isinstance(session_memory, dict)
                else None
            )

        if pending_question_contract is not None:
            return self.project_pending_question_contract(
                pending_question_contract,
                expected_reply_type=(
                    None
                    if pending_question_contract.get("expected_reply_type")
                    else projections.expected_reply_type
                ),
                expected_reply_reason=(
                    None
                    if pending_question_contract.get("reason")
                    else projections.expected_reply_reason
                ),
            )

        return self.project_pending_question_contract(
            None,
            expected_reply_type=projections.expected_reply_type,
            expected_reply_reason=projections.expected_reply_reason,
        )

    def project_context_manager_pending_question_contract(
        self,
        context: dict[str, Any] | None,
        *,
        context_manager_key: str = "context_manager",
        canonical_state_key: str = "canonical_dialog_state",
    ) -> dict[str, Any] | None:
        if not isinstance(context, dict):
            return None

        context_manager = (
            context.get(context_manager_key)
            if isinstance(context.get(context_manager_key), dict)
            else None
        )
        canonical_state = self.normalize_context_manager_canonical_state(
            context_manager.get(canonical_state_key)
            if isinstance(context_manager, dict)
            else None
        )
        return self.project_pending_question_contract(
            canonical_state.get("pending_question_contract")
            if isinstance(canonical_state, dict)
            else None
        )

    def project_context_current_goal(
        self,
        context: dict[str, Any] | None,
        *,
        runtime_key: str = _RUNTIME_CONTEXT_KEY,
        context_manager_key: str = "context_manager",
        canonical_state_key: str = "canonical_dialog_state",
    ) -> str | None:
        if not isinstance(context, dict):
            return None

        runtime_payload = context.get(runtime_key) if isinstance(context.get(runtime_key), dict) else None
        runtime_projection = self.normalize_runtime_conversation_projection(
            runtime_payload.get("conversation_projection")
            if isinstance(runtime_payload, dict)
            else None
        )
        if isinstance(runtime_projection, ConversationProjectionV1):
            projection_goal = self._normalize_projection_token(runtime_projection.current_goal)
            if projection_goal:
                return projection_goal
            frame_goal = self.project_current_goal_from_frame(
                self.project_semantic_frame(runtime_projection.semantic_frame)
            )
            if frame_goal:
                return frame_goal
        runtime_dialog_state = (
            runtime_payload.get("dialog_state") if isinstance(runtime_payload, dict) else None
        )
        runtime_semantic_state = (
            runtime_dialog_state.get("semantic_state")
            if isinstance(runtime_dialog_state, dict)
            and isinstance(runtime_dialog_state.get("semantic_state"), dict)
            else None
        )
        runtime_frame = (
            runtime_semantic_state.get("materialized_frame")
            if isinstance(runtime_semantic_state, dict)
            and isinstance(runtime_semantic_state.get("materialized_frame"), dict)
            else None
        )
        runtime_frame_goal = self.project_current_goal_from_frame(runtime_frame)
        if runtime_frame_goal:
            return runtime_frame_goal
        runtime_meta = runtime_dialog_state.get("meta") if isinstance(runtime_dialog_state, dict) else None
        runtime_dialog_goal = self._normalize_projection_token(
            runtime_meta.get("current_goal") if isinstance(runtime_meta, dict) else None
        )
        if runtime_dialog_goal:
            return runtime_dialog_goal

        context_manager = (
            context.get(context_manager_key)
            if isinstance(context.get(context_manager_key), dict)
            else None
        )
        canonical_state = self.normalize_context_manager_canonical_state(
            context_manager.get(canonical_state_key) if isinstance(context_manager, dict) else None
        )
        canonical_meta = canonical_state.get("meta") if isinstance(canonical_state, dict) else None
        canonical_goal = self._normalize_projection_token(
            canonical_meta.get("current_goal") if isinstance(canonical_meta, dict) else None
        )
        if canonical_goal:
            return canonical_goal

        manager_goal = self._normalize_projection_token(
            context_manager.get("current_goal") if isinstance(context_manager, dict) else None
        )
        if manager_goal:
            return manager_goal

        runtime_goal = self._normalize_projection_token(
            runtime_payload.get("current_goal") if isinstance(runtime_payload, dict) else None
        )
        if runtime_goal:
            return runtime_goal

        return self._normalize_projection_token(context.get("current_goal"))

    def project_context_service_referent(
        self,
        context: dict[str, Any] | None,
        *,
        runtime_key: str = _RUNTIME_CONTEXT_KEY,
        context_manager_key: str = "context_manager",
        canonical_state_key: str = "canonical_dialog_state",
        service_carryover_key: str = "service_carryover",
        service_default_ttl: int | None = None,
    ) -> str | None:
        if not isinstance(context, dict):
            return None

        runtime_payload = context.get(runtime_key) if isinstance(context.get(runtime_key), dict) else None
        runtime_projection = self.normalize_runtime_conversation_projection(
            runtime_payload.get("conversation_projection")
            if isinstance(runtime_payload, dict)
            else None
        )
        if isinstance(runtime_projection, ConversationProjectionV1):
            projection_service = self._normalize_projection_token(
                runtime_projection.semantic_slots.get("service")
                if isinstance(runtime_projection.semantic_slots, dict)
                else None
            ) or self._normalize_projection_token(
                runtime_projection.booking_state.get("service")
                if isinstance(runtime_projection.booking_state, dict)
                else None
            )
            if projection_service:
                return projection_service
            projection_referents = self.project_current_referents_from_frame(
                self.project_semantic_frame(runtime_projection.semantic_frame)
            )
            service_value = self._normalize_projection_token(projection_referents.service)
            if service_value:
                return service_value

        runtime_dialog_state = runtime_payload.get("dialog_state") if isinstance(runtime_payload, dict) else None
        runtime_referents = (
            runtime_dialog_state.get("current_referents")
            if isinstance(runtime_dialog_state, dict)
            else None
        )
        runtime_service = self._normalize_projection_token(
            runtime_referents.get("service")
            if isinstance(runtime_referents, dict)
            else None
        )
        if runtime_service:
            return runtime_service

        context_manager = (
            context.get(context_manager_key)
            if isinstance(context.get(context_manager_key), dict)
            else None
        )
        canonical_state = self.normalize_context_manager_canonical_state(
            context_manager.get(canonical_state_key) if isinstance(context_manager, dict) else None
        )
        canonical_service = self._normalize_projection_token(
            self._grounded_referents_from_canonical_state(canonical_state).get("service")
        )
        if canonical_service:
            return canonical_service

        if not isinstance(context_manager, dict) or not isinstance(service_default_ttl, int) or service_default_ttl <= 0:
            return None
        try:
            message_count = int(context_manager.get("message_count"))
        except (TypeError, ValueError):
            return None
        if message_count <= 0:
            return None
        projected_carryover = self.get_service_carryover(
            context_manager.get(service_carryover_key),
            message_count=message_count,
            default_ttl=service_default_ttl,
        )
        return self._normalize_projection_token(
            projected_carryover.get("service_query")
            if isinstance(projected_carryover, dict)
            else None
        )

    def project_context_session_memory_interaction_state(
        self,
        context: dict[str, Any] | None,
        *,
        runtime_key: str = _RUNTIME_CONTEXT_KEY,
        context_manager_key: str = "context_manager",
        canonical_state_key: str = "canonical_dialog_state",
        session_memory_key: str = "session_memory",
    ) -> dict[str, Any] | None:
        if not isinstance(context, dict):
            return None

        runtime_payload = context.get(runtime_key) if isinstance(context.get(runtime_key), dict) else None
        runtime_projection = self.normalize_runtime_conversation_projection(
            runtime_payload.get("conversation_projection")
            if isinstance(runtime_payload, dict)
            else None
        )
        runtime_dialog_state = runtime_payload.get("dialog_state") if isinstance(runtime_payload, dict) else None
        if isinstance(runtime_projection, ConversationProjectionV1) or isinstance(runtime_dialog_state, dict):
            loaded = self.load_runtime_payload(context, runtime_key=runtime_key)
            dialog_state = loaded.get("dialog_state")
            if isinstance(dialog_state, DialogState):
                projection_state = dialog_state.projections.session_memory_interaction_state.model_dump(
                    mode="python",
                    exclude_none=True,
                )
                if projection_state:
                    return projection_state
                dialog_state_interaction = dialog_state.interaction_state.model_dump(
                    mode="python",
                    exclude_none=True,
                )
                if dialog_state_interaction:
                    return dialog_state_interaction

        context_manager = (
            context.get(context_manager_key)
            if isinstance(context.get(context_manager_key), dict)
            else None
        )
        canonical_state = self.normalize_context_manager_canonical_state(
            context_manager.get(canonical_state_key) if isinstance(context_manager, dict) else None
        )
        canonical_interaction, _ = self.project_session_memory_interaction_state(
            canonical_state.get("interaction_state") if isinstance(canonical_state, dict) else None
        )
        if canonical_interaction:
            return canonical_interaction

        session_memory = (
            context.get(session_memory_key)
            if isinstance(context.get(session_memory_key), dict)
            else None
        )
        session_memory_interaction, _ = self.project_session_memory_interaction_state(
            session_memory.get("interaction_state") if isinstance(session_memory, dict) else None
        )
        return session_memory_interaction

    def build_context_manager_compatibility_snapshot(
        self,
        context: dict[str, Any] | None,
        *,
        runtime_key: str = _RUNTIME_CONTEXT_KEY,
        context_manager_key: str = "context_manager",
        canonical_state_key: str = "canonical_dialog_state",
        session_memory_key: str = "session_memory",
        expected_reply_type_key: str = "expected_reply_type",
        expected_reply_reason_key: str = "expected_reply_reason",
    ) -> dict[str, Any]:
        if not isinstance(context, dict):
            return {}

        existing_manager = (
            context.get(context_manager_key)
            if isinstance(context.get(context_manager_key), dict)
            else None
        )
        snapshot = dict(existing_manager) if isinstance(existing_manager, dict) else {}
        message_count = self._canonical_int(snapshot.get("message_count"))
        projected_pending_question_contract = self.project_context_pending_question_contract(
            context,
            runtime_key=runtime_key,
            context_manager_key=context_manager_key,
            canonical_state_key=canonical_state_key,
            session_memory_key=session_memory_key,
            expected_reply_type_key=expected_reply_type_key,
            expected_reply_reason_key=expected_reply_reason_key,
        )
        snapshot = self.set_context_manager_pending_question_contract(
            snapshot,
            pending_question_contract=projected_pending_question_contract,
            canonical_state_key=canonical_state_key,
        )
        projected_current_goal = self.project_context_current_goal(
            context,
            runtime_key=runtime_key,
            context_manager_key=context_manager_key,
            canonical_state_key=canonical_state_key,
        )
        if projected_current_goal:
            snapshot["current_goal"] = projected_current_goal
        else:
            snapshot.pop("current_goal", None)

        canonical_state = self.normalize_context_manager_canonical_state(
            snapshot.get(canonical_state_key)
        )
        projected_interaction_state = self.project_context_session_memory_interaction_state(
            context,
            runtime_key=runtime_key,
            context_manager_key=context_manager_key,
            canonical_state_key=canonical_state_key,
            session_memory_key=session_memory_key,
        )
        canonical_state = self.set_canonical_interaction_state(
            canonical_state,
            resume_slot=(
                self._normalize_projection_token(projected_interaction_state.get("resume_slot"))
                if isinstance(projected_interaction_state, dict)
                else None
            ),
            interaction_target=(
                self._normalize_projection_token(projected_interaction_state.get("interaction_target"))
                if isinstance(projected_interaction_state, dict)
                else None
            ),
            interaction_relation=(
                self._normalize_projection_token(projected_interaction_state.get("interaction_relation"))
                if isinstance(projected_interaction_state, dict)
                else None
            ),
            interaction_owner=(
                self._normalize_projection_token(projected_interaction_state.get("interaction_owner"))
                if isinstance(projected_interaction_state, dict)
                else None
            ),
            grounded_referents=(
                dict(projected_interaction_state.get("grounded_referents"))
                if isinstance(projected_interaction_state, dict)
                and isinstance(projected_interaction_state.get("grounded_referents"), dict)
                else None
            ),
            confirmation_state=(
                dict(projected_interaction_state.get("confirmation_state"))
                if isinstance(projected_interaction_state, dict)
                and isinstance(projected_interaction_state.get("confirmation_state"), dict)
                else None
            ),
            degrade_reason=(
                self._normalize_projection_token(projected_interaction_state.get("degrade_reason"))
                if isinstance(projected_interaction_state, dict)
                else None
            ),
        )
        projected_service = self.project_context_service_referent(
            context,
            runtime_key=runtime_key,
            context_manager_key=context_manager_key,
            canonical_state_key=canonical_state_key,
            service_default_ttl=0,
        )
        if projected_service:
            canonical_state = self.set_canonical_referent(
                canonical_state,
                referent_key="service",
                value=projected_service,
                message_count=message_count,
                source="conversation_projection",
            )
        snapshot = self.set_context_manager_canonical_state(
            snapshot,
            key=canonical_state_key,
            state=canonical_state,
        )
        return snapshot

    def build_context_session_memory_snapshot(
        self,
        context: dict[str, Any] | None,
        *,
        base_memory: dict[str, Any] | None = None,
        ignore_session_memory_projection_source: bool = False,
        now: datetime | None = None,
        default_ttl_hours: int | None = None,
        runtime_key: str = _RUNTIME_CONTEXT_KEY,
        context_manager_key: str = "context_manager",
        canonical_state_key: str = "canonical_dialog_state",
        session_memory_key: str = "session_memory",
        expected_reply_type_key: str = "expected_reply_type",
        expected_reply_reason_key: str = "expected_reply_reason",
    ) -> dict[str, Any] | None:
        if not isinstance(context, dict):
            return None

        projection_context = context
        if ignore_session_memory_projection_source:
            projection_context = dict(context)
            projection_context.pop(session_memory_key, None)

        source_memory = (
            deepcopy(base_memory)
            if isinstance(base_memory, dict)
            else (
                deepcopy(context.get(session_memory_key))
                if isinstance(context.get(session_memory_key), dict)
                else None
            )
        )
        existing_memory, _ = self.normalize_session_memory_payload(
            source_memory,
        )
        memory = dict(existing_memory) if isinstance(existing_memory, dict) else {}
        projected_current_goal = self.project_context_current_goal(
            projection_context,
            runtime_key=runtime_key,
            context_manager_key=context_manager_key,
            canonical_state_key=canonical_state_key,
        )
        if projected_current_goal:
            memory = self.update_session_memory_goal(
                memory,
                active_goal=projected_current_goal,
            )

        projected_pending_question_contract = self.project_context_pending_question_contract(
            projection_context,
            runtime_key=runtime_key,
            context_manager_key=context_manager_key,
            canonical_state_key=canonical_state_key,
            session_memory_key=session_memory_key,
            expected_reply_type_key=expected_reply_type_key,
            expected_reply_reason_key=expected_reply_reason_key,
        )
        memory = self.sync_session_memory_pending_question_contract(
            memory,
            pending_question_contract=projected_pending_question_contract,
        )
        projected_interaction_state = self.project_context_session_memory_interaction_state(
            projection_context,
            runtime_key=runtime_key,
            context_manager_key=context_manager_key,
            canonical_state_key=canonical_state_key,
            session_memory_key=session_memory_key,
        )
        if isinstance(projected_interaction_state, dict):
            memory["interaction_state"] = dict(projected_interaction_state)
        else:
            memory.pop("interaction_state", None)

        normalized_memory, _ = self.normalize_session_memory_payload(memory)
        if not normalized_memory:
            return None
        if now is not None and isinstance(default_ttl_hours, int) and default_ttl_hours > 0:
            normalized_memory = self.touch_session_memory_payload(
                normalized_memory,
                now=now,
                default_ttl_hours=default_ttl_hours,
            )
        return normalized_memory

    def rebuild_context_session_memory(
        self,
        context: dict[str, Any] | None,
        *,
        base_memory: dict[str, Any] | None = None,
        now: datetime | None = None,
        default_ttl_hours: int | None = None,
        runtime_key: str = _RUNTIME_CONTEXT_KEY,
        context_manager_key: str = "context_manager",
        canonical_state_key: str = "canonical_dialog_state",
        session_memory_key: str = "session_memory",
        expected_reply_type_key: str = "expected_reply_type",
        expected_reply_reason_key: str = "expected_reply_reason",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        updated_context = deepcopy(context) if isinstance(context, dict) else {}
        session_memory = self.build_context_session_memory_snapshot(
            updated_context,
            base_memory=base_memory,
            ignore_session_memory_projection_source=True,
            now=now,
            default_ttl_hours=default_ttl_hours,
            runtime_key=runtime_key,
            context_manager_key=context_manager_key,
            canonical_state_key=canonical_state_key,
            session_memory_key=session_memory_key,
            expected_reply_type_key=expected_reply_type_key,
            expected_reply_reason_key=expected_reply_reason_key,
        )
        updated_context = self.set_context_session_memory(
            updated_context,
            session_memory,
            key=session_memory_key,
        )
        return (
            updated_context,
            dict(session_memory) if isinstance(session_memory, dict) else {},
        )

    def sync_runtime_compatibility_context(
        self,
        context: dict[str, Any] | None,
        *,
        now: datetime,
        runtime_key: str = _RUNTIME_CONTEXT_KEY,
        context_manager_key: str = "context_manager",
        canonical_state_key: str = "canonical_dialog_state",
        session_memory_key: str = "session_memory",
        expected_reply_type_key: str = "expected_reply_type",
        expected_reply_reason_key: str = "expected_reply_reason",
        current_goal_key: str = "current_goal",
        session_memory_ttl_hours: int = 24,
    ) -> dict[str, Any]:
        updated = deepcopy(context) if isinstance(context, dict) else {}
        updated.pop(expected_reply_type_key, None)
        updated.pop(expected_reply_reason_key, None)
        updated.pop(current_goal_key, None)

        manager = self.build_context_manager_compatibility_snapshot(
            updated,
            runtime_key=runtime_key,
            context_manager_key=context_manager_key,
            canonical_state_key=canonical_state_key,
            session_memory_key=session_memory_key,
            expected_reply_type_key=expected_reply_type_key,
            expected_reply_reason_key=expected_reply_reason_key,
        )
        updated = self.set_context_manager_payload(
            updated,
            manager,
            key=context_manager_key,
        )

        session_memory = self.build_context_session_memory_snapshot(
            updated,
            now=now,
            default_ttl_hours=session_memory_ttl_hours,
            runtime_key=runtime_key,
            context_manager_key=context_manager_key,
            canonical_state_key=canonical_state_key,
            session_memory_key=session_memory_key,
            expected_reply_type_key=expected_reply_type_key,
            expected_reply_reason_key=expected_reply_reason_key,
        )
        return self.set_context_session_memory(
            updated,
            session_memory,
            key=session_memory_key,
        )

    def project_pending_question_contract_with_projection_fallback(
        self,
        contract: PendingQuestionContract | dict[str, Any] | None,
        *,
        expected_reply_type: str | None = None,
        expected_reply_reason: str | None = None,
    ) -> dict[str, Any] | None:
        projected = self.project_pending_question_contract(contract)
        if projected is not None:
            return self.project_pending_question_contract(
                projected,
                expected_reply_type=(
                    None if projected.get("expected_reply_type") else expected_reply_type
                ),
                expected_reply_reason=(
                    None if projected.get("reason") else expected_reply_reason
                ),
            )
        return self.project_pending_question_contract(
            None,
            expected_reply_type=expected_reply_type,
            expected_reply_reason=expected_reply_reason,
        )

    def set_context_manager_pending_question_contract(
        self,
        manager: dict[str, Any] | None,
        *,
        pending_question_contract: dict[str, Any] | PendingQuestionContract | None,
        canonical_state_key: str = "canonical_dialog_state",
    ) -> dict[str, Any]:
        updated = dict(manager) if isinstance(manager, dict) else {}
        canonical_state = self.normalize_context_manager_canonical_state(
            updated.get(canonical_state_key)
        )
        projected = self.project_pending_question_contract(pending_question_contract)
        if projected:
            canonical_state["pending_question_contract"] = projected
        else:
            canonical_state.pop("pending_question_contract", None)
        return self.set_context_manager_canonical_state(
            updated,
            key=canonical_state_key,
            state=canonical_state,
        )

    def project_legacy_fields(self, state: DialogState) -> dict[str, Any]:
        pending_question_contract = self._pending_question_from_frame(
            state.semantic_state.materialized_frame
        ) or self.project_pending_question_contract_with_projection_fallback(
            state.pending_question_contract,
            expected_reply_type=state.projections.expected_reply_type,
            expected_reply_reason=state.projections.expected_reply_reason,
        ) or {}
        projections = self.project_expected_reply_projections(
            state.projections,
            expected_reply_type=pending_question_contract.get("expected_reply_type"),
            expected_reply_reason=pending_question_contract.get("reason"),
        )
        return {
            "expected_reply_type": projections.expected_reply_type,
            "expected_reply_reason": projections.expected_reply_reason,
            "session_memory": {
                "interaction_state": state.projections.session_memory_interaction_state.model_dump(
                    mode="json",
                    exclude_none=True,
                )
            },
        }

    def _current_referents_from_grounded_referents(
        self,
        grounded_referents: dict[str, str] | None,
    ) -> CurrentReferents:
        grounded = grounded_referents if isinstance(grounded_referents, dict) else {}
        return CurrentReferents(
            service=self._normalize_projection_token(grounded.get("service")),
            specialist=self._normalize_projection_token(grounded.get("specialist")),
            branch=self._normalize_projection_token(grounded.get("branch")),
            booking=self._normalize_projection_token(grounded.get("booking_ref")),
            customer=self._normalize_projection_token(grounded.get("customer")),
        )

    def _build_runtime_grounded_referents(
        self,
        *,
        existing_state: DialogState,
        booking_payload: dict[str, Any] | None,
        decision: PolicyDecision,
        execution_payload: dict[str, Any] | None,
    ) -> dict[str, str]:
        grounded: dict[str, str] = {}

        def _remember(key: str, value: Any) -> None:
            normalized = self._normalize_projection_token(value)
            if normalized:
                grounded[key] = normalized

        for key, value in self.project_grounded_referents_from_frame(
            existing_state.semantic_state.materialized_frame
        ).items():
            _remember(key, value)
        _remember("service", existing_state.current_referents.service)
        _remember("specialist", existing_state.current_referents.specialist)
        _remember("branch", existing_state.current_referents.branch)
        _remember("booking_ref", existing_state.current_referents.booking)
        _remember("customer", existing_state.current_referents.customer)

        decision_semantic_contract = self._decision_semantic_contract(decision)
        execution_semantic_contract = self._execution_semantic_payload(
            execution_payload if isinstance(execution_payload, dict) else {},
            owner_only=self._has_canonical_semantic_owner(decision),
        )
        decision_referents = (
            decision_semantic_contract.get("referents")
            if isinstance(decision_semantic_contract.get("referents"), dict)
            else {}
        )
        execution_referents = (
            execution_semantic_contract.get("referents")
            if isinstance(execution_semantic_contract.get("referents"), dict)
            else {}
        )
        for referent_key, source_key in (
            ("service", "service"),
            ("specialist", "specialist"),
            ("branch", "branch"),
            ("booking_ref", "booking_ref"),
            ("customer", "customer"),
        ):
            payload = decision_referents.get(referent_key)
            if not isinstance(payload, dict):
                continue
            _remember(source_key, payload.get("value") or payload.get("entity_id"))
        for referent_key, source_key in (
            ("service", "service"),
            ("specialist", "specialist"),
            ("branch", "branch"),
            ("booking_ref", "booking_ref"),
            ("customer", "customer"),
        ):
            payload = execution_referents.get(referent_key)
            if not isinstance(payload, dict):
                continue
            _remember(source_key, payload.get("value") or payload.get("entity_id"))

        for key, value in (existing_state.interaction_state.grounded_referents or {}).items():
            if key in {"service", "specialist", "branch", "booking_ref", "customer"}:
                _remember(key, value)

        if isinstance(booking_payload, dict):
            _remember("service", booking_payload.get("service"))
            _remember("specialist", booking_payload.get("specialist_name") or booking_payload.get("specialist_id"))
            _remember(
                "booking_ref",
                booking_payload.get("appointment_id")
                or booking_payload.get("reference_id")
                or booking_payload.get("booking_id"),
            )
            _remember("customer", booking_payload.get("name"))

        _remember("service", decision.slots.get("service"))
        _remember("customer", decision.slots.get("name"))

        entity_type_map = {
            "service": "service",
            "specialist": "specialist",
            "branch": "branch",
            "booking": "booking_ref",
            "booking_ref": "booking_ref",
            "customer": "customer",
        }
        raw_entity_refs = (
            decision_semantic_contract.get("entity_refs")
            if isinstance(decision_semantic_contract, dict)
            else None
        )
        if isinstance(raw_entity_refs, list):
            for row in raw_entity_refs:
                if not isinstance(row, dict):
                    continue
                target_key = entity_type_map.get(
                    self._normalize_projection_token(row.get("entity_type")) or ""
                )
                if not target_key:
                    continue
                _remember(target_key, row.get("value") or row.get("entity_id"))

        if isinstance(execution_payload, dict):
            _remember("specialist", execution_payload.get("specialist_name") or execution_payload.get("specialist_id"))
            _remember(
                "booking_ref",
                execution_payload.get("appointment_id")
                or execution_payload.get("reference_id")
                or execution_payload.get("booking_id"),
            )
            _remember("customer", execution_payload.get("customer_name"))

        return grounded

    def _build_runtime_semantic_contract(
        self,
        *,
        existing_state: DialogState,
        booking_payload: dict[str, Any] | None,
        decision: PolicyDecision,
        execution_payload: dict[str, Any] | None,
        grounded_referents: dict[str, str] | None,
    ) -> dict[str, Any] | None:
        if self._is_synthetic_control_decision(decision):
            return None
        existing_contract = self._semantic_contract_from_frame(
            existing_state.semantic_state.materialized_frame
        ) or (
            dict(existing_state.meta.get("semantic_contract"))
            if isinstance(existing_state.meta.get("semantic_contract"), dict)
            else {}
        )
        decision_contract = self._decision_semantic_contract(decision)
        execution_contract = self._execution_semantic_payload(
            execution_payload if isinstance(execution_payload, dict) else {},
            owner_only=self._has_canonical_semantic_owner(decision),
        )
        if self._has_canonical_semantic_owner(decision) and decision_contract:
            contract = dict(decision_contract)
            contract["contract_version"] = "semantic_contract.v1"
            entity_refs = self._normalize_semantic_entity_refs(contract.get("entity_refs"))
            entity_refs.extend(
                self._normalize_semantic_entity_refs(execution_contract.get("entity_refs"))
            )
            entity_refs = self._normalize_semantic_entity_refs(entity_refs)
            if entity_refs:
                contract["entity_refs"] = entity_refs
            else:
                contract.pop("entity_refs", None)
            grounding_provenance = self._normalize_grounding_provenance(
                execution_contract.get("grounding_provenance")
            ) or self._normalize_grounding_provenance(
                decision_contract.get("grounding_provenance")
            )
            if grounding_provenance:
                contract["grounding_provenance"] = grounding_provenance
            referents = self._build_semantic_referents(
                existing_contract={},
                entity_refs=entity_refs,
                grounded_referents=None,
                booking_payload=None,
                decision=decision,
                execution_payload=None,
                execution_contract=execution_contract,
            )
            if referents:
                contract["referents"] = referents
            return contract if len(contract) > 1 else None
        contract: dict[str, Any] = {"contract_version": "semantic_contract.v1"}
        for source in (existing_contract, decision_contract, execution_contract):
            for key in (
                "subject_kind",
                "capability",
                "temporal_scope",
                "resolution_mode",
            ):
                value = self._normalize_projection_token(source.get(key))
                if value:
                    contract[key] = value
        for source in (decision_contract, execution_contract):
            for key in (
                "pending_question_act",
                "pending_question_target",
                "active_question_relation",
            ):
                value = self._normalize_projection_token(source.get(key))
                if value:
                    contract[key] = value

        entity_refs = self._normalize_semantic_entity_refs(existing_contract.get("entity_refs"))
        entity_refs.extend(self._normalize_semantic_entity_refs(decision_contract.get("entity_refs")))
        entity_refs.extend(self._normalize_semantic_entity_refs(execution_contract.get("entity_refs")))
        entity_refs = self._normalize_semantic_entity_refs(entity_refs)
        if entity_refs:
            contract["entity_refs"] = entity_refs

        grounding_provenance = None
        for source in (existing_contract, decision_contract, execution_contract):
            normalized = self._normalize_grounding_provenance(source.get("grounding_provenance"))
            if normalized:
                grounding_provenance = normalized
        if grounding_provenance:
            contract["grounding_provenance"] = grounding_provenance

        referents = self._build_semantic_referents(
            existing_contract=existing_contract,
            entity_refs=entity_refs,
            grounded_referents=grounded_referents,
            booking_payload=booking_payload,
            decision=decision,
            execution_payload=execution_payload,
            execution_contract=execution_contract,
        )
        if referents:
            contract["referents"] = referents
        return contract if len(contract) > 1 else None

    def _build_semantic_referents(
        self,
        *,
        existing_contract: dict[str, Any],
        entity_refs: list[dict[str, Any]],
        grounded_referents: dict[str, str] | None,
        booking_payload: dict[str, Any] | None,
        decision: PolicyDecision,
        execution_payload: dict[str, Any] | None,
        execution_contract: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        referents: dict[str, dict[str, Any]] = {}

        def _remember(
            referent_key: str,
            *,
            value: Any = None,
            entity_id: Any = None,
            entity_type: Any = None,
            source_ref: Any = None,
        ) -> None:
            if referent_key not in {"service", "specialist", "branch", "booking_ref", "customer"}:
                return
            payload = dict(referents.get(referent_key) or {})
            previous_value = payload.get("value")
            previous_entity_id = payload.get("entity_id")
            normalized_value = self._normalize_projection_token(value)
            if normalized_value:
                payload["value"] = normalized_value
            normalized_entity_id = self._normalize_projection_token(entity_id)
            if normalized_entity_id:
                payload["entity_id"] = normalized_entity_id
            has_identity = bool(
                self._normalize_projection_token(payload.get("value"))
                or self._normalize_projection_token(payload.get("entity_id"))
            )
            normalized_entity_type = self._normalize_projection_token(entity_type)
            if normalized_entity_type and has_identity:
                payload["entity_type"] = normalized_entity_type
            normalized_source_ref = self._normalize_projection_token(source_ref)
            source_changed = (
                ("source_ref" not in payload)
                or (normalized_value is not None and normalized_value != previous_value)
                or (normalized_entity_id is not None and normalized_entity_id != previous_entity_id)
            )
            if normalized_source_ref and (normalized_value or normalized_entity_id) and source_changed:
                payload["source_ref"] = normalized_source_ref
            if has_identity:
                referents[referent_key] = payload

        existing_referents = existing_contract.get("referents")
        if isinstance(existing_referents, dict):
            for referent_key, payload in existing_referents.items():
                if isinstance(payload, dict):
                    _remember(
                        referent_key,
                        value=payload.get("value"),
                        entity_id=payload.get("entity_id"),
                        entity_type=payload.get("entity_type"),
                        source_ref=payload.get("source_ref"),
                    )

        if isinstance(grounded_referents, dict):
            for referent_key, value in grounded_referents.items():
                _remember(referent_key, value=value, source_ref="runtime_grounding")

        decision_contract = self._decision_semantic_contract(decision)
        decision_referents = decision_contract.get("referents")
        if isinstance(decision_referents, dict):
            for referent_key, payload in decision_referents.items():
                if not isinstance(payload, dict):
                    continue
                _remember(
                    referent_key,
                    value=payload.get("value") or payload.get("entity_id"),
                    entity_id=payload.get("entity_id"),
                    entity_type=payload.get("entity_type"),
                    source_ref=payload.get("source_ref"),
                )

        execution_referents = execution_contract.get("referents")
        if isinstance(execution_referents, dict):
            for referent_key, payload in execution_referents.items():
                if not isinstance(payload, dict):
                    continue
                _remember(
                    referent_key,
                    value=payload.get("value") or payload.get("entity_id"),
                    entity_id=payload.get("entity_id"),
                    entity_type=payload.get("entity_type"),
                    source_ref=payload.get("source_ref"),
                )

        if isinstance(booking_payload, dict):
            _remember("service", value=booking_payload.get("service"), source_ref="booking_state")
            _remember(
                "specialist",
                value=booking_payload.get("specialist_name") or booking_payload.get("specialist_id"),
                source_ref="booking_state",
            )
            _remember("customer", value=booking_payload.get("name"), source_ref="booking_state")
            _remember(
                "booking_ref",
                value=booking_payload.get("appointment_id")
                or booking_payload.get("reference_id")
                or booking_payload.get("booking_id"),
                source_ref="booking_state",
            )

        for row in entity_refs:
            if not isinstance(row, dict):
                continue
            entity_type = self._normalize_projection_token(row.get("entity_type"))
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
                entity_id=row.get("entity_id"),
                entity_type=entity_type,
                source_ref=row.get("source_ref"),
            )

        slots = decision.slots if isinstance(decision.slots, dict) else {}
        _remember("service", value=slots.get("service"), source_ref="decision_slots")
        _remember("customer", value=slots.get("name"), source_ref="decision_slots")

        if isinstance(execution_payload, dict):
            _remember(
                "specialist",
                value=execution_payload.get("specialist_name") or execution_payload.get("specialist_id"),
                source_ref="execution",
            )
            _remember("customer", value=execution_payload.get("customer_name"), source_ref="execution")
            _remember(
                "booking_ref",
                value=execution_payload.get("appointment_id")
                or execution_payload.get("reference_id")
                or execution_payload.get("booking_id"),
                source_ref="execution",
            )

        return referents

    def _normalize_semantic_entity_refs(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        cleaned: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str, str]] = set()
        for item in value:
            if not isinstance(item, dict):
                continue
            payload: dict[str, Any] = {}
            entity_id = self._normalize_projection_token(item.get("entity_id") or item.get("id"))
            entity_type = self._normalize_projection_token(item.get("entity_type") or item.get("type"))
            source_ref = self._normalize_projection_token(item.get("source_ref"))
            entity_value = self._normalize_projection_token(item.get("value") or item.get("label"))
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

    def _normalize_grounding_provenance(self, value: Any) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            return None
        payload: dict[str, Any] = {}
        for key in ("pack_id", "entity_id", "source_ref", "resolver_id", "resolver_version"):
            token = self._normalize_projection_token(value.get(key))
            if token:
                payload[key] = token
        confidence = value.get("confidence")
        if isinstance(confidence, (int, float)):
            payload["confidence"] = max(0.0, min(float(confidence), 1.0))
        retrieval = value.get("retrieval")
        if isinstance(retrieval, dict) and retrieval:
            payload["retrieval"] = dict(retrieval)
        return payload or None

    def _build_booking_followup_dialog_state(
        self,
        *,
        base_state: DialogState,
        decision: PolicyDecision,
        expected_reply_type: str,
        expected_reply_reason: str | None,
        grounded_referents: dict[str, str] | None,
    ) -> DialogState:
        expected_reply_token = self._normalize_projection_token(expected_reply_type)
        if not expected_reply_token:
            raise ValueError("expected_reply_type_invalid")

        reason_token = self._normalize_projection_token(expected_reply_reason)
        base_pending = base_state.pending_question_contract
        next_question = self._normalize_projection_token(base_pending.next_question) or (
            _CANONICAL_EXPECTED_REPLY_SLOT_BY_TYPE.get(expected_reply_token)
        )
        open_questions = [
            token
            for token in (
                self._normalize_projection_token(item)
                for item in base_pending.open_questions
            )
            if token
        ]
        if not open_questions and next_question:
            open_questions = [next_question]

        interaction_target = (
            self._normalize_projection_token(base_state.interaction_state.interaction_target)
            or self._normalize_projection_token(base_pending.pending_question_target)
        )
        interaction_relation = (
            self._normalize_projection_token(base_state.interaction_state.interaction_relation)
            or self._normalize_projection_token(base_pending.active_question_relation)
        )
        pending_question_act = self._normalize_projection_token(base_pending.pending_question_act)
        interaction_owner = (
            self._normalize_projection_token(base_state.interaction_state.interaction_owner)
            or self.build_interaction_owner(
                explicit_owner=decision.interaction.owner,
                interaction_relation=interaction_relation,
                question_reason=reason_token,
            )
        )
        interaction_state = InteractionState(
            resume_slot=(
                self._normalize_projection_token(base_state.interaction_state.resume_slot)
                or _CANONICAL_EXPECTED_REPLY_SLOT_BY_TYPE.get(expected_reply_token)
                or next_question
            ),
            interaction_target=interaction_target,
            interaction_relation=interaction_relation,
            interaction_owner=interaction_owner,
            grounded_referents=dict(grounded_referents or {}),
        )
        pending_question_payload = self.project_pending_question_contract(
            base_pending,
            expected_reply_type=expected_reply_token,
            expected_reply_reason=reason_token,
            pending_question_act=pending_question_act,
            pending_question_target=interaction_target,
            active_question_relation=interaction_relation,
            next_question=next_question,
            open_questions=open_questions,
        )
        return DialogState(
            current_referents=self._current_referents_from_grounded_referents(grounded_referents),
            pending_question_contract=PendingQuestionContract.model_validate(
                pending_question_payload or {}
            ),
            interaction_state=interaction_state,
            projections=DialogStateProjections(
                expected_reply_type=expected_reply_token,
                expected_reply_reason=reason_token,
                session_memory_interaction_state=interaction_state,
            ),
            meta={
                "writer": "dialog_state_service",
                "owner_replacement_cutover": True,
            },
        )

    def project_expected_reply_projections(
        self,
        projections: DialogStateProjections | None = None,
        *,
        expected_reply_type: str | None = None,
        expected_reply_reason: str | None = None,
    ) -> DialogStateProjections:
        base = projections or DialogStateProjections()
        normalized_type = self._normalize_projection_token(
            expected_reply_type if expected_reply_type is not None else base.expected_reply_type
        )
        normalized_reason = self._normalize_projection_token(
            expected_reply_reason if expected_reply_reason is not None else base.expected_reply_reason
        )
        return base.model_copy(
            update={
                "expected_reply_type": normalized_type,
                "expected_reply_reason": normalized_reason,
            }
        )

    def set_expected_reply_context_fields(
        self,
        context: dict[str, Any] | None,
        *,
        expected_reply_type: str | None,
        expected_reply_reason: str | None = None,
    ) -> dict[str, Any]:
        updated = deepcopy(context) if isinstance(context, dict) else {}
        projections = self.project_expected_reply_projections(
            expected_reply_type=expected_reply_type,
            expected_reply_reason=expected_reply_reason,
        )
        if projections.expected_reply_type:
            updated["expected_reply_type"] = projections.expected_reply_type
        else:
            updated.pop("expected_reply_type", None)
        if projections.expected_reply_reason:
            updated["expected_reply_reason"] = projections.expected_reply_reason
        else:
            updated.pop("expected_reply_reason", None)
        return updated

    def sync_session_memory_pending_question_contract(
        self,
        memory: dict[str, Any] | None,
        *,
        pending_question_contract: dict[str, Any] | PendingQuestionContract | None,
    ) -> dict[str, Any]:
        updated = deepcopy(memory) if isinstance(memory, dict) else {}
        projected = self.project_pending_question_contract(pending_question_contract)
        if projected:
            updated["pending_question_contract"] = projected
            updated.pop("last_question_type", None)
        else:
            updated.pop("pending_question_contract", None)
        return updated

    def update_session_memory_on_question(
        self,
        memory: dict[str, Any] | None,
        *,
        expected_reply_type: str,
        active_goal: str | None,
    ) -> dict[str, Any]:
        updated = deepcopy(memory) if isinstance(memory, dict) else {}
        expected_reply_token = self._normalize_projection_token(expected_reply_type)
        if not expected_reply_token:
            return updated

        unanswered = updated.get("unanswered_questions")
        unanswered_list = (
            [item.strip() for item in unanswered if isinstance(item, str) and item.strip()]
            if isinstance(unanswered, list)
            else []
        )
        if expected_reply_token not in unanswered_list:
            unanswered_list.append(expected_reply_token)
        updated["unanswered_questions"] = unanswered_list
        updated["last_question_type"] = expected_reply_token

        normalized_goal = self._normalize_projection_token(active_goal)
        if normalized_goal:
            updated["active_goal"] = normalized_goal
            goal_stack = updated.get("goal_stack")
            cleaned_goal_stack = (
                [item.strip() for item in goal_stack if isinstance(item, str) and item.strip()]
                if isinstance(goal_stack, list)
                else []
            )
            if not cleaned_goal_stack or cleaned_goal_stack[-1] != normalized_goal:
                cleaned_goal_stack.append(normalized_goal)
            updated["goal_stack"] = cleaned_goal_stack[-3:]
        return updated

    def update_session_memory_on_answer(
        self,
        memory: dict[str, Any] | None,
        *,
        expected_reply_type: str,
        value: str,
    ) -> dict[str, Any]:
        updated = deepcopy(memory) if isinstance(memory, dict) else {}
        expected_reply_token = self._normalize_projection_token(expected_reply_type)
        value_token = self._normalize_projection_token(value)

        pending_slots = updated.get("pending_slots")
        pending_map = dict(pending_slots) if isinstance(pending_slots, dict) else {}
        unanswered = updated.get("unanswered_questions")
        unanswered_list = (
            [item.strip() for item in unanswered if isinstance(item, str) and item.strip()]
            if isinstance(unanswered, list)
            else []
        )
        if expected_reply_token and expected_reply_token in unanswered_list:
            unanswered_list = [item for item in unanswered_list if item != expected_reply_token]

        slot_key = _SESSION_MEMORY_PENDING_SLOT_BY_REPLY_TYPE.get(expected_reply_token or "")
        if slot_key and value_token:
            pending_map[slot_key] = value_token

        updated["pending_slots"] = pending_map
        updated["unanswered_questions"] = unanswered_list
        return updated

    def clear_session_memory_expected_reply(
        self,
        memory: dict[str, Any] | None,
        *,
        expected_reply_type: str | None,
    ) -> tuple[dict[str, Any], bool]:
        updated = deepcopy(memory) if isinstance(memory, dict) else {}
        if not updated:
            return updated, False

        expected_clean = self._normalize_projection_token(expected_reply_type)
        target_types: set[str] = set()
        if expected_clean in _SESSION_MEMORY_QUESTION_TYPES:
            target_types.add(expected_clean)

        last_question_type = updated.get("last_question_type")
        if (
            isinstance(last_question_type, str)
            and last_question_type.strip() in _SESSION_MEMORY_QUESTION_TYPES
        ):
            target_types.add(last_question_type.strip())

        if not target_types:
            return updated, False

        changed = False
        if (
            isinstance(updated.get("last_question_type"), str)
            and updated.get("last_question_type").strip() in target_types
        ):
            updated.pop("last_question_type", None)
            changed = True

        unanswered = updated.get("unanswered_questions")
        if isinstance(unanswered, list):
            filtered_unanswered = [
                item
                for item in unanswered
                if isinstance(item, str) and item.strip() and item.strip() not in target_types
            ]
            if filtered_unanswered != unanswered:
                updated["unanswered_questions"] = filtered_unanswered
                changed = True

        pending_slots = updated.get("pending_slots")
        if isinstance(pending_slots, dict):
            pending_map = dict(pending_slots)
            for target_type in target_types:
                slot_key = _SESSION_MEMORY_PENDING_SLOT_BY_REPLY_TYPE.get(target_type)
                if slot_key and slot_key in pending_map:
                    pending_map.pop(slot_key, None)
                    changed = True
            updated["pending_slots"] = pending_map

        return updated, changed

    def clear_context_session_memory_expected_reply(
        self,
        context: dict[str, Any] | None,
        *,
        expected_reply_type: str | None,
        now: datetime,
        default_ttl_hours: int,
        runtime_key: str = _RUNTIME_CONTEXT_KEY,
        context_manager_key: str = "context_manager",
        canonical_state_key: str = "canonical_dialog_state",
        session_memory_key: str = "session_memory",
        expected_reply_type_key: str = "expected_reply_type",
        expected_reply_reason_key: str = "expected_reply_reason",
    ) -> tuple[dict[str, Any], dict[str, Any], bool]:
        existing_memory = (
            context.get(session_memory_key)
            if isinstance(context, dict) and isinstance(context.get(session_memory_key), dict)
            else {}
        )
        cleared_memory, changed = self.clear_session_memory_expected_reply(
            existing_memory,
            expected_reply_type=expected_reply_type,
        )
        updated_context, rebuilt_memory = self.rebuild_context_session_memory(
            context,
            base_memory=cleared_memory,
            now=now,
            default_ttl_hours=default_ttl_hours,
            runtime_key=runtime_key,
            context_manager_key=context_manager_key,
            canonical_state_key=canonical_state_key,
            session_memory_key=session_memory_key,
            expected_reply_type_key=expected_reply_type_key,
            expected_reply_reason_key=expected_reply_reason_key,
        )
        normalized_existing, _ = self.normalize_session_memory_payload(existing_memory)
        return updated_context, rebuilt_memory, changed or rebuilt_memory != normalized_existing

    def update_session_memory_goal(
        self,
        memory: dict[str, Any] | None,
        *,
        active_goal: str,
    ) -> dict[str, Any]:
        updated = deepcopy(memory) if isinstance(memory, dict) else {}
        normalized_goal = self._normalize_projection_token(active_goal)
        if not normalized_goal:
            return updated
        updated["active_goal"] = normalized_goal
        goal_stack = updated.get("goal_stack")
        cleaned_goal_stack = (
            [item.strip() for item in goal_stack if isinstance(item, str) and item.strip()]
            if isinstance(goal_stack, list)
            else []
        )
        if not cleaned_goal_stack or cleaned_goal_stack[-1] != normalized_goal:
            cleaned_goal_stack.append(normalized_goal)
        updated["goal_stack"] = cleaned_goal_stack[-3:]
        return updated

    def touch_session_memory_payload(
        self,
        memory: dict[str, Any] | None,
        *,
        now: datetime,
        default_ttl_hours: int,
    ) -> dict[str, Any]:
        updated = deepcopy(memory) if isinstance(memory, dict) else {}
        try:
            ttl_hours = int(default_ttl_hours)
        except (TypeError, ValueError):
            ttl_hours = 24
        updated["last_updated_at"] = now.isoformat()
        updated["ttl_hours"] = max(ttl_hours, 1)
        return updated

    def sync_session_memory_interaction_state(
        self,
        memory: dict[str, Any] | None,
        *,
        interaction_state: dict[str, Any] | None,
        now: datetime,
        default_ttl_hours: int,
    ) -> tuple[dict[str, Any], bool]:
        updated = deepcopy(memory) if isinstance(memory, dict) else {}
        cleaned_state, _ = self.project_session_memory_interaction_state(interaction_state)

        changed = False
        if isinstance(cleaned_state, dict):
            if updated.get("interaction_state") != cleaned_state:
                updated["interaction_state"] = cleaned_state
                changed = True
        elif "interaction_state" in updated:
            updated.pop("interaction_state", None)
            changed = True

        if changed:
            updated = self.touch_session_memory_payload(
                updated,
                now=now,
                default_ttl_hours=default_ttl_hours,
            )
        return updated, changed

    def set_context_session_memory(
        self,
        context: dict[str, Any] | None,
        payload: dict[str, Any] | None,
        *,
        key: str,
    ) -> dict[str, Any]:
        session_memory = dict(payload) if isinstance(payload, dict) and payload else None
        return self._set_optional_context_payload(
            context,
            key=key,
            payload=session_memory,
        )

    def normalize_booking_payload(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        cleaned: dict[str, Any] = {}
        active = payload.get("active")
        if isinstance(active, bool):
            cleaned["active"] = active
        for key in _BOOKING_CONTEXT_STRING_KEYS:
            normalized = self._normalize_projection_token(payload.get(key))
            if normalized:
                cleaned[key] = normalized
        last_question = self._normalize_projection_token(payload.get("last_question"))
        if last_question in _BOOKING_CONTEXT_SLOT_KEYS:
            cleaned["last_question"] = last_question
        if "active" not in cleaned and any(
            key in cleaned
            for key in _BOOKING_CONTEXT_SLOT_KEYS | {"specialist_name", "specialist_id"}
        ):
            cleaned["active"] = True
        return cleaned or None

    def build_collect_owner_booking_payload(
        self,
        *,
        existing_booking: dict[str, Any] | None,
        now: datetime,
        last_question: str,
        slot_values: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        updated = self.normalize_booking_payload(existing_booking) or {}
        if updated.get("active") is not True:
            updated["active"] = True
        if not updated.get("started_at"):
            updated["started_at"] = now.isoformat()
        for slot_key, raw_value in (slot_values or {}).items():
            if slot_key not in _BOOKING_CONTEXT_SLOT_KEYS:
                continue
            normalized = self._normalize_projection_token(raw_value)
            if not normalized:
                continue
            if not updated.get(slot_key):
                updated[slot_key] = normalized
        normalized_last_question = self._normalize_projection_token(last_question)
        if normalized_last_question in _BOOKING_CONTEXT_SLOT_KEYS:
            updated["last_question"] = normalized_last_question
        return self.normalize_booking_payload(updated)

    def set_context_booking_payload(
        self,
        context: dict[str, Any] | None,
        payload: dict[str, Any] | None,
        *,
        key: str,
    ) -> dict[str, Any]:
        return self._set_optional_context_payload(
            context,
            key=key,
            payload=self.normalize_booking_payload(payload),
        )

    def load_runtime_payload(
        self,
        context: dict[str, Any] | None,
        *,
        runtime_key: str = _RUNTIME_CONTEXT_KEY,
    ) -> dict[str, Any]:
        working_context = dict(context) if isinstance(context, dict) else {}
        runtime_payload = (
            working_context.get(runtime_key)
            if isinstance(working_context.get(runtime_key), dict)
            else {}
        )
        runtime_turn_journal = self.normalize_runtime_turn_journal(
            runtime_payload.get("turn_journal")
            if isinstance(runtime_payload, dict)
            else None
        )
        runtime_projection = self.normalize_runtime_conversation_projection(
            runtime_payload.get("conversation_projection")
            if isinstance(runtime_payload, dict)
            else None
        )
        dialog_state_payload = runtime_payload.get("dialog_state")
        has_dialog_state_payload = isinstance(dialog_state_payload, dict)
        booking_payload = self.normalize_booking_payload(runtime_payload.get("booking"))
        if booking_payload is None:
            booking_payload = self.normalize_booking_payload(working_context.get("booking"))
        if not booking_payload and isinstance(runtime_projection, ConversationProjectionV1):
            booking_payload = self.normalize_booking_payload(runtime_projection.booking_state)
        pending_contract = {}
        expected_reply_type = None
        expected_reply_reason = None
        legacy_or_shadow_goal = self.project_context_current_goal(working_context)
        current_goal = legacy_or_shadow_goal if not has_dialog_state_payload else None

        if not isinstance(dialog_state_payload, dict):
            pending_contract = self.project_context_pending_question_contract(
                working_context,
                runtime_key=runtime_key,
            ) or {}
            expected_projections = self.project_expected_reply_projections(
                expected_reply_type=pending_contract.get("expected_reply_type"),
                expected_reply_reason=pending_contract.get("reason"),
            )
            expected_reply_type = expected_projections.expected_reply_type
            expected_reply_reason = expected_projections.expected_reply_reason
            fallback_next_question = (
                pending_contract.get("next_question")
                or _CANONICAL_EXPECTED_REPLY_SLOT_BY_TYPE.get(expected_reply_type or "")
            )
            dialog_state_payload = {
                "current_referents": {
                    "service": booking_payload.get("service") if isinstance(booking_payload, dict) else None,
                },
                "pending_question_contract": (
                    pending_contract
                    or {
                        "expected_reply_type": expected_reply_type,
                        "reason": expected_reply_reason,
                        "next_question": fallback_next_question,
                        "open_questions": [fallback_next_question] if fallback_next_question else [],
                    }
                ),
                "interaction_state": {
                    "interaction_owner": "consultant_runtime",
                },
            }
        dialog_state = self.normalize(dialog_state_payload)
        if isinstance(runtime_projection, ConversationProjectionV1):
            dialog_state = self._derive_dialog_state_from_projection(
                base_state=dialog_state,
                projection=runtime_projection,
            )
            booking_payload = (
                self.normalize_booking_payload(runtime_projection.booking_state)
                or booking_payload
                or {}
            )
            expected_reply_type = dialog_state.projections.expected_reply_type
            expected_reply_reason = dialog_state.projections.expected_reply_reason
            current_goal = (
                self._normalize_projection_token(runtime_projection.current_goal)
                or self.project_current_goal_from_frame(
                    self.project_semantic_frame(runtime_projection.semantic_frame)
                )
                or current_goal
            )
        semantic_state = dialog_state.semantic_state
        if not self.project_semantic_frame(semantic_state.materialized_frame):
            semantic_state = CanonicalSemanticState(
                materialized_frame=self._legacy_semantic_frame(
                    current_goal=current_goal,
                    semantic_contract=(
                        dict(dialog_state.meta.get("semantic_contract"))
                        if isinstance(dialog_state.meta.get("semantic_contract"), dict)
                        else None
                    ),
                    pending_question_contract=(
                        pending_contract
                        if isinstance(pending_contract, dict) and pending_contract
                        else self.project_pending_question_contract(dialog_state.pending_question_contract)
                    ),
                    booking_payload=booking_payload,
                    current_referents_payload=dialog_state.current_referents,
                ),
                event_log=list(semantic_state.event_log),
            )
        dialog_state = self.project_state_compatibility_fields(
            dialog_state.model_copy(
                update={
                    "semantic_state": semantic_state,
                }
            ),
            expected_reply_type=expected_reply_type,
            expected_reply_reason=expected_reply_reason,
        )
        expected_reply_type = dialog_state.projections.expected_reply_type
        expected_reply_reason = dialog_state.projections.expected_reply_reason
        semantic_goal = self._normalize_projection_token(
            dialog_state.semantic_state.materialized_frame.user_goal
        )
        dialog_goal = semantic_goal or self._normalize_projection_token(
            dialog_state.meta.get("current_goal")
            if isinstance(dialog_state.meta, dict)
            else None
        )
        if dialog_goal:
            current_goal = dialog_goal
        elif current_goal is None:
            current_goal = legacy_or_shadow_goal

        if not booking_payload and working_context.get("pending_resume"):
            restored = self.restore_pending_resume_payload(
                working_context.get("pending_resume"),
                now=datetime.now(timezone.utc),
            )
            restored_booking = self.normalize_booking_payload(restored.get("booking"))
            if restored_booking:
                booking_payload = restored_booking
            restored_expected = self.project_expected_reply_projections(
                expected_reply_type=restored.get("expected_reply_type"),
                expected_reply_reason=restored.get("expected_reply_reason"),
            )
            expected_reply_type = expected_reply_type or restored_expected.expected_reply_type
            expected_reply_reason = expected_reply_reason or restored_expected.expected_reply_reason
            if booking_payload and current_goal is None:
                current_goal = "booking"

        if not isinstance(runtime_projection, ConversationProjectionV1):
            runtime_projection = self._build_conversation_projection(
                conversation_id=None,
                existing_projection=None,
                decision=None,
                semantic_state=dialog_state.semantic_state,
                semantic_contract=(
                    dict(dialog_state.meta.get("semantic_contract"))
                    if isinstance(dialog_state.meta, dict)
                    and isinstance(dialog_state.meta.get("semantic_contract"), dict)
                    else self._semantic_contract_from_frame(dialog_state.semantic_state.materialized_frame)
                ),
                pending_question_contract=self.project_pending_question_contract_with_projection_fallback(
                    dialog_state.pending_question_contract,
                    expected_reply_type=dialog_state.projections.expected_reply_type,
                    expected_reply_reason=dialog_state.projections.expected_reply_reason,
                ),
                current_goal=current_goal,
                booking_payload=booking_payload,
            )

        return {
            "dialog_state": dialog_state,
            "booking_payload": booking_payload or {},
            "expected_reply_type": expected_reply_type,
            "expected_reply_reason": expected_reply_reason,
            "current_goal": current_goal or ("booking" if booking_payload else None),
            "turn_journal": runtime_turn_journal,
            "conversation_projection": runtime_projection,
        }

    def write_runtime_payload(
        self,
        context: dict[str, Any] | None,
        *,
        decision: PolicyDecision,
        execution_meta: dict[str, Any] | None,
        now: datetime,
        conversation_id: str | None = None,
        trace_id: str | None = None,
        last_reply_ref: str | None = None,
        runtime_key: str = _RUNTIME_CONTEXT_KEY,
    ) -> tuple[dict[str, Any], DialogState, dict[str, Any] | None]:
        working_context = dict(context) if isinstance(context, dict) else {}
        loaded = self.load_runtime_payload(working_context, runtime_key=runtime_key)
        existing_booking = loaded["booking_payload"] if isinstance(loaded["booking_payload"], dict) else {}
        execution_payload = dict(execution_meta) if isinstance(execution_meta, dict) else {}
        slot_values = execution_payload.get("slot_values")
        if not isinstance(slot_values, dict):
            slot_values = decision.slots

        clear_booking = bool(execution_payload.get("clear_booking"))
        is_synthetic_control = self._is_synthetic_control_decision(decision)
        merged_booking = self.normalize_booking_payload(existing_booking)
        loaded_current_goal = self._normalize_projection_token(loaded.get("current_goal"))
        decision_pending_contract = self._decision_pending_question_contract(decision)
        decision_semantic_contract = self._decision_semantic_contract(decision)
        collect_next_slot = self._normalize_projection_token(
            execution_payload.get("next_slot")
            or decision_pending_contract.next_question
            or _CANONICAL_EXPECTED_REPLY_SLOT_BY_TYPE.get(
                self._normalize_projection_token(decision_pending_contract.expected_reply_type) or ""
            )
        )
        collect_is_booking_followup = collect_next_slot in _BOOKING_CONTEXT_SLOT_KEYS
        owner_pending_question_contract = None
        if decision.outcome != "COLLECT":
            owner_pending_question_contract = self.project_pending_question_contract(
                decision_pending_contract,
            )
        if decision.outcome == "COLLECT" and collect_is_booking_followup:
            merged_booking = self.build_collect_owner_booking_payload(
                existing_booking=existing_booking,
                now=now,
                last_question=collect_next_slot or "service",
                slot_values=slot_values,
            )
        elif (
            decision.outcome == "FACT"
            and loaded_current_goal == "booking"
            and merged_booking
            and slot_values
        ):
            merged_booking = self.build_collect_owner_booking_payload(
                existing_booking=merged_booking,
                now=now,
                last_question=self._normalize_projection_token(
                    merged_booking.get("last_question")
                )
                or "service",
                slot_values=slot_values,
            )
        if isinstance(merged_booking, dict):
            semantic_referents = (
                decision_semantic_contract.get("referents")
                if isinstance(decision_semantic_contract.get("referents"), dict)
                else {}
            )
            specialist_referent = (
                semantic_referents.get("specialist")
                if isinstance(semantic_referents.get("specialist"), dict)
                else {}
            )
            for specialist_key in ("specialist_name", "specialist_id"):
                referent_field = "value" if specialist_key == "specialist_name" else "entity_id"
                specialist_value = self._normalize_projection_token(
                    specialist_referent.get(referent_field)
                    or execution_payload.get(specialist_key)
                    or merged_booking.get(specialist_key)
                )
                if specialist_value:
                    merged_booking[specialist_key] = specialist_value
            customer_name = self._normalize_projection_token(
                execution_payload.get("customer_name")
            )
            if customer_name and not merged_booking.get("name"):
                merged_booking["name"] = customer_name

        expected_reply_type = None
        expected_reply_reason = None
        current_goal = None
        if clear_booking:
            merged_booking = None
        elif decision.outcome == "HANDOFF":
            expected_reply_type = None
            expected_reply_reason = None
            current_goal = None
        elif owner_pending_question_contract:
            projections = self.project_expected_reply_projections(
                expected_reply_type=owner_pending_question_contract.get("expected_reply_type"),
                expected_reply_reason=owner_pending_question_contract.get("reason"),
            )
            expected_reply_type = projections.expected_reply_type
            expected_reply_reason = projections.expected_reply_reason
            current_goal = loaded_current_goal or self._normalize_projection_token(
                decision.meta.get("goal")
            )
            if current_goal is None and (merged_booking or decision.intent == "booking"):
                current_goal = "booking"
        elif decision.outcome == "COLLECT":
            next_slot = collect_next_slot
            if next_slot:
                expected_reply_type = {
                    "service": "service_choice",
                    "datetime": "time",
                    "name": "name",
                    "phone": "phone",
                    "media": "media",
                }.get(next_slot)
                expected_reply_reason = f"collect:{next_slot}"
            if collect_is_booking_followup:
                current_goal = "booking"
            else:
                current_goal = (
                    self._normalize_projection_token(decision.meta.get("goal"))
                    or self._normalize_projection_token(decision.intent)
                    or loaded_current_goal
                )
        elif merged_booking:
            existing_pending_question_contract = (
                self.project_pending_question_contract_with_projection_fallback(
                    loaded["dialog_state"].pending_question_contract,
                    expected_reply_type=loaded.get("expected_reply_type"),
                    expected_reply_reason=loaded.get("expected_reply_reason"),
                )
                or {}
            )
            projections = self.project_expected_reply_projections(
                expected_reply_type=existing_pending_question_contract.get("expected_reply_type"),
                expected_reply_reason=existing_pending_question_contract.get("reason"),
            )
            expected_reply_type = projections.expected_reply_type
            expected_reply_reason = projections.expected_reply_reason
            current_goal = "booking"

        grounded_referents = self._build_runtime_grounded_referents(
            existing_state=loaded["dialog_state"],
            booking_payload=merged_booking,
            decision=decision,
            execution_payload=execution_payload,
        )
        semantic_contract = self._build_runtime_semantic_contract(
            existing_state=loaded["dialog_state"],
            booking_payload=merged_booking,
            decision=decision,
            execution_payload=execution_payload,
            grounded_referents=grounded_referents,
        )
        semantic_execution_payload = dict(execution_payload)
        if self._has_canonical_semantic_owner(decision):
            semantic_enrichment = self._execution_semantic_payload(
                semantic_execution_payload,
                owner_only=True,
            )
            if semantic_enrichment and "semantic_enrichment" not in semantic_execution_payload:
                semantic_execution_payload["semantic_enrichment"] = semantic_enrichment
            semantic_execution_payload.pop("semantic_contract", None)
        elif semantic_contract and "semantic_contract" not in semantic_execution_payload:
            semantic_execution_payload["semantic_contract"] = semantic_contract
        semantic_state = self._build_semantic_state(
            existing_state=loaded["dialog_state"],
            decision=decision,
            execution_payload=semantic_execution_payload,
            current_goal=current_goal,
            booking_payload=merged_booking,
            now=now,
        )
        current_goal = current_goal or self._normalize_projection_token(
            semantic_state.materialized_frame.user_goal
        )
        if not is_synthetic_control:
            semantic_contract = (
                self._semantic_contract_from_frame(semantic_state.materialized_frame)
                or semantic_contract
            )
        if not expected_reply_type and not is_synthetic_control:
            frame_pending_contract = self._pending_question_from_frame(
                semantic_state.materialized_frame
            ) or {}
            frame_projections = self.project_expected_reply_projections(
                expected_reply_type=frame_pending_contract.get("expected_reply_type"),
                expected_reply_reason=frame_pending_contract.get("reason"),
            )
            expected_reply_type = frame_projections.expected_reply_type
            expected_reply_reason = frame_projections.expected_reply_reason

        if expected_reply_type and owner_pending_question_contract:
            dialog_state = self.build_collect_owner_state(
                decision=decision,
                expected_reply_type=expected_reply_type,
                expected_reply_reason=expected_reply_reason,
                grounded_referents=grounded_referents,
            )
            dialog_state.meta["current_goal"] = current_goal
            dialog_state.semantic_state = semantic_state
        elif expected_reply_type and decision.outcome == "COLLECT":
            dialog_state = self.build_collect_owner_state(
                decision=decision,
                expected_reply_type=expected_reply_type,
                expected_reply_reason=expected_reply_reason,
                grounded_referents=grounded_referents,
            )
            dialog_state.meta["current_goal"] = current_goal
            dialog_state.semantic_state = semantic_state
        elif expected_reply_type and current_goal == "booking":
            dialog_state = self._build_booking_followup_dialog_state(
                base_state=loaded["dialog_state"],
                decision=decision,
                expected_reply_type=expected_reply_type,
                expected_reply_reason=expected_reply_reason,
                grounded_referents=grounded_referents,
            )
            dialog_state.meta["current_goal"] = current_goal
            dialog_state.semantic_state = semantic_state
        else:
            interaction_state = InteractionState(
                interaction_owner=decision.interaction.owner,
                interaction_target=decision.interaction.target,
                interaction_relation=decision.interaction.relation,
                grounded_referents=grounded_referents,
            )
            dialog_state = DialogState(
                semantic_state=semantic_state,
                current_referents=self._current_referents_from_grounded_referents(
                    grounded_referents
                ),
                interaction_state=interaction_state,
                projections=DialogStateProjections(
                    expected_reply_type=expected_reply_type,
                    expected_reply_reason=expected_reply_reason,
                    session_memory_interaction_state=interaction_state,
                ),
                meta={
                    "writer": "dialog_state_service",
                    "current_goal": current_goal,
                },
            )
        dialog_state = self.project_state_compatibility_fields(
            dialog_state,
            expected_reply_type=expected_reply_type,
            expected_reply_reason=expected_reply_reason,
        )
        manager_payload = (
            working_context.get("context_manager")
            if isinstance(working_context.get("context_manager"), dict)
            else None
        )
        manager_message_count = self._canonical_int(
            manager_payload.get("message_count") if isinstance(manager_payload, dict) else None
        )
        existing_runtime_class_carryover = self._normalize_class_carryover_payload(
            loaded["dialog_state"].meta.get("class_carryover")
            if isinstance(loaded["dialog_state"].meta, dict)
            else None
        )
        runtime_class_carryover = self._build_touched_slice_class_carryover_payload(
            execution_meta=execution_payload,
            message_count=manager_message_count,
        ) or existing_runtime_class_carryover
        dialog_meta = dict(dialog_state.meta)
        if runtime_class_carryover:
            dialog_meta["class_carryover"] = deepcopy(runtime_class_carryover)
        else:
            dialog_meta.pop("class_carryover", None)
        dialog_state = dialog_state.model_copy(update={"meta": dialog_meta})
        projection_pending_contract = self.project_pending_question_contract_with_projection_fallback(
            dialog_state.pending_question_contract,
            expected_reply_type=dialog_state.projections.expected_reply_type,
            expected_reply_reason=dialog_state.projections.expected_reply_reason,
        )
        conversation_projection = self._build_conversation_projection(
            conversation_id=conversation_id,
            existing_projection=(
                loaded.get("conversation_projection")
                if isinstance(loaded.get("conversation_projection"), ConversationProjectionV1)
                else None
            ),
            decision=decision,
            semantic_state=dialog_state.semantic_state,
            semantic_contract=(
                dict(dialog_state.meta.get("semantic_contract"))
                if isinstance(dialog_state.meta, dict)
                and isinstance(dialog_state.meta.get("semantic_contract"), dict)
                else semantic_contract
            ),
            pending_question_contract=projection_pending_contract,
            current_goal=current_goal,
            booking_payload=merged_booking,
            last_reply_ref=last_reply_ref,
        )
        existing_journal = (
            loaded.get("turn_journal")
            if isinstance(loaded.get("turn_journal"), TurnJournalV1)
            else TurnJournalV1(conversation_id=conversation_id)
        )
        turn_journal = existing_journal.append_events(
            build_turn_journal_events(
                conversation_id=conversation_id,
                decision=decision,
                projection=conversation_projection,
                timestamp=now.isoformat(),
                trace_id=trace_id,
            )
        )

        runtime_payload = {
            "schema_version": "consultant_runtime.v1",
            "turn_journal": turn_journal.model_dump(mode="json", exclude_none=True),
            "conversation_projection": conversation_projection.model_dump(
                mode="json",
                exclude_none=True,
            ),
            "dialog_state": dialog_state.model_dump(mode="json", exclude_none=True),
            "booking": merged_booking,
            "updated_at": now.isoformat(),
        }
        runtime_payload = {
            key: value for key, value in runtime_payload.items() if value not in (None, {}, [])
        }
        updated_context = dict(working_context)
        updated_context[runtime_key] = runtime_payload
        updated_context = self.set_context_booking_payload(
            updated_context,
            merged_booking,
            key="booking",
        )
        updated_context = self.sync_runtime_compatibility_context(
            updated_context,
            now=now,
            runtime_key=runtime_key,
            context_manager_key="context_manager",
            canonical_state_key="canonical_dialog_state",
            session_memory_key="session_memory",
            expected_reply_type_key="expected_reply_type",
            expected_reply_reason_key="expected_reply_reason",
            current_goal_key="current_goal",
            session_memory_ttl_hours=24,
        )
        if runtime_class_carryover is not None or existing_runtime_class_carryover is not None:
            updated_context = self.set_context_manager_payload(
                updated_context,
                self.set_context_manager_class_carryover_payload(
                    updated_context.get("context_manager")
                    if isinstance(updated_context.get("context_manager"), dict)
                    else None,
                    manager_key="class_carryover",
                    canonical_state_key="canonical_dialog_state",
                    payload=runtime_class_carryover,
                ),
                key="context_manager",
            )

        if decision.outcome == "HANDOFF":
            pending_resume = self.capture_pending_resume_payload(
                updated_context,
                snapshot_keys=_RUNTIME_PENDING_RESUME_SNAPSHOT_KEYS,
            )
            if pending_resume:
                updated_context["pending_resume"] = pending_resume
        else:
            updated_context.pop("pending_resume", None)

        return updated_context, dialog_state, merged_booking

    def reset_runtime_continuity(
        self,
        context: dict[str, Any] | None,
        *,
        now: datetime,
        reason: str | None = None,
        runtime_key: str = _RUNTIME_CONTEXT_KEY,
        context_manager_key: str = "context_manager",
        canonical_state_key: str = "canonical_dialog_state",
        class_manager_key: str = "class_carryover",
        service_manager_key: str = "service_carryover",
        consult_context_key: str = "consult_context",
        booking_key: str = "booking",
        session_memory_key: str = "session_memory",
        re_entry_required_key: str = "re_entry_required",
        pending_resume_key: str = "pending_resume",
        intent_queue_key: str = "intent_queue",
        service_hint_key: str = "last_service_hint",
        service_hint_at_key: str = "last_service_hint_at",
    ) -> dict[str, Any]:
        updated = deepcopy(context) if isinstance(context, dict) else {}
        manager_payload = (
            updated.get(context_manager_key)
            if isinstance(updated.get(context_manager_key), dict)
            else None
        )
        manager = self.clear_context_manager_carryover_family(
            manager_payload,
            class_manager_key=class_manager_key,
            service_manager_key=service_manager_key,
            consult_manager_key=consult_context_key,
            canonical_state_key=canonical_state_key,
            referent_key="service",
        )
        manager.pop("current_goal", None)
        message_count = self._canonical_int(
            manager.get("message_count") if isinstance(manager, dict) else None
        )
        canonical_state = self.normalize_context_manager_canonical_state(
            manager.get(canonical_state_key) if isinstance(manager, dict) else None
        )
        canonical_state = self.set_canonical_pending_question_contract(
            canonical_state,
            expected_reply_type=None,
            reason=None,
            message_count=message_count,
        )
        canonical_state = self.set_canonical_interaction_state(
            canonical_state,
            resume_slot=None,
            interaction_target=None,
            interaction_relation=None,
            interaction_owner=None,
            grounded_referents=None,
            confirmation_state=None,
            degrade_reason=None,
        )
        for referent_key in ("master", "booking_ref"):
            canonical_state = self.set_canonical_referent(
                canonical_state,
                referent_key=referent_key,
                value=None,
                message_count=message_count,
            )
        manager = self.set_context_manager_canonical_state(
            manager,
            key=canonical_state_key,
            state=canonical_state,
        )
        updated = self.set_context_manager_payload(
            updated,
            manager,
            key=context_manager_key,
        )
        updated = self.set_expected_reply_context_fields(
            updated,
            expected_reply_type=None,
            expected_reply_reason=None,
        )
        updated = self.set_context_booking_payload(
            updated,
            {"active": False},
            key=booking_key,
        )
        updated = self.set_context_session_memory(
            updated,
            None,
            key=session_memory_key,
        )
        if self.is_re_entry_required(updated.get(re_entry_required_key)):
            updated = self.clear_context_re_entry_required(
                updated,
                reason=reason,
                now=now,
                key=re_entry_required_key,
            )
        else:
            updated.pop(re_entry_required_key, None)
        updated.pop(pending_resume_key, None)
        updated[intent_queue_key] = []
        updated.pop(service_hint_key, None)
        updated.pop(service_hint_at_key, None)
        updated.pop("current_goal", None)
        updated.pop(runtime_key, None)
        return updated

    def set_context_manager_payload(
        self,
        context: dict[str, Any] | None,
        payload: dict[str, Any] | None,
        *,
        key: str,
    ) -> dict[str, Any]:
        manager = dict(payload) if isinstance(payload, dict) and payload else None
        return self._set_optional_context_payload(
            context,
            key=key,
            payload=manager,
        )

    def _context_trace_list(self, value: Any) -> list[dict[str, Any]]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            return [value]
        return []

    def _context_trace_key(self, item: dict[str, Any]) -> tuple[Any, Any, Any]:
        return (item.get("stage"), item.get("decision"), item.get("recorded_at"))

    def merge_conversation_context_trace(
        self,
        existing: Any,
        incoming: Any,
        *,
        retain_trace: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] | None = None,
    ) -> list[dict[str, Any]] | None:
        existing_list = self._context_trace_list(existing)
        incoming_list = self._context_trace_list(incoming)
        if not existing_list and not incoming_list:
            return None
        if not existing_list:
            return retain_trace(incoming_list) if callable(retain_trace) else incoming_list
        if not incoming_list:
            return retain_trace(existing_list) if callable(retain_trace) else existing_list

        merged = list(existing_list)
        seen = {self._context_trace_key(item) for item in existing_list}
        for item in incoming_list:
            key = self._context_trace_key(item)
            if key != (None, None, None) and key in seen:
                continue
            merged.append(item)
            seen.add(key)
        return retain_trace(merged) if callable(retain_trace) else merged

    def prepare_conversation_context_write(
        self,
        existing_context: dict[str, Any] | None,
        incoming_context: Any,
        *,
        decision_trace_key: str,
        preserve_keys: tuple[str, ...] = (),
        retain_trace: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] | None = None,
    ) -> Any:
        if not isinstance(incoming_context, dict):
            return incoming_context

        existing = dict(existing_context) if isinstance(existing_context, dict) else {}
        updated = dict(incoming_context)
        for key in preserve_keys:
            if key not in updated and key in existing:
                updated[key] = existing.get(key)
        merged_trace = self.merge_conversation_context_trace(
            existing.get(decision_trace_key),
            updated.get(decision_trace_key),
            retain_trace=retain_trace,
        )
        if merged_trace is not None:
            updated[decision_trace_key] = merged_trace
        return updated

    def prepare_state_service_context_write(
        self,
        existing_context: dict[str, Any] | None,
        incoming_context: Any,
        *,
        decision_trace_key: str = "decision_trace",
    ) -> Any:
        return self.prepare_conversation_context_write(
            existing_context,
            incoming_context,
            decision_trace_key=decision_trace_key,
            preserve_keys=(
                "simulation",
                "simulation_mode",
                "simulation_id",
                "simulation_llm",
                "simulation_time",
                "memory_profile",
                "memory_pending",
            ),
            retain_trace=None,
        )

    def build_pending_resume_snapshot_context(
        self,
        context: dict[str, Any] | None,
        *,
        context_manager: dict[str, Any] | None,
        expected_reply_type: str | None,
        expected_reply_reason: str | None,
        intent_queue: list[str] | None,
        booking_context: dict[str, Any] | None,
        session_memory: dict[str, Any] | None,
    ) -> dict[str, Any]:
        snapshot_context = dict(context) if isinstance(context, dict) else {}
        snapshot_context["context_manager"] = (
            dict(context_manager) if isinstance(context_manager, dict) else {}
        )
        projections = self.project_expected_reply_projections(
            expected_reply_type=expected_reply_type,
            expected_reply_reason=expected_reply_reason,
        )
        if projections.expected_reply_type:
            snapshot_context["expected_reply_type"] = projections.expected_reply_type
        else:
            snapshot_context.pop("expected_reply_type", None)
        if projections.expected_reply_reason:
            snapshot_context["expected_reply_reason"] = projections.expected_reply_reason
        else:
            snapshot_context.pop("expected_reply_reason", None)
        snapshot_context["intent_queue"] = (
            list(intent_queue) if isinstance(intent_queue, list) else []
        )
        snapshot_context["booking"] = (
            dict(booking_context) if isinstance(booking_context, dict) else {"active": False}
        )
        snapshot_context["session_memory"] = (
            dict(session_memory) if isinstance(session_memory, dict) else {}
        )
        return snapshot_context

    def sync_context_manager_expected_reply_state(
        self,
        manager: dict[str, Any] | None,
        *,
        booking_state: dict[str, Any] | None,
        expected_reply_type: str | None,
        expected_reply_reason: str | None,
        message_count: int,
        service_carryover: dict[str, Any] | None = None,
        consult_context: dict[str, Any] | None = None,
        legacy_consult_context: dict[str, Any] | None = None,
        branch_id: Any = None,
        interaction_target: str | None = None,
        interaction_relation: str | None = None,
        interaction_owner: str | None = None,
        degrade_reason: str | None = None,
        canonical_state_key: str = "canonical_dialog_state",
        service_default_ttl: int = 0,
        consult_default_ttl: int = 0,
    ) -> dict[str, Any]:
        updated = dict(manager) if isinstance(manager, dict) else {}
        normalized_booking = self.normalize_booking_payload(booking_state) or {}
        state = self.normalize_context_manager_canonical_state(updated.get(canonical_state_key))

        service_value = self._normalize_projection_token(normalized_booking.get("service"))
        if service_value:
            state = self.set_canonical_referent(
                state,
                referent_key="service",
                value=service_value,
                message_count=message_count,
                source="booking_state",
                score=1.0,
                default_ttl=service_default_ttl or None,
            )

        specialist_value = self._normalize_projection_token(
            normalized_booking.get("specialist_name") or normalized_booking.get("specialist_id")
        )
        if specialist_value:
            state = self.set_canonical_referent(
                state,
                referent_key="master",
                value=specialist_value,
                message_count=message_count,
                source="booking_state",
                score=1.0,
                default_ttl=service_default_ttl or None,
            )

        for reference_key in ("appointment_id", "booking_id", "external_booking_id"):
            reference_value = self._normalize_projection_token(normalized_booking.get(reference_key))
            if not reference_value:
                continue
            state = self.set_canonical_referent(
                state,
                referent_key="booking_ref",
                value=reference_value,
                message_count=message_count,
                source="booking_state",
                score=1.0,
            )
            break

        if branch_id is not None:
            state = self.set_canonical_referent(
                state,
                referent_key="branch",
                value=str(branch_id),
                message_count=message_count,
                source="conversation_branch",
                score=1.0,
            )

        current_referents = state.get("current_referents")
        service_payload = current_referents.get("service") if isinstance(current_referents, dict) else None
        if not isinstance(service_payload, dict) and isinstance(service_carryover, dict):
            carryover_query = self._normalize_projection_token(service_carryover.get("service_query"))
            if carryover_query:
                carryover_score = service_carryover.get("service_query_score")
                state = self.set_canonical_referent(
                    state,
                    referent_key="service",
                    value=carryover_query,
                    message_count=self._canonical_int(
                        service_carryover.get("message_count"),
                        default=message_count,
                    ),
                    source=(
                        self._normalize_projection_token(service_carryover.get("service_query_source"))
                        or "legacy_service_carryover"
                    ),
                    score=carryover_score if isinstance(carryover_score, (int, float)) else None,
                    ttl=(
                        service_carryover.get("ttl")
                        if isinstance(service_carryover.get("ttl"), int)
                        else None
                    ),
                    default_ttl=service_default_ttl or None,
                )

        consult_payload = consult_context if isinstance(consult_context, dict) else None
        if consult_payload is None and isinstance(legacy_consult_context, dict):
            consult_payload = legacy_consult_context
        if isinstance(consult_payload, dict):
            state = self.set_canonical_consult_state(
                state,
                topic=consult_payload.get("topic"),
                question=consult_payload.get("question"),
                questions=(
                    consult_payload.get("questions")
                    if isinstance(consult_payload.get("questions"), list)
                    else None
                ),
                message_count=self._canonical_int(
                    consult_payload.get("message_count"),
                    default=message_count,
                ),
                default_ttl=consult_default_ttl,
            )

        state = self.sync_canonical_question_contract_state(
            state,
            expected_reply_type=expected_reply_type,
            expected_reply_reason=expected_reply_reason,
            message_count=message_count,
            interaction_target=interaction_target,
            interaction_relation=interaction_relation,
            interaction_owner=interaction_owner,
            grounded_referents=self._grounded_referents_from_canonical_state(state),
            confirmation_state=self._booking_confirmation_state(booking_state),
            degrade_reason=degrade_reason,
        )
        return self.set_context_manager_canonical_state(
            updated,
            key=canonical_state_key,
            state=state,
        )

    def build_expected_reply_context_sync_result(
        self,
        context: dict[str, Any] | None,
        *,
        expected_reply_type: str | None,
        reason: str,
        now: datetime,
        context_manager_key: str = "context_manager",
        canonical_state_key: str = "canonical_dialog_state",
        booking_key: str = "booking",
        session_memory_key: str = "session_memory",
        re_entry_required_key: str = "re_entry_required",
        service_carryover_key: str = "service_carryover",
        consult_context_key: str = "consult_context",
        session_memory_ttl_hours: int = 24,
        service_default_ttl: int = 0,
        consult_default_ttl: int = 0,
    ) -> ExpectedReplyContextSyncResult:
        updated = deepcopy(context) if isinstance(context, dict) else {}
        projections = self.project_expected_reply_projections(
            expected_reply_type=expected_reply_type,
            expected_reply_reason=reason,
        )
        normalized_type = projections.expected_reply_type
        normalized_reason = projections.expected_reply_reason or reason

        updated = self.set_expected_reply_context_fields(
            updated,
            expected_reply_type=normalized_type,
            expected_reply_reason=normalized_reason,
        )
        manager_payload = updated.get(context_manager_key)
        manager = dict(manager_payload) if isinstance(manager_payload, dict) else {}
        manager = self.sync_context_manager_expected_reply_state(
            manager,
            booking_state=updated.get(booking_key) if isinstance(updated.get(booking_key), dict) else None,
            expected_reply_type=normalized_type,
            expected_reply_reason=normalized_reason,
            message_count=self._canonical_int(manager.get("message_count")),
            service_carryover=(
                manager.get(service_carryover_key)
                if isinstance(manager.get(service_carryover_key), dict)
                else None
            ),
            legacy_consult_context=(
                manager.get(consult_context_key)
                if isinstance(manager.get(consult_context_key), dict)
                else None
            ),
            canonical_state_key=canonical_state_key,
            service_default_ttl=service_default_ttl,
            consult_default_ttl=consult_default_ttl,
        )
        updated = self.set_context_manager_payload(
            updated,
            manager,
            key=context_manager_key,
        )

        state = self.normalize_context_manager_canonical_state(manager.get(canonical_state_key))
        interaction_state = state.get("interaction_state") if isinstance(state, dict) else None
        session_memory, session_memory_changed = self.sync_session_memory_interaction_state(
            updated.get(session_memory_key) if isinstance(updated.get(session_memory_key), dict) else None,
            interaction_state=interaction_state if isinstance(interaction_state, dict) else None,
            now=now,
            default_ttl_hours=session_memory_ttl_hours,
        )
        if session_memory_changed:
            updated = self.set_context_session_memory(
                updated,
                session_memory,
                key=session_memory_key,
            )

        re_entry_cleared = False
        if normalized_type and self.is_re_entry_required(updated.get(re_entry_required_key)):
            updated = self.clear_context_re_entry_required(
                updated,
                reason=normalized_reason,
                now=now,
                key=re_entry_required_key,
            )
            re_entry_cleared = True

        question_memory: dict[str, Any] | None = None
        if normalized_type:
            active_goal = manager.get("current_goal")
            if isinstance(active_goal, str):
                active_goal = active_goal.strip() or None
            else:
                active_goal = None
            question_memory = self.update_session_memory_on_question(
                updated.get(session_memory_key) if isinstance(updated.get(session_memory_key), dict) else None,
                expected_reply_type=normalized_type,
                active_goal=active_goal,
            )
            question_memory = self.touch_session_memory_payload(
                question_memory,
                now=now,
                default_ttl_hours=session_memory_ttl_hours,
            )
            updated = self.set_context_session_memory(
                updated,
                question_memory,
                key=session_memory_key,
            )

        pending_question_contract = self.project_context_pending_question_contract(
            updated,
            context_manager_key=context_manager_key,
            canonical_state_key=canonical_state_key,
            session_memory_key=session_memory_key,
        )
        if pending_question_contract is not None:
            session_memory_payload = self.sync_session_memory_pending_question_contract(
                question_memory
                if isinstance(question_memory, dict)
                else (
                    updated.get(session_memory_key)
                    if isinstance(updated.get(session_memory_key), dict)
                    else None
                ),
                pending_question_contract=pending_question_contract,
            )
            question_memory = session_memory_payload
            updated = self.set_context_session_memory(
                updated,
                session_memory_payload,
                key=session_memory_key,
            )

        return ExpectedReplyContextSyncResult(
            context=updated,
            context_manager=manager,
            expected_reply_type=normalized_type,
            expected_reply_reason=normalized_reason,
            pending_question_contract=pending_question_contract,
            question_memory=question_memory,
            re_entry_cleared=re_entry_cleared,
        )

    def increment_context_manager_message_count(
        self,
        manager: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], int]:
        updated = dict(manager) if isinstance(manager, dict) else {}
        count = self._canonical_int(updated.get("message_count")) + 1
        updated["message_count"] = count
        return updated, count

    def is_session_memory_expired(
        self,
        memory: dict[str, Any] | None,
        *,
        now: datetime,
        default_ttl_hours: int,
    ) -> bool:
        payload = memory if isinstance(memory, dict) else {}
        try:
            ttl_hours = int(payload.get("ttl_hours", default_ttl_hours))
        except (TypeError, ValueError):
            ttl_hours = default_ttl_hours
        last_updated_at = self._parse_iso_datetime(payload.get("last_updated_at"))
        if not last_updated_at:
            return True
        return (now - last_updated_at) > timedelta(hours=max(ttl_hours, 1))

    def normalize_session_memory_payload(
        self,
        memory: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], str | None]:
        if not isinstance(memory, dict):
            return {}, "invalid_type"

        normalized = dict(memory)
        errors: list[str] = []

        def mark_error(reason: str) -> None:
            if reason not in errors:
                errors.append(reason)

        def normalize_string(key: str) -> None:
            value = normalized.get(key)
            if value is None:
                return
            if not isinstance(value, str):
                normalized.pop(key, None)
                mark_error(f"{key}_type")
                return
            value = value.strip()
            if value:
                normalized[key] = value
            else:
                normalized.pop(key, None)

        def normalize_int(key: str) -> None:
            value = normalized.get(key)
            if value is None:
                return
            try:
                normalized[key] = int(value)
            except (TypeError, ValueError):
                normalized.pop(key, None)
                mark_error(f"{key}_type")

        def normalize_list(key: str, *, limit: int | None = None) -> None:
            value = normalized.get(key)
            if value is None:
                return
            if not isinstance(value, list):
                normalized.pop(key, None)
                mark_error(f"{key}_type")
                return
            cleaned: list[str] = []
            for item in value:
                if not isinstance(item, str):
                    continue
                cleaned_item = item.strip()
                if cleaned_item:
                    cleaned.append(cleaned_item)
            if limit:
                cleaned = cleaned[-limit:]
            normalized[key] = cleaned

        def normalize_dict(key: str, *, values_as_str: bool) -> None:
            value = normalized.get(key)
            if value is None:
                return
            if not isinstance(value, dict):
                normalized.pop(key, None)
                mark_error(f"{key}_type")
                return
            cleaned: dict[str, Any] = {}
            for raw_key, raw_value in value.items():
                if not isinstance(raw_key, str):
                    continue
                cleaned_key = raw_key.strip()
                if not cleaned_key:
                    continue
                if values_as_str:
                    if not isinstance(raw_value, str):
                        continue
                    cleaned_value = raw_value.strip()
                    if not cleaned_value:
                        continue
                    cleaned[cleaned_key] = cleaned_value
                else:
                    cleaned[cleaned_key] = raw_value
            normalized[key] = cleaned

        normalize_string("mode")
        normalize_string("summary")
        normalize_string("last_updated")
        normalize_string("last_updated_at")
        normalize_string("active_goal")
        normalize_string("last_question_type")
        normalize_int("ttl")
        normalize_int("ttl_hours")
        normalize_list("goal_stack", limit=3)
        normalize_list("unanswered_questions")
        normalize_dict("slots", values_as_str=False)
        normalize_dict("pending_slots", values_as_str=True)

        interaction_state = normalized.get("interaction_state")
        cleaned_state, error = self.project_session_memory_interaction_state(interaction_state)
        if cleaned_state is None:
            if interaction_state is not None:
                normalized.pop("interaction_state", None)
                if error:
                    mark_error(error)
        else:
            normalized["interaction_state"] = cleaned_state

        pending_question_contract = self.project_session_memory_pending_question_contract(normalized)
        if pending_question_contract is not None:
            normalized["pending_question_contract"] = pending_question_contract
            normalized.pop("last_question_type", None)
        else:
            normalized.pop("pending_question_contract", None)

        try:
            MemoryContract(**normalized)
        except ValidationError as exc:
            return normalized, str(exc)
        if errors:
            return normalized, ",".join(errors)
        return normalized, None

    def project_session_memory_pending_question_contract(
        self,
        memory: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(memory, dict):
            return None
        pending_question_contract = self.project_pending_question_contract(
            memory.get("pending_question_contract")
        )
        if pending_question_contract is not None:
            return self.project_pending_question_contract(
                pending_question_contract,
                expected_reply_type=(
                    None
                    if pending_question_contract.get("expected_reply_type")
                    else self._normalize_projection_token(memory.get("last_question_type"))
                ),
            )
        return self.project_pending_question_contract(
            None,
            expected_reply_type=self._normalize_projection_token(memory.get("last_question_type")),
        )

    def capture_pending_resume_payload(
        self,
        context: dict[str, Any] | None,
        *,
        snapshot_keys: set[str],
    ) -> dict[str, Any]:
        if not isinstance(context, dict):
            return {}

        payload: dict[str, Any] = {}

        if "context_manager" in snapshot_keys:
            payload["context_manager"] = self.build_context_manager_compatibility_snapshot(context)

        pending_question_contract = self.project_context_pending_question_contract(context)
        if isinstance(payload.get("context_manager"), dict):
            payload["context_manager"] = self.build_context_manager_compatibility_snapshot(context)

        projections = self.project_expected_reply_projections(
            expected_reply_type=(
                pending_question_contract.get("expected_reply_type")
                if isinstance(pending_question_contract, dict)
                else None
            ),
            expected_reply_reason=(
                pending_question_contract.get("reason")
                if isinstance(pending_question_contract, dict)
                else None
            ),
        )
        if "expected_reply_type" in snapshot_keys and projections.expected_reply_type:
            payload["expected_reply_type"] = projections.expected_reply_type
        if "expected_reply_reason" in snapshot_keys and projections.expected_reply_reason:
            payload["expected_reply_reason"] = projections.expected_reply_reason

        intent_queue = context.get("intent_queue")
        if "intent_queue" in snapshot_keys and isinstance(intent_queue, list):
            payload["intent_queue"] = deepcopy(intent_queue)

        loaded_runtime = self.load_runtime_payload(context)
        runtime_payload = (
            context.get(_RUNTIME_CONTEXT_KEY)
            if isinstance(context.get(_RUNTIME_CONTEXT_KEY), dict)
            else None
        )
        runtime_projection = self.normalize_runtime_conversation_projection(
            runtime_payload.get("conversation_projection")
            if isinstance(runtime_payload, dict)
            else None
        )
        projection_booking = (
            self.normalize_booking_payload(runtime_projection.booking_state)
            if isinstance(runtime_projection, ConversationProjectionV1)
            else None
        )
        booking = projection_booking or (
            loaded_runtime.get("booking_payload")
            if isinstance(loaded_runtime.get("booking_payload"), dict)
            else context.get("booking")
        )
        if "booking" in snapshot_keys and isinstance(booking, dict):
            payload["booking"] = deepcopy(booking)

        session_memory_snapshot = self.build_context_session_memory_snapshot(context)
        if "session_memory" in snapshot_keys and isinstance(session_memory_snapshot, dict) and session_memory_snapshot:
            payload["session_memory"] = session_memory_snapshot

        last_service_hint = self._normalize_projection_token(context.get("last_service_hint"))
        if "last_service_hint" in snapshot_keys and last_service_hint:
            payload["last_service_hint"] = last_service_hint

        last_service_hint_at = self._normalize_projection_token(context.get("last_service_hint_at"))
        if "last_service_hint_at" in snapshot_keys and last_service_hint_at:
            payload["last_service_hint_at"] = last_service_hint_at

        return payload

    def restore_pending_resume_payload(
        self,
        pending_resume: dict[str, Any] | None,
        *,
        now: datetime,
    ) -> dict[str, Any]:
        if not isinstance(pending_resume, dict):
            return {}

        restored: dict[str, Any] = {}

        restored["context_manager"] = self.build_context_manager_compatibility_snapshot(pending_resume)
        pending_question_contract = self.project_context_manager_pending_question_contract(
            pending_resume
        )
        projections = self.project_expected_reply_projections(
            expected_reply_type=(
                pending_question_contract.get("expected_reply_type")
                if isinstance(pending_question_contract, dict)
                else None
            ),
            expected_reply_reason=(
                pending_question_contract.get("reason")
                if isinstance(pending_question_contract, dict)
                else None
            ),
        )
        if projections.expected_reply_type:
            restored["expected_reply_type"] = projections.expected_reply_type
        if projections.expected_reply_reason:
            restored["expected_reply_reason"] = projections.expected_reply_reason

        intent_queue = pending_resume.get("intent_queue")
        if isinstance(intent_queue, list):
            restored["intent_queue"] = deepcopy(intent_queue)
        else:
            restored["intent_queue"] = []

        booking_context = pending_resume.get("booking")
        if isinstance(booking_context, dict):
            restored["booking"] = deepcopy(booking_context)
        else:
            restored["booking"] = {"active": False}

        session_memory_restored = self.build_context_session_memory_snapshot(
            pending_resume,
            now=now,
            default_ttl_hours=24,
        )
        if isinstance(session_memory_restored, dict) and session_memory_restored:
            restored["session_memory"] = session_memory_restored

        service_hint = self._normalize_projection_token(
            pending_resume.get("last_service_hint") or pending_resume.get("service_hint")
        )
        if service_hint:
            restored["last_service_hint"] = service_hint

        service_hint_at = self._normalize_projection_token(
            pending_resume.get("last_service_hint_at") or pending_resume.get("service_hint_at")
        )
        if service_hint_at:
            restored["last_service_hint_at"] = service_hint_at

        restored["re_entry_required"] = self.set_re_entry_required(reason="pending_resume", now=now)
        return restored

    def derive_pending_resume_reason(
        self,
        context: dict[str, Any] | None,
        *,
        pending_resume_key: str = "pending_resume",
        context_manager_key: str = "context_manager",
        expected_reply_reason_key: str = "expected_reply_reason",
        session_memory_key: str = "session_memory",
        canonical_state_key: str = "canonical_dialog_state",
    ) -> str | None:
        if not isinstance(context, dict):
            return None

        def _extract_reason(candidate_context: dict[str, Any] | None) -> str | None:
            pending_contract = self.project_context_manager_pending_question_contract(
                candidate_context,
                context_manager_key=context_manager_key,
                canonical_state_key=canonical_state_key,
            )
            if not isinstance(pending_contract, dict):
                return None
            return self._normalize_projection_token(pending_contract.get("reason"))

        reason = _extract_reason(context)
        if reason:
            return reason

        pending_resume = context.get(pending_resume_key)
        if not isinstance(pending_resume, dict):
            return None

        return _extract_reason(pending_resume)

    def derive_pending_booking_resume_boundary_payload(
        self,
        context: dict[str, Any] | None,
        *,
        now: datetime | None = None,
        prompt_builder: Callable[[str | None], str | None] | None = None,
        pending_resume_key: str = "pending_resume",
        context_manager_key: str = "context_manager",
        booking_key: str = "booking",
        session_memory_key: str = "session_memory",
        expected_reply_type_key: str = "expected_reply_type",
    ) -> dict[str, Any] | None:
        if not isinstance(context, dict):
            return None

        def _build_boundary_payload(
            *,
            expected_reply_type: str | None,
            booking_state: dict[str, Any] | None,
            current_goal: str | None,
            session_memory: dict[str, Any] | None,
        ) -> dict[str, Any] | None:
            booking_payload = self.normalize_booking_payload(booking_state) or {}
            session_payload = dict(session_memory) if isinstance(session_memory, dict) else {}
            normalized_goal = self._normalize_projection_token(current_goal)
            memory_goal = self._normalize_projection_token(session_payload.get("active_goal"))
            booking_resume_active = bool(
                booking_payload.get("active") is True
                or normalized_goal == "booking"
                or memory_goal == "booking"
            )
            if not booking_resume_active:
                return None

            normalized_expected_reply = self.project_expected_reply_projections(
                expected_reply_type=expected_reply_type,
                expected_reply_reason=None,
            ).expected_reply_type
            if normalized_expected_reply not in _PENDING_RESUME_BOUNDARY_REPLY_TYPES:
                normalized_expected_reply = None

            booking_slot = self._normalize_projection_token(booking_payload.get("last_question"))
            if normalized_expected_reply is None and booking_slot in _PENDING_RESUME_BOUNDARY_REPLY_BY_SLOT:
                normalized_expected_reply = _PENDING_RESUME_BOUNDARY_REPLY_BY_SLOT[booking_slot]
            if normalized_expected_reply is None:
                inferred_booking_slot = self._infer_pending_booking_resume_slot(booking_payload)
                if booking_slot is None:
                    booking_slot = inferred_booking_slot
                if inferred_booking_slot in _PENDING_RESUME_BOUNDARY_REPLY_BY_SLOT:
                    normalized_expected_reply = _PENDING_RESUME_BOUNDARY_REPLY_BY_SLOT[
                        inferred_booking_slot
                    ]

            if normalized_expected_reply is None:
                last_question_type = self._normalize_projection_token(
                    session_payload.get("last_question_type")
                )
                if last_question_type in _PENDING_RESUME_BOUNDARY_REPLY_TYPES:
                    normalized_expected_reply = last_question_type
            if normalized_expected_reply is None:
                return None

            resume_slot = _CANONICAL_EXPECTED_REPLY_SLOT_BY_TYPE.get(normalized_expected_reply)
            if not resume_slot and booking_slot in _CANONICAL_PENDING_SLOTS:
                resume_slot = booking_slot
            if not resume_slot:
                return None

            boundary_booking_state = dict(booking_payload)
            if boundary_booking_state.get("active") is not True:
                boundary_booking_state["active"] = True
                if now is not None:
                    boundary_booking_state["started_at"] = now.isoformat()
            boundary_booking_state["last_question"] = resume_slot
            normalized_booking_state = self.normalize_booking_payload(boundary_booking_state)
            if not normalized_booking_state:
                return None

            payload: dict[str, Any] = {
                "booking_state": normalized_booking_state,
                "expected_reply_type": normalized_expected_reply,
                "resume_slot": resume_slot,
            }
            if callable(prompt_builder):
                boundary_prompt = prompt_builder(normalized_expected_reply)
                if not boundary_prompt:
                    return None
                payload["prompt"] = boundary_prompt
            return payload

        live_pending_question_contract = self.project_context_manager_pending_question_contract(
            context,
            context_manager_key=context_manager_key,
        )
        live_boundary_payload = _build_boundary_payload(
            expected_reply_type=(
                live_pending_question_contract.get("expected_reply_type")
                if isinstance(live_pending_question_contract, dict)
                else None
            ),
            booking_state=context.get(booking_key) if isinstance(context.get(booking_key), dict) else None,
            current_goal=self.project_context_current_goal(context),
            session_memory=(
                context.get(session_memory_key)
                if isinstance(context.get(session_memory_key), dict)
                else None
            ),
        )
        if live_boundary_payload is not None:
            return live_boundary_payload

        pending_resume = context.get(pending_resume_key)
        if not isinstance(pending_resume, dict):
            return None

        pending_question_contract = self.project_context_manager_pending_question_contract(
            pending_resume,
            context_manager_key=context_manager_key,
        )
        return _build_boundary_payload(
            expected_reply_type=(
                pending_question_contract.get("expected_reply_type")
                if isinstance(pending_question_contract, dict)
                else None
            ),
            booking_state=(
                pending_resume.get(booking_key)
                if isinstance(pending_resume.get(booking_key), dict)
                else None
            ),
            current_goal=self.project_context_current_goal(pending_resume),
            session_memory=(
                pending_resume.get(session_memory_key)
                if isinstance(pending_resume.get(session_memory_key), dict)
                else None
            ),
        )

    def _infer_pending_booking_resume_slot(
        self,
        booking_state: dict[str, Any] | None,
    ) -> str | None:
        booking_payload = self.normalize_booking_payload(booking_state) or {}
        if booking_payload.get("active") is not True:
            return None
        for slot in _CANONICAL_PENDING_SLOT_ORDER:
            if slot == "phone":
                continue
            if self._normalize_projection_token(booking_payload.get(slot)) is None:
                return slot
        return None

    def normalize_memory_profile(
        self,
        payload: dict[str, Any] | None,
        *,
        now: datetime,
        default_ttl_days: int,
    ) -> tuple[dict[str, Any], bool]:
        changed = False
        if not isinstance(payload, dict):
            payload = {}
            changed = True

        normalized = deepcopy(payload)
        if normalized.get("version") != 1:
            normalized["version"] = 1
            changed = True

        ttl_days = normalized.get("ttl_days")
        if not isinstance(ttl_days, int) or ttl_days <= 0:
            normalized["ttl_days"] = default_ttl_days
            changed = True

        consent = normalized.get("consent")
        if not isinstance(consent, dict):
            consent = {}
            changed = True
        status = consent.get("status")
        if status not in _MEMORY_PROFILE_CONSENT_STATUSES:
            consent["status"] = "unknown"
            changed = True
        if "prompt_count" not in consent:
            consent["prompt_count"] = 0
            changed = True
        normalized["consent"] = consent

        items = normalized.get("items")
        if not isinstance(items, dict):
            items = {}
            changed = True
        pruned: dict[str, Any] = {}
        for key, item in items.items():
            if not isinstance(key, str) or not isinstance(item, dict):
                changed = True
                continue
            expires_at = self._parse_memory_profile_time(item.get("expires_at"))
            if expires_at and expires_at <= now:
                changed = True
                continue
            pruned[key] = deepcopy(item)
        if pruned != items:
            changed = True
        normalized["items"] = pruned

        last_updated_at = normalized.get("last_updated_at")
        if last_updated_at and not self._parse_memory_profile_time(last_updated_at):
            normalized.pop("last_updated_at", None)
            changed = True
        return normalized, changed

    def get_memory_profile(
        self,
        payload: dict[str, Any] | None,
        *,
        now: datetime,
        default_ttl_days: int,
    ) -> tuple[dict[str, Any], bool]:
        return self.normalize_memory_profile(
            payload,
            now=now,
            default_ttl_days=default_ttl_days,
        )

    def set_memory_profile(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict) or not payload:
            return None
        return deepcopy(payload)

    def get_memory_pending(
        self,
        payload: dict[str, Any] | None,
        *,
        now: datetime,
    ) -> tuple[dict[str, Any] | None, bool]:
        if not isinstance(payload, dict):
            return None, False
        expires_at = self._parse_memory_profile_time(payload.get("expires_at"))
        if expires_at and expires_at <= now:
            return None, True
        return deepcopy(payload), False

    def set_memory_pending(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict) or not payload:
            return None
        return deepcopy(payload)

    def _set_optional_context_payload(
        self,
        context: dict[str, Any] | None,
        *,
        key: str,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        updated = dict(context) if isinstance(context, dict) else {}
        if payload:
            updated[key] = deepcopy(payload)
        else:
            updated.pop(key, None)
        return updated

    def _set_optional_manager_payload(
        self,
        manager: dict[str, Any] | None,
        *,
        key: str,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        updated = dict(manager) if isinstance(manager, dict) else {}
        if payload:
            updated[key] = deepcopy(payload)
        else:
            updated.pop(key, None)
        return updated

    def normalize_re_entry_required(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        required = payload.get("required")
        if not isinstance(required, bool):
            return None

        cleaned: dict[str, Any] = {"required": required}
        reason = self._normalize_projection_token(payload.get("reason"))
        if reason:
            cleaned["reason"] = reason
        if required:
            set_at = self._normalize_projection_token(payload.get("set_at"))
            if set_at:
                cleaned["set_at"] = set_at
        else:
            cleared_at = self._normalize_projection_token(payload.get("cleared_at"))
            if cleared_at:
                cleaned["cleared_at"] = cleared_at
        return ReEntryRequiredState.model_validate(cleaned).model_dump(exclude_none=True)

    def is_re_entry_required(self, payload: dict[str, Any] | None) -> bool:
        normalized = self.normalize_re_entry_required(payload)
        if not isinstance(normalized, dict):
            return False
        return normalized.get("required") is True

    def set_re_entry_required(
        self,
        *,
        reason: str | None,
        now: datetime,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "required": True,
            "set_at": now.isoformat(),
        }
        normalized_reason = self._normalize_projection_token(reason)
        if normalized_reason:
            payload["reason"] = normalized_reason
        return ReEntryRequiredState.model_validate(payload).model_dump(exclude_none=True)

    def set_context_re_entry_required_payload(
        self,
        context: dict[str, Any] | None,
        payload: dict[str, Any] | None,
        *,
        key: str,
    ) -> dict[str, Any]:
        return self._set_optional_context_payload(
            context,
            key=key,
            payload=self.normalize_re_entry_required(payload),
        )

    def set_context_re_entry_required(
        self,
        context: dict[str, Any] | None,
        *,
        reason: str | None,
        now: datetime,
        key: str,
    ) -> dict[str, Any]:
        return self.set_context_re_entry_required_payload(
            context,
            self.set_re_entry_required(reason=reason, now=now),
            key=key,
        )

    def clear_re_entry_required(
        self,
        *,
        reason: str | None,
        now: datetime,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "required": False,
            "cleared_at": now.isoformat(),
        }
        normalized_reason = self._normalize_projection_token(reason)
        if normalized_reason:
            payload["reason"] = normalized_reason
        return ReEntryRequiredState.model_validate(payload).model_dump(exclude_none=True)

    def clear_context_re_entry_required(
        self,
        context: dict[str, Any] | None,
        *,
        reason: str | None,
        now: datetime,
        key: str,
    ) -> dict[str, Any]:
        return self.set_context_re_entry_required_payload(
            context,
            self.clear_re_entry_required(reason=reason, now=now),
            key=key,
        )

    def normalize_handover_confirmation(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        cleaned: dict[str, Any] = {}
        asked_at = self._normalize_projection_token(payload.get("asked_at"))
        if asked_at:
            cleaned["asked_at"] = asked_at
        for key in ("status", "trigger_type", "trigger_value", "user_message"):
            value = self._normalize_projection_token(payload.get(key))
            if value:
                cleaned[key] = value
        if not cleaned:
            return None
        return HandoverConfirmationState.model_validate(cleaned).model_dump(exclude_none=True)

    def normalize_reengage_confirmation(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        cleaned: dict[str, Any] = {}
        asked_at = self._normalize_projection_token(payload.get("asked_at"))
        if asked_at:
            cleaned["asked_at"] = asked_at
        booking_messages = payload.get("booking_messages")
        if isinstance(booking_messages, list):
            normalized_messages = [
                item.strip()
                for item in booking_messages
                if isinstance(item, str) and item.strip()
            ]
            if normalized_messages:
                cleaned["booking_messages"] = normalized_messages
        if not cleaned:
            return None
        return ReengageConfirmationState.model_validate(cleaned).model_dump(exclude_none=True)

    def normalize_asr_confirmation(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        cleaned: dict[str, Any] = {}
        asked_at = self._normalize_projection_token(payload.get("asked_at"))
        if asked_at:
            cleaned["asked_at"] = asked_at
        transcript = self._normalize_projection_token(payload.get("transcript"))
        if transcript:
            cleaned["transcript"] = transcript
        attempt = payload.get("attempt")
        if isinstance(attempt, int) and attempt > 0:
            cleaned["attempt"] = attempt
        if not cleaned:
            return None
        return AsrConfirmationState.model_validate(cleaned).model_dump(exclude_none=True)

    def is_confirmation_active(
        self,
        payload: dict[str, Any] | None,
        *,
        now: datetime,
        ttl_minutes: int,
    ) -> bool:
        if ttl_minutes <= 0:
            return False
        if not isinstance(payload, dict):
            return False
        asked_at = self._parse_iso_datetime(payload.get("asked_at"))
        if asked_at is None:
            return False
        return (now - asked_at) <= timedelta(minutes=ttl_minutes)

    def set_handover_confirmation(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return self.normalize_handover_confirmation(payload)

    def set_reengage_confirmation(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return self.normalize_reengage_confirmation(payload)

    def set_asr_confirmation(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return self.normalize_asr_confirmation(payload)

    def set_context_handover_confirmation(
        self,
        context: dict[str, Any] | None,
        payload: dict[str, Any] | None,
        *,
        key: str = "handover_confirmation",
    ) -> dict[str, Any]:
        return self._set_optional_context_payload(
            context,
            key=key,
            payload=self.set_handover_confirmation(payload),
        )

    def set_context_reengage_confirmation(
        self,
        context: dict[str, Any] | None,
        payload: dict[str, Any] | None,
        *,
        key: str,
    ) -> dict[str, Any]:
        return self._set_optional_context_payload(
            context,
            key=key,
            payload=self.set_reengage_confirmation(payload),
        )

    def set_context_asr_confirmation(
        self,
        context: dict[str, Any] | None,
        payload: dict[str, Any] | None,
        *,
        key: str,
    ) -> dict[str, Any]:
        return self._set_optional_context_payload(
            context,
            key=key,
            payload=self.set_asr_confirmation(payload),
        )

    def normalize_asr_inflight(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        cleaned: dict[str, Any] = {}
        started_at = self._normalize_projection_token(payload.get("started_at"))
        if started_at:
            cleaned["started_at"] = started_at
        expires_at = self._normalize_projection_token(payload.get("expires_at"))
        if expires_at:
            cleaned["expires_at"] = expires_at
        if not cleaned:
            return None
        return AsrInflightState.model_validate(cleaned).model_dump(exclude_none=True)

    def get_asr_inflight(
        self,
        payload: dict[str, Any] | None,
        *,
        now: datetime,
    ) -> tuple[dict[str, Any] | None, bool]:
        normalized = self.normalize_asr_inflight(payload)
        if not normalized:
            return None, False
        expires_at = self._parse_iso_datetime(normalized.get("expires_at"))
        if expires_at and expires_at <= now:
            return None, True
        return normalized, False

    def set_asr_inflight(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return self.normalize_asr_inflight(payload)

    def set_context_asr_inflight(
        self,
        context: dict[str, Any] | None,
        payload: dict[str, Any] | None,
        *,
        key: str,
    ) -> dict[str, Any]:
        return self._set_optional_context_payload(
            context,
            key=key,
            payload=self.set_asr_inflight(payload),
        )

    def normalize_style_reference_pending(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        cleaned: dict[str, Any] = {}
        for key in ("reason", "created_at", "requested_at", "expires_at", "storage_path", "public_url", "public_url_expires_at", "sha256"):
            value = self._normalize_projection_token(payload.get(key))
            if value:
                cleaned[key] = value

        media = payload.get("media")
        if isinstance(media, dict):
            media_payload = self._normalize_style_reference_media(media)
            if media_payload:
                cleaned["media"] = media_payload

        if not cleaned:
            return None
        return StyleReferencePendingState.model_validate(cleaned).model_dump(exclude_none=True)

    def get_style_reference_pending(
        self,
        payload: dict[str, Any] | None,
        *,
        now: datetime,
    ) -> tuple[dict[str, Any] | None, bool]:
        normalized = self.normalize_style_reference_pending(payload)
        if not normalized:
            return None, False
        expires_at = self._parse_iso_datetime(normalized.get("expires_at"))
        if expires_at and expires_at <= now:
            return None, True
        return normalized, False

    def set_style_reference_pending(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        normalized = self.normalize_style_reference_pending(payload)
        if not normalized:
            return None
        return deepcopy(normalized)

    def set_context_style_reference_pending(
        self,
        context: dict[str, Any] | None,
        payload: dict[str, Any] | None,
        *,
        key: str,
    ) -> dict[str, Any]:
        return self._set_optional_context_payload(
            context,
            key=key,
            payload=self.set_style_reference_pending(payload),
        )

    def set_context_memory_profile(
        self,
        context: dict[str, Any] | None,
        payload: dict[str, Any] | None,
        *,
        key: str,
    ) -> dict[str, Any]:
        return self._set_optional_context_payload(
            context,
            key=key,
            payload=self.set_memory_profile(payload),
        )

    def set_context_memory_pending(
        self,
        context: dict[str, Any] | None,
        payload: dict[str, Any] | None,
        *,
        key: str,
    ) -> dict[str, Any]:
        return self._set_optional_context_payload(
            context,
            key=key,
            payload=self.set_memory_pending(payload),
        )

    def build_class_carryover_payload(
        self,
        *,
        class_name: str | None,
        intents: list[str] | None,
        info_sections: list[str] | None,
        message_count: int,
        default_ttl: int,
        allowed_intents: set[str],
        normalize_class_name: Callable[[str], str] | None = None,
    ) -> dict[str, Any] | None:
        raw_class = self._normalize_projection_token(class_name)
        if raw_class is None:
            return None
        normalized_class = (
            normalize_class_name(raw_class)
            if callable(normalize_class_name)
            else raw_class
        )
        normalized_class = self._normalize_projection_token(normalized_class)
        if normalized_class is None:
            return None

        cleaned_intents: list[str] = []
        seen: set[str] = set()
        if isinstance(intents, list):
            for intent in intents:
                if not isinstance(intent, str):
                    continue
                value = intent.strip().casefold()
                if not value or value in seen:
                    continue
                cleaned_intents.append(value)
                seen.add(value)

        cleaned_sections: list[str] = []
        if isinstance(info_sections, list):
            for section in info_sections:
                if not isinstance(section, str):
                    continue
                value = section.strip()
                if not value:
                    continue
                cleaned_sections.append(value)
                derived_intent = _CLASS_CARRYOVER_SECTION_INTENT_MAP.get(value.casefold())
                if derived_intent and derived_intent in allowed_intents and derived_intent not in seen:
                    cleaned_intents.append(derived_intent)
                    seen.add(derived_intent)

        return {
            "class": normalized_class,
            "intents": cleaned_intents,
            "info_sections": cleaned_sections,
            "message_count": self._canonical_int(message_count),
            "ttl": default_ttl,
        }

    def get_class_carryover(
        self,
        payload: dict[str, Any] | None,
        *,
        message_count: int,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None

        class_name = payload.get("class")
        if not isinstance(class_name, str) or not class_name.strip():
            return None
        try:
            last_count = int(payload.get("message_count"))
        except (TypeError, ValueError):
            return None
        ttl = payload.get("ttl")
        try:
            ttl = int(ttl)
        except (TypeError, ValueError):
            return None
        if ttl <= 0:
            return None
        age = message_count - last_count
        if age <= 0 or age > ttl:
            return None
        remaining = max(ttl - age + 1, 0)

        intents = payload.get("intents")
        if isinstance(intents, list):
            cleaned_intents = [intent for intent in intents if isinstance(intent, str) and intent.strip()]
        else:
            cleaned_intents = []

        info_sections = payload.get("info_sections")
        if not isinstance(info_sections, list):
            info_sections = []
        else:
            info_sections = deepcopy(info_sections)

        return {
            "class": class_name.strip(),
            "intents": cleaned_intents,
            "info_sections": info_sections,
            "age": age,
            "ttl": ttl,
            "remaining": remaining,
        }

    def _normalize_class_carryover_payload(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        raw_ttl = self._canonical_int(payload.get("ttl"))
        if raw_ttl <= 0:
            return None
        normalized = self.build_class_carryover_payload(
            class_name=payload.get("class"),
            intents=payload.get("intents") if isinstance(payload.get("intents"), list) else None,
            info_sections=(
                payload.get("info_sections")
                if isinstance(payload.get("info_sections"), list)
                else None
            ),
            message_count=self._canonical_int(payload.get("message_count")),
            default_ttl=raw_ttl,
            allowed_intents={
                self._normalize_projection_token(item)
                for item in (_CLASS_CARRYOVER_SECTION_INTENT_MAP.values())
            }
            | {
                item.strip().casefold()
                for item in (payload.get("intents") or [])
                if isinstance(item, str) and item.strip()
            },
            normalize_class_name=lambda value: value.strip().casefold(),
        )
        if normalized is None:
            return None
        normalized["ttl"] = raw_ttl
        return normalized

    def _build_touched_slice_class_carryover_payload(
        self,
        *,
        execution_meta: dict[str, Any] | None,
        message_count: int,
    ) -> dict[str, Any] | None:
        if not isinstance(execution_meta, dict):
            return None
        family_id = self._normalize_projection_token(execution_meta.get("fact_family_cutover"))
        if family_id != _TOUCHED_SLICE_CLASS_CARRYOVER_FAMILY_ID:
            return None

        raw_info_sections = execution_meta.get("info_sections")
        info_sections = [
            item.strip()
            for item in raw_info_sections
            if isinstance(item, str) and item.strip()
        ] if isinstance(raw_info_sections, list) else []

        emitted_refs: list[str] = []
        raw_fact_refs = execution_meta.get("fact_emitted_refs")
        if isinstance(raw_fact_refs, list):
            for item in raw_fact_refs:
                normalized = self._normalize_projection_token(item)
                if normalized and normalized in _TOUCHED_SLICE_CLASS_CARRYOVER_INTENTS:
                    emitted_refs.append(normalized)
                    existing_intents = {
                        _CLASS_CARRYOVER_SECTION_INTENT_MAP.get(section.strip().casefold())
                        for section in info_sections
                        if isinstance(section, str) and section.strip()
                    }
                    if normalized not in existing_intents and normalized not in info_sections:
                        info_sections.append(normalized)

        if not info_sections and not emitted_refs:
            return None

        return self.build_class_carryover_payload(
            class_name=_TOUCHED_SLICE_CLASS_CARRYOVER_CLASS,
            intents=emitted_refs,
            info_sections=info_sections,
            message_count=message_count,
            default_ttl=_TOUCHED_SLICE_CLASS_CARRYOVER_TTL_MESSAGES,
            allowed_intents=_TOUCHED_SLICE_CLASS_CARRYOVER_INTENTS,
            normalize_class_name=lambda value: value.strip().casefold(),
        )

    def set_canonical_class_carryover(
        self,
        state: dict[str, Any] | None,
        *,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        updated = self.normalize_context_manager_canonical_state(state)
        meta = updated.get("meta")
        meta = deepcopy(meta) if isinstance(meta, dict) else {}
        if isinstance(payload, dict) and payload:
            meta["class_carryover"] = deepcopy(payload)
        else:
            meta.pop("class_carryover", None)
        if meta:
            updated["meta"] = meta
        else:
            updated.pop("meta", None)
        return updated

    def clear_canonical_class_carryover(
        self,
        state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return self.set_canonical_class_carryover(state, payload=None)

    def set_context_manager_canonical_state(
        self,
        manager: dict[str, Any] | None,
        *,
        key: str,
        state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        normalized_state = (
            self.normalize_context_manager_canonical_state(state)
            if isinstance(state, dict)
            else None
        )
        return self._set_optional_manager_payload(
            manager,
            key=key,
            payload=normalized_state,
        )

    def set_context_manager_class_carryover(
        self,
        manager: dict[str, Any] | None,
        *,
        manager_key: str,
        canonical_state_key: str,
        class_name: str | None,
        intents: list[str] | None,
        info_sections: list[str] | None,
        message_count: int,
        default_ttl: int,
        allowed_intents: set[str],
        normalize_class_name: Callable[[str], str] | None = None,
    ) -> dict[str, Any]:
        payload = self.build_class_carryover_payload(
            class_name=class_name,
            intents=intents,
            info_sections=info_sections,
            message_count=message_count,
            default_ttl=default_ttl,
            allowed_intents=allowed_intents,
            normalize_class_name=normalize_class_name,
        )
        updated = self._set_optional_manager_payload(
            manager,
            key=manager_key,
            payload=payload,
        )
        canonical_state = updated.get(canonical_state_key)
        if isinstance(payload, dict):
            return self.set_context_manager_canonical_state(
                updated,
                key=canonical_state_key,
                state=self.set_canonical_class_carryover(
                    canonical_state,
                    payload=payload,
            ),
        )

    def set_context_manager_class_carryover_payload(
        self,
        manager: dict[str, Any] | None,
        *,
        manager_key: str,
        canonical_state_key: str,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        normalized_payload = self._normalize_class_carryover_payload(payload)
        updated = self._set_optional_manager_payload(
            manager,
            key=manager_key,
            payload=normalized_payload,
        )
        canonical_state = self.normalize_context_manager_canonical_state(
            updated.get(canonical_state_key) if isinstance(updated.get(canonical_state_key), dict) else None
        )
        return self.set_context_manager_canonical_state(
            updated,
            key=canonical_state_key,
            state=self.set_canonical_class_carryover(
                canonical_state,
                payload=normalized_payload,
            ),
        )
        if isinstance(canonical_state, dict):
            return self.set_context_manager_canonical_state(
                updated,
                key=canonical_state_key,
                state=self.clear_canonical_class_carryover(canonical_state),
            )
        return updated

    def prune_context_manager_class_carryover(
        self,
        manager: dict[str, Any] | None,
        *,
        manager_key: str,
        canonical_state_key: str,
        message_count: int,
        default_ttl: int,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        updated = dict(manager) if isinstance(manager, dict) else {}
        payload = updated.get(manager_key)
        if not isinstance(payload, dict):
            return updated, None

        class_name = self._normalize_projection_token(payload.get("class"))
        if not class_name:
            updated = self._set_optional_manager_payload(updated, key=manager_key, payload=None)
            canonical_state = updated.get(canonical_state_key)
            if isinstance(canonical_state, dict):
                updated = self.set_context_manager_canonical_state(
                    updated,
                    key=canonical_state_key,
                    state=self.clear_canonical_class_carryover(canonical_state),
                )
            return updated, {"reason": "invalid"}

        try:
            last_count = int(payload.get("message_count"))
        except (TypeError, ValueError):
            updated = self._set_optional_manager_payload(updated, key=manager_key, payload=None)
            canonical_state = updated.get(canonical_state_key)
            if isinstance(canonical_state, dict):
                updated = self.set_context_manager_canonical_state(
                    updated,
                    key=canonical_state_key,
                    state=self.clear_canonical_class_carryover(canonical_state),
                )
            return updated, {"reason": "invalid"}

        ttl = payload.get("ttl", default_ttl)
        try:
            ttl = int(ttl)
        except (TypeError, ValueError):
            ttl = default_ttl
        if ttl <= 0:
            ttl = default_ttl

        age = message_count - last_count
        if age > ttl:
            updated = self._set_optional_manager_payload(updated, key=manager_key, payload=None)
            canonical_state = updated.get(canonical_state_key)
            if isinstance(canonical_state, dict):
                updated = self.set_context_manager_canonical_state(
                    updated,
                    key=canonical_state_key,
                    state=self.clear_canonical_class_carryover(canonical_state),
                )
            return updated, {
                "reason": "expired",
                "age": age,
                "ttl": ttl,
                "class": class_name,
            }
        return updated, None

    def get_canonical_class_carryover(
        self,
        state: dict[str, Any] | None,
        *,
        message_count: int,
    ) -> dict[str, Any] | None:
        if not isinstance(state, dict):
            return None
        meta = state.get("meta")
        if not isinstance(meta, dict):
            return None
        payload = meta.get("class_carryover")
        return self.get_class_carryover(payload, message_count=message_count)

    def build_service_carryover_payload(
        self,
        *,
        service_query: str | None,
        source: str | None,
        score: float | None,
        message_count: int,
        default_ttl: int,
        projection_source: str | None,
        canonical_state_owner: str | None,
    ) -> dict[str, Any] | None:
        normalized_query = self._normalize_projection_token(service_query)
        if not normalized_query:
            return None
        payload: dict[str, Any] = {
            "service_query": normalized_query,
            "service_query_source": self._normalize_projection_token(source) or "unknown",
            "service_query_score": float(score) if isinstance(score, (int, float)) else 0.0,
            "message_count": self._canonical_int(message_count),
            "ttl": default_ttl,
        }
        normalized_projection_source = self._normalize_projection_token(projection_source)
        if normalized_projection_source:
            payload["projection_source"] = normalized_projection_source
        normalized_owner = self._normalize_projection_token(canonical_state_owner)
        if normalized_owner:
            payload["canonical_state_owner"] = normalized_owner
        return payload

    def get_service_carryover(
        self,
        payload: dict[str, Any] | None,
        *,
        message_count: int,
        default_ttl: int,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        service_query = self._normalize_projection_token(payload.get("service_query"))
        if not service_query:
            return None
        try:
            last_count = int(payload.get("message_count"))
        except (TypeError, ValueError):
            return None
        ttl = payload.get("ttl", default_ttl)
        try:
            ttl = int(ttl)
        except (TypeError, ValueError):
            return None
        if ttl <= 0:
            return None
        age = message_count - last_count
        if age <= 0 or age > ttl:
            return None
        remaining = max(ttl - age + 1, 0)
        return {
            "service_query": service_query,
            "service_query_source": payload.get("service_query_source"),
            "service_query_score": payload.get("service_query_score"),
            "age": age,
            "ttl": ttl,
            "remaining": remaining,
            "projection_source": payload.get("projection_source"),
            "canonical_state_owner": payload.get("canonical_state_owner"),
        }

    def set_context_manager_service_carryover(
        self,
        manager: dict[str, Any] | None,
        *,
        manager_key: str,
        canonical_state_key: str,
        referent_key: str,
        service_query: str | None,
        source: str | None,
        score: float | None,
        message_count: int,
        default_ttl: int,
        projection_source: str | None,
        canonical_state_owner: str | None,
    ) -> dict[str, Any]:
        score_value = float(score) if isinstance(score, (int, float)) else 0.0
        canonical_state = self.set_canonical_referent(
            self.normalize_context_manager_canonical_state(
                manager.get(canonical_state_key) if isinstance(manager, dict) else None
            ),
            referent_key=referent_key,
            value=service_query,
            message_count=message_count,
            source=source or "unknown",
            score=score_value,
            default_ttl=default_ttl,
        )
        updated = self.set_context_manager_canonical_state(
            manager,
            key=canonical_state_key,
            state=canonical_state,
        )
        payload = self.build_service_carryover_payload(
            service_query=service_query,
            source=source,
            score=score_value,
            message_count=message_count,
            default_ttl=default_ttl,
            projection_source=projection_source,
            canonical_state_owner=canonical_state_owner,
        )
        return self._set_optional_manager_payload(
            updated,
            key=manager_key,
            payload=payload,
        )

    def prune_context_manager_service_carryover(
        self,
        manager: dict[str, Any] | None,
        *,
        manager_key: str,
        canonical_state_key: str,
        referent_key: str,
        message_count: int,
        default_ttl: int,
        projection_source: str,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        canonical_state, canonical_event = self.prune_canonical_referent(
            self.normalize_context_manager_canonical_state(
                manager.get(canonical_state_key) if isinstance(manager, dict) else None
            ),
            referent_key=referent_key,
            message_count=message_count,
            projection_source=projection_source,
        )
        updated = self.set_context_manager_canonical_state(
            manager,
            key=canonical_state_key,
            state=canonical_state,
        )
        payload = updated.get(manager_key)
        if not isinstance(payload, dict):
            return updated, canonical_event

        service_query = self._normalize_projection_token(payload.get("service_query"))
        if not service_query:
            updated = self._set_optional_manager_payload(updated, key=manager_key, payload=None)
            return updated, canonical_event or {"reason": "invalid"}

        try:
            last_count = int(payload.get("message_count"))
        except (TypeError, ValueError):
            updated = self._set_optional_manager_payload(updated, key=manager_key, payload=None)
            return updated, canonical_event or {"reason": "invalid"}

        ttl = payload.get("ttl", default_ttl)
        try:
            ttl = int(ttl)
        except (TypeError, ValueError):
            ttl = default_ttl
        if ttl <= 0:
            ttl = default_ttl

        age = message_count - last_count
        if age > ttl:
            updated = self._set_optional_manager_payload(updated, key=manager_key, payload=None)
            return updated, canonical_event or {
                "reason": "expired",
                "age": age,
                "ttl": ttl,
                "service_query": service_query,
            }
        return updated, canonical_event

    def set_canonical_consult_state(
        self,
        state: dict[str, Any] | None,
        *,
        topic: str | None,
        question: str | None,
        questions: list[str] | None,
        message_count: int,
        default_ttl: int,
    ) -> dict[str, Any]:
        updated = self.normalize_context_manager_canonical_state(state)
        normalized_topic = self._normalize_projection_token(topic)
        normalized_question = self._normalize_projection_token(question)
        cleaned_questions = self.normalize_consult_questions(questions)
        if not normalized_topic and not normalized_question and not cleaned_questions:
            updated.pop("consult_state", None)
            return updated
        updated["consult_state"] = {
            "topic": normalized_topic,
            "question": normalized_question,
            "questions": cleaned_questions,
            "message_count": self._canonical_int(message_count),
            "ttl": default_ttl,
        }
        return updated

    def get_canonical_consult_state(
        self,
        state: dict[str, Any] | None,
        *,
        message_count: int,
    ) -> dict[str, Any] | None:
        normalized_state = self.normalize_context_manager_canonical_state(state)
        consult_state = normalized_state.get("consult_state")
        if not isinstance(consult_state, dict):
            return None
        ttl = consult_state.get("ttl")
        ttl_value = ttl if isinstance(ttl, int) and ttl > 0 else None
        age = max(self._canonical_int(message_count) - self._canonical_int(consult_state.get("message_count")), 0)
        if ttl_value is not None and age > ttl_value:
            return None
        result: dict[str, Any] = {
            "age": max(age, 1),
            "ttl": ttl_value,
            "remaining": max((ttl_value or 0) - age + 1, 0) if ttl_value is not None else None,
            "projection_source": "canonical_dialog_state",
            "canonical_state_owner": normalized_state.get("owner_id") or _CANONICAL_DIALOG_STATE_OWNER,
        }
        topic = self._normalize_projection_token(consult_state.get("topic"))
        if topic:
            result["topic"] = topic
        question = self._normalize_projection_token(consult_state.get("question"))
        if question:
            result["question"] = question
        questions = consult_state.get("questions")
        cleaned_questions = self.normalize_consult_questions(questions)
        if cleaned_questions:
            result["questions"] = cleaned_questions
        if "topic" not in result and "question" not in result and "questions" not in result:
            return None
        return result

    def prune_canonical_consult_state(
        self,
        state: dict[str, Any] | None,
        *,
        message_count: int,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        normalized_state = self.normalize_context_manager_canonical_state(state)
        consult_state = normalized_state.get("consult_state")
        if not isinstance(consult_state, dict):
            return normalized_state, None
        ttl = consult_state.get("ttl")
        if not isinstance(ttl, int) or ttl <= 0:
            return normalized_state, None
        age = max(self._canonical_int(message_count) - self._canonical_int(consult_state.get("message_count")), 0)
        if age <= ttl:
            return normalized_state, None
        normalized_state.pop("consult_state", None)
        return normalized_state, {
            "reason": "expired",
            "age": age,
            "ttl": ttl,
            "projection_source": "canonical_dialog_state",
            "canonical_state_owner": normalized_state.get("owner_id") or _CANONICAL_DIALOG_STATE_OWNER,
        }

    def build_consult_context_payload(
        self,
        *,
        topic: str | None,
        question: str | None,
        questions: list[str] | None,
        message_count: int,
        default_ttl: int,
        projection_source: str | None,
        canonical_state_owner: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "questions": self.normalize_consult_questions(questions),
            "topic": self._normalize_projection_token(topic),
            "question": self._normalize_projection_token(question),
            "message_count": self._canonical_int(message_count),
            "ttl": default_ttl,
        }
        normalized_projection_source = self._normalize_projection_token(projection_source)
        if normalized_projection_source:
            payload["projection_source"] = normalized_projection_source
        normalized_owner = self._normalize_projection_token(canonical_state_owner)
        if normalized_owner:
            payload["canonical_state_owner"] = normalized_owner
        return payload

    def get_consult_context(
        self,
        payload: dict[str, Any] | None,
        *,
        message_count: int,
        default_ttl: int,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        try:
            last_count = int(payload.get("message_count"))
        except (TypeError, ValueError):
            return None
        ttl = payload.get("ttl", default_ttl)
        try:
            ttl = int(ttl)
        except (TypeError, ValueError):
            return None
        if ttl <= 0:
            return None
        age = message_count - last_count
        if age <= 0 or age > ttl:
            return None
        remaining = max(ttl - age + 1, 0)
        result: dict[str, Any] = {
            "age": age,
            "ttl": ttl,
            "remaining": remaining,
            "projection_source": payload.get("projection_source"),
            "canonical_state_owner": payload.get("canonical_state_owner"),
        }
        topic = self._normalize_projection_token(payload.get("topic"))
        if topic:
            result["topic"] = topic
        question = self._normalize_projection_token(payload.get("question"))
        if question:
            result["question"] = question
        questions = self.normalize_consult_questions(payload.get("questions"))
        if questions:
            result["questions"] = questions
        if "topic" not in result and "question" not in result and "questions" not in result:
            return None
        return result

    def set_context_manager_consult_context(
        self,
        manager: dict[str, Any] | None,
        *,
        manager_key: str,
        canonical_state_key: str,
        topic: str | None,
        question: str | None,
        questions: list[str] | None,
        message_count: int,
        default_ttl: int,
        projection_source: str | None,
        canonical_state_owner: str | None,
    ) -> dict[str, Any]:
        canonical_state = self.set_canonical_consult_state(
            self.normalize_context_manager_canonical_state(
                manager.get(canonical_state_key) if isinstance(manager, dict) else None
            ),
            topic=topic,
            question=question,
            questions=questions,
            message_count=message_count,
            default_ttl=default_ttl,
        )
        updated = self.set_context_manager_canonical_state(
            manager,
            key=canonical_state_key,
            state=canonical_state,
        )
        payload = self.build_consult_context_payload(
            topic=topic,
            question=question,
            questions=questions,
            message_count=message_count,
            default_ttl=default_ttl,
            projection_source=projection_source,
            canonical_state_owner=canonical_state_owner,
        )
        return self._set_optional_manager_payload(
            updated,
            key=manager_key,
            payload=payload,
        )

    def prune_context_manager_consult_context(
        self,
        manager: dict[str, Any] | None,
        *,
        manager_key: str,
        canonical_state_key: str,
        message_count: int,
        default_ttl: int,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        canonical_state, canonical_event = self.prune_canonical_consult_state(
            self.normalize_context_manager_canonical_state(
                manager.get(canonical_state_key) if isinstance(manager, dict) else None
            ),
            message_count=message_count,
        )
        updated = self.set_context_manager_canonical_state(
            manager,
            key=canonical_state_key,
            state=canonical_state,
        )
        payload = updated.get(manager_key)
        if not isinstance(payload, dict):
            return updated, canonical_event

        try:
            last_count = int(payload.get("message_count"))
        except (TypeError, ValueError):
            updated = self._set_optional_manager_payload(updated, key=manager_key, payload=None)
            return updated, canonical_event or {"reason": "invalid"}

        ttl = payload.get("ttl", default_ttl)
        try:
            ttl = int(ttl)
        except (TypeError, ValueError):
            ttl = default_ttl
        if ttl <= 0:
            ttl = default_ttl

        age = message_count - last_count
        if age > ttl:
            updated = self._set_optional_manager_payload(updated, key=manager_key, payload=None)
            return updated, canonical_event or {
                "reason": "expired",
                "age": age,
                "ttl": ttl,
            }
        return updated, canonical_event

    def clear_context_manager_carryover_family(
        self,
        manager: dict[str, Any] | None,
        *,
        class_manager_key: str,
        service_manager_key: str,
        consult_manager_key: str,
        canonical_state_key: str,
        referent_key: str,
    ) -> dict[str, Any]:
        updated = self._set_optional_manager_payload(
            manager,
            key=class_manager_key,
            payload=None,
        )
        updated = self._set_optional_manager_payload(
            updated,
            key=service_manager_key,
            payload=None,
        )
        updated = self._set_optional_manager_payload(
            updated,
            key=consult_manager_key,
            payload=None,
        )
        canonical_state = self.clear_canonical_class_carryover(
            self.normalize_context_manager_canonical_state(
                updated.get(canonical_state_key) if isinstance(updated, dict) else None
            )
        )
        canonical_state = self.set_canonical_referent(
            canonical_state,
            referent_key=referent_key,
            value=None,
            message_count=0,
        )
        canonical_state = self.set_canonical_consult_state(
            canonical_state,
            topic=None,
            question=None,
            questions=None,
            message_count=0,
            default_ttl=1,
        )
        return self.set_context_manager_canonical_state(
            updated,
            key=canonical_state_key,
            state=canonical_state,
        )

    def normalize_intent_queue(
        self,
        queue: Any,
    ) -> list[str]:
        if not isinstance(queue, list):
            return []
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in queue:
            if not isinstance(item, str):
                continue
            value = item.strip().casefold()
            if not value or value in seen:
                continue
            cleaned.append(value)
            seen.add(value)
        return cleaned

    def get_intent_queue(
        self,
        context: dict[str, Any] | None,
    ) -> list[str]:
        if not isinstance(context, dict):
            return []
        return self.normalize_intent_queue(context.get("intent_queue"))

    def set_intent_queue(
        self,
        context: dict[str, Any] | None,
        *,
        queue: Any,
    ) -> dict[str, Any]:
        updated = deepcopy(context) if isinstance(context, dict) else {}
        cleaned = self.normalize_intent_queue(queue)
        if cleaned:
            updated["intent_queue"] = cleaned
        else:
            updated.pop("intent_queue", None)
        return updated

    def build_compact_summary_text(
        self,
        *,
        booking: dict[str, Any] | None,
        refusal_flags: dict[str, Any] | None,
        language: Any,
        is_refusal_flag_active: Callable[[dict[str, Any], str], bool],
    ) -> str:
        booking_payload = booking if isinstance(booking, dict) else {}
        flags_payload = refusal_flags if isinstance(refusal_flags, dict) else {}

        parts: list[str] = []
        service = self._normalize_projection_token(booking_payload.get("service"))
        if service:
            parts.append(f"Услуга: {service}")
        datetime_pref = self._normalize_projection_token(booking_payload.get("datetime"))
        if datetime_pref:
            parts.append(f"Время: {datetime_pref}")
        name = self._normalize_projection_token(booking_payload.get("name"))
        if name:
            parts.append(f"Имя: {name}")
        if not name and callable(is_refusal_flag_active) and is_refusal_flag_active(flags_payload, "name"):
            parts.append("Имя: отказ")
        if callable(is_refusal_flag_active) and is_refusal_flag_active(flags_payload, "phone"):
            parts.append("Телефон: отказ")
        if isinstance(language, str) and language and language != "unknown":
            parts.append(f"Язык: {language}")
        return "; ".join(parts).strip()

    def set_compact_summary(
        self,
        manager: dict[str, Any] | None,
        *,
        summary_text: str,
        reason: Any,
        now: datetime,
    ) -> dict[str, Any]:
        updated = deepcopy(manager) if isinstance(manager, dict) else {}
        updated["compact_summary"] = {
            "text": summary_text,
            "updated_at": now.isoformat(),
            "reason": reason,
        }
        return updated

    def get_clarify_attempt_state(
        self,
        manager: dict[str, Any] | None,
        *,
        intent: Any,
    ) -> tuple[int, str | None]:
        if not isinstance(manager, dict):
            return 0, None
        attempts = manager.get("clarify_attempts")
        if not isinstance(attempts, dict):
            return 0, None
        payload = attempts.get(intent)
        if not isinstance(payload, dict):
            return 0, None
        count = self._canonical_int(payload.get("count"))
        last_at = payload.get("last_at")
        return count, last_at if isinstance(last_at, str) else None

    def set_clarify_attempt_state(
        self,
        manager: dict[str, Any] | None,
        *,
        intent: Any,
        count: Any,
        now: datetime,
    ) -> dict[str, Any]:
        updated = deepcopy(manager) if isinstance(manager, dict) else {}
        attempts = updated.get("clarify_attempts")
        attempts_map = deepcopy(attempts) if isinstance(attempts, dict) else {}
        attempts_map[intent] = {
            "count": self._canonical_int(count),
            "last_at": now.isoformat(),
        }
        updated["clarify_attempts"] = attempts_map
        return updated

    def get_low_confidence_retry_count(
        self,
        context: dict[str, Any] | None,
    ) -> int:
        if not isinstance(context, dict):
            return 0
        return self._canonical_int(context.get("low_confidence_retry_count"))

    def set_low_confidence_retry_count(
        self,
        context: dict[str, Any] | None,
        *,
        count: Any,
    ) -> dict[str, Any]:
        updated = deepcopy(context) if isinstance(context, dict) else {}
        updated["low_confidence_retry_count"] = self._canonical_int(count)
        return updated

    def reset_low_confidence_retry_count(
        self,
        context: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], bool]:
        updated = deepcopy(context) if isinstance(context, dict) else {}
        raw_value = updated.get("low_confidence_retry_count")
        if not raw_value:
            return updated, False
        updated["low_confidence_retry_count"] = 0
        return updated, True

    def normalize_context_manager_canonical_state(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        state = deepcopy(payload) if isinstance(payload, dict) else {}
        state["owner_id"] = self._normalize_projection_token(state.get("owner_id")) or _CANONICAL_DIALOG_STATE_OWNER
        state["version"] = self._normalize_projection_token(state.get("version")) or _CANONICAL_DIALOG_STATE_VERSION
        state["current_referents"] = self._normalize_canonical_referents(state.get("current_referents"))

        pending_question_contract = self.normalize_canonical_pending_question_contract(
            state.get("pending_question_contract")
        )
        if pending_question_contract:
            state["pending_question_contract"] = pending_question_contract
        else:
            state.pop("pending_question_contract", None)

        interaction_state = self.normalize_canonical_interaction_state(state.get("interaction_state"))
        if interaction_state:
            state["interaction_state"] = interaction_state
        else:
            state.pop("interaction_state", None)

        consult_state = self._normalize_canonical_consult_state(state.get("consult_state"))
        if consult_state:
            state["consult_state"] = consult_state
        else:
            state.pop("consult_state", None)
        return state

    def build_canonical_pending_question_contract(
        self,
        *,
        expected_reply_type: str | None,
        reason: str | None,
        message_count: int,
        value: str | None = None,
    ) -> dict[str, Any] | None:
        normalized_expected_reply_type = self._normalize_projection_token(expected_reply_type)
        if not normalized_expected_reply_type:
            return None

        slot = _CANONICAL_EXPECTED_REPLY_SLOT_BY_TYPE.get(normalized_expected_reply_type)
        return self.project_pending_question_contract(
            {
                "expected_reply_type": normalized_expected_reply_type,
                "reason": self._normalize_projection_token(reason),
                "next_question": slot,
                "open_questions": [slot] if slot else [],
            }
        )

    def set_canonical_pending_question_contract(
        self,
        state: dict[str, Any] | None,
        *,
        expected_reply_type: str | None,
        reason: str | None,
        message_count: int,
        value: str | None = None,
    ) -> dict[str, Any]:
        updated = self.normalize_context_manager_canonical_state(state)
        payload = self.build_canonical_pending_question_contract(
            expected_reply_type=expected_reply_type,
            reason=reason,
            message_count=message_count,
            value=value,
        )
        if payload:
            updated["pending_question_contract"] = payload
        else:
            updated.pop("pending_question_contract", None)
        return updated

    def normalize_canonical_pending_question_contract(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        return self.project_pending_question_contract(payload)

    def set_canonical_interaction_state(
        self,
        state: dict[str, Any] | None,
        *,
        resume_slot: str | None,
        interaction_target: str | None,
        interaction_relation: str | None,
        interaction_owner: str | None,
        grounded_referents: dict[str, str] | None,
        confirmation_state: dict[str, Any] | None,
        degrade_reason: str | None,
    ) -> dict[str, Any]:
        updated = self.normalize_context_manager_canonical_state(state)
        payload = self.build_canonical_interaction_state(
            resume_slot=resume_slot,
            interaction_target=interaction_target,
            interaction_relation=interaction_relation,
            interaction_owner=interaction_owner,
            grounded_referents=grounded_referents,
            confirmation_state=confirmation_state,
            degrade_reason=degrade_reason,
        )
        if payload:
            updated["interaction_state"] = payload
        else:
            updated.pop("interaction_state", None)
        return updated

    def sync_canonical_question_contract_state(
        self,
        state: dict[str, Any] | None,
        *,
        expected_reply_type: str | None,
        expected_reply_reason: str | None,
        message_count: int,
        interaction_target: str | None,
        interaction_relation: str | None,
        interaction_owner: str | None,
        grounded_referents: dict[str, str] | None,
        confirmation_state: dict[str, Any] | None,
        degrade_reason: str | None,
    ) -> dict[str, Any]:
        updated = self.set_canonical_pending_question_contract(
            state,
            expected_reply_type=expected_reply_type,
            reason=expected_reply_reason,
            message_count=message_count,
        )
        normalized = self.normalize_context_manager_canonical_state(updated)
        pending_question_contract = normalized.get("pending_question_contract")
        if isinstance(pending_question_contract, dict):
            resume_slot = self._normalize_projection_token(pending_question_contract.get("next_question"))
            question_reason = self._normalize_projection_token(pending_question_contract.get("reason"))
        else:
            normalized_expected_reply_type = self._normalize_projection_token(expected_reply_type)
            resume_slot = _CANONICAL_EXPECTED_REPLY_SLOT_BY_TYPE.get(normalized_expected_reply_type)
            question_reason = self._normalize_projection_token(expected_reply_reason)
        existing_interaction = (
            normalized.get("interaction_state")
            if isinstance(normalized.get("interaction_state"), dict)
            else {}
        )
        canonical_interaction_target = (
            interaction_target
            if interaction_target is not None
            else existing_interaction.get("interaction_target")
        )
        canonical_interaction_relation = (
            interaction_relation
            if interaction_relation is not None
            else existing_interaction.get("interaction_relation")
        )
        canonical_interaction_owner = self.build_interaction_owner(
            explicit_owner=(
                interaction_owner
                if interaction_owner is not None
                else existing_interaction.get("interaction_owner")
            ),
            interaction_relation=canonical_interaction_relation,
            question_reason=question_reason,
        )
        canonical_degrade_reason = (
            degrade_reason
            if degrade_reason is not None
            else existing_interaction.get("degrade_reason")
        )
        return self.set_canonical_interaction_state(
            updated,
            resume_slot=resume_slot,
            interaction_target=canonical_interaction_target,
            interaction_relation=canonical_interaction_relation,
            interaction_owner=canonical_interaction_owner,
            grounded_referents=grounded_referents,
            confirmation_state=confirmation_state,
            degrade_reason=canonical_degrade_reason,
        )

    def build_canonical_interaction_state(
        self,
        *,
        resume_slot: str | None,
        interaction_target: str | None,
        interaction_relation: str | None,
        interaction_owner: str | None,
        grounded_referents: dict[str, str] | None,
        confirmation_state: dict[str, Any] | None,
        degrade_reason: str | None,
    ) -> dict[str, Any] | None:
        resume_slot_token = self._normalize_projection_token(resume_slot)
        if resume_slot_token not in _CANONICAL_PENDING_SLOTS:
            return None

        payload: dict[str, Any] = {"resume_slot": resume_slot_token}
        interaction_target_token = self._canonical_interaction_token(
            interaction_target,
            allowed=_CANONICAL_INTERACTION_TARGET_VALUES,
        )
        if interaction_target_token:
            payload["interaction_target"] = interaction_target_token
        interaction_relation_token = self._canonical_interaction_token(
            interaction_relation,
            allowed=_CANONICAL_INTERACTION_RELATION_VALUES,
        )
        if interaction_relation_token:
            payload["interaction_relation"] = interaction_relation_token
        interaction_owner_token = self._canonical_interaction_owner(interaction_owner)
        if interaction_owner_token:
            payload["interaction_owner"] = interaction_owner_token
        grounded_referents_payload = self._canonical_grounded_referents(grounded_referents)
        if grounded_referents_payload:
            payload["grounded_referents"] = grounded_referents_payload
        confirmation_state_payload = self._canonical_confirmation_state(confirmation_state)
        if confirmation_state_payload:
            payload["confirmation_state"] = confirmation_state_payload
        degrade_reason_token = self._canonical_degrade_reason(degrade_reason)
        if degrade_reason_token:
            payload["degrade_reason"] = degrade_reason_token
        return payload

    def normalize_canonical_interaction_state(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        return self.build_canonical_interaction_state(
            resume_slot=payload.get("resume_slot"),
            interaction_target=payload.get("interaction_target"),
            interaction_relation=payload.get("interaction_relation"),
            interaction_owner=payload.get("interaction_owner"),
            grounded_referents=payload.get("grounded_referents"),
            confirmation_state=payload.get("confirmation_state"),
            degrade_reason=payload.get("degrade_reason"),
        )

    def build_interaction_owner(
        self,
        *,
        explicit_owner: str | None,
        interaction_relation: str | None,
        question_reason: str | None,
    ) -> str | None:
        owner = self._canonical_interaction_owner(explicit_owner)
        if owner:
            return owner
        relation = self._canonical_interaction_token(
            interaction_relation,
            allowed=_CANONICAL_INTERACTION_RELATION_VALUES,
        )
        if relation:
            return f"llm_policy_core:{relation}"[:80]
        reason = self._normalize_projection_token(question_reason)
        if reason:
            return f"question_contract:{reason}"[:80]
        return None

    def project_session_memory_interaction_state(
        self,
        interaction_state: dict[str, Any] | None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        if interaction_state is None:
            return None, None
        if not isinstance(interaction_state, dict):
            return None, "interaction_state_type"

        cleaned: dict[str, Any] = {}
        resume_slot = interaction_state.get("resume_slot")
        if isinstance(resume_slot, str) and resume_slot.strip():
            resume_token = resume_slot.strip().casefold()
            if resume_token in _SESSION_MEMORY_INTERACTION_RESUME_SLOTS:
                cleaned["resume_slot"] = resume_token

        interaction_target = interaction_state.get("interaction_target")
        if isinstance(interaction_target, str) and interaction_target.strip():
            target_token = interaction_target.strip().casefold()
            if target_token in _SESSION_MEMORY_INTERACTION_TARGETS:
                cleaned["interaction_target"] = target_token

        interaction_relation = interaction_state.get("interaction_relation")
        if isinstance(interaction_relation, str) and interaction_relation.strip():
            relation_token = interaction_relation.strip().casefold()
            if relation_token in _SESSION_MEMORY_INTERACTION_RELATIONS:
                cleaned["interaction_relation"] = relation_token

        interaction_owner = interaction_state.get("interaction_owner")
        if isinstance(interaction_owner, str) and interaction_owner.strip():
            cleaned["interaction_owner"] = " ".join(interaction_owner.split())[:80]

        grounded_referents = interaction_state.get("grounded_referents")
        if isinstance(grounded_referents, dict):
            cleaned_referents: dict[str, str] = {}
            for referent_key in _SESSION_MEMORY_INTERACTION_REFERENT_KEYS:
                referent_value = grounded_referents.get(referent_key)
                if isinstance(referent_value, str) and referent_value.strip():
                    cleaned_referents[referent_key] = " ".join(referent_value.split())[:120]
            if cleaned_referents:
                cleaned["grounded_referents"] = cleaned_referents

        confirmation_state = interaction_state.get("confirmation_state")
        if isinstance(confirmation_state, dict):
            cleaned_confirmation: dict[str, Any] = {}
            required = confirmation_state.get("required")
            if isinstance(required, bool):
                cleaned_confirmation["required"] = required
            slot = confirmation_state.get("slot")
            if isinstance(slot, str) and slot.strip():
                slot_token = slot.strip().casefold()
                if slot_token in _SESSION_MEMORY_INTERACTION_RESUME_SLOTS:
                    cleaned_confirmation["slot"] = slot_token
            value = confirmation_state.get("value")
            if isinstance(value, str) and value.strip():
                cleaned_confirmation["value"] = " ".join(value.split())[:120]
            source = confirmation_state.get("source")
            if isinstance(source, str) and source.strip():
                cleaned_confirmation["source"] = " ".join(source.split())[:80]
            if cleaned_confirmation:
                cleaned["confirmation_state"] = cleaned_confirmation

        degrade_reason = interaction_state.get("degrade_reason")
        if isinstance(degrade_reason, str) and degrade_reason.strip():
            cleaned["degrade_reason"] = " ".join(degrade_reason.split())[:120]

        if "resume_slot" not in cleaned:
            return None, "interaction_state_resume_slot"

        try:
            projection = InteractionStateContract(**cleaned).model_dump(exclude_none=True)
        except ValidationError:
            return None, "interaction_state_contract"
        return projection, None

    def _grounded_referents_from_canonical_state(
        self,
        state: dict[str, Any] | None,
    ) -> dict[str, str]:
        referents = state.get("current_referents") if isinstance(state, dict) else None
        if not isinstance(referents, dict):
            return {}

        grounded: dict[str, str] = {}
        key_map = {
            "service": "service",
            "master": "specialist",
            "branch": "branch",
            "booking_ref": "booking_ref",
        }
        for canonical_key, target_key in key_map.items():
            payload = referents.get(canonical_key)
            if not isinstance(payload, dict):
                continue
            value = self._normalize_projection_token(payload.get("value"))
            if value:
                grounded[target_key] = value[:120]
        return grounded

    def _booking_confirmation_state(
        self,
        booking_state: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        confirmation = booking_state.get("confirmation") if isinstance(booking_state, dict) else None
        if not isinstance(confirmation, dict):
            return None

        cleaned: dict[str, Any] = {"required": True}
        slot = self._normalize_projection_token(confirmation.get("slot"))
        if slot in _SESSION_MEMORY_INTERACTION_RESUME_SLOTS:
            cleaned["slot"] = slot
        value = self._normalize_projection_token(confirmation.get("value"))
        if value:
            cleaned["value"] = value[:120]
        source = self._normalize_projection_token(confirmation.get("source"))
        if source:
            cleaned["source"] = source[:80]
        return cleaned

    @staticmethod
    def _normalize_projection_token(value: str | None) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _canonical_int(value: Any, *, default: int = 0) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return default
        return max(normalized, 0)

    def _canonical_interaction_token(self, value: Any, *, allowed: set[str]) -> str | None:
        token = self._normalize_projection_token(value)
        if token is None:
            return None
        normalized = token.casefold()
        if normalized not in allowed:
            return None
        return normalized

    def _canonical_interaction_owner(self, value: Any) -> str | None:
        owner = self._normalize_projection_token(value)
        if owner is None:
            return None
        return owner[:80]

    def _canonical_degrade_reason(self, value: Any) -> str | None:
        reason = self._normalize_projection_token(value)
        if reason is None:
            return None
        return reason[:120]

    def _canonical_grounded_referents(self, value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        cleaned: dict[str, str] = {}
        for referent_key in _CANONICAL_INTERACTION_REFERENT_KEYS:
            referent_value = self._normalize_projection_token(value.get(referent_key))
            if referent_value:
                cleaned[referent_key] = referent_value[:120]
        return cleaned

    def _canonical_confirmation_state(self, value: Any) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            return None
        cleaned: dict[str, Any] = {}
        required = value.get("required")
        if isinstance(required, bool):
            cleaned["required"] = required
        slot = self._normalize_projection_token(value.get("slot"))
        if slot in _CANONICAL_PENDING_SLOTS:
            cleaned["slot"] = slot
        slot_value = self._normalize_projection_token(value.get("value"))
        if slot_value:
            cleaned["value"] = slot_value[:120]
        source = self._normalize_projection_token(value.get("source"))
        if source:
            cleaned["source"] = source[:80]
        return cleaned or None

    def _normalize_canonical_referents(self, value: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(value, dict):
            return {}
        cleaned_referents: dict[str, dict[str, Any]] = {}
        for referent_key, raw_payload in value.items():
            if referent_key not in _CANONICAL_REFERENT_KEYS or not isinstance(raw_payload, dict):
                continue
            referent_value = self._normalize_projection_token(raw_payload.get("value"))
            if not referent_value:
                continue
            item: dict[str, Any] = {
                "value": referent_value,
                "message_count": self._canonical_int(raw_payload.get("message_count")),
            }
            source = self._normalize_projection_token(raw_payload.get("source"))
            if source:
                item["source"] = source
            score = raw_payload.get("score")
            if isinstance(score, (int, float)):
                item["score"] = float(score)
            ttl = raw_payload.get("ttl")
            if isinstance(ttl, int) and ttl > 0:
                item["ttl"] = ttl
            cleaned_referents[referent_key] = item
        return cleaned_referents

    def _normalize_canonical_consult_state(self, value: Any) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            return None
        cleaned_consult: dict[str, Any] = {
            "message_count": self._canonical_int(value.get("message_count"))
        }
        topic = self._normalize_projection_token(value.get("topic"))
        if topic:
            cleaned_consult["topic"] = topic
        question = self._normalize_projection_token(value.get("question"))
        if question:
            cleaned_consult["question"] = question
        raw_questions = value.get("questions")
        if isinstance(raw_questions, list):
            questions = [self._normalize_projection_token(item) for item in raw_questions]
            cleaned_questions = [item for item in questions if item]
            if cleaned_questions:
                cleaned_consult["questions"] = cleaned_questions
        ttl = value.get("ttl")
        if isinstance(ttl, int) and ttl > 0:
            cleaned_consult["ttl"] = ttl
        if len(cleaned_consult) > 1:
            return cleaned_consult
        return None

    def set_canonical_referent(
        self,
        state: dict[str, Any] | None,
        *,
        referent_key: str,
        value: str | None,
        message_count: int,
        source: str | None = None,
        score: float | None = None,
        ttl: int | None = None,
        default_ttl: int | None = None,
    ) -> dict[str, Any]:
        normalized_state = self.normalize_context_manager_canonical_state(state)
        if referent_key not in _CANONICAL_REFERENT_KEYS:
            return normalized_state

        referents = dict(normalized_state.get("current_referents") or {})
        referent_value = self._normalize_projection_token(value)
        if not referent_value:
            referents.pop(referent_key, None)
        else:
            payload: dict[str, Any] = {
                "value": referent_value,
                "message_count": self._canonical_int(message_count),
            }
            referent_source = self._normalize_projection_token(source)
            if referent_source:
                payload["source"] = referent_source
            if isinstance(score, (int, float)):
                payload["score"] = float(score)
            referent_ttl = ttl if isinstance(ttl, int) and ttl > 0 else default_ttl
            if isinstance(referent_ttl, int) and referent_ttl > 0:
                payload["ttl"] = referent_ttl
            referents[referent_key] = payload

        normalized_state["current_referents"] = referents
        return normalized_state

    def project_canonical_referent(
        self,
        state: dict[str, Any] | None,
        *,
        referent_key: str,
        message_count: int,
        projection_source: str,
    ) -> dict[str, Any] | None:
        normalized_state = self.normalize_context_manager_canonical_state(state)
        referents = normalized_state.get("current_referents")
        payload = referents.get(referent_key) if isinstance(referents, dict) else None
        if not isinstance(payload, dict):
            return None

        referent_value = self._normalize_projection_token(payload.get("value"))
        if not referent_value:
            return None
        ttl = payload.get("ttl")
        ttl_value = ttl if isinstance(ttl, int) and ttl > 0 else None
        age = max(self._canonical_int(message_count) - self._canonical_int(payload.get("message_count")), 0)
        if ttl_value is not None and age > ttl_value:
            return None
        return {
            "value": referent_value,
            "source": self._normalize_projection_token(payload.get("source")),
            "score": payload.get("score") if isinstance(payload.get("score"), (int, float)) else None,
            "age": max(age, 1),
            "ttl": ttl_value,
            "remaining": max((ttl_value or 0) - age + 1, 0) if ttl_value is not None else None,
            "projection_source": projection_source,
            "canonical_state_owner": normalized_state.get("owner_id") or _CANONICAL_DIALOG_STATE_OWNER,
        }

    def prune_canonical_referent(
        self,
        state: dict[str, Any] | None,
        *,
        referent_key: str,
        message_count: int,
        projection_source: str,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        normalized_state = self.normalize_context_manager_canonical_state(state)
        referents = dict(normalized_state.get("current_referents") or {})
        payload = referents.get(referent_key)
        if not isinstance(payload, dict):
            return normalized_state, None
        ttl = payload.get("ttl")
        if not isinstance(ttl, int) or ttl <= 0:
            return normalized_state, None
        age = max(self._canonical_int(message_count) - self._canonical_int(payload.get("message_count")), 0)
        if age <= ttl:
            return normalized_state, None

        referent_value = self._normalize_projection_token(payload.get("value"))
        referents.pop(referent_key, None)
        normalized_state["current_referents"] = referents
        return normalized_state, {
            "reason": "expired",
            "age": age,
            "ttl": ttl,
            "value": referent_value,
            "projection_source": projection_source,
            "canonical_state_owner": normalized_state.get("owner_id") or _CANONICAL_DIALOG_STATE_OWNER,
        }

    def _normalize_style_reference_media(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        cleaned: dict[str, Any] = {}
        for key in ("media_type", "raw_type", "mime", "url", "file_name", "caption"):
            value = self._normalize_projection_token(payload.get(key))
            if value:
                cleaned[key] = value
        for key in ("size_bytes", "duration_seconds"):
            value = payload.get(key)
            if isinstance(value, int) and value >= 0:
                cleaned[key] = value
        if isinstance(payload.get("ptt"), bool):
            cleaned["ptt"] = payload["ptt"]
        if not cleaned:
            return None
        return StyleReferenceMediaState.model_validate(cleaned).model_dump(exclude_none=True)

    def normalize_consult_questions(
        self,
        questions: Any,
        *,
        transform: Callable[[str], str] | None = None,
    ) -> list[str]:
        if not isinstance(questions, list):
            return []
        cleaned_questions: list[str] = []
        for item in questions:
            if not isinstance(item, str):
                continue
            value = self._normalize_projection_token(item)
            if not value:
                continue
            if callable(transform):
                value = self._normalize_projection_token(transform(value)) or value
            cleaned_questions.append(value)
        return cleaned_questions

    @staticmethod
    def _parse_iso_datetime(value: Any) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.strip())
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    @staticmethod
    def _parse_memory_profile_time(value: Any) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed


__all__ = [
    "AsrConfirmationState",
    "AsrInflightState",
    "CurrentReferents",
    "DialogState",
    "DialogStateProjections",
    "DialogStateService",
    "HandoverConfirmationState",
    "InteractionState",
    "ReengageConfirmationState",
    "ReEntryRequiredState",
    "StyleReferenceMediaState",
    "StyleReferencePendingState",
]
