from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

KNOWN_DUPLICATE_TOP_LEVEL_DEF_COUNTS = {
    Path("truffles-api/app/services/reasoning_core.py"): {
        "_filter_specialist_followup_helper_meta": 2,
        "_finalize_tool_reply_owner_execution": 2,
        "_should_accept_turn_planner_booking_verification_result": 2,
        "_should_accept_turn_planner_duration_collect_result": 2,
        "_should_accept_turn_planner_master_query_collect_result": 2,
        "_should_accept_turn_planner_master_query_result": 2,
        "_should_accept_turn_planner_master_query_service_not_found_collect_result": 2,
        "_should_accept_turn_planner_pricing_collect_result": 2,
        "_try_handle_turn_planner_safe_active_name_time_collect_owner_cutover": 2,
        "_try_handle_turn_planner_safe_bookability_time_collect_owner_cutover": 2,
        "_try_handle_turn_planner_safe_duration_collect_owner_cutover": 2,
        "_try_handle_turn_planner_safe_master_query_collect_owner_cutover": 2,
        "_try_handle_turn_planner_safe_master_query_fact_owner_cutover": 2,
        "_try_handle_turn_planner_safe_pricing_collect_owner_cutover": 2,
        "_try_handle_turn_planner_safe_service_choice_specialist_daypart_collect_owner_cutover": 2,
        "_try_handle_turn_planner_safe_service_choice_specialist_time_collect_owner_cutover": 2,
        "_try_handle_turn_planner_safe_specialist_datetime_collect_owner_cutover": 2,
        "_try_handle_turn_planner_safe_specialist_name_collect_owner_cutover": 2,
    }
}


def _top_level_duplicate_defs(path: Path) -> dict[str, list[int]]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    by_name: dict[str, list[int]] = {}
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            by_name.setdefault(node.name, []).append(node.lineno)
    return {name: lines for name, lines in by_name.items() if len(lines) > 1}


def test_known_duplicate_top_level_core_defs_do_not_grow() -> None:
    unexpected: list[str] = []
    stale_allowances: list[str] = []

    for rel_path, allowed in KNOWN_DUPLICATE_TOP_LEVEL_DEF_COUNTS.items():
        actual = _top_level_duplicate_defs(ROOT / rel_path)

        for name, lines in sorted(actual.items()):
            expected_count = allowed.get(name)
            if expected_count is None:
                unexpected.append(f"{rel_path}:{name}:unexpected duplicate at {lines}")
            elif len(lines) != expected_count:
                unexpected.append(
                    f"{rel_path}:{name}:expected {expected_count} defs, found {len(lines)} at {lines}"
                )

        for name, expected_count in sorted(allowed.items()):
            actual_lines = actual.get(name)
            if actual_lines is None:
                stale_allowances.append(f"{rel_path}:{name}:allowance stale, duplicate removed")
            elif len(actual_lines) != expected_count:
                stale_allowances.append(
                    f"{rel_path}:{name}:allowance stale, expected {expected_count}, found {len(actual_lines)}"
                )

    assert not unexpected and not stale_allowances, (
        "Shadowed top-level core defs changed; remove the debt in a dedicated block or update the explicit guard ledger.\n"
        + "Unexpected:\n- "
        + "\n- ".join(unexpected or ["none"])
        + "\nStale allowances:\n- "
        + "\n- ".join(stale_allowances or ["none"])
    )
