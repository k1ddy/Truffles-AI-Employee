"""Branch selection helpers (prompt/selection persistence)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Branch, Conversation, User
from app.routers.webhook.context_manager import _get_conversation_context, _set_conversation_context
from app.schemas.webhook import WebhookResponse
from app.services.state_machine import ConversationState

BRANCH_SELECTION_KEY = "branch_selection"
BRANCH_CONTEXT_KEY = "branch_id"
MSG_BRANCH_SELECTED = "Отлично, выбрали филиал {branch_name}. Чем могу помочь?"


def _coerce_uuid(value) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _get_branch_selection(context: dict) -> dict | None:
    selection = context.get(BRANCH_SELECTION_KEY) if isinstance(context, dict) else None
    if isinstance(selection, dict):
        return dict(selection)
    return None


def _set_branch_selection(context: dict, selection: dict | None) -> dict:
    context = dict(context)
    if selection:
        context[BRANCH_SELECTION_KEY] = selection
    else:
        context.pop(BRANCH_SELECTION_KEY, None)
    return context


def _get_user_metadata(user: User) -> dict:
    metadata = user.user_metadata if isinstance(user.user_metadata, dict) else {}
    return dict(metadata)


def _get_user_branch_preference(user: User) -> UUID | None:
    metadata = _get_user_metadata(user)
    return _coerce_uuid(metadata.get(BRANCH_CONTEXT_KEY))


def _set_user_branch_preference(user: User, branch_id: UUID) -> None:
    metadata = _get_user_metadata(user)
    metadata[BRANCH_CONTEXT_KEY] = str(branch_id)
    user.user_metadata = metadata


def _get_active_branches(db, client_id) -> list[Branch]:
    return (
        db.query(Branch)
        .filter(Branch.client_id == client_id, Branch.is_active.is_(True))
        .order_by(Branch.created_at.asc())
        .all()
    )


def _build_branch_prompt(branches: list[Branch]) -> str:
    lines = ["Пожалуйста, уточните филиал:"]
    for idx, branch in enumerate(branches, start=1):
        name = (branch.name or "").strip() or (branch.slug or "").strip() or str(branch.id)
        lines.append(f"{idx}. {name}")
    lines.append("Ответьте номером или названием филиала.")
    return "\n".join(lines)


def _build_branch_selection(branches: list[Branch], now: datetime) -> dict:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    options = [str(branch.id) for branch in branches]
    return {
        "asked_at": now.isoformat(),
        "options": options,
    }


def _match_branch_choice(
    message_text: str,
    branches: list[Branch],
    selection: dict | None,
) -> tuple[Branch | None, bool]:
    from . import _legacy as legacy

    normalized = legacy._normalize_text(message_text)
    if not normalized:
        return None, False

    if normalized.isdigit():
        index = int(normalized)
        options = selection.get("options") if isinstance(selection, dict) else None
        if isinstance(options, list) and 1 <= index <= len(options):
            target_id = _coerce_uuid(options[index - 1])
            if target_id:
                for branch in branches:
                    if branch.id == target_id:
                        return branch, True
        if 1 <= index <= len(branches):
            return branches[index - 1], True

    for branch in branches:
        name_norm = legacy._normalize_text(branch.name or "")
        slug_norm = legacy._normalize_text(branch.slug or "")
        if name_norm and name_norm in normalized:
            return branch, False
        if slug_norm and slug_norm in normalized:
            return branch, False
    return None, False


def _is_branch_only_message(message_text: str, branch: Branch, selected_by_index: bool) -> bool:
    from . import _legacy as legacy

    normalized = legacy._normalize_text(message_text)
    if not normalized:
        return False
    if selected_by_index and normalized.isdigit():
        return True
    if branch.name and normalized == legacy._normalize_text(branch.name):
        return True
    if branch.slug and normalized == legacy._normalize_text(branch.slug):
        return True
    return False


def _apply_branch_selection(
    *,
    conversation: Conversation,
    user: User,
    branch: Branch,
    context: dict,
    remember_branch: bool,
) -> None:
    updated_context = dict(context)
    updated_context[BRANCH_CONTEXT_KEY] = str(branch.id)
    updated_context.pop(BRANCH_SELECTION_KEY, None)
    _set_conversation_context(conversation, updated_context)
    conversation.branch_id = branch.id
    if remember_branch:
        _set_user_branch_preference(user, branch.id)


def _handle_branch_selection_gate(
    *,
    db: Session,
    client_id,
    settings,
    conversation: Conversation,
    user: User,
    metadata,
    message_text: str,
    now: datetime,
    send_and_save,
) -> WebhookResponse | None:
    from . import _legacy as legacy

    branch_mode = settings.branch_resolution_mode if settings and settings.branch_resolution_mode else "hybrid"
    remember_branch = (
        settings.remember_branch_preference
        if settings and settings.remember_branch_preference is not None
        else True
    )
    context = _get_conversation_context(conversation)
    branch_id = conversation.branch_id or _coerce_uuid(context.get(BRANCH_CONTEXT_KEY))
    if not branch_id and remember_branch:
        branch_id = legacy._get_user_branch_preference(user)

    if branch_id:
        if conversation.branch_id != branch_id:
            conversation.branch_id = branch_id
        if context.get(BRANCH_CONTEXT_KEY) != str(branch_id):
            context[BRANCH_CONTEXT_KEY] = str(branch_id)
            _set_conversation_context(conversation, context)
        if remember_branch and legacy._get_user_branch_preference(user) != branch_id:
            legacy._set_user_branch_preference(user, branch_id)
        return None

    instance_id = metadata.instanceId if metadata else None
    if branch_mode in {"by_instance", "hybrid"} and instance_id:
        branch = (
            db.query(Branch)
            .filter(
                Branch.client_id == client_id,
                Branch.instance_id == instance_id,
                Branch.is_active == True,
            )
            .first()
        )
        if branch:
            _apply_branch_selection(
                conversation=conversation,
                user=user,
                branch=branch,
                context=context,
                remember_branch=remember_branch,
            )

    if not conversation.branch_id and branch_mode in {"ask_user", "hybrid"}:
        branches = _get_active_branches(db, client_id)
        if len(branches) == 1:
            _apply_branch_selection(
                conversation=conversation,
                user=user,
                branch=branches[0],
                context=context,
                remember_branch=remember_branch,
            )
            return None
        if len(branches) > 1 and conversation.state == ConversationState.BOT_ACTIVE.value:
            selection = _get_branch_selection(context)
            if selection:
                matched_branch, selected_by_index = _match_branch_choice(
                    message_text, branches, selection
                )
                if matched_branch:
                    _apply_branch_selection(
                        conversation=conversation,
                        user=user,
                        branch=matched_branch,
                        context=context,
                        remember_branch=remember_branch,
                    )
                    if _is_branch_only_message(message_text, matched_branch, selected_by_index):
                        bot_response = MSG_BRANCH_SELECTED.format(
                            branch_name=matched_branch.name or matched_branch.slug or "филиал"
                        )
                        legacy._record_decision_trace(
                            conversation,
                            {
                                "stage": "branch_selection",
                                "decision": "selected",
                                "reason": "branch_only_message",
                                "branch_id": str(matched_branch.id),
                            },
                        )
                        bot_response, sent = send_and_save(bot_response)
                        result_message = (
                            "Branch selected (prompted)" if sent else "Branch selection response failed"
                        )
                        db.commit()
                        return WebhookResponse(
                            success=True,
                            message=result_message,
                            conversation_id=conversation.id,
                            bot_response=bot_response,
                        )
                else:
                    prompt = _build_branch_prompt(branches)
                    context = _set_branch_selection(context, _build_branch_selection(branches, now))
                    _set_conversation_context(conversation, context)
                    legacy._record_decision_trace(
                        conversation,
                        {
                            "stage": "branch_selection",
                            "decision": "prompt",
                            "reason": "retry",
                            "branches_count": len(branches),
                        },
                    )
                    prompt, sent = send_and_save(prompt)
                    result_message = (
                        "Branch selection requested (retry)"
                        if sent
                        else "Branch selection prompt failed"
                    )
                    db.commit()
                    return WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=prompt,
                    )
            else:
                prompt = _build_branch_prompt(branches)
                context = _set_branch_selection(context, _build_branch_selection(branches, now))
                _set_conversation_context(conversation, context)
                legacy._record_decision_trace(
                    conversation,
                    {
                        "stage": "branch_selection",
                        "decision": "prompt",
                        "reason": "initial",
                        "branches_count": len(branches),
                    },
                )
                prompt, sent = send_and_save(prompt)
                result_message = (
                    "Branch selection requested" if sent else "Branch selection prompt failed"
                )
                db.commit()
                return WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=prompt,
                )

    return None


__all__ = [
    "BRANCH_CONTEXT_KEY",
    "BRANCH_SELECTION_KEY",
    "MSG_BRANCH_SELECTED",
    "_apply_branch_selection",
    "_build_branch_prompt",
    "_build_branch_selection",
    "_coerce_uuid",
    "_get_active_branches",
    "_get_branch_selection",
    "_get_user_branch_preference",
    "_handle_branch_selection_gate",
    "_is_branch_only_message",
    "_match_branch_choice",
    "_set_branch_selection",
    "_set_user_branch_preference",
]
