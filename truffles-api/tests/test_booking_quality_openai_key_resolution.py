import ast
import os
from pathlib import Path


def _load_openai_key_helpers():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    selected_nodes = []
    wanted_functions = {
        "_load_env_file",
        "_clean_api_key",
        "_export_openai_api_key",
        "_openai_key_candidate_env_files",
        "_resolve_openai_api_key",
    }
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {"os": os}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    namespace["_resolve_env_from_container"] = lambda _container, _var: ""
    return namespace["_resolve_openai_api_key"], namespace["_export_openai_api_key"]


def _load_scenario_error_normalizer():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_normalize_scenario_generation_error":
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace: dict[str, object] = {}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace["_normalize_scenario_generation_error"]


def test_llm_quality_source_requires_openai_key_for_all_llm_mode_runs():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")

    assert 'elif args.mode == "llm":' in source
    assert "llm-quality: missing OPENAI_API_KEY for llm-mode run" in source


def test_openai_key_resolver_reads_local_truffles_api_env(monkeypatch, tmp_path):
    resolver, _ = _load_openai_key_helpers()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    env_dir = tmp_path / "truffles-api"
    env_dir.mkdir(parents=True, exist_ok=True)
    (env_dir / ".env").write_text("OPENAI_API_KEY=test-from-diagnose-env\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    key, source = resolver(None, container_name=None)

    assert key == "test-from-diagnose-env"
    assert source is not None and source.startswith("env_file:")


def test_openai_key_resolver_uses_container_fallback(monkeypatch, tmp_path):
    resolver, _ = _load_openai_key_helpers()
    resolver.__globals__["_openai_key_candidate_env_files"] = lambda: []
    resolver.__globals__["_resolve_env_from_container"] = (
        lambda _container, var: "container-key" if var == "OPENAI_API_KEY" else ""
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    key, source = resolver(None, container_name="truffles-api")

    assert key == "container-key"
    assert source == "container:truffles-api"


def test_openai_key_resolver_accepts_env_alias(monkeypatch, tmp_path):
    resolver, _ = _load_openai_key_helpers()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_KEY", "alias-env-key")
    monkeypatch.chdir(tmp_path)

    key, source = resolver(None, container_name=None)

    assert key == "alias-env-key"
    assert source == "env:OPENAI_API_KEY:OPENAI_KEY"


def test_openai_key_resolver_expands_env_reference_in_env_file(monkeypatch, tmp_path):
    resolver, _ = _load_openai_key_helpers()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_KEY", raising=False)
    env_dir = tmp_path / "truffles-api"
    env_dir.mkdir(parents=True, exist_ok=True)
    (env_dir / ".env").write_text(
        "OPENAI_API_KEY_FALLBACK=expanded-key\nOPENAI_API_KEY=${OPENAI_API_KEY_FALLBACK}\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    key, source = resolver(None, container_name=None)

    assert key == "expanded-key"
    assert source is not None and source.startswith("env_file:")


def test_openai_key_export_sets_env(monkeypatch):
    _, exporter = _load_openai_key_helpers()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exported = exporter("  'test-exported-key'  ")

    assert exported is True
    assert os.environ.get("OPENAI_API_KEY") == "test-exported-key"


def test_openai_key_export_rejects_empty(monkeypatch):
    _, exporter = _load_openai_key_helpers()
    monkeypatch.setenv("OPENAI_API_KEY", "existing-key")

    exported = exporter("   ")

    assert exported is False
    assert os.environ.get("OPENAI_API_KEY") == "existing-key"


def test_normalize_scenario_generation_error_prefers_runtime_error_line():
    normalizer = _load_scenario_error_normalizer()
    stderr = (
        "Traceback (most recent call last):\n"
        "  ...\n"
        "RuntimeError: openai_rate_or_quota_limited (insufficient_quota): limit reached\n"
    )

    normalized = normalizer(stderr)

    assert normalized == "openai_rate_or_quota_limited (insufficient_quota): limit reached"


def test_normalize_scenario_generation_error_detects_http_429_without_runtime_line():
    normalizer = _load_scenario_error_normalizer()
    stderr = "urllib.error.HTTPError: HTTP Error 429: Too Many Requests"

    normalized = normalizer(stderr)

    assert normalized == "openai_rate_or_quota_limited: provider returned HTTP 429"
