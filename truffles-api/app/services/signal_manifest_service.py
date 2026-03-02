from __future__ import annotations

import json
import re
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


@lru_cache(maxsize=1)
def load_signal_manifest() -> dict[str, Any]:
    path = _manifest_path()
    if not path.exists():
        raise SignalManifestError(f"Signal manifest file not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive parse guard
        raise SignalManifestError(f"Signal manifest parse failed: {exc}") from exc
    payload = raw if isinstance(raw, dict) else {}
    _validate_manifest(payload)
    return payload


def _regex_flags(flags: Any) -> int:
    if not isinstance(flags, list):
        return 0
    value = 0
    for token in flags:
        normalized = str(token or "").strip().upper()
        value |= _FLAG_BY_NAME.get(normalized, 0)
    return value


def _manifest_section(*path: str) -> Any:
    payload: Any = load_signal_manifest()
    for key in path:
        if not isinstance(payload, dict):
            return None
        payload = payload.get(key)
    return payload


@lru_cache(maxsize=64)
def get_signal_regex_pattern(section: str, key: str) -> re.Pattern[str] | None:
    spec = _manifest_section(section, "regex", key)
    if not isinstance(spec, dict):
        return None
    pattern = spec.get("pattern")
    if not isinstance(pattern, str) or not pattern:
        return None
    return re.compile(pattern, _regex_flags(spec.get("flags")))


@lru_cache(maxsize=64)
def get_signal_regex_replacements(section: str, key: str) -> tuple[tuple[re.Pattern[str], str], ...]:
    items = _manifest_section(section, "replacement_patterns", key)
    if not isinstance(items, list):
        return tuple()
    compiled: list[tuple[re.Pattern[str], str]] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        pattern = row.get("pattern")
        replacement = row.get("replacement")
        if not isinstance(pattern, str) or not pattern:
            continue
        if not isinstance(replacement, str):
            continue
        compiled.append((re.compile(pattern, _regex_flags(row.get("flags"))), replacement))
    return tuple(compiled)


@lru_cache(maxsize=64)
def get_signal_text_tokens(section: str, key: str) -> tuple[str, ...]:
    values = _manifest_section(section, "tokens", key)
    if not isinstance(values, list):
        return tuple()
    normalized: list[str] = []
    seen: set[str] = set()
    for item in values:
        token = str(item or "").strip()
        if not token:
            continue
        fold = token.casefold()
        if fold in seen:
            continue
        seen.add(fold)
        normalized.append(token)
    return tuple(normalized)


@lru_cache(maxsize=8)
def get_signal_char_map(section: str, key: str) -> dict[str, str]:
    payload = _manifest_section(section, key)
    if not isinstance(payload, dict):
        return {}
    result: dict[str, str] = {}
    for raw_key, raw_value in payload.items():
        char_key = str(raw_key or "")
        char_value = str(raw_value or "")
        if len(char_key) != 1 or len(char_value) != 1:
            continue
        result[char_key] = char_value
    return result


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
    "SignalManifestError",
    "get_booking_layout_swap_map",
    "get_booking_regex_pattern",
    "get_booking_regex_replacements",
    "get_booking_text_tokens",
    "get_info_regex_pattern",
    "get_signal_regex_pattern",
    "get_signal_regex_replacements",
    "get_signal_text_tokens",
    "load_signal_manifest",
]
