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
