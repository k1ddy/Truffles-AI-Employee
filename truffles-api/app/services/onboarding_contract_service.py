from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from app.schemas.capabilities import CapabilitiesPayload
from app.schemas.onboarding_contract import OnboardingContractPayload
from app.services.capabilities_service import merge_capabilities
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


def validate_onboarding_contract_payload(payload_json: dict[str, Any]) -> OnboardingContractPayload:
    try:
        return OnboardingContractPayload.model_validate(payload_json)
    except ValidationError as exc:
        summary = _summarize_validation_error(exc)
        raise ConsoleAPIError(400, "INVALID_PARAM", f"Invalid onboarding contract payload: {summary}") from exc


def onboarding_contract_payload_to_dict(payload: OnboardingContractPayload) -> dict[str, Any]:
    data = payload.model_dump(exclude_none=True, mode="json")
    purchased = data.get("purchased")
    if not isinstance(purchased, dict):
        purchased = {}
        data["purchased"] = purchased
    purchased.setdefault("channels", {})
    purchased.setdefault("providers", {})
    purchased.setdefault("features", {})
    provider_binding = data.get("provider_binding")
    if not isinstance(provider_binding, dict):
        provider_binding = {}
        data["provider_binding"] = provider_binding
    whatsapp_binding = provider_binding.get("whatsapp")
    if not isinstance(whatsapp_binding, dict):
        provider_binding["whatsapp"] = {}
    return data


def _merge_provider_binding(
    base: dict[str, Any] | None,
    override: dict[str, Any] | None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    if isinstance(base, dict):
        merged = deepcopy(base)

    whatsapp_base = merged.get("whatsapp")
    if not isinstance(whatsapp_base, dict):
        whatsapp_base = {}

    if isinstance(override, dict):
        whatsapp_override = override.get("whatsapp")
        if isinstance(whatsapp_override, dict):
            whatsapp_base = {**whatsapp_base, **whatsapp_override}

    merged["whatsapp"] = whatsapp_base
    return merged


def merge_onboarding_contract(
    base: dict[str, Any] | None,
    override: dict[str, Any] | None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "purchased": {
            "channels": {},
            "providers": {},
            "features": {},
        }
    }
    if isinstance(base, dict):
        merged = deepcopy(base)
    purchased_base = merged.get("purchased") if isinstance(merged, dict) else None
    if not isinstance(purchased_base, dict):
        purchased_base = {}

    purchased_override: dict[str, Any] | None = None
    if isinstance(override, dict):
        override_domain_slug = override.get("domain_slug")
        if isinstance(override_domain_slug, str) and override_domain_slug.strip():
            merged["domain_slug"] = override_domain_slug.strip()
        elif "domain_slug" not in merged and override_domain_slug is None:
            merged["domain_slug"] = None
        raw_override_purchased = override.get("purchased")
        if isinstance(raw_override_purchased, dict):
            purchased_override = raw_override_purchased

    merged["purchased"] = merge_capabilities(purchased_base, purchased_override)
    provider_binding_base = merged.get("provider_binding") if isinstance(merged, dict) else None
    provider_binding_override = override.get("provider_binding") if isinstance(override, dict) else None
    merged["provider_binding"] = _merge_provider_binding(provider_binding_base, provider_binding_override)
    if "domain_slug" not in merged:
        merged["domain_slug"] = None
    return merged


def _match_enabled_boolean(
    *,
    effective: bool | None,
    purchased: bool | None,
    key: str,
) -> list[str]:
    if effective is True and purchased is not True:
        return [key]
    return []


def find_capability_mismatches(
    *,
    purchased: CapabilitiesPayload,
    effective: CapabilitiesPayload,
) -> list[str]:
    mismatches: list[str] = []

    mismatches.extend(
        _match_enabled_boolean(
            effective=effective.channels.whatsapp,
            purchased=purchased.channels.whatsapp,
            key="channels.whatsapp",
        )
    )
    mismatches.extend(
        _match_enabled_boolean(
            effective=effective.channels.telegram,
            purchased=purchased.channels.telegram,
            key="channels.telegram",
        )
    )
    mismatches.extend(
        _match_enabled_boolean(
            effective=effective.channels.instagram,
            purchased=purchased.channels.instagram,
            key="channels.instagram",
        )
    )

    for key in ("availability_provider", "crm_provider", "calendar_provider"):
        effective_value = getattr(effective.providers, key)
        purchased_value = getattr(purchased.providers, key)
        if effective_value in (None, "none"):
            continue
        if purchased_value != effective_value:
            mismatches.append(f"providers.{key}")

    if effective.features.booking_mode is not None:
        purchased_mode = purchased.features.booking_mode
        if purchased_mode is None:
            mismatches.append("features.booking_mode")
        elif purchased_mode == "collect_preferences" and effective.features.booking_mode == "confirm_slots":
            mismatches.append("features.booking_mode")

    mismatches.extend(
        _match_enabled_boolean(
            effective=effective.features.knowledge_upload,
            purchased=purchased.features.knowledge_upload,
            key="features.knowledge_upload",
        )
    )
    mismatches.extend(
        _match_enabled_boolean(
            effective=effective.features.analytics,
            purchased=purchased.features.analytics,
            key="features.analytics",
        )
    )
    mismatches.extend(
        _match_enabled_boolean(
            effective=effective.features.auto_learn,
            purchased=purchased.features.auto_learn,
            key="features.auto_learn",
        )
    )
    return sorted(set(mismatches))
