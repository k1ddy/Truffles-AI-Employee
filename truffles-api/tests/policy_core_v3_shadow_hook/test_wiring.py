"""Wiring singleton tests for policy_core_v3_shadow_hook."""
from __future__ import annotations

import pathlib

import pytest

from app.policy_core_v3 import PolicyCoreV3Invoker
from app.policy_core_v3_shadow import JsonlArtifactSink
from app.policy_core_v3_shadow_hook import wiring


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
EXAMPLE_PACK = REPO_ROOT / "packs" / "beauty_salon_v1"


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """Each test starts with cleared singletons and no env vars set."""
    monkeypatch.delenv("POLICY_CORE_V3_SHADOW_PACK_PATH", raising=False)
    monkeypatch.delenv("POLICY_CORE_V3_SHADOW_JSONL_PATH", raising=False)
    monkeypatch.delenv("POLICY_CORE_V3_SHADOW_USE_LLM", raising=False)
    wiring.reset_singletons()
    yield
    wiring.reset_singletons()


def test_pack_returns_none_when_unset() -> None:
    assert wiring.get_shadow_pack() is None


def test_pack_loads_when_set(monkeypatch) -> None:
    monkeypatch.setenv("POLICY_CORE_V3_SHADOW_PACK_PATH", str(EXAMPLE_PACK))
    pack = wiring.get_shadow_pack()
    assert pack is not None
    assert pack.pack_id == "beauty_salon_v1"


def test_pack_returns_none_on_invalid_path(monkeypatch) -> None:
    monkeypatch.setenv("POLICY_CORE_V3_SHADOW_PACK_PATH", "/nonexistent/x")
    assert wiring.get_shadow_pack() is None


def test_pack_is_cached(monkeypatch) -> None:
    monkeypatch.setenv("POLICY_CORE_V3_SHADOW_PACK_PATH", str(EXAMPLE_PACK))
    a = wiring.get_shadow_pack()
    b = wiring.get_shadow_pack()
    assert a is b


def test_sink_returns_none_when_unset() -> None:
    assert wiring.get_shadow_sink() is None


def test_sink_returns_jsonl_sink_when_set(monkeypatch, tmp_path) -> None:
    target = tmp_path / "shadow.jsonl"
    monkeypatch.setenv("POLICY_CORE_V3_SHADOW_JSONL_PATH", str(target))
    sink = wiring.get_shadow_sink()
    assert isinstance(sink, JsonlArtifactSink)
    assert sink.path == target


def test_invoker_default_uses_mock(monkeypatch) -> None:
    inv = wiring.get_shadow_invoker()
    assert isinstance(inv, PolicyCoreV3Invoker)


def test_invoker_use_llm_false_uses_mock(monkeypatch) -> None:
    monkeypatch.setenv("POLICY_CORE_V3_SHADOW_USE_LLM", "false")
    inv = wiring.get_shadow_invoker()
    assert isinstance(inv, PolicyCoreV3Invoker)


def test_reset_singletons_clears_cache(monkeypatch) -> None:
    monkeypatch.setenv("POLICY_CORE_V3_SHADOW_PACK_PATH", str(EXAMPLE_PACK))
    a = wiring.get_shadow_pack()
    monkeypatch.delenv("POLICY_CORE_V3_SHADOW_PACK_PATH", raising=False)
    assert wiring.get_shadow_pack() is a  # still cached
    wiring.reset_singletons()
    assert wiring.get_shadow_pack() is None
