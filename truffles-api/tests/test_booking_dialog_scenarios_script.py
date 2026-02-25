import io
import json
import random
import urllib.error
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


def _load_module():
    base = Path(__file__).resolve()
    candidates = [
        base.parents[1] / "scripts" / "booking_dialog_scenarios.py",
        base.parents[2] / "scripts" / "booking_dialog_scenarios.py",
    ]
    script_path = next((path for path in candidates if path.exists()), candidates[0])
    if not script_path.exists():
        pytest.skip(
            "booking_dialog_scenarios.py not present in test runtime image",
            allow_module_level=True,
        )
    spec = spec_from_file_location("booking_dialog_scenarios", script_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_module = _load_module()
_merge_expectations = _module._merge_expectations


def test_resolve_openai_api_key_reads_local_truffles_api_env(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    env_dir = tmp_path / "truffles-api"
    env_dir.mkdir(parents=True, exist_ok=True)
    (env_dir / ".env").write_text("OPENAI_API_KEY=test-from-env-file\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    key, source = _module._resolve_openai_api_key(None)

    assert key == "test-from-env-file"
    assert source is not None and "truffles-api/.env" in source


def test_resolve_openai_api_key_accepts_env_alias(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_KEY", "alias-from-env")
    monkeypatch.chdir(tmp_path)

    key, source = _module._resolve_openai_api_key(None)

    assert key == "alias-from-env"
    assert source == "env:OPENAI_API_KEY:OPENAI_KEY"


def test_resolve_openai_api_key_expands_env_reference(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_KEY", raising=False)
    env_dir = tmp_path / "truffles-api"
    env_dir.mkdir(parents=True, exist_ok=True)
    (env_dir / ".env").write_text(
        "OPENAI_API_KEY_FALLBACK=expanded-script-key\nOPENAI_API_KEY=${OPENAI_API_KEY_FALLBACK}\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    key, source = _module._resolve_openai_api_key(None)

    assert key == "expanded-script-key"
    assert source is not None and "truffles-api/.env" in source


def test_merge_expectations_applies_override_fields():
    expect = _merge_expectations(
        ["booking", "handoff", "master"],
        {
            "action": "handoff",
            "reply_type": "name",
            "state": "pending",
            "expected_reply": "false",
            "info_sections": ["master"],
        },
    )

    assert expect["action"] == "handoff"
    assert expect["reply_type"] == "name"
    assert expect["state"] == "pending"
    assert expect["expected_reply"] is False
    assert "master" in (expect.get("info_sections") or [])


def test_merge_expectations_sanitizes_handoff_override_without_handoff_tags():
    expect = _merge_expectations(
        ["confirm"],
        {
            "action": "booking_escalated",
            "state": "manager_active",
            "expected_reply": "true",
        },
    )

    assert expect["action"] is None
    assert expect["state"] == "bot_active"
    assert expect["expected_reply"] is True


def test_merge_expectations_drops_info_override_without_info_tags():
    expect = _merge_expectations(
        ["booking"],
        {
            "info_sections": ["service_duration"],
            "expected_reply": "true",
        },
    )

    assert expect["info_sections"] == []
    assert expect["expected_reply"] is True


def test_merge_expectations_assigns_default_state_for_weak_tags():
    expect = _merge_expectations(["noise"], None)

    assert expect["state"] == "bot_active"


def test_generate_llm_dialogs_retries_after_json_error(monkeypatch):
    calls = {"parse": 0, "openai": 0}

    def _fake_openai(
        prompt, *, api_key, model, base_url, request_timeout=40.0, max_tokens=1800
    ):
        calls["openai"] += 1
        return "{}"

    def _fake_parse(_content, *, repair_fn=None):
        calls["parse"] += 1
        if calls["parse"] == 1:
            raise json.JSONDecodeError("bad", "{", 0)
        return {
            "dialogs": [
                {
                    "goal": "booking",
                    "turns": [
                        {
                            "kind": "text",
                            "text": "Хочу записаться",
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
                    ],
                }
            ]
        }

    monkeypatch.setattr(_module, "_call_openai", _fake_openai)
    monkeypatch.setattr(_module, "_parse_llm_json", _fake_parse)
    monkeypatch.setattr(_module, "_infer_context_from_dialog", lambda _dialog, _rng: {"service": "Стрижка"})
    monkeypatch.setattr(
        _module,
        "_ensure_required_tags",
        lambda turns, _ctx, *, max_turns, coverage=None: turns,
    )
    monkeypatch.setattr(_module, "_sanitize_llm_turns", lambda turns, _ctx, _rng: turns)
    monkeypatch.setattr(_module, "_prune_turns", lambda turns, _max_turns, _required: turns)
    monkeypatch.setattr(
        _module,
        "_media_turn",
        lambda _ctx, *, mode, kind: {"kind": mode, "text": kind, "tags": ["media"], "expect": {}},
    )

    dialogs = _module._generate_llm_dialogs(
        random.Random(7),
        count=1,
        min_turns=10,
        max_turns=15,
        include_media=False,
        media_mode="text",
        media_kind="photo",
        model="gpt-4o-mini",
        base_url="https://api.openai.com",
        api_key="test-key",
        coverage=["booking", "info", "interrupt", "handoff"],
        seed=7,
        llm_batch_size=1,
        llm_max_attempts=2,
        llm_request_timeout=15.0,
        llm_attempt_backoff=0.0,
        progress_stderr=False,
    )

    assert len(dialogs) == 1
    assert calls["openai"] == 2
    assert calls["parse"] == 2


def test_ensure_required_tags_adds_check_booking_and_confirm_for_booking_coverage():
    ctx = _module._build_context(random.Random(3))
    turns = [
        {"kind": "text", "text": "Хочу записаться", "tags": ["booking"], "expect": {}},
        {"kind": "text", "text": "Можно на 19:00?", "tags": ["time"], "expect": {}},
        {"kind": "text", "text": "Меня зовут Лена", "tags": ["name"], "expect": {}},
    ]

    enriched = _module._ensure_required_tags(
        turns,
        ctx,
        max_turns=12,
        coverage=["booking", "info", "interrupt"],
    )
    tags = {tag for turn in enriched for tag in (turn.get("tags") or [])}

    assert "check_booking" in tags
    assert "confirm" in tags


def test_ensure_required_tags_reorders_check_before_confirm():
    ctx = _module._build_context(random.Random(11))
    turns = [
        {"kind": "text", "text": "Да, подтверждаю.", "tags": ["confirm"], "expect": {}},
        {"kind": "text", "text": "Проверьте мою запись.", "tags": ["check_booking"], "expect": {}},
    ]

    enriched = _module._ensure_required_tags(
        turns,
        ctx,
        max_turns=12,
        coverage=["booking", "interrupt"],
    )
    check_idx = next(
        idx for idx, turn in enumerate(enriched) if "check_booking" in (turn.get("tags") or [])
    )
    confirm_idx = next(
        idx for idx, turn in enumerate(enriched) if "confirm" in (turn.get("tags") or [])
    )

    assert check_idx < confirm_idx


def test_call_openai_classifies_quota_error(monkeypatch):
    error_payload = json.dumps(
        {
            "error": {
                "code": "insufficient_quota",
                "message": "quota exceeded for this project",
            }
        }
    ).encode("utf-8")
    http_error = urllib.error.HTTPError(
        url="https://api.openai.com/v1/chat/completions",
        code=429,
        msg="Too Many Requests",
        hdrs=None,
        fp=io.BytesIO(error_payload),
    )

    def _raise_http_error(*_args, **_kwargs):
        raise http_error

    monkeypatch.setattr(_module.urllib.request, "urlopen", _raise_http_error)

    with pytest.raises(RuntimeError) as exc_info:
        _module._call_openai(
            "test prompt",
            api_key="test-key",
            model="gpt-5-mini",
            base_url="https://api.openai.com",
            max_tokens=256,
        )

    message = str(exc_info.value)
    assert "openai_rate_or_quota_limited" in message
    assert "insufficient_quota" in message
