#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - local guard should fail clearly if PyYAML is unavailable
    yaml = None


LEDGER_PATH = "docs/DECISION_LEDGER.yaml"
REQUIRED_ENTRY_IDS = (
    "DL-2026-05-03-001",
    "DL-2026-05-03-002",
    "DL-2026-05-03-003",
    "DL-2026-05-03-004",
    "DL-2026-05-04-005",
    "DL-2026-05-04-006",
    "DL-2026-05-04-007",
    "DL-2026-05-05-008",
    "DL-2026-05-05-009",
    "DL-2026-05-05-010",
    "DL-2026-05-07-011",
    "DL-2026-05-07-012",
    "DL-2026-05-07-013",
)

REQUIRED_FIELDS = (
    "id",
    "date",
    "capability",
    "architecture_layer",
    "problem",
    "decision",
    "classification",
    "changed_files",
    "proof_artifacts",
    "validation",
    "known_limits",
    "do_not_repeat",
    "next_allowed_action",
)

REQUIRED_TRIGGERS = (
    "mechanism_change",
    "architecture_decision",
    "blocker_open_close_reclassify",
    "tool_or_script_creation_change",
    "product_status_change",
    "proof_downgrade_or_invalidation",
)

ALLOWED_CLASSIFICATIONS = {
    "KEEP",
    "REPAIR",
    "STRANGLE",
    "REPLACE",
    "KILL",
    "DEFER",
    "SHADOW",
    "LATER",
    "UNKNOWN",
}

REQUIRED_DOC_TERMS = (
    "Decision & Action Ledger — 2026-05-03",
    "docs/DECISION_LEDGER.yaml",
    "DL-2026-05-03-001",
    "DL-2026-05-03-002",
    "SCRIPTED_TECHNICAL_PROOF",
    "REAL_WORLD_PRODUCT_PROOF",
    "Real-World Salon Acceptance Pack",
    "owner-approved messy dialogs",
    "Internal Pilot Proof",
    "Exploration lane",
    "owner-reviewed synthetic messy corpus",
    "behavioral failures do not stop run",
    "invalid-run",
    "failure-family map",
    "OWNER_REVIEWED_CORPUS_V0_AFTER_FAM_C0_DIAGNOSTIC_COMPLETE",
    "--transport-evidence-policy rendered",
    "DIAGNOSTIC_TRANCHE_NOT_PRODUCT_PROOF",
    "DIAGNOSTIC_AFTER_P0_NOT_ACCEPTANCE",
    "FAM-B1",
    "FAM-C0",
    "FAM-C1",
    "FOCUSED_EVIDENCE_RELIABILITY_PROOF_NOT_ACCEPTANCE",
    "DIAGNOSTIC_AFTER_FAM_C0_NOT_ACCEPTANCE",
    "pending ACK",
    "soft/recovered/advisory",
    "FAM-C2",
    "FAM-C3",
    "Single-Turn Decision/Data Ownership Audit",
    "decision path + data ownership path",
    "Customer Data Contract",
    "Packs / Knowledge",
    "Capabilities",
    "Operational DB",
    "RAG / Qdrant",
    "Policy-core context",
    "DL-2026-05-07-011",
    "FOCUSED_FAM_C2_C3_TECHNICAL_PROOF_NOT_ACCEPTANCE",
    "unsupported-service availability",
    "fact-interruption continuity",
    "planner-boundary state containment",
    "range-time rendering",
    "broader Pack v0 diagnostic",
    "DL-2026-05-07-012",
    "PACK_V0_FULL_DIAGNOSTIC_AFTER_FAM_C2_C3_NOT_ACCEPTANCE",
    "strict_pass_rate=1.0",
    "zero failure families",
    "info_answer_rate",
    "acceptance-governance",
    "DL-2026-05-07-013",
    "Quality Governance",
    "Replay Isolation",
    "run-scoped unique JID",
    "policy_core_invalid_schema",
    "multi-service service-choice",
)

REQUIRED_ENTRY_TERMS = {
    "DL-2026-05-03-001": (
        "SCRIPTED_TECHNICAL_PROOF",
        "REAL_WORLD_PRODUCT_PROOF",
        "Real-World Salon Acceptance Pack",
        "owner-approved messy dialogs",
        "real internal appointments",
    ),
    "DL-2026-05-03-002": (
        "Internal Pilot Proof",
        "owner-reviewed synthetic messy corpus",
        "Exploration lane",
        "behavioral failures do not stop run",
        "invalid-run",
        "failure-family map",
    ),
    "DL-2026-05-03-003": (
        "transport evidence",
        "rendered",
        "delivery",
        "do-not-use",
        "diagnostic failure-family map",
        "raw owner green",
    ),
    "DL-2026-05-03-004": (
        "Tranche B",
        "DIAGNOSTIC_TRANCHE_NOT_PRODUCT_PROOF",
        "booking-manage",
        "handoff contact",
        "strict Acceptance",
    ),
    "DL-2026-05-04-005": (
        "FAM-B1",
        "FAM-B3",
        "admin-confirmation",
        "HANDOFF",
        "calendar.cancel",
    ),
    "DL-2026-05-04-006": (
        "FAM-B2",
        "pending-state",
        "manager simulation",
        "race-tolerant",
        "Pack v0",
    ),
    "DL-2026-05-04-007": (
        "DIAGNOSTIC_AFTER_P0_NOT_ACCEPTANCE",
        "FAM-C0",
        "FAM-C1",
        "unsupported-service",
        "fact-interruption",
        "511-turn",
    ),
    "DL-2026-05-05-008": (
        "FAM-C0",
        "FOCUSED_EVIDENCE_RELIABILITY_PROOF_NOT_ACCEPTANCE",
        "pending ACK",
        "soft/recovered/advisory",
        "decision_meta_soft_timeouts",
        "webhook_recovered_timeouts",
        "pending_ack_soft_timeouts",
    ),
    "DL-2026-05-05-009": (
        "DIAGNOSTIC_AFTER_FAM_C0_NOT_ACCEPTANCE",
        "infra_valid=true",
        "strict_pass_rate=0.9545",
        "FAM-C2",
        "unsupported-service",
        "FAM-C3",
        "fact-interruption",
        "INVALID_RUN_DO_NOT_USE",
    ),
    "DL-2026-05-05-010": (
        "decision path",
        "data ownership path",
        "Customer Data Contract",
        "Packs / Knowledge",
        "Capabilities",
        "Operational DB",
        "RAG / Qdrant",
        "Policy-core context",
        "semantic owner",
    ),
    "DL-2026-05-07-011": (
        "FAM-C2",
        "FAM-C3",
        "FOCUSED_FAM_C2_C3_TECHNICAL_PROOF_NOT_ACCEPTANCE",
        "unsupported-service availability",
        "fact-interruption continuity",
        "planner-boundary state containment",
        "range-time rendering",
        "strict_pass_rate=1.0",
        "semantic_valid=true",
        "not Pack v0 Acceptance",
    ),
    "DL-2026-05-07-012": (
        "PACK_V0_FULL_DIAGNOSTIC_AFTER_FAM_C2_C3_NOT_ACCEPTANCE",
        "strict_pass_rate=1.0",
        "failure_family_count=0",
        "info_answer_rate",
        "infra_valid=false",
        "semantic_valid=false",
        "handoff semantic axes",
        "unsupported-service booking continuation",
        "acceptance-governance",
        "not Pack v0 Acceptance",
    ),
    "DL-2026-05-07-013": (
        "Quality Governance",
        "Replay Isolation",
        "run-scoped unique JID",
        "info_answer_rate=1.0",
        "infra_valid=true",
        "strict_pass_rate=0.9545",
        "policy_core_invalid_schema",
        "multi-service service-choice",
        "20260507l",
        "20260507m",
        "not Pack v0 Acceptance",
    ),
}

STALE_PRODUCT_CLAIMS = (
    "| Realistic Booking Matrix Closure | `PROVEN` |",
    "Status: `REALISTIC_BOOKING_MATRIX_PROVEN`",
    "status is `REALISTIC_BOOKING_MATRIX_PROVEN`",
    "Product-level realistic booking matrix is closed",
    "internal Console Calendar booking is product-closed",
    "`BSV1-04` is internally product-closed",
    "requires the live realistic booking result to remain `PROVEN`",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read(root: Path, relative_path: str) -> str:
    path = root / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _load_yaml(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing ledger file"
    if yaml is None:
        return None, "PyYAML is unavailable"
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"ledger yaml parse failed: {exc}"
    if not isinstance(payload, dict):
        return None, "ledger root must be a mapping"
    return payload, None


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "\n".join(_as_text(item) for item in value)
    if isinstance(value, dict):
        return "\n".join(f"{key}: {_as_text(item)}" for key, item in value.items())
    return str(value)


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    return False


def _entry_errors(entry: Any, index: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(entry, dict):
        return [f"entry[{index}] must be a mapping"]

    entry_id = str(entry.get("id") or f"entry[{index}]")
    for field in REQUIRED_FIELDS:
        if field not in entry or _is_empty(entry.get(field)):
            errors.append(f"ledger entry {entry_id} missing required field: {field}")

    classification = str(entry.get("classification") or "").strip()
    if classification and classification not in ALLOWED_CLASSIFICATIONS:
        errors.append(f"ledger entry {entry_id} has invalid classification: {classification}")

    for field in ("changed_files", "proof_artifacts", "validation", "known_limits", "do_not_repeat"):
        if field in entry and not isinstance(entry.get(field), list):
            errors.append(f"ledger entry {entry_id} field must be a list: {field}")

    return errors


def collect_decision_ledger_errors(root: Path) -> list[str]:
    ledger_path = root / LEDGER_PATH
    payload, load_error = _load_yaml(ledger_path)
    errors: list[str] = []
    if load_error:
        errors.append(f"decision_ledger_guard: {load_error}: {LEDGER_PATH}")
        return errors

    assert payload is not None
    triggers = payload.get("entry_required_for")
    if not isinstance(triggers, list):
        errors.append("ledger entry_required_for must be a list")
        triggers = []
    for trigger in REQUIRED_TRIGGERS:
        if trigger not in triggers:
            errors.append(f"ledger missing entry trigger: {trigger}")

    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        errors.append("ledger entries must be a non-empty list")
        entries = []

    for index, entry in enumerate(entries):
        errors.extend(_entry_errors(entry, index))

    for required_entry_id in REQUIRED_ENTRY_IDS:
        required_entry = next(
            (
                entry
                for entry in entries
                if isinstance(entry, dict) and str(entry.get("id")) == required_entry_id
            ),
            None,
        )
        if required_entry is None:
            errors.append(f"ledger missing required current entry: {required_entry_id}")
            continue
        entry_text = _as_text(required_entry)
        for term in REQUIRED_ENTRY_TERMS[required_entry_id]:
            if term not in entry_text:
                errors.append(f"ledger entry {required_entry_id} missing term: {term}")

    canon = _read(root, "docs/PRODUCT_SYSTEM_CANON.md")
    capability = _read(root, "docs/BEAUTY_SALON_V1_CAPABILITY_MAP.md")
    session_prompt = _read(root, "docs/SESSION_START_PROMPT.txt")
    tech = _read(root, "TECH.md")
    structure = _read(root, "STRUCTURE.md")
    combined = "\n".join((canon, capability, session_prompt, tech, structure))

    for term in REQUIRED_DOC_TERMS:
        if term not in combined:
            errors.append(f"missing decision ledger/product-proof term: {term}")

    for stale_claim in STALE_PRODUCT_CLAIMS:
        if stale_claim in combined:
            errors.append(f"stale real-world product proof claim remains: {stale_claim}")

    if "`scripts/decision_ledger_guard.py`" not in tech + structure:
        errors.append("decision ledger guard is not registered in TECH.md or STRUCTURE.md")

    if "`truffles-api/tests/architecture/test_decision_ledger_guard.py`" not in tech + structure:
        errors.append("decision ledger architecture test is not registered")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args()

    root = Path(args.repo_root or _repo_root()).resolve()
    errors = collect_decision_ledger_errors(root)
    if errors:
        for error in errors:
            print(f"decision_ledger_guard: FAIL: {error}")
        return 1
    print("decision_ledger_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
