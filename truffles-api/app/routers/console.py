import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import date as dt_date
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Callable, Optional
from urllib.parse import urlparse
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import and_, case, func, or_, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Agent,
    AgentIdentity,
    AgentMembership,
    Branch,
    Client,
    ClientCapability,
    ClientOnboardingContract,
    ClientSettings,
    Company,
    ConsoleBranchChange,
    ConsoleOpsJob,
    Conversation,
    Handover,
    KnowledgeVersion,
    LearnedResponse,
    Message,
    OutboxMessage,
    ReferencePack,
    User,
)
from app.models import (
    ConsoleMacro as ConsoleMacroModel,
)
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
    ConsoleErrorResponse,
    ConsoleFleetAttentionItem,
    ConsoleFleetAttentionResponse,
    ConsoleFleetAttentionSummary,
    ConsoleFleetSummary,
    ConsoleHealthResponse,
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
    ConsoleMembershipCreateRequest,
    ConsoleMembershipListResponse,
    ConsoleMembershipUpdateRequest,
    ConsoleMeResponse,
    ConsoleMessage,
    ConsoleMessageListResponse,
    ConsoleMetricsDailyResponse,
    ConsoleOnboardingAdvanceRequest,
    ConsoleOnboardingAutopilotIntake,
    ConsoleOnboardingAutopilotRequest,
    ConsoleOnboardingAutopilotResponse,
    ConsoleOnboardingContractPatchRequest,
    ConsoleOnboardingContractRecord,
    ConsoleOnboardingContractResponse,
    ConsoleOnboardingStatusResponse,
    ConsoleOnboardingStepStatus,
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
    ConsoleReferencePack,
    ConsoleReferencePackListResponse,
    ConsoleReferencePackUpsertRequest,
    ConsoleSettingsResponse,
    ConsoleSettingsUpdateRequest,
    ConsoleSettingsUpdateResponse,
    ConsoleSyncStatus,
    ConsoleTelegramHealthResponse,
    ConsoleTelegramLinkResponse,
    ConsoleTelegramTestRequest,
    ConsoleTelegramTestResponse,
    ConsoleTelegramTrail,
    ConsoleTelegramVerifyRequest,
    ConsoleTelegramVerifyResponse,
    ConsoleWebhookSecretResponse,
)
from app.schemas.console import (
    ConsoleMacro as ConsoleMacroSchema,
)
from app.schemas.onboarding_contract import ONBOARDING_CONTRACT_SCHEMA_VERSION, OnboardingContractPayload
from app.schemas.outbox_payload import validate_outbox_payload
from app.services.agent_link_service import build_telegram_deep_link, create_agent_link_token
from app.services.alert_service import alert_warning
from app.services.audit_service import record_audit_event
from app.services.capabilities_service import merge_capabilities, payload_to_dict
from app.services.console_auth import ConsoleAuthContext, get_console_context, require_console_permission
from app.services.console_confirmations import create_confirmation, mark_confirmation_used, require_confirmation
from app.services.console_errors import ConsoleAPIError, build_console_error_payload
from app.services.console_idempotency import (
    finalize_idempotency,
    release_idempotency,
    start_idempotency,
)
from app.services.escalation_service import resolve_telegram_routing
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
from app.services.metrics_daily_service import (
    get_metrics_daily_backfill_max_days,
    get_metrics_daily_default_date,
    run_metrics_daily_snapshot,
)
from app.services.onboarding_contract_service import (
    find_capability_mismatches,
    merge_onboarding_contract,
    onboarding_contract_payload_to_dict,
)
from app.services.onboarding_intake_service import build_intake_payload, evaluate_intake_payload
from app.services.onboarding_state import (
    OnboardingStep,
    advance_onboarding_step,
    build_onboarding_inputs,
    build_onboarding_status,
    ensure_onboarding_step,
    missing_prerequisites,
)
from app.services.pack_compiler_service import (
    PackCompilerError,
    build_compiled_pack_meta,
    extract_compiled_artifacts,
    parse_compiled_at,
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


def _require_branch_access(
    context: ConsoleAuthContext,
    branch_id: Optional[UUID],
    *,
    message: str,
) -> None:
    if branch_id is None:
        return
    if context.role in ("platform_admin", "owner", "admin"):
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
    return ConsoleBranch(
        id=branch.id,
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
        else:
            try:
                slug = _normalize_slug(str(raw_slug), "branch_slug")
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
        else:
            try:
                normalized["name"] = _normalize_required_text(str(raw_name), "name")
            except ConsoleAPIError as exc:
                errors.append(exc.message)

    if "timezone" in patch_payload:
        normalized["timezone"] = _normalize_optional_text(
            patch_payload.get("timezone") if isinstance(patch_payload.get("timezone"), str) else None
        )

    if "instance_id" in patch_payload:
        instance_id = _normalize_optional_text(
            patch_payload.get("instance_id") if isinstance(patch_payload.get("instance_id"), str) else None
        )
        _ensure_unique_branch_field(
            db,
            client_id=branch.client_id,
            field_name="instance_id",
            value=instance_id,
            exclude_branch_id=branch.id,
        )
        normalized["instance_id"] = instance_id

    if "phone" in patch_payload:
        phone = _normalize_optional_text(
            patch_payload.get("phone") if isinstance(patch_payload.get("phone"), str) else None
        )
        _ensure_unique_branch_field(
            db,
            client_id=branch.client_id,
            field_name="phone",
            value=phone,
            exclude_branch_id=branch.id,
        )
        normalized["phone"] = phone

    if "telegram_chat_id" in patch_payload:
        normalized["telegram_chat_id"] = _normalize_optional_text(
            patch_payload.get("telegram_chat_id") if isinstance(patch_payload.get("telegram_chat_id"), str) else None
        )

    if "knowledge_tag" in patch_payload:
        normalized["knowledge_tag"] = _normalize_optional_text(
            patch_payload.get("knowledge_tag") if isinstance(patch_payload.get("knowledge_tag"), str) else None
        )

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


_TENANT_LIFECYCLE_MODES = {"active", "archived", "all"}
_CLIENT_STATUS_ACTIVE = "active"
_CLIENT_STATUS_ARCHIVED = "deleted"
_CLIENT_LIFECYCLE_REASON_MAX_LEN = 500
_ACCESS_REASON_MAX_LEN = 500
_PRIVILEGED_ACCESS_ROLES = {"platform_admin", "owner", "admin"}
_CLIENT_ARCHIVE_SAMPLE_LIMIT = 20
_BRANCH_BOOTSTRAP_ACCOUNTS_MAX = 20
_BRANCH_GO_LIVE_STATES = {"pending", "approved", "rejected"}
_BRANCH_GO_LIVE_DEFAULT_STATE = "pending"
_GO_LIVE_WAIVER_MIN_HOURS = 1
_GO_LIVE_WAIVER_MAX_HOURS = 24 * 30
_INTEGRATION_DEFAULT_STALE_MINUTES = 60
_INTEGRATION_MIN_STALE_MINUTES = 5
_INTEGRATION_MAX_STALE_MINUTES = 24 * 60
_INTEGRATION_ALERT_ISSUES = {
    "instance_id_mismatch",
    "invalid_webhook_url",
    "invalid_webhook_secret",
    "inbound_without_outbound",
    "no_recent_inbound",
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


def _accessible_client_ids(context: ConsoleAuthContext) -> set[UUID]:
    client_ids = {client.id for client in (context.accessible_clients or [])}
    if context.client and context.client.id:
        client_ids.add(context.client.id)
    return client_ids


def _accessible_company_ids(context: ConsoleAuthContext) -> set[UUID]:
    return {client.company_id for client in (context.accessible_clients or []) if client.company_id}


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


def _ensure_membership_role_is_assignable(role: Optional[str]) -> None:
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
    for branch in branches:
        stats = branch_stats.setdefault(
            branch.client_id,
            {
                "total_branches": 0,
                "active_branches": 0,
                "degraded_branches": 0,
                "go_live_ready_branches": 0,
            },
        )
        stats["total_branches"] += 1
        if branch.is_active:
            stats["active_branches"] += 1
            if (branch.onboarding_state or "").strip().lower() == "go_no_go":
                stats["go_live_ready_branches"] += 1
        if (branch.integration_state or "").strip().lower() == "degraded":
            stats["degraded_branches"] += 1

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
        )
    return details


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


def _compose_fleet_summary(
    *,
    total_clients: int,
    company_ids: set[UUID],
    lifecycle_counts: dict[str, int],
    payment_counts: dict[str, int],
    service_counts: dict[str, int],
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
    )


def _build_fleet_summary_for_scope(
    db: Session,
    *,
    build_client_query: Callable[[Optional[datetime]], object],
    fleet_lifecycle: Optional[str],
    payment_status: Optional[str],
    service_state: Optional[str],
    batch_size: int = 200,
) -> ConsoleFleetSummary:
    lifecycle_counts = {state: 0 for state in _FLEET_LIFECYCLE_ORDER}
    payment_counts = {state: 0 for state in _FLEET_PAYMENT_ORDER}
    service_counts = {state: 0 for state in _FLEET_SERVICE_ORDER}
    total_clients = 0
    company_ids: set[UUID] = set()
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

        batch_details = _build_fleet_client_details_map(
            db,
            clients=batch,
            companies_by_id=batch_companies_by_id,
        )

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
        drift_issues=drift_issues,
        status=status,
    )


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
}


def _require_ops_access(context: ConsoleAuthContext, *, action: str = "read") -> None:
    message = "Only owner/admin/support can access ops"
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
) -> dict:
    pending = len(_query_scoped_outbox_message_rows(db, context=context, status="PENDING"))
    processing = len(_query_scoped_outbox_message_rows(db, context=context, status="PROCESSING"))
    failed = len(_query_scoped_outbox_message_rows(db, context=context, status="FAILED"))
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
        },
        "counts": {
            "pending": pending,
            "processing": processing,
            "failed": failed,
        },
    }


def _claim_scoped_outbox_rows(
    db: Session,
    *,
    context: ConsoleAuthContext,
    limit: int,
    idle_seconds: int,
    max_wait_seconds: int,
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

    if not conversation_ids:
        return []

    rows_query = (
        db.query(OutboxMessage)
        .filter(
            OutboxMessage.client_id == context.client.id,
            OutboxMessage.status == "PENDING",
            OutboxMessage.conversation_id.in_(conversation_ids),
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
    max_attempts = int(os.environ.get("OUTBOX_MAX_ATTEMPTS", "5"))
    retry_backoff_seconds = float(os.environ.get("OUTBOX_RETRY_BACKOFF_SECONDS", "2"))

    if mode == "dry_run":
        return _build_outbox_dry_run_summary(
            db,
            context=context,
            limit=limit,
            idle_seconds=idle_seconds,
            max_wait_seconds=max_wait_seconds,
        )

    claimed_rows = _claim_scoped_outbox_rows(
        db,
        context=context,
        limit=limit,
        idle_seconds=idle_seconds,
        max_wait_seconds=max_wait_seconds,
    )
    if not claimed_rows:
        return {
            "mode": "execute",
            "scope": {"client_id": str(context.client.id)},
            "processed": 0,
            "results": {"processed": 0, "failed": 0},
        }

    from app.routers.webhook import _process_outbox_rows

    results = await _process_outbox_rows(
        db,
        claimed_rows,
        max_attempts=max_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
    )
    return {
        "mode": "execute",
        "scope": {"client_id": str(context.client.id)},
        "processed": len(claimed_rows),
        "results": results,
    }


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
    last_activity_since_dt = _parse_datetime_param("last_activity_since", last_activity_since)
    sort_by_value = _parse_sort_param("sort_by", request.query_params.get("sort_by"))
    
    # Base query
    query = (
        db.query(Handover, Conversation, User)
        .join(Conversation, Handover.conversation_id == Conversation.id)
        .outerjoin(User, and_(User.id == Conversation.user_id, User.client_id == context.client.id))
        .filter(
            Handover.client_id == context.client.id,
            Conversation.client_id == context.client.id,
        )
    )

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
        .subquery()
    )

    last_inbound_subq = (
        db.query(
            Message.conversation_id.label("conversation_id"),
            func.max(Message.created_at).label("last_inbound_at"),
        )
        .filter(Message.role == "user")
        .group_by(Message.conversation_id)
        .subquery()
    )

    last_outbound_subq = (
        db.query(
            Message.conversation_id.label("conversation_id"),
            func.max(Message.created_at).label("last_outbound_at"),
        )
        .filter(Message.role.in_(["assistant", "manager", "system"]))
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
        .group_by(OutboxMessage.conversation_id)
        .subquery()
    )

    query = query.outerjoin(
        latest_message_subq,
        and_(
            latest_message_subq.c.conversation_id == Conversation.id,
            latest_message_subq.c.rn == 1,
        ),
    )
    query = query.outerjoin(last_inbound_subq, last_inbound_subq.c.conversation_id == Conversation.id)
    query = query.outerjoin(last_outbound_subq, last_outbound_subq.c.conversation_id == Conversation.id)
    query = query.outerjoin(outbox_subq, outbox_subq.c.conversation_id == Conversation.id)

    # Branch filter (RBAC + Request)
    allowed_branch_ids = {b.id for b in context.branches}
    is_privileged = context.agent.role in ("platform_admin", "owner", "admin")

    if not is_privileged:
        if not allowed_branch_ids:
            return ConsoleCaseListResponse(items=[], cursor=None, has_more=False)
        query = query.filter(Conversation.branch_id.in_(allowed_branch_ids))
    
    if branch_id is not None:
        bid = _parse_uuid_param("branch_id", branch_id)
        if not is_privileged and bid not in allowed_branch_ids:
            raise ConsoleAPIError(403, "ACCESS_DENIED", "Access to this branch denied")
        query = query.filter(Conversation.branch_id == bid)
    elif context.branch_restricted:
        query = query.filter(Conversation.branch_id.in_(allowed_branch_ids))
    
    # Status filter
    status_filters = _parse_case_status_param("status", request.query_params.get("status") or status)
    if status_filters:
        query = query.filter(Handover.status.in_(status_filters))
    
    # Date range filter
    if date_from is not None:
        from_date = _parse_date_param("date_from", date_from)
        start_of_day = datetime.combine(from_date, time.min).replace(tzinfo=timezone.utc)
        query = query.filter(Handover.created_at >= start_of_day)
    
    if date_to is not None:
        to_date = _parse_date_param("date_to", date_to)
        end_of_day = datetime.combine(to_date, time.max).replace(tzinfo=timezone.utc)
        query = query.filter(Handover.created_at <= end_of_day)
    
    # Assigned to me
    if assigned_to_me:
        query = query.filter(
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
            query = query.filter(or_(*conditions))

    if phone:
        digits = _normalize_phone_digits(phone)
        if digits:
            query = query.filter(
                func.regexp_replace(User.phone, r"\D", "", "g").ilike(f"%{digits}%")
            )

    if has_delivery_error:
        query = query.filter(outbox_subq.c.failed_count > 0)

    if has_pending_outbox:
        query = query.filter(outbox_subq.c.pending_count > 0)

    if last_activity_since_dt:
        query = query.filter(latest_message_subq.c.created_at >= last_activity_since_dt)

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
            ) in items
        ],
        cursor=next_cursor,
        has_more=has_more,
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
        decision_trace=decision_trace,
        last_inbound_at=case_health.get("last_inbound_at").isoformat() if case_health.get("last_inbound_at") else None,
        last_outbound_at=case_health.get("last_outbound_at").isoformat() if case_health.get("last_outbound_at") else None,
        last_activity_at=case_health.get("last_activity_at").isoformat() if case_health.get("last_activity_at") else None,
        last_activity_channel=case_health.get("last_activity_channel"),
        last_message_preview=case_health.get("last_message_preview"),
        needs_reply=case_health.get("needs_reply"),
        has_delivery_error=case_health.get("has_delivery_error"),
        has_pending_outbox=case_health.get("has_pending_outbox"),
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
    from app.models import Conversation, User
    from app.schemas.console import ConsoleManagerMessageRequest, ConsoleManagerMessageResponse
    from app.services.chatflow_service import send_bot_response
    from app.services.manager_message_service import get_user_remote_jid
    
    logger = get_logger("console_send_message")
    
    context = get_console_context(request, db)
    require_console_permission(context, "inbox", "write")
    idempotency = None
    idempotency_key = _get_idempotency_key(request)
    
    # Verify access to conversation via handover
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
            "content": body.content,
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
            content=body.content,
            created_at=datetime.now(timezone.utc),
            message_metadata={"source": "console"},
        )
        db.add(new_message)

        # Audit
        record_audit_event(
            db,
            actor=context.agent,
            event_type="message_sent",
            entity_type="conversation",
            entity_id=conversation_id,
            payload={"content_length": len(body.content), "source": "web_console"},
            branch_id=conversation.branch_id,
        )

        db.commit()
        commit_done = True
        db.refresh(new_message)
    except Exception:
        if idempotency and idempotency.record and not commit_done:
            release_idempotency(db, record=idempotency.record)
        raise
    
    # Send to WhatsApp
    delivery_status = "pending"
    delivery_error = None
    
    try:
        # Get user's WhatsApp JID
        remote_jid = get_user_remote_jid(db, conversation.user_id)
        
        if not remote_jid:
            logger.warning(f"No remote_jid for user {conversation.user_id}")
            delivery_status = "failed"
            delivery_error = "user_jid_not_found"
        else:
            # Send via ChatFlow (same as Telegram manager messages)
            sent = send_bot_response(
                db=db,
                client_id=context.client.id,
                remote_jid=remote_jid,
                message=body.content,
                branch_id=conversation.branch_id,
                idempotency_key=idempotency_key,
            )
            
            if sent:
                delivery_status = "delivered"
                logger.info(f"Message {new_message.id} sent to {remote_jid} via web console")
            else:
                delivery_status = "failed"
                delivery_error = "chatflow_send_failed"
                logger.error(f"Failed to send message {new_message.id} to {remote_jid}")
    except Exception as e:
        logger.error(f"WhatsApp delivery error: {e}")
        delivery_status = "failed"
        delivery_error = str(e)
    
    if delivery_status == "delivered":
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
                        text=f"🖥️ <b>{manager_label}</b>: {body.content}",
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
        success=delivery_status == "delivered",
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
    "/conversations/{conversation_id}/messages/media",
    response_model=ConsoleManagerMessageResponse,
)
async def send_manager_media(
    conversation_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
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


@router.get(
    "/health",
    response_model=ConsoleHealthResponse,
)
async def get_health(db: Session = Depends(get_db)) -> ConsoleHealthResponse:
    """Get system health status."""
    import os

    from app.models import OutboxMessage
    from app.schemas.console import ConsoleHealthResponse
    
    # Check database
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        print(f"DB health check error: {e}")
        db_status = "error"
    
    # Count outbox backlog
    try:
        backlog = (
            db.query(OutboxMessage)
            .filter(OutboxMessage.status.in_(["PENDING", "PROCESSING"]))
            .count()
        )
    except Exception:
        backlog = -1
    
    return ConsoleHealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        version=os.getenv("APP_VERSION", "dev"),
        database=db_status,
        redis="connected",  # Simplified for MVP
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
    from app.schemas.console import ConsoleSettingsUpdateRequest, ConsoleSettingsUpdateResponse
    
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "settings",
        "write",
        message="Only owner/admin can update settings",
    )
    
    # Get client settings
    from app.models import ClientSettings
    
    settings = db.query(ClientSettings).filter(
        ClientSettings.client_id == context.client.id
    ).first()
    
    if not settings:
        # Create settings if not exists
        settings = ClientSettings(client_id=context.client.id)
        db.add(settings)
    
    # Update fields if provided
    updated_fields = []
    if body.reminder_1_minutes is not None:
        settings.reminder_1_minutes = body.reminder_1_minutes
        updated_fields.append("reminder_1_minutes")
    if body.reminder_2_minutes is not None:
        settings.reminder_2_minutes = body.reminder_2_minutes
        updated_fields.append("reminder_2_minutes")
    if body.escalation_timeout_minutes is not None:
        settings.escalation_timeout_minutes = body.escalation_timeout_minutes
        updated_fields.append("escalation_timeout_minutes")
    
    db.commit()
    
    # Audit log
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
        message="Only owner/admin/support can access onboarding",
    )
    branch = _resolve_branch_for_onboarding(context, branch_id=branch_id)
    status = build_onboarding_status(db, branch)
    return _serialize_onboarding_status(branch, status)


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
    current = get_current_published(db, branch_id=branch.id)
    current_payload = current.payload_json if current else None
    payload, errors, warnings, diff = validate_draft(
        body.draft_text,
        current_payload=current_payload,
    )
    valid = not errors
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
            payload={
                "valid": valid,
                "errors": errors,
                "warnings": warnings,
            },
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
    responses={400: {"model": ConsoleErrorResponse}, 403: {"model": ConsoleErrorResponse}},
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

    current = get_current_published(db, branch_id=branch.id)
    current_payload = current.payload_json if current else None
    payload, errors, warnings, _diff = validate_draft(
        body.draft_text,
        current_payload=current_payload,
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

    company_uuid = _parse_uuid_param("company_id", company_id)
    query_value = _normalize_search_query("q", q) if q else None
    cursor_date = _parse_cursor_param(cursor)

    def _build_client_query(cursor_cutoff: Optional[datetime]):
        query = db.query(Client)
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
            batch_details = _build_fleet_client_details_map(
                db,
                clients=batch,
                companies_by_id=batch_companies_by_id,
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
        fleet_details_map = _build_fleet_client_details_map(
            db,
            clients=clients,
            companies_by_id=companies_by_id,
        )

    summary = None
    if include_summary_mode:
        summary = _build_fleet_summary_for_scope(
            db,
            build_client_query=_build_client_query,
            fleet_lifecycle=fleet_lifecycle_filter,
            payment_status=payment_status_filter,
            service_state=service_state_filter,
            batch_size=max(limit * 4, 100),
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
    client_id: Optional[str] = None,
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
    _reject_unknown_query_params(request, {"cursor", "limit", "q", "client_id", "lifecycle"})
    _validate_limit(limit)

    client_uuid = _parse_uuid_param("client_id", client_id)
    query = db.query(Branch)
    if lifecycle_mode == "active":
        query = query.filter(Branch.is_active.is_(True))
    elif lifecycle_mode == "archived":
        query = query.filter(Branch.is_active.is_(False))
    if client_uuid:
        query = query.filter(Branch.client_id == client_uuid)

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
    db: Session = Depends(get_db),
) -> ConsoleIntegrationsListResponse:
    context = get_console_context(request, db, require_selection=False, include_inactive_tenants=False)
    _require_platform_admin(context)
    _reject_unknown_query_params(request, {"stale_after_minutes"})

    active_clients = [
        client for client in (context.accessible_clients or []) if _is_client_active_status(client.status)
    ]
    if not active_clients:
        return ConsoleIntegrationsListResponse(
            stale_after_minutes=stale_after_minutes,
            items=[],
        )

    client_ids = [client.id for client in active_clients]
    client_slug_map = {client.id: client.name for client in active_clients}

    branches = (
        db.query(Branch)
        .filter(Branch.client_id.in_(client_ids))
        .order_by(Branch.client_id.asc(), Branch.name.asc(), Branch.created_at.asc())
        .all()
    )
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
    now = datetime.now(timezone.utc)
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
        )
        items.append(item)

    return ConsoleIntegrationsListResponse(
        stale_after_minutes=stale_after_minutes,
        items=items,
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
    if not branch.is_active:
        raise ConsoleAPIError(409, "INVALID_STATE", "Branch is inactive")

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
        db.commit()

    return ConsoleIntegrationBranchActionResponse(
        branch_id=branch.id,
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

    companies_by_id = {company.id: company for company in (context.companies or [])}
    fleet_details_map = _build_fleet_client_details_map(
        db,
        clients=active_clients,
        companies_by_id=companies_by_id,
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

    now = datetime.now(timezone.utc)
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

        stale_branches = 0
        integration_error_branches = 0
        integration_warn_branches = 0

        for branch in branches_by_client.get(client.id, []):
            if not branch.is_active:
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
    phone = _normalize_optional_text(body.phone)
    telegram_chat_id = _normalize_optional_text(body.telegram_chat_id)
    knowledge_tag = _normalize_optional_text(body.knowledge_tag)
    timezone_value = _normalize_optional_text(body.timezone)

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
        if account.role == "platform_admin" and context.role != "platform_admin":
            raise ConsoleAPIError(403, "ACCESS_DENIED", "Only platform admin can assign platform_admin role")
        membership_branch = branch if account.role in {"manager", "specialist"} else None
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
        phone = _normalize_optional_text(body.phone)
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
        branch.telegram_chat_id = _normalize_optional_text(body.telegram_chat_id)
        updated_fields.append("telegram_chat_id")

    if "knowledge_tag" in fields_set:
        branch.knowledge_tag = _normalize_optional_text(body.knowledge_tag)
        updated_fields.append("knowledge_tag")

    if "timezone" in fields_set:
        branch.timezone = _normalize_optional_text(body.timezone)
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
        message="Only owner/admin/support can access provisioning",
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
        message="Only owner/admin/support can access provisioning",
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

    reason = _normalize_access_reason(body.reason, required=True)
    inputs = build_onboarding_inputs(db, branch)
    missing = missing_prerequisites(OnboardingStep.GO_NO_GO, inputs)
    if missing:
        raise ConsoleAPIError(
            409,
            "GO_LIVE_GATE_REQUIRED",
            "Go-live prerequisites missing",
            {
                "operation": "branch_go_live_approve",
                "go_live_state": _normalize_branch_go_live_state(branch.go_live_state),
                "required_step": OnboardingStep.GO_NO_GO.value,
                "missing": missing,
            },
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

    reason = _normalize_access_reason(body.reason, required=True)
    ttl_hours = _normalize_go_live_waiver_ttl_hours(body.ttl_hours)

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

    if body.role in {"manager", "specialist"} and not body.branch_id:
        raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id required for manager/specialist role")
    if body.role == "platform_admin" and context.role != "platform_admin":
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Only platform admin can assign platform_admin role")

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
        oidc_subject=body.oidc_subject,
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
            "oidc_linked": bool(body.oidc_subject),
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
        message="Only owner/admin/support can access provisioning",
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
        message="Only owner/admin/support can access provisioning",
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
        message="Only owner/admin/support can access provisioning",
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

    phone = _normalize_required_text(body.phone, "phone")
    instance_id = _normalize_required_text(body.instance_id, "instance_id")
    requested_payment_status = body.payment_status or "pending"
    if context.role != "platform_admin":
        requested_payment_status = "pending"

    company: Optional[Company] = None
    if body.company_id:
        company = db.query(Company).filter(Company.id == body.company_id).first()
        if not company:
            raise ConsoleAPIError(404, "NOT_FOUND", "Company not found")
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

    client: Optional[Client] = None
    if body.client_id:
        client = db.query(Client).filter(Client.id == body.client_id).first()
        if not client:
            raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")
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
            timezone=_normalize_optional_text(body.timezone) or _AUTOPILOT_DEFAULT_TIMEZONE,
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
        branch.timezone = _normalize_optional_text(body.timezone) or branch.timezone or _AUTOPILOT_DEFAULT_TIMEZONE
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

    contract_payload = OnboardingContractPayload.model_validate(
        {
            "domain_slug": domain_slug or purchased_capabilities.domain_slug,
            "purchased": payload_to_dict(purchased_capabilities),
        }
    )
    contract_record = _get_latest_onboarding_contract(
        db,
        client_id=client.id,
        scope="branch",
        branch_id=branch.id,
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
            reference_pack = ReferencePack(
                domain_slug=effective_domain_slug,
                title=f"Reference pack: {effective_domain_slug}",
                description="Auto-created by onboarding autopilot",
                schema_version="v1",
                status="active",
                metadata_json={"source": "onboarding_autopilot"},
                created_by=context.agent.id,
            )
            db.add(reference_pack)
            db.flush()
            actions.append("reference_pack_created")

    intake_payload = build_intake_payload(
        client_data_json=body.client_data_json or {},
        client_data_text=body.client_data_text,
    )
    if isinstance(intake_payload.get("client_pack"), dict):
        salon = intake_payload["client_pack"].setdefault("salon", {})
        if isinstance(salon, dict) and not salon.get("name"):
            salon["name"] = branch.name
        communication = salon.setdefault("communication", {}) if isinstance(salon, dict) else {}
        languages = communication.get("languages") if isinstance(communication, dict) else None
        if not isinstance(languages, list):
            communication["languages"] = []
        if not salon.get("city"):
            salon["city"] = ""
        address = salon.setdefault("address", {}) if isinstance(salon, dict) else {}
        if isinstance(address, dict) and "full" not in address:
            address["full"] = ""

    draft_version = upsert_draft(
        db,
        branch_id=branch.id,
        client_id=client.id,
        payload_json=intake_payload,
        actor_id=context.agent.id,
    )
    missing_fields, missing_questions = evaluate_intake_payload(intake_payload)
    actions.append("knowledge_draft_saved")

    published = False
    published_version_id: Optional[UUID] = None
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
            missing_fields, missing_questions = evaluate_intake_payload(published_version.payload_json)
            actions.append("knowledge_published")
        except Exception:
            actions.append("knowledge_publish_failed")

    inputs = build_onboarding_inputs(db, branch)
    go_no_go_missing = missing_prerequisites(OnboardingStep.GO_NO_GO, inputs)
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
            payload=intake_payload,
        ),
        actions=actions,
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
        message="Only owner/admin/support can access provisioning",
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
    schema_version = body.schema_version or "v1"
    status_value = body.status or "active"
    metadata_json = body.metadata or {}

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
