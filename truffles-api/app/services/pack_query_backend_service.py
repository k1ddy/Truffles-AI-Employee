"""Backend adapter for distributed pack-query retrieval.

The runtime layer uses this module as a thin driver contract.
No backend is enabled by default.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable

_RETRIEVAL_MODE_ENV = "PACK_QUERY_RETRIEVAL_MODE"
_BACKEND_DRIVER_ENV = "PACK_QUERY_BACKEND_DRIVER"
_DEFAULT_DRIVER = "noop"
_VALID_RETRIEVAL_MODES = ("runtime_local", "backend_shadow", "backend_primary")
_DEFAULT_ENGINE = "pack_query_backend.v1"
_DEFAULT_ENGINE_VERSION = "2026-03-03"
_DEFAULT_METHOD = "distributed_hybrid_rrf"

BackendDriver = Callable[..., dict[str, Any] | None]


@dataclass(frozen=True)
class PackQueryBackendCandidate:
    canonical_name: str
    score: float
    sparse_score: float = 0.0
    dense_score: float = 0.0
    rerank_bonus: float = 0.0
    matched_alias: str | None = None


@dataclass(frozen=True)
class PackQueryBackendLookup:
    available: bool
    candidates: list[PackQueryBackendCandidate]
    meta: dict[str, Any]
    unavailable_reason: str | None = None


_DRIVER_REGISTRY: dict[str, BackendDriver] = {}


def register_backend_driver(name: str, driver: BackendDriver) -> None:
    token = str(name or "").strip().lower()
    if not token:
        return
    _DRIVER_REGISTRY[token] = driver


def clear_backend_driver_registry() -> None:
    _DRIVER_REGISTRY.clear()


def _normalize_mode(value: str | None) -> str:
    token = str(value or "").strip().lower()
    if token in _VALID_RETRIEVAL_MODES:
        return token
    return "runtime_local"


def get_pack_query_retrieval_mode(explicit_mode: str | None = None) -> str:
    if isinstance(explicit_mode, str) and explicit_mode.strip():
        return _normalize_mode(explicit_mode)
    return _normalize_mode(os.environ.get(_RETRIEVAL_MODE_ENV))


def _resolve_driver_name(explicit_driver: str | None = None) -> str:
    token = str(explicit_driver or "").strip().lower()
    if token:
        return token
    env_token = str(os.environ.get(_BACKEND_DRIVER_ENV) or "").strip().lower()
    if env_token:
        return env_token
    return _DEFAULT_DRIVER


def _coerce_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip()
    return token or None


def _coerce_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def _coerce_candidate(value: Any) -> PackQueryBackendCandidate | None:
    if not isinstance(value, dict):
        return None
    canonical_name = _coerce_text(value.get("canonical_name"))
    if not canonical_name:
        return None
    return PackQueryBackendCandidate(
        canonical_name=canonical_name,
        score=_coerce_score(value.get("score")),
        sparse_score=_coerce_score(value.get("sparse_score")),
        dense_score=_coerce_score(value.get("dense_score")),
        rerank_bonus=_coerce_score(value.get("rerank_bonus")),
        matched_alias=_coerce_text(value.get("matched_alias")),
    )


def _default_meta(driver: str, mode: str) -> dict[str, Any]:
    return {
        "engine": _DEFAULT_ENGINE,
        "engine_version": _DEFAULT_ENGINE_VERSION,
        "method": _DEFAULT_METHOD,
        "driver": driver,
        "mode": mode,
    }


def resolve_backend_candidates(
    *,
    query_text: str,
    client_slug: str | None,
    branch_id: str | None = None,
    top_k: int = 8,
    explicit_mode: str | None = None,
    explicit_driver: str | None = None,
) -> PackQueryBackendLookup:
    mode = get_pack_query_retrieval_mode(explicit_mode)
    driver_name = _resolve_driver_name(explicit_driver)
    base_meta = _default_meta(driver_name, mode)
    if mode == "runtime_local":
        return PackQueryBackendLookup(
            available=False,
            candidates=[],
            meta=base_meta,
            unavailable_reason="runtime_local_mode",
        )
    driver = _DRIVER_REGISTRY.get(driver_name)
    if driver is None:
        return PackQueryBackendLookup(
            available=False,
            candidates=[],
            meta=base_meta,
            unavailable_reason="driver_not_registered",
        )
    try:
        payload = driver(
            query_text=query_text,
            client_slug=client_slug,
            branch_id=branch_id,
            top_k=max(int(top_k), 1),
        )
    except Exception as exc:  # pragma: no cover - backend exceptions are environment specific
        return PackQueryBackendLookup(
            available=False,
            candidates=[],
            meta=base_meta,
            unavailable_reason=f"driver_error:{exc.__class__.__name__}",
        )
    if not isinstance(payload, dict):
        return PackQueryBackendLookup(
            available=False,
            candidates=[],
            meta=base_meta,
            unavailable_reason="driver_payload_invalid",
        )

    merged_meta = dict(base_meta)
    external_meta = payload.get("meta")
    if isinstance(external_meta, dict):
        for key in ("engine", "engine_version", "method", "driver"):
            token = _coerce_text(external_meta.get(key))
            if token:
                merged_meta[key] = token
    candidates: list[PackQueryBackendCandidate] = []
    for row in payload.get("candidates") or []:
        candidate = _coerce_candidate(row)
        if candidate is None:
            continue
        candidates.append(candidate)

    unavailable_reason = _coerce_text(payload.get("unavailable_reason"))
    if not candidates and not unavailable_reason:
        unavailable_reason = "no_candidates"
    available = bool(candidates)
    return PackQueryBackendLookup(
        available=available,
        candidates=candidates,
        meta=merged_meta,
        unavailable_reason=unavailable_reason,
    )


__all__ = [
    "PackQueryBackendCandidate",
    "PackQueryBackendLookup",
    "clear_backend_driver_registry",
    "get_pack_query_retrieval_mode",
    "register_backend_driver",
    "resolve_backend_candidates",
]
