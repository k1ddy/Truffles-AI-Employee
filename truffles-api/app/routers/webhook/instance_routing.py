"""Helpers for safe branch resolution by incoming instance id."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Branch


@dataclass(frozen=True)
class BranchInstanceResolution:
    branch: Branch | None
    match_mode: str


def _decode_instance_payload(instance_id: str | None) -> dict[str, Any] | None:
    raw = (instance_id or "").strip()
    if not raw:
        return None
    padding = "=" * ((4 - len(raw) % 4) % 4)
    try:
        decoded = base64.b64decode(f"{raw}{padding}")
        payload = json.loads(decoded.decode("utf-8"))
    except Exception:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _instance_uid(instance_id: str | None) -> str | None:
    payload = _decode_instance_payload(instance_id)
    if not payload:
        return None
    uid = payload.get("uid")
    if isinstance(uid, str):
        uid = uid.strip()
        if uid:
            return uid
    return None


def resolve_active_branch_by_instance(
    db: Session,
    *,
    client_id: UUID,
    instance_id: str | None,
) -> BranchInstanceResolution:
    incoming = (instance_id or "").strip()
    if not incoming:
        return BranchInstanceResolution(branch=None, match_mode="missing_instance_id")

    exact = (
        db.query(Branch)
        .filter(
            Branch.client_id == client_id,
            Branch.instance_id == incoming,
            Branch.is_active.is_(True),
        )
        .first()
    )
    if exact:
        return BranchInstanceResolution(branch=exact, match_mode="exact")

    incoming_uid = _instance_uid(incoming)
    if not incoming_uid:
        return BranchInstanceResolution(branch=None, match_mode="unknown_instance_id")

    candidates = (
        db.query(Branch)
        .filter(
            Branch.client_id == client_id,
            Branch.is_active.is_(True),
            Branch.instance_id.isnot(None),
        )
        .all()
    )

    matches: list[Branch] = []
    for branch in candidates:
        if _instance_uid(getattr(branch, "instance_id", None)) == incoming_uid:
            matches.append(branch)

    if len(matches) == 1:
        return BranchInstanceResolution(branch=matches[0], match_mode="uid_alias")
    if len(matches) > 1:
        return BranchInstanceResolution(branch=None, match_mode="ambiguous_uid_alias")
    return BranchInstanceResolution(branch=None, match_mode="unknown_instance_id")


__all__ = ["BranchInstanceResolution", "resolve_active_branch_by_instance"]
