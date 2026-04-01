from __future__ import annotations

import importlib.util
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


def write_config(repo: Path) -> dict:
    config = {
        "version": "test",
        "hotspots": [
            {
                "path": "truffles-api/app/core/dialog_state_service.py",
                "required_function_defs": [
                    "project_context_manager_pending_question_contract",
                    "restore_pending_resume_payload",
                ],
            },
            {
                "path": "truffles-api/app/services/state_service.py",
                "required_function_defs": [
                    "_prepare_pending_handoff_resume_boundary_restore",
                ],
            },
            {
                "path": "truffles-api/app/services/outbox_runtime_service.py",
                "required_function_defs": [
                    "run_canonical_outbox_process",
                    "run_default_outbox_process",
                ],
            },
        ],
        "function_call_contracts": [
            {
                "path": "truffles-api/app/core/dialog_state_service.py",
                "function_name": "restore_pending_resume_payload",
                "required_calls": ["project_context_manager_pending_question_contract"],
                "forbidden_calls": ["project_context_pending_question_contract"],
            },
            {
                "path": "truffles-api/app/services/state_service.py",
                "function_name": "_prepare_pending_handoff_resume_boundary_restore",
                "required_calls": ["project_context_manager_pending_question_contract"],
                "forbidden_calls": ["_derive_pending_resume_reason"],
            },
            {
                "path": "truffles-api/app/services/outbox_runtime_service.py",
                "function_name": "run_default_outbox_process",
                "required_calls": ["run_canonical_outbox_process"],
            },
        ],
        "function_source_contracts": [
            {
                "path": "truffles-api/app/services/state_service.py",
                "function_name": "_prepare_pending_handoff_resume_boundary_restore",
                "forbidden_substrings": ['boundary_payload.get("expected_reply_type")'],
            }
        ],
    }
    path = repo / "docs" / "SYSTEM_REPROOF_GUARD.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config


def write_repo(repo: Path, *, drift: bool = False) -> None:
    dialog_path = repo / "truffles-api" / "app" / "core" / "dialog_state_service.py"
    dialog_path.parent.mkdir(parents=True, exist_ok=True)
    if drift:
        dialog_path.write_text(
            "def project_context_pending_question_contract():\n    return {}\n\n"
            "def restore_pending_resume_payload():\n"
            "    project_context_pending_question_contract()\n"
            "    return {}\n",
            encoding="utf-8",
        )
    else:
        dialog_path.write_text(
            "def project_context_manager_pending_question_contract():\n    return {}\n\n"
            "def restore_pending_resume_payload():\n"
            "    project_context_manager_pending_question_contract()\n"
            "    return {}\n",
            encoding="utf-8",
        )

    state_path = repo / "truffles-api" / "app" / "services" / "state_service.py"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    if drift:
        state_path.write_text(
            "class Dummy:\n"
            "    def project_context_manager_pending_question_contract(self):\n"
            "        return {}\n\n"
            "def _dialog_state_service():\n"
            "    return Dummy()\n\n"
            "def _derive_pending_resume_reason(context):\n"
            "    return None\n\n"
            "def _prepare_pending_handoff_resume_boundary_restore():\n"
            "    _dialog_state_service().project_context_manager_pending_question_contract()\n"
            '    boundary_payload.get("expected_reply_type")\n'
            "    _derive_pending_resume_reason({})\n"
            "    return {}\n",
            encoding="utf-8",
        )
    else:
        state_path.write_text(
            "class Dummy:\n"
            "    def project_context_manager_pending_question_contract(self):\n"
            "        return {}\n\n"
            "def _dialog_state_service():\n"
            "    return Dummy()\n\n"
            "def _prepare_pending_handoff_resume_boundary_restore():\n"
            "    _dialog_state_service().project_context_manager_pending_question_contract()\n"
            "    return {}\n",
            encoding="utf-8",
        )

    outbox_path = repo / "truffles-api" / "app" / "services" / "outbox_runtime_service.py"
    outbox_path.parent.mkdir(parents=True, exist_ok=True)
    if drift:
        outbox_path.write_text(
            "async def run_canonical_outbox_process():\n    return {}, {}\n\n"
            "async def run_default_outbox_process():\n    return {}\n",
            encoding="utf-8",
        )
    else:
        outbox_path.write_text(
            "async def run_canonical_outbox_process():\n    return {}, {}\n\n"
            "async def run_default_outbox_process():\n    return await run_canonical_outbox_process()\n",
            encoding="utf-8",
        )


def test_system_reproof_guard_allows_exact_snapshot(tmp_path: Path) -> None:
    module = load_module("system_reproof_guard", SCRIPTS / "system_reproof_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    config = write_config(repo)
    write_repo(repo)

    assert module.evaluate(repo, config) == []


def test_system_reproof_guard_blocks_reintroduced_fallbacks(tmp_path: Path) -> None:
    module = load_module("system_reproof_guard", SCRIPTS / "system_reproof_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    config = write_config(repo)
    write_repo(repo, drift=True)

    violations = module.evaluate(repo, config)
    assert violations
    assert any("forbidden call still present -> project_context_pending_question_contract" in item for item in violations)
    assert any("forbidden call still present -> _derive_pending_resume_reason" in item for item in violations)
    assert any('forbidden source snippet still present -> boundary_payload.get("expected_reply_type")' in item for item in violations)
    assert any("function missing or empty -> run_default_outbox_process" in item for item in violations)


def test_repo_system_reproof_guard_snapshot_matches_current_repo() -> None:
    module = load_module("system_reproof_guard", SCRIPTS / "system_reproof_guard.py")
    config = yaml.safe_load((ROOT / "docs" / "SYSTEM_REPROOF_GUARD.yaml").read_text(encoding="utf-8"))

    assert module.evaluate(ROOT, config) == []
