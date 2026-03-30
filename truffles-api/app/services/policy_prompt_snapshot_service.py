from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


def _resolve_prompts_dir() -> Path:
    module_path = Path(__file__).resolve()
    for parent in module_path.parents:
        candidate = parent / "prompts"
        if candidate.is_dir():
            return candidate
    return module_path.parents[2] / "prompts"


_POLICY_CORE_PROMPTS_DIR = _resolve_prompts_dir()
_POLICY_CORE_PROMPT_PATH = _POLICY_CORE_PROMPTS_DIR / "llm_policy_core.md"
_POLICY_CORE_PROMPT_FALLBACK = """# LLM Policy Core Prompt
Return JSON only (no markdown). Required fields: intent, action, tool_action_hint, pack_refs, slots, expected_reply_type, next_question, open_questions, needs_manager, risk_signals, language, confidence, reason, goal, entity_refs, referents, subject_kind, capability, temporal_scope, resolution_mode, pending_question_act, pending_question_target, active_question_relation, resolver_id, resolver_version.
Optional fields: pack_refs, slots, next_question, open_questions, needs_manager,
risk_signals, language, reason, goal, entity_refs, subject_kind, capability, temporal_scope,
resolution_mode, pending_question_act, pending_question_target, active_question_relation,
resolver_id, resolver_version.
Use tool_action_hint and pack_refs only from the allowed lists provided in the input.
slots/open_questions/next_question may only use: service, datetime, name.
Semantic meaning should stay sparse, but strict structured output requires every declared
field to be present. When a declared field is semantically empty, emit null / [] / {}
for that field and let downstream normalization strip the empty carrier.
If memory.profile.semantic_contract or memory.profile.pending_question_contract is present,
use that canonical dialog contract for follow-up questions.
Intent list includes check_booking and verify_booking.
Treat inflected or prepositional service phrases as explicit service mention; do not
switch to collect only because the service is not in base dictionary form.
Use intent=master_query only when user explicitly asks about specialists for a concrete service/skill.
Availability or specialist-selection questions for a concrete service (for example,
"есть ли специалист по X" or "есть мастер по X") are master_query, not pricing.
If the service is already present, do not collect specialist name; return fact with
tool_action_hint=catalog.service_query and ground the service through slots.service or referents.service.
Example: "У вас есть специалист по окрашиванию?" -> intent=master_query,
action=fact, tool_action_hint=catalog.service_query, slots.service="окрашивание".
Example: "Какого мастера вы можете предложить?" -> intent=master_query,
action=collect, tool_action_hint=collect, next_question=service.
master_query requires slots.service or referents.service for fact answers.
If service is missing for master_query, use action=collect, tool_action_hint=collect,
next_question=service and open_questions must include service.
If active pending_question_contract expects datetime for a known service and the user fixes
a named specialist preference (for example "Мне нужно, чтобы мастер был Айгерим.",
"Хочу к Айгерим.", "Можно к Айгерим?"), keep action=collect and next_question=datetime,
but switch semantic axes to specialist follow-up: referents.specialist, subject_kind=specialist,
capability=bookability, resolution_mode=referent_followup, pending_question_target=specialist,
active_question_relation=referent_followup. Forbidden: generic subject_kind=service plus
active_question_relation=ask_about_requested_slot once referents.specialist is grounded.
For existing-booking lookup without referents.booking_ref, keep bot-active follow-up:
intent=check_booking, action=fact, tool_action=calendar.get_booking, reason=calendar_get_booking_collect_reference.
If customer referent is missing, set expected_reply_type=name, next_question=name, open_questions=[name].
If customer referent is already grounded but booking reference is still missing, set
expected_reply_type=time, next_question=datetime, open_questions=[datetime].
Existing-booking reference follow-up never changes semantic outcome to collect: even when you
need name or datetime, keep action=fact and tool_action_hint=calendar.get_booking and encode
the follow-up only through expected_reply_type / next_question / open_questions.
For calendar.get_booking reference follow-up with next_question=name, omit stale
pending_question_act/pending_question_target/active_question_relation carried from
old booking-create collect. Forbidden: pending_question_target=time or
active_question_relation=ask_about_requested_slot with
reason=calendar_get_booking_collect_reference and next_question=name.
For generic_info_interrupt during active booking continuity, preserve the active follow-up
contract from memory.profile.pending_question_contract: keep expected_reply_type,
next_question, open_questions, and any existing pending_question_act / pending_question_target.
subject_kind values: service, specialist, branch, booking, general.
capability values: pricing, duration, location, hours, promotions, bookability,
live_availability, booking_manage, consultation, portfolio, other.
temporal_scope values: none, specific_time, day, weekday, weekend, date_range.
resolution_mode values: direct, referent_followup, clarify_missing_subject,
clarify_missing_time, ask_about_requested_slot, policy_fact, live_calendar.
pending_question_target values: time, specialist.
active_question_relation values: fill_requested_slot, ask_about_requested_slot,
slot_constraint, slot_compare, mixed_fill_plus_question, referent_followup,
generic_info_interrupt, specialist_availability_interrupt,
specialist_availability_followup, tool_result_followup_specialist_missing.
"""
_POLICY_CORE_PROMPT_CACHE: "PolicyCorePromptSnapshotV1 | None" = None


class PolicyCorePromptSnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "policy_core_prompt_snapshot.v1"
    asset_version: str = "v1"
    prompt_text: str
    source: str
    fallback_used: bool = False


def load_policy_core_prompt_snapshot() -> PolicyCorePromptSnapshotV1:
    global _POLICY_CORE_PROMPT_CACHE
    if _POLICY_CORE_PROMPT_CACHE is not None:
        return _POLICY_CORE_PROMPT_CACHE
    prompt_text = ""
    source = str(_POLICY_CORE_PROMPT_PATH)
    fallback_used = False
    try:
        prompt_text = _POLICY_CORE_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        prompt_text = ""
    if not prompt_text:
        prompt_text = _POLICY_CORE_PROMPT_FALLBACK.strip()
        source = "policy_core_prompt_fallback.v1"
        fallback_used = True
    _POLICY_CORE_PROMPT_CACHE = PolicyCorePromptSnapshotV1(
        prompt_text=prompt_text,
        source=source,
        fallback_used=fallback_used,
    )
    return _POLICY_CORE_PROMPT_CACHE


__all__ = [
    "PolicyCorePromptSnapshotV1",
    "load_policy_core_prompt_snapshot",
]
