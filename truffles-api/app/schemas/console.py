from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictStr

from app.schemas.capabilities import CapabilitiesPayload
from app.schemas.onboarding_contract import (
    OnboardingContractPayload,
    OnboardingProviderBindingPayload,
)


class ConsoleError(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None
    trace_id: str


class ConsoleErrorResponse(BaseModel):
    error: ConsoleError


class ConsoleRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


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


ConsoleAgentRole = Literal[
    "owner",
    "admin",
    "manager",
    "support",
    "platform_admin",
    "specialist",
    "viewer",
]
ConsoleMembershipScope = Literal["company", "client", "branch"]
ConsoleGoLiveState = Literal["pending", "approved", "rejected"]


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
    lifecycle_state: Optional[
        Literal["lead", "contracting", "onboarding", "go_live_ready", "active", "paused", "archived"]
    ] = None
    payment_status: Optional[Literal["pending", "confirmed", "rejected", "unknown"]] = None
    commercial_state: Optional[
        Literal["contract_missing", "payment_pending", "payment_confirmed", "payment_rejected"]
    ] = None
    service_state: Optional[Literal["ok", "degraded", "attention"]] = None
    owner_name: Optional[str] = None
    next_action: Optional[str] = None
    total_branches: Optional[int] = None
    active_branches: Optional[int] = None
    degraded_branches: Optional[int] = None
    go_live_ready_branches: Optional[int] = None


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
    go_live_state: ConsoleGoLiveState = "pending"
    go_live_reason: Optional[str] = None
    go_live_reviewed_at: Optional[str] = None
    go_live_reviewed_by: Optional[UUID] = None
    go_live_waiver_until: Optional[str] = None
    go_live_waiver_reason: Optional[str] = None
    go_live_waiver_by: Optional[UUID] = None
    go_live_waiver_active: bool = False
    go_live_allowed: bool = False


class ConsoleCompanyListResponse(BaseModel):
    items: list[ConsoleCompany]
    cursor: Optional[str] = None
    has_more: bool


class ConsoleFleetSummary(BaseModel):
    total_companies: int
    total_clients: int
    active_clients: int
    onboarding_clients: int
    archived_clients: int
    paused_clients: int
    go_live_ready_clients: int
    degraded_clients: int
    payment_pending_clients: int
    payment_confirmed_clients: int
    lifecycle_counts: dict[str, int]
    payment_counts: dict[str, int]
    service_counts: dict[str, int]


ConsoleFleetAttentionLevel = Literal["high", "medium", "low"]


class ConsoleFleetAttentionItem(BaseModel):
    client_id: UUID
    client_slug: str
    client_name: Optional[str] = None
    company_id: Optional[UUID] = None
    company_name: Optional[str] = None
    lifecycle_state: Literal["lead", "contracting", "onboarding", "go_live_ready", "active", "paused", "archived"]
    payment_status: Literal["pending", "confirmed", "rejected", "unknown"]
    commercial_state: Literal["contract_missing", "payment_pending", "payment_confirmed", "payment_rejected"]
    service_state: Literal["ok", "degraded", "attention"]
    owner_name: Optional[str] = None
    next_action: str
    total_branches: int = 0
    active_branches: int = 0
    degraded_branches: int = 0
    go_live_ready_branches: int = 0
    stale_branches: int = 0
    integration_error_branches: int = 0
    integration_warn_branches: int = 0
    outbox_failed_24h: int = 0
    pending_handovers: int = 0
    attention_score: int
    attention_level: ConsoleFleetAttentionLevel
    reasons: list[str] = []
    suggested_actions: list[str] = []


class ConsoleFleetAttentionSummary(BaseModel):
    active_clients_total: int
    clients_with_attention: int
    high_risk_clients: int
    medium_risk_clients: int
    low_risk_clients: int
    stale_branches_total: int
    integration_error_branches_total: int
    integration_warn_branches_total: int
    outbox_failed_24h_total: int
    pending_handovers_total: int


class ConsoleFleetAttentionResponse(BaseModel):
    generated_at: str
    stale_after_minutes: int
    summary: ConsoleFleetAttentionSummary
    items: list[ConsoleFleetAttentionItem]


class ConsoleClientListResponse(BaseModel):
    items: list[ConsoleClient]
    cursor: Optional[str] = None
    has_more: bool
    summary: Optional[ConsoleFleetSummary] = None


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


class ConsoleCompanyCreateRequest(ConsoleRequestModel):
    name: StrictStr
    billing_info: Optional[dict] = None


class ConsoleCompanyCreateResponse(BaseModel):
    company: ConsoleCompany


class ConsoleCompanyUpdateRequest(ConsoleRequestModel):
    name: Optional[StrictStr] = None
    billing_info: Optional[dict] = None


class ConsoleClientCreateRequest(ConsoleRequestModel):
    slug: StrictStr
    company_id: UUID
    status: Optional[StrictStr] = "active"


class ConsoleClientCreateResponse(BaseModel):
    client: ConsoleClient


class ConsoleClientUpdateRequest(ConsoleRequestModel):
    slug: Optional[StrictStr] = None
    company_id: Optional[UUID] = None
    status: Optional[StrictStr] = None


class ConsoleClientLifecycleActionRequest(ConsoleRequestModel):
    reason: StrictStr


class ConsoleBranchBootstrapAccountTemplate(BaseModel):
    role: ConsoleAgentRole
    name: Optional[str] = None
    oidc_subject: Optional[str] = None
    is_active: Optional[bool] = True


class ConsoleBranchCreateRequest(ConsoleRequestModel):
    client_id: UUID
    slug: StrictStr
    name: StrictStr
    timezone: Optional[StrictStr] = None
    instance_id: Optional[StrictStr] = None
    phone: Optional[StrictStr] = None
    telegram_chat_id: Optional[StrictStr] = None
    knowledge_tag: Optional[StrictStr] = None
    working_hours: Optional[dict] = None
    booking_settings: Optional[dict] = None
    is_active: Optional[bool] = None
    bootstrap_accounts: list[ConsoleBranchBootstrapAccountTemplate] = []


class ConsoleBranchCreateResponse(BaseModel):
    branch: ConsoleBranch
    created_agents: list[ConsoleAgent] = []


class ConsoleBranchUpdateRequest(ConsoleRequestModel):
    slug: Optional[StrictStr] = None
    name: Optional[StrictStr] = None
    timezone: Optional[StrictStr] = None
    instance_id: Optional[StrictStr] = None
    phone: Optional[StrictStr] = None
    telegram_chat_id: Optional[StrictStr] = None
    knowledge_tag: Optional[StrictStr] = None
    working_hours: Optional[dict] = None
    booking_settings: Optional[dict] = None
    is_active: Optional[bool] = None
    confirmation_id: Optional[UUID] = None


class ConsoleBranchChangePatch(ConsoleRequestModel):
    slug: Optional[StrictStr] = None
    name: Optional[StrictStr] = None
    timezone: Optional[StrictStr] = None
    instance_id: Optional[StrictStr] = None
    phone: Optional[StrictStr] = None
    telegram_chat_id: Optional[StrictStr] = None
    knowledge_tag: Optional[StrictStr] = None
    working_hours: Optional[dict] = None
    booking_settings: Optional[dict] = None
    is_active: Optional[bool] = None


class ConsoleBranchChangeDraftRequest(ConsoleRequestModel):
    branch_id: UUID
    reason: StrictStr
    patch: ConsoleBranchChangePatch


class ConsoleBranchChangePublishRequest(ConsoleRequestModel):
    confirmation_id: Optional[UUID] = None


class ConsoleBranchChangeRollbackRequest(ConsoleRequestModel):
    reason: StrictStr
    confirmation_id: Optional[UUID] = None


class ConsoleBranchGoLiveDecisionRequest(ConsoleRequestModel):
    reason: StrictStr


class ConsoleBranchGoLiveWaiverRequest(ConsoleRequestModel):
    reason: StrictStr
    ttl_hours: int


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
OnboardingScorecardStatusValue = Literal["pass", "fail"]
OnboardingDocumentIngestionStatusValue = Literal["pass", "fail", "skipped"]
OnboardingDocumentIngestionSourceValue = Literal["published", "draft", "none"]
OnboardingSlaControlLoopStatusValue = Literal["pass", "warn", "fail"]
OnboardingSlaProviderStatusValue = Literal[
    "configured",
    "missing",
    "webhook_not_configured",
    "rebind_required",
    "billing_expired",
    "renewal_due",
    "not_required",
    "unknown",
]
OnboardingOperationalPipelineStatusValue = Literal["pass", "warn", "fail"]
OnboardingOperationalStageStatusValue = Literal["pass", "warn", "fail", "skip"]
OnboardingReadinessStatusValue = Literal["pass", "warn", "fail"]
OnboardingReadinessHardGateStatusValue = Literal["pass", "fail"]


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


class ConsoleOnboardingScorecardCheck(BaseModel):
    id: OnboardingStepId
    required: bool
    passed: bool
    missing: list[str] = []


class ConsoleOnboardingDocumentIngestion(BaseModel):
    status: OnboardingDocumentIngestionStatusValue
    valid: bool
    source: OnboardingDocumentIngestionSourceValue
    missing_fields: list[str] = []
    critical_missing_fields: list[str] = []


class ConsoleOnboardingSlaControlLoop(BaseModel):
    status: OnboardingSlaControlLoopStatusValue
    reminder_1_minutes: int
    reminder_2_minutes: int
    escalation_timeout_minutes: int
    pending_total: int
    warning_total: int
    breached_total: int
    provider_status: OnboardingSlaProviderStatusValue
    provider_paid_until: Optional[str] = None
    provider_days_to_renewal: Optional[int] = None
    provider_alert_state: str = "unknown"
    active_incidents: list[str] = []
    recommended_actions: list[str] = []


class ConsoleOnboardingOperationalStage(BaseModel):
    id: str
    label: str
    owner_lane: str
    required: bool
    status: OnboardingOperationalStageStatusValue
    blockers: list[str] = []
    next_action: Optional[str] = None


class ConsoleOnboardingOperationalPipeline(BaseModel):
    status: OnboardingOperationalPipelineStatusValue
    blocked: bool
    current_stage_id: Optional[str] = None
    blockers: list[str] = []
    next_actions: list[str] = []
    stages: list[ConsoleOnboardingOperationalStage] = []


class ConsoleOnboardingReadinessDimension(BaseModel):
    id: str
    status: OnboardingReadinessStatusValue
    blocker_codes: list[str] = []
    next_action_codes: list[str] = []


class ConsoleOnboardingReadinessQuestion(BaseModel):
    code: str
    question: str
    blocking_go_live: bool = False


class ConsoleOnboardingReadinessHardGate(BaseModel):
    enforced: bool
    status: OnboardingReadinessHardGateStatusValue
    blocker_codes: list[str] = []


class ConsoleOnboardingReadinessKernel(BaseModel):
    status: OnboardingReadinessStatusValue
    blocker_codes: list[str] = []
    next_action_codes: list[str] = []
    auto_questions: list[ConsoleOnboardingReadinessQuestion] = []
    dimensions: list[ConsoleOnboardingReadinessDimension] = []
    shadow_hard_gate: ConsoleOnboardingReadinessHardGate


class ConsoleOnboardingScorecardResponse(BaseModel):
    branch_id: UUID
    status: OnboardingScorecardStatusValue
    ready: bool
    checks: list[ConsoleOnboardingScorecardCheck]
    missing: list[str] = []
    document_ingestion: Optional[ConsoleOnboardingDocumentIngestion] = None
    sla_control_loop: Optional[ConsoleOnboardingSlaControlLoop] = None
    operational_pipeline: Optional[ConsoleOnboardingOperationalPipeline] = None
    readiness_kernel: Optional[ConsoleOnboardingReadinessKernel] = None
    generated_at: str


class ConsoleOnboardingAdvanceRequest(BaseModel):
    branch_id: UUID
    step_id: OnboardingStepId


ConfirmationAction = Literal[
    "knowledge_rollback",
    "branch_deactivate",
    "integration_reconcile",
    "provider_ops_execute",
]
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
    role: ConsoleAgentRole
    name: Optional[str] = None
    is_active: Optional[bool] = True
    oidc_subject: Optional[str] = None
    sso_username: Optional[str] = None
    sso_password: Optional[str] = None
    sso_temp_password: Optional[bool] = True


class ConsoleAgentCreateResponse(BaseModel):
    agent: ConsoleAgent


class ConsoleAgentMembership(BaseModel):
    id: UUID
    agent_id: UUID
    agent_name: Optional[str] = None
    agent_client_id: Optional[UUID] = None
    scope: ConsoleMembershipScope
    company_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    role: ConsoleAgentRole
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConsoleMembershipListResponse(BaseModel):
    items: list[ConsoleAgentMembership]


class ConsoleMembershipCreateRequest(BaseModel):
    agent_id: UUID
    scope: ConsoleMembershipScope
    role: ConsoleAgentRole
    company_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    is_active: Optional[bool] = True


class ConsoleMembershipUpdateRequest(BaseModel):
    scope: Optional[ConsoleMembershipScope] = None
    role: Optional[ConsoleAgentRole] = None
    company_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    reason: Optional[str] = None


class ConsoleAgentLifecycleActionRequest(BaseModel):
    reason: str


class ConsoleAgentOidcRebindRequest(BaseModel):
    oidc_subject: str
    reason: str


class ConsoleAgentOidcRebindResponse(BaseModel):
    agent_id: UUID
    oidc_subject: str
    previous_oidc_subject: Optional[str] = None


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
    handover_meta: Optional[dict] = None
    handover_media_refs: Optional[list[dict]] = None
    handover_messages: Optional[list[dict]] = None
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
    total: Optional[int] = None


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


ConsoleBusinessSeverity = Literal["critical", "warn", "info"]
ConsoleBusinessStatus = Literal["healthy", "degraded", "unhealthy"]
ConsoleSubscriptionQuotaSource = Literal["company_billing_info", "client_config", "unknown"]
ConsoleSubscriptionAlertLevel = Literal["normal", "warning_80", "limit_100"]
ConsoleFactKind = Literal["fact", "estimate", "missing"]
ConsoleFactScope = Literal["system", "client", "branch"]
ConsoleOwnerMode = Literal["capture_leads", "stable_quality", "team_protection"]


class ConsoleMetricFactMeta(BaseModel):
    kind: ConsoleFactKind
    source: str
    as_of: Optional[str] = None
    scope: ConsoleFactScope = "client"
    sample_size: Optional[int] = None
    note: Optional[str] = None


class ConsoleBusinessActionItem(BaseModel):
    id: str
    title: str
    description: str
    href: str
    severity: ConsoleBusinessSeverity


ConsoleIncidentSeverity = Literal["critical", "warn", "info"]
ConsoleIncidentScope = Literal["fleet", "client", "branch"]
ConsoleIncidentReasonCode = Literal[
    "outbox_backlog",
    "provider_billing_blocked",
    "provider_unavailable",
    "provider_auth",
    "provider_rate_limited",
    "integration_degraded",
    "handover_backlog",
    "unknown",
]


class ConsoleIncidentAction(BaseModel):
    id: str
    title: str
    description: str
    href: Optional[str] = None
    job_type: Optional[Literal["outbox_process", "integration_reconcile", "heal", "metrics_snapshot"]] = None
    mode: Optional[Literal["dry_run", "execute"]] = None
    params: Optional[dict] = None
    dry_run_first: bool = True
    requires_confirmation: bool = False


class ConsoleIncidentItem(BaseModel):
    id: str
    scope: ConsoleIncidentScope
    severity: ConsoleIncidentSeverity
    title: str
    summary: str
    reason_code: ConsoleIncidentReasonCode
    reason_label: str
    source: str
    detected_at: str
    client_id: Optional[UUID] = None
    client_slug: Optional[str] = None
    branch_id: Optional[UUID] = None
    metrics: dict[str, str | int | float | bool | None] = {}
    actions: list[ConsoleIncidentAction] = []


class ConsoleIncidentSummary(BaseModel):
    total: int
    critical: int
    warn: int
    info: int


class ConsoleIncidentListResponse(BaseModel):
    generated_at: str
    scope: ConsoleIncidentScope
    summary: ConsoleIncidentSummary
    items: list[ConsoleIncidentItem]


class ConsoleBusinessSummaryResponse(BaseModel):
    generated_at: str
    status: ConsoleBusinessStatus
    status_label: str
    scheduled_visits_today: int
    arrived_visits_today: int
    no_show_visits_today: int
    cancelled_visits_today: int
    arrival_rate_percent: Optional[float] = None
    reminder_delivery_failures_today: int
    no_show_followup_pending: int
    outbox_backlog: int
    outbox_failed_24h: int
    pending_cases: int
    active_cases: int
    unresolved_cases: int
    oldest_unresolved_minutes: Optional[int] = None
    first_response_p90_seconds: Optional[float] = None
    actions: list[ConsoleBusinessActionItem] = []
    metric_meta: dict[str, ConsoleMetricFactMeta] = {}


class ConsoleSubscriptionEvidenceItem(BaseModel):
    outbox_id: UUID
    conversation_id: Optional[UUID] = None
    inbound_message_id: str
    created_at: str
    status: str
    provider_status: Optional[str] = None
    provider_message_id: Optional[str] = None


ConsoleSubscriptionMeterType = Literal["messages", "channels", "addon"]
ConsoleSubscriptionMeterStatus = Literal[
    "ok",
    "warning",
    "limit_reached",
    "over_limit",
    "not_included",
    "included_not_configured",
    "unknown",
]
ConsoleSubscriptionContractHealthStatus = Literal["ok", "partial", "missing"]


class ConsoleSubscriptionPlanDefaults(BaseModel):
    plan_name: str
    included_messages: int
    included_whatsapp_channels: int
    source: str
    reference_only: bool = True


class ConsoleSubscriptionContractGap(BaseModel):
    code: str
    message: str
    severity: ConsoleBusinessSeverity = "warn"


class ConsoleSubscriptionContractHealth(BaseModel):
    status: ConsoleSubscriptionContractHealthStatus = "missing"
    summary: str
    gaps: list[ConsoleSubscriptionContractGap] = []
    quota_source: ConsoleSubscriptionQuotaSource = "unknown"
    whatsapp_source: Literal[
        "company_billing_info",
        "client_config",
        "onboarding_contract",
        "unknown",
    ] = "unknown"
    payment_status_source: Literal["onboarding_contract", "unknown"] = "unknown"
    has_active_onboarding_contract: bool = False


class ConsoleSubscriptionMeterItem(BaseModel):
    key: str
    label: str
    meter_type: ConsoleSubscriptionMeterType
    included: Optional[int] = None
    used: Optional[int] = None
    remaining: Optional[int] = None
    status: ConsoleSubscriptionMeterStatus = "unknown"
    source: str
    note: Optional[str] = None


class ConsoleSubscriptionSummaryResponse(BaseModel):
    generated_at: str
    period_start: str
    period_end: str
    next_billing_date: str
    plan_name: Optional[str] = None
    contract_label: Optional[str] = None
    currency: Optional[str] = None
    monthly_quota: Optional[int] = None
    quota_source: ConsoleSubscriptionQuotaSource = "unknown"
    billable_messages: int
    remaining_quota: Optional[int] = None
    projected_month_total: Optional[int] = None
    usage_percent: Optional[float] = None
    projected_remaining_quota: Optional[int] = None
    projected_over_quota: bool = False
    projected_overage_messages: Optional[int] = None
    quota_alert_level: ConsoleSubscriptionAlertLevel = "normal"
    quota_alert_message: str
    overage_policy_message: str
    over_quota: bool = False
    payment_status: Literal["pending", "confirmed", "rejected", "unknown"] = "unknown"
    payment_confirmed_at: Optional[str] = None
    payment_status_source: Literal["onboarding_contract", "unknown"] = "unknown"
    payment_status_message: Optional[str] = None
    contract_health: ConsoleSubscriptionContractHealth
    plan_defaults: ConsoleSubscriptionPlanDefaults
    meters: list[ConsoleSubscriptionMeterItem] = []
    recommended_actions: list[ConsoleBusinessActionItem] = []
    evidence: list[ConsoleSubscriptionEvidenceItem] = []
    metric_meta: dict[str, ConsoleMetricFactMeta] = {}


class ConsoleDataTrustSummaryResponse(BaseModel):
    generated_at: str
    status: ConsoleBusinessStatus
    status_label: str
    metric_date: Optional[str] = None
    analytics_scope_limited: bool = False
    first_response_missing_total: Optional[int] = None
    escalation_meta_missing_total: Optional[int] = None
    intent_missing_total: Optional[int] = None
    knowledge_last_published_at: Optional[str] = None
    knowledge_stale_hours: Optional[int] = None
    audit_events_24h: int
    critical_audit_events_24h: int
    actions: list[ConsoleBusinessActionItem] = []
    metric_meta: dict[str, ConsoleMetricFactMeta] = {}


class ConsoleTeamManagerPerformanceItem(BaseModel):
    manager_name: str
    unresolved_cases: int
    pending_cases: int
    active_cases: int
    oldest_unresolved_minutes: Optional[int] = None
    avg_first_response_seconds_30d: Optional[float] = None


class ConsoleTeamPerformanceSummaryResponse(BaseModel):
    generated_at: str
    status: ConsoleBusinessStatus
    status_label: str
    metric_date: Optional[str] = None
    analytics_scope_limited: bool = False
    manager_median_response_seconds: Optional[float] = None
    first_response_p90_seconds: Optional[float] = None
    unresolved_cases: int
    unresolved_older_than_60m: int
    managers: list[ConsoleTeamManagerPerformanceItem] = []
    actions: list[ConsoleBusinessActionItem] = []
    metric_meta: dict[str, ConsoleMetricFactMeta] = {}


class ConsoleOwnerOperationSettingsPatch(BaseModel):
    reminder_1_minutes: int
    reminder_2_minutes: int
    escalation_timeout_minutes: int


class ConsoleOwnerOperationMetricSnapshot(BaseModel):
    outbox_backlog: int
    unresolved_older_than_60m: int
    manager_median_response_seconds: Optional[float] = None


class ConsoleOwnerOperationMetricDelta(BaseModel):
    baseline: Optional[float] = None
    current: Optional[float] = None
    delta: Optional[float] = None
    trend: Literal["up", "down", "stable", "unknown"] = "unknown"


class ConsoleOwnerOperationPreviewResponse(BaseModel):
    generated_at: str
    mode: ConsoleOwnerMode
    mode_label: str
    settings_patch: ConsoleOwnerOperationSettingsPatch
    current_settings: ConsoleOwnerOperationSettingsPatch
    baseline: ConsoleOwnerOperationMetricSnapshot
    warnings: list[str] = []
    metric_meta: dict[str, ConsoleMetricFactMeta] = {}


class ConsoleOwnerOperationApplyRequest(BaseModel):
    mode: ConsoleOwnerMode


class ConsoleOwnerOperationApplyResponse(BaseModel):
    success: bool
    operation_id: UUID
    mode: ConsoleOwnerMode
    mode_label: str
    applied_settings: ConsoleOwnerOperationSettingsPatch
    previous_settings: ConsoleOwnerOperationSettingsPatch
    baseline: ConsoleOwnerOperationMetricSnapshot
    applied_at: str
    impact_check_due_at: str
    metric_meta: dict[str, ConsoleMetricFactMeta] = {}


class ConsoleOwnerOperationRollbackRequest(BaseModel):
    operation_id: Optional[UUID] = None


class ConsoleOwnerOperationRollbackResponse(BaseModel):
    success: bool
    operation_id: UUID
    restored_settings: ConsoleOwnerOperationSettingsPatch
    rolled_back_at: str
    message: str


class ConsoleOwnerOperationImpactResponse(BaseModel):
    operation_id: UUID
    mode: ConsoleOwnerMode
    checked_at: str
    due_at: str
    summary: Literal["improved", "regressed", "mixed_or_stable"]
    baseline: ConsoleOwnerOperationMetricSnapshot
    current: ConsoleOwnerOperationMetricSnapshot
    metrics: dict[str, ConsoleOwnerOperationMetricDelta] = {}
    metric_meta: dict[str, ConsoleMetricFactMeta] = {}


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


class ConsoleReminderCounts(BaseModel):
    pending: int
    sent: int
    failed: int
    due_now: int
    overdue_15m: int


class ConsoleReminderErrorBucket(BaseModel):
    reason: str
    count: int


class ConsoleReminderItem(BaseModel):
    id: UUID
    appointment_id: UUID
    branch_id: UUID
    channel: str
    template: str
    run_at: str
    status: str
    attempt: int
    max_attempts: int
    next_attempt_at: Optional[str] = None
    last_error: Optional[str] = None
    dedupe_key: str
    created_at: str
    updated_at: str
    outbox_id: Optional[UUID] = None
    outbox_status: Optional[str] = None
    outbox_attempts: Optional[int] = None
    outbox_last_error: Optional[str] = None
    outbox_updated_at: Optional[str] = None


class ConsoleReminderListResponse(BaseModel):
    items: list[ConsoleReminderItem]
    cursor: Optional[str] = None
    has_more: bool
    counts: ConsoleReminderCounts
    error_buckets: list[ConsoleReminderErrorBucket] = []


class ConsoleReminderRetryRequest(BaseModel):
    ids: Optional[list[UUID]] = None
    limit: Optional[int] = 100
    status: Literal["failed", "pending", "all"] = "failed"
    confirm: bool = False


class ConsoleReminderRetryResponse(BaseModel):
    success: bool
    retried: int
    skipped: int
    matched: int


ConsoleOpsJobType = Literal["outbox_process", "integration_reconcile", "heal", "metrics_snapshot"]
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


ConsoleBranchChangeStatus = Literal["draft", "validated", "publish_failed", "published", "rolled_back"]


class ConsoleBranchChangeRecord(BaseModel):
    id: UUID
    branch_id: UUID
    status: ConsoleBranchChangeStatus
    reason: str
    draft_payload: dict
    diff_payload: dict
    validation_payload: Optional[dict] = None
    base_snapshot: dict
    published_snapshot: Optional[dict] = None
    rollback_snapshot: Optional[dict] = None
    publish_error: Optional[str] = None
    rollback_error: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    validated_at: Optional[str] = None
    published_at: Optional[str] = None
    rolled_back_at: Optional[str] = None


class ConsoleBranchChangeResponse(BaseModel):
    change: ConsoleBranchChangeRecord
    branch: Optional[ConsoleBranch] = None


class ConsoleBranchChangeListResponse(BaseModel):
    items: list[ConsoleBranchChangeRecord]
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


class ConsoleOnboardingBlueprintQuestionTemplate(BaseModel):
    code: str
    question: str
    blocking_go_live: bool = False


class ConsoleOnboardingBlueprint(BaseModel):
    id: str
    domain_slug: str
    label: str
    summary: str
    payload: CapabilitiesPayload
    go_live_blockers_profile: list[str] = []
    question_templates: list[ConsoleOnboardingBlueprintQuestionTemplate] = []


class ConsoleOnboardingBlueprintListResponse(BaseModel):
    items: list[ConsoleOnboardingBlueprint]


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


class ConsoleOnboardingAutopilotRequest(ConsoleRequestModel):
    company_id: Optional[UUID] = None
    company_name: Optional[StrictStr] = None
    client_id: Optional[UUID] = None
    client_slug: Optional[StrictStr] = None
    branch_id: Optional[UUID] = None
    branch_slug: Optional[StrictStr] = None
    branch_name: Optional[StrictStr] = None
    timezone: Optional[StrictStr] = None
    phone: StrictStr
    instance_id: StrictStr
    payment_status: Optional[Literal["pending", "confirmed", "rejected"]] = "pending"
    domain_slug: Optional[StrictStr] = None
    purchased: Optional[CapabilitiesPayload] = None
    purchased_services: Optional[list[OnboardingPurchasedService]] = None
    provider_binding: Optional[OnboardingProviderBindingPayload] = None
    client_data_text: Optional[StrictStr] = None
    client_data_json: Optional[dict] = None
    activate_branch: Optional[bool] = False
    auto_create_reference_pack: Optional[bool] = True
    auto_publish_knowledge: Optional[bool] = False


IntakeFieldStatus = Literal["unknown", "assumed", "confirmed"]
IntakeFieldPriority = Literal["critical", "high", "medium", "low"]
IntakeQualityStatus = Literal["pass", "fail", "warn", "skip"]


class ConsoleOnboardingIntakeFieldState(BaseModel):
    field: str
    status: IntakeFieldStatus
    priority: IntakeFieldPriority


class ConsoleOnboardingIntakeQuestion(BaseModel):
    field: str
    question: str
    priority: IntakeFieldPriority
    blocking_go_live: bool = False


class ConsoleOnboardingIntakeCompile(BaseModel):
    status: Literal["pass", "fail"]
    infra_valid: bool
    schema_version: Optional[str] = None
    hash: Optional[str] = None
    pack_index_hash: Optional[str] = None
    signal_graph_present: bool = False
    policy_bundle_present: bool = False
    errors: list[str] = []


class ConsoleOnboardingIntakeQualityDimension(BaseModel):
    id: str
    status: IntakeQualityStatus
    required: bool = True
    details: list[str] = []


class ConsoleOnboardingIntakeQualityMatrix(BaseModel):
    status: Literal["pass", "fail"]
    infra_valid: bool
    semantic_valid: bool
    required_fields_count: int
    missing_fields_count: int
    critical_missing_fields_count: int
    integrity_missing_count: int
    missing_fields: list[str] = []
    critical_missing_fields: list[str] = []
    integrity_missing: list[str] = []
    dimensions: list[ConsoleOnboardingIntakeQualityDimension] = []
    regressions: list[str] = []
    comparison_blocked: bool = False
    comparison_block_reason: Optional[str] = None


class ConsoleOnboardingAutopilotIntake(BaseModel):
    knowledge_tag: str
    draft_saved: bool
    published: bool
    published_version_id: Optional[UUID] = None
    missing_fields: list[str] = []
    missing_questions: list[str] = []
    field_states: list[ConsoleOnboardingIntakeFieldState] = []
    question_queue: list[ConsoleOnboardingIntakeQuestion] = []
    compile: Optional[ConsoleOnboardingIntakeCompile] = None
    quality_matrix: Optional[ConsoleOnboardingIntakeQualityMatrix] = None
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
    client_id: UUID
    client_slug: str
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
    integration_state: Literal["ok", "degraded"] = "ok"
    integration_reason: Optional[str] = None
    integration_checked_at: Optional[str] = None
    integration_degraded_at: Optional[str] = None
    integration_recovered_at: Optional[str] = None
    provider_binding_provider: Optional[str] = None
    provider_binding_instance_id: Optional[str] = None
    provider_binding_webhook_status: Optional[Literal["configured", "pending", "rebind_required"]] = None
    provider_binding_paid_until: Optional[str] = None
    provider_binding_owner: Optional[str] = None
    provider_binding_next_renewal_at: Optional[str] = None
    provider_binding_last_rebind_at: Optional[str] = None
    provider_binding_rebind_required: Optional[bool] = None
    provider_binding_alert_state: Literal["ok", "warn", "critical", "unknown"] = "unknown"
    provider_binding_notes: Optional[str] = None
    provider_binding_payment_status: Literal["pending", "confirmed", "rejected", "unknown"] = "unknown"
    provider_binding_payment_confirmed_at: Optional[str] = None
    provider_binding_expiry_status: Literal["ok", "expiring_soon", "expired", "unknown"] = "unknown"
    provider_binding_days_until_expiry: Optional[int] = None
    drift_issues: list[str] = []
    status: Literal["ok", "warn", "error"]


ConsoleProviderOpsAction = Literal[
    "integration_reconcile",
    "provider_start_rebind",
    "provider_complete_rebind",
    "provider_renewal_confirmed",
    "provider_webhook_updated",
    "provider_send_reminder",
]
ConsoleProviderOpsQueuePriority = Literal["p0", "p1", "p2"]
ConsoleProviderLifecycleSlaState = Literal["none", "on_track", "due_soon", "overdue"]


class ConsoleProviderOpsQueueItem(BaseModel):
    client_id: UUID
    client_slug: str
    branch_id: UUID
    branch_slug: str
    branch_name: str
    priority: ConsoleProviderOpsQueuePriority
    recommended_action: ConsoleProviderOpsAction
    reasons: list[str] = []
    requires_confirmation: bool = True
    provider_binding_owner: Optional[str] = None
    provider_binding_next_renewal_at: Optional[str] = None
    provider_binding_last_rebind_at: Optional[str] = None
    provider_binding_alert_state: Literal["ok", "warn", "critical", "unknown"] = "unknown"
    provider_binding_expiry_status: Literal["ok", "expiring_soon", "expired", "unknown"] = "unknown"
    provider_binding_days_until_expiry: Optional[int] = None
    provider_binding_rebind_required: Optional[bool] = None
    generated_at: Optional[str] = None


class ConsoleProviderLifecycleItem(BaseModel):
    client_id: UUID
    client_slug: str
    branch_id: UUID
    branch_slug: str
    branch_name: str
    company_id: Optional[UUID] = None
    company_name: Optional[str] = None
    branch_phone: Optional[str] = None
    status: Literal["ok", "warn", "error"]
    whatsapp_status: Literal[
        "ok",
        "inactive",
        "missing_instance_id",
        "instance_id_mismatch",
        "invalid_webhook_url",
        "no_recent_inbound",
    ]
    integration_state: Literal["ok", "degraded"] = "ok"
    last_inbound_at: Optional[str] = None
    instance_id: Optional[str] = None
    provider_binding_provider: Optional[str] = None
    provider_binding_instance_id: Optional[str] = None
    provider_binding_webhook_status: Optional[Literal["configured", "pending", "rebind_required"]] = None
    provider_binding_paid_until: Optional[str] = None
    provider_binding_owner: Optional[str] = None
    provider_binding_next_renewal_at: Optional[str] = None
    provider_binding_last_rebind_at: Optional[str] = None
    provider_binding_rebind_required: Optional[bool] = None
    provider_binding_alert_state: Literal["ok", "warn", "critical", "unknown"] = "unknown"
    provider_binding_expiry_status: Literal["ok", "expiring_soon", "expired", "unknown"] = "unknown"
    provider_binding_days_until_expiry: Optional[int] = None
    next_action: Optional[ConsoleProviderOpsAction] = None
    priority: Optional[ConsoleProviderOpsQueuePriority] = None
    blockers: list[str] = []
    sla_deadline_at: Optional[str] = None
    sla_state: ConsoleProviderLifecycleSlaState = "none"
    generated_at: Optional[str] = None


class ConsoleProviderLifecycleListResponse(BaseModel):
    stale_after_minutes: int
    cursor: Optional[str] = None
    has_more: bool = False
    total_in_scope: int = 0
    items: list[ConsoleProviderLifecycleItem]


class ConsoleIntegrationsListResponse(BaseModel):
    stale_after_minutes: int
    cursor: Optional[str] = None
    has_more: bool = False
    total_in_scope: int = 0
    items: list[ConsoleBranchIntegrationStatus]
    provider_ops_queue: list[ConsoleProviderOpsQueueItem] = []


class ConsoleIntegrationBranchActionRequest(BaseModel):
    action: ConsoleProviderOpsAction = "integration_reconcile"
    mode: ConsoleOpsJobMode = "dry_run"
    confirmation_id: Optional[UUID] = None
    owner: Optional[str] = None
    notes: Optional[str] = None
    paid_until: Optional[str] = None
    next_renewal_at: Optional[str] = None
    instance_id: Optional[str] = None
    webhook_status: Optional[Literal["configured", "pending", "rebind_required"]] = None


class ConsoleIntegrationBranchActionResponse(BaseModel):
    branch_id: UUID
    action: ConsoleProviderOpsAction
    mode: ConsoleOpsJobMode
    result: dict


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
    skip_preflight_check: bool = False


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
