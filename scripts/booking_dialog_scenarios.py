#!/usr/bin/env python3
"""Generate booking dialog scenarios with interruptions for salon domain."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
import urllib.request
from typing import Any

SERVICES = [
    "стрижку",
    "мужскую стрижку",
    "женскую стрижку",
    "окрашивание",
    "маникюр",
    "педикюр",
    "коррекцию бровей",
]

MASTERS = ["Алия", "Айжан", "Мария", "Диана", "Салтанат"]
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
REQUIRED_LLM_TURNS = {
    "booking": {"text": "{greet}, хочу записаться на {service}.", "tags": ["booking"]},
    "time": {"text": "Можно {time_exact}?", "tags": ["time"]},
    "name": {"text": "Меня зовут {name}.", "tags": ["name"]},
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
            {"text": "Любой мастер подойдет.", "tags": ["master"]},
            {"text": "Можно {time_exact}?", "tags": ["time"]},
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
            {"text": "Можно {time_exact}?", "tags": ["time"]},
            {"text": "{noise}", "tags": ["noise"]},
            {"text": "Кстати, сколько стоит {service}?", "tags": ["interrupt", "price"]},
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
            {"text": "Можно {time_exact}?", "tags": ["time"]},
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
            {"text": "Любой мастер подойдет.", "tags": ["master"]},
            {"text": "Можно {time_exact}?", "tags": ["time"]},
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
            {"text": "Можно {time_exact}?", "tags": ["time"]},
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
            {"text": "Давайте продолжим запись, можно {time_exact}?", "tags": ["booking", "time"]},
            {"text": "Имя {name}.", "tags": ["name"]},
            {"text": "Телефон {phone}.", "tags": ["phone"]},
            {"text": "Да, подтверждаю.", "tags": ["confirm"]},
        ],
        "requires_media": False,
    },
]


def _build_context(rng: random.Random) -> dict[str, str]:
    service = rng.choice(SERVICES)
    return {
        "greet": rng.choice(GREETINGS),
        "service": service,
        "day": rng.choice(DAYS),
        "time_range": rng.choice(TIME_RANGES),
        "time_exact": rng.choice(TIME_EXACT),
        "time_exact_alt": rng.choice(TIME_EXACT),
        "name": rng.choice(NAMES),
        "phone": rng.choice(PHONES),
        "master": rng.choice(MASTERS),
        "interrupt_price": f"Сколько стоит {service}?",
        "interrupt_location": rng.choice(
            ["Где вы находитесь?", "Как до вас добраться?", "Адрес подскажите?"]
        ),
        "noise": rng.choice([item["text"] for item in NOISE]),
    }

def _infer_context_from_dialog(dialog: dict[str, Any], rng: random.Random) -> dict[str, str]:
    ctx = _build_context(rng)
    combined = " ".join(
        [turn.get("text", "") for turn in (dialog.get("turns") or []) if isinstance(turn, dict)]
    ).lower()
    for service in SERVICES:
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
        "expect": _merge_expectations(tags, turn.get("expect")),
    }


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
        media_payload = {
            "messageType": "image",
            "mediaData": {
                "type": "image",
                "mimetype": "image/jpeg",
                "url": "https://app.chatflow.kz/static/demo/reference.jpg",
                "fileName": "reference.jpg",
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


def _default_expect() -> dict[str, Any]:
    return {
        "action": None,
        "info_sections": [],
        "reply_type": None,
        "state": None,
        "expected_reply": None,
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
) -> list[dict[str, Any]]:
    existing = {tag for turn in turns for tag in (turn.get("tags") or [])}
    missing = [tag for tag in REQUIRED_LLM_TAGS if tag not in existing]
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
    return _prune_turns(turns, max_turns, set(REQUIRED_LLM_TAGS))

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
    }


def _merge_expectations(tags: list[str], override: Any) -> dict[str, Any]:
    expect = _default_expect()
    for tag in tags:
        if tag in EXPECT_INFO_SECTIONS:
            expect["info_sections"].extend(EXPECT_INFO_SECTIONS[tag])
        if tag in EXPECT_ACTION_BY_TAG and expect["action"] is None:
            expect["action"] = EXPECT_ACTION_BY_TAG[tag][:]
        if tag in EXPECT_REPLY_TYPE_BY_TAG and expect["reply_type"] is None:
            expect["reply_type"] = EXPECT_REPLY_TYPE_BY_TAG[tag]
        if tag in EXPECT_STATE_BY_TAG and expect["state"] is None:
            expect["state"] = EXPECT_STATE_BY_TAG[tag]
    info_sections = []
    for item in expect["info_sections"]:
        if isinstance(item, str):
            value = item.strip().lower()
            if value and value not in info_sections:
                info_sections.append(value)
    expect["info_sections"] = info_sections
    if isinstance(override, dict):
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
) -> dict[str, Any]:
    ctx = _build_context(rng)
    turns = [_format_turn(t, ctx) for t in template["turns"]]
    extras = [_format_turn(t, ctx) for t in EXTRA_TURNS] + [_format_turn(t, ctx) for t in INTERRUPTIONS]
    extras += [_format_turn(t, ctx) for t in NOISE]

    if include_media or template.get("requires_media"):
        turns.insert(rng.randint(1, len(turns) - 1), _media_turn(ctx, mode=media_mode, kind=media_kind))

    target = rng.randint(min_turns, max_turns)
    _insert_extras(turns, extras, rng, target)

    return {
        "dialog_id": f"{template['id']}-{rng.randint(1000, 9999)}",
        "goal": template["goal"],
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
        for key in ("action", "info_sections", "reply_type", "state", "expected_reply"):
            if key not in expect:
                warnings.append("expect_missing_key")
                break
    return warnings


def _call_openai(prompt: str, *, api_key: str, model: str, base_url: str) -> str:
    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 1800,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        body = json.loads(resp.read().decode("utf-8"))
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


def _repair_llm_json(content: str, *, api_key: str, model: str, base_url: str) -> str | None:
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
        return _call_openai(prompt, api_key=api_key, model=model, base_url=base_url)
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
) -> list[dict[str, Any]]:
    prompt = (
        "Generate JSON with key 'dialogs' as a list. "
        "Each dialog: {dialog_id, goal, turns}. "
        "turns is a list of {kind,text,tags,expect} with 10-15 client messages. "
        "Tags must be chosen from: booking, interrupt, price, duration, location, hours, parking, "
        "promo, master, time, time_alt, consult, channel, delay, media, noise, handoff. "
        "expect must include keys: action, info_sections, reply_type, state, expected_reply. "
        "Use canonical tokens only in expect (no natural language): "
        "action: null or one of [booking_escalated, escalate, handoff]; "
        "info_sections: array from [pricing, price, payment_info, payment, address, location, "
        "hours, working_hours, schedule, discounts, discount, promo, promotion, duration, "
        "service_duration, parking, master, specialist]; "
        "reply_type: null or one of [service_choice, time, name]; "
        "state: null or one of [bot_active, pending, manager_active]; "
        "expected_reply: true/false/null. "
        "Include interruptions (price/location/noise), time/name swaps, and at least one media reference. "
        "Beauty salon domain, Russian language, natural chat. "
        f"Count={count}, turns_range={min_turns}-{max_turns}. "
        f"media_mode={media_mode}, media_kind={media_kind}. "
        f"coverage_tags={','.join(coverage) if coverage else 'none'}. "
        f"seed={seed}."
    )
    content = _call_openai(prompt, api_key=api_key, model=model, base_url=base_url)
    payload = _parse_llm_json(
        content,
        repair_fn=lambda raw: _repair_llm_json(
            raw, api_key=api_key, model=model, base_url=base_url
        ),
    )
    dialogs = payload.get("dialogs") or []
    if not isinstance(dialogs, list):
        return []
    for dialog in dialogs:
        turns = dialog.get("turns") or []
        for turn in turns:
            tags = list(turn.get("tags") or [])
            turn["expect"] = _merge_expectations(tags, turn.get("expect"))
        ctx = _infer_context_from_dialog(dialog, rng)
        turns = _ensure_required_tags(turns, ctx, max_turns=max_turns)
        dialog["turns"] = turns
        if include_media and all("media" not in (turn.get("tags") or []) for turn in dialog.get("turns", [])):
            dialog.setdefault("turns", []).insert(
                1, _media_turn(ctx, mode=media_mode, kind=media_kind)
            )
            dialog["turns"] = _prune_turns(dialog["turns"], max_turns, set(REQUIRED_LLM_TAGS))
    return dialogs


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate booking dialog scenarios.")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--min-turns", type=int, default=10)
    parser.add_argument("--max-turns", type=int, default=15)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output", default="-")
    parser.add_argument("--mode", choices=["template", "llm"], default="template")
    parser.add_argument("--include-media", action="store_true")
    parser.add_argument("--media-mode", choices=["text", "payload"], default="text")
    parser.add_argument("--media-kind", choices=["photo", "audio"], default="photo")
    parser.add_argument("--coverage", default="booking,info,interrupt")
    parser.add_argument("--llm-model", default="gpt-4o-mini")
    parser.add_argument("--llm-base-url", default=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com"))
    parser.add_argument("--llm-api-key", default=os.environ.get("OPENAI_API_KEY"))
    args = parser.parse_args()

    rng = random.Random(args.seed or int(time.time()))
    coverage = []
    if args.coverage:
        raw_coverage = [item.strip() for item in args.coverage.split(",") if item.strip()]
        if raw_coverage and raw_coverage != ["none"]:
            coverage = raw_coverage
    missing_coverage: list[str] = []
    dialogs: list[dict[str, Any]] = []
    if args.mode == "llm":
        if not args.llm_api_key:
            raise SystemExit("LLM mode requires OPENAI_API_KEY or --llm-api-key")
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
