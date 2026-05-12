from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_closure_rescue_claim_guard_flags_missing_behavioral_semantic_audit(tmp_path: Path) -> None:
    module = _load_module("closure_rescue_claim_guard", SCRIPTS / "closure_rescue_claim_guard.py")
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    _write_json(bundle / "summary.json", {"status": "closed_proven", "closure_scope": "behavioral"})
    _write_json(bundle / "result.json", {"result": "success", "artifacts": {}})

    errors = module.collect_errors(bundle)
    assert any("semantic_audit mapping missing" in item for item in errors)


def test_closure_rescue_claim_guard_flags_behavioral_closure_without_green_no(tmp_path: Path) -> None:
    module = _load_module("closure_rescue_claim_guard", SCRIPTS / "closure_rescue_claim_guard.py")
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    _write_json(
        bundle / "summary.json",
        {
            "status": "closed_proven",
            "closure_scope": "behavioral",
            "semantic_audit": {
                "raw_owner": "yellow",
                "final_runtime": "green",
                "rescue": "yes",
            },
        },
    )
    _write_json(
        bundle / "result.json",
        {
            "result": "success",
            "artifacts": {
                "manual_audit": str(bundle / "manual_audit.md"),
                "proof_exact_live": str(bundle / "proof_exact_live.json"),
                "narrow_remeasure": str(bundle / "narrow_remeasure.json"),
            },
        },
    )

    errors = module.collect_errors(bundle)
    assert any("raw_owner = green" in item for item in errors)
    assert any("rescue = no" in item for item in errors)


def test_closure_rescue_claim_guard_accepts_behavioral_green_bundle(tmp_path: Path) -> None:
    module = _load_module("closure_rescue_claim_guard", SCRIPTS / "closure_rescue_claim_guard.py")
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    _write_json(
        bundle / "summary.json",
        {
            "status": "closed_proven",
            "closure_scope": "behavioral",
            "semantic_audit": {
                "raw_owner": "green",
                "final_runtime": "green",
                "rescue": "no",
            },
        },
    )
    _write_json(
        bundle / "result.json",
        {
            "result": "success",
            "artifacts": {
                "manual_audit": str(bundle / "manual_audit.md"),
                "proof_exact_live": str(bundle / "proof_exact_live.json"),
                "narrow_remeasure": str(bundle / "narrow_remeasure.json"),
            },
        },
    )

    assert module.collect_errors(bundle) == []


def test_closure_rescue_claim_guard_accepts_explicit_guard_only_bundle(tmp_path: Path) -> None:
    module = _load_module("closure_rescue_claim_guard", SCRIPTS / "closure_rescue_claim_guard.py")
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    _write_json(
        bundle / "summary.json",
        {
            "status": "closed_proven",
            "closure_scope": "guard_only",
            "semantic_audit": {
                "raw_owner": "N/A",
                "final_runtime": "N/A",
                "rescue": "N/A",
                "note": "guard-only enforcement block",
            },
        },
    )
    _write_json(
        bundle / "result.json",
        {
            "result": "success",
            "artifacts": {
                "manual_audit": str(bundle / "manual_audit.md"),
            },
        },
    )

    assert module.collect_errors(bundle) == []
