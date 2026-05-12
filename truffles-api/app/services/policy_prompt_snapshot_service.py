from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Any, Mapping

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

_POLICY_CORE_GENERATED_CONTRACT_BLOCK_MARKER = '{{GENERATED_MIXED_FIRST_TURN_FACT_CONTRACT_BLOCK}}'
_POLICY_CORE_LEGACY_FULL_BLOCK_START = '- Если standalone first-turn одновременно спрашивает working hours и ещё один service fact'
_POLICY_CORE_LEGACY_FULL_BLOCK_END = '- `catalog.portfolio` — только для portfolio/photos.'
_POLICY_CORE_LEGACY_COMPACT_BLOCK_START = 'If a standalone first turn asks both working hours and another service fact for a\nconcrete grounded service from the current message'
_POLICY_CORE_LEGACY_COMPACT_BLOCK_END = 'subject_kind values: service, specialist, branch, booking, general.'


@dataclass(frozen=True)
class PolicyCoreGeneratedRepairTemplateV1:
    template_id: str
    lines: tuple[str, ...]


@dataclass(frozen=True)
class PolicyCoreGeneratedValueRefV1:
    value_key: str


@dataclass(frozen=True)
class PolicyCoreGeneratedBoundaryPayloadTemplateV1:
    template_id: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class PolicyCoreGeneratedContractBlockV1:
    block_id: str
    full_prompt_text: str
    compact_prompt_text: str
    semantic_tokens: dict[str, tuple[str, ...]]
    repair_templates: tuple[PolicyCoreGeneratedRepairTemplateV1, ...] = ()
    boundary_payload_templates: tuple[PolicyCoreGeneratedBoundaryPayloadTemplateV1, ...] = ()


@dataclass(frozen=True)
class PolicyCoreBookingInfoInterruptVariantV1:
    head_intent: str
    tool_action_hint: str
    pack_refs: tuple[str, ...]
    capability: str
    example_message: str
    example_alternate_datetime: str
    families: tuple[str, ...] = ("service_grounding_progression", "active_continuity")


def _policy_core_generated_repair_template(
    template_id: str,
    *lines: str,
) -> PolicyCoreGeneratedRepairTemplateV1:
    return PolicyCoreGeneratedRepairTemplateV1(template_id=template_id, lines=tuple(lines))


def _policy_core_generated_value_ref(value_key: str) -> PolicyCoreGeneratedValueRefV1:
    return PolicyCoreGeneratedValueRefV1(value_key=value_key)


def _policy_core_generated_boundary_payload_template(
    template_id: str,
    *,
    intent: Any,
    tool_action_hint: Any,
    pack_refs: Any,
    slots: Any,
    expected_reply_type: Any,
    next_question: Any,
    open_questions: Any,
    goal: Any,
    referents: Any,
    subject_kind: Any,
    capability: Any,
    temporal_scope: Any,
    alternate_datetime: Any,
    resolution_mode: Any,
    pending_question_act: Any,
    pending_question_target: Any,
    active_question_relation: Any,
) -> PolicyCoreGeneratedBoundaryPayloadTemplateV1:
    return PolicyCoreGeneratedBoundaryPayloadTemplateV1(
        template_id=template_id,
        payload={
            "intent": intent,
            "action": "fact",
            "tool_action_hint": tool_action_hint,
            "pack_refs": pack_refs,
            "slots": slots,
            "expected_reply_type": expected_reply_type,
            "next_question": next_question,
            "open_questions": open_questions,
            "needs_manager": False,
            "risk_signals": [],
            "language": _policy_core_generated_value_ref("language"),
            "confidence": _policy_core_generated_value_ref("confidence"),
            "reason": _policy_core_generated_value_ref("reason"),
            "goal": goal,
            "entity_refs": [],
            "referents": referents,
            "subject_kind": subject_kind,
            "capability": capability,
            "temporal_scope": temporal_scope,
            "alternate_datetime": alternate_datetime,
            "resolution_mode": resolution_mode,
            "pending_question_act": pending_question_act,
            "pending_question_target": pending_question_target,
            "active_question_relation": active_question_relation,
            "resolver_id": None,
            "resolver_version": None,
        },
    )


def _policy_core_generated_token(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip()
    return token or None


_BOOKING_INFO_INTERRUPT_VARIANTS: tuple[PolicyCoreBookingInfoInterruptVariantV1, ...] = (
    PolicyCoreBookingInfoInterruptVariantV1(
        head_intent="pricing",
        tool_action_hint="catalog.service_query",
        pack_refs=("pricing",),
        capability="pricing",
        example_message="Сколько стоит маникюр?",
        example_alternate_datetime="на завтра в 18:00",
    ),
    PolicyCoreBookingInfoInterruptVariantV1(
        head_intent="pricing",
        tool_action_hint="catalog.service_query",
        pack_refs=("pricing", "duration"),
        capability="pricing",
        example_message="Сколько стоит маникюр и сколько длится?",
        example_alternate_datetime="на завтра в 18:00",
    ),
    PolicyCoreBookingInfoInterruptVariantV1(
        head_intent="promotions",
        tool_action_hint="catalog.service_query",
        pack_refs=("promotions",),
        capability="promotions",
        example_message="Есть ли акции на маникюр?",
        example_alternate_datetime="пятницу в 15:30",
    ),
    PolicyCoreBookingInfoInterruptVariantV1(
        head_intent="duration",
        tool_action_hint="catalog.service_query",
        pack_refs=("duration",),
        capability="duration",
        example_message="Сколько длится маникюр?",
        example_alternate_datetime="на завтра в 18:00",
    ),
    PolicyCoreBookingInfoInterruptVariantV1(
        head_intent="master_query",
        tool_action_hint="info",
        pack_refs=("master",),
        capability="master",
        example_message="Кто делает маникюр?",
        example_alternate_datetime="на завтра в 18:00",
    ),
    PolicyCoreBookingInfoInterruptVariantV1(
        head_intent="location",
        tool_action_hint="catalog.location",
        pack_refs=("parking",),
        capability="location",
        example_message="Есть ли парковка?",
        example_alternate_datetime="завтра вечером",
        families=("active_continuity",),
    ),
    PolicyCoreBookingInfoInterruptVariantV1(
        head_intent="location",
        tool_action_hint="catalog.location",
        pack_refs=("location",),
        capability="location",
        example_message="Где вы находитесь?",
        example_alternate_datetime="завтра вечером",
        families=("active_continuity",),
    ),
)


def iter_policy_core_booking_info_interrupt_variants(
    *,
    family: str | None = None,
) -> tuple[PolicyCoreBookingInfoInterruptVariantV1, ...]:
    if family is None:
        return _BOOKING_INFO_INTERRUPT_VARIANTS
    return tuple(
        variant
        for variant in _BOOKING_INFO_INTERRUPT_VARIANTS
        if family in variant.families
    )


def resolve_policy_core_booking_info_interrupt_variant(
    *,
    intent: str | None = None,
    capability: str | None = None,
    pack_refs: tuple[str, ...] | list[str] | None = None,
    family: str | None = None,
) -> PolicyCoreBookingInfoInterruptVariantV1 | None:
    normalized_intent = _policy_core_generated_token(intent)
    normalized_capability = _policy_core_generated_token(capability)
    normalized_pack_refs = tuple(
        token
        for token in (
            _policy_core_generated_token(item)
            for item in list(pack_refs or [])
        )
        if token is not None
    )
    candidates = iter_policy_core_booking_info_interrupt_variants(family=family)
    for variant in candidates:
        if (
            normalized_intent != variant.head_intent
            and normalized_capability != variant.capability
        ):
            continue
        if normalized_pack_refs and normalized_pack_refs != variant.pack_refs:
            continue
        return variant
    return None


def resolve_policy_core_booking_info_interrupt_signature(
    *,
    intent: str | None = None,
    capability: str | None = None,
    pack_refs: tuple[str, ...] | list[str] | None = None,
    family: str | None = None,
) -> dict[str, Any] | None:
    variant = resolve_policy_core_booking_info_interrupt_variant(
        intent=intent,
        capability=capability,
        pack_refs=pack_refs,
        family=family,
    )
    if variant is None:
        return None
    return {
        "head_intent": variant.head_intent,
        "tool_action_hint": variant.tool_action_hint,
        "pack_refs": list(variant.pack_refs),
        "capability": variant.capability,
        "families": list(variant.families),
    }


def _policy_core_join_examples(examples: tuple[str, ...], *, final_joiner: str) -> str:
    if not examples:
        return ""
    if len(examples) == 1:
        return examples[0]
    if len(examples) == 2:
        return f"{examples[0]} {final_joiner} {examples[1]}"
    return f"{', '.join(examples[:-1])}, {final_joiner} {examples[-1]}"


def _policy_core_render_booking_info_interrupt_messages() -> str:
    examples = tuple(
        f'"{variant.example_message}"'
        for variant in iter_policy_core_booking_info_interrupt_variants(
            family="service_grounding_progression"
        )
    )
    return _policy_core_join_examples(examples, final_joiner="or")


def _policy_core_render_pack_refs(pack_refs: tuple[str, ...], *, compact: bool) -> str:
    if compact:
        return "[" + ", ".join(pack_refs) + "]"
    return "[" + ", ".join(f'"{item}"' for item in pack_refs) + "]"


def _policy_core_render_booking_info_interrupt_concrete_examples(
    *,
    compact: bool,
    family: str,
    head_intent: str | None = None,
) -> str:
    fragments: list[str] = []
    for variant in iter_policy_core_booking_info_interrupt_variants(family=family):
        if head_intent is not None and variant.head_intent != head_intent:
            continue
        pack_refs = _policy_core_render_pack_refs(variant.pack_refs, compact=compact)
        if compact:
            fragments.append(
                "Example: "
                f'carried alternate_datetime="{variant.example_alternate_datetime}" + '
                f'"{variant.example_message}" -> intent={variant.head_intent}, '
                f"action=fact, tool_action_hint={variant.tool_action_hint}, "
                f"pack_refs={pack_refs}, goal=booking, resolution_mode=policy_fact, "
                "expected_reply_type=name, next_question=name, open_questions=[name], "
                "pending_question_act=fill_requested_slot, pending_question_target=time, "
                "active_question_relation=generic_info_interrupt."
            )
        else:
            fragments.append(
                "Concrete example: "
                f'carried `alternate_datetime="{variant.example_alternate_datetime}"` + '
                f'`"{variant.example_message}"` must return '
                f'`intent="{variant.head_intent}"`, `action="fact"`, '
                f'`tool_action_hint="{variant.tool_action_hint}"`, '
                f"`pack_refs={pack_refs}`, `goal=\"booking\"`, "
                '`resolution_mode="policy_fact"`, `expected_reply_type="name"`, '
                '`next_question="name"`, `open_questions=["name"]`, '
                '`pending_question_act="fill_requested_slot"`, '
                '`pending_question_target="time"`, and '
                '`active_question_relation="generic_info_interrupt"`.'
            )
    return " ".join(fragments)


def _policy_core_render_service_grounding_interrupt_invalid_examples(*, compact: bool) -> str:
    fragments: list[str] = []
    for variant in iter_policy_core_booking_info_interrupt_variants(
        family="service_grounding_progression"
    ):
        pack_refs = _policy_core_render_pack_refs(variant.pack_refs, compact=compact)
        if compact:
            fragments.append(
                "Counterexample invalid: "
                f'carried alternate_datetime="{variant.example_alternate_datetime}" + '
                f'"{variant.example_message}" -> intent={variant.head_intent}, '
                f"pack_refs={pack_refs}, subject_kind=general, "
                "expected_reply_type=service_choice, next_question=service, "
                "open_questions=[service], and empty slots.service/referents.service. "
                "This current turn itself grounds the missing service, so it must use "
                "subject_kind=service, ground slots.service/referents.service, and "
                "switch the follow-up to name with pending_question_act=fill_requested_slot "
                "and pending_question_target=time."
            )
        else:
            fragments.append(
                "Counterexample invalid: "
                f'carried `alternate_datetime="{variant.example_alternate_datetime}"` + '
                f'`"{variant.example_message}"` must NOT return '
                f'`intent="{variant.head_intent}"`, `pack_refs={pack_refs}`, '
                '`subject_kind="general"`, `expected_reply_type="service_choice"`, '
                '`next_question="service"`, `open_questions=["service"]`, and empty '
                '`slots.service` / `referents.service`. This current turn itself grounds '
                'the missing service, so it must use `subject_kind="service"`, ground '
                '`slots.service` / `referents.service`, and switch the follow-up to '
                '`name` with `pending_question_act="fill_requested_slot"` and '
                '`pending_question_target="time"`.'
            )
    return " ".join(fragments)


def _policy_core_render_active_booking_location_interrupt_examples(*, compact: bool) -> str:
    if compact:
        return (
            'Example: carried expected_reply_type=time, next_question=datetime, '
            'open_questions=[datetime], pending_question_act=slot_constraint, '
            'pending_question_target=time, alternate_datetime="завтра вечером" + '
            '"Есть ли парковка?" -> intent=location, action=fact, '
            'tool_action_hint=catalog.location, pack_refs=[parking], goal=booking, '
            'subject_kind=general, capability=location, resolution_mode=policy_fact, '
            'expected_reply_type=time, next_question=datetime, open_questions=[datetime], '
            'pending_question_act=slot_constraint, pending_question_target=time, '
            'active_question_relation=generic_info_interrupt, temporal_scope=day, '
            'alternate_datetime="завтра вечером". '
            'Example: carried same follow-up + "Где вы находитесь?" -> intent=location, '
            'action=fact, tool_action_hint=catalog.location, pack_refs=[location], '
            'subject_kind=general, and the same carried follow-up with '
            'active_question_relation=generic_info_interrupt.'
        )
    return (
        'Concrete example: carried `expected_reply_type="time"`, `next_question="datetime"`, '
        '`open_questions=["datetime"]`, `pending_question_act="slot_constraint"`, '
        '`pending_question_target="time"`, `temporal_scope="day"`, and '
        '`alternate_datetime="завтра вечером"` + `"Есть ли парковка?"` must return '
        '`intent="location"`, `action="fact"`, `tool_action_hint="catalog.location"`, '
        '`pack_refs=["parking"]`, `goal="booking"`, `subject_kind="general"`, '
        '`capability="location"`, `resolution_mode="policy_fact"`, '
        '`expected_reply_type="time"`, `next_question="datetime"`, '
        '`open_questions=["datetime"]`, `pending_question_act="slot_constraint"`, '
        '`pending_question_target="time"`, `active_question_relation="generic_info_interrupt"`, '
        '`temporal_scope="day"`, and `alternate_datetime="завтра вечером"`. '
        'Concrete example: carried the same follow-up contract + `"Где вы находитесь?"` must '
        'return `intent="location"`, `action="fact"`, `tool_action_hint="catalog.location"`, '
        '`pack_refs=["location"]`, `goal="booking"`, `subject_kind="general"`, '
        '`capability="location"`, `resolution_mode="policy_fact"`, and the same carried '
        '`expected_reply_type="time"`, `next_question="datetime"`, `open_questions=["datetime"]`, '
        '`pending_question_act="slot_constraint"`, `pending_question_target="time"`, '
        '`active_question_relation="generic_info_interrupt"`, `temporal_scope="day"`, '
        'and `alternate_datetime="завтра вечером"`.'
    )


def _policy_core_render_missing_service_location_interrupt_examples(*, compact: bool) -> str:
    if compact:
        return (
            'Concrete example: carried expected_reply_type=service_choice, '
            'next_question=service, open_questions=[service], temporal_scope=specific_time, '
            'alternate_datetime="на завтра в 18:00" + "Есть ли парковка?" -> '
            'intent=location, action=fact, tool_action_hint=catalog.location, '
            'pack_refs=[parking], goal=booking, subject_kind=general, capability=location, '
            'resolution_mode=policy_fact, expected_reply_type=service_choice, '
            'next_question=service, open_questions=[service], pending_question_act=null, '
            'pending_question_target=null, active_question_relation=generic_info_interrupt, '
            'and slots.service / referents.service stay empty. '
            'Concrete example: carried the same missing-service follow-up + "Где вы находитесь?" '
            'must keep service_choice/service and must not invent service grounding.'
        )
    return (
        'Concrete example: carried `expected_reply_type="service_choice"`, '
        '`next_question="service"`, `open_questions=["service"]`, '
        '`temporal_scope="specific_time"`, and `alternate_datetime="на завтра в 18:00"` + '
        '`"Есть ли парковка?"` must return `intent="location"`, `action="fact"`, '
        '`tool_action_hint="catalog.location"`, `pack_refs=["parking"]`, '
        '`goal="booking"`, `subject_kind="general"`, `capability="location"`, '
        '`resolution_mode="policy_fact"`, `expected_reply_type="service_choice"`, '
        '`next_question="service"`, `open_questions=["service"]`, '
        '`pending_question_act=null`, `pending_question_target=null`, and '
        '`active_question_relation="generic_info_interrupt"` while keeping '
        '`slots.service` / `referents.service` empty. Concrete example: carried the same '
        'missing-service follow-up + `"Где вы находитесь?"` must keep '
        '`expected_reply_type="service_choice"` / `next_question="service"` and must not '
        'invent service grounding.'
    )


def _policy_core_render_active_booking_location_interrupt_invalid_examples(*, compact: bool) -> str:
    if compact:
        return (
            'Counterexample invalid: carried expected_reply_type=time, next_question=datetime, '
            'open_questions=[datetime], pending_question_act=slot_constraint, '
            'pending_question_target=time, alternate_datetime="завтра вечером" + '
            '"Где вы находитесь?" -> active_question_relation=slot_constraint. '
            'On location/parking fact turns preserve pending_question_act/pending_question_target, '
            'but replace only active_question_relation with generic_info_interrupt.'
        )
    return (
        'Counterexample invalid: carried `expected_reply_type="time"`, '
        '`next_question="datetime"`, `open_questions=["datetime"]`, '
        '`pending_question_act="slot_constraint"`, `pending_question_target="time"`, and '
        '`alternate_datetime="завтра вечером"` + `"Где вы находитесь?"` must NOT keep '
        '`active_question_relation="slot_constraint"` on the fact turn. On location/parking '
        'interrupts preserve the carried `pending_question_act` / `pending_question_target`, '
        'but replace only `active_question_relation` with `"generic_info_interrupt"`.'
    )


_BOOKING_INFO_INTERRUPT_MESSAGES = _policy_core_render_booking_info_interrupt_messages()
_BOOKING_INFO_INTERRUPT_FULL_EXAMPLES = (
    _policy_core_render_booking_info_interrupt_concrete_examples(
        compact=False,
        family="service_grounding_progression",
    )
)
_BOOKING_INFO_INTERRUPT_COMPACT_EXAMPLES = (
    _policy_core_render_booking_info_interrupt_concrete_examples(
        compact=True,
        family="service_grounding_progression",
    )
)
_SERVICE_GROUNDING_INTERRUPT_INVALID_FULL_EXAMPLES = (
    _policy_core_render_service_grounding_interrupt_invalid_examples(compact=False)
)
_SERVICE_GROUNDING_INTERRUPT_INVALID_COMPACT_EXAMPLES = (
    _policy_core_render_service_grounding_interrupt_invalid_examples(compact=True)
)
_ACTIVE_BOOKING_LOCATION_INTERRUPT_FULL_EXAMPLES = (
    _policy_core_render_active_booking_location_interrupt_examples(compact=False)
)
_ACTIVE_BOOKING_LOCATION_INTERRUPT_COMPACT_EXAMPLES = (
    _policy_core_render_active_booking_location_interrupt_examples(compact=True)
)
_MISSING_SERVICE_LOCATION_INTERRUPT_FULL_EXAMPLES = (
    _policy_core_render_missing_service_location_interrupt_examples(compact=False)
)
_MISSING_SERVICE_LOCATION_INTERRUPT_COMPACT_EXAMPLES = (
    _policy_core_render_missing_service_location_interrupt_examples(compact=True)
)
_ACTIVE_BOOKING_LOCATION_INTERRUPT_INVALID_FULL_EXAMPLES = (
    _policy_core_render_active_booking_location_interrupt_invalid_examples(compact=False)
)
_ACTIVE_BOOKING_LOCATION_INTERRUPT_INVALID_COMPACT_EXAMPLES = (
    _policy_core_render_active_booking_location_interrupt_invalid_examples(compact=True)
)


_BOOKING_PROGRESSION_CONTRACT_BLOCK = PolicyCoreGeneratedContractBlockV1(
    block_id="booking_progression_single_owner_envelope",
    full_prompt_text=f"""- Canonical booking progression hard contract: pure booking progression turns stay on the owner-controlled booking path. Direct follow-up answers must not be silently reclassified into unrelated fact-side turns or synthetic state repairs.
- If active booking continuity still expects `datetime/time` and the user answers with a direct date/time clue, keep the booking collect owner path: `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, `goal="booking"`, `subject_kind="booking"`, `capability="bookability"`, and the canonical pending-question contract for the next slot step. Use `pending_question_act="slot_constraint"` only when the current message itself grounds a partial slot clue; otherwise preserve the carried collect relation. Do not drop carried `alternate_datetime` / `temporal_scope` while progression is still active.
- If this is the first booking collect for an already grounded service and the current message itself supplies only a partial day/date clue like `"Хочу записаться на маникюр завтра вечером."`, keep the owner on the slot-constraint collect path instead of reopening generic booking collect. Return `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, `goal="booking"`, `subject_kind="booking"`, `capability="bookability"`, `resolution_mode="direct"`, `expected_reply_type="time"`, `next_question="datetime"`, `open_questions=["datetime"]`, `pending_question_act="slot_constraint"`, `pending_question_target="time"`, `active_question_relation="slot_constraint"`, `temporal_scope="day"`, and `alternate_datetime="завтра вечером"`. Do NOT emit `subject_kind="service"`, do NOT drop `expected_reply_type="time"`, and do NOT fall back to the broad prompt that asks for both date and time again.
- If active booking continuity still expects `datetime/time`, memory already carries a day/date context, and the current message now supplies an explicit clock time after a side fact turn or after specialist/media carryover, that exact time advances the booking progression instead of reopening datetime collect. A preceding `generic_info_interrupt` only answers the side fact turn; it does not become the semantic owner of the next exact-time fill. Return `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, `goal="booking"`, `subject_kind="booking"`, `capability="bookability"`, `resolution_mode="direct"`, `slots.datetime="<carried day/date + exact clock time in user-language surface>"`, `alternate_datetime="<same exact surface>"`, `temporal_scope="specific_time"`, `expected_reply_type="name"`, `next_question="name"`, `open_questions=["name"]`, `pending_question_act="fill_requested_slot"`, `pending_question_target="time"`, and `active_question_relation="fill_requested_slot"`. Concrete example: specialist/media carry -> `"Сколько это длится?"` -> `"В 18:00."` must advance to customer-name collect, preserve grounded `referents.specialist`, and must NOT keep `expected_reply_type="time"`, `pending_question_target="specialist"`, or `active_question_relation="slot_constraint"`.
- If no service is grounded yet and the current message itself asks booking availability with an exact day/date + clock-time slot like `"На завтра в 18:00 есть время?"`, keep the owner on the missing-service booking collect path instead of degrading or widening the slot clue. Return `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, `goal="booking"`, `subject_kind="general"`, `capability="bookability"`, `resolution_mode="clarify_missing_subject"`, `slots.datetime="<grounded exact datetime surface>"`, `alternate_datetime="<same exact surface>"`, `temporal_scope="specific_time"`, `expected_reply_type="service_choice"`, `next_question="service"`, and `open_questions=["service"]`. Leave `pending_question_act`, `pending_question_target`, and `active_question_relation` empty while service is still missing. Concrete example: `"На завтра в 18:00 есть время?"` must NOT ground `slots.service="маникюр"` or invent any other service referent. Invalid shadow examples for this exact first-turn envelope: do NOT output `subject_kind="booking"`, do NOT switch to `resolution_mode="direct"`, do NOT jump to `expected_reply_type="name"` or `expected_reply_type="time"`, and do NOT set `pending_question_act="fill_requested_slot"`, `pending_question_act="slot_constraint"`, or `pending_question_act="ask_about_requested_slot"` while the service is still missing. Do NOT invent `slots.service` / `referents.service`, and do NOT widen this exact slot clue to `day` or `date_range`.
- If active booking continuity still expects the missing service (`expected_reply_type="service_choice"` / `next_question="service"`) and the user provides that service, keep one canonical booking progression owner path instead of reopening unrelated fact families. Preserve `goal="booking"` and move to the next canonical follow-up without inventing fact-side `pack_refs`.
- If active booking continuity still expects the missing service but memory already carries an exact requested datetime (`temporal_scope="specific_time"` plus non-null carried `alternate_datetime`), then a service-only reply like `"Маникюр."` must advance directly to customer-name collect instead of reopening time. Return `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, `subject_kind="booking"`, `capability="bookability"`, `resolution_mode="direct"`, `expected_reply_type="name"`, `next_question="name"`, `open_questions=["name"]`, `pending_question_act="fill_requested_slot"`, `pending_question_target="time"`, and `active_question_relation="fill_requested_slot"`. Preserve the carried exact datetime instead of asking for date/time again.
- If active booking continuity still expects the missing service, memory already carries an exact requested datetime (`temporal_scope="specific_time"` plus non-null carried `alternate_datetime`), and the current fact-side interrupt itself grounds that missing service — for example {_BOOKING_INFO_INTERRUPT_MESSAGES} — answer the requested fact family on the current turn, but advance the booking continuation immediately to customer-name collect. Only the service-grounding variants (`pricing` / `promotions` / `duration` / `master_query`) may switch the missing-service follow-up from `service_choice` to `name`; salon-level `location` / `parking` interrupts do NOT ground the missing service and must stay on the `service_choice` follow-up contract. Keep `goal="booking"`, the current fact intent/capability/tool family (`pricing` / `promotions` / `duration` / `master_query`), set `resolution_mode="policy_fact"`, ground `referents.service` or `slots.service` from the current message / `context.message_grounding_hints.service`, preserve carried `alternate_datetime` and `temporal_scope="specific_time"`, and set `expected_reply_type="name"`, `next_question="name"`, `open_questions=["name"]`, `pending_question_act="fill_requested_slot"`, `pending_question_target="time"`, and `active_question_relation="generic_info_interrupt"`. For this missing-service exact-datetime fact interrupt, `goal`, `pending_question_act`, and `pending_question_target` are mandatory continuation fields, not optional metadata: null or empty values are invalid even when the fact family itself is correct. {_BOOKING_INFO_INTERRUPT_FULL_EXAMPLES} {_MISSING_SERVICE_LOCATION_INTERRUPT_FULL_EXAMPLES} Invalid shadow example: carried `alternate_datetime="на завтра в 18:00"` + `"Сколько длится маникюр?"` must NOT keep `expected_reply_type="service_choice"` / `next_question="service"` once the current turn itself grounded the service; it must advance to `name` with `pending_question_act="fill_requested_slot"` and `pending_question_target="time"`. Do NOT keep `expected_reply_type="service_choice"`, do NOT ask for the service again, do NOT reopen time, do NOT clear `goal` / `pending_question_act` / `pending_question_target`, and do NOT switch this fact interrupt to `resolution_mode="direct"`.
- If active booking continuity already carries an exact requested datetime (`temporal_scope="specific_time"` plus non-null carried `alternate_datetime`), the missing service was grounded on the previous fact interrupt, and the current turn now fills the customer's own name — for example `"Меня зовут Амина."` right after `"Какие скидки на маникюр?"` or `"Кто делает маникюр?"` — the booking input set is complete. Return `intent="booking"`, `action="fact"`, `tool_action_hint="calendar.book_slot"`, `subject_kind="booking"`, `capability="bookability"`, and `resolution_mode="live_calendar"`. Preserve the grounded service, mirror the carried exact datetime into both `slots.datetime` and `alternate_datetime`, ground the customer through `slots.name` / `referents.customer`, and clear stale follow-up axes (`expected_reply_type`, `next_question`, `open_questions`, `pending_question_act`, `pending_question_target`, `active_question_relation`). Do NOT reopen datetime collect and do NOT drop the carried exact datetime on this customer-name turn.
- If active booking continuity already has all required booking inputs in memory (`service`, exact `datetime`, customer `name`, and contact `phone`), and the current message is only a confirmation such as `"да"`, `"ок"`, or `"подтверждаю"`, this is booking commit rather than customer-name carryover or planner degrade. Return `intent="booking"`, `action="fact"`, `tool_action_hint="calendar.book_slot"`, `subject_kind="booking"`, `capability="bookability"`, `resolution_mode="live_calendar"`, carry `slots.service`, `slots.datetime`, `slots.name`, and `slots.phone` from memory, clear stale follow-up axes, and keep `temporal_scope="specific_time"`. Mirror `slots.datetime` into `alternate_datetime` when possible; if `alternate_datetime` is absent, `slots.datetime` remains the executor canonical datetime.
- If active booking continuity is already on specialist carryover, keep `subject_kind="specialist"`, `resolution_mode="referent_followup"`, and `pending_question_target="specialist"` until the owner itself advances the progression. Concrete example: carried `alternate_datetime="завтра вечером"` + `"К Айдане."` must return `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, `subject_kind="specialist"`, `capability="bookability"`, `resolution_mode="referent_followup"`, `expected_reply_type="time"`, `next_question="datetime"`, `open_questions=["datetime"]`, `pending_question_target="specialist"`, and `active_question_relation="referent_followup"`. Do not rewrite specialist carryover to `time` just because a downstream layer prefers a generic datetime question, do not misfile specialist replies such as `"К Айдане."` into `slots.name`, and do NOT clear `expected_reply_type` / `next_question` on that specialist turn.
- If booking management continuity is active, keep the canonical owner path on `intent="check_booking"` with `capability="booking_manage"`. Customer-name fill, reference lookup, and direct manage follow-up remain owner-controlled progression; do not downgrade them into generic collect/fact turns outside the owner contract.
- Forbidden for this progression envelope: reopening already collected slots, downgrading direct booking progression into generic fact answers, silently dropping carried pending-question axes, or rewriting booking-manage follow-up into a different semantic family outside explicit owner output.""",
    compact_prompt_text=f"""Canonical booking progression hard contract: pure booking progression turns stay on the owner-controlled booking path. Direct follow-up answers must not be silently reclassified into unrelated fact turns or synthetic state repairs.
If active booking continuity still expects datetime/time and the user answers with a direct date/time clue, keep the booking collect owner path with intent=booking, action=collect, tool_action_hint=collect, goal=booking, subject_kind=booking, capability=bookability, and the canonical pending-question contract for the next slot step. Use pending_question_act=slot_constraint only when the current message itself grounds a partial slot clue; otherwise preserve the carried collect relation. Do not drop carried alternate_datetime / temporal_scope while progression is still active.
If this is the first booking collect for an already grounded service and the current message itself supplies only a partial day/date clue such as "Хочу записаться на маникюр завтра вечером.", keep the owner on the slot-constraint collect path: intent=booking, action=collect, tool_action_hint=collect, goal=booking, subject_kind=booking, capability=bookability, resolution_mode=direct, expected_reply_type=time, next_question=datetime, open_questions=[datetime], pending_question_act=slot_constraint, pending_question_target=time, active_question_relation=slot_constraint, temporal_scope=day, alternate_datetime="завтра вечером". Do NOT emit subject_kind=service, do NOT drop expected_reply_type=time, and do NOT fall back to the broad date+time prompt.
If active booking continuity still expects datetime/time, memory already carries a day/date context, and the current message now gives an explicit clock time after a side fact turn or after specialist/media carryover, that exact time must advance booking progression instead of reopening datetime collect. A previous generic_info_interrupt only answers the side fact turn; it does not own the next exact-time fill. Return intent=booking, action=collect, tool_action_hint=collect, goal=booking, subject_kind=booking, capability=bookability, resolution_mode=direct, slots.datetime=<carried day/date + exact clock time>, alternate_datetime=<same exact surface>, temporal_scope=specific_time, expected_reply_type=name, next_question=name, open_questions=[name], pending_question_act=fill_requested_slot, pending_question_target=time, active_question_relation=fill_requested_slot. Example: specialist/media carry -> "Сколько это длится?" -> "В 18:00." must advance to name collect, preserve referents.specialist, and must not keep expected_reply_type=time, pending_question_target=specialist, or active_question_relation=slot_constraint.
If no service is grounded yet and the current message itself asks booking availability with an exact day/date + clock-time slot such as "На завтра в 18:00 есть время?", keep the owner on the missing-service booking collect path instead of degrading or widening the slot clue. Return intent=booking, action=collect, tool_action_hint=collect, goal=booking, subject_kind=general, capability=bookability, resolution_mode=clarify_missing_subject, slots.datetime=<grounded exact datetime surface>, alternate_datetime=<same exact surface>, temporal_scope=specific_time, expected_reply_type=service_choice, next_question=service, open_questions=[service]. Leave pending_question_act / pending_question_target / active_question_relation empty while service is still missing. Example: "На завтра в 18:00 есть время?" must not invent slots.service=маникюр or any other grounded service. Invalid shadow examples for this exact first-turn envelope: do not emit subject_kind=booking, resolution_mode=direct, expected_reply_type=name, expected_reply_type=time, pending_question_act=fill_requested_slot, pending_question_act=slot_constraint, or pending_question_act=ask_about_requested_slot while the service is still missing. Do not invent slots.service / referents.service, and do not widen this exact slot clue to day or date_range.
If active booking continuity still expects service_choice/service and the user provides the missing service, keep one canonical booking progression owner path instead of reopening unrelated fact families. Preserve goal=booking and move to the next canonical follow-up without inventing fact-side pack_refs.
If active booking continuity still expects service_choice/service but memory already carries an exact requested datetime (temporal_scope=specific_time plus non-null carried alternate_datetime), then a service-only reply like "Маникюр." must advance directly to name collect: intent=booking, action=collect, tool_action_hint=collect, subject_kind=booking, capability=bookability, resolution_mode=direct, expected_reply_type=name, next_question=name, open_questions=[name], pending_question_act=fill_requested_slot, pending_question_target=time, active_question_relation=fill_requested_slot. Preserve the carried exact datetime instead of asking for time again.
If active booking continuity still expects the missing service, memory already carries an exact requested datetime (temporal_scope=specific_time plus non-null carried alternate_datetime), and the current fact-side interrupt itself grounds that service, answer the requested fact family but advance the booking continuation immediately to name collect. Only service-grounding variants pricing / promotions / duration / master_query may switch service_choice to name; location / parking interrupts must stay on the service_choice follow-up and must leave slots.service / referents.service empty. Examples: {_BOOKING_INFO_INTERRUPT_MESSAGES} must keep goal=booking, the current fact intent/capability/tool family, keep resolution_mode=policy_fact, ground referents.service or slots.service from the current message / context.message_grounding_hints.service, preserve alternate_datetime/temporal_scope=specific_time, and set expected_reply_type=name, next_question=name, open_questions=[name], pending_question_act=fill_requested_slot, pending_question_target=time, active_question_relation=generic_info_interrupt. For this exact interrupt family, goal/pending_question_act/pending_question_target are mandatory; null or empty values are invalid even if the fact family itself is correct. {_BOOKING_INFO_INTERRUPT_COMPACT_EXAMPLES} {_MISSING_SERVICE_LOCATION_INTERRUPT_COMPACT_EXAMPLES} Invalid shadow example: carried alternate_datetime="на завтра в 18:00" + "Сколько длится маникюр?" must not keep expected_reply_type=service_choice or next_question=service once the current turn grounds the service; it must advance to name with pending_question_act=fill_requested_slot and pending_question_target=time. Do not keep expected_reply_type=service_choice, ask for service again, reopen time, clear goal/pending_question_act/pending_question_target, or switch this fact interrupt to resolution_mode=direct.
If active booking continuity already carries an exact requested datetime, the missing service was grounded on the previous fact interrupt, and the current turn now fills the customer's own name, the booking input set is complete. Example: carried alternate_datetime="завтра в 18:00" + "Какие скидки на маникюр?" + "Меня зовут Амина." must return intent=booking, action=fact, tool_action_hint=calendar.book_slot, subject_kind=booking, capability=bookability, resolution_mode=live_calendar, slots.datetime="завтра в 18:00", alternate_datetime="завтра в 18:00", and the grounded customer name. Clear stale follow-up axes; do not reopen time and do not drop the carried exact datetime on this customer-name turn.
If active booking continuity already has all required booking inputs in memory (service, exact datetime, customer name, and contact phone), and the current message is only a confirmation such as "да", "ок", or "подтверждаю", this is booking commit rather than customer-name carryover or planner degrade. Return intent=booking, action=fact, tool_action_hint=calendar.book_slot, subject_kind=booking, capability=bookability, resolution_mode=live_calendar, carry slots.service / slots.datetime / slots.name / slots.phone from memory, clear stale follow-up axes, and keep temporal_scope=specific_time. Mirror slots.datetime into alternate_datetime when possible; if alternate_datetime is absent, slots.datetime remains the executor canonical datetime.
If active booking continuity is already on specialist carryover, keep subject_kind=specialist, resolution_mode=referent_followup, and pending_question_target=specialist until the owner itself advances the progression. Example: carried alternate_datetime="завтра вечером" + "К Айдане." must return intent=booking, action=collect, tool_action_hint=collect, subject_kind=specialist, capability=bookability, resolution_mode=referent_followup, expected_reply_type=time, next_question=datetime, open_questions=[datetime], pending_question_target=specialist, active_question_relation=referent_followup. Do not rewrite specialist carryover to time just because a downstream layer prefers a generic datetime question, do not misfile specialist replies such as "К Айдане." into slots.name, and do not clear expected_reply_type / next_question on that specialist turn; slots.name is only for the customer name.
If booking management continuity is active, keep the canonical owner path on intent=check_booking with capability=booking_manage. Customer-name fill, reference lookup, and direct manage follow-up remain owner-controlled progression; do not downgrade them into generic collect/fact turns outside the owner contract.
Forbidden: reopening already collected slots, downgrading direct booking progression into generic fact answers, silently dropping carried pending-question axes, or rewriting booking-manage follow-up into a different semantic family outside explicit owner output.""",
    semantic_tokens={
        "intents": ("booking", "check_booking")
        + tuple(variant.head_intent for variant in _BOOKING_INFO_INTERRUPT_VARIANTS),
        "actions": ("collect", "fact"),
        "expected_reply_types": ("service_choice", "time", "name", "phone"),
        "next_questions": ("service", "datetime", "name", "phone"),
        "subject_kinds": ("booking", "general", "service", "specialist"),
        "capabilities": (
            "bookability",
            "booking_manage",
            *(variant.capability for variant in _BOOKING_INFO_INTERRUPT_VARIANTS),
        ),
        "temporal_scopes": ("specific_time", "date_range"),
        "resolution_modes": (
            "direct",
            "clarify_missing_subject",
            "referent_followup",
            "live_calendar",
            "policy_fact",
        ),
        "pending_question_acts": ("slot_constraint", "fill_requested_slot"),
        "pending_question_targets": ("time", "phone", "specialist"),
        "active_question_relations": (
            "generic_info_interrupt",
            "slot_constraint",
            "fill_requested_slot",
            "referent_followup",
        ),
    },
)


_BOOKING_CONTINUITY_INTERRUPT_CONTRACT_BLOCK = PolicyCoreGeneratedContractBlockV1(
    block_id="booking_continuity_interrupt_envelope",
    full_prompt_text=f"""- Canonical active booking continuity hard contract: once any booking follow-up is already active, generic availability turns and fact-side interrupts MUST preserve `goal="booking"` and copy the carried follow-up axes exactly. This includes direct time collect, specialist `referent_followup`, and missing-service `clarify_missing_subject`. If carried temporal context already exists, preserve `alternate_datetime` and `temporal_scope` exactly. Carried `alternate_datetime` without matching non-null `temporal_scope` is invalid.
- If active booking continuity still expects `datetime/time` and the user asks a generic availability question like `"Когда можно записаться?"`, `"Какое время доступно?"`, or `"На какое время свободно?"`, keep the same booking collect owner on the canonical requested-slot path: `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, `goal="booking"`, `subject_kind="booking"`, `capability="bookability"`, `resolution_mode="ask_about_requested_slot"`, `pending_question_act="ask_about_requested_slot"`, `pending_question_target="time"`, `active_question_relation="ask_about_requested_slot"`, and preserve carried `expected_reply_type`, `next_question`, `open_questions`, `alternate_datetime`, and `temporal_scope`. Concrete example: carried `alternate_datetime="завтра вечером"` + message `"Когда можно записаться?"` must keep that same `alternate_datetime` and stay on `ask_about_requested_slot`, not `slot_constraint` and not any fact tool. Do NOT infer a new slot and do NOT tighten this turn to `slot_constraint` unless the current message itself grounds a new slot clue.
- If active booking continuity already carries any unresolved follow-up and the user asks a fact-side service interrupt instead of filling it, keep one canonical info-interrupt contract. Preserve `goal="booking"`, carried `expected_reply_type`, `next_question`, `open_questions`, `pending_question_act`, `pending_question_target`, `alternate_datetime`, and `temporal_scope`, then switch only `active_question_relation` to `generic_info_interrupt` so downstream state does not reinterpret the turn as booking collect. The carryover source of truth is `memory.profile.pending_question_contract`, except when that active pending contract currently expects media and `memory.profile.resume_pending_question_contract` exists; in that post-media case the resume contract owns `expected_reply_type`, `next_question`, `open_questions`, `pending_question_act`, and `pending_question_target`, and the media contract no longer owns the turn. This rule applies both to direct time follow-up and to non-direct continuity modes. Override for the missing-service exact-datetime envelope: if the carried follow-up still expects `service_choice`, memory already carries `temporal_scope="specific_time"` plus non-null `alternate_datetime`, and the current fact-side interrupt itself grounds the missing service, the follow-up must advance to `expected_reply_type="name"`, `next_question="name"`, `open_questions=["name"]`, `pending_question_act="fill_requested_slot"`, and `pending_question_target="time"` while the current turn remains `active_question_relation="generic_info_interrupt"`. Concrete examples: carried `pending_question_target="specialist"` + `"Сколько это длится?"` must keep `expected_reply_type="time"`, `next_question="datetime"`, `pending_question_target="specialist"`, and `active_question_relation="generic_info_interrupt"`; carried active media pending + resume `expected_reply_type="time"` + specialist carry + `"Сколько это длится?"` must return the duration fact family with `expected_reply_type="time"`, `next_question="datetime"`, `open_questions=["datetime"]`, `pending_question_target="specialist"`, and `active_question_relation="generic_info_interrupt"`, and must NOT keep `expected_reply_type="media"`, `next_question="media"`, or `open_questions=["media"]`; carried `expected_reply_type="service_choice"` + `"Есть ли парковка?"` must keep `expected_reply_type="service_choice"`, `next_question="service"`, `open_questions=["service"]`, `subject_kind="general"`, and `active_question_relation="generic_info_interrupt"`, and must not invent `slots.service` / `referents.service`; carried exact datetime + {_BOOKING_INFO_INTERRUPT_MESSAGES} must ground `referents.service`, switch the follow-up to `name`, and must not keep `service_choice`.
- Service-grounding interrupts under active booking continuity — `pricing`, `promotions`, `duration`, and `master_query` — must keep the exact current fact family (`catalog.service_query` for pricing/promotions/duration, `info` for master), `goal="booking"`, `resolution_mode="policy_fact"`, and `active_question_relation="generic_info_interrupt"`. Preserve the carried follow-up contract exactly when the active booking already waits for `time` or specialist continuity. But if the carryover still expects `service_choice` while memory already carries `temporal_scope="specific_time"` plus non-null `alternate_datetime`, then the current service-grounding fact turn itself closes the missing service: use `subject_kind="service"`, ground `slots.service` / `referents.service`, and switch the follow-up to `expected_reply_type="name"`, `next_question="name"`, `open_questions=["name"]`, `pending_question_act="fill_requested_slot"`, and `pending_question_target="time"`. Do NOT keep `subject_kind="general"` or empty service grounding on these service-grounding interrupts once the current turn names the service. If the carryover is specialist follow-up, keep `pending_question_target="specialist"` instead of rewriting it to `time`. {_BOOKING_INFO_INTERRUPT_FULL_EXAMPLES} {_SERVICE_GROUNDING_INTERRUPT_INVALID_FULL_EXAMPLES}
- Location / parking interrupt under active booking continuity: `"Есть ли парковка?"`, `"Где вы находитесь?"` => `intent="location"`, `action="fact"`, `tool_action_hint="catalog.location"`, `capability="location"`, `resolution_mode="policy_fact"`, and `active_question_relation="generic_info_interrupt"`. Use exact `pack_refs=["parking"]` for parking-only asks and `pack_refs=["location"]` for plain location asks. Preserve the carried follow-up contract exactly instead of hardcoding a new one. Because these turns answer salon-level facts, keep `subject_kind="general"` even when the active booking already carries a grounded service; do NOT rewrite these interrupts to `subject_kind="booking"` or `subject_kind="service"`. If the carryover still misses service, keep `subject_kind="general"` and leave `slots.service` / `referents.service` empty. If the carryover is specialist follow-up, keep `pending_question_target="specialist"` instead of rewriting it to `time`. Preserve the carried `pending_question_act` / `pending_question_target`, but replace only `active_question_relation` with `generic_info_interrupt` on the current fact turn. {_ACTIVE_BOOKING_LOCATION_INTERRUPT_FULL_EXAMPLES} {_ACTIVE_BOOKING_LOCATION_INTERRUPT_INVALID_FULL_EXAMPLES} Forbidden: leaving `active_question_relation="slot_constraint"` or `active_question_relation="ask_about_requested_slot"` on these location/parking fact turns, or dropping the carried follow-up from the same response.
- Forbidden for this continuity envelope: silently dropping carried `alternate_datetime`, emitting `temporal_scope=null` while `alternate_datetime` is still carried, rewriting info interrupts back into `capability="bookability"` / `resolution_mode="ask_about_requested_slot"`, keeping `active_question_relation="ask_about_requested_slot"` on pricing/promotions/duration/master/location fact turns, or inventing a grounded service while the carried follow-up still expects `service_choice`.""",
    compact_prompt_text=f"""Canonical active booking continuity hard contract: once any booking follow-up is already active, generic availability turns and fact-side interrupts MUST preserve goal=booking and copy the carried follow-up axes exactly. This includes direct time collect, specialist referent_followup, and missing-service clarify_missing_subject. If carried temporal context already exists, preserve alternate_datetime and temporal_scope exactly. Carried alternate_datetime without matching non-null temporal_scope is invalid.
If active booking continuity still expects datetime/time and the user asks a generic availability question such as "Когда можно записаться?" or "Какое время доступно?", keep the same booking collect owner on the canonical requested-slot path: intent=booking, action=collect, tool_action_hint=collect, goal=booking, subject_kind=booking, capability=bookability, resolution_mode=ask_about_requested_slot, pending_question_act=ask_about_requested_slot, pending_question_target=time, active_question_relation=ask_about_requested_slot, and preserve carried expected_reply_type / next_question / open_questions / alternate_datetime / temporal_scope. Example: carried alternate_datetime="завтра вечером" + message "Когда можно записаться?" must keep the same alternate_datetime and stay on ask_about_requested_slot, not slot_constraint and not any fact tool.
If active booking continuity already carries any unresolved follow-up and the user asks a fact-side service interrupt instead of filling it, keep one canonical info-interrupt contract. Preserve goal=booking, carried expected_reply_type / next_question / open_questions / pending_question_act / pending_question_target / alternate_datetime / temporal_scope, then switch only active_question_relation to generic_info_interrupt. The source of truth is memory.profile.pending_question_contract, except when that active pending contract currently expects media and memory.profile.resume_pending_question_contract exists; then the resume contract owns expected_reply_type / next_question / open_questions / pending_question_act / pending_question_target and media no longer owns the turn. This applies both to direct time follow-up and to non-direct continuity modes. Override for missing-service exact-datetime continuity: if the carryover still expects service_choice, memory already carries temporal_scope=specific_time plus alternate_datetime, and the current fact-side interrupt itself grounds the missing service, the follow-up must advance to expected_reply_type=name, next_question=name, open_questions=[name], pending_question_act=fill_requested_slot, pending_question_target=time while the current turn stays active_question_relation=generic_info_interrupt. Examples: carried pending_question_target=specialist + message "Сколько это длится?" must keep pending_question_target=specialist; active media pending + resume time/datetime + specialist carry + message "Сколько это длится?" must keep expected_reply_type=time, next_question=datetime, open_questions=[datetime], pending_question_target=specialist, and must not keep expected_reply_type=media; carried expected_reply_type=service_choice + message "Есть ли парковка?" must keep expected_reply_type=service_choice, next_question=service, open_questions=[service], subject_kind=general, active_question_relation=generic_info_interrupt, and must not invent service grounding; carried exact datetime + message {_BOOKING_INFO_INTERRUPT_MESSAGES} must ground referents.service and switch the follow-up to name instead of keeping service_choice.
Service-grounding interrupts pricing / promotions / duration / master under active booking continuity must keep the exact current fact family, goal=booking, resolution_mode=policy_fact, and active_question_relation=generic_info_interrupt. Preserve the carried follow-up exactly when booking already waits for time or specialist continuity. But if the carryover still expects service_choice and memory already carries temporal_scope=specific_time plus alternate_datetime, this current service-grounding fact turn itself closes the missing service: use subject_kind=service, ground slots.service / referents.service, and switch the follow-up to expected_reply_type=name, next_question=name, open_questions=[name], pending_question_act=fill_requested_slot, pending_question_target=time. Do not keep subject_kind=general or empty service grounding on these grounded service interrupts. If the carryover is specialist follow-up, keep pending_question_target=specialist instead of rewriting it to time. {_BOOKING_INFO_INTERRUPT_COMPACT_EXAMPLES} {_SERVICE_GROUNDING_INTERRUPT_INVALID_COMPACT_EXAMPLES} Location / parking interrupt: intent=location, action=fact, tool_action_hint=catalog.location, goal=booking, capability=location, resolution_mode=policy_fact, active_question_relation=generic_info_interrupt, with exact pack_refs=[parking] for parking-only asks and pack_refs=[location] for plain location asks. Because these turns answer salon-level facts, keep subject_kind=general even when booking already carries a grounded service. Preserve the carried follow-up contract exactly instead of hardcoding a new one. If the carryover still misses service, keep subject_kind=general and leave slots.service / referents.service empty. If the carryover is specialist follow-up, keep pending_question_target=specialist instead of rewriting it to time. Preserve the carried pending_question_act / pending_question_target, but replace only active_question_relation with generic_info_interrupt on the current fact turn. {_ACTIVE_BOOKING_LOCATION_INTERRUPT_COMPACT_EXAMPLES} {_ACTIVE_BOOKING_LOCATION_INTERRUPT_INVALID_COMPACT_EXAMPLES} Do not leave active_question_relation=slot_constraint or active_question_relation=ask_about_requested_slot on these location/parking fact turns.
Forbidden: dropping carried alternate_datetime, emitting temporal_scope=null while alternate_datetime is still carried, rewriting info interrupts back into capability=bookability / resolution_mode=ask_about_requested_slot, keeping active_question_relation=ask_about_requested_slot on pricing/promotions/duration/master/location fact turns, or inventing a grounded service while the carried follow-up still expects service_choice.""",
    semantic_tokens={
        "intents": ("booking", "location", "master_query", "pricing", "duration", "promotions"),
        "actions": ("collect", "fact"),
        "expected_reply_types": ("service_choice", "time", "phone"),
        "next_questions": ("service", "datetime", "phone"),
        "subject_kinds": ("booking", "service", "general"),
        "capabilities": ("bookability", "location", "master", "pricing", "duration", "promotions"),
        "temporal_scopes": ("specific_time", "day", "weekday", "weekend", "date_range"),
        "resolution_modes": ("ask_about_requested_slot", "policy_fact", "referent_followup", "clarify_missing_subject"),
        "pending_question_acts": ("ask_about_requested_slot", "slot_constraint"),
        "pending_question_targets": ("time", "phone", "specialist"),
        "active_question_relations": ("ask_about_requested_slot", "referent_followup", "generic_info_interrupt"),
    },
    repair_templates=(
        _policy_core_generated_repair_template(
            "active_booking_requested_slot_availability_followup",
            "The previous JSON misresolved a generic availability question during an active booking time follow-up.",
            "Keep the same booking collect owner on the canonical requested-slot path.",
            'Return `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, `subject_kind="booking"`, `capability="bookability"`, and `resolution_mode="ask_about_requested_slot"`.',
            'Preserve `expected_reply_type="$carry_reply_type"`, `next_question="$carry_next_question"`, and `open_questions=$open_questions`.',
            'Set `pending_question_act="ask_about_requested_slot"`, `pending_question_target="time"`, and `active_question_relation="ask_about_requested_slot"`.',
            "$carry_temporal_scope_clause",
            "$carry_alternate_datetime_clause",
            "Do NOT tighten this turn to `slot_constraint` unless the current message itself grounds a new slot clue.",
            "Return corrected JSON only.",
        ),
        _policy_core_generated_repair_template(
            "active_booking_info_interrupt_contract",
            "The previous JSON broke the canonical active-booking info-interrupt contract.",
            "Keep the current fact family exact and preserve booking continuity without rewriting the turn back into booking collect.",
            'Return `intent="$head_intent"`, `action="fact"`, `tool_action_hint="$tool_action_hint"`, `goal="booking"`, `pack_refs=$expected_pack_refs`, `subject_kind="$expected_subject_kind"`, `capability="$expected_capability"`, and `resolution_mode="policy_fact"`.',
            'Preserve `expected_reply_type="$carry_reply_type"`, `next_question="$carry_next_question"`, and `open_questions=$open_questions`.',
            'Preserve `pending_question_act="$carry_pending_act"`, `pending_question_target="$carry_pending_target"`, and set `active_question_relation="generic_info_interrupt"`.',
            "$carry_temporal_scope_clause",
            "$carry_alternate_datetime_clause",
            "$interrupt_subject_grounding_clause",
            "Do NOT rewrite this fact interrupt back into `capability=\"bookability\"` or `resolution_mode=\"ask_about_requested_slot\"`.",
            "Return corrected JSON only.",
        ),
    ),
)


_MIXED_FIRST_TURN_FACT_CONTRACT_BLOCK = PolicyCoreGeneratedContractBlockV1(
    block_id="mixed_first_turn_fact_booking_envelope",
    full_prompt_text='- Если standalone first-turn одновременно спрашивает working hours и ещё один service fact по уже grounded услуге из текущего message — service presence / pricing / duration / promotions, с optional `contact` / `parking` side asks (например `"Вы сегодня работаете? Вы маникюром занимаетесь?"`, `"Здравствуйте! Вы сегодня работаете? Сколько стоит педикюр?"`, `"До скольки открыты? Сколько по времени длится стрижка?"`, `"Вы сегодня работаете, есть акции на маникюр и как с вами связаться?"`, `"Вы сегодня работаете, есть акции на педикюр и как с вами связаться?"`) — не отвечай только на один вопрос и не открывай заново `service_choice` collect. Сохрани mixed fact scope через `intent="hours"`, `action="fact"`, `tool_action_hint="info"`, grounded service через `referents.service` или `slots.service`, `subject_kind="service"`, `capability="hours"`, `resolution_mode="policy_fact"`, и точные `pack_refs`: `["hours","services_overview"]` для service presence, `["hours","pricing"]` для price, `["hours","duration"]` для duration, `["hours","promotions"]` для promotions, плюс явно добавляй `contact` / `parking`, если пользователь их запросил в том же ходе, например `["hours","promotions","contact"]`. Не возвращай `subject_kind="general"` и не оставляй `slots.service` / `referents.service` пустыми, если текущий message сам называет конкретную услугу вроде `маникюр` или `педикюр`. Forbidden: `tool_action_hint="catalog.location"` с `pack_refs=["hours"]` only, молча выбрасывать `promotions`, и `action="collect"` / `expected_reply_type="service_choice"` когда service уже назван в current message.\n- Если standalone first-turn одновременно спрашивает working hours и grounded non-promotions service fact по уже названной услуге, а booking идёт только как side request (например `"Вы сегодня работаете и сколько стоит маникюр, можно записаться на 7?"`, `"До скольки открыты и сколько длится педикюр, можно записаться?"`) — hours остаётся head fact scope. Верни `intent="hours"`, `action="fact"`, `tool_action_hint="info"`, grounded service через `referents.service` или `slots.service`, `subject_kind="service"`, `capability="hours"`, `resolution_mode="policy_fact"`, `goal="booking"`, и точные `pack_refs`, которые сохраняют весь asked fact scope, например `["hours","pricing"]` или `["hours","duration"]`. Booking continuation не очищай: всегда задай точный follow-up contract `expected_reply_type="time"`, `next_question="datetime"`, `open_questions=["datetime"]`, `pending_question_target="time"`. Если current message уже сам grounded partial slot clue, задай `pending_question_act="slot_constraint"` и `active_question_relation="slot_constraint"`; иначе задай `pending_question_act="ask_about_requested_slot"` и `active_question_relation="ask_about_requested_slot"`. Forbidden: `expected_reply_type="time"` с пустыми `pending_question_act` / `pending_question_target` / `active_question_relation`, схлопывать такой turn до `intent="pricing"` / `["pricing"]`, молча выбрасывать `hours`, или очищать booking follow-up только потому, что в сообщении есть side booking ask.\n- Если standalone first-turn одновременно спрашивает working hours, address/location и также просит записать, но concrete service ещё не grounded (например `"Вы сегодня работаете, где вы находитесь, можно записаться?"`, `"Вы сегодня работаете, где вы находитесь, хочу записаться."`) — сохрани combined `hours + location` fact scope и missing-service booking follow-up в одном ходе. Это не pure booking collect family: даже если booking side ask сформулирован как вопрос `"можно записаться?"`, hours/location facts остаются в этом же ходе. Верни `action="fact"`, `tool_action_hint="info"`, точные `pack_refs=["hours","location"]`, `goal="booking"`, `subject_kind="general"`, `resolution_mode="policy_fact"`, `expected_reply_type="service_choice"`, `next_question="service"`, `open_questions=["service"]`. Head intent/capability может остаться `hours` или `location`, но не схлопывай fact scope до `["location"]` и не возвращай `intent="booking"`, `action="collect"`, `capability="bookability"` или `resolution_mode="clarify_missing_subject"` вместо combined fact answer. `pending_question_act`, `pending_question_target` и `active_question_relation` держи пустыми, пока услуга не grounded. Forbidden: ответ только адресом/часами без booking follow-up, pure collect-only output, или location-only fact scope, который молча выбрасывает explicit hours ask.\n- Если standalone first-turn одновременно спрашивает working hours, address/location и ещё один grounded service fact в одном сообщении — например `"Вы сегодня работаете, есть акции на маникюр и где находитесь?"`, `"Вы сегодня работаете, какие услуги есть, сколько стоит маникюр и где находитесь?"` — это один combined mixed-fact turn, а не promotions-only и не hours-only path. Сохрани combined scope через `action="fact"`, `tool_action_hint="info"`, grounded service через `referents.service` или `slots.service`, `subject_kind="service"`, `resolution_mode="policy_fact"`, и точные `pack_refs`, которые включают все явно запрошенные refs: например `["hours","location","promotions"]`, `["hours","location","pricing","services_overview"]`, `["hours","location","duration"]`. Head intent/capability может остаться `hours` или `location`, но не выбрасывай `location` и не сужай такой turn до `["hours","promotions"]` или `["promotions"]`. `services_overview` разрешён только если текущий message явно спрашивает service presence (`"какие услуги"`, `"занимаетесь"`, `"делаете"` и т.п.). Если пользователь спросил только hours + location + pricing/duration/promotions, не добавляй `services_overview` по аналогии с соседним примером. Forbidden: `"Вы сегодня работаете, где вы находитесь и сколько стоит маникюр?"` -> `pack_refs=["hours","location","pricing","services_overview"]`.\n- Если standalone first-turn одновременно спрашивает working hours, address/location и promotions/discounts без concrete grounded service — например `"Вы сегодня работаете, есть акции и где находитесь?"` или `"Вы сегодня работаете, есть акции, где находитесь и как с вами связаться?"` — это тоже combined mixed-fact turn, а не promotions-only и не hours+location-only path. Верни `action="fact"`, `tool_action_hint="info"`, `subject_kind="general"`, `resolution_mode="policy_fact"`, и точные `pack_refs`, которые сохраняют все явно запрошенные general refs: `["hours","location","promotions"]`, а при explicit contact/parking side asks — например `["hours","location","promotions","contact"]` или `["hours","location","promotions","parking"]`. Head intent/capability может остаться `hours` или `location`, но не выбрасывай `promotions` / `contact` / `parking` и не придумывай `slots.service` / `referents.service`.\n- Если standalone first-turn явно спрашивает address/location и одновременно задаёт один или несколько service facts по уже grounded услуге из current message — service presence / pricing / duration / master, без booking side ask (например `"Где вы находитесь и сколько стоит маникюр?"`, `"Сколько длится маникюр, кто делает маникюр и где вы находитесь?"`, `"Кто делает маникюр, сколько стоит и где вы находитесь?"`) — address/location остаётся head fact scope, даже если `location` сформулирован позже pricing/duration/master в surface order. Верни `intent="location"`, `action="fact"`, `tool_action_hint="info"`, grounded service через `referents.service` или `slots.service`, `subject_kind="service"`, `capability="location"`, `resolution_mode="policy_fact"`, и сохрани все явно запрошенные fact refs с `location` первым: `["location","services_overview"]` для service presence, `["location","pricing"]` для price, `["location","duration"]` для duration, `["location","master"]` для master, `["location","pricing","duration"]` если пользователь просит и цену, и длительность, `["location","pricing","master"]` если пользователь просит price + master, `["location","duration","master"]` если пользователь просит duration + master, `["location","pricing","services_overview"]` если пользователь просит price + service presence, и аналогично не выбрасывай `services_overview`, когда service presence явно запрошен вместе с pricing/duration/master. `services_overview` разрешён только если текущий message явно спрашивает service presence (`"какие услуги"`, `"занимаетесь"`, `"делаете"` и т.п.). Если пользователь спросил только location + pricing/duration/master, не добавляй `services_overview`. Очисти standalone follow-up fields: `expected_reply_type=null`, `next_question=null`, `open_questions=[]`, `pending_question_act=null`, `pending_question_target=null`, `active_question_relation=null`. Forbidden: выдумывать `hours`, переводить этот turn в booking collect, отвечать только service fact без location, оставлять `pricing` / `duration` / `master` ahead of `location` только потому, что они появились раньше в surface order, молча удалять явно запрошенный `services_overview` или добавлять `services_overview` без explicit service-presence question.\n- Если standalone first-turn явно спрашивает address/location и grounded service fact по уже названной услуге, а booking идёт только как side request (например `"Где вы находитесь и сколько длится педикюр, можно записаться завтра вечером?"`, `"Где вы находитесь и сколько стоит маникюр, можно записаться завтра вечером?"`, `"Сколько стоит маникюр, сколько длится, где находитесь и можно записаться?"`) — location остаётся head fact scope, но booking continuation не теряется. Верни `intent="location"`, `action="fact"`, `tool_action_hint="info"`, grounded service через `referents.service` или `slots.service`, `subject_kind="service"`, `capability="location"`, `resolution_mode="policy_fact"`, `goal="booking"`, и точные `pack_refs`, которые сохраняют весь asked fact scope: `["location","pricing"]`, `["location","duration"]`, `["location","pricing","duration"]`, а `services_overview` добавляй только если service presence явно запрошен. Booking continuation не очищай: всегда задай точный follow-up contract `expected_reply_type="time"`, `next_question="datetime"`, `open_questions=["datetime"]`, `pending_question_target="time"`. Если current message уже сам grounded partial slot clue, задай `pending_question_act="slot_constraint"` и `active_question_relation="slot_constraint"`; иначе задай `pending_question_act="ask_about_requested_slot"` и `active_question_relation="ask_about_requested_slot"`. Forbidden: `expected_reply_type="time"` с пустыми `pending_question_act` / `pending_question_target` / `active_question_relation`, схлопывать такой turn до fact-only, очищать booking follow-up только потому, что location остаётся head intent, или добавлять `services_overview` без explicit service-presence question.\n- Если standalone first-turn явно спрашивает grounded service fact и только добавляет booking как side request — даже с concrete temporal clue (например `"Сколько стоит педикюр и можно завтра в 6?"`, `"Сколько длится педикюр и можно завтра в 6?"`, `"Сколько стоит маникюр, можно записаться завтра вечером?"`) — service fact остаётся head intent, но booking continuation не теряется. Верни `intent="pricing"` или `intent="duration"` по текущему message, `action="fact"`, `tool_action_hint="catalog.service_query"`, точные `pack_refs=["pricing"]` или `pack_refs=["duration"]`, grounded service через `referents.service` или `slots.service`, `subject_kind="service"`, `capability` равный fact intent, `resolution_mode="policy_fact"`, `goal="booking"`, `expected_reply_type="time"`, `next_question="datetime"`, `open_questions=["datetime"]`, `pending_question_target="time"` и booking follow-up relation (`pending_question_act` / `active_question_relation`). Forbidden: переводить такой turn в booking collect, `calendar.book_slot`, вопрос про имя клиента или fact-only ответ без booking follow-up.\n- Head-intent precedence rule for standalone promotions-first mixed turns: если текущий standalone first-turn явно спрашивает про акции/скидки и не относится к working-hours-first mixed families выше, promotions/discounts — единственный допустимый semantic head этого хода. Даже если в том же сообщении есть booking ask, grounded service, address/location/contact/parking side asks, верни `intent="promotions"`, `capability="promotions"`, `action="fact"`, `tool_action_hint="catalog.service_query"`. Side asks кодируй через `pack_refs`, `goal`, `expected_reply_type`, `next_question`, `open_questions` и pending-question contract, но не меняй head intent. Forbidden competing head intents for this family: `intent="booking"`, `intent="location"`, `intent="pricing"`, `intent="consult"`, `intent="other"`.\n- Если standalone first-turn явно спрашивает про акции/скидки, одновременно просит address/location и одновременно просит записать, но concrete service ещё не grounded (например `"Есть скидки, хочу записаться и адрес, пожалуйста."`, `"Есть акции и где вы находитесь, хочу записаться."`) — promotions/discounts остаётся head fact, location должен остаться в том же fact scope, и booking progression нельзя терять. Верни `intent="promotions"`, `action="fact"`, `tool_action_hint="catalog.service_query"`, `pack_refs=["promotions","location"]`, `goal="booking"`, `capability="promotions"`, `subject_kind="general"`, `resolution_mode="policy_fact"`, `expected_reply_type="service_choice"`, `next_question="service"`, `open_questions=["service"]`. Оставь `pending_question_act=null`, `pending_question_target=null`, `active_question_relation=null`, не придумывай `slots.service` / `referents.service`. Forbidden: promotions+location without booking follow-up, чистый collect-only output, и молча выбрасывать explicit location/address.\n- Если standalone first-turn явно спрашивает про акции/скидки и одновременно добавляет side booking/location ask (например `"Есть скидки, хочу записаться и адрес, пожалуйста."` или `"Есть акции и где вы находитесь?"`), promotions/discounts остаётся head intent. Верни `intent="promotions"`, `action="fact"`, `tool_action_hint="catalog.service_query"`, `capability="promotions"`, `resolution_mode="policy_fact"`. Если текущий message явно спрашивает address/location, сохрани его в том же fact scope через точные `pack_refs=["promotions","location"]`; не выбрасывай location только потому, что promotions остаётся head intent. Если concrete service не grounded, держи `subject_kind="general"` и не придумывай `slots.service` / `referents.service`. Если service grounded, сохрани его и используй `subject_kind="service"`. Очисти standalone follow-up fields: `expected_reply_type=null`, `next_question=null`, `open_questions=[]`, `pending_question_act=null`, `pending_question_target=null`, `active_question_relation=null`. Forbidden: отвечать только адресом/локацией, молча выбрасывать явно запрошенный address/location, переводить этот turn в booking collect, использовать `intent="out_of_domain"` или `intent="other"`.\n- Если standalone first-turn явно спрашивает про акции/скидки и одновременно просит записать, но concrete service ещё не grounded и дополнительные general side asks ограничены contact/parking/location (например `"Есть скидки, хочу записаться."`, `"Есть акции, хочу записаться и как с вами связаться?"`), сохрани promotions как head fact, но не выбрасывай booking progression. Верни `intent="promotions"`, `action="fact"`, `tool_action_hint="catalog.service_query"`, `goal="booking"`, `capability="promotions"`, `subject_kind="general"`, `resolution_mode="policy_fact"`, `expected_reply_type="service_choice"`, `next_question="service"`, `open_questions=["service"]`. Если текущий message явно просит address/location/contact/parking, сохрани эти explicit general refs в том же fact scope: например `pack_refs=["promotions","contact"]` или `["promotions","location"]`; иначе используй `pack_refs=["promotions"]`. Оставь `pending_question_act=null`, `pending_question_target=null`, `active_question_relation=null`, не придумывай `slots.service` / `referents.service`. Forbidden: promotions-only reply without booking follow-up, pure collect-only output without promotions fact, и invented service grounding.\n- Если standalone first-turn явно спрашивает про акции/скидки и одновременно просит записать, а concrete service уже grounded в текущем message (например `"Есть акции на маникюр, хочу записаться."`, `"Есть скидки на педикюр, хочу записаться."`, `"Есть акции на маникюр, хочу записаться и адрес, пожалуйста."`, `"Есть акции на маникюр, хочу записаться и как с вами связаться?"`, `"Есть акции на маникюр, хочу записаться, где вы находитесь и как с вами связаться?"`), promotions/discounts всё ещё остаётся head fact, но service-choice collect reopening запрещён. Верни `intent="promotions"`, `action="fact"`, `tool_action_hint="catalog.service_query"`, `goal="booking"`, `capability="promotions"`, grounded service через `slots.service` и/или `referents.service`, `subject_kind="service"`, `resolution_mode="policy_fact"`, `expected_reply_type="time"`, `next_question="datetime"`, `open_questions=["datetime"]`, `pending_question_act="ask_about_requested_slot"`, `pending_question_target="time"`, `active_question_relation="ask_about_requested_slot"`. Если текущий message явно просит address/location/contact/parking, сохрани эти explicit general refs в том же fact scope: например `pack_refs=["promotions","location"]`, `["promotions","contact"]` или `["promotions","location","contact"]`; иначе используй `pack_refs=["promotions"]`. Forbidden: `expected_reply_type="service_choice"`, `next_question="service"` или `open_questions=["service"]`, когда concrete service уже grounded; location-head/service-fact override поверх explicit promotions+booking, снова спрашивать услугу, выбрасывать promotions fact, молча выбрасывать explicit address/location/contact/parking, чистый collect-only output и invented datetime.',
    compact_prompt_text='If a standalone first turn asks both working hours and another service fact for a\nconcrete grounded service from the current message — service presence / pricing /\nduration / promotions, with optional contact or parking side asks — preserve both\nfact families with intent=hours, action=fact, tool_action_hint=info,\nsubject_kind=service, capability=hours, resolution_mode=policy_fact, and exact\npack refs: [hours, services_overview] for service presence, [hours, pricing] for\nprice, [hours, duration] for duration, [hours, promotions] for promotions,\nplus contact/parking when explicitly asked in the same turn (for example\n[hours, promotions, contact]). Do NOT return subject_kind=general or leave\nslots.service / referents.service empty when the current message names a\nconcrete service such as маникюр or педикюр. Do NOT answer only hours with\ncatalog.location and do NOT reopen service_choice collect.\nIf a standalone first turn explicitly asks working hours and a grounded\nnon-promotions service fact, and booking is only a side request, keep hours as\nthe head fact scope: intent=hours, action=fact, tool_action_hint=info,\nsubject_kind=service, capability=hours, resolution_mode=policy_fact,\ngoal=booking, exact pack refs such as [hours, pricing] or [hours, duration],\nand preserve booking continuation through expected_reply_type=time,\nnext_question=datetime, open_questions=[datetime], pending_question_target=time,\nand a booking follow-up relation. Do NOT collapse the turn to pricing-only or\nduration-only, do NOT drop hours, and do NOT clear the booking follow-up just\nbecause the same turn also asks to book.\nIf a standalone first turn explicitly asks working hours, location/address, and\nalso asks to book while no concrete service is grounded, keep one combined\nhours+location fact scope and preserve the missing-service booking follow-up in\nthe same turn: action=fact, tool_action_hint=info, exact pack_refs=[hours, location],\ngoal=booking, subject_kind=general, resolution_mode=policy_fact,\nexpected_reply_type=service_choice, next_question=service,\nopen_questions=[service], and empty pending_question_act /\npending_question_target / active_question_relation. Head intent/capability may\nstay hours or location, but do NOT collapse the fact scope to [location], do\nNOT switch this family to intent=booking / action=collect / capability=bookability,\ndo NOT revert resolution_mode to clarify_missing_subject, and do NOT answer with\nhours/location facts only. Even when the booking side ask is phrased as\n"можно записаться?", it remains a side request inside the same mixed fact turn.\nIf a standalone first turn explicitly asks working hours, location/address, and one\ngrounded service fact in the same message, keep one combined mixed-fact scope\ninstead of collapsing to promotions-only or hours-only: action=fact,\ntool_action_hint=info, grounded service referent, subject_kind=service,\nresolution_mode=policy_fact, and exact pack refs that preserve every explicitly\nasked ref, for example [hours, location, promotions] or\n[hours, location, pricing, services_overview]. Head intent/capability may stay\nhours or location, but do NOT drop location from the final pack refs.\nservices_overview is allowed only when the current message explicitly asks service\npresence ("какие услуги", "занимаетесь", "делаете", etc.). If the user asked only\nhours + location + pricing/duration/promotions, do NOT add services_overview by\nanalogy to the nearby example. Forbidden: "Вы сегодня работаете, где вы\nнаходитесь и сколько стоит маникюр?" -> [hours, location, pricing,\nservices_overview].\nIf a standalone first turn explicitly asks working hours, location/address, and\npromotions/discounts without grounding a concrete service, keep one combined\nmixed-fact scope instead of collapsing to promotions-only or hours+location-only:\naction=fact, tool_action_hint=info, subject_kind=general,\nresolution_mode=policy_fact, exact pack refs [hours, location, promotions] or\n[hours, location, promotions, contact] when contact is explicitly requested,\nand no invented slots.service / referents.service. Head intent/capability may\nstay hours or location, but do NOT drop promotions/contact/parking from the\nfinal pack refs.\nIf a standalone first turn explicitly asks about location/address and also asks one\nor more grounded service facts from the current message, keep location/address as\nthe head fact scope even when the location ask appears later than pricing / duration / master in surface order: intent=location, action=fact, tool_action_hint=info,\nsubject_kind=service, capability=location, resolution_mode=policy_fact, and exact\npack refs with location first: [location, services_overview], [location, pricing], [location, duration], or [location, master].\nWhen multiple service facts are asked, preserve all requested refs as [location, pricing, duration], [location, pricing, master], or [location, duration, master]. services_overview is allowed only when the current\nmessage explicitly asks service presence; do NOT add it for plain location + pricing/duration/master.\nWithout a booking side ask, clear standalone follow-up fields. Do NOT invent hours,\nswitch to booking collect, answer only the service fact without location, or leave pricing/duration/master ahead of location just because those service facts appeared earlier in the message.\nIf the same standalone first turn also adds booking as a side request, keep\nlocation/address as the head fact scope and preserve booking continuation in the\nsame turn: intent=location, action=fact, tool_action_hint=info, goal=booking,\nexact pack refs such as [location, pricing], [location, duration], or\n[location, pricing, duration], subject_kind=service, capability=location,\nresolution_mode=policy_fact, expected_reply_type=time, next_question=datetime,\nopen_questions=[datetime], pending_question_target=time. If the current message already grounds a partial slot clue,\nuse pending_question_act=slot_constraint and active_question_relation=slot_constraint;\notherwise use pending_question_act=ask_about_requested_slot and\nactive_question_relation=ask_about_requested_slot. Do NOT leave any of those follow-up\nfields empty, do NOT collapse this family to fact-only, do NOT clear booking follow-up\nonly because location remains the head intent, and do NOT add services_overview\nwithout an explicit service-presence question.\nIf a standalone turn explicitly asks multiple fact families for the same grounded\nservice in one message, keep the full service fact scope in one turn:\naction=fact, tool_action_hint=catalog.service_query, exact pack_refs=[pricing, duration],\nsubject_kind=service, resolution_mode=policy_fact, and the grounded service referent.\nThis rule applies only to pure service-fact turns: if the same message also explicitly asks location/address or working hours, use the mixed-fact precedence rule instead and keep the general fact head first in pack_refs even when location/hours appears later in surface order. Intent/capability may stay on one requested service fact family only inside that pure service-fact envelope, but do NOT collapse\npack_refs to one section. Clear standalone follow-up fields. Do NOT answer only\npricing or only duration when both were explicitly requested.\nIf a standalone turn explicitly asks multiple grounded service fact families and\nbooking is only a side request with a temporal clue (for example "Сколько стоит\nманикюр и сколько длится, можно записаться завтра вечером?", "Сколько стоит\nпедикюр и сколько длится, можно записаться сегодня после 6?", or "Кто делает\nманикюр и как с вами связаться, можно записаться?"), keep the full multifact\nservice scope and booking continuation in one fact turn. This rule applies only\nto pure service-fact turns: if the same message also explicitly asks\nlocation/address, hours, or promotions, do NOT keep pricing / duration / master as\nthe head by analogy; use the mixed-fact precedence rule below and keep the\ngeneral fact head. Explicit contact or parking side asks stay inside the same pure\nservice-fact owner scope and do not cancel this multifact booking-followup\nfamily: action=fact, tool_action_hint=catalog.service_query, exact pack_refs such\nas [pricing, duration], [master, contact], or [master, parking], grounded\nservice referent, subject_kind=service, resolution_mode=policy_fact,\ngoal=booking, expected_reply_type=time, next_question=datetime, open_questions=[datetime],\npending_question_target=time. If the current message already grounds a partial slot clue,\nuse pending_question_act=slot_constraint and active_question_relation=slot_constraint;\notherwise use pending_question_act=ask_about_requested_slot and\nactive_question_relation=ask_about_requested_slot. Do NOT leave any of those follow-up\nfields empty, do NOT collapse this family to fact-only, do NOT clear booking\nfollow-up only because the head intent remains factual, and do NOT clear booking\nfollow-up only because the same pure service-fact turn explicitly asked contact\nor parking.\nIf a standalone first turn explicitly asks for a grounded service fact and only adds\nbooking as a side request — even with a concrete temporal clue — keep the service\nfact as the head intent: intent=pricing or intent=duration, action=fact,\ntool_action_hint=catalog.service_query, exact pack_refs=[pricing] or [duration],\nsubject_kind=service, matching capability, resolution_mode=policy_fact, goal=booking,\nexpected_reply_type=time, next_question=datetime, open_questions=[datetime],\npending_question_target=time, and a booking follow-up relation. Do NOT switch this\nturn to booking collect, calendar.book_slot, a customer-name question, or a\nfact-only reply without booking follow-up.\nIf a standalone first turn explicitly asks about promotions/discounts, explicitly asks\nfor address/location, and also asks to book without grounding the service, keep\npromotions as the head fact, preserve location in the same fact scope, and preserve\nbooking progression: intent=promotions, action=fact,\ntool_action_hint=catalog.service_query, pack_refs=[promotions, location],\ngoal=booking, capability=promotions, subject_kind=general,\nresolution_mode=policy_fact, expected_reply_type=service_choice,\nnext_question=service, open_questions=[service], with empty pending_question_act /\npending_question_target / active_question_relation. Do NOT reply with promotions +\nlocation only, do NOT switch this family to collect-only output, and do NOT drop the\nexplicit location/address request.\nFor standalone promotions-first mixed turns that are not one of the explicit\nworking-hours-first mixed families above, promotions/discounts is the only\nallowed head intent. Even if the same message also asks to book, already grounds\na service, or asks for address/location/contact/parking, keep\nintent=promotions, capability=promotions, action=fact, and\ntool_action_hint=catalog.service_query. Encode the side asks only through\npack_refs, goal, expected_reply_type, next_question, open_questions, and the\npending-question contract. Do NOT use intent=booking, intent=location,\nintent=pricing, intent=consult, or intent=other for this family.\nIf a standalone first turn explicitly asks about promotions/discounts and also adds\nside booking/location asks, keep promotions as the head intent:\nintent=promotions, action=fact, tool_action_hint=catalog.service_query,\ncapability=promotions, resolution_mode=policy_fact. If address/location is explicitly\nrequested, preserve it with exact pack_refs=[promotions, location] instead of dropping\nit. Use subject_kind=general when no concrete service is grounded; otherwise preserve\nthe grounded service and use subject_kind=service. Do NOT answer only location/address,\nsilently drop explicit location/address, turn this into booking collect, or use\nintent=out_of_domain / intent=other.\nIf a standalone first turn explicitly asks about promotions/discounts and also asks to\nbook while no concrete service is grounded, keep promotions as the head fact and\npreserve booking progression in the same turn: intent=promotions, action=fact,\ntool_action_hint=catalog.service_query, goal=booking, capability=promotions,\nsubject_kind=general, resolution_mode=policy_fact, expected_reply_type=service_choice,\nnext_question=service, open_questions=[service]. If the same message explicitly asks\nfor address/location/contact/parking, preserve those general refs in the same fact\nscope, for example pack_refs=[promotions, contact] or [promotions, location];\notherwise use pack_refs=[promotions]. Leave pending_question_act /\npending_question_target / active_question_relation empty, do not invent a service, do\nnot reply with promotions only, and do not switch this family to collect-only output.\nIf a standalone first turn explicitly asks about promotions/discounts and also asks to\nbook while the current message already grounds the concrete service, keep promotions as\nthe head fact and preserve booking progression without reopening service-choice collect:\nintent=promotions, action=fact, tool_action_hint=catalog.service_query,\ngoal=booking, capability=promotions, preserve the grounded service in slots.service\nand/or referents.service, use subject_kind=service, resolution_mode=policy_fact,\nexpected_reply_type=time, next_question=datetime, open_questions=[datetime],\npending_question_act=ask_about_requested_slot, pending_question_target=time,\nactive_question_relation=ask_about_requested_slot. If address/location/contact/parking\nis explicitly requested in the same message, preserve those general refs in the same\nfact scope, for example pack_refs=[promotions, location], [promotions, contact], or\n[promotions, location, contact]; otherwise use pack_refs=[promotions]. Do NOT let a\nbroader location-head/service-fact override win over explicit promotions+booking. Do\nNOT emit expected_reply_type=service_choice, next_question=service, or\nopen_questions=[service] once the service is already grounded. Do\nNOT ask for the service again, do NOT drop the promotions fact, do NOT drop explicit\naddress/location/contact/parking, do NOT switch this to collect-only output, and do\nNOT invent a concrete datetime.',
    semantic_tokens={
        "intents": (
            "hours",
            "location",
            "promotions",
            "pricing",
            "duration",
            "master_query",
        ),
        "actions": ("fact",),
        "expected_reply_types": ("service_choice", "time"),
        "next_questions": ("service", "datetime"),
        "subject_kinds": ("service", "general"),
        "capabilities": (
            "hours",
            "location",
            "promotions",
            "pricing",
            "duration",
            "master",
        ),
        "resolution_modes": ("policy_fact",),
        "pending_question_acts": ("ask_about_requested_slot", "slot_constraint"),
        "pending_question_targets": ("time",),
        "active_question_relations": ("ask_about_requested_slot", "slot_constraint"),
    },
    repair_templates=(
        _policy_core_generated_repair_template(
            "mixed_first_turn_location_service_fact_scope",
            "This standalone first turn explicitly asks about location/address and one or more grounded service facts.",
            "Keep the explicit location scope as the head fact family and do not fabricate working-hours intent.",
            'Return `intent="location"` and `action="fact"`.',
            'Use `tool_action_hint="info"` so runtime keeps the mixed fact scope together.',
            "Set `pack_refs=$expected_pack_refs` exactly.",
            '`subject_kind="service"`, `capability="location"`, and `resolution_mode="policy_fact"`.',
            'Clear standalone follow-up fields: `expected_reply_type=null`, `next_question=null`, `open_questions=[]`, `pending_question_act=null`, `pending_question_target=null`, and `active_question_relation=null`.',
            'Do NOT switch this turn to `intent="hours"` and do NOT convert it into booking collect.',
            "$grounded_service_clause",
            "Return corrected JSON only.",
        ),
        _policy_core_generated_repair_template(
            "mixed_first_turn_location_service_fact_booking_followup",
            "This standalone first turn explicitly asks about location/address, one or more grounded service facts, and also adds booking as a side request.",
            "Keep location as the head fact family and preserve booking continuation in the same turn.",
            'Return `intent="location"` and `action="fact"`.',
            'Use `tool_action_hint="info"` so runtime keeps the mixed fact scope together.',
            "Set `pack_refs=$expected_pack_refs` exactly.",
            '`subject_kind="service"`, `capability="location"`, `resolution_mode="policy_fact"`, and `goal="booking"`.',
            'Set `expected_reply_type="time"`, `next_question="datetime"`, and `open_questions=["datetime"]`.',
            'Set `pending_question_act="$pending_question_act"`, `pending_question_target="time"`, and `active_question_relation="$pending_question_act"` instead of clearing the booking follow-up relation.',
            'Do NOT switch this turn to `intent="hours"`, do NOT convert it into booking collect, and do NOT drop the booking follow-up.',
            "$grounded_service_clause",
            "Return corrected JSON only.",
        ),
        _policy_core_generated_repair_template(
            "mixed_first_turn_hours_service_booking_followup",
            "This standalone first turn explicitly asks working hours, a grounded non-promotions service fact, and also adds booking as a side request.",
            "Keep working hours as the head fact family and preserve booking continuation in the same turn.",
            'Return `intent="hours"`, `action="fact"`, and `tool_action_hint="info"`.',
            "Set `pack_refs=$expected_pack_refs` exactly.",
            '`subject_kind="service"`, `capability="hours"`, `resolution_mode="policy_fact"`, and `goal="booking"`.',
            'Set `expected_reply_type="time"`, `next_question="datetime"`, and `open_questions=["datetime"]`.',
            'Set `pending_question_target="time"` and keep a booking follow-up relation instead of clearing it.',
            'Do NOT collapse this turn to pricing-only or duration-only, and do NOT drop the booking follow-up.',
            "$grounded_service_clause",
            "Return corrected JSON only.",
        ),
        _policy_core_generated_repair_template(
            "mixed_first_turn_hours_location_booking_followup",
            "This standalone first turn explicitly asks working hours and location/address, and also asks to book without grounding a concrete service.",
            "Keep the hours/location fact answer in the same turn and preserve booking progression instead of clearing the missing-service follow-up.",
            'Return `intent="$head_ref"`, `action="fact"`, and `tool_action_hint="info"`.',
            "Set `pack_refs=$expected_pack_refs` exactly.",
            'Use `subject_kind="general"`, `capability="$head_ref"`, `resolution_mode="policy_fact"`, and `goal="booking"`.',
            'Set `expected_reply_type="service_choice"`, `next_question="service"`, and `open_questions=["service"]`.',
            'Clear `pending_question_act`, `pending_question_target`, and `active_question_relation` for this missing-service fact follow-up.',
            "Do NOT answer only with hours/location and do NOT switch this turn to pure collect.",
            "Return corrected JSON only.",
        ),
        _policy_core_generated_repair_template(
            "mixed_first_turn_hours_location_fact_scope",
            "$scope_line",
            "$extra_scope_line",
            'Return `intent="$head_ref"`, `action="fact"`, and `tool_action_hint="info"`.',
            "Set `pack_refs=$expected_pack_refs` exactly.",
            'Use `subject_kind="general"`, `capability="$head_ref"`, `resolution_mode="policy_fact"`, and `temporal_scope="none"`.',
            'Set `alternate_datetime=null`.',
            'Clear standalone follow-up fields: `expected_reply_type=null`, `next_question=null`, `open_questions=[]`, `pending_question_act=null`, `pending_question_target=null`, and `active_question_relation=null`.',
            "Return corrected JSON only.",
        ),
        _policy_core_generated_repair_template(
            "mixed_first_turn_service_fact_booking_side_precedence",
            "This standalone first turn asks for a grounded service fact and only adds booking as a side request.",
            "Keep the service fact as the head intent even if the side request mentions a concrete time/date.",
            'Return `intent="$expected_ref"`, `action="fact"`, and `tool_action_hint="catalog.service_query"`.',
            "Set `pack_refs=$expected_pack_refs` exactly.",
            'Use `capability="$expected_ref"`, `subject_kind="service"`, `resolution_mode="policy_fact"`, and `goal="booking"`.',
            'Set `expected_reply_type="time"`, `next_question="datetime"`, and `open_questions=["datetime"]`.',
            'Set `pending_question_target="time"` and keep a booking follow-up relation instead of clearing it.',
            'Do NOT switch this turn to booking collect or `calendar.book_slot`, and do NOT strip the booking continuation.',
            "$grounded_service_clause",
            "Return corrected JSON only.",
        ),
        _policy_core_generated_repair_template(
            "service_query_multifact_booking_followup",
            "This standalone turn asks multiple fact families for a grounded service and also adds booking as a side request.",
            "Keep the full multifact service scope and preserve booking continuation in the same fact turn.",
            'Return `intent="$head_intent"`, `action="fact"`, and `tool_action_hint="catalog.service_query"`.',
            "Set `pack_refs=$expected_pack_refs` exactly.",
            'Use `capability="$head_ref"`, `subject_kind="service"`, `resolution_mode="policy_fact"`, and `goal="booking"`.',
            'Keep `expected_reply_type="time"`, `next_question="datetime"`, `open_questions=["datetime"]`, and `pending_question_target="time"`.',
            'Use `pending_question_act="$pending_question_act"` and the same value for `active_question_relation`.',
            "Do NOT collapse this turn to fact-only and do NOT clear booking follow-up just because the head remains factual.",
            "$grounded_service_clause",
            "Return corrected JSON only.",
        ),
        _policy_core_generated_repair_template(
            "mixed_first_turn_hours_service_fact_scope",
            "This standalone first turn asks working hours plus another service fact for a concrete service already named in the current message.",
            "Do not answer only the hours part and do not reopen missing-service collect.",
            'Keep `intent="hours"` and `action="fact"`.',
            'Use `tool_action_hint="info"` so runtime preserves the mixed fact scope instead of a partial single-family answer.',
            "Set `pack_refs=$expected_pack_refs` exactly.",
            '`subject_kind="service"`, `capability="hours"`, and `resolution_mode="policy_fact"`.',
            'Clear standalone follow-up fields: `expected_reply_type=null`, `next_question=null`, `open_questions=[]`, `pending_question_act=null`, `pending_question_target=null`, and `active_question_relation=null`.',
            "$grounded_service_clause",
            "Return corrected JSON only.",
        ),
        _policy_core_generated_repair_template(
            "mixed_first_turn_promotions_precedence_fact_scope",
            "This standalone first turn asks about promotions or discounts and also includes side booking/location asks.",
            "Keep the promotions/discounts question as the head intent instead of answering only the side ask.",
            'Return `intent="promotions"`, `action="fact"`, `tool_action_hint="catalog.service_query"`, `pack_refs=$expected_pack_refs`, `capability="promotions"`, and `resolution_mode="policy_fact"`.',
            "If the current message explicitly asks for address/location, preserve that fact in the same response scope instead of dropping it.",
            "Do NOT switch this turn to `catalog.location`, do NOT convert it into booking collect, and do NOT use `intent=\"out_of_domain\"` or `intent=\"other\"`.",
            "$grounded_subject_clause",
            'Clear standalone follow-up fields: `expected_reply_type=null`, `next_question=null`, `open_questions=[]`, `pending_question_act=null`, `pending_question_target=null`, and `active_question_relation=null`.',
            "Return corrected JSON only.",
        ),
        _policy_core_generated_repair_template(
            "mixed_first_turn_promotions_precedence_missing_service_booking_followup",
            "This standalone first turn asks about promotions or discounts and also includes side booking/location asks.",
            "Keep the promotions/discounts question as the head intent instead of answering only the side ask.",
            'Return `intent="promotions"`, `action="fact"`, `tool_action_hint="catalog.service_query"`, `pack_refs=$expected_pack_refs`, `capability="promotions"`, `goal="booking"`, and `resolution_mode="policy_fact"`.',
            "If the current message explicitly asks for address/location, preserve that fact in the same response scope instead of dropping it.",
            "Do NOT switch this turn to `catalog.location`, do NOT convert it into booking collect, and do NOT use `intent=\"out_of_domain\"` or `intent=\"other\"`.",
            'If no concrete service is grounded, keep `subject_kind="general"` and leave `slots.service` / `referents.service` empty.',
            'Preserve missing-service booking follow-up: set `expected_reply_type="service_choice"`, `next_question="service"`, and `open_questions=["service"]` after the promotions fact scope.',
            'Clear `pending_question_act`, `pending_question_target`, and `active_question_relation` for this missing-service follow-up.',
            "Return corrected JSON only.",
        ),
        _policy_core_generated_repair_template(
            "mixed_first_turn_promotions_precedence_grounded_service_booking_followup",
            "This standalone first turn asks about promotions or discounts and also includes side booking/location asks.",
            "Keep the promotions/discounts question as the head intent instead of answering only the side ask.",
            'Return `intent="promotions"`, `action="fact"`, `tool_action_hint="catalog.service_query"`, `pack_refs=$expected_pack_refs`, `capability="promotions"`, `goal="booking"`, and `resolution_mode="policy_fact"`.',
            "If the current message explicitly asks for address/location, preserve that fact in the same response scope instead of dropping it.",
            "Do NOT switch this turn to `catalog.location`, do NOT convert it into booking collect, and do NOT use `intent=\"out_of_domain\"` or `intent=\"other\"`.",
            "$grounded_subject_clause",
            'Set `expected_reply_type="time"`, `next_question="datetime"`, and `open_questions=["datetime"]`.',
            'Set `pending_question_act="ask_about_requested_slot"`, `pending_question_target="time"`, and `active_question_relation="ask_about_requested_slot"`.',
            "Return corrected JSON only.",
        ),
        _policy_core_generated_repair_template(
            "promotions_booking_followup",
            "This standalone first turn asks about promotions or discounts and also explicitly asks to book, but the service is still missing.",
            "Keep the promotions fact in this same turn and preserve booking progression instead of dropping booking or switching to collect-only output.",
            'Return `intent="promotions"`, `action="fact"`, `tool_action_hint="catalog.service_query"`, `pack_refs=$expected_pack_refs`, `capability="promotions"`, `goal="booking"`, and `resolution_mode="policy_fact"`.',
            'Set `expected_reply_type="service_choice"`, `next_question="service"`, and `open_questions=["service"]` so runtime asks for the missing service after the promotions fact.',
            'Keep `subject_kind="general"` and leave `slots.service` / `referents.service` empty because no concrete service is grounded yet.',
            'Clear `pending_question_act`, `pending_question_target`, and `active_question_relation` for this standalone fact follow-up.',
            "Do NOT drop the booking ask, do NOT answer with promotions only, and do NOT switch this turn to pure collect.",
            "Return corrected JSON only.",
        ),
        _policy_core_generated_repair_template(
            "promotions_location_booking_followup",
            "This standalone first turn asks about promotions or discounts, asks for address/location, and also asks to book without grounding the service.",
            "Keep the promotions and location facts in the same turn and preserve booking progression instead of dropping the follow-up.",
            'Return `intent="promotions"`, `action="fact"`, `tool_action_hint="catalog.service_query"`, `pack_refs=$expected_pack_refs`, `capability="promotions"`, `goal="booking"`, and `resolution_mode="policy_fact"`.',
            'Set `expected_reply_type="service_choice"`, `next_question="service"`, and `open_questions=["service"]` so runtime asks only for the missing service after the promotions + location fact response.',
            'Keep `subject_kind="general"` and leave `slots.service` / `referents.service` empty because no concrete service is grounded yet.',
            'Clear `pending_question_act`, `pending_question_target`, and `active_question_relation` for this standalone fact follow-up.',
            "Do NOT answer with promotions+location only, do NOT switch this family to pure collect, and do NOT drop the booking ask.",
            "Return corrected JSON only.",
        ),
        _policy_core_generated_repair_template(
            "promotions_grounded_service_booking_followup",
            "This standalone first turn asks about promotions or discounts, already grounds the service in the current message, and also asks to book.",
            "Do not reopen service-choice collect because the service is already known.",
            "Do not emit `expected_reply_type=service_choice`, `next_question=service`, or `open_questions=[service]` once the service is already grounded.",
            'Return `intent="promotions"`, `action="fact"`, `tool_action_hint="catalog.service_query"`, `pack_refs=$expected_pack_refs`, `capability="promotions"`, `goal="booking"`, and `resolution_mode="policy_fact"`.',
            'Set `expected_reply_type="time"`, `next_question="datetime"`, and `open_questions=["datetime"]` so booking continues by asking only for date/time.',
            'Set `pending_question_act="ask_about_requested_slot"`, `pending_question_target="time"`, and `active_question_relation="ask_about_requested_slot"`.',
            'Keep `subject_kind="service"` and preserve the grounded service in `slots.service` or `referents.service`.',
            "$grounded_service_clause",
            "Do NOT ask the user to choose the service again and do NOT drop the promotions fact.",
            "Return corrected JSON only.",
        ),
    ),
    boundary_payload_templates=(
        _policy_core_generated_boundary_payload_template(
            "mixed_first_turn_location_service_fact_scope_boundary",
            intent="location",
            tool_action_hint="info",
            pack_refs=_policy_core_generated_value_ref("pack_refs"),
            slots=_policy_core_generated_value_ref("slots"),
            expected_reply_type=None,
            next_question=None,
            open_questions=[],
            goal=None,
            referents=_policy_core_generated_value_ref("referents"),
            subject_kind="service",
            capability="location",
            temporal_scope="none",
            alternate_datetime=None,
            resolution_mode="policy_fact",
            pending_question_act=None,
            pending_question_target=None,
            active_question_relation=None,
        ),
        _policy_core_generated_boundary_payload_template(
            "mixed_first_turn_location_service_fact_booking_followup_boundary",
            intent="location",
            tool_action_hint="info",
            pack_refs=_policy_core_generated_value_ref("pack_refs"),
            slots=_policy_core_generated_value_ref("slots"),
            expected_reply_type="time",
            next_question="datetime",
            open_questions=["datetime"],
            goal="booking",
            referents=_policy_core_generated_value_ref("referents"),
            subject_kind="service",
            capability="location",
            temporal_scope=_policy_core_generated_value_ref("temporal_scope"),
            alternate_datetime=_policy_core_generated_value_ref("alternate_datetime"),
            resolution_mode="policy_fact",
            pending_question_act=_policy_core_generated_value_ref("pending_question_act"),
            pending_question_target="time",
            active_question_relation=_policy_core_generated_value_ref("pending_question_act"),
        ),
        _policy_core_generated_boundary_payload_template(
            "mixed_first_turn_hours_location_booking_followup_boundary",
            intent=_policy_core_generated_value_ref("head_ref"),
            tool_action_hint="info",
            pack_refs=_policy_core_generated_value_ref("pack_refs"),
            slots={},
            expected_reply_type="service_choice",
            next_question="service",
            open_questions=["service"],
            goal="booking",
            referents={},
            subject_kind="general",
            capability=_policy_core_generated_value_ref("head_ref"),
            temporal_scope="none",
            alternate_datetime=None,
            resolution_mode="policy_fact",
            pending_question_act=None,
            pending_question_target=None,
            active_question_relation=None,
        ),
        _policy_core_generated_boundary_payload_template(
            "mixed_first_turn_hours_location_fact_scope_boundary",
            intent=_policy_core_generated_value_ref("head_ref"),
            tool_action_hint="info",
            pack_refs=_policy_core_generated_value_ref("pack_refs"),
            slots={},
            expected_reply_type=None,
            next_question=None,
            open_questions=[],
            goal=None,
            referents={},
            subject_kind="general",
            capability=_policy_core_generated_value_ref("head_ref"),
            temporal_scope="none",
            alternate_datetime=None,
            resolution_mode="policy_fact",
            pending_question_act=None,
            pending_question_target=None,
            active_question_relation=None,
        ),
        _policy_core_generated_boundary_payload_template(
            "mixed_first_turn_hours_service_fact_scope_boundary",
            intent="hours",
            tool_action_hint="info",
            pack_refs=_policy_core_generated_value_ref("pack_refs"),
            slots=_policy_core_generated_value_ref("slots"),
            expected_reply_type=None,
            next_question=None,
            open_questions=[],
            goal=None,
            referents=_policy_core_generated_value_ref("referents"),
            subject_kind="service",
            capability="hours",
            temporal_scope="none",
            alternate_datetime=None,
            resolution_mode="policy_fact",
            pending_question_act=None,
            pending_question_target=None,
            active_question_relation=None,
        ),
        _policy_core_generated_boundary_payload_template(
            "mixed_first_turn_hours_service_booking_followup_boundary",
            intent="hours",
            tool_action_hint="info",
            pack_refs=_policy_core_generated_value_ref("pack_refs"),
            slots=_policy_core_generated_value_ref("slots"),
            expected_reply_type="time",
            next_question="datetime",
            open_questions=["datetime"],
            goal="booking",
            referents=_policy_core_generated_value_ref("referents"),
            subject_kind="service",
            capability="hours",
            temporal_scope="none",
            alternate_datetime=None,
            resolution_mode="policy_fact",
            pending_question_act="ask_about_requested_slot",
            pending_question_target="time",
            active_question_relation="ask_about_requested_slot",
        ),
        _policy_core_generated_boundary_payload_template(
            "mixed_first_turn_hours_location_service_fact_scope_boundary",
            intent=_policy_core_generated_value_ref("head_ref"),
            tool_action_hint="info",
            pack_refs=_policy_core_generated_value_ref("pack_refs"),
            slots=_policy_core_generated_value_ref("slots"),
            expected_reply_type=None,
            next_question=None,
            open_questions=[],
            goal=None,
            referents=_policy_core_generated_value_ref("referents"),
            subject_kind="service",
            capability=_policy_core_generated_value_ref("head_ref"),
            temporal_scope="none",
            alternate_datetime=None,
            resolution_mode="policy_fact",
            pending_question_act=None,
            pending_question_target=None,
            active_question_relation=None,
        ),
        _policy_core_generated_boundary_payload_template(
            "mixed_first_turn_service_fact_booking_side_precedence_boundary",
            intent=_policy_core_generated_value_ref("expected_ref"),
            tool_action_hint="catalog.service_query",
            pack_refs=_policy_core_generated_value_ref("pack_refs"),
            slots=_policy_core_generated_value_ref("slots"),
            expected_reply_type="time",
            next_question="datetime",
            open_questions=["datetime"],
            goal="booking",
            referents=_policy_core_generated_value_ref("referents"),
            subject_kind="service",
            capability=_policy_core_generated_value_ref("expected_ref"),
            temporal_scope=_policy_core_generated_value_ref("temporal_scope"),
            alternate_datetime=_policy_core_generated_value_ref("alternate_datetime"),
            resolution_mode="policy_fact",
            pending_question_act=_policy_core_generated_value_ref("pending_question_act"),
            pending_question_target="time",
            active_question_relation=_policy_core_generated_value_ref("pending_question_act"),
        ),
        _policy_core_generated_boundary_payload_template(
            "service_query_multifact_scope_boundary",
            intent=_policy_core_generated_value_ref("head_intent"),
            tool_action_hint="catalog.service_query",
            pack_refs=_policy_core_generated_value_ref("pack_refs"),
            slots=_policy_core_generated_value_ref("slots"),
            expected_reply_type=None,
            next_question=None,
            open_questions=[],
            goal=None,
            referents=_policy_core_generated_value_ref("referents"),
            subject_kind="service",
            capability=_policy_core_generated_value_ref("head_ref"),
            temporal_scope="none",
            alternate_datetime=None,
            resolution_mode="policy_fact",
            pending_question_act=None,
            pending_question_target=None,
            active_question_relation=None,
        ),
        _policy_core_generated_boundary_payload_template(
            "service_query_multifact_booking_followup_boundary",
            intent=_policy_core_generated_value_ref("head_intent"),
            tool_action_hint="catalog.service_query",
            pack_refs=_policy_core_generated_value_ref("pack_refs"),
            slots=_policy_core_generated_value_ref("slots"),
            expected_reply_type="time",
            next_question="datetime",
            open_questions=["datetime"],
            goal="booking",
            referents=_policy_core_generated_value_ref("referents"),
            subject_kind="service",
            capability=_policy_core_generated_value_ref("head_ref"),
            temporal_scope=_policy_core_generated_value_ref("temporal_scope"),
            alternate_datetime=_policy_core_generated_value_ref("alternate_datetime"),
            resolution_mode="policy_fact",
            pending_question_act=_policy_core_generated_value_ref("pending_question_act"),
            pending_question_target="time",
            active_question_relation=_policy_core_generated_value_ref("pending_question_act"),
        ),
        _policy_core_generated_boundary_payload_template(
            "mixed_first_turn_promotions_precedence_fact_scope_boundary",
            intent="promotions",
            tool_action_hint="catalog.service_query",
            pack_refs=_policy_core_generated_value_ref("pack_refs"),
            slots=_policy_core_generated_value_ref("slots"),
            expected_reply_type=None,
            next_question=None,
            open_questions=[],
            goal=None,
            referents=_policy_core_generated_value_ref("referents"),
            subject_kind=_policy_core_generated_value_ref("subject_kind"),
            capability="promotions",
            temporal_scope="none",
            alternate_datetime=None,
            resolution_mode="policy_fact",
            pending_question_act=None,
            pending_question_target=None,
            active_question_relation=None,
        ),
        _policy_core_generated_boundary_payload_template(
            "promotions_booking_followup_boundary",
            intent="promotions",
            tool_action_hint="catalog.service_query",
            pack_refs=_policy_core_generated_value_ref("pack_refs"),
            slots={},
            expected_reply_type="service_choice",
            next_question="service",
            open_questions=["service"],
            goal="booking",
            referents={},
            subject_kind="general",
            capability="promotions",
            temporal_scope="none",
            alternate_datetime=None,
            resolution_mode="policy_fact",
            pending_question_act=None,
            pending_question_target=None,
            active_question_relation=None,
        ),
        _policy_core_generated_boundary_payload_template(
            "promotions_location_booking_followup_boundary",
            intent="promotions",
            tool_action_hint="catalog.service_query",
            pack_refs=_policy_core_generated_value_ref("pack_refs"),
            slots={},
            expected_reply_type="service_choice",
            next_question="service",
            open_questions=["service"],
            goal="booking",
            referents={},
            subject_kind="general",
            capability="promotions",
            temporal_scope="none",
            alternate_datetime=None,
            resolution_mode="policy_fact",
            pending_question_act=None,
            pending_question_target=None,
            active_question_relation=None,
        ),
        _policy_core_generated_boundary_payload_template(
            "promotions_grounded_service_booking_followup_boundary",
            intent="promotions",
            tool_action_hint="catalog.service_query",
            pack_refs=_policy_core_generated_value_ref("pack_refs"),
            slots=_policy_core_generated_value_ref("slots"),
            expected_reply_type="time",
            next_question="datetime",
            open_questions=["datetime"],
            goal="booking",
            referents=_policy_core_generated_value_ref("referents"),
            subject_kind="service",
            capability="promotions",
            temporal_scope="none",
            alternate_datetime=None,
            resolution_mode="policy_fact",
            pending_question_act="ask_about_requested_slot",
            pending_question_target="time",
            active_question_relation="ask_about_requested_slot",
        ),
    ),
)


def iter_policy_core_generated_contract_blocks() -> tuple[PolicyCoreGeneratedContractBlockV1, ...]:
    return (
        _BOOKING_PROGRESSION_CONTRACT_BLOCK,
        _BOOKING_CONTINUITY_INTERRUPT_CONTRACT_BLOCK,
        _MIXED_FIRST_TURN_FACT_CONTRACT_BLOCK,
    )


def policy_core_generated_contract_semantic_tokens() -> dict[str, frozenset[str]]:
    merged: dict[str, set[str]] = {}
    for block in iter_policy_core_generated_contract_blocks():
        for category, values in block.semantic_tokens.items():
            merged.setdefault(category, set()).update(
                value for value in values if isinstance(value, str) and value.strip()
            )
    return {category: frozenset(values) for category, values in merged.items()}


def iter_policy_core_generated_contract_repair_templates() -> tuple[PolicyCoreGeneratedRepairTemplateV1, ...]:
    templates: list[PolicyCoreGeneratedRepairTemplateV1] = []
    for block in iter_policy_core_generated_contract_blocks():
        templates.extend(block.repair_templates)
    return tuple(templates)


def policy_core_generated_contract_repair_template_ids() -> frozenset[str]:
    return frozenset(
        template.template_id for template in iter_policy_core_generated_contract_repair_templates()
    )


def iter_policy_core_generated_contract_boundary_payload_templates(
) -> tuple[PolicyCoreGeneratedBoundaryPayloadTemplateV1, ...]:
    templates: list[PolicyCoreGeneratedBoundaryPayloadTemplateV1] = []
    for block in iter_policy_core_generated_contract_blocks():
        templates.extend(block.boundary_payload_templates)
    return tuple(templates)


def policy_core_generated_contract_boundary_payload_template_ids() -> frozenset[str]:
    return frozenset(
        template.template_id
        for template in iter_policy_core_generated_contract_boundary_payload_templates()
    )


def render_policy_core_generated_contract_repair_template(
    template_id: str,
    **values: object,
) -> str:
    normalized_values = {key: "" if value is None else str(value) for key, value in values.items()}
    for template in iter_policy_core_generated_contract_repair_templates():
        if template.template_id != template_id:
            continue
        rendered_lines: list[str] = []
        for line in template.lines:
            rendered = Template(line).substitute(normalized_values).strip()
            if rendered:
                rendered_lines.append(rendered)
        return " ".join(rendered_lines)
    raise ValueError(f"Unknown policy-core generated contract repair template: {template_id}")


def _render_policy_core_generated_boundary_payload_value(
    template_value: Any,
    *,
    values: Mapping[str, Any],
    normalized_string_values: Mapping[str, str],
) -> Any:
    if isinstance(template_value, PolicyCoreGeneratedValueRefV1):
        if template_value.value_key not in values:
            raise ValueError(
                "Unknown policy-core generated boundary payload value: "
                f"{template_value.value_key}"
            )
        return deepcopy(values[template_value.value_key])
    if isinstance(template_value, str):
        return Template(template_value).substitute(normalized_string_values)
    if isinstance(template_value, tuple):
        return [
            _render_policy_core_generated_boundary_payload_value(
                item,
                values=values,
                normalized_string_values=normalized_string_values,
            )
            for item in template_value
        ]
    if isinstance(template_value, list):
        return [
            _render_policy_core_generated_boundary_payload_value(
                item,
                values=values,
                normalized_string_values=normalized_string_values,
            )
            for item in template_value
        ]
    if isinstance(template_value, dict):
        return {
            key: _render_policy_core_generated_boundary_payload_value(
                item,
                values=values,
                normalized_string_values=normalized_string_values,
            )
            for key, item in template_value.items()
        }
    return deepcopy(template_value)


def render_policy_core_generated_contract_boundary_payload_template(
    template_id: str,
    **values: object,
) -> dict[str, Any]:
    normalized_string_values = {
        key: "" if value is None else str(value) for key, value in values.items()
    }
    for template in iter_policy_core_generated_contract_boundary_payload_templates():
        if template.template_id != template_id:
            continue
        rendered = _render_policy_core_generated_boundary_payload_value(
            template.payload,
            values=values,
            normalized_string_values=normalized_string_values,
        )
        if not isinstance(rendered, dict):
            raise ValueError(
                "Policy-core generated boundary payload template did not render to a dict: "
                f"{template_id}"
            )
        return rendered
    raise ValueError(f"Unknown policy-core generated contract boundary payload template: {template_id}")


def _render_policy_core_generated_contract_blocks(*, compact: bool) -> str:
    parts: list[str] = []
    for block in iter_policy_core_generated_contract_blocks():
        rendered = block.compact_prompt_text if compact else block.full_prompt_text
        rendered = rendered.strip()
        if rendered:
            parts.append(rendered)
    return "\n".join(parts).strip()


def _inject_policy_core_generated_contract_blocks(prompt_text: str, *, compact: bool) -> str:
    normalized_prompt_text = prompt_text.strip()
    generated_block = _render_policy_core_generated_contract_blocks(compact=compact)
    if not generated_block:
        return normalized_prompt_text
    if _POLICY_CORE_GENERATED_CONTRACT_BLOCK_MARKER in normalized_prompt_text:
        return normalized_prompt_text.replace(_POLICY_CORE_GENERATED_CONTRACT_BLOCK_MARKER, generated_block)
    legacy_start = (
        _POLICY_CORE_LEGACY_COMPACT_BLOCK_START if compact else _POLICY_CORE_LEGACY_FULL_BLOCK_START
    )
    legacy_end = (
        _POLICY_CORE_LEGACY_COMPACT_BLOCK_END if compact else _POLICY_CORE_LEGACY_FULL_BLOCK_END
    )
    start_index = normalized_prompt_text.find(legacy_start)
    end_index = normalized_prompt_text.find(legacy_end)
    if start_index != -1 and end_index != -1 and end_index > start_index:
        return (
            normalized_prompt_text[:start_index]
            + generated_block
            + "\n"
            + normalized_prompt_text[end_index:]
        ).strip()
    return (normalized_prompt_text + "\n\n" + generated_block).strip()

_POLICY_CORE_PROMPT_FALLBACK = """# LLM Policy Core Prompt
Return JSON only (no markdown). Required fields: intent, action, tool_action_hint, pack_refs, slots, expected_reply_type, next_question, open_questions, needs_manager, risk_signals, language, confidence, reason, goal, entity_refs, referents, subject_kind, capability, temporal_scope, alternate_datetime, resolution_mode, pending_question_act, pending_question_target, active_question_relation, resolver_id, resolver_version.
Optional fields: pack_refs, slots, next_question, open_questions, needs_manager,
risk_signals, language, reason, goal, entity_refs, subject_kind, capability, temporal_scope,
alternate_datetime, resolution_mode, pending_question_act, pending_question_target, active_question_relation,
resolver_id, resolver_version.
Use tool_action_hint and pack_refs only from the allowed lists provided in the input.
tool_action_hint=consult is only valid for consult/media collect turns (action=collect,
expected_reply_type=media). Do not use action=fact with tool_action_hint=consult; bind factual
consultation/service-availability replies to info, catalog.service_query, catalog.location,
catalog.portfolio, or a calendar tool from allowed.tool_actions.
Use context.service_cards as pack-side service taxonomy hints. If the current message already
contains a concrete service phrase from those hints (or a close inflected/prepositional variant),
ground it through slots.service or referents.service and do not switch to collect just because
the phrase is not in base dictionary form.
If context.message_grounding_hints.service is present, treat that value as the canonical
current-turn service grounding hint derived from pack taxonomy for this user message. Echo it
through slots.service or referents.service when the turn stays grounded on that service. Do not
leave the service empty or keep missing-service collect if this hint already resolves the service.
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
If the current user asks whether a named service is available (for example "делаете пирсинг?",
"есть ли пирсинг?", or "можно ли на пирсинг?") and that service is not grounded by
context.service_cards or context.message_grounding_hints.service, treat the turn as a
service-availability FACT, not as booking collect. Return intent=services_overview or
intent=out_of_domain, action=fact, tool_action_hint=catalog.service_query,
pack_refs=[services_overview], subject_kind=service or general,
capability=other, resolution_mode=policy_fact, with no expected_reply_type,
next_question, open_questions, pending_question_act, pending_question_target, or
active_question_relation. Ground the service only from the current message surface: for
"делаете пирсинг?" use slots.service="пирсинг" / referents.service.value="пирсинг" or
leave service empty for a general overview; do not substitute a supported catalog service
such as "маникюр". If a later turn tries to book that unsupported/unconfirmed service
without choosing a supported service, keep FACT clarification/services overview and do not
treat plain contact as handoff context unless the user explicitly asks for a human.
Forbidden: action=collect, next_question=service, or the generic prompt "На какую услугу хотите записаться?"
for unsupported-service availability.
If active pending_question_contract expects datetime for a known service and the user fixes
a named specialist preference (for example "Мне нужно, чтобы мастер был Айгерим.",
"Хочу к Айгерим.", "Можно к Айгерим?"), keep action=collect and next_question=datetime,
but switch semantic axes to specialist follow-up: referents.specialist, subject_kind=specialist,
capability=bookability, resolution_mode=referent_followup, pending_question_act=null,
pending_question_target=specialist, active_question_relation=referent_followup.
Forbidden: generic subject_kind=service plus active_question_relation=ask_about_requested_slot,
or stale pending_question_act=slot_constraint, once referents.specialist is grounded.
pending_question_target must switch from time to specialist and active_question_relation must switch
from slot_constraint/ask_about_requested_slot to referent_followup.
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
If active pending_question_contract currently expects media but memory.profile.resume_pending_question_contract exists,
later fact-side side questions must preserve the booking resume contract from memory.profile.resume_pending_question_contract
instead of keeping expected_reply_type=media / next_question=media.
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
subject_kind=booking, capability=booking_manage. For cancel/reschedule/admin-confirm, return
action=handoff, tool_action_hint=handoff, needs_manager=true; the customer bot must not execute
calendar.cancel/calendar.reschedule. For pure check/verify without cancel/reschedule/admin-confirm,
use intent=check_booking or intent=verify_booking, action=fact, tool_action_hint=calendar.get_booking,
and keep the governed lookup follow-up (name when customer referent is missing, datetime when customer is already grounded).
Use handoff only if the user explicitly asks to contact a manager/human or safety/business policy requires it.
Do NOT emit intent=other, tool_action_hint=info, capability=bookability, or the generic
reply "Я уточню это для вас." for that interrupt family.
If active booking continuity still expects datetime, memory already carries a day/date context,
and the current message is still only a generic availability question (for example
"Когда можно записаться?", "Какое время доступно?", "На какое время свободно?"),
keep the turn on the canonical requested-slot owner:
intent=booking, action=collect, tool_action_hint=collect, subject_kind=booking,
pending_question_act=ask_about_requested_slot, pending_question_target=time,
active_question_relation=ask_about_requested_slot. Preserve carried alternate_datetime and temporal_scope exactly;
if memory already carries alternate_datetime="завтра вечером", keep alternate_datetime="завтра вечером"
and temporal_scope=day instead of dropping alternate_datetime to null.
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
If a standalone first turn explicitly asks working hours and a grounded
non-promotions service fact, and booking is only a side request (for example
"Вы сегодня работаете и сколько стоит маникюр, можно записаться на 7?" or
"До скольки открыты и сколько длится педикюр, можно записаться?"), keep
hours as the head fact scope: intent=hours, action=fact, tool_action_hint=info,
grounded service referent, subject_kind=service, capability=hours,
resolution_mode=policy_fact, goal=booking, and exact pack refs such as
[hours, pricing] or [hours, duration]. Preserve booking continuation instead of
clearing it: expected_reply_type=time, next_question=datetime,
open_questions=[datetime], pending_question_target=time, and a booking
follow-up relation. Do NOT collapse this family to pricing-only/duration-only,
do NOT drop hours, and do NOT clear the booking follow-up only because the turn
also asks to book.
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
services_overview is allowed only when the current message explicitly asks service
presence ("какие услуги", "занимаетесь", "делаете", etc.). If the user asked only
hours + location + pricing/duration/promotions, do NOT add services_overview by
analogy to the nearby example. Forbidden: "Вы сегодня работаете, где вы
находитесь и сколько стоит маникюр?" -> [hours, location, pricing,
services_overview].
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
duration, without a booking side ask (for example "Где вы находитесь и сколько
стоит маникюр?" or "Сколько стоит маникюр, сколько длится и где находитесь?") —
keep location/address as the head fact scope. Return intent=location, action=fact,
tool_action_hint=info, grounded service referent, subject_kind=service,
capability=location, resolution_mode=policy_fact, and exact pack refs:
[location, services_overview] for service presence, [location, pricing] for price,
[location, duration] for duration, [location, pricing, duration] when both price and
duration are explicitly requested. services_overview is allowed only when the
current message explicitly asks service presence; do NOT add it for plain
location + pricing/duration. Clear standalone follow-up fields. Do NOT invent
hours, do NOT
switch this turn into booking collect, do NOT answer only the service fact without
location, and do NOT add services_overview without an explicit service-presence
question.
If the same standalone first turn explicitly asks about location/address, a grounded
service fact, and also adds booking as a side request (for example "Где вы
находитесь и сколько длится педикюр, можно записаться завтра вечером?" or
"Сколько стоит маникюр, сколько длится, где находитесь и можно записаться?"),
keep location/address as the head fact scope and preserve booking continuation in
the same turn: intent=location, action=fact, tool_action_hint=info, grounded
service referent, subject_kind=service, capability=location,
resolution_mode=policy_fact, goal=booking, exact pack refs such as
[location, pricing], [location, duration], or [location, pricing, duration],
expected_reply_type=time, next_question=datetime, open_questions=[datetime],
pending_question_target=time, and a booking follow-up relation. Do NOT collapse
this family to fact-only, do NOT clear booking follow-up only because location
remains the head intent, and do NOT add services_overview without an explicit
service-presence question.
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
If a standalone turn explicitly asks multiple grounded service fact families and
booking is only a side request — with or without a temporal clue (for example "Сколько стоит
маникюр и сколько длится, можно записаться завтра вечером?", "Сколько стоит
педикюр и сколько длится, можно записаться сегодня после 6?", "Кто делает
маникюр и как с вами связаться, можно записаться?", or "Кто делает маникюр и
как с вами связаться, хочу записаться."), keep the full multifact service scope
and booking continuation in one fact turn. This rule applies only to pure
service-fact turns: if the same message also explicitly asks location/address,
hours, or promotions, do NOT keep pricing / duration / master as the head by
analogy; use the mixed-fact precedence rule below and keep the general fact
head. Explicit contact or parking side asks stay inside the same pure
service-fact owner scope and do not cancel this multifact booking-followup
family: action=fact, tool_action_hint=catalog.service_query, exact pack_refs such
as [pricing, duration], [master, contact], or [master, parking], grounded
service referent, subject_kind=service, resolution_mode=policy_fact,
goal=booking, expected_reply_type=time, next_question=datetime, open_questions=[datetime],
pending_question_target=time. If the current message already grounds a partial slot clue,
use pending_question_act=slot_constraint and active_question_relation=slot_constraint;
otherwise use pending_question_act=ask_about_requested_slot and
active_question_relation=ask_about_requested_slot. Do NOT leave any of those follow-up
fields empty, do NOT collapse this family to fact-only, do NOT clear booking
follow-up only because the head intent remains factual, and do NOT clear booking
follow-up only because the same pure service-fact turn explicitly asked contact
or parking.
If a standalone first turn explicitly asks for a grounded service fact and only adds
booking as a side request — even with a concrete temporal clue (for example
"Сколько стоит педикюр и можно завтра в 6?", "Сколько длится педикюр и можно завтра
в 6?", or "Сколько стоит маникюр, можно записаться завтра вечером?") — keep the
service fact as the head intent and preserve booking continuation. Return intent=pricing
or intent=duration from the current message, action=fact, tool_action_hint=catalog.service_query,
exact pack_refs=[pricing] or pack_refs=[duration], grounded service referent,
subject_kind=service, matching capability, resolution_mode=policy_fact, goal=booking,
expected_reply_type=time, next_question=datetime, open_questions=[datetime],
pending_question_target=time, and a booking follow-up relation. Do NOT switch this
turn into booking collect, calendar.book_slot, a customer-name question, or a
fact-only reply without booking follow-up.
For standalone promotions-first mixed turns that are not one of the explicit
working-hours-first mixed families above, promotions/discounts is the only
allowed head intent. Even if the same message also asks to book, already grounds
a service, or asks for address/location/contact/parking, keep
intent=promotions, capability=promotions, action=fact, and
tool_action_hint=catalog.service_query. Encode the side asks only through
pack_refs, goal, expected_reply_type, next_question, open_questions, and the
pending-question contract. Do NOT use intent=booking, intent=location,
intent=pricing, intent=consult, or intent=other for this family.
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
capability=bookability, resolution_mode=direct, pending_question_act=fill_requested_slot, pending_question_target=time, active_question_relation=fill_requested_slot,
slots.datetime=<grounded datetime surface>, alternate_datetime=<grounded datetime surface>, temporal_scope=specific_time,
expected_reply_type=name, next_question=name, open_questions=[name]. Preserve the grounded service. This is still a collect progression, not a live calendar commit: do NOT use resolution_mode=live_calendar and do NOT emit calendar.book_slot before the customer name is grounded.
Mirror the exact datetime surface into both slots.datetime and alternate_datetime: do NOT leave alternate_datetime null once the current message already provided the exact slot. That duplication is required, not redundant. For weekday + clock-time surfaces such as "пятницу в 15:30", still use temporal_scope=specific_time instead of weekday.
If the user asks for booking availability with a day/date clue but no service is grounded in the current message
or canonical carry-over (for example "На завтра есть время?" or "Есть ли окно на сегодня?"),
do NOT invent slots.service or referents.service and do NOT jump to slot_constraint.
Keep booking ownership, but ask for the missing service first:
intent=booking, action=collect, tool_action_hint=collect, capability=bookability,
subject_kind=general, resolution_mode=clarify_missing_subject,
expected_reply_type=service_choice, next_question=service, open_questions=[service].
You may preserve the grounded temporal clue through temporal_scope and optional alternate_datetime,
but clear pending_question_act/pending_question_target/active_question_relation until the service is grounded.
If the service is not actually grounded, slots.service and referents.service must stay empty.
Do NOT widen a single day/daypart clue like "завтра" to date_range; keep the precise grounded temporal_scope.
If the current user asks whether a named service is available (for example "делаете пирсинг?",
"есть ли пирсинг?", or "можно ли на пирсинг?") and that service is not grounded by
context.service_cards or context.message_grounding_hints.service, this service availability
FACT overrides missing-service booking collect: intent=services_overview or out_of_domain,
action=fact, tool_action_hint=catalog.service_query, pack_refs=[services_overview],
capability=other, resolution_mode=policy_fact, and no follow-up contract. Ground the
service only from the current message surface (for "делаете пирсинг?" use "пирсинг") or
leave it empty for a general overview; do not substitute a supported catalog service.
If a later turn tries to book that unsupported/unconfirmed service without choosing a supported
service, keep FACT clarification/services overview and do not treat plain contact as handoff context
unless the user explicitly asks for a human.
Forbidden: action=collect, next_question=service, or the generic prompt "На какую услугу хотите записаться?"
for unsupported-service availability.
If active booking continuity still expects the missing service, memory already carries an exact requested datetime
(temporal_scope=specific_time plus non-null carried alternate_datetime), and the current fact-side question
itself grounds that service (for example "Сколько стоит маникюр?", "Какие скидки на маникюр?",
"Сколько длится маникюр?", or "Кто делает маникюр?"), answer the requested fact family on this same turn
but advance the booking continuation immediately to customer-name collect:
keep the current fact intent/capability/tool family, ground referents.service or slots.service from the current
message / context.message_grounding_hints.service, keep goal=booking, keep resolution_mode=policy_fact,
preserve alternate_datetime and temporal_scope=specific_time,
and set expected_reply_type=name, next_question=name, open_questions=[name],
pending_question_act=fill_requested_slot, pending_question_target=time,
active_question_relation=generic_info_interrupt.
Concrete example: carried alternate_datetime="на завтра в 18:00" + "Кто делает маникюр?" =>
intent=master_query, action=fact, tool_action_hint=info, pack_refs=[master],
goal=booking, resolution_mode=policy_fact,
expected_reply_type=name, pending_question_act=fill_requested_slot,
pending_question_target=time, active_question_relation=generic_info_interrupt.
Concrete example: carried alternate_datetime="пятницу в 15:30" + "Есть ли акции на маникюр?" =>
intent=promotions, action=fact, tool_action_hint=catalog.service_query, pack_refs=[promotions],
goal=booking, resolution_mode=policy_fact, expected_reply_type=name,
pending_question_act=fill_requested_slot, pending_question_target=time,
active_question_relation=generic_info_interrupt.
Do NOT keep expected_reply_type=service_choice, do NOT ask for the service again, do NOT reopen time,
do NOT clear goal/pending_question_act/pending_question_target on this exact interrupt family,
and do NOT switch this fact interrupt to resolution_mode=direct.
If active booking continuity still expects datetime and the user gives a partial candidate slot
(for example "А как насчет пятницы на утро?", "Можно после 17:00?", "Давайте на завтра вечером.", or "У вас есть время на сегодня?"),
keep the turn under booking ownership but tighten the follow-up into a slot constraint:
intent=booking, action=collect, tool_action_hint=collect, subject_kind=booking,
capability=bookability, resolution_mode=direct,
pending_question_act=slot_constraint, pending_question_target=time,
active_question_relation=slot_constraint, alternate_datetime=<grounded candidate slot>,
temporal_scope=<grounded non-none scope>,
expected_reply_type=time, next_question=datetime, open_questions=[datetime].
Concrete example: "Хочу записаться на маникюр завтра вечером." => alternate_datetime="завтра вечером"
and the turn still waits for an exact time.
Do NOT fall back to the generic "На какую дату и время вам удобно?" prompt even if the previous JSON left temporal_scope as none.
Do NOT revert this narrowed turn to resolution_mode=ask_about_requested_slot once the current message already grounded the partial slot clue.
If specialist preference is already grounded from earlier turns, preserve referents.specialist but keep subject_kind=booking, active_question_relation=slot_constraint, and do not revert resolution_mode to referent_followup.
Keep alternate_datetime in the user's message surface; do not translate "завтра вечером" into "tomorrow evening".
If active booking continuity still expects datetime and the user provides their own name or contact out of order
(for example "Меня зовут Амина.", "Я Амина.", "Моё имя Амина Ахметова.", a short bare self-name reply like "Аружан" / "Айша",
phone-only "87015705555" / "7015705555", or "Айгуль 87073334455"),
keep booking ownership and preserve the active time follow-up contract:
intent=booking, action=collect, tool_action_hint=collect, goal=booking, subject_kind=booking,
expected_reply_type=time, next_question=datetime, open_questions=[datetime].
Keep the carried pending_question_act/pending_question_target/active_question_relation,
and keep the carried alternate_datetime/temporal_scope when the current message adds no new temporal clue,
but ground the customer canonically through slots.name=<customer name> and/or slots.phone=<phone>.
For a bare reply like "Аружан" or phone-only "87015705555" while alternate_datetime is already "завтра вечером", keep that same
alternate_datetime and temporal_scope instead of dropping them.
Acknowledgements/confirmations such as "да", "ок", "хорошо", or "да подтверждаю" are not customer names and must not rewrite slots.name or referents.customer.
Do NOT revert this turn to specialist referent-followup just because specialist preference is already carried.
Do NOT switch this turn to booking_manage, handoff, or planner_degrade while exact time is still missing.
Bare human-name replies without an explicit specialist marker still belong to customer-name carryover, not specialist switching.
Do NOT switch this turn to booking_manage and do NOT commit the booking while exact time is still missing.
If active booking continuity already carries day/date context, customer name is already grounded,
and the current message now gives an explicit clock time such as "Давайте в 18:00." or "Тогда в 11:30.",
this completes the booking input set rather than another slot_constraint collect:
intent=booking, action=fact, tool_action_hint=calendar.book_slot, subject_kind=booking,
capability=bookability, resolution_mode=live_calendar.
Preserve slots.service and slots.name, and ground slots.datetime by combining the current explicit time
with the carried day/date context from memory. Clear stale collect follow-up fields instead of keeping
expected_reply_type/next_question/open_questions/pending_question_act/pending_question_target/active_question_relation.
slots.datetime and alternate_datetime must mirror the same executor-parseable exact-time surface, for example
"завтра 18:00" or "завтра в 18:00"; do NOT keep stale daypart wording such as "завтра вечером в 18:00".
Concrete example: carried alternate_datetime="завтра вечером" plus customer name already grounded and
current message "Давайте в 18:00." => action=fact, tool_action_hint=calendar.book_slot,
slots.datetime="завтра 18:00" (or "завтра в 18:00") and the same exact surface in alternate_datetime.
If active booking continuity already has all required booking inputs in memory (service, executor-parseable exact datetime,
customer name, and contact phone), and the current message is only a confirmation such as "да", "ок",
or "подтверждаю", this is booking commit rather than customer-name carryover or planner_degrade:
intent=booking, action=fact, tool_action_hint=calendar.book_slot, subject_kind=booking,
capability=bookability, resolution_mode=live_calendar.
Carry slots.service, slots.datetime, slots.name, and slots.phone from canonical memory, clear stale collect axes,
and keep temporal_scope=specific_time. Mirror slots.datetime into alternate_datetime when possible; if alternate_datetime
is absent, slots.datetime remains the executor canonical datetime for commit.
If active booking continuity still expects datetime, memory already carries a day/date context,
and the current message is still only a generic availability question such as
"Когда можно записаться?", "Какое время доступно?", or "На какое время свободно?",
keep the canonical requested-slot owner instead of over-tightening to slot_constraint:
intent=booking, action=collect, tool_action_hint=collect, subject_kind=booking,
pending_question_act=ask_about_requested_slot, pending_question_target=time,
active_question_relation=ask_about_requested_slot, expected_reply_type=time,
next_question=datetime, open_questions=[datetime]. Preserve carried alternate_datetime and temporal_scope exactly:
if memory already carries alternate_datetime="завтра вечером", keep alternate_datetime="завтра вечером"
and temporal_scope=day instead of dropping alternate_datetime to null.
Do NOT switch to hours/location fact, do NOT infer a new slot from carried context alone, and do NOT replace a carried alternate_datetime with null.
If active booking continuity still expects datetime and the user fixes a named specialist preference
(for example "Мне нужен мастер Айгерим.", "Хочу к Айгерим.", "Можно к Айгерим?", or a short directional reply like "К Айдане."),
keep the turn under booking ownership and preserve time continuity:
intent=booking, action=collect, tool_action_hint=collect,
subject_kind=specialist, capability=bookability, resolution_mode=referent_followup,
pending_question_act=null, pending_question_target=specialist, active_question_relation=referent_followup,
expected_reply_type=time, next_question=datetime, open_questions=[datetime].
Ground the specialist through referents.specialist. Do NOT keep generic
subject_kind=service, active_question_relation=ask_about_requested_slot, or pending_question_act=slot_constraint
once the specialist is grounded.
Do NOT write the specialist marker into `slots.name`; `slots.name` is only for the customer name.
pending_question_target must switch from time to specialist once the named specialist is grounded.
If active booking continuity still expects datetime, a date/day is already carried in memory, and the user now supplies
an explicit clock time after that specialist/media carryover (for example "Можно на 17:45?", "А в 16:45 можно?",
"Давайте в 18:00."),
advance the slot-fill instead of asking for datetime again:
intent=booking, action=collect, tool_action_hint=collect,
subject_kind=booking, capability=bookability, resolution_mode=direct,
expected_reply_type=name, next_question=name, open_questions=[name],
pending_question_act=fill_requested_slot, pending_question_target=time,
active_question_relation=fill_requested_slot.
Ground the completed datetime into both slots.datetime and alternate_datetime by combining the carried day/date context
with the current exact clock time in the user's language surface. Preserve grounded service/specialist referents.
Keep one executor-parseable exact-time surface such as "завтра 17:45" or "завтра в 17:45"; do NOT keep
stale daypart wording once the exact clock time is grounded.
Do NOT keep expected_reply_type=time, next_question=datetime, pending_question_act=slot_constraint,
pending_question_target=specialist, active_question_relation=referent_followup, bare time-only alternate_datetime,
or translated carry-over such as "tomorrow 16:45" once the requested time is already grounded.
If slots.datetime is already grounded from the current turn, expected_reply_type can no longer stay time.
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
If a later post-media turn asks a fact-side side question instead of sending media
(for example "Сколько это длится?", "Есть ли парковка?", or "Кто делает маникюр?"),
reclassify it to the exact fact family but preserve the booking resume contract from
memory.profile.resume_pending_question_contract. Do NOT keep expected_reply_type=media,
next_question=media, or open_questions=[media] for these later fact interrupts.
If that later post-media turn already supplies a concrete clock time (for example "Можно на 17:45?" or "А в 16:45 можно?"),
advance the booking slot-fill instead of restoring the generic datetime prompt:
subject_kind=booking, capability=bookability, resolution_mode=direct,
expected_reply_type=name, next_question=name, open_questions=[name],
pending_question_act=fill_requested_slot, pending_question_target=time,
active_question_relation=fill_requested_slot.
Ground the completed datetime into both slots.datetime and alternate_datetime in the user's language surface.
Preserve grounded service/specialist referents and do NOT keep pending_question_target=specialist,
bare time-only alternate_datetime, or translated carry-over.
If slots.datetime is already grounded from the current turn, expected_reply_type can no longer stay time.
For generic info interrupt during active booking continuity, answer on fact path and preserve the active follow-up contract.
For check_booking/verify_booking without booking_ref, keep action=fact and tool_action_hint=calendar.get_booking.
If customer referent is missing, use expected_reply_type=name, next_question=name, open_questions=[name].
If customer referent is present but booking reference/time is still missing, use expected_reply_type=time, next_question=datetime, open_questions=[datetime].
For cancel/reschedule/admin-confirm requests, including grounded booking_ref cases
(for example "Тогда отмените запись.", "Отмените запись.", or "Перенесите на пятницу"),
do NOT execute calendar.cancel or calendar.reschedule from customer chat. Return action=handoff,
tool_action_hint=handoff, needs_manager=true, subject_kind=booking, capability=booking_manage,
preserve booking_ref/customer/contact context, and leave expected_reply_type / next_question / open_questions empty.
If booking_manage/admin-confirmation handoff context is already active and the next user turn only
adds service/date/time/name/phone details, keep action=handoff and capability=booking_manage;
store those details as context for the admin and do not switch to a new booking collect.
Do not turn active follow-up info/booking interrupts into handoff unless the user explicitly asks for a human or safety/business policy requires it.
Use exact fact scope:
- pricing -> catalog.service_query with pack_refs=[pricing]
- duration -> catalog.service_query with pack_refs=[duration]
- promotions -> catalog.service_query with pack_refs=[promotions]
- master_query -> info with pack_refs=[master], capability=master
- live_availability -> catalog.service_query with pack_refs=[master]
- standalone service-fact turns with explicit contact/parking side facts preserve those refs in the same owner scope
- location-only -> catalog.location with pack_refs=[location]
- hours-only -> catalog.location with pack_refs=[hours]
- parking-only -> catalog.location with pack_refs=[parking]
{{GENERATED_MIXED_FIRST_TURN_FACT_CONTRACT_BLOCK}}
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
    prompt_text = _inject_policy_core_generated_contract_blocks(prompt_text, compact=False)
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
    prompt_text = _inject_policy_core_generated_contract_blocks(prompt_text, compact=True)
    _POLICY_CORE_COMPACT_PROMPT_CACHE = PolicyCorePromptSnapshotV1(
        prompt_text=prompt_text,
        source=source,
        fallback_used=fallback_used,
    )
    return _POLICY_CORE_COMPACT_PROMPT_CACHE


__all__ = [
    "PolicyCoreBookingInfoInterruptVariantV1",
    "PolicyCoreGeneratedBoundaryPayloadTemplateV1",
    "PolicyCoreGeneratedContractBlockV1",
    "PolicyCoreGeneratedRepairTemplateV1",
    "PolicyCoreGeneratedValueRefV1",
    "PolicyCorePromptSnapshotV1",
    "iter_policy_core_booking_info_interrupt_variants",
    "iter_policy_core_generated_contract_boundary_payload_templates",
    "iter_policy_core_generated_contract_blocks",
    "iter_policy_core_generated_contract_repair_templates",
    "load_policy_core_compact_prompt_snapshot",
    "load_policy_core_prompt_snapshot",
    "policy_core_generated_contract_boundary_payload_template_ids",
    "policy_core_generated_contract_repair_template_ids",
    "policy_core_generated_contract_semantic_tokens",
    "resolve_policy_core_booking_info_interrupt_signature",
    "resolve_policy_core_booking_info_interrupt_variant",
    "render_policy_core_generated_contract_boundary_payload_template",
    "render_policy_core_generated_contract_repair_template",
]
