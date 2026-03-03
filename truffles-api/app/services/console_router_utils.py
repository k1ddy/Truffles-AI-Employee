import os
from urllib.parse import urlencode

from fastapi import Request


def request_with_query_params(request: Request, params: dict[str, object | None]) -> Request:
    scope = dict(request.scope)
    normalized: dict[str, str] = {}
    for key, value in params.items():
        if value is None:
            continue
        normalized[key] = str(value)
    scope["query_string"] = urlencode(normalized).encode("utf-8")
    return Request(scope, receive=request.receive)


def parse_env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def parse_env_csv_set(name: str, *, default: set[str]) -> set[str]:
    raw = os.getenv(name)
    if raw is None:
        return set(default)
    values = [item.strip() for item in raw.split(",")]
    return {value for value in values if value}


def parse_env_int(
    name: str,
    *,
    default: int,
    min_value: int,
    max_value: int,
) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw.strip())
    except (TypeError, ValueError):
        return default
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def dedupe_list(values: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique
