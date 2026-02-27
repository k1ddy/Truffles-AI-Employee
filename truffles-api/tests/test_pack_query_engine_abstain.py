from app.services import pack_runtime_service as runtime
from app.services.pack_runtime_types import PackDecision


def test_pack_query_engine_abstain_collect_uses_reason_signal():
    meta = runtime.ensure_resolver_meta(
        {
            "clarify_reason": "missing_service_query",
            "service_query": "",
        },
        action="booking_prompt",
        intent="service_clarify",
        resolver_id="pack_query_engine",
        client_slug="demo_salon",
    )

    contract = meta.get("resolver_contract")
    assert isinstance(contract, dict)
    assert contract.get("action_class") == "COLLECT"
    assert contract.get("abstain_reason") == "missing_service_query"


def test_pack_query_engine_abstain_margin_blocks_low_confidence_fact_fallback():
    decision = PackDecision(
        action="reply",
        response="Возможно, это по прайсу.",
        intent="pricing",
        meta={
            "resolver_contract": {
                "intent_class": "pricing",
                "action_class": "FACT",
                "confidence": 0.55,
                "abstain_reason": None,
            }
        },
    )

    assert runtime.is_timeout_fact_fallback_candidate(decision, min_confidence=0.6) is False
    assert runtime.is_timeout_fact_fallback_candidate(decision, min_confidence=0.5) is True


def test_pack_query_engine_abstain_reason_disables_fact_timeout_fallback():
    decision = PackDecision(
        action="reply",
        response="Нужно уточнить услугу.",
        intent="service_clarify",
        meta={
            "resolver_contract": {
                "intent_class": "service_clarify",
                "action_class": "FACT",
                "confidence": 0.95,
                "abstain_reason": "low_confidence_collect",
            }
        },
    )

    assert runtime.is_timeout_fact_fallback_candidate(decision, min_confidence=0.6) is False
