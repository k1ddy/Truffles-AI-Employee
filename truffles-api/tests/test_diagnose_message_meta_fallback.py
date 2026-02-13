import subprocess
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

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
    spec = spec_from_file_location("diagnose_script_meta_fallback", script_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_module = _load_module()


def test_fetch_message_meta_uses_conversation_hint_on_timeout(monkeypatch):
    calls = []

    def _fake_run_command(command, *, timeout=None):
        query = command[-1]
        calls.append(query)
        if "metadata->>'messageId'" in query:
            return subprocess.CompletedProcess(
                command,
                124,
                stdout="",
                stderr="[timeout] command exceeded 25.0s: psql",
            )
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='conv-1\t{"action":"reply","intent":"catalog.location"}\n',
            stderr="",
        )

    monkeypatch.setattr(_module, "run_command", _fake_run_command)

    conversation_id, meta, error = _module._fetch_message_meta(
        "n8n",
        "mid-1",
        timeout=8.0,
        conversation_id_hint="conv-1",
    )

    assert conversation_id == "conv-1"
    assert isinstance(meta, dict)
    assert meta.get("action") == "reply"
    assert error is None
    assert len(calls) == 2
    assert "conversation_id = 'conv-1'" in calls[1]


def test_fetch_message_meta_keeps_primary_error_when_not_timeout(monkeypatch):
    calls = []

    def _fake_run_command(command, *, timeout=None):
        calls.append(command[-1])
        return subprocess.CompletedProcess(
            command,
            1,
            stdout="",
            stderr="psql: connection refused",
        )

    monkeypatch.setattr(_module, "run_command", _fake_run_command)

    conversation_id, meta, error = _module._fetch_message_meta(
        "n8n",
        "mid-1",
        timeout=8.0,
        conversation_id_hint="conv-1",
    )

    assert conversation_id is None
    assert meta is None
    assert error == "psql: connection refused"
    assert len(calls) == 1
