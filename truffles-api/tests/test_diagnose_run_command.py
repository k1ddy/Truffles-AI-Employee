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

    dialogs, warnings, error = _module._llm_quality_generate_batch(args, count=1, seed=42)

    assert error is None
    assert len(dialogs) == 1
    assert warnings == {}
    assert captured["timeout"] == 123.0
    assert "--llm-api-key" not in captured["command"]
    assert captured["env"]["OPENAI_API_KEY"] == "test-key"


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

    dialogs, warnings, error = _module._llm_quality_generate_batch(args, count=5, seed=42)

    assert error is None
    assert len(dialogs) == 1
    assert warnings == {}
    assert captured["timeout"] == pytest.approx(205.0)
    assert "--progress-stderr" in captured["command"]


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
