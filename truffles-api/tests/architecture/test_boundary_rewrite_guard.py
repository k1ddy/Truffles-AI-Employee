from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed_repo(repo: Path, module) -> None:
    for relative_path in set(module.REQUIRED_SNIPPETS) | {
        module.INTENT_SERVICE,
        module.TURN_PLANNER,
        module.CONSULTANT_RUNTIME,
        module.DIAGNOSE,
    }:
        src = ROOT / relative_path
        dst = repo / relative_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)


def test_boundary_rewrite_guard_matches_current_repo() -> None:
    module = _load_module("boundary_rewrite_guard", SCRIPTS / "boundary_rewrite_guard.py")
    assert module.evaluate(ROOT) == []


def test_boundary_rewrite_guard_flags_missing_runtime_mirror(tmp_path: Path) -> None:
    module = _load_module("boundary_rewrite_guard", SCRIPTS / "boundary_rewrite_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo, module)

    runtime_path = repo / module.CONSULTANT_RUNTIME
    text = runtime_path.read_text(encoding="utf-8")
    runtime_path.write_text(
        text.replace('decision_meta["boundary_normalization_used"] = bool(', 'decision_meta["boundary_norm_used"] = bool('),
        encoding="utf-8",
    )

    violations = module.evaluate(repo)
    assert any("consultant_runtime.py missing required boundary rewrite snippet" in item for item in violations)


def test_boundary_rewrite_guard_flags_token_path_growth(tmp_path: Path) -> None:
    module = _load_module("boundary_rewrite_guard", SCRIPTS / "boundary_rewrite_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo, module)

    rogue = repo / "truffles-api" / "app" / "core" / "rogue_boundary.py"
    rogue.parent.mkdir(parents=True, exist_ok=True)
    rogue.write_text(
        "boundary_normalization_used = True\n",
        encoding="utf-8",
    )

    violations = module.evaluate(repo)
    assert any("token path set for boundary_normalization_used grew without waiver" in item for item in violations)


def test_boundary_rewrite_guard_flags_missing_reason_whitelist_member(tmp_path: Path) -> None:
    module = _load_module("boundary_rewrite_guard", SCRIPTS / "boundary_rewrite_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo, module)

    diagnose_path = repo / module.DIAGNOSE
    text = diagnose_path.read_text(encoding="utf-8")
    diagnose_path.write_text(
        text.replace('    "boundary_semantic_normalization",\n', ""),
        encoding="utf-8",
    )

    violations = module.evaluate(repo)
    assert any("LLM_POLICY_OVERRIDE_REASON_WHITELIST missing boundary_semantic_normalization" in item for item in violations)
