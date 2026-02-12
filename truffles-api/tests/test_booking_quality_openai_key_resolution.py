import ast
import os
from pathlib import Path


def _load_openai_key_resolver():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    selected_nodes = []
    wanted_functions = {
        "_load_env_file",
        "_clean_api_key",
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
    return namespace["_resolve_openai_api_key"]


def test_openai_key_resolver_reads_local_truffles_api_env(monkeypatch, tmp_path):
    resolver = _load_openai_key_resolver()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    env_dir = tmp_path / "truffles-api"
    env_dir.mkdir(parents=True, exist_ok=True)
    (env_dir / ".env").write_text("OPENAI_API_KEY=test-from-diagnose-env\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    key, source = resolver(None, container_name=None)

    assert key == "test-from-diagnose-env"
    assert source is not None and source.startswith("env_file:")


def test_openai_key_resolver_uses_container_fallback(monkeypatch, tmp_path):
    resolver = _load_openai_key_resolver()
    resolver.__globals__["_openai_key_candidate_env_files"] = lambda: []
    resolver.__globals__["_resolve_env_from_container"] = (
        lambda _container, var: "container-key" if var == "OPENAI_API_KEY" else ""
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    key, source = resolver(None, container_name="truffles-api")

    assert key == "container-key"
    assert source == "container:truffles-api"
