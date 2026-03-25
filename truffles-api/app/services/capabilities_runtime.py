from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.client_capability import ClientCapability
from app.schemas.capabilities import CapabilitiesPayload
from app.services.capabilities_service import merge_capabilities


@dataclass(frozen=True)
class RuntimeCapabilities:
    payload: CapabilitiesPayload
    client_id: UUID | None
    branch_id: UUID | None
    source: str
    has_records: bool
    has_tool_policy_records: bool = False


_RUNTIME_CAPABILITIES: ContextVar[RuntimeCapabilities | None] = ContextVar(
    "runtime_capabilities", default=None
)
_RUNTIME_CAPABILITIES_OVERRIDE: ContextVar[RuntimeCapabilities | None] = ContextVar(
    "runtime_capabilities_override", default=None
)


def _get_latest_capability(
    db: Session,
    *,
    client_id: UUID,
    scope: str,
    branch_id: UUID | None,
) -> ClientCapability | None:
    query = db.query(ClientCapability).filter(
        ClientCapability.client_id == client_id,
        ClientCapability.scope == scope,
    )
    if branch_id:
        query = query.filter(ClientCapability.branch_id == branch_id)
    else:
        query = query.filter(ClientCapability.branch_id.is_(None))
    return query.order_by(
        ClientCapability.updated_at.desc(),
        ClientCapability.created_at.desc(),
    ).first()


def set_runtime_capabilities(runtime_capabilities: RuntimeCapabilities | None):
    return _RUNTIME_CAPABILITIES.set(runtime_capabilities)


def get_runtime_capabilities() -> RuntimeCapabilities | None:
    return _RUNTIME_CAPABILITIES.get()


def set_runtime_capabilities_override(runtime_capabilities: RuntimeCapabilities | None):
    return _RUNTIME_CAPABILITIES_OVERRIDE.set(runtime_capabilities)


def get_runtime_capabilities_override() -> RuntimeCapabilities | None:
    return _RUNTIME_CAPABILITIES_OVERRIDE.get()


@contextmanager
def use_runtime_capabilities_override(runtime_capabilities: RuntimeCapabilities | None) -> Iterator[None]:
    override_token = set_runtime_capabilities_override(runtime_capabilities)
    runtime_token = set_runtime_capabilities(runtime_capabilities)
    try:
        yield
    finally:
        _RUNTIME_CAPABILITIES.reset(runtime_token)
        _RUNTIME_CAPABILITIES_OVERRIDE.reset(override_token)


def build_runtime_capabilities(
    db: Session,
    *,
    client_id: UUID | None,
    branch_id: UUID | None,
) -> RuntimeCapabilities:
    override_runtime = get_runtime_capabilities_override()
    if override_runtime is not None:
        if branch_id is None or override_runtime.branch_id is None or override_runtime.branch_id == branch_id:
            return override_runtime

    def _payload_has_tool_policy(payload: object) -> bool:
        return isinstance(payload, dict) and "tools" in payload

    if not client_id:
        return RuntimeCapabilities(
            payload=CapabilitiesPayload(),
            client_id=None,
            branch_id=branch_id,
            source="missing_client",
            has_records=False,
            has_tool_policy_records=False,
        )

    try:
        client_record = _get_latest_capability(
            db,
            client_id=client_id,
            scope="client",
            branch_id=None,
        )
        branch_record = (
            _get_latest_capability(
                db,
                client_id=client_id,
                scope="branch",
                branch_id=branch_id,
            )
            if branch_id
            else None
        )
    except Exception:
        return RuntimeCapabilities(
            payload=CapabilitiesPayload(),
            client_id=client_id,
            branch_id=branch_id,
            source="runtime_error",
            has_records=False,
            has_tool_policy_records=False,
        )

    client_payload = (
        client_record.payload_json
        if client_record and client_record.status == "active"
        else None
    )
    branch_payload = (
        branch_record.payload_json
        if branch_record and branch_record.status == "active"
        else None
    )
    has_records = bool(client_payload or branch_payload)
    has_tool_policy_records = bool(
        _payload_has_tool_policy(client_payload)
        or _payload_has_tool_policy(branch_payload)
    )

    merged = merge_capabilities(client_payload, branch_payload)
    try:
        payload = CapabilitiesPayload.model_validate(merged)
    except ValidationError:
        return RuntimeCapabilities(
            payload=CapabilitiesPayload(),
            client_id=client_id,
            branch_id=branch_id,
            source="invalid_payload",
            has_records=has_records,
            has_tool_policy_records=has_tool_policy_records,
        )

    return RuntimeCapabilities(
        payload=payload,
        client_id=client_id,
        branch_id=branch_id,
        source="client_capabilities" if has_records else "default",
        has_records=has_records,
        has_tool_policy_records=has_tool_policy_records,
    )


__all__ = [
    "RuntimeCapabilities",
    "build_runtime_capabilities",
    "get_runtime_capabilities",
    "get_runtime_capabilities_override",
    "set_runtime_capabilities",
    "set_runtime_capabilities_override",
    "use_runtime_capabilities_override",
]
