import ast
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace


def _load_jid_helpers():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in {
            "_llm_quality_pick_jid",
            "_llm_quality_resolve_jid_mode",
        }:
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {"hashlib": hashlib, "os": os}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace["_llm_quality_pick_jid"], namespace["_llm_quality_resolve_jid_mode"]


_pick_jid, _resolve_jid_mode = _load_jid_helpers()


def test_resolve_jid_mode_auto_prefers_unique_when_skip_outbox():
    args = SimpleNamespace(jid_mode="auto", skip_outbox=True)
    assert _resolve_jid_mode(args) == "unique"


def test_resolve_jid_mode_auto_prefers_round_robin_when_outbox_enabled():
    args = SimpleNamespace(jid_mode="auto", skip_outbox=False)
    assert _resolve_jid_mode(args) == "round_robin"


def test_pick_jid_unique_is_stable_per_index_and_run():
    jid_1 = _pick_jid([], 0, None, "unique", run_id="run-a")
    jid_2 = _pick_jid([], 0, None, "unique", run_id="run-a")
    jid_3 = _pick_jid([], 1, None, "unique", run_id="run-a")
    assert jid_1 == jid_2
    assert jid_1 != jid_3
    assert jid_1.endswith("@s.whatsapp.net")


def test_pick_jid_round_robin_uses_allowlist():
    class _Rng:
        @staticmethod
        def choice(values):
            return values[0]

    jids = ["77010000001@s.whatsapp.net", "77010000002@s.whatsapp.net"]
    assert _pick_jid(jids, 0, _Rng(), "round_robin") == jids[0]
    assert _pick_jid(jids, 1, _Rng(), "round_robin") == jids[1]
    assert _pick_jid(jids, 2, _Rng(), "round_robin") == jids[0]


def test_llm_quality_source_has_preflight_contamination_stop():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    assert "contaminated preflight" in source
    assert 'state_before in {"pending", "manager_active"}' in source
