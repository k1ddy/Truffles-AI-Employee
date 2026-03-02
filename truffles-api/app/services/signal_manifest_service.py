from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker, RefResolver

_SIGNAL_MANIFEST_SCHEMA_RELATIVE = "contracts/packs/signal_manifest.v1.jsonschema"
_FLAG_BY_NAME = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "DOTALL": re.DOTALL,
}


class SignalManifestError(RuntimeError):
    pass


@dataclass(frozen=True)
class CompiledSignalManifest:
    schema_version: str
    compiled_version: str
    manifest_path: str
    manifest_signature: str
    manifest_fingerprint: str
    compiled_at_utc: str
    payload: dict[str, Any]
    regex_by_section: dict[str, dict[str, re.Pattern[str]]]
    replacement_by_section: dict[str, dict[str, tuple[tuple[re.Pattern[str], str], ...]]]
    tokens_by_section: dict[str, dict[str, tuple[str, ...]]]
    char_maps_by_section: dict[str, dict[str, dict[str, str]]]


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        has_contracts = (parent / "contracts" / "packs").is_dir()
        has_repo_layout = (parent / "truffles-api" / "app").is_dir()
        has_container_layout = (parent / "app").is_dir()
        if has_contracts and (has_repo_layout or has_container_layout):
            return parent
    raise SignalManifestError("Unable to locate repository root for signal manifest service")


def _manifest_path() -> Path:
    root = _repo_root()
    candidates = (
        root / "truffles-api" / "app" / "knowledge" / "generic" / "SIGNAL_MANIFEST.yaml",
        root / "app" / "knowledge" / "generic" / "SIGNAL_MANIFEST.yaml",
    )
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def _schema_path() -> Path:
    return _repo_root() / _SIGNAL_MANIFEST_SCHEMA_RELATIVE


@lru_cache(maxsize=1)
def _load_schema_validator() -> Draft202012Validator:
    path = _schema_path()
    schema = json.loads(path.read_text(encoding="utf-8"))
    resolver = RefResolver(base_uri=path.resolve().as_uri(), referrer=schema)
    return Draft202012Validator(schema, resolver=resolver, format_checker=FormatChecker())


def _validate_manifest(payload: dict[str, Any]) -> None:
    validator = _load_schema_validator()
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.path))
    if not errors:
        return
    messages = []
    for err in errors:
        path = ".".join(str(part) for part in err.path) or "<root>"
        messages.append(f"{path}: {err.message}")
    raise SignalManifestError(
        "Signal manifest schema validation failed: " + "; ".join(messages[:8])
    )


def _regex_flags(flags: Any) -> int:
    if not isinstance(flags, list):
        return 0
    value = 0
    for token in flags:
        normalized = str(token or "").strip().upper()
        if normalized:
            value |= _FLAG_BY_NAME.get(normalized, 0)
    return value


def _compile_regex_spec(spec: Any, *, label: str) -> re.Pattern[str]:
    if not isinstance(spec, dict):
        raise SignalManifestError(f"Signal manifest regex spec is not object: {label}")
    pattern = spec.get("pattern")
    if not isinstance(pattern, str) or not pattern:
        raise SignalManifestError(f"Signal manifest regex pattern missing: {label}")
    try:
        return re.compile(pattern, _regex_flags(spec.get("flags")))
    except re.error as exc:
        raise SignalManifestError(f"Signal manifest regex compile failed ({label}): {exc}") from exc


def _compile_regex_section(payload: Any, *, label: str) -> dict[str, re.Pattern[str]]:
    if not isinstance(payload, dict):
        raise SignalManifestError(f"Signal manifest regex section is not object: {label}")
    compiled: dict[str, re.Pattern[str]] = {}
    for key, spec in payload.items():
        key_text = str(key or "").strip()
        if not key_text:
            continue
        compiled[key_text] = _compile_regex_spec(spec, label=f"{label}.{key_text}")
    return compiled


def _compile_replacement_section(
    payload: Any,
    *,
    label: str,
) -> dict[str, tuple[tuple[re.Pattern[str], str], ...]]:
    if not isinstance(payload, dict):
        return {}
    compiled: dict[str, tuple[tuple[re.Pattern[str], str], ...]] = {}
    for key, items in payload.items():
        key_text = str(key or "").strip()
        if not key_text or not isinstance(items, list):
            continue
        rows: list[tuple[re.Pattern[str], str]] = []
        for index, row in enumerate(items):
            if not isinstance(row, dict):
                continue
            replacement = row.get("replacement")
            if not isinstance(replacement, str):
                continue
            pattern = _compile_regex_spec(row, label=f"{label}.{key_text}[{index}]")
            rows.append((pattern, replacement))
        compiled[key_text] = tuple(rows)
    return compiled


def _compile_tokens_section(payload: Any) -> dict[str, tuple[str, ...]]:
    if not isinstance(payload, dict):
        return {}
    compiled: dict[str, tuple[str, ...]] = {}
    for key, values in payload.items():
        key_text = str(key or "").strip()
        if not key_text or not isinstance(values, list):
            continue
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in values:
            token = str(raw or "").strip()
            if not token:
                continue
            fold = token.casefold()
            if fold in seen:
                continue
            seen.add(fold)
            normalized.append(token)
        compiled[key_text] = tuple(normalized)
    return compiled


def _compile_char_maps_section(payload: Any) -> dict[str, dict[str, str]]:
    if not isinstance(payload, dict):
        return {}
    compiled: dict[str, dict[str, str]] = {}
    for key, mapping in payload.items():
        key_text = str(key or "").strip()
        if not key_text or not isinstance(mapping, dict):
            continue
        normalized: dict[str, str] = {}
        for raw_key, raw_value in mapping.items():
            char_key = str(raw_key or "")
            char_value = str(raw_value or "")
            if len(char_key) != 1 or len(char_value) != 1:
                continue
            normalized[char_key] = char_value
        compiled[key_text] = normalized
    return compiled


def _manifest_signature(path: Path) -> str:
    try:
        stat = path.stat()
    except FileNotFoundError as exc:
        raise SignalManifestError(f"Signal manifest file not found: {path}") from exc
    return f"{stat.st_mtime_ns}:{stat.st_size}"


@lru_cache(maxsize=8)
def _compile_manifest_cached(manifest_path: str, manifest_signature: str) -> CompiledSignalManifest:
    del manifest_signature
    path = Path(manifest_path)
    if not path.exists():
        raise SignalManifestError(f"Signal manifest file not found: {path}")

    raw_bytes = path.read_bytes()
    manifest_fingerprint = hashlib.sha256(raw_bytes).hexdigest()
    try:
        raw_payload = yaml.safe_load(raw_bytes.decode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive parse guard
        raise SignalManifestError(f"Signal manifest parse failed: {exc}") from exc

    payload = raw_payload if isinstance(raw_payload, dict) else {}
    _validate_manifest(payload)

    booking = payload.get("booking") if isinstance(payload.get("booking"), dict) else {}
    info = payload.get("info") if isinstance(payload.get("info"), dict) else {}

    booking_regex = _compile_regex_section(booking.get("regex"), label="booking.regex")
    info_regex = _compile_regex_section(info.get("regex"), label="info.regex")

    booking_replacements = _compile_replacement_section(
        booking.get("replacement_patterns"),
        label="booking.replacement_patterns",
    )
    booking_tokens = _compile_tokens_section(booking.get("tokens"))
    booking_char_maps = _compile_char_maps_section(
        {"layout_swap_map": booking.get("layout_swap_map")}
    )

    schema_version = str(payload.get("schema_version") or "signal_manifest.v1")
    compiled_version = f"{schema_version}:{manifest_fingerprint[:12]}"

    return CompiledSignalManifest(
        schema_version=schema_version,
        compiled_version=compiled_version,
        manifest_path=str(path),
        manifest_signature=_manifest_signature(path),
        manifest_fingerprint=manifest_fingerprint,
        compiled_at_utc=datetime.now(timezone.utc).isoformat(),
        payload=payload,
        regex_by_section={
            "booking": booking_regex,
            "info": info_regex,
        },
        replacement_by_section={
            "booking": booking_replacements,
        },
        tokens_by_section={
            "booking": booking_tokens,
        },
        char_maps_by_section={
            "booking": booking_char_maps,
        },
    )


def clear_signal_manifest_cache() -> None:
    _load_schema_validator.cache_clear()
    _compile_manifest_cached.cache_clear()


def get_compiled_signal_manifest(*, force_reload: bool = False) -> CompiledSignalManifest:
    if force_reload:
        clear_signal_manifest_cache()
    path = _manifest_path()
    signature = _manifest_signature(path)
    return _compile_manifest_cached(str(path), signature)


def load_signal_manifest() -> dict[str, Any]:
    return copy.deepcopy(get_compiled_signal_manifest().payload)


def get_signal_manifest_runtime_meta() -> dict[str, str]:
    bundle = get_compiled_signal_manifest()
    return {
        "schema_version": bundle.schema_version,
        "compiled_version": bundle.compiled_version,
        "manifest_path": bundle.manifest_path,
        "manifest_signature": bundle.manifest_signature,
        "manifest_fingerprint": bundle.manifest_fingerprint,
        "compiled_at_utc": bundle.compiled_at_utc,
    }


def get_signal_regex_pattern(section: str, key: str) -> re.Pattern[str] | None:
    bundle = get_compiled_signal_manifest()
    return (bundle.regex_by_section.get(section) or {}).get(key)


def get_signal_regex_replacements(section: str, key: str) -> tuple[tuple[re.Pattern[str], str], ...]:
    bundle = get_compiled_signal_manifest()
    return (bundle.replacement_by_section.get(section) or {}).get(key) or tuple()


def get_signal_text_tokens(section: str, key: str) -> tuple[str, ...]:
    bundle = get_compiled_signal_manifest()
    return (bundle.tokens_by_section.get(section) or {}).get(key) or tuple()


def get_signal_char_map(section: str, key: str) -> dict[str, str]:
    bundle = get_compiled_signal_manifest()
    return dict((bundle.char_maps_by_section.get(section) or {}).get(key) or {})


def get_booking_regex_pattern(key: str) -> re.Pattern[str] | None:
    return get_signal_regex_pattern("booking", key)


def get_booking_regex_replacements(key: str) -> tuple[tuple[re.Pattern[str], str], ...]:
    return get_signal_regex_replacements("booking", key)


def get_booking_text_tokens(key: str) -> tuple[str, ...]:
    return get_signal_text_tokens("booking", key)


def get_booking_layout_swap_map() -> dict[str, str]:
    return get_signal_char_map("booking", "layout_swap_map")


def get_info_regex_pattern(key: str) -> re.Pattern[str] | None:
    return get_signal_regex_pattern("info", key)


__all__ = [
    "CompiledSignalManifest",
    "SignalManifestError",
    "clear_signal_manifest_cache",
    "get_booking_layout_swap_map",
    "get_booking_regex_pattern",
    "get_booking_regex_replacements",
    "get_booking_text_tokens",
    "get_compiled_signal_manifest",
    "get_info_regex_pattern",
    "get_signal_char_map",
    "get_signal_manifest_runtime_meta",
    "get_signal_regex_pattern",
    "get_signal_regex_replacements",
    "get_signal_text_tokens",
    "load_signal_manifest",
]
