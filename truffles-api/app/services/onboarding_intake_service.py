from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

from app.services.knowledge_validation import get_missing_required_fields, get_required_fields_for_domain
from app.services.pack_compiler_service import PackCompilerError, compile_pack_payload
from app.services.reference_pack_integrity import (
    REFERENCE_PACK_SCHEMA_VERSION,
    build_reference_pack_metadata,
    evaluate_reference_pack_integrity,
)

_TIME_RANGE_RE = re.compile(r"(?P<start>\d{1,2}:\d{2})\s*[-–]\s*(?P<end>\d{1,2}:\d{2})")
_PRICE_RE = re.compile(r"(?P<price>\d[\d\s]{1,10})\s*(?:₸|тенге|kzt|тг)?", re.IGNORECASE)
_DURATION_RE = re.compile(r"(?P<minutes>\d{1,3})\s*(?:мин|min|minutes?)", re.IGNORECASE)
_KEY_VALUE_SPLIT_RE = re.compile(r"\s*[:=]\s*")
_BULLET_PREFIX_RE = re.compile(r"^[\-\*\u2022]\s*")
_FENCED_BLOCK_RE = re.compile(r"```(?P<lang>[^\n`]*)\n(?P<body>.*?)```", re.DOTALL)
_INTAKE_TOP_LEVEL_HINTS = {
    "business",
    "salon",
    "location",
    "operations",
    "communication",
    "catalog",
    "services_catalog",
    "service_duration_estimates",
    "booking",
    "guest_policy",
    "safety",
    "pricing",
    "quality",
    "price_list",
    "policy",
}

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
    (("название", "салон", "name"), "client_pack.business.name"),
    (("business name", "company name", "название бизнеса", "компания"), "client_pack.business.name"),
    (("город", "city"), "client_pack.location.city"),
    (("location city", "город локации"), "client_pack.location.city"),
    (("адрес", "address"), "client_pack.location.address.full"),
    (("location address", "business address", "адрес локации"), "client_pack.location.address.full"),
    (("часы", "график", "hours"), "client_pack.operations.hours"),
    (("working hours", "operations hours", "режим работы"), "client_pack.operations.hours"),
    (("язык", "languages", "language"), "client_pack.communication.languages"),
    (("communication languages", "языки общения"), "client_pack.communication.languages"),
    (("услуги", "services summary"), "client_pack.catalog.summary"),
    (("offerings summary", "products summary", "кратко о продуктах"), "client_pack.catalog.summary"),
    (("каталог услуг", "services catalog"), "client_pack.services_catalog.services"),
    (("catalog", "service catalog", "products catalog"), "client_pack.services_catalog.services"),
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
    "client_pack.business.name": "Как называется бизнес/филиал для клиентов?",
    "client_pack.location.city": "В каком городе работает филиал?",
    "client_pack.location.address.full": "Какой полный адрес филиала?",
    "client_pack.operations.hours.days": "В какие дни работает филиал?",
    "client_pack.operations.hours.open": "Во сколько филиал открывается?",
    "client_pack.operations.hours.close": "Во сколько филиал закрывается?",
    "client_pack.catalog.summary": "Кратко перечислите основные услуги.",
    "client_pack.communication.languages": "Какие языки общения доступны? Обязательно ru и kk.",
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

_PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
_CRITICAL_FIELDS = {
    "client_pack.booking.collect_fields",
    "client_pack.booking.bot_can_confirm",
    "client_pack.policy.hard_law",
    "client_pack.policy.payment_info",
    "client_pack.policy.reschedule",
    "client_pack.policy.cancel",
    "client_pack.policy.medical",
    "client_pack.policy.legal",
    "client_pack.policy.complaint",
    "client_pack.policy.discounts",
    "client_pack.policy.guard_topics.refund",
}
_HIGH_FIELDS = {
    "client_pack.location.city",
    "client_pack.location.address.full",
    "client_pack.operations.hours.days",
    "client_pack.operations.hours.open",
    "client_pack.operations.hours.close",
    "client_pack.communication.languages",
    "client_pack.services_catalog.services",
    "client_pack.price_list",
    "client_pack.service_duration_estimates",
}
_MEDIUM_FIELDS = {
    "client_pack.business.name",
    "client_pack.catalog.summary",
    "client_pack.guest_policy",
    "client_pack.safety.medical_note",
    "client_pack.pricing.price_from_reason",
    "client_pack.quality.expectations_photo",
}
_CONFIRMED_ALIASES: dict[str, tuple[str, ...]] = {
    "client_pack.business.name": (
        "client_pack.salon.name",
    ),
    "client_pack.location.city": (
        "client_pack.salon.city",
    ),
    "client_pack.location.address.full": (
        "client_pack.salon.address.full",
    ),
    "client_pack.operations.hours.days": (
        "client_pack.salon.hours.days",
    ),
    "client_pack.operations.hours.open": (
        "client_pack.salon.hours.open",
    ),
    "client_pack.operations.hours.close": (
        "client_pack.salon.hours.close",
    ),
    "client_pack.catalog.summary": (
        "client_pack.salon.services_summary",
    ),
    "client_pack.communication.languages": (
        "client_pack.salon.communication.languages",
    ),
}


@dataclass(frozen=True)
class IntakeFieldState:
    field: str
    status: str
    priority: str


@dataclass(frozen=True)
class IntakeQuestionItem:
    field: str
    question: str
    priority: str
    blocking_go_live: bool


@dataclass(frozen=True)
class IntakeCompileSummary:
    status: str
    infra_valid: bool
    schema_version: str | None
    hash: str | None
    pack_index_hash: str | None
    signal_graph_present: bool
    policy_bundle_present: bool
    errors: list[str]


@dataclass(frozen=True)
class IntakeQualityDimension:
    id: str
    status: str
    required: bool
    details: list[str]


@dataclass(frozen=True)
class IntakeQualityMatrix:
    status: str
    infra_valid: bool
    semantic_valid: bool
    required_fields_count: int
    missing_fields_count: int
    critical_missing_fields_count: int
    integrity_missing_count: int
    missing_fields: list[str]
    critical_missing_fields: list[str]
    integrity_missing: list[str]
    dimensions: list[IntakeQualityDimension]
    regressions: list[str]
    comparison_blocked: bool
    comparison_block_reason: str | None


@dataclass(frozen=True)
class IntakePackQualitySummary:
    compile: IntakeCompileSummary
    quality_matrix: IntakeQualityMatrix


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


def _get_nested_value(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _field_priority(field: str) -> str:
    if field in _CRITICAL_FIELDS:
        return "critical"
    if field in _HIGH_FIELDS:
        return "high"
    if field in _MEDIUM_FIELDS:
        return "medium"
    return "low"


def _dedupe_strings(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value).strip()
        if not token:
            continue
        lowered = token.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(token)
    return normalized


def _is_field_confirmed_by_json(field: str, client_data_json: dict[str, Any] | None) -> bool:
    if not isinstance(client_data_json, dict):
        return False
    normalized = _normalize_payload(client_data_json)
    candidates = (field, *_CONFIRMED_ALIASES.get(field, ()))
    for path in candidates:
        if _is_present(_get_nested_value(normalized, path)):
            return True
    return False


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


def _copy_if_missing(payload: dict[str, Any], *, source_path: str, target_path: str) -> None:
    source_keys = source_path.split(".")
    target_keys = target_path.split(".")
    source_cursor: Any = payload
    target_cursor: Any = payload
    for key in source_keys:
        if not isinstance(source_cursor, dict) or key not in source_cursor:
            return
        source_cursor = source_cursor[key]
    for key in target_keys[:-1]:
        existing = target_cursor.get(key)
        if not isinstance(existing, dict):
            existing = {}
            target_cursor[key] = existing
        target_cursor = existing
    if target_keys[-1] not in target_cursor or not target_cursor[target_keys[-1]]:
        target_cursor[target_keys[-1]] = source_cursor


def _apply_salon_compatibility_aliases(payload: dict[str, Any]) -> None:
    # Compatibility bridge for legacy runtime paths until all packs are fully canonical.
    alias_pairs = (
        ("client_pack.business.name", "client_pack.salon.name"),
        ("client_pack.location.city", "client_pack.salon.city"),
        ("client_pack.location.address.full", "client_pack.salon.address.full"),
        ("client_pack.operations.hours", "client_pack.salon.hours"),
        ("client_pack.catalog.summary", "client_pack.salon.services_summary"),
        ("client_pack.communication.languages", "client_pack.salon.communication.languages"),
    )
    for source_path, target_path in alias_pairs:
        _copy_if_missing(payload, source_path=source_path, target_path=target_path)


def _apply_canonical_aliases(payload: dict[str, Any]) -> None:
    alias_pairs = (
        ("client_pack.salon.name", "client_pack.business.name"),
        ("client_pack.salon.city", "client_pack.location.city"),
        ("client_pack.salon.address.full", "client_pack.location.address.full"),
        ("client_pack.salon.hours", "client_pack.operations.hours"),
        ("client_pack.salon.services_summary", "client_pack.catalog.summary"),
        ("client_pack.salon.communication.languages", "client_pack.communication.languages"),
    )
    for source_path, target_path in alias_pairs:
        _copy_if_missing(payload, source_path=source_path, target_path=target_path)


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
        stripped_line = raw_line.strip()
        if not _BULLET_PREFIX_RE.match(stripped_line):
            continue
        line = _BULLET_PREFIX_RE.sub("", stripped_line).strip()
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
        # Heuristic guard: markdown docs may contain long pseudo-key lines in tables/examples.
        if len(key) > 80 or len(value) > 500:
            continue
        field = _match_alias(key)
        if not field:
            continue

        if field == "client_pack.operations.hours":
            hours_payload = _parse_hours_value(value)
            if hours_payload:
                _set_nested_value(payload, "client_pack.operations.hours", hours_payload)
            continue
        if field == "client_pack.communication.languages":
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


def _markdown_to_intake_text(text: str) -> str:
    if not text:
        return ""
    in_fence = False
    lines: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith("#") or stripped.startswith(">"):
            continue
        if stripped.startswith("|"):
            continue
        lines.append(raw_line)
    return "\n".join(lines).strip()


def _extract_yaml_payload(text: str) -> dict[str, Any] | None:
    def _looks_like_intake_payload(parsed: dict[str, Any]) -> bool:
        if isinstance(parsed.get("client_pack"), dict):
            return True
        return any(key in parsed for key in _INTAKE_TOP_LEVEL_HINTS)

    candidates = [text]
    for match in _FENCED_BLOCK_RE.finditer(text):
        lang = (match.group("lang") or "").strip().casefold()
        if lang and lang not in {"yaml", "yml", "json"}:
            continue
        body = (match.group("body") or "").strip()
        if body:
            candidates.append(body)
    for candidate in candidates:
        try:
            parsed = yaml.safe_load(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict) and _looks_like_intake_payload(parsed):
            return _normalize_payload(parsed)
    return None


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
        _apply_canonical_aliases(payload)
        _apply_salon_compatibility_aliases(payload)
        return payload

    cleaned_text = _markdown_to_intake_text(normalized_text)
    yaml_payload = _extract_yaml_payload(normalized_text)
    if yaml_payload:
        payload = _deep_merge(payload, yaml_payload)
    else:
        kv_payload = _parse_key_value_text(cleaned_text)
        payload = _deep_merge(payload, kv_payload)

    detected_languages = _detect_languages(cleaned_text)
    if detected_languages:
        existing_languages = (
            payload.get("client_pack", {})
            .get("communication", {})
            .get("languages")
        )
        if not isinstance(existing_languages, list) or not existing_languages:
            _set_nested_value(payload, "client_pack.communication.languages", detected_languages)

    parsed_services = _parse_services_from_text(cleaned_text)
    for service in parsed_services:
        _append_service(payload, service)

    if not payload.get("client_pack", {}).get("catalog", {}).get("summary") and parsed_services:
        _set_nested_value(
            payload,
            "client_pack.catalog.summary",
            ", ".join(service.get("name", "") for service in parsed_services if service.get("name"))[:500],
        )

    _apply_canonical_aliases(payload)
    _apply_salon_compatibility_aliases(payload)

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


def evaluate_intake_payload(
    payload: dict[str, Any],
    *,
    domain_slug: str | None = None,
    require_booking: bool | None = None,
) -> tuple[list[str], list[str]]:
    missing = get_missing_required_fields(
        payload,
        domain_slug=domain_slug,
        require_booking=require_booking,
    )
    questions = build_missing_questions(missing)
    return missing, questions


def build_intake_field_states(
    payload: dict[str, Any],
    *,
    domain_slug: str | None = None,
    require_booking: bool | None = None,
    missing_fields: list[str] | None = None,
    client_data_json: dict[str, Any] | None = None,
) -> list[IntakeFieldState]:
    required_fields = get_required_fields_for_domain(
        domain_slug=domain_slug,
        require_booking=require_booking,
    )
    missing = (
        list(missing_fields)
        if missing_fields is not None
        else get_missing_required_fields(
            payload,
            domain_slug=domain_slug,
            require_booking=require_booking,
        )
    )
    missing_set = set(missing)
    states: list[IntakeFieldState] = []
    for field in required_fields:
        priority = _field_priority(field)
        if field in missing_set:
            states.append(IntakeFieldState(field=field, status="unknown", priority=priority))
            continue
        status = "confirmed" if _is_field_confirmed_by_json(field, client_data_json) else "assumed"
        states.append(IntakeFieldState(field=field, status=status, priority=priority))
    return states


def build_intake_question_queue(
    missing_fields: list[str],
) -> list[IntakeQuestionItem]:
    queue: list[IntakeQuestionItem] = []
    for field in missing_fields:
        priority = _field_priority(field)
        queue.append(
            IntakeQuestionItem(
                field=field,
                question=_MISSING_QUESTIONS.get(field, f"Уточните значение поля: {field}"),
                priority=priority,
                blocking_go_live=priority == "critical",
            )
        )
    return sorted(
        queue,
        key=lambda item: (_PRIORITY_ORDER.get(item.priority, 99), item.field),
    )


def build_intake_critical_missing_fields(missing_fields: list[str]) -> list[str]:
    return [field for field in missing_fields if _field_priority(field) == "critical"]


def build_intake_compile_summary(payload: dict[str, Any]) -> IntakeCompileSummary:
    try:
        compiled = compile_pack_payload(payload)
    except PackCompilerError as exc:
        errors = list(exc.errors) if exc.errors else [str(exc)]
        return IntakeCompileSummary(
            status="fail",
            infra_valid=True,
            schema_version=None,
            hash=None,
            pack_index_hash=None,
            signal_graph_present=False,
            policy_bundle_present=False,
            errors=_dedupe_strings(errors),
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        return IntakeCompileSummary(
            status="fail",
            infra_valid=False,
            schema_version=None,
            hash=None,
            pack_index_hash=None,
            signal_graph_present=False,
            policy_bundle_present=False,
            errors=[f"compile_exception:{exc.__class__.__name__}"],
        )

    signal_graph = compiled.get("signal_graph")
    policy_bundle = compiled.get("policy_bundle")
    pack_index = compiled.get("pack_index")
    pack_index_hash = pack_index.get("hash") if isinstance(pack_index, dict) else None
    return IntakeCompileSummary(
        status="pass",
        infra_valid=True,
        schema_version=compiled.get("schema_version"),
        hash=compiled.get("hash"),
        pack_index_hash=pack_index_hash if isinstance(pack_index_hash, str) else None,
        signal_graph_present=isinstance(signal_graph, dict),
        policy_bundle_present=isinstance(policy_bundle, dict),
        errors=[],
    )


def _build_quality_dimension(
    dimension_id: str,
    *,
    passed: bool,
    details: list[str] | None = None,
    required: bool = True,
) -> IntakeQualityDimension:
    return IntakeQualityDimension(
        id=dimension_id,
        status="pass" if passed else "fail",
        required=required,
        details=_dedupe_strings(list(details or [])),
    )


def _normalize_domain_slug(domain_slug: str | None) -> str | None:
    if not isinstance(domain_slug, str):
        return None
    normalized = domain_slug.strip().lower()
    return normalized or None


def _collect_integrity_missing(domain_slug: str | None) -> list[str]:
    normalized_domain = _normalize_domain_slug(domain_slug)
    if not normalized_domain:
        return ["reference_pack_domain"]
    metadata = build_reference_pack_metadata(domain_slug=normalized_domain)
    return evaluate_reference_pack_integrity(
        domain_slug=normalized_domain,
        schema_version=REFERENCE_PACK_SCHEMA_VERSION,
        metadata=metadata,
    )


def _dimension_status_map(
    dimensions: list[IntakeQualityDimension],
) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in dimensions:
        if not item.id:
            continue
        result[item.id] = item.status
    return result


def _compare_quality_baseline(
    *,
    compile_summary: IntakeCompileSummary,
    quality_matrix: IntakeQualityMatrix,
    baseline_summary: dict[str, Any] | None,
) -> tuple[list[str], bool, str | None]:
    if baseline_summary is None:
        return [], False, None
    if not isinstance(baseline_summary, dict):
        return [], True, "baseline_not_object"

    baseline_quality = baseline_summary.get("quality_matrix")
    baseline_compile = baseline_summary.get("compile")
    if not isinstance(baseline_quality, dict):
        return [], True, "baseline_quality_matrix_missing"
    if not isinstance(baseline_compile, dict):
        return [], True, "baseline_compile_missing"

    regressions: list[str] = []
    if baseline_quality.get("status") == "pass" and quality_matrix.status != "pass":
        regressions.append("status")
    if baseline_quality.get("infra_valid") is True and not quality_matrix.infra_valid:
        regressions.append("infra_valid")
    if baseline_quality.get("semantic_valid") is True and not quality_matrix.semantic_valid:
        regressions.append("semantic_valid")

    baseline_missing = baseline_quality.get("missing_fields_count")
    if isinstance(baseline_missing, int) and quality_matrix.missing_fields_count > baseline_missing:
        regressions.append("missing_fields_count")
    baseline_critical = baseline_quality.get("critical_missing_fields_count")
    if isinstance(baseline_critical, int) and quality_matrix.critical_missing_fields_count > baseline_critical:
        regressions.append("critical_missing_fields_count")

    current_dimensions = _dimension_status_map(quality_matrix.dimensions)
    baseline_dimensions = baseline_quality.get("dimensions")
    if isinstance(baseline_dimensions, list):
        for row in baseline_dimensions:
            if not isinstance(row, dict):
                continue
            dimension_id = row.get("id")
            baseline_status = row.get("status")
            if not isinstance(dimension_id, str) or not isinstance(baseline_status, str):
                continue
            if baseline_status == "pass" and current_dimensions.get(dimension_id) != "pass":
                regressions.append(f"dimension:{dimension_id}")

    if baseline_compile.get("status") == "pass" and compile_summary.status != "pass":
        regressions.append("compile.status")
    if baseline_compile.get("policy_bundle_present") is True and not compile_summary.policy_bundle_present:
        regressions.append("compile.policy_bundle_present")
    if baseline_compile.get("signal_graph_present") is True and not compile_summary.signal_graph_present:
        regressions.append("compile.signal_graph_present")

    return _dedupe_strings(regressions), False, None


def build_intake_pack_quality_summary(
    payload: dict[str, Any],
    *,
    domain_slug: str | None = None,
    require_booking: bool | None = None,
    baseline_summary: dict[str, Any] | None = None,
) -> IntakePackQualitySummary:
    required_fields = get_required_fields_for_domain(
        domain_slug=domain_slug,
        require_booking=require_booking,
    )
    missing_fields = get_missing_required_fields(
        payload,
        domain_slug=domain_slug,
        require_booking=require_booking,
    )
    critical_missing = build_intake_critical_missing_fields(missing_fields)
    integrity_missing = _collect_integrity_missing(domain_slug)
    compile_summary = build_intake_compile_summary(payload)

    dimensions: list[IntakeQualityDimension] = [
        _build_quality_dimension(
            "intake_required_fields",
            passed=len(missing_fields) == 0,
            details=missing_fields[:20],
        ),
        _build_quality_dimension(
            "intake_critical_fields",
            passed=len(critical_missing) == 0,
            details=critical_missing[:20],
        ),
        _build_quality_dimension(
            "reference_pack_integrity",
            passed=len(integrity_missing) == 0,
            details=integrity_missing[:20],
        ),
        _build_quality_dimension(
            "pack_compile",
            passed=compile_summary.status == "pass",
            details=compile_summary.errors[:20],
        ),
        _build_quality_dimension(
            "policy_bundle_present",
            passed=compile_summary.status == "pass" and compile_summary.policy_bundle_present,
            details=(["policy_bundle_missing"] if compile_summary.status == "pass" and not compile_summary.policy_bundle_present else []),
        ),
        _build_quality_dimension(
            "signal_graph_present",
            passed=compile_summary.status == "pass" and compile_summary.signal_graph_present,
            details=(["signal_graph_missing"] if compile_summary.status == "pass" and not compile_summary.signal_graph_present else []),
        ),
    ]

    semantic_valid = all(item.status == "pass" for item in dimensions if item.required)
    quality_matrix = IntakeQualityMatrix(
        status="pass" if compile_summary.infra_valid and semantic_valid else "fail",
        infra_valid=compile_summary.infra_valid,
        semantic_valid=semantic_valid,
        required_fields_count=len(required_fields),
        missing_fields_count=len(missing_fields),
        critical_missing_fields_count=len(critical_missing),
        integrity_missing_count=len(integrity_missing),
        missing_fields=_dedupe_strings(list(missing_fields)),
        critical_missing_fields=_dedupe_strings(list(critical_missing)),
        integrity_missing=_dedupe_strings(list(integrity_missing)),
        dimensions=dimensions,
        regressions=[],
        comparison_blocked=False,
        comparison_block_reason=None,
    )

    regressions, comparison_blocked, comparison_block_reason = _compare_quality_baseline(
        compile_summary=compile_summary,
        quality_matrix=quality_matrix,
        baseline_summary=baseline_summary,
    )
    quality_matrix = IntakeQualityMatrix(
        status=quality_matrix.status,
        infra_valid=quality_matrix.infra_valid,
        semantic_valid=quality_matrix.semantic_valid,
        required_fields_count=quality_matrix.required_fields_count,
        missing_fields_count=quality_matrix.missing_fields_count,
        critical_missing_fields_count=quality_matrix.critical_missing_fields_count,
        integrity_missing_count=quality_matrix.integrity_missing_count,
        missing_fields=quality_matrix.missing_fields,
        critical_missing_fields=quality_matrix.critical_missing_fields,
        integrity_missing=quality_matrix.integrity_missing,
        dimensions=quality_matrix.dimensions,
        regressions=regressions,
        comparison_blocked=comparison_blocked,
        comparison_block_reason=comparison_block_reason,
    )
    return IntakePackQualitySummary(
        compile=compile_summary,
        quality_matrix=quality_matrix,
    )
