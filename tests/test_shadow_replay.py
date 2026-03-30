from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_shadow_replay_module():
    module_path = Path(__file__).resolve().parents[1] / "ops" / "shadow_replay.py"
    spec = importlib.util.spec_from_file_location("shadow_replay", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("shadow_replay_spec_missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shadow_replay = _load_shadow_replay_module()


def _runtime_trace_contract(*, tool_ref: str = "calendar.list_slots", goal: str = "booking") -> dict:
    return {
        "schema_version": "runtime_trace_contract.v1",
        "trace_id": "trace-1",
        "owner_transition": {
            "decision_id": "decision-1",
            "requested_outcome": "collect",
            "intent": "booking",
            "capability_id": "bookability",
            "interaction_owner": "llm_policy_core_booking",
            "source": "llm_policy_core",
            "tool_action_hint": "calendar.list_slots",
            "needs_human": False,
            "goal": "booking",
        },
        "binding_transition": {
            "binding_id": "binding-1",
            "decision_id": "decision-1",
            "binding_outcome_type": "workflow_advance",
            "capability_id": "bookability",
            "selected_tool_or_workflow_ref": tool_ref,
            "idempotency_key": "decision-1",
            "resolved_args": {"service": "Маникюр"},
            "authz_scope": {},
            "timeout_policy": {},
            "retry_policy": {},
        },
        "action_transition": {
            "contract_action": "booking_prompt",
            "runtime_entrypoint": "consultant_runtime",
            "semantic_runtime_path": "consultant_core_v2",
            "reply_kind": "collect",
            "delivered": True,
            "execution_tool_action": "collect",
            "execution_tool_decision": "slot_constraint",
        },
        "state_transition": {
            "turn_id": "decision-1",
            "conversation_id": "conv-1",
            "current_semantic_decision_ref": "decision-1",
            "active_capability": "bookability",
            "active_workflow_ref": tool_ref,
            "current_goal": goal,
            "pending_question_contract": {
                "expected_reply_type": "time",
                "reason": "collect:datetime",
            },
            "semantic_contract": {
                "capability": "bookability",
                "subject_kind": "service",
            },
            "semantic_state_before": {},
            "semantic_state_after": {
                "user_goal": goal,
            },
            "journal_last_turn_id": "decision-1",
            "journal_event_types": [
                "SemanticDecisionIssued",
                "BindingPlanIssued",
                "ExecutionCompleted",
            ],
            "last_reply_ref": None,
        },
    }


def _bundle(message_id: str, runtime_trace_contract: dict) -> dict:
    return {
        "message": {
            "message_id": message_id,
            "message_uuid": f"uuid-{message_id}",
            "conversation_id": "conv-1",
            "content": "Подскажите время",
        },
        "decision_meta": {
            "action": "booking_prompt",
            "intent": "booking",
            "runtime_trace_contract": runtime_trace_contract,
        },
        "decision_trace": [
            {
                "stage": "consultant_runtime",
                "decision": "booking_prompt",
                "runtime_trace_contract": runtime_trace_contract,
            }
        ],
    }


def test_score_runtime_trace_contract_diff_uses_json_pointer_mismatches() -> None:
    baseline = _runtime_trace_contract()
    shadow = _runtime_trace_contract(tool_ref="calendar.book_slot", goal="handoff")

    score = shadow_replay._score_runtime_trace_contract_diff(baseline, shadow)

    assert score["status"] == "scored"
    assert 0.0 <= score["score"] < 1.0
    mismatch_pointers = {item["pointer"] for item in score["mismatches"]}
    assert "/binding_transition/selected_tool_or_workflow_ref" in mismatch_pointers
    assert "/state_transition/active_workflow_ref" in mismatch_pointers
    assert "/state_transition/current_goal" in mismatch_pointers
    assert score["section_scores"]["owner_transition"] == 1.0
    assert score["section_scores"]["binding_transition"] < 1.0
    assert score["section_scores"]["state_transition"] < 1.0


def test_build_report_includes_runtime_trace_contract_shadow_score() -> None:
    baseline_payload = {"bundles": [_bundle("message-1", _runtime_trace_contract())]}
    shadow_payload = {
        "bundles": [
            _bundle(
                "message-1",
                _runtime_trace_contract(tool_ref="calendar.book_slot", goal="handoff"),
            )
        ]
    }

    report = shadow_replay._build_report(
        base_payload=baseline_payload,
        shadow_payload=shadow_payload,
        input_path="baseline.json",
        shadow_path="shadow.json",
    )

    assert "runtime_trace_contract.shadow_score:" in report
    assert "runtime_trace_contract.mismatch_pointers:" in report
    assert "/binding_transition/selected_tool_or_workflow_ref" in report
    assert "/state_transition/current_goal" in report
    assert "- diff: mismatch" in report
