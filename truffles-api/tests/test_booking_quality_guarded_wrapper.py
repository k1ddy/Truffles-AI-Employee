import json
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
  mode="lock"
  while [[ $# -gt 0 ]]; do
    if [[ "$1" == "--mode" && $# -gt 1 ]]; then
      mode="$2"
      break
    fi
    shift
  done
  echo -e "chain-demo\t${mode}\ttok-demo"
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


def _write_pg_checklist(path: Path) -> None:
    payload = {
        "go_to_full": {
            "PG0": {"status": "pass"},
            "PG1": {"status": "pass"},
            "PG2": {"status": "pass"},
            "PG3": {"status": "pass"},
            "PG4": {"status": "pass"},
            "PG5": {"status": "pass"},
            "PG6": {"status": "pass"},
            "root_cause_statement": "handoff miss reproduced in L2 micro-chaos",
            "defect_mapping": [
                {
                    "defect_class": "handoff_miss",
                    "target_test": "truffles-api/tests/test_booking_quality_status_gate.py::test_quality_constant_requires_acceptance_envelope_for_critical_run",
                    "gate": "PG1",
                    "owner": "a1",
                }
            ],
        }
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _guarded_base_cmd(
    script_path: Path,
    run_id: str,
    pg_checklist: Path,
    *,
    mode: str = "lock",
    allow_pending_previous: bool = True,
    extra_quality_args: list[str] | None = None,
) -> list[str]:
    cmd = [
        str(script_path),
        "--mode",
        mode,
        "--run-id",
        run_id,
        "--pg-checklist",
        str(pg_checklist),
        "--allow-repeat-fingerprint",
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
    if allow_pending_previous:
        cmd.insert(7, "--allow-pending-previous")
    if extra_quality_args:
        cmd.extend(extra_quality_args)
    return cmd


def test_guarded_wrapper_acceptance_injects_chain_tokens(tmp_path):
    repo_root = _repo_root()
    wrapper = repo_root / "scripts" / "llm_quality_guarded.sh"
    if not wrapper.exists():
        pytest.skip("llm_quality_guarded.sh not present")

    controller_log = tmp_path / "controller.log"
    diagnose_log = tmp_path / "diagnose.log"
    fake_controller = tmp_path / "fake_controller.sh"
    fake_diagnose = tmp_path / "fake_diagnose.py"
    pg_checklist = tmp_path / "pg_checklist.json"
    _write_fake_controller(fake_controller, controller_log)
    _write_fake_diagnose(fake_diagnose, diagnose_log)
    _write_pg_checklist(pg_checklist)

    run_id = f"booking-lock-wrapper-{uuid4().hex[:8]}"
    env = dict(os.environ)
    env["LLM_QUALITY_CHAIN_CONTROLLER_BIN"] = str(fake_controller)
    env["LLM_QUALITY_DIAGNOSE_BIN"] = "python3"
    env["LLM_QUALITY_DIAGNOSE_SCRIPT"] = str(fake_diagnose)

    result = subprocess.run(
        _guarded_base_cmd(wrapper, run_id, pg_checklist),
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
    pg_checklist = tmp_path / "pg_checklist.json"
    _write_failing_controller(fake_controller, controller_log)
    _write_fake_diagnose(fake_diagnose, diagnose_log)
    _write_pg_checklist(pg_checklist)

    run_id = f"booking-lock-wrapper-{uuid4().hex[:8]}"
    env = dict(os.environ)
    env["LLM_QUALITY_CHAIN_CONTROLLER_BIN"] = str(fake_controller)
    env["LLM_QUALITY_DIAGNOSE_BIN"] = "python3"
    env["LLM_QUALITY_DIAGNOSE_SCRIPT"] = str(fake_diagnose)

    result = subprocess.run(
        _guarded_base_cmd(wrapper, run_id, pg_checklist),
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "chain controller prepare failed" in result.stderr
    assert controller_log.exists()
    assert not diagnose_log.exists()


def test_guarded_wrapper_supports_canary_mode(tmp_path):
    repo_root = _repo_root()
    wrapper = repo_root / "scripts" / "llm_quality_guarded.sh"
    if not wrapper.exists():
        pytest.skip("llm_quality_guarded.sh not present")

    controller_log = tmp_path / "controller_canary.log"
    diagnose_log = tmp_path / "diagnose_canary.log"
    fake_controller = tmp_path / "fake_controller_canary.sh"
    fake_diagnose = tmp_path / "fake_diagnose_canary.py"
    pg_checklist = tmp_path / "pg_checklist_canary.json"
    _write_fake_controller(fake_controller, controller_log)
    _write_fake_diagnose(fake_diagnose, diagnose_log)
    _write_pg_checklist(pg_checklist)

    run_id = f"booking-canary-wrapper-{uuid4().hex[:8]}"
    env = dict(os.environ)
    env["LLM_QUALITY_CHAIN_CONTROLLER_BIN"] = str(fake_controller)
    env["LLM_QUALITY_DIAGNOSE_BIN"] = "python3"
    env["LLM_QUALITY_DIAGNOSE_SCRIPT"] = str(fake_diagnose)

    result = subprocess.run(
        _guarded_base_cmd(wrapper, run_id, pg_checklist, mode="canary"),
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    controller_text = controller_log.read_text(encoding="utf-8")
    diagnose_text = diagnose_log.read_text(encoding="utf-8")
    assert "prepare --mode canary" in controller_text
    assert "finalize --mode canary" in controller_text
    assert "--chain-step canary" in diagnose_text


def test_guarded_wrapper_redacts_webhook_secret_in_ledger(tmp_path):
    repo_root = _repo_root()
    wrapper = repo_root / "scripts" / "llm_quality_guarded.sh"
    if not wrapper.exists():
        pytest.skip("llm_quality_guarded.sh not present")

    controller_log = tmp_path / "controller_secret.log"
    diagnose_log = tmp_path / "diagnose_secret.log"
    fake_controller = tmp_path / "fake_controller_secret.sh"
    fake_diagnose = tmp_path / "fake_diagnose_secret.py"
    pg_checklist = tmp_path / "pg_checklist_secret.json"
    ledger_dir = tmp_path / "guard_ledger"
    _write_fake_controller(fake_controller, controller_log)
    _write_fake_diagnose(fake_diagnose, diagnose_log)
    _write_pg_checklist(pg_checklist)

    run_id = f"booking-lock-wrapper-{uuid4().hex[:8]}"
    env = dict(os.environ)
    env["LLM_QUALITY_CHAIN_CONTROLLER_BIN"] = str(fake_controller)
    env["LLM_QUALITY_DIAGNOSE_BIN"] = "python3"
    env["LLM_QUALITY_DIAGNOSE_SCRIPT"] = str(fake_diagnose)
    env["LLM_QUALITY_GUARD_LEDGER_DIR"] = str(ledger_dir)

    result = subprocess.run(
        _guarded_base_cmd(
            wrapper,
            run_id,
            pg_checklist,
            extra_quality_args=["--webhook-secret", "super-secret-token"],
        ),
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    ledger_file = ledger_dir / "ledger.tsv"
    assert ledger_file.exists()
    ledger_text = ledger_file.read_text(encoding="utf-8")
    assert "super-secret-token" not in ledger_text
    assert "redacted" in ledger_text


def test_guarded_wrapper_allows_fresh_lock_after_audited_non_canonical_latest_run(tmp_path):
    repo_root = _repo_root()
    wrapper = repo_root / "scripts" / "llm_quality_guarded.sh"
    if not wrapper.exists():
        pytest.skip("llm_quality_guarded.sh not present")

    controller_log = tmp_path / "controller_lock.log"
    diagnose_log = tmp_path / "diagnose_lock.log"
    fake_controller = tmp_path / "fake_controller_lock.sh"
    fake_diagnose = tmp_path / "fake_diagnose_lock.py"
    pg_checklist = tmp_path / "pg_checklist_lock.json"
    index_root = tmp_path / "quality_index"
    latest_by_mode = index_root / "latest_by_mode"
    latest_by_mode.mkdir(parents=True, exist_ok=True)
    (latest_by_mode / "lock.json").write_text(
        json.dumps(
            {
                "run_id": "old-lock",
                "status": "incomplete",
                "manual_audit_status": "done",
                "artifact_integrity_valid": True,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _write_fake_controller(fake_controller, controller_log)
    _write_fake_diagnose(fake_diagnose, diagnose_log)
    _write_pg_checklist(pg_checklist)

    run_id = f"booking-lock-wrapper-{uuid4().hex[:8]}"
    env = dict(os.environ)
    env["LLM_QUALITY_CHAIN_CONTROLLER_BIN"] = str(fake_controller)
    env["LLM_QUALITY_DIAGNOSE_BIN"] = "python3"
    env["LLM_QUALITY_DIAGNOSE_SCRIPT"] = str(fake_diagnose)
    env["LLM_QUALITY_INDEX_ROOT"] = str(index_root)

    result = subprocess.run(
        _guarded_base_cmd(
            wrapper,
            run_id,
            pg_checklist,
            allow_pending_previous=False,
        ),
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "deferring lock admission to diagnose.py run-economy gate" in result.stderr
    assert diagnose_log.exists()


def test_guarded_wrapper_still_blocks_replay_after_non_canonical_latest_run(tmp_path):
    repo_root = _repo_root()
    wrapper = repo_root / "scripts" / "llm_quality_guarded.sh"
    if not wrapper.exists():
        pytest.skip("llm_quality_guarded.sh not present")

    controller_log = tmp_path / "controller_replay.log"
    diagnose_log = tmp_path / "diagnose_replay.log"
    fake_controller = tmp_path / "fake_controller_replay.sh"
    fake_diagnose = tmp_path / "fake_diagnose_replay.py"
    pg_checklist = tmp_path / "pg_checklist_replay.json"
    index_root = tmp_path / "quality_index"
    latest_by_mode = index_root / "latest_by_mode"
    latest_by_mode.mkdir(parents=True, exist_ok=True)
    (latest_by_mode / "replay.json").write_text(
        json.dumps(
            {
                "run_id": "old-replay",
                "status": "failed",
                "manual_audit_status": "done",
                "artifact_integrity_valid": True,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _write_fake_controller(fake_controller, controller_log)
    _write_fake_diagnose(fake_diagnose, diagnose_log)
    _write_pg_checklist(pg_checklist)

    run_id = f"booking-replay-wrapper-{uuid4().hex[:8]}"
    env = dict(os.environ)
    env["LLM_QUALITY_CHAIN_CONTROLLER_BIN"] = str(fake_controller)
    env["LLM_QUALITY_DIAGNOSE_BIN"] = "python3"
    env["LLM_QUALITY_DIAGNOSE_SCRIPT"] = str(fake_diagnose)
    env["LLM_QUALITY_INDEX_ROOT"] = str(index_root)

    result = subprocess.run(
        _guarded_base_cmd(
            wrapper,
            run_id,
            pg_checklist,
            mode="replay",
            allow_pending_previous=False,
            extra_quality_args=[
                "--scenarios-file",
                str(tmp_path / "scenarios.json"),
                "--baseline-summary",
                str(tmp_path / "summary.json"),
                "--reset-before-dialog",
                "--fail-on-regression",
            ],
        ),
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "previous run not canonical" in result.stderr
    assert not diagnose_log.exists()
