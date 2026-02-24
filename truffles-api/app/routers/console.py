import hashlib
import json
import os
import re
import secrets
from collections import deque
from dataclasses import dataclass
from datetime import date as dt_date
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from threading import Lock, Thread
from time import monotonic, perf_counter
from typing import Any, Callable, Literal, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request as URLRequest
from urllib.request import urlopen
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import and_, case, delete, event, func, or_, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.logging_config import (
    record_tenants_endpoint_latency,
    record_tenants_fleet_projection_compaction,
    record_tenants_fleet_projection_observation,
)
from app.models import (
    Agent,
    AgentIdentity,
    AgentMembership,
    AlertEvent,
    Branch,
    Client,
    ClientCapability,
    ClientOnboardingContract,
    ClientSettings,
    Company,
    ConsoleBranchChange,
    ConsoleOpsJob,
    Conversation,
    ConversationHumanLock,
    Handover,
    KnowledgeVersion,
    LearnedResponse,
    MarketingCampaign,
    MarketingCampaignDelivery,
    MarketingCampaignRecipient,
    Message,
    OutboxMessage,
    ReferencePack,
    TenantsFleetCache,
    TenantsFleetClientProjection,
    TenantsFleetPrewarmJob,
    TenantsWeeklySnapshot,
    User,
)
from app.models import (
    ConsoleMacro as ConsoleMacroModel,
)
from app.models.appointment import Appointment
from app.models.appointment_audit import AppointmentAudit
from app.models.reminder_job import ReminderJob
from app.schemas.capabilities import CAPABILITIES_SCHEMA_VERSION, CapabilitiesPayload
from app.schemas.console import (
    ConsoleAgent,
    ConsoleAgentCreateRequest,
    ConsoleAgentCreateResponse,
    ConsoleAgentIdentity,
    ConsoleAgentInfo,
    ConsoleAgentLifecycleActionRequest,
    ConsoleAgentListResponse,
    ConsoleAgentMembership,
    ConsoleAgentOidcRebindRequest,
    ConsoleAgentOidcRebindResponse,
    ConsoleAgentWithIdentities,
    ConsoleAuditEvent,
    ConsoleAuditListResponse,
    ConsoleBranch,
    ConsoleBranchBootstrapAccountTemplate,
    ConsoleBranchChangeDraftRequest,
    ConsoleBranchChangeListResponse,
    ConsoleBranchChangePublishRequest,
    ConsoleBranchChangeRecord,
    ConsoleBranchChangeResponse,
    ConsoleBranchChangeRollbackRequest,
    ConsoleBranchCreateRequest,
    ConsoleBranchCreateResponse,
    ConsoleBranchGoLiveDecisionRequest,
    ConsoleBranchGoLiveWaiverRequest,
    ConsoleBranchIntegrationStatus,
    ConsoleBranchListResponse,
    ConsoleBranchUpdateRequest,
    ConsoleBusinessActionItem,
    ConsoleBusinessSummaryResponse,
    ConsoleCapabilitiesPatchRequest,
    ConsoleCapabilitiesRecord,
    ConsoleCapabilitiesResponse,
    ConsoleCase,
    ConsoleCaseActionResponse,
    ConsoleCaseActionSync,
    ConsoleCaseListResponse,
    ConsoleClient,
    ConsoleClientCreateRequest,
    ConsoleClientCreateResponse,
    ConsoleClientLifecycleActionRequest,
    ConsoleClientListResponse,
    ConsoleClientUpdateRequest,
    ConsoleCompany,
    ConsoleCompanyCreateRequest,
    ConsoleCompanyCreateResponse,
    ConsoleCompanyListResponse,
    ConsoleCompanyUpdateRequest,
    ConsoleConfirmationCreateRequest,
    ConsoleConfirmationResponse,
    ConsoleDataTrustSummaryResponse,
    ConsoleErrorResponse,
    ConsoleFleetAttentionItem,
    ConsoleFleetAttentionResponse,
    ConsoleFleetAttentionSummary,
    ConsoleFleetSummary,
    ConsoleHealthResponse,
    ConsoleHumanLockPauseRequest,
    ConsoleHumanLockStatus,
    ConsoleHumanLockStatusResponse,
    ConsoleIncidentAction,
    ConsoleIncidentItem,
    ConsoleIncidentListResponse,
    ConsoleIncidentSummary,
    ConsoleIntegrationBranchActionRequest,
    ConsoleIntegrationBranchActionResponse,
    ConsoleIntegrationsListResponse,
    ConsoleKnowledgeCurrentResponse,
    ConsoleKnowledgeHistoryItem,
    ConsoleKnowledgeHistoryResponse,
    ConsoleKnowledgePublishRequest,
    ConsoleKnowledgePublishResponse,
    ConsoleKnowledgeRollbackRequest,
    ConsoleKnowledgeRollbackResponse,
    ConsoleKnowledgeValidateRequest,
    ConsoleKnowledgeValidateResponse,
    ConsoleLearningCandidate,
    ConsoleLearningCandidateActionResponse,
    ConsoleLearningCandidateListResponse,
    ConsoleMacroCreateRequest,
    ConsoleMacroCreateResponse,
    ConsoleMacroListResponse,
    ConsoleMacroUpdateRequest,
    ConsoleManagerMessageRequest,
    ConsoleManagerMessageResponse,
    ConsoleMarketingAudienceFunnel,
    ConsoleMarketingCampaign,
    ConsoleMarketingCampaignAudienceResponse,
    ConsoleMarketingCampaignCreateRequest,
    ConsoleMarketingCampaignCreateResponse,
    ConsoleMarketingCampaignDiagnosticsResponse,
    ConsoleMarketingCampaignExecuteRequest,
    ConsoleMarketingCampaignExecuteResponse,
    ConsoleMarketingCampaignLifecycleActionRequest,
    ConsoleMarketingCampaignListResponse,
    ConsoleMarketingCampaignPreflightResponse,
    ConsoleMarketingCampaignPreviewRequest,
    ConsoleMarketingCampaignPreviewResponse,
    ConsoleMarketingCampaignRecipient,
    ConsoleMarketingCampaignRetryRequest,
    ConsoleMarketingCampaignRetryResponse,
    ConsoleMarketingCampaignUpdateRequest,
    ConsoleMarketingDeliverySample,
    ConsoleMarketingSegmentCatalogResponse,
    ConsoleMembershipCreateRequest,
    ConsoleMembershipListResponse,
    ConsoleMembershipUpdateRequest,
    ConsoleMeResponse,
    ConsoleMessage,
    ConsoleMessageListResponse,
    ConsoleMetricFactMeta,
    ConsoleMetricsDailyResponse,
    ConsoleOnboardingAdvanceRequest,
    ConsoleOnboardingAutopilotIntake,
    ConsoleOnboardingAutopilotRequest,
    ConsoleOnboardingAutopilotResponse,
    ConsoleOnboardingBlueprint,
    ConsoleOnboardingBlueprintListResponse,
    ConsoleOnboardingBlueprintQuestionTemplate,
    ConsoleOnboardingBlueprintRequiredFieldsProfile,
    ConsoleOnboardingContractPatchRequest,
    ConsoleOnboardingContractRecord,
    ConsoleOnboardingContractResponse,
    ConsoleOnboardingDocumentIngestion,
    ConsoleOnboardingIntakeCompile,
    ConsoleOnboardingIntakeQualityDimension,
    ConsoleOnboardingIntakeQualityMatrix,
    ConsoleOnboardingOperationalPipeline,
    ConsoleOnboardingOperationalStage,
    ConsoleOnboardingReadinessDimension,
    ConsoleOnboardingReadinessHardGate,
    ConsoleOnboardingReadinessKernel,
    ConsoleOnboardingReadinessQuestion,
    ConsoleOnboardingScorecardCheck,
    ConsoleOnboardingScorecardResponse,
    ConsoleOnboardingSlaControlLoop,
    ConsoleOnboardingStatusResponse,
    ConsoleOnboardingStepStatus,
    ConsoleOnboardingThroughputMetrics,
    ConsoleOpsJobCatalogResponse,
    ConsoleOpsJobDefinition,
    ConsoleOpsJobListResponse,
    ConsoleOpsJobRecord,
    ConsoleOpsJobRunRequest,
    ConsoleOpsJobRunResponse,
    ConsoleOutboxCounts,
    ConsoleOutboxItem,
    ConsoleOutboxListResponse,
    ConsoleOutboxRetryRequest,
    ConsoleOutboxRetryResponse,
    ConsoleOutreachMessageRequest,
    ConsoleOutreachMessageResponse,
    ConsoleOwnerMode,
    ConsoleOwnerOperationApplyRequest,
    ConsoleOwnerOperationApplyResponse,
    ConsoleOwnerOperationImpactResponse,
    ConsoleOwnerOperationMetricDelta,
    ConsoleOwnerOperationMetricSnapshot,
    ConsoleOwnerOperationPreviewResponse,
    ConsoleOwnerOperationRollbackRequest,
    ConsoleOwnerOperationRollbackResponse,
    ConsoleOwnerOperationSettingsPatch,
    ConsoleProviderLifecycleItem,
    ConsoleProviderLifecycleListResponse,
    ConsoleProviderOpsQueueItem,
    ConsoleReferencePack,
    ConsoleReferencePackListResponse,
    ConsoleReferencePackUpsertRequest,
    ConsoleReminderCounts,
    ConsoleReminderErrorBucket,
    ConsoleReminderItem,
    ConsoleReminderListResponse,
    ConsoleReminderRetryRequest,
    ConsoleReminderRetryResponse,
    ConsoleSettingsResponse,
    ConsoleSettingsUpdateRequest,
    ConsoleSettingsUpdateResponse,
    ConsoleSubscriptionContractGap,
    ConsoleSubscriptionContractHealth,
    ConsoleSubscriptionEvidenceItem,
    ConsoleSubscriptionMeterItem,
    ConsoleSubscriptionPlanDefaults,
    ConsoleSubscriptionSummaryResponse,
    ConsoleSyncStatus,
    ConsoleTeamManagerPerformanceItem,
    ConsoleTeamPerformanceSummaryResponse,
    ConsoleTelegramHealthResponse,
    ConsoleTelegramLinkResponse,
    ConsoleTelegramTestRequest,
    ConsoleTelegramTestResponse,
    ConsoleTelegramTrail,
    ConsoleTelegramVerifyRequest,
    ConsoleTelegramVerifyResponse,
    ConsoleTenantsCompanyCockpitResponse,
    ConsoleTenantsPortfolioResponse,
    ConsoleTenantsSensitiveAccessAuditRequest,
    ConsoleTenantsSensitiveAccessAuditResponse,
    ConsoleTenantsWeeklySnapshotCreateRequest,
    ConsoleTenantsWeeklySnapshotCreateResponse,
    ConsoleTenantsWeeklySnapshotListResponse,
    ConsoleTenantsWeeklySnapshotPayload,
    ConsoleTenantsWeeklySnapshotRecord,
    ConsoleWebhookSecretResponse,
)
from app.schemas.console import (
    ConsoleMacro as ConsoleMacroSchema,
)
from app.schemas.onboarding_contract import (
    ONBOARDING_CONTRACT_SCHEMA_VERSION,
    OnboardingContractPayload,
    OnboardingProviderBindingWhatsApp,
)
from app.schemas.outbox_payload import validate_outbox_payload
from app.services.agent_link_service import build_telegram_deep_link, create_agent_link_token
from app.services.alert_service import alert_warning
from app.services.audit_service import AuditEvent, record_audit_event
from app.services.capabilities_service import merge_capabilities, payload_to_dict
from app.services.chatflow_service import get_instance_id, send_bot_response
from app.services.console_auth import ConsoleAuthContext, get_console_context, require_console_permission
from app.services.console_confirmations import create_confirmation, mark_confirmation_used, require_confirmation
from app.services.console_errors import ConsoleAPIError, build_console_error_payload
from app.services.console_idempotency import (
    finalize_idempotency,
    release_idempotency,
    start_idempotency,
)
from app.services.console_knowledge_preflight import (
    DEFAULT_PREFLIGHT_WINDOW_MINUTES,
    build_knowledge_draft_hash,
    build_knowledge_validate_payload,
    has_recent_knowledge_preflight,
)
from app.services.console_owner_admin import (
    build_data_trust_actions as _build_data_trust_actions,
)
from app.services.console_owner_admin import (
    build_owner_actions as _build_owner_actions,
)
from app.services.console_owner_admin import (
    build_team_performance_actions as _build_team_performance_actions,
)
from app.services.console_owner_admin import (
    classify_outbox_incident_reason as _classify_outbox_incident_reason,
)
from app.services.console_owner_admin import (
    derive_business_status as _derive_business_status,
)
from app.services.console_owner_admin import (
    derive_data_trust_status as _derive_data_trust_status,
)
from app.services.console_owner_admin import (
    derive_team_performance_status as _derive_team_performance_status,
)
from app.services.console_owner_admin import (
    load_latest_analytics_row as _load_latest_analytics_row,
)
from app.services.console_owner_admin import (
    resolve_subscription_alert as _resolve_subscription_alert,
)
from app.services.console_owner_admin import (
    resolve_subscription_contract_info as _resolve_subscription_contract_info,
)
from app.services.console_owner_admin import (
    safe_float as _safe_float,
)
from app.services.console_owner_admin import (
    safe_int as _safe_int,
)
from app.services.conversation_service import get_or_create_conversation, get_or_create_user
from app.services.escalation_service import resolve_telegram_routing
from app.services.human_lock_service import (
    HUMAN_LOCK_SCOPE_CONVERSATION,
    HUMAN_LOCK_SCOPE_REMOTE,
    get_active_human_lock,
    normalize_phone_to_jid,
    release_human_lock,
    resolve_conversation_remote_jid,
    upsert_human_lock,
)
from app.services.integration_guardrails_service import run_integration_watchdog_scoped
from app.services.knowledge_registry_service import (
    apply_pack_index_to_client_config,
    get_current_published,
    list_history,
    publish_version,
    restore_version,
    sync_published_branch_docs,
    upsert_draft,
    validate_draft,
)
from app.services.knowledge_validation import dump_pack_yaml
from app.services.learned_response_service import (
    approve_learned_response,
    is_agent_allowed_to_approve,
    reject_learned_response,
)
from app.services.learning_service import evaluate_candidate_eligibility, get_learning_policy
from app.services.manager_message_service import (
    notify_client_manager_status,
    process_console_media_upload,
)
from app.services.marketing import (
    MARKETING_SEGMENT_CODES,
    MARKETING_STATUS_APPROVED,
    MARKETING_STATUS_DRAFT,
    MARKETING_STATUS_IN_REVIEW,
    MARKETING_STATUS_PAUSED,
    MARKETING_STATUS_VALUES,
    build_marketing_campaign_preflight,
    build_marketing_segment_summary,
    describe_marketing_reason_code,
    describe_marketing_suppression_reason,
    fetch_marketing_audience_preview,
    get_marketing_segment_catalog,
    mark_campaign_approved,
    mark_campaign_paused,
    mark_campaign_resume,
    mark_campaign_under_review,
    materialize_marketing_campaign_audience,
    normalize_marketing_segment_params,
    normalize_marketing_status,
    refresh_marketing_campaign_lifecycle,
    resolve_campaign_segment_params,
    resolve_marketing_campaign_status,
    retry_failed_marketing_deliveries,
    run_marketing_campaign_execute,
)
from app.services.metrics_daily_service import (
    get_metrics_daily_backfill_max_days,
    get_metrics_daily_default_date,
    run_metrics_daily_snapshot,
)
from app.services.onboarding_blueprints import list_onboarding_blueprints
from app.services.onboarding_contract_service import (
    find_capability_mismatches,
    merge_onboarding_contract,
    onboarding_contract_payload_to_dict,
    validate_onboarding_contract_payload,
)
from app.services.onboarding_intake_service import (
    build_intake_field_states,
    build_intake_pack_quality_summary,
    build_intake_payload,
    build_intake_question_queue,
    evaluate_intake_payload,
)
from app.services.onboarding_state import (
    OnboardingStep,
    advance_onboarding_step,
    build_onboarding_inputs,
    build_onboarding_readiness_kernel,
    build_onboarding_scorecard,
    build_onboarding_status,
    ensure_onboarding_step,
)
from app.services.outbox_service import (
    archive_pending_outbox,
    build_inbound_message_id,
    enqueue_outbox_message,
)
from app.services.pack_compiler_service import (
    PackCompilerError,
    build_compiled_pack_meta,
    extract_compiled_artifacts,
    parse_compiled_at,
)
from app.services.provider_error_policy import classify_provider_error
from app.services.reference_branch_selection import (
    ReferenceBranchSignal,
    select_reference_branch_ids,
)
from app.services.reference_branch_selection import (
    has_recent_inbound as _reference_branch_has_recent_inbound,
)
from app.services.reference_pack_integrity import (
    REFERENCE_PACK_SCHEMA_VERSION,
    build_reference_pack_metadata,
)
from app.services.state_service import manager_resolve as state_manager_resolve
from app.services.state_service import manager_return as state_manager_return
from app.services.state_service import manager_take as state_manager_take
from app.services.telegram_service import TelegramService
from app.services.webhook_secret_service import derive_webhook_secret_from_instance

router = APIRouter(prefix="/console/v1", tags=["console"])


def _get_idempotency_key(request: Request) -> Optional[str]:
    return request.headers.get("Idempotency-Key") or request.headers.get("X-Idempotency-Key")


def _build_me_response(context: ConsoleAuthContext) -> ConsoleMeResponse:
    companies_by_id = {company.id: company for company in context.companies}
    companies = [
        ConsoleCompany(
            id=company.id,
            name=company.name,
            billing_info=company.billing_info,
        )
        for company in context.companies
    ]
    branches = [_serialize_branch(branch) for branch in context.branches]
    clients = [
        {
            "id": client.id,
            "slug": client.name,
            "name": client.name,
            "status": client.status,
            "company_id": client.company_id,
            "company_name": companies_by_id.get(client.company_id).name
            if client.company_id and client.company_id in companies_by_id
            else None,
        }
        for client in (context.accessible_clients or [])
    ]
    active_client = {
        "id": context.client.id,
        "slug": context.client.name,
        "name": context.client.name,
        "status": context.client.status,
        "company_id": context.client.company_id,
        "company_name": companies_by_id.get(context.client.company_id).name
        if context.client.company_id and context.client.company_id in companies_by_id
        else None,
    } if context.client else None
    return ConsoleMeResponse(
        agent={
            "id": context.agent.id,
            "name": context.agent.name,
            "role": context.role,
            "client_id": context.client.id,
            "branch_id": context.effective_branch_id or context.agent.branch_id,
            "is_active": context.agent.is_active,
        },
        client=active_client,
        branches=branches,
        clients=clients,
        companies=companies,
        company_selection_required=context.company_selection_required,
        selection_required=context.selection_required,
        branch_selection_required=context.branch_selection_required,
        selected_company_id=context.selected_company_id,
        selected_branch_id=context.effective_branch_id,
    )


def _calculate_sla_status(created_at: datetime) -> str:
    time_since_creation = (datetime.now(timezone.utc) - created_at).total_seconds()
    if time_since_creation > 7200:  # 2 hours
        return "breached"
    if time_since_creation > 3600:  # 1 hour
        return "warning"
    return "ok"


def _format_telegram_timestamp(value: Optional[int]) -> Optional[str]:
    if not value:
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()


def _build_telegram_link(
    chat_id: Optional[str],
    message_id: Optional[int],
    topic_id: Optional[int] = None,
) -> Optional[str]:
    if not chat_id:
        return None
    chat_id_str = str(chat_id)
    if not chat_id_str.startswith("-100"):
        return None
    internal_id = chat_id_str[4:]
    if not internal_id.isdigit():
        return None
    if not message_id:
        return None
    target_str = str(message_id)
    if not target_str.isdigit():
        return None
    link = f"https://t.me/c/{internal_id}/{target_str}"
    if topic_id:
        topic_str = str(topic_id)
        if topic_str.isdigit():
            link = f"{link}?thread={topic_str}"
    return link


def _build_telegram_desktop_link(
    chat_id: Optional[str],
    message_id: Optional[int],
    topic_id: Optional[int] = None,
) -> Optional[str]:
    if not chat_id:
        return None
    chat_id_str = str(chat_id).strip()
    if chat_id_str.startswith("-100"):
        chat_id_str = chat_id_str[4:]
    if not chat_id_str or not chat_id_str.isdigit():
        return None
    if not message_id:
        return None
    target_str = str(message_id)
    if not target_str.isdigit():
        return None
    link = f"tg://privatepost?channel={chat_id_str}&post={target_str}"
    if topic_id:
        topic_str = str(topic_id)
        if topic_str.isdigit():
            link = f"{link}&thread={topic_str}"
    return link


def _build_console_telegram_caption(manager_label: str, caption: Optional[str]) -> Optional[str]:
    normalized_caption = _normalize_optional_text(caption)
    label = manager_label.strip() if manager_label else "Менеджер"
    prefix = f"🖥️ <b>{label}</b>"
    if normalized_caption:
        return f"{prefix}: {normalized_caption}"
    return prefix


_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_KNOWLEDGE_TAG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_BRANCH_PHONE_ALLOWED_PATTERN = re.compile(r"^\+?[0-9][0-9\s()-]{5,23}$")
_TELEGRAM_CHAT_ID_PATTERN = re.compile(r"^-?[0-9]{5,20}$")


def _normalize_slug(value: Optional[str], field_name: str) -> str:
    if not value or not isinstance(value, str):
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} is required")
    slug = re.sub(r"\s+", "-", value.strip().lower())
    if not slug or not _SLUG_PATTERN.fullmatch(slug):
        raise ConsoleAPIError(400, "INVALID_PARAM", f"Invalid {field_name}")
    return slug


def _normalize_required_text(value: Optional[str], field_name: str) -> str:
    if not value or not isinstance(value, str):
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} is required")
    normalized = value.strip()
    if not normalized:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} is required")
    return normalized


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_timezone_name(value: Optional[str], field_name: str = "timezone") -> Optional[str]:
    normalized = _normalize_optional_text(value)
    if not normalized:
        return None
    try:
        ZoneInfo(normalized)
    except ZoneInfoNotFoundError as exc:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"Invalid {field_name}") from exc
    return normalized


def _normalize_branch_phone(value: Optional[str], field_name: str = "phone") -> Optional[str]:
    normalized = _normalize_optional_text(value)
    if not normalized:
        return None
    if not _BRANCH_PHONE_ALLOWED_PATTERN.fullmatch(normalized):
        raise ConsoleAPIError(400, "INVALID_PARAM", f"Invalid {field_name}")
    digits = _normalize_phone_digits(normalized)
    if len(digits) < 7 or len(digits) > 15:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"Invalid {field_name}")
    return normalized


def _normalize_telegram_chat_id(value: Optional[str], field_name: str = "telegram_chat_id") -> Optional[str]:
    normalized = _normalize_optional_text(value)
    if not normalized:
        return None
    if not _TELEGRAM_CHAT_ID_PATTERN.fullmatch(normalized):
        raise ConsoleAPIError(400, "INVALID_PARAM", f"Invalid {field_name}")
    return normalized


def _normalize_knowledge_tag(value: Optional[str], field_name: str = "knowledge_tag") -> Optional[str]:
    normalized = _normalize_optional_text(value)
    if not normalized:
        return None
    lowered = normalized.lower()
    if not _KNOWLEDGE_TAG_PATTERN.fullmatch(lowered):
        raise ConsoleAPIError(400, "INVALID_PARAM", f"Invalid {field_name}")
    return lowered


CONSOLE_MEDIA_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
CONSOLE_MEDIA_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
CONSOLE_MEDIA_AUDIO_EXTENSIONS = {".ogg", ".mp3", ".wav", ".m4a", ".aac", ".opus"}
CONSOLE_MEDIA_CAPTION_MAX = 4096


def _normalize_media_caption(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_optional_text(value)
    if normalized and len(normalized) > CONSOLE_MEDIA_CAPTION_MAX:
        raise ConsoleAPIError(400, "INVALID_PARAM", "caption слишком длинный")
    return normalized


def _resolve_console_media_type(file_name: Optional[str], content_type: Optional[str]) -> str:
    name = (file_name or "").lower()
    ext = Path(name).suffix
    mime = (content_type or "").lower().strip()

    if mime.startswith("video/") or ext in CONSOLE_MEDIA_VIDEO_EXTENSIONS:
        raise ConsoleAPIError(400, "MEDIA_TYPE_FORBIDDEN", "Видео из консоли не поддерживается")

    if mime.startswith("image/") or ext in CONSOLE_MEDIA_IMAGE_EXTENSIONS:
        return "photo"
    if mime.startswith("audio/") or ext in CONSOLE_MEDIA_AUDIO_EXTENSIONS:
        return "audio"
    return "document"


def _resolve_branch_from_context(context: ConsoleAuthContext) -> Branch:
    if context.effective_branch_id:
        for branch in context.branches:
            if branch.id == context.effective_branch_id:
                return branch
        raise ConsoleAPIError(403, "BRANCH_ACCESS_DENIED", "Access to this branch denied")
    if len(context.branches) == 1:
        return context.branches[0]
    raise ConsoleAPIError(400, "BRANCH_SELECTION_REQUIRED", "Branch selection required")


def _has_context_privileged_branch_access(context: ConsoleAuthContext) -> bool:
    if not _is_privileged_access_role(context.role):
        return False
    # Branch-scoped owner/admin must stay branch-restricted.
    return not bool(getattr(context, "branch_restricted", False))


def _require_branch_access(
    context: ConsoleAuthContext,
    branch_id: Optional[UUID],
    *,
    message: str,
) -> None:
    if branch_id is None:
        return
    if _has_context_privileged_branch_access(context):
        return
    allowed_branch_ids = {branch.id for branch in context.branches}
    if branch_id not in allowed_branch_ids:
        raise ConsoleAPIError(403, "ACCESS_DENIED", message)


def _ensure_unique_branch_field(
    db: Session,
    *,
    client_id: UUID,
    field_name: str,
    value: Optional[str],
    exclude_branch_id: Optional[UUID] = None,
) -> None:
    if not value:
        return
    column = getattr(Branch, field_name)
    query = db.query(Branch).filter(column == value)
    if field_name != "instance_id":
        query = query.filter(Branch.client_id == client_id)
    if exclude_branch_id:
        query = query.filter(Branch.id != exclude_branch_id)
    if query.first():
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} already in use")


def _serialize_branch(branch: Branch) -> ConsoleBranch:
    go_live_state = _normalize_branch_go_live_state(getattr(branch, "go_live_state", None))
    go_live_reviewed_at = _coerce_utc(getattr(branch, "go_live_reviewed_at", None))
    go_live_waiver_until = _coerce_utc(getattr(branch, "go_live_waiver_until", None))
    go_live_waiver_active = _is_branch_go_live_waiver_active(branch)
    branch_client = getattr(branch, "client", None)
    company_id = getattr(branch_client, "company_id", None) if branch_client is not None else None
    return ConsoleBranch(
        id=branch.id,
        client_id=branch.client_id,
        company_id=company_id,
        slug=branch.slug,
        name=branch.name,
        is_active=branch.is_active,
        instance_id=branch.instance_id,
        telegram_chat_id=branch.telegram_chat_id,
        phone=branch.phone,
        knowledge_tag=branch.knowledge_tag,
        timezone=branch.timezone,
        working_hours=branch.working_hours,
        booking_settings=branch.booking_settings,
        onboarding_state=branch.onboarding_state,
        onboarding_updated_at=branch.onboarding_updated_at.isoformat()
        if branch.onboarding_updated_at
        else None,
        go_live_state=go_live_state,
        go_live_reason=getattr(branch, "go_live_reason", None),
        go_live_reviewed_at=go_live_reviewed_at.isoformat() if go_live_reviewed_at else None,
        go_live_reviewed_by=getattr(branch, "go_live_reviewed_by", None),
        go_live_waiver_until=go_live_waiver_until.isoformat() if go_live_waiver_until else None,
        go_live_waiver_reason=getattr(branch, "go_live_waiver_reason", None),
        go_live_waiver_by=getattr(branch, "go_live_waiver_by", None),
        go_live_waiver_active=go_live_waiver_active,
        go_live_allowed=go_live_state == "approved" or go_live_waiver_active,
    )


_BRANCH_CHANGE_MANAGED_FIELDS = (
    "slug",
    "name",
    "timezone",
    "instance_id",
    "phone",
    "telegram_chat_id",
    "knowledge_tag",
    "working_hours",
    "booking_settings",
    "is_active",
)
_BRANCH_CHANGE_MUTABLE_STATUSES = {"draft", "validated", "publish_failed"}


def _snapshot_branch_for_change(branch: Branch) -> dict:
    return {
        "slug": branch.slug,
        "name": branch.name,
        "timezone": branch.timezone,
        "instance_id": branch.instance_id,
        "phone": branch.phone,
        "telegram_chat_id": branch.telegram_chat_id,
        "knowledge_tag": branch.knowledge_tag,
        "working_hours": _jsonable_payload(branch.working_hours if isinstance(branch.working_hours, dict) else {}),
        "booking_settings": _jsonable_payload(branch.booking_settings if isinstance(branch.booking_settings, dict) else {}),
        "is_active": bool(branch.is_active),
    }


def _build_branch_change_diff(base_snapshot: dict, patch_payload: dict) -> dict:
    diff: dict[str, dict[str, object]] = {}
    for field in _BRANCH_CHANGE_MANAGED_FIELDS:
        if field not in patch_payload:
            continue
        before = base_snapshot.get(field)
        after = patch_payload.get(field)
        if before == after:
            continue
        diff[field] = {
            "before": before,
            "after": after,
        }
    return diff


def _serialize_branch_change_record(change: ConsoleBranchChange) -> ConsoleBranchChangeRecord:
    return ConsoleBranchChangeRecord(
        id=change.id,
        branch_id=change.branch_id,
        status=change.status,
        reason=change.reason,
        draft_payload=change.draft_payload if isinstance(change.draft_payload, dict) else {},
        diff_payload=change.diff_payload if isinstance(change.diff_payload, dict) else {},
        validation_payload=change.validation_payload if isinstance(change.validation_payload, dict) else None,
        base_snapshot=change.base_snapshot if isinstance(change.base_snapshot, dict) else {},
        published_snapshot=change.published_snapshot if isinstance(change.published_snapshot, dict) else None,
        rollback_snapshot=change.rollback_snapshot if isinstance(change.rollback_snapshot, dict) else None,
        publish_error=change.publish_error,
        rollback_error=change.rollback_error,
        created_at=change.created_at.isoformat() if change.created_at else "",
        updated_at=change.updated_at.isoformat() if change.updated_at else None,
        validated_at=change.validated_at.isoformat() if change.validated_at else None,
        published_at=change.published_at.isoformat() if change.published_at else None,
        rolled_back_at=change.rolled_back_at.isoformat() if change.rolled_back_at else None,
    )


def _normalize_branch_change_patch(*, db: Session, branch: Branch, patch_payload: dict) -> tuple[dict, list[str]]:
    errors: list[str] = []
    normalized: dict[str, object] = {}

    if not isinstance(patch_payload, dict):
        return {}, ["patch must be an object"]

    if not any(field in patch_payload for field in _BRANCH_CHANGE_MANAGED_FIELDS):
        return {}, ["patch has no supported fields"]

    if "slug" in patch_payload:
        raw_slug = patch_payload.get("slug")
        if raw_slug is None:
            errors.append("slug cannot be null")
        elif not isinstance(raw_slug, str):
            errors.append("slug must be string")
        else:
            try:
                slug = _normalize_slug(raw_slug, "branch_slug")
            except ConsoleAPIError as exc:
                errors.append(exc.message)
            else:
                _ensure_unique_branch_field(
                    db,
                    client_id=branch.client_id,
                    field_name="slug",
                    value=slug,
                    exclude_branch_id=branch.id,
                )
                normalized["slug"] = slug

    if "name" in patch_payload:
        raw_name = patch_payload.get("name")
        if raw_name is None:
            errors.append("name cannot be null")
        elif not isinstance(raw_name, str):
            errors.append("name must be string")
        else:
            try:
                normalized["name"] = _normalize_required_text(raw_name, "name")
            except ConsoleAPIError as exc:
                errors.append(exc.message)

    if "timezone" in patch_payload:
        raw_timezone = patch_payload.get("timezone")
        if raw_timezone is not None and not isinstance(raw_timezone, str):
            errors.append("timezone must be string")
        else:
            try:
                normalized["timezone"] = _normalize_timezone_name(raw_timezone, "timezone")
            except ConsoleAPIError as exc:
                errors.append(exc.message)

    if "instance_id" in patch_payload:
        raw_instance_id = patch_payload.get("instance_id")
        if raw_instance_id is not None and not isinstance(raw_instance_id, str):
            errors.append("instance_id must be string")
        else:
            instance_id = _normalize_optional_text(raw_instance_id)
            _ensure_unique_branch_field(
                db,
                client_id=branch.client_id,
                field_name="instance_id",
                value=instance_id,
                exclude_branch_id=branch.id,
            )
            normalized["instance_id"] = instance_id

    if "phone" in patch_payload:
        raw_phone = patch_payload.get("phone")
        if raw_phone is not None and not isinstance(raw_phone, str):
            errors.append("phone must be string")
        else:
            try:
                phone = _normalize_branch_phone(raw_phone, "phone")
            except ConsoleAPIError as exc:
                errors.append(exc.message)
            else:
                _ensure_unique_branch_field(
                    db,
                    client_id=branch.client_id,
                    field_name="phone",
                    value=phone,
                    exclude_branch_id=branch.id,
                )
                normalized["phone"] = phone

    if "telegram_chat_id" in patch_payload:
        raw_chat_id = patch_payload.get("telegram_chat_id")
        if raw_chat_id is not None and not isinstance(raw_chat_id, str):
            errors.append("telegram_chat_id must be string")
        else:
            try:
                normalized["telegram_chat_id"] = _normalize_telegram_chat_id(raw_chat_id, "telegram_chat_id")
            except ConsoleAPIError as exc:
                errors.append(exc.message)

    if "knowledge_tag" in patch_payload:
        raw_knowledge_tag = patch_payload.get("knowledge_tag")
        if raw_knowledge_tag is not None and not isinstance(raw_knowledge_tag, str):
            errors.append("knowledge_tag must be string")
        else:
            try:
                normalized["knowledge_tag"] = _normalize_knowledge_tag(raw_knowledge_tag, "knowledge_tag")
            except ConsoleAPIError as exc:
                errors.append(exc.message)

    if "working_hours" in patch_payload:
        value = patch_payload.get("working_hours")
        if value is None:
            normalized["working_hours"] = {}
        elif isinstance(value, dict):
            normalized["working_hours"] = value
        else:
            errors.append("working_hours must be an object")

    if "booking_settings" in patch_payload:
        value = patch_payload.get("booking_settings")
        if value is None:
            normalized["booking_settings"] = {}
        elif isinstance(value, dict):
            normalized["booking_settings"] = value
        else:
            errors.append("booking_settings must be an object")

    if "is_active" in patch_payload:
        value = patch_payload.get("is_active")
        if value is None:
            errors.append("is_active cannot be null")
        elif isinstance(value, bool):
            normalized["is_active"] = value
        else:
            errors.append("is_active must be boolean")

    final_instance_id = (
        normalized.get("instance_id")
        if "instance_id" in normalized
        else branch.instance_id
    )
    final_is_active = (
        normalized.get("is_active")
        if "is_active" in normalized
        else bool(branch.is_active)
    )
    if final_is_active and not final_instance_id:
        errors.append("instance_id required to activate branch")
    if final_is_active and not branch.is_active:
        try:
            _require_branch_go_live_gate(branch, operation="branch_activate")
            _require_branch_scorecard_ready(db, branch, operation="branch_activate")
        except ConsoleAPIError as exc:
            errors.append(exc.message)

    return normalized, errors


def _build_branch_update_request(
    *,
    normalized_patch: dict,
    confirmation_id: Optional[UUID] = None,
) -> ConsoleBranchUpdateRequest:
    payload = dict(normalized_patch)
    if confirmation_id:
        payload["confirmation_id"] = confirmation_id
    return ConsoleBranchUpdateRequest.model_validate(payload)


def _serialize_macro(macro: ConsoleMacroModel) -> ConsoleMacroSchema:
    return ConsoleMacroSchema(
        id=macro.id,
        scope=macro.scope,
        label=macro.label,
        body=macro.body,
        is_active=macro.is_active,
        created_at=macro.created_at.isoformat() if macro.created_at else None,
        updated_at=macro.updated_at.isoformat() if macro.updated_at else None,
    )


def _serialize_onboarding_status(
    branch: Branch,
    status,
) -> ConsoleOnboardingStatusResponse:
    return ConsoleOnboardingStatusResponse(
        branch_id=branch.id,
        current_step=status.current_step.value,
        steps=[
            ConsoleOnboardingStepStatus(
                id=step.id.value,
                status=step.status,
                required=step.required,
                missing=step.missing,
            )
            for step in status.steps
        ],
        updated_at=branch.onboarding_updated_at.isoformat()
        if branch.onboarding_updated_at
        else None,
    )


def _resolve_readiness_hard_gate_blockers(readiness_kernel) -> list[str]:
    if readiness_kernel is None:
        return []
    candidates = list(getattr(readiness_kernel, "shadow_hard_gate_blockers", []) or [])
    selected = [
        code
        for code in candidates
        if code.startswith("go_no_go:") or code in _ONBOARDING_READINESS_HARD_GATE_CODES
    ]
    return _dedupe_list(selected)


def _is_readiness_hard_gate_enforced_for_branch(branch: Branch) -> bool:
    if _ONBOARDING_READINESS_HARD_GATE_ENABLED:
        return True
    branch_id = getattr(branch, "id", None)
    if branch_id is None:
        return False
    normalized_branch_id = str(branch_id).strip().lower()
    return normalized_branch_id in _ONBOARDING_READINESS_HARD_GATE_CANARY_BRANCH_IDS


def _serialize_onboarding_readiness_kernel(readiness_kernel, *, hard_gate_enforced: bool):
    if readiness_kernel is None:
        return None
    hard_gate_blockers = _resolve_readiness_hard_gate_blockers(readiness_kernel)
    return ConsoleOnboardingReadinessKernel(
        status=readiness_kernel.status,
        blocker_codes=list(readiness_kernel.blocker_codes),
        next_action_codes=list(readiness_kernel.next_action_codes),
        auto_questions=[
            ConsoleOnboardingReadinessQuestion(
                code=item.code,
                question=item.question,
                blocking_go_live=item.blocking_go_live,
            )
            for item in readiness_kernel.auto_questions
        ],
        dimensions=[
            ConsoleOnboardingReadinessDimension(
                id=item.id,
                status=item.status,
                blocker_codes=list(item.blocker_codes),
                next_action_codes=list(item.next_action_codes),
            )
            for item in readiness_kernel.dimensions
        ],
        shadow_hard_gate=ConsoleOnboardingReadinessHardGate(
            enforced=hard_gate_enforced,
            status="fail" if hard_gate_blockers else "pass",
            blocker_codes=hard_gate_blockers,
        ),
    )


def _serialize_onboarding_scorecard(
    branch: Branch,
    scorecard,
) -> ConsoleOnboardingScorecardResponse:
    document_ingestion = getattr(scorecard, "document_ingestion", None)
    sla_control_loop = getattr(scorecard, "sla_control_loop", None)
    operational_pipeline = getattr(scorecard, "operational_pipeline", None)
    readiness_kernel = getattr(scorecard, "readiness_kernel", None)
    hard_gate_enforced = _is_readiness_hard_gate_enforced_for_branch(branch)
    document_ingestion_payload = None
    if document_ingestion is not None:
        document_ingestion_payload = ConsoleOnboardingDocumentIngestion(
            status=document_ingestion.status,
            valid=document_ingestion.valid,
            source=document_ingestion.source,
            missing_fields=document_ingestion.missing_fields,
            critical_missing_fields=document_ingestion.critical_missing_fields,
        )
    sla_control_loop_payload = None
    if sla_control_loop is not None:
        sla_control_loop_payload = ConsoleOnboardingSlaControlLoop(
            status=sla_control_loop.status,
            reminder_1_minutes=sla_control_loop.reminder_1_minutes,
            reminder_2_minutes=sla_control_loop.reminder_2_minutes,
            escalation_timeout_minutes=sla_control_loop.escalation_timeout_minutes,
            pending_total=sla_control_loop.pending_total,
            warning_total=sla_control_loop.warning_total,
            breached_total=sla_control_loop.breached_total,
            provider_status=sla_control_loop.provider_status,
            provider_paid_until=sla_control_loop.provider_paid_until,
            provider_days_to_renewal=sla_control_loop.provider_days_to_renewal,
            provider_alert_state=sla_control_loop.provider_alert_state,
            active_incidents=sla_control_loop.active_incidents,
            recommended_actions=sla_control_loop.recommended_actions,
        )
    operational_pipeline_payload = None
    if operational_pipeline is not None:
        operational_pipeline_payload = ConsoleOnboardingOperationalPipeline(
            status=operational_pipeline.status,
            blocked=operational_pipeline.blocked,
            current_stage_id=operational_pipeline.current_stage_id,
            blockers=operational_pipeline.blockers,
            next_actions=operational_pipeline.next_actions,
            stages=[
                ConsoleOnboardingOperationalStage(
                    id=stage.id,
                    label=stage.label,
                    owner_lane=stage.owner_lane,
                    required=stage.required,
                    status=stage.status,
                    blockers=stage.blockers,
                    next_action=stage.next_action,
                )
                for stage in operational_pipeline.stages
            ],
        )
    return ConsoleOnboardingScorecardResponse(
        branch_id=branch.id,
        status="pass" if scorecard.ready else "fail",
        ready=scorecard.ready,
        checks=[
            ConsoleOnboardingScorecardCheck(
                id=check.id.value,
                required=check.required,
                passed=check.passed,
                missing=check.missing,
            )
            for check in scorecard.checks
        ],
        missing=scorecard.missing,
        document_ingestion=document_ingestion_payload,
        sla_control_loop=sla_control_loop_payload,
        operational_pipeline=operational_pipeline_payload,
        readiness_kernel=_serialize_onboarding_readiness_kernel(
            readiness_kernel,
            hard_gate_enforced=hard_gate_enforced,
        ),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _resolve_branch_for_onboarding(
    context: ConsoleAuthContext, *, branch_id: Optional[UUID]
) -> Branch:
    if branch_id:
        for branch in context.branches:
            if branch.id == branch_id:
                return branch
        raise ConsoleAPIError(403, "BRANCH_ACCESS_DENIED", "Access to this branch denied")
    return _resolve_branch_from_context(context)


def _build_telegram_trail(
    *,
    handover: Optional[Handover],
    conversation: Optional[Conversation],
    chat_id: Optional[str],
) -> Optional[ConsoleTelegramTrail]:
    if not handover and not conversation:
        return None
    message_id = handover.telegram_message_id if handover else None
    topic_id = conversation.telegram_topic_id if conversation else None
    delivered_at = handover.notified_at.isoformat() if handover and handover.notified_at else None
    delivery_status = "sent" if message_id else "pending"
    return ConsoleTelegramTrail(
        message_id=message_id,
        topic_id=topic_id,
        chat_id=str(chat_id) if chat_id else None,
        telegram_link=_build_telegram_link(chat_id, message_id, topic_id),
        telegram_desktop_link=_build_telegram_desktop_link(chat_id, message_id, topic_id),
        delivery_status=delivery_status,
        delivered_at=delivered_at,
    )


def _build_sync_status(status: str, detail: Optional[str] = None) -> ConsoleSyncStatus:
    return ConsoleSyncStatus(status=status, detail=detail)


def _normalize_phone_digits(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\D+", "", value)


def _is_env_enabled(value: Optional[str], *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _is_human_lock_v2_enabled() -> bool:
    return _is_env_enabled(os.environ.get("HUMAN_LOCK_V2_ENABLED"), default=True)


def _coerce_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _build_human_lock_status_payload(
    lock: ConversationHumanLock | None,
    *,
    remote_jid: str | None,
    now: datetime,
) -> ConsoleHumanLockStatus:
    if not lock:
        return ConsoleHumanLockStatus(active=False, remote_jid=remote_jid)

    lock_until = _coerce_utc_datetime(lock.lock_until)
    if not lock.active or not lock_until or lock_until <= now:
        return ConsoleHumanLockStatus(active=False, remote_jid=remote_jid)

    remaining_seconds = max(0, int((lock_until - now).total_seconds()))
    return ConsoleHumanLockStatus(
        active=True,
        remote_jid=remote_jid,
        lock_until=lock_until.isoformat(),
        remaining_seconds=remaining_seconds,
        source=lock.source,
        reason=lock.reason,
        locked_by_name=getattr(lock, "locked_by_name", None),
        lock_scope=getattr(lock, "lock_scope", None),
    )


def _build_case_human_lock_snapshot(
    db: Session,
    *,
    client_id: UUID,
    conversation: Conversation | None,
) -> dict:
    if not conversation:
        return {
            "human_lock_active": False,
            "human_lock_until": None,
            "human_lock_remaining_seconds": None,
            "human_lock_source": None,
            "human_lock_reason": None,
            "human_lock_by": None,
        }

    now_utc = datetime.now(timezone.utc)
    remote_jid = resolve_conversation_remote_jid(db, conversation=conversation)
    lock = get_active_human_lock(
        db,
        client_id=client_id,
        remote_jid=remote_jid,
        conversation_id=conversation.id,
        now=now_utc,
    )
    if not lock:
        return {
            "human_lock_active": False,
            "human_lock_until": None,
            "human_lock_remaining_seconds": None,
            "human_lock_source": None,
            "human_lock_reason": None,
            "human_lock_by": None,
        }

    lock_until = _coerce_utc_datetime(lock.lock_until)
    remaining_seconds = (
        max(0, int((lock_until - now_utc).total_seconds())) if lock_until else None
    )
    return {
        "human_lock_active": True,
        "human_lock_until": lock_until.isoformat() if lock_until else None,
        "human_lock_remaining_seconds": remaining_seconds,
        "human_lock_source": lock.source,
        "human_lock_reason": lock.reason,
        "human_lock_by": lock.locked_by_name,
    }


def _build_console_outbox_text_payload(
    *,
    client_id: UUID,
    branch_id: UUID | None,
    conversation_id: UUID | None,
    client_slug: str,
    remote_jid: str,
    instance_id: str,
    text_value: str,
    idempotency_key: str,
    source: str,
    now: datetime,
) -> dict:
    # tenant_context.source follows tenancy contract enum; keep console origin separately.
    return {
        "schema_version": "outbox.v1",
        "event_type": "whatsapp.send_text",
        "idempotency_key": idempotency_key,
        "client_id": str(client_id),
        "branch_id": str(branch_id) if branch_id else None,
        "tenant_context": {
            "client_id": str(client_id),
            "branch_id": str(branch_id) if branch_id else None,
            "client_slug": client_slug,
            "instance_id": instance_id,
            "source": "system",
            "origin_source": source,
        },
        "conversation_id": str(conversation_id) if conversation_id else None,
        "channel": "whatsapp",
        "created_at": now.isoformat(),
        "payload": {
            "remote_jid": remote_jid,
            "instance_id": instance_id,
            "idempotency_key": idempotency_key,
            "text": text_value,
        },
    }


def _normalize_pause_minutes(
    value: Optional[int],
    *,
    default: int = 30,
    allow_zero: bool = False,
    max_minutes: int = 24 * 60,
) -> int:
    if value is None:
        return default
    try:
        minutes = int(value)
    except (TypeError, ValueError) as exc:
        raise ConsoleAPIError(400, "INVALID_PARAM", "pause minutes must be an integer") from exc
    min_minutes = 0 if allow_zero else 1
    if minutes < min_minutes or minutes > max_minutes:
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            f"pause minutes must be between {min_minutes} and {max_minutes}",
        )
    return minutes


def _normalize_outreach_destination(value: Optional[str]) -> str:
    normalized = normalize_phone_to_jid(_normalize_optional_text(value))
    if not normalized:
        raise ConsoleAPIError(400, "INVALID_PARAM", "destination must be a WhatsApp phone or JID")
    return normalized


def _resolve_outreach_auto_case_bucket_minutes() -> int:
    raw_value = _normalize_optional_text(os.environ.get("OUTREACH_AUTO_CASE_BUCKET_MINUTES"))
    if raw_value is None:
        return _OUTREACH_AUTO_CASE_BUCKET_MINUTES_DEFAULT
    try:
        parsed = int(raw_value)
    except ValueError:
        return _OUTREACH_AUTO_CASE_BUCKET_MINUTES_DEFAULT
    if parsed < _OUTREACH_AUTO_CASE_BUCKET_MINUTES_MIN:
        return _OUTREACH_AUTO_CASE_BUCKET_MINUTES_MIN
    if parsed > _OUTREACH_AUTO_CASE_BUCKET_MINUTES_MAX:
        return _OUTREACH_AUTO_CASE_BUCKET_MINUTES_MAX
    return parsed


def _resolve_outreach_auto_case_bucket_start(*, now_utc: datetime, bucket_minutes: int) -> datetime:
    bucket_seconds = max(60, bucket_minutes * 60)
    bucket_epoch = int(now_utc.timestamp()) // bucket_seconds * bucket_seconds
    return datetime.fromtimestamp(bucket_epoch, tz=timezone.utc)


def _build_outreach_auto_case_dedupe_key(
    *,
    client_id: UUID,
    branch_id: UUID,
    remote_jid: str,
    bucket_started_at: datetime,
) -> str:
    payload = (
        f"{str(client_id)}:"
        f"{str(branch_id)}:"
        f"{remote_jid.strip().lower()}:"
        f"{int(bucket_started_at.timestamp())}"
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]
    return f"outreach-no-case:{digest}"


def _record_outreach_auto_case_trace(
    *,
    conversation: Conversation,
    case_id: UUID,
    decision: str,
    reason: str,
    dedupe_key: str,
    bucket_started_at: datetime,
    bucket_minutes: int,
) -> None:
    raw_context = getattr(conversation, "context", None)
    context = raw_context if isinstance(raw_context, dict) else {}
    raw_trace = context.get("decision_trace")
    if isinstance(raw_trace, list):
        trace_list = [item for item in raw_trace if isinstance(item, dict)]
    elif isinstance(raw_trace, dict):
        trace_list = [raw_trace]
    else:
        trace_list = []
    trace_list.append(
        {
            "stage": _OUTREACH_AUTO_CASE_TRACE_STAGE,
            "decision": decision,
            "reason": reason,
            "case_id": str(case_id),
            "dedupe_key": dedupe_key,
            "bucket_started_at": bucket_started_at.isoformat(),
            "bucket_minutes": bucket_minutes,
            "source": "console_outreach",
            "ts": datetime.now(timezone.utc).isoformat(),
        }
    )
    if len(trace_list) > _OUTREACH_AUTO_CASE_TRACE_MAX:
        trace_list = trace_list[-_OUTREACH_AUTO_CASE_TRACE_MAX :]
    context["decision_trace"] = trace_list
    conversation.context = context


def _update_outreach_auto_case_meta(
    case: Handover,
    *,
    reason: str,
    dedupe_key: str,
    bucket_started_at: datetime,
    bucket_minutes: int,
) -> None:
    raw_meta = getattr(case, "meta", None)
    meta = raw_meta if isinstance(raw_meta, dict) else {}
    meta["origin"] = "console_outreach"
    meta["auto_case"] = True
    meta["outreach_bootstrap_reason"] = reason
    meta["outreach_dedupe_key"] = dedupe_key
    meta["outreach_dedupe_bucket_started_at"] = bucket_started_at.isoformat()
    meta["outreach_dedupe_bucket_minutes"] = bucket_minutes
    meta["outreach_bootstrap_at"] = datetime.now(timezone.utc).isoformat()
    case.meta = meta


def _resolve_console_conversation_or_404(
    db: Session,
    *,
    client_id: UUID,
    conversation_id: UUID,
) -> Conversation:
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.client_id == client_id,
        )
        .first()
    )
    if not conversation:
        raise ConsoleAPIError(404, "NOT_FOUND", "Conversation not found")
    return conversation


def _bootstrap_outreach_conversation_case(
    db: Session,
    *,
    context: ConsoleAuthContext,
    remote_jid: str,
    branch_id: UUID,
    content: str,
) -> tuple[Conversation, Handover, bool]:
    now_utc = datetime.now(timezone.utc)
    user = get_or_create_user(
        db,
        client_id=context.client.id,
        remote_jid=remote_jid,
    )
    user.last_active_at = now_utc
    digits = _normalize_phone_digits(remote_jid.split("@", 1)[0])
    if digits and not _normalize_phone_digits(user.phone):
        user.phone = digits

    conversation = get_or_create_conversation(
        db,
        client_id=context.client.id,
        user_id=user.id,
        channel="whatsapp",
        branch_id=branch_id,
    )
    locked_conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation.id,
            Conversation.client_id == context.client.id,
        )
        .with_for_update()
        .first()
    )
    if locked_conversation:
        conversation = locked_conversation
    if conversation.branch_id is None:
        conversation.branch_id = branch_id
    conversation.last_message_at = now_utc
    bucket_minutes = _resolve_outreach_auto_case_bucket_minutes()
    bucket_started_at = _resolve_outreach_auto_case_bucket_start(
        now_utc=now_utc,
        bucket_minutes=bucket_minutes,
    )
    dedupe_key = _build_outreach_auto_case_dedupe_key(
        client_id=context.client.id,
        branch_id=branch_id,
        remote_jid=remote_jid,
        bucket_started_at=bucket_started_at,
    )

    existing_case = (
        db.query(Handover)
        .filter(
            Handover.client_id == context.client.id,
            Handover.conversation_id == conversation.id,
            Handover.status.in_(list(_OUTREACH_AUTO_CASE_ACTIVE_STATUSES)),
        )
        .order_by(Handover.created_at.desc())
        .first()
    )
    if existing_case:
        _update_outreach_auto_case_meta(
            existing_case,
            reason="active_case_reused",
            dedupe_key=dedupe_key,
            bucket_started_at=bucket_started_at,
            bucket_minutes=bucket_minutes,
        )
        _record_outreach_auto_case_trace(
            conversation=conversation,
            case_id=existing_case.id,
            decision="case_reused",
            reason="active_case_reused",
            dedupe_key=dedupe_key,
            bucket_started_at=bucket_started_at,
            bucket_minutes=bucket_minutes,
        )
        return conversation, existing_case, False

    dedupe_case = (
        db.query(Handover)
        .filter(
            Handover.client_id == context.client.id,
            Handover.conversation_id == conversation.id,
            Handover.trigger_type == "manual",
            Handover.trigger_value == _OUTREACH_AUTO_CASE_TRIGGER_VALUE,
            Handover.created_at >= bucket_started_at,
        )
        .order_by(Handover.created_at.desc())
        .first()
    )
    if dedupe_case:
        if dedupe_case.status not in _OUTREACH_AUTO_CASE_ACTIVE_STATUSES:
            dedupe_case.status = "active"
            dedupe_case.resolved_at = None
            dedupe_case.resolution_type = None
            dedupe_case.resolution_notes = None
            dedupe_case.first_response_at = dedupe_case.first_response_at or now_utc
        _update_outreach_auto_case_meta(
            dedupe_case,
            reason="dedupe_bucket_reused",
            dedupe_key=dedupe_key,
            bucket_started_at=bucket_started_at,
            bucket_minutes=bucket_minutes,
        )
        _record_outreach_auto_case_trace(
            conversation=conversation,
            case_id=dedupe_case.id,
            decision="case_reused",
            reason="dedupe_bucket_reused",
            dedupe_key=dedupe_key,
            bucket_started_at=bucket_started_at,
            bucket_minutes=bucket_minutes,
        )
        return conversation, dedupe_case, False

    agent_id = str(getattr(context.agent, "id", "")) if getattr(context.agent, "id", None) else None
    agent_name = _normalize_optional_text(getattr(context.agent, "name", None))
    auto_case = Handover(
        conversation_id=conversation.id,
        client_id=context.client.id,
        trigger_type="manual",
        trigger_value=_OUTREACH_AUTO_CASE_TRIGGER_VALUE,
        context_summary=f"Manual outreach without existing case ({remote_jid})",
        messages=[],
        meta={
            "origin": "console_outreach",
            "auto_case": True,
            "destination": remote_jid,
            "branch_id": str(branch_id),
            "outreach_bootstrap_reason": "new_case_created",
            "outreach_dedupe_key": dedupe_key,
            "outreach_dedupe_bucket_started_at": bucket_started_at.isoformat(),
            "outreach_dedupe_bucket_minutes": bucket_minutes,
            "outreach_bootstrap_at": now_utc.isoformat(),
        },
        status="active",
        manager_id=agent_id,
        created_at=now_utc,
        notified_at=now_utc,
        first_response_at=now_utc,
        user_message=content,
        manager_response=content,
        assigned_to_name=agent_name,
        assigned_to=agent_id,
        channel="whatsapp",
        channel_ref=remote_jid,
    )
    if auto_case.id is None:
        auto_case.id = uuid4()
    db.add(auto_case)
    _record_outreach_auto_case_trace(
        conversation=conversation,
        case_id=auto_case.id,
        decision="case_created",
        reason="new_case_created",
        dedupe_key=dedupe_key,
        bucket_started_at=bucket_started_at,
        bucket_minutes=bucket_minutes,
    )
    return conversation, auto_case, True


def _normalize_search_query(
    field_name: str,
    value: Optional[str],
    *,
    max_length: int = 128,
) -> Optional[str]:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if len(trimmed) > max_length:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} too long")
    if not trimmed.isprintable():
        raise ConsoleAPIError(400, "INVALID_PARAM", f"Invalid {field_name}")
    return trimmed


def _looks_like_uuid(value: str) -> Optional[UUID]:
    try:
        return UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None


def _resolve_last_activity_channel(
    *,
    role: Optional[str],
    metadata: Optional[dict],
    conversation_channel: Optional[str],
) -> Optional[str]:
    if not role:
        return None
    if role == "user":
        return conversation_channel or "whatsapp"
    if role == "manager":
        source = None
        if isinstance(metadata, dict):
            source = metadata.get("source")
        if source in ("telegram", "console"):
            return source
        return "console"
    if role in ("assistant", "system"):
        source = None
        if isinstance(metadata, dict):
            source = metadata.get("source")
        if source == "system":
            return "system"
        return conversation_channel or "whatsapp"
    return None


def _format_case_metrics(handover: Handover) -> dict:
    return {
        "first_response_at": handover.first_response_at.isoformat() if handover.first_response_at else None,
        "resolved_at": handover.resolved_at.isoformat() if handover.resolved_at else None,
        "resolution_time_seconds": handover.resolution_time_seconds,
    }


def _fetch_case_health(db: Session, conversation: Conversation) -> dict:
    latest_message = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .first()
    )
    last_inbound_at = (
        db.query(func.max(Message.created_at))
        .filter(Message.conversation_id == conversation.id, Message.role == "user")
        .scalar()
    )
    last_outbound_at = (
        db.query(func.max(Message.created_at))
        .filter(
            Message.conversation_id == conversation.id,
            Message.role.in_(["assistant", "manager", "system"]),
        )
        .scalar()
    )
    outbox_stats = (
        db.query(
            func.sum(
                case(
                    (OutboxMessage.status.in_(["PENDING", "PROCESSING"]), 1),
                    else_=0,
                )
            ).label("pending_count"),
            func.sum(
                case(
                    (OutboxMessage.status == "FAILED", 1),
                    else_=0,
                )
            ).label("failed_count"),
        )
        .filter(OutboxMessage.conversation_id == conversation.id)
        .first()
    )
    pending_count = outbox_stats.pending_count if outbox_stats else 0
    failed_count = outbox_stats.failed_count if outbox_stats else 0
    last_activity_at = latest_message.created_at if latest_message else None
    last_activity_channel = _resolve_last_activity_channel(
        role=latest_message.role if latest_message else None,
        metadata=latest_message.message_metadata if latest_message else None,
        conversation_channel=conversation.channel,
    )
    return {
        "last_inbound_at": last_inbound_at,
        "last_outbound_at": last_outbound_at,
        "last_activity_at": last_activity_at,
        "last_activity_channel": last_activity_channel,
        "last_message_preview": latest_message.content if latest_message else None,
        "needs_reply": bool(
            last_inbound_at and (not last_outbound_at or last_inbound_at > last_outbound_at)
        ),
        "has_delivery_error": bool(failed_count and failed_count > 0),
        "has_pending_outbox": bool(pending_count and pending_count > 0),
    }


def _sync_telegram_after_take(
    db: Session,
    *,
    conversation: Conversation,
    handover: Handover,
    manager_name: str,
) -> ConsoleSyncStatus:
    routing_meta = resolve_telegram_routing(
        db,
        conversation=conversation,
        client_id=conversation.client_id,
    )
    bot_token = routing_meta.get("bot_token")
    chat_id = routing_meta.get("chat_id")
    message_id = handover.telegram_message_id

    if not bot_token or not chat_id or not message_id:
        return _build_sync_status("skipped", "telegram_context_missing")

    telegram = TelegramService(bot_token)
    result = telegram._make_request(
        "editMessageReplyMarkup",
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "reply_markup": {
                "inline_keyboard": [[{"text": "Решено ✅", "callback_data": f"resolve_{handover.id}"}]]
            },
        },
    )
    if not result.get("ok"):
        return _build_sync_status("failed", "telegram_edit_failed")

    if conversation.telegram_topic_id:
        telegram.send_message(
            chat_id=str(chat_id),
            text=f"👤 <b>{manager_name}</b> взял заявку",
            message_thread_id=conversation.telegram_topic_id,
        )

    return _build_sync_status("ok")


def _sync_telegram_after_close(
    db: Session,
    *,
    conversation: Conversation,
    handover: Handover,
    manager_name: str,
    action: str,
) -> ConsoleSyncStatus:
    routing_meta = resolve_telegram_routing(
        db,
        conversation=conversation,
        client_id=conversation.client_id,
    )
    bot_token = routing_meta.get("bot_token")
    chat_id = routing_meta.get("chat_id")
    message_id = handover.telegram_message_id

    if not bot_token or not chat_id or not message_id:
        return _build_sync_status("skipped", "telegram_context_missing")

    telegram = TelegramService(bot_token)
    result = telegram._make_request(
        "editMessageReplyMarkup",
        {"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}},
    )
    if not result.get("ok"):
        return _build_sync_status("failed", "telegram_edit_failed")

    telegram.unpin_message(str(chat_id), message_id)

    if action == "return" and conversation.telegram_topic_id:
        telegram.send_message(
            chat_id=str(chat_id),
            text=f"🤖 Заявка закрыта, бот снова отвечает (by {manager_name})",
            message_thread_id=conversation.telegram_topic_id,
        )

    return _build_sync_status("ok")


def _notify_client_status(
    *,
    db: Session,
    conversation: Conversation,
    handover: Handover,
    status: str,
    manager_name: str,
) -> ConsoleSyncStatus:
    ok, detail = notify_client_manager_status(
        db,
        conversation=conversation,
        handover=handover,
        status=status,
        manager_name=manager_name,
    )
    if ok:
        return _build_sync_status("ok")
    if detail == "remote_jid_missing":
        return _build_sync_status("skipped", detail)
    return _build_sync_status("failed", detail or "notify_failed")


def _require_roles(
    context: ConsoleAuthContext,
    *,
    allowed: tuple[str, ...],
    message: str,
) -> None:
    if context.role not in allowed:
        raise ConsoleAPIError(403, "ACCESS_DENIED", message)


def _require_owner_admin(
    context: ConsoleAuthContext,
    *,
    message: str = "Only owner/admin/platform admin can manage Telegram connector",
) -> None:
    _require_roles(
        context,
        allowed=("platform_admin", "owner", "admin"),
        message=message,
    )


def _generate_verification_code() -> str:
    return secrets.token_hex(3).upper()


def _resolve_telegram_action_target(
    *,
    settings,
    branch,
    scope: str,
    chat_id: Optional[str],
    branch_id: Optional[UUID],
) -> tuple[str, str, Optional[UUID]]:
    if not settings or not getattr(settings, "telegram_bot_token", None):
        raise ConsoleAPIError(400, "TELEGRAM_CONFIG_MISSING", "Telegram bot token is not configured")

    resolved_branch_id = None
    resolved_chat_id = None

    if chat_id:
        resolved_chat_id = chat_id
        if branch_id:
            resolved_branch_id = branch_id
    elif scope == "branch":
        if not branch_id:
            raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id is required for branch scope")
        if not branch:
            raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
        resolved_branch_id = branch_id
        resolved_chat_id = getattr(branch, "telegram_chat_id", None)
        if not resolved_chat_id:
            raise ConsoleAPIError(
                400,
                "TELEGRAM_CONFIG_MISSING",
                "Branch telegram_chat_id is not configured",
                details={"branch_id": str(branch_id)},
            )
    else:
        resolved_chat_id = getattr(settings, "telegram_chat_id", None)
        if not resolved_chat_id:
            raise ConsoleAPIError(400, "TELEGRAM_CONFIG_MISSING", "Client telegram_chat_id is not configured")

    return settings.telegram_bot_token, resolved_chat_id, resolved_branch_id


def _reject_unknown_query_params(request: Request, allowed: set[str]) -> None:
    unknown = sorted(set(request.query_params.keys()) - allowed)
    if unknown:
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            f"Unknown query parameter(s): {', '.join(unknown)}",
        )


def _validate_limit(limit: int) -> None:
    if limit < 1 or limit > 100:
        raise ConsoleAPIError(400, "INVALID_PARAM", "limit must be between 1 and 100")


def _request_with_query_params(request: Request, params: dict[str, object | None]) -> Request:
    scope = dict(request.scope)
    normalized: dict[str, str] = {}
    for key, value in params.items():
        if value is None:
            continue
        normalized[key] = str(value)
    scope["query_string"] = urlencode(normalized).encode("utf-8")
    return Request(scope, receive=request.receive)


def _parse_uuid_param(name: str, value: Optional[str]) -> Optional[UUID]:
    if value is None:
        return None
    if value == "":
        raise ConsoleAPIError(400, "INVALID_PARAM", f"Invalid {name}")
    try:
        return UUID(value)
    except ValueError as exc:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"Invalid {name}") from exc


def _parse_bool_param(name: str, value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise ConsoleAPIError(400, "INVALID_PARAM", f"Invalid {name}")


def _parse_env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_env_csv_set(name: str, *, default: set[str]) -> set[str]:
    raw = os.getenv(name)
    if raw is None:
        return set(default)
    values = [item.strip() for item in raw.split(",")]
    return {value for value in values if value}


def _parse_env_int(
    name: str,
    *,
    default: int,
    min_value: int,
    max_value: int,
) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw.strip())
    except (TypeError, ValueError):
        return default
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def _dedupe_list(values: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


_TENANT_LIFECYCLE_MODES = {"active", "archived", "all"}
_CLIENT_STATUS_ACTIVE = "active"
_CLIENT_STATUS_ARCHIVED = "deleted"
_CLIENT_LIFECYCLE_REASON_MAX_LEN = 500
_ACCESS_REASON_MAX_LEN = 500
_PRIVILEGED_ACCESS_ROLES = {"platform_admin", "owner", "admin"}
_DEPRECATED_CONSOLE_ASSIGNMENT_ROLES = {"support", "specialist"}
_CLIENT_ARCHIVE_SAMPLE_LIMIT = 20
_BRANCH_BOOTSTRAP_ACCOUNTS_MAX = 20
_BRANCH_GO_LIVE_STATES = {"pending", "approved", "rejected"}
_BRANCH_GO_LIVE_DEFAULT_STATE = "pending"
_GO_LIVE_WAIVER_MIN_HOURS = 1
_GO_LIVE_WAIVER_MAX_HOURS = 24 * 30
_ONBOARDING_READINESS_HARD_GATE_DEFAULT_CODES = {
    "delivery:backlog_critical",
    "delivery:failed_24h_critical",
    "delivery:stale_processing_critical",
    "delivery:provider_billing_blocked_critical",
    "delivery:provider_auth_critical",
    "traffic:whatsapp_capability_mismatch",
    "traffic:telegram_capability_mismatch",
}
_ONBOARDING_READINESS_HARD_GATE_ENABLED = _parse_env_bool(
    "ONBOARDING_READINESS_HARD_GATE_ENABLED",
    default=False,
)
_ONBOARDING_READINESS_HARD_GATE_CODES = _parse_env_csv_set(
    "ONBOARDING_READINESS_HARD_GATE_CODES",
    default=_ONBOARDING_READINESS_HARD_GATE_DEFAULT_CODES,
)
_ONBOARDING_READINESS_HARD_GATE_CANARY_BRANCH_IDS = {
    item.strip().lower()
    for item in _parse_env_csv_set(
        "ONBOARDING_READINESS_HARD_GATE_CANARY_BRANCH_IDS",
        default=set(),
    )
    if item.strip()
}
_INTEGRATION_DEFAULT_STALE_MINUTES = 60
_INTEGRATION_MIN_STALE_MINUTES = 5
_INTEGRATION_MAX_STALE_MINUTES = 24 * 60
_PROVIDER_BINDING_EXPIRING_SOON_DAYS = 7
_PROVIDER_OPS_SLA_HOURS_BY_PRIORITY = {
    "p0": 4,
    "p1": 24,
    "p2": 72,
}
_PROVIDER_OPS_DUE_SOON_HOURS = 6
_PROVIDER_OPS_EXECUTE_CONFIRMATION_ACTION = "provider_ops_execute"
_PROVIDER_OPS_RECONCILE_ACTION = "integration_reconcile"
_PROVIDER_OPS_ACTIONS = {
    "integration_reconcile",
    "provider_start_rebind",
    "provider_complete_rebind",
    "provider_renewal_confirmed",
    "provider_webhook_updated",
    "provider_send_reminder",
}
_INTEGRATION_ALERT_ISSUES = {
    "instance_id_mismatch",
    "invalid_webhook_url",
    "invalid_webhook_secret",
    "inbound_without_outbound",
    "no_recent_inbound",
    "provider_binding_rebind_required",
    "provider_binding_expired",
    "provider_binding_expiring_soon",
}
_INTEGRATION_DRIFT_STATE: dict[str, str] = {}
_INTEGRATION_DRIFT_LOCK = Lock()
_FLEET_LIFECYCLE_STATES = {
    "lead",
    "contracting",
    "onboarding",
    "go_live_ready",
    "active",
    "paused",
    "archived",
}
_FLEET_PAYMENT_STATES = {"pending", "confirmed", "rejected", "unknown"}
_FLEET_SERVICE_STATES = {"ok", "degraded", "attention"}
_FLEET_COMMERCIAL_STATES = {
    "payment_confirmed",
    "payment_pending",
    "payment_rejected",
    "contract_missing",
}
_FLEET_NEXT_ACTION_STATES = {
    "qualify_and_collect_contract",
    "collect_signed_contract_and_payment",
    "complete_onboarding_steps",
    "confirm_payment_and_approve_go_live",
    "approve_go_live",
    "resolve_payment_or_service_blocker",
    "archived_no_action",
    "run_integration_recovery",
    "resolve_attention_items",
    "monitor_sla_and_quality",
}
_FLEET_LIFECYCLE_ORDER = [
    "lead",
    "contracting",
    "onboarding",
    "go_live_ready",
    "active",
    "paused",
    "archived",
]
_FLEET_PAYMENT_ORDER = ["pending", "confirmed", "rejected", "unknown"]
_FLEET_SERVICE_ORDER = ["ok", "degraded", "attention"]
_FLEET_ATTENTION_OUTBOX_WINDOW_HOURS = 24
_FLEET_ATTENTION_HANDOVER_PENDING_STATUSES = {"pending", "active"}
_FLEET_ATTENTION_HIGH_THRESHOLD = 70
_FLEET_ATTENTION_MEDIUM_THRESHOLD = 35
_FLEET_REFERENCE_BRANCH_RECENT_INBOUND_DAYS = 30
_ONBOARDING_THROUGHPUT_WINDOW_HOURS = 30 * 24
_TENANTS_FLEET_CACHE_TABLE_NAME = "tenants_fleet_cache"
_TENANTS_FLEET_PREWARM_JOB_TABLE_NAME = "tenants_fleet_prewarm_jobs"
_TENANTS_FLEET_CACHE_SUMMARY_TYPE = "fleet_summary"
_TENANTS_FLEET_CACHE_ATTENTION_TYPE = "fleet_attention"
_TENANTS_FLEET_CACHE_SCHEMA_VERSION = "v1"
_TENANTS_FLEET_CACHE_TTL_SECONDS = _parse_env_int(
    "TENANTS_FLEET_CACHE_TTL_SECONDS",
    default=180,
    min_value=30,
    max_value=3600,
)
_TENANTS_FLEET_CACHE_ASYNC_REFRESH_ENABLED = _parse_env_bool(
    "TENANTS_FLEET_CACHE_ASYNC_REFRESH_ENABLED",
    default=True,
)
_TENANTS_FLEET_CACHE_ASYNC_REFRESH_BUFFER_SECONDS = _parse_env_int(
    "TENANTS_FLEET_CACHE_ASYNC_REFRESH_BUFFER_SECONDS",
    default=60,
    min_value=10,
    max_value=1800,
)
_TENANTS_FLEET_CACHE_ASYNC_MAX_SCOPE_CLIENTS = _parse_env_int(
    "TENANTS_FLEET_CACHE_ASYNC_MAX_SCOPE_CLIENTS",
    default=5000,
    min_value=50,
    max_value=100000,
)
_TENANTS_FLEET_CACHE_PREWARM_ON_INVALIDATION_ENABLED = _parse_env_bool(
    "TENANTS_FLEET_CACHE_PREWARM_ON_INVALIDATION_ENABLED",
    default=True,
)
_TENANTS_FLEET_CACHE_PREWARM_MAX_COMPANY_SCOPES = _parse_env_int(
    "TENANTS_FLEET_CACHE_PREWARM_MAX_COMPANY_SCOPES",
    default=50,
    min_value=1,
    max_value=10000,
)
_TENANTS_FLEET_CACHE_PREWARM_GLOBAL_SCOPE_ENABLED = _parse_env_bool(
    "TENANTS_FLEET_CACHE_PREWARM_GLOBAL_SCOPE_ENABLED",
    default=True,
)
_TENANTS_FLEET_CACHE_PREWARM_GLOBAL_MAX_ACTIVE_CLIENTS = _parse_env_int(
    "TENANTS_FLEET_CACHE_PREWARM_GLOBAL_MAX_ACTIVE_CLIENTS",
    default=20000,
    min_value=100,
    max_value=200000,
)
_TENANTS_FLEET_CACHE_PREWARM_GLOBAL_ATTENTION_LIMIT = _parse_env_int(
    "TENANTS_FLEET_CACHE_PREWARM_GLOBAL_ATTENTION_LIMIT",
    default=20,
    min_value=1,
    max_value=200,
)
_TENANTS_FLEET_CACHE_PREWARM_COMPANY_ATTENTION_LIMIT = _parse_env_int(
    "TENANTS_FLEET_CACHE_PREWARM_COMPANY_ATTENTION_LIMIT",
    default=20,
    min_value=1,
    max_value=200,
)
_TENANTS_FLEET_CACHE_PREWARM_GLOBAL_MIN_INTERVAL_SECONDS = _parse_env_int(
    "TENANTS_FLEET_CACHE_PREWARM_GLOBAL_MIN_INTERVAL_SECONDS",
    default=30,
    min_value=1,
    max_value=3600,
)
_TENANTS_FLEET_PREWARM_DISPATCH_QUEUE_MAX = _parse_env_int(
    "TENANTS_FLEET_PREWARM_DISPATCH_QUEUE_MAX",
    default=512,
    min_value=16,
    max_value=10000,
)
_TENANTS_FLEET_PREWARM_DISPATCH_BATCH_MAX = _parse_env_int(
    "TENANTS_FLEET_PREWARM_DISPATCH_BATCH_MAX",
    default=64,
    min_value=1,
    max_value=512,
)
_TENANTS_FLEET_PREWARM_DISPATCH_STUCK_SECONDS = _parse_env_int(
    "TENANTS_FLEET_PREWARM_DISPATCH_STUCK_SECONDS",
    default=120,
    min_value=30,
    max_value=7200,
)
_OUTBOX_ARCHIVED_REASON_PREFIX = "archived_pending:"
_OUTBOX_CALENDAR_SYNC_REASON_PREFIX = "calendar_sync_failed:"
_OUTBOX_SYSTEM_EVENT_TYPES = {"calendar.sync_inbound", "calendar.sync_outbound"}
_DEFAULT_RUNTIME_REDIS_URL = "redis://truffles_redis_1:6379/0"
_OUTREACH_AUTO_CASE_BUCKET_MINUTES_DEFAULT = 30
_OUTREACH_AUTO_CASE_BUCKET_MINUTES_MIN = 1
_OUTREACH_AUTO_CASE_BUCKET_MINUTES_MAX = 240
_OUTREACH_AUTO_CASE_TRACE_MAX = 100
_OUTREACH_AUTO_CASE_TRACE_STAGE = "outreach_auto_case_bootstrap"
_OUTREACH_AUTO_CASE_TRIGGER_VALUE = "console_outreach_no_case"
_OUTREACH_AUTO_CASE_ACTIVE_STATUSES = {"pending", "active"}
_TENANTS_WEEKLY_SNAPSHOT_EVENT_TYPE = "tenants_weekly_snapshot_saved"
_TENANTS_WEEKLY_SNAPSHOT_ENTITY_TYPE = "tenant_snapshot"
_TENANTS_WEEKLY_SNAPSHOT_TABLE_NAME = "tenants_weekly_snapshots"
_TENANTS_FLEET_CLIENT_PROJECTION_TABLE_NAME = "tenants_fleet_client_projection"
_TENANTS_WEEKLY_SNAPSHOT_WEEK_KEY_PATTERN = re.compile(r"^\d{4}-W\d{2}$")
_TENANTS_SENSITIVE_ACCESS_EVENT_TYPE = "tenants_sensitive_id_accessed"
_TENANTS_SENSITIVE_FIELDS = {"instance_id"}
_TENANTS_SENSITIVE_ACTIONS = {"reveal", "copy"}
_TENANTS_FLEET_CACHE_REFRESH_INFLIGHT: set[str] = set()
_TENANTS_FLEET_CACHE_REFRESH_LOCK = Lock()
_TENANTS_FLEET_CACHE_PREWARM_COMPANY_IDS_INFO_KEY = "tenants_fleet_cache_prewarm_company_ids"
_TENANTS_FLEET_CACHE_PREWARM_GLOBAL_INFO_KEY = "tenants_fleet_cache_prewarm_global"
_TENANTS_FLEET_CACHE_PREWARM_EVENTS_INFO_KEY = "tenants_fleet_cache_prewarm_events"
_TENANTS_FLEET_CACHE_GLOBAL_PREWARM_LOCK = Lock()
_TENANTS_FLEET_CACHE_GLOBAL_PREWARM_NEXT_ALLOWED_AT = 0.0
_TENANTS_FLEET_PREWARM_DISPATCH_QUEUE: deque[dict[str, Any]] = deque()
_TENANTS_FLEET_PREWARM_DISPATCH_LOCK = Lock()
_TENANTS_FLEET_PREWARM_DISPATCH_WORKER: Optional[Thread] = None
_TENANTS_FLEET_PREWARM_JOB_STATUS_PENDING = "pending"
_TENANTS_FLEET_PREWARM_JOB_STATUS_PROCESSING = "processing"
_TENANTS_FLEET_PREWARM_JOB_STATUS_DONE = "done"
_TENANTS_FLEET_CLIENT_PROJECTION_ENABLED = _parse_env_bool(
    "TENANTS_FLEET_CLIENT_PROJECTION_ENABLED",
    default=True,
)
_TENANTS_FLEET_CLIENT_PROJECTION_MAX_SYNC_CLIENTS = _parse_env_int(
    "TENANTS_FLEET_CLIENT_PROJECTION_MAX_SYNC_CLIENTS",
    default=8000,
    min_value=100,
    max_value=100000,
)
_TENANTS_FLEET_CLIENT_PROJECTION_COMPACTION_MAX_CLIENTS = _parse_env_int(
    "TENANTS_FLEET_CLIENT_PROJECTION_COMPACTION_MAX_CLIENTS",
    default=4000,
    min_value=100,
    max_value=100000,
)
_TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_ENABLED = _parse_env_bool(
    "TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_ENABLED",
    default=True,
)
_TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_INTERVAL_SECONDS = _parse_env_int(
    "TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_INTERVAL_SECONDS",
    default=300,
    min_value=10,
    max_value=86400,
)
_TENANTS_FLEET_CLIENT_PROJECTION_STALE_AFTER_SECONDS = _parse_env_int(
    "TENANTS_FLEET_CLIENT_PROJECTION_STALE_AFTER_SECONDS",
    default=86400 * 7,
    min_value=300,
    max_value=86400 * 365,
)
_TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_MAX_DELETE = _parse_env_int(
    "TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_MAX_DELETE",
    default=2000,
    min_value=50,
    max_value=100000,
)
_TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_ENABLED = _parse_env_bool(
    "TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_ENABLED",
    default=True,
)
_TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_MAX_CLIENTS = _parse_env_int(
    "TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_MAX_CLIENTS",
    default=500,
    min_value=10,
    max_value=100000,
)
_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_ENABLED = _parse_env_bool(
    "TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_ENABLED",
    default=True,
)
_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_MAX_COMPANY_SCOPES = _parse_env_int(
    "TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_MAX_COMPANY_SCOPES",
    default=20,
    min_value=1,
    max_value=512,
)
_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_MIN_INTERVAL_SECONDS = _parse_env_int(
    "TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_MIN_INTERVAL_SECONDS",
    default=120,
    min_value=0,
    max_value=86400,
)
_TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_LOCK = Lock()
_TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_NEXT_ALLOWED_AT = 0.0
_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_LOCK = Lock()
_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_NEXT_ALLOWED_BY_COMPANY: dict[UUID, float] = {}


@dataclass
class _FleetClientDetails:
    lifecycle_state: str
    payment_status: str
    commercial_state: str
    service_state: str
    owner_name: Optional[str]
    next_action: str
    total_branches: int
    active_branches: int
    degraded_branches: int
    go_live_ready_branches: int
    reference_branch_ids: tuple[UUID, ...] = ()
    reference_branch_reason: str = "no_active_branches"


@dataclass
class _TenantsFleetCacheEntry:
    payload_json: dict[str, Any]
    generated_at: datetime
    expires_at: datetime


@dataclass
class _MembershipTarget:
    scope: str
    company_id: Optional[UUID]
    client_id: Optional[UUID]
    branch_id: Optional[UUID]
    company: Optional[Company]
    client: Optional[Client]
    branch: Optional[Branch]


def _parse_tenant_lifecycle_param(value: Optional[str]) -> str:
    if value is None:
        return "active"
    normalized = value.strip().lower()
    if normalized not in _TENANT_LIFECYCLE_MODES:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid lifecycle")
    return normalized


def _normalize_tenants_weekly_snapshot_week_key(value: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ConsoleAPIError(400, "INVALID_PARAM", "week_key required")
    if not _TENANTS_WEEKLY_SNAPSHOT_WEEK_KEY_PATTERN.match(normalized):
        raise ConsoleAPIError(400, "INVALID_PARAM", "week_key must match YYYY-Wnn")
    year_part, week_part = normalized.split("-W")
    try:
        iso_year = int(year_part)
        iso_week = int(week_part)
        # Validate that week exists in the given ISO year.
        datetime.fromisocalendar(iso_year, iso_week, 1)
    except ValueError as exc:
        raise ConsoleAPIError(400, "INVALID_PARAM", "week_key must be valid ISO week") from exc
    return f"{iso_year:04d}-W{iso_week:02d}"


def _normalize_tenants_weekly_snapshot_payload(
    value: Optional[dict | ConsoleTenantsWeeklySnapshotPayload],
) -> dict:
    if isinstance(value, ConsoleTenantsWeeklySnapshotPayload):
        return value.model_dump(mode="json")
    if not isinstance(value, dict):
        raise ConsoleAPIError(400, "INVALID_PARAM", "snapshot must be object")
    try:
        normalized = ConsoleTenantsWeeklySnapshotPayload.model_validate(value)
    except ValidationError as exc:
        raise ConsoleAPIError(400, "INVALID_PARAM", "snapshot schema invalid") from exc
    return normalized.model_dump(mode="json")


def _normalize_tenants_sensitive_access_field(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in _TENANTS_SENSITIVE_FIELDS:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Unsupported sensitive field")
    return normalized


def _normalize_tenants_sensitive_access_action(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in _TENANTS_SENSITIVE_ACTIONS:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Unsupported action")
    return normalized


def _serialize_tenants_weekly_snapshot_record(event: AuditEvent) -> ConsoleTenantsWeeklySnapshotRecord:
    payload = event.payload if isinstance(event.payload, dict) else {}
    week_key = payload.get("week_key")
    snapshot_payload = payload.get("snapshot")
    snapshot_schema_version = payload.get("snapshot_schema_version")
    try:
        snapshot = ConsoleTenantsWeeklySnapshotPayload.model_validate(snapshot_payload)
    except ValidationError:
        snapshot = ConsoleTenantsWeeklySnapshotPayload(
            generatedAt=event.created_at.isoformat(),
            sourceWindow=0,
            workspaceMode="portfolio",
            lifecycleMode="active",
            kpi={
                "onboardingCoverage": 0,
                "goLiveReadiness": 0,
                "serviceStability": 0,
                "decommissionShare": 0,
                "changeFailure": 0,
                "rollbackShare": 0,
                "blockedSignals": 0,
            },
            drilldown=[],
            attentionSummary={
                "activeClientsTotal": 0,
                "highRiskClients": 0,
                "mediumRiskClients": 0,
                "outboxFailed24hTotal": 0,
                "pendingHandoversTotal": 0,
            },
        )
    return ConsoleTenantsWeeklySnapshotRecord(
        id=event.id,
        created_at=event.created_at.isoformat(),
        client_id=event.client_id,
        week_key=week_key if isinstance(week_key, str) else "",
        snapshot=snapshot,
        snapshot_schema_version=snapshot_schema_version if isinstance(snapshot_schema_version, str) else "v1",
        actor_name=event.actor_name,
    )


def _serialize_tenants_weekly_snapshot_row(
    row: TenantsWeeklySnapshot,
) -> ConsoleTenantsWeeklySnapshotRecord:
    snapshot_payload = row.snapshot if isinstance(row.snapshot, dict) else {}
    try:
        snapshot = ConsoleTenantsWeeklySnapshotPayload.model_validate(snapshot_payload)
    except ValidationError:
        snapshot = ConsoleTenantsWeeklySnapshotPayload(
            generatedAt=row.updated_at.isoformat(),
            sourceWindow=0,
            workspaceMode="portfolio",
            lifecycleMode="active",
            kpi={
                "onboardingCoverage": 0,
                "goLiveReadiness": 0,
                "serviceStability": 0,
                "decommissionShare": 0,
                "changeFailure": 0,
                "rollbackShare": 0,
                "blockedSignals": 0,
            },
            drilldown=[],
            attentionSummary={
                "activeClientsTotal": 0,
                "highRiskClients": 0,
                "mediumRiskClients": 0,
                "outboxFailed24hTotal": 0,
                "pendingHandoversTotal": 0,
            },
        )

    return ConsoleTenantsWeeklySnapshotRecord(
        id=row.id,
        created_at=row.updated_at.isoformat(),
        client_id=row.client_id,
        week_key=row.week_key,
        snapshot=snapshot,
        snapshot_schema_version=(row.snapshot_schema_version or "v1").strip() or "v1",
        actor_name=row.actor_name,
    )


def _build_weekly_snapshot_schema_versions(
    items: list[ConsoleTenantsWeeklySnapshotRecord],
) -> dict[str, int]:
    versions: dict[str, int] = {}
    for item in items:
        version = (item.snapshot_schema_version or "").strip() or "unknown"
        versions[version] = versions.get(version, 0) + 1
    return versions


def _is_tenants_weekly_snapshot_table_missing_error(exc: ProgrammingError) -> bool:
    message = str(exc.orig if getattr(exc, "orig", None) is not None else exc).lower()
    return (
        _TENANTS_WEEKLY_SNAPSHOT_TABLE_NAME in message
        and "does not exist" in message
    )


def _is_tenants_fleet_cache_table_missing_error(exc: ProgrammingError) -> bool:
    message = str(exc.orig if getattr(exc, "orig", None) is not None else exc).lower()
    return (
        _TENANTS_FLEET_CACHE_TABLE_NAME in message
        and "does not exist" in message
    )


def _is_tenants_fleet_prewarm_job_table_missing_error(exc: ProgrammingError) -> bool:
    message = str(exc.orig if getattr(exc, "orig", None) is not None else exc).lower()
    return (
        _TENANTS_FLEET_PREWARM_JOB_TABLE_NAME in message
        and "does not exist" in message
    )


def _is_tenants_fleet_client_projection_table_missing_error(exc: ProgrammingError) -> bool:
    message = str(exc.orig if getattr(exc, "orig", None) is not None else exc).lower()
    return (
        _TENANTS_FLEET_CLIENT_PROJECTION_TABLE_NAME in message
        and "does not exist" in message
    )


def _hash_uuid_values(values: set[UUID]) -> str:
    if not values:
        return "none"
    payload = ",".join(sorted(str(value) for value in values))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_tenants_fleet_cache_scope_key(scope: dict[str, Any]) -> str:
    encoded = json.dumps(scope, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _build_clients_query_for_scope(
    db: Session,
    *,
    accessible_client_ids: set[UUID],
    lifecycle_mode: str,
    company_uuid: Optional[UUID],
    query_value: Optional[str],
    cursor_cutoff: Optional[datetime],
):
    query = db.query(Client)
    if accessible_client_ids:
        query = query.filter(Client.id.in_(list(accessible_client_ids)))
    # Keep legacy platform_admin behavior for empty in-memory scope in tests/recovery paths.
    if lifecycle_mode == "active":
        query = query.filter(Client.status == "active")
    elif lifecycle_mode == "archived":
        query = query.filter(Client.status != "active")
    if company_uuid:
        query = query.filter(Client.company_id == company_uuid)
    if query_value:
        query_value_lower = query_value.lower()
        uuid_value = _looks_like_uuid(query_value)
        filters = []
        if uuid_value:
            filters.append(Client.id == uuid_value)
        filters.append(func.lower(Client.name).like(f"%{query_value_lower}%"))
        query = query.filter(or_(*filters))
    if cursor_cutoff is not None:
        query = query.filter(Client.created_at < cursor_cutoff)
    return query


def _build_clients_summary_cache_scope_key(
    *,
    accessible_clients_hash: str,
    company_uuid: Optional[UUID],
    lifecycle_mode: str,
    query_value: Optional[str],
    fleet_lifecycle_filter: Optional[str],
    payment_status_filter: Optional[str],
    service_state_filter: Optional[str],
) -> str:
    return _build_tenants_fleet_cache_scope_key(
        {
            "scope": "clients_summary",
            "accessible_clients_hash": accessible_clients_hash,
            "company_id": str(company_uuid) if company_uuid else None,
            "lifecycle": lifecycle_mode,
            "q": query_value,
            "fleet_lifecycle": fleet_lifecycle_filter,
            "payment_status": payment_status_filter,
            "service_state": service_state_filter,
        }
    )


def _build_fleet_attention_cache_scope_key(
    *,
    active_client_ids: set[UUID],
    stale_after_minutes: int,
    include_low_mode: bool,
    limit: int,
) -> str:
    return _build_tenants_fleet_cache_scope_key(
        {
            "scope": "fleet_attention",
            "active_clients_hash": _hash_uuid_values(active_client_ids),
            "stale_after_minutes": stale_after_minutes,
            "include_low": include_low_mode,
            "limit": limit,
        }
    )


def _fleet_cache_refresh_token(cache_type: str, scope_key: str) -> str:
    return f"{cache_type}:{scope_key}"


def _try_claim_fleet_cache_refresh(cache_type: str, scope_key: str) -> bool:
    token = _fleet_cache_refresh_token(cache_type, scope_key)
    with _TENANTS_FLEET_CACHE_REFRESH_LOCK:
        if token in _TENANTS_FLEET_CACHE_REFRESH_INFLIGHT:
            return False
        _TENANTS_FLEET_CACHE_REFRESH_INFLIGHT.add(token)
    return True


def _release_fleet_cache_refresh(cache_type: str, scope_key: str) -> None:
    token = _fleet_cache_refresh_token(cache_type, scope_key)
    with _TENANTS_FLEET_CACHE_REFRESH_LOCK:
        _TENANTS_FLEET_CACHE_REFRESH_INFLIGHT.discard(token)


def _load_tenants_fleet_cache_entry(
    db: Session,
    *,
    cache_type: str,
    scope_key: str,
    now: datetime,
) -> Optional[_TenantsFleetCacheEntry]:
    try:
        row = (
            db.query(TenantsFleetCache)
            .filter(
                TenantsFleetCache.cache_type == cache_type,
                TenantsFleetCache.scope_key == scope_key,
                TenantsFleetCache.expires_at > now,
            )
            .first()
        )
    except ProgrammingError as exc:
        db.rollback()
        if _is_tenants_fleet_cache_table_missing_error(exc):
            return None
        return None
    except Exception:
        db.rollback()
        return None
    if row is None or not isinstance(row.payload_json, dict):
        return None
    generated_at = row.generated_at if isinstance(row.generated_at, datetime) else now
    expires_at = row.expires_at if isinstance(row.expires_at, datetime) else now
    return _TenantsFleetCacheEntry(
        payload_json=row.payload_json,
        generated_at=generated_at,
        expires_at=expires_at,
    )


def _load_tenants_fleet_cache_payload(
    db: Session,
    *,
    cache_type: str,
    scope_key: str,
    now: datetime,
) -> Optional[dict[str, Any]]:
    entry = _load_tenants_fleet_cache_entry(
        db,
        cache_type=cache_type,
        scope_key=scope_key,
        now=now,
    )
    if entry is None:
        return None
    return entry.payload_json


def _upsert_tenants_fleet_cache_payload(
    db: Session,
    *,
    cache_type: str,
    scope_key: str,
    scope_company_id: Optional[UUID] = None,
    scope_client_id: Optional[UUID] = None,
    payload: dict[str, Any],
    now: datetime,
    ttl_seconds: int = _TENANTS_FLEET_CACHE_TTL_SECONDS,
) -> None:
    expires_at = now + timedelta(seconds=max(ttl_seconds, 1))
    try:
        row = (
            db.query(TenantsFleetCache)
            .filter(
                TenantsFleetCache.cache_type == cache_type,
                TenantsFleetCache.scope_key == scope_key,
            )
            .first()
        )
        if row is None:
            row = TenantsFleetCache(
                cache_type=cache_type,
                scope_key=scope_key,
            )
            db.add(row)
        row.payload_json = payload
        row.scope_company_id = scope_company_id
        row.scope_client_id = scope_client_id
        row.schema_version = _TENANTS_FLEET_CACHE_SCHEMA_VERSION
        row.generated_at = now
        row.expires_at = expires_at
        row.updated_at = now
        db.commit()
    except ProgrammingError as exc:
        db.rollback()
        if _is_tenants_fleet_cache_table_missing_error(exc):
            return
        return
    except Exception:
        db.rollback()
        return


def _load_cached_fleet_summary(
    db: Session,
    *,
    scope_key: str,
    now: datetime,
) -> Optional[ConsoleFleetSummary]:
    payload = _load_tenants_fleet_cache_payload(
        db,
        cache_type=_TENANTS_FLEET_CACHE_SUMMARY_TYPE,
        scope_key=scope_key,
        now=now,
    )
    if not isinstance(payload, dict):
        return None
    try:
        return ConsoleFleetSummary.model_validate(payload)
    except ValidationError:
        return None


def _store_cached_fleet_summary(
    db: Session,
    *,
    scope_key: str,
    scope_company_id: Optional[UUID],
    now: datetime,
    summary: ConsoleFleetSummary,
) -> None:
    _upsert_tenants_fleet_cache_payload(
        db,
        cache_type=_TENANTS_FLEET_CACHE_SUMMARY_TYPE,
        scope_key=scope_key,
        scope_company_id=scope_company_id,
        payload=summary.model_dump(mode="json"),
        now=now,
    )


def _load_cached_fleet_attention(
    db: Session,
    *,
    scope_key: str,
    now: datetime,
) -> Optional[ConsoleFleetAttentionResponse]:
    payload = _load_tenants_fleet_cache_payload(
        db,
        cache_type=_TENANTS_FLEET_CACHE_ATTENTION_TYPE,
        scope_key=scope_key,
        now=now,
    )
    if not isinstance(payload, dict):
        return None
    try:
        return ConsoleFleetAttentionResponse.model_validate(payload)
    except ValidationError:
        return None


def _store_cached_fleet_attention(
    db: Session,
    *,
    scope_key: str,
    scope_company_id: Optional[UUID] = None,
    now: datetime,
    response: ConsoleFleetAttentionResponse,
) -> None:
    _upsert_tenants_fleet_cache_payload(
        db,
        cache_type=_TENANTS_FLEET_CACHE_ATTENTION_TYPE,
        scope_key=scope_key,
        scope_company_id=scope_company_id,
        payload=response.model_dump(mode="json"),
        now=now,
    )


def _is_fleet_cache_async_refresh_due(
    db: Session,
    *,
    cache_type: str,
    scope_key: str,
    now: datetime,
) -> bool:
    if not _TENANTS_FLEET_CACHE_ASYNC_REFRESH_ENABLED:
        return False
    entry = _load_tenants_fleet_cache_entry(
        db,
        cache_type=cache_type,
        scope_key=scope_key,
        now=now,
    )
    if entry is None:
        return False
    remaining_seconds = (entry.expires_at - now).total_seconds()
    return remaining_seconds <= _TENANTS_FLEET_CACHE_ASYNC_REFRESH_BUFFER_SECONDS


def _refresh_fleet_summary_cache_worker(task: dict[str, Any]) -> None:
    scope_key = str(task.get("scope_key") or "").strip()
    if not scope_key:
        return
    db = SessionLocal()
    try:
        raw_client_ids = task.get("accessible_client_ids") or []
        accessible_client_ids = {
            UUID(str(raw_id))
            for raw_id in raw_client_ids
            if raw_id
        }
        if not accessible_client_ids:
            return

        company_id_raw = task.get("company_id")
        company_uuid = UUID(str(company_id_raw)) if company_id_raw else None
        lifecycle_mode = str(task.get("lifecycle_mode") or "active").strip().lower()
        if lifecycle_mode not in _TENANT_LIFECYCLE_MODES:
            lifecycle_mode = "active"

        query_value_raw = task.get("query_value")
        query_value = str(query_value_raw).strip() if isinstance(query_value_raw, str) and query_value_raw.strip() else None
        fleet_lifecycle_filter = (
            str(task.get("fleet_lifecycle_filter")).strip().lower()
            if isinstance(task.get("fleet_lifecycle_filter"), str)
            else None
        )
        payment_status_filter = (
            str(task.get("payment_status_filter")).strip().lower()
            if isinstance(task.get("payment_status_filter"), str)
            else None
        )
        service_state_filter = (
            str(task.get("service_state_filter")).strip().lower()
            if isinstance(task.get("service_state_filter"), str)
            else None
        )
        batch_size_raw = task.get("batch_size")
        batch_size = int(batch_size_raw) if isinstance(batch_size_raw, int) and batch_size_raw > 0 else 100

        def _build_query(cursor_cutoff: Optional[datetime]):
            return _build_clients_query_for_scope(
                db,
                accessible_client_ids=accessible_client_ids,
                lifecycle_mode=lifecycle_mode,
                company_uuid=company_uuid,
                query_value=query_value,
                cursor_cutoff=cursor_cutoff,
            )

        materialize_projection = (
            _TENANTS_FLEET_CLIENT_PROJECTION_ENABLED
            and lifecycle_mode == "active"
            and query_value is None
            and fleet_lifecycle_filter is None
            and payment_status_filter is None
            and service_state_filter is None
        )
        materialize_processed_clients = 0
        materialize_truncated = False
        materialized_company_client_ids: set[UUID] = set()
        materialize_now = datetime.now(timezone.utc)

        def _on_batch_details(batch_clients: list[Client], details_map: dict[UUID, _FleetClientDetails]) -> None:
            nonlocal materialize_projection
            nonlocal materialize_processed_clients
            nonlocal materialize_truncated
            if not materialize_projection:
                return
            if materialize_processed_clients >= _TENANTS_FLEET_CLIENT_PROJECTION_MAX_SYNC_CLIENTS:
                materialize_truncated = True
                return
            remaining = _TENANTS_FLEET_CLIENT_PROJECTION_MAX_SYNC_CLIENTS - materialize_processed_clients
            selected_clients = batch_clients[:remaining]
            if not selected_clients:
                return
            selected_details: dict[UUID, _FleetClientDetails] = {}
            company_id_by_client: dict[UUID, Optional[UUID]] = {}
            for client in selected_clients:
                details = details_map.get(client.id)
                if not details:
                    continue
                selected_details[client.id] = details
                company_id_by_client[client.id] = client.company_id
                if company_uuid and client.company_id == company_uuid:
                    materialized_company_client_ids.add(client.id)
            if not selected_details:
                return
            persisted = _upsert_materialized_fleet_client_details(
                db,
                details_by_client_id=selected_details,
                company_id_by_client_id=company_id_by_client,
                now=materialize_now,
            )
            if not persisted:
                materialize_projection = False
                return
            materialize_processed_clients += len(selected_details)
            if len(batch_clients) > remaining:
                materialize_truncated = True

        summary = _build_fleet_summary_for_scope(
            db,
            build_client_query=_build_query,
            fleet_lifecycle=fleet_lifecycle_filter,
            payment_status=payment_status_filter,
            service_state=service_state_filter,
            batch_size=batch_size,
            on_batch_details=_on_batch_details,
            persist_projection_missing=(
                _TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_ENABLED
                and not materialize_projection
            ),
            persist_projection_missing_max_clients=_TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_MAX_CLIENTS,
        )
        if (
            materialize_projection
            and company_uuid is not None
            and not materialize_truncated
        ):
            _compact_materialized_fleet_client_scope(
                db,
                company_id=company_uuid,
                keep_client_ids=materialized_company_client_ids,
            )
        _store_cached_fleet_summary(
            db,
            scope_key=scope_key,
            scope_company_id=company_uuid,
            now=materialize_now,
            summary=summary,
        )
    except Exception:
        db.rollback()
    finally:
        db.close()
        _maybe_run_fleet_projection_maintenance()
        _release_fleet_cache_refresh(_TENANTS_FLEET_CACHE_SUMMARY_TYPE, scope_key)


def _schedule_fleet_summary_async_refresh(
    db: Session,
    *,
    scope_key: str,
    accessible_client_ids: set[UUID],
    lifecycle_mode: str,
    company_uuid: Optional[UUID],
    query_value: Optional[str],
    fleet_lifecycle_filter: Optional[str],
    payment_status_filter: Optional[str],
    service_state_filter: Optional[str],
    batch_size: int,
    now: datetime,
) -> None:
    if not _TENANTS_FLEET_CACHE_ASYNC_REFRESH_ENABLED:
        return
    if not accessible_client_ids:
        return
    if len(accessible_client_ids) > _TENANTS_FLEET_CACHE_ASYNC_MAX_SCOPE_CLIENTS:
        return
    if not _is_fleet_cache_async_refresh_due(
        db,
        cache_type=_TENANTS_FLEET_CACHE_SUMMARY_TYPE,
        scope_key=scope_key,
        now=now,
    ):
        return
    if not _try_claim_fleet_cache_refresh(_TENANTS_FLEET_CACHE_SUMMARY_TYPE, scope_key):
        return
    task = {
        "scope_key": scope_key,
        "accessible_client_ids": [str(client_id) for client_id in sorted(accessible_client_ids, key=str)],
        "lifecycle_mode": lifecycle_mode,
        "company_id": str(company_uuid) if company_uuid else None,
        "query_value": query_value,
        "fleet_lifecycle_filter": fleet_lifecycle_filter,
        "payment_status_filter": payment_status_filter,
        "service_state_filter": service_state_filter,
        "batch_size": batch_size,
    }
    _start_fleet_summary_refresh_task(
        scope_key=scope_key,
        task=task,
        thread_name="tenants-fleet-summary-refresh",
    )


def _start_fleet_summary_refresh_task(
    *,
    scope_key: str,
    task: dict[str, Any],
    thread_name: str,
) -> None:
    try:
        Thread(
            target=_refresh_fleet_summary_cache_worker,
            kwargs={"task": task},
            daemon=True,
            name=thread_name,
        ).start()
    except Exception:
        _release_fleet_cache_refresh(_TENANTS_FLEET_CACHE_SUMMARY_TYPE, scope_key)


def _queue_fleet_summary_prewarm_company_ids(
    db: Session,
    *,
    company_ids: set[UUID],
) -> None:
    if not _TENANTS_FLEET_CACHE_PREWARM_ON_INVALIDATION_ENABLED:
        return
    if not company_ids:
        return
    scoped_ids = {company_id for company_id in company_ids if company_id is not None}
    if not scoped_ids:
        return
    info_value = db.info.get(_TENANTS_FLEET_CACHE_PREWARM_COMPANY_IDS_INFO_KEY)
    if not isinstance(info_value, set):
        info_value = set()
        db.info[_TENANTS_FLEET_CACHE_PREWARM_COMPANY_IDS_INFO_KEY] = info_value
    info_value.update(scoped_ids)


def _queue_fleet_global_prewarm(db: Session) -> None:
    if not _TENANTS_FLEET_CACHE_PREWARM_GLOBAL_SCOPE_ENABLED:
        return
    db.info[_TENANTS_FLEET_CACHE_PREWARM_GLOBAL_INFO_KEY] = True


def _queue_fleet_incremental_prewarm_event(
    db: Session,
    *,
    reason: str,
    company_ids: set[UUID],
) -> None:
    scoped_ids = {
        company_id
        for company_id in company_ids
        if company_id is not None
    }
    info_value = db.info.get(_TENANTS_FLEET_CACHE_PREWARM_EVENTS_INFO_KEY)
    if not isinstance(info_value, list):
        info_value = []
        db.info[_TENANTS_FLEET_CACHE_PREWARM_EVENTS_INFO_KEY] = info_value
    normalized_event = {
        "reason": reason,
        "company_ids": [str(company_id) for company_id in sorted(scoped_ids, key=str)],
    }
    if normalized_event not in info_value:
        info_value.append(normalized_event)

    # Keep current scheduling contract while adding event stream metadata.
    _queue_fleet_summary_prewarm_company_ids(
        db,
        company_ids=scoped_ids,
    )
    _queue_fleet_global_prewarm(db)


def _extract_incremental_prewarm_targets(
    events: list[dict[str, Any]],
) -> tuple[set[UUID], bool]:
    scoped_company_ids: set[UUID] = set()
    global_prewarm_required = False
    for raw_event in events:
        if not isinstance(raw_event, dict):
            continue
        global_prewarm_required = True
        event_company_ids = raw_event.get("company_ids")
        if not isinstance(event_company_ids, list):
            continue
        for raw_company_id in event_company_ids:
            if isinstance(raw_company_id, UUID):
                scoped_company_ids.add(raw_company_id)
                continue
            if not isinstance(raw_company_id, str):
                continue
            try:
                scoped_company_ids.add(UUID(raw_company_id))
            except (TypeError, ValueError):
                continue
    return scoped_company_ids, global_prewarm_required


def _coalesce_incremental_prewarm_dispatch_batch(
    batch: list[dict[str, Any]],
) -> tuple[set[UUID], bool]:
    scoped_company_ids: set[UUID] = set()
    global_prewarm_required = False
    for raw_item in batch:
        if not isinstance(raw_item, dict):
            continue
        global_prewarm_required = global_prewarm_required or bool(raw_item.get("global_required"))
        raw_company_ids = raw_item.get("company_ids")
        if not isinstance(raw_company_ids, list):
            continue
        for raw_company_id in raw_company_ids:
            if isinstance(raw_company_id, UUID):
                scoped_company_ids.add(raw_company_id)
                continue
            if not isinstance(raw_company_id, str):
                continue
            try:
                scoped_company_ids.add(UUID(raw_company_id))
            except (TypeError, ValueError):
                continue
    return scoped_company_ids, global_prewarm_required


def _normalize_fleet_incremental_prewarm_company_ids(raw_company_ids: Any) -> set[UUID]:
    normalized: set[UUID] = set()
    if not isinstance(raw_company_ids, list):
        return normalized
    for raw_company_id in raw_company_ids:
        if isinstance(raw_company_id, UUID):
            normalized.add(raw_company_id)
            continue
        if not isinstance(raw_company_id, str):
            continue
        try:
            normalized.add(UUID(raw_company_id))
        except (TypeError, ValueError):
            continue
    return normalized


def _enqueue_fleet_incremental_prewarm_dispatch_inmemory(
    *,
    company_ids: set[UUID],
    global_prewarm_required: bool,
) -> None:
    normalized_company_ids = [str(company_id) for company_id in sorted(company_ids, key=str)]
    payload = {
        "company_ids": normalized_company_ids,
        "global_required": global_prewarm_required,
    }

    with _TENANTS_FLEET_PREWARM_DISPATCH_LOCK:
        if len(_TENANTS_FLEET_PREWARM_DISPATCH_QUEUE) >= _TENANTS_FLEET_PREWARM_DISPATCH_QUEUE_MAX:
            _TENANTS_FLEET_PREWARM_DISPATCH_QUEUE.clear()
            _TENANTS_FLEET_PREWARM_DISPATCH_QUEUE.append(
                {
                    "company_ids": normalized_company_ids,
                    "global_required": True,
                    "reason": "dispatch_queue_overflow",
                }
            )
        else:
            _TENANTS_FLEET_PREWARM_DISPATCH_QUEUE.append(payload)


def _drain_fleet_incremental_prewarm_dispatch_queue_inmemory_once() -> bool:
    with _TENANTS_FLEET_PREWARM_DISPATCH_LOCK:
        if not _TENANTS_FLEET_PREWARM_DISPATCH_QUEUE:
            return False
        batch: list[dict[str, Any]] = []
        while (
            _TENANTS_FLEET_PREWARM_DISPATCH_QUEUE
            and len(batch) < _TENANTS_FLEET_PREWARM_DISPATCH_BATCH_MAX
        ):
            batch.append(_TENANTS_FLEET_PREWARM_DISPATCH_QUEUE.popleft())

    scoped_company_ids, global_prewarm_required = _coalesce_incremental_prewarm_dispatch_batch(batch)
    if scoped_company_ids:
        _schedule_fleet_summary_prewarm_for_company_ids(company_ids=scoped_company_ids)
        _schedule_fleet_attention_prewarm_for_company_ids(company_ids=scoped_company_ids)
    if global_prewarm_required:
        _schedule_fleet_global_prewarm()
    return True


def _enqueue_fleet_incremental_prewarm_dispatch_durable(
    *,
    company_ids: set[UUID],
    global_prewarm_required: bool,
) -> bool:
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    normalized_company_ids = [str(company_id) for company_id in sorted(company_ids, key=str)]
    job_global_required = global_prewarm_required
    job_reason: Optional[str] = None
    try:
        pending_count = (
            db.query(func.count(TenantsFleetPrewarmJob.id))
            .filter(
                TenantsFleetPrewarmJob.status.in_(
                    [
                        _TENANTS_FLEET_PREWARM_JOB_STATUS_PENDING,
                        _TENANTS_FLEET_PREWARM_JOB_STATUS_PROCESSING,
                    ]
                )
            )
            .scalar()
            or 0
        )
        if pending_count >= _TENANTS_FLEET_PREWARM_DISPATCH_QUEUE_MAX:
            # Collapse pending backlog into a single global rebuild signal.
            db.query(TenantsFleetPrewarmJob).filter(
                TenantsFleetPrewarmJob.status == _TENANTS_FLEET_PREWARM_JOB_STATUS_PENDING
            ).update(
                {
                    TenantsFleetPrewarmJob.status: _TENANTS_FLEET_PREWARM_JOB_STATUS_DONE,
                    TenantsFleetPrewarmJob.completed_at: now,
                    TenantsFleetPrewarmJob.updated_at: now,
                    TenantsFleetPrewarmJob.last_error: "dispatch_queue_overflow",
                },
                synchronize_session=False,
            )
            job_global_required = True
            job_reason = "dispatch_queue_overflow"
        db.add(
            TenantsFleetPrewarmJob(
                company_ids=normalized_company_ids,
                global_required=job_global_required,
                reason=job_reason,
                status=_TENANTS_FLEET_PREWARM_JOB_STATUS_PENDING,
                updated_at=now,
            )
        )
        db.commit()
        return True
    except ProgrammingError as exc:
        db.rollback()
        if _is_tenants_fleet_prewarm_job_table_missing_error(exc):
            return False
        return False
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def _claim_fleet_incremental_prewarm_dispatch_batch() -> list[dict[str, Any]]:
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(seconds=_TENANTS_FLEET_PREWARM_DISPATCH_STUCK_SECONDS)
    try:
        try:
            db.query(TenantsFleetPrewarmJob).filter(
                TenantsFleetPrewarmJob.status == _TENANTS_FLEET_PREWARM_JOB_STATUS_PROCESSING,
                TenantsFleetPrewarmJob.locked_at.isnot(None),
                TenantsFleetPrewarmJob.locked_at < stale_before,
            ).update(
                {
                    TenantsFleetPrewarmJob.status: _TENANTS_FLEET_PREWARM_JOB_STATUS_PENDING,
                    TenantsFleetPrewarmJob.locked_at: None,
                    TenantsFleetPrewarmJob.updated_at: now,
                    TenantsFleetPrewarmJob.last_error: "processing_timeout_auto_heal",
                },
                synchronize_session=False,
            )
            db.commit()
        except Exception:
            db.rollback()

        rows = (
            db.query(TenantsFleetPrewarmJob)
            .filter(TenantsFleetPrewarmJob.status == _TENANTS_FLEET_PREWARM_JOB_STATUS_PENDING)
            .order_by(TenantsFleetPrewarmJob.created_at.asc(), TenantsFleetPrewarmJob.id.asc())
            .with_for_update(skip_locked=True)
            .limit(_TENANTS_FLEET_PREWARM_DISPATCH_BATCH_MAX)
            .all()
        )
        if not rows:
            db.commit()
            return []

        items: list[dict[str, Any]] = []
        for row in rows:
            row.status = _TENANTS_FLEET_PREWARM_JOB_STATUS_PROCESSING
            row.locked_at = now
            row.updated_at = now
            row.attempt_count = max(int(row.attempt_count or 0), 0) + 1
            items.append(
                {
                    "job_id": str(row.id),
                    "company_ids": [str(company_id) for company_id in _normalize_fleet_incremental_prewarm_company_ids(row.company_ids)],
                    "global_required": bool(row.global_required),
                }
            )
        db.commit()
        return items
    except ProgrammingError as exc:
        db.rollback()
        if _is_tenants_fleet_prewarm_job_table_missing_error(exc):
            return []
        return []
    except Exception:
        db.rollback()
        return []
    finally:
        db.close()


def _mark_fleet_incremental_prewarm_dispatch_jobs_completed(job_ids: set[UUID]) -> None:
    if not job_ids:
        return
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    try:
        db.query(TenantsFleetPrewarmJob).filter(TenantsFleetPrewarmJob.id.in_(list(job_ids))).update(
            {
                TenantsFleetPrewarmJob.status: _TENANTS_FLEET_PREWARM_JOB_STATUS_DONE,
                TenantsFleetPrewarmJob.locked_at: None,
                TenantsFleetPrewarmJob.completed_at: now,
                TenantsFleetPrewarmJob.updated_at: now,
                TenantsFleetPrewarmJob.last_error: None,
            },
            synchronize_session=False,
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _mark_fleet_incremental_prewarm_dispatch_jobs_retry(job_ids: set[UUID], *, error_message: str) -> None:
    if not job_ids:
        return
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    truncated_error = (error_message or "").strip()[:500]
    try:
        db.query(TenantsFleetPrewarmJob).filter(TenantsFleetPrewarmJob.id.in_(list(job_ids))).update(
            {
                TenantsFleetPrewarmJob.status: _TENANTS_FLEET_PREWARM_JOB_STATUS_PENDING,
                TenantsFleetPrewarmJob.locked_at: None,
                TenantsFleetPrewarmJob.updated_at: now,
                TenantsFleetPrewarmJob.last_error: truncated_error or "dispatch_retry",
            },
            synchronize_session=False,
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _drain_fleet_incremental_prewarm_dispatch_queue_once() -> bool:
    durable_batch = _claim_fleet_incremental_prewarm_dispatch_batch()
    if durable_batch:
        scoped_company_ids, global_prewarm_required = _coalesce_incremental_prewarm_dispatch_batch(durable_batch)
        job_ids: set[UUID] = set()
        for raw_item in durable_batch:
            raw_job_id = raw_item.get("job_id")
            if not isinstance(raw_job_id, str):
                continue
            try:
                job_ids.add(UUID(raw_job_id))
            except (TypeError, ValueError):
                continue
        try:
            if scoped_company_ids:
                _schedule_fleet_summary_prewarm_for_company_ids(company_ids=scoped_company_ids)
                _schedule_fleet_attention_prewarm_for_company_ids(company_ids=scoped_company_ids)
            if global_prewarm_required:
                _schedule_fleet_global_prewarm()
            _mark_fleet_incremental_prewarm_dispatch_jobs_completed(job_ids)
        except Exception as exc:
            _mark_fleet_incremental_prewarm_dispatch_jobs_retry(
                job_ids,
                error_message=str(exc),
            )
        return True

    return _drain_fleet_incremental_prewarm_dispatch_queue_inmemory_once()


def _fleet_incremental_prewarm_dispatch_worker() -> None:
    global _TENANTS_FLEET_PREWARM_DISPATCH_WORKER

    try:
        while True:
            drained = _drain_fleet_incremental_prewarm_dispatch_queue_once()
            _maybe_run_fleet_projection_maintenance()
            if not drained:
                break
    finally:
        should_restart = False
        with _TENANTS_FLEET_PREWARM_DISPATCH_LOCK:
            _TENANTS_FLEET_PREWARM_DISPATCH_WORKER = None
            should_restart = bool(_TENANTS_FLEET_PREWARM_DISPATCH_QUEUE)
        if should_restart:
            _ensure_fleet_incremental_prewarm_dispatch_worker()


def _ensure_fleet_incremental_prewarm_dispatch_worker() -> None:
    global _TENANTS_FLEET_PREWARM_DISPATCH_WORKER

    worker: Optional[Thread]
    with _TENANTS_FLEET_PREWARM_DISPATCH_LOCK:
        current_worker = _TENANTS_FLEET_PREWARM_DISPATCH_WORKER
        if current_worker is not None and current_worker.is_alive():
            return
        worker = Thread(
            target=_fleet_incremental_prewarm_dispatch_worker,
            daemon=True,
            name="tenants-fleet-prewarm-dispatch",
        )
        _TENANTS_FLEET_PREWARM_DISPATCH_WORKER = worker

    try:
        worker.start()
    except Exception:
        with _TENANTS_FLEET_PREWARM_DISPATCH_LOCK:
            if _TENANTS_FLEET_PREWARM_DISPATCH_WORKER is worker:
                _TENANTS_FLEET_PREWARM_DISPATCH_WORKER = None


def _enqueue_fleet_incremental_prewarm_dispatch(
    *,
    company_ids: set[UUID],
    global_prewarm_required: bool,
) -> None:
    if not company_ids and not global_prewarm_required:
        return

    persisted = _enqueue_fleet_incremental_prewarm_dispatch_durable(
        company_ids=company_ids,
        global_prewarm_required=global_prewarm_required,
    )
    if not persisted:
        _enqueue_fleet_incremental_prewarm_dispatch_inmemory(
            company_ids=company_ids,
            global_prewarm_required=global_prewarm_required,
        )
    _ensure_fleet_incremental_prewarm_dispatch_worker()


def _load_global_active_client_ids(
    *,
    max_clients: int,
) -> tuple[set[UUID], bool]:
    db = SessionLocal()
    try:
        rows = (
            db.query(Client.id)
            .filter(Client.status == _CLIENT_STATUS_ACTIVE)
            .order_by(Client.created_at.desc(), Client.id.desc())
            .limit(max_clients + 1)
            .all()
        )
        overflow = len(rows) > max_clients
        selected_rows = rows[:max_clients]
        return {
            row[0]
            for row in selected_rows
            if row and row[0] is not None
        }, overflow
    except Exception:
        db.rollback()
        return set(), False
    finally:
        db.close()


def _reserve_fleet_global_prewarm_slot(now_mono: float) -> bool:
    global _TENANTS_FLEET_CACHE_GLOBAL_PREWARM_NEXT_ALLOWED_AT

    with _TENANTS_FLEET_CACHE_GLOBAL_PREWARM_LOCK:
        if now_mono < _TENANTS_FLEET_CACHE_GLOBAL_PREWARM_NEXT_ALLOWED_AT:
            return False
        _TENANTS_FLEET_CACHE_GLOBAL_PREWARM_NEXT_ALLOWED_AT = (
            now_mono + _TENANTS_FLEET_CACHE_PREWARM_GLOBAL_MIN_INTERVAL_SECONDS
        )
    return True


def _load_active_clients_by_company(
    *,
    company_ids: set[UUID],
) -> dict[UUID, set[UUID]]:
    db = SessionLocal()
    try:
        rows = (
            db.query(Client.id, Client.company_id)
            .filter(
                Client.status == _CLIENT_STATUS_ACTIVE,
                Client.company_id.in_(list(company_ids)),
            )
            .all()
        )
        result: dict[UUID, set[UUID]] = {}
        for client_id, company_id in rows:
            if not company_id:
                continue
            result.setdefault(company_id, set()).add(client_id)
        return result
    except Exception:
        db.rollback()
        return {}
    finally:
        db.close()


def _load_company_ids_for_client_ids(
    *,
    client_ids: set[UUID],
    max_company_ids: int,
) -> set[UUID]:
    if not client_ids:
        return set()
    if max_company_ids <= 0:
        return set()

    db = SessionLocal()
    try:
        rows = (
            db.query(Client.company_id)
            .filter(
                Client.status == _CLIENT_STATUS_ACTIVE,
                Client.id.in_(list(client_ids)),
                Client.company_id.isnot(None),
            )
            .all()
        )
        company_ids: set[UUID] = set()
        for row in rows:
            raw_company_id: Any = None
            if isinstance(row, tuple):
                raw_company_id = row[0] if row else None
            elif hasattr(row, "company_id"):
                raw_company_id = getattr(row, "company_id")
            else:
                try:
                    raw_company_id = row[0]  # type: ignore[index]
                except Exception:
                    raw_company_id = None
            if isinstance(raw_company_id, UUID):
                company_ids.add(raw_company_id)
            elif raw_company_id:
                try:
                    company_ids.add(UUID(str(raw_company_id)))
                except (TypeError, ValueError):
                    continue
            if len(company_ids) >= max_company_ids:
                break
        return company_ids
    except Exception:
        db.rollback()
        return set()
    finally:
        db.close()


def _schedule_fleet_summary_prewarm_for_company_ids(
    *,
    company_ids: set[UUID],
) -> None:
    if not _TENANTS_FLEET_CACHE_PREWARM_ON_INVALIDATION_ENABLED:
        return
    if not company_ids:
        return
    capped_company_ids = set(sorted(company_ids, key=str)[:_TENANTS_FLEET_CACHE_PREWARM_MAX_COMPANY_SCOPES])
    if not capped_company_ids:
        return
    active_clients_by_company = _load_active_clients_by_company(company_ids=capped_company_ids)
    if not active_clients_by_company:
        return
    for company_id, active_client_ids in active_clients_by_company.items():
        if not active_client_ids:
            continue
        if len(active_client_ids) > _TENANTS_FLEET_CACHE_ASYNC_MAX_SCOPE_CLIENTS:
            continue
        scope_key = _build_clients_summary_cache_scope_key(
            accessible_clients_hash=_hash_uuid_values(active_client_ids),
            company_uuid=company_id,
            lifecycle_mode="active",
            query_value=None,
            fleet_lifecycle_filter=None,
            payment_status_filter=None,
            service_state_filter=None,
        )
        if not _try_claim_fleet_cache_refresh(_TENANTS_FLEET_CACHE_SUMMARY_TYPE, scope_key):
            continue
        task = {
            "scope_key": scope_key,
            "accessible_client_ids": [str(client_id) for client_id in sorted(active_client_ids, key=str)],
            "lifecycle_mode": "active",
            "company_id": str(company_id),
            "query_value": None,
            "fleet_lifecycle_filter": None,
            "payment_status_filter": None,
            "service_state_filter": None,
            "batch_size": 100,
        }
        _start_fleet_summary_refresh_task(
            scope_key=scope_key,
            task=task,
            thread_name="tenants-fleet-summary-prewarm",
        )


def _schedule_fleet_attention_prewarm_for_company_ids(
    *,
    company_ids: set[UUID],
) -> None:
    if not _TENANTS_FLEET_CACHE_PREWARM_ON_INVALIDATION_ENABLED:
        return
    if not company_ids:
        return
    capped_company_ids = set(sorted(company_ids, key=str)[:_TENANTS_FLEET_CACHE_PREWARM_MAX_COMPANY_SCOPES])
    if not capped_company_ids:
        return
    active_clients_by_company = _load_active_clients_by_company(company_ids=capped_company_ids)
    if not active_clients_by_company:
        return
    for active_client_ids in active_clients_by_company.values():
        if not active_client_ids:
            continue
        if len(active_client_ids) > _TENANTS_FLEET_CACHE_ASYNC_MAX_SCOPE_CLIENTS:
            continue
        scope_key = _build_fleet_attention_cache_scope_key(
            active_client_ids=active_client_ids,
            stale_after_minutes=_INTEGRATION_DEFAULT_STALE_MINUTES,
            include_low_mode=False,
            limit=_TENANTS_FLEET_CACHE_PREWARM_COMPANY_ATTENTION_LIMIT,
        )
        if not _try_claim_fleet_cache_refresh(_TENANTS_FLEET_CACHE_ATTENTION_TYPE, scope_key):
            continue
        task = {
            "scope_key": scope_key,
            "active_client_ids": [str(client_id) for client_id in sorted(active_client_ids, key=str)],
            "stale_after_minutes": _INTEGRATION_DEFAULT_STALE_MINUTES,
            "include_low_mode": False,
            "limit": _TENANTS_FLEET_CACHE_PREWARM_COMPANY_ATTENTION_LIMIT,
        }
        _start_fleet_attention_refresh_task(
            scope_key=scope_key,
            task=task,
            thread_name="tenants-fleet-attention-prewarm-company",
        )


def _schedule_fleet_global_prewarm() -> None:
    if not _TENANTS_FLEET_CACHE_PREWARM_GLOBAL_SCOPE_ENABLED:
        return
    if not _reserve_fleet_global_prewarm_slot(monotonic()):
        return

    active_client_ids, overflow = _load_global_active_client_ids(
        max_clients=_TENANTS_FLEET_CACHE_PREWARM_GLOBAL_MAX_ACTIVE_CLIENTS,
    )
    if not active_client_ids:
        return
    if overflow or len(active_client_ids) > _TENANTS_FLEET_CACHE_ASYNC_MAX_SCOPE_CLIENTS:
        _maybe_enqueue_projection_fallback_prewarm_for_client_ids(
            client_ids=active_client_ids,
        )
        return

    active_client_ids_sorted = sorted(active_client_ids, key=str)

    summary_scope_key = _build_clients_summary_cache_scope_key(
        accessible_clients_hash=_hash_uuid_values(active_client_ids),
        company_uuid=None,
        lifecycle_mode="active",
        query_value=None,
        fleet_lifecycle_filter=None,
        payment_status_filter=None,
        service_state_filter=None,
    )
    if _try_claim_fleet_cache_refresh(_TENANTS_FLEET_CACHE_SUMMARY_TYPE, summary_scope_key):
        summary_task = {
            "scope_key": summary_scope_key,
            "accessible_client_ids": [str(client_id) for client_id in active_client_ids_sorted],
            "lifecycle_mode": "active",
            "company_id": None,
            "query_value": None,
            "fleet_lifecycle_filter": None,
            "payment_status_filter": None,
            "service_state_filter": None,
            "batch_size": 100,
        }
        _start_fleet_summary_refresh_task(
            scope_key=summary_scope_key,
            task=summary_task,
            thread_name="tenants-fleet-summary-prewarm-global",
        )

    attention_scope_key = _build_fleet_attention_cache_scope_key(
        active_client_ids=active_client_ids,
        stale_after_minutes=_INTEGRATION_DEFAULT_STALE_MINUTES,
        include_low_mode=False,
        limit=_TENANTS_FLEET_CACHE_PREWARM_GLOBAL_ATTENTION_LIMIT,
    )
    if _try_claim_fleet_cache_refresh(_TENANTS_FLEET_CACHE_ATTENTION_TYPE, attention_scope_key):
        attention_task = {
            "scope_key": attention_scope_key,
            "active_client_ids": [str(client_id) for client_id in active_client_ids_sorted],
            "stale_after_minutes": _INTEGRATION_DEFAULT_STALE_MINUTES,
            "include_low_mode": False,
            "limit": _TENANTS_FLEET_CACHE_PREWARM_GLOBAL_ATTENTION_LIMIT,
        }
        _start_fleet_attention_refresh_task(
            scope_key=attention_scope_key,
            task=attention_task,
            thread_name="tenants-fleet-attention-prewarm-global",
        )


@event.listens_for(Session, "after_commit")
def _on_console_session_after_commit(session: Session) -> None:
    raw_events = session.info.pop(_TENANTS_FLEET_CACHE_PREWARM_EVENTS_INFO_KEY, None)
    if isinstance(raw_events, list):
        scoped_company_ids, global_prewarm_required = _extract_incremental_prewarm_targets(raw_events)

        # Clear legacy keys if event stream was present.
        session.info.pop(_TENANTS_FLEET_CACHE_PREWARM_COMPANY_IDS_INFO_KEY, None)
        session.info.pop(_TENANTS_FLEET_CACHE_PREWARM_GLOBAL_INFO_KEY, None)

        _enqueue_fleet_incremental_prewarm_dispatch(
            company_ids=scoped_company_ids,
            global_prewarm_required=global_prewarm_required,
        )
        return

    raw_company_ids = session.info.pop(_TENANTS_FLEET_CACHE_PREWARM_COMPANY_IDS_INFO_KEY, None)
    global_prewarm_required = bool(
        session.info.pop(_TENANTS_FLEET_CACHE_PREWARM_GLOBAL_INFO_KEY, False)
    )
    if not isinstance(raw_company_ids, set):
        raw_company_ids = set()
    scoped_company_ids = {company_id for company_id in raw_company_ids if isinstance(company_id, UUID)}
    _enqueue_fleet_incremental_prewarm_dispatch(
        company_ids=scoped_company_ids,
        global_prewarm_required=global_prewarm_required,
    )


@event.listens_for(Session, "after_rollback")
def _on_console_session_after_rollback(session: Session) -> None:
    session.info.pop(_TENANTS_FLEET_CACHE_PREWARM_EVENTS_INFO_KEY, None)
    session.info.pop(_TENANTS_FLEET_CACHE_PREWARM_COMPANY_IDS_INFO_KEY, None)
    session.info.pop(_TENANTS_FLEET_CACHE_PREWARM_GLOBAL_INFO_KEY, None)


def _build_fleet_attention_response_for_clients(
    db: Session,
    *,
    active_clients: list[Client],
    companies_by_id: dict[UUID, Company],
    stale_after_minutes: int,
    include_low_mode: bool,
    limit: int,
    now: datetime,
) -> ConsoleFleetAttentionResponse:
    fleet_details_map = _load_or_build_fleet_client_details_map(
        db,
        clients=active_clients,
        companies_by_id=companies_by_id,
        persist_missing=_TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_ENABLED,
        persist_missing_max_clients=_TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_MAX_CLIENTS,
    )

    client_ids = [client.id for client in active_clients]
    branches = db.query(Branch).filter(Branch.client_id.in_(client_ids)).all()
    branches_by_client: dict[UUID, list[Branch]] = {client.id: [] for client in active_clients}
    for branch in branches:
        branches_by_client.setdefault(branch.client_id, []).append(branch)

    token_rows = (
        db.query(
            ClientSettings.client_id,
            ClientSettings.telegram_bot_token,
        )
        .filter(ClientSettings.client_id.in_(client_ids))
        .all()
    )
    telegram_token_map: dict[UUID, bool] = {}
    for client_id, token in token_rows:
        telegram_token_map[client_id] = bool(_normalize_optional_text(token))

    inbound_observations = _load_latest_branch_inbound_observations_for_clients(
        db,
        client_ids=client_ids,
    )

    outbox_failed_map = _query_outbox_failed_24h_map(db, client_ids=client_ids, now=now)
    pending_handovers_map = _query_pending_handovers_map(db, client_ids=client_ids)

    summary = ConsoleFleetAttentionSummary(
        active_clients_total=len(active_clients),
        clients_with_attention=0,
        high_risk_clients=0,
        medium_risk_clients=0,
        low_risk_clients=0,
        stale_branches_total=0,
        integration_error_branches_total=0,
        integration_warn_branches_total=0,
        outbox_failed_24h_total=0,
        pending_handovers_total=0,
    )

    items: list[ConsoleFleetAttentionItem] = []
    for client in active_clients:
        details = fleet_details_map.get(client.id)
        if not details:
            continue

        reference_branch_ids = set(details.reference_branch_ids or ())
        stale_branches = 0
        integration_error_branches = 0
        integration_warn_branches = 0

        for branch in branches_by_client.get(client.id, []):
            if not branch.is_active:
                continue
            if reference_branch_ids and branch.id not in reference_branch_ids:
                continue
            observed = inbound_observations.get(branch.id)
            last_inbound_at: Optional[datetime] = None
            last_inbound_instance_id: Optional[str] = None
            if observed:
                last_inbound_at, last_inbound_instance_id = observed

            status = _build_branch_integration_status(
                client_id=client.id,
                client_slug=client.name,
                branch=branch,
                has_telegram_bot_token=telegram_token_map.get(client.id, False),
                stale_after_minutes=stale_after_minutes,
                last_inbound_at=last_inbound_at,
                last_inbound_instance_id=last_inbound_instance_id,
                now=now,
            )
            if status.whatsapp_status == "no_recent_inbound":
                stale_branches += 1
            if status.status == "error":
                integration_error_branches += 1
            elif status.status == "warn":
                integration_warn_branches += 1

        outbox_failed_24h = outbox_failed_map.get(client.id, 0)
        pending_handovers = pending_handovers_map.get(client.id, 0)
        score, level, reasons, suggested_actions = _resolve_fleet_attention_profile(
            service_state=details.service_state,
            stale_branches=stale_branches,
            integration_error_branches=integration_error_branches,
            integration_warn_branches=integration_warn_branches,
            outbox_failed_24h=outbox_failed_24h,
            pending_handovers=pending_handovers,
        )

        if score > 0:
            summary.clients_with_attention += 1
            if level == "high":
                summary.high_risk_clients += 1
            elif level == "medium":
                summary.medium_risk_clients += 1
            else:
                summary.low_risk_clients += 1
        summary.stale_branches_total += stale_branches
        summary.integration_error_branches_total += integration_error_branches
        summary.integration_warn_branches_total += integration_warn_branches
        summary.outbox_failed_24h_total += outbox_failed_24h
        summary.pending_handovers_total += pending_handovers

        if not include_low_mode and level == "low":
            continue

        company = companies_by_id.get(client.company_id) if client.company_id else None
        items.append(
            ConsoleFleetAttentionItem(
                client_id=client.id,
                client_slug=client.name,
                client_name=client.name,
                company_id=client.company_id,
                company_name=company.name if company else None,
                lifecycle_state=details.lifecycle_state,
                payment_status=details.payment_status,
                commercial_state=details.commercial_state,
                service_state=details.service_state,
                owner_name=details.owner_name,
                next_action=details.next_action,
                total_branches=details.total_branches,
                active_branches=details.active_branches,
                degraded_branches=details.degraded_branches,
                go_live_ready_branches=details.go_live_ready_branches,
                reference_branch_ids=list(details.reference_branch_ids),
                reference_branch_reason=details.reference_branch_reason,
                stale_branches=stale_branches,
                integration_error_branches=integration_error_branches,
                integration_warn_branches=integration_warn_branches,
                outbox_failed_24h=outbox_failed_24h,
                pending_handovers=pending_handovers,
                attention_score=score,
                attention_level=level,
                reasons=reasons,
                suggested_actions=suggested_actions,
            )
        )

    items.sort(
        key=lambda item: (
            item.attention_score,
            item.integration_error_branches,
            item.outbox_failed_24h,
            item.pending_handovers,
        ),
        reverse=True,
    )
    return ConsoleFleetAttentionResponse(
        generated_at=now.isoformat(),
        stale_after_minutes=stale_after_minutes,
        summary=summary,
        items=items[:limit],
    )


def _refresh_fleet_attention_cache_worker(task: dict[str, Any]) -> None:
    scope_key = str(task.get("scope_key") or "").strip()
    if not scope_key:
        return
    db = SessionLocal()
    try:
        raw_client_ids = task.get("active_client_ids") or []
        active_client_ids = {
            UUID(str(raw_id))
            for raw_id in raw_client_ids
            if raw_id
        }
        if not active_client_ids:
            return
        stale_after_minutes_raw = task.get("stale_after_minutes")
        stale_after_minutes = (
            int(stale_after_minutes_raw)
            if isinstance(stale_after_minutes_raw, int)
            else _INTEGRATION_DEFAULT_STALE_MINUTES
        )
        include_low_mode = bool(task.get("include_low_mode"))
        limit_raw = task.get("limit")
        limit = int(limit_raw) if isinstance(limit_raw, int) and limit_raw > 0 else 20
        now = datetime.now(timezone.utc)

        active_clients = (
            db.query(Client)
            .filter(
                Client.id.in_(list(active_client_ids)),
                Client.status == _CLIENT_STATUS_ACTIVE,
            )
            .all()
        )
        if not active_clients:
            response = ConsoleFleetAttentionResponse(
                generated_at=now.isoformat(),
                stale_after_minutes=stale_after_minutes,
                summary=ConsoleFleetAttentionSummary(
                    active_clients_total=0,
                    clients_with_attention=0,
                    high_risk_clients=0,
                    medium_risk_clients=0,
                    low_risk_clients=0,
                    stale_branches_total=0,
                    integration_error_branches_total=0,
                    integration_warn_branches_total=0,
                    outbox_failed_24h_total=0,
                    pending_handovers_total=0,
                ),
                items=[],
            )
        else:
            company_ids = {client.company_id for client in active_clients if client.company_id}
            companies_by_id = {
                company.id: company
                for company in db.query(Company).filter(Company.id.in_(list(company_ids))).all()
            } if company_ids else {}
            response = _build_fleet_attention_response_for_clients(
                db,
                active_clients=active_clients,
                companies_by_id=companies_by_id,
                stale_after_minutes=stale_after_minutes,
                include_low_mode=include_low_mode,
                limit=limit,
                now=now,
            )
        _store_cached_fleet_attention(
            db,
            scope_key=scope_key,
            now=now,
            response=response,
        )
    except Exception:
        db.rollback()
    finally:
        db.close()
        _maybe_run_fleet_projection_maintenance()
        _release_fleet_cache_refresh(_TENANTS_FLEET_CACHE_ATTENTION_TYPE, scope_key)


def _schedule_fleet_attention_async_refresh(
    db: Session,
    *,
    scope_key: str,
    active_client_ids: set[UUID],
    stale_after_minutes: int,
    include_low_mode: bool,
    limit: int,
    now: datetime,
) -> None:
    if not _TENANTS_FLEET_CACHE_ASYNC_REFRESH_ENABLED:
        return
    if not active_client_ids:
        return
    if len(active_client_ids) > _TENANTS_FLEET_CACHE_ASYNC_MAX_SCOPE_CLIENTS:
        return
    if not _is_fleet_cache_async_refresh_due(
        db,
        cache_type=_TENANTS_FLEET_CACHE_ATTENTION_TYPE,
        scope_key=scope_key,
        now=now,
    ):
        return
    if not _try_claim_fleet_cache_refresh(_TENANTS_FLEET_CACHE_ATTENTION_TYPE, scope_key):
        return
    task = {
        "scope_key": scope_key,
        "active_client_ids": [str(client_id) for client_id in sorted(active_client_ids, key=str)],
        "stale_after_minutes": stale_after_minutes,
        "include_low_mode": include_low_mode,
        "limit": limit,
    }
    _start_fleet_attention_refresh_task(
        scope_key=scope_key,
        task=task,
        thread_name="tenants-fleet-attention-refresh",
    )


def _start_fleet_attention_refresh_task(
    *,
    scope_key: str,
    task: dict[str, Any],
    thread_name: str,
) -> None:
    try:
        Thread(
            target=_refresh_fleet_attention_cache_worker,
            kwargs={"task": task},
            daemon=True,
            name=thread_name,
        ).start()
    except Exception:
        _release_fleet_cache_refresh(_TENANTS_FLEET_CACHE_ATTENTION_TYPE, scope_key)


def _invalidate_tenants_fleet_cache_scope(
    db: Session,
    *,
    reason: str,
    company_ids: Optional[set[UUID]] = None,
) -> None:
    # Keep cache invalidation best-effort and isolated from tenant mutations.
    # If cache storage is unavailable, writes must still succeed.
    _ = reason
    scoped_company_ids = {
        company_id
        for company_id in (company_ids or set())
        if company_id is not None
    }
    try:
        with db.begin_nested():
            statement = delete(TenantsFleetCache).where(
                TenantsFleetCache.cache_type.in_(
                    [
                        _TENANTS_FLEET_CACHE_SUMMARY_TYPE,
                        _TENANTS_FLEET_CACHE_ATTENTION_TYPE,
                    ]
                )
            )
            if scoped_company_ids:
                statement = statement.where(
                    or_(
                        TenantsFleetCache.scope_company_id.is_(None),
                        TenantsFleetCache.scope_company_id.in_(list(scoped_company_ids)),
                    )
                )
            db.execute(statement)
    except ProgrammingError as exc:
        if _is_tenants_fleet_cache_table_missing_error(exc):
            return
        return
    except Exception:
        return
    _queue_fleet_incremental_prewarm_event(
        db,
        reason=reason,
        company_ids=scoped_company_ids,
    )


def _normalize_client_lifecycle_reason(reason: str) -> str:
    value = (reason or "").strip()
    if not value:
        raise ConsoleAPIError(400, "INVALID_PARAM", "reason required")
    if len(value) > _CLIENT_LIFECYCLE_REASON_MAX_LEN:
        raise ConsoleAPIError(400, "INVALID_PARAM", "reason too long")
    return value


def _normalize_access_reason(
    reason: Optional[str],
    *,
    required: bool = False,
) -> Optional[str]:
    value = (reason or "").strip()
    if required and not value:
        raise ConsoleAPIError(400, "INVALID_PARAM", "reason required")
    if value and len(value) > _ACCESS_REASON_MAX_LEN:
        raise ConsoleAPIError(400, "INVALID_PARAM", "reason too long")
    return value or None


def _normalize_branch_go_live_state(value: Optional[str]) -> str:
    normalized = (value or "").strip().lower()
    if normalized in _BRANCH_GO_LIVE_STATES:
        return normalized
    return _BRANCH_GO_LIVE_DEFAULT_STATE


def _normalize_go_live_waiver_ttl_hours(value: int) -> int:
    if value < _GO_LIVE_WAIVER_MIN_HOURS or value > _GO_LIVE_WAIVER_MAX_HOURS:
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            f"ttl_hours must be between {_GO_LIVE_WAIVER_MIN_HOURS} and {_GO_LIVE_WAIVER_MAX_HOURS}",
        )
    return value


def _coerce_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _is_branch_go_live_waiver_active(
    branch: Branch,
    *,
    now: Optional[datetime] = None,
) -> bool:
    waiver_until = _coerce_utc(getattr(branch, "go_live_waiver_until", None))
    if waiver_until is None:
        return False
    current = now or datetime.now(timezone.utc)
    return waiver_until > current


def _is_branch_go_live_allowed(
    branch: Branch,
    *,
    now: Optional[datetime] = None,
) -> bool:
    go_live_state = _normalize_branch_go_live_state(getattr(branch, "go_live_state", None))
    if go_live_state == "approved":
        return True
    return _is_branch_go_live_waiver_active(branch, now=now)


def _require_branch_go_live_gate(branch: Branch, *, operation: str) -> None:
    now = datetime.now(timezone.utc)
    go_live_state = _normalize_branch_go_live_state(getattr(branch, "go_live_state", None))
    waiver_active = _is_branch_go_live_waiver_active(branch, now=now)
    if go_live_state == "approved" or waiver_active:
        return
    waiver_until = _coerce_utc(getattr(branch, "go_live_waiver_until", None))
    raise ConsoleAPIError(
        409,
        "GO_LIVE_GATE_REQUIRED",
        "Go-live approval required before branch activation",
        {
            "operation": operation,
            "go_live_state": go_live_state,
            "go_live_reason": getattr(branch, "go_live_reason", None),
            "go_live_waiver_active": waiver_active,
            "go_live_waiver_until": waiver_until.isoformat() if waiver_until else None,
        },
    )


def _require_branch_scorecard_ready(
    db: Session,
    branch: Branch,
    *,
    operation: str,
) -> None:
    scorecard = build_onboarding_scorecard(db, branch)
    hard_gate_enforced = _is_readiness_hard_gate_enforced_for_branch(branch)
    readiness_kernel = getattr(scorecard, "readiness_kernel", None)
    hard_gate_blockers: list[str] = []
    if readiness_kernel is not None:
        hard_gate_blockers = _resolve_readiness_hard_gate_blockers(readiness_kernel)
    if hard_gate_enforced and readiness_kernel is None:
        readiness_kernel = build_onboarding_readiness_kernel(
            db,
            branch,
            scorecard=scorecard,
        )
        hard_gate_blockers = _resolve_readiness_hard_gate_blockers(readiness_kernel)
    readiness_details = None
    if readiness_kernel is not None:
        hard_gate_status = "fail" if hard_gate_blockers else "pass"
        readiness_details = {
            "status": readiness_kernel.status,
            "blocker_codes": readiness_kernel.blocker_codes,
            "next_action_codes": readiness_kernel.next_action_codes,
            "shadow_hard_gate": {
                "enforced": hard_gate_enforced,
                "status": hard_gate_status,
                "blocker_codes": hard_gate_blockers,
            },
        }
    if scorecard.ready and not hard_gate_enforced:
        return
    if scorecard.ready and hard_gate_enforced and not hard_gate_blockers:
        return
    failed_checks = [
        check.id.value
        for check in scorecard.checks
        if check.required and not check.passed
    ]
    message = "Onboarding scorecard failed"
    missing = scorecard.missing
    scorecard_status = "fail"
    if scorecard.ready and hard_gate_enforced and hard_gate_blockers:
        message = "Onboarding readiness hard gate failed"
        missing = hard_gate_blockers
        scorecard_status = "pass"
    error_details = {
        "operation": operation,
        "required_step": OnboardingStep.GO_NO_GO.value,
        "missing": missing,
        "scorecard_status": scorecard_status,
        "failed_checks": failed_checks,
    }
    if readiness_details is not None:
        error_details["readiness_kernel"] = readiness_details
    raise ConsoleAPIError(
        409,
        "GO_LIVE_GATE_REQUIRED",
        message,
        error_details,
    )


def _accessible_client_ids(context: ConsoleAuthContext) -> set[UUID]:
    accessible_clients = getattr(context, "accessible_clients", None) or []
    client_ids = {client.id for client in accessible_clients if getattr(client, "id", None)}
    context_client = getattr(context, "client", None)
    if context_client and getattr(context_client, "id", None):
        client_ids.add(context_client.id)
    return client_ids


def _accessible_company_ids(context: ConsoleAuthContext) -> set[UUID]:
    accessible_clients = getattr(context, "accessible_clients", None) or []
    return {
        client.company_id
        for client in accessible_clients
        if getattr(client, "company_id", None)
    }


def _resolve_company_id_for_client_in_context(
    context: ConsoleAuthContext,
    client_id: Optional[UUID],
) -> Optional[UUID]:
    if client_id is None:
        return None
    accessible_clients = getattr(context, "accessible_clients", None) or []
    for client in accessible_clients:
        if getattr(client, "id", None) == client_id:
            return getattr(client, "company_id", None)
    context_client = getattr(context, "client", None)
    if context_client and getattr(context_client, "id", None) == client_id:
        return getattr(context_client, "company_id", None)
    return None


def _require_client_access(
    context: ConsoleAuthContext,
    client_id: UUID,
    *,
    message: str = "Client belongs to another tenant",
) -> None:
    if client_id not in _accessible_client_ids(context):
        raise ConsoleAPIError(403, "ACCESS_DENIED", message)


def _require_company_access(
    context: ConsoleAuthContext,
    company_id: UUID,
    *,
    message: str = "Company belongs to another tenant",
) -> None:
    if company_id not in _accessible_company_ids(context):
        raise ConsoleAPIError(403, "ACCESS_DENIED", message)


_MARKETING_ALLOWED_ROLES = {"platform_admin", "owner", "admin"}
_MARKETING_SAMPLE_LIMIT_DEFAULT = 5
_MARKETING_SAMPLE_LIMIT_MAX = 20
_MARKETING_EXECUTE_MAX_LIMIT = 500
_MARKETING_RETRY_LIMIT_DEFAULT = 100
_MARKETING_RETRY_LIMIT_MAX = 500
_MARKETING_AUDIENCE_LIMIT_DEFAULT = 100
_MARKETING_AUDIENCE_LIMIT_MAX = 500
_MARKETING_EDITABLE_STATUSES = {
    MARKETING_STATUS_DRAFT,
    MARKETING_STATUS_IN_REVIEW,
}


def _require_marketing_access(context: ConsoleAuthContext, *, action: str) -> None:
    if context.role not in _MARKETING_ALLOWED_ROLES:
        raise ConsoleAPIError(
            403,
            "ACCESS_DENIED",
            f"Only owner/admin/platform admin can {action} marketing campaigns",
        )


def _serialize_marketing_campaign(campaign: MarketingCampaign) -> ConsoleMarketingCampaign:
    segment_code = campaign.segment_code if campaign.segment_code in MARKETING_SEGMENT_CODES else "reactivation_30_120"
    status_value = resolve_marketing_campaign_status(campaign)
    try:
        segment_params = resolve_campaign_segment_params(
            campaign,
            segment_code=segment_code,
            strict=False,
        )
    except Exception:
        segment_params = normalize_marketing_segment_params(segment_code, None, strict=False)
    audience_filter = campaign.audience_filter if isinstance(campaign.audience_filter, dict) else {}
    segment_summary_raw = audience_filter.get("segment_summary")
    segment_summary = (
        segment_summary_raw.strip()
        if isinstance(segment_summary_raw, str) and segment_summary_raw.strip()
        else build_marketing_segment_summary(segment_code, segment_params)
    )
    return ConsoleMarketingCampaign(
        id=campaign.id,
        client_id=campaign.client_id,
        branch_id=campaign.branch_id,
        name=campaign.name,
        message_text=campaign.message_text,
        status=status_value,
        status_v2=status_value,
        segment_code=segment_code,
        segment_params=segment_params,
        segment_summary=segment_summary,
        audience_mode=campaign.audience_mode,
        preview_total=int(campaign.preview_total or 0),
        preflight_valid=bool(campaign.preflight_valid),
        preflight_snapshot=campaign.preflight_snapshot if isinstance(campaign.preflight_snapshot, dict) else None,
        approved_by=campaign.approved_by,
        approved_at=campaign.approved_at.isoformat() if campaign.approved_at else None,
        requested_review_at=campaign.requested_review_at.isoformat() if campaign.requested_review_at else None,
        run_started_at=campaign.run_started_at.isoformat() if campaign.run_started_at else None,
        run_completed_at=campaign.run_completed_at.isoformat() if campaign.run_completed_at else None,
        last_preview_at=campaign.last_preview_at.isoformat() if campaign.last_preview_at else None,
        executed_at=campaign.executed_at.isoformat() if campaign.executed_at else None,
        created_at=campaign.created_at.isoformat() if campaign.created_at else None,
        updated_at=campaign.updated_at.isoformat() if campaign.updated_at else None,
    )


def _serialize_marketing_audience_funnel(payload: Any) -> Optional[ConsoleMarketingAudienceFunnel]:
    if not isinstance(payload, dict):
        return None
    reason_counts = payload.get("suppression_reason_counts")
    normalized_reason_counts: dict[str, int] = {}
    if isinstance(reason_counts, dict):
        for reason, value in reason_counts.items():
            normalized_reason = str(reason).strip()
            if not normalized_reason:
                continue
            try:
                normalized_reason_counts[normalized_reason] = int(value or 0)
            except Exception:
                normalized_reason_counts[normalized_reason] = 0
    return ConsoleMarketingAudienceFunnel(
        candidate_count=int(payload.get("candidate_count") or 0),
        matched_count=int(payload.get("matched_count") or 0),
        segment_excluded_count=int(payload.get("segment_excluded_count") or 0),
        eligible_count=int(payload.get("eligible_count") or 0),
        suppressed_count=int(payload.get("suppressed_count") or 0),
        suppression_reason_counts=normalized_reason_counts,
    )


def _resolve_marketing_branch(
    context: ConsoleAuthContext,
    db: Session,
    branch_id: UUID,
) -> Branch:
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
    _require_client_access(context, branch.client_id, message="Branch belongs to another tenant")
    if context.client and branch.client_id != context.client.id:
        raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id does not belong to selected client")
    _require_branch_access(context, branch.id, message="Branch access denied for marketing operation")
    if not branch.is_active:
        raise ConsoleAPIError(409, "BRANCH_INACTIVE", "Branch must be active for marketing campaign")
    return branch


def _normalize_marketing_sample_limit(sample_limit: Optional[int]) -> int:
    if sample_limit is None:
        return _MARKETING_SAMPLE_LIMIT_DEFAULT
    if sample_limit < 1 or sample_limit > _MARKETING_SAMPLE_LIMIT_MAX:
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            f"sample_limit must be between 1 and {_MARKETING_SAMPLE_LIMIT_MAX}",
        )
    return sample_limit


def _normalize_marketing_max_recipients(max_recipients: Optional[int]) -> Optional[int]:
    if max_recipients is None:
        return None
    if max_recipients < 1 or max_recipients > _MARKETING_EXECUTE_MAX_LIMIT:
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            f"max_recipients must be between 1 and {_MARKETING_EXECUTE_MAX_LIMIT}",
        )
    return max_recipients


def _normalize_marketing_retry_limit(limit: Optional[int]) -> int:
    if limit is None:
        return _MARKETING_RETRY_LIMIT_DEFAULT
    if limit < 1 or limit > _MARKETING_RETRY_LIMIT_MAX:
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            f"limit must be between 1 and {_MARKETING_RETRY_LIMIT_MAX}",
        )
    return limit


def _normalize_marketing_audience_limit(limit: Optional[int]) -> int:
    if limit is None:
        return _MARKETING_AUDIENCE_LIMIT_DEFAULT
    if limit < 1 or limit > _MARKETING_AUDIENCE_LIMIT_MAX:
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            f"limit must be between 1 and {_MARKETING_AUDIENCE_LIMIT_MAX}",
        )
    return limit


def _normalize_marketing_segment_params_or_error(
    *,
    segment_code: str,
    raw_params: Any,
    field_name: str = "segment_params",
) -> dict[str, Any]:
    try:
        return normalize_marketing_segment_params(
            segment_code,
            raw_params,
            strict=True,
        )
    except ValueError as exc:
        code = str(exc)
        message_by_code = {
            "invalid_segment_params_keys": f"{field_name}: unsupported keys for selected segment",
            "invalid_min_days_since_last_visit": "segment_params.min_days_since_last_visit must be between 1 and 3650",
            "invalid_max_days_since_last_visit": "segment_params.max_days_since_last_visit must be between 1 and 3650",
            "invalid_reactivation_window": "segment_params: min_days_since_last_visit must be <= max_days_since_last_visit",
            "invalid_no_show_window_days": "segment_params.no_show_window_days must be between 1 and 365",
            "invalid_min_no_show_count": "segment_params.min_no_show_count must be between 1 and 10",
            "invalid_engagement_window_days": "segment_params.engagement_window_days must be between 1 and 90",
        }
        if code == "unsupported_segment":
            raise ConsoleAPIError(400, "INVALID_PARAM", "Unsupported segment_code") from exc
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            message_by_code.get(code, f"{field_name} contains invalid values"),
        ) from exc


def _resolve_marketing_campaign(
    context: ConsoleAuthContext,
    db: Session,
    campaign_id: UUID,
) -> MarketingCampaign:
    campaign = db.query(MarketingCampaign).filter(MarketingCampaign.id == campaign_id).first()
    if not campaign:
        raise ConsoleAPIError(404, "NOT_FOUND", "Campaign not found")
    if campaign.client_id != context.client.id:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Campaign belongs to another tenant")
    return campaign


def _effective_marketing_delivery_status(
    *,
    delivery_status: Optional[str],
    outbox_status: Optional[str],
) -> str:
    normalized_delivery = (delivery_status or "").strip().lower()
    if normalized_delivery == "replied":
        return "replied"

    normalized_outbox = (outbox_status or "").strip().upper()
    if normalized_outbox == "FAILED":
        return "failed"
    if normalized_outbox == "SENT":
        return "sent"
    if normalized_outbox in {"PENDING", "PROCESSING"}:
        return "queued"

    if normalized_delivery in {"queued", "sent", "failed", "replied"}:
        return normalized_delivery
    return "queued"


def _serialize_marketing_delivery_sample(
    delivery: MarketingCampaignDelivery,
    *,
    status: Literal["queued", "sent", "failed", "replied"],
    outbox_status: Optional[str],
    last_error: Optional[str],
) -> ConsoleMarketingDeliverySample:
    return ConsoleMarketingDeliverySample(
        delivery_id=delivery.id,
        conversation_id=delivery.conversation_id,
        recipient_jid=delivery.recipient_jid,
        status=status,
        outbox_status=outbox_status,
        last_error=last_error,
        updated_at=delivery.updated_at.isoformat() if delivery.updated_at else None,
    )


def _serialize_marketing_recipient(
    recipient: MarketingCampaignRecipient,
) -> ConsoleMarketingCampaignRecipient:
    reason_codes = recipient.reason_codes if isinstance(recipient.reason_codes, list) else []
    suppression_reasons = (
        recipient.suppression_reasons if isinstance(recipient.suppression_reasons, list) else []
    )
    segment_code = recipient.segment_code if recipient.segment_code in MARKETING_SEGMENT_CODES else "reactivation_30_120"
    return ConsoleMarketingCampaignRecipient(
        id=recipient.id,
        campaign_id=recipient.campaign_id,
        recipient_jid=recipient.recipient_jid,
        user_id=recipient.user_id,
        conversation_id=recipient.conversation_id,
        segment_code=segment_code,
        reason_codes=[str(value) for value in reason_codes],
        reason_hints=[
            hint
            for hint in [describe_marketing_reason_code(str(value)) for value in reason_codes]
            if hint
        ],
        suppressed=bool(recipient.suppressed),
        suppression_reasons=[str(value) for value in suppression_reasons],
        suppression_hints=[
            hint
            for hint in [describe_marketing_suppression_reason(str(value)) for value in suppression_reasons]
            if hint
        ],
        updated_at=recipient.updated_at.isoformat() if recipient.updated_at else None,
    )


def _ensure_unique_oidc_subject(
    db: Session,
    oidc_subject: Optional[str],
    *,
    exclude_agent_id: Optional[UUID] = None,
) -> Optional[str]:
    normalized_subject = _normalize_optional_text(oidc_subject)
    if not normalized_subject:
        return None
    query = db.query(AgentIdentity).filter(
        AgentIdentity.channel == "oidc",
        AgentIdentity.external_id == normalized_subject,
    )
    if exclude_agent_id:
        query = query.filter(AgentIdentity.agent_id != exclude_agent_id)
    if query.first():
        raise ConsoleAPIError(409, "OIDC_SUBJECT_IN_USE", "oidc_subject already linked to another agent")
    return normalized_subject


def _extract_keycloak_realm(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_optional_text(value)
    if not normalized:
        return None
    marker = "/realms/"
    if marker not in normalized:
        return None
    tail = normalized.split(marker, 1)[1].strip("/")
    if not tail:
        return None
    return tail.split("/", 1)[0]


def _extract_keycloak_base_url(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_optional_text(value)
    if not normalized:
        return None
    marker = "/realms/"
    if marker in normalized:
        return normalized.split(marker, 1)[0].rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return None


def _resolve_keycloak_admin_config() -> dict[str, Optional[str]]:
    issuer = _normalize_optional_text(os.environ.get("CONSOLE_OIDC_ISSUER") or os.environ.get("KEYCLOAK_ISSUER"))
    token_url = _normalize_optional_text(os.environ.get("CONSOLE_KEYCLOAK_TOKEN_URL"))
    if not token_url and issuer:
        token_url = f"{issuer.rstrip('/')}/protocol/openid-connect/token"

    realm = (
        _normalize_optional_text(os.environ.get("CONSOLE_KEYCLOAK_REALM"))
        or _normalize_optional_text(os.environ.get("KEYCLOAK_REALM"))
        or _extract_keycloak_realm(issuer)
        or _extract_keycloak_realm(token_url)
    )
    admin_base_url = (
        _normalize_optional_text(os.environ.get("CONSOLE_KEYCLOAK_ADMIN_BASE_URL"))
        or _normalize_optional_text(os.environ.get("KEYCLOAK_ADMIN_BASE_URL"))
        or _extract_keycloak_base_url(issuer)
        or _extract_keycloak_base_url(token_url)
    )
    client_id = _normalize_optional_text(os.environ.get("CONSOLE_KEYCLOAK_CLIENT_ID")) or "admin-cli"
    client_secret = _normalize_optional_text(os.environ.get("CONSOLE_KEYCLOAK_CLIENT_SECRET"))
    admin_username = _normalize_optional_text(
        os.environ.get("CONSOLE_KEYCLOAK_USERNAME")
        or os.environ.get("KEYCLOAK_ADMIN_USERNAME")
        or os.environ.get("KEYCLOAK_USERNAME")
    )
    admin_password = _normalize_optional_text(
        os.environ.get("CONSOLE_KEYCLOAK_PASSWORD")
        or os.environ.get("KEYCLOAK_ADMIN_PASSWORD")
        or os.environ.get("KEYCLOAK_PASSWORD")
    )

    missing = []
    if not token_url:
        missing.append("CONSOLE_KEYCLOAK_TOKEN_URL")
    if not admin_base_url:
        missing.append("CONSOLE_KEYCLOAK_ADMIN_BASE_URL")
    if not realm:
        missing.append("CONSOLE_KEYCLOAK_REALM")
    if not admin_username:
        missing.append("CONSOLE_KEYCLOAK_USERNAME")
    if not admin_password:
        missing.append("CONSOLE_KEYCLOAK_PASSWORD")
    if missing:
        details: dict[str, object] = {"missing": missing}
        aliases: dict[str, list[str]] = {}
        if "CONSOLE_KEYCLOAK_USERNAME" in missing:
            aliases["CONSOLE_KEYCLOAK_USERNAME"] = ["KEYCLOAK_ADMIN_USERNAME", "KEYCLOAK_USERNAME"]
        if "CONSOLE_KEYCLOAK_PASSWORD" in missing:
            aliases["CONSOLE_KEYCLOAK_PASSWORD"] = ["KEYCLOAK_ADMIN_PASSWORD", "KEYCLOAK_PASSWORD"]
        if aliases:
            details["aliases"] = aliases
        raise ConsoleAPIError(
            503,
            "INTEGRATION_UNAVAILABLE",
            "SSO provisioning is not configured",
            details=details,
        )

    return {
        "token_url": token_url,
        "admin_base_url": admin_base_url,
        "realm": realm,
        "client_id": client_id,
        "client_secret": client_secret,
        "admin_username": admin_username,
        "admin_password": admin_password,
    }


def _fetch_keycloak_admin_token(config: dict[str, Optional[str]]) -> str:
    payload = {
        "grant_type": "password",
        "client_id": config.get("client_id") or "admin-cli",
        "username": config.get("admin_username") or "",
        "password": config.get("admin_password") or "",
    }
    client_secret = config.get("client_secret")
    if client_secret:
        payload["client_secret"] = client_secret

    body = urlencode(payload).encode("utf-8")
    req = URLRequest(
        str(config["token_url"]),
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=10) as response:
            raw = response.read()
    except HTTPError as exc:
        raise ConsoleAPIError(503, "INTEGRATION_UNAVAILABLE", "SSO provisioning token request failed") from exc
    except URLError as exc:
        raise ConsoleAPIError(503, "INTEGRATION_UNAVAILABLE", "SSO provisioning endpoint is unreachable") from exc

    try:
        parsed = json.loads((raw or b"{}").decode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive parse guard
        raise ConsoleAPIError(503, "INTEGRATION_UNAVAILABLE", "Invalid SSO token response") from exc
    token = _normalize_optional_text(parsed.get("access_token"))
    if not token:
        raise ConsoleAPIError(503, "INTEGRATION_UNAVAILABLE", "SSO token response missing access_token")
    return token


def _keycloak_lookup_user_id(
    config: dict[str, Optional[str]],
    *,
    access_token: str,
    username: str,
) -> Optional[str]:
    query_url = (
        f"{config['admin_base_url']}/admin/realms/{config['realm']}/users"
        f"?username={quote(username)}&exact=true"
    )
    req = URLRequest(
        query_url,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    try:
        with urlopen(req, timeout=10) as response:
            raw = response.read()
    except HTTPError as exc:
        raise ConsoleAPIError(503, "INTEGRATION_UNAVAILABLE", "SSO user lookup failed") from exc
    except URLError as exc:
        raise ConsoleAPIError(503, "INTEGRATION_UNAVAILABLE", "SSO user lookup endpoint is unreachable") from exc

    try:
        users = json.loads((raw or b"[]").decode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive parse guard
        raise ConsoleAPIError(503, "INTEGRATION_UNAVAILABLE", "Invalid SSO lookup response") from exc
    if not isinstance(users, list) or not users:
        return None
    user_id = _normalize_optional_text((users[0] or {}).get("id"))
    return user_id


def _provision_sso_user_and_get_subject(
    *,
    username: str,
    password: str,
    temporary_password: bool,
) -> str:
    normalized_username = _normalize_required_text(username, "sso_username")
    normalized_password = (password or "").strip()
    if len(normalized_password) < 8:
        raise ConsoleAPIError(400, "INVALID_PARAM", "sso_password must be at least 8 characters")

    config = _resolve_keycloak_admin_config()
    access_token = _fetch_keycloak_admin_token(config)

    existing_user = _keycloak_lookup_user_id(
        config,
        access_token=access_token,
        username=normalized_username,
    )
    if existing_user:
        raise ConsoleAPIError(409, "INVALID_PARAM", "sso_username already exists")

    create_payload = {
        "username": normalized_username,
        "enabled": True,
        "credentials": [
            {
                "type": "password",
                "value": normalized_password,
                "temporary": bool(temporary_password),
            }
        ],
    }
    req = URLRequest(
        f"{config['admin_base_url']}/admin/realms/{config['realm']}/users",
        data=json.dumps(create_payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    created_location = None
    try:
        with urlopen(req, timeout=10) as response:
            created_location = response.headers.get("Location")
    except HTTPError as exc:
        if exc.code == 409:
            raise ConsoleAPIError(409, "INVALID_PARAM", "sso_username already exists") from exc
        if exc.code == 400:
            raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid SSO user payload") from exc
        raise ConsoleAPIError(503, "INTEGRATION_UNAVAILABLE", "SSO user provisioning failed") from exc
    except URLError as exc:
        raise ConsoleAPIError(503, "INTEGRATION_UNAVAILABLE", "SSO user provisioning endpoint is unreachable") from exc

    if created_location:
        user_id = _normalize_optional_text(created_location.rstrip("/").split("/")[-1])
        if user_id:
            return user_id

    resolved_user = _keycloak_lookup_user_id(
        config,
        access_token=access_token,
        username=normalized_username,
    )
    if not resolved_user:
        raise ConsoleAPIError(503, "INTEGRATION_UNAVAILABLE", "SSO user created but subject lookup failed")
    return resolved_user


def _serialize_agent(agent: Agent) -> ConsoleAgent:
    return ConsoleAgent(
        id=agent.id,
        name=agent.name,
        role=agent.role,
        client_id=agent.client_id,
        branch_id=agent.branch_id,
        is_active=agent.is_active,
    )


def _serialize_membership(
    membership: AgentMembership,
    *,
    agent: Optional[Agent] = None,
) -> ConsoleAgentMembership:
    member_agent = agent or membership.agent
    return ConsoleAgentMembership(
        id=membership.id,
        agent_id=membership.agent_id,
        agent_name=member_agent.name if member_agent else None,
        agent_client_id=member_agent.client_id if member_agent else None,
        scope=membership.scope,
        company_id=membership.company_id,
        client_id=membership.client_id,
        branch_id=membership.branch_id,
        role=membership.role,
        is_active=membership.is_active,
        created_at=membership.created_at.isoformat() if membership.created_at else None,
        updated_at=membership.updated_at.isoformat() if membership.updated_at else None,
    )


def _resolve_membership_target(
    db: Session,
    *,
    scope: str,
    company_id: Optional[UUID],
    client_id: Optional[UUID],
    branch_id: Optional[UUID],
) -> _MembershipTarget:
    normalized_scope = (scope or "").strip().lower()
    if normalized_scope not in {"company", "client", "branch"}:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid scope")

    if normalized_scope == "company":
        if not company_id:
            raise ConsoleAPIError(400, "INVALID_PARAM", "company_id required for company scope")
        if client_id or branch_id:
            raise ConsoleAPIError(400, "INVALID_PARAM", "Only company_id is allowed for company scope")
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ConsoleAPIError(404, "NOT_FOUND", "Company not found")
        return _MembershipTarget(
            scope=normalized_scope,
            company_id=company.id,
            client_id=None,
            branch_id=None,
            company=company,
            client=None,
            branch=None,
        )

    if normalized_scope == "client":
        if not client_id:
            raise ConsoleAPIError(400, "INVALID_PARAM", "client_id required for client scope")
        if company_id or branch_id:
            raise ConsoleAPIError(400, "INVALID_PARAM", "Only client_id is allowed for client scope")
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")
        company = db.query(Company).filter(Company.id == client.company_id).first() if client.company_id else None
        return _MembershipTarget(
            scope=normalized_scope,
            company_id=client.company_id,
            client_id=client.id,
            branch_id=None,
            company=company,
            client=client,
            branch=None,
        )

    if not branch_id:
        raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id required for branch scope")
    if company_id or client_id:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Only branch_id is allowed for branch scope")
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
    client = db.query(Client).filter(Client.id == branch.client_id).first()
    if not client:
        raise ConsoleAPIError(404, "NOT_FOUND", "Client not found for branch")
    company = db.query(Company).filter(Company.id == client.company_id).first() if client.company_id else None
    return _MembershipTarget(
        scope=normalized_scope,
        company_id=client.company_id,
        client_id=client.id,
        branch_id=branch.id,
        company=company,
        client=client,
        branch=branch,
    )


def _assert_membership_target_access(
    context: ConsoleAuthContext,
    target: _MembershipTarget,
) -> None:
    if target.client_id:
        _require_client_access(context, target.client_id)
    elif target.company_id:
        _require_company_access(context, target.company_id)

    if target.branch_id:
        _require_branch_access(
            context,
            target.branch_id,
            message="Branch belongs to another tenant",
        )


def _assert_agent_matches_membership_target(
    db: Session,
    *,
    agent: Agent,
    target: _MembershipTarget,
) -> None:
    if target.client_id and agent.client_id != target.client_id:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Agent belongs to another client")
    if target.company_id:
        agent_client = db.query(Client).filter(Client.id == agent.client_id).first()
        if not agent_client:
            raise ConsoleAPIError(404, "NOT_FOUND", "Agent client not found")
        if agent_client.company_id != target.company_id:
            raise ConsoleAPIError(400, "INVALID_PARAM", "Agent belongs to another company")


def _ensure_role_not_deprecated_for_assignment(role: Optional[str]) -> None:
    normalized_role = (role or "").strip().lower()
    if normalized_role in _DEPRECATED_CONSOLE_ASSIGNMENT_ROLES:
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            f"{normalized_role} role is deprecated for assignment; use owner/admin/manager/viewer",
        )


def _ensure_membership_role_is_assignable(role: Optional[str]) -> None:
    _ensure_role_not_deprecated_for_assignment(role)
    if role == "platform_admin":
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            "platform_admin role cannot be assigned via membership",
        )


def _ensure_membership_agent_is_mutable(agent: Agent) -> None:
    if agent.role == "platform_admin":
        raise ConsoleAPIError(
            409,
            "INVALID_STATE",
            "platform_admin membership is managed automatically",
        )


def _is_privileged_access_role(role: Optional[str]) -> bool:
    return (role or "").strip().lower() in _PRIVILEGED_ACCESS_ROLES


def _has_other_privileged_access_for_client(
    db: Session,
    *,
    client: Client,
    excluded_agent_ids: Optional[set[UUID]] = None,
    excluded_membership_ids: Optional[set[UUID]] = None,
) -> bool:
    excluded_agent_ids = excluded_agent_ids or set()
    excluded_membership_ids = excluded_membership_ids or set()

    platform_admin_query = db.query(Agent.id).filter(
        Agent.is_active.is_(True),
        Agent.role == "platform_admin",
    )
    if excluded_agent_ids:
        platform_admin_query = platform_admin_query.filter(~Agent.id.in_(excluded_agent_ids))
    if platform_admin_query.first():
        return True

    branch_ids = [row[0] for row in db.query(Branch.id).filter(Branch.client_id == client.id).all()]
    scope_filters = [and_(AgentMembership.scope == "client", AgentMembership.client_id == client.id)]
    if branch_ids:
        scope_filters.append(and_(AgentMembership.scope == "branch", AgentMembership.branch_id.in_(branch_ids)))
    if client.company_id:
        scope_filters.append(and_(AgentMembership.scope == "company", AgentMembership.company_id == client.company_id))

    membership_query = (
        db.query(AgentMembership.id)
        .join(Agent, Agent.id == AgentMembership.agent_id)
        .filter(
            Agent.is_active.is_(True),
            AgentMembership.is_active.is_(True),
            AgentMembership.role.in_(tuple(_PRIVILEGED_ACCESS_ROLES)),
            or_(*scope_filters),
        )
    )
    if excluded_agent_ids:
        membership_query = membership_query.filter(~AgentMembership.agent_id.in_(excluded_agent_ids))
    if excluded_membership_ids:
        membership_query = membership_query.filter(~AgentMembership.id.in_(excluded_membership_ids))
    if membership_query.first():
        return True

    legacy_agent_query = db.query(Agent).filter(
        Agent.is_active.is_(True),
        Agent.client_id == client.id,
        Agent.role.in_(tuple(_PRIVILEGED_ACCESS_ROLES)),
    )
    if excluded_agent_ids:
        legacy_agent_query = legacy_agent_query.filter(~Agent.id.in_(excluded_agent_ids))
    legacy_candidates = legacy_agent_query.all()
    if not legacy_candidates:
        return False

    candidate_ids = [agent.id for agent in legacy_candidates]
    membership_agent_ids = set()
    if candidate_ids:
        membership_agent_ids = {
            row[0]
            for row in db.query(AgentMembership.agent_id)
            .filter(AgentMembership.agent_id.in_(candidate_ids))
            .distinct()
            .all()
        }
    return any(agent.id not in membership_agent_ids for agent in legacy_candidates)


def _ensure_membership_change_keeps_privileged_access(
    db: Session,
    *,
    context: ConsoleAuthContext,
    membership: AgentMembership,
    agent: Agent,
    next_role: str,
    next_is_active: bool,
) -> None:
    current_privileged = membership.is_active and _is_privileged_access_role(membership.role)
    next_privileged = next_is_active and _is_privileged_access_role(next_role)
    if not current_privileged or next_privileged:
        return
    if membership.agent_id == context.agent.id:
        raise ConsoleAPIError(409, "INVALID_STATE", "Cannot disable or downgrade your own privileged membership")

    client = db.query(Client).filter(Client.id == agent.client_id).first()
    if not client:
        raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")
    if not _has_other_privileged_access_for_client(
        db,
        client=client,
        excluded_membership_ids={membership.id},
    ):
        raise ConsoleAPIError(
            409,
            "INVALID_STATE",
            "Cannot remove last active privileged membership for this client",
        )


def _ensure_agent_lifecycle_is_mutable(
    db: Session,
    *,
    context: ConsoleAuthContext,
    agent: Agent,
    enabling: bool,
) -> None:
    if agent.role == "platform_admin":
        raise ConsoleAPIError(409, "INVALID_STATE", "platform_admin account is protected")
    if not enabling and agent.id == context.agent.id:
        raise ConsoleAPIError(409, "INVALID_STATE", "Cannot disable your own account")
    if enabling or not _is_privileged_access_role(agent.role):
        return

    client = db.query(Client).filter(Client.id == agent.client_id).first()
    if not client:
        raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")
    if not _has_other_privileged_access_for_client(
        db,
        client=client,
        excluded_agent_ids={agent.id},
    ):
        raise ConsoleAPIError(409, "INVALID_STATE", "Cannot disable the last active privileged account for this client")


def _create_agent_with_membership(
    db: Session,
    *,
    client: Client,
    role: str,
    branch: Optional[Branch],
    name: Optional[str],
    is_active: bool,
    oidc_subject: Optional[str],
    linked_from: str,
    now: Optional[datetime] = None,
) -> Agent:
    created_at = now or datetime.now(timezone.utc)
    normalized_subject = _ensure_unique_oidc_subject(db, oidc_subject)

    agent = Agent(
        id=uuid4(),
        client_id=client.id,
        branch_id=branch.id if branch else None,
        role=role,
        name=_normalize_optional_text(name),
        is_active=is_active,
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(agent)

    # platform_admin is a global agent role; memberships are tenant-scoped only.
    if role != "platform_admin":
        membership = AgentMembership(
            id=uuid4(),
            agent_id=agent.id,
            scope="branch" if branch else "client",
            company_id=client.company_id,
            client_id=client.id,
            branch_id=branch.id if branch else None,
            role=role,
            is_active=is_active,
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(membership)

    if normalized_subject:
        identity = AgentIdentity(
            id=uuid4(),
            agent_id=agent.id,
            channel="oidc",
            external_id=normalized_subject,
            username=_normalize_optional_text(name),
            identity_metadata={"linked_from": linked_from},
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(identity)

    return agent


def _apply_membership_target_filters(
    query,
    *,
    scope: str,
    company_id: Optional[UUID],
    client_id: Optional[UUID],
    branch_id: Optional[UUID],
):
    query = query.filter(AgentMembership.scope == scope)
    if company_id:
        query = query.filter(AgentMembership.company_id == company_id)
    else:
        query = query.filter(AgentMembership.company_id.is_(None))
    if client_id:
        query = query.filter(AgentMembership.client_id == client_id)
    else:
        query = query.filter(AgentMembership.client_id.is_(None))
    if branch_id:
        query = query.filter(AgentMembership.branch_id == branch_id)
    else:
        query = query.filter(AgentMembership.branch_id.is_(None))
    return query


def _parse_fleet_lifecycle_param(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized == "all":
        return None
    if normalized not in _FLEET_LIFECYCLE_STATES:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid fleet_lifecycle")
    return normalized


def _parse_fleet_payment_param(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized == "all":
        return None
    if normalized not in _FLEET_PAYMENT_STATES:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid payment_status")
    return normalized


def _parse_fleet_service_param(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized == "all":
        return None
    if normalized not in _FLEET_SERVICE_STATES:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid service_state")
    return normalized


def _is_client_active_status(status: Optional[str]) -> bool:
    return (status or "").strip().lower() == _CLIENT_STATUS_ACTIVE


def _normalize_fleet_payment_status(value: Optional[str]) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"pending", "confirmed", "rejected"}:
        return normalized
    return "unknown"


def _resolve_fleet_commercial_state(payment_status: str) -> str:
    if payment_status == "confirmed":
        return "payment_confirmed"
    if payment_status == "pending":
        return "payment_pending"
    if payment_status == "rejected":
        return "payment_rejected"
    return "contract_missing"


def _resolve_fleet_service_state(
    *,
    client_active: bool,
    active_branches: int,
    degraded_branches: int,
    go_live_ready_branches: int,
) -> str:
    if not client_active:
        return "attention"
    if active_branches <= 0:
        return "attention"
    if degraded_branches > 0:
        return "degraded"
    if go_live_ready_branches < active_branches:
        return "attention"
    return "ok"


def _resolve_fleet_lifecycle_override(client: Client, company: Optional[Company]) -> Optional[str]:
    candidates: list[Optional[str]] = []
    if company and isinstance(company.billing_info, dict):
        candidates.append(company.billing_info.get("lifecycle_state"))
        candidates.append(company.billing_info.get("service_lifecycle_state"))
    if isinstance(client.config, dict):
        candidates.append(client.config.get("lifecycle_state"))
        candidates.append(client.config.get("service_lifecycle_state"))
    for raw in candidates:
        normalized = (raw or "").strip().lower() if isinstance(raw, str) else ""
        if normalized in _FLEET_LIFECYCLE_STATES:
            return normalized
    return None


def _resolve_fleet_lifecycle_state(
    *,
    client: Client,
    company: Optional[Company],
    payment_status: str,
    active_branches: int,
    go_live_ready_branches: int,
) -> str:
    override = _resolve_fleet_lifecycle_override(client, company)
    if override:
        return override
    if not _is_client_active_status(client.status):
        return "archived"
    if payment_status == "rejected":
        return "paused"
    if active_branches <= 0:
        if payment_status == "confirmed":
            return "onboarding"
        return "contracting"
    if go_live_ready_branches < active_branches:
        return "onboarding"
    if payment_status != "confirmed":
        return "go_live_ready"
    return "active"


def _resolve_fleet_next_action(
    *,
    lifecycle_state: str,
    service_state: str,
    payment_status: str,
) -> str:
    if lifecycle_state == "lead":
        return "qualify_and_collect_contract"
    if lifecycle_state == "contracting":
        return "collect_signed_contract_and_payment"
    if lifecycle_state == "onboarding":
        return "complete_onboarding_steps"
    if lifecycle_state == "go_live_ready":
        if payment_status != "confirmed":
            return "confirm_payment_and_approve_go_live"
        return "approve_go_live"
    if lifecycle_state == "paused":
        return "resolve_payment_or_service_blocker"
    if lifecycle_state == "archived":
        return "archived_no_action"
    if service_state == "degraded":
        return "run_integration_recovery"
    if service_state == "attention":
        return "resolve_attention_items"
    return "monitor_sla_and_quality"


def _build_reference_branch_decisions(
    *,
    branches: list[Branch],
    inbound_observations: dict[UUID, tuple[datetime, Optional[str]]],
    now: datetime,
) -> dict[UUID, tuple[tuple[UUID, ...], str]]:
    signals: list[ReferenceBranchSignal] = []
    for branch in branches:
        observed = inbound_observations.get(branch.id)
        last_inbound_at = observed[0] if observed else None
        signals.append(
            ReferenceBranchSignal(
                branch_id=branch.id,
                client_id=branch.client_id,
                is_active=bool(branch.is_active),
                slug=branch.slug,
                created_at=branch.created_at,
                has_instance_id=bool(_normalize_optional_text(branch.instance_id)),
                has_phone=bool(_normalize_optional_text(branch.phone)),
                has_recent_inbound=_reference_branch_has_recent_inbound(
                    last_inbound_at,
                    now=now,
                    window_days=_FLEET_REFERENCE_BRANCH_RECENT_INBOUND_DAYS,
                ),
                go_live_allowed=_is_branch_go_live_allowed(branch, now=now),
                onboarding_go_no_go=(branch.onboarding_state or "").strip().lower() == "go_no_go",
                integration_ok=(branch.integration_state or "").strip().lower() == "ok",
            )
        )
    decisions = select_reference_branch_ids(signals)
    return {
        client_id: (decision.branch_ids, decision.reason)
        for client_id, decision in decisions.items()
    }


def _select_reference_active_branches(
    branches: list[Branch],
    *,
    reference_branch_ids: tuple[UUID, ...],
) -> list[Branch]:
    active_branches = [branch for branch in branches if branch.is_active]
    if not active_branches:
        return []
    selected_ids = set(reference_branch_ids)
    if not selected_ids:
        return active_branches
    selected = [branch for branch in active_branches if branch.id in selected_ids]
    return selected or active_branches


def _build_fleet_client_details_map(
    db: Session,
    *,
    clients: list[Client],
    companies_by_id: dict[UUID, Company],
) -> dict[UUID, _FleetClientDetails]:
    if not clients:
        return {}

    client_ids = [client.id for client in clients]

    branch_stats: dict[UUID, dict[str, int]] = {
        client_id: {
            "total_branches": 0,
            "active_branches": 0,
            "degraded_branches": 0,
            "go_live_ready_branches": 0,
        }
        for client_id in client_ids
    }
    branches = db.query(Branch).filter(Branch.client_id.in_(client_ids)).all()
    branches_by_client: dict[UUID, list[Branch]] = {client_id: [] for client_id in client_ids}
    for branch in branches:
        branches_by_client.setdefault(branch.client_id, []).append(branch)
    now = datetime.now(timezone.utc)
    inbound_observations = _load_latest_branch_inbound_observations_for_clients(
        db,
        client_ids=client_ids,
    )
    reference_decisions = _build_reference_branch_decisions(
        branches=branches,
        inbound_observations=inbound_observations,
        now=now,
    )
    for client_id in client_ids:
        client_branches = branches_by_client.get(client_id, [])
        reference_branch_ids, _reason = reference_decisions.get(
            client_id,
            (tuple(), "no_active_branches"),
        )
        scoped_branches = _select_reference_active_branches(
            client_branches,
            reference_branch_ids=reference_branch_ids,
        )
        stats = branch_stats.setdefault(
            client_id,
            {
                "total_branches": 0,
                "active_branches": 0,
                "degraded_branches": 0,
                "go_live_ready_branches": 0,
            },
        )
        stats["total_branches"] = len(scoped_branches)
        stats["active_branches"] = len(scoped_branches)
        stats["go_live_ready_branches"] = sum(
            1
            for branch in scoped_branches
            if (branch.onboarding_state or "").strip().lower() == "go_no_go"
        )
        stats["degraded_branches"] = sum(
            1
            for branch in scoped_branches
            if (branch.integration_state or "").strip().lower() == "degraded"
        )

    owner_by_client: dict[UUID, Optional[str]] = {client_id: None for client_id in client_ids}
    owners = (
        db.query(Agent)
        .filter(
            Agent.client_id.in_(client_ids),
            Agent.is_active.is_(True),
            Agent.role.in_(["owner", "admin"]),
        )
        .order_by(
            case((Agent.role == "owner", 0), else_=1),
            Agent.created_at.asc(),
        )
        .all()
    )
    for agent in owners:
        if owner_by_client.get(agent.client_id):
            continue
        owner_by_client[agent.client_id] = (agent.name or "").strip() or None

    payment_by_client: dict[UUID, str] = {client_id: "unknown" for client_id in client_ids}
    contracts = (
        db.query(ClientOnboardingContract)
        .filter(
            ClientOnboardingContract.client_id.in_(client_ids),
            ClientOnboardingContract.status == "active",
        )
        .order_by(
            ClientOnboardingContract.updated_at.desc(),
            ClientOnboardingContract.created_at.desc(),
        )
        .all()
    )
    for contract in contracts:
        if payment_by_client.get(contract.client_id) != "unknown":
            continue
        payment_by_client[contract.client_id] = _normalize_fleet_payment_status(contract.payment_status)

    details: dict[UUID, _FleetClientDetails] = {}
    for client in clients:
        company = companies_by_id.get(client.company_id) if client.company_id else None
        stats = branch_stats.get(
            client.id,
            {
                "total_branches": 0,
                "active_branches": 0,
                "degraded_branches": 0,
                "go_live_ready_branches": 0,
            },
        )
        reference_branch_ids, reference_branch_reason = reference_decisions.get(
            client.id,
            (tuple(), "no_active_branches"),
        )
        payment_status = payment_by_client.get(client.id, "unknown")
        commercial_state = _resolve_fleet_commercial_state(payment_status)
        service_state = _resolve_fleet_service_state(
            client_active=_is_client_active_status(client.status),
            active_branches=stats["active_branches"],
            degraded_branches=stats["degraded_branches"],
            go_live_ready_branches=stats["go_live_ready_branches"],
        )
        lifecycle_state = _resolve_fleet_lifecycle_state(
            client=client,
            company=company,
            payment_status=payment_status,
            active_branches=stats["active_branches"],
            go_live_ready_branches=stats["go_live_ready_branches"],
        )
        next_action = _resolve_fleet_next_action(
            lifecycle_state=lifecycle_state,
            service_state=service_state,
            payment_status=payment_status,
        )
        details[client.id] = _FleetClientDetails(
            lifecycle_state=lifecycle_state,
            payment_status=payment_status,
            commercial_state=commercial_state,
            service_state=service_state,
            owner_name=owner_by_client.get(client.id),
            next_action=next_action,
            total_branches=stats["total_branches"],
            active_branches=stats["active_branches"],
            degraded_branches=stats["degraded_branches"],
            go_live_ready_branches=stats["go_live_ready_branches"],
            reference_branch_ids=tuple(reference_branch_ids),
            reference_branch_reason=reference_branch_reason,
        )
    return details


def _parse_projection_reference_branch_ids(raw_value: Any) -> tuple[UUID, ...]:
    if not isinstance(raw_value, list):
        return tuple()
    normalized: list[UUID] = []
    for item in raw_value:
        if isinstance(item, UUID):
            normalized.append(item)
            continue
        if not isinstance(item, str):
            continue
        try:
            normalized.append(UUID(item))
        except (TypeError, ValueError):
            continue
    return tuple(normalized)


def _build_fleet_client_details_from_projection(
    row: TenantsFleetClientProjection,
) -> Optional[_FleetClientDetails]:
    lifecycle_state = (row.lifecycle_state or "").strip().lower()
    payment_status = (row.payment_status or "").strip().lower()
    commercial_state = (row.commercial_state or "").strip().lower()
    service_state = (row.service_state or "").strip().lower()
    next_action = (row.next_action or "").strip().lower()
    if lifecycle_state not in _FLEET_LIFECYCLE_STATES:
        return None
    if payment_status not in _FLEET_PAYMENT_STATES:
        return None
    if commercial_state not in _FLEET_COMMERCIAL_STATES:
        return None
    if service_state not in _FLEET_SERVICE_STATES:
        return None
    if next_action not in _FLEET_NEXT_ACTION_STATES:
        return None
    return _FleetClientDetails(
        lifecycle_state=lifecycle_state,
        payment_status=payment_status,
        commercial_state=commercial_state,
        service_state=service_state,
        owner_name=_normalize_optional_text(row.owner_name),
        next_action=next_action,
        total_branches=max(int(row.total_branches or 0), 0),
        active_branches=max(int(row.active_branches or 0), 0),
        degraded_branches=max(int(row.degraded_branches or 0), 0),
        go_live_ready_branches=max(int(row.go_live_ready_branches or 0), 0),
        reference_branch_ids=_parse_projection_reference_branch_ids(row.reference_branch_ids),
        reference_branch_reason=(row.reference_branch_reason or "no_active_branches").strip() or "no_active_branches",
    )


def _load_materialized_fleet_client_details_map(
    db: Session,
    *,
    client_ids: set[UUID],
) -> tuple[dict[UUID, _FleetClientDetails], Optional[float]]:
    if not _TENANTS_FLEET_CLIENT_PROJECTION_ENABLED:
        return {}, None
    if not client_ids:
        return {}, None
    try:
        rows = (
            db.query(TenantsFleetClientProjection)
            .filter(TenantsFleetClientProjection.client_id.in_(list(client_ids)))
            .all()
        )
    except ProgrammingError as exc:
        db.rollback()
        if _is_tenants_fleet_client_projection_table_missing_error(exc):
            return {}, None
        return {}, None
    except Exception:
        db.rollback()
        return {}, None

    details_map: dict[UUID, _FleetClientDetails] = {}
    max_freshness_lag_seconds: Optional[float] = None
    now = datetime.now(timezone.utc)
    for row in rows:
        details = _build_fleet_client_details_from_projection(row)
        if not details:
            continue
        details_map[row.client_id] = details
        refreshed_at = getattr(row, "refreshed_at", None)
        if isinstance(refreshed_at, datetime):
            refreshed_at_utc = refreshed_at if refreshed_at.tzinfo else refreshed_at.replace(tzinfo=timezone.utc)
            lag_seconds = max((now - refreshed_at_utc).total_seconds(), 0.0)
            if max_freshness_lag_seconds is None or lag_seconds > max_freshness_lag_seconds:
                max_freshness_lag_seconds = lag_seconds
    return details_map, max_freshness_lag_seconds


def _upsert_materialized_fleet_client_details(
    db: Session,
    *,
    details_by_client_id: dict[UUID, _FleetClientDetails],
    company_id_by_client_id: dict[UUID, Optional[UUID]],
    now: datetime,
) -> bool:
    if not _TENANTS_FLEET_CLIENT_PROJECTION_ENABLED:
        return False
    if not details_by_client_id:
        return False
    client_ids = list(details_by_client_id.keys())
    try:
        rows = (
            db.query(TenantsFleetClientProjection)
            .filter(TenantsFleetClientProjection.client_id.in_(client_ids))
            .all()
        )
    except ProgrammingError as exc:
        db.rollback()
        if _is_tenants_fleet_client_projection_table_missing_error(exc):
            return False
        return False
    except Exception:
        db.rollback()
        return False

    row_by_client_id = {row.client_id: row for row in rows}
    for client_id, details in details_by_client_id.items():
        row = row_by_client_id.get(client_id)
        if row is None:
            row = TenantsFleetClientProjection(
                client_id=client_id,
                created_at=now,
            )
            db.add(row)
        row.company_id = company_id_by_client_id.get(client_id)
        row.lifecycle_state = details.lifecycle_state
        row.payment_status = details.payment_status
        row.commercial_state = details.commercial_state
        row.service_state = details.service_state
        row.owner_name = details.owner_name
        row.next_action = details.next_action
        row.total_branches = details.total_branches
        row.active_branches = details.active_branches
        row.degraded_branches = details.degraded_branches
        row.go_live_ready_branches = details.go_live_ready_branches
        row.reference_branch_ids = [str(branch_id) for branch_id in details.reference_branch_ids]
        row.reference_branch_reason = details.reference_branch_reason
        row.refreshed_at = now
        row.updated_at = now
    return True


def _compact_materialized_fleet_client_scope(
    db: Session,
    *,
    company_id: UUID,
    keep_client_ids: set[UUID],
) -> None:
    if not _TENANTS_FLEET_CLIENT_PROJECTION_ENABLED:
        return
    if len(keep_client_ids) > _TENANTS_FLEET_CLIENT_PROJECTION_COMPACTION_MAX_CLIENTS:
        return
    try:
        delete_query = db.query(TenantsFleetClientProjection).filter(
            TenantsFleetClientProjection.company_id == company_id,
        )
        if keep_client_ids:
            delete_query = delete_query.filter(
                TenantsFleetClientProjection.client_id.notin_(list(keep_client_ids))
            )
        delete_query.delete(synchronize_session=False)
    except ProgrammingError as exc:
        db.rollback()
        if _is_tenants_fleet_client_projection_table_missing_error(exc):
            return
    except Exception:
        db.rollback()
        return


def _compact_stale_materialized_fleet_projection_rows() -> int:
    if not _TENANTS_FLEET_CLIENT_PROJECTION_ENABLED:
        return 0
    if not _TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_ENABLED:
        return 0
    db = SessionLocal()
    stale_before = datetime.now(timezone.utc) - timedelta(seconds=_TENANTS_FLEET_CLIENT_PROJECTION_STALE_AFTER_SECONDS)
    try:
        stale_rows = (
            db.query(
                TenantsFleetClientProjection.id,
                TenantsFleetClientProjection.company_id,
            )
            .filter(TenantsFleetClientProjection.refreshed_at < stale_before)
            .order_by(TenantsFleetClientProjection.refreshed_at.asc(), TenantsFleetClientProjection.id.asc())
            .limit(_TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_MAX_DELETE)
            .all()
        )
        stale_ids: list[UUID] = []
        stale_company_ids: set[UUID] = set()
        for row in stale_rows:
            raw_projection_id: Any = None
            raw_company_id: Any = None
            if isinstance(row, tuple):
                raw_projection_id = row[0] if len(row) > 0 else None
                raw_company_id = row[1] if len(row) > 1 else None
            else:
                raw_projection_id = getattr(row, "id", None)
                raw_company_id = getattr(row, "company_id", None)
            if isinstance(raw_projection_id, UUID):
                stale_ids.append(raw_projection_id)
            elif raw_projection_id:
                try:
                    stale_ids.append(UUID(str(raw_projection_id)))
                except (TypeError, ValueError):
                    continue
            if isinstance(raw_company_id, UUID):
                stale_company_ids.add(raw_company_id)
            elif raw_company_id:
                try:
                    stale_company_ids.add(UUID(str(raw_company_id)))
                except (TypeError, ValueError):
                    continue
        if not stale_ids:
            record_tenants_fleet_projection_compaction(outcome="noop", deleted_rows=0)
            return 0
        deleted_rows = (
            db.query(TenantsFleetClientProjection)
            .filter(TenantsFleetClientProjection.id.in_(stale_ids))
            .delete(synchronize_session=False)
        )
        db.commit()
        deleted_count = max(int(deleted_rows or 0), 0)
        if deleted_count > 0 and stale_company_ids:
            try:
                _maybe_enqueue_projection_fallback_prewarm_for_company_ids(
                    company_ids=sorted(stale_company_ids, key=str),
                )
            except Exception:
                # Compaction must stay fail-open even if async prewarm enqueue fails.
                pass
        record_tenants_fleet_projection_compaction(outcome="success", deleted_rows=deleted_count)
        return deleted_count
    except ProgrammingError as exc:
        db.rollback()
        if _is_tenants_fleet_client_projection_table_missing_error(exc):
            record_tenants_fleet_projection_compaction(outcome="table_missing", deleted_rows=0)
            return 0
        record_tenants_fleet_projection_compaction(outcome="error", deleted_rows=0)
        return 0
    except Exception:
        db.rollback()
        record_tenants_fleet_projection_compaction(outcome="error", deleted_rows=0)
        return 0
    finally:
        db.close()


def _maybe_run_fleet_projection_maintenance(*, now_mono: Optional[float] = None) -> None:
    if not _TENANTS_FLEET_CLIENT_PROJECTION_ENABLED:
        return
    if not _TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_ENABLED:
        return
    current_mono = monotonic() if now_mono is None else now_mono
    global _TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_NEXT_ALLOWED_AT
    with _TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_LOCK:
        if current_mono < _TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_NEXT_ALLOWED_AT:
            return
        _TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_NEXT_ALLOWED_AT = (
            current_mono + _TENANTS_FLEET_CLIENT_PROJECTION_MAINTENANCE_INTERVAL_SECONDS
        )
    _compact_stale_materialized_fleet_projection_rows()


def _throttle_projection_fallback_prewarm_company_ids(
    *,
    company_ids: list[UUID],
    now_mono: Optional[float] = None,
) -> set[UUID]:
    if not company_ids:
        return set()
    if _TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_MIN_INTERVAL_SECONDS <= 0:
        return set(company_ids)

    current_mono = monotonic() if now_mono is None else now_mono
    interval_seconds = float(_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_MIN_INTERVAL_SECONDS)
    allowed_company_ids: set[UUID] = set()
    global _TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_NEXT_ALLOWED_BY_COMPANY
    with _TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_LOCK:
        for company_id in company_ids:
            next_allowed_at = _TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_NEXT_ALLOWED_BY_COMPANY.get(
                company_id,
                0.0,
            )
            if current_mono < next_allowed_at:
                continue
            _TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_NEXT_ALLOWED_BY_COMPANY[company_id] = (
                current_mono + interval_seconds
            )
            allowed_company_ids.add(company_id)

        # Keep per-company throttle map bounded under high-cardinality workloads.
        if len(_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_NEXT_ALLOWED_BY_COMPANY) > 8192:
            _TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_NEXT_ALLOWED_BY_COMPANY = {
                company_id: next_allowed_at
                for company_id, next_allowed_at in _TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_NEXT_ALLOWED_BY_COMPANY.items()
                if next_allowed_at > current_mono
            }
    return allowed_company_ids


def _maybe_enqueue_projection_fallback_prewarm_for_company_ids(
    *,
    company_ids: list[UUID],
) -> None:
    if not _TENANTS_FLEET_CLIENT_PROJECTION_ENABLED:
        return
    if not _TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_ENABLED:
        return
    if not company_ids:
        return

    ordered_unique_company_ids: list[UUID] = []
    seen_company_ids: set[UUID] = set()
    for company_id in company_ids:
        if company_id in seen_company_ids:
            continue
        seen_company_ids.add(company_id)
        ordered_unique_company_ids.append(company_id)
        if len(ordered_unique_company_ids) >= _TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_MAX_COMPANY_SCOPES:
            break

    throttled_company_ids = _throttle_projection_fallback_prewarm_company_ids(
        company_ids=ordered_unique_company_ids,
    )
    if not throttled_company_ids:
        return
    _enqueue_fleet_incremental_prewarm_dispatch(
        company_ids=throttled_company_ids,
        global_prewarm_required=False,
    )


def _maybe_enqueue_projection_fallback_prewarm_for_client_ids(
    *,
    client_ids: set[UUID],
) -> None:
    if not client_ids:
        return
    company_ids = _load_company_ids_for_client_ids(
        client_ids=client_ids,
        max_company_ids=_TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_MAX_COMPANY_SCOPES,
    )
    if not company_ids:
        return
    _maybe_enqueue_projection_fallback_prewarm_for_company_ids(
        company_ids=sorted(company_ids, key=str),
    )


def _maybe_enqueue_projection_fallback_prewarm_for_clients(
    *,
    fallback_clients: list[Client],
    persisted_client_ids: set[UUID],
) -> None:
    if not _TENANTS_FLEET_CLIENT_PROJECTION_ENABLED:
        return
    if not _TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_ENABLED:
        return
    if not fallback_clients:
        return

    raw_company_ids: list[UUID] = []
    seen_company_ids: set[UUID] = set()
    for client in fallback_clients:
        if client.id in persisted_client_ids:
            continue
        company_id = client.company_id
        if not company_id or company_id in seen_company_ids:
            continue
        seen_company_ids.add(company_id)
        raw_company_ids.append(company_id)
        if len(raw_company_ids) >= _TENANTS_FLEET_CLIENT_PROJECTION_FALLBACK_PREWARM_MAX_COMPANY_SCOPES:
            break
    _maybe_enqueue_projection_fallback_prewarm_for_company_ids(
        company_ids=raw_company_ids,
    )


def _load_or_build_fleet_client_details_map(
    db: Session,
    *,
    clients: list[Client],
    companies_by_id: dict[UUID, Company],
    persist_missing: bool = False,
    persist_missing_max_clients: Optional[int] = None,
) -> dict[UUID, _FleetClientDetails]:
    if not clients:
        return {}
    client_ids = {client.id for client in clients}
    details_by_client, max_freshness_lag_seconds = _load_materialized_fleet_client_details_map(
        db,
        client_ids=client_ids,
    )
    materialized_clients = len(details_by_client)
    missing_clients = [client for client in clients if client.id not in details_by_client]
    if not missing_clients:
        record_tenants_fleet_projection_observation(
            total_clients=len(clients),
            materialized_clients=materialized_clients,
            fallback_clients=0,
            max_freshness_lag_seconds=max_freshness_lag_seconds,
        )
        return details_by_client

    missing_companies_by_id = dict(companies_by_id)
    missing_company_ids = {
        client.company_id
        for client in missing_clients
        if client.company_id and client.company_id not in missing_companies_by_id
    }
    if missing_company_ids:
        extra_companies = db.query(Company).filter(Company.id.in_(list(missing_company_ids))).all()
        for company in extra_companies:
            missing_companies_by_id[company.id] = company
    computed_details = _build_fleet_client_details_map(
        db,
        clients=missing_clients,
        companies_by_id=missing_companies_by_id,
    )
    fallback_clients = len(computed_details)
    details_by_client.update(computed_details)
    persisted_client_ids: set[UUID] = set()
    if computed_details and persist_missing:
        details_to_persist = computed_details
        if (
            persist_missing_max_clients is not None
            and persist_missing_max_clients > 0
            and len(details_to_persist) > persist_missing_max_clients
        ):
            limited_client_ids = [
                client.id
                for client in missing_clients
                if client.id in details_to_persist
            ][:persist_missing_max_clients]
            details_to_persist = {
                client_id: details_to_persist[client_id]
                for client_id in limited_client_ids
            }
        if details_to_persist:
            now = datetime.now(timezone.utc)
            persisted = _upsert_materialized_fleet_client_details(
                db,
                details_by_client_id=details_to_persist,
                company_id_by_client_id={
                    client.id: client.company_id
                    for client in missing_clients
                    if client.id in details_to_persist
                },
                now=now,
            )
            if persisted:
                persisted_client_ids = set(details_to_persist.keys())
    if fallback_clients > 0:
        _maybe_enqueue_projection_fallback_prewarm_for_clients(
            fallback_clients=missing_clients,
            persisted_client_ids=persisted_client_ids,
        )
    record_tenants_fleet_projection_observation(
        total_clients=len(clients),
        materialized_clients=materialized_clients,
        fallback_clients=fallback_clients,
        max_freshness_lag_seconds=max_freshness_lag_seconds,
    )
    return details_by_client


def _fleet_client_matches_filters(
    details: _FleetClientDetails,
    *,
    fleet_lifecycle: Optional[str],
    payment_status: Optional[str],
    service_state: Optional[str],
) -> bool:
    if fleet_lifecycle and details.lifecycle_state != fleet_lifecycle:
        return False
    if payment_status and details.payment_status != payment_status:
        return False
    if service_state and details.service_state != service_state:
        return False
    return True


def _interpolated_percentile(values: list[float], percentile: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = ((len(ordered) - 1) * percentile) / 100.0
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    if lower_index == upper_index:
        return ordered[lower_index]
    fraction = rank - lower_index
    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]
    return lower_value + (upper_value - lower_value) * fraction


def _build_onboarding_throughput_metrics(
    db: Session,
    *,
    client_ids: set[UUID],
    window_hours: int = _ONBOARDING_THROUGHPUT_WINDOW_HOURS,
) -> ConsoleOnboardingThroughputMetrics:
    metrics = ConsoleOnboardingThroughputMetrics(window_hours=window_hours)
    if not client_ids:
        return metrics

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=max(window_hours, 1))
    branches = db.query(Branch).filter(Branch.client_id.in_(list(client_ids))).all()

    approved_branch_ids: set[UUID] = set()
    go_live_durations_hours: list[float] = []
    blocker_ages_hours: list[float] = []

    for branch in branches:
        go_live_state = _normalize_branch_go_live_state(getattr(branch, "go_live_state", None))
        reviewed_at = _coerce_utc(getattr(branch, "go_live_reviewed_at", None))
        created_at = _coerce_utc(getattr(branch, "created_at", None))

        if go_live_state == "approved" and reviewed_at and reviewed_at >= window_start:
            approved_branch_ids.add(branch.id)
            if created_at:
                go_live_durations_hours.append(max((reviewed_at - created_at).total_seconds() / 3600.0, 0.0))

        if not getattr(branch, "is_active", False):
            continue
        if _is_branch_go_live_allowed(branch, now=now):
            continue
        blocker_anchor = _coerce_utc(getattr(branch, "onboarding_updated_at", None)) or created_at
        if blocker_anchor:
            blocker_ages_hours.append(max((now - blocker_anchor).total_seconds() / 3600.0, 0.0))

    first_pass_approved = len(approved_branch_ids)
    if approved_branch_ids:
        go_live_events = (
            db.query(
                AuditEvent.branch_id.label("branch_id"),
                AuditEvent.event_type.label("event_type"),
                AuditEvent.created_at.label("created_at"),
            )
            .filter(
                AuditEvent.branch_id.in_(list(approved_branch_ids)),
                AuditEvent.event_type.in_(("branch_go_live_approved", "branch_go_live_rejected")),
            )
            .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
            .all()
        )
        rejected_before_first_approval: set[UUID] = set()
        first_approval_seen: set[UUID] = set()
        for event in go_live_events:
            branch_id = getattr(event, "branch_id", None)
            event_type = getattr(event, "event_type", None)
            if not branch_id or not isinstance(event_type, str):
                continue
            if event_type == "branch_go_live_rejected":
                if branch_id not in first_approval_seen:
                    rejected_before_first_approval.add(branch_id)
                continue
            if event_type == "branch_go_live_approved" and branch_id not in first_approval_seen:
                first_approval_seen.add(branch_id)
        first_pass_approved = sum(1 for branch_id in approved_branch_ids if branch_id not in rejected_before_first_approval)

    resolved_total = 0
    reopened_within_24h = 0
    resolved_state_by_incident: dict[tuple[UUID, str], Optional[datetime]] = {}
    incident_rows = (
        db.query(
            AlertEvent.client_id.label("client_id"),
            AlertEvent.alert_metadata.label("alert_metadata"),
            AlertEvent.created_at.label("created_at"),
            AlertEvent.id.label("id"),
        )
        .filter(
            AlertEvent.client_id.in_(list(client_ids)),
            AlertEvent.alert_type == _INCIDENT_STATE_ALERT_TYPE,
            AlertEvent.alert_metadata.isnot(None),
            AlertEvent.created_at >= (window_start - timedelta(hours=24)),
        )
        .order_by(AlertEvent.created_at.asc(), AlertEvent.id.asc())
        .all()
    )
    for row in incident_rows:
        metadata = getattr(row, "alert_metadata", None)
        if not isinstance(metadata, dict):
            continue
        incident_id = _normalize_optional_text(metadata.get("incident_id"))
        incident_state = _coerce_incident_state(metadata.get("incident_state"))
        event_client_id = getattr(row, "client_id", None)
        event_at = _coerce_utc(getattr(row, "created_at", None))
        if not incident_id or not incident_state or not event_client_id or event_at is None:
            continue
        incident_key = (event_client_id, incident_id)
        if incident_state == "resolved":
            resolved_state_by_incident[incident_key] = event_at
            if event_at >= window_start:
                resolved_total += 1
            continue
        if incident_state not in {"open", "in_progress"}:
            continue
        resolved_at = resolved_state_by_incident.get(incident_key)
        if resolved_at is None or resolved_at < window_start:
            continue
        if event_at <= resolved_at + timedelta(hours=24):
            reopened_within_24h += 1
            resolved_state_by_incident[incident_key] = None

    metrics.approved_branches_total = len(approved_branch_ids)
    metrics.first_pass_approved_branches = first_pass_approved
    median_hours = _interpolated_percentile(go_live_durations_hours, 50.0)
    blocker_age_p95 = _interpolated_percentile(blocker_ages_hours, 95.0)
    metrics.time_to_go_live_median_hours = round(median_hours, 1) if median_hours is not None else None
    metrics.blocker_age_p95_hours = round(blocker_age_p95, 1) if blocker_age_p95 is not None else None
    if metrics.approved_branches_total > 0:
        metrics.first_pass_go_live_rate_pct = round(
            (metrics.first_pass_approved_branches / metrics.approved_branches_total) * 100.0,
            1,
        )
    if resolved_total > 0:
        metrics.incident_reopen_rate_24h_pct = round((reopened_within_24h / resolved_total) * 100.0, 1)
    return metrics


def _compose_fleet_summary(
    *,
    total_clients: int,
    company_ids: set[UUID],
    lifecycle_counts: dict[str, int],
    payment_counts: dict[str, int],
    service_counts: dict[str, int],
    onboarding_throughput: Optional[ConsoleOnboardingThroughputMetrics] = None,
) -> ConsoleFleetSummary:
    return ConsoleFleetSummary(
        total_companies=len(company_ids),
        total_clients=total_clients,
        active_clients=lifecycle_counts["active"],
        onboarding_clients=lifecycle_counts["onboarding"],
        archived_clients=lifecycle_counts["archived"],
        paused_clients=lifecycle_counts["paused"],
        go_live_ready_clients=lifecycle_counts["go_live_ready"],
        degraded_clients=service_counts["degraded"],
        payment_pending_clients=payment_counts["pending"],
        payment_confirmed_clients=payment_counts["confirmed"],
        lifecycle_counts=lifecycle_counts,
        payment_counts=payment_counts,
        service_counts=service_counts,
        onboarding_throughput=onboarding_throughput,
    )


def _build_fleet_summary_for_scope(
    db: Session,
    *,
    build_client_query: Callable[[Optional[datetime]], object],
    fleet_lifecycle: Optional[str],
    payment_status: Optional[str],
    service_state: Optional[str],
    batch_size: int = 200,
    on_batch_details: Optional[Callable[[list[Client], dict[UUID, _FleetClientDetails]], None]] = None,
    persist_projection_missing: bool = False,
    persist_projection_missing_max_clients: Optional[int] = None,
) -> ConsoleFleetSummary:
    lifecycle_counts = {state: 0 for state in _FLEET_LIFECYCLE_ORDER}
    payment_counts = {state: 0 for state in _FLEET_PAYMENT_ORDER}
    service_counts = {state: 0 for state in _FLEET_SERVICE_ORDER}
    total_clients = 0
    company_ids: set[UUID] = set()
    matched_client_ids: set[UUID] = set()
    scan_cursor: Optional[datetime] = None

    while True:
        batch = (
            build_client_query(scan_cursor)
            .order_by(Client.created_at.desc(), Client.id.desc())
            .limit(batch_size)
            .all()
        )
        if not batch:
            break

        batch_company_ids = {client.company_id for client in batch if client.company_id}
        batch_companies_by_id: dict[UUID, Company] = {}
        if batch_company_ids:
            batch_companies = db.query(Company).filter(Company.id.in_(batch_company_ids)).all()
            batch_companies_by_id = {company.id: company for company in batch_companies}

        batch_details = _load_or_build_fleet_client_details_map(
            db,
            clients=batch,
            companies_by_id=batch_companies_by_id,
            persist_missing=persist_projection_missing,
            persist_missing_max_clients=persist_projection_missing_max_clients,
        )
        if on_batch_details is not None:
            on_batch_details(batch, batch_details)

        for client in batch:
            details = batch_details.get(client.id)
            if not details:
                continue
            if not _fleet_client_matches_filters(
                details,
                fleet_lifecycle=fleet_lifecycle,
                payment_status=payment_status,
                service_state=service_state,
            ):
                continue
            total_clients += 1
            matched_client_ids.add(client.id)
            if client.company_id:
                company_ids.add(client.company_id)
            lifecycle_counts[details.lifecycle_state] += 1
            payment_counts[details.payment_status] += 1
            service_counts[details.service_state] += 1

        if len(batch) < batch_size:
            break
        scan_cursor = batch[-1].created_at

    return _compose_fleet_summary(
        total_clients=total_clients,
        company_ids=company_ids,
        lifecycle_counts=lifecycle_counts,
        payment_counts=payment_counts,
        service_counts=service_counts,
        onboarding_throughput=_build_onboarding_throughput_metrics(
            db,
            client_ids=matched_client_ids,
        ),
    )


def _collect_client_archive_blockers(db: Session, client_id: UUID) -> dict[str, list[str]]:
    active_agents = (
        db.query(Agent)
        .filter(Agent.client_id == client_id, Agent.is_active.is_(True))
        .limit(_CLIENT_ARCHIVE_SAMPLE_LIMIT)
        .all()
    )
    active_memberships = (
        db.query(AgentMembership)
        .filter(AgentMembership.client_id == client_id, AgentMembership.is_active.is_(True))
        .limit(_CLIENT_ARCHIVE_SAMPLE_LIMIT)
        .all()
    )
    active_branches = (
        db.query(Branch)
        .filter(Branch.client_id == client_id, Branch.is_active.is_(True))
        .limit(_CLIENT_ARCHIVE_SAMPLE_LIMIT)
        .all()
    )
    return {
        "active_agent_ids": [str(agent.id) for agent in active_agents],
        "active_membership_ids": [str(membership.id) for membership in active_memberships],
        "active_branch_ids": [str(branch.id) for branch in active_branches],
    }


def _is_valid_webhook_url(value: Optional[str]) -> bool:
    url = (value or "").strip()
    if not url:
        return False
    parsed = urlparse(url)
    return bool(parsed.netloc) and parsed.scheme in {"http", "https"} and parsed.path.startswith("/webhook/")


def _extract_instance_id_from_metadata(metadata: Optional[dict]) -> Optional[str]:
    if not isinstance(metadata, dict):
        return None
    direct = metadata.get("instanceId") or metadata.get("instance_id")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    nested = metadata.get("metadata")
    if isinstance(nested, dict):
        nested_value = nested.get("instanceId") or nested.get("instance_id")
        if isinstance(nested_value, str) and nested_value.strip():
            return nested_value.strip()
    return None


def _load_latest_branch_inbound_observations_for_clients(
    db: Session,
    *,
    client_ids: list[UUID],
) -> dict[UUID, tuple[datetime, Optional[str]]]:
    if not client_ids:
        return {}

    ranked = (
        db.query(
            Conversation.branch_id.label("branch_id"),
            Message.created_at.label("created_at"),
            Message.message_metadata.label("metadata"),
            func.row_number()
            .over(
                partition_by=Conversation.branch_id,
                order_by=Message.created_at.desc(),
            )
            .label("rank"),
        )
        .join(Message, Message.conversation_id == Conversation.id)
        .filter(
            Conversation.client_id.in_(client_ids),
            Conversation.branch_id.isnot(None),
            Message.role == "user",
        )
        .subquery()
    )
    rows = (
        db.query(
            ranked.c.branch_id,
            ranked.c.created_at,
            ranked.c.metadata,
        )
        .filter(ranked.c.rank == 1)
        .all()
    )
    observations: dict[UUID, tuple[datetime, Optional[str]]] = {}
    for row in rows:
        branch_id = row.branch_id
        created_at = row.created_at
        if not branch_id or not created_at:
            continue
        instance_id = _extract_instance_id_from_metadata(row.metadata)
        observations[branch_id] = (created_at, instance_id)
    return observations


def _load_latest_branch_inbound_observations(
    db: Session,
    *,
    client_id: UUID,
) -> dict[UUID, tuple[datetime, Optional[str]]]:
    return _load_latest_branch_inbound_observations_for_clients(
        db,
        client_ids=[client_id],
    )


@dataclass(frozen=True)
class _ProviderBindingLifecycle:
    provider: Optional[str] = None
    instance_id: Optional[str] = None
    webhook_status: Optional[str] = None
    paid_until: Optional[str] = None
    owner: Optional[str] = None
    next_renewal_at: Optional[str] = None
    last_rebind_at: Optional[str] = None
    rebind_required: Optional[bool] = None
    alert_state: str = "unknown"
    notes: Optional[str] = None
    payment_status: str = "unknown"
    payment_confirmed_at: Optional[str] = None
    expiry_status: str = "unknown"
    days_until_expiry: Optional[int] = None


def _resolve_provider_binding_expiry(
    due_date: Optional[str],
    *,
    now_date: dt_date,
) -> tuple[str, Optional[int]]:
    value = _normalize_optional_text(due_date)
    if not value:
        return "unknown", None
    try:
        target_date = dt_date.fromisoformat(value)
    except ValueError:
        return "unknown", None
    days_until_expiry = (target_date - now_date).days
    if days_until_expiry < 0:
        return "expired", days_until_expiry
    if days_until_expiry <= _PROVIDER_BINDING_EXPIRING_SOON_DAYS:
        return "expiring_soon", days_until_expiry
    return "ok", days_until_expiry


def _resolve_provider_binding_alert_state(
    *,
    explicit_alert_state: Optional[str],
    webhook_status: Optional[str],
    rebind_required: bool,
    expiry_status: str,
    payment_status: str,
) -> str:
    normalized_explicit = _normalize_optional_text(explicit_alert_state)
    if normalized_explicit not in {"ok", "warn", "critical"}:
        normalized_explicit = None

    derived = "unknown"
    if rebind_required or webhook_status == "rebind_required" or expiry_status == "expired":
        derived = "critical"
    elif expiry_status == "expiring_soon" or payment_status == "pending":
        derived = "warn"
    elif expiry_status == "ok" and payment_status == "confirmed":
        derived = "ok"

    if not normalized_explicit:
        return derived

    rank = {
        "unknown": 0,
        "ok": 1,
        "warn": 2,
        "critical": 3,
    }
    return normalized_explicit if rank[normalized_explicit] >= rank[derived] else derived


def _build_provider_binding_lifecycle_map(
    db: Session,
    *,
    client_ids: list[UUID],
    branches: list[Branch],
    now: datetime,
) -> dict[UUID, _ProviderBindingLifecycle]:
    if not client_ids or not branches:
        return {}

    branch_ids = [branch.id for branch in branches]
    contracts = (
        db.query(ClientOnboardingContract)
        .filter(
            ClientOnboardingContract.client_id.in_(client_ids),
            ClientOnboardingContract.status == "active",
            or_(
                and_(
                    ClientOnboardingContract.scope == "client",
                    ClientOnboardingContract.branch_id.is_(None),
                ),
                and_(
                    ClientOnboardingContract.scope == "branch",
                    ClientOnboardingContract.branch_id.in_(branch_ids),
                ),
            ),
        )
        .order_by(
            ClientOnboardingContract.updated_at.desc(),
            ClientOnboardingContract.created_at.desc(),
        )
        .all()
    )

    client_contracts: dict[UUID, ClientOnboardingContract] = {}
    branch_contracts: dict[UUID, ClientOnboardingContract] = {}
    for contract in contracts:
        if contract.scope == "client" and contract.branch_id is None and contract.client_id not in client_contracts:
            client_contracts[contract.client_id] = contract
            continue
        if contract.scope == "branch" and contract.branch_id and contract.branch_id not in branch_contracts:
            branch_contracts[contract.branch_id] = contract

    lifecycle_by_branch: dict[UUID, _ProviderBindingLifecycle] = {}
    now_date = now.date()
    for branch in branches:
        branch_contract = branch_contracts.get(branch.id)
        client_contract = client_contracts.get(branch.client_id)
        payment_source = _resolve_onboarding_payment_source(
            client_record=client_contract,
            branch_record=branch_contract,
        )
        payment_status = payment_source.payment_status if payment_source else "unknown"
        payment_confirmed_at = (
            payment_source.payment_confirmed_at.isoformat()
            if payment_source and payment_source.payment_confirmed_at
            else None
        )

        client_payload = client_contract.payload_json if client_contract else None
        branch_payload = branch_contract.payload_json if branch_contract else None
        try:
            effective_payload = OnboardingContractPayload.model_validate(
                merge_onboarding_contract(client_payload, branch_payload)
            )
        except ValidationError:
            lifecycle_by_branch[branch.id] = _ProviderBindingLifecycle(
                payment_status=payment_status,
                payment_confirmed_at=payment_confirmed_at,
            )
            continue

        whatsapp_binding = effective_payload.provider_binding.whatsapp
        provider = _normalize_optional_text(whatsapp_binding.provider) if whatsapp_binding else None
        binding_instance_id = _normalize_optional_text(whatsapp_binding.instance_id) if whatsapp_binding else None
        webhook_status = whatsapp_binding.webhook_status if whatsapp_binding else None
        paid_until = _normalize_optional_text(whatsapp_binding.paid_until) if whatsapp_binding else None
        owner = _normalize_optional_text(whatsapp_binding.owner) if whatsapp_binding else None
        next_renewal_at = _normalize_optional_text(whatsapp_binding.next_renewal_at) if whatsapp_binding else None
        if not next_renewal_at:
            next_renewal_at = paid_until
        last_rebind_at = _normalize_optional_text(whatsapp_binding.last_rebind_at) if whatsapp_binding else None
        rebind_required = bool(whatsapp_binding.rebind_required) if whatsapp_binding else False
        if webhook_status == "rebind_required":
            rebind_required = True
        explicit_alert_state = whatsapp_binding.alert_state if whatsapp_binding else None
        notes = _normalize_optional_text(whatsapp_binding.notes) if whatsapp_binding else None
        expiry_status, days_until_expiry = _resolve_provider_binding_expiry(next_renewal_at, now_date=now_date)
        alert_state = _resolve_provider_binding_alert_state(
            explicit_alert_state=explicit_alert_state,
            webhook_status=webhook_status,
            rebind_required=rebind_required,
            expiry_status=expiry_status,
            payment_status=payment_status,
        )
        lifecycle_by_branch[branch.id] = _ProviderBindingLifecycle(
            provider=provider,
            instance_id=binding_instance_id,
            webhook_status=webhook_status,
            paid_until=paid_until,
            owner=owner,
            next_renewal_at=next_renewal_at,
            last_rebind_at=last_rebind_at,
            rebind_required=rebind_required,
            alert_state=alert_state,
            notes=notes,
            payment_status=payment_status,
            payment_confirmed_at=payment_confirmed_at,
            expiry_status=expiry_status,
            days_until_expiry=days_until_expiry,
        )

    return lifecycle_by_branch


def _build_branch_integration_status(
    *,
    client_id: UUID,
    client_slug: str,
    branch: Branch,
    has_telegram_bot_token: bool,
    stale_after_minutes: int,
    last_inbound_at: Optional[datetime],
    last_inbound_instance_id: Optional[str],
    now: datetime,
    provider_binding: Optional[_ProviderBindingLifecycle] = None,
) -> ConsoleBranchIntegrationStatus:
    branch_instance_id = _normalize_optional_text(branch.instance_id)
    branch_telegram_chat_id = _normalize_optional_text(branch.telegram_chat_id)
    integration_state = (_normalize_optional_text(getattr(branch, "integration_state", None)) or "ok").lower()
    if integration_state not in {"ok", "degraded"}:
        integration_state = "ok"
    integration_reason = _normalize_optional_text(getattr(branch, "integration_reason", None))
    integration_checked_at = getattr(branch, "integration_checked_at", None)
    integration_degraded_at = getattr(branch, "integration_degraded_at", None)
    integration_recovered_at = getattr(branch, "integration_recovered_at", None)
    binding = provider_binding or _ProviderBindingLifecycle()
    webhook_url: Optional[str] = None
    webhook_url_valid = False
    drift_issues: list[str] = []

    if branch_instance_id:
        webhook_secret = _normalize_optional_text(branch.webhook_secret) or _derive_webhook_secret_from_instance(
            branch_instance_id
        )
        webhook_url = _build_webhook_url(client_slug=client_slug, webhook_secret=webhook_secret)
        webhook_url_valid = _is_valid_webhook_url(webhook_url)

    if not branch.is_active:
        whatsapp_status = "inactive"
    elif not branch_instance_id:
        whatsapp_status = "missing_instance_id"
        drift_issues.append("missing_instance_id")
    elif last_inbound_instance_id and last_inbound_instance_id != branch_instance_id:
        whatsapp_status = "instance_id_mismatch"
        drift_issues.append("instance_id_mismatch")
    elif not webhook_url_valid:
        whatsapp_status = "invalid_webhook_url"
        drift_issues.append("invalid_webhook_url")
    else:
        stale_cutoff = now - timedelta(minutes=stale_after_minutes)
        if not last_inbound_at or last_inbound_at < stale_cutoff:
            whatsapp_status = "no_recent_inbound"
            drift_issues.append("no_recent_inbound")
        else:
            whatsapp_status = "ok"

    if not branch.is_active:
        telegram_status = "inactive"
    elif not has_telegram_bot_token:
        telegram_status = "missing_bot_token"
    elif not branch_telegram_chat_id:
        telegram_status = "missing_chat_id"
    else:
        telegram_status = "ok"

    status = "ok"
    if branch.is_active and whatsapp_status in {"missing_instance_id", "instance_id_mismatch", "invalid_webhook_url"}:
        status = "error"
    elif branch.is_active and (whatsapp_status == "no_recent_inbound" or telegram_status in {"missing_bot_token", "missing_chat_id"}):
        status = "warn"
    if branch.is_active and integration_state == "degraded":
        status = "error"
        if integration_reason and integration_reason not in drift_issues:
            drift_issues.append(integration_reason)
    if branch.is_active and binding.rebind_required:
        status = "error"
        if "provider_binding_rebind_required" not in drift_issues:
            drift_issues.append("provider_binding_rebind_required")
    if branch.is_active and binding.expiry_status == "expired":
        status = "error"
        if "provider_binding_expired" not in drift_issues:
            drift_issues.append("provider_binding_expired")
    elif branch.is_active and status != "error" and binding.expiry_status == "expiring_soon":
        status = "warn"
        if "provider_binding_expiring_soon" not in drift_issues:
            drift_issues.append("provider_binding_expiring_soon")
    if branch.is_active and status != "error" and binding.alert_state == "critical":
        status = "error"
    elif branch.is_active and status == "ok" and binding.alert_state == "warn":
        status = "warn"

    return ConsoleBranchIntegrationStatus(
        client_id=client_id,
        client_slug=client_slug,
        branch_id=branch.id,
        branch_slug=branch.slug,
        branch_name=branch.name,
        is_active=bool(branch.is_active),
        instance_id=branch_instance_id,
        telegram_chat_id=branch_telegram_chat_id,
        webhook_url=webhook_url,
        webhook_url_valid=webhook_url_valid,
        whatsapp_status=whatsapp_status,
        telegram_status=telegram_status,
        last_inbound_at=last_inbound_at.isoformat() if last_inbound_at else None,
        last_inbound_instance_id=last_inbound_instance_id,
        integration_state=integration_state,
        integration_reason=integration_reason,
        integration_checked_at=integration_checked_at.isoformat() if integration_checked_at else None,
        integration_degraded_at=integration_degraded_at.isoformat() if integration_degraded_at else None,
        integration_recovered_at=integration_recovered_at.isoformat() if integration_recovered_at else None,
        provider_binding_provider=binding.provider,
        provider_binding_instance_id=binding.instance_id,
        provider_binding_webhook_status=binding.webhook_status,
        provider_binding_paid_until=binding.paid_until,
        provider_binding_owner=binding.owner,
        provider_binding_next_renewal_at=binding.next_renewal_at,
        provider_binding_last_rebind_at=binding.last_rebind_at,
        provider_binding_rebind_required=binding.rebind_required,
        provider_binding_alert_state=binding.alert_state,
        provider_binding_notes=binding.notes,
        provider_binding_payment_status=binding.payment_status,
        provider_binding_payment_confirmed_at=binding.payment_confirmed_at,
        provider_binding_expiry_status=binding.expiry_status,
        provider_binding_days_until_expiry=binding.days_until_expiry,
        drift_issues=drift_issues,
        status=status,
    )


def _resolve_provider_ops_decision(
    item: ConsoleBranchIntegrationStatus,
) -> Optional[tuple[str, str, list[str]]]:
    priority_rank = {"p0": 0, "p1": 1, "p2": 2}
    if not item.is_active:
        return None

    reasons: list[str] = []
    priority = "p2"
    recommended_action = "provider_send_reminder"

    def _promote(level: str) -> None:
        nonlocal priority
        if priority_rank[level] < priority_rank[priority]:
            priority = level

    if item.provider_binding_rebind_required:
        reasons.append("provider_binding_rebind_required")
        recommended_action = "provider_complete_rebind"
        _promote("p0")

    if item.provider_binding_expiry_status == "expired":
        reasons.append("provider_binding_expired")
        if recommended_action == "provider_send_reminder":
            recommended_action = "provider_renewal_confirmed"
        _promote("p0")
    elif item.provider_binding_expiry_status == "expiring_soon":
        reasons.append("provider_binding_expiring_soon")
        if recommended_action == "provider_send_reminder":
            recommended_action = "provider_renewal_confirmed"
        _promote("p1")

    if item.whatsapp_status in {"missing_instance_id", "instance_id_mismatch", "invalid_webhook_url"}:
        reasons.append(item.whatsapp_status)
        if recommended_action == "provider_send_reminder":
            recommended_action = "provider_webhook_updated"
        _promote("p0")
    elif item.whatsapp_status == "no_recent_inbound":
        reasons.append("no_recent_inbound")
        if recommended_action == "provider_send_reminder":
            recommended_action = "integration_reconcile"
        _promote("p1")

    if item.integration_state == "degraded":
        reasons.append("integration_degraded")
        if recommended_action == "provider_send_reminder":
            recommended_action = "integration_reconcile"
        _promote("p0")

    if item.provider_binding_alert_state == "critical":
        reasons.append("provider_binding_alert_critical")
        if recommended_action == "provider_send_reminder":
            recommended_action = "provider_start_rebind"
        _promote("p0")
    elif item.provider_binding_alert_state == "warn":
        reasons.append("provider_binding_alert_warn")
        _promote("p1")

    if not reasons:
        return None
    return priority, recommended_action, list(dict.fromkeys(reasons))


def _resolve_provider_ops_sla(
    *,
    priority: Optional[str],
    generated_at: datetime,
    now: datetime,
) -> tuple[Optional[str], str]:
    if not priority:
        return None, "none"
    deadline = generated_at + timedelta(hours=_PROVIDER_OPS_SLA_HOURS_BY_PRIORITY.get(priority, 72))
    remaining = deadline - now
    if remaining.total_seconds() <= 0:
        state = "overdue"
    elif remaining <= timedelta(hours=_PROVIDER_OPS_DUE_SOON_HOURS):
        state = "due_soon"
    else:
        state = "on_track"
    return deadline.isoformat(), state


def _build_provider_ops_queue(
    items: list[ConsoleBranchIntegrationStatus],
    *,
    generated_at: datetime,
) -> list[ConsoleProviderOpsQueueItem]:
    priority_rank = {"p0": 0, "p1": 1, "p2": 2}
    queue_items: list[ConsoleProviderOpsQueueItem] = []
    for item in items:
        decision = _resolve_provider_ops_decision(item)
        if not decision:
            continue
        priority, recommended_action, dedup_reasons = decision
        queue_items.append(
            ConsoleProviderOpsQueueItem(
                client_id=item.client_id,
                client_slug=item.client_slug,
                branch_id=item.branch_id,
                branch_slug=item.branch_slug,
                branch_name=item.branch_name,
                priority=priority,
                recommended_action=recommended_action,
                reasons=dedup_reasons,
                requires_confirmation=True,
                provider_binding_owner=item.provider_binding_owner,
                provider_binding_next_renewal_at=item.provider_binding_next_renewal_at,
                provider_binding_last_rebind_at=item.provider_binding_last_rebind_at,
                provider_binding_alert_state=item.provider_binding_alert_state,
                provider_binding_expiry_status=item.provider_binding_expiry_status,
                provider_binding_days_until_expiry=item.provider_binding_days_until_expiry,
                provider_binding_rebind_required=item.provider_binding_rebind_required,
                generated_at=generated_at.isoformat(),
            )
        )

    queue_items.sort(
        key=lambda queue_item: (
            priority_rank.get(queue_item.priority, 99),
            queue_item.client_slug,
            queue_item.branch_name,
        )
    )
    return queue_items


def _build_provider_lifecycle_item(
    *,
    status: ConsoleBranchIntegrationStatus,
    branch: Branch,
    company_id: Optional[UUID],
    company_name: Optional[str],
    generated_at: datetime,
    now: datetime,
) -> ConsoleProviderLifecycleItem:
    decision = _resolve_provider_ops_decision(status)
    priority: Optional[str] = None
    next_action: Optional[str] = None
    blockers: list[str] = []
    if decision:
        priority, next_action, blockers = decision
    sla_deadline_at, sla_state = _resolve_provider_ops_sla(
        priority=priority,
        generated_at=generated_at,
        now=now,
    )
    return ConsoleProviderLifecycleItem(
        client_id=status.client_id,
        client_slug=status.client_slug,
        branch_id=status.branch_id,
        branch_slug=status.branch_slug,
        branch_name=status.branch_name,
        company_id=company_id,
        company_name=company_name,
        branch_phone=_normalize_optional_text(branch.phone),
        status=status.status,
        whatsapp_status=status.whatsapp_status,
        integration_state=status.integration_state,
        last_inbound_at=status.last_inbound_at,
        instance_id=status.instance_id,
        provider_binding_provider=status.provider_binding_provider,
        provider_binding_instance_id=status.provider_binding_instance_id,
        provider_binding_webhook_status=status.provider_binding_webhook_status,
        provider_binding_paid_until=status.provider_binding_paid_until,
        provider_binding_owner=status.provider_binding_owner,
        provider_binding_next_renewal_at=status.provider_binding_next_renewal_at,
        provider_binding_last_rebind_at=status.provider_binding_last_rebind_at,
        provider_binding_rebind_required=status.provider_binding_rebind_required,
        provider_binding_alert_state=status.provider_binding_alert_state,
        provider_binding_expiry_status=status.provider_binding_expiry_status,
        provider_binding_days_until_expiry=status.provider_binding_days_until_expiry,
        next_action=next_action,
        priority=priority,
        blockers=blockers,
        sla_deadline_at=sla_deadline_at,
        sla_state=sla_state,
        generated_at=generated_at.isoformat(),
    )


def _build_provider_ops_effective_payload(
    *,
    action: str,
    request_payload: ConsoleIntegrationBranchActionRequest,
    branch: Branch,
    binding: _ProviderBindingLifecycle,
    now_date: dt_date,
) -> tuple[dict[str, object], Optional[dict[str, object]], Optional[str]]:
    notes = _normalize_optional_text(request_payload.notes)
    owner = _normalize_optional_text(request_payload.owner) or binding.owner
    requested_instance = _normalize_optional_text(request_payload.instance_id)
    requested_webhook_status = request_payload.webhook_status
    reminder_note = None

    binding_patch: dict[str, object] = {
        "provider": binding.provider or "chatflow",
        "instance_id": requested_instance or binding.instance_id or _normalize_optional_text(branch.instance_id),
        "webhook_status": binding.webhook_status or "pending",
        "paid_until": binding.paid_until,
        "owner": owner,
        "next_renewal_at": binding.next_renewal_at,
        "last_rebind_at": binding.last_rebind_at,
        "rebind_required": bool(binding.rebind_required),
        "alert_state": binding.alert_state if binding.alert_state in {"ok", "warn", "critical"} else "warn",
        "notes": notes or binding.notes,
    }
    branch_patch: Optional[dict[str, object]] = None

    if action == "provider_start_rebind":
        binding_patch["webhook_status"] = "rebind_required"
        binding_patch["rebind_required"] = True
        binding_patch["alert_state"] = "critical"
        if notes:
            binding_patch["notes"] = notes
    elif action == "provider_complete_rebind":
        binding_patch["webhook_status"] = requested_webhook_status or "configured"
        binding_patch["rebind_required"] = False
        binding_patch["alert_state"] = "ok"
        binding_patch["last_rebind_at"] = now_date.isoformat()
        if requested_instance:
            binding_patch["instance_id"] = requested_instance
            branch_patch = {"instance_id": requested_instance}
    elif action == "provider_renewal_confirmed":
        paid_until_value = _normalize_optional_text(request_payload.paid_until)
        next_renewal_value = _normalize_optional_text(request_payload.next_renewal_at)
        if not paid_until_value and not next_renewal_value:
            raise ConsoleAPIError(
                400,
                "INVALID_PARAM",
                "paid_until or next_renewal_at is required for provider_renewal_confirmed",
            )
        paid_until_date = _parse_date_param("paid_until", paid_until_value)
        next_renewal_date = _parse_date_param("next_renewal_at", next_renewal_value)
        if paid_until_date:
            binding_patch["paid_until"] = paid_until_date.isoformat()
        if next_renewal_date:
            binding_patch["next_renewal_at"] = next_renewal_date.isoformat()
        elif paid_until_date:
            binding_patch["next_renewal_at"] = paid_until_date.isoformat()
        binding_patch["alert_state"] = "ok"
        binding_patch["rebind_required"] = False
    elif action == "provider_webhook_updated":
        if requested_instance:
            binding_patch["instance_id"] = requested_instance
            branch_patch = {"instance_id": requested_instance}
        binding_patch["webhook_status"] = requested_webhook_status or "configured"
        if binding_patch["webhook_status"] != "rebind_required":
            binding_patch["rebind_required"] = False
            if binding_patch["alert_state"] == "critical":
                binding_patch["alert_state"] = "warn"
    elif action == "provider_send_reminder":
        reminder_note = notes or "provider lifecycle reminder"
    else:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Unsupported provider ops action")

    return binding_patch, branch_patch, reminder_note


def _emit_integration_drift_signals(
    db: Session,
    *,
    context: ConsoleAuthContext,
    statuses: list[ConsoleBranchIntegrationStatus],
) -> None:
    has_updates = False
    for item in statuses:
        branch_key = str(item.branch_id)
        signature = ",".join(sorted(item.drift_issues))
        with _INTEGRATION_DRIFT_LOCK:
            previous_signature = _INTEGRATION_DRIFT_STATE.get(branch_key, "")
            if signature:
                _INTEGRATION_DRIFT_STATE[branch_key] = signature
            else:
                _INTEGRATION_DRIFT_STATE.pop(branch_key, None)
        if signature == previous_signature:
            continue
        if signature:
            record_audit_event(
                db,
                actor=context.agent,
                event_type="integration_drift_detected",
                entity_type="branch",
                entity_id=item.branch_id,
                payload={
                    "drift_issues": item.drift_issues,
                    "status": item.status,
                    "whatsapp_status": item.whatsapp_status,
                    "telegram_status": item.telegram_status,
                    "integration_state": item.integration_state,
                    "integration_reason": item.integration_reason,
                    "integration_checked_at": item.integration_checked_at,
                    "last_inbound_at": item.last_inbound_at,
                    "last_inbound_instance_id": item.last_inbound_instance_id,
                    "configured_instance_id": item.instance_id,
                },
                client_id=context.client.id,
                branch_id=item.branch_id,
            )
            if any(issue in _INTEGRATION_ALERT_ISSUES for issue in item.drift_issues):
                alert_warning(
                    "Integration drift detected",
                    {
                        "client_id": str(context.client.id),
                        "branch_id": str(item.branch_id),
                        "branch_slug": item.branch_slug,
                        "issues": ",".join(item.drift_issues),
                    },
                )
        else:
            record_audit_event(
                db,
                actor=context.agent,
                event_type="integration_drift_cleared",
                entity_type="branch",
                entity_id=item.branch_id,
                payload={"status": item.status},
                client_id=context.client.id,
                branch_id=item.branch_id,
            )
        has_updates = True

    if has_updates:
        db.commit()


def _resolve_fleet_attention_profile(
    *,
    service_state: str,
    stale_branches: int,
    integration_error_branches: int,
    integration_warn_branches: int,
    outbox_failed_24h: int,
    pending_handovers: int,
) -> tuple[int, str, list[str], list[str]]:
    score = 0
    reasons: list[str] = []
    suggested_actions: list[str] = []

    if integration_error_branches > 0:
        score += min(60, integration_error_branches * 25)
        reasons.append("integration_error")
        suggested_actions.append("open_integrations_registry_and_fix_bindings")

    if stale_branches > 0:
        score += min(30, stale_branches * 10)
        reasons.append("stale_inbound")
        suggested_actions.append("check_webhook_and_inbound_flow")

    if integration_warn_branches > 0:
        score += min(20, integration_warn_branches * 8)
        reasons.append("integration_warn")
        suggested_actions.append("review_integration_warnings")

    if outbox_failed_24h > 0:
        score += min(40, outbox_failed_24h * 5)
        reasons.append("outbox_failed")
        suggested_actions.append("run_outbox_process_job_and_review_errors")

    if pending_handovers > 0:
        score += min(30, pending_handovers * 8)
        reasons.append("pending_handovers")
        suggested_actions.append("review_escalation_queue")

    if service_state == "degraded":
        score += 15
        reasons.append("service_state_degraded")
        suggested_actions.append("execute_integration_recovery_runbook")
    elif service_state == "attention":
        score += 10
        reasons.append("service_state_attention")
        suggested_actions.append("resolve_attention_items")

    score = min(score, 100)

    if score >= _FLEET_ATTENTION_HIGH_THRESHOLD:
        level = "high"
    elif score >= _FLEET_ATTENTION_MEDIUM_THRESHOLD:
        level = "medium"
    else:
        level = "low"

    # Keep payload deterministic and compact.
    reasons = sorted(set(reasons))
    suggested_actions = sorted(set(suggested_actions))
    return score, level, reasons, suggested_actions


def _outbox_actionable_failure_filter():
    event_type = OutboxMessage.payload_json["event_type"].astext
    return or_(
        and_(
            OutboxMessage.last_error.is_(None),
            or_(event_type.is_(None), ~event_type.in_(_OUTBOX_SYSTEM_EVENT_TYPES)),
        ),
        and_(
            ~OutboxMessage.last_error.ilike(f"{_OUTBOX_ARCHIVED_REASON_PREFIX}%"),
            ~OutboxMessage.last_error.ilike(f"{_OUTBOX_CALENDAR_SYNC_REASON_PREFIX}%"),
            or_(event_type.is_(None), ~event_type.in_(_OUTBOX_SYSTEM_EVENT_TYPES)),
        ),
    )


def _query_outbox_failed_24h_map(
    db: Session,
    *,
    client_ids: list[UUID],
    now: datetime,
) -> dict[UUID, int]:
    if not client_ids:
        return {}
    cutoff = now - timedelta(hours=_FLEET_ATTENTION_OUTBOX_WINDOW_HOURS)
    rows = (
        db.query(
            OutboxMessage.client_id,
            func.count(OutboxMessage.id),
        )
        .filter(
            OutboxMessage.client_id.in_(client_ids),
            OutboxMessage.status == "FAILED",
            OutboxMessage.created_at >= cutoff,
            _outbox_actionable_failure_filter(),
        )
        .group_by(OutboxMessage.client_id)
        .all()
    )
    return {row[0]: int(row[1] or 0) for row in rows if row[0]}


def _query_pending_handovers_map(
    db: Session,
    *,
    client_ids: list[UUID],
) -> dict[UUID, int]:
    if not client_ids:
        return {}
    rows = (
        db.query(
            Handover.client_id,
            func.count(Handover.id),
        )
        .filter(
            Handover.client_id.in_(client_ids),
            Handover.status.in_(_FLEET_ATTENTION_HANDOVER_PENDING_STATUSES),
        )
        .group_by(Handover.client_id)
        .all()
    )
    return {row[0]: int(row[1] or 0) for row in rows if row[0]}


def _query_outbox_backlog_map(
    db: Session,
    *,
    client_ids: list[UUID],
) -> dict[UUID, int]:
    if not client_ids:
        return {}
    rows = (
        db.query(
            OutboxMessage.client_id,
            func.count(OutboxMessage.id),
        )
        .filter(
            OutboxMessage.client_id.in_(client_ids),
            OutboxMessage.status.in_(["PENDING", "PROCESSING"]),
        )
        .group_by(OutboxMessage.client_id)
        .all()
    )
    return {row[0]: int(row[1] or 0) for row in rows if row[0]}


def _query_integration_degraded_branch_count_map(
    db: Session,
    *,
    client_ids: list[UUID],
) -> dict[UUID, int]:
    if not client_ids:
        return {}
    rows = (
        db.query(
            Branch.client_id,
            func.count(Branch.id),
        )
        .filter(
            Branch.client_id.in_(client_ids),
            Branch.is_active.is_(True),
            func.lower(func.coalesce(Branch.integration_state, "ok")) == "degraded",
        )
        .group_by(Branch.client_id)
        .all()
    )
    return {row[0]: int(row[1] or 0) for row in rows if row[0]}


def _query_latest_failed_error_map(
    db: Session,
    *,
    client_ids: list[UUID],
    now: datetime,
) -> dict[UUID, str]:
    if not client_ids:
        return {}
    cutoff = now - timedelta(hours=24)
    rows = (
        db.query(
            OutboxMessage.client_id,
            OutboxMessage.last_error,
            OutboxMessage.updated_at,
            OutboxMessage.created_at,
        )
        .filter(
            OutboxMessage.client_id.in_(client_ids),
            OutboxMessage.status == "FAILED",
            OutboxMessage.last_error.isnot(None),
            OutboxMessage.updated_at >= cutoff,
            ~OutboxMessage.last_error.ilike(f"{_OUTBOX_ARCHIVED_REASON_PREFIX}%"),
        )
        .order_by(
            OutboxMessage.client_id.asc(),
            OutboxMessage.updated_at.desc(),
            OutboxMessage.created_at.desc(),
        )
        .all()
    )
    result: dict[UUID, str] = {}
    for client_id, last_error, _updated_at, _created_at in rows:
        if client_id in result:
            continue
        normalized = _normalize_optional_text(last_error)
        if normalized:
            result[client_id] = normalized
    return result


@dataclass
class _IncidentSignals:
    outbox_backlog: int
    outbox_failed_24h: int
    pending_handovers: int
    integration_degraded_branches: int
    last_error: Optional[str]


def _build_incident_actions(
    *,
    reason_code: str,
    outbox_backlog: int,
    integration_degraded_branches: int,
    branch_ids: Optional[list[UUID]],
    platform_scope: bool,
) -> list[ConsoleIncidentAction]:
    actions: list[ConsoleIncidentAction] = []
    outbox_limit = max(10, min(200, outbox_backlog if outbox_backlog > 0 else 25))
    outbox_params: dict[str, object] = {"limit": outbox_limit}
    if branch_ids:
        outbox_params["branch_ids"] = [str(branch_id) for branch_id in branch_ids]

    actions.append(
        ConsoleIncidentAction(
            id="open_ops",
            title="Открыть очередь отправки",
            description="Проверьте failed/pending и тренд ошибок перед действиями.",
            href="/ops",
            dry_run_first=True,
        )
    )
    actions.append(
        ConsoleIncidentAction(
            id="outbox_dry_run",
            title="Запустить dry-run outbox_process",
            description="Безопасная проверка: покажет, сколько сообщений можно обработать сейчас.",
            job_type="outbox_process",
            mode="dry_run",
            params=outbox_params,
            dry_run_first=True,
        )
    )

    if reason_code == "provider_billing_blocked":
        actions.append(
            ConsoleIncidentAction(
                id="open_subscription",
                title="Проверить оплату и тариф",
                description="Откройте Подписку и подтвердите, что оплата у провайдера и лимиты активны.",
                href="/subscription",
                dry_run_first=True,
            )
        )
        actions.append(
            ConsoleIncidentAction(
                id="open_integrations",
                title="Проверить provider binding",
                description="Проверьте paid_until/next_renewal_at и статус интеграции WhatsApp.",
                href="/integrations",
                dry_run_first=True,
            )
        )

    if reason_code == "integration_degraded" or integration_degraded_branches > 0:
        reconcile_params: dict[str, object] = {
            "limit": max(1, min(200, integration_degraded_branches or 25))
        }
        if branch_ids:
            reconcile_params["branch_ids"] = [str(branch_id) for branch_id in branch_ids]
        actions.append(
            ConsoleIncidentAction(
                id="integration_reconcile_dry_run",
                title="Запустить dry-run integration_reconcile",
                description="Проверьте drift/биндинги и оцените эффект до execute.",
                job_type="integration_reconcile",
                mode="dry_run",
                params=reconcile_params,
                dry_run_first=True,
            )
        )
        actions.append(
            ConsoleIncidentAction(
                id="open_integrations",
                title="Проверить интеграции",
                description="Откройте реестр интеграций и исправьте проблемные биндинги.",
                href="/integrations",
                dry_run_first=True,
            )
        )

    if platform_scope:
        actions.append(
            ConsoleIncidentAction(
                id="open_fleet_attention",
                title="Проверить fleet attention",
                description="Сверьте соседние компании с высоким риском и приоритизируйте remediation.",
                href="/tenants",
                dry_run_first=True,
            )
        )
    return actions


def _incident_severity_from_signals(signals: _IncidentSignals) -> Literal["critical", "warn"]:
    if (
        signals.outbox_backlog >= 1000
        or signals.outbox_failed_24h >= 100
        or signals.integration_degraded_branches >= 3
        or signals.pending_handovers >= 30
    ):
        return "critical"
    return "warn"


def _build_outbox_incident_item(
    *,
    scope: Literal["fleet", "client", "branch"],
    signals: _IncidentSignals,
    detected_at: datetime,
    client_id: Optional[UUID],
    client_slug: Optional[str],
    branch_id: Optional[UUID],
    branch_ids: Optional[list[UUID]],
    platform_scope: bool,
) -> ConsoleIncidentItem:
    reason_code, reason_label = _classify_outbox_incident_reason(
        last_error=signals.last_error,
        integration_degraded=signals.integration_degraded_branches > 0,
    )
    severity = _incident_severity_from_signals(signals)
    return ConsoleIncidentItem(
        id=f"outbox-{client_id or 'scope'}",
        scope=scope,
        severity=severity,
        title="Риск доставки сообщений",
        summary=(
            f"backlog={signals.outbox_backlog}, failed_24h={signals.outbox_failed_24h}, "
            f"integration_degraded={signals.integration_degraded_branches}"
        ),
        reason_code=reason_code,
        reason_label=reason_label,
        source="outbox_messages+branches",
        detected_at=detected_at.isoformat(),
        client_id=client_id,
        client_slug=client_slug,
        branch_id=branch_id,
        metrics={
            "outbox_backlog": signals.outbox_backlog,
            "outbox_failed_24h": signals.outbox_failed_24h,
            "integration_degraded_branches": signals.integration_degraded_branches,
            "pending_handovers": signals.pending_handovers,
            "last_error": _truncate_preview(signals.last_error, limit=160),
        },
        actions=_build_incident_actions(
            reason_code=reason_code,
            outbox_backlog=signals.outbox_backlog,
            integration_degraded_branches=signals.integration_degraded_branches,
            branch_ids=branch_ids,
            platform_scope=platform_scope,
        ),
    )


def _build_handover_incident_item(
    *,
    scope: Literal["fleet", "client", "branch"],
    signals: _IncidentSignals,
    detected_at: datetime,
    client_id: Optional[UUID],
    client_slug: Optional[str],
    branch_id: Optional[UUID],
) -> ConsoleIncidentItem:
    severity: Literal["critical", "warn"] = "critical" if signals.pending_handovers >= 30 else "warn"
    return ConsoleIncidentItem(
        id=f"handover-{client_id or 'scope'}",
        scope=scope,
        severity=severity,
        title="Очередь эскалаций перегружена",
        summary=f"pending_handovers={signals.pending_handovers}",
        reason_code="handover_backlog",
        reason_label="Неразобранные эскалации копятся",
        source="handovers",
        detected_at=detected_at.isoformat(),
        client_id=client_id,
        client_slug=client_slug,
        branch_id=branch_id,
        metrics={"pending_handovers": signals.pending_handovers},
        actions=[
            ConsoleIncidentAction(
                id="open_inbox_queue",
                title="Открыть очередь заявок",
                description="Назначьте ответственных менеджеров и разгрузите pending.",
                href="/",
                dry_run_first=True,
            ),
            ConsoleIncidentAction(
                id="open_team_kpi",
                title="Проверить Team KPI",
                description="Проверьте перегрузку по менеджерам и распределите нагрузку.",
                href="/business/team-performance",
                dry_run_first=True,
            ),
        ],
    )


def _build_scope_incident_items(
    *,
    scope: Literal["fleet", "client", "branch"],
    signals: _IncidentSignals,
    detected_at: datetime,
    client_id: Optional[UUID],
    client_slug: Optional[str],
    branch_id: Optional[UUID],
    branch_ids: Optional[list[UUID]],
    platform_scope: bool,
) -> list[ConsoleIncidentItem]:
    items: list[ConsoleIncidentItem] = []
    has_delivery_risk = (
        signals.outbox_backlog >= 500
        or signals.outbox_failed_24h >= 30
        or signals.integration_degraded_branches > 0
    )
    if has_delivery_risk:
        items.append(
            _build_outbox_incident_item(
                scope=scope,
                signals=signals,
                detected_at=detected_at,
                client_id=client_id,
                client_slug=client_slug,
                branch_id=branch_id,
                branch_ids=branch_ids,
                platform_scope=platform_scope,
            )
        )
    if signals.pending_handovers >= 10:
        items.append(
            _build_handover_incident_item(
                scope=scope,
                signals=signals,
                detected_at=detected_at,
                client_id=client_id,
                client_slug=client_slug,
                branch_id=branch_id,
            )
        )
    return items


def _build_incident_summary(items: list[ConsoleIncidentItem]) -> ConsoleIncidentSummary:
    return ConsoleIncidentSummary(
        total=len(items),
        critical=sum(1 for item in items if item.severity == "critical"),
        warn=sum(1 for item in items if item.severity == "warn"),
        info=sum(1 for item in items if item.severity == "info"),
    )


def _coerce_incident_state(value: object) -> Optional[str]:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in _INCIDENT_STATES:
        return normalized
    return None


def _load_incident_state_map(
    db: Session,
    *,
    client_id: UUID,
    incident_ids: list[str],
    allowed_branch_ids: Optional[list[UUID]],
) -> dict[str, dict[str, Optional[str]]]:
    incident_keys = sorted({item.strip() for item in incident_ids if isinstance(item, str) and item.strip()})
    if not incident_keys:
        return {}

    query = db.query(AlertEvent).filter(
        AlertEvent.client_id == client_id,
        AlertEvent.alert_type == _INCIDENT_STATE_ALERT_TYPE,
        AlertEvent.alert_metadata.isnot(None),
        AlertEvent.alert_metadata["incident_id"].astext.in_(incident_keys),
    )
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            return {}
        query = query.filter(or_(AlertEvent.branch_id.is_(None), AlertEvent.branch_id.in_(allowed_branch_ids)))

    rows = query.order_by(AlertEvent.created_at.desc(), AlertEvent.id.desc()).all()
    state_map: dict[str, dict[str, Optional[str]]] = {}
    for row in rows:
        metadata = row.alert_metadata if isinstance(row.alert_metadata, dict) else {}
        incident_id = _normalize_optional_text(metadata.get("incident_id"))
        if not incident_id or incident_id in state_map:
            continue

        incident_state = _coerce_incident_state(metadata.get("incident_state")) or "open"
        owner = _normalize_optional_text(metadata.get("owner"))
        due_at = _normalize_optional_text(metadata.get("due_at"))
        note = _normalize_optional_text(metadata.get("note"))
        state_map[incident_id] = {
            "incident_state": incident_state,
            "incident_state_updated_at": row.created_at.isoformat() if row.created_at else None,
            "incident_state_owner": owner,
            "incident_state_due_at": due_at,
            "incident_state_note": note,
        }
    return state_map


def _apply_incident_state_map(
    items: list[ConsoleIncidentItem],
    *,
    state_map: dict[str, dict[str, Optional[str]]],
) -> None:
    for item in items:
        state_payload = state_map.get(item.id)
        if not state_payload:
            item.incident_state = "open"
            item.incident_state_updated_at = None
            item.incident_state_owner = None
            item.incident_state_due_at = None
            item.incident_state_note = None
            continue
        item.incident_state = state_payload.get("incident_state") or "open"
        item.incident_state_updated_at = state_payload.get("incident_state_updated_at")
        item.incident_state_owner = state_payload.get("incident_state_owner")
        item.incident_state_due_at = state_payload.get("incident_state_due_at")
        item.incident_state_note = state_payload.get("incident_state_note")


def _parse_date_param(name: str, value: Optional[str]) -> Optional[dt_date]:
    if value is None:
        return None
    try:
        return dt_date.fromisoformat(value)
    except ValueError as exc:
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            f"Invalid {name} (expected YYYY-MM-DD)",
        ) from exc


def _parse_datetime_param(name: str, value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            f"Invalid {name} (expected ISO 8601)",
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _parse_cursor_param(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _format_learning_block_reason(reason: Optional[str]) -> str:
    return {
        "consent_not_granted": "consent_not_granted",
        "anonymization_disabled": "anonymization_disabled",
        "retention_expired": "retention_expired",
    }.get(reason, "policy_blocked")


def _resolve_learning_candidate_eligibility(
    learned_response: LearnedResponse,
    *,
    policy,
    now: datetime,
) -> tuple[bool, Optional[str]]:
    if learned_response.status != "pending":
        return False, f"status_{learned_response.status}"
    allowed, reason = evaluate_candidate_eligibility(
        policy,
        retention_expires_at=learned_response.retention_expires_at,
        now=now,
    )
    if not allowed:
        return False, reason
    return True, None


def _parse_sort_param(name: str, value: Optional[str], default: str = "last_activity") -> str:
    if value is None or str(value).strip() == "":
        return default
    normalized = str(value).strip().lower()
    if normalized not in {"last_activity", "created_at", "sla"}:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"Invalid {name}")
    return normalized


def _parse_case_status_param(name: str, value: Optional[str]) -> Optional[list[str]]:
    if value is None or str(value).strip() == "":
        return None
    normalized = str(value).strip().lower()
    if normalized == "open":
        return ["pending", "active"]
    if normalized in {"pending", "active", "resolved"}:
        return [normalized]
    raise ConsoleAPIError(400, "INVALID_PARAM", f"Invalid {name}")


def _resolve_case_sort_cursor(
    *,
    sort_by: str,
    last_activity_at: Optional[datetime],
    created_at: datetime,
) -> datetime:
    if sort_by == "last_activity":
        return last_activity_at or created_at
    return created_at


_OUTBOX_STATUS_MAP = {
    "pending": "PENDING",
    "processing": "PROCESSING",
    "failed": "FAILED",
}

_REMINDER_STATUS_MAP = {
    "pending": "PENDING",
    "sent": "SENT",
    "failed": "FAILED",
}

_REMINDER_RETRY_STATUS_MAP = {
    "pending": ["PENDING"],
    "failed": ["FAILED"],
    "all": ["PENDING", "FAILED"],
}

_OPS_JOB_DEFINITIONS = {
    "outbox_process": {
        "label": "Outbox Process",
        "description": "Process pending outbox messages for the selected tenant scope.",
        "supports_dry_run": True,
    },
    "integration_reconcile": {
        "label": "Integration Reconcile",
        "description": "Reconcile branch integration state and drift markers for selected scope.",
        "supports_dry_run": True,
    },
    "heal": {
        "label": "Heal",
        "description": "Run invariant healing checks in dry-run mode (execute disabled in slice 1).",
        "supports_dry_run": True,
    },
    "metrics_snapshot": {
        "label": "Metrics Snapshot",
        "description": "Compute daily metrics snapshot for the selected client.",
        "supports_dry_run": True,
    },
    "incident_state": {
        "label": "Incident State",
        "description": "Set incident workflow state (open/in_progress/resolved) with audit metadata.",
        "supports_dry_run": True,
    },
}

_INCIDENT_STATE_ALERT_TYPE = "console_incident_state"
_INCIDENT_STATES = {"open", "in_progress", "resolved"}


def _require_ops_access(context: ConsoleAuthContext, *, action: str = "read") -> None:
    message = "Only owner/admin can access ops"
    if action == "write":
        message = "Only owner/admin can manage ops"
    require_console_permission(
        context,
        "ops",
        action,
        message=message,
    )


def _require_platform_admin(context: ConsoleAuthContext) -> None:
    if context.role != "platform_admin":
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Platform admin access required")


def _normalize_outbox_status(status: Optional[str]) -> str:
    if not status:
        return "unknown"
    lowered = status.lower()
    if lowered in _OUTBOX_STATUS_MAP:
        return lowered
    return lowered


def _parse_outbox_status_param(status: Optional[str]) -> Optional[list[str]]:
    if not status:
        return ["FAILED"]
    normalized = status.strip().lower()
    if normalized == "all":
        return None
    if normalized not in _OUTBOX_STATUS_MAP:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid status")
    return [_OUTBOX_STATUS_MAP[normalized]]


def _normalize_reminder_status(status: Optional[str]) -> str:
    if not status:
        return "unknown"
    lowered = status.lower()
    if lowered in _REMINDER_STATUS_MAP:
        return lowered
    return lowered


def _parse_reminder_status_param(status: Optional[str]) -> Optional[list[str]]:
    if not status:
        return None
    normalized = status.strip().lower()
    if normalized == "all":
        return None
    if normalized not in _REMINDER_STATUS_MAP:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid status")
    return [_REMINDER_STATUS_MAP[normalized]]


def _parse_reminder_retry_status_param(status: str) -> list[str]:
    normalized = (status or "").strip().lower()
    if normalized not in _REMINDER_RETRY_STATUS_MAP:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid retry status")
    return _REMINDER_RETRY_STATUS_MAP[normalized]


def _truncate_preview(value: Optional[str], limit: int = 120) -> Optional[str]:
    if not value:
        return None
    preview = value.strip()
    if len(preview) <= limit:
        return preview
    if limit <= 3:
        return preview[:limit]
    return f"{preview[: limit - 3].rstrip()}..."


def _summarize_outbox_payload(payload_json: dict | None) -> dict[str, Optional[str] | bool]:
    if not isinstance(payload_json, dict):
        return {
            "message_type": None,
            "message_preview": None,
            "remote_jid": None,
            "instance_id": None,
            "forwarded_to_telegram": None,
            "channel": None,
        }
    contract, _ = validate_outbox_payload(payload_json)
    if contract:
        message_type = (contract.body.messageType or "").strip() or None
        message_preview = _truncate_preview(contract.body.message)
        remote_jid = contract.body.metadata.remoteJid
        instance_id = contract.body.metadata.instanceId
        forwarded_to_telegram = contract.body.metadata.forwarded_to_telegram
        channel = contract.tenant_context.source if contract.tenant_context else None
        if not channel and remote_jid:
            channel = "whatsapp"
        return {
            "message_type": message_type.lower() if message_type else None,
            "message_preview": message_preview,
            "remote_jid": remote_jid,
            "instance_id": instance_id,
            "forwarded_to_telegram": forwarded_to_telegram,
            "channel": channel,
        }
    body = payload_json.get("body", {}) if isinstance(payload_json.get("body"), dict) else {}
    metadata = body.get("metadata", {}) if isinstance(body.get("metadata"), dict) else {}
    raw_message = body.get("message") if isinstance(body, dict) else None
    remote_jid = metadata.get("remoteJid") or metadata.get("remote_jid")
    instance_id = metadata.get("instanceId") or metadata.get("instance_id")
    forwarded_to_telegram = metadata.get("forwarded_to_telegram") or metadata.get("forwardedToTelegram")
    tenant_context = payload_json.get("tenant_context", {}) if isinstance(payload_json.get("tenant_context"), dict) else {}
    channel = tenant_context.get("source")
    if not channel and remote_jid:
        channel = "whatsapp"
    return {
        "message_type": None,
        "message_preview": _truncate_preview(raw_message if isinstance(raw_message, str) else None),
        "remote_jid": remote_jid,
        "instance_id": instance_id,
        "forwarded_to_telegram": forwarded_to_telegram if isinstance(forwarded_to_telegram, bool) else None,
        "channel": channel,
    }


def _build_outbox_item(row: OutboxMessage) -> ConsoleOutboxItem:
    summary = _summarize_outbox_payload(row.payload_json if isinstance(row.payload_json, dict) else None)
    return ConsoleOutboxItem(
        id=row.id,
        status=_normalize_outbox_status(row.status),
        attempts=row.attempts,
        next_attempt_at=row.next_attempt_at.isoformat() if row.next_attempt_at else None,
        last_error=row.last_error,
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
        conversation_id=row.conversation_id,
        branch_id=row.branch_id,
        inbound_message_id=row.inbound_message_id,
        channel=summary.get("channel"),
        message_type=summary.get("message_type"),
        message_preview=summary.get("message_preview"),
        remote_jid=summary.get("remote_jid"),
        instance_id=summary.get("instance_id"),
        forwarded_to_telegram=summary.get("forwarded_to_telegram"),
    )


def _build_reminder_item(
    row: ReminderJob,
    *,
    outbox_row: Optional[OutboxMessage],
) -> ConsoleReminderItem:
    return ConsoleReminderItem(
        id=row.id,
        appointment_id=row.appointment_id,
        branch_id=row.branch_id,
        channel=row.channel,
        template=row.template,
        run_at=row.run_at.isoformat() if row.run_at else "",
        status=_normalize_reminder_status(row.status),
        attempt=row.attempt,
        max_attempts=row.max_attempts,
        next_attempt_at=row.next_attempt_at.isoformat() if row.next_attempt_at else None,
        last_error=row.last_error,
        dedupe_key=row.dedupe_key,
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
        outbox_id=outbox_row.id if outbox_row else None,
        outbox_status=_normalize_outbox_status(outbox_row.status) if outbox_row else None,
        outbox_attempts=outbox_row.attempts if outbox_row else None,
        outbox_last_error=outbox_row.last_error if outbox_row else None,
        outbox_updated_at=outbox_row.updated_at.isoformat() if outbox_row and outbox_row.updated_at else None,
    )


def _jsonable_payload(value: object) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        raw = value
    else:
        raw = {"value": value}
    return json.loads(json.dumps(raw, default=str))


def _build_ops_job_record(job: ConsoleOpsJob) -> ConsoleOpsJobRecord:
    return ConsoleOpsJobRecord(
        id=job.id,
        job_type=job.job_type,
        mode=job.mode,
        status=job.status,
        created_at=job.created_at.isoformat() if job.created_at else "",
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
        error_message=job.error_message,
        request_payload=job.request_payload if isinstance(job.request_payload, dict) else None,
        result_payload=job.result_payload if isinstance(job.result_payload, dict) else None,
    )


def _parse_ops_job_params(params: Optional[dict]) -> dict:
    if params is None:
        return {}
    if not isinstance(params, dict):
        raise ConsoleAPIError(400, "INVALID_PARAM", "params must be an object")
    return params


def _parse_ops_job_int_param(
    params: dict,
    *,
    name: str,
    default: int,
    min_value: int = 1,
    max_value: Optional[int] = None,
) -> int:
    raw = params.get(name, default)
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{name} must be an integer") from exc
    if value < min_value:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{name} must be >= {min_value}")
    if max_value is not None and value > max_value:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{name} must be <= {max_value}")
    return value


def _parse_ops_job_bool_param(
    params: dict,
    *,
    name: str,
    default: bool = False,
) -> bool:
    raw = params.get(name, default)
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return default
    if isinstance(raw, (int, float)) and raw in {0, 1}:
        return bool(raw)
    if isinstance(raw, str):
        normalized = raw.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ConsoleAPIError(400, "INVALID_PARAM", f"{name} must be a boolean")


def _parse_ops_job_text_param(
    params: dict,
    *,
    name: str,
    required: bool = False,
    max_length: int = 500,
) -> Optional[str]:
    raw = params.get(name)
    if raw is None:
        if required:
            raise ConsoleAPIError(400, "INVALID_PARAM", f"{name} is required")
        return None
    if not isinstance(raw, str):
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{name} must be a string")
    normalized = raw.strip()
    if not normalized:
        if required:
            raise ConsoleAPIError(400, "INVALID_PARAM", f"{name} is required")
        return None
    if len(normalized) > max_length:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{name} is too long (max {max_length})")
    return normalized


def _parse_ops_job_uuid_list_param(
    params: dict,
    *,
    name: str,
    max_items: int = 100,
) -> Optional[list[UUID]]:
    raw = params.get(name)
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{name} must be an array")
    if len(raw) > max_items:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{name} supports up to {max_items} items")
    parsed: list[UUID] = []
    seen: set[UUID] = set()
    for index, value in enumerate(raw):
        parsed_value = _parse_uuid_param(f"{name}[{index}]", str(value))
        if parsed_value in seen:
            continue
        seen.add(parsed_value)
        parsed.append(parsed_value)
    return parsed


def _resolve_branch_scope(context: ConsoleAuthContext) -> Optional[list[UUID]]:
    if not context.branch_restricted:
        return None
    branch_ids = [branch.id for branch in context.branches]
    return branch_ids


def _query_scoped_outbox_message_rows(
    db: Session,
    *,
    context: ConsoleAuthContext,
    status: str,
) -> list[OutboxMessage]:
    query = db.query(OutboxMessage).filter(
        OutboxMessage.client_id == context.client.id,
        OutboxMessage.status == status,
    )
    allowed_branch_ids = _resolve_branch_scope(context)
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            return []
        query = query.filter(OutboxMessage.branch_id.in_(allowed_branch_ids))
    return query.all()


def _build_outbox_dry_run_summary(
    db: Session,
    *,
    context: ConsoleAuthContext,
    limit: int,
    idle_seconds: int,
    max_wait_seconds: int,
    include_without_conversation: bool,
    archive_preview: Optional[dict] = None,
) -> dict:
    pending_rows = _query_scoped_outbox_message_rows(db, context=context, status="PENDING")
    pending = len(pending_rows)
    processing = len(_query_scoped_outbox_message_rows(db, context=context, status="PROCESSING"))
    failed = len(_query_scoped_outbox_message_rows(db, context=context, status="FAILED"))
    pending_with_conversation = sum(1 for row in pending_rows if row.conversation_id is not None)
    pending_without_conversation = pending - pending_with_conversation
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    pending_older_than_7d = sum(
        1
        for row in pending_rows
        if row.created_at and row.created_at <= stale_cutoff
    )
    return {
        "mode": "dry_run",
        "scope": {
            "client_id": str(context.client.id),
            "branch_ids": [str(branch_id) for branch_id in (_resolve_branch_scope(context) or [])],
        },
        "config": {
            "limit": limit,
            "idle_seconds": idle_seconds,
            "max_wait_seconds": max_wait_seconds,
            "include_without_conversation": include_without_conversation,
        },
        "counts": {
            "pending": pending,
            "processing": processing,
            "failed": failed,
            "pending_with_conversation": pending_with_conversation,
            "pending_without_conversation": pending_without_conversation,
            "pending_older_than_7d": pending_older_than_7d,
        },
        "archive_preview": archive_preview,
    }


def _build_outbox_archive_preview(
    db: Session,
    *,
    context: ConsoleAuthContext,
    older_than_hours: int,
    limit: int,
    only_without_conversation: bool,
) -> dict:
    if older_than_hours <= 0:
        return {"enabled": False}

    cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
    query = db.query(OutboxMessage).filter(
        OutboxMessage.client_id == context.client.id,
        OutboxMessage.status == "PENDING",
        OutboxMessage.created_at <= cutoff,
    )
    if only_without_conversation:
        query = query.filter(OutboxMessage.conversation_id.is_(None))

    allowed_branch_ids = _resolve_branch_scope(context)
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            return {
                "enabled": True,
                "candidates_total": 0,
                "candidates_capped": 0,
                "older_than_hours": older_than_hours,
                "limit": limit,
                "only_without_conversation": only_without_conversation,
            }
        query = query.filter(OutboxMessage.branch_id.in_(allowed_branch_ids))

    total = query.count()
    oldest_row = query.order_by(OutboxMessage.created_at.asc(), OutboxMessage.id.asc()).first()
    newest_row = query.order_by(OutboxMessage.created_at.desc(), OutboxMessage.id.desc()).first()
    return {
        "enabled": True,
        "candidates_total": total,
        "candidates_capped": min(total, limit),
        "older_than_hours": older_than_hours,
        "limit": limit,
        "only_without_conversation": only_without_conversation,
        "oldest_created_at": oldest_row.created_at.isoformat() if oldest_row and oldest_row.created_at else None,
        "newest_created_at": newest_row.created_at.isoformat() if newest_row and newest_row.created_at else None,
    }


def _claim_scoped_outbox_rows(
    db: Session,
    *,
    context: ConsoleAuthContext,
    limit: int,
    idle_seconds: int,
    max_wait_seconds: int,
    include_without_conversation: bool = True,
) -> list[dict]:
    now = datetime.now(timezone.utc)
    idle_cutoff = now - timedelta(seconds=idle_seconds)
    max_wait_cutoff = now - timedelta(seconds=max_wait_seconds)

    query = (
        db.query(
            OutboxMessage.conversation_id.label("conversation_id"),
            func.max(OutboxMessage.created_at).label("last_created_at"),
            func.min(OutboxMessage.created_at).label("first_created_at"),
        )
        .filter(
            OutboxMessage.client_id == context.client.id,
            OutboxMessage.status == "PENDING",
            OutboxMessage.conversation_id.isnot(None),
            or_(OutboxMessage.next_attempt_at.is_(None), OutboxMessage.next_attempt_at <= now),
        )
        .group_by(OutboxMessage.conversation_id)
        .order_by(func.max(OutboxMessage.created_at).asc())
        .limit(limit)
    )
    allowed_branch_ids = _resolve_branch_scope(context)
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            return []
        query = query.filter(OutboxMessage.branch_id.in_(allowed_branch_ids))

    batches = query.all()
    conversation_ids: list[UUID] = []
    for batch in batches:
        if not batch.conversation_id:
            continue
        is_idle = bool(batch.last_created_at and batch.last_created_at <= idle_cutoff)
        is_max_wait = bool(max_wait_seconds > 0 and batch.first_created_at and batch.first_created_at <= max_wait_cutoff)
        if is_idle or is_max_wait:
            conversation_ids.append(batch.conversation_id)

    single_message_ids: list[UUID] = []
    remaining_slots = max(0, limit - len(conversation_ids))
    if include_without_conversation and remaining_slots > 0:
        age_filters = [OutboxMessage.created_at <= idle_cutoff]
        if max_wait_seconds > 0:
            age_filters.append(OutboxMessage.created_at <= max_wait_cutoff)
        singles_query = (
            db.query(OutboxMessage.id)
            .filter(
                OutboxMessage.client_id == context.client.id,
                OutboxMessage.status == "PENDING",
                OutboxMessage.conversation_id.is_(None),
                or_(OutboxMessage.next_attempt_at.is_(None), OutboxMessage.next_attempt_at <= now),
                or_(*age_filters),
            )
            .order_by(OutboxMessage.created_at.asc(), OutboxMessage.id.asc())
            .limit(remaining_slots)
        )
        if allowed_branch_ids is not None:
            singles_query = singles_query.filter(OutboxMessage.branch_id.in_(allowed_branch_ids))
        single_message_ids = [row.id for row in singles_query.all()]

    if not conversation_ids and not single_message_ids:
        return []

    filters = []
    if conversation_ids:
        filters.append(OutboxMessage.conversation_id.in_(conversation_ids))
    if single_message_ids:
        filters.append(OutboxMessage.id.in_(single_message_ids))

    rows_query = (
        db.query(OutboxMessage)
        .filter(
            OutboxMessage.client_id == context.client.id,
            OutboxMessage.status == "PENDING",
            or_(*filters),
        )
        .order_by(OutboxMessage.created_at.asc(), OutboxMessage.id.asc())
    )
    if allowed_branch_ids is not None:
        rows_query = rows_query.filter(OutboxMessage.branch_id.in_(allowed_branch_ids))
    rows = rows_query.all()

    for row in rows:
        row.status = "PROCESSING"
        row.attempts = int(row.attempts or 0) + 1
        row.updated_at = now
    db.commit()

    return [
        {
            "id": row.id,
            "client_id": row.client_id,
            "branch_id": row.branch_id,
            "conversation_id": row.conversation_id,
            "inbound_message_id": row.inbound_message_id,
            "payload_json": row.payload_json,
            "attempts": row.attempts,
            "created_at": row.created_at,
        }
        for row in rows
    ]


def _build_metrics_snapshot_dry_run(
    *,
    context: ConsoleAuthContext,
    metric_date: dt_date,
    days: int,
) -> dict:
    return {
        "mode": "dry_run",
        "scope": {
            "client_id": str(context.client.id),
        },
        "metric_date": metric_date.isoformat(),
        "days": days,
    }


async def _run_outbox_process_job(
    db: Session,
    *,
    context: ConsoleAuthContext,
    mode: str,
    params: dict,
) -> dict:
    limit = _parse_ops_job_int_param(
        params,
        name="limit",
        default=int(os.environ.get("OUTBOX_PROCESS_LIMIT", "10")),
        min_value=1,
        max_value=200,
    )
    idle_seconds = _parse_ops_job_int_param(
        params,
        name="idle_seconds",
        default=int(float(os.environ.get("OUTBOX_COALESCE_SECONDS", "8"))),
        min_value=0,
        max_value=3600,
    )
    max_wait_seconds = _parse_ops_job_int_param(
        params,
        name="max_wait_seconds",
        default=int(float(os.environ.get("OUTBOX_MAX_WAIT_SECONDS", "10"))),
        min_value=0,
        max_value=3600,
    )
    include_without_conversation = _parse_ops_job_bool_param(
        params,
        name="include_without_conversation",
        default=True,
    )
    archive_pending_older_than_hours = _parse_ops_job_int_param(
        params,
        name="archive_pending_older_than_hours",
        default=0,
        min_value=0,
        max_value=24 * 365,
    )
    archive_pending_limit = _parse_ops_job_int_param(
        params,
        name="archive_pending_limit",
        default=limit,
        min_value=1,
        max_value=1000,
    )
    archive_pending_without_conversation_only = _parse_ops_job_bool_param(
        params,
        name="archive_pending_without_conversation_only",
        default=True,
    )
    max_attempts = int(os.environ.get("OUTBOX_MAX_ATTEMPTS", "5"))
    retry_backoff_seconds = float(os.environ.get("OUTBOX_RETRY_BACKOFF_SECONDS", "2"))

    if mode == "dry_run":
        archive_preview = _build_outbox_archive_preview(
            db,
            context=context,
            older_than_hours=archive_pending_older_than_hours,
            limit=archive_pending_limit,
            only_without_conversation=archive_pending_without_conversation_only,
        )
        return _build_outbox_dry_run_summary(
            db,
            context=context,
            limit=limit,
            idle_seconds=idle_seconds,
            max_wait_seconds=max_wait_seconds,
            include_without_conversation=include_without_conversation,
            archive_preview=archive_preview,
        )

    archive_result = None
    if archive_pending_older_than_hours > 0:
        archive_reason = f"archived_pending:older_than_{archive_pending_older_than_hours}h"
        archive_result = archive_pending_outbox(
            db,
            client_id=context.client.id,
            older_than_seconds=archive_pending_older_than_hours * 3600,
            limit=archive_pending_limit,
            reason=archive_reason,
            branch_ids=_resolve_branch_scope(context),
            only_without_conversation=archive_pending_without_conversation_only,
        )

    claimed_rows = _claim_scoped_outbox_rows(
        db,
        context=context,
        limit=limit,
        idle_seconds=idle_seconds,
        max_wait_seconds=max_wait_seconds,
        include_without_conversation=include_without_conversation,
    )
    if not claimed_rows:
        response = {
            "mode": "execute",
            "scope": {"client_id": str(context.client.id)},
            "processed": 0,
            "results": {"processed": 0, "failed": 0},
        }
        if archive_result is not None:
            response["archive"] = archive_result
        return response

    from app.routers.webhook import _process_outbox_rows

    results = await _process_outbox_rows(
        db,
        claimed_rows,
        max_attempts=max_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
    )
    response = {
        "mode": "execute",
        "scope": {"client_id": str(context.client.id)},
        "processed": len(claimed_rows),
        "results": results,
    }
    if archive_result is not None:
        response["archive"] = archive_result
    return response


async def _run_heal_job(
    db: Session,
    *,
    context: ConsoleAuthContext,
    mode: str,
    params: dict,
) -> dict:
    _ = params
    if mode == "dry_run":
        broken_no_topic = (
            db.query(Conversation)
            .filter(
                Conversation.client_id == context.client.id,
                Conversation.state.in_(["manager_active", "pending"]),
                Conversation.telegram_topic_id.is_(None),
            )
            .count()
        )
        broken_no_handover = (
            db.query(Conversation)
            .filter(
                Conversation.client_id == context.client.id,
                Conversation.state.in_(["manager_active", "pending"]),
            )
            .count()
        )
        return {
            "mode": "dry_run",
            "scope": {"client_id": str(context.client.id)},
            "checks": {
                "manager_or_pending_without_topic": broken_no_topic,
                "manager_or_pending_total": broken_no_handover,
            },
            "note": "execute mode for heal is disabled in slice 1",
        }
    raise ConsoleAPIError(400, "INVALID_PARAM", "heal execute is not available in this slice")


async def _run_metrics_snapshot_job(
    db: Session,
    *,
    context: ConsoleAuthContext,
    mode: str,
    params: dict,
) -> dict:
    metric_date_raw = params.get("metric_date")
    metric_date = (
        _parse_date_param("metric_date", str(metric_date_raw))
        if metric_date_raw is not None
        else get_metrics_daily_default_date()
    )
    max_days = get_metrics_daily_backfill_max_days()
    days = _parse_ops_job_int_param(
        params,
        name="days",
        default=1,
        min_value=1,
        max_value=max_days,
    )

    if mode == "dry_run":
        return _build_metrics_snapshot_dry_run(
            context=context,
            metric_date=metric_date,
            days=days,
        )

    results = []
    for offset in range(days - 1, -1, -1):
        day = metric_date - timedelta(days=offset)
        results.append(
            run_metrics_daily_snapshot(
                db,
                metric_date=day,
                client_ids=[context.client.id],
                status_allowlist=None,
            )
        )
    return {
        "mode": "execute",
        "scope": {"client_id": str(context.client.id)},
        "metric_date": metric_date.isoformat(),
        "days": days,
        "results": results,
    }


async def _run_incident_state_job(
    db: Session,
    *,
    context: ConsoleAuthContext,
    mode: str,
    params: dict,
) -> dict:
    incident_id = _parse_ops_job_text_param(params, name="incident_id", required=True, max_length=160)
    state_raw = _parse_ops_job_text_param(params, name="incident_state", required=True, max_length=32)
    incident_state = _coerce_incident_state(state_raw)
    if not incident_state:
        raise ConsoleAPIError(400, "INVALID_PARAM", "incident_state must be open, in_progress, or resolved")

    owner = _parse_ops_job_text_param(params, name="owner", required=False, max_length=160)
    note = _parse_ops_job_text_param(params, name="note", required=False, max_length=2000)
    evidence_confirmed = _parse_ops_job_bool_param(
        params,
        name="evidence_confirmed",
        default=False,
    )
    evidence_summary = _parse_ops_job_text_param(
        params,
        name="evidence_summary",
        required=False,
        max_length=2000,
    )
    reason_code = _parse_ops_job_text_param(params, name="reason_code", required=False, max_length=120)
    due_at_raw = _parse_ops_job_text_param(params, name="due_at", required=False, max_length=80)
    due_at = _parse_datetime_param("due_at", due_at_raw) if due_at_raw else None

    branch_id_raw = _parse_ops_job_text_param(params, name="branch_id", required=False, max_length=64)
    branch_id = _parse_uuid_param("branch_id", branch_id_raw) if branch_id_raw else context.effective_branch_id
    allowed_branch_ids = _resolve_branch_scope(context)
    if allowed_branch_ids is not None and branch_id is not None and branch_id not in set(allowed_branch_ids):
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Branch scope denied")

    if mode == "execute" and incident_state == "resolved":
        if not evidence_confirmed or not evidence_summary:
            raise ConsoleAPIError(
                409,
                "INCIDENT_EVIDENCE_REQUIRED",
                "Use evidence_confirmed=true and evidence_summary before setting incident_state=resolved",
            )

    payload = {
        "mode": mode,
        "scope": {
            "client_id": str(context.client.id),
            "branch_id": str(branch_id) if branch_id else None,
        },
        "incident_id": incident_id,
        "incident_state": incident_state,
        "owner": owner,
        "due_at": due_at.isoformat() if due_at else None,
        "note": note,
        "evidence_confirmed": evidence_confirmed,
        "evidence_summary": evidence_summary,
        "reason_code": reason_code,
    }
    if mode == "dry_run":
        return payload

    alert_metadata = {
        "incident_id": incident_id,
        "incident_state": incident_state,
        "owner": owner,
        "due_at": due_at.isoformat() if due_at else None,
        "note": note,
        "evidence_confirmed": evidence_confirmed,
        "evidence_summary": evidence_summary,
        "reason_code": reason_code,
        "source": "console_ops_job",
        "actor_agent_id": str(context.agent.id),
    }
    db.add(
        AlertEvent(
            client_id=context.client.id,
            branch_id=branch_id,
            conversation_id=None,
            message_id=None,
            alert_type=_INCIDENT_STATE_ALERT_TYPE,
            alert_metadata={key: value for key, value in alert_metadata.items() if value is not None},
        )
    )
    return payload


async def _run_integration_reconcile_job(
    db: Session,
    *,
    context: ConsoleAuthContext,
    mode: str,
    params: dict,
) -> dict:
    branch_ids = _parse_ops_job_uuid_list_param(params, name="branch_ids", max_items=100)
    limit = _parse_ops_job_int_param(params, name="limit", default=25, min_value=1, max_value=200)

    allowed_branch_ids = _resolve_branch_scope(context)
    if branch_ids and allowed_branch_ids is not None:
        disallowed = [branch_id for branch_id in branch_ids if branch_id not in set(allowed_branch_ids)]
        if disallowed:
            raise ConsoleAPIError(403, "ACCESS_DENIED", "Branch scope denied")

    selected_branch_ids = branch_ids
    if selected_branch_ids is None:
        branch_query = (
            db.query(Branch.id)
            .filter(
                Branch.client_id == context.client.id,
                Branch.is_active.is_(True),
            )
            .order_by(Branch.created_at.asc(), Branch.id.asc())
            .limit(limit)
        )
        if allowed_branch_ids is not None:
            if not allowed_branch_ids:
                selected_branch_ids = []
            else:
                branch_query = branch_query.filter(Branch.id.in_(allowed_branch_ids))
        if selected_branch_ids is None:
            selected_branch_ids = [row.id for row in branch_query.all()]

    result = run_integration_watchdog_scoped(
        db,
        client_id=context.client.id,
        branch_ids=selected_branch_ids,
        dry_run=(mode == "dry_run"),
    )
    result["scope"] = {
        "client_id": str(context.client.id),
        "branch_ids": [str(branch_id) for branch_id in selected_branch_ids or []],
    }
    return result


def _build_ops_job_artifact(
    *,
    job: ConsoleOpsJob,
    generated_at: datetime,
) -> dict[str, str]:
    return {
        "artifact_id": f"{job.job_type}:{job.id}",
        "artifact_type": f"{job.job_type}_report",
        "job_id": str(job.id),
        "job_type": job.job_type,
        "mode": job.mode,
        "generated_at": generated_at.isoformat(),
        "api_path": f"/console/v1/ops/jobs/{job.id}",
    }


def _attach_ops_job_artifact(
    *,
    job: ConsoleOpsJob,
    payload: object,
    generated_at: datetime,
) -> dict:
    wrapped = _jsonable_payload(payload)
    wrapped["artifact"] = _build_ops_job_artifact(job=job, generated_at=generated_at)
    return wrapped


@router.get(
    "/me",
    response_model=ConsoleMeResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def get_me(request: Request, db: Session = Depends(get_db)) -> ConsoleMeResponse:
    context = get_console_context(request, db, require_selection=False)
    if not context.agent or not context.client:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Console access missing")
    return _build_me_response(context)


@router.get(
    "/agents",
    response_model=ConsoleAgentListResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_agents(request: Request, db: Session = Depends(get_db)) -> ConsoleAgentListResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "team",
        "read",
        message="Only owner/admin can view agents",
    )

    agents = (
        db.query(Agent)
        .filter(Agent.client_id == context.client.id)
        .order_by(Agent.created_at.asc())
        .all()
    )
    agent_ids = [agent.id for agent in agents]
    identities = []
    if agent_ids:
        identities = (
            db.query(AgentIdentity)
            .filter(
                AgentIdentity.agent_id.in_(agent_ids),
                AgentIdentity.channel == "telegram",
            )
            .all()
        )

    identities_by_agent: dict[UUID, list[ConsoleAgentIdentity]] = {agent.id: [] for agent in agents}
    for identity in identities:
        identities_by_agent.setdefault(identity.agent_id, []).append(
            ConsoleAgentIdentity(
                channel="telegram",
                external_id=identity.external_id,
                username=identity.username,
                linked_at=identity.created_at.isoformat() if identity.created_at else None,
            )
        )

    return ConsoleAgentListResponse(
        items=[
            ConsoleAgentWithIdentities(
                id=agent.id,
                name=agent.name,
                role=agent.role,
                client_id=agent.client_id,
                branch_id=agent.branch_id,
                is_active=agent.is_active,
                identities=identities_by_agent.get(agent.id, []),
            )
            for agent in agents
        ]
    )


@router.post(
    "/agents/{agent_id}/telegram/link",
    response_model=ConsoleTelegramLinkResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def link_agent_telegram(
    agent_id: UUID, request: Request, db: Session = Depends(get_db)
) -> ConsoleTelegramLinkResponse:
    context = get_console_context(request, db)
    if context.role not in ("platform_admin", "owner", "admin") and context.agent.id != agent_id:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Only platform admin/owner/admin can link other agents")

    agent = (
        db.query(Agent)
        .filter(Agent.id == agent_id, Agent.client_id == context.client.id)
        .first()
    )
    if not agent:
        raise ConsoleAPIError(404, "NOT_FOUND", "Agent not found")

    settings = db.query(ClientSettings).filter(ClientSettings.client_id == context.client.id).first()
    if not settings or not settings.telegram_bot_token:
        raise ConsoleAPIError(400, "TELEGRAM_CONFIG_MISSING", "Telegram bot token is not configured")

    token, record = create_agent_link_token(
        db,
        agent=agent,
        created_by_id=context.agent.id,
    )

    bot_username = None
    telegram = TelegramService(settings.telegram_bot_token)
    bot_info = telegram._make_request("getMe")
    if bot_info.get("ok"):
        bot_username = bot_info.get("result", {}).get("username")

    deep_link = build_telegram_deep_link(bot_username, token)

    record_audit_event(
        db,
        actor=context.agent,
        event_type="telegram_link_created",
        entity_type="agent",
        entity_id=agent.id,
        payload={
            "expires_at": record.expires_at.isoformat(),
            "token_hint": token[:4],
        },
        branch_id=agent.branch_id,
    )

    db.commit()

    return ConsoleTelegramLinkResponse(
        token=token,
        deep_link=deep_link,
        bot_username=bot_username,
        expires_at=record.expires_at.isoformat(),
    )


@router.get(
    "/cases",
    response_model=ConsoleCaseListResponse,
    responses={401: {"model": ConsoleErrorResponse}},
)
async def list_cases(
    request: Request,
    status: Optional[str] = None,
    q: Optional[str] = None,
    branch_id: Optional[str] = None,
    assigned_to_me: bool = False,
    phone: Optional[str] = None,
    has_delivery_error: bool = False,
    has_pending_outbox: bool = False,
    has_human_lock: bool = False,
    last_activity_since: Optional[str] = None,
    sort_by: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> ConsoleCaseListResponse:
    context = get_console_context(request, db)
    require_console_permission(context, "inbox", "read")
    _reject_unknown_query_params(
        request,
        {
            "status",
            "q",
            "branch_id",
            "assigned_to_me",
            "phone",
            "has_delivery_error",
            "has_pending_outbox",
            "has_human_lock",
            "last_activity_since",
            "sort_by",
            "date_from",
            "date_to",
            "cursor",
            "limit",
        },
    )
    _validate_limit(limit)
    assigned_to_me = _parse_bool_param(
        "assigned_to_me",
        request.query_params.get("assigned_to_me"),
        default=assigned_to_me,
    )
    has_delivery_error = _parse_bool_param(
        "has_delivery_error",
        request.query_params.get("has_delivery_error"),
        default=has_delivery_error,
    )
    has_pending_outbox = _parse_bool_param(
        "has_pending_outbox",
        request.query_params.get("has_pending_outbox"),
        default=has_pending_outbox,
    )
    has_human_lock = _parse_bool_param(
        "has_human_lock",
        request.query_params.get("has_human_lock"),
        default=has_human_lock,
    )
    last_activity_since_dt = _parse_datetime_param("last_activity_since", last_activity_since)
    sort_by_value = _parse_sort_param("sort_by", request.query_params.get("sort_by"))

    # Base query with common filters used by both count and item fetch.
    base_query = (
        db.query(Handover, Conversation, User)
        .join(Conversation, Handover.conversation_id == Conversation.id)
        .outerjoin(User, and_(User.id == Conversation.user_id, User.client_id == context.client.id))
        .filter(
            Handover.client_id == context.client.id,
            Conversation.client_id == context.client.id,
        )
    )

    # Branch filter (RBAC + Request)
    allowed_branch_ids = {b.id for b in context.branches}
    is_privileged = _has_context_privileged_branch_access(context)

    if not is_privileged:
        if not allowed_branch_ids:
            return ConsoleCaseListResponse(items=[], cursor=None, has_more=False, total=0)
        base_query = base_query.filter(Conversation.branch_id.in_(allowed_branch_ids))

    if branch_id is not None:
        bid = _parse_uuid_param("branch_id", branch_id)
        if not is_privileged and bid not in allowed_branch_ids:
            raise ConsoleAPIError(403, "ACCESS_DENIED", "Access to this branch denied")
        base_query = base_query.filter(Conversation.branch_id == bid)
    elif context.branch_restricted:
        base_query = base_query.filter(Conversation.branch_id.in_(allowed_branch_ids))

    # Status filter
    status_filters = _parse_case_status_param("status", request.query_params.get("status") or status)
    if status_filters:
        base_query = base_query.filter(Handover.status.in_(status_filters))

    # Date range filter
    if date_from is not None:
        from_date = _parse_date_param("date_from", date_from)
        start_of_day = datetime.combine(from_date, time.min).replace(tzinfo=timezone.utc)
        base_query = base_query.filter(Handover.created_at >= start_of_day)

    if date_to is not None:
        to_date = _parse_date_param("date_to", date_to)
        end_of_day = datetime.combine(to_date, time.max).replace(tzinfo=timezone.utc)
        base_query = base_query.filter(Handover.created_at <= end_of_day)

    # Assigned to me
    if assigned_to_me:
        base_query = base_query.filter(
            or_(
                Handover.assigned_to == str(context.agent.id),
                and_(
                    Handover.assigned_to.is_(None),
                    Handover.assigned_to_name == context.agent.name,
                ),
            )
        )

    # Search filters
    query_value = _normalize_search_query("q", q)
    if query_value:
        conditions = []
        maybe_uuid = _looks_like_uuid(query_value)
        if maybe_uuid:
            conditions.append(Handover.id == maybe_uuid)
        digits = _normalize_phone_digits(query_value)
        if digits:
            conditions.append(func.regexp_replace(User.phone, r"\D", "", "g").ilike(f"%{digits}%"))
        conditions.append(User.name.ilike(f"%{query_value}%"))
        if conditions:
            base_query = base_query.filter(or_(*conditions))

    if phone:
        digits = _normalize_phone_digits(phone)
        if digits:
            base_query = base_query.filter(
                func.regexp_replace(User.phone, r"\D", "", "g").ilike(f"%{digits}%")
            )

    count_query = base_query
    if has_delivery_error:
        count_query = count_query.filter(
            db.query(OutboxMessage.id)
            .filter(
                OutboxMessage.client_id == context.client.id,
                OutboxMessage.conversation_id == Conversation.id,
                OutboxMessage.status == "FAILED",
            )
            .exists()
        )
    if has_pending_outbox:
        count_query = count_query.filter(
            db.query(OutboxMessage.id)
            .filter(
                OutboxMessage.client_id == context.client.id,
                OutboxMessage.conversation_id == Conversation.id,
                OutboxMessage.status.in_(["PENDING", "PROCESSING"]),
            )
            .exists()
        )
    if has_human_lock:
        now_utc = datetime.now(timezone.utc)
        count_query = count_query.filter(
            db.query(ConversationHumanLock.id)
            .filter(
                ConversationHumanLock.client_id == context.client.id,
                ConversationHumanLock.conversation_id == Conversation.id,
                ConversationHumanLock.lock_scope == HUMAN_LOCK_SCOPE_CONVERSATION,
                ConversationHumanLock.active.is_(True),
                ConversationHumanLock.lock_until > now_utc,
            )
            .exists()
        )
    if last_activity_since_dt:
        count_query = count_query.filter(
            db.query(Message.id)
            .filter(
                Message.client_id == context.client.id,
                Message.conversation_id == Conversation.id,
                Message.created_at >= last_activity_since_dt,
            )
            .exists()
        )
    # Full count for queue visibility (before cursor pagination).
    total_count = count_query.order_by(None).count()
    now_utc = datetime.now(timezone.utc)

    latest_message_subq = (
        db.query(
            Message.conversation_id.label("conversation_id"),
            Message.created_at.label("created_at"),
            Message.role.label("role"),
            Message.content.label("content"),
            Message.message_metadata.label("metadata"),
            func.row_number()
            .over(
                partition_by=Message.conversation_id,
                order_by=Message.created_at.desc(),
            )
            .label("rn"),
        )
        .filter(Message.client_id == context.client.id)
        .subquery()
    )

    last_inbound_subq = (
        db.query(
            Message.conversation_id.label("conversation_id"),
            func.max(Message.created_at).label("last_inbound_at"),
        )
        .filter(
            Message.client_id == context.client.id,
            Message.role == "user",
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    last_outbound_subq = (
        db.query(
            Message.conversation_id.label("conversation_id"),
            func.max(Message.created_at).label("last_outbound_at"),
        )
        .filter(
            Message.client_id == context.client.id,
            Message.role.in_(["assistant", "manager", "system"]),
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    outbox_subq = (
        db.query(
            OutboxMessage.conversation_id.label("conversation_id"),
            func.sum(
                case(
                    (OutboxMessage.status.in_(["PENDING", "PROCESSING"]), 1),
                    else_=0,
                )
            ).label("pending_count"),
            func.sum(
                case(
                    (OutboxMessage.status == "FAILED", 1),
                    else_=0,
                )
            ).label("failed_count"),
        )
        .filter(OutboxMessage.client_id == context.client.id)
        .group_by(OutboxMessage.conversation_id)
        .subquery()
    )

    human_lock_subq = (
        db.query(
            ConversationHumanLock.conversation_id.label("conversation_id"),
            ConversationHumanLock.lock_until.label("lock_until"),
            ConversationHumanLock.source.label("source"),
            ConversationHumanLock.reason.label("reason"),
            ConversationHumanLock.locked_by_name.label("locked_by_name"),
            func.row_number()
            .over(
                partition_by=ConversationHumanLock.conversation_id,
                order_by=ConversationHumanLock.lock_until.desc(),
            )
            .label("rn"),
        )
        .filter(
            ConversationHumanLock.client_id == context.client.id,
            ConversationHumanLock.lock_scope == HUMAN_LOCK_SCOPE_CONVERSATION,
            ConversationHumanLock.active.is_(True),
            ConversationHumanLock.lock_until > now_utc,
            ConversationHumanLock.conversation_id.isnot(None),
        )
        .subquery()
    )

    query = base_query.outerjoin(
        latest_message_subq,
        and_(
            latest_message_subq.c.conversation_id == Conversation.id,
            latest_message_subq.c.rn == 1,
        ),
    )
    query = query.outerjoin(last_inbound_subq, last_inbound_subq.c.conversation_id == Conversation.id)
    query = query.outerjoin(last_outbound_subq, last_outbound_subq.c.conversation_id == Conversation.id)
    query = query.outerjoin(outbox_subq, outbox_subq.c.conversation_id == Conversation.id)
    query = query.outerjoin(
        human_lock_subq,
        and_(
            human_lock_subq.c.conversation_id == Conversation.id,
            human_lock_subq.c.rn == 1,
        ),
    )

    if has_delivery_error:
        query = query.filter(outbox_subq.c.failed_count > 0)

    if has_pending_outbox:
        query = query.filter(outbox_subq.c.pending_count > 0)

    if last_activity_since_dt:
        query = query.filter(latest_message_subq.c.created_at >= last_activity_since_dt)
    if has_human_lock:
        query = query.filter(human_lock_subq.c.lock_until.is_not(None))

    # Sorting & Pagination (Cursor based on selected sort)
    sort_expr = Handover.created_at
    sort_desc = True
    if sort_by_value == "last_activity":
        sort_expr = func.coalesce(latest_message_subq.c.created_at, Handover.created_at)
    elif sort_by_value == "sla":
        sort_expr = Handover.created_at
        sort_desc = False

    cursor_date = _parse_cursor_param(cursor)
    if sort_desc:
        query = query.order_by(sort_expr.desc(), Handover.created_at.desc())
        if cursor_date is not None:
            query = query.filter(sort_expr < cursor_date)
    else:
        query = query.order_by(sort_expr.asc(), Handover.created_at.asc())
        if cursor_date is not None:
            query = query.filter(sort_expr > cursor_date)

    # Select handover + conversation + customer
    items = query.with_entities(
        Handover,
        Conversation,
        User,
        latest_message_subq.c.created_at.label("last_activity_at"),
        latest_message_subq.c.role.label("last_activity_role"),
        latest_message_subq.c.content.label("last_message_preview"),
        latest_message_subq.c.metadata.label("last_message_metadata"),
        last_inbound_subq.c.last_inbound_at,
        last_outbound_subq.c.last_outbound_at,
        outbox_subq.c.pending_count,
        outbox_subq.c.failed_count,
        human_lock_subq.c.lock_until,
        human_lock_subq.c.source,
        human_lock_subq.c.reason,
        human_lock_subq.c.locked_by_name,
    ).limit(limit + 1).all()
    
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]
        (
            last_handover,
            _last_conversation,
            _last_user,
            last_activity_at,
            _last_activity_role,
            _last_message_preview,
            _last_message_metadata,
            _last_inbound_at,
            _last_outbound_at,
            _pending_count,
            _failed_count,
            _lock_until,
            _lock_source,
            _lock_reason,
            _lock_by_name,
        ) = items[-1]
        cursor_value = _resolve_case_sort_cursor(
            sort_by=sort_by_value,
            last_activity_at=last_activity_at,
            created_at=last_handover.created_at,
        )
        next_cursor = cursor_value.isoformat()
    else:
        next_cursor = None

    return ConsoleCaseListResponse(
        items=[
            ConsoleCase(
                id=handover.id,
                conversation_id=handover.conversation_id,
                status=handover.status,
                trigger_type=handover.trigger_type,
                trigger_value=handover.trigger_value,
                context_summary=handover.context_summary,
                user_message=handover.user_message,
                assigned_to_name=handover.assigned_to_name,
                branch_id=conversation.branch_id,
                channel=handover.channel,
                created_at=handover.created_at.isoformat(),
                **_format_case_metrics(handover),
                sla_status=_calculate_sla_status(handover.created_at),
                customer_name=user.name if user else None,
                customer_phone=user.phone if user else None,
                customer_remote_jid=user.remote_jid if user else None,
                last_inbound_at=last_inbound_at.isoformat() if last_inbound_at else None,
                last_outbound_at=last_outbound_at.isoformat() if last_outbound_at else None,
                last_activity_at=last_activity_at.isoformat() if last_activity_at else None,
                last_activity_channel=_resolve_last_activity_channel(
                    role=last_activity_role,
                    metadata=last_message_metadata,
                    conversation_channel=conversation.channel,
                ),
                last_message_preview=last_message_preview,
                needs_reply=bool(
                    last_inbound_at and (not last_outbound_at or last_inbound_at > last_outbound_at)
                ),
                has_delivery_error=bool(failed_count and failed_count > 0),
                has_pending_outbox=bool(pending_count and pending_count > 0),
                human_lock_active=bool(lock_until),
                human_lock_until=lock_until.isoformat() if lock_until else None,
                human_lock_remaining_seconds=(
                    max(0, int((lock_until - now_utc).total_seconds())) if lock_until else None
                ),
                human_lock_source=lock_source,
                human_lock_reason=lock_reason,
                human_lock_by=lock_by_name,
            )
            for (
                handover,
                conversation,
                user,
                last_activity_at,
                last_activity_role,
                last_message_preview,
                last_message_metadata,
                last_inbound_at,
                last_outbound_at,
                pending_count,
                failed_count,
                lock_until,
                lock_source,
                lock_reason,
                lock_by_name,
            ) in items
        ],
        cursor=next_cursor,
        has_more=has_more,
        total=total_count,
    )


@router.post(
    "/cases/{case_id}/take",
    response_model=ConsoleCaseActionResponse,
    responses={409: {"model": ConsoleErrorResponse}},
)
async def take_case(
    case_id: UUID, request: Request, db: Session = Depends(get_db)
) -> ConsoleCaseActionResponse:
    context = get_console_context(request, db)
    require_console_permission(context, "inbox", "write")
    idempotency_key = _get_idempotency_key(request)
    idempotency = start_idempotency(
        db,
        client_id=context.client.id,
        agent_id=context.agent.id,
        idempotency_key=idempotency_key,
        scope="console.case.take",
        payload={"case_id": str(case_id)},
    )
    if idempotency and idempotency.replay:
        return JSONResponse(
            status_code=idempotency.response_status,
            content=idempotency.response_body,
        )
    
    # 1. Lock row for update
    case = (
        db.query(Handover)
        .filter(Handover.id == case_id, Handover.client_id == context.client.id)
        .with_for_update()
        .first()
    )

    if not case:
        if idempotency and idempotency.record:
            release_idempotency(db, record=idempotency.record)
        raise ConsoleAPIError(404, "NOT_FOUND", "Case not found")

    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == case.conversation_id)
        .with_for_update()
        .first()
    )
    if not conversation:
        if idempotency and idempotency.record:
            release_idempotency(db, record=idempotency.record)
        raise ConsoleAPIError(404, "NOT_FOUND", "Conversation not found")

    branch_id = conversation.branch_id
    manager_name = context.agent.name or "Менеджер"

    if case.status == "resolved":
        if idempotency and idempotency.record:
            release_idempotency(db, record=idempotency.record)
        raise ConsoleAPIError(409, "CASE_ALREADY_RESOLVED", "Case already resolved")

    if case.status == "active":
        if case.assigned_to_name and case.assigned_to_name != context.agent.name:
            if idempotency and idempotency.record:
                release_idempotency(db, record=idempotency.record)
            raise ConsoleAPIError(
                409,
                "CASE_ALREADY_TAKEN",
                "Case already taken",
                details={"current_assignee": case.assigned_to_name},
            )

        response = ConsoleCaseActionResponse(
            success=True,
            case=ConsoleCase(
                id=case.id,
                conversation_id=case.conversation_id,
                status=case.status,
                trigger_type=case.trigger_type,
                created_at=case.created_at.isoformat(),
                assigned_to_name=case.assigned_to_name,
                branch_id=branch_id,
                **_format_case_metrics(case),
            ),
            sync=ConsoleCaseActionSync(
                telegram=_build_sync_status("skipped", "already_taken"),
                client_notify=_build_sync_status("skipped", "already_taken"),
            ),
        )
        if idempotency and idempotency.record:
            finalize_idempotency(
                db,
                record=idempotency.record,
                response_status=200,
                response_body=response.model_dump(mode="json"),
            )
        return response

    previous_status = case.status
    result = state_manager_take(db, conversation, case, str(context.agent.id), manager_name)
    if not result.ok:
        if idempotency and idempotency.record:
            release_idempotency(db, record=idempotency.record)
        raise ConsoleAPIError(409, "CASE_ALREADY_TAKEN", result.error or "Case already taken")

    record_audit_event(
        db,
        actor=context.agent,
        event_type="case_taken",
        entity_type="handover",
        entity_id=case.id,
        payload={"previous_status": previous_status},
        branch_id=branch_id,
    )

    try:
        db.commit()
        db.refresh(case)
        telegram_status = _sync_telegram_after_take(
            db,
            conversation=conversation,
            handover=case,
            manager_name=manager_name,
        )
        client_notify = _notify_client_status(
            db=db,
            conversation=conversation,
            handover=case,
            status="connected",
            manager_name=manager_name,
        )
        record_audit_event(
            db,
            actor=context.agent,
            event_type="manager_connected",
            entity_type="handover",
            entity_id=case.id,
            payload={
                "telegram_status": telegram_status.status,
                "client_notify_status": client_notify.status,
            },
            branch_id=branch_id,
        )
        db.commit()

        response = ConsoleCaseActionResponse(
            success=True,
            case=ConsoleCase(
                id=case.id,
                conversation_id=case.conversation_id,
                status=case.status,
                trigger_type=case.trigger_type,
                created_at=case.created_at.isoformat(),
                assigned_to_name=case.assigned_to_name,
                branch_id=branch_id,
                **_format_case_metrics(case),
            ),
            sync=ConsoleCaseActionSync(
                telegram=telegram_status,
                client_notify=client_notify,
            ),
        )
        if idempotency and idempotency.record:
            finalize_idempotency(
                db,
                record=idempotency.record,
                response_status=200,
                response_body=response.model_dump(mode="json"),
            )
        return response
    except Exception:
        if idempotency and idempotency.record:
            release_idempotency(db, record=idempotency.record)
        raise


@router.post(
    "/cases/{case_id}/resolve",
    response_model=ConsoleCaseActionResponse,
)
async def resolve_case(
    case_id: UUID, request: Request, db: Session = Depends(get_db)
) -> ConsoleCaseActionResponse:
    context = get_console_context(request, db)
    require_console_permission(context, "inbox", "write")
    idempotency_key = _get_idempotency_key(request)
    idempotency = start_idempotency(
        db,
        client_id=context.client.id,
        agent_id=context.agent.id,
        idempotency_key=idempotency_key,
        scope="console.case.resolve",
        payload={"case_id": str(case_id)},
    )
    if idempotency and idempotency.replay:
        return JSONResponse(
            status_code=idempotency.response_status,
            content=idempotency.response_body,
        )

    case = (
        db.query(Handover)
        .filter(Handover.id == case_id, Handover.client_id == context.client.id)
        .with_for_update()
        .first()
    )
    if not case:
        if idempotency and idempotency.record:
            release_idempotency(db, record=idempotency.record)
        raise ConsoleAPIError(404, "NOT_FOUND", "Case not found")

    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == case.conversation_id)
        .with_for_update()
        .first()
    )
    if not conversation:
        if idempotency and idempotency.record:
            release_idempotency(db, record=idempotency.record)
        raise ConsoleAPIError(404, "NOT_FOUND", "Conversation not found")

    branch_id = conversation.branch_id
    manager_name = context.agent.name or "Менеджер"

    if case.status == "resolved":
        if idempotency and idempotency.record:
            release_idempotency(db, record=idempotency.record)
        raise ConsoleAPIError(409, "CASE_ALREADY_RESOLVED", "Case already resolved")

    if context.role not in ("platform_admin", "owner", "admin"):
        if case.assigned_to_name and case.assigned_to_name != context.agent.name:
            if idempotency and idempotency.record:
                release_idempotency(db, record=idempotency.record)
            raise ConsoleAPIError(403, "NOT_ASSIGNED", "You are not assigned to this case")

    result = state_manager_resolve(
        db,
        conversation,
        case,
        str(context.agent.id),
        manager_name,
        preserve_context=True,
    )
    if not result.ok:
        if idempotency and idempotency.record:
            release_idempotency(db, record=idempotency.record)
        raise ConsoleAPIError(409, "CASE_ALREADY_RESOLVED", result.error or "Case already resolved")

    record_audit_event(
        db,
        actor=context.agent,
        event_type="case_resolved",
        entity_type="handover",
        entity_id=case.id,
        branch_id=branch_id,
    )
    remote_jid = resolve_conversation_remote_jid(db, conversation=conversation)
    released_lock = release_human_lock(
        db,
        client_id=context.client.id,
        remote_jid=remote_jid,
        conversation_id=conversation.id,
        now=datetime.now(timezone.utc),
    )
    if released_lock:
        record_audit_event(
            db,
            actor=context.agent,
            event_type="human_lock_release_auto",
            entity_type="conversation",
            entity_id=conversation.id,
            payload={"reason": "case_resolved"},
            branch_id=branch_id,
        )

    try:
        db.commit()
        telegram_status = _sync_telegram_after_close(
            db,
            conversation=conversation,
            handover=case,
            manager_name=manager_name,
            action="resolve",
        )
        client_notify = _notify_client_status(
            db=db,
            conversation=conversation,
            handover=case,
            status="disconnected",
            manager_name=manager_name,
        )
        record_audit_event(
            db,
            actor=context.agent,
            event_type="manager_disconnected",
            entity_type="handover",
            entity_id=case.id,
            payload={
                "telegram_status": telegram_status.status,
                "client_notify_status": client_notify.status,
            },
            branch_id=branch_id,
        )
        db.commit()

        response = ConsoleCaseActionResponse(
            success=True,
            case=ConsoleCase(
                id=case.id,
                conversation_id=case.conversation_id,
                status=case.status,
                trigger_type=case.trigger_type,
                created_at=case.created_at.isoformat(),
                branch_id=branch_id,
                **_format_case_metrics(case),
            ),
            sync=ConsoleCaseActionSync(
                telegram=telegram_status,
                client_notify=client_notify,
            ),
        )
        if idempotency and idempotency.record:
            finalize_idempotency(
                db,
                record=idempotency.record,
                response_status=200,
                response_body=response.model_dump(mode="json"),
            )
        return response
    except Exception:
        if idempotency and idempotency.record:
            release_idempotency(db, record=idempotency.record)
        raise


@router.post(
    "/cases/{case_id}/return",
    response_model=ConsoleCaseActionResponse,
)
async def return_case(
    case_id: UUID, request: Request, db: Session = Depends(get_db)
) -> ConsoleCaseActionResponse:
    context = get_console_context(request, db)
    require_console_permission(context, "inbox", "write")
    idempotency_key = _get_idempotency_key(request)
    idempotency = start_idempotency(
        db,
        client_id=context.client.id,
        agent_id=context.agent.id,
        idempotency_key=idempotency_key,
        scope="console.case.return",
        payload={"case_id": str(case_id)},
    )
    if idempotency and idempotency.replay:
        return JSONResponse(
            status_code=idempotency.response_status,
            content=idempotency.response_body,
        )

    case = (
        db.query(Handover)
        .filter(Handover.id == case_id, Handover.client_id == context.client.id)
        .with_for_update()
        .first()
    )
    if not case:
        if idempotency and idempotency.record:
            release_idempotency(db, record=idempotency.record)
        raise ConsoleAPIError(404, "NOT_FOUND", "Case not found")

    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == case.conversation_id)
        .with_for_update()
        .first()
    )
    if not conversation:
        if idempotency and idempotency.record:
            release_idempotency(db, record=idempotency.record)
        raise ConsoleAPIError(404, "NOT_FOUND", "Conversation not found")

    branch_id = conversation.branch_id
    manager_name = context.agent.name or "Менеджер"

    if case.status == "resolved":
        if idempotency and idempotency.record:
            release_idempotency(db, record=idempotency.record)
        raise ConsoleAPIError(409, "CASE_ALREADY_RESOLVED", "Case already resolved")

    if context.role not in ("platform_admin", "owner", "admin"):
        if case.assigned_to_name and case.assigned_to_name != context.agent.name:
            if idempotency and idempotency.record:
                release_idempotency(db, record=idempotency.record)
            raise ConsoleAPIError(403, "NOT_ASSIGNED", "You are not assigned to this case")

    result = state_manager_return(
        db,
        conversation,
        case,
        str(context.agent.id),
        manager_name,
    )
    if not result.ok:
        if idempotency and idempotency.record:
            release_idempotency(db, record=idempotency.record)
        raise ConsoleAPIError(409, "CASE_ALREADY_RESOLVED", result.error or "Case already resolved")

    record_audit_event(
        db,
        actor=context.agent,
        event_type="case_returned",
        entity_type="handover",
        entity_id=case.id,
        branch_id=branch_id,
    )
    remote_jid = resolve_conversation_remote_jid(db, conversation=conversation)
    released_lock = release_human_lock(
        db,
        client_id=context.client.id,
        remote_jid=remote_jid,
        conversation_id=conversation.id,
        now=datetime.now(timezone.utc),
    )
    if released_lock:
        record_audit_event(
            db,
            actor=context.agent,
            event_type="human_lock_release_auto",
            entity_type="conversation",
            entity_id=conversation.id,
            payload={"reason": "case_returned"},
            branch_id=branch_id,
        )

    try:
        db.commit()
        telegram_status = _sync_telegram_after_close(
            db,
            conversation=conversation,
            handover=case,
            manager_name=manager_name,
            action="return",
        )
        client_notify = _notify_client_status(
            db=db,
            conversation=conversation,
            handover=case,
            status="disconnected",
            manager_name=manager_name,
        )
        record_audit_event(
            db,
            actor=context.agent,
            event_type="manager_disconnected",
            entity_type="handover",
            entity_id=case.id,
            payload={
                "telegram_status": telegram_status.status,
                "client_notify_status": client_notify.status,
            },
            branch_id=branch_id,
        )
        db.commit()

        response = ConsoleCaseActionResponse(
            success=True,
            case=ConsoleCase(
                id=case.id,
                conversation_id=case.conversation_id,
                status=case.status,
                trigger_type=case.trigger_type,
                created_at=case.created_at.isoformat(),
                branch_id=branch_id,
                **_format_case_metrics(case),
            ),
            sync=ConsoleCaseActionSync(
                telegram=telegram_status,
                client_notify=client_notify,
            ),
        )
        if idempotency and idempotency.record:
            finalize_idempotency(
                db,
                record=idempotency.record,
                response_status=200,
                response_body=response.model_dump(mode="json"),
            )
        return response
    except Exception:
        if idempotency and idempotency.record:
            release_idempotency(db, record=idempotency.record)
        raise


@router.get(
    "/cases/{case_id}/messages",
    response_model=ConsoleMessageListResponse,
)
async def get_case_messages(
    case_id: UUID,
    request: Request,
    cursor: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
) -> ConsoleMessageListResponse:
    context = get_console_context(request, db)
    require_console_permission(context, "inbox", "read")
    _reject_unknown_query_params(request, {"cursor", "limit"})
    _validate_limit(limit)
    
    case = db.query(Handover).filter(Handover.id == case_id, Handover.client_id == context.client.id).first()
    if not case:
        raise ConsoleAPIError(404, "NOT_FOUND", "Case not found")

    conversation = db.query(Conversation).filter(Conversation.id == case.conversation_id).first()
    if not conversation:
        raise ConsoleAPIError(404, "NOT_FOUND", "Conversation not found")
    _require_branch_access(context, conversation.branch_id, message="Access to this case denied")
        
    query = db.query(Message).filter(Message.conversation_id == case.conversation_id)
    query = query.order_by(Message.created_at.desc())
    
    cursor_date = _parse_cursor_param(cursor)
    if cursor_date is not None:
        query = query.filter(Message.created_at < cursor_date)

    items = query.limit(limit + 1).all()
    
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]
        next_cursor = items[-1].created_at.isoformat()
    else:
        next_cursor = None
        
    # Reverse for chat view (oldest first) if needed, but API usually returns newest first for pagination
    # Frontend will reverse.
    
    return ConsoleMessageListResponse(
        items=[
            ConsoleMessage(
                id=item.id,
                role=item.role,
                content=item.content,
                created_at=item.created_at.isoformat(),
                metadata=item.message_metadata
            )
            for item in items
        ],
        cursor=next_cursor,
        has_more=has_more
    )


@router.get(
    "/inbox/macros",
    response_model=ConsoleMacroListResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_inbox_macros(
    request: Request,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
) -> ConsoleMacroListResponse:
    context = get_console_context(request, db)
    require_console_permission(context, "inbox", "read")
    _reject_unknown_query_params(request, {"include_inactive"})

    branch = _resolve_branch_from_context(context)
    query = (
        db.query(ConsoleMacroModel)
        .filter(
            ConsoleMacroModel.client_id == context.client.id,
            ConsoleMacroModel.branch_id == branch.id,
        )
        .filter(
            or_(
                ConsoleMacroModel.agent_id.is_(None),
                ConsoleMacroModel.agent_id == context.agent.id,
            )
        )
    )
    if not include_inactive:
        query = query.filter(ConsoleMacroModel.is_active.is_(True))

    macros = query.order_by(ConsoleMacroModel.created_at.asc()).all()
    return ConsoleMacroListResponse(items=[_serialize_macro(macro) for macro in macros])


@router.post(
    "/inbox/macros",
    response_model=ConsoleMacroCreateResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def create_inbox_macro(
    request: Request,
    body: ConsoleMacroCreateRequest,
    db: Session = Depends(get_db),
) -> ConsoleMacroCreateResponse:
    context = get_console_context(request, db)
    require_console_permission(context, "inbox", "write")

    scope = _normalize_required_text(body.scope, "scope")
    if scope not in ("personal", "team"):
        raise ConsoleAPIError(400, "INVALID_PARAM", "scope must be personal or team")

    branch = _resolve_branch_from_context(context)
    now = datetime.now(timezone.utc)
    macro = ConsoleMacroModel(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=branch.id,
        agent_id=context.agent.id if scope == "personal" else None,
        scope=scope,
        label=_normalize_required_text(body.label, "label"),
        body=_normalize_required_text(body.body, "body"),
        is_active=body.is_active if body.is_active is not None else True,
        created_at=now,
        updated_at=now,
    )
    db.add(macro)
    db.commit()

    return ConsoleMacroCreateResponse(macro=_serialize_macro(macro))


@router.patch(
    "/inbox/macros/{macro_id}",
    response_model=ConsoleMacroSchema,
    responses={
        401: {"model": ConsoleErrorResponse},
        403: {"model": ConsoleErrorResponse},
        404: {"model": ConsoleErrorResponse},
    },
)
async def update_inbox_macro(
    macro_id: UUID,
    request: Request,
    body: ConsoleMacroUpdateRequest,
    db: Session = Depends(get_db),
) -> ConsoleMacroSchema:
    context = get_console_context(request, db)
    require_console_permission(context, "inbox", "write")

    branch = _resolve_branch_from_context(context)
    macro = (
        db.query(ConsoleMacroModel)
        .filter(
            ConsoleMacroModel.id == macro_id,
            ConsoleMacroModel.client_id == context.client.id,
            ConsoleMacroModel.branch_id == branch.id,
        )
        .first()
    )
    if not macro:
        raise ConsoleAPIError(404, "NOT_FOUND", "Macro not found")

    is_privileged = context.role in ("platform_admin", "owner", "admin")
    if macro.agent_id and macro.agent_id != context.agent.id and not is_privileged:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Cannot edit another agent's macro")

    fields_set = body.model_fields_set
    if "label" in fields_set:
        macro.label = _normalize_required_text(body.label, "label")
    if "body" in fields_set:
        macro.body = _normalize_required_text(body.body, "body")
    if "is_active" in fields_set:
        macro.is_active = bool(body.is_active)

    if fields_set:
        macro.updated_at = datetime.now(timezone.utc)
        db.commit()

    return _serialize_macro(macro)


@router.get(
    "/cases/{case_id}",
    response_model=ConsoleCase,
    responses={404: {"model": ConsoleErrorResponse}},
)
async def get_case(
    case_id: UUID, request: Request, db: Session = Depends(get_db)
) -> ConsoleCase:
    """Get single case details by ID."""
    context = get_console_context(request, db)
    require_console_permission(context, "inbox", "read")
    
    case = db.query(Handover).filter(
        Handover.id == case_id,
        Handover.client_id == context.client.id
    ).first()
    
    if not case:
        raise ConsoleAPIError(404, "NOT_FOUND", "Case not found")
    
    # Get customer info from User table via Conversation
    from app.models import Conversation as ConvModel
    from app.models import User
    from app.models.client_settings import ClientSettings
    from app.services.escalation_service import resolve_telegram_routing
    customer_name = None
    customer_phone = None
    customer_remote_jid = None
    decision_trace = None
    branch_id = None
    telegram_trail = None
    
    conversation = db.query(ConvModel).filter(ConvModel.id == case.conversation_id).first()
    if conversation:
        branch_id = conversation.branch_id
        
        # Get customer info
        if conversation.user_id:
            user = db.query(User).filter(User.id == conversation.user_id).first()
            if user:
                customer_name = user.name
                customer_phone = user.phone
                customer_remote_jid = user.remote_jid
        
        # Get decision trace from context
        context_data = conversation.context or {}
        raw_trace = context_data.get("decision_trace")
        if isinstance(raw_trace, list):
            decision_trace = raw_trace

        routing_meta = resolve_telegram_routing(
            db,
            conversation=conversation,
            client_id=context.client.id,
        )
        chat_id = routing_meta.get("chat_id")
        if not chat_id:
            settings = db.query(ClientSettings).filter(ClientSettings.client_id == context.client.id).first()
            chat_id = settings.telegram_chat_id if settings else None
        telegram_trail = _build_telegram_trail(
            handover=case,
            conversation=conversation,
            chat_id=chat_id,
        )

    case_health = _fetch_case_health(db, conversation) if conversation else {}
    human_lock_snapshot = _build_case_human_lock_snapshot(
        db,
        client_id=context.client.id,
        conversation=conversation,
    )
    handover_meta = case.meta if isinstance(case.meta, dict) else None
    handover_media_refs = (
        handover_meta.get("media_refs")
        if isinstance(handover_meta, dict) and isinstance(handover_meta.get("media_refs"), list)
        else None
    )
    handover_messages = case.messages if isinstance(case.messages, list) else None

    # Check branch access (skip if branch_id is None or agent is admin/owner)
    allowed_branch_ids = {b.id for b in context.branches}
    if branch_id is not None and branch_id not in allowed_branch_ids:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Access to this case denied")
    
    sla_status = _calculate_sla_status(case.created_at)
    
    return ConsoleCase(
        id=case.id,
        conversation_id=case.conversation_id,
        status=case.status,
        trigger_type=case.trigger_type,
        trigger_value=case.trigger_value,
        context_summary=case.context_summary,
        user_message=case.user_message,
        assigned_to_name=case.assigned_to_name,
        branch_id=branch_id,
        channel=case.channel,
        created_at=case.created_at.isoformat(),
        **_format_case_metrics(case),
        sla_status=sla_status,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_remote_jid=customer_remote_jid,
        handover_meta=handover_meta,
        handover_media_refs=handover_media_refs,
        handover_messages=handover_messages,
        decision_trace=decision_trace,
        last_inbound_at=case_health.get("last_inbound_at").isoformat() if case_health.get("last_inbound_at") else None,
        last_outbound_at=case_health.get("last_outbound_at").isoformat() if case_health.get("last_outbound_at") else None,
        last_activity_at=case_health.get("last_activity_at").isoformat() if case_health.get("last_activity_at") else None,
        last_activity_channel=case_health.get("last_activity_channel"),
        last_message_preview=case_health.get("last_message_preview"),
        needs_reply=case_health.get("needs_reply"),
        has_delivery_error=case_health.get("has_delivery_error"),
        has_pending_outbox=case_health.get("has_pending_outbox"),
        **human_lock_snapshot,
        telegram_trail=telegram_trail,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ConsoleManagerMessageResponse,
)
async def send_manager_message(
    conversation_id: UUID,
    body: ConsoleManagerMessageRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleManagerMessageResponse:
    """Send a message from the manager to the customer via WhatsApp."""
    from app.logging_config import get_logger
    from app.schemas.console import ConsoleManagerMessageRequest, ConsoleManagerMessageResponse

    logger = get_logger("console_send_message")

    context = get_console_context(request, db)
    require_console_permission(context, "inbox", "write")
    idempotency_key = _get_idempotency_key(request)
    normalized_content = _normalize_required_text(body.content, "content")
    pause_enabled = bool(getattr(body, "pause_enabled", True))
    pause_minutes = _normalize_pause_minutes(
        getattr(body, "pause_minutes", None),
        default=30,
        allow_zero=True,
    )
    pause_reason = _normalize_optional_text(getattr(body, "pause_reason", None)) or "manual_reply"
    human_lock_scope = (
        HUMAN_LOCK_SCOPE_CONVERSATION if _is_human_lock_v2_enabled() else HUMAN_LOCK_SCOPE_REMOTE
    )

    # Verify access to conversation via handover
    case = db.query(Handover).filter(
        Handover.conversation_id == conversation_id,
        Handover.client_id == context.client.id,
    ).first()

    if not case:
        raise ConsoleAPIError(404, "NOT_FOUND", "Conversation not found or access denied")

    conversation = _resolve_console_conversation_or_404(
        db,
        client_id=context.client.id,
        conversation_id=conversation_id,
    )
    _require_branch_access(context, conversation.branch_id, message="Access to this conversation denied")

    # Only allow if case is active and assigned to this agent, or agent is owner/admin
    if case.status != "active" and context.role not in ("platform_admin", "owner", "admin"):
        raise ConsoleAPIError(403, "CASE_NOT_ACTIVE", "Case must be active to send messages")

    if context.role not in ("platform_admin", "owner", "admin"):
        assigned_id = str(case.assigned_to or "").strip()
        if assigned_id:
            if assigned_id != str(context.agent.id):
                raise ConsoleAPIError(403, "NOT_ASSIGNED", "You are not assigned to this case")
        else:
            assigned_name = (case.assigned_to_name or "").strip()
            agent_name = (context.agent.name or "").strip()
            if assigned_name and assigned_name != agent_name:
                raise ConsoleAPIError(403, "NOT_ASSIGNED", "You are not assigned to this case")
            if not assigned_name:
                raise ConsoleAPIError(403, "NOT_ASSIGNED", "You are not assigned to this case")

    idempotency = start_idempotency(
        db,
        client_id=context.client.id,
        agent_id=context.agent.id,
        idempotency_key=idempotency_key,
        scope="console.conversation.message",
        payload={
            "conversation_id": str(conversation_id),
            "content": normalized_content,
        },
    )
    if idempotency and idempotency.replay:
        return JSONResponse(
            status_code=idempotency.response_status,
            content=idempotency.response_body,
        )

    # Create the message
    commit_done = False
    try:
        new_message = Message(
            conversation_id=conversation_id,
            client_id=context.client.id,
            role="manager",
            content=normalized_content,
            created_at=datetime.now(timezone.utc),
            message_metadata={"source": "console"},
        )
        db.add(new_message)
        case.manager_response = normalized_content
        if case.first_response_at is None:
            case.first_response_at = datetime.now(timezone.utc)
        if not case.assigned_to_name and context.agent.name:
            case.assigned_to_name = context.agent.name

        # Audit
        record_audit_event(
            db,
            actor=context.agent,
            event_type="message_sent",
            entity_type="conversation",
            entity_id=conversation_id,
            payload={"content_length": len(normalized_content), "source": "web_console"},
            branch_id=conversation.branch_id,
        )

        db.commit()
        commit_done = True
        db.refresh(new_message)
    except Exception:
        if idempotency and idempotency.record and not commit_done:
            release_idempotency(db, record=idempotency.record)
        raise

    delivery_status = "failed"
    delivery_error = None
    outbox_enqueued: Optional[bool] = None
    now_utc = datetime.now(timezone.utc)

    try:
        remote_jid = resolve_conversation_remote_jid(db, conversation=conversation)
        if not remote_jid:
            delivery_error = "user_jid_not_found"
        else:
            instance_id = get_instance_id(
                db,
                context.client.id,
                branch_id=conversation.branch_id,
                remote_jid=remote_jid,
            )
            if not instance_id:
                delivery_error = "instance_id_not_found"
            elif _is_env_enabled(os.environ.get("OUTBOX_WORKER_ENABLED"), default=False):
                outbox_idempotency_key = idempotency_key or build_inbound_message_id(
                    None,
                    remote_jid,
                    int(now_utc.timestamp()),
                    normalized_content,
                )
                client_slug = _normalize_optional_text(getattr(context.client, "name", None)) or "truffles"
                outbox_payload = _build_console_outbox_text_payload(
                    client_id=context.client.id,
                    branch_id=conversation.branch_id,
                    conversation_id=conversation.id,
                    client_slug=client_slug,
                    remote_jid=remote_jid,
                    instance_id=instance_id,
                    text_value=normalized_content,
                    idempotency_key=outbox_idempotency_key,
                    source="console_message",
                    now=now_utc,
                )
                outbox_enqueued = enqueue_outbox_message(
                    db,
                    client_id=context.client.id,
                    conversation_id=conversation.id,
                    inbound_message_id=outbox_idempotency_key,
                    payload_json=outbox_payload,
                    branch_id=conversation.branch_id,
                )
                metadata = dict(new_message.message_metadata or {})
                metadata.update(
                    {
                        "source": "console",
                        "outbox_enqueued": outbox_enqueued,
                        "outbox_event_type": "whatsapp.send_text",
                        "outbox_idempotency_key": outbox_idempotency_key,
                    }
                )
                new_message.message_metadata = metadata
                delivery_status = "queued"
            else:
                sent = send_bot_response(
                    db=db,
                    client_id=context.client.id,
                    remote_jid=remote_jid,
                    message=normalized_content,
                    branch_id=conversation.branch_id,
                    idempotency_key=idempotency_key,
                )
                if sent:
                    delivery_status = "delivered"
                else:
                    delivery_error = "chatflow_send_failed"

            if delivery_status in {"queued", "delivered"} and pause_enabled and pause_minutes > 0:
                upsert_human_lock(
                    db,
                    client_id=context.client.id,
                    remote_jid=remote_jid,
                    lock_until=now_utc + timedelta(minutes=pause_minutes),
                    conversation_id=conversation.id,
                    branch_id=conversation.branch_id,
                    locked_by_id=context.agent.id,
                    locked_by_name=context.agent.name,
                    source="console_message",
                    reason=pause_reason,
                    lock_scope=human_lock_scope,
                )
    except Exception as exc:
        logger.error("WhatsApp delivery error: %s", exc)
        delivery_status = "failed"
        delivery_error = str(exc)

    if delivery_status == "failed" and not delivery_error:
        delivery_error = "chatflow_send_failed"

    db.commit()

    if delivery_status in {"delivered", "queued"}:
        try:
            if conversation.telegram_topic_id:
                routing_meta = resolve_telegram_routing(
                    db,
                    conversation=conversation,
                    client_id=context.client.id,
                )
                bot_token = routing_meta.get("bot_token")
                chat_id = routing_meta.get("chat_id")
                if bot_token and chat_id:
                    telegram = TelegramService(bot_token)
                    manager_label = context.agent.name or "Менеджер"
                    result = telegram.send_message(
                        chat_id=str(chat_id),
                        text=f"🖥️ <b>{manager_label}</b>: {normalized_content}",
                        message_thread_id=conversation.telegram_topic_id,
                    )
                    if not result.get("ok"):
                        logger.warning(
                            "Telegram console echo failed",
                            extra={
                                "context": {
                                    "conversation_id": str(conversation_id),
                                    "error": result.get("error"),
                                }
                            },
                        )
        except Exception as exc:
            logger.warning(
                "Telegram console echo exception",
                extra={"context": {"conversation_id": str(conversation_id), "error": str(exc)}},
            )

    response = ConsoleManagerMessageResponse(
        success=delivery_status in {"delivered", "queued"},
        message=ConsoleMessage(
            id=new_message.id,
            role=new_message.role,
            content=new_message.content,
            created_at=new_message.created_at.isoformat(),
            metadata=new_message.message_metadata,
        ),
    )
    if idempotency and idempotency.record:
        finalize_idempotency(
            db,
            record=idempotency.record,
            response_status=200,
            response_body=response.model_dump(mode="json"),
        )
    return response


@router.post(
    "/outreach/messages",
    response_model=ConsoleOutreachMessageResponse,
)
async def send_outreach_message(
    body: ConsoleOutreachMessageRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleOutreachMessageResponse:
    """Send manual outreach message by phone/JID with optional per-client bot pause."""
    context = get_console_context(request, db)
    require_console_permission(context, "outreach", "write")

    remote_jid = _normalize_outreach_destination(body.destination)
    content = _normalize_required_text(body.content, "content")
    pause_minutes = _normalize_pause_minutes(body.pause_bot_minutes, default=30, allow_zero=True)
    pause_reason = _normalize_optional_text(body.pause_reason)
    idempotency_key = _get_idempotency_key(request)
    human_lock_scope = (
        HUMAN_LOCK_SCOPE_CONVERSATION if _is_human_lock_v2_enabled() else HUMAN_LOCK_SCOPE_REMOTE
    )

    conversation: Conversation | None = None
    auto_case: Handover | None = None
    auto_case_created = False
    branch_id = body.branch_id
    if body.conversation_id:
        conversation = _resolve_console_conversation_or_404(
            db,
            client_id=context.client.id,
            conversation_id=body.conversation_id,
        )
        if conversation.branch_id and branch_id and branch_id != conversation.branch_id:
            raise ConsoleAPIError(
                400,
                "INVALID_PARAM",
                "branch_id must match conversation branch",
            )
        branch_id = conversation.branch_id or branch_id
    if branch_id is not None:
        _require_branch_access(context, branch_id, message="Access to this branch denied")
    else:
        branch_id = _resolve_branch_from_context(context).id

    instance_id = get_instance_id(
        db,
        context.client.id,
        branch_id=branch_id,
        remote_jid=remote_jid,
    )
    if not instance_id:
        raise ConsoleAPIError(
            409,
            "INTEGRATION_UNAVAILABLE",
            "WhatsApp integration is not configured for this branch",
        )

    idempotency = start_idempotency(
        db,
        client_id=context.client.id,
        agent_id=context.agent.id,
        idempotency_key=idempotency_key,
        scope="console.outreach.message",
        payload={
            "destination": remote_jid,
            "content": content,
            "conversation_id": str(conversation.id) if conversation else None,
            "branch_id": str(branch_id) if branch_id else None,
            "pause_bot_minutes": pause_minutes,
        },
    )
    if idempotency and idempotency.replay:
        return JSONResponse(
            status_code=idempotency.response_status,
            content=idempotency.response_body,
        )

    if conversation is None:
        conversation, auto_case, auto_case_created = _bootstrap_outreach_conversation_case(
            db,
            context=context,
            remote_jid=remote_jid,
            branch_id=branch_id,
            content=content,
        )

    message: Message | None = None
    commit_done = False
    try:
        message_metadata = {
            "source": "console_outreach",
            "destination": remote_jid,
        }
        if auto_case:
            message_metadata["auto_case_id"] = str(auto_case.id)
            message_metadata["auto_case_created"] = auto_case_created

        message = Message(
            conversation_id=conversation.id,
            client_id=context.client.id,
            role="manager",
            content=content,
            created_at=datetime.now(timezone.utc),
            message_metadata=message_metadata,
        )
        db.add(message)
        db.flush()
        if auto_case and auto_case.trigger_message_id is None:
            auto_case.trigger_message_id = message.id

        record_audit_event(
            db,
            actor=context.agent,
            event_type="outreach_sent",
            entity_type="conversation",
            entity_id=conversation.id,
            payload={
                "destination": remote_jid,
                "content_length": len(content),
                "conversation_id": str(conversation.id),
                "case_id": str(auto_case.id) if auto_case else None,
                "auto_case_created": auto_case_created if auto_case else None,
                "mode": "no_case_auto_case" if auto_case else "conversation",
            },
            branch_id=branch_id,
        )
        db.commit()
        commit_done = True
        db.refresh(message)
        if auto_case:
            db.refresh(auto_case)
    except Exception:
        if idempotency and idempotency.record and not commit_done:
            release_idempotency(db, record=idempotency.record)
        raise

    delivery_status: Literal["queued", "delivered", "failed"] = "failed"
    delivery_error: Optional[str] = None
    outbox_enqueued: Optional[bool] = None
    lock_until: Optional[datetime] = None
    now_utc = datetime.now(timezone.utc)

    try:
        if _is_env_enabled(os.environ.get("OUTBOX_WORKER_ENABLED"), default=False):
            outbox_idempotency_key = idempotency_key or build_inbound_message_id(
                None,
                remote_jid,
                int(now_utc.timestamp()),
                content,
            )
            client_slug = _normalize_optional_text(getattr(context.client, "name", None)) or "truffles"
            outbox_payload = _build_console_outbox_text_payload(
                client_id=context.client.id,
                branch_id=branch_id,
                conversation_id=conversation.id,
                client_slug=client_slug,
                remote_jid=remote_jid,
                instance_id=instance_id,
                text_value=content,
                idempotency_key=outbox_idempotency_key,
                source="console_outreach",
                now=now_utc,
            )
            outbox_enqueued = enqueue_outbox_message(
                db,
                client_id=context.client.id,
                conversation_id=conversation.id,
                inbound_message_id=outbox_idempotency_key,
                payload_json=outbox_payload,
                branch_id=branch_id,
            )
            delivery_status = "queued"
            metadata = dict(message.message_metadata or {})
            metadata.update(
                {
                    "outbox_enqueued": outbox_enqueued,
                    "outbox_event_type": "whatsapp.send_text",
                    "outbox_idempotency_key": outbox_idempotency_key,
                }
            )
            message.message_metadata = metadata
        else:
            sent = send_bot_response(
                db=db,
                client_id=context.client.id,
                remote_jid=remote_jid,
                message=content,
                branch_id=branch_id,
                idempotency_key=idempotency_key,
            )
            if sent:
                delivery_status = "delivered"
            else:
                delivery_error = "chatflow_send_failed"

        if delivery_status in {"queued", "delivered"} and pause_minutes > 0:
            lock = upsert_human_lock(
                db,
                client_id=context.client.id,
                remote_jid=remote_jid,
                lock_until=now_utc + timedelta(minutes=pause_minutes),
                conversation_id=conversation.id,
                branch_id=branch_id,
                locked_by_id=context.agent.id,
                locked_by_name=context.agent.name,
                source="console_outreach",
                reason=pause_reason or "manual_pause",
                lock_scope=human_lock_scope,
            )
            lock_until = _coerce_utc_datetime(lock.lock_until)
    except Exception as exc:
        delivery_status = "failed"
        delivery_error = str(exc)

    if delivery_status == "failed" and not delivery_error:
        delivery_error = "chatflow_send_failed"

    db.commit()

    response = ConsoleOutreachMessageResponse(
        success=delivery_status in {"queued", "delivered"},
        delivery_status=delivery_status,
        remote_jid=remote_jid,
        conversation_id=conversation.id,
        case_id=auto_case.id if auto_case else None,
        case_created=auto_case_created if auto_case else None,
        outbox_enqueued=outbox_enqueued,
        lock_until=lock_until.isoformat() if lock_until else None,
        message=ConsoleMessage(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at.isoformat(),
            metadata=message.message_metadata,
        )
        if message
        else None,
        error_code=delivery_error,
    )
    if idempotency and idempotency.record:
        finalize_idempotency(
            db,
            record=idempotency.record,
            response_status=200,
            response_body=response.model_dump(mode="json"),
        )
    return response


@router.get(
    "/conversations/{conversation_id}/human-lock",
    response_model=ConsoleHumanLockStatusResponse,
)
async def get_conversation_human_lock_status(
    conversation_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleHumanLockStatusResponse:
    context = get_console_context(request, db)
    require_console_permission(context, "outreach", "read")

    conversation = _resolve_console_conversation_or_404(
        db,
        client_id=context.client.id,
        conversation_id=conversation_id,
    )
    _require_branch_access(context, conversation.branch_id, message="Access to this conversation denied")

    remote_jid = resolve_conversation_remote_jid(db, conversation=conversation)
    now_utc = datetime.now(timezone.utc)
    lock = get_active_human_lock(
        db,
        client_id=context.client.id,
        remote_jid=remote_jid,
        conversation_id=conversation.id,
        now=now_utc,
    )
    db.commit()
    return ConsoleHumanLockStatusResponse(
        success=True,
        status=_build_human_lock_status_payload(lock, remote_jid=remote_jid, now=now_utc),
    )


@router.post(
    "/conversations/{conversation_id}/human-lock/pause",
    response_model=ConsoleHumanLockStatusResponse,
)
async def pause_conversation_human_lock(
    conversation_id: UUID,
    body: ConsoleHumanLockPauseRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleHumanLockStatusResponse:
    context = get_console_context(request, db)
    require_console_permission(context, "outreach", "write")

    minutes = _normalize_pause_minutes(body.minutes, default=30, allow_zero=False)
    reason = _normalize_optional_text(body.reason) or "manual_pause"
    human_lock_scope = (
        HUMAN_LOCK_SCOPE_CONVERSATION if _is_human_lock_v2_enabled() else HUMAN_LOCK_SCOPE_REMOTE
    )
    conversation = _resolve_console_conversation_or_404(
        db,
        client_id=context.client.id,
        conversation_id=conversation_id,
    )
    _require_branch_access(context, conversation.branch_id, message="Access to this conversation denied")
    remote_jid = resolve_conversation_remote_jid(db, conversation=conversation)
    if not remote_jid:
        raise ConsoleAPIError(
            409,
            "INTEGRATION_UNAVAILABLE",
            "Customer WhatsApp contact is not available",
        )

    now_utc = datetime.now(timezone.utc)
    lock = upsert_human_lock(
        db,
        client_id=context.client.id,
        remote_jid=remote_jid,
        lock_until=now_utc + timedelta(minutes=minutes),
        conversation_id=conversation.id,
        branch_id=conversation.branch_id,
        locked_by_id=context.agent.id,
        locked_by_name=context.agent.name,
        source="console_pause",
        reason=reason,
        lock_scope=human_lock_scope,
    )
    record_audit_event(
        db,
        actor=context.agent,
        event_type="human_lock_pause",
        entity_type="conversation",
        entity_id=conversation.id,
        payload={
            "minutes": minutes,
            "remote_jid": remote_jid,
            "reason": reason,
        },
        branch_id=conversation.branch_id,
    )
    db.commit()
    return ConsoleHumanLockStatusResponse(
        success=True,
        status=_build_human_lock_status_payload(lock, remote_jid=remote_jid, now=now_utc),
    )


@router.delete(
    "/conversations/{conversation_id}/human-lock",
    response_model=ConsoleHumanLockStatusResponse,
)
async def release_conversation_human_lock(
    conversation_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleHumanLockStatusResponse:
    context = get_console_context(request, db)
    require_console_permission(context, "outreach", "write")

    conversation = _resolve_console_conversation_or_404(
        db,
        client_id=context.client.id,
        conversation_id=conversation_id,
    )
    _require_branch_access(context, conversation.branch_id, message="Access to this conversation denied")
    remote_jid = resolve_conversation_remote_jid(db, conversation=conversation)
    now_utc = datetime.now(timezone.utc)

    lock = release_human_lock(
        db,
        client_id=context.client.id,
        remote_jid=remote_jid,
        conversation_id=conversation.id,
        now=now_utc,
    )
    record_audit_event(
        db,
        actor=context.agent,
        event_type="human_lock_release",
        entity_type="conversation",
        entity_id=conversation.id,
        payload={
            "released": bool(lock),
            "remote_jid": remote_jid,
        },
        branch_id=conversation.branch_id,
    )
    db.commit()
    return ConsoleHumanLockStatusResponse(
        success=True,
        status=ConsoleHumanLockStatus(active=False, remote_jid=remote_jid),
    )


@router.post(
    "/conversations/{conversation_id}/messages/media",
    response_model=ConsoleManagerMessageResponse,
)
async def send_manager_media(
    conversation_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    pause_enabled: Optional[bool] = Form(True),
    pause_minutes: Optional[int] = Form(30),
    pause_reason: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> ConsoleManagerMessageResponse:
    """Send a media message from the manager to the customer via WhatsApp."""
    from app.logging_config import get_logger

    logger = get_logger("console_send_media")

    context = get_console_context(request, db)
    require_console_permission(context, "inbox", "write")
    idempotency = None
    idempotency_key = _get_idempotency_key(request)
    normalized_caption = _normalize_media_caption(caption)
    media_type = _resolve_console_media_type(file.filename, file.content_type)
    pause_enabled = bool(pause_enabled)
    pause_minutes = _normalize_pause_minutes(pause_minutes, default=30, allow_zero=True)
    pause_reason = _normalize_optional_text(pause_reason) or "manual_reply"
    human_lock_scope = (
        HUMAN_LOCK_SCOPE_CONVERSATION if _is_human_lock_v2_enabled() else HUMAN_LOCK_SCOPE_REMOTE
    )

    case = db.query(Handover).filter(
        Handover.conversation_id == conversation_id,
        Handover.client_id == context.client.id
    ).first()

    if not case:
        raise ConsoleAPIError(404, "NOT_FOUND", "Conversation not found or access denied")

    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise ConsoleAPIError(404, "NOT_FOUND", "Conversation not found")
    _require_branch_access(context, conversation.branch_id, message="Access to this conversation denied")

    if case.status != "active" and context.role not in ("platform_admin", "owner", "admin"):
        raise ConsoleAPIError(403, "CASE_NOT_ACTIVE", "Case must be active to send messages")

    if context.role not in ("platform_admin", "owner", "admin"):
        assigned_id = str(case.assigned_to or "").strip()
        if assigned_id:
            if assigned_id != str(context.agent.id):
                raise ConsoleAPIError(403, "NOT_ASSIGNED", "You are not assigned to this case")
        else:
            assigned_name = (case.assigned_to_name or "").strip()
            agent_name = (context.agent.name or "").strip()
            if assigned_name and assigned_name != agent_name:
                raise ConsoleAPIError(403, "NOT_ASSIGNED", "You are not assigned to this case")
            if not assigned_name:
                raise ConsoleAPIError(403, "NOT_ASSIGNED", "You are not assigned to this case")

    idempotency = start_idempotency(
        db,
        client_id=context.client.id,
        agent_id=context.agent.id,
        idempotency_key=idempotency_key,
        scope="console.conversation.media",
        payload={
            "conversation_id": str(conversation_id),
            "media_type": media_type,
            "file_name": file.filename,
            "content_type": file.content_type,
            "caption": normalized_caption,
        },
    )
    if idempotency and idempotency.replay:
        return JSONResponse(
            status_code=idempotency.response_status,
            content=idempotency.response_body,
        )

    try:
        saved_message, delivery_status, _delivery_error = await process_console_media_upload(
            db,
            conversation=conversation,
            handover=case,
            agent=context.agent,
            upload=file,
            media_type=media_type,
            caption=normalized_caption,
            idempotency_key=idempotency_key,
        )
    except Exception:
        if idempotency and idempotency.record:
            release_idempotency(db, record=idempotency.record)
        raise

    if delivery_status in {"delivered", "queued"}:
        remote_jid = resolve_conversation_remote_jid(db, conversation=conversation)
        if remote_jid and pause_enabled and pause_minutes > 0:
            upsert_human_lock(
                db,
                client_id=context.client.id,
                remote_jid=remote_jid,
                lock_until=datetime.now(timezone.utc) + timedelta(minutes=pause_minutes),
                conversation_id=conversation.id,
                branch_id=conversation.branch_id,
                locked_by_id=context.agent.id,
                locked_by_name=context.agent.name,
                source="console_media",
                reason=pause_reason,
                lock_scope=human_lock_scope,
            )

    if delivery_status in {"delivered", "queued"} and conversation.telegram_topic_id:
        try:
            routing_meta = resolve_telegram_routing(
                db,
                conversation=conversation,
                client_id=context.client.id,
            )
            bot_token = routing_meta.get("bot_token")
            chat_id = routing_meta.get("chat_id")
            if bot_token and chat_id:
                telegram = TelegramService(bot_token)
                media_meta = (saved_message.message_metadata or {}).get("media") or {}
                storage_path = media_meta.get("storage_path")
                public_url = media_meta.get("public_url")
                media_source = storage_path if storage_path and Path(storage_path).exists() else public_url
                telegram_caption = _build_console_telegram_caption(
                    context.agent.name or "Менеджер",
                    normalized_caption,
                )
                if media_source:
                    if media_type == "photo":
                        telegram.send_photo(
                            chat_id=str(chat_id),
                            photo=media_source,
                            caption=telegram_caption,
                            message_thread_id=conversation.telegram_topic_id,
                        )
                    elif media_type == "audio":
                        telegram.send_audio(
                            chat_id=str(chat_id),
                            audio=media_source,
                            caption=telegram_caption,
                            message_thread_id=conversation.telegram_topic_id,
                        )
                    else:
                        telegram.send_document(
                            chat_id=str(chat_id),
                            document=media_source,
                            caption=telegram_caption,
                            message_thread_id=conversation.telegram_topic_id,
                        )
        except Exception as exc:
            logger.warning(
                "Telegram console media echo failed",
                extra={"context": {"conversation_id": str(conversation_id), "error": str(exc)}},
            )

    response = ConsoleManagerMessageResponse(
        success=delivery_status in {"delivered", "queued"},
        message=ConsoleMessage(
            id=saved_message.id,
            role=saved_message.role,
            content=saved_message.content,
            created_at=saved_message.created_at.isoformat(),
            metadata=saved_message.message_metadata,
        ),
    )
    if idempotency and idempotency.record:
        finalize_idempotency(
            db,
            record=idempotency.record,
            response_status=200,
            response_body=response.model_dump(mode="json"),
        )
    return response


def _apply_billable_outbox_filters(query):
    return (
        query.filter(text("outbox_messages.payload_json->'tenant_context'->>'source' = 'system'"))
        .filter(text("COALESCE(LOWER(outbox_messages.meta->'simulation'->>'mode'), 'false') <> 'true'"))
        .filter(
            text(
                """
                (
                    LOWER(outbox_messages.meta->'provider_status'->>'status') IN ('sent', 'delivered', 'read')
                    OR (
                        outbox_messages.meta->'provider_status' IS NULL
                        AND outbox_messages.status = 'SENT'
                    )
                )
                """
            )
        )
    )


_DEFAULT_OWNER_MODE_SETTINGS = ConsoleOwnerOperationSettingsPatch(
    reminder_1_minutes=10,
    reminder_2_minutes=45,
    escalation_timeout_minutes=120,
)

_OWNER_MODE_CONFIG: dict[ConsoleOwnerMode, dict[str, object]] = {
    "capture_leads": {
        "label": "Больше закрытых лидов",
        "settings_patch": ConsoleOwnerOperationSettingsPatch(
            reminder_1_minutes=5,
            reminder_2_minutes=30,
            escalation_timeout_minutes=60,
        ),
        "warnings": [
            "Ускоренный режим повышает нагрузку на менеджеров в пиковые часы.",
        ],
    },
    "stable_quality": {
        "label": "Стабильное качество сервиса",
        "settings_patch": ConsoleOwnerOperationSettingsPatch(
            reminder_1_minutes=10,
            reminder_2_minutes=45,
            escalation_timeout_minutes=120,
        ),
        "warnings": [
            "Сбалансированный режим безопасен по умолчанию, но требует ежедневного контроля backlog.",
        ],
    },
    "team_protection": {
        "label": "Беречь команду в пик",
        "settings_patch": ConsoleOwnerOperationSettingsPatch(
            reminder_1_minutes=15,
            reminder_2_minutes=60,
            escalation_timeout_minutes=180,
        ),
        "warnings": [
            "Бережный режим снижает давление на команду, но может замедлить обработку лидов.",
        ],
    },
}


def _build_metric_meta(
    *,
    kind: Literal["fact", "estimate", "missing"],
    source: str,
    as_of: Optional[str] = None,
    scope: Literal["system", "client", "branch"] = "client",
    sample_size: Optional[int] = None,
    note: Optional[str] = None,
) -> ConsoleMetricFactMeta:
    return ConsoleMetricFactMeta(
        kind=kind,
        source=source,
        as_of=as_of,
        scope=scope,
        sample_size=sample_size,
        note=note,
    )


def _resolve_owner_mode_profile(mode: ConsoleOwnerMode) -> tuple[str, ConsoleOwnerOperationSettingsPatch, list[str]]:
    profile = _OWNER_MODE_CONFIG[mode]
    label = str(profile["label"])
    settings_patch = profile["settings_patch"]
    warnings = profile.get("warnings")
    return (
        label,
        settings_patch if isinstance(settings_patch, ConsoleOwnerOperationSettingsPatch) else _DEFAULT_OWNER_MODE_SETTINGS,
        list(warnings) if isinstance(warnings, list) else [],
    )


def _normalize_owner_settings(settings: Optional[ClientSettings]) -> ConsoleOwnerOperationSettingsPatch:
    if settings is None:
        return _DEFAULT_OWNER_MODE_SETTINGS.model_copy(deep=True)

    reminder_1 = settings.reminder_timeout_1 or _DEFAULT_OWNER_MODE_SETTINGS.reminder_1_minutes
    reminder_2 = settings.reminder_timeout_2 or _DEFAULT_OWNER_MODE_SETTINGS.reminder_2_minutes
    escalation = settings.auto_close_timeout or _DEFAULT_OWNER_MODE_SETTINGS.escalation_timeout_minutes
    return ConsoleOwnerOperationSettingsPatch(
        reminder_1_minutes=reminder_1,
        reminder_2_minutes=reminder_2,
        escalation_timeout_minutes=escalation,
    )


def _ensure_client_settings_row(db: Session, *, client_id: UUID) -> ClientSettings:
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client_id).first()
    if settings is None:
        settings = ClientSettings(client_id=client_id)
        db.add(settings)
    return settings


def _apply_owner_operation_settings(
    *,
    settings: ClientSettings,
    patch: ConsoleOwnerOperationSettingsPatch,
) -> None:
    settings.reminder_timeout_1 = patch.reminder_1_minutes
    settings.reminder_timeout_2 = patch.reminder_2_minutes
    settings.auto_close_timeout = patch.escalation_timeout_minutes


def _collect_owner_operation_metrics(
    *,
    db: Session,
    context: ConsoleAuthContext,
    now: datetime,
) -> tuple[ConsoleOwnerOperationMetricSnapshot, dict[str, ConsoleMetricFactMeta]]:
    allowed_branch_ids = _resolve_branch_scope(context)
    scope: Literal["system", "client", "branch"] = "branch" if allowed_branch_ids is not None else "client"

    outbox_query = db.query(OutboxMessage).filter(OutboxMessage.client_id == context.client.id)
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            outbox_backlog = 0
        else:
            outbox_query = outbox_query.filter(OutboxMessage.branch_id.in_(allowed_branch_ids))
            outbox_backlog = outbox_query.filter(OutboxMessage.status.in_(["PENDING", "PROCESSING"])).count()
    else:
        outbox_backlog = outbox_query.filter(OutboxMessage.status.in_(["PENDING", "PROCESSING"])).count()

    handover_query = db.query(Handover).filter(Handover.client_id == context.client.id)
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            unresolved_older_than_60m = 0
        else:
            handover_query = handover_query.join(
                Conversation,
                Handover.conversation_id == Conversation.id,
            ).filter(Conversation.branch_id.in_(allowed_branch_ids))
            unresolved_older_than_60m = handover_query.filter(
                Handover.status.in_(["pending", "active"]),
                Handover.created_at < (now - timedelta(minutes=60)),
            ).count()
    else:
        unresolved_older_than_60m = handover_query.filter(
            Handover.status.in_(["pending", "active"]),
            Handover.created_at < (now - timedelta(minutes=60)),
        ).count()

    analytics_scope_limited = allowed_branch_ids is not None
    analytics_row = _load_latest_analytics_row(
        db=db,
        client_id=context.client.id,
        metric_date=now.date(),
        analytics_scope_limited=analytics_scope_limited,
    )
    manager_median_response_seconds = _safe_float(
        analytics_row.get("manager_median_response_seconds") if analytics_row else None
    )
    metric_date = analytics_row.get("metric_date") if analytics_row else None
    analytics_as_of = metric_date.isoformat() if metric_date else now.date().isoformat()

    metric_meta = {
        "outbox_backlog": _build_metric_meta(
            kind="fact",
            source="outbox_messages",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=outbox_backlog,
        ),
        "unresolved_older_than_60m": _build_metric_meta(
            kind="fact",
            source="handovers",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=unresolved_older_than_60m,
        ),
        "manager_median_response_seconds": _build_metric_meta(
            kind="fact" if manager_median_response_seconds is not None else "missing",
            source="metrics_analytics_daily",
            as_of=analytics_as_of,
            scope=scope,
            sample_size=1 if manager_median_response_seconds is not None else None,
            note=(
                "company-level analytics unavailable in branch scope"
                if analytics_scope_limited and manager_median_response_seconds is None
                else None
            ),
        ),
    }
    snapshot = ConsoleOwnerOperationMetricSnapshot(
        outbox_backlog=outbox_backlog,
        unresolved_older_than_60m=unresolved_older_than_60m,
        manager_median_response_seconds=manager_median_response_seconds,
    )
    return snapshot, metric_meta


def _parse_owner_operation_settings(
    payload: dict,
    *,
    key: str,
) -> Optional[ConsoleOwnerOperationSettingsPatch]:
    raw = payload.get(key)
    if not isinstance(raw, dict):
        return None
    reminder_1 = _safe_int(raw.get("reminder_1_minutes"))
    reminder_2 = _safe_int(raw.get("reminder_2_minutes"))
    escalation = _safe_int(raw.get("escalation_timeout_minutes"))
    if not reminder_1 or not reminder_2 or not escalation:
        return None
    return ConsoleOwnerOperationSettingsPatch(
        reminder_1_minutes=reminder_1,
        reminder_2_minutes=reminder_2,
        escalation_timeout_minutes=escalation,
    )


def _parse_owner_operation_snapshot(
    payload: dict,
    *,
    key: str = "baseline",
) -> Optional[ConsoleOwnerOperationMetricSnapshot]:
    raw = payload.get(key)
    if not isinstance(raw, dict):
        return None
    outbox_backlog = _safe_int(raw.get("outbox_backlog"))
    unresolved_older_than_60m = _safe_int(raw.get("unresolved_older_than_60m"))
    manager_median = _safe_float(raw.get("manager_median_response_seconds"))
    if outbox_backlog is None or unresolved_older_than_60m is None:
        return None
    return ConsoleOwnerOperationMetricSnapshot(
        outbox_backlog=outbox_backlog,
        unresolved_older_than_60m=unresolved_older_than_60m,
        manager_median_response_seconds=manager_median,
    )


def _load_owner_mode_apply_event(
    *,
    db: Session,
    context: ConsoleAuthContext,
    operation_id: Optional[UUID] = None,
) -> Optional[AuditEvent]:
    query = db.query(AuditEvent).filter(
        AuditEvent.client_id == context.client.id,
        AuditEvent.event_type == "owner_mode_apply",
    )
    allowed_branch_ids = _resolve_branch_scope(context)
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            return None
        query = query.filter(AuditEvent.branch_id.in_(allowed_branch_ids))

    if operation_id is not None:
        return query.filter(AuditEvent.id == operation_id).first()
    return query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).first()


def _build_owner_operation_metric_delta(
    *,
    baseline: Optional[float],
    current: Optional[float],
) -> ConsoleOwnerOperationMetricDelta:
    if baseline is None or current is None:
        return ConsoleOwnerOperationMetricDelta(
            baseline=baseline,
            current=current,
            delta=None,
            trend="unknown",
        )
    delta = round(current - baseline, 3)
    if abs(delta) < 1e-9:
        trend = "stable"
    elif current < baseline:
        trend = "down"
    else:
        trend = "up"
    return ConsoleOwnerOperationMetricDelta(
        baseline=baseline,
        current=current,
        delta=delta,
        trend=trend,
    )


def _summarize_owner_operation_delta(metrics: dict[str, ConsoleOwnerOperationMetricDelta]) -> Literal[
    "improved",
    "regressed",
    "mixed_or_stable",
]:
    improved = 0
    regressed = 0
    for metric in metrics.values():
        if metric.trend == "down":
            improved += 1
        elif metric.trend == "up":
            regressed += 1
    if improved > 0 and regressed == 0:
        return "improved"
    if regressed > 0 and improved == 0:
        return "regressed"
    return "mixed_or_stable"


def _summarize_daily_visit_outcomes(status_rows: list[object]) -> tuple[int, int, int, int, int, Optional[float]]:
    status_counts: dict[str, int] = {}
    for row in status_rows:
        status_key = str(getattr(row, "status", "") or "").upper()
        status_counts[status_key] = int(getattr(row, "count", 0) or 0)

    scheduled_visits_today = int(sum(status_counts.values()))
    cancelled_visits_today = int(status_counts.get("CANCELLED", 0))
    no_show_visits_today = int(status_counts.get("NO_SHOW", 0))
    # Treat legacy CHECKED_IN as arrived for backward-compatible KPI.
    arrived_visits_today = int(status_counts.get("COMPLETED", 0) + status_counts.get("CHECKED_IN", 0))
    effective_planned_today = max(0, scheduled_visits_today - cancelled_visits_today)
    arrival_rate_percent = (
        round((arrived_visits_today / effective_planned_today) * 100, 1)
        if effective_planned_today > 0
        else None
    )
    return (
        scheduled_visits_today,
        arrived_visits_today,
        no_show_visits_today,
        cancelled_visits_today,
        effective_planned_today,
        arrival_rate_percent,
    )


def _compute_no_show_followup_pending(
    no_show_appointment_ids: list[UUID],
    followup_appointment_ids: list[UUID],
) -> int:
    no_show_set = {appointment_id for appointment_id in no_show_appointment_ids if appointment_id}
    if not no_show_set:
        return 0
    followed_up_set = {
        appointment_id for appointment_id in followup_appointment_ids if appointment_id in no_show_set
    }
    return max(0, len(no_show_set) - len(followed_up_set))


@router.get(
    "/business/summary",
    response_model=ConsoleBusinessSummaryResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def get_business_summary(
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleBusinessSummaryResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "business",
        "read",
        message="Only owner/admin can access business summary",
    )

    now = datetime.now(timezone.utc)
    day_start = datetime.combine(now.date(), time.min).replace(tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    outbox_failed_window_start = now - timedelta(hours=24)
    allowed_branch_ids = _resolve_branch_scope(context)

    handover_base = db.query(Handover).filter(Handover.client_id == context.client.id)
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            pending_cases = 0
            active_cases = 0
            unresolved_cases = 0
            oldest_unresolved_minutes = None
        else:
            handover_base = handover_base.join(
                Conversation,
                Handover.conversation_id == Conversation.id,
            ).filter(Conversation.branch_id.in_(allowed_branch_ids))
            pending_cases = handover_base.filter(Handover.status == "pending").count()
            active_cases = handover_base.filter(Handover.status == "active").count()
            unresolved_cases = pending_cases + active_cases
            oldest_unresolved_row = (
                handover_base.filter(Handover.status.in_(["pending", "active"]))
                .order_by(Handover.created_at.asc())
                .first()
            )
            oldest_unresolved_minutes = None
            if oldest_unresolved_row and oldest_unresolved_row.created_at:
                delta_seconds = (now - oldest_unresolved_row.created_at).total_seconds()
                oldest_unresolved_minutes = max(0, int(delta_seconds // 60))
    else:
        pending_cases = handover_base.filter(Handover.status == "pending").count()
        active_cases = handover_base.filter(Handover.status == "active").count()
        unresolved_cases = pending_cases + active_cases
        oldest_unresolved_row = (
            handover_base.filter(Handover.status.in_(["pending", "active"]))
            .order_by(Handover.created_at.asc())
            .first()
        )
        oldest_unresolved_minutes = None
        if oldest_unresolved_row and oldest_unresolved_row.created_at:
            delta_seconds = (now - oldest_unresolved_row.created_at).total_seconds()
            oldest_unresolved_minutes = max(0, int(delta_seconds // 60))

    outbox_query = db.query(OutboxMessage).filter(OutboxMessage.client_id == context.client.id)
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            outbox_backlog = 0
            outbox_failed_24h = 0
        else:
            outbox_query = outbox_query.filter(OutboxMessage.branch_id.in_(allowed_branch_ids))
            outbox_backlog = outbox_query.filter(
                OutboxMessage.status.in_(["PENDING", "PROCESSING"])
            ).count()
            outbox_failed_24h = outbox_query.filter(
                OutboxMessage.status == "FAILED",
                OutboxMessage.created_at >= outbox_failed_window_start,
                OutboxMessage.created_at < day_end,
                _outbox_actionable_failure_filter(),
            ).count()
    else:
        outbox_backlog = outbox_query.filter(
            OutboxMessage.status.in_(["PENDING", "PROCESSING"])
        ).count()
        outbox_failed_24h = outbox_query.filter(
            OutboxMessage.status == "FAILED",
            OutboxMessage.created_at >= outbox_failed_window_start,
            OutboxMessage.created_at < day_end,
            _outbox_actionable_failure_filter(),
        ).count()

    appointments_query = db.query(
        Appointment.status,
        func.count().label("count"),
    ).filter(
        Appointment.client_id == context.client.id,
        Appointment.start_at >= day_start,
        Appointment.start_at < day_end,
    )
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            appointment_status_rows: list[object] = []
        else:
            appointment_status_rows = (
                appointments_query
                .filter(Appointment.branch_id.in_(allowed_branch_ids))
                .group_by(Appointment.status)
                .all()
            )
    else:
        appointment_status_rows = appointments_query.group_by(Appointment.status).all()

    (
        scheduled_visits_today,
        arrived_visits_today,
        no_show_visits_today,
        cancelled_visits_today,
        effective_planned_today,
        arrival_rate_percent,
    ) = _summarize_daily_visit_outcomes(appointment_status_rows)
    reminder_failures_query = db.query(ReminderJob).filter(
        ReminderJob.client_id == context.client.id,
        ReminderJob.status == "FAILED",
        ReminderJob.updated_at >= day_start,
        ReminderJob.updated_at < day_end,
    )
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            reminder_delivery_failures_today = 0
        else:
            reminder_delivery_failures_today = reminder_failures_query.filter(
                ReminderJob.branch_id.in_(allowed_branch_ids)
            ).count()
    else:
        reminder_delivery_failures_today = reminder_failures_query.count()

    no_show_query = db.query(Appointment.id).filter(
        Appointment.client_id == context.client.id,
        Appointment.status == "NO_SHOW",
        Appointment.start_at >= day_start,
        Appointment.start_at < day_end,
    )
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            no_show_appointment_ids: list[UUID] = []
        else:
            no_show_appointment_ids = [
                row[0]
                for row in no_show_query.filter(Appointment.branch_id.in_(allowed_branch_ids)).all()
                if row and row[0]
            ]
    else:
        no_show_appointment_ids = [row[0] for row in no_show_query.all() if row and row[0]]

    followup_appointment_ids: list[UUID] = []
    if no_show_appointment_ids:
        followup_appointment_ids = [
            row[0]
            for row in (
                db.query(AppointmentAudit.appointment_id)
                .filter(
                    AppointmentAudit.appointment_id.in_(no_show_appointment_ids),
                    AppointmentAudit.action == "no_show_followup",
                )
                .distinct()
                .all()
            )
            if row and row[0]
        ]

    no_show_followup_pending = _compute_no_show_followup_pending(
        no_show_appointment_ids,
        followup_appointment_ids,
    )

    analytics_row = db.execute(
        text(
            """
            SELECT metric_date, first_response_p90_seconds
            FROM metrics_analytics_daily
            WHERE client_id = :client_id
              AND metric_date <= :metric_date
            ORDER BY metric_date DESC
            LIMIT 1
            """
        ),
        {"client_id": context.client.id, "metric_date": now.date()},
    ).mappings().first()
    metric_date = None
    if analytics_row and analytics_row.get("metric_date") is not None:
        metric_date = analytics_row.get("metric_date")
    first_response_p90_seconds = (
        float(analytics_row.get("first_response_p90_seconds"))
        if analytics_row and analytics_row.get("first_response_p90_seconds") is not None
        else None
    )
    scope: Literal["system", "client", "branch"] = "branch" if allowed_branch_ids is not None else "client"
    analytics_as_of = metric_date.isoformat() if metric_date is not None else now.date().isoformat()

    status, status_label = _derive_business_status(
        outbox_backlog=outbox_backlog,
        outbox_failed_24h=outbox_failed_24h,
        unresolved_cases=unresolved_cases,
    )
    actions = _build_owner_actions(
        outbox_backlog=outbox_backlog,
        outbox_failed_24h=outbox_failed_24h,
        unresolved_cases=unresolved_cases,
        first_response_p90_seconds=first_response_p90_seconds,
    )
    if reminder_delivery_failures_today > 0:
        actions.insert(
            0,
            ConsoleBusinessActionItem(
                id="reminder_delivery_failures",
                severity="critical" if reminder_delivery_failures_today >= 10 else "warn",
                title="Проверьте сбои напоминаний",
                description=(
                    f"Сегодня напоминания завершились ошибкой {reminder_delivery_failures_today} раз. "
                    "Проверьте Ops reminders."
                ),
                href="/ops",
            ),
        )
    if no_show_followup_pending > 0:
        actions.insert(
            0,
            ConsoleBusinessActionItem(
                id="no_show_followup_pending",
                severity="critical" if no_show_followup_pending >= 5 else "warn",
                title="Разберите неявки без follow-up",
                description=(
                    f"По {no_show_followup_pending} неявкам еще нет действия менеджера. "
                    "Откройте календарь и обработайте клиентов."
                ),
                href="/calendar",
            ),
        )
    if effective_planned_today >= 5 and no_show_visits_today > 0:
        no_show_rate = no_show_visits_today / effective_planned_today
        if no_show_rate >= 0.3:
            actions.insert(
                0,
                ConsoleBusinessActionItem(
                    id="reduce_no_show",
                    severity="critical" if no_show_rate >= 0.5 else "warn",
                    title="Снизьте неявки по записям",
                    description=(
                        f"Сегодня не пришли {no_show_visits_today} из {effective_planned_today} "
                        "запланированных визитов. Проверьте календарь и напоминания."
                    ),
                    href="/calendar",
                ),
            )
    metric_meta = {
        "outbox_backlog": _build_metric_meta(
            kind="fact",
            source="outbox_messages",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=outbox_backlog,
        ),
        "outbox_failed_24h": _build_metric_meta(
            kind="fact",
            source="outbox_messages",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=outbox_failed_24h,
        ),
        "pending_cases": _build_metric_meta(
            kind="fact",
            source="handovers",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=pending_cases,
        ),
        "active_cases": _build_metric_meta(
            kind="fact",
            source="handovers",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=active_cases,
        ),
        "unresolved_cases": _build_metric_meta(
            kind="fact",
            source="handovers",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=unresolved_cases,
        ),
        "oldest_unresolved_minutes": _build_metric_meta(
            kind="fact" if oldest_unresolved_minutes is not None else "missing",
            source="handovers",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=1 if oldest_unresolved_minutes is not None else None,
            note="no unresolved cases" if oldest_unresolved_minutes is None else None,
        ),
        "first_response_p90_seconds": _build_metric_meta(
            kind="fact" if first_response_p90_seconds is not None else "missing",
            source="metrics_analytics_daily",
            as_of=analytics_as_of,
            scope=scope,
            sample_size=1 if first_response_p90_seconds is not None else None,
        ),
        "scheduled_visits_today": _build_metric_meta(
            kind="fact",
            source="appointments",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=scheduled_visits_today,
        ),
        "arrived_visits_today": _build_metric_meta(
            kind="fact",
            source="appointments",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=arrived_visits_today,
        ),
        "no_show_visits_today": _build_metric_meta(
            kind="fact",
            source="appointments",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=no_show_visits_today,
        ),
        "cancelled_visits_today": _build_metric_meta(
            kind="fact",
            source="appointments",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=cancelled_visits_today,
        ),
        "arrival_rate_percent": _build_metric_meta(
            kind="fact" if arrival_rate_percent is not None else "missing",
            source="appointments",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=effective_planned_today if arrival_rate_percent is not None else None,
            note="no planned visits today" if arrival_rate_percent is None else None,
        ),
        "reminder_delivery_failures_today": _build_metric_meta(
            kind="fact",
            source="reminder_jobs",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=reminder_delivery_failures_today,
        ),
        "no_show_followup_pending": _build_metric_meta(
            kind="fact",
            source="appointments+appointment_audit",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=no_show_followup_pending,
        ),
    }

    return ConsoleBusinessSummaryResponse(
        generated_at=now.isoformat(),
        status=status,
        status_label=status_label,
        scheduled_visits_today=scheduled_visits_today,
        arrived_visits_today=arrived_visits_today,
        no_show_visits_today=no_show_visits_today,
        cancelled_visits_today=cancelled_visits_today,
        arrival_rate_percent=arrival_rate_percent,
        reminder_delivery_failures_today=reminder_delivery_failures_today,
        no_show_followup_pending=no_show_followup_pending,
        outbox_backlog=outbox_backlog,
        outbox_failed_24h=outbox_failed_24h,
        pending_cases=pending_cases,
        active_cases=active_cases,
        unresolved_cases=unresolved_cases,
        oldest_unresolved_minutes=oldest_unresolved_minutes,
        first_response_p90_seconds=first_response_p90_seconds,
        actions=actions,
        metric_meta=metric_meta,
    )


@router.get(
    "/business/incidents",
    response_model=ConsoleIncidentListResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_business_incidents(
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleIncidentListResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "business",
        "read",
        message="Only owner/admin can access business incidents",
    )

    now = datetime.now(timezone.utc)
    outbox_failed_window_start = now - timedelta(hours=24)
    allowed_branch_ids = _resolve_branch_scope(context)
    scope: Literal["client", "branch"] = "branch" if allowed_branch_ids is not None else "client"

    outbox_query = db.query(OutboxMessage).filter(OutboxMessage.client_id == context.client.id)
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            outbox_backlog = 0
            outbox_failed_24h = 0
            latest_failed_error = None
        else:
            outbox_query = outbox_query.filter(OutboxMessage.branch_id.in_(allowed_branch_ids))
            outbox_backlog = outbox_query.filter(
                OutboxMessage.status.in_(["PENDING", "PROCESSING"])
            ).count()
            outbox_failed_24h = outbox_query.filter(
                OutboxMessage.status == "FAILED",
                OutboxMessage.created_at >= outbox_failed_window_start,
                _outbox_actionable_failure_filter(),
            ).count()
            latest_failed_row = (
                outbox_query.filter(
                    OutboxMessage.status == "FAILED",
                    OutboxMessage.last_error.isnot(None),
                    ~OutboxMessage.last_error.ilike(f"{_OUTBOX_ARCHIVED_REASON_PREFIX}%"),
                )
                .order_by(OutboxMessage.updated_at.desc(), OutboxMessage.created_at.desc())
                .first()
            )
            latest_failed_error = (
                _normalize_optional_text(getattr(latest_failed_row, "last_error", None))
                if latest_failed_row
                else None
            )
    else:
        outbox_backlog = outbox_query.filter(
            OutboxMessage.status.in_(["PENDING", "PROCESSING"])
        ).count()
        outbox_failed_24h = outbox_query.filter(
            OutboxMessage.status == "FAILED",
            OutboxMessage.created_at >= outbox_failed_window_start,
            _outbox_actionable_failure_filter(),
        ).count()
        latest_failed_row = (
            outbox_query.filter(
                OutboxMessage.status == "FAILED",
                OutboxMessage.last_error.isnot(None),
                ~OutboxMessage.last_error.ilike(f"{_OUTBOX_ARCHIVED_REASON_PREFIX}%"),
            )
            .order_by(OutboxMessage.updated_at.desc(), OutboxMessage.created_at.desc())
            .first()
        )
        latest_failed_error = (
            _normalize_optional_text(getattr(latest_failed_row, "last_error", None))
            if latest_failed_row
            else None
        )

    handover_query = db.query(Handover).filter(
        Handover.client_id == context.client.id,
        Handover.status.in_(["pending", "active"]),
    )
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            pending_handovers = 0
        else:
            handover_query = handover_query.join(
                Conversation,
                Handover.conversation_id == Conversation.id,
            ).filter(Conversation.branch_id.in_(allowed_branch_ids))
            pending_handovers = handover_query.count()
    else:
        pending_handovers = handover_query.count()

    degraded_query = db.query(func.count(Branch.id)).filter(
        Branch.client_id == context.client.id,
        Branch.is_active.is_(True),
        func.lower(func.coalesce(Branch.integration_state, "ok")) == "degraded",
    )
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            integration_degraded_branches = 0
        else:
            degraded_query = degraded_query.filter(Branch.id.in_(allowed_branch_ids))
            integration_degraded_branches = int(degraded_query.scalar() or 0)
    else:
        integration_degraded_branches = int(degraded_query.scalar() or 0)

    signals = _IncidentSignals(
        outbox_backlog=outbox_backlog,
        outbox_failed_24h=outbox_failed_24h,
        pending_handovers=pending_handovers,
        integration_degraded_branches=integration_degraded_branches,
        last_error=latest_failed_error,
    )
    items = _build_scope_incident_items(
        scope=scope,
        signals=signals,
        detected_at=now,
        client_id=context.client.id,
        client_slug=context.client.name,
        branch_id=context.effective_branch_id,
        branch_ids=allowed_branch_ids,
        platform_scope=False,
    )
    state_map = _load_incident_state_map(
        db,
        client_id=context.client.id,
        incident_ids=[item.id for item in items],
        allowed_branch_ids=allowed_branch_ids,
    )
    _apply_incident_state_map(items, state_map=state_map)
    return ConsoleIncidentListResponse(
        generated_at=now.isoformat(),
        scope=scope,
        summary=_build_incident_summary(items),
        items=items,
    )


_DEFAULT_STARTER_INCLUDED_MESSAGES = 1000
_DEFAULT_STARTER_INCLUDED_WHATSAPP_CHANNELS = 1


def _parse_subscription_meter_limit(value: object) -> Optional[int]:
    if isinstance(value, bool):
        return 1 if value else 0
    parsed = _safe_int(value)
    if parsed is None or parsed < 0:
        return None
    return parsed


def _extract_subscription_channel_limit(payload: dict, *, channel: str) -> Optional[int]:
    if not isinstance(payload, dict):
        return None
    direct_keys = (
        f"{channel}_numbers",
        f"{channel}_number_limit",
        f"{channel}_channels",
        f"{channel}_channel_limit",
        f"{channel}_limit",
    )
    for key in direct_keys:
        parsed = _parse_subscription_meter_limit(payload.get(key))
        if parsed is not None:
            return parsed
    channels_map = payload.get("channels")
    if isinstance(channels_map, dict):
        parsed = _parse_subscription_meter_limit(channels_map.get(channel))
        if parsed is not None:
            return parsed
    return None


def _resolve_subscription_channel_limit(
    *,
    context: ConsoleAuthContext,
    channel: Literal["whatsapp", "telegram", "instagram"],
    onboarding_enabled: Optional[bool],
) -> tuple[Optional[int], str]:
    company = next(
        (item for item in context.companies if item.id == context.client.company_id),
        None,
    )
    company_billing = company.billing_info if company and isinstance(company.billing_info, dict) else {}
    client_config = context.client.config if isinstance(context.client.config, dict) else {}
    client_billing = client_config.get("billing") if isinstance(client_config.get("billing"), dict) else {}
    sources: list[tuple[str, dict]] = [
        ("company_billing_info", company_billing),
        ("client_config", client_billing),
    ]
    for source_name, source_payload in sources:
        if not isinstance(source_payload, dict):
            continue
        nested_subscription = source_payload.get("subscription")
        candidate_maps = [source_payload]
        if isinstance(nested_subscription, dict):
            candidate_maps.insert(0, nested_subscription)
        for payload in candidate_maps:
            parsed = _extract_subscription_channel_limit(payload, channel=channel)
            if parsed is not None:
                return parsed, source_name
    if onboarding_enabled is True:
        return 1, "onboarding_contract"
    if onboarding_enabled is False:
        return 0, "onboarding_contract"
    return None, "unknown"


def _resolve_subscription_count_meter_status(
    *,
    included: Optional[int],
    used: int,
    warn_ratio: float = 0.8,
) -> tuple[Literal["ok", "warning", "limit_reached", "over_limit", "not_included", "unknown"], Optional[int]]:
    if included is None:
        return "unknown", None
    if included <= 0:
        if used > 0:
            return "over_limit", 0
        return "not_included", 0
    if used > included:
        return "over_limit", 0
    remaining = max(0, included - used)
    if used == included:
        return "limit_reached", remaining
    threshold = included * warn_ratio
    if used >= threshold:
        return "warning", remaining
    return "ok", remaining


def _resolve_subscription_toggle_meter_status(
    *,
    included: Optional[int],
    used: int,
) -> Literal["ok", "over_limit", "not_included", "included_not_configured", "unknown"]:
    if included is None:
        return "unknown"
    if included <= 0:
        if used > 0:
            return "over_limit"
        return "not_included"
    if used <= 0:
        return "included_not_configured"
    return "ok"


def _resolve_subscription_payment_status_message(
    *,
    payment_status: str,
    payment_confirmed_at: Optional[str],
) -> str:
    if payment_status == "confirmed":
        if payment_confirmed_at:
            return f"Оплата подтверждена: {payment_confirmed_at}."
        return "Оплата подтверждена."
    if payment_status == "pending":
        return "Оплата в ожидании подтверждения. Проверьте реквизиты и статус у платформы."
    if payment_status == "rejected":
        return "Оплата отклонена. Нужна повторная проверка и подтверждение."
    return "Статус оплаты не заполнен в онбординге."


def _append_subscription_contract_gap(
    gaps: list[ConsoleSubscriptionContractGap],
    *,
    code: str,
    message: str,
    severity: Literal["critical", "warn", "info"],
) -> None:
    if any(item.code == code for item in gaps):
        return
    gaps.append(
        ConsoleSubscriptionContractGap(
            code=code,
            message=message,
            severity=severity,
        )
    )


def _resolve_subscription_contract_health(
    *,
    plan_name: Optional[str],
    contract_label: Optional[str],
    monthly_quota: Optional[int],
    quota_source: Literal["company_billing_info", "client_config", "unknown"],
    whatsapp_included: Optional[int],
    whatsapp_source: Literal["company_billing_info", "client_config", "onboarding_contract", "unknown"],
    whatsapp_used: int,
    payment_status: str,
    payment_status_source: Literal["onboarding_contract", "unknown"],
    has_active_onboarding_contract: bool,
) -> ConsoleSubscriptionContractHealth:
    gaps: list[ConsoleSubscriptionContractGap] = []

    if not _normalize_optional_text(plan_name) and not _normalize_optional_text(contract_label):
        _append_subscription_contract_gap(
            gaps,
            code="plan_missing",
            message="Не указан тариф или номер договора.",
            severity="warn",
        )
    if monthly_quota is None:
        _append_subscription_contract_gap(
            gaps,
            code="monthly_quota_missing",
            message="Не зафиксирован лимит сообщений в месяц.",
            severity="critical",
        )
    if whatsapp_included is None:
        _append_subscription_contract_gap(
            gaps,
            code="whatsapp_limit_missing",
            message="Не зафиксирован лимит WhatsApp-каналов.",
            severity="warn",
        )
    elif whatsapp_included <= 0 and whatsapp_used > 0:
        _append_subscription_contract_gap(
            gaps,
            code="whatsapp_contract_mismatch",
            message="Есть активные WhatsApp-каналы, но контрактный лимит равен нулю.",
            severity="critical",
        )
    if payment_status == "unknown":
        _append_subscription_contract_gap(
            gaps,
            code="payment_status_missing",
            message="Не заполнен статус оплаты в онбординге.",
            severity="warn",
        )

    known_signals = 0
    if _normalize_optional_text(plan_name) or _normalize_optional_text(contract_label):
        known_signals += 1
    if monthly_quota is not None:
        known_signals += 1
    if whatsapp_included is not None:
        known_signals += 1
    if payment_status != "unknown":
        known_signals += 1

    if not gaps:
        status: Literal["ok", "partial", "missing"] = "ok"
        summary = "Контракт заполнен: лимиты и оплата подтверждены."
    elif known_signals == 0:
        status = "missing"
        summary = "Контракт не заполнен: доступны только фактические данные использования."
    else:
        status = "partial"
        summary = "Контракт заполнен частично: часть лимитов или статусов отсутствует."

    return ConsoleSubscriptionContractHealth(
        status=status,
        summary=summary,
        gaps=gaps,
        quota_source=quota_source,
        whatsapp_source=whatsapp_source,
        payment_status_source=payment_status_source,
        has_active_onboarding_contract=has_active_onboarding_contract,
    )


def _append_subscription_action(
    actions: list[ConsoleBusinessActionItem],
    *,
    action_id: str,
    title: str,
    description: str,
    href: str,
    severity: Literal["critical", "warn", "info"],
) -> None:
    if any(item.id == action_id for item in actions):
        return
    actions.append(
        ConsoleBusinessActionItem(
            id=action_id,
            title=title,
            description=description,
            href=href,
            severity=severity,
        )
    )


@router.get(
    "/subscription/summary",
    response_model=ConsoleSubscriptionSummaryResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def get_subscription_summary(
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleSubscriptionSummaryResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "subscription",
        "read",
        message="Only owner/admin can access subscription summary",
    )

    now = datetime.now(timezone.utc)
    period_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if now.month == 12:
        period_end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        period_end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    allowed_branch_ids = _resolve_branch_scope(context)

    usage_query = db.query(OutboxMessage).filter(
        OutboxMessage.client_id == context.client.id,
        OutboxMessage.created_at >= period_start,
        OutboxMessage.created_at < period_end,
    )
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            usage_query = usage_query.filter(text("1 = 0"))
        else:
            usage_query = usage_query.filter(OutboxMessage.branch_id.in_(allowed_branch_ids))
    usage_query = _apply_billable_outbox_filters(usage_query)

    billable_messages = int(usage_query.count())
    evidence_rows = (
        usage_query.order_by(OutboxMessage.created_at.desc(), OutboxMessage.id.desc())
        .limit(25)
        .all()
    )

    branch_query = db.query(Branch).filter(Branch.client_id == context.client.id)
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            scoped_branches: list[Branch] = []
        else:
            scoped_branches = branch_query.filter(Branch.id.in_(list(allowed_branch_ids))).all()
    else:
        scoped_branches = branch_query.all()

    client_contract_record = _get_latest_onboarding_contract(
        db,
        client_id=context.client.id,
        scope="client",
        branch_id=None,
    )
    branch_contract_record = None
    if context.effective_branch_id:
        branch_contract_record = _get_latest_onboarding_contract(
            db,
            client_id=context.client.id,
            scope="branch",
            branch_id=context.effective_branch_id,
        )
    elif allowed_branch_ids is not None and len(allowed_branch_ids) == 1:
        only_branch_id = next(iter(allowed_branch_ids))
        branch_contract_record = _get_latest_onboarding_contract(
            db,
            client_id=context.client.id,
            scope="branch",
            branch_id=only_branch_id,
        )

    active_client_contract = (
        client_contract_record
        if client_contract_record and client_contract_record.status == "active"
        else None
    )
    active_branch_contract = (
        branch_contract_record
        if branch_contract_record and branch_contract_record.status == "active"
        else None
    )
    client_contract_payload = active_client_contract.payload_json if active_client_contract else None
    branch_contract_payload = active_branch_contract.payload_json if active_branch_contract else None
    effective_onboarding_payload: Optional[OnboardingContractPayload] = None
    if isinstance(client_contract_payload, dict) or isinstance(branch_contract_payload, dict):
        try:
            effective_onboarding_payload = OnboardingContractPayload.model_validate(
                merge_onboarding_contract(client_contract_payload, branch_contract_payload)
            )
        except ValidationError:
            effective_onboarding_payload = None

    payment_source = _resolve_onboarding_payment_source(
        client_record=active_client_contract,
        branch_record=active_branch_contract,
    )
    payment_status = payment_source.payment_status if payment_source else "unknown"
    payment_confirmed_at = (
        payment_source.payment_confirmed_at.isoformat()
        if payment_source and payment_source.payment_confirmed_at
        else None
    )
    payment_status_source: Literal["onboarding_contract", "unknown"] = (
        "onboarding_contract" if payment_source else "unknown"
    )

    client_capability_record = _get_latest_capability(
        db,
        client_id=context.client.id,
        scope="client",
        branch_id=None,
    )
    branch_capability_record = None
    if context.effective_branch_id:
        branch_capability_record = _get_latest_capability(
            db,
            client_id=context.client.id,
            scope="branch",
            branch_id=context.effective_branch_id,
        )
    elif allowed_branch_ids is not None and len(allowed_branch_ids) == 1:
        only_branch_id = next(iter(allowed_branch_ids))
        branch_capability_record = _get_latest_capability(
            db,
            client_id=context.client.id,
            scope="branch",
            branch_id=only_branch_id,
        )
    client_capability_payload = (
        client_capability_record.payload_json
        if client_capability_record and client_capability_record.status == "active"
        else None
    )
    branch_capability_payload = (
        branch_capability_record.payload_json
        if branch_capability_record and branch_capability_record.status == "active"
        else None
    )
    effective_capabilities = CapabilitiesPayload()
    if isinstance(client_capability_payload, dict) or isinstance(branch_capability_payload, dict):
        try:
            effective_capabilities = CapabilitiesPayload.model_validate(
                merge_capabilities(client_capability_payload, branch_capability_payload)
            )
        except ValidationError:
            effective_capabilities = CapabilitiesPayload()

    purchased_capabilities = (
        effective_onboarding_payload.purchased if effective_onboarding_payload else CapabilitiesPayload()
    )
    has_contract_entitlements = effective_onboarding_payload is not None
    onboarding_whatsapp_enabled = (
        purchased_capabilities.channels.whatsapp if has_contract_entitlements else None
    )
    onboarding_telegram_enabled = (
        purchased_capabilities.channels.telegram if has_contract_entitlements else None
    )
    onboarding_instagram_enabled = (
        purchased_capabilities.channels.instagram if has_contract_entitlements else None
    )
    plan_name, contract_label, currency, monthly_quota, quota_source = _resolve_subscription_contract_info(context)

    elapsed_days = max(1, (now.date() - period_start.date()).days + 1)
    total_days = max(1, (period_end.date() - period_start.date()).days)
    projected_month_total = int(round((billable_messages / elapsed_days) * total_days))
    next_billing_date = period_end.date().isoformat()

    remaining_quota = None
    usage_percent = None
    over_quota = False
    projected_remaining_quota = None
    projected_over_quota = False
    projected_overage_messages = None
    if monthly_quota is not None and monthly_quota > 0:
        remaining_quota = max(0, monthly_quota - billable_messages)
        usage_percent = round((billable_messages / monthly_quota) * 100, 1)
        over_quota = billable_messages > monthly_quota
        projected_remaining_quota = monthly_quota - projected_month_total
        projected_over_quota = projected_month_total > monthly_quota
        projected_overage_messages = (
            max(0, projected_month_total - monthly_quota) if projected_over_quota else 0
        )
    quota_alert_level, quota_alert_message = _resolve_subscription_alert(
        monthly_quota=monthly_quota,
        usage_percent=usage_percent,
        over_quota=over_quota,
        projected_over_quota=projected_over_quota,
    )
    default_plan = ConsoleSubscriptionPlanDefaults(
        plan_name="Starter",
        included_messages=_DEFAULT_STARTER_INCLUDED_MESSAGES,
        included_whatsapp_channels=_DEFAULT_STARTER_INCLUDED_WHATSAPP_CHANNELS,
        source="STRATEGY/PRODUCT.md",
        reference_only=True,
    )
    active_branches = [branch for branch in scoped_branches if branch.is_active]
    whatsapp_used = sum(1 for branch in active_branches if _normalize_optional_text(branch.instance_id))
    telegram_used = sum(1 for branch in active_branches if _normalize_optional_text(branch.telegram_chat_id))
    instagram_used = 0

    whatsapp_included, whatsapp_source = _resolve_subscription_channel_limit(
        context=context,
        channel="whatsapp",
        onboarding_enabled=onboarding_whatsapp_enabled,
    )
    whatsapp_note = None
    if whatsapp_included is None:
        whatsapp_note = "Лимит WhatsApp не подтвержден в контракте. Starter-план показывается только как справка."
    whatsapp_status, whatsapp_remaining = _resolve_subscription_count_meter_status(
        included=whatsapp_included,
        used=whatsapp_used,
    )

    telegram_included, telegram_source = _resolve_subscription_channel_limit(
        context=context,
        channel="telegram",
        onboarding_enabled=onboarding_telegram_enabled,
    )
    telegram_status, telegram_remaining = _resolve_subscription_count_meter_status(
        included=telegram_included,
        used=telegram_used,
    )

    instagram_included, instagram_source = _resolve_subscription_channel_limit(
        context=context,
        channel="instagram",
        onboarding_enabled=onboarding_instagram_enabled,
    )
    instagram_status, instagram_remaining = _resolve_subscription_count_meter_status(
        included=instagram_included,
        used=instagram_used,
    )

    messages_meter_included = monthly_quota if monthly_quota is not None and monthly_quota > 0 else None
    messages_meter_source = (
        f"subscription_contract:{quota_source}"
        if messages_meter_included is not None
        else "subscription_contract:unknown"
    )
    messages_meter_note = None
    if messages_meter_included is None:
        messages_meter_note = "Лимит сообщений не подтвержден в контракте. Billing показывает только факт отправок."
    messages_meter_status, messages_meter_remaining = _resolve_subscription_count_meter_status(
        included=messages_meter_included,
        used=billable_messages,
    )

    calendar_included = None
    if has_contract_entitlements:
        calendar_included = 1 if purchased_capabilities.providers.calendar_provider not in (None, "none") else 0
    calendar_used = 1 if effective_capabilities.providers.calendar_provider not in (None, "none") else 0
    calendar_status = _resolve_subscription_toggle_meter_status(included=calendar_included, used=calendar_used)

    crm_included = None
    if has_contract_entitlements:
        crm_included = 1 if purchased_capabilities.providers.crm_provider not in (None, "none") else 0
    crm_used = 1 if effective_capabilities.providers.crm_provider not in (None, "none") else 0
    crm_status = _resolve_subscription_toggle_meter_status(included=crm_included, used=crm_used)

    knowledge_included = None
    if has_contract_entitlements:
        knowledge_included = 1 if purchased_capabilities.features.knowledge_upload is True else 0
    knowledge_used = 1 if effective_capabilities.features.knowledge_upload is True else 0
    knowledge_status = _resolve_subscription_toggle_meter_status(included=knowledge_included, used=knowledge_used)

    analytics_included = None
    if has_contract_entitlements:
        analytics_included = 1 if purchased_capabilities.features.analytics is True else 0
    analytics_used = 1 if effective_capabilities.features.analytics is True else 0
    analytics_status = _resolve_subscription_toggle_meter_status(included=analytics_included, used=analytics_used)

    auto_learn_included = None
    if has_contract_entitlements:
        auto_learn_included = 1 if purchased_capabilities.features.auto_learn is True else 0
    auto_learn_used = 1 if effective_capabilities.features.auto_learn is True else 0
    auto_learn_status = _resolve_subscription_toggle_meter_status(
        included=auto_learn_included,
        used=auto_learn_used,
    )

    provider_binding_lifecycle = _build_provider_binding_lifecycle_map(
        db,
        client_ids=[context.client.id],
        branches=scoped_branches,
        now=now,
    )
    binding_critical_total = sum(
        1 for lifecycle in provider_binding_lifecycle.values() if lifecycle.alert_state == "critical"
    )
    binding_warn_total = sum(
        1 for lifecycle in provider_binding_lifecycle.values() if lifecycle.alert_state == "warn"
    )
    if binding_critical_total > 0:
        critical_note = f"{binding_critical_total} канал(ов) WhatsApp требует срочного внимания."
        whatsapp_note = f"{whatsapp_note} {critical_note}".strip() if whatsapp_note else critical_note
    elif binding_warn_total > 0:
        warn_note = f"{binding_warn_total} канал(ов) WhatsApp требуют плановой проверки."
        whatsapp_note = f"{whatsapp_note} {warn_note}".strip() if whatsapp_note else warn_note

    contract_health = _resolve_subscription_contract_health(
        plan_name=plan_name,
        contract_label=contract_label,
        monthly_quota=monthly_quota,
        quota_source=quota_source,
        whatsapp_included=whatsapp_included,
        whatsapp_source=whatsapp_source,
        whatsapp_used=whatsapp_used,
        payment_status=payment_status,
        payment_status_source=payment_status_source,
        has_active_onboarding_contract=bool(active_client_contract or active_branch_contract),
    )

    meters = [
        ConsoleSubscriptionMeterItem(
            key="bot_messages",
            label="Сообщения бота",
            meter_type="messages",
            included=messages_meter_included,
            used=billable_messages,
            remaining=messages_meter_remaining,
            status=messages_meter_status,
            source=messages_meter_source,
            note=messages_meter_note,
        ),
        ConsoleSubscriptionMeterItem(
            key="whatsapp_channels",
            label="WhatsApp каналы",
            meter_type="channels",
            included=whatsapp_included,
            used=whatsapp_used,
            remaining=whatsapp_remaining,
            status=whatsapp_status,
            source=whatsapp_source,
            note=whatsapp_note,
        ),
        ConsoleSubscriptionMeterItem(
            key="telegram_channels",
            label="Telegram каналы",
            meter_type="channels",
            included=telegram_included,
            used=telegram_used,
            remaining=telegram_remaining,
            status=telegram_status,
            source=telegram_source,
        ),
        ConsoleSubscriptionMeterItem(
            key="instagram_channels",
            label="Instagram каналы",
            meter_type="channels",
            included=instagram_included,
            used=instagram_used,
            remaining=instagram_remaining,
            status=instagram_status,
            source=instagram_source,
            note="Канал поддерживается контрактно, но runtime подключение проверяется отдельно.",
        ),
        ConsoleSubscriptionMeterItem(
            key="calendar_integration",
            label="Календарная интеграция",
            meter_type="addon",
            included=calendar_included,
            used=calendar_used,
            remaining=max(0, calendar_included - calendar_used) if calendar_included is not None else None,
            status=calendar_status,
            source="onboarding_contract.purchased.providers.calendar_provider",
        ),
        ConsoleSubscriptionMeterItem(
            key="crm_integration",
            label="CRM интеграция",
            meter_type="addon",
            included=crm_included,
            used=crm_used,
            remaining=max(0, crm_included - crm_used) if crm_included is not None else None,
            status=crm_status,
            source="onboarding_contract.purchased.providers.crm_provider",
        ),
        ConsoleSubscriptionMeterItem(
            key="knowledge_upload",
            label="Загрузка знаний",
            meter_type="addon",
            included=knowledge_included,
            used=knowledge_used,
            remaining=max(0, knowledge_included - knowledge_used) if knowledge_included is not None else None,
            status=knowledge_status,
            source="onboarding_contract.purchased.features.knowledge_upload",
        ),
        ConsoleSubscriptionMeterItem(
            key="analytics",
            label="Бизнес-аналитика",
            meter_type="addon",
            included=analytics_included,
            used=analytics_used,
            remaining=max(0, analytics_included - analytics_used) if analytics_included is not None else None,
            status=analytics_status,
            source="onboarding_contract.purchased.features.analytics",
        ),
        ConsoleSubscriptionMeterItem(
            key="auto_learn",
            label="Автообучение",
            meter_type="addon",
            included=auto_learn_included,
            used=auto_learn_used,
            remaining=max(0, auto_learn_included - auto_learn_used) if auto_learn_included is not None else None,
            status=auto_learn_status,
            source="onboarding_contract.purchased.features.auto_learn",
        ),
    ]

    recommended_actions: list[ConsoleBusinessActionItem] = []
    if contract_health.status == "missing":
        _append_subscription_action(
            recommended_actions,
            action_id="contract_fill_required",
            title="Заполните контракт подписки",
            description="Контрактные лимиты не подтверждены. До заполнения доступны только факты использования и доказательства outbox.",
            href="/settings",
            severity="critical",
        )
    elif contract_health.status == "partial":
        _append_subscription_action(
            recommended_actions,
            action_id="contract_complete_required",
            title="Дозаполните контракт подписки",
            description="Часть коммерческих полей отсутствует. Это мешает корректно оценивать риски по лимитам.",
            href="/settings",
            severity="warn",
        )

    if any(gap.code == "monthly_quota_missing" for gap in contract_health.gaps):
        _append_subscription_action(
            recommended_actions,
            action_id="set_monthly_quota_contract",
            title="Укажите лимит сообщений в договоре",
            description="Без лимита невозможно корректно считать остаток и риск перерасхода.",
            href="/settings",
            severity="critical",
        )
    if any(gap.code == "whatsapp_limit_missing" for gap in contract_health.gaps):
        _append_subscription_action(
            recommended_actions,
            action_id="set_whatsapp_limit_contract",
            title="Укажите лимит WhatsApp-каналов",
            description="Лимит каналов не зафиксирован. Уточните условия тарифа и обновите контракт.",
            href="/settings",
            severity="warn",
        )
    if any(gap.code == "payment_status_missing" for gap in contract_health.gaps):
        _append_subscription_action(
            recommended_actions,
            action_id="set_payment_status_contract",
            title="Заполните статус оплаты",
            description="Статус оплаты не указан в онбординге. Обновите поле, чтобы исключить двусмысленность.",
            href="/settings",
            severity="warn",
        )

    if over_quota or quota_alert_level == "limit_100":
        _append_subscription_action(
            recommended_actions,
            action_id="review_plan_overage",
            title="Лимит сообщений превышен",
            description="Проверьте тариф или снизьте поток нецелевых ответов бота, чтобы остановить перерасход.",
            href="/business",
            severity="critical",
        )
    elif quota_alert_level == "warning_80":
        _append_subscription_action(
            recommended_actions,
            action_id="review_quota_risk",
            title="Риск перерасхода в этом периоде",
            description="Текущая динамика близка к лимиту. Проверьте прогноз и подготовьте изменение плана заранее.",
            href="/subscription",
            severity="warn",
        )

    if payment_status in {"pending", "rejected"}:
        _append_subscription_action(
            recommended_actions,
            action_id="verify_payment_status",
            title="Проверьте статус оплаты подписки",
            description=_resolve_subscription_payment_status_message(
                payment_status=payment_status,
                payment_confirmed_at=payment_confirmed_at,
            ),
            href="/settings",
            severity="critical" if payment_status == "rejected" else "warn",
        )

    if whatsapp_status in {"over_limit", "not_included"}:
        _append_subscription_action(
            recommended_actions,
            action_id="whatsapp_limit_mismatch",
            title="Проверьте лимит WhatsApp каналов",
            description="Фактическое число подключений не совпадает с планом. Уточните договор и конфигурацию филиалов.",
            href="/settings",
            severity="critical",
        )
    elif whatsapp_included is not None and whatsapp_included > 0 and whatsapp_used == 0:
        _append_subscription_action(
            recommended_actions,
            action_id="whatsapp_setup_required",
            title="Подключите WhatsApp канал",
            description="Канал включён в план, но не настроен в текущем клиенте.",
            href="/settings",
            severity="warn",
        )

    if binding_critical_total > 0 or binding_warn_total > 0:
        _append_subscription_action(
            recommended_actions,
            action_id="review_whatsapp_binding_health",
            title="Проверьте состояние WhatsApp подключения",
            description="Есть риски по webhook/rebind/renewal. Проверьте параметры канала и продлите доступ при необходимости.",
            href="/settings",
            severity="critical" if binding_critical_total > 0 else "warn",
        )

    if any(
        meter.status == "included_not_configured"
        for meter in meters
        if meter.meter_type == "addon"
    ):
        _append_subscription_action(
            recommended_actions,
            action_id="configure_purchased_addons",
            title="Настройте купленные интеграции",
            description="Часть оплаченных интеграций включена в договоре, но ещё не активирована в рабочем контуре.",
            href="/settings",
            severity="info",
        )

    if not recommended_actions:
        _append_subscription_action(
            recommended_actions,
            action_id="subscription_monitor_daily",
            title="Подписка в норме",
            description="Проверяйте лимиты и статус подключения по расписанию, чтобы избежать сюрпризов в конце периода.",
            href="/subscription",
            severity="info",
        )

    scope: Literal["system", "client", "branch"] = "branch" if allowed_branch_ids is not None else "client"
    metric_meta = {
        "billable_messages": _build_metric_meta(
            kind="fact",
            source="outbox_messages",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=billable_messages,
        ),
        "monthly_quota": _build_metric_meta(
            kind="fact" if monthly_quota is not None else "missing",
            source=f"subscription_contract:{quota_source}",
            as_of=now.isoformat(),
            scope="client",
            sample_size=1 if monthly_quota is not None else None,
        ),
        "remaining_quota": _build_metric_meta(
            kind="fact" if remaining_quota is not None else "missing",
            source=f"derived:billable_messages+monthly_quota:{quota_source}",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=1 if remaining_quota is not None else None,
        ),
        "usage_percent": _build_metric_meta(
            kind="fact" if usage_percent is not None else "missing",
            source=f"derived:billable_messages+monthly_quota:{quota_source}",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=1 if usage_percent is not None else None,
        ),
        "projected_month_total": _build_metric_meta(
            kind="estimate",
            source="linear_projection:period_elapsed_days",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=elapsed_days,
            note="projection, not observed fact",
        ),
        "projected_remaining_quota": _build_metric_meta(
            kind="estimate" if projected_remaining_quota is not None else "missing",
            source="derived:projected_month_total+monthly_quota",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=elapsed_days if projected_remaining_quota is not None else None,
            note="projection, not observed fact" if projected_remaining_quota is not None else None,
        ),
        "projected_overage_messages": _build_metric_meta(
            kind="estimate" if projected_overage_messages is not None else "missing",
            source="derived:projected_month_total+monthly_quota",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=elapsed_days if projected_overage_messages is not None else None,
            note="projection, not observed fact" if projected_overage_messages is not None else None,
        ),
        "whatsapp_channels_used": _build_metric_meta(
            kind="fact",
            source="branches.instance_id",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=whatsapp_used,
        ),
        "whatsapp_channels_included": _build_metric_meta(
            kind="fact" if whatsapp_included is not None else "missing",
            source=f"subscription_contract:{whatsapp_source}",
            as_of=now.isoformat(),
            scope="client",
            sample_size=1 if whatsapp_included is not None else None,
            note=whatsapp_note if whatsapp_included is None else None,
        ),
        "payment_status": _build_metric_meta(
            kind="fact" if payment_status != "unknown" else "missing",
            source=f"onboarding_contract:{payment_status_source}",
            as_of=now.isoformat(),
            scope="client",
            sample_size=1 if payment_status != "unknown" else None,
        ),
    }

    evidence_items = []
    for row in evidence_rows:
        meta = row.meta if isinstance(row.meta, dict) else {}
        provider_status_meta = meta.get("provider_status") if isinstance(meta.get("provider_status"), dict) else {}
        evidence_items.append(
            ConsoleSubscriptionEvidenceItem(
                outbox_id=row.id,
                conversation_id=row.conversation_id,
                inbound_message_id=row.inbound_message_id,
                created_at=row.created_at.isoformat(),
                status=row.status,
                provider_status=provider_status_meta.get("status"),
                provider_message_id=provider_status_meta.get("provider_message_id"),
            )
        )

    return ConsoleSubscriptionSummaryResponse(
        generated_at=now.isoformat(),
        period_start=period_start.date().isoformat(),
        period_end=(period_end.date() - timedelta(days=1)).isoformat(),
        next_billing_date=next_billing_date,
        plan_name=plan_name,
        contract_label=contract_label,
        currency=currency,
        monthly_quota=monthly_quota,
        quota_source=quota_source,
        billable_messages=billable_messages,
        remaining_quota=remaining_quota,
        projected_month_total=projected_month_total,
        usage_percent=usage_percent,
        projected_remaining_quota=projected_remaining_quota,
        projected_over_quota=projected_over_quota,
        projected_overage_messages=projected_overage_messages,
        quota_alert_level=quota_alert_level,
        quota_alert_message=quota_alert_message,
        overage_policy_message="Перерасход считается по формуле overage = max(0, billable - quota).",
        over_quota=over_quota,
        payment_status=payment_status,
        payment_confirmed_at=payment_confirmed_at,
        payment_status_source=payment_status_source,
        payment_status_message=_resolve_subscription_payment_status_message(
            payment_status=payment_status,
            payment_confirmed_at=payment_confirmed_at,
        ),
        contract_health=contract_health,
        plan_defaults=default_plan,
        meters=meters,
        recommended_actions=recommended_actions,
        evidence=evidence_items,
        metric_meta=metric_meta,
    )


@router.get(
    "/business/data-trust",
    response_model=ConsoleDataTrustSummaryResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def get_business_data_trust(
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleDataTrustSummaryResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "business",
        "read",
        message="Only owner/admin can access data trust summary",
    )

    now = datetime.now(timezone.utc)
    allowed_branch_ids = _resolve_branch_scope(context)
    analytics_scope_limited = allowed_branch_ids is not None

    analytics_row = _load_latest_analytics_row(
        db=db,
        client_id=context.client.id,
        metric_date=now.date(),
        analytics_scope_limited=analytics_scope_limited,
    )
    metric_date = analytics_row.get("metric_date").isoformat() if analytics_row and analytics_row.get("metric_date") else None
    first_response_missing_total = _safe_int(
        analytics_row.get("first_response_missing_total") if analytics_row else None
    )
    escalation_meta_missing_total = _safe_int(
        analytics_row.get("escalation_meta_missing_total") if analytics_row else None
    )
    intent_missing_total = _safe_int(analytics_row.get("intent_missing_total") if analytics_row else None)

    knowledge_query = db.query(KnowledgeVersion).filter(
        KnowledgeVersion.client_id == context.client.id,
        KnowledgeVersion.status == "published",
    )
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            knowledge_query = knowledge_query.filter(text("1 = 0"))
        else:
            knowledge_query = knowledge_query.filter(KnowledgeVersion.branch_id.in_(allowed_branch_ids))
    latest_knowledge = (
        knowledge_query.order_by(
            KnowledgeVersion.published_at.desc(),
            KnowledgeVersion.created_at.desc(),
        ).first()
    )
    knowledge_last_published_at = (
        latest_knowledge.published_at.isoformat()
        if latest_knowledge and latest_knowledge.published_at is not None
        else None
    )
    knowledge_stale_hours = None
    if latest_knowledge and latest_knowledge.published_at is not None:
        knowledge_stale_hours = max(0, int((now - latest_knowledge.published_at).total_seconds() // 3600))

    audit_window_start = now - timedelta(hours=24)
    audit_query = db.query(AuditEvent).filter(
        AuditEvent.client_id == context.client.id,
        AuditEvent.created_at >= audit_window_start,
        AuditEvent.created_at < now,
    )
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            audit_query = audit_query.filter(text("1 = 0"))
        else:
            audit_query = audit_query.filter(AuditEvent.branch_id.in_(allowed_branch_ids))
    audit_events_24h = audit_query.count()
    critical_audit_events_24h = audit_query.filter(
        or_(
            AuditEvent.event_type.ilike("%failed%"),
            AuditEvent.event_type.ilike("%blocked%"),
            AuditEvent.event_type.ilike("%rejected%"),
        )
    ).count()

    status, status_label = _derive_data_trust_status(
        first_response_missing_total=first_response_missing_total,
        escalation_meta_missing_total=escalation_meta_missing_total,
        intent_missing_total=intent_missing_total,
        knowledge_stale_hours=knowledge_stale_hours,
        critical_audit_events_24h=critical_audit_events_24h,
        analytics_scope_limited=analytics_scope_limited,
    )
    actions = _build_data_trust_actions(
        first_response_missing_total=first_response_missing_total,
        escalation_meta_missing_total=escalation_meta_missing_total,
        intent_missing_total=intent_missing_total,
        knowledge_stale_hours=knowledge_stale_hours,
        critical_audit_events_24h=critical_audit_events_24h,
        analytics_scope_limited=analytics_scope_limited,
    )
    scope: Literal["system", "client", "branch"] = "branch" if allowed_branch_ids is not None else "client"
    analytics_as_of = metric_date or now.date().isoformat()
    metric_meta = {
        "first_response_missing_total": _build_metric_meta(
            kind="fact" if first_response_missing_total is not None else "missing",
            source="metrics_analytics_daily",
            as_of=analytics_as_of,
            scope=scope,
            sample_size=1 if first_response_missing_total is not None else None,
            note=(
                "company-level analytics unavailable in branch scope"
                if analytics_scope_limited and first_response_missing_total is None
                else None
            ),
        ),
        "escalation_meta_missing_total": _build_metric_meta(
            kind="fact" if escalation_meta_missing_total is not None else "missing",
            source="metrics_analytics_daily",
            as_of=analytics_as_of,
            scope=scope,
            sample_size=1 if escalation_meta_missing_total is not None else None,
            note=(
                "company-level analytics unavailable in branch scope"
                if analytics_scope_limited and escalation_meta_missing_total is None
                else None
            ),
        ),
        "intent_missing_total": _build_metric_meta(
            kind="fact" if intent_missing_total is not None else "missing",
            source="metrics_analytics_daily",
            as_of=analytics_as_of,
            scope=scope,
            sample_size=1 if intent_missing_total is not None else None,
            note=(
                "company-level analytics unavailable in branch scope"
                if analytics_scope_limited and intent_missing_total is None
                else None
            ),
        ),
        "knowledge_stale_hours": _build_metric_meta(
            kind="fact" if knowledge_stale_hours is not None else "missing",
            source="knowledge_versions",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=1 if knowledge_stale_hours is not None else None,
        ),
        "audit_events_24h": _build_metric_meta(
            kind="fact",
            source="audit_events",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=audit_events_24h,
        ),
        "critical_audit_events_24h": _build_metric_meta(
            kind="fact",
            source="audit_events",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=critical_audit_events_24h,
        ),
    }

    return ConsoleDataTrustSummaryResponse(
        generated_at=now.isoformat(),
        status=status,
        status_label=status_label,
        metric_date=metric_date,
        analytics_scope_limited=analytics_scope_limited,
        first_response_missing_total=first_response_missing_total,
        escalation_meta_missing_total=escalation_meta_missing_total,
        intent_missing_total=intent_missing_total,
        knowledge_last_published_at=knowledge_last_published_at,
        knowledge_stale_hours=knowledge_stale_hours,
        audit_events_24h=audit_events_24h,
        critical_audit_events_24h=critical_audit_events_24h,
        actions=actions,
        metric_meta=metric_meta,
    )


@router.get(
    "/business/team-performance",
    response_model=ConsoleTeamPerformanceSummaryResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def get_business_team_performance(
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleTeamPerformanceSummaryResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "business",
        "read",
        message="Only owner/admin can access team performance summary",
    )

    now = datetime.now(timezone.utc)
    allowed_branch_ids = _resolve_branch_scope(context)
    analytics_scope_limited = allowed_branch_ids is not None

    analytics_row = _load_latest_analytics_row(
        db=db,
        client_id=context.client.id,
        metric_date=now.date(),
        analytics_scope_limited=analytics_scope_limited,
    )
    metric_date = analytics_row.get("metric_date").isoformat() if analytics_row and analytics_row.get("metric_date") else None
    manager_median_response_seconds = _safe_float(
        analytics_row.get("manager_median_response_seconds") if analytics_row else None
    )
    first_response_p90_seconds = _safe_float(
        analytics_row.get("first_response_p90_seconds") if analytics_row else None
    )

    handover_base = db.query(Handover).filter(Handover.client_id == context.client.id)
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            unresolved_cases = 0
            unresolved_older_than_60m = 0
            managers: list[ConsoleTeamManagerPerformanceItem] = []
            top_manager_name = None
            top_manager_unresolved = 0
        else:
            handover_base = handover_base.join(
                Conversation,
                Handover.conversation_id == Conversation.id,
            ).filter(Conversation.branch_id.in_(allowed_branch_ids))
            unresolved_query = handover_base.filter(Handover.status.in_(["pending", "active"]))
            unresolved_cases = unresolved_query.count()
            unresolved_older_than_60m = unresolved_query.filter(
                Handover.created_at < (now - timedelta(minutes=60))
            ).count()
            manager_name_expr = func.coalesce(
                func.nullif(func.trim(Handover.assigned_to_name), ""),
                func.nullif(func.trim(Handover.assigned_to), ""),
                "Не назначен",
            )
            manager_rows = (
                unresolved_query.with_entities(
                    manager_name_expr.label("manager_name"),
                    func.count().label("unresolved_cases"),
                    func.sum(case((Handover.status == "pending", 1), else_=0)).label("pending_cases"),
                    func.sum(case((Handover.status == "active", 1), else_=0)).label("active_cases"),
                    func.min(Handover.created_at).label("oldest_created_at"),
                )
                .group_by(manager_name_expr)
                .order_by(func.count().desc())
                .limit(8)
                .all()
            )
            avg_response_rows = (
                handover_base.filter(
                    Handover.first_response_at.isnot(None),
                    Handover.created_at >= (now - timedelta(days=30)),
                    Handover.first_response_at >= Handover.created_at,
                )
                .with_entities(
                    manager_name_expr.label("manager_name"),
                    func.avg(func.extract("epoch", Handover.first_response_at - Handover.created_at)).label(
                        "avg_first_response_seconds_30d"
                    ),
                )
                .group_by(manager_name_expr)
                .all()
            )
            avg_response_by_manager = {
                row.manager_name: _safe_float(row.avg_first_response_seconds_30d)
                for row in avg_response_rows
            }
            managers = []
            top_manager_name = None
            top_manager_unresolved = 0
            for row in manager_rows:
                unresolved_value = int(row.unresolved_cases or 0)
                pending_value = int(row.pending_cases or 0)
                active_value = int(row.active_cases or 0)
                oldest_unresolved_minutes = None
                if row.oldest_created_at is not None:
                    oldest_unresolved_minutes = max(
                        0,
                        int((now - row.oldest_created_at).total_seconds() // 60),
                    )
                manager_name = row.manager_name or "Не назначен"
                if unresolved_value > top_manager_unresolved:
                    top_manager_unresolved = unresolved_value
                    top_manager_name = manager_name
                managers.append(
                    ConsoleTeamManagerPerformanceItem(
                        manager_name=manager_name,
                        unresolved_cases=unresolved_value,
                        pending_cases=pending_value,
                        active_cases=active_value,
                        oldest_unresolved_minutes=oldest_unresolved_minutes,
                        avg_first_response_seconds_30d=avg_response_by_manager.get(manager_name),
                    )
                )
    else:
        unresolved_query = handover_base.filter(Handover.status.in_(["pending", "active"]))
        unresolved_cases = unresolved_query.count()
        unresolved_older_than_60m = unresolved_query.filter(
            Handover.created_at < (now - timedelta(minutes=60))
        ).count()
        manager_name_expr = func.coalesce(
            func.nullif(func.trim(Handover.assigned_to_name), ""),
            func.nullif(func.trim(Handover.assigned_to), ""),
            "Не назначен",
        )
        manager_rows = (
            unresolved_query.with_entities(
                manager_name_expr.label("manager_name"),
                func.count().label("unresolved_cases"),
                func.sum(case((Handover.status == "pending", 1), else_=0)).label("pending_cases"),
                func.sum(case((Handover.status == "active", 1), else_=0)).label("active_cases"),
                func.min(Handover.created_at).label("oldest_created_at"),
            )
            .group_by(manager_name_expr)
            .order_by(func.count().desc())
            .limit(8)
            .all()
        )
        avg_response_rows = (
            handover_base.filter(
                Handover.first_response_at.isnot(None),
                Handover.created_at >= (now - timedelta(days=30)),
                Handover.first_response_at >= Handover.created_at,
            )
            .with_entities(
                manager_name_expr.label("manager_name"),
                func.avg(func.extract("epoch", Handover.first_response_at - Handover.created_at)).label(
                    "avg_first_response_seconds_30d"
                ),
            )
            .group_by(manager_name_expr)
            .all()
        )
        avg_response_by_manager = {
            row.manager_name: _safe_float(row.avg_first_response_seconds_30d)
            for row in avg_response_rows
        }
        managers = []
        top_manager_name = None
        top_manager_unresolved = 0
        for row in manager_rows:
            unresolved_value = int(row.unresolved_cases or 0)
            pending_value = int(row.pending_cases or 0)
            active_value = int(row.active_cases or 0)
            oldest_unresolved_minutes = None
            if row.oldest_created_at is not None:
                oldest_unresolved_minutes = max(
                    0,
                    int((now - row.oldest_created_at).total_seconds() // 60),
                )
            manager_name = row.manager_name or "Не назначен"
            if unresolved_value > top_manager_unresolved:
                top_manager_unresolved = unresolved_value
                top_manager_name = manager_name
            managers.append(
                ConsoleTeamManagerPerformanceItem(
                    manager_name=manager_name,
                    unresolved_cases=unresolved_value,
                    pending_cases=pending_value,
                    active_cases=active_value,
                    oldest_unresolved_minutes=oldest_unresolved_minutes,
                    avg_first_response_seconds_30d=avg_response_by_manager.get(manager_name),
                )
            )

    status, status_label = _derive_team_performance_status(
        unresolved_cases=unresolved_cases,
        unresolved_older_than_60m=unresolved_older_than_60m,
        manager_median_response_seconds=manager_median_response_seconds,
    )
    actions = _build_team_performance_actions(
        unresolved_older_than_60m=unresolved_older_than_60m,
        manager_median_response_seconds=manager_median_response_seconds,
        top_manager_name=top_manager_name,
        top_manager_unresolved=top_manager_unresolved,
        analytics_scope_limited=analytics_scope_limited,
    )
    scope: Literal["system", "client", "branch"] = "branch" if allowed_branch_ids is not None else "client"
    analytics_as_of = metric_date or now.date().isoformat()
    metric_meta = {
        "unresolved_cases": _build_metric_meta(
            kind="fact",
            source="handovers",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=unresolved_cases,
        ),
        "unresolved_older_than_60m": _build_metric_meta(
            kind="fact",
            source="handovers",
            as_of=now.isoformat(),
            scope=scope,
            sample_size=unresolved_older_than_60m,
        ),
        "manager_median_response_seconds": _build_metric_meta(
            kind="fact" if manager_median_response_seconds is not None else "missing",
            source="metrics_analytics_daily",
            as_of=analytics_as_of,
            scope=scope,
            sample_size=1 if manager_median_response_seconds is not None else None,
            note=(
                "company-level analytics unavailable in branch scope"
                if analytics_scope_limited and manager_median_response_seconds is None
                else None
            ),
        ),
        "first_response_p90_seconds": _build_metric_meta(
            kind="fact" if first_response_p90_seconds is not None else "missing",
            source="metrics_analytics_daily",
            as_of=analytics_as_of,
            scope=scope,
            sample_size=1 if first_response_p90_seconds is not None else None,
            note=(
                "company-level analytics unavailable in branch scope"
                if analytics_scope_limited and first_response_p90_seconds is None
                else None
            ),
        ),
    }

    return ConsoleTeamPerformanceSummaryResponse(
        generated_at=now.isoformat(),
        status=status,
        status_label=status_label,
        metric_date=metric_date,
        analytics_scope_limited=analytics_scope_limited,
        manager_median_response_seconds=manager_median_response_seconds,
        first_response_p90_seconds=first_response_p90_seconds,
        unresolved_cases=unresolved_cases,
        unresolved_older_than_60m=unresolved_older_than_60m,
        managers=managers,
        actions=actions,
        metric_meta=metric_meta,
    )


@router.post(
    "/business/operations/owner-mode/preview",
    response_model=ConsoleOwnerOperationPreviewResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def preview_owner_mode_operation(
    body: ConsoleOwnerOperationApplyRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleOwnerOperationPreviewResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "settings",
        "write",
        message="Only owner/admin can preview owner operation modes",
    )
    now = datetime.now(timezone.utc)
    mode_label, settings_patch, warnings = _resolve_owner_mode_profile(body.mode)
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == context.client.id).first()
    current_settings = _normalize_owner_settings(settings)
    baseline, metric_meta = _collect_owner_operation_metrics(db=db, context=context, now=now)

    if (
        current_settings.reminder_1_minutes == settings_patch.reminder_1_minutes
        and current_settings.reminder_2_minutes == settings_patch.reminder_2_minutes
        and current_settings.escalation_timeout_minutes == settings_patch.escalation_timeout_minutes
    ):
        warnings.append("Профиль уже активен: изменения в SLA не требуются.")
    if baseline.outbox_backlog >= 1000:
        warnings.append("Outbox backlog критический: сначала подтвердите, что команда готова к изменению режима.")

    return ConsoleOwnerOperationPreviewResponse(
        generated_at=now.isoformat(),
        mode=body.mode,
        mode_label=mode_label,
        settings_patch=settings_patch,
        current_settings=current_settings,
        baseline=baseline,
        warnings=warnings,
        metric_meta=metric_meta,
    )


@router.post(
    "/business/operations/owner-mode/apply",
    response_model=ConsoleOwnerOperationApplyResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def apply_owner_mode_operation(
    body: ConsoleOwnerOperationApplyRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleOwnerOperationApplyResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "settings",
        "write",
        message="Only owner/admin can apply owner operation modes",
    )
    now = datetime.now(timezone.utc)
    due_at = now + timedelta(hours=24)
    mode_label, settings_patch, _warnings = _resolve_owner_mode_profile(body.mode)
    baseline, metric_meta = _collect_owner_operation_metrics(db=db, context=context, now=now)

    settings = _ensure_client_settings_row(db, client_id=context.client.id)
    previous_settings = _normalize_owner_settings(settings)
    _apply_owner_operation_settings(settings=settings, patch=settings_patch)

    operation_id = uuid4()
    record_audit_event(
        db,
        actor=context.agent,
        event_type="owner_mode_apply",
        entity_type="client_settings",
        entity_id=context.client.id,
        payload={
            "operation_id": str(operation_id),
            "mode": body.mode,
            "mode_label": mode_label,
            "previous_settings": previous_settings.model_dump(mode="json"),
            "applied_settings": settings_patch.model_dump(mode="json"),
            "baseline": baseline.model_dump(mode="json"),
            "metric_meta": {key: value.model_dump(mode="json") for key, value in metric_meta.items()},
            "applied_at": now.isoformat(),
            "impact_check_due_at": due_at.isoformat(),
        },
        client_id=context.client.id,
        branch_id=context.effective_branch_id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
    )
    db.commit()

    return ConsoleOwnerOperationApplyResponse(
        success=True,
        operation_id=operation_id,
        mode=body.mode,
        mode_label=mode_label,
        applied_settings=settings_patch,
        previous_settings=previous_settings,
        baseline=baseline,
        applied_at=now.isoformat(),
        impact_check_due_at=due_at.isoformat(),
        metric_meta=metric_meta,
    )


@router.post(
    "/business/operations/owner-mode/rollback",
    response_model=ConsoleOwnerOperationRollbackResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def rollback_owner_mode_operation(
    body: ConsoleOwnerOperationRollbackRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleOwnerOperationRollbackResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "settings",
        "write",
        message="Only owner/admin can rollback owner operation modes",
    )

    source_event = _load_owner_mode_apply_event(
        db=db,
        context=context,
        operation_id=body.operation_id,
    )
    if source_event is None:
        raise ConsoleAPIError(404, "OWNER_OPERATION_NOT_FOUND", "Owner operation not found")

    payload = source_event.payload if isinstance(source_event.payload, dict) else {}
    restore_patch = _parse_owner_operation_settings(payload, key="previous_settings")
    if restore_patch is None:
        raise ConsoleAPIError(409, "OWNER_OPERATION_ROLLBACK_UNAVAILABLE", "Rollback snapshot not available")

    settings = _ensure_client_settings_row(db, client_id=context.client.id)
    _apply_owner_operation_settings(settings=settings, patch=restore_patch)
    rolled_back_at = datetime.now(timezone.utc)

    record_audit_event(
        db,
        actor=context.agent,
        event_type="owner_mode_rollback",
        entity_type="client_settings",
        entity_id=context.client.id,
        payload={
            "source_operation_id": str(source_event.id),
            "mode": payload.get("mode"),
            "restored_settings": restore_patch.model_dump(mode="json"),
            "rolled_back_at": rolled_back_at.isoformat(),
        },
        client_id=context.client.id,
        branch_id=context.effective_branch_id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
    )
    db.commit()

    return ConsoleOwnerOperationRollbackResponse(
        success=True,
        operation_id=source_event.id,
        restored_settings=restore_patch,
        rolled_back_at=rolled_back_at.isoformat(),
        message="Rollback completed",
    )


@router.get(
    "/business/operations/{operation_id}/impact",
    response_model=ConsoleOwnerOperationImpactResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def get_owner_mode_operation_impact(
    operation_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleOwnerOperationImpactResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "business",
        "read",
        message="Only owner/admin can access owner operation impact",
    )
    event = _load_owner_mode_apply_event(
        db=db,
        context=context,
        operation_id=operation_id,
    )
    if event is None:
        raise ConsoleAPIError(404, "OWNER_OPERATION_NOT_FOUND", "Owner operation not found")

    payload = event.payload if isinstance(event.payload, dict) else {}
    mode_value = str(payload.get("mode", "stable_quality"))
    mode: ConsoleOwnerMode = (
        mode_value
        if mode_value in {"capture_leads", "stable_quality", "team_protection"}
        else "stable_quality"
    )
    baseline = _parse_owner_operation_snapshot(payload, key="baseline")
    if baseline is None:
        raise ConsoleAPIError(409, "OWNER_OPERATION_IMPACT_UNAVAILABLE", "Baseline snapshot not available")

    due_at = payload.get("impact_check_due_at")
    if not isinstance(due_at, str) or not due_at.strip():
        due_at = event.created_at.isoformat() if event.created_at else datetime.now(timezone.utc).isoformat()

    checked_at = datetime.now(timezone.utc)
    current, metric_meta = _collect_owner_operation_metrics(db=db, context=context, now=checked_at)

    metrics = {
        "outbox_backlog": _build_owner_operation_metric_delta(
            baseline=float(baseline.outbox_backlog),
            current=float(current.outbox_backlog),
        ),
        "unresolved_older_than_60m": _build_owner_operation_metric_delta(
            baseline=float(baseline.unresolved_older_than_60m),
            current=float(current.unresolved_older_than_60m),
        ),
        "manager_median_response_seconds": _build_owner_operation_metric_delta(
            baseline=baseline.manager_median_response_seconds,
            current=current.manager_median_response_seconds,
        ),
    }
    summary = _summarize_owner_operation_delta(metrics)

    record_audit_event(
        db,
        actor=context.agent,
        event_type="owner_mode_impact_check",
        entity_type="client_settings",
        entity_id=context.client.id,
        payload={
            "source_operation_id": str(event.id),
            "mode": mode,
            "summary": summary,
            "metrics": {key: value.model_dump(mode="json") for key, value in metrics.items()},
            "checked_at": checked_at.isoformat(),
        },
        client_id=context.client.id,
        branch_id=context.effective_branch_id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
    )
    db.commit()

    return ConsoleOwnerOperationImpactResponse(
        operation_id=event.id,
        mode=mode,
        checked_at=checked_at.isoformat(),
        due_at=due_at,
        summary=summary,
        baseline=baseline,
        current=current,
        metrics=metrics,
        metric_meta=metric_meta,
    )


@router.get(
    "/health",
    response_model=ConsoleHealthResponse,
)
async def get_health(db: Session = Depends(get_db)) -> ConsoleHealthResponse:
    """Get system health status."""
    from app.models import OutboxMessage

    # Check database
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "error"

    # Redis is mandatory for runtime reliability (dedupe/state/queues).
    redis_status = "error"
    redis_url = ((os.getenv("REDIS_URL") or "").strip() or _DEFAULT_RUNTIME_REDIS_URL)
    try:
        import redis  # type: ignore

        redis.Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1).ping()
        redis_status = "connected"
    except Exception:
        redis_status = "error"

    # Count outbox backlog
    try:
        backlog = (
            db.query(OutboxMessage)
            .filter(OutboxMessage.status.in_(["PENDING", "PROCESSING"]))
            .count()
        )
    except Exception:
        backlog = -1

    if db_status != "connected":
        overall_status = "unhealthy"
    elif redis_status != "connected":
        overall_status = "degraded"
    else:
        overall_status = "ok"

    return ConsoleHealthResponse(
        status=overall_status,
        version=os.getenv("APP_VERSION", "dev"),
        database=db_status,
        redis=redis_status,
        outbox_backlog=backlog,
    )


@router.get(
    "/ops/outbox",
    response_model=ConsoleOutboxListResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_outbox(
    request: Request,
    status: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> ConsoleOutboxListResponse:
    """List outbox queue entries for ops."""
    context = get_console_context(request, db)
    _require_ops_access(context, action="read")

    _reject_unknown_query_params(request, {"status", "cursor", "limit"})
    _validate_limit(limit)

    status_filters = _parse_outbox_status_param(status)

    base_query = db.query(OutboxMessage).filter(OutboxMessage.client_id == context.client.id)
    if context.branch_restricted:
        allowed_branch_ids = {b.id for b in context.branches}
        if not allowed_branch_ids:
            return ConsoleOutboxListResponse(
                items=[],
                cursor=None,
                has_more=False,
                counts=ConsoleOutboxCounts(pending=0, processing=0, failed=0),
            )
        base_query = base_query.filter(OutboxMessage.branch_id.in_(allowed_branch_ids))

    counts_rows = (
        base_query.with_entities(OutboxMessage.status, func.count().label("count"))
        .group_by(OutboxMessage.status)
        .all()
    )
    counts = {"pending": 0, "processing": 0, "failed": 0}
    for status_value, count in counts_rows:
        normalized = _normalize_outbox_status(status_value)
        if normalized in counts:
            counts[normalized] = int(count or 0)

    query = base_query
    if status_filters:
        query = query.filter(OutboxMessage.status.in_(status_filters))

    cursor_date = _parse_cursor_param(cursor)
    if cursor_date is not None:
        query = query.filter(OutboxMessage.created_at < cursor_date)

    rows = (
        query.order_by(OutboxMessage.created_at.desc(), OutboxMessage.id.desc())
        .limit(limit + 1)
        .all()
    )
    has_more = len(rows) > limit
    items_rows = rows[:limit]
    next_cursor = items_rows[-1].created_at.isoformat() if has_more and items_rows else None

    return ConsoleOutboxListResponse(
        items=[_build_outbox_item(row) for row in items_rows],
        cursor=next_cursor,
        has_more=has_more,
        counts=ConsoleOutboxCounts(
            pending=counts["pending"],
            processing=counts["processing"],
            failed=counts["failed"],
        ),
    )


@router.post(
    "/ops/outbox/retry",
    response_model=ConsoleOutboxRetryResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def retry_outbox(
    body: ConsoleOutboxRetryRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleOutboxRetryResponse:
    """Retry failed outbox messages."""
    context = get_console_context(request, db)
    _require_ops_access(
        context,
        action="write",
    )

    ids = [entry for entry in (body.ids or []) if entry]
    if not ids:
        _validate_limit(body.limit or 100)

    query = db.query(OutboxMessage).filter(
        OutboxMessage.client_id == context.client.id,
        OutboxMessage.status == "FAILED",
    )
    if context.branch_restricted:
        allowed_branch_ids = {b.id for b in context.branches}
        if not allowed_branch_ids:
            return ConsoleOutboxRetryResponse(success=True, retried=0, skipped=len(ids))
        query = query.filter(OutboxMessage.branch_id.in_(allowed_branch_ids))

    if ids:
        query = query.filter(OutboxMessage.id.in_(ids))
    else:
        query = query.order_by(OutboxMessage.updated_at.desc()).limit(body.limit or 100)

    rows = query.all()
    if ids and not rows:
        raise ConsoleAPIError(404, "NOT_FOUND", "Outbox messages not found")

    now = datetime.now(timezone.utc)
    retried = 0
    for row in rows:
        row.status = "PENDING"
        row.next_attempt_at = None
        row.last_error = None
        row.updated_at = now
        retried += 1

    skipped = max(0, len(ids) - retried) if ids else 0

    record_audit_event(
        db,
        actor=context.agent,
        event_type="outbox_retry",
        entity_type="outbox",
        payload={
            "retried": retried,
            "skipped": skipped,
            "ids": [str(entry) for entry in ids] if ids else None,
        },
        client_id=context.client.id,
    )
    db.commit()

    return ConsoleOutboxRetryResponse(success=True, retried=retried, skipped=skipped)


@router.get(
    "/ops/reminders",
    response_model=ConsoleReminderListResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_reminders(
    request: Request,
    status: Optional[str] = None,
    template: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> ConsoleReminderListResponse:
    """List reminder jobs with diagnostics and linked outbox state."""
    context = get_console_context(request, db)
    _require_ops_access(context, action="read")

    _reject_unknown_query_params(request, {"status", "template", "cursor", "limit"})
    _validate_limit(limit)

    status_filters = _parse_reminder_status_param(status)
    template_filter = template.strip() if template and template.strip() else None
    allowed_branch_ids = _resolve_branch_scope(context)
    if allowed_branch_ids is not None and not allowed_branch_ids:
        return ConsoleReminderListResponse(
            items=[],
            cursor=None,
            has_more=False,
            counts=ConsoleReminderCounts(
                pending=0,
                sent=0,
                failed=0,
                due_now=0,
                overdue_15m=0,
            ),
            error_buckets=[],
        )

    base_query = db.query(ReminderJob).filter(ReminderJob.client_id == context.client.id)
    if allowed_branch_ids is not None:
        base_query = base_query.filter(ReminderJob.branch_id.in_(allowed_branch_ids))
    if template_filter:
        base_query = base_query.filter(ReminderJob.template == template_filter)

    counts_rows = (
        base_query.with_entities(ReminderJob.status, func.count().label("count"))
        .group_by(ReminderJob.status)
        .all()
    )
    counts = {"pending": 0, "sent": 0, "failed": 0}
    for status_value, count in counts_rows:
        normalized = _normalize_reminder_status(status_value)
        if normalized in counts:
            counts[normalized] = int(count or 0)

    now = datetime.now(timezone.utc)
    due_now = (
        base_query.filter(
            ReminderJob.status == "PENDING",
            ReminderJob.run_at <= now,
        ).count()
    )
    overdue_15m = (
        base_query.filter(
            ReminderJob.status == "PENDING",
            ReminderJob.run_at <= (now - timedelta(minutes=15)),
        ).count()
    )
    error_rows = (
        base_query.filter(
            ReminderJob.status == "FAILED",
            ReminderJob.last_error.isnot(None),
            ReminderJob.last_error != "",
        )
        .with_entities(ReminderJob.last_error, func.count().label("count"))
        .group_by(ReminderJob.last_error)
        .order_by(func.count().desc(), ReminderJob.last_error.asc())
        .limit(10)
        .all()
    )

    query = base_query
    if status_filters:
        query = query.filter(ReminderJob.status.in_(status_filters))

    cursor_date = _parse_cursor_param(cursor)
    if cursor_date is not None:
        query = query.filter(ReminderJob.created_at < cursor_date)

    rows = (
        query.order_by(ReminderJob.created_at.desc(), ReminderJob.id.desc())
        .limit(limit + 1)
        .all()
    )
    has_more = len(rows) > limit
    items_rows = rows[:limit]
    next_cursor = items_rows[-1].created_at.isoformat() if has_more and items_rows else None

    outbox_map: dict[str, OutboxMessage] = {}
    dedupe_keys = [row.dedupe_key for row in items_rows if row.dedupe_key]
    if dedupe_keys:
        outbox_query = db.query(OutboxMessage).filter(
            OutboxMessage.client_id == context.client.id,
            OutboxMessage.inbound_message_id.in_(dedupe_keys),
        )
        if allowed_branch_ids is not None:
            outbox_query = outbox_query.filter(OutboxMessage.branch_id.in_(allowed_branch_ids))
        outbox_rows = (
            outbox_query.order_by(OutboxMessage.created_at.desc(), OutboxMessage.id.desc())
            .all()
        )
        for outbox_row in outbox_rows:
            if outbox_row.inbound_message_id not in outbox_map:
                outbox_map[outbox_row.inbound_message_id] = outbox_row

    return ConsoleReminderListResponse(
        items=[
            _build_reminder_item(
                row,
                outbox_row=outbox_map.get(row.dedupe_key),
            )
            for row in items_rows
        ],
        cursor=next_cursor,
        has_more=has_more,
        counts=ConsoleReminderCounts(
            pending=counts["pending"],
            sent=counts["sent"],
            failed=counts["failed"],
            due_now=due_now,
            overdue_15m=overdue_15m,
        ),
        error_buckets=[
            ConsoleReminderErrorBucket(reason=str(reason), count=int(count or 0))
            for reason, count in error_rows
            if reason
        ],
    )


@router.post(
    "/ops/reminders/retry",
    response_model=ConsoleReminderRetryResponse,
    responses={
        401: {"model": ConsoleErrorResponse},
        403: {"model": ConsoleErrorResponse},
        404: {"model": ConsoleErrorResponse},
        409: {"model": ConsoleErrorResponse},
    },
)
async def retry_reminders(
    body: ConsoleReminderRetryRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleReminderRetryResponse:
    """Retry reminder jobs in FAILED/PENDING state."""
    context = get_console_context(request, db)
    _require_ops_access(context, action="write")

    ids = [entry for entry in (body.ids or []) if entry]
    if not ids:
        _validate_limit(body.limit or 100)
    status_filters = _parse_reminder_retry_status_param(body.status)

    query = db.query(ReminderJob).filter(ReminderJob.client_id == context.client.id)
    allowed_branch_ids = _resolve_branch_scope(context)
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            return ConsoleReminderRetryResponse(
                success=True,
                retried=0,
                skipped=len(ids),
                matched=0,
            )
        query = query.filter(ReminderJob.branch_id.in_(allowed_branch_ids))

    query = query.filter(ReminderJob.status.in_(status_filters))
    if ids:
        query = query.filter(ReminderJob.id.in_(ids))
    else:
        query = query.order_by(ReminderJob.updated_at.desc(), ReminderJob.id.desc()).limit(body.limit or 100)

    rows = query.all()
    if ids and not rows:
        raise ConsoleAPIError(404, "NOT_FOUND", "Reminder jobs not found")
    if len(rows) > 1 and not body.confirm:
        raise ConsoleAPIError(
            409,
            "CONFIRMATION_REQUIRED",
            "Bulk reminder retry requires confirm=true",
        )

    now = datetime.now(timezone.utc)
    retried = 0
    for row in rows:
        row.status = "PENDING"
        row.next_attempt_at = None
        row.last_error = None
        row.updated_at = now
        retried += 1

    skipped = max(0, len(ids) - retried) if ids else 0
    record_audit_event(
        db,
        actor=context.agent,
        event_type="reminder_retry",
        entity_type="reminder_jobs",
        payload={
            "retried": retried,
            "skipped": skipped,
            "matched": len(rows),
            "status": body.status,
            "ids": [str(entry) for entry in ids] if ids else None,
            "confirm": body.confirm,
        },
        client_id=context.client.id,
        branch_id=context.effective_branch_id,
    )
    db.commit()

    return ConsoleReminderRetryResponse(
        success=True,
        retried=retried,
        skipped=skipped,
        matched=len(rows),
    )


@router.get(
    "/ops/jobs/catalog",
    response_model=ConsoleOpsJobCatalogResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def get_ops_jobs_catalog(
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleOpsJobCatalogResponse:
    context = get_console_context(request, db)
    _require_ops_access(context, action="read")

    items = [
        ConsoleOpsJobDefinition(
            job_type=job_type,
            label=meta["label"],
            description=meta["description"],
            supports_dry_run=bool(meta["supports_dry_run"]),
        )
        for job_type, meta in _OPS_JOB_DEFINITIONS.items()
    ]
    return ConsoleOpsJobCatalogResponse(items=items)


@router.get(
    "/ops/jobs",
    response_model=ConsoleOpsJobListResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_ops_jobs(
    request: Request,
    cursor: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> ConsoleOpsJobListResponse:
    context = get_console_context(request, db)
    _require_ops_access(context, action="read")

    _reject_unknown_query_params(request, {"cursor", "limit"})
    _validate_limit(limit)

    query = db.query(ConsoleOpsJob).filter(ConsoleOpsJob.client_id == context.client.id)
    allowed_branch_ids = _resolve_branch_scope(context)
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            return ConsoleOpsJobListResponse(items=[], cursor=None, has_more=False)
        query = query.filter(ConsoleOpsJob.branch_id.in_(allowed_branch_ids))

    cursor_date = _parse_cursor_param(cursor)
    if cursor_date is not None:
        query = query.filter(ConsoleOpsJob.created_at < cursor_date)

    rows = (
        query.order_by(ConsoleOpsJob.created_at.desc(), ConsoleOpsJob.id.desc())
        .limit(limit + 1)
        .all()
    )
    has_more = len(rows) > limit
    items_rows = rows[:limit]
    next_cursor = items_rows[-1].created_at.isoformat() if has_more and items_rows else None

    return ConsoleOpsJobListResponse(
        items=[_build_ops_job_record(row) for row in items_rows],
        cursor=next_cursor,
        has_more=has_more,
    )


@router.get(
    "/ops/jobs/{job_id}",
    response_model=ConsoleOpsJobRunResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def get_ops_job(
    job_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleOpsJobRunResponse:
    context = get_console_context(request, db)
    _require_ops_access(context, action="read")

    query = db.query(ConsoleOpsJob).filter(
        ConsoleOpsJob.id == job_id,
        ConsoleOpsJob.client_id == context.client.id,
    )
    allowed_branch_ids = _resolve_branch_scope(context)
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            raise ConsoleAPIError(404, "NOT_FOUND", "Job not found")
        query = query.filter(ConsoleOpsJob.branch_id.in_(allowed_branch_ids))

    job = query.first()
    if not job:
        raise ConsoleAPIError(404, "NOT_FOUND", "Job not found")
    return ConsoleOpsJobRunResponse(job=_build_ops_job_record(job))


@router.post(
    "/ops/jobs/run",
    response_model=ConsoleOpsJobRunResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def run_ops_job(
    body: ConsoleOpsJobRunRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleOpsJobRunResponse:
    context = get_console_context(request, db)
    _require_ops_access(context, action="write")

    params = _parse_ops_job_params(body.params)
    if body.job_type not in _OPS_JOB_DEFINITIONS:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Unknown job_type")

    job = ConsoleOpsJob(
        client_id=context.client.id,
        branch_id=context.effective_branch_id,
        actor_agent_id=context.agent.id,
        job_type=body.job_type,
        mode=body.mode,
        status="success",
        request_payload=_jsonable_payload(
            {
                "job_type": body.job_type,
                "mode": body.mode,
                "params": params,
            }
        ),
    )
    db.add(job)
    db.flush()

    error_code: Optional[str] = None
    generated_at = datetime.now(timezone.utc)
    try:
        if body.job_type == "outbox_process":
            result_payload = await _run_outbox_process_job(
                db,
                context=context,
                mode=body.mode,
                params=params,
            )
        elif body.job_type == "integration_reconcile":
            result_payload = await _run_integration_reconcile_job(
                db,
                context=context,
                mode=body.mode,
                params=params,
            )
        elif body.job_type == "heal":
            result_payload = await _run_heal_job(
                db,
                context=context,
                mode=body.mode,
                params=params,
            )
        elif body.job_type == "metrics_snapshot":
            result_payload = await _run_metrics_snapshot_job(
                db,
                context=context,
                mode=body.mode,
                params=params,
            )
        elif body.job_type == "incident_state":
            result_payload = await _run_incident_state_job(
                db,
                context=context,
                mode=body.mode,
                params=params,
            )
        else:
            raise ConsoleAPIError(400, "INVALID_PARAM", "Unknown job_type")
        job.status = "success"
        job.error_message = None
        job.result_payload = _attach_ops_job_artifact(
            job=job,
            payload=result_payload,
            generated_at=generated_at,
        )
    except ConsoleAPIError as exc:
        error_code = exc.code
        job.status = "failed"
        job.error_message = exc.message
        job.result_payload = _attach_ops_job_artifact(
            job=job,
            payload={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                }
            },
            generated_at=generated_at,
        )
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)[:500]
        job.result_payload = _attach_ops_job_artifact(
            job=job,
            payload={
                "error": {
                    "code": "RUNTIME_ERROR",
                    "message": str(exc),
                }
            },
            generated_at=generated_at,
        )
    job.finished_at = datetime.now(timezone.utc)

    record_audit_event(
        db,
        actor=context.agent,
        event_type="ops_job_run",
        entity_type="ops_job",
        entity_id=job.id,
        payload={
            "job_type": body.job_type,
            "mode": body.mode,
            "status": job.status,
            "error_code": error_code,
            "error_message": job.error_message,
        },
        client_id=context.client.id,
        branch_id=context.effective_branch_id,
    )
    db.commit()
    db.refresh(job)
    return ConsoleOpsJobRunResponse(job=_build_ops_job_record(job))


@router.get(
    "/audit",
    response_model=ConsoleAuditListResponse,
)
async def list_audit_events(
    request: Request,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> ConsoleAuditListResponse:
    """List audit events for the current client."""
    from app.schemas.console import ConsoleAuditListResponse
    from app.services.audit_service import AuditEvent
    
    context = get_console_context(request, db)
    require_console_permission(context, "audit", "read")
    
    _reject_unknown_query_params(request, {"entity_type", "entity_id", "cursor", "limit"})
    _validate_limit(limit)

    query = db.query(AuditEvent).filter(AuditEvent.client_id == context.client.id)

    if context.branch_restricted:
        allowed_branch_ids = {b.id for b in context.branches}
        if not allowed_branch_ids:
            return ConsoleAuditListResponse(items=[], cursor=None, has_more=False)
        query = query.filter(AuditEvent.branch_id.in_(allowed_branch_ids))
    
    if entity_type is not None:
        if entity_type not in {"case", "conversation", "settings", "agent", "branch", "client", "integration"}:
            raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid entity_type")
        query = query.filter(AuditEvent.entity_type == entity_type)
    
    if entity_id is not None:
        eid = _parse_uuid_param("entity_id", entity_id)
        query = query.filter(AuditEvent.entity_id == eid)
    
    query = query.order_by(AuditEvent.created_at.desc())
    
    cursor_date = _parse_cursor_param(cursor)
    if cursor_date is not None:
        query = query.filter(AuditEvent.created_at < cursor_date)
    
    items = query.limit(limit + 1).all()
    
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]
        next_cursor = items[-1].created_at.isoformat()
    else:
        next_cursor = None
    
    return ConsoleAuditListResponse(
        items=[
            ConsoleAuditEvent(
                id=item.id,
                created_at=item.created_at.isoformat(),
                event_type=item.event_type,
                actor_name=item.actor_name,
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                payload=item.payload,
            )
            for item in items
        ],
        cursor=next_cursor,
        has_more=has_more,
    )


@router.get(
    "/settings",
    response_model=ConsoleSettingsResponse,
)
async def get_settings(
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleSettingsResponse:
    """Get settings info: branches, agents, and bot config for the current client."""
    from app.models import Agent
    from app.models.client_settings import ClientSettings
    from app.schemas.console import ConsoleBotConfig, ConsoleSettingsResponse
    
    context = get_console_context(request, db)
    require_console_permission(context, "settings", "read")
    
    # Get all branches for the client
    branches = db.query(Branch).filter(Branch.client_id == context.client.id).all()
    
    # Get all agents for the client
    agents = db.query(Agent).filter(Agent.client_id == context.client.id).all()
    
    # Get client settings
    client_settings = db.query(ClientSettings).filter(ClientSettings.client_id == context.client.id).first()
    
    bot_config = None
    data_sharing = None
    if isinstance(context.client.config, dict):
        data_sharing = context.client.config.get("data_sharing")
    if client_settings:
        bot_config = ConsoleBotConfig(
            reminder_timeout_1=getattr(client_settings, 'reminder_timeout_1', None),
            reminder_timeout_2=getattr(client_settings, 'reminder_timeout_2', None),
            auto_close_timeout=getattr(client_settings, 'auto_close_timeout', None),
            quiet_hours_enabled=getattr(client_settings, 'quiet_hours_enabled', False),
            quiet_hours_start=str(client_settings.quiet_hours_start) if getattr(client_settings, 'quiet_hours_start', None) else None,
            quiet_hours_end=str(client_settings.quiet_hours_end) if getattr(client_settings, 'quiet_hours_end', None) else None,
            tone=getattr(client_settings, 'tone', None),
            autolearn_enabled=getattr(client_settings, 'autolearn_enabled', False),
            booking_enabled=getattr(client_settings, 'booking_enabled', False),
            enable_reminders=getattr(client_settings, 'enable_reminders', True),
            enable_owner_escalation=getattr(client_settings, 'enable_owner_escalation', False),
            learning_consent_status=getattr(client_settings, 'learning_consent_status', None),
            learning_anonymization_mode=getattr(client_settings, 'learning_anonymization_mode', None),
            learning_retention_days=getattr(client_settings, 'learning_retention_days', None),
            data_sharing=data_sharing,
        )
    
    return ConsoleSettingsResponse(
        branches=[_serialize_branch(branch) for branch in branches],
        agents=[
            ConsoleAgentInfo(
                id=a.id,
                name=a.name,
                role=a.role,
                is_active=a.is_active,
            )
            for a in agents
        ],
        bot_config=bot_config,
    )


def _resolve_kpi_status(
    value: object,
    *,
    missing_total: int | None = None,
    estimate: bool = False,
) -> str:
    if value is None:
        return "need"
    if estimate:
        return "estimate"
    if missing_total and missing_total > 0:
        return "need"
    return "fact"


@router.get(
    "/metrics/daily",
    response_model=ConsoleMetricsDailyResponse,
)
async def get_metrics_daily(
    request: Request,
    date: Optional[str] = None,
    trend_days: Optional[int] = None,
    db: Session = Depends(get_db),
) -> ConsoleMetricsDailyResponse:
    """Get daily metrics for cases."""
    from app.schemas.console import ConsoleAnalyticsTrendPoint, ConsoleMetricsDailyResponse
    
    context = get_console_context(request, db)
    require_console_permission(context, "ops", "read")
    
    _reject_unknown_query_params(request, {"date", "trend_days"})

    # Parse date or use today
    if date is not None:
        target_date = _parse_date_param("date", date)
    else:
        target_date = datetime.now(timezone.utc).date()

    resolved_trend_days = trend_days if trend_days is not None else 7
    if resolved_trend_days < 3:
        resolved_trend_days = 3
    if resolved_trend_days > 60:
        resolved_trend_days = 60

    trend_start_date = target_date - timedelta(days=resolved_trend_days - 1)
    
    # Base query for the date
    start_of_day = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_of_day = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)

    base_query = db.query(Handover)
    if context.branch_restricted:
        allowed_branch_ids = {b.id for b in context.branches}
        if not allowed_branch_ids:
            return ConsoleMetricsDailyResponse(
                date=target_date.isoformat(),
                total_cases=0,
                pending_cases=0,
                active_cases=0,
                resolved_cases=0,
                avg_resolution_hours=None,
            )
        base_query = base_query.join(
            Conversation,
            Handover.conversation_id == Conversation.id,
        ).filter(Conversation.branch_id.in_(allowed_branch_ids))
    base_query = base_query.filter(
        Handover.client_id == context.client.id,
        Handover.created_at >= start_of_day,
        Handover.created_at <= end_of_day,
    )
    
    total = base_query.count()
    pending = base_query.filter(Handover.status == "pending").count()
    active = base_query.filter(Handover.status == "active").count()
    resolved = base_query.filter(Handover.status == "resolved").count()
    
    # Calculate average resolution time for resolved cases
    resolved_cases = base_query.filter(
        Handover.status == "resolved",
        Handover.resolved_at.isnot(None)
    ).all()
    
    avg_resolution = None
    if resolved_cases:
        total_hours = sum(
            (c.resolved_at - c.created_at).total_seconds() / 3600
            for c in resolved_cases
            if c.resolved_at
        )
        avg_resolution = round(total_hours / len(resolved_cases), 2)

    metrics_row = db.execute(
        text(
            """
            SELECT
              total_user_messages,
              total_bot_messages
            FROM metrics_daily
            WHERE client_id = :client_id AND metric_date = :metric_date
            """
        ),
        {"client_id": context.client.id, "metric_date": target_date},
    ).mappings().first()
    total_client_messages = metrics_row.get("total_user_messages") if metrics_row else None
    total_bot_messages = metrics_row.get("total_bot_messages") if metrics_row else None

    analytics_row = db.execute(
        text(
            """
            SELECT
              inbound_conversations_total,
              bot_closed_sessions,
              bot_closed_total_sessions,
              bot_closed_incomplete_total,
              bot_closed_rate,
              manager_median_response_seconds,
              manager_time_saved_seconds_estimate,
              booking_total,
              booking_attributed,
              booking_missing_conversation_total,
              booking_conversion_rate,
              first_response_p50_seconds,
              first_response_p90_seconds,
              first_response_missing_total,
              after_hours_total,
              after_hours_covered,
              after_hours_missing_total,
              after_hours_coverage_rate,
              escalation_total,
              escalation_quality_total,
              escalation_meta_missing_total,
              escalation_quality_rate,
              outbox_failed_total,
              outbox_saved_total,
              no_response_alert_total,
              intent_missing_total,
              top_intents,
              top_info_sections
            FROM metrics_analytics_daily
            WHERE client_id = :client_id AND metric_date = :metric_date
            """
        ),
        {"client_id": context.client.id, "metric_date": target_date},
    ).mappings().first()

    inbound_conversations_total = analytics_row.get("inbound_conversations_total") if analytics_row else None
    bot_closed_sessions = analytics_row.get("bot_closed_sessions") if analytics_row else None
    bot_closed_total_sessions = analytics_row.get("bot_closed_total_sessions") if analytics_row else None
    bot_closed_incomplete_total = analytics_row.get("bot_closed_incomplete_total") if analytics_row else None
    bot_closed_rate = analytics_row.get("bot_closed_rate") if analytics_row else None
    manager_median_response_seconds = (
        analytics_row.get("manager_median_response_seconds") if analytics_row else None
    )
    manager_time_saved_seconds_estimate = (
        analytics_row.get("manager_time_saved_seconds_estimate") if analytics_row else None
    )
    booking_total = analytics_row.get("booking_total") if analytics_row else None
    booking_attributed = analytics_row.get("booking_attributed") if analytics_row else None
    booking_missing_conversation_total = (
        analytics_row.get("booking_missing_conversation_total") if analytics_row else None
    )
    booking_conversion_rate = analytics_row.get("booking_conversion_rate") if analytics_row else None
    first_response_p50_seconds = (
        analytics_row.get("first_response_p50_seconds") if analytics_row else None
    )
    first_response_p90_seconds = (
        analytics_row.get("first_response_p90_seconds") if analytics_row else None
    )
    first_response_missing_total = (
        analytics_row.get("first_response_missing_total") if analytics_row else None
    )
    after_hours_total = analytics_row.get("after_hours_total") if analytics_row else None
    after_hours_covered = analytics_row.get("after_hours_covered") if analytics_row else None
    after_hours_missing_total = analytics_row.get("after_hours_missing_total") if analytics_row else None
    after_hours_coverage_rate = analytics_row.get("after_hours_coverage_rate") if analytics_row else None
    escalation_total = analytics_row.get("escalation_total") if analytics_row else None
    escalation_quality_total = analytics_row.get("escalation_quality_total") if analytics_row else None
    escalation_meta_missing_total = (
        analytics_row.get("escalation_meta_missing_total") if analytics_row else None
    )
    escalation_quality_rate = analytics_row.get("escalation_quality_rate") if analytics_row else None
    outbox_failed_total = analytics_row.get("outbox_failed_total") if analytics_row else None
    outbox_saved_total = analytics_row.get("outbox_saved_total") if analytics_row else None
    no_response_alert_total = analytics_row.get("no_response_alert_total") if analytics_row else None
    intent_missing_total = analytics_row.get("intent_missing_total") if analytics_row else None
    top_intents = analytics_row.get("top_intents") if analytics_row else None
    top_info_sections = analytics_row.get("top_info_sections") if analytics_row else None
    if analytics_row and top_intents is None:
        top_intents = []
    if analytics_row and top_info_sections is None:
        top_info_sections = []

    trend_rows = db.execute(
        text(
            """
            SELECT
              metric_date,
              bot_closed_rate,
              booking_conversion_rate,
              first_response_p50_seconds,
              after_hours_coverage_rate,
              escalation_quality_rate,
              outbox_failed_total,
              no_response_alert_total
            FROM metrics_analytics_daily
            WHERE client_id = :client_id
              AND metric_date >= :start_date
              AND metric_date <= :end_date
            ORDER BY metric_date
            """
        ),
        {
            "client_id": context.client.id,
            "start_date": trend_start_date,
            "end_date": target_date,
        },
    ).mappings().all()

    trend_by_date = {row["metric_date"]: row for row in trend_rows}
    analytics_trend = []
    for offset in range(resolved_trend_days):
        metric_date = trend_start_date + timedelta(days=offset)
        row = trend_by_date.get(metric_date)
        analytics_trend.append(
            ConsoleAnalyticsTrendPoint(
                date=metric_date.isoformat(),
                bot_closed_rate=row.get("bot_closed_rate") if row else None,
                booking_conversion_rate=row.get("booking_conversion_rate") if row else None,
                first_response_p50_seconds=row.get("first_response_p50_seconds") if row else None,
                after_hours_coverage_rate=row.get("after_hours_coverage_rate") if row else None,
                escalation_quality_rate=row.get("escalation_quality_rate") if row else None,
                outbox_failed_total=row.get("outbox_failed_total") if row else None,
                no_response_alert_total=row.get("no_response_alert_total") if row else None,
            )
        )

    bot_closed_status = _resolve_kpi_status(
        bot_closed_rate,
        missing_total=bot_closed_incomplete_total,
    )
    manager_time_saved_status = _resolve_kpi_status(
        manager_time_saved_seconds_estimate,
        estimate=True,
    )
    booking_status = _resolve_kpi_status(
        booking_conversion_rate,
        missing_total=booking_missing_conversation_total,
    )
    first_response_status = _resolve_kpi_status(first_response_p50_seconds)
    after_hours_status = _resolve_kpi_status(
        after_hours_coverage_rate,
        missing_total=after_hours_missing_total,
    )
    escalation_quality_status = _resolve_kpi_status(
        escalation_quality_rate,
        missing_total=escalation_meta_missing_total,
    )
    loss_risk_status = _resolve_kpi_status(outbox_failed_total)
    top_intents_status = _resolve_kpi_status(
        top_intents,
        missing_total=intent_missing_total,
    )

    return ConsoleMetricsDailyResponse(
        date=target_date.isoformat(),
        total_cases=total,
        pending_cases=pending,
        active_cases=active,
        resolved_cases=resolved,
        avg_resolution_hours=avg_resolution,
        total_client_messages=total_client_messages,
        total_bot_messages=total_bot_messages,
        inbound_conversations_total=inbound_conversations_total,
        bot_closed_sessions=bot_closed_sessions,
        bot_closed_total_sessions=bot_closed_total_sessions,
        bot_closed_incomplete_total=bot_closed_incomplete_total,
        bot_closed_rate=bot_closed_rate,
        bot_closed_status=bot_closed_status,
        manager_median_response_seconds=manager_median_response_seconds,
        manager_time_saved_seconds_estimate=manager_time_saved_seconds_estimate,
        manager_time_saved_status=manager_time_saved_status,
        booking_total=booking_total,
        booking_attributed=booking_attributed,
        booking_missing_conversation_total=booking_missing_conversation_total,
        booking_conversion_rate=booking_conversion_rate,
        booking_status=booking_status,
        first_response_p50_seconds=first_response_p50_seconds,
        first_response_p90_seconds=first_response_p90_seconds,
        first_response_missing_total=first_response_missing_total,
        first_response_status=first_response_status,
        after_hours_total=after_hours_total,
        after_hours_covered=after_hours_covered,
        after_hours_missing_total=after_hours_missing_total,
        after_hours_coverage_rate=after_hours_coverage_rate,
        after_hours_status=after_hours_status,
        escalation_total=escalation_total,
        escalation_quality_total=escalation_quality_total,
        escalation_meta_missing_total=escalation_meta_missing_total,
        escalation_quality_rate=escalation_quality_rate,
        escalation_quality_status=escalation_quality_status,
        outbox_failed_total=outbox_failed_total,
        outbox_saved_total=outbox_saved_total,
        no_response_alert_total=no_response_alert_total,
        loss_risk_status=loss_risk_status,
        intent_missing_total=intent_missing_total,
        top_intents=top_intents,
        top_info_sections=top_info_sections,
        top_intents_status=top_intents_status,
        analytics_trend=analytics_trend,
    )


@router.get(
    "/telegram/health",
    response_model=ConsoleTelegramHealthResponse,
)
async def get_telegram_health(
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleTelegramHealthResponse:
    from app.models.client_settings import ClientSettings
    from app.services.telegram_service import TelegramService

    context = get_console_context(request, db)
    require_console_permission(context, "ops", "read")
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == context.client.id).first()

    if not settings or not settings.telegram_bot_token:
        return ConsoleTelegramHealthResponse(
            status="error",
            webhook_alive=False,
            last_success_at=None,
            last_error_at=None,
            last_error_message="telegram_bot_token_missing",
            error_rate_24h=0.0,
            pending_messages=0,
        )

    info = TelegramService(settings.telegram_bot_token).get_webhook_info()
    if not info.get("ok"):
        error_message = info.get("description") or info.get("error") or "telegram_webhook_check_failed"
        return ConsoleTelegramHealthResponse(
            status="error",
            webhook_alive=False,
            last_success_at=None,
            last_error_at=None,
            last_error_message=error_message,
            error_rate_24h=0.0,
            pending_messages=0,
        )

    result = info.get("result", {}) if isinstance(info.get("result"), dict) else {}
    webhook_alive = bool(result.get("url"))
    pending_messages = int(result.get("pending_update_count") or 0)
    last_error_date_raw = result.get("last_error_date")
    last_error_at = _format_telegram_timestamp(last_error_date_raw)
    last_error_message = result.get("last_error_message")
    last_error_recent = False
    if last_error_date_raw:
        try:
            last_error_dt = datetime.fromtimestamp(int(last_error_date_raw), tz=timezone.utc)
            last_error_recent = (datetime.now(timezone.utc) - last_error_dt).total_seconds() < 86400
        except (TypeError, ValueError):
            last_error_recent = True
    if last_error_message and not last_error_recent:
        last_error_message = None

    last_success = (
        db.query(func.max(Handover.notified_at))
        .filter(
            Handover.client_id == context.client.id,
            Handover.telegram_message_id.isnot(None),
        )
        .scalar()
    )
    last_success_at = last_success.isoformat() if last_success else None

    status = "ok"
    if not webhook_alive:
        status = "error"
    elif pending_messages > 0 or last_error_recent:
        status = "degraded"

    return ConsoleTelegramHealthResponse(
        status=status,
        webhook_alive=webhook_alive,
        last_success_at=last_success_at,
        last_error_at=last_error_at,
        last_error_message=last_error_message,
        error_rate_24h=0.0,
        pending_messages=pending_messages,
    )


@router.post(
    "/telegram/verify",
    response_model=ConsoleTelegramVerifyResponse,
    responses={400: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def verify_telegram_connector(
    body: ConsoleTelegramVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleTelegramVerifyResponse:
    from app.models.client_settings import ClientSettings
    from app.services.telegram_service import TelegramService

    context = get_console_context(request, db)
    require_console_permission(
        context,
        "settings",
        "write",
        message="Only owner/admin can manage Telegram connector",
    )

    settings = db.query(ClientSettings).filter(ClientSettings.client_id == context.client.id).first()
    branch = None
    branch_id = body.branch_id
    if branch_id:
        branch = (
            db.query(Branch)
            .filter(Branch.id == branch_id, Branch.client_id == context.client.id)
            .first()
        )
        if not branch:
            raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
        ensure_onboarding_step(db, branch, OnboardingStep.TELEGRAM)

    bot_token, chat_id, resolved_branch_id = _resolve_telegram_action_target(
        settings=settings,
        branch=branch,
        scope=body.scope,
        chat_id=body.chat_id,
        branch_id=branch_id,
    )

    verification_code = _generate_verification_code()
    telegram = TelegramService(bot_token)
    result = telegram.send_message(
        chat_id=str(chat_id),
        text=f"Truffles verification code: {verification_code}",
    )
    success = bool(result.get("ok"))
    message_id = result.get("result", {}).get("message_id") if success else None
    delivery_status = "sent" if success else "failed"
    error_message = None if success else result.get("description") or result.get("error")

    record_audit_event(
        db,
        actor=context.agent,
        event_type="telegram_verify_sent" if success else "telegram_verify_failed",
        entity_type="branch" if resolved_branch_id else "client",
        entity_id=resolved_branch_id or context.client.id,
        payload={
            "scope": body.scope,
            "chat_id": str(chat_id),
            "branch_id": str(resolved_branch_id) if resolved_branch_id else None,
            "verification_code": verification_code,
            "message_id": message_id,
            "success": success,
            "error_message": error_message,
        },
        client_id=context.client.id,
        branch_id=resolved_branch_id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
    )
    db.commit()

    return ConsoleTelegramVerifyResponse(
        success=success,
        delivery_status=delivery_status,
        verification_code=verification_code,
        message_id=message_id,
        chat_id=str(chat_id),
        branch_id=resolved_branch_id,
        error_message=error_message,
    )


@router.post(
    "/telegram/test",
    response_model=ConsoleTelegramTestResponse,
    responses={400: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def send_telegram_test(
    body: ConsoleTelegramTestRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleTelegramTestResponse:
    from app.models.client_settings import ClientSettings
    from app.services.telegram_service import TelegramService

    context = get_console_context(request, db)
    require_console_permission(
        context,
        "settings",
        "write",
        message="Only owner/admin can manage Telegram connector",
    )

    settings = db.query(ClientSettings).filter(ClientSettings.client_id == context.client.id).first()
    branch = None
    branch_id = body.branch_id
    if branch_id:
        branch = (
            db.query(Branch)
            .filter(Branch.id == branch_id, Branch.client_id == context.client.id)
            .first()
        )
        if not branch:
            raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
        ensure_onboarding_step(db, branch, OnboardingStep.TELEGRAM)

    bot_token, chat_id, resolved_branch_id = _resolve_telegram_action_target(
        settings=settings,
        branch=branch,
        scope=body.scope,
        chat_id=body.chat_id,
        branch_id=branch_id,
    )

    message = body.message or "Truffles test message"
    telegram = TelegramService(bot_token)
    result = telegram.send_message(
        chat_id=str(chat_id),
        text=message,
    )
    success = bool(result.get("ok"))
    message_id = result.get("result", {}).get("message_id") if success else None
    delivery_status = "sent" if success else "failed"
    error_message = None if success else result.get("description") or result.get("error")

    record_audit_event(
        db,
        actor=context.agent,
        event_type="telegram_test_sent" if success else "telegram_test_failed",
        entity_type="branch" if resolved_branch_id else "client",
        entity_id=resolved_branch_id or context.client.id,
        payload={
            "scope": body.scope,
            "chat_id": str(chat_id),
            "branch_id": str(resolved_branch_id) if resolved_branch_id else None,
            "message": message,
            "message_id": message_id,
            "success": success,
            "error_message": error_message,
        },
        client_id=context.client.id,
        branch_id=resolved_branch_id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
    )
    db.commit()

    return ConsoleTelegramTestResponse(
        success=success,
        delivery_status=delivery_status,
        message_id=message_id,
        chat_id=str(chat_id),
        branch_id=resolved_branch_id,
        error_message=error_message,
    )


def _validate_console_settings_update(body: ConsoleSettingsUpdateRequest) -> None:
    if body.reminder_1_minutes is not None and not 5 <= body.reminder_1_minutes <= 60:
        raise ConsoleAPIError(400, "INVALID_INPUT", "reminder_1_minutes must be between 5 and 60")
    if body.reminder_2_minutes is not None and not 30 <= body.reminder_2_minutes <= 180:
        raise ConsoleAPIError(400, "INVALID_INPUT", "reminder_2_minutes must be between 30 and 180")
    if body.escalation_timeout_minutes is not None and not 30 <= body.escalation_timeout_minutes <= 360:
        raise ConsoleAPIError(
            400,
            "INVALID_INPUT",
            "escalation_timeout_minutes must be between 30 and 360",
        )
    if (
        body.reminder_1_minutes is not None
        and body.reminder_2_minutes is not None
        and body.reminder_1_minutes >= body.reminder_2_minutes
    ):
        raise ConsoleAPIError(
            400,
            "INVALID_INPUT",
            "reminder_1_minutes must be less than reminder_2_minutes",
        )
    if (
        body.reminder_2_minutes is not None
        and body.escalation_timeout_minutes is not None
        and body.reminder_2_minutes >= body.escalation_timeout_minutes
    ):
        raise ConsoleAPIError(
            400,
            "INVALID_INPUT",
            "reminder_2_minutes must be less than escalation_timeout_minutes",
        )


def _apply_console_settings_update(
    settings: ClientSettings,
    body: ConsoleSettingsUpdateRequest,
) -> list[str]:
    updated_fields: list[str] = []
    if body.reminder_1_minutes is not None:
        settings.reminder_timeout_1 = body.reminder_1_minutes
        updated_fields.append("reminder_timeout_1")
    if body.reminder_2_minutes is not None:
        settings.reminder_timeout_2 = body.reminder_2_minutes
        updated_fields.append("reminder_timeout_2")
    if body.escalation_timeout_minutes is not None:
        settings.auto_close_timeout = body.escalation_timeout_minutes
        updated_fields.append("auto_close_timeout")
    return updated_fields


@router.patch(
    "/settings",
    response_model=ConsoleSettingsUpdateResponse,
    responses={403: {"model": ConsoleErrorResponse}},
)
async def update_settings(
    request: Request,
    body: ConsoleSettingsUpdateRequest,
    db: Session = Depends(get_db),
) -> ConsoleSettingsUpdateResponse:
    """Update client settings (owner/admin only)."""
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "settings",
        "write",
        message="Only owner/admin can update settings",
    )

    _validate_console_settings_update(body)

    settings = db.query(ClientSettings).filter(
        ClientSettings.client_id == context.client.id
    ).first()

    if not settings:
        settings = ClientSettings(client_id=context.client.id)
        db.add(settings)

    updated_fields = _apply_console_settings_update(settings, body)

    db.commit()

    record_audit_event(
        db,
        client_id=context.client.id,
        actor_id=str(context.agent.id),
        actor_name=context.agent.name,
        event_type="settings_updated",
        entity_type="client_settings",
        entity_id=str(context.client.id),
        payload={"updated_fields": updated_fields},
    )

    return ConsoleSettingsUpdateResponse(
        success=True,
        message=f"Updated: {', '.join(updated_fields)}" if updated_fields else "No changes"
    )


@router.get(
    "/onboarding/status",
    response_model=ConsoleOnboardingStatusResponse,
    responses={400: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def get_onboarding_status(
    request: Request,
    branch_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
) -> ConsoleOnboardingStatusResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "provisioning",
        "read",
        message="Only owner/admin can access onboarding",
    )
    branch = _resolve_branch_for_onboarding(context, branch_id=branch_id)
    status = build_onboarding_status(db, branch)
    return _serialize_onboarding_status(branch, status)


@router.get(
    "/onboarding/scorecard",
    response_model=ConsoleOnboardingScorecardResponse,
    responses={400: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def get_onboarding_scorecard(
    request: Request,
    branch_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
) -> ConsoleOnboardingScorecardResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "provisioning",
        "read",
        message="Only owner/admin can access onboarding",
    )
    branch = _resolve_branch_for_onboarding(context, branch_id=branch_id)
    scorecard = build_onboarding_scorecard(db, branch)
    return _serialize_onboarding_scorecard(branch, scorecard)


@router.post(
    "/onboarding/advance",
    response_model=ConsoleOnboardingStatusResponse,
    responses={400: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}, 409: {"model": ConsoleErrorResponse}},
)
async def advance_onboarding(
    body: ConsoleOnboardingAdvanceRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleOnboardingStatusResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage onboarding",
    )
    branch = _resolve_branch_for_onboarding(context, branch_id=body.branch_id)
    status = advance_onboarding_step(
        db,
        branch,
        OnboardingStep(body.step_id),
        actor=context.agent,
    )
    db.commit()
    return _serialize_onboarding_status(branch, status)


@router.post(
    "/confirmations",
    response_model=ConsoleConfirmationResponse,
    responses={400: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def create_console_confirmation(
    body: ConsoleConfirmationCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleConfirmationResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "settings",
        "write",
        message="Only owner/admin can request confirmations",
    )
    confirmation = create_confirmation(
        db,
        context,
        action=body.action,
        target_type=body.target_type,
        target_id=body.target_id,
        reason=body.reason,
    )
    db.commit()
    return ConsoleConfirmationResponse(
        confirmation_id=confirmation.id,
        action=confirmation.action,
        target_type=confirmation.target_type,
        target_id=confirmation.target_id,
        expires_at=confirmation.expires_at.isoformat(),
    )


@router.get(
    "/knowledge/current",
    response_model=ConsoleKnowledgeCurrentResponse,
    responses={400: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def get_knowledge_current(
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleKnowledgeCurrentResponse:
    context = get_console_context(request, db)
    require_console_permission(context, "knowledge", "read")
    branch = _resolve_branch_from_context(context)
    version = get_current_published(db, branch_id=branch.id)
    if not version:
        return ConsoleKnowledgeCurrentResponse(version_id=None, payload=None, content=None)
    content = version.pack_yaml or dump_pack_yaml(version.payload_json)
    return ConsoleKnowledgeCurrentResponse(
        version_id=version.id,
        payload=version.payload_json,
        content=content or None,
    )


@router.post(
    "/knowledge/validate",
    response_model=ConsoleKnowledgeValidateResponse,
    responses={400: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def validate_knowledge(
    body: ConsoleKnowledgeValidateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleKnowledgeValidateResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "knowledge",
        "write",
        message="Only owner/admin can manage knowledge",
    )
    branch = _resolve_branch_from_context(context)
    ensure_onboarding_step(db, branch, OnboardingStep.KNOWLEDGE)
    onboarding_inputs = build_onboarding_inputs(db, branch)
    require_booking = (
        onboarding_inputs.capabilities.features.booking_mode is not None
        if onboarding_inputs.has_capabilities
        else None
    )
    current = get_current_published(db, branch_id=branch.id)
    current_payload = current.payload_json if current else None
    payload, errors, warnings, diff = validate_draft(
        body.draft_text,
        current_payload=current_payload,
        domain_slug=onboarding_inputs.reference_pack_domain_slug,
        require_booking=require_booking,
    )
    valid = not errors
    draft_hash = build_knowledge_draft_hash(body.draft_text)
    if payload:
        upsert_draft(
            db,
            branch_id=branch.id,
            client_id=context.client.id,
            payload_json=payload,
            actor_id=context.agent.id,
        )
        record_audit_event(
            db,
            actor=context.agent,
            event_type="knowledge_validate",
            entity_type="branch",
            entity_id=branch.id,
            payload=build_knowledge_validate_payload(
                valid=valid,
                errors=errors,
                warnings=warnings,
                draft_hash=draft_hash,
            ),
            client_id=context.client.id,
            branch_id=branch.id,
            actor_id=context.agent.id,
            actor_name=context.agent.name,
        )
        db.commit()
    return ConsoleKnowledgeValidateResponse(
        valid=valid,
        errors=errors,
        warnings=warnings,
        diff=diff or None,
    )


@router.post(
    "/knowledge/publish",
    response_model=ConsoleKnowledgePublishResponse,
    responses={400: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}, 409: {"model": ConsoleErrorResponse}},
)
async def publish_knowledge(
    body: ConsoleKnowledgePublishRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleKnowledgePublishResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "knowledge",
        "write",
        message="Only owner/admin can manage knowledge",
    )
    branch = _resolve_branch_from_context(context)
    ensure_onboarding_step(db, branch, OnboardingStep.KNOWLEDGE)
    onboarding_inputs = build_onboarding_inputs(db, branch)
    require_booking = (
        onboarding_inputs.capabilities.features.booking_mode is not None
        if onboarding_inputs.has_capabilities
        else None
    )
    draft_hash = build_knowledge_draft_hash(body.draft_text)

    if not body.skip_preflight_check:
        has_preflight = has_recent_knowledge_preflight(
            db=db,
            client_id=context.client.id,
            branch_id=branch.id,
            draft_hash=draft_hash,
            window_minutes=DEFAULT_PREFLIGHT_WINDOW_MINUTES,
        )
        if not has_preflight:
            raise ConsoleAPIError(
                409,
                "KNOWLEDGE_PREFLIGHT_REQUIRED",
                "Run Validate for this draft before Publish",
                {
                    "draft_hash": draft_hash,
                    "window_minutes": DEFAULT_PREFLIGHT_WINDOW_MINUTES,
                },
            )

    current = get_current_published(db, branch_id=branch.id)
    current_payload = current.payload_json if current else None
    payload, errors, warnings, _diff = validate_draft(
        body.draft_text,
        current_payload=current_payload,
        domain_slug=onboarding_inputs.reference_pack_domain_slug,
        require_booking=require_booking,
    )
    if not payload or errors:
        raise ConsoleAPIError(
            400,
            "KNOWLEDGE_INVALID",
            "Knowledge validation failed",
            {"errors": errors, "warnings": warnings},
        )

    try:
        version = publish_version(
            db,
            branch=branch,
            payload_json=payload,
            actor_id=context.agent.id,
            source_version_id=current.id if current else None,
        )
        db.commit()
    except PackCompilerError as exc:
        raise ConsoleAPIError(
            400,
            "KNOWLEDGE_INVALID",
            "Pack compiler validation failed",
            {"errors": exc.errors},
        ) from exc

    now = datetime.now(timezone.utc)
    try:
        sync_published_branch_docs(
            db,
            client_slug=context.client.name,
            branch=branch,
            version=version,
            backfill_other_branches=True,
        )
        compiled = extract_compiled_artifacts(version.payload_json, compile_if_missing=False)
        pack_index = compiled.get("pack_index") if isinstance(compiled, dict) else None
        if pack_index:
            compiled_at = parse_compiled_at(compiled.get("compiled_at") if isinstance(compiled, dict) else None)
            apply_pack_index_to_client_config(
                context.client,
                pack_index=pack_index,
                version_id=version.id,
                compiled_at=compiled_at or now,
                source="knowledge_publish",
                compiled_meta=build_compiled_pack_meta(
                    compiled,
                    version_id=version.id,
                    source="knowledge_publish",
                )
                if isinstance(compiled, dict)
                else None,
            )
        branch.knowledge_safe_mode = False
        branch.knowledge_safe_mode_reason = None
        branch.knowledge_safe_mode_at = now
        record_audit_event(
            db,
            actor=context.agent,
            event_type="knowledge_publish",
            entity_type="branch",
            entity_id=branch.id,
            payload={
                "version_id": str(version.id),
                "warnings": warnings,
                "draft_hash": draft_hash,
                "skip_preflight_check": body.skip_preflight_check,
            },
            client_id=context.client.id,
            branch_id=branch.id,
            actor_id=context.agent.id,
            actor_name=context.agent.name,
        )
        db.commit()
    except Exception as exc:
        branch.knowledge_safe_mode = True
        branch.knowledge_safe_mode_reason = str(exc)
        branch.knowledge_safe_mode_at = now
        record_audit_event(
            db,
            actor=context.agent,
            event_type="knowledge_publish_failed",
            entity_type="branch",
            entity_id=branch.id,
            payload={
                "version_id": str(version.id),
                "error": str(exc),
                "draft_hash": draft_hash,
                "skip_preflight_check": body.skip_preflight_check,
            },
            client_id=context.client.id,
            branch_id=branch.id,
            actor_id=context.agent.id,
            actor_name=context.agent.name,
        )
        db.commit()
        raise ConsoleAPIError(
            500,
            "KNOWLEDGE_SYNC_FAILED",
            "Knowledge publish failed",
            {"error": str(exc)},
        ) from exc

    return ConsoleKnowledgePublishResponse(
        success=True,
        version_id=version.id,
        published_at=version.published_at.isoformat() if version.published_at else None,
        message="Knowledge published",
    )


@router.get(
    "/knowledge/history",
    response_model=ConsoleKnowledgeHistoryResponse,
    responses={400: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_knowledge_history(
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleKnowledgeHistoryResponse:
    context = get_console_context(request, db)
    require_console_permission(context, "knowledge", "read")
    branch = _resolve_branch_from_context(context)
    items = list_history(db, branch_id=branch.id)
    return ConsoleKnowledgeHistoryResponse(
        items=[
            ConsoleKnowledgeHistoryItem(
                id=item.id,
                status=item.status,
                created_at=item.created_at.isoformat() if item.created_at else None,
                published_at=item.published_at.isoformat() if item.published_at else None,
                summary=item.summary,
            )
            for item in items
        ]
    )


@router.post(
    "/knowledge/rollback",
    response_model=ConsoleKnowledgeRollbackResponse,
    responses={
        400: {"model": ConsoleErrorResponse},
        403: {"model": ConsoleErrorResponse},
        404: {"model": ConsoleErrorResponse},
        409: {"model": ConsoleErrorResponse},
    },
)
async def rollback_knowledge(
    body: ConsoleKnowledgeRollbackRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleKnowledgeRollbackResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "knowledge",
        "write",
        message="Only owner/admin can manage knowledge",
    )
    branch = _resolve_branch_from_context(context)

    confirmation = require_confirmation(
        db,
        context,
        confirmation_id=body.confirmation_id,
        action="knowledge_rollback",
        target_type="knowledge_version",
        target_id=body.version_id,
    )

    version = (
        db.query(KnowledgeVersion)
        .filter(
            KnowledgeVersion.id == body.version_id,
            KnowledgeVersion.branch_id == branch.id,
        )
        .first()
    )
    if not version:
        raise ConsoleAPIError(404, "NOT_FOUND", "Knowledge version not found")
    if version.status == "draft":
        raise ConsoleAPIError(400, "INVALID_PARAM", "Cannot rollback to draft version")

    try:
        restored = restore_version(
            db,
            branch=branch,
            source_version=version,
            actor_id=context.agent.id,
        )
        db.commit()
    except PackCompilerError as exc:
        raise ConsoleAPIError(
            400,
            "KNOWLEDGE_INVALID",
            "Pack compiler validation failed",
            {"errors": exc.errors},
        ) from exc

    now = datetime.now(timezone.utc)
    try:
        sync_published_branch_docs(
            db,
            client_slug=context.client.name,
            branch=branch,
            version=restored,
            backfill_other_branches=True,
        )
        compiled = extract_compiled_artifacts(restored.payload_json, compile_if_missing=False)
        pack_index = compiled.get("pack_index") if isinstance(compiled, dict) else None
        if pack_index:
            compiled_at = parse_compiled_at(compiled.get("compiled_at") if isinstance(compiled, dict) else None)
            apply_pack_index_to_client_config(
                context.client,
                pack_index=pack_index,
                version_id=restored.id,
                compiled_at=compiled_at or now,
                source="knowledge_rollback",
                compiled_meta=build_compiled_pack_meta(
                    compiled,
                    version_id=restored.id,
                    source="knowledge_rollback",
                )
                if isinstance(compiled, dict)
                else None,
            )
        branch.knowledge_safe_mode = False
        branch.knowledge_safe_mode_reason = None
        branch.knowledge_safe_mode_at = now
        mark_confirmation_used(
            db,
            context,
            confirmation,
            action="knowledge_rollback",
            target_type="knowledge_version",
            target_id=body.version_id,
            outcome="success",
        )
        record_audit_event(
            db,
            actor=context.agent,
            event_type="knowledge_rollback",
            entity_type="branch",
            entity_id=branch.id,
            payload={
                "from_version_id": str(version.id),
                "to_version_id": str(restored.id),
            },
            client_id=context.client.id,
            branch_id=branch.id,
            actor_id=context.agent.id,
            actor_name=context.agent.name,
        )
        db.commit()
    except Exception as exc:
        branch.knowledge_safe_mode = True
        branch.knowledge_safe_mode_reason = str(exc)
        branch.knowledge_safe_mode_at = now
        mark_confirmation_used(
            db,
            context,
            confirmation,
            action="knowledge_rollback",
            target_type="knowledge_version",
            target_id=body.version_id,
            outcome="sync_failed",
        )
        record_audit_event(
            db,
            actor=context.agent,
            event_type="knowledge_rollback_failed",
            entity_type="branch",
            entity_id=branch.id,
            payload={
                "from_version_id": str(version.id),
                "to_version_id": str(restored.id),
                "error": str(exc),
            },
            client_id=context.client.id,
            branch_id=branch.id,
            actor_id=context.agent.id,
            actor_name=context.agent.name,
        )
        db.commit()
        raise ConsoleAPIError(
            500,
            "KNOWLEDGE_SYNC_FAILED",
            "Knowledge rollback failed",
            {"error": str(exc)},
        ) from exc

    return ConsoleKnowledgeRollbackResponse(
        success=True,
        version_id=restored.id,
    )


@router.get(
    "/learning/candidates",
    response_model=ConsoleLearningCandidateListResponse,
    responses={400: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_learning_candidates(
    request: Request,
    status: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=200),
    cursor: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> ConsoleLearningCandidateListResponse:
    context = get_console_context(request, db)
    require_console_permission(context, "knowledge", "read")
    branch = _resolve_branch_from_context(context)

    query = (
        db.query(LearnedResponse)
        .filter(
            LearnedResponse.client_id == context.client.id,
            LearnedResponse.branch_id == branch.id,
        )
    )
    if status:
        normalized = status.strip().lower()
        if normalized not in {"pending", "approved", "rejected"}:
            raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid status")
        query = query.filter(LearnedResponse.status == normalized)

    cursor_date = _parse_cursor_param(cursor)
    if cursor_date is not None:
        query = query.filter(LearnedResponse.created_at < cursor_date)

    items = (
        query.order_by(LearnedResponse.created_at.desc())
        .limit(limit + 1)
        .all()
    )
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]

    next_cursor = items[-1].created_at.isoformat() if has_more and items else None
    policy = get_learning_policy(db, context.client.id)
    now = datetime.now(timezone.utc)

    def _serialize_candidate(item: LearnedResponse) -> ConsoleLearningCandidate:
        can_approve, reason = _resolve_learning_candidate_eligibility(
            item,
            policy=policy,
            now=now,
        )
        return ConsoleLearningCandidate(
            id=item.id,
            status=item.status,
            question_text=item.question_text,
            response_text=item.response_text,
            source_name=item.source_name,
            source_role=item.source_role,
            source_channel=item.source_channel,
            candidate_type=item.candidate_type,
            branch_id=item.branch_id,
            handover_id=item.handover_id,
            created_at=item.created_at.isoformat() if item.created_at else None,
            updated_at=item.updated_at.isoformat() if item.updated_at else None,
            approved_at=item.approved_at.isoformat() if item.approved_at else None,
            rejected_at=item.rejected_at.isoformat() if item.rejected_at else None,
            retention_expires_at=(
                item.retention_expires_at.isoformat()
                if item.retention_expires_at
                else None
            ),
            consent_status=item.consent_status,
            anonymization_mode=item.anonymization_mode,
            can_approve=can_approve,
            ineligible_reason=_format_learning_block_reason(reason) if not can_approve else None,
        )

    return ConsoleLearningCandidateListResponse(
        items=[_serialize_candidate(item) for item in items],
        cursor=next_cursor,
        has_more=has_more,
    )


@router.post(
    "/learning/candidates/{candidate_id}/approve",
    response_model=ConsoleLearningCandidateActionResponse,
    responses={400: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def approve_learning_candidate(
    candidate_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleLearningCandidateActionResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "knowledge",
        "write",
        message="Only owner/admin can approve learning candidates",
    )
    branch = _resolve_branch_from_context(context)

    learned = (
        db.query(LearnedResponse)
        .filter(
            LearnedResponse.id == candidate_id,
            LearnedResponse.client_id == context.client.id,
        )
        .first()
    )
    if not learned:
        raise ConsoleAPIError(404, "NOT_FOUND", "Learning candidate not found")
    if learned.branch_id and learned.branch_id != branch.id:
        raise ConsoleAPIError(403, "BRANCH_ACCESS_DENIED", "Access to this branch denied")
    if not is_agent_allowed_to_approve(db, learned_response=learned, agent=context.agent):
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Access denied")

    if learned.status == "approved":
        return ConsoleLearningCandidateActionResponse(success=True, message="Already approved")
    if learned.status == "rejected":
        return ConsoleLearningCandidateActionResponse(success=False, message="Already rejected")

    policy = get_learning_policy(db, context.client.id)
    allowed, reason = _resolve_learning_candidate_eligibility(
        learned,
        policy=policy,
        now=datetime.now(timezone.utc),
    )
    if not allowed:
        return ConsoleLearningCandidateActionResponse(
            success=False,
            message=f"Blocked: {_format_learning_block_reason(reason)}",
        )

    applied = approve_learned_response(
        db,
        learned_response=learned,
        actor_id=context.agent.id,
    )
    db.commit()
    record_audit_event(
        db,
        client_id=context.client.id,
        branch_id=branch.id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
        event_type="learning_candidate_approved",
        entity_type="learned_response",
        entity_id=learned.id,
        payload={"applied_to_pack": applied},
    )

    message = "Approved and applied" if applied else "Approved (not applied)"
    return ConsoleLearningCandidateActionResponse(success=True, message=message)


@router.post(
    "/learning/candidates/{candidate_id}/reject",
    response_model=ConsoleLearningCandidateActionResponse,
    responses={400: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def reject_learning_candidate(
    candidate_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleLearningCandidateActionResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "knowledge",
        "write",
        message="Only owner/admin can reject learning candidates",
    )
    branch = _resolve_branch_from_context(context)

    learned = (
        db.query(LearnedResponse)
        .filter(
            LearnedResponse.id == candidate_id,
            LearnedResponse.client_id == context.client.id,
        )
        .first()
    )
    if not learned:
        raise ConsoleAPIError(404, "NOT_FOUND", "Learning candidate not found")
    if learned.branch_id and learned.branch_id != branch.id:
        raise ConsoleAPIError(403, "BRANCH_ACCESS_DENIED", "Access to this branch denied")
    if not is_agent_allowed_to_approve(db, learned_response=learned, agent=context.agent):
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Access denied")

    if learned.status == "rejected":
        return ConsoleLearningCandidateActionResponse(success=True, message="Already rejected")
    if learned.status == "approved":
        return ConsoleLearningCandidateActionResponse(success=False, message="Already approved")

    reject_learned_response(
        db,
        learned_response=learned,
        actor_id=context.agent.id,
    )
    db.commit()
    record_audit_event(
        db,
        client_id=context.client.id,
        branch_id=branch.id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
        event_type="learning_candidate_rejected",
        entity_type="learned_response",
        entity_id=learned.id,
        payload=None,
    )

    return ConsoleLearningCandidateActionResponse(success=True, message="Rejected")


@router.get(
    "/admin/companies",
    response_model=ConsoleCompanyListResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_companies(
    request: Request,
    cursor: Optional[str] = None,
    limit: int = 50,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ConsoleCompanyListResponse:
    context = get_console_context(request, db, require_selection=False)
    _require_platform_admin(context)
    _reject_unknown_query_params(request, {"cursor", "limit", "q"})
    _validate_limit(limit)

    query = db.query(Company)
    query_value = _normalize_search_query("q", q) if q else None
    if query_value:
        query_value_lower = query_value.lower()
        uuid_value = _looks_like_uuid(query_value)
        if uuid_value:
            query = query.filter(Company.id == uuid_value)
        else:
            query = query.filter(func.lower(Company.name).like(f"%{query_value_lower}%"))

    cursor_date = _parse_cursor_param(cursor)
    if cursor_date is not None:
        query = query.filter(Company.created_at < cursor_date)

    items = (
        query.order_by(Company.created_at.desc(), Company.id.desc())
        .limit(limit + 1)
        .all()
    )
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]
    next_cursor = items[-1].created_at.isoformat() if has_more and items[-1].created_at else None

    return ConsoleCompanyListResponse(
        items=[
            ConsoleCompany(
                id=company.id,
                name=company.name,
                billing_info=company.billing_info,
            )
            for company in items
        ],
        cursor=next_cursor,
        has_more=has_more,
    )


@router.get(
    "/admin/clients",
    response_model=ConsoleClientListResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_clients(
    request: Request,
    cursor: Optional[str] = None,
    limit: int = 50,
    q: Optional[str] = None,
    company_id: Optional[str] = None,
    lifecycle: Optional[str] = None,
    include_fleet: Optional[str] = None,
    include_summary: Optional[str] = None,
    fleet_lifecycle: Optional[str] = None,
    payment_status: Optional[str] = None,
    service_state: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ConsoleClientListResponse:
    lifecycle_mode = _parse_tenant_lifecycle_param(lifecycle)
    include_fleet_mode = _parse_bool_param("include_fleet", include_fleet, default=False)
    include_summary_mode = _parse_bool_param("include_summary", include_summary, default=False)
    fleet_lifecycle_filter = _parse_fleet_lifecycle_param(fleet_lifecycle)
    payment_status_filter = _parse_fleet_payment_param(payment_status)
    service_state_filter = _parse_fleet_service_param(service_state)
    if fleet_lifecycle_filter or payment_status_filter or service_state_filter:
        include_fleet_mode = True
    if include_summary_mode:
        include_fleet_mode = True
    context = get_console_context(
        request,
        db,
        require_selection=False,
        include_inactive_tenants=lifecycle_mode != "active",
    )
    _require_platform_admin(context)
    _reject_unknown_query_params(
        request,
        {
            "cursor",
            "limit",
            "q",
            "company_id",
            "lifecycle",
            "include_fleet",
            "include_summary",
            "fleet_lifecycle",
            "payment_status",
            "service_state",
        },
    )
    _validate_limit(limit)

    accessible_client_ids = _accessible_client_ids(context)
    accessible_clients_hash = _hash_uuid_values(accessible_client_ids)
    company_uuid = _parse_uuid_param("company_id", company_id)
    query_value = _normalize_search_query("q", q) if q else None
    cursor_date = _parse_cursor_param(cursor)

    def _build_client_query(cursor_cutoff: Optional[datetime]):
        return _build_clients_query_for_scope(
            db,
            accessible_client_ids=accessible_client_ids,
            lifecycle_mode=lifecycle_mode,
            company_uuid=company_uuid,
            query_value=query_value,
            cursor_cutoff=cursor_cutoff,
        )

    clients: list[Client] = []
    has_more = False
    if fleet_lifecycle_filter or payment_status_filter or service_state_filter:
        scan_cursor = cursor_date
        batch_size = max(limit * 3, 50)
        matched_clients: list[Client] = []
        while len(matched_clients) <= limit:
            batch = (
                _build_client_query(scan_cursor)
                .order_by(Client.created_at.desc(), Client.id.desc())
                .limit(batch_size)
                .all()
            )
            if not batch:
                break

            batch_company_ids = {client.company_id for client in batch if client.company_id}
            batch_companies_by_id: dict[UUID, Company] = {}
            if batch_company_ids:
                batch_companies = db.query(Company).filter(Company.id.in_(batch_company_ids)).all()
                batch_companies_by_id = {company.id: company for company in batch_companies}
            batch_details = _load_or_build_fleet_client_details_map(
                db,
                clients=batch,
                companies_by_id=batch_companies_by_id,
                persist_missing=_TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_ENABLED,
                persist_missing_max_clients=_TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_MAX_CLIENTS,
            )

            for client in batch:
                details = batch_details.get(client.id)
                if not details:
                    continue
                if not _fleet_client_matches_filters(
                    details,
                    fleet_lifecycle=fleet_lifecycle_filter,
                    payment_status=payment_status_filter,
                    service_state=service_state_filter,
                ):
                    continue
                matched_clients.append(client)
                if len(matched_clients) > limit:
                    break

            if len(matched_clients) > limit:
                break
            if len(batch) < batch_size:
                break
            scan_cursor = batch[-1].created_at

        has_more = len(matched_clients) > limit
        clients = matched_clients[:limit] if has_more else matched_clients
    else:
        clients = (
            _build_client_query(cursor_date)
            .order_by(Client.created_at.desc(), Client.id.desc())
            .limit(limit + 1)
            .all()
        )
        has_more = len(clients) > limit
        if has_more:
            clients = clients[:limit]

    next_cursor = clients[-1].created_at.isoformat() if has_more and clients and clients[-1].created_at else None

    company_ids = {client.company_id for client in clients if client.company_id}
    companies_by_id: dict[UUID, Company] = {}
    if company_ids:
        companies = db.query(Company).filter(Company.id.in_(company_ids)).all()
        companies_by_id = {company.id: company for company in companies}

    fleet_details_map: dict[UUID, _FleetClientDetails] = {}
    if include_fleet_mode:
        fleet_details_map = _load_or_build_fleet_client_details_map(
            db,
            clients=clients,
            companies_by_id=companies_by_id,
            persist_missing=_TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_ENABLED,
            persist_missing_max_clients=_TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_MAX_CLIENTS,
        )

    summary = None
    if include_summary_mode:
        summary_scope_key = _build_clients_summary_cache_scope_key(
            accessible_clients_hash=accessible_clients_hash,
            company_uuid=company_uuid,
            lifecycle_mode=lifecycle_mode,
            query_value=query_value,
            fleet_lifecycle_filter=fleet_lifecycle_filter,
            payment_status_filter=payment_status_filter,
            service_state_filter=service_state_filter,
        )
        summary_cache_now = datetime.now(timezone.utc)
        summary_batch_size = max(limit * 4, 100)
        summary = _load_cached_fleet_summary(
            db,
            scope_key=summary_scope_key,
            now=summary_cache_now,
        )
        if summary is None:
            summary = _build_fleet_summary_for_scope(
                db,
                build_client_query=_build_client_query,
                fleet_lifecycle=fleet_lifecycle_filter,
                payment_status=payment_status_filter,
                service_state=service_state_filter,
                batch_size=summary_batch_size,
                persist_projection_missing=_TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_ENABLED,
                persist_projection_missing_max_clients=_TENANTS_FLEET_CLIENT_PROJECTION_REQUEST_PERSIST_MAX_CLIENTS,
            )
            _store_cached_fleet_summary(
                db,
                scope_key=summary_scope_key,
                scope_company_id=company_uuid,
                now=summary_cache_now,
                summary=summary,
            )
        else:
            _schedule_fleet_summary_async_refresh(
                db,
                scope_key=summary_scope_key,
                accessible_client_ids=accessible_client_ids,
                lifecycle_mode=lifecycle_mode,
                company_uuid=company_uuid,
                query_value=query_value,
                fleet_lifecycle_filter=fleet_lifecycle_filter,
                payment_status_filter=payment_status_filter,
                service_state_filter=service_state_filter,
                batch_size=summary_batch_size,
                now=summary_cache_now,
            )

    return ConsoleClientListResponse(
        items=[
            ConsoleClient(
                id=client.id,
                slug=client.name,
                name=client.name,
                status=client.status,
                company_id=client.company_id,
                company_name=companies_by_id.get(client.company_id).name
                if client.company_id and client.company_id in companies_by_id
                else None,
                lifecycle_state=fleet_details_map[client.id].lifecycle_state if client.id in fleet_details_map else None,
                payment_status=fleet_details_map[client.id].payment_status if client.id in fleet_details_map else None,
                commercial_state=fleet_details_map[client.id].commercial_state if client.id in fleet_details_map else None,
                service_state=fleet_details_map[client.id].service_state if client.id in fleet_details_map else None,
                owner_name=fleet_details_map[client.id].owner_name if client.id in fleet_details_map else None,
                next_action=fleet_details_map[client.id].next_action if client.id in fleet_details_map else None,
                total_branches=fleet_details_map[client.id].total_branches if client.id in fleet_details_map else None,
                active_branches=fleet_details_map[client.id].active_branches if client.id in fleet_details_map else None,
                degraded_branches=fleet_details_map[client.id].degraded_branches if client.id in fleet_details_map else None,
                go_live_ready_branches=fleet_details_map[client.id].go_live_ready_branches
                if client.id in fleet_details_map
                else None,
                reference_branch_ids=list(fleet_details_map[client.id].reference_branch_ids)
                if client.id in fleet_details_map
                else None,
                reference_branch_reason=fleet_details_map[client.id].reference_branch_reason
                if client.id in fleet_details_map
                else None,
            )
            for client in clients
        ],
        cursor=next_cursor,
        has_more=has_more,
        summary=summary,
    )


@router.get(
    "/admin/branches",
    response_model=ConsoleBranchListResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_branches(
    request: Request,
    cursor: Optional[str] = None,
    limit: int = 50,
    q: Optional[str] = None,
    company_id: Optional[str] = None,
    client_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    lifecycle: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ConsoleBranchListResponse:
    lifecycle_mode = _parse_tenant_lifecycle_param(lifecycle)
    context = get_console_context(
        request,
        db,
        require_selection=False,
        include_inactive_tenants=lifecycle_mode != "active",
    )
    _require_platform_admin(context)
    _reject_unknown_query_params(request, {"cursor", "limit", "q", "company_id", "client_id", "branch_id", "lifecycle"})
    _validate_limit(limit)

    company_uuid = _parse_uuid_param("company_id", company_id)
    client_uuid = _parse_uuid_param("client_id", client_id)
    branch_uuid = _parse_uuid_param("branch_id", branch_id)
    query = db.query(Branch)
    client_join_applied = False

    def _ensure_client_join() -> None:
        nonlocal query, client_join_applied
        if client_join_applied:
            return
        query = query.join(Client, Client.id == Branch.client_id)
        client_join_applied = True

    if company_uuid:
        _require_company_access(context, company_uuid)
        _ensure_client_join()
        query = query.filter(Client.company_id == company_uuid)
    if lifecycle_mode == "active":
        _ensure_client_join()
        query = query.filter(
            Client.status == "active",
            Branch.is_active.is_(True),
        )
    elif lifecycle_mode == "archived":
        query = query.filter(Branch.is_active.is_(False))
    if client_uuid:
        _require_client_access(context, client_uuid)
        if company_uuid is not None:
            resolved_company_id = _resolve_company_id_for_client_in_context(context, client_uuid)
            if resolved_company_id is None:
                resolved_company_id = (
                    db.query(Client.company_id)
                    .filter(Client.id == client_uuid)
                    .scalar()
                )
            if resolved_company_id != company_uuid:
                raise ConsoleAPIError(400, "INVALID_PARAM", "client_id does not belong to company_id")
        query = query.filter(Branch.client_id == client_uuid)
    if branch_uuid:
        _require_branch_access(context, branch_uuid, message="Branch belongs to another tenant")
        branch_scope = (
            db.query(Branch.client_id.label("client_id"), Client.company_id.label("company_id"))
            .join(Client, Client.id == Branch.client_id)
            .filter(Branch.id == branch_uuid)
            .first()
        )
        if branch_scope is None:
            return ConsoleBranchListResponse(items=[], cursor=None, has_more=False)
        if client_uuid is not None and branch_scope.client_id != client_uuid:
            raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id does not belong to client_id")
        if company_uuid is not None and branch_scope.company_id != company_uuid:
            raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id does not belong to company_id")
        query = query.filter(Branch.id == branch_uuid)

    query_value = _normalize_search_query("q", q) if q else None
    if query_value:
        query_value_lower = query_value.lower()
        uuid_value = _looks_like_uuid(query_value)
        filters = []
        if uuid_value:
            filters.append(Branch.id == uuid_value)
        filters.extend(
            [
                func.lower(Branch.name).like(f"%{query_value_lower}%"),
                func.lower(Branch.slug).like(f"%{query_value_lower}%"),
                func.lower(Branch.instance_id).like(f"%{query_value_lower}%"),
                func.lower(Branch.phone).like(f"%{query_value_lower}%"),
            ]
        )
        query = query.filter(or_(*filters))

    cursor_date = _parse_cursor_param(cursor)
    if cursor_date is not None:
        query = query.filter(Branch.created_at < cursor_date)

    items = (
        query.order_by(Branch.created_at.desc(), Branch.id.desc())
        .limit(limit + 1)
        .all()
    )
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]
    next_cursor = items[-1].created_at.isoformat() if has_more and items[-1].created_at else None

    return ConsoleBranchListResponse(
        items=[_serialize_branch(branch) for branch in items],
        cursor=next_cursor,
        has_more=has_more,
    )


@router.get(
    "/admin/tenants/portfolio",
    response_model=ConsoleTenantsPortfolioResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def get_tenants_portfolio(
    request: Request,
    cursor: Optional[str] = None,
    limit: int = 20,
    q: Optional[str] = None,
    company_id: Optional[str] = None,
    lifecycle: Optional[str] = None,
    attention_limit: int = 20,
    stale_after_minutes: int = Query(
        _INTEGRATION_DEFAULT_STALE_MINUTES,
        ge=_INTEGRATION_MIN_STALE_MINUTES,
        le=_INTEGRATION_MAX_STALE_MINUTES,
    ),
    include_low: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ConsoleTenantsPortfolioResponse:
    started_at = perf_counter()
    try:
        _reject_unknown_query_params(
            request,
            {
                "cursor",
                "limit",
                "q",
                "company_id",
                "lifecycle",
                "attention_limit",
                "stale_after_minutes",
                "include_low",
            },
        )
        _validate_limit(limit)
        _validate_limit(attention_limit)
        lifecycle_mode = _parse_tenant_lifecycle_param(lifecycle)

        clients_request = _request_with_query_params(
            request,
            {
                "cursor": cursor,
                "limit": limit,
                "q": q,
                "company_id": company_id,
                "lifecycle": lifecycle_mode,
                "include_fleet": "true",
                "include_summary": "true",
            },
        )
        clients_response = await list_clients(
            request=clients_request,
            cursor=cursor,
            limit=limit,
            q=q,
            company_id=company_id,
            lifecycle=lifecycle_mode,
            include_fleet="true",
            include_summary="true",
            db=db,
        )

        attention_request = _request_with_query_params(
            request,
            {
                "limit": attention_limit,
                "stale_after_minutes": stale_after_minutes,
                "include_low": include_low,
            },
        )
        attention_response = await list_fleet_attention(
            request=attention_request,
            limit=attention_limit,
            stale_after_minutes=stale_after_minutes,
            include_low=include_low,
            db=db,
        )

        return ConsoleTenantsPortfolioResponse(
            generated_at=datetime.now(timezone.utc).isoformat(),
            clients=clients_response,
            fleet_attention=attention_response,
        )
    finally:
        record_tenants_endpoint_latency("portfolio", (perf_counter() - started_at) * 1000.0)


@router.get(
    "/admin/tenants/company-cockpit",
    response_model=ConsoleTenantsCompanyCockpitResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def get_tenants_company_cockpit(
    request: Request,
    company_id: str,
    client_id: Optional[str] = None,
    include_branches: Optional[str] = None,
    lifecycle: Optional[str] = None,
    client_limit: int = 20,
    branch_limit: int = 20,
    client_cursor: Optional[str] = None,
    branch_cursor: Optional[str] = None,
    client_q: Optional[str] = None,
    branch_q: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ConsoleTenantsCompanyCockpitResponse:
    started_at = perf_counter()
    try:
        _reject_unknown_query_params(
            request,
            {
                "company_id",
                "client_id",
                "include_branches",
                "lifecycle",
                "client_limit",
                "branch_limit",
                "client_cursor",
                "branch_cursor",
                "client_q",
                "branch_q",
            },
        )
        _validate_limit(client_limit)
        _validate_limit(branch_limit)
        lifecycle_mode = _parse_tenant_lifecycle_param(lifecycle)
        include_branches_mode = _parse_bool_param("include_branches", include_branches, default=True)

        company_uuid = _parse_uuid_param("company_id", company_id)
        if company_uuid is None:
            raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid company_id")

        selected_client_uuid = _parse_uuid_param("client_id", client_id)

        clients_request = _request_with_query_params(
            request,
            {
                "cursor": client_cursor,
                "limit": client_limit,
                "q": client_q,
                "company_id": str(company_uuid),
                "lifecycle": lifecycle_mode,
                "include_fleet": "true",
            },
        )
        clients_response = await list_clients(
            request=clients_request,
            cursor=client_cursor,
            limit=client_limit,
            q=client_q,
            company_id=str(company_uuid),
            lifecycle=lifecycle_mode,
            include_fleet="true",
            db=db,
        )

        branches_response = ConsoleBranchListResponse(items=[], cursor=None, has_more=False)
        if include_branches_mode:
            branches_request = _request_with_query_params(
                request,
                {
                    "cursor": branch_cursor,
                    "limit": branch_limit,
                    "q": branch_q,
                    "company_id": str(company_uuid),
                    "client_id": str(selected_client_uuid) if selected_client_uuid else None,
                    "lifecycle": lifecycle_mode,
                },
            )
            branches_response = await list_branches(
                request=branches_request,
                cursor=branch_cursor,
                limit=branch_limit,
                q=branch_q,
                company_id=str(company_uuid),
                client_id=str(selected_client_uuid) if selected_client_uuid else None,
                lifecycle=lifecycle_mode,
                db=db,
            )

        return ConsoleTenantsCompanyCockpitResponse(
            generated_at=datetime.now(timezone.utc).isoformat(),
            company_id=company_uuid,
            selected_client_id=selected_client_uuid,
            clients=clients_response,
            branches=branches_response,
        )
    finally:
        record_tenants_endpoint_latency("company_cockpit", (perf_counter() - started_at) * 1000.0)


@router.get(
    "/admin/tenants/weekly-snapshots",
    response_model=ConsoleTenantsWeeklySnapshotListResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_tenants_weekly_snapshots(
    request: Request,
    client_id: str,
    week_key: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = 12,
    db: Session = Depends(get_db),
) -> ConsoleTenantsWeeklySnapshotListResponse:
    context = get_console_context(request, db, require_selection=False)
    _require_platform_admin(context)
    _reject_unknown_query_params(request, {"client_id", "week_key", "cursor", "limit"})
    _validate_limit(limit)

    client_uuid = _parse_uuid_param("client_id", client_id)
    if client_uuid is None:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid client_id")

    normalized_week_key = _normalize_tenants_weekly_snapshot_week_key(week_key) if week_key else None
    cursor_date = _parse_cursor_param(cursor)

    try:
        query = db.query(TenantsWeeklySnapshot).filter(
            TenantsWeeklySnapshot.client_id == client_uuid,
        )
        if normalized_week_key:
            query = query.filter(TenantsWeeklySnapshot.week_key == normalized_week_key)
        if cursor_date is not None:
            query = query.filter(TenantsWeeklySnapshot.updated_at < cursor_date)

        rows = (
            query.order_by(TenantsWeeklySnapshot.updated_at.desc(), TenantsWeeklySnapshot.id.desc())
            .limit(limit + 1)
            .all()
        )
        has_more = len(rows) > limit
        items = rows[:limit]
        next_cursor = items[-1].updated_at.isoformat() if has_more and items else None
        serialized_items = [_serialize_tenants_weekly_snapshot_row(item) for item in items]
        return ConsoleTenantsWeeklySnapshotListResponse(
            items=serialized_items,
            cursor=next_cursor,
            has_more=has_more,
            storage_mode="table",
            schema_versions=_build_weekly_snapshot_schema_versions(serialized_items),
        )
    except ProgrammingError as exc:
        if not _is_tenants_weekly_snapshot_table_missing_error(exc):
            raise
        db.rollback()

    # Read-only fallback for environments where migration is not applied yet.
    audit_query = db.query(AuditEvent).filter(
        AuditEvent.client_id == client_uuid,
        AuditEvent.event_type == _TENANTS_WEEKLY_SNAPSHOT_EVENT_TYPE,
        AuditEvent.entity_type == _TENANTS_WEEKLY_SNAPSHOT_ENTITY_TYPE,
    )
    if cursor_date is not None:
        audit_query = audit_query.filter(AuditEvent.created_at < cursor_date)

    candidates = (
        audit_query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(max(limit * 4, 50))
        .all()
    )
    if normalized_week_key:
        candidates = [
            event
            for event in candidates
            if isinstance(event.payload, dict) and event.payload.get("week_key") == normalized_week_key
        ]

    has_more = len(candidates) > limit
    items = candidates[:limit] if has_more else candidates
    next_cursor = items[-1].created_at.isoformat() if has_more and items else None
    serialized_items = [_serialize_tenants_weekly_snapshot_record(item) for item in items]

    return ConsoleTenantsWeeklySnapshotListResponse(
        items=serialized_items,
        cursor=next_cursor,
        has_more=has_more,
        storage_mode="audit_fallback",
        schema_versions=_build_weekly_snapshot_schema_versions(serialized_items),
    )


@router.post(
    "/admin/tenants/weekly-snapshots",
    response_model=ConsoleTenantsWeeklySnapshotCreateResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def save_tenants_weekly_snapshot(
    request: Request,
    payload: ConsoleTenantsWeeklySnapshotCreateRequest,
    db: Session = Depends(get_db),
) -> ConsoleTenantsWeeklySnapshotCreateResponse:
    context = get_console_context(request, db, require_selection=False)
    _require_platform_admin(context)

    client = db.query(Client).filter(Client.id == payload.client_id).first()
    if client is None:
        raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")

    normalized_week_key = _normalize_tenants_weekly_snapshot_week_key(payload.week_key)
    normalized_snapshot = _normalize_tenants_weekly_snapshot_payload(payload.snapshot)
    now = datetime.now(timezone.utc)
    try:
        existing = (
            db.query(TenantsWeeklySnapshot)
            .filter(
                TenantsWeeklySnapshot.client_id == payload.client_id,
                TenantsWeeklySnapshot.week_key == normalized_week_key,
            )
            .first()
        )
    except ProgrammingError as exc:
        if not _is_tenants_weekly_snapshot_table_missing_error(exc):
            raise
        db.rollback()
        raise ConsoleAPIError(
            503,
            "TENANTS_WEEKLY_SNAPSHOT_STORAGE_UNAVAILABLE",
            "Weekly snapshots storage unavailable (read-only mode)",
        ) from exc

    if existing is None:
        existing = TenantsWeeklySnapshot(
            client_id=payload.client_id,
            week_key=normalized_week_key,
            created_at=now,
        )

    existing.snapshot = normalized_snapshot
    existing.snapshot_schema_version = "v1"
    existing.actor_id = context.agent.id
    existing.actor_name = context.agent.name
    existing.updated_at = now
    db.add(existing)
    db.commit()
    db.refresh(existing)
    return ConsoleTenantsWeeklySnapshotCreateResponse(
        item=_serialize_tenants_weekly_snapshot_row(existing),
    )


@router.post(
    "/admin/tenants/sensitive-access",
    response_model=ConsoleTenantsSensitiveAccessAuditResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def audit_tenants_sensitive_access(
    request: Request,
    payload: ConsoleTenantsSensitiveAccessAuditRequest,
    db: Session = Depends(get_db),
) -> ConsoleTenantsSensitiveAccessAuditResponse:
    context = get_console_context(request, db, require_selection=False)
    _require_platform_admin(context)

    field = _normalize_tenants_sensitive_access_field(payload.field)
    action = _normalize_tenants_sensitive_access_action(payload.action)
    context_value = (payload.context or "").strip() or None
    if context_value and len(context_value) > 64:
        raise ConsoleAPIError(400, "INVALID_PARAM", "context too long")

    branch = db.query(Branch).filter(Branch.id == payload.branch_id).first()
    if branch is None:
        raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")

    event = record_audit_event(
        db,
        actor=context.agent,
        event_type=_TENANTS_SENSITIVE_ACCESS_EVENT_TYPE,
        entity_type="branch",
        entity_id=branch.id,
        payload={
            "field": field,
            "action": action,
            "context": context_value,
        },
        client_id=branch.client_id,
        branch_id=branch.id,
    )
    db.commit()
    db.refresh(event)
    return ConsoleTenantsSensitiveAccessAuditResponse(
        ok=True,
        audit_id=event.id,
    )


@router.get(
    "/admin/marketing/segments",
    response_model=ConsoleMarketingSegmentCatalogResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def get_marketing_segments_catalog(
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleMarketingSegmentCatalogResponse:
    context = get_console_context(request, db, require_selection=True, include_inactive_tenants=False)
    _require_marketing_access(context, action="view")
    return ConsoleMarketingSegmentCatalogResponse(items=get_marketing_segment_catalog())


@router.get(
    "/admin/marketing/campaigns",
    response_model=ConsoleMarketingCampaignListResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_marketing_campaigns(
    request: Request,
    branch_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ConsoleMarketingCampaignListResponse:
    context = get_console_context(request, db, require_selection=True, include_inactive_tenants=False)
    _require_marketing_access(context, action="view")
    _reject_unknown_query_params(request, {"branch_id", "status"})

    branch_uuid = _parse_uuid_param("branch_id", branch_id)
    status_value = _normalize_optional_text(status)
    if status_value and status_value not in MARKETING_STATUS_VALUES:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid status")
    normalized_status = normalize_marketing_status(status_value) if status_value else None

    query = db.query(MarketingCampaign).filter(MarketingCampaign.client_id == context.client.id)
    if branch_uuid is not None:
        _resolve_marketing_branch(context, db, branch_uuid)
        query = query.filter(MarketingCampaign.branch_id == branch_uuid)
    if normalized_status:
        query = query.filter(
            or_(
                MarketingCampaign.status_v2 == normalized_status,
                and_(
                    MarketingCampaign.status_v2.is_(None),
                    MarketingCampaign.status.in_([status_value, normalized_status]),
                ),
            )
        )

    campaigns = query.order_by(MarketingCampaign.created_at.desc(), MarketingCampaign.id.desc()).all()
    return ConsoleMarketingCampaignListResponse(
        items=[_serialize_marketing_campaign(campaign) for campaign in campaigns],
    )


@router.post(
    "/admin/marketing/campaigns",
    response_model=ConsoleMarketingCampaignCreateResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def create_marketing_campaign(
    request: Request,
    payload: ConsoleMarketingCampaignCreateRequest,
    db: Session = Depends(get_db),
) -> ConsoleMarketingCampaignCreateResponse:
    context = get_console_context(request, db, require_selection=True, include_inactive_tenants=False)
    _require_marketing_access(context, action="create")

    branch = _resolve_marketing_branch(context, db, payload.branch_id)
    name = _normalize_required_text(payload.name, "name")
    message_text = _normalize_required_text(payload.message_text, "message_text")
    segment_code = _normalize_required_text(payload.segment_code, "segment_code")
    if segment_code not in MARKETING_SEGMENT_CODES:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Unsupported segment_code")
    segment_params = _normalize_marketing_segment_params_or_error(
        segment_code=segment_code,
        raw_params=payload.segment_params,
    )
    segment_summary = build_marketing_segment_summary(segment_code, segment_params)
    if len(name) > 120:
        raise ConsoleAPIError(400, "INVALID_PARAM", "name too long")
    if len(message_text) > 2000:
        raise ConsoleAPIError(400, "INVALID_PARAM", "message_text too long")

    now = datetime.now(timezone.utc)
    campaign = MarketingCampaign(
        client_id=context.client.id,
        branch_id=branch.id,
        created_by=context.agent.id,
        name=name,
        message_text=message_text,
        status=MARKETING_STATUS_DRAFT,
        status_v2=MARKETING_STATUS_DRAFT,
        segment_code=segment_code,
        audience_mode=payload.audience_mode,
        audience_filter={
            "segment_params": segment_params,
            "segment_summary": segment_summary,
        },
        preview_total=0,
        preflight_snapshot={},
        preflight_valid=False,
        created_at=now,
        updated_at=now,
    )
    db.add(campaign)
    db.flush()

    record_audit_event(
        db,
        client_id=context.client.id,
        branch_id=branch.id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
        event_type="marketing_campaign_created",
        entity_type="marketing_campaign",
        entity_id=campaign.id,
        payload={
            "campaign_name": campaign.name,
            "audience_mode": campaign.audience_mode,
            "segment_code": campaign.segment_code,
            "segment_params": segment_params,
        },
    )
    db.commit()
    db.refresh(campaign)

    return ConsoleMarketingCampaignCreateResponse(campaign=_serialize_marketing_campaign(campaign))


@router.patch(
    "/admin/marketing/campaigns/{campaign_id}",
    response_model=ConsoleMarketingCampaignCreateResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def update_marketing_campaign(
    campaign_id: str,
    request: Request,
    payload: ConsoleMarketingCampaignUpdateRequest,
    db: Session = Depends(get_db),
) -> ConsoleMarketingCampaignCreateResponse:
    context = get_console_context(request, db, require_selection=True, include_inactive_tenants=False)
    _require_marketing_access(context, action="update")

    campaign_uuid = _parse_uuid_param("campaign_id", campaign_id)
    if campaign_uuid is None:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid campaign_id")
    campaign = _resolve_marketing_campaign(context, db, campaign_uuid)
    _resolve_marketing_branch(context, db, campaign.branch_id)
    current_status = resolve_marketing_campaign_status(campaign)
    if current_status not in _MARKETING_EDITABLE_STATUSES:
        raise ConsoleAPIError(409, "INVALID_STATE", "Campaign can be edited only before approval")

    changed_fields: list[str] = []
    if payload.name is not None:
        normalized_name = _normalize_required_text(payload.name, "name")
        if normalized_name != campaign.name:
            campaign.name = normalized_name
            changed_fields.append("name")

    if payload.message_text is not None:
        normalized_message = _normalize_required_text(payload.message_text, "message_text")
        if normalized_message != campaign.message_text:
            campaign.message_text = normalized_message
            changed_fields.append("message_text")

    if payload.segment_code is not None:
        normalized_segment = _normalize_required_text(payload.segment_code, "segment_code")
        if normalized_segment not in MARKETING_SEGMENT_CODES:
            raise ConsoleAPIError(400, "INVALID_PARAM", "Unsupported segment_code")
        if normalized_segment != campaign.segment_code:
            campaign.segment_code = normalized_segment
            changed_fields.append("segment_code")

    current_segment_code = (
        campaign.segment_code if campaign.segment_code in MARKETING_SEGMENT_CODES else "reactivation_30_120"
    )
    current_segment_params = resolve_campaign_segment_params(
        campaign,
        segment_code=current_segment_code,
        strict=False,
    )
    next_segment_params = current_segment_params
    if payload.segment_params is not None:
        next_segment_params = _normalize_marketing_segment_params_or_error(
            segment_code=current_segment_code,
            raw_params=payload.segment_params,
        )
    elif payload.segment_code is not None:
        next_segment_params = _normalize_marketing_segment_params_or_error(
            segment_code=current_segment_code,
            raw_params=None,
        )

    if next_segment_params != current_segment_params:
        changed_fields.append("segment_params")

    if not changed_fields:
        raise ConsoleAPIError(400, "INVALID_PARAM", "No campaign fields changed")

    now = datetime.now(timezone.utc)
    db.query(MarketingCampaignRecipient).filter(MarketingCampaignRecipient.campaign_id == campaign.id).delete()
    audience_filter = campaign.audience_filter if isinstance(campaign.audience_filter, dict) else {}
    audience_filter.pop("preview_stats", None)
    audience_filter["segment_params"] = next_segment_params
    audience_filter["segment_summary"] = build_marketing_segment_summary(
        current_segment_code,
        next_segment_params,
    )
    campaign.audience_filter = audience_filter
    campaign.preview_total = 0
    campaign.last_preview_at = None
    campaign.preflight_valid = False
    campaign.preflight_snapshot = {
        "generated_at": now.isoformat(),
        "reason": "campaign_updated_preview_required",
        "changed_fields": sorted(changed_fields),
        "eligible_count": 0,
        "suppressed_count": 0,
    }
    campaign.updated_at = now
    db.add(campaign)

    record_audit_event(
        db,
        client_id=context.client.id,
        branch_id=campaign.branch_id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
        event_type="marketing_campaign_updated",
        entity_type="marketing_campaign",
        entity_id=campaign.id,
        payload={
            "changed_fields": sorted(changed_fields),
            "reason": _normalize_optional_text(payload.reason),
        },
    )
    db.commit()
    db.refresh(campaign)
    return ConsoleMarketingCampaignCreateResponse(campaign=_serialize_marketing_campaign(campaign))


@router.post(
    "/admin/marketing/campaigns/{campaign_id}/preview",
    response_model=ConsoleMarketingCampaignPreviewResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def preview_marketing_campaign(
    campaign_id: str,
    request: Request,
    payload: ConsoleMarketingCampaignPreviewRequest,
    db: Session = Depends(get_db),
) -> ConsoleMarketingCampaignPreviewResponse:
    context = get_console_context(request, db, require_selection=True, include_inactive_tenants=False)
    _require_marketing_access(context, action="preview")

    campaign_uuid = _parse_uuid_param("campaign_id", campaign_id)
    if campaign_uuid is None:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid campaign_id")

    campaign = _resolve_marketing_campaign(context, db, campaign_uuid)
    _resolve_marketing_branch(context, db, campaign.branch_id)
    sample_limit = _normalize_marketing_sample_limit(payload.sample_limit)
    now = datetime.now(timezone.utc)
    preview = materialize_marketing_campaign_audience(
        db,
        campaign=campaign,
        segment_code=campaign.segment_code,
        sample_limit=sample_limit,
        now=now,
    )
    record_audit_event(
        db,
        client_id=context.client.id,
        branch_id=campaign.branch_id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
        event_type="marketing_campaign_previewed",
        entity_type="marketing_campaign",
        entity_id=campaign.id,
        payload={
            "estimated_recipients": preview["estimated_recipients"],
            "eligible_count": preview["eligible_count"],
            "suppressed_count": preview["suppressed_count"],
        },
    )
    db.commit()

    return ConsoleMarketingCampaignPreviewResponse(
        campaign_id=campaign.id,
        branch_id=campaign.branch_id,
        audience_mode=campaign.audience_mode,
        estimated_recipients=preview["estimated_recipients"],
        eligible_count=preview["eligible_count"],
        suppressed_count=preview["suppressed_count"],
        segment_params=preview["segment_params"],
        segment_summary=preview["segment_summary"],
        sample_conversation_ids=preview["sample_conversation_ids"],
        sample_recipient_jids=preview["sample_recipient_jids"],
        funnel=ConsoleMarketingAudienceFunnel(
            candidate_count=int(preview.get("candidate_count") or 0),
            matched_count=int(preview.get("matched_count") or 0),
            segment_excluded_count=int(preview.get("segment_excluded_count") or 0),
            eligible_count=int(preview.get("eligible_count") or 0),
            suppressed_count=int(preview.get("suppressed_count") or 0),
            suppression_reason_counts={
                str(reason): int(count or 0)
                for reason, count in (preview.get("suppression_reason_counts") or {}).items()
            },
        ),
    )


@router.get(
    "/admin/marketing/campaigns/{campaign_id}/audience",
    response_model=ConsoleMarketingCampaignAudienceResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def get_marketing_campaign_audience(
    campaign_id: str,
    request: Request,
    include_suppressed: bool = True,
    limit: int = Query(_MARKETING_AUDIENCE_LIMIT_DEFAULT),
    db: Session = Depends(get_db),
) -> ConsoleMarketingCampaignAudienceResponse:
    context = get_console_context(request, db, require_selection=True, include_inactive_tenants=False)
    _require_marketing_access(context, action="view audience")
    _reject_unknown_query_params(request, {"include_suppressed", "limit"})

    campaign_uuid = _parse_uuid_param("campaign_id", campaign_id)
    if campaign_uuid is None:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid campaign_id")
    limit_value = _normalize_marketing_audience_limit(limit)

    campaign = _resolve_marketing_campaign(context, db, campaign_uuid)
    _resolve_marketing_branch(context, db, campaign.branch_id)
    items = fetch_marketing_audience_preview(
        db,
        campaign_id=campaign.id,
        include_suppressed=include_suppressed,
        limit=limit_value,
    )
    total_count = (
        db.query(func.count(MarketingCampaignRecipient.id))
        .filter(MarketingCampaignRecipient.campaign_id == campaign.id)
        .scalar()
        or 0
    )
    suppressed_count = (
        db.query(func.count(MarketingCampaignRecipient.id))
        .filter(
            MarketingCampaignRecipient.campaign_id == campaign.id,
            MarketingCampaignRecipient.suppressed.is_(True),
        )
        .scalar()
        or 0
    )
    return ConsoleMarketingCampaignAudienceResponse(
        campaign_id=campaign.id,
        total_count=int(total_count),
        eligible_count=max(int(total_count) - int(suppressed_count), 0),
        suppressed_count=int(suppressed_count),
        items=[_serialize_marketing_recipient(item) for item in items],
    )


@router.post(
    "/admin/marketing/campaigns/{campaign_id}/request-approval",
    response_model=ConsoleMarketingCampaignCreateResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def request_marketing_campaign_approval(
    campaign_id: str,
    request: Request,
    payload: ConsoleMarketingCampaignLifecycleActionRequest,
    db: Session = Depends(get_db),
) -> ConsoleMarketingCampaignCreateResponse:
    context = get_console_context(request, db, require_selection=True, include_inactive_tenants=False)
    _require_marketing_access(context, action="request approval")
    campaign_uuid = _parse_uuid_param("campaign_id", campaign_id)
    if campaign_uuid is None:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid campaign_id")
    campaign = _resolve_marketing_campaign(context, db, campaign_uuid)
    _resolve_marketing_branch(context, db, campaign.branch_id)

    now = datetime.now(timezone.utc)
    try:
        mark_campaign_under_review(campaign, now=now)
    except ValueError:
        raise ConsoleAPIError(409, "INVALID_STATE", "Campaign cannot be moved to in_review")
    db.add(campaign)
    record_audit_event(
        db,
        client_id=context.client.id,
        branch_id=campaign.branch_id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
        event_type="marketing_campaign_review_requested",
        entity_type="marketing_campaign",
        entity_id=campaign.id,
        payload={"reason": _normalize_optional_text(payload.reason)},
    )
    db.commit()
    db.refresh(campaign)
    return ConsoleMarketingCampaignCreateResponse(campaign=_serialize_marketing_campaign(campaign))


@router.post(
    "/admin/marketing/campaigns/{campaign_id}/approve",
    response_model=ConsoleMarketingCampaignCreateResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def approve_marketing_campaign(
    campaign_id: str,
    request: Request,
    payload: ConsoleMarketingCampaignLifecycleActionRequest,
    db: Session = Depends(get_db),
) -> ConsoleMarketingCampaignCreateResponse:
    context = get_console_context(request, db, require_selection=True, include_inactive_tenants=False)
    _require_marketing_access(context, action="approve")
    campaign_uuid = _parse_uuid_param("campaign_id", campaign_id)
    if campaign_uuid is None:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid campaign_id")
    campaign = _resolve_marketing_campaign(context, db, campaign_uuid)
    _resolve_marketing_branch(context, db, campaign.branch_id)

    now = datetime.now(timezone.utc)
    try:
        mark_campaign_approved(campaign, approved_by=context.agent.id, now=now)
    except ValueError:
        raise ConsoleAPIError(409, "INVALID_STATE", "Campaign cannot be approved from current state")
    db.add(campaign)
    record_audit_event(
        db,
        client_id=context.client.id,
        branch_id=campaign.branch_id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
        event_type="marketing_campaign_approved",
        entity_type="marketing_campaign",
        entity_id=campaign.id,
        payload={"reason": _normalize_optional_text(payload.reason)},
    )
    db.commit()
    db.refresh(campaign)
    return ConsoleMarketingCampaignCreateResponse(campaign=_serialize_marketing_campaign(campaign))


@router.get(
    "/admin/marketing/campaigns/{campaign_id}/preflight",
    response_model=ConsoleMarketingCampaignPreflightResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def get_marketing_campaign_preflight(
    campaign_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleMarketingCampaignPreflightResponse:
    context = get_console_context(request, db, require_selection=True, include_inactive_tenants=False)
    _require_marketing_access(context, action="view preflight")
    campaign_uuid = _parse_uuid_param("campaign_id", campaign_id)
    if campaign_uuid is None:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid campaign_id")
    campaign = _resolve_marketing_campaign(context, db, campaign_uuid)
    _resolve_marketing_branch(context, db, campaign.branch_id)

    refresh_marketing_campaign_lifecycle(db, campaign=campaign)
    snapshot = build_marketing_campaign_preflight(db, campaign=campaign)
    db.commit()
    outbox_health = snapshot.get("outbox_health") if isinstance(snapshot.get("outbox_health"), dict) else {}
    return ConsoleMarketingCampaignPreflightResponse(
        campaign_id=campaign.id,
        generated_at=str(snapshot.get("generated_at") or datetime.now(timezone.utc).isoformat()),
        preflight_valid=bool(snapshot.get("preflight_valid")),
        blocked_reasons=[str(value) for value in snapshot.get("blocked_reasons", [])],
        outbox_health_status=str(outbox_health.get("status") or "unknown"),
        outbox_pending=int(outbox_health.get("pending") or 0),
        outbox_failed_24h=int(outbox_health.get("failed_24h") or 0),
        provider_billing_blocked=bool(snapshot.get("provider_billing_blocked")),
        provider_billing_blocked_count=int(snapshot.get("provider_billing_blocked_count") or 0),
        audience_total=int(snapshot.get("audience_total") or 0),
        eligible_count=int(snapshot.get("eligible_count") or 0),
        suppressed_count=int(snapshot.get("suppressed_count") or 0),
        segment_params=snapshot.get("segment_params") if isinstance(snapshot.get("segment_params"), dict) else {},
        segment_summary=(
            str(snapshot.get("segment_summary")).strip()
            if isinstance(snapshot.get("segment_summary"), str)
            else None
        ),
        preview_stats=_serialize_marketing_audience_funnel(snapshot.get("preview_stats")),
        template_gate_enabled=bool(snapshot.get("template_gate_enabled")),
        template_state=snapshot.get("template_state"),
        template_ok=bool(snapshot.get("template_ok", True)),
    )


@router.post(
    "/admin/marketing/campaigns/{campaign_id}/pause",
    response_model=ConsoleMarketingCampaignCreateResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def pause_marketing_campaign(
    campaign_id: str,
    request: Request,
    payload: ConsoleMarketingCampaignLifecycleActionRequest,
    db: Session = Depends(get_db),
) -> ConsoleMarketingCampaignCreateResponse:
    context = get_console_context(request, db, require_selection=True, include_inactive_tenants=False)
    _require_marketing_access(context, action="pause")
    campaign_uuid = _parse_uuid_param("campaign_id", campaign_id)
    if campaign_uuid is None:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid campaign_id")
    campaign = _resolve_marketing_campaign(context, db, campaign_uuid)
    _resolve_marketing_branch(context, db, campaign.branch_id)

    try:
        mark_campaign_paused(campaign)
    except ValueError:
        raise ConsoleAPIError(409, "INVALID_STATE", "Campaign cannot be paused from current state")
    db.add(campaign)
    record_audit_event(
        db,
        client_id=context.client.id,
        branch_id=campaign.branch_id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
        event_type="marketing_campaign_paused",
        entity_type="marketing_campaign",
        entity_id=campaign.id,
        payload={"reason": _normalize_optional_text(payload.reason)},
    )
    db.commit()
    db.refresh(campaign)
    return ConsoleMarketingCampaignCreateResponse(campaign=_serialize_marketing_campaign(campaign))


@router.post(
    "/admin/marketing/campaigns/{campaign_id}/resume",
    response_model=ConsoleMarketingCampaignCreateResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def resume_marketing_campaign(
    campaign_id: str,
    request: Request,
    payload: ConsoleMarketingCampaignLifecycleActionRequest,
    db: Session = Depends(get_db),
) -> ConsoleMarketingCampaignCreateResponse:
    context = get_console_context(request, db, require_selection=True, include_inactive_tenants=False)
    _require_marketing_access(context, action="resume")
    campaign_uuid = _parse_uuid_param("campaign_id", campaign_id)
    if campaign_uuid is None:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid campaign_id")
    campaign = _resolve_marketing_campaign(context, db, campaign_uuid)
    _resolve_marketing_branch(context, db, campaign.branch_id)

    try:
        mark_campaign_resume(campaign)
    except ValueError:
        raise ConsoleAPIError(409, "INVALID_STATE", "Campaign cannot be resumed from current state")
    db.add(campaign)
    record_audit_event(
        db,
        client_id=context.client.id,
        branch_id=campaign.branch_id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
        event_type="marketing_campaign_resumed",
        entity_type="marketing_campaign",
        entity_id=campaign.id,
        payload={"reason": _normalize_optional_text(payload.reason)},
    )
    db.commit()
    db.refresh(campaign)
    return ConsoleMarketingCampaignCreateResponse(campaign=_serialize_marketing_campaign(campaign))


@router.post(
    "/admin/marketing/campaigns/{campaign_id}/execute",
    response_model=ConsoleMarketingCampaignExecuteResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def execute_marketing_campaign(
    campaign_id: str,
    request: Request,
    payload: ConsoleMarketingCampaignExecuteRequest,
    db: Session = Depends(get_db),
) -> ConsoleMarketingCampaignExecuteResponse:
    context = get_console_context(request, db, require_selection=True, include_inactive_tenants=False)
    _require_marketing_access(context, action="execute")
    if not payload.confirm_send:
        raise ConsoleAPIError(409, "CONFIRMATION_REQUIRED", "Use confirm_send=true to execute campaign")

    campaign_uuid = _parse_uuid_param("campaign_id", campaign_id)
    if campaign_uuid is None:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid campaign_id")

    campaign = _resolve_marketing_campaign(context, db, campaign_uuid)
    _resolve_marketing_branch(context, db, campaign.branch_id)
    max_recipients = _normalize_marketing_max_recipients(payload.max_recipients)

    now = datetime.now(timezone.utc)
    try:
        result = run_marketing_campaign_execute(
            db,
            campaign=campaign,
            message_text=campaign.message_text,
            max_recipients=max_recipients,
            now=now,
        )
    except ValueError as exc:
        if str(exc) == "preflight_failed":
            snapshot = campaign.preflight_snapshot if isinstance(campaign.preflight_snapshot, dict) else {}
            raise ConsoleAPIError(
                409,
                "GO_LIVE_GATE_REQUIRED",
                "Campaign preflight failed",
                details={
                    "blocked_reasons": snapshot.get("blocked_reasons", []),
                    "preflight_valid": bool(snapshot.get("preflight_valid")),
                },
            )
        raise

    record_audit_event(
        db,
        client_id=context.client.id,
        branch_id=campaign.branch_id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
        event_type="marketing_campaign_executed",
        entity_type="marketing_campaign",
        entity_id=campaign.id,
        payload={
            "queued_count": result["queued_count"],
            "skipped_count": result["skipped_count"],
            "max_recipients": max_recipients,
        },
    )
    db.commit()

    return ConsoleMarketingCampaignExecuteResponse(
        campaign_id=campaign.id,
        queued_count=result["queued_count"],
        skipped_count=result["skipped_count"],
        status="queued" if result["queued_count"] > 0 else "skipped",
    )


@router.get(
    "/admin/marketing/campaigns/{campaign_id}/diagnostics",
    response_model=ConsoleMarketingCampaignDiagnosticsResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def get_marketing_campaign_diagnostics(
    campaign_id: str,
    request: Request,
    sample_limit: Optional[int] = Query(None),
    db: Session = Depends(get_db),
) -> ConsoleMarketingCampaignDiagnosticsResponse:
    context = get_console_context(request, db, require_selection=True, include_inactive_tenants=False)
    _require_marketing_access(context, action="view diagnostics")

    campaign_uuid = _parse_uuid_param("campaign_id", campaign_id)
    if campaign_uuid is None:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid campaign_id")

    campaign = _resolve_marketing_campaign(context, db, campaign_uuid)
    _resolve_marketing_branch(context, db, campaign.branch_id)
    sample_limit_value = _normalize_marketing_sample_limit(sample_limit)
    refresh_marketing_campaign_lifecycle(db, campaign=campaign)

    rows = (
        db.query(
            MarketingCampaignDelivery,
            OutboxMessage.status.label("outbox_status"),
            OutboxMessage.last_error.label("outbox_last_error"),
        )
        .outerjoin(OutboxMessage, OutboxMessage.id == MarketingCampaignDelivery.outbox_id)
        .filter(MarketingCampaignDelivery.campaign_id == campaign.id)
        .order_by(MarketingCampaignDelivery.created_at.desc(), MarketingCampaignDelivery.id.desc())
        .all()
    )

    counts = {"queued": 0, "sent": 0, "failed": 0, "replied": 0}
    failure_classes: dict[str, int] = {}
    retryable_failed_count = 0
    permanent_failed_count = 0
    sample_failed: list[ConsoleMarketingDeliverySample] = []
    for delivery, outbox_status, outbox_last_error in rows:
        status_value = _effective_marketing_delivery_status(
            delivery_status=delivery.status,
            outbox_status=outbox_status,
        )
        counts[status_value] += 1
        if status_value != "failed":
            continue
        failure_text = outbox_last_error or delivery.error_reason
        classification = classify_provider_error(failure_text)
        reason_code = classification.incident_reason_code
        failure_classes[reason_code] = failure_classes.get(reason_code, 0) + 1
        if classification.retryable:
            retryable_failed_count += 1
        else:
            permanent_failed_count += 1
        if len(sample_failed) < sample_limit_value:
            sample_failed.append(
                _serialize_marketing_delivery_sample(
                    delivery,
                    status=status_value,
                    outbox_status=outbox_status,
                    last_error=failure_text,
                )
            )

    db.commit()
    return ConsoleMarketingCampaignDiagnosticsResponse(
        campaign_id=campaign.id,
        queued_count=counts["queued"],
        sent_count=counts["sent"],
        failed_count=counts["failed"],
        replied_count=counts["replied"],
        total_count=sum(counts.values()),
        failure_classes=failure_classes,
        retryable_failed_count=retryable_failed_count,
        permanent_failed_count=permanent_failed_count,
        sample_failed=sample_failed,
    )


@router.post(
    "/admin/marketing/campaigns/{campaign_id}/retry-failed",
    response_model=ConsoleMarketingCampaignRetryResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def retry_failed_marketing_campaign_deliveries(
    campaign_id: str,
    request: Request,
    payload: ConsoleMarketingCampaignRetryRequest,
    db: Session = Depends(get_db),
) -> ConsoleMarketingCampaignRetryResponse:
    context = get_console_context(request, db, require_selection=True, include_inactive_tenants=False)
    _require_marketing_access(context, action="retry")

    if not payload.confirm_retry:
        raise ConsoleAPIError(409, "CONFIRMATION_REQUIRED", "Use confirm_retry=true to retry failed deliveries")

    campaign_uuid = _parse_uuid_param("campaign_id", campaign_id)
    if campaign_uuid is None:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid campaign_id")

    campaign = _resolve_marketing_campaign(context, db, campaign_uuid)
    _resolve_marketing_branch(context, db, campaign.branch_id)
    retry_limit = _normalize_marketing_retry_limit(payload.limit)
    result = retry_failed_marketing_deliveries(
        db,
        campaign=campaign,
        limit=retry_limit,
    )

    record_audit_event(
        db,
        client_id=context.client.id,
        branch_id=campaign.branch_id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
        event_type="marketing_campaign_retry_failed",
        entity_type="marketing_campaign",
        entity_id=campaign.id,
        payload={
            "retried_count": result["retried_count"],
            "skipped_count": result["skipped_count"],
            "skipped_permanent": result["skipped_permanent"],
            "limit": retry_limit,
        },
    )
    db.commit()

    return ConsoleMarketingCampaignRetryResponse(
        campaign_id=campaign.id,
        retried_count=result["retried_count"],
        skipped_count=result["skipped_count"],
        skipped_permanent=result["skipped_permanent"],
    )


@router.get(
    "/admin/provider-lifecycle",
    response_model=ConsoleProviderLifecycleListResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_provider_lifecycle(
    request: Request,
    stale_after_minutes: int = Query(
        _INTEGRATION_DEFAULT_STALE_MINUTES,
        ge=_INTEGRATION_MIN_STALE_MINUTES,
        le=_INTEGRATION_MAX_STALE_MINUTES,
    ),
    cursor: Optional[str] = None,
    limit: int = 50,
    only_problematic: Optional[str] = None,
    company_id: Optional[str] = None,
    client_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ConsoleProviderLifecycleListResponse:
    context = get_console_context(request, db, require_selection=False, include_inactive_tenants=False)
    _require_platform_admin(context)
    _reject_unknown_query_params(
        request,
        {"stale_after_minutes", "cursor", "limit", "only_problematic", "company_id", "client_id", "branch_id"},
    )
    _validate_limit(limit)

    only_problematic_mode = _parse_bool_param("only_problematic", only_problematic, default=False)
    cursor_date = _parse_cursor_param(cursor)
    company_uuid = _parse_uuid_param("company_id", company_id)
    client_uuid = _parse_uuid_param("client_id", client_id)
    branch_uuid = _parse_uuid_param("branch_id", branch_id)

    active_clients = [
        client for client in (context.accessible_clients or []) if _is_client_active_status(client.status)
    ]
    if company_uuid:
        _require_company_access(context, company_uuid)
        active_clients = [client for client in active_clients if client.company_id == company_uuid]
    if client_uuid:
        _require_client_access(context, client_uuid)
        selected_client = next((client for client in (context.accessible_clients or []) if client.id == client_uuid), None)
        if company_uuid and selected_client and selected_client.company_id != company_uuid:
            raise ConsoleAPIError(400, "INVALID_PARAM", "client_id does not belong to company_id")
        active_clients = [client for client in active_clients if client.id == client_uuid]

    if branch_uuid:
        selected_branch = db.query(Branch).filter(Branch.id == branch_uuid).first()
        if not selected_branch:
            raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
        _require_client_access(context, selected_branch.client_id, message="Branch belongs to another tenant")
        if client_uuid and selected_branch.client_id != client_uuid:
            raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id does not belong to client_id")
        if company_uuid:
            selected_branch_company_id = next(
                (
                    client.company_id
                    for client in (context.accessible_clients or [])
                    if client.id == selected_branch.client_id
                ),
                None,
            )
            if selected_branch_company_id != company_uuid:
                raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id does not belong to company_id")

    if not active_clients:
        return ConsoleProviderLifecycleListResponse(
            stale_after_minutes=stale_after_minutes,
            cursor=None,
            has_more=False,
            total_in_scope=0,
            items=[],
        )

    client_ids = [client.id for client in active_clients]
    client_slug_map = {client.id: client.name for client in active_clients}
    client_company_map = {
        client.id: client.company_id
        for client in active_clients
        if getattr(client, "company_id", None)
    }

    company_ids = sorted({company_id for company_id in client_company_map.values() if company_id})
    companies_by_id: dict[UUID, Company] = {}
    if company_ids:
        companies_by_id = {
            company.id: company
            for company in db.query(Company).filter(Company.id.in_(company_ids)).all()
        }

    branches_query = db.query(Branch).filter(Branch.client_id.in_(client_ids))
    if branch_uuid:
        branches_query = branches_query.filter(Branch.id == branch_uuid)
    branches = (
        branches_query
        .order_by(Branch.created_at.desc(), Branch.id.desc())
        .all()
    )

    if not branches:
        return ConsoleProviderLifecycleListResponse(
            stale_after_minutes=stale_after_minutes,
            cursor=None,
            has_more=False,
            total_in_scope=0,
            items=[],
        )

    branch_client_ids = sorted({branch.client_id for branch in branches})
    token_rows = (
        db.query(
            ClientSettings.client_id,
            ClientSettings.telegram_bot_token,
        )
        .filter(ClientSettings.client_id.in_(branch_client_ids))
        .all()
    )
    telegram_token_map: dict[UUID, bool] = {}
    for row_client_id, token in token_rows:
        telegram_token_map[row_client_id] = bool(_normalize_optional_text(token))

    inbound_observations = _load_latest_branch_inbound_observations_for_clients(
        db,
        client_ids=branch_client_ids,
    )
    generated_at = datetime.now(timezone.utc)
    provider_binding_by_branch = _build_provider_binding_lifecycle_map(
        db,
        client_ids=branch_client_ids,
        branches=branches,
        now=generated_at,
    )

    lifecycle_rows: list[tuple[datetime, ConsoleProviderLifecycleItem]] = []
    for branch in branches:
        client_slug = client_slug_map.get(branch.client_id)
        if not client_slug:
            continue
        observed = inbound_observations.get(branch.id)
        last_inbound_at: Optional[datetime] = observed[0] if observed else None
        last_inbound_instance_id: Optional[str] = observed[1] if observed else None
        status = _build_branch_integration_status(
            client_id=branch.client_id,
            client_slug=client_slug,
            branch=branch,
            has_telegram_bot_token=telegram_token_map.get(branch.client_id, False),
            stale_after_minutes=stale_after_minutes,
            last_inbound_at=last_inbound_at,
            last_inbound_instance_id=last_inbound_instance_id,
            now=generated_at,
            provider_binding=provider_binding_by_branch.get(branch.id),
        )
        decision = _resolve_provider_ops_decision(status)
        if only_problematic_mode and status.status == "ok" and not decision:
            continue

        company_uuid_for_client = client_company_map.get(branch.client_id)
        company_name = (
            companies_by_id.get(company_uuid_for_client).name
            if company_uuid_for_client and company_uuid_for_client in companies_by_id
            else None
        )
        lifecycle_item = _build_provider_lifecycle_item(
            status=status,
            branch=branch,
            company_id=company_uuid_for_client,
            company_name=company_name,
            generated_at=generated_at,
            now=generated_at,
        )
        lifecycle_rows.append((branch.created_at, lifecycle_item))

    total_in_scope = len(lifecycle_rows)
    paged_rows = lifecycle_rows
    if cursor_date is not None:
        paged_rows = [row for row in paged_rows if row[0] and row[0] < cursor_date]

    has_more = len(paged_rows) > limit
    page_rows = paged_rows[:limit]
    next_cursor = page_rows[-1][0].isoformat() if has_more and page_rows and page_rows[-1][0] else None

    return ConsoleProviderLifecycleListResponse(
        stale_after_minutes=stale_after_minutes,
        cursor=next_cursor,
        has_more=has_more,
        total_in_scope=total_in_scope,
        items=[item for _created_at, item in page_rows],
    )


@router.get(
    "/admin/integrations",
    response_model=ConsoleIntegrationsListResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_integrations(
    request: Request,
    stale_after_minutes: int = Query(
        _INTEGRATION_DEFAULT_STALE_MINUTES,
        ge=_INTEGRATION_MIN_STALE_MINUTES,
        le=_INTEGRATION_MAX_STALE_MINUTES,
    ),
    cursor: Optional[str] = None,
    limit: int = 50,
    company_id: Optional[str] = None,
    client_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ConsoleIntegrationsListResponse:
    context = get_console_context(request, db, require_selection=False, include_inactive_tenants=False)
    _require_platform_admin(context)
    _reject_unknown_query_params(
        request,
        {"stale_after_minutes", "cursor", "limit", "company_id", "client_id", "branch_id"},
    )
    _validate_limit(limit)

    company_uuid = _parse_uuid_param("company_id", company_id)
    client_uuid = _parse_uuid_param("client_id", client_id)
    branch_uuid = _parse_uuid_param("branch_id", branch_id)
    cursor_date = _parse_cursor_param(cursor)

    active_clients = [
        client for client in (context.accessible_clients or []) if _is_client_active_status(client.status)
    ]
    if company_uuid:
        _require_company_access(context, company_uuid)
        active_clients = [client for client in active_clients if client.company_id == company_uuid]
    if client_uuid:
        _require_client_access(context, client_uuid)
        selected_client = next((client for client in (context.accessible_clients or []) if client.id == client_uuid), None)
        if company_uuid and selected_client and selected_client.company_id != company_uuid:
            raise ConsoleAPIError(400, "INVALID_PARAM", "client_id does not belong to company_id")
        active_clients = [client for client in active_clients if client.id == client_uuid]

    selected_branch: Optional[Branch] = None
    if branch_uuid:
        selected_branch = db.query(Branch).filter(Branch.id == branch_uuid).first()
        if not selected_branch:
            raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
        _require_client_access(context, selected_branch.client_id, message="Branch belongs to another tenant")
        if client_uuid and selected_branch.client_id != client_uuid:
            raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id does not belong to client_id")
        if company_uuid:
            selected_branch_company_id = next(
                (
                    client.company_id
                    for client in (context.accessible_clients or [])
                    if client.id == selected_branch.client_id
                ),
                None,
            )
            if selected_branch_company_id != company_uuid:
                raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id does not belong to company_id")

    if not active_clients:
        return ConsoleIntegrationsListResponse(
            stale_after_minutes=stale_after_minutes,
            cursor=None,
            has_more=False,
            total_in_scope=0,
            items=[],
            provider_ops_queue=[],
        )

    client_ids = [client.id for client in active_clients]
    client_slug_map = {client.id: client.name for client in active_clients}

    branches_scope_query = db.query(Branch).filter(Branch.client_id.in_(client_ids))
    if branch_uuid:
        branches_scope_query = branches_scope_query.filter(Branch.id == branch_uuid)

    total_in_scope = branches_scope_query.count()

    branches_query = branches_scope_query
    if cursor_date is not None:
        branches_query = branches_query.filter(Branch.created_at < cursor_date)
    branches = (
        branches_query.order_by(Branch.created_at.desc(), Branch.id.desc())
        .limit(limit + 1)
        .all()
    )
    has_more = len(branches) > limit
    if has_more:
        branches = branches[:limit]
    next_cursor = branches[-1].created_at.isoformat() if has_more and branches and branches[-1].created_at else None

    branch_client_ids = sorted({branch.client_id for branch in branches})
    if not branch_client_ids:
        return ConsoleIntegrationsListResponse(
            stale_after_minutes=stale_after_minutes,
            cursor=None,
            has_more=False,
            total_in_scope=total_in_scope,
            items=[],
            provider_ops_queue=[],
        )
    token_rows = (
        db.query(
            ClientSettings.client_id,
            ClientSettings.telegram_bot_token,
        )
        .filter(ClientSettings.client_id.in_(branch_client_ids))
        .all()
    )
    telegram_token_map: dict[UUID, bool] = {}
    for client_id, token in token_rows:
        telegram_token_map[client_id] = bool(_normalize_optional_text(token))

    inbound_observations = _load_latest_branch_inbound_observations_for_clients(
        db,
        client_ids=branch_client_ids,
    )
    now = datetime.now(timezone.utc)
    provider_binding_by_branch = _build_provider_binding_lifecycle_map(
        db,
        client_ids=branch_client_ids,
        branches=branches,
        now=now,
    )
    items = []
    for branch in branches:
        client_slug = client_slug_map.get(branch.client_id)
        if not client_slug:
            continue
        last_inbound_at: Optional[datetime] = None
        last_inbound_instance_id: Optional[str] = None
        observed = inbound_observations.get(branch.id)
        if observed:
            last_inbound_at, last_inbound_instance_id = observed
        item = _build_branch_integration_status(
            client_id=branch.client_id,
            client_slug=client_slug,
            branch=branch,
            has_telegram_bot_token=telegram_token_map.get(branch.client_id, False),
            stale_after_minutes=stale_after_minutes,
            last_inbound_at=last_inbound_at,
            last_inbound_instance_id=last_inbound_instance_id,
            now=now,
            provider_binding=provider_binding_by_branch.get(branch.id),
        )
        items.append(item)

    provider_ops_queue = _build_provider_ops_queue(
        items,
        generated_at=now,
    )
    return ConsoleIntegrationsListResponse(
        stale_after_minutes=stale_after_minutes,
        cursor=next_cursor,
        has_more=has_more,
        total_in_scope=total_in_scope,
        items=items,
        provider_ops_queue=provider_ops_queue,
    )


@router.post(
    "/admin/integrations/{branch_id}/reconcile",
    response_model=ConsoleIntegrationBranchActionResponse,
    responses={
        401: {"model": ConsoleErrorResponse},
        403: {"model": ConsoleErrorResponse},
        404: {"model": ConsoleErrorResponse},
        409: {"model": ConsoleErrorResponse},
    },
)
async def run_integration_reconcile_for_branch(
    branch_id: UUID,
    body: ConsoleIntegrationBranchActionRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleIntegrationBranchActionResponse:
    context = get_console_context(request, db, require_selection=False, include_inactive_tenants=False)
    _require_platform_admin(context)
    _reject_unknown_query_params(request, set())

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
    _require_client_access(context, branch.client_id, message="Branch belongs to another tenant")
    branch_company_id = _resolve_company_id_for_client_in_context(context, branch.client_id)
    if not branch.is_active:
        raise ConsoleAPIError(409, "INVALID_STATE", "Branch is inactive")

    action = body.action or _PROVIDER_OPS_RECONCILE_ACTION
    if action not in _PROVIDER_OPS_ACTIONS:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Unsupported integrations action")

    if action == _PROVIDER_OPS_RECONCILE_ACTION:
        confirmation = None
        if body.mode == "execute":
            confirmation = require_confirmation(
                db,
                context,
                confirmation_id=body.confirmation_id,
                action="integration_reconcile",
                target_type="branch",
                target_id=branch.id,
            )

        result = run_integration_watchdog_scoped(
            db,
            client_id=branch.client_id,
            branch_ids=[branch.id],
            dry_run=(body.mode == "dry_run"),
        )

        if body.mode == "execute":
            if confirmation:
                mark_confirmation_used(
                    db,
                    context,
                    confirmation,
                    action="integration_reconcile",
                    target_type="branch",
                    target_id=branch.id,
                )
            record_audit_event(
                db,
                actor=context.agent,
                event_type="integration_reconcile_run",
                entity_type="branch",
                entity_id=branch.id,
                payload={
                    "mode": body.mode,
                    "checked": result.get("checked"),
                    "degraded": result.get("degraded"),
                    "recovered": result.get("recovered"),
                    "remediated": result.get("remediated"),
                },
                client_id=branch.client_id,
                branch_id=branch.id,
            )
            _invalidate_tenants_fleet_cache_scope(
                db,
                reason="integration_reconcile_execute",
                company_ids={branch_company_id} if branch_company_id else None,
            )
            db.commit()
        return ConsoleIntegrationBranchActionResponse(
            branch_id=branch.id,
            action=action,
            mode=body.mode,
            result=result,
        )

    now = datetime.now(timezone.utc)
    lifecycle_map = _build_provider_binding_lifecycle_map(
        db,
        client_ids=[branch.client_id],
        branches=[branch],
        now=now,
    )
    binding = lifecycle_map.get(branch.id, _ProviderBindingLifecycle())
    binding_patch, branch_patch, reminder_note = _build_provider_ops_effective_payload(
        action=action,
        request_payload=body,
        branch=branch,
        binding=binding,
        now_date=now.date(),
    )

    result: dict[str, object] = {
        "action": action,
        "binding_before": {
            "provider": binding.provider,
            "instance_id": binding.instance_id,
            "webhook_status": binding.webhook_status,
            "paid_until": binding.paid_until,
            "owner": binding.owner,
            "next_renewal_at": binding.next_renewal_at,
            "last_rebind_at": binding.last_rebind_at,
            "rebind_required": binding.rebind_required,
            "alert_state": binding.alert_state,
            "notes": binding.notes,
            "payment_status": binding.payment_status,
            "payment_confirmed_at": binding.payment_confirmed_at,
            "expiry_status": binding.expiry_status,
            "days_until_expiry": binding.days_until_expiry,
        },
        "binding_patch": binding_patch,
        "branch_patch": branch_patch,
        "requires_confirmation": True,
    }

    confirmation = None
    if body.mode == "execute":
        confirmation = require_confirmation(
            db,
            context,
            confirmation_id=body.confirmation_id,
            action=_PROVIDER_OPS_EXECUTE_CONFIRMATION_ACTION,
            target_type="branch",
            target_id=branch.id,
        )

        if action == "provider_send_reminder":
            record_audit_event(
                db,
                actor=context.agent,
                event_type="provider_ops_reminder_sent",
                entity_type="branch",
                entity_id=branch.id,
                payload={
                    "mode": body.mode,
                    "action": action,
                    "note": reminder_note,
                    "binding_snapshot": result["binding_before"],
                },
                client_id=branch.client_id,
                branch_id=branch.id,
            )
        else:
            contract_record = _get_latest_onboarding_contract(
                db,
                client_id=branch.client_id,
                scope="branch",
                branch_id=branch.id,
            )
            base_payload: Optional[dict] = None
            if (
                contract_record
                and contract_record.status == "active"
                and isinstance(contract_record.payload_json, dict)
            ):
                base_payload = contract_record.payload_json
            if base_payload is None:
                client_record = _get_latest_onboarding_contract(
                    db,
                    client_id=branch.client_id,
                    scope="client",
                    branch_id=None,
                )
                client_payload = (
                    client_record.payload_json
                    if client_record and client_record.status == "active" and isinstance(client_record.payload_json, dict)
                    else None
                )
                base_payload = merge_onboarding_contract(client_payload, None)

            # Some older contracts can carry extra top-level keys.
            # Rebuild through merge helper to keep only contract-relevant structure
            # and fail with ConsoleAPIError (not unhandled ValidationError).
            effective_payload = validate_onboarding_contract_payload(
                merge_onboarding_contract(None, base_payload)
            )
            existing_binding = effective_payload.provider_binding.whatsapp
            base_binding_payload = (
                existing_binding.model_dump(exclude_none=True, mode="json")
                if existing_binding
                else {}
            )
            merged_binding_payload = {
                **base_binding_payload,
                **{key: value for key, value in binding_patch.items() if value is not None},
            }
            normalized_binding = OnboardingProviderBindingWhatsApp.model_validate(merged_binding_payload)
            if normalized_binding.webhook_status == "rebind_required":
                normalized_binding.rebind_required = True
            next_binding_payload = normalized_binding.model_dump(exclude_none=True, mode="json")
            effective_dict = onboarding_contract_payload_to_dict(effective_payload)
            contract_payload = validate_onboarding_contract_payload(
                merge_onboarding_contract(
                    effective_dict,
                    {
                        "provider_binding": {
                            "whatsapp": next_binding_payload,
                        }
                    },
                )
            )

            if not contract_record:
                contract_record = ClientOnboardingContract(
                    client_id=branch.client_id,
                    branch_id=branch.id,
                    scope="branch",
                    payload_json=onboarding_contract_payload_to_dict(contract_payload),
                    schema_version=ONBOARDING_CONTRACT_SCHEMA_VERSION,
                    status="active",
                    payment_status="pending",
                    created_by=context.agent.id,
                )
                db.add(contract_record)
            else:
                contract_record.payload_json = onboarding_contract_payload_to_dict(contract_payload)
                contract_record.schema_version = ONBOARDING_CONTRACT_SCHEMA_VERSION
                contract_record.status = "active"

            if action == "provider_renewal_confirmed":
                contract_record.payment_status = "confirmed"
                contract_record.payment_confirmed_at = now
                contract_record.payment_confirmed_by = context.agent.id

            webhook_secret_changed = False
            webhook_url = None
            if branch_patch and isinstance(branch_patch.get("instance_id"), str):
                next_instance_id = _normalize_optional_text(branch_patch.get("instance_id"))
                if next_instance_id:
                    _ensure_unique_branch_field(
                        db,
                        client_id=branch.client_id,
                        field_name="instance_id",
                        value=next_instance_id,
                        exclude_branch_id=branch.id,
                    )
                    branch.instance_id = next_instance_id
                    client = db.query(Client).filter(Client.id == branch.client_id).first()
                    if not client:
                        raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")
                    webhook_secret, webhook_url, webhook_secret_changed = _ensure_client_webhook_secret_from_instance(
                        db,
                        client=client,
                        branch=branch,
                        instance_id=next_instance_id,
                    )
                    result["webhook_secret_generated"] = webhook_secret_changed
                    result["webhook_secret"] = webhook_secret
                    result["webhook_url"] = webhook_url

            result["binding_after"] = next_binding_payload
            result["payment_status_after"] = contract_record.payment_status
            result["payment_confirmed_at_after"] = (
                contract_record.payment_confirmed_at.isoformat()
                if contract_record.payment_confirmed_at
                else None
            )
            result["webhook_secret_changed"] = webhook_secret_changed

            record_audit_event(
                db,
                actor=context.agent,
                event_type="provider_ops_action_run",
                entity_type="branch",
                entity_id=branch.id,
                payload={
                    "mode": body.mode,
                    "action": action,
                    "binding_patch": binding_patch,
                    "branch_patch": branch_patch,
                    "reminder_note": reminder_note,
                    "result": {
                        "payment_status_after": result.get("payment_status_after"),
                        "payment_confirmed_at_after": result.get("payment_confirmed_at_after"),
                        "webhook_secret_changed": result.get("webhook_secret_changed"),
                        "webhook_url": result.get("webhook_url"),
                    },
                },
                client_id=branch.client_id,
                branch_id=branch.id,
            )

        if confirmation:
            mark_confirmation_used(
                db,
                context,
                confirmation,
                action=_PROVIDER_OPS_EXECUTE_CONFIRMATION_ACTION,
                target_type="branch",
                target_id=branch.id,
            )
        _invalidate_tenants_fleet_cache_scope(
            db,
            reason="provider_ops_execute",
            company_ids={branch_company_id} if branch_company_id else None,
        )
        db.commit()
    else:
        result["dry_run"] = True
        result["reminder_note"] = reminder_note

    return ConsoleIntegrationBranchActionResponse(
        branch_id=branch.id,
        action=action,
        mode=body.mode,
        result=result,
    )


@router.get(
    "/admin/fleet/attention",
    response_model=ConsoleFleetAttentionResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_fleet_attention(
    request: Request,
    limit: int = 20,
    stale_after_minutes: int = Query(
        _INTEGRATION_DEFAULT_STALE_MINUTES,
        ge=_INTEGRATION_MIN_STALE_MINUTES,
        le=_INTEGRATION_MAX_STALE_MINUTES,
    ),
    include_low: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ConsoleFleetAttentionResponse:
    _reject_unknown_query_params(request, {"limit", "stale_after_minutes", "include_low"})
    _validate_limit(limit)
    if not isinstance(stale_after_minutes, int):
        stale_after_minutes = _INTEGRATION_DEFAULT_STALE_MINUTES
    normalized_include_low = include_low
    if normalized_include_low is not None and normalized_include_low.lower() == "null":
        normalized_include_low = None
    include_low_mode = _parse_bool_param("include_low", normalized_include_low, default=False)

    context = get_console_context(
        request,
        db,
        require_selection=False,
        include_inactive_tenants=False,
    )
    _require_platform_admin(context)

    active_clients = [
        client for client in (context.accessible_clients or []) if _is_client_active_status(client.status)
    ]
    if not active_clients:
        return ConsoleFleetAttentionResponse(
            generated_at=datetime.now(timezone.utc).isoformat(),
            stale_after_minutes=stale_after_minutes,
            summary=ConsoleFleetAttentionSummary(
                active_clients_total=0,
                clients_with_attention=0,
                high_risk_clients=0,
                medium_risk_clients=0,
                low_risk_clients=0,
                stale_branches_total=0,
                integration_error_branches_total=0,
                integration_warn_branches_total=0,
                outbox_failed_24h_total=0,
                pending_handovers_total=0,
            ),
            items=[],
        )

    active_client_ids = {client.id for client in active_clients}
    now = datetime.now(timezone.utc)
    attention_scope_key = _build_fleet_attention_cache_scope_key(
        active_client_ids=active_client_ids,
        stale_after_minutes=stale_after_minutes,
        include_low_mode=include_low_mode,
        limit=limit,
    )
    cached_response = _load_cached_fleet_attention(
        db,
        scope_key=attention_scope_key,
        now=now,
    )
    if cached_response is not None:
        _schedule_fleet_attention_async_refresh(
            db,
            scope_key=attention_scope_key,
            active_client_ids=active_client_ids,
            stale_after_minutes=stale_after_minutes,
            include_low_mode=include_low_mode,
            limit=limit,
            now=now,
        )
        return cached_response

    companies_by_id = {company.id: company for company in (context.companies or [])}
    response = _build_fleet_attention_response_for_clients(
        db,
        active_clients=active_clients,
        companies_by_id=companies_by_id,
        stale_after_minutes=stale_after_minutes,
        include_low_mode=include_low_mode,
        limit=limit,
        now=now,
    )
    _store_cached_fleet_attention(
        db,
        scope_key=attention_scope_key,
        now=now,
        response=response,
    )
    return response


@router.get(
    "/admin/incidents",
    response_model=ConsoleIncidentListResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_admin_incidents(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> ConsoleIncidentListResponse:
    _reject_unknown_query_params(request, {"limit"})
    _validate_limit(limit)

    context = get_console_context(
        request,
        db,
        require_selection=False,
        include_inactive_tenants=False,
    )
    _require_platform_admin(context)

    active_clients = [
        client for client in (context.accessible_clients or []) if _is_client_active_status(client.status)
    ]
    if not active_clients:
        return ConsoleIncidentListResponse(
            generated_at=datetime.now(timezone.utc).isoformat(),
            scope="fleet",
            summary=ConsoleIncidentSummary(total=0, critical=0, warn=0, info=0),
            items=[],
        )

    now = datetime.now(timezone.utc)
    client_ids = [client.id for client in active_clients]
    outbox_backlog_map = _query_outbox_backlog_map(db, client_ids=client_ids)
    outbox_failed_map = _query_outbox_failed_24h_map(db, client_ids=client_ids, now=now)
    pending_handovers_map = _query_pending_handovers_map(db, client_ids=client_ids)
    degraded_map = _query_integration_degraded_branch_count_map(db, client_ids=client_ids)
    latest_error_map = _query_latest_failed_error_map(db, client_ids=client_ids, now=now)

    items: list[ConsoleIncidentItem] = []
    for client in active_clients:
        signals = _IncidentSignals(
            outbox_backlog=outbox_backlog_map.get(client.id, 0),
            outbox_failed_24h=outbox_failed_map.get(client.id, 0),
            pending_handovers=pending_handovers_map.get(client.id, 0),
            integration_degraded_branches=degraded_map.get(client.id, 0),
            last_error=latest_error_map.get(client.id),
        )
        items.extend(
            _build_scope_incident_items(
                scope="fleet",
                signals=signals,
                detected_at=now,
                client_id=client.id,
                client_slug=client.name,
                branch_id=None,
                branch_ids=None,
                platform_scope=True,
            )
        )

    items_by_client: dict[UUID, list[ConsoleIncidentItem]] = {}
    for item in items:
        if item.client_id is None:
            continue
        items_by_client.setdefault(item.client_id, []).append(item)
    for client_id, scoped_items in items_by_client.items():
        state_map = _load_incident_state_map(
            db,
            client_id=client_id,
            incident_ids=[item.id for item in scoped_items],
            allowed_branch_ids=None,
        )
        _apply_incident_state_map(scoped_items, state_map=state_map)

    severity_rank = {"critical": 2, "warn": 1, "info": 0}
    items.sort(
        key=lambda item: (
            severity_rank.get(item.severity, 0),
            int(item.metrics.get("outbox_backlog") or 0),
            int(item.metrics.get("outbox_failed_24h") or 0),
            int(item.metrics.get("integration_degraded_branches") or 0),
            int(item.metrics.get("pending_handovers") or 0),
        ),
        reverse=True,
    )
    limited_items = items[:limit]
    return ConsoleIncidentListResponse(
        generated_at=now.isoformat(),
        scope="fleet",
        summary=_build_incident_summary(limited_items),
        items=limited_items,
    )


@router.post(
    "/admin/companies",
    response_model=ConsoleCompanyCreateResponse,
    responses={403: {"model": ConsoleErrorResponse}},
)
async def create_company(
    request: Request,
    body: ConsoleCompanyCreateRequest,
    db: Session = Depends(get_db),
) -> ConsoleCompanyCreateResponse:
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )

    name = _normalize_required_text(body.name, "name")
    billing_info = body.billing_info or {}
    now = datetime.now(timezone.utc)
    company = Company(
        id=uuid4(),
        name=name,
        billing_info=billing_info,
        created_at=now,
        updated_at=now,
    )
    db.add(company)
    record_audit_event(
        db,
        actor=context.agent,
        client_id=context.client.id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
        event_type="company_created",
        entity_type="company",
        entity_id=company.id,
        payload={"name": company.name},
    )
    db.commit()

    return ConsoleCompanyCreateResponse(
        company=ConsoleCompany(
            id=company.id,
            name=company.name,
            billing_info=company.billing_info,
        )
    )


@router.patch(
    "/admin/companies/{company_id}",
    response_model=ConsoleCompany,
    responses={403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def update_company(
    company_id: UUID,
    request: Request,
    body: ConsoleCompanyUpdateRequest,
    db: Session = Depends(get_db),
) -> ConsoleCompany:
    context = get_console_context(
        request,
        db,
        require_selection=False,
        include_inactive_tenants=True,
    )
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise ConsoleAPIError(404, "NOT_FOUND", "Company not found")
    if context.role != "platform_admin":
        _require_company_access(context, company.id)

    updated_fields: list[str] = []
    fields_set = body.model_fields_set

    if "name" in fields_set:
        name = _normalize_required_text(body.name, "name")
        if name != company.name:
            company.name = name
        updated_fields.append("name")

    if "billing_info" in fields_set:
        company.billing_info = body.billing_info or {}
        updated_fields.append("billing_info")

    if updated_fields:
        company.updated_at = datetime.now(timezone.utc)
        record_audit_event(
            db,
            actor=context.agent,
            event_type="company_updated",
            entity_type="company",
            entity_id=company.id,
            payload={"updated_fields": updated_fields},
            actor_id=context.agent.id,
            actor_name=context.agent.name,
        )
        _invalidate_tenants_fleet_cache_scope(
            db,
            reason="update_company",
            company_ids={company.id},
        )
        db.commit()

    return ConsoleCompany(
        id=company.id,
        name=company.name,
        billing_info=company.billing_info,
    )


@router.post(
    "/admin/clients",
    response_model=ConsoleClientCreateResponse,
    responses={403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def create_client(
    request: Request,
    body: ConsoleClientCreateRequest,
    db: Session = Depends(get_db),
) -> ConsoleClientCreateResponse:
    context = get_console_context(
        request,
        db,
        require_selection=False,
        include_inactive_tenants=True,
    )
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )

    slug = _normalize_slug(body.slug, "client_slug")
    existing = db.query(Client).filter(func.lower(Client.name) == slug.lower()).first()
    if existing:
        raise ConsoleAPIError(400, "INVALID_PARAM", "client_slug already exists")

    company = db.query(Company).filter(Company.id == body.company_id).first()
    if not company:
        raise ConsoleAPIError(404, "NOT_FOUND", "Company not found")
    if context.role != "platform_admin":
        _require_company_access(context, company.id)
    company_id = company.id

    status_value = (body.status or "active").strip()
    now = datetime.now(timezone.utc)
    client = Client(
        id=uuid4(),
        name=slug,
        status=status_value,
        config={},
        created_at=now,
        updated_at=now,
        company_id=company_id,
    )
    db.add(client)
    record_audit_event(
        db,
        actor=context.agent,
        event_type="client_created",
        entity_type="client",
        entity_id=client.id,
        payload={
            "slug": slug,
            "company_id": str(company_id) if company_id else None,
        },
        client_id=client.id,
    )
    _invalidate_tenants_fleet_cache_scope(
        db,
        reason="create_client",
        company_ids={company_id} if company_id else None,
    )
    db.commit()

    return ConsoleClientCreateResponse(
        client=ConsoleClient(
            id=client.id,
            slug=client.name,
            name=client.name,
            status=client.status,
            company_id=client.company_id,
            company_name=company.name,
        )
    )


@router.patch(
    "/admin/clients/{client_id}",
    response_model=ConsoleClient,
    responses={403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def update_client(
    client_id: UUID,
    request: Request,
    body: ConsoleClientUpdateRequest,
    db: Session = Depends(get_db),
) -> ConsoleClient:
    context = get_console_context(
        request,
        db,
        require_selection=False,
        include_inactive_tenants=True,
    )
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")
    _require_client_access(context, client.id)
    previous_company_id = client.company_id

    updated_fields: list[str] = []
    fields_set = body.model_fields_set
    company = None

    if "status" in fields_set:
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            "Use /admin/clients/{client_id}/archive or /restore for lifecycle changes",
        )

    if "slug" in fields_set:
        slug = _normalize_slug(body.slug, "client_slug")
        existing = (
            db.query(Client)
            .filter(func.lower(Client.name) == slug.lower(), Client.id != client.id)
            .first()
        )
        if existing:
            raise ConsoleAPIError(400, "INVALID_PARAM", "client_slug already exists")
        if slug != client.name:
            client.name = slug
        updated_fields.append("slug")

    if "company_id" in fields_set:
        if body.company_id:
            company = db.query(Company).filter(Company.id == body.company_id).first()
            if not company:
                raise ConsoleAPIError(404, "NOT_FOUND", "Company not found")
            if context.role != "platform_admin":
                _require_company_access(context, company.id)
            next_company_id = company.id
        else:
            next_company_id = None
        if next_company_id != client.company_id:
            has_client_branches = (
                db.query(Branch.id)
                .filter(Branch.client_id == client.id)
                .first()
                is not None
            )
            if has_client_branches:
                raise ConsoleAPIError(
                    400,
                    "INVALID_PARAM",
                    "company_id is immutable once client has branches",
                )
            client.company_id = next_company_id
        updated_fields.append("company_id")

    if updated_fields:
        client.updated_at = datetime.now(timezone.utc)
        record_audit_event(
            db,
            actor=context.agent,
            event_type="client_updated",
            entity_type="client",
            entity_id=client.id,
            payload={"updated_fields": updated_fields},
            client_id=client.id,
            actor_id=context.agent.id,
            actor_name=context.agent.name,
        )
        company_ids_to_invalidate = {
            company_id
            for company_id in {previous_company_id, client.company_id}
            if company_id is not None
        }
        _invalidate_tenants_fleet_cache_scope(
            db,
            reason="update_client",
            company_ids=company_ids_to_invalidate or None,
        )
        db.commit()

    company_name = None
    if client.company_id:
        if not company or company.id != client.company_id:
            company = db.query(Company).filter(Company.id == client.company_id).first()
        company_name = company.name if company else None

    return ConsoleClient(
        id=client.id,
        slug=client.name,
        name=client.name,
        status=client.status,
        company_id=client.company_id,
        company_name=company_name,
    )


@router.post(
    "/admin/clients/{client_id}/archive",
    response_model=ConsoleClient,
    responses={
        403: {"model": ConsoleErrorResponse},
        404: {"model": ConsoleErrorResponse},
        409: {"model": ConsoleErrorResponse},
    },
)
async def archive_client(
    client_id: UUID,
    request: Request,
    body: ConsoleClientLifecycleActionRequest,
    db: Session = Depends(get_db),
) -> ConsoleClient:
    context = get_console_context(request, db, require_selection=False, include_inactive_tenants=True)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")
    _require_client_access(context, client.id)
    if not _is_client_active_status(client.status):
        raise ConsoleAPIError(409, "INVALID_STATE", "Client is already archived")

    reason = _normalize_client_lifecycle_reason(body.reason)
    blockers = _collect_client_archive_blockers(db, client.id)
    blocker_counts = {
        "active_agents": len(blockers["active_agent_ids"]),
        "active_memberships": len(blockers["active_membership_ids"]),
        "active_branches": len(blockers["active_branch_ids"]),
    }
    if any(count > 0 for count in blocker_counts.values()):
        record_audit_event(
            db,
            actor=context.agent,
            event_type="client_archive_blocked",
            entity_type="client",
            entity_id=client.id,
            payload={
                "reason": reason,
                "blocker_counts": blocker_counts,
                "blockers": blockers,
            },
            client_id=client.id,
            actor_id=context.agent.id,
            actor_name=context.agent.name,
        )
        db.commit()
        raise ConsoleAPIError(
            409,
            "CLIENT_ARCHIVE_BLOCKED",
            "Client archive blocked by active dependencies",
            details={
                "blocker_counts": blocker_counts,
                "blockers": blockers,
            },
        )

    previous_status = client.status
    now = datetime.now(timezone.utc)
    client.status = _CLIENT_STATUS_ARCHIVED
    client.deleted_at = now
    client.updated_at = now
    record_audit_event(
        db,
        actor=context.agent,
        event_type="client_archived",
        entity_type="client",
        entity_id=client.id,
        payload={
            "reason": reason,
            "previous_status": previous_status,
            "next_status": client.status,
        },
        client_id=client.id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
    )
    _invalidate_tenants_fleet_cache_scope(
        db,
        reason="archive_client",
        company_ids={client.company_id} if client.company_id else None,
    )
    db.commit()

    company = db.query(Company).filter(Company.id == client.company_id).first() if client.company_id else None
    return _build_client_schema(client, company)


@router.post(
    "/admin/clients/{client_id}/restore",
    response_model=ConsoleClient,
    responses={
        403: {"model": ConsoleErrorResponse},
        404: {"model": ConsoleErrorResponse},
        409: {"model": ConsoleErrorResponse},
    },
)
async def restore_client(
    client_id: UUID,
    request: Request,
    body: ConsoleClientLifecycleActionRequest,
    db: Session = Depends(get_db),
) -> ConsoleClient:
    context = get_console_context(request, db, require_selection=False, include_inactive_tenants=True)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")
    _require_client_access(context, client.id)
    if _is_client_active_status(client.status):
        raise ConsoleAPIError(409, "INVALID_STATE", "Client is already active")

    reason = _normalize_client_lifecycle_reason(body.reason)
    previous_status = client.status
    now = datetime.now(timezone.utc)
    client.status = _CLIENT_STATUS_ACTIVE
    client.deleted_at = None
    client.updated_at = now
    record_audit_event(
        db,
        actor=context.agent,
        event_type="client_restored",
        entity_type="client",
        entity_id=client.id,
        payload={
            "reason": reason,
            "previous_status": previous_status,
            "next_status": client.status,
        },
        client_id=client.id,
        actor_id=context.agent.id,
        actor_name=context.agent.name,
    )
    _invalidate_tenants_fleet_cache_scope(
        db,
        reason="restore_client",
        company_ids={client.company_id} if client.company_id else None,
    )
    db.commit()

    company = db.query(Company).filter(Company.id == client.company_id).first() if client.company_id else None
    return _build_client_schema(client, company)


@router.post(
    "/admin/branches",
    response_model=ConsoleBranchCreateResponse,
    responses={403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def create_branch(
    request: Request,
    body: ConsoleBranchCreateRequest,
    db: Session = Depends(get_db),
) -> ConsoleBranchCreateResponse:
    context = get_console_context(
        request,
        db,
        require_selection=False,
        include_inactive_tenants=True,
    )
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )

    client = db.query(Client).filter(Client.id == body.client_id).first()
    if not client:
        raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")
    _require_client_access(context, client.id)

    slug = _normalize_slug(body.slug, "branch_slug")
    name = _normalize_required_text(body.name, "name")
    instance_id = _normalize_optional_text(body.instance_id)
    phone = _normalize_branch_phone(body.phone, "phone")
    telegram_chat_id = _normalize_telegram_chat_id(body.telegram_chat_id, "telegram_chat_id")
    knowledge_tag = _normalize_knowledge_tag(body.knowledge_tag, "knowledge_tag")
    timezone_value = _normalize_timezone_name(body.timezone, "timezone")

    _ensure_unique_branch_field(db, client_id=client.id, field_name="slug", value=slug)
    _ensure_unique_branch_field(db, client_id=client.id, field_name="instance_id", value=instance_id)
    _ensure_unique_branch_field(db, client_id=client.id, field_name="phone", value=phone)

    is_active = body.is_active if body.is_active is not None else bool(instance_id)
    if is_active and not instance_id:
        raise ConsoleAPIError(400, "INVALID_PARAM", "instance_id required to activate branch")

    bootstrap_accounts = body.bootstrap_accounts or []
    if len(bootstrap_accounts) > _BRANCH_BOOTSTRAP_ACCOUNTS_MAX:
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            f"bootstrap_accounts limit is {_BRANCH_BOOTSTRAP_ACCOUNTS_MAX}",
        )

    now = datetime.now(timezone.utc)
    branch = Branch(
        id=uuid4(),
        client_id=client.id,
        slug=slug,
        name=name,
        instance_id=instance_id,
        phone=phone,
        telegram_chat_id=telegram_chat_id,
        knowledge_tag=knowledge_tag,
        timezone=timezone_value,
        working_hours=body.working_hours if body.working_hours is not None else {},
        booking_settings=body.booking_settings if body.booking_settings is not None else {},
        is_active=is_active,
        onboarding_state=OnboardingStep.BRANCH_DRAFT.value,
        onboarding_updated_at=now,
        go_live_state=_BRANCH_GO_LIVE_DEFAULT_STATE,
        created_at=now,
        updated_at=now,
    )
    db.add(branch)
    webhook_secret_changed = False
    if instance_id:
        _secret, _url, webhook_secret_changed = _ensure_client_webhook_secret_from_instance(
            db,
            client=client,
            branch=branch,
            instance_id=instance_id,
        )

    created_agents: list[Agent] = []
    for account in bootstrap_accounts:
        _ensure_role_not_deprecated_for_assignment(account.role)
        if account.role == "platform_admin" and context.role != "platform_admin":
            raise ConsoleAPIError(403, "ACCESS_DENIED", "Only platform admin can assign platform_admin role")
        membership_branch = branch if account.role == "manager" else None
        created_agents.append(
            _create_agent_with_membership(
                db,
                client=client,
                role=account.role,
                branch=membership_branch,
                name=account.name,
                is_active=account.is_active if account.is_active is not None else True,
                oidc_subject=account.oidc_subject,
                linked_from="branch_account_factory",
                now=now,
            )
        )
    if created_agents:
        ensure_onboarding_step(db, branch, OnboardingStep.TEAM)
    if branch.is_active:
        _require_branch_go_live_gate(branch, operation="branch_activate")
        _require_branch_scorecard_ready(db, branch, operation="branch_activate")

    record_audit_event(
        db,
        actor=context.agent,
        event_type="branch_created",
        entity_type="branch",
        entity_id=branch.id,
        payload={
            "slug": slug,
            "name": name,
            "is_active": is_active,
            "webhook_secret_generated": webhook_secret_changed,
            "bootstrap_accounts_total": len(created_agents),
            "bootstrap_roles": [agent.role for agent in created_agents],
        },
        client_id=client.id,
        branch_id=branch.id,
    )
    _invalidate_tenants_fleet_cache_scope(
        db,
        reason="create_branch",
        company_ids={client.company_id} if client.company_id else None,
    )
    db.commit()

    return ConsoleBranchCreateResponse(
        branch=_serialize_branch(branch),
        created_agents=[_serialize_agent(agent) for agent in created_agents],
    )


@router.patch(
    "/admin/branches/{branch_id}",
    response_model=ConsoleBranch,
    responses={403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}, 409: {"model": ConsoleErrorResponse}},
)
async def update_branch(
    branch_id: UUID,
    request: Request,
    body: ConsoleBranchUpdateRequest,
    db: Session = Depends(get_db),
) -> ConsoleBranch:
    context = get_console_context(
        request,
        db,
        require_selection=False,
        include_inactive_tenants=True,
    )
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
    _require_client_access(context, branch.client_id)
    branch_company_id = _resolve_company_id_for_client_in_context(context, branch.client_id)

    confirmation = None
    previous_instance_id = branch.instance_id
    webhook_secret_changed = False

    fields_set = body.model_fields_set
    if "instance_id" in fields_set:
        ensure_onboarding_step(db, branch, OnboardingStep.INTEGRATIONS)
    if "telegram_chat_id" in fields_set:
        ensure_onboarding_step(db, branch, OnboardingStep.TELEGRAM)
    if "knowledge_tag" in fields_set:
        ensure_onboarding_step(db, branch, OnboardingStep.KNOWLEDGE)
    if "working_hours" in fields_set or "booking_settings" in fields_set:
        ensure_onboarding_step(db, branch, OnboardingStep.BOOKING)

    updated_fields: list[str] = []

    if "slug" in fields_set:
        slug = _normalize_slug(body.slug, "branch_slug")
        if slug != branch.slug:
            _ensure_unique_branch_field(
                db,
                client_id=branch.client_id,
                field_name="slug",
                value=slug,
                exclude_branch_id=branch.id,
            )
            branch.slug = slug
        updated_fields.append("slug")

    if "name" in fields_set:
        branch.name = _normalize_required_text(body.name, "name")
        updated_fields.append("name")

    instance_id = branch.instance_id
    if "instance_id" in fields_set:
        instance_id = _normalize_optional_text(body.instance_id)
        if instance_id != branch.instance_id:
            _ensure_unique_branch_field(
                db,
                client_id=branch.client_id,
                field_name="instance_id",
                value=instance_id,
                exclude_branch_id=branch.id,
            )
            branch.instance_id = instance_id
        updated_fields.append("instance_id")

    if "phone" in fields_set:
        phone = _normalize_branch_phone(body.phone, "phone")
        if phone != branch.phone:
            _ensure_unique_branch_field(
                db,
                client_id=branch.client_id,
                field_name="phone",
                value=phone,
                exclude_branch_id=branch.id,
            )
            branch.phone = phone
        updated_fields.append("phone")

    if "telegram_chat_id" in fields_set:
        branch.telegram_chat_id = _normalize_telegram_chat_id(body.telegram_chat_id, "telegram_chat_id")
        updated_fields.append("telegram_chat_id")

    if "knowledge_tag" in fields_set:
        branch.knowledge_tag = _normalize_knowledge_tag(body.knowledge_tag, "knowledge_tag")
        updated_fields.append("knowledge_tag")

    if "timezone" in fields_set:
        branch.timezone = _normalize_timezone_name(body.timezone, "timezone")
        updated_fields.append("timezone")

    if "working_hours" in fields_set:
        branch.working_hours = body.working_hours if body.working_hours is not None else {}
        updated_fields.append("working_hours")

    if "booking_settings" in fields_set:
        branch.booking_settings = body.booking_settings if body.booking_settings is not None else {}
        updated_fields.append("booking_settings")

    is_active = branch.is_active
    if "is_active" in fields_set:
        if body.is_active is None:
            raise ConsoleAPIError(400, "INVALID_PARAM", "is_active cannot be null")
        is_active = body.is_active
    elif "instance_id" in fields_set and instance_id is None:
        is_active = False

    if is_active and not instance_id:
        raise ConsoleAPIError(400, "INVALID_PARAM", "instance_id required to activate branch")
    if is_active and not branch.is_active:
        _require_branch_go_live_gate(branch, operation="branch_activate")
        _require_branch_scorecard_ready(db, branch, operation="branch_activate")

    requires_confirmation = False
    if "is_active" in fields_set and is_active is False and branch.is_active:
        requires_confirmation = True
    if "instance_id" in fields_set and instance_id is None and previous_instance_id is not None:
        requires_confirmation = True

    if requires_confirmation:
        confirmation = require_confirmation(
            db,
            context,
            confirmation_id=body.confirmation_id,
            action="branch_deactivate",
            target_type="branch",
            target_id=branch.id,
        )

    if is_active != branch.is_active:
        branch.is_active = is_active
        updated_fields.append("is_active")

    if instance_id and "instance_id" in fields_set:
        client_record = db.query(Client).filter(Client.id == branch.client_id).first()
        if client_record:
            _secret, _url, webhook_secret_changed = _ensure_client_webhook_secret_from_instance(
                db,
                client=client_record,
                branch=branch,
                instance_id=instance_id,
            )

    if updated_fields or webhook_secret_changed:
        branch.updated_at = datetime.now(timezone.utc)
        record_audit_event(
            db,
            actor=context.agent,
            event_type="branch_updated",
            entity_type="branch",
            entity_id=branch.id,
            payload={
                "updated_fields": updated_fields,
                "webhook_secret_generated": webhook_secret_changed,
            },
            client_id=branch.client_id,
            branch_id=branch.id,
        )
        if confirmation:
            mark_confirmation_used(
                db,
                context,
                confirmation,
                action="branch_deactivate",
                target_type="branch",
                target_id=branch.id,
            )
        _invalidate_tenants_fleet_cache_scope(
            db,
            reason="update_branch",
            company_ids={branch_company_id} if branch_company_id else None,
        )
        db.commit()

    return _serialize_branch(branch)


def _get_branch_change_for_context(
    db: Session,
    *,
    context: ConsoleAuthContext,
    change_id: UUID,
) -> ConsoleBranchChange:
    query = db.query(ConsoleBranchChange).filter(
        ConsoleBranchChange.id == change_id,
        ConsoleBranchChange.client_id == context.client.id,
    )
    allowed_branch_ids = _resolve_branch_scope(context)
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            raise ConsoleAPIError(404, "NOT_FOUND", "Branch change not found")
        query = query.filter(ConsoleBranchChange.branch_id.in_(allowed_branch_ids))
    change = query.first()
    if not change:
        raise ConsoleAPIError(404, "NOT_FOUND", "Branch change not found")
    return change


@router.get(
    "/admin/branch-changes",
    response_model=ConsoleBranchChangeListResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
)
async def list_branch_changes(
    request: Request,
    branch_id: Optional[UUID] = None,
    status: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> ConsoleBranchChangeListResponse:
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "read",
        message="Only owner/admin can access provisioning",
    )
    _reject_unknown_query_params(request, {"branch_id", "status", "cursor", "limit"})
    _validate_limit(limit)

    query = db.query(ConsoleBranchChange).filter(ConsoleBranchChange.client_id == context.client.id)
    if branch_id:
        query = query.filter(ConsoleBranchChange.branch_id == branch_id)

    allowed_branch_ids = _resolve_branch_scope(context)
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            return ConsoleBranchChangeListResponse(items=[], cursor=None, has_more=False)
        query = query.filter(ConsoleBranchChange.branch_id.in_(allowed_branch_ids))

    if status:
        normalized_status = status.strip().lower()
        allowed_statuses = {"draft", "validated", "publish_failed", "published", "rolled_back"}
        if normalized_status not in allowed_statuses:
            raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid status")
        query = query.filter(ConsoleBranchChange.status == normalized_status)

    cursor_date = _parse_cursor_param(cursor)
    if cursor_date is not None:
        query = query.filter(ConsoleBranchChange.created_at < cursor_date)

    rows = (
        query.order_by(ConsoleBranchChange.created_at.desc(), ConsoleBranchChange.id.desc())
        .limit(limit + 1)
        .all()
    )
    has_more = len(rows) > limit
    items_rows = rows[:limit]
    next_cursor = items_rows[-1].created_at.isoformat() if has_more and items_rows else None
    return ConsoleBranchChangeListResponse(
        items=[_serialize_branch_change_record(row) for row in items_rows],
        cursor=next_cursor,
        has_more=has_more,
    )


@router.get(
    "/admin/branch-changes/{change_id}",
    response_model=ConsoleBranchChangeResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def get_branch_change(
    change_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleBranchChangeResponse:
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "read",
        message="Only owner/admin can access provisioning",
    )
    change = _get_branch_change_for_context(db, context=context, change_id=change_id)
    branch = db.query(Branch).filter(Branch.id == change.branch_id).first()
    return ConsoleBranchChangeResponse(
        change=_serialize_branch_change_record(change),
        branch=_serialize_branch(branch) if branch else None,
    )


@router.post(
    "/admin/branch-changes/draft",
    response_model=ConsoleBranchChangeResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def draft_branch_change(
    body: ConsoleBranchChangeDraftRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleBranchChangeResponse:
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )

    branch = db.query(Branch).filter(Branch.id == body.branch_id).first()
    if not branch:
        raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
    _require_client_access(context, branch.client_id)

    reason = _normalize_access_reason(body.reason, required=True)
    patch_payload = body.patch.model_dump(exclude_unset=True)
    try:
        normalized_patch, errors = _normalize_branch_change_patch(db=db, branch=branch, patch_payload=patch_payload)
    except ConsoleAPIError as exc:
        normalized_patch, errors = {}, [exc.message]
    base_snapshot = _snapshot_branch_for_change(branch)
    diff_payload = _build_branch_change_diff(base_snapshot, normalized_patch)
    if not diff_payload:
        errors.append("No effective branch changes detected")

    now = datetime.now(timezone.utc)
    change = ConsoleBranchChange(
        client_id=branch.client_id,
        branch_id=branch.id,
        actor_agent_id=context.agent.id,
        status="draft",
        reason=reason,
        draft_payload=_jsonable_payload(normalized_patch),
        diff_payload=_jsonable_payload(diff_payload),
        validation_payload={
            "ok": len(errors) == 0,
            "errors": errors,
        },
        base_snapshot=_jsonable_payload(base_snapshot),
        base_branch_updated_at=branch.updated_at,
        created_at=now,
        updated_at=now,
    )
    db.add(change)
    record_audit_event(
        db,
        actor=context.agent,
        event_type="branch_change_drafted",
        entity_type="branch_change",
        entity_id=change.id,
        payload={
            "branch_id": str(branch.id),
            "status": change.status,
            "errors": errors,
        },
        client_id=branch.client_id,
        branch_id=branch.id,
    )
    db.commit()
    db.refresh(change)

    return ConsoleBranchChangeResponse(
        change=_serialize_branch_change_record(change),
        branch=_serialize_branch(branch),
    )


@router.post(
    "/admin/branch-changes/{change_id}/validate",
    response_model=ConsoleBranchChangeResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def validate_branch_change(
    change_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleBranchChangeResponse:
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )
    change = _get_branch_change_for_context(db, context=context, change_id=change_id)
    if change.status not in _BRANCH_CHANGE_MUTABLE_STATUSES:
        raise ConsoleAPIError(409, "INVALID_STATE", "Branch change is not mutable")

    branch = db.query(Branch).filter(Branch.id == change.branch_id).first()
    if not branch:
        raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
    _require_client_access(context, branch.client_id)

    errors: list[str] = []
    try:
        normalized_patch, errors = _normalize_branch_change_patch(
            db=db,
            branch=branch,
            patch_payload=change.draft_payload if isinstance(change.draft_payload, dict) else {},
        )
    except ConsoleAPIError as exc:
        normalized_patch, errors = {}, [exc.message]

    base_snapshot = _snapshot_branch_for_change(branch)
    diff_payload = _build_branch_change_diff(base_snapshot, normalized_patch)
    if not diff_payload:
        errors.append("No effective branch changes detected")

    now = datetime.now(timezone.utc)
    change.draft_payload = _jsonable_payload(normalized_patch)
    change.diff_payload = _jsonable_payload(diff_payload)
    change.base_snapshot = _jsonable_payload(base_snapshot)
    change.base_branch_updated_at = branch.updated_at
    change.validation_payload = {
        "ok": len(errors) == 0,
        "errors": errors,
    }
    change.status = "validated" if not errors else "draft"
    change.validated_at = now if not errors else None
    change.updated_at = now
    db.commit()
    db.refresh(change)
    return ConsoleBranchChangeResponse(
        change=_serialize_branch_change_record(change),
        branch=_serialize_branch(branch),
    )


@router.post(
    "/admin/branch-changes/{change_id}/publish",
    response_model=ConsoleBranchChangeResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}, 409: {"model": ConsoleErrorResponse}},
)
async def publish_branch_change(
    change_id: UUID,
    body: ConsoleBranchChangePublishRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleBranchChangeResponse:
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )
    change = _get_branch_change_for_context(db, context=context, change_id=change_id)
    if change.status not in {"validated", "publish_failed"}:
        raise ConsoleAPIError(409, "INVALID_STATE", "Branch change must be validated before publish")

    branch = db.query(Branch).filter(Branch.id == change.branch_id).first()
    if not branch:
        raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
    _require_client_access(context, branch.client_id)

    if change.base_branch_updated_at and branch.updated_at and change.base_branch_updated_at != branch.updated_at:
        raise ConsoleAPIError(
            409,
            "CHANGE_CONFLICT",
            "Branch changed since draft creation; revalidate before publish",
        )

    errors: list[str] = []
    try:
        normalized_patch, errors = _normalize_branch_change_patch(
            db=db,
            branch=branch,
            patch_payload=change.draft_payload if isinstance(change.draft_payload, dict) else {},
        )
    except ConsoleAPIError as exc:
        normalized_patch, errors = {}, [exc.message]
    diff_payload = _build_branch_change_diff(_snapshot_branch_for_change(branch), normalized_patch)
    if not diff_payload:
        errors.append("No effective branch changes detected")

    now = datetime.now(timezone.utc)
    if errors:
        message = "; ".join(errors)
        change.status = "publish_failed"
        change.publish_error = message
        change.validation_payload = {"ok": False, "errors": errors}
        change.updated_at = now
        db.commit()
        raise ConsoleAPIError(409, "CHANGE_VALIDATION_FAILED", message, {"errors": errors})

    update_request = _build_branch_update_request(
        normalized_patch=normalized_patch,
        confirmation_id=body.confirmation_id,
    )
    try:
        await update_branch(
            branch_id=branch.id,
            request=request,
            body=update_request,
            db=db,
        )
    except ConsoleAPIError as exc:
        change.status = "publish_failed"
        change.publish_error = exc.message
        change.updated_at = now
        db.commit()
        raise

    refreshed_branch = db.query(Branch).filter(Branch.id == branch.id).first()
    change.status = "published"
    change.publish_error = None
    change.published_snapshot = _jsonable_payload(_snapshot_branch_for_change(refreshed_branch)) if refreshed_branch else None
    change.published_at = now
    change.published_by = context.agent.id
    change.updated_at = now
    record_audit_event(
        db,
        actor=context.agent,
        event_type="branch_change_published",
        entity_type="branch_change",
        entity_id=change.id,
        payload={
            "branch_id": str(branch.id),
            "diff": diff_payload,
        },
        client_id=branch.client_id,
        branch_id=branch.id,
    )
    db.commit()
    db.refresh(change)
    return ConsoleBranchChangeResponse(
        change=_serialize_branch_change_record(change),
        branch=_serialize_branch(refreshed_branch) if refreshed_branch else None,
    )


@router.post(
    "/admin/branch-changes/{change_id}/rollback",
    response_model=ConsoleBranchChangeResponse,
    responses={401: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}, 409: {"model": ConsoleErrorResponse}},
)
async def rollback_branch_change(
    change_id: UUID,
    body: ConsoleBranchChangeRollbackRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleBranchChangeResponse:
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )
    change = _get_branch_change_for_context(db, context=context, change_id=change_id)
    if change.status != "published":
        raise ConsoleAPIError(409, "INVALID_STATE", "Only published change can be rolled back")

    branch = db.query(Branch).filter(Branch.id == change.branch_id).first()
    if not branch:
        raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
    _require_client_access(context, branch.client_id)
    rollback_reason = _normalize_access_reason(body.reason, required=True)

    base_snapshot = change.base_snapshot if isinstance(change.base_snapshot, dict) else {}
    current_snapshot = _snapshot_branch_for_change(branch)
    rollback_patch = {
        field: base_snapshot.get(field)
        for field in _BRANCH_CHANGE_MANAGED_FIELDS
        if field in base_snapshot and current_snapshot.get(field) != base_snapshot.get(field)
    }

    now = datetime.now(timezone.utc)
    if not rollback_patch:
        change.status = "rolled_back"
        change.rollback_error = None
        change.rollback_snapshot = _jsonable_payload(current_snapshot)
        change.rolled_back_at = now
        change.rolled_back_by = context.agent.id
        change.updated_at = now
        db.commit()
        db.refresh(change)
        return ConsoleBranchChangeResponse(
            change=_serialize_branch_change_record(change),
            branch=_serialize_branch(branch),
        )

    errors: list[str] = []
    try:
        normalized_patch, errors = _normalize_branch_change_patch(db=db, branch=branch, patch_payload=rollback_patch)
    except ConsoleAPIError as exc:
        normalized_patch, errors = {}, [exc.message]
    if errors:
        message = "; ".join(errors)
        change.rollback_error = message
        change.updated_at = now
        db.commit()
        raise ConsoleAPIError(409, "CHANGE_VALIDATION_FAILED", message, {"errors": errors})

    rollback_request = _build_branch_update_request(
        normalized_patch=normalized_patch,
        confirmation_id=body.confirmation_id,
    )
    try:
        await update_branch(
            branch_id=branch.id,
            request=request,
            body=rollback_request,
            db=db,
        )
    except ConsoleAPIError as exc:
        change.rollback_error = exc.message
        change.updated_at = now
        db.commit()
        raise

    refreshed_branch = db.query(Branch).filter(Branch.id == branch.id).first()
    change.status = "rolled_back"
    change.rollback_error = None
    change.rollback_snapshot = _jsonable_payload(_snapshot_branch_for_change(refreshed_branch)) if refreshed_branch else None
    change.rolled_back_at = now
    change.rolled_back_by = context.agent.id
    change.updated_at = now
    record_audit_event(
        db,
        actor=context.agent,
        event_type="branch_change_rolled_back",
        entity_type="branch_change",
        entity_id=change.id,
        payload={
            "branch_id": str(branch.id),
            "reason": rollback_reason,
        },
        client_id=branch.client_id,
        branch_id=branch.id,
    )
    db.commit()
    db.refresh(change)
    return ConsoleBranchChangeResponse(
        change=_serialize_branch_change_record(change),
        branch=_serialize_branch(refreshed_branch) if refreshed_branch else None,
    )


@router.post(
    "/admin/branches/{branch_id}/go-live/approve",
    response_model=ConsoleBranch,
    responses={403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}, 409: {"model": ConsoleErrorResponse}},
)
async def approve_branch_go_live(
    branch_id: UUID,
    request: Request,
    body: ConsoleBranchGoLiveDecisionRequest,
    db: Session = Depends(get_db),
) -> ConsoleBranch:
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage go-live gate",
    )

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
    _require_client_access(context, branch.client_id)
    branch_company_id = _resolve_company_id_for_client_in_context(context, branch.client_id)

    reason = _normalize_access_reason(body.reason, required=True)
    _require_branch_scorecard_ready(
        db,
        branch,
        operation="branch_go_live_approve",
    )

    now = datetime.now(timezone.utc)
    previous_state = _normalize_branch_go_live_state(branch.go_live_state)
    branch.go_live_state = "approved"
    branch.go_live_reason = reason
    branch.go_live_reviewed_at = now
    branch.go_live_reviewed_by = context.agent.id
    branch.go_live_waiver_until = None
    branch.go_live_waiver_reason = None
    branch.go_live_waiver_by = None
    branch.updated_at = now

    record_audit_event(
        db,
        actor=context.agent,
        event_type="branch_go_live_approved",
        entity_type="branch",
        entity_id=branch.id,
        payload={
            "previous_state": previous_state,
            "next_state": "approved",
            "reason": reason,
        },
        client_id=branch.client_id,
        branch_id=branch.id,
    )
    _invalidate_tenants_fleet_cache_scope(
        db,
        reason="approve_branch_go_live",
        company_ids={branch_company_id} if branch_company_id else None,
    )
    db.commit()
    return _serialize_branch(branch)


@router.post(
    "/admin/branches/{branch_id}/go-live/reject",
    response_model=ConsoleBranch,
    responses={403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def reject_branch_go_live(
    branch_id: UUID,
    request: Request,
    body: ConsoleBranchGoLiveDecisionRequest,
    db: Session = Depends(get_db),
) -> ConsoleBranch:
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage go-live gate",
    )

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
    _require_client_access(context, branch.client_id)
    branch_company_id = _resolve_company_id_for_client_in_context(context, branch.client_id)

    reason = _normalize_access_reason(body.reason, required=True)
    now = datetime.now(timezone.utc)
    previous_state = _normalize_branch_go_live_state(branch.go_live_state)
    branch.go_live_state = "rejected"
    branch.go_live_reason = reason
    branch.go_live_reviewed_at = now
    branch.go_live_reviewed_by = context.agent.id
    branch.go_live_waiver_until = None
    branch.go_live_waiver_reason = None
    branch.go_live_waiver_by = None
    branch.updated_at = now

    record_audit_event(
        db,
        actor=context.agent,
        event_type="branch_go_live_rejected",
        entity_type="branch",
        entity_id=branch.id,
        payload={
            "previous_state": previous_state,
            "next_state": "rejected",
            "reason": reason,
        },
        client_id=branch.client_id,
        branch_id=branch.id,
    )
    _invalidate_tenants_fleet_cache_scope(
        db,
        reason="reject_branch_go_live",
        company_ids={branch_company_id} if branch_company_id else None,
    )
    db.commit()
    return _serialize_branch(branch)


@router.post(
    "/admin/branches/{branch_id}/go-live/waive",
    response_model=ConsoleBranch,
    responses={403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def waive_branch_go_live(
    branch_id: UUID,
    request: Request,
    body: ConsoleBranchGoLiveWaiverRequest,
    db: Session = Depends(get_db),
) -> ConsoleBranch:
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage go-live gate",
    )

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
    _require_client_access(context, branch.client_id)
    branch_company_id = _resolve_company_id_for_client_in_context(context, branch.client_id)

    reason = _normalize_access_reason(body.reason, required=True)
    ttl_hours = _normalize_go_live_waiver_ttl_hours(body.ttl_hours)
    _require_branch_scorecard_ready(
        db,
        branch,
        operation="branch_go_live_waive",
    )

    now = datetime.now(timezone.utc)
    waiver_until = now + timedelta(hours=ttl_hours)
    branch.go_live_waiver_until = waiver_until
    branch.go_live_waiver_reason = reason
    branch.go_live_waiver_by = context.agent.id
    branch.updated_at = now

    record_audit_event(
        db,
        actor=context.agent,
        event_type="branch_go_live_waived",
        entity_type="branch",
        entity_id=branch.id,
        payload={
            "go_live_state": _normalize_branch_go_live_state(branch.go_live_state),
            "reason": reason,
            "ttl_hours": ttl_hours,
            "waiver_until": waiver_until.isoformat(),
        },
        client_id=branch.client_id,
        branch_id=branch.id,
    )
    _invalidate_tenants_fleet_cache_scope(
        db,
        reason="waive_branch_go_live",
        company_ids={branch_company_id} if branch_company_id else None,
    )
    db.commit()
    return _serialize_branch(branch)


@router.post(
    "/admin/agents",
    response_model=ConsoleAgentCreateResponse,
    responses={403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def create_agent(
    request: Request,
    body: ConsoleAgentCreateRequest,
    db: Session = Depends(get_db),
) -> ConsoleAgentCreateResponse:
    context = get_console_context(
        request,
        db,
        require_selection=False,
        include_inactive_tenants=True,
    )
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )

    client = db.query(Client).filter(Client.id == body.client_id).first()
    if not client:
        raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")
    _require_client_access(context, client.id)

    _ensure_role_not_deprecated_for_assignment(body.role)
    if body.role == "manager" and not body.branch_id:
        raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id required for manager role")
    if body.role == "platform_admin" and context.role != "platform_admin":
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Only platform admin can assign platform_admin role")

    sso_username = _normalize_optional_text(body.sso_username)
    sso_password = (body.sso_password or "").strip()
    if body.oidc_subject and sso_username:
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            "Use either oidc_subject or sso_username/sso_password, not both",
        )
    if sso_password and not sso_username:
        raise ConsoleAPIError(400, "INVALID_PARAM", "sso_username is required when sso_password is provided")
    if sso_username and not sso_password:
        raise ConsoleAPIError(400, "INVALID_PARAM", "sso_password is required when sso_username is provided")

    resolved_oidc_subject = body.oidc_subject
    if sso_username and sso_password:
        resolved_oidc_subject = _provision_sso_user_and_get_subject(
            username=sso_username,
            password=sso_password,
            temporary_password=bool(body.sso_temp_password if body.sso_temp_password is not None else True),
        )

    branch = None
    if body.branch_id:
        branch = (
            db.query(Branch)
            .filter(Branch.id == body.branch_id, Branch.client_id == client.id)
            .first()
        )
        if not branch:
            raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
        _require_branch_access(context, branch.id, message="Branch belongs to another tenant")

    branch_for_onboarding = branch
    if not branch_for_onboarding and context.effective_branch_id:
        branch_for_onboarding = (
            db.query(Branch)
            .filter(Branch.id == context.effective_branch_id, Branch.client_id == client.id)
            .first()
        )
    if branch_for_onboarding:
        ensure_onboarding_step(db, branch_for_onboarding, OnboardingStep.TEAM)

    now = datetime.now(timezone.utc)
    is_active = body.is_active if body.is_active is not None else True
    agent = _create_agent_with_membership(
        db,
        client=client,
        role=body.role,
        branch=branch,
        name=body.name,
        is_active=is_active,
        oidc_subject=resolved_oidc_subject,
        linked_from="admin_api",
        now=now,
    )

    record_audit_event(
        db,
        actor=context.agent,
        event_type="agent_created",
        entity_type="agent",
        entity_id=agent.id,
        payload={
            "role": agent.role,
            "branch_id": str(agent.branch_id) if agent.branch_id else None,
            "oidc_linked": bool(resolved_oidc_subject),
            "sso_username": sso_username,
        },
        client_id=client.id,
        branch_id=agent.branch_id,
    )
    db.commit()

    return ConsoleAgentCreateResponse(
        agent=_serialize_agent(agent)
    )


@router.get(
    "/admin/memberships",
    response_model=ConsoleMembershipListResponse,
    responses={403: {"model": ConsoleErrorResponse}},
)
async def list_memberships(
    request: Request,
    agent_id: Optional[str] = Query(default=None),
    scope: Optional[str] = Query(default=None),
    company_id: Optional[str] = Query(default=None),
    client_id: Optional[str] = Query(default=None),
    branch_id: Optional[str] = Query(default=None),
    include_inactive: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> ConsoleMembershipListResponse:
    context = get_console_context(
        request,
        db,
        require_selection=False,
        include_inactive_tenants=True,
    )
    require_console_permission(
        context,
        "provisioning",
        "read",
        message="Only owner/admin can view memberships",
    )

    parsed_agent_id = _parse_uuid_param("agent_id", agent_id)
    parsed_company_id = _parse_uuid_param("company_id", company_id)
    parsed_client_id = _parse_uuid_param("client_id", client_id)
    parsed_branch_id = _parse_uuid_param("branch_id", branch_id)
    include_inactive_rows = _parse_bool_param("include_inactive", include_inactive, default=False)

    normalized_scope = (scope or "").strip().lower() if scope else None
    if normalized_scope and normalized_scope not in {"company", "client", "branch"}:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid scope")

    query = db.query(AgentMembership)
    if parsed_agent_id:
        query = query.filter(AgentMembership.agent_id == parsed_agent_id)
    if normalized_scope:
        query = query.filter(AgentMembership.scope == normalized_scope)
    if parsed_company_id:
        _require_company_access(context, parsed_company_id)
        company_client_ids = [
            row[0]
            for row in db.query(Client.id).filter(Client.company_id == parsed_company_id).all()
        ]
        company_branch_ids: list[UUID] = []
        if company_client_ids:
            company_branch_ids = [
                row[0]
                for row in db.query(Branch.id).filter(Branch.client_id.in_(company_client_ids)).all()
            ]
        company_conditions = [AgentMembership.company_id == parsed_company_id]
        if company_client_ids:
            company_conditions.append(AgentMembership.client_id.in_(company_client_ids))
        if company_branch_ids:
            company_conditions.append(AgentMembership.branch_id.in_(company_branch_ids))
        query = query.filter(or_(*company_conditions))
    if parsed_client_id:
        _require_client_access(context, parsed_client_id)
        target_client = db.query(Client).filter(Client.id == parsed_client_id).first()
        if not target_client:
            raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")
        client_branch_ids = [
            row[0]
            for row in db.query(Branch.id).filter(Branch.client_id == parsed_client_id).all()
        ]
        client_conditions = [AgentMembership.client_id == parsed_client_id]
        if client_branch_ids:
            client_conditions.append(AgentMembership.branch_id.in_(client_branch_ids))
        if target_client.company_id:
            client_conditions.append(AgentMembership.company_id == target_client.company_id)
        query = query.filter(or_(*client_conditions))
    if parsed_branch_id:
        branch = db.query(Branch).filter(Branch.id == parsed_branch_id).first()
        if not branch:
            raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
        _require_client_access(context, branch.client_id)
        branch_client = db.query(Client).filter(Client.id == branch.client_id).first()
        company_id_for_branch = branch_client.company_id if branch_client else None
        branch_conditions = [
            AgentMembership.branch_id == parsed_branch_id,
            AgentMembership.client_id == branch.client_id,
        ]
        if company_id_for_branch:
            branch_conditions.append(AgentMembership.company_id == company_id_for_branch)
        query = query.filter(
            or_(*branch_conditions)
        )
    if not include_inactive_rows:
        query = query.filter(AgentMembership.is_active.is_(True))

    memberships = query.order_by(AgentMembership.created_at.desc()).all()
    if not memberships:
        return ConsoleMembershipListResponse(items=[])

    accessible_client_ids = _accessible_client_ids(context)
    accessible_company_ids = _accessible_company_ids(context)

    agent_ids = {membership.agent_id for membership in memberships}
    agents_by_id = {}
    if agent_ids:
        agents_by_id = {
            agent.id: agent
            for agent in db.query(Agent).filter(Agent.id.in_(agent_ids)).all()
        }

    branch_ids = {membership.branch_id for membership in memberships if membership.branch_id}
    branches_by_id = {}
    if branch_ids:
        branches_by_id = {
            branch.id: branch
            for branch in db.query(Branch).filter(Branch.id.in_(branch_ids)).all()
        }

    items: list[ConsoleAgentMembership] = []
    for membership in memberships:
        candidate_client_ids: set[UUID] = set()
        if membership.client_id:
            candidate_client_ids.add(membership.client_id)
        if membership.branch_id and membership.branch_id in branches_by_id:
            candidate_client_ids.add(branches_by_id[membership.branch_id].client_id)

        accessible = False
        if candidate_client_ids and candidate_client_ids & accessible_client_ids:
            accessible = True
        if not accessible and membership.company_id and membership.company_id in accessible_company_ids:
            accessible = True
        if not accessible:
            continue

        agent = agents_by_id.get(membership.agent_id)
        if agent and agent.role == "platform_admin":
            continue

        items.append(
            _serialize_membership(
                membership,
                agent=agent,
            )
        )

    return ConsoleMembershipListResponse(items=items)


@router.post(
    "/admin/memberships",
    response_model=ConsoleAgentMembership,
    responses={403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def create_membership(
    request: Request,
    body: ConsoleMembershipCreateRequest,
    db: Session = Depends(get_db),
) -> ConsoleAgentMembership:
    context = get_console_context(
        request,
        db,
        require_selection=False,
        include_inactive_tenants=True,
    )
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage memberships",
    )

    agent = db.query(Agent).filter(Agent.id == body.agent_id).first()
    if not agent:
        raise ConsoleAPIError(404, "NOT_FOUND", "Agent not found")
    _require_client_access(context, agent.client_id)
    _ensure_membership_agent_is_mutable(agent)
    _ensure_membership_role_is_assignable(body.role)

    target = _resolve_membership_target(
        db,
        scope=body.scope,
        company_id=body.company_id,
        client_id=body.client_id,
        branch_id=body.branch_id,
    )
    _assert_membership_target_access(context, target)
    _assert_agent_matches_membership_target(db, agent=agent, target=target)

    existing_query = db.query(AgentMembership).filter(AgentMembership.agent_id == agent.id)
    existing_query = _apply_membership_target_filters(
        existing_query,
        scope=target.scope,
        company_id=target.company_id,
        client_id=target.client_id,
        branch_id=target.branch_id,
    )
    existing = existing_query.order_by(AgentMembership.created_at.desc()).first()
    if existing and existing.is_active:
        raise ConsoleAPIError(409, "MEMBERSHIP_EXISTS", "Membership already exists")

    now = datetime.now(timezone.utc)
    is_active = body.is_active if body.is_active is not None else True

    if existing:
        existing.role = body.role
        existing.is_active = is_active
        existing.updated_at = now
        membership = existing
        event_type = "membership_reactivated"
    else:
        membership = AgentMembership(
            id=uuid4(),
            agent_id=agent.id,
            scope=target.scope,
            company_id=target.company_id,
            client_id=target.client_id,
            branch_id=target.branch_id,
            role=body.role,
            is_active=is_active,
            created_at=now,
            updated_at=now,
        )
        db.add(membership)
        event_type = "membership_created"

    record_audit_event(
        db,
        actor=context.agent,
        event_type=event_type,
        entity_type="agent_membership",
        entity_id=membership.id,
        payload={
            "agent_id": str(agent.id),
            "scope": membership.scope,
            "company_id": str(membership.company_id) if membership.company_id else None,
            "client_id": str(membership.client_id) if membership.client_id else None,
            "branch_id": str(membership.branch_id) if membership.branch_id else None,
            "role": membership.role,
            "is_active": membership.is_active,
        },
        client_id=membership.client_id or agent.client_id,
        branch_id=membership.branch_id,
    )
    db.commit()
    return _serialize_membership(membership, agent=agent)


@router.patch(
    "/admin/memberships/{membership_id}",
    response_model=ConsoleAgentMembership,
    responses={403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def update_membership(
    membership_id: UUID,
    request: Request,
    body: ConsoleMembershipUpdateRequest,
    db: Session = Depends(get_db),
) -> ConsoleAgentMembership:
    context = get_console_context(
        request,
        db,
        require_selection=False,
        include_inactive_tenants=True,
    )
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage memberships",
    )

    membership = db.query(AgentMembership).filter(AgentMembership.id == membership_id).first()
    if not membership:
        raise ConsoleAPIError(404, "NOT_FOUND", "Membership not found")
    agent = db.query(Agent).filter(Agent.id == membership.agent_id).first()
    if not agent:
        raise ConsoleAPIError(404, "NOT_FOUND", "Agent not found")

    _require_client_access(context, agent.client_id)
    _ensure_membership_agent_is_mutable(agent)

    previous_scope = membership.scope
    previous_company_id = membership.company_id
    previous_client_id = membership.client_id
    previous_branch_id = membership.branch_id
    previous_active = membership.is_active
    previous_role = membership.role

    fields_set = body.model_fields_set
    if "role" in fields_set:
        _ensure_membership_role_is_assignable(body.role)
    next_scope = body.scope if "scope" in fields_set else membership.scope
    next_company_id = body.company_id if "company_id" in fields_set else membership.company_id
    next_client_id = body.client_id if "client_id" in fields_set else membership.client_id
    next_branch_id = body.branch_id if "branch_id" in fields_set else membership.branch_id
    next_role = body.role if "role" in fields_set and body.role else membership.role
    next_is_active = body.is_active if "is_active" in fields_set and body.is_active is not None else membership.is_active

    target = _resolve_membership_target(
        db,
        scope=next_scope,
        company_id=next_company_id,
        client_id=next_client_id,
        branch_id=next_branch_id,
    )
    _assert_membership_target_access(context, target)
    _assert_agent_matches_membership_target(db, agent=agent, target=target)

    rescope_changed = (
        target.scope != previous_scope
        or target.company_id != previous_company_id
        or target.client_id != previous_client_id
        or target.branch_id != previous_branch_id
    )
    deactivation = "is_active" in fields_set and previous_active and body.is_active is False
    reason = _normalize_access_reason(body.reason, required=rescope_changed or deactivation)
    _ensure_membership_change_keeps_privileged_access(
        db,
        context=context,
        membership=membership,
        agent=agent,
        next_role=next_role,
        next_is_active=next_is_active,
    )

    duplicate_query = db.query(AgentMembership).filter(
        AgentMembership.id != membership.id,
        AgentMembership.agent_id == agent.id,
    )
    duplicate_query = _apply_membership_target_filters(
        duplicate_query,
        scope=target.scope,
        company_id=target.company_id,
        client_id=target.client_id,
        branch_id=target.branch_id,
    )
    duplicate = duplicate_query.filter(AgentMembership.is_active.is_(True)).first()
    if duplicate:
        raise ConsoleAPIError(409, "MEMBERSHIP_EXISTS", "Membership already exists for this scope")

    if "role" in fields_set and body.role:
        membership.role = body.role
    membership.scope = target.scope
    membership.company_id = target.company_id
    membership.client_id = target.client_id
    membership.branch_id = target.branch_id
    if "is_active" in fields_set and body.is_active is not None:
        membership.is_active = body.is_active
    membership.updated_at = datetime.now(timezone.utc)

    record_audit_event(
        db,
        actor=context.agent,
        event_type="membership_updated",
        entity_type="agent_membership",
        entity_id=membership.id,
        payload={
            "reason": reason,
            "previous_scope": previous_scope,
            "previous_company_id": str(previous_company_id) if previous_company_id else None,
            "previous_client_id": str(previous_client_id) if previous_client_id else None,
            "previous_branch_id": str(previous_branch_id) if previous_branch_id else None,
            "previous_role": previous_role,
            "previous_is_active": previous_active,
            "next_scope": membership.scope,
            "next_company_id": str(membership.company_id) if membership.company_id else None,
            "next_client_id": str(membership.client_id) if membership.client_id else None,
            "next_branch_id": str(membership.branch_id) if membership.branch_id else None,
            "next_role": membership.role,
            "next_is_active": membership.is_active,
        },
        client_id=membership.client_id or agent.client_id,
        branch_id=membership.branch_id,
    )
    db.commit()
    return _serialize_membership(membership, agent=agent)


@router.post(
    "/admin/agents/{agent_id}/disable",
    response_model=ConsoleAgent,
    responses={403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def disable_agent_access(
    agent_id: UUID,
    request: Request,
    body: ConsoleAgentLifecycleActionRequest,
    db: Session = Depends(get_db),
) -> ConsoleAgent:
    context = get_console_context(
        request,
        db,
        require_selection=False,
        include_inactive_tenants=True,
    )
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )
    reason = _normalize_access_reason(body.reason, required=True)

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise ConsoleAPIError(404, "NOT_FOUND", "Agent not found")
    _require_client_access(context, agent.client_id)
    _ensure_agent_lifecycle_is_mutable(
        db,
        context=context,
        agent=agent,
        enabling=False,
    )
    if not agent.is_active:
        raise ConsoleAPIError(409, "INVALID_STATE", "Agent is already disabled")

    agent.is_active = False
    agent.updated_at = datetime.now(timezone.utc)
    record_audit_event(
        db,
        actor=context.agent,
        event_type="agent_disabled",
        entity_type="agent",
        entity_id=agent.id,
        payload={"reason": reason},
        client_id=agent.client_id,
        branch_id=agent.branch_id,
    )
    db.commit()
    return _serialize_agent(agent)


@router.post(
    "/admin/agents/{agent_id}/enable",
    response_model=ConsoleAgent,
    responses={403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def enable_agent_access(
    agent_id: UUID,
    request: Request,
    body: ConsoleAgentLifecycleActionRequest,
    db: Session = Depends(get_db),
) -> ConsoleAgent:
    context = get_console_context(
        request,
        db,
        require_selection=False,
        include_inactive_tenants=True,
    )
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )
    reason = _normalize_access_reason(body.reason, required=True)

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise ConsoleAPIError(404, "NOT_FOUND", "Agent not found")
    _require_client_access(context, agent.client_id)
    _ensure_agent_lifecycle_is_mutable(
        db,
        context=context,
        agent=agent,
        enabling=True,
    )
    if agent.is_active:
        raise ConsoleAPIError(409, "INVALID_STATE", "Agent is already active")

    agent.is_active = True
    agent.updated_at = datetime.now(timezone.utc)
    record_audit_event(
        db,
        actor=context.agent,
        event_type="agent_enabled",
        entity_type="agent",
        entity_id=agent.id,
        payload={"reason": reason},
        client_id=agent.client_id,
        branch_id=agent.branch_id,
    )
    db.commit()
    return _serialize_agent(agent)


@router.post(
    "/admin/agents/{agent_id}/oidc/rebind",
    response_model=ConsoleAgentOidcRebindResponse,
    responses={403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def rebind_agent_oidc_identity(
    agent_id: UUID,
    request: Request,
    body: ConsoleAgentOidcRebindRequest,
    db: Session = Depends(get_db),
) -> ConsoleAgentOidcRebindResponse:
    context = get_console_context(
        request,
        db,
        require_selection=False,
        include_inactive_tenants=True,
    )
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )

    reason = _normalize_access_reason(body.reason, required=True)
    oidc_subject = _normalize_required_text(body.oidc_subject, "oidc_subject")
    _ensure_unique_oidc_subject(db, oidc_subject, exclude_agent_id=agent_id)

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise ConsoleAPIError(404, "NOT_FOUND", "Agent not found")
    _require_client_access(context, agent.client_id)
    if agent.role == "platform_admin" and context.role != "platform_admin":
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Only platform admin can rebind platform_admin OIDC")

    now = datetime.now(timezone.utc)
    oidc_identity = (
        db.query(AgentIdentity)
        .filter(AgentIdentity.agent_id == agent.id, AgentIdentity.channel == "oidc")
        .order_by(AgentIdentity.created_at.asc())
        .first()
    )
    previous_subject = oidc_identity.external_id if oidc_identity else None
    if oidc_identity:
        metadata = dict(oidc_identity.identity_metadata or {})
        metadata.update(
            {
                "rebound_from": previous_subject,
                "rebound_by": str(context.agent.id),
                "rebind_reason": reason,
            }
        )
        oidc_identity.external_id = oidc_subject
        oidc_identity.identity_metadata = metadata
        oidc_identity.updated_at = now
    else:
        oidc_identity = AgentIdentity(
            id=uuid4(),
            agent_id=agent.id,
            channel="oidc",
            external_id=oidc_subject,
            username=agent.name,
            identity_metadata={
                "linked_from": "admin_api_rebind",
                "rebind_reason": reason,
                "rebound_by": str(context.agent.id),
            },
            created_at=now,
            updated_at=now,
        )
        db.add(oidc_identity)

    record_audit_event(
        db,
        actor=context.agent,
        event_type="agent_oidc_rebound",
        entity_type="agent",
        entity_id=agent.id,
        payload={
            "reason": reason,
            "previous_oidc_subject": previous_subject,
            "next_oidc_subject": oidc_subject,
        },
        client_id=agent.client_id,
        branch_id=agent.branch_id,
    )
    db.commit()
    return ConsoleAgentOidcRebindResponse(
        agent_id=agent.id,
        oidc_subject=oidc_subject,
        previous_oidc_subject=previous_subject,
    )


def _get_latest_capability(
    db: Session,
    *,
    client_id: UUID,
    scope: str,
    branch_id: Optional[UUID],
) -> Optional[ClientCapability]:
    query = db.query(ClientCapability).filter(
        ClientCapability.client_id == client_id,
        ClientCapability.scope == scope,
    )
    if branch_id:
        query = query.filter(ClientCapability.branch_id == branch_id)
    else:
        query = query.filter(ClientCapability.branch_id.is_(None))
    return query.order_by(
        ClientCapability.updated_at.desc(),
        ClientCapability.created_at.desc(),
    ).first()


def _serialize_capabilities_record(record: ClientCapability) -> ConsoleCapabilitiesRecord:
    try:
        payload = CapabilitiesPayload.model_validate(record.payload_json or {})
    except ValidationError as exc:
        raise ConsoleAPIError(500, "CAPABILITIES_INVALID", "Stored capabilities payload is invalid") from exc
    return ConsoleCapabilitiesRecord(
        id=record.id,
        client_id=record.client_id,
        branch_id=record.branch_id,
        scope=record.scope,
        status=record.status,
        schema_version=record.schema_version,
        payload=payload,
        created_by=record.created_by,
        created_at=record.created_at.isoformat() if record.created_at else None,
        updated_at=record.updated_at.isoformat() if record.updated_at else None,
    )


@router.get(
    "/admin/capabilities",
    response_model=ConsoleCapabilitiesResponse,
    responses={403: {"model": ConsoleErrorResponse}},
)
async def get_capabilities(
    request: Request,
    branch_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
) -> ConsoleCapabilitiesResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "provisioning",
        "read",
        message="Only owner/admin can access provisioning",
    )

    if branch_id:
        branch = (
            db.query(Branch)
            .filter(Branch.id == branch_id, Branch.client_id == context.client.id)
            .first()
        )
        if not branch:
            raise ConsoleAPIError(403, "BRANCH_ACCESS_DENIED", "Access to this branch denied")

    client_record = _get_latest_capability(
        db,
        client_id=context.client.id,
        scope="client",
        branch_id=None,
    )
    branch_record = None
    if branch_id:
        branch_record = _get_latest_capability(
            db,
            client_id=context.client.id,
            scope="branch",
            branch_id=branch_id,
        )

    client_payload = (
        client_record.payload_json
        if client_record and client_record.status == "active"
        else None
    )
    branch_payload = (
        branch_record.payload_json
        if branch_record and branch_record.status == "active"
        else None
    )
    effective_payload = CapabilitiesPayload.model_validate(
        merge_capabilities(client_payload, branch_payload)
    )

    return ConsoleCapabilitiesResponse(
        client_id=context.client.id,
        branch_id=branch_id,
        effective=effective_payload,
        client_capabilities=_serialize_capabilities_record(client_record) if client_record else None,
        branch_capabilities=_serialize_capabilities_record(branch_record) if branch_record else None,
    )


@router.patch(
    "/admin/capabilities",
    response_model=ConsoleCapabilitiesRecord,
    responses={403: {"model": ConsoleErrorResponse}},
)
async def patch_capabilities(
    request: Request,
    body: ConsoleCapabilitiesPatchRequest,
    db: Session = Depends(get_db),
) -> ConsoleCapabilitiesRecord:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage capabilities",
    )

    schema_version = body.schema_version or CAPABILITIES_SCHEMA_VERSION
    if schema_version != CAPABILITIES_SCHEMA_VERSION:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Unsupported schema_version")

    if body.scope == "branch":
        if not body.branch_id:
            raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id required for branch scope")
        branch = (
            db.query(Branch)
            .filter(Branch.id == body.branch_id, Branch.client_id == context.client.id)
            .first()
        )
        if not branch:
            raise ConsoleAPIError(403, "BRANCH_ACCESS_DENIED", "Access to this branch denied")
    elif body.branch_id:
        raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id is only valid for branch scope")

    record = _get_latest_capability(
        db,
        client_id=context.client.id,
        scope=body.scope,
        branch_id=body.branch_id,
    )
    payload_dict = payload_to_dict(body.payload)
    status_value = body.status or (record.status if record else "active")

    if record:
        record.payload_json = payload_dict
        record.schema_version = schema_version
        record.status = status_value
    else:
        record = ClientCapability(
            client_id=context.client.id,
            branch_id=body.branch_id,
            scope=body.scope,
            payload_json=payload_dict,
            schema_version=schema_version,
            status=status_value,
            created_by=context.agent.id,
        )
        db.add(record)

    record_audit_event(
        db,
        actor=context.agent,
        event_type="capabilities_updated",
        entity_type="client_capabilities",
        entity_id=record.id,
        branch_id=record.branch_id,
        payload={
            "scope": record.scope,
            "client_id": str(context.client.id),
            "branch_id": str(record.branch_id) if record.branch_id else None,
            "schema_version": record.schema_version,
            "status": record.status,
        },
    )
    db.commit()

    return _serialize_capabilities_record(record)


def _get_latest_onboarding_contract(
    db: Session,
    *,
    client_id: UUID,
    scope: str,
    branch_id: Optional[UUID],
) -> Optional[ClientOnboardingContract]:
    query = db.query(ClientOnboardingContract).filter(
        ClientOnboardingContract.client_id == client_id,
        ClientOnboardingContract.scope == scope,
    )
    if branch_id:
        query = query.filter(ClientOnboardingContract.branch_id == branch_id)
    else:
        query = query.filter(ClientOnboardingContract.branch_id.is_(None))
    return query.order_by(
        ClientOnboardingContract.updated_at.desc(),
        ClientOnboardingContract.created_at.desc(),
    ).first()


def _serialize_onboarding_contract_record(
    record: ClientOnboardingContract,
) -> ConsoleOnboardingContractRecord:
    try:
        payload = OnboardingContractPayload.model_validate(record.payload_json or {})
    except ValidationError as exc:
        raise ConsoleAPIError(
            500,
            "ONBOARDING_CONTRACT_INVALID",
            "Stored onboarding contract payload is invalid",
        ) from exc
    return ConsoleOnboardingContractRecord(
        id=record.id,
        client_id=record.client_id,
        branch_id=record.branch_id,
        scope=record.scope,
        status=record.status,
        schema_version=record.schema_version,
        payment_status=record.payment_status,
        payment_confirmed_at=record.payment_confirmed_at.isoformat()
        if record.payment_confirmed_at
        else None,
        payment_confirmed_by=record.payment_confirmed_by,
        payload=payload,
        created_by=record.created_by,
        created_at=record.created_at.isoformat() if record.created_at else None,
        updated_at=record.updated_at.isoformat() if record.updated_at else None,
    )


def _resolve_onboarding_payment_source(
    *,
    client_record: Optional[ClientOnboardingContract],
    branch_record: Optional[ClientOnboardingContract],
) -> Optional[ClientOnboardingContract]:
    if branch_record and branch_record.status == "active":
        return branch_record
    if client_record and client_record.status == "active":
        return client_record
    return None


def _serialize_reference_pack(record: ReferencePack) -> ConsoleReferencePack:
    return ConsoleReferencePack(
        id=record.id,
        domain_slug=record.domain_slug,
        title=record.title,
        description=record.description,
        schema_version=record.schema_version,
        status=record.status,
        metadata=record.metadata_json or {},
        created_by=record.created_by,
        created_at=record.created_at.isoformat() if record.created_at else None,
        updated_at=record.updated_at.isoformat() if record.updated_at else None,
    )


def _serialize_onboarding_blueprint(record) -> ConsoleOnboardingBlueprint:
    return ConsoleOnboardingBlueprint(
        id=record.id,
        domain_slug=record.domain_slug,
        label=record.label,
        summary=record.summary,
        payload=record.payload,
        go_live_blockers_profile=list(record.go_live_blockers_profile),
        question_templates=[
            ConsoleOnboardingBlueprintQuestionTemplate(
                code=item.code,
                question=item.question,
                blocking_go_live=item.blocking_go_live,
            )
            for item in record.question_templates
        ],
        required_fields_profile=ConsoleOnboardingBlueprintRequiredFieldsProfile(
            fields=list(record.required_fields_profile.fields),
            checksum=record.required_fields_profile.checksum,
        ),
        readiness_weights={key: weight for key, weight in record.readiness_weights},
    )


_AUTOPILOT_DEFAULT_TIMEZONE = "Asia/Almaty"


def _derive_webhook_secret_from_instance(instance_id: str) -> str:
    normalized_instance = _normalize_required_text(instance_id, "instance_id")
    return derive_webhook_secret_from_instance(normalized_instance)


def _build_webhook_url(*, client_slug: str, webhook_secret: str) -> str:
    base_url = (
        os.environ.get("WEBHOOK_PUBLIC_BASE_URL")
        or os.environ.get("PUBLIC_API_BASE_URL")
        or "https://api.truffles.kz"
    ).rstrip("/")
    normalized_client_slug = _normalize_slug(client_slug, "client_slug")
    return f"{base_url}/webhook/{normalized_client_slug}?webhook_secret={webhook_secret}"


def _ensure_client_webhook_secret_from_instance(
    db: Session,
    *,
    client: Client,
    branch: Branch,
    instance_id: str,
) -> tuple[str, str, bool]:
    secret = _derive_webhook_secret_from_instance(instance_id)
    changed = (branch.webhook_secret or "").strip() != secret
    branch.webhook_secret = secret
    webhook_url = _build_webhook_url(client_slug=client.name, webhook_secret=secret)
    return secret, webhook_url, changed


def _slugify_seed(value: Optional[str], *, fallback_prefix: str, fallback_suffix: str) -> str:
    if isinstance(value, str):
        candidate = re.sub(r"[^a-z0-9_-]+", "-", value.strip().lower())
        candidate = re.sub(r"-{2,}", "-", candidate).strip("-_")
    else:
        candidate = ""
    if not candidate:
        suffix = re.sub(r"\D+", "", fallback_suffix)
        suffix = suffix[-6:] if suffix else ""
        candidate = f"{fallback_prefix}-{suffix}" if suffix else fallback_prefix
    return _normalize_slug(candidate, fallback_prefix)


def _next_available_branch_slug(
    db: Session,
    *,
    client_id: UUID,
    preferred_slug: str,
    exclude_branch_id: Optional[UUID] = None,
) -> str:
    slug = preferred_slug
    suffix = 2
    while True:
        query = db.query(Branch).filter(Branch.client_id == client_id, Branch.slug == slug)
        if exclude_branch_id:
            query = query.filter(Branch.id != exclude_branch_id)
        if not query.first():
            return slug
        slug = f"{preferred_slug}-{suffix}"
        suffix += 1


def _build_capabilities_from_purchased_services(
    *,
    purchased_services: Optional[list[str]],
    purchased_payload: Optional[CapabilitiesPayload],
    domain_slug: Optional[str],
) -> CapabilitiesPayload:
    services = set(purchased_services or [])
    base = CapabilitiesPayload()

    if "whatsapp" in services:
        base.channels.whatsapp = True
    if "telegram" in services:
        base.channels.telegram = True
    if "instagram" in services:
        base.channels.instagram = True

    if "booking_collect" in services:
        base.features.booking_mode = "collect_preferences"
    if "booking_confirm" in services:
        base.features.booking_mode = "confirm_slots"

    if "knowledge_upload" in services:
        base.features.knowledge_upload = True
    if "analytics" in services:
        base.features.analytics = True
    if "auto_learn" in services:
        base.features.auto_learn = True

    provider_map = {
        "provider_google_calendar": "google_calendar",
        "provider_local_calendar": "local",
        "provider_manual": "manual",
    }
    for key, provider in provider_map.items():
        if key in services:
            base.providers.calendar_provider = provider
            if provider == "manual":
                base.providers.availability_provider = "manual"

    if "provider_amocrm" in services:
        base.providers.crm_provider = "amocrm"
    if "provider_bitrix" in services:
        base.providers.crm_provider = "bitrix"

    if domain_slug:
        base.domain_slug = domain_slug

    merged = merge_capabilities(
        payload_to_dict(base),
        payload_to_dict(purchased_payload) if purchased_payload else None,
    )
    result = CapabilitiesPayload.model_validate(merged)
    if domain_slug:
        result.domain_slug = domain_slug
    return result


def _build_client_schema(client: Client, company: Optional[Company]) -> ConsoleClient:
    return ConsoleClient(
        id=client.id,
        slug=client.name,
        name=client.name,
        status=client.status,
        company_id=client.company_id,
        company_name=company.name if company else None,
    )


@router.get(
    "/admin/onboarding-contract",
    response_model=ConsoleOnboardingContractResponse,
    responses={403: {"model": ConsoleErrorResponse}},
)
async def get_onboarding_contract(
    request: Request,
    branch_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
) -> ConsoleOnboardingContractResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "provisioning",
        "read",
        message="Only owner/admin can access provisioning",
    )

    if branch_id:
        branch = (
            db.query(Branch)
            .filter(Branch.id == branch_id, Branch.client_id == context.client.id)
            .first()
        )
        if not branch:
            raise ConsoleAPIError(403, "BRANCH_ACCESS_DENIED", "Access to this branch denied")

    client_record = _get_latest_onboarding_contract(
        db,
        client_id=context.client.id,
        scope="client",
        branch_id=None,
    )
    branch_record = None
    if branch_id:
        branch_record = _get_latest_onboarding_contract(
            db,
            client_id=context.client.id,
            scope="branch",
            branch_id=branch_id,
        )

    client_payload = (
        client_record.payload_json
        if client_record and client_record.status == "active"
        else None
    )
    branch_payload = (
        branch_record.payload_json
        if branch_record and branch_record.status == "active"
        else None
    )
    effective_payload = OnboardingContractPayload.model_validate(
        merge_onboarding_contract(client_payload, branch_payload)
    )

    client_capability_record = _get_latest_capability(
        db,
        client_id=context.client.id,
        scope="client",
        branch_id=None,
    )
    branch_capability_record = None
    if branch_id:
        branch_capability_record = _get_latest_capability(
            db,
            client_id=context.client.id,
            scope="branch",
            branch_id=branch_id,
        )
    client_capability_payload = (
        client_capability_record.payload_json
        if client_capability_record and client_capability_record.status == "active"
        else None
    )
    branch_capability_payload = (
        branch_capability_record.payload_json
        if branch_capability_record and branch_capability_record.status == "active"
        else None
    )
    effective_capabilities = CapabilitiesPayload.model_validate(
        merge_capabilities(client_capability_payload, branch_capability_payload)
    )
    capability_mismatches = []
    if client_capability_payload or branch_capability_payload:
        capability_mismatches = find_capability_mismatches(
            purchased=effective_payload.purchased,
            effective=effective_capabilities,
        )

    payment_source = _resolve_onboarding_payment_source(
        client_record=client_record,
        branch_record=branch_record,
    )
    payment_status = payment_source.payment_status if payment_source else "pending"
    payment_confirmed_at = payment_source.payment_confirmed_at if payment_source else None
    payment_confirmed_by = payment_source.payment_confirmed_by if payment_source else None

    return ConsoleOnboardingContractResponse(
        client_id=context.client.id,
        branch_id=branch_id,
        effective=effective_payload,
        payment_status=payment_status,
        payment_confirmed_at=payment_confirmed_at.isoformat() if payment_confirmed_at else None,
        payment_confirmed_by=payment_confirmed_by,
        capability_mismatches=capability_mismatches,
        client_contract=_serialize_onboarding_contract_record(client_record) if client_record else None,
        branch_contract=_serialize_onboarding_contract_record(branch_record) if branch_record else None,
    )


@router.patch(
    "/admin/onboarding-contract",
    response_model=ConsoleOnboardingContractRecord,
    responses={403: {"model": ConsoleErrorResponse}},
)
async def patch_onboarding_contract(
    request: Request,
    body: ConsoleOnboardingContractPatchRequest,
    db: Session = Depends(get_db),
) -> ConsoleOnboardingContractRecord:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage onboarding contract",
    )
    if body.payment_status is not None and context.role != "platform_admin":
        raise ConsoleAPIError(
            403,
            "ACCESS_DENIED",
            "Only platform admin can update payment status",
        )

    schema_version = body.schema_version or ONBOARDING_CONTRACT_SCHEMA_VERSION
    if schema_version != ONBOARDING_CONTRACT_SCHEMA_VERSION:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Unsupported schema_version")

    if body.scope == "branch":
        if not body.branch_id:
            raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id required for branch scope")
        branch = (
            db.query(Branch)
            .filter(Branch.id == body.branch_id, Branch.client_id == context.client.id)
            .first()
        )
        if not branch:
            raise ConsoleAPIError(403, "BRANCH_ACCESS_DENIED", "Access to this branch denied")
    elif body.branch_id:
        raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id is only valid for branch scope")

    record = _get_latest_onboarding_contract(
        db,
        client_id=context.client.id,
        scope=body.scope,
        branch_id=body.branch_id,
    )
    payload_dict = onboarding_contract_payload_to_dict(body.payload)
    status_value = body.status or (record.status if record else "active")

    now = datetime.now(timezone.utc)
    if record:
        record.payload_json = payload_dict
        record.schema_version = schema_version
        record.status = status_value
    else:
        record = ClientOnboardingContract(
            client_id=context.client.id,
            branch_id=body.branch_id,
            scope=body.scope,
            payload_json=payload_dict,
            schema_version=schema_version,
            status=status_value,
            created_by=context.agent.id,
        )
        db.add(record)

    if body.payment_status is not None:
        record.payment_status = body.payment_status
        if body.payment_status == "confirmed":
            record.payment_confirmed_at = now
            record.payment_confirmed_by = context.agent.id
        else:
            record.payment_confirmed_at = None
            record.payment_confirmed_by = None
    elif not record.payment_status:
        record.payment_status = "pending"
        record.payment_confirmed_at = None
        record.payment_confirmed_by = None

    record_audit_event(
        db,
        actor=context.agent,
        event_type="onboarding_contract_updated",
        entity_type="client_onboarding_contract",
        entity_id=record.id,
        branch_id=record.branch_id,
        payload={
            "scope": record.scope,
            "client_id": str(context.client.id),
            "branch_id": str(record.branch_id) if record.branch_id else None,
            "schema_version": record.schema_version,
            "status": record.status,
            "payment_status": record.payment_status,
        },
    )
    db.commit()
    return _serialize_onboarding_contract_record(record)


@router.get(
    "/admin/webhook-secret",
    response_model=ConsoleWebhookSecretResponse,
    responses={403: {"model": ConsoleErrorResponse}},
)
async def get_webhook_secret(
    request: Request,
    branch_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
) -> ConsoleWebhookSecretResponse:
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "provisioning",
        "read",
        message="Only owner/admin can access provisioning",
    )

    branch = _resolve_branch_for_onboarding(context, branch_id=branch_id)
    if not branch.instance_id:
        raise ConsoleAPIError(400, "INVALID_PARAM", "instance_id is required before webhook secret generation")

    client = db.query(Client).filter(Client.id == branch.client_id).first()
    if not client:
        raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")

    webhook_secret, webhook_url, changed = _ensure_client_webhook_secret_from_instance(
        db,
        client=client,
        branch=branch,
        instance_id=branch.instance_id,
    )
    if changed:
        record_audit_event(
            db,
            actor=context.agent,
            event_type="webhook_secret_generated",
            entity_type="branch",
            entity_id=branch.id,
            payload={
                "client_id": str(client.id),
                "branch_id": str(branch.id),
                "instance_id": branch.instance_id,
            },
            client_id=client.id,
            branch_id=branch.id,
        )
        db.commit()

    return ConsoleWebhookSecretResponse(
        client_id=client.id,
        branch_id=branch.id,
        instance_id=branch.instance_id,
        webhook_secret=webhook_secret,
        webhook_url=webhook_url,
    )


@router.post(
    "/admin/onboarding/autopilot",
    response_model=ConsoleOnboardingAutopilotResponse,
    responses={403: {"model": ConsoleErrorResponse}},
)
async def run_onboarding_autopilot(
    request: Request,
    body: ConsoleOnboardingAutopilotRequest,
    db: Session = Depends(get_db),
) -> ConsoleOnboardingAutopilotResponse:
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can run onboarding autopilot",
    )

    now = datetime.now(timezone.utc)
    actions: list[str] = []

    phone = _normalize_branch_phone(body.phone, "phone")
    if not phone:
        raise ConsoleAPIError(400, "INVALID_PARAM", "phone is required")
    instance_id = _normalize_required_text(body.instance_id, "instance_id")
    requested_payment_status = body.payment_status or "pending"
    if context.role != "platform_admin":
        requested_payment_status = "pending"

    company: Optional[Company] = None
    if body.company_id:
        company = db.query(Company).filter(Company.id == body.company_id).first()
        if not company:
            raise ConsoleAPIError(404, "NOT_FOUND", "Company not found")
        if context.role != "platform_admin":
            _require_company_access(context, company.id)
    else:
        company_name = _normalize_optional_text(body.company_name)
        if company_name:
            company = db.query(Company).filter(func.lower(Company.name) == company_name.lower()).first()
            if not company:
                company = Company(
                    id=uuid4(),
                    name=company_name,
                    billing_info={},
                    created_at=now,
                    updated_at=now,
                )
                db.add(company)
                db.flush()
                actions.append("company_created")
            elif context.role != "platform_admin":
                _require_company_access(context, company.id)
        elif context.client and context.client.company_id:
            company = db.query(Company).filter(Company.id == context.client.company_id).first()

    if not company:
        default_company_name = _normalize_optional_text(body.company_name) or f"Company {phone[-4:]}"
        company = db.query(Company).filter(func.lower(Company.name) == default_company_name.lower()).first()
        if not company:
            company = Company(
                id=uuid4(),
                name=default_company_name,
                billing_info={},
                created_at=now,
                updated_at=now,
            )
            db.add(company)
            db.flush()
            actions.append("company_created")
        elif context.role != "platform_admin":
            _require_company_access(context, company.id)

    client: Optional[Client] = None
    if body.client_id:
        client = db.query(Client).filter(Client.id == body.client_id).first()
        if not client:
            raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")
        if context.role != "platform_admin":
            _require_client_access(context, client.id)
    else:
        slug_seed = _normalize_optional_text(body.client_slug) or _normalize_optional_text(body.company_name)
        client_slug = _slugify_seed(slug_seed, fallback_prefix="client", fallback_suffix=phone)
        client = db.query(Client).filter(func.lower(Client.name) == client_slug.lower()).first()
        if not client:
            client = Client(
                id=uuid4(),
                name=client_slug,
                status="active",
                config={},
                created_at=now,
                updated_at=now,
                company_id=company.id if company else None,
            )
            db.add(client)
            db.flush()
            actions.append("client_created")
        elif context.role != "platform_admin":
            _require_client_access(context, client.id)

    if not client:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Unable to resolve client")

    if company and client.company_id != company.id:
        client.company_id = company.id
        client.updated_at = now
        actions.append("client_company_updated")

    existing_phone_branch = db.query(Branch).filter(Branch.phone == phone).first()
    if existing_phone_branch and (not body.branch_id or existing_phone_branch.id != body.branch_id):
        raise ConsoleAPIError(400, "INVALID_PARAM", "phone already linked to another branch")
    existing_instance_branch = db.query(Branch).filter(Branch.instance_id == instance_id).first()
    if existing_instance_branch and (not body.branch_id or existing_instance_branch.id != body.branch_id):
        raise ConsoleAPIError(400, "INVALID_PARAM", "instance_id already linked to another branch")

    branch: Optional[Branch] = None
    if body.branch_id:
        branch = db.query(Branch).filter(Branch.id == body.branch_id).first()
        if not branch:
            raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
        if branch.client_id != client.id:
            raise ConsoleAPIError(403, "BRANCH_ACCESS_DENIED", "Branch belongs to another client")
    else:
        if existing_phone_branch and existing_phone_branch.client_id == client.id:
            branch = existing_phone_branch
            actions.append("branch_matched_by_phone")
        elif existing_instance_branch and existing_instance_branch.client_id == client.id:
            branch = existing_instance_branch
            actions.append("branch_matched_by_instance")

    if not branch:
        slug_seed = _normalize_optional_text(body.branch_slug) or _normalize_optional_text(body.branch_name) or client.name
        preferred_slug = _slugify_seed(slug_seed, fallback_prefix="branch", fallback_suffix=phone)
        branch_slug = _next_available_branch_slug(db, client_id=client.id, preferred_slug=preferred_slug)
        branch_name = _normalize_optional_text(body.branch_name) or branch_slug.replace("-", " ").title()
        branch = Branch(
            id=uuid4(),
            client_id=client.id,
            slug=branch_slug,
            name=branch_name,
            instance_id=instance_id,
            phone=phone,
            timezone=_normalize_timezone_name(body.timezone, "timezone") or _AUTOPILOT_DEFAULT_TIMEZONE,
            working_hours={},
            booking_settings={},
            is_active=bool(body.activate_branch if body.activate_branch is not None else False),
            onboarding_state=OnboardingStep.BRANCH_DRAFT.value,
            onboarding_updated_at=now,
            go_live_state=_BRANCH_GO_LIVE_DEFAULT_STATE,
            created_at=now,
            updated_at=now,
        )
        db.add(branch)
        db.flush()
        actions.append("branch_created")
    else:
        branch_slug = (
            _slugify_seed(body.branch_slug, fallback_prefix="branch", fallback_suffix=phone)
            if _normalize_optional_text(body.branch_slug)
            else branch.slug
        )
        branch.slug = _next_available_branch_slug(
            db,
            client_id=client.id,
            preferred_slug=branch_slug,
            exclude_branch_id=branch.id,
        )
        branch_name = _normalize_optional_text(body.branch_name)
        if branch_name:
            branch.name = branch_name
        branch.phone = phone
        branch.instance_id = instance_id
        branch.timezone = _normalize_timezone_name(body.timezone, "timezone") or branch.timezone or _AUTOPILOT_DEFAULT_TIMEZONE
        if body.activate_branch is not None:
            branch.is_active = body.activate_branch
        if not branch.onboarding_state:
            branch.onboarding_state = OnboardingStep.BRANCH_DRAFT.value
            branch.onboarding_updated_at = now
        branch.go_live_state = _normalize_branch_go_live_state(getattr(branch, "go_live_state", None))
        branch.updated_at = now
        actions.append("branch_updated")

    if branch.is_active and not branch.instance_id:
        raise ConsoleAPIError(400, "INVALID_PARAM", "instance_id required to activate branch")
    if branch.is_active:
        _require_branch_go_live_gate(branch, operation="branch_activate")

    if not branch.knowledge_tag:
        knowledge_seed = _normalize_optional_text(body.client_slug) or client.name
        branch.knowledge_tag = _slugify_seed(knowledge_seed, fallback_prefix="knowledge", fallback_suffix=phone)
        actions.append("knowledge_tag_generated")

    webhook_secret, webhook_url, webhook_secret_changed = _ensure_client_webhook_secret_from_instance(
        db,
        client=client,
        branch=branch,
        instance_id=instance_id,
    )
    if webhook_secret_changed:
        actions.append("webhook_secret_generated")

    domain_slug = _normalize_optional_text(body.domain_slug)
    purchased_capabilities = _build_capabilities_from_purchased_services(
        purchased_services=body.purchased_services,
        purchased_payload=body.purchased,
        domain_slug=domain_slug,
    )
    if not purchased_capabilities.domain_slug and domain_slug:
        purchased_capabilities.domain_slug = domain_slug

    capability_record = _get_latest_capability(
        db,
        client_id=client.id,
        scope="branch",
        branch_id=branch.id,
    )
    if capability_record:
        capability_record.payload_json = payload_to_dict(purchased_capabilities)
        capability_record.schema_version = CAPABILITIES_SCHEMA_VERSION
        capability_record.status = "active"
    else:
        capability_record = ClientCapability(
            client_id=client.id,
            branch_id=branch.id,
            scope="branch",
            payload_json=payload_to_dict(purchased_capabilities),
            schema_version=CAPABILITIES_SCHEMA_VERSION,
            status="active",
            created_by=context.agent.id,
        )
        db.add(capability_record)
    actions.append("capabilities_upserted")

    contract_record = _get_latest_onboarding_contract(
        db,
        client_id=client.id,
        scope="branch",
        branch_id=branch.id,
    )
    provider_binding_override = None
    if body.provider_binding is not None:
        provider_binding_override = body.provider_binding.model_dump(exclude_none=True, mode="json")
        whatsapp_override = provider_binding_override.get("whatsapp")
        if isinstance(whatsapp_override, dict):
            if not _normalize_optional_text(whatsapp_override.get("instance_id")):
                whatsapp_override["instance_id"] = instance_id
            paid_until_override = _normalize_optional_text(whatsapp_override.get("paid_until"))
            next_renewal_override = _normalize_optional_text(whatsapp_override.get("next_renewal_at"))
            if paid_until_override and not next_renewal_override:
                whatsapp_override["next_renewal_at"] = paid_until_override
    contract_payload_override: dict[str, object] = {
        "domain_slug": domain_slug or purchased_capabilities.domain_slug,
        "purchased": payload_to_dict(purchased_capabilities),
    }
    if provider_binding_override is not None:
        contract_payload_override["provider_binding"] = provider_binding_override
    base_contract_payload = (
        contract_record.payload_json
        if contract_record
        and contract_record.status == "active"
        and isinstance(contract_record.payload_json, dict)
        else None
    )
    contract_payload = OnboardingContractPayload.model_validate(
        merge_onboarding_contract(base_contract_payload, contract_payload_override)
    )
    if contract_record:
        contract_record.payload_json = onboarding_contract_payload_to_dict(contract_payload)
        contract_record.schema_version = ONBOARDING_CONTRACT_SCHEMA_VERSION
        contract_record.status = "active"
    else:
        contract_record = ClientOnboardingContract(
            client_id=client.id,
            branch_id=branch.id,
            scope="branch",
            payload_json=onboarding_contract_payload_to_dict(contract_payload),
            schema_version=ONBOARDING_CONTRACT_SCHEMA_VERSION,
            status="active",
            created_by=context.agent.id,
        )
        db.add(contract_record)
    contract_record.payment_status = requested_payment_status
    if requested_payment_status == "confirmed":
        contract_record.payment_confirmed_at = now
        contract_record.payment_confirmed_by = context.agent.id
    else:
        contract_record.payment_confirmed_at = None
        contract_record.payment_confirmed_by = None
    actions.append("onboarding_contract_upserted")

    reference_pack: Optional[ReferencePack] = None
    effective_domain_slug = contract_payload.domain_slug or purchased_capabilities.domain_slug
    if effective_domain_slug:
        reference_pack = (
            db.query(ReferencePack)
            .filter(ReferencePack.domain_slug == effective_domain_slug)
            .first()
        )
        if (
            not reference_pack
            and body.auto_create_reference_pack
            and context.role == "platform_admin"
        ):
            reference_metadata = build_reference_pack_metadata(
                domain_slug=effective_domain_slug,
                metadata={"source": "onboarding_autopilot"},
            )
            reference_pack = ReferencePack(
                domain_slug=effective_domain_slug,
                title=f"Reference pack: {effective_domain_slug}",
                description="Auto-created by onboarding autopilot",
                schema_version=REFERENCE_PACK_SCHEMA_VERSION,
                status="active",
                metadata_json=reference_metadata,
                created_by=context.agent.id,
            )
            db.add(reference_pack)
            db.flush()
            actions.append("reference_pack_created")
        elif (
            reference_pack
            and body.auto_create_reference_pack
            and context.role == "platform_admin"
        ):
            next_metadata = build_reference_pack_metadata(
                domain_slug=effective_domain_slug,
                metadata=reference_pack.metadata_json if isinstance(reference_pack.metadata_json, dict) else None,
            )
            if (
                reference_pack.schema_version != REFERENCE_PACK_SCHEMA_VERSION
                or reference_pack.metadata_json != next_metadata
            ):
                reference_pack.schema_version = REFERENCE_PACK_SCHEMA_VERSION
                reference_pack.metadata_json = next_metadata
                actions.append("reference_pack_integrity_synced")

    intake_payload = build_intake_payload(
        client_data_json=body.client_data_json or {},
        client_data_text=body.client_data_text,
    )
    booking_required = purchased_capabilities.features.booking_mode is not None
    if isinstance(intake_payload.get("client_pack"), dict):
        client_pack = intake_payload["client_pack"]
        business = client_pack.setdefault("business", {})
        if isinstance(business, dict) and not business.get("name"):
            business["name"] = branch.name
        communication = client_pack.setdefault("communication", {}) if isinstance(client_pack, dict) else {}
        languages = communication.get("languages") if isinstance(communication, dict) else None
        if not isinstance(languages, list):
            communication["languages"] = []
        location = client_pack.setdefault("location", {})
        if isinstance(location, dict) and not location.get("city"):
            location["city"] = ""
        address = location.setdefault("address", {}) if isinstance(location, dict) else {}
        if isinstance(address, dict) and "full" not in address:
            address["full"] = ""

    draft_version = upsert_draft(
        db,
        branch_id=branch.id,
        client_id=client.id,
        payload_json=intake_payload,
        actor_id=context.agent.id,
    )
    missing_fields, missing_questions = evaluate_intake_payload(
        intake_payload,
        domain_slug=effective_domain_slug,
        require_booking=booking_required,
    )
    actions.append("knowledge_draft_saved")

    published = False
    published_version_id: Optional[UUID] = None
    effective_intake_payload = intake_payload
    if body.auto_publish_knowledge and not missing_fields:
        try:
            published_version = publish_version(
                db,
                branch=branch,
                payload_json=intake_payload,
                actor_id=context.agent.id,
                source_version_id=draft_version.id if draft_version else None,
            )
            sync_published_branch_docs(
                db,
                client_slug=client.name,
                branch=branch,
                version=published_version,
                backfill_other_branches=True,
            )
            compiled = extract_compiled_artifacts(
                published_version.payload_json,
                compile_if_missing=False,
            )
            pack_index = compiled.get("pack_index") if isinstance(compiled, dict) else None
            if isinstance(pack_index, dict):
                compiled_at = parse_compiled_at(compiled.get("compiled_at")) or published_version.published_at or now
                apply_pack_index_to_client_config(
                    client,
                    pack_index=pack_index,
                    version_id=published_version.id,
                    compiled_at=compiled_at,
                    source="onboarding_autopilot",
                    compiled_meta=build_compiled_pack_meta(
                        compiled,
                        version_id=published_version.id,
                        compiled_at=compiled_at,
                        source="onboarding_autopilot",
                    ),
                )
            published = True
            published_version_id = published_version.id
            effective_intake_payload = published_version.payload_json
            missing_fields, missing_questions = evaluate_intake_payload(
                published_version.payload_json,
                domain_slug=effective_domain_slug,
                require_booking=booking_required,
            )
            actions.append("knowledge_published")
        except Exception:
            actions.append("knowledge_publish_failed")

    field_states = build_intake_field_states(
        effective_intake_payload,
        domain_slug=effective_domain_slug,
        require_booking=booking_required,
        missing_fields=missing_fields,
        client_data_json=body.client_data_json or {},
    )
    question_queue = build_intake_question_queue(
        missing_fields,
        domain_slug=effective_domain_slug,
    )
    pack_quality = build_intake_pack_quality_summary(
        effective_intake_payload,
        domain_slug=effective_domain_slug,
        require_booking=booking_required,
    )

    inputs = build_onboarding_inputs(db, branch)
    scorecard = build_onboarding_scorecard(db, branch)
    go_no_go_missing = scorecard.missing
    if body.activate_branch and not scorecard.ready:
        failed_checks = [
            check.id.value
            for check in scorecard.checks
            if check.required and not check.passed
        ]
        db.rollback()
        raise ConsoleAPIError(
            409,
            "GO_LIVE_GATE_REQUIRED",
            "Onboarding scorecard failed",
            {
                "operation": "onboarding_autopilot_activate",
                "required_step": OnboardingStep.GO_NO_GO.value,
                "missing": scorecard.missing,
                "scorecard_status": "fail",
                "failed_checks": failed_checks,
            },
        )
    onboarding_status = build_onboarding_status(db, branch)

    record_audit_event(
        db,
        actor=context.agent,
        event_type="onboarding_autopilot_run",
        entity_type="branch",
        entity_id=branch.id,
        payload={
            "company_id": str(company.id) if company else None,
            "client_id": str(client.id),
            "branch_id": str(branch.id),
            "actions": actions,
            "missing_count": len(missing_fields),
            "go_no_go_missing_count": len(go_no_go_missing),
        },
        client_id=client.id,
        branch_id=branch.id,
    )
    db.commit()

    return ConsoleOnboardingAutopilotResponse(
        company=ConsoleCompany(
            id=company.id,
            name=company.name,
            billing_info=company.billing_info,
        ),
        client=_build_client_schema(client, company),
        branch=_serialize_branch(branch),
        capabilities=_serialize_capabilities_record(capability_record),
        onboarding_contract=_serialize_onboarding_contract_record(contract_record),
        payment_status=contract_record.payment_status,
        webhook_secret=webhook_secret,
        webhook_url=webhook_url,
        reference_pack=_serialize_reference_pack(reference_pack) if reference_pack else None,
        onboarding_status=_serialize_onboarding_status(branch, onboarding_status),
        go_no_go_missing=go_no_go_missing,
        intake=ConsoleOnboardingAutopilotIntake(
            knowledge_tag=branch.knowledge_tag or "",
            draft_saved=True,
            published=published,
            published_version_id=published_version_id,
            missing_fields=missing_fields,
            missing_questions=missing_questions,
            field_states=[
                {
                    "field": item.field,
                    "status": item.status,
                    "priority": item.priority,
                }
                for item in field_states
            ],
            question_queue=[
                {
                    "field": item.field,
                    "question": item.question,
                    "priority": item.priority,
                    "blocking_go_live": item.blocking_go_live,
                }
                for item in question_queue
            ],
            compile=ConsoleOnboardingIntakeCompile(
                status=pack_quality.compile.status,
                infra_valid=pack_quality.compile.infra_valid,
                schema_version=pack_quality.compile.schema_version,
                hash=pack_quality.compile.hash,
                pack_index_hash=pack_quality.compile.pack_index_hash,
                signal_graph_present=pack_quality.compile.signal_graph_present,
                policy_bundle_present=pack_quality.compile.policy_bundle_present,
                errors=pack_quality.compile.errors,
            ),
            quality_matrix=ConsoleOnboardingIntakeQualityMatrix(
                status=pack_quality.quality_matrix.status,
                infra_valid=pack_quality.quality_matrix.infra_valid,
                semantic_valid=pack_quality.quality_matrix.semantic_valid,
                required_fields_count=pack_quality.quality_matrix.required_fields_count,
                missing_fields_count=pack_quality.quality_matrix.missing_fields_count,
                critical_missing_fields_count=pack_quality.quality_matrix.critical_missing_fields_count,
                integrity_missing_count=pack_quality.quality_matrix.integrity_missing_count,
                missing_fields=pack_quality.quality_matrix.missing_fields,
                critical_missing_fields=pack_quality.quality_matrix.critical_missing_fields,
                integrity_missing=pack_quality.quality_matrix.integrity_missing,
                dimensions=[
                    ConsoleOnboardingIntakeQualityDimension(
                        id=item.id,
                        status=item.status,
                        required=item.required,
                        details=item.details,
                    )
                    for item in pack_quality.quality_matrix.dimensions
                ],
                regressions=pack_quality.quality_matrix.regressions,
                comparison_blocked=pack_quality.quality_matrix.comparison_blocked,
                comparison_block_reason=pack_quality.quality_matrix.comparison_block_reason,
            ),
            payload=intake_payload,
        ),
        actions=actions,
    )


@router.get(
    "/admin/onboarding-blueprints",
    response_model=ConsoleOnboardingBlueprintListResponse,
    responses={403: {"model": ConsoleErrorResponse}},
)
async def list_onboarding_blueprints_api(
    request: Request,
    domain_slug: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> ConsoleOnboardingBlueprintListResponse:
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "read",
        message="Only owner/admin can access provisioning",
    )

    items = list_onboarding_blueprints()
    if domain_slug:
        normalized_domain_slug = _normalize_slug(domain_slug, "domain_slug")
        items = [item for item in items if item.domain_slug == normalized_domain_slug]

    return ConsoleOnboardingBlueprintListResponse(
        items=[_serialize_onboarding_blueprint(item) for item in items]
    )


@router.get(
    "/admin/reference-packs",
    response_model=ConsoleReferencePackListResponse,
    responses={403: {"model": ConsoleErrorResponse}},
)
async def list_reference_packs(
    request: Request,
    domain_slug: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> ConsoleReferencePackListResponse:
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "read",
        message="Only owner/admin can access provisioning",
    )

    query = db.query(ReferencePack)
    if domain_slug:
        normalized_domain_slug = _normalize_slug(domain_slug, "domain_slug")
        query = query.filter(ReferencePack.domain_slug == normalized_domain_slug)

    items = query.order_by(ReferencePack.domain_slug.asc()).all()
    return ConsoleReferencePackListResponse(items=[_serialize_reference_pack(item) for item in items])


@router.put(
    "/admin/reference-packs/{domain_slug}",
    response_model=ConsoleReferencePack,
    responses={403: {"model": ConsoleErrorResponse}},
)
async def upsert_reference_pack(
    domain_slug: str,
    body: ConsoleReferencePackUpsertRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ConsoleReferencePack:
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage reference packs",
    )
    if context.role != "platform_admin":
        raise ConsoleAPIError(
            403,
            "ACCESS_DENIED",
            "Only platform admin can manage reference packs",
        )

    normalized_domain_slug = _normalize_slug(domain_slug, "domain_slug")
    title = _normalize_required_text(body.title, "title")
    schema_version = body.schema_version or REFERENCE_PACK_SCHEMA_VERSION
    if schema_version != REFERENCE_PACK_SCHEMA_VERSION:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Unsupported reference pack schema_version")
    status_value = body.status or "active"
    metadata_json = build_reference_pack_metadata(
        domain_slug=normalized_domain_slug,
        metadata=body.metadata or {},
    )

    record = db.query(ReferencePack).filter(ReferencePack.domain_slug == normalized_domain_slug).first()
    if record:
        record.title = title
        record.description = _normalize_optional_text(body.description)
        record.schema_version = schema_version
        record.status = status_value
        record.metadata_json = metadata_json
    else:
        record = ReferencePack(
            domain_slug=normalized_domain_slug,
            title=title,
            description=_normalize_optional_text(body.description),
            schema_version=schema_version,
            status=status_value,
            metadata_json=metadata_json,
            created_by=context.agent.id,
        )
        db.add(record)
        db.flush()

    record_audit_event(
        db,
        actor=context.agent,
        event_type="reference_pack_upserted",
        entity_type="reference_pack",
        entity_id=record.id,
        payload={
            "domain_slug": normalized_domain_slug,
            "status": record.status,
            "schema_version": record.schema_version,
        },
    )
    db.commit()
    return _serialize_reference_pack(record)
