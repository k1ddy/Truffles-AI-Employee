from typing import Any, Optional
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field, model_validator


class WebhookMetadata(BaseModel):
    sender: Optional[str] = None
    timestamp: Optional[int] = None
    messageId: Optional[str] = None
    remoteJid: Optional[str] = None
    simulation_mode: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("simulation_mode", "simulationMode"),
    )
    simulation_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("simulation_id", "simulationId"),
    )
    simulation_llm: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("simulation_llm", "simulationLlm"),
    )
    simulation_time: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("simulation_time", "simulationTime"),
    )
    instanceId: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("instanceId", "instance_id", "instance"),
    )
    forwarded_to_telegram: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("forwarded_to_telegram", "forwardedToTelegram"),
    )


class WebhookBody(BaseModel):
    messageType: Optional[str] = "text"
    message: Optional[str] = None
    metadata: Optional[WebhookMetadata] = None
    mediaData: Optional[Any] = None


class WebhookTenantContext(BaseModel):
    company_id: UUID | None = None
    client_id: UUID | None = None
    branch_id: UUID | None = None
    client_slug: str | None = None
    branch_slug: str | None = None
    instance_id: str | None = None
    source: str | None = None
    origin_source: str | None = None


class WebhookRequest(BaseModel):
    body: WebhookBody
    client_slug: Optional[str] = "truffles"
    tenant_context: WebhookTenantContext = Field(default_factory=WebhookTenantContext)

    @model_validator(mode="after")
    def _normalize_tenant_context(self) -> "WebhookRequest":
        if not self.tenant_context:
            self.tenant_context = WebhookTenantContext()

        client_slug = (self.client_slug or "").strip()
        if client_slug and not (self.tenant_context.client_slug or "").strip():
            self.tenant_context.client_slug = client_slug

        if not (self.tenant_context.source or "").strip():
            self.tenant_context.source = "webhook"

        return self


class WebhookResponse(BaseModel):
    success: bool
    message: str
    conversation_id: Optional[UUID] = None
    bot_response: Optional[str] = None


# Decision Graph contracts
class IntentContract(BaseModel):
    intent: Optional[str] = None
    slots: Optional[dict[str, Any]] = None
    pack_refs: Optional[list[str]] = None
    next_question: Optional[str] = None
    open_questions: Optional[list[str]] = None
    goal: Optional[str] = None
    reason: Optional[str] = None
    needs_manager: Optional[bool] = None
    entity_refs: Optional[list[dict[str, Any]]] = None
    subject_kind: Optional[str] = None
    capability: Optional[str] = None
    temporal_scope: Optional[str] = None
    resolution_mode: Optional[str] = None
    resolver_id: Optional[str] = None
    resolver_version: Optional[str] = None
    language: Optional[str] = None
    emotion: Optional[str] = None
    confidence: Optional[float] = None
    risk_signals: Optional[list[str]] = None


class ContextContract(BaseModel):
    tenant_id: Optional[str] = None
    branch_id: Optional[str] = None
    state: Optional[str] = None
    timezone: Optional[str] = None
    mode: Optional[str] = None


class FactContract(BaseModel):
    schema_version: Optional[str] = None
    manifest_id: Optional[str] = None
    request: Optional[dict[str, Any]] = None
    plan: Optional[dict[str, Any]] = None
    result: Optional[dict[str, Any]] = None
    requested_refs: Optional[list[str]] = None
    allowed_emitted_sets: Optional[list[list[str]]] = None
    emitted_refs: Optional[list[str]] = None
    facts: Optional[dict[str, Any]] = None
    sources: Optional[list[str]] = None
    policy_flags: Optional[list[str]] = None


class ActionContract(BaseModel):
    action_type: Optional[str] = None
    required_next_slots: Optional[list[str]] = None
    escalation_reason: Optional[str] = None


class ResponseContract(BaseModel):
    tone: Optional[str] = None
    must_include: Optional[list[str]] = None
    must_not_include: Optional[list[str]] = None
    language: Optional[str] = None


class InteractionStateContract(BaseModel):
    resume_slot: Optional[str] = None
    interaction_target: Optional[str] = None
    interaction_relation: Optional[str] = None
    interaction_owner: Optional[str] = None
    grounded_referents: Optional[dict[str, str]] = None
    confirmation_state: Optional[dict[str, Any]] = None
    degrade_reason: Optional[str] = None


class MemoryContract(BaseModel):
    mode: Optional[str] = None
    slots: Optional[dict[str, Any]] = None
    interaction_state: Optional[InteractionStateContract] = None
    summary: Optional[str] = None
    last_updated: Optional[str] = None
    ttl: Optional[int] = None
    last_updated_at: Optional[str] = None
    ttl_hours: Optional[int] = None
    active_goal: Optional[str] = None
    last_question_type: Optional[str] = None
    goal_stack: Optional[list[str]] = None
    pending_slots: Optional[dict[str, str]] = None
    unanswered_questions: Optional[list[str]] = None
    current_referents: Optional[dict[str, str]] = None
    pending_question_contract: Optional[dict[str, Any]] = None
    semantic_contract: Optional[dict[str, Any]] = None
    consult_state: Optional[dict[str, Any]] = None


class TraceContract(BaseModel):
    stage: Optional[str] = None
    decision: Optional[str] = None
    reason: Optional[str] = None
    meta: Optional[dict[str, Any]] = None
