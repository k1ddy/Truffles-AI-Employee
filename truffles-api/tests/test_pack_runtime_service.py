from pathlib import Path

from app.services import demo_salon_knowledge as demo_runtime
from app.services import pack_runtime_default as default_runtime
from app.services import pack_runtime_service as runtime
from app.services.pack_runtime_types import PackDecision


def _project_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "app/services/pack_runtime_default.py").exists():
            return candidate
    return here.parents[1]


def _services_file(relative_path: str) -> Path:
    root = _project_root()
    return root / relative_path


def test_pack_runtime_service_reexports_default_adapter() -> None:
    assert runtime.get_pack_decision is not default_runtime.get_pack_decision
    assert runtime.get_pack_service_decision is not default_runtime.get_pack_service_decision
    assert runtime.get_pack_adapter is default_runtime.get_pack_adapter
    assert runtime.get_pack_price_reply is default_runtime.get_pack_price_reply
    assert runtime.get_pack_price_item is default_runtime.get_pack_price_item
    assert runtime.get_pack_service_hint is default_runtime.get_pack_service_hint


def test_get_pack_decision_enriches_resolver_contract(monkeypatch) -> None:
    base_decision = PackDecision(
        action="reply",
        response="Цена 10000 тг.",
        intent="price_query",
        meta={
            "fact_source": "truth",
            "service_query": "Маникюр",
            "service_query_source": "semantic_match",
            "service_query_score": 0.88,
        },
    )
    monkeypatch.setattr(runtime, "_runtime_get_pack_decision", lambda *_args, **_kwargs: base_decision)

    decision = runtime.get_pack_decision("Сколько стоит маникюр?", client_slug="demo_salon")

    assert isinstance(decision, PackDecision)
    assert decision is not base_decision
    meta = decision.meta or {}
    assert meta.get("resolver_id") == "pack_runtime.truth_gate"
    assert meta.get("resolver_version")
    assert meta.get("intent_class") == "price_query"
    assert meta.get("action_class") == "FACT"
    assert meta.get("resolver_confidence") == 0.88
    assert isinstance(meta.get("resolver_candidates"), list) and meta.get("resolver_candidates")
    assert isinstance(meta.get("resolver_contract"), dict)


def test_get_pack_service_decision_enriches_collect_contract_for_escalation(monkeypatch) -> None:
    base_decision = PackDecision(
        action="escalate",
        response="Передам администратору.",
        intent="service_clarify",
        meta={"clarify_reason": "missing_service_query"},
    )
    monkeypatch.setattr(
        runtime,
        "_runtime_get_pack_service_decision",
        lambda *_args, **_kwargs: base_decision,
    )

    decision = runtime.get_pack_service_decision("Классический интересует", client_slug="demo_salon")

    assert isinstance(decision, PackDecision)
    meta = decision.meta or {}
    assert meta.get("resolver_id") == "pack_runtime.service_matcher"
    assert meta.get("action_class") == "HANDOFF"
    assert meta.get("abstain_reason") in {"missing_service_query", "handoff_required"}


def test_has_walkin_without_booking_signal_fallback() -> None:
    assert runtime.has_walkin_without_booking_signal("Можно прийти без записи?")
    assert not runtime.has_walkin_without_booking_signal("Хочу записаться на завтра")


def test_pack_runtime_decision_back_compat_alias() -> None:
    assert runtime.PackDecision is PackDecision
    assert runtime.DemoSalonDecision is PackDecision
    assert demo_runtime.DemoSalonDecision is PackDecision


def test_pack_runtime_default_does_not_import_demo_module_directly() -> None:
    content = _services_file("app/services/pack_runtime_default.py").read_text(encoding="utf-8")
    assert "demo_salon_knowledge" not in content


def test_pack_runtime_generic_adapter_avoids_demo_module_imports() -> None:
    content = _services_file("app/services/pack_runtime_generic_adapter.py").read_text(encoding="utf-8")
    assert "demo_salon_knowledge" not in content
    assert "pack_runtime_demo_adapter" not in content


def test_pack_runtime_fallback_adapter_avoids_demo_module_imports() -> None:
    content = _services_file("app/services/pack_runtime_fallback_adapter.py").read_text(encoding="utf-8")
    assert "demo_salon_knowledge" not in content
    assert "pack_runtime_demo_adapter" not in content


def test_pack_runtime_default_routes_demo_slug_to_explicit_adapter() -> None:
    adapter = default_runtime._resolve_adapter("demo_salon")
    assert adapter.__name__ == "app.services.pack_runtime_demo_adapter"

    default_adapter = default_runtime._resolve_adapter("non_existing_slug")
    assert default_adapter.__name__ == "app.services.pack_runtime_generic_adapter"
