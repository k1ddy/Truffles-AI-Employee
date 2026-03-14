#!/usr/bin/env python3
"""Generate booking dialog scenarios for LLM/runtime quality checks."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - optional in minimal runtimes
    yaml = None

_API_ROOT = Path(__file__).resolve().parents[1] / "truffles-api"
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from app.services.scenario_contract_compiler import (
    compile_active_time_specialist_followup_expectations,
)

SERVICES = [
    "маникюр",
    "педикюр",
    "стрижку",
    "окрашивание",
    "брови и ресницы",
    "депиляцию",
    "уход за лицом",
]

MASTERS = ["Алия", "Айжан", "Мария"]
NAMES = ["Лена", "Айгуль", "Амина", "Катя", "Динара", "Марина"]
PHONES = [
    "+7 701 111 22 33",
    "+7 702 222 33 44",
    "+7 707 333 44 55",
    "+7 778 444 55 66",
]

DAYS = ["в пятницу", "в субботу", "в воскресенье", "завтра", "на выходных"]
TIME_RANGES = ["после 18", "после 19", "вечером", "в районе 17:30"]
TIME_EXACT = ["на 19:00", "на 18:30", "на 20:00", "на 17:45"]
REFERENCE_MEDIA_IMAGE_PATH = "/home/zhan/TrufflesLogoClear.png"
REFERENCE_MEDIA_IMAGE_NAME = "TrufflesLogoClear.png"

GREETINGS = ["Привет", "Здравствуйте", "Добрый день", "Салеметсиз бе"]
EXPECT_INFO_SECTIONS = {
    "price": ["pricing", "price", "payment_info", "payment"],
    "location": ["address", "location"],
    "hours": ["hours", "working_hours", "schedule"],
    "promo": ["discounts", "discount", "promo", "promotion"],
    "duration": ["duration", "service_duration"],
    "parking": ["parking"],
    "master": ["master", "specialist"],
}
EXPECT_ACTION_BY_TAG = {
    "handoff": ["booking_escalated", "escalate", "handoff"],
}
EXPECT_REPLY_TYPE_BY_TAG = {
    "booking": "time",
    "time": "name",
    "ask_about_requested_slot": "time",
    "slot_constraint": "time",
    "slot_compare": "time",
    "mixed_fill_plus_question": "time",
}
PENDING_QUESTION_TAGS = {
    "ask_about_requested_slot",
    "slot_constraint",
    "slot_compare",
    "mixed_fill_plus_question",
}
TARGETED_PENDING_QUESTION_TAGS = {
    "ask_about_requested_slot",
    "slot_constraint",
    "slot_compare",
}
PENDING_QUESTION_CONTEXT_PRESERVE_TAGS = {
    "info",
    "media",
    "price",
    "location",
    "hours",
    "promo",
    "duration",
    "parking",
    "master",
    "wrong_slot",
    "interrupt",
}
ACTIVE_PENDING_QUESTION_INFO_INTERRUPT_TAGS = {
    "info",
    "price",
    "duration",
    "hours",
    "location",
    "parking",
    "promo",
}
EXPECT_META_ANY_BY_TAG = {
    "ask_about_requested_slot": {
        "pending_question_act": ["ask_about_requested_slot"],
        "pending_question_target": ["time"],
        "expected_reply_type": ["time"],
    },
    "slot_constraint": {
        "pending_question_act": ["slot_constraint"],
        "pending_question_target": ["time"],
        "expected_reply_type": ["time"],
    },
    "slot_compare": {
        "pending_question_act": ["slot_compare"],
        "pending_question_target": ["time"],
        "expected_reply_type": ["time"],
    },
    "mixed_fill_plus_question": {
        "expected_reply_type": ["time"],
    },
}
EXPECT_TRACE_CONTAINS_BY_TAG = {
    "ask_about_requested_slot": [
        {
            "stage": "pending_question_interaction",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
        },
        {"stage": "question_contract", "expected_reply_type": "time"},
    ],
    "slot_constraint": [
        {
            "stage": "pending_question_interaction",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
        },
        {"stage": "question_contract", "expected_reply_type": "time"},
    ],
    "slot_compare": [
        {
            "stage": "pending_question_interaction",
            "pending_question_act": "slot_compare",
            "pending_question_target": "time",
        },
        {"stage": "question_contract", "expected_reply_type": "time"},
    ],
    "mixed_fill_plus_question": [
        {"stage": "question_contract", "expected_reply_type": "time"},
    ],
}
EXPECT_STATE_BY_TAG = {
    "handoff": "pending",
}
CANONICAL_EXPECT_ACTIONS = sorted(
    {action for actions in EXPECT_ACTION_BY_TAG.values() for action in actions}
)
CANONICAL_EXPECT_STATES = sorted(
    set(EXPECT_STATE_BY_TAG.values()) | {"bot_active", "pending", "manager_active"}
)
CANONICAL_EXPECT_REPLY_TYPES = sorted(
    set(EXPECT_REPLY_TYPE_BY_TAG.values()) | {"service_choice"}
)
CANONICAL_EXPECT_INFO_SECTIONS = sorted(
    {section for sections in EXPECT_INFO_SECTIONS.values() for section in sections}
)
REQUIRED_LLM_TAGS = ["booking", "time", "name"]
REQUIRED_BOOKING_CONFIRM_TAGS = ["check_booking", "confirm"]
REQUIRED_HANDOFF_TAGS = ["handoff"]
DEFAULT_REFERENCE_IMAGE_PATH = "/home/zhan/TrufflesLogoClear.png"
DEFAULT_REFERENCE_IMAGE_URL = "https://app.chatflow.kz/static/demo/reference.jpg"
LANGUAGE_PROFILE_CHOICES = ("ru", "kk", "mixed", "mixed_translit")
SEMANTIC_VARIATION_PROFILE_CHOICES = ("canonical", "synonym")
SLOT_FORMAT_PROFILE_CHOICES = ("canonical", "variant")
SURFACE_NOISE_PROFILE_CHOICES = ("clean", "typo")
REQUIRED_LLM_TURNS = {
    "booking": {"text": "{greet}, хочу записаться на {service}.", "tags": ["booking"]},
    "time": {"text": "Можно {time_exact}?", "tags": ["time"]},
    "name": {"text": "Меня зовут {name}.", "tags": ["name"]},
    "check_booking": {
        "text": "Проверьте, пожалуйста, мою запись на {day} {time_exact}.",
        "tags": ["check_booking"],
    },
    "confirm": {"text": "Да, подтверждаю.", "tags": ["confirm"]},
    "handoff": {
        "text": "Можно связаться с менеджером?",
        "tags": ["handoff", "human"],
        "expect": {"action": "handoff", "state": "pending"},
    },
}


def _clean_api_key(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = str(value).strip().strip('"').strip("'")
    return cleaned or None


def _load_env_file(path: str | None) -> dict[str, str]:
    if not path:
        return {}
    file_path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(file_path):
        return {}
    env: dict[str, str] = {}
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export ") :].strip()
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                cleaned_key = key.strip()
                cleaned_value = value.strip().strip('"').strip("'")
                if cleaned_value.startswith("${") and cleaned_value.endswith("}") and len(cleaned_value) > 3:
                    ref_key = cleaned_value[2:-1].strip()
                    if ref_key:
                        cleaned_value = env.get(ref_key) or os.environ.get(ref_key) or cleaned_value
                elif cleaned_value.startswith("$") and len(cleaned_value) > 1:
                    ref_key = cleaned_value[1:].strip()
                    if ref_key and all(ch.isalnum() or ch == "_" for ch in ref_key):
                        cleaned_value = env.get(ref_key) or os.environ.get(ref_key) or cleaned_value
                env[cleaned_key] = cleaned_value
    except Exception:
        return {}
    return env


def _openai_key_candidate_env_files() -> list[str]:
    script_file = globals().get("__file__")
    if script_file:
        script_dir = os.path.dirname(os.path.abspath(script_file))
    else:
        script_dir = os.path.join(os.getcwd(), "scripts")
    repo_root = os.path.dirname(script_dir)
    candidates = [
        os.environ.get("TRUFFLES_API_ENV_FILE"),
        os.environ.get("ENV_FILE"),
        os.path.join(os.getcwd(), "truffles-api", ".env"),
        os.path.join(os.getcwd(), ".env"),
        os.path.join(repo_root, "truffles-api", ".env"),
        os.path.join(repo_root, ".env"),
        "/home/zhan/truffles-main/truffles-api/.env",
        "/home/zhan/infrastructure/.env",
    ]
    unique: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        if not item:
            continue
        path = os.path.abspath(os.path.expanduser(str(item)))
        if path in seen:
            continue
        seen.add(path)
        unique.append(path)
    return unique


def _resolve_openai_api_key(explicit: str | None = None) -> tuple[str | None, str | None]:
    key_aliases = (
        "OPENAI_API_KEY",
        "OPENAI_KEY",
        "OPENAI_API_TOKEN",
        "OPENAI_TOKEN",
        "LLM_API_KEY",
        "OPENAI_JUDGE_API_KEY",
        "JUDGE_API_KEY",
    )

    def _alias_source(prefix: str, alias: str) -> str:
        if alias == "OPENAI_API_KEY":
            return prefix
        return f"{prefix}:{alias}"

    key = _clean_api_key(explicit)
    if key:
        return key, "explicit"
    for alias in key_aliases:
        env_key = _clean_api_key(os.environ.get(alias))
        if env_key:
            return env_key, _alias_source("env:OPENAI_API_KEY", alias)
    for env_path in _openai_key_candidate_env_files():
        env_map = _load_env_file(env_path)
        for alias in key_aliases:
            file_key = _clean_api_key(env_map.get(alias))
            if file_key:
                return file_key, _alias_source(f"env_file:{env_path}", alias)
    return None, None


def _required_llm_tags(coverage: list[str] | None) -> list[str]:
    required = list(REQUIRED_LLM_TAGS)
    coverage_tokens = {
        str(item).strip().lower()
        for item in (coverage or [])
        if isinstance(item, str) and str(item).strip()
    }
    if "handoff" in coverage_tokens:
        for tag in REQUIRED_HANDOFF_TAGS:
            if tag not in required:
                required.append(tag)
    return required


def _script_repo_root() -> Path:
    script_file = globals().get("__file__")
    if script_file:
        return Path(script_file).resolve().parents[1]
    return Path.cwd()


def _dedupe_strings(items: list[Any]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        token = text.casefold()
        if token in seen:
            continue
        seen.add(token)
        normalized.append(text)
    return normalized


def _load_json_file(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    resolved = Path(os.path.abspath(os.path.expanduser(path)))
    if not resolved.exists():
        return None
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _load_yaml_file(path: Path) -> dict[str, Any] | None:
    if yaml is None or not path.exists():
        return None
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _extract_service_names_from_truth(truth: dict[str, Any] | None) -> list[str]:
    if not isinstance(truth, dict):
        return []
    catalog = truth.get("services_catalog")
    raw_services: list[Any] = []
    if isinstance(catalog, dict):
        services = catalog.get("services")
        if isinstance(services, list):
            raw_services.extend(services)
        suggestions = catalog.get("suggestions")
        if isinstance(suggestions, list):
            raw_services.extend(suggestions)
    elif isinstance(catalog, list):
        raw_services.extend(catalog)
    names: list[Any] = []
    for item in raw_services:
        if isinstance(item, dict):
            names.append(item.get("name"))
        else:
            names.append(item)
    return _dedupe_strings(names)


def _extract_specialist_names_from_truth(truth: dict[str, Any] | None) -> list[str]:
    if not isinstance(truth, dict):
        return []
    raw_names: list[Any] = []
    masters_catalog = truth.get("masters_catalog")
    if isinstance(masters_catalog, dict):
        specialists = masters_catalog.get("specialists")
        if isinstance(specialists, list):
            for item in specialists:
                if isinstance(item, dict):
                    raw_names.append(item.get("name"))
                else:
                    raw_names.append(item)
    return _dedupe_strings(raw_names)


def _extract_languages_from_truth(truth: dict[str, Any] | None) -> list[str]:
    if not isinstance(truth, dict):
        return []
    salon = truth.get("salon")
    if not isinstance(salon, dict):
        return []
    communication = salon.get("communication")
    if not isinstance(communication, dict):
        return []
    languages = communication.get("languages")
    if not isinstance(languages, list):
        return []
    return _dedupe_strings(languages)


def _build_pack_scenario_context(client_slug: str | None) -> dict[str, Any]:
    slug = str(client_slug or "").strip()
    if not slug:
        return {}
    truth_path = _script_repo_root() / "truffles-api" / "app" / "knowledge" / slug / "SALON_TRUTH.yaml"
    truth = _load_yaml_file(truth_path)
    if not isinstance(truth, dict):
        return {"client_slug": slug, "errors": {"truth": f"missing_or_invalid:{truth_path}"}}
    salon = truth.get("salon") if isinstance(truth.get("salon"), dict) else {}
    business: dict[str, Any] = {}
    if isinstance(salon, dict):
        if salon.get("name"):
            business["display_name"] = salon.get("name")
        if salon.get("services_summary"):
            business["summary"] = salon.get("services_summary")
        if salon.get("city"):
            business["city"] = salon.get("city")
        languages = _extract_languages_from_truth(truth)
        if languages:
            business["languages"] = languages
    context: dict[str, Any] = {"client_slug": slug}
    if business:
        context["business"] = business
    services = _extract_service_names_from_truth(truth)
    if services:
        context["services"] = services
    specialists = _extract_specialist_names_from_truth(truth)
    if specialists:
        context["specialists"] = specialists
    return context


def _merge_scenario_context(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base or {})
    for key, value in (overlay or {}).items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _merge_scenario_context(merged[key], value)
            continue
        if key in merged and isinstance(merged[key], list) and isinstance(value, list):
            merged[key] = _dedupe_strings(list(merged[key]) + list(value))
            continue
        merged[key] = value
    return merged


def _resolve_scenario_context(
    *,
    client_slug: str | None,
    branch_slug: str | None,
    scenario_context_file: str | None,
) -> dict[str, Any]:
    context: dict[str, Any] = {}
    pack_context = _build_pack_scenario_context(client_slug)
    if pack_context:
        context = _merge_scenario_context(context, pack_context)
    file_context = _load_json_file(scenario_context_file)
    if file_context:
        context = _merge_scenario_context(context, file_context)
    slug = str(client_slug or "").strip()
    if slug and not context.get("client_slug"):
        context["client_slug"] = slug
    branch = str(branch_slug or "").strip()
    if branch and not context.get("branch_slug"):
        context["branch_slug"] = branch
    return context


def _scenario_context_service_candidates(
    scenario_context: dict[str, Any] | None,
) -> list[str]:
    if not isinstance(scenario_context, dict):
        return []
    return _dedupe_strings(scenario_context.get("services") or [])


def _scenario_context_specialist_candidates(
    scenario_context: dict[str, Any] | None,
) -> list[str]:
    if not isinstance(scenario_context, dict):
        return []
    return _dedupe_strings(scenario_context.get("specialists") or [])


def _scenario_context_summary(scenario_context: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(scenario_context, dict) or not scenario_context:
        return None
    business = scenario_context.get("business") if isinstance(scenario_context.get("business"), dict) else {}
    capabilities = (
        scenario_context.get("capabilities")
        if isinstance(scenario_context.get("capabilities"), dict)
        else {}
    )
    tools = capabilities.get("tools") if isinstance(capabilities.get("tools"), dict) else {}
    return {
        "client_slug": scenario_context.get("client_slug"),
        "branch_slug": scenario_context.get("branch_slug"),
        "business_display_name": business.get("display_name"),
        "business_summary": business.get("summary"),
        "languages": _dedupe_strings(business.get("languages") or []),
        "service_count": len(_scenario_context_service_candidates(scenario_context)),
        "specialist_count": len(_scenario_context_specialist_candidates(scenario_context)),
        "domain_slug": capabilities.get("domain_slug"),
        "tool_allow": _dedupe_strings(tools.get("allow") or []),
        "tool_deny": _dedupe_strings(tools.get("deny") or []),
        "allowed_fact_scopes": _dedupe_strings(capabilities.get("allowed_fact_scopes") or []),
        "handoff_policy": capabilities.get("handoff_policy"),
        "has_errors": bool(scenario_context.get("errors")),
    }


def _build_llm_generation_prompt(
    *,
    batch_count: int,
    min_turns: int,
    max_turns: int,
    coverage: list[str],
    media_mode: str,
    media_kind: str,
    seed: int | None,
    scenario_context: dict[str, Any] | None,
) -> str:
    summary = _scenario_context_summary(scenario_context)
    lines = [
        "Generate JSON with key 'dialogs' as a list.",
        "Each dialog: {dialog_id, goal, turns}.",
        "turns is a list of {kind,text,tags,expect} with 10-15 client messages.",
        "Tags must be chosen from: booking, interrupt, price, duration, location, hours, parking,",
        "promo, master, time, time_alt, ask_about_requested_slot, slot_constraint, slot_compare,",
        "mixed_fill_plus_question, consult, channel, delay, media, noise, handoff,",
        "cancel, reschedule, check_booking, confirm, tool.",
        "expect must include keys: action, info_sections, reply_type, state, expected_reply, allow_booking_stall.",
        "expect may optionally include meta/meta_any/meta_contains/trace_contains for structured runtime contracts.",
        "Use canonical tokens only in expect (no natural language):",
        "action: null or one of [booking_escalated, escalate, handoff];",
        "info_sections: array from [pricing, price, payment_info, payment, address, location,",
        "hours, working_hours, schedule, discounts, discount, promo, promotion, duration,",
        "service_duration, parking, master, specialist];",
        "reply_type: null or one of [service_choice, time, name];",
        "state: null or one of [bot_active, pending, manager_active];",
        "expected_reply: true/false/null.",
        "meta/meta_any/meta_contains keys must use canonical runtime fields such as action, source, expected_reply_type, expected_reply_reason, pending_question_target.",
        "trace_contains is a list of exact stage/decision evidence objects.",
        "Use ask_about_requested_slot / slot_constraint / slot_compare / mixed_fill_plus_question only",
        "for booking-active turns about the current requested slot before final slot fill.",
        "Include interruptions (price/location/noise), wrong slot answers, time/name swaps, and at least one media reference.",
        "Include at least one tool-related intent (cancel/reschedule/check booking) and a follow-up confirmation/denial turn.",
        "All turns must be CLIENT messages only (no assistant/manager lines).",
        "Do NOT write staff-like statements (e.g., 'Я вас записал', 'Работаем ежедневно',",
        "'Адрес:', 'Пришлите фото', 'Могу помочь').",
        "If you mention sending a photo, tag the turn with 'media' and phrase as the client",
        "(e.g., 'Могу прислать фото' instead of 'Вот фото'), otherwise avoid photo claims.",
    ]
    if summary:
        languages = ", ".join(summary.get("languages") or []) or "not specified"
        tool_allow = ", ".join(summary.get("tool_allow") or []) or "unspecified"
        tool_deny = ", ".join(summary.get("tool_deny") or []) or "none"
        fact_scopes = ", ".join(summary.get("allowed_fact_scopes") or []) or "unspecified"
        services = ", ".join(_scenario_context_service_candidates(scenario_context)[:8]) or "none"
        specialists = (
            ", ".join(_scenario_context_specialist_candidates(scenario_context)[:6]) or "none"
        )
        lines.extend(
            [
                "Scenario context is binding. Use it as the business/tool envelope.",
                "Do not assume beauty salon or Russian unless the context explicitly supports that.",
                f"client_slug={summary.get('client_slug') or 'unknown'}; "
                f"branch_slug={summary.get('branch_slug') or 'unknown'}; "
                f"domain_slug={summary.get('domain_slug') or 'unspecified'}.",
                f"business_name={summary.get('business_display_name') or 'unspecified'}; "
                f"business_summary={summary.get('business_summary') or 'unspecified'}.",
                f"languages={languages}.",
                f"known_services={services}.",
                f"known_specialists={specialists}.",
                f"tool_allow={tool_allow}; tool_deny={tool_deny}.",
                f"allowed_fact_scopes={fact_scopes}; "
                f"handoff_policy={summary.get('handoff_policy') or 'unspecified'}.",
                "If context is sparse, keep scenarios generic and do not invent unsupported business facts.",
            ]
        )
    else:
        lines.extend(
            [
                "No explicit business context was provided.",
                "Keep scenarios generic and do not assume one fixed business niche or language.",
            ]
        )
    lines.extend(
        [
            f"Count={batch_count}, turns_range={min_turns}-{max_turns}.",
            f"media_mode={media_mode}, media_kind={media_kind}.",
            f"coverage_tags={','.join(coverage) if coverage else 'none'}.",
            f"seed={seed}.",
        ]
    )
    return " ".join(lines)

ASSISTANT_TURN_PATTERNS = [
    re.compile(r"\bвам удобно\b", re.IGNORECASE),
    re.compile(r"\bна какую\b", re.IGNORECASE),
    re.compile(r"\bна какой\b", re.IGNORECASE),
    re.compile(r"\bкакой день\b", re.IGNORECASE),
    re.compile(r"\bкак вас зовут\b", re.IGNORECASE),
    re.compile(r"\bвас зовут\b", re.IGNORECASE),
    re.compile(r"\bпришлите\b", re.IGNORECASE),
    re.compile(r"\bуточните\b", re.IGNORECASE),
    re.compile(r"\bнапишите\b", re.IGNORECASE),
    re.compile(r"\bсообщите\b", re.IGNORECASE),
    re.compile(r"\bмогу помочь\b", re.IGNORECASE),
    re.compile(r"^адрес[: ]", re.IGNORECASE),
    re.compile(r"\bработаем\b", re.IGNORECASE),
    re.compile(r"\bя вас записал\b", re.IGNORECASE),
]

# Generated turns must stay semantically aligned with strong tags.
# Otherwise evaluator contracts can fail on scenario-text ambiguity.
MASTER_TAG_PATTERNS = [
    re.compile(r"\bмастер", re.IGNORECASE),
    re.compile(r"\bспециалист", re.IGNORECASE),
    re.compile(r"\bк\s+кому\b", re.IGNORECASE),
]
SPECIALIST_REFERENCE_PATTERNS = [
    re.compile(r"\bк\s+[A-ZА-ЯЁӘІҢҒҮҰҚӨҺ][A-Za-zА-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+\b"),
    re.compile(r"\bу\s+[A-ZА-ЯЁӘІҢҒҮҰҚӨҺ][A-Za-zА-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+\b"),
]
SPECIALIST_CHOICE_NAME_PATTERNS = [
    re.compile(
        r"\bвыбр\w*\s+[A-ZА-ЯЁӘІҢҒҮҰҚӨҺ][A-Za-zА-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+\b"
    ),
]
SPECIALIST_PREFERENCE_NAME_PATTERNS = [
    re.compile(
        r"\bпредпочит\w*\s+[A-ZА-ЯЁӘІҢҒҮҰҚӨҺ][A-Za-zА-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+\b",
        re.IGNORECASE,
    ),
]
RESCHEDULE_VERB_PATTERNS = [
    re.compile(r"\b(?:перенест\w*|перенос\w*|поменя\w*|измен\w*|сдвин\w*)\b", re.IGNORECASE),
    re.compile(r"\b(?:ауыстыр\w*|жылжыт\w*)\b", re.IGNORECASE),
]
RESCHEDULE_OBJECT_PATTERNS = [
    re.compile(r"\b(?:запис\w*|бронь\w*|дат\w*|врем\w*)\b", re.IGNORECASE),
    re.compile(r"\b(?:жазыл\w*|күн\w*|уақыт\w*)\b", re.IGNORECASE),
]
GENERIC_MASTER_INFO_QUESTION_PATTERNS = [
    re.compile(r"\bкто\s+(?:будет\s+)?(?:делать|проводить|выполнять)\b", re.IGNORECASE),
    re.compile(r"\bкто\s+из\s+мастер\w*\b", re.IGNORECASE),
    re.compile(
        r"\b(?:какой|какие|какого|какому)\s+(?:мастер\w*|специалист\w*)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:какой|какие|какого|какому)\b(?:\s+\w+){0,3}\s+\b(?:мастер\w*|специалист\w*)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:есть|будут|бывают|доступн\w*|свободн\w*)\b.*\b(?:мастер\w*|специалист\w*)\b",
        re.IGNORECASE,
    ),
]
STANDALONE_SPECIALIST_BOOKING_REQUEST_PATTERNS = [
    re.compile(r"^\s*(?:а\s+)?(?:можно|можно\s+ли|хочу|хотелось\s+бы|запишите)\b", re.IGNORECASE),
    re.compile(r"\bзапис\w*\b", re.IGNORECASE),
    re.compile(r"\bбола\s+ма\b", re.IGNORECASE),
    re.compile(r"\bжазыл\w*\b", re.IGNORECASE),
]
GENERIC_BOOKING_REQUEST_PATTERNS = [
    re.compile(
        r"\b(?:хочу|хотел(?:ось)?\s+бы|мне\s+нужно|нужно|можно(?:\s+ли)?)\b.*\bзапис\w*\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bзапис\w*\b.*\b(?:на|к)\b", re.IGNORECASE),
    re.compile(r"\bжазыл\w*\b", re.IGNORECASE),
]
REQUESTED_SLOT_QUESTION_PATTERNS = [
    re.compile(r"\b(?:на|в)\s+какое\s+время\b", re.IGNORECASE),
    re.compile(r"\bкакое\s+время\b.*\b(?:свобод\w*|доступн\w*|слот\w*|окн\w*)\b", re.IGNORECASE),
    re.compile(r"\b(?:свобод\w*|доступн\w*)\b.*\b(?:слот\w*|окн\w*|время)\b", re.IGNORECASE),
    re.compile(r"\b(?:слот\w*|окн\w*)\b.*\b(?:свобод\w*|доступн\w*|время)\b", re.IGNORECASE),
]

MIXED_SLOT_CONSTRAINT_PATTERNS = [
    re.compile(r"\b(?:утр\w*|вечер\w*|после\s+обеда|до\s+обеда|днем|днём|после\s+\d{1,2}|до\s+\d{1,2})\b", re.IGNORECASE),
    re.compile(r"\b(?:в|к)\s*(?:[01]?\d|2[0-3])(?::[0-5]\d)?\b", re.IGNORECASE),
    re.compile(
        r"\b(?:сегодня|завтра|послезавтра|(?:на|в)\s+(?:понедельник\w*|вторник\w*|сред\w*|четверг\w*|пятниц\w*|суббот\w*|воскресень\w*|выходн\w*))\b",
        re.IGNORECASE,
    ),
]
MIXED_SLOT_QUESTION_PATTERNS = [
    re.compile(r"\bесть\s+ли\b", re.IGNORECASE),
    re.compile(r"\bможно\s+ли\b", re.IGNORECASE),
    re.compile(r"\bсвобод\w*\b", re.IGNORECASE),
    re.compile(r"\bслот\w*\b", re.IGNORECASE),
    re.compile(r"\bокн\w*\b", re.IGNORECASE),
]
PARTIAL_DATE_FILL_PATTERNS = [
    re.compile(
        r"\b(?:сегодня|завтра|послезавтра|(?:на|в)\s+(?:понедельник\w*|вторник\w*|сред\w*|четверг\w*|пятниц\w*|суббот\w*|воскресень\w*)|(?:на\s+)?(?:эту|этой|следующ\w+)\s+недел\w*)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?)\b", re.IGNORECASE),
]
AVAILABILITY_QUERY_PATTERNS = [
    re.compile(r"\bсвобод\w*\b", re.IGNORECASE),
    re.compile(r"\bдоступн\w*\b", re.IGNORECASE),
    re.compile(r"\bслот\w*\b", re.IGNORECASE),
    re.compile(r"\bокн\w*\b", re.IGNORECASE),
    re.compile(r"\bкогда\b", re.IGNORECASE),
    re.compile(r"\bво\s+сколько\b", re.IGNORECASE),
]
TIME_OCCUPANCY_QUERY_PATTERNS = [
    re.compile(r"\bзанят\w*\b", re.IGNORECASE),
]
DEICTIC_TIME_REFERENCE_PATTERNS = [
    re.compile(r"\b(?:в|на)\s+это\s+время\b", re.IGNORECASE),
    re.compile(r"\b(?:в|на)\s+этот\s+слот\b", re.IGNORECASE),
    re.compile(r"\b(?:это|этот)\s+(?:время|слот)\b", re.IGNORECASE),
]
DEICTIC_DAY_REFERENCE_PATTERNS = [
    re.compile(r"\b(?:в|на)\s+этот\s+день\b", re.IGNORECASE),
    re.compile(r"\b(?:в|на)\s+эту\s+дат\w*\b", re.IGNORECASE),
    re.compile(r"\bэтот\s+день\b", re.IGNORECASE),
    re.compile(r"\bэту\s+дат\w*\b", re.IGNORECASE),
]
EXPLICIT_TIME_FILL_PATTERNS = [
    re.compile(r"\b(?:в|к|на)\s*(?:[01]?\d|2[0-3])(?::[0-5]\d)?\b", re.IGNORECASE),
    re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b", re.IGNORECASE),
]
AMBIGUOUS_TIME_FILL_PATTERNS = [
    re.compile(r"\bили\s+(?:позже|позднее|раньше|пораньше)\b", re.IGNORECASE),
    re.compile(r"\bне\s+(?:раньше|позже)\b", re.IGNORECASE),
    re.compile(r"\b(?:после|до)\s*(?:[01]?\d|2[0-3])(?::[0-5]\d)?\b", re.IGNORECASE),
]

FALLBACK_TEMPLATES_BY_TAG = {
    "location": "Где вы находитесь?",
    "hours": "Во сколько вы работаете?",
    "parking": "Есть ли парковка рядом?",
    "price": "Сколько стоит {service}?",
    "duration": "Сколько длится {service}?",
    "promo": "Есть ли акции на {service}?",
    "master": "Можно к мастеру {master}?",
    "booking": "{greet}, хочу записаться на {service}.",
    "time": "Можно {time_exact}?",
    "time_alt": "Если {time_exact} занято, можно {time_exact_alt}?",
    "ask_about_requested_slot": "На какое время лучше записаться?",
    "slot_constraint": "После обеда было бы удобнее.",
    "slot_compare": "Лучше утром или вечером?",
    "mixed_fill_plus_question": "Можно после 18, а утром или вечером лучше?",
    "name": "Меня зовут {name}.",
    "phone": "Телефон {phone}.",
    "confirm": "Да, все верно.",
    "check_booking": "Можете подтвердить мою запись?",
    "cancel": "Хочу отменить запись.",
    "reschedule": "Можно перенести запись?",
    "media": "Могу прислать фото.",
    "noise": "{noise}",
    "consult": "А у вас есть {service}?",
    "channel": "Можно только в чате?",
    "delay": "Я уточню и вернусь.",
    "handoff": "Можно связаться с менеджером?",
}
LANGUAGE_MUTATION_TAG_PRIORITY = [
    "booking",
    "price",
    "duration",
    "location",
    "hours",
    "parking",
    "promo",
    "master",
    "time",
    "time_alt",
    "ask_about_requested_slot",
    "slot_constraint",
    "slot_compare",
    "mixed_fill_plus_question",
    "name",
    "phone",
    "confirm",
    "check_booking",
    "cancel",
    "reschedule",
    "handoff",
    "consult",
    "channel",
    "delay",
    "noise",
]
KK_SURFACE_TEMPLATES_BY_TAG = {
    "booking": "{service} керек, {day} {time_range} бос уақыт бар ма?",
    "price": "{service} бағасы қанша?",
    "duration": "{service} қанша уақытқа созылады?",
    "location": "Мекенжайларыңыз қайда?",
    "hours": "Қай уақытқа дейін жұмыс істейсіздер?",
    "parking": "Тұрақ бар ма?",
    "promo": "{service} бойынша акция бар ма?",
    "master": "{master} маманына бола ма?",
    "time": "{time_exact} бола ма?",
    "time_alt": "{time_exact} болмаса, {time_exact_alt} бола ма?",
    "ask_about_requested_slot": "Қай уақытқа жазылған дұрыс?",
    "slot_constraint": "Түстен кейін болғаны ыңғайлы.",
    "slot_compare": "Таңертең жақсы ма, әлде кешке ме?",
    "mixed_fill_plus_question": "18:00-ден кейін болады, бірақ таңертең жақсы ма, әлде кешке ме?",
    "name": "Атым {name}.",
    "phone": "Нөмірім {phone}.",
    "confirm": "Иә, растаймын.",
    "check_booking": "Жазылуымды тексеріп беріңізші.",
    "cancel": "Жазылуды тоқтатқым келеді.",
    "reschedule": "Жазылуды ауыстыруға бола ма?",
    "handoff": "Менеджермен сөйлесуге бола ма?",
    "consult": "{service} бар ма?",
    "channel": "Тек чат арқылы жазысуға бола ма?",
    "delay": "Нақтылап алып, қайта жазамын.",
    "noise": "{noise}",
}
MIXED_SURFACE_TEMPLATES_BY_TAG = {
    "booking": "{greet}, {service} керек, можно {day} {time_range}?",
    "price": "{service} бағасы қанша вообще?",
    "duration": "{service} қанша уақыт алады вообще?",
    "location": "Адрестеріңіз қайда, подскажите?",
    "hours": "До скольки жұмыс істейсіздер?",
    "parking": "Парковка бар ма?",
    "promo": "{service} бойынша акция есть?",
    "master": "{master} мастері бар ма?",
    "time": "{time_exact} болады ма?",
    "time_alt": "{time_exact} занято болса, {time_exact_alt} болады ма?",
    "ask_about_requested_slot": "Қай уақытқа жазылған дұрыс вообще?",
    "slot_constraint": "Түстен кейін болғаны ыңғайлы вообще.",
    "slot_compare": "Таңертең жақсы ма, әлде кешке ме вообще?",
    "mixed_fill_plus_question": "18:00-ден кейін болады, бірақ таңертең жақсы ма, әлде кешке ме?",
    "name": "Менің атым {name}.",
    "phone": "Мой номер {phone}.",
    "confirm": "Иә, подтверждаю.",
    "check_booking": "Мою запись тексеріп бересіз бе?",
    "cancel": "Записьті отменить еткім келеді.",
    "reschedule": "Записьті ауыстыруға бола ма?",
    "handoff": "Можно с менеджером сөйлесуге бола ма?",
    "consult": "{service} вообще бар ма?",
    "channel": "Можно тек чатпен?",
    "delay": "Я уточню, потом қайта жазамын.",
    "noise": "{noise}",
}
CYRILLIC_TO_LATIN_MAP = {
    "а": "a",
    "ә": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "ғ": "gh",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "i",
    "к": "k",
    "қ": "q",
    "л": "l",
    "м": "m",
    "н": "n",
    "ң": "ng",
    "о": "o",
    "ө": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ұ": "u",
    "ү": "u",
    "ф": "f",
    "х": "h",
    "һ": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "і": "i",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}
TYPO_SURFACE_TEMPLATES_BY_TAG = {
    "booking": "{greet}, хачу записаца на {service}.",
    "price": "Скока стоит {service}?",
    "duration": "Скока по времени {service}?",
    "location": "Где вы находитесь, адресс подскажите?",
    "hours": "До скольки работаите?",
    "parking": "Порковка есть?",
    "promo": "Есть акция на {service}?",
    "master": "Можно к мастеру {master}?",
    "time": "Можно {time_exact}?",
    "time_alt": "Если {time_exact} занято, можна {time_exact_alt}?",
    "ask_about_requested_slot": "На какое время лутше записаться?",
    "slot_constraint": "После абеда было бы удобней.",
    "slot_compare": "Лутше утром или вечером?",
    "mixed_fill_plus_question": "Можно после 18, а утром или вечером лутше?",
    "name": "Миня зовут {name}.",
    "phone": "Телифон {phone}.",
    "confirm": "Да, потверждаю.",
    "check_booking": "Можите маю запись проверить?",
    "cancel": "Хачу отменить запись.",
    "reschedule": "Можно перенисти запись?",
    "handoff": "Можно с менеждером связаца?",
    "consult": "А у вас {service} есть?",
    "channel": "Можно тока в чате?",
    "delay": "Ща уточню и вернусь.",
    "noise": "{noise}",
}
RU_SYNONYM_TEMPLATES_BY_TAG = {
    "booking": "{greet}, хочу к вам на {service}.",
    "price": "По цене {service} подскажите, пожалуйста.",
    "duration": "Подскажите, сколько по времени занимает {service}?",
    "location": "Подскажите, как вас найти?",
    "hours": "Во сколько вы закрываетесь?",
    "parking": "Подскажите, рядом есть где припарковаться?",
    "promo": "Есть сейчас скидки на {service}?",
    "master": "Подскажите, к какому специалисту можно на {service}?",
    "time": "Сможете принять {time_exact}?",
    "time_alt": "Если {time_exact} не подойдет, можно {time_exact_alt}?",
    "ask_about_requested_slot": "Подскажите, на какое время лучше записаться?",
    "slot_constraint": "Мне удобнее после обеда.",
    "slot_compare": "Подскажите, утром лучше или вечером?",
    "mixed_fill_plus_question": "Можно после 18, а подскажите, утром лучше или вечером?",
    "name": "Можно оформить на имя {name}.",
    "phone": "Мой контакт {phone}.",
    "confirm": "Да, меня все устраивает.",
    "check_booking": "Пожалуйста, уточните мою запись.",
    "cancel": "Нужно снять мою запись.",
    "reschedule": "Хочу перенести запись на другое время.",
    "handoff": "Переключите, пожалуйста, на менеджера.",
    "consult": "Подскажите, делаете {service}?",
    "channel": "Можно без звонка, только перепиской?",
    "delay": "Я чуть позже вернусь с ответом.",
    "noise": "{noise}",
}
KK_SYNONYM_TEMPLATES_BY_TAG = {
    "booking": "{greet}, {service} бойынша жазылғым келеді.",
    "price": "{service} құны бойынша айтып жібересіз бе?",
    "duration": "{service} қанша уақыт алады, айтып жіберіңізші.",
    "location": "Сіздерді қалай табуға болады?",
    "hours": "Қай уақытта жабыласыздар?",
    "parking": "Қасыңызда көлік қоюға орын бар ма?",
    "promo": "{service} бойынша жеңілдік бар ма?",
    "master": "{service} үшін қай маманға жазылуға болады?",
    "time": "{time_exact} уақытына қабылдай аласыз ба?",
    "time_alt": "{time_exact} болмаса, {time_exact_alt} жарай ма?",
    "ask_about_requested_slot": "Қай уақытқа жазылған дұрыс, айтып жібересіз бе?",
    "slot_constraint": "Маған түстен кейін ыңғайлырақ.",
    "slot_compare": "Таңертең жақсы ма, әлде кешке ме, айтып жіберіңізші?",
    "mixed_fill_plus_question": "18:00-ден кейін бола ма, бірақ таңертең жақсы ма, әлде кешке ме?",
    "name": "Атым {name} деп жазып қойыңыз.",
    "phone": "Байланыс нөмірім {phone}.",
    "confirm": "Иә, маған солай ыңғайлы.",
    "check_booking": "Жазылуымды нақтылап беріңізші.",
    "cancel": "Жазылуымды алып тастағым келеді.",
    "reschedule": "Жазылуды басқа уақытқа ауыстырғым келеді.",
    "handoff": "Мені менеджерге қосып жібересіз бе?",
    "consult": "{service} жасайсыздар ма, айтып жіберіңізші?",
    "channel": "Қоңыраусыз, тек чатпен сөйлесуге бола ма?",
    "delay": "Кейінірек нақтылап қайта жазамын.",
    "noise": "{noise}",
}
MIXED_SYNONYM_TEMPLATES_BY_TAG = {
    "booking": "{greet}, хочу к вам на {service}, получится записаться?",
    "price": "{service} бағасы бойынша подскажите, пожалуйста.",
    "duration": "{service} қанша уақыт занимает вообще?",
    "location": "Как вас найти, мекенжайды подскажите?",
    "hours": "Во сколько вы закрываетесь вообще, қай уақытқа дейін?",
    "parking": "Рядом парковка бар ма, подскажите?",
    "promo": "{service} бойынша скидки сейчас есть?",
    "master": "{service} үшін к какому специалисту можно?",
    "time": "{time_exact} на это время получится ма?",
    "time_alt": "{time_exact} не выйдет болса, {time_exact_alt} можно ма?",
    "ask_about_requested_slot": "На какое время лучше записаться вообще?",
    "slot_constraint": "После обеда болғаны ыңғайлы.",
    "slot_compare": "Утром лучше ма, әлде вечером?",
    "mixed_fill_plus_question": "После 18 можно ма, но утром лучше ма, әлде вечером?",
    "name": "Можно записать на имя {name}, ок?",
    "phone": "Мой контакт номер {phone}.",
    "confirm": "Да, маған такой вариант подходит.",
    "check_booking": "Мою запись нақтылап бересіз бе?",
    "cancel": "Нужно записьті снять.",
    "reschedule": "Хочу записьті басқа уақытқа ауыстыру.",
    "handoff": "Переключите меня менеджерге, пожалуйста.",
    "consult": "{service} делаете вообще, айтып жіберіңізші?",
    "channel": "Можно без звонка, только чатпен?",
    "delay": "Я позже нақтылап қайта напишу.",
    "noise": "{noise}",
}
FALLBACK_TAG_PRIORITY = [
    "booking",
    "time",
    "ask_about_requested_slot",
    "slot_constraint",
    "slot_compare",
    "mixed_fill_plus_question",
    "name",
    "price",
    "duration",
    "location",
    "hours",
    "parking",
    "promo",
    "master",
    "check_booking",
    "cancel",
    "reschedule",
    "media",
    "noise",
    "consult",
    "channel",
    "delay",
    "handoff",
]

WRONG_TIME_TURN = {
    "text": "Меня зовут {name}.",
    "tags": ["wrong_slot", "name"],
    "expect": {"reply_type": "time", "allow_booking_stall": True},
}
WRONG_NAME_TURN = {
    "text": "эээ...",
    "tags": ["wrong_slot", "noise"],
    "expect": {"reply_type": "name", "allow_booking_stall": True},
}
WRONG_SERVICE_TURN = {
    "text": "Хочу {service}.",
    "tags": ["wrong_slot", "service"],
    "expect": {"reply_type": "time", "allow_booking_stall": True},
}
WRONG_DATE_TURN = {
    "text": "Давайте {day}.",
    "tags": ["wrong_slot", "date"],
    "expect": {"reply_type": "time", "allow_booking_stall": True},
}
WRONG_PHONE_TURN = {
    "text": "Телефон {phone}.",
    "tags": ["wrong_slot", "phone"],
    "expect": {"reply_type": "name", "allow_booking_stall": True},
}

INTERRUPTIONS = [
    {"text": "Сколько стоит {service}?", "tags": ["interrupt", "price"]},
    {"text": "Сколько длится процедура?", "tags": ["interrupt", "duration"]},
    {"text": "Где вы находитесь?", "tags": ["interrupt", "location"]},
    {"text": "Работаете сегодня?", "tags": ["interrupt", "hours"]},
    {"text": "Есть ли парковка?", "tags": ["interrupt", "parking"]},
    {"text": "Есть ли акция на {service}?", "tags": ["interrupt", "promo"]},
    {"text": "Можно к мастеру {master}?", "tags": ["interrupt", "master"]},
]

NOISE = [
    {"text": "👍", "tags": ["noise"]},
    {"text": "ок", "tags": ["noise"]},
    {"text": "эээ", "tags": ["noise"]},
    {"text": "??", "tags": ["noise"]},
    {"text": "сорри, отвлеклась", "tags": ["noise"]},
]

EXTRA_TURNS = [
    {"text": "Можно записаться на другое время, если 19:00 занято?", "tags": ["interrupt", "time_alt"]},
    {"text": "А у вас есть уходовые процедуры?", "tags": ["interrupt", "consult"]},
    {"text": "Мне бы без звонков, можно только в чате?", "tags": ["interrupt", "channel"]},
    {"text": "Можно только к женскому мастеру.", "tags": ["interrupt", "master"]},
    {"text": "Если можно, ближе к {time_exact}.", "tags": ["interrupt", "time"]},
    {"text": "На какое время лучше записаться?", "tags": ["ask_about_requested_slot"]},
    {"text": "После обеда было бы удобнее.", "tags": ["slot_constraint"]},
    {"text": "Лучше утром или вечером?", "tags": ["slot_compare"]},
    {"text": "Можно после 18, а утром или вечером лучше?", "tags": ["mixed_fill_plus_question"]},
    {"text": "Я еще уточню и вернусь.", "tags": ["interrupt", "delay"]},
]

SCENARIOS = [
    {
        "id": "haircut_price_location_photo",
        "goal": "book haircut with price/location interrupts + photo reference",
        "coverage": ["booking", "info", "interrupt"],
        "turns": [
            {"text": "{greet}! Хочу записаться на {service} {day} {time_range}, есть свободное?", "tags": ["booking"]},
            {"text": "{interrupt_price}", "tags": ["interrupt", "price"]},
            {"text": "{interrupt_location}", "tags": ["interrupt", "location"]},
            WRONG_SERVICE_TURN,
            WRONG_DATE_TURN,
            WRONG_TIME_TURN,
            {"text": "Любой мастер подойдет.", "tags": ["master"]},
            {"text": "Можно {time_exact}?", "tags": ["time"]},
            WRONG_NAME_TURN,
            WRONG_PHONE_TURN,
            {"text": "Меня зовут {name}.", "tags": ["name"]},
            {"text": "Телефон {phone}.", "tags": ["phone"]},
            {"text": "Да, все верно.", "tags": ["confirm"]},
        ],
        "requires_media": True,
    },
    {
        "id": "booking_time_swap_with_noise",
        "goal": "book service with time/name swaps and noise",
        "coverage": ["booking", "info", "interrupt"],
        "turns": [
            {"text": "{greet}, хочу записаться на {service} {day}.", "tags": ["booking"]},
            WRONG_SERVICE_TURN,
            WRONG_DATE_TURN,
            WRONG_TIME_TURN,
            {"text": "Можно {time_exact}?", "tags": ["time"]},
            {"text": "{noise}", "tags": ["noise"]},
            {"text": "Кстати, сколько стоит {service}?", "tags": ["interrupt", "price"]},
            WRONG_NAME_TURN,
            WRONG_PHONE_TURN,
            {"text": "Имя {name}.", "tags": ["name"]},
            {"text": "Телефон {phone}.", "tags": ["phone"]},
            {"text": "Да, подтверждаю.", "tags": ["confirm"]},
        ],
        "requires_media": False,
    },
    {
        "id": "booking_master_switch",
        "goal": "book with master preference changes",
        "coverage": ["booking", "info", "interrupt"],
        "turns": [
            {"text": "{greet}! Можно записаться на {service} {day} {time_range}?", "tags": ["booking"]},
            {"text": "Хотелось бы к {master}, но если занято, то любой.", "tags": ["master"]},
            {"text": "А где вы находитесь?", "tags": ["interrupt", "location"]},
            WRONG_SERVICE_TURN,
            WRONG_DATE_TURN,
            WRONG_TIME_TURN,
            {"text": "Можно {time_exact}?", "tags": ["time"]},
            WRONG_NAME_TURN,
            WRONG_PHONE_TURN,
            {"text": "Если нет, то {time_exact_alt}.", "tags": ["time"]},
            {"text": "Меня зовут {name}.", "tags": ["name"]},
            {"text": "Телефон {phone}.", "tags": ["phone"]},
            {"text": "Да.", "tags": ["confirm"]},
        ],
        "requires_media": False,
    },
    {
        "id": "booking_kz_mix",
        "goal": "book with RU/KZ mixed interruptions",
        "coverage": ["booking", "info", "interrupt"],
        "turns": [
            {"text": "{greet}! {service} керек, {day} {time_range} бар ма?", "tags": ["booking"]},
            {"text": "Бағасы қанша?", "tags": ["interrupt", "price"]},
            {"text": "Адресіңіз қайда?", "tags": ["interrupt", "location"]},
            WRONG_SERVICE_TURN,
            WRONG_DATE_TURN,
            WRONG_TIME_TURN,
            {"text": "Любой мастер подойдет.", "tags": ["master"]},
            {"text": "Можно {time_exact}?", "tags": ["time"]},
            WRONG_NAME_TURN,
            WRONG_PHONE_TURN,
            {"text": "Аты {name}.", "tags": ["name"]},
            {"text": "Номер {phone}.", "tags": ["phone"]},
            {"text": "Иә, дұрыс.", "tags": ["confirm"]},
        ],
        "requires_media": False,
    },
    {
        "id": "booking_multi_service",
        "goal": "book with multi-service request and interruptions",
        "coverage": ["booking", "info", "interrupt"],
        "turns": [
            {"text": "{greet}, хочу {service} и маникюр {day} {time_range}.", "tags": ["booking"]},
            {"text": "Можно сначала {service}, потом маникюр?", "tags": ["interrupt", "multi_service"]},
            {"text": "А сколько длится?", "tags": ["interrupt", "duration"]},
            WRONG_SERVICE_TURN,
            WRONG_DATE_TURN,
            WRONG_TIME_TURN,
            {"text": "Можно {time_exact}?", "tags": ["time"]},
            WRONG_NAME_TURN,
            WRONG_PHONE_TURN,
            {"text": "Меня зовут {name}.", "tags": ["name"]},
            {"text": "Телефон {phone}.", "tags": ["phone"]},
            {"text": "Да, подтверждаю.", "tags": ["confirm"]},
        ],
        "requires_media": False,
    },
    {
        "id": "booking_escalation_return",
        "goal": "request manager then resume booking",
        "coverage": ["booking", "handoff"],
        "turns": [
            {"text": "{greet}! Хочу записаться на {service}.", "tags": ["booking"]},
            {"text": "Можно связаться с менеджером?", "tags": ["handoff", "human"]},
            {"text": "Спасибо, жду.", "tags": ["pending"]},
            WRONG_SERVICE_TURN,
            WRONG_DATE_TURN,
            WRONG_TIME_TURN,
            {"text": "Давайте продолжим запись, можно {time_exact}?", "tags": ["time"]},
            WRONG_NAME_TURN,
            WRONG_PHONE_TURN,
            {"text": "Имя {name}.", "tags": ["name"]},
            {"text": "Телефон {phone}.", "tags": ["phone"]},
            {"text": "Да, подтверждаю.", "tags": ["confirm"]},
        ],
        "requires_media": False,
    },
]


def _language_profile_family(language_profile: str) -> str:
    lowered = str(language_profile or "ru").strip().lower()
    if lowered == "kk":
        return "kk_surface"
    if lowered == "mixed":
        return "ru_kk_code_switch"
    if lowered == "mixed_translit":
        return "ru_kk_mixed_translit"
    return "baseline_ru"


def _surface_noise_family(surface_noise_profile: str) -> str:
    lowered = str(surface_noise_profile or "clean").strip().lower()
    if lowered == "typo":
        return "typo_surface"
    return "clean_surface"


def _semantic_variation_family(semantic_variation_profile: str) -> str:
    lowered = str(semantic_variation_profile or "canonical").strip().lower()
    if lowered == "synonym":
        return "synonym_surface"
    return "canonical_surface"


def _slot_format_family(slot_format_profile: str) -> str:
    lowered = str(slot_format_profile or "canonical").strip().lower()
    if lowered == "variant":
        return "slot_format_variant"
    return "slot_format_canonical"


def _build_context(
    rng: random.Random, scenario_context: dict[str, Any] | None = None
) -> dict[str, str]:
    service_candidates = _scenario_context_service_candidates(scenario_context) or SERVICES
    specialist_candidates = _scenario_context_specialist_candidates(scenario_context) or MASTERS
    service = rng.choice(service_candidates)
    return {
        "greet": rng.choice(GREETINGS),
        "service": service,
        "day": rng.choice(DAYS),
        "time_range": rng.choice(TIME_RANGES),
        "time_exact": rng.choice(TIME_EXACT),
        "time_exact_alt": rng.choice(TIME_EXACT),
        "name": rng.choice(NAMES),
        "phone": rng.choice(PHONES),
        "master": rng.choice(specialist_candidates),
        "interrupt_price": f"Сколько стоит {service}?",
        "interrupt_location": rng.choice(
            ["Где вы находитесь?", "Как до вас добраться?", "Адрес подскажите?"]
        ),
        "noise": rng.choice([item["text"] for item in NOISE]),
    }

def _infer_context_from_dialog(
    dialog: dict[str, Any],
    rng: random.Random,
    scenario_context: dict[str, Any] | None = None,
) -> dict[str, str]:
    ctx = _build_context(rng, scenario_context=scenario_context)
    combined = " ".join(
        [turn.get("text", "") for turn in (dialog.get("turns") or []) if isinstance(turn, dict)]
    ).lower()
    for service in _scenario_context_service_candidates(scenario_context) or SERVICES:
        if service in combined:
            ctx["service"] = service
            break
    for candidate in TIME_EXACT:
        if candidate in combined:
            ctx["time_exact"] = candidate
            break
    for candidate in TIME_RANGES:
        if candidate in combined:
            ctx["time_range"] = candidate
            break
    for candidate in DAYS:
        if candidate in combined:
            ctx["day"] = candidate
            break
    return ctx


def _format_turn(turn: dict[str, Any], ctx: dict[str, str]) -> dict[str, Any]:
    text = turn["text"].format(**ctx)
    tags = list(turn.get("tags") or [])
    return {
        "kind": "text",
        "text": text,
        "tags": tags,
        "expect": _merge_expectations(tags, turn.get("expect"), text=text),
    }


def _language_mutation_primary_tag(tags: list[str]) -> str | None:
    lowered_tags = {
        str(tag).strip().lower()
        for tag in (tags or [])
        if isinstance(tag, str) and str(tag).strip()
    }
    for tag in LANGUAGE_MUTATION_TAG_PRIORITY:
        if tag in lowered_tags:
            return tag
    return None


def _language_surface_template(language_profile: str, tag: str | None) -> str | None:
    if not tag:
        return None
    lowered = str(language_profile or "ru").strip().lower()
    if lowered == "kk":
        return KK_SURFACE_TEMPLATES_BY_TAG.get(tag)
    if lowered in {"mixed", "mixed_translit"}:
        return MIXED_SURFACE_TEMPLATES_BY_TAG.get(tag)
    return None


def _transliterate_surface_text(text: str) -> str:
    pieces: list[str] = []
    for char in str(text or ""):
        mapped = CYRILLIC_TO_LATIN_MAP.get(char.lower())
        if mapped is None:
            pieces.append(char)
            continue
        if not mapped:
            continue
        pieces.append(mapped.capitalize() if char.isupper() else mapped)
    return "".join(pieces)


def _surface_noise_template(surface_noise_profile: str, tag: str | None) -> str | None:
    if not tag:
        return None
    lowered = str(surface_noise_profile or "clean").strip().lower()
    if lowered == "typo":
        return TYPO_SURFACE_TEMPLATES_BY_TAG.get(tag)
    return None


def _semantic_variation_template(
    semantic_variation_profile: str,
    tag: str | None,
    *,
    language_profile: str,
) -> str | None:
    if not tag:
        return None
    lowered = str(semantic_variation_profile or "canonical").strip().lower()
    if lowered != "synonym":
        return None
    language_family = _language_profile_family(language_profile)
    if language_family == "kk_surface":
        return KK_SYNONYM_TEMPLATES_BY_TAG.get(tag)
    if language_family in {"ru_kk_code_switch", "ru_kk_mixed_translit"}:
        return MIXED_SYNONYM_TEMPLATES_BY_TAG.get(tag)
    return RU_SYNONYM_TEMPLATES_BY_TAG.get(tag)


def _apply_surface_noise(
    turns: list[dict[str, Any]],
    ctx: dict[str, str],
    *,
    surface_noise_profile: str,
    rng: random.Random,
) -> list[dict[str, Any]]:
    lowered_profile = str(surface_noise_profile or "clean").strip().lower()
    if lowered_profile == "clean":
        return turns
    if lowered_profile not in SURFACE_NOISE_PROFILE_CHOICES:
        raise ValueError(f"unsupported surface_noise_profile={surface_noise_profile}")

    mutated: list[dict[str, Any]] = []
    mutated_indices: list[int] = []
    eligible_indices: list[int] = []
    for idx, turn in enumerate(turns):
        copied_turn = dict(turn)
        copied_turn["tags"] = list(turn.get("tags") or [])
        if isinstance(turn.get("expect"), dict):
            copied_turn["expect"] = dict(turn.get("expect") or {})
        primary_tag = _language_mutation_primary_tag(copied_turn.get("tags") or [])
        template = _surface_noise_template(lowered_profile, primary_tag)
        should_mutate = template is not None and copied_turn.get("kind") == "text"
        if should_mutate:
            eligible_indices.append(idx)
            should_mutate = rng.random() < 0.5
            if should_mutate and template is not None:
                copied_turn["text"] = template.format(**ctx)
                mutated_indices.append(idx)
        mutated.append(copied_turn)

    if eligible_indices and not mutated_indices:
        first_idx = eligible_indices[0]
        first_turn = mutated[first_idx]
        primary_tag = _language_mutation_primary_tag(first_turn.get("tags") or [])
        template = _surface_noise_template(lowered_profile, primary_tag)
        if template is not None:
            first_turn["text"] = template.format(**ctx)
            mutated_indices.append(first_idx)

    return mutated


def _apply_semantic_variation(
    turns: list[dict[str, Any]],
    ctx: dict[str, str],
    *,
    semantic_variation_profile: str,
    language_profile: str,
    rng: random.Random,
) -> list[dict[str, Any]]:
    lowered_profile = str(semantic_variation_profile or "canonical").strip().lower()
    if lowered_profile == "canonical":
        return turns
    if lowered_profile not in SEMANTIC_VARIATION_PROFILE_CHOICES:
        raise ValueError(
            f"unsupported semantic_variation_profile={semantic_variation_profile}"
        )

    mutated: list[dict[str, Any]] = []
    mutated_indices: list[int] = []
    eligible_indices: list[int] = []
    for idx, turn in enumerate(turns):
        copied_turn = dict(turn)
        copied_turn["tags"] = list(turn.get("tags") or [])
        if isinstance(turn.get("expect"), dict):
            copied_turn["expect"] = dict(turn.get("expect") or {})
        primary_tag = _language_mutation_primary_tag(copied_turn.get("tags") or [])
        template = _semantic_variation_template(
            lowered_profile,
            primary_tag,
            language_profile=language_profile,
        )
        should_mutate = template is not None and copied_turn.get("kind") == "text"
        if should_mutate:
            eligible_indices.append(idx)
            should_mutate = rng.random() < 0.5
            if should_mutate and template is not None:
                rendered = template.format(**ctx)
                if _language_profile_family(language_profile) == "ru_kk_mixed_translit":
                    rendered = _transliterate_surface_text(rendered)
                copied_turn["text"] = rendered
                mutated_indices.append(idx)
        mutated.append(copied_turn)

    if eligible_indices and not mutated_indices:
        first_idx = eligible_indices[0]
        first_turn = mutated[first_idx]
        primary_tag = _language_mutation_primary_tag(first_turn.get("tags") or [])
        template = _semantic_variation_template(
            lowered_profile,
            primary_tag,
            language_profile=language_profile,
        )
        if template is not None:
            rendered = template.format(**ctx)
            if _language_profile_family(language_profile) == "ru_kk_mixed_translit":
                rendered = _transliterate_surface_text(rendered)
            first_turn["text"] = rendered
            mutated_indices.append(first_idx)

    return mutated


def _format_phone_variant(phone: str) -> str:
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if len(digits) == 11 and digits[0] in {"7", "8"}:
        national = "8" + digits[1:]
        return (
            f"{national[0]} ({national[1:4]}) {national[4:7]}-"
            f"{national[7:9]}-{national[9:11]}"
        )
    return str(phone or "")


def _format_time_variant(value: str) -> str:
    text = str(value or "").strip()
    match = re.search(r"(\d{1,2}):(\d{2})", text)
    if not match:
        if text.startswith("после ") and text[6:].isdigit():
            return f"после {text[6:]}:00"
        if text == "вечером":
            return "ближе к вечеру"
        return text
    hour = match.group(1)
    minute = match.group(2)
    if text.startswith("на "):
        return f"к {hour}.{minute}"
    if text.startswith("после "):
        return f"после {hour}:{minute}"
    return text.replace(":", ".")


def _format_day_variant(value: str) -> str:
    mapping = {
        "в пятницу": "на пятницу",
        "в субботу": "на субботу",
        "в воскресенье": "на воскресенье",
        "завтра": "на завтра",
        "на выходных": "в выходные",
    }
    return mapping.get(str(value or "").strip(), str(value or ""))


def _format_time_range_variant(value: str) -> str:
    mapping = {
        "после 18": "после 18:00",
        "после 19": "после 19:00",
        "вечером": "ближе к вечеру",
        "в районе 17:30": "примерно к 17.30",
    }
    return mapping.get(str(value or "").strip(), _format_time_variant(value))


def _slot_format_replacement_pairs(
    ctx: dict[str, str],
    *,
    language_profile: str,
) -> list[tuple[str, str]]:
    replacements: list[tuple[str, str]] = []
    base_pairs = [
        (ctx.get("phone", ""), _format_phone_variant(ctx.get("phone", ""))),
        (ctx.get("time_exact", ""), _format_time_variant(ctx.get("time_exact", ""))),
        (ctx.get("time_exact_alt", ""), _format_time_variant(ctx.get("time_exact_alt", ""))),
        (ctx.get("day", ""), _format_day_variant(ctx.get("day", ""))),
        (ctx.get("time_range", ""), _format_time_range_variant(ctx.get("time_range", ""))),
    ]
    language_family = _language_profile_family(language_profile)
    for original, variant in base_pairs:
        if not original or not variant or original == variant:
            continue
        replacements.append((str(original), str(variant)))
        if language_family == "ru_kk_mixed_translit":
            translit_original = _transliterate_surface_text(str(original))
            translit_variant = _transliterate_surface_text(str(variant))
            if translit_original and translit_variant and translit_original != translit_variant:
                replacements.append((translit_original, translit_variant))
    replacements.sort(key=lambda item: len(item[0]), reverse=True)
    return replacements


def _apply_slot_format_variation(
    turns: list[dict[str, Any]],
    ctx: dict[str, str],
    *,
    slot_format_profile: str,
    language_profile: str,
) -> list[dict[str, Any]]:
    lowered_profile = str(slot_format_profile or "canonical").strip().lower()
    if lowered_profile == "canonical":
        return turns
    if lowered_profile not in SLOT_FORMAT_PROFILE_CHOICES:
        raise ValueError(f"unsupported slot_format_profile={slot_format_profile}")
    replacements = _slot_format_replacement_pairs(ctx, language_profile=language_profile)
    if not replacements:
        return turns

    mutated: list[dict[str, Any]] = []
    for turn in turns:
        copied_turn = dict(turn)
        copied_turn["tags"] = list(turn.get("tags") or [])
        if isinstance(turn.get("expect"), dict):
            copied_turn["expect"] = dict(turn.get("expect") or {})
        if copied_turn.get("kind") == "text":
            text = str(copied_turn.get("text") or "")
            for original, variant in replacements:
                if original and original in text:
                    text = text.replace(original, variant)
            copied_turn["text"] = text
        mutated.append(copied_turn)
    return mutated


def _apply_language_profile(
    turns: list[dict[str, Any]],
    ctx: dict[str, str],
    *,
    language_profile: str,
    rng: random.Random,
) -> list[dict[str, Any]]:
    lowered_profile = str(language_profile or "ru").strip().lower()
    if lowered_profile == "ru":
        return turns
    if lowered_profile not in LANGUAGE_PROFILE_CHOICES:
        raise ValueError(f"unsupported language_profile={language_profile}")

    mutated: list[dict[str, Any]] = []
    mutated_indices: list[int] = []
    eligible_indices: list[int] = []

    for idx, turn in enumerate(turns):
        copied_turn = dict(turn)
        copied_turn["tags"] = list(turn.get("tags") or [])
        if isinstance(turn.get("expect"), dict):
            copied_turn["expect"] = dict(turn.get("expect") or {})
        primary_tag = _language_mutation_primary_tag(copied_turn.get("tags") or [])
        template = _language_surface_template(lowered_profile, primary_tag)
        should_mutate = template is not None and copied_turn.get("kind") == "text"
        if should_mutate:
            eligible_indices.append(idx)
            if lowered_profile in {"mixed", "mixed_translit"}:
                should_mutate = rng.random() < 0.5
            if should_mutate and template is not None:
                rendered = template.format(**ctx)
                if lowered_profile == "mixed_translit":
                    rendered = _transliterate_surface_text(rendered)
                copied_turn["text"] = rendered
                mutated_indices.append(idx)
        mutated.append(copied_turn)

    if lowered_profile in {"mixed", "mixed_translit"} and eligible_indices and not mutated_indices:
        first_idx = eligible_indices[0]
        first_turn = mutated[first_idx]
        primary_tag = _language_mutation_primary_tag(first_turn.get("tags") or [])
        template = _language_surface_template(lowered_profile, primary_tag)
        if template is not None:
            rendered = template.format(**ctx)
            if lowered_profile == "mixed_translit":
                rendered = _transliterate_surface_text(rendered)
            first_turn["text"] = rendered
            mutated_indices.append(first_idx)

    return mutated


def _resolve_reference_photo_meta() -> tuple[str, str, str, str]:
    raw_path = os.environ.get("TRUFFLES_REFERENCE_IMAGE_PATH", DEFAULT_REFERENCE_IMAGE_PATH)
    local_path = os.path.abspath(os.path.expanduser(str(raw_path)))
    resolved_path = os.path.realpath(local_path)
    file_source = resolved_path if os.path.isfile(resolved_path) else local_path
    file_name = os.path.basename(file_source)
    if not file_name or "." not in file_name:
        file_name = "reference.jpg"
    mimetype = mimetypes.guess_type(file_source)[0] or "image/jpeg"
    photo_url = os.environ.get("TRUFFLES_REFERENCE_IMAGE_URL", DEFAULT_REFERENCE_IMAGE_URL)
    return local_path, file_name, mimetype, photo_url


def _media_turn(ctx: dict[str, str], *, mode: str, kind: str) -> dict[str, Any]:
    caption = "Вот фото референса"
    if mode == "text":
        return {
            "kind": "text",
            "text": caption,
            "tags": ["media", kind],
            "expect": _merge_expectations(["media", kind], None),
        }
    if kind == "audio":
        media_payload = {
            "messageType": "audio",
            "mediaData": {
                "type": "audio",
                "mimetype": "audio/ogg",
                "url": "https://app.chatflow.kz/static/demo/reference.ogg",
                "fileName": "reference.ogg",
                "caption": "Голосовое с уточнениями",
                "seconds": 8,
                "ptt": True,
            },
        }
    else:
        photo_local_path, photo_file_name, photo_mimetype, photo_url = _resolve_reference_photo_meta()
        media_payload = {
            "messageType": "image",
            "mediaData": {
                "type": "image",
                "mimetype": photo_mimetype,
                "url": photo_url,
                "fileName": photo_file_name,
                "localPath": photo_local_path,
                "caption": caption,
            },
        }
    return {
        "kind": "media",
        "text": caption,
        "tags": ["media", kind],
        "media": media_payload,
        "expect": _merge_expectations(["media", kind], None),
    }


def _looks_like_assistant_turn(text: str) -> bool:
    if not text:
        return False
    normalized = text.strip()
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in ASSISTANT_TURN_PATTERNS)


def _fallback_text_for_tags(tags: list[str], ctx: dict[str, str], rng: random.Random) -> str:
    for tag in FALLBACK_TAG_PRIORITY:
        if tag in tags:
            template = FALLBACK_TEMPLATES_BY_TAG.get(tag)
            if template:
                return template.format(**ctx)
    return f"{ctx.get('greet', 'Здравствуйте')}, хочу записаться на {ctx.get('service', 'услугу')}."


def _text_matches_tag_contract(text: str, tags: list[str]) -> bool:
    if not text:
        return False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "master" in lowered_tags:
        return _looks_like_specialist_reference(text)
    return True


def _looks_like_specialist_reference(text: str) -> bool:
    if not text:
        return False
    return any(
        pattern.search(text)
        for pattern in (
            MASTER_TAG_PATTERNS
            + SPECIALIST_REFERENCE_PATTERNS
            + SPECIALIST_CHOICE_NAME_PATTERNS
        )
    )


def _looks_like_generic_master_info_question(text: str | None) -> bool:
    if not text:
        return False
    return any(pattern.search(text) for pattern in GENERIC_MASTER_INFO_QUESTION_PATTERNS)


def _looks_like_specialist_availability_followup_question(text: str | None) -> bool:
    if not text:
        return False
    if not _looks_like_generic_master_info_question(text):
        return False
    if not any(pattern.search(text) for pattern in AVAILABILITY_QUERY_PATTERNS):
        return False
    return any(pattern.search(text) for pattern in PARTIAL_DATE_FILL_PATTERNS)


def _looks_like_grounded_time_specialist_availability_transition_question(text: str | None) -> bool:
    if not text:
        return False
    if not _looks_like_generic_master_info_question(text):
        return False
    if not any(pattern.search(text) for pattern in AVAILABILITY_QUERY_PATTERNS):
        return False
    return not any(pattern.search(text) for pattern in PARTIAL_DATE_FILL_PATTERNS)


def _looks_like_standalone_specialist_booking_request(text: str | None) -> bool:
    if not text:
        return False
    if _looks_like_generic_master_info_question(text):
        return False
    if not _looks_like_specialist_reference(text):
        return False
    return any(pattern.search(text) for pattern in STANDALONE_SPECIALIST_BOOKING_REQUEST_PATTERNS)


def _looks_like_named_specialist_preference_availability_question(text: str | None) -> bool:
    if not text:
        return False
    if not any(pattern.search(text) for pattern in SPECIALIST_PREFERENCE_NAME_PATTERNS):
        return False
    return any(
        pattern.search(text)
        for pattern in (AVAILABILITY_QUERY_PATTERNS + TIME_OCCUPANCY_QUERY_PATTERNS)
    )


def _looks_like_mixed_slot_question(text: str | None) -> bool:
    if not text:
        return False
    if not any(pattern.search(text) for pattern in MIXED_SLOT_CONSTRAINT_PATTERNS):
        return False
    return any(pattern.search(text) for pattern in MIXED_SLOT_QUESTION_PATTERNS)


def _looks_like_question_like_slot_constraint(text: str | None) -> bool:
    if not text:
        return False
    if _looks_like_explicit_time_fill(text):
        return False
    if not any(pattern.search(text) for pattern in MIXED_SLOT_CONSTRAINT_PATTERNS):
        return False
    lowered = text.strip().lower()
    return "?" in text or lowered.startswith(("можно", "а можно", "могу", "может"))


def _looks_like_reschedule_followup(text: str | None, tags: list[str]) -> bool:
    if not text:
        return False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if not (lowered_tags & (PENDING_QUESTION_TAGS | {"booking", "time"})):
        return False
    has_reschedule_verb = any(pattern.search(text) for pattern in RESCHEDULE_VERB_PATTERNS)
    has_reschedule_object = any(pattern.search(text) for pattern in RESCHEDULE_OBJECT_PATTERNS)
    has_temporal_followup = bool(
        has_reschedule_object
        or _looks_like_partial_date_fill_without_availability_query(text)
        or _looks_like_explicit_time_fill(text)
        or _looks_like_mixed_slot_question(text)
        or _looks_like_question_like_slot_constraint(text)
    )
    if has_reschedule_verb and has_reschedule_object:
        return True
    if has_reschedule_verb:
        return has_temporal_followup
    return has_temporal_followup


CHECK_BOOKING_FOLLOWUP_PATTERNS = (
    re.compile(r"\bкогда\b.*\b(запис|встреч|назнач)", re.IGNORECASE),
    re.compile(r"\b(?:моя|мою)\b.*\bзапис(?:ь|и|ью|е|ей)\b", re.IGNORECASE),
    re.compile(r"\bу\s+меня\b.*\b(?:запис(?:ь|и|ью|е|ей)|встреч)\b", re.IGNORECASE),
    re.compile(r"\b(провер|уточн).*\bзапис", re.IGNORECASE),
    re.compile(r"\bназначен[ао]?\b.*\b(встреч|запис)", re.IGNORECASE),
)


def _looks_like_check_booking_followup(text: str | None, tags: list[str]) -> bool:
    if not text:
        return False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "booking" not in lowered_tags:
        return False
    if lowered_tags & {"reschedule", "cancel", "confirm", "check_booking"}:
        return False
    return any(pattern.search(text) for pattern in CHECK_BOOKING_FOLLOWUP_PATTERNS)


def _looks_like_generic_booking_request(text: str | None) -> bool:
    if not text:
        return False
    if any(pattern.search(text) for pattern in CHECK_BOOKING_FOLLOWUP_PATTERNS):
        return False
    if any(pattern.search(text) for pattern in RESCHEDULE_VERB_PATTERNS):
        return False
    return any(pattern.search(text) for pattern in GENERIC_BOOKING_REQUEST_PATTERNS)


def _looks_like_requested_slot_question_without_temporal_scope(text: str | None) -> bool:
    if not text:
        return False
    if _looks_like_explicit_time_fill(text):
        return False
    if _looks_like_mixed_slot_question(text):
        return False
    if any(pattern.search(text) for pattern in PARTIAL_DATE_FILL_PATTERNS):
        return False
    if _looks_like_generic_master_info_question(text):
        return False
    return any(pattern.search(text) for pattern in REQUESTED_SLOT_QUESTION_PATTERNS)


def _looks_like_non_comparative_availability_question(text: str | None) -> bool:
    if _looks_like_requested_slot_question_without_temporal_scope(text):
        return True
    if not text:
        return False
    if _looks_like_explicit_time_fill(text):
        return False
    if _looks_like_mixed_slot_question(text):
        return False
    if any(pattern.search(text) for pattern in PARTIAL_DATE_FILL_PATTERNS):
        return False
    if _looks_like_generic_master_info_question(text):
        return False
    return any(pattern.search(text) for pattern in AVAILABILITY_QUERY_PATTERNS)


def _looks_like_service_grounded_booking(
    text: str | None,
    ctx: dict[str, str] | None = None,
) -> bool:
    if not text:
        return False
    if _looks_like_multi_service_booking_request(text, ctx):
        return False
    normalized = text.lower()
    candidates = []
    if isinstance(ctx, dict):
        candidates.append(ctx.get("service"))
    candidates.extend(SERVICES)
    seen: set[str] = set()
    for candidate in candidates:
        token = str(candidate or "").strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        if token in normalized:
            return True
    return False


MULTI_SERVICE_CONNECTOR_PATTERNS = (
    re.compile(r"\bи\b", re.IGNORECASE),
    re.compile(r"\bсначала\b", re.IGNORECASE),
    re.compile(r"\bпотом\b", re.IGNORECASE),
)


def _matched_service_candidates(
    text: str | None,
    ctx: dict[str, str] | None = None,
) -> list[str]:
    if not text:
        return []
    normalized = text.lower()
    candidates: list[str] = []
    if isinstance(ctx, dict):
        candidates.append(str(ctx.get("service") or ""))
    candidates.extend(SERVICES)
    matches: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        token = str(candidate or "").strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        if token in normalized:
            matches.append(token)
    return matches


def _looks_like_multi_service_booking_request(
    text: str | None,
    ctx: dict[str, str] | None = None,
) -> bool:
    matches = _matched_service_candidates(text, ctx)
    if len(matches) < 2:
        return False
    source_text = str(text or "")
    return any(pattern.search(source_text) for pattern in MULTI_SERVICE_CONNECTOR_PATTERNS)


def _normalize_stateful_booking_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> list[str]:
    if active_reply_type != "time":
        return tags
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "booking" not in lowered_tags:
        return tags
    if not _looks_like_mixed_slot_question(text):
        return tags

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "booking":
            tag = "mixed_fill_plus_question"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "booking" in normalized:
        normalized = [tag for tag in normalized if tag != "booking"]
    return normalized


def _normalize_active_name_master_info_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "name":
        return tags, False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "booking" not in lowered_tags:
        return tags, False
    if not _looks_like_generic_master_info_question(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "booking":
            tag = "master"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "master" not in normalized:
        normalized.insert(0, "master")
    return normalized, replaced


def _normalize_active_time_master_info_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "booking" not in lowered_tags:
        return tags, False
    if not _looks_like_generic_master_info_question(text):
        return tags, False
    if _looks_like_specialist_availability_followup_question(text):
        return tags, False
    if _looks_like_grounded_time_specialist_availability_transition_question(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "booking":
            tag = "master"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "master" not in normalized:
        normalized.insert(0, "master")
    return normalized, replaced


def _normalize_grounded_time_specialist_availability_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "slot_compare" not in lowered_tags:
        return tags, False
    if not _looks_like_grounded_time_specialist_availability_transition_question(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "slot_compare":
            tag = "master"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "master" not in normalized:
        normalized.insert(0, "master")
    return normalized, replaced


def _normalize_active_time_specialist_master_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type not in {None, "time"}:
        return tags, False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "master" not in lowered_tags:
        return tags, False
    if not _looks_like_specialist_reference(text or ""):
        return tags, False
    if active_reply_type is None and not _looks_like_standalone_specialist_booking_request(text):
        return tags, False
    if _looks_like_generic_master_info_question(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "master":
            tag = "booking"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "booking" not in normalized:
        normalized.insert(0, "booking")
    return normalized, replaced


def _normalize_active_time_booking_fill_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "booking" not in lowered_tags:
        return tags, False
    if _looks_like_mixed_slot_question(text):
        return tags, False
    if not _looks_like_explicit_time_fill(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "booking":
            tag = "time"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "time" not in normalized:
        normalized.insert(0, "time")
    return normalized, replaced


def _normalize_malformed_check_booking_tags(
    text: str | None,
    tags: list[str],
) -> tuple[list[str], bool]:
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "check_booking" not in lowered_tags:
        return tags, False
    if _looks_like_check_booking_followup(text, ["booking"]):
        return tags, False
    if not _looks_like_generic_booking_request(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "check_booking":
            tag = "booking"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "booking" not in normalized:
        normalized.insert(0, "booking")
    return normalized, replaced


def _normalize_booking_requested_slot_question_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "booking" not in lowered_tags:
        return tags, False
    if not _looks_like_requested_slot_question_without_temporal_scope(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "booking":
            tag = "ask_about_requested_slot"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "ask_about_requested_slot" not in normalized:
        normalized.insert(0, "ask_about_requested_slot")
    return normalized, replaced


def _normalize_slot_constraint_requested_slot_question_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "slot_constraint" not in lowered_tags:
        return tags, False
    if not _looks_like_requested_slot_question_without_temporal_scope(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "slot_constraint":
            tag = "ask_about_requested_slot"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "ask_about_requested_slot" not in normalized:
        normalized.insert(0, "ask_about_requested_slot")
    return normalized, replaced


def _normalize_slot_compare_requested_slot_question_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "slot_compare" not in lowered_tags:
        return tags, False
    if not _looks_like_non_comparative_availability_question(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "slot_compare":
            tag = "ask_about_requested_slot"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "ask_about_requested_slot" not in normalized:
        normalized.insert(0, "ask_about_requested_slot")
    return normalized, replaced


def _looks_like_partial_date_availability_slot_constraint(text: str | None) -> bool:
    if not text:
        return False
    if _looks_like_generic_master_info_question(text):
        return False
    if not any(pattern.search(text) for pattern in PARTIAL_DATE_FILL_PATTERNS):
        return False
    if _looks_like_explicit_time_fill(text):
        return False
    if any(pattern.search(text) for pattern in AMBIGUOUS_TIME_FILL_PATTERNS):
        return False
    lowered = f" {text.strip().lower()} "
    if " или " in lowered:
        return False
    has_availability_surface = any(
        pattern.search(text)
        for pattern in (AVAILABILITY_QUERY_PATTERNS + TIME_OCCUPANCY_QUERY_PATTERNS)
    )
    has_time_question_surface = _looks_like_mixed_slot_question(text) and bool(
        re.search(r"\bврем\w*\b", text, re.IGNORECASE)
    )
    return has_availability_surface or has_time_question_surface


def _normalize_slot_compare_partial_date_constraint_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "slot_compare" not in lowered_tags:
        return tags, False
    if not _looks_like_partial_date_availability_slot_constraint(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "slot_compare":
            tag = "slot_constraint"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "slot_constraint" not in normalized:
        normalized.insert(0, "slot_constraint")
    return normalized, replaced


def _looks_like_explicit_time_fill(text: str | None) -> bool:
    if not text:
        return False
    return any(pattern.search(text) for pattern in EXPLICIT_TIME_FILL_PATTERNS)


def _looks_like_ambiguous_time_fill(text: str | None) -> bool:
    if not text or not _looks_like_explicit_time_fill(text):
        return False
    return any(pattern.search(text) for pattern in AMBIGUOUS_TIME_FILL_PATTERNS)


def _looks_like_partial_date_fill_without_availability_query(text: str | None) -> bool:
    if not text:
        return False
    if _looks_like_explicit_time_fill(text):
        return False
    has_partial_date = any(pattern.search(text) for pattern in PARTIAL_DATE_FILL_PATTERNS)
    if not has_partial_date:
        return False
    return not any(pattern.search(text) for pattern in AVAILABILITY_QUERY_PATTERNS)


def _looks_like_grounded_time_availability_probe(text: str | None) -> bool:
    if not text:
        return False
    if not (
        _looks_like_explicit_time_fill(text)
        or any(pattern.search(text) for pattern in DEICTIC_TIME_REFERENCE_PATTERNS)
        or any(pattern.search(text) for pattern in DEICTIC_DAY_REFERENCE_PATTERNS)
    ):
        return False
    return (
        any(pattern.search(text) for pattern in MIXED_SLOT_QUESTION_PATTERNS)
        or any(pattern.search(text) for pattern in AVAILABILITY_QUERY_PATTERNS)
        or any(pattern.search(text) for pattern in TIME_OCCUPANCY_QUERY_PATTERNS)
    )


def _looks_like_grounded_partial_date_daypart_fill(text: str | None) -> bool:
    if not text:
        return False
    if _looks_like_explicit_time_fill(text):
        return False
    if any(pattern.search(text) for pattern in PARTIAL_DATE_FILL_PATTERNS):
        return False
    has_daypart_reference = bool(MIXED_SLOT_CONSTRAINT_PATTERNS and MIXED_SLOT_CONSTRAINT_PATTERNS[0].search(text))
    if not has_daypart_reference:
        return False
    return any(pattern.search(text) for pattern in AVAILABILITY_QUERY_PATTERNS)


def _normalize_slot_constraint_answer_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "slot_constraint" not in lowered_tags:
        return tags, False
    if _looks_like_mixed_slot_question(text):
        return tags, False
    if not _looks_like_explicit_time_fill(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "slot_constraint":
            tag = "time"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "slot_constraint" in normalized:
        normalized = [tag for tag in normalized if tag != "slot_constraint"]
    return normalized, replaced


def _normalize_partial_date_slot_constraint_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "slot_constraint" not in lowered_tags:
        return tags, False
    if _looks_like_mixed_slot_question(text):
        return tags, False
    if not _looks_like_partial_date_fill_without_availability_query(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "slot_constraint":
            tag = "time"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "slot_constraint" in normalized:
        normalized = [tag for tag in normalized if tag != "slot_constraint"]
    return normalized, replaced


def _normalize_partial_date_mixed_question_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "mixed_fill_plus_question" not in lowered_tags:
        return tags, False
    if not _looks_like_partial_date_fill_without_availability_query(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "mixed_fill_plus_question":
            tag = "booking"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "booking" not in normalized:
        normalized.insert(0, "booking")
    return normalized, replaced


def _normalize_grounded_time_probe_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "ask_about_requested_slot" not in lowered_tags:
        return tags, False
    if not _looks_like_explicit_time_fill(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "ask_about_requested_slot":
            tag = "time"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "time" not in normalized:
        normalized.insert(0, "time")
    return normalized, replaced


def _normalize_slot_compare_exact_time_fill_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "slot_compare" not in lowered_tags:
        return tags, False
    if not _looks_like_explicit_time_fill(text):
        return tags, False
    if _looks_like_ambiguous_time_fill(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "slot_compare":
            tag = "time"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "time" not in normalized:
        normalized.insert(0, "time")
    return normalized, replaced


def _normalize_grounded_partial_date_mixed_fill_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
    partial_date_anchor_active: bool,
) -> tuple[list[str], bool]:
    if active_reply_type != "time" or not partial_date_anchor_active:
        return tags, False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "mixed_fill_plus_question" not in lowered_tags:
        return tags, False
    if not _looks_like_grounded_partial_date_daypart_fill(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "mixed_fill_plus_question":
            tag = "time"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "time" not in normalized:
        normalized.insert(0, "time")
    return normalized, replaced


def _normalize_question_like_slot_constraint_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "ask_about_requested_slot" not in lowered_tags:
        return tags, False
    if not _looks_like_question_like_slot_constraint(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "ask_about_requested_slot":
            tag = "slot_constraint"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "slot_constraint" not in normalized:
        normalized.insert(0, "slot_constraint")
    return normalized, replaced


def _normalize_pending_question_tags(text: str | None, tags: list[str]) -> list[str]:
    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "ask_about_requested_slot" and _looks_like_mixed_slot_question(text):
            tag = "mixed_fill_plus_question"
            replaced = True
        elif tag == "ask_about_requested_slot" and _looks_like_generic_master_info_question(text):
            tag = "master"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "ask_about_requested_slot" in normalized:
        normalized = [tag for tag in normalized if tag != "ask_about_requested_slot"]
    return normalized


def _apply_service_grounded_booking_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    text: str | None,
    ctx: dict[str, str],
) -> dict[str, Any]:
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "booking" not in lowered_tags:
        return expect
    if not _looks_like_service_grounded_booking(text, ctx):
        return expect

    expect["reply_type"] = "time"

    meta = dict(expect.get("meta") or {})
    if meta.get("expected_reply_type") == "service_choice":
        meta["expected_reply_type"] = "time"
    if meta:
        expect["meta"] = meta

    meta_any = dict(expect.get("meta_any") or {})
    if meta_any.get("expected_reply_type"):
        meta_any["expected_reply_type"] = ["time"]
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in expect.get("trace_contains") or []:
        normalized_entry = dict(entry)
        if (
            normalized_entry.get("stage") == "question_contract"
            and normalized_entry.get("expected_reply_type") == "service_choice"
        ):
            normalized_entry["expected_reply_type"] = "time"
        trace_contains.append(normalized_entry)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def _apply_multi_service_booking_clarify_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    text: str | None,
    ctx: dict[str, str] | None,
) -> dict[str, Any]:
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "booking" not in lowered_tags:
        return expect
    if not _looks_like_multi_service_booking_request(text, ctx):
        return expect

    expect["reply_type"] = "service_choice"
    expect["expected_reply"] = True

    meta = dict(expect.get("meta") or {})
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = "service_choice"
    meta["expected_reply_contract_reason"] = "multi_service_booking_clarify"
    if meta:
        expect["meta"] = meta

    meta_any = dict(expect.get("meta_any") or {})
    meta_any["expected_reply_type"] = ["service_choice"]
    meta_any["expected_reply_contract_reason"] = ["multi_service_booking_clarify"]
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_target", None)
    meta_any.pop("pending_question_interaction", None)
    meta_any.pop("pending_question_owner", None)
    meta_any.pop("active_question_relation", None)
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in expect.get("trace_contains") or []:
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") == "pending_question_interaction":
            continue
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = "service_choice"
            normalized_entry["reason"] = "multi_service_booking_clarify"
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "service_choice",
        "reason": "multi_service_booking_clarify",
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def _apply_active_pending_question_info_interrupt_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    active_reply_type: str | None,
) -> dict[str, Any]:
    if active_reply_type not in {"service_choice", "time", "name"}:
        return expect

    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if not (lowered_tags & ACTIVE_PENDING_QUESTION_INFO_INTERRUPT_TAGS):
        return expect
    if lowered_tags & (
        PENDING_QUESTION_TAGS
        | {"booking", "time", "master", "handoff", "human", "pending", "cancel", "reschedule"}
    ):
        return expect

    expect["reply_type"] = active_reply_type
    expect["expected_reply"] = True

    meta = dict(expect.get("meta") or {})
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = active_reply_type
    if meta:
        expect["meta"] = meta

    meta_any = dict(expect.get("meta_any") or {})
    meta_any["expected_reply_type"] = [active_reply_type]
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_target", None)
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in expect.get("trace_contains") or []:
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") == "pending_question_interaction":
            continue
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = active_reply_type
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": active_reply_type,
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def _clear_multi_service_info_interrupt_followup_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    multi_service_clarify_active: bool,
) -> dict[str, Any]:
    if not multi_service_clarify_active:
        return expect

    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if not (lowered_tags & ACTIVE_PENDING_QUESTION_INFO_INTERRUPT_TAGS):
        return expect
    if lowered_tags & (
        PENDING_QUESTION_TAGS
        | {"booking", "time", "master", "handoff", "human", "pending", "cancel", "reschedule"}
    ):
        return expect

    expect["reply_type"] = None
    if expect.get("expected_reply") is None:
        expect["expected_reply"] = True

    meta = dict(expect.get("meta") or {})
    meta.pop("expected_reply_type", None)
    meta.pop("expected_reply_contract_reason", None)
    if meta:
        expect["meta"] = meta
    elif "meta" in expect:
        expect.pop("meta", None)

    meta_any = dict(expect.get("meta_any") or {})
    meta_any.pop("expected_reply_type", None)
    meta_any.pop("expected_reply_contract_reason", None)
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_target", None)
    meta_any.pop("pending_question_interaction", None)
    meta_any.pop("pending_question_owner", None)
    meta_any.pop("active_question_relation", None)
    if meta_any:
        expect["meta_any"] = meta_any
    elif "meta_any" in expect:
        expect.pop("meta_any", None)

    trace_contains = []
    for entry in expect.get("trace_contains") or []:
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") in {
            "question_contract",
            "pending_question_interaction",
        }:
            continue
        trace_contains.append(normalized_entry)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    elif "trace_contains" in expect:
        expect.pop("trace_contains", None)
    return expect


def _apply_service_grounded_booking_progress_interrupt_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    text: str | None,
    ctx: dict[str, str],
    active_reply_type: str | None,
) -> dict[str, Any]:
    if active_reply_type != "service_choice":
        return expect

    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if not (lowered_tags & {"price", "duration", "promo"}):
        return expect
    if not _looks_like_service_grounded_booking(text, ctx):
        return expect

    expect["reply_type"] = "time"
    expect["expected_reply"] = True

    meta = dict(expect.get("meta") or {})
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = "time"
    meta["expected_reply_contract_reason"] = "catalog_service_booking_progress"
    if meta:
        expect["meta"] = meta

    meta_any = dict(expect.get("meta_any") or {})
    meta_any["expected_reply_type"] = ["time"]
    meta_any["expected_reply_contract_reason"] = ["catalog_service_booking_progress"]
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_target", None)
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in expect.get("trace_contains") or []:
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") == "pending_question_interaction":
            continue
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = "time"
            normalized_entry["reason"] = "catalog_service_booking_progress"
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "time",
        "reason": "catalog_service_booking_progress",
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def _apply_ambiguous_time_fill_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    if active_reply_type != "time":
        return expect
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "time" not in lowered_tags:
        return expect
    if not _looks_like_ambiguous_time_fill(text):
        return expect

    expect["reply_type"] = "time"
    expect["expected_reply"] = True

    meta = dict(expect.get("meta") or {})
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = "time"
    if meta:
        expect["meta"] = meta

    meta_any = dict(expect.get("meta_any") or {})
    meta_any["expected_reply_type"] = ["time"]
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_target", None)
    meta_any.pop("pending_question_interaction", None)
    meta_any.pop("pending_question_owner", None)
    meta_any.pop("active_question_relation", None)
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in expect.get("trace_contains") or []:
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") == "pending_question_interaction":
            continue
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = "time"
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "time",
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def _apply_exact_time_fill_collect_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    if active_reply_type != "time":
        return expect
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "time" not in lowered_tags:
        return expect
    if not _looks_like_explicit_time_fill(text):
        return expect
    if _looks_like_ambiguous_time_fill(text):
        return expect

    expect["reply_type"] = "name"
    expect["expected_reply"] = True

    meta = dict(expect.get("meta") or {})
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = "name"
    if meta:
        expect["meta"] = meta

    meta_any = dict(expect.get("meta_any") or {})
    meta_any["expected_reply_type"] = ["name"]
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_target", None)
    meta_any.pop("pending_question_interaction", None)
    meta_any.pop("pending_question_owner", None)
    meta_any.pop("active_question_relation", None)
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in expect.get("trace_contains") or []:
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") == "pending_question_interaction":
            continue
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = "name"
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "name",
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def _apply_partial_date_fill_collect_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    if active_reply_type != "time":
        return expect
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "time" not in lowered_tags:
        return expect
    if not _looks_like_partial_date_fill_without_availability_query(text):
        return expect

    expect["reply_type"] = "name"
    expect["expected_reply"] = True

    meta = dict(expect.get("meta") or {})
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = "name"
    if meta:
        expect["meta"] = meta

    meta_any = dict(expect.get("meta_any") or {})
    meta_any["expected_reply_type"] = ["name"]
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_target", None)
    meta_any.pop("pending_question_interaction", None)
    meta_any.pop("pending_question_owner", None)
    meta_any.pop("active_question_relation", None)
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in expect.get("trace_contains") or []:
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") == "pending_question_interaction":
            continue
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = "name"
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "name",
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def _apply_grounded_partial_date_daypart_fill_expectations(
    expect: dict[str, Any],
    *,
    original_tags: list[str],
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
    partial_date_anchor_active: bool,
) -> dict[str, Any]:
    if active_reply_type != "time" or not partial_date_anchor_active:
        return expect
    original_lowered = {
        str(tag).strip().lower()
        for tag in original_tags
        if isinstance(tag, str) and str(tag).strip()
    }
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "mixed_fill_plus_question" not in original_lowered:
        return expect
    if "time" not in lowered_tags:
        return expect
    if not _looks_like_grounded_partial_date_daypart_fill(text):
        return expect

    expect["reply_type"] = "name"
    expect["expected_reply"] = True

    meta = dict(expect.get("meta") or {})
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = "name"
    if meta:
        expect["meta"] = meta

    meta_any = dict(expect.get("meta_any") or {})
    meta_any["expected_reply_type"] = ["name"]
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_target", None)
    meta_any.pop("pending_question_interaction", None)
    meta_any.pop("pending_question_owner", None)
    meta_any.pop("active_question_relation", None)
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in expect.get("trace_contains") or []:
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") == "pending_question_interaction":
            continue
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = "name"
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "name",
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def _apply_active_pending_question_cancel_interrupt_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    active_reply_type: str | None,
) -> dict[str, Any]:
    if active_reply_type not in {"service_choice", "time", "name"}:
        return expect

    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "cancel" not in lowered_tags:
        return expect
    if lowered_tags & {"booking", "time", "master", "reschedule", "check_booking"}:
        return expect

    expect["reply_type"] = active_reply_type
    expect["expected_reply"] = True

    meta = dict(expect.get("meta") or {})
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = active_reply_type
    if meta:
        expect["meta"] = meta

    meta_any = dict(expect.get("meta_any") or {})
    meta_any["expected_reply_type"] = [active_reply_type]
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in expect.get("trace_contains") or []:
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = active_reply_type
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": active_reply_type,
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def _apply_active_time_specialist_followup_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    if active_reply_type not in {"service_choice", "time", "name"}:
        return expect

    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    specialist_target_question = bool(
        active_reply_type == "time"
        and "ask_about_requested_slot" in lowered_tags
        and (
            _infer_pending_question_target(text, tags) == "specialist"
            or _looks_like_named_specialist_preference_availability_question(text)
        )
    )
    if specialist_target_question:
        expect["reply_type"] = "time"
        expect["info_sections"] = []

        meta = dict(expect.get("meta") or {})
        if meta.get("expected_reply_type"):
            meta["expected_reply_type"] = "time"
        if meta:
            expect["meta"] = meta

        meta_any = dict(expect.get("meta_any") or {})
        meta_any.pop("pending_question_act", None)
        meta_any.pop("pending_question_owner", None)
        meta_any.pop("booking_interrupt_info", None)
        meta_any.pop("intent", None)
        meta_any.pop("source", None)
        meta_any["pending_question_target"] = ["specialist"]
        meta_any["active_question_relation"] = ["referent_followup"]
        meta_any["expected_reply_type"] = ["time"]
        expect["meta_any"] = meta_any

        return compile_active_time_specialist_followup_expectations(expect)

    specialist_followup = bool(
        "booking" in lowered_tags
        and _looks_like_specialist_reference(text or "")
    )
    if not specialist_followup:
        return expect

    expect["reply_type"] = active_reply_type
    expect["info_sections"] = []

    meta = dict(expect.get("meta") or {})
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = active_reply_type
    if meta:
        expect["meta"] = meta

    meta_any = dict(expect.get("meta_any") or {})
    meta_any["pending_question_target"] = ["specialist"]
    meta_any["expected_reply_type"] = [active_reply_type]
    meta_any["pending_question_interaction"] = ["specialist_followup"]
    meta_any["pending_question_owner"] = ["booking_specialist_followup"]
    meta_any["active_question_relation"] = ["referent_followup"]
    meta_any.pop("booking_interrupt_info", None)
    meta_any.pop("intent", None)
    meta_any.pop("source", None)
    expect["meta_any"] = meta_any

    trace_contains = []
    for entry in expect.get("trace_contains") or []:
        normalized_entry = dict(entry)
        if (
            normalized_entry.get("stage") == "booking_interrupt"
            and normalized_entry.get("pending_question_target") == "specialist"
        ):
            continue
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = active_reply_type
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": active_reply_type,
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    specialist_trace = {
        "stage": "pending_question_interaction",
        "decision": "booking_specialist_followup",
        "pending_question_target": "specialist",
        "active_question_relation": "referent_followup",
        "expected_reply_type": active_reply_type,
    }
    if specialist_trace not in trace_contains:
        trace_contains.append(specialist_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def _infer_pending_question_target(text: str | None, tags: list[str]) -> str | None:
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if not (lowered_tags & TARGETED_PENDING_QUESTION_TAGS):
        return None
    if "master" in lowered_tags or _looks_like_specialist_reference(text or ""):
        return "specialist"
    return "time"


def _apply_pending_question_target_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    text: str | None,
) -> dict[str, Any]:
    target = _infer_pending_question_target(text, tags)
    if not target:
        return expect

    meta_any = dict(expect.get("meta_any") or {})
    meta_any["pending_question_target"] = [target]
    trace_contains = list(expect.get("trace_contains") or [])

    if target == "specialist":
        info_sections = list(expect.get("info_sections") or [])
        for section in EXPECT_INFO_SECTIONS["master"]:
            if section not in info_sections:
                info_sections.append(section)
        expect["info_sections"] = info_sections
        meta_any.pop("pending_question_act", None)
        meta_any["booking_interrupt_info"] = [True]
        meta_any["intent"] = ["master"]
        trace_contains = [
            entry
            for entry in trace_contains
            if entry.get("stage") != "pending_question_interaction"
        ]
        specialist_trace = {
            "stage": "booking_interrupt",
            "decision": "info_reply",
            "pending_question_target": "specialist",
            "booking_interrupt_info": True,
            "info_sections": ["master"],
        }
        if specialist_trace not in trace_contains:
            trace_contains.append(specialist_trace)

    expect["meta_any"] = meta_any
    expect["trace_contains"] = trace_contains
    return expect


def _apply_pending_master_info_interrupt_expectations(
    expect: dict[str, Any],
    *,
    original_tags: list[str],
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    original_lowered = {
        str(tag).strip().lower()
        for tag in original_tags
        if isinstance(tag, str) and str(tag).strip()
    }
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "ask_about_requested_slot" not in original_lowered:
        return expect
    if "master" not in lowered_tags:
        return expect
    if active_reply_type != "time":
        return expect
    if not _looks_like_generic_master_info_question(text):
        return expect
    if _looks_like_specialist_availability_followup_question(text):
        return expect

    expect["reply_type"] = "time"
    expect["expected_reply"] = True

    info_sections = list(expect.get("info_sections") or [])
    for section in EXPECT_INFO_SECTIONS["master"]:
        if section not in info_sections:
            info_sections.append(section)
    expect["info_sections"] = info_sections

    meta_any = dict(expect.get("meta_any") or {})
    meta_any["intent"] = ["master"]
    meta_any["source"] = ["booking_info_contract"]
    meta_any["booking_interrupt_info"] = [True]
    meta_any["pending_question_target"] = ["time"]
    meta_any["expected_reply_type"] = ["time"]
    meta_any.pop("pending_question_act", None)

    trace_contains = [
        dict(entry)
        for entry in (expect.get("trace_contains") or [])
        if entry.get("stage") != "pending_question_interaction"
    ]
    booking_interrupt_trace = {
        "stage": "booking_interrupt",
        "decision": "info_reply",
        "pending_question_target": "time",
        "booking_interrupt_info": True,
    }
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "time",
    }
    if booking_interrupt_trace not in trace_contains:
        trace_contains.append(booking_interrupt_trace)
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)

    expect["meta_any"] = meta_any
    expect["trace_contains"] = trace_contains
    return expect


def _apply_pending_specialist_availability_followup_expectations(
    expect: dict[str, Any],
    *,
    original_tags: list[str],
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    original_lowered = {
        str(tag).strip().lower()
        for tag in original_tags
        if isinstance(tag, str) and str(tag).strip()
    }
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "ask_about_requested_slot" not in original_lowered:
        return expect
    if "master" not in lowered_tags:
        return expect
    if active_reply_type != "time":
        return expect
    if not _looks_like_specialist_availability_followup_question(text):
        return expect

    expect["reply_type"] = "time"
    expect["expected_reply"] = True

    info_sections = list(expect.get("info_sections") or [])
    for section in EXPECT_INFO_SECTIONS["master"]:
        if section not in info_sections:
            info_sections.append(section)
    expect["info_sections"] = info_sections

    meta_any = dict(expect.get("meta_any") or {})
    meta_any["source"] = ["llm_policy_core"]
    meta_any["pending_question_act"] = ["ask_about_requested_slot"]
    meta_any["pending_question_target"] = ["specialist"]
    meta_any["pending_question_interaction"] = ["specialist_availability_followup"]
    meta_any["pending_question_owner"] = ["booking_specialist_availability_followup"]
    meta_any["active_question_relation"] = ["specialist_availability_followup"]
    meta_any["expected_reply_type"] = ["time"]
    expect["meta_any"] = meta_any

    trace_contains = [
        dict(entry)
        for entry in (expect.get("trace_contains") or [])
        if entry.get("stage") != "booking_interrupt"
    ]
    followup_trace = {
        "stage": "pending_question_interaction",
        "decision": "booking_specialist_availability_followup",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "specialist",
        "active_question_relation": "specialist_availability_followup",
        "expected_reply_type": "time",
    }
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "time",
    }
    if followup_trace not in trace_contains:
        trace_contains.append(followup_trace)
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    expect["trace_contains"] = trace_contains
    return expect


def _apply_grounded_time_specialist_availability_transition_expectations(
    expect: dict[str, Any],
    *,
    original_tags: list[str],
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    original_lowered = {
        str(tag).strip().lower()
        for tag in original_tags
        if isinstance(tag, str) and str(tag).strip()
    }
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if not (original_lowered & {"ask_about_requested_slot", "slot_compare"}):
        return expect
    if "master" not in lowered_tags:
        return expect
    if active_reply_type != "time":
        return expect
    if not _looks_like_grounded_time_specialist_availability_transition_question(text):
        return expect

    expect["reply_type"] = "name"
    expect["expected_reply"] = True

    info_sections = list(expect.get("info_sections") or [])
    for section in EXPECT_INFO_SECTIONS["master"]:
        if section not in info_sections:
            info_sections.append(section)
    expect["info_sections"] = info_sections

    meta_any = dict(expect.get("meta_any") or {})
    meta_any.pop("booking_interrupt_info", None)
    meta_any.pop("intent", None)
    meta_any["source"] = ["llm_policy_core"]
    meta_any["pending_question_act"] = ["ask_about_requested_slot"]
    meta_any["pending_question_target"] = ["specialist"]
    meta_any["pending_question_interaction"] = ["specialist_availability_followup"]
    meta_any["pending_question_owner"] = ["booking_specialist_availability_followup"]
    meta_any["active_question_relation"] = ["specialist_availability_followup"]
    meta_any["expected_reply_type"] = ["name"]
    expect["meta_any"] = meta_any

    trace_contains = [
        dict(entry)
        for entry in (expect.get("trace_contains") or [])
        if entry.get("stage") not in {"booking_interrupt", "question_contract"}
    ]
    followup_trace = {
        "stage": "pending_question_interaction",
        "decision": "booking_specialist_availability_followup",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "specialist",
        "active_question_relation": "specialist_availability_followup",
        "expected_reply_type": "name",
    }
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "name",
    }
    if followup_trace not in trace_contains:
        trace_contains.append(followup_trace)
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    expect["trace_contains"] = trace_contains
    return expect


def _apply_active_name_master_info_interrupt_expectations(
    expect: dict[str, Any],
    *,
    original_tags: list[str],
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    original_lowered = {
        str(tag).strip().lower()
        for tag in original_tags
        if isinstance(tag, str) and str(tag).strip()
    }
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "booking" not in original_lowered:
        return expect
    if "master" not in lowered_tags:
        return expect
    if active_reply_type != "name":
        return expect
    if not _looks_like_generic_master_info_question(text):
        return expect

    expect["reply_type"] = "name"
    expect["expected_reply"] = True

    info_sections = list(expect.get("info_sections") or [])
    for section in EXPECT_INFO_SECTIONS["master"]:
        if section not in info_sections:
            info_sections.append(section)
    expect["info_sections"] = info_sections

    meta_any = dict(expect.get("meta_any") or {})
    meta_any["intent"] = ["master"]
    meta_any["source"] = ["booking_info_contract"]
    meta_any["booking_interrupt_info"] = [True]
    meta_any["pending_question_target"] = ["specialist"]
    meta_any["expected_reply_type"] = ["name"]
    meta_any.pop("pending_question_act", None)
    expect["meta_any"] = meta_any

    trace_contains = [
        dict(entry)
        for entry in (expect.get("trace_contains") or [])
        if entry.get("stage") != "pending_question_interaction"
    ]
    booking_interrupt_trace = {
        "stage": "booking_interrupt",
        "decision": "info_reply",
        "pending_question_target": "specialist",
        "booking_interrupt_info": True,
        "info_sections": ["master"],
    }
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "name",
    }
    if booking_interrupt_trace not in trace_contains:
        trace_contains.append(booking_interrupt_trace)
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    expect["trace_contains"] = trace_contains
    return expect


def _apply_active_time_master_info_interrupt_expectations(
    expect: dict[str, Any],
    *,
    original_tags: list[str],
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    original_lowered = {
        str(tag).strip().lower()
        for tag in original_tags
        if isinstance(tag, str) and str(tag).strip()
    }
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "booking" not in original_lowered:
        return expect
    if "master" not in lowered_tags:
        return expect
    if active_reply_type != "time":
        return expect
    if not _looks_like_generic_master_info_question(text):
        return expect
    if _looks_like_specialist_availability_followup_question(text):
        return expect
    if _looks_like_grounded_time_specialist_availability_transition_question(text):
        return expect

    expect["reply_type"] = "time"
    expect["expected_reply"] = True

    info_sections = list(expect.get("info_sections") or [])
    for section in EXPECT_INFO_SECTIONS["master"]:
        if section not in info_sections:
            info_sections.append(section)
    expect["info_sections"] = info_sections

    meta_any = dict(expect.get("meta_any") or {})
    meta_any["intent"] = ["master"]
    meta_any["source"] = ["booking_info_contract"]
    meta_any["booking_interrupt_info"] = [True]
    meta_any["pending_question_target"] = ["time"]
    meta_any["expected_reply_type"] = ["time"]
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_interaction", None)
    meta_any.pop("pending_question_owner", None)
    meta_any.pop("active_question_relation", None)
    expect["meta_any"] = meta_any

    trace_contains = [
        dict(entry)
        for entry in (expect.get("trace_contains") or [])
        if entry.get("stage") != "pending_question_interaction"
    ]
    booking_interrupt_trace = {
        "stage": "booking_interrupt",
        "decision": "info_reply",
        "pending_question_target": "time",
        "booking_interrupt_info": True,
        "info_sections": ["master"],
    }
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "time",
    }
    if booking_interrupt_trace not in trace_contains:
        trace_contains.append(booking_interrupt_trace)
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    expect["trace_contains"] = trace_contains
    return expect


def _apply_active_name_time_availability_followup_expectations(
    expect: dict[str, Any],
    *,
    original_tags: list[str],
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    original_lowered = {
        str(tag).strip().lower()
        for tag in original_tags
        if isinstance(tag, str) and str(tag).strip()
    }
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if active_reply_type != "name":
        return expect
    if not ({"booking", "ask_about_requested_slot"} & (original_lowered | lowered_tags)):
        return expect
    if "booking" not in lowered_tags:
        return expect
    explicit_time_followup = bool(
        "ask_about_requested_slot" in (original_lowered | lowered_tags)
        and _looks_like_explicit_time_fill(text)
    )
    if not (
        _looks_like_grounded_time_availability_probe(text)
        or _looks_like_requested_slot_question_without_temporal_scope(text)
        or explicit_time_followup
    ):
        return expect

    expect["reply_type"] = "name"
    expect["expected_reply"] = True

    meta_any = dict(expect.get("meta_any") or {})
    meta_any.pop("booking_interrupt_info", None)
    meta_any.pop("intent", None)
    meta_any["source"] = ["llm_policy_core"]
    meta_any["pending_question_act"] = ["ask_about_requested_slot"]
    meta_any["pending_question_target"] = ["time"]
    meta_any["pending_question_interaction"] = ["ask_about_requested_slot"]
    meta_any["pending_question_owner"] = ["booking_time_availability_followup"]
    meta_any["active_question_relation"] = ["ask_about_requested_slot"]
    meta_any["expected_reply_type"] = ["name"]
    expect["meta_any"] = meta_any

    trace_contains = [
        dict(entry)
        for entry in (expect.get("trace_contains") or [])
        if entry.get("stage") not in {"booking_interrupt", "question_contract", "pending_question_interaction"}
    ]
    followup_trace = {
        "stage": "pending_question_interaction",
        "decision": "booking_time_availability_followup",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
        "expected_reply_type": "name",
    }
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "name",
    }
    if followup_trace not in trace_contains:
        trace_contains.append(followup_trace)
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    expect["trace_contains"] = trace_contains
    return expect


def _has_orphan_pending_question_tags(
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> bool:
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if not (lowered_tags & PENDING_QUESTION_TAGS):
        return False
    return active_reply_type != "time"


def _rewrite_orphan_pending_question_tags(tags: list[str]) -> list[str]:
    rewritten: list[str] = []
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag or tag in PENDING_QUESTION_TAGS:
            continue
        if tag not in rewritten:
            rewritten.append(tag)
    if "booking" not in rewritten:
        rewritten.insert(0, "booking")
    return rewritten


def _orphan_pending_question_expect_override() -> dict[str, Any]:
    return {
        "reply_type": "service_choice",
        "expected_reply": True,
        "meta_any": {
            "expected_reply_type": ["service_choice"],
        },
        "trace_contains": [
            {
                "stage": "question_contract",
                "expected_reply_type": "service_choice",
            }
        ],
    }


def _rewrite_reschedule_followup_tags(tags: list[str]) -> list[str]:
    rewritten: list[str] = []
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag or tag in PENDING_QUESTION_TAGS or tag in {"booking", "time"}:
            continue
        if tag not in rewritten:
            rewritten.append(tag)
    if "reschedule" not in rewritten:
        rewritten.insert(0, "reschedule")
    return rewritten


def _reschedule_followup_expect_override() -> dict[str, Any]:
    return {
        "action": "handoff",
        "state": "pending",
        "expected_reply": True,
    }


def _rewrite_check_booking_followup_tags(tags: list[str]) -> list[str]:
    rewritten: list[str] = []
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag or tag == "booking":
            continue
        if tag not in rewritten:
            rewritten.append(tag)
    if "check_booking" not in rewritten:
        rewritten.insert(0, "check_booking")
    return rewritten


def _check_booking_followup_expect_override() -> dict[str, Any]:
    return {
        "expected_reply": True,
    }


def _time_collect_expect_override() -> dict[str, Any]:
    return {
        "reply_type": "time",
        "expected_reply": True,
        "meta_any": {
            "expected_reply_type": ["time"],
        },
        "trace_contains": [
            {
                "stage": "question_contract",
                "expected_reply_type": "time",
            }
        ],
    }


def _advance_pending_question_context(
    active_reply_type: str | None,
    *,
    tags: list[str],
    expect: dict[str, Any] | None,
) -> str | None:
    reply_type = str((expect or {}).get("reply_type") or "").strip().lower() or None
    if reply_type == "service_choice" and _expectation_has_contract_reason(
        expect,
        "multi_service_booking_clarify",
    ):
        return None
    if reply_type:
        return reply_type
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if lowered_tags & PENDING_QUESTION_CONTEXT_PRESERVE_TAGS:
        return active_reply_type
    return None


def _advance_multi_service_clarify_context(
    multi_service_clarify_active: bool,
    *,
    tags: list[str],
    expect: dict[str, Any] | None,
) -> bool:
    if _expectation_has_contract_reason(expect, "multi_service_booking_clarify"):
        return True
    if not multi_service_clarify_active:
        return False

    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if lowered_tags & (
        {"booking", "time", "name", "phone", "confirm"}
        | PENDING_QUESTION_TAGS
        | {"slot_compare", "slot_constraint"}
    ):
        return False
    return bool(
        lowered_tags
        & (ACTIVE_PENDING_QUESTION_INFO_INTERRUPT_TAGS | {"info", "media", "photo", "interrupt"})
    )


def _expectation_has_contract_reason(
    expect: dict[str, Any] | None,
    reason: str,
) -> bool:
    normalized_reason = str(reason or "").strip().lower()
    if not normalized_reason:
        return False

    meta = dict((expect or {}).get("meta") or {})
    meta_reason = str(meta.get("expected_reply_contract_reason") or "").strip().lower()
    if meta_reason == normalized_reason:
        return True

    meta_any = dict((expect or {}).get("meta_any") or {})
    meta_any_reasons = meta_any.get("expected_reply_contract_reason")
    if isinstance(meta_any_reasons, str):
        meta_any_reasons = [meta_any_reasons]
    if isinstance(meta_any_reasons, list):
        for item in meta_any_reasons:
            item_reason = str(item or "").strip().lower()
            if item_reason == normalized_reason:
                return True

    for entry in (expect or {}).get("trace_contains") or []:
        if not isinstance(entry, dict):
            continue
        entry_reason = str(entry.get("reason") or "").strip().lower()
        if entry_reason == normalized_reason:
            return True
    return False


def _advance_partial_date_anchor_context(
    partial_date_anchor_active: bool,
    *,
    active_reply_type: str | None,
    tags: list[str],
    text: str | None,
    expect: dict[str, Any] | None,
) -> bool:
    if active_reply_type != "time":
        return False
    if _looks_like_partial_date_fill_without_availability_query(text):
        return True
    next_reply_type = str((expect or {}).get("reply_type") or "").strip().lower() or None
    if next_reply_type != "time":
        return False
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if lowered_tags & ACTIVE_PENDING_QUESTION_INFO_INTERRUPT_TAGS:
        if not _expectation_has_contract_reason(
            expect,
            "catalog_service_booking_progress",
        ):
            return False
    return partial_date_anchor_active


def _sanitize_llm_turns(
    turns: list[dict[str, Any]], ctx: dict[str, str], rng: random.Random
) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    active_reply_type: str | None = None
    partial_date_anchor_active = False
    multi_service_clarify_active = False
    active_management_tag: str | None = None
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        tags = list(turn.get("tags") or [])
        text = str(turn.get("text") or "").strip()
        kind = turn.get("kind") or "text"
        if kind != "media":
            kind = "text"
            if (
                not text
                or _looks_like_assistant_turn(text)
                or not _text_matches_tag_contract(text, tags)
            ):
                text = _fallback_text_for_tags(tags, ctx, rng)
        if not text:
            text = _fallback_text_for_tags(tags, ctx, rng)
        original_tags = list(tags)
        tags, malformed_check_booking_normalized = _normalize_malformed_check_booking_tags(
            text,
            tags,
        )
        tags = _normalize_pending_question_tags(text, tags)
        tags = _normalize_stateful_booking_tags(
            text,
            tags,
            active_reply_type=active_reply_type,
        )
        tags, active_time_specialist_master_normalized = _normalize_active_time_specialist_master_tags(
            text,
            tags,
            active_reply_type=active_reply_type,
        )
        tags, active_name_master_info_normalized = _normalize_active_name_master_info_tags(
            text,
            tags,
            active_reply_type=active_reply_type,
        )
        tags, active_time_master_info_normalized = _normalize_active_time_master_info_tags(
            text,
            tags,
            active_reply_type=active_reply_type,
        )
        tags, booking_time_fill_normalized = _normalize_active_time_booking_fill_tags(
            text,
            tags,
            active_reply_type=active_reply_type,
        )
        tags, booking_requested_slot_normalized = _normalize_booking_requested_slot_question_tags(
            text,
            tags,
            active_reply_type=active_reply_type,
        )
        tags, slot_constraint_requested_slot_normalized = (
            _normalize_slot_constraint_requested_slot_question_tags(
                text,
                tags,
                active_reply_type=active_reply_type,
            )
        )
        tags, slot_compare_requested_slot_normalized = (
            _normalize_slot_compare_requested_slot_question_tags(
                text,
                tags,
                active_reply_type=active_reply_type,
            )
        )
        tags, slot_compare_partial_date_constraint_normalized = (
            _normalize_slot_compare_partial_date_constraint_tags(
                text,
                tags,
                active_reply_type=active_reply_type,
            )
        )
        tags, slot_constraint_answer_normalized = _normalize_slot_constraint_answer_tags(
            text,
            tags,
            active_reply_type=active_reply_type,
        )
        tags, partial_date_slot_constraint_normalized = _normalize_partial_date_slot_constraint_tags(
            text,
            tags,
            active_reply_type=active_reply_type,
        )
        tags, grounded_time_probe_normalized = _normalize_grounded_time_probe_tags(
            text,
            tags,
            active_reply_type=active_reply_type,
        )
        tags, slot_compare_exact_time_normalized = _normalize_slot_compare_exact_time_fill_tags(
            text,
            tags,
            active_reply_type=active_reply_type,
        )
        tags, grounded_partial_date_mixed_fill_normalized = (
            _normalize_grounded_partial_date_mixed_fill_tags(
                text,
                tags,
                active_reply_type=active_reply_type,
                partial_date_anchor_active=partial_date_anchor_active,
            )
        )
        tags, question_like_slot_constraint_normalized = _normalize_question_like_slot_constraint_tags(
            text,
            tags,
            active_reply_type=active_reply_type,
        )
        tags, partial_date_mixed_normalized = _normalize_partial_date_mixed_question_tags(
            text,
            tags,
            active_reply_type=active_reply_type,
        )
        tags, grounded_time_specialist_availability_normalized = (
            _normalize_grounded_time_specialist_availability_tags(
                text,
                tags,
                active_reply_type=active_reply_type,
            )
        )
        check_booking_followup_normalized = _looks_like_check_booking_followup(text, tags)
        reschedule_followup_normalized = bool(
            active_management_tag == "reschedule" and _looks_like_reschedule_followup(text, tags)
        )
        if check_booking_followup_normalized:
            tags = _rewrite_check_booking_followup_tags(tags)
            turn["expect"] = _check_booking_followup_expect_override()
        elif reschedule_followup_normalized:
            tags = _rewrite_reschedule_followup_tags(tags)
            turn["expect"] = _reschedule_followup_expect_override()
        elif _has_orphan_pending_question_tags(tags, active_reply_type=active_reply_type):
            tags = _rewrite_orphan_pending_question_tags(tags)
            turn["expect"] = _orphan_pending_question_expect_override()
        elif active_time_specialist_master_normalized:
            turn["expect"] = (
                _orphan_pending_question_expect_override()
                if active_reply_type is None
                else {}
            )
        elif malformed_check_booking_normalized:
            turn["expect"] = {}
        elif active_name_master_info_normalized:
            turn["expect"] = {}
        elif active_time_master_info_normalized:
            turn["expect"] = {}
        elif booking_time_fill_normalized:
            turn["expect"] = {}
        elif booking_requested_slot_normalized:
            turn["expect"] = {}
        elif slot_constraint_requested_slot_normalized:
            turn["expect"] = {}
        elif slot_compare_requested_slot_normalized:
            turn["expect"] = {}
        elif slot_compare_partial_date_constraint_normalized:
            turn["expect"] = {}
        elif slot_constraint_answer_normalized:
            turn["expect"] = {}
        elif partial_date_slot_constraint_normalized:
            turn["expect"] = _time_collect_expect_override()
        elif grounded_time_probe_normalized:
            turn["expect"] = {}
        elif slot_compare_exact_time_normalized:
            turn["expect"] = {}
        elif grounded_partial_date_mixed_fill_normalized:
            turn["expect"] = {}
        elif question_like_slot_constraint_normalized:
            turn["expect"] = {}
        elif partial_date_mixed_normalized:
            turn["expect"] = _time_collect_expect_override()
        elif grounded_time_specialist_availability_normalized:
            turn["expect"] = {}
        turn["kind"] = kind
        turn["text"] = text
        turn["tags"] = tags
        turn["expect"] = _merge_expectations(tags, turn.get("expect"), text=text)
        turn["expect"] = _apply_multi_service_booking_clarify_expectations(
            turn["expect"],
            tags=tags,
            text=text,
            ctx=ctx,
        )
        turn["expect"] = _apply_service_grounded_booking_expectations(
            turn["expect"],
            tags=tags,
            text=text,
            ctx=ctx,
        )
        turn["expect"] = _apply_ambiguous_time_fill_expectations(
            turn["expect"],
            tags=tags,
            text=text,
            active_reply_type=active_reply_type,
        )
        turn["expect"] = _apply_exact_time_fill_collect_expectations(
            turn["expect"],
            tags=tags,
            text=text,
            active_reply_type=active_reply_type,
        )
        turn["expect"] = _apply_partial_date_fill_collect_expectations(
            turn["expect"],
            tags=tags,
            text=text,
            active_reply_type=active_reply_type,
        )
        turn["expect"] = _apply_grounded_partial_date_daypart_fill_expectations(
            turn["expect"],
            original_tags=original_tags,
            tags=tags,
            text=text,
            active_reply_type=active_reply_type,
            partial_date_anchor_active=partial_date_anchor_active,
        )
        turn["expect"] = _clear_multi_service_info_interrupt_followup_expectations(
            turn["expect"],
            tags=tags,
            multi_service_clarify_active=multi_service_clarify_active,
        )
        turn["expect"] = _apply_active_pending_question_info_interrupt_expectations(
            turn["expect"],
            tags=tags,
            active_reply_type=active_reply_type,
        )
        turn["expect"] = _apply_service_grounded_booking_progress_interrupt_expectations(
            turn["expect"],
            tags=tags,
            text=text,
            ctx=ctx,
            active_reply_type=active_reply_type,
        )
        turn["expect"] = _apply_active_pending_question_cancel_interrupt_expectations(
            turn["expect"],
            tags=tags,
            active_reply_type=active_reply_type,
        )
        turn["expect"] = _apply_active_time_specialist_followup_expectations(
            turn["expect"],
            tags=tags,
            text=text,
            active_reply_type=active_reply_type,
        )
        turn["expect"] = _apply_pending_specialist_availability_followup_expectations(
            turn["expect"],
            original_tags=original_tags,
            tags=tags,
            text=text,
            active_reply_type=active_reply_type,
        )
        turn["expect"] = _apply_grounded_time_specialist_availability_transition_expectations(
            turn["expect"],
            original_tags=original_tags,
            tags=tags,
            text=text,
            active_reply_type=active_reply_type,
        )
        turn["expect"] = _apply_pending_master_info_interrupt_expectations(
            turn["expect"],
            original_tags=original_tags,
            tags=tags,
            text=text,
            active_reply_type=active_reply_type,
        )
        turn["expect"] = _apply_active_name_master_info_interrupt_expectations(
            turn["expect"],
            original_tags=original_tags,
            tags=tags,
            text=text,
            active_reply_type=active_reply_type,
        )
        turn["expect"] = _apply_active_time_master_info_interrupt_expectations(
            turn["expect"],
            original_tags=original_tags,
            tags=tags,
            text=text,
            active_reply_type=active_reply_type,
        )
        turn["expect"] = _apply_active_name_time_availability_followup_expectations(
            turn["expect"],
            original_tags=original_tags,
            tags=tags,
            text=text,
            active_reply_type=active_reply_type,
        )
        active_reply_type = _advance_pending_question_context(
            active_reply_type,
            tags=tags,
            expect=turn["expect"],
        )
        partial_date_anchor_active = _advance_partial_date_anchor_context(
            partial_date_anchor_active,
            active_reply_type=active_reply_type,
            tags=tags,
            text=text,
            expect=turn["expect"],
        )
        lowered_tags = {
            str(tag).strip().lower()
            for tag in tags
            if isinstance(tag, str) and str(tag).strip()
        }
        multi_service_clarify_active = _advance_multi_service_clarify_context(
            multi_service_clarify_active,
            tags=tags,
            expect=turn["expect"],
        )
        if "reschedule" in lowered_tags:
            active_management_tag = "reschedule"
        elif "check_booking" in lowered_tags:
            active_management_tag = "check_booking"
        sanitized.append(turn)
    return sanitized


def _default_expect() -> dict[str, Any]:
    return {
        "action": None,
        "info_sections": [],
        "reply_type": None,
        "state": "bot_active",
        "expected_reply": None,
        "allow_booking_stall": False,
    }

def _prune_turns(turns: list[dict[str, Any]], max_turns: int, required_tags: set[str]) -> list[dict[str, Any]]:
    if len(turns) <= max_turns:
        return turns
    keep_indices = []
    for idx, turn in enumerate(turns):
        tags = set(turn.get("tags") or [])
        if tags & required_tags or "media" in tags:
            keep_indices.append(idx)
    selected: list[dict[str, Any]] = []
    used = set()
    for idx in keep_indices:
        if len(selected) >= max_turns:
            return selected[:max_turns]
        selected.append(turns[idx])
        used.add(idx)
    if len(selected) >= max_turns:
        return selected[:max_turns]
    for idx, turn in enumerate(turns):
        if idx in used:
            continue
        selected.append(turn)
        if len(selected) >= max_turns:
            break
    return selected

def _ensure_required_tags(
    turns: list[dict[str, Any]],
    ctx: dict[str, str],
    *,
    max_turns: int,
    coverage: list[str] | None = None,
) -> list[dict[str, Any]]:
    required_tags = _required_llm_tags(coverage)
    existing = {tag for turn in turns for tag in (turn.get("tags") or [])}
    missing = [tag for tag in required_tags if tag not in existing]
    if missing:
        for tag in missing:
            template = REQUIRED_LLM_TURNS.get(tag)
            if not template:
                continue
            formatted = _format_turn(template, ctx)
            if tag == "booking":
                turns.insert(0, formatted)
            else:
                turns.append(formatted)
    return _prune_turns(turns, max_turns, set(required_tags))


def _dialog_tag_set(dialog: dict[str, Any]) -> set[str]:
    tags: set[str] = set()
    turns = dialog.get("turns")
    if not isinstance(turns, list):
        return tags
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        for raw_tag in turn.get("tags") or []:
            if not isinstance(raw_tag, str):
                continue
            tag = raw_tag.strip().lower()
            if tag:
                tags.add(tag)
    return tags


def _select_dialog_for_booking_management_tag(
    dialogs: list[dict[str, Any]],
    *,
    tag: str,
    exclude: set[int] | None = None,
) -> int | None:
    exclude = exclude or set()
    candidates: list[tuple[int, int]] = []
    for idx, dialog in enumerate(dialogs):
        if idx in exclude:
            continue
        tag_set = _dialog_tag_set(dialog)
        if "booking" not in tag_set or tag in tag_set:
            continue
        score = 0
        if tag == "confirm":
            if "check_booking" in tag_set:
                continue
            if "name" in tag_set:
                score += 3
            if "time" in tag_set:
                score += 2
            if "phone" in tag_set:
                score += 1
        elif tag == "check_booking":
            if "confirm" in tag_set:
                continue
            if "booking" in tag_set:
                score += 2
            if "time" in tag_set:
                score += 1
        candidates.append((score, idx))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return candidates[0][1]


def _ensure_booking_management_coverage(
    dialogs: list[dict[str, Any]],
    *,
    coverage: list[str] | None,
    max_turns: int,
    rng: random.Random,
    scenario_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    coverage_tokens = {
        str(item).strip().lower()
        for item in (coverage or [])
        if isinstance(item, str) and str(item).strip()
    }
    if "booking" not in coverage_tokens or not dialogs:
        return dialogs

    present_tags = {tag for dialog in dialogs for tag in _dialog_tag_set(dialog)}
    missing = [tag for tag in REQUIRED_BOOKING_CONFIRM_TAGS if tag not in present_tags]
    if not missing:
        return dialogs

    reserved_dialogs: set[int] = set()
    for tag in missing:
        target_idx = _select_dialog_for_booking_management_tag(
            dialogs,
            tag=tag,
            exclude=reserved_dialogs,
        )
        if target_idx is None:
            target_idx = 0
        dialog = dialogs[target_idx]
        turns = list(dialog.get("turns") or [])
        ctx = _infer_context_from_dialog(dialog, rng, scenario_context=scenario_context)
        turns.append(_format_turn(REQUIRED_LLM_TURNS[tag], ctx))
        dialog["turns"] = _prune_turns(
            turns,
            max_turns,
            set(_required_llm_tags(coverage)) | {tag},
        )
        dialogs[target_idx] = dialog
        reserved_dialogs.add(target_idx)
    return dialogs


def _repair_post_coverage_orphan_pending_question_turns(
    dialogs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    repaired_dialogs: list[dict[str, Any]] = []
    for dialog in dialogs:
        if not isinstance(dialog, dict):
            continue
        normalized_dialog = dict(dialog)
        turns = list(normalized_dialog.get("turns") or [])
        active_reply_type: str | None = None
        partial_date_anchor_active = False
        multi_service_clarify_active = False
        active_management_tag: str | None = None
        repaired_turns: list[dict[str, Any]] = []
        for turn in turns:
            if not isinstance(turn, dict):
                continue
            normalized_turn = dict(turn)
            raw_tags = normalized_turn.get("tags") or []
            tags = [
                str(tag).strip().lower()
                for tag in raw_tags
                if isinstance(tag, str) and str(tag).strip()
            ]
            rewritten_check_booking_tags, malformed_check_booking_normalized = (
                _normalize_malformed_check_booking_tags(
                    str(normalized_turn.get("text") or ""),
                    tags,
                )
            )
            if malformed_check_booking_normalized:
                tags = rewritten_check_booking_tags
            rewritten_tags, active_time_specialist_master_normalized = (
                _normalize_active_time_specialist_master_tags(
                    str(normalized_turn.get("text") or ""),
                    tags,
                    active_reply_type=active_reply_type,
                )
            )
            rewritten_active_time_master_tags, active_time_master_info_normalized = (
                _normalize_active_time_master_info_tags(
                    str(normalized_turn.get("text") or ""),
                    tags,
                    active_reply_type=active_reply_type,
                )
            )
            rewritten_requested_slot_tags, booking_requested_slot_normalized = (
                _normalize_booking_requested_slot_question_tags(
                    str(normalized_turn.get("text") or ""),
                    tags,
                    active_reply_type=active_reply_type,
                )
            )
            rewritten_slot_constraint_requested_slot_tags, slot_constraint_requested_slot_normalized = (
                _normalize_slot_constraint_requested_slot_question_tags(
                    str(normalized_turn.get("text") or ""),
                    tags,
                    active_reply_type=active_reply_type,
                )
            )
            rewritten_slot_compare_requested_slot_tags, slot_compare_requested_slot_normalized = (
                _normalize_slot_compare_requested_slot_question_tags(
                    str(normalized_turn.get("text") or ""),
                    tags,
                    active_reply_type=active_reply_type,
                )
            )
            (
                rewritten_slot_compare_partial_date_constraint_tags,
                slot_compare_partial_date_constraint_normalized,
            ) = _normalize_slot_compare_partial_date_constraint_tags(
                str(normalized_turn.get("text") or ""),
                tags,
                active_reply_type=active_reply_type,
            )
            rewritten_slot_compare_tags, slot_compare_exact_time_normalized = (
                _normalize_slot_compare_exact_time_fill_tags(
                    str(normalized_turn.get("text") or ""),
                    tags,
                    active_reply_type=active_reply_type,
                )
            )
            (
                rewritten_grounded_partial_date_tags,
                grounded_partial_date_mixed_fill_normalized,
            ) = _normalize_grounded_partial_date_mixed_fill_tags(
                str(normalized_turn.get("text") or ""),
                tags,
                active_reply_type=active_reply_type,
                partial_date_anchor_active=partial_date_anchor_active,
            )
            if slot_compare_exact_time_normalized:
                normalized_turn["tags"] = rewritten_slot_compare_tags
                normalized_turn["expect"] = _merge_expectations(
                    rewritten_slot_compare_tags,
                    {},
                    text=str(normalized_turn.get("text") or ""),
                )
            elif booking_requested_slot_normalized:
                normalized_turn["tags"] = rewritten_requested_slot_tags
                normalized_turn["expect"] = _merge_expectations(
                    rewritten_requested_slot_tags,
                    {},
                    text=str(normalized_turn.get("text") or ""),
                )
            elif slot_constraint_requested_slot_normalized:
                normalized_turn["tags"] = rewritten_slot_constraint_requested_slot_tags
                normalized_turn["expect"] = _merge_expectations(
                    rewritten_slot_constraint_requested_slot_tags,
                    {},
                    text=str(normalized_turn.get("text") or ""),
                )
            elif slot_compare_requested_slot_normalized:
                normalized_turn["tags"] = rewritten_slot_compare_requested_slot_tags
                normalized_turn["expect"] = _merge_expectations(
                    rewritten_slot_compare_requested_slot_tags,
                    {},
                    text=str(normalized_turn.get("text") or ""),
                )
            elif slot_compare_partial_date_constraint_normalized:
                normalized_turn["tags"] = rewritten_slot_compare_partial_date_constraint_tags
                normalized_turn["expect"] = _merge_expectations(
                    rewritten_slot_compare_partial_date_constraint_tags,
                    {},
                    text=str(normalized_turn.get("text") or ""),
                )
            elif grounded_partial_date_mixed_fill_normalized:
                normalized_turn["tags"] = rewritten_grounded_partial_date_tags
                normalized_turn["expect"] = _merge_expectations(
                    rewritten_grounded_partial_date_tags,
                    {},
                    text=str(normalized_turn.get("text") or ""),
                )
            elif malformed_check_booking_normalized:
                normalized_turn["tags"] = rewritten_check_booking_tags
                normalized_turn["expect"] = _merge_expectations(
                    rewritten_check_booking_tags,
                    {},
                    text=str(normalized_turn.get("text") or ""),
                )
            elif active_time_specialist_master_normalized:
                normalized_turn["tags"] = rewritten_tags
                normalized_turn["expect"] = _merge_expectations(
                    rewritten_tags,
                    _orphan_pending_question_expect_override()
                    if active_reply_type is None
                    else {},
                    text=str(normalized_turn.get("text") or ""),
                )
            elif active_time_master_info_normalized:
                normalized_turn["tags"] = rewritten_active_time_master_tags
                normalized_turn["expect"] = _merge_expectations(
                    rewritten_active_time_master_tags,
                    {},
                    text=str(normalized_turn.get("text") or ""),
                )
            elif _looks_like_check_booking_followup(
                str(normalized_turn.get("text") or ""),
                tags,
            ):
                rewritten_tags = _rewrite_check_booking_followup_tags(tags)
                normalized_turn["tags"] = rewritten_tags
                normalized_turn["expect"] = _merge_expectations(
                    rewritten_tags,
                    _check_booking_followup_expect_override(),
                    text=str(normalized_turn.get("text") or ""),
                )
            elif active_management_tag == "reschedule" and _looks_like_reschedule_followup(
                str(normalized_turn.get("text") or ""),
                tags,
            ):
                rewritten_tags = _rewrite_reschedule_followup_tags(tags)
                normalized_turn["tags"] = rewritten_tags
                normalized_turn["expect"] = _merge_expectations(
                    rewritten_tags,
                    _reschedule_followup_expect_override(),
                    text=str(normalized_turn.get("text") or ""),
                )
            elif _has_orphan_pending_question_tags(tags, active_reply_type=active_reply_type):
                rewritten_tags = _rewrite_orphan_pending_question_tags(tags)
                normalized_turn["tags"] = rewritten_tags
                normalized_turn["expect"] = _merge_expectations(
                    rewritten_tags,
                    _orphan_pending_question_expect_override(),
                    text=str(normalized_turn.get("text") or ""),
                )
            expectations = (
                normalized_turn.get("expect")
                if isinstance(normalized_turn.get("expect"), dict)
                else {}
            )
            expectations = _apply_multi_service_booking_clarify_expectations(
                expectations,
                tags=normalized_turn.get("tags") or [],
                text=str(normalized_turn.get("text") or ""),
                ctx=None,
            )
            expectations = _apply_active_pending_question_info_interrupt_expectations(
                expectations,
                tags=normalized_turn.get("tags") or [],
                active_reply_type=active_reply_type,
            )
            expectations = _clear_multi_service_info_interrupt_followup_expectations(
                expectations,
                tags=normalized_turn.get("tags") or [],
                multi_service_clarify_active=multi_service_clarify_active,
            )
            expectations = _apply_service_grounded_booking_progress_interrupt_expectations(
                expectations,
                tags=normalized_turn.get("tags") or [],
                text=str(normalized_turn.get("text") or ""),
                ctx=None,
                active_reply_type=active_reply_type,
            )
            expectations = _apply_active_pending_question_cancel_interrupt_expectations(
                expectations,
                tags=normalized_turn.get("tags") or [],
                active_reply_type=active_reply_type,
            )
            expectations = _apply_exact_time_fill_collect_expectations(
                expectations,
                tags=normalized_turn.get("tags") or [],
                text=str(normalized_turn.get("text") or ""),
                active_reply_type=active_reply_type,
            )
            expectations = _apply_partial_date_fill_collect_expectations(
                expectations,
                tags=normalized_turn.get("tags") or [],
                text=str(normalized_turn.get("text") or ""),
                active_reply_type=active_reply_type,
            )
            expectations = _apply_grounded_partial_date_daypart_fill_expectations(
                expectations,
                original_tags=raw_tags,
                tags=normalized_turn.get("tags") or [],
                text=str(normalized_turn.get("text") or ""),
                active_reply_type=active_reply_type,
                partial_date_anchor_active=partial_date_anchor_active,
            )
            expectations = _apply_active_time_specialist_followup_expectations(
                expectations,
                tags=normalized_turn.get("tags") or [],
                text=str(normalized_turn.get("text") or ""),
                active_reply_type=active_reply_type,
            )
            expectations = _apply_active_time_master_info_interrupt_expectations(
                expectations,
                original_tags=raw_tags,
                tags=normalized_turn.get("tags") or [],
                text=str(normalized_turn.get("text") or ""),
                active_reply_type=active_reply_type,
            )
            expectations = _apply_active_name_time_availability_followup_expectations(
                expectations,
                original_tags=raw_tags,
                tags=normalized_turn.get("tags") or [],
                text=str(normalized_turn.get("text") or ""),
                active_reply_type=active_reply_type,
            )
            normalized_turn["expect"] = expectations
            active_reply_type = _advance_pending_question_context(
                active_reply_type,
                tags=normalized_turn.get("tags") or [],
                expect=expectations,
            )
            partial_date_anchor_active = _advance_partial_date_anchor_context(
                partial_date_anchor_active,
                active_reply_type=active_reply_type,
                tags=normalized_turn.get("tags") or [],
                text=str(normalized_turn.get("text") or ""),
                expect=expectations,
            )
            lowered_tags = {
                str(tag).strip().lower()
                for tag in (normalized_turn.get("tags") or [])
                if isinstance(tag, str) and str(tag).strip()
            }
            multi_service_clarify_active = _advance_multi_service_clarify_context(
                multi_service_clarify_active,
                tags=normalized_turn.get("tags") or [],
                expect=expectations,
            )
            if "reschedule" in lowered_tags:
                active_management_tag = "reschedule"
            elif "check_booking" in lowered_tags:
                active_management_tag = "check_booking"
            repaired_turns.append(normalized_turn)
        normalized_dialog["turns"] = repaired_turns
        repaired_dialogs.append(normalized_dialog)
    return repaired_dialogs

def _normalize_expect_token(token: Any, allowed: set[str] | None) -> str | None:
    if token is None:
        return None
    value = str(token).strip()
    if not value:
        return None
    lowered = value.lower()
    if lowered in {"none", "null"}:
        return None
    if allowed is not None and lowered not in allowed:
        return None
    return lowered

def _normalize_expect_value(value: Any, allowed: set[str] | None) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        tokens = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, list):
        tokens = [str(item).strip() for item in value if str(item).strip()]
    else:
        return None
    normalized = []
    for token in tokens:
        clean = _normalize_expect_token(token, allowed)
        if clean is not None:
            normalized.append(clean)
    if not normalized:
        return None
    if len(normalized) == 1:
        return normalized[0]
    return normalized

def _normalize_expected_reply(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return None


def _normalize_expect_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        key = raw_key.strip()
        if isinstance(raw_value, (str, int, float, bool)) or raw_value is None:
            normalized[key] = raw_value
            continue
        if isinstance(raw_value, list):
            cleaned = [
                item
                for item in raw_value
                if isinstance(item, (str, int, float, bool)) or item is None
            ]
            if cleaned:
                normalized[key] = cleaned
    return normalized


def _normalize_expect_contains_mapping(value: Any) -> dict[str, list[Any]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, list[Any]] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        key = raw_key.strip()
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        cleaned = [
            item
            for item in values
            if isinstance(item, (str, int, float, bool)) or item is None
        ]
        if cleaned:
            normalized[key] = cleaned
    return normalized


def _normalize_expect_trace_contains(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in value:
        mapping = _normalize_expect_mapping(item)
        if mapping:
            normalized.append(mapping)
    return normalized

def _normalize_llm_expect_override(override: Any) -> dict[str, Any]:
    if not isinstance(override, dict):
        return {}
    action = _normalize_expect_value(override.get("action"), set(CANONICAL_EXPECT_ACTIONS))
    info_sections = _normalize_expect_value(
        override.get("info_sections"), set(CANONICAL_EXPECT_INFO_SECTIONS)
    )
    if isinstance(info_sections, str):
        info_sections = [info_sections]
    reply_type = _normalize_expect_value(
        override.get("reply_type"), set(CANONICAL_EXPECT_REPLY_TYPES)
    )
    state = _normalize_expect_value(override.get("state"), set(CANONICAL_EXPECT_STATES))
    expected_reply = _normalize_expected_reply(override.get("expected_reply"))
    return {
        "action": action,
        "info_sections": info_sections,
        "reply_type": reply_type,
        "state": state,
        "expected_reply": expected_reply,
        "meta": _normalize_expect_mapping(override.get("meta")),
        "meta_any": _normalize_expect_contains_mapping(override.get("meta_any")),
        "meta_contains": _normalize_expect_contains_mapping(override.get("meta_contains")),
        "trace_contains": _normalize_expect_trace_contains(override.get("trace_contains")),
    }


def _sanitize_expect_state_by_tags(tags: list[str], state: Any) -> Any:
    if state is None:
        return None
    tag_set = {tag for tag in tags if isinstance(tag, str)}
    allow_pending = bool(tag_set & {"handoff", "human", "pending", "cancel", "reschedule"})
    allow_manager_active = bool(tag_set & {"handoff", "human", "pending"})

    def _allow(token: str | None) -> bool:
        if token is None:
            return True
        if token == "bot_active":
            return True
        if token == "pending":
            return allow_pending
        if token == "manager_active":
            return allow_manager_active
        return False

    if isinstance(state, list):
        cleaned = []
        for token in state:
            value = token if isinstance(token, str) else None
            if _allow(value):
                cleaned.append(value)
        if not cleaned:
            return None
        if len(cleaned) == 1:
            return cleaned[0]
        return cleaned

    token = state if isinstance(state, str) else None
    return token if _allow(token) else None


def _sanitize_expect_action_by_tags(tags: list[str], action: Any) -> Any:
    if action is None:
        return None
    tag_set = {tag for tag in tags if isinstance(tag, str)}
    allow_handoff = bool(tag_set & {"handoff", "human", "pending", "cancel", "reschedule"})

    def _allow(token: str | None) -> bool:
        if token is None:
            return True
        if token in {"booking_escalated", "escalate", "handoff"}:
            return allow_handoff
        return False

    if isinstance(action, list):
        cleaned = []
        for token in action:
            value = token if isinstance(token, str) else None
            if _allow(value):
                cleaned.append(value)
        if not cleaned:
            return None
        if len(cleaned) == 1:
            return cleaned[0]
        return cleaned

    token = action if isinstance(action, str) else None
    return token if _allow(token) else None


def _sanitize_expect_override_for_tags(
    override: Any,
    *,
    tags: list[str],
) -> Any:
    if not isinstance(override, dict):
        return override
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "mixed_fill_plus_question" not in lowered_tags:
        return override

    cleaned = _normalize_llm_expect_override(override)
    for key in ("meta", "meta_any", "meta_contains"):
        mapping = cleaned.get(key)
        if not isinstance(mapping, dict):
            continue
        normalized_mapping = dict(mapping)
        normalized_mapping.pop("pending_question_act", None)
        normalized_mapping.pop("pending_question_target", None)
        if normalized_mapping:
            cleaned[key] = normalized_mapping
        else:
            cleaned.pop(key, None)

    trace_contains = [
        dict(entry)
        for entry in (cleaned.get("trace_contains") or [])
        if entry.get("stage") != "pending_question_interaction"
    ]
    if trace_contains:
        cleaned["trace_contains"] = trace_contains
    else:
        cleaned.pop("trace_contains", None)
    return cleaned


def _merge_expectations(tags: list[str], override: Any, text: str | None = None) -> dict[str, Any]:
    expect = _default_expect()
    tag_set = {
        tag.strip().lower()
        for tag in tags
        if isinstance(tag, str) and tag.strip()
    }
    for tag in tags:
        if tag in EXPECT_INFO_SECTIONS:
            expect["info_sections"].extend(EXPECT_INFO_SECTIONS[tag])
        if tag in EXPECT_ACTION_BY_TAG and expect["action"] is None:
            expect["action"] = EXPECT_ACTION_BY_TAG[tag][:]
        if tag in EXPECT_REPLY_TYPE_BY_TAG and expect["reply_type"] is None:
            expect["reply_type"] = EXPECT_REPLY_TYPE_BY_TAG[tag]
        if tag in EXPECT_STATE_BY_TAG and expect["state"] is None:
            expect["state"] = EXPECT_STATE_BY_TAG[tag]
        if tag in EXPECT_META_ANY_BY_TAG:
            merged_meta_any = dict(expect.get("meta_any") or {})
            for key, values in EXPECT_META_ANY_BY_TAG[tag].items():
                bucket = list(merged_meta_any.get(key) or [])
                for value in values:
                    if value not in bucket:
                        bucket.append(value)
                if bucket:
                    merged_meta_any[key] = bucket
            if merged_meta_any:
                expect["meta_any"] = merged_meta_any
        if tag in EXPECT_TRACE_CONTAINS_BY_TAG:
            merged_trace = list(expect.get("trace_contains") or [])
            for entry in EXPECT_TRACE_CONTAINS_BY_TAG[tag]:
                if entry not in merged_trace:
                    merged_trace.append(dict(entry))
            if merged_trace:
                expect["trace_contains"] = merged_trace
    info_sections = []
    for item in expect["info_sections"]:
        if isinstance(item, str):
            value = item.strip().lower()
            if value and value not in info_sections:
                info_sections.append(value)
    expect["info_sections"] = info_sections
    if isinstance(override, dict):
        override = _sanitize_expect_override_for_tags(override, tags=tags)
        override = _normalize_llm_expect_override(override)
        for key in ("action", "reply_type", "state", "expected_reply"):
            if override.get(key) is not None:
                expect[key] = override.get(key)
        extra_sections = override.get("info_sections") or []
        if isinstance(extra_sections, str):
            extra_sections = [extra_sections]
        for section in extra_sections:
            if section and section not in expect["info_sections"]:
                expect["info_sections"].append(section)
        if override.get("meta"):
            merged_meta = dict(expect.get("meta") or {})
            merged_meta.update(override.get("meta") or {})
            expect["meta"] = merged_meta
        for key in ("meta_any", "meta_contains"):
            if override.get(key):
                merged_mapping = dict(expect.get(key) or {})
                for item_key, item_values in (override.get(key) or {}).items():
                    bucket = list(merged_mapping.get(item_key) or [])
                    for value in item_values:
                        if value not in bucket:
                            bucket.append(value)
                    if bucket:
                        merged_mapping[item_key] = bucket
                expect[key] = merged_mapping
        if override.get("trace_contains"):
            merged_trace = list(expect.get("trace_contains") or [])
            for entry in override.get("trace_contains") or []:
                if entry not in merged_trace:
                    merged_trace.append(entry)
            expect["trace_contains"] = merged_trace
    expect["state"] = _sanitize_expect_state_by_tags(tags, expect.get("state"))
    expect["action"] = _sanitize_expect_action_by_tags(tags, expect.get("action"))
    if expect.get("state") is None:
        # Scenario contract requires at least one strong oracle field per turn.
        # Keep state deterministic-by-default while allowing pending/manager
        # expansion in runtime evaluator based on turn tags.
        expect["state"] = "bot_active"
    if "media" in tag_set:
        # Style/media turns can legally end in pending with an immediate ack.
        # Keep reply expectation open in generated scenarios.
        expect["expected_reply"] = None
    if not any(tag in EXPECT_INFO_SECTIONS for tag in tags):
        expect["info_sections"] = []
    expect = _apply_pending_question_target_expectations(expect, tags=tags, text=text)
    return expect


def _insert_extras(turns: list[dict[str, Any]], extras: list[dict[str, Any]], rng: random.Random, target: int) -> None:
    extra_count = max(0, target - len(turns))
    if extra_count <= 0:
        return
    pool = extras[:]
    rng.shuffle(pool)
    for extra in pool[:extra_count]:
        idx = rng.randint(1, max(1, len(turns) - 1))
        turns.insert(idx, extra)


def _select_templates(
    rng: random.Random,
    *,
    count: int,
    coverage: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    if not coverage:
        return [rng.choice(SCENARIOS) for _ in range(count)], []
    missing: list[str] = []
    coverage_targets = coverage
    if count < len(coverage):
        coverage_targets = rng.sample(coverage, k=count)
        missing = [tag for tag in coverage if tag not in coverage_targets]
    selected: list[dict[str, Any]] = []
    remaining = SCENARIOS[:]
    for tag in coverage_targets:
        matches = [item for item in remaining if tag in (item.get("coverage") or [])]
        if not matches:
            missing.append(tag)
            continue
        choice = rng.choice(matches)
        selected.append(choice)
        remaining.remove(choice)
    while len(selected) < count:
        selected.append(rng.choice(SCENARIOS))
    if len(selected) > count:
        selected = selected[:count]
    rng.shuffle(selected)
    return selected, missing


def _generate_template_dialog(
    rng: random.Random,
    *,
    template: dict[str, Any],
    min_turns: int,
    max_turns: int,
    include_media: bool,
    media_mode: str,
    media_kind: str,
    language_profile: str,
    semantic_variation_profile: str,
    slot_format_profile: str,
    surface_noise_profile: str,
    scenario_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ctx = _build_context(rng, scenario_context=scenario_context)
    turns = [_format_turn(t, ctx) for t in template["turns"]]
    extras = [_format_turn(t, ctx) for t in EXTRA_TURNS] + [_format_turn(t, ctx) for t in INTERRUPTIONS]
    extras += [_format_turn(t, ctx) for t in NOISE]

    if include_media or template.get("requires_media"):
        turns.insert(rng.randint(1, len(turns) - 1), _media_turn(ctx, mode=media_mode, kind=media_kind))

    target = rng.randint(min_turns, max_turns)
    _insert_extras(turns, extras, rng, target)
    turns = _apply_language_profile(turns, ctx, language_profile=language_profile, rng=rng)
    turns = _apply_semantic_variation(
        turns,
        ctx,
        semantic_variation_profile=semantic_variation_profile,
        language_profile=language_profile,
        rng=rng,
    )
    turns = _apply_slot_format_variation(
        turns,
        ctx,
        slot_format_profile=slot_format_profile,
        language_profile=language_profile,
    )
    turns = _apply_surface_noise(turns, ctx, surface_noise_profile=surface_noise_profile, rng=rng)

    return {
        "dialog_id": f"{template['id']}-{rng.randint(1000, 9999)}",
        "goal": template["goal"],
        "language_profile": language_profile,
        "metamorphic_family": _language_profile_family(language_profile),
        "semantic_variation_profile": semantic_variation_profile,
        "semantic_mutation_family": _semantic_variation_family(semantic_variation_profile),
        "slot_format_profile": slot_format_profile,
        "slot_format_family": _slot_format_family(slot_format_profile),
        "surface_noise_profile": surface_noise_profile,
        "surface_mutation_family": _surface_noise_family(surface_noise_profile),
        "turns": turns,
    }


def _validate_dialog(dialog: dict[str, Any], *, min_turns: int, max_turns: int) -> list[str]:
    warnings: list[str] = []
    turns = dialog.get("turns") or []
    if not (min_turns <= len(turns) <= max_turns):
        warnings.append(f"turn_count_out_of_range={len(turns)}")
    tags = {tag for turn in turns for tag in (turn.get("tags") or [])}
    if "booking" not in tags:
        warnings.append("missing_booking_tag")
    if "interrupt" not in tags:
        warnings.append("missing_interrupt_tag")
    if "media" not in tags:
        warnings.append("missing_media_tag")
    for turn in turns:
        expect = turn.get("expect")
        if not isinstance(expect, dict):
            warnings.append("missing_expect_block")
            break
        for key in ("action", "info_sections", "reply_type", "state", "expected_reply", "allow_booking_stall"):
            if key not in expect:
                warnings.append("expect_missing_key")
                break
    return warnings


def _call_openai(
    prompt: str,
    *,
    api_key: str,
    model: str,
    base_url: str,
    request_timeout: float = 40.0,
    max_tokens: int = 1800,
) -> str:
    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": max(256, int(max_tokens)),
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=max(5.0, float(request_timeout))) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = ""
        try:
            raw = exc.read().decode("utf-8", errors="replace")
        except Exception:
            raw = ""
        message = f"openai_http_error_{exc.code}"
        if exc.code == 429:
            message = "openai_rate_or_quota_limited"
        elif exc.code == 401:
            message = "openai_auth_failed"
        elif exc.code == 403:
            message = "openai_forbidden"
        if raw:
            try:
                payload = json.loads(raw)
                error_payload = payload.get("error") if isinstance(payload, dict) else None
                if isinstance(error_payload, dict):
                    code = error_payload.get("code")
                    detail = error_payload.get("message")
                    if isinstance(code, str) and code.strip():
                        message = f"{message} ({code})"
                    if isinstance(detail, str) and detail.strip():
                        message = f"{message}: {detail.strip()}"
            except Exception:
                compact = " ".join(raw.split())
                if compact:
                    message = f"{message}: {compact[:400]}"
        raise RuntimeError(message) from exc
    return body["choices"][0]["message"]["content"]


def _parse_llm_json(content: str, *, repair_fn=None) -> dict[str, Any]:
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        if repair_fn:
            repaired = repair_fn(text)
            if repaired:
                return _parse_llm_json(repaired, repair_fn=None)
        raise


def _repair_llm_json(
    content: str,
    *,
    api_key: str,
    model: str,
    base_url: str,
    request_timeout: float,
) -> str | None:
    if not content:
        return None
    payload = content
    if len(payload) > 20000:
        payload = payload[:20000]
    prompt = (
        "Repair the JSON below and return only a valid JSON object. "
        "Keep the same schema with key 'dialogs'. "
        "Do not add commentary or markdown.\n\n"
        f"Broken JSON:\n{payload}"
    )
    try:
        return _call_openai(
            prompt,
            api_key=api_key,
            model=model,
            base_url=base_url,
            request_timeout=request_timeout,
        )
    except Exception:
        return None


def _generate_llm_dialogs(
    rng: random.Random,
    *,
    count: int,
    min_turns: int,
    max_turns: int,
    include_media: bool,
    media_mode: str,
    media_kind: str,
    model: str,
    base_url: str,
    api_key: str,
    coverage: list[str],
    seed: int | None,
    llm_batch_size: int,
    llm_max_attempts: int,
    llm_request_timeout: float,
    llm_attempt_backoff: float,
    progress_stderr: bool,
    scenario_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    def _emit_progress(payload: dict[str, Any]) -> None:
        if not progress_stderr:
            return
        line = {"stage": "booking_scenario_llm_progress"}
        line.update(payload)
        sys.stderr.write(json.dumps(line, ensure_ascii=False) + "\n")
        sys.stderr.flush()

    dialogs: list[dict[str, Any]] = []
    next_dialog_id = 1
    batch_size = max(1, int(llm_batch_size))
    max_attempts = max(1, int(llm_max_attempts))
    request_timeout = max(5.0, float(llm_request_timeout))
    attempt_backoff = max(0.0, float(llm_attempt_backoff))

    batch_index = 0
    while len(dialogs) < count:
        batch_index += 1
        remaining = count - len(dialogs)
        batch_count = min(batch_size, remaining)
        _emit_progress(
            {
                "event": "batch_start",
                "batch_index": batch_index,
                "batch_count": batch_count,
                "dialogs_ready": len(dialogs),
                "dialogs_target": count,
                "max_attempts": max_attempts,
                "request_timeout": request_timeout,
            }
        )
        prompt = _build_llm_generation_prompt(
            batch_count=batch_count,
            min_turns=min_turns,
            max_turns=max_turns,
            coverage=coverage,
            media_mode=media_mode,
            media_kind=media_kind,
            seed=seed,
            scenario_context=scenario_context,
        )
        max_tokens = max(1800, batch_count * max(min_turns, 10) * 120)
        payload: dict[str, Any] | None = None
        last_error: Exception | None = None
        for attempt_idx in range(max_attempts):
            attempt_no = attempt_idx + 1
            started_at = time.time()
            try:
                content = _call_openai(
                    prompt,
                    api_key=api_key,
                    model=model,
                    base_url=base_url,
                    request_timeout=request_timeout,
                    max_tokens=max_tokens,
                )
                payload = _parse_llm_json(
                    content,
                    repair_fn=lambda raw: _repair_llm_json(
                        raw,
                        api_key=api_key,
                        model=model,
                        base_url=base_url,
                        request_timeout=request_timeout,
                    ),
                )
                raw_dialogs = payload.get("dialogs") if isinstance(payload, dict) else None
                if isinstance(raw_dialogs, list) and raw_dialogs:
                    _emit_progress(
                        {
                            "event": "batch_attempt_success",
                            "batch_index": batch_index,
                            "attempt": attempt_no,
                            "elapsed_ms": round((time.time() - started_at) * 1000, 2),
                            "dialogs_returned": len(raw_dialogs),
                        }
                    )
                    break
                last_error = ValueError("llm payload has no dialogs")
                _emit_progress(
                    {
                        "event": "batch_attempt_empty",
                        "batch_index": batch_index,
                        "attempt": attempt_no,
                        "elapsed_ms": round((time.time() - started_at) * 1000, 2),
                    }
                )
            except Exception as exc:
                payload = None
                last_error = exc
                _emit_progress(
                    {
                        "event": "batch_attempt_error",
                        "batch_index": batch_index,
                        "attempt": attempt_no,
                        "elapsed_ms": round((time.time() - started_at) * 1000, 2),
                        "error": str(exc)[:300],
                    }
                )
            if attempt_no < max_attempts and attempt_backoff > 0.0:
                time.sleep(attempt_backoff * (2 ** attempt_idx))
        raw_dialogs = payload.get("dialogs") if isinstance(payload, dict) else None
        if not isinstance(raw_dialogs, list) or not raw_dialogs:
            if last_error:
                raise last_error
            raise ValueError("llm payload has no dialogs")

        for raw_dialog in raw_dialogs:
            if len(dialogs) >= count:
                break
            if not isinstance(raw_dialog, dict):
                continue
            dialog = dict(raw_dialog)
            turns = dialog.get("turns") or []
            for turn in turns:
                tags = list(turn.get("tags") or [])
                turn["expect"] = _merge_expectations(
                    tags, turn.get("expect"), text=str(turn.get("text") or "")
                )
            ctx = _infer_context_from_dialog(dialog, rng, scenario_context=scenario_context)
            turns = _ensure_required_tags(turns, ctx, max_turns=max_turns, coverage=coverage)
            turns = _sanitize_llm_turns(turns, ctx, rng)
            dialog["turns"] = turns
            dialog["dialog_id"] = dialog.get("dialog_id") or next_dialog_id
            next_dialog_id += 1
            if include_media and all(
                "media" not in (turn.get("tags") or []) for turn in dialog.get("turns", [])
            ):
                dialog.setdefault("turns", []).insert(
                    1, _media_turn(ctx, mode=media_mode, kind=media_kind)
                )
                dialog["turns"] = _prune_turns(
                    dialog["turns"], max_turns, set(_required_llm_tags(coverage))
                )
            dialogs.append(dialog)

    dialogs = _ensure_booking_management_coverage(
        dialogs,
        coverage=coverage,
        max_turns=max_turns,
        rng=rng,
        scenario_context=scenario_context,
    )
    return _repair_post_coverage_orphan_pending_question_turns(dialogs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate booking dialog scenarios.")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--min-turns", type=int, default=10)
    parser.add_argument("--max-turns", type=int, default=15)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output", default="-")
    parser.add_argument("--mode", choices=["template", "llm"], default="template")
    parser.add_argument("--language-profile", choices=list(LANGUAGE_PROFILE_CHOICES), default="ru")
    parser.add_argument(
        "--semantic-variation-profile",
        choices=list(SEMANTIC_VARIATION_PROFILE_CHOICES),
        default="canonical",
    )
    parser.add_argument(
        "--slot-format-profile",
        choices=list(SLOT_FORMAT_PROFILE_CHOICES),
        default="canonical",
    )
    parser.add_argument(
        "--surface-noise-profile",
        choices=list(SURFACE_NOISE_PROFILE_CHOICES),
        default="clean",
    )
    parser.add_argument("--include-media", action="store_true")
    parser.add_argument("--media-mode", choices=["text", "payload"], default="text")
    parser.add_argument("--media-kind", choices=["photo", "audio"], default="photo")
    parser.add_argument("--coverage", default="booking,info,interrupt")
    parser.add_argument("--llm-model", default="gpt-4o-mini")
    parser.add_argument("--llm-base-url", default=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com"))
    parser.add_argument("--llm-api-key", default=os.environ.get("OPENAI_API_KEY"))
    parser.add_argument(
        "--llm-batch-size",
        type=int,
        default=int(os.environ.get("BOOKING_SCENARIO_LLM_BATCH_SIZE", "2")),
    )
    parser.add_argument(
        "--llm-max-attempts",
        type=int,
        default=int(os.environ.get("BOOKING_SCENARIO_LLM_MAX_ATTEMPTS", "3")),
    )
    parser.add_argument(
        "--llm-request-timeout",
        type=float,
        default=float(os.environ.get("BOOKING_SCENARIO_LLM_REQUEST_TIMEOUT_SEC", "60")),
    )
    parser.add_argument(
        "--llm-attempt-backoff",
        type=float,
        default=float(os.environ.get("BOOKING_SCENARIO_LLM_ATTEMPT_BACKOFF_SEC", "0.6")),
    )
    parser.add_argument("--progress-stderr", action="store_true")
    parser.add_argument("--client-slug", default=None)
    parser.add_argument("--branch-slug", default=None)
    parser.add_argument("--scenario-context-file", default=None)
    args = parser.parse_args()
    if args.llm_batch_size < 1:
        raise SystemExit("--llm-batch-size must be >= 1")
    if args.llm_max_attempts < 1:
        raise SystemExit("--llm-max-attempts must be >= 1")
    if args.llm_request_timeout <= 0:
        raise SystemExit("--llm-request-timeout must be > 0")
    if args.llm_attempt_backoff < 0:
        raise SystemExit("--llm-attempt-backoff must be >= 0")
    llm_api_key_source: str | None = None
    if args.mode == "llm":
        resolved_key, resolved_source = _resolve_openai_api_key(args.llm_api_key)
        if resolved_key:
            args.llm_api_key = resolved_key
            llm_api_key_source = resolved_source
            os.environ.setdefault("OPENAI_API_KEY", resolved_key)
        if args.language_profile != "ru":
            raise SystemExit("--language-profile non-ru profiles are currently supported only in template mode")
        if args.semantic_variation_profile != "canonical":
            raise SystemExit(
                "--semantic-variation-profile synonym is currently supported only in template mode"
            )
        if args.slot_format_profile != "canonical":
            raise SystemExit(
                "--slot-format-profile variant is currently supported only in template mode"
            )
        if args.surface_noise_profile != "clean":
            raise SystemExit("--surface-noise-profile typo is currently supported only in template mode")

    rng = random.Random(args.seed or int(time.time()))
    coverage = []
    if args.coverage:
        raw_coverage = [item.strip() for item in args.coverage.split(",") if item.strip()]
        if raw_coverage and raw_coverage != ["none"]:
            coverage = raw_coverage
    scenario_context = _resolve_scenario_context(
        client_slug=args.client_slug,
        branch_slug=args.branch_slug,
        scenario_context_file=args.scenario_context_file,
    )
    missing_coverage: list[str] = []
    dialogs: list[dict[str, Any]] = []
    if args.mode == "llm":
        if not args.llm_api_key:
            raise SystemExit(
                "LLM mode requires OPENAI_API_KEY aliases or --llm-api-key "
                "(checked env and local .env candidates)"
            )
        dialogs = _generate_llm_dialogs(
            rng,
            count=args.count,
            min_turns=args.min_turns,
            max_turns=args.max_turns,
            include_media=args.include_media,
            media_mode=args.media_mode,
            media_kind=args.media_kind,
            model=args.llm_model,
            base_url=args.llm_base_url,
            api_key=args.llm_api_key,
            coverage=coverage,
            seed=args.seed,
            llm_batch_size=args.llm_batch_size,
            llm_max_attempts=args.llm_max_attempts,
            llm_request_timeout=args.llm_request_timeout,
            llm_attempt_backoff=args.llm_attempt_backoff,
            progress_stderr=bool(args.progress_stderr),
            scenario_context=scenario_context,
        )
        if not dialogs:
            raise SystemExit("LLM mode returned empty dialogs")
    else:
        templates, missing_coverage = _select_templates(rng, count=args.count, coverage=coverage)
        for template in templates:
            dialogs.append(
                _generate_template_dialog(
                    rng,
                    template=template,
                    min_turns=args.min_turns,
                    max_turns=args.max_turns,
                    include_media=args.include_media,
                    media_mode=args.media_mode,
                    media_kind=args.media_kind,
                    language_profile=args.language_profile,
                    semantic_variation_profile=args.semantic_variation_profile,
                    slot_format_profile=args.slot_format_profile,
                    surface_noise_profile=args.surface_noise_profile,
                    scenario_context=scenario_context,
                )
            )

    warnings: dict[str, list[str]] = {}
    if args.mode == "template" and args.coverage and missing_coverage:
        warnings["coverage"] = [f"missing_coverage_tag={tag}" for tag in missing_coverage]
    for dialog in dialogs:
        dialog_warnings = _validate_dialog(dialog, min_turns=args.min_turns, max_turns=args.max_turns)
        if dialog_warnings:
            warnings[dialog.get("dialog_id", "dialog")] = dialog_warnings

    output = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": args.seed,
        "mode": args.mode,
        "client_slug": args.client_slug,
        "branch_slug": args.branch_slug,
        "language_profile": args.language_profile,
        "semantic_variation_profile": args.semantic_variation_profile,
        "slot_format_profile": args.slot_format_profile,
        "surface_noise_profile": args.surface_noise_profile,
        "scenario_context_summary": _scenario_context_summary(scenario_context),
        "llm_api_key_source": llm_api_key_source if args.mode == "llm" else None,
        "count": len(dialogs),
        "turn_range": [args.min_turns, args.max_turns],
        "dialogs": dialogs,
        "warnings": warnings,
    }

    payload = json.dumps(output, ensure_ascii=False, indent=2)
    if args.output == "-":
        print(payload)
    else:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(payload)


if __name__ == "__main__":
    main()
