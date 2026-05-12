from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GUARD_PATH = ROOT / "scripts" / "decision_ledger_guard.py"


def _load_guard():
    spec = importlib.util.spec_from_file_location("decision_ledger_guard", GUARD_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_decision_ledger_guard_passes_current_repo() -> None:
    guard = _load_guard()

    assert guard.collect_decision_ledger_errors(ROOT) == []


def test_decision_ledger_guard_requires_required_entry(tmp_path: Path) -> None:
    guard = _load_guard()
    docs = tmp_path / "docs"
    scripts = tmp_path / "scripts"
    tests = tmp_path / "truffles-api" / "tests" / "architecture"
    docs.mkdir(parents=True)
    scripts.mkdir(parents=True)
    tests.mkdir(parents=True)
    (docs / "DECISION_LEDGER.yaml").write_text(
        "version: 1\n"
        "entry_required_for:\n"
        "  - mechanism_change\n"
        "entries: []\n",
        encoding="utf-8",
    )
    (docs / "PRODUCT_SYSTEM_CANON.md").write_text("", encoding="utf-8")
    (docs / "BEAUTY_SALON_V1_CAPABILITY_MAP.md").write_text("", encoding="utf-8")
    (docs / "SESSION_START_PROMPT.txt").write_text("", encoding="utf-8")
    (tmp_path / "TECH.md").write_text("", encoding="utf-8")
    (tmp_path / "STRUCTURE.md").write_text("", encoding="utf-8")

    errors = guard.collect_decision_ledger_errors(tmp_path)

    assert "ledger entries must be a non-empty list" in errors
    assert "ledger missing required current entry: DL-2026-05-03-001" in errors
    assert "ledger missing required current entry: DL-2026-05-03-002" in errors
    assert "ledger missing required current entry: DL-2026-05-03-003" in errors
    assert "ledger missing required current entry: DL-2026-05-03-004" in errors
    assert "ledger missing required current entry: DL-2026-05-05-010" in errors
    assert "ledger missing required current entry: DL-2026-05-07-011" in errors
    assert "ledger missing required current entry: DL-2026-05-07-012" in errors
    assert "ledger missing required current entry: DL-2026-05-07-013" in errors
    assert "ledger missing entry trigger: proof_downgrade_or_invalidation" in errors


def test_decision_ledger_guard_blocks_stale_product_claim(tmp_path: Path) -> None:
    guard = _load_guard()
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "DECISION_LEDGER.yaml").write_text(
        "version: 1\n"
        "entry_required_for:\n"
        "  - mechanism_change\n"
        "  - architecture_decision\n"
        "  - blocker_open_close_reclassify\n"
        "  - tool_or_script_creation_change\n"
        "  - product_status_change\n"
        "  - proof_downgrade_or_invalidation\n"
        "entries:\n"
        "  - id: DL-2026-05-03-001\n"
        "    date: 2026-05-03\n"
        "    capability: BSV1-04\n"
        "    architecture_layer: Process Governance\n"
        "    problem: scripted proof overstated\n"
        "    decision: SCRIPTED_TECHNICAL_PROOF not REAL_WORLD_PRODUCT_PROOF; Real-World Salon Acceptance Pack with owner-approved messy dialogs\n"
        "    classification: REPAIR\n"
        "    changed_files: [docs/PRODUCT_SYSTEM_CANON.md]\n"
        "    proof_artifacts: [real internal appointments]\n"
        "    validation: [guard]\n"
        "    known_limits: [owner-approved messy dialogs missing]\n"
        "    do_not_repeat: [do not overclaim]\n"
        "    next_allowed_action: Real-World Salon Acceptance Pack\n",
        encoding="utf-8",
    )
    (docs / "PRODUCT_SYSTEM_CANON.md").write_text(
        "## Decision & Action Ledger — 2026-05-03\n"
        "docs/DECISION_LEDGER.yaml\n"
        "DL-2026-05-03-001\n"
        "SCRIPTED_TECHNICAL_PROOF\n"
        "REAL_WORLD_PRODUCT_PROOF\n"
        "Real-World Salon Acceptance Pack\n"
        "owner-approved messy dialogs\n"
        "| Realistic Booking Matrix Closure | `PROVEN` |\n",
        encoding="utf-8",
    )
    (docs / "BEAUTY_SALON_V1_CAPABILITY_MAP.md").write_text("", encoding="utf-8")
    (docs / "SESSION_START_PROMPT.txt").write_text("", encoding="utf-8")
    (tmp_path / "TECH.md").write_text(
        "`scripts/decision_ledger_guard.py`\n"
        "`truffles-api/tests/architecture/test_decision_ledger_guard.py`\n",
        encoding="utf-8",
    )
    (tmp_path / "STRUCTURE.md").write_text("", encoding="utf-8")

    errors = guard.collect_decision_ledger_errors(tmp_path)

    assert (
        "stale real-world product proof claim remains: "
        "| Realistic Booking Matrix Closure | `PROVEN` |"
    ) in errors


def test_decision_ledger_guard_requires_internal_pilot_terms(tmp_path: Path) -> None:
    guard = _load_guard()
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "DECISION_LEDGER.yaml").write_text(
        "version: 1\n"
        "entry_required_for:\n"
        "  - mechanism_change\n"
        "  - architecture_decision\n"
        "  - blocker_open_close_reclassify\n"
        "  - tool_or_script_creation_change\n"
        "  - product_status_change\n"
        "  - proof_downgrade_or_invalidation\n"
        "entries:\n"
        "  - id: DL-2026-05-03-001\n"
        "    date: 2026-05-03\n"
        "    capability: BSV1-04\n"
        "    architecture_layer: Process Governance\n"
        "    problem: scripted proof overstated\n"
        "    decision: SCRIPTED_TECHNICAL_PROOF not REAL_WORLD_PRODUCT_PROOF; Real-World Salon Acceptance Pack with owner-approved messy dialogs\n"
        "    classification: REPAIR\n"
        "    changed_files: [docs/PRODUCT_SYSTEM_CANON.md]\n"
        "    proof_artifacts: [real internal appointments]\n"
        "    validation: [guard]\n"
        "    known_limits: [owner-approved messy dialogs missing]\n"
        "    do_not_repeat: [do not overclaim]\n"
        "    next_allowed_action: Real-World Salon Acceptance Pack\n"
        "  - id: DL-2026-05-03-002\n"
        "    date: 2026-05-03\n"
        "    capability: BSV1-04\n"
        "    architecture_layer: Quality Evidence\n"
        "    problem: fail-first LLM runs hide families\n"
        "    decision: Internal Pilot Proof with owner-reviewed synthetic messy corpus\n"
        "    classification: REPAIR\n"
        "    changed_files: [docs/PRODUCT_SYSTEM_CANON.md]\n"
        "    proof_artifacts: [candidate corpus]\n"
        "    validation: [guard]\n"
        "    known_limits: [not production transcripts]\n"
        "    do_not_repeat: [do not patch one row first]\n"
        "    next_allowed_action: run diagnostics\n",
        encoding="utf-8",
    )
    (docs / "PRODUCT_SYSTEM_CANON.md").write_text(
        "## Decision & Action Ledger — 2026-05-03\n"
        "docs/DECISION_LEDGER.yaml\n"
        "DL-2026-05-03-001\n"
        "DL-2026-05-03-002\n"
        "SCRIPTED_TECHNICAL_PROOF\n"
        "REAL_WORLD_PRODUCT_PROOF\n"
        "Real-World Salon Acceptance Pack\n"
        "owner-approved messy dialogs\n"
        "Internal Pilot Proof\n"
        "Exploration lane\n"
        "owner-reviewed synthetic messy corpus\n"
        "behavioral failures do not stop run\n"
        "invalid-run\n"
        "failure-family map\n",
        encoding="utf-8",
    )
    (docs / "BEAUTY_SALON_V1_CAPABILITY_MAP.md").write_text("", encoding="utf-8")
    (docs / "SESSION_START_PROMPT.txt").write_text("", encoding="utf-8")
    (tmp_path / "TECH.md").write_text(
        "`scripts/decision_ledger_guard.py`\n"
        "`truffles-api/tests/architecture/test_decision_ledger_guard.py`\n",
        encoding="utf-8",
    )
    (tmp_path / "STRUCTURE.md").write_text("", encoding="utf-8")

    errors = guard.collect_decision_ledger_errors(tmp_path)

    assert (
        "ledger entry DL-2026-05-03-002 missing term: "
        "behavioral failures do not stop run"
    ) in errors
    assert "ledger entry DL-2026-05-03-002 missing term: invalid-run" in errors
    assert "ledger entry DL-2026-05-03-002 missing term: failure-family map" in errors
