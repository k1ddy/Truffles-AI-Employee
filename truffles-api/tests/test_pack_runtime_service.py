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
