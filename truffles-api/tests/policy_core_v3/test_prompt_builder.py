"""Prompt builder purity & invariants for policy_core_v3."""
from __future__ import annotations

from app.policy_core_v3.prompt_builder import build_prompt


def test_prompt_is_deterministic(sample_input) -> None:
    a = build_prompt(sample_input)
    b = build_prompt(sample_input)
    assert a == b


def test_prompt_includes_pack_and_evidence_and_message(sample_input) -> None:
    p = build_prompt(sample_input)
    assert sample_input.pack_view.pack_id in p
    assert sample_input.pack_view.business_summary in p
    assert "brows" in p
    assert "ev-1" in p
    assert "ev-2" in p
    assert sample_input.current_message in p
    assert "allowed_intents:" in p
    assert "allowed_tool_ids:" in p


def test_prompt_lists_only_allowed_tool_ids(sample_input) -> None:
    p = build_prompt(sample_input)
    for tool in sample_input.tool_contracts:
        assert f"id={tool.id}" in p
    # `none` must be listed alongside actual tool ids
    assert "none" in p


def test_prompt_includes_retry_hint_when_provided(sample_input) -> None:
    base = build_prompt(sample_input)
    with_hint = build_prompt(sample_input, retry_hint="please return only JSON")
    assert "RETRY HINT" not in base
    assert "RETRY HINT" in with_hint
    assert "please return only JSON" in with_hint


def test_prompt_truncates_history_to_cap(sample_input) -> None:
    from app.policy_core_v3 import Turn

    long_input = sample_input.model_copy(
        update={
            "conversation_history": [
                Turn(role="customer", text=f"msg-{i}") for i in range(50)
            ],
            "history_max_turns": 5,
        }
    )
    p = build_prompt(long_input)
    # only last 5 should appear
    assert "msg-49" in p
    assert "msg-45" in p
    assert "msg-44" not in p
    assert "msg-0" not in p


def test_prompt_has_no_scenario_branches_in_output(sample_input) -> None:
    """Same prompt structure regardless of message content."""
    a = build_prompt(sample_input)
    b = build_prompt(
        sample_input.model_copy(update={"current_message": "хочу записаться"})
    )
    c = build_prompt(
        sample_input.model_copy(update={"current_message": "это медицинский вопрос"})
    )
    # All three must have identical section headers in identical order
    headers = [
        "# SYSTEM",
        "# TENANT PACK",
        "# CAPABILITIES",
        "# TOOLS",
        "# CONVERSATION STATE",
        "# CONVERSATION HISTORY",
        "# EVIDENCE BUNDLE",
        "# CURRENT MESSAGE",
        "# CONTEXT",
        "# OUTPUT",
    ]
    for prompt in (a, b, c):
        last = -1
        for h in headers:
            idx = prompt.find(h)
            assert idx > last, f"header {h} missing or out of order"
            last = idx
