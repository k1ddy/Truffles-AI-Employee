from __future__ import annotations

import re
from typing import Any

import yaml

from app.services.knowledge_validation import get_missing_required_fields

_TIME_RANGE_RE = re.compile(r"(?P<start>\d{1,2}:\d{2})\s*[-–]\s*(?P<end>\d{1,2}:\d{2})")
_PRICE_RE = re.compile(r"(?P<price>\d[\d\s]{1,10})\s*(?:₸|тенге|kzt|тг)?", re.IGNORECASE)
_DURATION_RE = re.compile(r"(?P<minutes>\d{1,3})\s*(?:мин|min|minutes?)", re.IGNORECASE)
_KEY_VALUE_SPLIT_RE = re.compile(r"\s*[:=]\s*")
_BULLET_PREFIX_RE = re.compile(r"^[\-\*\u2022]\s*")

_DAY_ALIASES: dict[str, tuple[str, ...]] = {
    "mon": ("mon", "monday", "пн", "понедельник"),
    "tue": ("tue", "tuesday", "вт", "вторник"),
    "wed": ("wed", "wednesday", "ср", "среда"),
    "thu": ("thu", "thursday", "чт", "четверг"),
    "fri": ("fri", "friday", "пт", "пятница"),
    "sat": ("sat", "saturday", "сб", "суббота"),
    "sun": ("sun", "sunday", "вс", "воскресенье"),
}

_LANGUAGE_TOKENS: dict[str, tuple[str, ...]] = {
    "ru": ("ru", "рус", "russian", "русский"),
    "kk": ("kk", "kz", "каз", "kazakh", "қаз", "казахский"),
}

_FIELD_ALIASES: list[tuple[tuple[str, ...], str]] = [
    (("название", "салон", "name"), "client_pack.salon.name"),
    (("город", "city"), "client_pack.salon.city"),
    (("адрес", "address"), "client_pack.salon.address.full"),
    (("часы", "график", "hours"), "client_pack.salon.hours"),
    (("язык", "languages", "language"), "client_pack.salon.communication.languages"),
    (("услуги", "services summary"), "client_pack.salon.services_summary"),
    (("каталог услуг", "services catalog"), "client_pack.services_catalog.services"),
    (("длительность", "duration"), "client_pack.service_duration_estimates"),
    (("booking fields", "collect fields", "поля записи"), "client_pack.booking.collect_fields"),
    (("bot can confirm", "confirm booking", "подтверждение"), "client_pack.booking.bot_can_confirm"),
    (("guest policy", "политика гостей"), "client_pack.guest_policy"),
    (("medical note", "медицин"), "client_pack.safety.medical_note"),
    (("price from", "цена от"), "client_pack.pricing.price_from_reason"),
    (("expectations", "ожидания"), "client_pack.quality.expectations_photo"),
    (("price list", "прайс"), "client_pack.price_list"),
    (("hard law", "hard_law"), "client_pack.policy.hard_law"),
    (("payment policy", "payment_info", "оплата"), "client_pack.policy.payment_info"),
    (("reschedule", "перенос"), "client_pack.policy.reschedule"),
    (("cancel", "отмена"), "client_pack.policy.cancel"),
    (("medical policy", "medical policy"), "client_pack.policy.medical"),
    (("legal", "юрид"), "client_pack.policy.legal"),
    (("complaint", "жалоб"), "client_pack.policy.complaint"),
    (("discount", "скидк"), "client_pack.policy.discounts"),
    (("refund", "возврат"), "client_pack.policy.guard_topics.refund"),
]

_MISSING_QUESTIONS: dict[str, str] = {
    "client_pack.salon.name": "Как называется бизнес/филиал для клиентов?",
    "client_pack.salon.city": "В каком городе работает филиал?",
    "client_pack.salon.address.full": "Какой полный адрес филиала?",
    "client_pack.salon.hours.days": "В какие дни работает филиал?",
    "client_pack.salon.hours.open": "Во сколько филиал открывается?",
    "client_pack.salon.hours.close": "Во сколько филиал закрывается?",
    "client_pack.salon.services_summary": "Кратко перечислите основные услуги.",
    "client_pack.salon.communication.languages": "Какие языки общения доступны? Обязательно ru и kk.",
    "client_pack.services_catalog.services": "Дайте список услуг с названиями и ценами.",
    "client_pack.service_duration_estimates": "Укажите длительности услуг.",
    "client_pack.booking.collect_fields": "Какие поля бот обязан собирать для записи?",
    "client_pack.booking.bot_can_confirm": "Бот может подтверждать запись автоматически?",
    "client_pack.guest_policy": "Есть ли ограничения/правила для гостей?",
    "client_pack.safety.medical_note": "Какой медицинский дисклеймер должен говорить бот?",
    "client_pack.pricing.price_from_reason": "Как бот объясняет, почему цена может быть \"от\"?",
    "client_pack.quality.expectations_photo": "Как бот предупреждает про ожидания/референс-фото?",
    "client_pack.price_list": "Нужен прайс-лист в структурированном виде.",
    "client_pack.policy.hard_law": "Укажите обязательные юридические ограничения (hard_law).",
    "client_pack.policy.payment_info": "Опишите правила оплаты.",
    "client_pack.policy.reschedule": "Опишите правила переноса записи.",
    "client_pack.policy.cancel": "Опишите правила отмены записи.",
    "client_pack.policy.medical": "Опишите медицинскую политику.",
    "client_pack.policy.legal": "Опишите юридическую политику.",
    "client_pack.policy.complaint": "Опишите процесс обработки жалоб.",
    "client_pack.policy.discounts": "Опишите политику скидок.",
    "client_pack.policy.guard_topics.refund": "Добавьте ключевые слова/правила по возврату.",
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        current = result.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            result[key] = _deep_merge(current, value)
        else:
            result[key] = value
    return result


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("client_pack"), dict):
        return payload
    return {"client_pack": payload}


def _set_nested_value(payload: dict[str, Any], path: str, value: Any) -> None:
    keys = path.split(".")
    cursor: dict[str, Any] = payload
    for key in keys[:-1]:
        existing = cursor.get(key)
        if not isinstance(existing, dict):
            existing = {}
            cursor[key] = existing
        cursor = existing
    cursor[keys[-1]] = value


def _append_service(payload: dict[str, Any], service: dict[str, Any]) -> None:
    if not service.get("name"):
        return
    services = payload.setdefault("client_pack", {}).setdefault("services_catalog", {}).setdefault("services", [])
    if not isinstance(services, list):
        services = []
        payload["client_pack"]["services_catalog"]["services"] = services
    services.append(service)

    price_list = payload.setdefault("client_pack", {}).setdefault("price_list", [])
    if not isinstance(price_list, list):
        price_list = []
        payload["client_pack"]["price_list"] = price_list
    price_item = {"name": service["name"]}
    if service.get("price") is not None:
        price_item["price"] = service["price"]
    price_list.append(price_item)


def _detect_languages(value: str) -> list[str]:
    lowered = value.casefold()
    detected: list[str] = []
    for code, aliases in _LANGUAGE_TOKENS.items():
        if any(alias in lowered for alias in aliases):
            detected.append(code)
    return sorted(set(detected))


def _detect_days(value: str) -> list[str]:
    lowered = value.casefold()
    detected: list[str] = []
    for code, aliases in _DAY_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            detected.append(code)
    return detected


def _parse_hours_value(value: str) -> dict[str, Any] | None:
    match = _TIME_RANGE_RE.search(value)
    if not match:
        return None
    days = _detect_days(value)
    if not days:
        days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    return {
        "days": days,
        "open": match.group("start"),
        "close": match.group("end"),
    }


def _parse_services_from_text(text: str) -> list[dict[str, Any]]:
    services: list[dict[str, Any]] = []
    for raw_line in text.splitlines():
        line = _BULLET_PREFIX_RE.sub("", raw_line).strip()
        if not line:
            continue
        if _KEY_VALUE_SPLIT_RE.search(line):
            continue
        duration_match = _DURATION_RE.search(line)
        price_match = _PRICE_RE.search(line)
        name = line
        if price_match:
            name = name[: price_match.start()].strip(" ,-;")
        if duration_match:
            name = name[: duration_match.start()].strip(" ,-;")
        if not name:
            continue
        service: dict[str, Any] = {"name": name}
        if price_match:
            normalized = re.sub(r"\s+", "", price_match.group("price"))
            try:
                service["price"] = int(normalized)
            except ValueError:
                pass
        if duration_match:
            service["duration_minutes"] = int(duration_match.group("minutes"))
        if len(service) > 1:
            services.append(service)
    return services


def _match_alias(key: str) -> str | None:
    lowered = key.casefold()
    for aliases, field in _FIELD_ALIASES:
        if any(alias in lowered for alias in aliases):
            return field
    return None


def _parse_key_value_text(text: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"client_pack": {}}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("-"):
            continue
        chunks = _KEY_VALUE_SPLIT_RE.split(line, maxsplit=1)
        if len(chunks) != 2:
            continue
        key, value = chunks[0].strip(), chunks[1].strip()
        if not key or not value:
            continue
        field = _match_alias(key)
        if not field:
            continue

        if field == "client_pack.salon.hours":
            hours_payload = _parse_hours_value(value)
            if hours_payload:
                _set_nested_value(payload, "client_pack.salon.hours", hours_payload)
            continue
        if field == "client_pack.salon.communication.languages":
            languages = _detect_languages(value)
            if languages:
                _set_nested_value(payload, field, languages)
            continue
        if field == "client_pack.policy.guard_topics.refund":
            terms = [item.strip() for item in re.split(r"[,;/]", value) if item.strip()]
            _set_nested_value(payload, field, terms)
            continue
        if field in ("client_pack.booking.bot_can_confirm",):
            lowered = value.casefold()
            bool_value = lowered in ("true", "1", "yes", "да")
            _set_nested_value(payload, field, bool_value)
            continue
        _set_nested_value(payload, field, value)
    return payload


def _extract_yaml_payload(text: str) -> dict[str, Any] | None:
    try:
        parsed = yaml.safe_load(text)
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None
    return _normalize_payload(parsed)


def build_intake_payload(
    *,
    client_data_json: dict[str, Any] | None,
    client_data_text: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"client_pack": {}}

    if isinstance(client_data_json, dict):
        payload = _deep_merge(payload, _normalize_payload(client_data_json))

    normalized_text = (client_data_text or "").strip()
    if not normalized_text:
        return payload

    yaml_payload = _extract_yaml_payload(normalized_text)
    if yaml_payload:
        payload = _deep_merge(payload, yaml_payload)
    else:
        kv_payload = _parse_key_value_text(normalized_text)
        payload = _deep_merge(payload, kv_payload)

    detected_languages = _detect_languages(normalized_text)
    if detected_languages:
        existing_languages = (
            payload.get("client_pack", {})
            .get("salon", {})
            .get("communication", {})
            .get("languages")
        )
        if not isinstance(existing_languages, list) or not existing_languages:
            _set_nested_value(payload, "client_pack.salon.communication.languages", detected_languages)

    parsed_services = _parse_services_from_text(normalized_text)
    for service in parsed_services:
        _append_service(payload, service)

    if not payload.get("client_pack", {}).get("salon", {}).get("services_summary") and parsed_services:
        _set_nested_value(
            payload,
            "client_pack.salon.services_summary",
            ", ".join(service.get("name", "") for service in parsed_services if service.get("name"))[:500],
        )

    return payload


def build_missing_questions(missing_fields: list[str]) -> list[str]:
    questions: list[str] = []
    seen: set[str] = set()
    for field in missing_fields:
        question = _MISSING_QUESTIONS.get(field)
        if not question:
            question = f"Уточните значение поля: {field}"
        if question in seen:
            continue
        seen.add(question)
        questions.append(question)
    return questions


def evaluate_intake_payload(payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    missing = get_missing_required_fields(payload)
    questions = build_missing_questions(missing)
    return missing, questions
