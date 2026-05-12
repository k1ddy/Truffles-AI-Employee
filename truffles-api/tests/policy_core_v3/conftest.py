"""Shared fixtures for policy_core_v3 unit tests.

The fixtures here keep tests independent of runtime, DB, or pack adapters.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.policy_core_v3 import (
    EvidenceItem,
    PackRules,
    PolicyTurnInput,
    ServiceView,
    SpecialistView,
    ToolContract,
    Turn,
)
from app.policy_core_v3.pack_view import StaticPackView


@pytest.fixture
def sample_pack() -> StaticPackView:
    return StaticPackView(
        pack_id="beauty_salon_v1",
        services=[
            ServiceView(
                id="brows",
                name="Оформление бровей",
                aliases=("брови", "бровки"),
                duration_min=30,
                price="5000 KZT",
            ),
            ServiceView(
                id="manicure",
                name="Маникюр",
                aliases=("маник",),
                duration_min=60,
                price="8000 KZT",
            ),
        ],
        specialists=[
            SpecialistView(id="anna", name="Анна", service_ids=("brows", "manicure")),
        ],
        rules=PackRules(
            bot_can_confirm=False,
            required_for_booking=("service", "datetime", "name", "phone"),
            identity_for_lookup=("name_or_phone",),
            escalate_topics=("medical", "refund", "complaint"),
        ),
        business_summary="Салон красоты Demo на Абая 1, открыт 10–20.",
    )


@pytest.fixture
def sample_tools() -> list[ToolContract]:
    return [
        ToolContract(
            id="calendar.book_slot",
            description="Create a pending appointment.",
            args_schema={
                "service_query": "text",
                "start_at": "datetime",
                "customer_name": "text",
                "customer_phone": "text",
            },
        ),
        ToolContract(
            id="calendar.get_booking",
            description="Look up an existing appointment by identity.",
            args_schema={
                "service_query": "text",
                "customer_name": "text",
                "customer_phone": "text",
                "lookup_datetime": "datetime",
            },
        ),
        ToolContract(
            id="handoff.create",
            description="Escalate the conversation to a human admin.",
            args_schema={"reason": "text"},
        ),
    ]


@pytest.fixture
def sample_input(sample_pack, sample_tools) -> PolicyTurnInput:
    return PolicyTurnInput(
        tenant_id="tenant-1",
        conversation_id="conv-1",
        current_message="можно завтра в 6 вечера на брови",
        conversation_history=[
            Turn(role="customer", text="привет"),
            Turn(role="bot", text="Здравствуйте! Чем могу помочь?"),
        ],
        state_slots={"customer_name": None, "customer_phone": None},
        pack_view=sample_pack,
        capabilities=["FACT", "COLLECT", "BOOKING", "MANAGE", "HANDOFF"],
        tool_contracts=sample_tools,
        evidence_bundle=[
            EvidenceItem(
                id="ev-1",
                source="lexicon",
                kind="service_alias",
                payload={"alias": "брови", "service_id": "brows"},
                confidence=0.95,
            ),
            EvidenceItem(
                id="ev-2",
                source="datetime_parser",
                kind="datetime_candidate",
                payload={"iso": "2026-05-12T18:00:00+05:00", "raw": "завтра в 6 вечера"},
                confidence=0.9,
            ),
        ],
        now=datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc),
        locale="ru-KZ",
        policy_version="v3-poc-test",
    )
