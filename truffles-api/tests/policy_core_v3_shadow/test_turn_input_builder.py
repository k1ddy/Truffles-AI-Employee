"""turn_input_builder purity & content tests."""
from __future__ import annotations

from app.policy_core_v3_shadow import to_policy_turn_input


def test_builder_is_pure(legacy_ctx) -> None:
    a = to_policy_turn_input(legacy_ctx)
    b = to_policy_turn_input(legacy_ctx)
    assert a.model_dump(mode="json") == b.model_dump(mode="json")


def test_builder_carries_pack_view_and_capabilities(legacy_ctx) -> None:
    out = to_policy_turn_input(legacy_ctx)
    assert out.pack_view.pack_id == legacy_ctx.pack.pack_id
    assert {s.id for s in out.pack_view.services} == {
        s.id for s in legacy_ctx.pack.services
    }
    assert set(out.capabilities) == set(legacy_ctx.pack.capabilities)


def test_builder_locale_falls_back_to_pack(legacy_ctx) -> None:
    out = to_policy_turn_input(legacy_ctx)
    assert out.locale == legacy_ctx.pack.locale


def test_builder_history_and_evidence_pass_through(legacy_ctx) -> None:
    out = to_policy_turn_input(legacy_ctx)
    assert len(out.conversation_history) == len(legacy_ctx.history)
    assert len(out.evidence_bundle) == len(legacy_ctx.evidence_bundle)
    assert out.evidence_bundle[0].id == "ev-1"


def test_builder_does_not_mutate_input(legacy_ctx) -> None:
    snapshot_history_len = len(legacy_ctx.history)
    snapshot_evidence_len = len(legacy_ctx.evidence_bundle)
    snapshot_slots = dict(legacy_ctx.state_slots)
    to_policy_turn_input(legacy_ctx)
    assert len(legacy_ctx.history) == snapshot_history_len
    assert len(legacy_ctx.evidence_bundle) == snapshot_evidence_len
    assert legacy_ctx.state_slots == snapshot_slots


def test_tool_contracts_match_pack_tools(legacy_ctx) -> None:
    out = to_policy_turn_input(legacy_ctx)
    pack_tool_ids = [t.id for t in legacy_ctx.pack.tools]
    out_tool_ids = [t.id for t in out.tool_contracts]
    assert out_tool_ids == pack_tool_ids
