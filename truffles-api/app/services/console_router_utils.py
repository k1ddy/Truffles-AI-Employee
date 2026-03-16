import os
from collections.abc import Callable
from urllib.parse import urlencode
from uuid import UUID

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


def reject_unknown_query_params(
    request: Request,
    allowed: set[str],
    *,
    error_factory: Callable[[str], Exception],
) -> None:
    unknown = sorted(set(request.query_params.keys()) - allowed)
    if not unknown:
        return
    raise error_factory(f"Unknown query parameter(s): {', '.join(unknown)}")


def validate_limit(
    limit: int | object,
    *,
    error_factory: Callable[[str], Exception],
    min_value: int = 1,
    max_value: int = 100,
) -> int:
    raw_limit = getattr(limit, "default", limit)
    try:
        normalized_limit = int(raw_limit)
    except (TypeError, ValueError) as exc:
        raise error_factory(f"limit must be between {min_value} and {max_value}") from exc

    if min_value <= normalized_limit <= max_value:
        return normalized_limit
    raise error_factory(f"limit must be between {min_value} and {max_value}")


def parse_uuid_param(
    name: str,
    value: str | None,
    *,
    error_factory: Callable[[str], Exception],
) -> UUID | None:
    if value is None:
        return None
    if value == "":
        raise error_factory(f"Invalid {name}")
    try:
        return UUID(value)
    except ValueError as exc:
        raise error_factory(f"Invalid {name}") from exc


def parse_bool_param(
    name: str,
    value: str | None,
    *,
    error_factory: Callable[[str], Exception],
    default: bool = False,
) -> bool:
    if value is None:
        return default
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise error_factory(f"Invalid {name}")
