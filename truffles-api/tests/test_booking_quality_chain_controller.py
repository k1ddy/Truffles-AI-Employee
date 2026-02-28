import json
import os
import subprocess
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

import pytest


def _load_module():
    base = Path(__file__).resolve()
    candidates = [
        base.parents[1] / "ops" / "diagnose.py",
        base.parents[2] / "ops" / "diagnose.py",
    ]
    script_path = next((path for path in candidates if path.exists()), candidates[0])
    if not script_path.exists():
        pytest.skip("ops/diagnose.py not present", allow_module_level=True)
    spec = spec_from_file_location("diagnose_script_chain", script_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_module = _load_module()


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
            "root_cause_statement": "calendar conflict reply leaked stale booking prompt",
            "defect_mapping": [
                {
                    "defect_class": "booking_flow_break",
                    "target_test": "truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_info_lateness_signal_uses_lateness_reply",
                    "gate": "PG1",
                    "owner": "a1",
                }
            ],
        }
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_chain_gate_requires_token_for_acceptance(tmp_path):
    args = SimpleNamespace(
        chain_id=None,
        chain_step=None,
        chain_token=None,
        resume=False,
        scenarios_file=None,
    )

    status = _module._llm_quality_build_chain_controller_gate_status(
        args=args,
        run_id="booking-lock-chain-demo",
        lane_effective="acceptance",
        output_dir=str(tmp_path / "run"),
        chain_root=str(tmp_path / "chain"),
    )

    assert status["required"] is True
    assert status["valid"] is False
    assert "chain_controller_required" in status["reasons"]


def test_chain_gate_rejects_run_id_mode_mismatch(tmp_path):
    chain_root = tmp_path / "chain"
    chain_root.mkdir(parents=True, exist_ok=True)
    state_path = chain_root / "demo.json"
    state = {
        "chain_id": "demo",
        "status": "active",
        "current_step": "lock",
        "active": {
            "step": "lock",
            "run_id": "booking-lock-chain-demo",
            "token": "tok-1",
            "resume_required": False,
        },
        "steps": {
            "lock": {
                "status": "running",
                "run_id": "booking-lock-chain-demo",
                "output_dir": str(tmp_path / "run"),
            }
        },
    }
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    args = SimpleNamespace(
        chain_id="demo",
        chain_step="lock",
        chain_token="tok-1",
        resume=False,
        scenarios_file=str(tmp_path / "replay_scenarios.json"),
    )

    status = _module._llm_quality_build_chain_controller_gate_status(
        args=args,
        run_id="booking-lock-chain-demo",
        lane_effective="acceptance",
        output_dir=str(tmp_path / "run"),
        chain_root=str(chain_root),
    )

    assert status["valid"] is False
    assert "run_id_mode_mismatch:replay:lock" in status["reasons"]
    assert "chain_step_mode_mismatch:lock:replay" in status["reasons"]


def test_chain_gate_requires_resume_when_chain_marks_resume_required(tmp_path):
    chain_root = tmp_path / "chain"
    chain_root.mkdir(parents=True, exist_ok=True)
    state_path = chain_root / "demo.json"
    state = {
        "chain_id": "demo",
        "status": "active",
        "current_step": "lock",
        "active": {
            "step": "lock",
            "run_id": "booking-lock-chain-demo",
            "token": "tok-2",
            "resume_required": True,
        },
        "steps": {
            "lock": {
                "status": "incomplete",
                "run_id": "booking-lock-chain-demo",
                "output_dir": str(tmp_path / "run"),
            }
        },
    }
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    args = SimpleNamespace(
        chain_id="demo",
        chain_step="lock",
        chain_token="tok-2",
        resume=False,
        scenarios_file=None,
    )

    status = _module._llm_quality_build_chain_controller_gate_status(
        args=args,
        run_id="booking-lock-chain-demo",
        lane_effective="acceptance",
        output_dir=str(tmp_path / "run"),
        chain_root=str(chain_root),
    )

    assert status["valid"] is False
    assert "chain_resume_required" in status["reasons"]


def test_chain_controller_prepare_and_finalize_advances_to_replay(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "quality_chain_controller.sh"
    if not script_path.exists():
        pytest.skip("quality_chain_controller.sh not present")

    run_id = "booking-lock-chain-e2e"
    output_dir = tmp_path / run_id
    pg_checklist = tmp_path / "pg_checklist.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_pg_checklist(pg_checklist)
    env = dict(os.environ)
    env["LLM_QUALITY_CHAIN_ROOT"] = str(tmp_path / "chain")

    prepare = subprocess.run(
        [
            str(script_path),
            "prepare",
            "--mode",
            "lock",
            "--run-id",
            run_id,
            "--output-dir",
            str(output_dir),
            "--pg-checklist",
            str(pg_checklist),
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    chain_id, chain_step, chain_token = prepare.stdout.strip().split("\t")
    assert chain_step == "lock"
    assert chain_token

    summary = {
        "run_id": run_id,
        "stop_reason": "done",
        "quality_status": {
            "infra_valid": True,
            "semantic_valid": True,
            "run_integrity_valid": True,
        },
        "blocking_reasons": {"reasons": {}},
        "judge": {"counts": {"judged": 40}},
    }
    manifest = {
        "run_id": run_id,
        "mode": "lock",
        "status": "canonical",
        "stop_reason": "done",
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    subprocess.run(
        [
            str(script_path),
            "finalize",
            "--mode",
            "lock",
            "--run-id",
            run_id,
            "--output-dir",
            str(output_dir),
            "--summary-path",
            str(output_dir / "summary.json"),
            "--exit-code",
            "0",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )

    status = subprocess.run(
        [str(script_path), "status", "--chain-id", chain_id],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    payload = json.loads(status.stdout)

    assert payload["steps"]["lock"]["status"] == "canonical"
    assert payload["status"] == "active"
    assert "--mode replay" in (payload.get("next_command") or "")
    assert (output_dir / "brief_for_next_agent.md").exists()


def test_chain_controller_blocks_lock_without_pg_checklist(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "quality_chain_controller.sh"
    if not script_path.exists():
        pytest.skip("quality_chain_controller.sh not present")

    run_id = "booking-lock-chain-no-pg"
    output_dir = tmp_path / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["LLM_QUALITY_CHAIN_ROOT"] = str(tmp_path / "chain")

    prepare = subprocess.run(
        [
            str(script_path),
            "prepare",
            "--mode",
            "lock",
            "--run-id",
            run_id,
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )

    assert prepare.returncode != 0
    assert "go_to_full_gate_required:missing_pg_checklist" in prepare.stderr


def test_chain_controller_blocks_lock_with_pg_checklist_missing_mapping(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "quality_chain_controller.sh"
    if not script_path.exists():
        pytest.skip("quality_chain_controller.sh not present")

    run_id = "booking-lock-chain-bad-pg"
    output_dir = tmp_path / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    pg_checklist = tmp_path / "pg_checklist_bad.json"
    pg_payload = {
        "go_to_full": {
            "PG0": {"status": "pass"},
            "PG1": {"status": "pass"},
            "PG2": {"status": "pass"},
            "PG3": {"status": "pass"},
            "PG4": {"status": "pass"},
            "PG5": {"status": "pass"},
            "PG6": {"status": "pass"},
            "root_cause_statement": "root cause exists",
        }
    }
    pg_checklist.write_text(json.dumps(pg_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    env = dict(os.environ)
    env["LLM_QUALITY_CHAIN_ROOT"] = str(tmp_path / "chain")

    prepare = subprocess.run(
        [
            str(script_path),
            "prepare",
            "--mode",
            "lock",
            "--run-id",
            run_id,
            "--output-dir",
            str(output_dir),
            "--pg-checklist",
            str(pg_checklist),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )

    assert prepare.returncode != 0
    assert "go_to_full_mapping_missing" in prepare.stderr


def test_chain_controller_blocks_lock_with_pg_checklist_invalid_target_test(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "quality_chain_controller.sh"
    if not script_path.exists():
        pytest.skip("quality_chain_controller.sh not present")

    run_id = "booking-lock-chain-bad-target-test"
    output_dir = tmp_path / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    pg_checklist = tmp_path / "pg_checklist_bad_target.json"
    pg_payload = {
        "go_to_full": {
            "PG0": {"status": "pass"},
            "PG1": {"status": "pass"},
            "PG2": {"status": "pass"},
            "PG3": {"status": "pass"},
            "PG4": {"status": "pass"},
            "PG5": {"status": "pass"},
            "PG6": {"status": "pass"},
            "root_cause_statement": "root cause exists",
            "defect_mapping": [
                {
                    "defect_class": "booking_flow_break",
                    "target_test": "truffles-api/tests/does_not_exist.py::test_missing",
                    "gate": "PG1",
                    "owner": "a1",
                }
            ],
        }
    }
    pg_checklist.write_text(json.dumps(pg_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    env = dict(os.environ)
    env["LLM_QUALITY_CHAIN_ROOT"] = str(tmp_path / "chain")

    prepare = subprocess.run(
        [
            str(script_path),
            "prepare",
            "--mode",
            "lock",
            "--run-id",
            run_id,
            "--output-dir",
            str(output_dir),
            "--pg-checklist",
            str(pg_checklist),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )

    assert prepare.returncode != 0
    assert "go_to_full_mapping_invalid:0:target_test_path_missing" in prepare.stderr
