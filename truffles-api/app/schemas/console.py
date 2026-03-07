from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr

from app.schemas.capabilities import CapabilitiesPayload, CapabilityPolicyOverrides
from app.schemas.compliance_policy import CompliancePolicyPayload
from app.schemas.onboarding_contract import (
    OnboardingContractPayload,
    OnboardingProviderBindingPayload,
)
from app.schemas.sla_profile import SlaProfilePayload


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
    reference_branch_ids: Optional[list[UUID]] = None
    reference_branch_reason: Optional[str] = None


class ConsoleBranch(BaseModel):
    id: UUID
    client_id: Optional[UUID] = None
    company_id: Optional[UUID] = None
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


class ConsoleOnboardingThroughputMetrics(BaseModel):
    window_hours: int = 24
    approved_branches_total: int = 0
    first_pass_approved_branches: int = 0
    time_to_go_live_median_hours: Optional[float] = None
    blocker_age_p95_hours: Optional[float] = None
    first_pass_go_live_rate_pct: Optional[float] = None
    incident_reopen_rate_24h_pct: Optional[float] = None


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
    onboarding_throughput: Optional[ConsoleOnboardingThroughputMetrics] = None


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
    reference_branch_ids: list[UUID] = []
    reference_branch_reason: Optional[str] = None
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


class ConsoleTenantsPortfolioResponse(BaseModel):
    generated_at: str
    clients: ConsoleClientListResponse
    fleet_attention: ConsoleFleetAttentionResponse


class ConsoleTenantsCompanyCockpitResponse(BaseModel):
    generated_at: str
    company_id: UUID
    selected_client_id: Optional[UUID] = None
    clients: ConsoleClientListResponse
    branches: ConsoleBranchListResponse


ConsoleTenantsSnapshotWorkspaceMode = Literal["portfolio", "onboarding", "changes", "decommission"]
ConsoleTenantsSnapshotLifecycleMode = Literal["active", "archived", "all"]
ConsoleTenantsSnapshotKpiId = Literal[
    "onboardingCoverage",
    "goLiveReadiness",
    "serviceStability",
    "decommissionShare",
    "changeFailure",
    "rollbackShare",
    "blockedSignals",
]
ConsoleTenantsSnapshotKpiStatus = Literal["ok", "warn", "critical"]


class ConsoleTenantsWeeklySnapshotKpi(BaseModel):
    model_config = ConfigDict(extra="forbid")

    onboardingCoverage: float
    goLiveReadiness: float
    serviceStability: float
    decommissionShare: float
    changeFailure: float
    rollbackShare: float
    blockedSignals: int


class ConsoleTenantsWeeklySnapshotDrilldownItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: ConsoleTenantsSnapshotKpiId
    status: ConsoleTenantsSnapshotKpiStatus
    value: float
    reason: str


class ConsoleTenantsWeeklySnapshotAttentionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activeClientsTotal: int
    highRiskClients: int
    mediumRiskClients: int
    outboxFailed24hTotal: int
    pendingHandoversTotal: int


class ConsoleTenantsWeeklySnapshotPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generatedAt: str
    sourceWindow: int
    workspaceMode: ConsoleTenantsSnapshotWorkspaceMode
    lifecycleMode: ConsoleTenantsSnapshotLifecycleMode
    kpi: ConsoleTenantsWeeklySnapshotKpi
    drilldown: list[ConsoleTenantsWeeklySnapshotDrilldownItem]
    attentionSummary: ConsoleTenantsWeeklySnapshotAttentionSummary


class ConsoleTenantsWeeklySnapshotRecord(BaseModel):
    id: UUID
    created_at: str
    client_id: UUID
    week_key: str
    snapshot: ConsoleTenantsWeeklySnapshotPayload
    snapshot_schema_version: str = "v1"
    actor_name: Optional[str] = None


class ConsoleTenantsWeeklySnapshotListResponse(BaseModel):
    items: list[ConsoleTenantsWeeklySnapshotRecord]
    cursor: Optional[str] = None
    has_more: bool
    storage_mode: Literal["table", "audit_fallback"] = "table"
    schema_versions: dict[str, int] = Field(default_factory=dict)


class ConsoleTenantsWeeklySnapshotCreateRequest(ConsoleRequestModel):
    client_id: UUID
    week_key: StrictStr
    snapshot: ConsoleTenantsWeeklySnapshotPayload


class ConsoleTenantsWeeklySnapshotCreateResponse(BaseModel):
    item: ConsoleTenantsWeeklySnapshotRecord


class ConsoleTenantsSensitiveAccessAuditRequest(ConsoleRequestModel):
    branch_id: UUID
    field: StrictStr
    action: Literal["reveal", "copy"]
    context: Optional[StrictStr] = None


class ConsoleTenantsSensitiveAccessAuditResponse(BaseModel):
    ok: bool = True
    audit_id: UUID


ConsoleMarketingCampaignStatus = Literal[
    "draft",
    "ready",
    "executed",
    "paused",
    "in_review",
    "approved",
    "scheduled",
    "running",
    "completed",
    "cancelled",
    "failed",
]
ConsoleMarketingCampaignStatusV2 = Literal[
    "draft",
    "in_review",
    "approved",
    "scheduled",
    "running",
    "paused",
    "completed",
    "cancelled",
    "failed",
]
ConsoleMarketingAudienceMode = Literal["branch_active_conversations"]
ConsoleMarketingDeliveryStatus = Literal["queued", "sent", "failed", "replied"]
ConsoleMarketingSegmentCode = Literal[
    "reactivation_30_120",
    "no_show_recovery_14d",
    "engaged_no_booking_7d",
]


class ConsoleMarketingCampaign(BaseModel):
    id: UUID
    client_id: UUID
    branch_id: UUID
    name: str
    message_text: str
    status: ConsoleMarketingCampaignStatus
    status_v2: ConsoleMarketingCampaignStatusV2 = "draft"
    segment_code: ConsoleMarketingSegmentCode = "reactivation_30_120"
    segment_params: dict[str, Any] = {}
    segment_summary: Optional[str] = None
    audience_mode: ConsoleMarketingAudienceMode
    preview_total: int = 0
    preflight_valid: bool = False
    preflight_snapshot: Optional[dict] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[str] = None
    requested_review_at: Optional[str] = None
    run_started_at: Optional[str] = None
    run_completed_at: Optional[str] = None
    last_preview_at: Optional[str] = None
    executed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConsoleMarketingCampaignCreateRequest(ConsoleRequestModel):
    branch_id: UUID
    name: StrictStr
    message_text: StrictStr
    segment_code: ConsoleMarketingSegmentCode = "reactivation_30_120"
    segment_params: Optional[dict[str, Any]] = None
    audience_mode: ConsoleMarketingAudienceMode = "branch_active_conversations"


class ConsoleMarketingCampaignCreateResponse(BaseModel):
    campaign: ConsoleMarketingCampaign


class ConsoleMarketingCampaignUpdateRequest(ConsoleRequestModel):
    name: Optional[StrictStr] = None
    message_text: Optional[StrictStr] = None
    segment_code: Optional[ConsoleMarketingSegmentCode] = None
    segment_params: Optional[dict[str, Any]] = None
    reason: Optional[StrictStr] = None


class ConsoleMarketingCampaignListResponse(BaseModel):
    items: list[ConsoleMarketingCampaign]


class ConsoleMarketingCampaignPreviewRequest(ConsoleRequestModel):
    sample_limit: Optional[int] = 5


class ConsoleMarketingAudienceFunnel(BaseModel):
    candidate_count: int = 0
    matched_count: int = 0
    segment_excluded_count: int = 0
    eligible_count: int = 0
    suppressed_count: int = 0
    suppression_reason_counts: dict[str, int] = {}


class ConsoleMarketingSegmentEditableField(BaseModel):
    key: str
    label: str
    type: Literal["int", "bool"]
    min: Optional[int] = None
    max: Optional[int] = None
    step: Optional[int] = None


class ConsoleMarketingSegmentDefinition(BaseModel):
    code: ConsoleMarketingSegmentCode
    label: str
    short_label: str
    description: str
    defaults: dict[str, Any] = {}
    summary: str
    editable_fields: list[ConsoleMarketingSegmentEditableField] = []


class ConsoleMarketingSegmentCatalogResponse(BaseModel):
    items: list[ConsoleMarketingSegmentDefinition]


class ConsoleMarketingCampaignPreviewResponse(BaseModel):
    campaign_id: UUID
    branch_id: UUID
    audience_mode: ConsoleMarketingAudienceMode
    estimated_recipients: int
    eligible_count: int = 0
    suppressed_count: int = 0
    segment_params: dict[str, Any] = {}
    segment_summary: Optional[str] = None
    sample_conversation_ids: list[UUID]
    sample_recipient_jids: list[str]
    funnel: ConsoleMarketingAudienceFunnel


class ConsoleMarketingCampaignExecuteRequest(ConsoleRequestModel):
    confirm_send: bool
    max_recipients: Optional[int] = None


class ConsoleMarketingCampaignExecuteResponse(BaseModel):
    campaign_id: UUID
    queued_count: int
    skipped_count: int
    status: Literal["queued", "skipped"]


class ConsoleMarketingDeliverySample(BaseModel):
    delivery_id: UUID
    conversation_id: Optional[UUID] = None
    recipient_jid: Optional[str] = None
    status: ConsoleMarketingDeliveryStatus
    outbox_status: Optional[str] = None
    last_error: Optional[str] = None
    updated_at: Optional[str] = None


class ConsoleMarketingCampaignDiagnosticsResponse(BaseModel):
    campaign_id: UUID
    queued_count: int
    sent_count: int
    failed_count: int
    replied_count: int
    total_count: int
    failure_classes: dict[str, int] = {}
    retryable_failed_count: int = 0
    permanent_failed_count: int = 0
    sample_failed: list[ConsoleMarketingDeliverySample]


class ConsoleMarketingCampaignRetryRequest(ConsoleRequestModel):
    confirm_retry: bool
    limit: Optional[int] = 100


class ConsoleMarketingCampaignRetryResponse(BaseModel):
    campaign_id: UUID
    retried_count: int
    skipped_count: int
    skipped_permanent: int = 0


class ConsoleMarketingCampaignAudienceRequest(ConsoleRequestModel):
    include_suppressed: bool = True
    limit: int = 100


class ConsoleMarketingCampaignRecipient(BaseModel):
    id: UUID
    campaign_id: UUID
    recipient_jid: str
    user_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    segment_code: ConsoleMarketingSegmentCode
    reason_codes: list[str] = []
    reason_hints: list[str] = []
    suppressed: bool = False
    suppression_reasons: list[str] = []
    suppression_hints: list[str] = []
    updated_at: Optional[str] = None


class ConsoleMarketingCampaignAudienceResponse(BaseModel):
    campaign_id: UUID
    total_count: int
    eligible_count: int
    suppressed_count: int
    items: list[ConsoleMarketingCampaignRecipient]


class ConsoleMarketingCampaignPreflightResponse(BaseModel):
    campaign_id: UUID
    generated_at: str
    preflight_valid: bool
    blocked_reasons: list[str] = []
    outbox_health_status: str
    outbox_pending: int = 0
    outbox_failed_24h: int = 0
    provider_billing_blocked: bool = False
    provider_billing_blocked_count: int = 0
    audience_total: int = 0
    eligible_count: int = 0
    suppressed_count: int = 0
    segment_params: dict[str, Any] = {}
    segment_summary: Optional[str] = None
    preview_stats: Optional[ConsoleMarketingAudienceFunnel] = None
    template_gate_enabled: bool = False
    template_state: Optional[str] = None
    template_ok: bool = True


class ConsoleMarketingCampaignLifecycleActionRequest(ConsoleRequestModel):
    reason: Optional[StrictStr] = None


ConsoleMacroActionType = Literal[
    "take_case",
    "resolve_case",
    "return_to_bot",
    "reopen_case",
    "snooze_case",
]


class ConsoleMacroAction(ConsoleRequestModel):
    type: ConsoleMacroActionType
    minutes: Optional[int] = None
    reason: Optional[StrictStr] = None


class ConsoleMacro(BaseModel):
    id: UUID
    scope: Literal["personal", "team"]
    label: str
    body: str
    action: Optional[ConsoleMacroAction] = None
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConsoleMacroListResponse(BaseModel):
    items: list[ConsoleMacro]


class ConsoleMacroCreateRequest(BaseModel):
    scope: Literal["personal", "team"]
    label: str
    body: str
    action: Optional[ConsoleMacroAction] = None
    is_active: Optional[bool] = True


class ConsoleMacroCreateResponse(BaseModel):
    macro: ConsoleMacro


class ConsoleMacroUpdateRequest(BaseModel):
    label: Optional[str] = None
    body: Optional[str] = None
    action: Optional[ConsoleMacroAction] = None
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


class ConsoleCaseBookingSummary(BaseModel):
    booking_id: UUID
    status: str
    start_at: Optional[str] = None
    specialist_name: Optional[str] = None
    service_type: Optional[str] = None
    needs_action: bool = False
    attention_reason: Optional[str] = None
    no_show_followup_done: bool = False
    no_show_followup_result: Optional[str] = None
    operator_summary: str


class ConsoleCase(BaseModel):
    id: UUID
    conversation_id: UUID
    status: str
    business_status_code: Optional[str] = None
    business_status_label: Optional[str] = None
    trigger_type: str
    trigger_value: Optional[str] = None
    context_summary: Optional[str] = None
    user_message: Optional[str] = None
    assigned_to_id: Optional[str] = None
    assigned_to_name: Optional[str] = None
    first_response_at: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution_time_seconds: Optional[int] = None
    branch_id: Optional[UUID] = None
    channel: Optional[str] = None
    created_at: str
    sla_status: Optional[str] = "ok"  # ok, warning, breached
    sla_action_state: Optional[str] = None  # reply_due, overdue, waiting_client, delivery_issue, pending_outbox, resolved
    sla_overdue_minutes: Optional[int] = None
    priority_tier: Optional[str] = None  # low, normal, high, urgent
    attention_reason: Optional[str] = None
    target_response_at: Optional[str] = None
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
    # Human lock (bot pause)
    human_lock_active: Optional[bool] = None
    human_lock_until: Optional[str] = None
    human_lock_remaining_seconds: Optional[int] = None
    human_lock_source: Optional[str] = None
    human_lock_reason: Optional[str] = None
    human_lock_by: Optional[str] = None
    # Case snooze
    snoozed_until: Optional[str] = None
    snoozed_reason: Optional[str] = None
    snoozed_by: Optional[str] = None
    # Telegram trail (for escalation visibility)
    telegram_trail: Optional[ConsoleTelegramTrail] = None
    # Linked booking semantic summary
    booking_summary: Optional[ConsoleCaseBookingSummary] = None


class ConsoleCaseListResponse(BaseModel):
    items: list[ConsoleCase]
    cursor: Optional[str] = None
    has_more: bool
    total: Optional[int] = None


class ConsoleSyncStatus(BaseModel):
    status: Literal["ok", "skipped", "failed"]
    detail: Optional[str] = None
    operator_message: Optional[str] = None


class ConsoleCaseActionSync(BaseModel):
    telegram: Optional[ConsoleSyncStatus] = None
    client_notify: Optional[ConsoleSyncStatus] = None


ConsoleCaseRoutingPolicyType = Literal["least_open_cases"]


class ConsoleCaseRoutingDecision(BaseModel):
    policy: ConsoleCaseRoutingPolicyType
    recommended_agent_id: UUID
    recommended_agent_name: str
    recommended_open_case_count: int = 0
    current_agent_id: Optional[UUID] = None
    current_agent_name: Optional[str] = None
    current_open_case_count: Optional[int] = None
    will_reassign: bool = True
    reason_code: str
    reason_summary: str


class ConsoleCaseActionResponse(BaseModel):
    success: bool
    case: ConsoleCase
    sync: Optional[ConsoleCaseActionSync] = None
    routing: Optional[ConsoleCaseRoutingDecision] = None


class ConsoleMacroExecuteRequest(ConsoleRequestModel):
    case_id: UUID


class ConsoleMacroExecuteResponse(BaseModel):
    success: bool
    macro: ConsoleMacro
    case: ConsoleCase
    sync: Optional[ConsoleCaseActionSync] = None


class ConsoleCaseAssigneeOption(BaseModel):
    agent_id: UUID
    agent_name: str
    role: str
    branch_id: Optional[UUID] = None
    is_current: bool = False
    open_case_count: int = 0


class ConsoleCaseAssigneeListResponse(BaseModel):
    items: list[ConsoleCaseAssigneeOption]
    routing: Optional[ConsoleCaseRoutingDecision] = None


class ConsoleCaseReassignRequest(ConsoleRequestModel):
    agent_id: Optional[UUID] = None
    mode: Literal["manual", "policy"] = "manual"
    policy: Optional[ConsoleCaseRoutingPolicyType] = None


class ConsoleCaseSnoozeRequest(ConsoleRequestModel):
    minutes: int = 30
    reason: Optional[StrictStr] = None


ConsoleCaseBulkActionType = Literal["reassign", "snooze", "route"]


class ConsoleCaseBulkActionRequest(ConsoleRequestModel):
    action: ConsoleCaseBulkActionType
    case_ids: list[UUID]
    agent_id: Optional[UUID] = None
    policy: Optional[ConsoleCaseRoutingPolicyType] = None
    minutes: Optional[int] = None
    reason: Optional[StrictStr] = None


class ConsoleCaseBulkActionResult(BaseModel):
    case_id: UUID
    status: Literal["processed", "skipped", "failed"]
    code: str
    message: Optional[str] = None
    case: Optional[ConsoleCase] = None
    routing: Optional[ConsoleCaseRoutingDecision] = None


class ConsoleCaseBulkActionResponse(BaseModel):
    success: bool
    action: ConsoleCaseBulkActionType
    requested_count: int
    processed_count: int
    skipped_count: int
    failed_count: int
    items: list[ConsoleCaseBulkActionResult]


class ConsoleMessageListResponse(BaseModel):
    items: list[ConsoleMessage]
    cursor: Optional[str] = None
    has_more: bool


class ConsoleManagerMessageRequest(BaseModel):
    content: str
    pause_enabled: bool = True
    pause_minutes: int = 30
    pause_reason: Optional[StrictStr] = None


class ConsoleManagerMessageResponse(BaseModel):
    success: bool
    message: ConsoleMessage


ConsoleOutreachDeliveryStatus = Literal["queued", "delivered", "failed"]


class ConsoleOutreachMessageRequest(ConsoleRequestModel):
    destination: StrictStr
    content: StrictStr
    conversation_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    pause_bot_minutes: Optional[int] = 30
    pause_reason: Optional[StrictStr] = None


class ConsoleOutreachMessageResponse(BaseModel):
    success: bool
    delivery_status: ConsoleOutreachDeliveryStatus
    remote_jid: Optional[str] = None
    conversation_id: Optional[UUID] = None
    case_id: Optional[UUID] = None
    case_created: Optional[bool] = None
    outbox_enqueued: Optional[bool] = None
    lock_until: Optional[str] = None
    message: Optional[ConsoleMessage] = None
    error_code: Optional[str] = None


class ConsoleHumanLockPauseRequest(ConsoleRequestModel):
    minutes: int = 30
    reason: Optional[StrictStr] = None


class ConsoleHumanLockStatus(BaseModel):
    active: bool
    remote_jid: Optional[str] = None
    lock_until: Optional[str] = None
    remaining_seconds: Optional[int] = None
    source: Optional[str] = None
    reason: Optional[str] = None
    locked_by_name: Optional[str] = None
    lock_scope: Optional[str] = None


class ConsoleHumanLockStatusResponse(BaseModel):
    success: bool
    status: ConsoleHumanLockStatus


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
ConsoleIncidentState = Literal["open", "in_progress", "resolved"]
ConsoleIncidentReasonCode = Literal[
    "outbox_backlog",
    "provider_billing_blocked",
    "provider_invalid_recipient",
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
    job_type: Optional[
        Literal[
            "outbox_process",
            "integration_reconcile",
            "heal",
            "metrics_snapshot",
            "incident_state",
            "compliance_lifecycle",
        ]
    ] = None
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
    incident_state: ConsoleIncidentState = "open"
    incident_state_updated_at: Optional[str] = None
    incident_state_owner: Optional[str] = None
    incident_state_due_at: Optional[str] = None
    incident_state_note: Optional[str] = None
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


ConsoleOpsJobType = Literal[
    "outbox_process",
    "integration_reconcile",
    "heal",
    "metrics_snapshot",
    "incident_state",
    "compliance_lifecycle",
]
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


class ConsoleAdminControlTowerOverviewSummary(BaseModel):
    active_clients_total: int
    clients_with_attention: int
    high_risk_clients: int
    incidents_total: int
    incidents_critical: int
    incidents_warn: int
    incidents_info: int
    ops_jobs_total_24h: int
    ops_jobs_failed_24h: int


class ConsoleAdminControlTowerOverviewResponse(BaseModel):
    generated_at: str
    stale_after_minutes: int
    attention_limit: int
    incident_limit: int
    ops_jobs_limit: int
    summary: ConsoleAdminControlTowerOverviewSummary
    fleet_attention: ConsoleFleetAttentionResponse
    incidents: ConsoleIncidentListResponse
    recent_ops_jobs: list[ConsoleOpsJobRecord]
    ops_job_catalog: list[ConsoleOpsJobDefinition]


class ConsoleAdminControlTowerIssueCount(BaseModel):
    code: str
    count: int


ConsoleAdminControlTowerActionPriority = Literal["p0", "p1", "p2"]
ConsoleAdminControlTowerActionSource = Literal["incident", "provider_ops", "readiness"]
ConsoleAdminControlTowerActionKind = Literal["navigate", "ops_job", "provider_action"]


class ConsoleAdminControlTowerActionItem(BaseModel):
    id: str
    priority: ConsoleAdminControlTowerActionPriority
    source: ConsoleAdminControlTowerActionSource
    kind: ConsoleAdminControlTowerActionKind
    title: str
    description: str
    reasons: list[str] = []
    href: Optional[str] = None
    incident_id: Optional[str] = None
    client_id: Optional[UUID] = None
    client_slug: Optional[str] = None
    branch_id: Optional[UUID] = None
    branch_slug: Optional[str] = None
    branch_name: Optional[str] = None
    job_type: Optional[ConsoleOpsJobType] = None
    mode: Optional[ConsoleOpsJobMode] = None
    params: Optional[dict] = None
    provider_action: Optional[str] = None
    requires_confirmation: bool = False
    evidence_links: list[str] = []


class ConsoleAdminControlTowerActionCenterSummary(BaseModel):
    total_actions: int
    p0_actions: int
    p1_actions: int
    p2_actions: int
    incident_actions: int
    provider_ops_actions: int
    readiness_actions: int


class ConsoleAdminControlTowerActionCenterResponse(BaseModel):
    generated_at: str
    stale_after_minutes: int
    limit: int
    include_p2: bool = True
    summary: ConsoleAdminControlTowerActionCenterSummary
    top_reasons: list[ConsoleAdminControlTowerIssueCount] = []
    items: list[ConsoleAdminControlTowerActionItem]


ConsoleAdminControlTowerMigrationWaveId = Literal["canary", "cohort", "fleet"]
ConsoleAdminControlTowerMigrationWaveGate = Literal["go", "hold"]
ConsoleAdminControlTowerMigrationSignalStatus = Literal["pass", "warn", "fail"]
ConsoleAdminControlTowerMigrationDecision = Literal["promote", "hold"]


class ConsoleAdminControlTowerMigrationWave(BaseModel):
    wave: ConsoleAdminControlTowerMigrationWaveId
    gate: ConsoleAdminControlTowerMigrationWaveGate
    reason: str
    candidate_clients_total: int
    candidate_branches_total: int
    blockers_total: int
    rollback_triggers: list[str] = []
    top_blockers: list[ConsoleAdminControlTowerIssueCount] = []


class ConsoleAdminControlTowerMigrationSignal(BaseModel):
    code: str
    status: ConsoleAdminControlTowerMigrationSignalStatus
    value: int
    threshold: int
    note: Optional[str] = None


class ConsoleAdminControlTowerPromotionAction(BaseModel):
    id: str
    wave: ConsoleAdminControlTowerMigrationWaveId
    gate: ConsoleAdminControlTowerMigrationWaveGate
    priority: ConsoleAdminControlTowerActionPriority
    source: ConsoleAdminControlTowerActionSource
    kind: ConsoleAdminControlTowerActionKind
    title: str
    description: str
    reasons: list[str] = []
    href: Optional[str] = None
    job_type: Optional[ConsoleOpsJobType] = None
    mode: Optional[ConsoleOpsJobMode] = None
    params: Optional[dict] = None
    evidence_links: list[str] = []


class ConsoleAdminControlTowerMigrationProgramSummary(BaseModel):
    active_clients_total: int
    total_branches: int
    ready_branches: int
    blocked_branches: int
    p0_actions: int
    p1_actions: int
    p2_actions: int
    waves_go: int
    waves_hold: int


class ConsoleAdminControlTowerMigrationProgramResponse(BaseModel):
    generated_at: str
    stale_after_minutes: int
    limit: int
    include_p2: bool = True
    summary: ConsoleAdminControlTowerMigrationProgramSummary
    waves: list[ConsoleAdminControlTowerMigrationWave]
    signals: list[ConsoleAdminControlTowerMigrationSignal] = []
    promotion_actions: list[ConsoleAdminControlTowerPromotionAction] = []


class ConsoleAdminControlTowerMigrationWaveDetailResponse(BaseModel):
    generated_at: str
    stale_after_minutes: int
    limit: int
    include_p2: bool = True
    wave: ConsoleAdminControlTowerMigrationWaveId
    decision: ConsoleAdminControlTowerMigrationDecision
    reason: str
    summary: ConsoleAdminControlTowerMigrationProgramSummary
    wave_state: ConsoleAdminControlTowerMigrationWave
    signals: list[ConsoleAdminControlTowerMigrationSignal] = []
    promotion_actions_total: int
    promotion_actions: list[ConsoleAdminControlTowerPromotionAction] = []


class ConsoleAdminControlTowerReadinessItem(BaseModel):
    company_id: Optional[UUID] = None
    company_name: Optional[str] = None
    client_id: UUID
    client_slug: str
    branch_id: UUID
    branch_slug: str
    branch_name: str
    current_step: OnboardingStepId
    scorecard_status: OnboardingScorecardStatusValue
    readiness_status: OnboardingReadinessStatusValue
    hard_gate_status: OnboardingReadinessHardGateStatusValue
    ready: bool
    go_live_state: str
    integration_state: Literal["ok", "degraded"] = "ok"
    missing: list[str] = []
    hard_gate_blockers: list[str] = []


class ConsoleAdminControlTowerReadinessSummary(BaseModel):
    total_branches: int
    ready_branches: int
    blocked_branches: int
    hard_gate_failed_branches: int
    go_live_draft_branches: int
    go_live_approved_branches: int
    go_live_rejected_branches: int
    degraded_branches: int


class ConsoleAdminControlTowerReadinessBoardResponse(BaseModel):
    generated_at: str
    limit: int
    include_ready: bool = False
    summary: ConsoleAdminControlTowerReadinessSummary
    top_blockers: list[ConsoleAdminControlTowerIssueCount] = []
    items: list[ConsoleAdminControlTowerReadinessItem]


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


class ConsolePolicyVersionRecord(BaseModel):
    id: UUID
    client_id: UUID
    branch_id: Optional[UUID] = None
    scope: Literal["client", "branch"]
    status: Literal["published", "archived"]
    schema_version: str
    version_number: int
    payload: CapabilityPolicyOverrides
    reason: Optional[str] = None
    source_version_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    published_by: Optional[UUID] = None
    published_at: Optional[str] = None


class ConsolePolicyRegistryResponse(BaseModel):
    client_id: UUID
    scope: Literal["client", "branch"]
    branch_id: Optional[UUID] = None
    active: Optional[ConsolePolicyVersionRecord] = None
    history: list[ConsolePolicyVersionRecord] = []


class ConsolePolicyRegistryPublishRequest(BaseModel):
    scope: Literal["client", "branch"]
    branch_id: Optional[UUID] = None
    schema_version: Optional[str] = None
    reason: str
    payload: CapabilityPolicyOverrides


class ConsolePolicyRegistryRollbackRequest(BaseModel):
    scope: Literal["client", "branch"]
    branch_id: Optional[UUID] = None
    target_version_id: UUID
    reason: str


class ConsolePolicyRegistryMutationResponse(BaseModel):
    success: bool
    record: ConsolePolicyVersionRecord
    from_version_id: Optional[UUID] = None


class ConsoleCompliancePolicyVersionRecord(BaseModel):
    id: UUID
    scope: Literal["global", "domain", "client", "branch"]
    data_class: str
    company_id: Optional[UUID] = None
    domain_key: Optional[str] = None
    client_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    status: Literal["published", "archived"]
    schema_version: str
    version_number: int
    payload: CompliancePolicyPayload
    reason: Optional[str] = None
    source_version_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    published_by: Optional[UUID] = None
    published_at: Optional[str] = None


class ConsoleCompliancePolicyRegistryResponse(BaseModel):
    scope: Literal["global", "domain", "client", "branch"]
    data_class: str
    company_id: Optional[UUID] = None
    domain_key: Optional[str] = None
    client_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    active: Optional[ConsoleCompliancePolicyVersionRecord] = None
    history: list[ConsoleCompliancePolicyVersionRecord] = []


class ConsoleCompliancePolicyRegistryPublishRequest(BaseModel):
    scope: Literal["global", "domain", "client", "branch"]
    data_class: str
    domain_key: Optional[str] = None
    branch_id: Optional[UUID] = None
    schema_version: Optional[str] = None
    reason: str
    payload: CompliancePolicyPayload


class ConsoleCompliancePolicyRegistryRollbackRequest(BaseModel):
    scope: Literal["global", "domain", "client", "branch"]
    data_class: str
    domain_key: Optional[str] = None
    branch_id: Optional[UUID] = None
    target_version_id: UUID
    reason: str


class ConsoleCompliancePolicyRegistryMutationResponse(BaseModel):
    success: bool
    record: ConsoleCompliancePolicyVersionRecord
    from_version_id: Optional[UUID] = None


class ConsoleComplianceLifecycleRunRecord(BaseModel):
    id: UUID
    scope: Literal["client", "branch"]
    data_class: str
    operation: Literal["retention_scan", "export_preview", "destruction_preview"]
    run_mode: Literal["preview", "manual"]
    status: Literal["running", "completed", "failed"]
    client_id: UUID
    branch_id: Optional[UUID] = None
    policy_version_id: Optional[UUID] = None
    policy_scope: Optional[str] = None
    summary: dict = {}
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    triggered_by: Optional[UUID] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConsoleComplianceLifecycleRecord(BaseModel):
    id: UUID
    run_id: UUID
    entity_type: str
    entity_id: Optional[str] = None
    action: str
    result: Literal["candidate", "skipped", "error"]
    payload: dict = {}
    occurred_at: Optional[str] = None


class ConsoleComplianceLifecycleArtifactRecord(BaseModel):
    id: UUID
    run_id: UUID
    scope: Literal["client", "branch"]
    data_class: str
    operation: Literal["retention_scan", "export_preview", "destruction_preview"]
    run_mode: Literal["preview", "manual"]
    status: Literal["running", "completed", "failed"]
    client_id: UUID
    branch_id: Optional[UUID] = None
    artifact_type: Literal["compliance_lifecycle_evidence"]
    artifact_digest: str
    payload: dict = {}
    records_count: int = 0
    evidence_record_count: int = 0
    published_by: Optional[UUID] = None
    published_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConsoleComplianceLifecycleRunRequest(BaseModel):
    scope: Literal["client", "branch"]
    branch_id: Optional[UUID] = None
    data_class: Literal["learned_responses"] = "learned_responses"
    operation: Literal["retention_scan", "export_preview", "destruction_preview"]
    run_mode: Optional[Literal["preview", "manual"]] = None
    max_items: int = Field(default=200, ge=1, le=500)
    reason: str


class ConsoleComplianceLifecycleRunResponse(BaseModel):
    success: bool
    run: ConsoleComplianceLifecycleRunRecord
    records: list[ConsoleComplianceLifecycleRecord] = []


class ConsoleComplianceLifecycleRunsResponse(BaseModel):
    items: list[ConsoleComplianceLifecycleRunRecord]


class ConsoleComplianceLifecycleArtifactResponse(BaseModel):
    success: bool
    artifact: ConsoleComplianceLifecycleArtifactRecord


class ConsoleSlaProfileVersionRecord(BaseModel):
    id: UUID
    scope: Literal["global", "domain", "client", "branch"]
    company_id: Optional[UUID] = None
    domain_key: Optional[str] = None
    client_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    status: Literal["published", "archived"]
    schema_version: str
    version_number: int
    payload: SlaProfilePayload
    reason: Optional[str] = None
    source_version_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    published_by: Optional[UUID] = None
    published_at: Optional[str] = None


class ConsoleSlaProfileRegistryResponse(BaseModel):
    scope: Literal["global", "domain", "client", "branch"]
    company_id: Optional[UUID] = None
    domain_key: Optional[str] = None
    client_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    active: Optional[ConsoleSlaProfileVersionRecord] = None
    history: list[ConsoleSlaProfileVersionRecord] = []


class ConsoleSlaProfileRegistryPublishRequest(BaseModel):
    scope: Literal["global", "domain", "client", "branch"]
    domain_key: Optional[str] = None
    branch_id: Optional[UUID] = None
    schema_version: Optional[str] = None
    reason: str
    payload: SlaProfilePayload


class ConsoleSlaProfileRegistryRollbackRequest(BaseModel):
    scope: Literal["global", "domain", "client", "branch"]
    domain_key: Optional[str] = None
    branch_id: Optional[UUID] = None
    target_version_id: UUID
    reason: str


class ConsoleSlaProfileRegistryMutationResponse(BaseModel):
    success: bool
    record: ConsoleSlaProfileVersionRecord
    from_version_id: Optional[UUID] = None


class ConsoleToolRegistryItem(BaseModel):
    id: UUID
    tool_action: str
    tool_group: str
    title: Optional[str] = None
    summary: Optional[str] = None
    schema_version: str
    status: Literal["active", "disabled"]
    certification_status: Literal["certified", "uncertified"]
    health_status: Literal["healthy", "degraded", "down"]
    allowed_scopes: list[Literal["client", "branch"]] = []
    metadata: dict = {}
    created_by: Optional[UUID] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConsoleToolRegistryListResponse(BaseModel):
    items: list[ConsoleToolRegistryItem]


class ConsoleToolRegistryUpsertRequest(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    schema_version: Optional[str] = None
    status: Optional[Literal["active", "disabled"]] = None
    certification_status: Optional[Literal["certified", "uncertified"]] = None
    health_status: Optional[Literal["healthy", "degraded", "down"]] = None
    allowed_scopes: Optional[list[Literal["client", "branch"]]] = None
    metadata: Optional[dict] = None


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


class ConsoleDomainCatalogItem(BaseModel):
    id: UUID
    domain_slug: str
    title: str
    summary: Optional[str] = None
    schema_version: str
    status: Literal["active", "disabled"]
    capability_template: CapabilitiesPayload
    metadata: dict
    created_by: Optional[UUID] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConsoleDomainCatalogListResponse(BaseModel):
    items: list[ConsoleDomainCatalogItem]


class ConsoleDomainCatalogUpsertRequest(BaseModel):
    title: str
    summary: Optional[str] = None
    schema_version: Optional[str] = None
    status: Optional[Literal["active", "disabled"]] = None
    capability_template: Optional[CapabilitiesPayload] = None
    metadata: Optional[dict] = None


class ConsoleOnboardingBlueprintQuestionTemplate(BaseModel):
    code: str
    question: str
    blocking_go_live: bool = False


class ConsoleOnboardingBlueprintRequiredFieldsProfile(BaseModel):
    fields: list[str] = []
    checksum: str


class ConsoleOnboardingBlueprint(BaseModel):
    id: str
    domain_slug: str
    label: str
    summary: str
    payload: CapabilitiesPayload
    go_live_blockers_profile: list[str] = []
    question_templates: list[ConsoleOnboardingBlueprintQuestionTemplate] = []
    required_fields_profile: ConsoleOnboardingBlueprintRequiredFieldsProfile
    readiness_weights: dict[str, int] = {}


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
ConsoleSlaViolationAction = Literal["none", "notify_manager", "escalate", "collect_only"]
ConsoleSlaProfileScope = Literal["global", "domain", "client", "branch"]


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
    sla_violation_action: Optional[ConsoleSlaViolationAction] = None
    sla_profile_id: Optional[UUID] = None
    sla_profile_version: Optional[int] = None
    sla_profile_scope: Optional[ConsoleSlaProfileScope] = None
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


class ConsoleAdminControlTowerDriftSummary(BaseModel):
    total_branches: int
    ok_branches: int
    warn_branches: int
    error_branches: int
    degraded_branches: int
    queue_p0: int
    queue_p1: int
    queue_p2: int


class ConsoleAdminControlTowerDriftBoardResponse(BaseModel):
    generated_at: str
    stale_after_minutes: int
    limit: int
    only_problematic: bool = True
    summary: ConsoleAdminControlTowerDriftSummary
    top_issues: list[ConsoleAdminControlTowerIssueCount] = []
    items: list[ConsoleProviderLifecycleItem]
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
    queue_lag_seconds: Optional[float] = None
    queue_lag_status: Optional[KpiStatus] = None
    stale_view_rate: Optional[float] = None
    stale_view_status: Optional[KpiStatus] = None
    case_action_apply_latency_seconds: Optional[float] = None
    case_action_apply_latency_status: Optional[KpiStatus] = None
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
