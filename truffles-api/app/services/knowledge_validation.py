from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import yaml

_COMMON_REQUIRED_FIELDS = [
    "client_pack.business.name",
    "client_pack.location.city",
    "client_pack.location.address.full",
    "client_pack.operations.hours.days",
    "client_pack.operations.hours.open",
    "client_pack.operations.hours.close",
    "client_pack.catalog.summary",
    "client_pack.communication.languages",
    "client_pack.services_catalog.services",
    "client_pack.price_list",
]

_BEAUTY_REQUIRED_FIELDS = (
    "client_pack.guest_policy",
    "client_pack.safety.medical_note",
    "client_pack.pricing.price_from_reason",
    "client_pack.quality.expectations_photo",
)

_BOOKING_REQUIRED_FIELDS = [
    "client_pack.service_duration_estimates",
    "client_pack.booking.collect_fields",
    "client_pack.booking.bot_can_confirm",
]

REQUIRED_CLIENT_PACK_FIELDS = (
    _COMMON_REQUIRED_FIELDS
    + list(_BEAUTY_REQUIRED_FIELDS)
    + _BOOKING_REQUIRED_FIELDS
)

REQUIRED_POLICY_FIELDS = [
    "client_pack.policy.hard_law",
    "client_pack.policy.payment_info",
    "client_pack.policy.reschedule",
    "client_pack.policy.cancel",
    "client_pack.policy.medical",
    "client_pack.policy.legal",
    "client_pack.policy.complaint",
    "client_pack.policy.discounts",
    "client_pack.policy.guard_topics.refund",
]

REQUIRED_PACK_FIELDS = REQUIRED_CLIENT_PACK_FIELDS + REQUIRED_POLICY_FIELDS
MINIMUM_DATA_CONTRACT_VERSION = "minimum_data_contract.v2"
MINIMUM_DATA_REQUIRED_LANGUAGES = ("ru", "kk")
MINIMUM_DATA_REQUIRED_FIELDS = REQUIRED_PACK_FIELDS
LOSSY_STRUCTURED_REWRITE_ERROR_PREFIX = "Lossy structured field rewrite blocked: "
_MINIMUM_DATA_DURATION_KEYS = (
    "duration_text",
    "duration",
    "duration_minutes",
    "duration_min",
    "duration_max",
    "duration_hours",
)

_MISSING = object()
_COMPILED_ARTIFACTS_KEY = "compiled_artifacts"
_LANGUAGE_ALIASES = {"kz": "kk"}
_DOMAIN_DEFAULT_BOOKING_REQUIRED = {
    "beauty": True,
    "clinic": True,
    "generic": True,
    "legal": False,
    "ecom": False,
}
_DOMAIN_EXTRA_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "beauty": _BEAUTY_REQUIRED_FIELDS,
    "clinic": _BEAUTY_REQUIRED_FIELDS,
    "generic": (),
    "legal": (),
    "ecom": (),
}
_DEFAULT_DOMAIN_EXTRA_REQUIRED_FIELDS = _BEAUTY_REQUIRED_FIELDS

# Backward-compatible aliases: v2 canonical paths stay stable in validation output,
# while legacy salon data still satisfies requirements.
_FIELD_VALIDATION_ALIASES: dict[str, tuple[str, ...]] = {
    "client_pack.business.name": (
        "client_pack.salon.name",
        "client_pack.organization.name",
    ),
    "client_pack.location.city": (
        "client_pack.salon.city",
    ),
    "client_pack.location.address.full": (
        "client_pack.salon.address.full",
        "client_pack.location.address_full",
    ),
    "client_pack.operations.hours.days": (
        "client_pack.salon.hours.days",
        "client_pack.hours.days",
    ),
    "client_pack.operations.hours.open": (
        "client_pack.salon.hours.open",
        "client_pack.hours.open",
    ),
    "client_pack.operations.hours.close": (
        "client_pack.salon.hours.close",
        "client_pack.hours.close",
    ),
    "client_pack.catalog.summary": (
        "client_pack.salon.services_summary",
        "client_pack.services.summary",
        "client_pack.offerings.summary",
    ),
    "client_pack.communication.languages": (
        "client_pack.salon.communication.languages",
        "client_pack.languages",
    ),
}

_STRUCTURED_REWRITE_GUARDED_PATHS: tuple[str, ...] = (
    "client_pack.guest_policy",
    "client_pack.policy.hard_law",
    "client_pack.policy.payment_info",
    "client_pack.policy.reschedule",
    "client_pack.policy.cancel",
    "client_pack.policy.medical",
    "client_pack.policy.legal",
    "client_pack.policy.complaint",
    "client_pack.policy.discounts",
    "client_pack.policy.guard_topics",
)


def _normalize_domain_slug(domain_slug: str | None) -> str | None:
    if not isinstance(domain_slug, str):
        return None
    cleaned = domain_slug.strip().lower()
    return cleaned or None


def _validation_path_candidates(path: str) -> tuple[str, ...]:
    aliases = _FIELD_VALIDATION_ALIASES.get(path, ())
    if not aliases:
        return (path,)
    # Keep deterministic order and always check canonical v2 path first.
    return (path, *aliases)


def _booking_required_for_domain(
    *,
    domain_slug: str | None,
    require_booking: bool | None,
) -> bool:
    if require_booking is not None:
        return bool(require_booking)
    normalized_domain = _normalize_domain_slug(domain_slug)
    if not normalized_domain:
        return True
    return _DOMAIN_DEFAULT_BOOKING_REQUIRED.get(normalized_domain, True)


def _extra_required_fields_for_domain(domain_slug: str | None) -> tuple[str, ...]:
    normalized_domain = _normalize_domain_slug(domain_slug)
    if not normalized_domain:
        return _DEFAULT_DOMAIN_EXTRA_REQUIRED_FIELDS
    return _DOMAIN_EXTRA_REQUIRED_FIELDS.get(
        normalized_domain,
        _DEFAULT_DOMAIN_EXTRA_REQUIRED_FIELDS,
    )


def get_required_fields_for_domain(
    *,
    domain_slug: str | None = None,
    require_booking: bool | None = None,
) -> list[str]:
    required_fields: list[str] = list(_COMMON_REQUIRED_FIELDS)
    normalized_domain = _normalize_domain_slug(domain_slug)
    for field in _extra_required_fields_for_domain(normalized_domain):
        if field not in required_fields:
            required_fields.append(field)
    if _booking_required_for_domain(
        domain_slug=normalized_domain,
        require_booking=require_booking,
    ):
        for field in _BOOKING_REQUIRED_FIELDS:
            if field not in required_fields:
                required_fields.append(field)
    for field in REQUIRED_POLICY_FIELDS:
        if field not in required_fields:
            required_fields.append(field)
    return required_fields


def strip_compiled_artifacts(payload: dict | None) -> dict | None:
    if not isinstance(payload, dict):
        return payload
    if _COMPILED_ARTIFACTS_KEY not in payload:
        return payload
    return {key: value for key, value in payload.items() if key != _COMPILED_ARTIFACTS_KEY}


def _get_nested_value(data: dict, path: str) -> Any:
    current: Any = data
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return _MISSING
        current = current[key]
    return current


def _is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _matches_structured_shape(previous_value: Any, next_value: Any) -> bool:
    if isinstance(previous_value, dict):
        return isinstance(next_value, dict) and len(next_value) > 0
    if isinstance(previous_value, list):
        return isinstance(next_value, list) and len(next_value) > 0
    return True


def _normalize_payload(data: dict) -> dict:
    if "client_pack" in data and isinstance(data.get("client_pack"), dict):
        return data
    return {"client_pack": data}


def _normalize_language_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        items = value
    elif isinstance(value, tuple):
        items = list(value)
    elif isinstance(value, str):
        items = [value]
    else:
        return []
    normalized: list[str] = []
    for item in items:
        if not isinstance(item, str):
            item = str(item)
        cleaned = item.strip().casefold()
        if not cleaned:
            continue
        cleaned = _LANGUAGE_ALIASES.get(cleaned, cleaned)
        normalized.append(cleaned)
    return normalized


def _has_duration_data(payload: dict) -> bool:
    duration_estimates = _get_nested_value(payload, "client_pack.service_duration_estimates")
    if duration_estimates is not _MISSING and not _is_empty_value(duration_estimates):
        return True
    services = _get_nested_value(payload, "client_pack.services_catalog.services")
    if not isinstance(services, list):
        return False
    for service in services:
        if not isinstance(service, dict):
            continue
        for key in _MINIMUM_DATA_DURATION_KEYS:
            if not _is_empty_value(service.get(key)):
                return True
    return False


def _extract_domain_slug_from_payload(payload: dict) -> str | None:
    normalized = _normalize_payload(payload)
    for path in (
        "client_pack.domain_slug",
        "domain_slug",
    ):
        value = _get_nested_value(normalized, path)
        if isinstance(value, str) and value.strip():
            return _normalize_domain_slug(value)
    return None


def get_missing_required_fields(
    payload: dict,
    *,
    required_fields: list[str] | None = None,
    domain_slug: str | None = None,
    require_booking: bool | None = None,
) -> list[str]:
    normalized = _normalize_payload(payload)
    normalized_domain = _normalize_domain_slug(domain_slug)
    fields = (
        required_fields
        if required_fields is not None
        else get_required_fields_for_domain(
            domain_slug=normalized_domain,
            require_booking=require_booking,
        )
    )
    missing: list[str] = []
    for path in fields:
        candidates = _validation_path_candidates(path)
        values = [_get_nested_value(normalized, candidate) for candidate in candidates]
        if all(value is _MISSING or _is_empty_value(value) for value in values):
            missing.append(path)
    language_path = "client_pack.communication.languages"
    language_values = [
        _get_nested_value(normalized, candidate)
        for candidate in _validation_path_candidates(language_path)
    ]
    language_payloads = [
        value for value in language_values if value is not _MISSING and not _is_empty_value(value)
    ]
    if (
        language_payloads
        and language_path not in missing
    ):
        normalized_languages: set[str] = set()
        for value in language_payloads:
            normalized_languages.update(_normalize_language_list(value))
        if not normalized_languages or not set(MINIMUM_DATA_REQUIRED_LANGUAGES).issubset(
            normalized_languages
        ):
            missing.append(language_path)
    return missing


def get_lossy_structured_rewrite_paths(
    payload: dict,
    *,
    previous_payload: dict | None,
) -> list[str]:
    if not isinstance(previous_payload, dict):
        return []
    normalized_previous = _normalize_payload(previous_payload)
    normalized_next = _normalize_payload(payload)
    blocked: list[str] = []
    for path in _STRUCTURED_REWRITE_GUARDED_PATHS:
        previous_value = _get_nested_value(normalized_previous, path)
        if previous_value is _MISSING or _is_empty_value(previous_value):
            continue
        if not isinstance(previous_value, (dict, list)):
            continue
        next_value = _get_nested_value(normalized_next, path)
        if next_value is _MISSING or _is_empty_value(next_value):
            blocked.append(path)
            continue
        if not _matches_structured_shape(previous_value, next_value):
            blocked.append(path)
    return blocked


def is_lossy_structured_rewrite_error(message: str) -> bool:
    return isinstance(message, str) and message.startswith(LOSSY_STRUCTURED_REWRITE_ERROR_PREFIX)


def should_block_draft_persist(errors: list[str]) -> bool:
    return any(is_lossy_structured_rewrite_error(message) for message in errors)


def get_missing_minimum_data_fields(payload: dict) -> list[str]:
    normalized = _normalize_payload(payload)
    domain_slug = _extract_domain_slug_from_payload(normalized)
    required_fields = get_required_fields_for_domain(domain_slug=domain_slug)
    missing = get_missing_required_fields(
        normalized,
        required_fields=required_fields,
    )
    if (
        "client_pack.service_duration_estimates" in required_fields
        and
        "client_pack.services_catalog.services" not in missing
        and "client_pack.service_duration_estimates" not in missing
        and not _has_duration_data(normalized)
    ):
        missing.append("client_pack.service_duration_estimates")
    language_path = "client_pack.communication.languages"
    if language_path not in missing:
        language_values = [
            _get_nested_value(normalized, candidate)
            for candidate in _validation_path_candidates(language_path)
        ]
        language_payloads = [
            value for value in language_values if value is not _MISSING and not _is_empty_value(value)
        ]
        if language_payloads:
            normalized_languages: set[str] = set()
            for languages in language_payloads:
                normalized_languages.update(_normalize_language_list(languages))
            if not normalized_languages or not set(MINIMUM_DATA_REQUIRED_LANGUAGES).issubset(
                normalized_languages
            ):
                missing.append(language_path)
    return missing


@dataclass(frozen=True)
class MinimumDataContractStatus:
    ready: bool
    missing_fields: list[str]


def evaluate_minimum_data_contract(payload: dict | None) -> MinimumDataContractStatus:
    if not isinstance(payload, dict):
        return MinimumDataContractStatus(ready=False, missing_fields=["client_pack"])
    missing = get_missing_minimum_data_fields(payload)
    return MinimumDataContractStatus(ready=not missing, missing_fields=missing)


def parse_draft_text(draft_text: str) -> tuple[dict | None, list[str]]:
    if not draft_text or not draft_text.strip():
        return None, ["draft_text is required"]
    try:
        payload = yaml.safe_load(draft_text)
    except Exception as exc:  # pragma: no cover - yaml error text varies
        return None, [f"Invalid YAML/JSON: {exc}"]
    if not isinstance(payload, dict):
        return None, ["Draft must be an object (YAML/JSON map)"]
    return _normalize_payload(payload), []


def validate_payload(
    payload: dict,
    *,
    previous_payload: dict | None = None,
    required_fields: list[str] | None = None,
    domain_slug: str | None = None,
    require_booking: bool | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if previous_payload:
        for path in get_lossy_structured_rewrite_paths(
            payload,
            previous_payload=previous_payload,
        ):
            errors.append(f"{LOSSY_STRUCTURED_REWRITE_ERROR_PREFIX}{path}")

    missing_fields = get_missing_required_fields(
        payload,
        required_fields=required_fields,
        domain_slug=domain_slug,
        require_booking=require_booking,
    )
    for path in missing_fields:
        errors.append(f"Missing required field: {path}")

    if previous_payload:
        warnings.extend(_diff_warnings(previous_payload, payload))

    return errors, warnings


def _diff_warnings(previous_payload: dict, payload: dict) -> list[str]:
    warnings: list[str] = []
    prev_services = _count_services(previous_payload)
    next_services = _count_services(payload)
    if prev_services and next_services < prev_services:
        warnings.append(
            f"services_catalog.services reduced: {prev_services} → {next_services}"
        )

    prev_price_items = _count_price_items(previous_payload)
    next_price_items = _count_price_items(payload)
    if prev_price_items and next_price_items < prev_price_items:
        warnings.append(
            f"price_list items reduced: {prev_price_items} → {next_price_items}"
        )
    return warnings


def _count_services(payload: dict) -> int:
    client_pack = payload.get("client_pack") if isinstance(payload, dict) else None
    if not isinstance(client_pack, dict):
        return 0
    catalog = client_pack.get("services_catalog")
    if not isinstance(catalog, dict):
        return 0
    services = catalog.get("services")
    if not isinstance(services, list):
        return 0
    return sum(1 for item in services if isinstance(item, dict))


def _count_price_items(payload: dict) -> int:
    client_pack = payload.get("client_pack") if isinstance(payload, dict) else None
    if not isinstance(client_pack, dict):
        return 0
    price_list = client_pack.get("price_list")
    if not isinstance(price_list, list):
        return 0
    total = 0
    for category in price_list:
        if not isinstance(category, dict):
            continue
        items = category.get("items")
        if isinstance(items, list):
            total += sum(1 for item in items if isinstance(item, dict))
    return total


def build_diff(current_payload: dict | None, next_payload: dict) -> str:
    import difflib

    current_text = dump_pack_yaml(current_payload) if current_payload else ""
    next_text = dump_pack_yaml(next_payload)
    diff_lines = difflib.unified_diff(
        current_text.splitlines(),
        next_text.splitlines(),
        fromfile="current",
        tofile="draft",
        lineterm="",
    )
    return "\n".join(diff_lines)


def dump_pack_yaml(payload: dict | None) -> str:
    if not payload:
        return ""
    payload = strip_compiled_artifacts(payload)
    return yaml.safe_dump(
        payload,
        sort_keys=False,
        allow_unicode=True,
    ).strip()


def build_payload_checksum(payload: dict) -> str:
    payload = strip_compiled_artifacts(payload)
    payload_text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload_text.encode("utf-8")).hexdigest()


def build_summary(payload: dict) -> str | None:
    client_pack = payload.get("client_pack") if isinstance(payload, dict) else None
    if not isinstance(client_pack, dict):
        return None
    business = client_pack.get("business")
    location = client_pack.get("location")
    salon = client_pack.get("salon")

    name = ""
    if isinstance(business, dict):
        name = str(business.get("name") or "").strip()
    if not name and isinstance(salon, dict):
        name = str(salon.get("name") or "").strip()

    city = ""
    if isinstance(location, dict):
        city = str(location.get("city") or "").strip()
    if not city and isinstance(salon, dict):
        city = str(salon.get("city") or "").strip()

    if name and city:
        return f"{name} ({city})"
    return name or None
