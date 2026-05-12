"""Pure prompt builder for Policy-Core v3.

A function of `PolicyTurnInput`. Same input → byte-equal output.

Spec: SPECS/POLICY_CORE_V3.md section 5.

Forbidden in this module:
- branching on tenant id, vertical, or service names;
- regex over `current_message`;
- per-scenario hints or "forced fields".
"""
from __future__ import annotations

import json
from textwrap import dedent

from .pack_view import EvidenceItem, PackView, ToolContract, Turn
from .schema import Intent, PolicyTurnInput


_OUTPUT_SCHEMA_HINT = dedent(
    """
    Return exactly one JSON object, no prose, matching this shape:

    {
      "intent": <one of: fact_question | slot_collect | booking_request |
                 booking_manage | handoff_request | smalltalk | unsupported |
                 unknown>,
      "slots": { "<slot_name>": "<value or null>", ... },
      "candidate_action": { "tool": "<tool_id or 'none'>", "args": { ... } },
      "evidence_refs": [ "<evidence_id>", ... ],
      "message_draft": "<your draft customer reply in customer locale>",
      "uncertainty": "low" | "medium" | "high",
      "notes": "<optional rationale>"
    }
    """
).strip()


_SYSTEM_HEADER = dedent(
    """
    You are the policy-core decision owner for a managed AI consultant
    serving service businesses. You are the only component allowed to decide
    customer intent and which tool (if any) to propose.

    Hard rules:
    - You must not invent services, prices, or specialists. Use only the
      tenant pack and evidence bundle below.
    - You must not confirm bookings, cancellations, or reschedules unless
      the pack rules permit it.
    - You must not reveal another customer's appointment without identity
      from the pack rules.
    - When required information is missing, choose intent=slot_collect and
      ask for exactly one missing slot.
    - For medical, legal, refund, or complaint topics listed in the pack
      escalate_topics, choose intent=handoff_request.
    - Cite evidence ids in `evidence_refs` whenever the answer relies on
      pack content or evidence facts.
    - Output strictly the JSON object specified at the end of this prompt.
    """
).strip()


def _format_services(pack: PackView) -> str:
    if not pack.services:
        return "(no services in pack)"
    rows = []
    for s in pack.services:
        bits = [f"id={s.id}", f"name={s.name}"]
        if s.aliases:
            bits.append("aliases=" + ",".join(s.aliases))
        if s.duration_min is not None:
            bits.append(f"duration_min={s.duration_min}")
        if s.price is not None:
            bits.append(f"price={s.price}")
        rows.append("- " + "; ".join(bits))
    return "\n".join(rows)


def _format_specialists(pack: PackView) -> str:
    if not pack.specialists:
        return "(no specialists in pack)"
    rows = []
    for sp in pack.specialists:
        services = ",".join(sp.service_ids) if sp.service_ids else "-"
        rows.append(f"- id={sp.id}; name={sp.name}; services={services}")
    return "\n".join(rows)


def _format_rules(pack: PackView) -> str:
    r = pack.rules
    return dedent(
        f"""
        - bot_can_confirm: {str(r.bot_can_confirm).lower()}
        - required_for_booking: {", ".join(r.required_for_booking) or "(none)"}
        - identity_for_lookup: {", ".join(r.identity_for_lookup) or "(none)"}
        - escalate_topics: {", ".join(r.escalate_topics) or "(none)"}
        """
    ).strip()


def _format_tools(tools: list[ToolContract]) -> str:
    if not tools:
        return "(no tools available)"
    rows = []
    for t in tools:
        schema_text = json.dumps(t.args_schema, ensure_ascii=False, sort_keys=True)
        rows.append(f"- id={t.id}\n  description: {t.description}\n  args_schema: {schema_text}")
    return "\n".join(rows)


def _format_history(history: list[Turn], cap: int) -> str:
    if not history:
        return "(empty)"
    tail = history[-cap:] if cap > 0 else history
    return "\n".join(f"{t.role}: {t.text}" for t in tail)


def _format_evidence(evidence: list[EvidenceItem]) -> str:
    if not evidence:
        return "(no evidence)"
    rows = []
    for e in evidence:
        payload_text = json.dumps(e.payload, ensure_ascii=False, sort_keys=True)
        rows.append(
            f"- id={e.id}; source={e.source}; kind={e.kind}; "
            f"confidence={e.confidence}; payload={payload_text}"
        )
    return "\n".join(rows)


def _format_state_slots(slots: dict) -> str:
    if not slots:
        return "(empty)"
    return json.dumps(slots, ensure_ascii=False, sort_keys=True, indent=2)


def _format_capabilities(caps: list[str]) -> str:
    return ", ".join(caps) if caps else "(none)"


def _allowed_intents() -> str:
    return ", ".join(i.value for i in Intent)


def build_prompt(turn: PolicyTurnInput, *, retry_hint: str | None = None) -> str:
    """Compose the LLM prompt deterministically from inputs.

    `retry_hint`, if provided, is appended verbatim at the end as additional
    instructions on the second attempt. It must come from
    `policy_core_v3.retry_policy`, never from scenario-specific code.
    """

    sections: list[str] = []

    sections.append("# SYSTEM")
    sections.append(_SYSTEM_HEADER)

    sections.append("# TENANT PACK")
    sections.append(f"pack_id: {turn.pack_view.pack_id}")
    sections.append(f"summary: {turn.pack_view.business_summary}")
    sections.append("services:")
    sections.append(_format_services(turn.pack_view))
    sections.append("specialists:")
    sections.append(_format_specialists(turn.pack_view))
    sections.append("rules:")
    sections.append(_format_rules(turn.pack_view))

    sections.append("# CAPABILITIES")
    sections.append(_format_capabilities(turn.capabilities))

    sections.append("# TOOLS")
    sections.append(_format_tools(turn.tool_contracts))
    if turn.tool_contracts:
        allowed_ids = ", ".join(t.id for t in turn.tool_contracts)
        sections.append(f"allowed_tool_ids: {allowed_ids}, none")
    else:
        sections.append("allowed_tool_ids: none")

    sections.append("# CONVERSATION STATE")
    sections.append(f"slots:\n{_format_state_slots(turn.state_slots)}")

    sections.append("# CONVERSATION HISTORY")
    sections.append(_format_history(turn.conversation_history, turn.history_max_turns))

    sections.append("# EVIDENCE BUNDLE")
    sections.append(_format_evidence(turn.evidence_bundle))

    sections.append("# CURRENT MESSAGE")
    sections.append(turn.current_message)

    sections.append("# CONTEXT")
    sections.append(f"now: {turn.now.isoformat()}")
    sections.append(f"locale: {turn.locale}")
    sections.append(f"policy_version: {turn.policy_version}")

    sections.append("# OUTPUT")
    sections.append(f"allowed_intents: {_allowed_intents()}")
    sections.append(_OUTPUT_SCHEMA_HINT)
    sections.append(
        "Reply with the customer-facing draft in the locale specified above. "
        "Reply with exactly one JSON object and nothing else."
    )

    if retry_hint:
        sections.append("# RETRY HINT")
        sections.append(retry_hint)

    return "\n\n".join(sections)
