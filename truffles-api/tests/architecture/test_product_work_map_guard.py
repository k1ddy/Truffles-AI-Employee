from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GUARD_PATH = ROOT / "scripts" / "product_work_map_guard.py"


def _load_guard():
    spec = importlib.util.spec_from_file_location("product_work_map_guard", GUARD_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_product_work_map_guard_passes_current_repo() -> None:
    guard = _load_guard()

    assert guard.collect_work_map_errors(ROOT) == []


def test_product_work_map_guard_blocks_stale_open_status(tmp_path: Path) -> None:
    guard = _load_guard()
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "PRODUCT_SYSTEM_CANON.md").write_text(
        "## Verified Product Work Map — 2026-05-01\n"
        "| Block | Status | Evidence | Decision |\n"
        "|---|---|---|---|\n"
        "| Console Lifecycle Acceptance Proof | `PROVEN` | proof | done |\n"
        "| Booking Matrix Closure | `PARTIAL_MECHANISM_PROVEN` | proof | realistic booking still open |\n"
        "| Observability End-To-End Turn Proof | `PROVEN` | proof | done |\n"
        "| Provider/Channel Readiness Proof | `BLOCKED_NON_CODE` | proof | blocked |\n"
        "| Beauty Salon v1 Go-Live | `PARTIAL_NOT_GO_LIVE` | proof | partial |\n"
        "No-repeat governance closure\n"
        "Shadow side-service removal\n"
        "Provider/channel proof only after commercial access is restored\n"
        "fresh dated regression artifact\n"
        "Next product block remains `Observability End-To-End Turn Proof`\n",
        encoding="utf-8",
    )
    (docs / "BEAUTY_SALON_V1_CAPABILITY_MAP.md").write_text(
        "## Verified Readiness Snapshot — 2026-05-01\n",
        encoding="utf-8",
    )
    (docs / "SESSION_START_PROMPT.txt").write_text(
        "scripts/product_work_map_guard.py\n",
        encoding="utf-8",
    )

    errors = guard.collect_work_map_errors(tmp_path)

    assert (
        "stale open-blocker phrase remains: "
        "Next product block remains `Observability End-To-End Turn Proof`"
    ) in errors


def test_product_work_map_guard_blocks_stale_booking_proven_status(tmp_path: Path) -> None:
    guard = _load_guard()
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "PRODUCT_SYSTEM_CANON.md").write_text(
        "## Verified Product Work Map — 2026-05-01\n"
        "| Block | Status | Evidence | Decision |\n"
        "|---|---|---|---|\n"
        "| Console Lifecycle Acceptance Proof | `PROVEN` | proof | done |\n"
        "| Booking Matrix Closure | `PROVEN` | proof | done |\n",
        encoding="utf-8",
    )
    (docs / "BEAUTY_SALON_V1_CAPABILITY_MAP.md").write_text("", encoding="utf-8")
    (docs / "CONSOLE_PLANE_ACCEPTANCE_MAP.md").write_text("", encoding="utf-8")
    (docs / "SESSION_START_PROMPT.txt").write_text("", encoding="utf-8")
    (tmp_path / "TECH.md").write_text("", encoding="utf-8")

    errors = guard.collect_work_map_errors(tmp_path)

    assert (
        "missing verified work-map status: "
        "Booking Matrix Closure = `PARTIAL_MECHANISM_PROVEN`"
    ) in errors
    assert "stale open-blocker phrase remains: | Booking Matrix Closure | `PROVEN` |" in errors


def test_product_work_map_guard_requires_architecture_handoff_target(tmp_path: Path) -> None:
    guard = _load_guard()
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "PRODUCT_SYSTEM_CANON.md").write_text(
        "## Verified Product Work Map — 2026-05-01\n"
        "| Block | Status | Evidence | Decision |\n"
        "|---|---|---|---|\n"
        "| Console Lifecycle Acceptance Proof | `PROVEN` | proof | done |\n"
        "| Booking Matrix Closure | `PARTIAL_MECHANISM_PROVEN` | proof | realistic booking still open |\n"
        "| Observability End-To-End Turn Proof | `PROVEN` | proof | done |\n"
        "| Provider/Channel Readiness Proof | `BLOCKED_NON_CODE` | proof | blocked |\n"
        "| Beauty Salon v1 Go-Live | `PARTIAL_NOT_GO_LIVE` | proof | partial |\n"
        "No-repeat governance closure\n"
        "Provider/channel proof only after commercial access is restored\n"
        "Shadow side-service removal\n"
        "fresh dated regression artifact\n",
        encoding="utf-8",
    )
    (docs / "BEAUTY_SALON_V1_CAPABILITY_MAP.md").write_text(
        "## Verified Readiness Snapshot — 2026-05-01\n",
        encoding="utf-8",
    )
    (docs / "CONSOLE_PLANE_ACCEPTANCE_MAP.md").write_text(
        "### 5.6 Console Lifecycle Acceptance Proof — 2026-04-29\n",
        encoding="utf-8",
    )
    (docs / "SESSION_START_PROMPT.txt").write_text(
        "scripts/product_work_map_guard.py\n",
        encoding="utf-8",
    )
    (tmp_path / "TECH.md").write_text("", encoding="utf-8")

    errors = guard.collect_work_map_errors(tmp_path)

    assert "missing architecture handoff baseline in canon" in errors
    assert "missing architecture handoff closure in canon" in errors
    assert (
        "missing process optimization closure in canon: "
        "Process Optimization Closure — 2026-05-02"
    ) in errors
    assert (
        "missing shadow removal dependency proof in canon: "
        "Shadow Removal Dependency Proof — 2026-05-02"
    ) in errors
    assert (
        "missing shadow side-service removal in canon: "
        "Shadow Side-Service Removal — 2026-05-02"
    ) in errors
    assert "missing superseded marker for historical short-term dependency order" in errors
    assert "missing architecture handoff closed status" in errors
    assert "missing architecture handoff baseline in TECH.md" in errors
    assert "missing architecture handoff closure in TECH.md" in errors
    assert "missing process optimization closure in TECH.md" in errors
    assert "missing shadow removal dependency proof in TECH.md" in errors
    assert "missing shadow side-service removal in TECH.md" in errors
    assert "missing Provider Gateway shadow authority closure section" in errors
    assert "missing remaining side services shadow authority closure section" in errors
    assert "missing shadow authority static guard closure section" in errors
    assert "missing shadow service lifecycle decision section" in errors
    assert "missing shadow stopped-or-disabled observability section" in errors
    assert "missing shadow stopped-or-disabled observability decision" in errors


def test_product_work_map_guard_blocks_stale_handoff_in_progress(tmp_path: Path) -> None:
    guard = _load_guard()
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "PRODUCT_SYSTEM_CANON.md").write_text(
        "## Verified Product Work Map — 2026-05-01\n"
        "## Architecture Consolidation / Handoff Baseline — 2026-05-01\n"
        "Status: `IN_PROGRESS_HANDOFF_BASELINE`.\n"
        "## Architecture Consolidation / Handoff Closure — 2026-05-02\n"
        "Status: `ARCHITECTURE_HANDOFF_CLOSED`.\n"
        "## Process Optimization Closure — 2026-05-02\n"
        "Status: `PROCESS_OPTIMIZED_AND_GUARDED`.\n"
        "One active product block at a time\n"
        "Docs update is an output of proof, not a substitute for proof\n"
        "Validation tiers\n"
        "T0 Reality\n"
        "T1 Touched Slice\n"
        "T2 Governance\n"
        "T3 Live Truth\n"
        "T4 Architecture Gate\n"
        "## Shadow Removal Dependency Proof — 2026-05-02\n"
        "Status: `SHADOW_REMOVAL_DEPENDENCY_PROVEN`.\n"
        "scripts/shadow_removal_dependency_truth.py\n"
        "removal_ready_for_later_block\n"
        "Shadow side-service removal block\n"
        "## Shadow Side-Service Removal — 2026-05-02\n"
        "Status: `SHADOW_SIDE_SERVICES_REMOVED`.\n"
        "canonical `/provider/*` and `/knowledge/snapshot`\n"
        "do not recreate removed side services\n"
        "## Historical short-term dependency order — superseded\n"
        "| Console Lifecycle Acceptance Proof | `PROVEN` |\n"
        "| Booking Matrix Closure | `PARTIAL_MECHANISM_PROVEN` |\n"
        "| Observability End-To-End Turn Proof | `PROVEN` |\n"
        "| Provider/Channel Readiness Proof | `BLOCKED_NON_CODE` |\n"
        "| Beauty Salon v1 Go-Live | `PARTIAL_NOT_GO_LIVE` |\n"
        "No-repeat governance closure\n"
        "Shadow side-service removal\n"
        "Provider/channel proof only after commercial access is restored\n"
        "fresh dated regression artifact\n"
        "Shadow/Authority Drain Closure — Provider Gateway First Slice — 2026-05-01\n"
        "Shadow/Authority Drain Closure — Remaining Side Services — 2026-05-01\n"
        "Shadow/Authority Drain Closure — Static Guard — 2026-05-02\n"
        "Shadow Service Lifecycle Decision — 2026-05-02\n"
        "Shadow Stopped-Or-Disabled Observability — 2026-05-02\n"
        "STOPPED_OR_DISABLED_OBSERVABILITY_PROVEN\n",
        encoding="utf-8",
    )
    (docs / "BEAUTY_SALON_V1_CAPABILITY_MAP.md").write_text(
        "## Verified Readiness Snapshot — 2026-05-01\n",
        encoding="utf-8",
    )
    (docs / "CONSOLE_PLANE_ACCEPTANCE_MAP.md").write_text(
        "### 5.6 Console Lifecycle Acceptance Proof — 2026-04-29\n",
        encoding="utf-8",
    )
    (docs / "SESSION_START_PROMPT.txt").write_text(
        "scripts/product_work_map_guard.py\n"
        "One active product block at a time\n"
        "Docs update is an output of proof, not a substitute for proof\n",
        encoding="utf-8",
    )
    (tmp_path / "TECH.md").write_text(
        "Architecture handoff baseline — 2026-05-01\n"
        "Architecture handoff closure — 2026-05-02\n"
        "Process optimization closure — 2026-05-02\n"
        "Shadow removal dependency proof — 2026-05-02\n"
        "Shadow side-service removal — 2026-05-02\n",
        encoding="utf-8",
    )

    errors = guard.collect_work_map_errors(tmp_path)

    assert "stale architecture handoff in-progress status remains" in errors


def test_product_work_map_guard_requires_shadow_removal_dependency_proof(tmp_path: Path) -> None:
    guard = _load_guard()
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "PRODUCT_SYSTEM_CANON.md").write_text(
        "## Verified Product Work Map — 2026-05-01\n"
        "## Architecture Consolidation / Handoff Baseline — 2026-05-01\n"
        "## Architecture Consolidation / Handoff Closure — 2026-05-02\n"
        "Status: `ARCHITECTURE_HANDOFF_CLOSED`.\n"
        "## Process Optimization Closure — 2026-05-02\n"
        "Status: `PROCESS_OPTIMIZED_AND_GUARDED`.\n"
        "One active product block at a time\n"
        "Docs update is an output of proof, not a substitute for proof\n"
        "Validation tiers\n"
        "T0 Reality\n"
        "T1 Touched Slice\n"
        "T2 Governance\n"
        "T3 Live Truth\n"
        "T4 Architecture Gate\n"
        "## Historical short-term dependency order — superseded\n"
        "| Console Lifecycle Acceptance Proof | `PROVEN` |\n"
        "| Booking Matrix Closure | `PARTIAL_MECHANISM_PROVEN` |\n"
        "| Observability End-To-End Turn Proof | `PROVEN` |\n"
        "| Provider/Channel Readiness Proof | `BLOCKED_NON_CODE` |\n"
        "| Beauty Salon v1 Go-Live | `PARTIAL_NOT_GO_LIVE` |\n"
        "No-repeat governance closure\n"
        "Shadow side-service removal\n"
        "Provider/channel proof only after commercial access is restored\n"
        "fresh dated regression artifact\n"
        "Shadow/Authority Drain Closure — Provider Gateway First Slice — 2026-05-01\n"
        "Shadow/Authority Drain Closure — Remaining Side Services — 2026-05-01\n"
        "Shadow/Authority Drain Closure — Static Guard — 2026-05-02\n"
        "Shadow Service Lifecycle Decision — 2026-05-02\n"
        "Shadow Stopped-Or-Disabled Observability — 2026-05-02\n"
        "STOPPED_OR_DISABLED_OBSERVABILITY_PROVEN\n",
        encoding="utf-8",
    )
    (docs / "BEAUTY_SALON_V1_CAPABILITY_MAP.md").write_text(
        "## Verified Readiness Snapshot — 2026-05-01\n",
        encoding="utf-8",
    )
    (docs / "CONSOLE_PLANE_ACCEPTANCE_MAP.md").write_text(
        "### 5.6 Console Lifecycle Acceptance Proof — 2026-04-29\n",
        encoding="utf-8",
    )
    (docs / "SESSION_START_PROMPT.txt").write_text(
        "scripts/product_work_map_guard.py\n"
        "One active product block at a time\n"
        "Docs update is an output of proof, not a substitute for proof\n",
        encoding="utf-8",
    )
    (tmp_path / "TECH.md").write_text(
        "Architecture handoff baseline — 2026-05-01\n"
        "Architecture handoff closure — 2026-05-02\n"
        "Process optimization closure — 2026-05-02\n"
        "Shadow/Authority Drain Closure\n"
        "Shadow side-service removal — 2026-05-02\n",
        encoding="utf-8",
    )

    errors = guard.collect_work_map_errors(tmp_path)

    assert (
        "missing shadow removal dependency proof in canon: "
        "Shadow Removal Dependency Proof — 2026-05-02"
    ) in errors
    assert "missing shadow removal dependency proof in TECH.md" in errors
    assert "missing shadow removal dependency term: SHADOW_REMOVAL_DEPENDENCY_PROVEN" in errors
    assert "missing shadow removal dependency term: scripts/shadow_removal_dependency_truth.py" in errors
    assert "missing shadow removal dependency term: removal_ready_for_later_block" in errors
    assert "missing shadow removal dependency term: Shadow side-service removal block" in errors


def test_product_work_map_guard_requires_process_optimization_closure(tmp_path: Path) -> None:
    guard = _load_guard()
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "PRODUCT_SYSTEM_CANON.md").write_text(
        "## Verified Product Work Map — 2026-05-01\n"
        "## Architecture Consolidation / Handoff Baseline — 2026-05-01\n"
        "## Architecture Consolidation / Handoff Closure — 2026-05-02\n"
        "Status: `ARCHITECTURE_HANDOFF_CLOSED`.\n"
        "## Historical short-term dependency order — superseded\n"
        "| Console Lifecycle Acceptance Proof | `PROVEN` |\n"
        "| Booking Matrix Closure | `PARTIAL_MECHANISM_PROVEN` |\n"
        "| Observability End-To-End Turn Proof | `PROVEN` |\n"
        "| Provider/Channel Readiness Proof | `BLOCKED_NON_CODE` |\n"
        "| Beauty Salon v1 Go-Live | `PARTIAL_NOT_GO_LIVE` |\n"
        "No-repeat governance closure\n"
        "Shadow side-service removal\n"
        "Provider/channel proof only after commercial access is restored\n"
        "fresh dated regression artifact\n"
        "Shadow/Authority Drain Closure — Provider Gateway First Slice — 2026-05-01\n"
        "Shadow/Authority Drain Closure — Remaining Side Services — 2026-05-01\n"
        "Shadow/Authority Drain Closure — Static Guard — 2026-05-02\n"
        "Shadow Service Lifecycle Decision — 2026-05-02\n"
        "Shadow Stopped-Or-Disabled Observability — 2026-05-02\n"
        "STOPPED_OR_DISABLED_OBSERVABILITY_PROVEN\n",
        encoding="utf-8",
    )
    (docs / "BEAUTY_SALON_V1_CAPABILITY_MAP.md").write_text(
        "## Verified Readiness Snapshot — 2026-05-01\n",
        encoding="utf-8",
    )
    (docs / "CONSOLE_PLANE_ACCEPTANCE_MAP.md").write_text(
        "### 5.6 Console Lifecycle Acceptance Proof — 2026-04-29\n",
        encoding="utf-8",
    )
    (docs / "SESSION_START_PROMPT.txt").write_text(
        "scripts/product_work_map_guard.py\n",
        encoding="utf-8",
    )
    (tmp_path / "TECH.md").write_text(
        "Architecture handoff baseline — 2026-05-01\n"
        "Architecture handoff closure — 2026-05-02\n"
        "Shadow side-service removal — 2026-05-02\n",
        encoding="utf-8",
    )

    errors = guard.collect_work_map_errors(tmp_path)

    assert (
        "missing process optimization closure in canon: "
        "Process Optimization Closure — 2026-05-02"
    ) in errors
    assert "missing process optimization closure in TECH.md" in errors
    assert "missing process optimization term: PROCESS_OPTIMIZED_AND_GUARDED" in errors
    assert "missing process optimization term: One active product block at a time" in errors
    assert (
        "missing process optimization term: "
        "Docs update is an output of proof, not a substitute for proof"
    ) in errors
