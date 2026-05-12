#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


VERIFIED_WORK_MAP_TITLE = "Verified Product Work Map — 2026-05-01"
PROCESS_OPTIMIZATION_TITLE = "Process Optimization Closure — 2026-05-02"
SHADOW_REMOVAL_DEPENDENCY_TITLE = "Shadow Removal Dependency Proof — 2026-05-02"
SHADOW_SIDE_SERVICE_REMOVAL_TITLE = "Shadow Side-Service Removal — 2026-05-02"

REQUIRED_STATUS_LINES = {
    "Console Lifecycle Acceptance Proof": "`PROVEN`",
    "Booking Matrix Closure": "`PARTIAL_MECHANISM_PROVEN`",
    "Realistic Booking Matrix Closure": "`SCRIPTED_TECHNICAL_PROOF`",
    "Observability End-To-End Turn Proof": "`PROVEN`",
    "Provider/Channel Readiness Proof": "`BLOCKED_NON_CODE`",
    "Beauty Salon v1 Go-Live": "`PARTIAL_NOT_GO_LIVE`",
}

REQUIRED_NEXT_WORK_TERMS = (
    "No-repeat governance closure",
    "No-repeat governance maintenance",
    "Provider/channel proof only after commercial access is restored",
    "Final Beauty Salon v1 Go-Live Review",
    "fresh dated regression artifact",
    "Decision & Action Ledger",
    "Real-World Salon Acceptance Pack",
    "Internal Pilot Proof",
    "Exploration lane",
    "owner-reviewed synthetic messy corpus",
    "behavioral failures do not stop run",
    "invalid-run",
    "failure-family map",
    "Single-Turn Decision/Data Ownership Audit",
    "decision path + data ownership path",
    "Customer Data Contract",
)

STALE_OPEN_BLOCKER_PHRASES = (
    "still need correlated end-to-end product proof",
    "go-live still needs correlated end-to-end turn evidence",
    "Next product block remains `Observability End-To-End Turn Proof`",
    "Booking runtime | previous work proves slices, but not whole representative matrix closure",
    "Console lifecycle | surfaces exist, but role/tenant/state/audit lifecycle proof is not complete",
    "Current Beauty Salon v1 blockers must therefore be treated in this order of dependency:",
    "Console still needs lifecycle/role/audit proof before product closure",
    "- Owner/Admin role proof;",
    "booking runtime matrix closure with `raw owner = green`, `final runtime = green`, `rescue = no`;",
    "| Booking Matrix Closure | `PROVEN` |",
    "representative matrix proof is `PROVEN`",
    "do not restart booking closure as a next block",
    "Do not restart booking closure as next block",
    "Booking runtime | representative D1 matrix is proven",
    "`BSV1-04` is closed for the recorded D1 matrix",
    "Do not reopen Console Lifecycle, Booking Matrix, or Observability E2E",
    "Console Lifecycle, Booking Matrix, and Observability E2E are not valid next blocks",
    "| Realistic Booking Matrix Closure | `BLOCKED_NOT_CLOSED` |",
    "Realistic Booking Matrix live result is `REALISTIC_BOOKING_MATRIX_BLOCKED_NOT_CLOSED`",
    "repair shared booking semantics for `Realistic Booking Matrix Closure`",
    "critical pass is `2/12`",
    "critical pass rate is `2/12`",
    "| Realistic Booking Matrix Closure | `PROVEN` |",
    "Status: `REALISTIC_BOOKING_MATRIX_PROVEN`",
    "status is `REALISTIC_BOOKING_MATRIX_PROVEN`",
    "Product-level realistic booking matrix is closed",
    "internal Console Calendar booking is product-closed",
    "`BSV1-04` is internally product-closed",
    "requires the live realistic booking result to remain `PROVEN`",
)

REQUIRED_PROCESS_TERMS = (
    "PROCESS_OPTIMIZED_AND_GUARDED",
    "One active product block at a time",
    "Docs update is an output of proof, not a substitute for proof",
    "Validation tiers",
    "T0 Reality",
    "T1 Touched Slice",
    "T2 Governance",
    "T3 Live Truth",
    "T4 Architecture Gate",
)

REQUIRED_SHADOW_REMOVAL_TERMS = (
    "SHADOW_REMOVAL_DEPENDENCY_PROVEN",
    "scripts/shadow_removal_dependency_truth.py",
    "removal_ready_for_later_block",
    "Shadow side-service removal block",
)

REQUIRED_SHADOW_SIDE_SERVICE_REMOVAL_TERMS = (
    "SHADOW_SIDE_SERVICES_REMOVED",
    "canonical `/provider/*` and `/knowledge/snapshot`",
    "do not recreate removed side services",
)

REQUIRED_BOOKING_RECLASSIFICATION_TERMS = (
    "Booking Matrix Reclassification — 2026-05-02",
    "BOOKING_MATRIX_PARTIAL_MECHANISM_PROVEN",
    "Realistic Booking Matrix Closure — 2026-05-03",
    "SCRIPTED_TECHNICAL_PROOF",
    "REAL_WORLD_PRODUCT_PROOF",
    "Real-World Salon Acceptance Pack",
    "owner-approved messy dialogs",
    "Decision & Action Ledger — 2026-05-03",
    "DL-2026-05-03-001",
    "DL-2026-05-03-002",
    "realistic_booking_matrix_product_summary_20260503g_fresh.json",
    "console_calendar_visibility_product_summary_20260503g_fresh.json",
    "valid=true",
    "BM-06 duplicate/retry",
    "BM-07 human-needed",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read(root: Path, relative_path: str) -> str:
    path = root / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def collect_work_map_errors(root: Path) -> list[str]:
    canon = _read(root, "docs/PRODUCT_SYSTEM_CANON.md")
    capability = _read(root, "docs/BEAUTY_SALON_V1_CAPABILITY_MAP.md")
    console_map = _read(root, "docs/CONSOLE_PLANE_ACCEPTANCE_MAP.md")
    session_prompt = _read(root, "docs/SESSION_START_PROMPT.txt")
    combined = "\n".join((canon, capability, console_map, session_prompt))

    errors: list[str] = []

    if VERIFIED_WORK_MAP_TITLE not in canon:
        errors.append(f"missing canon section: {VERIFIED_WORK_MAP_TITLE}")

    if "Architecture Consolidation / Handoff Baseline — 2026-05-01" not in canon:
        errors.append("missing architecture handoff baseline in canon")

    if "Architecture Consolidation / Handoff Closure — 2026-05-02" not in canon:
        errors.append("missing architecture handoff closure in canon")

    if PROCESS_OPTIMIZATION_TITLE not in canon:
        errors.append(f"missing process optimization closure in canon: {PROCESS_OPTIMIZATION_TITLE}")

    if SHADOW_REMOVAL_DEPENDENCY_TITLE not in canon:
        errors.append(f"missing shadow removal dependency proof in canon: {SHADOW_REMOVAL_DEPENDENCY_TITLE}")

    if SHADOW_SIDE_SERVICE_REMOVAL_TITLE not in canon:
        errors.append(f"missing shadow side-service removal in canon: {SHADOW_SIDE_SERVICE_REMOVAL_TITLE}")

    if "Historical short-term dependency order — superseded" not in canon:
        errors.append("missing superseded marker for historical short-term dependency order")

    if "ARCHITECTURE_HANDOFF_CLOSED" not in canon:
        errors.append("missing architecture handoff closed status")

    if "IN_PROGRESS_HANDOFF_BASELINE" in canon:
        errors.append("stale architecture handoff in-progress status remains")

    tech = _read(root, "TECH.md")
    if "Architecture handoff baseline — 2026-05-01" not in tech:
        errors.append("missing architecture handoff baseline in TECH.md")

    if "Architecture handoff closure — 2026-05-02" not in tech:
        errors.append("missing architecture handoff closure in TECH.md")

    if "Process optimization closure — 2026-05-02" not in tech:
        errors.append("missing process optimization closure in TECH.md")

    if "Shadow removal dependency proof — 2026-05-02" not in tech:
        errors.append("missing shadow removal dependency proof in TECH.md")

    if "Shadow side-service removal — 2026-05-02" not in tech:
        errors.append("missing shadow side-service removal in TECH.md")

    if "Shadow/Authority Drain Closure — Provider Gateway First Slice — 2026-05-01" not in canon:
        errors.append("missing Provider Gateway shadow authority closure section")

    if "Shadow/Authority Drain Closure — Remaining Side Services — 2026-05-01" not in canon:
        errors.append("missing remaining side services shadow authority closure section")

    if "Shadow/Authority Drain Closure — Static Guard — 2026-05-02" not in canon:
        errors.append("missing shadow authority static guard closure section")

    if "Shadow Service Lifecycle Decision — 2026-05-02" not in canon:
        errors.append("missing shadow service lifecycle decision section")

    if "Shadow Stopped-Or-Disabled Observability — 2026-05-02" not in canon:
        errors.append("missing shadow stopped-or-disabled observability section")

    if "STOPPED_OR_DISABLED_OBSERVABILITY_PROVEN" not in canon:
        errors.append("missing shadow stopped-or-disabled observability decision")

    if "KEEP_DISABLED_UNTIL_STOP_PROOF" in canon:
        errors.append("stale shadow service keep-disabled lifecycle decision remains")

    if "SHADOW_RUNTIME_AUTHORITY_ALLOW" in tech:
        errors.append("stale shadow authority override documentation remains in TECH.md")

    if "scripts/shadow_authority_runtime_guard.py" in tech:
        errors.append("stale shadow authority runtime guard documentation remains in TECH.md")

    if "Current lifecycle decision: `SHADOW / KEEP_DISABLED`" in tech:
        errors.append("stale shadow keep-disabled lifecycle documentation remains in TECH.md")

    if "Current lifecycle decision: `SHADOW / STOPPED_OR_DISABLED / DEPENDENCY_PROVEN`" in tech:
        errors.append("stale shadow stopped-or-disabled lifecycle documentation remains in TECH.md")

    if "Verified Readiness Snapshot — 2026-05-01" not in capability:
        errors.append("missing Beauty Salon verified readiness snapshot")

    if "Console Lifecycle Acceptance Proof — 2026-04-29" not in console_map:
        errors.append("missing Console lifecycle verified proof section")

    for block, status in REQUIRED_STATUS_LINES.items():
        if block not in canon:
            errors.append(f"missing verified work-map block: {block}")
        if f"| {block} | {status} |" not in canon:
            errors.append(f"missing verified work-map status: {block} = {status}")

    for term in REQUIRED_NEXT_WORK_TERMS:
        if term not in canon:
            errors.append(f"missing next-work/no-repeat term: {term}")

    process_combined = "\n".join((canon, tech, session_prompt))
    for term in REQUIRED_PROCESS_TERMS:
        if term not in process_combined:
            errors.append(f"missing process optimization term: {term}")

    for term in REQUIRED_SHADOW_REMOVAL_TERMS:
        if term not in process_combined:
            errors.append(f"missing shadow removal dependency term: {term}")

    for term in REQUIRED_SHADOW_SIDE_SERVICE_REMOVAL_TERMS:
        if term not in process_combined:
            errors.append(f"missing shadow side-service removal term: {term}")

    for term in REQUIRED_BOOKING_RECLASSIFICATION_TERMS:
        if term not in combined:
            errors.append(f"missing booking reclassification term: {term}")

    for stale_phrase in STALE_OPEN_BLOCKER_PHRASES:
        if stale_phrase in combined:
            errors.append(f"stale open-blocker phrase remains: {stale_phrase}")

    if "scripts/product_work_map_guard.py" not in session_prompt:
        errors.append("session boot protocol does not mention product_work_map_guard")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args()

    root = Path(args.repo_root or _repo_root()).resolve()
    errors = collect_work_map_errors(root)
    if errors:
        for error in errors:
            print(f"product_work_map_guard: FAIL: {error}")
        return 1
    print("product_work_map_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
