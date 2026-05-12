#!/usr/bin/env python3
"""Standalone dry-run of the Policy-Core v3 shadow path.

Runs without DB, without real LLM, without consultant_runtime. Loads the
example pack at `packs/beauty_salon_v1/`, fabricates one customer turn,
invokes the shadow runner with a mock LLM, and prints the resulting
ComparisonRecord as JSON to stdout.

Usage:
    python3 scripts/policy_core_v3_shadow_dryrun.py
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import sys
from datetime import datetime, timezone


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "truffles-api"))


# Imports must come after sys.path adjustment.
from app.pack_v1 import load_pack  # noqa: E402
from app.policy_core_v3 import (  # noqa: E402
    EvidenceItem,
    PolicyCoreV3Invoker,
    Turn,
)
from app.policy_core_v3_shadow import (  # noqa: E402
    InMemoryArtifactSink,
    LegacySummary,
    LegacyTurnContext,
    run_shadow,
)


async def _mock_llm(prompt: str) -> str:
    """Mock LLM that always returns a valid v3 decision JSON.

    Picked one realistic shape: model classifies the turn as a booking
    request, drafts a slot-collect follow-up, and cites the datetime
    evidence. This is a static stub — no inference happens here.
    """
    decision = {
        "intent": "booking_request",
        "slots": {
            "service_id": "brows",
            "datetime": "2026-05-12T18:00:00+05:00",
            "customer_name": None,
            "customer_phone": None,
        },
        "candidate_action": {"tool": "none", "args": {}},
        "evidence_refs": ["ev-1", "ev-2"],
        "message_draft": "Записываю на брови завтра в 18:00. Подскажите ваше имя?",
        "uncertainty": "low",
        "notes": "dry-run mock",
    }
    return json.dumps(decision, ensure_ascii=False)


async def main() -> int:
    pack = load_pack(REPO_ROOT / "packs" / "beauty_salon_v1")

    ctx = LegacyTurnContext(
        tenant_id="dryrun-tenant",
        conversation_id="dryrun-conv-1",
        current_message="можно завтра в 6 вечера на брови",
        pack=pack,
        now=datetime.now(timezone.utc),
        history=[
            Turn(role="customer", text="привет"),
            Turn(role="bot", text="Здравствуйте! Чем могу помочь?"),
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
            EvidenceItem(
                id="ev-2",
                source="datetime_parser",
                kind="datetime_candidate",
                payload={
                    "iso": "2026-05-12T18:00:00+05:00",
                    "raw": "завтра в 6 вечера",
                },
                confidence=0.9,
            ),
        ],
        policy_version="v3-shadow-dryrun",
    )

    legacy_summary = LegacySummary(
        intent="booking_request",
        action="collect",
        tool_action="calendar.list_slots",
        message_text="Записываю на брови. Скажите, пожалуйста, ваше имя.",
        rescue_flag=False,
        policy_core_degrade=False,
    )

    sink = InMemoryArtifactSink()
    invoker = PolicyCoreV3Invoker(_mock_llm)

    record = await run_shadow(
        ctx=ctx,
        legacy_summary=legacy_summary,
        invoker=invoker,
        sink=sink,
        turn_index=2,
        notes="dry-run on packs/beauty_salon_v1 with mock LLM",
    )

    payload = record.model_dump(mode="json")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))

    assert sink.records and sink.records[0] is record
    assert record.v3_outcome_kind == "decision"
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
