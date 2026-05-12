from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts/semantic_contract_sync_guard.py"
PROMPT_PATH = Path("prompts/llm_policy_core.md")
PROMPT_SERVICE_PATH = Path("truffles-api/app/services/policy_prompt_snapshot_service.py")
VOCAB_SERVICE_PATH = Path("truffles-api/app/services/policy_vocabulary_snapshot_service.py")
INTENT_SCHEMA_PATH = Path("truffles-api/app/schemas/intent.py")
MARKER = "{{GENERATED_MIXED_FIRST_TURN_FACT_CONTRACT_BLOCK}}"
FULL_INJECTION_SNIPPET = (
    "prompt_text = _inject_policy_core_generated_contract_blocks(prompt_text, compact=False)"
)


def _run_guard(repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_minimal_repo(tmp_path: Path) -> Path:
    for relative_path in (
        PROMPT_PATH,
        PROMPT_SERVICE_PATH,
        VOCAB_SERVICE_PATH,
        INTENT_SCHEMA_PATH,
    ):
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relative_path, target)

    for package_init in (
        "truffles-api/app/__init__.py",
        "truffles-api/app/services/__init__.py",
        "truffles-api/app/schemas/__init__.py",
    ):
        _write_text(tmp_path / package_init, "")
    return tmp_path


def test_semantic_contract_sync_guard_passes_on_current_repo():
    result = _run_guard(REPO_ROOT)

    assert result.returncode == 0, result.stderr
    assert "semantic_contract_sync_guard: OK" in result.stdout


def test_semantic_contract_sync_guard_fails_when_prompt_marker_is_removed(tmp_path: Path):
    repo_root = _build_minimal_repo(tmp_path)
    prompt_path = repo_root / PROMPT_PATH
    prompt_path.write_text(
        prompt_path.read_text(encoding="utf-8").replace(MARKER, "", 1),
        encoding="utf-8",
    )

    result = _run_guard(repo_root)

    assert result.returncode == 1
    assert "must contain generated contract marker exactly once" in result.stderr


def test_semantic_contract_sync_guard_fails_when_full_prompt_loader_skips_injection(tmp_path: Path):
    repo_root = _build_minimal_repo(tmp_path)
    service_path = repo_root / PROMPT_SERVICE_PATH
    service_path.write_text(
        service_path.read_text(encoding="utf-8").replace(
            FULL_INJECTION_SNIPPET,
            'prompt_text = prompt_text',
            1,
        ),
        encoding="utf-8",
    )

    result = _run_guard(repo_root)

    assert result.returncode == 1
    assert "full prompt loader no longer routes through generated contract injector" in result.stderr


def test_semantic_contract_sync_guard_fails_when_boundary_literal_is_not_declared(tmp_path: Path):
    repo_root = _build_minimal_repo(tmp_path)
    service_path = repo_root / PROMPT_SERVICE_PATH
    service_path.write_text(
        service_path.read_text(encoding="utf-8").replace(
            '            expected_reply_type="service_choice",\n'
            '            next_question="service",\n'
            '            open_questions=["service"],\n'
            '            goal="booking",\n'
            '            referents={},\n'
            '            subject_kind="general",',
            '            expected_reply_type="phone",\n'
            '            next_question="service",\n'
            '            open_questions=["service"],\n'
            '            goal="booking",\n'
            '            referents={},\n'
            '            subject_kind="general",',
            1,
        ),
        encoding="utf-8",
    )

    result = _run_guard(repo_root)

    assert result.returncode == 1
    assert "boundary payload literals missing from generated semantic token coverage expected_reply_types" in result.stderr
