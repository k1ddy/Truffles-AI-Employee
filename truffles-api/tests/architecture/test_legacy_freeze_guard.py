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


def init_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    return repo, "HEAD"


def write_config(repo: Path) -> dict:
    config = {
        "sunset_files": [
            {
                "path": "truffles-api/app/routers/webhook/decision.py",
                "active_waiver": None,
            }
        ]
    }
    path = repo / "docs" / "LEGACY_SUNSET.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config


def commit_base(repo: Path, decision_text: str) -> str:
    decision_path = repo / "truffles-api" / "app" / "routers" / "webhook" / "decision.py"
    decision_path.parent.mkdir(parents=True, exist_ok=True)
    decision_path.write_text(decision_text, encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def test_legacy_freeze_guard_blocks_executable_additions(tmp_path: Path) -> None:
    module = load_module("legacy_freeze_guard", SCRIPTS / "legacy_freeze_guard.py")
    repo, _ = init_repo(tmp_path)
    config = write_config(repo)
    base = commit_base(repo, "def keep():\n    return 1\n")
    decision_path = repo / "truffles-api" / "app" / "routers" / "webhook" / "decision.py"
    decision_path.write_text("def keep():\n    return 1\n\nvalue = 2\n", encoding="utf-8")

    violations = module.evaluate(repo, config, base, None)
    assert violations
    assert "decision.py" in violations[0]


def test_legacy_freeze_guard_allows_comment_only_additions(tmp_path: Path) -> None:
    module = load_module("legacy_freeze_guard", SCRIPTS / "legacy_freeze_guard.py")
    repo, _ = init_repo(tmp_path)
    config = write_config(repo)
    base = commit_base(repo, "def keep():\n    return 1\n")
    decision_path = repo / "truffles-api" / "app" / "routers" / "webhook" / "decision.py"
    decision_path.write_text("def keep():\n    return 1\n\n# comment only\n", encoding="utf-8")

    violations = module.evaluate(repo, config, base, None)
    assert violations == []


def test_legacy_freeze_guard_allows_only_scoped_waiver_lines(tmp_path: Path) -> None:
    module = load_module("legacy_freeze_guard", SCRIPTS / "legacy_freeze_guard.py")
    repo, _ = init_repo(tmp_path)
    config = write_config(repo)
    config["sunset_files"][0]["active_waiver"] = {
        "allowed_executable_lines": [
            "value = 2",
        ]
    }
    base = commit_base(repo, "def keep():\n    return 1\n")
    decision_path = repo / "truffles-api" / "app" / "routers" / "webhook" / "decision.py"
    decision_path.write_text("def keep():\n    return 1\n\nvalue = 2\n", encoding="utf-8")

    violations = module.evaluate(repo, config, base, None)
    assert violations == []


def test_legacy_freeze_guard_blocks_non_waived_lines_even_with_scoped_waiver(tmp_path: Path) -> None:
    module = load_module("legacy_freeze_guard", SCRIPTS / "legacy_freeze_guard.py")
    repo, _ = init_repo(tmp_path)
    config = write_config(repo)
    config["sunset_files"][0]["active_waiver"] = {
        "allowed_executable_lines": [
            "value = 2",
        ]
    }
    base = commit_base(repo, "def keep():\n    return 1\n")
    decision_path = repo / "truffles-api" / "app" / "routers" / "webhook" / "decision.py"
    decision_path.write_text(
        "def keep():\n    return 1\n\nvalue = 2\n\nanother_value = 3\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo, config, base, None)
    assert violations
    assert "another_value = 3" in violations[0]
