import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
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
_TARGET_TEST_REF = (
    "truffles-api/tests/test_message_endpoint.py::"
    "test_llm_policy_core_info_lateness_signal_uses_lateness_reply"
)


def _chain_controller_script() -> Path:
    base = Path(__file__).resolve()
    script_path = base.parents[2] / "scripts" / "quality_chain_controller.sh"
    if not script_path.exists():
        pytest.skip("scripts/quality_chain_controller.sh not present", allow_module_level=True)
    return script_path


def _write_l2_summary(
    path: Path,
    *,
    run_id: str,
    semantic_valid: bool = True,
    seed: int = 7,
    lane: str = "dev",
) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "run_id": run_id,
        "finished_at": now_iso,
        "quality_status": {
            "infra_valid": True,
            "semantic_valid": semantic_valid,
            "run_integrity_valid": True,
            "manual_audit_status": "done",
            "evidence_handoff_valid": True,
            "evidence_handoff_reasons": [],
            "quality_lane_effective": lane,
        },
        "evidence_handoff": {"valid": True, "reasons": []},
        "infra_valid": True,
        "semantic_valid": semantic_valid,
        "run_integrity_valid": True,
        "config": {"quality_lane_effective": lane, "seed": seed},
        "seed": seed,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_l1_junit(
    path: Path,
    *,
    target_refs: list[str],
    failed_targets: set[str] | None = None,
    path_attr_overrides: dict[str, str] | None = None,
) -> None:
    failed_targets = failed_targets or set()
    path_attr_overrides = path_attr_overrides or {}
    now_iso = datetime.now(timezone.utc).isoformat()
    failure_count = 0
    testcase_lines = []
    for target_ref in target_refs:
        path_part, test_name = target_ref.split("::", 1)
        report_path = str(path_attr_overrides.get(target_ref) or path_part).strip() or path_part
        test_symbol = test_name.split("[", 1)[0].strip()
        class_name = report_path.replace("/", ".").removesuffix(".py")
        base = (
            f'  <testcase classname="{class_name}" '
            f'name="{test_symbol}" file="{report_path}">'
        )
        if target_ref in failed_targets:
            failure_count += 1
            testcase_lines.append(
                base + "<failure message=\"assertion failed\" />" + "</testcase>"
            )
        else:
            testcase_lines.append(base + "</testcase>")
    payload = [
        '<?xml version="1.0" encoding="utf-8"?>',
        (
            f'<testsuite name="pytest" tests="{len(target_refs)}" '
            f'failures="{failure_count}" errors="0" skipped="0" '
            f'timestamp="{now_iso}">'
        ),
        *testcase_lines,
        "</testsuite>",
        "",
    ]
    path.write_text("\n".join(payload), encoding="utf-8")


def _write_pg_checklist(
    path: Path,
    *,
    l1_junit_path: Path | None = None,
    l1_recorded_at: str | None = None,
    l2_summary_path: Path | None = None,
    l2_run_id: str | None = None,
    freshness_hours: float | None = None,
    multi_seed_summaries: list[dict] | None = None,
    multi_seed_required: list[int] | None = None,
) -> None:
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
                    "target_test": _TARGET_TEST_REF,
                    "gate": "PG1",
                    "owner": "a1",
                }
            ],
        }
    }
    if l1_junit_path is not None:
        payload["go_to_full"]["l1_evidence"] = {
            "junit_xml_path": str(l1_junit_path),
        }
        if l1_recorded_at:
            payload["go_to_full"]["l1_evidence"]["recorded_at"] = str(l1_recorded_at)
    if l2_summary_path is not None:
        payload["go_to_full"]["l2_evidence"] = {
            "summary_path": str(l2_summary_path),
            "run_id": str(l2_run_id or ""),
        }
    if freshness_hours is not None:
        payload["go_to_full"]["evidence_freshness_hours"] = float(freshness_hours)
    if multi_seed_summaries is not None:
        payload["go_to_full"]["multi_seed_evidence"] = {
            "summaries": multi_seed_summaries,
        }
        if multi_seed_required is not None:
            payload["go_to_full"]["multi_seed_evidence"]["required_seeds"] = list(
                multi_seed_required
            )
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_multi_seed_summaries(
    base_dir: Path,
    *,
    seeds: list[int],
    run_id_prefix: str,
) -> list[dict]:
    summaries: list[dict] = []
    for seed in seeds:
        summary_path = base_dir / f"l2_summary_seed_{seed}.json"
        _write_l2_summary(
            summary_path,
            run_id=f"{run_id_prefix}-{seed}",
            seed=seed,
        )
        summaries.append(
            {
                "seed": seed,
                "summary_path": str(summary_path),
            }
        )
    return summaries


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


def test_chain_controller_bootstrap_imports_existing_lock(tmp_path):
    chain_root = tmp_path / "chain"
    chain_root.mkdir(parents=True, exist_ok=True)
    output_dir = tmp_path / "run"
    output_dir.mkdir(parents=True, exist_ok=True)

    chain_id = "bootstrap-a1"
    run_id = f"booking-lock-{chain_id}"
    summary_path = output_dir / "summary.json"
    _write_l2_summary(summary_path, run_id=run_id, semantic_valid=True)

    script_path = _chain_controller_script()
    env = os.environ.copy()
    env["LLM_QUALITY_CHAIN_ROOT"] = str(chain_root)
    result = subprocess.run(
        [
            str(script_path),
            "bootstrap",
            "--mode",
            "lock",
            "--run-id",
            run_id,
            "--output-dir",
            str(output_dir),
            "--summary-path",
            str(summary_path),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    state_path = chain_root / f"{chain_id}.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["steps"]["lock"]["status"] == "canonical"
    assert state["steps"]["lock"]["output_dir"] == str(output_dir)
    assert state["active"]["step"] == "replay"
    assert "--mode replay" in (state.get("next_command") or "")
    assert f"{output_dir}/summary.json" in (state.get("next_command") or "")
    assert (output_dir / "brief_for_next_agent.md").exists()


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
    l1_junit_path = tmp_path / "l1_junit.xml"
    l2_summary_path = tmp_path / "l2_summary.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_l1_junit(l1_junit_path, target_refs=[_TARGET_TEST_REF])
    _write_l2_summary(l2_summary_path, run_id="booking-l2-chain-e2e", seed=7)
    multi_seed = _write_multi_seed_summaries(
        tmp_path,
        seeds=[7, 19, 42],
        run_id_prefix="booking-l2-chain-e2e-seed",
    )
    _write_pg_checklist(
        pg_checklist,
        l1_junit_path=l1_junit_path,
        l2_summary_path=l2_summary_path,
        l2_run_id="booking-l2-chain-e2e",
        multi_seed_summaries=multi_seed,
    )
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


def test_chain_controller_accepts_repo_target_with_nested_junit_paths(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "quality_chain_controller.sh"
    if not script_path.exists():
        pytest.skip("quality_chain_controller.sh not present")

    run_id = "booking-lock-chain-junit-path-normalized"
    output_dir = tmp_path / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    pg_checklist = tmp_path / "pg_checklist_junit_path_normalized.json"
    l1_junit_path = tmp_path / "l1_junit_path_normalized.xml"
    l2_summary_path = tmp_path / "l2_summary_junit_path_normalized.json"
    _write_l1_junit(
        l1_junit_path,
        target_refs=[_TARGET_TEST_REF],
        path_attr_overrides={_TARGET_TEST_REF: "tests/test_message_endpoint.py"},
    )
    _write_l2_summary(l2_summary_path, run_id="booking-l2-junit-path-normalized", seed=7)
    multi_seed = _write_multi_seed_summaries(
        tmp_path,
        seeds=[7, 19, 42],
        run_id_prefix="booking-l2-junit-path-normalized-seed",
    )
    _write_pg_checklist(
        pg_checklist,
        l1_junit_path=l1_junit_path,
        l2_summary_path=l2_summary_path,
        l2_run_id="booking-l2-junit-path-normalized",
        multi_seed_summaries=multi_seed,
    )
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
    assert chain_id
    assert chain_step == "lock"
    assert chain_token


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


def test_chain_controller_blocks_lock_with_pg_checklist_missing_l2_evidence(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "quality_chain_controller.sh"
    if not script_path.exists():
        pytest.skip("quality_chain_controller.sh not present")

    run_id = "booking-lock-chain-missing-l2-evidence"
    output_dir = tmp_path / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    l1_junit_path = tmp_path / "l1_junit_missing_l2.xml"
    _write_l1_junit(l1_junit_path, target_refs=[_TARGET_TEST_REF])
    pg_checklist = tmp_path / "pg_checklist_no_l2.json"
    _write_pg_checklist(pg_checklist, l1_junit_path=l1_junit_path)

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
    assert "go_to_full_l2_evidence_missing" in prepare.stderr


def test_chain_controller_blocks_lock_with_pg_checklist_missing_multi_seed(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "quality_chain_controller.sh"
    if not script_path.exists():
        pytest.skip("quality_chain_controller.sh not present")

    run_id = "booking-lock-chain-missing-multi-seed"
    output_dir = tmp_path / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    l1_junit_path = tmp_path / "l1_junit_missing_multi_seed.xml"
    l2_summary_path = tmp_path / "l2_summary_missing_multi_seed.json"
    _write_l1_junit(l1_junit_path, target_refs=[_TARGET_TEST_REF])
    _write_l2_summary(l2_summary_path, run_id="booking-l2-missing-multi-seed", seed=7)
    pg_checklist = tmp_path / "pg_checklist_missing_multi_seed.json"
    _write_pg_checklist(
        pg_checklist,
        l1_junit_path=l1_junit_path,
        l2_summary_path=l2_summary_path,
        l2_run_id="booking-l2-missing-multi-seed",
    )

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
    assert "go_to_full_multi_seed_missing" in prepare.stderr


def test_chain_controller_blocks_lock_with_pg_checklist_non_green_l2(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "quality_chain_controller.sh"
    if not script_path.exists():
        pytest.skip("quality_chain_controller.sh not present")

    run_id = "booking-lock-chain-bad-l2"
    output_dir = tmp_path / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    pg_checklist = tmp_path / "pg_checklist_bad_l2.json"
    l1_junit_path = tmp_path / "l1_junit_bad_l2.xml"
    l2_summary_path = tmp_path / "l2_summary_bad.json"
    _write_l1_junit(l1_junit_path, target_refs=[_TARGET_TEST_REF])
    _write_l2_summary(l2_summary_path, run_id="booking-l2-chain-bad", semantic_valid=False)
    _write_pg_checklist(
        pg_checklist,
        l1_junit_path=l1_junit_path,
        l2_summary_path=l2_summary_path,
        l2_run_id="booking-l2-chain-bad",
    )

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
    assert "go_to_full_l2_not_green" in prepare.stderr


def test_chain_controller_blocks_lock_with_pg_checklist_missing_l1_evidence(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "quality_chain_controller.sh"
    if not script_path.exists():
        pytest.skip("quality_chain_controller.sh not present")

    run_id = "booking-lock-chain-missing-l1-evidence"
    output_dir = tmp_path / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    pg_checklist = tmp_path / "pg_checklist_no_l1.json"
    l2_summary_path = tmp_path / "l2_summary_no_l1.json"
    _write_l2_summary(l2_summary_path, run_id="booking-l2-no-l1")
    _write_pg_checklist(
        pg_checklist,
        l2_summary_path=l2_summary_path,
        l2_run_id="booking-l2-no-l1",
    )

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
    assert "go_to_full_l1_evidence_missing" in prepare.stderr


def test_chain_controller_blocks_lock_with_pg_checklist_failed_l1_target(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "quality_chain_controller.sh"
    if not script_path.exists():
        pytest.skip("quality_chain_controller.sh not present")

    run_id = "booking-lock-chain-failed-l1"
    output_dir = tmp_path / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    pg_checklist = tmp_path / "pg_checklist_failed_l1.json"
    l1_junit_path = tmp_path / "l1_junit_failed.xml"
    l2_summary_path = tmp_path / "l2_summary_failed_l1.json"
    _write_l1_junit(
        l1_junit_path,
        target_refs=[_TARGET_TEST_REF],
        failed_targets={_TARGET_TEST_REF},
    )
    _write_l2_summary(l2_summary_path, run_id="booking-l2-failed-l1")
    _write_pg_checklist(
        pg_checklist,
        l1_junit_path=l1_junit_path,
        l2_summary_path=l2_summary_path,
        l2_run_id="booking-l2-failed-l1",
    )

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
    assert "go_to_full_l1_target_not_passed" in prepare.stderr


def test_chain_controller_blocks_lock_with_pg_checklist_stale_l1_evidence(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "quality_chain_controller.sh"
    if not script_path.exists():
        pytest.skip("quality_chain_controller.sh not present")

    run_id = "booking-lock-chain-stale-l1"
    output_dir = tmp_path / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    pg_checklist = tmp_path / "pg_checklist_stale_l1.json"
    l1_junit_path = tmp_path / "l1_junit_stale.xml"
    l2_summary_path = tmp_path / "l2_summary_stale_l1.json"
    _write_l1_junit(l1_junit_path, target_refs=[_TARGET_TEST_REF])
    _write_l2_summary(l2_summary_path, run_id="booking-l2-stale-l1")
    stale_recorded_at = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
    _write_pg_checklist(
        pg_checklist,
        l1_junit_path=l1_junit_path,
        l1_recorded_at=stale_recorded_at,
        l2_summary_path=l2_summary_path,
        l2_run_id="booking-l2-stale-l1",
        freshness_hours=24.0,
    )

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
    assert "go_to_full_l1_evidence_stale" in prepare.stderr


def test_chain_controller_replay_finalize_advances_to_canary(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "quality_chain_controller.sh"
    if not script_path.exists():
        pytest.skip("quality_chain_controller.sh not present")

    chain_id = "chain-canary-progress"
    chain_root = tmp_path / "chain"
    env = dict(os.environ)
    env["LLM_QUALITY_CHAIN_ROOT"] = str(chain_root)

    lock_run_id = f"booking-lock-{chain_id}"
    lock_output_dir = tmp_path / lock_run_id
    lock_output_dir.mkdir(parents=True, exist_ok=True)
    lock_summary_path = lock_output_dir / "summary.json"
    _write_l2_summary(lock_summary_path, run_id=lock_run_id)

    bootstrap = subprocess.run(
        [
            str(script_path),
            "bootstrap",
            "--mode",
            "lock",
            "--run-id",
            lock_run_id,
            "--output-dir",
            str(lock_output_dir),
            "--summary-path",
            str(lock_summary_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert bootstrap.returncode == 0, bootstrap.stderr

    replay_run_id = f"booking-replay-{chain_id}"
    replay_output_dir = tmp_path / replay_run_id
    replay_output_dir.mkdir(parents=True, exist_ok=True)
    prepare_replay = subprocess.run(
        [
            str(script_path),
            "prepare",
            "--mode",
            "replay",
            "--run-id",
            replay_run_id,
            "--output-dir",
            str(replay_output_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert prepare_replay.returncode == 0, prepare_replay.stderr

    replay_summary = {
        "run_id": replay_run_id,
        "stop_reason": "done",
        "quality_status": {
            "infra_valid": True,
            "semantic_valid": True,
            "run_integrity_valid": True,
            "evidence_handoff_valid": True,
            "evidence_handoff_reasons": [],
        },
        "evidence_handoff": {"valid": True, "reasons": []},
        "blocking_reasons": {"reasons": {}},
        "judge": {"counts": {"judged": 40}},
    }
    replay_manifest = {
        "run_id": replay_run_id,
        "mode": "replay",
        "status": "canonical",
        "stop_reason": "done",
    }
    replay_summary_path = replay_output_dir / "summary.json"
    replay_manifest_path = replay_output_dir / "run_manifest.json"
    replay_summary_path.write_text(
        json.dumps(replay_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    replay_manifest_path.write_text(
        json.dumps(replay_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    finalize_replay = subprocess.run(
        [
            str(script_path),
            "finalize",
            "--mode",
            "replay",
            "--run-id",
            replay_run_id,
            "--output-dir",
            str(replay_output_dir),
            "--summary-path",
            str(replay_summary_path),
            "--exit-code",
            "0",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert finalize_replay.returncode == 0, finalize_replay.stderr

    status = subprocess.run(
        [str(script_path), "status", "--chain-id", chain_id],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    payload = json.loads(status.stdout)
    assert payload["steps"]["replay"]["status"] == "canonical"
    assert payload["active"]["step"] == "canary"
    assert "--mode canary" in (payload.get("next_command") or "")


def test_chain_controller_blocks_prepare_when_previous_step_evidence_handoff_invalid(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "quality_chain_controller.sh"
    if not script_path.exists():
        pytest.skip("quality_chain_controller.sh not present")

    chain_id = "chain-evidence-handoff-block"
    chain_root = tmp_path / "chain"
    env = dict(os.environ)
    env["LLM_QUALITY_CHAIN_ROOT"] = str(chain_root)

    lock_run_id = f"booking-lock-{chain_id}"
    lock_output_dir = tmp_path / lock_run_id
    lock_output_dir.mkdir(parents=True, exist_ok=True)
    lock_summary_path = lock_output_dir / "summary.json"
    lock_summary = {
        "run_id": lock_run_id,
        "stop_reason": "done",
        "quality_status": {
            "infra_valid": True,
            "semantic_valid": True,
            "run_integrity_valid": True,
            "manual_audit_status": "done",
            "evidence_handoff_valid": False,
            "evidence_handoff_reasons": ["manual_audit_not_done"],
        },
        "blocking_reasons": {"reasons": {}},
        "judge": {"counts": {"judged": 40}},
    }
    lock_summary_path.write_text(
        json.dumps(lock_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    bootstrap = subprocess.run(
        [
            str(script_path),
            "bootstrap",
            "--mode",
            "lock",
            "--run-id",
            lock_run_id,
            "--output-dir",
            str(lock_output_dir),
            "--summary-path",
            str(lock_summary_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert bootstrap.returncode == 0, bootstrap.stderr

    replay_run_id = f"booking-replay-{chain_id}"
    replay_output_dir = tmp_path / replay_run_id
    replay_output_dir.mkdir(parents=True, exist_ok=True)
    prepare_replay = subprocess.run(
        [
            str(script_path),
            "prepare",
            "--mode",
            "replay",
            "--run-id",
            replay_run_id,
            "--output-dir",
            str(replay_output_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert prepare_replay.returncode != 0
    assert "missing_evidence_handoff:lock:summary_evidence_handoff_invalid:manual_audit_not_done" in prepare_replay.stderr


def test_chain_controller_canary_failure_executes_rollback(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "quality_chain_controller.sh"
    if not script_path.exists():
        pytest.skip("quality_chain_controller.sh not present")

    chain_id = "chain-canary-rollback"
    chain_root = tmp_path / "chain"
    env = dict(os.environ)
    env["LLM_QUALITY_CHAIN_ROOT"] = str(chain_root)

    lock_run_id = f"booking-lock-{chain_id}"
    lock_output_dir = tmp_path / lock_run_id
    lock_output_dir.mkdir(parents=True, exist_ok=True)
    lock_summary_path = lock_output_dir / "summary.json"
    _write_l2_summary(lock_summary_path, run_id=lock_run_id)
    bootstrap = subprocess.run(
        [
            str(script_path),
            "bootstrap",
            "--mode",
            "lock",
            "--run-id",
            lock_run_id,
            "--output-dir",
            str(lock_output_dir),
            "--summary-path",
            str(lock_summary_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert bootstrap.returncode == 0, bootstrap.stderr

    replay_run_id = f"booking-replay-{chain_id}"
    replay_output_dir = tmp_path / replay_run_id
    replay_output_dir.mkdir(parents=True, exist_ok=True)
    prepare_replay = subprocess.run(
        [
            str(script_path),
            "prepare",
            "--mode",
            "replay",
            "--run-id",
            replay_run_id,
            "--output-dir",
            str(replay_output_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert prepare_replay.returncode == 0, prepare_replay.stderr

    replay_summary = {
        "run_id": replay_run_id,
        "stop_reason": "done",
        "quality_status": {
            "infra_valid": True,
            "semantic_valid": True,
            "run_integrity_valid": True,
            "evidence_handoff_valid": True,
            "evidence_handoff_reasons": [],
        },
        "evidence_handoff": {"valid": True, "reasons": []},
        "blocking_reasons": {"reasons": {}},
        "judge": {"counts": {"judged": 40}},
    }
    replay_manifest = {
        "run_id": replay_run_id,
        "mode": "replay",
        "status": "canonical",
        "stop_reason": "done",
    }
    replay_summary_path = replay_output_dir / "summary.json"
    replay_manifest_path = replay_output_dir / "run_manifest.json"
    replay_summary_path.write_text(
        json.dumps(replay_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    replay_manifest_path.write_text(
        json.dumps(replay_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    finalize_replay = subprocess.run(
        [
            str(script_path),
            "finalize",
            "--mode",
            "replay",
            "--run-id",
            replay_run_id,
            "--output-dir",
            str(replay_output_dir),
            "--summary-path",
            str(replay_summary_path),
            "--exit-code",
            "0",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert finalize_replay.returncode == 0, finalize_replay.stderr

    canary_run_id = f"booking-canary-{chain_id}"
    canary_output_dir = tmp_path / canary_run_id
    canary_output_dir.mkdir(parents=True, exist_ok=True)
    prepare_canary = subprocess.run(
        [
            str(script_path),
            "prepare",
            "--mode",
            "canary",
            "--run-id",
            canary_run_id,
            "--output-dir",
            str(canary_output_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert prepare_canary.returncode == 0, prepare_canary.stderr

    canary_summary = {
        "run_id": canary_run_id,
        "stop_reason": "semantic_regression",
        "quality_status": {
            "infra_valid": True,
            "semantic_valid": False,
            "run_integrity_valid": True,
        },
        "blocking_reasons": {"reasons": {"wrong_action": 1}},
        "judge": {"counts": {"judged": 40}},
    }
    canary_manifest = {
        "run_id": canary_run_id,
        "mode": "canary",
        "status": "failed",
        "stop_reason": "semantic_regression",
    }
    canary_summary_path = canary_output_dir / "summary.json"
    canary_manifest_path = canary_output_dir / "run_manifest.json"
    canary_summary_path.write_text(
        json.dumps(canary_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    canary_manifest_path.write_text(
        json.dumps(canary_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    finalize_canary = subprocess.run(
        [
            str(script_path),
            "finalize",
            "--mode",
            "canary",
            "--run-id",
            canary_run_id,
            "--output-dir",
            str(canary_output_dir),
            "--summary-path",
            str(canary_summary_path),
            "--exit-code",
            "1",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert finalize_canary.returncode == 0, finalize_canary.stderr

    status = subprocess.run(
        [str(script_path), "status", "--chain-id", chain_id],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    payload = json.loads(status.stdout)
    rollback = payload.get("rollback") if isinstance(payload.get("rollback"), dict) else {}
    assert payload["status"] == "blocked"
    assert payload["blocked_reason"] == "canary_rollback_executed"
    assert rollback.get("status") == "executed"
    assert rollback.get("source") == "auto_canary_no_go"
    assert rollback.get("failed_mode") == "canary"
    assert rollback.get("baseline_step") == "replay"
    assert payload.get("next_command") is None
    assert (canary_output_dir / "rollback.json").exists()
    assert (chain_root / f"{chain_id}-rollback.json").exists()


def test_chain_controller_manual_rollback_command(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "quality_chain_controller.sh"
    if not script_path.exists():
        pytest.skip("quality_chain_controller.sh not present")

    chain_id = "chain-manual-rollback"
    chain_root = tmp_path / "chain"
    env = dict(os.environ)
    env["LLM_QUALITY_CHAIN_ROOT"] = str(chain_root)

    lock_run_id = f"booking-lock-{chain_id}"
    lock_output_dir = tmp_path / lock_run_id
    lock_output_dir.mkdir(parents=True, exist_ok=True)
    lock_summary_path = lock_output_dir / "summary.json"
    _write_l2_summary(lock_summary_path, run_id=lock_run_id)

    bootstrap = subprocess.run(
        [
            str(script_path),
            "bootstrap",
            "--mode",
            "lock",
            "--run-id",
            lock_run_id,
            "--output-dir",
            str(lock_output_dir),
            "--summary-path",
            str(lock_summary_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert bootstrap.returncode == 0, bootstrap.stderr

    rollback = subprocess.run(
        [
            str(script_path),
            "rollback",
            "--chain-id",
            chain_id,
            "--reason",
            "manual-stop",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert rollback.returncode == 0, rollback.stderr

    status = subprocess.run(
        [str(script_path), "status", "--chain-id", chain_id],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    payload = json.loads(status.stdout)
    rollback_payload = payload.get("rollback") if isinstance(payload.get("rollback"), dict) else {}
    assert payload["status"] == "blocked"
    assert payload["blocked_reason"] == "rollback_executed"
    assert rollback_payload.get("source") == "manual"
    assert rollback_payload.get("reason") == "manual-stop"
