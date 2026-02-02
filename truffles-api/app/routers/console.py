import re
import secrets
from datetime import date as dt_date
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Agent,
    AgentIdentity,
    AgentMembership,
    Branch,
    Client,
    ClientCapability,
    ClientSettings,
    Company,
    Conversation,
    Handover,
    KnowledgeVersion,
    Message,
    OutboxMessage,
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
    ConsoleAgentListResponse,
    ConsoleAgentWithIdentities,
    ConsoleAuditEvent,
    ConsoleAuditListResponse,
    ConsoleBranch,
    ConsoleBranchCreateRequest,
    ConsoleBranchCreateResponse,
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
    ConsoleHealthResponse,
    ConsoleKnowledgeCurrentResponse,
    ConsoleKnowledgeHistoryItem,
    ConsoleKnowledgeHistoryResponse,
    ConsoleKnowledgePublishRequest,
    ConsoleKnowledgePublishResponse,
    ConsoleKnowledgeRollbackRequest,
    ConsoleKnowledgeRollbackResponse,
    ConsoleKnowledgeValidateRequest,
    ConsoleKnowledgeValidateResponse,
    ConsoleMacroCreateRequest,
    ConsoleMacroCreateResponse,
    ConsoleMacroListResponse,
    ConsoleMacroUpdateRequest,
    ConsoleManagerMessageRequest,
    ConsoleManagerMessageResponse,
    ConsoleMeResponse,
    ConsoleMessage,
    ConsoleMessageListResponse,
    ConsoleMetricsDailyResponse,
    ConsoleOnboardingAdvanceRequest,
    ConsoleOnboardingStatusResponse,
    ConsoleOnboardingStepStatus,
    ConsoleOutboxCounts,
    ConsoleOutboxItem,
    ConsoleOutboxListResponse,
    ConsoleOutboxRetryRequest,
    ConsoleOutboxRetryResponse,
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
)
from app.schemas.console import (
    ConsoleMacro as ConsoleMacroSchema,
)
from app.schemas.outbox_payload import validate_outbox_payload
from app.services.agent_link_service import build_telegram_deep_link, create_agent_link_token
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
from app.services.knowledge_registry_service import (
    apply_pack_index_to_client_config,
    get_current_published,
    list_history,
    publish_version,
    restore_version,
    sync_qdrant_from_pack,
    upsert_draft,
    validate_draft,
)
from app.services.knowledge_validation import dump_pack_yaml
from app.services.manager_message_service import (
    notify_client_manager_status,
    process_console_media_upload,
)
from app.services.onboarding_state import (
    OnboardingStep,
    advance_onboarding_step,
    build_onboarding_status,
    ensure_onboarding_step,
)
from app.services.pack_compiler_service import (
    PackCompilerError,
    build_compiled_pack_meta,
    extract_compiled_artifacts,
    parse_compiled_at,
)
from app.services.state_service import manager_resolve as state_manager_resolve
from app.services.state_service import manager_take as state_manager_take
from app.services.telegram_service import TelegramService

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
    branches = [
        ConsoleBranch(
            id=branch.id,
            slug=branch.slug,
            name=branch.name,
            is_active=branch.is_active,
            instance_id=branch.instance_id,
            telegram_chat_id=branch.telegram_chat_id,
            onboarding_state=branch.onboarding_state,
            onboarding_updated_at=branch.onboarding_updated_at.isoformat()
            if branch.onboarding_updated_at
            else None,
        )
        for branch in context.branches
    ]
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
    query = db.query(Branch).filter(Branch.client_id == client_id, column == value)
    if exclude_branch_id:
        query = query.filter(Branch.id != exclude_branch_id)
    if query.first():
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} already in use")


def _serialize_branch(branch: Branch) -> ConsoleBranch:
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
    )


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


def _require_platform_admin(context: ConsoleAuthContext) -> None:
    _require_roles(
        context,
        allowed=("platform_admin", "owner", "admin", "support"),
        message="Only platform admin/owner/admin/support can access admin operations",
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

    result = state_manager_resolve(
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

    case.resolution_notes = "Returned to bot by manager"

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
    
    # Get conversation to find user
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise ConsoleAPIError(404, "NOT_FOUND", "Conversation not found")

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

    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise ConsoleAPIError(404, "NOT_FOUND", "Conversation not found")

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
        )
    
    return ConsoleSettingsResponse(
        branches=[
            ConsoleBranch(
                id=b.id,
                slug=b.slug,
                name=b.name,
                is_active=b.is_active,
                instance_id=b.instance_id,
                telegram_chat_id=b.telegram_chat_id,
            )
            for b in branches
        ],
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


@router.get(
    "/metrics/daily",
    response_model=ConsoleMetricsDailyResponse,
)
async def get_metrics_daily(
    request: Request,
    date: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ConsoleMetricsDailyResponse:
    """Get daily metrics for cases."""
    from app.schemas.console import ConsoleMetricsDailyResponse
    
    context = get_console_context(request, db)
    require_console_permission(context, "ops", "read")
    
    _reject_unknown_query_params(request, {"date"})

    # Parse date or use today
    if date is not None:
        target_date = _parse_date_param("date", date)
    else:
        target_date = datetime.now(timezone.utc).date()
    
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
    
    return ConsoleMetricsDailyResponse(
        date=target_date.isoformat(),
        total_cases=total,
        pending_cases=pending,
        active_cases=active,
        resolved_cases=resolved,
        avg_resolution_hours=avg_resolution,
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
        sync_qdrant_from_pack(
            payload,
            client_slug=context.client.name,
            branch_id=branch.id,
            knowledge_tag=branch.knowledge_tag,
            version_id=version.id,
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
        sync_qdrant_from_pack(
            version.payload_json,
            client_slug=context.client.name,
            branch_id=branch.id,
            knowledge_tag=branch.knowledge_tag,
            version_id=restored.id,
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
    db: Session = Depends(get_db),
) -> ConsoleClientListResponse:
    context = get_console_context(request, db, require_selection=False)
    _require_platform_admin(context)
    _reject_unknown_query_params(request, {"cursor", "limit", "q", "company_id"})
    _validate_limit(limit)

    company_uuid = _parse_uuid_param("company_id", company_id)
    query = db.query(Client)
    if company_uuid:
        query = query.filter(Client.company_id == company_uuid)

    query_value = _normalize_search_query("q", q) if q else None
    if query_value:
        query_value_lower = query_value.lower()
        uuid_value = _looks_like_uuid(query_value)
        filters = []
        if uuid_value:
            filters.append(Client.id == uuid_value)
        filters.append(func.lower(Client.name).like(f"%{query_value_lower}%"))
        query = query.filter(or_(*filters))

    cursor_date = _parse_cursor_param(cursor)
    if cursor_date is not None:
        query = query.filter(Client.created_at < cursor_date)

    items = (
        query.order_by(Client.created_at.desc(), Client.id.desc())
        .limit(limit + 1)
        .all()
    )
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]
    next_cursor = items[-1].created_at.isoformat() if has_more and items[-1].created_at else None

    company_ids = {client.company_id for client in items if client.company_id}
    companies_by_id: dict[UUID, Company] = {}
    if company_ids:
        companies = db.query(Company).filter(Company.id.in_(company_ids)).all()
        companies_by_id = {company.id: company for company in companies}

    return ConsoleClientListResponse(
        items=[
            ConsoleClient(
                id=client.id,
                slug=client.name,
                name=client.name,
                company_id=client.company_id,
                company_name=companies_by_id.get(client.company_id).name
                if client.company_id and client.company_id in companies_by_id
                else None,
            )
            for client in items
        ],
        cursor=next_cursor,
        has_more=has_more,
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
    db: Session = Depends(get_db),
) -> ConsoleBranchListResponse:
    context = get_console_context(request, db, require_selection=False)
    _require_platform_admin(context)
    _reject_unknown_query_params(request, {"cursor", "limit", "q", "client_id"})
    _validate_limit(limit)

    client_uuid = _parse_uuid_param("client_id", client_id)
    query = db.query(Branch)
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
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise ConsoleAPIError(404, "NOT_FOUND", "Company not found")

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
    context = get_console_context(request, db, require_selection=False)
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
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")

    updated_fields: list[str] = []
    fields_set = body.model_fields_set
    company = None

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

    if "status" in fields_set:
        status_value = _normalize_required_text(body.status, "status")
        if status_value != client.status:
            client.status = status_value
        updated_fields.append("status")

    if "company_id" in fields_set:
        if body.company_id:
            company = db.query(Company).filter(Company.id == body.company_id).first()
            if not company:
                raise ConsoleAPIError(404, "NOT_FOUND", "Company not found")
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
    "/admin/branches",
    response_model=ConsoleBranchCreateResponse,
    responses={403: {"model": ConsoleErrorResponse}, 404: {"model": ConsoleErrorResponse}},
)
async def create_branch(
    request: Request,
    body: ConsoleBranchCreateRequest,
    db: Session = Depends(get_db),
) -> ConsoleBranchCreateResponse:
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )

    client = db.query(Client).filter(Client.id == body.client_id).first()
    if not client:
        raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")

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
        created_at=now,
        updated_at=now,
    )
    db.add(branch)
    record_audit_event(
        db,
        actor=context.agent,
        event_type="branch_created",
        entity_type="branch",
        entity_id=branch.id,
        payload={"slug": slug, "name": name, "is_active": is_active},
        client_id=client.id,
        branch_id=branch.id,
    )
    db.commit()

    return ConsoleBranchCreateResponse(branch=_serialize_branch(branch))


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
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")

    confirmation = None
    previous_instance_id = branch.instance_id

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

    if updated_fields:
        branch.updated_at = datetime.now(timezone.utc)
        record_audit_event(
            db,
            actor=context.agent,
            event_type="branch_updated",
            entity_type="branch",
            entity_id=branch.id,
            payload={"updated_fields": updated_fields},
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
    context = get_console_context(request, db, require_selection=False)
    require_console_permission(
        context,
        "provisioning",
        "write",
        message="Only owner/admin can manage provisioning",
    )

    client = db.query(Client).filter(Client.id == body.client_id).first()
    if not client:
        raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")

    if body.role == "manager" and not body.branch_id:
        raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id required for manager role")
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
    agent = Agent(
        id=uuid4(),
        client_id=client.id,
        branch_id=branch.id if branch else None,
        role=body.role,
        name=_normalize_optional_text(body.name),
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )
    db.add(agent)

    membership = AgentMembership(
        id=uuid4(),
        agent_id=agent.id,
        scope="branch" if branch else "client",
        company_id=client.company_id,
        client_id=client.id,
        branch_id=branch.id if branch else None,
        role=body.role,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )
    db.add(membership)

    if body.oidc_subject:
        identity = AgentIdentity(
            id=uuid4(),
            agent_id=agent.id,
            channel="oidc",
            external_id=body.oidc_subject,
            username=body.name,
            identity_metadata={"linked_from": "admin_api"},
            created_at=now,
            updated_at=now,
        )
        db.add(identity)

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
        agent=ConsoleAgent(
            id=agent.id,
            name=agent.name,
            role=agent.role,
            client_id=agent.client_id,
            branch_id=agent.branch_id,
            is_active=agent.is_active,
        )
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
