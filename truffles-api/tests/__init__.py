from __future__ import annotations

from typing import Any

from app.core import InteractionContract, PolicyDecision, TurnPlanner


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
        meta=meta,
    )
