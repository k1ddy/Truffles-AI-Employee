from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from app.services import demo_salon_knowledge as demo_runtime
from app.services import pack_query_backend_service
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


def test_capability_question_contract_selects_fact_for_hours_scope() -> None:
    contract = runtime.build_capability_question_contract(
        subject_kind="service",
        capability="hours",
        temporal_scope="weekend",
        requested_resolution_mode="referent_followup",
    )

    assert contract.get("contract_resolution_mode") == "policy_fact"
    assert contract.get("tool_action") == "info"
    assert contract.get("info_refs") == ["hours"]
    assert contract.get("referent_key") == "service"
    assert contract.get("prefers_referent") is True
    assert contract.get("requires_referent") is False


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


def test_resolve_master_intent_person_service_query_is_explicit() -> None:
    resolution = runtime.resolve_master_intent(
        message_text="У вас есть специалист по окрашиванию?",
        client_slug="demo_salon",
        service_query="окрашивание",
    )

    assert resolution.explicit is True
    assert resolution.reason == "person_service_signal"
    assert resolution.service_query == "окрашивание"


def test_resolve_master_intent_person_term_without_relation_stays_non_explicit() -> None:
    resolution = runtime.resolve_master_intent(
        message_text="Мастер-класс по окрашиванию будет?",
        client_slug="demo_salon",
        service_query="окрашивание",
    )

    assert resolution.explicit is False
    assert resolution.reason is None
    assert resolution.service_query == "окрашивание"


def test_resolve_master_intent_choose_specialist_with_service_query_is_explicit() -> None:
    resolution = runtime.resolve_master_intent(
        message_text="Могу ли я выбрать специалиста?",
        client_slug="demo_salon",
        service_query="маникюр",
    )

    assert resolution.explicit is True
    assert resolution.reason == "person_action_signal"
    assert resolution.service_query == "маникюр"


def test_resolve_master_intent_generic_specialist_question_with_service_query_is_explicit() -> None:
    resolution = runtime.resolve_master_intent(
        message_text="Есть ли доступные специалисты?",
        client_slug="demo_salon",
        service_query="маникюр",
    )

    assert resolution.explicit is True
    assert resolution.reason == "person_question_signal"
    assert resolution.service_query == "маникюр"


def test_resolve_master_intent_question_with_filler_before_master_is_explicit() -> None:
    resolution = runtime.resolve_master_intent(
        message_text="Какой у вас мастер?",
        client_slug="demo_salon",
        service_query="маникюр",
    )

    assert resolution.explicit is True
    assert resolution.reason == "question_person_signal"
    assert resolution.service_query == "маникюр"


def test_resolve_master_intent_choose_specialist_without_service_query_is_explicit() -> None:
    resolution = runtime.resolve_master_intent(
        message_text="Могу ли я выбрать специалиста?",
        client_slug="demo_salon",
    )

    assert resolution.explicit is True
    assert resolution.reason == "person_action_signal"
    assert resolution.service_query is None
    assert resolution.needs_service_clarify is True


def test_resolve_master_intent_named_master_question_with_service_query_is_explicit() -> None:
    resolution = runtime.resolve_master_intent(
        message_text="Можно к мастеру Айгерим?",
        client_slug="demo_salon",
        service_query="маникюр",
    )

    assert resolution.explicit is True
    assert resolution.reason == "person_named_question_signal"
    assert resolution.service_query == "маникюр"
    assert "Айгерим" in resolution.matched_signals


def test_resolve_master_intent_bare_named_specialist_question_with_service_query_is_explicit() -> None:
    resolution = runtime.resolve_master_intent(
        message_text="Могу ли я записаться к Айгерим?",
        client_slug="demo_salon",
        service_query="маникюр",
    )

    assert resolution.explicit is True
    assert resolution.reason == "named_question_signal"
    assert resolution.service_query == "маникюр"
    assert "Айгерим" in resolution.matched_signals


def test_resolve_master_intent_named_master_booking_command_stays_non_explicit() -> None:
    resolution = runtime.resolve_master_intent(
        message_text="Запишите меня к мастеру Айгерим на маникюр завтра.",
        client_slug="demo_salon",
        service_query="маникюр",
    )

    assert resolution.explicit is False
    assert resolution.reason is None
    assert resolution.service_query == "маникюр"


def test_pack_runtime_service_get_pack_service_hint_uses_runtime_fallback_when_scope_allows(monkeypatch) -> None:
    truth = {"services_catalog": []}
    monkeypatch.setattr(runtime, "_runtime_get_pack_service_hint", lambda *_args, **_kwargs: "Fallback Service")
    with _runtime_truth(truth, slug="demo_salon"):
        service_hint = runtime.get_pack_service_hint(
            "нужна услуга",
            client_slug="demo_salon",
        )
    assert service_hint == "Fallback Service"


def test_pack_runtime_service_backend_shadow_keeps_runtime_local_contract(monkeypatch) -> None:
    pack_query_backend_service.clear_backend_driver_registry()
    monkeypatch.setenv("PACK_QUERY_RETRIEVAL_MODE", "backend_shadow")
    monkeypatch.setenv("PACK_QUERY_BACKEND_DRIVER", "test_shadow")
    pack_query_backend_service.register_backend_driver(
        "test_shadow",
        lambda **_kwargs: {
            "candidates": [
                {
                    "canonical_name": "Профессиональная чистка зубов",
                    "score": 0.99,
                    "dense_score": 0.95,
                    "sparse_score": 0.9,
                }
            ]
        },
    )
    truth = {
        "services_catalog": [
            {
                "name": "Профессиональная чистка зубов",
                "aliases": ["чистка зубов"],
                "tenant_slug": "dental_pack",
            }
        ]
    }
    try:
        with _runtime_truth(truth, slug="dental_pack"):
            result = runtime.semantic_service_match("чистка зубов", "dental_pack")
    finally:
        pack_query_backend_service.clear_backend_driver_registry()

    assert result is not None
    assert result.canonical_name == "Профессиональная чистка зубов"
    assert isinstance(result.meta, dict)
    assert result.meta.get("retrieval_mode") == "backend_shadow"
    assert result.meta.get("selected_source") == "runtime_local"
    assert result.meta.get("backend_candidate_count") == 1
    assert result.meta.get("backend", {}).get("available") is True


def test_pack_runtime_service_backend_primary_prefers_backend_candidates(monkeypatch) -> None:
    pack_query_backend_service.clear_backend_driver_registry()
    monkeypatch.setenv("PACK_QUERY_RETRIEVAL_MODE", "backend_primary")
    monkeypatch.setenv("PACK_QUERY_BACKEND_DRIVER", "test_primary")
    pack_query_backend_service.register_backend_driver(
        "test_primary",
        lambda **_kwargs: {
            "meta": {
                "engine": "pack_query_backend.v1",
                "engine_version": "2026-03-03",
                "method": "distributed_hybrid_rrf",
            },
            "candidates": [
                {
                    "canonical_name": "Лечение кариеса",
                    "score": 0.88,
                    "dense_score": 0.9,
                    "sparse_score": 0.72,
                }
            ],
        },
    )
    truth = {
        "services_catalog": [
            {
                "name": "Профессиональная чистка зубов",
                "aliases": ["чистка зубов"],
                "tenant_slug": "dental_pack",
            },
            {
                "name": "Лечение кариеса",
                "aliases": ["лечение зуба", "кариес лечение"],
                "tenant_slug": "dental_pack",
            },
        ]
    }
    try:
        with _runtime_truth(truth, slug="dental_pack"):
            result = runtime.semantic_service_match("чистка зубов", "dental_pack")
    finally:
        pack_query_backend_service.clear_backend_driver_registry()

    assert result is not None
    assert result.canonical_name == "Лечение кариеса"
    assert isinstance(result.meta, dict)
    assert result.meta.get("retrieval_mode") == "backend_primary"
    assert result.meta.get("selected_source") == "backend_primary"
    assert result.meta.get("backend", {}).get("available") is True


def test_pack_runtime_service_backend_primary_fallback_is_explicit(monkeypatch) -> None:
    pack_query_backend_service.clear_backend_driver_registry()
    monkeypatch.setenv("PACK_QUERY_RETRIEVAL_MODE", "backend_primary")
    monkeypatch.setenv("PACK_QUERY_BACKEND_DRIVER", "missing_driver")
    truth = {
        "services_catalog": [
            {
                "name": "Профессиональная чистка зубов",
                "aliases": ["чистка зубов"],
                "tenant_slug": "dental_pack",
            }
        ]
    }
    with _runtime_truth(truth, slug="dental_pack"):
        result = runtime.semantic_service_match("чистка зубов", "dental_pack")

    assert result is not None
    assert result.canonical_name == "Профессиональная чистка зубов"
    assert isinstance(result.meta, dict)
    assert result.meta.get("retrieval_mode") == "backend_primary"
    assert result.meta.get("selected_source") == "runtime_local_fallback"
    assert result.meta.get("fallback_reason") == "backend_unavailable"
    assert result.meta.get("backend", {}).get("available") is False


def test_pack_runtime_service_backend_primary_filters_out_of_scope_backend_candidates(monkeypatch) -> None:
    pack_query_backend_service.clear_backend_driver_registry()
    monkeypatch.setenv("PACK_QUERY_RETRIEVAL_MODE", "backend_primary")
    monkeypatch.setenv("PACK_QUERY_BACKEND_DRIVER", "scope_driver")
    pack_query_backend_service.register_backend_driver(
        "scope_driver",
        lambda **_kwargs: {
            "candidates": [
                {
                    "canonical_name": "Сервис вне каталога",
                    "score": 0.97,
                    "dense_score": 0.97,
                }
            ]
        },
    )
    truth = {
        "services_catalog": [
            {
                "name": "Профессиональная чистка зубов",
                "aliases": ["чистка зубов"],
                "tenant_slug": "dental_pack",
            }
        ]
    }
    try:
        with _runtime_truth(truth, slug="dental_pack"):
            result = runtime.semantic_service_match("чистка зубов", "dental_pack")
    finally:
        pack_query_backend_service.clear_backend_driver_registry()

    assert result is not None
    assert result.canonical_name == "Профессиональная чистка зубов"
    assert isinstance(result.meta, dict)
    assert result.meta.get("selected_source") == "runtime_local_fallback"
    assert result.meta.get("fallback_reason") == "backend_scope_filtered"
