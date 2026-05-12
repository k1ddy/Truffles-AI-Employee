#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CLOSURE_CLAIM_TOKENS = {
    "closed",
    "closed_proven",
    "done",
    "fixed",
    "green",
    "pass",
    "passed",
    "success",
}
BEHAVIORAL_SCOPES = {"behavioral", "runtime_behavior", "owner_quality"}
NON_BEHAVIORAL_SCOPES = {"guard_only", "non_behavioral", "doc_only", "infra_only"}
BEHAVIORAL_VERDICTS = {"green", "yellow", "red"}
NON_BEHAVIORAL_VERDICTS = {"n/a"}
RESCUE_BEHAVIORAL = {"yes", "no"}


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"closure_rescue_claim_guard: FAIL: invalid JSON object: {path}")
    return data


def _normalize_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().casefold()
    return token or None


def _claims_closure(payload: dict[str, Any]) -> bool:
    for key in ("status", "result", "closure_status"):
        token = _normalize_token(payload.get(key))
        if token in CLOSURE_CLAIM_TOKENS:
            return True
    return False


def _semantic_audit(summary: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    for payload in (summary, result):
        semantic_audit = payload.get("semantic_audit")
        if isinstance(semantic_audit, dict):
            return semantic_audit
    return {}


def _closure_scope(summary: dict[str, Any], result: dict[str, Any], semantic_audit: dict[str, Any]) -> str | None:
    for candidate in (
        semantic_audit.get("scope"),
        summary.get("closure_scope"),
        result.get("closure_scope"),
    ):
        token = _normalize_token(candidate)
        if token:
            return token
    return None


def _require_artifact_path(errors: list[str], result: dict[str, Any], key: str) -> None:
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("result.json missing artifacts mapping for closure claim")
        return
    value = artifacts.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"result.json missing artifacts.{key} for closure claim")


def collect_errors(bundle_dir: Path) -> list[str]:
    errors: list[str] = []
    summary_path = bundle_dir / "summary.json"
    result_path = bundle_dir / "result.json"
    if not summary_path.exists():
        return [f"summary.json missing in {bundle_dir}"]
    if not result_path.exists():
        return [f"result.json missing in {bundle_dir}"]

    summary = _load_json(summary_path)
    result = _load_json(result_path)
    claim_bearing = _claims_closure(summary) or _claims_closure(result)
    if not claim_bearing:
        return []

    semantic_audit = _semantic_audit(summary, result)
    if not semantic_audit:
        return ["semantic_audit mapping missing for claim-bearing bundle"]

    scope = _closure_scope(summary, result, semantic_audit)
    if scope is None:
        errors.append("closure_scope missing for claim-bearing bundle")
        return errors

    raw_owner = _normalize_token(semantic_audit.get("raw_owner"))
    final_runtime = _normalize_token(semantic_audit.get("final_runtime"))
    rescue = _normalize_token(semantic_audit.get("rescue"))

    if scope in NON_BEHAVIORAL_SCOPES:
        if raw_owner not in NON_BEHAVIORAL_VERDICTS:
            errors.append("non-behavioral claim must declare semantic_audit.raw_owner = N/A")
        if final_runtime not in NON_BEHAVIORAL_VERDICTS:
            errors.append("non-behavioral claim must declare semantic_audit.final_runtime = N/A")
        if rescue not in NON_BEHAVIORAL_VERDICTS:
            errors.append("non-behavioral claim must declare semantic_audit.rescue = N/A")
        note = semantic_audit.get("note")
        if not isinstance(note, str) or not note.strip():
            errors.append("non-behavioral claim must include semantic_audit.note")
        _require_artifact_path(errors, result, "manual_audit")
        return errors

    if scope not in BEHAVIORAL_SCOPES:
        errors.append(f"unsupported closure_scope for claim-bearing bundle: {scope}")
        return errors

    if raw_owner not in BEHAVIORAL_VERDICTS:
        errors.append("behavioral claim missing valid semantic_audit.raw_owner verdict")
    if final_runtime not in BEHAVIORAL_VERDICTS:
        errors.append("behavioral claim missing valid semantic_audit.final_runtime verdict")
    if rescue not in RESCUE_BEHAVIORAL:
        errors.append("behavioral claim missing valid semantic_audit.rescue verdict")

    for artifact_key in ("manual_audit", "proof_exact_live", "narrow_remeasure"):
        _require_artifact_path(errors, result, artifact_key)

    if errors:
        return errors

    if raw_owner != "green":
        errors.append("behavioral closure claim requires semantic_audit.raw_owner = green")
    if final_runtime != "green":
        errors.append("behavioral closure claim requires semantic_audit.final_runtime = green")
    if rescue != "no":
        errors.append("behavioral closure claim requires semantic_audit.rescue = no")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-dir", required=True, help="Artifact bundle directory to validate")
    args = parser.parse_args()
    bundle_dir = Path(args.bundle_dir).resolve()
    errors = collect_errors(bundle_dir)
    if errors:
        for error in errors:
            print(f"closure_rescue_claim_guard: FAIL: {error}", file=sys.stderr)
        return 1
    print("closure_rescue_claim_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
