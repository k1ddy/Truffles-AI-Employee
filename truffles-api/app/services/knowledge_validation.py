from __future__ import annotations

import hashlib
import json
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
    "client_pack.booking.collect_fields",
    "client_pack.booking.bot_can_confirm",
    "client_pack.price_list",
]

_MISSING = object()


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

    for path in REQUIRED_CLIENT_PACK_FIELDS:
        value = _get_nested_value(payload, path)
        if value is _MISSING or _is_empty_value(value):
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
    return yaml.safe_dump(
        payload,
        sort_keys=False,
        allow_unicode=True,
    ).strip()


def build_payload_checksum(payload: dict) -> str:
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
