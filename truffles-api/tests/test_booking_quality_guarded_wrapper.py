import os
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _write_fake_controller(path: Path, log_path: Path) -> None:
    script = """#!/usr/bin/env bash
set -euo pipefail
cmd="${1:-}"
shift || true
echo "$cmd $*" >> "__LOG__"
if [[ "$cmd" == "prepare" ]]; then
  echo -e "chain-demo\tlock\ttok-demo"
  exit 0
fi
if [[ "$cmd" == "finalize" ]]; then
  exit 0
fi
exit 0
"""
    path.write_text(script.replace("__LOG__", str(log_path)), encoding="utf-8")
    path.chmod(0o755)


def _write_failing_controller(path: Path, log_path: Path) -> None:
    script = """#!/usr/bin/env bash
set -euo pipefail
cmd="${1:-}"
shift || true
echo "$cmd $*" >> "__LOG__"
if [[ "$cmd" == "prepare" ]]; then
  echo "prepare failed" >&2
  exit 2
fi
exit 0
"""
    path.write_text(script.replace("__LOG__", str(log_path)), encoding="utf-8")
    path.chmod(0o755)


def _write_fake_diagnose(path: Path, log_path: Path) -> None:
    script = """#!/usr/bin/env python3
import json
import os
import sys

args = sys.argv[1:]
with open(__LOG_PY__, "a", encoding="utf-8") as handle:
    handle.write(" ".join(args) + "\\n")

output_dir = None
for idx, token in enumerate(args):
    if token == "--output-dir" and idx + 1 < len(args):
        output_dir = args[idx + 1]
        break
if output_dir is None:
    output_dir = "/tmp/booking_quality/fake"
os.makedirs(output_dir, exist_ok=True)
summary_path = os.path.join(output_dir, "summary.json")
payload = {
    "run_id": "fake",
    "quality_status": {
        "infra_valid": True,
        "semantic_valid": True,
        "run_integrity_valid": True,
    },
    "infra_valid": True,
    "semantic_valid": True,
}
with open(summary_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, ensure_ascii=False, indent=2)
"""
    path.write_text(
        script.replace("__LOG_PY__", repr(str(log_path))),
        encoding="utf-8",
    )
    path.chmod(0o755)


def _guarded_base_cmd(script_path: Path, run_id: str) -> list[str]:
    return [
        str(script_path),
        "--mode",
        "lock",
        "--run-id",
        run_id,
        "--allow-repeat-fingerprint",
        "--allow-pending-previous",
        "--",
        "--base-url",
        "http://127.0.0.1:18172",
        "--client-slug",
        "demo_salon",
        "--mode",
        "llm",
        "--count",
        "10",
        "--min-turns",
        "10",
        "--max-turns",
        "15",
        "--include-media",
        "--scenario-coverage",
        "booking,info,interrupt,handoff",
        "--tool-hooks",
        "auto",
        "--jid-mode",
        "unique",
        "--judge-mode",
        "all",
        "--quality-lane",
        "acceptance",
        "--run-economy-gate",
        "block",
        "--manual-audit-gate",
        "block",
        "--fail-on-thresholds",
    ]


def test_guarded_wrapper_acceptance_injects_chain_tokens(tmp_path):
    repo_root = _repo_root()
    wrapper = repo_root / "scripts" / "llm_quality_guarded.sh"
    if not wrapper.exists():
        pytest.skip("llm_quality_guarded.sh not present")

    controller_log = tmp_path / "controller.log"
    diagnose_log = tmp_path / "diagnose.log"
    fake_controller = tmp_path / "fake_controller.sh"
    fake_diagnose = tmp_path / "fake_diagnose.py"
    _write_fake_controller(fake_controller, controller_log)
    _write_fake_diagnose(fake_diagnose, diagnose_log)

    run_id = f"booking-lock-wrapper-{uuid4().hex[:8]}"
    env = dict(os.environ)
    env["LLM_QUALITY_CHAIN_CONTROLLER_BIN"] = str(fake_controller)
    env["LLM_QUALITY_DIAGNOSE_BIN"] = "python3"
    env["LLM_QUALITY_DIAGNOSE_SCRIPT"] = str(fake_diagnose)

    result = subprocess.run(
        _guarded_base_cmd(wrapper, run_id),
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    controller_text = controller_log.read_text(encoding="utf-8")
    diagnose_text = diagnose_log.read_text(encoding="utf-8")

    assert "prepare --mode lock" in controller_text
    assert "finalize --mode lock" in controller_text
    assert "--chain-id chain-demo" in diagnose_text
    assert "--chain-step lock" in diagnose_text
    assert "--chain-token tok-demo" in diagnose_text


def test_guarded_wrapper_blocks_when_controller_prepare_fails(tmp_path):
    repo_root = _repo_root()
    wrapper = repo_root / "scripts" / "llm_quality_guarded.sh"
    if not wrapper.exists():
        pytest.skip("llm_quality_guarded.sh not present")

    controller_log = tmp_path / "controller_fail.log"
    diagnose_log = tmp_path / "diagnose_fail.log"
    fake_controller = tmp_path / "fake_controller_fail.sh"
    fake_diagnose = tmp_path / "fake_diagnose.py"
    _write_failing_controller(fake_controller, controller_log)
    _write_fake_diagnose(fake_diagnose, diagnose_log)

    run_id = f"booking-lock-wrapper-{uuid4().hex[:8]}"
    env = dict(os.environ)
    env["LLM_QUALITY_CHAIN_CONTROLLER_BIN"] = str(fake_controller)
    env["LLM_QUALITY_DIAGNOSE_BIN"] = "python3"
    env["LLM_QUALITY_DIAGNOSE_SCRIPT"] = str(fake_diagnose)

    result = subprocess.run(
        _guarded_base_cmd(wrapper, run_id),
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "chain controller prepare failed" in result.stderr
    assert controller_log.exists()
    assert not diagnose_log.exists()
