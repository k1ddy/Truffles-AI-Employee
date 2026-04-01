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
    spec = spec_from_file_location("diagnose_script", script_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_module = _load_module()


def test_default_judge_cache_file_includes_worktree_namespace():
    path = _module._llm_quality_default_judge_cache_file(
        "gpt-5.4-nano-2026-03-17", "https://api.openai.com/v1"
    )
    namespace = _module._llm_quality_worktree_namespace()
    assert "/tmp/booking_quality/_judge_cache/" in path
    assert namespace in path
    assert "api.openai.com" in path
    assert "gpt-5.4-nano-2026-03-17" in path


def test_save_and_load_judge_cache_trimmed(tmp_path):
    cache_path = tmp_path / "judge_cache.json"
    payload = {f"k{i}": {"verdict": "pass", "score": 1.0} for i in range(6)}

    _module._llm_quality_save_judge_cache(str(cache_path), payload, max_entries=4)
    loaded = _module._llm_quality_load_judge_cache(str(cache_path))

    assert isinstance(loaded, dict)
    assert len(loaded) == 4
    assert "k0" not in loaded
    assert "k1" not in loaded
    assert "k5" in loaded


def test_judge_cache_key_changes_with_prompt():
    k1 = _module._llm_quality_judge_cache_key(
        "gpt-5.4-nano-2026-03-17",
        "https://api.openai.com",
        "prompt-1",
    )
    k2 = _module._llm_quality_judge_cache_key(
        "gpt-5.4-nano-2026-03-17",
        "https://api.openai.com",
        "prompt-2",
    )
    assert isinstance(k1, str) and isinstance(k2, str)
    assert len(k1) == 64
    assert k1 != k2
