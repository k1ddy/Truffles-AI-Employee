from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
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
            "semantic_contract_tokens": ["expected_reply_type", "interaction_owner", "retag"],
            "forbidden_test_path_suffixes": ["diagnose.py", "booking_dialog_scenarios.py"],
            "forbidden_test_ast_exec_tokens": ["ast.parse(", "exec(compile(", "read_text("],
        },
    }
    path = repo / "docs" / "LEGACY_SUNSET.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config


def commit_base(repo: Path) -> str:
    (repo / "ops").mkdir(parents=True, exist_ok=True)
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    (repo / "truffles-api" / "tests").mkdir(parents=True, exist_ok=True)
    (repo / "ops" / "diagnose.py").write_text("def keep():\n    return None\n", encoding="utf-8")
    (repo / "scripts" / "booking_dialog_scenarios.py").write_text(
        "def keep():\n    return None\n",
        encoding="utf-8",
    )
    (repo / "truffles-api" / "tests" / "test_runtime.py").write_text(
        "def test_keep():\n    assert True\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def test_response_guard_blocks_ast_exec_loading_of_ops_diagnose(tmp_path: Path) -> None:
    module = load_module("proof_path_guard", SCRIPTS / "proof_path_guard.py")
    repo = init_repo(tmp_path)
    config = write_config(repo)
    base = commit_base(repo)
    test_file = repo / "truffles-api" / "tests" / "test_runtime.py"
    test_file.write_text(
        "import ast\n"
        "from pathlib import Path\n\n"
        "def test_guard():\n"
        "    script_path = Path(__file__).resolve().parents[2] / 'ops' / 'diagnose.py'\n"
        "    source = script_path.read_text(encoding='utf-8')\n"
        "    tree = ast.parse(source, filename=str(script_path))\n"
        "    exec(compile(tree, str(script_path), 'exec'), {}, {})\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo, config, base, None)
    assert violations
    assert "AST/exec load from proof-only path" in violations[0]


def test_response_guard_blocks_ast_exec_loading_of_booking_scenarios(tmp_path: Path) -> None:
    module = load_module("proof_path_guard", SCRIPTS / "proof_path_guard.py")
    repo = init_repo(tmp_path)
    config = write_config(repo)
    base = commit_base(repo)
    test_file = repo / "truffles-api" / "tests" / "test_runtime.py"
    test_file.write_text(
        "import ast\n"
        "from pathlib import Path\n\n"
        "def test_guard():\n"
        "    script_path = Path(__file__).resolve().parents[2] / 'scripts' / 'booking_dialog_scenarios.py'\n"
        "    source = script_path.read_text(encoding='utf-8')\n"
        "    tree = ast.parse(source, filename=str(script_path))\n"
        "    exec(compile(tree, str(script_path), 'exec'), {}, {})\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo, config, base, None)
    assert violations
    assert "AST/exec load from proof-only path" in violations[0]


def test_response_guard_allows_black_box_cli_reference_without_ast_exec(tmp_path: Path) -> None:
    module = load_module("proof_path_guard", SCRIPTS / "proof_path_guard.py")
    repo = init_repo(tmp_path)
    config = write_config(repo)
    base = commit_base(repo)
    test_file = repo / "truffles-api" / "tests" / "test_runtime.py"
    test_file.write_text(
        "import subprocess\n\n"
        "def test_guard():\n"
        "    cmd = ['python3', 'ops/diagnose.py', 'llm-quality-audit', '--strict-artifacts']\n"
        "    assert cmd[1] == 'ops/diagnose.py'\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo, config, base, None)
    assert violations == []


def test_targeted_proof_tests_no_longer_load_ops_diagnose_source() -> None:
    for rel_path in (
        "truffles-api/tests/test_booking_quality_expectation_sanitizer.py",
        "truffles-api/tests/test_booking_quality_scenario_contract_gate.py",
    ):
        source = (ROOT / rel_path).read_text(encoding="utf-8")
        assert "ops/diagnose.py" not in source
        assert "ast.parse(" not in source
        assert "spec_from_file_location(" not in source
        assert "exec(compile(" not in source


def test_booking_scenario_merge_tests_now_bind_shared_helper() -> None:
    source = (ROOT / "truffles-api/tests/test_booking_dialog_scenarios_script.py").read_text(
        encoding="utf-8"
    )
    assert "from app.services.llm_quality_contracts import (" in source
    assert "merge_booking_scenario_expectations" in source
    assert "_merge_expectations = _module._merge_expectations" not in source


def test_booking_scenario_script_sanitize_owner_delegates_to_shared_module() -> None:
    source = (ROOT / "scripts/booking_dialog_scenarios.py").read_text(encoding="utf-8")
    assert "from app.services.llm_quality_contracts import (" in source
    assert "sanitize_booking_scenario_llm_turns as _sanitize_llm_turns" in source
    assert "def _sanitize_llm_turns(" not in source
    assert "def _looks_like_assistant_turn(" not in source
    assert "def _fallback_text_for_tags(" not in source
    assert "def _text_matches_tag_contract(" not in source
