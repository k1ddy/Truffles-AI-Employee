from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    return repo


def write_config(repo: Path) -> dict:
    config = {
        "proof_only_files": ["ops/diagnose.py", "scripts/booking_dialog_scenarios.py"],
        "proof_guard": {
            "forbidden_runtime_imports": ["ops.diagnose", "scripts.booking_dialog_scenarios"],
            "forbidden_test_imports": ["ops.diagnose", "scripts.booking_dialog_scenarios"],
            "forbidden_test_path_suffixes": ["diagnose.py", "booking_dialog_scenarios.py"],
            "forbidden_test_ast_exec_tokens": ["ast.parse(", "exec(compile(", "read_text("],
            "semantic_contract_tokens": ["expected_reply_type", "interaction_owner", "retag"],
        },
    }
    path = repo / "docs" / "LEGACY_SUNSET.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config


def commit_base(repo: Path) -> str:
    (repo / "ops").mkdir(parents=True, exist_ok=True)
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    (repo / "truffles-api" / "app" / "services").mkdir(parents=True, exist_ok=True)
    (repo / "truffles-api" / "tests").mkdir(parents=True, exist_ok=True)
    (repo / "ops" / "diagnose.py").write_text("def keep():\n    return None\n", encoding="utf-8")
    (repo / "scripts" / "booking_dialog_scenarios.py").write_text("def keep():\n    return None\n", encoding="utf-8")
    (repo / "truffles-api" / "app" / "services" / "runtime.py").write_text("def keep():\n    return None\n", encoding="utf-8")
    (repo / "truffles-api" / "tests" / "test_runtime.py").write_text("def test_keep():\n    assert True\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def test_proof_path_guard_blocks_test_import_from_proof_module(tmp_path: Path) -> None:
    module = load_module("proof_path_guard", SCRIPTS / "proof_path_guard.py")
    repo = init_repo(tmp_path)
    config = write_config(repo)
    base = commit_base(repo)
    test_file = repo / "truffles-api" / "tests" / "test_runtime.py"
    test_file.write_text("from ops import diagnose\n\ndef test_keep():\n    assert diagnose is not None\n", encoding="utf-8")

    violations = module.evaluate(repo, config, base, None)
    assert violations
    assert "test import from proof-only module" in violations[0]


def test_proof_path_guard_blocks_semantic_tokens_in_proof_only_file(tmp_path: Path) -> None:
    module = load_module("proof_path_guard", SCRIPTS / "proof_path_guard.py")
    repo = init_repo(tmp_path)
    config = write_config(repo)
    base = commit_base(repo)
    diagnose = repo / "ops" / "diagnose.py"
    diagnose.write_text("def keep():\n    return None\n\nexpected_reply_type = 'time'\n", encoding="utf-8")

    violations = module.evaluate(repo, config, base, None)
    assert violations
    assert "semantic-authority token" in violations[0]


def test_proof_path_guard_blocks_test_ast_exec_from_proof_only_path(tmp_path: Path) -> None:
    module = load_module("proof_path_guard", SCRIPTS / "proof_path_guard.py")
    repo = init_repo(tmp_path)
    config = write_config(repo)
    base = commit_base(repo)
    test_file = repo / "truffles-api" / "tests" / "test_runtime.py"
    test_file.write_text(
        "import ast\n"
        "from pathlib import Path\n\n"
        "def test_keep():\n"
        "    script_path = Path(__file__).resolve().parents[2] / 'ops' / 'diagnose.py'\n"
        "    source = script_path.read_text(encoding='utf-8')\n"
        "    tree = ast.parse(source, filename=str(script_path))\n"
        "    exec(compile(tree, str(script_path), 'exec'), {}, {})\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo, config, base, None)
    assert violations
    assert "AST/exec load from proof-only path" in violations[0]


def test_proof_path_guard_allows_black_box_cli_reference(tmp_path: Path) -> None:
    module = load_module("proof_path_guard", SCRIPTS / "proof_path_guard.py")
    repo = init_repo(tmp_path)
    config = write_config(repo)
    base = commit_base(repo)
    test_file = repo / "truffles-api" / "tests" / "test_runtime.py"
    test_file.write_text(
        "import subprocess\n\n"
        "def test_keep():\n"
        "    cmd = ['python3', 'ops/diagnose.py', 'llm-quality-audit', '--strict-artifacts']\n"
        "    assert cmd[1] == 'ops/diagnose.py'\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo, config, base, None)
    assert violations == []


def test_proof_path_guard_ignores_config_strings_in_test_file(tmp_path: Path) -> None:
    module = load_module("proof_path_guard", SCRIPTS / "proof_path_guard.py")
    repo = init_repo(tmp_path)
    config = write_config(repo)
    base = commit_base(repo)
    test_file = repo / "truffles-api" / "tests" / "test_runtime.py"
    test_file.write_text(
        "def test_keep():\n"
        "    cfg = {\n"
        "        'proof_only_files': ['ops/diagnose.py', 'scripts/booking_dialog_scenarios.py'],\n"
        "        'tokens': ['ast.parse(', 'exec(compile(', 'read_text('],\n"
        "    }\n"
        "    assert 'ops/diagnose.py' in cfg['proof_only_files']\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo, config, base, None)
    assert violations == []


def test_proof_path_guard_ignores_fixture_paths_plus_config_strings(tmp_path: Path) -> None:
    module = load_module("proof_path_guard", SCRIPTS / "proof_path_guard.py")
    repo = init_repo(tmp_path)
    config = write_config(repo)
    base = commit_base(repo)
    test_file = repo / "truffles-api" / "tests" / "test_runtime.py"
    test_file.write_text(
        "def test_keep(tmp_path):\n"
        "    repo = tmp_path / 'repo'\n"
        "    repo.mkdir()\n"
        "    (repo / 'ops' / 'diagnose.py').parent.mkdir(parents=True, exist_ok=True)\n"
        "    (repo / 'ops' / 'diagnose.py').write_text('def keep():\\n    return None\\n', encoding='utf-8')\n"
        "    cfg = {\n"
        "        'tokens': ['ast.parse(', 'exec(compile(', 'read_text('],\n"
        "    }\n"
        "    assert 'read_text(' in cfg['tokens']\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo, config, base, None)
    assert violations == []
