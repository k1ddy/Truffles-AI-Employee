from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.outbox_payload import TenantContext


class KnowledgeSnapshotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_context: TenantContext
    version_id: str | None = None


class KnowledgeSnapshotSignature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    algorithm: str
    value: str
    key_id: str | None = None
    created_at: str | None = None


class KnowledgeSnapshotPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str = Field(..., min_length=1)
    tenant_context: TenantContext
    version_id: str = Field(..., min_length=1)
    schema_version: str = Field(..., min_length=1)
    created_at: str = Field(..., min_length=1)
    expires_at: str | None = None
    sha256: str = Field(..., min_length=1)
    packs: dict[str, Any]
    signature: KnowledgeSnapshotSignature | None = None
    extensions: dict[str, Any] | None = None
