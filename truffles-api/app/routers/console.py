import secrets
from datetime import date as dt_date
from datetime import datetime, time, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, Conversation, Handover, Message, User
from app.schemas.console import (
    ConsoleAgentInfo,
    ConsoleAuditEvent,
    ConsoleAuditListResponse,
    ConsoleBranch,
    ConsoleCase,
    ConsoleCaseActionResponse,
    ConsoleCaseListResponse,
    ConsoleErrorResponse,
    ConsoleHealthResponse,
    ConsoleManagerMessageRequest,
    ConsoleManagerMessageResponse,
    ConsoleMeResponse,
    ConsoleMessage,
    ConsoleMessageListResponse,
    ConsoleMetricsDailyResponse,
    ConsoleSettingsResponse,
    ConsoleSettingsUpdateRequest,
    ConsoleSettingsUpdateResponse,
    ConsoleTelegramHealthResponse,
    ConsoleTelegramTestRequest,
    ConsoleTelegramTestResponse,
    ConsoleTelegramTrail,
    ConsoleTelegramVerifyRequest,
    ConsoleTelegramVerifyResponse,
)
from app.services.audit_service import record_audit_event
from app.services.console_auth import ConsoleAuthContext, get_console_context
from app.services.console_errors import ConsoleAPIError, build_console_error_payload
from app.services.console_idempotency import (
    finalize_idempotency,
    release_idempotency,
    start_idempotency,
)

router = APIRouter(prefix="/console/v1", tags=["console"])


def _get_idempotency_key(request: Request) -> Optional[str]:
    return request.headers.get("Idempotency-Key") or request.headers.get("X-Idempotency-Key")


def _build_me_response(context: ConsoleAuthContext) -> ConsoleMeResponse:
    branches = [
        ConsoleBranch(
            id=branch.id,
            slug=branch.slug,
            name=branch.name,
            is_active=branch.is_active,
            instance_id=branch.instance_id,
            telegram_chat_id=branch.telegram_chat_id,
        )
        for branch in context.branches
    ]
    clients = [
        {
            "id": client.id,
            "slug": client.name,
            "name": client.name,
            "company_id": client.company_id,
        }
        for client in (context.accessible_clients or [])
    ]
    active_client = {
        "id": context.client.id,
        "slug": context.client.name,
        "name": context.client.name,
        "company_id": context.client.company_id,
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
        selection_required=context.selection_required,
        branch_selection_required=context.branch_selection_required,
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


def _build_telegram_link(chat_id: Optional[str], message_id: Optional[int]) -> Optional[str]:
    if not chat_id or not message_id:
        return None
    chat_id_str = str(chat_id)
    if not chat_id_str.startswith("-100"):
        return None
    internal_id = chat_id_str[4:]
    if not internal_id.isdigit():
        return None
    return f"https://t.me/c/{internal_id}/{message_id}"


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
        telegram_link=_build_telegram_link(chat_id, message_id),
        delivery_status=delivery_status,
        delivered_at=delivered_at,
    )


def _require_owner_admin(context: ConsoleAuthContext) -> None:
    if context.role not in ("owner", "admin"):
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Only owner/admin can manage Telegram connector")


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


def _parse_cursor_param(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


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
    "/cases",
    response_model=ConsoleCaseListResponse,
    responses={401: {"model": ConsoleErrorResponse}},
)
async def list_cases(
    request: Request,
    status: Optional[str] = None,
    branch_id: Optional[str] = None,
    assigned_to_me: bool = False,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> ConsoleCaseListResponse:
    context = get_console_context(request, db)
    _reject_unknown_query_params(
        request,
        {
            "status",
            "branch_id",
            "assigned_to_me",
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

    # Branch filter (RBAC + Request)
    allowed_branch_ids = {b.id for b in context.branches}
    is_privileged = context.agent.role in ("owner", "admin")

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
    if status is not None:
        if status not in {"pending", "active", "resolved"}:
            raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid status")
        query = query.filter(Handover.status == status)
    
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
        query = query.filter(Handover.assigned_to_name == context.agent.name)

    # Sorting & Pagination (Cursor based on created_at)
    query = query.order_by(Handover.created_at.desc())
    
    cursor_date = _parse_cursor_param(cursor)
    if cursor_date is not None:
        query = query.filter(Handover.created_at < cursor_date)

    # Select handover + conversation + customer
    items = query.with_entities(Handover, Conversation, User).limit(limit + 1).all()
    
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]
        next_cursor = items[-1][0].created_at.isoformat()
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
            )
            for handover, conversation, user in items
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

    # 2. Check if already taken
    if case.status == "active" and case.assigned_to_name and case.assigned_to_name != context.agent.name:
        if idempotency and idempotency.record:
            release_idempotency(db, record=idempotency.record)
        raise ConsoleAPIError(
            409,
            "CASE_ALREADY_TAKEN",
            "Case already taken",
            details={"current_assignee": case.assigned_to_name},
        )

    # Fetch conversation for branch_id before commit to avoid extra failures later
    conversation = db.query(Conversation).filter(Conversation.id == case.conversation_id).first()
    branch_id = conversation.branch_id if conversation else None

    # 3. Update
    case.status = "active"
    case.assigned_to_name = context.agent.name
    # case.assigned_to = str(context.agent.id) # If we migrate to IDs later
    db.add(case)
    
    # 4. Audit
    record_audit_event(
        db,
        actor=context.agent,
        event_type="case_taken",
        entity_type="handover",
        entity_id=case.id,
        payload={"previous_status": case.status},
        branch_id=branch_id,
    )

    try:
        db.commit()
        db.refresh(case)
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
    idempotency = None
    
    case = (
        db.query(Handover)
        .filter(Handover.id == case_id, Handover.client_id == context.client.id)
        .first()
    )
    
    if not case:
        raise ConsoleAPIError(404, "NOT_FOUND", "Case not found")

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

    case.status = "resolved"
    case.resolved_at = datetime.now(timezone.utc)
    case.resolved_by_name = context.agent.name
    db.add(case)
    
    conversation = db.query(Conversation).filter(Conversation.id == case.conversation_id).first()
    branch_id = conversation.branch_id if conversation else None

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
    "/cases/{case_id}",
    response_model=ConsoleCase,
    responses={404: {"model": ConsoleErrorResponse}},
)
async def get_case(
    case_id: UUID, request: Request, db: Session = Depends(get_db)
) -> ConsoleCase:
    """Get single case details by ID."""
    context = get_console_context(request, db)
    
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
    if case.status != "active" and context.role not in ("owner", "admin"):
        raise ConsoleAPIError(403, "CASE_NOT_ACTIVE", "Case must be active to send messages")
    
    if case.assigned_to_name != context.agent.name and context.role not in ("owner", "admin"):
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
        backlog = db.query(OutboxMessage).filter(OutboxMessage.status == "pending").count()
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
    last_error_at = _format_telegram_timestamp(result.get("last_error_date"))
    last_error_message = result.get("last_error_message")

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
    elif pending_messages > 0 or last_error_at:
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
    _require_owner_admin(context)

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
    _require_owner_admin(context)

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
    
    # Only owner/admin can update settings
    if context.role not in ("owner", "admin"):
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Only owner/admin can update settings")
    
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
