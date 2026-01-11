from typing import Any, Optional
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field


class WebhookMetadata(BaseModel):
    sender: Optional[str] = None
    timestamp: Optional[int] = None
    messageId: Optional[str] = None
    remoteJid: Optional[str] = None
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


class WebhookRequest(BaseModel):
    body: WebhookBody
    client_slug: Optional[str] = "truffles"


class WebhookResponse(BaseModel):
    success: bool
    message: str
    conversation_id: Optional[UUID] = None
    bot_response: Optional[str] = None


# Decision Graph contracts
class IntentContract(BaseModel):
    intent: Optional[str] = None
    slots: Optional[dict[str, Any]] = None
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


class MemoryContract(BaseModel):
    mode: Optional[str] = None
    slots: Optional[dict[str, Any]] = None
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


class TraceContract(BaseModel):
    stage: Optional[str] = None
    decision: Optional[str] = None
    reason: Optional[str] = None
    meta: Optional[dict[str, Any]] = None
