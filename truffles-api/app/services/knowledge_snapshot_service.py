from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from app.models import Branch, KnowledgeVersion
from app.schemas.outbox_payload import TenantContext
from app.services.knowledge_registry_service import (
    build_pack_index,
    build_pack_index_meta,
    get_current_published,
)


def _serialize_for_hash(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _hash_packs(packs: dict[str, Any]) -> str:
    return hashlib.sha256(_serialize_for_hash(packs).encode("utf-8")).hexdigest()


def _build_signature(sha256_value: str) -> dict[str, Any] | None:
    secret = os.environ.get("KNOWLEDGE_SNAPSHOT_HMAC_KEY")
    if not secret:
        return None
    key_id = os.environ.get("KNOWLEDGE_SNAPSHOT_KEY_ID")
    created_at = datetime.now(timezone.utc).isoformat()
    value = hmac.new(secret.encode("utf-8"), sha256_value.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "algorithm": "hmac-sha256",
        "value": value,
        "key_id": key_id,
        "created_at": created_at,
    }


def _coerce_uuid(value: str | UUID | None) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return UUID(value)
        except ValueError:
            return None
    return None


def _coerce_payload(payload_json: dict | None) -> dict | None:
    if not isinstance(payload_json, dict):
        return None
    if isinstance(payload_json.get("client_pack"), dict):
        return payload_json
    return {"client_pack": payload_json}


def _extract_packs(payload_json: dict) -> dict[str, Any]:
    client_pack = payload_json.get("client_pack") if isinstance(payload_json, dict) else None
    packs: dict[str, Any] = {"client_pack": client_pack or {}}
    consult_playbook = payload_json.get("consult_playbook")
    if isinstance(consult_playbook, dict):
        packs["consult_playbook"] = consult_playbook
    service_catalog = None
    if isinstance(client_pack, dict):
        service_catalog = client_pack.get("services_catalog")
    if isinstance(service_catalog, dict):
        packs["service_catalog"] = service_catalog
    faq = payload_json.get("faq")
    if not isinstance(faq, list) and isinstance(client_pack, dict):
        faq = client_pack.get("faq")
    if isinstance(faq, list):
        packs["faq"] = faq
    pack_index = build_pack_index(payload_json)
    if isinstance(pack_index, dict):
        packs["pack_index"] = pack_index
    return packs


def _build_tenant_context(
    tenant_context: TenantContext,
    *,
    client_slug: str | None,
    branch_slug: str | None,
    instance_id: str | None,
) -> dict[str, Any]:
    context = tenant_context.model_dump(exclude_none=True)
    if client_slug and not context.get("client_slug"):
        context["client_slug"] = client_slug
    if branch_slug and not context.get("branch_slug"):
        context["branch_slug"] = branch_slug
    if instance_id and not context.get("instance_id"):
        context["instance_id"] = instance_id
    context.setdefault("source", "knowledge_gateway")
    return context


def build_knowledge_snapshot(
    db,
    *,
    tenant_context: TenantContext,
    version_id: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    if not tenant_context or not tenant_context.client_id:
        return None, "missing_client_id"
    if not tenant_context.branch_id:
        return None, "missing_branch_id"

    client_id = _coerce_uuid(tenant_context.client_id)
    branch_id = _coerce_uuid(tenant_context.branch_id)
    if not client_id:
        return None, "invalid_client_id"
    if not branch_id:
        return None, "invalid_branch_id"

    branch = (
        db.query(Branch)
        .filter(Branch.id == branch_id, Branch.client_id == client_id)
        .first()
    )
    if not branch:
        return None, "branch_not_found"

    version = None
    if version_id:
        version_uuid = _coerce_uuid(version_id)
        if not version_uuid:
            return None, "invalid_version_id"
        version = (
            db.query(KnowledgeVersion)
            .filter(
                KnowledgeVersion.id == version_uuid,
                KnowledgeVersion.branch_id == branch_id,
                KnowledgeVersion.status == "published",
            )
            .first()
        )
    else:
        version = get_current_published(db, branch_id=branch_id)

    if not version:
        return None, "version_not_found"

    payload_json = _coerce_payload(version.payload_json)
    if not payload_json:
        return None, "invalid_payload"

    packs = _extract_packs(payload_json)
    sha256_value = _hash_packs(packs)

    now = datetime.now(timezone.utc)
    ttl_seconds = int(os.environ.get("KNOWLEDGE_SNAPSHOT_TTL_SECONDS", "0"))
    expires_at = None
    if ttl_seconds > 0:
        expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()

    signature = _build_signature(sha256_value)
    tenant_context_payload = _build_tenant_context(
        tenant_context,
        client_slug=branch.client.name if branch.client else None,
        branch_slug=branch.slug,
        instance_id=branch.instance_id,
    )

    pack_index_meta = None
    pack_index = packs.get("pack_index") if isinstance(packs, dict) else None
    if isinstance(pack_index, dict):
        compiled_at = version.published_at or version.created_at or now
        pack_index_meta = build_pack_index_meta(
            pack_index,
            version_id=version.id,
            compiled_at=compiled_at,
            source="knowledge_snapshot",
        )

    extensions = {"source": "knowledge_versions"}
    if pack_index_meta:
        extensions["pack_index"] = pack_index_meta

    snapshot = {
        "snapshot_id": str(uuid4()),
        "tenant_context": tenant_context_payload,
        "version_id": str(version.id),
        "schema_version": "knowledge_snapshot.v1",
        "created_at": now.isoformat(),
        "expires_at": expires_at,
        "sha256": sha256_value,
        "packs": packs,
        "signature": signature,
        "extensions": extensions,
    }
    return snapshot, None
