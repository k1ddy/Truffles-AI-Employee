from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker, RefResolver

_MATRIX_SCHEMA_RELATIVE = "contracts/policy/interaction_owner_matrix.v1.jsonschema"


class InteractionOwnerMatrixError(RuntimeError):
    pass


@dataclass(frozen=True)
class LoadedInteractionOwnerMatrix:
    schema_version: str
    matrix_id: str
    matrix_path: str
    matrix_signature: str
    matrix_fingerprint: str
    payload: dict[str, Any]
    row_by_id: dict[str, dict[str, Any]]


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        has_contracts = (parent / "contracts" / "policy").is_dir()
        has_repo_layout = (parent / "truffles-api" / "app").is_dir()
        has_container_layout = (parent / "app").is_dir()
        if has_contracts and (has_repo_layout or has_container_layout):
            return parent
    raise InteractionOwnerMatrixError(
        "Unable to locate repository root for interaction owner matrix service"
    )


def _matrix_path() -> Path:
    root = _repo_root()
    candidates = (
        root / "truffles-api" / "app" / "knowledge" / "generic" / "INTERACTION_OWNER_MATRIX.yaml",
        root / "app" / "knowledge" / "generic" / "INTERACTION_OWNER_MATRIX.yaml",
    )
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def _schema_path() -> Path:
    return _repo_root() / _MATRIX_SCHEMA_RELATIVE


@lru_cache(maxsize=1)
def _load_schema_validator() -> Draft202012Validator:
    path = _schema_path()
    schema = json.loads(path.read_text(encoding="utf-8"))
    resolver = RefResolver(base_uri=path.resolve().as_uri(), referrer=schema)
    return Draft202012Validator(schema, resolver=resolver, format_checker=FormatChecker())


def _validate_matrix(payload: dict[str, Any]) -> None:
    validator = _load_schema_validator()
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.path))
    if not errors:
        return
    messages: list[str] = []
    for err in errors:
        path = ".".join(str(part) for part in err.path) or "<root>"
        messages.append(f"{path}: {err.message}")
    raise InteractionOwnerMatrixError(
        "Interaction owner matrix schema validation failed: " + "; ".join(messages[:8])
    )


def _matrix_signature(path: Path) -> str:
    try:
        stat = path.stat()
    except FileNotFoundError as exc:
        raise InteractionOwnerMatrixError(f"Interaction owner matrix file not found: {path}") from exc
    return f"{stat.st_mtime_ns}:{stat.st_size}"


@lru_cache(maxsize=8)
def _load_matrix_cached(matrix_path: str, matrix_signature: str) -> LoadedInteractionOwnerMatrix:
    del matrix_signature
    path = Path(matrix_path)
    if not path.exists():
        raise InteractionOwnerMatrixError(f"Interaction owner matrix file not found: {path}")

    raw_bytes = path.read_bytes()
    matrix_fingerprint = hashlib.sha256(raw_bytes).hexdigest()
    try:
        raw_payload = yaml.safe_load(raw_bytes.decode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive parse guard
        raise InteractionOwnerMatrixError(f"Interaction owner matrix parse failed: {exc}") from exc

    payload = raw_payload if isinstance(raw_payload, dict) else {}
    _validate_matrix(payload)

    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    row_by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = row.get("row_id")
        if not isinstance(row_id, str) or not row_id.strip():
            continue
        row_by_id[row_id.strip()] = copy.deepcopy(row)

    return LoadedInteractionOwnerMatrix(
        schema_version=str(payload.get("schema_version") or "interaction_owner_matrix.v1"),
        matrix_id=str(payload.get("matrix_id") or "interaction_owner_matrix"),
        matrix_path=str(path),
        matrix_signature=_matrix_signature(path),
        matrix_fingerprint=matrix_fingerprint,
        payload=copy.deepcopy(payload),
        row_by_id=row_by_id,
    )


def load_interaction_owner_matrix() -> LoadedInteractionOwnerMatrix:
    path = _matrix_path()
    return _load_matrix_cached(str(path), _matrix_signature(path))


def get_interaction_owner_row(row_id: str) -> dict[str, Any] | None:
    token = str(row_id or "").strip()
    if not token:
        return None
    matrix = load_interaction_owner_matrix()
    row = matrix.row_by_id.get(token)
    return copy.deepcopy(row) if isinstance(row, dict) else None


__all__ = [
    "InteractionOwnerMatrixError",
    "LoadedInteractionOwnerMatrix",
    "get_interaction_owner_row",
    "load_interaction_owner_matrix",
]
