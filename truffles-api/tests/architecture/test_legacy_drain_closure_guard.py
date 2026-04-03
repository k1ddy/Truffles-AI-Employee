from __future__ import annotations

import importlib.util
import json
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


def _load_config() -> dict:
    return yaml.safe_load((ROOT / "docs/LEGACY_DRAIN_CLOSURE_GUARD.yaml").read_text(encoding="utf-8"))


def _load_registry() -> dict:
    return json.loads((ROOT / "docs/system_forensics/dead_surface_registry.json").read_text(encoding="utf-8"))


def test_repo_legacy_drain_closure_guard_snapshot_matches_current_repo() -> None:
    module = load_module("legacy_drain_closure_guard", SCRIPTS / "legacy_drain_closure_guard.py")
    config = _load_config()
    registry = _load_registry()

    assert module.evaluate(ROOT, config, registry) == []


def test_dead_surface_registry_marks_touched_envelope_adapter_and_unreachable_surfaces() -> None:
    registry = _load_registry()
    entries = {item["surface_path"]: item for item in registry["entries"]}

    assert registry["status"] == "machine_readable_system_reproof_base"
    assert registry["active_block"] == "Consultant Core Block G — Operational Final Dedupe"
    assert registry["caller_proof_law"]["adapter_only_for_touched_envelope"] == [
        "truffles-api/app/routers/webhook/http.py",
        "truffles-api/app/routers/webhook/session_memory.py",
    ]
    assert registry["caller_proof_law"]["startup_load_drained_from_package_root"] == [
        "truffles-api/app/routers/webhook/booking.py",
        "truffles-api/app/routers/webhook/context_manager.py",
        "truffles-api/app/routers/webhook/dedup.py",
        "truffles-api/app/routers/webhook/response.py",
    ]
    assert entries["truffles-api/app/routers/webhook/http.py"]["family_envelope_status"] == (
        "adapter_only_for_touched_envelope"
    )
    assert entries["truffles-api/app/routers/webhook/__init__.py"]["final_fate"] == "adapter_only"
    assert entries["truffles-api/app/routers/webhook/session_memory.py"]["final_fate"] == "adapter_only"
    assert entries["truffles-api/app/routers/webhook/session_memory.py"]["family_envelope_status"] == (
        "adapter_only_for_touched_envelope"
    )
    assert entries["truffles-api/app/routers/webhook/decision.py"]["final_fate"] == "unreachable"
    assert entries["truffles-api/app/routers/webhook/info.py"]["final_fate"] == "unreachable"
    assert entries["truffles-api/app/routers/webhook/context_manager.py"]["final_fate"] == "unreachable"
    assert entries["truffles-api/app/routers/webhook/context_manager.py"]["family_envelope_status"] == (
        "unreachable_for_touched_envelope"
    )
    assert entries["truffles-api/app/routers/webhook/booking.py"]["startup_load_mode"] == "lazy_export_only"
    assert entries["truffles-api/app/routers/webhook/booking.py"]["live_runtime_callers"] == []
    assert entries["truffles-api/app/routers/webhook/response.py"]["startup_load_mode"] == "lazy_export_only"
    assert entries["truffles-api/app/routers/webhook/response.py"]["live_runtime_callers"] == []


def test_webhook_package_root_uses_lazy_legacy_compat_exports_only() -> None:
    init_text = (ROOT / "truffles-api/app/routers/webhook/__init__.py").read_text(encoding="utf-8")
    config = _load_config()

    assert "from app.routers.webhook.booking import" not in init_text
    assert "from app.routers.webhook.context_manager import" not in init_text
    assert "from app.routers.webhook.dedup import" not in init_text
    assert "from .response import _apply_quiet_hours_notice, _maybe_append_booking_cta" not in init_text
    assert "_LAZY_COMPAT_EXPORTS" in init_text
    assert "import_module(" in init_text
    assert config["package_root_final_fate"] == "adapter_only"


def test_block_f_surface_fate_contract_matches_live_import_topology() -> None:
    module = load_module("legacy_drain_closure_guard", SCRIPTS / "legacy_drain_closure_guard.py")
    config = _load_config()

    assert config["final_fate_set"] == ["adapter_only", "observer_only", "unreachable", "removed"]
    assert config["surface_fates"]["session_memory"]["final_fate"] == "adapter_only"
    assert config["surface_fates"]["decision"]["final_fate"] == "unreachable"
    assert config["surface_fates"]["info"]["final_fate"] == "unreachable"
    assert config["surface_fates"]["context_manager"]["final_fate"] == "unreachable"

    violations: list[str] = []
    module._validate_surface_fates(ROOT, config, violations)
    assert violations == []
