from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from app.schemas.capabilities import CapabilitiesPayload
from app.services.console_errors import ConsoleAPIError


def _summarize_validation_error(exc: ValidationError, *, limit: int = 3) -> str:
    parts: list[str] = []
    for item in exc.errors():
        loc = item.get("loc") or []
        loc_text = ".".join(str(entry) for entry in loc) if loc else ""
        msg = item.get("msg") or "invalid"
        if loc_text:
            parts.append(f"{loc_text}:{msg}")
        else:
            parts.append(msg)
        if len(parts) >= limit:
            break
    return "; ".join(parts) or "invalid_payload"


def validate_capabilities_payload(payload_json: dict[str, Any]) -> CapabilitiesPayload:
    try:
        return CapabilitiesPayload.model_validate(payload_json)
    except ValidationError as exc:
        summary = _summarize_validation_error(exc)
        raise ConsoleAPIError(400, "INVALID_PARAM", f"Invalid capabilities payload: {summary}") from exc


def payload_to_dict(payload: CapabilitiesPayload) -> dict[str, Any]:
    data = payload.model_dump(exclude_none=True)
    data.setdefault("channels", {})
    data.setdefault("providers", {})
    data.setdefault("features", {})
    data.setdefault("tools", {})
    data.setdefault("policy_overrides", {})
    return data


def merge_capabilities(base: dict[str, Any] | None, override: dict[str, Any] | None) -> dict[str, Any]:
    merged = deepcopy(base or {})
    for section in ("channels", "providers", "features", "tools"):
        if section not in merged or not isinstance(merged.get(section), dict):
            merged[section] = {}

    if not override:
        return merged

    for key, value in override.items():
        if value is None:
            continue
        if isinstance(value, dict):
            current = merged.get(key)
            if not isinstance(current, dict):
                current = {}
            for sub_key, sub_value in value.items():
                if sub_value is None:
                    continue
                current[sub_key] = sub_value
            merged[key] = current
        else:
            merged[key] = value
    return merged


def merge_capabilities_layers(*layers: dict[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for layer in layers:
        merged = merge_capabilities(merged, layer)
    return merged
