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
        "continuity_guard": {
            "allowed_writer_paths": [
                "truffles-api/app/routers/webhook/context_manager.py",
            ],
            "guarded_tokens": [
                "expected_reply_type",
                "expected_reply_reason",
                "interaction_state",
                "pending_resume",
            ],
        }
    }
    path = repo / "docs" / "LEGACY_SUNSET.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config


def commit_base(repo: Path) -> str:
    allowed = repo / "truffles-api" / "app" / "routers" / "webhook" / "context_manager.py"
    decision = repo / "truffles-api" / "app" / "routers" / "webhook" / "decision.py"
    rogue = repo / "truffles-api" / "app" / "services" / "rogue.py"
    allowed.parent.mkdir(parents=True, exist_ok=True)
    rogue.parent.mkdir(parents=True, exist_ok=True)
    allowed.write_text("context = {}\n", encoding="utf-8")
    decision.write_text("context = {}\n", encoding="utf-8")
    rogue.write_text("context = {}\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def test_continuity_writer_guard_blocks_new_writer_outside_allowed_paths(tmp_path: Path) -> None:
    module = load_module("continuity_writer_guard", SCRIPTS / "continuity_writer_guard.py")
    repo = init_repo(tmp_path)
    config = write_config(repo)
    base = commit_base(repo)
    rogue = repo / "truffles-api" / "app" / "services" / "rogue.py"
    rogue.write_text('context = {}\ncontext["expected_reply_type"] = "time"\n', encoding="utf-8")

    violations = module.evaluate(repo, config, base, None)
    assert violations
    assert "rogue.py" in violations[0]


def test_continuity_writer_guard_allows_current_writer_paths(tmp_path: Path) -> None:
    module = load_module("continuity_writer_guard", SCRIPTS / "continuity_writer_guard.py")
    repo = init_repo(tmp_path)
    config = write_config(repo)
    base = commit_base(repo)
    allowed = repo / "truffles-api" / "app" / "routers" / "webhook" / "context_manager.py"
    allowed.write_text('context = {}\ncontext["expected_reply_type"] = "time"\n', encoding="utf-8")

    violations = module.evaluate(repo, config, base, None)
    assert violations == []


def test_continuity_writer_guard_ignores_local_read_or_trace_plumbing(tmp_path: Path) -> None:
    module = load_module("continuity_writer_guard", SCRIPTS / "continuity_writer_guard.py")
    repo = init_repo(tmp_path)
    config = write_config(repo)
    base = commit_base(repo)
    rogue = repo / "truffles-api" / "app" / "services" / "rogue.py"
    rogue.write_text(
        "\n".join(
            [
                "def build(payload, trace):",
                "    expected_reply_type = payload.get('expected_reply_type')",
                "    trace_event = {'expected_reply_type': expected_reply_type}",
                "    return trace_event",
                "",
            ]
        ),
        encoding="utf-8",
    )

    violations = module.evaluate(repo, config, base, None)
    assert violations == []


def test_continuity_writer_guard_blocks_context_assignment_from_pending_resume_helper(tmp_path: Path) -> None:
    module = load_module("continuity_writer_guard", SCRIPTS / "continuity_writer_guard.py")
    repo = init_repo(tmp_path)
    config = write_config(repo)
    base = commit_base(repo)
    rogue = repo / "truffles-api" / "app" / "services" / "rogue.py"
    rogue.write_text(
        "\n".join(
            [
                "def sync(conversation, now):",
                "    restored_context, _ = _restore_pending_resume_context(conversation.context, now=now)",
                "    conversation.context = restored_context",
                "",
            ]
        ),
        encoding="utf-8",
    )

    violations = module.evaluate(repo, config, base, None)
    assert violations
    assert "conversation.context = restored_context" in violations[0]


def test_continuity_writer_guard_allows_scoped_waiver_lines_in_frozen_file(tmp_path: Path) -> None:
    module = load_module("continuity_writer_guard", SCRIPTS / "continuity_writer_guard.py")
    repo = init_repo(tmp_path)
    config = write_config(repo)
    config["sunset_files"] = [
        {
            "path": "truffles-api/app/routers/webhook/decision.py",
            "active_waiver": {
                "allowed_executable_lines": [
                    'context["expected_reply_type"] = "time"',
                ]
            },
        }
    ]
    base = commit_base(repo)
    decision = repo / "truffles-api" / "app" / "routers" / "webhook" / "decision.py"
    decision.write_text('context = {}\ncontext["expected_reply_type"] = "time"\n', encoding="utf-8")

    violations = module.evaluate(repo, config, base, None)
    assert violations == []


def test_continuity_writer_guard_blocks_non_waived_lines_in_frozen_file(tmp_path: Path) -> None:
    module = load_module("continuity_writer_guard", SCRIPTS / "continuity_writer_guard.py")
    repo = init_repo(tmp_path)
    config = write_config(repo)
    config["sunset_files"] = [
        {
            "path": "truffles-api/app/routers/webhook/decision.py",
            "active_waiver": {
                "allowed_executable_lines": [
                    'context["expected_reply_type"] = "time"',
                ]
            },
        }
    ]
    base = commit_base(repo)
    decision = repo / "truffles-api" / "app" / "routers" / "webhook" / "decision.py"
    decision.write_text(
        'context = {}\ncontext["expected_reply_type"] = "time"\ncontext["expected_reply_reason"] = "slot"\n',
        encoding="utf-8",
    )

    violations = module.evaluate(repo, config, base, None)
    assert violations
    assert "expected_reply_reason" in violations[0]
