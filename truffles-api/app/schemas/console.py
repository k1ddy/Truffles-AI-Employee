from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.capabilities import CapabilitiesPayload
from app.schemas.onboarding_contract import OnboardingContractPayload


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


class ConsoleCompany(BaseModel):
    id: UUID
    name: str
    billing_info: Optional[dict] = None


class ConsoleClient(BaseModel):
    id: UUID
    slug: str
    name: Optional[str] = None
    status: Optional[str] = None
    company_id: Optional[UUID] = None
    company_name: Optional[str] = None


class ConsoleBranch(BaseModel):
    id: UUID
    slug: str
    name: str
    is_active: bool
    instance_id: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    phone: Optional[str] = None
    knowledge_tag: Optional[str] = None
    timezone: Optional[str] = None
    working_hours: Optional[dict] = None
    booking_settings: Optional[dict] = None
    onboarding_state: Optional[str] = None
    onboarding_updated_at: Optional[str] = None


class ConsoleCompanyListResponse(BaseModel):
    items: list[ConsoleCompany]
    cursor: Optional[str] = None
    has_more: bool


class ConsoleClientListResponse(BaseModel):
    items: list[ConsoleClient]
    cursor: Optional[str] = None
    has_more: bool


class ConsoleBranchListResponse(BaseModel):
    items: list[ConsoleBranch]
    cursor: Optional[str] = None
    has_more: bool


class ConsoleMacro(BaseModel):
    id: UUID
    scope: Literal["personal", "team"]
    label: str
    body: str
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConsoleMacroListResponse(BaseModel):
    items: list[ConsoleMacro]


class ConsoleMacroCreateRequest(BaseModel):
    scope: Literal["personal", "team"]
    label: str
    body: str
    is_active: Optional[bool] = True


class ConsoleMacroCreateResponse(BaseModel):
    macro: ConsoleMacro


class ConsoleMacroUpdateRequest(BaseModel):
    label: Optional[str] = None
    body: Optional[str] = None
    is_active: Optional[bool] = None


class ConsoleCompanyCreateRequest(BaseModel):
    name: str
    billing_info: Optional[dict] = None


class ConsoleCompanyCreateResponse(BaseModel):
    company: ConsoleCompany


class ConsoleCompanyUpdateRequest(BaseModel):
    name: Optional[str] = None
    billing_info: Optional[dict] = None


class ConsoleClientCreateRequest(BaseModel):
    slug: str
    company_id: UUID
    status: Optional[str] = "active"


class ConsoleClientCreateResponse(BaseModel):
    client: ConsoleClient


class ConsoleClientUpdateRequest(BaseModel):
    slug: Optional[str] = None
    company_id: Optional[UUID] = None
    status: Optional[str] = None


class ConsoleClientLifecycleActionRequest(BaseModel):
    reason: str


class ConsoleBranchCreateRequest(BaseModel):
    client_id: UUID
    slug: str
    name: str
    timezone: Optional[str] = None
    instance_id: Optional[str] = None
    phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    knowledge_tag: Optional[str] = None
    working_hours: Optional[dict] = None
    booking_settings: Optional[dict] = None
    is_active: Optional[bool] = None


class ConsoleBranchCreateResponse(BaseModel):
    branch: ConsoleBranch


class ConsoleBranchUpdateRequest(BaseModel):
    slug: Optional[str] = None
    name: Optional[str] = None
    timezone: Optional[str] = None
    instance_id: Optional[str] = None
    phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    knowledge_tag: Optional[str] = None
    working_hours: Optional[dict] = None
    booking_settings: Optional[dict] = None
    is_active: Optional[bool] = None
    confirmation_id: Optional[UUID] = None


OnboardingStepId = Literal[
    "branch_draft",
    "integrations",
    "team",
    "telegram",
    "knowledge",
    "booking",
    "go_no_go",
]

OnboardingStepStatusValue = Literal["complete", "available", "locked", "skipped"]


class ConsoleOnboardingStepStatus(BaseModel):
    id: OnboardingStepId
    status: OnboardingStepStatusValue
    required: bool
    missing: list[str] = []


class ConsoleOnboardingStatusResponse(BaseModel):
    branch_id: UUID
    current_step: OnboardingStepId
    steps: list[ConsoleOnboardingStepStatus]
    updated_at: Optional[str] = None


class ConsoleOnboardingAdvanceRequest(BaseModel):
    branch_id: UUID
    step_id: OnboardingStepId


ConfirmationAction = Literal["knowledge_rollback", "branch_deactivate"]
ConfirmationTargetType = Literal["knowledge_version", "branch"]


class ConsoleConfirmationCreateRequest(BaseModel):
    action: ConfirmationAction
    target_type: ConfirmationTargetType
    target_id: UUID
    reason: str


class ConsoleConfirmationResponse(BaseModel):
    confirmation_id: UUID
    action: ConfirmationAction
    target_type: ConfirmationTargetType
    target_id: UUID
    expires_at: str


class ConsoleAgentCreateRequest(BaseModel):
    client_id: UUID
    branch_id: Optional[UUID] = None
    role: Literal["owner", "admin", "manager", "support", "platform_admin", "specialist", "viewer"]
    name: Optional[str] = None
    is_active: Optional[bool] = True
    oidc_subject: Optional[str] = None


class ConsoleAgentCreateResponse(BaseModel):
    agent: ConsoleAgent


class ConsoleMeResponse(BaseModel):
    agent: ConsoleAgent
    client: Optional[ConsoleClient] = None
    branches: list[ConsoleBranch]
    clients: list[ConsoleClient] = []
    companies: list[ConsoleCompany] = []
    company_selection_required: bool = False
    selection_required: bool = False
    branch_selection_required: bool = False
    selected_company_id: Optional[UUID] = None
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
    first_response_at: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution_time_seconds: Optional[int] = None
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


ConsoleOpsJobType = Literal["outbox_process", "heal", "metrics_snapshot"]
ConsoleOpsJobMode = Literal["dry_run", "execute"]
ConsoleOpsJobStatus = Literal["success", "failed"]


class ConsoleOpsJobDefinition(BaseModel):
    job_type: ConsoleOpsJobType
    label: str
    description: str
    supports_dry_run: bool


class ConsoleOpsJobCatalogResponse(BaseModel):
    items: list[ConsoleOpsJobDefinition]


class ConsoleOpsJobRunRequest(BaseModel):
    job_type: ConsoleOpsJobType
    mode: ConsoleOpsJobMode = "dry_run"
    params: Optional[dict] = None


class ConsoleOpsJobRecord(BaseModel):
    id: UUID
    job_type: ConsoleOpsJobType
    mode: ConsoleOpsJobMode
    status: ConsoleOpsJobStatus
    created_at: str
    finished_at: Optional[str] = None
    error_message: Optional[str] = None
    request_payload: Optional[dict] = None
    result_payload: Optional[dict] = None


class ConsoleOpsJobRunResponse(BaseModel):
    job: ConsoleOpsJobRecord


class ConsoleOpsJobListResponse(BaseModel):
    items: list[ConsoleOpsJobRecord]
    cursor: Optional[str] = None
    has_more: bool


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
    # Learning consent
    learning_consent_status: Optional[str] = None
    learning_anonymization_mode: Optional[str] = None
    learning_retention_days: Optional[int] = None
    data_sharing: Optional[str] = None


class ConsoleSettingsResponse(BaseModel):
    branches: list[ConsoleBranch]
    agents: list[ConsoleAgentInfo]
    bot_config: Optional[ConsoleBotConfig] = None


class ConsoleLearningCandidate(BaseModel):
    id: UUID
    status: str
    question_text: str
    response_text: str
    source_name: Optional[str] = None
    source_role: Optional[str] = None
    source_channel: Optional[str] = None
    candidate_type: Optional[str] = None
    branch_id: Optional[UUID] = None
    handover_id: Optional[UUID] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    approved_at: Optional[str] = None
    rejected_at: Optional[str] = None
    retention_expires_at: Optional[str] = None
    consent_status: Optional[str] = None
    anonymization_mode: Optional[str] = None
    can_approve: bool = False
    ineligible_reason: Optional[str] = None


class ConsoleLearningCandidateListResponse(BaseModel):
    items: list[ConsoleLearningCandidate]
    cursor: Optional[str] = None
    has_more: bool


class ConsoleLearningCandidateActionResponse(BaseModel):
    success: bool
    message: str


class ConsoleCapabilitiesRecord(BaseModel):
    id: UUID
    client_id: UUID
    branch_id: Optional[UUID] = None
    scope: Literal["client", "branch"]
    status: Literal["active", "disabled"]
    schema_version: str
    payload: CapabilitiesPayload
    created_by: Optional[UUID] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConsoleCapabilitiesResponse(BaseModel):
    client_id: UUID
    branch_id: Optional[UUID] = None
    effective: CapabilitiesPayload
    client_capabilities: Optional[ConsoleCapabilitiesRecord] = None
    branch_capabilities: Optional[ConsoleCapabilitiesRecord] = None


class ConsoleCapabilitiesPatchRequest(BaseModel):
    scope: Literal["client", "branch"]
    branch_id: Optional[UUID] = None
    status: Optional[Literal["active", "disabled"]] = None
    schema_version: Optional[str] = None
    payload: CapabilitiesPayload


class ConsoleOnboardingContractRecord(BaseModel):
    id: UUID
    client_id: UUID
    branch_id: Optional[UUID] = None
    scope: Literal["client", "branch"]
    status: Literal["active", "disabled"]
    schema_version: str
    payment_status: Literal["pending", "confirmed", "rejected"]
    payment_confirmed_at: Optional[str] = None
    payment_confirmed_by: Optional[UUID] = None
    payload: OnboardingContractPayload
    created_by: Optional[UUID] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConsoleOnboardingContractResponse(BaseModel):
    client_id: UUID
    branch_id: Optional[UUID] = None
    effective: OnboardingContractPayload
    payment_status: Literal["pending", "confirmed", "rejected"]
    payment_confirmed_at: Optional[str] = None
    payment_confirmed_by: Optional[UUID] = None
    capability_mismatches: list[str] = []
    client_contract: Optional[ConsoleOnboardingContractRecord] = None
    branch_contract: Optional[ConsoleOnboardingContractRecord] = None


class ConsoleOnboardingContractPatchRequest(BaseModel):
    scope: Literal["client", "branch"]
    branch_id: Optional[UUID] = None
    status: Optional[Literal["active", "disabled"]] = None
    schema_version: Optional[str] = None
    payment_status: Optional[Literal["pending", "confirmed", "rejected"]] = None
    payload: OnboardingContractPayload


class ConsoleReferencePack(BaseModel):
    id: UUID
    domain_slug: str
    title: str
    description: Optional[str] = None
    schema_version: str
    status: Literal["active", "disabled"]
    metadata: dict
    created_by: Optional[UUID] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConsoleReferencePackListResponse(BaseModel):
    items: list[ConsoleReferencePack]


class ConsoleReferencePackUpsertRequest(BaseModel):
    title: str
    description: Optional[str] = None
    schema_version: Optional[str] = None
    status: Optional[Literal["active", "disabled"]] = None
    metadata: Optional[dict] = None


OnboardingPurchasedService = Literal[
    "whatsapp",
    "telegram",
    "instagram",
    "booking_collect",
    "booking_confirm",
    "knowledge_upload",
    "analytics",
    "auto_learn",
    "provider_google_calendar",
    "provider_local_calendar",
    "provider_manual",
    "provider_amocrm",
    "provider_bitrix",
]


class ConsoleOnboardingAutopilotRequest(BaseModel):
    company_id: Optional[UUID] = None
    company_name: Optional[str] = None
    client_id: Optional[UUID] = None
    client_slug: Optional[str] = None
    branch_id: Optional[UUID] = None
    branch_slug: Optional[str] = None
    branch_name: Optional[str] = None
    timezone: Optional[str] = None
    phone: str
    instance_id: str
    payment_status: Optional[Literal["pending", "confirmed", "rejected"]] = "pending"
    domain_slug: Optional[str] = None
    purchased: Optional[CapabilitiesPayload] = None
    purchased_services: Optional[list[OnboardingPurchasedService]] = None
    client_data_text: Optional[str] = None
    client_data_json: Optional[dict] = None
    activate_branch: Optional[bool] = True
    auto_create_reference_pack: Optional[bool] = True
    auto_publish_knowledge: Optional[bool] = False


class ConsoleOnboardingAutopilotIntake(BaseModel):
    knowledge_tag: str
    draft_saved: bool
    published: bool
    published_version_id: Optional[UUID] = None
    missing_fields: list[str] = []
    missing_questions: list[str] = []
    payload: dict


class ConsoleOnboardingAutopilotResponse(BaseModel):
    company: ConsoleCompany
    client: ConsoleClient
    branch: ConsoleBranch
    capabilities: ConsoleCapabilitiesRecord
    onboarding_contract: ConsoleOnboardingContractRecord
    payment_status: Literal["pending", "confirmed", "rejected"]
    webhook_secret: str
    webhook_url: str
    reference_pack: Optional[ConsoleReferencePack] = None
    onboarding_status: ConsoleOnboardingStatusResponse
    go_no_go_missing: list[str] = []
    intake: ConsoleOnboardingAutopilotIntake
    actions: list[str] = []


class ConsoleWebhookSecretResponse(BaseModel):
    client_id: UUID
    branch_id: UUID
    instance_id: str
    webhook_secret: str
    webhook_url: str


class ConsoleBranchIntegrationStatus(BaseModel):
    branch_id: UUID
    branch_slug: str
    branch_name: str
    is_active: bool
    instance_id: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_url_valid: bool = False
    whatsapp_status: Literal[
        "ok",
        "inactive",
        "missing_instance_id",
        "instance_id_mismatch",
        "invalid_webhook_url",
        "no_recent_inbound",
    ]
    telegram_status: Literal["ok", "inactive", "missing_bot_token", "missing_chat_id"]
    last_inbound_at: Optional[str] = None
    last_inbound_instance_id: Optional[str] = None
    drift_issues: list[str] = []
    status: Literal["ok", "warn", "error"]


class ConsoleIntegrationsListResponse(BaseModel):
    stale_after_minutes: int
    items: list[ConsoleBranchIntegrationStatus]


class ConsoleAgentListResponse(BaseModel):
    items: list[ConsoleAgentWithIdentities]


KpiStatus = Literal["fact", "estimate", "need"]


class ConsoleAnalyticsTopIntent(BaseModel):
    intent: str
    count: int
    share: float


class ConsoleAnalyticsTopSection(BaseModel):
    section: str
    count: int
    share: float


class ConsoleAnalyticsTrendPoint(BaseModel):
    date: str
    bot_closed_rate: Optional[float] = None
    booking_conversion_rate: Optional[float] = None
    first_response_p50_seconds: Optional[float] = None
    after_hours_coverage_rate: Optional[float] = None
    escalation_quality_rate: Optional[float] = None
    outbox_failed_total: Optional[int] = None
    no_response_alert_total: Optional[int] = None


class ConsoleMetricsDailyResponse(BaseModel):
    date: str
    total_cases: int
    pending_cases: int
    active_cases: int
    resolved_cases: int
    avg_resolution_hours: Optional[float] = None
    total_client_messages: Optional[int] = None
    total_bot_messages: Optional[int] = None
    inbound_conversations_total: Optional[int] = None
    bot_closed_sessions: Optional[int] = None
    bot_closed_total_sessions: Optional[int] = None
    bot_closed_incomplete_total: Optional[int] = None
    bot_closed_rate: Optional[float] = None
    bot_closed_status: Optional[KpiStatus] = None
    manager_median_response_seconds: Optional[float] = None
    manager_time_saved_seconds_estimate: Optional[float] = None
    manager_time_saved_status: Optional[KpiStatus] = None
    booking_total: Optional[int] = None
    booking_attributed: Optional[int] = None
    booking_missing_conversation_total: Optional[int] = None
    booking_conversion_rate: Optional[float] = None
    booking_status: Optional[KpiStatus] = None
    first_response_p50_seconds: Optional[float] = None
    first_response_p90_seconds: Optional[float] = None
    first_response_missing_total: Optional[int] = None
    first_response_status: Optional[KpiStatus] = None
    after_hours_total: Optional[int] = None
    after_hours_covered: Optional[int] = None
    after_hours_missing_total: Optional[int] = None
    after_hours_coverage_rate: Optional[float] = None
    after_hours_status: Optional[KpiStatus] = None
    escalation_total: Optional[int] = None
    escalation_quality_total: Optional[int] = None
    escalation_meta_missing_total: Optional[int] = None
    escalation_quality_rate: Optional[float] = None
    escalation_quality_status: Optional[KpiStatus] = None
    outbox_failed_total: Optional[int] = None
    outbox_saved_total: Optional[int] = None
    no_response_alert_total: Optional[int] = None
    loss_risk_status: Optional[KpiStatus] = None
    intent_missing_total: Optional[int] = None
    top_intents: Optional[list[ConsoleAnalyticsTopIntent]] = None
    top_info_sections: Optional[list[ConsoleAnalyticsTopSection]] = None
    top_intents_status: Optional[KpiStatus] = None
    analytics_trend: Optional[list[ConsoleAnalyticsTrendPoint]] = None


class ConsoleSettingsUpdateRequest(BaseModel):
    reminder_1_minutes: Optional[int] = None
    reminder_2_minutes: Optional[int] = None
    escalation_timeout_minutes: Optional[int] = None


class ConsoleSettingsUpdateResponse(BaseModel):
    success: bool
    message: str


class ConsoleKnowledgeCurrentResponse(BaseModel):
    version_id: Optional[UUID] = None
    payload: Optional[dict] = None
    content: Optional[str] = None


class ConsoleKnowledgeValidateRequest(BaseModel):
    draft_text: str


class ConsoleKnowledgeValidateResponse(BaseModel):
    valid: bool
    errors: list[str]
    warnings: list[str]
    diff: Optional[str] = None


class ConsoleKnowledgePublishRequest(BaseModel):
    draft_text: str


class ConsoleKnowledgePublishResponse(BaseModel):
    success: bool
    version_id: Optional[UUID] = None
    published_at: Optional[str] = None
    message: Optional[str] = None


class ConsoleKnowledgeHistoryItem(BaseModel):
    id: UUID
    status: str
    created_at: Optional[str] = None
    published_at: Optional[str] = None
    summary: Optional[str] = None


class ConsoleKnowledgeHistoryResponse(BaseModel):
    items: list[ConsoleKnowledgeHistoryItem]


class ConsoleKnowledgeRollbackRequest(BaseModel):
    version_id: UUID
    confirmation_id: Optional[UUID] = None


class ConsoleKnowledgeRollbackResponse(BaseModel):
    success: bool
    version_id: Optional[UUID] = None


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
