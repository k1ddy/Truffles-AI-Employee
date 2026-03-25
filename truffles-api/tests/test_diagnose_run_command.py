import json
import shlex
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
        pytest.skip(
            "ops/diagnose.py not present in test runtime image",
            allow_module_level=True,
        )
    spec = spec_from_file_location("diagnose_script", script_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_module = _load_module()


def test_run_command_passes_timeout(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_run(command, *, capture_output, text, timeout, env=None):
        captured["command"] = command
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["timeout"] = timeout
        captured["env"] = env
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr(_module.subprocess, "run", _fake_run)
    result = _module.run_command(["echo", "ok"], timeout=7)

    assert result.returncode == 0
    assert captured["timeout"] == 7
    assert captured["capture_output"] is True
    assert captured["text"] is True
    assert captured["env"] is None


def test_run_command_timeout_returns_completed_process(monkeypatch):
    def _fake_run(command, *, capture_output, text, timeout, env=None):
        raise subprocess.TimeoutExpired(command, timeout, output="partial", stderr="slow")

    monkeypatch.setattr(_module.subprocess, "run", _fake_run)
    result = _module.run_command(["docker", "exec", "slow"], timeout=1)

    assert result.returncode == 124
    assert "partial" in result.stdout
    assert "timeout" in result.stderr.lower()
    assert "docker exec slow" in result.stderr


def test_run_command_timeout_redacts_sensitive_cli_values(monkeypatch):
    def _fake_run(command, *, capture_output, text, timeout, env=None):
        raise subprocess.TimeoutExpired(command, timeout, output="", stderr="")

    monkeypatch.setattr(_module.subprocess, "run", _fake_run)
    result = _module.run_command(
        [
            "python3",
            "scripts/booking_dialog_scenarios.py",
            "--llm-api-key",
            "sk-secret-value",
        ],
        timeout=1,
    )

    assert "sk-secret-value" not in result.stderr
    assert "--llm-api-key '<redacted>'" in result.stderr


def test_llm_quality_generate_batch_uses_scenario_timeout(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_run_command(command, *, timeout=None, env=None):
        captured["command"] = command
        captured["timeout"] = timeout
        captured["env"] = env
        payload = {"dialogs": [{"dialog_id": "d1", "turns": []}], "warnings": {}}
        return subprocess.CompletedProcess(command, 0, stdout=str(payload).replace("'", '"'), stderr="")

    args = SimpleNamespace(
        min_turns=10,
        max_turns=15,
        mode="llm",
        media_mode="text",
        media_kind="photo",
        client_slug="demo_salon",
        branch_slug="almaty-center",
        scenario_coverage="booking,info,interrupt,handoff",
        include_media=True,
        llm_model="gpt-4o-mini",
        llm_base_url="https://api.openai.com",
        llm_api_key="test-key",
        scenario_llm_batch_size=2,
        scenario_llm_max_attempts=1,
        scenario_llm_request_timeout=35.0,
        scenario_llm_attempt_backoff=0.6,
        scenario_progress_stderr=False,
        scenario_gen_timeout=None,
    )

    monkeypatch.setenv("DIAGNOSE_SCENARIO_GEN_TIMEOUT_SEC", "123")
    monkeypatch.setattr(_module, "_llm_quality_dialog_script", lambda: "/tmp/fake_script.py")
    monkeypatch.setattr(_module, "run_command", _fake_run_command)

    dialogs, warnings, error = _module._llm_quality_generate_batch(
        args,
        count=1,
        seed=42,
        scenario_context_path="/tmp/scenario_context.json",
    )

    assert error is None
    assert len(dialogs) == 1
    assert warnings == {}
    assert captured["timeout"] == 123.0
    assert "--llm-api-key" not in captured["command"]
    assert captured["env"]["OPENAI_API_KEY"] == "test-key"
    assert "--client-slug" in captured["command"]
    assert "demo_salon" in captured["command"]
    assert "--branch-slug" in captured["command"]
    assert "almaty-center" in captured["command"]
    assert "--scenario-context-file" in captured["command"]
    assert "/tmp/scenario_context.json" in captured["command"]


def test_llm_quality_generate_batch_enables_progress_stderr_for_generated_llm_by_default(
    monkeypatch,
):
    captured: dict[str, object] = {}

    def _fake_run_command(command, *, timeout=None, env=None):
        captured["command"] = command
        payload = {"dialogs": [{"dialog_id": "d1", "turns": []}], "warnings": {}}
        return subprocess.CompletedProcess(command, 0, stdout=str(payload).replace("'", '"'), stderr="")

    args = SimpleNamespace(
        min_turns=10,
        max_turns=15,
        mode="llm",
        media_mode="text",
        media_kind="photo",
        client_slug="demo_salon",
        branch_slug=None,
        scenarios_file=None,
        scenario_coverage="booking,info,interrupt,handoff",
        include_media=True,
        llm_model="gpt-4o-mini",
        llm_base_url="https://api.openai.com",
        llm_api_key="test-key",
        scenario_llm_batch_size=2,
        scenario_llm_max_attempts=None,
        scenario_llm_request_timeout=60.0,
        scenario_llm_attempt_backoff=0.6,
        scenario_progress_stderr=None,
        scenario_gen_timeout=None,
    )

    monkeypatch.setenv("DIAGNOSE_SCENARIO_GEN_TIMEOUT_SEC", "10")
    monkeypatch.setattr(_module, "_llm_quality_dialog_script", lambda: "/tmp/fake_script.py")
    monkeypatch.setattr(_module, "run_command", _fake_run_command)

    dialogs, warnings, error = _module._llm_quality_generate_batch(
        args,
        count=1,
        seed=42,
        scenario_context_path="/tmp/scenario_context.json",
    )

    assert error is None
    assert len(dialogs) == 1
    assert warnings == {}
    assert "--llm-max-attempts" in captured["command"]
    assert captured["command"][captured["command"].index("--llm-max-attempts") + 1] == "3"
    assert "--progress-stderr" in captured["command"]


def test_llm_quality_generate_batch_expands_timeout_budget_for_llm(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_run_command(command, *, timeout=None, env=None):
        captured["command"] = command
        captured["timeout"] = timeout
        captured["env"] = env
        payload = {"dialogs": [{"dialog_id": "d1", "turns": []}], "warnings": {}}
        return subprocess.CompletedProcess(command, 0, stdout=str(payload).replace("'", '"'), stderr="")

    args = SimpleNamespace(
        min_turns=10,
        max_turns=15,
        mode="llm",
        media_mode="text",
        media_kind="photo",
        client_slug="demo_salon",
        branch_slug=None,
        scenario_coverage="booking,info,interrupt,handoff",
        include_media=True,
        llm_model="gpt-4o-mini",
        llm_base_url="https://api.openai.com",
        llm_api_key="test-key",
        scenario_llm_batch_size=2,
        scenario_llm_max_attempts=1,
        scenario_llm_request_timeout=60.0,
        scenario_llm_attempt_backoff=0.6,
        scenario_progress_stderr=True,
        scenario_gen_timeout=None,
    )

    monkeypatch.setenv("DIAGNOSE_SCENARIO_GEN_TIMEOUT_SEC", "10")
    monkeypatch.setattr(_module, "_llm_quality_dialog_script", lambda: "/tmp/fake_script.py")
    monkeypatch.setattr(_module, "run_command", _fake_run_command)

    dialogs, warnings, error = _module._llm_quality_generate_batch(
        args,
        count=5,
        seed=42,
        scenario_context_path="/tmp/scenario_context.json",
    )

    assert error is None
    assert len(dialogs) == 1
    assert warnings == {}
    assert captured["timeout"] == pytest.approx(205.0)
    assert "--progress-stderr" in captured["command"]


def test_llm_quality_generate_batch_uses_bounded_inner_retry_default(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_run_command(command, *, timeout=None, env=None):
        captured["command"] = command
        captured["timeout"] = timeout
        payload = {"dialogs": [{"dialog_id": "d1", "turns": []}], "warnings": {}}
        return subprocess.CompletedProcess(command, 0, stdout=str(payload).replace("'", '"'), stderr="")

    args = SimpleNamespace(
        min_turns=10,
        max_turns=15,
        mode="llm",
        media_mode="text",
        media_kind="photo",
        client_slug="demo_salon",
        branch_slug=None,
        scenarios_file=None,
        scenario_coverage="booking,info,interrupt,handoff",
        include_media=True,
        llm_model="gpt-4o-mini",
        llm_base_url="https://api.openai.com",
        llm_api_key="test-key",
        scenario_llm_batch_size=2,
        scenario_llm_max_attempts=None,
        scenario_llm_request_timeout=60.0,
        scenario_llm_attempt_backoff=0.6,
        scenario_progress_stderr=None,
        scenario_gen_timeout=None,
    )

    monkeypatch.setenv("DIAGNOSE_SCENARIO_GEN_TIMEOUT_SEC", "10")
    monkeypatch.delenv("BOOKING_SCENARIO_LLM_MAX_ATTEMPTS", raising=False)
    monkeypatch.setattr(_module, "_llm_quality_dialog_script", lambda: "/tmp/fake_script.py")
    monkeypatch.setattr(_module, "run_command", _fake_run_command)

    dialogs, warnings, error = _module._llm_quality_generate_batch(
        args,
        count=1,
        seed=42,
        scenario_context_path="/tmp/scenario_context.json",
    )

    assert error is None
    assert len(dialogs) == 1
    assert warnings == {}
    assert captured["timeout"] == pytest.approx(205.0)
    assert "--llm-max-attempts" in captured["command"]
    assert captured["command"][captured["command"].index("--llm-max-attempts") + 1] == "3"


def test_normalize_scenario_generation_error_includes_last_progress():
    stderr = "\n".join(
        [
            json.dumps(
                {
                    "stage": "booking_scenario_llm_progress",
                    "batch_index": 2,
                    "attempt": 1,
                    "event": "batch_attempt_error",
                }
            ),
            "RuntimeError: timed out while waiting for llm batch",
        ]
    )

    assert (
        _module._normalize_scenario_generation_error(stderr)
        == "timed out while waiting for llm batch"
    )

    timeout_only = "\n".join(
        [
            json.dumps(
                {
                    "stage": "booking_scenario_llm_progress",
                    "batch_index": 3,
                    "attempt": 1,
                    "event": "batch_attempt_error",
                    "error": "inner llm request timed out",
                }
            ),
            "timed out while waiting for llm batch",
        ]
    )

    assert (
        _module._normalize_scenario_generation_error(timeout_only)
        == (
            "scenario_generation_timeout "
            '(batch=3 attempt=1 event=batch_attempt_error error="inner llm request timed out")'
        )
    )


def test_llm_quality_structured_meta_expectation_is_strong_oracle():
    expectations = _module._llm_quality_extract_expectations(
        {
            "tags": ["booking"],
            "expect": {
                "action": None,
                "info_sections": [],
                "reply_type": None,
                "state": None,
                "expected_reply": None,
                "allow_booking_stall": False,
                "meta": {
                    "action": "booking_prompt",
                    "expected_reply_type": "time",
                },
                "trace_contains": [
                    {
                        "stage": "question_contract",
                        "decision": "set",
                        "expected_reply_type": "time",
                    }
                ],
            },
        }
    )

    assert expectations["meta"]["expected_reply_type"] == "time"
    assert expectations["trace_contains"][0]["stage"] == "question_contract"
    assert _module._llm_quality_is_weak_oracle_expectation(expectations) is False


def test_llm_quality_service_choice_booking_prompt_contract_catches_wrong_handoff_path():
    expectations = _module._llm_quality_extract_expectations(
        {
            "tags": ["booking"],
            "expect": {
                "action": None,
                "info_sections": [],
                "reply_type": "service_choice",
                "state": "bot_active",
                "expected_reply": True,
                "allow_booking_stall": False,
            },
        }
    )

    good_reasons = _module._llm_quality_evaluate_turn(
        meta={
            "action": "booking_prompt",
            "source": "llm_policy_core",
            "tool_action": "collect",
            "expected_reply_type": "service_choice",
            "expected_reply_reason": "booking_prompt",
        },
        trace_entries=[
            {
                "stage": "question_contract",
                "decision": "set",
                "expected_reply_type": "service_choice",
                "reason": "booking_prompt",
            }
        ],
        trace_error=None,
        state="bot_active",
        conv_meta={},
        handover_meta=None,
        bot_response=True,
        expected_response=True,
        expected_action=expectations.get("action"),
        expected_info_sections=expectations.get("info_sections"),
        expected_reply_type=expectations.get("reply_type"),
        expected_state=expectations.get("state"),
        expected_reply=expectations.get("expected_reply"),
        actual_expected_reply_type="service_choice",
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=expectations.get("allow_booking_stall"),
        outbox_text="На какую услугу хотите записаться?",
        outbox_payload=None,
        tool_signals={},
        outbox_summary={"count": 1, "status": "sent"},
        outbox_payload_status="sent",
        bot_response_inferred_duplicate_ack=False,
        meta_error=None,
        webhook_error=None,
        expected_meta=expectations.get("meta"),
        expected_meta_any=expectations.get("meta_any"),
        expected_meta_contains=expectations.get("meta_contains"),
        expected_trace_contains=expectations.get("trace_contains"),
    )
    assert good_reasons == []

    wrong_reasons = _module._llm_quality_evaluate_turn(
        meta={
            "action": "escalate",
            "source": "consultant_core_runtime",
            "tool_action": "handoff",
        },
        trace_entries=[
            {
                "stage": "turn_planner_safe_explicit_handoff_owner",
                "decision": "reply",
                "tool_action": "handoff",
            }
        ],
        trace_error=None,
        state="pending",
        conv_meta={},
        handover_meta={"status": "pending"},
        bot_response=False,
        expected_response=True,
        expected_action=expectations.get("action"),
        expected_info_sections=expectations.get("info_sections"),
        expected_reply_type=expectations.get("reply_type"),
        expected_state=expectations.get("state"),
        expected_reply=expectations.get("expected_reply"),
        actual_expected_reply_type=None,
        info_tags=[],
        info_answered={},
        booking_active=True,
        booking_progress_expected=False,
        booking_progressed=None,
        allow_booking_stall=expectations.get("allow_booking_stall"),
        outbox_text=None,
        outbox_payload=None,
        tool_signals={},
        outbox_summary={"count": 0, "status": None},
        outbox_payload_status=None,
        bot_response_inferred_duplicate_ack=False,
        meta_error=None,
        webhook_error=None,
        expected_meta=expectations.get("meta"),
        expected_meta_any=expectations.get("meta_any"),
        expected_meta_contains=expectations.get("meta_contains"),
        expected_trace_contains=expectations.get("trace_contains"),
    )

    assert "expected_action_mismatch" in wrong_reasons
    assert "expected_reply_type_mismatch" in wrong_reasons
    assert "expected_meta_mismatch" in wrong_reasons
    assert "expected_trace_miss" in wrong_reasons


def test_llm_quality_build_scenario_context_merges_pack_and_capabilities(monkeypatch):
    monkeypatch.setattr(
        _module,
        "_llm_quality_fetch_latest_capability_payload",
        lambda _db_user, *, client_id, scope, branch_id=None: (
            {
                "domain_slug": "clinic",
                "tools": {"allow": ["calendar.*"]},
                "allowed_fact_scopes": ["info.location"],
            },
            None,
        )
        if scope == "client"
        else (
            {
                "tools": {"deny": ["consult.*"]},
                "handoff_policy": "manager_request_only",
            },
            None,
        ),
    )

    scenario_context = _module._llm_quality_build_scenario_context(
        db_user="postgres",
        client_slug="clinic_pack",
        branch_slug="branch-a",
        client_meta={"client_id": "client-1", "branch_id": "branch-1", "branch_slug": "branch-a"},
        pack_context={
            "truth": {
                "salon": {
                    "name": "MedCare",
                    "services_summary": "Диагностика и базовые обследования.",
                    "communication": {"languages": ["ru", "kk"]},
                },
                "services_catalog": [
                    {"name": "УЗИ брюшной полости"},
                    {"name": "ЭКГ"},
                ],
                "masters_catalog": {
                    "specialists": [{"name": "Др. Айгерим"}],
                },
            },
            "errors": {},
        },
    )

    assert scenario_context["client_slug"] == "clinic_pack"
    assert scenario_context["branch_slug"] == "branch-a"
    assert scenario_context["business"]["display_name"] == "MedCare"
    assert scenario_context["business"]["languages"] == ["ru", "kk"]
    assert scenario_context["services"] == ["УЗИ брюшной полости", "ЭКГ"]
    assert scenario_context["specialists"] == ["Др. Айгерим"]
    assert scenario_context["capabilities"]["domain_slug"] == "clinic"
    assert scenario_context["capabilities"]["tools"]["allow"] == ["calendar.*"]
    assert scenario_context["capabilities"]["tools"]["deny"] == ["consult.*"]
    assert scenario_context["capabilities"]["handoff_policy"] == "manager_request_only"


def test_prepare_output_dir_resume_keeps_existing_artifacts(tmp_path):
    output_dir = tmp_path / "run"
    output_dir.mkdir(parents=True)
    artifact = output_dir / "summary.json"
    artifact.write_text("{}", encoding="utf-8")

    resolved = _module._llm_quality_prepare_output_dir(
        str(output_dir),
        allow_overwrite=False,
        resume=True,
    )

    assert Path(resolved) == output_dir
    assert artifact.exists()


def test_prepare_output_dir_rejects_resume_and_overwrite(tmp_path):
    output_dir = tmp_path / "run"
    output_dir.mkdir(parents=True)
    (output_dir / "summary.json").write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit):
        _module._llm_quality_prepare_output_dir(
            str(output_dir),
            allow_overwrite=True,
            resume=True,
        )


def test_build_command_from_args_includes_resume_flag():
    args = SimpleNamespace()
    command = _module._llm_quality_build_command_from_args(
        args,
        run_id="resume-demo",
        output_dir="/tmp/booking_quality/resume-demo",
        resume=True,
    )
    parts = shlex.split(command)

    assert "--resume" in parts
    assert "--allow-output-overwrite" not in parts


def test_run_manifest_resume_command_uses_resume_not_overwrite(tmp_path):
    output_dir = tmp_path / "run"
    output_dir.mkdir(parents=True)
    summary = {
        "run_id": "resume-run",
        "started_at": "2026-02-27T00:00:00+00:00",
        "finished_at": "2026-02-27T00:10:00+00:00",
        "stop_reason": "in_progress",
        "quality_status": {
            "infra_valid": False,
            "semantic_valid": False,
            "run_integrity_valid": False,
        },
    }
    args = SimpleNamespace(run_id="resume-run", output_dir=str(output_dir))

    _module._llm_quality_write_run_manifest(
        args=args,
        run_id="resume-run",
        output_dir=str(output_dir),
        summary=summary,
        run_economy_status={},
        runtime_preflight={},
        stop_reason="in_progress",
    )
    manifest_path = output_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    resume_command = manifest.get("resume_command") or ""

    assert "--resume" in resume_command
    assert "--allow-output-overwrite" not in resume_command


def test_run_manifest_preserves_command_when_rewritten_without_args(tmp_path):
    output_dir = tmp_path / "run"
    output_dir.mkdir(parents=True)
    initial_summary = {
        "run_id": "resume-run",
        "started_at": "2026-02-27T00:00:00+00:00",
        "finished_at": "2026-02-27T00:10:00+00:00",
        "stop_reason": "in_progress",
        "quality_status": {
            "infra_valid": False,
            "semantic_valid": False,
            "run_integrity_valid": False,
        },
    }
    args = SimpleNamespace(
        run_id="resume-run",
        output_dir=str(output_dir),
        judge_mode="off",
        allow_judge_off=True,
    )

    _module._llm_quality_write_run_manifest(
        args=args,
        run_id="resume-run",
        output_dir=str(output_dir),
        summary=initial_summary,
        run_economy_status={},
        runtime_preflight={},
        stop_reason="in_progress",
    )
    manifest_path = output_dir / "run_manifest.json"
    initial_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    rewritten_summary = {
        "run_id": "resume-run",
        "started_at": "2026-02-27T00:00:00+00:00",
        "finished_at": "2026-02-27T00:20:00+00:00",
        "stop_reason": None,
        "quality_status": {
            "infra_valid": True,
            "semantic_valid": True,
            "run_integrity_valid": True,
            "manual_audit_status": "done",
        },
    }
    _module._llm_quality_write_run_manifest(
        args=None,
        run_id="resume-run",
        output_dir=str(output_dir),
        summary=rewritten_summary,
        run_economy_status={},
        runtime_preflight={},
        stop_reason=None,
    )
    rewritten_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert initial_manifest.get("command")
    assert rewritten_manifest.get("command") == initial_manifest.get("command")
    assert rewritten_manifest.get("args") == initial_manifest.get("args")


def test_llm_quality_normalize_matrix_branch_slugs_preserves_alignment():
    assert _module._llm_quality_normalize_matrix_branch_slugs(
        "branch-a,,branch-c",
        expected_count=3,
    ) == ["branch-a", None, "branch-c"]

    with pytest.raises(ValueError):
        _module._llm_quality_normalize_matrix_branch_slugs(
            "branch-a,branch-b",
            expected_count=3,
        )


def test_llm_quality_build_scenario_context_contract_status_detects_service_hits(tmp_path):
    scenarios_path = tmp_path / "scenarios.json"
    scenario_context_file = tmp_path / "scenario_context.json"
    scenario_context_file.write_text("{}", encoding="utf-8")
    scenarios_path.write_text(
        json.dumps(
            {
                "source": {"type": "generated"},
                "scenario_context_file": str(scenario_context_file),
                "scenario_context": {
                    "client_slug": "clinic_pack",
                    "branch_slug": "downtown",
                    "services": ["УЗИ брюшной полости", "ЭКГ"],
                    "capabilities": {"domain_slug": "clinic"},
                },
                "dialogs": [
                    {
                        "turns": [
                            {"text": "Здравствуйте, хочу записаться на УЗИ брюшной полости."}
                        ]
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    status = _module._llm_quality_build_scenario_context_contract_status(
        mode="block",
        scenarios_path=str(scenarios_path),
        expected_client_slug="clinic_pack",
        expected_branch_slug="downtown",
    )

    assert status["valid"] is True
    assert status["service_hits"] == ["УЗИ брюшной полости"]
    assert status["domain_slug"] == "clinic"


def test_llm_quality_build_failure_family_report_groups_same_root_cause():
    failure_families = {}
    record = {
        "type": "turn",
        "last_trace_stage": "policy_core_guard",
        "conversation_state": "bot_active",
        "message_id": "m1",
        "conversation_id": "c1",
    }
    _module._llm_quality_record_failure_family(
        failure_families, "fact_without_evidence", record
    )
    _module._llm_quality_record_failure_family(
        failure_families,
        "fact_without_evidence",
        {**record, "message_id": "m2"},
    )

    report = _module._llm_quality_build_failure_family_report(failure_families)

    assert report["family_count"] == 1
    family = report["top_families"][0]
    assert family["count"] == 2
    assert family["reason"] == "fact_without_evidence"
    assert family["trace_stage"] == "policy_core_guard"
    assert family["state"] == "bot_active"


def test_llm_quality_has_fact_without_evidence_ignores_service_clarify_collect():
    meta = {
        "action": "reply",
        "intent": "service_clarify",
        "source": "llm_policy_core",
        "expected_reply_type": "service_choice",
        "expected_reply_reason": "llm_policy_core_collect",
    }

    assert _module._llm_quality_is_fact_like_reply(meta) is False
    assert _module._llm_quality_has_fact_without_evidence(meta) is False


def test_llm_quality_accepts_master_query_missing_subject_service_clarify_fallback():
    meta = {
        "action": "reply",
        "intent": "service_clarify",
        "source": "llm_policy_core",
        "expected_reply_type": "service_choice",
        "llm_policy_core": {
            "intent": "master_query",
            "subject_kind": "specialist",
            "resolution_mode": "clarify_missing_subject",
            "next_question": "service",
            "open_questions": ["service"],
            "payload": {
                "intent": "master_query",
                "subject_kind": "specialist",
                "resolution_mode": "clarify_missing_subject",
                "next_question": "service",
                "open_questions": ["service"],
            },
        },
    }
    trace_entries = [
        {
            "stage": "llm_policy_core",
            "intent": "master_query",
            "subject_kind": "specialist",
            "resolution_mode": "clarify_missing_subject",
            "next_question": "service",
        },
        {
            "stage": "question_contract",
            "decision": "llm_policy_core_collect",
            "missing_slot": "service",
        },
    ]

    assert (
        _module._llm_quality_has_master_query_missing_subject_info_fallback(
            meta=meta,
            trace_entries=trace_entries,
            expected_reply_type=None,
            actual_expected_reply_type="service_choice",
        )
        is True
    )


def test_run_llm_quality_matrix_passes_branch_slug_and_records_context_contract(
    monkeypatch, tmp_path
):
    captured_child_argv = []

    def _fake_parse_llm_quality_args(argv):
        captured_child_argv.append(list(argv))
        parsed = {}
        idx = 0
        while idx < len(argv):
            token = argv[idx]
            if token.startswith("--"):
                parsed[token] = argv[idx + 1] if idx + 1 < len(argv) and not argv[idx + 1].startswith("--") else True
                idx += 2 if parsed[token] is not True else 1
            else:
                idx += 1
        return SimpleNamespace(
            client_slug=parsed.get("--client-slug"),
            branch_slug=parsed.get("--branch-slug"),
            output_dir=parsed.get("--output-dir"),
            mode="llm",
            scenarios_file=None,
        )

    def _fake_run_llm_quality(child_args):
        output_dir = Path(child_args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "summary.json").write_text(
            json.dumps(
                {
                    "infra_valid": True,
                    "semantic_valid": True,
                    "quality_status": {"comparison_blocked": False},
                    "metrics": {
                        "rates": {"strict_pass_rate": 1.0, "degraded_fallback_rate": 0.0},
                        "counts": {"turns_missing_response": 0},
                    },
                    "failure_families": {
                        "family_count": 1,
                        "families": [
                            {
                                "family_id": "reason:fact_without_evidence|type:turn|category:evidence|stage:policy_core_guard|state:bot_active",
                                "reason": "fact_without_evidence",
                                "category": "evidence",
                                "record_type": "turn",
                                "trace_stage": "policy_core_guard",
                                "state": "bot_active",
                                "label": "fact_without_evidence; stage=policy_core_guard; state=bot_active",
                                "count": 2 if child_args.client_slug == "demo_salon" else 1,
                                "sample_turns": [],
                            }
                        ],
                        "top_families": [],
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        scenario_context_path = output_dir / "scenario_context.json"
        scenario_context_path.write_text("{}", encoding="utf-8")
        service_name = "Маникюр" if child_args.client_slug == "demo_salon" else "УЗИ брюшной полости"
        (output_dir / "scenarios.json").write_text(
            json.dumps(
                {
                    "source": {"type": "generated"},
                    "scenario_context_file": str(scenario_context_path),
                    "scenario_context": {
                        "client_slug": child_args.client_slug,
                        "branch_slug": child_args.branch_slug,
                        "services": [service_name],
                        "capabilities": {"domain_slug": "beauty" if child_args.client_slug == "demo_salon" else "clinic"},
                    },
                    "dialogs": [
                        {
                            "turns": [
                                {"text": f"Хочу записаться на {service_name}."},
                            ]
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(_module, "_parse_llm_quality_args", _fake_parse_llm_quality_args)
    monkeypatch.setattr(_module, "_run_llm_quality", _fake_run_llm_quality)

    args = SimpleNamespace(
        client_slugs="demo_salon,clinic_pack",
        branch_slugs="almaty-main,downtown",
        run_id_prefix="matrix-test",
        output_dir=str(tmp_path / "matrix"),
        allow_output_overwrite=False,
        continue_on_error=False,
        cross_domain_contract="block",
        cross_domain_min_non_salon=1,
        cross_domain_excluded_slugs="demo_salon",
        scenario_context_contract="block",
        llm_quality_args=["--mode", "llm", "--count", "1"],
    )

    _module._run_llm_quality_matrix(args)

    assert any("--branch-slug" in argv and "almaty-main" in argv for argv in captured_child_argv)
    assert any("--branch-slug" in argv and "downtown" in argv for argv in captured_child_argv)
    summary = json.loads((tmp_path / "matrix" / "matrix_summary.json").read_text(encoding="utf-8"))
    assert summary["all_ok"] is True
    assert summary["branch_slugs"] == ["almaty-main", "downtown"]
    assert all(row["scenario_context_valid"] is True for row in summary["rows"])
    assert summary["failure_families"]["family_count"] == 1
    assert summary["failure_families"]["families"][0]["count"] == 3
