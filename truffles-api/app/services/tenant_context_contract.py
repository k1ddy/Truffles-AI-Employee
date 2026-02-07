from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

_TENANT_CONTEXT_SCHEMA_RELATIVE = Path("contracts/tenancy/tenant_context.v1.jsonschema")


def _resolve_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / _TENANT_CONTEXT_SCHEMA_RELATIVE
        if candidate.is_file():
            return parent
    raise FileNotFoundError(f"Unable to locate {_TENANT_CONTEXT_SCHEMA_RELATIVE}")


@lru_cache(maxsize=1)
def _load_tenant_context_schema() -> dict[str, Any]:
    schema_path = _resolve_repo_root() / _TENANT_CONTEXT_SCHEMA_RELATIVE
    return json.loads(schema_path.read_text(encoding="utf-8"))


@lru_cache(maxsize=2)
def _build_validator(require_client_id: bool) -> Draft202012Validator:
    schema = copy.deepcopy(_load_tenant_context_schema())
    if not require_client_id:
        schema["required"] = []
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _summarize_validation_error(exc, *, limit: int = 1) -> str:
    parts: list[str] = []
    for error in exc:
        path = ".".join(str(part) for part in error.path) if error.path else "$"
        parts.append(f"{path}: {error.message}")
        if len(parts) >= limit:
            break
    return "; ".join(parts) or "invalid_tenant_context"


def validate_tenant_context_contract(
    tenant_context: Mapping[str, Any] | None,
    *,
    require_client_id: bool = True,
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(tenant_context, Mapping):
        return None, "tenant_context_not_object"

    payload = dict(tenant_context)
    validator = _build_validator(require_client_id=require_client_id)
    errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.path))
    if errors:
        return None, _summarize_validation_error(errors)
    return payload, None


__all__ = ["validate_tenant_context_contract"]
