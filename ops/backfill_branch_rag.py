#!/usr/bin/env python3
"""
Backfill branch-scoped RAG documents in Qdrant using published knowledge versions.

Dry-run by default. Use --execute to apply.

Examples:
  python3 ops/backfill_branch_rag.py --dry-run
  python3 ops/backfill_branch_rag.py --client-slug demo_salon --execute
  python3 ops/backfill_branch_rag.py --branch-id <uuid> --execute
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from uuid import UUID

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "truffles-api"
if str(APP_ROOT) not in __import__("sys").path:
    __import__("sys").path.append(str(APP_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models.branch import Branch  # noqa: E402
from app.models.client import Client  # noqa: E402
from app.services import knowledge_registry_service  # noqa: E402
from app.services.knowledge_registry_service import (  # noqa: E402
    get_current_published,
    sync_qdrant_from_pack,
)


def _patch_embedding_timeout(timeout_seconds: float) -> None:
    import time

    import httpx

    from app.services import knowledge_service

    def _get_embedding(text: str, *, client_slug: str | None = None):
        start = time.monotonic()
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.post(knowledge_service.BGE_M3_URL, json={"inputs": text})
        except httpx.TimeoutException as exc:
            raise RuntimeError("bge_timeout") from exc
        if response.status_code != 200:
            knowledge_service.record_bge_time(
                client_slug, (time.monotonic() - start) * 1000
            )
            raise Exception(f"BGE-M3 error: {response.status_code} - {response.text}")

        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            embedding = data[0] if isinstance(data[0], list) else data
        else:
            embedding = data.get("embedding") or data.get("embeddings") or data
        knowledge_service.record_bge_time(
            client_slug, (time.monotonic() - start) * 1000
        )
        return embedding

    knowledge_registry_service.get_embedding = _get_embedding


def _patch_qdrant_timeout(timeout_seconds: float) -> None:
    import httpx

    def _delete_client_docs(
        client_slug: str,
        *,
        branch_id: UUID | None,
        knowledge_tag: str | None,
    ) -> None:
        headers = (
            {"api-key": knowledge_registry_service.QDRANT_API_KEY}
            if knowledge_registry_service.QDRANT_API_KEY
            else None
        )
        must = [{"key": "metadata.client_slug", "match": {"value": client_slug}}]
        if knowledge_tag:
            must.append({"key": "metadata.knowledge_tag", "match": {"value": knowledge_tag}})
        if branch_id:
            must.append({"key": "metadata.branch_id", "match": {"value": str(branch_id)}})
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.post(
                    f"{knowledge_registry_service.QDRANT_HOST}/collections/{knowledge_registry_service.QDRANT_COLLECTION}/points/delete",
                    headers=headers,
                    json={"filter": {"must": must}},
                )
        except httpx.TimeoutException as exc:
            raise RuntimeError("qdrant_timeout") from exc
        if response.status_code not in {200, 202}:
            knowledge_registry_service.logger.warning(
                "Qdrant delete failed",
                extra={"context": {"status_code": response.status_code, "body": response.text}},
            )

    def _upsert_points(collection: str, points: list[dict]) -> None:
        if not points:
            return
        headers = (
            {"api-key": knowledge_registry_service.QDRANT_API_KEY}
            if knowledge_registry_service.QDRANT_API_KEY
            else None
        )
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.put(
                    f"{knowledge_registry_service.QDRANT_HOST}/collections/{collection}/points",
                    headers=headers,
                    json={"points": points},
                )
                if response.status_code not in {200, 201}:
                    raise RuntimeError(
                        f"Qdrant upsert error: {response.status_code} {response.text}"
                    )
        except httpx.TimeoutException as exc:
            raise RuntimeError("qdrant_timeout") from exc

    knowledge_registry_service._delete_client_docs = _delete_client_docs
    knowledge_registry_service._upsert_points = _upsert_points


@dataclass(frozen=True)
class BranchSyncTarget:
    client: Client
    branch: Branch


def _parse_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        raise SystemExit(f"Invalid UUID: {value}")


def _load_targets(
    db: Session,
    *,
    client_slug: str | None,
    branch_id: UUID | None,
    include_inactive: bool,
) -> list[BranchSyncTarget]:
    query = db.query(Branch, Client).join(Client, Client.id == Branch.client_id)
    if client_slug:
        query = query.filter(Client.name == client_slug)
    if branch_id:
        query = query.filter(Branch.id == branch_id)
    if not include_inactive:
        query = query.filter(Branch.is_active.is_(True))
    query = query.order_by(Client.name, Branch.slug)
    return [BranchSyncTarget(client=row[1], branch=row[0]) for row in query.all()]


def _iter_targets(targets: Iterable[BranchSyncTarget], *, limit: int | None) -> Iterable[BranchSyncTarget]:
    if limit is None:
        yield from targets
        return
    count = 0
    for target in targets:
        if count >= limit:
            return
        yield target
        count += 1


def _sync_branch(
    db: Session,
    *,
    target: BranchSyncTarget,
    execute: bool,
) -> tuple[bool, str, str | None]:
    client = target.client
    branch = target.branch
    published = get_current_published(db, branch_id=branch.id)
    if not published:
        return False, "no_published_knowledge", None

    if not execute:
        return True, "dry_run", str(published.id)

    sync_qdrant_from_pack(
        published.payload_json,
        client_slug=client.name,
        branch_id=branch.id,
        knowledge_tag=branch.knowledge_tag,
        version_id=published.id,
    )
    return True, "synced", str(published.id)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill branch RAG Qdrant payloads")
    parser.add_argument("--client-slug", help="Filter by client slug (clients.name)")
    parser.add_argument("--branch-id", help="Filter by branch UUID")
    parser.add_argument("--include-inactive", action="store_true", help="Include inactive branches")
    parser.add_argument("--limit", type=int, help="Limit number of branches")
    parser.add_argument("--bge-timeout", type=float, help="Override BGE timeout seconds")
    parser.add_argument("--qdrant-timeout", type=float, help="Override Qdrant timeout seconds")
    parser.add_argument("--execute", action="store_true", help="Apply Qdrant sync")
    parser.add_argument("--dry-run", action="store_true", help="Alias for default dry-run")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue on sync errors",
    )
    args = parser.parse_args()

    branch_id = _parse_uuid(args.branch_id)
    execute = bool(args.execute)

    if not execute:
        print("DRY RUN: pass --execute to apply changes")

    if args.bge_timeout:
        _patch_embedding_timeout(args.bge_timeout)
    if args.qdrant_timeout:
        _patch_qdrant_timeout(args.qdrant_timeout)

    db = SessionLocal()
    try:
        try:
            targets = _load_targets(
                db,
                client_slug=args.client_slug,
                branch_id=branch_id,
                include_inactive=args.include_inactive,
            )
        except OperationalError as exc:
            print("DB connection failed. Check DATABASE_URL or run in container with DB access.")
            print(f"Error: {exc}")
            return 2
        if not targets:
            print("No branches matched filters.")
            return 1

        processed = 0
        skipped = 0
        errors = 0

        for target in _iter_targets(targets, limit=args.limit):
            client = target.client
            branch = target.branch
            label = f"{client.name}:{branch.slug} ({branch.id})"
            try:
                ok, reason, version_id = _sync_branch(db, target=target, execute=execute)
            except Exception as exc:
                errors += 1
                print(f"ERROR {label}: {exc}")
                if not args.continue_on_error:
                    return 2
                continue

            if not ok:
                skipped += 1
                print(f"SKIP {label}: {reason}")
                continue

            processed += 1
            action = "PLAN" if reason == "dry_run" else "SYNC"
            tag = branch.knowledge_tag or "-"
            print(f"{action} {label} knowledge_tag={tag} version_id={version_id}")

        print(
            "Summary: "
            f"processed={processed} skipped={skipped} errors={errors} total={len(targets)}"
        )
        return 0 if errors == 0 else 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
