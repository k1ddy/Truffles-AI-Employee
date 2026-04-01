#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _bootstrap_python_path(root: Path) -> None:
    truffles_api = root / "truffles-api"
    candidate = str(truffles_api)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)


def _decision(*, build_test_semantic_decision_payload, build_binding_plan, planner):
    semantic_payload = build_test_semantic_decision_payload(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "calendar.list_slots",
            "reason": "collect_datetime",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "ask_about_requested_slot",
            "slots": {"service": "Маникюр"},
            "expected_reply_type": "time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        }
    )
    binding_plan, _projection_trace, error = build_binding_plan(
        semantic_decision=semantic_payload,
        allowed_tool_actions={"collect", "calendar.list_slots"},
    )
    if error is not None or binding_plan is None:
        raise RuntimeError(f"continuity guard could not build collect binding plan: {error}")
    return planner._build_policy_core_decision(
        semantic_payload,
        binding_plan_payload=binding_plan.model_dump(mode="python", exclude_none=True),
    )


def _handoff_decision(*, build_test_semantic_decision_payload, planner, BindingPlanV1):
    semantic_payload = build_test_semantic_decision_payload(
        {
            "intent": "handoff",
            "action": "handoff",
            "tool_action_hint": "handoff",
            "reason": "user_requests_human",
            "subject_kind": "conversation",
            "capability": "handoff",
            "resolution_mode": "policy_handoff",
        }
    )
    return planner._build_policy_core_decision(
        semantic_payload,
        binding_plan_payload=BindingPlanV1.build_compat(
            decision_id=semantic_payload["decision_id"],
            requested_outcome="handoff",
            capability_id="handoff",
            selected_tool_or_workflow_ref="handoff",
            handoff_reason_code="user_requests_human",
        ).model_dump(mode="python", exclude_none=True),
    )


def _stale_context(config: dict) -> dict:
    stale_type = str(config["stale_expected_reply_type"])
    stale_reason = str(config["stale_expected_reply_reason"])
    stale_goal = str(config["stale_current_goal"])
    return {
        "context_manager": {
            "message_count": 4,
            "current_goal": stale_goal,
            "canonical_dialog_state": {
                "owner_id": "context_manager.dialog_state.v1",
                "version": "v1",
                "pending_question_contract": {
                    "expected_reply_type": stale_type,
                    "reason": stale_reason,
                    "next_question": stale_type,
                    "open_questions": [stale_type],
                },
            },
        },
        "expected_reply_type": stale_type,
        "expected_reply_reason": stale_reason,
        "current_goal": stale_goal,
        "session_memory": {
            "active_goal": stale_goal,
            "pending_question_contract": {
                "expected_reply_type": stale_type,
                "reason": stale_reason,
                "next_question": stale_type,
                "open_questions": [stale_type],
            },
        },
    }


def _assert_projection(violations: list[str], updated: dict, expected_goal: str, expected_pending: dict) -> None:
    if "expected_reply_type" in updated:
        violations.append("top-level expected_reply_type survived canonical runtime write")
    if "expected_reply_reason" in updated:
        violations.append("top-level expected_reply_reason survived canonical runtime write")
    if "current_goal" in updated:
        violations.append("top-level current_goal survived canonical runtime write")

    manager = updated.get("context_manager") if isinstance(updated.get("context_manager"), dict) else {}
    if manager.get("current_goal") != expected_goal:
        violations.append(
            f"context_manager.current_goal drifted: expected {expected_goal!r}, got {manager.get('current_goal')!r}"
        )
    canonical_state = (
        manager.get("canonical_dialog_state")
        if isinstance(manager.get("canonical_dialog_state"), dict)
        else {}
    )
    if canonical_state.get("pending_question_contract") != expected_pending:
        violations.append(
            "context_manager.canonical_dialog_state.pending_question_contract did not reproject from canonical runtime state"
        )

    session_memory = updated.get("session_memory") if isinstance(updated.get("session_memory"), dict) else {}
    if session_memory.get("active_goal") != expected_goal:
        violations.append(
            f"session_memory.active_goal drifted: expected {expected_goal!r}, got {session_memory.get('active_goal')!r}"
        )
    if session_memory.get("pending_question_contract") != expected_pending:
        violations.append("session_memory.pending_question_contract did not reproject from canonical runtime state")
    interaction_state = (
        session_memory.get("interaction_state")
        if isinstance(session_memory.get("interaction_state"), dict)
        else {}
    )
    if interaction_state.get("resume_slot") != "datetime":
        violations.append("session_memory.interaction_state.resume_slot did not reflect the canonical pending question")


def _assert_pending_resume(violations: list[str], updated: dict, expected_goal: str, expected_pending: dict) -> None:
    pending_resume = updated.get("pending_resume") if isinstance(updated.get("pending_resume"), dict) else {}
    if not pending_resume:
        violations.append("pending_resume was not captured on the canonical handoff path")
        return

    manager = (
        pending_resume.get("context_manager")
        if isinstance(pending_resume.get("context_manager"), dict)
        else {}
    )
    if manager.get("current_goal") != expected_goal:
        violations.append(
            f"pending_resume.context_manager.current_goal drifted: expected {expected_goal!r}, got {manager.get('current_goal')!r}"
        )
    canonical_state = (
        manager.get("canonical_dialog_state")
        if isinstance(manager.get("canonical_dialog_state"), dict)
        else {}
    )
    if canonical_state.get("pending_question_contract") != expected_pending:
        violations.append("pending_resume.canonical_dialog_state pending question contract is not canonical-derived")
    if pending_resume.get("expected_reply_type") != expected_pending.get("expected_reply_type"):
        violations.append("pending_resume.expected_reply_type is not canonical-derived")
    if pending_resume.get("expected_reply_reason") != expected_pending.get("reason"):
        violations.append("pending_resume.expected_reply_reason is not canonical-derived")


def evaluate(root: Path, config: dict) -> list[str]:
    _bootstrap_python_path(root)

    from app.core import BindingPlanV1, DialogState, DialogStateService
    from app.core.consultant_runtime import ConsultantRuntime
    from app.core.turn_planner import TurnPlanner
    from app.core.policy_tool_projector import build_binding_plan
    from tests import build_test_semantic_decision_payload

    violations: list[str] = []
    now = datetime(2026, 3, 31, 8, 0, tzinfo=timezone.utc)
    expected_goal = str(config["expected_current_goal"])
    expected_pending_resume_goal = str(config.get("expected_pending_resume_current_goal", expected_goal))
    expected_pending = dict(config["expected_pending_question_contract"])
    planner = TurnPlanner()

    service = DialogStateService()
    updated, dialog_state, _ = service.write_runtime_payload(
        _stale_context(config),
        decision=_decision(
            build_test_semantic_decision_payload=build_test_semantic_decision_payload,
            build_binding_plan=build_binding_plan,
            planner=planner,
        ),
        execution_meta={},
        now=now,
    )
    if dialog_state.pending_question_contract.model_dump(mode="json", exclude_none=True) != expected_pending:
        violations.append("DialogState pending_question_contract drifted from expected canonical continuity contract")
    _assert_projection(violations, updated, expected_goal, expected_pending)
    handoff_updated, _handoff_state, _ = service.write_runtime_payload(
        updated,
        decision=_handoff_decision(
            build_test_semantic_decision_payload=build_test_semantic_decision_payload,
            planner=planner,
            BindingPlanV1=BindingPlanV1,
        ),
        execution_meta={},
        now=now,
    )
    _assert_pending_resume(violations, handoff_updated, expected_pending_resume_goal, expected_pending)

    runtime = ConsultantRuntime()
    runtime_updated, runtime_state = runtime._write_runtime_state(
        prepared=SimpleNamespace(),
        runtime_state=SimpleNamespace(
            context=_stale_context(config),
            dialog_state=DialogState.model_validate({}),
            booking_state={},
        ),
        decision=_decision(
            build_test_semantic_decision_payload=build_test_semantic_decision_payload,
            build_binding_plan=build_binding_plan,
            planner=planner,
        ),
        execution=SimpleNamespace(
            meta={},
            clear_booking=False,
            tool_decision="datetime",
        ),
        now=now,
    )
    if runtime_state.pending_question_contract.model_dump(mode="json", exclude_none=True) != expected_pending:
        violations.append("ConsultantRuntime pending_question_contract drifted from canonical runtime continuity contract")
    _assert_projection(violations, runtime_updated, expected_goal, expected_pending)

    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args()

    root = Path(args.repo_root or repo_root())
    config = load_yaml(root / "docs" / "CONTINUITY_STATE_NORMALIZATION_GUARD.yaml")
    violations = evaluate(root, config)
    if violations:
        for violation in violations:
            print(f"continuity_state_normalization_guard: FAIL: {violation}", file=sys.stderr)
        return 1
    print("continuity_state_normalization_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
