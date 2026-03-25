from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_agent_packet_and_top_level_consistency() -> None:
    build_agent_packet = load_module("build_agent_packet", SCRIPTS / "build_agent_packet.py")
    arch_guard = load_module("arch_guard", SCRIPTS / "arch_guard.py")

    truth = build_agent_packet.load_yaml(ROOT / "docs" / "SOURCE_OF_TRUTH.yaml")
    legacy = build_agent_packet.load_yaml(ROOT / "docs" / "LEGACY_SUNSET.yaml")
    build_agent_packet.validate_source_of_truth(ROOT, truth, legacy)
    packet = build_agent_packet.build_packet(truth, legacy)
    markdown = build_agent_packet.render_markdown(packet)

    assert packet["active_dec"].endswith("controlled-demolition.md")
    assert (
        packet["active_block_tp"]
        == "docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-reentry-initial-booking-invalid-schema-authority-reset-structural-implementation-a922.md"
    )
    assert (
        packet["active_master_block"]
        == "Consultant Core Pending Booking Reentry Initial Booking Invalid Schema Authority Reset Structural Implementation"
    )
    assert packet["source_of_truth_map"]["execution_strategy"]["mode"] == "owner_replacement_not_bridge_growth"
    assert (
        packet["source_of_truth_map"]["execution_strategy"]["current_nonnegotiable_next_move"]
        == "run_one_fresh_closure_replay_only_after_pending_booking_reentry_initial_booking_invalid_schema_authority_reset_evidence"
    )
    assert "## Execution Strategy Lock" in markdown
    assert "new_generic_ingress_phrase_bridge_family" in markdown
    assert "AGENT PACKET" in markdown
    assert arch_guard.validate_top_level_consistency(ROOT, truth, legacy) == []
