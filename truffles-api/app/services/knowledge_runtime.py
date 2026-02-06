from __future__ import annotations

import os
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.services.knowledge_registry_service import get_current_published
from app.services.pack_compiler_service import extract_compiled_artifacts


@dataclass(frozen=True)
class RuntimeTruth:
    truth: dict[str, Any]
    client_slug: str | None
    branch_id: UUID | None
    source: str
    version_id: str | None = None
    compiled_hash: str | None = None
    allow_fallback: bool = False


_RUNTIME_TRUTH: ContextVar[RuntimeTruth | None] = ContextVar("runtime_truth", default=None)


def _normalize_client_slug(client_slug: str | None) -> str | None:
    if client_slug is None:
        return None
    cleaned = str(client_slug).strip()
    return cleaned or None


def _is_env_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def should_allow_truth_fallback() -> bool:
    if _is_env_enabled(os.environ.get("KNOWLEDGE_RUNTIME_ALLOW_FALLBACK"), default=False):
        return True
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def set_runtime_truth(runtime_truth: RuntimeTruth | None) -> None:
    _RUNTIME_TRUTH.set(runtime_truth)


def get_runtime_truth() -> RuntimeTruth | None:
    return _RUNTIME_TRUTH.get()


def build_runtime_truth(
    db,
    *,
    client_slug: str | None,
    client_id: UUID | None,
    branch_id: UUID | None,
    allow_fallback: bool = False,
) -> RuntimeTruth:
    normalized_slug = _normalize_client_slug(client_slug)
    if not branch_id:
        return RuntimeTruth(
            truth={},
            client_slug=normalized_slug,
            branch_id=None,
            source="missing_branch",
            allow_fallback=allow_fallback,
        )

    try:
        version = get_current_published(db, branch_id=branch_id)
    except Exception:
        return RuntimeTruth(
            truth={},
            client_slug=normalized_slug,
            branch_id=branch_id,
            source="runtime_error",
            allow_fallback=allow_fallback,
        )

    if not version or not isinstance(getattr(version, "payload_json", None), dict):
        return RuntimeTruth(
            truth={},
            client_slug=normalized_slug,
            branch_id=branch_id,
            source="knowledge_not_published",
            allow_fallback=allow_fallback,
        )

    if client_id and getattr(version, "client_id", None) not in (None, client_id):
        return RuntimeTruth(
            truth={},
            client_slug=normalized_slug,
            branch_id=branch_id,
            source="client_mismatch",
            allow_fallback=allow_fallback,
        )

    compiled = extract_compiled_artifacts(version.payload_json, compile_if_missing=True)
    effective_pack = compiled.get("effective_pack") if isinstance(compiled, dict) else None
    if not isinstance(effective_pack, dict):
        return RuntimeTruth(
            truth={},
            client_slug=normalized_slug,
            branch_id=branch_id,
            source="effective_pack_missing",
            allow_fallback=allow_fallback,
        )

    return RuntimeTruth(
        truth=effective_pack,
        client_slug=normalized_slug,
        branch_id=branch_id,
        source="knowledge_versions",
        version_id=str(getattr(version, "id", None)) if getattr(version, "id", None) else None,
        compiled_hash=compiled.get("hash") if isinstance(compiled, dict) else None,
        allow_fallback=allow_fallback,
    )


__all__ = [
    "RuntimeTruth",
    "build_runtime_truth",
    "get_runtime_truth",
    "set_runtime_truth",
    "should_allow_truth_fallback",
]
