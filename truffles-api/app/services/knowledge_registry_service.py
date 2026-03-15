from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx

from app.logging_config import get_logger
from app.models import Branch, Client, KnowledgeVersion
from app.services.audit_service import record_audit_event
from app.services.knowledge_service import QDRANT_API_KEY, QDRANT_COLLECTION, QDRANT_HOST, get_embedding
from app.services.knowledge_validation import (
    LOSSY_STRUCTURED_REWRITE_ERROR_PREFIX,
    build_diff,
    build_payload_checksum,
    build_summary,
    dump_pack_yaml,
    get_lossy_structured_rewrite_paths,
    parse_draft_text,
    strip_compiled_artifacts,
    validate_payload,
)
from app.services.outbox_service import enqueue_outbox_message
from app.services.pack_compiler_service import (
    PackCompilerError,
    build_compiled_pack_meta,
    compile_pack_payload,
    extract_compiled_artifacts,
    inject_compiled_artifacts,
    parse_compiled_at,
)

logger = get_logger("knowledge_registry")

SERVICES_COLLECTION = "services_index"
PACK_INDEX_SCHEMA_VERSION = "pack_index.v1"
KNOWLEDGE_SYNC_STATUS_PENDING = "pending"
KNOWLEDGE_SYNC_STATUS_READY = "ready"
KNOWLEDGE_SYNC_STATUS_FAILED = "failed"
OUTBOX_EVENT_KNOWLEDGE_SYNC = "knowledge.sync"


def _coerce_string_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        items = value
    elif isinstance(value, tuple):
        items = list(value)
    elif isinstance(value, str):
        items = [value]
    else:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, str):
            item = str(item)
        cleaned = item.strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
    return normalized


def _normalize_lang_map(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, list[str]] = {}
    for lang_key, items in value.items():
        if not isinstance(lang_key, str):
            continue
        cleaned_key = lang_key.strip().casefold()
        if not cleaned_key:
            continue
        normalized_items = _coerce_string_list(items)
        if normalized_items:
            normalized[cleaned_key] = normalized_items
    return normalized


def _flatten_lang_map(value: Any) -> list[str]:
    if isinstance(value, dict):
        merged: list[str] = []
        for items in value.values():
            merged.extend(_coerce_string_list(items))
        return _coerce_string_list(merged)
    return _coerce_string_list(value)


def _extract_domain_pack(payload_json: dict) -> dict[str, Any]:
    if not isinstance(payload_json, dict):
        return {}
    domain_pack = payload_json.get("domain_pack")
    if isinstance(domain_pack, dict):
        return domain_pack
    client_pack = payload_json.get("client_pack")
    if isinstance(client_pack, dict) and isinstance(client_pack.get("domain_pack"), dict):
        return client_pack["domain_pack"]
    return {}


def _hash_pack_index(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_pack_index(payload_json: dict) -> dict[str, Any] | None:
    domain_pack = _extract_domain_pack(payload_json)
    if not domain_pack:
        return None

    anchors: dict[str, list[str]] = {}
    ood_anchors = domain_pack.get("ood_anchors")
    if isinstance(ood_anchors, dict):
        in_domain = _flatten_lang_map(ood_anchors.get("in_domain"))
        out_domain = _flatten_lang_map(ood_anchors.get("out_of_domain"))
        strict_in = _flatten_lang_map(ood_anchors.get("strict_in"))
        if in_domain:
            anchors["in_domain"] = in_domain
        if out_domain:
            anchors["out_of_domain"] = out_domain
        if strict_in:
            anchors["strict_in"] = strict_in

    lexicons: dict[str, dict[str, list[str]]] = {}
    for key, label in (
        ("guest_policy_lexicon", "guest_policy"),
        ("service_request_lexicon", "service_request"),
        ("services_overview_lexicon", "services_overview"),
        ("datetime_lexicon", "datetime"),
    ):
        normalized = _normalize_lang_map(domain_pack.get(key))
        if normalized:
            lexicons[label] = normalized

    index_payload: dict[str, Any] = {"schema_version": PACK_INDEX_SCHEMA_VERSION}
    if anchors:
        index_payload["anchors"] = anchors
    if lexicons:
        index_payload["lexicons"] = lexicons
    if len(index_payload) == 1:
        return None

    index_hash = _hash_pack_index(index_payload)
    index_payload["hash"] = index_hash
    return index_payload


def build_pack_index_meta(
    pack_index: dict[str, Any],
    *,
    version_id: UUID | None,
    compiled_at: datetime,
    source: str,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "schema_version": pack_index.get("schema_version"),
        "hash": pack_index.get("hash"),
        "version_id": str(version_id) if version_id else None,
        "compiled_at": compiled_at.isoformat(),
        "source": source,
    }
    return {key: value for key, value in meta.items() if value is not None}


def apply_pack_index_to_client_config(
    client: Client,
    *,
    pack_index: dict[str, Any],
    version_id: UUID | None,
    compiled_at: datetime,
    source: str,
    compiled_meta: dict[str, Any] | None = None,
) -> bool:
    if not isinstance(pack_index, dict):
        return False
    anchors = pack_index.get("anchors")
    if not isinstance(anchors, dict):
        anchors = {}

    config = dict(client.config or {})
    domain_router = dict(config.get("domain_router") or {})
    updated = False
    anchors_in = anchors.get("in_domain")
    anchors_out = anchors.get("out_of_domain")
    strict_in = anchors.get("strict_in")

    if anchors_in:
        domain_router["anchors_in"] = anchors_in
        updated = True
    if anchors_out:
        domain_router["anchors_out"] = anchors_out
        updated = True
    if strict_in:
        domain_router["strict_in_anchors"] = strict_in
        updated = True
    if updated:
        config["domain_router"] = domain_router

    config["pack_index"] = build_pack_index_meta(
        pack_index,
        version_id=version_id,
        compiled_at=compiled_at,
        source=source,
    )
    if compiled_meta:
        config["compiled_pack"] = compiled_meta
    client.config = config
    return True


def get_current_published(
    db,
    *,
    branch_id: UUID,
) -> KnowledgeVersion | None:
    return (
        db.query(KnowledgeVersion)
        .filter(
            KnowledgeVersion.branch_id == branch_id,
            KnowledgeVersion.status == "published",
        )
        .order_by(KnowledgeVersion.published_at.desc().nullslast(), KnowledgeVersion.created_at.desc())
        .first()
    )


def get_latest_draft(
    db,
    *,
    branch_id: UUID,
) -> KnowledgeVersion | None:
    return (
        db.query(KnowledgeVersion)
        .filter(
            KnowledgeVersion.branch_id == branch_id,
            KnowledgeVersion.status == "draft",
        )
        .order_by(KnowledgeVersion.created_at.desc())
        .first()
    )


def list_history(
    db,
    *,
    branch_id: UUID,
    limit: int = 50,
) -> list[KnowledgeVersion]:
    return (
        db.query(KnowledgeVersion)
        .filter(
            KnowledgeVersion.branch_id == branch_id,
            KnowledgeVersion.status.in_(["published", "archived"]),
        )
        .order_by(KnowledgeVersion.created_at.desc())
        .limit(limit)
        .all()
    )


def upsert_draft(
    db,
    *,
    branch_id: UUID,
    client_id: UUID,
    payload_json: dict,
    actor_id: UUID | None,
) -> KnowledgeVersion:
    draft = (
        get_latest_draft(
            db,
            branch_id=branch_id,
        )
    )
    now = datetime.now(timezone.utc)
    if draft:
        draft.payload_json = payload_json
        draft.checksum = build_payload_checksum(payload_json)
        draft.summary = build_summary(payload_json)
        draft.created_by = actor_id
        draft.created_at = now
        return draft

    draft = KnowledgeVersion(
        branch_id=branch_id,
        client_id=client_id,
        status="draft",
        payload_json=payload_json,
        checksum=build_payload_checksum(payload_json),
        summary=build_summary(payload_json),
        created_by=actor_id,
        created_at=now,
    )
    db.add(draft)
    return draft


def publish_version(
    db,
    *,
    branch: Branch,
    payload_json: dict,
    actor_id: UUID | None,
    source_version_id: UUID | None,
) -> KnowledgeVersion:
    now = datetime.now(timezone.utc)
    payload_clean = strip_compiled_artifacts(payload_json)
    current = get_current_published(db, branch_id=branch.id)
    current_payload = (
        strip_compiled_artifacts(current.payload_json)
        if current and isinstance(current.payload_json, dict)
        else None
    )
    blocked_paths = get_lossy_structured_rewrite_paths(
        payload_clean,
        previous_payload=current_payload,
    )
    if blocked_paths:
        raise PackCompilerError(
            "Pack compiler blocked lossy structured rewrite",
            errors=[
                f"{LOSSY_STRUCTURED_REWRITE_ERROR_PREFIX}{path}"
                for path in blocked_paths
            ],
        )
    try:
        compiled = compile_pack_payload(payload_clean, compiled_at=now)
    except PackCompilerError:
        raise
    payload_json = inject_compiled_artifacts(payload_clean, compiled)
    pack_yaml = dump_pack_yaml(payload_json)
    checksum = build_payload_checksum(payload_json)

    if current:
        current.status = "archived"

    version = KnowledgeVersion(
        branch_id=branch.id,
        client_id=branch.client_id,
        status="published",
        payload_json=payload_json,
        pack_yaml=pack_yaml,
        checksum=checksum,
        summary=build_summary(payload_json),
        source_version_id=source_version_id,
        created_by=actor_id,
        created_at=now,
        published_by=actor_id,
        published_at=now,
        sync_status=KNOWLEDGE_SYNC_STATUS_PENDING,
        sync_error=None,
        sync_completed_at=None,
    )
    db.add(version)
    return version


def mark_knowledge_version_sync_pending(version: KnowledgeVersion) -> None:
    version.sync_status = KNOWLEDGE_SYNC_STATUS_PENDING
    version.sync_error = None
    version.sync_completed_at = None


def mark_knowledge_version_sync_ready(
    version: KnowledgeVersion,
    *,
    completed_at: datetime,
) -> None:
    version.sync_status = KNOWLEDGE_SYNC_STATUS_READY
    version.sync_error = None
    version.sync_completed_at = completed_at


def mark_knowledge_version_sync_failed(
    version: KnowledgeVersion,
    *,
    error_message: str,
    completed_at: datetime,
) -> None:
    version.sync_status = KNOWLEDGE_SYNC_STATUS_FAILED
    version.sync_error = error_message
    version.sync_completed_at = completed_at


def normalize_knowledge_sync_status(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == KNOWLEDGE_SYNC_STATUS_READY:
        return KNOWLEDGE_SYNC_STATUS_READY
    if normalized == KNOWLEDGE_SYNC_STATUS_FAILED:
        return KNOWLEDGE_SYNC_STATUS_FAILED
    return KNOWLEDGE_SYNC_STATUS_PENDING


def knowledge_sync_status_label(value: Any) -> str:
    normalized = normalize_knowledge_sync_status(value)
    if normalized == KNOWLEDGE_SYNC_STATUS_READY:
        return "Синхронизировано"
    if normalized == KNOWLEDGE_SYNC_STATUS_FAILED:
        return "Синхронизация требует внимания"
    return "Синхронизация выполняется"


def enqueue_knowledge_sync_event(
    db,
    *,
    client: Client,
    branch: Branch,
    version: KnowledgeVersion,
    actor_id: UUID | None,
    actor_name: str | None,
    source: str,
) -> bool:
    payload_json = {
        "schema_version": "outbox.v1",
        "event_type": OUTBOX_EVENT_KNOWLEDGE_SYNC,
        "provider": "internal",
        "channel": "knowledge",
        "client_id": str(client.id),
        "branch_id": str(branch.id),
        "payload": {
            "client_id": str(client.id),
            "branch_id": str(branch.id),
            "version_id": str(version.id),
            "source": source,
            "actor_id": str(actor_id) if actor_id else None,
            "actor_name": actor_name,
        },
    }
    return enqueue_outbox_message(
        db,
        client_id=client.id,
        conversation_id=None,
        branch_id=branch.id,
        inbound_message_id=f"knowledge:sync:{version.id}:{uuid4()}",
        payload_json=payload_json,
    )


def _parse_event_uuid(value: Any) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            return None
    return None


def process_knowledge_sync_event(
    db,
    *,
    payload_json: dict[str, Any] | None,
) -> tuple[bool, str | None]:
    payload = payload_json.get("payload") if isinstance(payload_json, dict) else None
    if not isinstance(payload, dict):
        return False, "missing_payload"

    client_id = _parse_event_uuid(payload.get("client_id"))
    branch_id = _parse_event_uuid(payload.get("branch_id"))
    version_id = _parse_event_uuid(payload.get("version_id"))
    source = str(payload.get("source") or "knowledge_sync")
    actor_id = _parse_event_uuid(payload.get("actor_id"))
    actor_name = payload.get("actor_name") if isinstance(payload.get("actor_name"), str) else None
    if not client_id or not branch_id or not version_id:
        return False, "missing_fields"

    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        return False, "client_not_found"
    branch = (
        db.query(Branch)
        .filter(
            Branch.id == branch_id,
            Branch.client_id == client_id,
        )
        .first()
    )
    if branch is None:
        return False, "branch_not_found"
    version = (
        db.query(KnowledgeVersion)
        .filter(
            KnowledgeVersion.id == version_id,
            KnowledgeVersion.client_id == client_id,
        )
        .first()
    )
    if version is None:
        return False, "version_not_found"
    if version.branch_id != branch.id:
        return False, "branch_mismatch"
    if version.status != "published":
        return False, "version_not_published"

    if normalize_knowledge_sync_status(version.sync_status) == KNOWLEDGE_SYNC_STATUS_READY and not bool(
        getattr(branch, "knowledge_safe_mode", False)
    ):
        return True, None

    now = datetime.now(timezone.utc)
    try:
        sync_published_branch_docs(
            db,
            client_slug=client.name,
            branch=branch,
            version=version,
            backfill_other_branches=False,
        )
        compiled = extract_compiled_artifacts(version.payload_json, compile_if_missing=False)
        pack_index = compiled.get("pack_index") if isinstance(compiled, dict) else None
        if pack_index:
            compiled_at = parse_compiled_at(compiled.get("compiled_at") if isinstance(compiled, dict) else None)
            apply_pack_index_to_client_config(
                client,
                pack_index=pack_index,
                version_id=version.id,
                compiled_at=compiled_at or now,
                source=source,
                compiled_meta=build_compiled_pack_meta(
                    compiled,
                    version_id=version.id,
                    source=source,
                )
                if isinstance(compiled, dict)
                else None,
            )
        mark_knowledge_version_sync_ready(version, completed_at=now)
        branch.knowledge_safe_mode = False
        branch.knowledge_safe_mode_reason = None
        branch.knowledge_safe_mode_at = now
        record_audit_event(
            db,
            actor=None,
            event_type="knowledge_sync_completed",
            entity_type="branch",
            entity_id=branch.id,
            payload={
                "version_id": str(version.id),
                "source": source,
            },
            client_id=client.id,
            branch_id=branch.id,
            actor_id=actor_id,
            actor_name=actor_name,
        )
        db.commit()
        return True, None
    except Exception as exc:
        db.rollback()
        logger.warning(
            "Knowledge sync event failed",
            extra={
                "context": {
                    "client_id": str(client_id),
                    "branch_id": str(branch_id),
                    "version_id": str(version_id),
                    "source": source,
                    "error": str(exc),
                }
            },
        )
        branch = (
            db.query(Branch)
            .filter(
                Branch.id == branch_id,
                Branch.client_id == client_id,
            )
            .first()
        )
        version = (
            db.query(KnowledgeVersion)
            .filter(
                KnowledgeVersion.id == version_id,
                KnowledgeVersion.client_id == client_id,
            )
            .first()
        )
        if branch is not None and version is not None:
            error_message = str(exc)
            mark_knowledge_version_sync_failed(
                version,
                error_message=error_message,
                completed_at=now,
            )
            branch.knowledge_safe_mode = True
            branch.knowledge_safe_mode_reason = error_message
            branch.knowledge_safe_mode_at = now
            record_audit_event(
                db,
                actor=None,
                event_type="knowledge_sync_failed",
                entity_type="branch",
                entity_id=branch.id,
                payload={
                    "version_id": str(version.id),
                    "source": source,
                    "error": error_message,
                },
                client_id=client_id,
                branch_id=branch.id,
                actor_id=actor_id,
                actor_name=actor_name,
            )
            db.commit()
        return False, str(exc)


def restore_version(
    db,
    *,
    branch: Branch,
    source_version: KnowledgeVersion,
    actor_id: UUID | None,
) -> KnowledgeVersion:
    return publish_version(
        db,
        branch=branch,
        payload_json=source_version.payload_json,
        actor_id=actor_id,
        source_version_id=source_version.id,
    )


def validate_draft(
    draft_text: str,
    *,
    current_payload: dict | None,
    domain_slug: str | None = None,
    require_booking: bool | None = None,
) -> tuple[dict | None, list[str], list[str], str]:
    payload, parse_errors = parse_draft_text(draft_text)
    if parse_errors:
        return None, parse_errors, [], ""
    errors, warnings = validate_payload(
        payload,
        previous_payload=current_payload,
        domain_slug=domain_slug,
        require_booking=require_booking,
    )
    diff = build_diff(current_payload, payload)
    return payload, errors, warnings, diff


def sync_qdrant_from_pack(
    payload_json: dict,
    *,
    client_slug: str,
    branch_id: UUID | None,
    knowledge_tag: str | None,
    version_id: UUID,
) -> tuple[int, int]:
    pack_text = dump_pack_yaml(payload_json)
    if not pack_text:
        return 0, 0
    chunks = _split_into_chunks(
        pack_text,
        doc_name="client_pack",
        doc_id=str(version_id),
        client_slug=client_slug,
        branch_id=str(branch_id) if branch_id else None,
        knowledge_tag=knowledge_tag,
    )
    if not chunks:
        return 0, 0

    points = []
    for idx, chunk in enumerate(chunks):
        vector = get_embedding(chunk["content"], client_slug=client_slug)
        point_id = hashlib.md5(f"{version_id}:{idx}".encode("utf-8")).hexdigest()
        points.append(
            {
                "id": point_id,
                "vector": vector,
                "payload": chunk,
            }
        )

    _delete_client_docs(client_slug, branch_id=branch_id, knowledge_tag=knowledge_tag)
    _upsert_points(QDRANT_COLLECTION, points)

    services_count = sync_services_index(payload_json, client_slug=client_slug)
    return len(points), services_count


def _list_client_backfill_branches(
    db,
    *,
    client_id: UUID,
    exclude_branch_id: UUID | None,
) -> list[Branch]:
    query = db.query(Branch).filter(Branch.client_id == client_id)
    if exclude_branch_id:
        query = query.filter(Branch.id != exclude_branch_id)
    return query.order_by(Branch.created_at.asc()).all()


def backfill_client_published_branches(
    db,
    *,
    client_slug: str,
    client_id: UUID,
    exclude_branch_id: UUID | None,
) -> tuple[int, int]:
    synced = 0
    skipped = 0
    for branch in _list_client_backfill_branches(
        db,
        client_id=client_id,
        exclude_branch_id=exclude_branch_id,
    ):
        published = get_current_published(db, branch_id=branch.id)
        if not published:
            skipped += 1
            continue
        sync_qdrant_from_pack(
            published.payload_json,
            client_slug=client_slug,
            branch_id=branch.id,
            knowledge_tag=branch.knowledge_tag,
            version_id=published.id,
        )
        synced += 1
    return synced, skipped


def sync_published_branch_docs(
    db,
    *,
    client_slug: str,
    branch: Branch,
    version: KnowledgeVersion,
    backfill_other_branches: bool = True,
) -> dict[str, int]:
    docs_synced, services_synced = sync_qdrant_from_pack(
        version.payload_json,
        client_slug=client_slug,
        branch_id=branch.id,
        knowledge_tag=branch.knowledge_tag,
        version_id=version.id,
    )
    backfill_synced = 0
    backfill_skipped = 0
    if backfill_other_branches:
        backfill_synced, backfill_skipped = backfill_client_published_branches(
            db,
            client_slug=client_slug,
            client_id=branch.client_id,
            exclude_branch_id=branch.id,
        )
    return {
        "docs_synced": docs_synced,
        "services_synced": services_synced,
        "backfill_synced": backfill_synced,
        "backfill_skipped": backfill_skipped,
    }


def sync_services_index(payload_json: dict, *, client_slug: str) -> int:
    entries = _collect_service_entries(payload_json)
    if not entries:
        return 0

    first_vector = get_embedding(entries[0]["canonical_name"], client_slug=client_slug)
    vector_size = len(first_vector) if isinstance(first_vector, list) else 0
    if vector_size <= 0:
        raise RuntimeError("services_index embedding failed")

    _ensure_qdrant_collection(SERVICES_COLLECTION, vector_size)
    _delete_services(client_slug)

    points = []
    for idx, entry in enumerate(entries):
        name = entry["canonical_name"]
        vector = first_vector if idx == 0 else get_embedding(name, client_slug=client_slug)
        point_id_source = f"{client_slug}:{entry.get('entry_type')}:{name}:{entry.get('category') or ''}"
        point_id = hashlib.md5(point_id_source.encode("utf-8")).hexdigest()
        payload = {
            "client_slug": client_slug,
            "canonical_name": name,
            "category": entry.get("category"),
            "price_item": entry.get("price_item"),
        }
        entry_type = entry.get("entry_type")
        if entry_type:
            payload["entry_type"] = entry_type
        points.append({"id": point_id, "vector": vector, "payload": payload})

    _upsert_points(SERVICES_COLLECTION, points)
    return len(points)


def _ensure_qdrant_collection(collection: str, vector_size: int) -> None:
    headers = {"api-key": QDRANT_API_KEY} if QDRANT_API_KEY else None
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(f"{QDRANT_HOST}/collections/{collection}", headers=headers)
        if resp.status_code == 200:
            return
        if resp.status_code != 404:
            raise RuntimeError(f"Qdrant collection check failed: {resp.status_code} {resp.text}")
        create = client.put(
            f"{QDRANT_HOST}/collections/{collection}",
            headers=headers,
            json={"vectors": {"size": vector_size, "distance": "Cosine"}},
        )
        if create.status_code not in {200, 201}:
            raise RuntimeError(f"Qdrant create collection failed: {create.status_code} {create.text}")


def _upsert_points(collection: str, points: list[dict]) -> None:
    if not points:
        return
    headers = {"api-key": QDRANT_API_KEY} if QDRANT_API_KEY else None
    with httpx.Client(timeout=60.0) as client:
        response = client.put(
            f"{QDRANT_HOST}/collections/{collection}/points",
            headers=headers,
            json={"points": points},
        )
        if response.status_code not in {200, 201}:
            raise RuntimeError(f"Qdrant upsert error: {response.status_code} {response.text}")


def _delete_client_docs(
    client_slug: str,
    *,
    branch_id: UUID | None,
    knowledge_tag: str | None,
) -> None:
    headers = {"api-key": QDRANT_API_KEY} if QDRANT_API_KEY else None
    must = [{"key": "metadata.client_slug", "match": {"value": client_slug}}]
    if knowledge_tag:
        must.append({"key": "metadata.knowledge_tag", "match": {"value": knowledge_tag}})
    if branch_id:
        must.append({"key": "metadata.branch_id", "match": {"value": str(branch_id)}})
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{QDRANT_HOST}/collections/{QDRANT_COLLECTION}/points/delete",
            headers=headers,
            json={"filter": {"must": must}},
        )
    if response.status_code not in {200, 202}:
        logger.warning(
            "Qdrant delete failed",
            extra={"context": {"status_code": response.status_code, "body": response.text}},
        )


def _delete_services(client_slug: str) -> None:
    headers = {"api-key": QDRANT_API_KEY} if QDRANT_API_KEY else None
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{QDRANT_HOST}/collections/{SERVICES_COLLECTION}/points/delete",
            headers=headers,
            json={"filter": {"must": [{"key": "client_slug", "match": {"value": client_slug}}]}},
        )
    if response.status_code not in {200, 202}:
        logger.warning(
            "services_index delete failed",
            extra={"context": {"status_code": response.status_code, "body": response.text}},
        )


def _split_into_chunks(
    text: str,
    *,
    doc_name: str,
    doc_id: str,
    client_slug: str,
    branch_id: str | None,
    knowledge_tag: str | None,
) -> list[dict]:
    import re

    max_chunk_chars = int(os.environ.get("QDRANT_CHUNK_CHARS", "2000"))
    min_chunk_chars = 50

    def _append_chunks(section_text: str, *, section_index: int, section_title: str) -> list[dict]:
        section_text = section_text.strip()
        if len(section_text) < min_chunk_chars:
            return []

        if len(section_text) <= max_chunk_chars:
            return [section_text]

        parts = [part.strip() for part in re.split(r"\n\\s*\\n", section_text) if part.strip()]
        assembled: list[str] = []
        buffer = ""
        for part in parts:
            candidate = f"{buffer}\\n\\n{part}" if buffer else part
            if len(candidate) <= max_chunk_chars:
                buffer = candidate
                continue
            if buffer:
                assembled.append(buffer)
                buffer = ""
            if len(part) <= max_chunk_chars:
                buffer = part
                continue
            for idx in range(0, len(part), max_chunk_chars):
                chunk = part[idx : idx + max_chunk_chars]
                if len(chunk) >= min_chunk_chars:
                    assembled.append(chunk)
        if buffer:
            assembled.append(buffer)

        return [chunk for chunk in assembled if len(chunk) >= min_chunk_chars]

    chunks = []
    sections = re.split(r"\n(?=##?\\s)", text)
    for index, section in enumerate(sections):
        section = section.strip()
        if len(section) < min_chunk_chars:
            continue
        lines = section.split("\n")
        title = lines[0].replace("#", "").strip() if lines else f"Section {index}"
        metadata: dict[str, Any] = {
            "client_slug": client_slug,
            "doc_id": doc_id,
            "doc_name": doc_name,
            "section_title": title,
            "section_index": index,
        }
        if branch_id:
            metadata["branch_id"] = branch_id
        if knowledge_tag:
            metadata["knowledge_tag"] = knowledge_tag
        for offset, chunk_text in enumerate(
            _append_chunks(section, section_index=index, section_title=title)
        ):
            if offset:
                metadata = {**metadata, "chunk_index": offset}
            chunks.append({"content": chunk_text, "metadata": metadata})
    return chunks


def _collect_service_entries(payload_json: dict) -> list[dict]:
    client_pack = payload_json.get("client_pack") if isinstance(payload_json, dict) else None
    if not isinstance(client_pack, dict):
        return []
    price_list = client_pack.get("price_list")
    if not isinstance(price_list, list):
        price_list = []

    index: dict[str, str] = {}
    for category in price_list:
        if not isinstance(category, dict):
            continue
        category_name = str(category.get("category", "")).strip()
        items = category.get("items")
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if name and category_name:
                index[name.casefold()] = category_name

    entries: list[dict] = []
    for category in price_list:
        if not isinstance(category, dict):
            continue
        category_name = str(category.get("category", "")).strip()
        for item in category.get("items", []) if isinstance(category.get("items"), list) else []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            entries.append(
                {
                    "entry_type": "price_item",
                    "canonical_name": name,
                    "category": category_name or None,
                    "price_item": {
                        "name": name,
                        "price": item.get("price"),
                        "price_from": item.get("price_from"),
                        "note": item.get("note"),
                    },
                }
            )

    catalog = client_pack.get("services_catalog")
    services = catalog.get("services") if isinstance(catalog, dict) else None
    if isinstance(services, list):
        for service in services:
            if not isinstance(service, dict):
                continue
            name = str(service.get("name", "")).strip()
            if not name:
                continue
            category = None
            price_items = service.get("price_items") if isinstance(service.get("price_items"), list) else []
            for price_item_name in price_items:
                if not isinstance(price_item_name, str):
                    continue
                category = index.get(price_item_name.casefold())
                if category:
                    break
            entries.append(
                {
                    "entry_type": "service_catalog",
                    "canonical_name": name,
                    "category": category,
                    "price_item": None,
                }
            )

    seen: set[tuple[str, str, str | None]] = set()
    deduped: list[dict] = []
    for entry in entries:
        key = (
            str(entry.get("entry_type") or ""),
            str(entry.get("canonical_name") or "").casefold(),
            str(entry.get("category") or "") or None,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped
