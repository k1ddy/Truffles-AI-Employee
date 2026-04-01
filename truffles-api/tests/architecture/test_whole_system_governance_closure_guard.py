from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repo_whole_system_governance_closure_guard_matches_current_repo() -> None:
    module = load_module("whole_system_governance_closure_guard", SCRIPTS / "whole_system_governance_closure_guard.py")
    assert module.collect_errors(ROOT) == []


def test_governance_closure_guard_rejects_wrong_authority_next_phase(tmp_path: Path) -> None:
    module = load_module("whole_system_governance_closure_guard", SCRIPTS / "whole_system_governance_closure_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "docs" / "system_forensics").mkdir(parents=True)

    config = yaml.safe_load((ROOT / "docs" / "WHOLE_SYSTEM_GOVERNANCE_CLOSURE_GUARD.yaml").read_text(encoding="utf-8"))
    (repo / "docs" / "WHOLE_SYSTEM_GOVERNANCE_CLOSURE_GUARD.yaml").write_text(
        yaml.safe_dump(config), encoding="utf-8"
    )
    (repo / "docs" / "SOURCE_OF_TRUTH.yaml").write_text(
        yaml.safe_dump(
            {
                "active_block_tp": config["active_block_tp"],
                "current_non_negotiable_next_move": config["next_move"],
                "program": {
                    "current_block": config["active_block"],
                    "open_blockers": config["required_program_open_blockers"],
                },
            }
        ),
        encoding="utf-8",
    )
    authority = {
        "status": "machine_readable_whole_system_governance_closure_base",
        "active_block": config["active_block"],
        "entries": [{"mechanism_id": "semantic_turn_meaning", "next_phase_required": "wrong"}],
    }
    for name, payload in {
        "authority_registry.json": authority,
        "compatibility_carrier_inventory.json": {
            "status": "machine_readable_whole_system_governance_closure_base",
            "active_block": config["active_block"],
        },
        "dead_surface_registry.json": {
            "status": "machine_readable_whole_system_governance_closure_base",
            "active_block": config["active_block"],
        },
        "legacy_caller_surface.json": {
            "status": "machine_readable_whole_system_governance_closure_base",
            "active_block": config["active_block"],
        },
        "governance_delta.json": {
            "status": "machine_readable_governance_closure_delta_base",
            "active_block": config["active_block"],
            "deferred_next_blocks": config["required_deferred_next_blocks"],
        },
    }.items():
        (repo / "docs" / "system_forensics" / name).write_text(json.dumps(payload), encoding="utf-8")

    violations = module.collect_errors(repo)
    assert violations
    assert any("semantic_turn_meaning" in item for item in violations)


def test_governance_closure_guard_rejects_wrong_deferred_next_blocks(tmp_path: Path) -> None:
    module = load_module("whole_system_governance_closure_guard", SCRIPTS / "whole_system_governance_closure_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "docs" / "system_forensics").mkdir(parents=True)

    config = yaml.safe_load((ROOT / "docs" / "WHOLE_SYSTEM_GOVERNANCE_CLOSURE_GUARD.yaml").read_text(encoding="utf-8"))
    (repo / "docs" / "WHOLE_SYSTEM_GOVERNANCE_CLOSURE_GUARD.yaml").write_text(
        yaml.safe_dump(config), encoding="utf-8"
    )
    (repo / "docs" / "SOURCE_OF_TRUTH.yaml").write_text(
        yaml.safe_dump(
            {
                "active_block_tp": config["active_block_tp"],
                "current_non_negotiable_next_move": config["next_move"],
                "program": {
                    "current_block": config["active_block"],
                    "open_blockers": config["required_program_open_blockers"],
                },
            }
        ),
        encoding="utf-8",
    )
    good_entry = {"mechanism_id": "semantic_turn_meaning", "next_phase_required": config["required_authority_next_phase"]}
    for name, payload in {
        "authority_registry.json": {
            "status": "machine_readable_whole_system_governance_closure_base",
            "active_block": config["active_block"],
            "entries": [good_entry],
        },
        "compatibility_carrier_inventory.json": {
            "status": "machine_readable_whole_system_governance_closure_base",
            "active_block": config["active_block"],
        },
        "dead_surface_registry.json": {
            "status": "machine_readable_whole_system_governance_closure_base",
            "active_block": config["active_block"],
        },
        "legacy_caller_surface.json": {
            "status": "machine_readable_whole_system_governance_closure_base",
            "active_block": config["active_block"],
        },
        "governance_delta.json": {
            "status": "machine_readable_governance_closure_delta_base",
            "active_block": config["active_block"],
            "deferred_next_blocks": ["wrong"],
        },
    }.items():
        (repo / "docs" / "system_forensics" / name).write_text(json.dumps(payload), encoding="utf-8")

    violations = module.collect_errors(repo)
    assert violations
    assert any("deferred_next_blocks" in item for item in violations)
