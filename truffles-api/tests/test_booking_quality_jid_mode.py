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
            "_llm_quality_generate_unique_jid",
            "_llm_quality_pick_jid",
            "_llm_quality_resolve_jid_mode",
            "_llm_quality_select_fallback_jid",
        }:
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {"hashlib": hashlib, "os": os}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return (
        namespace["_llm_quality_generate_unique_jid"],
        namespace["_llm_quality_pick_jid"],
        namespace["_llm_quality_resolve_jid_mode"],
        namespace["_llm_quality_select_fallback_jid"],
    )


_generate_unique_jid, _pick_jid, _resolve_jid_mode, _select_fallback_jid = _load_jid_helpers()


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


def test_pick_jid_unique_prefers_allowlist_when_available():
    jids = ["77010000001@s.whatsapp.net", "77010000002@s.whatsapp.net"]
    jid_1 = _pick_jid(jids, 0, None, "unique", run_id="run-a")
    jid_2 = _pick_jid(jids, 1, None, "unique", run_id="run-a")
    jid_3 = _pick_jid(jids, 0, None, "unique", run_id="run-a")

    assert jid_1 in jids
    assert jid_2 in jids
    assert jid_1 != jid_2
    assert jid_1 == jid_3


def test_pick_jid_round_robin_uses_allowlist():
    class _Rng:
        @staticmethod
        def choice(values):
            return values[0]

    jids = ["77010000001@s.whatsapp.net", "77010000002@s.whatsapp.net"]
    assert _pick_jid(jids, 0, _Rng(), "round_robin") == jids[0]
    assert _pick_jid(jids, 1, _Rng(), "round_robin") == jids[1]
    assert _pick_jid(jids, 2, _Rng(), "round_robin") == jids[0]


def test_select_fallback_jid_prefers_alternate_allowlist_jid_when_outbox_enabled():
    jids = [
        "77010000001@s.whatsapp.net",
        "77010000002@s.whatsapp.net",
        "77010000003@s.whatsapp.net",
    ]
    assert (
        _select_fallback_jid(
            "77010000002@s.whatsapp.net",
            jids,
            1,
            run_id="run-a",
            skip_outbox=False,
            allow_non_allowlist=True,
        )
        == "77010000003@s.whatsapp.net"
    )


def test_select_fallback_jid_generates_unique_jid_after_allowlist_exhaustion_with_outbox_enabled():
    generated = _select_fallback_jid(
        "77010000001@s.whatsapp.net",
        ["77010000001@s.whatsapp.net"],
        0,
        run_id="run-a",
        skip_outbox=False,
        allow_non_allowlist=True,
    )
    assert generated == _generate_unique_jid(0, run_id="run-a", salt="fresh-dialog")
    assert generated != "77010000001@s.whatsapp.net"
    assert generated.endswith("@s.whatsapp.net")


def test_select_fallback_jid_generates_unique_jid_when_outbox_skipped():
    generated = _select_fallback_jid(
        "77010000001@s.whatsapp.net",
        ["77010000001@s.whatsapp.net"],
        0,
        run_id="run-a",
        skip_outbox=True,
        allow_non_allowlist=True,
    )
    assert generated == _generate_unique_jid(0, run_id="run-a", salt="fresh-dialog")
    assert generated != "77010000001@s.whatsapp.net"
    assert generated.endswith("@s.whatsapp.net")


def test_select_fallback_jid_skips_tried_allowlist_candidates():
    jids = [
        "77010000001@s.whatsapp.net",
        "77010000002@s.whatsapp.net",
        "77010000003@s.whatsapp.net",
    ]
    assert (
        _select_fallback_jid(
            "77010000001@s.whatsapp.net",
            jids,
            0,
            run_id="run-a",
            tried_jids={"77010000002@s.whatsapp.net"},
            skip_outbox=False,
            allow_non_allowlist=True,
        )
        == "77010000003@s.whatsapp.net"
    )


def test_select_fallback_jid_skips_tried_generated_candidate_after_allowlist_exhaustion():
    first_generated = _generate_unique_jid(0, run_id="run-a", salt="fresh-dialog")
    second_generated = _generate_unique_jid(0, run_id="run-a", salt="fresh-dialog-1")

    assert (
        _select_fallback_jid(
            "77010000001@s.whatsapp.net",
            ["77010000001@s.whatsapp.net"],
            0,
            run_id="run-a",
            tried_jids={first_generated},
            skip_outbox=False,
            allow_non_allowlist=True,
        )
        == second_generated
    )


def test_select_fallback_jid_exhausts_allowlist_before_generating_fresh_dialog_jid():
    tried = set()
    jids = [
        "77010000001@s.whatsapp.net",
        "77010000002@s.whatsapp.net",
        "77010000003@s.whatsapp.net",
    ]

    first = _select_fallback_jid(
        "77010000001@s.whatsapp.net",
        jids,
        0,
        run_id="run-a",
        tried_jids=tried,
        skip_outbox=False,
        allow_non_allowlist=True,
    )
    tried.add(first)
    second = _select_fallback_jid(
        first,
        jids,
        0,
        run_id="run-a",
        tried_jids=tried,
        skip_outbox=False,
        allow_non_allowlist=True,
    )
    tried.add(second)
    third = _select_fallback_jid(
        second,
        jids,
        0,
        run_id="run-a",
        tried_jids=tried,
        skip_outbox=False,
        allow_non_allowlist=True,
    )

    assert first == "77010000002@s.whatsapp.net"
    assert second == "77010000003@s.whatsapp.net"
    assert third == _generate_unique_jid(0, run_id="run-a", salt="fresh-dialog")


def test_select_fallback_jid_refuses_non_allowlist_when_flag_disabled():
    assert (
        _select_fallback_jid(
            "77010000001@s.whatsapp.net",
            ["77010000001@s.whatsapp.net"],
            0,
            run_id="run-a",
            skip_outbox=False,
            allow_non_allowlist=False,
        )
        is None
    )


def test_llm_quality_source_has_preflight_contamination_stop():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    assert "contaminated preflight" in source
    assert 'state_before in {"pending", "manager_active"}' in source
    assert "fallback_jid = _llm_quality_select_fallback_jid(" in source
    assert "while contaminated:" in source
