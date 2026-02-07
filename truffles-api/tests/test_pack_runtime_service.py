from pathlib import Path

from app.services import demo_salon_knowledge as demo_runtime
from app.services import pack_runtime_default as default_runtime
from app.services import pack_runtime_service as runtime
from app.services.pack_runtime_types import PackDecision


def test_pack_runtime_service_reexports_default_adapter() -> None:
    assert runtime.get_pack_decision is default_runtime.get_pack_decision
    assert runtime.get_pack_service_decision is default_runtime.get_pack_service_decision
    assert runtime.get_pack_price_reply is default_runtime.get_pack_price_reply
    assert runtime.get_pack_price_item is default_runtime.get_pack_price_item
    assert runtime.get_pack_service_hint is default_runtime.get_pack_service_hint


def test_pack_runtime_decision_back_compat_alias() -> None:
    assert runtime.PackDecision is PackDecision
    assert runtime.DemoSalonDecision is PackDecision
    assert demo_runtime.DemoSalonDecision is PackDecision


def test_pack_runtime_default_does_not_import_demo_module_directly() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    content = (repo_root / "truffles-api/app/services/pack_runtime_default.py").read_text(
        encoding="utf-8"
    )
    assert "demo_salon_knowledge" not in content


def test_pack_runtime_default_routes_demo_slug_to_explicit_adapter() -> None:
    adapter = default_runtime._resolve_adapter("demo_salon")
    assert adapter.__name__ == "app.services.pack_runtime_demo_adapter"

    default_adapter = default_runtime._resolve_adapter("non_existing_slug")
    assert default_adapter.__name__ == "app.services.pack_runtime_generic_adapter"
