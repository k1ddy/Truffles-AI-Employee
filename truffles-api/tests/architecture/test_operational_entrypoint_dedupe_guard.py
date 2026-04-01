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
                "path": "truffles-api/app/services/outbox_runtime_service.py",
                "required_function_defs": [
                    "run_canonical_outbox_process",
                    "run_default_outbox_process",
                    "run_scoped_outbox_process",
                    "run_outbox_worker_cycle",
                ],
            },
            {
                "path": "truffles-api/app/routers/console.py",
                "required_import_names": ["run_scoped_outbox_process"],
            },
        ],
        "function_call_contracts": [
            {
                "path": "truffles-api/app/services/outbox_runtime_service.py",
                "function_name": "run_default_outbox_process",
                "required_calls": ["run_canonical_outbox_process"],
            },
            {
                "path": "truffles-api/app/services/outbox_runtime_service.py",
                "function_name": "run_scoped_outbox_process",
                "required_calls": ["run_canonical_outbox_process"],
            },
            {
                "path": "truffles-api/app/services/outbox_runtime_service.py",
                "function_name": "run_outbox_worker_cycle",
                "required_calls": ["run_canonical_outbox_process"],
            },
            {
                "path": "truffles-api/app/routers/console.py",
                "function_name": "_run_outbox_process_job",
                "required_calls": ["run_scoped_outbox_process"],
                "forbidden_calls": ["claim_scoped_outbox_rows", "process_claimed_outbox_rows"],
            }
        ],
        "repo_callsite_contracts": [
            {
                "search_roots": ["truffles-api/app"],
                "call_names": ["run_canonical_outbox_process"],
                "exact_allowlist": ["truffles-api/app/services/outbox_runtime_service.py"],
            },
            {
                "search_roots": ["truffles-api/app"],
                "call_names": ["run_scoped_outbox_process"],
                "exact_allowlist": ["truffles-api/app/routers/console.py"],
            }
        ],
    }
    path = repo / "docs" / "OPERATIONAL_ENTRYPOINT_DEDUPE_GUARD.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config


def write_repo(repo: Path, *, drift: bool = False) -> None:
    service_path = repo / "truffles-api" / "app" / "services" / "outbox_runtime_service.py"
    service_path.parent.mkdir(parents=True, exist_ok=True)
    service_path.write_text(
        "async def run_canonical_outbox_process():\n    return {}\n\n"
        "async def run_default_outbox_process():\n    return await run_canonical_outbox_process()\n\n"
        "async def run_scoped_outbox_process():\n    return await run_canonical_outbox_process()\n\n"
        "async def run_outbox_worker_cycle():\n    return await run_canonical_outbox_process()\n",
        encoding="utf-8",
    )

    console_path = repo / "truffles-api" / "app" / "routers" / "console.py"
    console_path.parent.mkdir(parents=True, exist_ok=True)
    if drift:
        console_path.write_text(
            "from app.services.outbox_runtime_service import run_scoped_outbox_process\n\n"
            "async def _run_outbox_process_job():\n"
            "    claim_scoped_outbox_rows()\n"
            "    process_claimed_outbox_rows()\n"
            "    return await run_scoped_outbox_process()\n\n",
            encoding="utf-8",
        )
        extra_path = repo / "truffles-api" / "app" / "routers" / "admin.py"
        extra_path.write_text(
            "from app.services.outbox_runtime_service import run_scoped_outbox_process\n\n"
            "async def process_outbox():\n"
            "    return await run_scoped_outbox_process()\n",
            encoding="utf-8",
        )
    else:
        console_path.write_text(
            "from app.services.outbox_runtime_service import run_scoped_outbox_process\n\n"
            "async def _run_outbox_process_job():\n"
            "    return await run_scoped_outbox_process()\n",
            encoding="utf-8",
        )



def test_operational_entrypoint_dedupe_guard_allows_exact_snapshot(tmp_path: Path) -> None:
    module = load_module("operational_entrypoint_dedupe_guard", SCRIPTS / "operational_entrypoint_dedupe_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    config = write_config(repo)
    write_repo(repo)

    assert module.evaluate(repo, config) == []



def test_operational_entrypoint_dedupe_guard_blocks_console_drift(tmp_path: Path) -> None:
    module = load_module("operational_entrypoint_dedupe_guard", SCRIPTS / "operational_entrypoint_dedupe_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    config = write_config(repo)
    write_repo(repo, drift=True)

    violations = module.evaluate(repo, config)
    assert violations
    assert any("forbidden call still present -> claim_scoped_outbox_rows" in item for item in violations)
    assert any("forbidden call still present -> process_claimed_outbox_rows" in item for item in violations)
    assert any("repo callsite set for run_scoped_outbox_process grew without waiver" in item for item in violations)



def test_repo_operational_entrypoint_dedupe_snapshot_matches_current_repo() -> None:
    module = load_module("operational_entrypoint_dedupe_guard", SCRIPTS / "operational_entrypoint_dedupe_guard.py")
    config = yaml.safe_load((ROOT / "docs" / "OPERATIONAL_ENTRYPOINT_DEDUPE_GUARD.yaml").read_text(encoding="utf-8"))

    assert module.evaluate(ROOT, config) == []
