from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.services import demo_salon_knowledge as demo_runtime
from app.services import pack_query_backend_service
from app.services import pack_runtime_compat as compat_runtime
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


def test_pack_runtime_service_routes_helper_surface_through_selected_adapter() -> None:
    assert not hasattr(runtime, "get_pack_decision")
    assert not hasattr(default_runtime, "get_pack_decision")
    assert hasattr(compat_runtime, "get_pack_decision")
    assert not hasattr(runtime, "get_pack_service_decision")
    assert not hasattr(default_runtime, "get_pack_service_decision")
    assert hasattr(compat_runtime, "get_pack_service_decision")
    assert not hasattr(runtime, "get_pack_adapter")
    assert runtime.get_pack_runtime("demo_salon").client_slug == "demo_salon"

    combined_args = {"include_parking": True, "client_slug": "demo_salon"}
    assert runtime.build_info_combined_reply(**combined_args) == default_runtime.build_info_combined_reply(
        **combined_args
    )
    assert runtime.format_reply_from_truth("hours", client_slug="demo_salon") == default_runtime.format_reply_from_truth(
        "hours",
        client_slug="demo_salon",
    )
    assert runtime.format_reply_from_truth(
        "promotions",
        client_slug="demo_salon",
    ) == default_runtime.format_reply_from_truth(
        "promotions",
        client_slug="demo_salon",
    )
    now_utc = datetime(2026, 4, 1, 20, 0, 0, tzinfo=timezone.utc)
    assert runtime.build_quiet_hours_notice(
        client_slug="demo_salon",
        now_utc=now_utc,
    ) == default_runtime.build_quiet_hours_notice(
        client_slug="demo_salon",
        now_utc=now_utc,
    )
    assert runtime.build_evening_greeting(
        client_slug="demo_salon",
        now_utc=now_utc,
    ) == default_runtime.build_evening_greeting(
        client_slug="demo_salon",
        now_utc=now_utc,
    )


def test_pack_runtime_boundary_binds_selected_helper_surface() -> None:
    pack_runtime = runtime.get_pack_runtime("demo_salon")

    reply, meta = pack_runtime.build_info_combined_reply(include_parking=True)
    expected_reply, expected_meta = default_runtime.build_info_combined_reply(
        include_parking=True,
        client_slug="demo_salon",
    )

    assert (reply, meta) == (expected_reply, expected_meta)
    assert pack_runtime.format_reply_from_truth("hours") == default_runtime.format_reply_from_truth(
        "hours",
        client_slug="demo_salon",
    )


def test_get_pack_decision_enriches_resolver_contract() -> None:
    decision = compat_runtime.get_pack_decision("Сколько стоит маникюр?", client_slug="demo_salon")

    assert isinstance(decision, PackDecision)
    meta = decision.meta or {}
    assert meta.get("resolver_id") == "pack_runtime.truth_gate"
    assert meta.get("resolver_version")
    assert meta.get("intent_class") == "price_query"
    assert meta.get("action_class") == "FACT"
    assert meta.get("resolver_confidence") and meta.get("resolver_confidence") >= 0.56
    assert isinstance(meta.get("resolver_candidates"), list) and meta.get("resolver_candidates")
    assert isinstance(meta.get("resolver_contract"), dict)
    assert meta.get("resolver_contract", {}).get("entity_refs") == meta.get("entity_refs")
    assert meta.get("resolver_candidates") == meta.get("entity_refs")
    entity_refs = meta.get("entity_refs")
    assert entity_refs == meta.get("semantic_grounding", {}).get("entity_refs")
    assert entity_refs[0]["entity_type"] == "service"
    assert entity_refs[0]["value"] == "Маникюр"
    assert str(entity_refs[0]["entity_id"]).startswith("service:")
    assert any(row.get("entity_type") == "price_item" for row in entity_refs)
    assert meta.get("referents") == {
        "service": {
            "value": "Маникюр",
            "entity_id": entity_refs[0]["entity_id"],
            "entity_type": "service",
            "source_ref": meta.get("service_query_source"),
        }
    }
    semantic_grounding = meta.get("semantic_grounding")
    assert isinstance(semantic_grounding, dict)
    assert semantic_grounding.get("contract_version") == "semantic_contract.v1"
    assert semantic_grounding.get("entity_refs") == meta.get("entity_refs")
    assert semantic_grounding.get("referents") == meta.get("referents")
    fact_bundle = meta.get("fact_bundle")
    assert isinstance(fact_bundle, dict)
    assert fact_bundle.get("pack_id") == "demo_salon"
    assert fact_bundle.get("source_ref") == "truth"
    assert meta.get("grounding_provenance", {}).get("pack_id") == "demo_salon"
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
        "_adapter_service_decision",
        lambda *_args, **_kwargs: base_decision,
    )

    decision = compat_runtime.get_pack_service_decision("Классический интересует", client_slug="demo_salon")

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
            "intent_class": "service_match",
            "action_class": "FACT",
            "resolver_confidence": 0.9,
            "abstain_reason": None,
        },
    )
    assert runtime.has_consult_recommendation_signal(decision) is True


def test_is_timeout_fact_fallback_candidate_requires_fact_confidence_margin() -> None:
    fact_decision = PackDecision(
        action="reply",
        response="Салон работает с 9:00 до 21:00.",
        intent="hours",
        meta={
            "intent_class": "hours",
            "action_class": "FACT",
            "resolver_confidence": 0.83,
            "abstain_reason": None,
        },
    )
    assert runtime.is_timeout_fact_fallback_candidate(fact_decision, min_confidence=0.6) is True

    abstain_decision = PackDecision(
        action="reply",
        response="Нужно уточнение.",
        intent="hours",
        meta={
            "intent_class": "hours",
            "action_class": "FACT",
            "resolver_confidence": 0.91,
            "abstain_reason": "low_confidence_collect",
        },
    )
    assert runtime.is_timeout_fact_fallback_candidate(abstain_decision, min_confidence=0.6) is False

    low_conf_decision = PackDecision(
        action="reply",
        response="Возможно, это по прайсу.",
        intent="pricing",
        meta={
            "intent_class": "pricing",
            "action_class": "FACT",
            "resolver_confidence": 0.41,
            "abstain_reason": None,
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


def test_pack_runtime_service_hint_can_fallback_to_price_catalog_name() -> None:
    assert compat_runtime.get_pack_service_hint(
        "Сколько времени занимает укладка?",
        client_slug="demo_salon",
    ) == "Укладка феном"


def test_build_runtime_service_duration_reply_requires_explicit_service_label() -> None:
    reply = runtime.build_runtime_service_duration_reply(
        message="Сколько времени занимает укладка?",
        service_label="Маникюр",
        client_slug="demo_salon",
    )

    assert isinstance(reply, str)
    assert "маникюр" in reply.lower()
    assert "укладка" not in reply.lower()


def test_build_runtime_service_duration_reply_keeps_exact_price_item_without_reclarify() -> None:
    truth = {
        "services_catalog": {
            "services": [
                {
                    "name": "Стрижка",
                    "aliases": ["стрижка"],
                    "duration_text": "Обычно 20–60 минут.",
                }
            ],
            "duration_clarify": "По времени зависит от услуги. Какая именно?",
        },
        "price_list": [
            {
                "category": "Парикмахерский зал",
                "items": [{"name": "Укладка феном", "price": 3500}],
            }
        ],
        "team": {
            "hair": "Колористы 5+ лет, делают блонд, балаяж и другие сложные окрашивания."
        },
    }
    with _runtime_truth(truth, slug="demo_salon"):
        reply = runtime.build_runtime_service_duration_reply(
            message="Сколько времени занимает укладка?",
            service_label="укладка",
            client_slug="demo_salon",
        )

    assert reply == "Укладка феном — точная длительность зависит от объема и сложности."


def test_resolve_runtime_service_price_item_resolves_exact_price_item_name() -> None:
    truth = {
        "services_catalog": {
            "services": [
                {
                    "name": "Маникюр",
                    "aliases": ["маникюр"],
                    "price_items": ["Маникюр классический"],
                }
            ]
        },
        "price_list": [
            {
                "category": "Маникюр",
                "items": [{"name": "Маникюр классический", "price": 2500}],
            }
        ],
    }
    with _runtime_truth(truth, slug="demo_salon"):
        price_item = runtime.resolve_runtime_service_price_item(
            "Маникюр классический",
            client_slug="demo_salon",
        )

    assert isinstance(price_item, dict)
    assert price_item.get("name") == "Маникюр классический"


def test_build_master_reply_from_pack_uses_team_summary_when_profiles_are_unavailable() -> None:
    truth = {
        "services_catalog": {
            "services": [
                {
                    "name": "Маникюр",
                    "aliases": ["маникюр"],
                    "price_items": ["Маникюр классический"],
                    "duration_text": "Обычно 45–90 минут.",
                }
            ],
            "duration_clarify": "По времени зависит от услуги. Какая именно?",
        },
        "price_list": [
            {
                "category": "Парикмахерский зал",
                "items": [{"name": "Укладка феном", "price": 3500}],
            }
        ],
        "team": {
            "hair": "Колористы 5+ лет, делают блонд, балаяж и другие сложные окрашивания."
        },
    }
    with _runtime_truth(truth, slug="demo_salon"):
        resolution = compat_runtime.resolve_master_intent(
            message_text="Кто делает укладку?",
            client_slug="demo_salon",
            service_query="укладка",
            force_master_intent=True,
        )
        reply = runtime.build_master_reply_from_pack(
            client_slug="demo_salon",
            message_text="Кто делает укладку?",
            resolution=resolution,
        )

    assert reply is not None
    assert reply.action == "reply"
    assert reply.intent == "master"
    assert reply.meta.get("master_query_contract") == "team.v1"
    assert reply.meta.get("master_reply_mode") == "team_match"
    assert reply.meta.get("master_team_key") == "hair"
    assert "Укладка феном" in (reply.response or "")
    assert "администратор" not in (reply.response or "").casefold()


def test_build_master_reply_from_pack_does_not_ground_service_from_message_text() -> None:
    reply = runtime.build_master_reply_from_pack(
        client_slug="demo_salon",
        message_text="Кто делает укладку?",
        resolution=runtime.MasterIntentResolution(
            explicit=True,
            service_query=None,
            service_query_source="none",
            needs_service_clarify=True,
            reason="forced_master_intent",
            matched_signals=[],
        ),
    )

    assert reply is not None
    assert reply.action == "collect"
    assert reply.intent == "master"
    assert reply.meta.get("master_reply_mode") == "service_clarify"
    assert reply.meta.get("service_query") is None


def test_resolve_explicit_master_intent_uses_explicit_service_query_only() -> None:
    resolution = runtime.resolve_explicit_master_intent(
        client_slug="demo_salon",
        service_query="Маникюр",
        force_master_intent=False,
    )

    assert resolution.explicit is True
    assert resolution.service_query == "Маникюр"
    assert resolution.service_query_source == "input"
    assert resolution.reason == "explicit_service_query"


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
        result = compat_runtime.semantic_service_match("чистка зубов", "dental_pack")

    assert result is not None
    assert result.action == "match"
    assert result.canonical_name == "Профессиональная чистка зубов"
    assert isinstance(result.meta, dict)
    assert result.meta.get("engine") == "pack_query_engine.v2"
    assert result.meta.get("filters", {}).get("tenant_slug") == "dental_pack"
    assert result.meta.get("filters", {}).get("branch_id") == str(branch_id)


def test_resolve_master_intent_person_service_query_is_explicit() -> None:
    resolution = compat_runtime.resolve_master_intent(
        message_text="У вас есть специалист по окрашиванию?",
        client_slug="demo_salon",
        service_query="окрашивание",
    )

    assert resolution.explicit is True
    assert resolution.reason == "person_service_signal"
    assert resolution.service_query == "окрашивание"


def test_resolve_master_intent_person_term_without_relation_stays_non_explicit() -> None:
    resolution = compat_runtime.resolve_master_intent(
        message_text="Мастер-класс по окрашиванию будет?",
        client_slug="demo_salon",
        service_query="окрашивание",
    )

    assert resolution.explicit is False
    assert resolution.reason is None
    assert resolution.service_query == "окрашивание"


def test_resolve_master_intent_choose_specialist_with_service_query_is_explicit() -> None:
    resolution = compat_runtime.resolve_master_intent(
        message_text="Могу ли я выбрать специалиста?",
        client_slug="demo_salon",
        service_query="маникюр",
    )

    assert resolution.explicit is True
    assert resolution.reason == "person_action_signal"
    assert resolution.service_query == "маникюр"


def test_resolve_master_intent_generic_specialist_question_with_service_query_is_explicit() -> None:
    resolution = compat_runtime.resolve_master_intent(
        message_text="Есть ли доступные специалисты?",
        client_slug="demo_salon",
        service_query="маникюр",
    )

    assert resolution.explicit is True
    assert resolution.reason == "person_question_signal"
    assert resolution.service_query == "маникюр"


def test_resolve_master_intent_question_with_filler_before_master_is_explicit() -> None:
    resolution = compat_runtime.resolve_master_intent(
        message_text="Какой у вас мастер?",
        client_slug="demo_salon",
        service_query="маникюр",
    )

    assert resolution.explicit is True
    assert resolution.reason == "question_person_signal"
    assert resolution.service_query == "маникюр"


def test_resolve_master_intent_choose_specialist_without_service_query_is_explicit() -> None:
    resolution = compat_runtime.resolve_master_intent(
        message_text="Могу ли я выбрать специалиста?",
        client_slug="demo_salon",
    )

    assert resolution.explicit is True
    assert resolution.reason == "person_action_signal"
    assert resolution.service_query is None
    assert resolution.needs_service_clarify is True


def test_resolve_master_intent_named_master_question_with_service_query_is_explicit() -> None:
    resolution = compat_runtime.resolve_master_intent(
        message_text="Можно к мастеру Айгерим?",
        client_slug="demo_salon",
        service_query="маникюр",
    )

    assert resolution.explicit is True
    assert resolution.reason == "person_named_question_signal"
    assert resolution.service_query == "маникюр"
    assert "Айгерим" in resolution.matched_signals


def test_resolve_master_intent_bare_named_specialist_question_with_service_query_is_explicit() -> None:
    resolution = compat_runtime.resolve_master_intent(
        message_text="Могу ли я записаться к Айгерим?",
        client_slug="demo_salon",
        service_query="маникюр",
    )

    assert resolution.explicit is True
    assert resolution.reason == "named_question_signal"
    assert resolution.service_query == "маникюр"
    assert "Айгерим" in resolution.matched_signals


def test_resolve_master_intent_named_master_booking_command_stays_non_explicit() -> None:
    resolution = compat_runtime.resolve_master_intent(
        message_text="Запишите меня к мастеру Айгерим на маникюр завтра.",
        client_slug="demo_salon",
        service_query="маникюр",
    )

    assert resolution.explicit is False
    assert resolution.reason is None
    assert resolution.service_query == "маникюр"


def test_resolve_master_intent_pack_query_hint_uses_neutral_source_label(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime,
        "_resolve_pack_query_service_hint",
        lambda *_args, **_kwargs: "укладка",
    )

    resolution = compat_runtime.resolve_master_intent(
        message_text="Кто делает это?",
        client_slug="demo_salon",
        force_master_intent=True,
    )

    assert resolution.service_query == "укладка"
    assert resolution.service_query_source == "pack_query_hint"
    assert resolution.reason == "forced_master_intent"


def test_pack_runtime_service_get_pack_service_hint_uses_runtime_fallback_when_scope_allows(monkeypatch) -> None:
    truth = {"services_catalog": []}
    monkeypatch.setattr(runtime, "_adapter_service_hint", lambda *_args, **_kwargs: "Fallback Service")
    with _runtime_truth(truth, slug="demo_salon"):
        service_hint = compat_runtime.get_pack_service_hint(
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
            result = compat_runtime.semantic_service_match("чистка зубов", "dental_pack")
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
            result = compat_runtime.semantic_service_match("чистка зубов", "dental_pack")
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
        result = compat_runtime.semantic_service_match("чистка зубов", "dental_pack")

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
            result = compat_runtime.semantic_service_match("чистка зубов", "dental_pack")
    finally:
        pack_query_backend_service.clear_backend_driver_registry()

    assert result is not None
    assert result.canonical_name == "Профессиональная чистка зубов"
    assert isinstance(result.meta, dict)
    assert result.meta.get("selected_source") == "runtime_local_fallback"
    assert result.meta.get("fallback_reason") == "backend_scope_filtered"
