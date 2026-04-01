from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_registry() -> dict:
    return json.loads((ROOT / "docs/system_forensics/dead_surface_registry.json").read_text(encoding="utf-8"))


def test_legacy_mesh_caller_guard_matches_live_registry() -> None:
    module = load_module("legacy_mesh_caller_guard", SCRIPTS / "legacy_mesh_caller_guard.py")
    registry = _load_registry()

    assert module.evaluate(ROOT, registry) == []


def test_legacy_mesh_registry_captures_shadow_and_behavior_surfaces() -> None:
    registry = _load_registry()
    entries = {item["surface_path"]: item for item in registry["entries"]}

    assert registry["status"] == "machine_readable_system_reproof_base"
    assert registry["active_block"] == "Consultant Core Continuity / Boundary / Pack-Runtime / Legacy / Operational Reproof"
    assert registry["caller_proof_law"]["mounted_ingress_surfaces"] == [
        "truffles-api/app/main.py",
        "truffles-api/app/routers/webhook/__init__.py",
        "truffles-api/app/routers/webhook/http.py",
    ]
    assert registry["caller_proof_law"]["behavior_owning_surfaces"] == [
        "truffles-api/app/routers/webhook/http.py",
        "truffles-api/app/routers/webhook/session_memory.py",
    ]
    assert registry["caller_proof_law"]["observer_only_surfaces"] == [
        "truffles-api/app/routers/webhook/trace.py",
    ]
    assert {
        "truffles-api/app/routers/webhook/_legacy.py",
        "truffles-api/app/routers/webhook/decision.py",
        "truffles-api/tests/support_booking_prompt_owner_shadow.py",
        "truffles-api/tests/support_reasoning_core_shadow.py",
        "truffles-api/tests/support_legacy_webhook_shadow.py",
    }.issubset(set(registry["caller_proof_law"]["shadow_only_surfaces"]))
    assert {
        "truffles-api/app/routers/webhook/context_manager.py",
        "truffles-api/app/routers/webhook/response.py",
        "truffles-api/app/routers/webhook/booking.py",
        "truffles-api/app/routers/webhook/info.py",
        "truffles-api/app/routers/webhook/pending.py",
        "truffles-api/app/routers/webhook/policy.py",
        "truffles-api/app/routers/webhook/guards.py",
        "truffles-api/app/routers/webhook/dedup.py",
    }.issubset(set(registry["caller_proof_law"]["unmounted_surfaces"]))
    assert "truffles-api/app/webhook.py" not in registry["caller_proof_law"]["unmounted_surfaces"]
    assert registry["caller_proof_law"]["removed_surfaces"] == [
        "truffles-api/app/core/booking_prompt_owner.py",
        "truffles-api/app/services/reasoning_core.py",
        "truffles-api/app/webhook.py",
    ]

    http_entry = entries["truffles-api/app/routers/webhook/http.py"]
    assert http_entry["live_runtime_callers"] == [
        "truffles-api/app/routers/webhook/__init__.py",
        "truffles-api/app/core/consultant_runtime.py",
    ]
    assert http_entry["static_app_importers"] == [
        "truffles-api/app/core/consultant_runtime.py",
        "truffles-api/app/routers/webhook/__init__.py",
    ]

    reasoning_core_entry = entries["truffles-api/app/services/reasoning_core.py"]
    assert reasoning_core_entry["path_exists_expected"] is False
    assert reasoning_core_entry["classification"] == "removed_runtime_shadow_wrapper"
    assert reasoning_core_entry["static_app_importers"] == []
    assert reasoning_core_entry["test_only_importers"] == []

    support_reasoning_entry = entries["truffles-api/tests/support_reasoning_core_shadow.py"]
    assert support_reasoning_entry["authority_mode"] == "shadow_only_test_support"
    assert support_reasoning_entry["test_only_importers"] == [
        "truffles-api/tests/test_outbox_payload_contract.py",
        "truffles-api/tests/test_reasoning_core.py",
    ]


def test_legacy_mesh_registry_captures_frozen_surface_static_importers() -> None:
    entries = {item["surface_path"]: item for item in _load_registry()["entries"]}

    decision_entry = entries["truffles-api/app/routers/webhook/decision.py"]
    assert decision_entry["static_app_importers"] == [
        "truffles-api/app/routers/webhook/_legacy.py",
    ]
    assert decision_entry["live_runtime_callers"] == []

    booking_entry = entries["truffles-api/app/routers/webhook/booking.py"]
    assert booking_entry["classification"] == "lazy_export_only_unmounted_legacy_helper"
    assert booking_entry["live_runtime_callers"] == []
    assert booking_entry["startup_load_mode"] == "lazy_export_only"
    assert {
        "truffles-api/app/routers/webhook/context_manager.py",
        "truffles-api/app/routers/webhook/decision.py",
        "truffles-api/app/routers/webhook/response.py",
    }.issubset(set(booking_entry["static_app_importers"]))
    assert "truffles-api/app/services/reasoning_core.py" not in booking_entry["static_app_importers"]

    webhook_entry = entries["truffles-api/app/webhook.py"]
    assert webhook_entry["classification"] == "removed_runtime_shadow_wrapper"
    assert webhook_entry["path_exists_expected"] is False
    assert webhook_entry["static_app_importers"] == []
    assert webhook_entry["test_only_importers"] == []

    support_webhook_entry = entries["truffles-api/tests/support_legacy_webhook_shadow.py"]
    assert support_webhook_entry["classification"] == "shadow_only_test_residue"
    assert support_webhook_entry["test_only_importers"] == [
        "truffles-api/tests/test_booking_chaos_dialogs.py",
        "truffles-api/tests/test_message_endpoint.py",
    ]
