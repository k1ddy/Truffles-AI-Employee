import io
import json
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
    spec = spec_from_file_location("diagnose_script_openai_preflight", script_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_module = _load_module()


def test_openai_probe_timeout_respects_requested_budget_with_bounded_cap():
    assert _module._llm_quality_openai_probe_timeout(None) == 8.0
    assert _module._llm_quality_openai_probe_timeout(1.0) == 2.0
    assert _module._llm_quality_openai_probe_timeout(25.0) == 25.0
    assert _module._llm_quality_openai_probe_timeout(90.0) == 30.0


def test_openai_preflight_attempt_timeout_escalates_only_for_llm_retry():
    assert (
        _module._llm_quality_openai_preflight_attempt_timeout(
            purpose="llm",
            timeout=30.0,
            attempt=1,
        )
        == 30.0
    )
    assert (
        _module._llm_quality_openai_preflight_attempt_timeout(
            purpose="llm",
            timeout=30.0,
            attempt=2,
        )
        == 60.0
    )
    assert (
        _module._llm_quality_openai_preflight_attempt_timeout(
            purpose="judge",
            timeout=25.0,
            attempt=2,
        )
        == 25.0
    )


def test_collect_openai_preflight_result_reuses_identical_transport(monkeypatch):
    calls: list[tuple[str, str, str, float]] = []

    def _fake_preflight(*, purpose, api_key, model, base_url, timeout):
        calls.append((purpose, model, base_url, timeout))
        return {
            "purpose": purpose,
            "valid": True,
            "reason": None,
            "status": 200,
            "elapsed_ms": 123.45,
            "endpoint": f"{base_url}/v1/chat/completions",
            "model": model,
        }

    monkeypatch.setattr(_module, "_llm_quality_openai_key_preflight", _fake_preflight)

    cache: dict[str, dict] = {}
    first, first_reused = _module._llm_quality_collect_openai_preflight_result(
        purpose="llm",
        api_key="same-key",
        model="gpt-4o-mini",
        base_url="https://api.openai.com",
        timeout=8.0,
        cache=cache,
    )
    second, second_reused = _module._llm_quality_collect_openai_preflight_result(
        purpose="judge",
        api_key="same-key",
        model="gpt-4o-mini",
        base_url="https://api.openai.com",
        timeout=25.0,
        cache=cache,
    )

    assert first_reused is False
    assert second_reused is True
    assert len(calls) == 1
    assert first["reused"] is False
    assert second["reused"] is True
    assert second["purpose"] == "judge"
    assert second["status"] == 200


def test_collect_openai_preflight_result_does_not_reuse_different_transport(monkeypatch):
    calls: list[tuple[str, str, str, float]] = []

    def _fake_preflight(*, purpose, api_key, model, base_url, timeout):
        calls.append((purpose, model, base_url, timeout))
        return {
            "purpose": purpose,
            "valid": True,
            "reason": None,
            "status": 200,
            "elapsed_ms": 123.45,
            "endpoint": f"{base_url}/v1/chat/completions",
            "model": model,
        }

    monkeypatch.setattr(_module, "_llm_quality_openai_key_preflight", _fake_preflight)

    cache: dict[str, dict] = {}
    _module._llm_quality_collect_openai_preflight_result(
        purpose="llm",
        api_key="same-key",
        model="gpt-4o-mini",
        base_url="https://api.openai.com",
        timeout=8.0,
        cache=cache,
    )
    _module._llm_quality_collect_openai_preflight_result(
        purpose="judge",
        api_key="same-key",
        model="gpt-4.1-mini",
        base_url="https://api.openai.com",
        timeout=25.0,
        cache=cache,
    )

    assert len(calls) == 2


def test_openai_key_preflight_retries_single_timeout_and_recovers(monkeypatch):
    calls = {"count": 0}
    sleeps: list[float] = []
    timeouts: list[float] = []

    class _FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "pong"}}]}).encode("utf-8")

    def _fake_urlopen(req, timeout):
        timeouts.append(timeout)
        calls["count"] += 1
        if calls["count"] == 1:
            raise TimeoutError("timed out")
        return _FakeResponse()

    monkeypatch.setattr(_module.urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setattr(_module.time, "sleep", sleeps.append)

    result = _module._llm_quality_openai_key_preflight(
        purpose="llm",
        api_key="same-key",
        model="gpt-4o-mini",
        base_url="https://api.openai.com",
        timeout=8.0,
    )

    assert calls["count"] == 2
    assert sleeps == [0.5]
    assert timeouts == [8.0, 45.0]
    assert result["valid"] is True
    assert result["reason"] is None
    assert result["status"] == 200
    assert result["attempts"] == 2
    assert result["retried"] is True
    assert result["timeout_s"] == 45.0
    assert result["retry_reasons"] == [
        {"attempt": 1, "reason": "probe_error:TimeoutError", "status": None, "timeout_s": 8.0}
    ]


def test_openai_key_preflight_retries_retryable_url_error_once(monkeypatch):
    calls = {"count": 0}
    sleeps: list[float] = []
    timeouts: list[float] = []

    class _FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "pong"}}]}).encode("utf-8")

    def _fake_urlopen(req, timeout):
        timeouts.append(timeout)
        calls["count"] += 1
        if calls["count"] == 1:
            raise _module.urllib.error.URLError("temporary failure")
        return _FakeResponse()

    monkeypatch.setattr(_module.urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setattr(_module.time, "sleep", sleeps.append)

    result = _module._llm_quality_openai_key_preflight(
        purpose="llm",
        api_key="same-key",
        model="gpt-4o-mini",
        base_url="https://api.openai.com",
        timeout=8.0,
    )

    assert calls["count"] == 2
    assert sleeps == [0.5]
    assert timeouts == [8.0, 45.0]
    assert result["valid"] is True
    assert result["attempts"] == 2
    assert result["retried"] is True
    assert result["timeout_s"] == 45.0
    assert result["retry_reasons"] == [
        {"attempt": 1, "reason": "url_error:temporary failure", "status": None, "timeout_s": 8.0}
    ]


def test_openai_key_preflight_does_not_retry_rate_limit_http_error(monkeypatch):
    calls = {"count": 0}
    sleeps: list[float] = []
    timeouts: list[float] = []
    payload = json.dumps(
        {"error": {"code": "rate_limit_exceeded", "message": "rate limit reached"}}
    ).encode("utf-8")

    def _fake_urlopen(req, timeout):
        timeouts.append(timeout)
        calls["count"] += 1
        raise _module.urllib.error.HTTPError(
            req.full_url,
            429,
            "Too Many Requests",
            hdrs=None,
            fp=io.BytesIO(payload),
        )

    monkeypatch.setattr(_module.urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setattr(_module.time, "sleep", sleeps.append)

    result = _module._llm_quality_openai_key_preflight(
        purpose="llm",
        api_key="same-key",
        model="gpt-4o-mini",
        base_url="https://api.openai.com",
        timeout=8.0,
    )

    assert calls["count"] == 1
    assert sleeps == []
    assert timeouts == [8.0]
    assert result["valid"] is False
    assert result["reason"] == "rate_limit"
    assert result["status"] == 429
    assert result["attempts"] == 1
    assert result["retried"] is False
    assert result["timeout_s"] == 8.0
    assert "retry_reasons" not in result
