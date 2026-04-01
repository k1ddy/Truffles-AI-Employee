#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


REQUIRED_ROOT_KEYS = {
    "active_dec",
    "active_master_tp",
    "active_block_tp",
    "active_canon",
    "legacy_sunset",
    "authority_registry",
    "compatibility_carrier_inventory",
    "dead_surface_registry",
    "legacy_caller_surface",
    "governance_delta",
    "recovery_execution_lock",
    "governance_registries",
    "current_non_negotiable_next_move",
    "governing_architecture",
    "anti_partial_closure_law",
    "authority_recovery_program",
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

_CONFIDENCE_VALUES = {"high", "medium", "low"}
_AUTHORITY_REQUIRED_FIELDS = {
    "mechanism_id",
    "mechanism_class",
    "writer_law",
    "current_primary_actor_paths",
    "current_competing_writer_paths",
    "current_live_caller_paths",
    "current_truth_carriers",
    "target_owner",
    "target_contract",
    "next_phase_required",
    "full_closure_phase",
    "closure_criteria",
    "evidence",
    "confidence",
}
_COMPATIBILITY_REQUIRED_FIELDS = {
    "carrier_id",
    "carrier_layer",
    "covered_fields",
    "current_truth_rank",
    "known_writer_paths",
    "known_reader_paths",
    "writer_precedence",
    "reader_precedence",
    "allowed_future_write_paths",
    "guarded_context_tokens",
    "target_fate",
    "full_closure_phase",
    "fate_owner",
    "expiry_trigger",
    "evidence",
    "confidence",
}
_COMPATIBILITY_TOP_LEVEL_REQUIRED_FIELDS = {
    "canonical_owner_paths",
    "freeze_guard",
    "reader_precedence_law",
    "carriers",
}
_FREEZE_GUARD_REQUIRED_FIELDS = {
    "policy",
    "allowed_new_writer_paths",
    "guarded_context_tokens",
    "evidence",
}
_READER_PRECEDENCE_REQUIRED_FIELDS = {
    "default_order",
    "evidence",
}
_SURFACE_TOP_LEVEL_REQUIRED_FIELDS = {
    "active_block",
    "caller_proof_law",
    "entries",
}
_SURFACE_CALLER_PROOF_REQUIRED_FIELDS = {
    "policy",
    "behavior_owning_surfaces",
    "shadow_only_surfaces",
    "evidence",
}
_SURFACE_REQUIRED_FIELDS = {
    "surface_id",
    "surface_path",
    "surface_kind",
    "classification",
    "path_exists_expected",
    "current_role",
    "authority_mode",
    "caller_proof_status",
    "live_runtime_callers",
    "static_app_importers",
    "test_only_importers",
    "route_registration_paths",
    "hot_path_reachable",
    "target_fate",
    "evidence",
    "confidence",
}
_LEGACY_CALLER_TOP_LEVEL_REQUIRED_FIELDS = {
    "active_block",
    "freeze_policy",
    "entries",
}
_LEGACY_CALLER_FREEZE_POLICY_REQUIRED_FIELDS = {
    "policy",
    "frozen_adapter_only_modules",
    "shadow_or_wrapper_candidates",
    "forbidden_new_authority_classes",
    "evidence",
}
_LEGACY_CALLER_REQUIRED_FIELDS = {
    "module_path",
    "module_role",
    "freeze_mode",
    "mechanism_pressure",
    "hot_path_status",
    "live_runtime_callers",
    "static_app_importers",
    "test_only_importers",
    "target_fate",
    "evidence",
    "confidence",
}
_GOVERNANCE_DELTA_REQUIRED_FIELDS = {
    "active_block",
    "block_tp",
    "delta_summary",
    "locked_mechanisms",
    "frozen_modules",
    "new_machine_readable_artifacts",
    "deferred_next_blocks",
    "evidence",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: YAML document must be a mapping: {path}")
    return data


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: JSON document must be an object: {path}")
    return data


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _path_exists(root: Path, rel: str) -> bool:
    return (root / rel).exists()


def require_paths(root: Path, payload: dict[str, Any], keys: list[str]) -> None:
    for key in keys:
        rel = payload.get(key)
        if not _is_non_empty_string(rel):
            raise SystemExit(f"ERROR: missing required path key '{key}' in docs/SOURCE_OF_TRUTH.yaml")
        if not _path_exists(root, rel):
            raise SystemExit(f"ERROR: referenced path does not exist for '{key}': {rel}")


def require_file_list(root: Path, payload: dict[str, Any], *, section: str, key: str) -> None:
    items = payload.get(key)
    if not isinstance(items, list) or not all(_is_non_empty_string(item) for item in items):
        raise SystemExit(f"ERROR: {section}.{key} must be a list[str]")
    for rel in items:
        if not _path_exists(root, rel):
            raise SystemExit(f"ERROR: referenced path does not exist for '{section}.{key}': {rel}")


def _require_string_list(errors: list[str], value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list) or not all(_is_non_empty_string(item) for item in value):
        errors.append(f"{label} must be a list[str]")
        return []
    return [str(item).strip() for item in value]


def _validate_repo_paths(errors: list[str], root: Path, rels: list[str], *, label: str) -> None:
    for rel in rels:
        if not _path_exists(root, rel):
            errors.append(f"{label} references missing path: {rel}")


def _validate_confidence(errors: list[str], value: Any, *, label: str) -> None:
    if value not in _CONFIDENCE_VALUES:
        errors.append(f"{label} must be one of: {', '.join(sorted(_CONFIDENCE_VALUES))}")


def collect_source_of_truth_errors(root: Path, truth: dict[str, Any], legacy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_ROOT_KEYS.difference(truth))
    if missing:
        errors.append(f"docs/SOURCE_OF_TRUTH.yaml missing keys: {', '.join(missing)}")
        return errors

    for key in [
        "active_dec",
        "active_master_tp",
        "active_block_tp",
        "active_canon",
        "legacy_sunset",
        "authority_registry",
        "compatibility_carrier_inventory",
        "dead_surface_registry",
    "recovery_execution_lock",
    ]:
        rel = truth.get(key)
        if not _is_non_empty_string(rel):
            errors.append(f"missing required path key '{key}' in docs/SOURCE_OF_TRUTH.yaml")
            continue
        if not _path_exists(root, rel):
            errors.append(f"referenced path does not exist for '{key}': {rel}")

    current_next_move = truth.get("current_non_negotiable_next_move")
    if not _is_non_empty_string(current_next_move):
        errors.append("current_non_negotiable_next_move must be a non-empty string")

    governing_architecture = truth.get("governing_architecture")
    if not isinstance(governing_architecture, dict):
        errors.append("governing_architecture section must be a mapping")
    else:
        if not _is_non_empty_string(governing_architecture.get("statement")):
            errors.append("governing_architecture.statement must be a non-empty string")
        _require_string_list(errors, governing_architecture.get("planes"), label="governing_architecture.planes")

    anti_partial_closure_law = truth.get("anti_partial_closure_law")
    if not isinstance(anti_partial_closure_law, dict):
        errors.append("anti_partial_closure_law section must be a mapping")
    else:
        if not _is_non_empty_string(anti_partial_closure_law.get("summary")):
            errors.append("anti_partial_closure_law.summary must be a non-empty string")
        _require_string_list(
            errors,
            anti_partial_closure_law.get("unacceptable_if"),
            label="anti_partial_closure_law.unacceptable_if",
        )

    authority_recovery_program = truth.get("authority_recovery_program")
    phases: list[str] = []
    if not isinstance(authority_recovery_program, dict):
        errors.append("authority_recovery_program section must be a mapping")
    else:
        phases = _require_string_list(
            errors,
            authority_recovery_program.get("phases"),
            label="authority_recovery_program.phases",
        )

    governance_registries = truth.get("governance_registries")
    if not isinstance(governance_registries, dict):
        errors.append("governance_registries section must be a mapping")
    else:
        expected_sections = {
            "authority": truth.get("authority_registry"),
            "compatibility_carriers": truth.get("compatibility_carrier_inventory"),
            "surface_topology": truth.get("dead_surface_registry"),
            "legacy_caller_surface": truth.get("legacy_caller_surface"),
            "governance_delta": truth.get("governance_delta"),
        }
        for section_name, path_key_value in expected_sections.items():
            section = governance_registries.get(section_name)
            if not isinstance(section, dict):
                errors.append(f"governance_registries.{section_name} must be a mapping")
                continue
            if section.get("path") != path_key_value:
                errors.append(
                    f"governance_registries.{section_name}.path must match top-level registry path"
                )
            if not _is_non_empty_string(section.get("required_status")):
                errors.append(f"governance_registries.{section_name}.required_status must be a non-empty string")
        if isinstance(governance_registries.get("authority"), dict):
            _require_string_list(
                errors,
                governance_registries["authority"].get("required_mechanisms"),
                label="governance_registries.authority.required_mechanisms",
            )
        if isinstance(governance_registries.get("compatibility_carriers"), dict):
            _require_string_list(
                errors,
                governance_registries["compatibility_carriers"].get("required_carriers"),
                label="governance_registries.compatibility_carriers.required_carriers",
            )
        if isinstance(governance_registries.get("surface_topology"), dict):
            _require_string_list(
                errors,
                governance_registries["surface_topology"].get("required_surfaces"),
                label="governance_registries.surface_topology.required_surfaces",
            )
        if isinstance(governance_registries.get("legacy_caller_surface"), dict):
            _require_string_list(
                errors,
                governance_registries["legacy_caller_surface"].get("required_modules"),
                label="governance_registries.legacy_caller_surface.required_modules",
            )
        if isinstance(governance_registries.get("governance_delta"), dict):
            _require_string_list(
                errors,
                governance_registries["governance_delta"].get("required_locked_mechanisms"),
                label="governance_registries.governance_delta.required_locked_mechanisms",
            )

    forbidden = truth.get("forbidden_semantic_files")
    forbidden_files = _require_string_list(errors, forbidden, label="forbidden_semantic_files")

    proof_only = None
    proof_only_section = truth.get("proof_only")
    if not isinstance(proof_only_section, dict):
        errors.append("proof_only section must be a mapping")
    else:
        proof_only = _require_string_list(errors, proof_only_section.get("files"), label="proof_only.files")

    for section_name in ["semantic_owner", "continuity_owner", "boundary_owner", "turn_result_contract"]:
        section = truth.get(section_name)
        if not isinstance(section, dict):
            errors.append(f"{section_name} section must be a mapping")
            continue
        if "current_primary_files" in section:
            current_files = _require_string_list(errors, section.get("current_primary_files"), label=f"{section_name}.current_primary_files")
            _validate_repo_paths(errors, root, current_files, label=f"{section_name}.current_primary_files")
        if "target_primary_files" in section:
            target_files = _require_string_list(errors, section.get("target_primary_files"), label=f"{section_name}.target_primary_files")
            for rel in target_files:
                if rel.startswith("contracts/") and not _path_exists(root, rel):
                    errors.append(f"{section_name}.target_primary_files references missing path: {rel}")

    execution_strategy = truth.get("execution_strategy")
    if not isinstance(execution_strategy, dict):
        errors.append("execution_strategy section must be a mapping")
    else:
        for key in [
            "mode",
            "progress_credit_rule",
            "mandatory_sequence",
            "forbidden_shortcuts",
            "operator_instruction_if_uncertain",
            "current_nonnegotiable_next_move",
        ]:
            if key not in execution_strategy:
                errors.append(f"execution_strategy missing key '{key}'")
        mandatory_sequence = _require_string_list(
            errors,
            execution_strategy.get("mandatory_sequence"),
            label="execution_strategy.mandatory_sequence",
        )
        _require_string_list(
            errors,
            execution_strategy.get("forbidden_shortcuts"),
            label="execution_strategy.forbidden_shortcuts",
        )
        _require_string_list(
            errors,
            execution_strategy.get("operator_instruction_if_uncertain"),
            label="execution_strategy.operator_instruction_if_uncertain",
        )
        if execution_strategy.get("current_nonnegotiable_next_move") != current_next_move:
            errors.append(
                "current_non_negotiable_next_move must match execution_strategy.current_nonnegotiable_next_move"
            )
        if phases and mandatory_sequence and phases != mandatory_sequence:
            errors.append("authority_recovery_program.phases must match execution_strategy.mandatory_sequence")

    legacy_sunset_files = legacy.get("sunset_files")
    if not isinstance(legacy_sunset_files, list):
        errors.append("docs/LEGACY_SUNSET.yaml missing sunset_files list")
    else:
        sunset_paths = [item.get("path") for item in legacy_sunset_files if isinstance(item, dict)]
        if sorted(sunset_paths) != sorted(forbidden_files):
            errors.append("SOURCE_OF_TRUTH forbidden_semantic_files must match LEGACY_SUNSET sunset_files")

    legacy_proof_only = sorted(legacy.get("proof_only_files") or [])
    if proof_only is not None and legacy_proof_only != sorted(proof_only):
        errors.append("SOURCE_OF_TRUTH proof_only.files must match LEGACY_SUNSET proof_only_files")

    continuity_guard = legacy.get("continuity_guard")
    if not isinstance(continuity_guard, dict):
        errors.append("docs/LEGACY_SUNSET.yaml missing continuity_guard mapping")
    else:
        continuity_allowed = _require_string_list(
            errors,
            continuity_guard.get("allowed_writer_paths"),
            label="docs/LEGACY_SUNSET.yaml continuity_guard.allowed_writer_paths",
        )
        continuity_tokens = _require_string_list(
            errors,
            continuity_guard.get("guarded_tokens"),
            label="docs/LEGACY_SUNSET.yaml continuity_guard.guarded_tokens",
        )
        _validate_repo_paths(
            errors,
            root,
            continuity_allowed,
            label="docs/LEGACY_SUNSET.yaml continuity_guard.allowed_writer_paths",
        )
        if not continuity_allowed:
            errors.append("docs/LEGACY_SUNSET.yaml continuity_guard.allowed_writer_paths must not be empty")
        if not continuity_tokens:
            errors.append("docs/LEGACY_SUNSET.yaml continuity_guard.guarded_tokens must not be empty")

    program = truth.get("program")
    if not isinstance(program, dict):
        errors.append("program section must be a mapping")
    else:
        for key in [
            "current_block",
            "runtime_cutover_status",
            "allowed_touch",
            "forbidden_touch",
            "required_checks",
            "open_blockers",
        ]:
            if key not in program:
                errors.append(f"program missing key '{key}'")
        allowed_touch = set(_require_string_list(errors, program.get("allowed_touch"), label="program.allowed_touch"))
        forbidden_touch = set(_require_string_list(errors, program.get("forbidden_touch"), label="program.forbidden_touch"))
        _validate_repo_paths(errors, root, sorted(allowed_touch), label="program.allowed_touch")
        _validate_repo_paths(errors, root, sorted(forbidden_touch), label="program.forbidden_touch")
        overlap = sorted(allowed_touch.intersection(forbidden_touch))
        if overlap:
            errors.append(f"allowed_touch and forbidden_touch overlap: {', '.join(overlap)}")
        blocked_forbidden_files = set(forbidden_files).difference(allowed_touch)
        if blocked_forbidden_files and not blocked_forbidden_files.issubset(forbidden_touch):
            errors.append(
                "program.forbidden_touch must include every forbidden_semantic_file not explicitly waived by program.allowed_touch"
            )
        _require_string_list(errors, program.get("required_checks"), label="program.required_checks")
        _require_string_list(errors, program.get("open_blockers"), label="program.open_blockers")

    return errors


def load_machine_readable_governance(root: Path, truth: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        "authority_registry": load_json(root / truth["authority_registry"]),
        "compatibility_carrier_inventory": load_json(root / truth["compatibility_carrier_inventory"]),
        "dead_surface_registry": load_json(root / truth["dead_surface_registry"]),
        "legacy_caller_surface": load_json(root / truth["legacy_caller_surface"]),
        "governance_delta": load_json(root / truth["governance_delta"]),
    }


def collect_governance_registry_errors(root: Path, truth: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    governance = truth.get("governance_registries")
    if not isinstance(governance, dict):
        return ["governance_registries section missing or invalid"]

    try:
        registries = load_machine_readable_governance(root, truth)
    except (KeyError, json.JSONDecodeError) as exc:
        return [f"failed to load machine-readable governance registries: {exc}"]
    legacy = load_yaml(root / truth["legacy_sunset"])

    program = truth.get("program") if isinstance(truth.get("program"), dict) else {}
    runtime_cutover = program.get("runtime_cutover_status") if isinstance(program, dict) else {}
    open_blockers = program.get("open_blockers") if isinstance(program, dict) else []
    phases = set(((truth.get("authority_recovery_program") or {}).get("phases")) or [])

    authority = registries["authority_registry"]
    authority_section = governance.get("authority") or {}
    if authority.get("status") != authority_section.get("required_status"):
        errors.append("authority_registry status must match SOURCE_OF_TRUTH governance_registries.authority.required_status")
    if authority.get("status") == "machine_readable_governance_base":
        if isinstance(runtime_cutover, dict) and runtime_cutover.get("authority_topology") == (
            "not_yet_materialized_as_machine_readable_governance"
        ):
            errors.append(
                "program.runtime_cutover_status.authority_topology is stale: machine-readable governance base already exists"
            )
        if isinstance(open_blockers, list) and "authority_registry_not_yet_materialized" in open_blockers:
            errors.append(
                "program.open_blockers is stale: authority_registry_not_yet_materialized must be removed once the registry base exists"
            )
    mounted = authority.get("mounted_runtime_topology")
    if not isinstance(mounted, dict):
        errors.append("authority_registry.mounted_runtime_topology must be a mapping")
    else:
        for key in ["mounted_ingress_paths", "hot_path"]:
            rels = _require_string_list(errors, mounted.get(key), label=f"authority_registry.mounted_runtime_topology.{key}")
            _validate_repo_paths(errors, root, rels, label=f"authority_registry.mounted_runtime_topology.{key}")
    entries = authority.get("entries")
    if not isinstance(entries, list) or not entries:
        errors.append("authority_registry.entries must be a non-empty list")
    else:
        mechanism_ids: set[str] = set()
        for index, entry in enumerate(entries):
            label = f"authority_registry.entries[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{label} must be a mapping")
                continue
            missing = sorted(_AUTHORITY_REQUIRED_FIELDS.difference(entry))
            if missing:
                errors.append(f"{label} missing keys: {', '.join(missing)}")
                continue
            mechanism_id = entry.get("mechanism_id")
            if not _is_non_empty_string(mechanism_id):
                errors.append(f"{label}.mechanism_id must be a non-empty string")
            else:
                mechanism_ids.add(str(mechanism_id).strip())
            for key in ["mechanism_class", "writer_law", "target_contract", "next_phase_required", "full_closure_phase"]:
                if not _is_non_empty_string(entry.get(key)):
                    errors.append(f"{label}.{key} must be a non-empty string")
            for phase_key in ["next_phase_required", "full_closure_phase"]:
                phase_value = entry.get(phase_key)
                if _is_non_empty_string(phase_value) and phase_value not in phases:
                    errors.append(f"{label}.{phase_key} must be a declared recovery phase")
            for list_key in [
                "current_primary_actor_paths",
                "current_competing_writer_paths",
                "current_live_caller_paths",
                "current_truth_carriers",
                "target_owner",
                "closure_criteria",
                "evidence",
            ]:
                items = _require_string_list(errors, entry.get(list_key), label=f"{label}.{list_key}")
                if list_key.endswith("_paths") or list_key == "evidence":
                    _validate_repo_paths(errors, root, items, label=f"{label}.{list_key}")
            _validate_confidence(errors, entry.get("confidence"), label=f"{label}.confidence")
        required_mechanisms = set(
            _require_string_list(
                errors,
                authority_section.get("required_mechanisms"),
                label="governance_registries.authority.required_mechanisms",
            )
        )
        if required_mechanisms and mechanism_ids != required_mechanisms:
            errors.append("authority_registry mechanism set must match governance_registries.authority.required_mechanisms")

    compatibility = registries["compatibility_carrier_inventory"]
    compatibility_section = governance.get("compatibility_carriers") or {}
    if compatibility.get("status") != compatibility_section.get("required_status"):
        errors.append(
            "compatibility_carrier_inventory status must match SOURCE_OF_TRUTH governance_registries.compatibility_carriers.required_status"
        )
    missing_top_level = sorted(_COMPATIBILITY_TOP_LEVEL_REQUIRED_FIELDS.difference(compatibility))
    if missing_top_level:
        errors.append(
            "compatibility_carrier_inventory missing top-level keys: " + ", ".join(missing_top_level)
        )
    canonical_owner_paths = _require_string_list(
        errors,
        compatibility.get("canonical_owner_paths"),
        label="compatibility_carrier_inventory.canonical_owner_paths",
    )
    _validate_repo_paths(errors, root, canonical_owner_paths, label="compatibility_carrier_inventory.canonical_owner_paths")
    freeze_guard = compatibility.get("freeze_guard")
    if not isinstance(freeze_guard, dict):
        errors.append("compatibility_carrier_inventory.freeze_guard must be a mapping")
    else:
        missing = sorted(_FREEZE_GUARD_REQUIRED_FIELDS.difference(freeze_guard))
        if missing:
            errors.append("compatibility_carrier_inventory.freeze_guard missing keys: " + ", ".join(missing))
        if not _is_non_empty_string(freeze_guard.get("policy")):
            errors.append("compatibility_carrier_inventory.freeze_guard.policy must be a non-empty string")
        freeze_allowed_paths = _require_string_list(
            errors,
            freeze_guard.get("allowed_new_writer_paths"),
            label="compatibility_carrier_inventory.freeze_guard.allowed_new_writer_paths",
        )
        freeze_guard_tokens = _require_string_list(
            errors,
            freeze_guard.get("guarded_context_tokens"),
            label="compatibility_carrier_inventory.freeze_guard.guarded_context_tokens",
        )
        freeze_evidence = _require_string_list(
            errors,
            freeze_guard.get("evidence"),
            label="compatibility_carrier_inventory.freeze_guard.evidence",
        )
        _validate_repo_paths(
            errors,
            root,
            freeze_allowed_paths,
            label="compatibility_carrier_inventory.freeze_guard.allowed_new_writer_paths",
        )
        _validate_repo_paths(
            errors,
            root,
            freeze_evidence,
            label="compatibility_carrier_inventory.freeze_guard.evidence",
        )
        legacy_guard = legacy.get("continuity_guard") if isinstance(legacy.get("continuity_guard"), dict) else {}
        legacy_allowed_paths = set(legacy_guard.get("allowed_writer_paths") or [])
        legacy_guard_tokens = set(legacy_guard.get("guarded_tokens") or [])
        if legacy_allowed_paths and legacy_allowed_paths != set(freeze_allowed_paths):
            errors.append(
                "compatibility_carrier_inventory.freeze_guard.allowed_new_writer_paths must match LEGACY_SUNSET continuity_guard.allowed_writer_paths"
            )
        if legacy_guard_tokens and legacy_guard_tokens != set(freeze_guard_tokens):
            errors.append(
                "compatibility_carrier_inventory.freeze_guard.guarded_context_tokens must match LEGACY_SUNSET continuity_guard.guarded_tokens"
            )
    reader_precedence_law = compatibility.get("reader_precedence_law")
    if not isinstance(reader_precedence_law, dict):
        errors.append("compatibility_carrier_inventory.reader_precedence_law must be a mapping")
    else:
        missing = sorted(_READER_PRECEDENCE_REQUIRED_FIELDS.difference(reader_precedence_law))
        if missing:
            errors.append(
                "compatibility_carrier_inventory.reader_precedence_law missing keys: " + ", ".join(missing)
            )
        default_order = _require_string_list(
            errors,
            reader_precedence_law.get("default_order"),
            label="compatibility_carrier_inventory.reader_precedence_law.default_order",
        )
        if not default_order:
            errors.append("compatibility_carrier_inventory.reader_precedence_law.default_order must not be empty")
        precedence_evidence = _require_string_list(
            errors,
            reader_precedence_law.get("evidence"),
            label="compatibility_carrier_inventory.reader_precedence_law.evidence",
        )
        _validate_repo_paths(
            errors,
            root,
            precedence_evidence,
            label="compatibility_carrier_inventory.reader_precedence_law.evidence",
        )
    carriers = compatibility.get("carriers")
    if not isinstance(carriers, list) or not carriers:
        errors.append("compatibility_carrier_inventory.carriers must be a non-empty list")
    else:
        carrier_ids: set[str] = set()
        for index, entry in enumerate(carriers):
            label = f"compatibility_carrier_inventory.carriers[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{label} must be a mapping")
                continue
            missing = sorted(_COMPATIBILITY_REQUIRED_FIELDS.difference(entry))
            if missing:
                errors.append(f"{label} missing keys: {', '.join(missing)}")
                continue
            carrier_id = entry.get("carrier_id")
            if not _is_non_empty_string(carrier_id):
                errors.append(f"{label}.carrier_id must be a non-empty string")
            else:
                carrier_ids.add(str(carrier_id).strip())
            for key in [
                "carrier_layer",
                "current_truth_rank",
                "target_fate",
                "full_closure_phase",
                "fate_owner",
                "expiry_trigger",
            ]:
                if not _is_non_empty_string(entry.get(key)):
                    errors.append(f"{label}.{key} must be a non-empty string")
            phase_value = entry.get("full_closure_phase")
            if _is_non_empty_string(phase_value) and phase_value not in phases:
                errors.append(f"{label}.full_closure_phase must be a declared recovery phase")
            covered_fields = _require_string_list(errors, entry.get("covered_fields"), label=f"{label}.covered_fields")
            if not covered_fields:
                errors.append(f"{label}.covered_fields must not be empty")
            writer_paths = _require_string_list(errors, entry.get("known_writer_paths"), label=f"{label}.known_writer_paths")
            reader_paths = _require_string_list(errors, entry.get("known_reader_paths"), label=f"{label}.known_reader_paths")
            writer_precedence = _require_string_list(
                errors,
                entry.get("writer_precedence"),
                label=f"{label}.writer_precedence",
            )
            reader_precedence = _require_string_list(
                errors,
                entry.get("reader_precedence"),
                label=f"{label}.reader_precedence",
            )
            allowed_future_write_paths = _require_string_list(
                errors,
                entry.get("allowed_future_write_paths"),
                label=f"{label}.allowed_future_write_paths",
            )
            guarded_context_tokens = _require_string_list(
                errors,
                entry.get("guarded_context_tokens"),
                label=f"{label}.guarded_context_tokens",
            )
            evidence_paths = _require_string_list(errors, entry.get("evidence"), label=f"{label}.evidence")
            _validate_repo_paths(errors, root, writer_paths, label=f"{label}.known_writer_paths")
            _validate_repo_paths(errors, root, reader_paths, label=f"{label}.known_reader_paths")
            _validate_repo_paths(
                errors,
                root,
                allowed_future_write_paths,
                label=f"{label}.allowed_future_write_paths",
            )
            _validate_repo_paths(errors, root, evidence_paths, label=f"{label}.evidence")
            if not writer_precedence:
                errors.append(f"{label}.writer_precedence must not be empty")
            if not reader_precedence:
                errors.append(f"{label}.reader_precedence must not be empty")
            if not allowed_future_write_paths:
                errors.append(f"{label}.allowed_future_write_paths must not be empty")
            freeze_guard_tokens = set((compatibility.get("freeze_guard") or {}).get("guarded_context_tokens") or [])
            if set(guarded_context_tokens) - freeze_guard_tokens:
                errors.append(
                    f"{label}.guarded_context_tokens must be a subset of compatibility_carrier_inventory.freeze_guard.guarded_context_tokens"
                )
            _validate_confidence(errors, entry.get("confidence"), label=f"{label}.confidence")
        required_carriers = set(
            _require_string_list(
                errors,
                compatibility_section.get("required_carriers"),
                label="governance_registries.compatibility_carriers.required_carriers",
            )
        )
        if required_carriers and not required_carriers.issubset(carrier_ids):
            errors.append("compatibility_carrier_inventory must include every required carrier from SOURCE_OF_TRUTH")

    surfaces = registries["dead_surface_registry"]
    surface_section = governance.get("surface_topology") or {}
    if surfaces.get("status") != surface_section.get("required_status"):
        errors.append(
            "dead_surface_registry status must match SOURCE_OF_TRUTH governance_registries.surface_topology.required_status"
        )
    missing_surface_top_level = sorted(_SURFACE_TOP_LEVEL_REQUIRED_FIELDS.difference(surfaces))
    if missing_surface_top_level:
        errors.append("dead_surface_registry missing top-level keys: " + ", ".join(missing_surface_top_level))
    caller_proof_law = surfaces.get("caller_proof_law")
    if not isinstance(caller_proof_law, dict):
        errors.append("dead_surface_registry.caller_proof_law must be a mapping")
    else:
        missing = sorted(_SURFACE_CALLER_PROOF_REQUIRED_FIELDS.difference(caller_proof_law))
        if missing:
            errors.append("dead_surface_registry.caller_proof_law missing keys: " + ", ".join(missing))
        if not _is_non_empty_string(caller_proof_law.get("policy")):
            errors.append("dead_surface_registry.caller_proof_law.policy must be a non-empty string")
        for key in ["behavior_owning_surfaces", "shadow_only_surfaces", "evidence"]:
            items = _require_string_list(errors, caller_proof_law.get(key), label=f"dead_surface_registry.caller_proof_law.{key}")
            _validate_repo_paths(errors, root, items, label=f"dead_surface_registry.caller_proof_law.{key}")
    surface_entries = surfaces.get("entries")
    if not isinstance(surface_entries, list) or not surface_entries:
        errors.append("dead_surface_registry.entries must be a non-empty list")
    else:
        surface_paths: set[str] = set()
        for index, entry in enumerate(surface_entries):
            label = f"dead_surface_registry.entries[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{label} must be a mapping")
                continue
            missing = sorted(_SURFACE_REQUIRED_FIELDS.difference(entry))
            if missing:
                errors.append(f"{label} missing keys: {', '.join(missing)}")
                continue
            surface_path = entry.get("surface_path")
            if not _is_non_empty_string(surface_path):
                errors.append(f"{label}.surface_path must be a non-empty string")
            else:
                surface_paths.add(str(surface_path).strip())
            for key in [
                "surface_id",
                "surface_kind",
                "classification",
                "current_role",
                "authority_mode",
                "caller_proof_status",
                "target_fate",
            ]:
                if not _is_non_empty_string(entry.get(key)):
                    errors.append(f"{label}.{key} must be a non-empty string")
            path_exists_expected = entry.get("path_exists_expected")
            if not isinstance(path_exists_expected, bool):
                errors.append(f"{label}.path_exists_expected must be a boolean")
            elif _is_non_empty_string(surface_path):
                actual_exists = _path_exists(root, str(surface_path).strip())
                if actual_exists != path_exists_expected:
                    errors.append(
                        f"{label}.surface_path existence mismatch for {surface_path}: expected {path_exists_expected}, got {actual_exists}"
                    )
            for list_key in [
                "live_runtime_callers",
                "static_app_importers",
                "test_only_importers",
                "route_registration_paths",
                "evidence",
            ]:
                items = _require_string_list(errors, entry.get(list_key), label=f"{label}.{list_key}")
                _validate_repo_paths(errors, root, items, label=f"{label}.{list_key}")
            hot_path_reachable = entry.get("hot_path_reachable")
            if not isinstance(hot_path_reachable, bool):
                errors.append(f"{label}.hot_path_reachable must be a boolean")
            evidence_paths = _require_string_list(errors, entry.get("evidence"), label=f"{label}.evidence")
            _validate_repo_paths(errors, root, evidence_paths, label=f"{label}.evidence")
            _validate_confidence(errors, entry.get("confidence"), label=f"{label}.confidence")
        required_surfaces = set(
            _require_string_list(
                errors,
                surface_section.get("required_surfaces"),
                label="governance_registries.surface_topology.required_surfaces",
            )
        )
        if required_surfaces and not required_surfaces.issubset(surface_paths):
            errors.append("dead_surface_registry must include every required surface from SOURCE_OF_TRUTH")

    legacy_callers = registries["legacy_caller_surface"]
    legacy_caller_section = governance.get("legacy_caller_surface") or {}
    if legacy_callers.get("status") != legacy_caller_section.get("required_status"):
        errors.append(
            "legacy_caller_surface status must match SOURCE_OF_TRUTH governance_registries.legacy_caller_surface.required_status"
        )
    missing_legacy_top_level = sorted(_LEGACY_CALLER_TOP_LEVEL_REQUIRED_FIELDS.difference(legacy_callers))
    if missing_legacy_top_level:
        errors.append("legacy_caller_surface missing top-level keys: " + ", ".join(missing_legacy_top_level))
    freeze_policy = legacy_callers.get("freeze_policy")
    if not isinstance(freeze_policy, dict):
        errors.append("legacy_caller_surface.freeze_policy must be a mapping")
    else:
        missing = sorted(_LEGACY_CALLER_FREEZE_POLICY_REQUIRED_FIELDS.difference(freeze_policy))
        if missing:
            errors.append("legacy_caller_surface.freeze_policy missing keys: " + ", ".join(missing))
        if not _is_non_empty_string(freeze_policy.get("policy")):
            errors.append("legacy_caller_surface.freeze_policy.policy must be a non-empty string")
        for key in [
            "frozen_adapter_only_modules",
            "shadow_or_wrapper_candidates",
            "forbidden_new_authority_classes",
            "evidence",
        ]:
            items = _require_string_list(errors, freeze_policy.get(key), label=f"legacy_caller_surface.freeze_policy.{key}")
            if key != "forbidden_new_authority_classes":
                _validate_repo_paths(errors, root, items, label=f"legacy_caller_surface.freeze_policy.{key}")
    legacy_entries = legacy_callers.get("entries")
    if not isinstance(legacy_entries, list) or not legacy_entries:
        errors.append("legacy_caller_surface.entries must be a non-empty list")
    else:
        module_paths: set[str] = set()
        for index, entry in enumerate(legacy_entries):
            label = f"legacy_caller_surface.entries[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{label} must be a mapping")
                continue
            missing = sorted(_LEGACY_CALLER_REQUIRED_FIELDS.difference(entry))
            if missing:
                errors.append(f"{label} missing keys: {', '.join(missing)}")
                continue
            module_path = entry.get("module_path")
            if not _is_non_empty_string(module_path):
                errors.append(f"{label}.module_path must be a non-empty string")
            else:
                module_paths.add(str(module_path).strip())
                _validate_repo_paths(errors, root, [str(module_path).strip()], label=f"{label}.module_path")
            for key in ["module_role", "freeze_mode", "mechanism_pressure", "hot_path_status", "target_fate"]:
                if not _is_non_empty_string(entry.get(key)):
                    errors.append(f"{label}.{key} must be a non-empty string")
            for list_key in ["live_runtime_callers", "static_app_importers", "test_only_importers", "evidence"]:
                items = _require_string_list(errors, entry.get(list_key), label=f"{label}.{list_key}")
                _validate_repo_paths(errors, root, items, label=f"{label}.{list_key}")
            _validate_confidence(errors, entry.get("confidence"), label=f"{label}.confidence")
        required_modules = set(
            _require_string_list(
                errors,
                legacy_caller_section.get("required_modules"),
                label="governance_registries.legacy_caller_surface.required_modules",
            )
        )
        if required_modules and required_modules != module_paths:
            errors.append("legacy_caller_surface module set must match governance_registries.legacy_caller_surface.required_modules")

    governance_delta = registries["governance_delta"]
    governance_delta_section = governance.get("governance_delta") or {}
    if governance_delta.get("status") != governance_delta_section.get("required_status"):
        errors.append(
            "governance_delta status must match SOURCE_OF_TRUTH governance_registries.governance_delta.required_status"
        )
    missing_delta = sorted(_GOVERNANCE_DELTA_REQUIRED_FIELDS.difference(governance_delta))
    if missing_delta:
        errors.append("governance_delta missing keys: " + ", ".join(missing_delta))
    if not _is_non_empty_string(governance_delta.get("block_tp")):
        errors.append("governance_delta.block_tp must be a non-empty string")
    else:
        _validate_repo_paths(errors, root, [governance_delta["block_tp"]], label="governance_delta.block_tp")
    if not _is_non_empty_string(governance_delta.get("delta_summary")):
        errors.append("governance_delta.delta_summary must be a non-empty string")
    locked_mechanisms = _require_string_list(
        errors,
        governance_delta.get("locked_mechanisms"),
        label="governance_delta.locked_mechanisms",
    )
    frozen_modules = _require_string_list(
        errors,
        governance_delta.get("frozen_modules"),
        label="governance_delta.frozen_modules",
    )
    new_artifacts = _require_string_list(
        errors,
        governance_delta.get("new_machine_readable_artifacts"),
        label="governance_delta.new_machine_readable_artifacts",
    )
    deferred_blocks = _require_string_list(
        errors,
        governance_delta.get("deferred_next_blocks"),
        label="governance_delta.deferred_next_blocks",
    )
    delta_evidence = _require_string_list(errors, governance_delta.get("evidence"), label="governance_delta.evidence")
    _validate_repo_paths(errors, root, frozen_modules, label="governance_delta.frozen_modules")
    _validate_repo_paths(errors, root, new_artifacts, label="governance_delta.new_machine_readable_artifacts")
    _validate_repo_paths(errors, root, delta_evidence, label="governance_delta.evidence")
    if deferred_blocks:
        for block in deferred_blocks:
            if block not in phases:
                errors.append("governance_delta.deferred_next_blocks must contain declared recovery phases only")
    required_locked_mechanisms = set(
        _require_string_list(
            errors,
            governance_delta_section.get("required_locked_mechanisms"),
            label="governance_registries.governance_delta.required_locked_mechanisms",
        )
    )
    if required_locked_mechanisms and set(locked_mechanisms) != required_locked_mechanisms:
        errors.append(
            "governance_delta.locked_mechanisms must match governance_registries.governance_delta.required_locked_mechanisms"
        )
    authority_mechanisms = {entry.get("mechanism_id") for entry in authority.get("entries", []) if isinstance(entry, dict)}
    if authority_mechanisms and set(locked_mechanisms) != authority_mechanisms:
        errors.append("governance_delta.locked_mechanisms must match authority_registry mechanism ids")

    return errors


def collect_recovery_execution_lock_errors(root: Path, truth: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rel = truth.get("recovery_execution_lock")
    if not _is_non_empty_string(rel):
        return ["recovery_execution_lock must be a non-empty string"]
    lock_path = root / str(rel).strip()
    if not lock_path.exists():
        return [f"recovery_execution_lock path does not exist: {rel}"]
    lock = load_yaml(lock_path)
    root_first_context = lock.get("root_first_context")
    if not isinstance(root_first_context, dict):
        return ["recovery execution lock must define root_first_context"]

    expected_block_tp = root_first_context.get("active_block_tp")
    expected_block = root_first_context.get("active_block")
    expected_truth = root_first_context.get("current_practical_truth")
    expected_report = root_first_context.get("current_practical_report")
    expected_next_move = root_first_context.get("current_non_negotiable_next_move")
    expected_history_rule = root_first_context.get("historical_residue_rule")

    if truth.get("active_block_tp") != expected_block_tp:
        errors.append("active_block_tp must match docs/RECOVERY_EXECUTION_LOCK.yaml")
    current_truth = truth.get("current_practical_truth")
    if not isinstance(current_truth, dict):
        errors.append("current_practical_truth must remain a mapping")
    else:
        if current_truth.get("label") != expected_truth:
            errors.append("current_practical_truth.label must match docs/RECOVERY_EXECUTION_LOCK.yaml")
        if current_truth.get("report") != expected_report:
            errors.append("current_practical_truth.report must match docs/RECOVERY_EXECUTION_LOCK.yaml")
    if truth.get("current_non_negotiable_next_move") != expected_next_move:
        errors.append("current_non_negotiable_next_move must match docs/RECOVERY_EXECUTION_LOCK.yaml")

    execution_strategy = truth.get("execution_strategy")
    if not isinstance(execution_strategy, dict):
        errors.append("execution_strategy section must be a mapping")
    elif execution_strategy.get("current_nonnegotiable_next_move") != expected_next_move:
        errors.append("execution_strategy.current_nonnegotiable_next_move must match docs/RECOVERY_EXECUTION_LOCK.yaml")

    program = truth.get("program")
    if not isinstance(program, dict):
        errors.append("program section must be a mapping")
    else:
        if program.get("current_block") != expected_block:
            errors.append("program.current_block must match docs/RECOVERY_EXECUTION_LOCK.yaml")
        if program.get("historical_residue_rule") != expected_history_rule:
            errors.append("program.historical_residue_rule must match docs/RECOVERY_EXECUTION_LOCK.yaml")

    phase_advance = lock.get("phase_advance")
    if not isinstance(phase_advance, dict) or not _is_non_empty_string(phase_advance.get("waiver_file")):
        errors.append("recovery execution lock must define phase_advance.waiver_file")
    else:
        waiver_path = root / str(phase_advance["waiver_file"]).strip()
        if not waiver_path.exists():
            errors.append(f"recovery execution waiver path does not exist: {phase_advance['waiver_file']}")

    return errors


def validate_source_of_truth(root: Path, truth: dict[str, Any], legacy: dict[str, Any]) -> None:
    errors = collect_source_of_truth_errors(root, truth, legacy)
    errors.extend(collect_governance_registry_errors(root, truth))
    errors.extend(collect_recovery_execution_lock_errors(root, truth))
    if errors:
        raise SystemExit("ERROR: " + "\nERROR: ".join(errors))


def build_packet(root: Path, truth: dict[str, Any], legacy: dict[str, Any]) -> dict[str, Any]:
    program = truth["program"]
    recovery_lock = load_yaml(root / truth["recovery_execution_lock"])
    registries = load_machine_readable_governance(root, truth)
    packet = {
        "active_dec": truth["active_dec"],
        "active_master_tp": truth["active_master_tp"],
        "active_block_tp": truth["active_block_tp"],
        "active_canon": truth["active_canon"],
        "source_of_truth_map": {
            "current_non_negotiable_next_move": truth["current_non_negotiable_next_move"],
            "governing_architecture": truth["governing_architecture"],
            "anti_partial_closure_law": truth["anti_partial_closure_law"],
            "authority_recovery_program": truth["authority_recovery_program"],
            "execution_strategy": truth["execution_strategy"],
            "governance_registries": truth["governance_registries"],
            "authority_registry": truth["authority_registry"],
            "compatibility_carrier_inventory": truth["compatibility_carrier_inventory"],
            "dead_surface_registry": truth["dead_surface_registry"],
            "legacy_caller_surface": truth["legacy_caller_surface"],
            "governance_delta": truth["governance_delta"],
            "recovery_execution_lock": truth["recovery_execution_lock"],
            "semantic_owner": truth["semantic_owner"],
            "continuity_owner": truth["continuity_owner"],
            "boundary_owner": truth["boundary_owner"],
            "turn_result_contract": truth["turn_result_contract"],
            "projection_only": truth["projection_only"],
            "proof_only": truth["proof_only"],
            "forbidden_semantic_files": truth["forbidden_semantic_files"],
            "platform_evidence_requirement": truth["platform_evidence_requirement"],
        },
        "machine_readable_governance": registries,
        "recovery_execution_lock_map": recovery_lock,
        "legacy_sunset": legacy,
        "active_master_block": program["current_block"],
        "touch_list_allowed": program["allowed_touch"],
        "touch_list_forbidden": program["forbidden_touch"],
        "required_checks": program["required_checks"],
        "open_blockers": program["open_blockers"],
        "current_runtime_cutover_status": program["runtime_cutover_status"],
        "historical_residue_rule": program["historical_residue_rule"],
    }
    return packet


def render_markdown(packet: dict[str, Any]) -> str:
    cutover = packet["current_runtime_cutover_status"]
    recovery_lock = packet["recovery_execution_lock_map"]
    root_first_context = recovery_lock["root_first_context"]
    current_next_move = packet["source_of_truth_map"]["current_non_negotiable_next_move"]
    governing_architecture = packet["source_of_truth_map"]["governing_architecture"]
    anti_partial_closure_law = packet["source_of_truth_map"]["anti_partial_closure_law"]
    authority_recovery_program = packet["source_of_truth_map"]["authority_recovery_program"]
    execution_strategy = packet["source_of_truth_map"]["execution_strategy"]
    governance_registries = packet["source_of_truth_map"]["governance_registries"]
    authority_registry_path = packet["source_of_truth_map"]["authority_registry"]
    compatibility_registry_path = packet["source_of_truth_map"]["compatibility_carrier_inventory"]
    surface_registry_path = packet["source_of_truth_map"]["dead_surface_registry"]
    legacy_caller_surface_path = packet["source_of_truth_map"]["legacy_caller_surface"]
    governance_delta_path = packet["source_of_truth_map"]["governance_delta"]
    authority_registry = packet["machine_readable_governance"]["authority_registry"]
    compatibility_registry = packet["machine_readable_governance"]["compatibility_carrier_inventory"]
    surface_registry = packet["machine_readable_governance"]["dead_surface_registry"]
    legacy_caller_surface = packet["machine_readable_governance"]["legacy_caller_surface"]
    governance_delta = packet["machine_readable_governance"]["governance_delta"]
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
    lines.append(f"- `{packet['active_canon']}`")
    lines.append(f"- `{packet['active_master_tp']}`")
    lines.append(f"- `{packet['active_block_tp']}`")
    lines.append("- `docs/SOURCE_OF_TRUTH.yaml`")
    lines.append("- `docs/LEGACY_SUNSET.yaml`")
    lines.append("")
    lines.append("## Recovery Execution Lock")
    lines.append(f"- Lock file: `{packet['source_of_truth_map']['recovery_execution_lock']}`")
    lines.append(f"- Active practical truth: `{root_first_context['current_practical_truth']}`")
    lines.append(f"- Active block: `{root_first_context['active_block']}`")
    lines.append(f"- Runtime status: `{root_first_context['runtime_implementation_status']}`")
    lines.append(f"- Next move: `{root_first_context['current_non_negotiable_next_move']}`")
    lines.append(f"- Historical residue rule: `{packet['historical_residue_rule']}`")
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
    lines.append(f"- Current non-negotiable next move: `{current_next_move}`")
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
    lines.append("## Governing Architecture")
    lines.append(f"- Statement: `{governing_architecture['statement']}`")
    lines.append("- Planes:")
    for item in governing_architecture["planes"]:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Anti-Partial-Closure Law")
    lines.append(f"- Summary: {anti_partial_closure_law['summary']}")
    lines.append("- Unacceptable if:")
    for item in anti_partial_closure_law["unacceptable_if"]:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Root-First Recovery Program")
    for item in authority_recovery_program["phases"]:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Authority Base")
    lines.append(
        f"- Authority registry: `{authority_registry_path}` (`{authority_registry['status']}`, {len(authority_registry['entries'])} mechanisms)"
    )
    lines.append(
        f"- Compatibility carrier inventory: `{compatibility_registry_path}` (`{compatibility_registry['status']}`, {len(compatibility_registry['carriers'])} carriers)"
    )
    lines.append(
        f"- Surface topology registry: `{surface_registry_path}` (`{surface_registry['status']}`, {len(surface_registry['entries'])} surfaces)"
    )
    lines.append(
        f"- Legacy caller surface: `{legacy_caller_surface_path}` (`{legacy_caller_surface['status']}`, {len(legacy_caller_surface['entries'])} modules)"
    )
    lines.append(
        f"- Governance delta: `{governance_delta_path}` (`{governance_delta['status']}`, {len(governance_delta['locked_mechanisms'])} locked mechanisms)"
    )
    lines.append("- Source-of-truth governance requirements:")
    for section_name, section in governance_registries.items():
        required_key = next((key for key in section if key.startswith('required_') and key != 'required_status'), None)
        count = len(section.get(required_key, [])) if required_key else 0
        lines.append(
            f"- `{section_name}` -> `{section['required_status']}` with {count} required anchors"
        )
    lines.append("")
    lines.append("## Authority Registry Snapshot")
    lines.append("- Mounted ingress:")
    for item in authority_registry["mounted_runtime_topology"]["mounted_ingress_paths"]:
        lines.append(f"- `{item}`")
    lines.append("- Hot path:")
    for item in authority_registry["mounted_runtime_topology"]["hot_path"]:
        lines.append(f"- `{item}`")
    for entry in authority_registry["entries"]:
        lines.append(
            f"- `{entry['mechanism_id']}` -> next `{entry['next_phase_required']}`, full closure `{entry['full_closure_phase']}`, confidence `{entry['confidence']}`"
        )
    lines.append("")
    lines.append("## Compatibility Carrier Snapshot")
    lines.append("- Canonical owner paths:")
    for item in compatibility_registry["canonical_owner_paths"]:
        lines.append(f"- `{item}`")
    lines.append("- Freeze guard allowed new writer paths:")
    for item in compatibility_registry["freeze_guard"]["allowed_new_writer_paths"]:
        lines.append(f"- `{item}`")
    lines.append(
        f"- Freeze guard token count: `{len(compatibility_registry['freeze_guard']['guarded_context_tokens'])}`"
    )
    for entry in compatibility_registry["carriers"]:
        lines.append(
            f"- `{entry['carrier_id']}` -> `{entry['current_truth_rank']}` / target `{entry['target_fate']}` / phase `{entry['full_closure_phase']}`"
        )
    lines.append("")
    lines.append("## Surface Topology Snapshot")
    lines.append("- Behavior-owning legacy surfaces:")
    for item in surface_registry["caller_proof_law"]["behavior_owning_surfaces"]:
        lines.append(f"- `{item}`")
    lines.append("- Shadow-only surfaces:")
    for item in surface_registry["caller_proof_law"]["shadow_only_surfaces"]:
        lines.append(f"- `{item}`")
    for entry in surface_registry["entries"]:
        lines.append(
            f"- `{entry['surface_path']}` -> `{entry['classification']}` / authority `{entry['authority_mode']}` / hot path `{entry['hot_path_reachable']}` / confidence `{entry['confidence']}`"
        )
    lines.append("")
    lines.append("## Legacy Caller Freeze Snapshot")
    lines.append("- Frozen adapter-only modules:")
    for item in legacy_caller_surface["freeze_policy"]["frozen_adapter_only_modules"]:
        lines.append(f"- `{item}`")
    lines.append("- Shadow or wrapper candidates:")
    for item in legacy_caller_surface["freeze_policy"]["shadow_or_wrapper_candidates"]:
        lines.append(f"- `{item}`")
    for entry in legacy_caller_surface["entries"]:
        lines.append(
            f"- `{entry['module_path']}` -> `{entry['freeze_mode']}` / pressure `{entry['mechanism_pressure']}` / live callers `{len(entry['live_runtime_callers'])}` / app importers `{len(entry['static_app_importers'])}`"
        )
    lines.append("")
    lines.append("## Governance Delta Snapshot")
    lines.append(f"- Summary: {governance_delta['delta_summary']}")
    lines.append("- Locked mechanisms:")
    for item in governance_delta["locked_mechanisms"]:
        lines.append(f"- `{item}`")
    lines.append("- Deferred next blocks:")
    for item in governance_delta["deferred_next_blocks"]:
        lines.append(f"- `{item}`")
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
    packet = build_packet(root, truth, legacy)

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
