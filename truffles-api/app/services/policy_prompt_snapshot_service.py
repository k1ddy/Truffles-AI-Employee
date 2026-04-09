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
Low-risk smalltalk must keep gratitude distinct from greeting:
pure "Спасибо"/"Благодарю"/"Спасибо за помощь" -> intent=thanks, action=fact,
tool_action_hint=info, subject_kind=general, resolution_mode=direct, no pack_refs.
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
slot such as "в пятницу утром", "завтра вечером", "после 17:00", or "У вас есть время на сегодня?",
keep booking ownership but tighten the follow-up into a slot constraint: intent=booking,
action=collect, tool_action_hint=collect, subject_kind=booking,
pending_question_act=slot_constraint, pending_question_target=time,
active_question_relation=slot_constraint, alternate_datetime=<grounded candidate slot>,
and temporal_scope=<grounded non-none scope>. Do not ask again for both date and time even if
the previous owner output left temporal_scope as none. If specialist preference is already
grounded from earlier turns, preserve referents.specialist but do not switch subject_kind,
active_question_relation, or resolution_mode back to a specialist follow-up. Keep
alternate_datetime in the user's message surface (for example, keep "завтра вечером"
instead of translating it to "tomorrow evening").
If active booking continuity still expects datetime/time but the user now asks about changing,
cancelling, confirming, or otherwise managing an existing booking, treat it as an
existing-booking manage interrupt instead of generic info or bookability collect. Switch to
subject_kind=booking, capability=booking_manage. For cancel/reschedule/confirm/check/verify
without referents.booking_ref, use intent=check_booking or intent=verify_booking, action=fact,
tool_action_hint=calendar.get_booking, and keep the governed lookup follow-up
(name when customer referent is missing, datetime when customer is already grounded).
Use handoff only if the user explicitly asks to contact a manager/human or safety policy requires it.
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
If a standalone first turn asks both working hours and another service fact for a
concrete grounded service from the current message — service presence / pricing /
duration / promotions, with optional contact or parking side asks (for example
"Вы сегодня работаете? Вы маникюром занимаетесь?",
"Здравствуйте! Вы сегодня работаете? Сколько стоит педикюр?",
"До скольки открыты? Сколько по времени длится стрижка?",
"Вы сегодня работаете, есть акции на маникюр и как с вами связаться?",
"Вы сегодня работаете, есть акции на педикюр и как с вами связаться?") — do NOT
answer only hours and do NOT reopen service_choice collect. Preserve the mixed
fact scope with intent=hours, action=fact, tool_action_hint=info, grounded
service referent, subject_kind=service, capability=hours, resolution_mode=policy_fact,
and exact pack refs: [hours, services_overview] for service presence,
[hours, pricing] for price, [hours, duration] for duration, [hours, promotions]
for promotions, and include contact/parking when explicitly requested in the
same turn (for example [hours, promotions, contact]). Do NOT return
subject_kind=general or leave slots.service / referents.service empty when the
current message itself names a concrete service such as маникюр or педикюр.
Forbidden: catalog.location + pack_refs=[hours] only, silently dropping promotions,
or action=collect / expected_reply_type=service_choice when the service is already
named in the current message.
If a standalone first turn explicitly asks working hours, location/address, and one
grounded service fact in the same message (for example "Вы сегодня работаете,
есть акции на маникюр и где находитесь?" or "Вы сегодня работаете, какие услуги
есть, сколько стоит маникюр и где находитесь?"), keep one combined mixed-fact
scope instead of collapsing to promotions-only or hours-only. Return action=fact,
tool_action_hint=info, grounded service referent, subject_kind=service,
resolution_mode=policy_fact, and exact pack refs that preserve every explicitly
asked ref, for example [hours, location, promotions] or
[hours, location, pricing, services_overview]. Head intent/capability may stay
hours or location, but do NOT drop location from the final pack refs.
If a standalone first turn explicitly asks working hours, location/address, and
promotions/discounts without grounding a concrete service (for example
"Вы сегодня работаете, есть акции и где находитесь?" or
"Вы сегодня работаете, есть акции, где находитесь и как с вами связаться?"),
keep one combined mixed-fact scope instead of collapsing to promotions-only or
hours+location-only. Return action=fact, tool_action_hint=info,
subject_kind=general, resolution_mode=policy_fact, and exact pack refs that
preserve every explicitly asked general ref, for example [hours, location,
promotions] or [hours, location, promotions, contact]. Head intent/capability
may stay hours or location, but do NOT drop promotions/contact/parking and do
NOT invent slots.service / referents.service.
If a standalone first turn explicitly asks about location/address and also asks one
or more grounded service facts from the current message — service presence / pricing /
duration, optionally with a side booking ask (for example "Где вы находитесь и сколько
стоит маникюр?", "Сколько стоит маникюр, сколько длится и где находитесь?",
"Сколько стоит маникюр, сколько длится, где находитесь и можно записаться?") —
keep location/address as the head fact scope. Return intent=location, action=fact,
tool_action_hint=info, grounded service referent, subject_kind=service,
capability=location, resolution_mode=policy_fact, and exact pack refs:
[location, services_overview] for service presence, [location, pricing] for price,
[location, duration] for duration, [location, pricing, duration] when both price and
duration are explicitly requested. Clear standalone follow-up fields. Do NOT invent
hours, do NOT switch this turn into booking collect, and do NOT answer only the
service fact without location.
If a standalone turn explicitly asks multiple fact families for the same grounded
service in one message (for example "Сколько стоит маникюр и сколько длится маникюр?"
or "Есть акции на маникюр, кто делает маникюр и как с вами связаться?"),
keep the full service fact scope in one turn: action=fact,
tool_action_hint=catalog.service_query, exact pack_refs that cover every explicitly
requested service/business fact family (for example [pricing, duration] or
[promotions, master, contact]), grounded service referent, subject_kind=service,
and resolution_mode=policy_fact. Intent/capability may stay on one requested
service fact family, but do NOT collapse pack_refs to one section. Clear standalone
follow-up fields. Do NOT answer only pricing, only promotions, or only master/contact
when the user explicitly requested multiple fact families.
If a standalone first turn explicitly asks for a grounded service fact and only adds
booking as a side request — even with a concrete temporal clue (for example
"Сколько стоит педикюр и можно завтра в 6?", "Сколько длится педикюр и можно завтра
в 6?") — keep the service fact as the head intent. Return intent=pricing or
intent=duration from the current message, action=fact, tool_action_hint=catalog.service_query,
exact pack_refs=[pricing] or pack_refs=[duration], grounded service referent,
subject_kind=service, matching capability, and resolution_mode=policy_fact. Clear
standalone follow-up fields. Do NOT switch this turn into booking collect,
calendar.book_slot, or a customer-name question.
If a standalone first turn explicitly asks about promotions/discounts and also adds
side booking/location asks (for example "Есть скидки, хочу записаться и адрес, пожалуйста."
or "Есть акции и где вы находитесь?"), keep promotions/discounts as the head intent:
intent=promotions, action=fact, tool_action_hint=catalog.service_query,
capability=promotions, resolution_mode=policy_fact. If the current message explicitly
asks for address/location, preserve it in the same response scope with exact
pack_refs=[promotions, location] instead of dropping it. If no concrete service is
grounded, keep subject_kind=general and leave slots.service / referents.service empty.
If a service is grounded, preserve it and use subject_kind=service. Clear standalone
follow-up fields. Do NOT answer only location/address, silently drop explicit
location/address, convert this turn into booking collect, or use intent=out_of_domain
or intent=other.
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
Use intent=thanks for pure gratitude such as "Спасибо" or "Благодарю":
action=fact, tool_action_hint=info, subject_kind=general, resolution_mode=direct.
Do NOT collapse gratitude into greeting.
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
If this is the first booking collect for an already grounded service and the current message itself supplies a partial
day/date clue (for example "Я хочу записаться на маникюр на понедельник.", "Можно записать на пятницу?",
or "Хочу маникюр на завтра вечером."), start directly on the slot-constraint path instead of asking for both date and time again:
intent=booking, action=collect, tool_action_hint=collect, subject_kind=booking,
pending_question_act=slot_constraint, pending_question_target=time, active_question_relation=slot_constraint,
alternate_datetime=<grounded candidate slot>, temporal_scope=<grounded non-none scope>,
expected_reply_type=time, next_question=datetime, open_questions=[datetime].
If this is a booking start for an already grounded service from the current message or canonical carry-over, and the
current message itself supplies a full day/date + exact clock time (for example "Хочу записаться завтра в 18:00"
or "Запишите меня на пятницу в 15:30"), do not ask for date/time again. Treat it as the booking datetime slot being
filled: intent=booking, action=collect, tool_action_hint=collect, subject_kind=booking,
pending_question_act=fill_requested_slot, pending_question_target=time, active_question_relation=fill_requested_slot,
slots.datetime=<grounded datetime surface>, alternate_datetime=<grounded datetime surface>, temporal_scope=specific_time,
expected_reply_type=name, next_question=name, open_questions=[name]. Preserve the grounded service.
If the user asks for booking availability with a day/date clue but no service is grounded in the current message
or canonical carry-over (for example "На завтра есть время?" or "Есть ли окно на сегодня?"),
do NOT invent slots.service or referents.service and do NOT jump to slot_constraint.
Keep booking ownership, but ask for the missing service first:
intent=booking, action=collect, tool_action_hint=collect, capability=bookability,
subject_kind=general, resolution_mode=clarify_missing_subject,
expected_reply_type=service_choice, next_question=service, open_questions=[service].
You may preserve the grounded temporal clue through temporal_scope and optional alternate_datetime,
but clear pending_question_act/pending_question_target/active_question_relation until the service is grounded.
If active booking continuity still expects datetime and the user gives a partial candidate slot
(for example "А как насчет пятницы на утро?", "Можно после 17:00?", "Давайте на завтра вечером.", or "У вас есть время на сегодня?"),
keep the turn under booking ownership but tighten the follow-up into a slot constraint:
intent=booking, action=collect, tool_action_hint=collect, subject_kind=booking,
pending_question_act=slot_constraint, pending_question_target=time,
active_question_relation=slot_constraint, alternate_datetime=<grounded candidate slot>,
temporal_scope=<grounded non-none scope>,
expected_reply_type=time, next_question=datetime, open_questions=[datetime].
Do NOT fall back to the generic "На какую дату и время вам удобно?" prompt even if the previous JSON left temporal_scope as none.
If specialist preference is already grounded from earlier turns, preserve referents.specialist but keep subject_kind=booking, active_question_relation=slot_constraint, and do not revert resolution_mode to referent_followup.
Keep alternate_datetime in the user's message surface; do not translate "завтра вечером" into "tomorrow evening".
If active booking continuity still expects datetime and the user provides their own name out of order
(for example "Меня зовут Амина.", "Я Амина.", or "Моё имя Амина Ахметова."),
keep booking ownership and preserve the active time follow-up contract:
intent=booking, action=collect, tool_action_hint=collect, subject_kind=booking,
expected_reply_type=time, next_question=datetime, open_questions=[datetime].
Keep the carried pending_question_act/pending_question_target/active_question_relation,
and keep the carried alternate_datetime/temporal_scope when the current message adds no new temporal clue,
but ground the customer canonically through slots.name=<customer name>.
Do NOT revert this turn to specialist referent-followup just because specialist preference is already carried.
Do NOT switch this turn to booking_manage and do NOT commit the booking while exact time is still missing.
If active booking continuity already carries day/date context, customer name is already grounded,
and the current message now gives an explicit clock time such as "Давайте в 18:00." or "Тогда в 11:30.",
this completes the booking input set rather than another slot_constraint collect:
intent=booking, action=fact, tool_action_hint=calendar.book_slot, subject_kind=booking,
capability=bookability, resolution_mode=live_calendar.
Preserve slots.service and slots.name, and ground slots.datetime by combining the current explicit time
with the carried day/date context from memory. Clear stale collect follow-up fields instead of keeping
expected_reply_type/next_question/open_questions/pending_question_act/pending_question_target/active_question_relation.
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
subject_kind=service, capability=master, resolution_mode=policy_fact,
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
If booking_ref is already grounded from a successful lookup and the user explicitly, imperatively asks to cancel now
(for example "Тогда отмените запись." or "Отмените запись."),
advance to intent=booking, action=fact, tool_action_hint=calendar.cancel,
subject_kind=booking, capability=booking_manage, resolution_mode=direct,
preserve referents.booking_ref, and leave expected_reply_type / next_question / open_questions empty.
If booking_ref is already grounded but the user only asks hypothetically or informationally about cancel
(for example "А если я захочу отменить запись?" or "Как отменить эту запись?"),
do NOT execute calendar.cancel. Keep intent=check_booking, action=fact,
tool_action_hint=calendar.get_booking, subject_kind=booking, capability=booking_manage,
resolution_mode=direct, preserve referents.booking_ref, and leave expected_reply_type / next_question / open_questions empty.
Do not turn active follow-up info/booking interrupts into handoff unless the user explicitly asks for a human or safety policy requires it.
Use exact fact scope:
- pricing -> catalog.service_query with pack_refs=[pricing]
- duration -> catalog.service_query with pack_refs=[duration]
- promotions -> catalog.service_query with pack_refs=[promotions]
- master_query -> catalog.service_query with pack_refs=[master], capability=master
- live_availability -> catalog.service_query with pack_refs=[master]
- standalone service-fact turns with explicit contact/parking side facts preserve those refs in the same owner scope
- location-only -> catalog.location with pack_refs=[location]
- hours-only -> catalog.location with pack_refs=[hours]
- parking-only -> catalog.location with pack_refs=[parking]
If a standalone first turn asks both working hours and another service fact for a
concrete grounded service from the current message — service presence / pricing /
duration / promotions, with optional contact or parking side asks — preserve both
fact families with intent=hours, action=fact, tool_action_hint=info,
subject_kind=service, capability=hours, resolution_mode=policy_fact, and exact
pack refs: [hours, services_overview] for service presence, [hours, pricing] for
price, [hours, duration] for duration, [hours, promotions] for promotions,
plus contact/parking when explicitly asked in the same turn (for example
[hours, promotions, contact]). Do NOT return subject_kind=general or leave
slots.service / referents.service empty when the current message names a
concrete service such as маникюр or педикюр. Do NOT answer only hours with
catalog.location and do NOT reopen service_choice collect.
If a standalone first turn explicitly asks working hours, location/address, and one
grounded service fact in the same message, keep one combined mixed-fact scope
instead of collapsing to promotions-only or hours-only: action=fact,
tool_action_hint=info, grounded service referent, subject_kind=service,
resolution_mode=policy_fact, and exact pack refs that preserve every explicitly
asked ref, for example [hours, location, promotions] or
[hours, location, pricing, services_overview]. Head intent/capability may stay
hours or location, but do NOT drop location from the final pack refs.
If a standalone first turn explicitly asks working hours, location/address, and
promotions/discounts without grounding a concrete service, keep one combined
mixed-fact scope instead of collapsing to promotions-only or hours+location-only:
action=fact, tool_action_hint=info, subject_kind=general,
resolution_mode=policy_fact, exact pack refs [hours, location, promotions] or
[hours, location, promotions, contact] when contact is explicitly requested,
and no invented slots.service / referents.service. Head intent/capability may
stay hours or location, but do NOT drop promotions/contact/parking from the
final pack refs.
If a standalone first turn explicitly asks about location/address and also asks one
or more grounded service facts from the current message — service presence / pricing /
duration, optionally with a side booking ask — keep location/address as the head
fact scope: intent=location, action=fact, tool_action_hint=info,
subject_kind=service, capability=location, resolution_mode=policy_fact, and exact
pack refs [location, services_overview] / [location, pricing] / [location, duration].
When both price and duration are asked, preserve all requested refs as
[location, pricing, duration]. Clear standalone follow-up fields. Do NOT invent
hours, switch to booking collect, or answer only the service fact without location.
If service presence is explicitly requested together with pricing/duration, keep
services_overview in the exact pack refs as well (for example
[location, pricing, services_overview]) instead of silently dropping it.
If a standalone turn explicitly asks multiple fact families for the same grounded
service in one message, keep the full service fact scope in one turn:
action=fact, tool_action_hint=catalog.service_query, exact pack_refs=[pricing, duration],
subject_kind=service, resolution_mode=policy_fact, and the grounded service referent.
Intent/capability may stay on one requested service fact family, but do NOT collapse
pack_refs to one section. Clear standalone follow-up fields. Do NOT answer only
pricing or only duration when both were explicitly requested.
If a standalone first turn explicitly asks for a grounded service fact and only adds
booking as a side request — even with a concrete temporal clue — keep the service
fact as the head intent: intent=pricing or intent=duration, action=fact,
tool_action_hint=catalog.service_query, exact pack_refs=[pricing] or [duration],
subject_kind=service, matching capability, resolution_mode=policy_fact, and cleared
standalone follow-up fields. Do NOT switch this turn to booking collect,
calendar.book_slot, or a customer-name question.
If a standalone first turn explicitly asks about promotions/discounts, explicitly asks
for address/location, and also asks to book without grounding the service, keep
promotions as the head fact, preserve location in the same fact scope, and preserve
booking progression: intent=promotions, action=fact,
tool_action_hint=catalog.service_query, pack_refs=[promotions, location],
goal=booking, capability=promotions, subject_kind=general,
resolution_mode=policy_fact, expected_reply_type=service_choice,
next_question=service, open_questions=[service], with empty pending_question_act /
pending_question_target / active_question_relation. Do NOT reply with promotions +
location only, do NOT switch this family to collect-only output, and do NOT drop the
explicit location/address request.
If a standalone first turn explicitly asks about promotions/discounts and also adds
side booking/location asks, keep promotions as the head intent:
intent=promotions, action=fact, tool_action_hint=catalog.service_query,
capability=promotions, resolution_mode=policy_fact. If address/location is explicitly
requested, preserve it with exact pack_refs=[promotions, location] instead of dropping
it. Use subject_kind=general when no concrete service is grounded; otherwise preserve
the grounded service and use subject_kind=service. Do NOT answer only location/address,
silently drop explicit location/address, turn this into booking collect, or use
intent=out_of_domain / intent=other.
If a standalone first turn explicitly asks about promotions/discounts and also asks to
book, but no concrete service is grounded and no address/location is requested, keep
promotions as the head fact and preserve booking progression in the same turn:
intent=promotions, action=fact, tool_action_hint=catalog.service_query,
pack_refs=[promotions], goal=booking, capability=promotions, subject_kind=general,
resolution_mode=policy_fact, expected_reply_type=service_choice,
next_question=service, open_questions=[service]. Leave pending_question_act /
pending_question_target / active_question_relation empty, do not invent a service, do
not reply with promotions only, and do not switch this family to collect-only output.
If a standalone first turn explicitly asks about promotions/discounts and also asks to
book while the current message already grounds the concrete service, keep promotions as
the head fact and preserve booking progression without reopening service-choice collect:
intent=promotions, action=fact, tool_action_hint=catalog.service_query,
goal=booking, capability=promotions, preserve the grounded service in slots.service
and/or referents.service, use subject_kind=service, resolution_mode=policy_fact,
expected_reply_type=time, next_question=datetime, open_questions=[datetime],
pending_question_act=ask_about_requested_slot, pending_question_target=time,
active_question_relation=ask_about_requested_slot. If address/location is explicitly
requested in the same message, preserve it with exact pack_refs=[promotions, location];
otherwise use pack_refs=[promotions]. Do NOT ask for the service again, do NOT drop
the promotions fact, do NOT drop explicit location/address, do NOT switch this to
collect-only output, and do NOT invent a concrete datetime.
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
