from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.schemas.console import (
    ConsoleCaseAssigneeOption,
    ConsoleCaseRoutingDecision,
    ConsoleCaseRoutingScoreFactor,
)
from app.services.console_routing_profiles import (
    ROUTING_STATUS_FOLLOW_UP_ONLY,
    ROUTING_STATUS_PAUSED,
)

CASE_ROUTING_POLICY_DEFAULT = "least_open_cases"
CASE_ROUTING_POLICY_FOLLOW_UP_SLA_BALANCE = "follow_up_sla_balance"
SUPPORTED_CASE_ROUTING_POLICIES = (
    CASE_ROUTING_POLICY_DEFAULT,
    CASE_ROUTING_POLICY_FOLLOW_UP_SLA_BALANCE,
)

_FOLLOW_UP_OWNER_BONUS = 120
_FOLLOW_UP_OVERDUE_BONUS = 60
_CURRENT_OWNER_CONTINUITY_BONUS = 8
_LOW_SLA_LOAD_WEIGHT = 10
_MEDIUM_SLA_LOAD_WEIGHT = 16
_HIGH_SLA_LOAD_WEIGHT = 24


@dataclass(frozen=True)
class CaseRoutingBookingContext:
    appointment_id: UUID | None = None
    follow_up_owner_id: UUID | None = None
    follow_up_due_at: datetime | None = None
    follow_up_overdue: bool = False


@dataclass(frozen=True)
class CaseRoutingSignalContext:
    sla_status: str = "ok"
    sla_action_state: str | None = None
    sla_overdue_minutes: int | None = None


@dataclass(frozen=True)
class _RoutingScoreEvaluation:
    option: ConsoleCaseAssigneeOption
    score: int
    breakdown: list[ConsoleCaseRoutingScoreFactor]


@dataclass(frozen=True)
class AssigneeAssignmentEvaluation:
    option: ConsoleCaseAssigneeOption
    assignment_eligible: bool
    at_capacity: bool
    block_reason_code: str | None = None


def normalize_case_routing_policy(policy: Optional[str], *, default: str = CASE_ROUTING_POLICY_DEFAULT) -> str:
    normalized = (policy or default).strip().lower()
    if normalized not in SUPPORTED_CASE_ROUTING_POLICIES:
        raise ValueError("Unsupported routing policy")
    return normalized


def adjust_case_routing_loads(
    load_overrides: dict[UUID, int],
    *,
    previous_assignee_id: Optional[str],
    next_assignee_id: str,
) -> None:
    if previous_assignee_id:
        try:
            previous_uuid = UUID(previous_assignee_id)
        except (TypeError, ValueError):
            previous_uuid = None
        if previous_uuid and previous_uuid in load_overrides:
            load_overrides[previous_uuid] = max(0, int(load_overrides.get(previous_uuid, 0)) - 1)

    try:
        next_uuid = UUID(next_assignee_id)
    except (TypeError, ValueError):
        return
    load_overrides[next_uuid] = int(load_overrides.get(next_uuid, 0)) + 1


def build_case_routing_decision(
    *,
    assignee_options: list[ConsoleCaseAssigneeOption],
    current_assignee_id: Optional[str],
    policy: str,
    load_overrides: Optional[dict[UUID, int]] = None,
    booking_context: Optional[CaseRoutingBookingContext] = None,
    signal_context: Optional[CaseRoutingSignalContext] = None,
) -> tuple[Optional[ConsoleCaseRoutingDecision], Optional[ConsoleCaseAssigneeOption]]:
    if not assignee_options:
        return None, None

    assignment_evaluations = annotate_case_assignee_options(
        assignee_options,
        current_assignee_id=current_assignee_id,
        booking_context=booking_context,
        load_overrides=load_overrides,
    )
    eligible_options = [item.option for item in assignment_evaluations if item.assignment_eligible]
    if not eligible_options:
        return None, None

    current_option = next(
        (
            option
            for option in eligible_options
            if current_assignee_id and str(option.agent_id) == current_assignee_id
        ),
        None,
    )

    if policy == CASE_ROUTING_POLICY_DEFAULT:
        recommended_option = min(
            eligible_options,
            key=lambda option: (
                _resolve_assignee_load(option, load_overrides),
                0 if current_assignee_id and str(option.agent_id) == current_assignee_id else 1,
                option.agent_name.lower(),
                str(option.agent_id),
            ),
        )
        recommended_load = _resolve_assignee_load(recommended_option, load_overrides)
        current_load = _resolve_assignee_load(current_option, load_overrides) if current_option else None
        will_reassign = not current_assignee_id or str(recommended_option.agent_id) != current_assignee_id
        breakdown = [
            ConsoleCaseRoutingScoreFactor(
                code="load",
                label="нагрузка открытыми заявками",
                value=-recommended_load,
            )
        ]
        recommended_score = -recommended_load
        current_score = -current_load if current_load is not None else None

        if not current_assignee_id:
            reason_code = "unassigned_case"
            reason_summary = (
                f"Назначить {recommended_option.agent_name}: меньше всего открытых заявок "
                f"({recommended_load}) в доступной очереди."
            )
        elif current_option is None:
            reason_code = "current_owner_unavailable"
            reason_summary = (
                f"Назначить {recommended_option.agent_name}: текущий владелец недоступен для этой очереди, "
                f"у выбранного {recommended_load} в работе."
            )
        elif not will_reassign:
            reason_code = "current_owner_kept"
            reason_summary = (
                f"Текущий владелец {recommended_option.agent_name} уже соответствует политике: "
                f"{recommended_load} в работе."
            )
        else:
            reason_code = "least_open_cases"
            reason_summary = (
                f"Назначить {recommended_option.agent_name}: {recommended_load} в работе "
                f"вместо {current_option.agent_name} · {current_load or 0}."
            )

        return (
            ConsoleCaseRoutingDecision(
                policy=policy,
                recommended_agent_id=recommended_option.agent_id,
                recommended_agent_name=recommended_option.agent_name,
                recommended_open_case_count=recommended_load,
                current_agent_id=current_option.agent_id if current_option else None,
                current_agent_name=current_option.agent_name if current_option else None,
                current_open_case_count=current_load,
                will_reassign=will_reassign,
                reason_code=reason_code,
                reason_summary=reason_summary,
                recommended_score=recommended_score,
                current_score=current_score,
                score_breakdown=breakdown,
            ),
            recommended_option,
        )

    evaluations = sorted(
        (
            _build_follow_up_sla_balance_evaluation(
                option,
                current_assignee_id=current_assignee_id,
                load_overrides=load_overrides,
                booking_context=booking_context,
                signal_context=signal_context,
            )
            for option in eligible_options
        ),
        key=lambda item: (
            -item.score,
            0 if current_assignee_id and str(item.option.agent_id) == current_assignee_id else 1,
            _resolve_assignee_load(item.option, load_overrides),
            item.option.agent_name.lower(),
            str(item.option.agent_id),
        ),
    )
    recommended = evaluations[0]
    recommended_option = recommended.option
    recommended_load = _resolve_assignee_load(recommended_option, load_overrides)
    current_load = _resolve_assignee_load(current_option, load_overrides) if current_option else None
    current_evaluation = next(
        (
            item
            for item in evaluations
            if current_assignee_id and str(item.option.agent_id) == current_assignee_id
        ),
        None,
    )
    current_score = current_evaluation.score if current_evaluation else None
    will_reassign = not current_assignee_id or str(recommended_option.agent_id) != current_assignee_id
    reason_code, reason_summary = _build_follow_up_sla_balance_reason(
        recommended=recommended,
        current_option=current_option,
        current_score=current_score,
        booking_context=booking_context,
        signal_context=signal_context,
        will_reassign=will_reassign,
    )

    return (
        ConsoleCaseRoutingDecision(
            policy=policy,
            recommended_agent_id=recommended_option.agent_id,
            recommended_agent_name=recommended_option.agent_name,
            recommended_open_case_count=recommended_load,
            current_agent_id=current_option.agent_id if current_option else None,
            current_agent_name=current_option.agent_name if current_option else None,
            current_open_case_count=current_load,
            will_reassign=will_reassign,
            reason_code=reason_code,
            reason_summary=reason_summary,
            recommended_score=recommended.score,
            current_score=current_score,
            score_breakdown=recommended.breakdown,
        ),
        recommended_option,
    )


def annotate_case_assignee_options(
    assignee_options: list[ConsoleCaseAssigneeOption],
    *,
    current_assignee_id: Optional[str],
    booking_context: Optional[CaseRoutingBookingContext] = None,
    load_overrides: Optional[dict[UUID, int]] = None,
) -> list[AssigneeAssignmentEvaluation]:
    evaluations = [
        _evaluate_case_assignee_assignment(
            option,
            current_assignee_id=current_assignee_id,
            booking_context=booking_context,
            load_overrides=load_overrides,
        )
        for option in assignee_options
    ]
    for evaluation in evaluations:
        evaluation.option.at_capacity = evaluation.at_capacity
        evaluation.option.assignment_eligible = evaluation.assignment_eligible
        evaluation.option.assignment_block_reason_code = evaluation.block_reason_code
    return evaluations


def _resolve_assignee_load(
    option: ConsoleCaseAssigneeOption,
    load_overrides: Optional[dict[UUID, int]] = None,
) -> int:
    if load_overrides is None:
        return int(option.open_case_count or 0)
    return int(load_overrides.get(option.agent_id, option.open_case_count or 0))


def _resolve_sla_load_weight(signal_context: Optional[CaseRoutingSignalContext]) -> int:
    if signal_context is None:
        return _LOW_SLA_LOAD_WEIGHT
    action_state = str(signal_context.sla_action_state or "").lower()
    sla_status = str(signal_context.sla_status or "ok").lower()
    if action_state in {"delivery_issue", "pending_outbox", "overdue"} or sla_status == "breached":
        return _HIGH_SLA_LOAD_WEIGHT
    if action_state == "reply_due" or sla_status == "warning":
        return _MEDIUM_SLA_LOAD_WEIGHT
    return _LOW_SLA_LOAD_WEIGHT


def _evaluate_case_assignee_assignment(
    option: ConsoleCaseAssigneeOption,
    *,
    current_assignee_id: Optional[str],
    booking_context: Optional[CaseRoutingBookingContext],
    load_overrides: Optional[dict[UUID, int]],
) -> AssigneeAssignmentEvaluation:
    is_current = bool(current_assignee_id and str(option.agent_id) == current_assignee_id)
    load = _resolve_assignee_load(option, load_overrides)
    at_capacity = option.max_open_case_count is not None and load >= int(option.max_open_case_count)
    status = str(option.routing_status or "available").lower()

    if is_current:
        return AssigneeAssignmentEvaluation(
            option=option,
            assignment_eligible=True,
            at_capacity=at_capacity,
        )

    if status == ROUTING_STATUS_PAUSED:
        return AssigneeAssignmentEvaluation(
            option=option,
            assignment_eligible=False,
            at_capacity=at_capacity,
            block_reason_code="paused",
        )

    if status == ROUTING_STATUS_FOLLOW_UP_ONLY:
        follow_up_match = bool(
            booking_context
            and booking_context.follow_up_owner_id
            and booking_context.follow_up_owner_id == option.agent_id
        )
        if not follow_up_match:
            return AssigneeAssignmentEvaluation(
                option=option,
                assignment_eligible=False,
                at_capacity=at_capacity,
                block_reason_code="follow_up_only",
            )

    if at_capacity:
        return AssigneeAssignmentEvaluation(
            option=option,
            assignment_eligible=False,
            at_capacity=True,
            block_reason_code="at_capacity",
        )

    return AssigneeAssignmentEvaluation(
        option=option,
        assignment_eligible=True,
        at_capacity=at_capacity,
    )


def _build_follow_up_sla_balance_evaluation(
    option: ConsoleCaseAssigneeOption,
    *,
    current_assignee_id: Optional[str],
    load_overrides: Optional[dict[UUID, int]],
    booking_context: Optional[CaseRoutingBookingContext],
    signal_context: Optional[CaseRoutingSignalContext],
) -> _RoutingScoreEvaluation:
    breakdown: list[ConsoleCaseRoutingScoreFactor] = []
    load = _resolve_assignee_load(option, load_overrides)
    load_weight = _resolve_sla_load_weight(signal_context)
    load_penalty = -(load * load_weight)
    breakdown.append(
        ConsoleCaseRoutingScoreFactor(
            code="load",
            label=(
                f"нагрузка с весом SLA x{load_weight}"
                if load_weight != _LOW_SLA_LOAD_WEIGHT
                else "нагрузка открытыми заявками"
            ),
            value=load_penalty,
        )
    )
    score = load_penalty

    if current_assignee_id and str(option.agent_id) == current_assignee_id:
        score += _CURRENT_OWNER_CONTINUITY_BONUS
        breakdown.append(
            ConsoleCaseRoutingScoreFactor(
                code="current_owner",
                label="текущий владелец",
                value=_CURRENT_OWNER_CONTINUITY_BONUS,
            )
        )

    if booking_context and booking_context.follow_up_owner_id == option.agent_id:
        score += _FOLLOW_UP_OWNER_BONUS
        breakdown.append(
            ConsoleCaseRoutingScoreFactor(
                code="follow_up_owner",
                label="владелец no-show follow-up",
                value=_FOLLOW_UP_OWNER_BONUS,
            )
        )
        if booking_context.follow_up_overdue:
            score += _FOLLOW_UP_OVERDUE_BONUS
            breakdown.append(
                ConsoleCaseRoutingScoreFactor(
                    code="follow_up_overdue",
                    label="просроченный follow-up требует continuity",
                    value=_FOLLOW_UP_OVERDUE_BONUS,
                )
            )

    return _RoutingScoreEvaluation(option=option, score=score, breakdown=breakdown)


def _build_follow_up_sla_balance_reason(
    *,
    recommended: _RoutingScoreEvaluation,
    current_option: ConsoleCaseAssigneeOption | None,
    current_score: int | None,
    booking_context: Optional[CaseRoutingBookingContext],
    signal_context: Optional[CaseRoutingSignalContext],
    will_reassign: bool,
) -> tuple[str, str]:
    recommended_name = recommended.option.agent_name
    recommended_score = recommended.score
    load = _resolve_assignee_load(recommended.option)
    current_suffix = ""
    if current_option is not None and current_score is not None:
        current_suffix = f" вместо {current_option.agent_name} · score {current_score}."
    else:
        current_suffix = "."

    if booking_context and booking_context.follow_up_owner_id == recommended.option.agent_id:
        if booking_context.follow_up_overdue:
            return (
                "follow_up_owner_overdue",
                f"Назначить {recommended_name}: у него уже overdue no-show follow-up по связанной записи, score {recommended_score}{current_suffix}",
            )
        return (
            "follow_up_owner_continuity",
            f"Назначить {recommended_name}: он ведет follow-up по связанной записи, score {recommended_score}{current_suffix}",
        )

    action_state = str(signal_context.sla_action_state or "").lower() if signal_context else ""
    sla_status = str(signal_context.sla_status or "ok").lower() if signal_context else "ok"
    if action_state in {"delivery_issue", "pending_outbox", "overdue", "reply_due"} or sla_status in {"warning", "breached"}:
        if not will_reassign:
            return (
                "current_owner_kept",
                f"Текущий владелец {recommended_name} уже лучший по политике: score {recommended_score}, нагрузка {load}.",
            )
        return (
            "sla_risk_balanced_load",
            f"Назначить {recommended_name}: из-за SLA-риска нагрузка учитывается строже, score {recommended_score}{current_suffix}",
        )

    if not will_reassign:
        return (
            "current_owner_kept",
            f"Текущий владелец {recommended_name} уже лучший по политике: score {recommended_score}, нагрузка {load}.",
        )

    if current_option is None:
        return (
            "current_owner_unavailable",
            f"Назначить {recommended_name}: текущий владелец недоступен, лучший score {recommended_score}.",
        )

    return (
        "follow_up_sla_balance",
        f"Назначить {recommended_name}: лучший баланс нагрузки и continuity, score {recommended_score}{current_suffix}",
    )
