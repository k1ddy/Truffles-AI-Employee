import ast
from pathlib import Path

import pytest


def _load_livecheck_secret_helpers():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    wanted_functions = {
        "_clean_webhook_secret",
        "_llm_quality_resolve_expected_webhook_secret",
        "_livecheck_select_webhook_secret",
    }
    selected_nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted_functions
    ]
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace


def test_livecheck_prefers_runtime_expected_secret_when_available():
    ns = _load_livecheck_secret_helpers()
    ns["_resolve_webhook_secret_with_source"] = lambda *_args, **_kwargs: ("env-secret", "env:WEBHOOK_SECRET")

    secret, source = ns["_livecheck_select_webhook_secret"](
        client_slug="demo_salon",
        explicit_secret=None,
        client_meta={"branch_webhook_secret": "branch-secret", "client_webhook_secret": "client-secret"},
    )

    assert secret == "branch-secret"
    assert source == "runtime_expected:branch"


def test_livecheck_rejects_mismatched_explicit_secret():
    ns = _load_livecheck_secret_helpers()
    ns["_resolve_webhook_secret_with_source"] = lambda *_args, **_kwargs: ("fallback-secret", "client_settings")

    with pytest.raises(SystemExit, match="explicit webhook secret mismatch"):
        ns["_livecheck_select_webhook_secret"](
            client_slug="demo_salon",
            explicit_secret="wrong-secret",
            client_meta={"branch_webhook_secret": "branch-secret"},
        )


def test_livecheck_uses_fallback_when_expected_secret_missing():
    ns = _load_livecheck_secret_helpers()
    ns["_resolve_webhook_secret_with_source"] = lambda *_args, **_kwargs: ("fallback-secret", "client_settings")

    secret, source = ns["_livecheck_select_webhook_secret"](
        client_slug="demo_salon",
        explicit_secret=None,
        client_meta={},
    )

    assert secret == "fallback-secret"
    assert source == "client_settings"
