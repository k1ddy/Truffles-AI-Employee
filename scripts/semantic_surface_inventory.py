#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BOOKING_QUALITY_ROOT = Path("/tmp/booking_quality")

CANONICAL_FIELDS = (
    "action",
    "outcome",
    "expected_reply_type",
    "expected_reply_reason",
    "pending_question_target",
    "active_question_relation",
    "semantic_contract",
    "semantic_frame",
)

SCANNED_PATHS = (
    "truffles-api/app/services/intent_service.py",
    "truffles-api/app/core/turn_planner.py",
    "truffles-api/app/core/dialog_state_service.py",
    "truffles-api/app/core/consultant_runtime.py",
    "truffles-api/app/core/turn_executor.py",
    "truffles-api/app/core/response_realizer.py",
    "truffles-api/app/routers/webhook/decision.py",
    "truffles-api/app/routers/webhook/info.py",
    "truffles-api/app/routers/webhook/booking.py",
    "truffles-api/app/routers/webhook/response.py",
    "truffles-api/app/routers/webhook/class_router_runtime.py",
    "truffles-api/app/routers/webhook/booking_compat.py",
    "truffles-api/app/routers/webhook/decision_compat.py",
    "truffles-api/app/routers/webhook/info_compat.py",
    "truffles-api/app/routers/webhook/info_followup_compat.py",
    "truffles-api/app/routers/webhook/policy_compat.py",
    "truffles-api/app/routers/webhook/response_compat.py",
    "truffles-api/app/services/pack_runtime_compat.py",
    "truffles-api/app/services/demo_salon_knowledge_compat.py",
    "truffles-api/app/services/scenario_contract_compiler.py",
    "truffles-api/app/services/llm_quality_contracts.py",
    "scripts/single_semantic_owner_guard.py",
    "scripts/continuity_writer_guard.py",
)

OWNER_PATHS = {
    "truffles-api/app/services/intent_service.py",
    "truffles-api/app/core/turn_planner.py",
}

OWNER_DERIVED_STATE_PATHS = {
    "truffles-api/app/core/dialog_state_service.py",
}

ORACLE_PATHS = {
    "truffles-api/app/services/scenario_contract_compiler.py",
    "truffles-api/app/services/llm_quality_contracts.py",
}

STATIC_GUARD_PATHS = {
    "scripts/single_semantic_owner_guard.py",
    "scripts/continuity_writer_guard.py",
}


@dataclass(frozen=True)
class Occurrence:
    field: str
    path: str
    line: int
    kind: str
    container: str | None
    function: str | None
    layer: str
    authority: str
    legality: str
    scope: str
    source_segment: str | None


def git_output(args: list[str]) -> str:
    return subprocess.check_output(["git", "-C", str(REPO_ROOT), *args], text=True)


def resolve_head() -> str:
    try:
        return git_output(["rev-parse", "HEAD"]).strip()
    except Exception:
        return "unknown"


def source_segment(source: str, node: ast.AST | None) -> str | None:
    if node is None:
        return None
    return (ast.get_source_segment(source, node) or "").strip() or None


def literal_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def assignment_targets(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.Assign):
        return list(node.targets)
    if isinstance(node, ast.AnnAssign):
        return [node.target]
    if isinstance(node, ast.AugAssign):
        return [node.target]
    return []


def assignment_value(node: ast.AST) -> ast.AST | None:
    if isinstance(node, ast.Assign):
        return node.value
    if isinstance(node, ast.AnnAssign):
        return node.value
    if isinstance(node, ast.AugAssign):
        return node.value
    return None


def target_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return source_segment("", node)
    return None


def iter_dict_entries(node: ast.Dict) -> list[tuple[str, ast.AST]]:
    entries: list[tuple[str, ast.AST]] = []
    for key, value in zip(node.keys, node.values):
        key_token = literal_string(key)
        if key_token is None:
            continue
        entries.append((key_token, value))
    return entries


def classify_path(path: str, field: str) -> tuple[str, str, str]:
    if path in OWNER_PATHS:
        return "owner", "legal", "live_runtime"
    if path in OWNER_DERIVED_STATE_PATHS:
        return "owner_derived_state", "legal", "live_runtime"
    if path in ORACLE_PATHS:
        return "oracle_expectation", "legal", "oracle"
    if path in STATIC_GUARD_PATHS:
        return "static_guard", "legal", "tooling"
    if path.endswith("_compat.py"):
        return "compat", "illegal", "live_runtime"
    if "/routers/webhook/" in path:
        return "router", "illegal", "live_runtime"
    if path.endswith("consultant_runtime.py"):
        return "runtime_trace", "illegal", "live_runtime"
    if path.endswith("turn_executor.py"):
        return "executor", "illegal", "live_runtime"
    if path.endswith("response_realizer.py"):
        return "realizer", "illegal", "live_runtime"
    if path.endswith("class_router_runtime.py"):
        return "controller", "illegal", "live_runtime"
    return "other", "illegal", "unknown"


def container_scope(path: str, field: str, container: str | None) -> str:
    if path in ORACLE_PATHS:
        return "oracle_expectation"
    if path in STATIC_GUARD_PATHS:
        return "tooling_guard"
    if container in {"decision_meta", "trace_event", "question_contract_entry"}:
        return "runtime_trace_meta"
    if container in {"pending_question_contract", "expected_pending_question_contract"}:
        return "pending_contract"
    if container in {"semantic_contract", "runtime_trace_contract_payload"}:
        return "semantic_contract"
    if container in {"expect", "meta", "meta_any"}:
        return "scenario_expectation"
    return "unknown"


class SurfaceScanner(ast.NodeVisitor):
    def __init__(self, *, path: str, source: str):
        self.path = path
        self.source = source
        self.function_stack: list[str] = []
        self.occurrences: list[Occurrence] = []

    def _record(
        self,
        *,
        field: str,
        node: ast.AST,
        kind: str,
        container: str | None,
        value_node: ast.AST | None = None,
    ) -> None:
        authority, legality, layer = classify_path(self.path, field)
        self.occurrences.append(
            Occurrence(
                field=field,
                path=self.path,
                line=getattr(node, "lineno", 0) or 0,
                kind=kind,
                container=container,
                function=self.function_stack[-1] if self.function_stack else None,
                layer=layer,
                authority=authority,
                legality=legality,
                scope=container_scope(self.path, field, container),
                source_segment=source_segment(self.source, node if value_node is None else value_node),
            )
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> Any:
        self._scan_assignment(node)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        self._scan_assignment(node)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> Any:
        self._scan_assignment(node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        func = node.func
        if isinstance(func, ast.Attribute):
            receiver = source_segment(self.source, func.value)
            if func.attr in {"update", "setdefault"}:
                dict_node: ast.Dict | None = None
                if func.attr == "update" and node.args and isinstance(node.args[0], ast.Dict):
                    dict_node = node.args[0]
                if func.attr == "setdefault" and node.args:
                    key = literal_string(node.args[0])
                    if key in CANONICAL_FIELDS:
                        self._record(
                            field=key,
                            node=node,
                            kind="call.setdefault",
                            container=receiver,
                            value_node=node,
                        )
                if dict_node is not None:
                    for key, value in iter_dict_entries(dict_node):
                        if key in CANONICAL_FIELDS:
                            self._record(
                                field=key,
                                node=node,
                                kind=f"call.{func.attr}",
                                container=receiver,
                                value_node=value,
                            )
            if func.attr == "model_copy":
                for keyword in node.keywords:
                    if keyword.arg == "update" and isinstance(keyword.value, ast.Dict):
                        for key, value in iter_dict_entries(keyword.value):
                            if key in CANONICAL_FIELDS:
                                self._record(
                                    field=key,
                                    node=node,
                                    kind="call.model_copy_update",
                                    container=receiver,
                                    value_node=value,
                                )
        self.generic_visit(node)

    def _scan_assignment(self, node: ast.AST) -> None:
        targets = assignment_targets(node)
        value = assignment_value(node)
        if isinstance(value, ast.Dict):
            containers = [source_segment(self.source, target) for target in targets] or [None]
            container = next((item for item in containers if item), None)
            for key, entry_value in iter_dict_entries(value):
                if key in CANONICAL_FIELDS:
                    self._record(
                        field=key,
                        node=node,
                        kind="dict_literal",
                        container=container,
                        value_node=entry_value,
                    )
        for target in targets:
            if isinstance(target, ast.Subscript):
                key = literal_string(target.slice)
                if key in CANONICAL_FIELDS:
                    self._record(
                        field=key,
                        node=node,
                        kind="subscript_assign",
                        container=source_segment(self.source, target.value),
                    )


def scan_file(path: Path) -> list[Occurrence]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    scanner = SurfaceScanner(path=str(path.relative_to(REPO_ROOT)), source=source)
    scanner.visit(tree)
    return scanner.occurrences


def summarize_occurrences(occurrences: list[Occurrence]) -> dict[str, Any]:
    by_field: dict[str, dict[str, Any]] = {}
    for field in CANONICAL_FIELDS:
        rows = [item for item in occurrences if item.field == field]
        by_field[field] = {
            "occurrence_count": len(rows),
            "paths": sorted({item.path for item in rows}),
            "illegal_paths": sorted({item.path for item in rows if item.legality == "illegal"}),
            "authorities": sorted({item.authority for item in rows}),
            "scopes": sorted({item.scope for item in rows}),
        }

    by_path: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[Occurrence]] = defaultdict(list)
    for item in occurrences:
        grouped[item.path].append(item)
    for path, rows in sorted(grouped.items()):
        by_path[path] = {
            "field_count": len({item.field for item in rows}),
            "occurrence_count": len(rows),
            "fields": sorted({item.field for item in rows}),
            "legality": sorted({item.legality for item in rows}),
            "authority": sorted({item.authority for item in rows}),
            "scope": sorted({item.scope for item in rows}),
        }
    return {"by_field": by_field, "by_path": by_path}


def latest_path(pattern: str) -> Path | None:
    matches = sorted(BOOKING_QUALITY_ROOT.glob(pattern), key=lambda item: item.stat().st_mtime)
    return matches[-1] if matches else None


def load_json(path: Path | None) -> Any:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_manual_audit_families() -> list[dict[str, Any]]:
    families: list[dict[str, Any]] = []
    for path in sorted(BOOKING_QUALITY_ROOT.glob("*_manual_audit.json")):
        payload = load_json(path)
        if not isinstance(payload, dict):
            continue
        if payload.get("human_semantic_valid") is not True:
            continue
        run_id = str(payload.get("run_id") or path.stem).strip()
        summary = str(payload.get("summary") or "").strip()
        if not summary:
            continue
        families.append(
            {
                "family_id": run_id,
                "status": "fixed_recent",
                "classification": "human_semantic_green",
                "mechanism_class": "focused_family_proof",
                "summary": summary,
                "evidence": [str(path)],
            }
        )
    return families


def load_open_oracle_family() -> list[dict[str, Any]]:
    replay_dir = latest_path("a922-broader-replay-*")
    if replay_dir is None:
        return []
    failure_families = load_json(replay_dir / "failure_families.json")
    responses = replay_dir / "responses.jsonl"
    if not isinstance(failure_families, dict):
        return []
    grouped: dict[str, dict[str, Any]] = {}
    for family in failure_families.get("families") or []:
        if not isinstance(family, dict):
            continue
        sample_turns = family.get("sample_turns") or []
        if not sample_turns:
            continue
        message_id = str(sample_turns[0].get("message_id") or "").strip()
        if not message_id:
            continue
        cluster = grouped.setdefault(
            message_id,
            {
                "family_id": f"oracle:{message_id}",
                "status": "open",
                "classification": "oracle_or_evaluator_error",
                "mechanism_class": "scenario_expectation_drift",
                "reason_codes": [],
                "sample_turns": sample_turns,
                "evidence": [str(replay_dir / "failure_families.json"), str(responses)],
            },
        )
        reason = str(family.get("reason") or "").strip()
        if reason and reason not in cluster["reason_codes"]:
            cluster["reason_codes"].append(reason)
    for cluster in grouped.values():
        reasons = sorted(cluster["reason_codes"])
        cluster["summary"] = (
            "Scenario/oracle expectation drift on a runtime-correct specialist follow-up turn; "
            f"reasons={','.join(reasons)}"
        )
    return list(grouped.values())


def load_contract_action_family() -> list[dict[str, Any]]:
    proof_path = latest_path("a922-contract-action-live-proof-*.json")
    if proof_path is None:
        return []
    payload = load_json(proof_path)
    if not isinstance(payload, dict):
        return []
    decision_meta = payload.get("decision_meta_subset")
    rtc = payload.get("runtime_trace_contract_subset")
    if not isinstance(decision_meta, dict) or not isinstance(rtc, dict):
        return []
    return [
        {
            "family_id": "boundary:contract_action_compression",
            "status": "fixed_recent",
            "classification": "boundary_fallback_error",
            "mechanism_class": "canonical_action_compression",
            "summary": (
                "Focused live proof now preserves owner collect action end-to-end in decision_meta "
                "and runtime_trace_contract."
            ),
            "evidence": [str(proof_path)],
            "observed_values": {
                "decision_meta_action": decision_meta.get("action"),
                "owner_requested_outcome": rtc.get("owner_requested_outcome"),
                "contract_action": rtc.get("contract_action"),
            },
        }
    ]


def build_family_registry() -> dict[str, Any]:
    fixed_recent = load_manual_audit_families()
    fixed_recent.extend(load_contract_action_family())
    open_families = load_open_oracle_family()
    return {
        "schema_version": "b0.family_registry.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "open_families": open_families,
        "fixed_recent_families": fixed_recent,
        "summary": {
            "open_family_count": len(open_families),
            "fixed_recent_count": len(fixed_recent),
        },
    }


def build_block_order(family_registry: dict[str, Any]) -> list[dict[str, Any]]:
    open_mechanisms = sorted(
        {
            str(item.get("mechanism_class"))
            for item in family_registry.get("open_families") or []
            if isinstance(item, dict) and item.get("mechanism_class")
        }
    )
    return [
        {
            "block_id": "B1",
            "objective": "Focused Proof Harness",
            "why_now": [
                "broader_replay_is_too_expensive_for_primary_debugging",
                "focused_live_proof_needs_one_canonical_entrypoint",
            ],
            "blocked_by": ["B0"],
            "first_check": "python3 scripts/focused_family_proof.py --help",
        },
        {
            "block_id": "B2",
            "objective": "Static Guard Expansion",
            "why_now": ["non_owner_surfaces_must_be_detected_before_runtime_fix_batches"],
            "blocked_by": ["B0", "B1"],
            "first_check": "python3 scripts/single_semantic_owner_guard.py",
        },
        {
            "block_id": "B3",
            "objective": "Semantic Write Barrier",
            "why_now": ["eliminate_non_owner_canonical_writers", *open_mechanisms],
            "blocked_by": ["B0", "B1", "B2"],
            "first_check": "cd truffles-api && PYTHONPATH=. pytest -q tests/test_consultant_core_runtime_contracts.py",
        },
        {
            "block_id": "B4",
            "objective": "Canonical Presentation Split",
            "why_now": ["collect_vs_booking_prompt_taxonomy_conflict_must_be_removed"],
            "blocked_by": ["B3"],
            "first_check": "cd truffles-api && PYTHONPATH=. pytest -q tests/test_message_endpoint.py -k booking_prompt",
        },
        {
            "block_id": "B5",
            "objective": "Boundary Zero Semantic Recovery",
            "why_now": ["boundary_layers_must_only_validate_block_or_degrade"],
            "blocked_by": ["B4"],
            "first_check": "cd truffles-api && PYTHONPATH=. pytest -q tests/test_consultant_core_runtime_contracts.py -k boundary",
        },
        {
            "block_id": "B6",
            "objective": "Compat Router Controller Freeze",
            "why_now": ["remaining_compat_and_router_semantic_surfaces_must_be_observer_only"],
            "blocked_by": ["B5"],
            "first_check": "cd truffles-api && PYTHONPATH=. pytest -q tests/architecture/test_single_semantic_owner_guard.py",
        },
    ]


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the B0 semantic surface inventory.")
    parser.add_argument("--output-dir", required=True, help="Directory for emitted B0 artifacts.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    files_scanned: list[str] = []
    occurrences: list[Occurrence] = []
    missing_files: list[str] = []
    for rel_path in SCANNED_PATHS:
        path = REPO_ROOT / rel_path
        if not path.exists():
            missing_files.append(rel_path)
            continue
        files_scanned.append(rel_path)
        occurrences.extend(scan_file(path))

    summary = summarize_occurrences(occurrences)
    surface_map = {
        "schema_version": "b0.semantic_surface_inventory.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "active_head": resolve_head(),
        "canonical_fields": list(CANONICAL_FIELDS),
        "files_scanned": files_scanned,
        "missing_files": missing_files,
        "hot_path_coverage": {
            "required_field_count": len(CANONICAL_FIELDS),
            "covered_field_count": sum(
                1 for field in CANONICAL_FIELDS if summary["by_field"][field]["occurrence_count"] > 0
            ),
            "files_scanned_count": len(files_scanned),
        },
        "occurrences": [item.__dict__ for item in sorted(occurrences, key=lambda row: (row.path, row.line, row.field))],
        "by_field": summary["by_field"],
        "by_path": summary["by_path"],
        "summary": {
            "occurrence_count": len(occurrences),
            "illegal_occurrence_count": sum(1 for item in occurrences if item.legality == "illegal"),
            "illegal_paths": sorted({item.path for item in occurrences if item.legality == "illegal"}),
        },
    }
    family_registry = build_family_registry()
    block_order = build_block_order(family_registry)

    write_json(output_dir / "surface_map.json", surface_map)
    write_json(output_dir / "family_registry.json", family_registry)
    write_json(output_dir / "block_order.json", block_order)
    write_json(
        output_dir / "result.json",
        {
            "status": "ok",
            "surface_map": str(output_dir / "surface_map.json"),
            "family_registry": str(output_dir / "family_registry.json"),
            "block_order": str(output_dir / "block_order.json"),
            "covered_field_count": surface_map["hot_path_coverage"]["covered_field_count"],
            "required_field_count": surface_map["hot_path_coverage"]["required_field_count"],
            "open_family_count": family_registry["summary"]["open_family_count"],
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
