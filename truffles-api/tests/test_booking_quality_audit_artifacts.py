import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "ops" / "diagnose.py"


def _write_run_artifacts(run_dir: Path, run_id: str, *, tags, strict_ok, strict_reasons, judge_verdict, judge_reasons):
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "brief.md").write_text("# brief\n", encoding="utf-8")
    (run_dir / "scenarios.json").write_text(
        json.dumps(
            {
                "count": 1,
                "dialogs": [
                    {
                        "dialog_id": 1,
                        "goal": "audit artifact coverage",
                        "turns": [
                            {
                                "kind": "text",
                                "text": "Хочу записаться на маникюр",
                                "tags": list(tags),
                                "expect": {"reply_type": "time", "action": "collect"},
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    decision_meta = {
        "intent": "booking",
        "action": "booking_prompt",
        "source": "llm_policy_core",
        "expected_reply_type": "time",
        "policy_core_mode": "live",
        "llm_policy_core": {
            "intent": "booking",
            "final_action": "collect",
            "final_tool_action": "collect",
            "next_question": "datetime",
            "resolution_mode": "collect_missing_slots",
        },
    }
    decision_trace = [
        {"stage": "policy_core_guard", "decision": "accept_owner", "reason": "ok"},
        {"stage": "question_contract", "decision": "booking_question", "expected_reply_type": "time"},
    ]
    response_row = {
        "dialog_id": 1,
        "dialog_goal": "audit artifact coverage",
        "dialog_index": 1,
        "turn_index": 1,
        "turn_kind": "text",
        "turn_tags": list(tags),
        "turn_text": "Хочу записаться на маникюр",
        "expected_reply_type": "time",
        "conversation_state": "bot_active",
        "message_id": f"{run_id}-001",
        "decision_meta": decision_meta,
        "decision_trace": decision_trace,
        "evaluation": {
            "ok": strict_ok,
            "strict_ok": strict_ok,
            "reasons": list(strict_reasons),
            "strict_reasons": list(strict_reasons),
            "semantic_strict_reasons": list(strict_reasons),
            "hard_reasons": [],
        },
        "judge": {
            "verdict": judge_verdict,
            "reasons": list(judge_reasons),
            "summary": "manual review needed",
            "score": 0 if judge_verdict == "fail" else 1,
        },
        "inline_response_text": "На какое время вас записать?",
        "turn_expectations": {"reply_type": "time", "action": "collect"},
    }
    (run_dir / "responses.jsonl").write_text(
        json.dumps(response_row, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    trace_row = {
        "dialog_id": 1,
        "dialog_index": 1,
        "turn_index": 1,
        "message_id": f"{run_id}-001",
        "decision_meta": decision_meta,
        "decision_trace": decision_trace,
    }
    (run_dir / "trace_bundle.jsonl").write_text(
        json.dumps(trace_row, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (run_dir / "summary.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "infra_valid": True,
                "semantic_valid": strict_ok,
                "stop_reason": "completed",
                "config": {"count": 1},
                "quality_status": {
                    "infra_valid": True,
                    "semantic_valid": strict_ok,
                    "run_integrity_reasons": [],
                    "manual_audit_required": True,
                    "manual_audit_status": "pending",
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _run_audit(run_dir: Path):
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "llm-quality-audit", "--run-dir", str(run_dir), "--status", "done", "--pretty"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_llm_quality_audit_emits_workspace_family_registry_and_judge_conflicts(tmp_path):
    run_dir = tmp_path / "run-audit-artifacts"
    _write_run_artifacts(
        run_dir,
        "run-audit-artifacts",
        tags=["booking", "check_booking"],
        strict_ok=False,
        strict_reasons=["booking_flow_break", "expected_action_mismatch"],
        judge_verdict="pass",
        judge_reasons=[],
    )

    result = _run_audit(run_dir)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    workspace_json = run_dir / "manual_audit_workspace.json"
    family_registry_json = run_dir / "family_registry.json"
    judge_conflicts_jsonl = run_dir / "judge_conflicts.jsonl"
    assert workspace_json.exists()
    assert family_registry_json.exists()
    assert judge_conflicts_jsonl.exists()
    assert payload["artifacts"]["manual_audit_workspace_json"] == str(workspace_json)
    assert payload["artifacts"]["family_registry_json"] == str(family_registry_json)
    assert payload["judge_conflicts"]["count"] == 1

    workspace = json.loads(workspace_json.read_text(encoding="utf-8"))
    assert workspace["turns"][0]["provisional_primary_bucket"] == "product"
    assert "booking slot continuity / collect->commit" in workspace["turns"][0]["provisional_mechanism_hints"]
    assert workspace["turns"][0]["path_scaffold"]["owner_output"]["next_question"] == "datetime"

    registry = json.loads(family_registry_json.read_text(encoding="utf-8"))
    assert registry["backlog_summary"]["product"]["family_count"] >= 1
    assert any(
        family["primary_bucket"] == "product"
        and "oracle" in family["buckets"]
        and family["turn_count"] == 1
        for family in registry["families"]
    )

    conflicts = [json.loads(line) for line in judge_conflicts_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(conflicts) == 1
    assert conflicts[0]["strict_ok"] is False
    assert conflicts[0]["judge_verdict"] == "pass"


def test_llm_quality_trends_command_aggregates_run_dirs(tmp_path):
    run_a = tmp_path / "run-a"
    run_b = tmp_path / "run-b"
    _write_run_artifacts(
        run_a,
        "run-a",
        tags=["booking", "check_booking"],
        strict_ok=False,
        strict_reasons=["booking_flow_break"],
        judge_verdict="fail",
        judge_reasons=["bot skipped required booking step"],
    )
    _write_run_artifacts(
        run_b,
        "run-b",
        tags=["parking", "info"],
        strict_ok=False,
        strict_reasons=["hallucinated_fact"],
        judge_verdict="fail",
        judge_reasons=["parking answer is irrelevant"],
    )
    assert _run_audit(run_a).returncode == 0
    assert _run_audit(run_b).returncode == 0

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "llm-quality-trends",
            "--run-dir",
            str(run_a),
            "--run-dir",
            str(run_b),
            "--pretty",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["run_count"] == 2
    assert payload["bucket_totals"]["product"]["family_count"] >= 2
    mechanism_hints = {entry["mechanism_hint"] for entry in payload["mechanism_trends"]}
    assert "booking slot continuity / collect->commit" in mechanism_hints
    assert "fact selection / fact composition" in mechanism_hints
