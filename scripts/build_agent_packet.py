#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


REQUIRED_ROOT_KEYS = {
    "active_dec",
    "active_master_tp",
    "active_block_tp",
    "active_canon",
    "legacy_sunset",
    "execution_strategy",
    "semantic_owner",
    "continuity_owner",
    "boundary_owner",
    "turn_result_contract",
    "projection_only",
    "proof_only",
    "forbidden_semantic_files",
    "platform_evidence_requirement",
    "program",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: YAML document must be a mapping: {path}")
    return data


def require_paths(root: Path, payload: dict, keys: list[str]) -> None:
    for key in keys:
        rel = payload.get(key)
        if not isinstance(rel, str) or not rel.strip():
            raise SystemExit(f"ERROR: missing required path key '{key}' in docs/SOURCE_OF_TRUTH.yaml")
        target = root / rel
        if not target.exists():
            raise SystemExit(f"ERROR: referenced path does not exist for '{key}': {rel}")


def require_file_list(root: Path, payload: dict, *, section: str, key: str) -> None:
    items = payload.get(key)
    if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
        raise SystemExit(f"ERROR: {section}.{key} must be a list[str]")
    for rel in items:
        if not (root / rel).exists():
            raise SystemExit(f"ERROR: referenced path does not exist for '{section}.{key}': {rel}")


def validate_source_of_truth(root: Path, truth: dict, legacy: dict) -> None:
    missing = sorted(REQUIRED_ROOT_KEYS.difference(truth))
    if missing:
        raise SystemExit(f"ERROR: docs/SOURCE_OF_TRUTH.yaml missing keys: {', '.join(missing)}")

    require_paths(root, truth, ["active_dec", "active_master_tp", "active_block_tp", "active_canon", "legacy_sunset"])

    forbidden = truth.get("forbidden_semantic_files")
    if not isinstance(forbidden, list) or not all(isinstance(item, str) for item in forbidden):
        raise SystemExit("ERROR: forbidden_semantic_files must be a list[str]")

    proof_only = truth.get("proof_only", {}).get("files")
    if not isinstance(proof_only, list) or not all(isinstance(item, str) for item in proof_only):
        raise SystemExit("ERROR: proof_only.files must be a list[str]")

    for section_name in ["semantic_owner", "continuity_owner", "boundary_owner", "turn_result_contract"]:
        section = truth.get(section_name)
        if not isinstance(section, dict):
            raise SystemExit(f"ERROR: {section_name} section must be a mapping")
        if "current_primary_files" in section:
            require_file_list(root, section, section=section_name, key="current_primary_files")
        if "target_primary_files" in section:
            require_file_list(root, section, section=section_name, key="target_primary_files")

    execution_strategy = truth.get("execution_strategy")
    if not isinstance(execution_strategy, dict):
        raise SystemExit("ERROR: execution_strategy section must be a mapping")
    for key in [
        "mode",
        "progress_credit_rule",
        "mandatory_sequence",
        "forbidden_shortcuts",
        "operator_instruction_if_uncertain",
        "current_nonnegotiable_next_move",
    ]:
        if key not in execution_strategy:
            raise SystemExit(f"ERROR: execution_strategy missing key '{key}'")
    for list_key in ["mandatory_sequence", "forbidden_shortcuts", "operator_instruction_if_uncertain"]:
        value = execution_strategy.get(list_key)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise SystemExit(f"ERROR: execution_strategy.{list_key} must be a list[str]")

    legacy_sunset_files = legacy.get("sunset_files")
    if not isinstance(legacy_sunset_files, list):
        raise SystemExit("ERROR: docs/LEGACY_SUNSET.yaml missing sunset_files list")
    sunset_paths = [item.get("path") for item in legacy_sunset_files if isinstance(item, dict)]
    if sorted(sunset_paths) != sorted(forbidden):
        raise SystemExit("ERROR: SOURCE_OF_TRUTH forbidden_semantic_files must match LEGACY_SUNSET sunset_files")

    legacy_proof_only = legacy.get("proof_only_files")
    if sorted(legacy_proof_only or []) != sorted(proof_only):
        raise SystemExit("ERROR: SOURCE_OF_TRUTH proof_only.files must match LEGACY_SUNSET proof_only_files")

    program = truth.get("program")
    if not isinstance(program, dict):
        raise SystemExit("ERROR: program section must be a mapping")
    for key in ["current_block", "runtime_cutover_status", "allowed_touch", "forbidden_touch", "required_checks", "open_blockers"]:
        if key not in program:
            raise SystemExit(f"ERROR: program missing key '{key}'")

    allowed_touch = set(program.get("allowed_touch") or [])
    forbidden_touch = set(program.get("forbidden_touch") or [])
    overlap = sorted(allowed_touch.intersection(forbidden_touch))
    if overlap:
        raise SystemExit(f"ERROR: allowed_touch and forbidden_touch overlap: {', '.join(overlap)}")

    if not set(forbidden).issubset(forbidden_touch):
        raise SystemExit("ERROR: program.forbidden_touch must include every forbidden_semantic_file")


def build_packet(truth: dict, legacy: dict) -> dict:
    program = truth["program"]
    packet = {
        "active_dec": truth["active_dec"],
        "active_master_tp": truth["active_master_tp"],
        "active_block_tp": truth["active_block_tp"],
        "active_canon": truth["active_canon"],
        "source_of_truth_map": {
            "execution_strategy": truth["execution_strategy"],
            "semantic_owner": truth["semantic_owner"],
            "continuity_owner": truth["continuity_owner"],
            "boundary_owner": truth["boundary_owner"],
            "turn_result_contract": truth["turn_result_contract"],
            "projection_only": truth["projection_only"],
            "proof_only": truth["proof_only"],
            "forbidden_semantic_files": truth["forbidden_semantic_files"],
            "platform_evidence_requirement": truth["platform_evidence_requirement"],
        },
        "legacy_sunset": legacy,
        "active_master_block": program["current_block"],
        "touch_list_allowed": program["allowed_touch"],
        "touch_list_forbidden": program["forbidden_touch"],
        "required_checks": program["required_checks"],
        "open_blockers": program["open_blockers"],
        "current_runtime_cutover_status": program["runtime_cutover_status"],
    }
    return packet


def render_markdown(packet: dict) -> str:
    cutover = packet["current_runtime_cutover_status"]
    execution_strategy = packet["source_of_truth_map"]["execution_strategy"]
    semantic = packet["source_of_truth_map"]["semantic_owner"]
    continuity = packet["source_of_truth_map"]["continuity_owner"]
    boundary = packet["source_of_truth_map"]["boundary_owner"]
    forbidden = packet["source_of_truth_map"]["forbidden_semantic_files"]
    proof_only = packet["source_of_truth_map"]["proof_only"]["files"]
    lines: list[str] = []
    lines.append("# AGENT PACKET")
    lines.append("")
    lines.append("Read only these first:")
    lines.append(f"- `{packet['active_dec']}`")
    lines.append(f"- `{packet['active_master_tp']}`")
    lines.append(f"- `{packet['active_block_tp']}`")
    lines.append("- `docs/SOURCE_OF_TRUTH.yaml`")
    lines.append("- `docs/LEGACY_SUNSET.yaml`")
    lines.append("")
    lines.append("## Active Block")
    lines.append(f"- {packet['active_master_block']}")
    lines.append("")
    lines.append("## Current Runtime Cutover")
    for key, value in cutover.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("## Execution Strategy Lock")
    lines.append(f"- Mode: `{execution_strategy['mode']}`")
    lines.append(f"- Progress credit rule: `{execution_strategy['progress_credit_rule']}`")
    lines.append(f"- Current non-negotiable next move: `{execution_strategy['current_nonnegotiable_next_move']}`")
    lines.append("- Mandatory sequence:")
    for item in execution_strategy["mandatory_sequence"]:
        lines.append(f"- `{item}`")
    lines.append("- Forbidden shortcuts:")
    for item in execution_strategy["forbidden_shortcuts"]:
        lines.append(f"- `{item}`")
    lines.append("- If context is thin or memory is uncertain:")
    for item in execution_strategy["operator_instruction_if_uncertain"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Semantic Owner")
    lines.append(f"- Contract: `{semantic['contract']}`")
    lines.append(f"- Current: `{semantic['cutover_status']}`")
    for item in semantic.get("current_primary_files", []):
        lines.append(f"- Current authority file: `{item}`")
    for item in semantic.get("target_primary_files", []):
        lines.append(f"- Target file: `{item}`")
    lines.append("")
    lines.append("## Continuity Owner")
    lines.append(f"- Contract: `{continuity['contract']}`")
    lines.append(f"- Current: `{continuity['cutover_status']}`")
    for item in continuity.get("current_primary_files", []):
        lines.append(f"- Current writer file: `{item}`")
    for item in continuity.get("target_primary_files", []):
        lines.append(f"- Target file: `{item}`")
    lines.append("")
    lines.append("## Boundary Owner")
    lines.append(f"- Contract: `{boundary['contract']}`")
    lines.append(f"- Current: `{boundary['cutover_status']}`")
    for item in boundary.get("current_primary_files", []):
        lines.append(f"- Current file: `{item}`")
    for item in boundary.get("target_primary_files", []):
        lines.append(f"- Target file: `{item}`")
    lines.append("")
    lines.append("## Allowed Touch")
    for item in packet["touch_list_allowed"]:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Forbidden Touch")
    for item in packet["touch_list_forbidden"]:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Proof-Only Files")
    for item in proof_only:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Legacy Sunset Files")
    for item in forbidden:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Required Checks")
    for item in packet["required_checks"]:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Open Blockers")
    for item in packet["open_blockers"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_or_check(path: Path, content: str, *, check: bool) -> None:
    if check:
        if not path.exists():
            raise SystemExit(f"ERROR: generated file missing: {path}")
        existing = path.read_text(encoding="utf-8")
        if existing != content:
            raise SystemExit(f"ERROR: generated file is stale: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Validate generated files instead of writing them")
    args = parser.parse_args()

    root = repo_root()
    truth_path = root / "docs" / "SOURCE_OF_TRUTH.yaml"
    legacy_path = root / "docs" / "LEGACY_SUNSET.yaml"
    truth = load_yaml(truth_path)
    legacy = load_yaml(legacy_path)
    validate_source_of_truth(root, truth, legacy)
    packet = build_packet(truth, legacy)

    json_content = json.dumps(packet, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    md_content = render_markdown(packet)

    json_path = root / "docs" / "_generated" / "AGENT_PACKET.json"
    md_path = root / "docs" / "_generated" / "AGENT_PACKET.md"
    write_or_check(json_path, json_content, check=args.check)
    write_or_check(md_path, md_content, check=args.check)

    if not args.check:
        print(f"Wrote {md_path}")
        print(f"Wrote {json_path}")
    else:
        print("build_agent_packet: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
