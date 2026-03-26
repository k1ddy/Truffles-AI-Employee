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

from app.services.llm_quality_contracts import (
    BookingScenarioPostCoverageRepairCallbacks,
    merge_booking_scenario_expectations,
    repair_booking_scenario_post_coverage_dialogs,
    sanitize_booking_scenario_llm_turns as _sanitize_llm_turns,
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
_BOOKING_SCENARIO_SERVICE_CANDIDATES = tuple(SERVICES)

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
        "action: null or one of [booking_prompt, booking_escalated, escalate, handoff];",
        "info_sections: array from [pricing, price, payment_info, payment, address, location,",
        "hours, working_hours, schedule, discounts, discount, promo, promotion, duration,",
        "service_duration, parking, master, specialist];",
        "reply_type: null or one of [service_choice, time, name];",
        "state: null or one of [bot_active, pending, manager_active];",
        "expected_reply: true/false/null.",
        "meta/meta_any/meta_contains keys must use canonical runtime fields already emitted in decision_meta for collect/question-contract turns (for example action, source, tool_action).",
        "trace_contains is a list of exact stage/decision evidence objects.",
        "For service-missing booking collect turns (`reply_type=service_choice` on `booking` tags), require explicit booking collect evidence via `action=booking_prompt` plus structured `meta`/`trace_contains`.",
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
        "id": "booking_weekend_service_followup",
        "goal": "book after weekend hours interrupt while service is still missing",
        "coverage": ["booking", "info", "interrupt"],
        "turns": [
            {
                "text": "{greet}! Хочу записаться.",
                "tags": ["booking"],
                "expect": {"reply_type": "service_choice", "expected_reply": True},
            },
            {"text": "А по выходным вы работаете?", "tags": ["interrupt", "hours"]},
            {
                "text": "Можно записаться на выходные?",
                "tags": ["booking"],
                "expect": {"reply_type": "service_choice", "state": "bot_active", "expected_reply": True},
            },
            {"text": "На {service}.", "tags": ["booking"]},
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
    format_ctx = _build_context(random.Random(0))
    format_ctx.update(
        {
            key: value
            for key, value in (ctx or {}).items()
            if isinstance(key, str) and isinstance(value, str) and value
        }
    )
    text = str(turn.get("text") or "").format_map(format_ctx)
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


_BOOKING_SCENARIO_POST_COVERAGE_REPAIR_CALLBACKS = (
    BookingScenarioPostCoverageRepairCallbacks(
        service_candidates=_BOOKING_SCENARIO_SERVICE_CANDIDATES,
    )
)


def _repair_post_coverage_orphan_pending_question_turns(
    dialogs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return repair_booking_scenario_post_coverage_dialogs(
        dialogs,
        callbacks=_BOOKING_SCENARIO_POST_COVERAGE_REPAIR_CALLBACKS,
    )


def _merge_expectations(tags: list[str], override: Any, text: str | None = None) -> dict[str, Any]:
    return merge_booking_scenario_expectations(tags, override, text=text)


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
        selected: list[dict[str, Any]] = []
        remaining = SCENARIOS[:]
        while len(selected) < count:
            if not remaining:
                remaining = SCENARIOS[:]
            choice = rng.choice(remaining)
            selected.append(choice)
            remaining.remove(choice)
        return selected, []
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
        pool = remaining or SCENARIOS[:]
        choice = rng.choice(pool)
        selected.append(choice)
        if choice in remaining:
            remaining.remove(choice)
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
    }
    token_limit = max(256, int(max_tokens))
    if str(model or "").strip().lower().startswith("gpt-5"):
        payload["max_completion_tokens"] = token_limit
    else:
        payload["max_tokens"] = token_limit
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
    parser.add_argument("--llm-model", default="gpt-5.4-nano-2026-03-17")
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
