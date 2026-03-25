from contextlib import contextmanager
from uuid import uuid4

from app.services import pack_runtime_service as runtime
from app.services.knowledge_runtime import RuntimeTruth, set_runtime_truth
from app.services.pack_runtime_types import PackDecision


@contextmanager
def _runtime_truth(payload: dict, *, slug: str, branch_id=None):
    runtime_payload = RuntimeTruth(
        truth=payload,
        client_slug=slug,
        branch_id=branch_id,
        source="test_pack_query_engine_abstain",
        allow_fallback=False,
    )
    set_runtime_truth(runtime_payload)
    try:
        yield
    finally:
        set_runtime_truth(None)


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


def test_pack_query_engine_abstain_strict_branch_filter_blocks_fallback():
    branch_id = uuid4()
    truth = {
        "services_catalog": [
            {
                "name": "Маникюр",
                "aliases": ["маникюр", "ногти"],
                "tenant_slug": "demo_salon",
                "branch_ids": [str(uuid4())],
            }
        ]
    }

    with _runtime_truth(truth, slug="demo_salon", branch_id=branch_id):
        match = runtime.semantic_service_match("маникюр", "demo_salon")
        hint = runtime.get_pack_service_hint("маникюр", client_slug="demo_salon")

    assert match is None
    assert hint is None


def test_pack_query_engine_abstain_tenant_filter_blocks_cross_slug_resolution():
    truth = {
        "services_catalog": [
            {
                "name": "Профессиональная чистка зубов",
                "aliases": ["чистка зубов", "профчистка"],
                "tenant_slug": "dental_pack",
            }
        ]
    }

    with _runtime_truth(truth, slug="clinic_pack"):
        match = runtime.semantic_service_match("чистка зубов", "clinic_pack")
        hint = runtime.get_pack_service_hint("чистка зубов", client_slug="clinic_pack")

    assert match is None
    assert hint is None


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
