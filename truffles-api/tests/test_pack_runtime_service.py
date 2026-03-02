from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from app.services import demo_salon_knowledge as demo_runtime
from app.services import pack_runtime_default as default_runtime
from app.services import pack_runtime_service as runtime
from app.services.knowledge_runtime import RuntimeTruth, set_runtime_truth
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


@contextmanager
def _runtime_truth(payload: dict, *, slug: str, branch_id=None):
    runtime_payload = RuntimeTruth(
        truth=payload,
        client_slug=slug,
        branch_id=branch_id,
        source="test_pack_runtime_service",
        allow_fallback=False,
    )
    set_runtime_truth(runtime_payload)
    try:
        yield
    finally:
        set_runtime_truth(None)


def test_pack_runtime_service_reexports_default_adapter() -> None:
    assert runtime.get_pack_decision is not default_runtime.get_pack_decision
    assert runtime.get_pack_service_decision is not default_runtime.get_pack_service_decision
    assert runtime.get_pack_adapter is default_runtime.get_pack_adapter
    assert runtime.get_pack_price_reply is default_runtime.get_pack_price_reply
    assert runtime.get_pack_price_item is default_runtime.get_pack_price_item
    assert runtime.get_pack_service_hint is not default_runtime.get_pack_service_hint
    assert runtime.semantic_service_match is not default_runtime.semantic_service_match


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
    fact_bundle = meta.get("fact_bundle")
    assert isinstance(fact_bundle, dict)
    assert fact_bundle.get("pack_id") == "demo_salon"
    assert fact_bundle.get("source_ref") == "truth"
    assert isinstance(meta.get("provenance"), dict)
    assert meta.get("provenance", {}).get("pack_id") == "demo_salon"


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


def test_has_consult_recommendation_signal_prefers_contract_meta() -> None:
    decision = PackDecision(
        action="reply",
        response="Подберу вариант.",
        intent="service_match",
        meta={
            "consult_recommendation": True,
            "resolver_contract": {
                "intent_class": "service_match",
                "action_class": "FACT",
                "confidence": 0.9,
                "abstain_reason": None,
            },
        },
    )
    assert runtime.has_consult_recommendation_signal(decision) is True


def test_is_timeout_fact_fallback_candidate_requires_fact_confidence_margin() -> None:
    fact_decision = PackDecision(
        action="reply",
        response="Салон работает с 9:00 до 21:00.",
        intent="hours",
        meta={
            "resolver_contract": {
                "intent_class": "hours",
                "action_class": "FACT",
                "confidence": 0.83,
                "abstain_reason": None,
            }
        },
    )
    assert runtime.is_timeout_fact_fallback_candidate(fact_decision, min_confidence=0.6) is True

    abstain_decision = PackDecision(
        action="reply",
        response="Нужно уточнение.",
        intent="hours",
        meta={
            "resolver_contract": {
                "intent_class": "hours",
                "action_class": "FACT",
                "confidence": 0.91,
                "abstain_reason": "low_confidence_collect",
            }
        },
    )
    assert runtime.is_timeout_fact_fallback_candidate(abstain_decision, min_confidence=0.6) is False

    low_conf_decision = PackDecision(
        action="reply",
        response="Возможно, это по прайсу.",
        intent="pricing",
        meta={
            "resolver_contract": {
                "intent_class": "pricing",
                "action_class": "FACT",
                "confidence": 0.41,
                "abstain_reason": None,
            }
        },
    )
    assert runtime.is_timeout_fact_fallback_candidate(low_conf_decision, min_confidence=0.6) is False


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
    assert "_PACK_ADAPTER_BY_SLUG" not in content


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
    assert adapter.__name__ == "app.services.pack_runtime_demo_salon_adapter"

    default_adapter = default_runtime._resolve_adapter("non_existing_slug")
    assert default_adapter.__name__ == "app.services.pack_runtime_generic_adapter"


def test_pack_runtime_service_semantic_match_returns_hybrid_meta() -> None:
    branch_id = uuid4()
    truth = {
        "services_catalog": [
            {
                "name": "Профессиональная чистка зубов",
                "aliases": ["чистка зубов", "профчистка"],
                "tenant_slug": "dental_pack",
                "branch_ids": [str(branch_id)],
            }
        ]
    }
    with _runtime_truth(truth, slug="dental_pack", branch_id=branch_id):
        result = runtime.semantic_service_match("чистка зубов", "dental_pack")

    assert result is not None
    assert result.action == "match"
    assert result.canonical_name == "Профессиональная чистка зубов"
    assert isinstance(result.meta, dict)
    assert result.meta.get("engine") == "pack_query_engine.v2"
    assert result.meta.get("filters", {}).get("tenant_slug") == "dental_pack"
    assert result.meta.get("filters", {}).get("branch_id") == str(branch_id)


def test_pack_runtime_service_get_pack_service_hint_uses_runtime_fallback_when_scope_allows(monkeypatch) -> None:
    truth = {"services_catalog": []}
    monkeypatch.setattr(runtime, "_runtime_get_pack_service_hint", lambda *_args, **_kwargs: "Fallback Service")
    with _runtime_truth(truth, slug="demo_salon"):
        service_hint = runtime.get_pack_service_hint(
            "нужна услуга",
            client_slug="demo_salon",
        )
    assert service_hint == "Fallback Service"
