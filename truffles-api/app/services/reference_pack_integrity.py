from __future__ import annotations

import hashlib
import json
from typing import Any

from app.services.knowledge_validation import (
    MINIMUM_DATA_CONTRACT_VERSION,
    get_required_fields_for_domain,
)

REFERENCE_PACK_SCHEMA_VERSION = "v2"
REFERENCE_PACK_INTEGRITY_VERSION = "reference_pack_integrity.v2"


def build_required_fields_checksum(required_fields: list[str]) -> str:
    payload_text = json.dumps(required_fields, ensure_ascii=False)
    return hashlib.sha256(payload_text.encode("utf-8")).hexdigest()


def _normalize_domain_slug(domain_slug: str | None) -> str | None:
    if not isinstance(domain_slug, str):
        return None
    normalized = domain_slug.strip().lower()
    return normalized or None


def _normalize_required_fields(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return None
        cleaned = item.strip()
        if not cleaned:
            return None
        result.append(cleaned)
    return result


def _dedupe(values: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def build_reference_pack_metadata(
    *,
    domain_slug: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_domain = _normalize_domain_slug(domain_slug)
    required_fields = get_required_fields_for_domain(domain_slug=normalized_domain)
    checksum = build_required_fields_checksum(required_fields)

    result: dict[str, Any] = dict(metadata or {})
    result["integrity"] = {
        "version": REFERENCE_PACK_INTEGRITY_VERSION,
        "minimum_data_contract_version": MINIMUM_DATA_CONTRACT_VERSION,
        "required_fields": required_fields,
        "required_fields_checksum": checksum,
    }
    return result


def evaluate_reference_pack_integrity(
    *,
    domain_slug: str | None,
    schema_version: str | None,
    metadata: dict[str, Any] | None,
) -> list[str]:
    normalized_domain = _normalize_domain_slug(domain_slug)
    if not normalized_domain:
        return ["reference_pack_domain"]

    expected_required_fields = get_required_fields_for_domain(domain_slug=normalized_domain)
    expected_checksum = build_required_fields_checksum(expected_required_fields)
    issues: list[str] = []

    if (schema_version or "").strip() != REFERENCE_PACK_SCHEMA_VERSION:
        issues.append("reference_pack_schema_version")

    if not isinstance(metadata, dict) or not metadata:
        issues.append("reference_pack_metadata")
        return _dedupe(issues)

    integrity = metadata.get("integrity")
    if not isinstance(integrity, dict):
        issues.append("reference_pack_integrity")
        return _dedupe(issues)

    if (integrity.get("version") or "").strip() != REFERENCE_PACK_INTEGRITY_VERSION:
        issues.append("reference_pack_integrity_version")

    if (integrity.get("minimum_data_contract_version") or "").strip() != MINIMUM_DATA_CONTRACT_VERSION:
        issues.append("reference_pack_minimum_data_contract_version")

    required_fields = _normalize_required_fields(integrity.get("required_fields"))
    if required_fields is None or required_fields != expected_required_fields:
        issues.append("reference_pack_required_fields")

    checksum = integrity.get("required_fields_checksum")
    if not isinstance(checksum, str) or checksum.strip() != expected_checksum:
        issues.append("reference_pack_required_fields_checksum")

    return _dedupe(issues)
