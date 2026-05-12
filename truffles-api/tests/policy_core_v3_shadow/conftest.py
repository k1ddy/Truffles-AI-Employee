"""Shared fixtures for shadow-run tests.

No DB, no real LLM, no consultant_runtime imports.
"""
from __future__ import annotations

import pathlib
from datetime import datetime, timezone

import pytest

from app.pack_v1 import PackV1, load_pack
from app.policy_core_v3 import EvidenceItem, Turn
from app.policy_core_v3_shadow import LegacySummary, LegacyTurnContext


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
EXAMPLE_PACK = REPO_ROOT / "packs" / "beauty_salon_v1"


@pytest.fixture
def example_pack() -> PackV1:
    return load_pack(EXAMPLE_PACK)


@pytest.fixture
def legacy_ctx(example_pack: PackV1) -> LegacyTurnContext:
    return LegacyTurnContext(
        tenant_id="t-test",
        conversation_id="c-test",
        current_message="можно завтра в 6 вечера на брови",
        pack=example_pack,
        now=datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc),
        history=[
            Turn(role="customer", text="привет"),
            Turn(role="bot", text="Здравствуйте."),
        ],
        state_slots={"customer_name": None, "customer_phone": None},
        evidence_bundle=[
            EvidenceItem(
                id="ev-1",
                source="lexicon",
                kind="service_alias",
                payload={"alias": "брови", "service_id": "brows"},
                confidence=0.95,
            ),
        ],
    )


@pytest.fixture
def legacy_summary() -> LegacySummary:
    return LegacySummary(
        intent="booking_request",
        action="collect",
        tool_action="calendar.list_slots",
        message_text="Скажите, пожалуйста, ваше имя.",
        rescue_flag=False,
        policy_core_degrade=False,
    )
