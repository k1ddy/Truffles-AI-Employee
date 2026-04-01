from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Iterator
from uuid import UUID

from app.services.knowledge_registry_service import get_active_knowledge_version
from app.services.pack_compiler_service import extract_compiled_artifacts
from app.services.runtime_mode_service import is_nonprod_eval_mode


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
_RUNTIME_TRUTH_OVERRIDE: ContextVar[RuntimeTruth | None] = ContextVar("runtime_truth_override", default=None)


def _normalize_client_slug(client_slug: str | None) -> str | None:
    if client_slug is None:
        return None
    cleaned = str(client_slug).strip()
    return cleaned or None


def _is_env_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _is_dev_or_test_runtime() -> bool:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    if is_nonprod_eval_mode(os.environ):
        return True
    if _is_env_enabled(os.environ.get("DEBUG"), default=False):
        return True
    return False


def should_allow_truth_fallback() -> bool:
    # Pytest keeps fallback enabled to avoid forcing DB setup in unit tests.
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    # Outside dev/test contexts we stay fail-closed: published pack only.
    if not _is_dev_or_test_runtime():
        return False
    return _is_env_enabled(os.environ.get("KNOWLEDGE_RUNTIME_ALLOW_FALLBACK"), default=False)


def set_runtime_truth(runtime_truth: RuntimeTruth | None):
    return _RUNTIME_TRUTH.set(runtime_truth)


def get_runtime_truth() -> RuntimeTruth | None:
    return _RUNTIME_TRUTH.get()


def set_runtime_truth_override(runtime_truth: RuntimeTruth | None):
    return _RUNTIME_TRUTH_OVERRIDE.set(runtime_truth)


def get_runtime_truth_override() -> RuntimeTruth | None:
    return _RUNTIME_TRUTH_OVERRIDE.get()


@contextmanager
def use_runtime_truth_override(runtime_truth: RuntimeTruth | None) -> Iterator[None]:
    override_token = set_runtime_truth_override(runtime_truth)
    runtime_token = set_runtime_truth(runtime_truth)
    try:
        yield
    finally:
        _RUNTIME_TRUTH.reset(runtime_token)
        _RUNTIME_TRUTH_OVERRIDE.reset(override_token)


def build_runtime_truth(
    db,
    *,
    client_slug: str | None,
    client_id: UUID | None,
    branch_id: UUID | None,
    allow_fallback: bool = False,
) -> RuntimeTruth:
    override_truth = get_runtime_truth_override()
    if override_truth is not None:
        if branch_id is None or override_truth.branch_id is None or override_truth.branch_id == branch_id:
            return override_truth

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
        version = get_active_knowledge_version(db, branch_id=branch_id)
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
            source="knowledge_not_active",
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
        source="knowledge_active_version",
        version_id=str(getattr(version, "id", None)) if getattr(version, "id", None) else None,
        compiled_hash=compiled.get("hash") if isinstance(compiled, dict) else None,
        allow_fallback=allow_fallback,
    )


def build_runtime_truth_from_payload(
    *,
    payload_json: dict[str, Any] | None,
    client_slug: str | None,
    branch_id: UUID | None,
    source: str,
    version_id: str | None = None,
    allow_fallback: bool = False,
) -> RuntimeTruth:
    normalized_slug = _normalize_client_slug(client_slug)
    if not isinstance(payload_json, dict):
        return RuntimeTruth(
            truth={},
            client_slug=normalized_slug,
            branch_id=branch_id,
            source="payload_missing",
            version_id=version_id,
            allow_fallback=allow_fallback,
        )

    compiled = extract_compiled_artifacts(payload_json, compile_if_missing=True)
    effective_pack = compiled.get("effective_pack") if isinstance(compiled, dict) else None
    if not isinstance(effective_pack, dict):
        return RuntimeTruth(
            truth={},
            client_slug=normalized_slug,
            branch_id=branch_id,
            source="effective_pack_missing",
            version_id=version_id,
            allow_fallback=allow_fallback,
        )

    return RuntimeTruth(
        truth=effective_pack,
        client_slug=normalized_slug,
        branch_id=branch_id,
        source=source,
        version_id=version_id,
        compiled_hash=compiled.get("hash") if isinstance(compiled, dict) else None,
        allow_fallback=allow_fallback,
    )


__all__ = [
    "RuntimeTruth",
    "build_runtime_truth",
    "build_runtime_truth_from_payload",
    "get_runtime_truth",
    "get_runtime_truth_override",
    "set_runtime_truth",
    "set_runtime_truth_override",
    "should_allow_truth_fallback",
    "use_runtime_truth_override",
]
