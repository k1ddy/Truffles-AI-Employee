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


def _hours_decision(build_test_policy_override_decision):
    return build_test_policy_override_decision(
        {
            "intent": "hours",
            "action": "fact",
            "tool_action": "catalog.location",
            "fact_refs": ["hours"],
            "reason": "hours_lookup",
            "goal": "info",
            "capability": "hours",
            "subject_kind": "branch",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )


def _promotions_decision(build_test_policy_override_decision):
    return build_test_policy_override_decision(
        {
            "intent": "promotions",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "fact_refs": ["promotions"],
            "reason": "promo_lookup",
            "goal": "info",
            "capability": "promotions",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )


def _expected_payload(config: dict) -> dict:
    return {
        "class": str(config["expected_class_name"]),
        "intents": list(config["expected_intents"]),
        "info_sections": list(config["expected_info_sections"]),
        "message_count": int(config["expected_message_count"]),
        "ttl": int(config["expected_ttl"]),
    }


def evaluate(root: Path, config: dict) -> list[str]:
    _bootstrap_python_path(root)

    from app.core import DialogState, DialogStateService
    from app.core.consultant_runtime import ConsultantRuntime
    from tests import build_test_policy_override_decision

    violations: list[str] = []
    expected = _expected_payload(config)
    family_id = str(config["family_id"])
    now = datetime(2026, 3, 30, 14, 0, tzinfo=timezone.utc)

    service = DialogStateService()
    context = {
        "context_manager": {
            "message_count": expected["message_count"],
            "canonical_dialog_state": {
                "owner_id": "context_manager.dialog_state.v1",
                "version": "v1",
            },
        }
    }
    updated, dialog_state, _ = service.write_runtime_payload(
        context,
        decision=_hours_decision(build_test_policy_override_decision),
        execution_meta={
            "fact_family_cutover": family_id,
            "info_sections": list(config["expected_info_sections"]),
            "fact_emitted_refs": list(config["expected_intents"]),
        },
        now=now,
    )

    if dialog_state.meta.get("class_carryover") != expected:
        violations.append(
            f"dialog_state meta.class_carryover drifted: expected {expected!r}, got {dialog_state.meta.get('class_carryover')!r}"
        )
    manager = updated.get("context_manager") if isinstance(updated.get("context_manager"), dict) else {}
    if manager.get("class_carryover") != expected:
        violations.append(
            f"context_manager.class_carryover drifted: expected {expected!r}, got {manager.get('class_carryover')!r}"
        )
    canonical_state = manager.get("canonical_dialog_state") if isinstance(manager.get("canonical_dialog_state"), dict) else {}
    canonical_meta = canonical_state.get("meta") if isinstance(canonical_state.get("meta"), dict) else {}
    if canonical_meta.get("class_carryover") != expected:
        violations.append(
            "context_manager.canonical_dialog_state.meta.class_carryover no longer mirrors runtime touched-slice carryover"
        )

    updated["context_manager"]["message_count"] = expected["message_count"] + 1
    next_updated, next_dialog_state, _ = service.write_runtime_payload(
        updated,
        decision=_promotions_decision(build_test_policy_override_decision),
        execution_meta={"info_sections": ["promotions"]},
        now=now,
    )
    if next_dialog_state.meta.get("class_carryover") != expected:
        violations.append("runtime write no longer preserves touched-slice class_carryover across the next non-family turn")
    next_manager = (
        next_updated.get("context_manager") if isinstance(next_updated.get("context_manager"), dict) else {}
    )
    if next_manager.get("class_carryover") != expected:
        violations.append("derived context_manager.class_carryover no longer preserves the canonical touched-slice payload")

    runtime = ConsultantRuntime()
    runtime_updated, runtime_dialog_state = runtime._write_runtime_state(
        prepared=SimpleNamespace(),
        runtime_state=SimpleNamespace(
            context={
                "context_manager": {
                    "message_count": expected["message_count"],
                    "canonical_dialog_state": {
                        "owner_id": "context_manager.dialog_state.v1",
                        "version": "v1",
                    },
                }
            },
            dialog_state=DialogState.model_validate({}),
            booking_state={},
        ),
        decision=_hours_decision(build_test_policy_override_decision),
        execution=SimpleNamespace(
            meta={
                "fact_family_cutover": family_id,
                "info_sections": list(config["expected_info_sections"]),
                "fact_emitted_refs": list(config["expected_intents"]),
            },
            clear_booking=False,
            tool_decision="location_bundle",
        ),
        now=now,
    )
    if runtime_dialog_state.meta.get("class_carryover") != expected:
        violations.append("ConsultantRuntime._write_runtime_state no longer materializes touched-slice class_carryover")
    runtime_manager = (
        runtime_updated.get("context_manager") if isinstance(runtime_updated.get("context_manager"), dict) else {}
    )
    if runtime_manager.get("class_carryover") != expected:
        violations.append("ConsultantRuntime._write_runtime_state no longer projects touched-slice class_carryover into context_manager")

    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args()

    root = Path(args.repo_root or repo_root())
    config = load_yaml(root / "docs" / "TOUCHED_SLICE_CONTINUITY_GUARD.yaml")
    violations = evaluate(root, config)
    if violations:
        for violation in violations:
            print(f"touched_slice_continuity_guard: FAIL: {violation}", file=sys.stderr)
        return 1
    print("touched_slice_continuity_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
