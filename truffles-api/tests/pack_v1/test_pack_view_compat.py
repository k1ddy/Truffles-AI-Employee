"""PackV1 → PackView compatibility test.

Spec: SPECS/PACK_V1.md section 6 + acceptance criterion 5.
"""
from __future__ import annotations

import pathlib
from datetime import datetime, timezone

from app.pack_v1 import load_pack, to_pack_view
from app.policy_core_v3 import PolicyTurnInput, ToolContract, build_prompt
from app.policy_core_v3.pack_view import PackView


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
EXAMPLE_PACK = REPO_ROOT / "packs" / "beauty_salon_v1"


def test_pack_v1_satisfies_pack_view_protocol() -> None:
    pack = load_pack(EXAMPLE_PACK)
    view = to_pack_view(pack)
    assert isinstance(view, PackView)
    assert view.pack_id == pack.pack_id
    assert view.business_summary == pack.business.summary
    assert {s.id for s in view.services} == {s.id for s in pack.services}
    assert view.rules.bot_can_confirm == pack.rules.bot_can_confirm


def test_policy_core_v3_prompt_builds_from_pack_v1() -> None:
    """Smoke test: a real pack feeds a real policy-core v3 prompt with no shim."""
    pack = load_pack(EXAMPLE_PACK)
    view = to_pack_view(pack)

    tools = [
        ToolContract(id=t.id, description=t.description, args_schema=t.args_schema)
        for t in pack.tools
    ]

    turn = PolicyTurnInput(
        tenant_id="t1",
        conversation_id="c1",
        current_message="можно завтра в 6 вечера на брови",
        pack_view=view,
        capabilities=list(pack.capabilities),
        tool_contracts=tools,
        now=datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc),
        locale=pack.locale,
    )
    prompt = build_prompt(turn)
    assert pack.pack_id in prompt
    assert "brows_lashes" in prompt or "Брови и ресницы" in prompt
    assert "calendar.book_slot" in prompt
    assert "handoff.create" in prompt
    assert "allowed_tool_ids:" in prompt
