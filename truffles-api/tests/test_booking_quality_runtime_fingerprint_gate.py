import ast
import subprocess
from pathlib import Path


def _diagnose_source_and_tree():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    return script_path, source, tree


def _load_runtime_gate_helpers():
    script_path, _source, tree = _diagnose_source_and_tree()
    wanted_functions = {
        "_llm_quality_clean_git_commit",
        "_llm_quality_resolve_expected_runtime_commit",
        "_llm_quality_runtime_fingerprint_preflight",
    }
    selected_nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted_functions
    ]
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {"subprocess": subprocess}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace


def _llm_quality_base_url_default_expr(tree):
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name != "_parse_llm_quality_args":
            continue
        for call in ast.walk(node):
            if not isinstance(call, ast.Call):
                continue
            if not isinstance(call.func, ast.Attribute):
                continue
            if call.func.attr != "add_argument":
                continue
            if not call.args:
                continue
            if not isinstance(call.args[0], ast.Constant):
                continue
            if call.args[0].value != "--base-url":
                continue
            for keyword in call.keywords:
                if keyword.arg == "default":
                    return keyword.value
    raise AssertionError("base-url parser arg not found")


def test_llm_quality_parser_requires_explicit_base_url_or_env():
    _script_path, source, tree = _diagnose_source_and_tree()
    default_expr = _llm_quality_base_url_default_expr(tree)

    assert isinstance(default_expr, ast.Call)
    assert isinstance(default_expr.func, ast.Attribute)
    assert isinstance(default_expr.func.value, ast.Attribute)
    assert isinstance(default_expr.func.value.value, ast.Name)
    assert default_expr.func.value.value.id == "os"
    assert default_expr.func.value.attr == "environ"
    assert default_expr.func.attr == "get"
    assert len(default_expr.args) == 1
    assert isinstance(default_expr.args[0], ast.Constant)
    assert default_expr.args[0].value == "TRUFFLES_API_BASE_URL"
    assert "llm-quality: --base-url is required" in source


def test_runtime_fingerprint_preflight_passes_when_commit_matches(monkeypatch):
    ns = _load_runtime_gate_helpers()
    monkeypatch.setitem(
        ns,
        "_llm_quality_resolve_expected_runtime_commit",
        lambda _explicit: ("abc123", "arg", None),
    )
    monkeypatch.setitem(
        ns,
        "_fetch_json",
        lambda _url, _timeout: {"version": "main", "git_commit": "abc123"},
    )

    result = ns["_llm_quality_runtime_fingerprint_preflight"](
        base_url="http://127.0.0.1:8000",
        expected_commit="abc123",
        timeout=10.0,
    )

    assert result["valid"] is True
    assert result["reasons"] == []
    assert result["runtime_commit"] == "abc123"
    assert result["expected_commit"] == "abc123"
    assert result["endpoint"].endswith("/admin/version")


def test_runtime_fingerprint_preflight_fails_on_commit_mismatch(monkeypatch):
    ns = _load_runtime_gate_helpers()
    monkeypatch.setitem(
        ns,
        "_llm_quality_resolve_expected_runtime_commit",
        lambda _explicit: ("abc123", "arg", None),
    )
    monkeypatch.setitem(
        ns,
        "_fetch_json",
        lambda _url, _timeout: {"version": "main", "git_commit": "def456"},
    )

    result = ns["_llm_quality_runtime_fingerprint_preflight"](
        base_url="http://localhost:60033",
        expected_commit="abc123",
        timeout=7.0,
    )

    assert result["valid"] is False
    assert "git_commit_mismatch" in result["reasons"]
    assert result["runtime_commit"] == "def456"


def test_runtime_fingerprint_preflight_fails_when_runtime_commit_missing(monkeypatch):
    ns = _load_runtime_gate_helpers()
    monkeypatch.setitem(
        ns,
        "_llm_quality_resolve_expected_runtime_commit",
        lambda _explicit: ("abc123", "arg", None),
    )
    monkeypatch.setitem(
        ns,
        "_fetch_json",
        lambda _url, _timeout: {"version": "main", "git_commit": "unknown"},
    )

    result = ns["_llm_quality_runtime_fingerprint_preflight"](
        base_url="http://localhost:60033",
        expected_commit="abc123",
        timeout=7.0,
    )

    assert result["valid"] is False
    assert "runtime_commit_missing" in result["reasons"]


def test_runtime_fingerprint_preflight_fails_when_expected_commit_unresolved(monkeypatch):
    ns = _load_runtime_gate_helpers()
    monkeypatch.setitem(
        ns,
        "_llm_quality_resolve_expected_runtime_commit",
        lambda _explicit: (
            None,
            "git_head",
            "expected_commit_resolve_error:git_rev_parse_failed",
        ),
    )
    monkeypatch.setitem(
        ns,
        "_fetch_json",
        lambda _url, _timeout: {"version": "main", "git_commit": "abc123"},
    )

    result = ns["_llm_quality_runtime_fingerprint_preflight"](
        base_url="http://localhost:60033",
        expected_commit=None,
        timeout=7.0,
    )

    assert result["valid"] is False
    assert "expected_commit_resolve_error:git_rev_parse_failed" in result["reasons"]
    assert "expected_commit_missing" in result["reasons"]


def test_resolve_expected_runtime_commit_prefers_explicit_value(monkeypatch):
    ns = _load_runtime_gate_helpers()
    observed = {}

    def _fake_run(*_args, **_kwargs):
        observed["called"] = True
        return subprocess.CompletedProcess([], 0, stdout="deadbeef\n", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    monkeypatch.setitem(ns, "_llm_quality_repo_root", lambda: "/tmp/repo")

    commit, source, reason = ns["_llm_quality_resolve_expected_runtime_commit"]("ABC123")

    assert commit == "abc123"
    assert source == "arg"
    assert reason is None
    assert observed == {}
