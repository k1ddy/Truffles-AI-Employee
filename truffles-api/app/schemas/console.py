from typing import Optional
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


class ConsoleClient(BaseModel):
    id: UUID
    slug: str


class ConsoleBranch(BaseModel):
    id: UUID
    slug: str
    name: str
    is_active: bool
    telegram_chat_id: Optional[str] = None


class ConsoleMeResponse(BaseModel):
    agent: ConsoleAgent
    client: ConsoleClient
    branches: list[ConsoleBranch]


class ConsoleMessage(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: str
    metadata: Optional[dict] = None


class ConsoleTelegramTrail(BaseModel):
    """Telegram notification details for a case."""
    message_id: Optional[int] = None
    topic_id: Optional[int] = None
    chat_id: Optional[str] = None
    telegram_link: Optional[str] = None
    delivery_status: Optional[str] = None  # sent, failed, pending
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
    # Telegram trail (TG-01)
    telegram_trail: Optional[ConsoleTelegramTrail] = None


class ConsoleCaseListResponse(BaseModel):
    items: list[ConsoleCase]
    cursor: Optional[str] = None
    has_more: bool


class ConsoleCaseActionResponse(BaseModel):
    success: bool
    case: ConsoleCase


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


# TG-02: Branch Telegram Settings
class ConsoleBranchTelegramUpdate(BaseModel):
    telegram_chat_id: Optional[str] = None


class ConsoleBranchTelegramResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    telegram_chat_id: Optional[str] = None
    telegram_verified: bool = False


class ConsoleTelegramVerifyResponse(BaseModel):
    verified: bool
    chat_title: Optional[str] = None
    chat_type: Optional[str] = None
    is_forum: bool = False
    error: Optional[str] = None


class ConsoleTelegramTestResponse(BaseModel):
    success: bool
    message_id: Optional[int] = None
    error: Optional[str] = None


# TG-03: Telegram Health
class ConsoleTelegramHealthResponse(BaseModel):
    status: str  # ok, degraded, error
    webhook_alive: bool = False
    last_success_at: Optional[str] = None
    last_error_at: Optional[str] = None
    last_error_message: Optional[str] = None
    error_rate_24h: float = 0.0
    pending_messages: int = 0
