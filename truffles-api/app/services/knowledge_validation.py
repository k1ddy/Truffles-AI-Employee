from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import yaml

REQUIRED_CLIENT_PACK_FIELDS = [
    "client_pack.salon.name",
    "client_pack.salon.city",
    "client_pack.salon.address.full",
    "client_pack.salon.hours.days",
    "client_pack.salon.hours.open",
    "client_pack.salon.hours.close",
    "client_pack.salon.services_summary",
    "client_pack.salon.communication.languages",
    "client_pack.services_catalog.services",
    "client_pack.service_duration_estimates",
    "client_pack.booking.collect_fields",
    "client_pack.booking.bot_can_confirm",
    "client_pack.guest_policy",
    "client_pack.safety.medical_note",
    "client_pack.pricing.price_from_reason",
    "client_pack.quality.expectations_photo",
    "client_pack.price_list",
]

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
MINIMUM_DATA_CONTRACT_VERSION = "minimum_data_contract.v1"
MINIMUM_DATA_REQUIRED_LANGUAGES = ("ru", "kk")
MINIMUM_DATA_REQUIRED_FIELDS = [
    "client_pack.salon.name",
    "client_pack.salon.city",
    "client_pack.salon.address.full",
    "client_pack.salon.hours.days",
    "client_pack.salon.hours.open",
    "client_pack.salon.hours.close",
    "client_pack.salon.services_summary",
    "client_pack.salon.communication.languages",
    "client_pack.services_catalog.services",
    "client_pack.service_duration_estimates",
    "client_pack.booking.collect_fields",
    "client_pack.booking.bot_can_confirm",
    "client_pack.price_list",
    "client_pack.guest_policy",
    "client_pack.safety.medical_note",
    "client_pack.pricing.price_from_reason",
    "client_pack.quality.expectations_photo",
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


def get_missing_required_fields(
    payload: dict,
    *,
    required_fields: list[str] | None = None,
) -> list[str]:
    normalized = _normalize_payload(payload)
    fields = required_fields if required_fields is not None else REQUIRED_PACK_FIELDS
    missing: list[str] = []
    for path in fields:
        value = _get_nested_value(normalized, path)
        if value is _MISSING or _is_empty_value(value):
            missing.append(path)
    language_path = "client_pack.salon.communication.languages"
    language_value = _get_nested_value(normalized, language_path)
    if (
        language_value is not _MISSING
        and not _is_empty_value(language_value)
        and language_path not in missing
    ):
        normalized_languages = set(_normalize_language_list(language_value))
        if not normalized_languages or not set(MINIMUM_DATA_REQUIRED_LANGUAGES).issubset(
            normalized_languages
        ):
            missing.append(language_path)
    return missing


def get_missing_minimum_data_fields(payload: dict) -> list[str]:
    normalized = _normalize_payload(payload)
    missing = get_missing_required_fields(
        normalized,
        required_fields=MINIMUM_DATA_REQUIRED_FIELDS,
    )
    if (
        "client_pack.services_catalog.services" not in missing
        and "client_pack.service_duration_estimates" not in missing
        and not _has_duration_data(normalized)
    ):
        missing.append("client_pack.service_duration_estimates")
    if "client_pack.salon.communication.languages" not in missing:
        languages = _get_nested_value(normalized, "client_pack.salon.communication.languages")
        if languages is not _MISSING:
            normalized_languages = set(_normalize_language_list(languages))
            if not normalized_languages or not set(MINIMUM_DATA_REQUIRED_LANGUAGES).issubset(
                normalized_languages
            ):
                missing.append("client_pack.salon.communication.languages")
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


def validate_payload(payload: dict, *, previous_payload: dict | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    missing_fields = get_missing_required_fields(payload)
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
    salon = client_pack.get("salon")
    if not isinstance(salon, dict):
        return None
    name = str(salon.get("name") or "").strip()
    city = str(salon.get("city") or "").strip()
    if name and city:
        return f"{name} ({city})"
    return name or None
