#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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


def evaluate(root: Path, config: dict) -> list[str]:
    _bootstrap_python_path(root)

    from app.core.turn_executor import TurnExecutor
    from app.services import tool_registry_service
    from tests import build_test_policy_override_decision

    violations: list[str] = []
    expected_tool_action = str(config["expected_runtime_tool_action"])
    expected_hours_refs = list(config["expected_hours_allowed_fact_refs"])
    expected_parking_refs = list(config["expected_parking_allowed_fact_refs"])
    family_id = str(config["family_id"])
    expected_bundle_policy = str(config["expected_bundle_policy"])
    expected_mixed_scope_reason = str(config["expected_mixed_scope_reason"])

    captured: dict[str, object] = {}

    def _execute_catalog_location(db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Адрес: Абая 10. Работаем ежедневно с 10:00 до 20:00.",
            error_code=None,
            decision_meta={
                "tool_action": kwargs["tool_action"],
                "tool_decision": "location_bundle",
                "info_sections": ["address", "hours"],
            },
            trace={"stage": "tool_registry", "decision": "location_bundle"},
        )

    reroute_decision = build_test_policy_override_decision(
        {
            "intent": "hours",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "tool_args": {"service_query": "маникюр"},
            "pack_refs": ["hours"],
            "fact_refs": ["hours"],
            "slots": {"service": "маникюр"},
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

    with patch("app.services.tool_registry_service.execute_tool_action", _execute_catalog_location):
        reroute_result = TurnExecutor().execute(
            reroute_decision,
            db=object(),
            message_text="До скольки вы сегодня работаете?",
            client_slug="demo_salon",
            branch_id=None,
            booking_state=None,
            user_name=None,
            user_phone=None,
            now=datetime.now(timezone.utc),
        )

    if captured.get("tool_action") != expected_tool_action:
        violations.append(
            f"first fact-family reroute drifted: expected tool_action={expected_tool_action!r}, got {captured.get('tool_action')!r}"
        )
    if captured.get("tool_args") != {}:
        violations.append(f"first fact-family reroute must clear stale tool_args, got {captured.get('tool_args')!r}")
    if captured.get("allowed_fact_refs") != expected_hours_refs:
        violations.append(
            f"first fact-family reroute allowed_fact_refs drifted: expected {expected_hours_refs!r}, got {captured.get('allowed_fact_refs')!r}"
        )
    projection = reroute_result.meta.get("tool_execution_projection") or {}
    if projection.get("tool_action") != expected_tool_action:
        violations.append(f"first fact-family projection drifted: expected tool_action={expected_tool_action!r}")
    if projection.get("fact_family_cutover") != family_id:
        violations.append(f"first fact-family projection missing family_id={family_id!r}")
    if projection.get("fact_family_bundle_policy") != expected_bundle_policy:
        violations.append(
            f"first fact-family projection bundle policy drifted: expected {expected_bundle_policy!r}, got {projection.get('fact_family_bundle_policy')!r}"
        )
    if reroute_result.meta.get("fact_allowed_refs") != expected_hours_refs:
        violations.append(
            f"first fact-family contract drifted: expected allowed refs {expected_hours_refs!r}, got {reroute_result.meta.get('fact_allowed_refs')!r}"
        )

    bypass_calls = {"direct_truth": 0, "pack_runtime": 0}

    def _format_reply_from_truth(*args, **kwargs):
        bypass_calls["direct_truth"] += 1
        return "Есть парковка рядом с салоном."

    def _get_pack_decision(*args, **kwargs):
        bypass_calls["pack_runtime"] += 1
        return SimpleNamespace(
            response="Есть парковка рядом с салоном.",
            intent="parking",
            meta={"info_sections": ["parking"]},
            action="reply",
        )

    bypass_decision = build_test_policy_override_decision(
        {
            "intent": "parking",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": ["parking"],
            "fact_refs": ["parking"],
            "reason": "parking_question",
            "goal": "info",
            "capability": "parking",
            "subject_kind": "branch",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    with (
        patch(
            "app.services.tool_registry_service.execute_tool_action",
            lambda db, **kwargs: SimpleNamespace(
                handled=False,
                ok=False,
                response_text=None,
                error_code=None,
                decision_meta={},
                trace={},
            ),
        ),
        patch("app.services.pack_runtime_service.format_reply_from_truth", _format_reply_from_truth),
        patch("app.services.pack_runtime_service.get_pack_decision", _get_pack_decision),
    ):
        bypass_result = TurnExecutor().execute(
            bypass_decision,
            db=object(),
            message_text="У вас есть парковка?",
            client_slug="demo_salon",
            branch_id=None,
            booking_state=None,
            user_name=None,
            user_phone=None,
            now=datetime.now(timezone.utc),
        )

    if bypass_calls != {"direct_truth": 0, "pack_runtime": 0}:
        violations.append(f"first fact-family bypass reopened: {bypass_calls!r}")
    if bypass_result.tool_action != expected_tool_action:
        violations.append(
            f"first fact-family unresolved path drifted: expected tool_action={expected_tool_action!r}, got {bypass_result.tool_action!r}"
        )
    if bypass_result.tool_decision != "fact_family_unresolved":
        violations.append(
            f"first fact-family unresolved decision drifted: expected 'fact_family_unresolved', got {bypass_result.tool_decision!r}"
        )
    if bypass_result.meta.get("fact_fallback_reason") != "first_fact_family_cutover_unresolved":
        violations.append(
            "first fact-family unresolved meta drifted: expected fact_fallback_reason='first_fact_family_cutover_unresolved'"
        )
    if bypass_result.meta.get("fact_allowed_refs") != expected_parking_refs:
        violations.append(
            f"first fact-family parking contract drifted: expected allowed refs {expected_parking_refs!r}, got {bypass_result.meta.get('fact_allowed_refs')!r}"
        )

    mixed_scope_calls = {"direct_truth": 0, "pack_runtime": 0}

    def _mixed_scope_format_reply(*args, **kwargs):
        mixed_scope_calls["direct_truth"] += 1
        return "Адрес: Абая 10."

    def _mixed_scope_pack_decision(*args, **kwargs):
        mixed_scope_calls["pack_runtime"] += 1
        return SimpleNamespace(
            response="Адрес: Абая 10.",
            intent="location",
            meta={"info_sections": ["location"]},
            action="reply",
        )

    mixed_scope_decision = build_test_policy_override_decision(
        {
            "intent": "other",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": ["parking", "promotions"],
            "fact_refs": ["parking", "promotions"],
            "reason": "mixed_scope_question",
            "goal": "info",
            "capability": "parking",
            "subject_kind": "branch",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    with (
        patch(
            "app.services.tool_registry_service.execute_tool_action",
            lambda db, **kwargs: SimpleNamespace(
                handled=False,
                ok=False,
                response_text=None,
                error_code=None,
                decision_meta={},
                trace={},
            ),
        ),
        patch("app.services.pack_runtime_service.format_reply_from_truth", _mixed_scope_format_reply),
        patch("app.services.pack_runtime_service.get_pack_decision", _mixed_scope_pack_decision),
    ):
        mixed_scope_result = TurnExecutor().execute(
            mixed_scope_decision,
            db=object(),
            message_text="Подскажите парковку и акции.",
            client_slug="demo_salon",
            branch_id=None,
            booking_state=None,
            user_name=None,
            user_phone=None,
            now=datetime.now(timezone.utc),
        )

    if mixed_scope_calls != {"direct_truth": 0, "pack_runtime": 0}:
        violations.append(f"mixed first fact-family scope reopened sibling bypass: {mixed_scope_calls!r}")
    if mixed_scope_result.tool_decision != "fact_family_unresolved":
        violations.append(
            f"mixed first fact-family scope drifted: expected tool_decision='fact_family_unresolved', got {mixed_scope_result.tool_decision!r}"
        )
    if mixed_scope_result.meta.get("fact_fallback_reason") != expected_mixed_scope_reason:
        violations.append(
            "mixed first fact-family scope drifted: expected configured mixed-scope unresolved reason"
        )

    with patch.object(tool_registry_service, "_resolve_branch", lambda db, branch_id: None):
        location_result = tool_registry_service.execute_tool_action(
            object(),
            tool_action=expected_tool_action,
            tool_args={},
            conversation_id=None,
            branch_id=None,
            client_slug="demo_salon",
            service_query=None,
            info_sections_hint=["location", "hours"],
            message_text="У вас есть парковка?",
            expected_reply_type=None,
            now=datetime.now(timezone.utc),
            allowed_fact_refs=expected_hours_refs,
        )

    info_sections = location_result.decision_meta.get("info_sections") or []
    if "parking" in info_sections:
        violations.append(
            "catalog.location widened emitted scope: parking reappeared even though allowed_fact_refs excluded it"
        )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args()

    root = Path(args.repo_root or repo_root())
    config = load_yaml(root / "docs" / "FACT_FAMILY_CUTOVER_GUARD.yaml")
    violations = evaluate(root, config)
    if violations:
        for violation in violations:
            print(f"fact_family_cutover_guard: FAIL: {violation}", file=sys.stderr)
        return 1
    print("fact_family_cutover_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
