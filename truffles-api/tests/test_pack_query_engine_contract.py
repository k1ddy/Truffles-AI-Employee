from app.services import pack_runtime_service as runtime
from app.services.pack_runtime_types import PackDecision


def test_pack_query_engine_contract_emits_fact_bundle_and_provenance():
    meta = runtime.ensure_resolver_meta(
        {
            "fact_source": "truth:hours",
            "service_query": "Маникюр",
            "service_query_source": "semantic_match",
            "service_query_score": 0.91,
            "info_sections": ["hours"],
        },
        action="reply",
        intent="hours",
        resolver_id="pack_query_engine",
        client_slug="demo_salon",
    )

    contract = meta.get("resolver_contract")
    assert isinstance(contract, dict)
    assert contract.get("resolver_id") == "pack_query_engine"
    assert contract.get("action_class") == "FACT"
    assert contract.get("intent_class") == "hours"
    assert contract.get("confidence") == 0.91

    fact_bundle = meta.get("fact_bundle")
    assert isinstance(fact_bundle, dict)
    assert fact_bundle.get("pack_id") == "demo_salon"
    assert fact_bundle.get("source_ref") == "truth:hours"
    assert fact_bundle.get("action_class") == "FACT"

    provenance = meta.get("provenance")
    assert isinstance(provenance, dict)
    assert provenance.get("pack_id") == "demo_salon"
    assert provenance.get("source_ref") == "truth:hours"


def test_pack_query_engine_contract_collects_for_service_not_found_intent():
    meta = runtime.ensure_resolver_meta(
        {
            "service_query": "Что-то непонятное",
            "service_query_source": "intent_decomp",
            "clarify_reason": "missing_service_query",
        },
        action="reply",
        intent="service_not_found",
        resolver_id="pack_query_engine",
        client_slug="demo_salon",
    )

    contract = meta.get("resolver_contract")
    assert isinstance(contract, dict)
    assert contract.get("action_class") == "COLLECT"
    assert isinstance(contract.get("abstain_reason"), str)
    assert contract.get("abstain_reason")


def test_pack_query_engine_enrich_keeps_response_and_embeds_contract():
    base = PackDecision(
        action="reply",
        response="Салон работает с 9:00 до 21:00.",
        intent="hours",
        meta={"fact_source": "truth:hours"},
    )

    enriched = runtime.enrich_pack_decision(
        base,
        resolver_id="pack_query_engine",
        resolver_version="2026-02-25",
        client_slug="demo_salon",
    )

    assert isinstance(enriched, PackDecision)
    assert enriched.response == base.response
    assert enriched.intent == base.intent
    assert enriched.meta.get("resolver_contract_version") == "v1"
    assert enriched.meta.get("resolver_contract", {}).get("resolver_version") == "2026-02-25"
