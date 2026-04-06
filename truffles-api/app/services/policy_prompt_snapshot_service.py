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
_POLICY_CORE_COMPACT_PROMPT_PATH = _POLICY_CORE_PROMPTS_DIR / "llm_policy_core_compact.md"
_POLICY_CORE_PROMPT_FALLBACK = """# LLM Policy Core Prompt
Return JSON only (no markdown). Required fields: intent, action, tool_action_hint, pack_refs, slots, expected_reply_type, next_question, open_questions, needs_manager, risk_signals, language, confidence, reason, goal, entity_refs, referents, subject_kind, capability, temporal_scope, alternate_datetime, resolution_mode, pending_question_act, pending_question_target, active_question_relation, resolver_id, resolver_version.
Optional fields: pack_refs, slots, next_question, open_questions, needs_manager,
risk_signals, language, reason, goal, entity_refs, subject_kind, capability, temporal_scope,
alternate_datetime, resolution_mode, pending_question_act, pending_question_target, active_question_relation,
resolver_id, resolver_version.
Use tool_action_hint and pack_refs only from the allowed lists provided in the input.
Use context.service_cards as pack-side service taxonomy hints. If the current message already
contains a concrete service phrase from those hints (or a close inflected/prepositional variant),
ground it through slots.service or referents.service and do not switch to collect just because
the phrase is not in base dictionary form.
slots/open_questions/next_question may only use: service, datetime, name, phone, media.
Semantic meaning should stay sparse, but strict structured output requires every declared
field to be present. When a declared field is semantically empty, emit null / [] / {}
for that field and let downstream normalization strip the empty carrier.
If memory.profile.semantic_contract or memory.profile.pending_question_contract is present,
use that canonical dialog contract for follow-up questions.
Intent list includes check_booking and verify_booking.
Treat inflected or prepositional service phrases as explicit service mention; do not
switch to collect only because the service is not in base dictionary form.
Inline service fact rule: if the current message already names a concrete service phrase
(for example "укладка", "окрашивание", "маникюр"), keep the turn on the fact path and
ground that service through slots.service or referents.service. Only ask to choose a
service when the current message truly lacks an explicit service mention.
Example: "Сколько времени занимает укладка?" -> intent=duration,
action=fact, tool_action_hint=catalog.service_query, slots.service="укладка".
Forbidden: action=collect, next_question=service, reason=service_missing_for_duration_query.
Use intent=master_query only when user explicitly asks about specialists for a concrete service/skill.
Availability or specialist-selection questions for a concrete service (for example,
"есть ли специалист по X" or "есть мастер по X") are master_query, not pricing.
If the service is already present, do not collect specialist name; return fact with
tool_action_hint=catalog.service_query and ground the service through slots.service or referents.service.
Example: "У вас есть специалист по окрашиванию?" -> intent=master_query,
action=fact, tool_action_hint=catalog.service_query, slots.service="окрашивание".
Example: "Кто делает укладку?" -> intent=master_query,
action=fact, tool_action_hint=catalog.service_query, slots.service="укладка".
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
If the active existing-booking follow-up was asking for customer name and the user just supplied that
name, stay on intent=check_booking, action=fact, tool_action=calendar.get_booking and move the
follow-up to expected_reply_type=time, next_question=datetime, open_questions=[datetime].
Do not switch to booking collect and do not place natural-language prompt text into next_question.
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
If customer explicitly offers a photo/reference/example for consultation before choosing a
service, keep action=collect with tool_action_hint=consult, capability=consultation,
reason=user_offers_photos_for_style_reference, pack_refs=[style_reference],
expected_reply_type=media, next_question=media, open_questions=[media]. Forbidden:
next_question=service or the generic booking prompt about choosing a service.
If active booking continuity still expects datetime and the user supplies a partial candidate
slot such as "в пятницу утром", "завтра вечером", or "после 17:00", keep booking ownership
but tighten the follow-up into a slot constraint: intent=booking, action=collect,
tool_action_hint=collect, subject_kind=booking, pending_question_act=slot_constraint,
pending_question_target=time, active_question_relation=slot_constraint, and
alternate_datetime=<grounded candidate slot>. Do not ask again for both date and time once
temporal_scope is already not none.
If active booking continuity still expects datetime/time but the user now asks about changing,
cancelling, confirming, or otherwise managing an existing booking, treat it as an
existing-booking manage interrupt instead of generic info or bookability collect. Switch to
subject_kind=booking, capability=booking_manage. For cancel/reschedule/confirm without
referents.booking_ref use action=handoff, tool_action_hint=handoff, needs_manager=true.
For check/verify existing booking use action=fact with tool_action_hint=calendar.get_booking.
Do NOT emit intent=other, tool_action_hint=info, capability=bookability, or the generic
reply "Я уточню это для вас." for that interrupt family.
If active booking continuity still expects datetime, memory already carries a day/date context,
and the current message is still only a generic availability question (for example
"Когда можно записаться?", "Какое время доступно?", "На какое время свободно?"),
keep the turn on the canonical requested-slot owner:
intent=booking, action=collect, tool_action_hint=collect, subject_kind=booking,
pending_question_act=ask_about_requested_slot, pending_question_target=time,
active_question_relation=ask_about_requested_slot.
Do NOT switch to hours/location fact and do NOT tighten to slot_constraint unless the current
message itself adds a new grounded candidate slot.
For catalog.location, exact location-family scope must stay in pack_refs:
parking-only -> pack_refs=[parking], hours-only -> pack_refs=[hours],
address/location-only -> pack_refs=[location]. Combine refs only when the user
explicitly asks multiple location-family sections in the same turn.
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
_POLICY_CORE_COMPACT_PROMPT_FALLBACK = """# LLM Policy Core Compact Prompt
Return JSON only (no markdown). Required fields: intent, action, tool_action_hint, pack_refs, slots, expected_reply_type, next_question, open_questions, needs_manager, risk_signals, language, confidence, reason, goal, entity_refs, referents, subject_kind, capability, temporal_scope, alternate_datetime, resolution_mode, pending_question_act, pending_question_target, active_question_relation, resolver_id, resolver_version.
Use tool_action_hint and pack_refs only from the allowed lists in the input.
Treat memory.profile.semantic_contract and memory.profile.pending_question_contract as canonical follow-up context.
For active pending_question_contract, interpret the current message against that pending slot first:
- expected_reply_type=time -> fill datetime if the user gave a date/time answer.
- expected_reply_type=name -> fill customer name if the user gave a name answer.
- expected_reply_type=phone -> fill phone if the user gave a phone answer.
- expected_reply_type=media -> keep media continuation only when the user is actually sending/offering reference media.
If the current message fulfills the pending slot, keep action=collect unless all booking inputs are now complete.
When service + datetime + customer name are already grounded and the turn is ready to commit the booking,
return action=fact and tool_action_hint=calendar.book_slot. Do not keep the turn on collect once booking inputs are complete.
If active booking continuity still expects the requested slot and the user asks whether a candidate time is available,
keep the turn under booking ownership: intent=booking, action=collect, tool_action_hint=collect.
Preserve the active pending_question_contract exactly. Do NOT switch to intent=master_query and do NOT emit
calendar.list_slots while the requested booking slot is still incomplete.
If active booking continuity still expects datetime and the user gives a partial candidate slot
(for example "А как насчет пятницы на утро?", "Можно после 17:00?", "Давайте на завтра вечером."),
keep the turn under booking ownership but tighten the follow-up into a slot constraint:
intent=booking, action=collect, tool_action_hint=collect, subject_kind=booking,
pending_question_act=slot_constraint, pending_question_target=time,
active_question_relation=slot_constraint, alternate_datetime=<grounded candidate slot>,
expected_reply_type=time, next_question=datetime, open_questions=[datetime].
Do NOT fall back to the generic "На какую дату и время вам удобно?" prompt once temporal_scope is already not none.
If active booking continuity still expects datetime, memory already carries a day/date context,
and the current message is still only a generic availability question such as
"Когда можно записаться?", "Какое время доступно?", or "На какое время свободно?",
keep the canonical requested-slot owner instead of over-tightening to slot_constraint:
intent=booking, action=collect, tool_action_hint=collect, subject_kind=booking,
pending_question_act=ask_about_requested_slot, pending_question_target=time,
active_question_relation=ask_about_requested_slot, expected_reply_type=time,
next_question=datetime, open_questions=[datetime].
Do NOT switch to hours/location fact and do NOT infer alternate_datetime from carried context alone.
If active booking continuity still expects datetime and the user fixes a named specialist preference
(for example "Мне нужен мастер Айгерим.", "Хочу к Айгерим.", "Можно к Айгерим?"),
keep the turn under booking ownership and preserve time continuity:
intent=booking, action=collect, tool_action_hint=collect,
subject_kind=specialist, capability=bookability, resolution_mode=referent_followup,
pending_question_target=specialist, active_question_relation=referent_followup,
expected_reply_type=time, next_question=datetime, open_questions=[datetime].
Ground the specialist through referents.specialist. Do NOT keep generic
subject_kind=service or active_question_relation=ask_about_requested_slot once the specialist is grounded.
If active booking continuity still expects datetime, a date/day is already carried in memory, and the user now supplies
an explicit clock time after that specialist/media carryover (for example "Можно на 17:45?", "Давайте в 18:00."),
advance the slot-fill instead of asking for datetime again:
intent=booking, action=collect, tool_action_hint=collect,
expected_reply_type=name, next_question=name, open_questions=[name],
pending_question_act=fill_requested_slot, pending_question_target=time,
active_question_relation=fill_requested_slot.
Preserve grounded service/specialist referents. Do NOT keep pending_question_target=specialist or
active_question_relation=referent_followup once the requested time is already grounded.
If active booking continuity still expects datetime and the user asks a generic specialist/master question
without naming a concrete specialist (for example "Какой специалист будет делать маникюр?",
"Кто делает маникюр?", "Какой мастер работает с маникюром?"),
this is a generic info interrupt, not a specialist referent follow-up:
intent=master_query, action=fact, tool_action_hint=info, pack_refs=[master],
subject_kind=service, capability=portfolio, resolution_mode=policy_fact,
active_question_relation=generic_info_interrupt.
Preserve expected_reply_type=time, next_question=datetime, open_questions=[datetime],
and keep the carried pending_question_act/pending_question_target. Do NOT ask the generic
booking time prompt on this turn.
If active booking continuity still expects datetime and the user asks about promotions/discounts
(for example "Есть ли акции?", "Какие скидки на маникюр?", "У вас есть промо на маникюр?"),
this is a promotions info interrupt, not pricing and not booking collect:
intent=promotions, action=fact, tool_action_hint=catalog.service_query, pack_refs=[promotions],
subject_kind=service, capability=promotions, resolution_mode=policy_fact,
active_question_relation=generic_info_interrupt.
Preserve expected_reply_type=time, next_question=datetime, open_questions=[datetime],
and keep the carried pending_question_act/pending_question_target. Do NOT ask the generic
booking time prompt on this turn and do NOT downgrade pack_refs to pricing.
If active booking continuity still expects datetime and the user offers photo/reference/example media,
switch to consult-media follow-up under the same booking continuity:
intent=consult, action=collect, tool_action_hint=consult, pack_refs=[style_reference],
expected_reply_type=media, next_question=media, open_questions=[media].
Preserve the carried pending_question_act/pending_question_target/active_question_relation and grounded service.
Do NOT answer this media offer as fact/info and do NOT emit info_ref_unresolved.
If a later user turn asks again about booking time/slot after that media follow-up,
media continuity no longer owns the turn. Restore the booking collect contract from
memory.profile.resume_pending_question_contract:
intent=booking, action=collect, tool_action_hint=collect, capability=bookability,
expected_reply_type=time, next_question=datetime, open_questions=[datetime].
Do NOT keep expected_reply_type=media or next_question=media for time-question turns after active media follow-up.
If that later post-media turn already supplies a concrete clock time (for example "Можно на 17:45?"),
advance the booking slot-fill instead of restoring the generic datetime prompt:
expected_reply_type=name, next_question=name, open_questions=[name],
pending_question_act=fill_requested_slot, pending_question_target=time,
active_question_relation=fill_requested_slot.
Preserve grounded service/specialist referents and do NOT keep pending_question_target=specialist.
For generic info interrupt during active booking continuity, answer on fact path and preserve the active follow-up contract.
For check_booking/verify_booking without booking_ref, keep action=fact and tool_action_hint=calendar.get_booking.
If customer referent is missing, use expected_reply_type=name, next_question=name, open_questions=[name].
If customer referent is present but booking reference/time is still missing, use expected_reply_type=time, next_question=datetime, open_questions=[datetime].
Do not turn active follow-up info/booking interrupts into handoff unless the user explicitly asks for a human or safety policy requires it.
Use exact fact scope:
- pricing -> catalog.service_query with pack_refs=[pricing]
- duration -> catalog.service_query with pack_refs=[duration]
- promotions -> catalog.service_query with pack_refs=[promotions]
- master_query/live_availability -> catalog.service_query with pack_refs=[master]
- location-only -> catalog.location with pack_refs=[location]
- hours-only -> catalog.location with pack_refs=[hours]
- parking-only -> catalog.location with pack_refs=[parking]
subject_kind values: service, specialist, branch, booking, general.
capability values: pricing, duration, location, hours, promotions, bookability, live_availability, booking_manage, consultation, portfolio, other.
temporal_scope values: none, specific_time, day, weekday, weekend, date_range.
resolution_mode values: direct, referent_followup, clarify_missing_subject, clarify_missing_time, ask_about_requested_slot, policy_fact, live_calendar.
pending_question_target values: time, specialist.
active_question_relation values: fill_requested_slot, ask_about_requested_slot, slot_constraint, slot_compare, mixed_fill_plus_question, referent_followup, generic_info_interrupt, specialist_availability_interrupt, specialist_availability_followup, tool_result_followup_specialist_missing.
"""
_POLICY_CORE_PROMPT_CACHE: "PolicyCorePromptSnapshotV1 | None" = None
_POLICY_CORE_COMPACT_PROMPT_CACHE: "PolicyCorePromptSnapshotV1 | None" = None


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


def load_policy_core_compact_prompt_snapshot() -> PolicyCorePromptSnapshotV1:
    global _POLICY_CORE_COMPACT_PROMPT_CACHE
    if _POLICY_CORE_COMPACT_PROMPT_CACHE is not None:
        return _POLICY_CORE_COMPACT_PROMPT_CACHE
    prompt_text = ""
    source = str(_POLICY_CORE_COMPACT_PROMPT_PATH)
    fallback_used = False
    try:
        prompt_text = _POLICY_CORE_COMPACT_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        prompt_text = ""
    if not prompt_text:
        prompt_text = _POLICY_CORE_COMPACT_PROMPT_FALLBACK.strip()
        source = "policy_core_compact_prompt_fallback.v1"
        fallback_used = True
    _POLICY_CORE_COMPACT_PROMPT_CACHE = PolicyCorePromptSnapshotV1(
        prompt_text=prompt_text,
        source=source,
        fallback_used=fallback_used,
    )
    return _POLICY_CORE_COMPACT_PROMPT_CACHE


__all__ = [
    "PolicyCorePromptSnapshotV1",
    "load_policy_core_compact_prompt_snapshot",
    "load_policy_core_prompt_snapshot",
]
