from contextlib import contextmanager
from uuid import uuid4

import pytest

from app.services import booking_signal_service, info_signal_service, pack_runtime_service, tool_registry_service
from app.services.knowledge_runtime import RuntimeTruth, set_runtime_truth

PACK_CASES = (
    {
        "slug": "clinic_pack",
        "service_query": "Сколько стоит УЗИ брюшной полости?",
        "expected_service": "УЗИ брюшной полости",
        "overview_positive": "Какие обследования у вас есть?",
        "overview_negative": "Какие процедуры для зубов доступны?",
        "portfolio_prompt": "Покажите примеры работ, пожалуйста",
        "instagram": "https://instagram.com/clinic_pack",
        "truth": {
            "salon": {"instagram": "https://instagram.com/clinic_pack"},
            "services_catalog": [
                {
                    "name": "УЗИ брюшной полости",
                    "price": "15000 тг",
                    "duration": "30 мин",
                }
            ],
            "client_pack": {
                "signals": {
                    "services_overview_phrases": [
                        "какие обследования",
                        "перечень обследований",
                    ]
                }
            },
        },
    },
    {
        "slug": "dental_pack",
        "service_query": "Сколько стоит профессиональная чистка зубов?",
        "expected_service": "Профессиональная чистка зубов",
        "overview_positive": "Какие процедуры для зубов доступны?",
        "overview_negative": "Какие обследования у вас есть?",
        "portfolio_prompt": "Есть фото результатов?",
        "instagram": "https://instagram.com/dental_pack",
        "truth": {
            "salon": {"instagram": "https://instagram.com/dental_pack"},
            "services_catalog": [
                {
                    "name": "Профессиональная чистка зубов",
                    "price": "22000 тг",
                    "duration": "45 мин",
                }
            ],
            "client_pack": {
                "signals": {
                    "services_overview_phrases": [
                        "какие процедуры для зубов",
                        "что по лечению зубов",
                    ]
                }
            },
        },
    },
)


@contextmanager
def _runtime_truth(case):
    payload = RuntimeTruth(
        truth=case["truth"],
        client_slug=case["slug"],
        branch_id=uuid4(),
        source="cross_domain_contract_suite",
        allow_fallback=False,
    )
    set_runtime_truth(payload)
    try:
        yield
    finally:
        set_runtime_truth(None)


@pytest.mark.parametrize("case", PACK_CASES, ids=[item["slug"] for item in PACK_CASES])
def test_cross_domain_contract_suite_info_booking_tool_registry(case):
    with _runtime_truth(case):
        assert info_signal_service.looks_like_services_overview_message(
            case["overview_positive"],
            client_slug=case["slug"],
        )
        assert not info_signal_service.looks_like_services_overview_message(
            case["overview_negative"],
            client_slug=case["slug"],
        )

        assert (
            pack_runtime_service.get_pack_service_hint(
                case["service_query"],
                client_slug=case["slug"],
            )
            == case["expected_service"]
        )

        assert booking_signal_service.extract_time_token("Можно на 14:30?") == "14:30"
        assert booking_signal_service.has_duration_context_marker("сколько длится процедура")

        reply, error = tool_registry_service._catalog_portfolio(
            case["slug"],
            message_text=case["portfolio_prompt"],
        )
        assert error is None
        assert isinstance(reply, str)
        assert case["instagram"] in reply
