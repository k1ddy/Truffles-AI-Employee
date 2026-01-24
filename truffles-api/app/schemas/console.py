from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class ConsoleError(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None
    trace_id: str


class ConsoleErrorResponse(BaseModel):
    error: ConsoleError


class ConsoleAgent(BaseModel):
    id: UUID
    name: Optional[str] = None
    role: str
    client_id: UUID
    branch_id: Optional[UUID] = None
    is_active: bool


class ConsoleAgentIdentity(BaseModel):
    channel: Literal["telegram"]
    external_id: str
    username: Optional[str] = None
    linked_at: Optional[str] = None


class ConsoleAgentWithIdentities(BaseModel):
    id: UUID
    name: Optional[str] = None
    role: str
    client_id: UUID
    branch_id: Optional[UUID] = None
    is_active: bool
    identities: list[ConsoleAgentIdentity] = []


class ConsoleClient(BaseModel):
    id: UUID
    slug: str
    name: Optional[str] = None
    company_id: Optional[UUID] = None


class ConsoleBranch(BaseModel):
    id: UUID
    slug: str
    name: str
    is_active: bool
    instance_id: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class ConsoleMeResponse(BaseModel):
    agent: ConsoleAgent
    client: Optional[ConsoleClient] = None
    branches: list[ConsoleBranch]
    clients: list[ConsoleClient] = []
    selection_required: bool = False
    branch_selection_required: bool = False
    selected_branch_id: Optional[UUID] = None


class ConsoleMessage(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: str
    metadata: Optional[dict] = None


class ConsoleTelegramTrail(BaseModel):
    message_id: Optional[int] = None
    topic_id: Optional[int] = None
    chat_id: Optional[str] = None
    telegram_link: Optional[str] = None
    telegram_desktop_link: Optional[str] = None
    delivery_status: Optional[str] = None
    delivered_at: Optional[str] = None


class ConsoleCase(BaseModel):
    id: UUID
    conversation_id: UUID
    status: str
    trigger_type: str
    trigger_value: Optional[str] = None
    context_summary: Optional[str] = None
    user_message: Optional[str] = None
    assigned_to_name: Optional[str] = None
    branch_id: Optional[UUID] = None
    channel: Optional[str] = None
    created_at: str
    sla_status: Optional[str] = "ok"  # ok, warning, breached
    # Customer info
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_remote_jid: Optional[str] = None
    # Decision trace
    decision_trace: Optional[list[dict]] = None
    # Inbox health
    last_inbound_at: Optional[str] = None
    last_outbound_at: Optional[str] = None
    last_activity_at: Optional[str] = None
    last_activity_channel: Optional[str] = None
    last_message_preview: Optional[str] = None
    needs_reply: Optional[bool] = None
    has_delivery_error: Optional[bool] = None
    has_pending_outbox: Optional[bool] = None
    # Telegram trail (for escalation visibility)
    telegram_trail: Optional[ConsoleTelegramTrail] = None


class ConsoleCaseListResponse(BaseModel):
    items: list[ConsoleCase]
    cursor: Optional[str] = None
    has_more: bool


class ConsoleSyncStatus(BaseModel):
    status: Literal["ok", "skipped", "failed"]
    detail: Optional[str] = None


class ConsoleCaseActionSync(BaseModel):
    telegram: Optional[ConsoleSyncStatus] = None
    client_notify: Optional[ConsoleSyncStatus] = None


class ConsoleCaseActionResponse(BaseModel):
    success: bool
    case: ConsoleCase
    sync: Optional[ConsoleCaseActionSync] = None


class ConsoleMessageListResponse(BaseModel):
    items: list[ConsoleMessage]
    cursor: Optional[str] = None
    has_more: bool


class ConsoleManagerMessageRequest(BaseModel):
    content: str


class ConsoleManagerMessageResponse(BaseModel):
    success: bool
    message: ConsoleMessage


class ConsoleHealthResponse(BaseModel):
    status: str
    version: str
    database: str
    redis: str
    outbox_backlog: int


class ConsoleOutboxCounts(BaseModel):
    pending: int
    processing: int
    failed: int


class ConsoleOutboxItem(BaseModel):
    id: UUID
    status: str
    attempts: int
    next_attempt_at: Optional[str] = None
    last_error: Optional[str] = None
    created_at: str
    updated_at: str
    conversation_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    inbound_message_id: str
    channel: Optional[str] = None
    message_type: Optional[str] = None
    message_preview: Optional[str] = None
    remote_jid: Optional[str] = None
    instance_id: Optional[str] = None
    forwarded_to_telegram: Optional[bool] = None


class ConsoleOutboxListResponse(BaseModel):
    items: list[ConsoleOutboxItem]
    cursor: Optional[str] = None
    has_more: bool
    counts: ConsoleOutboxCounts


class ConsoleOutboxRetryRequest(BaseModel):
    ids: Optional[list[UUID]] = None
    limit: Optional[int] = 100


class ConsoleOutboxRetryResponse(BaseModel):
    success: bool
    retried: int
    skipped: int


class ConsoleAuditEvent(BaseModel):
    id: UUID
    created_at: str
    event_type: str
    actor_name: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    payload: Optional[dict] = None


class ConsoleAuditListResponse(BaseModel):
    items: list[ConsoleAuditEvent]
    cursor: Optional[str] = None
    has_more: bool


class ConsoleAgentInfo(BaseModel):
    id: UUID
    name: Optional[str] = None
    role: str
    is_active: bool


class ConsoleBotConfig(BaseModel):
    """Bot configuration from client_settings for display."""
    # SLA/Reminders
    reminder_timeout_1: Optional[int] = None  # minutes
    reminder_timeout_2: Optional[int] = None  # minutes
    auto_close_timeout: Optional[int] = None  # minutes
    # Quiet hours
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    # Bot behavior
    tone: Optional[str] = None
    autolearn_enabled: bool = False
    booking_enabled: bool = False
    # Escalation
    enable_reminders: bool = True
    enable_owner_escalation: bool = False


class ConsoleSettingsResponse(BaseModel):
    branches: list[ConsoleBranch]
    agents: list[ConsoleAgentInfo]
    bot_config: Optional[ConsoleBotConfig] = None


class ConsoleAgentListResponse(BaseModel):
    items: list[ConsoleAgentWithIdentities]


class ConsoleMetricsDailyResponse(BaseModel):
    date: str
    total_cases: int
    pending_cases: int
    active_cases: int
    resolved_cases: int
    avg_resolution_hours: Optional[float] = None


class ConsoleSettingsUpdateRequest(BaseModel):
    reminder_1_minutes: Optional[int] = None
    reminder_2_minutes: Optional[int] = None
    escalation_timeout_minutes: Optional[int] = None


class ConsoleSettingsUpdateResponse(BaseModel):
    success: bool
    message: str


class ConsoleTelegramHealthResponse(BaseModel):
    status: str
    webhook_alive: bool
    last_success_at: Optional[str] = None
    last_error_at: Optional[str] = None
    last_error_message: Optional[str] = None
    error_rate_24h: float
    pending_messages: int


class ConsoleTelegramVerifyRequest(BaseModel):
    scope: Literal["client", "branch"] = "client"
    branch_id: Optional[UUID] = None
    chat_id: Optional[str] = None


class ConsoleTelegramVerifyResponse(BaseModel):
    success: bool
    delivery_status: str
    verification_code: str
    message_id: Optional[int] = None
    chat_id: Optional[str] = None
    branch_id: Optional[UUID] = None
    error_message: Optional[str] = None


class ConsoleTelegramTestRequest(ConsoleTelegramVerifyRequest):
    message: Optional[str] = None


class ConsoleTelegramTestResponse(BaseModel):
    success: bool
    delivery_status: str
    message_id: Optional[int] = None
    chat_id: Optional[str] = None
    branch_id: Optional[UUID] = None
    error_message: Optional[str] = None


class ConsoleTelegramLinkResponse(BaseModel):
    token: str
    deep_link: Optional[str] = None
    bot_username: Optional[str] = None
    expires_at: str
