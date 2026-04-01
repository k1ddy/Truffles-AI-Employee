from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.core import (
    BindingPlanV1,
    DialogStateService,
    InteractionContract,
    PolicyDecision,
    SemanticDecisionV1,
    TurnPlanner,
)
from app.core.policy_tool_projector import build_binding_plan
from app.services.state_service import _build_session_memory_observability_snapshot


def build_test_policy_override_decision(
    payload: dict[str, Any],
    *,
    interaction_owner: str,
    interaction_relation: str | None = None,
    source: str = "policy_core",
) -> PolicyDecision:
    planner = TurnPlanner()
    action = planner._normalize_token(payload.get("action")) or "handoff"
    intent = planner._normalize_token(payload.get("intent")) or "other"
    tool_action = planner._normalize_tool_action(payload.get("tool_action"))
    outcome = planner._ACTION_TO_OUTCOME.get(action)
    if outcome is None:
        raise ValueError(f"unsupported_policy_action:{action}")
    relation = interaction_relation or planner._normalize_token(
        payload.get("active_question_relation")
    )
    capability = planner._normalize_token(payload.get("capability"))
    entity_refs = planner._normalize_entity_refs(payload.get("entity_refs"))
    pending_question = planner._build_pending_question_contract(payload)
    semantic_frame = planner._build_semantic_frame_payload(
        payload,
        entity_refs=entity_refs,
        pending_question=pending_question,
    )
    meta: dict[str, Any] = {
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
    if entity_refs:
        meta["entity_refs"] = entity_refs
    semantic_contract = planner._build_semantic_contract_payload(
        payload,
        entity_refs=entity_refs,
        semantic_frame=semantic_frame,
    )
    if semantic_contract:
        meta["semantic_contract"] = semantic_contract
    binding_decision_id = uuid4().hex
    binding_plan, _projection_trace, _projection_error = build_binding_plan(
        semantic_decision={
            "decision_id": binding_decision_id,
            "action": action,
            "tool_action_hint": tool_action,
            "slots": planner._normalize_string_dict(payload.get("slots")),
            "pack_refs": planner._normalize_list(payload.get("pack_refs")),
            "entity_refs": entity_refs,
            "referents": dict((semantic_contract or {}).get("referents") or {}),
            "intent": intent,
            "capability": capability,
            "subject_kind": planner._normalize_token(payload.get("subject_kind")),
            "temporal_scope": planner._normalize_token(payload.get("temporal_scope")),
            "resolution_mode": planner._normalize_token(payload.get("resolution_mode")),
            "reason": planner._normalize_token(payload.get("reason")),
            "decision_summary": planner._normalize_token(payload.get("reason")),
            "next_question": planner._normalize_token(payload.get("next_question")),
            "open_questions": planner._normalize_list(payload.get("open_questions")),
            "pending_question_act": planner._normalize_token(payload.get("pending_question_act")),
            "pending_question_target": planner._normalize_token(payload.get("pending_question_target")),
            "active_question_relation": planner._normalize_token(
                payload.get("active_question_relation")
            ),
        },
        allowed_tool_actions={
            tool_action,
            "collect",
            "handoff",
            "calendar.list_slots",
            "calendar.book_slot",
            "calendar.get_booking",
            "calendar.reschedule",
            "calendar.cancel",
            "catalog.service_query",
            "catalog.location",
            "catalog.portfolio",
        },
    )
    if binding_plan is None:
        binding_plan = BindingPlanV1.build_compat(
            decision_id=binding_decision_id,
            requested_outcome=action,
            capability_id=capability,
            selected_tool_or_workflow_ref=tool_action,
            resolved_args=planner._normalize_dict(payload.get("tool_args")),
            handoff_reason_code=planner._normalize_token(payload.get("reason")),
        )
    return PolicyDecision(
        outcome=outcome,
        action=action,
        intent=intent,
        source=source,
        tool_action=tool_action,
        tool_args=planner._normalize_dict(payload.get("tool_args")),
        slots=planner._normalize_string_dict(payload.get("slots")),
        pack_refs=planner._normalize_list(payload.get("pack_refs")),
        capability_refs=[capability] if capability else [],
        risk_signals=planner._normalize_list(payload.get("risk_signals")),
        interaction=InteractionContract(
            owner=interaction_owner,
            target=planner._normalize_token(payload.get("pending_question_target")),
            relation=relation,
        ),
        semantic_frame=semantic_frame,
        pending_question_contract=pending_question,
        binding_plan=binding_plan,
        meta=meta,
    )


def build_test_semantic_decision_payload(payload: dict[str, Any]) -> dict[str, Any]:
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(payload)
    return semantic_decision.model_dump(mode="python", exclude_none=True)


def build_test_sync_session_memory_interaction_state(
    context: dict[str, Any],
    *,
    interaction_state: dict[str, Any] | None,
    now: datetime,
) -> tuple[dict[str, Any], dict[str, Any]]:
    service = DialogStateService()
    memory, changed = service.sync_session_memory_interaction_state(
        context.get("session_memory") if isinstance(context.get("session_memory"), dict) else {},
        interaction_state=interaction_state,
        now=now,
        default_ttl_hours=24,
    )
    if changed:
        context = service.set_context_session_memory(context, memory, key="session_memory")
    return context, memory


def build_test_reset_session_memory(
    *,
    context: dict[str, Any],
    context_manager: dict[str, Any],
    reason: str,
    now: datetime,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    from app.routers.webhook import decision as decision_router
    from app.routers.webhook.booking import _clear_service_hint, _set_booking_context
    from app.routers.webhook.context_manager import _set_context_manager, _set_expected_reply_type
    from app.routers.webhook.guards import _set_intent_queue

    service = DialogStateService()
    manager = service.clear_context_manager_carryover_family(
        context_manager,
        class_manager_key=decision_router.CLASS_CARRYOVER_KEY,
        service_manager_key=decision_router.SERVICE_CARRYOVER_KEY,
        consult_manager_key=decision_router.CONSULT_CONTEXT_KEY,
        canonical_state_key="canonical_dialog_state",
        referent_key="service",
    )
    updated_context = _set_context_manager(context, manager)
    updated_context = _set_expected_reply_type(updated_context, None)
    updated_context = _set_intent_queue(updated_context, [])
    updated_context = _set_booking_context(updated_context, {"active": False})
    updated_context = _clear_service_hint(updated_context)
    updated_context = service.set_context_session_memory(
        updated_context,
        None,
        key="session_memory",
    )
    memory_payload = service.touch_session_memory_payload(
        {},
        now=now,
        default_ttl_hours=24,
    )
    snapshot = _build_session_memory_observability_snapshot(memory_payload)
    snapshot["reason"] = reason
    return updated_context, manager, snapshot
