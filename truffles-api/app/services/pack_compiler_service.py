from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from jsonschema import Draft202012Validator, FormatChecker, RefResolver

from app.services.knowledge_validation import strip_compiled_artifacts

COMPILED_ARTIFACTS_KEY = "compiled_artifacts"
PACK_INDEX_SCHEMA_VERSION = "pack_index.v1"
COMPILED_PACK_SCHEMA_VERSION = "compiled_pack.v1"
POLICY_BUNDLE_SCHEMA_VERSION = "policy_bundle.v1"
SIGNAL_GRAPH_SCHEMA_VERSION = "signal_graph.v1"


class PackCompilerError(RuntimeError):
    def __init__(self, message: str, *, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "contracts" / "packs" / "signal_graph.v1.jsonschema").is_file():
            return parent
    for parent in current.parents:
        if (parent / "contracts").is_dir():
            return parent
    return current.parents[3]


def _load_schema(relative_path: str) -> Draft202012Validator:
    schema_path = _repo_root() / relative_path
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    resolver = RefResolver(base_uri=schema_path.resolve().as_uri(), referrer=schema)
    return Draft202012Validator(schema, resolver=resolver, format_checker=FormatChecker())


def _validate_schema(relative_path: str, payload: dict[str, Any]) -> None:
    validator = _load_schema(relative_path)
    errors = sorted(validator.iter_errors(payload), key=lambda err: err.path)
    if not errors:
        return
    messages = []
    for error in errors:
        location = ".".join(str(part) for part in error.path)
        if location:
            messages.append(f"{location}: {error.message}")
        else:
            messages.append(error.message)
    raise PackCompilerError("Pack compiler schema validation failed", errors=messages)


def _coerce_string_list(value: Any) -> list[str]:
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
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, str):
            item = str(item)
        cleaned = item.strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
    return normalized


def _normalize_lang_map(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, list[str]] = {}
    for lang_key, items in value.items():
        if not isinstance(lang_key, str):
            continue
        cleaned_key = lang_key.strip().casefold()
        if not cleaned_key:
            continue
        normalized_items = _coerce_string_list(items)
        if normalized_items:
            normalized[cleaned_key] = normalized_items
    return normalized


def _normalize_anchor_map(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    anchors: dict[str, list[str]] = {}
    for key in ("in_domain", "out_of_domain", "strict_in"):
        normalized = _coerce_string_list(value.get(key))
        if normalized:
            anchors[key] = normalized
    return anchors


def _extract_domain_pack(payload_json: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload_json, dict):
        return {}
    domain_pack = payload_json.get("domain_pack")
    if isinstance(domain_pack, dict):
        return domain_pack
    client_pack = payload_json.get("client_pack")
    if isinstance(client_pack, dict) and isinstance(client_pack.get("domain_pack"), dict):
        return client_pack["domain_pack"]
    return {}


def _extract_policy_pack(payload_json: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload_json, dict):
        return {}
    client_pack = payload_json.get("client_pack")
    if isinstance(client_pack, dict) and isinstance(client_pack.get("policy"), dict):
        return dict(client_pack["policy"])
    policy = payload_json.get("policy")
    if isinstance(policy, dict):
        return dict(policy)
    return {}


def _build_effective_pack(payload_json: dict[str, Any]) -> dict[str, Any]:
    payload = strip_compiled_artifacts(payload_json) if isinstance(payload_json, dict) else {}
    client_pack = payload.get("client_pack")
    effective: dict[str, Any] = {}
    if isinstance(client_pack, dict):
        effective.update(client_pack)
        effective["client_pack"] = client_pack
        for key, value in payload.items():
            if key in {"client_pack", COMPILED_ARTIFACTS_KEY}:
                continue
            effective[key] = value
        return effective
    return {key: value for key, value in payload.items() if key != COMPILED_ARTIFACTS_KEY}


def _build_signal_graph(domain_pack: dict[str, Any]) -> dict[str, Any]:
    signal_graph: dict[str, Any] = {"schema_version": SIGNAL_GRAPH_SCHEMA_VERSION}
    anchors = _normalize_anchor_map(domain_pack.get("ood_anchors"))
    if anchors:
        signal_graph["ood_anchors"] = anchors
    lexicons: dict[str, dict[str, list[str]]] = {}
    for key, label in (
        ("guest_policy_lexicon", "guest_policy"),
        ("service_request_lexicon", "service_request"),
        ("services_overview_lexicon", "services_overview"),
        ("datetime_lexicon", "datetime"),
    ):
        normalized = _normalize_lang_map(domain_pack.get(key))
        if normalized:
            lexicons[label] = normalized
    if lexicons:
        signal_graph["lexicons"] = lexicons
    signal_lexicons = domain_pack.get("signal_lexicons")
    if isinstance(signal_lexicons, dict) and signal_lexicons:
        signal_graph["signal_lexicons"] = signal_lexicons
    _validate_schema("contracts/packs/signal_graph.v1.jsonschema", signal_graph)
    return signal_graph


def _build_policy_bundle(payload_json: dict[str, Any]) -> dict[str, Any]:
    policy_pack = _extract_policy_pack(payload_json)
    bundle = {"schema_version": POLICY_BUNDLE_SCHEMA_VERSION, "policy": policy_pack}
    _validate_schema("contracts/policy/policy_bundle.v1.jsonschema", bundle)
    return bundle


def _extract_pack_versions(payload_json: dict[str, Any]) -> dict[str, Any]:
    versions: dict[str, Any] = {}
    client_pack = payload_json.get("client_pack") if isinstance(payload_json, dict) else None
    if isinstance(client_pack, dict) and isinstance(client_pack.get("version"), str):
        versions["client_pack"] = client_pack.get("version")
    company_pack = payload_json.get("company_pack")
    if isinstance(company_pack, dict) and isinstance(company_pack.get("version"), str):
        versions["company_pack"] = company_pack.get("version")
    domain_pack = _extract_domain_pack(payload_json)
    if isinstance(domain_pack, dict) and isinstance(domain_pack.get("version"), str):
        versions["domain_pack"] = domain_pack.get("version")
    return versions


def _hash_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _hash_compiled_payload(compiled_payload: dict[str, Any]) -> str:
    payload = dict(compiled_payload)
    payload.pop("compiled_at", None)
    payload.pop("hash", None)
    return _hash_payload(payload)


def build_pack_index(payload_json: dict[str, Any]) -> dict[str, Any] | None:
    domain_pack = _extract_domain_pack(payload_json)
    if not domain_pack:
        return None

    anchors: dict[str, list[str]] = {}
    ood_anchors = domain_pack.get("ood_anchors")
    if isinstance(ood_anchors, dict):
        in_domain = _coerce_string_list(ood_anchors.get("in_domain"))
        out_domain = _coerce_string_list(ood_anchors.get("out_of_domain"))
        strict_in = _coerce_string_list(ood_anchors.get("strict_in"))
        if in_domain:
            anchors["in_domain"] = in_domain
        if out_domain:
            anchors["out_of_domain"] = out_domain
        if strict_in:
            anchors["strict_in"] = strict_in

    lexicons: dict[str, dict[str, list[str]]] = {}
    for key, label in (
        ("guest_policy_lexicon", "guest_policy"),
        ("service_request_lexicon", "service_request"),
        ("services_overview_lexicon", "services_overview"),
        ("datetime_lexicon", "datetime"),
    ):
        normalized = _normalize_lang_map(domain_pack.get(key))
        if normalized:
            lexicons[label] = normalized

    index_payload: dict[str, Any] = {"schema_version": PACK_INDEX_SCHEMA_VERSION}
    if anchors:
        index_payload["anchors"] = anchors
    if lexicons:
        index_payload["lexicons"] = lexicons
    if len(index_payload) == 1:
        return None

    index_payload["hash"] = _hash_payload(index_payload)
    return index_payload


def compile_pack_payload(
    payload_json: dict[str, Any],
    *,
    compiled_at: datetime | None = None,
) -> dict[str, Any]:
    if not isinstance(payload_json, dict):
        raise PackCompilerError("Pack compiler expected dict payload", errors=["payload_json must be a dict"])

    now = compiled_at or datetime.now(timezone.utc)
    payload = strip_compiled_artifacts(payload_json)
    domain_pack = _extract_domain_pack(payload)
    pack_index = build_pack_index(payload) or {}
    signal_graph = _build_signal_graph(domain_pack)
    policy_bundle = _build_policy_bundle(payload)
    effective_pack = _build_effective_pack(payload)
    versions = _extract_pack_versions(payload)

    compiled_payload: dict[str, Any] = {
        "schema_version": COMPILED_PACK_SCHEMA_VERSION,
        "compiled_at": now.isoformat(),
        "pack_index": pack_index,
        "signal_graph": signal_graph,
        "policy_bundle": policy_bundle,
        "effective_pack": effective_pack,
    }
    if versions:
        compiled_payload["versions"] = versions
    compiled_payload["hash"] = _hash_compiled_payload(compiled_payload)
    return compiled_payload


def extract_compiled_artifacts(
    payload_json: dict[str, Any],
    *,
    compile_if_missing: bool = True,
) -> dict[str, Any] | None:
    if not isinstance(payload_json, dict):
        return None
    compiled = payload_json.get(COMPILED_ARTIFACTS_KEY)
    if isinstance(compiled, dict):
        return compiled
    if not compile_if_missing:
        return None
    return compile_pack_payload(payload_json)


def inject_compiled_artifacts(
    payload_json: dict[str, Any],
    compiled_artifacts: dict[str, Any],
) -> dict[str, Any]:
    payload = strip_compiled_artifacts(payload_json) if isinstance(payload_json, dict) else {}
    enriched = copy.deepcopy(payload)
    enriched[COMPILED_ARTIFACTS_KEY] = copy.deepcopy(compiled_artifacts)
    return enriched


def build_compiled_pack_meta(
    compiled_artifacts: dict[str, Any],
    *,
    version_id: UUID | None,
    source: str,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "schema_version": compiled_artifacts.get("schema_version"),
        "hash": compiled_artifacts.get("hash"),
        "version_id": str(version_id) if version_id else None,
        "compiled_at": compiled_artifacts.get("compiled_at"),
        "source": source,
    }
    return {key: value for key, value in meta.items() if value is not None}


def parse_compiled_at(value: str | None) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
