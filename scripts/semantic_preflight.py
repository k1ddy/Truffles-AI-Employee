#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _run_guard(command: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout, result.stderr


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _guard_commands(repo_root: Path, *, scripts_root: Path, bundle_dir: Path | None) -> list[tuple[str, list[str]]]:
    commands: list[tuple[str, list[str]]] = [
        (
            "single_semantic_owner_guard.py",
            [
                sys.executable,
                str(scripts_root / "single_semantic_owner_guard.py"),
                "--repo-root",
                str(repo_root),
            ],
        ),
        (
            "semantic_contract_sync_guard.py",
            [
                sys.executable,
                str(scripts_root / "semantic_contract_sync_guard.py"),
                "--repo-root",
                str(repo_root),
            ],
        ),
    ]
    if bundle_dir:
        commands.append(
            (
                "closure_rescue_claim_guard.py",
                [
                    sys.executable,
                    str(scripts_root / "closure_rescue_claim_guard.py"),
                    "--bundle-dir",
                    str(bundle_dir.resolve()),
                ],
            )
        )
    return commands


def _runtime_fingerprint_preflight(
    *,
    scripts_root: Path,
    base_url: str | None,
    expected_commit: str | None,
    request_timeout: float,
) -> dict[str, Any]:
    if not base_url:
        return {"checked": False}
    proof_module = _load_module("focused_family_proof", scripts_root / "focused_family_proof.py")
    resolved_expected_commit = proof_module._resolve_expected_commit(expected_commit)
    fingerprint = proof_module.validate_runtime_fingerprint(
        base_url=base_url,
        expected_commit=resolved_expected_commit,
        timeout=request_timeout,
    )
    payload = proof_module.runtime_fingerprint_payload(fingerprint)
    payload["checked"] = True
    return payload


def run_preflight(
    *,
    repo_root: Path,
    bundle_dir: Path | None = None,
    base_url: str | None = None,
    expected_commit: str | None = None,
    request_timeout: float = 10.0,
) -> dict[str, Any]:
    scripts_root = Path(__file__).resolve().parent
    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    for label, command in _guard_commands(repo_root, scripts_root=scripts_root, bundle_dir=bundle_dir):
        returncode, stdout, stderr = _run_guard(command)
        messages = [line.strip() for line in (stderr or stdout).splitlines() if line.strip()]
        checks.append(
            {
                "name": label,
                "valid": returncode == 0,
                "command": command,
                "messages": messages,
            }
        )
        if returncode != 0:
            if not messages:
                messages = [f"{label} exited with code {returncode}"]
            for line in messages:
                failures.append(f"{label}: {line}")

    runtime_fingerprint = _runtime_fingerprint_preflight(
        scripts_root=scripts_root,
        base_url=base_url,
        expected_commit=expected_commit,
        request_timeout=request_timeout,
    )
    if runtime_fingerprint.get("checked") and not runtime_fingerprint.get("valid", False):
        reasons = runtime_fingerprint.get("reasons") or ["unknown"]
        failures.append(
            "runtime_fingerprint: "
            f"endpoint={runtime_fingerprint.get('endpoint')} "
            f"expected_commit={runtime_fingerprint.get('expected_commit') or 'unknown'} "
            f"runtime_commit={runtime_fingerprint.get('runtime_commit') or 'unknown'} "
            f"reasons={','.join(str(item) for item in reasons)}"
        )

    return {
        "valid": not failures,
        "repo_root": str(repo_root),
        "bundle_dir": str(bundle_dir.resolve()) if bundle_dir else None,
        "repo_checks": checks,
        "runtime_fingerprint": runtime_fingerprint,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repository root to validate",
    )
    parser.add_argument(
        "--bundle-dir",
        default=None,
        help="Optional artifact bundle directory for closure/rescue claim validation",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Optional runtime base URL for /admin/version fingerprint validation",
    )
    parser.add_argument(
        "--expected-commit",
        default=None,
        help="Optional explicit commit to compare against runtime fingerprint",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=10.0,
        help="HTTP timeout for runtime fingerprint validation",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path for writing the JSON preflight payload",
    )
    args = parser.parse_args()

    payload = run_preflight(
        repo_root=Path(args.repo_root).resolve(),
        bundle_dir=Path(args.bundle_dir).resolve() if args.bundle_dir else None,
        base_url=args.base_url,
        expected_commit=args.expected_commit,
        request_timeout=args.request_timeout,
    )

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False))
    if not payload["valid"]:
        for failure in payload["failures"]:
            print(f"semantic_preflight: FAIL: {failure}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
